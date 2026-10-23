"""Build deterministic OI portable geometry from an explicit garden manifest.

This adapter produces inferred LOD0/LOD1 surfaces/envelopes, never a survey.
It uses WGS84 ECEF/ENU coordinates and OI's X-east, Y-up, -Z-north frame.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import tempfile
import re
import uuid
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

Json = dict[str, Any]
Point = tuple[float, float]


def canonical(value: Any) -> bytes:
    """Serialize semantic content deterministically, rejecting nonfinite numbers."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value: Any) -> str:
    """Identify JSON content independently of formatting."""
    return hashlib.sha256(canonical(value)).hexdigest()


def number(value: Any) -> float:
    """Require a finite numeric value; booleans are not measurements."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Expected a finite number')
    return float(value)


def text(value: Any) -> str:
    """Require bounded nonblank text for source references and IDs."""
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ValueError('Expected 1–512 characters of nonblank text')
    return value


def ecef(longitude: float, latitude: float, height: float) -> list[float]:
    """Convert WGS84 degrees and ellipsoidal meters into ECEF meters."""
    lon, lat = math.radians(longitude), math.radians(latitude)
    n = 6378137.0 / math.sqrt(1 - 6.6943799901413165e-3 * math.sin(lat) ** 2)
    return [(n + height) * math.cos(lat) * math.cos(lon),
            (n + height) * math.cos(lat) * math.sin(lon),
            (n * (1 - 6.6943799901413165e-3) + height) * math.sin(lat)]


def frame(anchor: Json) -> list[list[float]]:
    """Return row-major OI Y-up local-to-ECEF matrix at heading zero."""
    lon, lat = number(anchor['longitude']), number(anchor['latitude'])
    if not (-74.4 < lon < -73.6 and 40 < lat < 41.1):
        raise ValueError('Expected NYC longitude/latitude in WGS84 degrees')
    height = 0.0 if anchor['height_m'] is None else number(anchor['height_m'])
    x, y = math.radians(lon), math.radians(lat)
    origin = ecef(lon, lat, height)
    east = [-math.sin(x), math.cos(x), 0]
    up = [math.cos(y) * math.cos(x), math.cos(y) * math.sin(x), math.sin(y)]
    south = [math.sin(y) * math.cos(x), math.sin(y) * math.sin(x), -math.cos(y)]
    return [[east[i], up[i], south[i], origin[i]] for i in range(3)] + [[0, 0, 0, 1]]


def local_point(coordinate: list[float], anchor: Json) -> list[float]:
    """Project one WGS84 lon/lat pair onto the anchor's meter frame."""
    if len(coordinate) != 2:
        raise ValueError('Footprints use two-dimensional lon/lat coordinates')
    lon, lat = map(number, coordinate)
    if not (-74.4 < lon < -73.6 and 40 < lat < 41.1):
        raise ValueError('Footprint coordinate outside NYC')
    matrix = frame(anchor)
    point = ecef(lon, lat, anchor['height_m'] or 0.0)
    delta = [point[i] - matrix[i][3] for i in range(3)]
    return [sum(matrix[i][j] * delta[i] for i in range(3)) for j in range(3)]


def cross(a: Point, b: Point, c: Point) -> float:
    """Return the signed twice-area of a 2D triangle."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def on_segment(a: Point, b: Point, p: Point) -> bool:
    """Test boundary membership with sub-micrometer numeric tolerance."""
    return abs(cross(a, b, p)) < 1e-8 and all(min(a[i], b[i]) - 1e-8 <= p[i] <= max(a[i], b[i]) + 1e-8 for i in (0, 1))


def intersects(a: Point, b: Point, c: Point, d: Point) -> bool:
    """Detect crossing or touching line segments, including collinear overlap."""
    return (cross(a, b, c) * cross(a, b, d) < 0 and cross(c, d, a) * cross(c, d, b) < 0) or any((on_segment(a, b, c), on_segment(a, b, d), on_segment(c, d, a), on_segment(c, d, b)))


def triangulate(points: list[Point]) -> list[int]:
    """Ear-clip one simple ring; reject self-intersections and degeneracies."""
    n = len(points)
    if not 3 <= n <= 500 or len(set(points)) != n:
        raise ValueError('Expected 3–500 distinct polygon vertices')
    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            if intersects(points[i], points[(i + 1) % n], points[j], points[(j + 1) % n]):
                raise ValueError('Self-intersecting footprint')
    area = sum(points[i][0] * points[(i + 1) % n][1] - points[(i + 1) % n][0] * points[i][1] for i in range(n))
    if abs(area) < 1e-6:
        raise ValueError('Degenerate footprint')
    remaining = list(range(n)) if area > 0 else list(reversed(range(n)))
    triangles: list[int] = []
    while len(remaining) > 3:
        for i, b in enumerate(remaining):
            a, c = remaining[i - 1], remaining[(i + 1) % len(remaining)]
            if cross(points[a], points[b], points[c]) <= 1e-8:
                continue
            if any(all(cross(points[u], points[v], points[p]) >= -1e-8 for u, v in ((a, b), (b, c), (c, a))) for p in remaining if p not in (a, b, c)):
                continue
            triangles.extend([a, c, b])  # X/Z CCW reversed for upward Y normals.
            remaining.pop(i)
            break
        else:
            raise ValueError('Cannot triangulate footprint; simplify collinear vertices')
    triangles.extend([remaining[0], remaining[2], remaining[1]])
    return triangles


def inside(point: Point, polygon: list[Point]) -> bool:
    """Test point-in-polygon, accepting boundary points."""
    result = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if on_segment(a, b, point):
            return True
        if (a[1] > point[1]) != (b[1] > point[1]) and point[0] < (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]) + a[0]:
            result = not result
    return result


def provenance(value: Json) -> Json:
    """Allowlist evidence fields and require documented geometry reuse rights."""
    source = text(value['source_url'])
    if not source.startswith(('https://', 'http://')):
        raise ValueError('Expected source URL')
    observed = value['observed_at']
    if observed is not None:
        if len(observed) != 10:
            raise ValueError('Expected YYYY-MM-DD observation date')
        date.fromisoformat(observed)
    if value['confidence'] not in ('high', 'medium', 'low', 'unknown'):
        raise ValueError('Invalid confidence')
    rights = value['rights']
    if rights['status'] not in ('owned', 'licensed', 'permission'):
        raise ValueError('Geometry use requires documented rights; unknown is link-only')
    return {'source_url': source, 'observed_at': observed, 'confidence': value['confidence'],
            'rights': {'status': rights['status'], 'reference': text(rights['reference'])},
            'note': text(value['note'])}


def box(dimensions: list[float]) -> tuple[list[float], list[int]]:
    """Create a bottom-centered, indexed LOD1 box in Y-up meters."""
    w, h, d = dimensions
    vertices = [v for x, y, z in [(-w/2,0,-d/2),(w/2,0,-d/2),(w/2,h,-d/2),(-w/2,h,-d/2),(-w/2,0,d/2),(w/2,0,d/2),(w/2,h,d/2),(-w/2,h,d/2)] for v in (x,y,z)]
    return vertices, [0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,3,7,6,3,6,2,0,4,7,0,7,3,1,2,6,1,6,5]


def build_scene(manifest: Json) -> tuple[Json, Json]:
    """Create native portable OI geometry and a separate georeferencing sidecar.

    Manifest v2 explicitly permits inferred renderings. It is separate from
    scene_quality's v1 verified-only physical-feature gate.
    """
    if manifest['schema_version'] != '2.0':
        raise ValueError('Expected garden manifest version 2.0')
    source = manifest['source']
    if source['coordinate_system'] != 'EPSG:4326':
        raise ValueError('Expected EPSG:4326')
    record_id, url = text(source['record_id']), text(source['url'])
    anchor = {k: manifest['anchor'][k] for k in ('longitude', 'latitude', 'height_m')}
    matrix = frame(anchor)
    features = manifest['features']
    if not isinstance(features, list) or len(features) > 999:
        raise ValueError('Expected at most 999 features')
    footprint = manifest['footprint']
    if footprint is None:
        raise ValueError('No footprint: a registry point cannot produce site geometry')
    if footprint['status'] not in ('source_backed', 'inferred'):
        raise ValueError('Invalid footprint evidence status')
    evidence = provenance(footprint['provenance'])
    geometry = footprint['geometry']
    if geometry['type'] != 'Polygon' or len(geometry['coordinates']) != 1:
        raise ValueError('v2 supports a single Polygon without holes; never discard holes')
    ring = geometry['coordinates'][0]
    if len(ring) < 4 or ring[0] != ring[-1]:
        raise ValueError('Polygon ring must be closed')
    points = [(p[0], p[2]) for p in (local_point(c, anchor) for c in ring[:-1])]
    indices = triangulate(points)
    assets: list[Json] = []
    instances: list[Json] = []
    records: list[Json] = []
    unknowns: list[Json] = []
    extents = [abs(v) for p in points for v in p]
    if max(extents) > 50:
        raise ValueError('Footprint exceeds OI 100m room; choose a closer anchor or smaller explicit site')
    bounds = [max(1.0, 2 * max(abs(p[0]) for p in points)), max(1.0, 2 * max(abs(p[1]) for p in points)), 1.0]

    def add(fid: str, category: str, vertices: list[float], triangles: list[int], position: list[float], rotation: list[float], ev: Json, status: str, representation: str) -> None:
        """Normalize an OI asset once, preserving placement and metadata."""
        lo = [min(vertices[i::3]) for i in range(3)]
        hi = [max(vertices[i::3]) for i in range(3)]
        offset = [(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2]
        normalized = [v - offset[i % 3] for i, v in enumerate(vertices)]
        angle = math.radians(rotation[1])
        position = [position[0] + math.cos(angle)*offset[0] + math.sin(angle)*offset[2], position[1] + offset[1], position[2] - math.sin(angle)*offset[0] + math.cos(angle)*offset[2]]
        feature_record = {'instance_id': fid, 'category': category, 'evidence_status': status,
                          'representation': representation, 'provenance': ev, 'record_id': record_id,
                          'anchor': anchor, 'adapter': 'nyc-robo-garden/2.0'}
        name = f'[INFERRED {representation}] {fid}'[:512]
        asset_id = 'garden-' + hashlib.sha256((record_id + ':' + fid).encode()).hexdigest()[:24]
        src = {'kind': 'generated', 'generator': 'form-industries', 'filename': 'garden-manifest.json',
               'digest': digest({'feature': feature_record, 'vertices': normalized, 'indices': triangles})}
        asset = {'schemaVersion': 1, 'id': asset_id, 'name': name, 'source': src, 'units': 'm', 'upAxis': 'Y',
                 'originOffset': offset, 'dimensions': [hi[i] - lo[i] for i in range(3)],
                 'parts': [{'id': fid, 'name': name, 'vertices': normalized, 'indices': triangles,
                            'color': [0.35, 0.48, 0.28] if category == 'terrain' else [0.65, 0.45, 0.22],
                            'metadata': {'gardenEvidence': canonical(feature_record).decode()}}],
                 'hierarchy': {'id': asset_id, 'name': name, 'partIds': [fid], 'children': []},
                 'warnings': ['Procedural inferred representation; not surveyed geometry or physical validation.']}
        assets.append(asset)
        instances.append({'id': fid, 'assetId': asset_id, 'name': name, 'position': position, 'rotation': rotation, 'visible': True})
        records.append(feature_record)

    add('site-ground', 'terrain', [v for x,z in points for v in (x,0,z)], indices, [0,0,0], [0,0,0], evidence, footprint['status'], 'LOD0 flat surface')
    ids = {'site-ground'}
    for feature in sorted(features, key=lambda f: f['id']):
        fid = text(feature['id'])
        if len(fid) > 160 or re.fullmatch(r'[a-zA-Z0-9_.:/-]+', fid) is None:
            raise ValueError('Feature IDs must be MCP-compatible ASCII identifiers, at most 160 characters')
        if fid in ids:
            raise ValueError('Duplicate feature ID')
        ids.add(fid)
        category = feature['category']
        if category not in ('bed','growing_area','path','greenhouse','building','water','power','crop','seasonal_product'):
            raise ValueError('Invalid feature category')
        if feature['status'] == 'unknown':
            if feature.get('geometry') is not None:
                raise ValueError('Unknown features cannot have geometry')
            unknowns.append({'id': fid, 'category': category, 'reason': text(feature['reason'])})
            continue
        if feature['status'] not in ('source_backed', 'inferred'):
            raise ValueError('Invalid feature evidence status')
        ev = provenance(feature['provenance'])
        geom = feature['geometry']
        if geom['type'] != 'box':
            raise ValueError('LOD1 features require explicit box geometry')
        dims = list(map(number, geom['dimensions_m']))
        pos = list(map(number, geom['position_m']))
        angle = number(geom['yaw_degrees'])
        if len(dims) != 3 or len(pos) != 3 or not all(0 < d <= 100 for d in dims) or pos[1] < 0 or pos[1] + dims[1] > 100:
            raise ValueError('Invalid dimensions or position; expected X/Y/Z meters')
        verts, tris = box(dims)
        theta = math.radians(angle)
        corners = [(pos[0] + math.cos(theta)*x + math.sin(theta)*z, pos[2] - math.sin(theta)*x + math.cos(theta)*z) for x,z in [(-dims[0]/2,-dims[2]/2),(dims[0]/2,-dims[2]/2),(dims[0]/2,dims[2]/2),(-dims[0]/2,dims[2]/2)]]
        # Concave boundaries require checking entire edges, not only corners.
        if not all(inside(p, points) for p in corners):
            raise ValueError('Feature envelope extends outside footprint')
        for a,b in zip(corners, corners[1:]+corners[:1]):
            for c,d in zip(points, points[1:]+points[:1]):
                if cross(a,b,c)*cross(a,b,d) < -1e-12 and cross(c,d,a)*cross(c,d,b) < -1e-12:
                    raise ValueError('Feature envelope crosses footprint boundary')
        bounds[2] = max(bounds[2], pos[1] + dims[1])
        add(fid, category, verts, tris, pos, [0,angle,0], ev, feature['status'], 'LOD1 envelope')
    scene = {'format': 'astra.scene', 'version': 1, 'units': 'm', 'upAxis': 'Y', 'room': bounds,
             'assets': [{k: a[k] for k in ('id','name','source','dimensions')} for a in assets],
             'instances': instances, 'bundledAssets': assets, 'bundledVersions': [],
             'animation': {'duration': 1, 'loop': False, 'tracks': []}}
    sidecar = {'schema': 'garden-georeference/1', 'manifest_sha256': digest(manifest), 'scene_sha256': digest(scene),
               'source': {'record_id': record_id, 'url': url, 'coordinate_system': 'EPSG:4326'},
               'anchor': anchor, 'height_assumed_zero': anchor['height_m'] is None,
               'local_frame': 'meters; +X east, +Y up, -Z north; heading 0',
               'local_to_ecef_column_major': [matrix[i][j] for j in range(4) for i in range(4)],
               'features': records, 'unknowns': unknowns,
               'registry_snapshot_version': manifest.get('registry_snapshot_version'),
               'evidence': manifest.get('evidence', []),
               'limitations': ['All rendered surfaces/envelopes are inferred, including flat terrain.',
                               'Source-backed evidence does not make procedural geometry surveyed.',
                               'No current crops, yields, site access or robot suitability inferred.']}
    return scene, sidecar


def prepare_manifest(registry: Json, garden_id: str, evidence_bundle: Json | None = None) -> Json:
    """Select a registry site without inventing layout from a pin or tax lot.

    Optional raw evidence is validated through the #6 importer and filtered to
    this confirmed site. Ambiguous matches never become scene facts.
    """
    from garden_registry.evidence import validate

    matches = [record for record in registry['records'] if record['id'] == garden_id]
    if len(matches) != 1:
        raise ValueError('Expected one exact stable garden ID in registry')
    record = matches[0]
    anchor = {'longitude': record['longitude'], 'latitude': record['latitude'], 'height_m': None}
    frame(anchor)
    evidence: list[Json] = []
    if evidence_bundle is not None:
        imported = validate(evidence_bundle, registry)
        sources = {item['id']: item for item in imported['sources']}
        for claim in imported['accepted'] + imported['unknowns']:
            if claim['site_match']['status'] == 'confirmed' and claim['site_match']['garden_id'] == garden_id:
                evidence.append({'record': claim, 'sources': [sources[c['source_id']] for c in claim['citations']]})
    return {'schema_version': '2.0', 'source': {'record_id': garden_id, 'url': record['source_url'], 'coordinate_system': 'EPSG:4326'},
            'registry_snapshot_version': registry['snapshot_version'], 'anchor': anchor,
            'footprint': None, 'features': [], 'evidence': sorted(evidence, key=lambda e: e['record']['id'])}


def write_json(path: Path, value: Any) -> None:
    """Write stable readable JSON; inputs must not contain credentials."""
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def reload_package(directory: Path) -> tuple[Json, Json]:
    """Rebuild and verify a saved bundle before accepting geometry/provenance."""
    manifest = json.loads((directory / 'garden-manifest.json').read_text())
    expected_scene, expected_meta = build_scene(manifest)
    scene = json.loads((directory / 'garden.oi.json').read_text())
    meta = json.loads((directory / 'garden-georeference.json').read_text())
    if scene != expected_scene or meta != expected_meta:
        raise ValueError('Scene or georeferencing does not match the retained manifest')
    return scene, meta


def build_mcp_request(directory: Path, versions: dict[str, str], backend: str = 'cloud') -> Json:
    """Bind verified portable geometry to immutable OI versions for MCP.

    The caller must upload/inspect these exact generated assets first. Asset
    readiness and ownership are enforced by OI, not guessed by this adapter.
    """
    if backend not in ('cloud', 'local'):
        raise ValueError('Expected cloud or local asset backend')
    scene, meta = reload_package(directory)
    if set(versions) != {asset['id'] for asset in scene['assets']}:
        raise ValueError('Provide exactly one version for each portable asset ID')
    for version in versions.values():
        if str(uuid.UUID(version)) != version.lower():
            raise ValueError('Expected canonical version UUID')
    payload = {'name': ('Garden | ' + meta['source']['record_id'])[:200],
               'room': dict(zip(('width', 'depth', 'height'), scene['room'])),
               'instances': [{k: item[k] for k in ('id', 'name', 'position', 'rotation', 'visible')} |
                              {'asset': {'kind': backend, 'version_id': versions[item['assetId']]}}
                             for item in scene['instances']]}
    return {'version': 1, 'request_id': str(uuid.uuid5(uuid.NAMESPACE_URL, digest(payload))),
            'agent': 'nyc-robo-garden', 'scene': payload}


def import_local_assets(directory: Path, oi_root: Path, data_dir: Path) -> dict[str, str]:
    """Import verified bundled geometry through OI's validating local CLI."""
    scene, _ = reload_package(directory)
    oi_root = oi_root.resolve()
    cli = oi_root / 'cli/local-scenes.ts'
    if not cli.is_file():
        raise ValueError('OI checkout lacks the local scene backend')
    env = dict(os.environ, ASTRA_SCENE_BACKEND='local',
               ASTRA_SCENE_DATA_DIR=str(data_dir.resolve()), ASTRA_ROOT=str(oi_root))
    versions = {}
    with tempfile.TemporaryDirectory() as tmp:
        bundle = Path(tmp) / 'asset.json'
        for asset in scene['bundledAssets']:
            write_json(bundle, {'schemaVersion': 1, 'asset': asset})
            result = subprocess.run(['node', '--import', 'tsx', str(cli), 'import-asset', str(bundle)],
                                    cwd=oi_root, env=env, check=True, capture_output=True, text=True)
            reference = json.loads(result.stdout)
            if reference.get('kind') != 'local':
                raise ValueError('OI returned a non-local asset reference')
            versions[asset['id']] = reference['version_id']
    build_mcp_request(directory, versions, 'local')
    return versions


def export_package(manifest: Json, output: Path, oi_root: Path | None = None) -> Json:
    """Write a portable bundle and optionally run OI's actual 3D Tiles exporter."""
    scene, sidecar = build_scene(manifest)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use an empty output directory to avoid stale scene files')
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'garden-manifest.json', manifest)
    write_json(output / 'garden.oi.json', scene)
    write_json(output / 'garden-georeference.json', sidecar)
    reload_package(output)
    if oi_root is not None:
        exporter = oi_root / 'tools/geospatial/export_scene.py'
        if not exporter.is_file():
            raise ValueError('OI geospatial exporter not found')
        anchor = sidecar['anchor']
        subprocess.run([sys.executable, str(exporter.resolve()), str((output / 'garden.oi.json').resolve()),
                        str((output / 'tiles').resolve()), f"--longitude={anchor['longitude']}",
                        f"--latitude={anchor['latitude']}", f"--height={anchor['height_m'] or 0}", '--heading=0',
                        '--license-note=See ../garden-georeference.json for per-feature rights; procedural inferred geometry'], check=True)
        # OI's exporter intentionally allowlists metadata: retain a companion
        # linked by exact instance IDs instead of claiming it exports all fields.
        write_json(output / 'tiles/garden-evidence.json', sidecar)
    return {'scene_sha256': digest(scene), 'instances': len(scene['instances']), 'unknowns': len(sidecar['unknowns']), 'tiles_exported': oi_root is not None}


def main() -> None:
    """Generate or verify a portable garden scene from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build')
    build.add_argument('manifest', type=Path)
    build.add_argument('--output', type=Path, required=True)
    build.add_argument('--oi-root', type=Path)
    mcp = commands.add_parser('mcp-request')
    mcp.add_argument('directory', type=Path)
    mcp.add_argument('--asset-versions', type=Path, required=True)
    mcp.add_argument('--send', action='store_true')
    mcp.add_argument('--oi-root', type=Path)
    mcp.add_argument('--backend', choices=('cloud', 'local'), default='cloud')
    mcp.add_argument('--data-dir', type=Path, help='Local SQLite/assets directory; required for local --send')
    local = commands.add_parser('import-local')
    local.add_argument('directory', type=Path)
    local.add_argument('--oi-root', type=Path, required=True)
    local.add_argument('--data-dir', type=Path, required=True)
    local.add_argument('--output', type=Path, required=True, help='Write local asset-version bindings')
    prepare = commands.add_parser('prepare')
    prepare.add_argument('--registry', type=Path, required=True)
    prepare.add_argument('--garden-id', required=True)
    prepare.add_argument('--evidence', type=Path, help='Raw evidence bundle from the #6 contract')
    prepare.add_argument('--output', type=Path, required=True)
    reload = commands.add_parser('reload')
    reload.add_argument('directory', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'build':
            result = export_package(json.loads(args.manifest.read_text()), args.output, args.oi_root)
        elif args.command == 'import-local':
            if args.output.exists():
                raise ValueError('Asset bindings output already exists')
            versions = import_local_assets(args.directory, args.oi_root, args.data_dir)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            write_json(args.output, versions)
            result = {'assets': len(versions), 'bindings': str(args.output), 'backend': 'local'}
        elif args.command == 'mcp-request':
            request = build_mcp_request(args.directory, json.loads(args.asset_versions.read_text()), args.backend)
            result = {'tool': 'astra.create_scene', 'arguments': request}
            if args.send:
                from scripts.garden_to_oi_mcp import send_request
                if args.oi_root is None or not (args.oi_root/'server/astra-mcp.mjs').is_file():
                    raise ValueError('--send requires --oi-root with the real MCP server')
                env = {'ASTRA_SCENE_BACKEND': 'local' if args.backend == 'local' else 'supabase'}
                if args.backend == 'local':
                    if args.data_dir is None:
                        raise ValueError('Local --send requires --data-dir matching import-local')
                    env['ASTRA_SCENE_DATA_DIR'] = str(args.data_dir.resolve())
                result = asyncio.run(send_request(request, args.oi_root/'server/astra-mcp.mjs', args.oi_root, env))
        elif args.command == 'prepare':
            draft = prepare_manifest(json.loads(args.registry.read_text()), args.garden_id,
                                     json.loads(args.evidence.read_text()) if args.evidence else None)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            write_json(args.output, draft)
            result = {'record_id': args.garden_id, 'status': 'needs_explicit_footprint', 'evidence_records': len(draft['evidence'])}
        else:
            scene, meta = reload_package(args.directory)
            result = {'scene_sha256': digest(scene), 'instances': len(scene['instances']), 'record_id': meta['source']['record_id']}
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Garden scene failed: {exc}\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()

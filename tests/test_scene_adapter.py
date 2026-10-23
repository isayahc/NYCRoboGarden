"""Geometry, provenance and deterministic package regression tests."""
from __future__ import annotations

import copy
import asyncio
import json
import math
import os
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

from garden_registry.scene_adapter import build_mcp_request, build_scene, export_package, frame, import_local_assets, local_point, prepare_manifest, reload_package, triangulate

ROOT = Path(__file__).resolve().parents[1]


def fixture() -> dict:
    """Load the explicitly fictional garden fixture."""
    return json.loads((ROOT / 'data/scenes/fictional-garden.json').read_text())


class SceneAdapterTests(unittest.TestCase):
    """Verify geometry never silently becomes measured or loses provenance."""

    def test_generated_scene_and_unknowns(self) -> None:
        """Produce real indexed geometry but no invented water connection."""
        scene, meta = build_scene(fixture())
        self.assertEqual(len(scene['instances']), 4)
        self.assertEqual(len(meta['unknowns']), 1)
        self.assertTrue(meta['height_assumed_zero'])
        self.assertTrue(all(i['name'].startswith('[INFERRED ') for i in scene['instances']))
        self.assertEqual(scene['room'][2], 3)
        for asset in scene['bundledAssets']:
            self.assertEqual(asset['source']['kind'], 'generated')
            self.assertGreaterEqual(len(asset['parts'][0]['indices']), 6)

    def test_registry_and_evidence_handoff(self) -> None:
        """Select stable IDs and preserve historical evidence without making beds."""
        registry = {'snapshot_version': 'fixture', 'records': [{
            'id': 'nyc-greenthumb:B400-GT001', 'longitude': -73.947992,
            'latitude': 40.689338, 'source_url': 'https://data.cityofnewyork.us/resource/p78i-pat6.json'}]}
        raw = json.loads((ROOT/'data/evidence/hattie-carthan.json').read_text())
        draft = prepare_manifest(registry, 'nyc-greenthumb:B400-GT001', raw)
        self.assertIsNone(draft['footprint'])
        self.assertEqual(draft['features'], [])
        self.assertEqual(len(draft['evidence']), 9)
        self.assertNotIn('herban-herbs-unresolved', {e['record']['id'] for e in draft['evidence']})
        with self.assertRaisesRegex(ValueError, 'No footprint'):
            build_scene(draft)
        with self.assertRaises(ValueError):
            prepare_manifest(registry, 'missing')

    def test_local_axes_and_multiple_anchors(self) -> None:
        """ECEF basis remains orthonormal, right-handed and meter scale."""
        for lon, lat in [(-73.95, 40.68), (-74.02, 40.72)]:
            a = {'longitude': lon, 'latitude': lat, 'height_m': 12}
            m = frame(a)
            self.assertLess(max(map(abs, local_point([lon, lat], a))), 1e-8)
            for i in range(3):
                for j in range(3):
                    self.assertAlmostEqual(sum(m[k][i]*m[k][j] for k in range(3)), float(i == j), places=12)
            # Independent local curvature formulas: 1e-5 degree east/north.
            latr = math.radians(lat)
            e2 = 6.6943799901413165e-3
            n = 6378137 / math.sqrt(1-e2*math.sin(latr)**2)
            meridian = 6378137*(1-e2)/(1-e2*math.sin(latr)**2)**1.5
            east = local_point([lon+1e-5, lat], a)
            north = local_point([lon, lat+1e-5], a)
            self.assertAlmostEqual(east[0], math.radians(1e-5)*(n+12)*math.cos(latr), places=6)
            self.assertAlmostEqual(north[2], -math.radians(1e-5)*(meridian+12), places=6)

    def test_concave_polygon_area_and_self_intersection(self) -> None:
        """Ear clipping preserves a concave footprint rather than filling its hull."""
        polygon = [(0,0),(4,0),(4,1),(1,1),(1,4),(0,4)]
        indices = triangulate(polygon)
        area = 0.0
        for i in range(0,len(indices),3):
            a,b,c = [polygon[k] for k in indices[i:i+3]]
            area += abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
        self.assertAlmostEqual(area, 7)
        with self.assertRaises(ValueError):
            triangulate([(0,0),(3,3),(0,3),(3,0)])

    def test_determinism_and_tampered_reload(self) -> None:
        """JSON exports are repeatable and reject edited geometry or sidecars."""
        m = fixture()
        first = build_scene(m)
        m['features'].reverse()
        second = build_scene(m)
        self.assertEqual(first[0], second[0])
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)/'package'
            export_package(m, directory)
            self.assertEqual(reload_package(directory), second)
            path = directory/'garden.oi.json'
            scene = json.loads(path.read_text())
            scene['instances'][0]['position'][0] += 1
            path.write_text(json.dumps(scene))
            with self.assertRaisesRegex(ValueError, 'does not match'):
                reload_package(directory)

    def test_rejects_unsupported_or_unlicensed_geometry(self) -> None:
        """Reject missing footprint, holes, unknown rights, oversize and bad data."""
        mutations = [lambda m: m.update(footprint=None),
                     lambda m: m['footprint']['geometry']['coordinates'].append(m['footprint']['geometry']['coordinates'][0]),
                     lambda m: m['footprint']['provenance']['rights'].update(status='unknown'),
                     lambda m: m['anchor'].update(latitude=-73.95),
                     lambda m: m['anchor'].update(height_m=float('nan')),
                     lambda m: m['features'][0]['geometry'].update(dimensions_m=[False,1,1]),
                     lambda m: m['features'][0]['geometry'].update(dimensions_m=[200,1,1]),
                     lambda m: m['features'][0]['geometry'].update(position_m=[8,0,10]),
                     lambda m: m['features'].append(copy.deepcopy(m['features'][0]))]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                m = fixture()
                mutation(m)
                with self.assertRaises(ValueError):
                    build_scene(m)

    def test_provenance_survives_normalization(self) -> None:
        """Asset metadata and sidecar retain dates, confidence, IDs and rights."""
        scene, meta = build_scene(fixture())
        for asset, instance, feature in zip(scene['bundledAssets'], scene['instances'], meta['features']):
            self.assertEqual(json.loads(asset['parts'][0]['metadata']['gardenEvidence']), feature)
            self.assertEqual(feature['instance_id'], instance['id'])
        ground = scene['bundledAssets'][0]
        pose = scene['instances'][0]['position']
        first = local_point(fixture()['footprint']['geometry']['coordinates'][0][0], fixture()['anchor'])
        self.assertAlmostEqual(ground['parts'][0]['vertices'][0] + pose[0], first[0])
        self.assertAlmostEqual(ground['parts'][0]['vertices'][2] + pose[2], first[2])

    def test_mcp_exact_asset_bindings(self) -> None:
        """Reject incomplete bindings; repeated requests have stable identities."""
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)/'package'
            export_package(fixture(), directory)
            scene, _ = reload_package(directory)
            versions = {a['id']: str(uuid.uuid5(uuid.NAMESPACE_URL, a['id'])) for a in scene['assets']}
            request = build_mcp_request(directory, versions)
            self.assertEqual(request, build_mcp_request(directory, versions))
            local = build_mcp_request(directory, versions, 'local')
            self.assertNotEqual(local['request_id'], request['request_id'])
            self.assertTrue(all(i['asset']['kind'] == 'local' for i in local['scene']['instances']))
            with self.assertRaises(ValueError):
                build_mcp_request(directory, versions, 'invalid')
            self.assertEqual(request['scene']['room']['depth'], scene['room'][1])
            self.assertEqual(request['scene']['instances'][1]['position'], scene['instances'][1]['position'])
            with self.assertRaises(ValueError):
                build_mcp_request(directory, {})
            versions[scene['assets'][0]['id']] = 'not-a-uuid'
            with self.assertRaises(ValueError):
                build_mcp_request(directory, versions)

    @unittest.skipUnless(os.environ.get('OI_ROOT'), 'Set OI_ROOT to an npm-installed OI checkout')
    def test_local_sqlite_mcp_restart_export(self) -> None:
        """Persist generated garden assets, restart MCP and reopen SQLite export."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from scripts.garden_to_oi_mcp import send_request
        oi = Path(os.environ['OI_ROOT']).resolve()
        with tempfile.TemporaryDirectory() as tmp:
            directory, store = Path(tmp)/'package', Path(tmp)/'store'
            export_package(fixture(), directory)
            versions = import_local_assets(directory, oi, store)
            self.assertEqual(versions, import_local_assets(directory, oi, store))
            request = build_mcp_request(directory, versions, 'local')
            env = dict(os.environ, ASTRA_ROOT=str(oi), ASTRA_SCENE_BACKEND='local',
                       ASTRA_SCENE_DATA_DIR=str(store), ASTRA_SCENE_TOOLS_ENABLED='true',
                       VITE_SUPABASE_URL='', VITE_SUPABASE_PUBLISHABLE_KEY='',
                       ASTRA_CLI_CONFIG=str(Path(tmp)/'no-login.json'))

            async def verify():
                created = await send_request(request, oi/'server/astra-mcp.mjs', oi, env)
                self.assertEqual(created['revision_id'], 1)
                # send_request closes its server; this is a fresh MCP process.
                server = StdioServerParameters(command='node', args=[str(oi/'server/astra-mcp.mjs')], env=env)
                async with stdio_client(server) as (reader, writer):
                    async with ClientSession(reader, writer) as session:
                        await session.initialize()
                        read = await session.call_tool('astra.read_scene', {'version': 1, 'scene_id': created['scene_id']})
                        self.assertFalse(read.isError)
                        self.assertEqual(read.structuredContent['scene']['instances'], request['scene']['instances'])
                        retry = await session.call_tool('astra.create_scene', request)
                        self.assertFalse(retry.isError)
                        self.assertEqual(retry.structuredContent, created)
                return created

            created = asyncio.run(verify())
            self.assertTrue((store/'scenes.sqlite').is_file())
            portable = directory/'sqlite-export.json'
            subprocess.run(['node', '--import', 'tsx', 'cli/local-scenes.ts', 'export',
                            created['scene_id'], str(portable), '1'], cwd=oi, env=env, check=True)
            subprocess.run(['node', '--import', 'tsx', str(ROOT/'scripts/verify_oi_roundtrip.mjs'),
                            str(directory), str(portable)], cwd=oi, check=True)

    @unittest.skipUnless(os.environ.get('OI_ROOT'), 'Set OI_ROOT to an npm-installed OI checkout')
    def test_actual_oi_roundtrip_and_tiles(self) -> None:
        """Run upstream hydration/export/reimport and its geospatial converter."""
        oi = Path(os.environ['OI_ROOT']).resolve()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)/'package'
            export_package(fixture(), directory, oi)
            scene, _ = reload_package(directory)
            versions = {a['id']: str(uuid.uuid5(uuid.NAMESPACE_URL, a['id'])) for a in scene['assets']}
            request = build_mcp_request(directory, versions)
            (directory/'mcp-request.json').write_text(json.dumps(request))
            subprocess.run(['node','--import','tsx',str(ROOT/'scripts/verify_oi_roundtrip.mjs'),str(directory)],cwd=oi,check=True)
            tiles = json.loads((directory/'tiles/tileset.json').read_text())
            sidecar = json.loads((directory/'garden-georeference.json').read_text())
            self.assertEqual(len(tiles['root']['children']), 4)
            # OI exporter root maps ENU (Z-up); our sidecar maps E/U/-N.
            enu = tiles['root']['transform']
            ours = sidecar['local_to_ecef_column_major']
            for i in range(3):
                self.assertAlmostEqual(enu[i], ours[i], places=12)
                self.assertAlmostEqual(enu[8+i], ours[4+i], places=12)
                self.assertAlmostEqual(-enu[4+i], ours[8+i], places=12)
                self.assertAlmostEqual(enu[12+i], ours[12+i], places=8)
            for child in tiles['root']['children']:
                self.assertTrue((directory/'tiles'/child['content']['uri']).is_file())
                self.assertIn(child['metadata']['properties']['instanceId'], {f['instance_id'] for f in sidecar['features']})

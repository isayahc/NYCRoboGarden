"""Normalize GreenThumb records and attach explicitly identified parcel geometry."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import urlopen

DATASET = 'p78i-pat6'
API = f'https://data.cityofnewyork.us/resource/{DATASET}.json'
CATALOG = f'https://data.cityofnewyork.us/dataset/{DATASET}'
METADATA = f'https://data.cityofnewyork.us/api/views/{DATASET}.json'
TERMS = 'https://opendata.cityofnewyork.us/overview/#termsofuse'
SCHEMA_VERSION = '1.0.0'
BOROUGHS = {'B': 'Brooklyn', 'X': 'Bronx', 'M': 'Manhattan', 'Q': 'Queens', 'R': 'Staten Island'}
JSON = dict[str, Any]


def canonical(value: Any) -> str:
    """Serialize JSON deterministically, rejecting non-finite numbers."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    """Return the full SHA256 of canonical JSON."""
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(url: str) -> Any:
    """Fetch public JSON with a timeout; propagate failures rather than publish partial data."""
    with urlopen(url, timeout=60) as response:
        return json.load(response)


def fetch_snapshot(fetch: Callable[[str], Any] = read_json, page_size: int = 1000) -> tuple[list[JSON], JSON]:
    """Page in source row-ID order, rejecting source changes or inconsistent counts."""
    if not 1 <= page_size <= 50000:
        raise ValueError('page_size must be between 1 and 50000')
    before = fetch(METADATA)
    if not before.get('rowsUpdatedAt'):
        raise ValueError('Source update timestamp missing')
    count_url = API + '?' + urlencode({'$select': 'count(*)'})
    count = int(fetch(count_url)[0]['count'])
    rows: list[JSON] = []
    while len(rows) < count:
        page = fetch(API + '?' + urlencode({'$limit': page_size, '$offset': len(rows), '$order': ':id'}))
        if not isinstance(page, list) or not page:
            raise ValueError('Unexpected empty or invalid source page')
        rows.extend(page)
    after = fetch(METADATA)
    if before['rowsUpdatedAt'] != after.get('rowsUpdatedAt') or len(rows) != count or int(fetch(count_url)[0]['count']) != count:
        raise ValueError('Source changed during download; retry the complete snapshot')
    return rows, after


def clean(value: Any) -> str:
    """Trim and normalize whitespace in a source field."""
    return ' '.join(str(value or '').split())


def bbls(value: Any) -> list[str]:
    """Accept only explicit ten-digit NYC BBLs, not inferred address matches."""
    parts = re.split(r'[;,\s/]+', clean(value))
    return sorted({p for p in parts if re.fullmatch(r'[1-5][0-9]{9}', p)})


def location(row: JSON) -> tuple[float, float] | None:
    """Read source latitude/longitude; never manufacture a polygon centroid."""
    try:
        lat, lon = float(row['lat']), float(row['lon'])
    except (KeyError, TypeError, ValueError):
        return None
    if math.isfinite(lat) and math.isfinite(lon) and 40 <= lat <= 42 and -75 <= lon <= -72:
        return lat, lon
    return None


def polygon(value: Any) -> JSON | None:
    """Validate WGS84 polygon structure/ranges; this is not a topology or survey check."""
    if not isinstance(value, dict) or value.get('type') not in ('Polygon', 'MultiPolygon'):
        return None
    coords = value.get('coordinates')
    polygons = [coords] if value['type'] == 'Polygon' else coords
    if not isinstance(polygons, list) or not polygons:
        return None
    for rings in polygons:
        if not isinstance(rings, list) or not rings:
            return None
        for ring in rings:
            if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
                return None
            for point in ring:
                if not isinstance(point, list) or len(point) != 2:
                    return None
                if any(isinstance(n, bool) or not isinstance(n, (float, int)) or not math.isfinite(n) for n in point):
                    return None
                if not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                    return None
            if len({tuple(p) for p in ring[:-1]}) < 3:
                return None
    return {'type': value['type'], 'coordinates': coords}


@dataclass(frozen=True)
class Garden:
    """A stable source entity; points, mapped boundaries and parcels remain distinct."""
    id: str
    version: str
    parks_id: str
    name: str
    address: str
    borough: str
    status: str
    latitude: float | None
    longitude: float | None
    location_geometry: JSON | None
    source_boundaries: list[JSON]
    parcel_candidates: list[JSON]
    bbls: list[str]
    source_url: str
    source_row_hashes: list[str]
    source_row_count: int
    conflicts: JSON
    warnings: list[str]


def parcel_index(collection: JSON | None, metadata: JSON | None) -> dict[str, list[JSON]]:
    """Index a supplied WGS84 parcel FeatureCollection by explicit BBL identifiers."""
    if collection is None:
        return {}
    required = ('source_url', 'source_version', 'retrieved_at', 'license_status', 'terms_url')
    if not metadata or any(not metadata.get(k) for k in required):
        raise ValueError('Parcel metadata requires ' + ', '.join(required))
    if collection.get('type') != 'FeatureCollection' or 'crs' in collection or not isinstance(collection.get('features'), list):
        raise ValueError('Parcels must be RFC 7946 WGS84 GeoJSON without a legacy CRS')
    result: dict[str, list[JSON]] = {}
    for feature in collection['features']:
        if not isinstance(feature, dict) or feature.get('type') != 'Feature':
            raise ValueError('Invalid parcel feature')
        props = feature.get('properties') or {}
        ids = bbls(props.get('bbl', props.get('BBL')))
        geometry = polygon(feature.get('geometry'))
        if len(ids) != 1 or geometry is None:
            raise ValueError('Each parcel requires one ten-digit BBL and a valid WGS84 polygon')
        candidate = {'bbl': ids[0], 'geometry': geometry, 'role': 'tax_lot_candidate',
                     'match_method': 'exact_source_bbl', 'is_verified_garden_footprint': False,
                     'provenance': metadata}
        result.setdefault(ids[0], []).append(candidate)
    return {key: [items[h] for h in sorted(items)] for key, values in result.items()
            for items in [{digest(v): v for v in values}]}


def normalize(rows: list[JSON], parcels: dict[str, list[JSON]] | None = None) -> list[Garden]:
    """Deduplicate by Parks ID and report conflicting values without fuzzy merging."""
    groups: dict[str, list[JSON]] = {}
    for row in rows:
        if not isinstance(row, dict) or not clean(row.get('parksid')):
            raise ValueError('Every garden row requires a Parks ID; refusing unstable generated IDs')
        groups.setdefault(clean(row['parksid']).upper(), []).append(row)
    records: list[Garden] = []
    for parks_id, group in sorted(groups.items()):
        # Deterministic representative: prefer valid location, then completeness, then canonical JSON.
        ordered = sorted(group, key=lambda r: (location(r) is None, -sum(bool(v) for v in r.values()), canonical(r)))
        row = ordered[0]
        loc = location(row)
        conflicts: JSON = {}
        for field in sorted(set().union(*(r.keys() for r in group))):
            variants = {canonical(r.get(field)): r.get(field) for r in group}
            if len(variants) > 1:
                conflicts[field] = [variants[k] for k in sorted(variants)]
        boundaries = {digest(g): g for r in group if (g := polygon(r.get('multipolygon'))) is not None}
        ids = sorted({b for r in group for b in bbls(r.get('bbl'))})
        warnings = []
        if loc is None:
            warnings.append('missing_or_invalid_source_location')
        if any(r.get('multipolygon') is not None and polygon(r['multipolygon']) is None for r in group):
            warnings.append('invalid_source_boundary_omitted')
        if any(clean(r.get('bbl')) and not bbls(r['bbl']) for r in group):
            warnings.append('invalid_source_bbl')
        if conflicts:
            warnings.append('conflicting_source_rows_review_required')
        if parcels is not None and any(b not in parcels for b in ids):
            warnings.append('some_bbls_have_no_supplied_parcel')
        hashes = sorted({digest(r) for r in group})
        records.append(Garden(
            id=f'nyc-greenthumb:{parks_id}', version=digest(hashes), parks_id=parks_id,
            name=clean(row.get('gardenname')), address=clean(row.get('address')),
            borough=BOROUGHS.get(clean(row.get('borough')), clean(row.get('borough'))),
            status=clean(row.get('status')), latitude=loc[0] if loc else None,
            longitude=loc[1] if loc else None,
            location_geometry={'type': 'Point', 'coordinates': [loc[1], loc[0]]} if loc else None,
            source_boundaries=[{'geometry': boundaries[k], 'role': 'source_mapped_garden_boundary',
                                'source_field': 'multipolygon', 'source_url': CATALOG,
                                'is_verified_garden_footprint': False} for k in sorted(boundaries)],
            parcel_candidates=[p for b in ids for p in (parcels or {}).get(b, [])], bbls=ids,
            source_url=API + '?' + urlencode({'$where': "parksid='" + clean(row['parksid']).replace("'", "''") + "'"}),
            source_row_hashes=hashes, source_row_count=len(group), conflicts=conflicts, warnings=warnings))
    return records


def build(rows: list[JSON], metadata: JSON, retrieved_at: str,
          parcel_geojson: JSON | None = None, parcel_metadata: JSON | None = None) -> JSON:
    """Build a versioned snapshot with source metadata, quality counts and typed records."""
    if metadata.get('id') != DATASET:
        raise ValueError('Metadata does not identify the expected GreenThumb dataset')
    index = parcel_index(parcel_geojson, parcel_metadata)
    records = normalize(rows, index if parcel_geojson is not None else None)
    source = {'dataset_id': DATASET, 'catalog_url': CATALOG, 'api_url': API,
              'attribution': metadata.get('attribution'), 'retrieved_at': retrieved_at,
              'source_updated_at': metadata.get('rowsUpdatedAt'),
              'refresh_frequency': metadata.get('metadata', {}).get('custom_fields', {}).get('Update', {}).get('Update Frequency', 'unspecified'),
              'license_id': metadata.get('licenseId'),
              'license_status': 'declared' if metadata.get('licenseId') else 'unspecified',
              'terms_url': TERMS, 'metadata_sha256': digest(metadata),
              'raw_rows_sha256': digest(rows)}
    return {'schema_version': SCHEMA_VERSION,
            'snapshot_version': digest({'schema': SCHEMA_VERSION, 'records': [asdict(r) for r in records],
                                        'source_metadata': metadata}),
            'source': source, 'parcel_source': parcel_metadata,
            'summary': {'input_rows': len(rows), 'gardens': len(records),
                        'duplicate_rows_collapsed': len(rows) - len(records),
                        'missing_locations': sum(r.location_geometry is None for r in records),
                        'gardens_with_boundaries': sum(bool(r.source_boundaries) for r in records),
                        'gardens_with_parcels': sum(bool(r.parcel_candidates) for r in records),
                        'conflicting_ids': sum(bool(r.conflicts) for r in records)},
            'records': [asdict(r) for r in records]}


def write_json(path: Path, value: Any) -> None:
    """Write readable UTF-8 JSON, never permitting NaN or Infinity."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def main() -> None:
    """Download or replay a source snapshot and write the registry plus a point layer."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, help='Replay saved GreenThumb JSON rows offline')
    parser.add_argument('--metadata', type=Path, help='Saved Socrata metadata for offline replay')
    parser.add_argument('--parcels', type=Path, help='Optional local WGS84 parcel GeoJSON with bbl/BBL')
    parser.add_argument('--parcel-metadata', type=Path, help='Required provenance JSON for supplied parcels')
    parser.add_argument('--retrieved-at', help='Original snapshot retrieval timestamp for offline replay')
    parser.add_argument('--output', type=Path, default=Path('data/generated'))
    args = parser.parse_args()
    if bool(args.raw) != bool(args.metadata) or bool(args.parcels) != bool(args.parcel_metadata):
        parser.error('--raw/--metadata and --parcels/--parcel-metadata must be supplied in pairs')
    if args.raw and not args.retrieved_at:
        parser.error('--retrieved-at is required for offline replay')
    if not args.raw and args.retrieved_at:
        parser.error('--retrieved-at is only valid for offline replay')
    retrieved = args.retrieved_at or datetime.now(timezone.utc).isoformat()
    timestamp = datetime.fromisoformat(retrieved.replace('Z', '+00:00'))
    if timestamp.tzinfo is None:
        parser.error('retrieved-at must include a timezone')
    rows, metadata = ((json.loads(args.raw.read_text()), json.loads(args.metadata.read_text()))
                      if args.raw else fetch_snapshot())
    parcel_data = json.loads(args.parcels.read_text()) if args.parcels else None
    parcel_meta = json.loads(args.parcel_metadata.read_text()) if args.parcel_metadata else None
    result = build(rows, metadata, retrieved, parcel_data, parcel_meta)
    # Validate everything before publishing outputs; source errors leave no partial registry.
    canonical(result)
    write_json(args.output / 'source.rows.json', rows)
    write_json(args.output / 'source.metadata.json', metadata)
    if parcel_data is not None:
        write_json(args.output / 'source.parcels.geojson', parcel_data)
        write_json(args.output / 'source.parcels.metadata.json', parcel_meta)
    write_json(args.output / 'registry.json', result)
    write_json(args.output / 'locations.geojson', {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'id': r['id'], 'geometry': r['location_geometry'],
         'properties': {'name': r['name'], 'geometry_role': 'source_location_point',
                        'is_footprint': False, 'registry_id': r['id']}} for r in result['records']]})
    print(json.dumps(result['summary'], sort_keys=True))


if __name__ == '__main__':
    main()

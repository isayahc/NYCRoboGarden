"""Offline contract tests for source identity, evidence and geometry semantics."""
import copy
import json
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from garden_registry.registry import DATASET, METADATA, build, fetch_snapshot, normalize, parcel_index, polygon

FIXTURES = Path(__file__).parent / 'fixtures'


class RegistryTests(unittest.TestCase):
    """Exercise malformed inputs, source changes and deterministic normalization."""

    def setUp(self) -> None:
        """Load a small, captured official source sample."""
        self.rows = json.loads((FIXTURES / 'greenthumb.json').read_text())
        self.metadata = json.loads((FIXTURES / 'metadata.json').read_text())

    def test_identity_and_version(self) -> None:
        """IDs survive source corrections while record versions change."""
        old = normalize(self.rows)[0]
        changed = copy.deepcopy(self.rows)
        for row in changed:
            row['address'] = 'Corrected address'
        new = normalize(changed)[0]
        self.assertEqual(old.id, new.id)
        self.assertNotEqual(old.version, new.version)

    def test_dedup_is_order_independent_and_conflicts_retained(self) -> None:
        """Conflicting rows cannot silently erase evidence or depend on row order."""
        duplicate = copy.deepcopy(self.rows[0])
        duplicate['address'] = 'Alternate address'
        rows = self.rows + [duplicate, self.rows[0]]
        a = build(rows, self.metadata, '2026-10-23T17:00:00Z')
        b = build(list(reversed(rows)), self.metadata, '2026-10-24T17:00:00Z')
        self.assertEqual(a['records'], b['records'])
        self.assertEqual(a['snapshot_version'], b['snapshot_version'])
        self.assertEqual(a['summary']['duplicate_rows_collapsed'], 2)
        self.assertEqual(a['summary']['conflicting_ids'], 1)
        record = next(r for r in a['records'] if r['parks_id'] == self.rows[0]['parksid'])
        self.assertEqual(len(record['conflicts']['address']), 2)

    def test_missing_location_is_not_a_centroid(self) -> None:
        """A polygon does not justify fabricating a source location coordinate."""
        row = dict(self.rows[0]);row.pop('lat')
        record = normalize([row])[0]
        self.assertIsNone(record.location_geometry)
        self.assertIsNone(record.latitude)
        self.assertTrue(record.source_boundaries)
        self.assertFalse(record.source_boundaries[0]['is_verified_garden_footprint'])

    def test_invalid_coordinates(self) -> None:
        """Non-finite, zero and swapped locations are rejected."""
        for lat, lon in [('NaN', '-73'), ('0', '0'), ('-73', '40'), ('inf', '-73')]:
            with self.subTest(lat=lat, lon=lon):
                self.assertIsNone(normalize([{**self.rows[0], 'lat': lat, 'lon': lon}])[0].location_geometry)

    def test_missing_identity_fails(self) -> None:
        """Never manufacture unstable garden IDs when source identity disappears."""
        with self.assertRaises(ValueError):
            normalize([{'gardenname': 'Unknown'}])

    def test_bad_boundary_is_omitted(self) -> None:
        """Source points and malformed polygons cannot become boundaries."""
        for geometry in [{'type': 'Point', 'coordinates': [-73, 40]},
                         {'type': 'Polygon', 'coordinates': []},
                         {'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1]]]},
                         {'type': 'Polygon', 'coordinates': [[[1000000, 200000], [1, 0], [1, 1], [1000000, 200000]]]}]:
            with self.subTest(geometry=geometry):
                self.assertIsNone(polygon(geometry))
                r = normalize([{**self.rows[0], 'multipolygon': geometry}])[0]
                self.assertEqual(r.source_boundaries, [])
                self.assertIn('invalid_source_boundary_omitted', r.warnings)

    def test_parcel_exact_match_and_provenance(self) -> None:
        """Parcel matches remain candidates rather than garden footprints."""
        meta = {'source_url': 'https://example.org/parcels', 'source_version': 'synthetic-test',
                'retrieved_at': '2026-10-23T17:00:00Z', 'license_status': 'test fixture',
                'terms_url': 'https://example.org/terms'}
        feature = {'type': 'Feature', 'properties': {'BBL': self.rows[0]['bbl']},
                   'geometry': self.rows[0]['multipolygon']}
        collection = {'type': 'FeatureCollection', 'features': [feature, feature]}
        index = parcel_index(collection, meta)
        records = normalize(self.rows, index)
        matching = next(r for r in records if r.parks_id == self.rows[0]['parksid'])
        self.assertEqual(len(matching.parcel_candidates), 1)
        self.assertFalse(matching.parcel_candidates[0]['is_verified_garden_footprint'])
        self.assertEqual(matching.parcel_candidates[0]['provenance'], meta)
        self.assertEqual(sum(bool(r.parcel_candidates) for r in records), 1)
        with self.assertRaises(ValueError):
            parcel_index(collection, None)
        with self.assertRaises(ValueError):
            parcel_index({**collection, 'crs': {'name': 'EPSG:2263'}}, meta)

    def test_license_is_not_invented(self) -> None:
        """Missing publisher license fields remain explicitly unspecified."""
        result = build(self.rows, self.metadata, '2026-10-23T17:00:00Z')
        self.assertEqual(result['source']['license_status'], 'unspecified')
        self.assertEqual(result['schema_version'], '1.0.0')
        with self.assertRaises(ValueError):
            build(self.rows, {'id': 'wrong'}, '2026-10-23T17:00:00Z')

    def test_pagination_and_source_change(self) -> None:
        """A complete multi-page fetch succeeds; mid-fetch updates abort."""
        calls = []
        def fetch(url: str) -> object:
            """Return deterministic source pages for an offline pagination test."""
            calls.append(url)
            if url == METADATA:
                return {'id': DATASET, 'rowsUpdatedAt': 1}
            query = parse_qs(urlparse(url).query)
            if '$select' in query:
                return [{'count': '2'}]
            self.assertEqual(query['$order'], [':id'])
            return self.rows[int(query['$offset'][0]):int(query['$offset'][0]) + 1]
        rows, _ = fetch_snapshot(fetch, page_size=1)
        self.assertEqual(rows, self.rows)
        self.assertEqual(len(calls), 6)
        count = 0
        def changed(url: str) -> object:
            """Simulate a dataset update between the before and after metadata reads."""
            nonlocal count
            if url == METADATA:
                count += 1
                return {'rowsUpdatedAt': count}
            return fetch(url)
        with self.assertRaises(ValueError):
            fetch_snapshot(changed, page_size=1)


if __name__ == '__main__':
    unittest.main()

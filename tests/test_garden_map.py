"""Check geographic provenance, missing-coordinate handling and map snapshot integrity."""
import json
from pathlib import Path
import unittest

from scripts.build_garden_map import BOROUGHS, build, simplify_ring


class GardenMapTests(unittest.TestCase):
    def test_coordinates_are_preserved_and_missing_points_not_invented(self):
        ring = [[-74, 40.7], [-73.99, 40.7], [-73.99, 40.71], [-74, 40.7]]
        boroughs = [{'boroname': name, 'the_geom': {'type': 'Polygon', 'coordinates': [ring]}} for name in BOROUGHS.values()]
        gardens = [{'parksid': 'B1', 'gardenname': 'A', 'borough': 'B', 'lat': '40.123456789', 'lon': '-73.987654321'},
                   {'parksid': 'B2', 'gardenname': 'B', 'borough': 'B', 'lat': '', 'lon': ''}]
        result = build(gardens, boroughs)
        self.assertEqual(result['record_count'], 2)
        self.assertEqual(result['mapped_count'], 1)
        self.assertEqual(result['gardens'][0]['location'], [-73.987654321, 40.123456789])
        self.assertIsNone(result['gardens'][1]['location'])
        self.assertEqual(result['crs'], 'EPSG:4326')

    def test_closed_ring_survives_simplification(self):
        ring = [[-74, 40.7], [-73.99999, 40.7], [-73.99998, 40.7],
                [-73.99, 40.7], [-73.99, 40.71], [-74, 40.71], [-74, 40.7]]
        result = simplify_ring(ring)
        self.assertEqual(result[0], result[-1])
        self.assertGreaterEqual(len(result), 4)
        self.assertLess(len(result), len(ring))

    def test_bundled_snapshot_has_all_boroughs_and_consistent_counts(self):
        path = Path(__file__).resolve().parents[1] / 'docs/gardens-map/map-data.json'
        data = json.loads(path.read_text())
        self.assertEqual({b['name'] for b in data['boroughs']}, set(BOROUGHS.values()))
        self.assertEqual(data['record_count'], len(data['gardens']))
        self.assertEqual(data['mapped_count'], sum(g['location'] is not None for g in data['gardens']))
        self.assertGreater(data['mapped_count'], 500)
        for garden in data['gardens']:
            if garden['location']:
                lon, lat = garden['location']
                self.assertTrue(-74.4 < lon < -73.6 and 40 < lat < 41.1)
        self.assertIn('gthc-hcne', data['sources']['boroughs'])
        self.assertIn('p78i-pat6', data['sources']['gardens'])
        for b in data['boroughs']:
            for polygon in b['geometry']['coordinates']:
                for ring in polygon:
                    self.assertGreaterEqual(len(ring), 4)
                    self.assertEqual(ring[0], ring[-1])

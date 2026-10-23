"""Offline regression tests for garden scene validation boundaries."""
from __future__ import annotations

import copy
import unittest

from garden_registry.scene_quality import check_scene, validate_oi_request
from scripts.garden_to_oi_mcp import build_request


def fixture() -> dict:
    """Return a fictional NYC-coordinate scene; not a surveyed real site."""
    return {
        "schema_version": "1.0",
        "source": {"url": "https://example.org/fictional", "record_id": "fixture-1", "coordinate_system": "EPSG:4326"},
        "anchor": {"latitude": 40.68, "longitude": -73.95, "height_m": None},
        "local_frame": {"units": "meters", "up_axis": "Y", "dimensions_m": {"width": 20, "depth": 30, "height": 5}},
        "site_footprint_verified": False,
        "features": [],
    }


class QualityTests(unittest.TestCase):
    """Verify quality gates reject fabricated or invalid spatial geometry."""

    def test_deterministic_digest_and_roundtrip(self) -> None:
        """Key ordering and JSON round trips do not affect scene identity."""
        import json
        value = fixture()
        a = check_scene(value)
        b = check_scene(json.loads(json.dumps(value, sort_keys=True)))
        self.assertEqual(a, b)
        self.assertEqual(a["feature_count"], 0)

    def test_swapped_coordinates(self) -> None:
        """Swapped axes cannot silently georeference a scene."""
        value = fixture()
        value["anchor"] = {"latitude": -73.95, "longitude": 40.68}
        with self.assertRaises(ValueError):
            check_scene(value)

    def test_missing_crs_and_scale(self) -> None:
        """Reject untyped CRS, feet-as-meters or too-large dimensions."""
        value = fixture()
        value["source"]["coordinate_system"] = "EPSG:2263"
        with self.assertRaises(ValueError):
            check_scene(value)
        value = fixture()
        value["local_frame"]["units"] = "feet"
        with self.assertRaises(ValueError):
            check_scene(value)
        value = fixture()
        value["local_frame"]["dimensions_m"]["depth"] = 200
        with self.assertRaises(ValueError):
            check_scene(value)

    def test_no_invented_garden_geometry(self) -> None:
        """A garden point alone must not become an asserted garden bed."""
        value = fixture()
        value["features"] = [{"id": "bed-1", "status": "verified", "position_m": [0, 0, 0]}]
        with self.assertRaises(ValueError):
            check_scene(value)

    def test_provenance_and_bounds(self) -> None:
        """Only attributed, bounded surveyed features can pass validation."""
        value = fixture()
        value["site_footprint_verified"] = True
        value["features"] = [{"id": "bed-1", "status": "verified",
                              "provenance": {"source_url": "https://example.org/survey",
                                             "observed_at": "2026-10-23"},
                              "position_m": [0, 0, 0]}]
        self.assertEqual(check_scene(value)["feature_count"], 1)
        missing = copy.deepcopy(value)
        missing["features"][0]["provenance"] = {}
        with self.assertRaises(ValueError):
            check_scene(missing)
        outside = copy.deepcopy(value)
        outside["features"][0]["position_m"] = [100, 0, 0]
        with self.assertRaises(ValueError):
            check_scene(outside)

    def test_oi_mcp_contract(self) -> None:
        """Bridge emits a plausible typed asset reference without server access."""
        request = build_request(
            {"gardenname": "Fictional", "lat": 40.68, "lon": -73.95},
            "11111111-1111-4111-8111-111111111111", 20, 30, 5)
        validate_oi_request(request)
        request["scene"]["instances"][0]["asset"]["kind"] = "example"
        with self.assertRaises(ValueError):
            validate_oi_request(request)


if __name__ == "__main__":
    unittest.main()

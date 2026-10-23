"""Contract tests for the garden-to-OI MCP request builder."""

import unittest

from scripts.garden_to_oi_mcp import build_request


class GardenSceneRequestTests(unittest.TestCase):
    """Verify OI scene requests reject unsupported site metadata."""

    def test_create_scene_contract(self) -> None:
        """A surveyed geometry asset produces a valid typed MCP request."""
        request = build_request(
            {"gardenname": "Test Garden", "lat": 40.68, "lon": -73.95},
            "11111111-1111-4111-8111-111111111111", 20, 30, 5
        )
        self.assertEqual(request["version"], 1)
        self.assertEqual(request["scene"]["room"]["depth"], 30)
        self.assertEqual(
            request["scene"]["instances"][0]["asset"]["kind"], "cloud"
        )
        self.assertEqual(len(request["scene"]["instances"]), 1)

    def test_bad_coordinates(self) -> None:
        """Out-of-region coordinates must fail instead of misplacing geometry."""
        with self.assertRaises(ValueError):
            build_request(
                {"gardenname": "Test", "lat": 0, "lon": 0},
                "11111111-1111-4111-8111-111111111111", 20, 20, 5
            )

    def test_bad_dimensions(self) -> None:
        """Reject sizes outside the scene API limit."""
        with self.assertRaises(ValueError):
            build_request(
                {"gardenname": "Test", "lat": 40.68, "lon": -73.95},
                "11111111-1111-4111-8111-111111111111", 200, 20, 5
            )


if __name__ == "__main__":
    unittest.main()

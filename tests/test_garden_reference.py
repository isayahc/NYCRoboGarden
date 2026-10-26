"""Guard the real-site boundary reference against unsupported physical claims."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from garden_registry.scene_adapter import build_scene, export_package, reload_package
from scripts.build_garden_reference import GARDEN_ID, ROOT, frozen_registry, reference_manifest


class GardenReferenceTests(unittest.TestCase):
    """Check source retention, no invented interiors, and deterministic replay."""

    def test_exact_municipal_polygon_and_unknown_interiors(self) -> None:
        """The real-site mesh must retain all four source corners and no features."""
        registry = frozen_registry()
        record = next(r for r in registry["records"] if r["id"] == GARDEN_ID)
        manifest = reference_manifest()
        self.assertEqual(manifest["footprint"]["geometry"]["coordinates"],
                         record["source_boundaries"][0]["geometry"]["coordinates"][0])
        scene, metadata = build_scene(manifest)
        self.assertEqual(len(scene["instances"]), 1)
        self.assertEqual(len(scene["bundledAssets"][0]["parts"][0]["indices"]), 6)
        self.assertEqual(len(metadata["unknowns"]), 9)
        self.assertTrue(metadata["height_assumed_zero"])
        self.assertIsNone(manifest["footprint"]["provenance"]["observed_at"])
        self.assertTrue(all(f["status"] == "unknown" and f["geometry"] is None
                            for f in manifest["features"]))
        self.assertEqual(manifest["footprint"]["status"], "source_backed")

    def test_committed_scene_matches_frozen_sources(self) -> None:
        """Rebuilding from the archived registry and evidence reproduces the package."""
        retained = ROOT / "data/scenes/st-nicholas-boundary"
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "reference"
            export_package(reference_manifest(), directory)
            for filename in ("garden-manifest.json", "garden.oi.json", "garden-georeference.json"):
                self.assertEqual((directory / filename).read_bytes(), (retained / filename).read_bytes())
            scene = json.loads((directory / "garden.oi.json").read_text())
            scene["instances"][0]["position"][0] += 1
            (directory / "garden.oi.json").write_text(json.dumps(scene))
            with self.assertRaisesRegex(ValueError, "does not match"):
                reload_package(directory)

    def test_unknown_rights_and_unknown_geometry_fail_closed(self) -> None:
        """Neither unknown reuse rights nor a box attached to an unknown may pass."""
        manifest = reference_manifest()
        unlicensed = copy.deepcopy(manifest)
        unlicensed["footprint"]["provenance"]["rights"]["status"] = "unknown"
        with self.assertRaisesRegex(ValueError, "documented rights"):
            build_scene(unlicensed)
        manifest["features"][0]["geometry"] = {"type": "box"}
        with self.assertRaisesRegex(ValueError, "Unknown features cannot"):
            build_scene(manifest)


if __name__ == "__main__":
    unittest.main()

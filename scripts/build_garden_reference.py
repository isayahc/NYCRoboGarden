"""Replay the reviewed St. Nicholas boundary reference through the existing adapter.

This is an explicit selection of one municipal polygon, not an automatic survey
or a general policy for promoting registry polygons to verified garden layouts.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from garden_registry.registry import build
from garden_registry.scene_adapter import export_package, local_point, prepare_manifest, write_json

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data/research/layout-audit-2026-10-26"
GARDEN_ID = "nyc-greenthumb:M394-GT001"
UNKNOWN_GEOMETRY = {
    "bed": "Current count, corner coordinates, dimensions and heights are unmeasured.",
    "growing_area": "Active growing extents and seasonal use are unmeasured.",
    "path": "Entrances, clear widths, slopes, surfaces and obstacles are unmeasured.",
    "greenhouse": "Operator reports a greenhouse; its footprint, height and interior dimensions are unmeasured.",
    "building": "Operator describes a shed/rooftop project; footprint, height and load capacity are unverified.",
    "water": "Operator describes rainwater work; current outlets, routing and readiness are unverified.",
    "power": "No measured locations or verified capacity of electrical service.",
    "crop": "No dated current crop inventory or mapped plant positions.",
    "seasonal_product": "Markets and CSA do not establish crops grown within this footprint.",
}


def read_json(path: Path) -> Any:
    """Read a UTF-8 JSON source without fetching or modifying it."""
    return json.loads(path.read_text(encoding="utf-8"))


def frozen_registry() -> dict[str, Any]:
    """Replay the full archived registry and verify its semantic snapshot hashes."""
    snapshot = read_json(SOURCES / "snapshot.json")
    registry = build(read_json(SOURCES / "source.rows.json"),
                     read_json(SOURCES / "source.metadata.json"),
                     snapshot["source"]["retrieved_at"])
    for key in ("schema_version", "snapshot_version", "source", "summary"):
        if registry[key] != snapshot[key]:
            raise ValueError(f"Frozen registry no longer matches snapshot: {key}")
    return registry


def reference_manifest() -> dict[str, Any]:
    """Preserve the reviewed polygon exactly and leave every interior unknown."""
    registry = frozen_registry()
    record = next(item for item in registry["records"] if item["id"] == GARDEN_ID)
    boundaries = record["source_boundaries"]
    if len(boundaries) != 1:
        raise ValueError("Reviewed site must have exactly one source boundary")
    geometry = boundaries[0]["geometry"]
    if geometry["type"] != "MultiPolygon" or len(geometry["coordinates"]) != 1:
        raise ValueError("Cannot discard disconnected polygon parts")
    if len(geometry["coordinates"][0]) != 1:
        raise ValueError("Cannot discard polygon holes")
    evidence = read_json(ROOT / "data/evidence/st-nicholas-miracle.json")
    manifest = prepare_manifest(registry, GARDEN_ID, evidence)
    manifest["footprint"] = {
        "status": "source_backed",
        "geometry": {"type": "Polygon", "coordinates": copy.deepcopy(geometry["coordinates"][0])},
        "provenance": {
            "source_url": record["source_url"],
            "observed_at": None,
            "confidence": "medium",
            "rights": {
                "status": "permission",
                "reference": "NYC Open Data public reuse policy: https://www.nyc.gov/opendata/get-started/FAQs ; https://cityofnewyork.github.io/opendatatsm/publicpolicies.html . Dataset licenseId remains null; no CC license asserted.",
            },
            "note": "NYC Parks mapped boundary, retrieved 2026-10-26. Geometry capture date and field accuracy unknown. Polygon vertices unchanged; one-part MultiPolygon unwrapped to Polygon. MapPLUTO 26v2 tax-lot comparison differs by about 1.7 m. Flat Y=0 and null-height zero are visualization assumptions. Not a surveyed fence, usable floor or approved robot workspace.",
        },
    }
    manifest["features"] = [
        {"id": f"{category}-unknown", "category": category, "status": "unknown",
         "geometry": None, "reason": reason}
        for category, reason in UNKNOWN_GEOMETRY.items()
    ]
    return manifest


def main() -> None:
    """Build a fresh portable scene package, optionally including real OI Tiles."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--oi-root", type=Path)
    args = parser.parse_args()
    manifest = reference_manifest()
    result = export_package(manifest, args.output, args.oi_root)
    parcel = next(f for f in read_json(SOURCES / "mappluto-candidates.geojson")["features"]
                  if str(f["properties"]["BBL"]) == "1019530044")
    geometry = parcel["geometry"]
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    write_json(args.output / "reference-overlays.json", {
        "role": "comparison_annotations_only_not_scene_features",
        "parcel_source": read_json(SOURCES / "mappluto-provenance.json"),
        "parcel_bbl": "1019530044",
        "parcel_rings_local_m": [[local_point(c[:2], manifest["anchor"]) for c in ring]
                                 for polygon in polygons for ring in polygon],
        "website_pin_local_m": local_point([-73.95172, 40.81181], manifest["anchor"]),
        "website_pin_source": "https://stnicholasmiraclegarden.org/",
        "website_pin_role": "published_pin_not_surveyed_entrance_or_control",
    })
    write_json(args.output / "reference-status.json", {
        "site": "St. Nicholas Miracle Garden",
        "record_id": GARDEN_ID,
        "scope": "municipal_boundary_reference_only",
        "field_measured_features": 0,
        "interior_features_rendered": 0,
        "boundary_capture_date": None,
        "field_accuracy_m": None,
        "operator_approval": None,
        "robot_clearance_validated": False,
        "unknown_geometry_categories": list(UNKNOWN_GEOMETRY),
        "report": "docs/garden-layout-audit.md",
    })
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

"""Offline quality gates for evidence-backed garden scene manifests.

Coordinates are WGS84 degrees, dimensions and local offsets are meters.
This validates contracts, not real-world survey accuracy or robot safety.
"""
from __future__ import annotations

import hashlib
import json
import math
import uuid
from typing import Any


def finite(value: Any) -> bool:
    """Return whether a value is a finite non-boolean real number."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def check_scene(scene: dict[str, Any]) -> dict[str, Any]:
    """Validate a garden scene manifest and return a stable content digest.

    A registry point or parcel is never proof of bed-level geometry.
    Geometry is accepted only with an explicit verified source reference.
    """
    if scene.get("schema_version") != "1.0":
        raise ValueError("Unsupported garden scene schema")
    source = scene.get("source")
    if not isinstance(source, dict) or not source.get("url") or not source.get("record_id"):
        raise ValueError("Source URL and stable record ID required")
    if source.get("coordinate_system") != "EPSG:4326":
        raise ValueError("WGS84 EPSG:4326 is required")
    anchor = scene.get("anchor")
    if not isinstance(anchor, dict):
        raise ValueError("Missing anchor")
    lat, lon = anchor.get("latitude"), anchor.get("longitude")
    if not all(map(finite, (lat, lon))) or not (40 < lat < 41.1 and -74.4 < lon < -73.6):
        raise ValueError("Invalid NYC WGS84 anchor; check longitude/latitude order")
    if anchor.get("height_m") is not None and not finite(anchor["height_m"]):
        raise ValueError("Height must be finite or unknown (null)")
    frame = scene.get("local_frame")
    if not isinstance(frame, dict) or frame.get("units") != "meters" or frame.get("up_axis") != "Y":
        raise ValueError("OI local frame must use Y-up meters")
    dimensions = frame.get("dimensions_m")
    if not isinstance(dimensions, dict) or not all(finite(dimensions.get(k)) and 1 <= dimensions[k] <= 100 for k in ("width", "depth", "height")):
        raise ValueError("OI dimensions must be 1–100 meters")
    if scene.get("site_footprint_verified") is not True and scene.get("features"):
        raise ValueError("Cannot render physical features from unverified site geometry")
    features = scene.get("features", [])
    if not isinstance(features, list):
        raise ValueError("Features must be an array")
    ids: set[str] = set()
    for feature in features:
        if not isinstance(feature, dict) or not feature.get("id") or feature["id"] in ids:
            raise ValueError("Missing or duplicate feature ID")
        ids.add(feature["id"])
        if feature.get("status") != "verified":
            raise ValueError("Scene physical features require verified status")
        provenance = feature.get("provenance", {})
        if not isinstance(provenance, dict) or not provenance.get("source_url") or not provenance.get("observed_at"):
            raise ValueError("Feature requires source URL and observation date")
        offset = feature.get("position_m")
        if not isinstance(offset, list) or len(offset) != 3 or not all(map(finite, offset)):
            raise ValueError("Feature position must be three finite meter coordinates")
        x, y, z = offset
        if not (-dimensions["width"] / 2 <= x <= dimensions["width"] / 2 and
                -dimensions["depth"] / 2 <= z <= dimensions["depth"] / 2 and
                0 <= y <= dimensions["height"]):
            raise ValueError("Feature origin outside declared local scene bounds")
    # Do not hash generated timestamps or a caller UUID; digest captures semantic input.
    stable = json.dumps(scene, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {"sha256": hashlib.sha256(stable.encode("utf-8")).hexdigest(),
            "feature_count": len(features), "record_id": source["record_id"]}


def validate_oi_request(request: dict[str, Any]) -> None:
    """Check OI MCP request fields without relying on external services."""
    if request.get("version") != 1 or not isinstance(request.get("scene"), dict):
        raise ValueError("Expected astra.create_scene version 1")
    try:
        uuid.UUID(str(request["request_id"]))
    except (ValueError, KeyError, AttributeError) as exc:
        raise ValueError("Invalid request UUID") from exc
    room = request["scene"].get("room", {})
    if not all(finite(room.get(k)) and 1 <= room[k] <= 100 for k in ("width", "depth", "height")):
        raise ValueError("OI room scale invalid")
    instances = request["scene"].get("instances")
    if not isinstance(instances, list) or not instances:
        raise ValueError("An actual cloud geometry asset is required")
    for instance in instances:
        if instance.get("asset", {}).get("kind") != "cloud":
            raise ValueError("Garden model must be a cloud geometry asset")
        try:
            uuid.UUID(instance["asset"]["version_id"])
        except (KeyError, ValueError, AttributeError) as exc:
            raise ValueError("Invalid OI asset version ID") from exc
        if instance.get("visible") is not True:
            raise ValueError("Garden geometry must be visible")

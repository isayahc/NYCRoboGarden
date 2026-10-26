"""Independently check archived NYC boundaries and the generated reference mesh.

Optional validation dependencies: requirements-layout-validation.txt.
Numerical agreement tests software conversion; it never establishes survey accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pyproj
import shapely
from pyproj import Geod, Transformer
from shapely.geometry import Point, Polygon, shape

from garden_registry.scene_adapter import local_point, reload_package, write_json
from scripts.build_garden_reference import GARDEN_ID, SOURCES, frozen_registry, read_json

SHORTLIST = {"M394-GT001", "MGT018", "B400-GT001", "B572-GT001",
             "BGT025", "BGT036", "B126-GT001"}


def project(geometry: Any) -> Any:
    """Project WGS84 geometry into metric UTM 18N for layer comparisons."""
    transformer = Transformer.from_crs(4326, 32618, always_xy=True)
    return shapely.transform(geometry, transformer.transform, interleaved=False)


def audit_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Screen all collected boundaries, retaining shortlisted diagnostics."""
    geod = Geod(ellps="WGS84")
    counts = {"gardens": len(registry["records"]), "invalid_boundaries": 0,
              "missing_locations": 0, "location_outside_all_boundaries": 0,
              "multiple_source_boundaries": 0, "multipart_or_holed_boundaries": 0}
    anomalies: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    parcels = read_json(SOURCES / "mappluto-candidates.geojson")["features"]
    for row in registry["records"]:
        polygons = [shape(b["geometry"]) for b in row["source_boundaries"]]
        flags: list[str] = []
        if len(polygons) != 1:
            flags.append("multiple_source_boundaries")
        if not polygons or any(not p.is_valid for p in polygons):
            flags.append("invalid_boundaries")
        if any(len(p.geoms) != 1 or any(len(g.interiors) for g in p.geoms) for p in polygons):
            flags.append("multipart_or_holed_boundaries")
        if row["location_geometry"] is None:
            flags.append("missing_locations")
        elif not any(p.covers(shape(row["location_geometry"])) for p in polygons):
            flags.append("location_outside_all_boundaries")
        for flag in flags:
            counts[flag] += 1
        if flags:
            anomalies.append({"id": row["id"], "name": row["name"], "flags": flags})
        if row["parks_id"] not in SHORTLIST:
            continue
        g = polygons[0]
        area = sum(abs(geod.geometry_area_perimeter(part)[0]) for part in g.geoms)
        metric = project(g)
        anchor = {"longitude": row["longitude"], "latitude": row["latitude"], "height_m": None}
        local = [local_point(c, anchor) for c in g.geoms[0].exterior.coords]
        item = {k: row[k] for k in ("id", "name", "address", "status", "bbls")}
        item.update({"area_geodesic_m2": area, "flags": flags,
                     "single_ring_adapter_compatible": len(g.geoms) == 1 and not g.geoms[0].interiors,
                     "fits_existing_anchor_100m_room": max(abs(p[i]) for p in local for i in (0, 2)) <= 50})
        matches = [p for p in parcels if str(p["properties"]["BBL"]) in row["bbls"]]
        item["parcel_comparisons"] = []
        for p in matches:
            parcel = project(shape(p["geometry"]))
            item["parcel_comparisons"].append({
                "bbl": str(p["properties"]["BBL"]), "version": p["properties"]["Version"],
                "registry_address": row["address"], "parcel_address": p["properties"]["Address"],
                "tax_lot_reported_area_sq_ft": p["properties"]["LotArea"],
                "intersection_over_union": metric.intersection(parcel).area / metric.union(parcel).area,
                "hausdorff_distance_m": metric.hausdorff_distance(parcel),
                "meaning": "layer disagreement, not measured positional error",
            })
        candidates.append(item)
    return {"summary": counts, "candidates": candidates, "anomalies": anomalies}


def verify_package(directory: Path) -> dict[str, Any]:
    """Check native mesh area, exact source vertices and PROJ frame agreement."""
    scene, sidecar = reload_package(directory)
    registry = frozen_registry()
    row = next(r for r in registry["records"] if r["id"] == GARDEN_ID)
    manifest = read_json(directory / "garden-manifest.json")
    ring = row["source_boundaries"][0]["geometry"]["coordinates"][0][0]
    assert manifest["footprint"]["geometry"]["coordinates"] == [ring]
    assert len(scene["instances"]) == 1 and len(scene["bundledAssets"]) == 1
    assert len(sidecar["unknowns"]) == 9
    anchor = manifest["anchor"]
    transformer = Transformer.from_pipeline(
        "+proj=pipeline +step +proj=cart +ellps=WGS84 "
        f"+step +proj=topocentric +ellps=WGS84 +lon_0={anchor['longitude']} "
        f"+lat_0={anchor['latitude']} +h_0=0")
    errors: list[float] = []
    points = []
    for lon, lat in ring[:-1]:
        east, north, up = transformer.transform(lon, lat, 0)
        expected = [east, up, -north]
        actual = local_point([lon, lat], anchor)
        errors.append(max(abs(a - b) for a, b in zip(actual, expected)))
        points.append((actual[0], actual[2]))
    assert max(errors) < 1e-6, "Adapter disagrees with independent PROJ topocentric conversion"
    geom = scene["bundledAssets"][0]["parts"][0]
    vertices, indices = geom["vertices"], geom["indices"]
    positions = [(vertices[i], vertices[i + 2]) for i in range(0, len(vertices), 3)]
    triangles = [Polygon([positions[j] for j in indices[i:i+3]]) for i in range(0, len(indices), 3)]
    expected_polygon = Polygon(positions)
    mesh = shapely.union_all(triangles)
    assert expected_polygon.is_valid and mesh.symmetric_difference(expected_polygon).area < 1e-8
    assert abs(sum(t.area for t in triangles) - expected_polygon.area) < 1e-8
    # Restore the adapter's one-time normalization to check actual mesh placement.
    instance_position = scene["instances"][0]["position"]
    restored = [(p[0] + instance_position[0], p[1] + instance_position[2]) for p in positions]
    assert max(math.dist(a, b) for a, b in zip(restored, points)) < 1e-8
    geod = Geod(ellps="WGS84")
    area, perimeter = geod.polygon_area_perimeter(*zip(*ring))
    assert abs(mesh.area - abs(area)) < 0.001
    edges = [geod.inv(*a, *b)[2] for a, b in zip(ring[:-1], ring[1:])]
    audit = audit_registry(registry)
    selected = next(c for c in audit["candidates"] if c["id"] == GARDEN_ID)
    website_point = Point(-73.95172, 40.81181)
    municipal = shape(row["source_boundaries"][0]["geometry"])
    return {"schema": "garden-reference-validation/1", "site": GARDEN_ID,
            "checks": "passed", "libraries": {"pyproj": pyproj.__version__, "shapely": shapely.__version__},
            "source_file_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(SOURCES.iterdir()) if p.is_file()},
            "registry_snapshot_version": registry["snapshot_version"],
            "source_vertices_unchanged": True, "mesh_instances": 1,
            "triangles": len(triangles), "unknown_categories": 9,
            "geodesic_area_m2": abs(area), "local_mesh_area_m2": mesh.area,
            "perimeter_m": perimeter, "edge_lengths_m": edges,
            "proj_max_difference_m": max(errors),
            "parks_published_area_sq_ft": 1595,
            "parks_area_difference_percent": 100 * (abs(area) / (1595 * 0.09290304) - 1),
            "operator_website_point": {"longitude": website_point.x, "latitude": website_point.y,
                "inside_municipal_boundary": municipal.covers(website_point),
                "distance_to_boundary_m": project(website_point).distance(project(municipal)),
                "source_url": "https://stnicholasmiraclegarden.org/",
                "note": "Published website pin; not a surveyed entrance or control point."},
            "parcel_comparisons": selected["parcel_comparisons"], "registry_audit": audit,
            "limits": ["No survey, operator signoff, measured interiors or robot trials.",
                       "GIS layer agreement and conversion tolerance do not establish field accuracy.",
                       "Source update timestamps are not boundary capture dates."]}


def main() -> None:
    """Validate a retained scene package and write reproducible diagnostics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify_package(args.package)
    write_json(args.output, report)
    print(json.dumps({key: report[key] for key in ("checks", "geodesic_area_m2", "triangles", "proj_max_difference_m")}))


if __name__ == "__main__":
    main()

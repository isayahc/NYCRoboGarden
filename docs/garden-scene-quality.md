# Garden scene quality gates

Run the offline regression suite from the repository root:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

`garden_registry.scene_quality.check_scene` validates a **versioned site scene manifest** for CRS declaration (WGS84 EPSG:4326), NYC coordinate limits and axis ordering, metric/Y-up frame, OI room limits, geometry containment, unique feature IDs, source attribution, and deterministic semantic digest. Empty feature lists are allowed when no survey exists; point-only garden records **cannot** assert a physical layout.

`validate_oi_request` validates the typed MCP handoff envelope and cloud asset IDs. This is offline schema-level checking only: it does not certify OI server acceptance, mesh geometry, triangle winding, collisions, farm terrain traversability, crop accuracy, or actual surveyed alignment.

The test fixture uses **fictional garden metadata** with coordinates inside NYC, not an identified active garden. The quality checks protect claims and fail closed on unverified geometry. For a real pilot, attach a licensed survey or operator-approved plan, measured bed and structure outlines, documented observation dates, and a validated elevation reference.

## Remaining gates under #9

- [ ] Add measured boundary fixture and independent survey comparison (with tolerance in meters)
- [ ] Convert lat/lon/ellipsoidal altitude into the OI local metric frame and back; compare at multiple anchors
- [ ] Validate actual OI export/import scene revisions and 3D Tiles viewer placement
- [ ] Add browser screenshot/feature picking verification across real garden geometry
- [ ] Run articulated ASTRA/SO-101 physical plausibility and clearance tests separately; UI keyframes are not physics

The parser's digest is deterministic across JSON key order but not across source-data changes; it is not an attestable signature of field truth.

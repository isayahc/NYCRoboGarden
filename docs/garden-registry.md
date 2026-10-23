# NYC garden registry

Issue [#5](https://github.com/isayahc/Spooky-Civic-AI-Hackathon/issues/5) provides the data foundation for selecting gardens in Open Industries. This module produces versioned records, source evidence and a location layer. It does not generate a 3D scene or certify a site for robot operation.

## Run

Python 3.10 or newer; standard library only. Run from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 -m garden_registry --output data/generated
```

The online command downloads the [GreenThumb registry](https://data.cityofnewyork.us/dataset/GreenThumb-Garden-Info/p78i-pat6) in pages ordered by Socrata row ID. It checks the row count and source update timestamp before and after collection and aborts on inconsistencies. Network failures propagate; rerun rather than treating an interrupted fetch as a complete snapshot. A successful run saves:

| File | Content |
| --- | --- |
| `source.rows.json` | Raw registry rows for replay |
| `source.metadata.json` | Publisher metadata, including update and license fields |
| `registry.json` | Schema version, content version, source metadata, quality counts and garden records |
| `locations.geojson` | Source location points only, with null geometry for missing locations |
| `source.parcels.geojson` and `source.parcels.metadata.json` | Copies of optional parcel inputs, when supplied |

Outputs are local and ignored by Git. Archive all these files together for long-term reproducibility. A subsequent online run may legitimately produce a different snapshot.

### Offline sample and exact replay

Two official rows and reduced publisher metadata are committed in `tests/fixtures/`. They are a sample, not the complete garden inventory. The sample was retrieved on October 23, 2026; use this command to exercise the pipeline without network access:

```bash
python3 -m garden_registry \
  --raw tests/fixtures/greenthumb.json \
  --metadata tests/fixtures/metadata.json \
  --retrieved-at 2026-10-23T17:32:14.222513+00:00 \
  --output data/generated/sample
```

For exact replay of a full run, take the original `source.retrieved_at` value from `registry.json` and supply it with that run's saved source files:

```bash
python3 -m garden_registry \
  --raw data/generated/source.rows.json \
  --metadata data/generated/source.metadata.json \
  --retrieved-at ORIGINAL_RETRIEVAL_TIMESTAMP \
  --output data/replay
```

If the original run included parcels, also pass the saved parcel GeoJSON and metadata via the flags below. With identical inputs and retrieval timestamp, the JSON outputs are deterministic. The source rows' hash preserves input order; the snapshot content version is independent of row ordering and registry retrieval time.

## Identity and schema

`Garden` is a typed dataclass in `garden_registry/registry.py`. The export's `schema_version` is `1.0.0`.

- `id`: `nyc-greenthumb:<PARKS_ID>`, using the publisher's Parks ID. Missing IDs abort ingestion rather than creating unstable IDs from names or addresses.
- `version`: SHA256 of the sorted distinct raw-row hashes for this Parks ID. It versions source evidence; parcel changes are captured by `snapshot_version`.
- `snapshot_version`: SHA256 of the schema, normalized records and publisher metadata. This includes parcel evidence when supplied.
- `latitude`, `longitude`, `location_geometry`: source location in WGS84; GeoJSON coordinates use longitude then latitude. Invalid, non-finite, swapped or clearly out-of-region points become null with a warning.
- `source_boundaries`: structurally validated source polygons, explicitly labeled `source_mapped_garden_boundary`. No boundary is synthesized from a point.
- `bbls`, `parcel_candidates`: explicit tax-lot identifiers and optional matched polygons, separate from garden boundaries.
- `source_url`, `source_row_hashes`, `source_row_count`, `conflicts`, `warnings`: traceability and review evidence.

Deduplication groups only by Parks ID. It does not merge similarly named gardens or neighboring sites. All distinct row hashes and conflicting field values are retained. The representative row is chosen deterministically: valid location first, then field completeness, then canonical JSON ordering. All distinct valid source boundaries and valid BBLs from the group are retained. Conflicts require review; the representative is not asserted to be correct.

All source statuses are retained, including inactive or non-GreenThumb entries. A registry entry is not evidence of current production, public access or participation in this project. IDs are stable while the publisher preserves Parks IDs; upstream ID replacement requires a future alias/migration policy.

## Parcel geometry

The official [MapPLUTO catalog](https://data.cityofnewyork.us/City-Government/Primary-Land-Use-Tax-Lot-Output-Map-MapPLUTO-/f888-ni5f) describes tax-lot geography. Obtain the desired release and export a relevant subset as RFC 7946 GeoJSON in WGS84 longitude/latitude. This implementation accepts an explicit local parcel snapshot; it does not automatically download the citywide MapPLUTO archive or guess a parcel from an address or nearest point.

Each feature must have a single ten-digit `properties.bbl` or `properties.BBL` and Polygon/MultiPolygon geometry. Projected coordinates and legacy `crs` declarations are rejected. Supply a separate provenance JSON file:

```json
{
  "source_url": "https://data.cityofnewyork.us/City-Government/Primary-Land-Use-Tax-Lot-Output-Map-MapPLUTO-/f888-ni5f",
  "source_version": "REPLACE_WITH_DOWNLOADED_RELEASE",
  "retrieved_at": "REPLACE_WITH_ACTUAL_ISO8601_TIMESTAMP",
  "license_status": "REPLACE_WITH_PUBLISHER_LICENSE_OR_UNSPECIFIED",
  "terms_url": "REPLACE_WITH_APPLICABLE_PUBLISHER_TERMS_URL"
}
```

```bash
python3 -m garden_registry \
  --parcels /path/to/parcels.geojson \
  --parcel-metadata /path/to/parcels.metadata.json \
  --output data/generated
```

Matching uses exact source BBLs only. Identical parcel features are deduplicated; distinct polygons for one BBL remain separate candidates. Unmatched BBLs are reported. A tax lot can be larger than a garden, cover multiple uses or reflect a different date. Every candidate has `is_verified_garden_footprint: false`. Source garden polygons also remain unverified; there is no automatic promotion to a surveyed footprint.

Geometry checks cover type, nesting, finite coordinate ranges and closed rings. They do not validate self-intersections, topological validity, point containment, survey accuracy or physical accessibility. Heights, beds, crops, irrigation, structures and robot-clearance maps require additional evidence. Missing source coordinates remain missing even if a polygon is present.

## Source metadata and refresh

The source is NYC Parks' GreenThumb Garden Info, dataset `p78i-pat6`. The publisher metadata is queried at `https://data.cityofnewyork.us/api/views/p78i-pat6.json`. Its declared refresh frequency is copied into each export; the inspected sample says monthly. Refresh is an explicit CLI run, not an automatic job.

The export records retrieval time, source update epoch, content hashes, attribution, license ID/status and a link to NYC Open Data terms. The inspected metadata has no license ID, so the pipeline records `unspecified`; it does not invent a Creative Commons license. Parcel provenance must be supplied for the chosen release. These metadata fields record evidence and do not substitute for reviewing publisher terms.

See [verification evidence](garden-registry-verification.json) for the live run's counts and hashes. Offline tests cover deterministic deduplication, conflict preservation, source-ID changes, missing and invalid coordinates, malformed boundaries, exact BBL joins, missing provenance, pagination and mid-download source changes.

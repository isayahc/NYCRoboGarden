# Garden evidence research (issue #6)

This version defines a reviewable evidence contract and imports a small primary-source research sample into the registry from #5. It does not reconstruct a garden or establish deployment suitability. Python 3.10+ and the standard library are sufficient.

## Reproduce

```bash
python3 -m garden_registry --output data/generated
python3 -m garden_registry.evidence --input data/evidence/hattie-carthan.json --registry data/generated/registry.json --output data/generated/evidence.json
python3 -m unittest discover -s tests -v
```

For exact replay, preserve the registry snapshot used as `--registry`. The evidence output includes its `snapshot_version` and a SHA-256 version of canonical evidence content. Live registry refreshes may change that version. The committed research input is the reviewed transcription, not a live scraper. No sponsor credentials or new dependencies are required. Existing CI discovers the evidence tests automatically.

Expected sample result: **1 accepted historical report, 1 unresolved site match, 8 explicit unknowns**. Accepted means source-backed and matched, not verified today or approved for robot operation. Planned records remain labelled planned. Consumers must inspect state, date, confidence and limitations.

## Version 1.0 contract

The authoritative executable contract is [`garden_registry/evidence.py`](../garden_registry/evidence.py); [`hattie-carthan.json`](../data/evidence/hattie-carthan.json) is a complete example. IDs are curator-assigned stable identifiers. Update an existing record when correcting it; keep separate records for conflicting reports or different observations. Do not silently replace historical evidence with a current assertion.

| Field | Meaning / requirement |
| --- | --- |
| `schema_version` | Exactly `1.0` |
| `sources` | Unique IDs; URL, title, publisher, publication date or null, retrieval date, rights record |
| `records[].id` | Unique stable evidence ID |
| `site_match` | `confirmed`, `ambiguous` or `unmatched`; candidate registry IDs and rationale. Only confirmed matches have `garden_id`. All IDs must exist in the supplied registry. |
| `category` | `bed`, `growing_area`, `path`, `greenhouse`, `building`, `water`, `power`, `crop`, `seasonal_product` |
| `state` | `reported`, `observed`, `planned`, `unknown`; a direct observation requires a date |
| `claim`, `value`, `unit` | Narrow paraphrase and source-stated value/unit, or null. Do not conflate additions with totals, production with market inventory, or planned with installed. |
| `observed_at`, `time_basis` | YYYY-MM-DD or null, with explanation. Event/observation date is distinct from publication and retrieval dates. Do not invent a day for month-only evidence; preserve its precision in `time_basis`. |
| `confidence` | `high`, `medium`, `low`, `unknown`, with rationale; assesses the particular claim, not general site suitability |
| `citations` | Source IDs plus page/section locator and a short supporting paraphrase. Every non-unknown claim requires at least one. |
| `layout` | Null in v1. Sources can reference plans but this importer does not accept unverified geometry. |
| `season` | Source-stated seasonal window and year in text, or null; never infer harvest dates from a generic crop calendar |
| `limitations` | List of unresolved limitations, competing reports or follow-up needs |

Unknown records require null claim/value/unit/date/season and unknown confidence. Missing evidence is not evidence of absence. An unsupported negative assertion such as “no water” must not replace an unknown. Source links alone cannot prove a claim: a reviewer must read the cited passage and confirm its scope.

Confidence rubric: **high** = specific first-party statement or dated direct observation; **medium** = identifiable but indirect or incomplete evidence; **low** = tentative or identity-limited evidence; **unknown** = no assessment. Old evidence may have high confidence as a historical report while providing no confidence about present conditions.

## Collection checklist

| Category | Capture when supported; otherwise leave unknown |
| --- | --- |
| Beds and growing areas | Count, whether added or total, dimensions and units, material, soil/container type, accessibility |
| Paths | Width and units, surface, entrance connection, steps, slope, pedestrian use |
| Greenhouses and buildings | Function, enclosure type, footprint, height, installed vs planned status |
| Water | Source, access point, irrigation type, availability, operator authorization |
| Power | Supply type, outlet/location, voltage and capacity only if explicitly documented; operator verification needed |
| Crops | Species/common name, cultivar if stated, growing area, planting/harvest observation date |
| Seasonal products | Product, season/year, whether grown here or sold here, quantity/unit only if sourced |

Use one evidence record per narrow claim, even when multiple claims cite one source. Future measured layouts must add a new schema version with coordinate system, units, scale/calibration method, observation date, accuracy, source citations and rights. Street points, parcel polygons and imagery-derived guesses are not surveyed bed geometry.

## Research sample and site identity

Reviewed on 2026-10-23:

- [GrowNYC renovation press release](https://www.grownyc.org/files/gmkt/Press/hattie_carthan_renovation_with_tracy_morgan.pdf), published 2019-03-29, page 1: reports 30 beds added at Hattie Carthan Community Garden during the previous day's renovation. The exact garden name, borough/neighborhood and GreenThumb affiliation support the registry match to `nyc-greenthumb:B400-GT001`. This does not provide dimensions, a bed map or a current inventory.
- [Herban Farm operator page](https://yonnette.wixsite.com/hcherbanfarm/about_us), “About us” and address: describes an herb farm at 49 Van Buren Street. The registry Community Garden is at 719 Marcy Avenue. Similar names are insufficient to merge these sites. The farm description stays unresolved with no assigned garden ID; resolve the farm's own registry identity before importing its evidence.

All other sample categories are explicitly unassessed. In particular, a seasonal market is not evidence that any particular product was grown at that garden. This is a seed research sample, not a citywide inventory. No aerial image, plan or photo has been downloaded, traced or redistributed.

## Imagery and plan sourcing protocol

1. Prefer operator-supplied surveys/plans and dated site photographs with documented permission, or official datasets with explicit applicable reuse terms. A publicly viewable image is not automatically reusable.
2. Record the original publisher, URL, author where known, title, capture/observation date, retrieval date, license/permission reference, attribution requirements and limits on redistribution, derivatives or automated access. Do not infer capture dates from upload dates.
3. Review the specific asset's terms before downloading, storing, tracing, transforming or redistributing it. Check provider restrictions on map tiles, screenshots, derived geometry and automated retrieval. If rights remain unclear, retain a link and paraphrased factual notes only, and seek permission before using the asset.
4. For operator permissions, retain a durable permission reference covering the intended uses. Confirm access for field photography and avoid collecting identifiable visitors or private interior details unnecessarily. Site access and robotics deployment permission are separate from image reuse permission.
5. If future versions admit assets, retain their checksum, original file, attribution and license/permission evidence alongside derived artifacts. Record measurement method and uncertainty. Have the operator review layouts before physical use.

The v1 rights object contains `status` (`unknown`, `licensed`, `permission`, `owned`), `license_url` (null only when unknown), and `asset_use` (always `link_only`). The importer rejects asset download requests regardless of status. Both sample sources have unknown reuse rights. This workflow does not grant rights or automatically establish legal clearance.

## Verification and limits

Tests cover historical dates/count units, site-match quarantine, unknowns vs false values, missing/dangling citations, invalid dates, unknown garden IDs, invented geometry, asset restrictions and deterministic versioning. Run the full suite with the command above.

Validation checks structure and references; it cannot determine if a passage is true, whether a human matched the right site, or whether a permission document is valid. No images are interpreted, no current crops/utilities are asserted, and no robot motion should be generated from these records. Resolve uncertain matches with address, operator and boundary evidence; preserve disagreements as separate cited records until reviewed.

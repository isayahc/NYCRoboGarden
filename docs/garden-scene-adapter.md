# Garden manifest → Open-Industries scene

Issue #7 is implemented by `garden_registry.scene_adapter`: a Python standard-library adapter that creates **actual indexed meshes in OI's portable `astra.scene` format**, georeferencing metadata, and optional 3D Tiles through OI's exporter. It also prepares typed MCP requests after those exact assets have been uploaded to OI.

The reproducible example is **fictional**, at illustrative Brooklyn coordinates. Its ground, bed, path and greenhouse are explicitly inferred. It demonstrates the adapter, not an as-built garden or an approved deployment location. Real-site measurements and browser end-to-end verification remain #9/#10 work.

## Generate, export and reopen

Run from this repository, with Python 3.10+:

```bash
python3 -m garden_registry.scene_adapter build data/scenes/fictional-garden.json --output data/generated/garden-demo
python3 -m garden_registry.scene_adapter reload data/generated/garden-demo
python3 -m unittest discover -s tests -v
```

Use a fresh output directory each time. `reload` regenerates from the retained manifest and checks the scene and sidecar for differences; hashes alone are not treated as proof. Outputs:

| File | Purpose |
| --- | --- |
| `garden-manifest.json` | Exact authored input, retained for deterministic regeneration |
| `garden.oi.json` | Native OI scene, with bundled geometry, stable instance/asset IDs, meter poses and per-part evidence metadata |
| `garden-georeference.json` | WGS84 anchor, local→ECEF transform, source identity, observations/confidence/rights, unknowns, limitations and content hashes |

Import `garden.oi.json` using OI's **Drop files or browse** workflow. OI's native portable export can be reopened with the same geometry, poses and evidence. Keep the sidecar with it: OI's portable format has no top-level geospatial anchor field, although the anchor is also retained in each generated part's evidence metadata. The workbench is a local meter scene; the geographic placement is applied by the Tiles exporter.

### Real Open-Industries export and verification

The integration is pinned in CI to OI commit `acfcdf7f10813639d9036ae2a00466209f32389d` (including local SQLite persistence):

```bash
git clone https://github.com/Mapped-Assembly/Open-Industries.git ../Open-Industries
git -C ../Open-Industries checkout acfcdf7f10813639d9036ae2a00466209f32389d
npm --prefix ../Open-Industries ci --ignore-scripts
python3 -m pip install 'mcp>=1.12,<2'
python3 -m garden_registry.scene_adapter build data/scenes/fictional-garden.json --output data/generated/garden-tiles --oi-root ../Open-Industries
OI_ROOT="$(realpath ../Open-Industries)" python3 -m unittest discover -s tests -p test_scene_adapter.py -v
```

Use Node 24 for the pinned OI integration. The adapter invokes OI's `tools/geospatial/export_scene.py`, producing `tiles/tileset.json`, four GLBs for this fixture, and upstream provenance/export reports. `tiles/garden-evidence.json` retains the garden-specific evidence keyed by the same instance IDs found in tile metadata. The upstream exporter deliberately allowlists fields, so consumers must join this companion file for full observations/rights/unknowns.

The optional integration tests exercise OI's **actual** `readManifest → hydrateManifest → makeManifest → readManifest → hydrateManifest` functions and the local SQLite MCP workflow described below. They reject missing-asset placeholders and check geometry, poses, metadata and provenance equality after JSON serialization. They also invoke OI's actual MCP schema validator and geospatial exporter. Without `OI_ROOT`, both integration tests are explicitly skipped; ordinary Python tests still run. CI includes a separate pinned OI job so these checks are not silently omitted there.

## Prepare a real site from #5 and #6

```bash
python3 -m garden_registry --output data/generated/registry
python3 -m garden_registry.scene_adapter prepare --registry data/generated/registry/registry.json --garden-id nyc-greenthumb:B400-GT001 --evidence data/evidence/hattie-carthan.json --output data/generated/hattie-manifest.json
```

This carries the exact registry identity, snapshot, anchor and validated evidence forward. Ambiguous matches are excluded. It intentionally writes `footprint: null` and no physical features. A source polygon or tax lot is a candidate, not automatic proof of a usable garden footprint, and historical bed counts do not supply bed locations. `build` fails clearly until an explicit, attributed footprint is supplied.

Edit the prepared manifest using the complete fictional fixture as a structural example, replacing its geometry and sources with your own reviewed inputs. Never transfer its fictional layout to a real garden as a measured layout. Source-backed measurements and explicitly inferred design choices are separate statuses; all output mesh approximations remain inferred.

## Manifest v2.0 contract

This schema is separate from `scene_quality.py`'s v1 verified-only feature gate. That existing gate and its tests remain intact; v2 supports explicitly inferred LOD0/LOD1 renderings.

| Field | Contract |
| --- | --- |
| `source` | Stable `record_id`, source `url`, `coordinate_system: EPSG:4326` |
| `anchor` | NYC longitude/latitude and WGS84 ellipsoidal `height_m`, or null for unknown height |
| `footprint` | One closed GeoJSON Polygon ring in lon/lat order; `status: source_backed` or `inferred`; provenance required |
| `features` | Unique stable IDs, category, evidence status, geometry and provenance; unknown entries instead carry a reason and null geometry |
| Feature geometry | `type: box`, `position_m: [x,y,z]`, `dimensions_m: [width,height,depth]`, `yaw_degrees`; dimensions are explicit, never inferred from names |
| Provenance | `source_url`, `observed_at` date or null, confidence, explanatory note, rights status (`owned`, `licensed`, `permission`) and reference |
| Optional evidence | The selected site's #6 records and cited sources, retained without turning claims into geometry |

Supported categories: bed, growing_area, path, greenhouse, building, water, power, crop and seasonal_product. A crop envelope is a conceptual spatial representation, not species, yield or season verification. `source_backed` describes the input evidence; generated boxes are still labeled `[INFERRED LOD1 envelope]`. Terrain is `[INFERRED LOD0 flat surface]` even when its horizontal footprint is source-backed. Unknown features are listed in the sidecar and never rendered.

Geometry with unknown reuse rights is rejected; use the #6 link-only research workflow for it. Declaring rights is a curator assertion, not automated permission verification. No images are downloaded. Do not put credentials or private source material into manifests, since the authored input is retained in the package.

## Coordinate and geometry conventions

- WGS84 geographic coordinates are converted through ECEF into a local tangent frame: **+X east, +Y up, -Z north**, meters, heading zero.
- A null ellipsoidal height uses zero **only as an explicitly flagged visualization assumption**. It is not sea-level elevation or measured terrain. Provide an independently supported ellipsoidal height for real geographic alignment.
- The footprint is flattened to local Y=0. There is no terrain elevation model or inferred topography.
- Concave rings are triangulated, preserving the supplied outline. Holes, MultiPolygons, self-intersections and degenerate polygons are rejected; they are never replaced with a bounding rectangle. Simplify excessive collinear vertices if triangulation rejects them. Maximum 500 vertices and 999 feature boxes.
- OI currently requires the generated-source discriminator `generator: form-industries`; the actual authoring adapter is recorded as `nyc-robo-garden/2.0` in every part’s evidence metadata. This compatibility value does not assert CAD or survey origin.
- Asset vertices are normalized once about their X/Z center and bottom Y. That offset is applied to instance placement once, including yaw. It is not added again by the Tiles exporter.
- Room dimensions are derived from extents around the declared anchor and must remain within OI's 1–100 m limits. Features must fit within the supplied footprint, including rotated envelope edges. Large gardens need explicit subdivision in future work; this adapter does not silently rescale them.
- Sidecar transforms are column-major local Y-up→ECEF. OI's Tiles root is ENU/Z-up→ECEF with the prescribed Y-up conversion applied to content. The tests check those conventions agree.

## Local SQLite save, restart and export

No Supabase account, credentials or `.env` is required. Use Node 24 and Python 3.11+ with `pip install 'mcp>=1.12,<2'` for MCP sending. CI verifies with MCP SDK 1.30.0; SDK 2 changes the client API.

After building `data/generated/garden-demo` above:

```bash
python3 -m garden_registry.scene_adapter import-local data/generated/garden-demo \
  --oi-root ../Open-Industries --data-dir data/generated/oi-local \
  --output data/generated/local-asset-versions.json
python3 -m garden_registry.scene_adapter mcp-request data/generated/garden-demo \
  --asset-versions data/generated/local-asset-versions.json --backend local \
  --data-dir data/generated/oi-local --oi-root ../Open-Industries --send
```

The importer validates the package, imports every bundled geometry asset through OI's CLI, and records its immutable local version. Reimports deduplicate in OI; use a new bindings output filename. `--send` selects the backend explicitly and resolves the data directory to an absolute path. Use the same data directory for import, MCP and export. The default request backend remains `cloud` for existing callers.

The result supplies `scene_id` and `revision_id`. To export that saved revision, substitute those returned values:

```bash
ASTRA_SCENE_DATA_DIR="$(realpath data/generated/oi-local)" \
  node --import ../Open-Industries/node_modules/tsx/dist/loader.mjs \
  ../Open-Industries/cli/local-scenes.ts export SCENE_UUID \
  data/generated/garden-saved.scene.json REVISION_NUMBER
```

Open `garden-saved.scene.json` in the workbench via **Drop files or browse**. Keep the original `garden-georeference.json` beside the export. Local `oi-local://` identifiers are MCP identifiers, not browser URLs; browser cloud-save controls are not connected to SQLite.

The integration test imports actual generated geometry, saves through MCP, stops the server, reads from a fresh server, checks idempotent retry, exports the persisted revision, and hydrates it with OI's native scene code. Geometry, poses and evidence are compared against the original package.

## Authenticated MCP handoff

Portable scene generation and Tiles export require no account. Cloud persistence uses the existing local OI MCP server and [its setup instructions](oi-mcp-garden-scenes.md).

Import the portable scene in OI, upload its generated assets using the workbench, then discover and inspect their ready immutable versions via `astra.list_scene_assets` / `astra.inspect_scene_asset`. Create a local JSON object mapping **every `assets[].id` from `garden.oi.json`** to the UUID of its matching uploaded cloud version. The adapter validates the mapping and UUID syntax; OI verifies readiness and account ownership. The operator must confirm each version represents the matching geometry.

```bash
python3 -m garden_registry.scene_adapter mcp-request data/generated/garden-demo --asset-versions data/generated/asset-versions.json
# Python 3.11+ and pip install 'mcp>=1.12,<2' are required only for --send:
python3 -m garden_registry.scene_adapter mcp-request data/generated/garden-demo --asset-versions data/generated/asset-versions.json --send --oi-root ../Open-Industries
```

This submits the actual scene poses and inferred labels, without pretending generated assets were surveyed. The deterministic request UUID supports identical retries; changed scene content/bindings produce a new ID. This is a create operation, not an update to an existing scene. Keep `garden-georeference.json` with the returned revision reference because MCP does not accept arbitrary geospatial metadata. Authenticated cloud save and browser viewing are not claimed by the local integration test.

## Verification evidence and boundaries

See [garden-scene-adapter-verification.json](garden-scene-adapter-verification.json) for the pinned revision, fixture hash and recorded results. The suite covers axes/scale at two anchors, concave triangulation, unknown rights, missing geometry, malformed values, full-envelope bounds, deterministic artifacts, tamper rejection, registry/evidence matching and MCP bindings. The OI integration validates native scene roundtrip, actual Tiles export and the actual MCP request schema.

The fixture has four rendered instances and one non-rendered unknown water feature. It establishes software interoperability, not real-site accuracy. Browser rendering/picking in two renderers, surveyed pilot comparison, cloud authentication and robotic stability remain separate verification work in #8–#10.

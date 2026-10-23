# Garden → Open-Industries MCP scene handoff

This bridge calls **the real** local `astra.create_scene` MCP tool. It requires a ready OI cloud asset with garden geometry. Public GreenThumb coordinates locate a garden but **do not** reconstruct its beds, plants, paths, structures, or terrain.

## Prerequisites

1. Clone [Mapped-Assembly/Open-Industries](https://github.com/Mapped-Assembly/Open-Industries), run `npm ci`, configure Supabase migrations and local CLI login, and enable `ASTRA_SCENE_TOOLS_ENABLED=true` as documented in [OI MCP scenes](https://github.com/Mapped-Assembly/Open-Industries/blob/main/docs/mcp-scenes.md).
2. Import your surveyed garden model into OI, upload its geometry to private cloud Storage, then call `astra.list_scene_assets` to obtain a **ready** `version_id`.
3. Create `garden.json` with `gardenname`, `lat`, and `lon` from a GreenThumb record. For example `{"gardenname":"Sample garden","lat":40.68,"lon":-73.95}` (illustrative, not a verified garden).
4. `python -m pip install mcp` (Python 3.11+).

## Preview the MCP request

```bash
python scripts/garden_to_oi_mcp.py garden.json --asset-version-id YOUR-READY-ASSET-UUID --width-m 20 --depth-m 20
```

## Generate/save the scene through OI MCP

```bash
python scripts/garden_to_oi_mcp.py garden.json --asset-version-id YOUR-READY-ASSET-UUID --width-m 20 --depth-m 20 --oi-root /path/to/Open-Industries --send
```

Width, depth and height must be measured or otherwise evidenced (OI permits 1–100 m). Replace the example widths with surveyed dimensions and ensure imported geometry uses OI's Y-up meter coordinate system. The `lat`/`lon` fields are validated NYC coordinates for provenance; **MCP's typed scene contract has no georeferencing field**, so the scene itself is not automatically positioned on the earth. For external georeferencing, use the OI [3D Tiles exporter](https://github.com/Mapped-Assembly/Open-Industries/tree/main/tools/geospatial) with a separately verified WGS84 anchor and ellipsoidal height.

The returned revision URL is owner-scoped and requires login. Do not put credentials in garden files. An auth, configuration, or asset error is reported rather than fabricated success.

## Remaining integration

- Add a map-selection download or API handoff for the record.
- Supply measured/photogrammetric garden geometry assets and metadata.
- Embed the signed-in OI viewer and propagate asset source, uncertainty, and exact WGS84 anchor.
- Test the full workflow against a local OI MCP and validated garden model.

Tracking: [#7](https://github.com/isayahc/Spooky-Civic-AI-Hackathon/issues/7), [#8](https://github.com/isayahc/Spooky-Civic-AI-Hackathon/issues/8).

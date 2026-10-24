# Author spaces with OpenCode + Open-Industries MCP

OpenCode writes the garden manifest and calls OI's scene tools. The Python adapter
validates geometry/provenance and imports assets; OI MCP persists the scene in its
local SQLite backend. Export the saved revision and open it in the OI workbench.
This is the space-authoring step toward #10, not the completed recorded pilot.

## Setup (WSL2/Linux)

Use Node 24 and Python 3.11+. Keep Open-Industries beside this repository:

```bash
git clone https://github.com/Mapped-Assembly/Open-Industries.git ../Open-Industries
npm --prefix ../Open-Industries ci --ignore-scripts
npm install -g opencode-ai
python -m pip install 'mcp>=1.12,<2'
python -m scripts.author_space configure --oi-root ../Open-Industries
export OPENCODE_CONFIG="$PWD/data/generated/authoring/opencode.json"
opencode mcp list
opencode
```

`configure` writes absolute machine-local paths into ignored generated files. It
sets `ASTRA_SCENE_BACKEND=local`, enables OI's scene tools and uses the same data
directory for asset import, MCP and export. It does not replace a user's existing
project config, select a model, or write provider credentials. Select/authenticate
your preferred model in OpenCode if one is not already configured. Local scene
storage requires no Supabase account; the OpenCode model may require its own login.

In OpenCode:

```text
/author-space Create a conceptual garden with tomato, lettuce and carrot beds, a wide inspection aisle, a greenhouse and a robot staging area. Keep all invented geometry marked inferred.
```

The command reads the v2 schema, authors a manifest, prepares/imports assets,
inspects them through MCP, calls `astra.create_scene`, reads the saved revision,
and exports it. Each run uses a fresh output directory. It must report tool errors
instead of fabricating saved IDs. Additional edits to an existing OI scene can use
`astra.read_scene` followed by `astra.update_scene` with the returned base revision;
use a fresh request UUID and handle revision conflicts before retrying.

A ready-to-open example is committed as
[`robo-garden-concept.scene.json`](../data/scenes/robo-garden-concept.scene.json),
with its [georeference/evidence sidecar](../data/scenes/robo-garden-concept-georeference.json).
It was saved through actual OI MCP and exported from revision 1. The sample was
prepared by Codex and published by the deterministic replay; it was not generated
by an OpenCode model.

## Replay the committed concept without a model

The sample contains three named crop-bed envelopes, a path, greenhouse, robot
staging area, and ground. These are original box/envelope concepts, not detailed
crop meshes, a surveyed Brooklyn garden, or the MuJoCo robot assembly.

```bash
python -m scripts.author_space prepare data/scenes/robo-garden-concept.json \
  --output data/generated/my-garden
python -m scripts.author_space publish data/generated/my-garden
python -m scripts.author_space export data/generated/my-garden
```

`publish` calls the real `astra.create_scene` MCP tool using the same arguments
OpenCode would submit; it is a deterministic replay, not an OpenCode model run.
It derives the request from the validated package and immutable asset bindings.
Repeating it without changes is idempotent. `export` requires the actual saved
receipt and refuses to overwrite an existing export.

Open `data/generated/my-garden/authored.scene.json` with **Drop files or browse**
in the OI workbench. Keep `garden-georeference.json` with it. An `oi-local://`
identifier is not a public browser link. This does not automatically load the
space into the existing MuJoCo farm server.

## Evidence and verification

The illustrative anchor is not a real pilot selection. Layouts remain `inferred`,
observation dates unknown, and water availability explicitly unknown. To author
against a real garden, first use the registry/evidence `prepare` workflow in
[garden-scene-adapter.md](garden-scene-adapter.md), then add attributed measured or
explicitly proposed geometry; never relabel a conceptual layout as an as-built site.

Run unit checks and the actual OI import/save/read/export integration:

```bash
python -m unittest discover -s tests -p test_author_space.py -v
OI_ROOT="$(realpath ../Open-Industries)" python -m unittest discover -s tests -p test_author_space.py -v
```

OpenCode MCP and command configuration follow the official docs:
- https://opencode.ai/docs/mcp-servers/
- https://opencode.ai/docs/commands/

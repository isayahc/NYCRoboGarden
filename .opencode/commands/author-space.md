---
description: Author a conceptual garden space and persist it through Open-Industries MCP
agent: build
---
Author a garden space for this request: $ARGUMENTS

Read docs/opencode-authoring.md, docs/garden-scene-adapter.md and
 data/scenes/robo-garden-concept.json before making changes.

1. Write a new version 2.0 garden manifest under data/scenes with a descriptive
   filename. Reuse the schema, not an unrelated site's factual identity. Keep
   source-backed records separate from proposed geometry. Use inferred status,
   explicit dimensions, original conceptual geometry and unknown observation dates
   for invented layouts. Do not assert measured boundaries or current crops for a
   real garden. Preserve any supplied citations and unresolved site facts.
2. Run `python -m scripts.author_space prepare <manifest> --output <fresh-directory>`.
   Fix validation errors; do not bypass bounds, source or rights validation.
3. Read create-scene.arguments.json from that directory. Use the configured `oi`
   MCP server's astra.inspect_scene_asset on each referenced local asset and then
   astra.create_scene with those exact arguments. Never invent asset UUIDs or scene
   IDs. If a tool reports an error, report the error rather than success.
4. Save the actual create result object as scene-receipt.json in the output
   directory. Call astra.read_scene for that scene_id and revision_id and verify
   the saved instances and poses match the request.
5. Run `python -m scripts.author_space export <directory>`. Report the portable
   authored.scene.json file, actual scene/revision IDs, and conceptual limitations.

Use a new output directory for each authored variant. Keep the existing robot
mission intact. This command authors OI spaces; it does not connect them to MuJoCo,
control hardware, prove reachability, or finish issue #10's browser recording.

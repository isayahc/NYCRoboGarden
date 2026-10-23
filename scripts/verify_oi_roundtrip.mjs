/** Verify a generated package with the actual OI portable-scene implementation.
 * Run from an npm-installed OI checkout: node --import tsx /path/to/this.mjs PACKAGE.
 */
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const { readManifest, hydrateManifest, makeManifest } = await import(pathToFileURL(resolve('src/lib/workspace.ts')).href);
const directory = resolve(process.argv[2]);
const original = JSON.parse(readFileSync(resolve(directory, 'garden.oi.json'), 'utf8'));
const metadata = JSON.parse(readFileSync(resolve(directory, 'garden-georeference.json'), 'utf8'));
const imported = hydrateManifest(readManifest(original), []);
assert.ok(imported.items.every(item => !item.missing), 'No missing geometry placeholders');
const exported = JSON.parse(JSON.stringify(makeManifest(imported, true)));
const reopened = hydrateManifest(readManifest(JSON.parse(JSON.stringify(exported))), []);
assert.deepEqual(exported, original, 'Portable export preserves geometry, poses and metadata');
assert.deepEqual(reopened, imported, 'Native OI reopen preserves the workspace');
for (const item of reopened.items) {
  const evidence = JSON.parse(item.asset.parts[0].metadata.gardenEvidence);
  assert.equal(evidence.instance_id, item.id);
  assert.deepEqual(evidence, metadata.features.find(feature => feature.instance_id === item.id));
  assert.ok(item.name.startsWith('[INFERRED '));
}
console.log(JSON.stringify({ oiNativeRoundtrip: 'passed', instances: reopened.items.length, provenance: 'preserved' }));

const requestPath = resolve(directory, 'mcp-request.json');
if (existsSync(requestPath)) {
  const { validateSceneRequest } = await import(pathToFileURL(resolve('server/mcp-scene-contract.mjs')).href);
  validateSceneRequest('astra.create_scene', JSON.parse(readFileSync(requestPath, 'utf8')));
  console.log(JSON.stringify({ upstreamMcpSchema: 'passed', cloudSave: 'not-attempted' }));
}

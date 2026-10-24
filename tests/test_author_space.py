"""Check OpenCode configuration and the real local OI authoring path."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.author_space import configure, export_saved, prepare
from garden_registry.scene_adapter import build_scene, write_json
from scripts.garden_to_oi_mcp import send_request

ROOT = Path(__file__).resolve().parents[1]


class AuthorSpaceTests(unittest.TestCase):
    """Check setup failure and the concept's generated geometry."""

    def test_missing_checkout(self) -> None:
        """Configuration must reject a path without the real OI server."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                configure(root, root / 'db', root / 'settings.json')
            self.assertFalse((root / 'settings.json').exists())

    def test_concept(self) -> None:
        """The committed conceptual beds build with retained unknown water evidence."""
        scene, sidecar = build_scene(json.loads((ROOT / 'data/scenes/robo-garden-concept.json').read_text()))
        self.assertEqual(len(scene['instances']), 7)
        self.assertEqual(len(sidecar['unknowns']), 1)
        self.assertEqual(sidecar['source']['record_id'], 'concept:robo-garden')

    @unittest.skipUnless(os.environ.get('OI_ROOT'), 'Set OI_ROOT for real MCP integration')
    def test_real_mcp_authoring(self) -> None:
        """Import, save twice idempotently, restart/read and export through actual OI."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oi = Path(os.environ['OI_ROOT']).resolve()
            settings = configure(oi, root / 'database', root / 'config/settings.json')
            config = json.loads(Path(settings['opencode_config']).read_text())
            env = config['mcp']['oi']['environment']
            output = root / 'space'
            prepare(ROOT / 'data/scenes/robo-garden-concept.json', output, settings)
            request = json.loads((output / 'create-scene.arguments.json').read_text())
            receipt = asyncio.run(send_request(request, oi / 'server/astra-mcp.mjs', oi, env))
            self.assertIn('scene_id', receipt)
            retry = asyncio.run(send_request(request, oi / 'server/astra-mcp.mjs', oi, env))
            self.assertEqual(receipt, retry)

            async def read_saved() -> dict:
                """Reconnect using a fresh MCP server process and read the saved revision."""
                params = StdioServerParameters(command='node', args=[str(oi / 'server/astra-mcp.mjs')], env={**os.environ, **env})
                async with stdio_client(params) as (reader, writer):
                    async with ClientSession(reader, writer) as session:
                        await session.initialize()
                        result = await session.call_tool('astra.read_scene', {'version': 1, 'scene_id': receipt['scene_id'], 'revision_id': receipt['revision_id']})
                        self.assertFalse(result.isError)
                        return dict(result.structuredContent or {})

            saved = asyncio.run(read_saved())
            self.assertEqual(saved['scene']['instances'], request['scene']['instances'])
            write_json(output / 'scene-receipt.json', receipt)
            result = export_saved(output, settings)
            portable = json.loads(Path(result['export']).read_text())
            self.assertEqual(len(portable['instances']), 7)
            with self.assertRaises(subprocess.CalledProcessError):
                export_saved(output, settings)


if __name__ == '__main__':
    unittest.main()

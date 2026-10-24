"""Prepare garden spaces for OpenCode and persist them through real OI MCP."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from garden_registry.scene_adapter import (
    build_mcp_request, export_package, import_local_assets, write_json,
)
from scripts.garden_to_oi_mcp import send_request

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / 'data/generated/authoring/settings.json'


def configure(oi_root: Path, data_dir: Path, settings: Path = SETTINGS) -> dict[str, Any]:
    """Write machine-local OpenCode config without changing the user's existing config."""
    oi_root, data_dir = oi_root.resolve(), data_dir.resolve()
    for required in ('server/astra-mcp.mjs', 'node_modules/tsx/package.json'):
        if not (oi_root / required).is_file():
            raise ValueError(f'Missing {required} in OI checkout; run npm ci there first')
    settings.parent.mkdir(parents=True, exist_ok=True)
    config_path = settings.with_name('opencode.json')
    config = {'$schema': 'https://opencode.ai/config.json', 'mcp': {'oi': {
        'type': 'local', 'command': ['node', str(oi_root / 'server/astra-mcp.mjs')],
        'enabled': True, 'timeout': 30000,
        'environment': {'ASTRA_ROOT': str(oi_root), 'ASTRA_SCENE_TOOLS_ENABLED': 'true',
                        'ASTRA_SCENE_BACKEND': 'local', 'ASTRA_SCENE_DATA_DIR': str(data_dir)},
    }}}
    write_json(config_path, config)
    result = {'oi_root': str(oi_root), 'data_dir': str(data_dir), 'opencode_config': str(config_path)}
    write_json(settings, result)
    return result


def prepare(manifest: Path, output: Path, settings: dict[str, Any]) -> dict[str, Any]:
    """Validate authored geometry, import immutable assets and emit exact MCP arguments."""
    result = export_package(json.loads(manifest.read_text()), output)
    versions = import_local_assets(output, Path(settings['oi_root']), Path(settings['data_dir']))
    write_json(output / 'asset-versions.json', versions)
    request = build_mcp_request(output, versions, 'local')
    request['agent'] = 'opencode-garden-author'
    write_json(output / 'create-scene.arguments.json', request)
    return {**result, 'arguments': str(output / 'create-scene.arguments.json')}


def export_saved(output: Path, settings: dict[str, Any]) -> dict[str, Any]:
    """Export an MCP-created immutable revision to a portable OI workbench file."""
    receipt = json.loads((output / 'scene-receipt.json').read_text())
    if 'scene_id' not in receipt or 'revision_id' not in receipt:
        raise ValueError('Receipt must contain actual scene_id and revision_id from OI MCP')
    root = Path(settings['oi_root'])
    destination = output.resolve() / 'authored.scene.json'
    subprocess.run(['node', '--import', 'tsx', 'cli/local-scenes.ts', 'export',
                    receipt['scene_id'], str(destination), str(receipt['revision_id'])],
                   cwd=root, env={**os.environ, 'ASTRA_SCENE_DATA_DIR': settings['data_dir']},
                   check=True, capture_output=True, text=True)
    return {'scene_id': receipt['scene_id'], 'revision_id': receipt['revision_id'],
            'export': str(destination)}


def main() -> None:
    """Configure OpenCode, prepare assets, or replay the exact authoring request."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    setup = commands.add_parser('configure')
    setup.add_argument('--oi-root', type=Path, required=True)
    setup.add_argument('--data-dir', type=Path, default=ROOT / 'data/generated/oi-local')
    prep = commands.add_parser('prepare')
    prep.add_argument('manifest', type=Path)
    prep.add_argument('--output', type=Path, required=True)
    for name in ('publish', 'export'):
        child = commands.add_parser(name)
        child.add_argument('directory', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'configure':
            result = configure(args.oi_root, args.data_dir)
        else:
            settings = json.loads(SETTINGS.read_text())
            if args.command == 'prepare':
                result = prepare(args.manifest, args.output, settings)
            elif args.command == 'publish':
                # Revalidate retained geometry and derive bindings, not arbitrary stored arguments.
                request = build_mcp_request(args.directory, json.loads((args.directory / 'asset-versions.json').read_text()), 'local')
                request['agent'] = 'opencode-garden-author'
                root = Path(settings['oi_root'])
                result = asyncio.run(send_request(request, root / 'server/astra-mcp.mjs', root,
                    {'ASTRA_SCENE_BACKEND': 'local', 'ASTRA_SCENE_DATA_DIR': settings['data_dir']}))
                if 'scene_id' not in result or 'revision_id' not in result:
                    raise ValueError(f'OI did not persist a scene: {result}')
                write_json(args.directory / 'scene-receipt.json', result)
            else:
                result = export_saved(args.directory, settings)
    except (ValueError, OSError, KeyError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Space authoring failed: {exc}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

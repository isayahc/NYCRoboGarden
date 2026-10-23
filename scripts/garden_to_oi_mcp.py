#!/usr/bin/env python3
"""Create an Open-Industries MCP scene from an evidence-backed garden handoff.

Requires an authenticated local Open-Industries MCP service and an existing
cloud asset that represents surveyed garden geometry. Garden coordinates alone
cannot reconstruct an as-built 3D garden.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any


def build_request(
    garden: dict[str, Any],
    asset_version_id: str,
    width_m: float,
    depth_m: float,
    height_m: float,
) -> dict[str, Any]:
    """Construct a typed astra.create_scene request for known site geometry."""
    uuid.UUID(asset_version_id)
    if not all(1.0 <= n <= 100.0 for n in (width_m, depth_m, height_m)):
        raise ValueError("OI room dimensions must each be 1–100 meters.")
    name = str(garden.get("gardenname") or garden.get("name") or "").strip()
    if not name:
        raise ValueError("Garden name is required.")
    latitude = float(garden["lat"])
    longitude = float(garden["lon"])
    if not (40.0 < latitude < 41.1 and -74.4 < longitude < -73.6):
        raise ValueError("Coordinates are outside the NYC bounding box.")
    return {
        "version": 1,
        "request_id": str(uuid.uuid4()),
        "agent": "nyc-robo-garden",
        "scene": {
            "name": f"Garden | {name[:100]}",
            "room": {"width": width_m, "depth": depth_m, "height": height_m},
            "instances": [
                {
                    "id": "garden-surveyed-geometry",
                    "name": "Surveyed site geometry (cloud asset)",
                    "asset": {"kind": "cloud", "version_id": asset_version_id},
                    "position": [0, 0, 0],
                    "rotation": [0, 0, 0],
                    "visible": True,
                }
            ],
        },
    }


async def send_request(
    request: dict[str, Any], server_path: Path, root: Path,
    environment: dict[str, str] | None = None
) -> dict[str, Any]:
    """Invoke the local OI MCP stdio tool with the Python MCP SDK."""
    try:
        from mcp import ClientSession, StdioServerParameters  # type: ignore[import-not-found]
        from mcp.client.stdio import stdio_client  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("Install the MCP client SDK: pip install 'mcp>=1.12,<2'") from exc
    env = dict(os.environ)
    env.update(environment or {})
    env["ASTRA_ROOT"] = str(root.resolve())
    env["ASTRA_SCENE_TOOLS_ENABLED"] = "true"
    server = StdioServerParameters(
        command="node", args=[str(server_path.resolve())], env=env
    )
    async with stdio_client(server) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            result = await session.call_tool("astra.create_scene", request)
            if result.isError:
                raise RuntimeError(f"OI MCP rejected the scene: {result.content}")
            return dict(result.structuredContent or {})


def main() -> None:
    """Validate garden handoff and either print or submit an MCP scene request."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("garden", type=Path, help="Downloaded selected-garden JSON")
    parser.add_argument("--asset-version-id", required=True, help="Ready OI cloud asset UUID")
    parser.add_argument("--width-m", required=True, type=float, help="Surveyed scene width (m)")
    parser.add_argument("--depth-m", required=True, type=float, help="Surveyed scene depth (m)")
    parser.add_argument("--height-m", default=5.0, type=float, help="Scene height (m)")
    parser.add_argument("--send", action="store_true", help="Call local OI MCP")
    parser.add_argument("--oi-root", type=Path, help="Local Open-Industries checkout")
    args = parser.parse_args()
    garden = json.loads(args.garden.read_text(encoding="utf-8"))
    if not isinstance(garden, dict):
        parser.error("Garden handoff must be a JSON object")
    request = build_request(
        garden, args.asset_version_id, args.width_m, args.depth_m, args.height_m
    )
    if not args.send:
        print(json.dumps({"tool": "astra.create_scene", "arguments": request}, indent=2))
        return
    if args.oi_root is None:
        parser.error("--oi-root is required with --send")
    server_path = args.oi_root / "server" / "astra-mcp.mjs"
    if not server_path.is_file():
        parser.error(f"MCP server not found: {server_path}")
    result = asyncio.run(send_request(request, server_path, args.oi_root))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

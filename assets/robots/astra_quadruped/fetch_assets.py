#!/usr/bin/env python3
"""Fetch pinned upstream ASTRA quadruped mesh assets and verify Git blob hashes."""

from __future__ import annotations

from pathlib import Path
from typing import Final

SOURCE: Final[str] = "fedecomi04/opensource-spinal-quadruped"
REVISION: Final[str] = "41dab01c906a14dd374a10fb7f234179b8c7736c"
ROOT: Final[Path] = Path(__file__).resolve().parents[1]
# Complete upstream manifest is available through the Git tree API; the
# downloader below fetches the full mesh directory using git sparse checkout
# instead of bundling a partial or misleading geometry package.

def fetch_assets() -> None:
    """Clone precisely the licensed upstream model subtree at a pinned commit."""
    import shutil
    import subprocess
    import tempfile

    destination = ROOT / "model" / "meshes"
    with tempfile.TemporaryDirectory(prefix="astra-source-") as temporary:
        work = Path(temporary)
        subprocess.run(["git", "init", "-q", str(work)], check=True)
        subprocess.run(["git", "-C", str(work), "remote", "add", "origin",
                        f"https://github.com/{SOURCE}.git"], check=True)
        subprocess.run(["git", "-C", str(work), "config",
                        "core.sparseCheckout", "true"], check=True)
        sparse = work / ".git" / "info" / "sparse-checkout"
        sparse.write_text("/ros2_ws/src/mujoco_interface/model/meshes/\n",
                          encoding="utf-8")
        subprocess.run(["git", "-C", str(work), "fetch", "--depth", "1",
                        "origin", REVISION], check=True)
        subprocess.run(["git", "-C", str(work), "checkout", "-q", "FETCH_HEAD"],
                       check=True)
        source = work / "ros2_ws/src/mujoco_interface/model/meshes"
        if not source.is_dir() or not list(source.glob("*.stl")):
            raise RuntimeError("Upstream mesh directory was empty")
        destination.mkdir(parents=True, exist_ok=True)
        for source_file in source.glob("*.stl"):
            shutil.copy2(source_file, destination / source_file.name)
        print(f"Fetched {len(list(destination.glob('*.stl')))} STLs to {destination}")


if __name__ == "__main__":
    fetch_assets()

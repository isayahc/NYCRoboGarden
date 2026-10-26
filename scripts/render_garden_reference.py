"""Render an exact source-layer comparison for the research report (matplotlib)."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from garden_registry.scene_adapter import local_point
from scripts.build_garden_reference import ROOT, read_json


def render(output: Path) -> None:
    """Plot municipal geometry with equal scales and explicit evidence limits."""
    package = ROOT / "data/scenes/st-nicholas-boundary"
    manifest = read_json(package / "garden-manifest.json")
    overlays = read_json(package / "reference-overlays.json")
    verification = read_json(ROOT / "docs/garden-layout-validation.json")
    local = [local_point(c, manifest["anchor"]) for c in manifest["footprint"]["geometry"]["coordinates"][0]]
    points = [(p[0], -p[2]) for p in local]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig = plt.figure(figsize=(12, 8), facecolor="#f5f6ee")
    ax = fig.add_axes((.08, .18, .53, .64), facecolor="#f5f6ee")
    ax.add_patch(Polygon(points, closed=True, facecolor="#c6d8ab", edgecolor="#305f40", linewidth=2.2,
                         label="GreenThumb garden boundary"))
    for ring in overlays["parcel_rings_local_m"]:
        xy = [(p[0], -p[2]) for p in ring]
        ax.plot(*zip(*xy), linestyle=(0, (4, 3)), linewidth=1.8, color="#a16b32", label="MapPLUTO 26v2 tax lot")
    for i, (east, north) in enumerate(points[:-1]):
        ax.scatter(east, north, color="#305f40", s=22, zorder=4)
        ax.annotate(chr(65 + i), (east, north), xytext=(-11, 9), textcoords="offset points", weight="bold", color="#244a32")
        nxt = points[i + 1]
        ax.annotate(f"{verification['edge_lengths_m'][i]:.2f} m", ((east+nxt[0])/2, (north+nxt[1])/2),
                    xytext=(9, 0), textcoords="offset points", fontsize=9,
                    bbox={"facecolor":"#f5f6ee", "edgecolor":"none", "alpha":.85, "pad":2})
    ax.scatter(0, 0, marker="+", color="#31577a", s=70, label="Registry anchor")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-18, 18); ax.set_ylim(-19, 19)
    ax.set_xticks(range(-15, 20, 5)); ax.set_yticks(range(-15, 20, 5))
    ax.grid(alpha=.18); ax.set_axisbelow(True)
    ax.set_xlabel("East of registry anchor (m)"); ax.set_ylabel("North of registry anchor (m)")
    for spine in ax.spines.values(): spine.set_color("#b8c3b1")
    ax.annotate("N", (13, 15), (13, 10), ha="center", fontsize=12, weight="bold",
                arrowprops={"arrowstyle":"-|>", "color":"#305f40"})
    ax.legend(loc="lower left", fontsize=8, framealpha=.95)
    fig.text(.08,.93,"NYC ROBO GARDEN / REAL-SITE REFERENCE",fontsize=10,color="#527156",weight="bold")
    fig.text(.08,.875,"St. Nicholas Miracle Garden",fontsize=25,color="#213c2b",weight="bold")
    fig.text(.65,.76,f"{verification['geodesic_area_m2']:.2f} m²",fontsize=31,color="#213c2b")
    fig.text(.65,.71,"Calculated municipal footprint",fontsize=12,color="#527156")
    fig.text(.65,.66,"4 source corners preserved\n0 measured interior features\n9 unknown geometry categories",fontsize=13,color="#213c2b",linespacing=1.8,va="top")
    fig.text(.65,.43,"1.72 m layer disagreement",fontsize=14,color="#8b5b2b",weight="bold")
    fig.text(.65,.36,"Tax lot and garden outline differ.\nNeither is a field survey.",fontsize=11,color="#4d5f50",linespacing=1.6)
    fig.text(.65,.22,"Beds, greenhouse position, paths\nand utilities await measurements.\nFlat rendering; elevation unknown.",fontsize=11,color="#4d5f50",linespacing=1.6)
    fig.text(.08,.08,"NYC Parks GreenThumb p78i-pat6 · NYC DCP MapPLUTO 26v2 · retrieved October 26, 2026",fontsize=9,color="#527156")
    fig.text(.08,.045,"Distances are calculated from GIS coordinates. Source capture date, field accuracy and operator approval are unknown.",fontsize=9,color="#527156")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    """Write a standalone PNG or vector figure from retained JSON geometry."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/media/st-nicholas-boundary.png")
    render(parser.parse_args().output)


if __name__ == "__main__":
    main()

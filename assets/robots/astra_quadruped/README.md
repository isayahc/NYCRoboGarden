# ASTRA open-source quadruped (simulation asset)

Upstream: [fedecomi04/opensource-spinal-quadruped](https://github.com/fedecomi04/opensource-spinal-quadruped)
Pinned upstream commit: `41dab01c906a14dd374a10fb7f234179b8c7736c`

This directory contains two original MuJoCo XML descriptions and the upstream MIT LICENSE. **The full mesh geometry is downloaded reproducibly**, rather than checked into this PR, because several upstream STL files exceed the GitHub connector's binary-transfer limit. Do not attempt to simulate the complete robot until the meshes have been retrieved.

## Fetch exact model geometry (WSL2 / Linux)

```bash
python3 assets/robots/astra_quadruped/fetch_assets.py
```

This populates `assets/robots/astra_quadruped/model/meshes/` with upstream STL files, preserving paths used in the MuJoCo model XML. The script needs git and network access. The source commit is pinned to make builds repeatable.

The complete upstream CAD STEP file is available at [cad/ASTRA_quadruped.step](https://github.com/fedecomi04/opensource-spinal-quadruped/blob/main/cad/ASTRA_quadruped.step) but is **not vendored** here.

## Intended composition with SO-101

- Load ASTRA's articulated chassis and four legs in a MuJoCo-capable runtime.
- Use the existing `assets/robots/so101/` robot model for the separate manipulator.
- Introduce a **new, explicitly modeled mounting frame** to position the SO-101 on ASTRA.
- Validate payload mass, torque, stability and reach before describing this combination as physically feasible.
- Use Open-Industries for visual layout and motion planning; OI scene keyframes are not a validated contact-physics solver.

**Site assumptions:** Dirt, uneven paths, slopes and garden edges should become testing scenarios. Upstream incline demonstrations are not proof of mud, waterproofing, dust resistance or outdoor carrying capacity.

## License / provenance

Root upstream repository license is MIT (included as `LICENSE`). Verify any separately licensed third-party components before packaging a combined redistributable simulator. Upstream model and mesh files are preserved in their source formats. No SO-101 mount, combined URDF/MJCF or physics validation is provided in this PR.

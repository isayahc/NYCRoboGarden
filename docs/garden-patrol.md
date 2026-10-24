# Mounted arm garden patrol

[Watch the 36-second demonstration](media/garden-patrol.mp4).

This standalone MuJoCo visual demo assembles the repository's actual ASTRA quadruped mesh hierarchy and SO-101 arm URDF, adds a mounting plate to the front chassis, and animates a repeating route around three fictional raised beds. A close-up inset in the video shows the assembly at its native meter scale.

## Run on WSL2 / Linux

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-simulation.txt
python simulation/garden_patrol.py
```

The interactive viewer requires a display (WSLg works). Drag to orbit and scroll to zoom. Close the viewer to exit. To export without a desktop:

```bash
MUJOCO_GL=egl python simulation/garden_patrol.py --video data/generated/garden-patrol.mp4
python -m unittest discover -s tests -p test_garden_patrol.py -v
```

EGL rendering requires working OpenGL/EGL drivers. Video output defaults to a complete 36-second loop at 30 fps; use `--seconds` and `--fps` to change it. The committed video is 12 fps; its 640×360 render is upscaled to 1280×720 for readable titles. No credentials or hardware connection are required.

## Assembly and motion

- ASTRA's original XML hierarchy and 21 pinned upstream STL meshes are preserved.
- `arm_mount` is a fixed child of `frontbase`, at local `(0, 0.10, 0.39)` meters. The mounting plate and support are illustrative geometry.
- The arm is built from the existing URDF's full parent/child joint chain, fixed-axis RPY transforms, visual origins and joint limits. Its joints remain at zero during transit.
- The route is a smooth closed ellipse around three beds. Two-link leg poses alternate diagonal pairs; the base pose is prescribed.
- The integration test samples 181 positions across one loop, checks the invariant mount transform, finite state, arm joint limits, route closure, and separation of every robot geometry bounding sphere from the beds.

## Scope

This is **kinematic playback**, implemented with `mj_forward`, not a balance controller or contact-dynamics simulation. Foot slip and ground contact are not validated. The supplied arm has five DOF and no moving gripper jaw. The model does not establish payload capacity, mount strength, torque margins or outdoor suitability. It sends no commands to a real robot.

This is a standalone demo in the garden project; it is not yet connected to the Open-Industries runtime, the NYC map, or a surveyed garden. Bed locations are fictional. Existing OI scene generation remains available separately.

## Asset repairs and provenance

The ASTRA downloader previously resolved its destination one directory too high. That path is fixed. The 21 fetched STL files are now committed so this demo runs after dependency installation without an additional model download. Source revision: `41dab01c906a14dd374a10fb7f234179b8c7736c` of `fedecomi04/opensource-spinal-quadruped`; MIT license is retained beside the model.

The empty `lower_arm_link_collision.stl` is restored byte-for-byte from `viam-devrel/so-101` commit `859e510f44af6d34b767423363462120fada193c`, path `assets/urdf/meshes/lower_arm_link_collision.stl`. Other arm files remain unchanged. Existing Apache-2.0 attribution is retained.

# Mounted arm garden patrol

[Watch the 36-second demonstration — Simulation](media/garden-patrol.mp4).

The README now pairs this third-person view with a [simulated robot POV](../README.md#near-future-goal-autonomous-garden-patrol). The POV comes from an illustrative chassis-mounted virtual camera, not physical hardware. See [media provenance and reproduction](media/README.md) and the [research and physical-validation plan](embodied-ai-research.md). The autonomous patrol workflow is a near-future goal; the implemented behavior below remains kinematic simulation.

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

## Server-driven harvesting mission

From the repository root, after installing `requirements-simulation.txt`:

```bash
python -m simulation.server
```

Open http://127.0.0.1:8080 in a WebGL-capable browser. Three.js renders the actual
compiled robot meshes and garden geometry locally; the server performs only
kinematics and pose updates. The server does not require EGL or an OpenGL context.
The dashboard shows task progress, the collection-box count, measured render FPS
and incoming pose-update rate. **Follow action** moves the camera in for harvesting;
**Farm overview** pulls out. Drag to orbit, scroll to zoom and right-drag to pan.
Manually orbiting turns off automatic following.

Geometry is fetched once, using compact binary mesh buffers.
Browser-only copies of CAD meshes are simplified with targets of 800–4,000 triangles
per mesh (topology and shape preservation can prevent reaching the exact target;
fewer than 100,000 triangles total, down from about 580,000);
the authoritative MuJoCo geometry and arm kinematics are unchanged. Server-sent events
deliver 30 Hz world poses; the browser interpolates position and quaternion with
a 100 ms buffer and renders with `requestAnimationFrame`. Browser refresh rate,
GPU and scene complexity determine actual FPS. Three.js 0.169.0 and OrbitControls
are vendored with their MIT license, so there is no runtime CDN dependency.
Stationary geometry is batched by material. If rendering stays below 25 FPS,
the browser reduces internal render resolution, down to 50%; the current scale
is displayed alongside FPS. Software WebGL renderers such as SwiftShader can
remain slow even with reduced geometry; use hardware-accelerated WebGL for smooth playback.

A shared, continuously repeating mission begins when the backend starts. The dog
approaches beds 3, 2 and 1 in order, collecting a carrot, lettuce and tomato.
Each 12-second stop visibly reaches, closes the fingers, lifts the vegetable,
carries it over the mounted collection box, releases it and retracts the arm.
The base and legs hold their pose during each stop. After 72 seconds it reaches home
and immediately starts the next cycle. Refreshing or opening multiple browsers does not reset
progress. The dashboard shows the current cycle; Ctrl-C stops the server.

`GET /api/status` provides the phase, active bed, carried item, deposited items,
collection-box count, completed tasks, cycle number,
within-cycle elapsed time, total elapsed time and `looping: true`.
`GET /api/scene` returns geometry metadata, `/assets/mesh/<id>.bin` supplies mesh
buffers, `/api/state` returns a pose snapshot, and `/api/events` continuously streams
poses and status over SSE. `/frame.jpg` has been removed: no JPEG polling or encoding
is used by this dashboard. Simulated harvesting results are
written to `data/generated/farm-mission/mission.json` after each harvest. This file is
reset at the start of each cycle; each result includes its cycle number.
Use `--fps 30` to set pose-update rate, `--output PATH`, `--port 8081`, or `--host 0.0.0.0`
to change the output directory, port, or expose the read-only demo on your LAN.

`simulation/harvest_mission.py` solves position-only IK for the actual mounted arm
and clips all five arm joints to their URDF limits. Visible finger joints open and
close. One harvestable vegetable at each bed edge is represented by a mocap body:
it stays on the bed until pickup, follows the tool during carry, then interpolates
into a box slot and remains there during transit. Produce resets each cycle.

Attachment, release and locomotion are scripted kinematics, not validated grasp,
contact, load-bearing or crop-health physics. The server has no sensor observations
or Viam hardware execution. It runs independently of Open-Industries. The previous
interactive patrol and video export commands remain available unchanged.

Validation: `python -m unittest discover -s tests -p test_farm_mission.py -v`.
Harvest geometry checks: `python -m unittest discover -s tests -p test_harvest_mission.py -v`.
Browser scene/stream checks: `python -m unittest discover -s tests -p test_browser_scene.py -v`.

### Sample crops

Bed 1 contains tomato plants with red fruit, bed 2 contains green lettuce rosettes,
and bed 3 contains carrots with orange shoulders and leafy tops. Each bed has eight
stylized plants built from local MuJoCo geometry; no asset downloads are needed.
The dashboard, status API and saved harvest results identify the crop by name.
The eight background plants remain static; the additional harvestable vegetable
at each bed edge moves into the collection box. Growth and crop health are not modeled.

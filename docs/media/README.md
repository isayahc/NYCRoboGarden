# Demonstration media and provenance

All motion footage here is **Simulation**. The README reserves a **Physical Hardware** slot marked **Pending physical validation**; no real seed-placement recording is included. Sponsor marks elsewhere in the README are attribution logos, not robotics evidence.

## Assets

| Asset | Source and transformation | Duration / dimensions | File size |
| --- | --- | --- | --- |
| [Seed station GIF](seed-station-simulation.gif) | Exact October 24 session `so101_seed_station.gif`, recovered from conversation files and matched byte-for-byte to the session render output; optimized without changing the sequence | 44 s; 480×300; 6 fps average | 2,334,150 bytes (2.23 MiB) |
| [Patrol video](garden-patrol.mp4) | Existing repository asset, unchanged | 36 s; 1280×720; 12 fps | 630,365 bytes (0.60 MiB) |
| [Patrol GIF](garden-patrol.gif) | Preview derived from the existing patrol video | 36 s; 480×270; 6 fps average | 875,460 bytes (0.83 MiB) |
| [Robot POV video](garden-patrol-pov.mp4) | New rendering of the existing model and route through the exporter below | 36 s; 640×360; 12 fps | 523,315 bytes (0.50 MiB) |
| [Robot POV GIF](garden-patrol-pov.gif) | Preview derived from that POV video | 36 s; 480×270; 6 fps average | 2,737,501 bytes (2.61 MiB) |

GIF previews loop and use a 96-color palette with Bayer dithering. Durations are unchanged; GIF timing alternates centisecond intervals to approximate 6 fps. All GIF frames were decoded, and sample frames were visually inspected. MP4 uses H.264/yuv420p. GitHub renders the repository-relative GIF images inline; linked MP4 files provide a separate video/download view without relying on unsupported inline HTML video. Tables use ordinary GitHub-supported HTML, with captions outside the imagery and no light-background CSS. GitHub may scroll a wide table on a narrow screen; each image links to its standalone asset/video.

## October 24 seed station

The recovered original is 11,323,357 bytes, 768×480, 440 frames / 44 seconds. SHA-256: `1da1ee7168cde36c4b26b3c7f918d13181ef32f2bc7f556339c5826c8b928ad1`. This is the requested workstation animation: SO-101, seed dishes, colored planting compartments, six pick-and-place cycles and a gripper close-up. It is not an unrelated garden animation.

The source session's `render_station.py` describes a photo-inspired, illustrative station with joint-limited kinematics and timeline-controlled seed attachment/release. The source uses SO-101 URDF and STL models from [TheRobotStudio/SO-ARM100, commit fda892cba81032c46c40976a48c9ceadbf40a9ca](https://github.com/TheRobotStudio/SO-ARM100/tree/fda892cba81032c46c40976a48c9ceadbf40a9ca/Simulation/SO101). Upstream [Apache-2.0 license](../../assets/robots/so101/LICENSE-SO-ARM100) is retained in the repository. Rendered colors and workstation geometry are illustrative. Source photos do not make the resulting animation physical footage.

The separate session's renderer/source bundle is not part of this repository; this PR imports its exact animation as an optimized derivative. Re-encoding below requires that original GIF. The local original and conversation copy were both accessible during preparation; no requested simulation media is missing.

## Reproduce the patrol POV

From the repository root, with the existing simulation dependencies and a working EGL/OpenGL driver:

```bash
pip install -r requirements-simulation.txt
MUJOCO_GL=egl python -m scripts.render_patrol_pov
```

[Exporter source](../../scripts/render_patrol_pov.py) calls the unchanged `build_model()` and `pose()` in [garden_patrol.py](../../simulation/garden_patrol.py). It uses a fixed camera offset `(-0.10, 0.28, 0.36)` meters in the `frontbase` frame, with forward direction proportional to `(-0.85, 1.0, -0.18)` and 75° vertical field of view. The chassis transform carries that camera around the same 36-second route. This front-left view approximates a possible garden-facing sensor location; no physical camera intrinsics, extrinsics, lens distortion or sensor noise have been calibrated. Both renderer eyes share the same pose for a monoscopic view. No crops are detected or classified by this exporter.

The POV is newly rendered from the simulation, not a crop of the third-person video and not generated physical footage. Robot mesh attribution remains in the [SO-101](../../assets/robots/so101/README.md) and [ASTRA](../../assets/robots/astra_quadruped/README.md) asset documentation.

## Optimize previews

With FFmpeg installed, substitute an input GIF or MP4 and an output GIF path:

```bash
ffmpeg -i INPUT -filter_complex \
  '[0:v]fps=6,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3' \
  -loop 0 OUTPUT.gif
```

Used pairs: original `so101_seed_station.gif` → `seed-station-simulation.gif`; `garden-patrol.mp4` → `garden-patrol.gif`; `garden-patrol-pov.mp4` → `garden-patrol-pov.gif`. Encoding/library versions can affect bytes; inspect captions and the entire sequence after regeneration.

## Replace the physical-hardware placeholder

When a real SO-101 recording is available, add a repository asset and replace only the right media cell of the README's seed-placement table. Keep the **Physical Hardware** label and record capture date, arm/tool configuration, seed/tray type, operating mode (teleoperation, scripted or autonomous), trial count and failures/interventions. Link the complete trial evidence and evaluation results. Remove **Pending physical validation** only for the specific capability supported by those trials; station success does not validate garden patrol. See the [validation plan](../embodied-ai-research.md#physical-validation-plan).

## Committed media manifest

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `garden-patrol-pov.gif` | 2737501 | `5c8946cfb2c602d8c0a619b53186e43eec3247d641a70de18b83c689b5f99fee` |
| `garden-patrol-pov.mp4` | 523315 | `1a9bb91c6e96ca74a8e24b5059ee7411fb916b77a6ee26aa19017475df953c81` |
| `garden-patrol.gif` | 875460 | `16827fcf093e227891086bf626f8a74b34167de046f0c6c4cba066b937e10793` |
| `garden-patrol.mp4` | 630365 | `7d509ea968375db82fc04a0e4e2eaef5c85d2e69141fd968109787eefa665a84` |
| `seed-station-simulation.gif` | 2334150 | `9a7abeedc4cba6519ba4f13ed14c00cf6e1fd55941b24ea1bd4e7eae7461b6d5` |

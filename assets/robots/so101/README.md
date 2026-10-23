# SO-101 robot assets

This folder contains the **SO-101 articulated robot arm** used in the Spooky Civic AI Hackathon Viam track.

## Contents

- `urdf/so101.urdf` — robot kinematic/joint description.
- `urdf/meshes/*_collision.stl` — five collision meshes referenced by the URDF.
- `visual/*.glb` — six per-link visual meshes from Viam's SO-101 module, including an optional end-effector reference frame.
- `LICENSE-SO-ARM100` — upstream Apache-2.0 license text for the source URDF and collision models.

## Provenance

Copied without geometric modification from [viam-devrel/so-101](https://github.com/viam-devrel/so-101) (`main`, 2026-10-23):

- [URDF and collision STL files](https://github.com/viam-devrel/so-101/tree/main/assets/urdf)
- [GLB visual link meshes](https://github.com/viam-devrel/so-101/tree/main/internal/geometry/meshes/so101)
- [Viam module repository and licensing](https://github.com/viam-devrel/so-101)

The source URDF notes that its geometry is derived from TheRobotStudio/SO-ARM100. Retain applicable upstream attribution and verify the module's licensing when redistributing or transforming the visualization GLBs.

## Integration notes

**These are separate articulated link meshes, not one pre-assembled static GLB.** To visualize and animate the complete robot in Open-Industries, resolve each visual mesh to its corresponding robot joint/link transform from the arm's kinematic model. Preserve mesh-local coordinates and meter units; validate the assembled home pose and joint limits with the physical arm before motion planning.

The URDF uses relative paths to the STL files under `urdf/meshes/`; keep that directory structure. The STL files are collision geometry and will not necessarily match the detailed GLB appearance.

No robot connection credentials or live machine configuration are included.

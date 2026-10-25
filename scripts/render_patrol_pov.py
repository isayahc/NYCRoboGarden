"""Render a chassis-mounted virtual camera on the existing kinematic patrol.

Run from the repository root: MUJOCO_GL=egl python -m scripts.render_patrol_pov
This adds no hardware camera, perception, navigation, or robot controller.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw

from simulation.garden_patrol import PERIOD, build_model, pose


def camera_frame(data):
    """Fixed illustrative front-left sensor pose, in chassis coordinates."""
    body = data.body('frontbase')
    rotation = body.xmat.reshape(3, 3)
    position = body.xpos + rotation @ np.array([-.10, .28, .36])
    forward = rotation @ np.array([-.85, 1., -.18])
    forward /= np.linalg.norm(forward)
    up = rotation @ np.array([0., 0., 1.])
    up -= np.dot(up, forward) * forward
    up /= np.linalg.norm(up)
    return position, forward, up


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('docs/media/garden-patrol-pov.mp4'))
    parser.add_argument('--seconds', type=float, default=PERIOD)
    parser.add_argument('--fps', type=int, default=12)
    args = parser.parse_args()
    if args.seconds <= 0 or args.fps <= 0:
        parser.error('seconds and fps must be positive')
    model = build_model()
    model.vis.global_.fovy = 75
    data = mujoco.MjData(model)
    camera = mujoco.MjvCamera()
    camera.distance = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with mujoco.Renderer(model, height=360, width=640) as renderer:
        with imageio.get_writer(args.output, fps=args.fps, codec='libx264',
                                pixelformat='yuv420p', macro_block_size=1) as writer:
            for frame in range(round(args.seconds * args.fps)):
                pose(model, data, frame / args.fps)
                renderer.update_scene(data, camera=camera)
                position, forward, up = camera_frame(data)
                for eye in renderer.scene.camera:
                    eye.pos[:] = position
                    eye.forward[:] = forward
                    eye.up[:] = up
                image = Image.fromarray(renderer.render())
                draw = ImageDraw.Draw(image)
                draw.rectangle((0, 0, 640, 38), fill='#10251f')
                draw.text((12, 7), 'SIMULATION | Robot POV | Virtual front-left camera', fill='white')
                draw.text((12, 22), 'Scripted patrol / fictional beds / no physical sensor capture', fill='#bdebd4')
                writer.append_data(np.asarray(image))


if __name__ == '__main__':
    main()

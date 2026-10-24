"""Kinematic ASTRA + SO-101 garden patrol; no hardware commands or dynamics claims."""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BEDS = (-1.0, 0.0, 1.0)
PERIOD = 36.0


def quaternion(rpy: str) -> str:
    """Convert URDF fixed-axis roll/pitch/yaw to MuJoCo wxyz quaternion."""
    r, p, y = (float(v) / 2 for v in rpy.split())
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return ' '.join(map(str, (cr*cp*cy+sr*sp*sy, sr*cp*cy-cr*sp*sy, cr*sp*cy+sr*cp*sy, cr*cp*sy-sr*sp*cy)))


def build_model() -> mujoco.MjModel:
    """Attach the URDF arm hierarchy rigidly to ASTRA's front chassis."""
    source = ROOT / 'assets/robots/astra_quadruped/model'
    xml = ET.parse(source / 'model.xml').getroot()
    for mesh in xml.findall('./asset/mesh'):
        path = source / mesh.attrib['file']
        if not path.is_file():
            raise FileNotFoundError(f'{path}: run python assets/robots/astra_quadruped/fetch_assets.py')
        mesh.set('file', str(path))
    for name in ('sensor', 'actuator', 'equality'):
        for element in xml.findall(name):
            xml.remove(element)
    # Playback calls mj_forward only; these contact parameters are not a controller.
    for geom in xml.iter('geom'):
        geom.set('rgba', '0.23 0.27 0.29 1')
    world = xml.find('worldbody')
    assert world is not None
    for light in world.findall('light'):
        light.set('castshadow', 'false')
        light.set('ambient', '.35 .35 .35')
    ground = world.find("body[@name='ground']/geom")
    assert ground is not None
    ground.set('size', '4 3 0.1')
    ground.set('rgba', '0.34 0.38 0.25 1')
    ET.SubElement(xml, 'visual')
    ET.SubElement(xml.find('visual'), 'global', offwidth='1280', offheight='720')
    for i, x in enumerate(BEDS):
        ET.SubElement(world, 'geom', name=f'bed_{i}', type='box', pos=f'{x} 0 0.12', size='0.32 0.65 0.12', rgba='0.38 0.23 0.13 1')
        ET.SubElement(world, 'geom', type='box', pos=f'{x} 0 0.245', size='0.28 0.61 0.015', rgba='0.15 0.10 0.065 1')
        for y in (-.45, -.15, .15, .45):
            for dx in (-.14, .14):
                ET.SubElement(world, 'geom', type='ellipsoid', pos=f'{x+dx} {y} .30', size='.075 .075 .08', rgba='.22 .48 .12 1')
    chassis = world.find("body[@name='frontbase']")
    assert chassis is not None
    mount = ET.SubElement(chassis, 'body', name='arm_mount', pos='0 0.10 0.39')
    ET.SubElement(mount, 'geom', name='mount_plate', type='box', pos='0 0 -.015', size='.075 .07 .015', rgba='.8 .6 .2 1')
    ET.SubElement(chassis, 'geom', type='box', pos='0 .10 .345', size='.025 .025 .03', rgba='.8 .6 .2 1')
    urdf_dir = ROOT / 'assets/robots/so101/urdf'
    urdf = ET.parse(urdf_dir / 'so101.urdf').getroot()
    bodies: dict[str, ET.Element] = {'base': ET.SubElement(mount, 'body', name='arm_base')}
    pending = list(urdf.findall('joint'))
    while pending:
        progressed = False
        for joint in pending[:]:
            parent = joint.find('parent').attrib['link']
            if parent not in bodies:
                continue
            child = joint.find('child').attrib['link']
            origin = joint.find('origin')
            body = ET.SubElement(bodies[parent], 'body', name=f'arm_{child}', pos=origin.attrib.get('xyz', '0 0 0'), quat=quaternion(origin.attrib.get('rpy', '0 0 0')))
            bodies[child] = body
            if joint.attrib['type'] != 'fixed':
                limit = joint.find('limit')
                ET.SubElement(body, 'joint', name=f"arm_{joint.attrib['name']}", type='hinge', axis=joint.find('axis').attrib['xyz'], range=f"{limit.attrib['lower']} {limit.attrib['upper']}", limited='true')
                ET.SubElement(body, 'inertial', mass='.01', pos='0 0 0', diaginertia='.00001 .00001 .00001')
            pending.remove(joint)
            progressed = True
        if not progressed:
            raise ValueError('Disconnected URDF joint hierarchy')
    for link in urdf.findall('link'):
        visual = link.find('visual')
        if visual is None:
            continue
        name = link.attrib['name']
        meshpath = urdf_dir / visual.find('geometry/mesh').attrib['filename']
        if not meshpath.is_file() or meshpath.stat().st_size < 84:
            raise ValueError(f'Missing or empty mesh: {meshpath}')
        ET.SubElement(xml.find('asset'), 'mesh', name=f'arm_mesh_{name}', file=str(meshpath))
        origin = visual.find('origin')
        ET.SubElement(bodies[name], 'geom', type='mesh', mesh=f'arm_mesh_{name}', pos=origin.attrib['xyz'], quat=quaternion(origin.attrib.get('rpy', '0 0 0')), rgba='.95 .67 .12 1')
    ET.SubElement(bodies['tool'], 'site', name='arm_tcp', size='.012', rgba='1 .2 .1 1')
    return mujoco.MjModel.from_xml_string(ET.tostring(xml, encoding='unicode'))


def route(t: float) -> tuple[float, float, float]:
    """Return a smooth closed elliptical patrol in meters and heading radians."""
    a = 2 * math.pi * (t % PERIOD) / PERIOD
    return 2.25 * math.cos(a), 1.55 * math.sin(a), math.atan2(-2.25*math.sin(a), 1.55*math.cos(a))


def pose(model: mujoco.MjModel, data: mujoco.MjData, t: float) -> None:
    """Set deterministic base and two-link leg poses, keeping the arm attached."""
    mujoco.mj_resetData(model, data)
    x, y, heading = route(t)
    # ASTRA faces local +Y; a Z rotation maps +Y to the path tangent.
    yaw = -heading
    data.qpos[:7] = (x, y, -.026, math.cos(yaw/2), 0, 0, math.sin(yaw/2))
    for leg, offset in (('FR', 0), ('RL', 0), ('FL', math.pi), ('RR', math.pi)):
        phase = 2*math.pi*t*1.25 + offset
        forward = .035 * math.cos(phase)
        down = .24 - .035 * max(0, math.sin(phase))
        length = math.hypot(forward, down)
        a, b = .14, .126
        knee = math.pi - math.acos(np.clip((a*a+b*b-length*length)/(2*a*b), -1, 1))
        hip = math.atan2(forward, down) - math.acos(np.clip((a*a+length*length-b*b)/(2*a*length), -1, 1))
        sign = -1 if leg.endswith('L') else 1
        for name, value in (('femur', hip), ('tibia', knee)):
            data.qpos[model.joint(f'{leg}_j_{name}').qposadr[0]] = value * sign
    data.time = t
    mujoco.mj_forward(model, data)


def main() -> None:
    """Open interactive playback or export an MP4 using EGL on headless Linux."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path)
    parser.add_argument('--seconds', type=float, default=PERIOD)
    parser.add_argument('--fps', type=int, default=30)
    args = parser.parse_args()
    if args.seconds <= 0 or args.fps <= 0:
        parser.error('seconds and fps must be positive')
    model = build_model()
    data = mujoco.MjData(model)
    camera = mujoco.MjvCamera()
    camera.lookat[:] = (0, 0, .15)
    camera.distance, camera.azimuth, camera.elevation = 6.5, 135, -40
    if args.video:
        import imageio.v2 as imageio
        from PIL import Image, ImageDraw
        args.video.parent.mkdir(parents=True, exist_ok=True)
        with mujoco.Renderer(model, height=360, width=640) as renderer, imageio.get_writer(str(args.video), fps=args.fps) as writer:
            for frame in range(round(args.seconds*args.fps)):
                pose(model, data, frame/args.fps)
                renderer.update_scene(data, camera)
                image = Image.fromarray(renderer.render()).resize((1280, 720))
                close = mujoco.MjvCamera()
                close.lookat[:] = data.xpos[model.body('arm_mount').id]
                close.distance, close.azimuth, close.elevation = 1.35, 135, -25
                renderer.update_scene(data, close)
                inset = Image.fromarray(renderer.render()).resize((400, 225))
                image.paste(inset, (860, 70))
                draw = ImageDraw.Draw(image)
                draw.rectangle((0, 0, 1280, 54), fill='#19251e')
                draw.text((24, 12), 'NYC ROBO GARDEN | ASTRA + SO-101 | Kinematic patrol / fictional beds', fill='white', font_size=22)
                writer.append_data(np.asarray(image))
                if frame % (args.fps * 6) == 0:
                    print(f'Rendered {frame/args.fps:.0f}/{args.seconds:g} seconds', flush=True)
        print(args.video.resolve())
    else:
        from mujoco import viewer as mjviewer
        with mjviewer.launch_passive(model, data) as viewer:
            viewer.cam.lookat[:] = camera.lookat
            viewer.cam.distance, viewer.cam.azimuth, viewer.cam.elevation = camera.distance, camera.azimuth, camera.elevation
            start = time.monotonic()
            while viewer.is_running():
                pose(model, data, time.monotonic()-start)
                viewer.sync()
                time.sleep(1/60)


if __name__ == '__main__':
    main()

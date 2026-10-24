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
CROPS = ("Tomatoes", "Lettuce", "Carrots")


def quaternion(rpy: str) -> str:
    """Convert URDF fixed-axis roll/pitch/yaw to MuJoCo wxyz quaternion."""
    r, p, y = (float(v) / 2 for v in rpy.split())
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return ' '.join(map(str, (cr*cp*cy+sr*sp*sy, sr*cp*cy-cr*sp*sy, cr*sp*cy+sr*cp*sy, cr*cp*sy-sr*sp*cy)))


def add_crop(world: ET.Element, bed: int, plant: int, x: float, y: float) -> None:
    """Build a stylized tomato, lettuce or carrot plant from native geometry."""
    body = ET.SubElement(world, 'body', name=f'crop_{bed}_{plant}', pos=f'{x} {y} .26')
    if bed == 0:
        ET.SubElement(body, 'geom', type='capsule', fromto='0 0 0 0 0 .32', size='.009', rgba='.18 .36 .08 1')
        for z, direction in ((.12, -1), (.23, 1)):
            ET.SubElement(body, 'geom', type='ellipsoid', pos=f'{direction*.055} 0 {z}', size='.065 .025 .018', rgba='.15 .44 .08 1')
            ET.SubElement(body, 'geom', type='sphere', pos=f'{-direction*.045} .025 {z}', size='.035', rgba='.88 .08 .025 1')
    elif bed == 1:
        for leaf in range(6):
            angle = leaf * math.pi / 3
            ET.SubElement(body, 'geom', type='ellipsoid', pos=f'{.035*math.cos(angle)} {.035*math.sin(angle)} .045', size='.055 .045 .035', rgba='.34 .65 .12 1')
        ET.SubElement(body, 'geom', type='ellipsoid', pos='0 0 .07', size='.042 .042 .045', rgba='.56 .78 .22 1')
    else:
        # Orange shoulders at the soil surface with narrow leafy tops.
        ET.SubElement(body, 'geom', type='ellipsoid', pos='0 0 .005', size='.028 .028 .025', rgba='1 .36 .025 1')
        for leaf in range(5):
            angle = leaf * 2 * math.pi / 5
            ET.SubElement(body, 'geom', type='capsule', fromto=f'0 0 .02 {.045*math.cos(angle)} {.045*math.sin(angle)} .16', size='.008', rgba='.19 .53 .06 1')


def build_model(harvest: bool = False) -> mujoco.MjModel:
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
        for row, y in enumerate((-.45, -.15, .15, .45)):
            for column, dx in enumerate((-.14, .14)):
                add_crop(world, i, row * 2 + column, x + dx, y)
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
    if harvest:
        # Visual pick/place props are opt-in so the original patrol is unchanged.
        bodies['tool'].find("site[@name='arm_tcp']").set('pos', '0 0 .055')
        for name, sign in (('left', -1), ('right', 1)):
            finger = ET.SubElement(bodies['tool'], 'body', name=f'arm_finger_{name}', pos=f'{sign*.012} 0 .025')
            ET.SubElement(finger, 'joint', name=f'arm_finger_{name}', type='slide', axis=f'{sign} 0 0', range='0 .035', limited='true')
            ET.SubElement(finger, 'geom', type='box', size='.007 .014 .035', rgba='.15 .18 .2 1', mass='.005')
        crate = ET.SubElement(chassis, 'body', name='collection_box', pos='.20 -.06 .34')
        ET.SubElement(crate, 'geom', type='box', size='.12 .10 .012', rgba='.65 .40 .17 1')
        for x, y, sx, sy in ((-.12, 0, .008, .10), (.12, 0, .008, .10), (0, -.10, .12, .008), (0, .10, .12, .008)):
            ET.SubElement(crate, 'geom', type='box', pos=f'{x} {y} .045', size=f'{sx} {sy} .045', rgba='.88 .65 .30 1')
        ET.SubElement(crate, 'site', name='box_drop', pos='0 0 .14', size='.005', rgba='0 0 0 0')
        for bed, x in enumerate(BEDS):
            item = ET.SubElement(world, 'body', name=f'harvest_item_{bed}', mocap='true', pos=f'{x} .55 .32')
            if bed == 0:
                ET.SubElement(item, 'geom', type='sphere', size='.035', rgba='.95 .06 .025 1')
                ET.SubElement(item, 'geom', type='capsule', fromto='0 0 .025 0 0 .055', size='.005', rgba='.1 .4 .05 1')
            elif bed == 1:
                for leaf in range(5):
                    angle = leaf * 2 * math.pi / 5
                    ET.SubElement(item, 'geom', type='ellipsoid', pos=f'{.018*math.cos(angle)} {.018*math.sin(angle)} 0', size='.027 .023 .026', rgba='.45 .85 .12 1')
            else:
                ET.SubElement(item, 'geom', type='ellipsoid', size='.023 .023 .055', rgba='1 .36 .015 1')
                for dx in (-.015, .015):
                    ET.SubElement(item, 'geom', type='capsule', fromto=f'0 0 .04 {dx} 0 .09', size='.006', rgba='.15 .65 .04 1')
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

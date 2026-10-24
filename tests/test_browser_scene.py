"""Browser geometry and streamed state must match the authoritative MuJoCo scene."""
import json
import struct
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError

try:
    import mujoco
    import numpy as np
    from simulation.browser_scene import BrowserScene
    from simulation.garden_patrol import build_model
    from simulation.harvest_mission import HarvestMission
    from simulation.server import MissionRuntime, handler_for
except ImportError:
    mujoco = None


@unittest.skipIf(mujoco is None, 'Install requirements-simulation.txt')
class BrowserSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = build_model(harvest=True)
        cls.data = mujoco.MjData(cls.model)
        cls.mission = HarvestMission(cls.model)
        cls.mission.update(cls.data, 0)
        cls.exported = BrowserScene(cls.model, cls.data)

    def test_mesh_buffers_and_world_poses(self):
        model, data, exported = self.model, self.data, self.exported
        self.assertEqual(len(exported.document['geometries']), model.ngeom)
        self.assertTrue(exported.meshes)
        self.assertLess(sum(struct.unpack('<II', blob[:8])[1] for blob in exported.meshes.values()), 100_000)
        for index, blob in exported.meshes.items():
            nv, nf = struct.unpack('<II', blob[:8])
            self.assertEqual(len(blob), 8+nv*12+nf*12)
            vertices = np.frombuffer(blob, dtype='<f4', offset=8, count=nv*3).reshape(-1, 3)
            faces = np.frombuffer(blob, dtype='<u4', offset=8+nv*12).reshape(-1, 3)
            self.assertLess(int(faces.max()), nv)
            start = model.mesh_vertadr[index]
            original = model.mesh_vert[start:start+model.mesh_vertnum[index]]
            self.assertLess(nf, model.mesh_facenum[index])
            # Decimation may move vertices slightly, but must preserve scale and location.
            np.testing.assert_allclose(vertices.min(axis=0), original.min(axis=0), atol=.01)
            np.testing.assert_allclose(vertices.max(axis=0), original.max(axis=0), atol=.01)
        for elapsed in (0, 9.8, 15.8, 33, 51, 60):
            self.mission.update(data, elapsed)
            for row in exported.poses(data):
                geom = row[0]
                np.testing.assert_allclose(row[1:4], data.geom_xpos[geom])
                q = np.array([row[7], *row[4:7]])
                matrix = np.empty(9)
                mujoco.mju_quat2Mat(matrix, q)
                np.testing.assert_allclose(matrix, data.geom_xmat[geom], atol=1e-12)
        for bed in range(3):
            body = model.body(f'harvest_item_{bed}').id
            self.assertIn(int(model.body_geomadr[body]), exported.dynamic)
        self.assertNotIn(model.geom('bed_0').id, exported.dynamic)

    def test_scene_routes_and_continuous_events(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = MissionRuntime(Path(directory))
            runtime.scene, runtime.meshes = self.exported.document, self.exported.meshes
            runtime.transforms = self.exported.poses(self.data)
            runtime.status = {'phase': 'walking', 'sequence': 1, 'total_elapsed': 0}
            runtime.sequence = 1
            with ThreadingHTTPServer(('127.0.0.1', 0), handler_for(runtime)) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                base = f'http://127.0.0.1:{server.server_port}'
                try:
                    for path in ('/', '/viewer.js', '/vendor/three.module.min.js', '/vendor/OrbitControls.js', '/vendor/BufferGeometryUtils.js'):
                        with urlopen(base+path, timeout=5) as response:
                            self.assertEqual(response.status, 200)
                    with urlopen(base+'/api/state') as response:
                        self.assertEqual(json.load(response)['transforms'], runtime.transforms)
                    with urlopen(base+'/api/scene') as response:
                        self.assertEqual(json.load(response)['up'], 'Z')
                    mesh_id = next(iter(runtime.meshes))
                    with urlopen(base+f'/assets/mesh/{mesh_id}.bin') as response:
                        self.assertEqual(response.read(), runtime.meshes[mesh_id])
                    with self.assertRaises(HTTPError) as error:
                        urlopen(base+'/frame.jpg')
                    self.assertEqual(error.exception.code, 404)
                    with urlopen(base+'/api/events', timeout=5) as response:
                        self.assertEqual(response.headers['Content-Type'], 'text/event-stream')
                        first = json.loads(response.readline().decode().removeprefix('data: '))
                        response.readline()
                        self.assertEqual(first['sequence'], 1)
                        with runtime.changed:
                            runtime.sequence = 2
                            runtime.status = {**runtime.status, 'sequence': 2, 'total_elapsed': .033}
                            runtime.changed.notify_all()
                        second = json.loads(response.readline().decode().removeprefix('data: '))
                        self.assertEqual(second['sequence'], 2)
                finally:
                    runtime.stop.set()
                    with runtime.changed:
                        runtime.changed.notify_all()
                    server.shutdown()
                    thread.join()

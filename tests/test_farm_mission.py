"""Mission timing, mounted assembly and server snapshot integration checks."""
import json
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

try:
    import mujoco
    import numpy as np
    from simulation.farm_mission import DURATION, DWELL, STOPS, mission_pose, state_at
    from simulation.garden_patrol import build_model
except ImportError:
    mujoco = None


@unittest.skipIf(mujoco is None, 'Install requirements-simulation.txt')
class MissionTests(unittest.TestCase):
    """Verify ordered tasks, stopped legs, moving arm and a stable home pose."""

    def test_schedule_and_assembly(self) -> None:
        """Each bed receives one full scan before the mounted robot returns home."""
        model = build_model()
        data = mujoco.MjData(model)
        mission_pose(model, data, 0)
        home = data.qpos.copy()
        for index, (travel, bed) in enumerate(STOPS):
            start = travel + index * DWELL
            before = state_at(start - .001)
            self.assertNotIn(bed, before.completed)
            mission_pose(model, data, start)
            initial = data.qpos.copy()
            middle = mission_pose(model, data, start + DWELL/2)
            self.assertEqual(middle.active_bed, bed)
            self.assertEqual(middle.travel, travel)
            self.assertFalse(np.array_equal(initial, data.qpos))
            for j in range(model.njnt):
                joint = model.joint(j)
                if not joint.name.startswith('arm_'):
                    np.testing.assert_equal(data.qpos[joint.qposadr[0]], initial[joint.qposadr[0]])
            self.assertIn(bed, state_at(start + DWELL).completed)
        for t in np.linspace(0, DURATION, 241):
            mission_pose(model, data, float(t))
            self.assertTrue(np.isfinite(data.qpos).all())
            chassis, mount = model.body('frontbase').id, model.body('arm_mount').id
            local = data.xmat[chassis].reshape(3, 3).T @ (data.xpos[mount]-data.xpos[chassis])
            np.testing.assert_allclose(local, (0, .10, .39), atol=1e-9)
            for name in ('1', '2', '3', '4', '5'):
                joint = model.joint('arm_'+name)
                self.assertLessEqual(joint.range[0], data.qpos[joint.qposadr[0]])
                self.assertGreaterEqual(joint.range[1], data.qpos[joint.qposadr[0]])
        final = mission_pose(model, data, DURATION + 100)
        self.assertEqual(final.phase, 'complete')
        self.assertEqual(final.completed, (2, 1, 0))
        np.testing.assert_allclose(home, data.qpos, atol=1e-9)

    def test_http_reads_do_not_advance_mission(self) -> None:
        """Multiple clients observe the same mission and receive valid route types."""
        from simulation.server import MissionRuntime, handler_for
        with tempfile.TemporaryDirectory() as temporary:
            runtime = MissionRuntime(Path(temporary))
            runtime.status = {'phase': 'complete', 'elapsed': DURATION}
            with ThreadingHTTPServer(('127.0.0.1', 0), handler_for(runtime)) as server:
                thread = threading.Thread(target=server.serve_forever)
                thread.start()
                try:
                    url = f'http://127.0.0.1:{server.server_port}'
                    for _ in range(2):
                        with urlopen(url + '/api/status') as response:
                            self.assertEqual(json.load(response), runtime.status)
                    with urlopen(url) as response:
                        self.assertIn(b'Farm harvesting mission', response.read())
                finally:
                    server.shutdown()
                    thread.join()

    def test_runtime_repeats_and_resets_cycle_results(self) -> None:
        """The pose loop crosses mission boundaries and starts fresh tasks."""
        from simulation.server import MissionRuntime, DURATION as LOOP_DURATION
        with tempfile.TemporaryDirectory() as temporary:
            runtime = MissionRuntime(Path(temporary))
            snapshots = []
            runtime.stop = MagicMock()
            runtime.stop.is_set.side_effect = [False, False, False, False, True]
            runtime.stop.wait.side_effect = lambda _: snapshots.append(runtime.snapshot()[1])
            times = [100, 100+LOOP_DURATION-.1, 100+LOOP_DURATION+.1, 101+LOOP_DURATION]
            with patch('simulation.server.mujoco.Renderer', side_effect=AssertionError('Backend must not render')), patch(
                'simulation.server.time.monotonic', side_effect=[100, *[t for instant in times for t in (instant, instant)]]
            ):
                runtime.run()
            self.assertIsNone(runtime.error)
            self.assertEqual([s['cycle'] for s in snapshots], [1, 1, 2, 2])
            self.assertEqual(snapshots[1]['completed'], (2, 1, 0))
            self.assertEqual(len(snapshots[1]['results']), 3)
            self.assertTrue(all(r['cycle'] == 1 for r in snapshots[1]['results']))
            self.assertEqual(snapshots[2]['completed'], ())
            self.assertEqual(snapshots[2]['results'], [])
            self.assertEqual(snapshots[3]['phase'], 'walking')
            self.assertGreater(snapshots[3]['elapsed'], snapshots[2]['elapsed'])
            self.assertTrue(snapshots[3]['looping'])
            self.assertEqual(json.loads((Path(temporary) / 'mission.json').read_text()), [])
            self.assertTrue(runtime.transforms)
            self.assertTrue(runtime.scene['geometries'])

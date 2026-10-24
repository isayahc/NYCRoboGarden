"""Verify visible pick/carry/release geometry and mission resets."""
import unittest

try:
    import mujoco
    import numpy as np
    from simulation.garden_patrol import build_model
    from simulation.harvest_mission import HarvestMission, STOPS, DWELL, DURATION, state_at
except ImportError:
    mujoco = None


@unittest.skipIf(mujoco is None, 'Install requirements-simulation.txt')
class HarvestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = build_model(harvest=True)
        cls.mission = HarvestMission(cls.model)

    def test_pick_carry_and_release(self):
        m, mission = self.model, self.mission
        data = mujoco.MjData(m)
        for index, (travel, bed) in enumerate(STOPS):
            start = travel + index * DWELL
            state = mission.update(data, start+2.5)
            np.testing.assert_allclose(data.site_xpos[mission.tcp], mission.sources[bed], atol=.003)
            np.testing.assert_allclose(data.mocap_pos[mission.items[bed]], mission.sources[bed])
            self.assertEqual(state.phase, 'grasping')
            for offset in (3.5, 4, 6, 8):
                state = mission.update(data, start+offset)
                self.assertEqual(state.carried_bed, bed)
                np.testing.assert_allclose(data.mocap_pos[mission.items[bed]], data.site_xpos[mission.tcp], atol=1e-9)
            state = mission.update(data, start+10)
            self.assertIn(bed, state.deposited)
            local = data.xmat[mission.box].reshape(3, 3).T @ (data.mocap_pos[mission.items[bed]]-data.xpos[mission.box])
            self.assertLess(abs(local[0]), .12)
            self.assertLess(abs(local[1]), .10)
            self.assertAlmostEqual(local[2], .045)
        mission.update(data, 0)
        for bed in range(3):
            np.testing.assert_allclose(data.mocap_pos[mission.items[bed]], mission.sources[bed])

    def test_limits_and_closed_cycle(self):
        m, mission = self.model, self.mission
        data = mujoco.MjData(m)
        mission.update(data, 0)
        home = data.qpos.copy()
        for elapsed in np.linspace(0, DURATION, 361):
            mission.update(data, float(elapsed))
            self.assertTrue(np.isfinite(data.qpos).all())
            for joint in mission.joints:
                self.assertGreaterEqual(data.qpos[joint.qposadr[0]], joint.range[0])
                self.assertLessEqual(data.qpos[joint.qposadr[0]], joint.range[1])
        np.testing.assert_allclose(data.qpos, home, atol=1e-9)
        self.assertEqual(state_at(DURATION).deposited, (2, 1, 0))
        self.assertEqual(state_at(0).deposited, ())

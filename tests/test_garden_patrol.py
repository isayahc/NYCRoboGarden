"""Integration checks for the mounted mobile-manipulator visual demonstration."""
import math
import unittest

try:
    import mujoco
    import numpy as np
    from simulation.garden_patrol import BEDS, PERIOD, build_model, pose, route
except ImportError:
    mujoco = None


@unittest.skipIf(mujoco is None, 'Install requirements-simulation.txt for model checks')
class PatrolTests(unittest.TestCase):
    """Check model assembly, attachment, route closure and obstacle separation."""

    def test_full_loop(self) -> None:
        """Sample one patrol, verifying attachment and actual geom bounds versus beds."""
        model = build_model()
        data = mujoco.MjData(model)
        chassis = model.body('frontbase').id
        mount = model.body('arm_mount').id
        robot_bodies = {chassis}
        for body in range(chassis + 1, model.nbody):
            if model.body_parentid[body] in robot_bodies:
                robot_bodies.add(body)
        robot_geoms = [g for g in range(model.ngeom) if model.geom_bodyid[g] in robot_bodies]
        for t in np.linspace(0, PERIOD, 181):
            pose(model, data, float(t))
            self.assertTrue(np.isfinite(data.qpos).all())
            local_mount = data.xmat[chassis].reshape(3, 3).T @ (data.xpos[mount]-data.xpos[chassis])
            np.testing.assert_allclose(local_mount, (0, .10, .39), atol=1e-9)
            for g in robot_geoms:
                # MuJoCo's geom bounding sphere encloses every rendered mesh vertex.
                x, y = data.geom_xpos[g, :2]
                radius = model.geom_rbound[g]
                for bed_x in BEDS:
                    distance = math.hypot(max(abs(x-bed_x)-.32, 0), max(abs(y)-.65, 0))
                    self.assertGreater(distance, radius, f'bed clearance at t={t}, geom={g}')
        np.testing.assert_allclose(route(0), route(PERIOD), atol=1e-12)
        end_pose = data.qpos.copy()
        pose(model, data, 0)
        np.testing.assert_allclose(data.qpos, end_pose, atol=1e-10)
        for name in ('1', '2', '3', '4', '5'):
            joint = model.joint('arm_'+name)
            value = data.qpos[joint.qposadr[0]]
            self.assertGreaterEqual(value, joint.range[0])
            self.assertLessEqual(value, joint.range[1])


if __name__ == '__main__':
    unittest.main()

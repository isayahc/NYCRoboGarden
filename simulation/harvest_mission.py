"""Kinematic harvest choreography: solve arm poses, carry produce, release into a box.

Produce attachment and release are scripted; this is not a contact/grasp controller.
"""
from dataclasses import dataclass
import mujoco
import numpy as np

from simulation.garden_patrol import BEDS, pose

DWELL = 12.0
STOPS = ((6.0, 2), (12.0, 1), (18.0, 0))
DURATION = 72.0


def smooth(value):
    value = np.clip(value, 0, 1)
    return value * value * (3 - 2 * value)


@dataclass(frozen=True)
class HarvestState:
    elapsed: float
    travel: float
    phase: str
    active_bed: int | None
    scan_progress: float
    completed: tuple[int, ...]
    carried_bed: int | None
    deposited: tuple[int, ...]


def state_at(elapsed):
    elapsed = min(max(elapsed, 0), DURATION)
    completed = []
    for index, (travel, bed) in enumerate(STOPS):
        start = travel + index * DWELL
        if elapsed < start:
            return HarvestState(elapsed, elapsed-index*DWELL, 'walking', None, 0, tuple(completed), None, tuple(completed))
        if elapsed < start + DWELL:
            t = elapsed-start
            phase = ('reaching' if t < 2.5 else 'grasping' if t < 3.5 else
                     'lifting' if t < 5 else 'carrying' if t < 7 else
                     'placing' if t < 8.5 else 'releasing' if t < 9.5 else 'retracting')
            carried = bed if 3.5 <= t < 8.5 else None
            deposited = tuple(completed + ([bed] if t >= 9.5 else []))
            return HarvestState(elapsed, travel, phase, bed, t/DWELL, tuple(completed), carried, deposited)
        completed.append(bed)
    return HarvestState(elapsed, elapsed-3*DWELL, 'complete' if elapsed >= DURATION else 'returning', None, 0, tuple(completed), None, tuple(completed))


class HarvestMission:
    def __init__(self, model):
        self.model = model
        self.joints = [model.joint('arm_'+str(i)) for i in range(1, 6)]
        self.qids = np.array([j.qposadr[0] for j in self.joints])
        self.dofs = np.array([j.dofadr[0] for j in self.joints])
        self.limits = np.array([j.range for j in self.joints])
        self.tcp = model.site('arm_tcp').id
        self.box = model.body('collection_box').id
        self.items = [model.body(f'harvest_item_{b}').mocapid[0] for b in range(3)]
        self.sources = [np.array([x, .55, .32]) for x in BEDS]
        self.waypoints = {}
        data = mujoco.MjData(model)
        for travel, bed in STOPS:
            self.base_pose(data, travel)
            source = self.sources[bed]
            box = data.site_xpos[model.site('box_drop').id].copy()
            positions = [source + [0, 0, .12], source,
                         source + [0, 0, .18], box + [0, 0, .08], box]
            previous = np.zeros(5)
            solved = []
            for target in positions:
                previous = self.solve(data, target, previous)
                solved.append(previous.copy())
            # Approach, close, lift, transfer, lower, release, retract.
            self.waypoints[bed] = list(zip(
                (0, 1.5, 2.5, 3.5, 5, 7, 8.5, 9.5, 10.5, 12),
                [np.zeros(5), solved[0], solved[1], solved[1], solved[2],
                 solved[3], solved[4], solved[4], solved[3], np.zeros(5)]))

    def base_pose(self, data, travel):
        pose(self.model, data, travel)
        points = [(0, (1.8, 1.3)), (6, (1.0, .96)), (12, (0.0, .96)),
                  (18, (-1.0, .96)), (36, (1.8, 1.3))]
        for (ta, a), (tb, b) in zip(points, points[1:]):
            if travel <= tb:
                xy = np.array(a) + smooth((travel-ta)/(tb-ta))*(np.array(b)-a)
                break
        else:
            xy = np.array(points[-1][1])
        data.qpos[:7] = (*xy, -.026, 0, 0, 0, 1)
        mujoco.mj_forward(self.model, data)

    def solve(self, data, target, initial):
        """Position-only damped IK, bounded by the actual URDF joint limits."""
        for seed in (initial, np.array([1.4, -.7, .7, -.5, 0]), np.array([-1.4, .7, -.7, .5, 0])):
            q = seed.copy()
            for _ in range(250):
                data.qpos[self.qids] = q
                mujoco.mj_forward(self.model, data)
                error = target - data.site_xpos[self.tcp]
                if np.linalg.norm(error) < .003:
                    return q
                jac = np.zeros((3, self.model.nv))
                mujoco.mj_jacSite(self.model, data, jac, None, self.tcp)
                j = jac[:, self.dofs]
                dq = j.T @ np.linalg.solve(j @ j.T + .0002*np.eye(3), error)
                q = np.clip(q + np.clip(dq, -.15, .15), self.limits[:, 0], self.limits[:, 1])
        raise ValueError(f'Harvest target unreachable: {target.tolist()}')

    def update(self, data, elapsed):
        state = state_at(elapsed)
        self.base_pose(data, state.travel)
        t = state.scan_progress * DWELL
        if state.active_bed is not None:
            for (ta, a), (tb, b) in zip(self.waypoints[state.active_bed], self.waypoints[state.active_bed][1:]):
                if t <= tb:
                    data.qpos[self.qids] = a + smooth((t-ta)/(tb-ta))*(b-a)
                    break
        grip = .028
        if state.active_bed is not None:
            if 2.5 <= t < 3.5:
                grip = .028 - .016*smooth(t-2.5)
            elif 3.5 <= t < 8.5:
                grip = .012
            elif 8.5 <= t < 9.5:
                grip = .012 + .016*smooth(t-8.5)
        for name in ('left', 'right'):
            data.qpos[self.model.joint('arm_finger_'+name).qposadr[0]] = grip
        mujoco.mj_forward(self.model, data)
        for bed in range(3):
            position = self.sources[bed].copy()
            if bed == state.carried_bed:
                position = data.site_xpos[self.tcp].copy()
            elif bed in state.deposited or (bed == state.active_bed and 8.5 <= t < 9.5):
                slot = np.array([-.07 + bed*.07, 0, .045])
                position = data.xpos[self.box] + data.xmat[self.box].reshape(3, 3) @ slot
                if bed == state.active_bed and t < 9.5:
                    position = data.site_xpos[self.tcp]*(1-smooth(t-8.5)) + position*smooth(t-8.5)
            data.mocap_pos[self.items[bed]] = position
        data.time = state.elapsed
        mujoco.mj_forward(self.model, data)
        return state

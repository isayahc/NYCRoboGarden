"""Deterministic, hardware-free bed inspection mission for the mounted robot."""
from __future__ import annotations

from dataclasses import dataclass
import math

import mujoco

from simulation.garden_patrol import PERIOD, pose

DWELL = 4.0
STOPS = ((6.0, 2), (9.0, 1), (12.0, 0))
DURATION = PERIOD + DWELL * len(STOPS)


@dataclass(frozen=True)
class MissionState:
    """Mission clock, patrol clock and task progress for a single shared run."""

    elapsed: float
    travel: float
    phase: str
    active_bed: int | None
    scan_progress: float
    completed: tuple[int, ...]


def state_at(elapsed: float) -> MissionState:
    """Pause the patrol clock at each stop and finish once back at home."""
    elapsed = min(max(elapsed, 0.0), DURATION)
    completed: list[int] = []
    for index, (travel, bed) in enumerate(STOPS):
        start = travel + index * DWELL
        if elapsed < start:
            return MissionState(elapsed, elapsed - index * DWELL, 'walking', None, 0, tuple(completed))
        if elapsed < start + DWELL:
            return MissionState(elapsed, travel, 'inspecting', bed, (elapsed-start)/DWELL, tuple(completed))
        completed.append(bed)
    phase = 'complete' if elapsed >= DURATION else 'returning'
    return MissionState(elapsed, elapsed-len(STOPS)*DWELL, phase, None, 0, tuple(completed))


def mission_pose(model: mujoco.MjModel, data: mujoco.MjData, elapsed: float) -> MissionState:
    """Animate transit and a joint-limited scan, with all four legs still at stops."""
    state = state_at(elapsed)
    pose(model, data, state.travel)
    if state.phase == 'inspecting':
        # A smooth out-and-back scan returns to the transit pose at both ends.
        envelope = math.sin(math.pi * state.scan_progress) ** 2
        for name, amplitude in (('1', .45), ('2', -.25), ('3', .35), ('4', -.2)):
            joint = model.joint('arm_' + name)
            value = amplitude * envelope
            data.qpos[joint.qposadr[0]] = max(joint.range[0], min(joint.range[1], value))
    data.time = state.elapsed
    mujoco.mj_forward(model, data)
    return state

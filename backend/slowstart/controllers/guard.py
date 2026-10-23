"""Calls to `@human` functions go through here (R9.5). While one is still a stub, the guard serves a
baseline and says so, so the app works and the state is visible, never hidden."""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

from slowstart.controllers import exercise, policies, steps
from slowstart.models import (
    DayResult,
    ExerciseParams,
    GoalSource,
    Session,
    StepDecision,
    StepParams,
    Target,
)


def step_window(
    days: Sequence[DayResult], today: dt.date, params: StepParams
) -> tuple[StepDecision, GoalSource]:
    try:
        decision = steps.next_window(days, params)
    except NotImplementedError:
        window = policies.fallback_window(days, today, params)
        phase = "slow_start" if not days else "cruising"
        return StepDecision(window=window, threshold=None, phase=phase), "fallback"
    window = int(min(max(decision.window, params.floor), params.ceiling))
    return decision.model_copy(update={"window": window}), "controller"


def exercise_target(
    sessions: Sequence[Session], name: str, params: ExerciseParams
) -> tuple[Target, GoalSource]:
    try:
        return exercise.next_target(sessions, name, params), "controller"
    except NotImplementedError:
        return policies.repeat_last(sessions, name, params), "fallback"


def levels_state() -> dict[str, str]:
    """For /api/health and the app's badge: which `@human` levels are still stubs."""
    probes = {
        "H1": lambda: steps.next_window([], StepParams()),
        "H2": lambda: exercise.next_target([], "squat", ExerciseParams()),
    }
    state: dict[str, str] = {}
    for name, probe in probes.items():
        try:
            probe()
        except NotImplementedError:
            state[name] = "locked"
        except Exception:  # written, but not right yet
            state[name] = "unlocked"
        else:
            state[name] = "unlocked"
    return state

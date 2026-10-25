"""Baseline policies. They share a signature with the controller policies so the evaluation harness
can run them side by side, and they are the fallbacks the guard serves while an `@human` stub is
still a stub.

A steps policy is `(history, day) -> int | None`: the goal for `day`, using only `history`.
`history` holds DayResults from before `day`; a policy ignores anything on or after it.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

import numpy as np

from slowstart.models import (
    DayResult,
    ExerciseParams,
    Session,
    SetResult,
    StepParams,
    Target,
)

LOOKBACK_DAYS = 28


def recent_steps(
    history: Sequence[DayResult], day: dt.date, days: int = LOOKBACK_DAYS
) -> list[int]:
    """Steps on worn days in the `days` calendar days before `day`, oldest first."""
    start = day - dt.timedelta(days=days)
    rows = sorted(
        (d for d in history if start <= d.date < day and d.steps is not None), key=lambda d: d.date
    )
    return [d.steps for d in rows if d.steps is not None]


def clamp_goal(value: float, params: StepParams) -> int:
    return int(min(max(round(value), params.floor), params.ceiling))


def fixed_10k(history: Sequence[DayResult], day: dt.date) -> int:
    return 10_000


def trailing_median(
    history: Sequence[DayResult], day: dt.date, params: StepParams | None = None
) -> int | None:
    steps = recent_steps(history, day)
    if not steps:
        return None
    return clamp_goal(float(np.median(steps)), params or StepParams())


def own_quantile(
    history: Sequence[DayResult], day: dt.date, q: float = 0.30, params: StepParams | None = None
) -> int | None:
    """The person's own q-th percentile over the last 28 days: the fair rival for the TabPFN cap,
    which also aims to be reached about 7 days in 10."""
    steps = recent_steps(history, day)
    if not steps:
        return None
    return clamp_goal(float(np.quantile(steps, q)), params or StepParams())


MIN_IMPORTED = 7


def history_start(history: Sequence[DayResult], params: StepParams) -> int | None:
    """R1.10: where the controller starts for someone who brought history, or None for a new person.

    The days imported before the first played day (no goal); their own 30th percentile over the last 28
    calendar days of them, rounded to 50. Days played later never change it."""
    played = [d.date for d in history if d.goal is not None]
    first_played = min(played) if played else None
    imported = [
        d for d in history if d.goal is None and (first_played is None or d.date < first_played)
    ]
    if not imported:
        return None
    last = max(d.date for d in imported)
    steps = recent_steps(imported, last + dt.timedelta(days=1))
    if len(steps) < MIN_IMPORTED:
        return None
    return clamp_goal(round(float(np.quantile(steps, 0.30)) / 50) * 50, params)


def fallback_window(history: Sequence[DayResult], day: dt.date, params: StepParams) -> int:
    """What the guard serves while H1 is a stub, and the cap when the predictor is unavailable (R1.8):
    80% of the trailing 14-day median, or the starting goal for a brand-new person."""
    steps = recent_steps(history, day, days=14)
    if not steps:
        return params.start
    return clamp_goal(0.8 * float(np.median(steps)), params)


# ---- exercises ----


def working_sets(session: Session) -> list[SetResult]:
    return [s for s in session.sets if s.reps > 0]


def top_weight(session: Session) -> float | None:
    weights = [s.weight_kg for s in working_sets(session) if s.weight_kg]
    return max(weights) if weights else None


def best_reps(session: Session, sets: int) -> list[int]:
    return sorted((s.reps for s in working_sets(session)), reverse=True)[:sets]


def repeat_last(sessions: Sequence[Session], exercise: str, params: ExerciseParams) -> Target:
    """Baseline and guard fallback: do what you did last time (or the starter if you never did)."""
    spec = params.scheme[exercise]
    ordered = sorted(sessions, key=lambda s: s.date)
    if not ordered:
        return Target(sets=spec.sets, reps=spec.reps, weight_kg=spec.starter_weight_kg)
    last = ordered[-1]
    if spec.kind == "bodyweight":
        reps = best_reps(last, spec.sets)
        return Target(sets=spec.sets, reps=max(1, min(reps) if reps else spec.reps), weight_kg=None)
    weight = top_weight(last) or spec.starter_weight_kg
    return Target(sets=spec.sets, reps=spec.reps, weight_kg=weight)


def fixed_plan(sessions: Sequence[Session], exercise: str, params: ExerciseParams) -> Target:
    """Baseline: always add one step to what you did last time, whatever happened (+2.5 kg, or +1 rep)."""
    spec = params.scheme[exercise]
    base = repeat_last(sessions, exercise, params)
    if not sessions:
        return base
    if spec.kind == "bodyweight":
        return Target(sets=base.sets, reps=base.reps + 1)
    return Target(
        sets=base.sets,
        reps=base.reps,
        weight_kg=(base.weight_kg or 0.0) + (spec.increment_kg or 0.0),
    )

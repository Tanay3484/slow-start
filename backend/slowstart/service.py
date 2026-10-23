"""Assemble today's goal: the controller's window, capped by the predictor (design section 1)."""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

from slowstart.config import Settings
from slowstart.controllers import guard
from slowstart.models import DayResult, ExerciseGoal, ExerciseParams, Goal, Session, StepParams
from slowstart.prediction.cap import compute_cap
from slowstart.prediction.predictor import Predictor


def clean_history(history: Sequence[DayResult], today: dt.date) -> list[DayResult]:
    """One entry per date (the last one wins), oldest first, nothing from today or later."""
    by_date = {d.date: d for d in history if d.date < today}
    return [by_date[k] for k in sorted(by_date)]


def step_goal(
    history: Sequence[DayResult],
    today: dt.date,
    predictor: Predictor | None,
    settings: Settings,
    params: StepParams | None = None,
) -> Goal:
    params = params or StepParams()
    days = clean_history(history, today)
    decision, source = guard.step_window(days, today, params)
    cap = compute_cap(days, today, predictor, settings, params)
    goal = decision.window if cap.value is None else min(decision.window, cap.value)
    goal = int(min(max(goal, params.floor), params.ceiling))
    notes = []
    if source == "fallback":
        notes.append("The step controller (H1) is not written yet; a baseline set this goal.")
    if cap.source == "median":
        notes.append("The predictor was unavailable; the cap is 80% of your recent median.")
    return Goal(
        goal=goal,
        window=decision.window,
        threshold=decision.threshold,
        phase=decision.phase,
        cap=cap,
        source=source,
        note=" ".join(notes),
    )


def exercise_goal(
    sessions: Sequence[Session], exercise: str, params: ExerciseParams | None = None
) -> ExerciseGoal:
    params = params or ExerciseParams()
    mine = [s for s in sessions if s.exercise == exercise]
    target, source = guard.exercise_target(mine, exercise, params)
    note = (
        "The exercise controller (H2) is not written yet; 'repeat last time' set this."
        if (source == "fallback")
        else ""
    )
    return ExerciseGoal(
        exercise=exercise,
        label=params.scheme[exercise].label,
        target=target,
        source=source,
        note=note,
    )

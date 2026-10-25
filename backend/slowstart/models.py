"""Domain and API models. Frozen, so a controller cannot mutate what it is given."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Phase = Literal["slow_start", "cruising", "recovering"]
CapSource = Literal["tabpfn", "median", "none"]
GoalSource = Literal["controller", "fallback"]


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class DayResult(Frozen):
    """One day of walking. `steps is None` means missing (tracker not worn).
    `goal is None` means no goal was shown that day (before the app was used)."""

    date: dt.date
    steps: int | None = Field(default=None, ge=0)
    goal: int | None = Field(default=None, ge=0)
    excused: bool = False


class StepParams(Frozen):
    start: int = 1500
    floor: int = 1000
    ceiling: int = 20000
    ai: int = 250


class StepDecision(Frozen):
    window: int
    threshold: int | None = None
    phase: Phase = "slow_start"


class Cap(Frozen):
    value: int | None = None
    p30: int | None = None
    p50: int | None = None
    source: CapSource = "none"


class Goal(Frozen):
    goal: int
    window: int
    threshold: int | None = None
    phase: Phase
    cap: Cap
    source: GoalSource
    note: str = ""
    from_history: int | None = None  # R1.10: the start taken from imported days, if any


class SetResult(Frozen):
    weight_kg: float | None = None
    reps: int = Field(ge=0)


class Session(Frozen):
    date: dt.date
    exercise: str
    sets: list[SetResult]


class Target(Frozen):
    sets: int
    reps: int
    weight_kg: float | None = None


class ExerciseSpec(Frozen):
    label: str
    kind: Literal["barbell", "dumbbell", "bodyweight"]
    sets: int
    reps: int
    increment_kg: float | None
    starter_weight_kg: float | None


class ExerciseParams(Frozen):
    lift_miss_cut: float = 0.90
    bodyweight_miss_cut: float = 0.80
    scheme: dict[str, ExerciseSpec] = Field(default_factory=lambda: dict(DEFAULT_SCHEME))


def _spec(label, kind, sets, reps, inc, start):
    return ExerciseSpec(
        label=label, kind=kind, sets=sets, reps=reps, increment_kg=inc, starter_weight_kg=start
    )


# Exercises the app supports (R2.2). Deadlift is one heavy set; the rest are three.
DEFAULT_SCHEME: dict[str, ExerciseSpec] = {
    "squat": _spec("Squat", "barbell", 3, 5, 2.5, 20.0),
    "bench_press": _spec("Bench press", "barbell", 3, 8, 2.5, 20.0),
    "deadlift": _spec("Deadlift", "barbell", 1, 5, 2.5, 40.0),
    "overhead_press": _spec("Overhead press", "barbell", 3, 8, 2.5, 20.0),
    "barbell_row": _spec("Barbell row", "barbell", 3, 8, 2.5, 20.0),
    "dumbbell_bench_press": _spec("Dumbbell bench press", "dumbbell", 3, 10, 1.0, 8.0),
    "dumbbell_row": _spec("Dumbbell row", "dumbbell", 3, 10, 1.0, 8.0),
    "dumbbell_shoulder_press": _spec("Dumbbell shoulder press", "dumbbell", 3, 10, 1.0, 6.0),
    "goblet_squat": _spec("Goblet squat", "dumbbell", 3, 10, 1.0, 8.0),
    "push_up": _spec("Push-up", "bodyweight", 3, 8, None, None),
    "pull_up": _spec("Pull-up", "bodyweight", 3, 3, None, None),
    "dip": _spec("Dip", "bodyweight", 3, 5, None, None),
    "bodyweight_squat": _spec("Bodyweight squat", "bodyweight", 3, 12, None, None),
}


# ---- API bodies ----


class StepGoalRequest(BaseModel):
    today: dt.date
    history: list[DayResult] = Field(default_factory=list, max_length=800)
    # False: the controller's window alone, no cap. The website's "try the controller" uses it.
    use_cap: bool = True


class ExerciseGoalRequest(BaseModel):
    exercise: str
    sessions: list[Session] = Field(default_factory=list, max_length=800)


class ExerciseGoal(Frozen):
    exercise: str
    label: str
    target: Target
    source: GoalSource
    note: str = ""


class ImportRequest(BaseModel):
    text: str = Field(max_length=8_000_000)
    filename: str = ""


class CheckinRequest(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    name: str = Field(default="you", max_length=40)


class Checkin(Frozen):
    energy: Literal["low", "ok", "high"]
    body: list[str]
    excused: bool
    line: str  # Slumbrock's reaction: from Gemma, or a template
    tip: str = ""  # chosen by code from a curated list, never by the model
    aside: str = ""  # now and then, a rock joke
    source: Literal["gemma", "template"]

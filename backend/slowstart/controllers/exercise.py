"""H2: the exercise controller.

Planned as one of Tanay's hand-written levels; Tanay handed it over to Claude on 2026-10-25 to make the
deadline, and the README and the post say so. The contract, with a worked example, is in
specs/001-slow-start-mvp/tasks.md under H2: the same family as the step controller (add a step after a
success, cut after a miss), with a gentler cut for lifts, the way a deload works.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from slowstart.models import ExerciseParams, ExerciseSpec, Session, Target


def _working(session: Session) -> list[tuple[float | None, int]]:
    return [(s.weight_kg, s.reps) for s in session.sets if s.reps > 0]


def _anchor(first: Session, spec: ExerciseSpec) -> Target:
    """The first target: what the person showed they can do in their first session."""
    sets = _working(first)
    if spec.kind == "bodyweight":
        best = sorted((r for _, r in sets), reverse=True)[: spec.sets]
        return Target(sets=spec.sets, reps=max(1, min(best)) if best else spec.reps, weight_kg=None)
    weights = [w for w, _ in sets if w]
    return Target(
        sets=spec.sets,
        reps=spec.reps,
        weight_kg=max(weights) if weights else spec.starter_weight_kg,
    )


def meets(session: Session, target: Target) -> bool:
    """At least `target.sets` working sets at the target weight (any weight for bodyweight) and reps."""
    done = [
        1
        for w, r in _working(session)
        if r >= target.reps and (target.weight_kg is None or (w or 0.0) >= target.weight_kg - 1e-9)
    ]
    return len(done) >= target.sets


def _step_up(t: Target, spec: ExerciseSpec) -> Target:
    if spec.kind == "bodyweight":
        return t.model_copy(update={"reps": t.reps + 1})
    weight = round((t.weight_kg or 0.0) + (spec.increment_kg or 0.0), 2)
    return t.model_copy(update={"weight_kg": weight})


def _cut(t: Target, spec: ExerciseSpec, params: ExerciseParams) -> Target:
    if spec.kind == "bodyweight":
        return t.model_copy(
            update={"reps": max(1, math.floor(t.reps * params.bodyweight_miss_cut))}
        )
    inc = spec.increment_kg or 1.0
    cut = math.floor((t.weight_kg or 0.0) * params.lift_miss_cut / inc + 1e-9) * inc
    return t.model_copy(update={"weight_kg": round(max(inc, cut), 2)})


def next_target(sessions: Sequence[Session], exercise: str, params: ExerciseParams) -> Target:
    """Return the sets, reps and load for the next session of `exercise`."""
    spec = params.scheme[exercise]
    ordered = sorted(sessions, key=lambda s: s.date)
    if not ordered:
        return Target(sets=spec.sets, reps=spec.reps, weight_kg=spec.starter_weight_kg)
    target = _anchor(ordered[0], spec)
    for session in ordered:
        target = _step_up(target, spec) if meets(session, target) else _cut(target, spec, params)
    return target

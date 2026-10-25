"""Walk-forward evaluation of exercise policies on a Hevy log (R8.2, design section 10).

For every session of an exercise, each policy suggests a target using only the sessions before it; the
real session is then checked against that target. Scored on the sessions in the held-out window, on the
(exercise, date) pairs where every policy produced a target.

Two numbers per policy, because either alone can be gamed:

- **met**: the share of sessions that reached the suggested target.
- **level**: how demanding the target was, as a ratio to what the person did last time
  (weight for lifts, reps for bodyweight). A policy that "wins" by suggesting less than last time shows
  up as level < 1.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from slowstart.controllers import exercise, policies
from slowstart.models import ExerciseParams, Session, SetResult, Target

TargetPolicy = Callable[[Sequence[Session], str, ExerciseParams], Target]
MIN_HISTORY = 3


@dataclass(frozen=True)
class Scored:
    exercise: str
    date: dt.date
    met: int
    level: float


def meets(target: Target, session: Session) -> bool:
    sets = policies.working_sets(session)
    if target.weight_kg is None:
        done = [s for s in sets if s.reps >= target.reps]
    else:
        done = [
            s for s in sets if (s.weight_kg or 0.0) >= target.weight_kg and s.reps >= target.reps
        ]
    return len(done) >= target.sets


def level(target: Target, last: Session) -> float | None:
    """How demanding the target is compared with the last session."""
    if target.weight_kg is not None:
        prev = policies.top_weight(last)
        return target.weight_kg / prev if prev else None
    # The reps the person reliably did: the lowest of their best `sets` sets, as the target is built.
    reliable = policies.best_reps(last, target.sets)
    return target.reps / min(reliable) if reliable else None


def make_policies(include_controller: bool = True) -> dict[str, TargetPolicy]:
    out: dict[str, TargetPolicy] = {
        "repeat_last": policies.repeat_last,
        "fixed_plan": policies.fixed_plan,
    }
    if include_controller:
        out["controller"] = exercise.next_target
    return out


def controller_is_written(params: ExerciseParams) -> bool:
    try:
        exercise.next_target([], "squat", params)
    except NotImplementedError:
        return False
    except Exception:  # written, maybe wrong; the tests will say
        return True
    return True


def top_set(session: Session) -> SetResult | None:
    """The heaviest working set (most reps on ties, and for bodyweight)."""
    sets = policies.working_sets(session)
    return max(sets, key=lambda s: (s.weight_kg or 0.0, s.reps), default=None)


def top_set_params(
    sessions: Sequence[Session], start: dt.date, params: ExerciseParams
) -> ExerciseParams:
    """R8.6: the same scheme, but one set at the person's usual top-set reps from before `start`."""
    scheme = dict(params.scheme)
    for ex, rows in group_sessions([s for s in sessions if s.date < start]).items():
        if ex not in scheme:
            continue
        reps = sorted(t.reps for t in map(top_set, rows) if t)
        if reps:
            scheme[ex] = scheme[ex].model_copy(update={"sets": 1, "reps": reps[len(reps) // 2]})
    return params.model_copy(update={"scheme": scheme})


def group_sessions(sessions: Sequence[Session]) -> dict[str, list[Session]]:
    out: dict[str, list[Session]] = {}
    for s in sorted(sessions, key=lambda x: x.date):
        out.setdefault(s.exercise, []).append(s)
    return out


def score(
    sessions: Sequence[Session],
    policy_map: Mapping[str, TargetPolicy],
    start: dt.date,
    params: ExerciseParams | None = None,
) -> dict[str, list[Scored]]:
    params = params or ExerciseParams()
    by_ex = group_sessions(sessions)
    per_policy: dict[str, dict[tuple[str, dt.date], Scored]] = {name: {} for name in policy_map}
    for ex, rows in by_ex.items():
        if ex not in params.scheme:
            continue
        for i, session in enumerate(rows):
            if session.date < start or i < MIN_HISTORY:
                continue
            before = rows[:i]  # strictly earlier sessions only
            for name, policy in policy_map.items():
                target = policy(before, ex, params)
                lvl = level(target, before[-1])
                if lvl is None:
                    continue
                per_policy[name][(ex, session.date)] = Scored(
                    ex, session.date, int(meets(target, session)), lvl
                )
    keys = set.intersection(*(set(d) for d in per_policy.values())) if per_policy else set()
    return {name: [d[k] for k in sorted(keys)] for name, d in per_policy.items()}

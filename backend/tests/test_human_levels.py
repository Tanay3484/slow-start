"""Contract tests for Tanay's `@human` levels H1-H3 (specs/001-slow-start-mvp/tasks.md).

While a function is still a stub (`NotImplementedError`) its tests skip. As soon as it is written they run.
Run one level at a time: `pytest backend/tests/test_human_levels.py -k H1`.
"""

from __future__ import annotations

import datetime as dt
import math

import pytest

from slowstart.controllers.exercise import next_target
from slowstart.controllers.steps import next_window
from slowstart.evaluation.stats import goal_level, paired_bootstrap
from slowstart.models import DayResult, ExerciseParams, Session, SetResult, StepParams, Target

P = StepParams()
D0 = dt.date(2026, 10, 1)


def locked(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except NotImplementedError as exc:
        pytest.skip(f"WIP: {exc}")


def day(i: int, steps: int | None, goal: int | None, excused: bool = False) -> DayResult:
    return DayResult(date=D0 + dt.timedelta(days=i), steps=steps, goal=goal, excused=excused)


# ---------------- H1: the step controller ----------------

H1_TABLE = [
    ([], 1500, None, "slow_start"),
    ([(1600, 1500)], 3000, None, "slow_start"),
    ([(1600, 1500), (3200, 3000)], 6000, None, "slow_start"),
    ([(1600, 1500), (3200, 3000), (4200, 6000)], 3000, 3000, "recovering"),
    ([(1600, 1500), (3200, 3000), (4200, 6000), (3100, 3000)], 3250, 3000, "cruising"),
    (
        [(1600, 1500), (3200, 3000), (4200, 6000), (3100, 3000), (800, 3250)],
        1625,
        1625,
        "recovering",
    ),
]


def run(pairs, **kw):
    return [day(i, s, g, **kw) for i, (s, g) in enumerate(pairs)]


@pytest.mark.parametrize(("pairs", "window", "threshold", "phase"), H1_TABLE)
def test_H1_worked_example(pairs, window, threshold, phase):
    out = locked(next_window, run(pairs), P)
    assert (out.window, out.threshold, out.phase) == (window, threshold, phase)


def test_H1_unsorted_input_gives_the_same_answer():
    ordered = run(H1_TABLE[4][0])
    out = locked(next_window, list(reversed(ordered)), P)
    assert out.window == 3250


def test_H1_input_is_not_mutated():
    days_in = run(H1_TABLE[4][0])
    before = list(days_in)
    locked(next_window, days_in, P)
    assert days_in == before


def test_H1_excused_and_missing_days_change_nothing():
    base = run([(1600, 1500)])
    plain = locked(next_window, base, P)
    with_extras = base + [day(5, 0, 3000, excused=True), day(6, None, 3000), day(7, 900, None)]
    out = locked(next_window, with_extras, P)
    assert (out.window, out.threshold) == (plain.window, plain.threshold)


def test_H1_a_miss_never_goes_below_the_floor():
    out = locked(next_window, run([(0, 1500), (0, 1000), (0, 1000)]), P)
    assert out.window == P.floor


def test_H1_the_ceiling_holds():
    out = locked(next_window, run([(2000, 1500), (4000, 3000), (7000, 6000), (13000, 12000)]), P)
    assert out.window == P.ceiling


# ---------------- H2: the exercise controller ----------------

X = ExerciseParams()


def sess(i: int, exercise: str, *sets: tuple[float | None, int]) -> Session:
    return Session(
        date=D0 + dt.timedelta(days=i * 3),
        exercise=exercise,
        sets=[SetResult(weight_kg=w, reps=r) for w, r in sets],
    )


def bench(i, weight, reps=8, n=3):
    return sess(i, "bench_press", *[(weight, reps)] * n)


def pushups(i, reps, n=3):
    return sess(i, "push_up", *[(None, reps)] * n)


def test_H2_no_history_gives_the_starter():
    assert locked(next_target, [], "bench_press", X) == Target(sets=3, reps=8, weight_kg=20.0)


def test_H2_a_met_session_adds_one_increment():
    assert locked(next_target, [bench(0, 60)], "bench_press", X) == Target(
        sets=3, reps=8, weight_kg=62.5
    )


def test_H2_two_met_sessions():
    out = locked(next_target, [bench(0, 60), bench(1, 62.5)], "bench_press", X)
    assert out.weight_kg == 65.0


def test_H2_a_missed_session_cuts_about_ten_percent_to_the_increment():
    out = locked(next_target, [bench(0, 60), bench(1, 62.5, n=2)], "bench_press", X)
    assert out.weight_kg == 55.0 and (out.sets, out.reps) == (3, 8)


def test_H2_bodyweight_adds_a_rep():
    out = locked(next_target, [pushups(0, 10), pushups(1, 11)], "push_up", X)
    assert (out.reps, out.weight_kg) == (12, None)


def test_H2_bodyweight_miss_cuts_twenty_percent():
    out = locked(next_target, [pushups(0, 10), pushups(1, 6)], "push_up", X)
    assert out.reps == 8


def test_H2_unsorted_sessions_give_the_same_answer():
    ordered = [bench(0, 60), bench(1, 62.5)]
    assert locked(next_target, list(reversed(ordered)), "bench_press", X).weight_kg == 65.0


def test_H2_the_cut_never_reaches_zero():
    out = locked(
        next_target,
        [sess(0, "dip", (None, 1), (None, 1), (None, 1)), sess(1, "dip", (None, 0))],
        "dip",
        X,
    )
    assert out.reps >= 1


# ---------------- H3: evaluation statistics ----------------


def test_H3_goal_level_is_the_mean_ratio():
    assert locked(goal_level, [100, 200], [200, 200]) == pytest.approx(0.75)


def test_H3_goal_level_skips_non_positive_references():
    assert locked(goal_level, [100, 200, 50], [200, 0, -5]) == pytest.approx(0.5)


def test_H3_goal_level_with_nothing_is_nan():
    assert math.isnan(locked(goal_level, [100], [0]))


def test_H3_bootstrap_identical_policies():
    a = [1, 0, 1, 1, 0, 1]
    assert locked(paired_bootstrap, a, a, list("aabbcc")) == (0.0, 0.0, 0.0)


def test_H3_bootstrap_one_policy_always_better():
    diff, lo, hi = locked(paired_bootstrap, [1] * 6, [0] * 6, list("aabbcc"))
    assert (diff, lo, hi) == (1.0, 1.0, 1.0)


def test_H3_bootstrap_interval_brackets_the_difference_and_is_repeatable():
    a = [1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1]
    b = [1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1]
    groups = list("aaabbbcccddd")
    first = locked(paired_bootstrap, a, b, groups, 500, 7)
    again = paired_bootstrap(a, b, groups, 500, 7)
    assert first == again
    diff, lo, hi = first
    assert lo <= diff <= hi and diff == pytest.approx(sum(a) / 12 - sum(b) / 12)


@pytest.mark.parametrize(
    ("a", "b", "g"), [([1], [1, 0], ["a"]), ([], [], []), ([1, 0], [1, 0], ["a"])]
)
def test_H3_bootstrap_rejects_bad_input(a, b, g):
    locked(paired_bootstrap, [1], [1], ["a"])  # skip while it is a stub
    with pytest.raises(ValueError):
        paired_bootstrap(a, b, g)

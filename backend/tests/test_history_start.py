"""R1.10: someone who imports history starts from it, not from 1,500."""

from __future__ import annotations

import datetime as dt

from slowstart.config import Settings
from slowstart.controllers import policies
from slowstart.models import DayResult, StepParams
from slowstart.service import step_goal

D0 = dt.date(2026, 9, 1)


def imported(steps: list[int | None]) -> list[DayResult]:
    return [DayResult(date=D0 + dt.timedelta(days=i), steps=s) for i, s in enumerate(steps)]


def test_no_imported_history_keeps_the_default_start():
    assert policies.history_start([], StepParams()) is None
    assert policies.history_start(imported([4000] * 6), StepParams()) is None  # fewer than 7


def test_start_is_the_own_30th_percentile_of_the_last_28_imported_days_rounded_to_50():
    old = [20000] * 30  # older than the last 28: ignored
    recent = [3000, 3100, 3200, 3300, 3400, 3500, 3600, 3700, 3800, 3900] * 2 + [None] * 8
    start = policies.history_start(imported(old + recent), StepParams())
    assert start == 3250  # 30th percentile of 3,000..3,900 twice is 3,270, rounded to 50


def test_days_played_later_never_move_the_start():
    history = imported([5000] * 20)
    first = policies.history_start(history, StepParams())
    played = [
        DayResult(date=D0 + dt.timedelta(days=20 + i), steps=s, goal=5000)
        for i, s in enumerate([1000, 9000])
    ]
    assert policies.history_start(history + played, StepParams()) == first == 5000


def test_the_goal_service_starts_from_history_and_says_so():
    days = imported([6000] * 28)
    today = D0 + dt.timedelta(days=28)
    goal = step_goal(days, today, predictor=None, settings=Settings(), use_cap=False)
    assert goal.from_history == 6000
    assert goal.window == 6000 and goal.goal == 6000
    fresh = step_goal([], today, predictor=None, settings=Settings(), use_cap=False)
    assert fresh.from_history is None and fresh.window == 1500

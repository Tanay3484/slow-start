"""The evaluation harnesses must never let a policy see the day it is setting a goal for (R8.3)."""

from __future__ import annotations

import datetime as dt

import numpy as np
from conftest import days
from slowstart.config import Settings
from slowstart.evaluation import steps_eval, training_eval
from slowstart.models import DayResult, ExerciseParams, Session, SetResult, StepParams, Target
from slowstart.prediction.predictor import EmpiricalPredictor

D0 = dt.date(2026, 10, 1)


def people(n_days=25):
    # Each person's steps rise by a fixed amount a day, so any peek at the future would be obvious.
    return {
        "A": days([3000 + 100 * i for i in range(n_days)]),
        "B": days([5000 + 150 * i for i in range(n_days)]),
    }


def test_simulate_hands_each_policy_only_earlier_days():
    seen = []

    def spy(person, history, day):
        assert all(d.date < day for d in history), "a policy was shown today or the future"
        seen.append((len(history), day))
        return 1000

    out = steps_eval.simulate("A", people()["A"], spy)
    assert [n for n, _ in seen] == list(range(25)) and len(out) == 25


def test_policies_get_the_goals_they_set_but_never_the_steps_of_the_day_they_are_setting():
    def policy(person, history, day):
        # The last history entry is yesterday, with its own goal and steps, and nothing about today.
        assert not history or history[-1].date == day - dt.timedelta(days=1)
        return 2000 + len(history)

    out = steps_eval.simulate("A", people()["A"], policy)
    assert [d.goal for d in out][:3] == [2000, 2001, 2002]
    assert out[5].steps == 3500


def test_calendar_caps_train_only_on_earlier_days():
    """Steps rise by a constant each day, so the training targets from the past are all lower than any
    test day. If the day itself leaked into training, the largest training target would reach it."""

    class Recorder(EmpiricalPredictor):
        def __init__(self):
            self.calls = []

        def quantiles(self, x_train, y_train, x_test, qs):
            self.calls.append((float(np.max(y_train)), len(x_train)))
            return super().quantiles(x_train, y_train, x_test, qs)

    data = people()
    rec = Recorder()
    settings = Settings(use_tabpfn=False, feature_set="v1")
    caps = steps_eval.calendar_caps(data, rec, settings, min_pool=10)
    assert caps and rec.calls
    by_day = {d.date: d.steps for d in data["B"]}  # B is the higher walker
    first_test_day = min(day for _, day in caps)
    # Every training target seen on any call is below the highest steps ever recorded before that
    # call's day: i.e. strictly earlier than B's value on the last day that has a cap.
    last_day = max(day for _, day in caps)
    assert max(c[0] for c in rec.calls) < by_day[last_day]
    assert first_test_day > D0


def test_score_only_counts_person_days_every_policy_answered():
    data = people()
    caps = {("A", D0 + dt.timedelta(days=20)): (2500.0, 3000.0)}  # a cap for one day only
    policy_map = steps_eval.make_policies(caps, StepParams(), include_controller=False)
    scored, meta = steps_eval.score(data, policy_map, D0 + dt.timedelta(days=15))
    sizes = {len(v) for v in scored.values()}
    assert sizes == {1} and meta["person_days"] == 1


def test_training_policies_see_only_earlier_sessions():
    def mk(i, w):
        return Session(
            date=D0 + dt.timedelta(days=3 * i),
            exercise="bench_press",
            sets=[SetResult(weight_kg=w, reps=8)] * 3,
        )

    sessions = [mk(i, 50 + 2.5 * i) for i in range(12)]
    seen = []

    def spy(before, ex, params):
        assert all(s.date < sessions[len(before)].date for s in before)
        seen.append(len(before))
        return Target(sets=3, reps=8, weight_kg=50.0)

    out = training_eval.score(sessions, {"spy": spy}, D0)
    assert seen and min(seen) >= training_eval.MIN_HISTORY
    assert all(r.met == 1 for r in out["spy"])  # a light target is always met
    assert (
        training_eval.meets(Target(sets=3, reps=8, weight_kg=60.0), sessions[0]) is False
    )  # 50 kg session does not meet 60


def test_level_flags_a_policy_that_asks_for_less():
    last = Session(date=D0, exercise="squat", sets=[SetResult(weight_kg=100.0, reps=5)] * 3)
    assert training_eval.level(Target(sets=3, reps=5, weight_kg=90.0), last) == 0.9
    bw = Session(date=D0, exercise="push_up", sets=[SetResult(weight_kg=None, reps=10)] * 3)
    assert training_eval.level(Target(sets=3, reps=12), bw) == 1.2


def test_baseline_policies_run_on_every_exercise():
    params = ExerciseParams()
    for ex in params.scheme:
        t = training_eval.make_policies(include_controller=False)["fixed_plan"]([], ex, params)
        assert t.sets >= 1 and t.reps >= 1


def test_dayresult_import_for_type_checkers():
    assert DayResult(date=D0, steps=1).steps == 1

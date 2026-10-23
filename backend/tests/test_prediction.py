from __future__ import annotations

import datetime as dt

import numpy as np
import pytest
from conftest import START, days
from slowstart.config import Settings
from slowstart.controllers import policies
from slowstart.models import Cap, StepParams
from slowstart.prediction.cap import compute_cap, load_prior, prior_sample
from slowstart.prediction.features import FEATURES, day_features, steps_map, training_rows
from slowstart.prediction.predictor import EmpiricalPredictor

SETTINGS = Settings(use_tabpfn=False, prior_rows=50)
PARAMS = StepParams()
WEEK = [6000, 7000, 5000, 8000, 6500, 9000, 4000, 7500, 6800, 7200]


def test_features_use_only_earlier_days():
    s = steps_map(days(WEEK))
    target = START + dt.timedelta(days=8)
    base = day_features(s, target)
    # Add the target day itself and future days with absurd values: nothing may change.
    polluted = dict(s)
    polluted[target] = 99999
    polluted[target + dt.timedelta(days=1)] = 99999
    assert day_features(polluted, target) == base


def test_features_need_three_recent_worn_days():
    assert day_features(steps_map(days([5000, 6000])), START + dt.timedelta(days=3)) is None


def test_feature_vector_matches_the_names():
    vec = day_features(steps_map(days(WEEK)), START + dt.timedelta(days=9))
    assert len(vec) == len(FEATURES)
    assert vec[0] == WEEK[8] and vec[1] == WEEK[7]  # lag1, lag2


def test_missing_lag_is_nan():
    s = steps_map(days([5000, 6000, None, 7000, 8000, 6500]))
    vec = day_features(s, START + dt.timedelta(days=5))
    assert vec[0] == 8000 and vec[1] == 7000 and np.isnan(vec[2])  # day 2 was not worn


def test_training_rows_are_rebuilt_from_the_past_only():
    steps = steps_map(days(WEEK))
    rows = training_rows(steps)
    assert rows
    for day, feats, target in rows:
        past_only = {d: s for d, s in steps.items() if d < day}
        np.testing.assert_array_equal(feats, day_features(past_only, day))
        assert target == steps[day]


def test_bundled_prior_loads():
    x, y = load_prior()
    assert x.shape[1] == len(FEATURES) and len(x) == len(y) > 500
    sx, sy = prior_sample(30)
    assert len(sx) == 30 == len(sy)


def test_cap_none_before_a_week_of_history():
    cap = compute_cap(
        days([5000, 6000, 7000]), START + dt.timedelta(days=3), None, SETTINGS, PARAMS
    )
    assert cap == Cap(source="none")


def test_cap_uses_the_predictor_and_rounds_to_fifty():
    hist = days(WEEK)
    cap = compute_cap(hist, START + dt.timedelta(days=10), EmpiricalPredictor(), SETTINGS, PARAMS)
    assert cap.source == "tabpfn"  # any predictor result is labelled so; the app only builds TabPFN
    assert cap.p30 % 50 == 0 and PARAMS.floor <= cap.value <= PARAMS.ceiling
    assert cap.p50 >= cap.p30


def test_cap_falls_back_to_the_median_when_the_predictor_fails():
    class Broken:
        name = "broken"

        def quantiles(self, *a, **k):
            raise RuntimeError("boom")

    cap = compute_cap(days(WEEK), START + dt.timedelta(days=10), Broken(), SETTINGS, PARAMS)
    assert cap.source == "median" and cap.value == pytest.approx(0.8 * np.median(WEEK[-10:]), abs=1)


def test_cap_without_a_predictor_is_the_median_cap():
    cap = compute_cap(days(WEEK), START + dt.timedelta(days=10), None, SETTINGS, PARAMS)
    assert cap.source == "median"


# ---- baseline policies ----


def test_policies_ignore_the_day_itself_and_the_future():
    hist = days(WEEK)
    day = START + dt.timedelta(days=5)
    ref = policies.own_quantile(hist, day), policies.trailing_median(hist, day)
    future = hist + days([99999] * 5, start=day)  # same dates as the target and after
    assert (policies.own_quantile(future, day), policies.trailing_median(future, day)) == ref


def test_fixed_policy_and_empty_history():
    assert policies.fixed_10k([], START) == 10_000
    assert policies.trailing_median([], START) is None
    assert policies.fallback_window([], START, PARAMS) == PARAMS.start


# ---- feature set v2: relative to the person's own scale ----


def test_v2_features_are_scale_free_except_the_log_scale():
    from slowstart.prediction.features import FEATURE_SETS, FEATURES_V2

    fs = FEATURE_SETS["v2"]
    day = START + dt.timedelta(days=9)
    a, scale_a = fs.features(steps_map(days(WEEK)), day)
    b, scale_b = fs.features(steps_map(days([s * 2 for s in WEEK])), day)
    assert scale_b == pytest.approx(2 * scale_a)
    i = FEATURES_V2.index("log_scale")
    for k, (x, y) in enumerate(zip(a, b, strict=True)):
        if k != i:
            assert x == pytest.approx(y, nan_ok=True)
    assert b[i] - a[i] == pytest.approx(np.log(2))


def test_v2_rows_use_only_the_past_and_a_ratio_target():
    from slowstart.prediction.features import FEATURE_SETS

    fs = FEATURE_SETS["v2"]
    steps = steps_map(days(WEEK))
    rows = fs.rows(steps)
    assert rows
    for day, feats, ratio, scale in rows:
        past = {d: s for d, s in steps.items() if d < day}
        again, scale_again = fs.features(past, day)
        np.testing.assert_array_equal(feats, again)
        assert scale == scale_again and ratio * scale == pytest.approx(steps[day])


def test_v2_cap_is_multiplied_back_into_steps():
    settings = SETTINGS.model_copy(update={"feature_set": "v2"})
    hist = days(WEEK)
    cap = compute_cap(hist, START + dt.timedelta(days=10), EmpiricalPredictor(), settings, PARAMS)
    # The stand-in predicts a ratio near 1 times the person's 14-day median (about 6,900).
    assert cap.source == "tabpfn" and 1_000 <= cap.value <= 20_000
    assert cap.p50 > 2_000

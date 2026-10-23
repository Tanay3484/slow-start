"""Features for predicting a day's steps from earlier days only (design section 6).

Every feature for day `d` uses days strictly before `d`; `tests/test_prediction.py` proves it. Missing
lags are NaN, which TabPFN handles natively.

Two feature sets exist, chosen on a validation window before the final evaluation (see results/):

- `v1`: raw steps (lags, means). One pooled model has to learn every person's scale.
- `v2`: everything relative to the person's own 14-day median, and the model predicts a ratio that is
  multiplied back. Pooling across people then shares what is common (the shape of a week) and leaves the
  scale to each person.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from slowstart.models import DayResult

FEATURES = ("lag1", "lag2", "lag3", "mean7", "median14", "min7", "weekday", "weekend")
FEATURES_V2 = (
    "lag1_r", "lag2_r", "lag3_r", "mean7_r", "min7_r", "std14_r", "low_share7",
    "weekday", "weekend", "log_scale",
)  # fmt: skip
MIN_RECENT = 3  # worn days needed in the last 7


def steps_map(days: Sequence[DayResult]) -> dict[dt.date, int]:
    """Worn days only. Missing and excused-without-steps days are left out."""
    return {d.date: d.steps for d in days if d.steps is not None}


def _window(steps: Mapping[dt.date, int], day: dt.date, n: int) -> list[int]:
    return [s for d, s in steps.items() if 0 < (day - d).days <= n]


def day_features(steps: Mapping[dt.date, int], day: dt.date) -> list[float] | None:
    """v1 feature vector for `day`, or None when the last week is too thin to say anything."""
    last7 = _window(steps, day, 7)
    last14 = _window(steps, day, 14)
    if len(last7) < MIN_RECENT:
        return None

    def lag(k: int) -> float:
        value = steps.get(day - dt.timedelta(days=k))
        return float(value) if value is not None else float("nan")

    return [
        lag(1), lag(2), lag(3),
        float(np.mean(last7)), float(np.median(last14)), float(np.min(last7)),
        float(day.weekday()), 1.0 if day.weekday() >= 5 else 0.0,
    ]  # fmt: skip


def day_features_v2(steps: Mapping[dt.date, int], day: dt.date) -> tuple[list[float], float] | None:
    """v2 features and the scale (the 14-day median) that turns a predicted ratio back into steps."""
    last7 = _window(steps, day, 7)
    last14 = _window(steps, day, 14)
    if len(last7) < MIN_RECENT:
        return None
    scale = float(np.median(last14))
    if scale <= 0:
        return None

    def lag(k: int) -> float:
        value = steps.get(day - dt.timedelta(days=k))
        return value / scale if value is not None else float("nan")

    feats = [
        lag(1), lag(2), lag(3),
        float(np.mean(last7)) / scale, float(np.min(last7)) / scale,
        float(np.std(last14)) / scale, float(np.mean([s < 0.7 * scale for s in last7])),
        float(day.weekday()), 1.0 if day.weekday() >= 5 else 0.0, float(np.log(scale)),
    ]  # fmt: skip
    return feats, scale


@dataclass(frozen=True)
class FeatureSet:
    name: str
    names: tuple[str, ...]
    # (steps before the day, day) -> (features, scale) or None. The target is steps / scale.
    features: Callable[[Mapping[dt.date, int], dt.date], tuple[list[float], float] | None]

    def rows(self, steps: Mapping[dt.date, int]) -> list[tuple[dt.date, list[float], float, float]]:
        """(day, features, target / scale, scale) for every worn day with enough history behind it."""
        out = []
        for day in sorted(steps):
            got = self.features({d: s for d, s in steps.items() if d < day}, day)
            if got is not None:
                feats, scale = got
                out.append((day, feats, steps[day] / scale, scale))
        return out


def _v1(steps: Mapping[dt.date, int], day: dt.date) -> tuple[list[float], float] | None:
    feats = day_features(steps, day)
    return None if feats is None else (feats, 1.0)


FEATURE_SETS: dict[str, FeatureSet] = {
    "v1": FeatureSet("v1", FEATURES, _v1),
    "v2": FeatureSet("v2", FEATURES_V2, day_features_v2),
}


def training_rows(steps: Mapping[dt.date, int]) -> list[tuple[dt.date, list[float], float]]:
    """v1 rows: (day, features, steps) for every worn day that has enough history behind it."""
    return [(d, f, t) for d, f, t, _ in FEATURE_SETS["v1"].rows(steps)]

"""Features for predicting a day's steps from earlier days only (design section 6).

Every feature for day `d` uses days strictly before `d`; `tests/test_features.py` proves it. Missing
lags are NaN, which TabPFN handles natively.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence

import numpy as np

from slowstart.models import DayResult

FEATURES = ("lag1", "lag2", "lag3", "mean7", "median14", "min7", "weekday", "weekend")
MIN_RECENT = 3  # worn days needed in the last 7


def steps_map(days: Sequence[DayResult]) -> dict[dt.date, int]:
    """Worn days only. Missing and excused-without-steps days are left out."""
    return {d.date: d.steps for d in days if d.steps is not None}


def day_features(steps: Mapping[dt.date, int], day: dt.date) -> list[float] | None:
    """Feature vector for `day`, or None when the last week is too thin to say anything."""
    last7 = [s for d, s in steps.items() if 0 < (day - d).days <= 7]
    last14 = [s for d, s in steps.items() if 0 < (day - d).days <= 14]
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


def training_rows(steps: Mapping[dt.date, int]) -> list[tuple[dt.date, list[float], float]]:
    """(day, features, steps) for every worn day that has enough history behind it."""
    rows = []
    for day in sorted(steps):
        feats = day_features(steps, day)
        if feats is not None:
            rows.append((day, feats, float(steps[day])))
    return rows

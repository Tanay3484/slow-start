"""The cap (TCP's "receiver window"): the most a person will probably manage tomorrow (R1.7, R1.8).

The goal is `min(window, cap)`. The cap is TabPFN's 30th percentile for the day, so the goal is
reached about 7 days in 10. If the predictor is off or fails, the cap falls back to 80% of the
trailing 14-day median and says so.
"""

from __future__ import annotations

import csv
import datetime as dt
import logging
from collections.abc import Sequence
from functools import lru_cache
from importlib import resources

import numpy as np

from slowstart.config import Settings
from slowstart.controllers.policies import clamp_goal, fallback_window
from slowstart.models import Cap, DayResult, StepParams
from slowstart.prediction.features import FEATURE_SETS, steps_map
from slowstart.prediction.predictor import Predictor

log = logging.getLogger("slowstart.cap")
ROUND_TO = 50


@lru_cache
def load_prior(feature_set: str = "v1") -> tuple[np.ndarray, np.ndarray]:
    """The bundled public rows (Kaggle Fitbit set, CC0, ids dropped): a cold start for new people.
    Rows are in the feature set's own space, and the target is already divided by the scale."""
    path = resources.files("slowstart.data").joinpath(f"prior_steps_{feature_set}.csv")
    rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
    body = np.array(rows[1:], dtype=float)
    n = len(FEATURE_SETS[feature_set].names)
    return body[:, :n], body[:, n]


def prior_sample(n: int, seed: int = 0, feature_set: str = "v1") -> tuple[np.ndarray, np.ndarray]:
    x, y = load_prior(feature_set)
    if n >= len(x):
        return x, y
    idx = np.random.default_rng(seed).choice(len(x), size=n, replace=False)
    return x[idx], y[idx]


def _round(value: float, params: StepParams) -> int:
    return clamp_goal(round(value / ROUND_TO) * ROUND_TO, params)


def median_cap(history: Sequence[DayResult], today: dt.date, params: StepParams) -> Cap:
    return Cap(value=fallback_window(history, today, params), source="median")


def compute_cap(
    history: Sequence[DayResult],
    today: dt.date,
    predictor: Predictor | None,
    settings: Settings,
    params: StepParams,
) -> Cap:
    steps = steps_map([d for d in history if d.date < today])
    if len(steps) < settings.cap_min_days:
        return Cap(source="none")
    if predictor is None:
        return median_cap(history, today, params)
    try:
        fs = FEATURE_SETS[settings.feature_set]
        got = fs.features(steps, today)
        if got is None:
            return median_cap(history, today, params)
        x_test, scale = got
        own = fs.rows(steps)
        x_prior, y_prior = prior_sample(settings.prior_rows, feature_set=fs.name)
        x_train = np.vstack([x_prior, np.array([r[1] for r in own])]) if own else x_prior
        y_train = np.concatenate([y_prior, np.array([r[2] for r in own])]) if own else y_prior
        q = predictor.quantiles(x_train, y_train, np.array([x_test]), [settings.cap_quantile, 0.5])
        p30, p50 = float(q[0][0]) * scale, float(q[1][0]) * scale
        return Cap(
            value=_round(p30, params),
            p30=_round(p30, params),
            p50=_round(p50, params),
            source="tabpfn",
        )
    except Exception:  # the cap must never take the app down
        log.exception("predictor failed; using the median cap")
        return median_cap(history, today, params)

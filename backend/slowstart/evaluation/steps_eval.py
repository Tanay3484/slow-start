"""Walk-forward evaluation of step-goal policies (R8.1, R8.3, design section 10).

Every policy sets each day's goal seeing only the days before it, then the day is revealed. A policy
is scored on the held-out window (the last `window_days` calendar days of the data) on exactly the
person-days where every policy produced a goal, so the comparison is like for like.

TabPFN is fitted once per calendar day on everyone's rows from *earlier* days (never the day itself),
and the predictions are cached. The cap is therefore the same for every policy that uses it.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from slowstart.config import Settings
from slowstart.controllers import policies, steps
from slowstart.models import DayResult, StepParams
from slowstart.prediction.cap import _round
from slowstart.prediction.features import day_features, steps_map, training_rows
from slowstart.prediction.predictor import Predictor

log = logging.getLogger("slowstart.eval")

# (person, history-before-day, day) -> goal or None
Policy = Callable[[str, Sequence[DayResult], dt.date], "int | None"]
QUANTILES = (0.30, 0.50)


@dataclass(frozen=True)
class Scored:
    person: str
    day: dt.date
    steps: int
    goal: int
    reference: float  # the person's median steps before the window


def calendar_caps(
    people: Mapping[str, Sequence[DayResult]],
    predictor: Predictor,
    settings: Settings,
    min_pool: int = 50,
    cache_path: Path | None = None,
    progress: Callable[[str], None] = lambda _: None,
) -> dict[tuple[str, dt.date], tuple[float, float]]:
    """(person, day) -> (p30, p50) of that day's steps, fitted on rows from earlier days only."""
    series = {p: steps_map(days) for p, days in people.items()}
    pool_rows = sorted(
        ((d, feats, target) for s in series.values() for d, feats, target in training_rows(s)),
        key=lambda r: r[0],
    )
    cache: dict[str, list[float]] = {}
    if cache_path and cache_path.exists():
        cache = json.loads(cache_path.read_text())

    out: dict[tuple[str, dt.date], tuple[float, float]] = {}
    all_days = sorted({d.date for days in people.values() for d in days})
    for i, day in enumerate(all_days):
        wanted: list[tuple[str, list[float]]] = []
        for p, days in people.items():
            if day not in {d.date for d in days}:
                continue
            past = {d: s for d, s in series[p].items() if d < day}
            if len(past) < settings.cap_min_days:
                continue
            feats = day_features(past, day)
            if feats is not None:
                wanted.append((p, feats))
        if not wanted:
            continue
        keys = [f"{p}|{day.isoformat()}" for p, _ in wanted]
        if all(k in cache for k in keys):
            for (p, _), k in zip(wanted, keys, strict=True):
                out[(p, day)] = (cache[k][0], cache[k][1])
            continue
        train = [r for r in pool_rows if r[0] < day]
        if len(train) < min_pool:
            continue
        x_train = np.array([r[1] for r in train], dtype=float)
        y_train = np.array([r[2] for r in train], dtype=float)
        x_test = np.array([w[1] for w in wanted], dtype=float)
        q = predictor.quantiles(x_train, y_train, x_test, list(QUANTILES))
        for j, ((p, _), k) in enumerate(zip(wanted, keys, strict=True)):
            cache[k] = [float(q[0][j]), float(q[1][j])]
            out[(p, day)] = (cache[k][0], cache[k][1])
        progress(f"  caps {i + 1}/{len(all_days)} {day} ({len(train)} rows, {len(wanted)} people)")
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache))
    return out


def simulate(person: str, days: Sequence[DayResult], policy: Policy) -> list[DayResult]:
    """Run one policy over one person: it sets the goal, then the day's steps are revealed."""
    out: list[DayResult] = []
    for d in sorted(days, key=lambda x: x.date):
        goal = policy(person, list(out), d.date)
        out.append(DayResult(date=d.date, steps=d.steps, goal=goal))
    return out


def window_start(people: Mapping[str, Sequence[DayResult]], window_days: int) -> dt.date:
    last = max(d.date for days in people.values() for d in days)
    return last - dt.timedelta(days=window_days - 1)


def score(
    people: Mapping[str, Sequence[DayResult]],
    policy_map: Mapping[str, Policy],
    start: dt.date,
    min_history: int = 7,
) -> tuple[dict[str, list[Scored]], dict]:
    """Scores every policy on the person-days where all of them set a goal."""
    sims = {
        name: {p: simulate(p, days, pol) for p, days in people.items()}
        for name, pol in policy_map.items()
    }
    refs: dict[str, float] = {}
    for p, days in people.items():
        before = [d.steps for d in days if d.date < start and d.steps is not None]
        if before:
            refs[p] = float(np.median(before))

    keys: set[tuple[str, dt.date]] | None = None
    for per_person in sims.values():
        ok = {
            (p, d.date)
            for p, rows in per_person.items()
            for d in rows
            if d.date >= start
            and d.steps is not None
            and d.goal is not None
            and p in refs
            and sum(1 for x in rows if x.date < d.date and x.steps is not None) >= min_history
        }
        keys = ok if keys is None else keys & ok

    keys = keys or set()
    scored: dict[str, list[Scored]] = {}
    for name, per_person in sims.items():
        by_key = {(p, d.date): d for p, rows in per_person.items() for d in rows}
        scored[name] = [
            Scored(p, day, by_key[(p, day)].steps, by_key[(p, day)].goal, refs[p])
            for p, day in sorted(keys)
        ]
    meta = {
        "window_start": start.isoformat(),
        "person_days": len(keys),
        "people": len({p for p, _ in keys}),
    }
    return scored, meta


def make_policies(
    caps: Mapping[tuple[str, dt.date], tuple[float, float]],
    params: StepParams,
    include_controller: bool = True,
) -> dict[str, Policy]:
    def cap_for(person: str, day: dt.date) -> int | None:
        q = caps.get((person, day))
        return _round(q[0], params) if q else None

    def fixed(person, history, day):
        return policies.fixed_10k(history, day)

    def median(person, history, day):
        return policies.trailing_median(history, day, params)

    def own_p30(person, history, day):
        return policies.own_quantile(history, day, 0.30, params)

    def tabpfn_cap(person, history, day):
        return cap_for(person, day)

    out: dict[str, Policy] = {
        "fixed_10000": fixed,
        "trailing_median_28d": median,
        "own_p30_28d": own_p30,
        "tabpfn_p30_cap": tabpfn_cap,
    }
    if include_controller:

        def window(history):
            return steps.next_window(history, params).window

        def controller(person, history, day):
            return window(history)

        def controller_capped(person, history, day):
            w, c = window(history), cap_for(person, day)
            return w if c is None else min(w, c)

        out["controller"] = controller
        out["controller_tabpfn_cap"] = controller_capped
    return out


def controller_is_written(params: StepParams) -> bool:
    try:
        steps.next_window([], params)
    except NotImplementedError:
        return False
    except Exception:  # written, maybe wrong; the tests will say
        return True
    return True


def met_vector(rows: Sequence[Scored]) -> list[int]:
    return [int(r.steps >= r.goal) for r in rows]

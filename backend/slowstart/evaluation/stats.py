"""H3: evaluation statistics. These two functions are Tanay's to write by hand.

The contract, with edge cases, is in specs/001-slow-start-mvp/tasks.md under H3. Until they are
written the evaluation prints "locked" for the columns that need them; the goal-met rates do not.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def goal_level(goals: Sequence[float], reference: Sequence[float]) -> float:
    """Mean of goal / reference over pairs with reference > 0 (NaN if there are none).

    The guardrail against winning by setting tiny goals."""
    ratios = [g / r for g, r in zip(goals, reference, strict=True) if r > 0]

    if len(ratios) == 0:
        return float("nan")

    return float(np.mean(ratios))


def paired_bootstrap(
    a: Sequence[int],
    b: Sequence[int],
    groups: Sequence[str],
    n: int = 2000,
    seed: int = 0,
) -> tuple[float, float, float]:
    """(mean(a) - mean(b), lo, hi): a 95% interval from resampling people, not days.

    `a` and `b` are 0/1 "goal met" outcomes for two policies on the same person-days, in the same
    order; `groups` gives each day's person."""

    if (len(a) == 0 or len(b) == 0 or len(groups) == 0) or (
        len(a) != len(b) or len(b) != len(groups)
    ):
        raise ValueError("Bad Inputs")

    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)

    diff = a_arr.mean() - b_arr.mean()

    # Each person's days, as positions in the lists. Resampling people (not days) keeps a person's
    # days together, because days from the same person are not independent.
    people = sorted(set(groups))
    days_of = {p: [i for i, g in enumerate(groups) if g == p] for p in people}

    rng = np.random.default_rng(seed)  # a fixed seed: the same answer every run
    samples = []
    for _ in range(n):
        picked = rng.choice(people, size=len(people), replace=True)

        positions = []
        for p in picked:
            positions.extend(days_of[p])

        samples.append(a_arr[positions].mean() - b_arr[positions].mean())

    lo, hi = np.percentile(samples, 2.5), np.percentile(samples, 97.5)

    return float(diff), float(lo), float(hi)

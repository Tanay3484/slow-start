"""H3: evaluation statistics. These two functions are Tanay's to write by hand.

The contract, with edge cases, is in specs/001-slow-start-mvp/tasks.md under H3. Until they are
written the evaluation prints "locked" for the columns that need them; the goal-met rates do not.
"""

from __future__ import annotations

from collections.abc import Sequence


def goal_level(goals: Sequence[float], reference: Sequence[float]) -> float:
    """Mean of goal / reference over pairs with reference > 0 (NaN if there are none).

    The guardrail against winning by setting tiny goals."""
    raise NotImplementedError("H3: goal_level is yours to write (see tasks.md)")


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
    raise NotImplementedError("H3: paired_bootstrap is yours to write (see tasks.md)")

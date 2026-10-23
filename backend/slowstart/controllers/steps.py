"""H1: the step controller. This one is Tanay's to write by hand.

The contract, with a worked example, is in specs/001-slow-start-mvp/tasks.md under H1.
Until it is written, `NotImplementedError` makes `controllers.guard` serve a baseline and the app
shows a "fallback" badge. Do not catch the error here.
"""

from __future__ import annotations

from collections.abc import Sequence

from slowstart.models import DayResult, StepDecision, StepParams


def next_window(days: Sequence[DayResult], params: StepParams) -> StepDecision:
    """Return the controller's window (goal before any cap) for the day after `days`."""
    raise NotImplementedError("H1: the step controller is yours to write (see tasks.md)")

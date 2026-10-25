"""H1: the step controller. This one is Tanay's to write by hand.

The contract, with a worked example, is in specs/001-slow-start-mvp/tasks.md under H1.
Until it is written, `NotImplementedError` makes `controllers.guard` serve a baseline and the app
shows a "fallback" badge. Do not catch the error here.

Skeleton: the structure is filled in; every line marked TODO is yours. When all of them are done,
delete the `raise NotImplementedError` line and run:
    backend/.venv/Scripts/python -m pytest backend/tests/test_human_levels.py -k H1
"""

from __future__ import annotations

from collections.abc import Sequence

from slowstart.models import DayResult, StepDecision, StepParams


def next_window(days: Sequence[DayResult], params: StepParams) -> StepDecision:
    """Return the controller's window (goal before any cap) for the day after `days`."""
    window = params.start  # TCP's congestion window: starts small
    threshold: int | None = None  # TCP's ssthresh: unknown until the first miss
    last_was_miss = False  # for the phase at the end

    for day in sorted(days, key=lambda d: d.date):  # oldest first, whatever order they came in
        if (day.excused) or (day.steps is None) or (day.goal is None):
            continue

        met = day.steps >= day.goal

        if met:
            if threshold is None or window < threshold:
                window *= 2
                if threshold is not None:
                    window = min(window, threshold)
            else:
                window += params.ai
            last_was_miss = False
        else:
            threshold = window = max(window // 2, params.floor)
            last_was_miss = True

        window = max(min(window, params.ceiling), params.floor)

    if last_was_miss:
        phase = "recovering"
    elif threshold is None or window < threshold:
        phase = "slow_start"
    else:
        phase = "cruising"

    return StepDecision(window=window, threshold=threshold, phase=phase)

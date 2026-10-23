"""H2: the exercise controller. This one is Tanay's to write by hand.

The contract, with a worked example, is in specs/001-slow-start-mvp/tasks.md under H2.
"""

from __future__ import annotations

from collections.abc import Sequence

from slowstart.models import ExerciseParams, Session, Target


def next_target(sessions: Sequence[Session], exercise: str, params: ExerciseParams) -> Target:
    """Return the sets, reps and load for the next session of `exercise`."""
    raise NotImplementedError("H2: the exercise controller is yours to write (see tasks.md)")

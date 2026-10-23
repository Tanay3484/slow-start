"""Pick one real person from the public Fitbit set to play in the app's demo, and write their daily steps
to app/src/demo/persona.json. The set is anonymous and CC0; no id is written.

    python -I scripts/build_demo_persona.py

The chosen person has most days worn and enough ups and downs that the demo shows both a win streak and
a miss, which is what makes the halving visible.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from slowstart.evaluation.fitbit import load_fitbit

OUT = Path("app/src/demo/persona.json")


def main() -> int:
    people = load_fitbit()
    scored = []
    for pid, days in people.items():
        worn = [d.steps for d in days if d.steps is not None]
        if len(worn) < 40:
            continue
        cv = statistics.pstdev(worn) / statistics.mean(worn)
        scored.append((cv if 0.35 <= cv <= 0.7 else 0, len(worn), pid))
    scored.sort(reverse=True)
    _, _, pid = scored[0]
    days = people[pid]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "source": "Kaggle 'Fitbit Fitness Tracker Data' (Mobius), CC0. One anonymous person.",
                "days": [{"date": d.date.isoformat(), "steps": d.steps} for d in days],
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    worn = [d.steps for d in days if d.steps is not None]
    print(
        f"wrote {len(days)} days ({len(worn)} worn), median {statistics.median(worn):.0f} steps -> {OUT}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

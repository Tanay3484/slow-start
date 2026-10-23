"""Build backend/slowstart/data/prior_steps.csv: feature rows from the public Fitbit set, with ids and
dates dropped. It is the cold start for a person with little history of their own.

    python -I scripts/build_prior.py

The evaluation does NOT use this file (it contains the test days); it pools only earlier days.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from slowstart.evaluation.fitbit import load_fitbit
from slowstart.prediction.features import FEATURES, steps_map, training_rows

OUT = Path("backend/slowstart/data/prior_steps.csv")


def main() -> int:
    people = load_fitbit()
    rows = []
    for days in people.values():
        for _, feats, target in training_rows(steps_map(days)):
            rows.append([*feats, target])
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([*FEATURES, "target"])
        writer.writerows([["nan" if v != v else round(v, 3) for v in r] for r in rows])
    print(f"wrote {len(rows)} rows from {len(people)} people to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

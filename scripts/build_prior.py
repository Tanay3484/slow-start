"""Build backend/slowstart/data/prior_steps.csv: feature rows from the public Fitbit set, with ids and
dates dropped. It is the cold start for a person with little history of their own.

    python -I scripts/build_prior.py

The evaluation does NOT use this file (it contains the test days); it pools only earlier days.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

from slowstart.evaluation.fitbit import load_fitbit
from slowstart.prediction.features import FEATURE_SETS, steps_map

OUT_DIR = Path("backend/slowstart/data")


def main() -> int:
    people = load_fitbit()
    for name, fs in FEATURE_SETS.items():
        rows = []
        for days in people.values():
            for _, feats, target, _ in fs.rows(steps_map(days)):
                rows.append([*feats, target])
        out = OUT_DIR / f"prior_steps_{name}.csv"
        with out.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([*fs.names, "target"])
            writer.writerows([["nan" if math.isnan(v) else round(v, 4) for v in r] for r in rows])
        print(f"wrote {len(rows)} rows from {len(people)} people to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

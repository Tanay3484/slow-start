"""Load the public Kaggle Fitbit set ("Fitbit Fitness Tracker Data", Mobius, listed CC0) for the
evaluation and the bundled prior.

Download it with `kaggle datasets download -d arashnic/fitbit -p data/raw/fitbit`. The zip holds two
Fitabase exports (2016-03-12 to 04-11 and 04-12 to 05-12) with overlapping people. Days with 0 steps
are a tracker that was not worn, so they become missing (steps = None).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from slowstart.data.steps_import import people_in_fitabase
from slowstart.models import DayResult

DEFAULT_ZIP = Path("data/raw/fitbit/fitbit.zip")


def load_fitbit(zip_path: Path | str = DEFAULT_ZIP) -> dict[str, list[DayResult]]:
    """People keyed by their (anonymous) Fitabase id, days sorted, exports merged."""
    merged: dict[str, dict] = {}
    with zipfile.ZipFile(zip_path) as z:
        names = sorted(n for n in z.namelist() if n.endswith("dailyActivity_merged.csv"))
        if not names:
            raise FileNotFoundError("No dailyActivity_merged.csv in that zip")
        for name in names:
            text = z.read(name).decode("utf-8-sig")
            for pid, days in people_in_fitabase(text).items():
                bucket = merged.setdefault(pid, {})
                for d in days:
                    bucket[d.date] = d
    return {pid: [days[k] for k in sorted(days)] for pid, days in merged.items()}

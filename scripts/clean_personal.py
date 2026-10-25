"""Clean one person's exports for the personal backtest, and say what was kept and why.

    python -I scripts/clean_personal.py data/private

Reads `Takeout/Fit/Daily activity metrics/Daily activity metrics.csv` and `hevy.csv` from that folder
and writes `steps_clean.csv` (date,steps) next to them. The rules were fixed before the backtest ran:

- Steps come from the daily summary CSV, which Google has already merged across the phone and the
  watch. The per-device files in `All Data` overlap, so adding them up would count steps twice.
- Days from `--since` on (default 2024-01-01: the first date after which every day has a row).
- The last day is dropped: the export ran during it, so it is a partial day.
- Under `--min-steps` (default 500, the importer's `MIN_STEPS`) is a phone or watch that was not carried,
  not a real day. It is written as 0. The app's importer applies the same rule to every upload.

Hevy needs no file of its own: the importer already drops warm-ups, empty sets, assisted and weighted
bodyweight variants and the exercises the app does not support. This prints what it kept.
Nothing personal is written outside the given folder.
"""

from __future__ import annotations

import argparse
import datetime as dt
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from slowstart.data.hevy_import import parse_hevy
from slowstart.data.steps_import import MIN_STEPS, parse_steps

FIT_CSV = Path("Takeout/Fit/Daily activity metrics/Daily activity metrics.csv")


def clean_steps(
    text: str, since: dt.date, min_steps: int
) -> tuple[list[tuple[dt.date, int]], dict]:
    imported = parse_steps(text)
    recorded = {d.date: d.steps for d in imported.days}
    last = max(recorded) - dt.timedelta(days=1)  # the export day is partial
    rows: list[tuple[dt.date, int]] = []
    report = {
        "format": imported.format,
        "first_in_file": min(recorded),
        "dropped_export_day": max(recorded),
    }
    missing = low = 0
    day = since
    while day <= last:
        steps = recorded.get(day)
        if steps is None:
            missing += 1
            steps = 0
        elif steps < min_steps:
            low += 1
            steps = 0
        rows.append((day, steps))
        day += dt.timedelta(days=1)
    report |= {"days": len(rows), "no_row_or_blank": missing, f"under_{min_steps}": low}
    return rows, report


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="the folder holding Takeout/ and hevy.csv (data/private)")
    ap.add_argument("--since", default="2024-01-01")
    ap.add_argument("--min-steps", type=int, default=MIN_STEPS)
    args = ap.parse_args()
    folder = Path(args.folder)

    rows, report = clean_steps(
        (folder / FIT_CSV).read_text(encoding="utf-8-sig"),
        dt.date.fromisoformat(args.since),
        args.min_steps,
    )
    out = folder / "steps_clean.csv"
    out.write_text(
        "date,steps\n" + "".join(f"{d.isoformat()},{s}\n" for d, s in rows), encoding="utf-8"
    )
    print(f"Steps -> {out}")
    for k, v in report.items():
        print(f"  {k}: {v}")
    by_year = defaultdict(list)
    for d, s in rows:
        if s:
            by_year[d.year].append(s)
    for year, vals in sorted(by_year.items()):
        print(f"  {year}: {len(vals)} days counted, median {statistics.median(vals):,.0f}")

    hevy = folder / "hevy.csv"
    if hevy.exists():
        imp = parse_hevy(hevy.read_text(encoding="utf-8-sig"))
        print(f"\nHevy: {len(imp.sessions)} sessions of supported lifts, {imp.first} to {imp.last}")
        print(f"  per exercise: {imp.exercises}")
        print(f"  empty sets skipped: {imp.skipped_rows}; {'; '.join(imp.warnings)}")
        print(f"  most-logged left out: {list(imp.unsupported)[:8]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

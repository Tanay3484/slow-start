"""Read daily steps from the formats a person can realistically hand over (R3.1, R3.3).

Three formats, detected from the content:

1. Fitbit / Google Takeout "Global Export Data" `steps-*.json`: a list of per-minute
   `{"dateTime": "MM/DD/YY HH:MM:SS", "value": "12"}` records, summed per day.
2. Fitabase `dailyActivity_merged.csv` (the public Kaggle set): `Id, ActivityDate, TotalSteps`.
3. Any CSV with a date column and a steps column (`date,steps`).

A day with 0 steps is a tracker that was not worn, not a real zero, so it becomes missing and is counted.
Everything is parsed in memory; nothing is stored (R3.4). Real Takeout layouts change between exports,
so unrecognised input raises `ImportError_` with a message that says what was expected.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
from collections import defaultdict

from pydantic import BaseModel

from slowstart.models import DayResult

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%m-%Y", "%d %b %Y", "%b %d, %Y")


class ImportError_(ValueError):  # noqa: N801 - avoids shadowing the builtin ImportError
    pass


class ImportedSteps(BaseModel):
    days: list[DayResult]
    format: str
    not_worn: int
    first: dt.date | None
    last: dt.date | None
    warnings: list[str] = []


def parse_date(text: str) -> dt.date:
    text = text.strip().strip('"')
    if "T" in text or (" " in text and ":" in text):
        head = text.replace("T", " ").split(" ")[0]
        if head.count("-") == 2 or head.count("/") == 2:
            text = head
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ImportError_(f"Could not read the date {text!r}")


def _finish(totals: dict[dt.date, int], fmt: str, warnings: list[str]) -> ImportedSteps:
    days = [DayResult(date=d, steps=(s if s > 0 else None)) for d, s in sorted(totals.items())]
    not_worn = sum(1 for d in days if d.steps is None)
    if not days:
        raise ImportError_("No days found in that file")
    if not_worn:
        warnings.append(f"{not_worn} day(s) with 0 steps were treated as 'tracker not worn'")
    return ImportedSteps(
        days=days,
        format=fmt,
        not_worn=not_worn,
        first=days[0].date,
        last=days[-1].date,
        warnings=warnings,
    )


def _from_takeout_json(text: str) -> ImportedSteps:
    try:
        rows = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ImportError_("That looks like JSON but could not be read") from exc
    if (
        not isinstance(rows, list)
        or not rows
        or not isinstance(rows[0], dict)
        or ("dateTime" not in rows[0])
    ):
        raise ImportError_("Expected a Fitbit export: a list of {dateTime, value} records")
    totals: dict[dt.date, int] = defaultdict(int)
    for row in rows:
        try:
            totals[parse_date(str(row["dateTime"]))] += int(float(row["value"]))
        except (KeyError, TypeError, ValueError, ImportError_):
            continue
    return _finish(totals, "fitbit_takeout_json", [])


def _find(header: list[str], *names: str) -> int | None:
    lowered = [h.strip().lower() for h in header]
    for name in names:
        if name in lowered:
            return lowered.index(name)
    return None


def people_in_fitabase(text: str) -> dict[str, list[DayResult]]:
    """For the evaluation: one list of days per person in a Fitabase export."""
    reader = csv.reader(io.StringIO(text.lstrip("﻿")))
    header = next(reader, [])
    i_id, i_date, i_steps = (
        _find(header, "id"),
        _find(header, "activitydate"),
        _find(header, "totalsteps"),
    )
    if None in (i_id, i_date, i_steps):
        raise ImportError_("Expected Fitabase columns Id, ActivityDate, TotalSteps")
    people: dict[str, dict[dt.date, int]] = defaultdict(dict)
    for row in reader:
        if len(row) <= max(i_id, i_date, i_steps):
            continue
        people[row[i_id]][parse_date(row[i_date])] = int(float(row[i_steps]))
    return {
        pid: [DayResult(date=d, steps=(s if s > 0 else None)) for d, s in sorted(days.items())]
        for pid, days in people.items()
    }


def _from_csv(text: str) -> ImportedSteps:
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    if not rows:
        raise ImportError_("The file is empty")
    header = rows[0]
    i_date = _find(header, "date", "activitydate", "day", "datetime", "timestamp")
    i_steps = _find(header, "steps", "totalsteps", "step_count", "value")
    if i_date is None or i_steps is None:
        raise ImportError_("Expected a CSV with a date column and a steps column")
    i_id = _find(header, "id")
    if i_id is not None and len({r[i_id] for r in rows[1:] if len(r) > i_id}) > 1:
        raise ImportError_("That file has several people in it; import one person's steps")
    totals: dict[dt.date, int] = defaultdict(int)
    bad = 0
    for row in rows[1:]:
        try:
            totals[parse_date(row[i_date])] += int(float(row[i_steps]))
        except (IndexError, ValueError, ImportError_):
            bad += 1
    warnings = [f"{bad} row(s) could not be read and were skipped"] if bad else []
    fmt = "fitabase_csv" if _find(header, "activitydate") is not None else "csv"
    return _finish(totals, fmt, warnings)


def parse_steps(text: str) -> ImportedSteps:
    body = text.lstrip("﻿").lstrip()
    if body.startswith("["):
        return _from_takeout_json(body)
    return _from_csv(body)

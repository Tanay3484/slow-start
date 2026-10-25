"""Read a Hevy CSV export into sessions of the exercises the app supports (R3.2).

Hevy's export has one row per set: title, start_time, end_time, description, exercise_title,
superset_id, exercise_notes, set_index, set_type, weight_kg (or weight_lbs), reps, distance_*,
duration_seconds, rpe. Warm-up sets are dropped. Exercises the app does not support are counted and
reported, never silently lost. Parsed in memory; nothing is stored (R3.4).
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import re
from collections import defaultdict

from pydantic import BaseModel

from slowstart.models import Session, SetResult

LBS_TO_KG = 0.45359237
HEVY_DATE_FORMATS = (
    "%d %b %Y, %H:%M",
    "%b %d, %Y, %I:%M %p",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
)

# First match wins, so the specific patterns come before the general ones.
EXERCISE_PATTERNS: list[tuple[str, str]] = [
    (r"\bgoblet squat", "goblet_squat"),
    (r"(body ?weight|air) squat", "bodyweight_squat"),
    (
        r"\b(romanian|stiff|sumo|trap bar|single leg|rack pull)\b.*deadlift|deadlift.*\b(romanian|stiff)\b",
        "",
    ),
    (r"^deadlift( \(barbell\))?$", "deadlift"),
    (r"^(back )?squat( \(barbell\))?$", "squat"),
    (r"^bench press( \(barbell\))?$", "bench_press"),
    (r"^bench press \(dumbbell\)$|^dumbbell bench press$", "dumbbell_bench_press"),
    (r"^(overhead press|standing military press|military press)( \(barbell\))?$", "overhead_press"),
    (
        r"^(shoulder press|seated shoulder press|overhead press|seated overhead press) \(dumbbell\)$",
        "dumbbell_shoulder_press",
    ),
    (r"^(bent over row|barbell row|pendlay row)( \(barbell\))?$", "barbell_row"),
    (
        r"^(dumbbell row|one arm dumbbell row|bent over row \(dumbbell\)|single arm row \(dumbbell\))$",
        "dumbbell_row",
    ),
    (r"^push[- ]?ups?$", "push_up"),
    (r"^pull[- ]?ups?$", "pull_up"),
    # Bodyweight moves are scored on reps alone, so assisted and weighted variants stay out.
    (r"^(tricep|triceps|chest)? ?dips?$", "dip"),
]


def canonical_exercise(title: str) -> str | None:
    t = re.sub(r"\s+", " ", title.strip().lower())
    for pattern, ident in EXERCISE_PATTERNS:
        if re.search(pattern, t):
            return ident or None
    return None


class ImportedWorkouts(BaseModel):
    sessions: list[Session]
    exercises: dict[str, int]
    unsupported: dict[str, int]
    skipped_rows: int
    first: dt.date | None
    last: dt.date | None
    warnings: list[str] = []


class HevyImportError(ValueError):
    pass


def parse_hevy_date(text: str) -> dt.date:
    text = text.strip().strip('"')
    for fmt in HEVY_DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise HevyImportError(f"Could not read the workout date {text!r}")


def _number(text: str) -> float | None:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def parse_hevy(text: str) -> ImportedWorkouts:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    fields = [f.strip().lower() for f in (reader.fieldnames or [])]
    if not {"start_time", "exercise_title", "reps"} <= set(fields):
        raise HevyImportError(
            "Expected a Hevy export with start_time, exercise_title and reps columns"
        )
    lbs = "weight_lbs" in fields and "weight_kg" not in fields

    grouped: dict[tuple[dt.date, str], list[SetResult]] = defaultdict(list)
    unsupported: dict[str, int] = defaultdict(int)
    skipped = 0
    for raw in reader:
        row = {k.strip().lower(): v for k, v in raw.items() if k}
        if (row.get("set_type") or "normal").strip().lower() == "warmup":
            continue
        reps = _number(row.get("reps", ""))
        if reps is None or reps <= 0:
            skipped += 1
            continue
        ident = canonical_exercise(row.get("exercise_title", ""))
        if ident is None:
            unsupported[row.get("exercise_title", "?").strip() or "?"] += 1
            continue
        try:
            day = parse_hevy_date(row["start_time"])
        except (KeyError, HevyImportError):
            skipped += 1
            continue
        weight = _number(row.get("weight_lbs" if lbs else "weight_kg", ""))
        if weight is not None:
            weight = round(weight * (LBS_TO_KG if lbs else 1.0), 2)
        grouped[(day, ident)].append(SetResult(weight_kg=weight or None, reps=int(reps)))

    sessions = [
        Session(date=day, exercise=ident, sets=sets)
        for (day, ident), sets in sorted(grouped.items())
    ]
    counts: dict[str, int] = defaultdict(int)
    for s in sessions:
        counts[s.exercise] += 1
    warnings = []
    if unsupported:
        warnings.append(
            f"{sum(unsupported.values())} set(s) of unsupported exercises were left out"
        )
    return ImportedWorkouts(
        sessions=sessions,
        exercises=dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        unsupported=dict(sorted(unsupported.items(), key=lambda kv: -kv[1])[:20]),
        skipped_rows=skipped,
        first=sessions[0].date if sessions else None,
        last=sessions[-1].date if sessions else None,
        warnings=warnings,
    )

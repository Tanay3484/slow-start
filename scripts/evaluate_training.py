"""Reproduce the training results (R8.2) from a Hevy CSV export.

    python -I scripts/evaluate_training.py data/private/hevy.csv

Only aggregate numbers are written to results/training.md, so they can be committed. Anything per
session stays in results/private/ (git-ignored). The controller row says "locked" until H2 is written,
and the interval column until H3 is.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from slowstart.data.hevy_import import parse_hevy
from slowstart.evaluation import stats, training_eval
from slowstart.models import ExerciseParams

BASELINE = "repeat_last"
LABELS = {
    "repeat_last": "Repeat last session",
    "fixed_plan": "Fixed plan (+1 step every session)",
    "controller": "Controller (add a step, cut after a miss)",
}


def locked(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        return None


def table(sessions, start, params, ctl) -> tuple[list[dict], list]:
    scored = training_eval.score(sessions, training_eval.make_policies(ctl), start, params)
    base = scored[BASELINE]
    base_met = [r.met for r in base]
    groups = [r.exercise for r in base]
    rows = []
    for key, items in scored.items():
        met = [r.met for r in items]
        rows.append(
            {
                "policy": key,
                "label": LABELS[key],
                "met": sum(met) / len(met) if met else None,
                "level": sum(r.level for r in items) / len(items) if items else None,
                "vs_baseline": None
                if key == BASELINE
                else locked(stats.paired_bootstrap, met, base_met, groups),
            }
        )
    return rows, base


def build(text: str, window_days: int) -> dict:
    params = ExerciseParams()
    imported = parse_hevy(text)
    if not imported.sessions:
        raise SystemExit("No supported sessions found in that file.")
    last = max(s.date for s in imported.sessions)
    start = last - dt.timedelta(days=window_days - 1)
    ctl = training_eval.controller_is_written(params)
    rows, base = table(imported.sessions, start, params, ctl)
    top = training_eval.top_set_params(imported.sessions, start, params)
    top_rows, top_base = table(imported.sessions, start, top, ctl)
    return {
        "generated": dt.date.today().isoformat(),
        "window_start": start.isoformat(),
        "window_end": last.isoformat(),
        "sessions_loaded": len(imported.sessions),
        "exercises_loaded": imported.exercises,
        "scored_sessions": len(base),
        "scored_exercises": sorted({r.exercise for r in base}),
        "controller_written": ctl,
        "rows": rows,
        "top_set": {
            "reps": {ex: top.scheme[ex].reps for ex in sorted({r.exercise for r in top_base})},
            "scored_sessions": len(top_base),
            "rows": top_rows,
        },
    }


def pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def rows_md(rows: list[dict]) -> list[str]:
    lines = [
        "| Policy | Target met | Level vs last session | Met vs repeat-last (95% CI) |",
        "|---|---|---|---|",
    ]
    for row in rows:
        vs = row["vs_baseline"]
        text = (
            "(baseline)"
            if row["policy"] == BASELINE
            else "locked"
            if vs is None
            else f"{vs[0] * 100:+.1f} pts ({vs[1] * 100:+.1f} to {vs[2] * 100:+.1f})"
        )
        level = "n/a" if row["level"] is None else f"{row['level']:.2f}"
        lines.append(f"| {row['label']} | {pct(row['met'])} | {level} | {text} |")
    return lines


def markdown(r: dict) -> str:
    top = r["top_set"]
    reps = ", ".join(f"{ex} {n}" for ex, n in top["reps"].items())
    lines = [
        "# Training results",
        "",
        f"Generated {r['generated']}. {r['sessions_loaded']} supported sessions loaded; "
        f"{r['scored_sessions']} scored across {len(r['scored_exercises'])} exercises in "
        f"{r['window_start']} to {r['window_end']}.",
        "",
        "## The app's fixed scheme (planned before the data)",
        "",
        *rows_md(r["rows"]),
        "",
        "## Scored on the top set (R8.6, exploratory: added after the fixed scheme failed)",
        "",
        f"One working set per session at the usual top-set reps from before the window ({reps}). "
        f"{top['scored_sessions']} sessions scored.",
        "",
        *rows_md(top["rows"]),
        "",
        "**Target met**: the real next session reached the suggested sets, reps and load. **Level**: how "
        "demanding the target was compared with the last session; below 1.00 means it asked for less "
        "than last time. The interval resamples exercises, not sessions.",
        "",
        "## Limits",
        "",
        "- One person's log. The backtest replays what Tanay did *without* the app, so a suggestion can "
        "only be judged by what was done anyway.",
        "- No TabPFN here: with about a dozen exercises and a few dozen sessions each, a predictor would "
        "be fitted on too little to claim anything. It is used for steps only.",
        "- The fixed scheme (for example 3 x 8 at one weight) is rarely what a lifter who works up to a "
        "top set does, so its low level means the scheme does not fit the lifter. The top-set table was "
        "designed after seeing that, on the same log, so it is exploratory, not a held-out test.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="a Hevy CSV export (keep it outside the repo or in data/private/)")
    ap.add_argument("--out", default="results")
    ap.add_argument("--window-days", type=int, default=90)
    args = ap.parse_args()
    result = build(Path(args.csv).read_text(encoding="utf-8-sig"), args.window_days)
    out = Path(args.out)
    (out / "private").mkdir(parents=True, exist_ok=True)
    (out / "private" / "training.json").write_text(json.dumps(result, indent=2, default=str))
    (out / "training.md").write_text(markdown(result), encoding="utf-8")
    print(markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())

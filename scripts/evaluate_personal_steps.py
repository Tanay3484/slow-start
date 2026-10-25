"""The steps backtest on one person's own history (the first user), the way the app would run it.

    python -I scripts/clean_personal.py data/private
    python -I scripts/evaluate_personal_steps.py data/private/steps_clean.csv

Fixed before it ran: the held-out window is the last 90 days; every policy sees only the days before
the one it sets a goal for; the cap is the product's own `compute_cap` (TabPFN v2 on the bundled public
rows plus this person's earlier days), fed the last 365 days as the app sends them; caps are computed
from 28 days before the window, so the controller enters the window already capped. One person means
the interval cannot resample people, so it resamples ISO weeks.

Only aggregate numbers go to results/personal_steps.md. Per-day caps stay in results/private/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

from slowstart.config import Settings
from slowstart.data.steps_import import parse_steps
from slowstart.evaluation import stats, steps_eval
from slowstart.models import StepParams
from slowstart.prediction.cap import compute_cap
from slowstart.prediction.predictor import TabPFNPredictor

BASELINE = "own_p30_28d"
HISTORY_DAYS = 365  # what the app sends (app/src/game/day.ts)
LEAD_DAYS = 28
ME = "me"
LABELS = {
    "fixed_10000": "Fixed 10,000",
    "trailing_median_28d": "Own 28-day median",
    "own_p30_28d": "Own 28-day 30th percentile",
    "tabpfn_p30_cap": "TabPFN 30th percentile (cap alone)",
    "controller": "Controller (slow start / AIMD)",
    "controller_tabpfn_cap": "Slow Start (controller + TabPFN cap)",
}


def personal_caps(
    days, start, settings, params, cache_path: Path, n_estimators: int
) -> tuple[dict, dict]:
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    predictor = None
    sources: dict[str, int] = {}
    caps = {}
    first = start - dt.timedelta(days=LEAD_DAYS)
    todo = [d.date for d in days if d.date >= first]
    for i, day in enumerate(todo):
        key = day.isoformat()
        if key not in cache:
            predictor = predictor or TabPFNPredictor(n_estimators)
            history = [d for d in days if d.date < day][-HISTORY_DAYS:]
            t0 = time.perf_counter()
            cap = compute_cap(history, day, predictor, settings, params)
            cache[key] = [cap.p30 if cap.p30 is not None else cap.value, cap.source]
            print(
                f"  cap {i + 1}/{len(todo)} {day}: {cache[key][0]} ({cap.source}, {time.perf_counter() - t0:.1f} s)"
            )
            cache_path.write_text(json.dumps(cache))
        value, source = cache[key]
        sources[source] = sources.get(source, 0) + 1
        if value is not None:
            caps[(ME, day)] = (float(value), float(value))
    return caps, sources


def build(args) -> dict:
    settings = Settings().model_copy(update={"tabpfn_estimators": args.n_estimators})
    params = StepParams(ai=settings.step_ai)
    imported = parse_steps(Path(args.csv).read_text(encoding="utf-8-sig"))
    days = imported.days
    people = {ME: days}
    start = steps_eval.window_start(people, args.window_days)
    cache = Path(args.out) / "private" / "cache" / f"personal-caps-n{args.n_estimators}.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    caps, sources = personal_caps(days, start, settings, params, cache, args.n_estimators)

    base = steps_eval.make_policies(caps, params, include_controller=True)
    # the app sends a year of history, so every policy sees at most that
    policy_map = {k: (lambda p, h, d, f=f: f(p, h[-HISTORY_DAYS:], d)) for k, f in base.items()}
    scored, meta = steps_eval.score(people, policy_map, start)

    weeks = [f"{r.day.isocalendar()[0]}-W{r.day.isocalendar()[1]:02d}" for r in scored[BASELINE]]
    base_met = steps_eval.met_vector(scored[BASELINE])
    rows = []
    for key, items in scored.items():
        met = steps_eval.met_vector(items)
        rows.append(
            {
                "policy": key,
                "label": LABELS[key],
                "goal_met": sum(met) / len(met) if met else None,
                "mean_goal": sum(r.goal for r in items) / len(items) if items else None,
                "goal_level": stats.goal_level(
                    [r.goal for r in items], [r.reference for r in items]
                ),
                "vs_baseline": None
                if key == BASELINE
                else stats.paired_bootstrap(met, base_met, weeks),
            }
        )
    window = [d for d in days if d.date >= start]
    return {
        "generated": dt.date.today().isoformat(),
        "data": f"one person's Google Fit daily step counts ({imported.format}), cleaned by "
        "scripts/clean_personal.py",
        "first": imported.first.isoformat(),
        "last": imported.last.isoformat(),
        "days_loaded": len(days),
        "not_carried": imported.not_worn,
        "window_start": start.isoformat(),
        "window_days": args.window_days,
        "window_not_carried": sum(d.steps is None for d in window),
        "scored_days": meta["person_days"],
        "weeks": len(set(weeks)),
        "reference_median": scored[BASELINE][0].reference if scored[BASELINE] else None,
        "cap_sources": sources,
        "step_ai": params.ai,
        "rows": rows,
    }


def markdown(r: dict) -> str:
    def pct(x):
        return "n/a" if x is None else f"{x * 100:.1f}%"

    lines = [
        "# Personal steps backtest (the first user)",
        "",
        f"Generated {r['generated']}. {r['data']}: {r['days_loaded']} days from {r['first']} to "
        f"{r['last']}, {r['not_carried']} of them with the phone or watch not carried. Held out: the last "
        f"{r['window_days']} days from {r['window_start']}, {r['scored_days']} of them scored "
        f"({r['window_not_carried']} not carried) across {r['weeks']} weeks. Usual day before the window "
        f"(median): {r['reference_median']:,.0f} steps. Step per win: {r['step_ai']:,}.",
        "",
        "| Policy | Goal met | Mean goal | Goal level | Met vs own 30th percentile (95% CI) |",
        "|---|---|---|---|---|",
    ]
    for row in r["rows"]:
        vs = row["vs_baseline"]
        text = (
            "(baseline)"
            if vs is None
            else f"{vs[0] * 100:+.1f} pts ({vs[1] * 100:+.1f} to {vs[2] * 100:+.1f})"
        )
        lines.append(
            f"| {row['label']} | {pct(row['goal_met'])} | {row['mean_goal']:,.0f} | "
            f"{row['goal_level']:.2f} | {text} |"
        )
    lines += [
        "",
        f"Cap sources over the window and its 28-day lead: {r['cap_sources']}.",
        "",
        "**Goal level**: the mean goal divided by the usual day before the window; below 1.00 asks for "
        "less than usual. The interval resamples weeks, because there is one person.",
        "",
        "## Limits",
        "",
        "- One person, and mostly a phone in a pocket: the watch synced to Google Fit on few days, so "
        "days the phone sat on a desk count low.",
        "- A backtest replays days lived without the app. It cannot show whether a goal changes "
        "behaviour; it shows how often each goal would have been met.",
        "- Under 500 steps is read as not carried (scripts/clean_personal.py); that line was drawn before "
        "this ran.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="date,steps from scripts/clean_personal.py")
    ap.add_argument("--out", default="results")
    ap.add_argument("--window-days", type=int, default=90)
    ap.add_argument("--n-estimators", type=int, default=4)
    args = ap.parse_args()
    result = build(args)
    out = Path(args.out)
    (out / "private").mkdir(parents=True, exist_ok=True)
    (out / "private" / "personal_steps.json").write_text(json.dumps(result, indent=2, default=str))
    (out / "personal_steps.md").write_text(markdown(result), encoding="utf-8")
    print(markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())

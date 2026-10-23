"""Reproduce the steps results (R8.1): every policy, held out, on the public Fitbit set.

    python -I scripts/evaluate_steps.py            # real TabPFN v2, writes results/steps.{json,md}
    python -I scripts/evaluate_steps.py --fake     # pipeline check with a stand-in predictor; DO NOT QUOTE

Predictions are cached in results/cache/, so a rerun takes seconds. The controller rows and the goal-level
and interval columns say "locked" until H1 and H3 are written; everything else always runs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from importlib import metadata
from pathlib import Path

from slowstart.config import Settings
from slowstart.evaluation import stats, steps_eval
from slowstart.evaluation.fitbit import DEFAULT_ZIP, load_fitbit
from slowstart.models import StepParams
from slowstart.prediction.predictor import EmpiricalPredictor, TabPFNPredictor

BASELINE = "own_p30_28d"
LABELS = {
    "fixed_10000": "Fixed 10,000",
    "trailing_median_28d": "Own 28-day median",
    "own_p30_28d": "Own 28-day 30th percentile",
    "tabpfn_p30_cap": "TabPFN 30th percentile (cap alone)",
    "controller": "Controller (slow start / AIMD)",
    "controller_tabpfn_cap": "Controller + TabPFN cap",
}


def locked(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        return None


def build(args) -> dict:
    params, settings = StepParams(), Settings()
    settings = settings.model_copy(update={"tabpfn_estimators": args.n_estimators})
    people = load_fitbit(args.zip)
    ids = {pid: f"P{i + 1:02d}" for i, pid in enumerate(sorted(people))}
    people = {ids[pid]: days for pid, days in people.items()}
    all_days = [d for days in people.values() for d in days]
    not_worn = sum(1 for d in all_days if d.steps is None)

    predictor = EmpiricalPredictor() if args.fake else TabPFNPredictor(args.n_estimators)
    name = "fake" if args.fake else f"tabpfn-v2-n{args.n_estimators}"
    cache = Path(args.out) / "cache" / f"caps-{name}.json"
    print(f"loaded {len(people)} people, {len(all_days)} person-days, {not_worn} not worn")
    caps = steps_eval.calendar_caps(people, predictor, settings, cache_path=cache, progress=print)

    ctl = steps_eval.controller_is_written(params)
    policy_map = steps_eval.make_policies(caps, params, include_controller=ctl)
    start = steps_eval.window_start(people, args.window_days)
    scored, meta = steps_eval.score(people, policy_map, start)

    base_met = steps_eval.met_vector(scored[BASELINE])
    groups = [r.person for r in scored[BASELINE]]
    rows = []
    for key, items in scored.items():
        met = steps_eval.met_vector(items)
        entry = {
            "policy": key,
            "label": LABELS[key],
            "goal_met": sum(met) / len(met) if met else None,
            "mean_goal": sum(r.goal for r in items) / len(items) if items else None,
            "goal_level": locked(
                stats.goal_level, [r.goal for r in items], [r.reference for r in items]
            ),
            "vs_baseline": None,
        }
        if key != BASELINE:
            entry["vs_baseline"] = locked(stats.paired_bootstrap, met, base_met, groups)
        rows.append(entry)

    reached = {}
    for key in ("tabpfn_p30_cap", BASELINE):
        items = scored.get(key, [])
        reached[key] = sum(r.steps >= r.goal for r in items) / len(items) if items else None

    return {
        "generated": dt.date.today().isoformat(),
        "dry_run": bool(args.fake),
        "predictor": predictor.name,
        "tabpfn_package": None if args.fake else metadata.version("tabpfn"),
        "n_estimators": args.n_estimators,
        "data": "Kaggle 'Fitbit Fitness Tracker Data' (arashnic/fitbit), CC0, 2016-03-12 to 2016-05-12",
        "people_loaded": len(people),
        "person_days_loaded": len(all_days),
        "not_worn_excluded": not_worn,
        "controller_written": ctl,
        "params": params.model_dump(),
        **meta,
        "rows": rows,
        "cap_calibration": reached,
    }


def fmt(x, pct=False, digits=1):
    if x is None:
        return "locked"
    if isinstance(x, float) and math.isnan(x):
        return "n/a"
    return f"{x * 100:.{digits}f}%" if pct else f"{x:.2f}"


def markdown(r: dict) -> str:
    lines = []
    if r["dry_run"]:
        lines += [
            "> **DRY RUN with a stand-in predictor. Do not quote these numbers.**",
            "",
        ]
    lines += [
        "# Steps results",
        "",
        f"Generated {r['generated']}. Data: {r['data']}.",
        "",
        f"- **{r['people']} people, {r['person_days']} person-days** scored: the last window starting "
        f"{r['window_start']}, only days where every policy set a goal and the person had at least 7 "
        "worn days before.",
        f"- {r['not_worn_excluded']} of {r['person_days_loaded']} loaded person-days have 0 steps and are "
        "treated as 'tracker not worn': not scored and not fed to any policy.",
        f"- Predictor: {r['predictor']}"
        + (
            f" (tabpfn {r['tabpfn_package']}, {r['n_estimators']} estimators, CPU)"
            if not r["dry_run"]
            else ""
        )
        + ". Fitted per calendar day on everyone's earlier rows only.",
        "",
        "| Policy | Goal met | Mean goal (steps) | Goal level | Met vs own 30th pct (95% CI) |",
        "|---|---|---|---|---|",
    ]
    for row in r["rows"]:
        vs = row["vs_baseline"]
        if row["policy"] == BASELINE:
            vs_text = "(baseline)"
        elif vs is None:
            vs_text = "locked"
        else:
            vs_text = f"{vs[0] * 100:+.1f} pts ({vs[1] * 100:+.1f} to {vs[2] * 100:+.1f})"
        lines.append(
            f"| {row['label']} | {fmt(row['goal_met'], pct=True)} | "
            f"{row['mean_goal']:.0f} | {fmt(row['goal_level'])} | {vs_text} |"
        )
    lines += [
        "",
        "**Goal met** is the share of person-days with steps ≥ goal. **Goal level** is the mean of "
        "goal ÷ the person's median steps before the window: a policy cannot win by quietly setting tiny "
        "goals without this number showing it. The interval resamples people, not days.",
        "",
        "Cap calibration (share of days at or above the 30th-percentile goal; ideal is about 70%): "
        + ", ".join(f"{LABELS[k]} {fmt(v, pct=True)}" for k, v in r["cap_calibration"].items()),
        "",
        "## Limits",
        "",
        "- About 33 people for about two months, in 2016. The held-out window is 14 days.",
        "- A backtest replays what people did *without* the app. It cannot show whether a goal changes "
        "what someone does.",
        "- Zero-step days are treated as missing, which removes honest rest days that happened to log 0.",
        "- The controller rows are empty until H1 is written, and the goal-level and interval columns "
        "until H3 is.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", default=str(DEFAULT_ZIP))
    ap.add_argument("--out", default="results")
    ap.add_argument("--window-days", type=int, default=14)
    ap.add_argument("--n-estimators", type=int, default=4)
    ap.add_argument("--fake", action="store_true", help="stand-in predictor; pipeline check only")
    args = ap.parse_args()
    result = build(args)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = "steps.dryrun" if args.fake else "steps"
    (out / f"{stem}.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    (out / f"{stem}.md").write_text(markdown(result), encoding="utf-8")
    print(markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Collect the four steps runs (validation and final, feature sets v1 and v2) into one table.

    python -I scripts/summarise_steps.py        # writes results/steps.summary.md

Reads results/steps.{validation,final}-{v1,v2}.json, which scripts/evaluate_steps.py wrote.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RESULTS = Path("results")
# The website quotes these numbers; it reads them from here, never from hand-typed text.
SITE = Path("app/src/site/evidence.json")
RUNS = [("validation", "v1"), ("validation", "v2"), ("final", "v1"), ("final", "v2")]


def load(label: str, fs: str) -> dict:
    d = json.loads((RESULTS / f"steps.{label}-{fs}.json").read_text(encoding="utf-8"))
    d["by"] = {r["policy"]: r for r in d["rows"]}
    return d


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    lines = [
        "# Steps results: all four runs",
        "",
        "Validation: data cut at 2016-04-28, scored on the 14 days before it. Final: all data, scored on "
        "the last 14 days. TabPFN is fitted per calendar day on everyone's earlier rows only. The feature "
        "set was chosen on the validation window by a rule written before the v2 result was seen: pick "
        "the higher goal-met rate, provided the mean goal is at least 90% of the plain 30th "
        "percentile's. Both qualified, v1 was higher (a half-point difference), so v1 is the default.",
        "",
        "| Window | Person-days (people) | Fixed 10,000 | Own 28-day median | Own 28-day 30th pct "
        "| TabPFN v1 | TabPFN v2 |",
        "|---|---|---|---|---|---|---|",
    ]

    def cell(run: dict, key: str) -> str:
        r = run["by"][key]
        return f"{r['goal_met'] * 100:.1f}% (goal {r['mean_goal']:.0f})"

    for label in ("validation", "final"):
        v1, v2 = load(label, "v1"), load(label, "v2")
        lines.append(
            f"| {label} | {v1['person_days']} ({v1['people']}) | {cell(v1, 'fixed_10000')} | "
            f"{cell(v1, 'trailing_median_28d')} | {cell(v1, 'own_p30_28d')} | "
            f"{cell(v1, 'tabpfn_p30_cap')} | {cell(v2, 'tabpfn_p30_cap')} |"
        )
    lines += [
        "",
        "Each cell is the share of person-days with steps at or above the goal, then the mean goal in steps.",
        "",
    ]
    diffs = []
    for label, fs in RUNS:
        run = load(label, fs)
        d = run["by"]["tabpfn_p30_cap"]["goal_met"] - run["by"]["own_p30_28d"]["goal_met"]
        diffs.append(f"{label} {fs}: {d * 100:+.1f} pts")
    lines += ["TabPFN minus the plain 30th percentile: " + "; ".join(diffs) + ".", ""]
    (RESULTS / "steps.summary.md").write_text("\n".join(lines), encoding="utf-8")
    evidence = {}
    for label, fs in RUNS:
        run = load(label, fs)
        evidence[f"{label}_{fs}"] = {
            "person_days": run["person_days"],
            "people": run["people"],
            "window_start": run["window_start"],
            "policies": {
                k: {"goal_met": round(v["goal_met"], 4), "mean_goal": round(v["mean_goal"])}
                for k, v in run["by"].items()
            },
        }
    SITE.parent.mkdir(parents=True, exist_ok=True)
    chosen_path = RESULTS / "sweep" / "chosen.json"
    if chosen_path.exists():
        chosen = json.loads(chosen_path.read_text(encoding="utf-8"))["chosen"]
        for label in ("validation", "final"):
            run = json.loads(
                (RESULTS / "sweep" / f"steps.{label}-ai{chosen}-v1.json").read_text(
                    encoding="utf-8"
                )
            )
            by = {r["policy"]: r for r in run["rows"]}
            evidence[f"sweep_{label}"] = {
                "step": chosen,
                "policies": {
                    k: {
                        "goal_met": round(v["goal_met"], 4),
                        "mean_goal": round(v["mean_goal"]),
                        "goal_level": round(v["goal_level"], 3),
                        "vs_p30": v["vs_baseline"],
                    }
                    for k, v in by.items()
                },
            }
    SITE.write_text(json.dumps(evidence, indent=1), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())

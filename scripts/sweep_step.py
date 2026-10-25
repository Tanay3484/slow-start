"""Sweep the controller's step per won day (StepParams.ai) on the validation window, pick one by a rule
fixed before the sweep ran, then evaluate that one once on the final window.

    python scripts/sweep_step.py        # writes results/sweep/ and results/steps.sweep.md

The rule (written before any sweep result was seen, 2026-10-25): choose the LARGEST step whose
validation goal-met rate for "Controller + TabPFN cap" is at least 70%, the same "about 7 days in 10"
the cap aims for. A larger step asks for more; the 70% floor keeps the goal winnable.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

STEPS = [250, 500, 750, 1000, 1500]
FLOOR = 0.70
OUT = Path("results/sweep")


def run(label: str, ai: int, until: str | None) -> dict:
    args = [sys.executable, "scripts/evaluate_steps.py", "--features", "v1", "--label", f"{label}-ai{ai}",
            "--ai", str(ai), "--out", str(OUT)]  # fmt: skip
    if until:
        args += ["--until", until]
    subprocess.run(args, check=True, capture_output=True)
    data = json.loads((OUT / f"steps.{label}-ai{ai}-v1.json").read_text(encoding="utf-8"))
    return {r["policy"]: r for r in data["rows"]}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    val = {ai: run("validation", ai, "2016-04-28") for ai in STEPS}
    ok = [ai for ai in STEPS if val[ai]["controller_tabpfn_cap"]["goal_met"] >= FLOOR]
    chosen = max(ok) if ok else STEPS[0]
    fin = run("final", chosen, None)

    def row(r: dict) -> str:
        lvl = r["goal_level"]
        return f"{r['goal_met'] * 100:.1f}% | {r['mean_goal']:.0f} | {lvl:.2f}"

    lines = [
        "# The controller's step per won day: sweep on validation, one final run",
        "",
        f"Rule, fixed before the sweep: the largest step whose validation goal-met rate (controller + "
        f"TabPFN cap) is at least {FLOOR:.0%}. Chosen: **{chosen} steps**.",
        "",
        "| Step per win | Validation: goal met · mean goal · goal level (controller + cap) |",
        "|---|---|",
        *[
            f"| {ai}{' (chosen)' if ai == chosen else ''} | {row(val[ai]['controller_tabpfn_cap'])} |"
            for ai in STEPS
        ],
        "",
        f"Final window, step {chosen}:",
        "",
        "| Policy | Goal met | Mean goal | Goal level | Met vs own 30th pct (95% CI) |",
        "|---|---|---|---|---|",
    ]
    for key in (
        "fixed_10000",
        "trailing_median_28d",
        "own_p30_28d",
        "tabpfn_p30_cap",
        "controller",
        "controller_tabpfn_cap",
    ):
        r = fin[key]
        vs = r["vs_baseline"]
        vs_text = (
            "(baseline)"
            if vs is None
            else f"{vs[0] * 100:+.1f} pts ({vs[1] * 100:+.1f} to {vs[2] * 100:+.1f})"
        )
        lines.append(
            f"| {r['label']} | {r['goal_met'] * 100:.1f}% | {r['mean_goal']:.0f} | {r['goal_level']:.2f} | {vs_text} |"
        )
    lines.append("")
    Path("results/steps.sweep.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "chosen.json").write_text(
        json.dumps({"rule_floor": FLOOR, "steps": STEPS, "chosen": chosen}), encoding="utf-8"
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())

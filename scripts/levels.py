"""Progress board for Tanay's four @human levels.

    python scripts/levels.py        # H1-H4: locked, cracking, or unlocked

A level is *locked* while its function is still a stub (its contract tests skip), *cracking* while some
of its tests fail, and *unlocked* when all of them pass.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

LEVELS = [
    ("H1", "Step controller", "pytest", "H1"),
    ("H2", "Exercise controller", "pytest", "H2"),
    ("H3", "Evaluation statistics", "pytest", "H3"),
    ("H4", "XP and stage rule", "vitest", ""),
]
ROOT = Path(__file__).resolve().parent.parent


def count(text: str, word: str) -> int:
    m = re.search(rf"(\d+) {word}", text)
    return int(m.group(1)) if m else 0


def run_pytest(key: str) -> tuple[int, int, int]:
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "backend/tests/test_human_levels.py", "-k", key, "-o", "addopts=", "-q", "--tb=no", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout  # fmt: skip
    return count(out, "passed"), count(out, "failed"), count(out, "skipped")


def run_vitest() -> tuple[int, int, int]:
    out = subprocess.run(
        "npx vitest run src/game/xp.test.ts",
        cwd=ROOT / "app",
        capture_output=True,
        text=True,
        shell=True,
    ).stdout
    out = re.sub(r"\x1b\[[0-9;]*m", "", out)
    line = next((ln for ln in out.splitlines() if ln.strip().startswith("Tests")), "")
    return count(line, "passed"), count(line, "failed"), count(line, "skipped")


def main() -> int:
    for ident, name, runner, key in LEVELS:
        passed, failed, skipped = run_pytest(key) if runner == "pytest" else run_vitest()
        total = passed + failed + skipped
        if total and skipped == total:
            state = "LOCKED   "
        elif failed:
            state = "CRACKING "
        else:
            state = "UNLOCKED "
        bar = "#" * passed + "x" * failed + "." * skipped
        print(f"{ident}  {state} {name:<24} [{bar}] {passed}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

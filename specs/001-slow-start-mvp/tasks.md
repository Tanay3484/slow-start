# Tasks — Slow Start MVP

Status: Draft
Owner: Tanay
Updated: 2026-10-23
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

Owners: `@ai` Claude builds it. `@human` Tanay writes it by hand; Claude gives hints, writes the contract
tests first when asked, and reviews. Every task cites requirement ids.

Written ahead of approval at Tanay's request. Boxes are ticked as work lands, with the task id in the
commit message.

## Your four tasks

These are the project's core. Each is a pure function with a clear contract, 1–3 hours, and the app runs on
a stub until it lands (`NotImplementedError` → the guard serves a baseline and the app shows a "fallback"
badge). The contract tests are in `backend/tests/test_human_levels.py` and `app/src/game/xp.test.ts`; they
skip while a stub is in place and run as soon as you replace it.

### H1 — Step controller (@human) · R1.1–R1.6, R1.9 · about 2 h

File: `backend/slowstart/controllers/steps.py` · Function: `next_window(days, params) -> StepDecision`

**In:** `days`, a list of `DayResult(date, steps, goal, excused)`, oldest first, possibly unsorted, possibly
empty. `params: StepParams(start=1500, floor=1000, ceiling=20000, ai=250)`.

**Out:** `StepDecision(window, threshold, phase)` for the *next* day.

**Rules.** Replay the days in date order with two numbers: `window`, starting at `params.start`, and
`threshold`, starting at `None` (no threshold yet).

- Skip a day if `excused`, or `steps is None` (not worn), or `goal is None` (never planned).
- A day is **met** when `steps >= goal`. (`goal` is what was shown, which may be below `window`.)
- Met and `threshold is None` or `window < threshold`: `window = window * 2`, but never past `threshold` if
  there is one. (Slow start.)
- Met and `window >= threshold`: `window = window + params.ai`. (Cruising.)
- Missed: `window = max(window // 2, params.floor)`, and `threshold = window`.
- Always clamp to `[floor, ceiling]`.
- Phase: `recovering` if the last counted day was a miss; else `slow_start` while `threshold is None` or
  `window < threshold`; else `cruising`.

**Worked example** (start 1500, ai 250, every goal equal to the window):

| Days so far (steps vs goal) | Window | Threshold | Phase |
|---|---|---|---|
| none | 1500 | None | slow_start |
| 1600 vs 1500 (met) | 3000 | None | slow_start |
| + 3200 vs 3000 (met) | 6000 | None | slow_start |
| + 4200 vs 6000 (missed) | 3000 | 3000 | recovering |
| + 3100 vs 3000 (met) | 3250 | 3000 | cruising |
| + 800 vs 3250 (missed) | 1625 | 1625 | recovering |

**Edge cases:** empty history; one day; unsorted input; an excused day in the middle changes nothing; a
miss at the floor stays at the floor; the ceiling holds; two identical dates; input list is not mutated.

**Check:** `pytest backend/tests/test_human_levels.py -k H1`. Hint ladder available from the `task-coach`
agent.

### H2 — Exercise controller (@human) · R2.1–R2.5 · about 2 h

File: `backend/slowstart/controllers/exercise.py` · Function:
`next_target(sessions, exercise, params) -> Target`

**In:** `sessions`, a list of `Session(date, exercise, sets=[SetResult(weight_kg, reps)])` for **one**
exercise, possibly empty. `exercise` is a key of `params.scheme`. `params` holds, per exercise, the number
of sets, the load increment (barbell 2.5 kg, dumbbell 1 kg, bodyweight none), and a starter target.

**Out:** `Target(sets, reps, weight_kg)` for the next session. `weight_kg is None` for bodyweight.

**Rules.** Replay in date order. Anchor the target on the first session: weighted lifts take that
session's heaviest working weight and the scheme's reps; bodyweight takes the lowest reps among its best
`sets` sets. With no sessions, return the starter target.

- A session **meets** the target when it has at least `target.sets` sets with `weight >= target.weight`
  (any weight for bodyweight) and `reps >= target.reps`.
- Met: add one step. Weighted: `weight + increment`. Bodyweight: `reps + 1`.
- Missed: cut. Weighted: `floor(weight * 0.90 / increment) * increment`, at least one increment.
  Bodyweight: `max(1, floor(reps * 0.80))`.
- Warm-up sets never reach this function (the importer drops them).

**Worked example** (bench press, scheme 3 sets × 8, increment 2.5 kg):

| Sessions | Next target |
|---|---|
| none | starter (20 kg × 8 × 3) |
| 3×8 @ 60 | 62.5 kg × 8 × 3 |
| 3×8 @ 60, then 3×8 @ 62.5 | 65 kg × 8 × 3 |
| 3×8 @ 60, then 2×8 @ 62.5 | 56.25 → 55 kg × 8 × 3 |
| push-up: 3 sets of 10, then 3 of 11 | 12 reps × 3 sets |
| push-up: 3×10, then 3×6 | 8 reps × 3 sets |

**Edge cases:** unsorted sessions; one session; bodyweight versus weighted; sets with different weights in
one session; a session with fewer sets than the target; the cut never reaches zero.

**Check:** `pytest backend/tests/test_human_levels.py -k H2`.

### H3 — Evaluation statistics (@human) · R8.1, R8.4 · about 1.5 h

File: `backend/slowstart/evaluation/stats.py` · Functions:
`goal_level(goals, reference) -> float` and
`paired_bootstrap(a, b, groups, n=2000, seed=0) -> tuple[float, float, float]`

- `goal_level`: the mean of `goal / reference` over pairs with `reference > 0`. `nan` if none. This is the
  guardrail against winning by setting tiny goals.
- `paired_bootstrap`: `a` and `b` are lists of 0/1 "goal met" outcomes for two policies on the **same**
  person-days, in the same order. `groups` gives each day's person. Return `(mean(a) - mean(b), lo, hi)`,
  a 95% interval from resampling **people**, not days (days within a person are not independent). With a
  fixed `seed` the result is identical every run.

**Edge cases:** unequal lengths raise `ValueError`; empty input raises `ValueError`; one person only;
identical policies give `(0.0, 0.0, 0.0)`; `n` small.

**Check:** `pytest backend/tests/test_human_levels.py -k H3`.

### H4 — XP and stage rule (@human) · R4.3, R4.4, R4.7, R6.3 · about 1 h, TypeScript

File: `app/src/game/xp.ts` · Functions: `xpForDay(d) -> number` and `stageForXp(xp) -> 0 | 1 | 2 | 3`

- `xpForDay({ goal, steps, trained, explored })`: your design. Contract: never negative; a missed day
  gives 0 (nothing is taken away); a won day gives more than a missed one; more steps never give less XP;
  training and exploring each add XP; the result is a whole number.
- `stageForXp(xp)`: stage 0 asleep, 1 drowsy, 2 awake, 3 roaring. Thresholds are yours; they must be
  increasing, and a person who wins every day should reach stage 3 in about three weeks.

**Check:** `npm test` in `app/` (Vitest), file `src/game/xp.test.ts`.

## Setup

- [ ] T1 `@ai` Repo scaffold: licence, gitignore, README, CI job named `tests`, pyproject, lint config. R9.3
- [ ] T2 `@ai` Specs 000 and 001 drafted. (this file)

## Backend

- [ ] T3 `@ai` Settings (`SS_`), models, error types. R9.3
- [ ] T4 `@ai` Steps importers: Takeout, `date,steps` CSV, Fitabase. R3.1, R3.3
- [ ] T5 `@ai` Hevy CSV importer with summary. R3.2
- [ ] T6 `@ai` Baseline policies and the guard around the `@human` stubs. R1.8, R2.5, R9.5
- [ ] T7 `@ai` Features, `Predictor` protocol, TabPFN v2 predictor, cap. R1.7–R1.9, R9.1
- [ ] T8 `@ai` API: health, goal/steps, goal/exercise, import/steps, import/hevy. R1, R2, R3.4
- [ ] T9 `@ai` Check-in: Ollama client, schema, keyword reader, templates. R5
- [ ] T10 `@ai` `scripts/evaluate_steps.py`, cache, no-look-ahead test. R8.1, R8.3, R8.4
- [ ] T11 `@ai` Tune `PRIOR_ROWS` and `n_estimators` for latency. Design §6
- [ ] T12 `@ai` Run the steps evaluation, write `results/steps.md`. R8.1, R8.5 (needs H1, H3 for the
  controller rows)
- [ ] T13 `@ai` `scripts/evaluate_training.py` for a Hevy CSV. R8.2 (needs H2 and Tanay's export)
- [ ] T14 `@ai` Contract tests for H1–H3. `@human` tasks above

## App

- [ ] T15 `@ai` App scaffold: Vite, TypeScript, Vitest, state store, API client with fallback. R7
- [ ] T16 `@ai` Pixel art: Slumbrock ×4, wild creatures, rare ones, backgrounds. R4.10
- [ ] T17 `@ai` Game loop and Home screen: spawn, HP, win/miss, stages, Speed/Power. R4
- [ ] T18 `@ai` Check-in screen. R5
- [ ] T19 `@ai` Demo mode with a real person from the public data. R4.9
- [ ] T20 `@ai` Places and explore bonus, ported from Golden Hour. R6
- [ ] T21 `@ai` Import, export and delete screens. R3, R7.3
- [ ] T22 `@ai` Contract tests for H4 and app logic. R4

## Ship

- [ ] T23 `@ai` Capacitor Android project, debug APK, GitHub release. R7.2
- [ ] T24 `@ai` Dockerfile, `render.yaml`, deploy, smoke test on a phone. R9.1
- [ ] T25 `@ai` README with credits, screenshots, run instructions. R9.4
- [ ] T26 `@human+ai` Post draft by `post-writer`; Tanay edits and publishes
- [ ] T27 `@human` Export Takeout steps and the Hevy CSV into `data/private/`; use the app daily

## Order

1. T1–T3, then T4–T7 and T14 in parallel with H1–H3 (Tanay).
2. T8, T10, T11 once T7 lands; T12 once H1 and H3 land.
3. T15–T17 independent of the backend; T19 needs T8 and the dataset.
4. T23 early on Saturday: the APK build is the riskiest app step.

## Open questions

None blocking.

## Changelog

- 2026-10-23: First draft.

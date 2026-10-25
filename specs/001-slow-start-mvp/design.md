# Design — Slow Start MVP

Status: Draft
Owner: Tanay
Updated: 2026-10-23
Requirements: [requirements.md](requirements.md)

## 1. The idea in one picture

TCP lets a sender go faster only as fast as two limits allow:

| TCP | Slow Start |
|---|---|
| Congestion window (cwnd), grown by the sender | **Window**: the controller's goal, from `controllers/` |
| Receiver window (rwnd), advertised by the receiver | **Cap**: TabPFN's 30th percentile of tomorrow's steps |
| Effective window = min(cwnd, rwnd) | **Goal** = min(window, cap) |
| Slow start: double per success | Double the goal after a met day, up to the threshold |
| Congestion avoidance: +1 per round | Add 250 steps per met day above the threshold |
| Loss: halve, set ssthresh | Missed day: halve the window, set the threshold |

The controller finds how much the person can do. The predictor stops it from asking too much on a day
the history says will be low. Code decides every number. Gemma only reads a check-in and talks as the
giant.

## 2. Architecture

```
Phone / browser ── app/ (TypeScript, Vite, canvas pixel art, localStorage)
      │  Capacitor wraps the same build as an Android APK
      │
      ├──▶ Overpass (OpenStreetMap), straight from the device: places, no server in between
      │
      └──▶ backend/ (FastAPI, one Render web service, also serves the built app)
              ├─ controllers/   steps, exercise (@human)   + baseline policies
              ├─ prediction/    features, TabPFN v2 predictor, cap
              ├─ data/          Takeout / Fitabase / Hevy importers (in memory)
              ├─ checkin/       reader + Slumbrock lines  ──▶ Ollama, gemma3 (private service)
              └─ api.py
```

- **The server holds no user data.** The app sends the history it needs for one call and keeps its own
  copy. The server processes it in memory (R3.4). This is honest in the post: the data is sent to our own
  server, and never to a closed API.
- **Why Python:** TabPFN is a Python library. The app is TypeScript because Capacitor wraps a web build.
- **Why the app does not hold the controller:** the controller is an `@human` Python function that the
  backtest also runs. One implementation, one source of truth.
- **Places run on the device** because Render's shared IP was rate-limited by Overpass in Week 1, and
  because the location then never reaches our server (R6.2).

## 3. Parameters (`slowstart/config.py`, env prefix `SS_`)

| Name | Value | Meaning |
|---|---|---|
| `STEP_START` | 1,500 | First goal for a new person |
| `STEP_FLOOR` / `STEP_CEILING` | 1,000 / 20,000 | R1.9 |
| `STEP_AI` | 1,500 in the product (`SS_STEP_AI`), 250 in the contract tests | Steps added per met day above the threshold; chosen by a sweep, see section 6 |
| `CAP_QUANTILE` | 0.30 | Cap is the 30th percentile, so about 7 days in 10 are reachable |
| `CAP_MIN_DAYS` | 7 | History needed before TabPFN is used |
| `PRIOR_ROWS` | tuned in T11 | Public rows added to a person's own rows |
| `FALLBACK_CAP` | 0.8 × trailing 14-day median | R1.8 |
| `LIFT_MISS_CUT` / `BW_MISS_CUT` | 0.90 / 0.80 | R2.4 |

## 4. Data model (Python, `slowstart/models.py`)

```python
class DayResult:      date: date; steps: int | None; goal: int | None; excused: bool = False
class StepDecision:   window: int; threshold: int | None; phase: Literal["slow_start","cruising","recovering"]
class Cap:            value: int | None; p30: int | None; p50: int | None; source: Literal["tabpfn","median","none"]
class Goal:           goal: int; window: int; cap: Cap; phase: ...; source: Literal["controller","fallback"]
class SetResult:      weight_kg: float | None; reps: int
class Session:        date: date; exercise: str; sets: list[SetResult]
class Target:         sets: int; reps: int; weight_kg: float | None
```

`steps is None` means missing (not worn). A day with `goal is None` was never planned (pre-install).

## 5. Controllers (`slowstart/controllers/`)

### 5.1 Steps (`steps.py`, **H1, @human**)

```python
def next_window(days: Sequence[DayResult], params: StepParams) -> StepDecision
```

Replays `days` oldest to newest, starting at `STEP_START`, applying R1.2–R1.5, and returns the window
for the next day. `DayResult.goal` is the goal that was shown (window capped); the replay judges a day
met when `steps >= goal`. Pure, no I/O, does not mutate `days`.

### 5.2 Exercise (`exercise.py`, **H2, @human**)

```python
def next_target(sessions: Sequence[Session], exercise: str, params: ExerciseParams) -> Target
```

R2.3–R2.4. Equipment increments: barbell 2.5 kg, dumbbell 1 kg. No history: the starter target from a
table in `params`. Pure.

### 5.3 The guard (`guard.py`, @ai)

Wraps both. If a function raises `NotImplementedError` (still a stub), the guard returns the baseline:
steps `0.8 × trailing 14-day median`, exercises "repeat last session", and marks `source: "fallback"`.
The app shows the fallback in a small badge so the stub state is visible, never hidden.

### 5.4 Baselines (`policies.py`, @ai)

Fixed 10,000; trailing 28-day median; own 30th percentile of the last 28 days (the fair rival for the
cap, at the same goal level); repeat last; fixed plan (+2.5 kg or +1 rep). Each is
`(history) -> goal` and shares one signature with the controller policies in the harness.

## 6. Prediction (`slowstart/prediction/`)

- **Features** (`features.py`, @ai) for target day `d`, from earlier days only: steps at lag 1, 2, 3; mean
  of the last 7; median of the last 14; min of the last 7; weekday; weekend flag. Needs at least 3 days
  in the last 7.
- **Predictor** (`predictor.py`): a `Predictor` protocol, `fit(X, y)` then `quantiles(X, qs)`. The real
  one wraps `TabPFNRegressor.create_default_for_version(ModelVersion.V2, device="cpu")`. Tests use a fake.
  `TABPFN_ALLOW_CPU_LARGE_DATASET=1` is set because the pooled set passes 1,000 rows.
- **Training rows** for a live call: the person's own earlier days plus `PRIOR_ROWS` rows from the
  bundled public dataset (`backend/slowstart/data/prior_steps.csv`, from the Kaggle Fitbit set, CC0,
  ids dropped). This is the cold start.
- **Cap** (`cap.py`): `p30 = quantile(0.30)`, rounded to 50, clamped to floor and ceiling.
- **Measured in the spike** (2026-10-23, laptop CPU, 14 fits, about 1,000 training rows each): median
  12.6 s per fit and predict, peak 584 MB. On 350 held-out person-days the p30 cap was met on 66.9% of
  days at a goal level of 0.81 of the person's median. The real comparison is against the own 30th
  percentile, in T12.
- **Feature sets, and how one was chosen.** The first real run (`v1`, raw steps) did not beat a plain
  "own 30th percentile of the last 28 days" at the same goal level (66.6% against 69.7% goal met). `v2`
  expresses every feature relative to the person's 14-day median and predicts a ratio, so one pooled
  model shares the shape of a week and leaves the scale to each person. To avoid tuning on the test
  window, the two sets were compared on a **validation window** (data cut at 2016-04-28, scored on the 14
  days before it), the better one was picked, and only then evaluated on the final 14 days. All four
  runs are kept in `results/` and reported. **Outcome** (`results/steps.summary.md`): the sign of
  TabPFN's difference from the plain 30th percentile flipped between windows (+3.9 and +3.4 points on
  validation for v1 and v2, -3.1 for both on the final window), so on 33 people the two are
  indistinguishable. The rule picked v1 (68.0% against 67.5% on validation, a half-point gap); v2 is
  reported as the alternative. TabPFN's hit rate stayed near the 70% target in both windows (68.0%,
  66.6%) while the plain percentile's swung (64.0%, 69.7%), which is suggestive of steadier calibration
  and nothing more, with two windows.
- **The controller's step, and how it was chosen.** With your H1 controller and a 250-step climb, the
  final window showed 86.6% of goals met at goal level 0.50: after each halving the climb back is so slow
  that the goal sits at about half of a usual day. The step was swept (250 to 1,500) on the validation
  window under a rule fixed before the sweep: the largest step whose validation goal-met rate stays at or
  above 70%. That was 1,500, the top of the range tested (so a larger step might also pass). On the final
  window it gives 71.1% at goal level 0.74, against 69.7% at 0.79 for the plain 30th percentile: a tie.
  `results/steps.sweep.md`.
- **Latency plan:** one prediction per person per day, cached in the app. `PRIOR_ROWS` is tuned so a
  call stays under about 8 s on the Render plan. The app shows "Slumbrock is waking up" while it waits.

## 7. API (`slowstart/api.py`)

| Route | Body → response |
|---|---|
| `GET /api/health` | status, model name, predictor ready, controller state (`locked`/`unlocked`) |
| `POST /api/goal/steps` | `{today, history[{date,steps,goal,excused}]}` → `Goal` |
| `POST /api/goal/exercise` | `{exercise, sessions[…]}` → `Target`, `chance?` |
| `POST /api/import/steps` | file text → days, `not_worn`, summary |
| `POST /api/import/hevy` | file text → sessions, exercises, skipped, summary |
| `POST /api/checkin` | `{text}` → `{energy, body[], excused, line, source}` |

## 8. Check-in (`slowstart/checkin/`)

- Ollama client behind an interface (Golden Hour pattern): schema-constrained JSON, `num_predict`
  capped, every string has a `maxLength`, fields in written order.
- `energy` and `body` come from the model; `excused` is **set by code** from a keyword list and the
  model's `energy == "low"` plus a `body` match. The model never decides it (R5.2).
- Slumbrock's line: one sentence, at most 20 words, rejected if it contains a digit or a place name not
  given. Rejected or failed: a template line (R5.3, R5.4).

## 9. The game (`app/src/`)

| Module | Job |
|---|---|
| `state.ts` | One store, saved to `localStorage`: days, goals, XP, seen creatures, explored cells |
| `game/day.ts` | Spawn the day's creature, apply steps, settle yesterday |
| `game/xp.ts` | **H4, @human**: `xpForDay`, `stageForXp`. Stub: flat 10 XP, one stage per 100 XP |
| `game/creatures.ts` | Slumbrock and the wild creatures: names, habitats, sprite keys |
| `art/sprites.ts` | Pixel sprites as palette grids (half drawn, mirrored), `draw()` at integer scale |
| `api.ts` | Calls the backend, caches today's goal, falls back to the last goal (R7.4) |
| `places.ts` | Port of Golden Hour's Overpass query, categories and ranking, from the device |
| `explore.ts` | Place cells (about 500 m), first-visit check, rare spawn |
| `screens/` | Home, Check-in, Places, Collection, Import and settings, Demo |

Art: every creature is a palette grid in a TypeScript string array, drawn at an integer scale on a
`<canvas>` with `image-rendering: pixelated`. Slumbrock has four stages. Wild creatures are small
(16×16), grouped by habitat: park, waterfront, street, gym, plus rare ones for exploring.

The demo replays one real person's days from the public dataset, with a "Next day" button, calling the
live backend for each goal, so a judge sees slow start, the cap and a halving in a minute.

## 10. Evidence (`scripts/`)

- `evaluate_steps.py`: loads the public data, treats 0-step days as not worn, runs every policy day by
  day for every person (each policy sees only earlier days), scores the last 14 calendar days, and writes
  `results/steps.md` and `results/steps.json`: goal-met rate, goal level, and a paired bootstrap interval
  for each policy against the own-30th-percentile baseline. TabPFN predictions are cached per day in
  `results/cache/` so a rerun is quick.
- `evaluate_training.py`: from a Hevy CSV, split by date, last 3 months scored; `results/private/`
  holds anything derived from personal data, and only aggregate numbers go to `results/training.md`.
- `tests/test_no_lookahead.py`: a policy wrapper that raises if it is handed a day on or after the day
  it sets a goal for (R8.3).

## 11. Deployment

`render.yaml` Blueprint: `slowstart` (web, Docker, Python 3.11, CPU torch, TabPFN v2 weights baked in at
build, built app copied in) and `slowstart-ollama` (private service, gemma3, as in Golden Hour). The web
service needs about 1 GB at run time: plan `standard` (2 GB). Check the shared Render credit first; Week 1
and Week 2 services should be suspended by Tanay in the dashboard.

## 12. Risks

| Risk | Plan |
|---|---|
| The `@human` controllers land late | The guard keeps the app running on baselines; the harness reports controller rows as locked until they land |
| TabPFN too slow on Render | Smaller `PRIOR_ROWS`, `n_estimators=4`, cache per day |
| No personal data yet (Takeout, Hevy) | Importers are tested on synthetic fixtures; Claim 2 and the personal backtest wait for Tanay's exports. If they never arrive, the post says it |
| Public step data is short and from 2016 | Stated as the main limit in the post |
| APK build (Gradle, JDK) | Build early on Saturday; a web-only release is the fallback |
| Pixel art takes longer than planned | Fewer wild creatures; Slumbrock's four stages come first |

## Open questions

None blocking.

## Changelog

- 2026-10-23: First draft, with the TabPFN spike numbers.
- 2026-10-23: Added the feature-set comparison and its outcome (section 6), a per-client rate limit on
  the routes that cost CPU, and measured the container: with no network, 1 CPU and a 2 GB limit, TabPFN
  loads in 2.9 s, a goal call takes about 5 s, and peak memory is 598 MB. The 512 MB plans cannot hold it.
- 2026-10-25: The step per win is a setting (`SS_STEP_AI`, 1,500) chosen by a sweep on the validation
  window; the deploy is web 1c-2g plus Gemma 4B on 2c-4g.

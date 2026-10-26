# Slow Start

A fitness game for lazy people. Your daily step goal and your next workout are set the way TCP sets how
fast a connection may send: **start small, double after each success, grow slowly once you're near your
level, and halve after a miss, never to zero.** A second limit, TabPFN's prediction of what you'll
probably manage tomorrow, stops it asking for too much on a day the history says will be a low one.

You look after **Slumbrock**, a pixel-art stone giant that wakes up as you keep going. The idea comes from
a monster whose ability, also called Slow Start, halves its stats for its first five turns. The creature,
art and names here are original; nothing is taken from Pokémon or Nintendo.

Built for the DEV Hacktoberfest 2026 Open-Source AI Challenge, Week 3: *Slow and Steady*.

**Live:** <https://slowstart.onrender.com> (the game is at `/play`, the field guide at `/guide`).

## Who wrote what

The project was built with an AI coding agent (Claude) under a spec-first workflow
([`specs/`](specs/)). Four core functions were set aside to be written by hand:

| Level | Function | Written by |
|---|---|---|
| H1 | The step controller (`backend/slowstart/controllers/steps.py`) | Tanay, from a skeleton |
| H3 | The evaluation statistics (`backend/slowstart/evaluation/stats.py`) | Tanay, from a skeleton |
| H2 | The exercise controller (`backend/slowstart/controllers/exercise.py`) | Claude, handed over by Tanay to make the deadline |
| H4 | The XP and stage rule (`app/src/game/xp.ts`) | Claude, handed over by Tanay to make the deadline |

Everything else (the app, the art, the engine, the backend, the evaluation harness) was written by Claude
and reviewed by Tanay through pull requests.

## What the first evaluation found

On the public Fitbit data (33 people, two months, 2016), on held-out days:

- A fixed 10,000 steps is met on **34.6%** of days.
- The first controller (a 250-step climb after each win) met **86.6%**, but only by asking for **half** of
  what people usually walk. The goal-level guardrail caught it.
- With the climb chosen on a validation window by a rule fixed in advance (1,500 steps), Slow Start meets
  **71.1%** of days while asking for **74%** of a usual day. A plain "your own 30th percentile" meets
  **69.7%** at **79%**. The difference is +1.4 points (95% interval −4.8 to +7.4): **a tie**.
- TabPFN's cap on its own ties the plain percentile too (−3.1 points, −9.1 to +2.2).

So Slow Start is as good as the best simple rule here, not better. What the simple rule cannot do is start
on day one; it needs four weeks of history. The protocol and every table are in
[`results/steps.summary.md`](results/steps.summary.md) and [`results/steps.sweep.md`](results/steps.sweep.md).

## How it works

| TCP | Slow Start |
|---|---|
| Congestion window, grown by the sender | **Window:** the step controller's goal |
| Receiver window, advertised by the receiver | **Cap:** TabPFN's 30th percentile of tomorrow's steps |
| Effective window = min(cwnd, rwnd) | **Goal** = min(window, cap) |
| Slow start: double per success | Double the goal after a met day |
| Loss: halve, set the threshold | Missed day: halve the window, set the threshold |

Code decides every number. TabPFN v2 (open weights, CPU) predicts. Gemma reads a one-line check-in and
speaks as the giant; it never sets a number.

## Layout

```
backend/     Python 3.11, FastAPI: controllers, TabPFN cap, importers, check-in, API
app/         TypeScript + Vite pixel-art game; the same build is wrapped as an Android APK (Capacitor)
scripts/     evaluation and data scripts; every number in the post comes from here
results/     what the scripts wrote
specs/       the brief, requirements, design and tasks (AI-PDLC)
```

## Run it

```bash
python -m venv backend/.venv
backend/.venv/Scripts/pip install -e "backend[dev,model]"   # model = CPU torch + TabPFN
backend/.venv/Scripts/pytest backend
backend/.venv/Scripts/uvicorn --factory slowstart.api:app_factory --reload
```

```bash
cd app && npm install && npm run dev                # the game, with /api proxied to :8000
python scripts/levels.py                            # progress on the four hand-written levels
python -I scripts/evaluate_steps.py --features v1   # the steps evaluation (cached after the first run)
docker build -t slowstart . && docker run -p 8000:8000 slowstart   # one image: app + API + TabPFN
```

The Android app is the same build wrapped with Capacitor: `cd app && npm run build && npx cap sync android`,
then build `app/android` with Android Studio or `gradlew assembleDebug` (set `VITE_API_BASE` to the server's
address first, or the app runs offline-only).

Tests use a fake predictor and need no model, network or GPU. The real predictor downloads TabPFN v2
weights from Hugging Face on first use.

## Known limits

- The public step data is short and old; a backtest cannot show whether a goal changes behaviour.
- The place search uses OpenStreetMap's public Overpass servers. They were not reachable from the
  development machine (the main server answered 406 to every request), so the live query is covered by
  tests and a mocked end-to-end run, not by a live one. The app degrades to "no suggestions".
- The Android build is a debug-signed APK, installed by hand.

## After the deadline

The entry was submitted on 2026-10-26 (the deadline was 2026-10-25, 23:59 PDT). The project as judged
is the `main` branch up to [`f1528e7`](https://github.com/Tanay3484/slow-start/commit/f1528e7) (release
v0.2.0). Every change after that is listed here with its date.

**Changed after the deadline**

- 2026-10-26: this section of the README. No code has changed.

**Planned, to be built once Week 3's winners are announced**

From reader feedback on the DEV post (thanks to
[@ahmedznouda](https://dev.to/ahmedznouda/comment/3j157), who found all three):

- **Keep excused days out of TabPFN's features.** The controller already ignores a sick day, but its
  steps still reach the predictor's features (last three days, weekly minimum, fortnight median). A week
  of flu keeps the cap low after the window was protected. Excused days should be dropped from the
  features, as "not carried" days already are.
- **"I don't feel great today" should excuse the day.** The excuse word list needs phrases with no sick
  word in them.
- **"Was sick last week, back at it today" should not.** Sickness in the past tense must not excuse
  today. Both sentences become tests.

A feedback form in the app:

- **Report a bug or ask for a feature without a GitHub account.** A form in the game (type, title,
  description, and an optional GitHub username to be tagged when it is fixed) is posted as an issue by a
  bot account. The bot's token can only open issues; a GitHub Action applies the labels `type/bug`,
  `type/feature-request` or `type/data-bug`. The form is rate-limited, strips email addresses, and warns
  that the issue is public.

## Credits

- **Golden Hour** (same author, Week 1, MIT): the Ollama client pattern and the OpenStreetMap place
  queries are adapted from it.
- **Fitbit Fitness Tracker Data** (Mobius, Kaggle, CC0): the public step history behind the evaluation
  and the bundled cold-start prior.
- **TabPFN v2** (Prior Labs, Apache 2.0 with attribution): the predictor.
- **Gemma** (Google) through Ollama: check-in reader and the giant's voice.

## Licence

MIT, see [LICENSE](LICENSE).

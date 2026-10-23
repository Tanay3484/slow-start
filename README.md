# Slow Start

A fitness game for lazy people. Your daily step goal and your next workout are set the way TCP sets how
fast a connection may send: **start small, double after each success, grow slowly once you're near your
level, and halve after a miss, never to zero.** A second limit, TabPFN's prediction of what you'll
probably manage tomorrow, stops it asking for too much on a day the history says will be a low one.

You look after **Slumbrock**, a pixel-art stone giant that wakes up as you keep going. The idea comes from
a monster whose ability, also called Slow Start, halves its stats for its first five turns. The creature,
art and names here are original; nothing is taken from Pokémon or Nintendo.

Built for the DEV Hacktoberfest 2026 Open-Source AI Challenge, Week 3: *Slow and Steady*.

> **Status (2026-10-23):** the app, backend, evaluation and Android build work. Four core functions
> (the step and exercise controllers, the evaluation statistics, and the XP rule) are being written by hand
> by the author; until each lands, a labelled baseline stands in and the app says so. The specs in
> [`specs/`](specs/) say what is built and what is not. Numbers are in [`results/`](results/).

## What the first evaluation found

On the public Fitbit data (33 people, two months, 2016), TabPFN's 30th-percentile cap and a plain "your own
30th percentile over the last 28 days" are **indistinguishable**: TabPFN was ahead by 3.9 points on the
validation window and behind by 3.1 on the final one. Both are met on about two days in three, against
one in three for a fixed 10,000, but they also ask for much less (a mean goal near 6,900 steps against
10,000), so that gap says little on its own. The comparison, the protocol and the limits are in
[`results/steps.summary.md`](results/steps.summary.md).

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

## Credits

- **Golden Hour** (same author, Week 1, MIT): the Ollama client pattern and the OpenStreetMap place
  queries are adapted from it.
- **Fitbit Fitness Tracker Data** (Mobius, Kaggle, CC0): the public step history behind the evaluation
  and the bundled cold-start prior.
- **TabPFN v2** (Prior Labs, Apache 2.0 with attribution): the predictor.
- **Gemma** (Google) through Ollama: check-in reader and the giant's voice.

## Licence

MIT, see [LICENSE](LICENSE).

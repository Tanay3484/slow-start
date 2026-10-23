# Slow Start

A fitness game for lazy people. Your daily step goal and your next workout are set the way TCP sets how
fast a connection may send: **start small, double after each success, grow slowly once you're near your
level, and halve after a miss, never to zero.** A second limit, TabPFN's prediction of what you'll
probably manage tomorrow, stops it asking for too much on a day the history says will be a low one.

You look after **Slumbrock**, a pixel-art stone giant that wakes up as you keep going. The idea comes from
a monster whose ability, also called Slow Start, halves its stats for its first five turns. The creature,
art and names here are original; nothing is taken from Pokémon or Nintendo.

Built for the DEV Hacktoberfest 2026 Open-Source AI Challenge, Week 3: *Slow and Steady*.

> **Status (2026-10-23):** under construction. The specs in [`specs/`](specs/) say what is built and what
> is still a stub. Numbers will appear in [`results/`](results/) when the evaluation has run.

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

Tests use a fake predictor and need no model, network or GPU. The real predictor downloads TabPFN v2
weights from Hugging Face on first use.

## Credits

- **Golden Hour** (same author, Week 1, MIT): the Ollama client pattern and the OpenStreetMap place
  queries are adapted from it.
- **Fitbit Fitness Tracker Data** (Mobius, Kaggle, CC0): the public step history behind the evaluation
  and the bundled cold-start prior.
- **TabPFN v2** (Prior Labs, Apache 2.0 with attribution): the predictor.
- **Gemma** (Google) through Ollama: check-in reader and the giant's voice.

## Licence

MIT, see [LICENSE](LICENSE).

# Week 3 — Slow and Steady — agent guide

Hacktoberfest 2026 Week 3 entry. The master guide in `../CLAUDE.md` holds the workflow and playbook; this
file holds what is specific to this week.

**Product: Slow Start** (picked 2026-10-20): goals for lazy people set by TCP-style congestion control,
with a creature to look after in the style of a monster-collecting game. The idea came from Regigas's
ability. Use an original creature only: no Pokémon names, sprites or branding. Tanay is into fitness and
will be its first user. A web app plus an Android APK (Capacitor) from one codebase, Python backend with
TabPFN v2 and Gemma. Finalists from the four idea rounds (2026-10-20), kept for the post:

1. **Sloth Scroll**: a browser extension that slows scrolling as the feed turns distressing. Small open
   model fine-tuned on GoEmotions (Tinker). For anxious people.
2. **Where Did I Put It?**: photograph drawers once; an open vision model indexes them; search finds the
   item. Test: 50 hidden items. Gemma vision, vector search (Atlas or Tiger Data).
3. **Slow Start**: TCP-style AIMD goals for lazy people; TabPFN predicts tomorrow's steps; backtest on
   public wearable step data (Fitbit CC0, LifeSnaps). TabPFN, Temporal, Gemma.
4. **Wait For It**: a patient price-watching agent that says when to buy. SerpApi, Browserbase, TabPFN,
   Temporal. Risk: public price-history data for the backtest.

Rejected in the rounds: developer tools (wrong brief), Golden Hour-style weather apps, India-specific
ideas, anything that watches the user through a webcam or microphone.

## The challenge

- Page: <https://dev.to/challenges/hacktoberfest-week3-2026-10-19>. Partner descriptions:
  <https://dev.to/challenges/hf26>.
- Theme: **Slow and Steady** (International Sloth Day, 2026-10-20). Build something with open-weight
  models or open-source AI **that rewards laziness**: a tool for relaxation, an automation for a task you
  dread, or anything that does the work so you don't have to. The open pieces must make the project work.
- Their examples: an overnight group-chat summariser, an offline bedtime story or soundscape, a
  fridge-photo grocery list, a file and inbox tidier. Early entries (2026-10-20) are already crowded with
  file sorters, inbox triage, standup writers, grocery lists and Docker-log summarisers: avoid those.
- The post must say why open innovation matters for the build. **Bonus: the lazy payoff**, measured. How
  much time or effort does it actually save?
- Due **2026-10-25 23:59 PDT** (2026-10-26 06:59 UTC). Winners the week of 2026-10-26.
- Judging, heaviest first: writing quality, relevance to prompt and theme, creativity, technical
  execution, partner tech (optional). Ties go to the most positive reactions on DEV.
- Rules: new project started and finished in the window (note post-deadline commits in the README),
  English, 18+, one entry, one win per challenge, credit any non-trivial prior work.
- Template sections: What I Built, Demo, Code, How I Built It, Why Does Open Innovation Matter?, My Agent
  Session (optional, DevRelay), The Lazy Payoff (optional), Prize Categories. Tags `devchallenge`,
  `hf26challenge`.

## Prize categories (21 winners)

Overall $250. Featured $200: Render, TabPFN, Tinker, Arduino, DigitalOcean, Gemma. Partner $100: Auth0 for
AI Agents, Backboard, Browserbase, ElevenLabs, Entire, GitHub Copilot, Mastra, MongoDB Atlas, Sentry Agent
Tracing, SerpApi, Temporal, Tiger Data, Ultramarine (Paper Instruments), .tech Domain.

New this week:

- **Auth0 for AI Agents**: sign users in to an agent, call tools on their behalf with Token Vault, have a
  person approve a risky action first, or limit RAG retrieval with fine-grained authorisation.
- **Browserbase**: give an agent a real browser (Stagehand SDK), pull context an open model reasons over,
  or turn a one-off agent run into a repeatable workflow.
- **Ultramarine**: Paper Instruments' hosted model through the OpenAI or Anthropic SDK; state what the run
  cost; $5 credit at hacktoberfest.com/my/promos. It is a hosted model, so it conflicts with the
  open-weight-only rule unless it is used only off the runtime path. Check before entering.

Carried over (see Week 2's guide for detail): Render (AI runtime or agent front end; **won in Week 1**),
TabPFN (v2 weights are open; 3.5 needs a non-commercial licence), Tinker (fine-tune and beat a baseline
on performance, latency or cost), Gemma (most crowded: about 186 entries in Week 1), Entire (share the
agent sessions, or search past agent work to explain why code exists), Temporal (durable agent that
survives a kill), Tiger Data (pgvector, hybrid search, Tiger MCP), Sentry (traces with latency, tokens,
cost and a bug they found), GitHub Copilot (coding agent, CLI, Actions), .tech (free domain from promos).

## What Week 1 winners did (read 2026-10-20)

- Tinker winner (TrailTruth): public NPS alerts with the rangers' own categories as the answer key,
  126 held-out alerts, base vs fine-tuned vs keyword heuristic, McNemar p-values, a "what went wrong"
  list, a Temporal kill test, Entire checkpoints. The number is in the title.
- Temporal winner (Fieldcast): a held-out year, two baselines, and an ablation that broke their own
  result (the forecast was a forecast of people, not butterflies), reported as the headline.

## Where things stand (2026-10-23, late)

Built: the app, backend, importers, evaluation (steps done; training waits for Tanay's Hevy export), Android
debug APK, Dockerfile and Blueprint (image tested with no network). Waiting on Tanay: H1-H4, the Render
decision (four paid services already run; see memory), making the repo public, own data exports. Not
verified: live OpenStreetMap from this machine (Overpass answers 406 to this IP), the APK on a device.

Steps evaluation finding to keep honest in the post: TabPFN's cap and the plain own-30th-percentile are
indistinguishable on this data (validation +3.9, final -3.1 points). The feature set was picked by a rule
written before the v2 result (see `results/steps.summary.md`).

## Where things stood earlier (2026-10-23)

Tanay was away on TOEFL prep until 2026-10-23 and asked for the whole build to be done by the agent, with
four `@human` tasks left for Tanay (H1-H4 in `specs/001-slow-start-mvp/tasks.md`). The brief,
requirements, design and tasks are `Status: Draft`: they were written alongside the build at Tanay's
request, so code is provisional until Tanay approves them.

## The four `@human` levels

H1 step controller (`backend/slowstart/controllers/steps.py`), H2 exercise controller
(`controllers/exercise.py`), H3 evaluation statistics (`evaluation/stats.py`), H4 XP and stage rule
(`app/src/game/xp.ts`). Rules for agents:

- Never write, complete or paste the body of an `@human` function. Use the `task-coach` subagent for hints,
  tests-first and reviews. Tanay may hand a task over explicitly.
- Never weaken or delete a contract test in `backend/tests/test_human_levels.py` or `app/src/game/xp.test.ts`
  to make a level pass. If a test is wrong, propose the fix.
- Code that calls them goes through `controllers/guard.py` and must work while they are stubs.
  `@ai` tests must pass whether the levels are locked or unlocked.

## Commands

- Setup: `python -m venv backend/.venv` then `backend/.venv/Scripts/pip install -e "backend[dev,model]"`
- Backend tests / lint: `backend/.venv/Scripts/python -m pytest backend` · `ruff check backend scripts`
  · `ruff format --check backend scripts`
- Run: `backend/.venv/Scripts/uvicorn --factory slowstart.api:app_factory` (port 8000). Gemma needs Ollama
  (`SS_MODEL=gemma3:1b`); without it check-ins use templates.
- App: `cd app && npm install && npm run dev` (Node 18: Vite 5 and Capacitor 6 only).
- Data: the public Fitbit set is downloaded with `kaggle datasets download -d arashnic/fitbit -p data/raw/fitbit`
  (kept out of git). Tanay's own exports go in `data/private/` (also out of git).
- Evaluation: `scripts/evaluate_steps.py [--features v1|v2] [--until DATE] [--label final|validation]`
  (TabPFN predictions are cached in `results/cache/`), `scripts/summarise_steps.py` (the four-run table),
  `scripts/evaluate_training.py <hevy.csv>` (needs Tanay's export in `data/private/`).
- Progress on the four hand-written levels: `python scripts/levels.py`.
- Art: `python scripts/draw_sprites.py --preview` (sprites are drawn in code; the JSON is generated).
- Docker (Desktop must be running): `docker build -t slowstart .`; test with `--network none --memory=2g`.
- Android: `cd app && npm run build && npx cap sync android`; then `gradlew assembleDebug` in `app/android`
  with `JAVA_HOME` set to Android Studio's `jbr`. In PowerShell do not append `2>&1` to `java -version`.
- Run Python that reads downloaded data with `-I`.

## Conventions

- Python 3.11, FastAPI, pydantic; TypeScript + Vite for the app. One settings module, env prefix `SS_`.
- Model, TabPFN and OpenStreetMap sit behind small interfaces that tests fake. No network in tests.
- TabPFN v2 weights only (Apache 2.0). 2.5 and later are non-commercial.
- Pixel art is original and 2D. No Pokémon or Nintendo names, sprites or branding.
- The server never stores what a person sends. Personal data never goes in the repo.
- Every number in the post comes from a script in `scripts/` and a file in `results/`.
- Post draft in `drafts/devto-submission.md` (git-ignored). Tanay publishes.
- Repo: `Tanay3484/slow-start`. `main` is protected like Week 2 (PR, 1 approval, `tests` check). Work on a
  branch and open a PR; never push to `main`.

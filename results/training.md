# Training results

Generated 2026-10-26. 415 supported sessions loaded; 35 scored across 6 exercises in 2026-07-05 to 2026-10-02.

## The app's fixed scheme (planned before the data)

| Policy | Target met | Level vs last session | Met vs repeat-last (95% CI) |
|---|---|---|---|
| Repeat last session | 0.0% | 1.00 | (baseline) |
| Fixed plan (+1 step every session) | 0.0% | 1.06 | +0.0 pts (+0.0 to +0.0) |
| Controller (add a step, cut after a miss) | 25.7% | 0.12 | +25.7 pts (+0.0 to +45.3) |

## Scored on the top set (R8.6, exploratory: added after the fixed scheme failed)

One working set per session at the usual top-set reps from before the window (bench_press 5, deadlift 2, dumbbell_bench_press 8, dumbbell_shoulder_press 6, pull_up 7, push_up 12). 35 sessions scored.

| Policy | Target met | Level vs last session | Met vs repeat-last (95% CI) |
|---|---|---|---|
| Repeat last session | 31.4% | 1.00 | (baseline) |
| Fixed plan (+1 step every session) | 8.6% | 1.06 | -22.9 pts (-46.2 to +0.0) |
| Controller (add a step, cut after a miss) | 77.1% | 0.82 | +45.7 pts (-2.6 to +81.8) |

**Target met**: the real next session reached the suggested sets, reps and load. **Level**: how demanding the target was compared with the last session; below 1.00 means it asked for less than last time. The interval resamples exercises, not sessions.

## Limits

- One person's log. The backtest replays what Tanay did *without* the app, so a suggestion can only be judged by what was done anyway.
- No TabPFN here: with about a dozen exercises and a few dozen sessions each, a predictor would be fitted on too little to claim anything. It is used for steps only.
- The fixed scheme (for example 3 x 8 at one weight) is rarely what a lifter who works up to a top set does, so its low level means the scheme does not fit the lifter. The top-set table was designed after seeing that, on the same log, so it is exploratory, not a held-out test.

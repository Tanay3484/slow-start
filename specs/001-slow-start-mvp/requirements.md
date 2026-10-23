# Requirements — Slow Start MVP

Status: Draft
Owner: Tanay
Updated: 2026-10-23
Brief: [../000-brief/brief.md](../000-brief/brief.md)

Written ahead of approval at Tanay's request (2026-10-23, deadline 2026-10-26 06:59 UTC). Code built from
this spec is provisional until Tanay approves it.

## Terms

- **Window (cwnd):** the controller's own goal, before any cap. Named after TCP's congestion window.
- **Cap (rwnd):** the highest goal the predictor thinks the person will probably reach. Named after TCP's
  receiver window.
- **Goal:** `min(window, cap)`, the number shown to the person today.
- **Met:** steps ≥ goal. For a lift, the suggested sets were completed.
- **Not worn:** a day with 0 steps in imported data. It is treated as missing, not as a miss.
- **Excused:** a day the person said they were ill or injured. It neither grows nor cuts the goal.

## R1 Step goals

- R1.1 WHEN the app asks for today's step goal, the system SHALL return a goal computed from the person's
  history by the step controller, with the phase it is in (`slow_start`, `cruising`, `recovering`).
- R1.2 WHILE the window is below the slow-start threshold, the controller SHALL double it after a met day.
- R1.3 WHILE the window is at or above the threshold, the controller SHALL add a fixed step after a met day.
- R1.4 WHEN a day is missed, the controller SHALL halve the window, set the threshold to the new window, and
  never go below the floor. The goal SHALL NOT drop to zero.
- R1.5 WHEN a day is excused or not worn, the controller SHALL leave the window and threshold unchanged.
- R1.6 The controller SHALL be a pure function of the history: same history, same decision.
- R1.7 WHILE the person has at least 7 days of history, the system SHALL cap the goal at the predictor's
  30th percentile for the day, so that the goal is reached about 7 days in 10.
- R1.8 IF the predictor is unavailable or fails, THEN the system SHALL cap the goal at 80% of the trailing
  14-day median, and SHALL say `cap_source: "median"` in the response.
- R1.9 The goal SHALL never exceed the ceiling (20,000 steps) nor fall below the floor (1,000 steps).

## R2 Exercise goals

- R2.1 WHEN the app asks for a target for an exercise, the system SHALL return the next sets, reps and (for
  weighted lifts) load, computed from that exercise's session history by the exercise controller.
- R2.2 The supported exercises SHALL be: squat, bench press, deadlift, overhead press, barbell row, a few
  dumbbell lifts, and push-up, pull-up, dip, bodyweight squat.
- R2.3 WHEN a session meets its target, the controller SHALL add one step: one rep for bodyweight, one load
  increment for weights.
- R2.4 WHEN a session misses its target, the controller SHALL cut it: the load by about 10%, or the reps by
  about 20% for bodyweight, rounded to the equipment's increment.
- R2.5 Training SHALL be optional. Skipping it SHALL cost no XP and SHALL NOT change a step goal.
- R2.6 WHERE a person has at least 20 past sessions of an exercise, the system SHOULD show the predictor's
  chance of completing the target.

## R3 Import

- R3.1 The system SHALL import daily steps from a Fitbit/Google Takeout step export, from a CSV with
  `date,steps` columns, and from Fitabase `dailyActivity` CSVs.
- R3.2 The system SHALL import workouts from a Hevy CSV export, ignoring warm-up sets and unsupported
  exercises, and SHALL report how many sessions and which exercises it found and how many rows it skipped.
- R3.3 WHEN an import contains days with 0 steps, the system SHALL treat them as not worn and say how many.
- R3.4 The server SHALL process an import in memory and SHALL NOT store it or log its contents.
- R3.5 Personal data SHALL NOT be committed to the repository. Committed fixtures are synthetic or derived
  from the public dataset.

## R4 Game

- R4.1 WHEN a day starts, the system SHALL spawn one wild creature whose HP equals the day's step goal.
- R4.2 WHEN steps are logged, the creature's HP SHALL fall by that many steps. At zero HP the person wins.
- R4.3 WHEN the person wins a day, they SHALL earn XP by the XP rule (an `@human` function).
- R4.4 Slumbrock's stage SHALL come from total XP: asleep, drowsy, awake, roaring.
- R4.5 WHEN a day is missed, the creature SHALL escape, tomorrow's goal SHALL be cut by the controller, and
  no XP SHALL be removed. There SHALL be no streak.
- R4.6 Steps SHALL raise Slumbrock's Speed and training SHALL raise its Power. Both SHALL start at half and
  reach full at the last stage.
- R4.7 Logging a workout SHALL give bonus XP. It SHALL NOT be required to win.
- R4.8 The app SHALL keep a collection of every creature the person has met.
- R4.9 The app SHALL offer a demo that replays a real person from the public dataset day by day, with no
  sign-in and no import.
- R4.10 All artwork SHALL be 2D pixel art, original, with no Pokémon or Nintendo names, sprites or branding.

## R5 Check-in

- R5.1 WHEN the person writes a one-line check-in, the system SHALL read it into `energy`
  (`low|ok|high`), `body` (areas that hurt), and `excused` (`true|false`), and reply with a line from
  Slumbrock.
- R5.2 The model SHALL only label the text. Code SHALL decide whether the day is excused and SHALL apply it.
- R5.3 IF the model is unavailable or returns invalid output, THEN the system SHALL use a keyword reader
  and a template line, and SHALL say `source: "template"`.
- R5.4 The reply line SHALL contain no number the person did not give.

## R6 Places and exploring

- R6.1 WHEN the person asks, the app SHALL list real nearby places for the day's activity (park or
  promenade for a walk, gym or outdoor gym for training) from OpenStreetMap.
- R6.2 The person's exact location SHALL stay on the device. Only a coarse area query leaves it, to
  OpenStreetMap's public Overpass service.
- R6.3 WHEN an activity is logged inside a place cell the person has not logged from before, the system
  SHALL count it as an exploration, give a rare creature, and add bonus XP.
- R6.4 IF the place service is unreachable, THEN the app SHALL still work without suggestions.

## R7 Platform

- R7.1 The web app SHALL work logged out, on a phone-sized screen, in a current browser.
- R7.2 The same code SHALL build an Android APK (Capacitor) that installs and plays offline once the day's
  goal is loaded.
- R7.3 The person's data SHALL live on the device. The app SHALL offer export and delete.
- R7.4 WHEN the backend is unreachable, the app SHALL use the last goal it received, or a documented
  fallback goal, and say so.

## R8 Evidence

- R8.1 One command SHALL reproduce the steps results: policies fixed 10,000, trailing median, own 30th
  percentile, controller, controller with TabPFN cap, with goal-met rate and goal level.
- R8.2 One command SHALL reproduce the training results from a Hevy CSV: repeat last, fixed plan,
  controller, with met rate and progression.
- R8.3 A test SHALL prove that no policy sees data from the day it sets a goal for or later.
- R8.4 The results SHALL be written to `results/` with the data source, the date, the rows used and the
  exclusions (not-worn days).
- R8.5 The post SHALL quote only numbers from `results/`.

## R9 Open and operable

- R9.1 No closed AI API SHALL be called at runtime. TabPFN SHALL use the v2 weights (Apache 2.0).
- R9.2 External calls (model, OpenStreetMap, TabPFN) SHALL sit behind small interfaces so tests run with
  fakes and no network.
- R9.3 Settings SHALL come from one module with the `SS_` prefix.
- R9.4 The README SHALL credit Golden Hour for the place code and the Kaggle dataset for the step data.
- R9.5 Code that calls an `@human` function SHALL go through a guard and SHALL work while it is a stub.

## Non-goals

As in the brief: live Health Connect sync, routes, store listings, notifications, iOS, multiplayer,
calories, diet, sleep, medical advice.

## Open questions

1. Is a 20,000-step ceiling and a 1,000-step floor right for older walkers? (Decide at review.)
2. Should a day with 0 steps typed by hand count as a miss? (Draft: yes. Only imported zeros are "not
   worn".)

## Changelog

- 2026-10-23: First draft, written alongside the build at Tanay's request.

# Brief — Slow Start

Status: Draft
Owner: Tanay
Updated: 2026-10-20

## Product

A fitness game for lazy people. Slow Start sets your daily step goal and your next workout the way TCP
sets how fast a connection may send:

- **Start small and double after each success.** This is the slow-start phase.
- **Once near your usual level, grow by a small fixed step.** This is the additive increase.
- **After a miss, cut the goal and carry on.** This is the multiplicative decrease, and the goal never
  drops to zero.

TabPFN predicts tomorrow from your own history, so a goal is never set above what you will probably
manage. You never set a goal yourself.

Around it is a small 2D pixel-art monster game. You look after **Slumbrock**, an original stone giant that
wakes up as you keep going. The idea comes from a monster whose ability, also called Slow Start, halves
its stats for its first five turns. Our creature, art and names are our own. Nothing is taken from
Pokémon or Nintendo.

## User

- **Who:** Tanay, who trains with Hevy (a long log, Pro account), wears a Pixel Watch 3 and carries a
  Pixel 9 Pro. Tanay is the first user and the data source.
- **Who else it is for:** anyone who has quit a fitness app because its goals were set for someone else,
  including people who never go to a gym. You can raise Slumbrock on evening walks alone: a parent who
  walks after dinner is as welcome as someone with a barbell. Workouts add to the game but are never
  required, and skipping them costs nothing.
- **The moment:** the morning after a missed day. A normal app shows a broken streak. Slow Start shows a
  smaller goal you can win and a giant that is only a little sleepier.

## Lazy payoff

You make no decisions. The app picks the step goal every day, and the reps or weight for each exercise.
We count the decisions it takes off you (from the Hevy log, sets planned per week) and report the steps
and training kept up while you decided nothing.

## How it works

1. **Data in.** Steps from the Pixel Watch (a Google Takeout export now; live sync later). Workouts from
   Hevy (a CSV export, or the Pro API if time allows). Users can also type the day's steps or a one-line
   check-in.
2. **Three ways to feed the giant, each with its own controller.**
   - **Walking and running:** steps.
   - **Bodyweight:** push-ups, pull-ups, dips, squats. The controller sets reps.
   - **Weights:** squat, bench press, deadlift, overhead press, barbell row, and a few dumbbell lifts. The
     controller sets the load.

   Each controller is a pure function with tests. How hard a miss cuts the goal differs per activity: a
   step goal halves, while a lift drops back about 10%, which is a normal deload.
3. **TabPFN predicts.**
   - For steps: tomorrow's likely count. The goal is capped at a level you reach with high probability.
   - For exercises: the chance you complete the suggested set next session.
4. **Gemma reads and talks.** It turns a check-in ("leg day, knees sore, short walk") into fields code
   can score, and writes Slumbrock's lines. It never sets a number.
5. **The game.**
   - Each day a wild creature appears, and its HP is today's goal. Walking and training wear it down.
   - A win gives XP, and Slumbrock wakes up through four stages: asleep, drowsy, awake, roaring.
   - A miss means the creature gets away and tomorrow's goal is cut. There is no streak to lose.
   - Steps feed Slumbrock's Speed and training feeds its Power. Like its namesake, it starts with both
     halved.
6. **Places, reusing Golden Hour's OpenStreetMap code (credited).**
   - The app suggests real nearby spots for the day's activity: a park or promenade for a walk, an
     outdoor gym or a gym for training.
   - Each kind of place has its own wild creatures (parks, waterfronts, gyms).
   - **Explore bonus:** logging activity from a place you have never logged from before brings a rare
     creature and extra XP. Code checks you were really there, from the device's location. The location
     stays on the device apart from the coarse area query Golden Hour already makes.
7. **One codebase, two apps.** A web app that works logged out, and the same app as an Android APK
   (Capacitor) on GitHub Releases. The Python backend (TabPFN and Gemma) runs on Render. All art is 2D
   pixel art drawn in code and rendered crisp.

## Evidence plan

**Claim 1 (steps):** goals from the controller with TabPFN are met on more days than a fixed 10,000 or
your own median, without simply shrinking the goal.

- **Data:**
  - The Kaggle Fitbit set, listed as CC0: real daily steps from about 30 people over about 2 months. A
    longer open dataset only if time allows and the results need it. Otherwise the post states the
    limit and the plan.
  - Tanay's own Pixel Watch history.
- **Policies compared:** a fixed 10,000; your trailing 28-day median; the controller alone; the
  controller with TabPFN.
- **Metrics:** the share of days the goal was met, and **goal level** (the mean goal divided by the
  person's median before the test window). Goal level is the guardrail: a policy that wins by setting tiny
  goals loses on it.
- **Held out:** every policy sees only days before the one it sets a goal for. TabPFN is fitted on each
  person's earlier days only, and the last 2 weeks of every person are scored.

**Claim 2 (training):** the controller's next-session suggestions are ones Tanay actually manages, more
often than a fixed plan, while still progressing.

- **Data:** Tanay's Hevy log, limited to the lifts and bodyweight exercises named above.
- **Policies compared:** repeat last session; a fixed plan (+2.5 kg, or +1 rep, each session); the
  controller; the controller with TabPFN.
- **Metrics:**
  - The share of suggestions met or beaten next session, compared by estimated one-rep max for lifts and
    by reps for bodyweight.
  - The progression rate.
  - TabPFN's calibration (Brier score) against the base rate.
- **Held out:** the log is split by date, and the last 3 months are scored.

**Limits we will state:**
- A backtest replays what people did without the app, so it cannot show how a goal changes behaviour.
- Days of live use cover that only for one person, and briefly.
- The public step data is short and old (2016).
- Steps and training are measured, not effort or health.

All numbers come from one command in `scripts/`.

## First user

Tanay uses it daily from Friday 2026-10-23 until submission. Before that, Tanay's own history gives a
backtest of how the app would have set goals over the past months. If a parent or a gym friend tries it
(a walker would be ideal), the post quotes them; if not, it says so.

## Prize categories

| Category | Build decision that justifies it |
|----------|----------------------------------|
| TabPFN | It predicts every goal cap and every exercise's chance of success, inside the controller loop |
| Render | Backend, TabPFN and Gemma run there from one Blueprint |
| Gemma | Reads every check-in and writes Slumbrock's lines |
| .tech Domain | Only if the web app is served from a free .tech domain |

## Decisions

- **Backend:** Python (TabPFN is a Python library). **App:** TypeScript and Vite, wrapped with Capacitor
  for Android.
- **TabPFN v2 weights:** Apache 2.0 with an attribution clause. Versions 2.5 and later are non-commercial,
  so we use v2.
- **Art:** 2D pixel art only, drawn as small palette grids in code, so sprites live in the repo as text
  and are easy to change. Names: Slumbrock and the wild creatures are original.
- **Golden Hour's place code** (Overpass client and ranking) is reused and adapted for activity places,
  and credited in the README and the post.
- **Personal data stays out of the repo.** The demo runs on public data; imports are Tanay's own.
- Storage, where imports are parsed, model size and hosting cost are settled in design.

## Non-goals

- Live sync from Health Connect or Fitbit.
- Turn-by-turn routes or maps beyond a list of nearby places.
- Play Store listing, push notifications, iOS.
- Multiplayer, battles between friends, trading.
- Calories, diet, sleep, or any medical advice.

## Cut line

If time runs short, drop in this order:

1. .tech domain
2. Hevy API sync (keep CSV import)
3. Explore bonus (keep place suggestions)
4. Place suggestions
5. battle animations (keep static scenes)
6. Gemma lines (templates instead)
7. the APK (web only)

The two backtests, the three controllers and the core game loop are never cut.

## Open questions

None.

## Changelog

- 2026-10-20: First draft after Tanay picked Slow Start, with steps and workouts and a game layer.
- 2026-10-20: Tanay's answers. Pixel art only; the giant is named Slumbrock. Kaggle Fitbit data first, a
  longer set only if needed. Lifting limited to the main compounds plus a few bodyweight and dumbbell
  exercises, and walking alone is a full way to play (for older and non-gym users). Added place
  suggestions from Golden Hour's code and an explore bonus, both above the APK in the cut line.

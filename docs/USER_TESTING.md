# User testing: your own data, not the demo

What it takes to test Slow Start for real with your own steps and workouts, and what gets measured.

## 1. Export your history (about 10 minutes of clicking; Takeout can take hours to arrive)

### Steps from the Pixel Watch (Fitbit)

1. On the phone, open the **Fitbit** app, then your profile picture.
2. Look for **Manage data and privacy** (or Settings → **Your data**), then **Export your data**. It opens
   **Google Takeout** with Fitbit selected. You can also go straight to <https://takeout.google.com>, press
   **Deselect all**, and tick only **Fitbit**.
3. Choose **Export once**, file type **.zip**, and create the export. Google emails a download link when
   it is ready, which can take a few hours.
4. Unzip it. Daily steps are in files named like `steps-2026-09-01.json` (one per month), usually under
   `Takeout/Fitbit/Global Export Data/`.

Menu names change between app versions. If the folder looks different, put the whole zip in
`data/private/` and the importer is adapted to it. Nothing in `data/private/` is ever committed.

### Workouts from Hevy

1. In the **Hevy** app: **Profile** → the gear (**Settings**) → **Export & Import Data** →
   **Export Workouts**. It saves or shares a `workouts.csv`. On the web, the same option is under
   Settings at hevy.com.
2. Save it as `data/private/hevy.csv`.
3. Optional, for live sync later: **Settings → Developer** on hevy.com creates an API key (Pro). Keep it in
   your password manager; it is not needed for the test.

## 2. Load it into the app

1. Open the game and choose **Start for real** (not the demo).
2. Go to the **Data** tab:
   - **Import steps**: select all the `steps-*.json` files at once (or one CSV with `date,steps`).
   - **Import workouts**: select `hevy.csv`.
3. The import reads the files on the server in memory and keeps nothing; the history is saved on the
   device. Days with 0 steps are treated as "watch not worn".

Until the server is deployed, run it on the laptop (see the README) and open <http://localhost:8000/play>.
To use it from the phone on the same Wi-Fi, start the server with `--host 0.0.0.0` and open
`http://<the laptop's IP>:8000/play` on the phone.

## 3. The test (Saturday evening to Sunday)

Each evening, in **Live** mode:

1. **Today**: type the day's step count from the watch. Watch the creature take the hits.
2. **Talk**: one line about how the day felt ("knees sore, short walk").
3. **Optional**: log a workout from Hevy in the training card.
4. Write two lines in `drafts/user-notes.md` (git-ignored): what surprised you, what annoyed you.

If you can, hand the phone to a parent or someone who does not lift for ten minutes: the demo, then
"Start for real" with one day of steps. Ask three questions and write down the answers word for word:

- Was the goal one you would try for?
- Did you understand why the goal was that number? (the "Why this number?" panel)
- Would you open it again tomorrow? What would make you?

## 4. What gets measured

With your exports in `data/private/`:

```bash
backend/.venv/Scripts/python -I scripts/evaluate_training.py data/private/hevy.csv   # results/training.md
```

The steps from your own watch get the same walk-forward backtest as the public data (how often each
policy's goal would have been met, and at what goal level); that script is added once the export is in,
because its exact format is only known then.

Reported in the post: how many days you used it, how many goals were met, how many decisions the app
took off you (one step goal a day plus one target per exercise per session), and what the second person
said, quoted. If something was not tested, the post says that too.

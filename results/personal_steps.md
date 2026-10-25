# Personal steps backtest (the first user)

Generated 2026-10-26. one person's Google Fit daily step counts (csv), cleaned by scripts/clean_personal.py: 1028 days from 2024-01-01 to 2026-10-24, 70 of them with the phone or watch not carried. Held out: the last 90 days from 2026-07-27, 90 of them scored (0 not carried) across 13 weeks. Usual day before the window (median): 3,319 steps. Step per win: 1,500.

| Policy | Goal met | Mean goal | Goal level | Met vs own 30th percentile (95% CI) |
|---|---|---|---|---|
| Fixed 10,000 | 0.0% | 10,000 | 3.01 | -68.9 pts (-75.6 to -61.5) |
| Own 28-day median | 52.2% | 3,836 | 1.16 | -16.7 pts (-24.4 to -9.9) |
| Own 28-day 30th percentile | 68.9% | 2,725 | 0.82 | (baseline) |
| TabPFN 30th percentile (cap alone) | 68.9% | 2,967 | 0.89 | +0.0 pts (-6.7 to +5.6) |
| Controller (slow start / AIMD) | 60.0% | 3,652 | 1.10 | -8.9 pts (-16.9 to -1.1) |
| Slow Start (controller + TabPFN cap) | 71.1% | 2,812 | 0.85 | +2.2 pts (-5.5 to +8.8) |

Cap sources over the window and its 28-day lead: {'tabpfn': 118}.

**Goal level**: the mean goal divided by the usual day before the window; below 1.00 asks for less than usual. The interval resamples weeks, because there is one person.

## Limits

- One person, and mostly a phone in a pocket: the watch synced to Google Fit on few days, so days the phone sat on a desk count low.
- A backtest replays days lived without the app. It cannot show whether a goal changes behaviour; it shows how often each goal would have been met.
- Under 500 steps is read as not carried (scripts/clean_personal.py); that line was drawn before this ran.

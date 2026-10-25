# Steps results

Generated 2026-10-25. Data: Kaggle 'Fitbit Fitness Tracker Data' (arashnic/fitbit), CC0, 2016-03-12 to 2016-05-12. Feature set: v1, data cut at 2016-04-28 (validation).

- **33 people, 406 person-days** scored: the last window starting 2016-04-15, only days where every policy set a goal and the person had at least 7 worn days before.
- 94 of 981 loaded person-days have 0 steps and are treated as 'tracker not worn': not scored and not fed to any policy.
- Predictor: tabpfn-v2 (tabpfn 9.2.0, 4 estimators, CPU). Fitted per calendar day on everyone's earlier rows only.

| Policy | Goal met | Mean goal (steps) | Goal level | Met vs own 30th pct (95% CI) |
|---|---|---|---|---|
| Fixed 10,000 | 36.2% | 10000 | 1.60 | -27.8 pts (-41.3 to -14.6) |
| Own 28-day median | 53.9% | 8369 | 1.03 | -10.1 pts (-13.1 to -7.3) |
| Own 28-day 30th percentile | 64.0% | 7009 | 0.83 | (baseline) |
| TabPFN 30th percentile (cap alone) | 68.0% | 6809 | 0.86 | +3.9 pts (-0.3 to +8.4) |
| Controller (slow start / AIMD) | 74.9% | 5604 | 0.75 | +10.8 pts (+5.1 to +16.2) |
| Controller + TabPFN cap | 77.8% | 5612 | 0.73 | +13.8 pts (+8.5 to +18.9) |

**Goal met** is the share of person-days with steps ≥ goal. **Goal level** is the mean of goal ÷ the person's median steps before the window: a policy cannot win by quietly setting tiny goals without this number showing it. The interval resamples people, not days.

Cap calibration (share of days at or above the 30th-percentile goal; ideal is about 70%): TabPFN 30th percentile (cap alone) 68.0%, Own 28-day 30th percentile 64.0%

## Limits

- About 33 people for about two months, in 2016. The held-out window is 14 days.
- A backtest replays what people did *without* the app. It cannot show whether a goal changes what someone does.
- Zero-step days are treated as missing, which removes honest rest days that happened to log 0.
- The controller rows are empty until H1 is written, and the goal-level and interval columns until H3 is.

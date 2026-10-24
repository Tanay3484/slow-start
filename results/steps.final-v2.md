# Steps results

Generated 2026-10-23. Data: Kaggle 'Fitbit Fitness Tracker Data' (arashnic/fitbit), CC0, 2016-03-12 to 2016-05-12. Feature set: v2, all data (final).

- **32 people, 350 person-days** scored: the last window starting 2016-04-29, only days where every policy set a goal and the person had at least 7 worn days before.
- 133 of 1373 loaded person-days have 0 steps and are treated as 'tracker not worn': not scored and not fed to any policy.
- Predictor: tabpfn-v2 (tabpfn 9.2.0, 4 estimators, CPU). Fitted per calendar day on everyone's earlier rows only.

| Policy | Goal met | Mean goal (steps) | Goal level | Met vs own 30th pct (95% CI) |
|---|---|---|---|---|
| Fixed 10,000 | 34.6% | 10000 | locked | locked |
| Own 28-day median | 46.3% | 8536 | locked | locked |
| Own 28-day 30th percentile | 69.7% | 6798 | locked | (baseline) |
| TabPFN 30th percentile (cap alone) | 66.6% | 6947 | locked | locked |

**Goal met** is the share of person-days with steps ≥ goal. **Goal level** is the mean of goal ÷ the person's median steps before the window: a policy cannot win by quietly setting tiny goals without this number showing it. The interval resamples people, not days.

Cap calibration (share of days at or above the 30th-percentile goal; ideal is about 70%): TabPFN 30th percentile (cap alone) 66.6%, Own 28-day 30th percentile 69.7%

## Limits

- About 33 people for about two months, in 2016. The held-out window is 14 days.
- A backtest replays what people did *without* the app. It cannot show whether a goal changes what someone does.
- Zero-step days are treated as missing, which removes honest rest days that happened to log 0.
- The controller rows are empty until H1 is written, and the goal-level and interval columns until H3 is.

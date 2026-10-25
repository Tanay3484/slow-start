# The controller's step per won day: sweep on validation, one final run

Rule, fixed before the sweep: the largest step whose validation goal-met rate (controller + TabPFN cap) is at least 70%. Chosen: **1500 steps**.

| Step per win | Validation goal met | Mean goal | Goal level |
|---|---|---|---|
| 250 | 88.4% | 3986 | 0.52 |
| 500 | 83.5% | 4674 | 0.61 |
| 750 | 80.3% | 5328 | 0.69 |
| 1000 | 77.8% | 5612 | 0.73 |
| 1500 (chosen) | 73.6% | 6140 | 0.79 |

Final window, step 1500:

| Policy | Goal met | Mean goal | Goal level | Met vs own 30th pct (95% CI) |
|---|---|---|---|---|
| Fixed 10,000 | 34.6% | 10000 | 1.48 | -35.1 pts (-48.3 to -21.6) |
| Own 28-day median | 46.3% | 8536 | 1.01 | -23.4 pts (-28.7 to -18.6) |
| Own 28-day 30th percentile | 69.7% | 6798 | 0.79 | (baseline) |
| TabPFN 30th percentile (cap alone) | 66.6% | 6860 | 0.84 | -3.1 pts (-9.1 to +2.2) |
| Controller (slow start / AIMD) | 67.7% | 6135 | 0.78 | -2.0 pts (-8.6 to +4.5) |
| Controller + TabPFN cap | 71.1% | 5970 | 0.74 | +1.4 pts (-4.8 to +7.4) |

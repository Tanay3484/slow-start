# Steps results: all four runs

Validation: data cut at 2016-04-28, scored on the 14 days before it. Final: all data, scored on the last 14 days. TabPFN is fitted per calendar day on everyone's earlier rows only. The feature set was chosen on the validation window by a rule written before the v2 result was seen: pick the higher goal-met rate, provided the mean goal is at least 90% of the plain 30th percentile's. Both qualified, v1 was higher (a half-point difference), so v1 is the default.

| Window | Person-days (people) | Fixed 10,000 | Own 28-day median | Own 28-day 30th pct | TabPFN v1 | TabPFN v2 |
|---|---|---|---|---|---|---|
| validation | 406 (33) | 36.2% (goal 10000) | 53.9% (goal 8369) | 64.0% (goal 7009) | 68.0% (goal 6809) | 67.5% (goal 6996) |
| final | 350 (32) | 34.6% (goal 10000) | 46.3% (goal 8536) | 69.7% (goal 6798) | 66.6% (goal 6860) | 66.6% (goal 6947) |

Each cell is the share of person-days with steps at or above the goal, then the mean goal in steps.

TabPFN minus the plain 30th percentile: validation v1: +3.9 pts; validation v2: +3.4 pts; final v1: -3.1 pts; final v2: -3.1 pts.

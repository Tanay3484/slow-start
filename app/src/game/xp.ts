// H4: the XP and stage rule.
//
// Planned as one of Tanay's hand-written levels; Tanay handed it over to Claude on 2026-10-25 to make
// the deadline, and the README and the post say so. The contract is in specs/001-slow-start-mvp/tasks.md
// under H4, and the checks are in xp.test.ts.

export class NotImplemented extends Error {}

export interface DayFacts {
  /** The step goal for the day, in steps. */
  goal: number;
  /** Steps logged, or null if nothing was logged. */
  steps: number | null;
  /** The person logged a workout. */
  trained: boolean;
  /** The person logged from a place they had never logged from before. */
  explored: boolean;
}

export type Stage = 0 | 1 | 2 | 3; // asleep, drowsy, awake, roaring

const WIN_XP = 10; // catching the day's creature
const MAX_OVERSHOOT_XP = 5; // one more for every fifth of the goal walked past it, at most five
const TRAINED_XP = 5; // a bonus, never a requirement
const EXPLORED_XP = 25; // somewhere new is worth the most: it is the hardest thing to make yourself do
// Wins at 10 to 15 XP a day reach roaring in about three weeks; the first stage arrives within days.
const STAGE_AT = [0, 30, 90, 200] as const;

/** XP earned for one day. A whole number, never negative. */
export function xpForDay(day: DayFacts): number {
  let xp = 0;
  if (day.steps !== null && day.goal > 0 && day.steps >= day.goal) {
    const past = (day.steps - day.goal) / day.goal; // how far past the goal, as a share of it
    xp += WIN_XP + Math.min(MAX_OVERSHOOT_XP, Math.floor(past * 5));
  }
  if (day.trained) xp += TRAINED_XP;
  if (day.explored) xp += EXPLORED_XP;
  return xp;
}

/** Slumbrock's stage for a total XP. */
export function stageForXp(xp: number): Stage {
  let stage: Stage = 0;
  STAGE_AT.forEach((at, i) => {
    if (xp >= at) stage = i as Stage;
  });
  return stage;
}

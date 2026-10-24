// H4: the XP and stage rule. This file is Tanay's to write by hand.
//
// The contract is in specs/001-slow-start-mvp/tasks.md under H4, and the checks are in xp.test.ts.
// Until it is written the functions throw NotImplemented, and game/rules.ts serves a fallback and
// the app shows a "fallback" badge. Do not catch the error here.

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

/** XP earned for one day. A whole number, never negative. */
export function xpForDay(_day: DayFacts): number {
  throw new NotImplemented("H4: xpForDay is yours to write (see tasks.md)");
}

/** Slumbrock's stage for a total XP. */
export function stageForXp(_xp: number): Stage {
  throw new NotImplemented("H4: stageForXp is yours to write (see tasks.md)");
}

// Everything that calls the @human XP rule goes through here (R9.5): while xp.ts is a stub, a plain
// fallback rule serves, and `xpRuleWritten()` lets the UI say so.
import { NotImplemented, stageForXp, xpForDay, type DayFacts, type Stage } from "./xp";

const FALLBACK_STAGE_AT = [0, 60, 200, 450];

export function fallbackXp(d: DayFacts): number {
  const won = d.steps !== null && d.steps >= d.goal;
  return (won ? 10 : 0) + (d.trained ? 5 : 0) + (d.explored ? 25 : 0);
}

export function fallbackStage(xp: number): Stage {
  let stage: Stage = 0;
  FALLBACK_STAGE_AT.forEach((at, i) => {
    if (xp >= at) stage = i as Stage;
  });
  return stage;
}

export function dayXp(d: DayFacts): number {
  try {
    return xpForDay(d);
  } catch (e) {
    if (e instanceof NotImplemented) return fallbackXp(d);
    throw e;
  }
}

export function stageOf(xp: number): Stage {
  try {
    return stageForXp(xp);
  } catch (e) {
    if (e instanceof NotImplemented) return fallbackStage(xp);
    throw e;
  }
}

export function xpRuleWritten(): boolean {
  try {
    xpForDay({ goal: 1, steps: 1, trained: false, explored: false });
    return true;
  } catch (e) {
    return !(e instanceof NotImplemented);
  }
}

/** XP still needed for the next stage, or null at the top. Works with whichever rule is live. */
export function nextStageAt(xp: number): number | null {
  const now = stageOf(xp);
  if (now === 3) return null;
  let lo = xp;
  let hi = Math.max(xp + 1, 1);
  while (stageOf(hi) === now && hi < 1_000_000) hi *= 2;
  if (stageOf(hi) === now) return null;
  while (lo + 1 < hi) {
    const mid = Math.floor((lo + hi) / 2);
    if (stageOf(mid) === now) lo = mid;
    else hi = mid;
  }
  return hi;
}

// Contract tests for H4 (specs/001-slow-start-mvp/tasks.md). They skip while xp.ts is a stub.
import { describe, expect, it } from "vitest";
import { NotImplemented, stageForXp, xpForDay, type DayFacts } from "./xp";

const day = (over: Partial<DayFacts> = {}): DayFacts => ({
  goal: 4000,
  steps: 4000,
  trained: false,
  explored: false,
  ...over,
});

// Runs `fn`, and skips the test while the level is still a stub.
function written<T>(ctx: { skip: () => void }, fn: () => T): T {
  try {
    return fn();
  } catch (e) {
    if (e instanceof NotImplemented) ctx.skip();
    throw e;
  }
}

describe("H4 xpForDay", () => {
  it("is a whole, non-negative number", (ctx) => {
    for (const d of [day(), day({ steps: 0 }), day({ steps: null }), day({ steps: 9000, trained: true })]) {
      const xp = written(ctx, () => xpForDay(d));
      expect(Number.isInteger(xp)).toBe(true);
      expect(xp).toBeGreaterThanOrEqual(0);
    }
  });

  it("gives a missed step day no step XP, and a won day more", (ctx) => {
    const miss = written(ctx, () => xpForDay(day({ steps: 1000 })));
    const win = xpForDay(day({ steps: 4000 }));
    expect(miss).toBe(0);
    expect(win).toBeGreaterThan(miss);
  });

  it("never gives less for more steps", (ctx) => {
    const a = written(ctx, () => xpForDay(day({ steps: 4000 })));
    const b = xpForDay(day({ steps: 6000 }));
    const c = xpForDay(day({ steps: 12000 }));
    expect(b).toBeGreaterThanOrEqual(a);
    expect(c).toBeGreaterThanOrEqual(b);
  });

  it("rewards training and exploring, even on a missed step day", (ctx) => {
    const base = written(ctx, () => xpForDay(day({ steps: 1000 })));
    expect(xpForDay(day({ steps: 1000, trained: true }))).toBeGreaterThan(base);
    expect(xpForDay(day({ steps: 1000, explored: true }))).toBeGreaterThan(base);
    expect(xpForDay(day({ steps: null, trained: true }))).toBeGreaterThan(0);
  });
});

describe("H4 stageForXp", () => {
  it("starts asleep and never goes down", (ctx) => {
    expect(written(ctx, () => stageForXp(0))).toBe(0);
    let last = 0;
    for (let xp = 0; xp <= 3000; xp += 10) {
      const s = stageForXp(xp);
      expect(s).toBeGreaterThanOrEqual(last);
      expect([0, 1, 2, 3]).toContain(s);
      last = s;
    }
  });

  it("reaches roaring for someone who wins about every day for three weeks", (ctx) => {
    const perWin = written(ctx, () => xpForDay(day()));
    expect(stageForXp(perWin * 21)).toBe(3);
    expect(stageForXp(perWin * 2)).toBeLessThan(3);
  });
});

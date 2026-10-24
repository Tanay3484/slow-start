import { describe, expect, it } from "vitest";
import { newState } from "../state";
import type { DayRecord } from "../types";
import { addDays, emptyDay, historyFor, hpLeft, outcomeOf, settle, statsOf, todayISO, totalXp, xpOfDay } from "./day";

const rec = (over: Partial<DayRecord>): DayRecord => ({ ...emptyDay("2026-10-20"), goal: 4000, ...over });

describe("outcomeOf (R4.2, R4.5)", () => {
  it("is won the moment the goal is reached, even mid-day", () => {
    expect(outcomeOf(rec({ steps: 4000 }), "2026-10-20")).toBe("win");
    expect(outcomeOf(rec({ steps: 5200 }), "2026-10-20")).toBe("win");
  });
  it("is only a miss once the day is over", () => {
    expect(outcomeOf(rec({ steps: 1000 }), "2026-10-20")).toBe("open");
    expect(outcomeOf(rec({ steps: 1000 }), "2026-10-21")).toBe("miss");
  });
  it("treats an unlogged or excused day as rest, never a miss", () => {
    expect(outcomeOf(rec({ steps: null }), "2026-10-21")).toBe("rest");
    expect(outcomeOf(rec({ steps: 100, excused: true }), "2026-10-21")).toBe("rest");
  });
  it("treats imported history with no goal as rest", () => {
    expect(outcomeOf(rec({ goal: null, steps: 9000 }), "2026-10-21")).toBe("rest");
  });
});

describe("day helpers", () => {
  it("hpLeft never goes below zero", () => {
    expect(hpLeft(4000, 1500)).toBe(2500);
    expect(hpLeft(4000, 9000)).toBe(0);
    expect(hpLeft(4000, null)).toBe(4000);
  });
  it("adds days across month ends", () => {
    expect(addDays("2026-10-31", 1)).toBe("2026-11-01");
    expect(addDays("2026-03-01", -1)).toBe("2026-02-28");
  });
  it("formats the local date", () => {
    expect(todayISO(new Date(2026, 9, 5, 23, 59))).toBe("2026-10-05");
  });
  it("settle creates today and closes yesterday", () => {
    const s = { ...newState("live"), days: [rec({ steps: 1000 })] };
    const out = settle(s, "2026-10-21");
    expect(out.days.map((d) => [d.date, d.outcome])).toEqual([
      ["2026-10-20", "miss"],
      ["2026-10-21", "open"],
    ]);
  });
  it("historyFor excludes today and later (the backend must not see them)", () => {
    const s = { ...newState("live"), days: [rec({}), rec({ date: "2026-10-21" }), rec({ date: "2026-10-22" })] };
    expect(historyFor(s, "2026-10-21").map((d) => d.date)).toEqual(["2026-10-20"]);
  });
});

describe("XP and stats (work with the fallback rule or Tanay's)", () => {
  it("is a non-negative whole number, derived from the days", () => {
    const days = [
      rec({ steps: 4000 }),
      rec({ date: "2026-10-21", steps: 100 }),
      rec({ date: "2026-10-22", steps: null, trained: true }),
    ];
    for (const d of days) {
      const xp = xpOfDay(d);
      expect(Number.isInteger(xp)).toBe(true);
      expect(xp).toBeGreaterThanOrEqual(0);
    }
    expect(totalXp(days)).toBe(days.reduce((a, d) => a + xpOfDay(d), 0));
  });
  it("gives imported days with no goal no XP", () => {
    expect(xpOfDay(rec({ goal: null, steps: 20000 }))).toBe(0);
  });
  it("a win is worth at least a miss", () => {
    expect(xpOfDay(rec({ steps: 4000 }))).toBeGreaterThanOrEqual(xpOfDay(rec({ steps: 100 })));
  });
  it("starts Speed and Power at half and caps at full (R4.6)", () => {
    expect(statsOf([], [])).toMatchObject({ speed: 0.5, power: 0.5 });
    const wins = Array.from({ length: 40 }, (_, i) =>
      rec({ date: addDays("2026-09-01", i), steps: 5000, outcome: "win" }),
    );
    const work = Array.from({ length: 30 }, (_, i) => ({ date: addDays("2026-09-01", i), exercise: "squat", sets: [] }));
    expect(statsOf(wins, work)).toMatchObject({ speed: 1, power: 1 });
  });
});

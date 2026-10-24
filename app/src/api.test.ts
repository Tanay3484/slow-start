import { describe, expect, it } from "vitest";
import { offlineGoal } from "./api";

describe("offlineGoal (R7.4)", () => {
  it("starts a new person small", () => {
    expect(offlineGoal([], "2026-10-21")).toMatchObject({ goal: 1500, source: "offline", phase: "slow_start" });
  });
  it("uses 80% of the recent median, rounded to 50, and ignores today", () => {
    const days = Array.from({ length: 10 }, (_, i) => ({
      date: `2026-10-${String(10 + i).padStart(2, "0")}`,
      steps: 6000 as number | null,
    }));
    days.push({ date: "2026-10-21", steps: 99999 });
    expect(offlineGoal(days, "2026-10-21").goal).toBe(4800);
  });
  it("skips days that were not worn", () => {
    expect(offlineGoal([{ date: "2026-10-20", steps: null }], "2026-10-21").goal).toBe(1500);
  });
  it("stays between the floor and the ceiling", () => {
    expect(offlineGoal([{ date: "2026-10-20", steps: 500 }], "2026-10-21").goal).toBe(1000);
    expect(offlineGoal([{ date: "2026-10-20", steps: 90000 }], "2026-10-21").goal).toBe(20000);
  });
});

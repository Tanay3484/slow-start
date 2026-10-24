import { describe, expect, it } from "vitest";
import { nextStageAt, stageOf } from "./rules";

describe("stage helpers work with either XP rule", () => {
  it("never goes down and stays within 0..3", () => {
    let last = 0;
    for (let xp = 0; xp < 5000; xp += 7) {
      const s = stageOf(xp);
      expect(s).toBeGreaterThanOrEqual(last);
      expect(s).toBeLessThanOrEqual(3);
      last = s;
    }
  });
  it("finds the XP at which the next stage starts", () => {
    const at = nextStageAt(0);
    expect(at).not.toBeNull();
    expect(stageOf(at as number)).toBeGreaterThan(stageOf(0));
    expect(stageOf((at as number) - 1)).toBe(stageOf(0));
  });
  it("has no next stage at the top", () => {
    expect(nextStageAt(1_000_000)).toBeNull();
  });
});

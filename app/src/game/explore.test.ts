import { describe, expect, it } from "vitest";
import { cellId, haversineM, isNewCell } from "./explore";

describe("explore bonus (R6.3)", () => {
  it("gives nearby points the same cell and far points another", () => {
    expect(cellId(18.5204, 73.8567)).toBe(cellId(18.5206, 73.8569));
    expect(cellId(18.5204, 73.8567)).not.toBe(cellId(18.6204, 73.8567));
  });
  it("stores a coarse cell, not the exact position", () => {
    const id = cellId(18.52043217, 73.85674419);
    expect(id).not.toContain("18.52043");
    expect(id.split(",").every((p) => p.split(".")[1].length === 3)).toBe(true);
  });
  it("is new only the first time", () => {
    expect(isNewCell([], "1,2")).toBe(true);
    expect(isNewCell(["1,2"], "1,2")).toBe(false);
  });
  it("measures distance on the globe", () => {
    expect(haversineM(0, 0, 0, 0)).toBe(0);
    expect(haversineM(18.5204, 73.8567, 18.5304, 73.8567)).toBeGreaterThan(1100);
    expect(haversineM(18.5204, 73.8567, 18.5304, 73.8567)).toBeLessThan(1120);
  });
});

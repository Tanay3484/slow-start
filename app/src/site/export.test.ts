import { describe, expect, it } from "vitest";
import { ICONS } from "./export";

describe("export page icons", () => {
  it("are all 16 x 16", () => {
    for (const [name, rows] of Object.entries(ICONS)) {
      expect(rows, name).toHaveLength(16);
      for (const row of rows) expect(row.length, `${name}: ${row}`).toBe(16);
    }
  });
});

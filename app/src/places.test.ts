import { describe, expect, it } from "vitest";
import { buildQuery, cellCentre, findPlaces, parseElements, rankPlaces } from "./places";

describe("places (R6.1, R6.2)", () => {
  it("queries OpenStreetMap with the cell centre, never the exact position", () => {
    const q = buildQuery(18.52043217, 73.85674419, "walk", 1600);
    expect(q).not.toContain("18.52043217");
    expect(q).not.toContain("73.85674419");
    expect(q).toContain("18.52,73.86");
    expect(q).toContain("[maxsize:67108864]");
    expect(cellCentre(18.52043217, 73.85674419)).toEqual([18.52, 73.86]);
  });

  const good = { type: "way", id: 1, center: { lat: 18.521, lon: 73.857 }, tags: { name: "Sarasbaug", leisure: "park" } };

  it("keeps named, classifiable places and computes distance and walk time", () => {
    const [p] = parseElements([good], "walk", 18.5204, 73.8567);
    expect(p).toMatchObject({ name: "Sarasbaug", kind: "Park", habitat: "park" });
    expect(p.walkMin).toBeGreaterThanOrEqual(1);
  });

  it("treats the network answer as untrusted input", () => {
    const junk: unknown[] = [
      null,
      5,
      "x",
      { type: "way" },
      { ...good, id: "1" },
      { ...good, type: "evil" },
      { ...good, tags: null },
      { ...good, tags: { leisure: "park" } },
      { ...good, center: { lat: 999, lon: 0 } },
      { ...good, center: { lat: "1", lon: 2 } },
      { ...good, tags: { name: "Unrelated", shop: "bakery" } },
    ];
    expect(parseElements(junk, "walk", 18.52, 73.85)).toEqual([]);
    expect(parseElements("not an array", "walk", 0, 0)).toEqual([]);
  });

  it("keeps markup in a name as plain text (the UI shows names with textContent)", () => {
    const evil = { ...good, tags: { name: "<img src=x onerror=alert(1)>", leisure: "park" } };
    expect(parseElements([evil], "walk", 18.52, 73.85)[0].name).toBe("<img src=x onerror=alert(1)>");
  });

  it("deduplicates by name and kind, nearest first, two per kind at most", () => {
    const mk = (id: number, name: string, lat: number) => ({
      type: "node",
      id,
      lat,
      lon: 73.85,
      tags: { name, leisure: "park" },
    });
    const places = parseElements(
      [mk(1, "A Park", 18.521), mk(2, "A  Park", 18.521), mk(3, "B Park", 18.522), mk(4, "C Park", 18.523), mk(5, "D Park", 18.524)],
      "walk",
      18.52,
      73.85,
    );
    expect(places.length).toBe(4);
    const ranked = rankPlaces(places);
    expect(ranked.length).toBe(2);
    expect(ranked[0].distanceM).toBeLessThanOrEqual(ranked[1].distanceM);
  });

  it("falls through dead servers and then reports failure", async () => {
    let calls = 0;
    const dead = (async () => {
      calls++;
      throw new Error("down");
    }) as unknown as typeof fetch;
    await expect(findPlaces(18.52, 73.85, "walk", 20, dead)).rejects.toThrow();
    expect(calls).toBe(2);
    const ok = (async () => ({ ok: true, json: async () => ({ elements: [good] }) })) as unknown as typeof fetch;
    expect((await findPlaces(18.5204, 73.8567, "walk", 20, ok)).length).toBe(1);
  });
});

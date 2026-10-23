// Nearby places from OpenStreetMap, straight from the device (R6.1, R6.2).
//
// Ported from Golden Hour (same author, Week 1, MIT; src/golden_hour/places.py and ranking.py): the
// Overpass query with a small `maxsize` that busy servers accept, named places only, and a cap of two per
// category. Overpass only ever sees the centre of the ~1 km grid cell, never the exact position.
import { haversineM } from "./game/explore";
import type { Habitat, Place } from "./types";

export type Activity = "walk" | "train";

interface Rule {
  selector: string;
  kind: string;
  habitat: Habitat;
}

const RULES: Record<Activity, Rule[]> = {
  walk: [
    { selector: '["leisure"="park"]', kind: "Park", habitat: "park" },
    { selector: '["leisure"="garden"]', kind: "Garden", habitat: "park" },
    { selector: '["leisure"="nature_reserve"]', kind: "Nature reserve", habitat: "park" },
    { selector: '["natural"="beach"]', kind: "Beach", habitat: "water" },
    { selector: '["waterway"~"^(river|canal)$"]', kind: "Waterside", habitat: "water" },
    { selector: '["tourism"="viewpoint"]', kind: "Viewpoint", habitat: "park" },
  ],
  train: [
    { selector: '["leisure"="fitness_station"]', kind: "Outdoor gym", habitat: "gym" },
    { selector: '["leisure"="fitness_centre"]', kind: "Gym", habitat: "gym" },
    { selector: '["leisure"="sports_centre"]', kind: "Sports centre", habitat: "gym" },
  ],
};

export const ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"];
const CELL_DECIMALS = 2; // ~1.1 km grid
const CELL_SLACK_M = 800;
export const WALK_M_PER_MIN = 80;
const PER_RULE = 40;
const MAX_PER_KIND = 2;

export function cellCentre(lat: number, lon: number): [number, number] {
  const f = 10 ** CELL_DECIMALS;
  return [Math.round(lat * f) / f, Math.round(lon * f) / f];
}

export function buildQuery(lat: number, lon: number, activity: Activity, radiusM: number): string {
  const [clat, clon] = cellCentre(lat, lon);
  const parts = ["[out:json][timeout:25][maxsize:67108864];"];
  for (const rule of RULES[activity]) {
    parts.push(`nwr(around:${radiusM + CELL_SLACK_M},${clat},${clon})${rule.selector}["name"];out center tags ${PER_RULE};`);
  }
  return parts.join("\n");
}

function classify(tags: Record<string, string>, activity: Activity): Rule | null {
  for (const rule of RULES[activity]) {
    const m = [...rule.selector.matchAll(/\["(\w+)"(=|~)"([^"]+)"\]/g)];
    if (m.length && m.every(([, key, op, val]) => (op === "=" ? tags[key] === val : new RegExp(val).test(tags[key] ?? "")))) return rule;
  }
  return null;
}

const isCoord = (v: unknown, limit: number): v is number => typeof v === "number" && Number.isFinite(v) && Math.abs(v) <= limit;
const nameKey = (n: string) => n.toLowerCase().replace(/[^a-z0-9]/g, "");

/** Overpass answers are untrusted input: every field is checked before it is used. */
export function parseElements(elements: unknown, activity: Activity, lat: number, lon: number): Place[] {
  if (!Array.isArray(elements)) return [];
  const seen = new Map<string, Place>();
  for (const e of elements as Record<string, unknown>[]) {
    if (!e || typeof e !== "object" || typeof e.id !== "number" || !["node", "way", "relation"].includes(String(e.type))) continue;
    const tags = e.tags as Record<string, string> | undefined;
    if (!tags || typeof tags !== "object") continue;
    const name = String(tags["name:en"] ?? tags.name ?? "").trim().slice(0, 80);
    const point = (e.center && typeof e.center === "object" ? e.center : e) as Record<string, unknown>;
    if (!name || !isCoord(point.lat, 90) || !isCoord(point.lon, 180)) continue;
    const rule = classify(tags, activity);
    if (!rule) continue;
    const distanceM = Math.round(haversineM(lat, lon, point.lat, point.lon));
    const key = `${nameKey(name)}|${rule.kind}`;
    if (seen.has(key)) continue;
    seen.set(key, {
      id: `${e.type}/${e.id}`,
      name,
      kind: rule.kind,
      habitat: rule.habitat,
      lat: point.lat,
      lon: point.lon,
      distanceM,
      walkMin: Math.max(1, Math.ceil(distanceM / WALK_M_PER_MIN)),
    });
  }
  return [...seen.values()];
}

/** Nearest first, at most two of each kind, at most `k` in all (Golden Hour's ranking idea). */
export function rankPlaces(places: readonly Place[], k = 5): Place[] {
  const perKind = new Map<string, number>();
  const out: Place[] = [];
  for (const p of [...places].sort((a, b) => a.distanceM - b.distanceM || a.name.localeCompare(b.name))) {
    const n = perKind.get(p.kind) ?? 0;
    if (n >= MAX_PER_KIND) continue;
    perKind.set(p.kind, n + 1);
    out.push(p);
    if (out.length === k) break;
  }
  return out;
}

export async function findPlaces(lat: number, lon: number, activity: Activity, maxWalkMin = 20, fetchFn: typeof fetch = fetch): Promise<Place[]> {
  const radiusM = maxWalkMin * WALK_M_PER_MIN;
  const query = buildQuery(lat, lon, activity, radiusM);
  for (const url of ENDPOINTS) {
    try {
      const res = await fetchFn(url, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `data=${encodeURIComponent(query)}`,
      });
      if (!res.ok) continue;
      const data = (await res.json()) as { elements?: unknown };
      return rankPlaces(parseElements(data.elements, activity, lat, lon).filter((p) => p.distanceM <= radiusM));
    } catch {
      /* try the next server */
    }
  }
  throw new Error("The map service did not answer");
}

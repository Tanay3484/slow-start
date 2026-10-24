// Slumbrock and the wild creatures. All original; the art is drawn in scripts/draw_sprites.py.
import type { Habitat } from "../types";

export interface Creature {
  name: string;
  habitat: Habitat;
  sprite: string;
  blurb: string;
}

export const CREATURES: Record<string, Creature> = {
  mossling: { name: "Mossling", habitat: "park", sprite: "mossling", blurb: "Grows a new leaf for every quiet walk." },
  leafwing: { name: "Leafwing", habitat: "park", sprite: "leafwing", blurb: "Only lands where the path is wide." },
  pebbit: { name: "Pebbit", habitat: "street", sprite: "pebbit", blurb: "A pebble that learned to hop. Naps in doorways." },
  lampwick: { name: "Lampwick", habitat: "street", sprite: "lampwick", blurb: "Switches on at dusk and expects company." },
  ripplet: { name: "Ripplet", habitat: "water", sprite: "ripplet", blurb: "Follows anyone who walks beside water." },
  plateling: { name: "Kettlebub", habitat: "gym", sprite: "plateling", blurb: "Lifts its own little bar all day. Weighs more than it looks." },
  chalkpuff: { name: "Chalkpuff", habitat: "gym", sprite: "chalkpuff", blurb: "Appears in a cloud whenever hands get dusty." },
  wanderwisp: { name: "Wanderwisp", habitat: "rare", sprite: "wanderwisp", blurb: "Only shows up somewhere you have never been." },
  starpebble: { name: "Starpebble", habitat: "rare", sprite: "starpebble", blurb: "Fell from the sky into a place you found first." },
};

const POOLS: Record<Habitat, string[]> = {
  park: ["mossling", "leafwing", "pebbit"],
  street: ["pebbit", "lampwick", "mossling"],
  water: ["ripplet", "leafwing"],
  gym: ["plateling", "chalkpuff"],
  rare: ["wanderwisp", "starpebble"],
};

function hash(text: string): number {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** The same day and place always give the same creature. */
export function creatureFor(date: string, habitat: Habitat, salt = ""): string {
  const pool = POOLS[habitat];
  return pool[hash(date + salt) % pool.length];
}

export const ALL_IDS = Object.keys(CREATURES);

export const STAGE_NAMES = ["Asleep", "Drowsy", "Awake", "Roaring"] as const;

export const HABITAT_LABEL: Record<Habitat, string> = {
  park: "Park",
  street: "Street",
  water: "Waterfront",
  gym: "Gym",
  rare: "Somewhere new",
};

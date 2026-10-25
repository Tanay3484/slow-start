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

export interface GuideEntry {
  rarity: "Common" | "Uncommon" | "Rare";
  find: string;
  howToCatch: string;
  trivia: string[];
}

/** The field guide (guide.html). All original, all a little silly. */
export const GUIDE: Record<string, GuideEntry> = {
  mossling: {
    rarity: "Common",
    find: "Parks and gardens, and now and then a quiet street.",
    howToCatch: "Reach the day's step goal anywhere green.",
    trivia: [
      "A Mossling is about nine parts moss to one part optimism.",
      "It sleeps standing up, like a very small, very green horse.",
      "If a Mossling sneezes near you, it is pollen season. Sorry.",
    ],
  },
  leafwing: {
    rarity: "Common",
    find: "Parks, and paths beside water.",
    howToCatch: "Reach your goal on a day you walk somewhere with wide paths.",
    trivia: [
      "Its wings are two leaves it refused to give back to the tree.",
      "Leafwings migrate by following people who forgot their earphones.",
      "It can fly perfectly well. It just prefers being carried by the wind.",
    ],
  },
  pebbit: {
    rarity: "Common",
    find: "Streets, doorways and the edges of parks.",
    howToCatch: "Reach your goal on an ordinary day. Pebbits love ordinary days.",
    trivia: [
      "Pebbits count steps by tapping one foot. They lose count at three.",
      "Its favourite food is gravel. It has never once tried gravel.",
      "Stack two Pebbits and you get a very confused Pebbit.",
    ],
  },
  lampwick: {
    rarity: "Uncommon",
    find: "Streets after dusk, under the oldest lamp posts.",
    howToCatch: "Reach your goal on a street walk, ideally in the evening.",
    trivia: [
      "Its glow brightens when you walk past slowly. It is lonely, not lazy.",
      "Moths have been trying to start a fan club for centuries.",
      "A Lampwick never switches off. It just dims and pretends to be asleep.",
    ],
  },
  ripplet: {
    rarity: "Uncommon",
    find: "Riversides, beaches and anywhere a puddle has ambitions.",
    howToCatch: "Reach your goal on a day you walk beside water.",
    trivia: [
      "A Ripplet is technically one very determined raindrop.",
      "It cannot swim. It will not admit this.",
      "Two Ripplets that meet become one slightly larger, much happier Ripplet.",
    ],
  },
  plateling: {
    rarity: "Uncommon",
    find: "Gyms and outdoor gyms, mostly near the heavy end.",
    howToCatch: "Log a workout, or reach your goal on a day you train at a gym.",
    trivia: [
      "Kettlebub has never skipped leg day, because it has no legs.",
      "It weighs exactly as much as you think you can lift, plus a little.",
      "The little bar it lifts is its own handle. Nobody has told it.",
    ],
  },
  chalkpuff: {
    rarity: "Uncommon",
    find: "Gyms, anywhere hands get dusty.",
    howToCatch: "Train somewhere with chalk in the air.",
    trivia: [
      "Every Chalkpuff is made of the chalk someone forgot to wipe off the bar.",
      "Clapping your hands is how you say hello. It is also how you make a new one.",
      "It is mostly harmless. It is entirely sneezy.",
    ],
  },
  wanderwisp: {
    rarity: "Rare",
    find: "Only in a place you have never logged from before.",
    howToCatch: "Open Places, walk somewhere new, and tap I'm here when you arrive.",
    trivia: [
      "Nobody has seen a Wanderwisp twice in the same place. Nobody has really tried.",
      "It is said to be the ghost of a shortcut.",
      "Its eyes glow brighter the further you are from home.",
    ],
  },
  starpebble: {
    rarity: "Rare",
    find: "Only in a place you have never logged from before.",
    howToCatch: "Explore somewhere new. Starpebbles land where nobody has looked yet.",
    trivia: [
      "Each Starpebble is a piece of a star that decided walking looked fun.",
      "If you find one, make a wish. It will not come true, but you walked there, which is better.",
      "It twinkles at the tips when it is happy, which is always.",
    ],
  },
};

export const SLUMBROCK_STAGES = [
  { name: "Asleep", text: "Asleep for three hundred years. Snores in a low rumble you can feel in your shoes." },
  { name: "Drowsy", text: "One eye open. The rune in his chest warms like an ember." },
  { name: "Awake", text: "Both eyes glowing, and the moss on his shoulders starts to flower." },
  { name: "Roaring", text: "Arms up, rune white-hot. Slow start. Steady wins." },
] as const;

export const STAGE_NAMES = ["Asleep", "Drowsy", "Awake", "Roaring"] as const;

export const HABITAT_LABEL: Record<Habitat, string> = {
  park: "Park",
  street: "Street",
  water: "Waterfront",
  gym: "Gym",
  rare: "Somewhere new",
};

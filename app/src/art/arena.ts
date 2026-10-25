// The battle arena: a small game engine drawn in code at 240 x 135 and scaled up crisp by CSS.
//
// What it does, all from the view the controller passes in:
//   - a living scene per habitat and time of day (parallax hills, clouds, water, lamps, weather particles)
//   - Slumbrock and the day's wild creature, breathing, blinking and bobbing, reacting when tapped
//   - an entrance when a new creature appears, an attack with a damage number for every step logged,
//     a capture sequence at zero HP (the creature then follows Slumbrock as a companion), and an
//     evolution burst when Slumbrock reaches a new stage
import type { Habitat } from "../types";
import { drawSprite, spriteFps, spriteSize, type Face } from "./sprites";

export const W = 240;
export const H = 135;
const GROUND = 114;
const S = 2; // sprite scale inside the arena

export interface ArenaView {
  /** Which day (and which save) this is; a change means a new encounter, never damage. */
  day: string;
  stage: 0 | 1 | 2 | 3;
  creature: string; // sprite id
  creatureName: string;
  habitat: Habitat;
  hp: number; // 0..1
  hpSteps: number; // steps still to walk
  goal: number;
  hour: number;
  caught: boolean;
  companions: string[]; // sprite ids of creatures caught on earlier days, most recent first
  /** A scene with no wild creature (the landing page's story). */
  noFoe?: boolean;
}

type Ease = (t: number) => number;
const easeOut: Ease = (t) => 1 - (1 - t) ** 3;
const easeIn: Ease = (t) => t * t * t;
const easeInOut: Ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
const bounce: Ease = (t) => {
  const n = 7.5625;
  const d = 2.75;
  if (t < 1 / d) return n * t * t;
  if (t < 2 / d) return n * (t -= 1.5 / d) * t + 0.75;
  if (t < 2.5 / d) return n * (t -= 2.25 / d) * t + 0.9375;
  return n * (t -= 2.625 / d) * t + 0.984375;
};

interface Tween {
  obj: Record<string, number>;
  key: string;
  from: number;
  to: number;
  start: number;
  dur: number;
  ease: Ease;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  ay: number;
  life: number;
  max: number;
  size: number;
  color: string;
  kind: "px" | "text" | "glow" | "leaf";
  text?: string;
  big?: boolean;
  drag?: number;
}

class Actor {
  ox = 0;
  oy = 0;
  sx = 1;
  sy = 1;
  alpha = 1;
  visible = true;
  tint: string | undefined;
  face: Face = "idle";
  faceUntil = 0;
  nextBlink = 1500 + Math.random() * 3000;
  phase = Math.random() * 1000;
  hop = 0; // extra lift, animated by tweens
  constructor(
    public sprite: string,
    public x: number,
    public y: number,
    public scale = S,
    public flip = false,
  ) {}

  get size() {
    const s = spriteSize(this.sprite);
    return { w: s.w * this.scale, h: s.h * this.scale };
  }

  hits(px: number, py: number): boolean {
    const { w, h } = this.size;
    return this.visible && px >= this.x + this.ox && px <= this.x + this.ox + w && py >= this.y + this.oy && py <= this.y + this.oy + h;
  }

  draw(g: CanvasRenderingContext2D, now: number, calm: boolean): void {
    if (!this.visible || this.alpha <= 0) return;
    if (now > this.nextBlink) {
      this.faceUntil = Math.max(this.faceUntil, now + 140);
      if (this.face === "idle") this.face = "blink";
      this.nextBlink = now + 2200 + Math.random() * 3600;
    }
    if (now > this.faceUntil) this.face = "idle";
    const fps = spriteFps(this.sprite);
    const frame = Math.floor(((now + this.phase) / 1000) * fps);
    const t = (now + this.phase) / 520;
    const bob = calm ? 0 : Math.sin(t) * 1.2;
    const squash = calm ? 0 : Math.sin(t) * 0.025;
    // shadow on the ground, smaller while hopping
    const { w } = this.size;
    const lift = this.hop + Math.max(0, -bob);
    g.fillStyle = "rgba(10, 12, 28, 0.35)";
    const sw = Math.max(6, w * 0.62 - lift * 0.8);
    g.fillRect(Math.round(this.x + this.ox + (w - sw) / 2), GROUND + 3, Math.round(sw), 2);
    g.fillRect(Math.round(this.x + this.ox + (w - sw * 0.7) / 2), GROUND + 2, Math.round(sw * 0.7), 1);
    drawSprite(g, this.sprite, this.x + this.ox, this.y + this.oy + bob - this.hop, this.scale, {
      face: this.face,
      frame,
      alpha: this.alpha,
      tint: this.tint,
      flip: this.flip,
      sx: this.sx * (1 + squash),
      sy: this.sy * (1 - squash),
    });
  }
}

// ---------------------------------------------------------------- the scene

const SKIES: Record<string, string[]> = {
  morning: ["#41a6f6", "#8fd3f7", "#ffd6a5", "#ffb38a", "#ffe8c7"],
  day: ["#2c6bd6", "#41a6f6", "#73c7f7", "#a8e2fb", "#d6f4ff"],
  dusk: ["#2a1748", "#5d275d", "#b13e53", "#ef7d57", "#ffcd75"],
  night: ["#0b0e1f", "#141a33", "#1f2a4d", "#29366f", "#3b4a7a"],
  rare: ["#140b24", "#2a1048", "#5d275d", "#9d4fc9", "#c98bf2"],
};

function skyKey(hour: number, habitat: Habitat): string {
  if (habitat === "rare") return "rare";
  if (hour >= 5 && hour < 9) return "morning";
  if (hour >= 9 && hour < 17) return "day";
  if (hour >= 17 && hour < 20) return "dusk";
  return "night";
}

function seeded(seed: number): () => number {
  let s = seed >>> 0;
  return () => (s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296;
}

function disc(g: CanvasRenderingContext2D, cx: number, cy: number, r: number, color: string): void {
  g.fillStyle = color;
  for (let y = -r; y <= r; y++) {
    const half = Math.floor(Math.sqrt(r * r - y * y));
    g.fillRect(Math.round(cx - half), Math.round(cy + y), half * 2 + 1, 1);
  }
}

/** The parts of the scene that do not move, drawn once per habitat and time of day. */
function staticLayer(habitat: Habitat, sky: string): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = W;
  c.height = H;
  const g = c.getContext("2d")!;
  const bands = SKIES[sky];
  const bandH = Math.ceil(GROUND / bands.length);
  bands.forEach((col, i) => {
    g.fillStyle = col;
    g.fillRect(0, i * bandH, W, bandH + 1);
    if (i > 0) {
      // dithered seam between bands
      g.fillStyle = bands[i - 1];
      for (let x = 0; x < W; x += 2) g.fillRect(x + ((i % 2) as number), i * bandH, 1, 1);
    }
  });
  const r = seeded(11);
  if (sky === "night" || sky === "rare") {
    for (let i = 0; i < 40; i++) {
      g.fillStyle = r() > 0.8 ? "#ffcd75" : "#e2fbff";
      g.fillRect(Math.floor(r() * W), Math.floor(r() * 70), 1, 1);
    }
  }
  // far hills
  const far = sky === "night" ? "#1a2240" : sky === "dusk" ? "#4a2550" : sky === "rare" ? "#2a1048" : "#5a7fb4";
  const near = sky === "night" ? "#1f2f3a" : sky === "dusk" ? "#3e2a45" : sky === "rare" ? "#1f0f33" : habitat === "street" ? "#566c86" : "#3b8a5a";
  for (let x = 0; x < W; x++) {
    const h1 = 26 + Math.sin(x / 23) * 6 + Math.sin(x / 9 + 1) * 2;
    g.fillStyle = far;
    g.fillRect(x, GROUND - h1, 1, h1);
  }
  if (habitat === "street") {
    // a skyline, windows lit at night
    const rb = seeded(5);
    for (let x = 0; x < W; ) {
      const bw = 14 + Math.floor(rb() * 18);
      const bh = 20 + Math.floor(rb() * 34);
      g.fillStyle = sky === "night" ? "#141a33" : sky === "dusk" ? "#3a2340" : "#7d8fb0";
      g.fillRect(x, GROUND - bh, bw - 2, bh);
      g.fillStyle = sky === "night" || sky === "dusk" ? "#ffcd75" : "#c4d4dd";
      for (let wy = GROUND - bh + 4; wy < GROUND - 6; wy += 6)
        for (let wx = x + 3; wx < x + bw - 4; wx += 5) if (rb() > (sky === "night" ? 0.45 : 0.7)) g.fillRect(wx, wy, 2, 3);
      x += bw;
    }
  }
  for (let x = 0; x < W; x++) {
    const h2 = 12 + Math.sin(x / 31 + 2) * 5 + Math.sin(x / 13) * 2;
    if (habitat === "gym") break;
    g.fillStyle = near;
    g.fillRect(x, GROUND - h2, 1, h2);
    if (x % 3 === 0) {
      g.fillStyle = "rgba(255,255,255,0.12)";
      g.fillRect(x, GROUND - h2, 1, 1);
    }
  }
  if (habitat === "gym") {
    // inside: a wall, a window, racks
    g.fillStyle = "#4a2c25";
    g.fillRect(0, 0, W, GROUND);
    g.fillStyle = "#5b362c";
    for (let y = 6; y < GROUND; y += 12) g.fillRect(0, y, W, 1);
    for (let i = 0; i < 2; i++) {
      const wx = 30 + i * 120;
      g.fillStyle = bands[2];
      g.fillRect(wx, 14, 56, 40);
      g.fillStyle = bands[4];
      g.fillRect(wx, 40, 56, 14);
      g.fillStyle = "#2e1a14";
      g.fillRect(wx + 27, 14, 2, 40);
      g.fillRect(wx, 33, 56, 2);
      g.strokeStyle = "#2e1a14";
    }
    g.fillStyle = "#2e1a14";
    g.fillRect(0, GROUND - 26, W, 3);
    for (let x = 12; x < W; x += 26) {
      g.fillStyle = "#94b0c2";
      g.fillRect(x, GROUND - 30, 16, 2);
      g.fillStyle = "#3a4466";
      g.fillRect(x - 2, GROUND - 33, 4, 8);
      g.fillRect(x + 14, GROUND - 33, 4, 8);
    }
  }
  if (habitat === "water") {
    g.fillStyle = sky === "night" ? "#0b1f4a" : "#1f3a8a";
    g.fillRect(0, GROUND - 22, W, 22);
  }
  if (habitat === "park" || habitat === "rare") {
    const rt = seeded(habitat === "park" ? 3 : 9);
    for (const tx of [8, 60, 188, 224]) {
      const th = 16 + Math.floor(rt() * 10);
      g.fillStyle = "#3e1d12";
      g.fillRect(tx, GROUND - th, 3, th);
      const leaf = habitat === "rare" ? ["#2a1048", "#5d275d", "#9d4fc9"] : sky === "night" ? ["#0f2a1c", "#173d29", "#1f5f3a"] : ["#1f5f3a", "#2e9a4f", "#63c74d"];
      disc(g, tx + 1, GROUND - th - 8, 10, leaf[0]);
      disc(g, tx, GROUND - th - 9, 8, leaf[1]);
      disc(g, tx - 2, GROUND - th - 11, 4, leaf[2]);
    }
  }
  // ground
  const top = habitat === "street" ? "#8b9bb4" : habitat === "gym" ? "#3a2420" : habitat === "water" ? "#e4c78c" : habitat === "rare" ? "#3e2160" : "#38b764";
  const body = habitat === "street" ? "#566c86" : habitat === "gym" ? "#2a1814" : habitat === "water" ? "#c9a46a" : habitat === "rare" ? "#2a1048" : "#257a46";
  g.fillStyle = body;
  g.fillRect(0, GROUND, W, H - GROUND);
  g.fillStyle = top;
  g.fillRect(0, GROUND, W, 3);
  const rg = seeded(21);
  for (let i = 0; i < 70; i++) {
    const x = Math.floor(rg() * W);
    const y = GROUND + 4 + Math.floor(rg() * (H - GROUND - 5));
    g.fillStyle = rg() > 0.5 ? top : "rgba(0,0,0,0.18)";
    g.fillRect(x, y, rg() > 0.7 ? 2 : 1, 1);
  }
  if (habitat === "street") {
    g.fillStyle = "#3a4466";
    for (let x = 0; x < W; x += 20) g.fillRect(x, GROUND + 3, 1, H - GROUND);
  }
  if (habitat === "park") {
    const rf = seeded(8);
    for (let i = 0; i < 12; i++) {
      const x = Math.floor(rf() * W);
      g.fillStyle = ["#ffcd75", "#ff8fab", "#f4f4f4"][i % 3];
      g.fillRect(x, GROUND + 5 + Math.floor(rf() * 12), 1, 1);
    }
  }
  return c;
}

// ---------------------------------------------------------------- the engine

const AMBIENT: Record<Habitat, { color: string[]; kind: Particle["kind"]; rate: number }> = {
  park: { color: ["#63c74d", "#a7f070", "#ffcd75"], kind: "leaf", rate: 0.9 },
  street: { color: ["#c0cbdc", "#8b9bb4"], kind: "px", rate: 0.5 },
  water: { color: ["#8fe3ff", "#e2fbff"], kind: "px", rate: 1.2 },
  gym: { color: ["#eef2f8", "#c0cbdc"], kind: "px", rate: 0.8 },
  rare: { color: ["#f2d6ff", "#ffcd75", "#73eff7"], kind: "glow", rate: 1.6 },
};

export class Arena {
  /** A box holding the pixel canvas and, on top, a full-resolution canvas just for text. */
  readonly el: HTMLDivElement;
  private canvas: HTMLCanvasElement;
  private g: CanvasRenderingContext2D;
  private tcanvas: HTMLCanvasElement;
  private tg: CanvasRenderingContext2D;
  private k = 1; // text-canvas pixels per arena pixel
  private view: ArenaView | null = null;
  private raf = 0;
  private hero: Actor;
  private foe: Actor | null = null;
  private pals: Actor[] = [];
  private tweens: Tween[] = [];
  private timers: { at: number; fn: () => void }[] = [];
  private particles: Particle[] = [];
  private banner: { text: string; sub?: string; color: string; start: number; dur: number } | null = null;
  private shake = { mag: 0, until: 0 };
  private flash = { color: "#ffffff", start: 0, dur: 0 };
  private wipe = { start: -1, dur: 650 };
  private rays = { start: -1, dur: 0 };
  private ring = { start: -1, dur: 0, x: 0, y: 0 };
  private layerKey = "";
  private layer: HTMLCanvasElement | null = null;
  private calm = typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
  private busyUntil = 0;
  private fontReady = false;
  private capturing: string | null = null; // held back from the companions until the orb lands
  private awaitGoal = false; // the entrance banner waits until the day's goal is known
  private ambientAcc = 0;
  private last = 0;

  constructor() {
    this.el = document.createElement("div");
    this.el.className = "arena-box";
    this.el.setAttribute("role", "img");
    this.canvas = document.createElement("canvas");
    this.canvas.width = W;
    this.canvas.height = H;
    this.canvas.className = "arena";
    this.g = this.canvas.getContext("2d")!;
    // Text drawn into a 240 x 135 canvas and blown up is a blur, so words go on their own canvas at the
    // screen's real resolution. It keeps a 16:9 shape so it crops exactly like the pixel canvas.
    this.tcanvas = document.createElement("canvas");
    this.tcanvas.className = "arena-text";
    this.tcanvas.setAttribute("aria-hidden", "true");
    this.tg = this.tcanvas.getContext("2d")!;
    this.el.append(this.canvas, this.tcanvas);
    this.hero = new Actor("slumbrock_0", 8, 0);
    this.place(this.hero);
    this.el.addEventListener("pointerdown", (e) => this.onTap(e));
    if (document.fonts?.load) {
      void document.fonts.load('8px "Press Start 2P"').then(() => (this.fontReady = true)).catch(() => {});
    }
  }

  private place(a: Actor): void {
    const { h } = a.size;
    a.y = GROUND + 4 - h + a.scale * 2;
  }

  // ------------------------------------------------------------ the view

  update(v: ArenaView): void {
    const prev = this.view;
    this.view = v;
    this.el.setAttribute("aria-label", `Slumbrock, ${["asleep", "drowsy", "awake", "roaring"][v.stage]}, facing ${v.creatureName}`);
    const sameDay = prev !== null && prev.day === v.day && prev.creature === v.creature;
    if (sameDay && v.caught && !prev.caught && this.foe) this.capturing = v.creature;
    if (!sameDay) this.capturing = null;
    this.syncPals(v);
    if (!sameDay) {
      this.hero.sprite = `slumbrock_${v.stage}`;
      this.place(this.hero);
      this.foe = null;
      if (!v.caught && !v.noFoe) this.enter(v, prev !== null);
      return;
    }
    if (v.noFoe) {
      if (v.stage > prev.stage) this.evolve(v.stage);
      else if (v.stage !== prev.stage) this.hero.sprite = `slumbrock_${v.stage}`;
      return;
    }
    if (this.awaitGoal && v.goal > 0) {
      this.awaitGoal = false;
      this.announce(v);
    }
    // A goal arriving is not damage: only count steps once the goal is known on both sides.
    const dealt = prev.goal > 0 && v.goal > 0 ? prev.hpSteps - v.hpSteps : 0;
    const delay = Math.max(0, this.busyUntil - performance.now());
    if (dealt > 0 && this.foe) {
      this.later(delay, () => this.attack(dealt, v.goal, v.hp === 0));
    } else if (dealt < 0 && this.foe) {
      this.burst(this.foeCenter().x, this.foeCenter().y, ["#63c74d", "#a7f070"], 8, 0.6);
    }
    if (v.stage > prev.stage) {
      const wait = delay + (dealt > 0 ? (v.hp === 0 ? 2600 : 700) : 0);
      this.later(wait, () => this.evolve(v.stage));
    } else if (v.stage !== prev.stage) {
      this.hero.sprite = `slumbrock_${v.stage}`;
    }
  }

  private announce(v: ArenaView): void {
    this.say(`${v.creatureName.toUpperCase()} BLOCKS THE PATH`, `Walk ${v.goal.toLocaleString("en-US")} steps to catch it`, "#ffcd75", 2600);
  }

  private syncPals(v: ArenaView): void {
    const want = v.companions.filter((id) => id !== this.capturing).slice(0, 2);
    if (want.join() === this.pals.map((p) => p.sprite).join()) return;
    this.pals = want.map((id, i) => {
      const a = new Actor(id, 104 + i * 24, 0, 1, i === 1);
      this.place(a);
      return a;
    });
  }

  // ------------------------------------------------------------ the loop

  start(): void {
    if (this.raf) return;
    const loop = (t: number) => {
      this.frame(t);
      this.raf = requestAnimationFrame(loop);
    };
    this.raf = requestAnimationFrame(loop);
  }

  stop(): void {
    cancelAnimationFrame(this.raf);
    this.raf = 0;
  }

  private later(ms: number, fn: () => void): void {
    this.timers.push({ at: performance.now() + ms, fn });
  }

  private tween(obj: object, key: string, to: number, dur: number, ease: Ease = easeOut, delay = 0): void {
    const o = obj as Record<string, number>;
    this.later(delay, () => {
      this.tweens = this.tweens.filter((t) => !(t.obj === o && t.key === key));
      this.tweens.push({ obj: o, key, from: o[key], to, start: performance.now(), dur, ease });
    });
  }

  private frame(now: number): void {
    const dt = Math.min(50, now - (this.last || now));
    this.last = now;
    const due = this.timers.filter((t) => t.at <= now);
    this.timers = this.timers.filter((t) => t.at > now);
    due.forEach((t) => t.fn());
    this.tweens = this.tweens.filter((t) => {
      const k = Math.min(1, (now - t.start) / t.dur);
      t.obj[t.key] = t.from + (t.to - t.from) * t.ease(k);
      return k < 1;
    });
    this.draw(now, dt);
  }

  // ------------------------------------------------------------ events

  private centerOf(a: Actor) {
    const { w, h } = a.size;
    return { x: a.x + a.ox + w / 2, y: a.y + a.oy + h / 2 };
  }

  /** Where the wild creature is now; a sensible spot if it has already gone (delayed effects). */
  private foeCenter() {
    return this.foe ? this.centerOf(this.foe) : { x: W - 48, y: GROUND - 30 };
  }

  private enter(v: ArenaView, wipe: boolean): void {
    const id = v.creature;
    const foe = new Actor(id, W - spriteSize(id).w * S - 14, 0, S, true);
    this.place(foe);
    foe.oy = -110;
    this.foe = foe;
    const t0 = wipe && !this.calm ? 500 : 0;
    if (wipe && !this.calm) this.wipe.start = performance.now();
    this.tween(foe, "oy", 0, this.calm ? 1 : 700, bounce, t0);
    this.later(t0 + 420, () => {
      this.burst(this.centerOf(foe).x, GROUND + 2, ["#c0cbdc", "#eef2f8"], 10, 0.5, -0.4);
      this.kick(1.5, 160);
    });
    if (v.goal > 0) this.later(t0 + 200, () => this.announce(v));
    else this.awaitGoal = true;
    this.busyUntil = performance.now() + t0 + 900;
  }

  private attack(dealt: number, goal: number, finishing: boolean): void {
    if (!this.foe) return;
    const foe = this.foe;
    const share = goal > 0 ? dealt / goal : 0.2;
    const big = share >= 0.3;
    this.busyUntil = performance.now() + 700;
    // Slumbrock lunges, the creature flinches
    this.tween(this.hero, "ox", 24, 130, easeIn);
    this.tween(this.hero, "ox", 0, 340, easeOut, 140);
    this.tween(this.hero, "sx", 1.08, 120, easeOut);
    this.tween(this.hero, "sx", 1, 200, easeOut, 140);
    this.later(130, () => {
      foe.face = "hit";
      foe.faceUntil = performance.now() + 380;
      foe.tint = "#ffffff";
      this.later(90, () => (foe.tint = undefined));
      this.tween(foe, "ox", big ? 12 : 7, 90, easeOut);
      this.tween(foe, "ox", 0, 380, easeInOut, 100);
      this.tween(foe, "sy", 0.86, 80, easeOut);
      this.tween(foe, "sy", 1, 260, bounce, 90);
      const c = this.centerOf(foe);
      this.burst(c.x - 10, c.y, big ? ["#ffffff", "#ffcd75", "#ef7d57"] : ["#ffffff", "#ffcd75"], big ? 22 : 12, big ? 1.4 : 1);
      this.burst(this.hero.x + 60, GROUND + 2, ["#c0cbdc"], 6, 0.4, -0.3);
      this.kick(big ? 4 : 2, big ? 320 : 180);
      this.float(`-${dealt.toLocaleString("en-US")}`, c.x, c.y - 26, big ? "#ffcd75" : "#ffffff", big);
      if (big) this.float("STOMP!", c.x - 8, c.y - 42, "#ef7d57", true, 1100);
    });
    if (finishing) this.later(520, () => this.capture());
  }

  private capture(): void {
    if (!this.foe) return;
    const foe = this.foe;
    const c = this.centerOf(foe);
    this.capturing = foe.sprite;
    this.busyUntil = performance.now() + 2400;
    this.ring = { start: performance.now(), dur: 1300, x: c.x, y: c.y };
    foe.tint = "#f2d6ff";
    this.tween(foe, "sx", 0.15, 900, easeIn, 350);
    this.tween(foe, "sy", 0.15, 900, easeIn, 350);
    this.tween(foe, "alpha", 0, 300, easeIn, 1100);
    this.later(1250, () => {
      // an orb of light flies home to Slumbrock
      const orb: Particle = { x: c.x, y: c.y, vx: -3.1, vy: -2.2, ay: 0.09, life: 0, max: 46, size: 3, color: "#fff1a8", kind: "glow", drag: 1 };
      this.particles.push(orb);
      this.later(760, () => {
        this.burst(this.hero.x + 50, this.hero.y + 60, ["#ffcd75", "#fff1a8", "#73eff7", "#a7f070", "#ff8fab"], 34, 1.6);
        this.flashScreen("#fff1a8", 260);
        this.kick(2, 200);
        this.say("CAUGHT!", "It will follow Slumbrock from now on", "#a7f070", 2400);
        this.capturing = null;
        if (this.view) this.syncPals(this.view);
        for (const p of this.pals) {
          p.hop = 14;
          this.tween(p, "hop", 0, 600, bounce);
        }
        this.hero.face = "yawn";
        this.hero.faceUntil = performance.now() + 900;
        this.tween(this.hero, "hop", 8, 160, easeOut);
        this.tween(this.hero, "hop", 0, 380, bounce, 170);
      });
    });
    this.later(1500, () => {
      if (this.foe === foe) this.foe = null;
    });
  }

  private evolve(stage: number): void {
    this.busyUntil = performance.now() + 2200;
    this.rays = { start: performance.now(), dur: 2000 };
    this.tween(this.hero, "hop", 6, 500, easeInOut);
    this.later(700, () => {
      this.flashScreen("#ffffff", 450);
      this.hero.sprite = `slumbrock_${stage}`;
      this.place(this.hero);
      this.kick(5, 420);
      this.burst(this.hero.x + 50, this.hero.y + 50, ["#ffcd75", "#ffffff", "#73eff7"], 40, 2);
    });
    this.tween(this.hero, "hop", 0, 500, bounce, 900);
    const names = ["ASLEEP", "DROWSY", "AWAKE", "ROARING"];
    this.later(800, () => this.say(`SLUMBROCK IS ${names[stage]}!`, stage === 3 ? "Fully awake. Steady wins." : "Keep going and he keeps waking", "#73eff7", 2800));
  }

  private onTap(e: PointerEvent): void {
    const r = this.canvas.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * W;
    const y = ((e.clientY - r.top) / r.height) * H;
    const now = performance.now();
    if (this.hero.hits(x, y)) {
      const stage = this.view?.stage ?? 0;
      this.hero.face = stage === 0 ? "blink" : "yawn";
      this.hero.faceUntil = now + 800;
      this.tween(this.hero, "hop", stage === 0 ? 2 : 7, 140, easeOut);
      this.tween(this.hero, "hop", 0, 420, bounce, 150);
      this.float(stage === 0 ? "z z z" : stage === 3 ? "ROAR!" : "hm?", this.hero.x + 50, this.hero.y + 6, "#e2fbff", false, 900);
      if (stage >= 2) this.kick(1.5, 150);
      return;
    }
    if (this.foe?.hits(x, y)) {
      this.tween(this.foe, "hop", 12, 150, easeOut);
      this.tween(this.foe, "hop", 0, 450, bounce, 160);
      this.tween(this.foe, "sy", 1.12, 120, easeOut);
      this.tween(this.foe, "sy", 1, 300, bounce, 130);
      const c = this.foeCenter();
      this.float("!", c.x, c.y - 34, "#ffcd75", false, 600);
      return;
    }
    for (const p of this.pals) {
      if (p.hits(x, y)) {
        this.tween(p, "hop", 8, 120, easeOut);
        this.tween(p, "hop", 0, 360, bounce, 130);
        this.burst(p.x + 17, p.y + 6, ["#ff8fab", "#ffcd75"], 6, 0.5);
      }
    }
  }

  // ------------------------------------------------------------ effects

  private kick(mag: number, dur: number): void {
    if (this.calm) return;
    this.shake = { mag, until: performance.now() + dur };
  }

  private flashScreen(color: string, dur: number): void {
    if (this.calm) return;
    this.flash = { color, start: performance.now(), dur };
  }

  private say(text: string, sub: string | undefined, color: string, dur: number): void {
    this.banner = { text, sub, color, start: performance.now(), dur };
  }

  private float(text: string, x: number, y: number, color: string, big = false, ms = 950): void {
    this.particles.push({ x, y, vx: (Math.random() - 0.5) * 0.3, vy: -0.55, ay: 0.006, life: 0, max: ms / 16.7, size: 1, color, kind: "text", text, big });
  }

  private burst(x: number, y: number, colors: string[], n: number, power: number, lift = -1): void {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2;
      const sp = (0.6 + Math.random() * 1.6) * power;
      this.particles.push({
        x,
        y,
        vx: Math.cos(a) * sp,
        vy: Math.sin(a) * sp + lift * 0.6,
        ay: 0.06,
        life: 0,
        max: 26 + Math.random() * 24,
        size: Math.random() > 0.7 ? 2 : 1,
        color: colors[i % colors.length],
        kind: "px",
        drag: 0.96,
      });
    }
  }

  private ambient(dt: number, v: ArenaView): void {
    const a = AMBIENT[v.habitat];
    const night = skyKey(v.hour, v.habitat) === "night";
    this.ambientAcc += (dt / 1000) * a.rate * (this.calm ? 0.3 : 1);
    while (this.ambientAcc > 1) {
      this.ambientAcc -= 1;
      if (night && v.habitat !== "rare") {
        // fireflies
        this.particles.push({ x: Math.random() * W, y: 40 + Math.random() * 60, vx: (Math.random() - 0.5) * 0.2, vy: (Math.random() - 0.5) * 0.15, ay: 0, life: 0, max: 200, size: 1, color: "#fff1a8", kind: "glow" });
        continue;
      }
      if (a.kind === "leaf") {
        this.particles.push({ x: Math.random() * W, y: -4, vx: 0.15 + Math.random() * 0.3, vy: 0.25 + Math.random() * 0.2, ay: 0, life: 0, max: 520, size: 2, color: a.color[Math.floor(Math.random() * a.color.length)], kind: "leaf" });
      } else if (v.habitat === "water") {
        this.particles.push({ x: Math.random() * W, y: GROUND - 2 - Math.random() * 18, vx: 0, vy: -0.05, ay: 0, life: 0, max: 60, size: 1, color: a.color[Math.floor(Math.random() * 2)], kind: "px" });
      } else {
        this.particles.push({ x: Math.random() * W, y: 20 + Math.random() * 80, vx: (Math.random() - 0.5) * 0.12, vy: -0.03 - Math.random() * 0.05, ay: 0, life: 0, max: 260, size: 1, color: a.color[Math.floor(Math.random() * a.color.length)], kind: a.kind });
      }
    }
    if (v.stage === 0 && Math.random() < dt / 1400) {
      this.particles.push({ x: this.hero.x + 66, y: this.hero.y + 16, vx: 0.18, vy: -0.22, ay: 0, life: 0, max: 130, size: 1, color: "#e2fbff", kind: "text", text: "z" });
    }
    if (v.stage === 3 && Math.random() < dt / 300) {
      this.particles.push({ x: this.hero.x + 50 + (Math.random() - 0.5) * 30, y: this.hero.y + 64, vx: (Math.random() - 0.5) * 0.4, vy: -0.6 - Math.random() * 0.4, ay: 0, life: 0, max: 50, size: 1, color: Math.random() > 0.5 ? "#ffcd75" : "#fff1a8", kind: "px" });
    }
  }

  // ------------------------------------------------------------ drawing

  /** Keep the text canvas at the screen's resolution (cover-cropped like the pixel canvas). */
  private syncText(): void {
    const bw = this.el.clientWidth;
    const bh = this.el.clientHeight;
    if (!bw || !bh) return;
    const dpr = Math.min(3, window.devicePixelRatio || 1);
    const k = Math.max(bw / W, bh / H) * dpr;
    const w = Math.round(W * k);
    const h = Math.round(H * k);
    if (this.tcanvas.width !== w || this.tcanvas.height !== h) {
      this.tcanvas.width = w;
      this.tcanvas.height = h;
    }
    this.k = k;
  }

  /** Crisp text on the overlay. `size` is in arena pixels; the pixel font is sharpest at multiples of 8. */
  private text(s: string, x: number, y: number, color: string, size = 8, alpha = 1): void {
    const g = this.tg;
    const k = this.k;
    const px = Math.max(8, Math.round((size * k) / 8) * 8);
    g.save();
    g.globalAlpha = alpha;
    g.font = this.fontReady ? `${px}px "Press Start 2P"` : `bold ${px}px monospace`;
    g.textAlign = "center";
    g.textBaseline = "top";
    g.lineJoin = "round";
    g.lineWidth = Math.max(2, Math.round(px / 4));
    g.strokeStyle = "#141626";
    const tx = Math.round(x * k);
    const ty = Math.round(y * k);
    g.strokeText(s, tx, ty);
    g.fillStyle = color;
    g.fillText(s, tx, ty);
    g.restore();
  }

  private glow(x: number, y: number, r: number, color: string, alpha: number): void {
    const g = this.g;
    g.save();
    g.globalCompositeOperation = "lighter";
    for (let i = 3; i >= 1; i--) {
      g.globalAlpha = alpha * (0.22 / i);
      disc(g, x, y, Math.round((r * i) / 3), color);
    }
    g.restore();
  }

  private draw(now: number, dt: number): void {
    const v = this.view;
    if (!v) return;
    const g = this.g;
    const sky = skyKey(v.hour, v.habitat);
    const key = `${v.habitat}|${sky}`;
    if (key !== this.layerKey || !this.layer) {
      this.layer = staticLayer(v.habitat, sky);
      this.layerKey = key;
    }
    this.syncText();
    const tg = this.tg;
    tg.setTransform(1, 0, 0, 1, 0, 0);
    tg.clearRect(0, 0, this.tcanvas.width, this.tcanvas.height);
    g.save();
    tg.save();
    if (now < this.shake.until) {
      const sx = Math.round((Math.random() - 0.5) * this.shake.mag * 2);
      const sy = Math.round((Math.random() - 0.5) * this.shake.mag * 2);
      g.translate(sx, sy);
      tg.translate(sx * this.k, sy * this.k);
    }
    g.drawImage(this.layer, 0, 0);

    // sun or moon, clouds, water, aurora
    if (v.habitat !== "gym") {
      if (sky === "night" || sky === "rare") {
        disc(g, 196, 22, 7, "#e2fbff");
        disc(g, 199, 20, 6, SKIES[sky][1]);
      } else {
        const sy = sky === "dusk" ? 60 : sky === "morning" ? 44 : 20;
        this.glow(200, sy, 18, "#fff1a8", 0.9);
        disc(g, 200, sy, 7, sky === "dusk" ? "#ef7d57" : "#fff1a8");
      }
      if (sky !== "night") {
        g.fillStyle = sky === "dusk" ? "#ffcd75" : "#f4f4f4";
        const drift = now / 260;
        for (const [cx, cy, w] of [[30, 16, 22], [120, 28, 30], [190, 12, 18]] as const) {
          const x = ((cx + drift * (w / 26)) % (W + 60)) - 30;
          g.fillRect(Math.round(x), cy, w, 3);
          g.fillRect(Math.round(x + 4), cy - 2, Math.round(w * 0.6), 2);
          g.fillRect(Math.round(x + 2), cy + 3, w - 4, 1);
        }
      }
      if (sky === "rare" || (sky === "night" && v.habitat === "park")) {
        g.save();
        g.globalCompositeOperation = "lighter";
        for (let x = 0; x < W; x += 2) {
          const y = 30 + Math.sin(x / 18 + now / 1400) * 8 + Math.sin(x / 7 + now / 900) * 2;
          g.fillStyle = x % 6 === 0 ? "rgba(115,239,247,0.35)" : "rgba(201,139,242,0.28)";
          g.fillRect(x, Math.round(y), 2, 10);
        }
        g.restore();
      }
    }
    if (v.habitat === "water") {
      for (let x = 0; x < W; x += 3) {
        const y = GROUND - 20 + Math.round(Math.sin(x / 11 + now / 500) * 1.5);
        g.fillStyle = "#41a6f6";
        g.fillRect(x, y, 2, 1);
        if ((x + Math.floor(now / 120)) % 17 === 0) {
          g.fillStyle = "#e2fbff";
          g.fillRect(x, y + 6, 2, 1);
        }
      }
    }
    if (v.habitat === "street") {
      // the lamp post: its light pools on the ground at dusk and night
      g.fillStyle = "#262b44";
      g.fillRect(226, GROUND - 46, 2, 46);
      g.fillRect(220, GROUND - 47, 10, 2);
      g.fillStyle = sky === "night" || sky === "dusk" ? "#fff1a8" : "#c0cbdc";
      g.fillRect(220, GROUND - 45, 4, 3);
      if (sky === "night" || sky === "dusk") this.glow(222, GROUND - 42, 22, "#ffcd75", 1);
    }

    // characters
    for (const p of this.pals) p.draw(g, now, this.calm);
    this.hero.draw(g, now, this.calm);
    if (this.foe) this.foe.draw(g, now, this.calm);

    // Slumbrock's rune and eyes glow brighter as he wakes
    const stage = v.stage;
    const hx = this.hero.x + this.hero.ox;
    const hy = this.hero.y + this.hero.oy - this.hero.hop;
    const pulse = 0.65 + Math.sin(now / 420) * 0.35;
    if (stage >= 1) this.glow(hx + 49, hy + 63, 8 + stage * 3, stage === 1 ? "#ef7d57" : "#ffcd75", (0.5 + stage * 0.25) * pulse);
    if (stage >= 1) {
      const ey = hy + 2 * (14 + [5, 2, 0, -1][stage]);
      this.glow(hx + 39, ey, 5, "#73eff7", 0.6 * pulse);
      this.glow(hx + 59, ey, 5, "#73eff7", 0.6 * pulse);
    }
    if (this.foe && (this.foe.sprite === "lampwick" || this.foe.sprite === "wanderwisp" || this.foe.sprite === "starpebble")) {
      const c = this.foeCenter();
      const col = this.foe.sprite === "wanderwisp" ? "#c98bf2" : "#ffcd75";
      this.glow(c.x, c.y - (this.foe.sprite === "lampwick" ? 12 : 0), 20, col, 0.8 * pulse);
    }

    // capture ring
    if (this.ring.start >= 0) {
      const k = (now - this.ring.start) / this.ring.dur;
      if (k > 1) this.ring.start = -1;
      else {
        const r = 30 * (1 - k * 0.6);
        for (let i = 0; i < 16; i++) {
          const a = i * (Math.PI / 8) + now / 180;
          g.fillStyle = i % 2 ? "#ffcd75" : "#f2d6ff";
          g.fillRect(Math.round(this.ring.x + Math.cos(a) * r), Math.round(this.ring.y + Math.sin(a) * r * 0.55), 2, 2);
        }
        this.glow(this.ring.x, this.ring.y, 16, "#f2d6ff", 1 - k);
      }
    }
    // evolution rays
    if (this.rays.start >= 0) {
      const k = (now - this.rays.start) / this.rays.dur;
      if (k > 1) this.rays.start = -1;
      else {
        g.save();
        g.globalCompositeOperation = "lighter";
        g.globalAlpha = Math.sin(k * Math.PI) * 0.5;
        g.fillStyle = "#fff1a8";
        const cx = hx + 50;
        const cy = hy + 50;
        for (let i = 0; i < 12; i++) {
          const a = i * (Math.PI / 6) + now / 900;
          g.beginPath();
          g.moveTo(cx, cy);
          g.lineTo(cx + Math.cos(a) * 200, cy + Math.sin(a) * 200);
          g.lineTo(cx + Math.cos(a + 0.12) * 200, cy + Math.sin(a + 0.12) * 200);
          g.closePath();
          g.fill();
        }
        g.restore();
      }
    }

    // particles
    this.ambient(dt, v);
    const steps = dt / 16.7;
    this.particles = this.particles.filter((p) => {
      p.life += steps;
      p.vy += p.ay * steps;
      if (p.drag) {
        p.vx *= p.drag ** steps;
        p.vy *= p.drag ** steps;
      }
      p.x += p.vx * steps;
      p.y += p.vy * steps;
      if (p.kind === "leaf") p.x += Math.sin((p.life + p.y) / 14) * 0.25;
      const fade = Math.min(1, (p.max - p.life) / 18);
      if (p.kind === "text") {
        this.text(p.text ?? "", p.x, p.y, p.color, p.big ? 10 : 8, Math.max(0, fade));
      } else if (p.kind === "glow") {
        this.glow(p.x, p.y, p.size === 3 ? 9 : 4, p.color, Math.max(0, fade) * (0.6 + Math.sin(p.life / 6) * 0.4));
        g.fillStyle = p.color;
        g.fillRect(Math.round(p.x), Math.round(p.y), p.size === 3 ? 2 : 1, p.size === 3 ? 2 : 1);
      } else {
        g.globalAlpha = Math.max(0, fade);
        g.fillStyle = p.color;
        const s = p.kind === "leaf" ? (Math.floor(p.life / 10) % 2 ? 2 : 1) : p.size;
        g.fillRect(Math.round(p.x), Math.round(p.y), s, p.kind === "leaf" ? 1 : s);
        g.globalAlpha = 1;
      }
      return p.life < p.max && p.y < H + 10 && p.x > -20 && p.x < W + 20;
    });

    // night darkens everything a little, except what glows
    if (sky === "night") {
      g.fillStyle = "rgba(10, 14, 40, 0.18)";
      g.fillRect(0, 0, W, H);
    }

    // banner
    if (this.banner) {
      const b = this.banner;
      const k = (now - b.start) / b.dur;
      if (k > 1) this.banner = null;
      else {
        const slide = k < 0.12 ? easeOut(k / 0.12) : k > 0.88 ? 1 - easeIn((k - 0.88) / 0.12) : 1;
        const y = Math.round(-30 + slide * 36);
        g.fillStyle = "rgba(20, 22, 38, 0.82)";
        g.fillRect(0, y, W, b.sub ? 28 : 18);
        g.fillStyle = b.color;
        g.fillRect(0, y + (b.sub ? 27 : 17), W, 1);
        this.text(b.text, W / 2, y + 5, b.color, 8);
        if (b.sub) this.text(b.sub, W / 2, y + 17, "#c0cbdc", 6);
      }
    }
    g.restore();
    tg.restore();

    // screen flash and the battle wipe
    if (this.flash.dur && now - this.flash.start < this.flash.dur) {
      g.globalAlpha = 1 - (now - this.flash.start) / this.flash.dur;
      g.fillStyle = this.flash.color;
      g.fillRect(0, 0, W, H);
      g.globalAlpha = 1;
    }
    if (this.wipe.start >= 0) {
      const k = (now - this.wipe.start) / this.wipe.dur;
      if (k > 1) this.wipe.start = -1;
      else {
        const cover = k < 0.5 ? easeIn(k * 2) : 1 - easeOut((k - 0.5) * 2);
        g.fillStyle = "#141626";
        for (let row = 0; row < H; row += 9) {
          const w = cover * (W + 40) - ((row / 9) % 2) * 20;
          if (w <= 0) continue;
          if ((row / 9) % 2) g.fillRect(W - w, row, w, 9);
          else g.fillRect(0, row, w, 9);
        }
      }
    }
  }
}

// The battle arena: a small canvas, drawn in code at 144 x 80 and scaled up crisp by CSS.
// Slumbrock on the left, the day's wild creature on the right. HUD text lives in the DOM above it.
import type { Habitat } from "../types";
import { drawSprite, spriteSize } from "./sprites";

export const W = 144;
export const H = 80;
const GROUND = 62;

export interface ArenaView {
  stage: 0 | 1 | 2 | 3;
  creature: string; // sprite name
  habitat: Habitat;
  /** 0 to 1: how much of the creature's HP is left. */
  hp: number;
  hour: number;
}

const SKY: Record<string, string[]> = {
  morning: ["#73eff7", "#a7f0ba", "#f4f4f4"],
  day: ["#41a6f6", "#73eff7", "#c4d4dd"],
  dusk: ["#5d275d", "#b13e53", "#ef7d57"],
  night: ["#1a1c2c", "#333c57", "#3b5dc9"],
  rare: ["#1a1c2c", "#5d275d", "#9d6bd3"],
};

const GROUND_COLOR: Record<Habitat, [string, string]> = {
  park: ["#38b764", "#257179"],
  street: ["#566c86", "#333c57"],
  water: ["#3b5dc9", "#29366f"],
  gym: ["#b86f50", "#733e39"],
  rare: ["#5d275d", "#3e2137"],
};

function skyKey(hour: number, habitat: Habitat): string {
  if (habitat === "rare") return "rare";
  if (hour >= 5 && hour < 9) return "morning";
  if (hour >= 9 && hour < 17) return "day";
  if (hour >= 17 && hour < 20) return "dusk";
  return "night";
}

function rnd(seed: number): () => number {
  let s = seed >>> 0;
  return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296);
}

function drawBackground(g: CanvasRenderingContext2D, v: ArenaView, t: number): void {
  const key = skyKey(v.hour, v.habitat);
  const [top, mid, low] = SKY[key];
  g.fillStyle = top;
  g.fillRect(0, 0, W, 22);
  g.fillStyle = mid;
  g.fillRect(0, 22, W, 20);
  g.fillStyle = low;
  g.fillRect(0, 42, W, GROUND - 42);
  const r = rnd(7);
  if (key === "night" || key === "rare") {
    g.fillStyle = "#f4f4f4";
    for (let i = 0; i < 18; i++) g.fillRect(Math.floor(r() * W), Math.floor(r() * 40), 1, 1);
  } else {
    g.fillStyle = "#f4f4f4";
    const drift = (t / 900) % (W + 40);
    for (const [cx, cy] of [[20, 10], [90, 20]] as const) {
      const x = ((cx + drift) % (W + 40)) - 20;
      g.fillRect(x, cy, 16, 3);
      g.fillRect(x + 4, cy - 2, 9, 2);
    }
  }
  // habitat scenery behind the characters
  if (v.habitat === "park") {
    g.fillStyle = "#257179";
    for (const x of [6, 52, 118]) {
      g.fillRect(x + 3, GROUND - 14, 3, 14);
      g.fillStyle = "#38b764";
      g.fillRect(x - 2, GROUND - 28, 14, 16);
      g.fillStyle = "#257179";
    }
  } else if (v.habitat === "street") {
    g.fillStyle = "#333c57";
    g.fillRect(120, GROUND - 30, 3, 30);
    g.fillStyle = key === "day" || key === "morning" ? "#ffcd75" : "#fff1a8";
    g.fillRect(116, GROUND - 34, 11, 5);
  } else if (v.habitat === "water") {
    g.fillStyle = "#3b5dc9";
    g.fillRect(0, GROUND - 10, W, 10);
    g.fillStyle = "#73eff7";
    for (let x = 0; x < W; x += 12) g.fillRect(x + ((t / 400) % 6 | 0), GROUND - 6, 5, 1);
  } else if (v.habitat === "gym") {
    g.fillStyle = "#733e39";
    g.fillRect(0, GROUND - 22, W, 22);
    g.fillStyle = "#94b0c2";
    for (const x of [14, 70, 112]) g.fillRect(x, GROUND - 16, 18, 2);
  }
  const [a, b] = GROUND_COLOR[v.habitat];
  g.fillStyle = a;
  g.fillRect(0, GROUND, W, H - GROUND);
  g.fillStyle = b;
  for (let x = 0; x < W; x += 4) g.fillRect(x + ((x / 4) % 2) * 2, GROUND + 4 + ((x / 4) % 3) * 4, 2, 1);
  g.fillRect(0, GROUND, W, 1);
}

export class Arena {
  readonly el: HTMLCanvasElement;
  private g: CanvasRenderingContext2D;
  private view: ArenaView | null = null;
  private raf = 0;
  private flashUntil = 0;
  private winAt = 0;
  private stageUpAt = 0;

  constructor() {
    this.el = document.createElement("canvas");
    this.el.width = W;
    this.el.height = H;
    this.el.className = "arena";
    this.el.setAttribute("role", "img");
    this.g = this.el.getContext("2d")!;
  }

  update(view: ArenaView): void {
    const prev = this.view;
    if (prev && view.hp < prev.hp - 0.001) this.flashUntil = performance.now() + 220;
    if (prev && view.hp === 0 && prev.hp > 0) this.winAt = performance.now();
    if (prev && view.stage > prev.stage) this.stageUpAt = performance.now();
    this.view = view;
    this.el.setAttribute("aria-label", `Slumbrock facing a wild ${view.creature}`);
  }

  start(): void {
    if (this.raf) return;
    const loop = (t: number) => {
      this.draw(t);
      this.raf = requestAnimationFrame(loop);
    };
    this.raf = requestAnimationFrame(loop);
  }

  stop(): void {
    cancelAnimationFrame(this.raf);
    this.raf = 0;
  }

  private draw(t: number): void {
    const v = this.view;
    if (!v) return;
    const g = this.g;
    drawBackground(g, v, t);

    const bob = Math.round(Math.sin(t / 420) * 1);
    const slumber = `slumbrock_${v.stage}`;
    const ss = spriteSize(slumber);
    const sx = 10;
    const sy = GROUND + 6 - ss.h * 2 + (v.stage === 0 ? 0 : bob);
    drawSprite(g, slumber, sx, sy, 2);
    if (v.stage === 0) {
      g.fillStyle = "#f4f4f4";
      g.font = "bold 7px monospace";
      const phase = (t / 700) % 3;
      for (let i = 0; i < 3; i++) {
        const p = (phase + i) % 3;
        g.globalAlpha = 1 - p / 3;
        g.fillText("z", sx + 48 + p * 4, sy + 4 - p * 6);
      }
      g.globalAlpha = 1;
    }
    if (performance.now() - this.stageUpAt < 900) {
      g.fillStyle = "#ffcd75";
      for (let i = 0; i < 10; i++) {
        const a = (t / 120 + i * 0.63) % (Math.PI * 2);
        g.fillRect(sx + 34 + Math.cos(a) * 36, sy + 34 + Math.sin(a) * 30, 2, 2);
      }
    }

    const cs = spriteSize(v.creature);
    const cx = W - cs.w * 2 - 12;
    const cy = GROUND + 4 - cs.h * 2 + bob * (v.stage === 0 ? 1 : -1);
    const sinceWin = performance.now() - this.winAt;
    if (this.winAt && sinceWin < 900) {
      const a = Math.max(0, 1 - sinceWin / 700);
      drawSprite(g, v.creature, cx, cy - sinceWin / 40, 2, { alpha: a, tint: a < 0.6 ? "#f4f4f4" : undefined });
    } else if (v.hp > 0) {
      const flashing = performance.now() < this.flashUntil;
      const shake = flashing ? ((t / 40) % 2 < 1 ? -1 : 1) : 0;
      drawSprite(g, v.creature, cx + shake, cy, 2, { flip: true, tint: flashing ? "#f4f4f4" : undefined });
    }
  }
}

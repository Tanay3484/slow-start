// Draws the palette-grid sprites from sprites.json (written by scripts/draw_sprites.py).
// Every frame is pre-rendered once at 1 pixel per cell, so drawing it scaled is one crisp drawImage.
import data from "./sprites.json";

export type Face = "idle" | "blink" | "hit" | "yawn";

interface SpriteData {
  idle: string[][];
  blink: string[];
  hit: string[];
  yawn?: string[];
  fps: number;
}

const { palette, sprites } = data as unknown as { palette: Record<string, string>; sprites: Record<string, SpriteData> };

const cache = new Map<string, HTMLCanvasElement>();

function rowsOf(name: string, face: Face, frame: number): string[] {
  const s = sprites[name];
  if (!s) throw new Error(`Unknown sprite ${name}`);
  if (face === "blink") return s.blink;
  if (face === "hit") return s.hit;
  if (face === "yawn") return s.yawn ?? s.idle[0];
  return s.idle[((frame % s.idle.length) + s.idle.length) % s.idle.length];
}

export function bitmap(name: string, face: Face = "idle", frame = 0, tint?: string): HTMLCanvasElement {
  const key = `${name}|${face}|${face === "idle" ? frame % sprites[name].idle.length : 0}|${tint ?? ""}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const rows = rowsOf(name, face, frame);
  const c = document.createElement("canvas");
  c.width = rows[0].length;
  c.height = rows.length;
  const g = c.getContext("2d")!;
  rows.forEach((row, y) => {
    for (let x = 0; x < row.length; x++) {
      const ch = row[x];
      if (ch === ".") continue;
      g.fillStyle = tint ?? palette[ch];
      g.fillRect(x, y, 1, 1);
    }
  });
  cache.set(key, c);
  return c;
}

export function spriteSize(name: string): { w: number; h: number } {
  const rows = sprites[name].idle[0];
  return { w: rows[0].length, h: rows.length };
}

export function spriteFps(name: string): number {
  return sprites[name].fps;
}

export interface DrawOpts {
  face?: Face;
  frame?: number;
  alpha?: number;
  tint?: string;
  flip?: boolean;
  /** Squash and stretch, around the sprite's feet. */
  sx?: number;
  sy?: number;
}

export function drawSprite(ctx: CanvasRenderingContext2D, name: string, x: number, y: number, scale: number, o: DrawOpts = {}): void {
  const bmp = bitmap(name, o.face ?? "idle", o.frame ?? 0, o.tint);
  const w = Math.round(bmp.width * scale * (o.sx ?? 1));
  const h = Math.round(bmp.height * scale * (o.sy ?? 1));
  const baseW = bmp.width * scale;
  const baseH = bmp.height * scale;
  const dx = Math.round(x + (baseW - w) / 2);
  const dy = Math.round(y + (baseH - h));
  ctx.save();
  ctx.imageSmoothingEnabled = false;
  ctx.globalAlpha = o.alpha ?? 1;
  if (o.flip) {
    ctx.translate(dx + w, dy);
    ctx.scale(-1, 1);
    ctx.drawImage(bmp, 0, 0, w, h);
  } else {
    ctx.drawImage(bmp, dx, dy, w, h);
  }
  ctx.restore();
}

/** A sprite as a data URL, for <img> tags. */
export function spriteUrl(name: string, tint?: string): string {
  return bitmap(name, "idle", 0, tint).toDataURL();
}

export const SPRITE_NAMES = Object.keys(sprites);

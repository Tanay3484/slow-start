// Draws the palette-grid sprites from sprites.json (written by scripts/draw_sprites.py).
import data from "./sprites.json";

type SpriteData = { palette: Record<string, string>; sprites: Record<string, string[]> };
const { palette, sprites } = data as SpriteData;

const cache = new Map<string, HTMLCanvasElement>();

/** A sprite pre-rendered at 1 pixel per cell, so drawing it scaled is one crisp drawImage. */
function bitmap(name: string, tint?: string): HTMLCanvasElement {
  const key = `${name}|${tint ?? ""}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const rows = sprites[name];
  if (!rows) throw new Error(`Unknown sprite ${name}`);
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
  const rows = sprites[name];
  return { w: rows[0].length, h: rows.length };
}

export function drawSprite(
  ctx: CanvasRenderingContext2D,
  name: string,
  x: number,
  y: number,
  scale: number,
  opts: { alpha?: number; tint?: string; flip?: boolean } = {},
): void {
  const bmp = bitmap(name, opts.tint);
  ctx.save();
  ctx.imageSmoothingEnabled = false;
  ctx.globalAlpha = opts.alpha ?? 1;
  if (opts.flip) {
    ctx.translate(Math.round(x) + bmp.width * scale, Math.round(y));
    ctx.scale(-1, 1);
    ctx.drawImage(bmp, 0, 0, bmp.width * scale, bmp.height * scale);
  } else {
    ctx.drawImage(bmp, Math.round(x), Math.round(y), bmp.width * scale, bmp.height * scale);
  }
  ctx.restore();
}

/** A sprite as a data URL, for <img> tags in the collection and elsewhere. */
export function spriteUrl(name: string, tint?: string): string {
  return bitmap(name, tint).toDataURL();
}

export const SPRITE_NAMES = Object.keys(sprites);

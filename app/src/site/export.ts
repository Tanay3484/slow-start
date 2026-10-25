// The export guide: original 16 x 16 pixel icons for each kind of source (not the apps' logos).
import "@fontsource/press-start-2p/index.css";
import "./site.css";

const PALETTE: Record<string, string> = {
  k: "#0b0c18", // outline
  g: "#4a5578", // body
  d: "#232842", // screen
  s: "#73eff7", // watch face ring
  r: "#ef7d57", // heart
  n: "#a7f070", // activity bar, header row
  y: "#ffcd75", // plates
  w: "#f4f4f4", // cells, button
};

export const ICONS: Record<string, string[]> = {
  phone: [
    "...kkkkkkkkkk...",
    "...kggggggggk...",
    "...kgddddddgk...",
    "...kgddddddgk...",
    "...kgrrddrrgk...",
    "...kgrrrrrrgk...",
    "...kgrrrrrrgk...",
    "...kgdrrrrdgk...",
    "...kgddrrddgk...",
    "...kgddddddgk...",
    "...kgnnnnnngk...",
    "...kgddddddgk...",
    "...kggggggggk...",
    "...kgggwwgggk...",
    "...kggggggggk...",
    "...kkkkkkkkkk...",
  ],
  watch: [
    ".....kkkkkk.....",
    ".....kggggk.....",
    ".....kggggk.....",
    "....kkkkkkkk....",
    "...kkddddddkk...",
    "..kkddssssddkk..",
    "..kddsddddsddk..",
    "..kdsddnnddsdk..",
    "..kdsddnnddsdk..",
    "..kddsddddsddk..",
    "..kkddssssddkk..",
    "...kkddddddkk...",
    "....kkkkkkkk....",
    ".....kggggk.....",
    ".....kggggk.....",
    ".....kkkkkk.....",
  ],
  dumbbell: [
    "................",
    "................",
    "................",
    "................",
    ".kkk........kkk.",
    "kyyyk......kyyyk",
    "kyyykkkkkkkkyyyk",
    "kyyyggggggggyyyk",
    "kyyyggggggggyyyk",
    "kyyykkkkkkkkyyyk",
    "kyyyk......kyyyk",
    ".kkk........kkk.",
    "................",
    "................",
    "................",
    "................",
  ],
  sheet: [
    "................",
    "..kkkkkkkkkkkk..",
    "..knnnnnnnnnnk..",
    "..knnnnnnnnnnk..",
    "..kkkkkkkkkkkk..",
    "..kwwwkwwwwwwk..",
    "..kkkkkkkkkkkk..",
    "..kwwwkwwwwwwk..",
    "..kkkkkkkkkkkk..",
    "..kwwwkwwwwwwk..",
    "..kkkkkkkkkkkk..",
    "..kwwwkwwwwwwk..",
    "..kkkkkkkkkkkk..",
    "................",
    "................",
    "................",
  ],
};

function draw(canvas: HTMLCanvasElement, rows: string[]): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  rows.forEach((row, y) =>
    [...row].forEach((ch, x) => {
      const colour = PALETTE[ch];
      if (!colour) return;
      ctx.fillStyle = colour;
      ctx.fillRect(x, y, 1, 1);
    }),
  );
}

if (typeof document !== "undefined") {
  for (const c of document.querySelectorAll<HTMLCanvasElement>("canvas[data-icon]")) {
    const rows = ICONS[c.dataset.icon ?? ""];
    if (rows) draw(c, rows);
  }
}

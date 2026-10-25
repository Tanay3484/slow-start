// The field guide: every creature, where it lives, how to catch it, and trivia nobody asked for.
import "@fontsource/press-start-2p/index.css";
import "./site.css";
import { drawSprite, spriteSize } from "../art/sprites";
import { h } from "../dom";
import { ALL_IDS, CREATURES, GUIDE, HABITAT_LABEL, SLUMBROCK_STAGES } from "../game/creatures";
import type { Habitat } from "../types";

const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Creatures this browser has met in live play (read-only; the guide never changes a save). */
function seenInLive(): Set<string> {
  try {
    const raw = localStorage.getItem("slowstart.live.v1");
    return new Set(raw ? ((JSON.parse(raw) as { seen?: string[] }).seen ?? []) : []);
  } catch {
    return new Set();
  }
}

interface Anim {
  canvas: HTMLCanvasElement;
  sprite: string;
  scale: number;
  hop: number;
  phase: number;
}
const anims: Anim[] = [];

function spriteCanvas(sprite: string, scale: number): HTMLCanvasElement {
  const s = spriteSize(sprite);
  const canvas = h("canvas", { width: s.w * scale, height: s.h * scale + 8, "aria-hidden": "true" });
  const a: Anim = { canvas, sprite, scale, hop: 0, phase: Math.random() * 3000 };
  anims.push(a);
  canvas.addEventListener("pointerenter", () => (a.hop = 1));
  canvas.addEventListener("click", () => (a.hop = 1));
  return canvas;
}

function loop(t: number): void {
  for (const a of anims) {
    const g = a.canvas.getContext("2d")!;
    g.clearRect(0, 0, a.canvas.width, a.canvas.height);
    const frame = Math.floor(((t + a.phase) / 1000) * 5);
    const blink = (t + a.phase) % 3600 < 130;
    const hop = a.hop > 0 ? Math.sin(a.hop * Math.PI) * 4 * a.scale : 0;
    if (a.hop > 0) a.hop = Math.max(0, a.hop - 0.035);
    const bob = calm ? 0 : Math.sin((t + a.phase) / 480) * a.scale * 0.6;
    g.fillStyle = "rgba(0,0,0,0.3)";
    g.fillRect(a.canvas.width * 0.22, a.canvas.height - 6, a.canvas.width * 0.56, 3);
    drawSprite(g, a.sprite, 0, bob - hop + 2, a.scale, { frame, face: blink ? "blink" : hop > a.scale * 2.5 ? "hit" : "idle" });
  }
  requestAnimationFrame(loop);
}

function stages(): void {
  const box = document.getElementById("stages")!;
  SLUMBROCK_STAGES.forEach((s, i) => {
    box.append(
      h("article", { class: "stage-card" },
        spriteCanvas(`slumbrock_${i}`, 3),
        h("span", { class: "stage-n" }, `Stage ${i + 1}`),
        h("b", {}, s.name),
        h("p", {}, s.text),
      ),
    );
  });
}

function bestiary(): void {
  const seen = seenInLive();
  const cards = document.getElementById("cards")!;
  const filters = document.getElementById("filters")!;
  const all: { el: HTMLElement; habitat: Habitat }[] = [];
  for (const id of ALL_IDS) {
    const c = CREATURES[id];
    const g = GUIDE[id];
    const el = h("article", { class: `beast ${c.habitat === "rare" ? "rare" : ""}` },
      h("div", { class: "beast-art" }, spriteCanvas(c.sprite, 4), seen.has(id) ? h("span", { class: "seen" }, "Seen") : null),
      h("div", { class: "beast-body" },
        h("div", { class: "beast-head" },
          h("b", {}, c.name),
          h("span", { class: `rarity r-${g.rarity.toLowerCase()}` }, g.rarity),
        ),
        h("span", { class: "hab" }, HABITAT_LABEL[c.habitat]),
        h("p", { class: "blurb" }, c.blurb),
        h("dl", {},
          h("dt", {}, "Where"), h("dd", {}, g.find),
          h("dt", {}, "How to catch"), h("dd", {}, g.howToCatch),
        ),
        h("p", { class: "trivia-label" }, "Did you know?"),
        h("ul", { class: "trivia" }, ...g.trivia.map((t) => h("li", {}, t))),
      ),
    );
    all.push({ el, habitat: c.habitat });
    cards.append(el);
  }
  document.getElementById("n-creatures")!.textContent = String(ALL_IDS.length);
  document.getElementById("n-rare")!.textContent = String(ALL_IDS.filter((id) => GUIDE[id].rarity === "Rare").length);
  document.getElementById("n-seen")!.textContent = `${ALL_IDS.filter((id) => seen.has(id)).length}/${ALL_IDS.length}`;

  const kinds: (Habitat | "all")[] = ["all", "park", "street", "water", "gym", "rare"];
  const buttons = kinds.map((k) => {
    const b = h("button", { class: `btn ghost ${k === "all" ? "on" : ""}`, "aria-pressed": k === "all" ? "true" : "false" }, k === "all" ? "All" : HABITAT_LABEL[k]);
    b.addEventListener("click", () => {
      buttons.forEach((x) => {
        x.classList.toggle("on", x === b);
        x.setAttribute("aria-pressed", String(x === b));
      });
      all.forEach(({ el, habitat }) => (el.hidden = k !== "all" && habitat !== k));
    });
    return b;
  });
  filters.append(...buttons);
}

stages();
bestiary();
requestAnimationFrame(loop);

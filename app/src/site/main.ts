// The landing page: a scroll story, the real numbers, a live controller widget and the creature cards.
import "@fontsource/press-start-2p/index.css";
import "./site.css";
import { Capacitor } from "@capacitor/core";
import { Arena } from "../art/arena";
import { drawSprite, spriteSize } from "../art/sprites";
import { h } from "../dom";
import { CREATURES, HABITAT_LABEL } from "../game/creatures";
import evidence from "./evidence.json";

// In the Android app there is no landing page: go straight to the game.
if (Capacitor.isNativePlatform()) location.replace("./play.html");

const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
const fmtInt = (n: number) => n.toLocaleString("en-US");
const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

// ---------------------------------------------------------------- the story

const BEATS = [
  { stage: 0, hour: 23, pals: [] as string[] },
  { stage: 1, hour: 6, pals: ["mossling"] },
  { stage: 2, hour: 12, pals: ["mossling", "leafwing"] },
  { stage: 3, hour: 18, pals: ["leafwing", "ripplet"] },
] as const;

function story(): void {
  const section = document.getElementById("story")!;
  const scene = document.getElementById("scene")!;
  const beats = [...section.querySelectorAll<HTMLElement>("[data-beat]")];
  const bar = section.querySelector<HTMLElement>(".progress i")!;
  const pips = [...section.querySelectorAll<HTMLElement>("[data-pip]")];
  const arena = new Arena();
  scene.append(arena.el);
  arena.start();
  let current = -1;
  const show = (i: number) => {
    if (i === current) return;
    current = i;
    const b = BEATS[i];
    arena.update({
      day: "story",
      stage: b.stage,
      creature: "mossling",
      creatureName: "",
      habitat: "park",
      hp: 1,
      hpSteps: 1,
      goal: 0,
      hour: b.hour,
      caught: false,
      companions: [...b.pals],
      noFoe: true,
    });
    beats.forEach((el, j) => el.classList.toggle("on", j === i));
    pips.forEach((el, j) => el.classList.toggle("on", j <= i));
    section.dataset.beat = String(i);
  };
  let ticking = false;
  const onScroll = () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      ticking = false;
      const r = section.getBoundingClientRect();
      const span = section.offsetHeight - innerHeight;
      const p = Math.min(1, Math.max(0, -r.top / Math.max(1, span)));
      bar.style.width = `${(p * 100).toFixed(1)}%`;
      show(Math.min(3, Math.floor(p * 4 * 0.999)));
      section.classList.toggle("done", p > 0.96);
    });
  };
  addEventListener("scroll", onScroll, { passive: true });
  addEventListener("resize", onScroll);
  show(0);
  onScroll();
}

// ---------------------------------------------------------------- evidence

type Ev = typeof evidence;
function lookup(path: string): unknown {
  return path.split(".").reduce<unknown>((o, k) => (o as Record<string, unknown> | undefined)?.[k], evidence as unknown);
}

function fillEvidence(): void {
  document.querySelectorAll<HTMLElement>("[data-ev]").forEach((el) => {
    const v = lookup(el.dataset.ev!);
    if (typeof v !== "number") return;
    el.textContent = el.dataset.fmt === "pct" ? pct(v) : fmtInt(v);
  });
  const ev = evidence as Ev;
  // Every row comes from the same runs: the controller at the step chosen on validation.
  const rows: [string, keyof Ev["sweep_final"]["policies"], boolean][] = [
    ["Fixed 10,000", "fixed_10000", false],
    ["Your 28-day median", "trailing_median_28d", false],
    ["Your 30th percentile", "own_p30_28d", true],
    ["TabPFN 30th percentile", "tabpfn_p30_cap", true],
    ["Slow Start (rules + TabPFN cap)", "controller_tabpfn_cap", true],
  ];
  const body = document.getElementById("ev-rows")!;
  for (const [label, key, strong] of rows) {
    const val = ev.sweep_validation.policies[key];
    const fin = ev.sweep_final.policies[key];
    body.append(
      h("tr", { class: strong ? "strong" : "" },
        h("td", {}, label),
        h("td", {}, pct(val.goal_met)),
        h("td", {}, pct(fin.goal_met)),
        h("td", {}, `${Math.round(fin.goal_level * 100)}%`),
      ),
    );
  }
  const vs = ev.sweep_final.policies.controller_tabpfn_cap.vs_p30 as number[];
  const signed = (x: number) => `${x >= 0 ? "+" : "−"}${Math.abs(x * 100).toFixed(1)}`;
  document.getElementById("ev-note")!.textContent =
    `${ev.final_v1.people} people, ${fmtInt(ev.validation_v1.person_days)} validation and ${fmtInt(ev.final_v1.person_days)} final person-days. ` +
    `"Asks for" is the goal as a share of the person's usual day: lower goals are always easier to meet, so read the two together. ` +
    `Slow Start against the plain percentile on the final window: ${signed(vs[0])} points (95% interval ${signed(vs[1])} to ${signed(vs[2])}). A tie.`;
}

function waffle(): void {
  const box = document.getElementById("waffle")!;
  const lit = Math.round((evidence as Ev).final_v1.policies.fixed_10000.goal_met * 100);
  const cells = Array.from({ length: 100 }, () => box.appendChild(h("i", {})));
  let done = false;
  new IntersectionObserver((entries) => {
    if (done || !entries.some((e) => e.isIntersecting)) return;
    done = true;
    // light the met days in a scattered order (a fixed shuffle, so it looks the same every visit)
    let seed = 7;
    const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
    const order = cells.map((_, i) => i);
    for (let i = order.length - 1; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [order[i], order[j]] = [order[j], order[i]];
    }
    order.slice(0, lit).forEach((i, n) => setTimeout(() => cells[i].classList.add("on"), calm ? 0 : n * 18));
  }, { threshold: 0.4 }).observe(box);
}

// ---------------------------------------------------------------- try the controller

interface TryDay { date: string; steps: number | null; goal: number | null; excused: boolean }

function tryWidget(): void {
  const box = document.getElementById("try-box")!;
  const goalEl = document.getElementById("try-goal")!;
  const phaseEl = document.getElementById("try-phase")!;
  const note = document.getElementById("try-note")!;
  const chart = document.getElementById("try-chart")!;
  const start = new Date(Date.UTC(2026, 0, 1));
  const iso = (n: number) => new Date(start.getTime() + n * 86_400_000).toISOString().slice(0, 10);
  let days: TryDay[] = [];
  let goal = 1500;
  const shown: { goal: number; kind: string }[] = [];
  const PHASE: Record<string, [string, string]> = {
    slow_start: ["Slow start", "slow_start"],
    cruising: ["Cruising", "cruising"],
    recovering: ["Recovering", "recovering"],
  };

  const draw = () => {
    const ns = "http://www.w3.org/2000/svg";
    chart.replaceChildren();
    const rows = shown.slice(-14);
    const max = Math.max(4000, ...rows.map((r) => r.goal), goal);
    const bw = 300 / 15;
    const y = (v: number) => 112 - (v / max) * 100;
    rows.forEach((r, i) => {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("x", String(i * bw + 3));
      rect.setAttribute("width", String(bw - 6));
      rect.setAttribute("y", String(y(r.goal)));
      rect.setAttribute("height", String(112 - y(r.goal)));
      rect.setAttribute("class", `b ${r.kind}`);
      chart.append(rect);
    });
    const next = document.createElementNS(ns, "rect");
    next.setAttribute("x", String(rows.length * bw + 3));
    next.setAttribute("width", String(bw - 6));
    next.setAttribute("y", String(y(goal)));
    next.setAttribute("height", String(112 - y(goal)));
    next.setAttribute("class", "b next");
    chart.append(next);
  };

  const ask = async () => {
    box.classList.add("busy");
    try {
      const res = await fetch("./api/goal/steps", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ today: iso(days.length), history: days, use_cap: false }),
      });
      if (res.status === 429) throw new Error("Easy: too many clicks. Wait a few seconds.");
      if (!res.ok) throw new Error(`The server said ${res.status}`);
      const g = (await res.json()) as { goal: number; phase: string; source: string };
      goal = g.goal;
      goalEl.textContent = fmtInt(goal);
      const [label, cls] = PHASE[g.phase] ?? ["", ""];
      phaseEl.textContent = label;
      phaseEl.className = `chip ${cls}`;
      note.textContent =
        g.source === "fallback"
          ? "Stand-in answering: the real controller is still being written by hand, so this shows a plain baseline instead of the doubling."
          : "The real controller answered.";
    } catch (e) {
      note.textContent = e instanceof Error && e.message.startsWith("Easy") ? e.message : "The server is asleep right now. The game itself works offline.";
    } finally {
      box.classList.remove("busy");
      draw();
    }
  };

  box.addEventListener("click", (e) => {
    const act = (e.target as HTMLElement).closest<HTMLButtonElement>("[data-act]")?.dataset.act;
    if (!act || box.classList.contains("busy")) return;
    if (act === "reset") {
      days = [];
      shown.length = 0;
    } else {
      const steps = act === "win" ? goal + 200 : act === "miss" ? Math.round(goal * 0.55) : 0;
      days.push({ date: iso(days.length), steps: act === "rest" ? null : steps, goal, excused: act === "rest" });
      shown.push({ goal, kind: act });
    }
    void ask();
  });
  draw();
  void ask();
}

// ---------------------------------------------------------------- creatures

function creatures(): void {
  const grid = document.getElementById("creature-grid")!;
  const cards: { canvas: HTMLCanvasElement; sprite: string; hop: number; phase: number }[] = [];
  for (const [id, c] of Object.entries(CREATURES)) {
    const size = spriteSize(c.sprite);
    const canvas = h("canvas", { width: size.w * 3, height: size.h * 3 + 6, "aria-hidden": "true" });
    const card = h("article", { class: `creature reveal ${c.habitat === "rare" ? "rare" : ""}`, tabindex: 0 },
      canvas,
      h("b", {}, c.name),
      h("span", { class: "hab" }, HABITAT_LABEL[c.habitat]),
      h("p", {}, c.blurb),
    );
    const entry = { canvas, sprite: c.sprite, hop: 0, phase: Math.random() * 3000 };
    const poke = () => (entry.hop = 1);
    card.addEventListener("pointerenter", poke);
    card.addEventListener("focus", poke);
    card.addEventListener("click", poke);
    grid.append(card);
    cards.push(entry);
    void id;
  }
  const loop = (t: number) => {
    for (const c of cards) {
      const g = c.canvas.getContext("2d")!;
      g.clearRect(0, 0, c.canvas.width, c.canvas.height);
      const fps = 5;
      const frame = Math.floor(((t + c.phase) / 1000) * fps);
      const blink = (t + c.phase) % 3400 < 130;
      const hop = c.hop > 0 ? Math.sin(c.hop * Math.PI) * 12 : 0;
      if (c.hop > 0) c.hop = Math.max(0, c.hop - 0.035);
      const bob = calm ? 0 : Math.sin((t + c.phase) / 480) * 2;
      g.fillStyle = "rgba(0,0,0,0.3)";
      g.fillRect(c.canvas.width * 0.25, c.canvas.height - 5, c.canvas.width * 0.5, 3);
      drawSprite(g, c.sprite, 0, bob - hop, 3, { frame, face: blink ? "blink" : hop > 6 ? "hit" : "idle" });
    }
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
}

// ---------------------------------------------------------------- reveal on scroll

function reveal(): void {
  const io = new IntersectionObserver(
    (entries) => entries.forEach((e) => e.isIntersecting && (e.target.classList.add("in"), io.unobserve(e.target))),
    { threshold: 0.15, rootMargin: "0px 0px -40px 0px" },
  );
  document.querySelectorAll(".reveal").forEach((el, i) => {
    (el as HTMLElement).style.setProperty("--d", `${(i % 4) * 70}ms`);
    io.observe(el);
  });
}

story();
fillEvidence();
waffle();
tryWidget();
creatures();
reveal();

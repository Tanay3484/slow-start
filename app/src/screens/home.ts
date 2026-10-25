import type { Controller } from "../controller";
import { dayOf, hpLeft, statsOf } from "../game/day";
import { CREATURES, HABITAT_LABEL, STAGE_NAMES } from "../game/creatures";
import { nextStageAt, stageOf, xpRuleWritten } from "../game/rules";
import { h, fmt } from "../dom";
import type { DayRecord, Goal, Phase } from "../types";

const PHASE_TEXT: Record<Phase, { chip: string; why: string }> = {
  slow_start: { chip: "Slow start", why: "The window doubles after every win, until the first miss tells it where your level is." },
  cruising: { chip: "Cruising", why: "You are near your level now, so the window grows by a small fixed step after each win." },
  recovering: { chip: "Recovering", why: "The last counted day was missed, so the window was halved. It never drops to zero." },
};

function toggled(c: Controller, key: string, e: Event): void {
  if ((e.target as HTMLDetailsElement).open) c.open.add(key);
  else c.open.delete(key);
}

function bubbleText(c: Controller, day: DayRecord): string {
  const stage = stageOf(c.xp);
  if (c.s.checkin?.date === c.date) return c.s.checkin.line;
  if (day.outcome === "win") return ["...mm. Good. I felt that.", "Steady steps. I am waking up.", "Let us stomp. Again tomorrow."][stage % 3];
  if (day.outcome === "miss") return "Missed one? Fine. Tomorrow's goal gets smaller, and I am still here.";
  if (day.excused) return "Rest. I am not going anywhere.";
  if (stage === 0) return "...zzz... Small steps wake me... zzz...";
  return "A wild creature is in the way. Walk it down.";
}

function trendChart(days: DayRecord[]): SVGElement | null {
  const rows = days.filter((d) => d.goal !== null).slice(-14);
  if (rows.length < 2) return null;
  const W = 300;
  const H = 90;
  const max = Math.max(...rows.map((d) => Math.max(d.goal ?? 0, d.steps ?? 0)), 1000);
  const bw = W / rows.length;
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("class", "trend");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Goal (gold line) against steps (bars) for the last days");
  const y = (v: number) => H - 4 - (v / max) * (H - 12);
  rows.forEach((d, i) => {
    const bar = document.createElementNS(ns, "rect");
    const top = y(d.steps ?? 0);
    bar.setAttribute("x", String(i * bw + 2));
    bar.setAttribute("y", String(top));
    bar.setAttribute("width", String(Math.max(2, bw - 4)));
    bar.setAttribute("height", String(H - 4 - top));
    bar.setAttribute("class", d.outcome === "win" ? "bar win" : d.outcome === "miss" ? "bar miss" : "bar");
    svg.append(bar);
  });
  const pts = rows.map((d, i) => `${i * bw + bw / 2},${y(d.goal ?? 0)}`).join(" ");
  const line = document.createElementNS(ns, "polyline");
  line.setAttribute("points", pts);
  line.setAttribute("class", "goal-line");
  svg.append(line);
  return svg;
}

function goalCard(c: Controller, day: DayRecord): HTMLElement {
  const goal: Goal | null = c.s.goalCache?.date === c.date ? c.s.goalCache.goal : null;
  const card = h("section", { class: "card goal" });
  card.append(h("h2", {}, "Today's goal"));
  if (c.busy === "goal" || day.goal === null) {
    card.append(h("p", { class: "waking" }, "Slumbrock is waking up… the first goal can take a moment while the model loads."));
    return card;
  }
  card.append(h("div", { class: "big" }, fmt(day.goal), h("small", {}, " steps")));
  if (goal) {
    const phase = PHASE_TEXT[goal.phase];
    const chips = h("div", { class: "chips" }, h("span", { class: `chip ${goal.phase}` }, phase.chip));
    if (goal.source !== "controller") {
      chips.append(h("span", { class: "chip warn", title: goal.note }, goal.source === "offline" ? "Offline goal" : "Baseline goal"));
    }
    card.append(chips);
    const capText =
      goal.cap.source === "tabpfn"
        ? `${fmt(goal.cap.value ?? 0)} (TabPFN: about 7 days in 10 you reach this)`
        : goal.cap.source === "median"
          ? `${fmt(goal.cap.value ?? 0)} (80% of your recent median; the predictor was unavailable)`
          : "none yet (it needs a week of your steps)";
    card.append(
      h(
        "details",
        { class: "why", open: c.open.has("why"), ontoggle: (e: Event) => toggled(c, "why", e) },
        h("summary", {}, "Why this number?"),
        h("p", {}, phase.why),
        h("ul", {},
          h("li", {}, h("b", {}, "Window "), `${fmt(goal.window)}: what the controller asks for.`),
          h("li", {}, h("b", {}, "Cap "), capText),
          h("li", {}, h("b", {}, "Goal "), "the lower of the two. Like TCP: the sender's window and the receiver's window."),
        ),
        goal.note ? h("p", { class: "note" }, goal.note) : null,
      ),
    );
  }
  return card;
}

function stepsCard(c: Controller, day: DayRecord): HTMLElement {
  const card = h("section", { class: "card" });
  card.append(h("h2", {}, "Steps"));
  if (day.goal === null) return card;
  const done = day.outcome === "win";
  card.append(
    h("p", { class: "meta" }, `Logged ${fmt(day.steps ?? 0)} of ${fmt(day.goal)}.`, done ? " Caught!" : day.outcome === "miss" ? " This one got away." : ""),
  );

  if (c.isDemo) {
    if (c.demoOver) return card;
    const played = day.steps !== null || day.excused;
    card.append(
      h("p", { class: "meta" }, `Day ${Math.min(c.s.demoIndex + 1, c.demoLength)} of ${c.demoLength} of one real person's steps (public data).`),
      played
        ? h("button", { class: "btn primary", onclick: () => void c.nextDemoDay() }, c.s.demoIndex + 1 >= c.demoLength ? "See how it ended ▶" : "Next day ▶")
        : h("button", { class: "btn primary", onclick: () => c.playDemoDay() }, "Walk the day ▶"),
    );
    return card;
  }

  const input = h("input", { type: "number", inputmode: "numeric", min: 0, max: 100000, placeholder: "Steps today", "aria-label": "Steps today", value: day.steps ?? "" });
  const save = () => {
    const n = Number(input.value);
    if (input.value !== "" && Number.isFinite(n)) c.logSteps(n);
  };
  card.append(
    h("div", { class: "row" }, input, h("button", { class: "btn primary", onclick: save }, "Log")),
    h("div", { class: "row quick" }, ...[500, 1000, 2000].map((n) => h("button", { class: "btn", onclick: () => c.logSteps((day.steps ?? 0) + n) }, `+${fmt(n)}`))),
    h(
      "label",
      { class: "check" },
      h("input", { type: "checkbox", checked: day.excused, onchange: (e: Event) => c.setExcused((e.target as HTMLInputElement).checked) }),
      " Ill or hurt today? Excuse the day: nothing changes, no penalty.",
    ),
  );
  return card;
}

function trainCard(c: Controller): HTMLElement {
  const card = h("details", { class: "card train", open: c.open.has("train"), ontoggle: (e: Event) => toggled(c, "train", e) });
  card.append(h("summary", {}, "Optional: train today for bonus XP"));
  if (!c.catalog) {
    card.append(h("p", { class: "meta" }, "Waiting for the server…"));
    return card;
  }
  const ids = Object.keys(c.catalog);
  const select = h(
    "select",
    { "aria-label": "Exercise", onchange: (e: Event) => { c.selectedExercise = (e.target as HTMLSelectElement).value; void c.loadTarget(c.selectedExercise); c.onChange(); } },
    ...ids.map((id) => h("option", { value: id, selected: id === c.selectedExercise }, c.catalog![id].label)),
  );
  card.append(h("p", { class: "meta" }, "No gym? Push-ups and bodyweight squats count the same. And no workout at all is fine: a walk is a full way to play."), select);
  const info = c.catalog[c.selectedExercise];
  const goal = c.targets.get(c.selectedExercise);
  if (!goal) {
    void c.loadTarget(c.selectedExercise);
    card.append(h("p", { class: "meta" }, "Fetching a target…"));
    return card;
  }
  const t = goal.target;
  const weighted = info.kind !== "bodyweight";
  card.append(
    h("div", { class: "big small" }, `${t.sets} × ${t.reps}`, weighted && t.weight_kg !== null ? ` @ ${t.weight_kg} kg` : ""),
  );
  if (goal.source === "fallback") card.append(h("span", { class: "chip warn", title: goal.note }, "Baseline target"));
  const sets = h("input", { type: "number", min: 1, max: 20, value: t.sets, "aria-label": "Sets" });
  const reps = h("input", { type: "number", min: 1, max: 200, value: t.reps, "aria-label": "Reps" });
  const weight = h("input", { type: "number", min: 0, step: 0.5, value: t.weight_kg ?? "", "aria-label": "Weight in kilograms" });
  card.append(
    h("div", { class: "row triple" },
      h("label", {}, "Sets", sets), h("label", {}, "Reps", reps), weighted ? h("label", {}, "kg", weight) : null),
    h("button", {
      class: "btn primary",
      onclick: () => {
        const w = weighted && weight.value !== "" ? Number(weight.value) : null;
        const n = Math.max(1, Math.min(20, Number(sets.value) || 1));
        c.logWorkout(c.selectedExercise, Array.from({ length: n }, () => ({ weight_kg: w, reps: Math.max(1, Number(reps.value) || 1) })));
      },
    }, "Log it"),
  );
  return card;
}

/** The arena and everything about Slumbrock. On a wide screen it stays pinned beside every tab. */
export function stagePanel(c: Controller): HTMLElement {
  const day = c.day;
  const xp = c.xp;
  const stage = stageOf(xp);
  const creature = CREATURES[day.creature] ?? CREATURES.mossling;
  const goal = day.goal ?? 0;
  const left = hpLeft(goal || 1, day.steps);
  const next = nextStageAt(xp);
  const stats = statsOf(c.s.days, c.s.workouts);

  c.syncArena();
  const hpPct = day.goal === null ? 100 : Math.round((left / goal) * 100);
  const arena = h("div", { class: "arena-wrap" }, c.arena.el, h("p", { class: "tap-hint" }, "Tap them"));
  const plates = h("div", { class: "plates" },
    h("div", { class: "plate me" },
      h("div", { class: "name" }, "Slumbrock", h("small", {}, ` ${STAGE_NAMES[stage]}`)),
      h("div", { class: "bar xp" }, h("i", { style: `width:${next === null ? 100 : Math.min(100, Math.round((xp / next) * 100))}%` })),
      h("div", { class: "num" }, next === null ? `XP ${fmt(xp)} · MAX` : `XP ${fmt(xp)} / ${fmt(next)}`),
    ),
    h("div", { class: `plate foe ${day.outcome === "win" ? "caught" : ""}` },
      h("div", { class: "name" }, creature.name, h("small", {}, ` ${HABITAT_LABEL[creature.habitat]}`)),
      h("div", { class: "bar hp" }, h("i", { style: `width:${hpPct}%` })),
      h("div", { class: "num" }, day.goal === null ? "…" : day.outcome === "win" ? "CAUGHT" : `HP ${fmt(left)}`),
    ),
  );
  const bubble = h("div", { class: "bubble", role: "status" }, bubbleText(c, day));
  const statRow = h("div", { class: "stats" },
    h("div", {}, h("span", {}, "Speed"), h("div", { class: "bar sm" }, h("i", { style: `width:${Math.round(stats.speed * 100)}%` }))),
    h("div", {}, h("span", {}, "Power"), h("div", { class: "bar sm pw" }, h("i", { style: `width:${Math.round(stats.power * 100)}%` }))),
  );
  const flags = h("div", { class: "chips" });
  if (!xpRuleWritten()) flags.append(h("span", { class: "chip warn", title: "H4 is not written yet; a simple rule is in use." }, "XP: baseline rule"));
  return h("section", { class: "stage", "aria-label": "Slumbrock" }, arena, plates, bubble, statRow, flags);
}

export function homeScreen(c: Controller): HTMLElement {
  const root = h("div", { class: "screen home" });
  const day = c.day;
  if (c.say) root.append(h("p", { class: `say ${c.say.kind}`, role: "status" }, c.say.text));
  root.append(goalCard(c, day), stepsCard(c, day), trainCard(c));
  const chart = trendChart(c.s.days.map((d) => dayOf(c.s, d.date)!));
  if (chart) root.append(h("section", { class: "card" }, h("h2", {}, "Goal against steps"), chart, h("p", { class: "meta" }, "Gold line: your goal. Bars: your steps (green: caught, red: got away). Watch it double, then halve, then creep up.")));
  if (c.demoOver) {
    root.append(h("section", { class: "card" }, h("h2", {}, "That's the whole story"), h("p", {}, "These were one real person's 40 days from a public dataset. Start your own, or watch it again."),
      h("div", { class: "row" }, h("button", { class: "btn primary", onclick: () => void c.switchMode("live") }, "Play for real"), h("button", { class: "btn", onclick: () => void c.restartDemo() }, "Watch again"))));
  }
  return root;
}

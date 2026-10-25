import { spriteUrl } from "../art/sprites";
import type { Controller } from "../controller";
import { h } from "../dom";
import { ALL_IDS, CREATURES, HABITAT_LABEL } from "../game/creatures";
import { xpRuleWritten } from "../game/rules";

// ---------------------------------------------------------------- Talk

const capitalise = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

export function talkScreen(c: Controller): HTMLElement {
  const root = h("div", { class: "screen" });
  const box = h("textarea", { maxlength: 300, rows: 3, placeholder: "e.g. leg day, knees sore, only a short walk in me", "aria-label": "How are you today?", oninput: (e: Event) => { c.draft = (e.target as HTMLTextAreaElement).value; } });
  box.value = c.draft;
  const send = () => {
    const text = box.value.trim();
    if (text) void c.sendCheckin(text);
  };
  root.append(
    h("section", { class: "card" },
      h("h2", {}, "Tell Slumbrock"),
      h("p", { class: "meta" }, "One line about how today feels. Gemma answers as Slumbrock; the tip and whether the day is excused are decided by code. Ill or hurt? The day is excused: no cut, no penalty."),
      box,
      h("button", { class: "btn primary", disabled: c.busy === "checkin", onclick: send }, c.busy === "checkin" ? "Slumbrock is thinking…" : "Talk"),
    ),
  );
  const r = c.lastCheckin;
  if (r) {
    root.append(
      h("section", { class: "card reply" },
        h("div", { class: "bubble big-bubble" }, r.line, r.aside ? h("span", { class: "aside" }, ` ${r.aside}`) : null),
        r.tip ? h("p", { class: "tip" }, capitalise(r.tip.replace(/^Tip:\s*/, ""))) : null,
        h("div", { class: "chips" },
          h("span", { class: "chip" }, `Energy: ${r.energy}`),
          ...r.body.map((b) => h("span", { class: "chip" }, b)),
          r.excused ? h("span", { class: "chip good" }, "Day excused") : null,
          h("span", { class: "chip warn", title: "Where the reply line came from" }, r.source === "gemma" ? "Gemma" : "Template (model not reachable)"),
        ),
      ),
    );
  }
  if (c.say) root.append(h("p", { class: `say ${c.say.kind}` }, c.say.text));
  return root;
}

// ---------------------------------------------------------------- Places

export function placesScreen(c: Controller): HTMLElement {
  const root = h("div", { class: "screen" });
  const mode = (a: "walk" | "train", label: string) =>
    h("button", { class: `btn ${c.placesActivity === a ? "primary" : ""}`, onclick: () => void c.searchPlaces(a) }, label);
  root.append(
    h("section", { class: "card" },
      h("h2", {}, "Find a spot"),
      h("p", { class: "meta" }, "Log your steps or a workout from somewhere you have never logged from, and a rare creature follows you home."),
      h("div", { class: "row" }, mode("walk", "Places to walk"), mode("train", "Places to train")),
      h("p", { class: "privacy" }, "Your exact position stays on this device. OpenStreetMap only gets the centre of a ~1 km square, and only a square id is saved."),
    ),
  );
  if (c.busy === "places") root.append(h("p", { class: "waking" }, "Looking around…"));
  if (c.places) {
    root.append(
      ...c.places.map((p) =>
        h("section", { class: "card place" },
          h("div", {}, h("b", {}, p.name), h("div", { class: "meta" }, `${p.kind} · ${HABITAT_LABEL[p.habitat]} · ${p.walkMin} min walk (${p.distanceM} m)`)),
          h("button", { class: "btn", onclick: () => void c.exploreAt(p) }, "I'm here"),
        ),
      ),
    );
  }
  if (c.say) root.append(h("p", { class: `say ${c.say.kind}` }, c.say.text));
  return root;
}

// ---------------------------------------------------------------- Collection

export function dexScreen(c: Controller): HTMLElement {
  const root = h("div", { class: "screen" });
  const seen = new Set(c.s.seen);
  root.append(h("section", { class: "card" }, h("h2", {}, `Collection ${ALL_IDS.filter((i) => seen.has(i)).length} / ${ALL_IDS.length}`),
    h("p", { class: "meta" }, "Every day brings a wild creature. Different places bring different ones, and somewhere new brings a rare one."),
    h("a", { class: "btn", href: "./guide.html" }, "Field guide and trivia")));
  const grid = h("div", { class: "dex" });
  for (const id of ALL_IDS) {
    const cr = CREATURES[id];
    const known = seen.has(id);
    grid.append(
      h("div", { class: `dex-item ${known ? "" : "unknown"}` },
        h("img", { src: spriteUrl(cr.sprite, known ? undefined : "#333c57"), alt: known ? cr.name : "Unknown creature", width: 72, height: 72 }),
        h("b", {}, known ? cr.name : "???"),
        h("span", { class: "meta" }, known ? cr.blurb : cr.habitat === "rare" ? "Found somewhere new" : `Lives in: ${HABITAT_LABEL[cr.habitat]}`),
      ),
    );
  }
  root.append(grid);
  return root;
}

// ---------------------------------------------------------------- Data

async function readFiles(input: HTMLInputElement): Promise<string[]> {
  return Promise.all([...(input.files ?? [])].map((f) => f.text()));
}

export function dataScreen(c: Controller): HTMLElement {
  const root = h("div", { class: "screen" });
  const out = h("p", { class: "say info", role: "status" });
  out.hidden = true;
  const show = (text: string, kind: "info" | "good" | "bad" = "info") => {
    out.hidden = false;
    out.className = `say ${kind}`;
    out.textContent = text;
  };

  const stepsFile = h("input", { type: "file", accept: ".json,.csv,.txt", multiple: true, "aria-label": "Step files" });
  const hevyFile = h("input", { type: "file", accept: ".csv", "aria-label": "Hevy export" });

  root.append(
    h("section", { class: "card" },
      h("h2", {}, c.isDemo ? "Demo mode" : "Your data"),
      h("p", { class: "meta" }, c.isDemo ? "You are watching one real person from a public dataset. Nothing here is yours." : "Everything is stored on this device only. The server processes an import in memory and keeps nothing."),
      h("button", { class: "btn", onclick: () => void c.switchMode(c.isDemo ? "live" : "demo") }, c.isDemo ? "Play for real" : "Watch the demo"),
    ),
  );

  if (!c.isDemo) {
    root.append(
      h("section", { class: "card" },
        h("h2", {}, "Import steps"),
        h("p", { class: "meta" }, "A Fitbit / Pixel Watch export from Google Takeout (the steps-*.json files), or any CSV with date and steps columns. Days with 0 steps are treated as the tracker not being worn."),
        stepsFile,
        h("button", { class: "btn", onclick: async () => {
          try {
            show("Reading…");
            const texts = await readFiles(stepsFile);
            if (!texts.length) return show("Choose a file first.");
            const lines: string[] = [];
            for (const t of texts) lines.push(await c.importStepsFile(t));
            show(lines.join(" "), "good");
          } catch (e) {
            show(e instanceof Error ? e.message : "Could not read that file", "bad");
          }
        } }, "Import steps"),
      ),
      h("section", { class: "card" },
        h("h2", {}, "Import workouts"),
        h("p", { class: "meta" }, "A Hevy CSV export (Profile, Settings, Export data). Only the main lifts, a few dumbbell lifts and bodyweight moves are used; warm-ups are skipped."),
        hevyFile,
        h("button", { class: "btn", onclick: async () => {
          try {
            show("Reading…");
            const [text] = await readFiles(hevyFile);
            if (!text) return show("Choose a file first.");
            show(await c.importHevyFile(text), "good");
          } catch (e) {
            show(e instanceof Error ? e.message : "Could not read that file", "bad");
          }
        } }, "Import workouts"),
      ),
    );
  }
  root.append(out);

  root.append(
    h("section", { class: "card" },
      h("h2", {}, "Your copy"),
      h("div", { class: "row" },
        h("button", { class: "btn", onclick: async () => {
          try {
            await navigator.clipboard.writeText(c.exportJson());
            show("Copied to the clipboard.", "good");
          } catch {
            show("Could not copy; try Download.", "bad");
          }
        } }, "Copy"),
        h("button", { class: "btn", onclick: () => {
          const a = h("a", { href: URL.createObjectURL(new Blob([c.exportJson()], { type: "application/json" })), download: "slow-start.json" });
          a.click();
          URL.revokeObjectURL(a.href);
        } }, "Download"),
        h("button", { class: "btn danger", onclick: () => { if (confirm("Delete everything saved on this device?")) c.wipe(); } }, "Delete all"),
      ),
    ),
  );

  const hl = c.health;
  const lv = hl?.levels ?? {};
  const row = (k: string, v: string) => h("li", {}, h("b", {}, `${k} `), v);
  root.append(
    h("section", { class: "card status" },
      h("h2", {}, "Under the hood"),
      hl
        ? h("ul", {},
            row("Predictor", hl.predictor === "tabpfn-v2" ? "TabPFN v2, open weights, running on the server's CPU" : "none (goals use the median cap)"),
            row("Language model", `${hl.model} (Gemma, through Ollama) reads check-ins; it never sets a number`),
            row("Step controller (H1)", lv.H1 === "unlocked" ? "written" : "not written yet: a baseline goal is used"),
            row("Exercise controller (H2)", lv.H2 === "unlocked" ? "written" : "not written yet: 'repeat last time' is used"),
            row("XP rule (H4)", xpRuleWritten() ? "written" : "not written yet: a simple rule is used"),
          )
        : h("p", { class: "meta" }, "The server is out of reach, so goals come from your recent median."),
      h("p", { class: "meta" }, "Open source, MIT. Step data in the demo: Kaggle Fitbit set (CC0). Place search adapted from Golden Hour. All art is original pixel art."),
    ),
  );
  return root;
}

// ---------------------------------------------------------------- Welcome

export function welcomeOverlay(c: Controller): HTMLElement {
  return h("div", { class: "overlay", role: "dialog", "aria-modal": "true", "aria-label": "Welcome" },
    h("div", { class: "card welcome" },
      h("h1", {}, "Slow Start"),
      h("p", {}, "Meet ", h("b", {}, "Slumbrock"), ", a sleepy stone giant. It wakes up as you keep going. Your daily goal starts tiny, doubles after each win, and halves after a miss, the way a network connection finds its speed. Never to zero."),
      h("p", { class: "meta" }, "No account. Your data stays on this device. Walking alone is a full way to play; workouts are a bonus."),
      h("div", { class: "row" },
        h("button", { class: "btn primary", onclick: () => { c.dismissWelcome(); void c.switchMode("demo"); } }, "Watch the demo"),
        h("button", { class: "btn", onclick: () => c.dismissWelcome() }, "Start for real"),
      ),
    ),
  );
}

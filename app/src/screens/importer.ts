// Importing history, on the Today screen in live play: steps from a phone or watch export, and an
// optional Hevy log. Open on a fresh start; folded away once there is history.
import type { Controller } from "../controller";
import { h } from "../dom";
import { type ImportReport, issueUrl } from "../issue";

async function readFiles(input: HTMLInputElement): Promise<string[]> {
  return Promise.all([...(input.files ?? [])].map((f) => f.text()));
}

const names = (input: HTMLInputElement) => [...(input.files ?? [])].map((f) => f.name);

export function importCard(c: Controller): HTMLElement {
  const hasHistory = c.s.days.some((d) => d.steps !== null && d.goal === null);
  const card = h("details", {
    class: "card import",
    open: c.importNote !== null || c.open.has("import") || (!hasHistory && !c.open.has("import-shut")),
    ontoggle: (e: Event) => {
      const open = (e.target as HTMLDetailsElement).open;
      c.open[open ? "add" : "delete"]("import");
      c.open[open ? "delete" : "add"]("import-shut");
    },
  });
  card.append(h("summary", {}, hasHistory ? "Import more history" : "Bring your history: import steps and workouts"));

  const out = h("p", { class: "say info", role: "status" });
  out.hidden = true;
  const issue = h("a", { target: "_blank", rel: "noopener" }, "Raise an issue on GitHub");
  const help = h("p", { class: "meta issue-help" }, "Not sure, or the wrong numbers showing? ", issue, " and we will teach the cleaner your case. Only the file name and the message above go in; never the file.");
  help.hidden = true;
  const paint = (note: NonNullable<Controller["importNote"]>) => {
    out.hidden = false;
    out.className = `say ${note.kind}`;
    out.textContent = note.text;
    help.hidden = !note.report;
    if (note.report) issue.setAttribute("href", issueUrl({ ...note.report, said: note.text }));
  };
  const show = (text: string, kind: "info" | "good" | "bad" = "info", report?: Omit<ImportReport, "said">) => {
    c.importNote = { text, kind, report };
    paint(c.importNote);
    if (!card.isConnected) c.onChange(); // an import redraws the screen; draw the new one with the note
  };
  if (c.importNote) paint(c.importNote);

  const stepsFile = h("input", { type: "file", accept: ".json,.csv,.txt", multiple: true, "aria-label": "Step files" });
  const hevyFile = h("input", { type: "file", accept: ".csv", "aria-label": "Hevy export" });

  card.append(
    h("p", { class: "meta" }, "Your history sets the ceiling, so tomorrow's goal never asks for more than you will probably manage. Read in memory on the server, kept only on this device. ", h("a", { href: "./export.html", target: "_blank" }, "How do I export?")),
    h("h3", {}, "Steps"),
    h("p", { class: "meta" }, "Google Fit's Daily activity metrics.csv, a Fitbit / Pixel Watch export (all the steps-*.json files), or any CSV with date and steps columns. Days under 500 steps count as the phone or watch not carried, never as a miss."),
    h("div", { class: "row file" },
      stepsFile,
      h("button", { class: "btn", onclick: async () => {
        const report = { kind: "steps" as const, files: names(stepsFile) };
        try {
          show("Reading…");
          const texts = await readFiles(stepsFile);
          if (!texts.length) return show("Choose a file first.");
          const lines: string[] = [];
          for (const t of texts) lines.push(await c.importStepsFile(t));
          show(lines.join(" "), "good", report);
        } catch (e) {
          show(e instanceof Error ? e.message : "Could not read that file", "bad", report);
        }
      } }, "Import steps"),
    ),
    h("h3", {}, "Workouts (optional)"),
    h("p", { class: "meta" }, "A Hevy CSV export. Only the main lifts, a few dumbbell lifts and bodyweight moves are used; warm-ups, empty sets and assisted or weighted bodyweight variants are skipped."),
    h("div", { class: "row file" },
      hevyFile,
      h("button", { class: "btn", onclick: async () => {
        const report = { kind: "workouts" as const, files: names(hevyFile) };
        try {
          show("Reading…");
          const [text] = await readFiles(hevyFile);
          if (!text) return show("Choose a file first.");
          show(await c.importHevyFile(text), "good", report);
        } catch (e) {
          show(e instanceof Error ? e.message : "Could not read that file", "bad", report);
        }
      } }, "Import workouts"),
    ),
    out,
    help,
  );
  return card;
}

// All the app's actions live here; screens only read state and call these.
import * as api from "./api";
import { Arena } from "./art/arena";
import persona from "./demo/persona.json";
import { CREATURES, creatureFor } from "./game/creatures";
import { HISTORY_DAYS, addDays, dayOf, emptyDay, historyFor, settle, todayISO, totalXp, upsertDay, withOutcome } from "./game/day";
import { cellId, haversineM, isNewCell } from "./game/explore";
import { stageOf } from "./game/rules";
import { getPosition } from "./geo";
import { findPlaces } from "./places";
import type { Place } from "./types";
import { loadState, newState, savedMode, Store } from "./state";
import type { DayRecord, ExerciseGoal, ExerciseInfo, Habitat, SetLog, State } from "./types";

export type Tab = "today" | "talk" | "places" | "dex" | "data";
export type Say = { text: string; kind: "info" | "good" | "bad" } | null;

const PERSONA = persona.days as { date: string; steps: number | null }[];
const WELCOME_KEY = "slowstart.welcomed";
const NEAR_M = 400; // how close you must be to a place to log from it
// The demo walks through every kind of place and time of day, so a first-time visitor sees them all.
const DEMO_HABITATS: Habitat[] = ["park", "water", "street", "park", "gym", "water", "street"];
const DEMO_HOURS = [10, 18, 21, 7, 13, 19, 22];
const FORMAT_LABEL: Record<string, string> = {
  google_fit_csv: "a Google Fit daily summary",
  fitbit_takeout_json: "a Fitbit export",
  fitabase_csv: "a Fitabase CSV",
  csv: "a date and steps CSV",
};

export class Controller {
  readonly store: Store;
  readonly arena = new Arena();
  tab: Tab = "today";
  busy = "";
  say: Say = null;
  /** The last import's message on the Data tab; kept here because an import redraws the screen. */
  importNote: { text: string; kind: "info" | "good" | "bad"; report?: { kind: "steps" | "workouts"; files: string[] } } | null = null;
  health: api.Health | null = null;
  catalog: Record<string, ExerciseInfo> | null = null;
  targets = new Map<string, ExerciseGoal>();
  places: Place[] | null = null;
  selectedExercise = "push_up";
  lastCheckin: api.Checkin | null = null;
  draft = ""; // an unsent check-in, kept across re-renders
  open = new Set<string>(); // which <details> are open, kept across re-renders
  placesActivity: "walk" | "train" = "walk";
  welcome = false;
  onChange: () => void = () => {};

  constructor() {
    this.store = new Store(loadState(savedMode()));
    try {
      this.welcome = localStorage.getItem(WELCOME_KEY) !== "1";
    } catch {
      this.welcome = true;
    }
    this.store.subscribe(() => this.onChange());
  }

  get s(): State {
    return this.store.get();
  }

  get isDemo(): boolean {
    return this.s.mode === "demo";
  }

  get date(): string {
    if (!this.isDemo) return todayISO();
    return PERSONA[Math.min(this.s.demoIndex, PERSONA.length - 1)].date;
  }

  get demoOver(): boolean {
    return this.isDemo && this.s.demoIndex >= PERSONA.length;
  }

  get demoLength(): number {
    return PERSONA.length;
  }

  get day(): DayRecord {
    return dayOf(this.s, this.date) ?? emptyDay(this.date);
  }

  get xp(): number {
    return totalXp(this.s.days);
  }

  notify(text: string | null, kind: "info" | "good" | "bad" = "info"): void {
    this.say = text ? { text, kind } : null;
    this.onChange();
  }

  private mark(creatureId: string): void {
    this.store.set((s) => (s.seen.includes(creatureId) ? s : { ...s, seen: [...s.seen, creatureId] }));
  }

  dismissWelcome(): void {
    try {
      localStorage.setItem(WELCOME_KEY, "1");
    } catch {
      /* nothing to do */
    }
    this.welcome = false;
    this.onChange();
  }

  /** Called once at start, and again whenever the mode or the date changes. */
  async boot(): Promise<void> {
    this.store.set((s) => settle(s, this.date, this.isDemo ? DEMO_HABITATS[s.demoIndex % DEMO_HABITATS.length] : "park"));
    void api.health().then((h) => { this.health = h; this.onChange(); }).catch(() => {});
    void api.exercises().then((c) => { this.catalog = c; this.onChange(); }).catch(() => {});
    await this.ensureGoal();
  }

  /** R1.1: ask the backend once per day; the goal then holds for the whole day. */
  async ensureGoal(): Promise<void> {
    const date = this.date;
    const s0 = this.s;
    const cached = s0.goalCache?.date === date ? s0.goalCache.goal : null;
    let day = dayOf(s0, date) ?? emptyDay(date);
    if (cached && day.goal !== null) return;
    this.busy = "goal";
    this.onChange();
    const goal = cached ?? (await api.stepGoal(historyFor(s0, date), date, s0.days));
    day = dayOf(this.s, date) ?? emptyDay(date);
    this.store.set((s) => ({
      ...upsertDay(s, withOutcome({ ...day, goal: goal.goal, window: goal.window }, date)),
      goalCache: { date, goal },
    }));
    this.busy = "";
    this.mark(this.day.creature);
    this.onChange();
  }

  private patchDay(patch: Partial<DayRecord>): void {
    const date = this.date;
    this.store.set((s) => {
      const cur = dayOf(s, date) ?? emptyDay(date);
      return upsertDay(s, withOutcome({ ...cur, ...patch }, date));
    });
  }

  logSteps(steps: number): void {
    const before = this.day;
    const clean = Math.max(0, Math.min(100_000, Math.round(steps)));
    this.patchDay({ steps: clean });
    const after = this.day;
    if (before.outcome !== "win" && after.outcome === "win") {
      this.notify(`${CREATURES[after.creature].name} was caught. Slumbrock stirs.`, "good");
    } else {
      this.onChange();
    }
  }

  setExcused(excused: boolean): void {
    this.patchDay({ excused });
  }

  // ----- the demo -----

  playDemoDay(): void {
    const row = PERSONA[Math.min(this.s.demoIndex, PERSONA.length - 1)];
    if (row.steps === null) {
      this.setExcused(true);
      this.notify("The tracker was not worn this day. A rest day, no penalty.", "info");
    } else {
      this.logSteps(row.steps);
    }
  }

  async nextDemoDay(): Promise<void> {
    const next = PERSONA[this.s.demoIndex + 1]?.date ?? addDays(this.date, 1);
    const habitat = DEMO_HABITATS[(this.s.demoIndex + 1) % DEMO_HABITATS.length];
    this.store.set((s) => ({ ...settle(s, next, habitat), demoIndex: s.demoIndex + 1 }));
    if (this.demoOver) return this.onChange();
    this.notify(null);
    await this.boot();
  }

  async restartDemo(): Promise<void> {
    this.store.replace({ ...newState("demo", "Demo person"), mode: "demo" });
    this.notify(null);
    await this.boot();
  }

  async switchMode(mode: State["mode"]): Promise<void> {
    // Live play keeps its save. The demo always starts from day one, so every visitor sees the whole story.
    this.store.replace(mode === "demo" ? newState("demo", "Demo person") : loadState(mode));
    this.tab = "today";
    this.targets.clear();
    this.notify(null);
    await this.boot();
  }

  // ----- training -----

  async loadTarget(exercise: string): Promise<void> {
    if (this.targets.has(exercise)) return;
    try {
      this.targets.set(exercise, await api.exerciseGoal(exercise, this.s.workouts));
    } catch (e) {
      this.notify(e instanceof Error ? e.message : "Could not get a target", "bad");
    }
    this.onChange();
  }

  logWorkout(exercise: string, sets: SetLog[]): void {
    const date = this.date;
    this.store.set((s) => ({
      ...s,
      workouts: [...s.workouts.filter((w) => !(w.date === date && w.exercise === exercise)), { date, exercise, sets }],
    }));
    this.targets.delete(exercise);
    this.patchDay({ trained: true });
    this.notify("Logged. Slumbrock flexes. Training is a bonus, never a requirement.", "good");
    void this.loadTarget(exercise);
  }

  // ----- check-in -----

  async sendCheckin(text: string): Promise<void> {
    this.busy = "checkin";
    this.onChange();
    try {
      const r = await api.checkin(text);
      this.lastCheckin = r;
      const date = this.date;
      this.store.set((s) => ({ ...s, checkin: { date, line: [r.line, r.aside].filter(Boolean).join(" ") } }));
      if (r.excused) this.setExcused(true);
    } catch (e) {
      this.notify(e instanceof Error ? e.message : "Slumbrock could not hear you", "bad");
    } finally {
      this.busy = "";
      this.onChange();
    }
  }

  // ----- places and exploring -----

  async searchPlaces(activity: "walk" | "train"): Promise<void> {
    this.placesActivity = activity;
    this.busy = "places";
    this.places = null;
    this.onChange();
    try {
      const here = await getPosition();
      this.places = await findPlaces(here.lat, here.lon, activity);
      if (this.places.length === 0) this.notify("No named places found nearby. Try the other kind.", "info");
    } catch (e) {
      this.notify(e instanceof Error ? e.message : "Could not look for places", "bad");
    } finally {
      this.busy = "";
      this.onChange();
    }
  }

  async exploreAt(place: Place): Promise<void> {
    let here;
    try {
      here = await getPosition();
    } catch (e) {
      return this.notify(e instanceof Error ? e.message : "Could not find your location", "bad");
    }
    const away = haversineM(here.lat, here.lon, place.lat, place.lon);
    if (away > NEAR_M) {
      return this.notify(`You are about ${Math.round(away / 10) * 10} m from ${place.name}. Get a little closer first.`, "info");
    }
    const cell = cellId(here.lat, here.lon);
    const fresh = isNewCell(this.s.explored, cell);
    const date = this.date;
    const creature = creatureFor(date, fresh ? "rare" : place.habitat, cell);
    if (fresh) this.store.set((s) => ({ ...s, explored: [...s.explored, cell] }));
    this.patchDay({ explored: this.day.explored || fresh, creature });
    this.mark(creature);
    this.notify(
      fresh ? `New ground! A ${CREATURES[creature].name} followed you from ${place.name}.` : `You have been here before. A ${CREATURES[creature].name} is nearby.`,
      fresh ? "good" : "info",
    );
  }

  // ----- data -----

  async importStepsFile(text: string): Promise<string> {
    const imp = await api.importSteps(text);
    const today = this.date;
    this.store.set((s) => {
      let next = s;
      for (const d of imp.days) {
        if (d.date >= today) continue;
        const cur = dayOf(next, d.date) ?? emptyDay(d.date);
        next = upsertDay(next, { ...cur, steps: cur.steps ?? d.steps });
      }
      const noGoalYet = dayOf(next, today)?.steps === null;
      return { ...next, goalCache: noGoalYet ? null : next.goalCache };
    });
    if (dayOf(this.s, today)?.steps === null) this.patchDay({ goal: null, window: null });
    await this.ensureGoal();
    // The file's own today is steps so far: log them, and Slumbrock attacks like any logged steps.
    // Without today in the file, the history still gets a stomp, but no damage.
    const todayRow = imp.days.find((d) => d.date === today && d.steps !== null);
    const sofar = this.day.steps ?? 0;
    const past = imp.days.filter((d) => d.date < today).length;
    if (!this.isDemo && todayRow?.steps && todayRow.steps > sofar) {
      this.logSteps(todayRow.steps);
    } else if (past > 0) {
      this.arena.cheer(`${past.toLocaleString("en-US")} DAYS IMPORTED`, "Your goal now starts from them");
    }
    const notes = imp.warnings.map((w) => ` ${w}.`).join("");
    const kept = imp.days.length > HISTORY_DAYS ? ` Goals use the latest ${HISTORY_DAYS} days.` : "";
    const logged = todayRow?.steps && todayRow.steps > sofar ? ` Today so far: ${todayRow.steps.toLocaleString("en")} steps, logged from the file.` : "";
    return `Read ${imp.days.length.toLocaleString("en")} days as ${FORMAT_LABEL[imp.format] ?? imp.format} (${imp.first} to ${imp.last}).${notes}${kept}${logged}`;
  }

  async importHevyFile(text: string): Promise<string> {
    const imp = await api.importHevy(text);
    const keys = new Set(imp.sessions.map((x) => `${x.date}|${x.exercise}`));
    this.store.set((s) => ({
      ...s,
      workouts: [...s.workouts.filter((w) => !keys.has(`${w.date}|${w.exercise}`)), ...imp.sessions].sort((a, b) => a.date.localeCompare(b.date)),
    }));
    this.targets.clear();
    const names = Object.entries(imp.exercises).slice(0, 4).map(([k, n]) => `${this.catalog?.[k]?.label ?? k} (${n})`).join(", ");
    const left = Object.values(imp.unsupported).reduce((a, b) => a + b, 0);
    return `Read ${imp.sessions.length} sessions: ${names || "none supported"}.${left ? ` ${left} set(s) of other exercises were left out.` : ""}`;
  }

  exportJson(): string {
    return JSON.stringify(this.s, null, 1);
  }

  wipe(): void {
    this.store.replace(newState(this.s.mode, this.s.name));
    this.targets.clear();
    this.places = null;
    this.notify("Everything on this device was deleted.", "info");
    void this.boot();
  }

  // ----- what the arena shows -----

  syncArena(): void {
    const day = this.day;
    const c = CREATURES[day.creature] ?? CREATURES.mossling;
    const goal = day.goal ?? 1;
    const left = Math.max(0, goal - (day.steps ?? 0));
    const earlier = this.s.days
      .filter((d) => d.date < this.date && d.outcome === "win")
      .sort((a, b) => b.date.localeCompare(a.date))
      .map((d) => CREATURES[d.creature]?.sprite)
      .filter((x): x is string => Boolean(x));
    const caught = day.goal !== null && day.outcome === "win";
    const companions = [...new Set([...(caught ? [c.sprite] : []), ...earlier])];
    this.arena.update({
      day: `${this.s.mode}|${day.date}`,
      stage: stageOf(this.xp),
      creature: c.sprite,
      creatureName: c.name,
      habitat: c.habitat,
      hp: day.goal === null ? 1 : left / goal,
      hpSteps: day.goal === null ? 1 : left,
      goal: day.goal ?? 0,
      hour: this.isDemo ? DEMO_HOURS[this.s.demoIndex % DEMO_HOURS.length] : new Date().getHours(),
      caught,
      companions,
    });
  }
}

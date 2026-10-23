// All the app's actions live here; screens only read state and call these.
import * as api from "./api";
import { Arena } from "./art/arena";
import persona from "./demo/persona.json";
import { CREATURES, creatureFor } from "./game/creatures";
import { addDays, dayOf, emptyDay, historyFor, settle, todayISO, totalXp, upsertDay, withOutcome } from "./game/day";
import { cellId, haversineM, isNewCell } from "./game/explore";
import { stageOf } from "./game/rules";
import { getPosition } from "./geo";
import { findPlaces } from "./places";
import type { Place } from "./types";
import { loadState, newState, savedMode, Store } from "./state";
import type { DayRecord, ExerciseGoal, ExerciseInfo, SetLog, State } from "./types";

export type Tab = "today" | "talk" | "places" | "dex" | "data";
export type Say = { text: string; kind: "info" | "good" | "bad" } | null;

const PERSONA = persona.days as { date: string; steps: number | null }[];
const WELCOME_KEY = "slowstart.welcomed";
const NEAR_M = 400; // how close you must be to a place to log from it

export class Controller {
  readonly store: Store;
  readonly arena = new Arena();
  tab: Tab = "today";
  busy = "";
  say: Say = null;
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
    this.store.set((s) => settle(s, this.date));
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
    this.store.set((s) => ({ ...settle(s, next), demoIndex: s.demoIndex + 1 }));
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
    this.store.replace(loadState(mode));
    if (mode === "demo" && this.s.days.length === 0) this.store.set((s) => ({ ...s, name: "Demo person" }));
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
      this.store.set((s) => ({ ...s, checkin: { date, line: r.line } }));
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
    const note = imp.not_worn ? ` ${imp.not_worn} day(s) with 0 steps were treated as "tracker not worn".` : "";
    return `Read ${imp.days.length} days (${imp.first} to ${imp.last}).${note}`;
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
    this.arena.update({
      stage: stageOf(this.xp),
      creature: c.sprite,
      habitat: c.habitat,
      hp: day.goal === null ? 1 : Math.max(0, goal - (day.steps ?? 0)) / goal,
      hour: this.isDemo ? 10 : new Date().getHours(),
    });
  }
}

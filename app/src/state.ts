// One store, saved on the device (R7.3). Live play and the demo keep separate saves.
import type { State } from "./types";

const MODE_KEY = "slowstart.mode";
const saveKey = (mode: State["mode"]) => `slowstart.${mode}.v1`;

export function newState(mode: State["mode"], name = "you"): State {
  return {
    v: 1,
    mode,
    name,
    days: [],
    workouts: [],
    seen: [],
    explored: [],
    goalCache: null,
    demoIndex: 0,
    checkin: null,
  };
}

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null; // private windows and blocked storage: the app still runs, it just forgets
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* nothing to do */
  }
}

export function savedMode(): State["mode"] {
  return read(MODE_KEY) === "demo" ? "demo" : "live";
}

export function loadState(mode: State["mode"]): State {
  const raw = read(saveKey(mode));
  if (!raw) return newState(mode);
  try {
    const parsed = JSON.parse(raw) as State;
    return parsed.v === 1 ? { ...newState(mode), ...parsed, mode } : newState(mode);
  } catch {
    return newState(mode);
  }
}

export function saveState(state: State): void {
  write(saveKey(state.mode), JSON.stringify(state));
  write(MODE_KEY, state.mode);
}

export function clearState(mode: State["mode"]): void {
  try {
    localStorage.removeItem(saveKey(mode));
  } catch {
    /* nothing to do */
  }
}

type Listener = (s: State) => void;

export class Store {
  private state: State;
  private listeners = new Set<Listener>();

  constructor(initial: State) {
    this.state = initial;
  }

  get(): State {
    return this.state;
  }

  set(next: State | ((s: State) => State)): void {
    this.state = typeof next === "function" ? next(this.state) : next;
    saveState(this.state);
    this.listeners.forEach((l) => l(this.state));
  }

  /** Swap the whole save, e.g. when switching between live play and the demo. */
  replace(next: State): void {
    this.set(next);
  }

  subscribe(l: Listener): () => void {
    this.listeners.add(l);
    return () => this.listeners.delete(l);
  }
}

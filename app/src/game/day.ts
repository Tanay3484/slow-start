// The day loop (R4): spawn, damage, win or miss, XP and stats. Pure functions over State.
import type { DayRecord, Habitat, State, WorkoutLog } from "../types";
import { creatureFor } from "./creatures";
import { dayXp } from "./rules";

export function todayISO(now: Date = new Date()): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function addDays(iso: string, n: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const t = new Date(Date.UTC(y, m - 1, d + n));
  return t.toISOString().slice(0, 10);
}

export function hpLeft(goal: number, steps: number | null): number {
  return Math.max(0, goal - (steps ?? 0));
}

export function emptyDay(date: string, habitat: Habitat = "park"): DayRecord {
  return {
    date,
    steps: null,
    goal: null,
    window: null,
    excused: false,
    trained: false,
    explored: false,
    creature: creatureFor(date, habitat),
    outcome: "open",
  };
}

/** R4.2, R4.5: won as soon as the goal is reached; a miss only once the day is over. An excused day
 *  and a day with nothing logged are rest days, never misses. */
export function outcomeOf(day: DayRecord, today: string): DayRecord["outcome"] {
  if (day.goal === null) return "rest";
  if (day.steps !== null && day.steps >= day.goal) return "win";
  if (day.excused) return "rest";
  if (day.date < today) return day.steps === null ? "rest" : "miss";
  return "open";
}

export function withOutcome(day: DayRecord, today: string): DayRecord {
  const outcome = outcomeOf(day, today);
  return outcome === day.outcome ? day : { ...day, outcome };
}

/** XP is derived from the day records every time, so changing the rule never leaves it out of step. */
export function xpOfDay(day: DayRecord): number {
  if (day.goal === null) return 0; // history imported from before the app was used earns nothing
  return dayXp({ goal: day.goal, steps: day.steps, trained: day.trained, explored: day.explored });
}

export function totalXp(days: readonly DayRecord[]): number {
  return days.reduce((sum, d) => sum + xpOfDay(d), 0);
}

export interface Stats {
  speed: number; // 0.5 to 1: steps
  power: number; // 0.5 to 1: training
  wins: number;
  trainings: number;
}

/** R4.6: both start at half, like Slow Start's namesake, and reach full over time. */
export function statsOf(days: readonly DayRecord[], workouts: readonly WorkoutLog[]): Stats {
  const wins = days.filter((d) => d.goal !== null && d.outcome === "win").length;
  const trainDays = new Set(workouts.map((w) => w.date)).size;
  return {
    speed: 0.5 + 0.5 * Math.min(1, wins / 21),
    power: 0.5 + 0.5 * Math.min(1, trainDays / 12),
    wins,
    trainings: trainDays,
  };
}

/** Days before `today` as the backend wants them. Imported days have no goal; they still feed the cap. */
export function historyFor(state: State, today: string) {
  return state.days
    .filter((d) => d.date < today)
    .map((d) => ({ date: d.date, steps: d.steps, goal: d.goal, excused: d.excused }));
}

export function dayOf(state: State, date: string): DayRecord | undefined {
  return state.days.find((d) => d.date === date);
}

/** Make sure `date` has a record and every earlier day has its final outcome. */
export function settle(state: State, today: string): State {
  let days = state.days.map((d) => withOutcome(d, today));
  if (!days.some((d) => d.date === today)) days = [...days, emptyDay(today)];
  days = days.sort((a, b) => a.date.localeCompare(b.date));
  return { ...state, days };
}

export function upsertDay(state: State, day: DayRecord): State {
  const rest = state.days.filter((d) => d.date !== day.date);
  return { ...state, days: [...rest, day].sort((a, b) => a.date.localeCompare(b.date)) };
}

// The backend client (R7.4). Every call has a timeout, and the goal has an offline fallback, so the
// app still plays when the server is asleep or unreachable.
import type { DayRecord, ExerciseGoal, ExerciseInfo, Goal, SetLog, WorkoutLog } from "./types";

const BASE = ((import.meta.env.VITE_API_BASE as string | undefined) ?? "").replace(/\/$/, "");

export class ApiError extends Error {}

async function request<T>(path: string, init: RequestInit, timeoutMs: number): Promise<T> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const res = await fetch(`${BASE}${path}`, { ...init, signal: ctl.signal });
    if (!res.ok) {
      let detail = "";
      try {
        detail = ((await res.json()) as { detail?: string }).detail ?? "";
      } catch {
        /* no body */
      }
      throw new ApiError(detail || `HTTP ${res.status}`);
    }
    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError(e instanceof Error && e.name === "AbortError" ? "The server took too long" : "The server is out of reach");
  } finally {
    clearTimeout(timer);
  }
}

function post<T>(path: string, body: unknown, timeoutMs = 60_000): Promise<T> {
  return request<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }, timeoutMs);
}

export interface Health {
  status: string;
  predictor: string;
  model: string;
  levels: Record<string, "locked" | "unlocked">;
}

export const health = () => request<Health>("/api/health", {}, 8_000);

/** 80% of the median of the last 14 days, or the starting goal: what the app uses with no server. */
export function offlineGoal(days: readonly Pick<DayRecord, "date" | "steps">[], today: string): Goal {
  const recent = days
    .filter((d) => d.steps !== null && d.date < today)
    .slice(-14)
    .map((d) => d.steps as number)
    .sort((a, b) => a - b);
  const median = recent.length ? recent[Math.floor(recent.length / 2)] : null;
  const goal = median === null ? 1500 : Math.min(20000, Math.max(1000, Math.round((0.8 * median) / 50) * 50));
  return {
    goal,
    window: goal,
    threshold: null,
    phase: median === null ? "slow_start" : "cruising",
    cap: { value: null, p30: null, p50: null, source: "none" },
    source: "offline",
    note: "Offline: the server could not be reached, so this goal comes from your recent median.",
  };
}

export async function stepGoal(history: unknown[], today: string, days: readonly DayRecord[]): Promise<Goal> {
  try {
    return await post<Goal>("/api/goal/steps", { today, history });
  } catch {
    return offlineGoal(days, today);
  }
}

export const exerciseGoal = (exercise: string, sessions: WorkoutLog[]) =>
  post<ExerciseGoal>("/api/goal/exercise", { exercise, sessions: sessions.filter((s) => s.exercise === exercise) }, 20_000);

export const exercises = () => request<Record<string, ExerciseInfo>>("/api/exercises", {}, 8_000);

export interface Checkin {
  energy: "low" | "ok" | "high";
  body: string[];
  excused: boolean;
  line: string;
  /** Chosen by code from a curated list, never by the model. */
  tip: string;
  /** Now and then, a rock joke. */
  aside: string;
  source: "gemma" | "template";
}

export const checkin = (text: string) => post<Checkin>("/api/checkin", { text }, 90_000);

export interface ImportedSteps {
  days: { date: string; steps: number | null }[];
  format: string;
  not_worn: number;
  first: string | null;
  last: string | null;
  warnings: string[];
}

export interface ImportedWorkouts {
  sessions: { date: string; exercise: string; sets: SetLog[] }[];
  exercises: Record<string, number>;
  unsupported: Record<string, number>;
  skipped_rows: number;
  first: string | null;
  last: string | null;
  warnings: string[];
}

export const importSteps = (text: string) => post<ImportedSteps>("/api/import/steps", { text }, 120_000);
export const importHevy = (text: string) => post<ImportedWorkouts>("/api/import/hevy", { text }, 120_000);

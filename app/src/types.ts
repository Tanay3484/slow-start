// Shapes shared by the app. The API shapes mirror backend/slowstart/models.py.

export type Phase = "slow_start" | "cruising" | "recovering";
export type Outcome = "open" | "win" | "miss" | "rest";
export type Habitat = "park" | "water" | "street" | "gym" | "rare";

export interface Cap {
  value: number | null;
  p30: number | null;
  p50: number | null;
  source: "tabpfn" | "median" | "none";
}

export interface Goal {
  goal: number;
  window: number;
  threshold: number | null;
  phase: Phase;
  cap: Cap;
  /** "offline" is only ever set by the app, when the backend could not be reached. */
  source: "controller" | "fallback" | "offline";
  note: string;
}

export interface SetLog {
  weight_kg: number | null;
  reps: number;
}

export interface WorkoutLog {
  date: string;
  exercise: string;
  sets: SetLog[];
}

export interface Target {
  sets: number;
  reps: number;
  weight_kg: number | null;
}

export interface ExerciseGoal {
  exercise: string;
  label: string;
  target: Target;
  source: "controller" | "fallback";
  note: string;
}

export interface ExerciseInfo {
  label: string;
  kind: "barbell" | "dumbbell" | "bodyweight";
  sets: number;
  reps: number;
  increment_kg: number | null;
  starter_weight_kg: number | null;
}

/** One day of play. `steps` is null until something is logged. */
export interface DayRecord {
  date: string; // YYYY-MM-DD
  steps: number | null;
  goal: number | null;
  window: number | null;
  excused: boolean;
  trained: boolean;
  explored: boolean;
  creature: string;
  outcome: Outcome;
}

export interface State {
  v: 1;
  mode: "live" | "demo";
  name: string;
  days: DayRecord[];
  workouts: WorkoutLog[];
  seen: string[];
  explored: string[]; // place cells the person has logged from
  goalCache: { date: string; goal: Goal } | null;
  demoIndex: number; // demo only: how many persona days have been played
  checkin: { date: string; line: string } | null;
}

export interface Place {
  id: string;
  name: string;
  kind: string;
  habitat: Habitat;
  lat: number;
  lon: number;
  distanceM: number;
  walkMin: number;
}

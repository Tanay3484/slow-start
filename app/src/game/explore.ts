// The explore bonus (R6.3): the first time you log from a place cell you have never logged from.
// A cell is about 550 m on a side. Only the cell id is stored, never the exact position.

const CELL_DEG = 0.005;

export function cellId(lat: number, lon: number): string {
  const q = (v: number) => (Math.round(v / CELL_DEG) * CELL_DEG).toFixed(3);
  return `${q(lat)},${q(lon)}`;
}

export function isNewCell(explored: readonly string[], cell: string): boolean {
  return !explored.includes(cell);
}

export function haversineM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const p = Math.PI / 180;
  const a =
    Math.sin(((lat2 - lat1) * p) / 2) ** 2 +
    Math.cos(lat1 * p) * Math.cos(lat2 * p) * Math.sin(((lon2 - lon1) * p) / 2) ** 2;
  return 12_742_000 * Math.asin(Math.sqrt(a));
}

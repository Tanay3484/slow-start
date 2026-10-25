// A tiny element builder. Text goes in through textContent, so nothing from the network or from
// OpenStreetMap place names can ever be parsed as HTML.
type Child = Node | string | number | null | false | undefined;
type Attrs = Record<string, string | number | boolean | EventListener | undefined>;

export function h<K extends keyof HTMLElementTagNameMap>(tag: K, attrs: Attrs = {}, ...children: Child[]): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === false) continue;
    if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2).toLowerCase(), value as EventListener);
    else if (key === "class") el.className = String(value);
    else if (value === true) el.setAttribute(key, "");
    else el.setAttribute(key, String(value));
  }
  for (const c of children.flat()) {
    if (c === null || c === false || c === undefined) continue;
    el.append(typeof c === "object" ? c : document.createTextNode(String(c)));
  }
  return el;
}

export const fmt = (n: number) => n.toLocaleString("en-US");

/** A tiny pixel icon from an 8x8 bitmap ('#' filled), drawn in the current text colour. */
export function pixelIcon(rows: string[]): SVGSVGElement {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 8 8");
  svg.setAttribute("class", "ico");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("shape-rendering", "crispEdges");
  rows.forEach((row, y) =>
    [...row].forEach((ch, x) => {
      if (ch !== "#") return;
      const r = document.createElementNS(ns, "rect");
      r.setAttribute("x", String(x));
      r.setAttribute("y", String(y));
      r.setAttribute("width", "1");
      r.setAttribute("height", "1");
      r.setAttribute("fill", "currentColor");
      svg.append(r);
    }),
  );
  return svg;
}

export const ICONS: Record<string, string[]> = {
  today: ["...##...", "..####..", "..####..", "...###..", ".##.....", "####....", "####....", ".##....."],
  talk: [".######.", "########", "##.##.##", "########", ".######.", "..##....", ".#......", "........"],
  places: ["..####..", ".##..##.", ".##..##.", "..####..", "...##...", "...##...", "....#...", "........"],
  dex: ["###.###.", "#.#.#.#.", "###.###.", "........", "###.###.", "#.#.#.#.", "###.###.", "........"],
  data: ["#######.", "#.###.##", "#.###..#", "#......#", "#.####.#", "#.####.#", "#######.", "........"],
};

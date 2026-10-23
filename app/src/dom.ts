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

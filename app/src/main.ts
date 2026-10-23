import "@fontsource/press-start-2p/index.css";
import "./style.css";
import { Controller, type Tab } from "./controller";
import { h } from "./dom";
import { homeScreen } from "./screens/home";
import { dataScreen, dexScreen, placesScreen, talkScreen, welcomeOverlay } from "./screens/other";

const c = new Controller();
const root = document.getElementById("app")!;

const TABS: { id: Tab; label: string }[] = [
  { id: "today", label: "Today" },
  { id: "talk", label: "Talk" },
  { id: "places", label: "Places" },
  { id: "dex", label: "Dex" },
  { id: "data", label: "Data" },
];

function screen() {
  switch (c.tab) {
    case "talk": return talkScreen(c);
    case "places": return placesScreen(c);
    case "dex": return dexScreen(c);
    case "data": return dataScreen(c);
    default: return homeScreen(c);
  }
}

let queued = false;
function render(): void {
  if (queued) return;
  queued = true;
  queueMicrotask(() => {
    queued = false;
    const scroll = window.scrollY;
    const header = h("header", { class: "top" },
      h("h1", {}, "Slow Start"),
      c.isDemo ? h("span", { class: "chip warn" }, "Demo") : null,
    );
    const nav = h("nav", { class: "tabs", "aria-label": "Sections" },
      ...TABS.map((t) =>
        h("button", { class: t.id === c.tab ? "on" : "", "aria-current": t.id === c.tab ? "page" : undefined, onclick: () => { c.tab = t.id; c.say = null; render(); window.scrollTo(0, 0); } }, t.label),
      ),
    );
    const parts: Node[] = [header, h("main", {}, screen()), nav];
    if (c.welcome) parts.push(welcomeOverlay(c));
    root.replaceChildren(...parts);
    window.scrollTo(0, scroll);
  });
}

c.onChange = render;
c.arena.start();
render();
void c.boot();

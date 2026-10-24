import "@fontsource/press-start-2p/index.css";
import "./style.css";
import { Controller, type Tab } from "./controller";
import { h, ICONS, pixelIcon } from "./dom";
import { homeScreen, stagePanel } from "./screens/home";
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
    const nav = h("nav", { class: "tabs", "aria-label": "Sections" },
      ...TABS.map((t) =>
        h("button", { class: t.id === c.tab ? "on" : "", "aria-current": t.id === c.tab ? "page" : undefined, onclick: () => { c.tab = t.id; c.say = null; render(); window.scrollTo(0, 0); } },
          pixelIcon(ICONS[t.id]), h("span", {}, t.label)),
      ),
    );
    const header = h("header", { class: "top" },
      h("a", { class: "brand", href: "./", title: "About Slow Start" }, "Slow Start"),
      nav,
      c.isDemo ? h("span", { class: "chip warn mode" }, "Demo") : h("span", { class: "chip mode" }, "Live"),
    );
    const layout = h("div", { class: `layout tab-${c.tab}` }, stagePanel(c), h("main", { class: "panel" }, screen()));
    const parts: Node[] = [header, layout];
    if (c.welcome) parts.push(welcomeOverlay(c));
    root.replaceChildren(...parts);
    window.scrollTo(0, scroll);
  });
}

c.onChange = render;
c.arena.start();
render();

// The landing page links here with ?demo=1 so a visitor lands straight in the demo.
const wantsDemo = new URLSearchParams(location.search).get("demo") === "1";
if (wantsDemo) {
  c.dismissWelcome();
  history.replaceState(null, "", location.pathname);
  void c.switchMode("demo");
} else {
  void c.boot();
}

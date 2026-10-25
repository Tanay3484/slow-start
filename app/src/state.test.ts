import { beforeEach, describe, expect, it } from "vitest";
import { loadState, newState, saveState, savedMode } from "./state";

// A tiny in-memory localStorage for node.
class MemoryStorage {
  private m = new Map<string, string>();
  getItem(k: string) {
    return this.m.has(k) ? this.m.get(k)! : null;
  }
  setItem(k: string, v: string) {
    this.m.set(k, v);
  }
  removeItem(k: string) {
    this.m.delete(k);
  }
  keys() {
    return [...this.m.keys()];
  }
}

let store: MemoryStorage;
beforeEach(() => {
  store = new MemoryStorage();
  (globalThis as unknown as { localStorage: MemoryStorage }).localStorage = store;
});

describe("saves", () => {
  it("keeps live play between loads", () => {
    saveState({ ...newState("live"), seen: ["mossling"] });
    expect(loadState("live").seen).toEqual(["mossling"]);
  });

  it("never keeps the demo: every load starts at day one", () => {
    saveState({ ...newState("demo"), seen: ["mossling"], demoIndex: 7 });
    const demo = loadState("demo");
    expect(demo.seen).toEqual([]);
    expect(demo.demoIndex).toBe(0);
  });

  it("drops a demo save left by an older build", () => {
    store.setItem("slowstart.demo.v1", JSON.stringify({ ...newState("demo"), seen: ["starpebble"], demoIndex: 12 }));
    expect(loadState("demo").seen).toEqual([]);
    expect(store.keys()).not.toContain("slowstart.demo.v1");
  });
});

describe("modes", () => {
  it("opening the game after watching the demo is live play, never the demo", () => {
    saveState({ ...newState("demo", "Demo person"), demoIndex: 12 });
    expect(savedMode()).toBe("live");
    expect(store.keys()).not.toContain("slowstart.demo.v1");
  });

  it("clears the mode an older build remembered", () => {
    store.setItem("slowstart.mode", "demo");
    loadState("live");
    expect(store.keys()).not.toContain("slowstart.mode");
    expect(savedMode()).toBe("live");
  });
});

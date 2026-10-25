import { resolve } from "node:path";
import { defineConfig } from "vite";

// Four pages: the landing site (index.html), the game (play.html), the field guide (guide.html) and the
// export guide (export.html). In dev, /api goes to the Python backend on :8000. In production the backend
// serves this build from the same origin.
export default defineConfig({
  base: "./",
  server: { proxy: { "/api": "http://localhost:8000" } },
  build: {
    target: "es2022",
    sourcemap: false,
    rollupOptions: {
      input: {
        index: resolve(__dirname, "index.html"),
        play: resolve(__dirname, "play.html"),
        guide: resolve(__dirname, "guide.html"),
        export: resolve(__dirname, "export.html"),
      },
    },
  },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});

import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "dev.tanay.slowstart",
  appName: "Slow Start",
  webDir: "dist",
  server: { androidScheme: "https" },
  backgroundColor: "#1a1c2c",
};

export default config;

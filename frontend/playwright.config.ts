import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/e2e",
  use: {
    baseURL: process.env.UI_URL || "http://localhost:3010",
    headless: true,
  },
  workers: 1,
  retries: 0,
});

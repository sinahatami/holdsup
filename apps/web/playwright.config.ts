import { defineConfig, devices } from "@playwright/test";

const port = 3100;
const apiPort = 3101;

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/warm-up.ts",
  fullyParallel: true,
  reporter: process.env.CI ? "github" : "list",
  use: { baseURL: `http://localhost:${port}` },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // What the Next.js server reads from the API (a stored check). The browser's own
      // calls go to http://api.test and are mocked inside each test.
      command: "node e2e/mock-server.mjs",
      url: `http://127.0.0.1:${apiPort}/`,
      reuseExistingServer: !process.env.CI,
      env: { PORT: String(apiPort) },
    },
    {
      command: `pnpm exec next dev --port ${port}`,
      url: `http://localhost:${port}`,
      reuseExistingServer: !process.env.CI,
      env: {
        NEXT_PUBLIC_API_URL: "http://api.test",
        HOLDSUP_API_URL: `http://127.0.0.1:${apiPort}`,
      },
    },
  ],
});

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  reporter: [["list"], ["html", { open: "never", outputFolder: "../docs/playwright-report" }]],
  use: {
    baseURL: "http://127.0.0.1:4180",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 4180",
    url: "http://127.0.0.1:4180",
    reuseExistingServer: !process.env.CI,
    stdout: "pipe",
    stderr: "pipe",
  },
  projects: [
    {
      name: "desktop-chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } },
    },
    {
      name: "mobile-chromium",
      use: { ...devices["Pixel 5"] },
    },
  ],
});

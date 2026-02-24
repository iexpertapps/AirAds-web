import { defineConfig, devices } from '@playwright/test';

/**
 * AirAd Frontend — Playwright E2E Configuration
 *
 * Runs against the Vite dev server (or a pre-built preview).
 * Set PLAYWRIGHT_BASE_URL env var to override (e.g. staging URL).
 *
 * Usage:
 *   npx playwright test                    # all tests, headless
 *   npx playwright test --ui               # interactive UI mode
 *   npx playwright test e2e/auth.spec.ts   # single file
 */

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173';
const API_BASE_URL = process.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'playwright-results.json' }],
  ],
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: BASE_URL,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      VITE_API_BASE_URL: API_BASE_URL,
      VITE_E2E: 'true',
    },
  },
});

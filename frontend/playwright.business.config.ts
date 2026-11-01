import { defineConfig } from '@playwright/test';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

// Authenticated tests deliberately produce no trace, video, screenshot or HTML artifact.
if (!process.env.FACTORY_OPS_BROWSER_AUTH_FILE) {
  const directory = mkdtempSync(path.join(tmpdir(), 'factory-ops-business-'));
  process.env.FACTORY_OPS_BROWSER_AUTH_FILE = path.join(directory, 'credentials.json');
}
process.env.FACTORY_OPS_API_PROXY_TARGET = 'http://127.0.0.1:8011';
export default defineConfig({
  testDir: './business-tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  reporter: [['line']],
  outputDir: '.business-test-results',
  use: {
    baseURL: 'http://127.0.0.1:4174',
    viewport: { width: 1440, height: 1000 },
    trace: 'off',
    video: 'off',
    screenshot: 'off',
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH },
  },
  webServer: [
    {
      command: '../.venv/bin/python ../scripts/serve_business_test_api.py',
      url: 'http://127.0.0.1:8011/api/v1/health',
      timeout: 30000,
      reuseExistingServer: false,
    },
    {
      command:
        'npm run preview -- --host 127.0.0.1 --port 4174 --strictPort --outDir dist-business',
      url: 'http://127.0.0.1:4174',
      timeout: 30000,
      reuseExistingServer: false,
    },
  ],
});

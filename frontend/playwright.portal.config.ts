import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './portal-tests', workers: 1, retries: 0, forbidOnly: Boolean(process.env.CI),
  reporter: [['line']], outputDir: '.portal-test-results',
  use: { baseURL: 'http://127.0.0.1:5195', trace: 'off', video: 'off', screenshot: 'off' },
  webServer: [
    { command: '../.venv/bin/python ../scripts/serve_monitor_portal_test_api.py',
      env: { FACTORY_OPS_SYNTHETIC_PORTAL_TEST: '1' },
      url: 'http://127.0.0.1:8016/api/v1/health', reuseExistingServer: false, timeout: 30000 },
    { command: 'npx vite --config portal-test/vite.config.ts',
      url: 'http://127.0.0.1:5195', reuseExistingServer: false, timeout: 30000 },
  ],
});

import { defineConfig } from '@playwright/test';
import { mkdtempSync, chmodSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import path from 'node:path';

if (!process.env.FACTORY_OPS_IDENTITY_FIXTURE) {
  const directory = mkdtempSync(path.join(tmpdir(), 'factory-ops-identity-'));
  process.env.FACTORY_OPS_IDENTITY_FIXTURE = path.join(directory, 'credentials.json');
  process.env.FACTORY_OPS_TEST_TLS_KEY = path.join(directory, 'localhost.key');
  process.env.FACTORY_OPS_TEST_TLS_CERT = path.join(directory, 'localhost.crt');
  execFileSync(
    'openssl',
    [
      'req',
      '-x509',
      '-newkey',
      'rsa:2048',
      '-nodes',
      '-days',
      '1',
      '-keyout',
      process.env.FACTORY_OPS_TEST_TLS_KEY,
      '-out',
      process.env.FACTORY_OPS_TEST_TLS_CERT,
      '-subj',
      '/CN=localhost',
      '-addext',
      'subjectAltName=DNS:localhost',
    ],
    { stdio: 'ignore' },
  );
  chmodSync(process.env.FACTORY_OPS_TEST_TLS_KEY, 0o600);
}
process.env.FACTORY_OPS_API_PROXY_TARGET = 'http://127.0.0.1:8012';
export default defineConfig({
  testDir: './identity-tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  reporter: [['line']],
  outputDir: '.identity-test-results',
  use: {
    baseURL: 'https://localhost:4175',
    ignoreHTTPSErrors: true,
    viewport: { width: 1440, height: 1000 },
    trace: 'off',
    screenshot: 'off',
    video: 'off',
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH },
  },
  webServer: [
    {
      command: '../.venv/bin/python ../scripts/serve_identity_test_api.py',
      url: 'http://127.0.0.1:8012/api/v1/health',
      timeout: 30000,
      reuseExistingServer: false,
    },
    {
      command:
        'npm run preview -- --host localhost --port 4175 --strictPort --outDir dist-identity',
      url: 'https://localhost:4175',
      ignoreHTTPSErrors: true,
      timeout: 30000,
      reuseExistingServer: false,
    },
  ],
});

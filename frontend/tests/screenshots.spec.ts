import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

const screens = [
  ['pc-workbench', 'workbench', false],
  ['pc-assets', 'assets', false],
  ['pc-asset-detail', 'assets/preview', false],
  ['pc-work-order', 'work-orders/preview', false],
  ['pc-roles', 'settings?tab=roles', false],
  ['pc-integrations', 'settings?tab=integrations', false],
  ['mobile-home', 'm/home', true],
  ['mobile-tasks', 'm/tasks', true],
  ['mobile-scan', 'm/scan', true],
  ['mobile-messages', 'm/messages', true],
  ['mobile-me', 'm/me', true],
  ['mobile-asset-detail', 'm/assets/preview', true],
] as const;
for (const [name, route, mobile] of screens) {
  test(`交付截图：${name}`, async ({ page }, testInfo) => {
    await page.setViewportSize(
      mobile ? { width: 390, height: 844 } : { width: 1440, height: 1060 },
    );
    await page.goto('/#/' + route);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    const folder = process.env.CAPTURE_SHELL_SCREENSHOTS
      ? path.resolve('../docs/delivery/screenshots/m0-5')
      : testInfo.outputDir;
    await mkdir(folder, { recursive: true });
    await page.screenshot({
      path: path.join(folder, name + '.png'),
      fullPage: !mobile,
      animations: 'disabled',
    });
  });
}

import { test as base, expect, type Page } from '@playwright/test';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

export interface SyntheticFixture {
  factories: Record<string, string>;
  assets: Record<string, string>;
  users: Record<string, string>;
  codes: Record<string, string[]>;
}
const transportSubjects = new WeakMap<Page, string>();
export const test = base.extend<{ data: SyntheticFixture; boundary: void }>({
  data: async ({}, use) => {
    await use(
      JSON.parse(
        await readFile(process.env.FACTORY_OPS_IDENTITY_FIXTURE!, 'utf8'),
      ) as SyntheticFixture,
    );
  },
  boundary: [
    async ({ page }, use) => {
      const rejected: string[] = [];
      const errors: string[] = [];
      await page.route('**/*', async (route) => {
        const url = new URL(route.request().url());
        if (
          url.origin === 'https://accounts.feishu.cn' &&
          url.pathname === '/open-apis/authen/v1/authorize'
        ) {
          if (
            url.searchParams.get('client_id') !== 'SYNTH-APP' ||
            url.searchParams.get('code_challenge_method') !== 'S256'
          )
            throw new Error('Synthetic authorization contract mismatch');
          const file = process.env.FACTORY_OPS_IDENTITY_FIXTURE!;
          const data = JSON.parse(await readFile(file, 'utf8')) as SyntheticFixture;
          const role = transportSubjects.get(page) ?? 'engineer';
          const code = data.codes[role]?.shift();
          if (!code) throw new Error('Synthetic authorization pool exhausted');
          await writeFile(file, JSON.stringify(data), { mode: 0o600 });
          const destination = new URL('https://localhost:4175/api/v1/auth/feishu/callback');
          destination.searchParams.set('state', url.searchParams.get('state') ?? '');
          destination.searchParams.set('code', code);
          return route.fulfill({ status: 302, headers: { location: destination.href }, body: '' });
        }
        if (url.origin !== 'https://localhost:4175') {
          rejected.push('unexpected external request');
          return route.abort();
        }
        return route.continue();
      });
      page.on('pageerror', () => errors.push('uncaught browser error'));
      await use();
      expect(rejected).toEqual([]);
      expect(errors).toEqual([]);
    },
    { auto: true },
  ],
});
export { expect };
export async function chooseIdentity(page: Page, role: string) {
  // Test-only choice stays in the intercepted browser transport, never in a platform request.
  transportSubjects.set(page, role);
}
export async function enter(page: Page, role = 'engineer', target = '/assets') {
  await page.goto('/#/login?return_to=' + encodeURIComponent(target));
  await expect(page.getByRole('button', { name: '通过飞书登录' })).toBeEnabled();
  await chooseIdentity(page, role);
  await page.getByRole('button', { name: '通过飞书登录' }).click();
  await expect
    .poll(
      () => page.url().startsWith('https://localhost:4175/#/') && !page.url().includes('/login'),
    )
    .toBe(true);
  await expect(page.locator('#main-content')).toBeVisible();
}
export async function capture(page: Page, filename: string) {
  if (process.env.FACTORY_OPS_CAPTURE_SCREENSHOTS !== '1') return;
  if (/[?&](?:state|code)=/.test(page.url()))
    throw new Error('Cannot capture an authentication callback');
  await expect(
    page.getByText(/隔离测试环境 · 合成身份|隔离测试环境 · 合成数据/).first(),
  ).toBeVisible();
  const directory = path.resolve('../docs/delivery/screenshots/m1-02');
  await mkdir(directory, { recursive: true });
  await page.screenshot({
    path: path.join(directory, filename + '.png'),
    fullPage: (page.viewportSize()?.width ?? 1440) > 760,
  });
}

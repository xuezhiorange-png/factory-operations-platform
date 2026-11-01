import { test, expect, enter, capture } from './fixture';

test('PC 登录回到设备详情，安全 Cookie 不可被脚本读取，退出后不可查询', async ({
  page,
  context,
  data,
}) => {
  await page.goto('/#/login');
  await expect(page.getByRole('button', { name: '通过飞书登录' })).toBeEnabled();
  await capture(page, 'pc-login');
  await enter(page, 'engineer', `/assets/${data.assets.A}?factory=${data.factories.A}`);
  await expect(page.getByRole('heading', { name: 'SYNTH-设备-A', exact: true })).toBeVisible();
  const safeCookies = (await context.cookies()).filter(
    (cookie) => cookie.name === '__Host-factory_ops_session',
  );
  expect(
    safeCookies.length === 1 &&
      safeCookies.every((cookie) => cookie.secure && cookie.httpOnly && cookie.sameSite === 'Lax'),
  ).toBe(true);
  expect(await page.evaluate(() => document.cookie.includes('__Host-factory_ops_session'))).toBe(
    false,
  );
  await page.getByRole('button', { name: /^当前账号：/ }).click();
  await expect(
    page.getByRole('heading', { name: 'SYNTH-人员-engineer', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: '退出登录', exact: true }).click();
  await expect(page.getByRole('heading', { name: '登录设备运维平台' })).toBeVisible();
  await page.goto(`/#/assets/${data.assets.A}?factory=${data.factories.A}`);
  await expect(page).toHaveURL(/\/login/);
});

test('PC 集团可切厂并刷新台账，保留原有工作台与导航', async ({ page, data }) => {
  await enter(page, 'group', '/workbench');
  await expect(page.getByRole('heading', { name: '工作台', exact: true })).toBeVisible();
  await page.getByRole('button', { name: /合成测试工厂 A/ }).click();
  await page.getByRole('link', { name: '合成测试工厂 B', exact: true }).click();
  await expect(page.getByText('SYNTH-设备-B', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('combobox', { name: '所属工厂' })).toHaveValue(data.factories.B!);
  await capture(page, 'pc-authenticated-assets');
});

test('H5 工作台免登入口复用授权流程，保持五入口与设备刷新', async ({ page, data }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(
    `/#/m/login?auto=1&return_to=${encodeURIComponent(`/m/assets/${data.assets.A}?factory=${data.factories.A}`)}`,
  );
  await expect(page.getByRole('heading', { name: 'SYNTH-设备-A', exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText('合成位置-A', { exact: true })).toBeVisible();
  await expect(
    page.getByRole('navigation', { name: '移动端主导航' }).getByRole('link'),
  ).toHaveCount(5);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await capture(page, 'h5-authenticated-detail');
});

test('首次登录仅建待授权账号，不获得设备或其他工厂数据', async ({ page, data }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enter(page, 'pending', '/m/me');
  await expect(
    page.getByText('账号待授权。请联系集团负责人分配角色与工厂范围。', { exact: true }),
  ).toBeVisible();
  await capture(page, 'h5-pending-account');
  await page.goto(`/#/m/assets/${data.assets.B}?factory=${data.factories.B}`);
  await expect(page.getByRole('heading', { name: '无查询权限', exact: true })).toBeVisible();
  await expect(page.getByText('SYNTH-设备-B', { exact: true })).toHaveCount(0);
});

test('未登录、登录过期和身份服务异常有不同提示，并可恢复', async ({ page, context }) => {
  await page.goto('/#/assets');
  await expect(page.getByText('尚未登录', { exact: true })).toBeVisible();
  await enter(page);
  await context.clearCookies();
  await page.route('**/api/v1/auth/me', (route) =>
    route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ error: { code: 'session_expired' } }),
    }),
  );
  await page.goto('/#/workbench');
  await expect(page.getByText('登录已过期或被撤销，请重新登录。', { exact: true })).toBeVisible();
  await page.unroute('**/api/v1/auth/me');
  await page.route('**/api/v1/auth/me', (route) => route.abort('failed'));
  await page.getByRole('button', { name: '重新检查服务' }).click();
  await expect(page.getByText('身份服务异常，请稍后重试。', { exact: true })).toBeVisible();
  await page.unroute('**/api/v1/auth/me');
  await page.getByRole('button', { name: '重新检查服务' }).click();
  await expect(page.getByText('尚未登录', { exact: true })).toBeVisible();
});

test('登录页拒绝外部回跳，工程师无法通过 UUID 访问 B 厂', async ({ page, data }) => {
  await enter(page, 'engineer', '//external.invalid');
  await expect(page).toHaveURL(/\/workbench/);
  await page.goto(`/#/assets/${data.assets.B}?factory=${data.factories.B}`);
  await expect(page.getByRole('heading', { name: '无查询权限', exact: true })).toBeVisible();
  await expect(page.getByText('SYNTH-设备-B', { exact: true })).toHaveCount(0);
});

test('H5 异常授权保留原目标，重新发起可恢复', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const pattern = 'https://accounts.feishu.cn/open-apis/authen/v1/authorize**';
  const failedTransport = async (route: import('@playwright/test').Route) => {
    const request = new URL(route.request().url());
    const destination = new URL('https://localhost:4175/api/v1/auth/feishu/callback');
    destination.searchParams.set('state', request.searchParams.get('state') ?? '');
    destination.searchParams.set('code', 'SYNTH-EXPIRED-CODE');
    await route.fulfill({ status: 302, headers: { location: destination.href }, body: '' });
  };
  await page.route(pattern, failedTransport);
  await page.goto('/#/m/login?return_to=/m/home');
  await page.getByRole('button', { name: '通过飞书登录' }).click();
  await expect(
    page.getByText('登录未完成。凭证可能无效、过期或已使用，请重新发起登录。', { exact: true }),
  ).toBeVisible();
  expect(new URL(page.url()).hash.startsWith('#/m/login')).toBe(true);
  await page.unroute(pattern, failedTransport);
  await page.getByRole('button', { name: '通过飞书登录' }).click();
  await expect(
    page.getByRole('heading', { name: '现场工作，有序连接', exact: true }),
  ).toBeVisible();
});

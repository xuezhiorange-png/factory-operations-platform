import { test, expect, type Page } from '@playwright/test';
async function persona(page: Page, name = 'engineer') {
  await page.request.post('/__portal_test__', {
    form: { persona: name }, headers: { Origin: 'http://127.0.0.1:5195' },
  });
}
test('monitor headers cannot create a personal operations identity', async ({ page }) => {
  await page.setExtraHTTPHeaders({ Authorization: `Bearer ${'a'.repeat(48)}`, 'X-User-ID': 'admin' });
  await page.goto('/operations/assets');
  await expect(page.getByRole('heading', { name: '统一登录待接入' })).toBeVisible();
  await expect(page.locator('.asset-data-row')).toHaveCount(0);
});
for (const width of [320, 390, 768, 1440]) {
  test(`real scoped API list/detail and responsive fit at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await persona(page);
    await page.goto('/operations/assets');
    await expect(page.getByText('隔离测试环境 · 合成数据')).toBeVisible();
    await expect(page.locator('.asset-data-row')).toHaveCount(2);
    const scope = page.getByRole('combobox', { name: '所属工厂' });
    await expect(scope.locator('option')).toHaveCount(1);
    await page.locator('.asset-data-row').first().getByRole('link', { name: '查看详情' }).click();
    await expect(page.getByRole('heading', { name: '设备详情' })).toBeVisible();
    await expect(page.getByText('尚未关联', { exact: true })).toBeVisible();
    await expect(page.locator('.operations-portal')).toHaveJSProperty('scrollWidth', await page.locator('.operations-portal').evaluate(e => e.clientWidth));
    await expect(page.locator('iframe')).toHaveCount(0);
    await page.getByRole('link', { name: '返回设备台账' }).click();
    await expect(page.locator('.asset-data-row')).toHaveCount(2);
  });
}
test('foreign factory query and tampered asset IDs never reveal other records', async ({ page }) => {
  const ids = await (await page.request.get('/__portal_test__/ids')).json();
  await persona(page);
  await page.goto(`/operations/assets?factory=${ids.factories.B}`);
  await expect(page.getByRole('heading', { name: '无查询权限' })).toBeVisible();
  await expect(page.locator('.asset-data-row')).toHaveCount(0);
  await page.goto(`/operations/assets/${ids.assets.B}?factory=${ids.factories.A}`);
  await expect(page.getByRole('heading', { name: '没有可访问的设备' })).toBeVisible();
  await expect(page.getByText('SYNTH-设备-B', { exact: true })).toHaveCount(0);
});
test('unmapped monitoring IDs never fall back to an arbitrary asset', async ({ page }) => {
  await persona(page);
  await page.goto('/operations/from-monitor?monitor_factory_id=FAC_UNKNOWN&monitor_device_id=unknown');
  await expect(page.getByRole('heading', { name: '尚未关联' })).toBeVisible();
  await expect(page.locator('.asset-data-row')).toHaveCount(0);
});
test('pending modules are explicit and personnel logic is not duplicated', async ({ page }) => {
  await persona(page);
  for (const [path, title] of [
    ['inspections', '人员巡检'], ['issues', '问题报修'], ['work-orders', '维修工单'],
    ['maintenance', '设备保养'], ['inventory', '备品备件'], ['analytics', '统计分析'],
  ]) {
    await page.goto(`/operations/${path}`);
    await expect(page.getByRole('heading', { name: `${title} · 待开发` })).toBeVisible();
    await expect(page.locator('table')).toHaveCount(0);
  }
  await page.goto('/operations/settings');
  await expect(page.getByRole('heading', { name: '无人员管理权限' })).toBeVisible();
  await persona(page, 'group');
  await page.reload();
  await expect(page.locator('.people-table tbody tr')).not.toHaveCount(0);
});
test('losing the personal session clears previously visible data', async ({ page }) => {
  await persona(page);
  await page.goto('/operations/assets');
  await expect(page.locator('.asset-data-row')).toHaveCount(2);
  await persona(page, 'none');
  await page.reload();
  await expect(page.getByRole('heading', { name: '统一登录待接入' })).toBeVisible();
  await expect(page.locator('.asset-data-row')).toHaveCount(0);
});

test('disconnected entry never requests business or identity APIs despite a valid personal cookie', async ({ page }) => {
  await persona(page, 'group');
  const requests: string[] = [];
  page.on('request', request => { if (request.url().includes('/operations-api/')) requests.push(request.url()); });
  await page.goto('/operations/assets?connected=false');
  await expect(page.getByRole('heading', { name: '设备运维待接入' })).toBeVisible();
  await expect(page.getByRole('button', { name: '重新校验运维权限' })).toHaveCount(0);
  await page.getByRole('link', { name: '维修工单 待开发' }).click();
  await expect(page.getByRole('heading', { name: '设备运维待接入' })).toBeVisible();
  await expect(page.locator('.asset-data-row, .people-table')).toHaveCount(0);
  expect(requests).toEqual([]);
});

test('disconnected deep link does not load an asset or monitoring association', async ({ page }) => {
  const ids = await (await page.request.get('/__portal_test__/ids')).json();
  await persona(page);
  const requests: string[] = [];
  page.on('request', request => { if (request.url().includes('/operations-api/')) requests.push(request.url()); });
  await page.goto(`/operations/assets/${ids.assets.A}?factory=${ids.factories.A}&connected=false`);
  await expect(page.getByRole('heading', { name: '设备运维待接入' })).toBeVisible();
  await expect(page.locator('.detail-fields')).toHaveCount(0);
  expect(requests).toEqual([]);
});

import type { Page } from '@playwright/test';
import { test, expect, enter, capture, protectPage } from './fixture';

async function row(page: Page, id: string) {
  const result = page.locator(`tr[data-person-id="${id}"]`);
  await expect(result).toBeVisible();
  return result;
}
async function restore(
  page: Page,
  id: string,
  role: string | null,
  factoryIds: string[],
  active = true,
) {
  const response = await page.request.get('/api/v1/access/users?limit=100');
  const body = await response.json();
  const current = body.items.find((item: { id: string }) => item.id === id);
  if (!current) throw new Error('Synthetic cleanup target missing');
  const nonce = await page.evaluate(
    () =>
      document.cookie
        .split('; ')
        .find((item) => item.startsWith('__Host-factory_ops_csrf='))
        ?.split('=')[1] ?? '',
  );
  const result = await page.request.patch(`/api/v1/access/users/${id}`, {
    headers: { Origin: 'https://localhost:4175', 'X-CSRF-Token': nonce },
    data: {
      expected_version: current.version,
      role,
      active,
      factory_ids: factoryIds,
      reason: 'SYNTH-隔离用例恢复',
    },
  });
  expect([200, 409].includes(result.status())).toBe(true);
}

test('集团人员页跨厂授权、审计与旧工程师会话撤销', async ({ page, browser, data }) => {
  const employeeContext = await browser.newContext({
    baseURL: 'https://localhost:4175',
    ignoreHTTPSErrors: true,
  });
  const employee = await employeeContext.newPage();
  const verify = await protectPage(employee);
  await enter(employee, 'engineer');
  await expect(employee.getByText('SYNTH-设备-A', { exact: true })).toBeVisible();
  await enter(page, 'group', '/settings?tab=people');
  try {
    const person = await row(page, data.users.engineer!);
    await expect(person).toContainText('已绑定');
    await expect(person).toContainText('工程师');
    expect(
      await page
        .locator('.people-table')
        .evaluate((element) => element.scrollWidth <= element.clientWidth + 1),
    ).toBe(true);
    await capture(page, 'pc-personnel');
    await person.getByRole('button', { name: '管理授权' }).click();
    await page.getByRole('checkbox', { name: '合成测试工厂 B', exact: true }).check();
    await page.getByRole('textbox', { name: '变更原因', exact: true }).fill('SYNTH-工程师跨厂授权');
    await capture(page, 'pc-access-drawer');
    await page.getByRole('button', { name: '保存授权', exact: true }).click();
    await expect(
      page.getByText('变更已由服务端确认，旧会话已撤销。', { exact: true }),
    ).toBeVisible();
    await employee.reload();
    await expect(
      employee.getByText('登录已过期或被撤销，请重新登录。', { exact: true }),
    ).toBeVisible();
    await enter(employee, 'engineer', `/assets?factory=${data.factories.B}`);
    await expect(employee.getByText('SYNTH-设备-B', { exact: true })).toBeVisible();
    await (await row(page, data.users.engineer!)).getByRole('button', { name: '变更记录' }).click();
    await expect(page.getByText('SYNTH-工程师跨厂授权', { exact: true })).toBeVisible();
    await capture(page, 'pc-access-history');
  } finally {
    await restore(page, data.users.engineer!, 'engineer', [data.factories.A!]);
    verify();
    await employeeContext.close();
  }
});

test('H5 人员管理单厂选择、停用和恢复，旧会话不复活', async ({ page, browser, data }) => {
  const employeeContext = await browser.newContext({
    baseURL: 'https://localhost:4175',
    ignoreHTTPSErrors: true,
  });
  const employee = await employeeContext.newPage();
  const verify = await protectPage(employee);
  await enter(employee, 'admin');
  await page.setViewportSize({ width: 390, height: 844 });
  await enter(page, 'group', '/m/settings?tab=people');
  try {
    const person = await row(page, data.users.admin!);
    await person.getByRole('button', { name: '管理授权' }).click();
    await expect(
      page.getByRole('checkbox', { name: '合成测试工厂 B', exact: true }),
    ).toBeDisabled();
    await page.getByRole('checkbox', { name: '账号启用', exact: true }).uncheck();
    await page.getByRole('textbox', { name: '变更原因', exact: true }).fill('SYNTH-离职停用');
    await page.getByRole('button', { name: '保存授权', exact: true }).click();
    await expect(
      (await row(page, data.users.admin!)).getByText('停用', { exact: true }),
    ).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.evaluate(() => window.scrollTo(0, 0));
    expect(
      await page
        .locator('.people-table')
        .evaluate((element) => element.getBoundingClientRect().right <= innerWidth),
    ).toBe(true);
    await capture(page, 'h5-personnel');
    await employee.reload();
    await expect(
      employee.getByText('登录已过期或被撤销，请重新登录。', { exact: true }),
    ).toBeVisible();
    await restore(page, data.users.admin!, 'factory_equipment_admin', [data.factories.A!], true);
    const oldSession = await employee.request.get('/api/v1/auth/me');
    expect(oldSession.status()).toBe(401);
    await enter(employee, 'admin');
    await expect(employee.getByText('SYNTH-设备-A', { exact: true })).toBeVisible();
  } finally {
    await restore(page, data.users.admin!, 'factory_equipment_admin', [data.factories.A!]);
    verify();
    await employeeContext.close();
  }
});

test('工程师人员入口拒绝访问，失败写入没有成功提示', async ({ page, data }) => {
  await enter(page, 'engineer', '/settings?tab=people');
  await expect(
    page.getByRole('heading', { name: '仅集团负责人可管理人员', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: /^当前账号：/ }).click();
  await page.getByRole('button', { name: '退出登录', exact: true }).click();
  await enter(page, 'group', '/settings?tab=people');
  await (await row(page, data.users.multi!)).getByRole('button', { name: '管理授权' }).click();
  await page.getByRole('checkbox', { name: '合成测试工厂 B', exact: true }).uncheck();
  await page.getByRole('textbox', { name: '变更原因', exact: true }).fill('SYNTH-模拟网络异常');
  await page.route('**/api/v1/access/users/*', (route) =>
    route.request().method() === 'PATCH' ? route.abort('failed') : route.continue(),
  );
  await page.getByRole('button', { name: '保存授权', exact: true }).click();
  await expect(page.getByText('变更未获确认，请刷新核对后重试。', { exact: true })).toBeVisible();
  await expect(page.getByText('变更已由服务端确认，旧会话已撤销。', { exact: true })).toHaveCount(
    0,
  );
});

test('人员会话撤销和飞书解绑均需确认，解绑后拒绝重新登录', async ({ page, browser }) => {
  const employeeContext = await browser.newContext({
    baseURL: 'https://localhost:4175',
    ignoreHTTPSErrors: true,
  });
  const employee = await employeeContext.newPage();
  const verify = await protectPage(employee);
  try {
    await enter(employee, 'lifecycle', '/m/me');
    const current = await (await employee.request.get('/api/v1/auth/me')).json();
    await enter(page, 'group', '/settings?tab=people');
    await (await row(page, current.id)).getByRole('button', { name: '管理授权' }).click();
    await page.getByRole('textbox', { name: '变更原因', exact: true }).fill('SYNTH-主动撤销会话');
    await page.getByRole('button', { name: '撤销全部会话', exact: true }).click();
    await expect(page.getByText('确认撤销此人员的全部平台会话？', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: '确认操作', exact: true }).click();
    await expect(
      page.getByText('变更已由服务端确认，旧会话已撤销。', { exact: true }),
    ).toBeVisible();
    await employee.reload();
    await expect(
      employee.getByText('登录已过期或被撤销，请重新登录。', { exact: true }),
    ).toBeVisible();
    await enter(employee, 'lifecycle', '/m/me');
    await (await row(page, current.id)).getByRole('button', { name: '管理授权' }).click();
    await page.getByRole('textbox', { name: '变更原因', exact: true }).fill('SYNTH-身份解绑');
    await page.getByRole('button', { name: '解绑飞书', exact: true }).click();
    await page.getByRole('button', { name: '确认操作', exact: true }).click();
    await expect(await row(page, current.id)).toContainText('已解绑');
    await employee.reload();
    await employee.getByRole('button', { name: '通过飞书登录' }).click();
    await expect(
      employee.getByText('账号已停用或身份绑定已撤销，请联系集团负责人。', { exact: true }),
    ).toBeVisible();
  } finally {
    verify();
    await employeeContext.close();
  }
});

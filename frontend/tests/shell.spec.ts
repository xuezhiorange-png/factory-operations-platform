import AxeBuilder from '@axe-core/playwright';
import { test as base, expect } from '@playwright/test';

const test = base.extend<{ networkBoundary: void }>({
  networkBoundary: [
    async ({ page }, use) => {
      const forbidden: string[] = [];
      const errors: string[] = [];
      await page.route('**/*', (route) => {
        const request = route.request();
        const url = new URL(request.url());
        if (
          url.origin !== 'http://127.0.0.1:4173' ||
          url.pathname.startsWith('/api/') ||
          !['GET', 'HEAD'].includes(request.method())
        ) {
          forbidden.push(`${request.method()} ${url.origin}${url.pathname}`);
          return route.abort();
        }
        return route.continue();
      });
      page.on('pageerror', (error) => errors.push(error.message));
      await use();
      expect(
        forbidden,
        'Shell must not call business APIs, write data or contact external systems',
      ).toEqual([]);
      expect(errors, 'No uncaught browser errors').toEqual([]);
    },
    { auto: true },
  ],
});

const modulePages = [
  ['assets', '设备台账'],
  ['inspections', '巡检管理'],
  ['issues', '问题报修'],
  ['work-orders', '维修工单'],
  ['maintenance', '设备保养'],
  ['inventory', '备品备件'],
  ['analytics', '统计分析'],
  ['settings', '系统设置'],
  ['design-system', '界面组件规范'],
] as const;
const details = [
  ['assets/preview', '设备详情'],
  ['inspections/preview', '巡检任务详情'],
  ['issues/preview', '报修详情'],
  ['work-orders/preview', '维修工单详情'],
] as const;

for (const mobile of [false, true]) {
  const prefix = mobile ? '/m/' : '/';
  const label = mobile ? 'H5' : 'PC';
  for (const [path, title] of [...modulePages, ...details]) {
    test(`${label} 直达与刷新：${title}`, async ({ page }) => {
      if (mobile) await page.setViewportSize({ width: 390, height: 844 });
      await page.goto(`/#${prefix}${path}`);
      await expect(page.getByRole('heading', { level: 1, name: title, exact: true })).toBeVisible();
      if (path.endsWith('preview'))
        await expect(page.getByText('详情结构预览', { exact: true })).toBeVisible();
      await page.reload();
      await expect(page.getByRole('heading', { level: 1, name: title, exact: true })).toBeVisible();
      await expect(page).toHaveTitle(`${title} · 加工厂设备运维`);
    });
  }
}
for (const [path, title] of [
  ['home', '现场工作，有序连接'],
  ['tasks', '我的任务'],
  ['scan', '扫码进入设备'],
  ['messages', '消息中心'],
  ['me', '我的'],
] as const) {
  test(`移动五入口直达刷新：${path}`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/#/m/${path}`);
    await expect(page.getByRole('heading', { name: title, exact: true, level: 1 })).toBeVisible();
    await page.reload();
    await expect(page.getByRole('heading', { name: title, exact: true, level: 1 })).toBeVisible();
    await expect(
      page.getByRole('navigation', { name: '移动端主导航' }).locator('a[aria-current="page"]'),
    ).toHaveCount(1);
  });
}

test('PC 工作台、侧栏、面包屑和详情返回', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/#\/workbench$/);
  await expect(page.locator('.metric-value')).toHaveText(['—', '—', '—', '—']);
  await page.reload();
  await expect(page.getByRole('heading', { name: '工作台', level: 1, exact: true })).toBeVisible();
  await page
    .getByRole('navigation', { name: '主导航', exact: true })
    .getByRole('link', { name: '设备台账', exact: true })
    .click();
  await page.getByRole('link', { name: '预览详情结构' }).click();
  await expect(page).toHaveURL(/#\/assets\/preview$/);
  await expect(
    page.getByRole('navigation', { name: '面包屑' }).getByText('设备详情'),
  ).toBeVisible();
  await page.getByRole('link', { name: '返回设备台账' }).click();
  await expect(page.getByRole('heading', { level: 1, name: '设备台账' })).toBeVisible();
});

test('搜索、筛选、页签仅改变界面，刷新重置，不产生保存成功', async ({ page }) => {
  await page.goto('/#/assets');
  await expect(page.getByRole('button', { name: '新增设备' })).toBeDisabled();
  await expect(page.getByRole('button', { name: '导出', exact: true })).toBeDisabled();
  await page.getByRole('textbox', { name: '搜索设备', exact: true }).fill('仅测试搜索交互');
  await expect(page.getByText('当前没有可查询的业务数据')).toBeVisible();
  await page.getByRole('button', { name: '筛选', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: '筛选条件' });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('combobox', { name: '设备分类', exact: true }).selectOption('制冷设备');
  await dialog.getByRole('button', { name: '查看筛选条件' }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByText('界面筛选条件已更新', { exact: false })).toBeVisible();
  await page.getByRole('tab', { name: '在用设备' }).click();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: '停用 / 封存' })).toHaveAttribute(
    'aria-selected',
    'true',
  );
  await page.reload();
  await expect(page.getByRole('textbox', { name: '搜索设备', exact: true })).toHaveValue('');
  await expect(page.getByText('保存成功')).toHaveCount(0);
});

test('原生弹窗支持 Escape、焦点恢复与抽屉关闭', async ({ page }) => {
  await page.goto('/#/design-system');
  const opener = page.getByRole('button', { name: '打开弹窗', exact: true });
  await opener.click();
  await expect(page.getByRole('dialog', { name: '弹窗组件展示' })).toBeVisible();
  await page.keyboard.press('Tab');
  expect(await page.evaluate(() => Boolean(document.activeElement?.closest('dialog')))).toBe(true);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(opener).toBeFocused();
  await page.getByRole('button', { name: '打开抽屉' }).click();
  await page.getByRole('dialog').getByRole('button', { name: '关闭', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('tab', { name: '加载状态' }).click();
  await expect(page.getByRole('status', { name: '' })).toHaveAttribute('aria-busy', 'true');
});

test('工厂与账号没有伪造数据，三角色没有切换或授权按钮', async ({ page }) => {
  await page.goto('/#/workbench');
  await page.getByRole('button', { name: '未选择工厂' }).click();
  await expect(page.getByRole('dialog').getByText('工厂组织尚未接入')).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: '账号状态：未登录' }).click();
  await expect(page.getByRole('dialog').getByText('身份服务尚未接入')).toBeVisible();
  await page.getByRole('link', { name: '查看三角色设计' }).click();
  await expect(page.locator('.role-card')).toHaveCount(3);
  await expect(page.locator('.role-card').getByRole('button')).toHaveCount(0);
  await expect(
    page.getByText('任何人不得验收本人实际执行的维修工单。', { exact: false }),
  ).toBeVisible();
  await page.getByRole('tab', { name: '集成设置', exact: true }).click();
  await page.getByRole('button', { name: '查看接入边界' }).last().click();
  await expect(page.getByRole('dialog').getByText('只补充运行事实，不下发控制命令')).toBeVisible();
});

test('移动首页跳转、底栏五入口与相机边界', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = async () => {
      document.documentElement.dataset.cameraRequested = 'yes';
      throw new Error('Camera calls are forbidden in the shell');
    };
  });
  await page.goto('/');
  await expect(page).toHaveURL(/#\/m\/home$/);
  const nav = page.getByRole('navigation', { name: '移动端主导航' });
  await nav.getByRole('link', { name: '任务', exact: true }).click();
  await page.getByRole('link', { name: '巡检任务结构' }).click();
  await expect(page.getByRole('heading', { name: '巡检任务详情', level: 1 })).toBeVisible();
  await nav.getByRole('link', { name: '扫码', exact: true }).click();
  await expect(page.getByRole('button', { name: '开始扫码 · 待开发' })).toBeDisabled();
  expect(
    await page.evaluate(() => document.documentElement.dataset.cameraRequested),
  ).toBeUndefined();
  await nav.getByRole('link', { name: '消息', exact: true }).click();
  await expect(page.getByText('消息服务尚未接入', { exact: true })).toBeVisible();
  await nav.getByRole('link', { name: '我的', exact: true }).click();
  await expect(page.getByText('未登录 · 未分配角色或工厂')).toBeVisible();
});

for (const width of [320, 390, 768, 1024, 1440]) {
  test(`响应式宽度 ${width}：内容不溢出屏幕`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const paths =
      width < 760
        ? ['m/home', 'm/assets', 'm/assets/preview', 'm/settings?tab=roles', 'm/me', 'workbench']
        : ['workbench', 'assets', 'assets/preview', 'settings?tab=integrations'];
    for (const path of paths) {
      await page.goto('/#/' + path);
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
        path,
      ).toBe(true);
    }
  });
}

test('窄屏管理端可打开和关闭侧栏', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#/workbench');
  await expect(page.getByRole('navigation', { name: '主导航', exact: true })).not.toBeVisible();
  await page.getByRole('button', { name: '打开导航菜单' }).click();
  await page
    .getByRole('navigation', { name: '主导航', exact: true })
    .getByRole('link', { name: '设备台账', exact: true })
    .click();
  await expect(page.getByRole('heading', { name: '设备台账', level: 1 })).toBeVisible();
  await expect(page.getByRole('navigation', { name: '主导航', exact: true })).not.toBeVisible();
});

test('跳到内容链接不破坏 hash 路由', async ({ page }) => {
  await page.goto('/#/workbench');
  await page.keyboard.press('Tab');
  await page.getByRole('link', { name: '跳到主要内容' }).press('Enter');
  await expect(page).toHaveURL(/#\/workbench$/);
  await expect(page.getByRole('main')).toBeFocused();
});
for (const path of ['missing', 'm/missing']) {
  test(`未知路径可恢复：${path}`, async ({ page }) => {
    await page.goto('/#/' + path);
    await expect(page.getByRole('heading', { name: '这个页面不在工作空间中' })).toBeVisible();
    await page.getByRole('link', { name: '返回工作台', exact: true }).click();
    await expect(page.getByRole('heading', { level: 1 })).not.toHaveText('这个页面不在工作空间中');
  });
}
for (const path of [
  'workbench',
  'assets',
  'assets/preview',
  'settings?tab=roles',
  'm/home',
  'm/scan',
]) {
  test(`基本无障碍检查：${path}`, async ({ page }) => {
    if (path.startsWith('m/')) await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/#/' + path);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(
      results.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => ({ target: n.target, summary: n.failureSummary })),
      })),
    ).toEqual([]);
  });
}

test('页面搜索只导航模块，不查询业务记录', async ({ page }) => {
  await page.goto('/#/workbench');
  await page.getByRole('button', { name: '搜索页面', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: '页面导航' });
  await dialog.getByRole('textbox', { name: '搜索模块页面' }).fill('保养');
  await expect(dialog.getByRole('link')).toHaveCount(1);
  await dialog.getByRole('link', { name: '设备保养' }).click();
  await expect(page.getByRole('heading', { name: '设备保养', level: 1 })).toBeVisible();
  await expect(dialog).not.toBeVisible();
});

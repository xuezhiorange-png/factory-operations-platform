import { test as base, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
interface Fixture {
  factories: Record<string, string>;
  assets: Record<string, string>;
  tokens: Record<string, string>;
}
const test = base.extend<{
  data: Fixture;
  role: string;
  identity: void;
  networkBoundary: void;
}>({
  role: ["engineer", { option: true }],
  data: async ({}, use) => {
    const descriptor: unknown = JSON.parse(
      await readFile(process.env.FACTORY_OPS_BROWSER_AUTH_FILE!, "utf8"),
    );
    if (
      typeof descriptor !== "object" ||
      !descriptor ||
      !("tokens" in descriptor)
    )
      throw new Error("Synthetic fixture is unavailable");
    await use(descriptor as Fixture);
  },
  identity: [
    async ({ context, data, role }, use) => {
      const token = data.tokens[role];
      if (typeof token !== "string" || !/^[A-Za-z0-9_-]{43}$/.test(token))
        throw new Error("Synthetic session is unavailable");
      await context.addCookies([
        {
          name: "factory_ops_session",
          value: token,
          domain: "127.0.0.1",
          path: "/",
          httpOnly: true,
          sameSite: "Lax",
          secure: false,
        },
      ]);
      await use();
      await context.clearCookies();
    },
    { auto: true },
  ],
  networkBoundary: [
    async ({ page }, use) => {
      const rejected: string[] = [];
      const errors: string[] = [];
      await page.route("**/*", (route) => {
        const r = route.request();
        const url = new URL(r.url());
        if (
          url.origin !== "http://127.0.0.1:4174" ||
          !["GET", "HEAD"].includes(r.method())
        ) {
          rejected.push("unexpected request");
          return route.abort();
        }
        return route.continue();
      });
      page.on("pageerror", () => errors.push("uncaught browser error"));
      await use();
      expect(rejected).toEqual([]);
      expect(errors).toEqual([]);
    },
    { auto: true },
  ],
});

test("PC 页面读取真实合成数据库，搜索与详情保持工厂范围", async ({
  page,
  data,
}) => {
  await page.goto("/#/assets");
  await expect(
    page.getByText("隔离测试环境 · 合成数据", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("SYNTH-设备-A", { exact: true })).toBeVisible();
  await expect(page.getByText("SYNTH-设备-B", { exact: true })).toHaveCount(0);
  await expect(
    page.getByRole("combobox", { name: "所属工厂" }).getByRole("option"),
  ).toHaveCount(1);
  await page
    .getByRole("textbox", { name: "搜索设备", exact: true })
    .fill("SYNTH-设备-A");
  await expect(page.locator(".asset-data-row")).toHaveCount(1);
  await page.getByRole("link", { name: "查看详情" }).click();
  await expect(
    page.getByRole("heading", { name: "SYNTH-设备-A", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("合成测试工厂 A", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("合成位置-A", { exact: true })).toBeVisible();
  expect(
    await page.evaluate(() => document.cookie.includes("factory_ops_session")),
  ).toBe(false);
  await expect(page).toHaveURL(new RegExp(data.assets.A));
});

test("H5 设备详情直接访问和刷新使用真实 API", async ({ page, data }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/#/m/assets/${data.assets.A}?factory=${data.factories.A}`);
  await expect(
    page.getByRole("heading", { name: "SYNTH-设备-A", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("SYNTH-制造商 / SYNTH-MODEL", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("真实空查询与请求失败为不同状态", async ({ page }) => {
  await page.goto("/#/assets");
  await expect(page.locator(".asset-data-row")).toHaveCount(2);
  await page
    .getByRole("textbox", { name: "搜索设备", exact: true })
    .fill("no-match-synthetic");
  await expect(
    page.getByRole("heading", { name: "暂无设备数据", exact: true }),
  ).toBeVisible();
  await page.route("**/api/v1/factories/*/assets?*", (route) =>
    route.abort("failed"),
  );
  await page.getByRole("button", { name: "刷新查询" }).click();
  await expect(
    page.getByRole("heading", { name: "设备查询失败" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "暂无设备数据", exact: true }),
  ).toHaveCount(0);
});

test("未授权工厂、直接 UUID 与匿名会话不显示设备", async ({
  page,
  context,
  data,
}) => {
  await page.goto(`/#/assets?factory=${data.factories.B}`);
  await expect(
    page.getByRole("heading", { name: "无查询权限", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("SYNTH-设备-B", { exact: true })).toHaveCount(0);
  await page.goto(`/#/m/assets/${data.assets.B}?factory=${data.factories.B}`);
  await expect(
    page.getByRole("heading", { name: "无查询权限", exact: true }),
  ).toBeVisible();
  await context.clearCookies();
  await page.goto("/#/assets");
  await expect(
    page.getByRole("heading", { name: "无查询权限", exact: true }),
  ).toBeVisible();
});

test("API 加载中有真实等待状态，搜索不会渲染过期结果", async ({ page }) => {
  let release!: () => void;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/factories/*/assets?*", async (route) => {
    await pending;
    await route.continue();
  });
  await page.goto("/#/assets");
  try {
    await expect(page.getByRole("status")).toContainText("正在查询设备数据");
  } finally {
    release();
  }
  await expect(page.locator(".asset-data-row")).toHaveCount(2);
  await page
    .getByRole("textbox", { name: "搜索设备", exact: true })
    .fill("SYNTH-设备-B");
  await expect(
    page.getByRole("heading", { name: "暂无设备数据", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("SYNTH-设备-A", { exact: true })).toHaveCount(0);
});

test.describe("集团负责人合成会话", () => {
  test.use({ role: "group" });
  test("集团可查询其他工厂，真实空工厂不会显示成无权限", async ({
    page,
    data,
  }) => {
    await page.goto(`/#/assets?factory=${data.factories.B}`);
    await expect(page.getByText("SYNTH-设备-B", { exact: true })).toBeVisible();
    await page.getByRole("link", { name: "查看详情" }).click();
    await expect(
      page.getByRole("heading", { name: "SYNTH-设备-B", exact: true }),
    ).toBeVisible();
    await page.getByRole("link", { name: "返回设备台账" }).click();
    await expect(page.getByRole("combobox", { name: "所属工厂" })).toHaveValue(
      data.factories.B!,
    );
    await expect(page.getByText("SYNTH-设备-B", { exact: true })).toBeVisible();
    await page
      .getByRole("combobox", { name: "所属工厂" })
      .selectOption(data.factories.EMPTY!);
    await expect(
      page.getByRole("heading", { name: "暂无设备数据", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "无查询权限", exact: true }),
    ).toHaveCount(0);
  });
});

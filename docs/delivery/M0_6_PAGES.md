# M0.6 GitHub Pages 静态预览部署与验收

日期：2026-11-01。项目：`xuezhiorange-png/factory-operations-platform`。

## 范围与公开性

只公开**已完成 M0.5 的空系统**：固定源代码提交 `f38232dd3821c22b964d8298edddac6b5be63705`（已合并 PR #3）。不随未来 M1 业务代码升级自动发布。

预览内没有真实账号、工厂、设备、数据、API、数据库、飞书身份或监控接口；业务写入按钮禁用。GitHub Pages 是**公开访问**，不能当作含敏感数据的私有测试环境。

## 部署前提（需仓库所有者一次性操作）

GitHub Pages 当前未启用（检查仓库 `has_pages=false`）。到 [Settings → Pages](https://github.com/xuezhiorange-png/factory-operations-platform/settings/pages)，在 Build and deployment → Source 中选择 **GitHub Actions**。

此设置不在本仓库 GitHub 连接所支持的写操作范围内，不能靠默认 `GITHUB_TOKEN` 自动启用 Pages。若未启用，部署 job 将明确跳过，并不意味着已经上线。

配置后到 [Actions → M0.6 Static Shell Pages Preview](https://github.com/xuezhiorange-png/factory-operations-platform/actions/workflows/m0-6-pages-preview.yml)，选择 Run workflow，在 `main` 执行。只有 GitHub Actions 的 `deploy` 作业成功后，才算发布完成。

预期站点地址（**不是上线证据**）：
- PC：`https://xuezhiorange-png.github.io/factory-operations-platform/#/workbench`
- H5：`https://xuezhiorange-png.github.io/factory-operations-platform/#/m/home`

实际发布 URL 以 GitHub Actions `deploy` 输出的 `page_url` 为准；上线后还需要浏览器实际验证。

## 技术实现

- `M0.6 Static Shell Pages Preview` 使用两次只读 checkout：固定 M0.5 源码和当前审核脚本。
- Vue 构建使用 `npm run build -- --base /factory-operations-platform/`，与 GitHub Pages 仓库子路径一致；本地 Vite 配置不变。
- 使用现有 hash 路由。静态浏览器刷新与前进/后退不需要后端 URL rewrite。
- `scripts/check_pages_dist.py` 验证构建入口的 JS/CSS 路径、资产存在性及禁止发布的调试/凭据扩展名；它不替代安全扫描。
- PR 检查只生成短期预览构建 artifact，不会部署。合并后仅在默认分支和 Pages 已启用时执行部署。
- 后续功能开发即使修改 `main` 中的前端，预览部署也始终检出固定的 M0.5 提交，不会发布未来业务代码。只有单独审查变更固定 SHA 才能调整。
- 不需要使用企业服务器、不操作旧冷库监控、不新建数据库、不开启业务权限或飞书登录。

## 验收标准

1. Pages 设置 Source=GitHub Actions，`deploy` job 成功，给出 GitHub 确认的 `page_url`。
2. 站点仓库子路径返回 HTTP 200，JS/CSS 无 404；不出现空白页。
3. PC 工作台、设备台账、巡检、报修、维修、保养、备件、分析、设置与二级详情导航可用，刷新/返回正常。
4. H5 首页、任务、扫码、消息、我的可用；仍明确显示扫码/业务未接入、不申请相机权限。
5. 在实际 iPhone Safari / 飞书内置浏览器至少做一次人工体验；本轮自动 Chromium 不能代替。
6. 无真实业务接口请求、飞书和监控访问；全站公开展示的只有空系统文案与本地静态资源。
7. 明确注明 Pages 部署成功与现场真机体验是不同验收步骤。

## 回滚

撤销工作流代码**不一定会删除已经发布的 Pages 网站**。需在 Settings → Pages 对站点取消发布/关闭，必要时撤销 `github-pages` 环境部署。不可依靠删除 PR 自动撤销已公开的内容。

现有生产服务器、PLC、冷库监控与真实业务数据库均不涉及。
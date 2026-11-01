# ADR-0003：M0.5 平台空壳、路由与模块边界

状态：本轮实现，待 Draft PR 评审 | 日期：2026-11-01  
TASK_ID：`FACTORY_OPS_M0_5_PLATFORM_SHELL`

## 决策

在 M0 的 Vue 3 / TypeScript 工程上增加平台空壳，不创建业务数据库、业务 API、认证实现或真实数据。
M0 PR 尚未合并，独立分支 `codex/m0-5-platform-shell` 依赖 `codex/m0-bootstrap`，不覆盖或合并 M0。

## M0 合并后的基线更新（2026-11-01）

- M0 [PR #1](https://github.com/xuezhiorange-png/factory-operations-platform/pull/1) 已以普通 Merge Commit `2f23bb38af875157ea4811d5d0b7b5287912008c` 合并至 `main`。
- 本 M0.5 [PR #2](https://github.com/xuezhiorange-png/factory-operations-platform/pull/2) 的目标分支随后由 `codex/m0-bootstrap` 改为 `main`，历史依赖记录保留作为开发背景。
- 合并前需按最新提交重新验证 GitHub Actions 的 Backend、Frontend、Docs 作业；在校验结果通过前不得声称合并成功。
- 本次 ADR 维护不新增业务 API、数据库、登录、飞书接入、监控写入或生产部署。


- PC 与 H5 分别使用 DesktopLayout 和 MobileLayout，共享颜色、组件、模块视图和接口类型。
- Vue Router 使用 hash history；直接访问 `/#/assets` 或 `/#/m/tasks` 后刷新不需要服务端 rewrite。
  首次进入根路径时，宽度不超过 760px 进入 H5，否则进入管理端；显式链接可切换界面，不因旋转屏幕强制跳页。
- 本轮按用户要求展示全部八个主要模块；覆盖 PRD 一期六入口的排期建议，保养/备件/分析仍为待开发空壳。
- `app/` 拥有路由与导航；`shared/` 拥有布局、交互与设计系统；`modules/` 拥有各模块页面、文案和拟定读接口。
- 页面按路由懒加载。共享表格没有业务数据源，筛选/搜索只管理临时 UI 条件，不发出假查询。
- 业务操作使用原生 disabled。可点击入口仅进行页面导航、页签、抽屉/弹窗或筛选展示；不显示保存成功。
- 指标使用“— / 待接入”，不填充示例设备、人员、任务、告警或趋势数据。详情明确是结构预览。
- 系统设置只说明三种正式管理角色，无登录、角色切换、鉴权 guard、用户会话、token 或权限模拟。
- 飞书不加载 SDK，扫码不调用 getUserMedia；监控只定义只读端口，不请求真实系统、不提供控制方法。

## 设计系统与可访问性

深墨侧栏与青绿色强调、浅灰画布、白色卡片；系统字体，无外部字体/图片请求。
表格横向滚动限定在表格容器内，H5 使用 safe-area 与固定五入口；窄屏管理端使用折叠侧栏。
页签支持方向键、Home/End；弹窗/抽屉使用原生 dialog 提供焦点限制、Escape 和焦点恢复；
跳到内容按钮保留 hash 路由。辅助文字按实际背景修正对比度，支持减少动态效果。

自动化使用 Chromium + Playwright 和六个页面的 axe 基础扫描，不能据此宣称完整 WCAG 合规或飞书实机兼容。

## 兼容、迁移与回滚

后端与既有 `/api/v1/health` 契约原样保留；前端空壳不自动调用健康接口，不需要运行 API 或数据库即可浏览。
新增 vue-router 与图标库，更新 npm 锁文件；新增浏览器测试依赖，不引入企业配置。
旧 M0 根页面由工作台替代；业务 API、数据库、生产系统没有迁移或副作用。

回滚通过撤销本轮前端/CI/文档提交恢复 M0；不强推、不删除生产数据、不改原监控。
后续接入方法见 [前端接入说明](FRONTEND_SHELL.md)。

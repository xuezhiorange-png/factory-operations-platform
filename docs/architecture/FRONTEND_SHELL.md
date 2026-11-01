# M0.5 前端模块接入说明

本轮只有 UI 空壳，任何 `contracts.ts` 都是拟定接口边界，不是已发布 API 或可用适配器。

## 目录与依赖

```text
frontend/src/
  app/                    路由、导航、404
  shared/
    layouts/              PC 布局与 H5 五入口布局
    components/           页头、页签、空状态、表格壳、详情壳、弹窗/抽屉、加载状态
    composables/          仅 UI 的端路径选择
    contracts.ts          工厂范围、分页查询、拟定只读端口
    types.ts / icons.ts   展示配置与统一图标
  modules/
    dashboard/            工作台，无 KPI 数据或模拟任务
    assets/               设备台账、详情结构、读端口
    inspections/          巡检任务/计划/模板入口、任务详情、读端口
    issues/               问题池、报修详情、读端口
    work-orders/          工单列表、详情结构、读端口
    maintenance/          保养计划/任务/模板入口、读端口
    inventory/            备件台账/领退/流水入口、读端口
    analytics/            报表/分析入口、读端口
    settings/             组织、三角色、集成、基础设置、组件规范、读端口
    integrations/         飞书入口能力和监控只读端口，均无实现
    mobile/               首页、任务、扫码、消息、我的
  tokens.css / style.css  颜色、字体、间距、组件和响应式规则
```

共享组件不引用具体业务模块。模块可依赖 shared；路由负责装配，组件不直接发起业务请求。
M0 原 `src/api/health.ts` 保留原样，但本轮没有自动调用；不会伪装后端在线。

## 页面路由

32 个实际页面：PC 14 个、H5 18 个；另有根路径重定向和两端 404。
`id` 可以是未来实体标识；本轮不会用它查询或冒充记录，`preview` 是明确的结构预览入口。

| 模块 | PC hash 路径 | H5 hash 路径 |
|---|---|---|
| 工作台 / 首页 | `/#/workbench` | `/#/m/home` |
| 设备台账 | `/#/assets` | `/#/m/assets` |
| 设备详情 | `/#/assets/:id` | `/#/m/assets/:id` |
| 巡检管理 | `/#/inspections` | `/#/m/inspections` |
| 巡检任务详情 | `/#/inspections/:id` | `/#/m/inspections/:id` |
| 问题报修 | `/#/issues` | `/#/m/issues` |
| 报修详情 | `/#/issues/:id` | `/#/m/issues/:id` |
| 维修工单 | `/#/work-orders` | `/#/m/work-orders` |
| 工单详情 | `/#/work-orders/:id` | `/#/m/work-orders/:id` |
| 设备保养 | `/#/maintenance` | `/#/m/maintenance` |
| 备品备件 | `/#/inventory` | `/#/m/inventory` |
| 统计分析 | `/#/analytics` | `/#/m/analytics` |
| 系统设置 | `/#/settings` | `/#/m/settings` |
| 组件规范（评审入口） | `/#/design-system` | `/#/m/design-system` |
| 我的任务 | — | `/#/m/tasks` |
| 扫码 | — | `/#/m/scan` |
| 消息 | — | `/#/m/messages` |
| 我的 | — | `/#/m/me` |

设置支持 `?tab=organization|roles|integrations|general`，刷新保留当前设置页签。
路由静态资源加载失败时显示独立恢复页；“重新加载页面”会完整刷新原目标，避免浏览器缓存失败导入导致循环报错，
“返回工作台”按失败目标选择 PC/H5 入口。不会显示原始错误、令牌或 URL 参数，也不会执行业务请求。
窄屏管理端菜单使用原生 dialog 与首尾焦点循环；Esc、路由跳转、跨断点关闭时均释放遮罩和焦点。

列表筛选与搜索仅在当前页面临时保留，刷新/离开后重置，不写 localStorage。
桌面“搜索页面”只搜索模块名称，不搜索业务数据。

## 可操作与禁用边界

可操作：导航、返回、页签、页面搜索、筛选条件展示/重置、说明弹窗/抽屉、组件状态展示。
禁用：所有新增、编辑、导出、保存、提交、巡检开工、扫码、配置连接、工厂切换和消息已读。
空表格不是“后端查询结果为零”；明确显示“业务尚未接入”。指标也不显示伪造的零或百分比。

## 逐模块接入步骤

1. 先冻结模块的正式请求/响应与错误契约；拟定端口中的字段需与后端共同评审，不可直接当成数据库模型。
2. 在对应模块增加 `api/` 适配器，以依赖注入/显式装配替换空状态；不要让公共布局包含请求细节。
3. 由后端校验身份、最新工厂授权、实体真实所属工厂、任务指派和状态；前端路由、角色标签和 factoryId 不构成权限。
4. 增加真实 loading/error/empty/loaded 四态；无权限、未连接、查询为空和请求失败必须区分。
5. 只有正式接口、事务审计、幂等/版本控制和成功/拒绝/重复/越权/回滚测试完成后才启用写按钮。
6. 保留既有路由、PC/H5 共享状态规则和浏览器回归测试，再逐步替换详情预览入口。

| 模块 | 接入先决条件 |
|---|---|
| assets | 稳定资产 ID、位置/机位/测点分离、安装有效期、导入对账、二维码与附件授权 |
| inspections | 模板版本、批次/任务、被指派/实际执行人、漏检/晚检/代检事实 |
| issues | 保留来源、位置报修、分诊与重复关联；与工单独立 |
| work-orders | 状态机、实际维修人、非本人验收、事务审计/outbox、幂等/并发 |
| maintenance | 可信周期/计量来源，计划变更、延期和取消留痕 |
| inventory | 明确 ERP 责任边界，工单关联的不可删领退流水 |
| analytics | 可信时间轴与口径；缺数据不计算 MTTR/MTBF |
| settings | 企业身份后端校验、本地三角色与厂范围、会话撤权；显示标签不是授权 |
| integrations | 飞书凭证只在后端；监控只读白名单、有效期映射、原事件幂等，无控制端口 |

## H5 与上线限制

使用 responsive viewport、viewport-fit 和 safe-area；未使用飞书 JS SDK、相机、SSO 或企业租户。
浏览器模拟手机尺寸不代表 iOS/Android 飞书 WebView、实际扫码、离线照片或通知已验收。
所有字体/图标均随构建本地打包，没有 CDN。静态根路径托管假设与 hash 路由见 ADR；
子目录托管需要另配 Vite base，正式接口代理、登录与发布均不在本轮范围。

测试与截图见 [M0.5 验证记录](../delivery/M0_5_VERIFICATION.md)。

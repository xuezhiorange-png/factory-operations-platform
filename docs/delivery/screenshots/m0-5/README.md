# M0.5 实际页面截图

由本地 Chromium 从构建后的 Vue 应用采集；全部为空壳界面，没有实际工厂、设备、人员或任务记录。
PC 1440×1060（全页可高于 1060），H5 390×844（视口截图，页面可向下滚动）。

| 页面 | 路由 | 截图 |
|---|---|---|
| PC 工作台 | `/#/workbench` | [查看](pc-workbench.png) |
| PC 设备台账 | `/#/assets` | [查看](pc-assets.png) |
| PC 设备详情 | `/#/assets/preview` | [查看](pc-asset-detail.png) |
| PC 工单详情 | `/#/work-orders/preview` | [查看](pc-work-order.png) |
| PC 三角色预留 | `/#/settings?tab=roles` | [查看](pc-roles.png) |
| PC 集成设置 | `/#/settings?tab=integrations` | [查看](pc-integrations.png) |
| H5 首页 | `/#/m/home` | [查看](mobile-home.png) |
| H5 任务 | `/#/m/tasks` | [查看](mobile-tasks.png) |
| H5 扫码 | `/#/m/scan` | [查看](mobile-scan.png) |
| H5 消息 | `/#/m/messages` | [查看](mobile-messages.png) |
| H5 我的 | `/#/m/me` | [查看](mobile-me.png) |
| H5 设备详情 | `/#/m/assets/preview` | [查看](mobile-asset-detail.png) |

复现命令见 [验证记录](../../M0_5_VERIFICATION.md)。源码中的 `screenshots.spec.ts` 控制采集路线，
普通 CI 将截图保存在测试 artifact；只有显式 `CAPTURE_SHELL_SCREENSHOTS=1` 才更新本目录图片。

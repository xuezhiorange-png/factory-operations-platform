# M1-02 PC / H5 截图（隔离合成环境）

截图来自本地 HTTPS 浏览器→正常 OAuth 回调/会话 API→独立 PostgreSQL 的自动化流程。
飞书官方端点使用可验证 HTTP 响应替身，不代表真实租户认证已接通。
只显示合成人员/工厂/设备，未保存 Cookie、授权码、state、令牌、trace 或浏览器 storage state。
截图函数拒绝认证回调 URL，且要求页面具有“隔离测试环境”标记。

| 页面 | 截图 |
|---|---|
| PC 登录 | [pc-login.png](pc-login.png) |
| 集团负责人查询 B 厂台账 | [pc-authenticated-assets.png](pc-authenticated-assets.png) |
| H5 已认证设备详情 | [h5-authenticated-detail.png](h5-authenticated-detail.png) |
| H5 首次登录待授权 | [h5-pending-account.png](h5-pending-account.png) |
| PC 人员管理 | [pc-personnel.png](pc-personnel.png) |
| PC 工程师工厂授权 | [pc-access-drawer.png](pc-access-drawer.png) |
| PC 权限变更记录 | [pc-access-history.png](pc-access-history.png) |
| H5 人员管理卡片 | [h5-personnel.png](h5-personnel.png) |

重拍仅在隔离测试库配置完成后设置 `FACTORY_OPS_CAPTURE_SCREENSHOTS=1 npm run test:identity`。
CI 不设置该变量，也不上传认证浏览器输出目录。

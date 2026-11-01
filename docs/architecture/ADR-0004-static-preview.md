# ADR-0004：M0.6 公开静态预览与版本冻结

状态：待 PR 评审 | 日期：2026-11-01

## 决策

仅用 GitHub Pages 展示无数据的 M0.5 空壳，不在原生产服务器部署；构建输入固定为 `f38232dd3821c22b964d8298edddac6b5be63705`，避免 M1 以后真实业务代码被自动发布到公共网站。

Pages 源为 GitHub Actions，页面资源使用 `/factory-operations-platform/` 基路径，Vue hash 路由保留。PR 只检查静态构建，默认分支在 Pages 由仓库所有者启用后才可部署。GitHub Pages 公开且不具备内部业务数据授权保护，严禁纳入个人、设备和企业凭据。

## 权限与边界

发布 job 限 `refs/heads/main`，PR 不获得 pages write 或 id-token write。静态页面不开启 API、SSO、监控读写、PLC 操作或真实扫码。仓库设置 Pages Source 需人工完成，不在 Actions 内用默认 token 尝试高权限启用。

## 后续变更与回滚

更新预览需单独 PR 审核版本 pin；功能 PR 不更新静态预览。上线后即使撤销工作流，既有 Pages 仍可能公开，需手动取消发布。实现细节见 [M0.6 交付说明](../delivery/M0_6_PAGES.md)。
# 接口现状与后续目录

## M1-01 已实现：工厂范围内的设备只读查询

已实现 `GET /api/v1/factories`、`GET /api/v1/factories/{factory_id}/assets`、
`GET /api/v1/factories/{factory_id}/assets/{asset_id}`。均需后端有效会话与逐次工厂授权，
无正式登录或写 API。请求/响应、错误、审计及只读 MCP 契约见
[M1-01 完整契约](M1_01_ASSET_READ.md)，当前边界见
[ADR-0005](../architecture/ADR-0005-minimal-business-foundation.md)。

## 已实现：进程存活

`GET /api/v1/health`：无需登录，无请求体/工厂参数，成功返回 HTTP 200、`application/json`：

```json
{"status":"ok","service":"factory-operations","stage":"M0"}
```

三个字段是固定字面量，OpenAPI `/openapi.json` 可读取；FastAPI `/docs` 为框架文档。
无业务数据、无写入/审计事件、不查询数据库、不验证飞书或监控，不代表 readiness。
前端只据此展示 API 进程连接状态，5 秒超时显示未连接。Vite 的 `/api` 代理仅用于开发，
`vite build` 的静态文件不会自动代理 API，后续测试环境需配置同源反向代理。

## 计划接口（全部未实现，不是可调用 API）

| 阶段 | 路径草案 | 权限和事务要点 |
|---|---|---|
| M1 | `POST /api/v1/auth/feishu/exchange` | 官方身份校验+本地角色/厂授权；不以姓名/部门授权 |
| M1 | `POST /api/v1/factories/{factory_id}/assets` | 服务端授权；新增审计+幂等+事务 |
| M1 | `PATCH /api/v1/factories/{factory_id}/assets/{asset_id}` | 资源真实工厂与路由一致；更新版本号 |
| M1 | `POST /api/v1/factories/{factory_id}/asset-imports` | 先校验、差异预览，再确认；不静默覆盖身份 |
| M1 | `POST /api/v1/factories/{factory_id}/assets/{asset_id}/installations` | 有效期/机位/同厂约束；保留旧历史 |
| M1 | `GET /api/v1/factories/{factory_id}/attachments/{attachment_id}` | 同厂/所属资源授权后颁发短期对象链接 |
| M3 | `POST /api/v1/factories/{factory_id}/work-orders/{id}/verify` | 待验收、实际维修人独立性、版本号、事务审计/outbox |
| M5 | `GET /api/v1/factories/{factory_id}/assets/{asset_id}/monitor-summary` | 已确认映射、只读适配、采集时间/断联标识 |

未来接口需明确请求/响应 Schema、审计字段和错误码后才能实现。约定错误含义：未认证 401、
无工厂资格 403、在授权工厂下资源不存在 404、状态/版本/幂等冲突 409、输入无效 422；
禁止通过错误消息泄漏其他工厂资源。`factory_id` 取决于服务端资源归属，不能仅信任客户端传值。
验收/导入确认等写操作携带幂等键，相同键不同负载拒绝，审计和 outbox 与状态同事务。

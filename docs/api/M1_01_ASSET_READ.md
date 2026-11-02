# M1-01 设备只读 HTTP 与 MCP 契约

M1-03A 更新：远程 `/mcp`、第三项 list_factories 和官方 aily JWT 验证见
[当前 MCP 契约](M1_03A_REMOTE_MCP.md)。本文件保留 M1-01 历史基线及 HTTP 查询规则。

范围：真实 PostgreSQL 查询；仅三条业务 GET。无设备/授权写入、附件端点或正式身份登录。
运行时 OpenAPI 为 `/openapi.json`，本文件补充鉴权、隔离及错误约定。

## 认证与数据源

已由可信服务端签发的平台不透明会话通过 `factory_ops_session` Cookie 或
`Authorization: Bearer <opaque-session>` 提交。两个来源不一致则 401；不接收客户端 `user_id`，
`X-User-Id` 和未验证 `x-aily-jwt` 不能登录。数据库逐次验证摘要、签发/过期/撤销时间、
用户启用状态及最新工厂授权。前端不保存/读取令牌，使用同源 HttpOnly Cookie。
本轮不提供正式会话签发接口；隔离测试仅通过线下 fixture 创建合成会话。

业务响应均设置 `Cache-Control: no-store`、`Vary: Cookie, Authorization`。
`data_source` 为组合入口的服务端元信息：正常配置为 `configured_database`，隔离测试为
`synthetic_test`；客户端不能选择此值。后者在页面明确标注“隔离测试环境 · 合成数据”。
这个字段不证明已接入生产，也不授予查询权限。

## GET /api/v1/factories

无查询参数，200 返回 `{items: Factory[], data_source}`。
`Factory` 为 `{id: UUID, code: string, name: string}`，按工厂编码排序，仅含启用且有资格的工厂。
集团负责人获得全部启用工厂；工程师及厂管理员按持久化授权过滤；有效工程师零授权时返回空列表。

## GET /api/v1/factories/{factory_id}/assets

路径为 UUID。先校验调用者工厂资格，然后对启用工厂内的设备进行查询及计数。

| 查询参数 | 约束 | 默认/含义 |
|---|---|---|
| q | 字符串，最长 100 | 空；去首尾空白后匹配编号或名称，不区分大小写；`%`、`_` 按字面量搜索 |
| category | refrigeration / processing / utilities / other | 可选：制冷、加工、公用工程、其他 |
| status | pending / in_use / inactive / retired | 可选：待验收/安装、在用、停用/封存、报废；非实时状态 |
| limit | 整数 1–100 | 20 |
| offset | 整数 0–100000 | 0 |

未知/重复参数返回 422，包括查询中的 `factory_id` / `user_id`。
按 `asset_code, id` 稳定排序；`total` 为当前授权工厂及全部筛选条件下的总数。
200 返回 `{items: Asset[], total: integer, limit: integer, offset: integer, data_source}`。
没有匹配记录也是 200、`items: []`、`total: 0`，不能用空列表代替权限或后端错误。

## GET /api/v1/factories/{factory_id}/assets/{asset_id}

两个路径参数都为 UUID，无查询参数。先校验工厂资格，再以工厂与资产 UUID 双重过滤。
200 返回 `{asset: Asset, data_source}`。资产不在该范围内统一 404，不泄漏其真实工厂。

`Asset` 的允许返回字段如下；不扩展 ORM 对象或返回任意关联关系：

| 字段 | JSON 类型与约束 |
|---|---|
| id / factory_id | UUID 字符串 |
| asset_code / name | 字符串，厂内编号唯一、基础名称必填 |
| category / status | 上表枚举 |
| location | 字符串或 null，仅位置描述，不是机位实体 |
| manufacturer / model / serial_number | 字符串或 null |
| version | 正整数，本轮只读，预留后续并发更新 |
| created_at / updated_at | 含时区 ISO 8601 字符串 |

没有附件、图片、文件下载地址、员工信息、身份标识或会话摘要。
访问不存在的附件路径返回 404，POST 设备返回 405；没有隐含新增或导出功能。

## 错误及审计

| HTTP | code | 含义 |
|---|---|---|
| 401 | authentication_required | 缺少/无效/过期/撤销会话、停用用户；带 WWW-Authenticate: Bearer |
| 403 | permission_denied | 身份有效但没有管理角色、工厂授权或管理员授权配置不合法 |
| 404 | not_found | 已授权范围中不存在/已停用的工厂或设备；不披露其他工厂数据 |
| 422 | invalid_request | 额外/重复参数，或应用查询参数不合法 |
| 422 | FastAPI detail | 路径 UUID、类型、枚举、长度、数值边界等框架校验失败 |
| 503 | storage_unavailable | 数据库/事务/审计不可用；不返回驱动错误、SQL 或连接串 |

应用错误为 `{"error":{"code":"…","message":"固定安全提示"}}`，框架校验错误为
标准 `detail` 数组。客户端按状态映射页面，不显示后端任意错误内容。
成功及已认证授权拒绝事务内写审计（动作、操作者、范围、允许/拒绝、渠道、时间）；
不保存搜索文本、原始凭证或员工资料。审计失败不返回设备数据。
本轮尚无完整安全事件采集/审计查询 API。

## 只读 MCP 契约（未对外监听）

契约源：`application/mcp.py` 的 `TOOLS` 与 `ReadOnlyAssetMcp`。
两个工具均 `readOnlyHint: true`，输入 `additionalProperties: false`，不允许 `user_id`。
来源凭据由适配层独立传给 IdentityProvider，不能放在模型工具参数中。

| 工具 | 输入 | JSON 安全输出 |
|---|---|---|
| search_assets | 必填 factory_id；可选 q、limit、offset，边界及默认值同 HTTP | `{items: Asset[], total, limit, offset}` |
| get_asset_detail | 必填 factory_id、asset_id，均 UUID 字符串 | `Asset` |

MCP 当前不提供 category/status 参数；不返回 HTTP 特有的 data_source 包装。
查询输出与 HTTP 使用同一公共领域 DTO，UUID/时间转为字符串。
身份、无权限、未找到、无效输入、存储错误使用同一应用错误；网络 MCP 协议包装与官方认证
仍待 M1-02 实现，此处不声称已是可连接豆包的服务器。

例如以下仅为**合成契约输入**，并非真实工厂或资产，调用仍需可信服务端身份：

```json
{"factory_id":"10000000-0000-4000-8000-000000000001","q":"SYNTH-设备","limit":20,"offset":0}
```

实际 `DoubaoMcpIdentityProvider` 始终返回 `identity_provider_unavailable`（503 语义），不解析 JWT 充当认证。
测试替身只在隔离测试中使用，证明同一应用服务的跨厂 UUID 隔离、即时撤权与身份解绑拒绝。
官方签名/期限/身份来源校验的待办见 [身份适配设计](../architecture/IDENTITY_ADAPTERS_M1.md)。

# M1-03A 远程 MCP 契约

实际路径：`/mcp`，使用 `factory_ops.bootstrap:app` 的 FastAPI 组合入口。
默认关闭时 HTTP 503；明确配置后为 Streamable HTTP POST，JSON-RPC 2.0。
不是 `/sse`，不要求 Feishu 登录 Cookie。无状态，不分配 MCP Session ID。
仅初始化/发现/只读工具，无 prompts、资源下载、附件、写工具和匿名业务访问。

## 传输与认证

每个 HTTP 请求都须携带 `x-aily-jwt: <official-signed-jwt>`（无 Bearer 前缀）。
初始化、通知、工具发现、工具调用、GET/DELETE 均重新验签。
不接受 Cookie、Authorization 共享 Token、x-aily-user、x-aily-token 或 URL 参数替代身份。
签名、期限、租户、用户及 agent allowlist 校验见 [ADR-0008](../architecture/ADR-0008-remote-mcp-readonly.md)。

POST 请求须携带 `Content-Type: application/json`，`Accept: application/json, text/event-stream`。
兼容测试协议 `2025-11-25` 初始化与官方 SDK 默认 legacy 协商（使用当前 SDK 支持的握手版本）；
初始化后发送协商得到的 `MCP-Protocol-Version`。该 SDK 也带新版协议能力，真实客户端协商 **UNVERIFIED**。
通知接受时 202；工具响应为 application/json，无状态只读服务无长期订阅，认证后的 GET / DELETE
返回 405，Allow: POST。断连后新连接可重新初始化并重试只读查询；不提供 SSE 事件续传或审计去重。
请求体上限 16 KiB，分页最多 100 条。Host 必须匹配配置的公共 authority；若带 Origin 必须精确匹配
配置的 HTTPS origin，缺 Origin 的服务间请求可用。配置为 HTTPS 时拒绝未识别为 HTTPS 的请求。
所有 MCP 响应 no-store，Vary: x-aily-jwt，不写 Cookie。公开反代需限流和超时，见运行说明。

## 工具

`tools/list` 返回下面三项、完整 JSON Schema（拒绝额外参数）及只读/非破坏/幂等/封闭范围 annotations。
服务 instructions 与中文工具描述提示先发现工厂，再解析明确设备对象；有歧义先澄清，不能猜 UUID。
idempotentHint 表示业务查询无变更；每次查询仍会新增访问审计。

| 名称 | 输入 | 输出 structuredContent |
|---|---|---|
| `list_factories` | `{}` | `{items: [{id, code, name}]}`，仅当前授权的活动工厂 |
| `search_assets` | `factory_id: UUID`；可选 q（设备编号/名称，≤100 字）、limit（1–100，默认20）、offset（0–100000，默认0） | `{items: Asset[], total, limit, offset}` |
| `get_asset_detail` | `factory_id: UUID, asset_id: UUID` | 单个 Asset |

Asset 字段与现有应用 DTO 相同：id、factory_id、asset_code、name、category、location、manufacturer、model、
serial_number、status、version、created_at、updated_at。UUID 为字符串，时间为带时区 ISO8601。
location/manufacturer/model/serial_number 可为 null。无附件、账号资料、外部身份、监控测点和跨厂关联。
搜索是字面量匹配，百分号/下划线不扩大查询。空结果 total=0 不是失败或虚假数据。

自然语言路径：用户说“查询 A 厂 EQ-001”，AI 调用 list_factories，将名称明确匹配到该工具返回的 id，
以这个 id 和 q=EQ-001 查询，再将候选设备的 id / factory_id 传给详情工具。
同名工厂、多个候选设备或用户未指定工厂时先向用户澄清，不要求其手动提供 UUID。
客户端的 factory_id 仅表示请求目标，数据库授权与设备实际工厂仍须通过，不能作为权限凭证。

## 可复制的协议示例（占位符，不是真实数据）

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"isolated-review-client","version":"1"}}}
```

```json
{"jsonrpc":"2.0","method":"notifications/initialized"}
```

```json
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
```

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_factories","arguments":{}}}
```

成功工具结果同时包含 text JSON 和相同 structuredContent；不返回前端专用 data_source 包装。

## 错误

| 层次 | 响应 |
|---|---|
| JWT 缺失/无效/过期/错误租户/agent | HTTP 401，`{"error":{"code":"authentication_required"}}` |
| 未启用/缺配置 | HTTP 503，identity_provider_unavailable |
| 不可信 Origin / 不匹配 Host / HTTP 非 TLS | HTTP 403 / 421 / 403 |
| 不支持方法/过大请求体 | HTTP 405 / 413 |
| JSON 格式错误/未知 JSON-RPC 方法 | SDK 的协议错误；隔离验证分别为 HTTP400 / JSON-RPC -32601 |
| 工具发现时身份未绑定或角色未授权 | JSON-RPC -32001，安全的应用错误 code |
| tools/call 业务拒绝 | HTTP200 的 result.isError=true；content[0].text 中为下述 error 对象；无 structuredContent |

工具错误对象为 `{"error":{"code":"permission_denied","message":"无权访问请求的工厂范围"}}`。
code 包括 authentication_required（绑定/用户失效）、permission_denied、not_found、invalid_request、
storage_unavailable；未知内部故障使用 service_unavailable，不返回异常详情、SQL、签名、JWT 或参数回显。
在授权工厂中请求其他工厂设备 UUID 得到 not_found；直接请求未授权工厂得到 permission_denied。
未知 UUID 与其他工厂 UUID 不通过不同错误消息透露资源是否存在。

隔离拒绝证据与完整命令见 [验证记录](../delivery/M1_03A_VERIFICATION.md)。

# M1-02 身份及人员授权 API

认证部分（A）依赖 M1-01，人员授权部分（B）继续依赖 A。没有匿名注册管理员、飞书密钥配置页面、
通讯录同步、MCP 网络服务或业务写工具。只读资产契约继续见 [M1-01](M1_01_ASSET_READ.md)。

## 身份接口（M1-02A）

| 方法/路径（前缀 /api/v1） | 契约 |
|---|---|
| GET /auth/config | `{configured: bool, data_source, h5_method: "oauth_redirect"}`；不返回 App Secret 或人员 |
| POST /auth/feishu/start | JSON `{return_to, channel: "pc"/"h5"}`；精确 Origin；返回 authorization_url 并设置 HttpOnly 浏览器挑战 Cookie |
| GET /auth/feishu/callback | 唯一 state/code；消费挑战、服务端官方交换/核实身份，303 回已保存的内部 hash 目标或固定登录错误页 |
| GET /auth/me | 仅 Cookie；返回 `{id, display_name, role, status: "authorized"/"pending", factories: [{id,code,name}]}` |
| POST /auth/logout | Cookie + Origin + CSRF；事务撤销当前会话并审计，204 后清理 Cookie |

当前用户信息不包含令牌、会话摘要、CSRF 摘要或外部 open_id。新身份 role=null、工厂列表为空，
状态 pending；已有工程师没有有效工厂授权也是 pending。没有新建第四种管理角色。
UI 只是显示服务端结果，任何客户端角色、工厂或人员参数均不能授予权限。

Cookie：`__Host-factory_ops_session`（Secure/HttpOnly/Path=/）、
`__Host-factory_ops_oauth`（同上，五分钟）、`__Host-factory_ops_csrf`（Secure/Path=/、可读 nonce）；
均 host-only、SameSite=Lax。原 M1-01 测试模式 legacy Cookie 仅在未配置身份服务时兼容，
真实身份模式读取 __Host Cookie；Bearer 设备只读能力仍须数据库中的有效会话，不用于人员写接口。

写请求同时要求 `Origin == FACTORY_OPS_PUBLIC_ORIGIN` 和 `X-CSRF-Token` 与 CSRF Cookie 匹配，
再校验其摘要、会话、角色及工厂资格。GET 回调通过一次性 state/PKCE 防 CSRF，不接受自报 user_id。
auth 请求校验失败不会回显可能含凭证的请求体。

业务响应 `Cache-Control: no-store`、`Vary: Cookie, Authorization`、`Referrer-Policy: no-referrer`。
认证回调中的 code/state 属敏感材料，运行 ASGI 推荐 `--no-access-log`，代理不得记录查询串/请求体/Cookie。

| 状态/错误码 | 含义 |
|---|---|
| 401 authentication_required | 没有会话 Cookie |
| 401 session_expired | 无效、过期、撤销或被权限/身份状态淘汰的会话 |
| 401 invalid_login | 不可信、错误范围、过期或重放的登录凭证/挑战 |
| 403 permission_denied | 已识别身份被停用/解绑，或没有所需管理资格 |
| 403 csrf_rejected | Origin/CSRF 校验失败 |
| 422 invalid_request | 多余字段、类型或不安全回跳等参数错误 |
| 503 identity_provider_unavailable | 未配置或外部认证服务异常，失败关闭 |
| 503 storage_unavailable | 数据库/事务/审计异常，无内部错误细节 |

普通 API 错误为 `{error:{code,message}}`。回调将固定错误码带到安全登录页，
不回传飞书原始错误/令牌；已验证挑战的失败保留 PC/H5 原目标，重新登录须新 state 与新 code。

## 真实接入配置与边界

后端通过受控进程环境配置 `DATABASE_URL`、`FACTORY_OPS_PUBLIC_ORIGIN`（精确 HTTPS origin）、
`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_TENANT_KEY`，固定回调为
`<origin>/api/v1/auth/feishu/callback`。缺任何身份配置都不能启动成功认证。
前端用 `VITE_ASSETS_API_ENABLED=true VITE_IDENTITY_ENABLED=true` 开启功能。
前端不接收 Secret、长期 token 或平台会话原文，没有共享账号或假登录开关。

真实 App/租户权限、H5 无确认行为、人员变更事件及定期对账均 **UNVERIFIED**。
实际官方资料和 Cookie 设计见 [ADR-0006](../architecture/ADR-0006-feishu-platform-sessions.md)。
后续 B 的人员契约、数据库约束及初始化说明在独立依赖 PR 中补充。

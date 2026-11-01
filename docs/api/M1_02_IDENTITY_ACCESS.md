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
人员生命周期在 B 的独立依赖 PR 中实现，契约如下。

## 人员接口（M1-02B）

全部接口要求当前有效 Cookie 和服务端确认的集团负责人；工程师/厂管理员不能访问人员列表/历史。
参数中的 user_id 只是待管理目标，绝不替代操作者身份。写请求另须 Origin + 会话绑定 CSRF。

| 方法/路径（前缀 /api/v1） | 输入及响应 |
|---|---|
| GET /access/users | limit=20（1–100）、offset=0（0–100000）；`{items: Person[], total, limit, offset}` |
| GET /access/users/{user_id}/changes | 同上分页；`{items: ChangeRecord[], total, limit, offset}` |
| PATCH /access/users/{user_id} | `{expected_version, role, active, factory_ids, reason}`；返回 MutationResult |
| POST /access/users/{user_id}/revoke-sessions | `{expected_version, reason}`；返回 MutationResult |
| POST /access/users/{user_id}/unbind-feishu | 同上；停用该目标全部有效飞书绑定并撤销平台会话，返回 MutationResult |

Person：`{id, display_name, role, active, factories:[{id,code,name}], feishu_binding, version}`。
role 仅三种正式值或 null；feishu_binding 为 bound/unbound/none；不含 open_id、电话、邮件、令牌或摘要。
集团负责人范围显示为全部启用工厂，factory_ids 必须空；无角色亦必须空；工程师可零到多个，
厂管理员至多一个，零范围仍待授权。工厂必须真实存在且启用，重复工厂/额外字段均拒绝。

expected_version 是严格正整数，active 是严格布尔值，reason 去空白后为 2–300 字符。
版本过期、重复/无变化提交、删除最后启用集团负责人或不满足生命周期条件均返回 409 version_conflict。
写入成功才返回 `{user: Person, reauthentication_required: bool}`，操作者修改自己时须重新登录。
新权限只供后续有效认证使用；旧会话即使角色/工厂改回也不恢复。

ChangeRecord：`{id, actor_id, action, occurred_at, details:{before,after,reason}}`。
before/after 只含 role、active、factory_ids、feishu_binding、version，不包含员工显示名或身份凭据。
action 为 access.changed / access.sessions_revoked / access.feishu_unbound / access.bootstrap。
历史只读；操作者 UUID 为审计关联键。按时间降序及 ID 排序，工厂名称由当前目录展示，审计保留原 UUID。
不存在目标 404，非法输入 422，权限/CSRF 403，无效会话 401，审计/存储故障安全 503；
任何失败不会回传原始 SQL 或身份字段，也不会留下部分授权、会话撤销或成功审计。

离线首位集团负责人说明见 [ADR-0007](../architecture/ADR-0007-access-lifecycle.md)。
没有注册/初始化/任意身份重绑 HTTP 端点。受控停用当前可用，真实人员事件/定期对账仍 UNVERIFIED。

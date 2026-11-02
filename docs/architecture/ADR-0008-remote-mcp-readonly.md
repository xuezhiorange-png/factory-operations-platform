# ADR-0008：aily 身份与远程只读 MCP

- 状态：M1-03A 实现，Draft 评审；未部署、未接入正式租户。
- 基线：main `c37736070166d17b12b0058f7e32929e99872753`，PR #5/#6/#7 已合并。
- 官方协议核对日期：2026-11-02。真实 aily 租户与公网链路 **UNVERIFIED**。

## 决策

保留 FastAPI / Vue 3 / PostgreSQL 模块化单体、飞书 OAuth 和人员管理。
新增独立 `/mcp`，直接验证 aily 的请求身份，无需先建立飞书网页登录会话。
使用官方 Python SDK `mcp==2.3.0` 的 Streamable HTTP，选择无状态、有界 JSON 响应。
SDK 处理 JSON-RPC、初始化、能力发现与通知；适配层只负责身份、错误分类和调用应用服务。
不实现旧式 `/sse` 服务、不创建第二套人员权限、没有写工具或设备控制。

API 适配层 → `ReadOnlyAssetMcp` → `AssetQueries` → 既有 UOW / PostgreSQL。
SQL 同步操作在线程池中执行，每次调用独立事务。现有 `_principal`、厂范围过滤、DTO、审计提交
保持为唯一查询授权路径；MCP 不访问 ORM。工具发现也经过 `list_factories` 的身份/角色检查。
成功读取须先完成审计提交；数据库或审计不可用不返回设备数据。未知/失效身份不具备可写审计的
有效 actor，返回通用拒绝，不伪造用户审计。网关可记录不含身份材料的状态码计数。

## 官方身份协议与本地映射

来源：[aily MCP 使用](https://aily.feishu.cn/hc/1u7kleqg_73ahi33a)。该页明确支持
HTTPStreaming、自定义 MCP 的 JWT 开关、每请求 `x-aily-jwt`、HS256，以及编辑页生成的签名密钥。
密钥作为原始字符串使用，不做 Base64 解码。官方声明有效期 24 小时；页面仍带上线日期提示，
因此文档能力与真实租户可用性分开记录，不能据页面声明认为正式联调成功。

只接受 HS256，PyJWT 验签并要求 `exp`、`tenant_id`、`user_id`、`agent_id`。
tenant_id / user_id 按官方类型接收 JSON 整数，拒绝字符串、浮点、布尔值；Python 保留大整数精度。
exp 为未过期的整数时间戳，最多还剩 24 小时；服务器时间必须同步。
租户必须与受控配置相等，agent_id 必须在明确 allowlist 中。
不要求协议未定义的 iss / aud / scope / jti，不访问 JWKS，不从邮箱、部门、工号推断角色。
文档没有签名的工厂调用范围；可验证范围是租户 + 智能体 + 用户，业务厂范围仍由本地数据库决定。

既有 identity 唯一键映射为：

| 本地字段 | 值 |
|---|---|
| provider | `doubao_mcp` |
| issuer | 固定适配器来源命名空间 `https://aily.feishu.cn`，并非要求 JWT 带 iss |
| tenant_id | 已验证的 tenant_id，无损转换成十进制字符串 |
| app_id | 已验证的 agent_id，作为渠道内身份命名空间 |
| subject_id | 已验证的 user_id，无损转换成十进制字符串 |

不同智能体下的身份须分别确认并绑定到同一个内部用户，不能按姓名自动合并。
未绑定者查询失败，已绑定未授权者没有管理权限；工程师无厂授权只能得到空厂列表。
每次读取重新解析活动绑定、用户状态、当前角色/厂授权，不缓存 Principal 或接受客户端 user_id。
撤厂权、停用、解绑提交后的下一次查询立即受限；已开始的事务不是可远程撤销的流式订阅。

JWT 是可重复用于多个请求的短期身份凭证，不是一次性授权码；官方没有 jti，不能虚构单次消费。
窃取后在有效期内仍可能重放，必须依靠 HTTPS、令牌保密、数据库停用/解绑和必要时密钥轮换。
平台 Cookie 的“撤销会话”只撤销网页会话；紧急阻断 MCP 用停用用户或解绑 MCP 身份。
若仅停用后又启用同一绑定，尚未过期的旧 JWT 可按重新授予的当前权限访问；需要永久阻断时解绑或轮换密钥。
HS256 密钥持有者可签发任意身份，密钥与受控配置属高权限材料，不能分发给员工或通用客户端。

## 离线受控管理

`bootstrap_mcp_access` 是独立操作员 CLI，无 HTTP/MCP 注册或授权接口。
需要显式操作员开关、专用数据库访问及来自官方通道、验签成功的私有 JWT 文件。
创建待授权账号不会授予角色；首位负责人仅在没有活动负责人时、匹配账号版本下初始化一次。
已有负责人后，绑定/授权/解绑必须验证当前负责人身份，使用既有生命周期锁、版本控制和审计。
授权变更复用 `AccessService.apply_change`，保留最后负责人保护、管理员至多一厂和数据库约束。
身份附加至已有账号要求明确目标与当前版本，禁止无审批接管、重复绑定、移动或自动恢复已解绑身份。
人工误解绑的恢复需另行评审，不通过关闭校验或直接删除历史记录处理。

CLI 只在受控终端运行，不是新增 AI 写工具；不接收命令行明文 JWT。
凭证文件必须是操作员所有、无组/其他访问权限、非软链接的有界普通文件；不输出 JWT、签名密钥或员工信息。
绑定、角色变更与审计同事务失败回滚。审计表 append-only；操作者核实身份的依据保存在受控工单，
reason 使用工单编号，勿粘贴密钥、令牌或员工个人信息。

## 兼容与数据迁移

新增 Alembic revision：**无**。复用 factories / users / user_factory_access / external_identities /
assets / auth_sessions / audit_events / oauth_flows，当前 head 仍 `0003_access_lifecycle`。
设备 UUID、工厂隔离及现有 session / CSRF / Feishu 流程不变。前端和 M0.6 冻结文件不修改。
历史 M1 文档中的“豆包未监听”代表当时状态，本 ADR 和新契约描述当前能力。

关闭 `FACTORY_OPS_MCP_ENABLED` 即关闭 MCP；回退代码和依赖即可恢复合并前行为。
保留已生成的绑定与审计；不降级/清空数据库。既有 0003 降级保护会拒绝抹掉已填写的审计事实。

## 资料

- [MCP Streamable HTTP 规范](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [官方 Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [工具及错误契约](../api/M1_03A_REMOTE_MCP.md)
- [接入、日志、凭据和回滚运行说明](../operations/M1_03A_MCP_RUNBOOK.md)
- [隔离验证记录](../delivery/M1_03A_VERIFICATION.md)

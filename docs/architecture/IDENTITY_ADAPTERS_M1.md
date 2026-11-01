# M1 身份适配：平台会话、飞书与豆包

## M1-02A 更新

FeishuIdentityProvider 已实现官方授权码交换与用户信息校验，配置完整才启用；
目前未获得真实应用配置，真实认证 **UNVERIFIED**，默认通道关闭。
HTTP 已增加平台会话签发/退出、一次性浏览器挑战、PKCE、Origin/CSRF 保护及当前身份接口。
实现以 [ADR-0006](ADR-0006-feishu-platform-sessions.md) 和
[M1-02 API](../api/M1_02_IDENTITY_ACCESS.md) 为准。
以下保留 M1-01 的设计基线；其中“当前不可用”描述仅代表当时状态。
豆包仍不可用，不公开 MCP 监听，不形成第二套业务权限。

## 当前可执行范围

`IdentityProvider.authenticate(credential)` 返回内部身份引用，应用服务随后从数据库解析用户、
角色和工厂授权。HTTP 仅接收平台不透明会话，数据库只存摘要；本轮不提供会话签发、登录、
授权管理或测试登录 HTTP 端点。没有有效会话时，业务 API 返回 401。

隔离测试在测试专用 schema 中离线生成随机会话，用 HttpOnly Cookie 贯穿浏览器、API、
PostgreSQL；不向产品提供角色切换或身份输入框。测试会话文件位于 checkout 外的私有临时目录，
权限 0600，用完删除，不写 Git、日志或 CI artifact。浏览器测试不记录 trace、视频或截图。

`ExternalIdentity` 只供可信服务端适配器构造，不能从客户端 JSON/HTTP 头直接反序列化。
映射键为 `(provider, issuer, tenant_id, app_id, subject_id)`，完整相等且绑定启用，
才解析为内部用户；用户/本地角色/工厂授权仍需逐次校验。已验证外部身份不自动获得管理角色。

## FeishuIdentityProvider

代码位于 `infrastructure/identity/providers.py`，当前所有输入均返回
`IdentityUnavailable`，未安装飞书 SDK、未请求租户接口、未绑定员工。

后续 M1-02 应按获准使用的官方企业自建应用文档实现并评审：

1. 核实 PC 与工作台 H5 的官方授权码交换方式、应用与租户范围、身份标识语义；服务端交换凭证。
2. 验证一次性凭证、有效期、防重放；PC OAuth 的 state、回跳地址和浏览器会话绑定。
3. 验证应用、租户、身份来源，转换为明确的 `ExternalIdentity`；不用姓名、电话或部门猜身份。
4. 显式配置本地账号绑定与初次授权流程，不把通讯录成员自动授予工程师。
5. 签发随机高熵平台会话，摘要入库；生产 Cookie 需 Secure、HttpOnly、适当 SameSite、
   有限期限、轮换与退出撤销；写 API 引入前补齐 CSRF/Origin 防护。
6. 人员停用、离职、身份解绑与权限变更持久化留痕，事件验签、防重放与定期对账共同保障撤权。

官方租户能力、具体授权参数、事件权限及真实手机容器兼容性均为 **UNVERIFIED**。
本轮没有创建应用、操作正式租户、读取员工或发送消息。

## DoubaoMcpIdentityProvider

代码同上，当前始终拒绝认证；未公开 MCP HTTP/SSE/stdio 服务，未配置豆包连接。
`x-aily-jwt` 是后续凭证入口约定，不是本轮可信的已验证身份来源。

后续需先按豆包企业工作伙伴的官方集成文档确认以下协议，不能根据示例 JWT 猜测：

| 验证事项 | 必须具备的拒绝行为 |
|---|---|
| 官方签名算法、密钥/JWKS 来源、密钥轮换 | 不接受 unsigned/none、算法混淆、未知密钥；不从令牌自带 URL 任意取钥 |
| 可信发行者、受众及租户/应用范围 | 缺失或不符均拒绝，不能只解析 payload |
| exp、nbf、iat 及允许时钟偏差 | 过期、未生效或不合理期限拒绝；实际必选 claims 以官方协议确认 |
| 身份来源与企业用户标识语义 | 校验官方来源并映射完整绑定键；不接受客户端 user_id 或 AI 指定操作者 |
| 防重放、请求/会话绑定、转发边界 | 依据官方能力设计；不信任任意代理透传的用户头 |
| 失败和凭据处理 | 失败关闭、限流、脱敏；不记完整 JWT，不把身份凭证回传给模型 |

具体算法、JWKS 地址、issuer/audience 值、claim 字段及官方生产连通性均为 **UNVERIFIED**，
本仓库没有编造官方端点或实现“解析即登录”。凭据与公钥信任配置必须来自受控环境，
任何 AI/客户端 `factory_id` 都要再次经过本地授权，`user_id` 不属于工具输入。

## 共用应用服务与 MCP 契约

`ReadOnlyAssetMcp` 接受可信 `IdentityProvider` 和 `AssetQueries`，验证参数后调用
`search_assets` / `get_asset_detail`。不会创建 SQLAlchemy Session、查表或跳过工厂校验。
详情的 UUID 必须位于已授权工厂；总数及搜索结果同样限定范围。数据序列化只包含公共设备 DTO，
UUID/UTC 时间为 JSON 字符串，不返回身份引用、附件或内部用户资料。

生产适配器当前不可用。契约测试用显式的 `SyntheticVerifiedProvider` 测试替身验证服务复用、
跨厂拒绝、撤工厂授权、解绑身份、无效参数和未知写工具拒绝；此替身不在运行组合入口中。
HTTP/MCP 的完整输入输出见 [只读契约](../api/M1_01_ASSET_READ.md)。

审计 `channel` 当前为 `api / doubao_mcp`；飞书 H5 使用普通 API，不另造一套业务授权。
将来增加网络 MCP 封装时，只负责官方身份校验、协议错误映射和结构化输出，
必须继续复用应用服务；`readOnlyHint` 只是客户端提示，实际只读由仅有两个查询用例保证。

## 正式可用前的缺口

本轮具备会话校验及工厂隔离基础，不具备真实用户登录和会话签发运维流程。
尚需官方协议确认、真实身份适配、管理授权事务/审计、会话吊销事件、最小数据库权限、
可信同源反向代理、TLS、日志脱敏/保留及备份恢复演练。未经另行授权不部署、不接正式租户。
任务清单见 [M1-02 / M1-03](../delivery/M1_NEXT_TASKS.md)。

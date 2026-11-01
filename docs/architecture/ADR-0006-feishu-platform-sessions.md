# ADR-0006：飞书身份与平台会话（M1-02A）

任务 `FACTORY_OPS_M1_02_FEISHU_IDENTITY_AND_ACCESS`，拆分 A（认证/会话）与 B（人员授权/生命周期）。
开始时重新读取 GitHub：PR #5 仍为 Draft、未合并，最新 HEAD 为
`bc6f77bc4a4ea2ed7db8730fbfd92a2ab0e7f007`；A 从其远程 HEAD 创建，堆叠到 M1-01。
没有 Ready、合并或编辑 PR #5；B 继续堆叠在 A 上。

## 官方资料与选型

2026-11-01 阅读飞书官方页面及其 `.md` 版本：

- [获取授权码](https://open.feishu.cn/document/authentication-management/access-token/obtain-oauth-code)
- [获取 user_access_token](https://open.feishu.cn/document/authentication-management/access-token/get-user-access-token)
- [获取用户信息](https://open.feishu.cn/document/server-docs/authentication-management/login-state-management/get)
- [H5 免登说明](https://open.feishu.cn/document/client-docs/h5/development-guide/step-3)

PC 与 H5 采用官方网页 OAuth 重定向流程，使用固定授权地址
`https://accounts.feishu.cn/open-apis/authen/v1/authorize`。H5 从 `/#/m/login?auto=1`
进入同一流程；官方允许客户端内已授权场景免确认跳转，但真实容器行为仍 UNVERIFIED。
本轮不混用 `requestAccess` 授权码，不加载 JS SDK；后续如改 SDK，需另测协议及兼容性。

采用官方文档明确配对的 PKCE S256 + `authen/v2/oauth/token`，随后查询
`authen/v1/user_info`。官方 token 页同时说明 v3 迁移，而授权页目前注明 PKCE 暂配 v2；
本轮保持这一文档明确的组合，始终正确同时发送 challenge 和 verifier，不依赖 v2 对错误 PKCE 的宽容。
实际企业应用许可、v3 切换、发布范围和设备容器均需沙箱复核，不能据文档声称已接通租户。
无需通讯录、手机号、部门或 offline_access 权限；不持久化飞书 access/refresh token。

## 信任路径

1. 浏览器同源 POST 发起登录，服务端检查精确 HTTPS Origin；不信任 Host/Forwarded 或客户端回调地址。
2. 创建随机 state 与浏览器秘密。数据库只保存摘要、五分钟期限、渠道及白名单内的原目标路由。
   浏览器秘密用 Secure/HttpOnly、SameSite=Lax、host-only、Path=/ 的 `__Host-factory_ops_oauth` 保存，
   同时作为 PKCE verifier，S256 challenge 发给飞书。
3. 回调要求唯一的 state/code，与 Cookie 摘要匹配。行锁消费 state，唯一 code 摘要阻止重放；
   在外部请求之前提交保留记录，网络失败后必须重新发起登录。
4. 服务端用配置的 App ID/Secret、固定 redirect_uri、code/verifier 换取令牌。固定官方 HTTPS
   端点、TLS 默认校验、8 秒超时、不跟随重定向、不重试交换、不接受客户端身份头。
5. 使用刚获得且尚有效的令牌获取用户信息，强制租户匹配，保留可信 open_id 与应用/发行者范围。
   应用绑定由服务端 client_id/Secret 交换保证；任何明确返回的错误应用标识也会被拒绝。
   上游失败只返回固定安全错误，不回显凭据、SQL、原始异常或个人资料。
6. 按完整外部身份键查找本地绑定。首次有效身份建立 `role=NULL` 的待授权用户和绑定；
   不从姓名、手机号、部门或飞书可见性授予管理角色。停用/解绑身份不自动重新创建。
   名称只作显示，可保存在独立业务库，不用于授权，也不写入公共源码/日志。
7. 同事务写登录审计并签发 256-bit 随机平台会话；只保存 SHA-256 摘要。
   会话绑定当前授权版本与外部身份。旧浏览器会话在新登录时撤销。
8. 固定同源 hash 路由回跳；拒绝协议相对地址、外部地址、转义字符、fragment、API/登录循环目标。
   有效挑战后的登录失败也保留 PC/H5 的原目标；无可信挑战时回到固定安全登录页。

## Cookie、会话与写请求

平台会话为 `__Host-factory_ops_session`，Secure、HttpOnly、host-only、Path=/，默认 8 小时；
Cookie 不进入 JSON、localStorage、sessionStorage 或 URL。生产入口必须 HTTPS。
本轮选 SameSite=Lax：独立同源 PC 与飞书顶层 H5 重定向，允许 OAuth 回调带挑战 Cookie。
未支持跨站 iframe/第三方 Cookie 场景，不为了兼容未知环境关闭 Secure 或放宽成 None。
实际反向代理、TLS、H5 容器及 Cookie 限制仍 UNVERIFIED。

CSRF nonce 另用 `__Host-factory_ops_csrf` Cookie（Secure、SameSite=Lax，可读）保存，数据库仅存摘要。
所有受 Cookie 保护的写请求须精确 Origin、Cookie/Header nonce 一致、摘要与当前有效会话匹配。
nonce 不是平台身份凭据，不可代替会话。登录发起为匿名同源 POST，依靠 Origin；
跨站 OAuth GET 回调只依靠一次性浏览器绑定 state/PKCE，不豁免人员管理写请求。

每次读取会话均检查签发时间、过期、撤销、用户 active、auth_version 及绑定 active/归属。
角色和工厂仍从 PostgreSQL 逐次读取。B 实现角色/调厂/停用/解绑事务、授权版本递增与主动撤销。
退出须 CSRF/Origin，通过后撤销当前会话、追加审计、删除 Cookie；失败不显示“退出成功”。

## 数据与迁移

`0002_feishu_sessions` 添加 `oauth_flows`；users 增加 display_name、auth_version、version；
auth_sessions 增加 auth_version、外部身份外键、csrf_hash。保持原有资产 UUID/表和只读接口。
不自动迁移、不创建首位管理员、不导入员工；受控首位集团负责人由 B 的离线流程实现。
审计失败时新用户/绑定/会话同事务回滚，已消费的登录挑战保留，防止异常重放。

降级先撤销所有平台会话，再删除新增结构，避免旧代码忽略绑定/版本校验后继续接受新会话。
任何有数据的环境先停止认证/写入，评审备份及前向修复；不能把隔离库 downgrade 当正式恢复方案。

## 验证与限制

测试使用独立 PostgreSQL schema、官方 HTTP 形状的 MockTransport、合成身份，真实凭据通道默认关闭。
HTTPS 浏览器用临时本地证书，只有测试浏览器接受该自签证书；访问飞书的后端 TLS 校验从未关闭。
无 trace/视频/HTML/认证状态 artifact。显式截图只捕获带合成标记的最终页面，排除回调 URL。
测试记录见 [M1-02A 交付](../delivery/M1_02A_VERIFICATION.md)。

真实飞书认证 **UNVERIFIED**；未获 App ID/Secret/租户配置，未联系正式租户。
人员事件/通讯录权限未取得，不接收或宣称同步成功。公开上线前仍需入口限流、挑战留存清理策略、
日志去查询串、最小 DB 权限、TLS/代理及备份演练。M0.6 冻结文件与源 SHA 均不修改。

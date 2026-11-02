# ADR-0009：MCP 隔离 HTTPS 网关与最小数据库权限

状态：M1-03B 阶段一实现；真实豆包联调尚未执行。
基线：main `bfa5adeb56c30cedd5d804b0dd17e79b3457ae5b`，PR #8 已合并。

## 沿用现有应用

不改 `/mcp`、JWT provider、AssetQueries、三角色、厂权限或数据库业务模型。
新增的 Docker / Nginx / PostgreSQL 配置只服务独立合成测试环境，不接入飞书自建应用。
MCP 仍为 Streamable HTTP、三项只读工具，无写工具、控制命令或匿名查询。
没有改 PC/H5、冷库/PLC/规划 MCP，也不改 M0.6 冻结预览。

## 网络与信任边界

Nginx TLS → 私有 gateway 网络 → FastAPI → 私有 database 网络 → PostgreSQL17。
只有 Nginx 连接独立 ingress bridge 以发布端口；默认仅 `127.0.0.1:<随机测试端口>`。
FastAPI 与数据库无 ports、无 host networking、无外部/生产数据卷，gateway / database 均 internal。
没有将 Docker socket 挂入服务。自动测试只操作唯一的 `mcp03b_<随机值>` 项目并在结束后销毁。

Nginx 只代理精确 `/mcp`；`/docs`、`/openapi.json`、`/api`、`/sse`、`/mcp/` 等一律404。
Host 须匹配受控 authority，转发固定 Host 与 HTTPS scheme，覆盖客户端 X-Forwarded-Proto / For，
保留 Origin、x-aily-jwt 和 SDK 协议/Accept 头。后端只信任 gateway 地址 `172.30.83.2`，不使用 `*`。
来自其他内部容器伪造的 HTTPS 转发头也会被拒绝。变更网段时必须同步改这条固定信任配置。
IPv4 固定网段适用于单个隔离测试项目；同机并行启动需另行规划网段及信任地址。

代理设置16KiB请求体、头/体超时、上游连接/读写超时、每来源 IP 10r/s（burst20）和8条并发连接，
超额429 / Retry-After。它不是经过验签的“每员工配额”；aily 共享出口可能触发同一个 IP 配额，
实际生产容量和限流值仍 UNVERIFIED，不可把该起点当成压测结果。

## 数据库权限

测试库固定 `factory_ops_mcp_synthetic`，数据库 shared comment 标记为
`FACTORY_OPS_M1_03B_SYNTHETIC_ONLY`，独立 factory_ops schema，由迁移账号拥有。
撤销 PUBLIC 的数据库与 public schema 权限。所有密码独立生成，不写 Compose environment 或 argv。

| 角色 | 权限与持有者 |
|---|---|
| factory_ops_bootstrap | 仅 DB 初始化容器持有；创建其他角色与私有 schema，不提供给 API |
| factory_ops_migrator | 非 superuser、无建库/建角色/复制能力；拥有测试 schema，仅显式迁移/合成数据操作使用 |
| factory_ops_runtime | SELECT factories/assets/users/user_factory_access/external_identities，INSERT audit_events；无业务写、DDL、身份改写、审计读改删或角色切换 |
| factory_ops_operator | 受控离线人员管理：查询必要表，INSERT/UPDATE users/identities，INSERT/DELETE厂授权，追加审计；为既有撤会话触发器仅授予 auth_sessions 的 user_id/revoked_at SELECT 和 revoked_at UPDATE |

API 没有迁移或操作员凭据，也没有离线初始化开关。操作员工具使用原有应用服务和工厂/角色约束，
不建立第二套业务权限。运行账号设置5秒 statement_timeout、2秒 lock_timeout、10秒闲置事务期限。
数据库连接角色是服务权限，不是产品管理角色；users.role 仍只有集团负责人、工程师、加工厂设备管理员三种。
这些数据库权限限制服务进程的能力，工厂行范围仍由原 AssetQueries 判断，不虚称新增 RLS。

迁移显式执行现有 Alembic head；M1-03B **没有新增业务迁移**。
角色、私有 schema 与 GRANT 是新测试库的部署配置，不能直接套用到现有或生产数据库。
合成 seed 仅接受精确数据库名、标记及空 factories/assets/users，拒绝重复导入或覆盖已有资料。

## 凭据、日志与证据

镜像以 UID10001 运行 API，Nginx UID101；只读 rootfs、drop ALL capabilities、no-new-privileges、
有界 tmpfs。文件 secret 按服务分别只读挂载，不进入镜像或 Docker Config.Env；只有 CA 以 build secret
供 pip 使用，不关闭 TLS 校验。具体本地文件权限取舍见运行说明。

网关访问日志固定为 time / request_id / route（mcp 或 blocked）/ jwt_present（布尔）/ status / seconds。
不记录 URI query、请求体、Header 值、IP、员工标识、签名密钥和 JWT；拒绝带 query 的 MCP 请求。
关闭可能含原始 URI 的 Nginx error log、Uvicorn access log，不开启 HTTP/SDK/SQL DEBUG。
初次发现缺 JWT 可保留 jwt_present=false + 401 证据，不能从日志取出 JWT 或反推出用户。
应用日志故障可通过状态码与有权限的私有数据库审计调查，不能为诊断临时打开全量请求日志。

操作员诊断只接受私有凭证文件，经过官方 provider 验签后输出算法、字段类型、剩余秒数，
不输出字段值、原始令牌或密钥，没有 HTTP 凭证捕获接口。
CI 只上传经白名单构造的状态 JSON，不上传命令日志、secret、证书私钥、身份文件或容器日志。
每项检查标记 PASS / FAIL / BLOCKED / UNVERIFIED；本机 PASS 不代表真实豆包已接入。

## 参考与交付

- [当前 MCP 架构](ADR-0008-remote-mcp-readonly.md)、[契约](../api/M1_03A_REMOTE_MCP.md)
- [Nginx 限流官方文档](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
- [Uvicorn 信任转发头设置](https://www.uvicorn.org/settings/)
- [阶段一运行与阶段二接入说明](../operations/M1_03B_MCP_INTEGRATION.md)
- [状态及测试证据](../delivery/M1_03B_VERIFICATION.md)

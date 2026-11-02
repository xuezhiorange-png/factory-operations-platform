# M1-03B 联调准备与验证状态

TASK_ID：FACTORY_OPS_M1_03B_MCP_LIVE_INTEGRATION。
分支：`codex/m1-03b-mcp-live-integration`，独立 Draft PR，等待评审。
基线 main `bfa5adeb56c30cedd5d804b0dd17e79b3457ae5b`，开工重新确认 PR #8 merged；
[基线 CI 41382168964](https://github.com/xuezhiorange-png/factory-operations-platform/actions/runs/41382168964) PASS。
本轮只完成阶段一；阶段二真实豆包连接未执行，不能声称已成功接入。
最终 HEAD、PR 链接和该 HEAD 的 Actions 结果在 Draft PR 描述中记录，避免文档自引用 SHA。

## 状态定义

PASS：已实际执行且符合预期。FAIL：已执行但不符合预期。
BLOCKED：缺少权限、配置或前置条件而无法执行。UNVERIFIED：外部行为尚未取得实测证据。
HTTP200 中的 MCP isError 是业务拒绝，不是查询成功；负向测试正确拒绝才记 PASS。

## 阶段一本机结果（2026-11-02）

Python3.12 / Docker28 / Compose2.40 / PostgreSQL17 / Nginx1.28 / 官方 MCP SDK2.3。
真实进程、TLS、反代与数据库，没有把 MockTransport 或纯 ASGI 用例当作网关联通证明。
只使用合成工厂、设备、账号与随机测试密钥；证书显式加入客户端信任，不关闭 TLS 验证。
**26 PASS，0 FAIL，0 本机 BLOCKED。** 以下名称与 CI 状态 JSON 一致。

| 检查 | 状态 | 证据 |
|---|---|---|
| isolated_postgresql17_and_migrations | PASS | 独立标记空库，既有 Alembic head，合成 factories/assets |
| controlled_offline_identity_bootstrap | PASS | 原离线 CLI：pending→首位负责人→审批绑定/三角色授权，事务落库 |
| value_free_jwt_diagnostics | PASS | 合成签名验签；只输出 HS256、字段类型与剩余期限 |
| network_and_secret_isolation | PASS | 实际容器绑定仅127.0.0.1 HTTPS；API/DB无端口发布，私有网络、非root/只读rootfs、文件secret |
| public_template_render_only | PASS | 仅以文档保留IP渲染模板，无启动/公网部署 |
| least_database_privileges | PASS | 表权限矩阵与12类实际 SQL 拒绝；无 DDL/业务写/身份改写/审计读改删/角色切换 |
| missing_jwt_discovery_refused | PASS | tools/list 缺 JWT 时401；不开放匿名发现 |
| invalid_jwt_refused | PASS | 无效、过期、错误租户/agent/签名均401 |
| shared_identity_refused | PASS | 共享 Bearer 与明文 x-aily-user 不可代替 JWT，401 |
| only_mcp_route_exposed | PASS | docs/openapi/api/health/sse/尾斜杠等均404 |
| forwarding_and_origin | PASS | 错 Host421、错 Origin403；外部伪造转发头被覆盖，正常 TLS 请求成功 |
| untrusted_forwarder_refused | PASS | 其他内部容器伪造 HTTPS scheme，后端403 |
| stateless_http_methods | PASS | 带合法JWT的GET/DELETE405，POST正常 |
| body_and_query_limits | PASS | 大于16KiB请求413；带query请求400，不回显敏感哨兵 |
| unbound_and_pending_refused | PASS | 未绑定 authentication_required；待授权 permission_denied，无 DTO |
| three_roles | PASS | 集团2厂，工程师/管理员各1厂，按服务端当前授权返回 |
| cross_factory_and_uuid_refused | PASS | 跨厂 permission_denied；A厂传B厂设备UUID not_found |
| grant_revocation_immediate | PASS | 同一JWT跨厂授予后可查；撤权后的下一次请求拒绝 |
| account_disabled_refused | PASS | 受控停用后，同一JWT authentication_required |
| identity_unbound_refused | PASS | 受控解绑后，同一JWT authentication_required |
| audit_failure_closed | PASS | 撤 runtime 审计INSERT权限后 storage_unavailable，无 DTO；恢复后可查 |
| database_disconnect_recovery | PASS | 停止独立PG后安全拒绝；重启后新查询恢复 |
| official_client_tls_and_reconnect | PASS | 官方SDK经Nginx TLS，两次新连接均发现三工具并完成按工厂/编号定位及详情，无附件/账号数据 |
| edge_rate_limit | PASS | 并发突发出现429/Retry-After，其他缺JWT请求401，无查询成功 |
| redacted_logs | PASS | 固定6字段日志、JWT presence布尔值；无令牌、已知密钥/密码、查询字符串、私钥 |
| owned_stack_cleanup | PASS | 仅删除本轮唯一随机项目的容器、网络、数据卷；临时凭据/证书清理 |

本机命令：

```bash
.venv/bin/python scripts/mcp_gateway_test.py --report /tmp/mcp03b-status.json
.venv/bin/ruff check backend scripts deploy/mcp-test
python scripts/check_docs.py
```

Ruff、Actions actionlint、diff/文档本地链接在交付前检查。GitHub Actions 增加独立 MCP gateway job
重复上述26项，保留原后端165项与 PC/H5 90项及三种构建；远程结果以最终 HEAD 的实际检查记录为准。
CI只上传脱敏状态JSON，不上传容器/命令日志、JWT、secret目录、私钥或认证浏览器trace。

## 阶段二真实豆包状态

| 检查/前置 | 状态 | 原因或下一步 |
|---|---|---|
| 公网测试部署明确授权 | BLOCKED | 用户尚未授权部署；本轮未执行 |
| 独立测试主机/IP、隔离域名、受信TLS及防火墙 | BLOCKED | 未提供，不复用冷库或冻结Pages |
| 企业工作伙伴管理员配置与合成测试账号 | BLOCKED | 未取得，不改变正式租户 |
| 平台签名密钥、tenant_id、agent_id受控配置 | BLOCKED | 未提供；不得发到聊天/GitHub，不用本机自造密钥替代平台配置 |
| 首次添加/工具发现是否发送 x-aily-jwt | UNVERIFIED | 本机401/presence=false证明本平台拒绝策略，不能证明真实平台请求行为 |
| 真实 JWT 算法、字段类型、期限及范围 | UNVERIFIED | 需官方签发的获准测试账号凭据；不虚构 iss/aud 等字段 |
| 真实凭据安全导出、受控绑定与首位授权 | UNVERIFIED | 无平台调试权限/流程实测，不新增公开捕获接口 |
| 真实豆包三个工具执行、无权限/跨厂/撤权/停用/解绑 | UNVERIFIED | 目前只有本机独立服务+合成身份的端到端结果 |
| 真实豆包断连恢复、提示及自然语言顺序/消歧 | UNVERIFIED | 未连接正式客户端；按运行说明执行后逐项填PASS/FAIL |
| 公网客户端协议协商、共享出口限流/容量 | UNVERIFIED | 本机限流通过不代表实际平台负载或生产容量 |

若首次发现没有 JWT，记录 request_id / 时刻 / jwt_present=false / 401。
兼容性未通过时保持失败关闭，禁止匿名业务查询、共享 Token 或伪造员工身份。

## 变更与迁移

- 新增 deploy/mcp-test 的 Dockerfile、构建过滤、Compose、本机/公开评审模板、Nginx、DB初始化、
  文件secret启动器、隔离数据库工具与操作员诊断。
- 新增 scripts/mcp_gateway_test.py；CI新增独立本机网关验证，忽略本地输出并只上传状态JSON。
- README、文档索引/check_docs、ADR-0009、本运行/交付记录补充入口。
- **新增业务数据库迁移：无。** 使用既有 0003_access_lifecycle；新数据库部署角色/GRANT不用于现有数据库。
- backend/src、现有 MCP/Feishu/权限/应用服务、frontend 与冻结文件均未修改。

## 风险与回滚

真实平台兼容性尚未验证，是当前主要未完成项。HS256 密钥持有者可签发身份，JWT有效期内可重放，
人工离职停用需要责任人；没有事件同步就不能假称已自动撤权。
per-IP限流可能把 aily 共享出口计入同一配额，公网参数须经隔离联调确认。
日志脱敏以减少排障内容为代价，不能为排障开启全量Header/body日志。
本机Compose文件secret依赖宿主0700父目录；长期环境应使用受控secret存储与正确UID权限。

回滚：关闭该测试网关入口和API，回退配置/镜像；保留长期评审库的审计与授权事实，不降级/清空既有数据库。
自动验证可销毁它创建的临时合成项目；不执行全局清理，不影响其他项目。
详情与用户需完成的步骤见 [M1-03B运行说明](../operations/M1_03B_MCP_INTEGRATION.md)。
保持 Draft，不 Ready、不合并、不部署。

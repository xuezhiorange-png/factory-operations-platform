# M1-03A：接入及上线前运行方案

本轮只开发、隔离验证；以下为后续经明确授权才可执行的接入/部署方案。
**未部署公网服务、未连接正式豆包租户、未导入真实人员或设备。**
真实 aily JWT 下发、租户 UI、实际用户 ID 类型、签名密钥强度、agent_id、客户端协商和公网 HTTPS 均 **UNVERIFIED**。
当前没有可供真实租户连接的服务地址。占位地址与配置不能被描述为已上线服务。

## aily 官方接入步骤

依据 2026-11-02 核对的 [MCP 使用](https://aily.feishu.cn/hc/1u7kleqg_73ahi33a)：

1. 先经授权准备独立评审域名和隔离 PostgreSQL，仅放合成数据。默认关闭业务入口，禁止共用冷库服务。
2. 企业工作伙伴 → MCP → 添加自定义 MCP，填写名称、描述、请求地址；选 HTTPStreaming /
   Streamable HTTP 对应选项（真实租户标签需核实），开启“JWT身份令牌”，保存配置。
3. 在 MCP 编辑页面获取平台生成的 identityJWTSecret，由授权操作员直接注入服务端 secret 管理器。
   不 Base64 解码，不将其填成客户端共享 user Token；员工不持有签名密钥。
4. 核实受控 tenant_id、实际 agent_id 并配置 allowlist。服务端接受官方整数 tenant_id/user_id，
   如真实租户返回不同类型或无 JWT，保持关闭并核实协议，不能回退到邮箱/明文身份头/共享 Token。
5. 完成下面的受控绑定与首位授权，再用两位合成身份分别测试工厂范围和拒绝访问。
   aily 首次探测若在尚无用户 JWT 的管理上下文进行，可能得到 401；该行为 **UNVERIFIED**，
   不为使“连接成功”而加匿名工具目录或业务查询例外。
6. 在合成用户对话中提出“列出我能访问的工厂”“查某厂某编号设备”，检查工具发现、名称消歧、详情、
   错误恢复和断连重连；真实平台联调后才把对应状态从 UNVERIFIED 改成实测结果。

可复制到配置工单/UI 的文字（替换域名；不含密钥）：

```text
名称：加工厂设备运维（只读·隔离评审）
描述：查询本人有权访问的加工厂和设备基础台账。先用 list_factories 匹配工厂名称，再用 search_assets 按编号或名称定位，最后用 get_asset_detail 查询明确设备。有歧义先澄清。不控制设备、不查询冷库监控、不写业务数据。
请求地址：https://YOUR-ISOLATED-REVIEW-HOST/mcp
传输方式：HTTPStreaming / Streamable HTTP
JWT身份令牌：开启（每个请求自动发送 x-aily-jwt）
自定义Header：留空；不要填写员工 user_id 或共享身份 Token
```

这是官方 UI 字段清单，不虚构其 JSON 导入格式。请求 URL 是单个 /mcp 路径，没有 /sse 或查询凭据。

## 服务端受控配置

`.env.example` 仅列占位字段；应用不自动读取 .env。由受控环境向后端进程注入：

```text
DATABASE_URL=postgresql+psycopg://<dedicated-user>:<secret>@<isolated-db>/<platform-db>
FACTORY_OPS_MCP_ENABLED=1
FACTORY_OPS_MCP_PUBLIC_ORIGIN=https://YOUR-ISOLATED-REVIEW-HOST
AILY_TENANT_ID=<verified-numeric-tenant-id>
AILY_ALLOWED_AGENT_IDS=<approved-agent-id-1>,<approved-agent-id-2>
AILY_IDENTITY_JWT_SECRET=<platform-generated-raw-signing-secret>
```

配置完整才启用；无 DATABASE_URL 或未开开关时 /mcp 返回503；配置格式错误时启动拒绝且错误不回显配置值。
签名密钥要求至少32 UTF-8字节；如平台生成密钥达不到要求，先核实和评审，不能随意换成自造共享密钥。
此通道不需要 FEISHU_APP_ID / SECRET，不签发网页会话，也不改变现有 PC/H5 登录行为。
数据库迁移仍显式执行既有 Alembic head，M1-03A 没有新增 DDL。

## 受控离线绑定及授权

操作员需要独立主机/终端的 DB 权限、人工身份核对工单和官方签发的短期用户 JWT。
令牌只能通过获准的受控诊断流程直接写入临时 secret 卷，0600、操作员所有；不得粘贴到 GitHub、
聊天、shell 参数/历史、curl verbose 或访问日志。真实租户中获取及销毁该临时凭证的操作流程 **UNVERIFIED**；
本轮仅用合成 JWT 验证 CLI，不读取正式员工请求。不要新增公开 token 捕获或“登录成功”测试接口。

仅在操作员命令进程设置 `FACTORY_OPS_ALLOW_OFFLINE_BOOTSTRAP=1`，不带到 Web 运行环境。
命令要求 `--confirm-offline-change`、reason（工单号）与当前版本。命令只输出内部 user_id 和 version，
输出仍在受控终端保管。以下变量是操作员的私有路径、DB 当前 UUID/版本和工单编号：

```bash
# 无活动负责人时，只能创建新的待授权账号，不接管已有人员。
python -m factory_ops.bootstrap_mcp_access bind \
  --identity-file "$LEAD_JWT_FILE" --reason "$APPROVAL_REFERENCE" --confirm-offline-change

# 用上一步返回的 version 初始化首位负责人；后续重复初始化拒绝。
python -m factory_ops.bootstrap_mcp_access bootstrap \
  --identity-file "$LEAD_JWT_FILE" --expected-version "$PENDING_VERSION" \
  --reason "$APPROVAL_REFERENCE" --confirm-offline-change

# 已有负责人后，新增人员必须验证负责人 JWT；新人员仍是 pending。
python -m factory_ops.bootstrap_mcp_access bind \
  --identity-file "$EMPLOYEE_JWT_FILE" --actor-identity-file "$LEAD_JWT_FILE" \
  --reason "$APPROVAL_REFERENCE" --confirm-offline-change

# 若原有负责人仅关联 Feishu、尚无任何活动 MCP 负责人，操作员凭明确审批进行首次关联。
# 目标必须是已有活动 group_lead；不升角色，版本不匹配或已有 MCP 负责人时拒绝。
python -m factory_ops.bootstrap_mcp_access bind \
  --identity-file "$LEAD_JWT_FILE" --target "$EXISTING_LEAD_INTERNAL_ID" \
  --expected-version "$EXISTING_LEAD_VERSION" --confirm-initial-lead-link \
  --reason "$APPROVAL_REFERENCE" --confirm-offline-change

# 同一内部账号关联另一已核实身份时，bind 额外传 --target 与 --expected-version。
# 授予工程师 A/B 两厂；factory 参数表示完整替换后的授权集合。
python -m factory_ops.bootstrap_mcp_access grant \
  --identity-file "$LEAD_JWT_FILE" --target "$EMPLOYEE_INTERNAL_ID" \
  --expected-version "$EMPLOYEE_VERSION" --role engineer \
  --factory "$FACTORY_A_ID" --factory "$FACTORY_B_ID" \
  --reason "$APPROVAL_REFERENCE" --confirm-offline-change

# 紧急停用：使用当前版本；不传 factory 即清空所有显式授权。
python -m factory_ops.bootstrap_mcp_access grant \
  --identity-file "$LEAD_JWT_FILE" --target "$EMPLOYEE_INTERNAL_ID" \
  --expected-version "$EMPLOYEE_CURRENT_VERSION" --role pending --disable \
  --reason "$APPROVAL_REFERENCE" --confirm-offline-change

# 解绑 MCP 身份（不删除历史），使用新的当前版本。
python -m factory_ops.bootstrap_mcp_access unbind \
  --identity-file "$LEAD_JWT_FILE" --target "$EMPLOYEE_INTERNAL_ID" \
  --expected-version "$EMPLOYEE_CURRENT_VERSION" \
  --reason "$APPROVAL_REFERENCE" --confirm-offline-change
```

工厂 UUID 由负责人 list_factories 或受控数据库只读核对获得，不交给普通用户记忆。
相同官方身份重复绑定、自动重启已解绑记录、版本冲突、最后活动负责人降权/停用均拒绝。
离线授权不增加匿名接口或 MCP 写工具。授权事实与人员生命周期继续存 PostgreSQL；操作同事务审计。
JWT 过期后命令拒绝，需重新取得官方短期凭证；不能用签名密钥为真实员工伪造身份代替官方验真。

## 公网 HTTPS 方案（未执行）

- 独立运维域名/服务、受信证书、TLS1.2+。反代仅转发 /mcp 至本平台环回/私网 FastAPI；
  无冷库、PLC、规划 MCP 路由或数据库网络连通。数据库仅私网开放，最小数据库账号及备份策略另行审批。
- FastAPI 用 `factory_ops.bootstrap:app`，不自动迁移。仅信任反代固定地址的 forwarded headers，
  正确传递 HTTPS scheme 和原始 Host，禁止 `forwarded-allow-ips=*`；直接公网不能访问 backend 端口。
  若未正确识别 HTTPS，入口403，不降低服务端校验。没有跨域 CORS 或 Cookie 认证例外。
- 网关限制 POST 大小16KiB、请求速率/每用户并发、连接数和应用/DB 超时，返回429/503；
  参考起点：读/总请求超时30秒、连接超时5秒，再按隔离负载测试确定。无长连接 SSE 缓冲需求。
  本轮未进行公网容量/代理压测，参数与客户端重试行为 **UNVERIFIED**。
- 关闭反代 body/header/query 日志及 Uvicorn access log，禁用 SDK/HTTP/SQL DEBUG、遥测 payload 采集、
  异常局部变量采集。使用只含路径（去 query）、时间、状态码、耗时和独立 request_id 的访问指标；
  不记录 JWT、Cookie、Authorization、签名密钥、SQL 参数、设备内容或员工标识。SDK 协议警告须限速。
- 凭据放 secret 管理器，按服务身份读取，不进镜像、前端构建、仓库或 CI artifact。
  修改密钥/allowlist 需受控滚动重启；本版单密钥，轮换时先关闭入口、在平台与后端同步、隔离验签后再开启。
  旧签名立即拒绝；密钥泄漏同时停入口并调查受保护审计，不能只等24小时自然过期。
- 业务审计按现有 append-only 表保留，授权管理 reason 禁止个人信息与凭据。
  工厂/账号变更提交后用原 JWT 复测拒绝；通讯录/人员事件尚未接入，人工停用流程必须明确责任人。

## 回滚

1. 关闭 `FACTORY_OPS_MCP_ENABLED` 并受控重启，入口503；如曾配置反代，同时关闭 /mcp 转发。
2. 必要时撤销 aily MCP 配置、轮换签名密钥；正式租户操作需要另行授权，本轮未执行。
3. 回退本 PR 的代码与 Python 依赖至 main 基线，不改前端、Feishu 配置或冻结 Pages。
4. 无新增迁移，不需要数据库 downgrade。保留 users、身份绑定、厂授权和历史审计；
   不删除审计、不将冷库或生产数据库当作恢复目标。对已授权账号的撤权需单独受控变更并留痕。

后续：先完成独立合成租户验签/类型/agent 范围及代理验证，再评审真实数据接入与生产权限运营。
MCP 写工具、匿名服务、飞书事件同步和设备控制均不属于本交付。

# M1-03B：隔离 HTTPS 测试与真实豆包接入准备

阶段一仅在本机独立 Docker 项目执行合成测试；阶段二需要额外明确授权、隔离域名和企业工作伙伴配置。
本轮没有公网部署、正式租户变更、真实设备或员工数据导入。**不接入飞书企业自建应用。**
保留现有 Feishu 代码，但该测试栈没有相应配置，网关也不暴露登录或人员 HTTP API。

## 文件与启动边界

配置在 [deploy/mcp-test](../../deploy/mcp-test/compose.yaml)：

| 文件 | 用途 |
|---|---|
| compose.yaml | 独立 PG17、API、TLS proxy；默认仅发布127.0.0.1，迁移/离线工具使用 operator profile |
| Dockerfile / Dockerfile.dockerignore | 非 root Python 镜像，限定构建上下文，CA 只用 build secret |
| nginx.conf.template | 精确路由、转发头、TLS1.2+、限流、超时和日志字段白名单 |
| init-db.sh | 初始化隔离测试库账号和私有 schema；撤销 PUBLIC 默认访问 |
| entrypoint.py | 读取各角色的文件 secret，进程内构造 DB URL；不输出配置 |
| database.py | 显式迁移、空库合成 seed、权限检查和隔离故障注入；不作为 HTTP/MCP 入口 |
| inspect_identity.py | 操作员私有 JWT 文件诊断，仅输出验签结果、类型和期限 |
| compose.public-review.example.yaml | 仅模板，CI/本机验证不加载；需要审批、专用 IP、隔离域名与受信证书后才可使用 |

API 与数据库没有宿主端口。API 只信任 Nginx 的固定私网地址；不是信任任意客户端的 X-Forwarded-Proto。
运行、迁移、授权账号权限和限制见 [ADR-0009](../architecture/ADR-0009-isolated-mcp-gateway.md)。
本配置固定 synthetic 数据库名与标记，禁止改成生产库或挂载既有数据卷。

## 可立即执行的自动化本机验证

需要 Linux 本机 Docker Engine / Compose2、Python3.12、OpenSSL。确认使用本机 socket，保留已有代理、
CA 和 registry 凭据；不要改 Docker 默认 context 或访问远端 daemon。没有 Docker 时标记 BLOCKED，不能填 PASS。

```bash
python -m venv .venv
.venv/bin/python -m pip install -e './backend[dev]'
.venv/bin/python scripts/mcp_gateway_test.py --report /tmp/mcp03b-status.json
```

脚本只允许本机 daemon，不接受外部 URL。自动创建 checkout 外0700私有目录、随机密码/签名密钥、
localhost 测试证书、不同合成账号 JWT；所有工厂/设备为 SYNTH 数据。
通过显式迁移与原有离线 CLI 完成 pending→首位负责人→审批绑定/三角色授权，再运行真实 Nginx TLS /
官方 MCP 客户端 / PostgreSQL 测试。客户端显式信任测试 CA，没有关闭证书校验。
正常完成后删除唯一测试项目的容器、网络、数据卷与临时凭据；只留下脱敏状态 JSON。
为兼容 Compose5 / Buildx Bake 的文件读取限制，公开 CA 证书临时复制到已忽略的
`.mcp-gateway-test-results`，仅通过 BuildKit secret 使用，结束时删除，不写入镜像或artifact。
这不是签名密钥、私钥或 JWT；其他私密配置仍只在 checkout 外。
失败时也尝试清理，保留私有诊断，不上传；状态报告区分未执行与已失败，不把跳过当作通过。
用例包括撤权/停用/解绑、审计权限撤销、数据库断开恢复等，仅操作本轮新建合成测试库。

本机 secret 文件对不同容器 UID 采用0444，但其宿主父目录0700，且运行时仅按服务挂载必要单文件；
不能把父目录改成公共可遍历目录。JWT 文件仍0600、由运行操作员 CLI 的 UID 所有，挂载身份目录只给
operator / 测试 probe。长期评审环境建议使用平台 secret manager 正确映射 UID/0400 权限。
无论何种方式，密钥、JWT、数据库密码都不得进入 Git、命令行参数、shell 历史或 CI artifact。

## 只准备配置与手动本机启动

以下命令仍只针对独立本机合成测试环境，不属于公网部署授权。

```bash
umask 077
.venv/bin/python scripts/mcp_gateway_test.py --prepare-only > /tmp/mcp03b-prepared.json
MCP_PRIVATE_DIR="$(jq -r .private_directory /tmp/mcp03b-prepared.json)"
MCP_TEST_PROJECT="$(jq -r .project /tmp/mcp03b-prepared.json)"

mcp_test_compose() {
  env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
    docker --host=unix:///var/run/docker.sock compose --project-name "$MCP_TEST_PROJECT" \
    --env-file "$MCP_PRIVATE_DIR/compose.env" --file deploy/mcp-test/compose.yaml "$@"
}
mcp_test_compose build api
mcp_test_compose up -d --wait db
mcp_test_compose run --rm -T migrate python /app/mcp-test/database.py migrate
mcp_test_compose run --rm -T migrate python /app/mcp-test/database.py seed --confirm-synthetic-only
```

先用原 [离线绑定与授权流程](M1_03A_MCP_RUNBOOK.md) 初始化合成账号，再启动：

```bash
mcp_test_compose run --rm -T operator python -m factory_ops.bootstrap_mcp_access bind \
  --identity-file /run/identities/lead.jwt --reason SYNTH-APPROVAL --confirm-offline-change
# 用返回的当前 version 替换下方变量；不猜版本、不跳过人工核对。
mcp_test_compose run --rm -T operator python -m factory_ops.bootstrap_mcp_access bootstrap \
  --identity-file /run/identities/lead.jwt --expected-version "$PENDING_VERSION" \
  --reason SYNTH-APPROVAL --confirm-offline-change
mcp_test_compose up -d --wait api proxy
```

启动不自动迁移或创建管理员。重复 seed 拒绝覆盖。操作员 profile 是受控终端命令，不是新的 MCP 工具。
本机地址由 prepare 输出 origin 决定，工具路径固定 `/mcp`；无 JWT 的首次工具发现应拒绝401。
不要把本机合成签名密钥/测试 JWT 填入正式豆包配置，或用真实签名密钥为员工自行签发 JWT。

## 第二阶段的前置条件与用户操作

当前这些条件 **BLOCKED**：没有明确公网测试部署授权、专用测试主机/IP与隔离域名/受信 TLS、
企业工作伙伴管理员配置和获准使用的合成测试账号。环境未提供正式签名密钥及可信租户/agent 配置。
用户需要在上述条件准备好后，指定范围并明确授权；本轮不代替用户改变正式租户。
敏感值通过受控 secret 环境配置，不发送到聊天或 Public GitHub。

经授权后才按以下步骤操作：

阶段二须创建新的隔离评审项目和空账号库，迁移后只 seed 合成工厂/设备，再用官方测试账号 JWT 绑定授权。
不把本机演示已经授予角色的合成 JWT/账号库直接切换成官方密钥；这会留下不再匹配来源的旧绑定。
自动验证项目已销毁；公开模板的渲染通过也不代表其已部署或已通过公网 TLS 验证。

1. 在独立测试主机配置专用域名与公开受信证书；默认本机自签 localhost 证书不能用于豆包公网连接。
   验证 firewall 只开放必要 TLS 入口，不开放8000/5432或 Docker API。基础 Compose 仍仅本机绑定；
   公开测试模板需单独加载，提供专用绑定 IP 与审批编号。变量不等于授权，不能为让模板可运行而自行审批。
2. 将 identity_settings 的 public_origin、代理 MCP_PUBLIC_AUTHORITY 和证书域名同步为获准地址；
   将平台签名密钥、tenant_id、agent_id allowlist 存入受控配置。DB 仍只含合成设备/工厂/测试账号。
   只创建测试 MCP，不创建/开启飞书自建应用。
3. 企业工作伙伴 → MCP → 添加自定义 MCP，选择 HTTPStreaming / Streamable HTTP，开启 JWT 身份令牌。
   在编辑页获取平台生成的 identityJWTSecret，按原始字符串注入；不能用共享 Token 或明文用户头代替。
4. 初次添加、初始化和 tools/list 时，记录时刻、request_id、jwt_present 与状态码；
   若 jwt_present=false 且401，保留该协议事实，标记兼容性 FAIL/BLOCKED，查官方平台行为。
   不开放匿名工具目录或业务查询，不填假身份、不取消验签。日志不会保存 JWT 原文。
5. 在获准的安全调试流程中将官方测试账号 JWT 写入私有临时文件（0600、操作员所有）。
   平台是否提供这种受控导出方式 **UNVERIFIED**；无法安全取得时保持绑定 BLOCKED，
   不新增公开捕获接口或从代理日志提取令牌。用 operator 运行下述诊断，验证算法、字段类型、期限和本地范围：

   ```bash
   mcp_test_compose run --rm -T operator python /app/mcp-test/inspect_identity.py /run/identities/review.jwt
   ```

   通过输出仅含 PASS、HS256、claim_types、remaining_seconds，不包含身份值。未通过不能声称认证成功。
   受控离线绑定使用官方验签通过的身份和人工核对工单；不从姓名/邮箱/部门赋权。
6. 按 M1-03A 既有命令绑定测试账号、初始化或关联负责人、授予测试工厂；不添加匿名注册。
   真实员工目录、姓名、手机号、邮箱等不导入；测试账号外部标识仅存隔离 DB，不进入公开报告。
7. 在豆包执行三个工具、消歧、错误恢复和后述拒绝/撤权用例，按实际结果填写 PASS/FAIL；
   全部联调和评审完成前不将真实业务数据接入，不自行 Ready、合并或部署正式环境。

官方依据：[aily MCP 使用](https://aily.feishu.cn/hc/1u7kleqg_73ahi33a)。
官方页面描述不等于当前租户实测，实际 UI、JWT 下发和客户端版本协商均需记录。

## 可复制的豆包 MCP 配置文字

```text
名称：加工厂设备运维（合成数据·只读测试）
描述：只查询本人当前授权的合成加工厂和设备基础档案。先 list_factories 按名称确认工厂，再 search_assets 按设备编号或名称搜索，最后 get_asset_detail 查询明确设备；有歧义先澄清。没有设备控制、业务写入或冷库监控能力。
请求地址：https://YOUR-APPROVED-ISOLATED-DOMAIN/mcp
传输方式：HTTPStreaming / Streamable HTTP
JWT身份令牌：开启；每个请求由平台发送 x-aily-jwt
自定义Header：留空，不填共享身份 Token 或员工 user_id
```

上面是 UI 字段清单，不虚构平台 JSON 导入格式。没有已部署可用的公网 URL。

## 真实豆包验收步骤（当前 UNVERIFIED）

| 场景 | 预期与记录 |
|---|---|
| 初次添加/初始化/tools/list | JWT presence布尔值、状态、协商版本、仅三个只读工具；不记录原 token |
| 合成测试账号签名/类型/过期 | HS256，官方 user_id/tenant_id 整数，agent_id字符串，exp整数且有效；如协议不符先记录，不擅自放宽 |
| list_factories → search_assets → get_asset_detail | 仅本账号授权工厂和合成设备；AI自行使用工具返回 UUID，不要求用户记忆 |
| “查询 SYNTH-EQ-001”且两厂同号 | AI先列授权工厂并澄清，不能猜测；实际自然语言行为须实测 |
| 未绑定/已绑定无角色 | authentication_required / permission_denied，业务错误无 structuredContent |
| 工程师跨厂/管理员越权/直接设备 UUID | 依当前授权通过或拒绝；在 A 厂传 B 厂 UUID 为 not_found |
| 用同一 JWT 撤厂权/停用/解绑后再请求 | permission_denied / authentication_required；不因已初始化连接而缓存旧授权 |
| 连接断开重连/可恢复错误 | 新连接验签，重新初始化和只读查询；不把 HTTP200 的 isError 当成功 |

长连接续传、真实平台重试策略、共享出口限流容量仍需另行验证。本服务无独立 GET SSE 流，合法 GET/DELETE405。
网关/应用/db 日志按 ADR 白名单保留，实际 JWT、密钥、完整请求/响应或员工身份不写入验收附件。

## 回滚与清理

自动验证只销毁其唯一随机项目，禁止 `docker system prune` 或操作其他项目。
手动长期评审环境先停止 proxy/API、保留 PG 数据卷与审计，再回退本 PR 的配置/镜像；无需业务迁移降级。
如阶段二曾经获准配置公网入口，先关该入口和测试 MCP，并经授权轮换签名密钥；不要把此说明视为已执行。
仅一次性的合成测试项目可在确认名称与归属后 `down --volumes`，并删除私有目录及身份临时文件。
prepare-only 保留的公开CA临时文件也应按 compose.env 中 MCP_BUILD_CA_FILE 的路径删除。
不清空已有平台数据库、不删除历史审计、不改变冷库或冻结 Pages。

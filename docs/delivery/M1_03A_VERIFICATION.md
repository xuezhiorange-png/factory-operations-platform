# M1-03A 隔离验证与交付记录

TASK_ID：FACTORY_OPS_M1_03A_REMOTE_MCP_READONLY。
基线 main `c37736070166d17b12b0058f7e32929e99872753`；开工时确认 PR #5/#6/#7 merged。
基线 [main CI 41364199593](https://github.com/xuezhiorange-png/factory-operations-platform/actions/runs/41364199593) success。
分支 `codex/m1-03a-remote-mcp-readonly`，独立 Draft PR，准确 HEAD / 最新 Actions 结果记录在 PR 描述。
本轮没有部署、正式租户/真实数据访问、Ready 或合并。

## 测试环境与结果

2026-11-02，Python3.12、PostgreSQL17（本机环回55433、临时容器、tmpfs、随机测试密码），
测试库限定 factory_ops_test，每例随机 schema；凭据只在 checkout 外0600文件，执行后销毁。
测试官方 JWT 类型采用合成大整数/随机签名密钥，没有真实员工身份或设备。
HTTPS 用临时自签 localhost 证书，官方 MCP 客户端显式信任测试 CA，未关闭 TLS 校验。

| 验证 | 结果 |
|---|---|
| 后端 pytest（原115 + 新50） | 165 passed，0 skipped，11.98秒 |
| Ruff / 文档本地链接 / CI actionlint / git diff --check | 全部通过；106必需文件、133本地链接 |
| PC/H5 shell、设备 API、Feishu/IAM 浏览器回归 | 73 + 6 + 11 = 90 passed（32.9 / 7.1 / 14.8秒） |
| 默认/设备/身份三种前端构建（均含类型检查） | 全部通过 |
| GitHub Actions | 推送后记录到 Draft PR，不以本地通过代替远程结果 |

后端命令（测试 URL 通过受控环境注入，不能把私有 URL 写到命令行输出）：

```bash
python -m pip install -e './backend[dev]'
python -m pytest -q backend/tests
ruff check backend scripts
python scripts/check_docs.py
```

前端沿用现有 npm ci、build、test:e2e；VITE_ASSETS_API_ENABLED=true 构建到 dist-business 后
test:business；再启用 VITE_IDENTITY_ENABLED=true 构建到 dist-identity 后 test:identity。
认证浏览器无 trace、视频或自动截图 artifact；本轮页面没有改动，不重新上传合成身份截图。

## 协议及拒绝访问证据

下表来自实际 FastAPI / 官方 MCP SDK / 隔离 PostgreSQL 测试断言，响应中不留 JWT。

| 测试场景 | 已验证响应/行为 |
|---|---|
| initialize（2025-11-25）→ 通知 → tools/list | 200 / 202 / 三工具；无 MCP Session ID |
| HTTPS 官方客户端三工具、关闭连接再重连 | 两次新 TLS 连接均发现三工具并正确读取合成 A 厂设备 |
| 正常启动组合、Feishu 配置全部缺失 | MCP 独立验签并读取授权设备；未建立网页登录会话 |
| JWT 缺失、无效、过期、错签名、错租户 | initialize/list/call/GET/DELETE 均 HTTP401 |
| HS384 / alg=none / 必填 claim 缺失 / 错 agent / 类型错误 | 验签器拒绝；无 issuer/audience 的合法官方形状可用 |
| Cookie、共享 Bearer、x-aily-user、重复 JWT 头 | 无身份替代通道，HTTP401 |
| 未绑定 / 已绑定未授权 / 停用 | authentication_required / permission_denied / authentication_required |
| 集团、跨厂工程师、单厂管理员、零厂工程师 | 分别只返回3/2/1/0个合成授权工厂；后两者拒绝 B 厂查询 |
| 直接查未授权 B 厂 / 在 A 厂传 B 厂设备 UUID | permission_denied / not_found，无越权数据 |
| 同一个 JWT 撤 A 厂权限后再次查询 | 空厂列表；A 厂 search permission_denied，无授权缓存 |
| 同一个 JWT 身份解绑后再次查询 | authentication_required |
| 数据库失败 / 审计插入失败 | isError + storage_unavailable，无 structuredContent；恢复后正常查询 |
| 未知方法 / 未知工具 / 非法 UUID / 额外 user_id | -32601 / invalid_request；不回显输入敏感哨兵 |
| 错 Origin / 错 Host / 过大 body / 独立 GET | 403 / 421 / 413 / 405 |
| 首位负责人并发初始化 | 仅1个成功，另1个冲突；仅1名集团负责人 |
| 已有 Feishu-only 负责人首次 MCP 关联 | 显式离线确认、目标既有集团角色与版本匹配；禁止升角色，并发只绑定1项 |
| 绑定审计失败 | users 与 external_identities 同事务回滚，均无残留 |
| 既有迁移/失败回滚/审计不可变/CSRF/版本并发 | 原有后端用例全量回归通过 |

详细实现：[JWT 单元测试](../../backend/tests/test_doubao_jwt.py)、
[远程 MCP 与 TLS 测试](../../backend/tests/test_remote_mcp.py)、
[离线授权及并发](../../backend/tests/test_mcp_access.py)。
工具业务错误采用 HTTP200 result.isError，不把 HTTP200 当作授权成功。

## 变更和迁移清单

- 服务依赖：backend/pyproject.toml，官方 MCP SDK / PyJWT。
- 远程组合：api/app.py、api/mcp.py、bootstrap.py、mcp_config.py。
- 复用查询及授权：application/mcp.py、application/access.py。
- 受控人员绑定：application/mcp_access.py、infrastructure/database/mcp_access.py、bootstrap_mcp_access.py。
- 验签：infrastructure/identity/doubao.py、providers.py。
- 验证：tests/conftest.py、test_mcp_identity.py，以及上述三个新测试文件。
- 配置与文档：.env.example、README.md、scripts/check_docs.py、新 ADR/契约/运行说明/本记录；
  身份、集成、API 索引补充当前实现入口。
- 新增数据库迁移：**无**，现有 Alembic head `0003_access_lifecycle`。
- 未修改任何 frontend、M0.6 冻结文件、冷库项目或生产配置。

## 未验证能力、风险与下一步

**UNVERIFIED**：正式 aily 用户 JWT 下发及数值类型、管理端无用户探测行为、签名密钥与 agent 范围、
实际协议版本协商、真实豆包自然语言执行、正式飞书认证/人员事件、真实租户数据、公网反代/证书/限流/容量。
签名密钥或 JWT 泄漏、24小时内重放、人员离职未及时人工停用是主要运营风险。
本轮合成测试证明本平台拒绝路径，不代表外部平台或生产环境安全验收已完成。

后续先在另行授权的隔离沙箱完成 [运行说明](../operations/M1_03A_MCP_RUNBOOK.md) 中的联调，
确认服务端配置/官方类型后再评审真实数据接入。持续使用同一套人员与工厂授权；不增加第二套权限或写工具。
回滚为关 MCP 开关/转发、回退代码与依赖；没有新增迁移，不删除账号或审计。
保持 Draft，等待审核；部署、Ready、Merge 需明确另行授权。

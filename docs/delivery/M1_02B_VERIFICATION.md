# M1-02B 人员授权与生命周期验证记录

任务 `FACTORY_OPS_M1_02_FEISHU_IDENTITY_AND_ACCESS`，日期 2026-11-01。
独立分支 `codex/m1-02b-access-lifecycle`，基于 M1-02A 的
`ff7ae7fd6c8a824c5c162d175fea68196a030f76`（[Draft PR #6](https://github.com/xuezhiorange-png/factory-operations-platform/pull/6)）。
A 依赖仍未合并的 [PR #5](https://github.com/xuezhiorange-png/factory-operations-platform/pull/5)，
没有 Ready、合并或修改 PR #5。最终 B 的 HEAD、Draft PR 与远程 CI 证据在 B PR 描述中。

## 变更文件与迁移

逐文件路径见 [完整 A/B 文件清单](M1_02_CHANGED_FILES.md)，各 PR 的 Files changed 仅显示本段增量。

| 范围 | 文件/内容 |
|---|---|
| 数据库 | `backend/migrations/versions/0003_access_lifecycle.py`；审计 JSONB、正版本、单厂约束/授权版本/撤会话触发器 |
| 业务服务 | `application/access.py`；集团负责人管理、角色/工厂/启用、并发版本、生命周期与离线首次初始化 |
| 持久化 | `infrastructure/database/access.py`；DTO、事务、当前目录、审计与历史分页；沿用同一 users/授权/身份表 |
| API/组合 | `api/access.py`、`api/app.py`、`bootstrap.py`；五个人员接口及依赖装配，无匿名初始化接口 |
| 离线入口 | `bootstrap_access.py`；显式操作员开关、可信绑定与一次性首位负责人初始化 |
| 页面 | `frontend/src/modules/settings/people/`、原 SettingsPage；列表、绑定状态、角色/工厂、停用/撤会话/解绑、记录，PC 表格/H5 卡片 |
| 测试 | `test_access_lifecycle.py`、原测试/合成夹具、`identity-tests/people.spec.ts`；无真实身份或数据 |
| 文档 | [ADR-0007](../architecture/ADR-0007-access-lifecycle.md)、[契约](../api/M1_02_IDENTITY_ACCESS.md)、[后续任务](M1_02_NEXT_TASKS.md)、[截图](screenshots/m1-02/README.md) |

M1-02 的完整链是 `0001_m1_foundation → 0002_feishu_sessions → 0003_access_lifecycle`。
全部变更走 Alembic，不调用 create_all、不自动迁移、不创建真实用户/首位负责人、不修改设备表和原 UUID。

## 测试环境与命令

使用本任务自己的 PostgreSQL 17 临时容器（loopback + tmpfs），测试专用 `factory_ops_test`；
每个后端用例独立随机 schema。浏览器测试服务使用自己的合成 schema、一次性 code 池及 HTTP 响应替身，
经过正常 API/授权/数据库；无测试登录或角色切换 HTTP 端点，没有访问正式飞书、员工或生产数据库。
环境变量必须为受控 `FACTORY_OPS_TEST_DATABASE_URL`，不回退到 DATABASE_URL。

```bash
.venv/bin/python -m pytest -q backend/tests
.venv/bin/ruff check backend scripts
python scripts/check_docs.py
cd frontend
npm ci --no-audit --no-fund
npm run build
npm run test:e2e
VITE_ASSETS_API_ENABLED=true npm run build -- --outDir dist-business
npm run test:business
VITE_ASSETS_API_ENABLED=true VITE_IDENTITY_ENABLED=true npm run build -- --outDir dist-identity
npm run test:identity
```

Node 22 LTS / Python 3.12 / Chromium。HTTPS 证书与合成授权码在 checkout 外私有临时目录；
认证 trace/视频/HTML/自动失败截图均关闭，输出目录不上传。
显式合成截图只包含最终页面，不捕获 state/code 回调或 storage state；CI 不重拍这些截图。

## 本地最终结果

| 验证 | 结果 |
|---|---|
| 后端真实 PostgreSQL 单元/集成 | 115 passed，0 skipped；1 条既有 Starlette/httpx 弃用警告 |
| 原 PC/H5 浏览器 | 73 passed |
| M1-01 真实设备 API 浏览器 | 6 passed |
| HTTPS 身份与人员浏览器 | 11 passed（A 7 项 + B 4 项） |
| 三种能力模式类型检查/构建 | 通过 |
| Ruff / actionlint / 文档链接 / diff check | 通过 |

验证要点：

1. 集团负责人、工程师、多厂工程师、单厂管理员与待授权身份；错误/过期/重放/错误应用或租户的登录均拒绝。
2. 非集团人员不能读取人员列表/记录或写授权，伪造操作者字段不接受；跨 Origin、缺失/错误 CSRF 拒绝。
3. 工程师增厂/调厂、角色取消、停用、主动撤会话、解绑均拒绝旧 Cookie 和设备 UUID。
   重新启用也不能复活旧会话，重新认证后才按当前授权读取。
4. 直接数据库并发给管理员加不同工厂只允许一个成功；多厂工程师直接改成管理员被拒绝。
   失败事务不部分撤销原合法会话；授权版本不能减小。
5. 两个并发人员编辑只接受一个版本并保留一条成功事实；重复/过期版本或移除最后负责人返回 409。
6. 首位负责人无公开注册/初始化路由；离线开关、应用/租户绑定、待授权与版本校验，初始化重放/并发均拒绝。
7. 审计写入失败时权限、版本、会话撤销一并回滚；管理端不能修改/删除历史，数据库追加触发器仍有效。
8. 全链反复升级/降级；0001/0002 DDL 失败回滚和重试继续通过；0003 拒绝旧多厂管理员并完整回滚，
   修正合成旧数据后可重试。有授权审计详情时拒绝降级擦除事实，原审计与 schema 保留。
9. MCP 同一个应用服务在调厂、停用后重新读取相同用户/授权，不能沿用旧范围；没有第二套权限。
10. PC/H5 人员写入由服务端实际确认，失败无成功提示；解绑/撤会话有明确确认，手机显示全部字段并保留五入口。
    原工作台、导航、设备搜索/详情/刷新继续通过。

## 首位负责人操作边界

只在经授权的评审/沙箱环境，由持受控数据库权限的操作员确认已验证待授权账号及版本，
注入 DATABASE_URL、FEISHU_APP_ID、FEISHU_TENANT_KEY 后使用离线入口。下列为参数模板，
不得在本轮会话中替用户对真实环境执行：

```bash
FACTORY_OPS_ALLOW_OFFLINE_BOOTSTRAP=1 python -m factory_ops.bootstrap_access \
  "$FACTORY_OPS_BOOTSTRAP_USER_ID" \
  --expected-version "$FACTORY_OPS_BOOTSTRAP_EXPECTED_VERSION" \
  --reason "受控首位负责人初始化" --confirm-first-group-lead
```

命令不接收密码/外部 open_id，不生成共享账号，完成后必须重新认证；事件记录保留初始化原因。
已有启用负责人时拒绝再次初始化。最后负责人停用/交接须先明确授权接任者。

## UNVERIFIED、风险与回滚

- **真实飞书认证、租户许可/发布、实际 PC/H5 容器与 TLS/代理/Cookie 行为均 UNVERIFIED**。
  未取得真实应用配置，默认失败关闭；自动化只验证官方协议形状及拒绝/事务/页面行为。
- 真实通讯录/人员变更事件和定期对账未接入，不读取真实员工，不声称同步成功。
  离职/停用需负责人及时人工处理，不能假定平台已自动得知飞书侧变更。
- 正式使用前需最小 DB 运行权限、入口限流、过期挑战/会话清理、脱敏与审计保留、依赖锁定、备份恢复和沙箱实测。
- 回退代码时保留 B schema/审计并关闭人员写入口，优先前向修复。有审计详情时 0003 降级主动拒绝；
  仅可丢弃空测试库可降级，且先撤销会话。不得为回滚删除历史事实。

M0.6 冻结四文件和源 SHA 不变，未操作冷库监控、PLC、生产服务/数据库、正式飞书配置或部署。
豆包保持解耦，真实账号/JWT/MCP 服务仍 UNVERIFIED，无匿名服务或写工具。
后续事项见 [M1-02 后续任务](M1_02_NEXT_TASKS.md)。全部交付保持 Draft，等待审核。

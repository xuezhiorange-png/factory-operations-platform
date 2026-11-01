# M0 Draft PR 正文

标题：`M0: 初始化独立 FastAPI/Vue 工程、权限基线与 CI`

目标：`xuezhiorange-png/factory-operations-platform`  
Head：`codex/m0-bootstrap` → Base：`main`  
TASK_ID：`FACTORY_OPS_M0_BOOTSTRAP_DRAFT_PR`

已创建 [Draft PR #1](https://github.com/xuezhiorange-png/factory-operations-platform/pull/1)。
本文件保存可审阅正文；最新 HEAD 与 Checks 以远程 PR 页面和正文证据为准。

## 本 PR 解决什么问题？

导入用户提供的 M0 工程包，建立独立 FastAPI/Vue 3 工程基础和可重复前端构建。
原管理员策略可携带多厂授权，验收示例只判断工厂与维修人；现在管理员最多一厂，
验收还要求待验收状态与完整维修人证据，且所有角色均禁止自验。

## 范围

- 仅公开进程健康检查，固定响应契约；无设备台账/认证/飞书/监控业务接口。
- 预留 Application/Infrastructure，测试分层导入方向；三角色及厂范围保持纯策略示例。
- Node 22、package-lock.json、npm ci、Vue 类型/构建验证；Actions 只读权限、超时、并发取消，无部署步骤。
- 补充 API 目录、资产/导入基线、M1 验收集、架构审阅及回滚说明。
- 审阅资产/机位/位置/测点、Issue/WO、飞书身份、本地授权、只读映射和事务审计/outbox/幂等预留。

## 验证

| 检查 | 本地结果 |
|---|---|
| `.venv/bin/python -m pytest -q backend/tests` | 32 passed；1 条 Starlette/httpx 弃用警告 |
| `.venv/bin/ruff check backend scripts` | PASS |
| `.venv/bin/python -m pip check` / compileall | PASS |
| `.venv/bin/python scripts/check_docs.py` | PASS；必备路径与本地链接 |
| Node 22：`npm ci --no-audit --no-fund` / `npm run build` | PASS；包含 Vue TypeScript 检查 |
| Node 22：`npm audit` | 0 vulnerabilities（本次结果） |
| `actionlint .github/workflows/ci.yml` | PASS（1.7.7）；不是远程 Actions 通过证据 |
| Uvicorn/Vite HTTP 冒烟 | PASS；健康接口、开发代理、业务接口缺席 |

首轮已验证 SHA：`0707c26b276d6c9b4facb2bed02daed9394dbca6`。
远程 [push 运行](https://github.com/xuezhiorange-png/factory-operations-platform/actions/runs/41295392210) 与
[PR 运行](https://github.com/xuezhiorange-png/factory-operations-platform/actions/runs/41295409730) 均为 success，
三个作业全部通过：32 项后端测试/Ruff、npm ci/Vue 类型/Vite 构建、文档检查。

详细环境、命令与限制：[LOCAL_VERIFICATION](LOCAL_VERIFICATION.md)。

## 未验证与风险

用户明确授权在 Public 仓库提交本轮 M0 骨架；不含真实人员/设备/凭据或生产配置。
首轮 push 和 pull_request 的三项远程作业均通过；最新提交以 PR Checks 为准。
实际认证/会话撤权、业务数据库/迁移、事务回滚与并发尚未实现；不可生产使用。
Python 依赖未完整锁定，当前测试客户端有弃用警告。未运行浏览器、移动端或 Compose。
飞书租户/登录/人员同步/机器人、监控实际接口/SSO/webhook/告警映射均为 UNVERIFIED；
没有使用真实设备/员工数据，不推断外部接口存在。

## 数据兼容与回滚

没有数据库变更、已发布业务 API 或外部配置副作用。回滚通过撤销初始化提交的 PR 完成，
不强推，不操作真实库，不影响原冷库规划/监控。后续数据库变更必须使用 Alembic。

## 后续任务

1. 保持 Draft，核对远程 backend/frontend/docs CI；main 分支保护尚未启用，后续需维护者配置。
2. 评审三角色、资产编码/导入/有效期约束、跨厂历史权限及 M1 验收集。
3. 在测试环境以小 PR 实现 M1 授权、迁移、台账和事务审计；独立授权后再核实飞书与只读监控。

- [x] 未触碰生产监控、控制器或真实数据库
- [x] 无伪造生产数据或已完成功能提示
- [x] 本地验证和未验证项分别记录
- [x] 只创建 Draft，不 Ready / Merge / Deploy

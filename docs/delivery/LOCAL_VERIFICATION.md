# M0 本地验证与交付记录

日期：2026-11-01。TASK_ID：`FACTORY_OPS_M0_BOOTSTRAP_DRAFT_PR`。
目标：`xuezhiorange-png/factory-operations-platform`；交付分支：`codex/m0-bootstrap`。

## 工程包来源

已取得并解压用户提供的 `1-factory-operations-platform-M0.zip`，原包含 40 个文件（含隐藏文件），
导入目录 `/workspace/factory-operations-platform`。读取了 AGENTS、V1.3 PRD 和 CODEX_TASK_M0。
原 ZIP SHA-256：`ca13b49d460d5c10696d2986eec8d955018b190f4804e50dee677f105b5c3521`。
没有用 ZIP 替代源代码，也没有访问任何旧冷库规划/监控项目或生产服务器。

## 已运行的验证

环境：Linux / Python 3.12.14；前端命令通过下面的 npm exec 使用 Node 22.23.4、npm 10.9.9，
与 CI 的 Node 22 主版本一致（宿主默认 Node 24.19.0）。

| 检查 | 结果 | 实际命令/证据 |
|---|---|---|
| 安装 Python 工程与开发依赖 | PASS | `python -m venv .venv`；`.venv/bin/python -m pip install -e './backend[dev]'` |
| 后端/策略/架构/OpenAPI 测试 | PASS | `.venv/bin/python -m pytest -q backend/tests`，32 passed；见下方弃用警告 |
| Python 依赖一致性 | PASS | `.venv/bin/python -m pip check`，No broken requirements found |
| Ruff | PASS | `.venv/bin/ruff check backend scripts` |
| 字节码语法 | PASS | `.venv/bin/python -m compileall -q backend/src backend/tests scripts` |
| 文档基线与本地链接 | PASS | `.venv/bin/python scripts/check_docs.py`；检查必备文件与本地链接，不访问外链/锚点 |
| 首次前端安装/锁文件生成 | PASS | 在 frontend 下使用 Node 22 执行 `npm install --no-fund`，生成并保留 package-lock.json |
| 前端干净安装 | PASS | 同环境 `npm ci --no-audit --no-fund` |
| Vue 类型检查及 Vite 构建 | PASS | 同环境 `npm run build`（内含 `npm run typecheck`），12 modules transformed |
| npm 依赖审计（含开发依赖） | PASS | 同环境 `npm audit`，found 0 vulnerabilities；仅代表本次注册表结果 |
| Actions 静态校验 | PASS | actionlint 1.7.7：`actionlint .github/workflows/ci.yml`，退出码 0；发布包校验和已核对 |
| 本地 HTTP 冒烟 | PASS | Uvicorn liveness 200；Vite 首页 200；Vite /api 转发返回完整健康契约；业务 GET/POST 均 404 |
| 浏览器渲染/移动端 | UNVERIFIED | 本轮未运行浏览器或真实手机测试，HTTP 200 不代表视觉/交互验收 |
| PostgreSQL / Alembic / Compose | UNVERIFIED | M0 不连接数据库，无迁移；未启动 Compose |
| GitHub 远程 Actions | PENDING | 已获目标仓库读写权限，推送后检查真实 backend/frontend/docs 作业；不以本地结果代替远程 CI |
| Draft PR | PENDING | 在 main 基线上导入并推送后创建；链接和状态以远程证据为准 |
| 飞书/监控实测 | UNVERIFIED | 无外部连接、登录、通知、SSO、webhook 或事件回放证据 |

前端命令前缀（在 `frontend/`）：

```bash
npm exec --yes --package=node@22 --package=npm@10 -- node --version
npm exec --yes --package=node@22 --package=npm@10 -- npm --version
npm exec --yes --package=node@22 --package=npm@10 -- npm ci --no-audit --no-fund
npm exec --yes --package=node@22 --package=npm@10 -- npm run build
npm exec --yes --package=node@22 --package=npm@10 -- npm audit
```

装有 Node 22.12+ / npm 10 的环境可直接运行上述 `npm ci`、`npm run build`，不必重复使用 npm exec。
构建生成 dist/index.html、CSS 1.78 kB、JS 66.44 kB（gzip 26.68 kB）；这些产物不进入 Git。

本次 Python 主要版本：FastAPI 0.162.0、Starlette 1.10.0、Pydantic 2.14.2、
httpx 0.28.1、pytest 9.2.0、Ruff 0.17.3。Starlette TestClient 提示使用 httpx 的接口弃用，
建议后续维护测试客户端；未屏蔽警告。当前依赖范围没有完整 Python 锁文件，后续版本漂移需关注。

## GitHub 导入基线与可见性

用户已创建目标仓库，当前 GitHub 连接具有读写权限。远程 `main` 初始提交为
`cf793350fb57dc23cd9fdc6cdd8e389342eaca9b`，仅含 README；未含额外项目规则或业务代码。
已将本地 M0 源码接到该基线上，旧本地根提交 `7afc652267ebd50479d983577b43b63c2020939a`
仅作本地归档，不强推，不修改 main。

仓库当前 Public，与原任务书 Private 要求不同。尝试调整可见性时 GitHub 返回 403；
用户随后明确授权“按 Public 提交 M0 骨架”。按该最新授权提交源码、文档和合成示例，
不包含真实人员/设备/凭据/生产配置。原 AGENTS、PRD、任务书原文保留，例外在 README/ADR/清单中说明。

main 分支目前未保护；本轮不擅自调整仓库策略。只创建 Draft PR、观察 Actions，
不执行 Ready、合并、自动合并、强推或部署。PR 与实际 CI 运行证据将在推送后记录。

## 验证边界与后续

VERIFIED 只包括本地源码、测试、依赖安装、构建、文档和 Actions 静态校验。
DESIGN_REVIEWED 表示设计预留，不表示实现。
M1 需要认证/撤权、实体工厂授权、Alembic、导入/附件及事务测试；M3 需要状态机、并发/幂等、
审计/outbox 和独立验收集成测试。试点、飞书和监控需独立的外部授权及脱敏样本。

风险和设计依据见 [M0 审阅](../architecture/M0_REVIEW.md)，回滚见
[M0 运行说明](../operations/M0_RUNBOOK.md)。本轮仅在独立工作目录操作，没有部署或改动其他项目。

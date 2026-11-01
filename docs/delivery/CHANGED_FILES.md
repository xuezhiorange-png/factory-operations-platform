# M0 交付文件清单

以下与用户原始 ZIP 的 40 个文件比较。
远程 main 基线为初始化 README（`cf793350fb57dc23cd9fdc6cdd8e389342eaca9b`）；
本轮 M0 提交以该提交为父提交，main 保持不变。

合计：54 个源文件；新增 14、修改 20、原样导入 20，未删除原包文件。

## 新增文件

- `.gitattributes`
- `backend/src/factory_ops/application/__init__.py`
- `backend/src/factory_ops/infrastructure/__init__.py`
- `backend/tests/test_architecture.py`
- `docs/acceptance/M1_ASSETS.md`
- `docs/api/README.md`
- `docs/architecture/M0_REVIEW.md`
- `docs/data/ASSET_BASELINE.md`
- `docs/delivery/CHANGED_FILES.md`
- `docs/delivery/PR_DRAFT.md`
- `docs/operations/M0_RUNBOOK.md`
- `frontend/.nvmrc`
- `frontend/package-lock.json`
- `frontend/src/api/health.ts`

## 完善的原包文件

- `.github/workflows/ci.yml`
- `README.md`
- `backend/src/factory_ops/api/health.py`
- `backend/src/factory_ops/domain/authorization.py`
- `backend/tests/conftest.py`
- `backend/tests/test_authorization.py`
- `backend/tests/test_health.py`
- `docs/TECH_DEBT.md`
- `docs/architecture/ADR-0001-modular-monolith.md`
- `docs/architecture/ADR-0002-auth-and-factory-scope.md`
- `docs/architecture/data-model.md`
- `docs/architecture/integrations.md`
- `docs/architecture/overview.md`
- `docs/architecture/permissions.md`
- `docs/delivery/GITHUB_START.md`
- `docs/delivery/LOCAL_VERIFICATION.md`
- `docs/delivery/M0_CHECKLIST.md`
- `frontend/package.json`
- `frontend/src/App.vue`
- `scripts/check_docs.py`

## 原样导入

- `.editorconfig`
- `.env.example`
- `.github/pull_request_template.md`
- `.gitignore`
- `AGENTS.md`
- `backend/pyproject.toml`
- `backend/src/factory_ops/__init__.py`
- `backend/src/factory_ops/api/__init__.py`
- `backend/src/factory_ops/api/app.py`
- `backend/src/factory_ops/domain/__init__.py`
- `docker-compose.dev.yml`
- `docs/delivery/CODEX_TASK_M0.md`
- `docs/delivery/PILOT_CHECKLIST.md`
- `docs/delivery/ROADMAP.md`
- `docs/product/PRD_V1.3.md`
- `frontend/index.html`
- `frontend/src/main.ts`
- `frontend/src/style.css`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`

AGENTS、V1.3 PRD 和 M0 任务书内容原样保留。没有把虚拟环境、node_modules、dist、真实 .env 或私密数据纳入交付。
用户明确授权本轮 Public M0 骨架；原 Private 要求的例外在 README、ADR 和交付记录中说明。

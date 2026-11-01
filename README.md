# 加工厂设备运维管理平台 / Factory Operations Platform

> **M0.5 平台界面空壳（2026-11-01）**。在 M0 基础上实现 PC 管理端与移动 H5 页面框架、导航、交互展示和 CI。**尚未实现实际设备台账、登录授权、巡检、报修或监控联动；不得用于生产。**

## 目标

多加工厂全厂设备管理。管理角色仅三类：**集团负责人、工程师、加工厂设备管理员**。员工报修和被指派执行是受限业务入口，不属于第四个管理角色。移动端通过飞书工作台 H5 使用；冷库监控仅作为受控只读数据源。

## 技术

- 后端：Python 3.12+ / FastAPI，计划使用 SQLAlchemy 2、Alembic、PostgreSQL
- 前端：Node 22.12+（推荐 22 LTS）/ Vue 3 / TypeScript / Vite；M0.5 包含模块化管理端与 H5 空壳
- CI：GitHub Actions（后端测试、静态检查、前端构建/浏览器回归、文档基线检查）
- 业务模块分层：API → Application → Domain，外部系统隔离在 Infrastructure/Adapters
- 生产部署、飞书凭据、监控系统访问权限都不包含在此工程包里

## 本地开发

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
python -m pip install -e './backend[dev]'
uvicorn factory_ops.api.app:app --reload --port 8000
# GET http://127.0.0.1:8000/api/v1/health  -> {"status":"ok", ...}

cd frontend
nvm use                  # 如已安装 nvm；未安装时自行使用 Node 22.12+ / 24
npm ci
npm run dev
# 浏览器打开 http://127.0.0.1:5173；Vite 将 /api 代理到 8000
```

已在联网开发环境生成 `frontend/package-lock.json`，并使用 Node 22 完成 `npm ci`、Vue 类型检查和构建。
CI 使用同一锁文件与 `frontend/.nvmrc`；远程 Actions 与 Draft PR 的实际状态见
[验证记录](docs/delivery/LOCAL_VERIFICATION.md)。健康检查仅代表进程存活，不代表数据库或集成就绪。

## 测试

```bash
python -m pytest -q backend/tests
python scripts/check_docs.py
ruff check backend scripts
cd frontend && npm run build
npx playwright install --with-deps chromium
npm run test:e2e
```

## 目录

```
backend/          FastAPI 最小入口与三角色授权策略示例
frontend/         Vue 3 路由、公共组件、PC/H5 布局与独立业务模块空壳
.github/workflows 基础自动化测试，**不会自动部署**
docs/product/     V1.3 产品需求基线
docs/architecture/架构边界、权限、ERD 草案、集成设计和 ADR
docs/api/         已实现健康接口与后续接口目录（后续接口均未实现）
docs/data/        资产身份、编码与导入协议草案
docs/acceptance/  M1 台账最小验收集（尚未执行）
docs/operations/  M0 本地运行、回滚与后续发布门槛
docs/delivery/    M0 验收清单、试点数据、Codex 分解任务
scripts/          只读一致性检查
```

## 安全及交付边界

1. 在**独立 GitHub 仓库**开发（本轮用户明确授权 Public 仅提交 M0 骨架），不触碰 `cold-storage-planning-agent`，也不推断它是监控系统源代码。
2. 严禁未经授权修改/停止监控生产服务，严禁连真实 PLC 写命令，严禁直接写监控数据库。
3. 所有业务状态变化必须在后续实现中具备事务审计、幂等和并发控制；前端隐藏按钮不等于权限控制。
4. 只允许经测试、人工审查后合并；首个功能 PR 保持 Draft，未授权不得 Ready、合并或部署。
5. **本工程包不包含任何正式环境的账号、密码、密钥、设备私有信息或业务数据。**

请先读 [AGENTS.md](AGENTS.md)、[V1.3 PRD](docs/product/PRD_V1.3.md) 和 [M0 验收清单](docs/delivery/M0_CHECKLIST.md)。

M0 基线审阅见 [架构审阅](docs/architecture/M0_REVIEW.md)。
M0.5 的 [接入说明与完整路由](docs/architecture/FRONTEND_SHELL.md)、
[验证记录](docs/delivery/M0_5_VERIFICATION.md) 和 [主要截图](docs/delivery/screenshots/m0-5/README.md) 已提供。
M0/M0.5 已合并后的导航与加载失败恢复补强见 [交互收尾记录](docs/delivery/M0_5_RESILIENCE.md)。
管理端入口 `/#/workbench`，H5 入口 `/#/m/home`；前端可独立浏览，无需启动后端或数据库。
M0 的授权策略没有接入业务 API，不构成已上线的认证/权限系统；当前不需要启动数据库。

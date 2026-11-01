# 加工厂设备运维管理平台 / Factory Operations Platform

M1-02A 新增飞书服务端身份交换、PC/H5 登录入口、待授权账号及安全平台会话。
真实飞书 **UNVERIFIED**，缺配置时通道关闭；认证开关、HTTPS 与隔离测试说明见
[交付记录](docs/delivery/M1_02A_VERIFICATION.md) 和
[身份 API](docs/api/M1_02_IDENTITY_ACCESS.md)。以下 M1-01 记录作为基础能力说明保留，
其“登录尚未实现”仅代表当时状态；完整人员授权生命周期在独立 B PR 接续。

> **M1-01 最小真实业务基础，等待评审，未部署。** 保留 M0.5 PC/H5 空壳，新增独立 PostgreSQL、
> 三角色工厂隔离及设备台账只读 API。飞书/豆包身份仍待官方适配，无正式登录、设备写入或生产数据。

## 当前能力

- Python 3.12+ / FastAPI / SQLAlchemy 2 / Alembic / PostgreSQL 17，单仓库模块化单体。
- Vue 3 / TypeScript / Vite，Node 22.12+（推荐 22 LTS），依赖锁文件已提交。
- 三种管理角色：集团负责人、工程师、加工厂设备管理员；角色及工厂授权由后端逐次从数据库读取。
- 工厂列表、厂内设备列表/搜索及详情；PC 台账与 PC/H5 详情可开启真实只读查询。
- `FeishuIdentityProvider`、`DoubaoMcpIdentityProvider` 保留独立边界，当前失败关闭；
  两个只读 MCP 工具仅契约与测试，无豆包网络连接、无写工具。
- GitHub Actions 执行真实隔离 PostgreSQL 测试及既有 PC/H5 回归，不自动部署业务版本。

巡检、报修、工单、保养、库存、附件、实际登录/会话签发及授权管理仍未实现。
飞书和豆包是未来接入渠道，设备事实保存在独立数据库。不得用于生产。

## 本地运行

先阅读 [AGENTS.md](AGENTS.md)、[V1.3 PRD](docs/product/PRD_V1.3.md) 与
[ADR-0005](docs/architecture/ADR-0005-minimal-business-foundation.md)。本轮 M1-01 授权范围与实现
见 [验证记录](docs/delivery/M1_01_VERIFICATION.md)，不改变历史 M0 的交付记录。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e './backend[dev]'
# 不接数据库也可运行健康检查；不是业务 readiness
uvicorn factory_ops.api.app:app --reload --port 8000

cd frontend
nvm use
npm ci --no-audit --no-fund
npm run dev
```

默认浏览 `http://127.0.0.1:5173/#/workbench` 或 `/#/m/home`，设备模块仍是未接入的空壳。
不需要数据库，不会生成设备或假账号。

需要数据库评审时，先复制 `.env.example` 为本地 `.env`，替换开发占位密码；不要提交 `.env`。
仅在独立开发环境运行 `docker compose --env-file .env -f docker-compose.dev.yml up -d db`，
不要复用生产/其他项目数据库。通过安全的本地方式向进程环境注入对应 `DATABASE_URL`
（`postgresql+psycopg`，Alembic/应用不会自动加载 `.env`），在项目根目录执行：

```bash
alembic -c backend/alembic.ini upgrade head
uvicorn factory_ops.bootstrap:app --reload --port 8000
# 另一个终端，在 frontend/ 中开启设备查询能力
VITE_ASSETS_API_ENABLED=true npm run dev
```

迁移只建表，不插入账号或资产。真实业务端点需要有效平台会话，无会话返回 401、页面显示无权限；
开关不会授予权限。本轮没有模拟登录或产品内测试身份选择器。完整浏览器联调使用隔离合成 fixture，
见下述验证文档；正式身份接入见 [身份适配设计](docs/architecture/IDENTITY_ADAPTERS_M1.md)。

Vite 开发/本地 preview 代理 `/api` 到 loopback 8000（测试可显式配置
`FACTORY_OPS_API_PROXY_TARGET`）。静态 build 不提供代理；未来受控环境需另配同源反向代理与 TLS。
本轮不执行部署。

## 测试

```bash
python -m pytest -q backend/tests
ruff check backend scripts
python scripts/check_docs.py
cd frontend
npm run build
npx playwright install --with-deps chromium
npm run test:e2e
VITE_ASSETS_API_ENABLED=true npm run build -- --outDir dist-business
npm run test:business
```

真实数据库测试必须设置 `FACTORY_OPS_TEST_DATABASE_URL`，只允许专用 loopback
`factory_ops_test` 数据库；每个测试使用临时 schema 并经 Alembic 建表/清理。
没有该环境变量时后端集成测试会跳过，不能算业务验证通过；CI 显式创建独立 PostgreSQL service，
执行全部后端和浏览器联调。认证测试关闭 trace/截图/视频/HTML 产物，凭据留在 checkout 外私有临时文件。
命令、结果、迁移/回滚与风险见 [M1-01 验证记录](docs/delivery/M1_01_VERIFICATION.md)。

## 目录与契约

```text
backend/src/factory_ops/api/             HTTP 白名单 DTO 与只读路由
backend/src/factory_ops/application/     共用查询服务、身份/MCP/持久化端口
backend/src/factory_ops/domain/          纯领域设备 DTO、三角色策略
backend/src/factory_ops/infrastructure/  PostgreSQL、失败关闭的身份适配器
backend/migrations/                     Alembic 修订
frontend/src/modules/assets/            既有页面、真实 API 客户端与查询状态
frontend/src/shared/                    公共布局与组件
frontend/business-tests/                 浏览器→真实 API→隔离数据库
docs/                                  PRD、ADR、契约、验证与后续任务
```

- [HTTP 与只读 MCP 契约](docs/api/M1_01_ASSET_READ.md)
- [身份适配设计](docs/architecture/IDENTITY_ADAPTERS_M1.md)
- [M1-02 与 M1-03 后续清单](docs/delivery/M1_NEXT_TASKS.md)
- [M0.5 页面接入/路由](docs/architecture/FRONTEND_SHELL.md)、[历史截图](docs/delivery/screenshots/m0-5/README.md)
- [M0.6 冻结预览](docs/delivery/M0_6_PAGES.md)：冻结工作流与源 SHA 保持原样，不发布本轮代码。

## 安全和交付边界

独立仓库中只提交源码、契约及合成测试，无员工信息、真实设备、身份令牌或飞书密钥。
不修改既有冷库规划/监控项目，不访问生产服务器、PLC、真实业务库或正式飞书租户。
列表、详情及未来 MCP 均复用后端授权；客户端工厂选择和 AI 参数不能代替授权。
M1-01 在独立分支提交 Draft PR，未经另行明确授权不 Ready、Merge 或 Deploy。

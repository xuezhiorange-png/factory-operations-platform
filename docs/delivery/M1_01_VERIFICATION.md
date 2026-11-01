# M1-01 最小真实业务基础验证记录

任务：`FACTORY_OPS_M1_01_MINIMAL_BUSINESS_FOUNDATION`。独立分支：
`codex/m1-01-business-foundation`，基于 `main` 的 `b9420ee`；未覆盖已合并工作。
本地记录日期：2026-11-01。最终 HEAD、Draft PR 及远程 Actions 结果以 PR 描述为准。

## 实际实现

- PostgreSQL 17、SQLAlchemy 2、Alembic 初始修订 `0001_m1_foundation`，七张基础表。
- 服务端不透明会话校验，三角色与逐次工厂授权；工厂、设备列表、设备详情真实只读 API。
- 已有 PC 台账与 PC/H5 详情按构建能力开关接入；未重建管理页面。
- Feishu/Doubao 身份适配端口失败关闭，两个只读 MCP 契约复用应用服务。
- 成功查询/授权拒绝审计，审计异常阻止返回设备数据；无业务写入或附件 API。

架构及迁移决策见 [ADR-0005](../architecture/ADR-0005-minimal-business-foundation.md)，
字段、认证与错误契约见 [HTTP/MCP 文档](../api/M1_01_ASSET_READ.md)。

## 隔离环境与可重复执行

本地使用独立 Docker PostgreSQL 17 容器、仅 loopback 端口、tmpfs 数据目录；
不复用任何已有项目数据库。测试只接受 `postgresql+psycopg`、`127.0.0.1/localhost` 和
`factory_ops_test` 库名，每个测试使用随机专用 schema，Alembic 建表后插入合成数据，结束删除该 schema。
真实租户/生产数据/冷库监控/PLC 均未访问。

需先在独立本地 PostgreSQL 或 CI 临时 service 中创建测试库，并通过受控环境注入
`FACTORY_OPS_TEST_DATABASE_URL`。它不会自动回退到 `DATABASE_URL`。没有测试 URL 时集成用例跳过，
不得据此宣称业务验证通过；本记录及 CI 都显式提供专用测试库，后端无跳过。

```bash
python -m venv .venv
.venv/bin/python -m pip install -e './backend[dev]'
.venv/bin/python -m pytest -q backend/tests
.venv/bin/ruff check backend scripts
python scripts/check_docs.py

cd frontend
# Node 22 LTS，使用已提交的 package-lock.json
npm ci --no-audit --no-fund
npm run build
npx playwright install --with-deps chromium
npm run test:e2e
VITE_ASSETS_API_ENABLED=true npm run build -- --outDir dist-business
npm run test:business
```

`test:business` 启动独立 loopback FastAPI 测试进程与 Vite preview，使用真实数据库和离线合成会话。
需要项目根目录 `.venv`；本地可用 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 指向已安装 Chromium。
不会增加测试登录 HTTP 端点、访问外部系统或为产品生成预置账号。

## 测试结果

| 验证 | 本地结果 | 证明范围 |
|---|---|---|
| Python/真实 PostgreSQL | 66 passed，无 skipped | 领域策略、架构边界、API、数据库、MCP 契约 |
| 原有 PC/H5 Playwright | 73 passed | 原路由、刷新、导航、响应式、交互、无障碍与加载失败恢复 |
| 真实 API PC/H5 Playwright | 6 passed | 浏览器→FastAPI→PostgreSQL，查询/搜索/详情/刷新/工厂切换及四种状态 |
| 默认与 API 开启构建 | 通过，均含 TypeScript 检查 | 两种能力模式独立产物，前端测试代码参与类型检查 |
| Ruff、文档本地链接、actionlint、diff 空白检查 | 通过 | 代码静态规则、交付文件、工作流语法 |

后端现有 Starlette TestClient/httpx 有一条弃用警告，不影响通过；Python 完整锁文件及
客户端依赖升级留待工程加固。真实飞书/豆包、正式浏览器 SSO、生产容量/备份恢复均 **UNVERIFIED**。

重点断言：

1. 集团、单厂/多厂工程师、单厂管理员得到服务端允许范围；无授权工程师无厂可选。
2. A 厂身份查询/搜索 B 厂、直接访问 B UUID、在 A 路径嵌入 B UUID 均拒绝，不泄漏名称/数量。
3. 使用同一个旧会话，在授权提交撤销、移除角色、集团降权、停用用户、撤销/过期/未生效会话后再次查询均拒绝。
4. 伪造用户头/用户参数、额外或重复查询参数、冲突 Cookie/Bearer、管理员多厂误配不放行。
5. 列表/详情无附件、令牌或外部身份字段；附件路径未开放，POST 设备不允许。
6. 搜索字面量 `%`/`_`、无匹配、分类/状态、稳定分页与同厂计数，结果不包含其他工厂。
7. Alembic 两轮升/降级、元数据一致性、外键/重复编号/角色约束；DDL 中途失败全部回滚后可重试。
8. 审计 UPDATE/DELETE 被数据库拒绝；插入审计失败返回安全 503、事务回滚、不返回设备。
9. 两个真实身份 provider 不声称成功；MCP 测试替身下的跨厂/直接 UUID、撤工厂授权、解绑身份与写工具均拒绝。
10. 浏览器清楚区分加载、空数据、网络失败、无权限；详情刷新与集团返回列表保留工厂范围，H5 不横向溢出。

## CI 与产物保密

沿用现有 CI 三个 job，后端和前端业务测试各有独立 PostgreSQL service。CI 里的
`synthetic-ci-only` 仅用于本 job 内即时销毁的测试服务，绝非真实环境密码；无需生产 secrets。
前端先运行原空壳测试，再单独构建 `dist-business` 运行真实 API 测试。

认证用例的临时会话文件位于 checkout 外、0600 权限，测试服务器退出后删除；
trace、截图、视频、HTML 报告关闭，`.business-test-results` 不进入上传路径或 Git。
保留的原空壳 Playwright artifact 不包含认证。测试日志不打印会话、JWT、连接串或员工资料。
不上传已认证浏览器状态，不将合成登录接口加入运行时应用。

## M0.6 与边界核对

冻结 Pages 工作流、ADR-0004、M0_6_PAGES 及 check_pages_dist.py 与基线无差异；
冻结源仍为 `f38232dd3821c22b964d8298edddac6b5be63705`。业务分支不触发修改静态版本或部署。
没有修改冷库规划/监控项目、生产服务器、PLC、正式飞书配置或生产数据库。

本轮尚无正式登录/授权管理界面、设备维护/导入/附件/完整生命周期、真实 MCP 网络服务。
当前适合隔离评审，不是可上线的完整 M1；下一步见 [M1-02 / M1-03 清单](M1_NEXT_TASKS.md)。
回退先关闭前端读开关并回退代码，保留已有数据；`downgrade base` 仅在可丢弃隔离库验证，
会删除本轮表，禁止作为正式数据的常规回滚方式。交付保持 Draft，等待审核。

# 加工厂设备运维管理平台 / Factory Operations Platform

> **M1-02：身份与人员授权，Draft 等待审核，未部署。** 已有设备只读台账、PC/H5 页面与独立数据库。
> 飞书真实租户认证、人员事件及实际手机容器均 **UNVERIFIED**；缺配置时认证通道关闭。

## 已实现范围

- Vue 3 + TypeScript + FastAPI + PostgreSQL 17，SQLAlchemy 2 / Alembic，单仓库模块化单体。
- 官方飞书网页 OAuth 服务端适配，PC/H5 登录入口、待授权账号、高熵平台会话、退出、Origin/CSRF 与安全回跳。
- 固定三角色：集团负责人、工程师、加工厂设备管理员。后端逐次校验当前身份及工厂授权，不从部门或姓名赋权。
- 现有设置页面的人员管理：绑定状态、角色、工厂、启用/停用、撤会话、飞书解绑与变更记录。
  数据库限制管理员至多一厂；权限变化撤销旧会话，重新启用不恢复旧会话；审计与变更同事务。
- 工厂列表、厂内设备列表/搜索和详情，PC/H5 共用真实只读 API。其余运维业务仍待接入。
- 豆包只保留两个只读 MCP 契约，身份适配器仍失败关闭，无网络监听或写工具。

没有部署、真实员工/设备导入、通讯录同步、监控/PLC 操作、巡检/维修/保养/库存或复杂审批。
飞书和豆包是接入渠道，设备与授权事实始终保存在独立运维数据库。

## 交付与契约

- [M1-02A 认证/会话测试记录](docs/delivery/M1_02A_VERIFICATION.md)、[ADR 与官方资料](docs/architecture/ADR-0006-feishu-platform-sessions.md)
- [M1-02B 人员授权/生命周期记录](docs/delivery/M1_02B_VERIFICATION.md)、[数据库/并发与回滚决策](docs/architecture/ADR-0007-access-lifecycle.md)
- [身份及人员 API](docs/api/M1_02_IDENTITY_ACCESS.md)、[设备 HTTP/MCP 契约](docs/api/M1_01_ASSET_READ.md)
- [PC/H5 合成环境截图](docs/delivery/screenshots/m1-02/README.md)、[后续实测与豆包任务](docs/delivery/M1_02_NEXT_TASKS.md)

A 依赖未合并的 PR #5，B 依赖 A。各 PR 描述提供准确 HEAD 与实际 Actions 链接；均保持 Draft。
历史 [M1-01 验证](docs/delivery/M1_01_VERIFICATION.md)、[M0.5 页面](docs/architecture/FRONTEND_SHELL.md)
和 [M0.6 冻结预览](docs/delivery/M0_6_PAGES.md) 保留，冻结工作流/源码不修改。

## 本地空壳与设备基础

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e './backend[dev]'
uvicorn factory_ops.api.app:app --reload --port 8000 --no-access-log
cd frontend
nvm use
npm ci --no-audit --no-fund
npm run dev
```

默认能力开关关闭，可浏览 `/#/workbench` 与 `/#/m/home` 空壳，不生成假账号或设备。
健康接口只报告存活，不代表数据库、身份或集成就绪。

在独立开发环境复制 `.env.example` 为本地 `.env` 并替换占位密码，可使用已有
`docker-compose.dev.yml`；不复用其他项目/生产数据库。向进程安全注入 DATABASE_URL 后显式执行：

```bash
alembic -c backend/alembic.ini upgrade head
uvicorn factory_ops.bootstrap:app --reload --port 8000 --no-access-log
```

应用不自动读 `.env`、连接迁移或创建管理员。Vite 开发/preview 代理仅供本地使用，静态构建不提供 API 代理。

## 身份评审环境

需要受控的同源 HTTPS 与固定回调。后端配置见 [身份 API](docs/api/M1_02_IDENTITY_ACCESS.md)：
DATABASE_URL、FACTORY_OPS_PUBLIC_ORIGIN、FEISHU_APP_ID、FEISHU_APP_SECRET、FEISHU_TENANT_KEY。
Secret 只在受控环境注入，不提交、不交给前端。缺配置不伪造成功登录。

前端构建设置 `VITE_ASSETS_API_ENABLED=true VITE_IDENTITY_ENABLED=true`；开关只启用页面能力，不授予权限。
生产 Cookie 始终 Secure/HttpOnly，普通 HTTP 页面不能用来验证正式登录；本轮不配置或部署正式环境。
首次有效身份只建立待授权账号，首位集团负责人通过离线受控流程确认，之后由其管理本地角色与工厂。
没有公开注册、测试登录或前端角色选择入口。离线操作边界见 B 交付记录。

## 隔离测试

Python 3.12 / Node 22 LTS。安全注入 FACTORY_OPS_TEST_DATABASE_URL，必须指向 loopback 的
factory_ops_test 测试库；每例随机 schema，真实 PostgreSQL/Alembic，合成身份与设备。
不设置测试 URL 时集成用例跳过，不能据此算业务通过；CI 明确创建独立 PostgreSQL service。

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
VITE_ASSETS_API_ENABLED=true VITE_IDENTITY_ENABLED=true npm run build -- --outDir dist-identity
npm run test:identity
```

最后一组自动创建本地 HTTPS 测试证书，只替换官方认证传输，仍调用正常平台 API/会话/权限与独立数据库。
不接真实飞书。认证 trace、视频、HTML 和自动失败截图关闭；私有凭据文件在 checkout 外，结束删除。
显式截图只用于带合成标记的最终页面，CI 不上传认证输出。原空壳浏览器证据继续保留。

## 安全与回滚

阅读 [AGENTS.md](AGENTS.md) 与 [V1.3 PRD](docs/product/PRD_V1.3.md)。没有生产访问、Ready/Merge/Deploy 授权。
现有冷库监控、PLC、生产库和 M0.6 冻结公开预览保持不变。Public GitHub 中只包含源码、契约与合成测试。

停用/离职当前须及时人工处理，真实人员事件和对账未接通。正式使用前须完成沙箱认证、最小 DB 权限、
限流/清理、日志脱敏、审计保留及备份演练。回退代码保留 schema 与审计，关闭写入口并优先前向修复；
0003 有授权审计详情时拒绝降级擦除历史，空隔离库降级先撤会话。不得为回滚删除真实授权事实。

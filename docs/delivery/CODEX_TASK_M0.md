# 可直接给 Codex 的首轮任务

目标仓库：`xuezhiorange-png/factory-operations-platform`（独立 Private 仓库）。

**任务 ID：FACTORY_OPS_M0_BOOTSTRAP_DRAFT_PR**

## 已明确边界

- 全厂设备、多工厂、设备台账为先；三种管理角色固定（集团负责人/工程师/加工厂设备管理员）。
- 飞书工作台 H5/免登/机器人通知，现有冷库监控仅只读联动；M0 只设计契约，不实际接入。
- M0 工程包包含 FastAPI 健康检查、最小 Vue 页面、CI、设计/测试/验收文档；不能视为功能已开发。

## 执行步骤

1. 只在新仓库检查、修正初始化工程。**不进入**旧冷库规划仓库或现有生产环境。
2. 检查文件/路径/内容、Python 环境依赖及安全边界，并运行所有后端测试、Ruff、文档检查。
3. 在联网开发环境执行 `cd frontend && npm install`，生成并提交 `package-lock.json`；CI 改为 `npm ci` 并验证 Vue TS/build。
4. 完成初步架构审阅：设备/机位/位置/测点身份、Issue vs WO、三角色/厂范围、飞书身份映射、outbox/幂等/审计模型。
5. 输出 M0 未核实事项，明确监控接口及飞书实际配置需用户授权后确认。
6. 在新仓库创建适当分支并提交 **Draft PR**，附测试证据和文档目录。只读审查 PR，不 Ready、不合并、不部署。

## 严禁

- 禁止变更、重启、停机任何生产服务；禁止 PLC/控制器读写、网络扫描。
- 禁止读取或提交真实企业账号、密钥、设备控制数据或客户隐私。
- 不准擅自把示例策略当成已启用的认证系统。
- 不准编造端到端功能运行、飞书成功登录、监控实际接口存在等证据。

## 输出格式

TASK_ID / REPO / BRANCH / PR_NUMBER / PR_STATE / HEAD_SHA / CI_STATUS /
BACKEND_TEST / FRONTEND_BUILD / DOCS_CHECK /
VERIFIED / UNVERIFIED / CHANGED_FILES / RISKS / NEXT_ACTION。

注意：如仓库尚未由仓库所有者创建，应明确说明无法直接创建；不得改用既有 `cold-storage-planning-agent` 承载新系统。

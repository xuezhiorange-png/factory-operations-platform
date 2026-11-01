# M1-02A：飞书认证与平台会话交付记录

日期 2026-11-01。任务 `FACTORY_OPS_M1_02_FEISHU_IDENTITY_AND_ACCESS` 的 A 部分。
分支 `codex/m1-02a-feishu-session`，基于重新读取的 PR #5 最新 HEAD
`bc6f77bc4a4ea2ed7db8730fbfd92a2ab0e7f007`，PR #5 仍为 Draft，因此提交依赖它的堆叠 Draft PR。
本记录不授权 Ready、合并或部署。最终 HEAD、PR 编号与远程 CI 链接记录在该 PR 描述中。

## 变更清单

- `backend/migrations/versions/0002_feishu_sessions.py`：oauth_flows；用户授权版本、名称；绑定会话、CSRF 摘要。
- `application/auth.py`、`infrastructure/database/auth.py`：登录挑战/重放/事务、待授权账号、会话签发/退出。
- `infrastructure/identity/feishu.py`：固定官方 HTTPS 交换和 user_info 校验，缺配置失败关闭。
- `api/auth.py`、组合入口：五个身份接口、Cookie、Origin、CSRF、无凭据回显和安全回跳。
- 既有设备 API 复用当前授权并识别新 Cookie；身份/会话失效不继续显示旧设备结果。
- `frontend/src/modules/identity`：PC/H5 登录、当前身份、待授权、退出与异常恢复；复用原布局及工厂选择。
- 独立 HTTPS 浏览器夹具、测试与 CI；只显示合成人员/工厂/设备。
- [ADR-0006](../architecture/ADR-0006-feishu-platform-sessions.md)、
  [身份契约](../api/M1_02_IDENTITY_ACCESS.md)、[截图](screenshots/m1-02/README.md)。

## 实际本地结果

| 检查 | 结果 |
|---|---|
| PostgreSQL 后端单元/集成测试 | 95 passed，0 skipped；1 条既有 Starlette/httpx 弃用警告 |
| 原 PC/H5 空壳浏览器 | 73 passed |
| M1-01 真实 API 浏览器 | 6 passed |
| 新 HTTPS 登录/会话浏览器 | 7 passed |
| 三种前端模式类型检查及构建 | 通过 |
| Ruff / actionlint / 文档链接 / diff check | 通过 |

后端验证官方响应无效/过期/错误租户或应用、无效身份、未配置通道、未绑定/未授权、三角色及多厂工程师、
state 浏览器绑定/期限/重放、code 重放、相同挑战并发只签发一次、会话轮换/退出、绑定撤销、
Origin/CSRF、回跳白名单、审计失败回滚，以及新增迁移中途失败后回滚重试。
原 M1-01 的跨厂查询/搜索/直接 UUID、角色与权限变更后旧授权拒绝、迁移升降级继续通过。

浏览器实际执行：正常平台入口→官方授权页的显式测试传输替身→真实后端回调→真实 PostgreSQL
绑定/会话→原 PC/H5 台账；验证 Secure/HttpOnly Cookie、深链、工厂切换/刷新、退出、待授权、
跨厂拒绝、登录过期/服务错误及 H5 异常授权重试。没有公开测试登录/角色选择 API。

## 重复执行

使用独立 loopback PostgreSQL `factory_ops_test`，每例随机 schema，绝不回退到业务 DATABASE_URL。
凭据通过 `FACTORY_OPS_TEST_DATABASE_URL` 安全注入，不在命令或日志展示。

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

Node 22 LTS；Chromium 由 Playwright 安装，本地也可设 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`。
新测试配置生成 checkout 外私有临时证书，浏览器只对这个本地自签环境设置 ignoreHTTPSErrors，
后端访问官方飞书始终校验 TLS。合成 OAuth code 池在私有 0600 文件，服务退出后删除；
认证 trace/视频/HTML/自动失败截图关闭，输出目录不上传。显式截图不含回调、令牌或个人真实数据。

## 真实认证与安全风险

**飞书真实认证：UNVERIFIED。** 当前环境没有飞书应用配置/密钥，未创建或修改正式应用，未读取真实员工。
自动化证明实现与拒绝分支，不证明租户发布/许可、真实 H5 免确认、网络代理、Cookie 或事件权限已获验证。
没有通讯录事件端点或同步“成功”提示；人工受控停用及授权变更由 B 实现。

正式使用前需管理员确认官方应用配置、固定回调/HTTPS 同源环境、最小权限与可见性，
在获准沙箱完成 PC/H5 实测；还需入口限流、挑战/会话留存清理、代理/ASGI 查询串脱敏、最小 DB 权限及备份演练。
不是生产交付，本轮不部署。首位集团负责人初始化和人员授权界面属于 B，不在 A 暗设管理员。

回滚先关闭身份/设备功能并停止写入，保留并备份数据库。0002 降级会先撤销会话，再删除新增字段/挑战表，
不会物理删除设备；降级会丢失新增身份显示/版本信息，只在可丢弃测试库验证。
有数据环境优先前向修复；恢复登录需重新认证，不复用旧会话。

M0.6 四个冻结文件、固定源 SHA 均无改动；冷库监控、PLC、生产服务器/数据库均未操作。
豆包 provider 仍失败关闭，两个只读工具契约保持不变；后续任务见
[M1 后续清单](M1_NEXT_TASKS.md)，B 交付将补充人员生命周期及豆包校验接入事项。

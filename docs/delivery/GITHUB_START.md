# GitHub 导入与 Draft PR 交付

## 本轮仓库与授权

目标：`xuezhiorange-png/factory-operations-platform`，分支 `codex/m0-bootstrap`，目标 `main`。
用户已创建仓库；当前 Public，用户明确授权本轮按 Public 提交 M0 骨架，覆盖原工程包 Private 要求。
不得据此提交真实设备、员工数据、凭据或生产配置。原任务书内容保留，当前例外见
[ADR-0001](../architecture/ADR-0001-modular-monolith.md)。

已核实 main 初始化提交为 `cf793350fb57dc23cd9fdc6cdd8e389342eaca9b`，仅含 README。
M0 分支必须以该 main 基线为祖先，不能把旧本地根提交强推为 main。
完整验证与远程交付证据见 [验证记录](LOCAL_VERIFICATION.md)，正文见 [PR 正文](PR_DRAFT.md)。

## 交付步骤

1. 导入工程包目录内容，保留隐藏文件；不提交 ZIP、.git、.venv、node_modules、dist 或真实 .env。
2. 运行后端测试、Ruff、文档检查、npm ci、Vue 类型检查/构建、Actions 静态检查。
3. 检查暂存文件及凭据模式后，仅推送 `codex/m0-bootstrap`，不强推、不推送 main。
4. 创建 `draft=true` 的 PR，正文包含测试、风险、架构预留和回滚；观察真实 backend/frontend/docs 作业。
5. 核对 PR base/head/SHA/草稿状态与变更文件；更新验证记录，不 Ready、合并或部署。

等价的创建命令（仅作说明，不代表已执行成功）：

```bash
gh pr create --repo xuezhiorange-png/factory-operations-platform \
  --base main --head codex/m0-bootstrap --draft \
  --title "M0: 初始化独立 FastAPI/Vue 工程、权限基线与 CI" \
  --body-file docs/delivery/PR_DRAFT.md
```

## 尚未完成的门槛

main 分支保护、必须审查和发布环境策略尚未启用，不能把当前 PR 自动视作允许合并。
本轮不连接生产服务器、飞书实际租户或监控项目，不创建 Actions secrets，无部署工作流。

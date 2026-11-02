# 现有服务器审计：网络阻塞与交付状态

TASK_ID：FACTORY_OPS_M1_03B_EXISTING_SERVER_AUDIT。
基线 main `85c7d18ba44148e1a7133c08525cc2a2421200e6`，PR #9 已合并。
分支 `codex/m1-03b-existing-server-audit`；独立 Draft PR，最终HEAD/CI见PR描述。
公开记录使用“目标测试服务器”代号，实际地址由任务指定，不在Public仓库补充发布服务器身份或域名。

## 实际执行与网络证据

2026-11-02，当前环境状态 current/enforced，但 TCP destination grants 的 domains/ip_ranges 均为空，
没有VPN、现成SSH工具通道或已加载的SSH agent身份。
对环境声明的TCP代理仅做一次连接资格探测，结果 ConnectionRefusedError，尚未建立到目标22的通道。
**没有进行SSH认证，没有执行任何服务器命令。此后停止全部远程尝试。**

这是当前执行环境的出站限制，不能据此判断目标22端口、防火墙或authorized_keys是否有问题。
没有修改网络策略、SSH密钥、用户、SSH配置、防火墙、服务器Nginx、Docker、数据库或服务。
没有改用其他代理/VPN/80/443等方式重试目标；没有公网部署或豆包操作。

## 按要求填写的结果

```text
SERVER_AUDIT=BLOCKED：Codex无法建立SSH出站通道；SSH认证与服务器命令均未执行。
EXISTING_SERVICES=UNVERIFIED：实际容器/宿主服务、冷库监控及规划归属尚未核实；所有既有服务均默认不可触碰。
AVAILABLE_RESOURCES=UNVERIFIED：目标CPU/内存/磁盘/Docker/Compose及剩余容量没有服务器证据。
PORT_CONFLICTS=UNVERIFIED：22/80/443/3001/8000/8101及候选18443均未取得占用快照。
DOCKER_NETWORK_CONFLICTS=UNVERIFIED：PR9固定172.30.83.0/28已确认；尚无目标网络/路由数据，不能宣称无冲突。
RECOMMENDED_TEST_DOMAIN=factory-ops-mcp-test.<OWNER_CONFIRMED_BASE_DOMAIN>：候选，域名归属/DNS/TLS均UNVERIFIED。
RECOMMENDED_LOCAL_PORT=127.0.0.1:18443：候选，必须审计并复核未占用；不抢占公网443。
ISOLATION_PLAN=PLANNED：独立项目/目录/PG17卷/凭据/私有网络；优先既有Nginx新虚拟主机，仅/mcp；容器化Nginx路径须另核实。
BACKUP_AND_ROLLBACK_PLAN=PLANNED/UNVERIFIED：未执行备份或恢复；任何后续配置修改前需私有备份和隔离恢复验证、明确授权。
READY_FOR_DEPLOYMENT=NO。
```

没有把Codex环境、合成fixture或PR #9的本机TLS结果当作目标服务器事实。
PR #9通过的26项网关检查仍只证明本机合成环境，不证明本服务器的容量、网络或真实豆包兼容性。

## 当前不可触碰清单

因为尚未识别实际名称/ID，本清单是保护边界，不是已完成的服务盘点：

| 资源 | 当前处理 |
|---|---|
| 冷库监控、冷库规划及其MCP/数据/证书/目录 | 不停止、重启、连接、改写或复用；精确ID待所有者核实 |
| 其他全部现有容器/宿主服务，含未分类/停止的服务 | 默认保护，禁止为了腾端口或内存调整 |
| 已有Docker网络、数据卷、数据库、daemon配置 | 不改网络成员/地址，不挂载旧卷，不查询/清理数据库，不prune |
| 既有Nginx配置、80/443入口、域名/生产证书私钥 | 不修改、不reload、不替换；未来新vhost须备份与明确授权 |
| SSH、用户、授权密钥、防火墙 | 不修改，不通过重复换公钥解决当前出站问题 |

工具在目标上运行后会输出所有既有资源的稳定代号/短ID保护表；分类仍由所有者确认，未知项不自动解除保护。

## 离线交付与验证

- [只读审计工具](../../scripts/audit_existing_server.py)：只读命令白名单、固定本机Docker socket、无shell执行，输出脱敏JSON。
- [Mac/服务器控制台命令](../operations/EXISTING_SERVER_READONLY_AUDIT.md)：只用现有ops/授权身份，单次SSH尝试、严格主机指纹；stdin执行，不在服务器写脚本。
- [隔离部署及备份/回滚草案](../proposals/EXISTING_SERVER_ISOLATION_PLAN.md)：仅方案，不加载配置或执行部署。
- [工具验证](../../backend/tests/test_server_audit_tooling.py)：使用纯合成metadata/临时文件，未运行真实审计或访问服务器。

离线测试覆盖禁止命令、固定Docker端点、错误输出隐藏、密钥/.env/软链接拒读、IPv4/IPv6/UDP端口解析、
CIDR与上级路由冲突、缺数据不能判安全、Nginx/URI/域名脱敏、证书日期/SAN及既有资源保护。
本地22项通过；后续完整CI结果在Draft PR记录，不把工具测试PASS写成SERVER_AUDIT=PASS。

取得目标上的脱敏审计JSON后，先复核主机、服务归属、完整Nginx结构、证书、端口/网络与资源余量，
再评审下一阶段变更。审计未完成和授权未满足前，READY_FOR_DEPLOYMENT始终NO。

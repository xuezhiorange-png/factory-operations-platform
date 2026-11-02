# 现有测试服务器：只读审计操作

TASK_ID：FACTORY_OPS_M1_03B_EXISTING_SERVER_AUDIT。
本轮只读，不能以这份操作说明作为配置修改、部署、Nginx reload、Docker网络调整或豆包操作授权。
Codex 当前没有可用 SSH 出站通道，已经停止远程尝试；目标服务器事实尚未采集。
不要通过重复换公钥、重建用户或修改防火墙解决 Codex 的出站限制。

## 在 Mac 使用现有授权 SSH 身份

先在本机取得本 Draft PR 的 [审计脚本](../../scripts/audit_existing_server.py)。
目标地址使用任务指定值，现有私钥仅保留在自己的 Mac，不上传到聊天、GitHub或Codex。
推荐用 `-i` 明确选择已有授权身份；只有现有SSH配置已明确选择同一IdentityFile时才按该配置省略它。
仅在agent中加载但未配置的自定义身份，不能配合IdentitiesOnly=yes盲目省略 `-i`。不生成新密钥。

```bash
umask 077
AUDIT_HOST='填写本次任务指定的测试服务器IP'
AUTHORIZED_SSH_KEY="$HOME/.ssh/填写已有授权私钥文件名"
AUDIT_OUTPUT="$HOME/factory-ops-server-audit.json"

ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -o UpdateHostKeys=no \
  -o ConnectTimeout=8 -o ConnectionAttempts=1 -o IdentitiesOnly=yes \
  -i "$AUTHORIZED_SSH_KEY" "ops@$AUDIT_HOST" \
  'PYTHONDONTWRITEBYTECODE=1 python3 - --collect' \
  < scripts/audit_existing_server.py > "$AUDIT_OUTPUT"

# 仅在 Mac 验证输出是 JSON；不上传未经核对的原始配置或 SSH 输出。
python3 -m json.tool "$AUDIT_OUTPUT" > /dev/null
```

脚本经 stdin 执行，不在服务器保存脚本/报告，不安装软件，不创建目录或文件。
SSH/系统本身可能产生正常访问审计日志，不代表修改了应用配置。
已知主机指纹不匹配、连接失败或无有效身份时停止；不得改成 StrictHostKeyChecking=no / accept-new，
不得反复尝试、修改 authorized_keys 或服务器安全配置。指纹/身份由已有受控渠道核实。

只有已有非交互 sudo 权限并由操作者选择时，远程命令可改为：

```text
PYTHONDONTWRITEBYTECODE=1 python3 - --collect --sudo-readonly
```

它只给白名单元数据命令添加 `sudo -n`，不询问密码、不修改 sudoers 或用户组。
无法读取的项保持 BLOCKED；Nginx 配置只以当前用户权限读取，不自动提权读取配置。

## 在服务器控制台运行

使用已经授权的控制台账号，将同一脚本内容直接粘贴进 Python stdin：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - --collect <<'PY'
# 在此粘贴 scripts/audit_existing_server.py 的完整内容，再输入结束标记。
PY
```

不重定向到服务器文件，不 git clone、scp、pip install、apt install 或 chmod。
要求已有 Python3（建议3.10+）、Docker CLI、ss/ip、OpenSSL。缺命令/权限时记录缺项，不为补齐报告安装或修改服务器。
先确认控制台属于目标主机，脚本不能自行证明主机身份。不能把 Mac/Codex 本机资源填成目标服务器资源。

## 收集范围与脱敏

- CPU核数/负载、MemAvailable/Swap、根与计划目录父分区空间、Docker数据根空间（有权限时）、版本。
- 所有现有容器（含停止的）、发布端口、Docker网络/卷、运行中的宿主服务；不读取卷内容或查询数据库。
- TCP/UDP监听与Docker发布映射交叉检查22、80、443、3001、8000、8101，以及候选18443。
- PR #9 固定 `172.30.83.0/28` 与已有Docker IPAM、非默认宿主路由重叠检查。
- 静态Nginx配置中的域名代号、监听端口、代理目标类别/端口、公钥证书日期/SAN匹配代号。

容器/网络保留可识别的短ID，其余服务名、域名、路径和卷名用稳定代号。
不输出 `.Env`、Cmd、Entrypoint、完整Labels、URI路径/query、Authorization、JWT、证书私钥或员工信息。
配置中的 ssl_certificate_key 不进入证书读取列表；密钥/.env/credentials路径及其软链接被拒绝。
命令错误仅标记不可用，原始stderr不会出现在报告中。

白名单不允许 stop/restart/exec/cp/prune、网络/卷变更、compose up、nginx -t/-T/-s、防火墙或数据库命令。
本轮没有为“验证配置”运行 nginx -t/-T，它们可能打开配置引用的日志文件，留待明确授权的变更阶段。

## 报告的边界

`NOT_OBSERVED` 只表示快照中未观察到占用，不是端口可分配保证；部署前还要重新核对预留与计划任务。
网络无重叠也只在采集时有效。缺少Docker/路由资料时必须为 UNVERIFIED，不能猜测安全网段。
名称关键词仅是冷库监控/规划的线索，`classification_verified=false` 需要所有者确认。
**所有既有资源默认不可触碰，包括未分类服务。**

Nginx扫描不是运行中有效配置证明：不假设未展开的include、容器内置文件或相对路径等于不存在。
容器内配置不通过docker exec读取；bind来源可读时扫描其元数据，无法核实的保持UNVERIFIED。
证书只核对本地公钥证书日期与SAN，不能证明公网证书链、域名解析、实际服务的证书或TLS连通。
权限不足或配置不完整时由所有者在受控控制台补充核对，不能公开原始配置/密钥来排障。

工具始终输出 `ready_for_deployment=NO`。人工复核、私有备份/恢复验证、资源预算、域名和变更授权
没有完成之前不得部署。详见 [隔离方案](../proposals/EXISTING_SERVER_ISOLATION_PLAN.md)。

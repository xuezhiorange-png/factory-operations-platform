# 现有测试服务器的运维 MCP 隔离方案（待审计）

状态：PLANNED，目标服务器尚未审计，READY_FOR_DEPLOYMENT=NO。
本文件不是部署操作手册或变更授权，不直接运行PR #9的公网模板。
不得为上线腾出既有22/80/443/3001/8000/8101、停服务、改防火墙或连接现有网络/数据库。

## 需要先取得的事实

完成 [只读审计](../operations/EXISTING_SERVER_READONLY_AUDIT.md)，由所有者确认：

- 所有当前容器、宿主服务、网络和卷的归属，特别是冷库监控/规划与未知服务；全部纳入保护表。
- CPU负载、MemAvailable/Swap、Docker与拟用目录所在分区空间；不能把一次快照当成持续容量保证。
- 既有Nginx是宿主进程、host-network容器还是bridge容器，完整include/vhost、上游与TLS使用方式。
- 候选域名实际归属、DNS指向、证书链/期限与续签职责；不复用或替换冷库生产密钥。
- 所有指定端口和候选18443的实际监听/发布/预留；所有Docker IPAM及宿主/VPN路由是否重叠。

缺一项维持NO，不凭容器名、证书文件存在或“未观察到监听”自动准入。

## 独立资源候选

| 项目 | 草案 | 当前状态 |
|---|---|---|
| Compose项目 | factory_ops_mcp_sandbox | UNVERIFIED，确认与旧项目不重名 |
| 工作目录 | /srv/factory-ops-mcp-test | UNVERIFIED，须为空且独立，不在冷库/规划目录下 |
| 私密配置目录 | 该项目独立的private目录，0700/secret按UID最小读取 | PLANNED，不复用任何现有密码/密钥 |
| PostgreSQL17 | 新库factory_ops_mcp_synthetic与新角色、独立命名卷 | PLANNED，不使用或挂载旧数据库/卷 |
| 本机网关 | 127.0.0.1:18443 | UNVERIFIED，端口候选而非已保留 |
| API/PG | 容器内部8000/5432，无宿主端口 | PLANNED，不发布到公网 |
| 私网 | 新项目独有gateway/database；网段须审计后分配 | UNVERIFIED，不连接既有网络 |
| 测试域名 | factory-ops-mcp-test.<OWNER_CONFIRMED_BASE_DOMAIN> | UNVERIFIED，不能作为已可访问URL |

PR #9 gateway 为 `172.30.83.0/28`，proxy `.2`、api `.3`，Uvicorn只信任 `.2`。
检查与**全部现有Docker网段和非默认路由**重叠，不能只比字符串相等；`172.30.0.0/16`也构成冲突。
PR #9数据库网络自动分配，现有服务器接入前也要确认地址池与独立网段规划。
如需另选CIDR，必须同步调整新项目proxy/API固定IP及Uvicorn可信代理地址，并重跑隔离测试；不改旧网络。

资源预算待审批：可考虑API384MiB、独立网关128MiB、PG512MiB上限，另保留至少1GiB宿主余量与磁盘余量；
CPU总配额应根据冷库现有峰值与实际核数制定。PR #9的DB尚无此共享服务器资源预算，不能照搬即部署。
无充足余量则保持BLOCKED，不能通过压缩旧服务或删卷解决。

## 优先方案：既有Nginx新增独立虚拟主机

仅当审计确认既有Nginx运行于宿主或host-network容器、可以访问宿主loopback时：

```text
外部HTTPS443（现有Nginx，独立新server_name与测试证书）
  → 精确/mcp
  → https://127.0.0.1:18443（新项目独立TLS网关）
  → 私网FastAPI:8000
  → 私网PostgreSQL17:5432（仅合成数据）
```

不新增公网443监听者，不改旧vhost的server_name/default_server/location，不给旧应用加路径改写。
新vhost只代理精确 `/mcp`，其余路径404；不暴露/docs、/api、登录、管理接口或数据库。
转发固定受控Host与HTTPS scheme，保留Origin/x-aily-jwt/协议与Accept，覆盖客户端伪造转发头，
并沿用有界body/超时/限流、no-store和脱敏日志。不得增加匿名发现或共享Token例外。

两段TLS使用独立材料：公网证书由域名所有者按现有受控流程管理；内层证书使用新测试项目专用key/CA，
不复制旧冷库生产私钥。外层到内层必须验证证书链与SAN，使用对应SNI（例如专用内层localhost证书），
不得用proxy_ssl_verify off绕过自签证书。具体路径与签发方式待审批，当前不签证书、不改Nginx。

如果既有Nginx是bridge容器，容器里的127.0.0.1不是宿主loopback，不能直接套用上图。
必须先由所有者核实原入口的连通结构，再评审新项目的独立连接方法；不能为接入直接connect旧网络、
重建旧Nginx或把本机端口改成0.0.0.0。未解决前保持NO，不抢占443建立第二个公网入口。

## 变更前的备份及恢复验证（尚未执行）

1. 所有者批准精确变更范围、窗口与允许的平滑reload；当前审计授权不包含reload。
2. 在受控私有备份位置保存Nginx有效配置及include依赖、属主/权限/软链接清单、文件hash，
   以及现有容器ID/镜像标识/端口/网络/卷元数据。原始配置可能含凭据，不进GitHub或聊天。
3. 不读取/导出旧数据库内容，不复制生产私钥到本项目；涉及证书/密钥恢复能力由所有者在受控环境核对。
4. 将备份恢复到隔离目录，比较hash/属主/权限/include；用匹配版本的Nginx离线验证副本，
   日志与pid指向演练目录，不覆盖活跃配置或占用80/443。记录可恢复证据与操作者。
5. 备份或恢复演练未通过，禁止任何配置写入。之后的nginx -t、平滑reload、新项目启动也需明确授权。

## 下一阶段回滚设计

先撤新vhost的MCP入口，再在已授权范围恢复已验证的配置副本并做语法检查/平滑reload；
不得stop/restart既有Nginx或冷库服务。无法保证无影响则停止变更，交所有者处理。
仅停止/移除本项目自己新增的服务，保留其审计与必要合成数据备份；不做全局Docker清理，不删任何旧卷/网络。
不降级原平台业务schema，不改SSH/用户/防火墙/生产密钥。

真实豆包配置、身份绑定或工具联调不属于本轮服务器审计；继续保持UNVERIFIED。
审计完成、保护表确认、容量与路由满足、备份恢复通过、域名/TLS就绪和明确变更授权后，才评审是否可部署。

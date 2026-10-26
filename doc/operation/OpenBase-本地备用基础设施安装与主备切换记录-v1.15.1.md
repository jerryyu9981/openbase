# OpenBase 本地备用基础设施安装与主备切换记录

| 项 | 内容 |
|---|---|
| 文档版本 | v1.15.1 |
| 文档状态 | [Approved] |
| 适用环境 | 本机联调环境（Windows，D 盘） |
| 主用基础设施 | 局域网 `192.168.0.151` |
| 备用基础设施 | 本机 `127.0.0.1`（根目录 `D:\infra`） |
| 编写日期 | 2026-10-20 |
| 编写人 | 研发（AI 辅助执行） |

## 修订历史

| 版本 | 日期 | 修订人 | 修订说明 |
|---|---|---|---|
| v1.0.0 | 2026-10-20 | 研发 | 首版：明确「局域网主用 + 本地备用」定位，回滚 9 个 env 文件的本地化改写，落地启动期主备探测与备用覆盖层 |
| v1.1.0 | 2026-10-20 | 研发 | 补齐 Neo4j（harness）与 MinIO，新增备用基础设施启动脚本 |
| v1.2.0 | 2026-10-20 | 研发 | 根目录迁至 `D:\infra` 并完成目录规范化：归档历史版本、Qdrant 统一到 1.7.4、MinIO/Neo4j bin-src-data 分区、Neo4j 数据持久化；主备切换脚本去除明文凭据（改从 `.env.shared-infra` 读取）；七服务复测全绿 |
| v1.3.0 | 2026-10-20 | 研发 | 新增 §9 主备切换逻辑验证（5 场景，含强制模式）、§10 运维注意事项（Redis AOF 可写目录、启动入口现状）；补充端到端切换证据 |
| v1.3.1 | 2026-10-20 | 研发 | 修复 MinIO「无许可证离线模式，S3 操作全部拒绝」：AIStor 二进制替换为社区版 RELEASE.2025-07-23（GNU AGPLv3），旧二进制与 AIStor 格式数据归档至 `D:\infra\archive\minio-aistor-*`；重建数据目录并实测建桶/上传/列举/删除全部通过 |
| v1.4.0 | 2026-10-20 | 研发 | 补齐 `D:\infra` 启停脚本（start-infra.ps1 / stop-infra.ps1）：WMI 脱沙箱启动、逐组件就绪等待、凭据零硬编码；完成 stop→start 闭环实测并记录脚本约定 |
| v1.5.0 | 2026-10-21 | 研发 | 新增 §12 打通 LLM 与 DPS 认证：OpenLLM 服务账号/租户/Key 落位、DPS 三张 RBAC/组织表补数；定位并修复「DPS 403 组织不存在」根因为备用库未按主用固定 UUID 复刻（`OPENBASE_DPS_CODE_MAP` 注入）；走查账号口令重置为统一临时口令 |
| v1.6.0 | 2026-10-21 | 研发 | 新增 §13 LLM 走查数据注入：登记 1 个 openai 兼容 provider 与 3 条模型（2 chat + 1 embedding），`llm-proxy/models` 由空数组变为 3 条；明确占位 provider 不具备真实推理能力（chat 返回 5001）。另修复前端 5173 仅监听 IPv6（`::1`）导致 `127.0.0.1` 无法访问的问题（启动参数显式 `--host 127.0.0.1`） |
| v1.7.0 | 2026-10-21 | 研发 | 新增 §14 LLM 对话链路走查：以标准库实现 OpenAI 兼容 mock（端口 8025）并接入启动脚本；provider `api_base_url` 指向 mock；`llm-proxy/chat` 与 `chat/stream` 均实测通过（非流式 200、流式 18 个 SSE 事件） |
| v1.8.0 | 2026-10-21 | 研发 | 新增 §15 局域网 Ollama 与远程 DeepSeek 接入：注入 2 个 provider + 6 条模型；DeepSeek 改为本地反代（8026）从进程环境注入 Key、库内不存明文；OpenLLM 适配器超时改为读 `provider.config.timeout`，OpenBase 上游超时放宽至 300s；`DEFAULT_LLM_MODEL` 对齐 `qwen2.5:0.5b` 并重启 |
| v1.8.1 | 2026-10-21 | 研发 | DeepSeek Key 经密钥文件（`%USERPROFILE%\.openbase\deepseek_api_key.txt`）配置完成，反代 `key_configured=true`；`deepseek-chat` 真实调用通过（200，12.3s，64 tokens） |
| v1.9.0 | 2026-10-25 | 研发 | **启动期主备探测固化为受管入口**：`scripts/service-orchestrator.ps1` 新增 `-DbMode auto/primary/standby/off` 与 `-Action dbcheck`；每次 start/startcheck/monitor 前探测主用 PostgreSQL，异常自动切本机 `127.0.0.1:5432`；主备均不可达拒绝启动（退出码 2）；覆盖通过子进程环境变量（不改写 `.env`），证据落 `doc/test/evidence/ops/**`；新增 §16（含实测矩阵与边界），§4 入口同步 |
| v1.10.0 | 2026-10-25 | 研发 | **P1 落地**：① `monitor` 周期复检（默认 ≥60s，`-DbRecheckSec` 可缩短）——主用恢复/失联**只提示不回切**，证据 `db-monitor-recheck-*.json`；② Redis/Qdrant/Neo4j/MinIO 同批 TCP 探测，**仅提示不阻断**（PG 为唯一硬门禁），纳入证据 `dependencies`；③ `dbcheck -Json` 机器可读输出（schema v2）；新增 §16.7，§16.2/§16.5 同步 |
| v1.11.0 | 2026-10-25 | 研发 | **P0 数据面探针 + 四设施切换（用户决策）**：新增 `scripts/infra_probe.py`（stdlib，不含第三方依赖）——PG `select 1`、Redis `PING+DBSIZE`、Qdrant `GET /collections`、Neo4j `RETURN 1`、MinIO `health/ready`；探测由 TCP 升级为**数据面**（探针不可用显式回落 TCP 并记 degraded）；**主用数据面不通即切备用**（PG 硬门禁 + 四设施覆盖：Redis/Qdrant/Neo4j/MinIO 的共享键与各仓自有键）；**数据面同步问题暂时挂起**，切换强制 WARN 留痕；证据 schema v3（新增 `data_plane`）；新增 §16.8，守门用例 15 → **20 例** |
| v1.12.0 | 2026-10-25 | 研发 | **每次启动服务前校验数据库（用户决策）**：`Start-Service` 统一入口新增 `Assert-ServiceDataPlane`——全量启动、`-Only` 单服务、monitor 自愈重启**一律先校验**该服务依赖（pg/redis/qdrant/neo4j）；当前通道共享库不可用 ⇒ **拒绝启动该服务**，其它设施 DOWN ⇒ WARN 不阻断；`-ProbeTtlSec`（默认 60s）内复用探测结果、过期按需重探；新增 §16.9，守门用例 20 → **21 例** |
| v1.13.0 | 2026-10-25 | 研发 | **D-05 解除：解释器解析与运行环境自检**。系统 Python 3.12.10（`D:\Python`）已安装，新建专用 venv `D:\venvs\openbase`（`pip install -e .` 全依赖）；`Start-Service` 新增候选链解析（`OPENBASE_<SVC>_PYTHON` → `-PythonHome` → `OPENBASE_PYTHON` → 各仓 venv → 系统 Python → 3.13 桥接 → PATH），每个候选做 `import uvicorn` 自检，全部失败给出可读错误并拒绝该服务；实测单服务启动成功（PID 9100、健康检查 3s、stop 后端口释放）；新增 §16.10，守门用例 21 → **23 例** |
| v1.14.0 | 2026-10-25 | 研发 | **OpenLLM / OpenMemory 专用 venv 落地**（`D:\venvs\openllm`、`D:\venvs\openmemory`），候选链同步补入；OpenLLM 实测启动 + `/health` 200，OpenMemory 依赖导入通过；记录上游 requirements 缺口（`python_requires` 非法行、`httpx==0.26` 与 `mcp>=1.0` 冲突、缺 `psycopg/pyjwt/numpy/qdrant-client/OTel gRPC`）与本机补丁（`bcrypt<5`、`qdrant-client==1.7.3`）；新增 §16.11 |
| v1.15.0 | 2026-10-25 | 研发 | **全栈 7 服务一次启动成功**：修复 oidc-idp 解释器自检（pgAdmin 桥接需门控环境）、frontend 启动方式（`npm.cmd` 在 WMI 下静默退出 → 直调 `node + vite.js`）；openllm/openrag 冷启动 >60s → 服务级 `HealthWait=180`，frontend `HealthWait=120`；dps 运行时确定为 OpenRAG `.venv3`（依赖经 `cross-libs.pth` 注入）；全量检查 **27 PASS / 0 FAIL / 0 SKIP**；新增 §16.12 |
| v1.15.1 | 2026-10-26 | 研发 | **前端全页面走查（77 页）驱动的三项修复**：① 恢复 `.env` 中被 2026-10-21 轮换写坏、OpenLLM 未登记的 `OPENBASE_LLM_API_KEY`（SHA-256 与库内 `openbase-gateway-v143` 一致），租户映射改回 `tenant-1`；② 编排器**全服务脱离会话启动**并**白名单传递进程环境**（WMI 子进程不继承调用方环境 → 丢 `POSTGRES_URL` → openbase 退化内存模式，库依赖接口全 500）；③ 健康检查通过后落盘**真实监听 PID**（`stop` 不再留孤儿）。新增 §16.13；守门用例 23 → **24 例** |

## 1. 背景与定位

- 各仓 `.env` / `.env.shared-infra` 中登记的基础设施地址为局域网 `192.168.0.151`，该地址是**唯一主用环境**。
- 本机 `127.0.0.1`（`D:\infra`）上的同名组件仅作为**备用环境**：只有主用不可达时才启用，**不取代主用**。
- 因此配置文件必须保持主用地址；备用能力通过**启动期覆盖**实现，不改写配置文件。

## 2. 主备组件对照

| 组件 | 主用 | 备用 | 备用版本 | 备用目录 |
|---|---|---|---|---|
| PostgreSQL | `192.168.0.151:5432` | `127.0.0.1:5432` | 17（既有安装） | `D:\PostgreSQL\17` |
| Redis | `192.168.0.151:6380` | `127.0.0.1:6380` | 8.10.2 | `D:\infra\redis8` |
| Qdrant | `192.168.0.151:6333/6334` | `127.0.0.1:6333/6334` | 1.7.4 | `D:\infra\qdrant` |
| ChromaDB | `192.168.0.151:8001` | `127.0.0.1:8005` | 1.5.9 | `D:\infra\chroma` |
| MinIO | `192.168.0.151:9000/9001` | `127.0.0.1:9000/9001` | RELEASE.2025-07-23（社区版 AGPLv3） | `D:\infra\minio` |
| Neo4j | `192.168.0.151:7474/7687` | `127.0.0.1:7474/7687` | 内核 5.26.16（harness） | `D:\infra\neo4j` |

凭据一律不写入本文件：PostgreSQL / MinIO 等共享键取值见 `OpenBase\.env.shared-infra`；Redis 备用口令见 `D:\infra\redis8\redis-6380.conf`。

### 2.1 备用与主用的已知差异

| 差异 | 原因 |
|---|---|
| Chroma 端口 8005 | 本机 8001 已被 OpenLLM 占用 |
| Redis 8.10.2 | 运行时 `redis-py 8.0.1` 默认 RESP3（发送 `HELLO 3`），Redis 5.0 不支持 |
| Qdrant 1.7.4 | 运行时 `qdrant-client 1.7.3` 无法解析 1.19.2 的 collection 响应 |
| Neo4j 由 `neo4j-harness` 启动 | 官方发行源 `dist.neo4j.org` / `neo4j.com/artifact.php` 在本机出口返回 403 |
| Redis 目录名为 `redis8` | 版本化命名，与 `archive\redis-5.0.14` 对应；目录内含发行包、`data`、运行配置与日志 |

## 3. 目录布局（`D:\infra`）

```
D:\infra\
  README.md                 # 组件清单与启停说明
  start-infra.ps1           # 统一启动（端口探测 + WMI 脱离式启动）
  stop-infra.ps1            # 统一停止（仅限备用组件端口）
  migrate-layout.ps1        # 目录规范化一次性脚本（幂等）
  redis8\                   # Redis 8.10.2
    Redis-8.10.2-Windows-x64-msys2\   # 发行包（exe/dll）
    redis-6380.conf                   # 运行配置
    data\                             # AOF/RDB
    redis.log
  qdrant\                   # Qdrant 1.7.4
    bin\ config\ storage\ snapshots\ logs\
  chroma\                   # ChromaDB
    lib\ data\ logs\ run_chroma.py
  minio\                    # MinIO
    bin\ data\ logs\
  neo4j\                    # Neo4j 5.26.16（harness）
    src\ lib\ classes\ data\ logs\ pom.xml
  jdk21\                    # Neo4j 运行所需 JRE（21.0.12.1）
  maven\                    # 拉取 Neo4j 依赖（含华为云镜像 settings.xml）
  downloads\                # 安装包归档（zip）
  logs\                     # 统一运行日志（start/stop/migrate）
  archive\                  # 历史版本归档，不参与运行
  sqlite\                   # 既有 SQLite 文件（OpenLLM 备用路径）
  postgresql\               # 既有安装说明（见 README）
```

## 4. 启停与切换

```powershell
# 启动备用基础设施（已监听端口自动跳过）
powershell -NoProfile -ExecutionPolicy Bypass -File D:\infra\start-infra.ps1

# 停止备用基础设施
powershell -NoProfile -ExecutionPolicy Bypass -File D:\infra\stop-infra.ps1

# 启动七个应用服务（受管入口；默认 -DbMode auto：探测主用 PostgreSQL，异常自动切本机 127.0.0.1:5432）
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\service-orchestrator.ps1 -Action start

# 仅探测共享库主备（不启动任何服务）
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\service-orchestrator.ps1 -Action dbcheck
```

- 启动横幅/日志会打印实际生效模式：`共享库探测：primary=…/standby=127.0.0.1:5432 … ⇒ mode=primary|standby`。
- 工程内 `doc/tmp/start-local-infra.ps1` 为备用基础设施启动的薄封装，事实源为 `D:\infra\start-infra.ps1`。
- 备用覆盖仅作用于**子进程环境变量**，不改写任何 `.env`；主用恢复后重启即自动回主用。
- **历史说明**：早期临时入口 `doc/tmp/start-all-services.ps1` 已废弃，能力于 v1.9.0 固化进
  `scripts/service-orchestrator.ps1`（详见 §16）。

PostgreSQL 备用模式覆盖的键（P0，v1.9.0）：

| 服务 | 覆盖键 | 值来源 |
|---|---|---|
| openbase | `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_URL`（及 `OPENBASE_DB_URL` 若声明） | `.env.shared-infra` 主用 DSN 仅替换主机端口 |
| dps | 同上（定义期读取 `$env:POSTGRES_URL`） | 同上 |
| openllm | `DATABASE_URL` | 各仓 `.env` 原值仅替换主机端口（保留 scheme/凭据/库名） |
| openrag | `OPENRAG_DATABASE_URL` | 同上 |
| openmemory | `OPENMEMORY_DB__HOST` / `OPENMEMORY_DB__PORT` | 备用主机与端口 |

> Redis / Qdrant / Neo4j / MinIO 的备用覆盖暂**未**纳入 P0（见 §16.5 后续阶段），仍按原方式由
> `D:\infra\start-infra.ps1` 启动 + 手工确认；P0 只解决「共享数据库（PostgreSQL）」的启动期主备。

## 5. 本次整理记录（v1.2.0）

| 项 | 处理 |
|---|---|
| 历史版本归档 | `redis`（5.0.14）、`qdrant`（1.19.2）、`qdrant-client-lib`、`qdrant-client-only` 移入 `archive\` |
| Qdrant 统一 | 1.7.4 由 `qdrant17\` 迁入 `qdrant\{bin,config,storage,snapshots,logs}`，空目录清理 |
| MinIO | 二进制归入 `minio\bin\`，数据 `minio\data\`，日志 `minio\logs\` |
| Neo4j | 源码归入 `neo4j\src\`，日志归入 `neo4j\logs\`，重新编译 `classes`（数据目录持久化到 `neo4j\data`） |
| Chroma | 日志归入 `chroma\logs\`，启动器落在 `chroma\run_chroma.py` |
| 凭据治理 | `start-infra.ps1` 不再硬编码任何口令，统一从 `.env.shared-infra` 读取；Redis 口令只存在于其运行配置 |

## 6. 实测结果（2026-10-20 18:56，备用模式）

| 组件 | 端口 | 结果 |
|---|---|---|
| PostgreSQL | 5432 | UP |
| Redis | 6380 | UP（未认证请求返回 `NOAUTH`，符合预期） |
| Qdrant | 6333 / 6334 | UP（版本 1.7.4） |
| ChromaDB | 8005 | UP（heartbeat 200） |
| Neo4j | 7474 / 7687 | UP（HTTP 200） |
| MinIO | 9000 / 9001 | UP（`/minio/health/live` 200） |

| 应用 | 端口 | 结果 |
|---|---|---|
| openllm | 8001 | `healthy`（postgresql / redis 均 healthy） |
| openrag | 8010 | `healthy`（database / vector_store up） |
| openmemory | 8020 | `healthy`（vector / metadata / session 均 healthy） |
| dps | 8030 | liveness 200 |
| openbase | 8000 | `openapi.json` 200 |
| oidc-idp | 8090 | 健康检查通过 |
| frontend | 5173 | 200（仅监听 IPv6，访问用 `http://localhost:5173`） |

## 7. 已知限制

1. Neo4j 备用为 harness 嵌入式实例，**未启用认证**：客户端仍传 `neo4j/<口令>`，服务端忽略；数据已持久化到 `D:\infra\neo4j\data`。
2. Qdrant 备用 storage 由 1.7.4 初始化，OpenMemory 首次启动会创建 collection 与索引；若 Qdrant 刚启动正在加载，可能出现一次初始化超时，重试即可。
3. MinIO 已由 AIStor 切换为社区版（RELEASE.2025-07-23，GNU AGPLv3）：**无许可证限制，S3 读写正常**（建桶/上传/列举/删除实测通过）；旧 AIStor 二进制与数据已归档至 `D:\infra\archive\minio-aistor-*`。默认凭据仍取自共享 env（`minioadmin`），建议后续轮换。
4. 备用模式下直接手工启动单个服务会读到主用地址并连接失败，属预期行为；请统一使用启动脚本。

## 8. 回退

1. 主用恢复：直接重启应用服务（默认 `auto` 自动回主用），无需改配置。
2. 彻底下线备用：停止 `.infra` 目录内各组件进程；配置文件与数据保留，不影响主用。
3. 目录回滚：`archive\` 内保留迁移前实例，可直接移回原位置。

## 9. 主备切换逻辑验证（2026-10-20）

验证脚本：`doc\tmp\verify-infra-switch.ps1`（只读演练，不启动/重启任何进程）。

方法：以 `doc\tmp\start-all-services.ps1` 为唯一事实源生成等价副本，仅在 `Test-PrimaryInfra` 入口注入 `FORCE_PROBE` 开关模拟主用可达性（`$PrimaryHost` 保持真实值），并在启动循环前插入诊断块后 `exit`。凭据输出一律脱敏为 `:***@`。

| 场景 | 探测条件 | InfraMode | 期望 | 实际 | 结论 |
|---|---|---|---|---|---|
| A | 主用可达（强制 up） | auto | primary，不覆盖 | `mode=primary`，`overrides_applied=False`，共享键保持 `192.168.0.151`、Chroma `8001` | PASS |
| B | 主用不可达（强制 down） | auto | local，覆盖生效 | `mode=local`，`overrides_applied=True`，共享键 `127.0.0.1`、Chroma `8005` | PASS |
| C | 真实探测（`192.168.0.151` 实际不可达） | auto | local | `mode=local`，覆盖生效 | PASS |
| D | 真实探测为下行 | 强制 `primary` | 强制优先，走主用 | `mode=primary`，不覆盖 | PASS |
| E | 主用可达 | 强制 `local` | 强制优先，走备用 | `mode=local`，覆盖生效 | PASS |

覆盖值核对（场景 B/C 一致）：

| 键 | 覆盖结果 |
|---|---|
| `POSTGRES_URL` / `POSTGRES_HOST` | `127.0.0.1:5432` |
| `REDIS_URL` | `127.0.0.1:6380`（本机口令，输出脱敏） |
| `CHROMA_PORT` / `CHROMA_URL` | `8005` / `http://127.0.0.1:8005` |
| `QDRANT_URL` / `NEO4J_URI` | `http://127.0.0.1:6333` / `bolt://127.0.0.1:7687` |
| `OPENMEMORY_GRAPH__URI` / `..._CACHE__HOST` / `..._VECTOR__HOST` | `bolt://127.0.0.1:7687` / `127.0.0.1` / `127.0.0.1` |
| `OPENRAG_DATABASE_URL` / `OPENRAG_QDRANT_URL` | `postgresql+asyncpg://…@127.0.0.1:5432/nuct` / `http://127.0.0.1:6333` |
| `OPENBASE_REDIS_URL` | `redis://:***@127.0.0.1:6380/0` |

端到端证据（真实以 local 模式拉起，2026-10-20 19:19）：

| 项 | 结果 |
|---|---|
| 启动横幅 | `infra mode: local (primary=192.168.0.151, fallback=127.0.0.1)` |
| openllm `/health` | `healthy`，`postgresql=healthy`、`redis=healthy` |
| openrag `/api/v1/system/health` | `healthy`，`database=up`、`vector_store=up` |
| openmemory `/health` | `healthy`，vector / metadata / session 均 healthy |
| openbase 登录 | `POST /api/v1/auth/login` 成功返回 token |
| 七服务端口 | 8000/8001/8010/8020/8030/8090/5173 全部监听 |

**判定语义说明**：探测对 `5432`、`6380`、`6333` 三者取"全部可达"才判定主用；任一不通即整体降级到备用，不产生"PG 走主用、Qdrant 走本地"的混合态（避免跨环境数据割裂）。

## 10. 运维注意事项

1. **Redis 数据目录必须可写**：本机存在文件写入策略限制，Redis 以默认工作目录启动时 AOF 写入会被拒（`MISCONF Errors writing to the AOF file: Permission denied`），表现为 OpenLLM `/health` 的 `redis=unreachable`。启动时须显式指定可写目录：
   ```
   redis-server.exe redis-6380.conf --dir /cygdrive/d/infra/redis8/data --logfile /cygdrive/d/infra/redis8/redis.log
   ```
2. **启停脚本**：`D:\infra\start-infra.ps1` 与 `D:\infra\stop-infra.ps1` 已补齐（详见 §11），基础设施无需再逐组件手工启动。
3. **进程保活**：基础设施与应用服务均需以脱离会话方式启动，否则会话回收时会被一并终止。
4. **primary 模式下的覆盖表**：`LocalServiceEnv` 在 primary 模式下仍会被构造，但合并条件含 `$ResolvedMode -eq 'local'`，不会注入；诊断输出中看到本地地址属预期，不代表已生效（以 `overrides_applied` 为准）。
5. **前端必须显式绑定 IPv4**：Vite 默认 `localhost` 在本机解析为 `::1`，只监听 IPv6 回环，`http://127.0.0.1:5173` 会连接失败。启动参数须带 `--host 127.0.0.1`（已在 `start-all-services.ps1` 固化）；排查时用 `Get-NetTCPConnection -LocalPort 5173` 看 `LocalAddress` 是 `::1` 还是 `127.0.0.1`。

## 11. 启停脚本（v1.4.0 补齐）

| 脚本 | 作用 |
|---|---|
| `D:\infra\start-infra.ps1` | 启动 Redis / Qdrant / Chroma / Neo4j / MinIO；已监听端口自动跳过；支持 `-Only redis,qdrant` 选择性启动 |
| `D:\infra\stop-infra.ps1` | 按端口停止上述五个组件（按 PID 去重），不触碰 PostgreSQL 与七个应用服务；支持 `-Only` |

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\infra\start-infra.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File D:\infra\stop-infra.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File D:\infra\start-infra.ps1 -Only redis
```

实现约定（已在脚本中固化）：

| 约定 | 原因 |
|---|---|
| 通过 `Invoke-CimMethod Win32_Process::Create` 脱离会话启动 | 会话回收时不连带终止；且 Qdrant/Chroma 需写自身数据目录，普通子进程会因写入策略失败 |
| 逐组件启动 + 端口就绪轮询（redis/qdrant/minio 60s，chroma/neo4j 90s） | Neo4j 首次加载与 Redis AOF 回放较慢，"启动即打印成功"会误判 |
| Redis 显式 `--dir /cygdrive/d/infra/redis8/data --logfile ...` | 规避 AOF 写入被拦截导致的 `MISCONF` |
| MinIO 凭据从 `.env.shared-infra` 读取 | 脚本不落明文口令 |
| 脚本以 UTF-8（带 BOM）保存 | PowerShell 5.1 读取无 BOM 的 UTF-8 中文注释会误判语法 |

实测闭环（2026-10-20 19:37 起）：`stop-infra.ps1` 停净五个组件 → `start-infra.ps1` 全部拉起 → Qdrant collections、Chroma heartbeat、Neo4j HTTP、MinIO health、Redis `PING/SET/GET` 全部通过；应用侧七服务健康。

## 12. LLM 与 DPS 认证打通（v1.5.0）

走查前 `llm-proxy` 与 `dps-proxy` 均返回 401/403。两处问题相互独立，按下述口径处置。

### 12.1 OpenLLM 侧（LLM 认证）

| 项 | 处置 |
|---|---|
| 服务账号 | 在 OpenLLM 注册 `openbase-svc`（`public.users.role=admin`），并将其 `organization_id` 指向 `demo` 租户 |
| 租户 | 经 `POST :8001/api/v1/tenants` 建 `demo` 租户（`public.tenants.tenant_code=demo`），作为 Key 的归属外键 |
| API Key | 新建 `openbase-gateway-v2`；**明文仅在创建响应的 `secret_key` 字段**（`api_key` 是元数据对象，取它会得到空明文） |
| 旧 Key | 原 `openbase-gateway` 置 `is_active=false` 并写 `deleted_at`，避免双活 |
| OpenBase 侧 | `.env` 写入 `OPENBASE_LLM_API_KEY` 与 `OPENBASE_LLM_API_KEYS_BY_TENANT={"demo":"<同一 Key>"}`；`.env` 不入库，明文不落本文档 |

常见错误：直接建 Key 会报 `api_keys_organization_id_fkey` 违反——原实现把 `organization_id` 填成了用户 id，必须先有租户再把用户挂到该租户。

### 12.2 DPS 侧（DPS 认证）

DPS 连接固定 `search_path=platform`，身份经 `X-User-ID` / `X-Tenant-ID` / `X-Org-ID` / `X-User-Role` 入站，且**组织与租户必须已在库**，否则 403。需要三张表就位：

| 表 | 作用 | 缺失时表现 |
|---|---|---|
| `platform.user_roles` | 主体 → 角色绑定（决定 `resource:action` 权限） | 403（权限不通过） |
| `platform.organization` | 入站 `X-Org-ID` 归属校验 | 403 `组织不存在` |
| `platform.tenant` | 入站 `X-Tenant-ID` 归属校验（须属于该组织） | 403 `租户不存在或不属于该组织` |

#### 根因：备用库未复刻主用固定 UUID（本次实际故障点）

启动脚本会把 `.env.shared-infra` 中所有 `OPENBASE_*` 注入 OpenBase 进程，其中：

```
OPENBASE_DPS_CODE_MAP={"schema_version":1,...,"entries":[
  {"tenant_code":"tenant-1","dps_org_id":"10000000-0000-0000-0000-000000000001",
                            "dps_tenant_id":"20000000-0000-0000-0000-000000000001"},
  {"tenant_code":"tenant-2","dps_org_id":"10000000-0000-0000-0000-000000000002",
                            "dps_tenant_id":"20000000-0000-0000-0000-000000000002"}]}
```

登记式基线的优先级**高于** `.env` 里的 `OPENBASE_DPS_ORG_MAP` / `OPENBASE_DPS_TENANT_MAP`。因此未绑定租户的 `admin` 落兜底 `tenant-1` 时，出站头是主用的固定 UUID，而不是 `dps-org-001` / `dps-tenant-001` 这两个 code。备用库若自造 UUID，就会出现「code 能查到、UUID 查不到」→ 403 `组织不存在`。

**结论：备用库必须按主用同 UUID 复刻组织/租户，不得自造 UUID。**（与 `DPS/scripts/seed-shared-infra.py` 的固定 UUID 口径一致）

幂等补齐 SQL（对本地备用库 `nuct` 执行；已建行先归位再补建，避免 code 唯一约束冲突）：

```sql
BEGIN;
-- 现有 tenant-1 先迁到 org-1 名下，腾出旧 dps-org-001 的引用
UPDATE platform.tenant SET org_id = (SELECT id FROM platform.organization WHERE code='org-1')
WHERE code='tenant-1';
DELETE FROM platform.tenant WHERE code='dps-tenant-001';
DELETE FROM platform.organization WHERE code='dps-org-001';
-- 按主用固定 UUID 复刻
INSERT INTO platform.organization (id,name,code,status,created_at,updated_at)
VALUES ('10000000-0000-0000-0000-000000000001','DPS 联调组织','dps-org-001','active',now(),now());
INSERT INTO platform.tenant (id,org_id,name,code,status,created_at,updated_at)
VALUES ('20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',
        'DPS 联调租户','dps-tenant-001','active',now(),now());
COMMIT;
```

补充说明：
- 租户校验结果有 60s 负缓存（key `tenant:validate:{org}:{tenant}`）。补数后若仍 403，等 60s 再试，无需重启 DPS。
- `demo` 租户走查链路的出站值就是 `demo`（映射表未命中），因此库内 `platform.organization.code='demo'` / `platform.tenant.code='demo'` 需同时存在。

### 12.3 验证矩阵（2026-10-21 实测）

| 场景 | 请求 | 结果 |
|---|---|---|
| LLM 转发 | `GET /api/v1/llm-proxy/models` | 200 |
| DPS 读（标签） | `GET /api/v1/dps-proxy/tags/categories` | 200 |
| DPS 读（报表） | `GET /api/v1/dps-proxy/reports/overview` | 200 |
| DPS 读（画像） | `GET /api/v1/dps-proxy/portraits?page=1&page_size=5` | 200 |
| DPS 读（审计） | `GET /api/v1/dps-proxy/audit/logs?page=1&page_size=5` | 200 |
| 只读档写动作 | `POST /api/v2/tags/categories`（`X-User-Role=viewer`） | 403（readonly 档禁写，符合设计） |
| demo-admin（org_admin→readwrite） | `GET llm-proxy/models` / `GET dps-proxy/tags/categories` | 200 / 200 |
| demo-user（viewer→readonly） | `GET dps-proxy/tags/categories` / `POST dps-proxy/tags/categories` | 200 / 403 `PERM_FORBIDDEN` |

走查账号口令已重置为统一临时口令（仅本机备用库生效，口令不入库本文档，走查结束后请变更）。

### 12.4 遗留

| 项 | 说明 |
|---|---|
| `llm-proxy/models` 返回空数组 | 已在 v1.6.0 处置，见 §13（占位 provider + 3 条模型） |
| `tenant-2` 固定 UUID | `OPENBASE_DPS_CODE_MAP` 登记了 `tenant-2`，本地未建租户；若后续启用 tenant-2 需按同法补 `10000000-...-0002` / `20000000-...-0002` |

## 13. LLM 走查数据注入（v1.6.0）

### 13.1 目的与口径

`llm-proxy/models` 上游为 OpenLLM `/openllm/v1/models`，其实现（`app/api/chat.py::list_models`）读取：

- `public.llm_models` 中 `status='active'` 且 `is_public=true` 的记录；
- 每条记录经 `provider_id` 关联 `public.llm_providers`（列表里的 `owned_by` 取 provider_name）；
- 若租户/团队配置了 `allowed_models` 白名单则再过滤；未配置即全量返回。

因此"模型有数据"必须同时具备 **provider 行 + model 行**，只插 model 会因外键失败。

### 13.2 注入内容

| 对象 | 标识 | 说明 |
|---|---|---|
| provider | `provider_code=openai-compat-walkthrough` | `provider_type=openai`，`api_base_url=https://api.openai.com/v1`，`status=active`、`health_status=healthy`；**未配置密钥引用** |
| 模型 | `gpt-4o` | chat；capabilities `chat/vision/tools`；128K 上下文 |
| 模型 | `gpt-4o-mini` | chat；capabilities `chat/tools`；128K 上下文 |
| 模型 | `text-embedding-3-small` | embedding；8191 上下文 |

全部模型 `is_public=true`、`status=active`，`metadata.source=walkthrough-seed` 便于识别与清理。

幂等 SQL（本地备用库 `nuct`）：

```sql
BEGIN;
INSERT INTO public.llm_providers
  (id, provider_name, provider_code, provider_type, api_base_url, config, status, priority, health_status)
VALUES
  ('11111111-1111-1111-1111-111111111101','OpenAI 兼容（走查占位）','openai-compat-walkthrough','openai',
   'https://api.openai.com/v1','{"timeout":60}'::jsonb,'active',0,'healthy')
ON CONFLICT (provider_code) DO NOTHING;

INSERT INTO public.llm_models
  (id, provider_id, model_name, model_code, model_type, capabilities, context_window, max_tokens,
   supports_streaming, supports_vision, supports_tools, supports_json_mode,
   input_price_per_1k, output_price_per_1k, config, status, is_public, metadata)
VALUES
  ('22222222-2222-2222-2222-222222222201',
   (SELECT id FROM public.llm_providers WHERE provider_code='openai-compat-walkthrough'),
   'GPT-4o','gpt-4o','chat',ARRAY['chat','vision','tools'],128000,16384,
   true,true,true,true,0.005000,0.015000,'{}'::jsonb,'active',true,
   '{"source":"walkthrough-seed","note":"走查占位数据"}'::jsonb),
  ('22222222-2222-2222-2222-222222222202',
   (SELECT id FROM public.llm_providers WHERE provider_code='openai-compat-walkthrough'),
   'GPT-4o mini','gpt-4o-mini','chat',ARRAY['chat','tools'],128000,16384,
   true,false,true,true,0.000150,0.000600,'{}'::jsonb,'active',true,
   '{"source":"walkthrough-seed","note":"走查占位数据"}'::jsonb),
  ('22222222-2222-2222-2222-222222222203',
   (SELECT id FROM public.llm_providers WHERE provider_code='openai-compat-walkthrough'),
   'Text Embedding 3 Small','text-embedding-3-small','embedding',ARRAY['embedding'],8191,8191,
   false,false,false,false,0.000020,0.000000,'{}'::jsonb,'active',true,
   '{"source":"walkthrough-seed","note":"走查占位数据"}'::jsonb)
ON CONFLICT (id) DO NOTHING;
COMMIT;
```

### 13.3 验证结果（2026-10-21）

| 场景 | 请求 | 结果 |
|---|---|---|
| 模型列表（admin） | `GET /api/v1/llm-proxy/models` | 200，返回 3 条（gpt-4o / gpt-4o-mini / text-embedding-3-small） |
| 模型列表（demo-admin / demo-user） | 同上 | 200，同一集合（未配置 allowed_models 约束） |
| 模型详情 | `GET /api/v1/llm-proxy/models/gpt-4o` | 200 |
| 对话（非流式） | `POST /api/v1/llm-proxy/chat` | 见 §14（v1.7.0 接入 mock 上游后为 200） |

### 13.4 边界与回退

- **不具备真实推理能力**：provider 为占位登记，模型列表可走查；对话链路已在 v1.7.0 由本地 mock 承接（见 §14），mock 只回固定占位文本，不代表真实推理。需要真实模型时替换 `api_base_url` 并配置密钥引用。
- **清理（回退）**：
  ```sql
  DELETE FROM public.llm_models WHERE metadata->>'source' = 'walkthrough-seed';
  DELETE FROM public.llm_providers WHERE provider_code = 'openai-compat-walkthrough';
  ```
- 若 OpenLLM 侧对 provider 做健康巡检，`health_status` 可能被改为 `unhealthy`；列表查询不校验 provider 健康，故列表仍可见。

## 14. LLM 对话链路走查（本地 mock 上游，v1.7.0）

### 14.1 背景

v1.6.0 的占位 provider `api_base_url` 指向公网且无密钥引用，`llm-proxy/chat` 返回 500 `5001`。为覆盖对话类走查项，新增本机 OpenAI 兼容 mock 作为上游，**仅占位、不具推理能力**。

### 14.2 实现与端点

脚本：`OpenBase\doc\tmp\mock_openai_server.py`（Python 标准库 `ThreadingHTTPServer`，无第三方依赖，仅监听 `127.0.0.1:8025`）。

| 端点 | 行为 |
|---|---|
| `GET /health` | `{"status":"ok","service":"mock-openai"}`，供启动脚本健康轮询 |
| `GET /v1/models` | 返回 3 条与 §13 一致的模型项 |
| `POST /v1/chat/completions` | 非流式返回标准 `chat.completion`（含 usage）；`stream=true` 时按 SSE 分块返回并以 `data: [DONE]` 结束 |
| `POST /v1/embeddings` | 返回 8 维占位向量 |

回复内容为 `[mock] 已收到：<最后一条用户消息>。这是走查用占位回复，未调用真实模型。`

### 14.3 接入方式

1. `doc/tmp/start-all-services.ps1` 新增服务 `llm-mock`（端口 8025，健康检查 `/health`，WMI 脱离式启动，与其余服务同机制）：
   ```powershell
   @{ Name='llm-mock'; Port=8025; Cwd="$Root\OpenBase"; Cmd=$PgPy;
      Args=@("$Root\OpenBase\doc\tmp\mock_openai_server.py");
      Env=@{ MOCK_OPENAI_PORT='8025' }; Health=@('http://127.0.0.1:8025/health'); Wait=60 },
   ```
2. provider 指向 mock（OpenAIAdapter 以 `base_url` + `/chat/completions` 拼接，故 base 带 `/v1`）：
   ```sql
   UPDATE public.llm_providers
   SET api_base_url='http://127.0.0.1:8025/v1', updated_at=now()
   WHERE provider_code='openai-compat-walkthrough';
   ```
3. **无需重启 OpenLLM / OpenBase**：provider 配置在每次请求时按 `provider_id` 查库（`_call_llm_once`），改库即生效；只需启动新的 mock 进程。

### 14.4 验证结果（2026-10-21）

| 场景 | 请求 | 结果 |
|---|---|---|
| 非流式对话 | `POST /api/v1/llm-proxy/chat`（demo-admin，model=gpt-4o） | 200，`data.content` 为 mock 回复，`usage.total_tokens=238`，`routing_trace` 正常返回 |
| 流式对话 | `POST /api/v1/llm-proxy/chat/stream`（model=gpt-4o-mini） | 200，`text/event-stream`，18 个 `data:` 事件，末尾为 usage 汇总 |
| 模型列表 | `GET /api/v1/llm-proxy/models` | 200，3 条 |
| mock 健康 | `GET http://127.0.0.1:8025/health` | 200 |

### 14.5 边界与回退

- mock 只回固定文本，不做真实推理；对话内容、质量类走查项不能被 mock 结果代表。
- mock 未启动时对话恢复为 500 `5001`（链路其余环节不受影响）。
- 切回真实模型：改 `api_base_url` 为真实 OpenAI 兼容地址并配置 `api_key_ref`，随后可停用 mock：
  ```powershell
  Stop-Process -Id (Get-NetTCPConnection -LocalPort 8025 -State Listen).OwningProcess -Force
  ```
- mock 仅监听回环地址，不对外暴露。

## 15. 局域网 Ollama 与远程 DeepSeek 接入（v1.8.0）

### 15.1 数据来源

| 来源 | 地址 | 说明 |
|---|---|---|
| 局域网 Ollama | `http://192.168.0.4:11434` | OpenAI 兼容 `/v1`；实测 `/v1/models` 返回 4 个模型 |
| 远程 DeepSeek | `https://api.deepseek.com/v1` | 需要 API Key；本方案经本地反代注入 |

Ollama 实际模型（以 `/v1/models` 为准，`model_code` 必须与之一致）：

`qwen3.5:4b-q4_K_M`、`qwen3.5:2b-q4_K_M`、`llama3.2:1b`、`qwen2.5:0.5b`

### 15.2 注入内容

| provider | `api_base_url` | `config.timeout` | 模型 |
|---|---|---|---|
| `ollama-lan` | `http://192.168.0.4:11434/v1` | 300 | 上述 4 个 Ollama 模型（chat，`is_public=true`） |
| `deepseek` | `http://127.0.0.1:8026/v1` | 120 | `deepseek-chat`、`deepseek-reasoner` |

两家 provider 的 `api_key_ref` 均为 **NULL**（Ollama 不需要；DeepSeek 由反代注入）。种子 SQL 见 `doc/tmp/seed_llm_providers.sql`（幂等，provider 按 `provider_code` 收敛、model 按固定 id 收敛）。

注入后 `GET /api/v1/llm-proxy/models` 返回 **9 条**（3 条 mock 占位 + 4 条 Ollama + 2 条 DeepSeek）。

### 15.3 DeepSeek 本地反代（密钥不落库）

OpenLLM 实现中 `provider.api_key_ref` 被直接当作 Bearer 明文使用（代码注释亦标注"实际应存 Vault"）。为满足"密钥不落库/不落仓库"，改为本地反代：

- 服务：`doc/tmp/deepseek_proxy.py`（标准库，监听 `127.0.0.1:8026`），透传
  `/v1/chat/completions`（含 SSE）、`/v1/models`、`/v1/embeddings` 到 `https://api.deepseek.com`；
- Key 来源（按优先级）：
  1. 启动脚本所在进程的环境变量 `DEEPSEEK_API_KEY`；
  2. 密钥文件 `%USERPROFILE%\.openbase\deepseek_api_key.txt`（可用 `DEEPSEEK_API_KEY_FILE` 覆盖路径）；
- 未配置 Key 时：`GET /health` 返回 `key_configured=false`，业务端点返回
  `503 DEEPSEEK_API_KEY_NOT_CONFIGURED`（不静默透传 401）；
- 启动脚本已登记服务 `deepseek-proxy`（端口 8026）。

**当前状态（2026-10-21）**：已按方式二完成配置，密钥落于 `%USERPROFILE%\.openbase\deepseek_api_key.txt`，`GET /health` 返回 `key_configured=true`，真实调用已通过（见 §15.6）。密钥内容不写入本文件、不入库、不入仓库。

启用真实 DeepSeek 调用：

```powershell
# 方式一：用户级环境变量（新开终端生效）
setx DEEPSEEK_API_KEY "sk-..."
# 方式二：密钥文件（目录需已存在）
New-Item -ItemType Directory -Force "$env:USERPROFILE\.openbase" | Out-Null
Set-Content -Path "$env:USERPROFILE\.openbase\deepseek_api_key.txt" -Value "sk-..." -NoNewline
# 重新拉起反代
& 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -ExecutionPolicy Bypass `
  -File 'D:\Trae CN\myproject\Dev\OpenBase\doc\tmp\start-all-services.ps1' -Only deepseek-proxy
```

### 15.4 超时可配置（OpenLLM 源码改动）

局域网 Ollama 在 CPU 上推理时单次可达数分钟，原 `OpenAIAdapter` 硬编码 60s 读超时必然失败。

| 文件 | 改动 |
|---|---|
| `OpenLLM/backend/app/gateway/openai_adapter.py` | `httpx.Timeout` 改读 `provider_config["config"]["timeout"]`，缺省仍 60s |
| `OpenLLM/backend/app/api/openllm_gateway.py` | 同步/流式两处 `provider_config` 增传 `"config": provider.config or {}` |
| `OpenBase/.env` | `OPENBASE_LLM_UPSTREAM_TIMEOUT=300`、`OPENBASE_LLM_STREAM_TIMEOUT=300`（原默认 120s，会先于 OpenLLM 断开） |

重启 OpenLLM 后生效（本次实测启动耗时 317s）。

### 15.5 默认模型对齐

`OpenLLM/backend/.env`：`DEFAULT_LLM_MODEL` 由未注册的 `deepseek-v4-flash` 改为 `qwen2.5:0.5b`（局域网 Ollama 实测最快），未指定模型的请求不再报"模型不存在"。

### 15.6 验证结果（2026-10-21）

| 场景 | 结果 |
|---|---|
| `GET /api/v1/llm-proxy/models` | 200，9 条 |
| `POST /api/v1/llm-proxy/chat`（`qwen2.5:0.5b`） | **200**，5.5s，真实推理 |
| `POST /api/v1/llm-proxy/chat`（`qwen3.5:2b-q4_K_M`） | 502 `SYS_502`（300s 超时）；Ollama `/api/ps` 显示该模型 `size_vram=0`，纯 CPU 推理 |
| `POST /api/v1/llm-proxy/chat`（`deepseek-chat`） | **200**（Key 已配置，12.3s，64 tokens）；未配置 Key 时为 500 `5001` 快速失败 |
| 反代直连 `POST :8026/v1/chat/completions` | 503 `DEEPSEEK_API_KEY_NOT_CONFIGURED` |
| 反代 `GET :8026/health` | 200，`key_configured` 随 Key 配置变化 |
| `model=auto` 路由 | 200，选中 `qwen2.5:0.5b`（`routing_trace.model.reason=router`），87.8s（含路由判定与冷加载） |

为让 `auto`（cost 策略）优先选中可用模型，按推理成本给 4 个 Ollama 模型设置递增价格元数据
（0.5b 0.0001/0.0002 → 1b 0.0005/0.001 → 2b 0.001/0.002 → 4b 0.002/0.004，见 `doc/tmp/update_model_prices.sql`）；
该价格仅用于选路，本地 Ollama 无实际计费。

### 15.7 边界与注意事项

- **模型可用性取决于 Ollama 侧算力**：`qwen2.5:0.5b` 实测可用；`qwen3.5:2b/4b` 在 CPU 上推理，单次超过 300s，网关会 502。走查对话建议选 0.5b，或先在 Ollama 侧确认模型 `size_vram > 0`。
- 首次调用仍有冷加载开销（实测 2B 冷加载约 175s）；可用 `keep_alive` 预热，但模型被驱逐后会再次变慢。
- DeepSeek 未配置 Key 前只提供"模型可见/可选"，真实调用会快速失败。
- 反代仅监听回环地址，密钥既不入库也不入仓库；`api_key_ref` 保持 NULL 是刻意的安全约束。
- **`model` 字段不要省略**：`/api/v1/llm-proxy/chat` 只带 `messages` 不带 `model` 时，网关按组件路由契约要求 `query`，返回 400 `4003`；请显式传 `model`（如 `qwen2.5:0.5b`）或 `auto`。

## 16. 启动期自动探测与主备切换（P0 落地，2026-10-25）

### 16.1 需求与口径

- **要求**：每次启动服务前先检测**主用共享库**（PostgreSQL `192.168.0.151:5432`）状态；异常则切换到**备用库通道**（本机 `127.0.0.1:5432`）。
- **口径确认（2026-10-25）**：「备用库通道」= **本机 `127.0.0.1` 上的数据库**（本机 PostgreSQL，默认端口 5432），不含局域网其他主机。
- **单一决策点**：`scripts/service-orchestrator.ps1`（受管编排入口）；`start` / `startcheck` / `monitor` 启动前**必探测**。
- **不改配置**：`.env` / `.env.shared-infra` 永远保持主用地址；备用仅以**子进程环境变量**覆盖，主用恢复后重启自动回主用。
- **不半启动**：主备均不可达 ⇒ **拒绝启动任何服务**（退出码 2）。

### 16.2 参数与判定

| 参数 | 取值 | 说明 |
|---|---|---|
| `-DbMode` | `auto`（默认）/ `primary` / `standby` / `off` | auto=主用优先、异常切备用；primary/standby=强制；off=不探测（兼容旧行为） |
| `-DbProbeTimeoutSec` | 默认 `3` | 单端点探测超时（秒） |
| `-Json` | 开关，仅配 `-Action dbcheck` | 输出机器可读 JSON（schema v3，含 `data_plane` / `dependencies` / `evidence_path`），供脚本/流水线消费；stdout 不含人类摘要 |
| `-DbRecheckSec` | 默认 `0`（自动） | monitor 周期复检间隔；0 时取 `max(60, -Interval)`，仅供联调缩短 |
| `-Action dbcheck` | —— | **仅探测**：打印判定 + 脱敏目标 + 公共设施状态 + 证据路径，不启动/停止任何服务 |

判定顺序：`pg_isready`（首选，含服务端握手）→ 失败回落 **TCP 连通**；
主机端口来源：主用取 `POSTGRES_HOST`/`POSTGRES_PORT`（或从 `POSTGRES_URL` 解析），
备用默认 `127.0.0.1:5432`，可用 `OPENBASE_PG_STANDBY_HOST` / `OPENBASE_PG_STANDBY_PORT` 覆盖，
备用 DSN 可用 `OPENBASE_PG_STANDBY_URL` 整体覆盖（凭据与主用不同时）。

证据文件命名：`db-startup-probe-<yyyyMMdd-HHmmss>-<action>.json`（启动期判定，schema v2）、
`db-monitor-recheck-<yyyyMMdd-HHmmss>.json`（monitor 周期复检，schema v1）。

### 16.3 备用通道生效目标（仅替换主机端口，保留各仓 scheme/凭据/库名）

| 服务 | 生效方式 |
|---|---|
| openbase / dps | `POSTGRES_*` 覆盖 + （如声明）`OPENBASE_DB_URL` 替换 |
| openllm | 注入 `DATABASE_URL`（读其 `.env` 原值替换 `@host:port`） |
| openrag | 注入 `OPENRAG_DATABASE_URL`（同上，保留 `postgresql+asyncpg://`） |
| openmemory | 注入 `OPENMEMORY_DB__HOST` / `OPENMEMORY_DB__PORT` |

日志与证据中的 DSN **一律脱敏**（`://user:***@host:port/db`），不落明文口令。

### 16.4 实测矩阵（2026-10-25，本机）

| 场景 | 命令 | 判定 | 退出码 | 证据 |
|---|---|---|:--:|---|
| 主用可达 | `-Action dbcheck` | `mode=primary`（主用 `pg_isready` 1173ms） | 0 | `db-startup-probe-20261025-020157.json` |
| 强制备用 | `-Action dbcheck -DbMode standby` | `mode=standby`；5 个服务目标均指向 `127.0.0.1:5432`（口令脱敏） | 0 | `db-startup-probe-20261025-020449.json` |
| **主用异常自动切备用** | 预置 `POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=1` 模拟主用不可达 | `primary healthy=false` → **自动切 standby**，5 个服务目标指向 `127.0.0.1:5432` | 0 | `db-startup-probe-20261025-020926.json` |
| 强制备用目标不可达 | `-DbMode standby` + `OPENBASE_PG_STANDBY_PORT=1` | `mode=unavailable`；**未启动任何服务**（8000 无监听） | **2** | `db-startup-probe-20261025-020822.json` |

### 16.5 边界与后续阶段

| # | 事项 | 当前 | 后续 |
|:-:|---|---|---|
| 1 | 启动期 vs 运行期 | 启动期判定 + **monitor 周期复检**（P1 已交付）；复检只提示不回切 | **P2**：应用内启动自检（见 #3） |
| 2 | 纳管范围 | PostgreSQL 为**硬门禁**；Redis/Qdrant/Neo4j/MinIO 已纳管**数据面探测并在主用不通时切备用**（P0 已交付，见 §16.8；数据同步挂起） | 数据同步与回切（Phase 4） |
| 3 | 绕过编排直启 | 直接 `uvicorn` 不走探测（预期行为） | **P2**：应用内启动自检开关（`OPENBASE_DB_STARTUP_PROBE=warn|require|off`，默认 warn） |
| 4 | 数据一致性 | 备用库为主用**手工复刻**（UUID 必须一致，见 §12） | **P2**：评估逻辑复制/备份恢复，明确 RPO/RTO 与切回校验 |
| 5 | 写入语义 | 切备用后照常读写（备用可写） | **P2**：如需「主用只读、备用可写」双活语义，单独立项评审 |

### 16.6 故障排查

- 探测通过但服务连不上：确认被探测端口与目标服务 DSN 一致（`dbcheck` 输出会列出 5 个生效目标）。
- `.env` 含中文时行号错位：脚本已改为按 **UTF-8** 显式读取（PS 5.1 `Get-Content` 默认 ANSI 会导致解析偏差）。
- 停止后端口仍监听：以 `Get-NetTCPConnection -LocalPort <port> -State Listen` 复核并重试 `-Action stop`（见 S2 报告 D-04）。

### 16.7 周期复检与公共设施探测（P1 落地，2026-10-25）

#### 16.7.1 monitor 周期复检（只提示，不回切）

| 运行态 | 复检发现 | 行为 |
|---|---|---|
| 备用通道（standby） | 主用**已恢复** | `INFO` 提示「主用共享库已恢复…回切需在维护窗口重启编排」，落 `db-monitor-recheck-*.json` |
| 备用通道（standby） | 主用与备用**同时失联** | `ERROR` 提示立即恢复主用或本机备用，落证据 |
| 主用通道（primary） | 主用**失联** | `ERROR` 提示「连接池仍指向主用，建议重启编排进入备用通道」，落证据 |
| 主用通道（primary） | 主用正常 | 静默（不写日志、不落证据） |

约束：**不自动回切、不重启任何服务**（运行中连接池指向已解析端点，热切换会导致连接漂移）；
同一提示文本仅记录一次（状态变化才再次落证据），避免每分钟刷盘。

#### 16.7.2 公共设施探测（仅提示，不阻断）

- 探测对象：`redis`（`REDIS_HOST`/`REDIS_PORT`，默认 6380）、`qdrant`（`QDRANT_*`，6333）、
  `neo4j`（`NEO4J_HOST`/`NEO4J_BOLT_PORT`，7687）、`minio`（`MINIO_*`，9000）；取值来源为
  进程环境（`.env.shared-infra` 已注入）。
- 判定：TCP 连通（超时同 `-DbProbeTimeoutSec`）。
- 策略：**不参与启动门禁**——PG 是唯一硬门禁；四类设施不可达时 `WARN` 并提示
  `D:\infra\start-infra.ps1`，避免「主库可用但 Qdrant 抖动」导致整体拒启。
- 结果纳入证据 `dependencies` 字段（`dbcheck -Json` 可直接消费）。
- **v1.11.0 起行为变更**：主用数据面不通且备用可用时**自动切备用**（覆盖各仓环境键），
  数据同步仍挂起 → 见 §16.8；本节「仅提示不阻断」仅描述**不阻断启动**这一层语义。

#### 16.7.3 实测（2026-10-25，本机）

| 场景 | 命令 | 结果 | 证据 |
|---|---|---|---|
| 主用可达 + 四设施全绿 | `-Action dbcheck` | `mode=primary`；redis/qdrant/neo4j/minio 均 `ok`（2~55ms） | `db-startup-probe-20261025-024459-dbcheck.json` |
| JSON 消费 | `-Action dbcheck -Json` | stdout 为纯 JSON（schema v2），`dependencies` 四键齐全，`evidence_path` 指向证据 | `db-startup-probe-20261025-024508-dbcheck.json` |
| **备用通道下主用恢复** | `-Action monitor -DbMode standby -Only __none__ -DbRecheckSec 1` | 复检 `current=standby / desired=primary`，提示「主用共享库已恢复」，**未启动任何服务** | `db-monitor-recheck-20261025-024559.json`、`db-startup-probe-20261025-024558-monitor.json` |

守门用例：`tests/test_orchestrator_db_failover.py` 共 **20 例**（静态契约 12 + 行为契约 8），
其中 `test_monitor_recheck_notices_primary_recovery` / `test_primary_infrastructure_outage_switches_to_standby`
在对应备用实例不可达时显式 `skip`（不伪造通过）。

### 16.8 数据面探针与四设施切换（P0，2026-10-25 用户决策）

#### 16.8.1 判定升级：从「端口通」到「真的能用」

| 设施 | 数据面判据 | 说明 |
|---|---|---|
| PostgreSQL | `psql -c "select 1" -c "show server_version"` | 覆盖 TCP + 认证 + 库存在 + 可执行查询；口令经 `PGPASSWORD` 传递，不上命令行 |
| Redis | `AUTH`（可选）→ `PING` → `DBSIZE` → `INFO replication` | 能读 keyspace；记录 `role` / `master_link_status` |
| Qdrant | `GET /collections` | 能读集合元数据；返回集合数 |
| Neo4j | `POST /db/<db>/tx/commit` 执行 `RETURN 1 AS ok` | 覆盖认证 + 库可用 + 可执行查询 |
| MinIO | `GET /minio/health/ready` | 服务端就绪（含磁盘/集群状态）；桶与对象列表需 `mc` |

实现：`scripts/infra_probe.py`（**stdlib-only**，不引入 redis/qdrant/psycopg/minio 依赖）；
编排侧只组装 spec（**spec 不含明文口令，只写环境变量名**）→ 执行 → 读回 JSON。

| 参数 | 取值 | 说明 |
|---|---|---|
| `-ProbeLevel` | `auto`（默认）/ `data` / `tcp` | auto=优先数据面、探针不可用回落 TCP；data=仅数据面（失败即判不可用）；tcp=仅端口/`pg_isready` |
| 证据 `probe_mode` | `data-plane` / `partial` / `tcp` | `partial` 表示部分目标回落；回落原因写入 `data_plane.degraded` |

#### 16.8.2 切换规则（主用不通即切备用）

| 对象 | 规则 | 阻断启动 |
|---|---|:---:|
| PostgreSQL | 主用数据面不通且备用数据面可用 ⇒ `mode=standby`（5 个服务按各自 DSN 换主机端口） | 是（双不可达 exit 2） |
| Redis / Qdrant / Neo4j / MinIO | 主用数据面不通且备用数据面可用 ⇒ **该设施切本机备用**并覆盖以下键 | 否（仅 WARN） |
| 任意设施 | 主用不通且备用也不通 ⇒ 保持 `DOWN`，提示 `D:\infra\start-infra.ps1` | 否（PG 除外） |

覆盖键（仅替换主机/端口/URL，保留 scheme、凭据、库名；**不改写任何 `.env`**）：

| 设施 | 覆盖键 |
|---|---|
| Redis | `REDIS_HOST/PORT/URL`、`OPENBASE_REDIS_URL`、`OPENMEMORY_CACHE__HOST/PORT`、`OPENRAG_REDIS_URL`（仅 `OPENRAG_REDIS_ENABLED=true`） |
| Qdrant | `QDRANT_HOST/PORT/GRPC_PORT/URL`、`OPENRAG_QDRANT_URL`、`OPENRAG_QDRANT_GRPC_URL`、`OPENMEMORY_VECTOR__HOST/PORT` |
| Neo4j | `NEO4J_HOST/BOLT_PORT/URI`、`OPENMEMORY_GRAPH__URI` |
| MinIO | `MINIO_HOST/PORT/ENDPOINT`（当前无服务消费方，先覆盖备后用） |

备用端点：`127.0.0.1` + 各规范端口（Redis 6380 / Qdrant 6333+6334 / Neo4j 7474+7687 / MinIO 9000），
可用 `OPENBASE_INFRA_STANDBY_HOST`、`OPENBASE_REDIS_STANDBY_PORT`、`OPENBASE_QDRANT_STANDBY_PORT(_GRPC)`、
`OPENBASE_NEO4J_STANDBY_HTTP_PORT`、`OPENBASE_NEO4J_STANDBY_BOLT_PORT`、`OPENBASE_MINIO_STANDBY_PORT` 覆盖。

#### 16.8.3 数据面同步：**暂时挂起（用户决策 2026-10-25）**

- 本阶段只做「探测 + 切换 + 留痕」，**不做数据同步**；
- 切到备用后备用数据可能为空或落后，因此切换必然输出
  `WARN 公共设施已切备用：…（数据面同步问题暂时挂起——备用数据可能为空或落后，请人工核对）`；
- 各设施的主备版本基线（2026-10-25 实测）：PG 14.23（Alpine）→ 17.10（Windows）、
  Redis 7.4.9 → 8.10.2、Qdrant 1.7.4 → 1.7.4、Neo4j 5.17.0（community）→ 5.26.16、MinIO 主用版本待取；
- 同步方案与 RPO/RTO 见全栈计划 §7.0 Phase 4（待评审），本文件不承诺数据一致性。

#### 16.8.4 实测（2026-10-25，本机）

| 场景 | 命令 | 结果 | 证据 |
|---|---|---|---|
| 主用全绿（数据面） | `-Action dbcheck` | `mode=primary`；五项目标均 `data-plane`（PG 2.2s / 四设施 2~350ms） | `db-startup-probe-20261025-125145-dbcheck.json` |
| **主用 PG 不通 ⇒ 切备用库** | 预置 `POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=1` | `mode=standby`；5 服务目标指向 `127.0.0.1:5432` | 本轮实测（JSON 断言 `resolved_mode=standby`） |
| **主用 MinIO 不通 ⇒ 四设施切换** | 预置 `MINIO_HOST=127.0.0.1 MINIO_PORT=1` | `minio` 切至 `127.0.0.1:9000`，覆盖 `MINIO_HOST/MINIO_PORT/MINIO_ENDPOINT`，`switched=[minio]` | 同上（`data_plane.switched`） |
| 主用与备用均不可达 | `-DbMode standby` + `OPENBASE_PG_STANDBY_PORT=1` | `mode=unavailable`，**exit 2** | `db-startup-probe-20261025-134928-dbcheck.json` |
| 主用 Redis 不通且备用未起 | 预置 `REDIS_HOST=127.0.0.1 REDIS_PORT=1` | `redis DOWN`，不切换，提示 `start-infra.ps1` | `db-startup-probe-20261025-134936-dbcheck.json` |
| 仅端口判定（兼容） | `-Action dbcheck -ProbeLevel tcp` | 回落 `pg_isready`/TCP，`probe_mode=tcp` | `db-startup-probe-20261025-135208-dbcheck.json` |

#### 16.8.5 已知边界

| # | 事项 | 现状 | 后续 |
|:-:|---|---|---|
| 1 | 数据同步 | **挂起**：切备用后数据可能为空/落后 | Phase 4：按设施选型（PG dump/restore 或逻辑复制、Redis REPLICAOF、Qdrant snapshot、MinIO mirror、Neo4j dump/load） |
| 2 | 回切 | 需重启编排；切换期间写入备用的数据不合并回主用 | Phase 4 与数据同步一并定义 |
| 3 | Chroma | 未纳管（主用 8001 / 备用 8005） | 端口差异需单独处理 |
| 4 | 探测开销 | PG 每次启动多约 2s（psql 子进程）；`dbcheck` 全量约 8s | 可复用常驻探针或连接池化，暂不优化 |
| 5 | `status` 耗时 | `Get-NetTCPConnection` 单次约 2.7s（既有实现，非本轮引入） | 后续可改用 `IPGlobalProperties` 批量读取 |

### 16.9 每次启动前的数据库校验（P0，2026-10-25 用户决策）

#### 16.9.1 触发范围

| 入口 | 是否校验 | 说明 |
|---|:---:|---|
| `-Action start`（全量） | ✅ | 全局门禁 + **每个服务**启动前各校验一次 |
| `-Action start -Only <svc>`（单服务） | ✅ | 与全量走同一 `Start-Service` 入口 |
| `-Action startcheck` | ✅ | 启动段同 `start` |
| `-Action monitor`（自愈重启） | ✅ | 每次真正拉起服务前都校验（结果按 TTL 复用） |
| `-Action dbcheck` / `status` / `stop` | —— | 只探测/只读，不启动服务 |

#### 16.9.2 按服务依赖校验

| 服务 | 校验的设施 |
|---|---|
| openbase | PostgreSQL、Redis |
| openllm | PostgreSQL、Redis |
| openrag | PostgreSQL、Qdrant |
| openmemory | PostgreSQL、Redis、Qdrant、Neo4j |
| dps | PostgreSQL |
| frontend | 无（经 OpenBase 转发，不直连数据库） |

#### 16.9.3 判定与处置

1. **当前通道的共享库**（primary 或已切的 standby）数据面不可用 ⇒ **拒绝启动该服务**（`ERROR`，返回 false，不影响其它服务）；
2. 其它设施数据面不可用 ⇒ `WARN` 但不阻断（与「PG 是唯一硬门禁」一致）；
3. 所有校验结果写编排日志：`<svc> 启动前数据面校验：pg=ok(primary,data-plane) / redis=ok`；
4. **TTL 复用**：`-ProbeTtlSec`（默认 60s）内复用上次探测结果，过期则按该服务依赖按需重探（分批探测结果**合并**，不会冲掉其它设施）。

#### 16.9.4 实测（2026-10-25）

- 命令：`-Action start -Only openbase`
- 日志：`2026-10-25 14:38:04 [INFO] openbase 启动前数据面校验：pg=ok(primary,data-plane) / redis=ok`
- 说明：该校验发生在**依赖健康检查与进程拉起之前**；本次拉起阶段因宿主缺少裸 `python`
  （既有问题 **D-05**，见全栈计划 B4）失败，与数据库校验无关。

#### 16.9.5 边界

- `frontend` 不直连数据库，不做校验（其可用性取决于 OpenBase）；
- 绕过编排直接 `uvicorn` 仍不触发（Phase 4 的应用内自检）；
- 备用设施未启动时，该校验只会 `WARN` 对应设施，不会阻断服务启动。

### 16.10 解释器解析与运行环境自检（D-05 解除，2026-10-25）

#### 16.10.1 背景

编排的 6 个 Python 服务原先统一使用 `Command = 'python'`，依赖 PATH 解析；本机从未安装系统级
Python，唯一解释器是 pgAdmin 内嵌 3.13（不注册 PATH），因此 `Start-Process` 直接报
`The system cannot find the file specified`（D-05）。

#### 16.10.2 处置

| 项 | 内容 |
|---|---|
| 系统 Python | `D:\Python\python.exe` → **3.12.10**（完整安装） |
| 专用 venv | `D:\venvs\openbase\Scripts\python.exe`，由 `python -m venv` + `pip install -e .` 生成（含 fastapi/uvicorn/pydantic/sqlalchemy 等全部运行期依赖） |
| 解析顺序 | `OPENBASE_<SVC>_PYTHON` → `-PythonHome`（exe/目录）→ `OPENBASE_PYTHON` → 各仓默认 venv（openbase=`D:\venvs\openbase`、openrag=`.venv3`）→ 系统 Python → pgAdmin 3.13 桥接（自动注入 `OPENBASE_PY_DEPS`/`OPENBASE_PY_ROOT`）→ PATH 上的 python |
| 自检 | 每个候选执行 `python -c "import uvicorn"`，**全部失败**时输出 `启动前运行环境校验失败：未找到可用 Python…` 并拒绝该服务启动 |
| 生效范围 | 全量启动 / `-Only` 单服务 / monitor 自愈重启（统一 `Start-Service`） |

**ABI 说明（关键）**：既有 `.venv` 内的 `_pydantic_core.cp313-win_amd64.pyd` 是 **cp313** 产物，
系统 3.12 即使加 `PYTHONPATH=.venv` 也会在 `import pydantic` 处失败（已实测）。
因此必须**用系统 Python 新建 venv**，不能复用 3.13 的 `.venv`；3.13 桥接仅作为最后兜底。

#### 16.10.3 实测（2026-10-25）

| 场景 | 命令 | 结果 |
|---|---|---|
| 依赖导入自检 | `D:\venvs\openbase\Scripts\python.exe -c "import uvicorn, fastapi, pydantic"` | 通过（Python 3.12.10 / uvicorn 0.54.0 / pydantic 2.14.1） |
| **单服务启动** | `-Action start -Only openbase` | `解释器：D:\venvs\openbase\Scripts\python.exe` → 进程 PID 9100 → **健康检查 3s 通过**（8000） |
| 停止与端口核对 | `-Action stop` | 停止完成；8000 **已释放** |
| 反例（预期失败） | 系统 3.12 + `PYTHONPATH=.venv` | `import pydantic` 失败（cp313 ABI 不兼容），故不作为候选 |

#### 16.10.4 边界

- OpenLLM / OpenMemory 的专用 venv 已在 v1.14.0 补齐（见 §16.11）；`D:\uv` 仍为空目录（uv 未安装），
  uv 管理属后续固化项；
- 解释器解析结果在**同一编排进程内缓存**，进程重启后重新自检；
- 该自检只验证 `import uvicorn`，不校验业务依赖完整性；业务级失败仍以服务健康检查为准。

### 16.11 三仓专用 venv 与上游依赖缺口（2026-10-25）

#### 16.11.1 已建立的解释器环境

| 服务 | 解释器 | 依据 | 验证 |
|---|---|---|---|
| openbase | `D:\venvs\openbase\Scripts\python.exe`（3.12.10） | `pip install -e .`（pyproject 全依赖） | `import uvicorn, fastapi, pydantic, openbase.demo_app` 通过；启动健康 3s |
| openllm | `D:\venvs\openllm\Scripts\python.exe`（3.12.10） | `requirements.txt`（过滤非法行后） | `import main` 通过；**启动后 `/health` 200** |
| openmemory | `D:\venvs\openmemory\Scripts\python.exe`（3.12.10） | `pip install -e .`（pyproject，含 torch 2.14 / sentence-transformers 3.4） | `import uvicorn, openmemory` 通过 |
| openrag | `D:\Trae CN\myproject\Dev\OpenRAG\.venv3\python.exe`（3.11.9） | 各仓既有环境 | 既有基线 |

候选链已按上表补入（`Get-PythonCandidates`），顺序仍为：服务级 env → `-PythonHome` → 全局 env → 各仓 venv → 系统 Python → 3.13 桥接 → PATH。

#### 16.11.2 OpenLLM 上游 requirements 缺口（本次逐项踩到）

| # | 现象 | 处置（本机，不改上游仓库） |
|:-:|---|---|
| 1 | `python_requires>=3.10` 是非法依赖行 → `ResolutionImpossible` | 本地生成**临时过滤副本**（剔除该行，未入库）后安装 |
| 2 | `httpx==0.26.0` 与 `mcp>=1.0`（要求 httpx≥0.27）冲突 | 放宽为 `httpx>=0.27,<1.0` |
| 3 | 同上导致 pydantic 版本过旧 | 放宽为 `pydantic>=2.7,<3`、`pydantic-settings>=2.2,<3` |
| 4 | 代码导入 `jwt` 但 requirements 只有 `python-jose` | 追加 `pyjwt` |
| 5 | `DATABASE_URL` 用 `postgresql+psycopg://`，但只装了 `psycopg2-binary` | 追加 `psycopg[binary]>=3.1` |
| 6 | `vector_store.py` 需要 `numpy` / `qdrant-client`，requirements 未列 | 追加 `numpy`、`qdrant-client==1.7.3` |
| 7 | `app/core/otel.py` 需要 OTLP **gRPC** 导出器 | 追加 `opentelemetry-exporter-otlp-proto-grpc` |
| 8 | 未锁 `bcrypt`，pip 装了 5.0.0（与 passlib 1.7.4 不兼容） | 锁 `bcrypt>=4,<5`（实际 4.3.0） |

> 建议由 OpenLLM 仓在下个版本修正 requirements（上述 8 项均有明确改法），本仓仅做本机环境落地。

#### 16.11.3 OpenMemory 版本约束冲突

- `openmemory 7.3.2` 声明 `qdrant-client>=1.9.0`；
- 但共享 Qdrant 服务端是 **1.7.4**，新客户端（1.19/1.20）无法解析其响应（既有实测结论）；
- 本机选择 **`qdrant-client==1.7.3`**（pip 会给出 constraint 警告，运行期以服务端兼容性优先）。

#### 16.11.4 实测（2026-10-25）

| 场景 | 结果 |
|---|---|
| `-Action start -Only openllm` | 解释器 `D:\venvs\openllm\Scripts\python.exe` → 进程创建 → **`/health` 返回 200** |
| 冷启动耗时 | **>60s**（首次导入 torch/transformers 等），编排记录 `健康检查超时（已等待 62s/60s）` 但进程实际健康 |
| `-Action stop` | openllm 正常停止；8000 / 8001 均 `RELEASED` |
| OpenMemory | 依赖导入通过；未做完整启动（需 Qdrant/Redis 备用与模型预热） |

#### 16.11.5 新增观察项（待处理）

| # | 事项 | 现状 | 建议 |
|:-:|---|---|---|
| 1 | OpenLLM 冷启动 >60s | 首次启动触发健康等待告警（服务实际可用） | 为 openllm 增加服务级 `HealthWait`（如 180s），与 openmemory 一致 |
| 2 | `D:\uv` 目录为空 | 未安装 uv 可执行 | 若要 uv 管理，先安装 `uv.exe`，再以 `uv venv` 重建三仓环境 |
| 3 | requirements 上游缺陷 | 见 §16.11.2 八项 | 由 OpenLLM 仓修正后再回归 |

### 16.12 全栈 7 服务启动实测（2026-10-25，人工走查前置）

#### 16.12.1 启动结果

| 服务 | 端口 | 解释器/运行时 | 冷启动 | 结果 |
|---|---:|:---:|---:|---|
| openllm | 8001 | `D:\venvs\openllm\Scripts\python.exe` | 91s | ✅ |
| openrag | 8010 | `D:\Trae CN\myproject\Dev\OpenRAG\.venv3\python.exe` | >62s | ✅（`/api/v1/system/health` 200） |
| openmemory | 8020 | `D:\venvs\openmemory\Scripts\python.exe` | 113s | ✅ |
| oidc-idp | 8090 | pgAdmin 3.13 + `.venv` 桥接 | 41s | ✅ |
| dps | 8030 | OpenRAG `.venv3`（依赖经 `cross-libs.pth`） | 34s | ✅ |
| openbase | 8000 | `D:\venvs\openbase\Scripts\python.exe` | 60s | ✅ |
| frontend | 5173 | `node + node_modules\vite\bin\vite.js` | 65s | ✅ |

全量检查（`-Action checkall`）：**27 PASS / 0 FAIL / 0 SKIP**，证据
`doc/test/evidence/ops/checkall-20261025-2253.txt`。

#### 16.12.2 本轮修复的三个启动缺陷

| # | 现象 | 根因 | 修复 |
|:-:|---|---|---|
| 1 | oidc-idp 报「未找到可用 Python」 | 候选自检 `import uvicorn` 在 pgAdmin 桥接上执行时**未注入门控环境**，必然失败（选择后才注入，鸡生蛋） | `Test-PythonRuntime` 对 `*pgAdmin*` 先设 `OPENBASE_PY_DEPS/ROOT` 再自检 |
| 2 | frontend `npm.cmd run dev` 静默退出（exit 1，无错误输出） | npm 11 + WMI/Start-Process 组合下 `npm.cmd` 无法正常拉起子进程 | 改为直调 `node node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5173` |
| 3 | openllm/openrag/frontend 健康等待超时（服务实际可用） | 全局 `HealthTimeout=60s` 短于真实冷启动 | 服务级 `HealthWait`：openllm 180 / openrag 180 / frontend 120（openmemory 300 既有） |

#### 16.12.3 人工走查入口

| 目标 | 地址 |
|---|---|
| 统一前端 | `http://127.0.0.1:5173/`（登录 `admin / admin123`，走查环境默认账号） |
| OpenBase API 文档 | `http://127.0.0.1:8000/docs` |
| OpenLLM 健康/状态 | `http://127.0.0.1:8001/health`、`/api/v1/status` |
| OpenRAG 健康 | `http://127.0.0.1:8010/api/v1/system/health` |
| OpenMemory 健康 | `http://127.0.0.1:8020/health` |
| DPS 存活 | `http://127.0.0.1:8030/health/liveness` |
| 本地 OIDC IdP | `http://127.0.0.1:8090/.well-known/openid-configuration` |

停止：`.\scripts\service-orchestrator.ps1 -Action stop`（停止后以 `Get-NetTCPConnection` 核对端口，见 D-04）。

### 16.13 前端全页面走查（77 页）驱动的三项修复（2026-10-26）

走查口径与逐页结果见 `doc/test/OpenBase-前端全页面走查清单-v1.0.0.md`；终轮证据
`doc/test/evidence/s6/ui-walkthrough-20261026-r4.json`（**PASS 77 / FAIL 0，api 失败 0 次**）。

#### 16.13.1 修复项

| # | 现象 | 根因 | 修复 | 验证 |
|:-:|---|---|---|---|
| 1 | 告警中心 / 工具调用 / Prompt 实验 **401**（`无效的API密钥`） | 2026-10-21 轮换把 `.env` 的 `OPENBASE_LLM_API_KEY` 换成 OpenLLM 库内**不存在**的 Key；租户映射键误写为 `demo`（真实 claim 为 `tenant-1`） | 恢复 `sk-openllm-b16f68…`（SHA-256 与库内 `openbase-gateway-v143` 一致，`is_active=t`、`permissions=["*"]`）；租户映射改回 `tenant-1` | `alerts` / `alerts/rules` / `tool-calls` / `prompt-experiments` / `providers` 全部 **200** |
| 2 | 服务健康检查通过后数秒消失（前端全站 502/503） | 编排器仅 `frontend` 声明 `Detach`，其余走 `Start-Process`，随启动会话被 Job Object 回收 | 全部 7 个服务统一 `Detach = $true`（WMI 脱离会话） | `-Action start -Only openbase` 后进程存活，端口保持监听 |
| 3 | 脱离启动后**所有库依赖接口 500**（`/auth/me`、`/users`、`/tenants`） | WMI `Win32_Process.Create` 子进程**不继承**调用方进程环境 → `.env.shared-infra` 注入的 `POSTGRES_URL` 丢失 → `demo_app` 回退内存模式 | `Start-DetachedProcess` 白名单传递环境（系统必需键 + `POSTGRES_/REDIS_/QDRANT_/NEO4J_/MINIO_/SQLITE_/OLLAMA_` + 各仓前缀），再以 `$Svc.Env` 覆盖；不整份快照（命令行超限时 WMI 返回 8） | `/auth/me`、`/users`、`/proxy/openllm/*` 全部 **200** |
| 4 | （D-04 残留）`stop` 只杀包装进程，python 孤儿仍占用端口 | `start` 落盘的是包装 powershell PID | 健康检查通过后按端口反查真实监听 PID 并落盘（`Get-PortPid` + `Save-Pid`） | 落盘 PID 与端口占用进程一致；`stop` 后端口释放 |

#### 16.13.2 守门用例

`tests/test_orchestrator_db_failover.py` 新增
`test_all_services_detach_and_record_listening_pid`：断言 7 个服务均声明 `Detach`、健康检查后按端口反查 PID、
环境快照语句存在。全文件 **24 例全部通过**。

#### 16.13.3 教训（写入工程约定）

1. **静默 `except ImportError: continue` 会让整片路由消失**，只在前端表现为 404 —— 装配期必须留痕（DEF-WT-01）。
2. **密钥轮换必须同步校验目标系统登记状态**（SHA-256 比对），并保留上一版备份文件以便回滚（DEF-WT-02）。
3. **WMI 脱离启动 = 环境隔离**：任何依赖进程环境注入的配置都必须在启动脚本内显式传递（DEF-WT-03）。
4. 走查前必须**先刷新登录态**（`expires_in=7200`），过期 token 会被误判为「全页失败」。







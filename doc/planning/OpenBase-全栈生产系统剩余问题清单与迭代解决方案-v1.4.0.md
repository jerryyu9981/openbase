# OpenBase-全栈生产系统剩余问题清单与迭代解决方案-v1.4.0

| 项目 | 内容 |
|------|------|
| 文档名称 | 全栈生产系统剩余问题清单与迭代解决方案（OpenBase 主仓 + 四仓 + 运维面） |
| 文档编号 | OB-PLAN-REMAIN-FULLSTACK-v1.4.0 |
| 版本 | **v1.4.0** |
| 状态 | **[Review]**（待人工批准后排期执行） |
| 编制日期 | 2026-10-25 |
| 编制人 | FA-OpenBase-Dev（AI 辅助） |
| 代码基线 | `366a200`（产品版本 **1.4.12**） |
| 上游依据 | 《OpenBase-剩余事项统一清查与小版本迭代计划-v1.0.0》v1.20.0；《OpenBase-长尾迭代收口审计-v1.12.0》v1.3.0；《OpenBase-S2-三级回滚演练报告-v1.1.0》；《OpenBase-主备双通道生产上线必办事项清单-v2.2.0》；《OpenBase-生产环境配置下发单-XR-OPS-07-v1.0.0》（XR-OPS-07-ENV-001）；《OpenBase-主备双通道生产上线回滚方案-v1.0.0》 |
| 口径 | 仅登记**尚未闭环**项；已闭环项不重复排期（见各上游文档「已闭环基线」） |

## 修订历史

| 版本 | 日期 | 编制人 | 修订内容 |
|------|------|--------|---------|
| v1.4.0 | 2026-10-25 | FA-OpenBase-Dev（AI 辅助） | **每次启动服务前校验数据库**：`Start-Service` 统一入口新增 `Assert-ServiceDataPlane`（全量 / `-Only` 单服务 / monitor 自愈一致）；按服务依赖校验 pg/redis/qdrant/neo4j；当前通道共享库不可用 ⇒ 拒绝该服务；`-ProbeTtlSec` 内复用探测；守门 20 → **21 例**（运维记录 v1.12.0 §16.9） |
| v1.3.0 | 2026-10-25 | FA-OpenBase-Dev（AI 辅助） | **A8 Phase 3（P0 子集）已交付**：判定升级为数据面探针（`scripts/infra_probe.py`，stdlib）；**主用不通即切备用**（PG 硬门禁 + Redis/Qdrant/Neo4j/MinIO 覆盖）；数据面同步**暂时挂起**并强制告警；证据 schema v3；守门用例 15 → **20 例**。原 Phase 3 拆分为 Phase 3（已交付）与 **Phase 4（数据同步/回切，挂起）** |
| v1.2.0 | 2026-10-25 | FA-OpenBase-Dev（AI 辅助） | **A8 Phase 2（P1）已交付**：monitor 周期复检（≥60s，主用恢复/失联只提示不回切）+ Redis/Qdrant/Neo4j/MinIO 纳管探测（仅提示不阻断）+ `dbcheck -Json`（schema v2）；守门用例 9 → **15 例**；§7.0 状态与附录来源同步（运维记录 v1.10.0 §16.7） |
| v1.1.0 | 2026-10-25 | FA-OpenBase-Dev（AI 辅助） | 新增 **A8 共享库主备启动探测**（P0 Phase 1 已交付：受管入口启动前探测主用 PostgreSQL，异常自动切本机 `127.0.0.1:5432`，双不可达拒绝启动；单测 9 例）；补齐 §7.0 三阶段优先迭代（运行期复检/多组件纳管/HA 与切回），汇总项由 17 增至 **18** |
| v1.0.0 | 2026-10-25 | FA-OpenBase-Dev（AI 辅助） | 首次产出：统一汇总本仓/跨仓/运维面剩余 17 项（阻断 7 / 工程 4 / 跨仓能力 2 / 冻结 4），给出 v1.13.0 / v1.13.1 / v1.14.0 三个小版本迭代方案、依赖关键路径、验收门禁与回滚策略 |

---

## 1. 汇总口径

- **优先级**：P0 = 生产阻断（Go/No-Go）；P1 = 上线后一周内必须收敛；P2 = 计划内迭代；P3 = 可延后。
- **责任方**：`OPS` = 生产部署面；`OB` = OpenBase 本仓；`LL/RG/OM/DPS` = 对应仓；`研发` = 本仓研发。
- **状态**：`未启动` / `进行中` / `待窗口` / `冻结`。
- **阶段命名**：`S0~S4` 为演进阶段（Stage）；`P0~P3` 仅表示需求优先级；`Phase x.y` 为单版本内迭代阶段。

## 2. 总览

| 类别 | 数量 | 其中 P0 | 说明 |
|------|:----:|:------:|------|
| A 生产阻断（Go/No-Go） | 8 | 7 | A1~A7 依赖生产部署面或共享 PG；**A8 已交付 Phase 1/2/3**（数据同步 Phase 4 挂起） |
| B 本仓工程项 | 4 | 1 | 1 项代码修复（D-04）、1 项联调窗口、1 项环境固化；**B3 推送已闭环** |
| C 跨仓能力/契约 | 2 | 0 | 均需目标侧主数据或跨仓契约评审 |
| D 冻结/不建设 | 4 | 0 | 已书面裁定，仅登记解冻条件 |
| **合计** | **18** | **8** | —— |

## 3. A 类：生产阻断（Go/No-Go）

| ID | 事项 | 责任方 | 现状 | 验收判据 | 依据 |
|:--:|------|:------:|------|---------|------|
| A1 | **G1 三 REAL 开关生产下发**：`OPENLLM_OPENRAG_REAL` / `OPENLLM_OPENMEMORY_REAL` / `OPENLLM_DPS_REAL` + `OPENMEMORY_ENABLED` / `DPS_ENABLED` 置 `true` | OPS（LL 陪同） | 🟡 联调窗口已验证（production 下三组件 `ok`）；**生产主机 `.env` 未下发** | 运行态确认真实契约端点被调用（非 stub）；`/health` 三组件 `ok`；`.env` 备份留档 | 清单 v2.2.0 G1 |
| A2 | **G2 生产门禁 5 组置真**：`ENFORCE_INBOUND_IDENTITY_HEADERS` / `RBAC_PERMISSION_ENFORCE` / `TENANT_SCOPE_ENFORCE` / `TENANT_HEADER_CONSISTENCY_ENFORCE` / `QUOTA_MISSING_FAIL_CLOSED` | OPS | 🟡 窗口已验证（6 个反例全部拒绝）；**生产 `.env` 未下发** | `ENV=production` 正常启动；启动日志无门禁告警；任一回落实例化即拒绝启动 | 清单 v2.2.0 G2 |
| A3 | **XR-OPS-07 生产开关下发**：`OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=true` | OPS | 🟡 下发单就绪；本地 `--env-file` 演练 PASS、开发 `.env` FAIL（缺口证据） | 生产以 `--env-file` 核验输出 PASS；回填下发单 §7 回执（含退出码） | 下发单 XR-OPS-07-ENV-001 |
| A4 | **S2 生产实机段 3 项**：L1-5b（`.env` 置回 → 受管重启 → `/health` → 恢复）/ L2-5（按 `channel_report` 复位 + 写路径恢复）/ L3-5b（生产镜像回切 + 回滚后 15 分钟内 `verify_release.py` 无 FAIL） | OPS + 研发 | 🟡 离线段 + 本地活实例段已闭环（14 PASS / 3 PENDING / 0 FAIL） | 3 项全部 PASS 并回填 S2 报告 §8；**停止服务后必须核对端口**（D-04） | S2 报告 v1.1.0 §8 |
| A5 | **G7 端到端转发复核**：OpenBase B 通道按 `X-Tenant-ID` 选租户级 Key 的真实转发 | OB/LL | 🟡 代码 + `.env` 注入完成、进程内选择 PASS；**端到端复核因共享 PG 中断未完成** | 真实 `/openllm/v1/writeback` 三路经 OpenBase 转发 `accepted=true` 并留证 | 清单 v2.2.0 G7；台账 XR-OPS-04 |
| A6 | **XR-OPS-04 生产 Key 注入/轮换 + DPS 码表登记** | OPS/研发 | 未启动 | 密钥注入与轮换记录归档；DPS 码表（org/tenant）登记可查 | 台账 XR-OPS-04 |
| A7 | **生产发布门禁执行**：`scripts/verify_release.py --base-url <生产>` | OPS/OB | 工具就绪（本地活实例 PASS 7 / FAIL 0） | 生产实例 0 FAIL（WARN/INFO 允许）方可切流 | 执行记录 v1.4.0 §2 |
| A8 | **共享库主备启动探测（本机备用库通道）**：每次启动前探测主用 PostgreSQL，异常切本机 `127.0.0.1:5432`，双不可达拒绝启动 | OB | ✅ **Phase 1/2/3 已交付**：`-DbMode` + `-Action dbcheck` + 前置门禁 + 5 服务覆盖；**Phase 3（P0）**：数据面探针（`infra_probe.py`）、主用不通即切备用（含四设施）、数据同步挂起告警、证据 schema v3；**另：每次启动服务前（全量/`-Only`/monitor 自愈）按服务依赖校验数据库，当前通道共享库不可用则拒绝该服务启动**；守门用例 21 例 | 主用数据面可用→primary；主用不通→自动切备用且留痕；双不可达→exit 2；单服务启动前校验可见且 PG 不可用即拒启 | 运维记录 v1.12.0 §16.8 / §16.9 |

> A1~A3 为同一批 `.env` 下发动作（可一次窗口完成，分别留回执）；A4 依赖 A1/A2 已下发；A5 依赖共享 PG 健康；A7 为最终放行闸门。

## 4. B 类：本仓工程项

| ID | 事项 | 优先级 | 现状 | 处置方案 | 验收判据 |
|:--:|------|:------:|------|---------|---------|
| B1 | **D-04 编排 PID 记录与真实监听进程错位**：`service-orchestrator.ps1 -Action stop` 首次按 PID 记录停止未生效（PID 296 包装进程 vs 真实 uvicorn 34120） | **P0（运维正确性）** | 已登记（S2 报告 v1.1.0 D-04） | ① `start` 时以**端口反查真实监听 PID** 记录（`Get-NetTCPConnection -State Listen`）；② `stop` 增加「PID 未命中 → 端口兜底」；③ 停止后输出端口核对结果；④ 补单测/集成测（对假进程表 stub）；⑤ 运维手册与回滚方案同步「以端口核对为准」 | `stop` 一次即停净（端口无监听）；连续 3 次启停无残留；单测覆盖 PID 命中/未命中两分支 |
| B2 | **S7 门禁 B 面**：SMOKE-S0-S6、K07-SYS-1 | P1 | 需真实四仓运行态；本机四仓未运行、OpenLLM 因 `psycopg` 缺失不可启动 | 联调窗口内启动四仓（含 OIDC IdP）后执行 `scripts/gate_aggregate.py`，回填 `doc/test/evidence/s7/gate/**` | 冒烟与 K07 矩阵由 PENDING 转 PASS（或附可解释原因） |
| B3 | **github 补推** | P1 | ✅ **已闭环（2026-10-25）**：`4cfa4e7` / `c187348` / `40364ff` / `4d3847b` 已推送，三远程 HEAD 一致（`4d3847b`） | 后续网络异常时按同法重试并 `ls-remote` 核对 | origin/backup/github 三者 HEAD 相同 |
| B4 | **运行期依赖与环境固化**（XR-OPS-02 剩余）：OpenLLM 缺 `prometheus_client`/OTel gRPC 子包、宿主 Python 缺 `psycopg` pq wrapper、编排裸 `python` 需 shim | P1 | 现以临时桥接/替代运行时规避 | ① 各仓 `requirements`/镜像锁定依赖并加 `python -c "import psycopg, prometheus_client"` 自检；② 编排增加启动前依赖自检（失败即显式报错，不静默）；③ 文档化 shim + `OPENBASE_PY_DEPS/PY_ROOT` 前置（本机开发面） | 干净环境按文档一次启动成功；依赖自检失败可读报错 |

> 说明：B1 是**唯一需要改代码**的本仓项，且直接关系回滚动作正确性，建议优先于其它迭代项。

## 5. C 类：跨仓能力与契约

| ID | 事项 | 责任方 | 现状与阻塞 | 处置方案 | 解冻/验收 |
|:--:|------|:------:|-----------|---------|----------|
| C1 | **OpenRAG / OpenMemory「码 → 真实 UUID」** | RG/OM + OB | 冻结：OpenBase `Tenant` 仅 `id`(bigint)/`name`/`code`（`openbase/core/models/base.py:391-401`），**不含目标系统 UUID** | 方案 A（推荐）：目标侧提供 `code → uuid` 查询接口，OpenBase 出站前解析并缓存（TTL + 失败回退原码）；方案 B：目标侧接受码并在内部解析（沿用 C1-d 双形态） | 目标主数据可读；解析失败 fail-closed 或显式告警；灰度开关 + 回退开关 |
| C2 | **OpenLLM 写路径仍 UUID-only** | LL + OB | 范围限定：写面仅接受 UUID | 单独立项评审：OpenLLM 写路径接受租户码 → 内部解析；需评估幂等键、审计口径与回滚语义 | 评审通过后按 C1-d 模式实现；未通过维持现状 |

## 6. D 类：冻结 / 不建设（仅登记解冻条件）

| ID | 事项 | 裁定 | 解冻条件 |
|:--:|------|------|---------|
| D1 | XR-LLM-03 模型对比「推荐」 | 冻结（无标注/评分数据） | 具备结构化评分数据源与可解释口径 |
| D2 | XR-LLM-04 成本优化建议「应用」 | 冻结（启发式文本、无建议 ID 与回滚语义） | 结构化建议 + 幂等执行 + 回滚端点 |
| D3 | XR-LLM-05 单条工具调用取消 | 冻结（仅链级取消） | 可中断执行器落地 |
| D4 | OB-05 注册/找回密码 | 不建设（企业内平台由管理员开户/重置） | 引入邮件与风控基础设施 |

## 7. 迭代解决方案

### 7.0 共享库主备启动探测（A8，优先执行；Phase 1/2/3 已交付，Phase 4 挂起）

| 阶段 | 内容 | 状态 | 验收 |
|:----:|------|:----:|------|
| **Phase 1（P0）** | 受管入口启动前探测主用 PostgreSQL（`pg_isready` → TCP 回落）；异常自动切本机 `127.0.0.1:5432`；5 个服务按各自 DSN 仅替换主机端口；双不可达拒绝启动（退出码 2）；`-Action dbcheck` 只探测；证据 JSON（脱敏）+ 结构日志；单测 9 例 | ✅ **已交付** | 主用可达→primary；主用异常→standby（5 目标均 127.0.0.1）；双不可达→exit 2 且 8000 无监听 |
| **Phase 2（P1）** | ① `monitor` 周期复检（默认 ≥60s，`-DbRecheckSec` 可缩短；主用恢复/失联**只提示不回切**，证据 `db-monitor-recheck-*.json`）；② Redis/Qdrant/Neo4j/MinIO 纳管**探测**（TCP，仅提示不阻断，PG 为唯一硬门禁）；③ `dbcheck -Json`（schema v2，含 `dependencies` / `evidence_path`）；守门用例 9 → 15 例 | ✅ **已交付** | 主用恢复可见提示且**未重启任何服务**；四设施状态入证据；JSON stdout 可直接解析 |
| **Phase 3（P0 子集，用户决策 2026-10-25）** | ① 判定升级为**数据面探针**（`scripts/infra_probe.py`，stdlib）：PG `select 1` / Redis `PING+DBSIZE` / Qdrant `GET /collections` / Neo4j `RETURN 1` / MinIO `health/ready`；② 探针不可用时**显式回落 TCP** 并记 `degraded`；③ **主用数据面不通即切备用**：PG 硬门禁 + Redis/Qdrant/Neo4j/MinIO 覆盖；④ **每次启动服务前按依赖校验**（全量/`-Only`/monitor 自愈，`-ProbeTtlSec` 内复用）；⑤ 证据 schema v3（`data_plane`）；守门用例 15 → 21 例 | ✅ **已交付** | 五目标 `data-plane` 判定；主用不通→切备用并 WARN 留痕；双不可达→exit 2；单服务启动前校验可见、PG 不可用即拒启；`-ProbeLevel tcp` 兼容旧行为 |
| **Phase 4（P2，数据同步，挂起）** | ① 按设施选型同步：PG `pg_dump/pg_restore`（或主用改 `wal_level=logical` 后逻辑复制）、Redis `REPLICAOF`、Qdrant snapshot 恢复、MinIO `mc mirror`、Neo4j `dump/load`；② 定义 RPO/RTO 与回切合并策略；③ 应用内启动自检开关（`OPENBASE_DB_STARTUP_PROBE=warn|require|off`）；④ Chroma 纳管；⑤ 双活/只读语义单独立项 | **挂起（用户决策）** | 切换后数据可用性达标；回切前后一致性核验通过 |

> Phase 3 的边界：**数据面同步问题暂时挂起**——切到备用后数据可能为空或落后，切换必然 WARN 留痕；
> 运行期仍**只提示不回切**（连接池漂移），回切须重启编排。
> 绕过编排直接 `uvicorn` 仍不触发探测（Phase 4 处理）；备用库为主用**手工复刻**，切换前提是备用实例已按主用 UUID 复刻（运维记录 §12）。

### 7.1 v1.13.0 —— 运维收口窗口（无新功能，OPS 主导）

| 项 | 内容 |
|----|------|
| 范围 | A1、A2、A3、A4、A5、A6、A7 + B3 |
| 前置 | 生产部署面可操作；共享 PG 健康；下发单与回滚方案在手 |
| 执行顺序 | ① 备份 `.env` → ② A1/A2/A3 一次下发（分项回执）→ ③ A4-L1 开关回退演练 → ④ A4-L2 通道复位 → ⑤ A4-L3 镜像回切 + `verify_release` → ⑥ A5 G7 端到端复核 → ⑦ A6 Key 轮换/码表 → ⑧ A7 放行核验 → ⑨ B3 补推 |
| 门禁 | 生产 `ENV=production` 启动成功；反例拒绝；S2 §8 三项回填 PASS；`verify_release` 0 FAIL；三远程 HEAD 一致 |
| 回滚 | 三级回滚（开关/通道/版本），回滚后 15 分钟内 `verify_release` 复验；**stop 后核对端口（D-04）** |
| 产出 | 下发单回执、S2 报告升 v1.2.0（[Approved]）、执行记录升 v1.5.0（[Approved]）、生产核验输出归档 |

### 7.2 v1.13.1 —— 可靠性加固（研发主导，先于/并行于 7.1 的代码部分）

| 项 | 内容 |
|----|------|
| 范围 | B1（D-04 修复）、B4（依赖与环境固化） |
| 前置 | 无（纯本仓代码/脚本，可在开发面独立验证） |
| 实施要点 | B1：`start` 记录真实监听 PID；`stop` 增加端口兜底与结果回显；单测覆盖两分支；同步回滚方案 §4.1 与运维手册。B4：各仓依赖锁定 + 启动自检 + 文档化前置 |
| 门禁 | `ruff` 0 错误；新增单测全绿；全量回归不劣于基线（当前 **1311 passed / 4 skipped / 0 功能失败**）；连续 3 次启停无残留端口 |
| 回滚 | 纯脚本/文档回退，无数据结构变更 |
| 产出 | 编排脚本修复 + 单测；运维手册 v1.1.0；S2 报告补充 D-04 闭环状态 |

### 7.3 v1.14.0 —— 跨仓能力补齐（需跨仓排期与主数据）

| 项 | 内容 |
|----|------|
| 范围 | C1（码→UUID）、C2（写路径码支持评审）、B2（S7 B 面联调窗口） |
| 前置 | C1 需 OpenRAG/OpenMemory 提供主数据查询或接受码；B2 需四仓运行态窗口（依赖 B4 完成） |
| 实施要点 | C1 按方案 A 落地（出站解析 + TTL 缓存 + 失败策略 + 灰度/回退开关），沿用 C1-d 纯函数三仓复用模式；C2 先行评审（不预先承诺实现）；B2 在窗口内跑门禁聚合 |
| 门禁 | 解析失败不产生伪主体头；既有 UUID 路径零变化；三仓回执；门禁聚合无新增 FAIL |
| 回滚 | C1 灰度开关置假即回退原码路径 |
| 产出 | 派单 + 三仓回执；门禁聚合证据；台账与审计更新 |

### 7.4 依赖与关键路径

```
A1/A2/A3（.env 下发）
      └─> A4-L1（重启验证）
A5（G7 端到端）  <- 依赖共享 PG 健康
A4-L2/L3        <- 依赖通道运行态 + 镜像
A7（放行核验）  <- 依赖 A1~A4 全部完成
B1（编排修复）  —— 独立，建议最先做（影响回滚动作正确性）
A8（共享库主备）—— Phase 1/2/3 已完成；Phase 4（数据同步/回切）挂起，可与 B1 合并迭代
B4（环境固化）  ——> B2（四仓运行态窗口）——> S7 B 面
C1              <- 依赖目标侧主数据；C2 <- 依赖评审结论
```

## 8. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 共享 PG 抖动（本轮多次出现 `connection was closed`） | 端到端/全量回归失败，误判为回归 | 失败项**隔离复跑**判定；A5 安排在 PG 健康窗口；关键证据要求双跑一致 |
| 门禁回退即失去保护（回滚方案 §7.1） | L1 回退后应用在配置不合规下可启动 | 回退须与「临时接受门禁缺失」授权一并决策；尽快恢复；留痕 |
| 编排 stop 未停净（D-04） | 端口残留、新旧进程并存导致验证失真 | B1 修复前，一律以端口核对为准并重试；禁止裸 `Stop-Process` |
| 跨仓依赖排期不可控（C1/C2/B4） | v1.14.0 整体后移 | 本仓先交付 C1 调用侧骨架 + 灰度为假；以派单回执推动 |
| 版本载体漂移（如 lockfile 1.3.0、旧基线三处不统一） | 回退时版本自检失真 | 发布前执行版本一致性检查；L3 回退记录人工核对（S2 D-01） |

## 9. 验收与放行判据（汇总）

| # | 判据 | 通过标准 |
|:-:|------|---------|
| 1 | 生产启动 | A1~A3 下发后 `ENV=production` 正常启动，`/health` 200，三组件 `ok` |
| 2 | 门禁反例 | 任一生产门禁回落后**拒绝启动**（进程级） |
| 3 | 回滚可执行 | S2 §8 三项 PASS；stop 后端口无监听；回滚后 15 分钟内 `verify_release` 0 FAIL |
| 4 | 跨租户写回 | G7 三路 `accepted=true`，重复投递 `duplicated=true` |
| 5 | 回归基线 | 后端 ≥1311 passed / 0 功能失败；前端 370 passed；`ruff` 0 错误 |
| 6 | 版本一致 | 三处锚点 + lockfile 一致；三远程 HEAD 一致 |
| 7 | 文档留痕 | 下发回执、演练报告、执行记录均升版并附修订历史 |

## 10. 附录 A：来源追溯

| 本文条目 | 来源 |
|---------|------|
| A1/A2 | 必办事项清单 v2.2.0 §1（G1/G2） |
| A3 | 生产环境配置下发单 XR-OPS-07-ENV-001 §2~§7 |
| A4 | S2 三级回滚演练报告 v1.1.0 §8（L1-5b / L2-5 / L3-5b） |
| A5/A6 | 必办事项清单 v2.2.0 G7；台账 XR-OPS-04 |
| A7 | 发布强制核验执行记录 v1.4.0 §2（`verify_release.py`） |
| A8 | 《OpenBase-本地备用基础设施安装与主备切换记录-v1.12.0》§16 / §16.8 / §16.9；`scripts/service-orchestrator.ps1`；`scripts/infra_probe.py`；`tests/test_orchestrator_db_failover.py`（21 例） |
| B1 | S2 报告 v1.1.0 §7（D-04） |
| B2 | 收口审计 v1.3.0 §5#5；S7 门禁 16 例守门用例 |
| B3 | 本会话推送记录（`4cfa4e7` / `c187348` / `40364ff` / `4d3847b` 已推，三远程一致） |
| B4 | 台账 XR-OPS-02「正式镜像依赖仍待 OPS 固化」；S2 报告 §2 |
| C1/C2 | 收口审计 v1.3.0 §5#1/#2（含代码级复核） |
| D1~D4 | 台账 XR-LLM-03/04/05、OB-05 |

## 11. 附录 B：关键命令

```bash
# 生产放行核验（0 FAIL 方可切流）
python scripts/verify_release.py --base-url http://<prod>:8000 --expected-version 1.4.12

# 生产开关下发核验（开关值以目标 env 为准）
python scripts/verify_production_switches.py --env-file <目标 .env> --json <回执路径>

# S2 实机段：受管启停（停止后必须核对端口）
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/service-orchestrator.ps1 -Action stop -Only openbase
Get-NetTCPConnection -LocalPort 8000 -State Listen

# 本地回归基线
python -m pytest tests --ignore=tests/test_s7_t6_gate.py
python -m pytest tests/test_s7_t6_gate.py
cd openbase-ui && npm run test
```

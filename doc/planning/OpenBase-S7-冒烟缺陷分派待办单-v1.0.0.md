# OpenBase-S7-冒烟缺陷分派待办单-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S7-FAULT-DISPATCH-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Draft] |
| 日期 | 2026-09-11 |
| 作者 | AI（S7 批次 9 冒烟缺陷分派会话；证据与各仓配置只读核对 2026-09-11） |
| 用途 | **冒烟缺陷分派与闭环回填**：将 S7-T6-2 全量冒烟 S0~S6 实测暴露的三项功能缺陷（F-1/F-2/F-3），逐条落笔为「现象与证据 → 根因判定 → 修复动作 → 验证方式 → 回填位置 → 风险与边界」，供责任方按单修复、重跑指定用例、回填台账，并由 OpenBase 侧复核收口 |
| 上游依据 | ①`doc/test/evidence/s7/smoke/smoke-summary.json`、`doc/test/evidence/s7/smoke/s0-s6-cases.json`（P0 30 例：PASS 14 / FAIL 9 / BLOCKED 7；P1 2 例 BLOCKED）；②`doc/test/evidence/s7/env/env-check.json`（READY 14 / UNREACHABLE 2 / BLOCKED 1）；③《OpenBase-S7-联调窗口环境检查报告-v1.0.0.md》（`doc/planning/`，内部 **v1.0.2**，§2.6 四项功能缺陷）；④《OpenBase-真实联调冒烟清单-v1.0.0.md》（仓根，内部 **v1.1.0**，§3 用例定义）；⑤各仓实际配置文件（只读定位）；⑥《OpenBase-S7-沙箱外执行单-v1.0.0.md》（`doc/planning/`，内部 **v1.0.5**，§2/§3 结构与回填位）；⑦《OpenBase-数据隔离实现任务卡-v1.0.0.md》（K02/K07/K09/K10/K15，七线 JT 口径回填位） |
| 关联证据 | `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}`；`doc/test/evidence/s7/env/env-check.json`；`doc/test/evidence/s7/gate/gate-aggregate.json` |
| 使用说明（闭环四步） | **① 责任方按单修复**（§2~§4「修复动作」）→ **② 重跑指定用例**（各缺陷「验证方式」用例 ID 清单 + 命令模板）→ **③ 回填三处**（执行单 §2/§3、测试报告 §2.2、`smoke-summary.json`）→ **④ 通知 OpenBase 侧复核**（§7 复核动作） |
| 脱敏口径 | 本单**不输出任何明文密钥 / 口令**；数据库 / Redis 连接串仅记 host 与库名，键值以「已配置 / 脱敏」表述；`.env` 只引用键名，值以「当前值 / 目标值」呈现（密钥类不落值） |
| 适用范围 | S7 段冒烟 S0~S6 暴露的 **F-1 / F-2 / F-3**；**不含** F-4（统一前端路由告警，v1.0.2 已修复，E2E 9/9 PASS）与 S5-6（禁停服务降级，归受控窗口 / T3 纪律） |

### 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-11 | AI（S7 批次 9 冒烟缺陷分派会话） | 初始版本：基于 `smoke-summary.json` / `s0-s6-cases.json` / `env-check.json` 与各仓只读配置核对，形成 §1 分派总表、§2~§4 逐缺陷详单（现象与证据 / 根因判定 / 修复动作 / 验证方式 / 回填位置 / 风险与边界）、§5 闭环检查清单、§6 执行纪律、§7 OpenBase 侧复核动作、附录（用例→缺陷→责任方映射 + 冒烟快照）。**仅新建本单，未改动任何代码、未对四仓执行 git 写操作、未将 `dogfood-output/` 纳入提交面** |

---

## §1 分派总表

> 口径：**阻塞用例数** = 该缺陷直接导致 FAIL / BLOCKED 的 **P0** 用例条数；三缺陷合计 **15** 条。关联断言与关联卡取自《OpenBase-S7-沙箱外执行单-v1.0.5》§2/§3 与《OpenBase-数据隔离实现任务卡-v1.0.0》。

| 编号 | 标题 | 责任方 | 优先级 | 阻塞用例数 | 关联 S7 断言 | 关联卡（七线 JT） | 状态 |
|:---:|------|--------|:---:|:---:|-----------|------------------|:---:|
| **F-1** | OpenLLM 上游 Ollama 不可达（`192.168.0.4:11434` / `localhost:11434` 连接被拒）+ 三真实开关未全开（`open_memory`/`open_rag` client 未注入；`dps` client 已注入但探活 401） | **OpenLLM 仓 + 环境侧**（联调窗口：启动上游 / 改上游地址 / 置开关） | P0 | **8** | S7-T6-2（冒烟 S0~S6） | K15（REAL_* 兜底收口）、K02(LL) | 待修复 |
| **F-2** | OpenRAG 共享库 `collections` 表缺 `tenant_code` 列 → `GET /api/v1/collections`（带 X-API-Key）500、集合创建 / 列表、文本入库（`/documents/text`）、检索、以及经网关的 `rag-proxy query` 500 | **OpenRAG 仓** | P0 | **5** | S7-T6-2、S7-T4-1~4（L2-2 通道矩阵）、S7-T6-4（K07/SYS-1 真实终验） | K10（OpenRAG 强制过滤骨架）、K02(RG) | 待修复 |
| **F-3** | OpenLLM `TRUSTED_PROXY_SOURCES=llm-proxy` 与 OpenBase 注入的 `openbase-llm-proxy` 不一致 → M3 可信源不生效（`identity.proxy_source=null`、审计外部身份未采纳） | **OpenLLM 仓**（白名单取值对齐）；OpenBase 提供协议头单一事实源对标 | P0 | **2** | S7-T6-2、S7-T6-1（RA-06 M3 五项真实面） | K09（编排出站身份透传）、K02(LL) | 待修复 |
| — | **合计** | — | — | **15** | — | — | — |

> **冒烟快照**（`smoke-summary.json`，`generated_at=2026-09-11T18:57:56+08:00`，`openbase_commit=0595bcde788bd19d3a2e21ffc647b827eaa3fded` / 短号 `0595bcd`）：**P0 30 例 PASS 14 / FAIL 9 / BLOCKED 7；P1 2 例 BLOCKED**（`entry_criteria_met=false`）。9 条 FAIL **全部**由 F-1/F-2/F-3 覆盖（F-1 2 条：S0-1、S1-2；F-2 5 条：S1-1、S3-1、S3-2、S3-3、S6-1；F-3 2 条：S0-4、S5-3）；7 条 BLOCKED 中 6 条由 F-1 覆盖（S2-4、S3-4、S5-1、S5-2、S5-4、S5-5），余 1 条 **S5-6** 为禁停服务约束（归受控窗口，不在本单）。

---

## §2 F-1 详单（OpenLLM 上游 Ollama 不可达 + 三真实开关未全开）

### 2.1 现象与证据

证据文件：`doc/test/evidence/s7/smoke/smoke-summary.json` 与 `s0-s6-cases.json`（同源）；`doc/test/evidence/s7/env/env-check.json`。逐条引用如下：

| 用例 ID | 请求（脱敏） | 状态 | 判定 | 证据摘要（脱敏） |
|:---:|------|:---:|:---:|------|
| S0-1 | `GET http://127.0.0.1:8001/openllm/v1/health`（Authorization 已使用） | 200 | **FAIL** | `{"openmemory": "组件 open_memory 不可用: client 未注入", "openrag": "client_not_injected", "dps": "组件 dps 不可用: HTTP 401: 缺少组织或租户标识 (status=401)"}` |
| S1-2 | `GET http://127.0.0.1:8001/openllm/v1/health`（三上游探活） | 200 | **FAIL** | 同上（openmemory/openrag client 未注入 → 上游不可达） |
| S2-4 | `POST http://127.0.0.1:8000/api/v1/llm-proxy/chat`（主通道非流式） | 500 | **BLOCKED** | `{"code":5001,"message":"内部错误，请稍后再试","data":null,"timestamp":"2026-09-11T10:57:55.055096+00:00"}` |
| S3-4 | `POST http://127.0.0.1:8000/api/v1/llm-proxy/chat`（rag） | 500 | **BLOCKED** | `{"code":5001,...}`（Ollama 不可达 + rag client 未注入） |
| S5-1 | `POST http://127.0.0.1:8000/api/v1/llm-proxy/chat`（非流式 /chat） | 500 | **BLOCKED** | `{"code":5001,...}` |
| S5-2 | `POST http://127.0.0.1:8000/api/v1/llm-proxy/chat/stream`（SSE） | 200 | **BLOCKED** | `event: routing` → `{"components":{"need_memory":false,"need_rag":false,"reason":"explicit","rag_source":"skipped"},"model":{"selected":"gpt-4o-mini","reason":"cost"},"parallel":false}`（受上游不可达阻塞） |
| S5-4 | 流式收尾 `EvaluateSession`（依赖 S5-2 流式成功） | — | **BLOCKED** | `—`（依赖 S5-2；受 Ollama 上游不可达阻塞） |
| S5-5 | `POST http://127.0.0.1:8000/api/v1/llm-proxy/chat`（llm-only explicit 语义） | 500 | **BLOCKED** | `{"code":5001,...}` |

> 环境侧佐证 `env-check.json` → `checks[name=openllm_runtime]` 功能注记：`/openllm/v1/health` 显示 openmemory/openrag 组件 client 未注入、dps client 已注入；LLM 推理上游 Ollama（`192.168.0.4:11434` 与 `localhost:11434`）连接被拒 → `/openllm/v1/chat` 5001。对应 `pending_items[id=ENV-OPENLLM-UPSTREAM]`（owner=联调窗口）。

### 2.2 根因判定

1. **上游地址不可达**：OpenLLM 运行态读取的上游为局域网 Ollama。实测配置（只读）：
   - `D:\Trae CN\myproject\Dev\OpenLLM\backend\.env` **L24** `OLLAMA_HOST=http://192.168.0.4:11434`、**L25** `OLLAMA_BASE_URL=http://192.168.0.4:11434/v1`；
   - `D:\Trae CN\myproject\Dev\OpenLLM\.env.shared-infra` **L36** `OLLAMA_HOST=http://192.168.0.4:11434`、**L37** `OLLAMA_BASE_URL=http://192.168.0.4:11434/v1`；
   - 代码默认（`backend\app\core\config.py` **L152~L153**）为 `OLLAMA_BASE_URL=http://localhost:11434/v1` / `OLLAMA_HOST=None`。
   实测 `192.168.0.4:11434` 与 `localhost:11434` **连接被拒**（All connection attempts failed）→ `/openllm/v1/chat` 返回 5001。
2. **三真实开关未全开**：`backend\.env` 中**未出现** `OPENLLM_OPENMEMORY_REAL` / `OPENLLM_OPENRAG_REAL` 两键 → 生效值为代码默认 `False`（`config.py` **L247~L250** `OPENLLM_OPENMEMORY_REAL` default `False`；**L218~L221** `OPENLLM_OPENRAG_REAL` default `False`；模板 `backend\.env.example` **L40/L41** 亦为 `false`）→ `open_memory` / `open_rag` **client 未注入**。
3. **dps 侧另一情形**：`backend\.env` **L51** `OPENLLM_DPS_REAL=true`（真实契约已开，且 **L52~L55** 四头 ORG/TENANT/USER/ROLE 已配）→ dps client **已注入**，但探活因**缺少组织 / 租户头**返回 HTTP 401（`/openllm/v1/health` 探活口径，非本次分派阻塞项）。

> **判定结论**：F-1 = 「上游 Ollama 不可达」+「`OPENLLM_OPENMEMORY_REAL` / `OPENLLM_OPENRAG_REAL` 未开启」双因素叠加；属**环境待办 + 开关未置**（`env-check.json` 明确标注「环境待办」），非用例设计缺陷。

### 2.3 修复动作

> 责任方：**OpenLLM 仓 + 环境侧（联调窗口）**。以下键名均自实际文件只读核对。

**步骤 A — 启动 Ollama（或改上游地址为可用实例）**

| 文件 | 行号 | 键名 | 当前值 | 目标值 |
|------|:---:|------|--------|--------|
| `OpenLLM\backend\.env` | L24 | `OLLAMA_HOST` | `http://192.168.0.4:11434` | 可达实例地址（如已启动的 Ollama） |
| `OpenLLM\backend\.env` | L25 | `OLLAMA_BASE_URL` | `http://192.168.0.4:11434/v1` | 可达实例 `<base>/v1` |
| `OpenLLM\.env.shared-infra` | L36/L37 | `OLLAMA_HOST` / `OLLAMA_BASE_URL` | `http://192.168.0.4:11434` / `.../v1` | 与上保持一致 |

**步骤 B — 置三真实开关（逐键当前值 / 目标值）**

| 文件 | 行号 | 键名 | 当前值 | 目标值 |
|------|:---:|------|--------|--------|
| `OpenLLM\backend\.env` | —（缺省） | `OPENLLM_OPENMEMORY_REAL` | 未配置 → 生效 `False`（config.py L247~L250 默认） | `true` |
| `OpenLLM\backend\.env` | —（缺省） | `OPENLLM_OPENRAG_REAL` | 未配置 → 生效 `False`（config.py L218~L221 默认） | `true` |
| `OpenLLM\backend\.env` | L51 | `OPENLLM_DPS_REAL` | `true` | 保持 `true`（已注入） |
| `OpenLLM\backend\.env` | L52~L55 | `OPENLLM_DPS_REAL_ORG` / `_TENANT` / `_USER` / `_ROLE` | `dps-org-001` / `dps-tenant-001` / `1` / `super_admin` | 保持（与 DPS 预置实体一致） |

**步骤 C — 核对起服日志 `contract=real`（S0-1 判据）**：OpenLLM 起服日志须出现三注入点契约生效标记（`open_memory` / `open_rag` / `dps`），对齐冒烟清单 §3「S0-1 三真实开关生效：起服日志出现 `contract=real`」。

**注意事项**：
- 上游地址 / 开关属**本机环境配置**，`.env*` 已被 `.gitignore` 排除，**不得入库**；
- **密钥 / 口令零进入提交面**；不得为「过测试」放宽断言或屏蔽 5001；
- 开关可临时置 `true` 冒烟、失败即回退 `False`（冒烟清单 §2.2 / §4 口径）。

### 2.4 验证方式

- **重跑用例 ID（8 例，期望 PASS）**：`S0-1`、`S1-2`、`S2-4`、`S3-4`、`S5-1`、`S5-2`、`S5-4`、`S5-5`。
- **期望结果**：
  - `S0-1` / `S1-2`：`/openllm/v1/health` 三组件均可用（无 `client 未注入` / `client_not_injected`）；
  - `S2-4` / `S3-4` / `S5-1` / `S5-5`：主通道非流式 / rag / llm-only 均 `2xx`，无 `code=5001`；
  - `S5-2`：SSE 事件 `routing→chunk→done` 正常；
  - `S5-4`：流式收尾触发 `EvaluateSession` 并在真实 OpenMemory 出现该轮记忆。
- **命令模板**（PowerShell；尖括号占位替换为真实值）：
  ```powershell
  # 探活（S0-1 / S1-2）
  curl.exe -s -H "Authorization: Bearer <JWT>" 'http://127.0.0.1:8001/openllm/v1/health'

  # 主通道（S2-4 / S3-4 / S5-1 / S5-5）
  curl.exe -s -X POST -H "Authorization: Bearer <JWT>" -H "Content-Type: application/json" `
    -d '{\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"stream\":false}' `
    'http://127.0.0.1:8000/api/v1/llm-proxy/chat'

  # 结果归档 + 聚合（真实面）
  python 'D:\Trae CN\myproject\Dev\OpenBase\scripts\gate_aggregate.py' --face real --only SMOKE-S0-S6 --out 'D:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\s7\gate\gate-aggregate.json'
  ```
  逐例结果归档至 `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}`。

### 2.5 回填位置

| 回填位 | 具体位置 |
|--------|---------|
| 各仓 JT 台账 / 任务卡 | OpenLLM 仓 JT 台账；`OpenBase-数据隔离实现任务卡-v1.0.0.md` **K15（REAL_* 兜底收口）** / K02(LL) 行状态 |
| 执行单 §2/§3 | 《OpenBase-S7-沙箱外执行单-v1.0.5》**§2.5**（P2 执行结果回填）/ **§3.5**（T6 真实面执行结果） |
| 测试报告 §2.2 | 《OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0》**§2.2 联调窗口实跑结论更新**（S7-T6-2 行） |
| 冒烟证据 | `doc/test/evidence/s7/smoke/smoke-summary.json`（`cases[].verdict` / `pending_or_failed[]`）与 `s0-s6-cases.json` |
| 环境检查报告 | 《OpenBase-S7-联调窗口环境检查报告-v1.0.0》（内部 v1.0.2）**§2.6 F-1** 行状态、`env-check.json` `pending_items[ENV-OPENLLM-UPSTREAM]` |

### 2.6 风险与边界

- **仅环境 / 开关调整**，不得为过测试改动 OpenLLM 业务代码或放宽健康 / 对话断言；
- 上游地址变更须保证 DPS / Redis 等其余依赖不受影响；改后须保留起服日志作为 S0-1 判据；
- **不得停止或重启服务**（冒烟期）；Ollama 启动属新增进程，须与受管编排一致；
- **S5-6（OpenRAG 停服降级）不在本单**：其 BLOCKED 缘于「任务约束禁止停止 / 重启服务」，归 T3 / 受控窗口，不得以 F-1 修复名义启停服务；
- 密钥 / 口令不入库、不入报告明文；**回归失败即停**。

---

## §3 F-2 详单（OpenRAG 共享库 `collections` 表缺 `tenant_code` 列）

### 3.1 现象与证据

证据文件：`doc/test/evidence/s7/smoke/smoke-summary.json` 与 `s0-s6-cases.json`；`env-check.json`。

| 用例 ID | 请求（脱敏） | 状态 | 判定 | 证据摘要（脱敏） |
|:---:|------|:---:|:---:|------|
| S1-1 | OpenRAG / OpenMemory 鉴权（`X-API-Key` 已使用） | 500 | **FAIL** | `RAG no-key=401, key=500; MEM no-key=401, key=200` |
| S3-1 | `POST/GET http://127.0.0.1:8010/api/v1/collections`（X-API-Key） | 500 | **FAIL** | `{"code":"INTERNAL-5000","message":"创建知识库失败: ... asyncpg.exceptions.UndefinedColumnError: column collections.tenant_code does not exist ... [SQL: SELECT collections.id, collections.name, col...]"}` |
| S3-2 | `POST http://127.0.0.1:8010/api/v1/collections/{cid}/documents/text` | 500 | **FAIL** | `{"code":"INTERNAL-5000","message":"文本入库失败: ... column collections.tenant_code does not exist ..."}`（无法进入 PENDING→COMPLETED 轮询） |
| S3-3 | `POST http://127.0.0.1:8010/api/v1/collections/{cid}/query/retrieve` | 500 | **FAIL** | `{"code":"INTERNAL-5000","message":"检索失败: ... column collections.tenant_code does not exist ..."}` |
| S6-1 | `POST http://127.0.0.1:8000/api/v1/rag-proxy/collections/{cid}/query/retrieve`（经网关） | 500 | **FAIL** | `{"code":"INTERNAL-5000","message":"检索失败: ... column collections.tenant_code does not exist ..."}` |

> 环境侧佐证 `env-check.json` → `checks[name=openrag_runtime]`：`collections 相关端点因 DB 列 collections.tenant_code 缺失返回 INTERNAL-5000`；`impact` 明确「**真实缺陷，非环境待办**」。对应 `pending_items[id=ENV-OPENRAG-SCHEMA]`（owner=OpenRAG 子系统仓）。

### 3.2 根因判定

1. **运行态数据库为共享 PG**：`D:\Trae CN\myproject\Dev\OpenRAG\.env` **L9** `OPENRAG_DATABASE_URL=postgresql+asyncpg://<user>@192.168.0.151:5432/nuct`（共享库 `nuct`，口令已配置、脱敏）。共享库内 `collections` 为**早期建立的既有表，缺 `tenant_code` 列**。
2. **ORM 已声明列、但既有表不会被自动 ALTER**：`D:\Trae CN\myproject\Dev\OpenRAG\src\openrag\storage\postgres.py` **L60~L89** `CollectionTable` 已声明 `tenant_code = Column(String(64), nullable=False, default="default", server_default="default")`（**L76**）及索引 `idx_collections_name` / `idx_collections_tenant` / `uq_collections_tenant_name`（**L86~L88**）；但 `PostgresStore.initialize()`（**L279~L306**）仅执行 `Base.metadata.create_all`（**L300~L301**）——**`create_all` 对既有表不会 `ALTER TABLE ADD COLUMN`**。
3. **PG 侧缺正向落列迁移**：`D:\Trae CN\myproject\Dev\OpenRAG\src\openrag\storage\migrations.py` 模块 docstring 明示「**本仓无 alembic → create_all/DDL 幂等迁移器**」（**L1**）；`s3_tenant_columns` 迁移项（**L4**）的**可执行入口为 SQLite**（`ensure_tenant_columns_sqlite` **L109**、`run_tenant_column_migration_sqlite` **L251**）；**PG 侧仅有 `plan_rollback_postgres_tenant_columns()`（L311，回滚）与 `plan_composite_unique_postgres()`（L432，复合唯一）两个计划函数，缺「PG 正向 `ADD COLUMN tenant_code` + 存量回填 + 索引」的执行体，且未在启动 / 部署链路中执行**。
4. **部署脚本显式不支持 PG**：`D:\Trae CN\myproject\Dev\OpenRAG\scripts\tenant_backfill_report.py` **L47~L49** 对 `postgresql*` 直接 `SystemExit("PG 后端对账请在 S3 联调环境执行（R-4）；本机以 SQLite 验证")`。
5. **列名完全吻合报错**：报错 `column collections.tenant_code does not exist` 与缺失迁移的列名一致，且 `SELECT collections.id, collections.name, ...` 为 ORM 默认列清单查询，佐证「表结构落后于 ORM 模型」。

> **判定结论**：F-2 = **共享 PG `collections` 历史表缺 `tenant_code` 列 + OpenRAG 缺 PG 正向幂等迁移执行路径**；属**真实代码 / 迁移缺陷**（责任在 OpenRAG 仓）。

### 3.3 修复动作

> 责任方：**OpenRAG 仓**。须在 OpenRAG **既有迁移机制内**（`migrations.py` 幂等迁移器，非引入 alembic）以**正式迁移**落地。

1. **新增 PG 正向迁移执行体**（建议置于 `src\openrag\storage\migrations.py`，与 SQLite 入口同构、幂等可重放）：
   - 落列：`ALTER TABLE collections ADD COLUMN IF NOT EXISTS tenant_code VARCHAR(64) NOT NULL DEFAULT 'default';`（`documents` / `chunks` 同构，对齐 ORM `postgres.py` L76 / L112 / L148）；
   - 存量回填：`collections` 按 `metadata` 推导（复用 `_derive_tenant_from_metadata`，键集 `METADATA_TENANT_KEYS`），不可推导行落 `BACKFILL_RESERVED_TENANT_CODE`（对齐 SQLite 口径 `migrations.py` L149~L192）；`documents` / `chunks` 从所属 `collections` 继承；
   - 索引：`CREATE INDEX IF NOT EXISTS idx_collections_tenant ON collections (tenant_code);`（`idx_documents_tenant` / `idx_chunks_tenant` 同构，对齐 L86~L88 / L124 / L159）；
   - 复合唯一：复用 `plan_composite_unique_postgres()`（**L432~L443**）——`DROP INDEX IF EXISTS uq_collections_tenant_name` + `CREATE UNIQUE INDEX IF NOT EXISTS uq_collections_tenant_name ON collections (tenant_code, name);`（**与 K10 / B2 定案口径一致**：collection 唯一升级为 `(tenant_code, name)` 复合唯一）。
2. **接入执行链路（关键，否则仍不落列）**：在 `PostgresStore.initialize()`（`postgres.py` **L279~L306**）`create_all` 之后调用该 PG 迁移；或以迁移标记位（对齐 SQLite 的 `storage_migration_log` 语义，L24~L25 / L79~L106）保证幂等；另可在 `scripts\tenant_backfill_report.py` 放开 PG 分支（现 L47~L49 直接拒绝 PG）。
3. **注意事项**：
   - 迁移**幂等**（`IF NOT EXISTS` / 标记位），可重放；**仅限 `collections` / `documents` / `chunks` 三表**的租户列迁移，**不得对共享 PG 做其他破坏性变更**；
   - 迁移前建议先跑同名冲突预检 `report_duplicate_name_conflicts_sqlite`（PG 侧对应检出）避免建唯一索引失败；
   - 口令 / 密钥不入库、不入报告；迁移命令走参数化 / 幂等 DDL。

### 3.4 验证方式

- **重跑用例 ID（5 例，期望 PASS）**：`S1-1`、`S3-1`、`S3-2`、`S3-3`、`S6-1`。
- **期望结果**：
  - `S1-1`：OpenRAG 无 key → 401；正确 `X-API-Key`（键名 `OPENRAG_API_SERVICE_API_KEY`，值脱敏）→ 200；
  - `S3-1`：集合创建 / 列表 `2xx`（id 与 name 关联），检索命中（score / 元数据正确）；
  - `S3-2`：文本入库 → `status=PENDING` → 轮询 `GET documents/{id}` → `COMPLETED`；
  - `S3-3`：入库 `COMPLETED` 后 retrieve 命中新文本片段；
  - `S6-1`：经网关 `rag-proxy .../query/retrieve` `2xx`（含 `X-API-Key` 与**域过滤**生效）。
- **命令模板**（PowerShell）：
  ```powershell
  # OpenRAG 迁移落地后，跑既有回归（OpenRAG 仓内）
  python -m pytest tests -q

  # 重跑 collections 全链（S3-1/S3-2/S3-3）
  curl.exe -s -H "X-API-Key: <OPENRAG_API_SERVICE_API_KEY>" -H "Content-Type: application/json" `
    'http://127.0.0.1:8010/api/v1/collections'

  # 经网关（S6-1）
  curl.exe -s -X POST -H "Authorization: Bearer <JWT>" -H "Content-Type: application/json" `
    -d '{\"query\":\"ping\",\"top_k\":5}' `
    'http://127.0.0.1:8000/api/v1/rag-proxy/collections/<cid>/query/retrieve'
  ```
  结果归档至 `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}`；OpenRAG 侧回归留证于 OpenRAG 仓证据目录。

### 3.5 回填位置

| 回填位 | 具体位置 |
|--------|---------|
| 各仓 JT 台账 / 任务卡 | OpenRAG 仓 JT 台账；`OpenBase-数据隔离实现任务卡-v1.0.0.md` **K10（OpenRAG 强制过滤骨架）** / K02(RG) 行状态 |
| 执行单 §2/§3 | 《OpenBase-S7-沙箱外执行单-v1.0.5》**§2.5** / **§3.5** |
| 测试报告 §2.2 | 《OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0》**§2.2**（S7-T6-2 行；并关联 S7-T4 / S7-T6-4 真实面） |
| 冒烟证据 | `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}` |
| 环境检查报告 | 《OpenBase-S7-联调窗口环境检查报告-v1.0.0》（内部 v1.0.2）**§2.6 F-2** 行、`env-check.json` `pending_items[ENV-OPENRAG-SCHEMA]` |

### 3.6 风险与边界

- **仅允许** `collections` / `documents` / `chunks` 的 `tenant_code` 列迁移；**禁止对公共 PG 库做其他破坏性变更**（不得删表 / 改主键 / 全表重写三表以外对象）；
- 迁移须在 **OpenRAG 仓内以正式迁移落地**（迁移器 + 启动 / 部署接入），不得由 OpenBase 侧直连改库绕过；
- **OpenRAG 仓禁 `git add repository`**（禁把 `repository/` 目录纳入提交面）；
- 迁移前做同名冲突预检，迁移后须全量回归（`python -m pytest tests`）；**回归失败即停**；
- 与 K10 / B2 定案口径一致：`(tenant_code, name)` 复合唯一、域过滤 fail-closed；不得为过测试弱化域过滤断言。

---

## §4 F-3 详单（`TRUSTED_PROXY_SOURCES` 取值 `llm-proxy` 与 OpenBase 注入 `openbase-llm-proxy` 不一致）

### 4.1 现象与证据

证据文件：`doc/test/evidence/s7/smoke/smoke-summary.json` 与 `s0-s6-cases.json`。

| 用例 ID | 请求（脱敏） | 状态 | 判定 | 证据摘要（脱敏） |
|:---:|------|:---:|:---:|------|
| S0-4 | `POST http://127.0.0.1:8001/openllm/v1/chat`，头 `X-Proxy-Source: openbase-llm-proxy` | `null` | **FAIL** | 实测对比：`"openbase-llm-proxy": {"delegated":null,"effective":null,"principal":null,"request_id":"req-5e06b84c1cd3","proxy_chain":[],"proxy_source":null}`；`"llm-proxy": {"effective":{"role":"admin","subject_id":"smoke_ext_user","tenant_code":"smoke-ext-tenant","subject_type":"user"},"principal":{...,"auth_method":"***MASKED..."}}` |
| S5-3 | `GET http://127.0.0.1:8001/api/v1/audit-logs` | 200 | **FAIL** | 同上：`openbase-llm-proxy` → `identity.principal=null` / `proxy_source=null`；仅 `llm-proxy` 取值被采纳。伪造头在非受信源下 `principal=null`（不落库） |

> `reason`（原文口径）：OpenLLM `TRUSTED_PROXY_SOURCES=llm-proxy`，不含 OpenBase 注入值 `openbase-llm-proxy`（行为实测：前者 `proxy_source=null`，后者采纳）。对应 `env-check.json` `pending_items[id=ENV-OPENLLM-TRUSTED-SOURCE]`（owner=OpenLLM 子系统仓）。

### 4.2 根因判定

**两侧取值不一致**，实测证据与只读配置逐项对照：

| 侧 | 位置 | 键 / 常量 | 实际取值 |
|----|------|-----------|----------|
| **OpenLLM（运行态）** | `D:\Trae CN\myproject\Dev\OpenLLM\backend\.env` **L28** | `TRUSTED_PROXY_SOURCES` | `llm-proxy`（**实测生效值**，与 OpenBase 注入值不一致） |
| OpenLLM（代码默认） | `backend\app\core\config.py` **L43~L46** | `TRUSTED_PROXY_SOURCES` default | `openbase-llm-proxy` |
| OpenLLM（模板） | `backend\.env.example` **L29** | `TRUSTED_PROXY_SOURCES` | `openbase-llm-proxy` |
| **OpenBase（注入方）** | `openbase\modules\protocol_headers\constants.py` **L88** | `PROXY_SOURCE_LLM` | `openbase-llm-proxy` |
| OpenBase（llm-proxy 出口） | `openbase\modules\llm_proxy\__init__.py` **L67~L68** | 读出站头 | 注入 `X-Proxy-Source: openbase-llm-proxy` |
| 规范（单一事实源） | `doc\design\OpenBase-协议头规范-v1.0.md` **§8 L147~L152** | `PROXY_SOURCE_LLM` | `openbase-llm-proxy`（「值不变，下游白名单零迁移」） |

> **判定结论**：F-3 = **运行态 `.env` 将白名单覆盖为 `llm-proxy`，与规范 / 代码默认 / OpenBase 注入值 `openbase-llm-proxy` 不一致** → OpenLLM 判定 `openbase-llm-proxy` 为非受信来源 → `identity.proxy_source=null`、审计外部身份不采纳（M3 不成立）。

### 4.3 修复动作

> 责任方：**OpenLLM 仓**（白名单取值对齐）；OpenBase 提供协议头单一事实源对标（无需改注入值）。

1. 将 `D:\Trae CN\myproject\Dev\OpenLLM\backend\.env` **L28** `TRUSTED_PROXY_SOURCES` 由 `llm-proxy` 修改为 **`openbase-llm-proxy`**（对齐 `config.py` L43~L46 代码默认、`.env.example` L29、协议头规范 v1.0 §8）。
   - 若需保留既有来源可**逗号分隔追加**：`TRUSTED_PROXY_SOURCES=openbase-llm-proxy,<其他来源>`（对齐白名单「可覆盖追加来源」语义，`config.py` L45）。
2. **统一来源常量口径**：以《OpenBase-协议头规范-v1.0》§8 来源标识常量表为准（`protocol_headers/constants.py` 为单一发布面），两侧不得各自定义同义异值。
3. **回归 OpenLLM 既有用例**：K09 / K15（`OpenBase-数据隔离实现任务卡-v1.0.0.md` **K09 L173**「编排出站身份透传」、**K15 L225**「REAL_* 兜底收口」；对应 OpenLLM 单测 `backend\tests\unit\test_external_identity.py`、`test_s4_t2_identity_base.py`、`test_s4_t3_outbound_headers.py`、`test_s4_t7_channel_preference.py`）。
4. **注意事项**：
   - 仅**白名单取值对齐**，**不得改动身份透传业务逻辑，不得放宽伪造头拦截**（非受信来源 `principal` 仍应 `null`）；
   - `.env` 不入库；密钥 / 口令零进入提交面。

### 4.4 验证方式

- **重跑用例 ID（2 例，期望 PASS）**：`S0-4`、`S5-3`。
- **期望结果**：
  - `S0-4`：带 `X-Proxy-Source: openbase-llm-proxy`（+ 四维身份头）时，`identity.proxy_source=openbase-llm-proxy`、`identity.principal/effective` 非空（采纳）；
  - `S5-3`：`GET /api/v1/audit-logs` 审计 `detail.identity` **六键**（`subject_id` / `subject_type` / `tenant_code` / `role` / `auth_method` / `proxy_source`）齐备，且 `external_user_id` / `external_org_id` 非空；伪造 JWT / 非受信来源头**不落库**。
- **命令模板**（PowerShell）：
  ```powershell
  # S0-4 可信源生效初探（expected: proxy_source=openbase-llm-proxy）
  curl.exe -s -X POST -H "X-Proxy-Source: openbase-llm-proxy" -H "X-User-ID: <uid>" `
    -H "X-Tenant-ID: <tenant>" -H "Content-Type: application/json" `
    -d '{\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}' `
    'http://127.0.0.1:8001/openllm/v1/chat'

  # S5-3 审计核对
  curl.exe -s 'http://127.0.0.1:8001/api/v1/audit-logs'

  # OpenLLM 既有 K09/K15 回归
  python -m pytest tests/unit/test_external_identity.py tests/unit/test_s4_t2_identity_base.py tests/unit/test_s4_t3_outbound_headers.py -q
  ```
  结果归档至 `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}`。

### 4.5 回填位置

| 回填位 | 具体位置 |
|--------|---------|
| 各仓 JT 台账 / 任务卡 | OpenLLM 仓 JT 台账；`OpenBase-数据隔离实现任务卡-v1.0.0.md` **K09** / K15 / K02(LL) 行状态 |
| 执行单 §2/§3 | 《OpenBase-S7-沙箱外执行单-v1.0.5》**§2.5** / **§3.5** |
| 测试报告 §2.2 | 《OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0》**§2.2**（S7-T6-2 行；并关联 S7-T6-1 RA-06 M3） |
| 冒烟证据 | `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}` |
| 环境检查报告 | 《OpenBase-S7-联调窗口环境检查报告-v1.0.0》（内部 v1.0.2）**§2.6 F-3** 行、`env-check.json` `pending_items[ENV-OPENLLM-TRUSTED-SOURCE]` |

### 4.6 风险与边界

- 仅**白名单取值对齐**；不得降低 M3 信任校验强度，不得使非受信来源身份头落库；
- 若选择「统一两侧取值」而非改白名单，须以协议头规范 v1.0 §8 单一事实源为准，并同步评估 OpenBase 其余出口常量一致性；
- 回归 K09 / K15 若失败即停，不得绕过；
- 密钥 / 口令零进入提交面。

---

## §5 闭环检查清单

> 责任方逐缺陷填写；`已修复` / `已重跑` / `已回填` / `OpenBase 复核` 四栏以 `☐` → `☑` 勾选并附责任人 / 日期。**任一栏未完成不得判定缺陷关闭**。

### 5.1 F-1（OpenLLM 上游 Ollama + 三真实开关）

| 检查项 | 是否完成 | 责任人 | 日期 | 备注 |
|--------|:---:|--------|------|------|
| 已修复（启动上游 / 改地址 + 置 `OPENLLM_OPENMEMORY_REAL=true` / `OPENLLM_OPENRAG_REAL=true`，日志 `contract=real`） | ☐ | | | |
| 已重跑（S0-1/S1-2/S2-4/S3-4/S5-1/S5-2/S5-4/S5-5 全 PASS） | ☐ | | | |
| 已回填（执行单 §2.5/§3.5、测试报告 §2.2、`smoke-summary.json`） | ☐ | | | |
| OpenBase 复核（§7） | ☐ | | | |

### 5.2 F-2（OpenRAG `collections.tenant_code` 迁移）

| 检查项 | 是否完成 | 责任人 | 日期 | 备注 |
|--------|:---:|--------|------|------|
| 已修复（OpenRAG 仓内 PG 正向幂等迁移 + 启动 / 部署接入 + 既有回归） | ☐ | | | |
| 已重跑（S1-1/S3-1/S3-2/S3-3/S6-1 全 PASS，含 X-API-Key 与域过滤） | ☐ | | | |
| 已回填（执行单 §2.5/§3.5、测试报告 §2.2、`smoke-summary.json`） | ☐ | | | |
| OpenBase 复核（§7） | ☐ | | | |

### 5.3 F-3（`TRUSTED_PROXY_SOURCES` 白名单对齐）

| 检查项 | 是否完成 | 责任人 | 日期 | 备注 |
|--------|:---:|--------|------|------|
| 已修复（`backend\.env` L28 改为 `openbase-llm-proxy`；K09/K15 回归） | ☐ | | | |
| 已重跑（S0-4/S5-3 全 PASS，`proxy_source=openbase-llm-proxy` 且审计六键 + external 身份） | ☐ | | | |
| 已回填（执行单 §2.5/§3.5、测试报告 §2.2、`smoke-summary.json`） | ☐ | | | |
| OpenBase 复核（§7） | ☐ | | | |

---

## §6 执行纪律（硬约束）

1. **禁伪造结果**：不得填写假 `PASS` / 假响应码 / 假 `request_id` / 假 hash；未执行项一律保持 `PENDING` 并附 `reason`。
2. **不得停止或重启服务**：全程不得停止 / 重启五服务；`S5-6`（OpenRAG 停服降级）与 T3 主备切换归**受控窗口**，不在本单执行。
3. **不得改公共 PG 结构**：**除 F-2 的 `collections` / `documents` / `chunks` 租户列迁移**外，禁止对共享 PG 做任何破坏性变更；F-2 迁移须在 **OpenRAG 仓内以正式迁移落地**（迁移器 + 启动 / 部署接入），不得由 OpenBase 侧直连改库绕过。
4. **OpenRAG 仓禁 `git add repository`**：`repository/` 目录不得纳入提交面。
5. **敏感文件零进入提交面**：`.env*` / 密钥 / 口令 / 令牌不得入库、不得入报告明文（本单已按脱敏口径处理）。
6. **逐项显式 `git add`，禁 `git add -A`**：提交面须显式指定文件；**`dogfood-output/` 不纳入任何提交面**（对齐设计草案 §5.3/§5.4、放行清单 §0 红线）。
7. **不得改动子系统仓**：本单仅在 OpenBase 仓新建；四仓修复由责任方在各自仓内按单执行，须遵循各仓提交纪律。
8. **回归失败即停**：任一回归失败，停止后续步骤并回溯（不掩盖、不带病通过）。

---

## §7 完成后的 OpenBase 侧复核动作

责任方三缺陷修复并回填后，由 OpenBase 侧按序执行复核（复核通过方可关闭缺陷）：

1. **重跑 S0~S6 相关段**：按《OpenBase-真实联调冒烟清单-v1.1.0》§3 逐条真实 HTTP，重点覆盖 F-1（S0-1/S1-2/S2-4/S3-4/S5-1/S5-2/S5-4/S5-5）、F-2（S1-1/S3-1/S3-2/S3-3/S6-1）、F-3（S0-4/S5-3）；结果归档 `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}`。
2. **门禁聚合复跑**：`python 'D:\Trae CN\myproject\Dev\OpenBase\scripts\gate_aggregate.py'`（含 `--face real --only SMOKE-S0-S6`），更新 `doc/test/evidence/s7/gate/gate-aggregate.json`。
3. **更新测试报告断言状态**：《OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0》**§2.2** 逐行由 `PENDING` → `PASS` / `FAIL`（S7-T6-2 行及关联 S7-T4 / S7-T6-1 / S7-T6-4），并同步 §3 段门禁六项。
4. **段门禁六项复评**：① RA-06 ② 冒烟 S0-S6 ③ 对齐清单关闭 ④ 三原则总验证 ⑤ 跨仓会签 ⑥ 24 卡 / JT 回写——逐项复核结论，回填总收官报告 §2 六项聚合自检表。
5. **回填下游文档**：更新《OpenBase-S7-联调窗口环境检查报告-v1.0.0》§2.6 三缺陷行状态、`env-check.json` `pending_items` 对应项；按文档版本管理规范同步版本与修订历史。

---

## 附录

### 附录 A 用例 → 缺陷 → 责任方映射表

| 用例 ID | 段 | 判定 | 归属缺陷 | 责任方 | 关联断言 |
|:---:|:---:|:---:|:---:|--------|---------|
| S0-1 | S0 | FAIL | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S0-4 | S0 | FAIL | **F-3** | OpenLLM（+ OpenBase 协议头对标） | S7-T6-2 / S7-T6-1 |
| S1-1 | S1 | FAIL | **F-2** | OpenRAG | S7-T6-2 |
| S1-2 | S1 | FAIL | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S2-4 | S2 | BLOCKED | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S3-1 | S3 | FAIL | **F-2** | OpenRAG | S7-T6-2 / S7-T4-1~4 |
| S3-2 | S3 | FAIL | **F-2** | OpenRAG | S7-T6-2 / S7-T4-1~4 |
| S3-3 | S3 | FAIL | **F-2** | OpenRAG | S7-T6-2 / S7-T4-1~4 |
| S3-4 | S3 | BLOCKED | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S5-1 | S5 | BLOCKED | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S5-2 | S5 | BLOCKED | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S5-3 | S5 | FAIL | **F-3** | OpenLLM（+ OpenBase 协议头对标） | S7-T6-2 / S7-T6-1 |
| S5-4 | S5 | BLOCKED | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S5-5 | S5 | BLOCKED | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S6-1 | S6 | FAIL | **F-2** | OpenRAG | S7-T6-2 / S7-T6-4 |
| S5-6 | S5 | BLOCKED | **不受控（禁停服务）** | 受控窗口 / T3 | S7-T6-2（挂起登记，不在本单） |

### 附录 B 当前冒烟结果快照

来源：`doc/test/evidence/s7/smoke/smoke-summary.json`（`generated_at=2026-09-11T18:57:56+08:00`，`mode=real`，`openbase_commit=0595bcde788bd19d3a2e21ffc647b827eaa3fded`）。

| 维度 | 值 |
|------|-----|
| P0 总数 | 30 |
| P0 PASS | 14（S0-2/S0-3/S0-5/S2-1/S2-2/S2-3/S2-5/S2-6/S4-0/S4-1/S4-2/S4-3/S6-2/S6-4） |
| P0 FAIL | 9（S0-1/S0-4/S1-1/S1-2/S3-1/S3-2/S3-3/S5-3/S6-1） |
| P0 BLOCKED | 7（S2-4/S3-4/S5-1/S5-2/S5-4/S5-5/S5-6） |
| P1 总数 | 2（S4-4、S6-3，均 BLOCKED） |
| 入口准则 | `entry_criteria_met=false`（五服务 `/health` 通过；但三真实开关未全开且 OpenLLM 上游不可达） |
| 缺陷归属 | FAIL 9 = F-1(2) + F-2(5) + F-3(2)；BLOCKED 7 = F-1(6) + 禁停约束(1，S5-6) |

来源：`doc/test/evidence/s7/env/env-check.json`（`rechecked_at=2026-09-11T20:45:00+08:00`）。

| 状态 | 数量 | 说明 |
|------|:---:|------|
| READY | 14 | 真实 PG（含业务 schema）/ `openbase_test` / Redis / 本地 IdP 8090 / 四仓运行态 / 网关 8000 / 前端 5173 / Playwright 等 |
| NOT_READY | 0 | `openbase_test` 建库闭环后归零 |
| UNREACHABLE | 2 | Keycloak 8080、nginx `/ui/` |
| BLOCKED | 1 | OpenLLM `jerry.yu` 远端（受限挂起，不阻断段门禁） |

---

> **文档结束**。本单为 S7 段冒烟缺陷（F-1/F-2/F-3）**分派与闭环回填待办**（[Draft] v1.0.0）；所有键名 / 文件路径 / 行号均自实际仓内只读核对得出，每缺陷的验证用例 ID 与 `smoke` 证据逐条对应；**不输出明文密钥 / 口令**；未改动任何代码、未对四仓执行 git 写操作、未将 `dogfood-output/` 纳入提交面。

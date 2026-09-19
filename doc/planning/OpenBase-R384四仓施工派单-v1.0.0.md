# OpenBase-R384四仓施工派单-v1.0.0

| 项 | 内容 |
|------|------|
| 文档编号 | OB-DISPATCH-R384-CROSSREPO-v1.0.0 |
| 文档版本 | v1.3.0 |
| 状态 | [Review] |
| 作者 | PM-OpenBase-Dev / AA-OpenBase-Dev |
| 日期 | 2026-09-16 |
| 存放 | doc/planning/ |
| 接收方 | **DPS / OpenLLM / OpenMemory / OpenRAG 四仓**（各仓独立评审、独立提交、独立发布） |
| 上游依据 | 《OpenBase-D6四仓request_id日志接线改动说明-v1.0.0》（施工依据本体）；**《OpenBase-R384改动包-v1.0.0》（可落地代码，含 D-6 落点更正）**；《OpenBase-R384-四仓日志接入可行性粗筛与D6施工量评估-v1.0.0》；《OpenBase-Phase迭代计划-v1.4.6》§7 Phase 6；《OpenBase-R384四仓日志接入覆盖状态说明-v1.4.6》；《OpenBase-单版本规划文档-v1.4.7》；《OpenBase-技术债务总表》TD-新增-020；《OpenBase-候选需求池》§1.13/§1.14 |
| 性质 | **跨仓施工派单**（分发给四仓对话的作业单）。派单不等于施工：各仓以此为依据走自身评审与发布流程，OpenBase 侧不代改他仓代码 |

---

## 1. 派单范围与目标

| 项 | 内容 |
|----|------|
| 派单事由 | R-384「四仓日志接入日志中心」在 v1.4.6 为**部分交付**：OpenBase 侧 `repo_log` 适配器已交付，四仓侧 `request_id` 接线与 JSONL 结构化**未实施**（Phase 6 门禁未满足，已按降级条款显式声明，登记 TD-新增-020） |
| 本派单覆盖 | BL-146-16（D-6 四仓接线）、BL-146-17（四仓 JSONL 结构化）、BL-146-18（采集命名对齐，主要落 OpenBase 编排器）、BL-146-20（端到端串联验收）、Phase 6 任务 6.0（前置核实三项） |
| 派单目标 | ① 四仓请求日志携带 `request_id`，取值与网关出站头 `X-Request-Id` **完全一致**；② 四仓输出 **JSON Lines** 且可被 OpenBase 适配器解析；③ 日志中心可检索四仓日志；④ 端到端串联验收通过 |
| 不改变 | 接口契约、鉴权语义、既有日志语义（只增字段不删不弱化）、各仓依赖（不新增三方库） |
| 总量 | 4 仓 / 7 个文件 / +38~+67 行；D-6 本体 ≈4.2 人天（含跨仓流程） |

## 2. 四仓基线快照（实测 2026-09-16）

| 仓 | 分支 | HEAD | 目标文件现状（实测） |
|----|------|------|---------------------|
| DPS | `main` | `386378c` | `src/main.py:37-40` `basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")`；`src/identity/request_id.py` 已有 `get_current_request_id()` / `set_current_request_id()`，生成 `req-{12hex}` |
| OpenLLM | `feature/s4-identity-channel-b` | `e2683ce` | `backend/main.py:80-83` `basicConfig(format=settings.LOG_FORMAT)`；`backend/app/core/config.py:180-182` `LOG_LEVEL="INFO"` / `LOG_FORMAT` 默认值**不含** `request_id` |
| OpenMemory | `release/v7.3.0` | `019ce6b` | `src/openmemory/api/middleware/structured_log.py:26` `logger = logging.getLogger(__name__)`（标准 logger，`extra` 被根 formatter 丢弃）；`:31` `request_id_ctx`；`src/openmemory/utils/struct_logger.py:65` 同组 ContextVar 再声明、`:329` `get_logger()` |
| OpenRAG | `release/v1.10.0` | `cc16567` | `src/openrag/main.py:96-177` 已注册 CORS / TraceContext / RoleGate / BlockSubjectGate / IdentityGate / APIKey / Prometheus，**未注册 `LoggingMiddleware`**；`src/openrag/observability/logging.py:390` `LoggingMiddleware` 定义存在，`__call__:415-428` 仅处理 `X-Correlation-ID`/`X-Trace-ID`/`X-Span-ID` |

> 基线为只读实测（未对四仓执行任何 git 写操作）。各仓施工前请以**自身 HEAD** 复核本表。

### 2.1 启动路径实测（**关键：决定改动落点**，2026-09-16 依据 OpenBase 编排器实测）

| 仓 | 编排器实际启动命令 | 日志配置现状 | **D-6 原落点是否生效** | **修正落点** |
|----|------------------|-------------|:--------------------:|-------------|
| **DPS** | `python -m uvicorn rest_api.app:app --app-dir src` | `src/rest_api/app.py:40` 仅 `logger = logging.getLogger(__name__)`，**无日志配置** | ❌ **不生效**（`src/main.py:37-40` 的 `basicConfig` 不被执行） | **`src/rest_api/app.py`**（+ 抽 `src/logging_setup.py` 供 `main.py` 共用） |
| **OpenLLM** | `python -m uvicorn main:app`（cwd=`backend`） | `backend/main.py:80-83` `basicConfig(format=settings.LOG_FORMAT)` | ✅ 生效 | 不变 |
| **OpenMemory** | `python scripts\start_openmemory.py`（→ `create_app()`） | `src/openmemory/api/server.py:788` 的 `basicConfig` **在 `main()` 内** | ❌ **不生效** | **`src/openmemory/api/server.py`（模块级或 `create_app()`）** + `structured_log.py` 门面改造 |
| **OpenRAG** | `python -m uvicorn openrag.main:app --app-dir src` | `src/openrag/main.py:51` `setup_logging(json_format=settings.is_production)`（lifespan 内） | ✅ 生效 | 不变；另需 `json_format=True`（采集环境）方为 JSONL |

> **施工前必读**：DPS 与 OpenMemory 若按 D-6 原落点实施，**改动不会生效**。已按修正落点给出可落地改动，见《OpenBase-R384改动包-v1.0.0》。

### 2.2 勘误（P1）：`RequestIdFilter` 必须挂 **handler**，不可挂 root logger

> 2026-09-19 追加（源自四仓实施反馈）。**OpenLLM / OpenMemory / OpenRAG 三仓独立复现并各自修正**；DPS 按 §4.1 原样实现后由 OpenBase 侧独立探针复现并修正。**后续任何仓引用本派单 §5/§6 或《改动包》§2 的 `configure_logging` 代码，一律以下方修正版为准。**

**问题**：§5/§6 的通用件把 `RequestIdFilter` 加在 **root logger**（`logging.getLogger().addFilter(...)`）。CPython `logging` 语义为：**logger 级 filter 只对「自该 logger 发起」的记录生效**；子 logger 记录向祖先传播时**只执行祖先的 handler，不执行祖先的 filter**。四仓业务代码普遍使用 `logging.getLogger(__name__)`（子 logger），故原样实现会让这些记录的 `request_id` 恒为 `-`（即便请求上下文存在）→ 验收①「请求日志携带 request_id」对**应用日志**不可达。

**独立复现证据**（OpenBase 侧探针，针对 DPS 修正前版本）：

```text
子 logger（middleware.audit_middleware）→ "request_id": "-"
root 直发（logging.getLogger().info）  → "request_id": "req-abc123456789"
```

**修正**：filter 挂到**托管 handler** 上——所有经该 handler 输出的记录（无论源自哪个 logger）均被注入。

```python
    handler = logging.StreamHandler()                    # 默认 stderr
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter(get_request_id))   # ← 挂在 handler，不是 root logger
    logger.addHandler(handler)
```

**附带修正（幂等语义）**：重复调用时**不重复添加 handler**，但须把 filter 重整为**本次**传入的取值函数，避免首个调用方的 getter 被永久固化（DPS 实测：前序调用传入 `lambda: None` 会使后续注入失效）。

**四仓落实状态（各仓实现差异均视为等效合规）**：

| 仓 | 注入机制 | 落实状态 |
|----|---------|---------|
| DPS | handler 级 filter | ✅ 已修正（2026-09-19，OpenBase 侧；专项单测 9 → **10 passed**，含 P1 回归护栏；独立探针复测通过）。另保留"已显式携带 `request_id` 不被覆盖"适配（`BaseHTTPMiddleware` 子 task 下 contextvar 不可见） |
| OpenLLM | handler 级 filter | ✅ 仓内已修正（回执记录 4 处偏离，含清理既有 root handler 防双写、`ensure_ascii=True`） |
| OpenMemory | handler 级 filter | ✅ 仓内已修正（另含接管 `basicConfig` 遗留 handler、`_revive_app_loggers` 复启被 alembic `fileConfig` 停用的 logger） |
| OpenRAG | structlog `contextvars.bind_contextvars` | ✅ 结构性正确，无需 filter（`merge_contextvars` 自动合入每条日志） |

## 3. Phase 6 任务 6.0 前置核实派单（跨仓开工前必做）

| # | 核实项 | 核实方法（可执行） | 判据 / 产出 | 本派单实测提示 |
|:-:|-------|-------------------|------------|---------------|
| 1 | **OpenMemory 实际启动路径与根 logger** | 用真实启动脚本起服务（`scripts/start_openmemory.py`）→ 访问任一接口 → 检查采集文件或 stderr 是否出现**应用级日志行**（非 uvicorn 自身行）；并 `grep -n basicConfig` 定位其所在函数 | 若应用 INFO 日志缺失 → 证实 `basicConfig` 未生效，需移出 `main()`；产出「启动路径 + 日志配置位置」结论 | 已实测：`src/openmemory/api/server.py:782` 的 `main()` 内才有 `basicConfig`；而 `scripts/start_openmemory.py:162,239-241` 走 `create_app(...)` + `uvicorn.Server(...)`，**不经过 `main()`** → 倾向"未配置"，待实跑确认 |
| 2 | **OpenRAG 两套日志栈统一方案** | 核对 `observability/logging.py` 与 `config/logging.py` 的 `get_logger` 来源、`set_correlation_id` 定义来源是否同一对象；确认 `setup_logging` 的调用点与传参 | 产出「统一为哪一套」的定论 + contextvar 单一来源确认 | 已实测：`observability/logging.py:410` 的 `self.logger = get_logger("openrag.api")` 与 `config/logging.py:71` 的 `get_logger` **同源**（structlog 门面），kwargs 调用风格成立，注册**不会**报错 → D-6 R-3 风险由"两套栈并存"降级为"确认 contextvar 单一来源" |
| 3 | **四仓受信来源判定口径对齐** | 逐仓列出既有"受信代理来源"判定实现位置（对标 OpenBase 侧 `TRUSTED_PROXY_SOURCES`），并确认其用于 `X-Request-Id` 透传判定的可行性 | 产出四仓各自的实现位置 + "受信=透传 / 非受信=重生成"两分支单测方案 | D-6 R-6：各仓沿用自身既有校验实现，口径以 OpenBase 协议头规范为准 |

| 4 | **各仓启动路径与日志配置生效点**（决定改动落在哪个文件） | 对照 §2.1 实测表，在各仓内确认：① 生产/编排启动命令；② 该路径下日志配置是否执行（打印一条应用 INFO 日志并观察采集文件/控制台） | 产出「实际生效的日志配置位置」结论；若与 §2.1 不一致，须先更正落点再施工 | ⚠️ **本派单已实测**：DPS 实走 `rest_api.app:app`（`main.py` 配置不生效）、OpenMemory 实走启动脚本（`main()` 的 `basicConfig` 不生效）→ 两仓落点已更正，见 §2.1 |

> **门禁**：上述四项未产出结论前，不得开始 6.1/6.2 的跨仓代码改动。

## 4. 统一契约（四仓一致，强制）

| 项 | 约定 |
|----|------|
| 头名 | `X-Request-Id` |
| 取值语义 | **受信来源透传复用**；**非受信来源携带则忽略并本地重新生成** `req-{12hex}`（防伪造串联） |
| 日志字段名 | 统一 `request_id`（JSON key 与 format 占位符同名） |
| 兜底 | 无上下文路径（豁免/健康检查/非请求上下文）**一律输出 `"-"`**，禁止 `KeyError` |
| 输出流 | 维持现状（DPS/OpenLLM/OpenMemory → stderr；OpenRAG → stdout），不得改为仅落自有文件 |
| 级别 | 沿用各仓现有级别开关，不新增 |
| 禁止 | 不记录令牌/密码/密钥/完整请求体；沿用各仓既有脱敏逻辑 |
| 采集目录名 | **锁定** `logs/<svc>/`，svc 取值 `dps` / `openllm` / `openmemory` / `openrag`，**不得改名**（OpenBase 侧按目录名映射 `module`） |

## 5. 统一 JSONL 契约（对齐 OpenBase `RepoLogAdapter` 实测口径）

> 以下字段名为 **OpenBase 侧适配器实际读取的键**（`openbase/modules/logs/repository.py::RepoLogAdapter._parse_line`，含别名）。四仓按此输出即可被解析；**字段超集允许**，多余字段忽略。

| 字段 | 必需 | 类型 | 适配器读取键（含别名） | 说明 |
|------|:---:|------|----------------------|------|
| `ts` | **必需** | ISO 8601 字符串 | `ts` / `timestamp` / `time` | `Z` 允许；无时区视为 UTC。**无法解析时间戳的行会被整行丢弃**（DEF-BE-146-001 修复后的既定口径） |
| `request_id` | **必需** | 字符串 | `request_id` / `requestId` / `trace_id` | R-384 核心；须与网关出站头完全一致 |
| `method` | 必需 | 字符串 | `method` | 缺失则四维分类"操作类型"退化 |
| `path` | 必需 | 字符串 | `path` / `url` | 用于操作类型派生 |
| `status_code` | 必需 | **JSON 数字** | `status` / `status_code` | **必须为数字**：字符串 `"200"` 不会被采纳（`isinstance(status, int)` 判定），会导致"结果"维度落 `unknown` |
| `duration_ms` | 建议 | 数字 | `duration` / `duration_ms` | 数字可，数字字符串经 `int()` 容错 |
| `level` | 建议 | 字符串 | `level` | 归入 `summary`（**服务端会脱敏**） |
| `operator_id` | 建议 | 字符串 | `operator_id` / `operator` | 四维分类"操作人"来源 |
| `tenant_id` / `ip` / `case_id` / `step_id` / `run_id` / `action` | 可选 | 字符串 | `tenant_id`；`ip`/`ip_address`；`case_id`；`step_id`；`run_id`；`action` | 有则更完整 |
| `service` / `message` / `event` | 可选 | 字符串 | 同名 | 归入 `summary`（**服务端脱敏**，勿放敏感值） |
| `module` | **不需要** | — | — | 由采集目录名 `svc` 显式映射（`dps→dps`、`openrag→rag`、`openmemory→memory`、`openllm→llm`），四仓**无需输出** |

**示例行（单行，UTF-8）**：

```json
{"ts":"2026-09-16T12:34:56.789Z","level":"INFO","service":"openrag","request_id":"req-abc123456789","method":"POST","path":"/api/v1/query","status_code":200,"duration_ms":42,"operator_id":"u-1001"}
```

**文件命名与切片契约**：

| 项 | 约定 |
|----|------|
| 文件名 | `<svc>-YYYYMMDD.jsonl`（适配器白名单实际接受 `.jsonl` 与 `.log`，并容许 `-HHmmss` 与 `.err` 变体） |
| 当前偏差 | OpenRAG 采集文件名仍为 `openrag-YYYYMMDD-HHMMSS.log`（**启动时间戳**，未按日切分）——由 BL-146-18 在 OpenBase 编排器侧统一，OpenRAG 无需自改 |
| 扫描上限 | 适配器默认窗口 **2 天**、单次 **200,000 行/源**（按目标 svc 目录独立计算）→ 若单日行数接近上限，须评估按级别采样 |
| 行格式 | **每行一个 JSON 对象**，行首为 `{`、行尾为 `}`（适配器以此判定 JSON 行）；非 JSON 行走纯文本回退解析（能力受限） |

## 6. 逐仓施工单

### 6.1 DPS（改动量最小：+10 / -1 行）

| 项 | 内容 |
|----|------|
| 改动文件 | **`src/rest_api/app.py`**（实际生效落点，`:40` 处插入装配）；新增 `src/logging_setup.py`（通用件）；`src/main.py` 同步改为调用同一装配函数（开发模式一致性） |
| 落点更正说明 | **D-6 §3.1 原落点 `src/main.py` 在本仓实际启动路径下不生效**（编排器实启 `rest_api.app:app`）——详见 §2.1 与《改动包》§1 |
| 改动 1 | 在 `logging.basicConfig` **之前**引入 `from identity.request_id import get_current_request_id` |
| 改动 2 | 新增 `RequestIdFilter(logging.Filter)`：`record.request_id = get_current_request_id() or "-"` |
| 改动 3 | `format` 改为 `"%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s"`，并在 `basicConfig` 之后 `logging.getLogger().addFilter(RequestIdFilter())` |
| 关键注意 | ① 必须 `addFilter` 挂到 **root logger**（`basicConfig` 只建 handler）；② 豁免路径不写 contextvar → 由 `"-"` 兜底，**不要**让 `record.request_id` 缺省不设，否则 format 抛 `KeyError` |
| JSONL（BL-146-17） | 同一文件内将 formatter 或 handler 切换为 JSON Lines 输出（字段见 §5）；**输出流保持 stderr** |
| 新增单测 | `src/tests/test_r384_request_id_filter.py`：有 contextvar / 无 contextvar 两分支 + JSONL 行可解析 |
| 回归命令 | `python -m pytest src/tests -p no:randomly`；`python -m ruff check src`；`python scripts/k07_endpoint_matrix.py --check`；`python scripts/smoke_l3_2.py --quick` |
| 风险 | format 变更影响**所有**日志行（既有人工 `grep` 习惯）→ 在运行手册登记新格式样例 |

### 6.2 OpenLLM（+10 / -2 行）

| 项 | 内容 |
|----|------|
| 改动文件 | `backend/main.py`（`basicConfig` 位于 `:80-83`）、`backend/app/core/config.py`（`LOG_FORMAT` 默认值 `:181-182`） |
| 改动 | 同 DPS 的 `RequestIdFilter` + root `addFilter`；`LOG_FORMAT` 默认值改为 `"%(asctime)s - [%(request_id)s] - %(name)s - %(levelname)s - %(message)s"` |
| 关键注意 | `LOG_FORMAT` 是**配置项**：若部署侧环境变量已显式设置旧格式，新字段不会显示 → **两侧必须同步**（部署配置与代码默认值） |
| JSONL | 同 §5 契约输出 JSON Lines；`request_id` 可复用既有 `app/identity/audit_identity.py::identity_log_extra()` 已产出的 `request_id`（当前只进审计库） |
| 新增单测 | `backend/tests/unit/test_r384_request_id_filter.py`（两分支 + format 渲染含 `-` 兜底） |
| 回归命令 | `python -B -m pytest tests/unit -p no:cacheprovider`；`python -m ruff check app scripts tests/unit`；`python scripts/k07_endpoint_matrix.py --verify`；`python scripts/verify-env/verify_env.py --fail-fast`；`python scripts/smoke_l3_2.py` |
| 提交纪律 | 本仓工作区现存大量未入库残留（含**敏感文件** `backend/.env.shared-infra`、`data/edge_tokens.jsonl`，以及 336 项历史误入库 `.pyc` 变更）→ **禁止 `git add -A`**，只 add 本派单涉及文件 |

### 6.3 OpenMemory（改动量最小，但有循环导入风险）

| 项 | 内容 |
|----|------|
| 改动文件 | `src/openmemory/api/middleware/structured_log.py`（`logger` 位于 `:26`，`request_id_ctx` 位于 `:31`）；视核实结果可能涉及 `src/openmemory/api/server.py` |
| 改动（方案 A，推荐） | 删除模块级 `logger = logging.getLogger(__name__)`，改为**延迟导入**结构化门面：函数内 `from openmemory.utils.struct_logger import get_logger` 后取 `get_logger(__name__)`；调用点由 `extra={"structured": log_entry}` 调整为该门面的 kwargs 形式 |
| 实施前必查（不得凭猜） | `utils/struct_logger.py::StructLogger._log()` 对 kwargs 的处理方式（是否注入 `extra`、是否与 `extra["structured"]` 合并）——据此决定调用点写法 |
| 改动（方案 B，备选） | 在启动路径用 `dictConfig` 给根 logger 装载 JSON formatter（改变**全部**日志格式，影响面大） |
| 前置核实强关联 | 6.0 核实项①：`api/server.py:782 main()` 内的 `basicConfig` 在 `scripts/start_openmemory.py` 启动路径下**不执行** → 需把日志配置移到模块级或 `create_app()` 内，否则应用日志无法进入采集流（这是本仓能否达成的**关键前提**） |
| 新增单测 | 导入顺序单测（避免 `struct_logger` ↔ 中间件循环依赖）+ `request_id` 出现在结构化行中 |
| 回归命令 | `python -m pytest`（按本仓 `pyproject.toml [tool.pytest.ini_options]` 配置执行）+ `ruff`（以本仓既有命令为准，施工前请复核并登记实际命令） |
| 风险 | 中（循环导入；`StructLogger` kwargs 形态；启动路径） |

### 6.4 OpenRAG（改动最大：需启用一个从未注册的中间件）

| 项 | 内容 |
|----|------|
| 改动文件 | `src/openrag/main.py`（注册段 `:96-177`）、`src/openrag/observability/logging.py`（`LoggingMiddleware` `:390`，`__call__` `:412-428`）；可选 `src/openrag/config/logging.py` |
| 改动 1（注册） | 在 **Prometheus 之后**按既有 `try/except ImportError` 风格注册：`app.add_middleware(LoggingMiddleware, service_name="openrag")`（后注册者位于外层，可覆盖全部请求） |
| 改动 2（受信透传） | 在 `__call__` 的 `X-Correlation-ID` 处理之后并列补 `X-Request-Id`：受信来源 → `set_request_id(rid)` 透传复用；非受信携带 → 忽略并本地重新生成 `req-{12hex}` |
| 改动 3（JSONL） | 实测实际生效栈为 `src/openrag/config/logging.py::setup_logging`（structlog：`TimeStamper(fmt="iso")` 输出键为 **`timestamp`**，`json_format=True` 时用 `JSONRenderer`）。采集环境下以 `json_format=True` 输出 JSON Lines；**输出流保持 stdout** |
| 实测降险结论 | `LoggingMiddleware.logger` 取自 `get_logger("openrag.api")`（structlog 门面），其 `logger.info("request_started", method=..., ...)` kwargs 风格**成立**，注册不会报错；`config/logging.py` 的文本 handler `logging.Formatter("%(message)s")` 与 structlog 属同一栈 → **不存在"两套栈重复输出"**（D-6 R-3 降级） |
| 需并行核实 | `api/middleware/trace.py::TraceContextMiddleware` 已注册且**不处理 `X-Request-Id`**（实测无匹配），与本改动不冲突；但须确认其 correlation-id contextvar 与 `observability/logging.py` 的 `set_correlation_id` 是否同一对象（6.0 核实项②） |
| 新增单测 | `tests/unit/test_r384_request_id.py`：受信透传 / 非受信忽略重生成两分支（可参照本仓 `tests/unit/test_s3_t7_audit_identity.py` 的 request_id 用例范式） |
| 回归命令 | `python run_tests.py`；`python -B -m pytest tests/unit -p no:cacheprovider`；`python -m ruff check src scripts tests/unit`；四静态扫描（`scan_no_edgerouter_assembly` / `scan_no_identity_header_bypass` / `scan_tenant_scope` / `scan_auto_purge`）；`python scripts/k07_endpoint_matrix.py`；`python scripts/smoke_l3_2.py`；`python scripts/verify_env_contract.py --fail-fast` |
| 风险 | 中（启用中间件后日志量上升 → 保持 `log_request_body=False` / `log_response_body=False` 默认；必要时按级别采样） |

## 7. 采集侧施工单（BL-146-18 / v1.4.7 BL-147-04，OpenBase 编排器）

| 项 | 内容 |
|----|------|
| 归属 | OpenBase 侧（本仓），不在四仓派单范围 |
| 内容 | 编排器输出命名对齐 `{svc}-YYYYMMDD.jsonl`；扩展名随四仓结构化切换为 `.jsonl` |
| 当前状态 | **✅ 已实施（2026-09-19，v1.4.7 / BL-147-04）** |
| 落地口径 | ① **结构化流**采集文件改用 `.jsonl`：stdout 结构化（OpenRAG）→ `{svc}-YYYYMMDD.jsonl`；stderr 结构化（DPS / OpenLLM / OpenMemory）→ `{svc}-YYYYMMDD.err.jsonl`；非结构化流保持 `.log` / `.err.log`；② **归档命名缺陷修复**：同日重复启动归档由 `{svc}-YYYYMMDD.err-HHmmss.log` 改为 `{svc}-YYYYMMDD-HHmmss.err.log`（时间戳须在 `.err` **之前**，否则不匹配适配器白名单 `REPO_LOG_NAME_RE`、日志中心按目录扫描会漏读）；③ 命名单点抽为 `Get-ServiceLogFileName` / `Get-ServiceLogArchiveName`；④ 新增 `-Action namecheck` 命名实测动作（编排器命名校验 + 在盘扫描 + 临时目录归档自检） |
| 校验判据 | `openbase/modules/logs/repository.py::REPO_LOG_NAME_RE`（唯一判据，禁止他处复刻正则）；实测证据 `doc/test/evidence/v147/step3-namecheck-20260919.txt` |
| 余项（待人工裁定） | 四仓结构化流中仍混有 **uvicorn 自身访问日志**（纯文本）→ 采集文件非严格 100% 合法 JSON。「严格全 JSON」需**四仓侧**统一 uvicorn 日志配置（或关闭 access log），属跨仓余项；见《OpenBase-DevLogReport-v1.4.7》§5 |

## 8. 验收判据（四仓统一）

| 类别 | 标准 | 判定方式 |
|------|------|---------|
| **串联一致性** | 同一请求在网关日志与子系统日志中的 `request_id` **完全一致** | 取响应头 `X-Request-Id`，两侧 grep 比对 |
| **JSONL 可解析** | 采集文件每行为合法 JSON 对象，含 §5 必需字段，`status_code` 为数字 | 逐行 `json.loads` + 字段断言；OpenBase 侧以 `source=repo_log` 检索命中 |
| **兜底健壮** | 无上下文/豁免/健康检查路径不抛 `KeyError`，输出 `"-"` | 单测 + 匿名请求实测 |
| **输出流不变** | 日志仍写原 stdout/stderr（可被编排器捕获） | 重定向验证 |
| **回归** | 各仓既有测试全通过 | 各仓回归命令（见 §6） |
| **覆盖率** | 新增代码满足各仓自身覆盖率要求 | 各仓覆盖率报告 |
| **安全** | 不新增敏感字段输出（token/密码/完整请求体） | 单测 + 日志扫描 |

**端到端验证方法（任选一仓先做）**：

```powershell
# 1) 取网关 request_id（响应头回传）
$resp = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/dps-proxy/reports/overview' `
  -Headers @{ Authorization = "Bearer $env:OPENBASE_ACCESS_TOKEN" }
$rid = $resp.Headers['X-Request-Id']

# 2) 在子系统采集日志中按同一 request_id 检索（结构化后为 .jsonl）
Select-String -Path 'logs/dps/*.jsonl' -Pattern $rid

# 3) 反向校验：伪造头（非受信来源）应生成新的 req-{12hex}
```

**通过判据**：步骤 2 命中该 `request_id`，且命中行的 `status_code` / `duration_ms` 与该次请求实际结果一致。

## 9. 提交与回执要求（各仓）

| 项 | 要求 |
|----|------|
| 分支 | 各仓自定（建议在各自发布分支上作业；OpenLLM 当前为 `feature/s4-identity-channel-b`，OpenMemory 为 `release/v7.3.0`，OpenRAG 为 `release/v1.10.0`，DPS 为 `main`） |
| 提交粒度 | 建议批 A（`request_id` 接线）与批 B（JSONL 结构化）**分两批**，或经四仓同意后**合并同批**（省一轮跨仓评审/提交/回归 ≈8h） |
| 提交信息模板 | `feat(logging): R-384/BL-146-16 四仓 request_id 日志接线 + JSONL 结构化（依据 OpenBase-D6 说明）` |
| 提交纪律 | **禁止 `git add -A`**；只 add 本派单涉及文件；提交前复核暂存区无敏感文件（`.env*` / 令牌样本） |
| 回执内容 | ① 批 A / 批 B 的 commit hash；② 回归命令与通过数；③ 新增单测证据（含两分支）；④ 覆盖状态确认（是否达到 §8 全部判据） |
| hash 回填 | 回执后由 OpenBase 侧回填至《技术债务总表》TD-新增-020 与本派单 §10 |

### 9.1 hash 回填位

| 仓 | 批 A（`request_id` 接线） | 批 B（JSONL 结构化） | 回归结论 | 回填日期 |
|----|--------------------------|---------------------|---------|---------|
| DPS | `145d858`（A+B 合并同批） | `145d858`（同批） | 专项单测 **10 passed**（OpenBase 侧独立复跑，P1 修正后；修正前 9）；仓内全量回归见《覆盖状态说明》§2.0（含 A/B 归因） | 2026-09-19 |
| OpenLLM | `0c44c26`（A+B 合并同批） | `0c44c26`（同批） | 专项单测 **7 passed**（独立复跑）；仓内全量 **2643 passed / 6 failed**（非本批变更面） | 2026-09-19 |
| OpenMemory | `6d18e49`（A+B 合并同批） | `6d18e49`（同批） | 专项单测 **12 passed**（独立复跑）；仓内全量 **1431 passed / 36 skipped** | 2026-09-19 |
| OpenRAG | `390f5dd`（A+B 合并同批） | `390f5dd`（同批） | 专项单测 **7 passed**（独立复跑） | 2026-09-19 |

> 逐仓文档提交：DPS `75bb420`、OpenLLM `13eeccd`、OpenMemory `0613fef`、OpenRAG `a005a87` / `f134d2f`（见《R384派单分发清单》§3）。
> **待办**：DPS 的 P1 修正（filter 挂 handler）**尚在工作树未提交**，该仓提交后须回填本表与其代码 commit。

## 10. 风险与未决项

| # | 风险/未决 | 级别 | 应对 |
|:-:|----------|:----:|------|
| 1 | **跨仓排期不可控**（四仓各有版本节奏，本仓无法单方推进） | **高** | 各仓独立评审；以本派单为施工依据；开放问题由各仓对话上报本仓决策 |
| 2 | OpenMemory 启动路径导致**日志配置未生效**（6.0 核实项①） | 中·高 | 施工前必做核实；必要时把配置移至模块级/`create_app()` |
| 3 | OpenMemory 循环导入（`struct_logger` ↔ 中间件） | 中 | 延迟导入（函数内 import）+ 导入顺序单测 |
| 4 | OpenRAG 启用中间件后日志量上升 | 中 | 保持 body 记录默认关闭；必要时按级别采样 |
| 5 | DPS / OpenLLM format 变更影响既有人工 grep 习惯 | 低 | 各仓运行手册登记新格式样例 |
| 6 | 四仓日志含敏感字段（token 等） | 中 | 沿用各仓既有脱敏 + 日志扫描单测；OpenBase 侧另做服务端脱敏兜底 |
| 7 | 受信来源判定口径各仓不一 | 中 | 以 OpenBase 协议头规范为准；各仓沿用自身既有校验实现（6.0 核实项③） |
| 8 | `status_code` 输出为字符串导致"结果"维度落 `unknown` | 中 | 按 §5 契约强制输出 **JSON 数字**；纳入 JSONL 可解析判据 |
| 9 | 单日行数接近适配器上限（200,000 行/源） | 低 | 施工后按生产 QPS 重估；必要时按级别采样 |

## 11. 施工时序与依赖

```text
6.0 前置核实（三项结论产出）         ← 跨仓开工门禁
  ↓
批 A：四仓 request_id 接线（BL-146-16）  ← 价值自足（可串联排查）
  ↓（建议与批 A 合并同批以省流程）
批 B：四仓 JSONL 结构化（BL-146-17）
  ↓
BL-146-18 采集命名对齐（OpenBase 编排器，可与批 A/B 并行）
  ↓
BL-146-20 端到端串联验收（四仓 + 本仓回归）
  ↓
OpenBase 侧回填 hash 与技术债务总表；TD-新增-020 状态更新
```

## 12. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-16 | PM-OpenBase-Dev / AA-OpenBase-Dev | 初始创建：R-384 四仓施工派单。含四仓基线快照（实测 HEAD）、6.0 前置核实三项（附实测提示——OpenMemory 启动路径与 OpenRAG 日志栈统一已取得关键证据）、统一契约与 **JSONL 字段契约（按 OpenBase 适配器实测读取键逐项对齐）**、逐仓施工单（文件/改动/单测/回归/风险）、采集侧派单、验收判据与端到端验证方法、提交回执与 hash 回填位、9 项风险与施工时序 |
| v1.1.0 | 2026-09-16 | AA-OpenBase-Dev | **新增 §2.1 启动路径实测表并更正两处改动落点**（依据 OpenBase 编排器 `scripts/service-orchestrator.ps1` 实测命令）：① **DPS** 实走 `rest_api.app:app`，D-6 原落点 `src/main.py` 的 `basicConfig` **不生效** → 落点更正为 `src/rest_api/app.py`（+ 抽 `src/logging_setup.py` 双入口共用）；② **OpenMemory** 实走 `scripts\start_openmemory.py` → `create_app()`，`api/server.py:788 main()` 内的 `basicConfig` **不生效** → 落点更正为 `src/openmemory/api/server.py`（模块级或 `create_app()`）；③ OpenLLM / OpenRAG 落点确认有效。同步：§3 核实项新增 **④ 各仓启动路径与日志配置生效点**、门禁表述由三项改为四项；上游依据增列《OpenBase-R384改动包-v1.0.0》（可落地代码）。文件内版本 v1.1.0，文件名沿用 -v1.0.0（与项目既有 D-6 说明同例） |
| v1.2.0 | 2026-09-19 | AA-OpenBase-Dev | **新增 §2.2 勘误（P1）：`RequestIdFilter` 必须挂 handler、不可挂 root logger**——§5/§6 通用件原将 filter 加在 root logger，而 CPython 语义下祖先 logger 的 filter 不参与子 logger 记录传播，致 `logging.getLogger(__name__)`（四仓普遍）记录 `request_id` 恒为 `-`、验收①对应用日志不可达。含独立复现证据（DPS 修正前：子 logger `-` / root 直发正确）、修正代码、幂等语义附带修正（filter 须重整为本次 getter）、四仓落实状态表（OpenLLM/OpenMemory/OpenRAG 仓内独立修正，DPS 由 OpenBase 侧修正并加 P1 回归护栏）。**后续引用一律以修正版为准** |
| v1.3.0 | 2026-09-19 | AD-OpenBase-Dev | **§7 采集侧施工单置「已实施」（v1.4.7 / BL-147-04）**：补落地口径（结构化流 `.jsonl` 命名规则／归档命名缺陷修复〔时间戳须在 `.err` 之前〕／命名单点抽取／`-Action namecheck`）与校验判据（`REPO_LOG_NAME_RE`）+ 实测证据路径；新增「余项（待人工裁定）——uvicorn 访问日志非结构化」；**§9.1 hash 回填位回填四仓 commit 与回归结论**（DPS `145d858`/OpenLLM `0c44c26`/OpenMemory `6d18e49`/OpenRAG `390f5dd`，并标注 DPS P1 修正待入库） |

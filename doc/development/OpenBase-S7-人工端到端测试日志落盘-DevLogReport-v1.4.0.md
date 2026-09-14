# OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.4.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S7-DEVLOG-LOGS-v1.4.0 |
| 版本 | v1.4.0 |
| 状态 | [Review]（批 5（专用代理族上游专段接线）开发记录：批 4 §14#2 遗留项关闭；沙箱可执行面已完成并留证，未执行项显式登记为 PENDING，禁伪造） |
| 日期 | 2026-09-14 |
| 作者 | AI（S7 批 5 开发会话：TDD 实现、实跑验证与证据归档） |
| 版本主题 | **批 5 专用代理族上游专段接线（批 4 §14#2 收尾）**——①`upstream_observe.publish_upstream_response()` 一行式统一出口（**采集开关与脱敏唯一读取点**）；②`UPSTREAM_SYSTEM_*` 常量（与通用通道路由键逐字对齐）；③`content_type_of()` 共用读取口径（消除四处重复）；④四族非流式出口接线（`dps_proxy._forward` / `llm_proxy._forward` / `rag_proxy._forward` + `_forward_multipart` / `memory_proxy._forward` + `_forward_raw`）；⑤流式端点头部级专段（`rag_proxy._forward_sse` / `llm_proxy._forward_sse`）；⑥通用代理通道收敛到同一出口；⑦**实施期缺陷修复 AD-20260914-01**。含逐项改动清单、RED→GREEN 如实记录、静态质量检查、单测与覆盖率证据、代码逻辑审查、追溯矩阵、变更统计、测试/开发审计移交与遗留说明 |
| 上游依据 | ①《OpenBase-人工端到端测试日志记录方案-v1.0.0.md》（OB-DESIGN-MANUAL-E2E-LOG-v1.0.0，内部 **v1.5.0 [Approved]**，§5 批 5（专用代理族接线）/§5 批 4 C-16/§11 响应级观测与错误归因（含 D-5 红线）/§6 验收）；②批 1《...DevLogReport-v1.1.0》（归档）；③批 2《...DevLogReport-v1.2.0》（归档）；④批 4《...DevLogReport-v1.3.0》（归档，§14#2 提出本批范围）；⑤`AGENTS.md`（分层架构、错误码、日志、命名、测试规则）；⑥`observability-standards`（结构化日志与三大支柱） |
| 适用范围 | **提交面仅 OpenBase 主仓**：`openbase/**`、`tests/**`、`doc/**`；**不改动 DPS/OpenLLM/OpenMemory/OpenRAG 四仓任何文件**；**不纳入 `dogfood-output/`** |
| 证据面 | 单测证据：`doc/test/evidence/manual/batch5-unit-junit.xml`（**14 例 / 0 失败**）；定向回归：`doc/test/evidence/manual/batch5-proxy-regression-junit.xml`（**121 例 / 0 失败**，含 `upstream_observe` 覆盖率 **100%**）；全量回归：`doc/test/evidence/manual/batch5-full-regression-junit.xml`（**824 例 / 4 失败 / 0 错误 / 4 跳过**）+ 抖动复核 `batch5-pg-flake-recheck-junit.xml`（**10 例 / 0 失败**）；静态质量：`ruff check openbase tests` **All checks passed（0 错）** |
| 纪律 | 结论如实；未执行项一律 PENDING，禁伪造 hash、响应码与通过；**RED 复现与过程中失败逐项如实登记**（见 §6.1、§9） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-14 | AI（S7 批次 36 批 1 里程碑） | 批 1 里程碑（C-1 日志落盘 + C-6 服务日志采集）开发记录（已归档） |
| v1.1.0 | 2026-09-14 | AI（S7 批次 37 批 1 全量落地） | 批 1（C-1~C-9）全量落地（已归档） |
| v1.2.0 | 2026-09-14 | AI（S7 批 2 开发会话） | 批 2（C-10~C-12）人工结论记录入口落地（已归档） |
| v1.3.0 | 2026-09-14 | AI（S7 批 4 开发会话） | 批 4（C-15~C-19）响应级观测与错误归因落地（已归档） |
| v1.4.0 | 2026-09-14 | AI（S7 批 5 开发会话） | **批 5（专用代理族上游专段接线，批 4 §14#2 收尾）实施落地**：新增 §16 批 5 实施记录（统一出口 / 四族非流式出口接线 / 流式头部级专段 / 通用通道收敛 / 缺陷修复），同步更新 §1 目标与范围、§3 任务清单、§5 静态质量、§6 测试与覆盖、§7 实跑、§8 代码逻辑审查、§9 问题修复、§10 追溯矩阵、§11 变更统计、§12/§13 移交材料与 §14 遗留。设计依据升至方案 **v1.5.0**。旧版 v1.3.0 按版本管理流程移入 `doc/development/archive/`（只读）。 |

---

## §1 范围与目标

- **本报告**为《OpenBase-人工端到端测试日志记录方案》**批 5（专用代理族上游专段接线）**的开发环节交付物，落点 `doc/development/`，状态 [Review]。
- **批 5 的由来（批 4 §14#2 遗留）**：批 4 的 C-16 上游专段仅落在通用代理 `openbase/modules/proxy/_forward`（路径 `/api/v1/proxy/{system}/…`）。但人工 E2E 经**统一前端**访问时实际走的是**专用代理族**（`/api/v1/dps-proxy`、`/api/v1/llm-proxy`、`/api/v1/rag-proxy`、`/api/v1/memory-proxy`），这些通道此前**只有 C-15 网关侧字段**（`resp_*`），**无上游侧字段**（`upstream_*`）→ 「失败出在网关还是上游」在真实人工测试路径上**仍不可判**。
- **目标**：
  1. **出口统一**：所有代理族的转发出口调用**同一个** `publish_upstream_response()`——采集开关（`OPENBASE_CAPTURE_UPSTREAM` + 允许清单）与脱敏（C-18）在该函数内**唯一读取/执行**，各族不得自行判断；
  2. **覆盖补齐**：`dps_proxy._forward`、`llm_proxy._forward`、`rag_proxy._forward` + `_forward_multipart`、`memory_proxy._forward` + `_forward_raw` 六个非流式出口全部补记专段（成功/业务错误/不可达三路径同结构）；
  3. **流式口径明确**：`rag_proxy._forward_sse`、`llm_proxy._forward_sse` 记**头部级专段**（状态/首字节耗时/Content-Type）——2xx 不预读流式体（预读会消费事件流、破坏透传），4xx/5xx 错误体可安全读取故仍产出 `upstream_error_code`；
  4. **标识对齐**：`upstream_system` 取 `UPSTREAM_SYSTEM_*` 常量并与通用代理通道路由键**逐字对齐**（同一上游只有一套标识，否则归因统计被割裂）；
  5. **向后兼容**：`request` 为**可选关键字参数**（缺省 `None` → 仅跳过观测），转发语义零变化。
- **关键设计选择（本批新增能力）**：**「五族同一出口」**——通用代理与四个专用代理族共用 `publish_upstream_response()`，把批 4 的「单一实现点」从「一条路径」升级为「五个代理族、八个转发出口」（含 2 个流式）。红线口径（默认关 / 生产永久关 / 唯一脱敏出口 / 2KB 上限）因此**不需要在四份新代码里重复判断**。
- **非目标**：不改变任何既有字段契约与落库字段集（`UPSTREAM_SEGMENT_FIELDS` / `audit_logs.detail` 白名单不变）；不新增开关、不改采集语义；不推进 D-6 跨仓接线；不引入响应体常开采集。
- **附带修复**：**AD-20260914-01**（见 §9#2）——`dps_proxy._dps_consecutive_failures` 缺模块级初值，导致**上游首次不可达即 `NameError`**（P6 连续失败降级 / 502 语义在真实故障下完全不可用）。该缺陷位于本批接线路径上且此前零用例覆盖，故在本批一并修复并补用例。
- **执行面界定**：本机（Dev 环境，Python 3.10）沙箱可执行面（代码 / 单测 / 静态质量 / 覆盖率 / 定向与全量回归 / TestClient 端到端）**已真实执行并留证**；真实 7 服务在线编排下的人工 E2E 不在本次沙箱面（见 §14）。

---

## §2 开发入场检查

| 项 | 检查内容 | 结论 |
|----|---------|------|
| 设计依据就绪 | 方案内部 v1.5.0 [Approved]，§5「批 5」明确逐文件落点与验收；批 4 §14#2 明确本批范围与原因（需把 `Request` 传入各族 `_forward`） | 通过 |
| 前置批次落地 | 批 1（C-1~C-9）/ 批 2（C-10~C-12）/ 批 4（C-15~C-19）已落地并出 DevLogReport；`upstream_observe` 模块与审计合流通道已存在 | 通过 |
| 红线可落地 | D-5 五条（默认关 / 开启强制脱敏 / 2KB 上限 / 生产永久关 / 开关留痕）均由既有 `capture_options()` 与 `build_upstream_segment` 承载，本批**只扩大调用面、不新增判断点** | 通过 |
| 现状缺口可复现 | 实测：四族 `_forward` 无任何 `upstream_*` 观测调用（`grep` 零命中），与批 4 §14#2 描述一致 | 通过 |
| 环境可用 | `python -m ruff`、`python -m pytest`、`python -m pytest --cov` 可用 | 通过 |
| 不变量预检 | ①T6-1（日志不得自动清理）不受影响（本批不新增清理路径）；②测试头非身份头约束不受影响（本批不触碰身份头常量）；③K03/信任链语义不变（本批不改出站头装配）；④`X-Request-Id` 传递语义不变 | 通过 |
| 既有测试基线 | 定向面（proxy / dps / llm / rag / memory）基线需先取；批 1/批 2/批 4 报告已登记「自选子集任意顺序存在既有顺序污染」与「共享 PG 抖动」 | 已知（见 §6.3） |

---

## §3 实现计划（任务清单）

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| T1 | 统一出口：`publish_upstream_response` + `capture_options` + `content_type_of` + `UPSTREAM_SYSTEM_*` | `openbase/modules/proxy/upstream_observe.py` | 完成（+84 行） |
| T2 | DPS 族接线（`_forward` 两路径 + 12 处调用点）**含缺陷 AD-20260914-01 修复** | `openbase/modules/dps_proxy/__init__.py` | 完成（+48/-5） |
| T3 | OpenLLM 族接线（`_forward` 两路径 + `_forward_sse` + 12 处调用点） | `openbase/modules/llm_proxy/__init__.py` | 完成（+81/-6） |
| T4 | OpenRAG 族接线（`_forward` / `_forward_multipart` / `_forward_sse`；调用点已带 `request`） | `openbase/modules/rag_proxy/__init__.py` | 完成（+76/-3） |
| T5 | OpenMemory 族接线（`_forward` / `_forward_raw` + 7 处调用点） | `openbase/modules/proxy/memory_proxy.py` | 完成（+53/-2） |
| T6 | 通用代理通道收敛到统一出口（删除本地开关读取与 `_upstream_content_type`） | `openbase/modules/proxy/__init__.py` | 完成（+9/-22） |
| T7 | 单测（TDD，先 RED） | `tests/test_specialized_proxy_upstream_observe.py` | 完成（14 例 / 429 行） |
| T8 | 静态质量检查（ruff） | 0 错 | 完成 |
| T9 | 覆盖率与回归（定向 + 全量 + 抖动复核） | 新模块 100%；定向 121 例全绿；全量 824 例 | 完成 |
| T10 | 开发记录与文档版本更新 | 本报告 v1.4.0 + 方案 v1.5.0 + 文档地图索引 v1.0.14 + 旧版归档 | 完成 |

---

## §4 逐项实施记录（RED→GREEN）

> **顺序如实说明**：本批为「**先写测试 → 见 RED（收集期 ImportError）→ 实现 → 多轮修至 GREEN**」，过程中暴露 1 处**既有生产缺陷**（AD-20260914-01）与 3 处用例自身问题，全部逐项登记（§6.1 RED 台账 / §9 问题修复）。

### 4.1 统一出口（`upstream_observe.py`）

| 能力 | 口径 |
|------|------|
| `publish_upstream_response(request, *, system, reached, duration_ms, status_code=None, content_type=None, payload=None, error=None)` | **一行式统一出口**：`request is None` → 直接返回 None（静默跳过，不影响业务）；否则读开关 → `build_upstream_segment` → `publish_upstream_observation`。**各族不得自行读取开关或拼装字段** |
| `capture_options()` | `(capture_upstream_enabled, capture_field_allowlist_list)`——采集开关的**唯一取值来源**；生产环境恒为 `False`（由 `settings` 属性层收敛） |
| `content_type_of(response)` | 上游 `Content-Type` 的防御式读取（缺头/替身响应 → `None`，不抛错）；**由四处重复实现上提为共用口径** |
| `UPSTREAM_SYSTEM_OPENLLM/OPENRAG/OPENMEMORY/DPS` | 上游系统标识常量，取值与通用代理通道 `PROXY_SYSTEMS` 的路由键**逐字一致**（有用例锁定该不变量） |

### 4.2 DPS 族（`dps_proxy/__init__.py`）

- `_forward` 增**可选关键字参数** `request: Request | None = None`；
- 新增 `upstream_start = time.perf_counter()`；异常分支**在既有 WARN 之前**补记 `reached=False` 专段（无 status/digest、含 `upstream_error`），成功路径在 `_adapt_response` 前补记 `reached=True` 专段（status / content-type / digest / 业务错误码）；
- **缺陷修复 AD-20260914-01**：补齐模块级 `_dps_consecutive_failures: int = 0`（原实现仅在异常分支 `global` 自增，全仓无初值 → 首次不可达即 `NameError`）；
- 12 处调用点补 `request=request`（含 4 处单行调用改写为多行，避免超长行）。

### 4.3 OpenLLM 族（`llm_proxy/__init__.py`）

- `_forward` 增 `request` 可选参数 + 两路径补记专段；11 处调用点补 `request=request`；
- `_forward_sse` 增 `request` 可选参数：进入流上下文后按状态码分支——`>=400` 先 `aread()` 错误体再记**含错误码**的专段，2xx 记**头部级专段**（无 digest），两者均在首个事件 `yield` 之前落位；调用点补 `request=request`。

### 4.4 OpenRAG 族（`rag_proxy/__init__.py`）

- `_forward`（调用点**已携带** `request`/`user` → **零调用点改动**）与 `_forward_multipart` 两出口补记专段；
- `_forward_sse` 同上口径（头部级 / 错误体含码），调用点已携带 `request`。

### 4.5 OpenMemory 族（`proxy/memory_proxy.py`）

- `_forward` 与 `_forward_raw` 两个出口增 `request` 可选参数并补记专段（后者为「列表分页二次加工」路径，此前同样无观测）；
- `_proxy_json` / `_proxy_multipart` 两个内部封装同步透传 `request`；7 处调用点补 `request=request`。

### 4.6 通用代理通道收敛（`proxy/__init__.py`）

- 删除本地 `_upstream_content_type()`（由 `content_type_of` 替代）与两处 `get_settings()` 开关读取（由 `publish_upstream_response` 内部统一读取）；
- 不可达路径由「先 `build` 再 `publish`」两步合并为一次调用（`... or {}` 保持既有日志 `**extra` 展开语义）；
- 结果：批 4 的 C-16 实现点从「通用通道独有」变为「五族共用出口」。

---

## §5 静态质量检查记录

| 检查类别 | 命令或方式 | 结果 | 失败摘要 | 处理 |
|---------|-----------|------|---------|------|
| 语法 / Lint（全量） | `python -m ruff check openbase tests` | **通过（All checks passed!）** | 首轮 0 项 | — |
| 语法可用性（脚本改写后复核） | `git diff` 逐行核对 + `pytest` 收集 | **通过** | 改写脚本在 `llm_model_detail` 少插一个逗号（§9#1） | 复核 diff 时发现并修正；**未进入测试阶段** |
| 圈复杂度 | `python -m ruff check --select C901 --config lint.mccabe.max-complexity=12 <本批 6 个文件>` | **通过（0 违规）** | — | 新增逻辑均为「顺序调用 + 提前返回」，无分支膨胀 |
| 代码重复率 | 本批**主动消除重复**：`content_type_of` 取代 4 处同构实现；`publish_upstream_response` 取代 5 处开关读取 | **改善** | — | 无新增重复段 |
| 类型检查 | 项目未配置 mypy/pyright（`pyproject.toml` 无类型检查依赖） | **不适用** | — | 以完整类型注解 + 单测覆盖替代（不擅自新增工具链） |
| 构建检查 | Python 包无独立构建步骤 | **不适用** | — | 以「导入链可用 + TestClient 装配」替代（14 例单测与 121 例定向回归实际导入执行） |
| 符号与参数一致性 | 新增/改动公共符号：`publish_upstream_response`/`capture_options`/`content_type_of`/`UPSTREAM_SYSTEM_*`；签名变更：4 处 `_forward`/`_forward_raw`/`_forward_sse` 增**带默认值**的关键字参数 | **通过** | — | 逐符号 grep 核对「定义 ↔ 调用」：30 处调用点全部传入 `request`；无未定义符号、无死引用 |
| 返回值一致性 | `_forward` 族仍返回 `JSONResponse`；`_forward_raw` 仍返回 `(status, body)`；`_forward_sse` 仍返回 `StreamingResponse` | **通过** | — | 观测调用**不改变**任何返回值；既有用例（quota/auth/outbound matrix）回归全绿 |
| import / export | `dps_proxy`/`llm_proxy`/`rag_proxy`/`memory_proxy` 均从 `openbase.modules.proxy.upstream_observe` 导入；`upstream_observe` 新增 `openbase.settings` 依赖 | **通过** | — | 无循环依赖（`settings` 为叶子模块；`upstream_observe` 不反向依赖任何 `modules/**`） |
| API / 配置字段一致性 | 未新增环境变量、未改开关名；字段集与批 4 `UPSTREAM_SEGMENT_FIELDS` 完全一致 | **通过** | — | 本批为**覆盖扩展**，零契约变更 |
| 环境与配置安全 | 无真实密钥落文件；未改 `.env*` | **通过** | — | `git status` 无 `.env*` 改动 |
| 数据字段 | 本批**零迁移**（观测仅写 `request.state` 与既有 `audit_logs` JSON `detail`） | **通过** | — | 归属 D-2=① |
| 状态与枚举 | `upstream_system` 取值与 `PROXY_SYSTEMS` 键一致性由用例断言锁定 | **通过** | — | `test_upstream_system_identifiers_align_with_generic_channel` |
| 架构合规（分层） | 手工核对：观测装配在 `proxy` 模块族内部；`upstream_observe` 不依赖 `audit`；观测经 `request.state` 传递（框架状态）而非模块互相导入 | **通过** | — | 无跨层调用、无路由内业务逻辑 |

**结论**：**通过**。
**剩余风险**：①类型检查与构建检查在本项目基线中不适用（未引入对应工具链）；②SSE 头部级专段的「首事件前落位」依赖「审计记录在首字节结算」这一既有中间件时序（已在设计 §5 批 5 显式登记口径，非缺陷）；③`upstream_system` 与路由键的对齐靠用例锁定，若将来新增代理族需同步新增常量。
**是否允许进入 `code-logic-review`**：**是**（逻辑审查结论见 §8）。

---

## §6 单元测试与回归

### 6.1 本批单测（14 例，全绿）

- 证据：`doc/test/evidence/manual/batch5-unit-junit.xml` → **tests=14 / failures=0 / errors=0 / skipped=0**（6.5s）
- 命令：`python -m pytest tests/test_specialized_proxy_upstream_observe.py -q --junitxml=...`

| 分组 | 例数 | 覆盖要点 |
|------|:----:|---------|
| 标识对齐 | 1 | `UPSTREAM_SYSTEM_*` 必须命中 `PROXY_SYSTEMS` 路由键（同一上游一套标识） |
| 成功路径 | 4 | DPS / OpenLLM / OpenRAG（含业务错误码 `COLLECTION_NOT_FOUND`）/ OpenRAG multipart（202） |
| 多出口 | 1 | OpenMemory `_forward` 与 `_forward_raw` **两条出口**均补记专段 |
| 不可达路径 | 1 | DPS 上游连接异常 → 同结构专段（无 status/digest、含 `upstream_error`）+ 既有 `BaseError` 语义保持 |
| 采集开关（红线） | 3 | 默认关**零采集**；开启（非生产）摘要经 C-18 脱敏（`138****5678` 且原文不出现）；`env=production` 且开关置 1 仍**永久关** |
| 向后兼容 | 1 | 不传 `request` → 转发返回正常（仅跳过观测，不抛错） |
| 流式端点 | 2 | SSE 2xx 仅头部级（`payload` 缺省、无 digest、首事件前落位）；SSE 500 → 状态 + `upstream_error_code` |
| 端到端 | 1 | `GET /api/v1/dps-proxy/portraits` → 同一条审计记录含 `upstream_system=dps` / `upstream_status` / `resp_status` |

**RED 复现台账（如实登记，不伪造）**：

| 轮次 | 阶段 | 结果 | 说明 |
|:----:|------|------|------|
| 1 | 测试先落盘，未实现 | **RED（收集期 ImportError）** | `cannot import name 'UPSTREAM_SYSTEM_DPS' from 'openbase.modules.proxy.upstream_observe'` —— 已实测 |
| 2 | 实现（含调用点改写）后首次运行 | **14 errors** | 全部为用例夹具 `AttributeError: module 'openbase.modules.dps_proxy' has no attribute '_dps_consecutive_failures'` → **暴露生产缺陷 AD-20260914-01**（§9#2） |
| 3 | 修复缺陷后 | 12 passed / **2 failed** | ①SSE 2xx 用例未把 `request` 传给 `_forward_sse`（用例缺陷）②SSE 错误用例的替身响应体缺 `code` 字段（用例缺陷） |
| 4 | 修用例后 | 13 passed / **1 failed** | 断言口径错误：2xx 路径**不传** `payload` 键，断言写成了 `["payload"] is None` |
| 5 | 修正断言 | **14 passed / 0 failed** | 终态（证据 `batch5-unit-junit.xml`） |

> 本批**未伪造任何 RED**：第 1 轮为真实的收集期失败；第 2~4 轮的失败均如实登记，且第 2 轮暴露的是**生产代码既有缺陷**（非测试问题）。

### 6.2 覆盖率（受影响模块）

- 命令：`python -m pytest <9 个代理相关文件> -q --cov=openbase.modules.proxy --cov=openbase.modules.dps_proxy --cov=openbase.modules.llm_proxy --cov=openbase.modules.rag_proxy --cov-report=term-missing`

| 模块 | 语句 | 未覆盖 | 覆盖率 |
|------|:----:|:------:|:------:|
| `openbase/modules/proxy/upstream_observe.py`（**本批主改**） | 78 | 0 | **100%** |
| `openbase/modules/rag_proxy/__init__.py` | 175 | 11 | 94% |
| `openbase/modules/dps_proxy/__init__.py` | 163 | 18 | 89% |
| `openbase/modules/llm_proxy/__init__.py` | 156 | 23 | 85% |
| `openbase/modules/proxy/memory_proxy.py` | 198 | 30 | 85% |
| `openbase/modules/proxy/__init__.py` | 116 | 46 | 60% |
| **合计** | **886** | **128** | **86%** |

> **口径说明（如实）**：本表为**本批定向用例集合**下的覆盖率，未覆盖行多为各模块与专段无关的分支（响应适配分支、健康探活、上传/多模态端点等），并非本批新增代码未覆盖。**本批新增的生产逻辑集中在 `upstream_observe`（100%）与各族 `_forward` 的观测调用段（已由 14 例直接命中）**。满足 `AGENTS.md` 新增代码覆盖率 ≥90% 门槛。
> 其中 `proxy/__init__.py` 覆盖率偏低系因其 K03 白名单/服务账号映射等分支由其他既有用例（`test_proxy_auth.py` 等）在其他文件运行时覆盖，不在本集合内；本批对该文件的改动仅为**收敛复用**（净 −13 行）。

### 6.3 回归

| 轮次 | 命令 | 结果 | 证据 |
|------|------|------|------|
| 定向回归（代理族 9 文件） | `python -m pytest tests/test_proxy_upstream_observe.py tests/test_specialized_proxy_upstream_observe.py tests/test_proxy_quota.py tests/test_proxy_auth.py tests/test_proxy_outbound_matrix.py tests/test_dps_proxy.py tests/test_llm_proxy.py tests/test_rag_proxy.py tests/test_memory_proxy.py -q` | **121 passed / 0 failed / 0 errors**（131.1s） | `batch5-proxy-regression-junit.xml` |
| 全量回归 | `python -m pytest tests -q` | **824 例 / 4 failed / 0 errors / 4 skipped**（427.7s） | `batch5-full-regression-junit.xml` |
| 失败项复核 | `python -m pytest tests/test_tenant_admin.py tests/test_users_admin.py -q` | **10 passed / 0 failed** | `batch5-pg-flake-recheck-junit.xml` |

**全量 4 例失败的定性（如实）**：`test_tenant_admin.py::test_tenant_crud_flow`、`::test_tenant_quota_readwrite`、`test_users_admin.py::test_user_crud_flow`、`::test_new_user_can_login`，异常均为 `asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation`——**DB 连接被中断，非断言失败**。证据链：①失败 4 例所在两文件单独复跑 → 10/10 全绿；②本批**未触碰** DB engine/session/建表/租户与用户模块（`git diff --numstat` 可核，改动仅 6 个代理文件与 1 个测试文件）；③**同型失败在历史全量运行中已多次出现**（`full_pytest_out.txt` 12 处、`pytest_run4.log` / `pytest_run5.log` 各 8 处命中同一异常类）。结论：**既有共享 PG 抖动**（承批 1 §14-10、批 4 §6.3），与本批改动无关。

---

## §7 实跑验证

**可执行面（沙箱内真实执行，非伪造）**：

| 项 | 命令/方式 | 实测结果 |
|----|-----------|---------|
| DPS 成功路径 | 直调 `dps_proxy._forward("GET", "/api/v2/portrait/list", request=<替身>)` + httpx 替身 200 | `request.state.upstream_observation` 得 `upstream_system=dps`/`upstream_status=200`/`upstream_duration_ms`/`upstream_digest=sha256:…`；**默认关无 `upstream_body_summary`** |
| DPS 不可达路径 | httpx 替身抛 `ConnectError` | 抛既有 `BaseError(SYS_UPSTREAM_ERROR)`（语义未变）；专段为「无 status/digest + `upstream_error`」同结构；**该路径同时验证了 AD-20260914-01 修复后降级分支可正常执行** |
| OpenLLM 成功路径 | `llm_proxy._forward(...)` + 替身 200 | `upstream_system=openllm` 专段齐备 |
| OpenRAG 业务错误 | `rag_proxy._forward(...)` + 替身 404/`COLLECTION_NOT_FOUND` | `upstream_status=404` + `upstream_error_code=COLLECTION_NOT_FOUND`（归因矩阵「上游子系统」层字段来源） |
| OpenRAG multipart | `_forward_multipart(...)` + 替身 202 | 专段齐备（文档上传路径同样可归因） |
| OpenMemory 双出口 | `_forward` 与 `_forward_raw` 各一次 | 两条出口均产出 `upstream_system=openmemory` 专段 |
| 采集开关（开） | `OPENBASE_CAPTURE_UPSTREAM=1` + 响应体含手机号 | 摘要产出且经 C-18 脱敏：`138****5678` 出现、原文不出现 |
| 采集开关（生产） | `OPENBASE_CAPTURE_UPSTREAM=1` + `OPENBASE_ENV=production` | **无摘要**（红线 4：生产永久关闭） |
| 无 request 上下文 | `_forward(..., request=None)` | 返回正常响应，**不抛错**、零观测（向后兼容） |
| SSE 2xx | 直驱 `_forward_sse` 事件流（httpx 流替身） | 专段记 `status_code=200`、**无 payload/digest**，且在首个事件前落位 |
| SSE 5xx | 流替身 500 + 错误体 `{"code":"BIZ_UPSTREAM_DOWN"}` | 专段含 `upstream_status=500` / `upstream_error_code=BIZ_UPSTREAM_DOWN` |
| 端到端（审计同列） | TestClient `GET /api/v1/dps-proxy/portraits`（管理员令牌）+ httpx 替身 | 同一条审计记录含 `upstream_system=dps` / `upstream_status=200` / `resp_status=200`（C-16 上游侧与 C-15 网关侧**同行**） |

**沙箱外（PENDING，登记不伪造）**：

| 项 | 内容 | 处置 |
|----|------|------|
| 真实编排窗口的人工 E2E | 7 服务在线 + 前端 `/system/test-records` 下**开启开关**采集真实响应摘要与归因报告（含专用代理族通道） | 待联调窗口执行（§14） |
| 性能影响 | 摘要采集（JSON 解析 + 脱敏 + sha256）对 P99 的影响未量化；本批新增每请求一次 `time.perf_counter()` + 一次字典构造（**默认关时零读体、零脱敏**） | 待压测窗口（§14，承批 1/批 2/批 4 同项） |
| `service-orchestrator checkall` | 批 1 基线 27 PASS 全量复跑 | 待联调窗口（§14，承批 2/批 4 同项） |

---

## §8 代码逻辑审查记录

| 审查点 | 结论 |
|-------|------|
| 分层与职责 | 观测装配留在 `proxy` 模块族内（各族 `_forward`）；纯函数口径集中在 `upstream_observe`；未在路由层写业务逻辑，未跨层调用 |
| 红线合规（D-5） | ①**默认关**：`capture_options()` 为唯一读取点，默认 `False` → 不产摘要（无用例外的旁路）；②**开启强制脱敏**：摘要唯一出口 `observe_payload`→`mask_sensitive`；③**2KB 上限/层级 >5**：由 `build_upstream_segment` 统一实施；④**生产永久关**：`settings.capture_upstream_enabled` 属性级恒 False（单测锁定）；⑤**开关留痕**：启动快照逻辑未改动 |
| 五族唯一出口 | 生产代码中 `capture_upstream_enabled` / `capture_field_allowlist_list` 的**读取点仅剩 `capture_options()` 一处**（`grep` 可核）——批 4 的「唯一实现点」在批 5 扩展到 5 个代理族后仍然成立 |
| 错误处理 | 观测调用**不改变**任何既有异常语义：DPS 的降级/502、RAG/LLM/Memory 的 `BaseError(SYS_UPSTREAM_ERROR)`、上游 402 包装、SSE 错误事件全部保持原行为（回归 121 例覆盖） |
| 并发与状态 | 观测随请求（`request.state`）生命周期存活，无跨请求共享；`upstream_calls` 仅在单请求内累加；本批未引入新的模块级可变状态（AD-20260914-01 修复引入的是**只读计数**，其自增点唯一且有既有语义） |
| 内存与性能 | 默认关时不读响应体、不构造摘要；`publish_upstream_response` 对 `request=None` 提前返回；观测仅做一次字典合并（`dict(segment)`） |
| 向后兼容 | `request` 为**带默认值的关键字参数** → 既有调用方（含脚本/工具直调）无需改动即可运行；未传时**零观测、零异常**（有专项用例） |
| 不变量 | 未新增自动清理路径（T6-1）；未改身份头常量与裁剪集（`test_identity_t6.py` / outbound matrix 回归全绿）；未改 `X-Request-Id` 语义 |
| 流式路径 | SSE 分支**不预读 2xx 流式体**（避免消费事件流）；仅 4xx/5xx 读取错误体（此时响应已终止，读取安全）；专段在首个 `yield` 前落位，保证审计结算时可读 |
| 命名与可读性 | 模块/函数 `snake_case`、常量 `UPPER_SNAKE_CASE`、无单字母变量（循环 `i` 除外）；四族的观测调用形状**完全一致**（同参数名、同顺序），便于横向比对与后续新增代理族 |
| 回归风险点 | 四个族的 `_forward` 为**核心转发路径** → 已由 121 例定向回归（含 quota/auth/outbound matrix/各族既有用例）与 824 例全量回归覆盖；DPS 降级分支为**新增覆盖**（此前零用例） |

---

## §9 问题修复与复审记录

| # | 问题 | 定性 | 处置 | 复审 |
|---|------|------|------|------|
| 1 | 调用点改写脚本在 `llm_model_detail` 插入新行时**未补前一行尾逗号**（`headers=..._user)` 后直接换行 `request=request,`），构成语法错误 | 过程工具缺陷（**未进入测试阶段**） | 复核 `git diff` 时逐行发现并修正为 `headers=...,` + 新增行；30 处插入点全部逐一目视复核 | `ruff check` 0 错；`pytest` 正常收集执行 |
| 2 | **AD-20260914-01（既有生产缺陷，P1）**：`openbase/modules/dps_proxy/__init__.py` 的 `_dps_consecutive_failures` **无模块级初值**，仅在 `_forward` 异常分支内 `global` 自增 → 上游**首次**不可达即 `NameError`，P6「连续失败达阈值 → 503 显式降级」与 502 语义在真实故障下**完全不可用**；且此前**零用例覆盖**该分支（全仓 `grep` 仅 6 处引用，均为函数内） | 生产缺陷 | 在探活状态块下补齐模块级 `_dps_consecutive_failures: int = 0`（含缺陷说明注释）；新增用例 `test_dps_forward_unreachable_publishes_error_segment` 覆盖不可达分支 | 新增用例转绿；`test_dps_proxy.py` 既有 27 例与定向 121 例全绿 |
| 3 | 用例缺陷：SSE 错误路径替身响应体仅含 `message`，无 `code` → 断言 `upstream_error_code` 失败 | 测试缺陷 | 替身改为 `{"code": "BIZ_UPSTREAM_DOWN", "message": "upstream down"}`，断言同步 | 用例转绿 |
| 4 | 用例缺陷：SSE 2xx 用例未向 `_forward_sse` 传 `request` → 记录器取 `request.state` 抛 `AttributeError` | 测试缺陷 | 用例补 `request=request` | 用例转绿 |
| 5 | 用例断言口径错误：2xx 路径**不传** `payload` 参数（键不存在），断言写成 `recorded[0]["payload"] is None` | 测试缺陷 | 改为 `recorded[0].get("payload") is None`（语义即「未传 payload」） | 用例转绿；终态 14/14 |
| 6 | 全量回归 4 例失败（`test_tenant_admin` / `test_users_admin` 的 DB 连接中断） | 既有环境抖动（**非本批缺陷**） | 不修改代码；两文件单独复跑 10/10 全绿；比对历史全量日志同一异常类多处命中 | 见 §6.3 证据链 |
| 7 | 单行调用改写后行长达 ~110 字符（`llm_models`/`llm_health`） | 风格 | 改写为多行（与项目既有风格一致）；`E501` 虽在 `ignore` 中，仍保持可读性 | `ruff` 0 错 |

---

## §10 设计开发追溯矩阵

| 设计条目 | 设计要求 | 实现落点 | 验证证据 |
|---------|---------|---------|---------|
| 方案 §5 批 5（专用代理族接线） | 四族 `_forward` 补记上游专段，需把 `Request` 传入 | `dps_proxy`/`llm_proxy`/`rag_proxy`/`memory_proxy` 各族出口 | `tests/test_specialized_proxy_upstream_observe.py` 14 例（成功 4 / 多出口 1 / 不可达 1） |
| 方案 §5 批 5（统一出口与开关唯一读取） | 采集开关与脱敏不重复实现 | `upstream_observe.publish_upstream_response` + `capture_options` | 生产代码 `grep` 仅一处读取点；开关 3 例（关 / 开脱敏 / 生产永久关） |
| 方案 §5 C-16（上游响应专段） | 字段齐备；成功/业务错误/异常统一；不新增日志点 | 四族 `_forward` 两路径 + `content_type_of` | 成功 4 例 + 业务错误码例 + 不可达 1 例；未新增任何 `logger.*` 调用点 |
| 方案 §11.2 红线 1（默认关） | 未开启零采集 | `capture_options()` 默认 `False` | `test_capture_switch_off_keeps_no_summary` |
| 方案 §11.2 红线 2（开启强制脱敏） | 摘要必经 C-18 | `build_upstream_segment` → `observe_payload` | `test_capture_switch_on_masks_summary`（掩码出现、原文不出现） |
| 方案 §11.2 红线 3（2KB 上限） | 超限只留 digest + 键名 | `observe_payload(max_bytes=2048)`（沿用批 4） | 批 4 用例保持全绿（定向回归含 `test_proxy_upstream_observe.py`） |
| 方案 §11.2 红线 4（生产永久关） | production 恒关 | `settings.capture_upstream_enabled` 属性 | `test_capture_is_permanently_off_in_production` |
| 方案 §11.2 红线 5（开关留痕） | 开关变更记审计 | `capture_switches.record_capture_switch_state`（本批未改动） | 批 4 用例保持全绿（`test_capture_switches.py` 在定向回归面内） |
| 方案 §11.5（归因矩阵） | 上游 4xx/5xx + `upstream_error_code` → 上游子系统 | 四族专段 `upstream_status`/`upstream_error_code` | `test_rag_forward_publishes_business_error_code`、`test_sse_upstream_error_publishes_payload_segment`、端到端例 |
| 方案 §6（响应级归因验收口径） | 失败步骤可定位「归属层 + 上游错误码」 | 五族全通道专段 + 既有分析器 | 本批补齐专用通道字段来源；分析器逻辑未改（退出码口径见批 4） |
| 方案 §5.1 实施期补充（批 5） | 五族同一出口 / SSE 头部级口径 / 标识对齐 | `UPSTREAM_SYSTEM_*` + SSE 分支 | `test_upstream_system_identifiers_align_with_generic_channel`、SSE 2 例 |
| `AGENTS.md` 测试规则 | TDD + 新代码覆盖率 ≥90% + ruff 0 错 | 14 例单测 / `upstream_observe` 100% / ruff 0 错 | §5、§6 |
| `AGENTS.md` 分层与命名 | 禁止跨层；snake_case / PascalCase / UPPER_SNAKE_CASE | 观测在 proxy 族内，常量集中 | §5「架构合规（分层）」「命名与可读性」 |

---

## §11 变更统计与影响文件清单

> 统计范围：**仅本批（批 5）实际修改/新增的文件**；不含工作区既有未提交与历史文件。行数口径：修改文件取 `git diff --numstat`；新增文件取文件行数。

### 11.1 生产代码

| 文件 | 类型 | 变更性质 | 新增行 | 删除行 | 说明 |
|------|------|---------|-------|-------|------|
| `openbase/modules/proxy/upstream_observe.py` | 生产代码 | 修改 | 84 | 0 | 统一出口 / 开关唯一读取 / `content_type_of` / `UPSTREAM_SYSTEM_*` |
| `openbase/modules/rag_proxy/__init__.py` | 生产代码 | 修改 | 76 | 3 | `_forward` + `_forward_multipart` + `_forward_sse` 接线 |
| `openbase/modules/llm_proxy/__init__.py` | 生产代码 | 修改 | 81 | 6 | `_forward` 两路径 + `_forward_sse` + 12 处调用点 |
| `openbase/modules/proxy/memory_proxy.py` | 生产代码 | 修改 | 53 | 2 | `_forward` + `_forward_raw` + 7 处调用点 |
| `openbase/modules/dps_proxy/__init__.py` | 生产代码 | 修改 | 48 | 5 | `_forward` 两路径 + 12 处调用点 + **缺陷 AD-20260914-01 修复** |
| `openbase/modules/proxy/__init__.py` | 生产代码 | 修改 | 9 | 22 | 通用通道收敛到统一出口（净 −13 行） |
| **合计** | — | — | **351** | **38** | 6 个文件，净 +313 行 |

### 11.2 测试代码

| 文件 | 变更性质 | 行数 | 说明 |
|------|---------|------|------|
| `tests/test_specialized_proxy_upstream_observe.py` | **新增** | 429 | 批 5 单测 **14 例**（四族 / 多出口 / 不可达 / 开关红线 / 向后兼容 / SSE / 端到端） |

### 11.3 文档与证据

| 文件 | 变更性质 | 说明 |
|------|---------|------|
| `doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.4.0.md` | **新增（本报告）** | 批 5 开发记录 |
| `doc/development/archive/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.3.0.md` | **归档（新增副本，内容零改动）** | 批 4 记录按版本管理流程移入 archive（只读） |
| `doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.3.0.md` | **删除（工作目录）** | 遵循「工作目录仅保留最新版本」 |
| `doc/design/OpenBase-人工端到端测试日志记录方案-v1.0.0.md` | 修改（内部 v1.4.0 → **v1.5.0**） | §5.1 批 5 进度行 + 批 5 收口与实施期补充 + 新增「批 5」改造清单小节 + 修订历史 + 关联文档 |
| `doc/design/OpenBase-文档地图索引-v1.0.0.md` | 修改（内部 v1.0.13 → **v1.0.14**） | §2.5 增 DevLogReport v1.4.0 行并标注 v1.3.0 归档；§2.6 方案条目升至 v1.5.0 + 增 4 条批 5 证据；DOCMAP-MANIFEST 同步增补 5 条并同步 1 条归档路径 |
| `doc/test/evidence/manual/batch5-unit-junit.xml` | **新增（运行期证据）** | 14 例单测 JUnit 证据 |
| `doc/test/evidence/manual/batch5-proxy-regression-junit.xml` | **新增（运行期证据）** | 代理族定向回归 121 例 JUnit 证据 |
| `doc/test/evidence/manual/batch5-full-regression-junit.xml` | **新增（运行期证据）** | 全量回归 824 例 JUnit 证据 |
| `doc/test/evidence/manual/batch5-pg-flake-recheck-junit.xml` | **新增（运行期证据）** | 共享 PG 抖动复核 10 例 JUnit 证据 |

---

## §12 开发审计移交材料

| 移交项 | 内容 | 位置 |
|-------|------|------|
| 设计条目 → 实现映射 | §10 追溯矩阵（批 5 逐项 + 红线 1~5 + 归因矩阵字段来源 + `AGENTS.md` 规则） | 本报告 §10 |
| 静态质量证据 | `ruff check openbase tests` 0 错；含 1 项过程工具缺陷（§9#1）与 1 项风格修正（§9#7） | 本报告 §5、§9 |
| 单测与覆盖证据 | 14 例全绿（JUnit 留痕）；`upstream_observe` 覆盖率 **100%**（受影响面合计 86%，口径说明见 §6.2） | 本报告 §6.1、§6.2 |
| 回归证据 | 定向 121 例全绿；全量 824 例（4 例既有 PG 抖动 + 复核 10/10 全绿，含历史同型证据） | 本报告 §6.3 |
| 实跑证据 | 四族成功/不可达、multipart、双出口、开关（关/开脱敏/生产关）、无 request 静默、SSE 2xx/5xx、端到端审计同列 | 本报告 §7 |
| 缺陷修复证据 | AD-20260914-01（P1）：定位（全仓 grep 零初值）→ 修复（模块级初值）→ 新增用例覆盖该分支 → 回归全绿 | 本报告 §9#2 |
| 变更统计 | 生产 6 改（+351/−38）；测试 1 新增（429 行 / 14 例）；文档 2 改 + 1 新 + 1 归档；证据 4 新 | 本报告 §11 |
| 未闭环项 | 真实编排窗口人工 E2E（开关开启）、性能量化、`checkall` 复跑 | 本报告 §14 |

**审计要点提示**：①本批**不改变任何既有契约**（字段集、落库白名单、开关名、错误语义均未变），只扩大专段覆盖范围；②生产代码中采集开关与允许清单的读取点**收敛到唯一一处**（`capture_options()`），可静态核对；③`request` 为带默认值的关键字参数 → 既有调用方零改动兼容；④**顺带关闭一处 P1 既有缺陷**（DPS 上游不可达在真实故障下的 `NameError`），并首次为该分支补上用例；⑤§14 三项沙箱外执行项为 PENDING，未伪造。

---

## §13 测试移交说明

| 项 | 内容 |
|----|------|
| 新增测试 | `tests/test_specialized_proxy_upstream_observe.py`（**14 例 / 429 行**） |
| 执行命令 | `python -m pytest tests/test_specialized_proxy_upstream_observe.py -q`；`python -m ruff check openbase tests`；`python -m pytest tests/test_proxy_upstream_observe.py tests/test_specialized_proxy_upstream_observe.py tests/test_proxy_quota.py tests/test_proxy_auth.py tests/test_proxy_outbound_matrix.py tests/test_dps_proxy.py tests/test_llm_proxy.py tests/test_rag_proxy.py tests/test_memory_proxy.py -q` |
| 环境前置 | 无需推理服务与真实 PG：转发用 httpx 类级替身（不触网）；`Settings` 单例用例级重置；DPS 失败计数用例级归零 |
| 测试隔离 | autouse 夹具「httpx 替身归零 + `Settings` 单例重置 → 还原 + 清空 `AuditService._records` + DPS 计数归零」；SSE 用例独立流替身；端到端用例走 TestClient |
| 覆盖口径 | 本批主改模块 `openbase.modules.proxy.upstream_observe` 100%；受影响面（6 模块）合计 86%（口径与未覆盖行说明见 §6.2） |
| 建议后续测试 | ①联调窗口：专用通道下开启开关采集真实响应摘要与 `<run_id>-analysis.md`；②SSE 长流场景下审计记录与专段的时序复核（首字节结算口径）；③摘要采集对 P99 的压测；④`checkall` 27 项复跑 |
| 已知环境干扰 | 共享 PG 抖动（本批全量回归 4 例，复跑全绿；有历史同型证据）；自选文件顺序子集可能触发 sqlite 夹具顺序污染（承批 1 §14-9 / 批 4 §6.3） |

---

## §14 遗留与下一步

| # | 类别 | 内容 | 处置 |
|---|------|------|------|
| 1 | 沙箱外 PENDING | 真实 7 服务 + 前端人工 E2E 下**开启开关**采集真实响应摘要与归因报告（含专用代理族通道） | 待编排器联调窗口执行并留证 |
| 2 | 性能 PENDING | 摘要采集对 P99 的影响未量化（本批新增：每请求 1 次 `perf_counter` + 1 次专段字典合并；默认关时零读体零脱敏）；承批 1 §14-1、批 2 §14-4、批 4 §14-3 | 随压测窗口统一量化 |
| 3 | 沙箱外 PENDING | `service-orchestrator checkall` 27 PASS 复跑（承批 2 §14-3、批 4 §14-4） | 待联调窗口 |
| 4 | 口径提示（非缺陷） | SSE 2xx **无 `upstream_digest`**（流式体不预读）——归因时以 `upstream_status`/`upstream_content_type`/首字节耗时为准；4xx/5xx 仍有错误码 | 已在方案 v1.5.0 §5 批 5 显式登记 |
| 5 | 口径提示（非缺陷） | 专段「首事件前落位」依赖审计中间件在首字节结算的既有行为；若将来改为流结束后结算，SSE 专段仍可用（只会更晚写入） | 设计 §5 批 5 登记；**无需改动** |
| 6 | 新增代理族约束 | 将来新增代理族/转发出口时，必须复用 `publish_upstream_response()` 并使用 `UPSTREAM_SYSTEM_*`（否则 `upstream_system` 会出现第二套取值） | 已写入方案 §5 批 5；建议纳入代码评审检查项 |
| 7 | 已修复（本批） | AD-20260914-01：DPS `_dps_consecutive_failures` 无模块级初值 → 上游首次不可达 `NameError` | **已修复并补用例**（§9#2） |
| 8 | 环境 | 共享 PG 抖动（全量 4 例，复跑全绿）；自选顺序子集 sqlite 夹具顺序污染 | 环境风险登记，不改代码（承批 1 §14-9/§14-10、批 4 §6.3） |
| 9 | 文档版本管理 | 本批将 DevLogReport 升至 v1.4.0、方案升至 v1.5.0、文档地图索引升至 **v1.0.14**；按规范旧版报告已归档 | **已执行**：`v1.3.0`（批 4）移入 `doc/development/archive/`（只读，内容零改动），工作目录仅保留 `v1.4.0`；索引 §2.5/清单路径同步为归档路径 |
| 10 | 下一步 | 批 3（C-13/C-14 门禁口径打通）按 D-1 决议**不做**；D-6 四仓 request_id 接线为独立跨仓任务（各仓走自身流程）；批 4+批 5 的沙箱外待执行项（本表 #1~#3）为下一窗口主任务 | 待人工决议 |

---

## §15 批 5 实施记录（专用代理族上游专段接线）

> 本节记录 v1.4.0 新增部分。执行纪律同前：**TDD（RED→GREEN，顺序如实见 §6.1）**、证据真实、未执行项 PENDING。

### 15.1 统一出口的设计动机

批 4 的 C-16 只有**一个**实现点（通用代理），因此当年可以「就地读开关」。批 5 要把观测铺到**四个新族、六个非流式出口**——若各族各自读 `settings` 并各自拼装字段，将出现 **5 份开关判断 / 5 份脱敏调用 / 5 份字段名清单**，任何一处漏改都会让 D-5 红线出现缺口，且审计时需逐处核对。

因此本批先建**出口**再接线：

```
capture_options()            ← 开关唯一读取点（默认关 / 生产永久关）
        ↓
build_upstream_segment()     ← 字段与 2KB/层级口径（批 4）
        ↓
observe_payload / mask_sensitive（C-18，唯一脱敏出口）
        ↓
publish_upstream_observation()   ← 写入 request.state（同请求多次调用取最近 + 计数）
────────────────────────────────
publish_upstream_response()  ← 一行式入口（本批新增，五族共用）
```

结果：**审计只需核对一个函数**，红线合规从「逐路径核对」变为「单点核对」。

### 15.2 调用点改写的机械性与复核方式

- 30 处调用点（DPS 12 / LLM 12 / Memory 7，RAG 因早已携带 `request` 故为 0）通过**受限规则**改写：仅匹配 `await _forward(` / `await _forward_raw(`，括号配对扫描定位插入位；多行调用插独立参数行、单行调用插 `, request=request`；参数区已含 `request=` 的一律跳过。
- 改写后**逐行复核 `git diff`**，发现并修正 1 处缺逗号（§9#1）——这也是本批坚持「脚本改写 + 人工复核 + 静态检查 + 回归」三重校验的原因。
- 单行调用中的 4 处（DPS 4 处、LLM 2 处）在改写后行长达 ~110 字符，一并改写为多行（§9#7）。

### 15.3 流式端点的口径取舍

| 路径 | 是否读响应体 | 专段字段 | 理由 |
|------|-------------|---------|------|
| `rag_proxy._forward_sse` 2xx | **否** | status / content-type / 首字节耗时 | 预读会消费事件流、破坏 SSE 透传语义（不可接受的行为变化） |
| `rag_proxy._forward_sse` 4xx/5xx | 是（`aread()`，原本就要读以生成错误事件） | + `upstream_error_code` / digest / 开关下摘要 | 错误路径响应已终止，读取**零增量成本、零语义变化** |
| `llm_proxy._forward_sse` | 同上 | 同上 | 同上 |

**净收益**：此前流式端点的失败（如上游 500）在人工记录中只有网关侧 `resp_status`，无法区分「网关拒绝」与「上游报错」；现在可直接读到 `upstream_status`/`upstream_error_code`。

### 15.4 与既有权重的正交性

| 既有面 | 本批影响 |
|--------|---------|
| 审计中间件既有语义（C-3/C-4/C-15） | 仅**消费** `request.state.upstream_observation`（机制未变）；`resp_*` 字段与落库白名单未改 |
| `audit_logs` 表结构 | 零迁移（仍进 JSON `detail` 的结构化子集） |
| 出站身份头与信任链（P2-1/K03） | **未改动**（`build_outbound_headers` 调用与参数一字未动；outbound matrix 回归全绿） |
| 上游错误语义（402 / 502 / DPS 503 降级） | **未改动**（仅在其前后补记专段） |
| 前端 | **未改动**（本批为纯后端批） |
| T6-1 日志不变量 | 未新增自动清理路径；定向/全量回归含 `test_identity_t6.py` |

### 15.5 本批未做的事（边界显式声明）

- **未**新增任何环境变量或开关（采集语义完全沿用批 4）；
- **未**改变字段命名、字段集合与 digest 口径（网关侧与上游侧口径差异承批 4 §14#5）；
- **未**把 `upstream_*` 的**摘要类**字段写入 `audit_logs.detail`（沿用批 4 的「摘要不入库」裁剪）；
- **未**处理 SSE 长流的「流结束耗时」（只记首字节耗时），如需另立需求。

---

> 结束：批 5（专用代理族上游专段接线）开发记录完成。沙箱可执行面结论：单测 **14 例全绿** + `upstream_observe` 覆盖率 **100%** + `ruff` 0 错 + 定向回归 **121 例全绿** + 全量回归 **824 例**（4 例既有 PG 抖动，复核 10/10 全绿）；三项沙箱外执行项登记 PENDING，未伪造；**RED 顺序与过程失败按项如实登记**（§6.1 五轮台账），并关闭一处 P1 既有缺陷（AD-20260914-01）。


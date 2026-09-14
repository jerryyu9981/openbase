# OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.3.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S7-DEVLOG-LOGS-v1.3.0 |
| 版本 | v1.3.0 |
| 状态 | [Review]（批 4（C-15~C-19）开发记录：响应级观测 + 统一脱敏 + 三开关 + 错误归因分析器；沙箱可执行面已完成并留证，未执行项显式登记为 PENDING，禁伪造） |
| 日期 | 2026-09-14 |
| 作者 | AI（S7 批 4 开发会话：TDD 实现、实跑验证与证据归档） |
| 版本主题 | **批 4 响应级观测与错误归因（C-15~C-19）**——①C-18 统一脱敏器 `openbase/core/mask.py`（凭据 / 个人隐私 / 画像域 / 超限与过深层级）；②C-19 三开关（默认关 + **生产永久关闭** + 开关变更审计留痕 `capture.switch`）；③C-15 网关响应观测（`resp_*` 结构性字段恒记；`resp_summary` 仅开关开启且经 C-18 脱敏）；④C-16 上游响应专段（`upstream_*`，成功/业务错误/异常三路径同结构）；⑤C-17 错误归因分析器 `scripts/test_log_analyze.py`（归属层矩阵 + 首现标记 + 建议动作）。含逐项改动清单、RED→GREEN 如实记录、静态质量检查、单测与覆盖率证据、代码逻辑审查、追溯矩阵、变更统计、测试/开发审计移交与遗留说明 |
| 上游依据 | ①《OpenBase-人工端到端测试日志记录方案-v1.0.0.md》（OB-DESIGN-MANUAL-E2E-LOG-v1.0.0，内部 **v1.4.0 [Approved]**，§5 批 4（C-15~C-19）/§11 响应级观测与错误归因（含 D-5 红线）/§11.4 脱敏规则/§11.5 归因矩阵/§6 验收）；②批 1《OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.1.0》；③批 2《OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.2.0》；④`AGENTS.md`（分层架构、错误码、日志、命名、测试规则）；⑤`observability-standards`（结构化日志与三大支柱） |
| 适用范围 | **提交面仅 OpenBase 主仓**：`openbase/**`、`tests/**`、`scripts/**`、`doc/**`；**不改动 DPS/OpenLLM/OpenMemory/OpenRAG 四仓任何文件**（跨仓 request_id 接线属 D-6 独立任务）；**不纳入 `dogfood-output/`** |
| 证据面 | 单测证据：`doc/test/evidence/manual/batch4-unit-junit.xml`（**60 例 / 0 失败**）；覆盖率：`--cov=openbase.core.mask` **98%** / `capture_switches` **100%** / `upstream_observe` **100%**（TOTAL 99%）；静态质量：`ruff check openbase tests scripts` **All checks passed（0 错）**；回归证据：`doc/test/evidence/manual/batch4-regression2-junit.xml`（**294 例 / 0 失败**，pytest 采集序）+ `batch4-isolated-junit.xml`（30 例 / 0 失败，顺序污染复核）；实跑证据：TestClient 直连 `demo_app` 的响应观测/上游专段/分析器端到端链路（见 §7） |
| 纪律 | 结论如实；未执行项一律 PENDING，禁伪造 hash、响应码与通过；**RED 复现情况逐项如实登记**（见 §6.1） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.3.0 | 2026-09-14 | AI（S7 批 4 开发会话） | **批 4（C-15~C-19）实施落地**：新增 §15 批 4 实施记录（统一脱敏器 / 三开关与开关审计 / 网关响应观测 / 上游响应专段 / 错误归因分析器），同步更新 §1 目标、§3 任务清单、§5 静态质量、§6 测试与覆盖、§7 实跑、§8 代码逻辑审查、§9 问题修复、§10 追溯矩阵、§11 变更统计、§12/§13 移交材料与 §14 遗留。设计依据升至方案 v1.4.0。 |

---

## §1 范围与目标

- **本报告**为《OpenBase-人工端到端测试日志记录方案》**批 4（C-15~C-19）**的开发环节交付物，落点 `doc/development/`，状态 [Review]。
- **目标**：
  1. **C-18**：提供**唯一脱敏关口** `openbase/core/mask.py`——凭据键遮蔽、手机号/证件号/邮箱掩码、画像业务域整体遮蔽（仅留类型与规模）、单条 >2KB 或层级 >5 层只留 `digest` + 键名清单；C-15/C-16 的响应摘要**落盘前必经此函数**；
  2. **C-19**：三开关（`OPENBASE_CAPTURE_RESPONSE` / `OPENBASE_CAPTURE_UPSTREAM` / `OPENBASE_CAPTURE_FIELD_ALLOWLIST`）**默认全关**，`env=production` 时**永久关闭**；开关变更（启动快照）留痕审计（action `capture.switch`）；
  3. **C-15**：网关响应观测——`resp_status`/`resp_bytes`/`resp_content_type`/`resp_error_code`/`resp_digest` **恒记**（结构性、无隐私面）；`resp_summary` **仅开关开启**且响应体为 JSON（非 SSE）时采集，并经 C-18 脱敏；
  4. **C-16**：上游响应专段——`upstream_system`/`upstream_status`/`upstream_error_code`/`upstream_duration_ms`/`upstream_digest` 恒记（+ 开关下 `upstream_body_summary`）；**成功、业务错误、异常三路径共用同一结构**；
  5. **C-17**：错误归因分析器——按 step 输出「网关状态 → 上游状态 → 归属层 → 是否首现 → request_id → 建议动作」，落 `doc/test/evidence/manual/<run_id>-analysis.md`，**不含响应明文**。
- **关键设计选择（本批新增能力）**：C-15 与 C-16 观测字段**汇入同一条 L1 记录**（`request.state.upstream_observation` → 审计中间件合流），使「网关 500 是网关自身故障还是上游透传」的判定**无需跨行 join**。
- **非目标**：不做响应采集的常开（红线 D-5：默认关 + 生产永久关）；不做请求体侧的额外采集；不推进 D-6 跨仓接线；不改既有接口契约与权限模型；**批 3（C-13/C-14 门禁口径打通）按 D-1 决议仍不做**。
- **执行面界定**：本机（Dev 环境，Python 3.10）沙箱可执行面（代码 / 单测 / 静态质量 / 覆盖率 / TestClient 实跑）**已真实执行并留证**；真实 7 服务在线编排 + 前端人工 E2E 下的开关开启观测不在本次沙箱面（见 §14）。

---

## §2 开发入场检查

| 项 | 检查内容 | 结论 |
|----|---------|------|
| 设计依据就绪 | 方案内部 v1.3.0 [Approved]，§5 批 4 明确 C-15~C-19 文件级落点与验收；§11 已定三开关/脱敏规则/归因矩阵/红线 | 通过 |
| 前置批次落地 | 批 1（C-1~C-9）与批 2（C-10~C-12）已落地并出 DevLogReport（`logs/**/*.jsonl` 落盘、用例上下文字段、`audit_logs` 复用通道） | 通过 |
| 红线可落地 | D-5：默认关 + 开启强制脱敏 + 2KB 上限 + 生产永久关 + 开关留痕——五条均有对应实现点（§15.2/§15.1） | 通过 |
| 现状缺口可复现 | §11.1 实证：`APICallRecord` 无响应字段、proxy 层仅 4 处错误日志 → 原方案**无法观测响应数据**（本批补齐） | 通过 |
| 环境可用 | `python -m ruff`、`python -m pytest`、`python -m pytest --cov` 可用 | 通过 |
| 不变量预检 | ①T6-1（日志不得自动清理）不受影响（本批不新增清理路径）；②测试头非身份头约束不受影响（本批不触碰身份头集合）；③K03/信任链语义不变（本批不改出站头装配） | 通过 |
| 既有测试基线 | 定向面（audit/proxy/identity_t6/settings/auth/app/testing）基线需先取：批 1/批 2 报告已登记「自选子集任意顺序存在既有顺序污染」 | 已知（见 §6.3） |

---

## §3 实现计划（任务清单）

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| T1 | C-18 统一脱敏器 + 单测 | `openbase/core/mask.py`、`tests/test_mask.py` | 完成（21 例） |
| T2 | C-19 三开关 + 生产永久关 + 开关审计留痕 + 单测 | `openbase/settings.py`、`openbase/modules/audit/capture_switches.py`、`openbase/demo_app.py`、`tests/test_capture_switches.py` | 完成（9 例） |
| T3 | C-15 网关响应观测 + 错误码来源补标 + 单测 | `openbase/modules/audit/__init__.py`、`openbase/core/errors/base.py`、`openbase/core/deps/auth.py`、`tests/test_audit_response_observe.py` | 完成（14 例） |
| T4 | C-16 上游响应专段 + 通用代理接线 + 单测 | `openbase/modules/proxy/upstream_observe.py`、`openbase/modules/proxy/__init__.py`、`tests/test_proxy_upstream_observe.py` | 完成（9 例） |
| T5 | C-17 错误归因分析器 + 单测 | `scripts/test_log_analyze.py`、`tests/test_test_log_analyze.py` | 完成（7 例） |
| T6 | 静态质量检查（ruff，含 scripts） | 0 错 | 完成 |
| T7 | 覆盖率与定向回归 | 新模块 99%；定向回归 294 例全绿 | 完成 |
| T8 | 开发记录与文档版本更新 | 本报告 v1.3.0 + 方案 v1.4.0 + 文档地图索引 v1.0.12 | 完成 |

---

## §4 逐项实施记录（RED→GREEN）

> **顺序如实说明**：C-19 与 C-16 为「先写测试 → 见 RED（`ModuleNotFoundError`）→ 实现 → GREEN」；C-15/C-17 为「先写测试 → 直接实现 → 首跑暴露实现缺口 → 修至 GREEN」；C-18 为「实现与单测同批落地」（详见 §6.1 的 RED 复现台账，不伪造 RED）。

### 4.1 C-18 统一脱敏器（`openbase/core/mask.py`，252 行）

| 能力 | 口径 |
|------|------|
| `mask_sensitive(value, *, allowlist, path, depth)` | 递归脱敏：**凭据键**（password/token/secret/api_key/authorization/jwt/… 小写片段匹配）→ `***`（容器值只留类型与规模）；**个人隐私文本**：手机号保前 3 后 4（`138****5678`）、18 位证件号保前 4 后 4、邮箱本地部掩码（`a***@example.com`）；**画像业务域**（portrait(s)/profile(s)/face(s)/avatar）**任何类型**都只留 `{_redacted, type, size}`；**层级 >5** → `<max-depth>`；**允许清单**命中的字段路径（精确或子树前缀）保留原值（错误归因需要） |
| `observe_payload(payload, *, allowlist, max_bytes=2048)` | 响应体观测统一口径：`bytes`/`digest`/`keys`/`summary`/`truncated`/`captured`；**超限（>2KB）或层级过深** → `summary=None`，只留 `digest` + **顶层键名清单**（不存原文）；非 JSON → 只留**脱敏后短预览** |
| `digest_of(payload)` | `sha256:<16 hex>`：只用于「两次响应是否同源」比对，不可逆推原文 |

### 4.2 C-19 三开关与开关审计留痕

- `openbase/settings.py`：新增 `capture_response`/`capture_upstream`/`capture_field_allowlist`（默认 `False/False/""`），并新增三个派生属性：`capture_field_allowlist_list`（逗号解析、去空）、**`capture_response_enabled`/`capture_upstream_enabled`（`env == "production"` 时恒 False → 红线 4「生产永久关闭」）**；
- `openbase/modules/audit/capture_switches.py`（新增 91 行）：`capture_switch_state()`（单一取值来源，避免日志与落库两处口径漂移）、`record_capture_switch_state()`（结构化日志**必发** + 仅「实际生效」时 best-effort 落 `audit_logs`，action `capture.switch`；失败仅 WARN + rollback，**绝不阻断启动**）；
- `openbase/demo_app.py`：新增启动钩子 `_record_capture_switch_state()` 接线（红线 5「开关本身留痕」）。

### 4.3 C-15 网关响应观测（`openbase/modules/audit/__init__.py` 等）

| 变更点 | 说明 |
|--------|------|
| `should_capture_body(content_type)` | 采集判定：仅 `application/json` 且**非** `text/event-stream` 允许读体（保护 SSE 与二进制透传） |
| `build_response_observation(...)` | 纯函数口径：未采集 → `resp_bytes` 取 `Content-Length`、`resp_digest` 为**结构性摘要**（`状态码\|类型\|长度\|错误码` 的 sha256）；已采集 → **真实字节数 + 内容摘要** + 脱敏 `resp_summary`（超限/过深时改带 `resp_keys`） |
| `_observe_response` / `_read_response_body` | 中间件侧：默认关**不读响应体**；开启且为 JSON 时读取并重建同内容响应（读取失败回退元数据口径，**绝不影响业务响应**） |
| `_observation_fields` + `_record`/`_emit_request_log` | 网关观测（C-15）与上游专段（C-16）**合流**进 `extra` 与 L1 JSON 日志（一条记录承载「网关 → 上游」两级） |
| `_persist_audit_record` | `audit_logs.detail` 增补**结构性**字段（`resp_*`/`upstream_*` 结构化子集）；**摘要类不入库**（避免 detail 膨胀与隐私面扩大） |
| `openbase/core/errors/base.py` | 四个统一异常处理器补标 `request.state.error_code`（AUTH_401 / PARAM_422 / HTTP 状态码 / SYS_INTERNAL_ERROR）→ `resp_error_code` 有真实来源 |
| `openbase/core/deps/auth.py` | 中间件**直接构造**的错误响应（missing/invalid token、主体校验失败、非受信身份头 403）同样补标错误码（与异常处理器**同源**，不引入第二套口径） |

### 4.4 C-16 上游响应专段（`openbase/modules/proxy/`）

- `upstream_observe.py`（新增 141 行）：`build_upstream_segment(...)`（成功/业务错误/不可达三路径**共用同一结构**）、`extract_upstream_error_code(...)`（顶层 `code` / `error_code` / `error.code` / `detail.code`，仅取标量，取不到即 None 不臆造）、`publish_upstream_observation(...)`（写入 `request.state.upstream_observation`，同请求多次调用取最近一次并累计 `upstream_calls`）、`elapsed_ms(...)`；
- `proxy/__init__.py` 的 `_forward`：①**不新增日志点**——上游不可达沿用既有 `warning` 并补带同一专段；402 沿用既有 `info` 并补带专段；②新增唯一一处响应后专段装配（覆盖成功与业务错误路径）；③防御式读取 `_upstream_content_type()` / `getattr(upstream, "content", None)`（替身响应缺头不抛错，见 §9#1）。

### 4.5 C-17 错误归因分析器（`scripts/test_log_analyze.py`，316 行）

| 能力 | 口径 |
|------|------|
| `attribute(record)` | §11.5 矩阵逐行落地：网关码（AUTH_* / PERM_UNTRUSTED_IDENTITY_HEADER / PERM_SERVICE_KEY_WRITE_DENIED / 其它 PERM_*）→ 网关层；**上游 4xx/5xx（优先于网关 5xx）** → 上游子系统；502 / `SYS_UPSTREAM_ERROR` → 网络/上游不可达；其余 5xx → 网关/系统；4xx → 网关业务；2xx → 无错误。每层附**可执行建议动作**（指向下一跳证据） |
| `_group_steps` | 按 `(case_id, step_id)` 分组（失败记录优先作代表），标记**首现**（每用例仅第一个失败步骤为「是」，避免连锁噪音当新问题） |
| `render_markdown` | §1 归因表（8 列，与 §11.6 口径一致）+ §2 证据引用（`resp_digest`/`upstream_digest`/`upstream_error_code`，**不含响应明文**）+ §3 口径与边界（补充证据、不参与门禁 D-3） |
| 退出码 | `0` 无失败 / `1` 有失败步骤 / `2` PENDING（无带用例上下文记录，且**不产出**空报告） |

---

## §5 静态质量检查记录

| 检查类别 | 命令或方式 | 结果 | 失败摘要 | 处理 |
|---------|-----------|------|---------|------|
| 语法 / Lint（全量，含脚本） | `python -m ruff check openbase tests scripts` | **通过（All checks passed!）** | 首轮 1 项 `UP012`（不必要的 `encode`） | 改为 bytes 字面量后复检通过 |
| 圈复杂度 | `python -m ruff check --select C901 --config lint.mccabe.max-complexity=12 <本批 6 个文件>` | **通过（0 违规）** | 首轮 `observe_payload` 13 > 12 | 拆出 `_keys_of`/`_decode_json`/`_summary_of_decoded` 三个纯函数后复检通过（并消除超限/过深分支的键名逻辑重复） |
| 代码重复率（近似口径） | 本地 6 行滑窗分片统计（jscpd/pylint 在本环境不可用，见下注） | **通过：0.83%（< 3%）** | — | 重复片段仅常量名/`if not raw:` 等琐碎行，无需处理 |
| 类型检查 | 项目未配置 mypy/pyright（`pyproject.toml` 无类型检查依赖） | **不适用** | — | 以完整类型注解 + 单测覆盖替代；如需可另立引入任务（不擅自新增工具链） |
| 构建检查 | Python 包无独立构建步骤（`pip install -e .` 之外无打包动作） | **不适用** | — | 以「导入链可用」替代：全部新增模块经 TestClient 装配 + 60 例单测实际导入执行 |
| 符号与参数一致性 | 新增/改动的公共符号：`should_capture_body`/`build_response_observation`/`mask_sensitive`/`observe_payload`/`digest_of`/`build_upstream_segment`/`extract_upstream_error_code`/`publish_upstream_observation`/`capture_switch_state`/`record_capture_switch_state`/`attribute` | **通过** | — | 逐符号 grep 核对「定义 ↔ 调用」；无未定义符号、无死引用（观测字段名在 `audit.RESP_FIELD_NAMES`/`UPSTREAM_FIELD_NAMES` 与 `proxy.upstream_observe.UPSTREAM_SEGMENT_FIELDS` 间对齐） |
| 返回值一致性 | `_forward` 返回 `JSONResponse`；观测装配不改返回值；分析器 `main()` 返回退出码 0/1/2 | **通过** | — | 既有 `test_proxy_quota`/`test_proxy_auth` 回归通过（见 §9#1） |
| import / export | `openbase.modules.proxy.upstream_observe` 新模块被 `proxy/__init__` 导入；`capture_switches` 被 `demo_app` 导入 | **通过** | — | 无循环依赖（`upstream_observe` 仅依赖 `core.mask`；`capture_switches` 仅依赖 `settings`/`core`） |
| API / 配置字段一致性 | 三开关环境变量名（`OPENBASE_CAPTURE_RESPONSE`/`OPENBASE_CAPTURE_UPSTREAM`/`OPENBASE_CAPTURE_FIELD_ALLOWLIST`）与方案 §11.3 逐字对齐 | **通过** | — | 单测以 env 名断言（`test_capture_switches_env_override`） |
| 环境与配置安全 | 无真实密钥落文件；未改 `.env*`；新增字段无默认密钥 | **通过** | — | `git status` 无 `.env*` 改动 |
| 数据字段 | 本批**零迁移**（仅写 `audit_logs` 既有 JSON `detail`） | **通过** | — | 归属 D-2=① |
| 状态与枚举 | 新增动作码 `capture.switch`；归因层名称与 `ErrorCode` 枚举值断言对齐 | **通过** | — | `test_record_switch_state_on_persists_audit_row`、`test_credential_headers_are_never_captured`（按枚举取值断言） |
| 架构合规（分层） | 手工核对：`core/mask.py` 不依赖 `modules/**`；`audit`/`proxy` 模块间的观测传递经 `request.state`（框架状态）而非互相导入 | **通过** | — | 无跨层调用、无路由内业务逻辑 |

**结论**：**通过**。
**剩余风险**：①类型检查与构建检查在本项目基线中不适用（未引入对应工具链，未擅自新增）；②重复率检查为**本地近似口径**（jscpd/pylint/radon 未安装），已如实标注；③观测字段名在三处常量表对齐，后续若改名需三处同步（已用常量集中管理降低风险）。
**是否允许进入 `code-logic-review`**：**是**（逻辑审查结论见 §8）。

检查期修复项（均已复检通过）：

| 问题 | 现象 | 修复 |
|------|------|------|
| `UP012` 不必要的 `encode` | `tests/test_mask.py` 对 ASCII 字面量调用 `.encode()` | 改为 bytes 字面量 `b"plain text 13812345678"` |
| 圈复杂度超阈值（C901） | `observe_payload` 复杂度 13（阈值按门禁取 15、本批自设 12） | 拆出 `_keys_of`/`_decode_json`/`_summary_of_decoded`；同时消除超限/过深分支的键名逻辑重复 |

---

## §6 单元测试与回归

### 6.1 本批单测（60 例，全绿）

- 证据：`doc/test/evidence/manual/batch4-unit-junit.xml` → **tests=60 / failures=0 / errors=0 / skipped=0**（75.3s）
- 命令：`python -m pytest tests/test_mask.py tests/test_capture_switches.py tests/test_audit_response_observe.py tests/test_proxy_upstream_observe.py tests/test_test_log_analyze.py -q --junitxml=...`

| 用例文件（对应 C 项） | 例数 | 覆盖要点 |
|----------------------|:----:|---------|
| `tests/test_mask.py`（C-18） | 21 | 凭据键与容器遮蔽、手机号/证件号/邮箱掩码、自由文本内隐私、画像域（object/array/string/int/None）整体遮蔽、域精确匹配不误伤、层级 >5、单条 >2KB、允许清单（精确 + 子树前缀 + 空条目忽略）、digest 稳定性与差异、`None`/空体/标量/数组/非 JSON 边界 |
| `tests/test_capture_switches.py`（C-19） | 9 | 默认全关、env 开启生效、**生产永久关闭**、允许清单解析、开关快照载荷、全关仅日志不落库、开启落 `audit_logs`（action `capture.switch`）、落库失败降级、**rollback 亦失败仍降级**、落库总开关关闭静默 |
| `tests/test_audit_response_observe.py`（C-15） | 14 | 默认关无 `resp_summary` 且有结构性字段、L1 日志同带、开关开启摘要经脱敏（手机号 `138****5678` 且原文不出现）、深层响应只留 `resp_keys`、凭据头不入记录、`should_capture_body` 六种内容类型矩阵、结构性/内容 digest、允许清单透传、`resp_error_code` 取自异常处理器（AUTH_401 / BIZ_404） |
| `tests/test_proxy_upstream_observe.py`（C-16） | 9 | 专段结构性字段、业务错误码提取（顶层 + 嵌套）、不可达同结构、开关摘要经脱敏、过深只留键名、允许清单保留归因字段、`upstream_calls` 计数与最近一次覆盖、**通用代理端到端**（上游 404 → `upstream_*` 与 `resp_status` 同列一条记录） |
| `tests/test_test_log_analyze.py`（C-17） | 7 | 归因矩阵逐行核对（鉴权/信任链/K03/网络/上游/无错误）、上游 5xx 优先归因上游、报告产物与首现标记、**报告不含响应明文**、全绿退出码 0、无记录 PENDING(2) 且不产报告、`--run-id` 过滤 |

**RED 复现台账（如实登记，不伪造）**：

| C 项 | 测试是否先于实现 | RED 证据 | 说明 |
|------|------------------|----------|------|
| C-19 | 是 | `ModuleNotFoundError: No module named 'openbase.modules.audit.capture_switches'` | 收集期即 RED（已实测） |
| C-16 | 是 | `ERROR tests/test_proxy_upstream_observe.py`（模块不存在，收集期失败） | 已实测 |
| C-15 | 是（测试先落盘） | 首跑 3 类缺口：`'Settings' object has no attribute '_settings'`（测试夹具需经 `sys.modules` 取模块，因 `openbase.settings` 被实例遮蔽）、深层响应误判为可摘要、`BIZ_NOT_FOUND` 实际值为 `BIZ_404` | 「先写测试 → 直接实现 → 首跑暴露缺口 → 修至 GREEN」 |
| C-17 | 是（测试先落盘） | 首跑 2 类缺口：报告文件名口径（单轮次应取记录内 run_id）、无记录时不应产出文件 | 同上 |
| C-18 | 否（实现与单测同批） | 首跑 1 处真实失败：超限载荷未产出**顶层键名清单** | **如实说明**：本项未做到严格 RED 先行；失败项已修正并复跑全绿 |

### 6.2 覆盖率（新增模块）

- 命令：`python -m pytest tests/test_mask.py tests/test_capture_switches.py tests/test_proxy_upstream_observe.py tests/test_audit_response_observe.py -q --cov=openbase.core.mask --cov=openbase.modules.audit.capture_switches --cov=openbase.modules.proxy.upstream_observe --cov-report=term-missing`

| 模块 | 语句 | 未覆盖 | 覆盖率 |
|------|:----:|:------:|:------:|
| `openbase/core/mask.py` | 116 | 2 | **98%**（未覆盖：`_max_depth` 的空容器分支） |
| `openbase/modules/audit/capture_switches.py` | 38 | 0 | **100%** |
| `openbase/modules/proxy/upstream_observe.py` | 58 | 0 | **100%** |
| **合计** | **212** | **2** | **99%** |

> 满足 `AGENTS.md` 新增代码覆盖率 ≥90% 门槛。

### 6.3 回归

| 轮次 | 命令 | 结果 | 证据 |
|------|------|------|------|
| 定向回归（**pytest 采集序**，受影响面） | `python -m pytest tests -q -k "audit or proxy or identity_t6 or settings or demo_app or security or test_app or test_auth or test_case_context or logging_setup or test_log or testing_api"` | **294 passed / 0 failed / 0 errors / 0 skipped**（155.6s） | `doc/test/evidence/manual/batch4-regression2-junit.xml` |
| 顺序污染复核（**自定义文件顺序**子集） | `python -m pytest tests/test_audit_db_persist.py tests/test_identity_t6.py -q` | **30 passed / 0 failed** | `doc/test/evidence/manual/batch4-isolated-junit.xml` |

**过程记录（如实）**：首轮自选**自定义文件顺序**的 16 文件子集出现 16 例失败（`test_audit_db_persist` 3 例 + `test_identity_t6` 13 例，均为 `sqlite3.OperationalError: no such table: openbase.file_records` 类**建表/夹具**问题，非断言失败）。处置：①单独复跑二者 → **30 例全绿**；②改用 **pytest 采集序**重跑受影响面 → **294 例全绿**；③本批**未触碰** DB engine/session/建表路径（`git diff` 可核）。结论：与批 1 §14-9 已登记的「自选子集任意顺序存在既有跨文件顺序污染」一致，**与批 4 改动无关**，属既有环境/夹具风险，登记不改代码。

---

## §7 实跑验证

**可执行面（沙箱内真实执行，非伪造）**：

| 项 | 命令/方式 | 实测结果 |
|----|-----------|---------|
| 默认关（零采集） | TestClient 请求 `GET /api/v1/test-runs/run-x/summary`（无 token） | 401；审计记录含 `resp_status=401`/`resp_error_code=AUTH_401`/`resp_digest`/`resp_bytes`，**无 `resp_summary`** |
| 开关注入 + 脱敏生效 | 置 `OPENBASE_CAPTURE_RESPONSE=1`，提交含手机号的语义错误入参（422） | 422；`resp_summary` 存在，记录中**手机号原文不出现**、掩码值 `138****5678` 出现 |
| 深层响应保护 | 置开启，请求用例摘要（嵌套 >5 层） | 仅 `resp_keys` + `resp_digest`，**无 `resp_summary`** |
| 凭据不落审计 | 开启下带 `Authorization` 请求 | 记录整体不含 token 原文；`resp_error_code=BIZ_404` |
| 上游专段（端到端） | 通用代理 `GET /api/v1/proxy/dps/api/v2/portrait/list`（httpx 替身返回 404/`BIZ_404`） | 网关 404；记录同列 `upstream_system=dps`/`upstream_status=404`/`upstream_error_code=BIZ_404`/`upstream_duration_ms`/`upstream_calls=1` 与 `resp_status=404` |
| 开关审计留痕 | 开启 + 假会话工厂 | `audit_logs` 增 1 行（action `capture.switch`，detail 含三开关与生效标记） |
| 归因分析器（构造轮次） | 混合轮次（403 信任链 / 502 / 上游 500 / 200） | 报告 `run-analyze-1-analysis.md` 生成，含「网关信任链 / 网络/上游不可达 / 上游子系统」三归属层 + 首现标记 + `sha256:` 摘要引用；退出码 **1**；全绿轮次退出码 **0**；无记录退出码 **2** 且不产文件 |
| 归因分析器（**真实轮次**） | `python scripts/test_log_analyze.py --run-id run-20260914-0230`（批 1 真实落盘日志） | 退出码 **0**；`steps=3 / failed=0`；报告 `doc/test/evidence/manual/run-20260914-0230-analysis.md` 生成 |
| 归因分析器（**真实失败轮次**） | `python scripts/test_log_analyze.py --run-id run-20260914-0225`（批 1 真实落盘日志，含 404 步骤） | 退出码 **1**；`steps=2 / failed=1`；归属层「无错误 + 网关业务」，建议动作指向「按错误码核对请求参数与业务前置条件」；报告 `run-20260914-0225-analysis.md` 生成 |

> **真实轮次报告的字段边界（如实说明）**：`run-20260914-0230`/`0225` 的日志产生于**批 1**（早于 C-15/C-16 落地），故其 `resp_digest`/`upstream_*` 列均为 `-`（日志行中本就无这些字段）——归因表仍可工作（依赖 `status_code`/`resp_error_code`）。批 4 之后产生的轮次将同时具备两级观测字段。

**沙箱外（PENDING，登记不伪造）**：

| 项 | 内容 | 处置 |
|----|------|------|
| 真实编排窗口的人工 E2E | 7 服务在线 + 前端 `/system/test-records` 下**开启开关**采集真实响应摘要与归因报告 | 待联调窗口执行（§14） |
| 专用代理族上游专段 | `dps_proxy`/`rag_proxy`/`llm_proxy`/`memory_proxy` 的 `_forward` 接线（需传 `Request`） | 待下一步（§14） |
| 性能影响 | 摘要采集（含 JSON 解析 + 脱敏 + sha256）对 P99 的影响未量化 | 待压测窗口（§14，承批 1/批 2 同项） |
| `service-orchestrator checkall` | 批 1 基线 27 PASS 全量复跑 | 待联调窗口（§14，承批 2 同项） |

---

## §8 代码逻辑审查记录

| 审查点 | 结论 |
|-------|------|
| 分层与职责 | 脱敏器在 `core/`（跨模块共用）；观测装配在 `audit`（网关侧）与 `proxy`（上游侧）各自模块内；分析器为 `scripts/` 只读工具。未在路由层写业务逻辑，未跨层调用 |
| 红线合规（D-5） | ①默认关：`should_capture_body` 不被调用即不读体（`capture_response_enabled` 判定在前）；②开启强制脱敏：摘要唯一出口是 `observe_payload`→`mask_sensitive`，无旁路；③2KB 上限与层级 >5 只留 digest + 键名；④生产永久关（属性级恒 False）；⑤开关留痕（启动快照 + `capture.switch` 审计行） |
| 日志与隐私 | 摘要类字段**不入** `audit_logs.detail`；`Authorization` 等敏感头沿用既有 `SENSITIVE_HEADERS` 过滤（有专项用例）；digest 为单向摘要，不构成原文泄漏 |
| 错误码规范 | 新增错误码标注（`request.state.error_code`）不改变响应体契约；分析器判定码值与 `ErrorCode` 枚举一致（用例按枚举取值断言，避免魔法值） |
| 错误处理 | 响应体采集失败 → 回退元数据口径（不抛错）；开关审计落库失败 → WARN + rollback，**不阻断启动**；上游观测装配**不改变**既有 forward/402/降级语义 |
| 并发与状态 | 观测随请求（`request.state`）生命周期存活，无跨请求共享；`upstream_calls` 仅在单请求内累加；开关为进程级只读配置（不热更），无竞态 |
| 内存与性能 | 仅开启时读取响应体（并限 JSON），关闭路径零额外拷贝；`observe_payload` 对超限/过深提前返回，避免深拷贝大结构 |
| 不变量 | 未新增任何自动清理路径（T6-1 不变量不受影响）；未修改身份头常量与裁剪集 |
| 命名与可读性 | 模块/函数 snake_case、常量 UPPER_SNAKE_CASE、无单字母变量（循环 `i` 除外）；纯函数与中间件方法职责单一，观测口径集中在 `build_*` 纯函数（便于单测与复用） |
| 回归风险点 | `_forward` 改动触及核心转发路径 → 已用替身响应覆盖（`test_proxy_quota` 触发并修复，见 §9#1）；审计中间件改动 → 定向回归 294 例覆盖 |

---

## §9 问题修复与复审记录

| # | 问题 | 处置 | 复审 |
|---|------|------|------|
| 1 | `tests/test_proxy_quota.py` 两例失败：`'_FakeResponse' object has no attribute 'headers'`（本批 `_forward` 新增读取上游 `Content-Type`，既有替身无该属性） | 生产侧改为**防御式读取**：新增 `_upstream_content_type(response)`（缺头/替身 → None）与 `getattr(upstream, "content", None)`，**不修改既有测试替身** | `pytest tests/test_proxy_quota.py tests/test_proxy_auth.py tests/test_proxy_upstream_observe.py` 全绿；定向回归 294 例全绿 |
| 2 | 超限载荷未产出顶层键名清单（C-18 首跑失败） | `observe_payload` 调整：先解析 JSON 取键名，再按「超限 → summary=None」返回 | `test_oversized_payload_keeps_digest_and_keys_only` 等转绿；覆盖率 98% |
| 3 | 深层响应（嵌套 >5）被误当作可摘要（C-15 首跑暴露） | 新增 `_max_depth` 前置判定：层级过深 → 与超限同口径（只留 digest + 键名清单） | `test_deep_response_keeps_keys_only`、`test_oversized_and_deep_array_payloads_keep_array_marker` 转绿 |
| 4 | 测试夹具取 `openbase.settings` 模块失败（`'Settings' object has no attribute '_settings'`：包命名空间被实例遮蔽） | 夹具改经 `sys.modules["openbase.settings"]` 取模块并做「重置 → 还原」隔离 | C-15 14 例全绿 |
| 5 | 断言口径错位：`BIZ_NOT_FOUND` 实际枚举值为 `BIZ_404`；`resp_error_code` 对中间件直出错误为 None | ①用例改为按 `ErrorCode` 枚举断言；②`AuthMiddleware` 两处错误响应补标 `request.state.error_code`（与异常处理器同源） | 断言修正后转绿；中间件直出 401 的 `resp_error_code=AUTH_401` 已实测 |
| 6 | 自定义顺序子集 16 例夹具失败（sqlite 建表） | 单独复跑 30 例全绿 + 改用 pytest 采集序 294 例全绿；判定既有顺序污染（批 1 §14-9），不改代码 | 见 §6.3 |
| 7 | 画像域键持有标量（如 `avatar: 42`）时原实现回落原值 | 收紧为「画像域**任何类型**只留类型与规模」 | `test_redacted_domain_scalar_and_array_values_keep_shape_only` 转绿 |
| 8 | 圈复杂度：`observe_payload` 13（`ruff C901` 阈值 12 报violation） | 拆出 `_keys_of`/`_decode_json`/`_summary_of_decoded` 三个纯函数；顺带消除「超限」与「过深」两分支的键名逻辑重复 | `ruff check --select C901`（阈值 12）0 违规；60 例单测复跑全绿；覆盖率 99% 保持 |

---

## §10 设计开发追溯矩阵

| 设计条目 | 设计要求 | 实现落点 | 验证证据 |
|---------|---------|---------|---------|
| 方案 §5 C-18（统一脱敏器） | 凭据/隐私/画像域/超限与过深；落盘前必经 | `openbase/core/mask.py`（`mask_sensitive`/`observe_payload`/`digest_of`） | `tests/test_mask.py` 21 例；覆盖率 98% |
| 方案 §11.2 红线 1（默认关） | 未开启零采集零落盘 | `settings.capture_*`（默认 False）+ `_observe_response` 前置判定 | `test_response_summary_absent_when_switch_off`、`test_capture_switches_default_off` |
| 方案 §11.2 红线 2（开启强制脱敏） | 摘要必经 C-18 | `build_response_observation`→`observe_payload`→`mask_sensitive`（唯一出口） | `test_summary_captured_and_masked_when_switch_on`、`test_segment_capture_masks_summary` |
| 方案 §11.2 红线 3（2KB 上限） | 超限只留 digest + 键名清单 | `observe_payload(max_bytes=2048)` | `test_oversized_payload_keeps_digest_and_keys_only` |
| 方案 §11.2 红线 4（生产永久关） | production 恒关 | `capture_response_enabled`/`capture_upstream_enabled` 属性 | `test_capture_is_permanently_off_in_production` |
| 方案 §11.2 红线 5（开关留痕） | 开关变更记审计 | `capture_switches.record_capture_switch_state` + `demo_app` 启动钩子 | `test_record_switch_state_on_persists_audit_row`（action `capture.switch`） |
| 方案 §11.4（脱敏规则） | 凭据/隐私/画像/超限与过深 | `mask_sensitive` + `_summary_of_value` + `_max_depth` | `test_mask.py` 全量 21 例 |
| 方案 §11.3（三开关） | 三开关默认关 + 允许清单默认空 | `settings.py`（含 `capture_field_allowlist_list`） | `test_capture_switches_env_override`、`test_allowlist_keeps_raw_value_for_attribution` |
| 方案 §5 C-15（网关响应摘要） | 结构性字段恒记 + 开关摘要 + `resp_error_code` | `audit/__init__.py`（`should_capture_body`/`build_response_observation`/`_observe_response`）+ `errors/base.py` + `deps/auth.py` | `tests/test_audit_response_observe.py` 14 例 |
| 方案 §5 C-16（上游响应专段） | 字段齐备；成功/业务错误/异常统一；不新增日志点 | `proxy/upstream_observe.py` + `proxy/__init__.py::_forward` | `tests/test_proxy_upstream_observe.py` 9 例；覆盖率 100% |
| 方案 §11.5（归因矩阵） | 六类归因口径 | `scripts/test_log_analyze.py::attribute` | `test_attribute_matrix_covers_design_rows`、`test_attribute_prefers_upstream_over_gateway_5xx` |
| 方案 §11.6（分析器输出） | 按 step 一行一结论 + 首现 + 建议动作；落 `<run_id>-analysis.md` | `render_markdown`/`_group_steps`/`main` | `test_analyze_writes_report_with_attribution`、`test_analyze_no_records_is_pending` |
| 方案 §6（红线合规验收） | 关时 0 条摘要；开时敏感字段 0 命中 | 采集前置判定 + C-18 唯一出口 | §7 实跑：关闭无摘要；开启原文不出现、掩码出现 |
| 方案 D-3（补充证据定位） | 人工结论不参与门禁 | 分析器报告 §3 显式声明 + 不串入门禁打分 | `render_markdown` 固定文案 + 代码无门禁耦合 |
| `AGENTS.md` 测试规则 | TDD + 新代码覆盖率 ≥90% + ruff 0 错 | 60 例单测 / 99% 覆盖 / ruff 0 错 | §5、§6 |

---

## §11 变更统计与影响文件清单

> 统计范围：**仅本批（批 4）实际修改/新增的文件**；不含工作区既有未提交与历史文件。行数口径：修改文件取 `git diff --numstat`；新增文件取文件行数。

### 11.1 生产代码

| 文件 | 类型 | 变更性质 | 新增行 | 删除行 | 说明 |
|------|------|---------|-------|-------|------|
| `openbase/core/mask.py` | 生产代码 | **新增** | 315 | 0 | C-18 统一脱敏器（脱敏 / 观测载荷 / digest；含圈复杂度拆分后的纯函数） |
| `openbase/modules/audit/capture_switches.py` | 生产代码 | **新增** | 91 | 0 | C-19 开关状态快照 + `capture.switch` 审计留痕 |
| `openbase/modules/proxy/upstream_observe.py` | 生产代码 | **新增** | 141 | 0 | C-16 上游专段构造 / 错误码提取 / 请求内汇聚 |
| `openbase/modules/audit/__init__.py` | 生产代码 | 修改 | 280 | 25 | C-15 响应观测 + C-16 观测合流 + 落库 detail 扩展 |
| `openbase/modules/proxy/__init__.py` | 生产代码 | 修改 | 44 | 2 | C-16 `_forward` 三路径补记 + 防御式读取 |
| `openbase/settings.py` | 生产代码 | 修改 | 33 | 0 | C-19 三开关与派生属性（生产永久关） |
| `openbase/core/errors/base.py` | 生产代码 | 修改 | 11 | 0 | C-15 异常处理器补标错误码 |
| `openbase/core/deps/auth.py` | 生产代码 | 修改 | 13 | 7 | C-15 中间件直出错误响应补标错误码 |
| `openbase/demo_app.py` | 生产代码 | 修改 | 14 | 0 | C-19 启动开关留痕接线 |

**生产代码小计**：新增 **547 行**（3 个新文件：`mask.py` 315 + `capture_switches.py` 91 + `upstream_observe.py` 141）；修改 **395 行新增 / 34 行删除**（6 个文件：`audit/__init__.py` 280/25、`proxy/__init__.py` 44/2、`settings.py` 33/0、`deps/auth.py` 13/7、`errors/base.py` 11/0、`demo_app.py` 14/0）。

### 11.2 脚本与工具

| 文件 | 变更性质 | 行数 | 说明 |
|------|---------|------|------|
| `scripts/test_log_analyze.py` | **新增** | 316 | C-17 错误归因分析器（CLI + 归因矩阵 + 报告渲染） |

### 11.3 测试代码

| 文件 | 变更性质 | 行数 | 说明 |
|------|---------|------|------|
| `tests/test_mask.py` | **新增** | 220 | C-18 单测 **21 例** |
| `tests/test_capture_switches.py` | **新增** | 190 | C-19 单测 **9 例**（含假会话/回滚降级替身） |
| `tests/test_audit_response_observe.py` | **新增** | 218 | C-15 单测 **14 例** |
| `tests/test_proxy_upstream_observe.py` | **新增** | 233 | C-16 单测 **9 例**（含 httpx 替身端到端） |
| `tests/test_test_log_analyze.py` | **新增** | 221 | C-17 单测 **7 例** |

> 行数为终态实测（`(Get-Content <file>).Count`）；测试代码合计 **1082 行 / 60 例**。

### 11.4 文档与证据

| 文件 | 变更性质 | 说明 |
|------|---------|------|
| `doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.3.0.md` | **新增（本报告）** | 批 4 开发记录 |
| `doc/design/OpenBase-人工端到端测试日志记录方案-v1.0.0.md` | 修改（内部 v1.3.0 → **v1.4.0**） | §5.1 批 4 进度行 + 实施期补充（digest 口径 / 启动期置开关 / 接线范围）+ 关联文档 + 修订历史 |
| `doc/design/OpenBase-文档地图索引-v1.0.0.md` | 修改（内部 v1.0.11 → **v1.0.13**） | 登记批 2/批 4 DevLogReport、方案条目至 v1.4.0、增补 C-17 分析器与批 4 证据、DOCMAP-MANIFEST 增补 5 条；v1.0.13 追加旧版归档与索引路径同步 |
| `doc/development/archive/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.1.0.md` | **归档（移动，内容零改动）** | 批 1 记录按版本管理流程移入 archive（只读） |
| `doc/development/archive/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.2.0.md` | **归档（移动，内容零改动）** | 批 2 记录按版本管理流程移入 archive（只读） |
| `doc/test/evidence/manual/batch4-unit-junit.xml` | **新增（运行期证据）** | 60 例单测 JUnit 证据 |
| `doc/test/evidence/manual/batch4-regression2-junit.xml` | **新增（运行期证据）** | 定向回归 294 例 JUnit 证据（pytest 采集序） |
| `doc/test/evidence/manual/batch4-isolated-junit.xml` | **新增（运行期证据）** | 顺序污染复核 30 例 JUnit 证据 |
| `doc/test/evidence/manual/batch4-regression-junit.xml` | **新增（运行期证据，过程留痕）** | 首轮自定义顺序子集 174 例（16 例夹具失败）的**过程证据**，用于 §6.3 复核说明，**不作为通过依据** |
| `doc/test/evidence/manual/run-20260914-0230-analysis.md` | **新增（运行期证据）** | 归因分析器在**真实 PASS 轮次**上的产物（退出码 0） |
| `doc/test/evidence/manual/run-20260914-0225-analysis.md` | **新增（运行期证据）** | 归因分析器在**真实 FAIL 轮次**上的产物（退出码 1，归属层「网关业务」） |

---

## §12 开发审计移交材料

| 移交项 | 内容 | 位置 |
|-------|------|------|
| 设计条目 → 实现映射 | §10 追溯矩阵（C-15~C-19 逐项 + 五条红线 + 归因矩阵 + 验收口径） | 本报告 §10 |
| 静态质量证据 | `ruff check openbase tests scripts` 0 错（含 1 项修复复审） | 本报告 §5、§9#1 |
| 单测与覆盖证据 | 60 例全绿（JUnit 留痕）+ 新模块覆盖率 99%（`mask` 98% / `capture_switches` 100% / `upstream_observe` 100%） | 本报告 §6.1、§6.2 |
| 回归证据 | 定向回归 294 例全绿（pytest 采集序）+ 顺序污染复核 30 例全绿 + 过程失败如实留痕 | 本报告 §6.3 |
| 实跑证据 | 默认关零采集 / 开启脱敏 / 深层保护 / 上游专段同列 / 开关审计行 / 分析器退出码 0-1-2 | 本报告 §7 |
| 变更统计 | 生产 3 新 + 6 改；脚本 1 新；测试 5 新；文档 2 改 + 1 新；证据 4 新 | 本报告 §11 |
| 未闭环项 | 真实编排窗口人工 E2E（开关开启）、专用代理族接线、性能量化、`checkall` 复跑 | 本报告 §14 |

**审计要点提示**：①本批**新增能力全部默认关闭**（生产永久关）→ 对既有业务与生产流量**零行为变化**；②开启路径的唯一摘要出口是 C-18 脱敏器（无旁路，可静态核对）；③响应摘要**不入** `audit_logs.detail`，入库仅结构性字段；④`_forward` 为核心路径 → 既有替身用例触发并已修复（§9#1），定向回归全绿；⑤§14 四项沙箱外执行项为 PENDING，未伪造。

---

## §13 测试移交说明

| 项 | 内容 |
|----|------|
| 新增测试 | `tests/test_mask.py`(21) / `tests/test_capture_switches.py`(9) / `tests/test_audit_response_observe.py`(14) / `tests/test_proxy_upstream_observe.py`(9) / `tests/test_test_log_analyze.py`(7)，合计 **60 例** |
| 执行命令 | `python -m pytest tests/test_mask.py tests/test_capture_switches.py tests/test_audit_response_observe.py tests/test_proxy_upstream_observe.py tests/test_test_log_analyze.py -q`；`python -m ruff check openbase tests scripts`；`python -m pytest tests -q -k "<受影响面>"` |
| 环境前置 | 无需推理服务与真实 PG：DB 落库用 `OPENBASE_AUDIT_DB_PERSIST` 开关 + 假会话工厂；开关用 `monkeypatch.setenv` + Settings 单例重置；代理用 httpx 替身（不触网） |
| 测试隔离 | C-15 用例 autouse 夹具「重置 Settings 单例 → 还原」+ 清空 `AuditService._records`；C-19 用例独立假会话；分析器用例全部落 `tmp_path`（不污染仓库证据目录） |
| 覆盖口径 | 对**新增模块** `openbase.core.mask` / `openbase.modules.audit.capture_switches` / `openbase.modules.proxy.upstream_observe` 合计 99% |
| 建议后续测试 | ①联调窗口：开关开启下的真实响应摘要与 `<run_id>-analysis.md` 产物复核；②专用代理族接线后的上游专段用例；③摘要采集对 P99 的压测；④`checkall` 27 项复跑 |
| 已知环境干扰 | 自定义文件顺序的自选子集会触发 sqlite 夹具顺序污染（本批已复核并改用 pytest 采集序；承批 1 §14-9）；共享 PG 抖动（承批 1 §14-10） |

---

## §14 遗留与下一步

| # | 类别 | 内容 | 处置 |
|---|------|------|------|
| 1 | 沙箱外 PENDING | 真实 7 服务 + 前端人工 E2E 下**开启开关**采集真实响应摘要与归因报告 | 待编排器联调窗口执行并留证 |
| 2 | 接线范围 PENDING | 专用代理族（`dps_proxy`/`rag_proxy`/`llm_proxy`/`memory_proxy`）上游专段接线（需把 `Request` 传入其 `_forward`，本批为避免大范围改动核心路径未做） | 下一步（建议与批 4 收尾一并评审）；当前这些通道仅具 C-15 网关侧字段 |
| 3 | 性能 PENDING | 摘要采集（JSON 解析 + 脱敏 + sha256）对请求尾耗时/P99 的影响未量化；承批 1 §14-1、批 2 §14-4 | 随压测窗口统一量化 |
| 4 | 沙箱外 PENDING | `service-orchestrator checkall` 27 PASS 复跑（承批 2 §14-3） | 待联调窗口 |
| 5 | 口径提示（非缺陷） | 网关侧 `resp_digest` 在**未采集**时为结构性摘要、采集后为内容摘要；上游侧恒为内容摘要 | 已在方案 v1.4.0 §5.1 实施期补充显式登记 |
| 6 | 运行约束（非缺陷） | 采集开关需**进程启动时**设置（Settings 启动读取 env，进程内不热更）；变更以启动快照留痕 | 已在方案 v1.4.0 登记；如需热更，另立需求（涉及动态配置面） |
| 7 | 环境 | 自定义顺序子集触发 sqlite 夹具顺序污染（16 例，单独跑即绿）；共享 PG 抖动 | 环境风险登记，不改代码（承批 1 §14-9/§14-10） |
| 8 | 文档版本管理 | 本批将 DevLogReport 升至 v1.3.0、方案升至 v1.4.0、文档地图索引升至 **v1.0.13**；按规范旧版报告已归档 | **已执行（人工确认后）**：`v1.1.0`（批 1）/`v1.2.0`（批 2）移入 `doc/development/archive/`（只读，内容零改动），工作目录仅保留 `v1.3.0`；索引 §2.5/清单路径同步为归档路径 |
| 9 | 下一步 | 批 3（C-13/C-14 门禁口径打通）按 D-1 决议**不做**；D-6 四仓 request_id 接线为独立跨仓任务（各仓走自身流程） | 待人工决议 |

---

## §15 批 4 实施记录（C-15~C-19）

> 本节记录 v1.3.0 新增部分。执行纪律同前：**TDD（RED→GREEN，顺序如实见 §6.1）**、证据真实、未执行项 PENDING。

### 15.1 C-18 统一脱敏器细节

- 敏感键片段与 `logging_setup.SENSITIVE_KEY_FRAGMENTS` 口径一致并扩充（`jwt`/`signature`/`bearer`），避免两套脱敏名单漂移；
- 隐私正则作用于**值文本**（不作用于键名）：手机号 `(\d{3})\d{4}(\d{4})` → 前 3 后 4；18 位证件号 → 前 4 后 4；邮箱 → 本地部 `首字符 + ***`；
- 画像域采用**精确匹配**（`portrait`/`portraits`/`profile`/`profiles`/`face`/`faces`/`face_image`/`avatar`），显式避免 `portrait_count` 之类统计字段被误伤（有用例锁定）；
- 允许清单支持**精确路径**与**子树前缀**（`error` 命中 `error.code`），空条目忽略；
- `digest_of` 输出 `sha256:<16 hex>`：用于「两次响应是否同源」比对，不存原文也能比对。

### 15.2 C-19 三开关与留痕细节

- 三开关经 `pydantic-settings` 的 `OPENBASE_` 前缀映射（`capture_response` → `OPENBASE_CAPTURE_RESPONSE` 等），**默认全关**；
- 「实际生效值」由属性给出（`env == "production"` 恒 False）——调用方只读属性，避免各处重复判断导致红线遗漏；
- `capture_switch_state()` 为日志与落库的**唯一取值来源**（防两处口径漂移）；
- `record_capture_switch_state()`：**日志必发**（便于排查「开关到底是不是开的」）；**落库仅在生效时**（生产全关 → 零写入）；落库与回滚失败均仅 WARN；
- 启动钩子位于 `demo_app`（`@app.on_event("startup")`），与既有 identity outbox 钩子并列，不改变既有启动语义。

### 15.3 C-15 网关响应观测细节

- **零采集判定在最前**：`settings.capture_response_enabled` 为假 → **不进入** `_read_response_body`（连体都不读），仅产出结构性字段；
- **读体范围保守**：仅 `application/json` 且非 `text/event-stream`；读体后**重建同内容响应**（剔除 `content-length`/`content-type` 后由框架按实际内容生成），保证透传等价；
- **错误码单一来源**：异常处理器与 `AuthMiddleware` 直出错误响应**两处都**标注 `request.state.error_code`，`_observe_response` 只读该值，不重复解析响应体；
- **合流**：`_observation_fields()` 把 C-15 与 C-16 字段合并进 `extra` 与 L1 payload（同一条 `api.request` 记录）；
- **落库裁剪**：`STRUCTURAL_DETAIL_FIELDS` 白名单决定入库字段（摘要类与键名类不入库）。

### 15.4 C-16 上游专段细节

- 三路径共用 `build_upstream_segment`：**成功**（status/content-type/digest/error_code）→ **业务错误**（同上，另有 `upstream_error_code`）→ **不可达**（无 status/digest，有 `upstream_error`）；
- 业务错误码提取覆盖四种契约键位（`error_code`/`code`/`error.code`/`detail.code`），仅接受标量；**取不到即 None**（不臆造）；
- 「不新增日志点」的落地方式：不可达与 402 两条既有日志**补带同一专段字典**，响应后专段装配为唯一新增代码点（无重复日志行）；
- 同请求多次上游调用（聚合场景）：`publish_upstream_observation` 保留最近一次并累计 `upstream_calls`，便于定位「聚合链路中哪个上游先坏」；
- **接线范围**：本批落在通用代理 `proxy/__init__.py::_forward`（方案指定落点）；专用代理族接线见 §14#2。

### 15.5 C-17 分析器细节

- 输入面仅认「C-1 formatter 结构化行」+ 带 `case_id` 的记录（无 case 上下文的记录不参与，避免把运维流量当测试步骤）；
- 每 `(case_id, step_id)` 一行：**失败记录优先**作代表（PASS 记录的 200 不掩盖同步骤的失败）；
- 「首现」= 每用例第一个失败步骤 → 后续失败多为连锁噪音（报告显式说明）；
- 报告三段：归因表（8 列，与 §11.6 一致）→ 证据引用（digest/错误码，**不含明文**）→ 口径与边界（含「补充证据、不参与门禁」D-3 声明）；
- 退出码与聚合脚本同族（0/1/2），便于串入人工测试脚本链；**无记录不产空报告**（避免证据污染）。

### 15.6 与既有权重的正交性

| 既有面 | 本批影响 |
|--------|---------|
| 审计中间件既有语义（C-3/C-4） | 仅**追加**字段（`resp_*`/`upstream_*`）；用例上下文、落库降级、身份 extra 语义不变 |
| `audit_logs` 表结构 | 零迁移（结构字段进 JSON `detail`），承 D-2=① |
| 出站身份头与信任链（P2-1/K03） | **未改动**（本批不触碰身份头常量与裁剪集） |
| 前端（批 2 C-11/C-12） | **未改动**（批 4 为纯后端 + 脚本批） |
| T6-1 日志不变量 | 未新增自动清理路径；定向回归含 `test_identity_t6.py` 全绿 |

---

> 结束：批 4（C-15~C-19）开发记录完成。沙箱可执行面结论：单测 60 例全绿 + 新模块覆盖率 99% + `ruff` 0 错 + 定向回归 294 例全绿；四项沙箱外执行项（真实开关观测 E2E / 专用代理族接线 / 性能量化 / checkall 复跑）登记 PENDING，未伪造；**RED 顺序按项如实登记**（C-18 未做到严格 RED 先行，已在 §6.1 说明）。

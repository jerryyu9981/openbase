# OpenBase-人工端到端测试日志记录方案-v1.0.0

## 文档元信息

| 项 | 内容 |
|------|-----|
| 文档编号 | OB-DESIGN-MANUAL-E2E-LOG-v1.0.0 |
| 版本 | v1.1.0 |
| 状态 | **[Approved]（2026-09-13 决议冻结：D-1~D-6 全部确认，见 §9.1）** |
| 作者 | AI（S7 批次 31 方案编制会话） |
| 日期 | 2026-09-13 |
| 适用范围 | 人工端到端测试（统一前端 → 各后端服务）期间的**结果记录与复盘**；不改动业务语义 |
| 关联文档 | 《OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0》（v1.0.23）；《OpenBase-文档地图索引-v1.0.0》（v1.0.8）；可观测性标准（日志/指标/追踪三大支柱） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-13 | AI（S7 批次 31） | 初始版本：现状核查（4 处缺口）+ 三层记录通道设计 + 字段/事件字典 + 用例上下文贯穿 + 人工结论记录三方案对比 + 文件级改造清单 + 验收标准 + 待决策项 |
| v1.0.1 | 2026-09-13 | AI（S7 批次 32） | **补齐「响应级观测与错误归因」并确认合规红线（D-5）**：经逐行核查 `APICallRecord`（无响应字段）与 proxy 层 5 处日志点（仅 K03/服务密钥写拒绝/上游不可达/402，**上游正常与业务错误响应未留痕**），确认原方案**无法观测子系统响应数据**；新增 §11（响应采集三开关、脱敏规则、上游响应字段、错误归因矩阵、分析器输出）与 §5 批 4（C-15 网关响应摘要 / C-16 上游响应专段 / C-17 错误归因分析器 / C-18 统一脱敏器）；§4.2 增 `resp_*`/`upstream_*` 字段族；§6 增响应级归因率与红线合规验收；§7 增合规风险行；§9 增 D-5（**已确认：默认关闭 + 开启强制脱敏**） |
| v1.0.2 | 2026-09-13 | AI（S7 批次 33 跨仓前提核实会话） | **跨仓前提实测核实并入（§11.8）**：前提 1（子进程日志可被编排器捕获）**四仓 PASS、无需改动**（DPS `src/main.py:37-41` stderr / OpenLLM `backend/main.py:80-83` stderr / OpenRAG `repository/config/logging.py:58-63` stdout / OpenMemory `api/server.py:788-791` stderr）；前提 2（日志带 request_id）**四仓均未打通、需各自最小改动**（DPS 死接线 / OpenLLM 只进审计 DB / OpenMemory 仅差 `structured_log.py:26` 一行 / OpenRAG 全仓零匹配且中间件未注册）。新增 §9 D-6（是否推动四仓补接线）；顺带登记两处既有缺口（OpenRAG 请求日志中间件未注册、OpenMemory 启动路径可能不配置日志）。**本仓仅更新方案文档，未改动业务代码** |
| v1.1.0 | 2026-09-13 | AI（S7 批次 34 决议冻结会话） | **决策全部冻结，方案置 [Approved]**：D-1=②（批 1+批 2，批 3 不做）/ D-2=①（复用 `audit_logs`，零迁移）/ D-3=①（人工记录仅作补充证据、不参与门禁）/ D-4=①（复用既有编号 + `AD-HOC-` 兜底）/ D-5=①（默认关闭 + 开启强制脱敏，硬约束）/ D-6=②（推动四仓补齐 request_id 接线，独立跨仓任务、不阻塞本仓）。新增 §9.1 决议记录，并冻结实施顺序（批 1 → 批 2 → 批 4）与首个里程碑（C-1 + C-6）。状态由 [Draft] 升为 [Approved]。**本次仅文档定稿，代码实施自下一批次开始** |

---

## §1 背景与目标

### 1.1 背景

当前人工端到端测试（例如按 [61 页逐服务清单](computer://d:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\s6\ui-e2e-all-services.json) 逐页点检、或按 S0-S6 冒烟用例逐条验证）的**结果只存在于测试者脑子里或临时记录中**：服务侧虽有结构化日志调用，但既不落文件、也无法按「用例」维度检索，测试结束后无法复盘、无法对账、无法形成可审计证据。

### 1.2 目标

1. **每次人工测试的结果可被日志完整记录**，且能按「run（测试轮次）→ case（用例）→ step（步骤）」三级检索；
2. 每条记录可与**网关请求级记录**（`request_id`）关联，形成「人判定 ↔ 系统客观响应」双证据；
3. 记录具备**持久性**（服务重启不丢）与**可聚合性**（一键生成与既有 evidence 同构的报告）；
4. 严格遵守日志规范：结构化、分级、**不记录密码/令牌/密钥/完整请求体/个人隐私**。

### 1.3 非目标

- 不替代现有自动化证据链（Playwright E2E / s7 冒烟 / 门禁聚合），人工记录是其**补充**；
- 不引入外部可观测性栈（Loki/Jaeger 等），本方案只解决「本地联调期人工测试留痕」；
- 不做业务语义变更（不改接口契约、不改权限模型）。

---

## §2 现状核查（缺口与证据）

> 结论：**做人工测试留痕这件事，当前基础设施缺 4 块**。以下均为代码实证（文件 + 行号）。

| # | 缺口 | 证据 | 影响 |
|---|------|------|------|
| **G-1** | **无任何 logging 配置**：全仓无 `basicConfig` / `dictConfig` / `Handler` / `Formatter` / 级别配置 | `openbase/` 下 grep 上述关键词**零命中** | 代码里 `logger.info("...", extra={...})` 的结构化字段**在默认 formatter 下不落盘**（只输出 message），且无文件输出、无轮转、无级别开关 → 人工测试期间**无处可查** |
| **G-2** | **服务日志未采集**：编排器启动子进程用 `Start-Process -WindowStyle Hidden -PassThru`，**不重定向 stdout/stderr** | `scripts/service-orchestrator.ps1:331`；`logs/` 目录实测仅 `logs/service-orchestrator/orchestrator-YYYYMMDD.log` | 子系统与 OpenBase 进程的 stdout/stderr 全部丢失；日志库里连「服务启动是否成功」都查不到 |
| **G-3** | **审计记录为内存态**：`AuditService._records` 为**环形缓冲 5000 条**，进程退出即丢 | `openbase/modules/audit/__init__.py:104-113`（`MAX_RECORDS = 5000`，注释「生产接数据库」）；仅 proxy 出站跳经 `record_proxy_hop` 落 DB | 人工测试结果**无法跨重启检索**，无法与 DB 对账；记录量超 5000 条会静默淘汰 |
| **G-4** | **无「用例上下文」贯穿**：仅有请求级 `request_id`（中间件生成、响应头 `X-Request-Id` 回传） | `openbase/modules/audit/__init__.py:227-243`；前端 `openbase-ui/src/core/api/http.ts` 请求拦截器**只注入 `Authorization`** | 无法把「一次人工测试的若干个步骤」聚合成一个用例结果；测试者无法把页面操作与后端日志对上号 |

**已有可用基础（不需重建）**：① 网关侧已有**请求级审计记录**（method/path/status/duration/request_id/operator/tenant/ip/ua/请求体摘要/error/identity）；② `request_id` 已在出站装配中透传（`protocol_headers/inject.py:46-53`，`X-Request-Id` 取值「显式 > `request.state.request_id` > 新生成」）；③ 已有 `audit_logs` 表与 `record_proxy_hop` 落库范例；④ 已有 `scripts/gate_aggregate.py` 风格的聚合脚本样例。

---

## §3 总体设计

### 3.1 三层记录通道

| 层 | 通道 | 触发方式 | 记录内容 | 落点 |
|----|------|---------|---------|------|
| **L1 请求级** | 结构化日志（JSON） | 自动（中间件） | 每请求一条：method/path/status/duration/request_id/**case_id/step_id**/actor/tenant/channel/error_code | `logs/<service>/app-YYYYMMDD.jsonl` |
| **L1′ 请求级** | 审计记录 | 自动（中间件） | 同 L1 + 请求体摘要 + identity，**可查询/可跨重启** | `audit_logs` 表（+ 内存缓冲加速） |
| **L2 用例级** | 用例事件日志 | 半自动（人触发/前端埋点/CLI） | run/case/step 的开始、结果（PASS/FAIL/BLOCKED）、人判定理由、耗时 | `logs/<service>/test-YYYYMMDD.jsonl` |
| **L3 证据级** | 聚合报告 | 一键脚本 | 按 run 汇总的 JSON + Markdown（与 Playwright/smoke evidence 同构） | `doc/test/evidence/manual/<run_id>.json｜.md` |

### 3.2 数据流

```
测试者（浏览器/Postman/CLI）
  │  X-Test-Case-Id: UI-DPS-0007   X-Test-Step-Id: 3      ← 非身份头，不触发身份门禁
  ▼
统一前端(5173) ──/api──▶ OpenBase 网关(8000)
  │                          ├─ AuditMiddleware：生成 request_id、读 case/step 头 → request.state
  │                          ├─ L1  JSON 日志（全字段）
  │                          ├─ L1′ 审计记录（case_id 一并入库，可查）
  │                          └─ 出站透传 X-Request-Id（+ 可选 X-Test-Case-Id）→ 子系统
  ▼                                              ▼
子系统(8001/8010/8020/8030) 日志（同 request_id 可串联；同 case_id 可聚合）
  │
  ▼
测试者判定 PASS/FAIL ──▶ L2 用例事件（前端面板 / CLI / 受权 API）
  │
  ▼
scripts/test_log_aggregate.py ──▶ L3 报告（按 case 汇总 + 双证据关联）
```

### 3.3 关键设计取舍

| 取舍 | 决策 | 理由 |
|------|------|------|
| 用例上下文用什么承载 | 自定义头 `X-Test-Case-Id` / `X-Test-Step-Id` | **非身份头**：不在 `INBOUND_IDENTITY_HEADERS` 集合内，**不触发信任链门禁（不会 403）**，也不影响既有租户/JWT 口径 |
| 人判定结果写在哪 | 用例事件日志（L2）为主，DB 为辅 | 判定属主观结论，日志即可承载；落库仅为查询便利，非必需 |
| 是否新建表 | 优先复用 `audit_logs`（`extra` 扩展字段） | 避免迁移成本；仅当查询性能不足再立专表 |
| 日志格式 | JSON Lines（`.jsonl`） | 结构化规范要求；便于 grep/jq/聚合脚本消费，且与既有 evidence JSON 生态一致 |

---

## §4 日志规范落地（字段与事件字典）

### 4.1 必填字段（对齐可观测性标准）

| 字段 | 说明 | 取值来源 |
|------|------|---------|
| `ts` | ISO 8601 UTC 毫秒 | 日志框架 |
| `level` | DEBUG/INFO/WARN/ERROR/FATAL | 日志框架 |
| `service` | 服务名（openbase/openllm/openrag/openmemory/dps/frontend） | 启动配置 |
| `module` | 模块名（如 `audit.middleware`） | `logger.name` |
| `message` | 人类可读描述 | 调用点 |
| `env` | dev/test/pro/联调 | `OPENBASE_ENV` |
| `version` | 服务版本/提交号 | 启动时注入 |

### 4.2 场景扩展字段（本方案新增，标 ★）

| 字段 | 场景 | 示例 |
|------|------|------|
| `request_id` | 请求级 | `req-9f3a1c02d4e7` |
| ★ `run_id` | 测试轮次 | `run-20260913-2130` |
| ★ `case_id` | 用例编号（复用既有编号体系：`S0-1`…`S6-4`、`UI-DPS-0007`、`S7-T2-1`） | `UI-DPS-0007` |
| ★ `step_id` | 用例内步骤序号 | `3` |
| ★ `result` | 用例/步骤结论 | `PASS` / `FAIL` / `BLOCKED` / `SKIPPED` |
| ★ `channel` | 双通道 | `A`（子系统直连）/ `B`（网关编排） |
| ★ `system` | 目标子系统 | `dps` / `openllm` / `openrag` / `openmemory` |
| `method`/`path`/`status_code`/`duration_ms` | API 请求 | 中间件采集 |
| `error_code` | 错误码（AUTH/PERM/PARAM/BIZ/SYS/STORAGE 前缀） | 异常处理器 |
| `actor`/`tenant` | 主体与租户 | JWT/主体上下文 |
| `evidence_ref` | 证据引用 | `doc/test/evidence/manual/run-.../UI-DPS-0007.json` |
| ★ `resp_status` | 网关回给调用方的状态码 | `403` |
| ★ `resp_error_code` | 网关错误信封中的错误码（从响应体提取，非明文） | `PERM_UNTRUSTED_IDENTITY_HEADER` |
| ★ `resp_bytes` / `resp_digest` | 响应体长度 / 内容摘要（sha256 前 16） | `1024` / `a3f19c02…` |
| ★ `resp_summary` | 响应摘要（**仅 `OPENBASE_CAPTURE_RESPONSE=1` 且经脱敏后**，≤2KB） | `{"code":"…","message":"…"}` |
| ★ `upstream_system` | 上游子系统 | `dps` |
| ★ `upstream_status` | **上游子系统返回的状态码** | `500` |
| ★ `upstream_error_code` | 上游错误信封中的错误码（如有） | `BIZ_XXX` |
| ★ `upstream_duration_ms` | 上游耗时（与网关总耗时分离，用于定位慢在谁身上） | `832` |
| ★ `upstream_digest` / `upstream_body_summary` | 上游响应摘要与内容摘要（同受开关与脱敏约束） | — |
| ★ `retry_count` | 上游重试次数 | `0` |

### 4.3 事件字典（L2 用例级）

| event | 时机 | 必带字段 |
|-------|------|---------|
| `test.run.start` | 一轮人工测试开始 | `run_id`、`operator`、`env`、`scope`（页面清单/用例集） |
| `test.case.start` | 单个用例开始 | `run_id`、`case_id`、`title`、`precondition` |
| `test.step.result` | 每个步骤（通常 1 请求/1 交互） | `case_id`、`step_id`、`result`、`expected`、`observed`、`duration_ms`、`request_id` |
| `test.case.end` | 用例结束 | `case_id`、`result`、`reason`（FAIL/BLOCKED 必填）、`evidence_ref` |
| `test.run.end` | 一轮测试结束 | `run_id`、`total/pass/fail/blocked` |

### 4.4 禁止记录（硬约束，验收项）

密码、令牌、API 密钥（任何级别）；身份证号/手机号（需脱敏保留后 4 位）；完整请求/响应体（>1KB 只记摘要）；SQL 完整语句与参数值。**复用既有 `SENSITIVE_HEADERS` 过滤与 `MAX_BODY_SIZE=1MB` 摘要逻辑**（`openbase/modules/audit/__init__.py:200-220`）并加单测。

---

## §5 改造清单（文件级）

> 分三批，**批 1 是必需最小集**（纯后端 + 脚本，不动前端、不动接口契约）。

### 批 1：日志落盘 + 用例上下文 + 持久化 + 聚合（必需）

| # | 文件 | 动作 | 说明 |
|---|------|------|------|
| C-1 | `openbase/core/logging_setup.py` | **新增** | JSON Lines formatter；`RotatingFileHandler`（按日 + 大小，保留 30 天）；级别由 `OPENBASE_LOG_LEVEL` 控制；敏感字段过滤；`service/env/version` 注入 |
| C-2 | `openbase/demo_app.py`（及其他服务入口） | 修改 | 启动时调用 `setup_logging()`；记录 `service.start`（含端口/版本/提交号） |
| C-3 | `openbase/modules/audit/__init__.py` | 修改 | ① `dispatch` 读取 `X-Test-Case-Id`/`X-Test-Step-Id` → `request.state`；② `_record` 的 `extra` 增 `case_id/step_id/run_id/channel`；③ 新增 JSON 日志落盘（复用同一 formatter） |
| C-4 | `openbase/modules/audit/__init__.py`（`AuditService`） | 修改 | 记录**异步落 DB**（`audit_logs`，best-effort；失败仅 WARN 不阻断），内存缓冲保留作加速；提供按 `case_id` 查询 |
| C-5 | `openbase/modules/protocol_headers/inject.py` | 修改 | 出站头增可选 `X-Test-Case-Id` 透传（与 `X-Request-Id` 同源策略），使子系统日志可按 case 聚合 |
| C-6 | `scripts/service-orchestrator.ps1` | 修改 | `start` 时把每服务 stdout/stderr 重定向到 `logs/<service>/<service>-YYYYMMDD.log`（消 G-2；注意保留既有 `-Only`/`-DryRun` 语义） |
| C-7 | `scripts/test_log_aggregate.py` | **新增** | 按 `run_id`/`case_id` 聚合 `logs/**/*.jsonl` → `doc/test/evidence/manual/<run_id>.json` + 同名 `.md`；退出码 0/1/2 沿用项目约定 |
| C-8 | `openbase/modules/audit/__init__.py` 的 API | 复用 | 既有 `/api/v1/audit/records` 增加 `case_id`/`run_id` 过滤参数（只读查询） |
| C-9 | `tests/`（新增） | **新增** | 单测：JSON formatter 字段齐全率、敏感字段过滤、case 头解析、落库失败降级不阻断、聚合脚本分组正确 |

### 批 2：人工结论记录入口（推荐）

| # | 文件 | 动作 | 说明 |
|---|------|------|------|
| C-10 | `openbase/modules/testing/`（新模块）或 `audit` 内扩展 | **新增** | 受权 API：`POST /api/v1/test-records`（单条）、`POST /api/v1/test-runs`（开轮）、`PATCH /api/v1/test-records/{id}`（改判）、`GET /api/v1/test-runs/{run_id}/summary`；权限码 `test:record`（默认仅 admin） |
| C-11 | 前端 `openbase-ui/src/core/api/http.ts` | 修改 | 「测试模式」开关（localStorage `ob_test_mode` 或 URL `?test_case=UI-DPS-0007`）→ 自动注入 `X-Test-Case-Id`；关闭时零影响 |
| C-12 | 前端新增「测试记录」面板（如 `/system/test-records`） | **新增** | 显示本 run 的用例清单与结果，支持一键判定 PASS/FAIL + 填理由；复用 `/system/audit` 页面风格 |

### 批 3：与门禁口径打通（可选）

| # | 文件 | 动作 | 说明 |
|---|------|------|------|
| C-13 | `scripts/gate_aggregate.py` | 修改 | 新增「人工测试记录」章节：读取 `doc/test/evidence/manual/*.json` 作为**补充证据**（不替代自动化断言） |
| C-14 | 文档 | 修改 | 测试报告中登记人工 run 的结论与证据引用 |

### 批 4：响应级观测与错误归因（v1.0.1 新增，受 D-5 红线约束）

| # | 文件 | 动作 | 说明 |
|---|------|------|------|
| C-15 | `openbase/modules/audit/__init__.py`（响应侧） | 修改 | 网关响应摘要采集：`resp_status`/`resp_bytes`/`resp_content_type`/`resp_error_code`/`resp_digest`；`resp_summary` **仅在 `OPENBASE_CAPTURE_RESPONSE=1` 时采集**并经 C-18 脱敏 |
| C-16 | `openbase/modules/proxy/__init__.py`（`_forward`，`:273-301`） | 修改 | 上游响应专段：`upstream_system`/`upstream_status`/`upstream_error_code`/`upstream_duration_ms`/`upstream_digest`（+ 开关下 `upstream_body_summary`）；**成功与业务错误路径统一补记**，异常路径复用同一结构（不新增日志点） |
| C-17 | `scripts/test_log_analyze.py` | **新增** | 错误归因分析器：按 step 输出「网关状态 → 上游状态 → 归属层 → 是否首现 → request_id → 建议动作」；输出 `doc/test/evidence/manual/＜run_id＞-analysis.md` |
| C-18 | `openbase/core/mask.py` | **新增** | 统一脱敏器 `mask_sensitive()`（凭据/个人隐私/画像业务数据/超限摘要）+ 单测；**C-15/C-16 落盘前必经此函数** |
| C-19 | `openbase/settings.py` + `tests/` | 修改/新增 | 三开关（`OPENBASE_CAPTURE_RESPONSE`/`OPENBASE_CAPTURE_UPSTREAM`/`OPENBASE_CAPTURE_FIELD_ALLOWLIST`）默认关；开关变更记审计；单测覆盖「关时零采集」「开时脱敏生效」 |

---

## §6 验收标准

| 类别 | 标准 | 判定方式 |
|------|------|---------|
| **可检索性** | 一次人工 run 中 ≥95% 的用例可通过 `case_id` 在日志中检索到 | `jq`/聚合脚本统计命中率 |
| **字段完整性** | L1/L2 记录必填字段齐全率 100% | 单测 + 聚合脚本 schema 校验 |
| **双证据关联** | 每条 `test.step.result` 均带 `request_id`，且能在 L1′ 审计记录中命中 | 关联查询断言 |
| **持久性** | 服务重启后，重启前 run 的记录仍可查询 | 重启 + 查询回归 |
| **合规** | 敏感字段（密码/token/key）与超限请求体**0 命中** | 单测 + 全量日志扫描 |
| **性能** | 日志写入不阻塞主请求；P99 增量 < 5ms | 压测对比 |
| **容量** | 单服务单日日志 < 200MB（1000 请求/日量级，含样本） | 实测 |
| **响应级归因**（v1.0.1） | ≥90% 的失败步骤可定位到「归属层 + 上游错误码」；上游耗时与网关耗时可分离 | `scripts/test_log_analyze.py` 输出统计 |
| **红线合规**（v1.0.1，D-5） | 采集默认关闭时日志中 `resp_summary`/`upstream_body_summary` **0 条**；开启后敏感字段（token/key/password/证件号/手机号原文）**0 命中**；单条摘要 ≤2KB | 全量日志扫描 + 单测 |

---

## §7 风险与假设

| 项 | 说明 | 应对 |
|----|------|------|
| 落库依赖 `audit_logs` 现有结构 | 需确认 `extra`/`detail` 字段可扩展（JSON 列） | 批 1 先做；若不可扩展则立专表 `test_records` |
| 编排器日志重定向改动 | 重定向会影响「隐藏窗口」启动方式，需回归 `start/stop/status/checkall` | 改动后跑编排全量检查（当前基线 27 PASS / 0 FAIL） |
| 自定义头被误加入身份集合 | 若将来把 `X-Test-Case-Id` 混入 `INBOUND_IDENTITY_HEADERS` 会触发 403 | 在 `protocol_headers/constants.py` 注释中显式标注「非身份头，禁止加入裁剪集」 |
| 人工记录主观性 | PASS/FAIL 由人判定，可能失真 | 强制要求「FAIL/BLOCKED 必填 reason」，并要求附 `request_id` 客观证据 |
| 日志量增长 | 全量 INFO + 请求级日志 | 采样策略（ERROR/WARN 100%、INFO 可配）、按日轮转 + 30 天保留 |
| 响应采集合规（v1.0.1） | DPS 画像等域属**个人隐私数据**，误采即合规事故 | 已定红线（D-5）：默认关闭 + 开启强制脱敏 + 2KB 摘要上限 + 开关变更留痕审计 + 生产永久关闭 |

**假设**：① 人工测试在联调环境（dev/pro）进行，允许文件落盘；② 测试者使用浏览器/Postman/CLI，均可携带自定义头；③ 生产环境默认关闭 `test.*` 事件与 case 头透传。

---

## §8 实施步骤与工作量

| 步骤 | 内容 | 产出 | 估时 |
|------|------|------|------|
| 1 | 批 1 C-1~C-5（日志落盘 + case 头 + 落库） | 代码 + 单测 | 4~6h |
| 2 | 批 1 C-6（编排器日志重定向）+ 回归 `startcheck` | 编排脚本 + 27 项全绿 | 1~2h |
| 3 | 批 1 C-7/C-8/C-9（聚合脚本 + 查询过滤 + 测试） | 脚本 + 证据样例 | 2~3h |
| 4 | 批 2 C-10~C-12（受权 API + 前端测试模式与面板） | 接口契约 + UI + E2E | 6~8h |
| 5 | 批 3（门禁打通 + 文档回填） | 报告 + 证据 | 1~2h |

**最小可用路径**：步骤 1~3（约 7~11h）即可满足「人工测试每条结果可被日志记录并聚合复盘」。

---

## §9 待决策项（需评审确认后才进入实施）

| # | 决策项 | 选项 | 建议 |
|---|--------|------|------|
| **D-1** | 记录通道范围 | ① 仅批 1（后端日志 + 脚本聚合）② 批 1+批 2（含受权 API 与前端面板）③ 全部含批 3 | **②**：批 1 先落地并用起来，批 2 提供人工判定入口与可视化，体验闭环 |
| **D-2** | 是否落库 | ① 复用 `audit_logs` ② 新建 `test_records` 表 ③ 不落库（纯文件） | 先 ①（零迁移）；若查询压力大再 ② |
| **D-3** | 是否纳入 S7 门禁口径 | ① 仅作补充证据（不参与门禁判定）② 纳入门禁（人工 run 必须全绿） | **①**：人工记录保持「补充证据」定位，避免与自动化断言口径混淆 |
| **D-4** | 用例编号体系 | ① 复用既有（S0-1…S6-4 / UI-<模块>-<序号> / S7-T2-1）② 新建人工用例集 | **①**：复用保证与既有证据可对齐，不新增第二套编号 |
| **D-5** | **响应数据采集红线** | ① 默认关闭，开启时强制脱敏（2KB 摘要上限、生产永久关闭）② 常开（便于分析）③ 完全不采集响应 | **①（已确认 2026-09-13）**：默认关闭保证零合规暴露；仅在联调/人工测试窗口显式开启，且落盘前必经 C-18 脱敏。**②③ 不再作为可选项** |
| **D-6** | **是否推动四仓补齐 request_id 日志接线**（v1.0.2 新增，源于 §11.8 实测） | ① 暂不推动（靠网关侧 `upstream_*` 定位到「错在上游」即够）② 推动四仓各做最小改动（DPS/OpenLLM 各 1 个 Filter + format、OpenMemory 1 行、OpenRAG 注册中间件 + 补头）③ 只修 OpenRAG（其请求日志根本未注册） | **②**：四仓的状态码/耗时**其实都已采集**（指标/审计表/中间件组装），只差「送进日志」这一步，改动成本极低；收益是人工排查能追进子系统内部日志。**须列为独立跨仓任务（各仓走各自的开发流程），不阻塞 OpenBase 侧批 1/批 2** |

### 9.1 决议记录（2026-09-13 冻结）

| 决策 | 决议 | 生效实施范围 |
|------|------|-------------|
| **D-1** | **②**（批 1 + 批 2） | 实施 C-1~C-12；**批 3（门禁打通 C-13/C-14）不做** |
| **D-2** | **①**（复用 `audit_logs` 表 + JSON 扩展字段，零迁移） | C-4/C-8 的落库与查询基于既有表；实施时核实 `detail`/`extra` 是否为可扩展 JSON 列，若不是则退回「新建 `test_records` 表」 |
| **D-3** | **①**（人工记录**仅作补充证据**，不参与门禁判定） | C-13/C-14 不做；人工 run 结果只落 `doc/test/evidence/manual/**` 与报告附录 |
| **D-4** | **①**（复用既有编号：`S0-1…S6-4` / `UI-<模块>-<序号>` / `S7-T2-1`）+ `AD-HOC-<日期>-<序号>` 兜底 | 日志与证据中的 `case_id` 一律采用既有编号体系，不新增第二套 |
| **D-5** | **①**（默认关闭 + 开启强制脱敏，2KB 上限，生产永久关闭） | C-15/C-16/C-18/C-19 的**硬约束** |
| **D-6** | **②**（推动四仓补齐 request_id 接线） | 列为**独立跨仓任务**（DPS/OpenLLM 各 1 个 Filter + format、OpenMemory 1 行、OpenRAG 注册中间件 + 补头），各仓走各自流程；**不阻塞** OpenBase 侧批 1/批 2 |

**实施顺序（冻结）**：批 1（C-1~C-9）→ 批 2（C-10~C-12）→ 批 4（C-15~C-19）；批 3 不做；四仓接线并行独立推进。

**首个里程碑（冻结）**：C-1（日志落盘）+ C-6（服务日志采集）——不涉及接口与前端，风险最低，完成后人工测试即刻有文件可查。

---

## §10 与既有资产的关系

| 既有资产 | 关系 |
|---------|------|
| `openbase/modules/audit/__init__.py` | **被扩展**：新增 case 上下文与落库，不改既有审计语义 |
| `scripts/service-orchestrator.ps1` | **被扩展**：新增子进程日志重定向，不改启停语义 |
| `scripts/gate_aggregate.py` | **可选扩展**：新增人工记录章节作为补充证据 |
| `openbase-ui/scripts/ui_e2e_all_services.mjs` | **可复用**：测试模式开关与 case 头注入逻辑可共用 |
| `doc/test/evidence/**` | **扩展落点**：新增 `manual/` 子目录，与自动化证据并列不混用 |
| Playwright / s7 冒烟 / 门禁聚合 | **互补**：自动化负责「可复现断言」，人工记录负责「探索性验证与体验问题留痕」 |

---

## §11 响应级观测与错误归因（v1.0.1 新增）

> 本章回答两个问题：**能否观测各子系统的响应数据？能否据此分析每一步的响应错误？**
> 结论：**原方案不能**——响应体是盲区，必须补 C-15~C-19 才能达到「按步骤归因到上游」的能力。

### 11.1 为什么原方案观测不到响应数据（实证）

| 核查点 | 实证 | 结论 |
|--------|------|------|
| 审计记录字段 | `APICallRecord`（`openbase/modules/audit/__init__.py:32-50`）字段为 method/path/status_code/duration_ms/request_id/operator/tenant/ip/ua/**request_body**/error/extra | **无任何响应字段** |
| 代理层日志点 | `openbase/modules/proxy/__init__.py` 共 5 处日志，全部落在 K03 绕过审计、服务密钥写拒绝、上游不可达、上游 402 | **上游正常响应与业务错误响应未留痕** |
| 上游响应去向 | `_forward` 中 `payload = upstream.json()`（失败回退 `upstream.text[:2000]`）→ `JSONResponse(status_code=upstream.status_code, content=payload)`（`:298-301`） | 上游响应**原样透传浏览器，未落日志/审计** |
| 子系统侧 | OpenRAG 有请求级日志中间件（`src/openrag/observability/logging.py:456`）；DPS 有 `identity/request_id.py` contextvar 与审计表 `request_id` 列 | 具备按 request_id 串联的基础，但**各仓是否记状态码/响应摘要需逐仓核实**（列为实施前置任务） |

**能力边界（原方案）**：可回答「哪一步、网关返回了什么状态码/错误码、耗时多少」；**不可回答**「上游子系统到底返回了什么、错误出在网关还是上游」。

### 11.2 红线（D-5，已确认的硬约束）

1. **默认关闭**：`OPENBASE_CAPTURE_RESPONSE` / `OPENBASE_CAPTURE_UPSTREAM` 未设或为 `0` 时，**零采集、零落盘**（响应摘要字段不出现，仅保留 `resp_status`/`resp_bytes`/`resp_digest` 等非敏感结构字段）；
2. **开启时强制脱敏**：任何响应摘要**落盘前必经 C-18 `mask_sensitive()`**，命中敏感字段即遮蔽；
3. **单条上限 2KB**：超限只存 `resp_digest` + 键名清单，不存原文；
4. **生产永久关闭**：仅联调/人工测试窗口可开启；
5. **开关本身留痕**：响应采集的开启/关闭作为审计事件记录（谁、何时、对哪个服务开启）；
6. **域级最小化**：`OPENBASE_CAPTURE_FIELD_ALLOWLIST` 默认空 → 默认只留结构化键名与 digest，画像等隐私域**整体遮蔽**。

### 11.3 三开关设计

| 开关 | 默认 | 作用 |
|------|------|------|
| `OPENBASE_CAPTURE_RESPONSE` | `0`（关） | 网关侧响应摘要（C-15） |
| `OPENBASE_CAPTURE_UPSTREAM` | `0`（关） | 上游子系统响应摘要（C-16） |
| `OPENBASE_CAPTURE_FIELD_ALLOWLIST` | 空 | 允许保留原值的字段白名单（如 `error.code`、`error.message`） |

### 11.4 脱敏规则（C-18）

| 类别 | 处理 |
|------|------|
| 凭据 | `authorization`/`token`/`api_key`/`password`/`secret`/`cookie` → `***` |
| 个人隐私 | 手机号（保留后 4 位）、证件号/身份证、邮箱（本地部掩码）、住址 |
| 画像业务域 | `portraits` 等域**默认整体遮蔽**，仅留键名与长度 |
| 超限/嵌套过深 | >2KB 或层级 >5 层 → 摘要 + digest，不存原文 |

### 11.5 错误归因矩阵（C-17 输出口径）

| 观测到的错误 | 归属层 | 排查入口 |
|-------------|--------|---------|
| `401 AUTH_401` | 网关鉴权 | 是否携带 JWT / 是否走 key 通道 |
| `403 PERM_UNTRUSTED_IDENTITY_HEADER` | 网关信任链 | 调用方是否直连带身份头（应改走 JWT 或 proxy） |
| `403 PERM_SERVICE_KEY_WRITE_DENIED` | 网关 K03 | 写操作是否需 `sk-agent-*` 服务账号或登记白名单 |
| `502 SYS_UPSTREAM_ERROR` | 网络/上游不可达 | 上游端口、进程、编排器状态 |
| 上游 4xx/5xx + `upstream_error_code` | **上游子系统** | 子系统日志（同 `request_id`）→ 该仓错误码表 |
| 网关 200 但响应不符预期 | 契约/数据 | `resp_digest` 对比 + 子系统日志 |

### 11.6 分析器输出（`scripts/test_log_analyze.py`）

按步骤输出一行一结论，并给出「首次失败即停」脚手架（避免人工测试把连锁噪音当新问题）：

```
case_id      step  gateway  upstream  归属层      首现  request_id           建议动作
UI-DPS-0007  3     403      -         网关信任链   是    req-9f3a1c02d4e7    该页应走 JWT，勿带身份头
UI-DPS-0011  2     502      -         网络/上游    是    req-77b10d9ac331    检查 dps:8030 进程
UI-DPS-0014  5     500      500       上游子系统   是    req-1c02ab77d9f4    查 DPS 日志同 request_id
```

输出落 `doc/test/evidence/manual/<run_id>-analysis.md`（含每步的 `resp_digest`/`upstream_status` 引用，**不含响应明文**）。

### 11.7 与自动化的边界

响应采集**只服务人工探索性测试**；Playwright / s7 冒烟继续使用自身断言，**不依赖**响应摘要，避免形成第二套判定口径（与 D-3「人工记录仅作补充证据」一致）。

### 11.8 跨仓前提核实结果（2026-09-13 实测，只读核查四仓源码）

**前提 1：子系统日志是否可被编排器重定向捕获 → 四仓 PASS，无需任何改动**

| 仓 | 实际日志出口 | 证据 |
|----|-------------|------|
| DPS | stderr（`basicConfig` 未传 filename/handlers/stream） | `src/main.py:37-41` |
| OpenLLM | stderr（同上） | `backend/main.py:80-83` |
| OpenRAG | stdout（**实际生效的是 `config/logging.py`，不是 `observability/logging.py`**） | `repository/config/logging.py:58-63` |
| OpenMemory | stderr | `src/openmemory/api/server.py:788-791` |

**前提 2：子系统日志是否携带 request_id → 四仓均未打通，各需最小改动**

| 仓 | 结论 | 实证 | 最小改动 |
|----|------|------|---------|
| DPS | **FAIL（死接线）** | contextvar 仅在 `identity_gate_middleware.py:109` 写入，全仓**无任何 Filter/Formatter/`extra=` 消费它**；`get_current_request_id()` 零调用；`error_handlers.py:81-87` 是把 rid 拼进 message 文本（且取自 `request.state`） | 根 logger 加 1 个 Filter + format 加 `%(request_id)s` |
| OpenLLM | **FAIL** | `app/identity/audit_identity.py:112-129` 的 `identity_log_extra()` **已产出 request_id，但只塞进审计 DB**（`app/middleware/audit.py:320-327`），从未传给 `logger.*(extra=…)` | 同上（Filter + format） |
| OpenMemory | **FAIL（仅差 1 行）** | `utils/struct_logger.py:253-255` 有 JSON formatter 且从 contextvars 取 `request_id`；`api/middleware/structured_log.py:144-197` **已组装** `request_id`/`status_code`/`elapsed_ms` 并以 `extra={"structured":…}` 发出，但 `:26` 用的是普通 `logging.getLogger` → 被根 logger 的纯文本 formatter **丢弃** | `structured_log.py:26` 改用 `get_logger` |
| OpenRAG | **FAIL（既有缺口更重）** | `repository` 全目录 `request_id`/`X-Request-Id` **零匹配**（其相关性 ID 走 `X-Correlation-ID`）；`observability/logging.py:366` 的 `LoggingMiddleware` **定义但从未注册**（`main.py` 只注册 CORS + Prometheus）；`security/audit_logger.py` 不存在 | ① 注册请求日志中间件 ② 补 `X-Request-Id` 受信透传 ③（可选）补审计模块 |

**关键结论**：前提 2 **不阻塞本方案**——网关侧 C-16 已能提供 `upstream_status`/`upstream_error_code`/`upstream_duration_ms`，足以判定「错在网关还是上游」。补齐四仓接线只影响「能否进一步追进子系统**内部**日志」。另一个有利事实：四仓的**状态码/耗时其实都已采集**（DPS 指标 + 审计表 / OpenLLM DB + 指标 / OpenMemory 中间件组装 / OpenRAG Prometheus 指标），**只差「送进日志」这一步**，故跨仓改动成本很低（详见 D-6）。

**顺带发现的两处既有缺口（与本方案无关，但影响人工排查效率，已登记）**

1. **OpenRAG 请求日志中间件从未注册** → 其「请求日志」实际不存在；其 S3 文档声称的 `audit_logger`/`detail.identity` 亦未落地（目录不存在）。这解释了为何此前排查上游问题时看不到 OpenRAG 请求日志。
2. **OpenMemory 的 `basicConfig` 只在 `main()` 内** → 若以 `uvicorn openmemory.api.server:create_app` 方式启动，根 logger 不被配置（需核实编排器实际启动命令；已列入实施前置核对）。

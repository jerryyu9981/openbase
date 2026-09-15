# OpenBase-S7-人工端到端测试日志落盘-测试用例-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S7-TC-LOGS-v1.0.0 |
| 版本 | v1.1.0 |
| 状态 | [Review]（Step 4 测试阶段用例基线；沙箱可判定面与**联调窗口真实面**均已实跑回填，未执行项登记 PENDING，禁伪造） |
| 日期 | 2026-09-14 |
| 作者 | AI（S7 批 6 测试阶段会话，责任角色：AT 测试工程师 + AU 审计师复核视图） |
| 用途 | 「人工端到端测试日志落盘」流的 **Step 4 测试用例基线**（TT-ID 矩阵）：逐条关联设计条目（方案 §5 改造清单 C-1~C-19 + 批 5）、代码落点、测试文件与用例名、预期结果、断言级别与执行面；作为《OpenBase-S7-人工端到端测试日志落盘-测试报告-v1.0.0》与《OpenBase-S7-人工端到端测试日志落盘-测试回溯对比审计报告-v1.0.0》的用例来源 |
| 上游依据 | ①《OpenBase-人工端到端测试日志记录方案-v1.0.0.md》（OB-DESIGN-MANUAL-E2E-LOG-v1.0.0，内部 **v1.5.0 [Approved]**，§4 字段字典 / §5 改造清单 C-1~C-19 与批 5 / §6 验收标准 / §11 响应级观测与红线 D-5 / §9.1 决议 D-1~D-6）；②《OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.4.0.md》（OB-S7-DEVLOG-LOGS-v1.4.0，[Review]，§3 任务清单 / §10 追溯矩阵 / §13 测试移交说明）；③`AGENTS.md`（测试规则：TDD、覆盖率 ≥90%、`python -m pytest tests`）；④`testing-stage-execution`（T1-T4 四层测试架构、断言分级 L1~L4、禁止软断言）；⑤`project-document-management`（用例文档命名与落点） |
| 适用范围 | **提交面仅 OpenBase 主仓**（`openbase/**`、`openbase-ui/**`、`tests/**`、`doc/**`）；**不改动 DPS/OpenLLM/OpenMemory/OpenRAG 四仓任何文件**；**不纳入 `dogfood-output/`** |
| 追溯口径 | 本流为**设计驱动增量流**（无独立《开发需求文档》）：需求/验收追溯源 = 方案 §5 改造清单（C-1~C-19 + 批 5 补全）+ §6 验收标准 9 行 + §11.2 红线 6 条。逐条映射见 §3；该口径已在测试报告与回溯审计中显式登记 |
| 纪律 | 用例名与文件路径**一律取自仓内真实文件**（逐条 `grep` 核实，禁杜撰）；**未执行项一律 PENDING，禁填假响应码/假通过**；沙箱外执行面单列（§3.6） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-14 | AI（S7 批 6 测试阶段会话，AT/AU） | 初始版本：建立 TT-LOGS-001~059 用例基线（59 条，覆盖 C-1~C-19 + 批 5 + 契约/回归/覆盖率/静态质量），逐条关联设计条目、代码落点、真实测试文件与用例名、预期结果、断言级别与执行面；含 §4 覆盖矩阵与缺口分析、§5 未纳入项与跳过项、§6 追溯与维护规则。**本次仅新建用例文档，未改动任何业务代码与四仓文件** |
| v1.1.0 | 2026-09-14 | AI（S7 批 7 联调窗口真实面执行会话，AT/AU） | **联调窗口真实面执行回填**：§3.6 增设 v1.1.0 执行回填说明（TT-057 `checkall` 27 PASS ✅ / TT-058 前端 E2E 9/9 ✅ / TT-055 真实人工 E2E 部分达成（5 PASS + 归因 3/3，1 例 502 环境性）/ TT-056 性能仍 PENDING）；同步反映 TT-015（C-6 行为面）随 TT-057 关闭。**未新增用例，未改动业务代码**（缺陷 AD-20260914-02 的修复与回归见测试报告 §13.7 与 DevLogReport §17） |

---

## §1 用例设计口径

### 1.1 层级与执行面

| 口径 | 定义 | 本流落地 |
|------|------|---------|
| **T1 契约层** | 前后端/跨仓接口定义一致性 | 三测试头（`X-Test-Case-Id`/`X-Test-Step-Id`/`X-Test-Run-Id`）非身份头约束 + `test:record` 端点族 schema（`openbase/modules/testing/schemas.py`） + 前端 `core/api/testing.ts` 与 `core/api/http.ts` 拦截器同源 |
| **T2 接口层** | 后端接口功能正确性（状态码 + 响应结构 + 边界） | `tests/test_testing_api.py`（23 例）、`tests/test_test_case_context.py`（14 例）、`tests/test_audit_db_persist.py`（7 例）、`tests/test_audit_records` 过滤面 |
| **T3 集成层** | 服务内/服务间链路正确性（本流为**后端为主**，T3a 以服务内链路巡检替代全页面巡检） | 六族转发出口观测（`tests/test_proxy_upstream_observe.py` 9 例 + `tests/test_specialized_proxy_upstream_observe.py` 14 例，含 TestClient 端到端 1 例）；前端 `openbase-ui/tests/**`（13 文件 / 147 例，含测试模式 4 例） |
| **T4 验收层** | 核心业务流走查（人工判定入口 + 日志可检索） | 本地聚合脚本实跑（`run-20260914-0225` / `run-20260914-0230`）+ 前端 `/system/test-records` 面板；真实 7 服务在线走查登记 PENDING（§3.6） |

### 1.2 断言级别（对齐 `testing-stage-execution`）

| 级别 | 口径 | 本流用法 |
|:----:|------|---------|
| **L1 硬断言** | 关键行为必须成立，超时/不符即失败 | 红线类（默认关零采集、生产永久关、脱敏命中、不可达同结构、D-6 头不触发 403）与 CRUD 关键路径 |
| **L2 条件断言** | 可选分支存在则验证 | 矩阵化参数校验（`test_should_capture_body_matrix`） |
| **L3 存在性断言** | 结构齐备（字段名/键集合） | 字段齐备率类断言 |
| **L4 网络层断言** | E2E 网络健康（无代码类 5xx/requestfailed/console.error） | 前端 Playwright 面（本窗口 PENDING，承 S6 已达标证据） |

> **禁止软断言**：本流用例**不含** `if ... is_visible() ... else: assert` 模式（后端为主，无 UI 软断言分支）；前端 `tests/**` 为 vitest 单测/集成，不含 Playwright 软断言分支。

### 1.3 TT-ID 编号规则

- 格式：`TT-LOGS-{三位序号}`；序号按「设计分组」连续分配（G1 批 1 / G2 批 2 / G3 批 4 / G4 批 5 / G5 契约与回归 / G6 沙箱外与跳过）。
- 每条用例同时给出：**设计条目**（C-x 或批 5）、**代码落点**、**测试文件与用例名**（真实存在）、**预期结果**、**断言级别**、**执行面**（A = 沙箱内实测 / A+B = 结构面实测 + 真实面 PENDING / B = 真实面 PENDING）。

---

## §2 用例总览与统计

| 分组 | 范围 | 用例数 | 对应设计条目 | 执行面 |
|:----:|------|:------:|-------------|:------:|
| G1 | 日志链路（批 1） | TT-LOGS-001~015（15） | C-1~C-9 | A（C-6 为 A+B） |
| G2 | 人工结论入口（批 2） | TT-LOGS-016~023（8） | C-10~C-12 | A（C-12 为 A+B） |
| G3 | 响应级观测与归因（批 4） | TT-LOGS-024~042（19） | C-15~C-19 | A |
| G4 | 专用代理族接线（批 5） | TT-LOGS-043~050（8） | C-16 补全 | A |
| G5 | 契约与回归门禁 | TT-LOGS-051~054（4） | §6 验收标准 + `AGENTS.md` | A |
| G6 | 沙箱外执行面与跳过项 | TT-LOGS-055~059（5） | §6 性能/容量 + D-1 决议 | B（055~058）/ 不适用（059） |
| **合计** | — | **59** | C-1~C-19 + 批 5 | — |

**统计口径**：沙箱内可判定（A / A+B 的结构面）**54 条**；真实面 PENDING **4 条**（055~058）；不适用（经决议不做）**1 条**（059）。

---

## §3 用例明细

### 3.1 G1 日志链路（批 1：C-1~C-9）

| TT-ID | 设计条目 | 代码落点 | 测试文件 :: 用例名 | 预期结果 | 级别 | 执行面 |
|-------|---------|---------|-------------------|---------|:----:|:------:|
| TT-LOGS-001 | C-1（JSONL 落盘、必填字段、按日切分、幂等） | `openbase/core/logging_setup.py` | `tests/test_logging_setup.py::test_formatter_emits_required_fields` / `::test_formatter_keeps_structured_extras` / `::test_bind_log_context_injects_fields_into_every_record` / `::test_setup_logging_writes_jsonl_and_is_idempotent` / `::test_setup_logging_level_follows_env` / `::test_daily_file_handler_splits_by_date` | 每条记录含 `ts/level/service/module/message/env/version`；结构化 extra 不丢失；重复 setup 不产生双 handler；级别随 `OPENBASE_LOG_LEVEL`；按日落 `logs/<service>/<service>-YYYYMMDD.jsonl` | L1/L3 | A |
| TT-LOGS-002 | C-1（敏感字段过滤） | 同上 | `::test_formatter_masks_sensitive_keys_recursively` / `::test_sensitive_filter_keeps_non_sensitive_records` | 凭据类键递归遮蔽；非敏感记录不被误过滤 | L1 | A |
| TT-LOGS-003 | C-1（超限截断） | 同上 | `::test_formatter_truncates_oversized_values` | 超长值截断，记录仍可序列化 | L3 | A |
| TT-LOGS-004 | C-1（`request_id` 兜底） | 同上 | `::test_formatter_request_id_defaults_to_dash` | 无上下文时输出 `"-"`，不抛 `KeyError` | L1 | A |
| TT-LOGS-005 | C-1 + 不变量 T6-1（禁自动清理） | 同上 | `::test_daily_file_handler_never_deletes_historical_logs` / `::test_module_declares_no_auto_purge_path` | 历史日志不被自动删除；模块内**零按保留期清理路径** | L1 | A |
| TT-LOGS-006 | C-2（启动接线 + 版本注入） | `openbase/demo_app.py`、`openbase/core/logging_setup.py::_resolve_version`、`scripts/oidc-idp/idp_server.py` | `::test_resolve_version_prefers_explicit_then_env` / `::test_resolve_version_falls_back_to_git_commit` / `::test_resolve_version_defaults_when_git_unavailable` / `::test_setup_logging_version_flows_into_records` / `::test_oidc_idp_entry_wires_structured_logging` | 版本取值优先级（显式 > 环境 > git 短提交号 > 默认）；版本流入每条记录；IdP 入口完成接线 | L1/L3 | A |
| TT-LOGS-007 | C-3（三测试头解析与上下文） | `openbase/modules/audit/__init__.py::_extract_test_context` | `tests/test_test_case_context.py::test_extract_test_context_reads_headers` / `::test_extract_test_context_absent_returns_none_values` / `::test_extract_test_context_run_id_falls_back_to_env` / `::test_dispatch_puts_test_context_into_request_state` | `case_id`/`step_id`（纯数字归一 int）/`run_id` 正确解析并落 `request.state`；缺省回退 `OPENBASE_TEST_RUN_ID`；全缺省为 None 不报错 | L1 | A |
| TT-LOGS-008 | C-3 + §3.3（非身份头，不触发信任链） | `openbase/modules/protocol_headers/constants.py` | `::test_test_case_headers_are_not_identity_headers` | 三头**不在** `IDENTITY_HEADERS`/`INBOUND_IDENTITY_HEADERS` 集合内（携带不产生 403） | L1 | A |
| TT-LOGS-009 | C-3（L1 记录字段合流） | `openbase/modules/audit/__init__.py::_record`/`_emit_request_log` | `::test_record_extra_carries_case_context_and_channel` / `::test_record_emits_l1_json_log_with_case_context` / `::test_record_without_case_context_omits_fields` | L1 记录 `extra` 含 `case_id/step_id/run_id/channel`；无上下文时不出现该组字段 | L1 | A |
| TT-LOGS-010 | C-4（异步落库 + best-effort 降级） | `openbase/modules/audit/__init__.py::_persist_audit_record` | `tests/test_audit_db_persist.py::test_persist_audit_record_writes_audit_log_row` / `::test_persist_audit_record_disabled_by_switch` / `::test_persist_audit_record_degrades_without_blocking` / `::test_dispatch_persists_audit_record_after_response` | 落库成功写入 `audit_logs`；开关关闭时不落库；落库失败仅 WARN **不阻断**响应；中间件响应后落库 | L1 | A |
| TT-LOGS-011 | C-4（按 case/run 查询） | 同上（`query_audit_logs_by_case` 家族） | `::test_query_audit_logs_by_case_id` / `::test_query_audit_logs_by_run_id` / `::test_query_audit_logs_without_filter_returns_all` | 按 `case_id`/`run_id` 精确命中；无过滤返回全部 | L1 | A |
| TT-LOGS-012 | C-5（出站 `X-Test-Case-Id` 透传） | `openbase/modules/protocol_headers/inject.py` | `::test_outbound_headers_carry_test_case_id_from_request_state` / `::test_outbound_headers_omit_test_case_id_when_absent` / `::test_outbound_headers_explicit_test_case_id_wins` / `::test_outbound_headers_reject_header_injection_in_case_id` | 出站头透传同源策略（显式 > `request.state`）；缺省不注入；含 CRLF 等注入字符被拒 | L1 | A |
| TT-LOGS-013 | C-8（查询过滤参数） | `openbase/modules/audit/__init__.py::records(case_id, run_id)` + `/api/v1/audit/records` | `::test_audit_service_records_expose_case_context_and_filter` / `::test_audit_records_endpoint_accepts_case_and_run_filters` | 只读查询端点接受 `case_id`/`run_id` 过滤并命中当步记录 | L1 | A |
| TT-LOGS-014 | C-7（聚合脚本） | `scripts/test_log_aggregate.py` | `tests/test_test_log_aggregate.py::test_aggregate_groups_by_run_and_case` / `::test_aggregate_filters_other_runs` / `::test_aggregate_skips_malformed_lines_and_non_jsonl` / `::test_aggregate_marks_pending_without_records` / `::test_main_writes_json_and_markdown` / `::test_main_returns_fail_when_failed_step_present` / `::test_main_returns_pending_when_no_records` / `::test_markdown_contains_evidence_columns` | 按 `run_id`/`case_id` 聚合；过滤他轮；容忍脏行与非 jsonl；无记录 → PENDING；输出 `.json` + `.md`（含证据列）；退出码 0/1/2 | L1 | A |
| TT-LOGS-015 | C-6（编排器日志重定向） | `scripts/service-orchestrator.ps1`（`Start-Service` 重定向 + `-ServiceLogRoot` + 同日归档） | 结构面：脚本静态核对（重定向/参数/归档分支）；行为面：`service-orchestrator checkall` | 每服务 stdout/stderr 落 `logs/<service>/<service>-YYYYMMDD.log`，**保留既有 `-Only`/`-DryRun` 语义**；`checkall` 27 PASS / 0 FAIL / 0 SKIP | L1 | **A+B**（行为面复跑见 TT-LOGS-057） |

### 3.2 G2 人工结论入口（批 2：C-10~C-12）

| TT-ID | 设计条目 | 代码落点 | 测试文件 :: 用例名 | 预期结果 | 级别 | 执行面 |
|-------|---------|---------|-------------------|---------|:----:|:------:|
| TT-LOGS-016 | C-10（鉴权 + 权限码 `test:record`） | `openbase/modules/testing/__init__.py` | `tests/test_testing_api.py::test_testing_requires_auth` / `::test_testing_forbidden_without_permission` | 未认证 401；无 `test:record` 权限 403（错误信封一致） | L1 | A |
| TT-LOGS-017 | C-10（开轮） | 同上 | `::test_create_test_run_auto_generates_run_id` / `::test_create_test_run_duplicate_conflict` | `POST /test-runs` 自动生成 `run_id`；重复开轮冲突（4xx） | L1 | A |
| TT-LOGS-018 | C-10（结论录入与强校验） | 同上 + `openbase/modules/testing/schemas.py` | `::test_create_pass_record` / `::test_fail_requires_reason` / `::test_fail_with_reason_ok` / `::test_blocked_requires_reason` / `::test_invalid_result_validation_error` / `::test_record_unknown_run_not_found` / `::test_non_numeric_step_id_kept_as_is` | PASS 可无 reason；FAIL/BLOCKED **强制 reason**；非法 result 校验失败；未知 run 404；非数字 step 原样保留 | L1 | A |
| TT-LOGS-019 | C-10（改判） | 同上 | `::test_update_record_pass_to_fail` / `::test_update_record_fail_without_reason` / `::test_update_unknown_record_not_found` / `::test_update_record_with_observed` / `::test_result_service_require_reason` | `PATCH /test-records/{id}` 改判成立；改判为 FAIL 无 reason 被拒；未知 id 404；`observed` 可携带客观证据 | L1 | A |
| TT-LOGS-020 | C-10（run 汇总） | 同上 | `::test_summary_aggregates_counts` / `::test_summary_passed_all_green` / `::test_summary_unknown_run_not_found` / `::test_summary_aggregates_blocked_and_skipped` | 汇总按 PASS/FAIL/BLOCKED/SKIPPED 计数；全绿判定；未知 run 404 | L1 | A |
| TT-LOGS-021 | C-10（落库 best-effort） | 同上 | `::test_db_persist_disabled_is_silent` / `::test_db_persist_success_path` / `::test_db_persist_failure_degraded` | 落库开关关闭静默；成功写入；失败降级**不阻断** | L1 | A |
| TT-LOGS-022 | C-11（前端测试模式注入三头） | `openbase-ui/src/core/api/http.ts` | `openbase-ui/tests/http.spec.ts`（测试模式段：URL `?test_case=` / localStorage `ob_test_mode=1` 注入；关闭零影响） | 开关开启 → 自动注入 `X-Test-Case-Id` 等头；关闭 → 请求头零变化 | L1 | A |
| TT-LOGS-023 | C-12（`/system/test-records` 面板与路由） | `openbase-ui/src/pages/SystemTestRecords.vue`、`src/core/api/testing.ts`、`src/core/router/index.ts` | 结构面：路由注册（`system/test-records`，`permission: 'test:record'`）+ `testing.ts` 客户端方法 + 拦截器（http.spec.ts 间接）；行为面：Playwright 关键页走查 | 面板可开轮/录入/改判并展示 run 汇总；未授权不可达；真实浏览器交互无阻塞性缺陷 | L1/L4 | **A+B**（行为面见 TT-LOGS-058） |

### 3.3 G3 响应级观测与归因（批 4：C-15~C-19）

| TT-ID | 设计条目 | 代码落点 | 测试文件 :: 用例名 | 预期结果 | 级别 | 执行面 |
|-------|---------|---------|-------------------|---------|:----:|:------:|
| TT-LOGS-024 | C-15 + 红线 1（默认关零采集） | `openbase/modules/audit/__init__.py::build_response_observation` | `tests/test_audit_response_observe.py::test_response_summary_absent_when_switch_off` | 默认关时**无** `resp_summary`；结构性字段（`resp_status`/`resp_bytes`/`resp_digest`）齐备 | L1 | A |
| TT-LOGS-025 | C-15（L1 结构化字段与结构性 digest） | 同上 | `::test_l1_log_carries_structured_response_fields` / `::test_structural_digest_without_body_capture` | L1 记录同列 `resp_*` 字段；未采体时 digest 为结构性摘要（状态码\|类型\|长度\|错误码） | L3 | A |
| TT-LOGS-026 | C-15 + 红线 2/3/6（开启脱敏、上限、白名单） | 同上 + `openbase/core/mask.py` | `::test_summary_captured_and_masked_when_switch_on` / `::test_deep_response_keeps_keys_only` / `::test_credential_headers_are_never_captured` / `::test_allowlist_threaded_into_observation` / `::test_observation_with_payload_reports_real_bytes_and_summary` | 开启后摘要产出且**必经脱敏**（手机号 `138****5678`）；过深只留键名；凭据头永不采；白名单透传生效；采体后 `resp_bytes` 为真实字节 | L1 | A |
| TT-LOGS-027 | C-15（读体口径矩阵） | 同上（`should_capture_body`） | `::test_should_capture_body_matrix` | 仅 JSON 类响应可读体；SSE/非 JSON **永不读体** | L2 | A |
| TT-LOGS-028 | C-16（成功/业务错误/不可达三路径同结构） | `openbase/modules/proxy/upstream_observe.py` + `openbase/modules/proxy/__init__.py` | `tests/test_proxy_upstream_observe.py::test_segment_records_status_duration_and_digest` / `::test_segment_unreachable_keeps_same_structure` / `::test_generic_proxy_records_upstream_segment` | 三路径专段字段集合一致（不可达无 status/digest、含 `upstream_error`）；通用通道接入统一出口 | L1 | A |
| TT-LOGS-029 | C-16（业务错误码提取） | `upstream_observe.extract_upstream_error_code` | `::test_segment_extracts_business_error_code` / `::test_error_code_extraction_returns_none_for_unsupported_payloads` | 支持顶层 `code` 与 `error.code`；不支持形态返回 None 不抛错 | L1 | A |
| TT-LOGS-030 | C-16（摘要脱敏/层级/白名单） | 同上 + `mask.py` | `::test_segment_capture_masks_summary` / `::test_segment_capture_deep_payload_keeps_keys_only` / `::test_segment_capture_allowlist_keeps_attribution_field` | 开关下摘要经脱敏；层级 >5 只留键名；白名单字段保留原值（归因可用） | L1 | A |
| TT-LOGS-031 | C-16（同请求计数与最近值） | `upstream_observe.publish_upstream_observation` | `::test_publish_accumulates_calls_and_keeps_latest` | 同请求多次调用累加 `upstream_calls` 并保留最近一次专段 | L1 | A |
| TT-LOGS-032 | C-17（归因矩阵） | `scripts/test_log_analyze.py` | `tests/test_test_log_analyze.py::test_attribute_matrix_covers_design_rows` / `::test_attribute_prefers_upstream_over_gateway_5xx` | 设计 §11.5 矩阵逐行覆盖（鉴权/信任链/K03/网络/上游/契约）；上游 5xx **优先归因上游** | L1 | A |
| TT-LOGS-033 | C-17（报告输出与退出码） | 同上 | `::test_analyze_writes_report_with_attribution` / `::test_analyze_never_prints_response_plaintext` / `::test_analyze_all_pass_returns_zero` / `::test_analyze_no_records_is_pending` / `::test_analyze_run_id_filter` | 输出 `<run_id>-analysis.md`（归属层/首现/request_id/建议动作）；**报告不含响应明文**；退出码 0/1/2；按 run 过滤 | L1 | A |
| TT-LOGS-034 | C-18（凭据遮蔽） | `openbase/core/mask.py::mask_sensitive` | `tests/test_mask.py::test_sensitive_keys_are_masked` / `::test_nested_credential_container_keeps_shape_only` | `authorization/token/api_key/password/secret/cookie` → `***`；嵌套容器仅留形状 | L1 | A |
| TT-LOGS-035 | C-18（个人隐私掩码） | 同上 | `::test_phone_keeps_prefix_and_suffix` / `::test_id_card_keeps_head_and_tail` / `::test_email_local_part_is_masked` / `::test_privacy_masked_inside_free_text` | 手机号保留首尾、证件号保留头尾、邮箱本地部掩码、自由文本中的隐私同样命中 | L1 | A |
| TT-LOGS-036 | C-18 + 红线 6（画像域整体遮蔽） | 同上 | `::test_redacted_domain_keeps_shape_not_content` / `::test_redacted_domain_is_exact_match` / `::test_redacted_domain_scalar_and_array_values_keep_shape_only` | `portraits` 等域整体遮蔽（仅留类型与规模）；精确匹配不误伤同名前缀键 | L1 | A |
| TT-LOGS-037 | C-18 + 红线 3（2KB/层级上限） | 同上（`observe_payload(max_bytes=2048)`） | `::test_depth_over_limit_is_collapsed` / `::test_oversized_payload_keeps_digest_and_keys_only` / `::test_summary_is_produced_under_limit` / `::test_oversized_and_deep_array_payloads_keep_array_marker` | >2KB 或层级 >5 → 只留 digest + 键名清单；未超限产出摘要；数组超限保留数组标记 | L1 | A |
| TT-LOGS-038 | C-18（白名单与 digest 稳定性） | 同上 | `::test_allowlist_keeps_raw_value_for_attribution` / `::test_default_allowlist_is_empty_means_mask_all` / `::test_digest_is_stable_and_differs_by_content` / `::test_allowlist_supports_subtree_prefix_and_ignores_blank_entries` | 白名单保留原值；默认空 = 全遮蔽；digest 稳定且随内容变化；支持子树前缀、忽略空项 | L1 | A |
| TT-LOGS-039 | C-18（边界形态） | 同上 | `::test_non_json_body_is_masked_preview` / `::test_json_array_payload_is_summarized_with_size` / `::test_scalar_and_empty_payloads_are_handled` / `::test_observe_payload_none_means_not_captured` | 非 JSON 走脱敏预览；数组摘要带规模；标量/空载荷不抛错；`None` 视为未采集 | L3 | A |
| TT-LOGS-040 | C-19 + 红线 1（三开关默认关 / env 开启） | `openbase/settings.py` | `tests/test_capture_switches.py::test_capture_switches_default_off` / `::test_capture_switches_env_override` / `::test_capture_switch_state_payload` | 三开关默认全关；env 置 1 生效；开关状态快照载荷正确 | L1 | A |
| TT-LOGS-041 | C-19 + 红线 4（生产永久关） | `openbase/settings.py`（属性层收敛） | `::test_capture_is_permanently_off_in_production` | `OPENBASE_ENV=production` 时置 1 **仍恒关** | L1 | A |
| TT-LOGS-042 | C-19 + 红线 5（开关留痕与降级） | `openbase/modules/audit/capture_switches.py`、`openbase/demo_app.py` | `::test_record_switch_state_off_logs_without_db` / `::test_record_switch_state_on_persists_audit_row` / `::test_record_switch_state_db_failure_is_degraded` / `::test_record_switch_state_tolerates_rollback_failure` / `::test_record_switch_state_db_disabled_is_silent` | 开启时落 `capture.switch` 审计行；关闭时仅日志；落库/回滚失败均降级不阻断 | L1 | A |

### 3.4 G4 专用代理族接线（批 5：C-16 补全）

| TT-ID | 设计条目 | 代码落点 | 测试文件 :: 用例名 | 预期结果 | 级别 | 执行面 |
|-------|---------|---------|-------------------|---------|:----:|:------:|
| TT-LOGS-043 | 批 5（标识对齐不变量） | `openbase/modules/proxy/upstream_observe.py::UPSTREAM_SYSTEM_*` | `tests/test_specialized_proxy_upstream_observe.py::test_upstream_system_identifiers_align_with_generic_channel` | `UPSTREAM_SYSTEM_*` 必须命中通用通道 `PROXY_SYSTEMS` 路由键（同一上游一套标识） | L1 | A |
| TT-LOGS-044 | 批 5（四族非流式出口成功/业务错误） | `dps_proxy/__init__.py`、`llm_proxy/__init__.py`、`rag_proxy/__init__.py` | `::test_dps_forward_publishes_success_segment` / `::test_llm_forward_publishes_success_segment` / `::test_rag_forward_publishes_business_error_code` / `::test_rag_multipart_forward_publishes_segment` | 各族成功路径均产出 `upstream_system`/`upstream_status`/`upstream_duration_ms`/digest；RAG 业务错误携 `upstream_error_code`；multipart（202）同样记段 | L1 | A |
| TT-LOGS-045 | 批 5（多出口：memory 双出口） | `openbase/modules/proxy/memory_proxy.py` | `::test_memory_forward_and_raw_publish_segments` | `_forward` 与 `_forward_raw` **两条出口**均补记专段 | L1 | A |
| TT-LOGS-046 | 批 5 + 缺陷 AD-20260914-01（不可达路径） | `dps_proxy/__init__.py`（含 `_dps_consecutive_failures` 模块级初值修复） | `::test_dps_forward_unreachable_publishes_error_segment` | 上游连接异常 → 专段结构一致（无 status/digest + `upstream_error`）；既有 `BaseError(SYS_UPSTREAM_ERROR)` 语义保持；降级分支可正常执行（原 `NameError` 已修） | L1 | A |
| TT-LOGS-047 | 批 5（流式头部级专段与错误体） | `rag_proxy/__init__.py::_forward_sse`、`llm_proxy/__init__.py::_forward_sse` | `::test_sse_forward_publishes_header_level_segment` / `::test_sse_upstream_error_publishes_payload_segment` | 2xx 仅头部级（status/首字节耗时/Content-Type，**无 digest**）且首事件前落位；4xx/5xx 含 `upstream_error_code` | L1 | A |
| TT-LOGS-048 | 批 5 + 红线 1/2/4（开关三态） | `upstream_observe.publish_upstream_response` + `capture_options` | `::test_capture_switch_off_keeps_no_summary` / `::test_capture_switch_on_masks_summary` / `::test_capture_is_permanently_off_in_production` | 默认关零摘要；开启摘要经脱敏（原文不出现）；生产恒关 | L1 | A |
| TT-LOGS-049 | 批 5（向后兼容） | 四族 `_forward`（`request` 可选关键字参数） | `::test_forward_without_request_skips_observation_silently` | 不传 `request` → 转发返回正常、零观测、不抛错 | L1 | A |
| TT-LOGS-050 | 批 5（端到端：专段与网关侧同列） | 全链路（`/api/v1/dps-proxy/portraits`） | `::test_dps_proxy_endpoint_records_segment_in_audit` | 同一条审计记录含 `upstream_system=dps` / `upstream_status` / `resp_status`（C-16 上游侧与 C-15 网关侧**同行**） | L1 | A |

### 3.5 G5 契约与回归门禁

| TT-ID | 门禁项 | 命令 | 预期结果 | 执行面 |
|-------|-------|------|---------|:------:|
| TT-LOGS-051 | 代理族定向回归（转发主路径零回归） | `python -m pytest tests/test_proxy_upstream_observe.py tests/test_specialized_proxy_upstream_observe.py tests/test_proxy_quota.py tests/test_proxy_auth.py tests/test_proxy_outbound_matrix.py tests/test_dps_proxy.py tests/test_llm_proxy.py tests/test_rag_proxy.py tests/test_memory_proxy.py -q` | 全绿，0 failed / 0 errors | A |
| TT-LOGS-052 | 全量回归 | `python -m pytest tests -q` | 通过率 ≥95%；失败项须定性（环境抖动 vs 缺陷）并复核 | A |
| TT-LOGS-053 | 覆盖率门禁（新增/主改模块 ≥80%） | `python -m pytest <本流用例集> --cov=openbase.core.mask --cov=openbase.core.logging_setup --cov=openbase.modules.proxy --cov=openbase.modules.audit.capture_switches --cov=openbase.modules.testing --cov-report=term-missing` | 新增/主改模块覆盖率 ≥80%（`upstream_observe` 目标 100%） | A |
| TT-LOGS-054 | 静态质量 | `python -m ruff check openbase tests` | **0 错**（`All checks passed!`） | A |

### 3.6 G6 沙箱外执行面与跳过项

| TT-ID | 项 | 依据 | 预期结果 | 处置 | 执行面 |
|-------|----|------|---------|------|:------:|
| TT-LOGS-055 | 真实编排窗口人工 E2E（**开启采集开关**，含专用代理族通道） | 方案 §6 可检索性/响应级归因；DevLogReport §14#1 | 真实 7 服务 + 前端下开轮跑通；`case_id` 检索命中率 ≥95%；失败步骤可定位「归属层 + 上游错误码」 | 待联调窗口执行并留证 | B（PENDING） |
| TT-LOGS-056 | 性能：日志写入不阻塞主请求，P99 增量 <5ms | 方案 §6 性能；DevLogReport §14#2 | 压测对比达标 | 随压测窗口量化 | B（PENDING） |
| TT-LOGS-057 | `service-orchestrator checkall` 复跑（27 PASS 基线） | C-6；DevLogReport §14#3 | 27 PASS / 0 FAIL / 0 SKIP | 待联调窗口（本窗口未启动 7 服务编排，禁伪造） | B（PENDING） |
| TT-LOGS-058 | 前端关键页 Playwright 走查（含 `/system/test-records`） | C-12；`openbase-ui/playwright.config.ts`（执行面说明：需前端 5173 运行态） | 关键页 9/9 PASS、`console.warn=0`（L4 网络层断言） | 待统一前端运行态窗口；承 S6 已达标证据（`doc/test/evidence/s6/ui-e2e/**`） | B（PENDING） |
| TT-LOGS-059 | 批 3（C-13/C-14 门禁口径打通） | 方案 §9.1 决议 **D-1 = ②** | — | **经决议不做**（不适用，非缺陷）；测试报告中登记跳过项与理由 | 不适用 |

> **v1.1.0 执行回填（联调窗口真实面，2026-09-14 晚）**：TT-LOGS-057（`checkall`）→ **✅ 达成**（27 PASS / 0 FAIL / 0 SKIP）；TT-LOGS-058（前端关键页 E2E）→ **✅ 达成**（9/9 PASS，含 Q-FE-4b）；TT-LOGS-055（真实人工 E2E，采集开关开启）→ **🚧 部分达成**（6 步 5 PASS + 归因 3/3 全部定位归属层；1 例 `llm-proxy` 502 定性为 CPU 推理 23s > 网关上游超时 20s 的**环境性**）；TT-LOGS-056（性能/容量）仍 **PENDING**（未压测）。另：TT-LOGS-015（C-6 行为面）随 TT-057 一并关闭。详见测试报告 §13 与回溯审计 §9。

---

## §4 覆盖矩阵与缺口分析

### 4.1 覆盖矩阵（模块 × 用例类型）

| 模块 / 面 | 契约(T1) | 接口(T2) | 集成(T3) | 回归 | 覆盖率 | 安全/合规 | 目标用例数 | 现状 |
|-----------|:-------:|:-------:|:-------:|:----:|:-----:|:--------:|:---------:|------|
| 日志落盘（`core/logging_setup`） | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 6 | 达成（TT-001~006） |
| 用例上下文（`audit` + 协议头） | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 8 | 达成（TT-007~013） |
| 聚合脚本（`scripts/test_log_aggregate.py`） | — | ✅ | ✅ | ✅ | ✅ | ✅ | 8 | 达成（TT-014） |
| 编排器日志重定向（`service-orchestrator.ps1`） | — | — | ⭕ | ✅ | — | — | 1 | 结构面达成；行为面 PENDING（TT-015/057） |
| 人工结论入口（`modules/testing`） | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 23（＋前端） | 达成（TT-016~022） |
| 前端测试模式与面板（`openbase-ui`） | ✅ | ✅ | ⭕ | ✅ | ✅ | — | 2 | 结构面达成；浏览器面 PENDING（TT-023/058） |
| 网关响应观测（`audit` 响应侧） | — | ✅ | ✅ | ✅ | ✅ | ✅ | 13 | 达成（TT-024~027） |
| 上游专段（`proxy/upstream_observe` + 通用通道） | — | ✅ | ✅ | ✅ | ✅ | ✅ | 9 | 达成（TT-028~031） |
| 错误归因分析器（`scripts/test_log_analyze.py`） | — | ✅ | ✅ | ✅ | ✅ | ✅ | 7 | 达成（TT-032~033） |
| 统一脱敏器（`core/mask`） | — | ✅ | ✅ | ✅ | ✅ | ✅ | 21 | 达成（TT-034~039） |
| 三开关与留痕（`settings` + `capture_switches`） | — | ✅ | ✅ | ✅ | ✅ | ✅ | 8 | 达成（TT-040~042） |
| 专用代理族接线（四族 + 通用通道收敛） | — | ✅ | ✅ | ✅ | ✅ | ✅ | 14 | 达成（TT-043~050） |
| 门禁（静态质量 / 回归 / 覆盖率） | — | — | — | ✅ | ✅ | — | 4 | 达成（TT-051~054） |
| 真实编排窗口（人工 E2E / 性能 / checkall / 浏览器） | — | — | ⭕ | — | — | — | 4 | **PENDING**（TT-055~058） |

> 图例：✅ 已覆盖（有对应用例且本窗口实测）｜⭕ 部分覆盖（结构面覆盖、真实面 PENDING）｜— 不适用。

### 4.2 缺口分析

| 模块 | 现有用例数 | 目标用例数 | 缺口 | 等级 | 处置 |
|------|:---------:|:---------:|:----:|:----:|------|
| 真实编排窗口（人工 E2E / 性能 / checkall / 浏览器走查） | 0（结构面 3） | 4 | **+4** | **P1** | 联调窗口执行并回填（TT-055~058）；已登记技术债（性能/容量） |
| 编排器日志重定向行为面 | 0 | 1 | +1 | P2 | 随 checkall 复跑一并关闭（TT-015/057） |
| 前端面板真实浏览器交互 | 0 | 1 | +1 | P2 | 随前端运行态窗口执行（TT-023/058） |
| 其余模块 | — | — | **0** | — | — |

> **P0 缺口 = 0**（无核心业务/安全面缺口）。P1 缺口 4 条均属**真实环境依赖**（非代码缺陷），已在本窗口如实登记 PENDING 并给出关闭条件。

### 4.3 度量指标（本窗口）

| 指标 | 目标 | 本窗口 |
|------|:----:|:------:|
| 用例覆盖率（已有/目标） | ≥90% | 55 / 59 = **93%** |
| 硬断言比例（含 L1 硬断言） | ≥60% | 55 / 59 = **93%**（仅 L2/L3 断言者 4 条：TT-003/025/027/039） |
| 软断言数量 | 0 | **0** |
| 巡检覆盖率（本流为后端为主，T3a 以服务内链路替代） | 100% | 100%（链路：六族转发 + 审计合流） |
| 人工测试执行率（计划项） | 100% | 沙箱内计划项 100%；沙箱外 4 项 PENDING（已批准延期） |
| 缺陷逃逸率 | ≤20% | 本窗口独立复算新增发现**缺陷 0**（3 例失败定性为既有夹具顺序污染，见测试报告 §缺陷闭环） |

---

## §5 未纳入项与跳过项

| 项 | 类型 | 理由 | 影响 | 补救计划 | 批准 |
|----|------|------|------|---------|------|
| C-13（`gate_aggregate.py` 增人工测试记录章节） / C-14（测试报告登记人工 run） | **跳过（经决议不做）** | 方案 §9.1 **D-1 = ②**（批 1+批 2 闭环；批 3 不纳入本流） | 门禁聚合不自动消费人工 run（人工结论仍可经 `/system/test-records` 与聚合脚本查看） | 如需并入自动化门禁，另立需求 | 项目负责人（决议冻结） |
| 真实 7 服务在线人工 E2E（开关开启） | 环境依赖 | 沙箱内无法提供完整 7 服务 + IdP + 前端运行态（承 S7 环境检查报告 §1） | 真实摘要/归因数据未采集 | TT-LOGS-055（联调窗口） | 待联调窗口批准 |
| 性能量化（P99 增量） | 环境依赖 | 需压测窗口与稳定基线 | 性能门禁未关闭 | TT-LOGS-056 | 待压测窗口批准 |
| `checkall` 复跑 / 前端浏览器走查 | 环境依赖 | 同上（服务未编排启动） | 行为面未复现 | TT-LOGS-057/058 | 待联调窗口批准 |

---

## §6 追溯说明与维护规则

### 6.1 追溯链

```
方案（设计 v1.5.0）
  §5 改造清单 C-1~C-19（含批 5）─┐
  §6 验收标准 9 行 ──────────────┼─▶ TT-LOGS-001~059 ─▶ 测试报告 § 执行结果 ─▶ 测试回溯对比审计
  §11.2 红线 1~6 ────────────────┘        （本文件）           （实测证据）          （逐项核对）
```

- **设计要求 → 用例**：每条设计条目至少 1 条用例（C-1~C-19、批 5 全覆盖，覆盖率见 §4.3）。
- **用例 → 代码**：每条用例给出代码落点（模块/函数），与 DevLogReport §10 追溯矩阵一致。
- **用例 → 结果**：执行结果与证据路径见《OpenBase-S7-人工端到端测试日志落盘-测试报告-v1.0.0》§3/§4 与 `doc/test/evidence/manual/t4-*.xml|txt`。

### 6.2 维护规则

1. 设计条目变更（新增/修改 C-x）必须同步新增或修订用例并在 §修订历史递增版本；
2. 沙箱外项关闭后，须将其执行面 `B` 更新为 `A` 并补证据路径（禁止直接改写为 PASS 而无证据）；
3. 用例名与文件路径若发生重构，须同步更新本表（保持「仓内真实存在」）；
4. 本文件与测试报告、回溯审计报告三者版本须同步递增（`project-document-management` §6）。

---

> **文档结束**。本文件为「人工端到端测试日志落盘」流 Step 4 测试用例基线（[Review] v1.0.0，59 条 TT-LOGS）；用例名与路径均取自仓内真实文件，沙箱外 4 项 PENDING 未伪造结论。

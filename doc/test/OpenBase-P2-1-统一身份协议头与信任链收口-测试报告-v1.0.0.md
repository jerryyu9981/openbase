# OpenBase-P2-1-统一身份协议头与信任链收口-测试报告-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-P21-TEST-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Review]（T1~T10 用例与断言 + S1b 段门禁五项自检全绿；待人工批准进入部署/S2 移交） |
| 日期 | 2026-09-08 |
| 作者 | AT-OpenBase（P2-1 测试） |
| 存放 | doc/test/ |
| 版本主题 | P2-1（S1b）T1~T10 用例与断言矩阵、分组回归策略（Windows 单进程 C 层崩溃规避）、回归结果、覆盖率口径记录（protocol_headers ≥90% 保持）、S1b 段门禁五项自检小节、R3 补测与移交登记 |
| 上游依据 | 《OpenBase-P2-1-统一身份协议头与信任链收口设计草案》v1.1.0 §10（T1~T10 RED 断言编号）；《OpenBase-P2-1-统一身份协议头与信任链收口立项方案》v1.1.0 §5 验收 / §9 里程碑；《OpenBase-多系统联调联试分阶段版本规划（子系统纵切）》v1.3.0（S1b 门禁）；P2-1 DevLogReport v1.0.0 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-08 | AT-OpenBase（P2-1 测试） | 初始版本：T1~T10 用例与断言矩阵、RED→GREEN 摘要、分组回归结果、覆盖率口径、S1b 段门禁五项自检小节、R3 补测与移交登记 |

---

## 1. 基本信息

- 测试对象：OpenBase 主仓 main（P2-1 批次 3 收口 HEAD；前置提交链 25b65d7 → 9a0aa49 + 批次 3 代码提交 + 本文档提交）。
- 测试环境：Windows（Python 3.10.11 / pytest / ruff / SQLite 本地库，模块级独立 DB 文件）；真实凭据类用例默认 skip（OPENBASE_TEST_REAL_INFRA 未置位）。
- 测试结论：**通过**。全量分组回归全绿；ruff 0；覆盖率按既有口径记录（protocol_headers ≥90% 保持）；S1b 段门禁五项自检全绿。

## 2. 分组回归运行策略说明（Windows 平台单进程 C 层崩溃规避）

- 背景：starlette BaseHTTPMiddleware + anyio 多实例在 Windows 单进程叠加执行存在非确定性 C 层崩溃（TD-新增-009）。`tests/conftest.py` 以 `WindowsSelectorEventLoopPolicy` 缓解后仍按**分组子进程隔离**执行。
- 编排：`python scripts/run_regression.py --group-size 3`——按测试文件分组（每组 ≤3 文件），每组独立 pytest 子进程（`-p no:cacheprovider`），崩溃组自动重试（≤3 次）；先 ruff（0 错误放行）再分组 pytest 最后汇总。覆盖率运行附 `--cov`（分组 `--cov-append` 合并）。

## 3. T1~T10 用例与断言矩阵（对照设计草案 §10 RED 断言）

| 任务 | 测试文件 | 用例数 | §10 断言覆盖 | 结果 |
|------|---------|:---:|-------------|:---:|
| T1（K01/OB-3） | tests/test_protocol_headers_lib.py + test_proxy_outbound_matrix.py | 21 + 11 | T1-1~T1-12 | ✅ 全绿（25b65d7） |
| T2（K03） | tests/test_verdict_k03.py | 14 | T2-1~T2-10 | ✅ 全绿（51c6657） |
| T3（K02/SYS-1） | tests/test_protocol_headers_lib.py（T3 段）+ test_inbound_header_gate.py + test_api_keys.py | — | T3-1~T3-9 | ✅ 全绿（25b65d7） |
| T4（K07/SYS-1） | tests/ K07 断言 + scripts/k07_endpoint_matrix.py | — | T4-1~T4-5 | ✅ 全绿（09f28fa） |
| T5（OB-6） | tests/test_service_agent_outbound.py | 17 | T5-1~T5-7 | ✅ 全绿（9a0aa49） |
| T6（OB-12，Q-D） | tests/test_role_intertranslate.py | 27 | T6-1~T6-6 | ✅ 全绿（9a0aa49） |
| T7（OB-8） | tests/test_org_alias_code.py | 24 | T7-1~T7-7 + 附断言 | ✅ 全绿（2fe18b2） |
| T8（OB-13） | tests/test_audit_identity_chain.py | 12 | T8-1~T8-7 | ✅ 全绿（0f65363） |
| T9（OB-9） | tests/test_verify_env.py | 6 | T9-1~T9-6 + 产物/复用断言 | ✅ 全绿（ef0d028） |
| T10（回归/门禁） | scripts/run_regression.py --group-size 3 | 全仓 | T10-1~T10-6 | ✅ 见 §4/§5/§6 |

### 3.1 批次 3 RED→GREEN 摘要（T7/T8/T9 断言编号逐条）

| 断言 | RED 复现（回退基线观察） | GREEN 载体 |
|------|------------------------|-----------|
| T7-1 dps X-Org-ID == X-Tenant-ID | 基线出站仍取 `ctx.org_id` 独立链（ghost-org ≠ acme）→ 断言失败 | test_t7_1_dps_org_alias_equals_tenant / _equals_mapped_tenant |
| T7-2 llm/memory 出站同源别名 | 基线取独立 org_id 中间态（org-001 ≠ tenant-001）→ 失败 | test_t7_2_llm_org_alias_same_source / test_t7_2_memory_org_alias_same_source |
| T7-3 enforce_org_alias 403 | 基线无 enforce 参数（TypeError）→ 失败 | test_t7_3_enforce_org_alias_mismatch_raises_403 / _consistent_passes / _default_off_compat / test_t7_3_dps_proxy_enforce_org_alias_conflict_403 |
| T7-4 validate_dps_code_map | 基线无 dps_code_map 模块（ImportError）→ 失败 | test_t7_4_valid_map_passes / _empty_map_is_valid_default / _invalid_json_rejected / _wrong_schema_version_rejected / _unknown_tenant_code_rejected / _dps_ids_empty_rejected / _duplicate_code_rejected |
| T7-5 冲突检测 | 同上（模块不存在）→ 失败 | test_t7_5_conflict_detected / test_t7_5_no_conflict_when_clean |
| T7-6 deprecated 默认值 | 基线 settings 无 deprecated_dps_defaults（AttributeError）→ 失败 | test_t7_6_deprecated_defaults_reported / _empty_when_unset / test_t7_6_deprecation_warnings_text |
| T7-7 对账脚本 0 未决 | 基线 scripts/audit_dps_code_map.py 不存在（FileNotFound）→ 失败 | test_t7_7_audit_report_clean_map / _conflict_exit_nonzero / test_t7_config_example_dps_code_map_file / test_t7_baseline_doc_registered |
| T8-1 identity schema 六键 | 基线 identity_audit 无 build_identity_section（ImportError）→ 失败 | test_t8_1_proxy_outbound_identity_schema_complete / _delegation_audit_identity_schema_complete / _lifecycle_purge_audit_merged_identity_section / test_t8_1_build_identity_section_six_keys_present |
| T8-2 委托出站审计抽样一致 | 同 T8-1（ImportError）→ 失败 | test_t8_2_delegated_outbound_audit_matches_agent_header |
| T8-3 proxy.outbound 钩子同 request_id | 基线 AuditMiddleware 无 _persist_outbound_proxy_hop（AttributeError）→ 失败 | test_t8_3_record_proxy_hop_lands_row_same_request_id / test_t8_3_audit_middleware_persists_outbound_hop |
| T8-4 agent 直连审计含 agent_id+source+域+动作 | 同 T8-1 → 失败 | test_t8_4_agent_audit_identity_carries_source_domain_action |
| T8-5 中间件链路 extra.identity | 基线 _record 未并 identity（缺键断言）→ 失败 | test_t8_5_audit_middleware_record_merges_state_identity |
| T8-6 既有字段不回退 | 同 T8-1（ImportError）→ 失败 | test_t8_6_legacy_columns_kept / test_t8_6_delegation_audit_legacy_detail_intact |
| T8-7 U4 边界文档化 | 设计草案 D-OB13-1~3 在基线即存在（本断言设计期即绿，随批次 3 纳入） | test_t8_7_u4_boundary_documented |
| T9-1 contract 存在且 schema 通过 | 基线 contract.json 缺 enforce_token_version/k03_bypass_whitelist/tracking → 断言失败；clean run 报告缺失 | test_t9_1_contract_exists_and_schema_valid / test_t9_1_script_clean_run_exit_zero |
| T9-2 脚本可执行/退出码/--fail-fast | 基线 verify-env.ps1 不存在 → report missing（RED） | test_t9_2_3_5_warn_scenarios_reported（exit 1）/ test_t9_2_fail_fast_aborts_nonzero |
| T9-3 白名单矩阵对账可定位 | 同 T9-2 | test_t9_2_3_5_warn_scenarios_reported（WHITELIST_MISMATCH expected/rogue-source 断言） |
| T9-4 映射对账冲突输出 | 同 T9-2 | test_t9_4_6_mapping_errors_and_report_lists（DPS_CODE_MAP_CONFLICT/INVALID，exit 2） |
| T9-5 DB 检查位 | 同 T9-2 | test_t9_2_3_5_warn_scenarios_reported（DB_CHECK_UNREACHABLE） |
| T9-6 报告含 WARN/ERROR 清单 | 同 T9-2 | test_t9_4_6_mapping_errors_and_report_lists（severities WARN+ERROR；summary.exit_code=2） |

## 4. 回归结果与跳过原因（T10-1/T10-4）

### 4.1 回归结果

- 执行：`python scripts/run_regression.py --group-size 3`（19 组子进程隔离，崩溃组自动重试 ≤3）。
- 汇总（批次 3 实测）：**556 passed / 0 failed / 4 skipped**。
- 结论：全量分组回归全绿、ruff 0；P2-1 全部断言用例 + 存量 proxy/服务 Key/调用方回归（test_proxy_auth、test_dps_proxy、test_llm_proxy、test_rag_proxy、test_memory_proxy、test_api_keys* 等）无回退。

### 4.2 skip 原因

- 4 skipped = `test_storage_s3_real.py` 真实存储凭据类用例（需 `OPENBASE_TEST_REAL_INFRA=1`），按既有模块级 skip 跳过，与存量基线行为一致，非 P2-1 引入。

## 5. 覆盖率复核（T10-3，按既有口径记录）

| 项 | 实测 | 目标/说明 |
|----|------|----------|
| 全仓 openbase 行覆盖率 | `run_regression.py --cov --group-size 3` 分组聚合实测 = **86%**（6763 语句 / 925 miss） | 既有口径记录（86% 级，随新增语句数微幅变化）；全仓 ≥90% 需 R3 补测（端点/DB 驱动路径缺口，登记 R3-1） |
| protocol_headers 包 | **92%**（589 语句 / 46 miss）：inject 98% / identity_audit 100% / role_map 90% / validate 96% / identity_context 97% / dps_code_map 78% | **保持 ≥90% 门槛** |
| 新增模块覆盖缺口 | dps_code_map 78%（branch 位：DB 探测/离线降级分支）；端点/DB 驱动与 Windows TestClient 线程桥采集边界（同 TD-新增-009/既有基线口径） | 随 R3 补测（遗留登记 R3-1） |

## 6. S1b 段门禁自检小节（规划 v1.3.0 S1b / T10-5，五项逐条）

| # | 门禁自检项 | 核对结论 | 证据 |
|---|--------|:---:|------|
| G-1 | **协议头规范 v1.0 发布物齐备**（规范文档+共享包+出站矩阵/双通道用例） | ✅ | `doc/design/OpenBase-协议头规范-v1.0.md`（[Approved]，v1.0.1 批准注记）；`openbase/modules/protocol_headers/` 六模块 + dps_code_map/identity_audit；`tests/test_protocol_headers_lib.py` T3-1 发布物/常量值断言全绿；出站矩阵/双通道用例见 test_proxy_outbound_matrix.py / test_service_agent_outbound.py |
| G-2 | **非白名单带头 403（enforce）用例** | ✅ | `tests/test_inbound_header_gate.py::test_t2_5_enforce_403_untrusted_identity_headers`（enforce 开 → 403 `PERM_UNTRUSTED_IDENTITY_HEADER`）；`test_t3_7_strip_removes_headers_without_403`（剥离过渡期）；`test_api_keys.py::test_identity_context_ignores_untrusted_headers`；settings `enforce_inbound_identity_headers` 两段式开关 |
| G-3 | **服务账号用例全绿**（sk-agent 四 proxy 出站+审计+ob_k_ 主体映射） | ✅ | `test_service_agent_outbound.py`（T5-1~T5-7：dps/rag/memory/llm 四 proxy sk-agent 出站四头 + X-Proxy-Source/X-Agent-Id；agent 匿名直连写拒绝；agent 出站审计含 agent_id+source+域；U1 密钥面发放/吊销回归）；`test_identity_t1.py`（sk-agent 密钥面）；`test_audit_identity_chain.py` T8-4（agent 直连审计含 agent_id+source+域+动作） |
| G-4 | **verify-env 可用** | ✅ | `scripts/verify-env.ps1` 实跑：`warnings=9 errors=0 exit_code=1`（本环境 dps_default_* deprecated + 本地服务未启动 + 白名单未配置 → 全部 WARN 非阻断，符合 §9.2 雏形语义），报告落盘 `scripts/verify-env-report.json` → 证据副本 `doc/test/evidence/verify-env-report.json`；`tests/test_verify_env.py` T9-1~T9-6（clean exit 0 / WARN exit 1 / ERROR exit 2 / --fail-fast 非 0） |
| G-5 | **K07 模板 v1.0 + 角色互译表发布物 [Review] 待人工批准**（文档版本/修订历史登记） | ✅ | `doc/design/OpenBase-端点过滤矩阵模板-v1.0.md`（v1.0.0，[Review] 待人工批准，修订历史登记 v1.0.0 行）+ `doc/design/OpenBase-角色互译表-v1.0.md`（v1.0.0，[Review] 待人工批准，修订历史登记 v1.0.0 行）；`scripts/k07_endpoint_matrix.py` 骨架 + `tests/test_k07_endpoint_matrix.py` 全绿；台账回写见 DevLogReport §9 与任务卡 v1.3.0（K07 已发布 / OB-12 已完成） |

> 自检说明：S1b 段门禁的 ⑤ 发布物（K07 端点过滤矩阵模板 v1.0 / 角色互译表 v1.0）**维持 [Review] 状态、随本文档一并提交人工批准**；本文档提交后经人工门禁回写 [Approved]，不在此批次由开发侧自行批准（登记于遗留项 §8「评审人工复核点」）。

### 6.1 台账回写核对（T10-6）

| 台账对象 | 回写内容 | 依据 |
|---------|---------|------|
| 数据隔离实现任务卡（v1.2.0 → v1.3.0） | K01/K03（OB-3）✅已完成（实施）；K02 规范 v1.0 已发布 + OpenBase 试点完成；K07 模板 v1.0 已发布；K08 补充委托头唯一签发规范收口；升级项 OB-6/OB-8/OB-9/OB-12/OB-13 ✅已完成（P2-1），OB-7/OB-10 外移 | P2-1 DevLogReport v1.0.0 §9；设计草案 §11.1 台账登记 |
| P2-1 立项方案（v1.0.0 → v1.1.0） | [Draft] → [Approved]，批准日期 2026-09-07，批准注记 + 修订行 | 用户对话确认 + 里程碑 ① |
| P2-1 设计草案（v1.0.0 → v1.1.0） | [Draft] → [Approved]，批准日期 2026-09-08，批准注记 + 修订行 | 用户对话确认「按这个方案来」+ Q-D-1~3 |
| 协议头规范 v1.0 | [Draft] v1.0.0 → [Approved] v1.0.1（批准注记 + 修订行；S1b 门禁项①发布物） | 设计草案 [Approved]（2026-09-08 人工批准 Q-D-1~3）+ 发布物齐备核对（T3-1） |
| 端点过滤矩阵模板 v1.0（K07） | v1.0.0 发布物 **维持 [Review] 待人工批准**（修订历史登记于批次 2；S1b 门禁项⑤，本批次不自行批准） | 任务卡 v1.3.0 K07 已发布（填报随 S2-S5）；随本文档提交人工门禁 |
| 角色互译表 v1.0（OB-12） | v1.0.0 发布物 **维持 [Review] 待人工批准**（修订历史登记于批次 2；S1b 门禁项⑤，本批次不自行批准） | 任务卡 v1.3.0 OB-12 已完成（Q-D-1~3 结论在文档内）；随本文档提交人工门禁 |
| DPS-code 映射基线登记示例 v1.0.0 | 新增发布物（T7，登记式基线示例；随实施登记） | P2-1 DevLogReport v1.0.0 §9；config/dps_code_map.example.json |

## 7. 环境遗留与已知限制

| 项 | 说明 |
|----|------|
| 真实服务探活 | verify-env upstream/DB 探活在本地开发环境为 WARN（服务未启动/DB 未起）；S1b 只要求雏形可用，fail-fast 语义随 R3 收紧（R3-3） |
| coverage 采集边界 | Windows TestClient 线程桥 → 端点驱动模块覆盖低估（登记 R3-1，与既有口径一致） |
| 强模式开关默认关 | enforce_org_alias/enforce_inbound_identity_headers/enforce_token_version 等默认 False（两段式发布第一段兼容）；第二段随部署窗口开启（R3-2） |
| dps_code_map 生产登记 | 默认空表；.env 中 dps_default_* 触发 verify-env WARN（T7-6 语义），部署段经 audit_dps_code_map.py 登记入基线（R3-4） |
| 评审人工复核点（[Review] 项） | K07 端点过滤矩阵模板 v1.0 / 角色互译表 v1.0 发布物**维持 [Review] 待人工批准**（版本 v1.0.0、修订历史登记于批次 2）；S1b 门禁项⑤随本文档提交人工门禁回写 [Approved]，本批次不自行批准 |

## 8. 结论

- 全量分组回归全绿、ruff 0、覆盖率按既有口径记录（protocol_headers 92% ≥90% 保持）；S1b 段门禁五项自检**全绿**（协议头规范 v1.0 发布物齐备 / 非白名单带头 403 / 服务账号用例全绿 / verify-env 可用 / K07 模板+角色互译表发布物 [Review] 待人工批准登记），台账回写完成。
- 遗留：K07 模板 v1.0 / 角色互译表 v1.0 发布物维持 [Review] 状态，随本文档提交人工门禁回写 [Approved]；R3-1~R3-4 与 S2-S5 移交登记见 §7/§8。

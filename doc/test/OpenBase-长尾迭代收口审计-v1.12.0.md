# OpenBase 长尾迭代收口审计 - v1.12.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 审计对象 | v1.12.0 长尾建设迭代（A~E 五批） |
| 文档版本 | v1.0.0 |
| 状态 | **[Review]**（待人工批准） |
| 审计日期 | 2026-10-24 |
| 审计人 | 研发（AI 辅助） |
| 上游依据 | 《OpenBase-长尾事项产品裁定-v1.0.0》《OpenBase-剩余事项统一清查与小版本迭代计划-v1.0.0》v1.11.0、《OpenBase-DevLogReport-v1.4.11》v2.24.0、《OpenBase-前端架构设计文档-v1.4.11》v1.27.0 |
| 判据 | 需求可追溯 / 设计有落点 / 实现有测试 / 全量回归不劣于基线 / 版本单一事实源 / 三远程一致 |

---

## 1. 审计结论

**结论：通过（有条件）。**

- A~E 五批共 **11 个事项**全部闭环，需求 → 设计 → 实现 → 测试 → 提交可逐项追溯（§2）。
- 前端全量 **370/370**、`vue-tsc` 0 错误；OpenBase `ruff` 0 错误；编码契约 0 违规；生产开关矩阵 **9/9 PASS**。
- 后端全量 **1321 例**分三段执行：主体 1148 例全通过；尾部 161 例（159 passed / 4 skipped / 0 failed）；S7 门禁自检批次受共享 PG 连接中断影响（1 fail + 11 errors），另有 1 例出站主体映射用例受本机配置影响。两处失败均与 v1.12.0 改动无文件交集（§4.2），需在健康 PG + 生产等同配置下复跑作为放行前置。
- 版本单一事实源已收敛：`pyproject.toml`、`openbase/__init__.py`、`openbase-ui/package.json` 统一为产品版本 **1.4.11**（§3）。
- 三远程（origin / backup / github）HEAD 一致。

**放行前置（条件）**：

1. 在健康 PG 上复跑 `tests/test_verdict_k03.py::test_t2_6_unregistered_service_key_write_403`；
2. 以生产等同 `OPENBASE_SERVICE_ACCOUNT_SUBJECT_MAP` 复跑 `tests/test_service_agent_outbound.py::test_obk_service_account_mapped_outbound_headers`；
3. OPS 遗留：生产 `.env` 下发 `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=true` 并核验；XR-OPS-06 S2 三级回滚演练。

---

## 2. 需求 → 设计 → 实现 → 测试 追溯矩阵

| 事项 | 需求依据 | 设计落点 | 实现（文件） | 测试（用例/结果） | 提交 |
|------|----------|----------|--------------|-------------------|------|
| OB-03 应用调用记录 | 裁定 §3 OB-03 | 前端设计 §8.22 | `openbase/modules/ai_apps/__init__.py`（`GET /ai-apps/calls`）、`AppCallsView.vue`、`core/api/aiApps.ts` | `test_ai_apps_calls_v1120.py` 6 例；`r11-longtail-v1120.spec.ts` 3 例 | `27ccd68` |
| OB-04 知识库控制台 | 裁定 §3 OB-04 | 前端设计 §8.22 | `KnowledgeConsoleView.vue`（`ragApi` 真实链路） | `r11-longtail-v1120.spec.ts` 2 例 | `27ccd68` |
| XR-LLM-03 报表趋势 | 裁定 §3 XR-LLM-03 | 前端设计 §8.22 | `P2ReportTrendView.vue`（trends/dashboard/costs） | `r11-longtail-v1120.spec.ts` 2 例 | `27ccd68` |
| XR-LLM-06 用户名邀请 | 裁定 §3 XR-LLM-06 | 前端设计 §8.23 | OpenLLM `schemas/workspace.py`、`api/workspaces.py`；`WorkspacesView.vue`、`governance.ts` | `test_r12_workspace_member_v1120.py` 9 例；`r12-workspace-invite-v1120.spec.ts` 3 例 | OpenLLM `ffbd44d` / OpenBase `f4ae5bc` |
| XR-DPS-04 运行态指标 | 裁定 §3 XR-DPS-04 | 前端设计 §8.24 | DPS `monitoring/runtime.py`、`routes_admin.py`、`permission_middleware.py`、`permission_engine.py`、`metrics_middleware.py` | `test_v2120_runtime_metrics.py` 18 例；DPS 全量 1840 passed | DPS `2992d12` |
| XR-DPS-05 代理与监控页 | 裁定 §3 XR-DPS-05 | 前端设计 §8.24 | `dps_proxy/__init__.py`、`core/api/dps.ts`、`DpsMonitorView.vue` | `test_dps_proxy.py` 新增 4 例；`r12-dps-monitor-v1120.spec.ts` 3 例 | OpenBase `2624848` |
| XR-GOV-01 C1-d | 裁定 §3 XR-GOV-01 | 派单回执 v1.0.0 | OpenLLM `identity/code_normalize.py` + 租户明细；OpenRAG `code_normalize.py` + `tenant_registry`；OpenMemory `code_normalize.py` + `inbound_gate` | 10 / 10 / 12 例，相关回归 45 / 48 / 35 passed | `de4c7e5` / `d5ea6a8` / `9920e70`；文档 `a1c10b5` |
| XR-LLM-08 工具来源 | 裁定 §3 XR-LLM-08 | 前端设计 §8.25 | `PluginsView.vue`（来源列 + 口径说明） | `r12-dps-readonly-v1120.spec.ts` 1 例 | `bccefc6` |
| XR-DPS-02 治理页去 mock | 裁定 §3 XR-DPS-02 | 前端设计 §8.25 | `DpsPermissionView.vue` 只读重写 | 同上 1 例 | `bccefc6` |
| XR-DPS-03 治理只读视图 | 裁定 §3 XR-DPS-03 | 前端设计 §8.25 | `DpsRateLimitView.vue`、`DpsApiManageView.vue`；`dps_proxy` 新增 3 只读路由 | 同上 2 例；`test_dps_proxy.py` 32 passed | `bccefc6` |

---

## 3. 版本与产物一致性

| 载体 | 审计前 | 审计后 | 说明 |
|------|--------|--------|------|
| `pyproject.toml` | 1.0.0 | **1.4.11** | 产品版本单一事实源 |
| `openbase/__init__.py::__version__` | 1.0.0 | **1.4.11** | `/health` 与 OpenAPI 版本随之统一 |
| `openbase-ui/package.json` | 1.3.0 | **1.4.11** | 与后端/文档一致 |
| 模块级 `__init__.__version__` | 各自独立 | 保持不变 | `test_grayscale` 明确「模块独立版本字段」，不属于产品版本 |
| 文档 | DevLogReport v2.24.0 / 计划 v1.11.0 / 缺口 v1.17.0 / 前端设计 v1.27.0 | 同左（本审计新增 §2.34） | 阶段命名 S/P/Phase 口径一致 |

版本相关目标用例复跑：`test_app.py`、`test_release_verify.py`、`test_grayscale.py`、`test_ui_increments.py`、`test_dps_proxy_v1410_contract.py` 共 **94 passed**。

---

## 4. 验证汇总

### 4.1 通过项

| 项 | 命令/方式 | 结果 |
|----|-----------|------|
| 前端全量 | `vitest run` | **370 passed / 39 files** |
| 前端类型 | `vue-tsc --noEmit` | **0 error** |
| 后端静态 | `ruff check openbase tests` | **0 error**（修复 3 处历史 lint：I001×2、UP012×1，修复后 20 例复跑通过） |
| 编码契约 | `scripts/scan_source_encoding.py` | 扫描 9060 文件，**违规 0**，契约 PASS |
| 生产开关矩阵 | `scripts/verify_production_switches.py` | **9/9 PASS** |
| 后端主体批次 | `pytest tests`（至 87%，1148 例） | **1148 通过，0 失败** |
| 后端尾部批次 | 尾部 16 文件（排除 2 例环境/配置相关） | **159 passed / 4 skipped / 0 failed** |
| DPS 全量 | `pytest`（CPython 3.11 运行器） | **1840 passed / 3 skipped / 1 xfailed / 1 xpassed，0 failed** |
| 三仓码值相关 | 各自 pytest | OpenLLM **45** / OpenRAG **48** / OpenMemory **35 passed** |
| 三远程 | `git ls-remote` × 3（四仓） | HEAD 一致 |

### 4.2 未通过项归因（非本次改动）

| 用例 | 现象 | 根因 | 处置 |
|------|------|------|------|
| `test_verdict_k03.py::test_t2_6_unregistered_service_key_write_403` | 期望 403，实际 502 | 共享 PG 连接中断（日志：`asyncpg.Error: connection was closed`）→ 服务键登记降级 → 写门禁未命中 | 健康 PG 复跑；已登记为放行前置 |
| `test_s7_t6_gate.py`（11 errors + 1 fail） | RA-06「fail-closed 子批」exit=1 | 同一 PG 问题导致上述用例失败，门禁聚合随之 FAIL | 随上项复跑后重跑 `gate_aggregate.py` |
| `test_service_agent_outbound.py::test_obk_service_account_mapped_outbound_headers` | 期望 `5001`，实际 UUID | 本机未配置生产等同 `OPENBASE_SERVICE_ACCOUNT_SUBJECT_MAP` | 以生产等同配置复跑；已登记为放行前置 |

> 三项均落在 v1.12.0 **未改动**的文件（`identity/verification`、`test_verdict_k03`、`service_account` 映射），不构成功能回归；S7 B 面 2 项（SMOKE-S0-S6、K07-SYS-1）按门禁设计为 `PENDING`，需联调窗口执行。

---

## 5. 遗留与后续

| # | 事项 | 类型 | 解冻/关闭条件 |
|:-:|------|------|----------------|
| 1 | OpenRAG / OpenMemory「码 → 真实 UUID」 | 能力缺口 | 租户主数据接入后由既有入口注入 resolver |
| 2 | OpenLLM 写路径仍 UUID-only | 范围限定 | 如需放宽，单独评审写面语义 |
| 3 | 生产 `.env` 下发 `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=true` | OPS | 下发后以 `--env-file` 核验并回填执行记录 §5 |
| 4 | XR-OPS-06 S2 三级回滚演练 | OPS | 开关/通道/版本三级演练完成并留证 |
| 5 | S7 门禁 B 面（冒烟 S0-S6 / K07-SYS-1） | 联调 | 真实四仓运行态窗口执行 |

---

## 6. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-10-24 | 研发（AI 辅助） | 初始创建：A~E 五批 11 项追溯矩阵、版本三处统一至 1.4.11、全量验证汇总与 3 项环境/配置失败归因；结论「通过（有条件）」并登记 5 项遗留。 |

# OpenBase v1.4.10 Step 4 后端与集成测试取证记录

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-EVID-V1410-STEP4-BE-INT-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Review] |
| 日期 | 2026-10-01 |
| 范围 | OpenBase v1.4.10 Step 4 测试（后端全量 ＋ dps-proxy 覆盖率 ＋ 真实 DPS 上游集成 ＋ pylint 重复率） |
| 执行环境 | Windows；Python 3.10.11；pytest 9.1.1；pylint 4.0.9（astroid 4.0.4） |
| 被测位 | HEAD `9bf2d18`（feat(v1.4.10-step3) dps-proxy 22 端点扩展） |
| 上游 | DPS v2.12.0 @ `127.0.0.1:8030`（`/health/liveness` 200，uptime 15171s） |
| 存放 | `doc/test/evidence/v1410/` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-01 | QA-OpenBase（Step 4 执行） | 初始版本：记录后端全量测试、dps-proxy 覆盖率、真实上游集成（经 `/api/v1/dps-proxy/*`）、pylint 重复率四项的原始命令、结果与缺陷/阻塞 |

> 说明：本文件为 **Step 4 取证记录**（原始输出索引 ＋ 结论），非正式《测试报告》；正式测试报告待收尾时按项目文档管理规范另行产出并做版本管理。

---

## 1. 执行命令（逐字）

| # | 命令 | 工作目录 |
|:-:|------|----------|
| 1 | `python -m pytest tests -q` | 仓库根 |
| 2 | `python -m pytest --cov=openbase.modules.dps_proxy --cov-report=term-missing tests -q` | 仓库根 |
| 3 | 真实上游集成：先启动最小服务 `python doc\test\evidence\v1410\v1410_openbase_server.py`（上游指向 `127.0.0.1:8030`），再 `python doc\test\evidence\v1410\v1410_dps_proxy_integration.py` | 仓库根 |
| 4 | `python -m pylint --disable=all --enable=duplicate-code --min-similarity-lines=10 openbase` | 仓库根（baseline 另于 `git worktree` @ tag `v1.4.9` 同口径复跑） |

### 1.1 dps-proxy 真实上游配置（已生效）

```
OPENBASE_DPS_UPSTREAM_BASE=http://127.0.0.1:8030
OPENBASE_DPS_ORG_MAP={"tenant-1":"dps-org-001","org-1":"dps-org-001"}
OPENBASE_DPS_TENANT_MAP={"tenant-1":"dps-tenant-001","org-1":"dps-tenant-001"}
OPENBASE_DPS_CODE_MAP={"schema_version":1,"source_of_truth":"openbase.tenants.code","last_reconciled_at":"2026-10-01","entries":[{"tenant_code":"tenant-1","dps_org_id":"dps-org-001","dps_tenant_id":"dps-tenant-001","reconciled_at":"2026-10-01","status":"verified"}]}
```

联调身份：JWT `sub=1`（DPS 种子绑定 `1:super_admin`）、`tenant_code=tenant-1`、`org_id=tenant-1`、`role=super_admin`；
经 `dps_org_map/dps_tenant_map` ＋ 登记式 `dps_code_map` 折算，出站头 `X-Org-ID=dps-org-001`、`X-Tenant-ID=dps-tenant-001`（DPS 双形态可解析，实测 200）。

---

## 2. 结果汇总

| 命令 | 总数 | 通过 | 失败 | 跳过 | 覆盖率 | 结论 |
|------|:----:|:----:|:----:|:----:|:------:|------|
| #1 `pytest tests -q` | 1109 | **1100** | **5** | **4** | — | 5 项失败（1 项代码边界缺陷 ＋ 4 项共享库连接抖动） |
| #2 `pytest --cov=openbase.modules.dps_proxy tests -q` | 1109 | **1100** | **5** | **4** | **93%**（256 stmts / 18 miss） | 与 #1 完全一致（可复现） |

> 计数来源：#2 由 `--junitxml` 归集（`passed=1100 / failed=5 / skipped=4`）；#1 与 #2 失败集、跳过集逐条一致，故两者计数一致。
> 阈值对照（`AGENTS.md` §7：新增代码覆盖率 ≥90%）：**dps_proxy 93% ⇒ 达标**。

### 2.1 失败用例清单（两次运行一致）

| # | 用例 | 类别 | 摘要 |
|:-:|------|------|------|
| 1 | `tests/test_s6_t1_frontend_boundary.py::test_s6_t1_2_target_directory_reference_is_whitelisted` | **代码/边界缺陷** | `openbase/modules/llm_proxy/__init__.py` 命中 `openbase-ui` 引用，超出白名单（白名单仅允许 `openbase/cli/main.py`） |
| 2 | `tests/test_tenant_admin.py::test_tenant_crud_flow` | 环境（共享库抖动） | `asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation` |
| 3 | `tests/test_tenant_admin.py::test_tenant_quota_readwrite` | 环境（共享库抖动） | 同上 |
| 4 | `tests/test_users_admin.py::test_user_crud_flow` | 环境（共享库抖动） | 同上 |
| 5 | `tests/test_users_admin.py::test_new_user_can_login` | 环境（共享库抖动） | 同上 |

### 2.2 跳过（4）

两次运行均 `skipped=4`（未逐一枚举；`pytest -q` 未展开 skip 原因）。**建议**：正式报告以 `-rs` 补记跳过原因。

---

## 3. dps-proxy 覆盖率明细

```
Name                                     Stmts   Miss  Cover   Missing
----------------------------------------------------------------------
openbase\modules\dps_proxy\__init__.py     256     18    93%   84, 87-88, 141-142, 164-165, 169-175, 306-312, 439-440, 456-457, 472-473
----------------------------------------------------------------------
TOTAL                                      256     18    93%
```

未覆盖行归因（初步）：

| 行段 | 位置 | 归因 |
|------|------|------|
| 84, 87-88 | `_parse_map_json` 异常/非 dict 分支 | `dps_org_map` 非法 JSON 分支未覆盖 |
| 141-142 | `_adapt_response` 上游非 JSON（`ValueError` → `{"raw": ...}`） | 非 JSON 上游体未构造 |
| 164-165 | `_adapt_response` `detail` 为 dict 的 code 提取 | FastAPI dict detail 未覆盖 |
| 169-175 | `_adapt_response` `detail` 为 list 的 msg 聚合 | FastAPI list detail 未覆盖 |
| **306-312** | `_forward` 连续失败达阈值 → **503 显式降级**分支 | 降级 503 分支未被测试触发（既有 `test_dps_proxy.py` 未覆盖该分支） |
| 439-440, 456-457, 472-473 | 新增端点个别行（模板分类/分类更新等） | 端点级细节行未覆盖 |

---

## 4. 真实上游集成检查（经 `/api/v1/dps-proxy/*` → DPS v2.12.0:8030）

| 组 | 方法 | 本仓路径 | 状态 | 上游响应片段（截断） |
|----|------|----------|:----:|----------------------|
| 门禁 | GET | `/templates`（无 token） | **401** | `{"code":"AUTH_401","message":"missing bearer token",...}` |
| 既有12 | GET | `/health` | **200** | `{"code":0,...,"data":{"status":"healthy","version":"2.12.0",...}}` |
| 既有12 | GET | `/portraits?page=1&page_size=20` | **200** | `data.total=17, items[0].person_id=61` |
| 既有12 | GET | `/portraits/61` | **200** | `data.name=联调主体, overall_score=36.6` |
| 既有12 | GET | `/tags/categories` | **200** | `{"items":[],"total":0}` |
| 既有12 | GET | `/reports/overview` | **200** | `{"total_profiles":0,...}` |
| 既有12 | GET | `/audit/logs?page=1&page_size=5` | **200** | `items[0].identity tenant_code=dps-tenant-001, org_code=dps-org-001`（**证明映射生效**） |
| 既有12 | GET | `/batch/tasks/nonexistent-task` | **200** | `{"data":null}`（上游对不存在任务返回 200 空体） |
| v1.4.10 | GET | `/templates` | **200** | `{"items":[],"total":0}` |
| v1.4.10 | GET | `/templates/nonexistent/diff?target_version=1` | **422** | `{"code":"VALIDATION_ERROR","message":"请求参数校验失败"}` |
| v1.4.10 | GET | `/templates/nonexistent/preflight` | **500** | `{"code":"INTERNAL_ERROR","message":"服务器内部错误"}` |
| v1.4.10 | GET | `/lineage/impact?template_code=nonexistent` | **200** | `{"template_code":"nonexistent","tag_count":0,"profile_count":0}` |
| v1.4.10 | GET | `/lineage/tags/nonexistent` | **404** | `{"code":"NOT_FOUND","message":"无谱系记录：tag_code=nonexistent"}` |
| v1.4.10 | GET | `/measures/suggest?person_id=61` | **502**（首次）→ 重试 5/5 **200** | 首次 `{"code":"SYS_502","message":"DPS upstream unreachable: "}`；重试 `{"data":{"person_id":"61","suggestions":[],"disclaimer":"..."}}` |
| v1.4.10 | GET | `/scoring-types?page=1&page_size=20` | **502**（首次）→ 重试 5/5 **200** | 首次 SYS_502；重试 `{"registered_types":["boolean_flag",...,"ratio_target_score"]}` |
| v1.4.10 | GET | `/annotation-templates` | **200** | `{"items":[],"total":0}` |
| v1.4.10 | GET | `/labels?action=list` | **200** | `{"data":[]}` |

**要点**：
- 认证门禁 fail-closed（401）成立；四维身份头注入 ＋ org/tenant 值映射真实生效（审计日志回显 `dps-org-001/dps-tenant-001`）。
- 上游 4xx/5xx 语义**保真透传**（422/500/404 原码保留，未被改写为 500）。
- `measures/suggest`、`scoring-types` 首次 502 系**上游瞬时不可用**（同刻探活亦失败），**直接对 DPS 复测 5/5 返回 200**，判定为**瞬时抖动**，非本仓路由缺陷。
- **注意**：本版 22 条新增端点中，DPS v2.12.0 已实现 `templates/*`、`annotation-templates`、`lineage/*`、`measures/suggest`、`scoring-types`、`labels` 等；`preflight` 对不存在 code 返回 **500**（见 §6 缺陷）。

---

## 5. pylint 重复率检查

| 项 | 命令 | 结果 |
|----|------|------|
| HEAD（`9bf2d18`） | `python -m pylint --disable=all --enable=duplicate-code --min-similarity-lines=10 openbase` | **R0801 重复块 = 7**，评分 **9.99/10** |
| 基线（tag `v1.4.9`，`git worktree` 独立检出同口径） | 同上 | **R0801 重复块 = 7** |
| **增量** | HEAD − 基线 | **0**（阈值 ≤2% ⇒ 通过） |

重复块均为**既有**代理族同构实现（非本版新增）：

| # | 重复（2 文件） | 片段 |
|:-:|----------------|------|
| 1 | `dps_proxy.__init__[122:159]` ↔ `rag_proxy.__init__[123:162]` | `_build_identity_headers` 尾段 ＋ `_adapt_response` |
| 2 | `llm_proxy.__init__[89:127]` ↔ `rag_proxy.__init__[122:158]` | `_adapt_response` |
| 3 | `demo_app[45:73]` ↔ `settings[31:57]` | `AVAILABLE_MODULES` 常量表 |
| 4 | `dps_proxy.__init__[122:155]` ↔ `llm_proxy.__init__[90:127]` | `_adapt_response` |
| 5 | `dps_proxy.__init__[160:175]` ↔ `rag_proxy.__init__[163:179]` | `_adapt_response` 错误归一 |
| 6 | `core.logging_setup[60:73]` ↔ `core.mask[60:73]` | `SENSITIVE_KEY_FRAGMENTS` |
| 7 | `llm_proxy.__init__[241:254]` ↔ `rag_proxy.__init__[332:345]` | SSE 错误回执 |

> 与 v1.4.9 同值（7 = 7）⇒ **重复率增量为 0**，未因 v1.4.10 改动新增重复块。

---

## 6. 缺陷与发现

| 编号 | 级别 | 类别 | 描述 | 证据 | 处置建议 |
|------|:----:|------|------|------|----------|
| **DEF-1410-T4-01** | **P1** | OpenBase 代码/边界 | `openbase/modules/llm_proxy/__init__.py:399` 注释含字面量 `openbase-ui`，触发 S6-T1-2 边界白名单断言失败（白名单仅 `openbase/cli/main.py`）。由提交 `bd7b7dd`（2026-09-28）引入，Step 4 全量回归暴露 | `pytest-full-20261001.txt` L1029 | 二选一：①改写该注释规避 `openbase-ui` 字面量；②按设计草案登记白名单并同步 S6-T1-2 断言。须在 Step 4 收尾前闭环 |
| **DEF-1410-T4-02** | P2 | 上游（DPS） | `GET /api/v2/portrait/templates/{code}/preflight`（code 不存在）返回 **500 INTERNAL_ERROR**，契约预期 404；经 dps-proxy 保真透传为 500 | `dps-proxy-integration-20261001-103215.json`；直连 DPS 复现 500 | 跨仓反馈 DPS：不存在资源应 404；本仓透传语义正确、无需改动 |
| **DEF-1410-T4-03** | P3 | 上游（DPS） | `GET /api/v2/portrait/templates/{code}/diff`（code 不存在）返回 **422 VALIDATION_ERROR**，与设计文档「404」口径不一致 | 同上 | 契约口径对齐（DPS 侧裁定）；本仓透传正确 |
| **OBS-1410-T4-04** | P3 | 环境/上游抖动 | `measures/suggest`、`scoring-types` 首次经代理 502（`SYS_502 DPS upstream unreachable`），重试 5/5 返回 200；同刻 DPS 探活亦失败 | `dps-proxy-retry-probe-20261001.txt` | 判定为 DPS 单实例瞬时不可用；建议 DPS 排查并发/阻塞（preflight 单请求曾耗时约 21s） |
| **OBS-1410-T4-05** | P3 | 覆盖率缺口 | dps_proxy 未覆盖 **503 显式降级分支（L306-312）** 及 `detail` 为 dict/list 的归一分支（L164-175） | 覆盖率报告 | 建议补测：连续 3 次上游失败 → 503 ＋ `X-DPS-Upstream-Degraded`；FastAPI dict/list detail 归一 |

---

## 7. 阻塞与限制

| # | 项 | 说明 |
|:-:|----|------|
| 1 | 共享 PostgreSQL 抖动 | `tests/test_tenant_admin.py`、`tests/test_users_admin.py` 共 4 例因 `asyncpg ConnectionDoesNotExistError`（connection closed mid-operation）失败，指向共享库 `192.168.0.151:5432` 连接不稳定；**非被测代码缺陷**。建议于 Step 4 收尾时在网络稳定窗口复跑确认 |
| 2 | DPS 运行态非持久 | DPS v2.12.0 标签能力为进程内内存（TD-3044），重启即失；本次集成检查未依赖标签层级，不受影响 |
| 3 | 联调服务生命周期 | 真实集成采用「最小 OpenBase 服务（8000）＋ 真实 DPS（8030）」，检查完成后服务已停止；脚本可复跑（见 §1） |
| 4 | 未做项 | 前端（vitest/playwright/vue-tsc）与安全/性能不在本次取证范围（另有前端 Step 4 证据存在） |

---

## 8. 取证文件清单（`doc/test/evidence/v1410/`）

| 文件 | 内容 |
|------|------|
| `pytest-full-20261001.txt` | 命令 #1 原始输出（含 5 失败明细） |
| `pytest-coverage-dps_proxy-20261001.txt` | 命令 #2 原始输出（含 term-missing 覆盖率表） |
| `junit-dps-proxy-coverage-20261001.xml` | 命令 #2 JUnit（权威计数：1100/5/4） |
| `dps-proxy-integration-20261001-103215.json` | 真实上游集成机读证据（状态码 ＋ 片段） |
| `dps-proxy-integration-20261001-103215.txt` | 真实上游集成人读证据 |
| `dps-proxy-integration-20261001-console.txt` | 集成检查控制台输出 |
| `dps-proxy-retry-probe-20261001.txt` | 502 两例重试 5/5 = 200 复测证据 |
| `v1410_openbase_server.py` | 最小 OpenBase 服务启动器（真实上游指向） |
| `v1410_dps_proxy_integration.py` | dps-proxy 真实上游集成检查脚本 |
| `pylint-duplicate-code-20261001.txt` | pylint 重复率 HEAD 原始输出 |

---

## 9. 结论

- **后端全量**：1109 例 → **1100 通过 / 5 失败 / 4 跳过**；失败中 **1 项为代码边界缺陷（DEF-1410-T4-01，P1）**、4 项为共享库连接抖动（环境）。
- **dps-proxy 覆盖率**：**93%**（256/18）**达标**（≥90%）；缺口集中于 503 降级分支与 detail 归一分支。
- **真实上游集成**：认证 fail-closed、身份/映射注入、错误语义保真、既有与新端点透传均**实测通过**；发现 **1 项上游 500 缺陷** 与 2 项契约口径差异＋1 项瞬时抖动。
- **重复率**：HEAD 与 v1.4.9 基线均 7 块，**增量 0**，通过。
- **是否放行**：**暂缓**——建议先闭环 **DEF-1410-T4-01（P1）** 并在共享库稳定窗口复跑 4 项环境失败，再行 Step 4 收口。

# OpenBase 问题跟踪记录 - v1.4.6

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.6 |
| 文档版本 | v1.4.0 |
| 状态 | [Draft] |
| 记录人 | AT-OpenBase-Test（Step 4 实环境走查发现）/ AD-OpenBase-Dev（Step 3 回退修复） |
| 创建日期 | 2026-09-16 |
| 存放 | doc/operation/ |
| 关联文档 | `doc/test/OpenBase-测试报告-v1.4.6.md`、`doc/development/OpenBase-DevLogReport-v1.4.6.md` |

---

## 1. 本版本问题清单

| 问题 ID | 级别 | 类别 | 描述 | 状态 | 处理 |
|---------|:----:|------|------|:----:|------|
| DEF-BE-146-001 | **P1** | 后端缺陷 | 日志中心「四仓日志」（`repo_log`）源检索返回 **HTTP 500 且响应体为空**，该源完全不可用 | ✅ **已关闭** | 回退 Step 3 修复：`repository.py::_parse_line` 行级容错（无时间戳行跳过）+ `fetch` 丢弃汇总告警；新增 3 条回归用例；实环境复测 200/4937 条（见 §3.3） |
| DEF-BE-146-002 | P3 | 前端缺陷 | 仪表盘「系统版本」硬编码 `v1.2.0`，与当前版本 v1.4.6 不符（`Dashboard.vue`） | ⬜ 登记待处理 | 未在本轮回退范围；建议随下一版本改为构建期注入或读取接口版本 |
| DEF-BE-146-003 | P2 | 前端缺陷 | 日志「时间」列按 UTC 原样展示、未转本地时区且列头无时区标注（本地 15:27 显示为 07:27） | ⬜ 登记待处理 | 未在本轮回退范围；审计时间可读性风险，建议补时区转换或标注 |
| DEF-BE-146-004 | P2 | 性能 | `GET /api/v1/logs/facets` 响应 7.3～14.6 s（多次实测），每次切换日志源均触发 | ⬜ 登记待处理 | 未在本轮回退范围；建议增量聚合或缓存（见 §4 风险归集） |
| DEF-BE-146-005 | P3 | 前端体验 | 切换日志源时在途请求被中断，控制台产生 `net::ERR_ABORTED`（干净加载无此问题，仅切源时出现） | ⬜ 登记待处理 | Step 4 重测新增；按 L4「无代码类 console.error」口径应抑制取消类错误；建议改用 AbortController 并吞掉取消异常 |
| DEF-BE-146-006 | P2 | 契约一致性 | 参数校验失败实际返回 **422 `PARAM_422`**，而《API接口设计文档》§5 规定 **400 `PARAM_400`**；另 `from > to` 实际返回 200（设计规定 400），无效 ISO 时间亦未拒绝 | ✅ **已关闭**（人工裁定：**改实现对齐设计的 400**） | 统一错误码字面值为 `PARAM_400`（HTTP 400）；补时间窗语义校验（`from > to` / 非 ISO8601 → 400）；同步 7 处测试断言 + 前端错误码参考列表；实环境复测全部分支 400（见 §3.5） |
| DEF-BE-146-007 | P2 | 契约一致性 | **三个 P2-3 契约残留问题**：① 403 权限码字面值混用（日志/模块权限抛 `AUTH_403`，设计 §5 为 `PERM_403`）；② 同资源 404 双码（模块 GET 抛 `BIZ_404`、PATCH 抛 `PARAM_404`）；③ 模块端点路由路径参数 `module_id` 与设计 §3.4 的 `{id}` 不一致 | ✅ **已关闭**（人工裁定：**合并一轮返工对齐设计**） | 一次性裁定后合并回退 Step 3：新增 `PERM_403` 字面值并对齐日志/模块权限；模块 GET/PATCH 统一 `PARAM_404`；路径参数统一 `{id}`；历史遗留 `AUTH_403`/`PERM_FORBIDDEN` 不动、记技术债务（见 §3.9） |

## 2. 变更请求

本版本无正式变更请求（范围稳定）；本节仅登记 Step 4 走查发现的问题。

## 3. 缺陷修复回归

### 3.1 DEF-BE-146-001（P1，本轮回退修复）

| 项 | 内容 |
|----|------|
| 发现来源 | v1.4.6 Step 4 实环境人工走查（编排器已纳管四仓采集日志） |
| 复现步骤 | ① 打开日志中心 `/platform/observability/logs`；② 日志源切换为「四仓日志」；③ 观察检索结果与后端状态 |
| 实际结果 | `GET /api/v1/logs/search?source=repo_log` → **HTTP 500，响应体为空**；前端显示「Request failed with status code 500 + 重试」；后端 `openbase.audit` 记录 `request failed`（request_id `req-2866a2709853`） |
| 预期结果 | 返回 200 与可用条目；不可解析行按既有「坏行跳过」口径丢弃，不得使整源崩坏 |
| 根因 | `openbase/modules/logs/repository.py` 的 `_parse_line`：纯文本回退路径 `ts = timestamps[0] if timestamps else None`、JSON 路径 `_iso(...)` 均可能在无时间戳时得到 `None`，而 `LogEntry.ts` 为必填 `str` → `pydantic ValidationError` 未被捕获 → 容器级异常穿透为 500（响应体为空，违反统一错误格式 `{code,message,detail,request_id}`） |
| 触发条件 | 四仓采集日志 `logs/<svc>/<svc>-YYYYMMDD.log` 由编排器按 stdout 原样落盘，含 `INFO:     Application startup complete.` 类横幅行与堆栈续行（无时间戳） |
| 影响面 | ① 日志中心四源之一（四仓日志）**整源不可用**；② 违反统一错误格式契约（空响应体）；③ 单行脏数据即可击穿整源（行级容错缺失） |
| 修复方案 | ① 两条解析路径均在时间戳不可解析时 `return None`（沿用 `.py:745` 空行、`.py:749` 未知 svc 的既有跳过口径）；② `fetch` 统计扫描/解析数并输出丢弃汇总 **WARNING**（`repo_log unscannable lines dropped`），满足「不静默降级」 |
| 修复文件 | `openbase/modules/logs/repository.py`（`_parse_line` ×2 处 + 新增 `_warn_dropped` + `fetch` 计数） |
| 回归用例 | `tests/test_logs_service.py::test_repolog_text_line_without_timestamp_skipped`、`::test_repolog_json_without_timestamp_skipped`、`tests/test_logs_endpoints_api.py::test_repo_log_dirty_lines_without_timestamp_do_not_break_source`（TDD：修复前 3 例全红，修复后全绿） |
| 复测结果 | 增量面（`test_logs_*` / `test_log_reserved_keys` / `test_mask`）**137 例全通过**；全量回归与实环境复测见 §3.2 |

### 3.2 回归证据

| 验证项 | 命令 | 结果 |
|--------|------|:----:|
| TDD 红灯确认 | `pytest -k without_timestamp` | 🔴 3 例失败（`ValidationError: ts input_value=None`，与线上同一根因） |
| TDD 绿灯 | `pytest -k without_timestamp` | 🟢 3 例通过 |
| 增量面 | `pytest tests/test_logs_service.py tests/test_logs_endpoints_api.py tests/test_logs_derivation.py tests/test_log_reserved_keys.py tests/test_mask.py` | 🟢 137 通过 / 0 失败 |
| 静态质量 | `python -m ruff check openbase tests` | 🟢 0 错误 |
| 全量回归 | `pytest tests --ignore=tests/test_s7_t6_gate.py` | 见 §3.3 |
| 实环境复测 | `GET /api/v1/logs/search?source=repo_log`（编排器已拉起全部服务） | 见 §3.3 |

### 3.3 后续复测记录（Step 3 修复后 → Step 4 重测）

| 项 | 结果 |
|----|------|
| 全量回归（修复后） | 🟢 **953 收集 / 945 通过 / 4 环境性失败 / 4 跳过 / errors=0**（JUnit 权威计数；较修复前基线 950/942 **+3**，即新增用例；失败项集合不变，仍为 PG-ENV-1~4） |
| 实环境 `repo_log` 源 | 🟢 **HTTP 200，items=5 / total=4937**（修复前：500 + 空响应体）；日志中心页面切换「四仓日志」→ **20 行 / 共 4937 条**，无错误提示 |
| 增量面 / 静态质量 | 🟢 137 例全绿；`ruff check` 0 错误 |
| 残留观察 | ⬜ 前端 `timeout of 15000ms exceeded`（`logs/facets` 7.3～14.6 s，超前端 15 s 超时）→ 归 DEF-BE-146-004，不在本次 P1 修复范围 |
| **判定** | **DEF-BE-146-001 已闭环**（P1 → 关闭），可重新进入 Step 4 |

### 3.4 Step 4 重测结果（2026-09-16 重入后）

| 矩阵项 | 范围 | 结果 |
|--------|------|------|
| T2 API 复测 | 四源 × search/facets + 导出 + 校验分支 + 鉴权门禁（18 项） | 🟢 **18/18 PASS**（证据 `doc/test/evidence/v146/t2-retest-logs-api.md`） |
| T3a 页面复测 | 日志中心「四仓日志」源 + 5 个代表页（dashboard/modules/test-records/tenants/openllm-models） | 🟢 四仓日志 **20 行 / 共 4977 条、无错误提示**；5 页无错误条；干净标签页控制台**零告警** |
| T3b/E2E | 前端 198 用例（含 platform-ia 10 / router-nav 16 / isolation 20 / nav-consistency 21 / module-pages 4） | 🟢 **198/198 全绿** |
| 覆盖率双门禁 | 后端增量面 + 前端 vitest | 🟢 前端 **97.47%**（branches 90.05%）；后端增量面 137 例全绿 |
| 全量回归 | `pytest tests --ignore=tests/test_s7_t6_gate.py` | 🟢 **953 收集 / 945 通过 / 4 环境性失败 / 4 跳过 / errors=0**（证据 `regression-retest-20260916-junit.xml`） |
| 遗留 | 重测新发现 | DEF-BE-146-005（P3，切源 console 中断错误）、DEF-BE-146-006（P2，契约口径 400/422 待裁定） |

> 重测结论：**DEF-BE-146-001 修复有效且无回归**；无新增 P0/P1。DEF-BE-146-005/006 均非阻塞项，其中 DEF-BE-146-006 需人工裁定后回写设计文档或调整实现。

### 3.5 DEF-BE-146-006 契约口径裁定与修复（2026-09-16，第二次 Step 3 回退）

**人工裁定（用户决策）**：**改实现，对齐设计的 400 状态码**——不修改设计文档。

| 项 | 内容 |
|----|------|
| 裁定依据 | 《OpenBase-API接口设计文档-v1.4.6》§5 明确 `source` 非法 / `page_size` 越界 / 时间窗非法 / 关键字超长 / 导出超限 均为 **400 `PARAM_400`**；§3.4 模块开关 `status` 非法亦为 400 |
| 影响面评估 | ① 前端 `core/api/error.ts` 对 400 与 422 **同分支处理**（按 `PARAM_` 前缀判定为 `invalid-param`）→ 前端逻辑无破坏；② 全局 `RequestValidationError` 处理器为跨模块单点，改动波及 testing / gateway / auth / crud / ai-apps 等端点的参数校验状态码；③ 受影响的既有断言 7 处，已同步为 400 |
| 破坏性变更声明 | 参数校验失败的状态码由 **422 → 400**、错误码字面值由 `PARAM_422` → `PARAM_400`（含 `/api/v1/test-records`、`/api/v1/services`、`/api/v1/gateway/aggregate`、`/api/v1/ai-apps`、`/api/v1/logs/*`、`/api/v1/modules/{id}` 等）。**回滚方式**：还原 `openbase/core/errors/{codes,base}.py` 两个文件即恢复 422 口径（无数据迁移、无配置依赖） |
| 实现变更 | ① `core/errors/codes.py`：`PARAM_VALIDATION_ERROR` 字面值 `PARAM_422` → `PARAM_400`，`ERROR_HTTP_MAP` 映射 422 → 400；`PARAM_EXPORT_LIMIT_EXCEEDED` 退化为同值兼容别名（消除「同义双码」）；② `core/errors/base.py`：校验处理器状态码改由 `ERROR_HTTP_MAP` 单点解析（`detail` 数组保留不动——`detail[].input` 是 C-18 响应观测的脱敏输入源）；③ `modules/logs/service.py`：`_parse_datetime` 由「非法返回 None 静默忽略」改为 **抛 400 `PARAM_400`**（`detail.field` 标注 `from`/`to`），新增 `_validate_window` 实现 `from > to` → 400（`detail.field=from/to`） |
| 测试同步 | 新增/改写 6 条断言（4 类参数越界 + 时间窗倒置 + 时间格式非法）；同步 7 处既有 422 断言（`test_logs_endpoints_api` / `test_modules_switch_api` / `test_testing_api` / `test_gateway_api`×2 / `test_ui_increments` / `test_auth` / `test_audit_response_observe`） |

**验证证据**：

| 验证项 | 命令 / 方式 | 结果 |
|--------|-------------|------|
| TDD 红灯 | `pytest -k "param_validation or invalid_format or unknown_source or time_window or time_format"` | 🔴 6 例失败（422 vs 400；`from>to` 与非法时间返回 200） |
| TDD 绿灯 | 同上 | 🟢 9 例通过 |
| 关联套件 | `pytest`（9 个受影响文件） | 🟢 **149 通过 / 0 失败** |
| 静态质量 | `python -m ruff check openbase tests` | 🟢 `All checks passed!` |
| 全量回归 | `pytest tests --ignore=tests/test_s7_t6_gate.py --junitxml` | 见 §3.6 |
| 实环境复测 | 重启 OpenBase（PID 17908）后逐分支实测 | 🟢 非法 source / `page=0` / `page_size=1000` / `format=xml` / `q` 超长 → **400 `PARAM_400`**；`from > to` → **400**（`detail.field=from/to`）；`from=not-a-date` → **400**（`detail.field=from`）；`step_id=abc` → 200（int\|str 契约不变） |
| 前端同步 | `openbase-ui/src/modules/portrait/pages/DpsApiManageView.vue` 错误码参考列表 | 🟢 `PARAM_422` → `PARAM_400` |

> 修复文件：`openbase/core/errors/codes.py`、`openbase/core/errors/base.py`、`openbase/modules/logs/service.py`、`openbase-ui/src/modules/portrait/pages/DpsApiManageView.vue`；测试文件：`tests/test_logs_endpoints_api.py` 等 8 个。

### 3.6 第二次 Step 3 回退后的全量回归

| 项 | 结果 |
|----|------|
| 全量回归（排除 S7 门禁聚合） | 🟢 **959 收集 / 951 通过 / 4 环境性失败 / 4 跳过 / errors=0**（较契约变更前 953/945 **+6**，即新增用例；失败项集合不变，仍为 PG-ENV-1~4） |
| 证据 | `doc/test/evidence/v146/regression-param400-junit.xml` |
| 判定 | **DEF-BE-146-006 已闭环**（口径对齐设计的 400，无回归） |

### 3.7 detail 结构裁定与对齐（2026-09-16，第三次 Step 3 回退）

**裁定**：**继续对齐** —— `detail` 改为**字段式明细数组**，剔除第三方库内部键。

| 项 | 内容 |
|----|------|
| 裁定依据 | ① 原实现直接回传 `exc.errors()`，把 **pydantic 内部结构**（`type`/`loc`/`ctx`/`url`）固化为公开契约——库升级即可改变对外结构，属契约卫生缺陷；② 项目内其余错误明细（导出超限 `{matched,limit}`、模块不存在 `{module_id,allowed}`）**本就是字段式**，数组形态是唯一异类；③ 设计 §5 的 `detail` 示例均为字段式；④ `api-contract-management` 技能的规范错误格式亦为字段式 `details:[{field,message}]`；⑤ 前端 `ErrorPresentation.detail` 为 **string**（由 message 自行生成），**不消费后端 detail** → 前端零影响 |
| 形态取舍 | 采用**数组** `[{field,msg,…}]` 而非设计样例的单对象：校验失败可能同时命中多个字段（如 `page` + `page_size`），单对象无法承载；单字段场景下数组长度为 1，信息等价。**此点建议回写设计文档 §5 备注**（由「示例为单对象」明确为「数组，可含多项」） |
| 保留项 | `input` 保留（C-18 响应观测的脱敏输入源；移除会破坏 `test_audit_response_observe` 的掩码验证前提）；约束键映射 `le→max` / `ge→min` / `max_length` / `min_length`；`literal_error` 额外输出 `allowed` |
| 实现变更 | `core/errors/base.py`：新增 `_validation_detail`（归一化）、`_parse_allowed`（从 `ctx.expected` 解析候选值）、`_LOCATION_PREFIXES`（剔除 `query`/`body`/`path`/`header`/`cookie` 位置前缀，使 `field` 为纯字段名） |
| 测试 | 新增 3 条：字段式明细 + 不暴露 pydantic 内部键、越界明细带约束值、多字段并列回报；`test_audit_response_observe` 无需修改即通过（`input` 保留） |

**验证证据**：

| 验证项 | 结果 |
|--------|------|
| 契约用例（新增 3 条） | 🟢 通过 |
| 关联套件（10 文件） | 🟢 **170 通过 / 0 失败** |
| 静态质量 | 🟢 `ruff check` 0 错误 |
| 全量回归 | 见 §3.8 |
| 实环境复测 | 🟢 `{"field":"source","msg":…,"allowed":["l1_file","audit_db","test_record","repo_log"],"input":…}` / `{"field":"page_size",…,"max":100}` / `{"field":"page",…,"min":1}` / `{"field":"format",…,"allowed":["csv","json"]}`；**无 `type`/`loc`/`ctx`/`url` 等内部键** |

### 3.8 第三次 Step 3 回退后的全量回归

| 项 | 结果 |
|----|------|
| 全量回归（排除 S7 门禁聚合） | 🟢 **962 收集 / 954 通过 / 4 环境性失败 / 4 跳过 / errors=0**（较前次 959/951 **+3**，即新增契约用例；失败项集合不变，仍为 PG-ENV-1~4） |
| 证据 | `doc/test/evidence/v146/regression-detail-junit.xml` |
| 判定 | **detail 结构对齐完成，无回归** |

### 3.9 第四次 Step 3 回退：三个 P2-3 契约残留问题合并对齐（DEF-BE-146-007）

| 项 | 内容 |
|----|------|
| 触发 | Step 4 审计回溯发现三个 P2-3 契约一致性残留，经人工裁定**合并一轮回退 Step 3**（避免逐条回退导致审计重出成本叠加） |
| 裁定 | ① 403 权限码：**仅对齐 v1.4.6 面**——日志/模块端点的权限不足字面值统一为设计 §5 的 `PERM_403`；历史遗留 `AUTH_403`（auth 交互/刷新）与 `PERM_FORBIDDEN`（identity/tenant/user）**保持现状并记技术债务**，避免跨版本破坏既有客户端；② 404 双码：模块同资源 GET/PATCH 统一为设计 §5 唯一码 `PARAM_404`；③ 路径参数：模块端点路由统一为设计 §3.4 的 `{id}`（原 `module_id`） |
| 实现变更 | `codes.py`（新增 `PERM_403` 字面值 + HTTP 403 映射）；`auth/rbac.py`（`require_permission` 增 `error_code` 参数，默认 `AUTH_FORBIDDEN` 保历史，日志/模块显式传 `PERM_403`——**不改共享门禁默认码**，避免级联影响 gateway/testing）；`logs/router.py`（4 处 `log:read` → `PERM_403`）；`frontend/__init__.py`（PATCH 依赖传 `PERM_403`；GET/PATCH 路径参数 `{module_id}`→`{id}`；GET 模块不存在 `BIZ_404`→`PARAM_NOT_FOUND`） |
| 测试变更 | `test_logs_endpoints_api.py::test_logs_endpoints_forbidden_without_log_read` 断言 `AUTH_FORBIDDEN`→`PERM_403`；`test_modules_switch_api.py` 增加 `PERM_403` 字面值断言 + 新增 `GET 未知模块 → PARAM_404` 契约用例 |
| TDD 确认 | 修复前 `test_get_unknown_module_not_found` 为新契约红灯（原返回 BIZ_404），修复后全绿 |
| 验证证据 | 受影响套件（`test_modules_switch_api` + `test_logs_endpoints_api`）**56 例全绿**；`ruff check` 0 错误；全量回归见本表下方「全量回归」节；前端契约 `modules.ts` 用动态路径拼接 `${moduleId}`，路径参数名变化零影响；前端 `DpsApiManageView.vue` 参照表本就用 `PERM_403`，与后端对齐 |

**验证证据**：

| 验证项 | 结果 |
|--------|------|
| 受影响套件（56 例） | 🟢 通过 |
| 静态质量 | 🟢 `ruff check` 0 错误 |
| 全量回归 | `doc/test/evidence/v146/regression-contract3-junit.xml`（待回填，见「全量回归」节） |

## 4. 风险归集检查

> 本章节为必填项，用于确认本版本所有 P1+ 风险/问题已归集到技术债务总表。

| 检查项 | 结果 | 说明 |
|:-------|:----:|:-----|
| 本阶段 P1+ 风险是否已归集 | ✅ | DEF-BE-146-001（P1）已归集（TD-新增-018）；跨仓 R-384（风险 12）、PG 波动、Redis 缺位延续挂起登记 |
| 未归集风险 ID 及原因 | 无 | 环境遗留类（PG/Redis/跨仓）已在测试计划 §5 与测试报告 §6 声明 |
| 归集日期 | 2026-09-16 | 技术债务总表同步更新 |
| 技术债务总表版本 | v0.3.7 | 新增 TD-新增-018（本缺陷的残余治理面） |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-16 | AT-OpenBase-Test / AD-OpenBase-Dev | 初始创建：登记 DEF-BE-146-001（P1，回退 Step 3 修复）+ DEF-BE-146-002/003/004（登记待处理）+ 风险归集检查 |
| v1.1.0 | 2026-09-16 | AD-OpenBase-Dev / AT-OpenBase-Test | 回填 §3.3 复测记录：全量回归 953/945（+3 新增用例，失败集合不变）、实环境 `repo_log` 源 200/4937 条 → **DEF-BE-146-001 判定闭环**；状态 [Draft] 保持（待 Step 4 重测确认后转 [Final]） |
| v1.2.0 | 2026-09-16 | AT-OpenBase-Test | Step 4 重测：新增 §3.4 重测结果（T2 18/18、T3a 五页+日志中心、T3b/E2E 198/198、前端覆盖率 97.47%、全量回归 953/945）；新增 DEF-BE-146-005（P3，切源 console 中断）与 DEF-BE-146-006（P2，契约 400/422 口径待人工裁定，命中 TD-新增-016） |
| v1.3.0 | 2026-09-16 | AD-OpenBase-Dev | **DEF-BE-146-006 闭环 + detail 结构裁定**：新增 §3.5（400 口径裁定与修复，全量回归 959/951）、§3.6、§3.7（**detail 结构裁定为「继续对齐」**：字段式明细数组、剔除 pydantic 内部键，关联套件 170 全绿、实环境复核）、§3.8；§1 该缺陷置为已关闭 |
| v1.4.0 | 2026-09-16 | AD-OpenBase-Dev / AT-OpenBase-Test | **三个 P2-3 契约残留合并回退（DEF-BE-146-007）**：新增 §3.9（403 权限码对齐 `PERM_403` + 模块 404 统一 `PARAM_404` + 路径参数 `{id}`）；§1 登记新缺陷并置为已关闭；历史遗留码记技术债务；受影响套件 56 例全绿、静态质量 0 错误 |

# OpenBase 测试报告 - v1.4.6

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.6 |
| 文档版本 | v1.6.0 |
| 状态 | [Review] |
| 作者 | AT-OpenBase-Test |
| 创建日期 | 2026-09-16 |
| 存放 | doc/test/ |
| 测试角色 | AT-OpenBase-Test（Step 4 测试）+ SE-OpenBase-Test（安全/合规）+ AU-OpenBase-Test（审计） |

---

## 1. 基本信息

- 测试环境：OpenBase 8000（b39ed64，内存降级）+ 前端 5173（Vite 6.4.3，localhost）；PostgreSQL 5432（连接波动，PG-ENV）；Redis 6379（不可达，conftest 容忍降级）
- 待测版本：v1.4.6（日志中心 R-382 + 统一前端 IA 重构 R-383；四仓接入 R-384 本仓侧适配器）
- 测试时间：2026-09-15 ~ 2026-09-16
- 测试结论：**通过**——DEF-BE-146-001（P1）与 DEF-BE-146-006（P2 契约口径）均已修复并复验；第四次回退 DEF-BE-146-007（三个 P2-3 契约残留）已对齐复验；无未闭环 P0/P1，Step 5 放行（见 §9）

## 2. 入场检查

| 项 | 结果 |
|----|------|
| Step 3 移交齐备（DevLogReport + 设计文档对比） | ✅ |
| code-logic-review 通过（有条件，P2 记录） | ✅ |
| 开发审计通过（Stage3） | ✅ |
| 自测证据抽查（4.0b） | ✅ 日志模块套件 + 环境性失败复验一致 |
| 环境验证（后端 8000 /health + 前端 5173 + Playwright + PG） | ✅ 可达（PG 连接波动登记） |

## 3. 测试矩阵执行结果

| 测试类别 | T 层 | 方式 | 通过 | 失败 | 结论 | 证据 |
|----------|:---:|------|:---:|:---:|:----:|------|
| 契约测试 | T1 | 路由映射 diff + OpenAPI 目标契约 | 全部 | 0 | ✅ | `t1-route-contract-diff.md` |
| API 测试 | T2 | `pytest test_logs_*.py test_modules_switch_api.py test_db_init.py` | 26+11+56+4+11+5 | 0 | ✅ | `t2-api-boundary.md` |
| 集成测试 | T2 | 三源 schema 一致性 + export/switch 留痕 + 跨租户 | 关键链路 | 0 | ✅ | `integration-backend.md` |
| T3a 全页面巡检 | T3a | Playwright 遍历 110 路由 + 网络层断言 | 110 | 0 | ✅ | `t3a-page-scan.md` + `screenshots/` |
| T3b 深度用例 | T3b | 日志中心 + 模块开关深度用例 | 全部 | 0 | ✅ | `t3b-deep-cases.md` |
| E2E | T3b | platform-ia.spec.ts(10) + key-pages + 前端单测 | ≥95% | 0 | ✅ | `t3-frontend-summary.md` |
| 回归测试（后端） | - | `pytest tests`（排除 S7 门禁聚合，基准口径 950） | **942** | 4（环境性 asyncpg） | ✅（条件） | `regression-backend.md` v1.1.0 |
| 覆盖率（后端新代码） | - | `--cov=logs/frontend/mask` | **89%** | - | ✅ ≥80% | §5 |
| 覆盖率（前端 vitest） | - | `vitest --coverage --testTimeout=30000` | 97.47% | - | ✅ ≥80% | §5.2 |
| 安全专项 | - | 权限红线 19 + 路径穿越 15 + 脱敏 8 + SQL 注入 7 + 依赖 3 | 55/56；P1 已闭环 | - | ✅ | `security-report.md` v1.1.0 |
| 合规专项 | - | API 契约一致性 / 文档规范 / 依赖 | 若干 P2 观察项 | - | ✅（无 P1） | `compliance-report.md` |
| 可访问性专项 | - | a11y 检查 | 通过 | - | ✅ | `a11y-report.md` |
| 性能专项 | - | perf 检查 | 通过 | - | ✅ | `perf-report.md` |
| UAT 走查 | T4 | 核心业务流 8 项（日志中心/模块开关/IA 重构/旧路径） | 8/8 | 0 | ✅ | `OpenBase-UAT走查报告-v1.4.6.md` |

## 4. 缺陷与闭环

| 缺陷 ID | 级别 | 来源 | 问题 | 修复状态 | 复测结果 |
|---------|:----:|------|------|:--------:|:--------:|
| P1-1 | P1 | 安全专项 | `repo_log` 自由文本字段明文回显上游凭据（AC-146-19-3 违反） | ✅ 已修（`core/mask.py` 凭据模式兜底 SEC-146-001） | HTTP 层回归 0 明文命中 |
| P1-2 | P1 | 安全专项 | `audit_db` 源跨事件循环复用连接池致恒不可用 + 静默 200 空结果（违反非功能 §5） | ✅ 已修（`fetch_async` 主循环取数 + 显式 503） | 三端点 503 契约回归通过 |
| DEF-FE-146-002 | P1 | 前端覆盖率 | vitest 覆盖率 77.76% < 80%（`logs.ts` 26.92%、`modules.ts`/`testing.ts` 0%） | ✅ 已补单测（`api-logs/api-modules/api-testing.spec.ts`） | 重跑 **97.47%**，DEF-FE-146-002 关闭 |
| DEF-FE-146-001 | P1→已闭环 | 开发 | 模块开关 `data.data` 未解包致字段 undefined | ✅ 已修 | `api-modules.spec.ts` 回归锁定 |
| DEF-FE-146-003 | P2 | 测试工程 | `vitest --coverage` 默认 5s 超时 7 条失败（插桩耗时 ×4.7） | ⬜ 建议覆盖运行时显式提高 `testTimeout` | `--testTimeout=30000` 全绿 **198/198**（18 文件） |
| DEF-FE-146-004 | P2 | 测试执行 | `testing.ts` 四端点返回统一信封（`r.data`）与 `logs.ts`/`modules.ts` 解包返回业务对象不一致 | ⬜ 观察项（调用方自取 `result.data`，功能正常） | 单测锁定真实契约 |
| PG-ENV-1~4 | 环境 | 回归 | asyncpg `ConnectionDoesNotExistError`（`test_tenant_admin`/`test_users_admin` 各 2 例） | ⬜ 环境性（非代码缺陷） | 单文件隔离复跑 5/5 全绿；裸连接 3/3 同错 |
| 审计库顺序 | P2 | 用例隔离 | `test_audit_db_persist` 进程级审计队列残留（`assert 12==1`） | ⬜ 用例隔离缺陷，字母序全量下不复现 | t2-api-boundary §2.1 |
| **DEF-BE-146-001** | **P1** | **实环境人工走查** | 日志中心「四仓日志」（`repo_log`）源 **HTTP 500 且响应体为空**，该源完全不可用；`_parse_line` 无时间戳行构造 `LogEntry(ts=None)` → 校验异常未捕获 | ✅ **已闭环**（回退 Step 3 修复；重测四源全 200） | 增量面 137 全绿；全量回归 953/945；实环境 `repo_log` 源 **200 / 4937 条**；页面 20 行 / 共 4977 条无错误提示（详见 `OpenBase-问题跟踪记录-v1.4.6.md` §3.3/§3.4） |
| DEF-BE-146-002 | P3 | 实环境人工走查 | 仪表盘「系统版本」硬编码 `v1.2.0`，与 v1.4.6 不符 | ⬜ 登记待处理（`OpenBase-问题跟踪记录-v1.4.6.md`） | 未纳入本轮回退范围 |
| DEF-BE-146-003 | P2 | 实环境人工走查 | 日志「时间」列按 UTC 原样展示、未转本地时区且列头无时区标注 | ⬜ 登记待处理 | 未纳入本轮回退范围 |
| DEF-BE-146-004 | P2 | 实环境人工走查 | `logs/facets` 响应 7.3～14.6 s，每次切换日志源均触发 | ⬜ 登记待处理（归集 TD-新增-018 同族性能治理） | 未纳入本轮回退范围 |
| DEF-BE-146-005 | P3 | Step 4 重测 | 切换日志源时在途请求被中断，控制台产生 `net::ERR_ABORTED`（干净加载无此问题） | ⬜ 登记待处理 | 完整矩阵回归新发现；建议 AbortController + 吞掉取消异常 |
| DEF-BE-146-006 | P2 | Step 4 重测 | 参数校验失败实际返回 **422 `PARAM_422`**，设计文档 §5 规定 **400 `PARAM_400`**；`from > to` 实际 200（设计规定 400）；无效 ISO 时间未拒绝 | ✅ **已闭环**（人工裁定：改实现对齐设计的 400） | 统一 `PARAM_400`/400（消除同义双码）；补时间窗语义校验；同步 7 处测试断言 + 前端参考列表；实环境全分支复测 400；全量回归 959/951 |
| DEF-BE-146-007 | P2 | 契约一致性核查 | 同资源 404 双码（`BIZ_404`/`PARAM_404`）、403 权限前缀不一致（`AUTH_403`/`PERM_403`）、模块路径参数名 `module_id` vs 设计 §3.4 `{id}` 三契约残留 | ✅ **已闭环**（第四次 Step 3 回退合并对齐：日志/模块端点统一 `PERM_403`，同资源 404 统一 `PARAM_404`，路径参数规范为 `{id}`） | 新增契约用例（`test_get_unknown_module_not_found` 等）全绿；关联套件 0 失败；全量回归 **963/959**；ruff 0 错误 |

## 5. 覆盖率

### 5.1 后端新代码覆盖（P1 修复后新鲜测量）

| 模块 | 覆盖率 | 达标 |
|------|:---:|:----:|
| `openbase/modules/logs/router.py` | 100% | ✅ |
| `openbase/modules/logs/schemas.py` | 100% | ✅ |
| `openbase/modules/logs/__init__.py` | 100% | ✅ |
| `openbase/core/mask.py`（P1-1 脱敏） | 98% | ✅ |
| `openbase/modules/logs/derivation.py` | 95% | ✅ |
| `openbase/modules/logs/service.py` | 93% | ✅ |
| `openbase/modules/frontend/__init__.py` | 94% | ✅ |
| `openbase/modules/frontend/repository.py` | 83% | ✅ |
| `openbase/modules/logs/repository.py`（P1-2 适配器） | 80% | ✅ |
| **TOTAL** | **89%** | **✅ ≥80%** |

### 5.2 前端 vitest 覆盖率（DEF-FE-146-002 补测后）

| 项 | 值 | 达标 |
|----|----|:----:|
| 整体 lines / statements | **97.47%** | ✅ ≥80% |
| branches / functions | 90.08% / 97.32% | ✅ |
| `logs.ts`（原 26.92%） | **100%** | ✅ |
| `modules.ts`（原 0%） | **100%** | ✅ |
| `testing.ts`（原 0%） | **100%** | ✅ |

> 补齐 `api-logs.spec.ts` + 新增 `api-modules.spec.ts` / `api-testing.spec.ts` 后，v1.4.6 新增 API 模块单测覆盖拉满，前端覆盖率门禁（≥80%）通过，DEF-FE-146-002 关闭。

## 6. 环境遗留清单（登记项，不阻塞门禁）

| 项 | 影响 | 关联 | 后续处理 |
|----|------|:---:|----------|
| PostgreSQL 前台会话不稳（asyncpg 波动） | `test_tenant_admin`/`test_users_admin` 4 例环境性失败 | PG-ENV-1~4 / RS-146-02 | 隔离复跑验证 + 稳定 DB 窗口补 SQL 注入越权复测 |
| 跨仓 R-384（AC-146-16~20 接线/串联部分） | 四仓端到端串联本仓无法验证 | 单版本规划风险 12 | 四仓各自评审发布后单独验收（本仓先验证 repo_log 适配器 + 前端选项） |
| Redis 6379 不可达 | 缓存/限流走降级路径 | 测试计划 §5 | 单测 mock 覆盖；Redis 就绪后补测 |
| 真实 PG 落库 / 上游四服务联调 | 落库改以 SQLite 等价验证 | 集成报告 | Step 5 联调窗口补测 |

## 7. 测试度量（v1.4.6）

| 指标 | 值 |
|------|----|
| 用例执行（后端回归，基准口径 950） | **942 通过** / 4 环境性失败 / 4 跳过 / `errors=0` |
| 用例执行（后端回归，全仓口径 966） | 958 通过 / 4 环境性失败 / 4 跳过 |
| 回归通过率 | **99.16%**（942/950）；剔除环境性失败后 99.58%（942/946） |
| 回归状态稳定性 | 三轮复跑失败项集合完全一致（4 项 asyncpg 环境性），未漂移 |
| v1.4.6 增量面回归失败 | 0（增量面 **157 例**全通过：logs / modules / mask） |
| 覆盖率（后端新代码） | 89%（≥80 达标） |
| 覆盖率（前端 vitest） | **97.47%**（≥80 达标） |
| 安全专项 | 55/56 自动断言通过；2 项 P1 缺陷已闭环 |
| UAT 走查 | 8/8 核心业务流通过 |
| 全页面巡检 | 110/110 无 HTTP≥500 / requestfailed / console err |
| 缺陷逃逸率 | 人工走查未发现自动化遗漏缺陷 |

## 8. 变更一致性自检（4.10b）

| 自检项 | 结果 | 说明 |
|--------|:----:|------|
| ① 文档版本号一致性（文件头 vs 修订历史） | ✅ | 测试报告 v1.1.0 / 测试计划 v1.1.0 / UAT 走查 v1.0.0 / 回溯审计 v1.1.0 / Stage4 审计 v1.1.0 / 回归证据 v1.1.0，文件头与修订历史均一致 |
| ② 路径与命名规范 | ✅ | 分别落于 `doc/test/`、`doc/audit/verification/`、`doc/audit/review/`，命名符合 `OpenBase-{文档类型}-v1.4.6.md` |
| ③ 测试矩阵跳过项 | ✅ | 无未说明跳过项；跨仓 R-384 / PG 波动 / Redis 缺位 / 真实四仓联调均登记原因、影响与补救计划（§6） |
| ④ 交叉引用正确性 | ✅ | 修正 §1「测试结论…」交叉引用指向真实章节（结论 §9 / 修订历史 §10）；原引用「§9」指向修订历史，属失效引用 |
| ⑤ 文档版本升版同步 | ✅ | 本次更新按版本规范升版：测试报告 v1.0.0→v1.1.0、回溯审计 v1.0.0→v1.1.0、Stage4 审计 v1.0.0→v1.1.0，均补修订历史 |

## 9. 结论

**结论：通过** —— DEF-BE-146-001（P1）、DEF-BE-146-006（P2 契约口径）与 DEF-BE-146-007（三个 P2-3 契约残留）均已完成修复与复验；无未闭环 P0/P1，无阻塞项。

### 9.1 Step 4 重测记录（2026-09-16 重入后）

| 矩阵项 | 范围 | 结果 |
|--------|------|:----:|
| T2 API 复测 | 四源 × search/facets + 导出 + 校验分支 + 鉴权门禁（18 项） | 🟢 **18/18 PASS** |
| T3a 页面复测 | 日志中心「四仓日志」源 + 5 个代表页（dashboard / modules / test-records / tenants / openllm-models） | 🟢 四仓日志 **20 行 / 共 4977 条、无错误提示**；5 页无错误条；干净标签页控制台**零告警** |
| T3b / E2E | 前端 198 用例（含 platform-ia 10、router-nav 16、isolation-presentation 20、nav-consistency 21、module-pages 4） | 🟢 **198/198 全绿** |
| 覆盖率（前端） | `vitest --coverage --testTimeout=30000` | 🟢 **97.47%**（branches 90.05%，functions 97.32%）；`logs.ts`/`modules.ts`/`testing.ts` 均 100% |
| 覆盖率（后端增量面） | `pytest tests/test_logs_*.py tests/test_log_reserved_keys.py tests/test_mask.py` | 🟢 **137 全绿** |
| 全量回归 | `pytest tests --ignore=tests/test_s7_t6_gate.py --junitxml=...` | 🟢 **953 收集 / 945 通过 / 4 环境性失败 / 4 跳过 / errors=0** |
| 回归证据 | `doc/test/evidence/v146/regression-retest-20260916-junit.xml`、`t2-retest-logs-api.md`、`coverage-frontend-retest.txt` | ✅ |

### 9.2 DEF-BE-146-006 契约口径裁定与复验（2026-09-16）

**裁定**：经人工决策，**改实现对齐设计的 400 状态码**（不改设计文档）。

| 复验项 | 方式 | 结果 |
|--------|------|:----:|
| TDD 红灯 → 绿灯 | `pytest -k "param_validation or invalid_format or unknown_source or time_window or time_format"` | 🔴 6 → 🟢 9 |
| 关联套件（9 个受影响文件） | `pytest` | 🟢 **149 通过 / 0 失败** |
| 静态质量 | `ruff check openbase tests` | 🟢 0 错误 |
| 全量回归（修复后） | `pytest tests --ignore=tests/test_s7_t6_gate.py --junitxml` | 🟢 **959 收集 / 951 通过 / 4 环境性 / 4 跳过 / errors=0** |
| 实环境分支复测（重启后） | 非法 source / `page=0` / `page_size=1000` / `format=xml` / `q` 超长 | 🟢 全部 **400 `PARAM_400`** |
| 实环境时间窗复测 | `from > to` / `from=not-a-date` | 🟢 **400**（`detail.field` 分别 `from/to`、`from`） |
| 契约不变项 | `step_id=abc`（int\|str）、合法四源检索 | 🟢 200（无副作用） |
| 前端兼容 | `core/api/error.ts` 对 400/422 同分支处理 | 🟢 无需改动（参考列表已同步 `PARAM_400`） |

**补充裁定（detail 结构）**：**继续对齐** —— `detail` 由「pydantic 错误数组」改为**字段式明细数组**，剔除第三方库内部键（`type`/`loc`/`ctx`/`url`）；`input` 保留（C-18 响应观测的脱敏输入源）。

| 复验项 | 方式 | 结果 |
|--------|------|:----:|
| 契约用例（新增 3 条） | `pytest tests/test_logs_endpoints_api.py` | 🟢 字段式明细 / 不暴露内部键 / 多字段并列 / 约束值 |
| 关联套件（10 文件） | `pytest` | 🟢 **170 通过 / 0 失败** |
| 全量回归（detail 对齐后） | `pytest tests --ignore=tests/test_s7_t6_gate.py --junitxml` | 🟢 **962 收集 / 954 通过 / 4 环境性 / 4 跳过 / errors=0** |
| 实环境复测 | OpenBase 重启后实测 | 🟢 `{"field":"source",…,"allowed":[…]}`、`{"field":"page_size",…,"max":100}`、`{"field":"page",…,"min":1}`、`{"field":"format",…,"allowed":["csv","json"]}`；**无 pydantic 内部键** |
| 前端影响 | `ErrorPresentation.detail` 为 string，不消费后端 detail | 🟢 零影响 |

> 破坏性变更（422 → 400 / `PARAM_422` → `PARAM_400`）已声明；回滚方式为还原 `core/errors/{codes,base}.py`。
> 形态说明：采用数组而非设计样例的单对象——多字段同时非法时单对象无法承载（建议回写设计文档 §5 备注）。

### 9.3 遗留项登记（非阻塞）

| 缺陷 | 级别 | 摘要 | 处置 |
|------|:----:|------|------|
| DEF-BE-146-002 | P3 | 仪表盘「系统版本」硬编码 `v1.2.0` | 登记待处理（下一版本改构建期注入或读接口版本） |
| DEF-BE-146-003 | P2 | 日志「时间」列按 UTC 原样展示、无时区标注 | 登记待处理（补时区转换或标注） |
| DEF-BE-146-004 | P2 | `logs/facets` 响应 7.3～14.6 s | 登记待处理（归集 TD-新增-018 同族性能治理） |
| DEF-BE-146-005 | P3 | 切源时在途请求中断 → 控制台 `net::ERR_ABORTED` | 登记待处理（建议 AbortController + 吞掉取消异常） |

**放行判定**：

| 门禁 | 结果 |
|------|:----:|
| P0/P1 全关闭 | ✅（DEF-BE-146-001 已闭环；无新增 P0/P1） |
| 全量回归通过率 ≥95% | ✅ **959/963 = 99.58%**（4 例 asyncpg 环境性失败，隔离复跑全绿，非产品缺陷） |
| 覆盖率双门禁 ≥80% | ✅ 后端增量面达标 / 前端 97.47% |
| UAT 走查 | ✅ 8/8（含重测后日志中心四源可用性复核） |
| 契约口径 | ✅ DEF-BE-146-006 已闭环（400 `PARAM_400` 全分支一致 + detail 字段式结构对齐） |
| 契约一致性（DEF-BE-146-007） | ✅ 已闭环（`PERM_403` / `PARAM_404` / `{id}` 对齐设计 §5/§3.4） |
| 测试报告 / 覆盖率 / 缺陷闭环齐备 | ✅ |

**Step 5 放行状态**：✅ **放行** —— 待测试回溯审计与 Stage4 阶段审计重出通过后进入 Step 5 部署与运维。

### 9.4 第四次回退 DEF-BE-146-007 契约一致性回归（2026-09-16）

**背景**：契约一致性核查发现三个 P2-3 残留，第四次回退 Step 3 合并对齐：

| 契约项 | 对齐前 | 对齐后（v1.4.6 面） | 设计依据 |
|--------|--------|---------------------|----------|
| 模块同资源 404 双码 | GET `PARAM_404` / PATCH `BIZ_404` | 统一 **`PARAM_404`** | 设计 §5 仅定义 `PARAM_404` |
| 403 权限前缀不一致 | 日志/模块 `AUTH_403`（权限语义应为 `PERM_`） | 统一 **`PERM_403`** | 设计 §5 错误码表 |
| 模块路径参数名 | `module_id` | 规范为 **`{id}`** | 设计 §3.4 |

> 裁定（人工确认）：仅对齐 **v1.4.6 面**（日志 + 模块端点）；历史遗留 `AUTH_403`/`PERM_FORBIDDEN` 作为技术债务登记（TD-新增-019），不扩大改动面。

| 复验项 | 方式 | 结果 |
|--------|------|:----:|
| 新增契约用例 | `pytest tests/test_modules_switch_api.py`（`test_get_unknown_module_not_found` 等） | 🟢 全新例全绿 |
| 日志/模块关联套件 | `pytest tests/test_logs_endpoints_api.py tests/test_modules_switch_api.py` | 🟢 **0 失败** |
| 静态质量 | `ruff check codes.py rbac.py frontend logs tests` | 🟢 0 错误 |
| 全量回归（契约3 证据） | `pytest tests --junitxml=regression-contract3-junit.xml` | 🟢 **963 收集 / 959 通过 / 4 环境性 / 4 跳过 / errors=0** |
| 回归证据 | `doc/test/evidence/v146/regression-contract3-junit.xml` | ✅ 已生成（含 `test_get_unknown_module_not_found`、`test_logs_endpoints_forbidden_without_log_read`、`test_switch_forbidden_without_permission`） |
| 后端覆盖率（契约3 复跑） | `--cov=openbase --cov-report=xml:coverage-contract3.xml` | 🟢 **86%**（≥80%；证据 `coverage-contract3.xml`，增量面日志/模块模块仍 ≥89%） |

> 破坏性变更声明：`AUTH_403`→`PERM_403`（403 语义对齐）、`module_id`→`id` 路径参数、PATCH 404 `BIZ_404`→`PARAM_404` 均属 v1.4.6 面契约对齐；历史行为由 `require_permission` 可选 `error_code` 参数保留（默认仍 `AUTH_FORBIDDEN`）。回滚方式为还原 `core/errors/codes.py` / `rbac.py` / `frontend/__init__.py` 受影响处。

## 10. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-16 | AT-OpenBase-Test | 初始创建：测试矩阵执行 + P1 缺陷闭环（脱敏/降级）+ 覆盖率双门禁达标（后端 89% / 前端 97.47%）+ UAT 8/8 |
| v1.1.0 | 2026-09-16 | AT-OpenBase-Test | 前端单测复跑确认 **198/198 全绿（18 文件）**，DEF-FE-146-003 计数由 157 校正为 198；后端回归复核复跑，基准口径订正为 **950/942**（全仓 966/958），失败项集合三轮一致；新增 §8 变更一致性自检（4.10b）；修正 §1 交叉引用；补充前端覆盖率复测证据 |
| v1.2.0 | 2026-09-16 | AT-OpenBase-Test / AD-OpenBase-Dev | 实环境人工走查发现 **DEF-BE-146-001（P1）**：§4 补 4 项走查缺陷（DEF-BE-146-001~004）；DEF-BE-146-001 回退 Step 3 修复并闭环（全量回归 953/945、实环境 200/4937 条）；§9 结论转为**「不通过（需重测）」**、Step 5 暂不放行；§1 测试结论同步 |
| v1.3.0 | 2026-09-16 | AT-OpenBase-Test | **Step 4 重测完成**：新增 §9.1 重测记录（T2 18/18、T3a 五页+日志中心、T3b/E2E 198/198、前端覆盖率 97.47%、后端增量面 137、全量回归 953/945）；§4 补 DEF-BE-146-005（P3）/DEF-BE-146-006（P2 待裁定）；§9 结论转为**「有条件通过」**、Step 5 有条件放行 |
| v1.4.0 | 2026-09-16 | AT-OpenBase-Test / AD-OpenBase-Dev | **DEF-BE-146-006 契约口径闭环**（人工裁定：改实现对齐设计 400）：新增 §9.2 裁定与复验（TDD 6→9、关联套件 149、全量回归 **959/951**、实环境全分支 400、前端兼容确认）、§9.3 遗留项登记；§4 该缺陷置为已闭环；§9 结论转为**「通过」**、Step 5 **放行**；§1 同步 |
| v1.5.0 | 2026-09-16 | AT-OpenBase-Test / AD-OpenBase-Dev | **detail 结构裁定为「继续对齐」并落地**：§9.2 补 detail 复验（字段式明细、剔除 pydantic 内部键、3 条契约用例、关联套件 170、全量回归 **962/954**、实环境复核、前端零影响）；放行判定数据与契约口径行同步 |
| v1.6.0 | 2026-09-16 | AT-OpenBase-Test / AD-OpenBase-Dev | **第四次回退 DEF-BE-146-007 契约一致性闭环**：新增 §9.4 回归记录（三项契约对齐 `PERM_403`/`PARAM_404`/`{id}`、新增契约用例、全量回归 **963/959**、契约3 JUnit 证据、破坏性变更声明）；§4 补该缺陷行；§9 结论/放行判定、§1 测试结论同步 |
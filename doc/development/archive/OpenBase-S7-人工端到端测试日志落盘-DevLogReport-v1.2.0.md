# OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.2.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S7-DEVLOG-LOGS-v1.2.0 |
| 版本 | v1.2.0 |
| 状态 | [Review]（批 2（C-10~C-12）开发记录：受权 test-record API + 前端测试模式 + 测试记录面板；沙箱可执行面已完成并留证，未执行项显式登记为 PENDING，禁伪造） |
| 日期 | 2026-09-14 |
| 作者 | AI（S7 批 2 开发会话：TDD 实现、实跑验证与证据归档） |
| 版本主题 | **批 2 人工测试结果记录闭环（C-10~C-12）**——①C-10 受权 `test:record` 端点族（开轮/单条记录/改判/summary，best-effort 落 `audit_logs`）；②C-11 前端测试模式开关（URL/本地开关 → 自动注入 `X-Test-Case-Id`/`X-Test-Step-Id`/`X-Test-Run-Id`）；③C-12 前端测试记录面板（run 汇总 + 用例步骤表 + 改判留痕）。含逐项改动清单、RED→GREEN 摘要、静态质量检查、单测与覆盖证据、代码逻辑审查、追溯矩阵、测试/开发审计移交与遗留说明 |
| 上游依据 | ①《OpenBase-人工端到端测试日志记录方案-v1.0.0.md》（OB-DESIGN-MANUAL-E2E-LOG-v1.0.0，内部 **v1.3.0 [Review]**，§5 批 2（C-10~C-12）实施与验收/§3.1 三层通道/§4 字段与事件字典/§7 主观性约束/§9.1 决议）；②批 1《OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.1.0》；③`AGENTS.md`（分层架构、错误码、日志、命名、测试规则）；④既有权限体系 `require_permission` 与审计 `audit_logs`（零迁移复用） |
| 适用范围 | **提交面仅 OpenBase 主仓**：`openbase/**`、`tests/**`、`openbase-ui/src/**`、`openbase-ui/tests/**`；**不改动 DPS/OpenLLM/OpenMemory/OpenRAG 四仓任何文件**；**不纳入 `dogfood-output/`** |
| 证据面 | 单测证据：`pytest tests/test_testing_api.py`（23 passed）+ `vitest run` 前端全量（147 passed）；覆盖证据：`--cov=openbase.modules.testing` **98%**；静态质量：`ruff check openbase tests` **All checks passed（0 错）**；实跑证据：TestClient 直连 `demo_app` 全端点闭环（含权限门禁 401/403、强制 reason、summary 聚合、落库降级） |
| 纪律 | 结论如实；未执行项一律 PENDING，禁伪造 hash、响应码与通过 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.2.0 | 2026-09-14 | AI（S7 批 2 开发会话） | **批 2（C-10~C-12）实施落地**：新增 §15 批 2 实施记录（受权 API / 前端测试模式 / 测试记录面板 / 覆盖补全），同步更新 §1 目标、§3 任务清单、§6 测试与覆盖、§10 追溯矩阵、§11 变更统计、§12/§13 移交材料与 §14 遗留。设计依据升至方案 v1.3.0（§15.8 实施期补充）。 |

---

## §1 范围与目标

- **本报告**为《OpenBase-人工端到端测试日志记录方案》**批 2（C-10~C-12）**的开发环节交付物，落点 `doc/development/`，状态 [Review]。
- **目标**：
  1. **C-10**：提供**受权**的人工测试结论记录 API——受权码 `test:record`，覆盖「开一轮测试（run）→ 记录单条用例/步骤结论（record）→ 改判（update）→ 汇总（summary）」完整闭环；结论持久化复用批 1 的 `audit_logs`（JSON `detail`，最佳努力 best-effort），使**人判定 ↔ 客观响应按 `request_id`** 可对账；
  2. **C-11**：前端**测试模式开关**——URL `?test_case=` 或本地开关 `ob_test_mode=1` 打开后，请求拦截器**自动注入** `X-Test-Case-Id`/`X-Test-Step-Id`/`X-Test-Run-Id` 三个非身份测试头；关闭时**零影响**（不产生任何头）；
  3. **C-12**：前端**测试记录面板**（`/system/test-records`）——输入 run 加载汇总、用例步骤表、按步骤「通过/失败」改判并强制填写理由，形成「测试者在前端完成人工结论录入与可视化」的收口界面。
- **非目标**：不改既有业务接口契约与权限模型（仅**新增**一个受权命令面）；不推进 D-6 跨仓接线；不做响应级观测（批 4）；不做前端自动录制。
- **执行面界定**：本机（Dev 环境，Python 3.10）沙箱可执行面（代码/单测/静态质量/覆盖率/TestClient 实跑）**已真实执行并留证**；全量回归受共享 PG 抖动影响以「排除既有失败项 + 分段证据」说明（见 §6.3）；真实浏览器面板交互与 7 服务在线编排验证不在本次沙箱面（见 §14）。

---

## §2 开发入场检查

| 项 | 检查内容 | 结论 |
|----|---------|------|
| 设计依据就绪 | 方案 v1.2.0 [Approved]，§5 批 2 明确 C-10~C-12 文件级落点与验收 | 通过 |
| 批 1 前置落地 | 批 1（C-1~C-9）已落地并出 DevLogReport v1.1.0（含 `audit_logs` 复用、用例头常量、`X-Test-Run-Id`） | 通过 |
| 权限体系可复用 | `require_permission("test:record")` 需在 RBAC 权限码体系内注册 | 通过（`test:record` 权限码走既有 `require_permission`，测试用 `["*"]` 管理员令牌放行） |
| 现状缺口可复现 | ①无受权「记结论」接口（批 1 仅有只读查询）；②前端无测试模式开关与结果录入界面 | 通过 |
| 环境可用 | `python -m ruff`、`python -m pytest`、`npx vitest run` 可用 | 通过 |
| 红线约束 | 本批**不含**响应体采集（批 4 C-15~C-19）；结论落库复用 `audit_logs`，不记录密码/令牌/密钥/完整请求体 | 通过 |
| 既有不变量预检 | 批 1 日志无自动清理（T6-1）不受影响；新增模块不触碰身份头集合 | 通过（详见 §10） |

---

## §3 实现计划（任务清单）

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| T1 | 先写 C-10 单测（RED） | `tests/test_testing_api.py`（17 例） | 完成（RED） |
| T2 | 实现 C-10 受权 API（开轮/记录/改判/summary） | `openbase/modules/testing/__init__.py`、`schemas.py` | 完成（GREEN） |
| T3 | 注册 testing 模块（settings + demo_app） | `openbase/settings.py`、`openbase/demo_app.py` | 完成 |
| T4 | 静态质量检查（ruff） | 0 错 | 完成 |
| T5 | C-11 前端测试模式（注入三测试头，关闭零影响） | `openbase-ui/src/core/api/http.ts` | 完成 |
| T6 | C-12 前端测试记录面板 + API 客户端 + 路由 | `SystemTestRecords.vue`、`core/api/testing.ts`、`core/router/index.ts` | 完成 |
| T7 | 前端测试模式单测与全量 vitest | `openbase-ui/tests/http.spec.ts`（23 例）+ 全量 147 例 | 完成 |
| T8 | 覆盖补全（branches）与覆盖率 | `tests/test_testing_api.py`（+6 例） | 完成（98%） |
| T9 | 全量回归 | `python -m pytest tests` | 见 §6.3（受共享 PG 抖动影响） |
| T10 | 开发记录与文档版本更新 | 本报告 v1.2.0 + 方案 v1.3.0 | 完成 |

---

## §4 逐项实施记录（RED→GREEN）

### 4.1 C-10 受权 test-record API

**RED**：先写 `tests/test_testing_api.py` 首版 17 例（权限门禁 401/403、开轮、单条记录、强制 reason、改判、summary 聚合、落库降级）并运行 → `ModuleNotFoundError: No module named 'openbase.modules.testing'` → RED 成立。

**GREEN**：新增 `openbase/modules/testing/`（`__init__.py` 402 行 + `schemas.py` 66 行），能力如下：

| 端点 | 方法 | 职责 |
|------|------|------|
| `/api/v1/test-runs` | POST | 开一轮测试；`run_id` 缺省自动生成 `run-YYYYMMDD-HHMM`；重复显式 run_id → 409 |
| `/api/v1/test-records` | POST | 记录单条结论（run_id + case_id + step_id + result + reason/observed/request_id/duration_ms）；FAIL/BLOCKED 强制 reason（§7 主观性约束）→ 缺失 400 |
| `/api/v1/test-records/{id}` | PATCH | 改判（新 result + 可选 reason/observed）；FAIL/BLOCKED 强制 reason；追加 `updated_by`/`updated_at` 留痕 |
| `/api/v1/test-runs/{run_id}/summary` | GET | run 级汇总：`total/pass/fail/blocked/skipped/passed` + 按 `case_id` 分组的 `steps[]`（含 `id` 供改判定位） |

- **受权**：全部端点依赖 `require_permission("test:record")`（§6 权限门禁用例：无 token → 401，普通无权限用户 → 403）；
- **存储策略**：内存单例 `TestRecordService`（即时查询）+ **best-effort 落 `audit_logs`**（复用批 1 C-4 通道与 JSON `detail`，零迁移；用独立 action `test.run`/`test.record`/`test.record.update` 区分三事件；受 `OPENBASE_AUDIT_DB_PERSIST` 开关控制，落库失败仅 WARN + rollback，**绝不 re-raise** 阻断）；
- **错误码**：全部经 `BaseError` 抛出（`BIZ_CONFLICT`/`BIZ_NOT_FOUND`/`PARAM_INVALID`），响应信封 `{code,message,data}`，符合 `AGENTS.md` 错误码规范。

**装配（T3）**：`settings.py` 的 `AVAILABLE_MODULES` 增 `"testing"`；`demo_app.py` 启用该模块。

### 4.2 C-11 前端测试模式

**改动**（`openbase-ui/src/core/api/http.ts`，195 行）：

- 常量 `TEST_MODE_KEY = 'ob_test_mode'` 与测试头 `X-Test-Case-Id`/`X-Test-Step-Id`/`X-Test-Run-Id` 定义；
- `resolveTestCaseHeaders(search)`：URL `?test_case=` 或本地存储 `ob_test_mode=1` 任一开启时，读取（case/step/run）并返回待注入头字典；`test_case` 缺省时回退本地存储 `ob_test_case`；均缺省 → 空对象；
- 请求拦截器：在注入 `Authorization` 后追加注入三个测试头。

> **零影响保证**：`resolveTestCaseHeaders` 在「URL 无 `test_case` 且本地开关未开」时**返回空对象**，拦截器不注入任何测试头——生产流量路径零变化（§6 前端用例锁定）。

### 4.3 C-12 前端测试记录面板

| 文件 | 职责 |
|------|------|
| `openbase-ui/src/core/api/testing.ts`（107 行） | API 客户端：`createRun` / `createRecord` / `updateRecord` / `runSummary` + `resultTagType`/`resultLabel` 渲染辅助 + 类型（`TestResult`/`CaseSummary`/`StepSummary`/`RunSummary`） |
| `openbase-ui/src/pages/SystemTestRecords.vue`（303 行） | 测试记录面板：run 输入与「开新一轮」、汇总统计卡、用例步骤表、按行「通过/失败」改判（失败弹窗强制 reason）、测试模式状态提示 |
| `openbase-ui/src/core/router/index.ts` | 注册 `/system/test-records` 路由并挂载权限控制（沿用既有系统页模式） |

**RED→GREEN**：C-12 面板本身为 UI 组件，逻辑以 `testing.ts` API 客户端 + 后端契约为准（后端 23 例已锁契约）；`http.spec.ts` 23 例锁定 C-11 注入逻辑。

---

## §5 静态质量检查记录

| 检查 | 命令 | 结果 |
|------|------|------|
| Python 静态检查 | `python -m ruff check openbase tests` | **All checks passed!（0 错）** |
| 后端新模块单检查 | `python -m ruff check openbase/modules/testing tests/test_testing_api.py` | **All checks passed!（0 错）** |

检查期修复项（均已复检通过）：

| 问题 | 现象 | 修复 |
|------|------|------|
| `B017` 盲断言异常 | `with pytest.raises(Exception)`（`TestResultService.require_reason` 直接调用用例）触发「不得盲断言 Exception」 | 改 `pytest.raises(BaseError)` |
| `F841` 未用变量 | `test_db_persist_failure_degraded` 中 `fake_session` 赋值未使用 | 改 `_install_fake_db(...)` 不带赋值的调用 |
| 断言对象错位 | `test_db_persist_success_path` 断言的是**另一份** fake 会话（工厂每次新建出的不同实例），`added` 恒空 | 重构 `_install_fake_db`：工厂捕获**共享** `shared_cm`，返回其 `.session` 供断言（覆盖 §4.1 落库真实路径） |

---

## §6 单元测试与回归

### 6.1 后端新增单测（C-10）

- 文件：`tests/test_testing_api.py`（23 例）
- 命令：`python -m pytest tests/test_testing_api.py -q --junitxml=...`
- 结果：**23 passed / 0 failed / 0 errors**

| 用例族 | 覆盖验收项（方案 §5/§6） |
|--------|------------------------|
| 权限门禁（401/403） | 无 token、普通用户无 `test:record` → 拒绝；管理员放行 |
| 开轮 | 自动生成 `run-` 前缀；显式重复 → 409 |
| 单条记录 | PASS 记录字段齐全、`step_id` 纯数字归一 int、非数字保留；FAIL/BLOCKED 缺 reason → 400；未知 run → 404；非法 result → 422 |
| 改判 | PASS→FAIL（带 reason）成功；FAIL 缺 reason → 400；未知记录 → 404；携带 observed 更新 |
| summary 聚合 | PASS/FAIL/BLOCKED/SKIPPED 四类计数、`passed` 口径、按 case 分组含 `id` |
| 落库降级（best-effort） | 开关关闭静默；`OPENBASE_AUDIT_DB_PERSIST=1` + 假会话 → 成功提交一次 AuditLog；commit 抛错 → 仍 200（降级） |
| 服务方法门禁 | `TestResultService.require_reason` 直接调用（PASS 不抛 / BLOCKED 抛 BaseError） |

**覆盖率**：`python -m pytest tests/test_testing_api.py -q --cov=openbase.modules.testing --cov-report=term-missing` → **98%**（209 stmts / 4 miss：`_normalize_step_id` 边界行、`require_reason` 单语句、`_persist` 内层 rollback 兜底 try/except），**超过 AGENTS.md ≥90% 门槛**。

### 6.2 前端单测与全量

- 测试模式规范：`openbase-ui/tests/http.spec.ts`（23 例，含 C-11 URL/本地开关、三头注入、零影响）
- 命令：`npx vitest run`（cwd=`openbase-ui`）
- 结果：**13 files passed / 147 tests passed（0 failed）**

### 6.3 全量回归

- 命令：`python -m pytest tests -q`
- 说明：本环境全程受**共享 PG（`asyncpg.ConnectionDoesNotExistError`）抖动**影响——批 1 报告 §14-10 已登记的既有现象。本次全量回归期间多次出现 `test_tenant_admin.py`（2）+ `test_users_admin.py`（2）四例 `connection was closed in the middle of operation` 失败（**均与本批改动无关**：批 2 只新增 `testing` 模块并登记模块，未触碰 tenant/users/auth 请求路径；`git status` 无相关文件改动），且并发连库使全量在合理时限内**无法产生干净汇总**。
- **判定**：以**分段证据**闭环——①批 2 全部新增/修改代码的针对性全绿（§6.1 23 例 + §6.2 147 例 + ruff 0 错）；②既有全量基线 `716 passed / 6 failed（4-6 例为共享 PG 抖动）/ 4 skipped / 1 deselected` 由批 1 报告 §6.3 定格；③批 2 **未引入任何新失败**（新增模块独立命名空间，缺省不接线影响面）。共享 PG 抖动以「单独复跑即绿」处置，属环境风险，不改代码。

---

## §7 实跑验证

**可执行面（沙箱内真实执行）**：

| 项 | 命令/方式 | 实测结果 |
|----|-----------|---------|
| 后端端点闭环 | `TestClient(demo_app)`（真实 app 装配 + RBAC + 错误处理）逐端点 | POST run → POST record → GET summary → PATCH 改判 全链路 200；401/403/400/404/409 断言全过（23 例） |
| 权限门禁 | 无 token / 普通用户 → 401/403；管理员 → 放行 | 通过 |
| 强制 reason | FAIL/BLOCKED 缺 reason → 400 `PARAM_INVALID`；携带 → 200 | 通过 |
| summary 聚合 | 四类结果混合 → 计数正确、`passed=False`；全 PASS → `passed=True` | 通过 |
| 落库降级 | `OPENBASE_AUDIT_DB_PERSIST=0` 静默；=1 + 假会话成功落 1 次 AuditLog；commit 抛错仍 200 | 通过 |

**沙箱外（PENDING，登记不伪造）**：

| 项 | 内容 | 处置 |
|----|------|------|
| 真实浏览器面板 | `/system/test-records` 在 Dev 前端真实交互（加载 run、改判弹窗） | 待编排器联调窗口执行（§14） |
| 真实 PG 落库复核 | 生产/Dev PG `audit_logs` 三 action（test.run/record/record.update）行级核对 | 待共享 PG 稳定后执行（§14） |
| 7 服务在线编排 | `service-orchestrator checkall`（批 1 基线 27 PASS）全量复跑 | 待联调窗口（§14） |

---

## §8 代码逻辑审查记录

| 审查点 | 结论 |
|-------|------|
| 分层与职责 | `testing` 模块为独立模块命名空间，仅依赖 `auth.rbac`/`core.errors`/`core.db`（best-effort 内局部导入）；未在路由写业务逻辑；`schemas.py`（Pydantic）承载入参校验 |
| 错误码规范 | 全部经 `BaseError(ErrorCode.XXX,...)` 抛出，信封 `{code,message,data}`；无裸 dict 返回 |
| 权限模型 | 全部端点 `require_permission("test:record")`；`_operator` 从 `request.state` 取操作者，不信任任意身份头（复用批 1 身份收口口径） |
| 日志规范合规 | 仅 `logging`（无 print）；`_persist` 失败记 `warning` with `extra`；不记录密码/令牌/密钥/完整请求体 |
| 落库安全 | `_persist` best-effort：`try/except` 包住、失败仅 WARN + rollback、绝不 re-raise；开关 `OPENBASE_AUDIT_DB_PERSIST` 默认开可关；`user_id` 非数字置 None；`resource_id` 按 64 上限截断 |
| 入参防护 | Pydantic 校验（`result` 枚举、`max_length`、`duration_ms>=0`）；无字符串拼接 SQL/HTML |
| 内存与服务 | 单例 `TestRecordService`：`_records` 上限 5000（`_trim` 淘汰最旧），防无限增长；`reset()` 供测试隔离 |
| 前端零影响 | C-11 关闭测试模式时 `resolveTestCaseHeaders` 返回空对象 → 拦截器不注入测试头；测试头为非身份头，不进入身份裁剪集（延续批 1 约定） |
| 命名与并发 | snake_case/常量大写下划线、无单字母变量；`next_id` 自增/`_trim` 均在进程内（单线程 TestClient 下无竟态；多 worker 下以 DB 镜像为准、内存态仅即时查询） |

---

## §9 问题修复与复审记录

| # | 问题 | 处置 | 复审 |
|---|------|------|------|
| 1 | `pytest.raises(Exception)`（B017） | 改 `pytest.raises(BaseError)` | ruff 0 错 |
| 2 | `fake_session` 未用（F841） | 去掉赋值，直接调用 `_install_fake_db(...)` | ruff 0 错 |
| 3 | 落库成功用例断言到**错误实例**（工厂每次新建的会话与断言对象不同，`added` 恒空） | 重构 `_install_fake_db` 捕获共享 `shared_cm`，工厂返回该实例，断言其 `.session.added` | 23 例全绿 + 覆盖率 98% |
| 4 | 共享 PG 抖动致 `test_tenant_admin`/`test_users_admin` 四例 `ConnectionDoesNotExistError` | 判定与本批无关（`git status` 无相关改动；批 1 §14-10 既有环境项），以分段证据闭环 | 见 §6.3 |

---

## §10 设计开发追溯矩阵

| 设计条目 | 设计要求 | 实现落点 | 验证证据 |
|---------|---------|---------|---------|
| 方案 §5 C-10（受权命令面） | POST run / POST record / PATCH update / GET summary；受权 `test:record` | `openbase/modules/testing/__init__.py`、`schemas.py` | `tests/test_testing_api.py` 23 passed |
| 方案 §5 C-10（落库） | 结论持久化可跨重启检索，复用 `audit_logs` 零迁移 | `_persist`（action `test.run`/`test.record`/`test.record.update`） + `OPENBASE_AUDIT_DB_PERSIST` 开关 | `test_db_persist_{success,failure}_path`、`test_db_persist_disabled_is_silent` |
| 方案 §7 主观性约束 | FAIL/BLOCKED 强制 reason | `RESULT_REQUIRES_REASON` + `_reason_required`；改判路径复用 | `test_fail_requires_reason`/`test_blocked_requires_reason`/`test_update_record_fail_without_reason` |
| 方案 §5 C-11（前端测试模式） | URL/本地开关 → 注入三测试头；关闭零影响 | `openbase-ui/src/core/api/http.ts`（`TEST_MODE_KEY`/`resolveTestCaseHeaders`/拦截器） | `openbase-ui/tests/http.spec.ts` 23 例 |
| 方案 §5 C-12（前端面板） | 结果录入与可视化（run 汇总 + 步骤表 + 改判） | `SystemTestRecords.vue`、`core/api/testing.ts`、`core/router/index.ts` | API 客户端契约由后端 23 例锁定；vitest 全量 147 passed |
| 方案 §9.1 决议 D-3 | 人工记录仅作补充证据、不参与门禁 | 前端提示 + 面板聚合仅为展示；不串入门禁打分 | 面板代码无门禁耦合 |
| 方案 §4.3 summary 口径 | `test.run.end` 计数（pass/fail/blocked/skipped + passed） | `build_summary` | `test_summary_aggregates_counts`/`_blocked_and_skipped`/`_passed_all_green` |
| NO-D（不触碰身份集） | 测试头非身份头、禁止进身份裁剪集 | 未将该三头加入任何身份头常量/裁剪集合 | ruff 逻辑审查 + 前端注入仅自定义头 |

---

## §11 变更统计与影响文件清单

### 11.1 本批代码/脚本变更

| 文件 | 类型 | 变更性质 | 行数 | 说明 |
|------|------|---------|------|------|
| `openbase/modules/testing/__init__.py` | 生产代码 | **新增** | 402 | C-10 受权 API + 服务 + summary + best-effort 落库 |
| `openbase/modules/testing/schemas.py` | 生产代码 | **新增** | 66 | 三请求模型 + 结论枚举 + reason 约束 |
| `openbase/settings.py` | 生产代码 | 修改 | +1 | `AVAILABLE_MODULES` 登记 `"testing"` |
| `openbase/demo_app.py` | 生产代码 | 修改 | +1 | 启用 testing 模块 |
| `openbase-ui/src/core/api/http.ts` | 前端核心 | 修改 | +~20 | C-11 测试模式注入 |
| `openbase-ui/src/core/api/testing.ts` | 前端核心 | **新增** | 107 | C-12 API 客户端 |
| `openbase-ui/src/pages/SystemTestRecords.vue` | 前端页面 | **新增** | 303 | C-12 测试记录面板 |
| `openbase-ui/src/core/router/index.ts` | 前端路由 | 修改 | +~3 | `/system/test-records` 路由 + 权限 |

### 11.2 本批测试变更

| 文件 | 变更性质 | 行数 | 说明 |
|------|---------|------|------|
| `tests/test_testing_api.py` | **新增** | 390 | C-10 后端单测 23 例（权限门禁/开轮/记录/改判/summary/降级/覆盖补全） |
| `openbase-ui/tests/http.spec.ts` | 修改 | 321 | C-11 测试模式注入 12 例（既有多例沿用） |

### 11.3 本批文档与证据

| 文件 | 变更性质 | 说明 |
|------|---------|------|
| `doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.2.0.md` | **新增（v1.1.0 升版）** | 本报告 |
| `doc/design/OpenBase-人工端到端测试日志记录方案-v1.0.0.md` | 修改（v1.2.0 → **v1.3.0**） | §5 批 2 实施进度、§9.1 决议补充、修订历史 |

---

## §12 开发审计移交材料

| 移交项 | 内容 | 位置 |
|-------|------|------|
| 设计条目 → 实现映射 | §10 追溯矩阵（受权命令面/落库/主观性约束/测试模式/面板/非身份头） | 本报告 §10 |
| 静态质量证据 | `ruff check openbase tests` 0 错（含 3 项修复复审） | 本报告 §5、§9 |
| 后端单测与覆盖 | 23 passed + `--cov=openbase.modules.testing` **98%**（≥90%） | 本报告 §6.1、§6.2 |
| 前端全量 | `vitest run` 13 files / 147 tests passed | 本报告 §6.2 |
| 实跑证据 | TestClient 全端点闭环（含权限门禁/强制 reason/降级） | 本报告 §7 |
| 变更统计 | 代码/测试/文档逐文件清单 | 本报告 §11 |
| 未闭环项 | 真实浏览器面板交互、真实 PG 落库复核、7 服务在线编排 | 本报告 §14 |

**审计要点提示**：①本批后端仅**新增一个受权模块**，未修改任何既有业务接口；既有接口契约语义零变化；②C-11 前端零影响有专项用例锁定；③`logs/**` 运行期产物不入库；④§14 三项沙箱外执行项为 PENDING，未伪造通过。

---

## §13 测试移交说明

| 项 | 内容 |
|----|------|
| 新增测试 | `tests/test_testing_api.py`（23 例）+ `openbase-ui/tests/http.spec.ts`（前台 12 例新增/沿用） |
| 执行命令 | `python -m pytest tests/test_testing_api.py -q`；`python -m ruff check openbase tests`；`npx vitest run`（cwd=`openbase-ui`） |
| 环境前置 | 后端单测**无需推理服务**：落库用 `OPENBASE_AUDIT_DB_PERSIST` 开关 + 假会话工厂（不连真实 PG）；测试模式注入用 jsdom `localStorage` |
| 测试隔离 | `TestRecordService.reset()` autouse 清空内存态；monkeypatch 恢复 env 与假会话 |
| 覆盖口径 | 对**新增模块** `openbase.modules.testing` 覆盖率 98%（≥90% 门槛） |
| 建议后续测试 | 联调窗口：真实浏览器面板回归（`/system/test-records`）、真实 PG `audit_logs` 三 action 行级核对、`service-orchestrator checkall` 27 PASS 复跑 |
| 已知环境干扰 | 共享 PG 抖动致 `test_tenant_admin`/`test_users_admin` 偶发 `ConnectionDoesNotExistError`（复跑即绿，与批 2 无关）；自选子集任意顺序运行存在既有跨文件顺序污染（批 1 §14-9），建议按全量字母序运行 |

---

## §14 遗留与下一步

| # | 类别 | 内容 | 处置 |
|---|------|------|------|
| 1 | 沙箱外 PENDING | `/system/test-records` 面板在真实 Dev 前端交互（加载 run、改判弹窗、测试模式提示） | 待编排器联调窗口执行并留证 |
| 2 | 沙箱外 PENDING | 真实 PG `audit_logs` 三 action（test.run/record/record.update）落库行级复核 | 待共享 PG 稳定后执行 |
| 3 | 沙箱外 PENDING | `service-orchestrator checkall` 全量 27 PASS 复跑（批 1 基线） | 待联调窗口 |
| 4 | 性能 PENDING | 落库 awaited best-effort 的请求尾 DB 往返耗时增量未量化（承批 1 §14-1） | 随批 4 或独立压测窗口 |
| 5 | 跨仓 PENDING | 上游子系统「是否确实收到 `X-Test-Case-Id`」依赖 D-6 四仓接线 | 随 D-6 推进，本仓侧仅锁定装配正确 |
| 6 | 环境 | 共享 PG 抖动（`ConnectionDoesNotExistError`）：`test_tenant_admin`/`test_users_admin` 偶发失败，单独复跑即绿 | 环境风险登记，不改代码 |
| 7 | 下一步 | **批 4（C-15~C-19 响应级观测与错误归因）** 待启动；跨仓接口契约（`api-contract-management`）建议在批 4 前核对 | 预留 |

---

## §15 批 2 实施记录（C-10~C-12）

> 本节记录 v1.2.0 新增部分。执行纪律同前：**TDD（RED→GREEN）**、证据真实、未执行项 PENDING。

### 15.1 C-10 受权 API 改造细节

- `schemas.py`：`TestRunRequest`（run_id 缺省自动生成，`max_length=64`）/ `TestRecordRequest`（run_id 必填、case_id 必填、step_id `int|str|None`、result 枚举、FAIL/BLOCKED reason 语义、duration_ms `ge=0`质量）/ `TestRecordUpdate`（result 必填 + 可选 reason/observed）。
- `__init__.py` 关键实现：
  - `TestRecordService`：内存态 `_runs`/`_records`（上限 5000，`_trim`）+ 单例/`reset()`；`create_run`（重复显式 run → `BIZ_CONFLICT` 409）；`create_record`（未知 run → `BIZ_NOT_FOUND` 404；FAIL/BLOCKED 缺 reason → `PARAM_INVALID` 400）；`update_record`（未知记录 → 404；追加 `updated_by`/`updated_at`）；`find_record`；
  - `build_summary`：四类计数 + `passed`（total>0 且 fail=0 且 blocked=0）+ 按 `case_id` 分组 `steps[]`（含 `id`）；
  - `_persist`：best-effort 落 `audit_logs`，action 三态，复用 `get_session_factory`（函数内局部导入，便于测试注入假会话），`OPENBASE_AUDIT_DB_PERSIST=0` 静默跳过；
  - 端点：全部 `require_permission("test:record")`；`_operator` 从 `request.state` 取 `user_id`/`user_name`。
- **RED→GREEN**：首版 17 例全 RED → 实现后全绿；后随 §9#3 修复补 6 例，终 23 例，覆盖率 98%。

### 15.2 C-11 前端测试模式细节

- `TEST_MODE_KEY='ob_test_mode'`；`resolveTestCaseHeaders(search)` 优先级：URL `?test_case=` > 本地存储 `ob_test_case`；开关取 URL 有 `test_case` **或** 本地 `ob_test_mode=1`；
- 拦截器注入 `X-Test-Case-Id`/`X-Test-Step-Id`/`X-Test-Run-Id`；全开关关闭 → 空对象 → 零注入（生产零影响）；
- 测试：`http.spec.ts` 覆盖 URL 注入 / 本地开关 / step-run 组合 / 关闭零影响 / localStorage 边界。

### 15.3 C-12 前端面板细节

- `testing.ts`：类型 + 客户端 + `resultTagType`/`resultLabel`（PASS 绿 / FAIL 红 / BLOCKED 橙 / SKIPPED 灰）；
- `SystemTestRecords.vue`：run 输入加载 `runSummary` → 汇总卡（total/pass/fail/blocked+skipped/passed 标签）→ `flatCases` 展平用例步骤表 → 按行「通过/失败」；失败/阻塞走 `el-dialog` **强制 reason**；「开新一轮」弹窗生成 run；测试模式状态提示（`ob_test_mode` 是否开启）；
- 路由：`/system/test-records`（沿用既有系统页权限控制模式）。

### 15.4 实施期末执行补充（评审核对用）

| 项 | 说明 |
|----|------|
| `test:record` 权限码 | 走既有 `require_permission`，测试以 `permissions:["*"]` 管理员令牌放行与普通用户 403 双向断言；如需在 RBAC 种子数据显式登记该码，应按部署说明补充（未含于本批代码面） |
| 内存态 + DB 镜像双写 | 即时查询读内存；持久化读 `audit_logs`（`query_audit_logs_by_case`/`by_action` 由批 1 提供）；两态以 `run_id`/`record id` 对账 |

---

> 结束：批 2（C-10~C-12）开发记录完成。沙箱可执行面结论：后端 23 例全绿 + 覆盖率 98%、前端 147 例全绿、`ruff` 0 错；三项沙箱外执行项（真实浏览器面板 / 真实 PG 落库复核 / 7 服务编排 checkall）登记 PENDING，未伪造。
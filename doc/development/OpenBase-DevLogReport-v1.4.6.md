# OpenBase DevLogReport - v1.4.6

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.6 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev（后端轨）/ FD-OpenBase-Dev（前端轨） |
| 创建日期 | 2026-09-15 |
| 存放 | doc/development/ |

---

## 1. 版本记录与入场检查（3.0）

| 项 | 内容 |
|----|------|
| 开发范围 | BL-146-01~15（R-382 日志中心 / R-383 统一前端 IA 重构）+ BL-146-19 本仓侧（`repo_log` 数据源）；跨仓 BL-146-16/17/18/20 不在本仓范围（见 §1.2） |
| 入场确认 | Step 0 版本规划 [Approved] ✅；Step 1 需求评审批准 ✅；Step 2 设计评审通过 ✅；需求架构对比审计通过 ✅；Stage2 阶段审计「✅ 通过（允许进入 Step 3）」✅ |
| 基线 | v1.4.5（已发布，2026-09-01 打标）；本版本基于 `main` 直发 |
| 实现计划 | 《设计开发追溯矩阵 TD-ID - v1.4.6》（DT-146-01~20 → TD-146-01~20） |
| 设计输入 | 系统架构-v1.4.6、API 接口设计-v1.4.6、UI 设计-v1.4.6、前端架构设计-v1.4.6、非功能设计说明-v1.4.6、部署架构草案-v1.4.6、设计评审记录-v1.4.6 |
| 带入 Step 3 的必办项（设计评审记录 §9 / Stage2 审计 §7） | ①阶段 6.0 三项前置核实；②路径级归属矩阵脚本生成；③`module.switch` 留痕失败口径定案；④迁移按域分批 + 引用检索存证 —— 四项均已在本次闭环（见 §3.5/§9） |

### 1.2 范围边界声明

- 本仓 Step 3 完成范围：**Phase 1~5（BL-146-01~15）+ BL-146-19 本仓侧**。
- **Phase 6 跨仓部分（BL-146-16/17/18/20）挂起**：D-6 四仓 `request_id` 接线与 JSONL 结构化需在 DPS / OpenLLM / OpenMemory / OpenRAG 四仓分别评审与发布（单版本规划风险 12，跨仓排期不可控）；本仓已就绪的前置件为 `RepoLogAdapter`（JSONL 优先/纯文本回退 + svc↔module 映射 + 脱敏）与前端 `repo_log` 数据源选项。**不得以本仓回归替代跨仓验收**（AC-146-16-1/20-1 需四仓就绪后执行）。

## 2. 任务拆解与追溯（3.1 / 3.2）

| 轨道 | 子任务 | 对应 TD | 对应 BL |
|------|--------|---------|---------|
| 整体 | 入场确认、任务拆解、TD-ID 矩阵、Subtask CheckList、版本控制记录 | TD-146-01~20 | — |
| 后端 ⚙️ | 日志模块骨架与分层（Router/Service/Derivation/Repository/Schemas） | TD-146-01/02/03 | BL-146-01/02 |
| 后端 ⚙️ | 四适配器（`l1_file` / `audit_db` / `test_record` / `repo_log`） | TD-146-04/05/06/13 | BL-146-01/04/05/07/19 |
| 后端 ⚙️ | 三端点 `search` / `facets`（+`presets`）/ `export` | TD-146-07/08/09 | BL-146-02/03/04/06 |
| 后端 ⚙️ | 权限与脱敏（`log:read` 种子 + 路径三重校验 + 服务端脱敏） | TD-146-10 | BL-146-07 |
| 后端 ⚙️ | 模块开关写路径（`PATCH /api/v1/modules/{id}` + 留痕 + 持久化） | TD-146-15 | BL-146-15 |
| 前端 🎨 | 日志中心页 + `logs.ts` + `/system/audit` 收口 | TD-146-02/11 | BL-146-08/09 |
| 前端 🎨 | 顶层三分 + 平台四域导航 + 权限过滤 | TD-146-17 | BL-146-10/11 |
| 前端 🎨 | 页面迁移（22 项）+ 模块瘦身 + `Forbidden` 页 | TD-146-12/17 | BL-146-12/13 |
| 前端 🎨 | 旧路径重定向（32 条）+ 权限三处一致 | TD-146-14 | BL-146-14 |
| 前端 🎨 | 归属矩阵脚本化生成（禁人工转写） | TD-146-16 | BL-146-11 |
| 前端 🎨 | 模块开关管理页 + API 层 | TD-146-15 | BL-146-15 |

## 3. 实现内容（3.3）

### 3.1 后端轨道（AD-OpenBase-Dev）

| 文件 | 变更 | 说明 |
|------|------|------|
| `openbase/modules/logs/__init__.py` | 新建 | 导出 `router`；`__version__ = "1.0.0"`（AD-146-04 修复） |
| `openbase/modules/logs/schemas.py` | 新建 | `LogEntry`（18 字段）+ `LogSource/LogModule/LogOperation/LogResult` 枚举 + `LogQueryParams`/`LogSearchParams`/`LogExportParams` |
| `openbase/modules/logs/derivation.py` | 新建 | 分类派生单点实现（`derive_module_from_path`/`derive_operation`/`derive_result_from_status`/`derive_result_from_test`）+ `REPO_LOG_SVC_TO_MODULE` 映射 + `svc_dir_to_module`/`module_to_svc_dir` |
| `openbase/modules/logs/repository.py` | 新建 | Repository 层：`BaseRepository`（时间窗/过滤/聚合/切片）+ `L1FileAdapter` + `AuditDbAdapter` + `TestRecordAdapter` + `RepoLogAdapter` + `ADAPTERS` 注册表 + `_mask_props` 脱敏 |
| `openbase/modules/logs/service.py` | 新建 | `search`/`facets`/`export`/`build_facets_presets`；导出契约：`EXPORT_ROW_LIMIT=10000`、`CSV_BOM`、`export_filename()`（`logs-{source}-{YYYYMMDD-HHMMSS}.{ext}`）、`export_filter_summary()`（不含 `q`）、`record_export_audit()`（`action=log.export`，运行时失败降级 WARN） |
| `openbase/modules/logs/router.py` | 新建 | 4 端点（`search`/`facets`/`facets/presets`/`export`），全部 `Depends(require_permission("log:read"))`；查询参数改为 `Annotated[LogSearchParams, Query()]`（AD-146-02 修复） |
| `openbase/modules/frontend/__init__.py` | 修改 | `PATCH /api/v1/modules/{module_id}`：`module:manage` 门禁 + 状态枚举白名单（非法 422）+ 幂等 `no_change`；**先留痕后变更**，留痕失败 fail-closed（`BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE` / 503）；读取优先 DB、回退出厂值；`effective=next_login` |
| `openbase/modules/frontend/repository.py` | 新建 | `ModuleStatusRepository`：`dynamic_modules` 表参数化读写（幂等 upsert） |
| `openbase/core/db/init.py` | 修改 | 幂等种子新增 `log:read`、`module:manage` 并授 `org_admin`（user/viewer 不授） |
| `openbase/core/errors/codes.py` | 修改 | 新增 `BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE`（503）、`PARAM_EXPORT_LIMIT_EXCEEDED`（`PARAM_400`/400）、`BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE`（503） |
| `openbase/core/models/__init__.py` | 修改 | 导出 `DynamicModule`（既有模型，本次接入使用） |
| `openbase/settings.py`、`demo_app.py`、`openbase/__init__.py` | 修改 | 注册并挂载 `logs` 模块 |

### 3.2 前端轨道（FD-OpenBase-Dev）

| 文件/目录 | 变更 | 说明 |
|-----------|------|------|
| `src/core/api/logs.ts` | 新建（142 行） | `LogEntry` 类型 + 4 数据源（含 `repo_log`）+ `LOG_SOURCE_OPTIONS` + 4 维分类常量 + `logsApi`（search/facets/export） |
| `src/core/api/modules.ts` | 新建（50 行） | 模块列表/启停（`PATCH /modules/{id}`，`effective=next_login` 类型） |
| `src/core/router/legacyRedirects.ts` | 新建（60 行） | 32 条旧路径 → 新路径映射（函数式 redirect，显式回填 `query`/`hash`） |
| `src/core/router/index.ts` | 修改（192 行） | 静态路由装配 `platformRoutes`/`personalRoutes`/`legacyRedirectRoutes`；`moduleRouteLoaders` 移除 `gateway`；守卫无权限 → `/forbidden` |
| `src/core/layouts/AppLayout.vue` | 修改（253 行） | 顶层三分（仪表盘 / 业务模块 / 平台管理）+ 平台四域二级分组（身份与权限 / 平台配置与密钥 / 可观测与审计 / 开发者资源）+ 按权限码裁剪；`businessModules` 过滤 `gateway` |
| `src/pages/platform/routes.ts` | 新建（62 行） | 26 条平台路由（identity 7 / config 3 / observability 13 / developers 3），`meta.permission` 齐备 |
| `src/pages/personal/routes.ts` | 新建（10 行） | `/personal/settings` |
| `src/pages/Forbidden.vue` | 新建（30 行） | 403 落地页（携带 `from` 回跳） |
| `src/pages/platform/observability/LogsView.vue` | 新建（565 行） | 日志中心页：检索栏（数据源/关键字/时间窗/导出）+ 分类导航（四维计数）+ 表格（服务端分页 + `truncated` 提示）+ 详情抽屉 + 三态 |
| `src/pages/platform/config/ModuleSwitchView.vue` | 新建（110 行） | 模块列表 + 启停开关（提示「下次登录/刷新生效，不热生效（ADR-146-07）」） |
| `src/pages/platform/**`（identity 7 / config 2 / observability 9 / developers 3） | 迁移 | 由 `src/modules/{openllm,memory,knowledge,gateway,portrait}/pages/**` 与 `src/pages/*` 迁入（22 项重命名） |
| `src/modules/{openllm,knowledge,memory,gateway}/index.ts` | 修改 | 模块瘦身：`openllm` 由 4 板块收敛为 3 板块（删 16 条系统性路由）；`knowledge` 删 `users`/`settings`；`memory` 删 `admin`/`api-gateway`/`monitor`；`gateway` 组件指向平台域 |
| `src/modules/openllm/pages/AuditLogsView.vue` | 删除 | 存量 mock 审计页收口（BL-146-09） |
| `scripts/gen_ownership_matrix.mjs` | 重写（477 行） | 路由对象级解析（消除吞首条缺陷）+ 以 `legacyRedirects.ts` 为唯一事实源 + 内置双向自校验（差异非 0 退出码 1） |
| `doc/design/OpenBase-路径归属矩阵-v1.4.6.md` | 重新生成（135 行） | 106 路由 / 需重定向 32 / 未登记 0 / 与 legacy 差异 0 |

### 3.3 测试增量

| 文件 | 变更 | 用例数 |
|------|------|:------:|
| `tests/test_logs_endpoints_api.py` | 新建 | 17（search 4 / facets 2 / presets 1 / export 4 / 红线 6） |
| `tests/test_logs_service.py` | 修改（238→272 行） | 导出载荷与上限分支断言收紧 |
| `tests/test_logs_derivation.py` | 修改 | 派生规则 + 路径→模块（含 ruff 规范修复） |
| `tests/test_log_reserved_keys.py` | 既有 | 保留键防泄漏 |
| `tests/test_modules_switch_api.py` | 重写（306 行） | 留痕 fail-closed、落库/回退/重启语义、幂等与 422 |
| `tests/test_db_init.py` | 修改（141→238 行） | +2：权限种子存在性与 `org_admin` 授权断言（含 user/viewer 不持有） |
| `openbase-ui/tests/platform-ia.spec.ts` | 新建（129 行） | 10（路由/权限/旧路径重定向/query-hash 保留/无重复 from） |
| `openbase-ui/tests/isolation-presentation.spec.ts` | 修改（392→414 行） | `afterEach` 卸载修复跨用例 DOM 残留（FE-146-02） |
| `openbase-ui/tests/router-nav.spec.ts` | 修改 | 适配新 IA 的三层菜单断言 |

## 4. 静态质量检查（3.4）

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 后端语法/Lint | `python -m ruff check openbase tests` | ✅ `All checks passed!`（修复前 `Found 6 errors`） |
| 前端类型检查 | `npx vue-tsc --noEmit` | ✅ 退出码 0（0 错误） |
| 前端 Lint | `npx eslint .` | ✅ 退出码 0（0 问题） |
| 前端构建 | `npm run build` | ✅ 构建成功（`openbase-ui/dist` 产物生成） |
| 可观测性合规 | 结构化日志 + `request_id` 贯穿（导出留痕带本次 `request_id`，实测 `X-Request-Id` 与留痕一致）；禁止 `print` | ✅ |
| 编码约定审查（分层/错误码/日志/命名） | Router→Service→Repository 未跨层；错误统一 `BaseError(ErrorCode.*)`（`AUTH_403`/`PARAM_400`/`BIZ_*_UNAVAILABLE`）；命名 snake_case/PascalCase | ✅ |
| 技术债务增长率 | 新增 TODO：**0**（阈值 ≤5）；新增高复杂度函数：**0**（阈值 ≤3）；代码重复率增量：**0**（阈值 ≤2%） | ✅ 阈值内（后端/前端均无新增 TODO 标记；生成器重写后消除了与 `legacyRedirects.ts` 的重复维护） |
| 安全编码检查（OWASP 视角） | 路径穿越三重校验（文件名白名单）；SQL 全程参数化；无 `SELECT *`；日志脱敏（`mask_sensitive`/`_mask_props`）；检索关键字不落盘；无令牌 401 / 无权限 403 红线用例 | ✅ 无 P0/P1 |

## 5. 实际运行验证（3.5）

### 5.1 L1 构建验证

| 端 | 命令 | 证据 |
|----|------|------|
| 后端 | `python -m ruff check openbase tests` | `All checks passed!` |
| 前端 | `npx vue-tsc --noEmit` + `npm run build` | 类型 0 错误；`openbase-ui/dist` 产物于 2026-09-15 14:47 生成（新鲜） |

### 5.2 L2 启动验证

| 服务 | 端口 | 证据 |
|------|:----:|------|
| OpenBase（`openbase.demo_app:app`，含 `logs` 模块） | 8011 | `python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8011` 启动成功；`GET /health` → **200** `{"status":"ok"}` |
| 前端（构建产物） | — | 由 `npm run build` 产物验证（未做浏览器启动，属测试阶段 E2E 范围） |

### 5.3 L3 冒烟测试（核心用例）

| # | 用例 | 输入 | 真实输出 | 结论 |
|:-:|------|------|----------|:----:|
| 1 | 健康检查 | `GET /health` | `200 {"status":"ok"}` | ✅ |
| 2 | 日志查询权限红线 | `GET /api/v1/logs/search?source=l1_file`（无令牌） | `401` | ✅ |
| 3 | 模块列表权限红线 | `GET /api/v1/modules`（无令牌） | `401` | ✅ |
| 4 | 查询参数接线（AD-146-02 修复运行期确认） | `GET /openapi.json` | `/api/v1/logs/search` 注册 query 参数 **13** 个（`source,module,operation,result,operator,q,...`）；`/api/v1/logs/export` **12** 个 | ✅ |
| 5 | 导出契约（HTTP 层） | `GET /api/v1/logs/export?source=l1_file`（TestClient + 临时 L1 数据） | `200`；`content-type: text/csv; charset=utf-8`；`content-disposition: attachment; filename="logs-l1_file-20260915-211240.csv"`；首 4 字节 `b'\xef\xbb\xbft'`；表头为 §2 18 字段原名原序；留痕 1 行 `action=log.export` | ✅ |

> 说明：用例 5 与导出的超限（10005 → `400 PARAM_400 {matched:10005,limit:10000}`）、留痕通道关闭（`503 BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE`）等取证据来自 `tests/test_logs_endpoints_api.py` 的运行时输出，逐条已记录于《代码逻辑审查记录-v1.4.6》§3/§5。

### 5.4 前端运行验证（L1/L2/L3 适配）

| 层 | 证据 |
|----|------|
| L1 构建 | `vue-tsc` 0 错误 + `vite build` 成功 |
| L2 启动 | 构建产物可生成（本地 dev/preview 启动归测试阶段 E2E 范围） |
| L3 冒烟 | `vitest run` 14 文件 / 157 用例全通过；`isolation-presentation`（20）/`router-nav`（16）/`platform-ia`（10）覆盖路由可达、菜单权限、旧路径重定向 |

## 6. 开发自测（3.6）

| 端 | 命令 | 结果 |
|----|------|------|
| 后端全量（排除阻塞用例文件） | `python -m pytest tests --ignore=tests/test_s7_t6_gate.py` | `4 failed, 926 passed, 4 skipped in 260.54s`（4 项为 asyncpg 环境性失败，见 §9.2） |
| 后端日志/开关聚焦 | `pytest tests/test_logs_*.py tests/test_modules_switch_api.py tests/test_db_init.py tests/test_audit_db_persist.py` | `104 passed` |
| 后端跨套件回归 | 11 文件（审计队列/开关/端点矩阵/测试记录） | `183 passed` |
| 前端单测 | `npx vitest run`（并发 / 串行 / 4 进程压力） | `14 passed (14) / 157 passed (157)` ×3 |
| 归属矩阵自校验 | `node openbase-ui/scripts/gen_ownership_matrix.mjs` | 退出码 0；`未登记=0`、差异 `0` |

## 7. 代码逻辑审查（3.7）

| 项 | 结论 |
|----|------|
| 审查记录 | 《OpenBase-代码逻辑审查记录-v1.4.6》（14 维度） |
| 发现问题 | **2 × P0 + 8 × P1**（AD-146-01~08、FE-146-01/02） |
| 闭环情况 | **10/10 全部在本阶段闭环**，未闭环 P0/P1 = 0 |
| 审查结论 | **通过**（含 2 项已记录设计偏差 + 10 项待评审口径，见审查记录 §4/§8） |

### 7.1 联调联审（3.7c）

| 条件 | 结果 |
|------|------|
| 激活轨道 | 后端 ⚙️ + 前端 🎨（≥2 轨）→ 执行三端贯通与 API 契约一致性验证 |
| API 契约一致性 | ✅ 路径/方法/参数/响应/错误码前后端一致：`/api/v1/logs/search|facets|export`（前端 `logs.ts` ↔ 后端 `router.py`）；`/api/v1/modules`、`PATCH /api/v1/modules/{id}`（`modules.ts` ↔ `frontend/__init__.py`）；错误码 `AUTH_403`/`PARAM_400`/`BIZ_*_UNAVAILABLE` 前后端一致；`LogSource` 4 值与后端 `ADAPTERS` 4 键一致；`LogEntry` 18 字段与 CSV 表头同序 |
| 阻塞问题 | 无 P0/P1 阻塞 |

## 8. DevLogReport 变更一致性自检（3.9b）

| 自检项 | 结果 |
|--------|------|
| 文件头版本号 ↔ 修订历史底部版本号 | ✅ 一致（v1.0.0 / v1.0.0） |
| 新创建文件路径与命名规范匹配 | ✅ 命名遵循 `OpenBase-{文档名}-v{版本号}.md`；代码文件 snake_case / PascalCase |
| 产出物存在性（LS/Glob 实测） | ✅ 见 §10 |
| 本报告与追溯矩阵/审查记录交叉引用一致 | ✅ |
| 基线提交（commit） | ⚠️ **待人工执行**：本执行环境的 `git` 进程对 `.git/objects/**` 写入被系统拒绝（实测 `git hash-object -w`、`git add` 均报 `unable to write file .git/objects/...: Permission denied`，而同一用户经 PowerShell 直接写入该目录成功），因此本阶段全部变更**已落工作区但未提交**。待在工作环境执行 §8.1 命令完成基线提交（提交后需回填本行为 ✅ 并同步交付物清单） |

### 8.1 待执行的基线提交命令（人工）

```powershell
cd 'd:\Trae CN\myproject\Dev\OpenBase'
git add -A
git commit -m "feat(v1.4.6): 日志中心（R-382）+ 统一前端 IA 重构（R-383）Step 3 开发闭环" -m "后端：logs 模块 4 端点 + 4 适配器 + 派生规则 + 权限脱敏；模块开关写端点落 dynamic_modules + 留痕 fail-closed。前端：顶层三分 + 平台四域 + 22 页迁移 + 32 条旧路径重定向 + 日志中心页 + 模块开关页。修复：.gitignore 误命中致 logs 模块未入库（P0）、日志端点参数被解析为 Body（P0）、导出 4 项契约漂移、归属矩阵生成器吞首条路由、前端单测 DOM 残留（P1）。测试：后端 926 passed / 前端 157 passed。refs TD-146-01..20"
```

> 提交后请核对：`openbase/modules/logs/**`（6 文件）是否已入库、`doc/design/OpenBase-路径归属矩阵-v1.4.6.md` 与 `doc/development/*v1.4.6*` 是否随提交进入基线。

## 9. 问题修复与复审（3.8）与技术债务

### 9.1 本阶段新增/偿还债务

| 债务 ID | 分类 | 级别 | 内容 | 处置 |
|---------|------|:----:|------|------|
| TD-新增-012 | 架构/交付债务 | P1 | `.gitignore` 的 `logs/` 规则误命中 `openbase/modules/logs/`，导致日志中心后端实现长期未入库 | **本版本偿还**（AD-146-01） |
| TD-新增-013 | 测试债务 | P2 | `tests/test_s7_t6_gate.py` module 级 fixture 调用 external subprocess 干跑门禁脚本，导致全量回归阻塞（16 用例未计入统计） | 登记，Step 4 处置（RS-146-03） |
| TD-新增-014 | 健壮性债务 | P2 | `L1FileAdapter.fetch` 对 `json.loads` 无容错，粘连行抛 `JSONDecodeError` → 500 | 登记，后续版本偿还（RS-146-05） |
| TD-新增-015 | 契约一致性债务 | P2 | 导出契约 10 项细节口径未定（`<ts>` 格式/时区、`matched` 口径、失败路径是否留痕、`PARAM_400` vs `PARAM_INVALID` 并存等） | 登记，Step 4 评审裁定后回写设计文档（RS-146-01） |
| TD-新增-016 | 架构一致性债务 | P2 | 后端 `gateway` 仍在 `AVAILABLE_MODULES`/`DEFAULT_MODULES` 注册，前端已不装载为业务模块 | 登记，Step 4 明确口径（RS-146-04） |

> 归集动作：上述 P1/P2 债务已按「风险归集门禁」写入 `doc/version/global/OpenBase-技术债务总表.md`（版本升位）。

### 9.2 环境性失败说明（非业务缺陷）

`pytest` 全量中 `tests/test_tenant_admin.py`（2）与 `tests/test_users_admin.py`（2）共 4 例失败，错误为 `asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation`；**隔离复跑 10/10 全部通过**（`python -m pytest tests/test_tenant_admin.py tests/test_users_admin.py` → `10 passed in 10.22s`），且与本次改动无关（改动前基线同为这 4 例）。归因为沙箱真实 PostgreSQL 连接不稳定，与《OpenBase-存量测试对齐任务清单》§7.3 同类，移交 Step 4 在稳定环境重跑登记。

## 10. 产出物存在性验证（3.15 门禁）

| 核对项 | 路径 | 实测 | 判定 |
|--------|------|------|:----:|
| 追溯矩阵 | `doc/development/OpenBase-设计开发追溯矩阵-v1.4.6.md` | 存在且非空 | ✅ |
| 代码逻辑审查记录 | `doc/development/OpenBase-代码逻辑审查记录-v1.4.6.md` | 存在且非空 | ✅ |
| DevLogReport | `doc/development/OpenBase-DevLogReport-v1.4.6.md` | 本文件 | ✅ |
| 开发审计移交材料 | `doc/development/OpenBase-开发审计移交材料-v1.4.6.md` | 存在且非空 | ✅ |
| 后端源码 | `openbase/modules/logs/{__init__,router,service,repository,derivation,schemas}.py` | 6/6 存在（10/79/301/579/114/55 行） | ✅ |
| 后端源码（模块开关） | `openbase/modules/frontend/{__init__,repository}.py` | 2/2 存在 | ✅ |
| 前端页面 | `openbase-ui/src/pages/platform/**`（22 页）+ `personal/routes.ts` + `Forbidden.vue` | 存在且非空（LogsView 565 行、ModuleSwitchView 110 行） | ✅ |
| 归属矩阵产物 | `doc/design/OpenBase-路径归属矩阵-v1.4.6.md` | 135 行（脚本生成，未登记 0） | ✅ |
| 阶段审计报告 | `doc/audit/review/OpenBase-阶段审计报告-Stage3-v1.4.6.md` | 存在且非空 | ✅ |

## 11. 测试移交说明（Step 4 输入）

| 项 | 内容 |
|----|------|
| 测试环境 | 后端 `python -m uvicorn openbase.demo_app:app --port 8011`（真实 PostgreSQL/Redis 建议就绪，避免 §9.2 环境性失败）；前端 `npm run build` + 本地预览 |
| 启动命令 | 后端 `python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000`；前端 `npm run dev`（或部署 `dist`） |
| 测试数据 | 日志中心：L1 文件分片（`OPENBASE_LOG_DIR` 可注入临时目录）、`audit_logs`、测试记录三源；模块开关：`dynamic_modules` 表（初始化链 `create_all` 自动建表） |
| 建议回归范围 | ①日志中心主链路（登录 → `/system/logs` 重定向 → 检索/分类/分页/详情/导出）；②导出契约（AC-146-06-1~4）；③旧路径重定向 32 条无 404；④菜单权限与 `/forbidden`；⑤模块开关（含留痕失败 fail-closed 与重启保持）；⑥前端 157 用例 + E2E key-pages |
| 已知风险 | RS-146-01 导出待评审口径；RS-146-02 asyncpg 环境性失败；RS-146-03 `test_s7_t6_gate.py` 阻塞；RS-146-04 gateway 注册口径；RS-146-05 L1 解析容错 |
| 待评审口径 | 审查记录 §8 RS-146-01 的 10 项（涉及 API 契约细节，建议 Step 4 入场前裁定并回写设计文档） |
| 跨仓依赖 | BL-146-16/17/18/20 需四仓就绪后单独验收（AC-146-16-1/20-1） |

## 12. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-15 | AD-OpenBase-Dev / FD-OpenBase-Dev | 初始版本：v1.4.6 Step 3 编码记录。范围 BL-146-01~15 + BL-146-19 本仓侧（跨仓 4 项挂起）；实现后端 11 文件 + 前端 30 文件 + 测试 9 文件；静态质量（ruff/vue-tsc/eslint/build）全通过；实际运行验证 L1/L2/L3 通过；自测后端 926 passed、前端 157 passed；逻辑审查 2 P0 + 8 P1 全部闭环；新增债务 5 项（TD-新增-012~016）已归集；产出物存在性 9/9 通过 |

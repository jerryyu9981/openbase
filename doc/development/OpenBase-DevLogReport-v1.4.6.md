# OpenBase DevLogReport - v1.4.6

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.6 |
| 文档版本 | v1.4.0 |
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
| 基线提交（commit） | ✅ **已完成**：`db5682b`（父提交 `43586d5`），266 files changed / +25,497 / −440；`git fsck` 无错误、工作区 `git status` 干净、`openbase/modules/logs/**` 6 文件已入库。提交方式见 §8.1（含环境限制绕行说明） |

### 8.1 基线提交记录（含环境限制绕行）

本执行环境中 `git` 进程对 `<repo>/.git/objects/**` 的写入被系统拒绝（`git hash-object -w` / `git add` 均报 `unable to write file .git/objects/...: Permission denied`，而同一用户经 PowerShell 直接写入该目录成功；在仓库外新建仓库执行同样的 git 写对象操作则正常）。绕行方式（未改动仓库配置、未跳过 hooks）：

```powershell
$repo = 'd:\Trae CN\myproject\Dev\OpenBase'
$objs = '<可写临时目录>\objs-new'          # 新对象先落到仓库外可写目录
$env:GIT_OBJECT_DIRECTORY = $objs
$env:GIT_ALTERNATE_OBJECT_DIRECTORIES = ($repo -replace '\\','/') + '/.git/objects'   # 既有历史仍从原对象库读
git add -A
git commit -m '...'                        # 见提交信息（refs TD-146-01..20）
# 提交后把新对象归位到真实对象库（PowerShell 写入不受该限制）
Copy-Item -Path "$objs\*" -Destination "$repo\.git\objects\" -Recurse -Force
```

**验证结果**：`git log --oneline -n 3` → `db5682b`（HEAD）→ `43586d5`（父）；`git cat-file -t HEAD` → `commit`；`git fsck` 仅剩历史 dangling 对象（无错误）；`git status --porcelain` 空；`git ls-files openbase/modules/logs/*` 6/6；`git ls-files node_modules/*` = 0（已随提交将 Vitest 缓存移出跟踪，并在 `.gitignore` 增补 `node_modules/`、`.vite/`）。

> 提交后核对：`openbase/modules/logs/**`（6 文件）✅ 已入库；`doc/design/OpenBase-路径归属矩阵-v1.4.6.md` 与 `doc/development/*v1.4.6*` ✅ 随提交进入基线。

## 9. 问题修复与复审（3.8）与技术债务

### 9.1 本阶段新增/偿还债务

| 债务 ID | 分类 | 级别 | 内容 | 处置 |
|---------|------|:----:|------|------|
| TD-新增-013 | 架构/交付债务 | P1 | `.gitignore` 的 `logs/` 规则误命中 `openbase/modules/logs/`，导致日志中心后端实现长期未入库 | **本版本偿还**（AD-146-01） |
| TD-新增-014 | 测试债务 | P2 | `tests/test_s7_t6_gate.py` module 级 fixture 调用 external subprocess 干跑门禁脚本，导致全量回归阻塞（16 用例未计入统计） | 登记，Step 4 处置（RS-146-03） |
| TD-新增-015 | 健壮性债务 | P2 | `L1FileAdapter.fetch` 对 `json.loads` 无容错，粘连行抛 `JSONDecodeError` → 500 | 登记，后续版本偿还（RS-146-05） |
| TD-新增-016 | 契约一致性债务 | P2 | 导出契约 10 项细节口径未定（`<ts>` 格式/时区、`matched` 口径、失败路径是否留痕、`PARAM_400` vs `PARAM_INVALID` 并存等） | 登记，Step 4 评审裁定后回写设计文档（RS-146-01） |
| TD-新增-017 | 架构一致性债务 | P2 | 后端 `gateway` 仍在 `AVAILABLE_MODULES`/`DEFAULT_MODULES` 注册，前端已不装载为业务模块 | 登记，Step 4 明确口径（RS-146-04） |
| TD-新增-018 | 健壮性债务 | P1（残余面 P2） | 日志适配器行级容错覆盖不全：`RepoLogAdapter._parse_line` 无时间戳行构造 `LogEntry(ts=None)` → 校验异常穿透为 500 | **本轮回退已偿还 repo_log 路径**（§9.3）；同族缺口（`L1FileAdapter`/`test_record`/`audit_db`）登记后续版本偿还（RS-146-07） |

> 编号口径：v1.4.6 新增债务在总表中占用 **TD-新增-013~018**（TD-新增-012 已被 v1.4.4 的「OpenRAG 上游契约缺口」占用，本版本不重复使用；TD-新增-018 由 Step 4 实环境走查回退登记）。

> 归集动作：上述 P1/P2 债务已按「风险归集门禁」写入 `doc/version/global/OpenBase-技术债务总表.md`（版本升位）。

### 9.2 环境性失败说明（非业务缺陷）

`pytest` 全量中 `tests/test_tenant_admin.py`（2）与 `tests/test_users_admin.py`（2）共 4 例失败，错误为 `asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation`；**隔离复跑 10/10 全部通过**（`python -m pytest tests/test_tenant_admin.py tests/test_users_admin.py` → `10 passed in 10.22s`），且与本次改动无关（改动前基线同为这 4 例）。归因为沙箱真实 PostgreSQL 连接不稳定，与《OpenBase-存量测试对齐任务清单》§7.3 同类，移交 Step 4 在稳定环境重跑登记。

### 9.3 Step 4 走查回退修复记录（DEF-BE-146-001）

**回退触发**：Step 4 实环境人工走查发现 P1 缺陷（日志中心「四仓日志」源 500），按 `project-development-workflow` Step 4 门禁 5 回退至 Step 3 修复。回退记录见 `.devflow/state.json` → `auditResults.v1_4_6_step_4_rollback_to_step_3`。

| 项 | 内容 |
|----|------|
| 缺陷 | DEF-BE-146-001（P1）：`GET /api/v1/logs/search?source=repo_log` → HTTP 500 且响应体为空 |
| 根因 | `openbase/modules/logs/repository.py::_parse_line`：JSON 路径 `_iso(...)` 与纯文本路径 `timestamps[0] if timestamps else None` 均可能在无时间戳时得到 `None`，而 `LogEntry.ts` 为必填 `str` → `pydantic ValidationError` 未捕获 → 容器级异常穿透为 500 |
| 触发条件 | 编排器按 stdout 原样采集的四仓日志含无时间戳行（厂商横幅 `INFO:     Application startup complete.`、堆栈续行） |
| 修复 | ① 两条解析路径时间戳不可解析时 `return None`（沿用既有「坏行跳过」口径）；② 新增 `_warn_dropped`，`fetch` 统计扫描/解析数并输出丢弃汇总 WARNING（不静默降级） |

**TDD 与验证证据**：

| 验证项 | 命令 | 结果 |
|--------|------|------|
| TDD 红灯（修复前） | `pytest -k without_timestamp` | 🔴 3 例失败（`ValidationError: ts input_value=None`，与线上同一根因） |
| TDD 绿灯（修复后） | `pytest -k without_timestamp` | 🟢 3 例通过 |
| 增量面回归 | `pytest tests/test_logs_service.py tests/test_logs_endpoints_api.py tests/test_logs_derivation.py tests/test_log_reserved_keys.py tests/test_mask.py` | 🟢 **137 通过 / 0 失败** |
| 静态质量 | `python -m ruff check openbase tests` | 🟢 `All checks passed!`（0 错误） |
| 全量回归（修复后） | `pytest tests --ignore=tests/test_s7_t6_gate.py --junitxml=...` | 🟢 **953 收集 / 945 通过 / 4 环境性失败 / 4 跳过 / errors=0**（较修复前基线 950/942 **+3**，即新增用例；失败项集合不变，仍为 PG-ENV-1~4） |
| 实环境复测 | `GET /api/v1/logs/search?source=repo_log`（编排器已拉起 7 服务，OpenBase 重启加载修复） | 🟢 **HTTP 200，items=5 / total=4937**（修复前 500 + 空响应体）；日志中心页面切换「四仓日志」→ **20 行 / 共 4937 条**，无错误提示 |

**新增回归用例（3 条）**：

| 用例 | 层级 | 断言口径 |
|------|:----:|----------|
| `tests/test_logs_service.py::test_repolog_text_line_without_timestamp_skipped` | 适配器 | 无时间戳文本行跳过，仅返回可解析行（L1-硬断言） |
| `tests/test_logs_service.py::test_repolog_json_without_timestamp_skipped` | 适配器 | JSON 行缺 `ts` 且无行首时间戳时同口径跳过（L1-硬断言） |
| `tests/test_logs_endpoints_api.py::test_repo_log_dirty_lines_without_timestamp_do_not_break_source` | 端点 | 检索返回 200（不再 500/空体），`total` 与条目 `source` 正确（L1-硬断言） |

**遗留说明**：实环境复测中观察到前端 `timeout of 15000ms exceeded` 告警（`logs/facets` 响应 7.3～14.6 s，超出前端 15 s 超时），属已登记的性能项（测试报告 §4 DEF-BE-146-004），不在本次 P1 修复范围；同族行级容错缺口（`L1FileAdapter`/`test_record`/`audit_db`）登记为 RS-146-07 / TD-新增-018。

> 修复文件：`openbase/modules/logs/repository.py`（`_parse_line` ×2 处 + 新增 `_warn_dropped` + `fetch` 计数）；用例文件：`tests/test_logs_service.py`、`tests/test_logs_endpoints_api.py`。

### 9.4 第二次回退修复记录（DEF-BE-146-006 契约口径，2026-09-16）

**回退触发**：Step 4 重测发现参数校验口径与设计 §5 不一致（422 `PARAM_422` vs 400 `PARAM_400`），经**人工裁定「改实现对齐设计 400」**后回退 Step 3 修复。

| 项 | 内容 |
|----|------|
| 裁定 | 改实现对齐《API接口设计文档-v1.4.6》§5 的 400；不修改设计文档 |
| 实现变更 | ① `core/errors/codes.py`：`PARAM_VALIDATION_ERROR` 字面值 → `PARAM_400`、`ERROR_HTTP_MAP` 422 → 400、`PARAM_EXPORT_LIMIT_EXCEEDED` 退化为同值兼容别名（消除同义双码）；② `core/errors/base.py`：校验处理器状态码改由 `ERROR_HTTP_MAP` 单点解析（`detail` 数组保留——`detail[].input` 是 C-18 响应观测的脱敏输入源）；③ `modules/logs/service.py`：`_parse_datetime` 由静默返回 None 改为抛 400（`detail.field=from`/`to`），新增 `_validate_window`（`from > to` → 400，`detail.field=from/to`） |
| 破坏性变更 | 参数校验失败 **422 → 400**、字面值 `PARAM_422` → `PARAM_400`（波及 logs / test-records / services / gateway / ai-apps / modules 等端点）。回滚方式：还原 `core/errors/{codes,base}.py` |
| 影响面评估 | 前端 `core/api/error.ts` 对 400/422 同分支处理（按 `PARAM_` 前缀）→ 无破坏；7 处既有断言同步为 400；前端参考列表 `DpsApiManageView.vue` 同步 `PARAM_400` |

**验证证据**：

| 验证项 | 命令 | 结果 |
|--------|------|------|
| TDD 红灯 → 绿灯 | `pytest -k "param_validation or invalid_format or unknown_source or time_window or time_format"` | 🔴 6 → 🟢 9 |
| 关联套件 | `pytest`（9 个受影响文件） | 🟢 149 通过 / 0 失败 |
| 静态质量 | `ruff check openbase tests` | 🟢 0 错误 |
| 全量回归 | `pytest tests --ignore=tests/test_s7_t6_gate.py --junitxml=regression-param400-junit.xml` | 🟢 **959 收集 / 951 通过 / 4 环境性失败 / 4 跳过 / errors=0** |
| 实环境复测 | OpenBase 重启后逐分支实测 | 🟢 非法 source / `page=0` / `page_size=1000` / `format=xml` / `q` 超长 / `from>to` / `from=not-a-date` 全部 **400 `PARAM_400`**；`step_id=abc` 仍 200（契约不变） |

> 修复文件：`openbase/core/errors/codes.py`、`openbase/core/errors/base.py`、`openbase/modules/logs/service.py`、`openbase-ui/src/modules/portrait/pages/DpsApiManageView.vue`。

### 9.5 第三次回退修复记录（detail 结构对齐，2026-09-16）

**回退触发**：`detail` 结构裁定为「继续对齐」（见问题跟踪记录 §3.7），回退 Step 3 实施。

| 项 | 内容 |
|----|------|
| 裁定 | **继续对齐**：`detail` 由「pydantic 错误数组」改为「字段式明细数组」 |
| 核心动因 | 原实现直接回传 `exc.errors()`，将 **pydantic 内部键**（`type`/`loc`/`ctx`/`url`）固化为公开 API 契约——第三方库升级即可改变对外结构；且项目内其余错误明细本就是字段式，数组形态为唯一异类 |
| 实现变更 | `core/errors/base.py`：新增 `_validation_detail`（归一化为 `field`/`msg` + 约束键 + `allowed`）、`_parse_allowed`（解析 `ctx.expected` 候选值）、`_LOCATION_PREFIXES`（剔除位置前缀使 `field` 为纯字段名）；处理器改调 `_validation_detail(exc.errors())` |
| 保留项 | `input` 保留（C-18 响应观测的脱敏输入源，移除会破坏 `tests/test_audit_response_observe.py` 的掩码验证前提） |
| 契约影响 | 前端零影响（`ErrorPresentation.detail` 为 string，不消费后端 detail）；3 条新增契约用例锁定形态 |
| 形态说明 | 采用数组而非设计样例的单对象：多字段同时非法时单对象无法承载（建议回写设计文档 §5 备注） |

**验证证据**：

| 验证项 | 命令 | 结果 |
|--------|------|------|
| 契约用例（新增 3 条） | `pytest tests/test_logs_endpoints_api.py` | 🟢 通过（字段式明细 / 不暴露内部键 / 多字段并列 / 约束值） |
| 关联套件 | `pytest`（10 个文件） | 🟢 **170 通过 / 0 失败** |
| 静态质量 | `ruff check openbase tests` | 🟢 0 错误 |
| 全量回归 | `pytest tests --ignore=tests/test_s7_t6_gate.py --junitxml=regression-detail-junit.xml` | 🟢 **962 收集 / 954 通过 / 4 环境性失败 / 4 跳过 / errors=0** |
| 实环境复测 | OpenBase 重启后实测 | 🟢 `{"field":"source",…,"allowed":[…]}` / `{"field":"page_size",…,"max":100}` / `{"field":"page",…,"min":1}` / `{"field":"format",…,"allowed":["csv","json"]}`；无 pydantic 内部键 |

> 修复文件：`openbase/core/errors/base.py`；用例文件：`tests/test_logs_endpoints_api.py`。

### 9.6 第四次回退修复记录（DEF-BE-146-007 三个契约残留合并对齐，2026-09-16）

**回退触发**：Step 4 审计回溯发现三个 P2-3 契约一致性残留，经人工裁定**合并一轮回退 Step 3**（避免逐条回退导致审计重出成本叠加）。

| 项 | 内容 |
|----|------|
| 裁定 | ① 403 权限码：**仅对齐 v1.4.6 面**——日志/模块端点权限不足字面值统一为设计 §5 `PERM_403`；历史遗留 `AUTH_403`/`PERM_FORBIDDEN` **不改**（记技术债务 TD-新增-019），避免跨版本破坏既有客户端；② 404 双码：模块同资源 GET/PATCH 统一 `PARAM_404`；③ 路径参数：模块路由统一 `{id}` |
| 实现变更 | `core/errors/codes.py`（新增 `PERM_403` + HTTP 403 映射）；`modules/auth/rbac.py`（`require_permission` 增 `error_code` 参数，默认 `AUTH_FORBIDDEN` 保历史，日志/模块显式传 `PERM_403`——不改共享门禁默认码，避免级联影响 gateway/testing）；`modules/logs/router.py`（4 处 `log:read` → `PERM_403`）；`modules/frontend/__init__.py`（PATCH 依赖传 `PERM_403`；GET/PATCH 路径参数 `{module_id}`→`{id}`；GET 模块不存在 `BIZ_404`→`PARAM_NOT_FOUND`） |
| 测试变更 | `test_logs_endpoints_api.py::test_logs_endpoints_forbidden_without_log_read` 断言 `AUTH_FORBIDDEN`→`PERM_403`；`test_modules_switch_api.py` 增 `PERM_403` 字面值断言 + 新增 `GET 未知模块 → PARAM_404` 契约用例 |
| 契约影响 | 破坏性变更：模块端点权限不足 `AUTH_403`→`PERM_403`、模块 GET 未知 `BIZ_404`→`PARAM_404`、OpenAPI 路径参数 `module_id`→`id`；**前端零影响**（`modules.ts` 动态路径拼接 ${moduleId}，参数名变化不中断调用；`DpsApiManageView.vue` 参照表本用 `PERM_403`） |

**验证证据**：

| 验证项 | 命令 | 结果 |
|--------|------|------|
| 受影响套件 | `pytest tests/test_modules_switch_api.py tests/test_logs_endpoints_api.py` | 🟢 **56 通过 / 0 失败** |
| 静态质量 | `ruff check openbase tests` | 🟢 0 错误 |
| 全量回归 | `pytest tests --ignore=tests/test_s7_t6_gate.py --junitxml=regression-contract3-junit.xml` | 🟢 **963 收集 / 959 通过 / 4 环境性失败 / 4 跳过 / errors=0**（证据 `doc/test/evidence/v146/regression-contract3-junit.xml`；失败项集合与前三轮一致，均为 asyncpg 环境性） |

> 修复文件：`openbase/core/errors/codes.py`、`openbase/modules/auth/rbac.py`、`openbase/modules/logs/router.py`、`openbase/modules/frontend/__init__.py`；用例文件：`tests/test_logs_endpoints_api.py`、`tests/test_modules_switch_api.py`。

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
| v1.0.0 | 2026-09-15 | AD-OpenBase-Dev / FD-OpenBase-Dev | 初始版本：v1.4.6 Step 3 编码记录。范围 BL-146-01~15 + BL-146-19 本仓侧（跨仓 4 项挂起）；实现后端 11 文件 + 前端 30 文件 + 测试 9 文件；静态质量（ruff/vue-tsc/eslint/build）全通过；实际运行验证 L1/L2/L3 通过；自测后端 926 passed、前端 157 passed；逻辑审查 2 P0 + 8 P1 全部闭环；新增债务 5 项（TD-新增-013~017）已归集；产出物存在性 9/9 通过 |
| v1.0.1 | 2026-09-15 | AD-OpenBase-Dev | 基线提交闭环：新增 §8.1 提交记录（commit `db5682b`，父 `43586d5`，266 files / +25,497 / −440），记录 `.git/objects` 写入受限的环境绕行方式与验证结果（fsck 无错误、工作区干净、logs 模块 6 文件入库、Vitest 缓存移出跟踪并补 `.gitignore`）；§8 自检表「基线提交」由待办改为已完成 |
| v1.1.0 | 2026-09-16 | AD-OpenBase-Dev / AT-OpenBase-Test | Step 4 走查回退修复（DEF-BE-146-001，P1）：新增 §9.3 回退修复记录（TDD 红→绿 3 例、增量面 137 全绿、ruff 0 错误、全量回归 953/945、实环境 `repo_log` 源 200/4937 条）；§9.1 补 TD-新增-018 与 RS-146-07；编号口径更新为 TD-新增-013~018 |
| v1.2.0 | 2026-09-16 | AD-OpenBase-Dev / AT-OpenBase-Test | **第二次回退修复**（DEF-BE-146-006 契约口径，人工裁定改实现对齐设计 400）：新增 §9.4 记录（422/`PARAM_422` → 400/`PARAM_400` 统一、时间窗语义校验、破坏性变更与回滚声明、TDD 6→9、关联套件 149、全量回归 **959/951**、实环境全分支 400） |
| v1.3.0 | 2026-09-16 | AD-OpenBase-Dev | **第三次回退修复**（detail 结构裁定为「继续对齐」）：新增 §9.5 记录（`detail` 改字段式明细、剔除 pydantic 内部键、`input` 保留、3 条契约用例、关联套件 170、全量回归 **962/954**、实环境复核） |
| v1.4.0 | 2026-09-16 | AD-OpenBase-Dev | **第四次回退修复（DEF-BE-146-007 三个契约残留合并对齐）**：新增 §9.6 记录（403 → `PERM_403` 仅对齐 v1.4.6 面 + 历史遗留记 TD-新增-019、404 同资源统一 `PARAM_404`、路径参数 `{module_id}`→`{id}`；`require_permission` 增可选 `error_code` 默认 `AUTH_FORBIDDEN` 保历史、避免网关/测试门禁级联；受影响套件 56 全绿、ruff 0 错误、全量回归 **963/959**、契约3 JUnit 证据落盘） |

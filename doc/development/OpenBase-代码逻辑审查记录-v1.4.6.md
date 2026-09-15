# OpenBase 代码逻辑审查记录 - v1.4.6

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.6 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 审查人 | FD-OpenBase-Dev（前端轨）/ AD-OpenBase-Dev（后端轨）交叉审查 |
| 审查时间 | 2026-09-15 |
| 存放 | doc/development/ |

---

## 1. 基本信息

| 项 | 内容 |
|----|------|
| 审查对象 | v1.4.6 开发增量：R-382 日志中心（后端 4 端点 + 4 适配器 + 前端日志中心页）、R-383 统一前端 IA 重构（顶层三分 + 平台四域 + 页面迁移 + 旧路径重定向 + 模块开关页）、BL-146-19 本仓侧 `repo_log` 数据源 |
| 关联需求 | `doc/requirements/OpenBase-开发需求文档-v1.4.6.md`（BL-146-01~15）；`doc/requirements/OpenBase-需求追溯矩阵-v1.4.6.md`（RT-146-01~09 / AC-146-*） |
| 关联设计 | 系统架构-v1.4.6、API 接口设计-v1.4.6 §2~§5、UI 设计-v1.4.6、前端架构设计-v1.4.6、非功能设计说明-v1.4.6、设计评审记录-v1.4.6 §3（DT-146-01~20） |
| 静态质量证据 | `python -m ruff check openbase tests` → `All checks passed!`（0 错误）；`npx vue-tsc --noEmit` → 0 错误；`npx eslint .` → 0 问题 |
| 自测证据 | 后端 `pytest`：`926 passed, 4 failed, 4 skipped`（4 项为 asyncpg 环境性失败，见 §8）；前端 `vitest run`：`14 files / 157 tests passed`（串行与并发各 1 次 + 4 进程满载压力 1 次） |
| **审查结论** | **通过（含 2 项已记录偏差与 10 项待评审口径，均无 P0/P1 未闭环）** |

## 2. 审查范围

- 后端：`openbase/modules/logs/**`（6 文件）、`openbase/modules/frontend/**`（端点 + 新增 repository）、`openbase/core/db/init.py`（权限种子）、`openbase/core/errors/codes.py`、`openbase/core/models/__init__.py`、`openbase/settings.py`、`openbase/demo_app.py`、`openbase/__init__.py`。
- 前端：`openbase-ui/src/pages/platform/**`（22 页）、`src/pages/{personal,Forbidden}`、`src/core/{router,layouts,api}/*`、`src/modules/{openllm,knowledge,memory,gateway}/index.ts`、`scripts/gen_ownership_matrix.mjs`。
- 测试：后端 6 个文件（新增 1 个端到端 HTTP 套件 + 扩展 5 个）、前端 3 个文件。
- 不在本次范围：BL-146-16/17/18/20（跨仓，各仓独立评审与发布，见追溯矩阵 §1.1）。

## 3. 需求覆盖

| 需求项 | 实现位置 | 证据 | 结论 |
|--------|----------|------|:----:|
| RT-146-01 统一查询接口（三源 + 统一 `LogEntry`） | `logs/router.py`、`repository.py`（`ADAPTERS` 4 源）、`schemas.py` | `tests/test_logs_endpoints_api.py` 17 例（含分页/关键字/时间窗/模块过滤） | ✅ |
| RT-146-02 四维分类 + 计数 | `logs/derivation.py`、`service.py::facets`、`router.py::facets_logs`（+`facets/presets`） | facets 维度计数用例 | ✅ |
| RT-146-03 关键字与多条件组合 | `service.py::_build_filters`、`router.py` | `q=req-kw-1` 用例；关键字不落盘（AC-146-03-3）由导出留痕断言锁定 | ✅ |
| RT-146-04 时间窗与分页（上限 100 / `truncated`） | `service.py::_pagination`、`router.py` | 分页与时间窗用例 | ✅ |
| RT-146-05 测试三元组检索 | `repository.py::TestRecordAdapter` | 适配器单测 | ✅ |
| RT-146-06 导出（≤10000 / BOM / 脱敏 / 留痕） | `service.py`（`EXPORT_ROW_LIMIT=10000`、`CSV_BOM`、`export_filename`、`record_export_audit`） | 运行时取证：`attachment; filename="logs-l1_file-20260915-211240.csv"`、首 4 字节 `b'\xef\xbb\xbft'`、10005 条 → 400 `PARAM_400` `{matched:10005,limit:10000}`、留痕 `action=log.export` `detail={actor,source,filters,row_count,format}` 且不含检索词 | ✅ |
| RT-146-07 权限与脱敏（`log:read`） | `router.py`（4 端点 `require_permission("log:read")`）、`core/db/init.py`（种子 + org_admin 授权）、`repository.py`（路径三重校验、`_mask_props`） | 401×3 / 403（`AUTH_403`）/ 伪造令牌 401 / 敏感明文脱敏断言 | ✅ |
| RT-146-08 前端日志中心页 | `src/pages/platform/observability/LogsView.vue`（565 行）、`src/core/api/logs.ts` | `tests/platform-ia.spec.ts`（路由/权限/重定向 10 例）+ `vitest` 全绿 | ✅ |
| RT-146-09 存量 mock 页收口 | 删除 `AuditLogsView.vue`；`legacyRedirects.ts` 承接 `/system/audit` → 日志中心 | 全局检索 `AuditLogsView`/`system-audit`/`mockLogs` 在 `src` 与 `tests` 命中 0；`git status` 显示 `D` | ✅ |
| BL-146-10/11 顶层三分 + 平台四域 + 归属矩阵 | `AppLayout.vue`（三分 + 四域 `PLATFORM_LEAVES`，权限过滤）、`pages/platform/routes.ts`（26 条）、`gen_ownership_matrix.mjs` + 矩阵产物 | 矩阵输出：`路由条数=106（声明 76 + 旧路径承接 30） 需重定向=32 平台四域=26 个人域=1 业务本色=43 全局静态页=4 未登记=0`、`与 legacyRedirects.ts 条目差异=0`、退出码 0 | ✅ |
| BL-146-12/13 模块瘦身 + 目录边界治理 | `openllm/index.ts` 路由 4 板块 → 3 板块（删 16 条系统性路由）；`knowledge`/`memory`/`gateway` 同步瘦身；22 项页面迁移 | 特色页零删减核对见表 §4；迁移后 `vue-tsc`/`eslint`/`vitest` 全绿 | ✅ |
| BL-146-14 路由兼容与权限一致 | `legacyRedirects.ts`（32 条）+ `router/index.ts`（守卫 403 → `/forbidden`）+ 菜单权限过滤 | `tests/platform-ia.spec.ts`：每个旧路径均为已注册顶层路由、redirect 目标与预期一致、保留 query/hash、无重复 from | ✅ |
| BL-146-15 模块开关管理页 + 写接口 | `modules/frontend/__init__.py::switch_module`、`modules/frontend/repository.py`、`modules.ts`、`ModuleSwitchView.vue`、`core/db/init.py` | `tests/test_modules_switch_api.py` + `tests/test_db_init.py`：PATCH 幂等、非法枚举 422、留痕失败 fail-closed（503）、落库后重启保持 | ✅ |
| BL-146-19 本仓侧 `repo_log` 数据源 | `repository.py::RepoLogAdapter`、`derivation.py`（svc↔module 映射）、`logs.ts`（`LogSource` 含 `repo_log`） | 适配器单测 + `LOG_SOURCE_OPTIONS` 实测含 `repo_log` | ✅ |

**需求覆盖率**：本仓范围 P0/P1 = BL-146-01~15 + BL-146-19 本仓侧，**15/15 落地 + 1 项本仓侧落地**；跨仓 4 项（BL-146-16/17/18/20）**不在本仓审计范围**，已在追溯矩阵 §1.1 登记挂起原因与前置条件，非「未实现」。

## 4. 设计一致性

| 设计项 | 实现情况 | 偏差 | 影响 | 处理 |
|--------|----------|------|------|------|
| DT-146-11 日志中心页路径 | 落地 `src/pages/platform/observability/logs`（设计原文 `/system/logs`） | VC-013 新 IA 归位（设计评审记录已备注） | 无（旧路径 301/重定向承接，无 404） | 已记录 |
| DT-146-15 模块状态持久化 | 落 `dynamic_modules` 表（设计列为「Step 3 施工前确认」决策点） | 设计未定案 → 本次定案为「DB 优先 + 内存回退」 | 正向（消除重启回退） | 已记录，建议回写设计文档 |
| DT-146-09 导出「留痕通道被显式关闭」 | `OPENBASE_AUDIT_DB_PERSIST=0` 时 fail-closed（503） | 设计 §3.3 仅规定「留痕**失败**不阻断导出」（运行时失败已按设计降级） | 新增错误码需评审确认 | 已记录为待评审口径 6（回退成本 = 删 1 处调用） |
| DT-146-09 导出 `<ts>` 格式 | `YYYYMMDD-HHMMSS`（本地时区） | 设计仅写占位符 `<ts>`，未定义格式/时区 | 低（ASCII、无非法字符、可排序） | 已记录为待评审口径 1/2 |
| DT-146-15 模块开关后端注册身份 | 前端已排除 `gateway` 业务装载、组件指向平台域；后端仍在 `AVAILABLE_MODULES`/`DEFAULT_MODULES` 注册（提供 API 面） | 设计「gateway 归平台域」为前端归域语义 | 低（无 `/gateway` 业务路由，旧路径已重定向） | 记为 P2 观察项，建议 Step 4 明确口径 |
| GenericPage 四规则（DT-146-16） | 矩阵按「本色保留 / 复承载 / 迁移」三类标注 | 无 | 无 | — |

**框架/依赖**：无新增第三方依赖、无新架构引入、模块分层（Router → Service → Repository）未被破坏；`logs` 模块的 ADAPTERS 注册表为设计已规划的扩展点。

## 5. 问题清单

| ID | 级别 | 类型 | 位置 | 问题 | 影响 | 处理 |
|----|:----:|------|------|------|------|------|
| AD-146-01 | **P0** | 交付完整性 | `.gitignore:43` | 规则 `logs/` 未锚定根目录，命中 `openbase/modules/logs/`，导致日志中心后端 6 个源文件**从未纳入版本控制**（`git ls-files` 为空、无任何提交） | 交付物随时可能丢失，审计/移交无法取证 | ✅ 已修复：改为 `/logs/`；实测 `check-ignore` 对 `openbase/modules/logs/*` 无命中、根 `logs/` 仍忽略 |
| AD-146-02 | **P0** | API 契约/可用性 | `openbase/modules/logs/router.py` | 三端点用 `params: LogSearchParams = Depends()`，在 FastAPI 0.139 + Pydantic 2.13 下模型内 `list[...]` 被判定为 **Body** 参数：`GET /api/v1/logs/search?source=l1_file` → 500（`ValidationError: 4 validation errors`），重复查询参数完全不生效（OpenAPI 未注册为 query） | 日志中心主链路不可用 | ✅ 已修复：改 `Annotated[LogSearchParams, Query()]`（Query Parameter Models）；修复前 7 例红 → 修复后 17 例绿 |
| AD-146-03 | P1 | 静态质量 | `tests/test_logs_*.py`、`tests/test_modules_switch_api.py` | `ruff check` 6 条错误（W292×3 / I001 / UP037 / F401） | 违反 AGENTS.md「ruff 0 错误」门禁 | ✅ 已修复：`All checks passed!` |
| AD-146-04 | P1 | 模块规约 | `openbase/modules/logs/__init__.py` | 缺 `__version__` → `tests/test_grayscale.py::test_modules_init_version_present` 失败 | 模块清单与灰度校验失败 | ✅ 已修复：补 `1.0.0`（与同批模块一致） |
| AD-146-05 | P1 | 权限/安全 | `openbase/core/db/init.py` | `log:read`、`module:manage` **未登记进权限种子**，非 admin 角色经 `user→role→permission` 链永远查不到（仅靠 admin `*` 通配） | 权限无法分配，AC-146-07-1/15-1 在真实角色下不可达 | ✅ 已修复：幂等种子登记并授 `org_admin`（user/viewer 不授，与 `auth:api-keys:*` 口径一致），`tests/test_db_init.py` +2 用例 |
| AD-146-06 | P1 | 审计闭环 | `openbase/modules/frontend/__init__.py` | 原实现「先改状态、后 best-effort 留痕」：留痕失败仅 WARN、且可被 `OPENBASE_AUDIT_DB_PERSIST=0` **整体静默跳过** → 出现「状态已变 + 无留痕」不可回溯 | 违反 AC-146-15-3 强制留痕 | ✅ 已修复：改为**先留痕后变更**，留痕失败 → 状态不变 + `BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE`（503），`no_change` 仍 200 不重复留痕（Step 3 定案，见 §7） |
| AD-146-07 | P1 | 数据一致性 | `openbase/modules/frontend/__init__.py` | 模块启停状态仅存进程内存（就地改 `DEFAULT_MODULES`），重启/多 worker 即回退 | 「模块开关」语义不成立 | ✅ 已修复：落 `dynamic_modules`（幂等 upsert），DB 不可用回退内存并 WARN；实测 PATCH 后落库、模拟重启后 GET 仍为 `disabled` |
| AD-146-08 | P1 | 设计-实现漂移 | `openbase/modules/logs/service.py` | 导出 4 项不符设计 §3.3：文件名固定 `logs.csv`、CSV 无 BOM、无 10000 上限拦截、无 `log.export` 留痕 | AC-146-06-1~4 不达标 | ✅ 已修复：四项全部对齐设计原文，运行时取证见 §3 |
| FE-146-01 | P1 | 交付/门禁产物 | `openbase-ui/scripts/gen_ownership_matrix.mjs` | 提取正则把每个模块首条路由与后一条并成一次匹配 → **5/5 模块首条路由被吞**（`/openllm/models`、`/knowledge/list`、`/memory/list`、`/portrait/list`、`/gateway/services`）；矩阵与 `legacyRedirects.ts` 差异 4 条；矩阵产物早于路由改造（12:59 < 13:13~13:20）已过期 | Phase 4 门禁产物（归属矩阵，AC-146-11-2）不可信 | ✅ 已修复：重写为按路由对象逐条解析 + 以 `legacyRedirects.ts` 为唯一事实源；重生成后 `未登记=0`、差异 `0`、退出码 0 |
| FE-146-02 | P1 | 测试稳定性 | `openbase-ui/tests/isolation-presentation.spec.ts` | 用例挂载 Element Plus 组件后从不卸载，DOM 节点逐例累积（0→20→39→…→105），并发下 `S6-T3-2` 偶发 5000ms 超时 | 前端回归不可复现（虚假红灯） | ✅ 已修复：`afterEach` 统一卸载 + 清空挂载点；修复后并发/串行/4 进程压力均 157/157 绿 |

**未闭环 P0/P1**：**0 项**。

## 6. 静态质量检查证据

| 检查项 | 命令或方式 | 结果 |
|--------|-----------|------|
| 后端语法/Lint | `python -m ruff check openbase tests` | `All checks passed!`（0 错误） |
| 前端类型 | `npx vue-tsc --noEmit` | 退出码 0，输出为空 |
| 前端 Lint | `npx eslint .` | 退出码 0，0 问题 |
| 前端构建 | `npm run build`（vite build，产物 `openbase-ui/dist`） | 构建成功（提交前 24 小时内新鲜证据） |
| 符号/参数/返回值/配置一致性 | 契约字段比对：`LogEntry` 18 字段 ↔ `logs.ts` 类型 ↔ CSV 表头同序；`LogSource` 4 值 ↔ `ADAPTERS` 4 键 | 一致（导出表头实测为 §2 18 列原名原序） |
| 命名/结构一致性（维度 14） | 设计规划「新建/重命名/删除」文件操作 vs 实际 `LS/Glob` | 一致（22 迁移 + 1 删除 + 6 后端新建，偏差 2 项已在追溯矩阵 §2 登记） |

## 7. 自测证据与修复复审

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 后端全量（排除阻塞用例文件） | `python -m pytest tests --ignore=tests/test_s7_t6_gate.py` | `4 failed, 926 passed, 4 skipped`（4 项 asyncpg 环境性失败，见 §8） |
| 日志/模块开关聚焦套件 | `pytest tests/test_logs_*.py tests/test_modules_switch_api.py tests/test_db_init.py tests/test_audit_db_persist.py` | `104 passed` |
| 跨套件回归（审计队列/开关/端点矩阵） | 11 文件组合 | `183 passed` |
| 前端全量单测 | `npx vitest run`（并发 + 串行 + 压力） | `14 passed (14) / 157 passed (157)` ×3 |
| 归属矩阵自校验 | `node openbase-ui/scripts/gen_ownership_matrix.mjs` | 退出码 0；`未登记=0`、与 legacy 差异 `0` |

| 问题 ID | 修复方式 | 复审结果 |
|---------|----------|----------|
| AD-146-01 | `.gitignore` 规则改为 `/logs/` | `git check-ignore` 对 `openbase/modules/logs/*` 无输出；`git status` 已显示 `?? openbase/modules/logs/` |
| AD-146-02 | `Annotated[..., Query()]`（3 端点） | 17 例端到端 HTTP 用例由 7 红 → 全绿 |
| AD-146-03 | ruff `--fix` + 手工 | 复跑 `All checks passed!` |
| AD-146-04 | 补 `__version__` | `test_grayscale` 由红转绿 |
| AD-146-05 | 幂等种子 + 授权 | `tests/test_db_init.py` 新增 2 例由红转绿；断言 user/viewer 不得持有 |
| AD-146-06 | 先留痕后变更 + fail-closed | `test_modules_switch_api.py` 重写（原「静默 200」断言改为失败断言）全绿 |
| AD-146-07 | `dynamic_modules` 落库 | 落库 + 模拟重启保持用例全绿 |
| AD-146-08 | 文件名/BOM/上限/留痕四项 | 运行时取证（真实响应头/字节/响应体/留痕行）全部符合设计 |
| FE-146-01 | 生成器重写 + 重生成 | `未登记=0`、差异 `0`、退出码 0；5 条曾缺失首路由均在矩阵中 |
| FE-146-02 | `afterEach` 卸载 + 清空挂载点 | DOM 节点数恒为 0；三种执行方式均 157/157 |

## 8. 剩余风险（P2/P3，可带入测试阶段）

| ID | 级别 | 内容 | 影响 | 建议 |
|----|:----:|------|------|------|
| RS-146-01 | P2 | 导出 10 项待评审口径（`<ts>` 格式/时区、`matched` 口径、`detail.filters` 键集与 `q` 处理、失败路径是否留痕、「通道显式关闭」的 503 语义、`PARAM_400` vs `PARAM_INVALID` 并存、JSON 是否需 BOM、是否需 RFC 5987 等） | 契约细节歧义，可能触发前后端二次对齐 | Step 4 前由评审裁定并回写 API 设计文档（本记录 §4 已逐条登记） |
| RS-146-02 | P2 | `pytest` 4 项 asyncpg `connection was closed` 失败（`test_tenant_admin`/`test_users_admin`），隔离复跑 10/10 通过；改动前基线同为这 4 项 | 全量回归存在非确定性红灯 | 归因为沙箱真实 PostgreSQL 连接不稳（与《存量测试对齐任务清单》§7.3 同类），建议 Step 4 在稳定环境重跑并登记 |
| RS-146-03 | P2 | `tests/test_s7_t6_gate.py` 会阻塞（其 module 级 fixture 调 subprocess 干跑门禁脚本）→ 全量回归须 `--ignore` 该文件（16 用例未计入） | 全量统计不完整 | 建议 Step 4 为该用例加超时/跳过标记，或在联调窗口内执行 |
| RS-146-04 | P2 | 后端 `gateway` 仍在 `AVAILABLE_MODULES`/`DEFAULT_MODULES` 注册（前端已不装载为业务模块） | 注册表返回 gateway 但无 `/gateway` 业务路由 | Step 4 明确「保留 API 面 / 移除注册」口径 |
| RS-146-05 | P2 | `L1FileAdapter.fetch` 对 `json.loads` 无容错，粘连行会抛 `JSONDecodeError` → 500（既有缺口，非本次引入） | 单行坏数据导致整次查询失败 | 纳入技术债务，Step 4/后续版本补容错 |
| RS-146-06 | P3 | `openbase/modules/versions.json` 未含 `logs`/`frontend` 最新版本（生成口径既有行为） | 版本清单与实际 `__version__` 不联动 | 后续统一由生成脚本处理 |

## 9. 最终结论

**结论：通过（允许进入开发审计）** —— 经交叉审查：

1. 本仓范围内 BL-146-01~15 + BL-146-19 本仓侧**需求全覆盖**，追溯链 DT-146-01~20 → TD-146-01~20 → 文件齐备（见《设计开发追溯矩阵-v1.4.6》）。
2. 审查发现 **2 项 P0 + 8 项 P1 全部在本阶段闭环**（未闭环 P0/P1 = 0）；静态质量（ruff / vue-tsc / eslint / build）与开发自测（后端 926 passed / 前端 157 passed）证据齐备且新鲜。
3. 2 项设计偏差（日志中心页路径归位、导出通道关闭语义 + 新增错误码）与 10 项待评审口径**已逐条登记**，其中「日志中心页归位」由设计评审记录 VC-013 备注支撑，「模块状态持久化 / 留痕失败口径」属设计明确委派给 Step 3 的定案项（已实现并写入代码注释与测试）。
4. 跨仓 4 项（BL-146-16/17/18/20）**明确排除**在本仓审计范围，不构成掩盖。
5. 剩余风险 6 项均为 P2/P3，已归集建议（见 §8），不阻塞开发审计移交。

**移交条件**：Step 4 测试须重点覆盖 §8 的 RS-146-01（导出契约细节）与 RS-146-02（环境稳定性），并在稳定环境下补齐 `test_s7_t6_gate.py` 的 16 个门禁用例。

## 10. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-15 | FD-OpenBase-Dev / AD-OpenBase-Dev | 初始版本：14 维度审查；需求覆盖 15/15（本仓范围）；发现 2 P0 + 8 P1（全部闭环）与 6 项剩余风险；结论通过并允许进入开发审计 |

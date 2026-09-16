# OpenBase 设计开发追溯矩阵 TD-ID - v1.4.6

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.6 |
| 文档版本 | v1.0.2 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev（后端轨）/ FD-OpenBase-Dev（前端轨） |
| 创建日期 | 2026-09-15 |
| 存放 | doc/development/ |
| 设计输入 | 设计评审记录-v1.4.6 §3（DT-146-01~20）、需求追溯矩阵-v1.4.6 §2/§3（RT-146-01~09 / AC-146-*） |

---

## 1. 追溯矩阵（DT → TD → BL → 文件）

> 说明：DT-146-01~20 为 Step 2 《设计评审记录-v1.4.6》§3 登记的设计项；TD 编号与 DT 一一对应。TC 列为本版本实现落点（文件/目录以仓库真实存在为准，行数为 2026-09-15 实测）。

| DT-ID（设计项） | TD-ID（开发项） | BL-ID | 涉及文件（真实路径） | 状态 |
|----------------|-----------------|-------|----------------------|:----:|
| DT-146-01 logs 模块骨架与分层（Router/Service/Derivation/Repository/Schemas） | TD-146-01 模块落地 + 挂载 | BL-146-01 | `openbase/modules/logs/__init__.py`、`router.py`、`service.py`、`derivation.py`、`repository.py`、`schemas.py`；`openbase/settings.py`、`openbase/demo_app.py`、`openbase/__init__.py` | ✅ 完成 |
| DT-146-02 统一 `LogEntry` 契约（18 字段 × 三源映射） | TD-146-02 契约实现 + 前端类型 | BL-146-01 | `openbase/modules/logs/schemas.py`；`openbase-ui/src/core/api/logs.ts` | ✅ 完成 |
| DT-146-03 分类派生规则（module / operation / result） | TD-146-03 派生单点实现 | BL-146-02 | `openbase/modules/logs/derivation.py` | ✅ 完成（未知值落 other/unknown，不丢记录） |
| DT-146-04 `L1FileAdapter`（分片倒序 + 提前终止 + 文件名白名单） | TD-146-04 适配器实现 | BL-146-01/04/07 | `openbase/modules/logs/repository.py`（`L1FileAdapter`） | ✅ 完成 |
| DT-146-05 `AuditDbAdapter`（参数化查询 + `detail` 键提取） | TD-146-05 适配器实现 | BL-146-01/05 | `openbase/modules/logs/repository.py`（`AuditDbAdapter`） | ✅ 完成 |
| DT-146-06 `TestRecordAdapter`（复用既有服务） | TD-146-06 适配器实现 | BL-146-01/05 | `openbase/modules/logs/repository.py`（`TestRecordAdapter`） | ✅ 完成 |
| DT-146-07 `/logs/search`（筛选 + 稳定排序 + 分页 + 截断语义） | TD-146-07 端点实现 + 查询参数接线修复 | BL-146-03/04 | `openbase/modules/logs/router.py`、`service.py` | ✅ 完成（含缺陷修复 AD-146-01） |
| DT-146-08 `/logs/facets`（计数与列表同口径） | TD-146-08 端点实现（+ `facets/presets`） | BL-146-02 | `openbase/modules/logs/router.py`、`service.py` | ✅ 完成 |
| DT-146-09 `/logs/export`（流式 + 上限 + 脱敏 + `log.export` 留痕） | TD-146-09 导出契约补齐 | BL-146-06 | `openbase/modules/logs/service.py`、`router.py`；`openbase/core/errors/codes.py` | ✅ 完成（文件名/BOM/10000 上限/留痕四项漂移闭环） |
| DT-146-10 权限与脱敏（`log:read` + 跨租户 + 路径三重校验 + 检索词不留痕） | TD-146-10 权限种子 + 脱敏 + 校验 | BL-146-07 | `openbase/modules/logs/router.py`、`repository.py`；`openbase/core/db/init.py`；`openbase/core/mask.py` | ✅ 完成（权限码已入种子并授 org_admin） |
| DT-146-11 前端日志中心页 + `core/api/logs.ts` + `/system/audit` 重定向 | TD-146-11 页面 + API 层 + 下线重定向 | BL-146-08/09 | `openbase-ui/src/pages/platform/observability/LogsView.vue`、`src/core/api/logs.ts`、`src/core/router/legacyRedirects.ts`；删除 `src/modules/openllm/pages/AuditLogsView.vue` | ✅ 完成（模板静态扫描 mockLogs 命中 0） |
| DT-146-12 目录边界治理：平台/全局页迁出 `modules/*/pages/` | TD-146-12 目录迁移 + 引用修复 | BL-146-13 | `openbase-ui/src/pages/platform/{identity,config,observability,developers}/**`、`src/pages/personal/**`（22 项迁移 + 1 项删除） | ✅ 完成 |
| DT-146-13 `RepoLogAdapter`（第四类源：JSONL 优先/纯文本回退 + svc↔module 映射 + 脱敏） | TD-146-13 适配器 + 前端数据源 | BL-146-19 | `openbase/modules/logs/repository.py`（`RepoLogAdapter`）、`derivation.py`；`openbase-ui/src/core/api/logs.ts` | ✅ 完成（**本仓侧**；四仓实际产出待 BL-146-16/17 就绪）；**2026-09-16 返工**：`_parse_line` 行级容错（无时间戳行跳过）+ `fetch` 丢弃汇总告警（DEF-BE-146-001，P1，见 DevLogReport §9.3） |
| DT-146-14 重定向映射表 + 权限三处一致（`/platform/**` 前缀；旧路径禁 404） | TD-146-14 重定向表 + 菜单/路由权限一致 | BL-146-14 | `openbase-ui/src/core/router/legacyRedirects.ts`、`src/core/router/index.ts`、`src/pages/platform/routes.ts`、`src/core/layouts/AppLayout.vue`、`tests/platform-ia.spec.ts` | ✅ 完成（32 条旧路径，矩阵差异 0） |
| DT-146-15 模块状态写路径：`PATCH /api/v1/modules/{id}` + `module:manage` + 留痕 + 只读降级 | TD-146-15 写端点 + 持久化 + 定案口径 | BL-146-15 | `openbase/modules/frontend/__init__.py`、`modules/frontend/repository.py`、`openbase/core/errors/codes.py`、`openbase/core/models/__init__.py`、`openbase/core/db/init.py`；`openbase-ui/src/core/api/modules.ts`、`src/pages/platform/config/ModuleSwitchView.vue` | ✅ 完成（状态落 `dynamic_modules`；留痕失败 fail-closed 定案） |
| DT-146-16 路径级归属矩阵 + GenericPage 四规则 | TD-146-16 矩阵脚本化生成 + 规则落地 | BL-146-11 | `openbase-ui/scripts/gen_ownership_matrix.mjs`；`doc/design/OpenBase-路径归属矩阵-v1.4.6.md`（脚本产物） | ✅ 完成（106 路由 / 未登记 0 / 差异 0） |
| DT-146-17 前端目标路由与顶层三分菜单 | TD-146-17 顶层三分 + 平台四域导航 | BL-146-10/11 | `openbase-ui/src/core/layouts/AppLayout.vue`、`src/pages/platform/routes.ts`、`src/pages/personal/routes.ts`、`src/modules/{openllm,knowledge,memory,gateway}/index.ts`、`src/pages/Forbidden.vue`、`tests/platform-ia.spec.ts`、`tests/router-nav.spec.ts` | ✅ 完成 |
| DT-146-18 非功能增补（性能/安全/可观测口径） | TD-146-18 实现侧对齐 | BL-146-10~15 | 实现侧落点：导出上限 10000（`service.EXPORT_ROW_LIMIT`）、路径三重校验、脱敏、`request_id` 贯穿 | ✅ 完成（设计文档侧无新增实现件） |
| DT-146-19 部署增补 | TD-146-19 部署侧对齐 | BL-146-10~15 | 本版本无新增部署件（前端为构建产物替换，后端无新增迁移脚本） | ✅ 完成（无实现项，登记为「不适用」） |
| DT-146-20 原型产出 | TD-146-20 原型落盘 | BL-146-08/10/11 | `doc/design/prototype/logs.html`、`doc/design/prototype/ia-overview.html`、`doc/design/prototype/index.html` | ✅ 完成（Step 2 产出，Step 3 回溯对照） |

### 1.1 版本范围内挂起项（跨仓，不计入本仓 Step 3）

| BL-ID | 内容 | 挂起原因 | 证据 |
|-------|------|----------|------|
| BL-146-16 | D-6 四仓 `request_id` 接线 | 跨仓改动（DPS/OpenLLM/OpenMemory/OpenRAG），各仓独立评审与发布，排期不由本仓控制（单版本规划风险 12） | 本仓无该四仓源码；本仓已提供 `repo_log` 适配器与检索口径 |
| BL-146-17 | 四仓日志结构化（JSONL） | 同上 | `RepoLogAdapter` 已按 JSONL 优先/纯文本回退实现，待四仓产出符合最小字段集的 JSONL |
| BL-146-18 | 采集按日切分与命名对齐 | 属编排器（跨仓基础设施）侧改造 | `RepoLogAdapter` 已按 `{svc}-YYYYMMDD.jsonl` 约定解析分片 |
| BL-146-20 | 端到端串联与接入验收 | 依赖 BL-146-16/17 就绪后方可执行 AC-146-16-1/20-1 | 本仓侧验收前置项（适配器 + 数据源选项）已就绪 |

> 口径：本仓 v1.4.6 Step 3 的完成范围为 **BL-146-01~15（Phase 1~5）+ BL-146-19 本仓侧**；上表 4 项属跨仓依赖，需在四仓就绪后按 Phase 6 单独施工与验收，不得以本仓回归替代（Cross-repo 边界）。

## 2. Subtask CheckList（子任务状态表）

> 比对方式：以设计文档规划的「新建/重命名/删除」文件操作 vs 实际编码完成状态，逐项实测（LS/Glob + 行数）。

| 子任务 | 设计规划文件操作 | 实际状态 | 偏差 |
|--------|------------------|:--------:|------|
| TD-146-01 模块 | 新建 `openbase/modules/logs/{__init__,router,service,derivation,repository,schemas}.py` | ✅ | 无（文件名与设计一致） |
| TD-146-01 挂载 | `settings.py`/`demo_app.py`/`openbase/__init__.py` 注册并挂载 `logs` | ✅ | 无 |
| TD-146-02 前端类型 | 新建 `openbase-ui/src/core/api/logs.ts` | ✅ | 无 |
| TD-146-04/05/06/13 适配器 | 设计规划落 `logs/repository.py`（未逐适配器拆分文件） | ✅ | 无（与设计落点一致） |
| TD-146-09 导出契约 | 补 `EXPORT_ROW_LIMIT`/BOM/文件名/留痕 | ✅ | 无 |
| TD-146-10 权限种子 | `core/db/init.py` 新增 `log:read`、`module:manage` 并授 `org_admin` | ✅ | 无 |
| TD-146-11 页面 | 新建日志中心页（设计原文 `src/pages/LogsView.vue`） | ✅ | **有**：按 VC-013 新 IA 落位为 `src/pages/platform/observability/LogsView.vue`（已由设计 DT-146-11 备注确认） |
| TD-146-11 删除 | 删除 `src/modules/openllm/pages/AuditLogsView.vue` | ✅ | 无（全局引用检索 0 残留；生成器脚本 1 处死映射键已随 TD-146-16 重写消除） |
| TD-146-12 迁移 | 平台/全局页迁出模块目录 → `src/pages/platform/**` | ✅ | 无（22 项重命名 + 1 项删除） |
| TD-146-14 重定向 | 新建 `src/core/router/legacyRedirects.ts` | ✅ | 无 |
| TD-146-15 写路径 | `PATCH /api/v1/modules/{id}` + `modules.ts` + `ModuleSwitchView.vue` | ✅ | **有（新增件）**：为实现持久化新增 `openbase/modules/frontend/repository.py`（设计未逐文件规划，属实现细节落地，已在 DevLogReport 记录） |
| TD-146-16 矩阵脚本 | 新建 `openbase-ui/scripts/gen_ownership_matrix.mjs`（禁人工转写） | ✅ | 无（重写提取逻辑，477 行） |
| TD-146-20 原型 | `doc/design/prototype/{logs.html,ia-overview.html}` | ✅ | 无 |
| 后端测试 | 新建/扩展日志与模块开关测试 | ✅ | 无（新增 `tests/test_logs_endpoints_api.py`，扩展 5 个既有文件） |
| 前端测试 | 新建 `tests/platform-ia.spec.ts`；维护 `router-nav.spec.ts` | ✅ | 无 |

**Subtask CheckList 结论**：设计规划文件操作 **全部落地**；2 项偏差均为「落位调整/实现细节新增」，已在设计评审记录与 DevLogReport 中登记，无未完成项、无静默推迟项。

## 3. 版本控制记录（分支策略 + commit 约定）

| 项 | 内容 |
|----|------|
| 分支策略 | main 直发（项目惯例，v1.4.4/v1.4.5 同） |
| commit 格式 | `type(scope): subject`，footer 引用 TD-ID（如 `refs TD-146-09`） |
| TDD 合规 | feat/fix 提交必须包含对应测试文件变更；测试先于生产代码提交 |
| 版本号联动 | 后端模块 `__version__` 与 `openbase/modules/versions.json` 口径一致 |
| 备份 | 提交前 .devflow hooks（post-push）自动备份；重要节点打标 |
| **本版本基线提交** | **`db5682b`**（父 `43586d5`，2026-09-15 21:48）：`feat(v1.4.6): 日志中心（R-382）+ 统一前端 IA 重构（R-383）Step 3 开发闭环`，footer `refs TD-146-01..20`；266 files changed / +25,497 / −440；提交后 `git fsck` 无错误、工作区干净、`openbase/modules/logs/**` 6 文件入库 |

### 3.1 本版本新增/修改文件（TD-ID 索引）

| 轨道 | 文件 | 行数（2026-09-15 实测） | 关联 TD |
|------|------|:----------------------:|---------|
| 后端 | `openbase/modules/logs/__init__.py` | 10（`__version__=1.0.0`） | TD-146-01 |
| 后端 | `openbase/modules/logs/router.py` | 79 | TD-146-07/08/09/10 |
| 后端 | `openbase/modules/logs/service.py` | 301 | TD-146-07/08/09 |
| 后端 | `openbase/modules/logs/repository.py` | 579 | TD-146-04/05/06/13 |
| 后端 | `openbase/modules/logs/derivation.py` | 114 | TD-146-03/13 |
| 后端 | `openbase/modules/logs/schemas.py` | 55 | TD-146-02 |
| 后端 | `openbase/modules/frontend/__init__.py` | 375 | TD-146-15 |
| 后端 | `openbase/modules/frontend/repository.py` | 76（新增） | TD-146-15 |
| 后端 | `openbase/core/db/init.py` | 235 | TD-146-10/15 |
| 后端 | `openbase/core/errors/codes.py` | 145 | TD-146-09/15 |
| 后端 | `openbase/core/models/__init__.py` | 65 | TD-146-15 |
| 后端 | `openbase/settings.py`、`demo_app.py`、`openbase/__init__.py` | — | TD-146-01 |
| 前端 | `src/pages/platform/**`（22 页） | 见 §1 | TD-146-11/12/17 |
| 前端 | `src/pages/personal/routes.ts`、`src/pages/Forbidden.vue` | 10 / 30 | TD-146-17 |
| 前端 | `src/core/router/legacyRedirects.ts`、`src/core/router/index.ts` | 60 / 192 | TD-146-14 |
| 前端 | `src/core/layouts/AppLayout.vue` | 253 | TD-146-17 |
| 前端 | `src/core/api/logs.ts`、`src/core/api/modules.ts` | 142 / 50 | TD-146-02/13/15 |
| 前端 | `scripts/gen_ownership_matrix.mjs` | 477 | TD-146-16 |
| 测试 | `tests/test_logs_endpoints_api.py`（新增）等 6 个后端测试文件 | 见 DevLogReport §3 | TD-146-* |
| 测试 | `openbase-ui/tests/{platform-ia,isolation-presentation,router-nav}.spec.ts` | 129 / 414 / — | TD-146-14/17 |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-15 | AD-OpenBase-Dev | 初始创建：DT-146-01~20 → TD-146-01~20 追溯矩阵（20 项全落地）、跨仓挂起项 4 项（BL-146-16/17/18/20）、Subtask CheckList（16 项核对，2 项偏差登记）、版本控制记录与文件索引 |
| v1.0.1 | 2026-09-15 | AD-OpenBase-Dev | 版本控制记录回填：新增「本版本基线提交 `db5682b`（父 `43586d5`）」行，记录提交范围 266 files / +25,497 / −440 与提交后校验（fsck 无错误、工作区干净、logs 模块 6 文件入库） |
| v1.0.2 | 2026-09-16 | AD-OpenBase-Dev | Step 4 走查返工回填：DT-146-13（`RepoLogAdapter`）行追加返工说明（`_parse_line` 行级容错 + `fetch` 丢弃汇总告警，DEF-BE-146-001 / P1）；追溯链 DT-146-13 → TD-146-13 → `repository.py` 保持不变，仅补状态与证据 |

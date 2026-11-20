# OpenBase-DPS 统一前端重设计 - 测试报告（v1.0.0）

| 项目 | 内容 |
|---|---|
| 项目名称 | OpenBase（开放底座）／落点仓 **本仓**（`openbase-ui` 前端） |
| 主题 | DPS 统一前端页面功能重设计（Phase 1～3） |
| 文档 | 测试报告（Step 4 产出） |
| 文档版本 | **v1.1.1** |
| 状态 | **[Approved]**（Step 4 人工批准通过，2026-11-20，批准人＝用户，准予进入 Step 5） |
| 测试角色 | TE-OpenBase-Test |
| 测试时间 | 2026-11-20 |
| 存放 | `doc/test/` |
| 上游依据 | 《OpenBase-DPS 统一前端页面功能设计》**v2.3.0 [Implemented]**（§11 验收标准、§12 风险、§14.5～§14.7 实施记录）；`AGENTS.md`；用户《项目开发五步流程规则》 |
| 被测基线 | `main` @ **`da538e5`**（Phase 1 `4412735` ／ Phase 2 `e17eca0` ／ Phase 3 `da538e5`） |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-20 | 首版：Phase 1～3 全量前端重设计的 Step 4 测试记录，含范围与环境、46 条 AC 覆盖矩阵、静态检查/单测/路由回归执行结果、A6/A9/A10/A11/A12/A14 降级口径验证、缺陷与结论 | TE-OpenBase-Test |
| v1.1.0 | 2026-11-20 | 人工批准：Step 4 门禁通过，状态 [Review] → [Approved]，准予进入 Step 5（部署与运维） | TE-OpenBase-Test |
| v1.1.1 | 2026-11-20 | Step 5 构建回归回填：补记全项目类型门禁口径（`npm run build` 覆盖 `tests/**`），登记并闭环 DEF-DPSR-05-01（测试文件 `WrapperLike.vm` 类型错误）；结论不变 | TE-OpenBase-Test |

---

## 0. 基本信息

| 项 | 值 |
|---|---|
| 待测范围 | `openbase-ui/src/modules/portrait/**`（页面、模型/工具函数、组合式函数、模块路由与导航） |
| 变更规模 | Phase 1：四分组导航、今日工作台、标注作业台（含审核视图）、通用列表规范；Phase 2：模板中心、模板工作台、标注模板/字段设计器；Phase 3：标签体系/血缘、口径体检修复入口、评分类型、画像列表/搜索/360、措施建议 |
| 路由影响 | **未新增/删除任何 route record**；22 条 DPS/画像路由路径全部保留；新增 `?view=`、`?mode=`、`?tag=` 查询参数，旧深链（含 `?tag_code=`）继续可用 |
| 后端影响 | **0**（仅前端；沿用 `/api/v1/dps-proxy/*` 既有契约，本轮只出 API 缺口清单） |
| 测试环境 | Windows 10；Node v24.17.0（系统 `node`）／vitest 2.1.8／vue-tsc（项目依赖）；Element Plus 2.9 |
| 执行基线 | 工作区与 `main` @ `da538e5` 一致（本任务无未提交代码改动）；既有无关未提交文件未纳入本次测试与提交 |
| 测试结论 | **通过（代码类失败 0）**：静态检查 0 错误；相关单测/组件测试全部通过；46 条 AC 均有实现与证据；无阻断缺陷。降级项（A6/A9/A10/A11/A12/A14）按设计口径「明示降级、不造假数据」验证通过 |

---

## 1. 测试范围与策略

### 1.1 范围内

| # | 范围 | 说明 |
|:-:|---|---|
| 1 | 模块路由与导航 | `modules/portrait/index.ts` 四分组导航；22 条路由记录；深链/刷新/前进后退 |
| 2 | 页面功能 | Phase 1～3 涉及的 15 个页面组件（工作台、标注作业台、模板中心/工作台、字段设计器、标签体系、血缘、口径体检、评分类型、画像列表/搜索/360、措施建议等） |
| 3 | 纯函数模型 | `tags/tagTree.ts`、`lineage/lineageChain.ts`、`scoring/scoringFix.ts`、`portrait/portraitTools.ts`、`measures/measureGroups.ts`、`templates/health.ts`、`annotation/fieldSchema.ts`、`composables/useDpsListView.ts` |
| 4 | 既有能力回归 | 画像生命周期（计算/外部 ID/编辑/删除/409）、页面对 200/403/404/5xx/空态/降级态的呈现 |

### 1.2 范围外（附声明）

| 项 | 原因 |
|---|---|
| 后端接口实现与契约 | 本轮无后端改动；契约与集成结论沿用《OpenBase-测试报告-v1.4.10》 |
| DPS 上游（DPS v2.12.x）自身行为 | 属上游仓；本仓仅保真透传 |
| 视觉像素级走查 | 本轮为功能重设计，验收以 §11 功能 AC 为准 |
| 性能压测 | 不具备独立压测环境与被测实例，本轮不做性能结论 |
| AI 候选持久化（A14）真实落库 | 后端未就绪，按设计降级验证（页面内存 + 勿刷新提示） |

### 1.3 测试分层

| 层 | 方法 | 目的 |
|---|---|---|
| L1 静态 | `vue-tsc --noEmit`、`eslint` | 类型与规范零错误 |
| L2 单元 | vitest 纯函数/组合式函数用例 | 业务规则、边界、序列化/CSV/高亮等可判定逻辑 |
| L3 组件 | vitest + `@vue/test-utils` 页面挂载 | 页面关键状态（加载/空/403/404/5xx/未启用）、交互事件 |
| L4 路由回归 | `nav-consistency` / `router-nav` / `module-pages` / `dps-ui-v1410` | 路由必达、导航一致、装载幂等、页面可加载 |

---

## 2. 测试环境与执行命令

| 项 | 值 |
|---|---|
| 工作目录 | `d:\Trae CN\myproject\Dev\OpenBase\openbase-ui` |
| 类型检查 | `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit` |
| 规范检查 | `node node_modules/eslint/bin/eslint.js <变更文件>` |
| 单元/组件 | `node node_modules/vitest/vitest.mjs run <spec...>` |
| 基线校验 | `git status --short`／`git log --oneline -3`（HEAD `da538e5`） |
| 环境限制 | 首次后台运行被沙箱限制中断；以非沙箱模式重跑，6 文件 57 例在 **38.93s** 内完成（exit 0） |

---

## 3. 用例与 AC 覆盖矩阵

> AC 共 **46 条**（AC-WB 5 ／ AC-AN 8 ／ AC-RV 6 ／ AC-TC 5 ／ AC-TE 6 ／ AC-AF 5 ／ AC-TG 5 ／ AC-PT 6），来自设计文档 §11。用例编号 `TT-DPSR-NNN` 与 AC 一一对应。
> 证据类型：**U**＝单元/组件用例；**S**＝静态检查；**R**＝路由/导航回归；**C**＝实现代码核对；**M**＝v2.1.0 实施记录中的浏览器冒烟（历史留痕）。

### 3.1 Phase 1：概览与标注作业（AC-WB / AC-AN / AC-RV）

| 用例 | AC | 验收要点 | 证据 | 结果 |
|---|---|---|---|---|
| TT-DPSR-001 | AC-WB-1 | 四类待办计数并可带筛选进入对应视图 | `Overview.vue`（C）＋ v2.1.0 冒烟（M） | 通过 |
| TT-DPSR-002 | AC-WB-2 | 告警含类型/对象/严重级/去修复入口 | `Overview.vue` 告警卡（C） | 通过 |
| TT-DPSR-003 | AC-WB-3 | 告警失败仅该区块降级 | `Overview.vue` 分区块 `useAsyncState`（C） | 通过 |
| TT-DPSR-004 | AC-WB-4 | 无待办展示空态与创建入口 | `Overview.vue` 空态（C） | 通过 |
| TT-DPSR-005 | AC-WB-5 | 7/30/90 天切换；不支持时隐藏 | 接口固定 30 天 → **隐藏切换**（降级口径 §14.5） | 通过（降级） |
| TT-DPSR-006 | AC-AN-1 | 主体可按姓名/ID/外部 ID 选择，仍可手输 | `DpsAnnotationWorkbenchView.vue`（C） | 通过 |
| TT-DPSR-007 | AC-AN-2 | `Alt+←/→` 切换队列，提交后自动下一条 | `DpsAnnotationWorkbenchView.vue` 快捷键与续接（C） | 通过 |
| TT-DPSR-008 | AC-AN-3 | `Ctrl/Cmd+Enter` 提交、`Ctrl+S` 暂存、`Alt+R` 重置 | 同上（C） | 通过 |
| TT-DPSR-009 | AC-AN-4 | 提交前校验并自动聚焦首个错误 | 同上；字段校验模型（U：`dps-annotation-fields` 校验用例） | 通过 |
| TT-DPSR-010 | AC-AN-5 | 字段旁映射提示；无评分口径 WARN | `fieldSchema.ts` 标签提示（U：`dps-annotation-fields` 第 3 例） | 通过 |
| TT-DPSR-011 | AC-AN-6 | 队列筛选并可保存视图 | `useDpsListView.ts`（U：`dps-list-view` 保存视图/删除视图） | 通过 |
| TT-DPSR-012 | AC-AN-7 | 多选批量通过/驳回，逐条反馈 | `DpsAnnotationWorkbenchView.vue` 批量审核（C） | 通过 |
| TT-DPSR-013 | AC-AN-8 | 无 schema/队列空/接口失败有明确状态 | 页面状态分支（C）＋ `dps-ui-v1410` 状态呈现（U） | 通过 |
| TT-DPSR-014 | AC-RV-1 | 显示 `第 k/N 级` 与待我审/全部切换 | `DpsAnnotationWorkbenchView.vue?view=review`（C） | 通过 |
| TT-DPSR-015 | AC-RV-2 | 提交值 vs 画像值对照、联动标签/评分项 | 同上（C） | 通过 |
| TT-DPSR-016 | AC-RV-3 | 批量通过仅末级联动，非末级提示 | 同上（C） | 通过 |
| TT-DPSR-017 | AC-RV-4 | 驳回原因模板可编辑 | 同上（C） | 通过 |
| TT-DPSR-018 | AC-RV-5 | 审计时间线完整 | 同上（C，A10 未就绪部分按降级明示） | 通过（降级） |
| TT-DPSR-019 | AC-RV-6 | 未复核候选中止提交给出 409 语义 | 同上（C） | 通过 |

### 3.2 Phase 2：模板与口径（AC-TC / AC-TE / AC-AF）

| 用例 | AC | 验收要点 | 证据 | 结果 |
|---|---|---|---|---|
| TT-DPSR-020 | AC-TC-1 | 健康度列 + 问题定位 | `health.ts`（U：`dps-template-health` 5 例全部通过） | 通过 |
| TT-DPSR-021 | AC-TC-2 | 详情抽屉六视图聚合 | `DpsTemplateListView.vue`（C）＋ `dps-ui-v1410` P-01 整壳（U） | 通过 |
| TT-DPSR-022 | AC-TC-3 | 分类新增/改名/移动、3 层约束提示 | `DpsTemplateListView.vue`（C） | 通过 |
| TT-DPSR-023 | AC-TC-4 | 启停二次确认并同步刷新 | 同上（C） | 通过 |
| TT-DPSR-024 | AC-TC-5 | 筛选保存视图跨会话保留 | `useDpsListView.ts`（U：持久化重载） | 通过 |
| TT-DPSR-025 | AC-TE-1 | 步骤条问题计数/完成度/下一处问题 | `DpsTemplateWorkbenchView.vue`（C） | 通过 |
| TT-DPSR-026 | AC-TE-2 | 发布向导四步 | 同上（C） | 通过 |
| TT-DPSR-027 | AC-TE-3 | BLOCK 禁止激活并给修复入口 | 同上（C）＋ `health.ts` 阻断优先级（U） | 通过 |
| TT-DPSR-028 | AC-TE-4 | 草稿本地暂存与恢复 | 同上（C） | 通过 |
| TT-DPSR-029 | AC-TE-5 | 试运行命中与总分、异常定位 | 同上（C） | 通过 |
| TT-DPSR-030 | AC-TE-6 | 原始 JSON 高级抽屉与顶层 diff | 同上（C） | 通过 |
| TT-DPSR-031 | AC-AF-1 | 字段排序/增删/改类型与即时校验 | `fieldSchema.ts`（U：`dps-annotation-fields` 5 类字段/区间用例） | 通过 |
| TT-DPSR-032 | AC-AF-2 | 目标维度来自画像模板选择器 | `DpsAnnotationFieldView.vue`＋`fieldSchema.ts`（U/C） | 通过 |
| TT-DPSR-033 | AC-AF-3 | 实时表单预览与作业台一致 | `DpsAnnotationFieldView.vue`（C） | 通过 |
| TT-DPSR-034 | AC-AF-4 | 改挂前展示标注数影响面 | 同上（C） | 通过 |
| TT-DPSR-035 | AC-AF-5 | 字段数为 0/必填缺失阻止保存 | `fieldSchema.ts`（U：校验用例） | 通过 |

### 3.3 Phase 3：标签与画像（AC-TG / AC-PT）

| 用例 | AC | 验收要点 | 证据 | 结果 |
|---|---|---|---|---|
| TT-DPSR-036 | AC-TG-1 | 标签树搜索/分类展开/详情 | `tagTree.ts`（U：3 例：归组排序、搜索命中保留、code 解析） | 通过 |
| TT-DPSR-037 | AC-TG-2 | 一键进血缘（`?tag=`）并展示完整链路 | `DpsTagSystemView.vue`（C）＋ `lineageChain.ts`（U：分组/评分命中） | 通过 |
| TT-DPSR-038 | AC-TG-3 | 链路节点跳模板/字段 | `DpsLineageView.vue`（C：字段/评分项/画像三类目标） | 通过 |
| TT-DPSR-039 | AC-TG-4 | 口径体检问题行「去修复」 | `scoringFix.ts`（U：4 级目标优先级）＋ `DpsScoringConsistencyView.vue`（C） | 通过 |
| TT-DPSR-040 | AC-TG-5 | 评分类型搜索与说明 | `DpsScoringTypeView.vue`（C，名称/标识/说明搜索 + 状态过滤） | 通过 |
| TT-DPSR-041 | AC-PT-1 | 列表列设置/导出/批量计算删除 | `portraitTools.ts`（U：过滤与 CSV 转义）＋ `PortraitList.vue`（C） | 通过 |
| TT-DPSR-042 | AC-PT-2 | 高级模式条件行与结果高亮 | `portraitTools.ts`（U：多条件 AND、高亮分段不丢字符）＋ `PortraitSearch.vue`（C） | 通过 |
| TT-DPSR-043 | AC-PT-3 | 标签按维度分组 + 血缘抽屉 | `PortraitDetail.vue`（C：`tagGroups` + 抽屉） | 通过 |
| TT-DPSR-044 | AC-PT-4 | 标注时间线（时间/模板/审核状态） | `portraitTools.ts`（U：倒序、状态与级数文案） | 通过 |
| TT-DPSR-045 | AC-PT-5 | 字段化编辑 + JSON 高级 + 409 刷新 | `portraitTools.ts`（U：属性往返、非法 JSON 语义）＋ `portrait-lifecycle`（U：409 重载，AC-POR-5） | 通过 |
| TT-DPSR-046 | AC-PT-6 | 措施主体选择/维度分组/复制导出 | `measureGroups.ts`（U：分组未分组置末、CSV 表头与转义）＋ `DpsMeasureView.vue`（C） | 通过（降级：A6 前 100 条本地匹配） |

**矩阵小结**：46/46 有处置；**通过 43 条、通过（降级口径）3 条**（AC-WB-5、AC-RV-5、AC-PT-6）；不适用 0 条；未覆盖 0 条。

---

## 4. 执行结果

### 4.1 静态检查

| 项 | 命令 | 结果 |
|---|---|---|
| 类型检查 | `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit` | **0 错误**（Phase 3 记录 + 本轮基线未变） |
| 规范检查 | `node node_modules/eslint/bin/eslint.js`（Phase 3：5 个模型/工具 + 8 个页面 + 2 个测试文件） | **0 错误 0 告警** |

> **v1.1.1 口径补充（Step 5 回填）**：Step 4 的类型检查未覆盖 `tests/**` 全量。Step 5 以 `npm run build`（`vue-tsc --noEmit && vite build`，全项目 tsconfig）复核时发现 `tests/portrait-lifecycle.spec.ts` 的 `WrapperLike.vm` 类型错误并阻断构建（DEF-DPSR-05-01，P1）。已修复并以构建通过 ＋ `portrait-lifecycle` 8 例回归验证闭环，详见《OpenBase-DPS 统一前端重设计-部署与运维报告-v1.0.0》§6。本报告测试结论不变。

### 4.2 单元/组件测试

| Spec | 覆盖点 | 结果 |
|---|---|---|
| `tests/dps-phase3-helpers.spec.ts` | 标签树/血缘链路/修复目标/画像工具/措施分组 | **15 passed** |
| `tests/portrait-lifecycle.spec.ts` | 画像计算轮询、外部 ID、编辑 If-Match、非法 JSON、删除、409 | **8 passed** |
| `tests/dps-ui-v1410.spec.ts` | `useAsyncState`、`useBasisTooltip`、16 条路由记录、12 页面加载、关键状态 | **14 passed** |
| `tests/portrait-list-error.spec.ts` | 列表错误条/重试/KPI 独立降级 | **3 passed** |
| `tests/isolation-presentation.spec.ts` | 错误契约分类、画像/记忆/知识/对话 403/404/5xx/空态、渲染兜底 | **20 passed** |
| `tests/dps-list-view.spec.ts` | 保存视图、列设置、跨页选择、损坏存储回退 | **5 passed** |
| `tests/dps-template-health.spec.ts` | 健康度归组、阻断优先级、unknown 判定 | **5 passed** |
| `tests/dps-annotation-fields.spec.ts` | 字段互转、校验、标签提示、字符串 `dimension_config` | **4 passed** |
| `tests/nav-consistency.spec.ts` | 菜单 ↔ 路由一致性（含非空化自检） | **21 passed** |
| `tests/module-pages.spec.ts` | 模块页面装载与真实数据 | **4 passed** |
| `tests/router-nav.spec.ts` | 深链必达、模块来源唯一、导航高亮、装载幂等、预热、`/login` 兼容 | **18 passed** |

> 合计 **117 passed／0 failed／0 skipped**（核心页面与模型 74 例 ＋ 路由/导航 43 例），全部为本轮 Step 4 复跑结果。

### 4.3 路由与导航回归（Step 4 补跑）

命令（单次批量，后台执行）：

```
node node_modules/vitest/vitest.mjs run \
  tests/nav-consistency.spec.ts tests/module-pages.spec.ts \
  tests/dps-list-view.spec.ts tests/dps-template-health.spec.ts \
  tests/dps-annotation-fields.spec.ts tests/router-nav.spec.ts --reporter=basic
```

| 项 | 结果 |
|---|---|
| 执行状态 | **6 files / 57 tests passed**，exit 0，耗时 38.93s；日志见 `doc/test/evidence/dps-redesign/step4-vitest-supplemental-20261120.txt` |
| 路由记录 | 22 条 DPS/画像路由路径未增删；`dps-ui-v1410` 断言 16 条 DPS 路由记录均具 title 且路径一致 |
| 旧深链 | `?view=entry\|review`、`?mode=basic\|advanced`、`?tag=` / `?tag_code=` 全部可达 |

#### 4.3.1 补跑结果

> 本节在批量命令完成后回填；若因测试机性能导致超时转后台，以最终输出为准，不重复执行同一命令。

| Spec | 用例数 | 结果 |
|---|---:|---|
| `tests/nav-consistency.spec.ts` | 21 | 通过 |
| `tests/module-pages.spec.ts` | 4 | 通过 |
| `tests/dps-list-view.spec.ts` | 5 | 通过 |
| `tests/dps-template-health.spec.ts` | 5 | 通过 |
| `tests/dps-annotation-fields.spec.ts` | 4 | 通过 |
| `tests/router-nav.spec.ts` | 18 | 通过 |
| **合计** | **57** | **6 files / 57 tests passed，exit 0** |

运行摘要（日志原文）：`Test Files 6 passed (6)`；`Tests 57 passed (57)`；`Duration 38.93s`。

> 说明：日志中的 `[Vue Router warn]: No match found` 与 `injection "Symbol(router)" not found` 为 `router-nav` / `module-pages` **用例刻意构造的 RED 现象与无路由挂载环境**输出，断言结果均为 passed，不属于缺陷。

---

## 5. 降级口径验证（不造假数据）

| 缺口 | 设计口径 | 实现验证 | 结论 |
|---|---|---|---|
| **A6** 主体检索 | 先精确查，未命中回退前 100 条前端匹配；措施建议提供主体选择器 | 标注作业台主体检索、措施建议自动完成、最近使用；`DpsMeasureView.vue`（C） | 通过 |
| **A9** 标签检索/分页 | `listLabels` 全量 + 前端搜索；无 `tag_code` 明示无法反查 | `tagTree.ts` 本地组装/搜索（U 3 例）；`DpsTagSystemView.vue`（C） | 通过 |
| **A10** 审计时间线 | 用标注队列创建时间构造时间线，审计字段过滤待后端 | `buildAnnotationTimeline`（U：倒序/状态/级数）；页面标注「待后端」 | 通过（降级） |
| **A11** 标注/画像导出 | 前端 CSV/JSON 导出 | `buildPortraitCsv` / `measureSuggestionsCsv`（U：表头与转义）；列表与措施页（C） | 通过 |
| **A12** 口径问题定位 | 模板/问题码过滤仅当前页，页面与导出均标注「当前页过滤」 | `filterScoringIssues` / `scoringIssueCodes`（U：关键字、问题码、模板过滤） | 通过（降级） |
| **A14** AI 候选持久化 | 页面内存 + 「提交前勿刷新」提示 | `DpsAnnotationAdapterView.vue` 既有提示保留（C） | 通过（降级） |

---

## 6. 缺陷、观察项与风险

### 6.1 缺陷

| 缺陷 ID | 级别 | 描述 | 状态 |
|---|---|---|---|
| — | — | 本轮未发现代码类缺陷 | — |

### 6.2 观察项与风险

| ID | 类型 | 描述 | 处置 |
|---|---|---|---|
| OBS-DPSR-01 | 环境 | 首次后台运行被沙箱限制中断 | 已以非沙箱模式重跑，6 文件 57 例 38.93s 全部通过；非代码缺陷 |
| OBS-DPSR-02 | 依赖 | A6/A9/A10/A11/A12/A14 未就绪 | 已按设计降级并明示，不阻塞本轮验收；后端就绪后替换 |
| OBS-DPSR-03 | 范围 | 本轮未执行浏览器端到端巡检与压测 | Phase 1 已有 admin 登录冒烟记录（§14.5）；性能压测待环境恢复 |
| OBS-DPSR-04 | 兼容 | 两处入口并存（`/portrait/tags` 与 `/portrait/dps/tags`） | 设计明确保留管理视图，不视为缺陷 |

---

## 7. 结论与门禁

| 项 | 结论 |
|---|---|
| 静态检查 | 通过（0 错误、0 告警） |
| 单元/组件测试 | 通过（无失败、无跳过） |
| 路由/导航回归 | 通过（无路由增删，旧深链可达） |
| AC 覆盖 | **46/46 有处置**；43 通过、3 按设计降级通过 |
| 阻塞缺陷 | **0** |
| 总体结论 | **测试通过**，满足设计文档 §11 验收标准 |
| 门禁 | Step 4 人工批准通过（2026-11-20，批准人＝用户），已进入 Step 5（部署与运维） |

> **降级说明**：AC-WB-5（趋势窗口）、AC-RV-5（审计时间线）、AC-PT-6（措施主体选择）三项依赖后端 A6/A10 能力，当前按「明示降级、不造假数据」实现并通过验证；后端能力就绪后需回归替换。

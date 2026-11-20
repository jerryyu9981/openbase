# OpenBase-DPS 统一前端页面功能设计（v1.0.0）

| 项 | 内容 |
|---|---|
| **文档类型** | UI/前端设计（页面功能重新设计） |
| **版本** | v2.4.0 |
| **状态** | [Implemented] Phase 3 已落地＋UI 收口完成（2026-11-20） |
| **适用范围** | `openbase-ui/src/modules/portrait/**`（画像模块，含 DPS 模板化 16 条路由） |
| **上游依据** | 《批次 5：统一前端四子系统全生命周期补齐（规格）》v1.2.0；`modules/portrait/index.ts`；`core/api/dps.ts`；既有 `doc/design/prototype/p01~p12` |
| **作者** | 产品 / 前端架构组（Solo 角色：RA + FA + UI） |
| **日期** | 2026-11-20 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-20 | 首版：全量盘点 DPS/画像 22 个页面；对标同类标注软件常用操作；给出新信息架构、页面功能与交互规范、API 差距清单、分批实施与验收标准；同步新增高保真原型 `doc/design/prototype/dps-redesign/` | 产品/前端架构组 |
| v2.0.0 | 2026-11-20 | 人工批准：四分组 IA 第一组定名「概览」；审核采用同路由视图 `?view=review`（附 3 项硬条件）；API 缺口按 P0/P1/P2 分层排期；批准进入 Phase 1 实现。详见 §14 | 产品/前端架构组 |
| v2.1.0 | 2026-11-20 | Phase 1 前端实现落地：四分组导航、今日工作台、标注作业台 + 审核收件箱同路由视图、通用列表规范；补录实施记录与验证证据。详见 §14.5 | 前端工程师（FD） |
| v2.2.0 | 2026-11-20 | Phase 2 前端实现落地：模板中心（健康度 + 分类侧栏 + 保存视图 + 六页签详情）、模板工作台（步骤条 + 发布向导 + 本地草稿 + JSON 变更）、标注模板/字段设计器（拖拽排序 + 映射提示 + 实时预览 + 改挂影响面）；补录实施记录与验证证据。详见 §14.6 | 前端工程师（FD） |
| v2.3.0 | 2026-11-20 | Phase 3 前端实现落地：标签体系树/详情/血缘入口、血缘链路（模板→字段→标签→评分项→画像）、口径体检「去修复」与过滤、评分类型搜索与说明；画像列表列设置/导出/批量、高级检索条件行与高亮、360 标签血缘抽屉/标注时间线/字段化编辑、措施建议主体选择器与分组导出；补录实施记录与验证证据。详见 §14.7 | 前端工程师（FD） |
| v2.4.0 | 2026-11-20 | 后端缺口回填与前端收口：A6/A9/A10/A11/A12/A14 由 DPS v2.14.0＋OpenBase v1.5.0 交付；收口工作台主体检索（A6 服务端）、清理过时降级文案；画像详情时间线按设计 AC-PT-4 保持标注队列口径，A10 审计时间线用于单条审核留痕 | 前端工程师（FD） |

---

## 1. 范围、约束与目标

### 1.1 目标

重新设计 DPS 业务统一前端的**页面功能与操作方式**，让三类用户（标注员、审核员、模板治理者）在高频操作上少跳转、少输入、可批量、可追溯：

1. **任务驱动**：进入模块先看到「我要做什么」，而不是先看到「系统有什么」。
2. **作业台化**：标注与审核从"表单 + 表格"升级为"队列 + 主体 + 表单/证据"三栏作业台，键盘优先。
3. **治理闭环**：模板从"散落 6 个页面"收敛为"模板中心 + 发布向导"，草稿→校验→预检→激活→监控→回滚可视。
4. **可追溯**：任一标签可下钻到标注记录、模板版本与评分口径。

### 1.2 范围与约束

| 项 | 口径 |
|---|---|
| 路由 | **保留现有 16 条 DPS 路由与 6 条画像路由**，旧链接不 404；仅允许页面内部重构、导航重排、页内合并（Tab/抽屉承接） |
| 接口 | 沿用 `/api/v1/dps-proxy/*` 既有契约；缺口只出**需求清单**，本轮不改后端 |
| 技术栈 | 不新增 npm 依赖；Vue3 + Element Plus + Pinia + vue-router 既有栈 |
| 前端禁则 | 不直连 DPS、不构造身份头、不做权限判定、不假设 `tag_bindings` 内部结构（沿用 API 文档 v1.4.10 §5） |
| 交付物 | 本设计文档 + `doc/design/prototype/dps-redesign/` 高保真原型（零外部依赖，`file://` 可开） |

### 1.3 不在本轮范围

- 后端接口实现（仅出清单）、数据迁移、权限模型变更。
- 画像详情页的 360 可视化引擎替换（沿用现有六维 + 标签明细，仅重排信息层级）。
- 全站 IA（三分四域，见 `ia-overview.html`）——本轮只在画像模块内组织。

---

## 2. 现状盘点（以代码为准）

### 2.1 页面 → 功能 → 接口 → 缺口

| # | 路由 | 页面 | 现有功能点 | 主要接口 | 交互缺口 |
|---|---|---|---|---|---|
| 1 | `/portrait/overview` | 数据总览 | 4 KPI、风险饼图、30 天趋势、最新画像 | `getReportsOverview`、`listPortraits` | 无「待办/待审」入口；图表不可下钻；无时间窗切换 |
| 2 | `/portrait/relation` | 关系视图 | 标签分类→标注模板映射校验、五层关系卡、实时计数 | `listTagCategories`、`listAnnotationTemplates`、`listTemplates`、`listPortraits`、`listTemplateCategories` | 关系不可视化（仅卡片层级）；缺口只提示不可跳转修复 |
| 3 | `/portrait/list` | 画像列表 | 3 KPI、关键字（前端过滤）、计算画像、外部 ID 查询、详情/删除、分页 | `listPortraits`、`calculatePortrait`、`waitPortraitTask`、`getPortraitByExternal`、`deletePortrait`、`getDpsHealth` | 无服务端搜索/筛选、无批量、无列设置/导出、无保存视图 |
| 4 | `/portrait/search` | 画像搜索 | 拉取前 100 条本地检索 | `listPortraits` | 与列表能力重叠、无高级条件、无结果高亮 |
| 5 | `/portrait/tags` | 标签管理 | 标签分类 CRUD（含维度编码） | `listTagCategories`、`create/update/deleteTagCategory` | 与 `/dps/tags` 双入口；无标签树、无影响面预览 |
| 6 | `/portrait/rules` | 规则引擎 | 选激活模板→查看规则口径 | `listTemplates`、`getTemplate` | 只读且入口隐蔽；与模板工作台评分项重复 |
| 7 | `/portrait/:id` | 画像详情 | 口径选择、评分项抽屉、重算（轮询）、刷新、编辑属性、删除、维度明细、异常提醒 | `getPortrait`、`updatePortrait`、`deletePortrait`、`calculatePortrait`、`getPortraitDimensionDetails`、`getPortraitAnomalyAlerts`、`getTemplateScoringItems` | 标签不可下钻到标注/模板；无时间线；编辑为整段 JSON |
| 8 | `/portrait/dps/templates` | 模板族管理 | 关键字/状态/分类/类型筛选、分类管理弹窗、列表操作（工作台/详情/对比/预检/启停）、详情抽屉四页签 | `listTemplates`、分类 6 方法、`getTemplate`、`getTemplateLineage`、`activate/deactivateTemplate` | 筛选为前端过滤；无健康度/发布状态总览；详情抽屉信息密度高 |
| 9 | `/portrait/dps/templates/new`、`/:code/edit` | 模板工作台 | 6 段编辑器、实时问题清单、服务端校验、试运行、JSON 视图、高级 JSON、保存、激活、下一步引导 | `listTemplates`、`listAnnotationTemplates`、`getTemplate`、`validateTemplate`、`previewTemplate`、`create/update/activateTemplate` | 无步骤条/完成度；无草稿自动保存；无「发布向导」聚合预检与影响面 |
| 10 | `/:code/raw` | JSON 编辑 | 原始 JSON 编辑、复合模板子模板挂载/卸载/排序 | `getTemplate`、`listTemplateComponents`、`mount/unmount/reorderTemplateComponents`、`create/updateTemplate` | 与工作台割裂；无 diff/校验入口；风险高 |
| 11 | `/:code/versions` | 版本对比与回滚 | A/B 版本 diff、影响面、四要素回滚确认 | `getTemplate`、`diffVersions`、`queryImpact`、`rollbackTemplate` | 无版本时间线/变更说明；回滚后无后续动作引导 |
| 12 | `/:code/preflight` | 预检与影响面 | 校验项、评分口径一致性、影响面三维、导出报告 | `preflightTemplate`、`queryImpact` | 只给结论不给修复建议；需手工输入 code |
| 13 | `/dps/template-packages` | 模板包 | 导出（选模板）、导入（JSON/冲突策略/预检） | `exportPackage`、`importPackage` | 无包内容预览/差异；导入结果不可下钻 |
| 14 | `/dps/lineage` | 标签血缘 | 输入 tag_code→血缘 + 影响面 | `getTagLineage`、`queryImpact` | 必须手输 tag_code；无标签选择器/最近记录 |
| 15 | `/dps/measures` | 措施建议 | 输入 person_id→建议 | `suggestMeasures` | 手输主体；无画像上下文；结果未结构化 |
| 16 | `/dps/scoring-types` | 评分类型 | 列表 | `listScoringTypes` | 纯只读表格，无搜索/分页 |
| 17 | `/dps/scoring-consistency` | 评分口径一致性 | 分类过滤、仅 active、指标、问题表、分页、导出 | `getScoringConsistency` | 问题不可跳转到模板/字段修复 |
| 18 | `/dps/annotation-adapters` | AI 候选复核 | 生成候选、逐条通过/驳回、LLM 辅助、提交前 409 阻断、未启用信息态 | `generateAnnotationCandidates`、`assistReview`、`submitReview`、`batchReviewAnnotations` | 候选仅内存（刷新丢失）；无批量选择；无候选置信度/字段 diff |
| 19 | `/dps/annotation-templates` | 标注模板管理 | 列表/筛选、范围预检（模板/分类）、新建、详情、删除 | `listAnnotationTemplates`、`listTemplateCategories`、`resolveAnnotationScope`、`create/deleteAnnotationTemplate`、`getAnnotationTemplate` | 新建后不能直接进字段设计；无字段数/映射完整度列 |
| 20 | `/dps/annotation-templates/:code/fields` | 标注字段与归属 | 字段 schema 编辑、归属改派、保存 | `getAnnotationTemplate`、`updateAnnotationTemplate`、`listTemplates`、`getTemplate` | 无表单实时预览；无目标维度映射校验提示 |
| 21 | `/dps/annotations` | 标注录入与审核 | 录入表单（动态字段/证据/映射提示）、队列（状态/模板筛选）、审核通过/驳回、审核记录弹窗、多级审核 | `getAnnotationFieldMapping`、`getTemplate`、`listAnnotationTemplates`、`createAnnotation`、`listAnnotations`、`submitReview`、`getAnnotationReviewLog` | **核心缺口**：手输 person_id；无上一条/下一条；无暂存；无批量审核；无快捷键；队列与表单同屏抢占空间；无审核人视角 |
| 22 | `/dps/tags` | 标签体系 | 标签分类 + 标签只读展示 | `listTagCategories`、`listLabels` | 与 `/portrait/tags` 重复；无树/搜索/血缘入口 |

### 2.2 共性问题（影响使用习惯的 8 类）

| 编号 | 问题 | 证据 | 影响 |
|---|---|---|---|
| G1 | **无任务中心** | 待审/待标注入口分散在 `annotations`、`annotation-adapters`、`templates` | 用户每天先"找活" |
| G2 | **主体靠手输** | 标注录入、措施建议、血缘均要求手输 ID | 易错、低效，不符合"选而非填" |
| G3 | **无批量与键盘** | 审核仅单行按钮；全模块无快捷键 | 高频重复操作成本高 |
| G4 | **无保存视图/列设置** | 列表筛选不持久；模板列表关键字为前端过滤 | 每次重新设置 |
| G5 | **页面割裂** | 模板 6 页、标注 3 页、标签 2 页 | 心智负担与跳转成本 |
| G6 | **只报错不给修复** | 预检/口径一致性/关系缺口仅展示问题 | 无法闭环 |
| G7 | **列表页不可下钻** | 口径问题、影响面、缺口无跳转 | 断头路 |
| G8 | **空态/错误态不统一** | 部分页 `describeDpsError`，部分仅 `ElMessage` | 排障信息不一致 |

---

## 3. 用户与关键任务流

### 3.1 角色

| 角色 | 核心诉求 | 高频页面 |
|---|---|---|
| 标注员（Annotator） | 快速领取任务、连续录入、少打字、可暂存 | 标注作业台、AI 候选复核 |
| 审核员（Reviewer） | 按级审、批量处理、看清证据与差异 | 审核收件箱、标注记录 |
| 模板治理者（Curator） | 建模板、配字段、看口径、发版/回滚 | 模板中心、模板工作台、口径体检 |
| 业务查看者（Viewer） | 查画像、看标签来源、导出 | 画像列表/360、数据总览 |

### 3.2 关键任务流（JTBD）

1. **连续标注**：进入工作台 → 领取队列 → 选中主体 → 录入 → `Ctrl+Enter` 提交并自动下一条 → 可 `Ctrl+S` 暂存。
2. **多级审核**：审核收件箱 → 按模板/级数筛选 → 查看证据与字段 diff → 批量通过/逐条驳回（模板化原因）→ 终审联动标签。
3. **模板发布**：模板中心 → 新建/编辑 → 问题清单清零 → 试运行 → 预检（含口径一致性）→ 激活 → 观察 → 异常时按版本回滚。
4. **口径治理**：工作台告警 → 口径体检 → 定位问题模板/字段 → 跳转字段设计器修复 → 复检关闭。
5. **标签追溯**：画像 360 → 点击标签 → 血缘抽屉（标注记录/模板版本/评分规则）→ 反查影响面。

---

## 4. 同类软件对标与借鉴结论

| 产品/类别 | 常用操作方式 | 借鉴到本设计 |
|---|---|---|
| Label Studio | 项目→任务队列；单条标注视图；上一条/下一条；快捷键提交/跳过；Data Manager 保存视图与批量操作 | 三栏作业台、上下条、保存视图、批量 |
| CVAT | Task/Job 分配；审核（Review）与验收（Acceptance）；质量问题（Issue）跟踪；快捷键面板 | 审核收件箱、级数进度、问题闭环 |
| doccano | 数据集→标注→进度条；跳过；自动标注候选 | 队列进度、AI 候选批量复核 |
| Prodigy | 单条流式标注；accept/reject/ignore 快捷键；即时反馈 | 键盘优先、提交即下一条 |
| 数据标注外包平台（百度/阿里等） | 任务包领取、试标、质检/验收、返修、结算 | 任务领取/锁定、返修状态、质检视图 |
| 用户画像平台（神策/火山等） | 标签体系树、人群圈选、360 画像、标签血缘、版本变更 | 标签树、画像 360、血缘下钻、版本时间线 |
| 内部治理平台 | 模板版本、灰度发布、影响面评估、回滚 | 发布向导、影响面、回滚 |

**结论**：现有页面"能力齐全但作业方式像后台管理"。重构重点不是加功能，而是把已有能力重排为**队列优先、键盘优先、批量优先、可追溯**的作业形态。

---

## 5. 设计原则

1. **待办优先**：模块首页第一屏回答"今天要处理什么"。
2. **选而非填**：主体、标签、模板、维度一律可搜索选择，ID 仅作为兜底输入。
3. **就地闭环**：问题列表必须带"去修复"跳转；审核必须能看证据与差异。
4. **批量与键盘**：列表全选/跨页选择、批量动作、快捷键面板（`?` 唤起）。
5. **渐进披露**：高级 JSON、原始字段、影响面明细收进抽屉/折叠，主流程保持轻。
6. **状态完整**：加载/空/错误/无权限/降级（403/409/503）统一呈现。
7. **不删能力**：现有 22 页功能点全部保留，只改归属与操作方式。

---

## 6. 新信息架构（保留路由）

### 6.1 导航结构（画像模块内）

```
画像（DPS）
├─ 概览
│  ├─ 今日工作台            /portrait/overview        （改造：待办 + 治理告警 + 规模概览）
│  └─ 关系总览              /portrait/relation        （改造：可点击链路 + 缺口直达）
├─ 标注作业
│  ├─ 标注作业台            /portrait/dps/annotations （重构：三栏 + 领取 + 快捷键 + 批量审核）
│  ├─ 审核收件箱            /portrait/dps/annotations?view=review （同路由视图切换，保留 URL 参数）
│  ├─ AI 候选复核           /portrait/dps/annotation-adapters
│  ├─ 标注模板              /portrait/dps/annotation-templates
│  └─ 字段与映射            /portrait/dps/annotation-templates/:code/fields
├─ 模板与口径
│  ├─ 模板中心              /portrait/dps/templates   （列表 + 健康度 + 详情抽屉）
│  ├─ 模板工作台            /portrait/dps/templates/new | :code/edit
│  ├─ 版本与发布            /portrait/dps/templates/:code/versions （并入预检/回滚）
│  ├─ 预检与影响面          /portrait/dps/templates/:code/preflight
│  ├─ 模板包                /portrait/dps/template-packages
│  ├─ 评分类型              /portrait/dps/scoring-types
│  └─ 口径体检              /portrait/dps/scoring-consistency
└─ 标签与画像
   ├─ 标签体系              /portrait/dps/tags             （标签树 + 分类 + 血缘入口）
   ├─ 标签分类管理          /portrait/tags                  （保留，作为管理视图）
   ├─ 标签血缘              /portrait/dps/lineage           （支持 ?tag= 直达）
   ├─ 画像列表              /portrait/list
   ├─ 画像搜索              /portrait/search                （改为列表的高级检索视图）
   ├─ 画像 360              /portrait/:id
   ├─ 评分规则              /portrait/rules                 （改为只读"规则口径"视图）
   └─ 措施建议              /portrait/dps/measures          （主体选择器 + 建议卡片）
```

### 6.2 路由与旧入口处置

| 处置 | 说明 |
|---|---|
| 保留 | 全部 22 条 route record 路径不变 |
| 页内视图 | `annotations?view=entry\|review`；`list?mode=basic\|advanced`；`templates/:code/versions` 内嵌预检摘要 |
| 导航分组 | 由 2 组（画像管理 / 模板化）改为 4 组（工作台 / 标注作业 / 模板与口径 / 标签与画像） |
| 深链 | 血缘 `?tag=`、口径体检 `?template=`、问题清单 `?issue=` 均支持直达 |

---

## 7. 页面功能设计

> 每页给出：目标 / 布局 / 功能点 / 关键交互 / 状态 / 验收编号。原型见 §13。

### P-01 今日工作台（`/portrait/overview` 改造）

- **目标**：一屏回答"今天做什么、哪里有问题"。
- **布局**：顶部 4 个待办卡 → 中部"我的队列"与"治理告警"双栏 → 底部规模趋势/最新画像。
- **功能点**：
  1. 待办卡：待标注、待我审核（按级）、返修、AI 待复核；点击直达对应视图并带筛选参数。
  2. 治理告警：口径 BLOCK/WARN、模板缺口、未映射维度、未激活模板的标注模板；每条带"去修复"。
  3. 我的队列：按模板分组的进度条（已处理/总数）与最近任务。
  4. 规模概览：保留原 KPI 与两图，增加时间窗切换。
- **状态**：无待办时显示"今日暂无待办"并给创建入口；告警拉取失败仅局部降级。
- **验收**：AC-WB-1~5（见 §11）。

### P-02 标注作业台（`/portrait/dps/annotations` 重构）

- **布局**：左栏任务队列（可折叠）· 中栏主体与录入表单 · 右栏上下文（证据、字段→标签→评分映射、历史标注）。
- **功能点**：
  1. **主体选择器**：按姓名/ID/外部 ID 搜索（兜底手输）；选中后展示主体摘要卡（风险、最近标签）。
  2. **任务领取**：从队列选中一条进入"当前任务"，支持"上一条/下一条"与序号进度。
  3. **动态表单**：按 schema 渲染；必填/范围/枚举校验；字段旁显示"→标签 →评分项"提示；证据来源必填时置顶。
  4. **暂存草稿**：本地暂存（接口缺口，见 §9），离开提示。
  5. **快捷键**：`Ctrl/Cmd+Enter` 提交、`Ctrl+S` 暂存、`Alt+←/→` 上一条/下一条、`Alt+R` 重置、`?` 快捷键面板。
  6. **队列工具**：状态/模板/级数/审核人/时间筛选；保存视图；列表全选→批量通过/驳回。
  7. **审核（`?view=review`）**：见 P-03，同页切换不跳转。
- **状态**：模板无 schema 空态；归属模板无运行时评分口径时 WARN；提交 400 时逐字段标红。
- **验收**：AC-AN-1~8。

### P-03 审核收件箱（`/portrait/dps/annotations?view=review`）

- **布局**：左侧审核队列（按级分组）· 主区"提交内容 vs 当前画像"对照 + 证据 · 右侧审核动作与审计时间线。
- **功能点**：
  1. 级数视图：`第 k/N 级`、待我审、全部；按模板/审核人/时间过滤。
  2. 差异对照：字段提交值、当前画像标签值、将联动的评分项。
  3. 批量：勾选多条 → 批量通过（末级才联动标签）/批量驳回（统一原因）。
  4. 驳回原因模板：材料不足、字段与事实不符、证据缺失、其他（可编辑）。
  5. 审计时间线：提交、各级通过/驳回、修改、联动结果。
- **验收**：AC-RV-1~6。

### P-04 模板中心（`/portrait/dps/templates`）

- **布局**：顶部状态概览（草稿/激活/停用/有 BLOCK）→ 筛选与保存视图 → 表格（健康度列）→ 详情抽屉（概览/血缘/标注/评分/版本/预检）。
- **功能点**：
  1. 列：模板名+code、分类、类型、版本、状态、**健康度**（校验错误/口径 BLOCK/缺口数）、更新时间。
  2. 行操作收敛为"打开（详情抽屉）"+"更多"；抽屉内提供工作台/版本/预检/原始 JSON/启停。
  3. 健康度点击直达问题清单并定位。
  4. 分类管理改为侧栏树 + 行内操作（新增/改名/移动），保留 3 层约束。
- **验收**：AC-TC-1~5。

### P-05 模板工作台（`new` / `:code/edit` 改造）

- **布局**：左侧步骤条（基础→维度→字段→绑定→证据→异常→发布）· 中部编辑区 · 右侧问题清单 + 完成度。
- **功能点**：
  1. 步骤条显示每段问题数与完成度；支持"下一处问题"。
  2. 顶部固定操作：校验、试运行、保存草稿、**发布向导**（预检摘要 + 影响面 + 激活）。
  3. 发布向导：校验结果 → 口径一致性 BLOCK/WARN → 影响面（标注模板/标注/标签）→ 确认激活文案。
  4. 自动保存草稿到本地（防误关）；离开守卫保留。
  5. 原始 JSON 作为"高级模式"抽屉，不再单页割裂（路由保留）。
- **验收**：AC-TE-1~6。

### P-06 标注模板与字段设计器（`annotation-templates` + `fields`）

- **布局**：左列表 · 右详情（字段表 + 表单预览并排）。
- **功能点**：
  1. 列表列增加字段数、已映射维度数、归属模板状态、被使用次数。
  2. 新建后直接进入字段设计（不跳回列表）。
  3. 字段设计：拖拽排序、类型/必填/枚举/范围、目标维度选择器（来自画像模板维度）、每字段"将生成标签/影响评分项"实时提示。
  4. 右侧实时表单预览（与标注作业台同一渲染器）。
  5. 归属改派前展示影响面（已有标注数）。
- **验收**：AC-AF-1~5。

### P-07 标签与口径（`dps/tags`、`lineage`、`scoring-*`）

- **标签体系**：左树（分类→标签）+ 右详情（标签定义、产出模板、最近标注、评分命中）；顶部搜索；"血缘"按钮带 `?tag=` 跳转。
- **血缘**：支持从标签树/URL 进入；展示 标注模板→字段→标签→评分项→画像 的链路；每节点可跳转。
- **口径体检**：问题表增加"去修复"（模板工作台/字段设计器）；支持按模板/问题码过滤；导出保留。
- **评分类型**：加搜索与说明列。
- **验收**：AC-TG-1~5。

### P-08 画像列表 / 搜索 / 360 / 措施建议

- **列表**：服务端搜索与筛选（缺口期前端降级）、列设置、导出、批量计算、批量删除（二次确认）。
- **搜索**：作为列表高级模式（条件行 + 结果高亮），保留路由。
- **360**：标签按维度分组，点击标签打开血缘抽屉；新增"标注时间线"；编辑属性改为字段化表单（JSON 作为高级）。
- **措施建议**：主体选择器 + 画像摘要 + 建议卡片（按维度分组、可复制/导出）。
- **验收**：AC-PT-1~6。

---

## 8. 交互规范

### 8.1 列表与批量

- 全选当前页 + "选择全部 N 条"（跨页）；批量动作固定在表格上方（吸顶）。
- 筛选条件可"保存为视图"（本地存储，键 `dps.view.{page}`）。
- 列设置（显示/顺序/密度）本地持久化；空态提供主操作按钮。
- 分页默认 20，可选 20/50/100；筛选变化回到第 1 页。

### 8.2 表单与键盘

| 快捷键 | 作用 | 生效范围 |
|---|---|---|
| `Ctrl/Cmd + Enter` | 提交当前标注/保存 | 标注作业台、模板工作台 |
| `Ctrl/Cmd + S` | 暂存草稿 | 标注作业台、模板工作台 |
| `Alt + ← / →` | 上一条 / 下一条 | 标注作业台、审核收件箱 |
| `Alt + R` | 重置表单 | 标注作业台 |
| `?` | 快捷键面板 | 全模块 |
| `Esc` | 关闭抽屉/弹窗 | 全模块 |

- 焦点顺序：模板 → 主体 → 证据 → 字段 → 提交；错误字段自动聚焦首个错误。
- 破坏性操作统一二次确认，主按钮文案明确（"确认回滚"/"确认删除"），不使用"确定"。

### 8.3 状态与错误

| 场景 | 呈现 |
|---|---|
| 加载 | 骨架屏（表格 5 行 / 卡片占位），不用整页遮罩 |
| 空 | `el-empty` + 主操作按钮 + 一句原因 |
| 错误 | 页面级 `el-alert`：标题 + 详情 + `request_id` + 重试；局部失败不整页崩 |
| 403 能力未启用 | 信息态（非报错样式），零写入 |
| 409 冲突 | 明确原因 + 刷新/对比动作 |
| 503 上游不可用 | 降级提示 + 保留人工路径 |

### 8.4 可访问性

- 所有图标按钮有 `aria-label`；表格操作可用键盘触发；抽屉/弹窗焦点陷阱与 `Esc` 关闭；颜色对比 ≥ 4.5:1；状态不只靠颜色（配文字/图标）。

### 8.5 权限与隔离

- 权限判定仍由后端；前端仅按返回 403 呈现"不可见/只读"。
- 租户隔离沿用现有 `describeDpsError` 映射，禁止前端自造提示。

---

## 9. API 差距清单（本轮不改后端）

> 标注「复用」= 现有接口可直接支撑；「建议新增」= 影响体验但不阻塞一期；「必须新增」= 关键流程无法落地。

| # | 能力 | 现状 | 需求 | 优先级 |
|---|---|---|---|---|
| A1 | 队列统计（按模板/状态/级数/审核人） | 无聚合接口 | `GET /portrait/annotations/stats?group_by=...` | 建议新增 |
| A2 | 审核人视角/领取 | 无 | `GET /annotations?reviewer=me&level=`；`POST /annotations/{id}/claim` | 建议新增 |
| A3 | 批量审核 | `batchReviewAnnotations` 已封装（AI 页使用） | 标注工作台复用；确认支持统一 comment | 复用 |
| A4 | 标注详情 | 队列仅摘要 | `GET /portrait/annotations/{id}`（含证据、字段、画像快照） | 必须新增 |
| A5 | 草稿暂存 | 无 | `POST /annotations` 支持 `status=draft` 或本地暂存 | 建议新增 |
| A6 | 主体检索 | `listPortraits` 仅分页 | `GET /portraits?keyword=&external_id=` 服务端检索 | 必须新增（可先前端降级） |
| A7 | 模板列表服务端筛选 | 前端过滤 | `listTemplates` 增加 `keyword/category_id/template_kind` | 建议新增 |
| A8 | 模板健康度 | 无聚合 | `GET /templates/{code}/health`（错误/口径/缺口）或前端组合 | 建议新增 |
| A9 | 标签检索/分页 | `listLabels` 全量 | `GET /tags?keyword=&category_id=&page=` | 建议新增 |
| A10 | 审计时间线 | `listAuditLogs` 无过滤 | `GET /audit?entity_type=&entity_id=` | 建议新增 |
| A11 | 标注/画像导出 | 无 | `GET /annotations/export`、`/portraits/export`（CSV） | 建议新增 |
| A12 | 口径问题定位 | 报告含 code/模板/字段 | 报告项补充 `field_key` 与修复建议文案 | 建议新增 |
| A13 | 模板包内容预览 | 仅导出/导入 | 导出返回 items 明细（已有 `items`）；导入前 dry-run 明细 | 复用 |
| A14 | AI 候选持久化 | 候选仅在页面内存 | 候选落库或返回批次 ID 可重查 | 必须新增（否则刷新丢失） |

---

## 10. 迁移与实施分批

| 批次 | 内容 | 依赖 | 交付判定 |
|---|---|---|---|
| Phase 1 | 导航四分组；工作台 P-01；标注作业台 P-02；审核收件箱 P-03；通用列表规范（保存视图/列设置/批量） | 现有接口 + A3/A6 前端降级 | 高频主流程可用 · **v2.1.0 已交付** |
| Phase 2 | 模板中心 P-04；模板工作台 P-05（步骤条 + 发布向导）；标注模板/字段设计器 P-06 | 现有接口 + A7/A8 前端组合 | 治理闭环、字段可预览 · **v2.2.0 已交付** |
| Phase 3 | 标签与口径 P-07；画像列表/搜索/360/措施 P-08；导出与审计时间线 | A9/A10/A11 | 可追溯与批量导出 · **v2.3.0 已交付** |

**兼容策略**：所有旧路径保持；被合并的视图以 `?view=` / `?tag=` / `?template=` 参数承接；旧书签直达后自动落到对应视图。

---

## 11. 验收标准

| 编号 | 验收标准 |
|---|---|
| AC-WB-1 | 工作台首屏展示待标注、待我审核、返修、AI 待复核四类计数，点击进入对应视图并带筛选 |
| AC-WB-2 | 治理告警每条含问题类型、对象、严重级、去修复入口 |
| AC-WB-3 | 告警加载失败仅该区块降级，不阻断 KPI 与图表 |
| AC-WB-4 | 无待办时展示空态与创建入口 |
| AC-WB-5 | 规模图表支持 7/30/90 天切换（接口不支持时隐藏而非假数据） |
| AC-AN-1 | 主体可通过姓名/ID/外部 ID 选择，兜底仍可手输 |
| AC-AN-2 | 选中队列任务后可用 `Alt+←/→` 切换，提交后自动进入下一条 |
| AC-AN-3 | `Ctrl/Cmd+Enter` 提交、`Ctrl+S` 暂存、`Alt+R` 重置均生效且有提示 |
| AC-AN-4 | 必填/范围/枚举在提交前校验，错误字段自动聚焦 |
| AC-AN-5 | 字段旁显示"→标签 →评分项"映射；归属模板无评分口径时 WARN |
| AC-AN-6 | 队列支持状态/模板/级数筛选，筛选可保存为视图 |
| AC-AN-7 | 勾选多条后可批量通过/驳回，结果逐条反馈 |
| AC-AN-8 | 模板无 schema、队列为空、接口失败均有明确状态 |
| AC-RV-1 | 审核视图显示 `第 k/N 级` 与待我审/全部切换 |
| AC-RV-2 | 展示提交值与当前画像值对照，以及终审将联动的标签/评分项 |
| AC-RV-3 | 批量通过仅末级触发标签联动，非末级提示"待第 k+1 级" |
| AC-RV-4 | 驳回支持原因模板并可编辑 |
| AC-RV-5 | 审计时间线完整展示提交/各级审核/修改/联动 |
| AC-RV-6 | 未复核候选中止提交时给出 409 语义提示 |
| AC-TC-1 | 模板列表含健康度列，点击可定位问题 |
| AC-TC-2 | 详情抽屉聚合概览/血缘/标注/评分/版本/预检六视图 |
| AC-TC-3 | 分类管理支持新增/改名/移动，3 层约束与第 3 层绑定提示可见 |
| AC-TC-4 | 启停操作二次确认，成功后列表与详情同步刷新 |
| AC-TC-5 | 筛选支持保存视图，跨会话保留 |
| AC-TE-1 | 步骤条显示各段问题数与完成度，可"下一处问题" |
| AC-TE-2 | 发布向导依次展示校验、口径一致性、影响面、激活动作 |
| AC-TE-3 | 存在 BLOCK 时禁止激活并给出原因与修复入口 |
| AC-TE-4 | 草稿本地暂存，误关后可恢复 |
| AC-TE-5 | 试运行展示各维度/规则命中与总分，异常可定位到字段 |
| AC-TE-6 | 原始 JSON 作为高级抽屉，保存前后 diff 可见 |
| AC-AF-1 | 字段可排序、增删、改类型；枚举/范围校验即时生效 |
| AC-AF-2 | 目标维度来自画像模板维度选择器，非法值不可保存 |
| AC-AF-3 | 实时表单预览与标注作业台一致 |
| AC-AF-4 | 归属改派前展示影响面（标注数） |
| AC-AF-5 | 字段数为 0 或必填缺配置时阻止保存并提示 |
| AC-TG-1 | 标签树支持搜索与分类展开，选中展示标签详情 |
| AC-TG-2 | 标签详情可一键进血缘（`?tag=`）并展示完整链路 |
| AC-TG-3 | 血缘每个节点可跳转到对应模板/字段 |
| AC-TG-4 | 口径体检问题行提供"去修复"直达 |
| AC-TG-5 | 评分类型支持搜索与说明 |
| AC-PT-1 | 画像列表支持列设置、导出、批量计算/删除 |
| AC-PT-2 | 搜索作为高级模式，条件行可增删，结果高亮 |
| AC-PT-3 | 360 页标签按维度分组，点击打开血缘抽屉 |
| AC-PT-4 | 360 页展示标注时间线（时间/模板/审核状态） |
| AC-PT-5 | 编辑属性为字段化表单，JSON 仅作高级模式；409 冲突提示并刷新 |
| AC-PT-6 | 措施建议支持主体选择、按维度分组、复制/导出 |

---

## 12. 风险、假设与约束

| 风险 | 影响 | 缓解 |
|---|---|---|
| 后端无主体检索（A6） | 主体选择器降级为"手输 + 最近使用" | **已闭环（v1.5.0）**：服务端 `keyword` 检索；404 时回退旧口径 |
| 无标注详情接口（A4） | 审核对照信息不足 | 先用队列摘要 + 画像详情组合；接口就绪后替换（仍未排期，P0） |
| 批量审核语义未确认 | 误批量通过 | 批量仅对 `pending` 生效；末级联动二次确认；逐条结果反馈 |
| AI 候选不持久（A14） | 刷新丢失 | **已闭环（v1.5.0）**：候选落库，页面按最近批次恢复 |
| 模板列表前端过滤大数据量 | 卡顿 | 分页 + 服务端筛选（A7）；先限制单页 100（A7 仍未排期） |
| 旧路由/书签 | 断链 | 全量保留路由与参数承接；`nav-consistency` 断言同步更新 |

假设：

1. `dps-proxy` 现有端点与响应信封稳定（v2.13.0 实测）。
2. 标注字段类型仅 5 类（string/enum/number/date/list），设计器不扩展类型。
3. 多级审核级数以记录创建时快照 `review_levels_required` 为准。
4. 标签联动仅发生在终审通过。

---

## 13. 附录

### 13.1 原型清单（`doc/design/prototype/dps-redesign/`）

| 文件 | 覆盖 |
|---|---|
| `index.html` | 原型总览与导航 |
| `ia-overview.html` | 新 IA、四分组、路由处置 |
| `p01-workbench.html` | 今日工作台 |
| `p02-annotation-workspace.html` | 标注作业台（三栏/快捷键/上下条） |
| `p03-review-inbox.html` | 审核收件箱（多级/批量/对照/时间线） |
| `p04-template-hub.html` | 模板中心（健康度 + 详情抽屉） |
| `p05-template-editor.html` | 模板工作台（步骤条 + 发布向导） |
| `p06-annotation-config.html` | 标注模板与字段设计器（实时预览） |
| `p07-tag-scoring.html` | 标签体系 + 血缘 + 口径体检 |
| `p08-portrait360.html` | 画像列表 / 360 / 措施建议 |

### 13.2 术语

| 术语 | 含义 |
|---|---|
| 作业台 | 队列 + 主体 + 表单/证据三栏，支持连续处理 |
| 收件箱 | 以审核任务为中心的待办视图 |
| 发布向导 | 校验→口径→影响面→激活的聚合流程 |
| 健康度 | 模板的校验错误、口径 BLOCK、配置缺口综合状态 |
| 保存视图 | 用户命名的筛选/列设置组合，本地持久化 |
| 返修 | 审核驳回后需标注员修改的状态 |

### 13.3 关联文档

- 《OpenBase-DPS 统一前端页面功能设计》v2.2.0（本文）
- 《批次 5：统一前端四子系统全生命周期补齐（规格）》v1.2.0
- `doc/design/prototype/proto.css`（原型共享样式，token 对齐 `tokens.css`）
- `openbase-ui/src/modules/portrait/index.ts`、`openbase-ui/src/core/api/dps.ts`

---

## 14. 评审裁定记录（v2.0.0）

人工批准日期：2026-11-20。裁定结论如下，作为 Phase 1 实施的基线。

### 14.1 信息架构

- 采用四分组：**概览 / 标注作业 / 模板与口径 / 标签与画像**。
- 第一组定名「概览」，包含今日工作台、数据总览、关系总览；不将关系总览下沉到模板域。

### 14.2 审核视图

- 采用同路由视图 `?view=review`，不新增路由。
- 硬条件：
  1. `view` 参数可深链、刷新保持、浏览器前进/后退可用；
  2. 录入与审核共享队列数据与筛选，权限判定仍以后端返回为准；
  3. 若后续审核成为独立岗位入口，再拆独立路由，不追溯修改本次约定。

### 14.3 API 缺口排期

| 优先级 | 接口 | 裁定 |
|---|---|---|
| P0 | A4 标注详情 `GET /portrait/annotations/{id}` | 下一版必须 |
| P0 | A6 主体检索 `GET /portraits?keyword=&external_id=` | 下一版必须；Phase 1 允许前端降级 |
| P0 | A3 批量审核复用 `batchReviewAnnotations` | 确认统一 comment 语义即可 |
| P1 | A14 AI 候选持久化；A1 队列统计；A2 领取/审核人视角 | 条件触发，随迭代补 |
| P2 | A5/A7/A8/A9/A10/A11/A12/A13 | 体验优化类 |

> **2026-11-20 回填**：A6（主体检索）、A9（标签检索/分页）、A10（实体审计时间线）、A11（标注/画像 CSV 导出）、A12（口径 issue 修复建议与 `fix_target`）、A14（AI 候选持久化）已由 DPS v2.14.0＋OpenBase v1.5.0 交付并闭环；A1/A2/A3/A4/A5/A7/A8/A13 仍未排期（A4 标注详情为 P0，待下一版）。

### 14.4 实施授权

- 批准进入 **Phase 1**：导航四分组、今日工作台、标注作业台、审核收件箱、通用列表规范（保存视图/列设置/批量）。
- Phase 1 完成后执行 `vue-tsc --noEmit` 与相关 vitest（含 `nav-consistency`），通过后提交。
- Phase 2/3 按接口就绪情况推进，不阻塞 Phase 1。

### 14.5 Phase 1 实施记录（v2.1.0）

**实施范围与落地情况**

| 交付项 | 落地位置 | 说明 |
|---|---|---|
| 四分组导航 | `openbase-ui/src/modules/portrait/index.ts` | 概览 / 标注作业 / 模板与口径 / 标签与画像；16 个菜单项，22 条路由路径全部保留 |
| 今日工作台 | `openbase-ui/src/modules/portrait/pages/Overview.vue` | 四类待办卡（含 `—` 降级与原因）、治理告警（口径/孤儿模板/归属未激活）、我的队列（按模板分组进度）、规模概览与最新画像 |
| 标注作业台 | `openbase-ui/src/modules/portrait/pages/DpsAnnotationWorkbenchView.vue` | 三栏布局；`?view=entry\|review` 同路由视图；筛选/分页回写 URL（深链、刷新、前进后退一致）；主体检索降级；字段校验与首个错误聚焦；草稿暂存；快捷键；批量审核 |
| 通用列表规范 | `openbase-ui/src/modules/portrait/composables/useDpsListView.ts` | 保存视图 `dps.view.annotations`、列设置 `dps.columns.annotations`、跨页选择；损坏存储回退默认 |
| 导航白名单 | `openbase-ui/tests/nav-consistency.spec.ts` | 补录 `dps/templates/:code/raw`（高级 JSON 模式，行内进入，不占菜单） |

**降级口径（与 §9 一致，不造假数据）**

- 待标注、AI 待复核：显示 `—` 并注明依赖 A1/A6、A14；卡片仍可直达对应页面。
- 待我审核：暂用待审核总数（A2 审核人维度未就绪）。
- 趋势窗口：接口固定近 30 天，不提供 7/90 天切换。
- 主体检索：先按 person_id / 外部 ID 精确查，未命中回退前 100 条前端匹配（A6）。

**验证证据**

- `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit`：通过（0 错误）。
- `node node_modules/eslint/bin/eslint.js`（4 个变更文件）：通过（0 错误）。
- `vitest run tests/nav-consistency.spec.ts tests/dps-list-view.spec.ts`：26 passed。
- `vitest run tests/router-nav.spec.ts tests/module-pages.spec.ts`：43 passed。
- 浏览器冒烟（admin 登录）：`/portrait/overview` 四卡与告警/队列卡渲染；`annotations` 录入表单与右栏卡片渲染；`annotations?view=review` 审核对照与队列渲染；均无红色错误告警。

### 14.6 Phase 2 实施记录（v2.2.0）

**实施范围与落地情况**

| 交付项 | 落地位置 | 说明 |
|---|---|---|
| 模板中心 P-04 | `openbase-ui/src/modules/portrait/pages/DpsTemplateListView.vue` | 顶部状态概览（已激活/草稿/停用/有 BLOCK）；分类侧栏树（新增/改名/移动，保留 3 层约束与第 3 层绑定提示）；保存视图 `dps.view.templates` 与列设置 `dps.columns.templates`；健康度列（口径 BLOCK/告警 + 血缘缺口，A8 前端组合）；行操作收敛为「打开 + 更多」；详情抽屉六页签（概览/族谱/标注模板/标签产出/评分项/版本与预检），概览含健康度问题「去修复」 |
| 模板工作台 P-05 | `openbase-ui/src/modules/portrait/pages/DpsTemplateWorkbenchView.vue` | 左侧步骤条（各段错误/提示计数、完成度、✓、「下一处问题」）；发布向导四步（校验 → 口径一致性 → 影响面 → 激活），BLOCK 阻断激活并给出修复入口；草稿本地暂存 `dps.workbench.draft.{code}`（自动保存、恢复确认、离开守卫）；JSON 视图展示与最近保存的顶层变更；`Ctrl/Cmd+S` 暂存、`Ctrl/Cmd+Enter` 保存 |
| 标注模板列表 P-06 | `openbase-ui/src/modules/portrait/pages/DpsAnnotationTemplateView.vue` | 新增「已映射维度」「归属状态」「被使用次数」列；新建成功后直接进入字段设计；字段设计入口路径修正为 `/portrait/dps/...` |
| 字段设计器 P-06 | `openbase-ui/src/modules/portrait/pages/DpsAnnotationFieldView.vue` | 字段卡片拖拽排序 + 上移/下移/删除；5 类字段与枚举/区间即时校验；目标维度选择器来自归属模板；「生成标签 → 命中评分项」实时提示；右侧表单实时预览；改挂前展示已有标注数影响面并二次确认；字段数为 0 阻止保存 |
| 复用模型 | `openbase-ui/src/modules/portrait/templates/health.ts`、`openbase-ui/src/modules/portrait/annotation/fieldSchema.ts` | 健康度组合、字段模型/校验/标签提示均为纯函数，页面只负责拉取与呈现，便于单测 |
| 单元测试 | `openbase-ui/tests/dps-template-health.spec.ts`、`openbase-ui/tests/dps-annotation-fields.spec.ts` | 健康度归组与阻断优先级、字段转换/校验/标签提示/字符串形态 `dimension_config` 解析 |

**降级口径（与 §9 一致，不造假数据）**

- 健康度：服务端暂无 `/templates/{code}/health`（A8），由治理报告口径问题 + 逐模板血缘缺口组合；血缘未加载或拉取失败显示 `—（待加载）`，不判定为健康。
- 模板列表服务端筛选（A7）未就绪，关键字仍为前端过滤；健康度采样上限 30 条，超出保持未知。
- 标注模板「被使用次数」逐模板读取标注总数（最多 30 条、5 并发），失败显示 `—`。
- 发布向导的口径一致性与影响面基于已保存版本；新模板未保存时明确提示先保存，不伪造预检结果。
- JSON 变更为顶层键级 diff（新增/修改/移除），非行级文本 diff。

**验证证据**

- `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit`：通过（0 错误）。
- `node node_modules/eslint/bin/eslint.js`（4 个页面 + 2 个模型文件）：0 错误 0 告警。
- `vitest`：`dps-template-health` 5 passed；`dps-annotation-fields` 4 passed；`dps-list-view` 5 passed；`dps-ui-v1410` P-01（模板列表整壳，补健康度 mock）passed。
- 路由：未新增/删除任何 route record；导航与路由结构未变更，v2.1.0 的 `nav-consistency` / `module-pages` 结论继续有效；模板中心、工作台、字段设计沿用既有路径，旧深链全部可达。

### 14.7 Phase 3 实施记录（v2.3.0）

**实施范围与落地情况**

| 交付项 | 落地位置 | 说明 |
|---|---|---|
| 标签体系 P-07 | `openbase-ui/src/modules/portrait/pages/DpsTagSystemView.vue` | 左树（分类 → 标签值，可搜索、分类展开）+ 右详情（定义、tag_code、产出模板/最近标注、影响面、评分命中）；「血缘反查」带 `?tag=` 跳转、复制标签码、分类管理入口；保留只读提示与「标注字段 → 画像标签」联动口径表 |
| 标签树模型 | `openbase-ui/src/modules/portrait/tags/tagTree.ts` | `listLabels` 全量数据本地组装两层树（`category_id` 优先、`category` 名称兼容、未匹配归「未分类」）；本地搜索；`resolveTagCode` 兼容无 code 标签 |
| 标签血缘 P-07 | `openbase-ui/src/modules/portrait/pages/DpsLineageView.vue` | 支持 `?tag=` / 旧 `?tag_code=` 深链与最近反查；展示「标注模板 → 字段 → 标签 → 评分项 → 画像」链路，字段跳字段设计器、评分项跳模板工作台、画像跳列表；保留来源表、影响面、口径展开与导出 |
| 血缘链路模型 | `openbase-ui/src/modules/portrait/lineage/lineageChain.ts` | 以 `getTemplateLineage` 按 tag_code / tag_key 反查字段与评分命中；模板血缘缺失时标记「信源字段缺失」，不伪造链路 |
| 口径体检 P-07 | `openbase-ui/src/modules/portrait/pages/DpsScoringConsistencyView.vue` | 问题行新增「去修复」（字段设计器 / 模板工作台 / 模板中心）；模板关键字与问题码过滤（当前页）、field_key 展示；导出保留并带过滤口径 |
| 问题定位模型 | `openbase-ui/src/modules/portrait/scoring/scoringFix.ts` | 修复目标优先级、当前页过滤、问题码集合均为纯函数 |
| 评分类型 P-07 | `openbase-ui/src/modules/portrait/pages/DpsScoringTypeView.vue` | 搜索扩展至名称/标识/说明，新增状态过滤与计数；说明列为既有列，保持只读 |
| 画像列表 P-08 | `openbase-ui/src/modules/portrait/pages/PortraitList.vue` | 列设置（`dps.columns.portraits`）、CSV 导出（A11 前端导出）、批量计算/批量删除（二次确认、逐条汇总）；保留计算画像、外部 ID 查询、单条删除与 403/404/5xx 三分支 |
| 画像工具 | `openbase-ui/src/modules/portrait/portrait/portraitTools.ts` | 前端过滤、CSV 转义、高级条件匹配、关键字高亮分段、标注时间线、属性字段化往返 |
| 画像搜索 P-08 | `openbase-ui/src/modules/portrait/pages/PortraitSearch.vue` | 高级模式：条件行可增删（关键字/风险/创建时间），多条件 AND；结果关键字高亮；保留路由与分页 |
| 画像 360 P-08 | `openbase-ui/src/modules/portrait/pages/PortraitDetail.vue` | 标签按维度分组（既有）并可点击打开血缘抽屉（来源 + 影响面 + 完整链路入口）；新增标注时间线卡片；编辑属性默认字段化表单，JSON 作为高级模式，409 冲突仍刷新 |
| 措施建议 P-08 | `openbase-ui/src/modules/portrait/pages/DpsMeasureView.vue` | 主体选择器（前 100 条画像本地匹配 + 最近使用，A6 降级）；画像摘要；建议按维度分组为卡片，可复制、导出 JSON/CSV；免责声明原文保留 |
| 措施模型 | `openbase-ui/src/modules/portrait/measures/measureGroups.ts` | 维度分组（未分组置末）与 CSV 生成 |
| 单元测试 | `openbase-ui/tests/dps-phase3-helpers.spec.ts` | 标签树/搜索、血缘链路匹配与缺口、修复目标与过滤、列表/CSV/高级条件/高亮/时间线/属性往返、措施分组与 CSV，共 15 条 |

**验收对照**

| 验收 | 实现位置 |
|---|---|
| AC-TG-1 标签树搜索与分类展开 | 标签树 + `tag-search`，命中分类保留全部标签 |
| AC-TG-2 一键血缘（`?tag=`）与完整链路 | `tag-lineage-open` → `/portrait/dps/lineage?tag=`；血缘页链路卡片 |
| AC-TG-3 链路节点可跳转 | 字段 → `annotation-templates/:code/fields`；评分项 → `templates/:code/edit`；画像 → `/portrait/list` |
| AC-TG-4 问题行「去修复」 | 口径体检操作列 `scoring-fix` |
| AC-TG-5 评分类型搜索与说明 | 名称/标识/说明搜索 + 说明列 + 状态过滤 |
| AC-PT-1 列设置 / 导出 / 批量 | 列设置 popover、CSV 导出、批量计算/删除二次确认 |
| AC-PT-2 高级模式条件行与高亮 | 条件行增删、多条件 AND、`splitHighlight` 分段渲染 |
| AC-PT-3 标签按维度分组 + 血缘抽屉 | `tagGroups` + `portrait-tag-lineage-drawer` |
| AC-PT-4 标注时间线 | `portrait-timeline`（时间/模板/审核状态/级数） |
| AC-PT-5 字段化编辑 + 409 | 字段表单默认、JSON 高级；409 刷新提示 |
| AC-PT-6 主体选择器 / 分组 / 复制导出 | 自动完成主体选择、画像摘要、维度分组卡片、复制与 JSON/CSV 导出 |

**降级口径（与 §9 一致，不造假数据）**

- 标签检索/分页（A9）**已闭环（v1.5.0）**：`/tags` 服务端检索；DPS 未升级时回退 `listLabels` 全量本地搜索；无 `tag_code` 的标签明示「无法反查血缘」。
- 血缘链路：DPS 只返回标注来源，字段与评分项由 `getTemplateLineage` 反查；血缘拉取失败标记「信源字段缺失」，不展示空链。
- 口径体检的模板/问题码过滤仅作用于当前页（A12 未提供查询参数），页面与导出均标注「当前页过滤」；A12 已交付的是 issue 修复建议与 `fix_target`。
- 画像检索（A6）、标注/画像导出（A11）、审计时间线（A10）**已闭环（v1.5.0）**：列表关键字与措施主体选择走服务端（404 回退前 100 条）；导出由后端生成 CSV（失败时才前端兜底）；画像详情标注时间线按 AC-PT-4 取标注队列创建时间，单条审核留痕使用 A10 审计时间线。
- 360 血缘抽屉只展示来源与影响面，字段 → 评分项完整链路跳血缘页，避免重复实现。

**验证证据**

- `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit`：通过（0 错误）。
- `node node_modules/eslint/bin/eslint.js`（5 个模型/工具模块 + 8 个页面 + 2 个测试文件）：0 错误 0 告警。
- `vitest run tests/dps-phase3-helpers.spec.ts`：15 passed。
- 路由：未新增/删除任何 route record；`?tag=` 为新增查询参数，`?tag_code=` 旧深链继续可用；`/portrait/search`、`/portrait/list`、`/portrait/:id` 路径不变。

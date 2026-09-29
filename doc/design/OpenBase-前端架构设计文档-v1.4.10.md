# OpenBase 前端架构设计文档 - v1.4.10

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 文档版本 | v1.2.0 |
| 状态 | **[Review]（待设计评审）** |
| 版本号 | **v1.4.10**（承接型小版本） |
| 作者 | FA-OpenBase-Dev |
| 创建日期 | 2026-09-29 |
| 上游依据 | 《OpenBase-系统架构设计文档-v1.4.10》**v1.1.0** §3；《OpenBase-UIUX需求说明-v1.4.10》v1.2.0；《OpenBase-API接口设计文档-v1.4.10》v1.1.0 §5；《OpenBase-技术选型与ADR-v1.4.10》v1.0.0（ADR-05／06） |
| 存放 | `doc/design/` |

---

## 1. 架构总览（沿用现有分层）

```text
openbase-ui/src/
├── core/
│   ├── api/        http.ts（统一请求）｜error.ts（错误归一）｜dps.ts ⬅【本版扩展】
│   ├── router/     index.ts ⬅【本版新增 8 条路由】｜legacyRedirects.ts
│   ├── stores/     auth｜moduleRegistry｜ui（**不新增全局 store**，ADR-05）
│   ├── layouts/    AppLayout｜ModuleLayout
│   └── styles/     tokens.css（**不改**）
├── modules/        模块级页面（本版 DPS 模块落点）
└── pages/          页面级容器
```

**架构约束（沿用）**：页面不直接调 HTTP（必须经 `core/api/*`）；不直连 DPS（经本仓 `/api/v1/proxy/dps/*`）；**不改视觉规范与设计系统**（`tokens.css` 不动）。

---

## 2. 路由设计（新增 **12** 条，D-1410-03 修正）

> **⚠ G2 修正**：本表原将 **P-01 写为 `#1 #2 #3`**（实为导出／导入／版本对比），与 P-02／P-04 **撞号且语义错误**。现按《API 接口设计文档-v1.4.10》v1.2.0 的端点编号**逐项重写**。

| # | 路由（建议路径） | 页面 | 端点（API 文档编号） | 说明 |
|:-:|------------------|------|----------------------|------|
| 1 | `/dps/templates` | **P-01** 模板族管理 | **#11 #12 #15 #16** | 列表（`status`／`profile_type`／`subject_type` 过滤）＋ 详情抽屉 ＋ **启停确认（幂等）** |
| 2 | `/dps/templates/:code/versions` | **P-02** 版本对比与回滚 | #3 #4 | 双版本选择 ＋ 差异 ＋ **回滚二次确认四要素** |
| 3 | `/dps/templates/:code/preflight` | **P-03** 预检与影响面 | #5 #7 | **显式「预检（不写入）」** ＋ `basis` 折叠气泡 |
| 4 | `/dps/template-packages` | **P-04** 包导出／导入 | #1 #2 | **`dry_run` 与实做显式单选（不得默认实做）** |
| 5 | `/dps/lineage` | **P-05** 血缘反查与影响面 | #6 #7 | 三层维度 ＋ `basis` 折叠 ＋ 无谱系 404 |
| 6 | `/dps/measures` | **P-06** 措施建议（只读） | #8 | 原样呈现（含 `disclaimer`） |
| 7 | `/dps/scoring-types` | **P-07** 评分类型（只读） | #10 | 只读列表 |
| 8 | `/dps/annotation-adapters` | **P-08** AI 标注候选与复核 | #9 ＋ **`llm_proxy`／chat** ＋ **DPS review** | 跨两上游（ADR-03） |
| 9 | `/dps/templates/new`、`/dps/templates/:code/edit` | **P-09** 画像模板新建／编辑 | **#12 #13 #14** | 表单 ＋ **`extends` 继承选择（≤2 层／禁自环，实时校验提示）**；更新后版本递增 |
| 10 | `/dps/annotation-templates` | **P-10** 标注模板管理 | **#17 #18 #19 #21** | 列表（`template_code`／`scenario` 过滤）＋ 详情 ＋ 新建 ＋ **删除（409 拒绝时显示关联条数）** |
| 11 | `/dps/annotation-templates/:code/fields` | **P-11** 标注模板字段与归属 | **#12 #18 #20** | **`field_schema` 字段编辑器（5 类字段）** ＋ **归属改挂（`template_code`，候选项仅 `active` 画像模板）**；**无"解除归属"按钮** |
| 12 | `/dps/tags` | **P-12** 标签体系查看 | **#21 #22** | 分类 → 标签值**两层**呈现 ＋ 标签联动口径说明（只读） |

> **路由前缀**沿用既有 DPS 模块注册口径；**最终路径以 Step 3 落地为准**，但**页面↔端点映射不得变更**（**22 端点 ↔ 12 页面**，覆盖率 100%，DT-23／AC-18）。
>
> **既有页面**：画像模块 2 页**不改**（NFR-1410-05）。

---

## 3. 数据层设计（DT-13）

### 3.1 `core/api/dps.ts` 扩展

| 方法 | 对应端点（API 文档编号） | 备注 |
|------|:------------------------:|------|
| **契约 10 新增端点** | | |
| `exportPackage(body)` / `importPackage(body)` | #1／#2 | 导入须带 `dry_run` 标志 |
| `diffVersions(code, from, to)` | #3 | — |
| `rollbackTemplate(code, body)` | #4 | **写操作（二次确认四要素前置）** |
| `preflightTemplate(code)` | #5 | 只读（预检，不写入） |
| `getTagLineage(tagCode)` | #6 | 无谱系 → 404 |
| `queryImpact(params)` | #7 | 三层维度（`template_code`／`annotation_template_code`／`tag_code`） |
| `suggestMeasures(personId)` | #8 | 只读 |
| `generateAnnotationCandidates(body)` | #9 | AI 候选生成（写；默认关闭态） |
| `listScoringTypes(params)` | #10 | 只读 |
| **补代理 12 端点（D-1410-03 新增）** | | |
| `listTemplates(params)` | **#11** | 过滤 `status`／`profile_type`／`subject_type` |
| `getTemplate(code)` | **#12** | 详情（含 `extends`／`dimension_config`／`tag_bindings`，**原样呈现不假设结构**） |
| `createTemplate(body)` | **#13** | 写；400 含字段级原因／409 `code` 冲突 |
| `updateTemplate(code, body)` | **#14** | 写；版本递增 ＋ history |
| `activateTemplate(code)` / `deactivateTemplate(code)` | **#15／#16** | 写（**动作按 `update`**）；**幂等** |
| `listAnnotationTemplates(params)` | **#17** | 过滤 `template_code`／`scenario` |
| `getAnnotationTemplate(code)` | **#18** | 详情（含 `field_schema`） |
| `createAnnotationTemplate(body)` | **#19** | 写；**`template_code` 必填且归属须 `active`** |
| `updateAnnotationTemplate(code, body)` | **#20** | 写；**含 `template_code` 即改挂**（**不提供"解除归属"**） |
| `deleteAnnotationTemplate(code)` | **#21** | 写；**409 时展示关联标注条数** |
| `listLabels()` | **#22** | 只读（`action=list`；仅此一种） |
| **跨上游协作（非本版 22 端点）** | | |
| `assistReview(payload)` | **`llm_proxy` `/chat`** | 复核辅助（OpenLLM 通道，A-1410-01） |
| `submitReview(annotationId, body)` | **DPS 既有 review 端点** | 复核提交（`POST /portrait/annotations/{id}/review`） |

> **mock 真实化（DT-13）**：DPS 模块范围内**不得残留 mock 常量**（AC-13）；数据一律经上述方法。
>
> **方法总数**：**22 个（10 新增 ＋ 12 补代理）＋ 2 个跨上游协作方法**。`dps.ts` 既有 11 个方法**不改**。

### 3.2 状态与副作用

| 项 | 设计 |
|----|------|
| 页面状态 | **组合式函数**（页面内聚），不引入新全局 store（ADR-05） |
| 共享逻辑 | 抽取 `useAsyncState()`（加载／错误／空态）与 `useBasisTooltip()`（`basis` 折叠，ADR-06） |
| 缓存 | **不引入前端缓存层**（每次进入页面拉取；避免与后端口径分叉） |

---

## 4. 状态与错误呈现架构（DT-14）

| 层 | 职责 | 落点 |
|----|------|------|
| `core/api/http.ts` | 请求封装、超时、`request_id` 透传 | 既有，不改 |
| `core/api/error.ts` | **错误归一**：按 `code` 映射为可呈现模型 | 扩展映射表（新增 409／422 语义） |
| 页面 | 按归一模型渲染**空态／错误态／未启用态** | **12 页**统一样式（不改 tokens） |

**错误码呈现分工**：

| code | 呈现 | 页面 |
|:----:|------|------|
| 400 | 语义文案（如「该字段键不受支持」／**字段级校验原因**／**归属模板未激活**／**`extends` 深度超限**） | P-03／P-04／P-05／**P-09／P-10／P-11** |
| 403 | 「无权限执行」／「AI 通道未启用」 | 全部写操作页（含 **P-09~P-11**）／ P-08 |
| 404 | 「未找到」（含无谱系） | P-05／P-02／**P-09／P-10／P-11** |
| **409** | 「存在未复核候选，不得进入标签/画像路径」／「code 冲突未指定策略」／**「`code` 已存在」**／**「存在 N 条关联标注数据，禁止删除」** | P-08／P-04／**P-09（创建冲突）／P-10（删除被拒）** |
| 422 | 「包结构非法」（白名单校验） | P-04 |
| 503 | 「AI 适配器暂不可用」（**降级非阻塞**） | P-08 |
| 5xx／不可用 | 「服务暂不可用」＋ 重试（**不静默降级**） | 全部 |

---

## 5. 构建与产物

| 项 | 设计 |
|----|------|
| 构建 | 沿用既有 Vite 配置（**不改构建链**） |
| 产物 | `dist-v1.4.10` |
| 体积 | 无新依赖 ⇒ 体积增量应主要来自页面代码；Step 3 记录基线对比 |
| 兼容 | 沿用既有浏览器支持面 |

---

## 6. 与设计系统的关系

| 项 | 结论 |
|----|------|
| `tokens.css` / 设计系统 | **不改**（规划 §2.2 已排除视觉规范改动） |
| **原型一致性（强制）** | 原型 `doc/design/prototype/` **逐项照搬** `tokens.css` 的 `--ob-*` 变量 ＋ 模拟 **Element Plus** 组件视觉 ＋ 对齐 `AppLayout.vue` 布局（侧栏 220／64px ＋ 顶栏 56px ＋ 内容区）；实现时**不得偏离**（详见 UI 设计文档 §1.1） |
| **页面落点与命名** | 8 页落点 **`openbase-ui/src/modules/portrait/pages/`**，命名沿用既有 `Dps*View.vue` 风格（如 `DpsTemplateListView.vue`）；**不新建模块、不改既有页面** |
| 组件复用 | 优先复用既有基础组件；不足时**新增业务组件**（不改基础组件语义） |
| 无障碍 | 新增交互须满足 UIUX §6（键盘可达、`aria-expanded` 用于 `basis` 折叠、`prefers-reduced-motion`） |

---

## 7. 前端架构风险

| # | 风险 | 级别 | 缓解 |
|:-:|------|:----:|------|
| 1 | 8 页并发开发导致**状态处理不一致** | P2 | 统一 `useAsyncState()` ＋ 错误码映射表（§4） |
| 2 | P-08 跨两上游（DPS ＋ OpenLLM）**语义混淆** | P1 | UI 明确标识来源；`llm_proxy` 不可用时**仅降级辅助**（不阻断复核提交） |
| 3 | 回滚等写操作**误触** | **P1** | 二次确认四要素（UI 设计 §P-02）＋ 权限门禁结果呈现 |
| 4 | `basis` 折叠过深导致复核遗漏 | P2 | `tag_count=0` 等场景**强制展开**（ADR-06 风险缓解） |

---

## 8. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| **v1.2.0** | 2026-09-29 | FA-OpenBase-Dev | **D-1410-03 回写（G2 缺陷闭环 ＋ 页面 8 → 12）**：① **§2 路由表全量重写** —— 原将 P-01 写为 `#1 #2 #3`（实为导出／导入／版本对比）**撞号且语义错误**，现改为 **P-01↔#11·#12·#15·#16**，并新增 **P-09 画像模板新建／编辑（#12·#13·#14，`extends` 继承选择）／P-10 标注模板管理（#17·#18·#19·#21）／P-11 标注模板字段与归属（#12·#18·#20，**无"解除归属"按钮**）／P-12 标签体系查看（#21·#22）**；② **§3.1 方法表全量重写** —— 原编号系统性错位（`listTemplates`→#1 实为导出），现按 API 文档编号分「契约 10 新增」「补代理 12」两段列 **22 方法 ＋ 2 跨上游方法**；③ §4 页面数 8 → **12**；错误码分工补 **P-09~P-11** 与新增 409 语义（`code` 已存在／存在 N 条关联标注）；④ 声明既有画像 2 页不改。 |
| v1.1.0 | 2026-09-29 | FA-OpenBase-Dev | 按「原型必须与前端既有设计风格一致」要求增补 §6 两行强制约束：**原型一致性（照搬 `tokens.css` `--ob-*` 变量 ＋ 模拟 Element Plus 视觉 ＋ 对齐 `AppLayout.vue` 布局，禁止自创主题）**；**页面落点 `openbase-ui/src/modules/portrait/pages/`，命名沿用 `Dps*View.vue`，不新建模块、不改既有页面**。 |
| v1.0.0 | 2026-09-29 | FA-OpenBase-Dev | 初始创建（Step 2 §2.5b 产出）：**架构总览**（沿用 core／modules／pages 分层，标注本版扩展点）；**路由设计 8 条**（页面↔端点映射）；**数据层设计**（`dps.ts` 扩展 14 个方法，含 **AI 复核跨两上游**；mock 真实化；组合式函数承载页面状态，**不新增全局 store**）；**状态与错误呈现架构**（错误码映射表 **7 类 ＋ 兜底**）；**构建与产物**（不改构建链）；**与设计系统关系**（不改 tokens）；**风险 4 项**（2 项 P1）。状态 [Review]。 |

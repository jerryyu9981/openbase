# OpenBase 前端架构设计文档 - v1.4.11

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 文档版本 | v1.23.0 |
| 状态 | **[Approved]** |
| 版本号 | **v1.4.11**（公共功能域重组与统一页面骨架） |
| 作者 | FA-OpenBase-Dev |
| 创建日期 | 2026-09-29 |
| 更新日期 | 2026-10-23 |
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

## 8. 公共功能域重组与统一页面骨架（v1.4.11）

### 8.1 目标

1. 非业务专属的统一前端功能全部归集到「公共功能」域；
2. 公共功能内的业务模块开关决定对应模块页面/菜单是否展示（停用即不可见、直链不可达）；
3. 功能划分与页面排布统一到商用生产系统级（统一骨架、统一门禁、统一空态/加载/错误）。

### 8.2 信息架构（公共功能五域 + 业务模块）

```text
/（AppLayout）
├── 仪表盘 /dashboard
├── 公共功能（静态路由 /platform/**，权限码 + 模块依赖双门禁）
│   ├── 身份与权限    租户/角色/组织团队用户/工作空间/用户/记忆席位/注册找回/画像数据权限
│   ├── 平台配置与密钥 全局配置/模块开关/API 密钥/画像接口限流
│   ├── 可观测与审计   日志/测试记录/统一监控/GPU/用量/计费/服务发现/网关测试/成本/告警/画像系统监控
│   ├── AI 能力治理    提供商/模型分类/路由策略/熔断器/模型部署/下载/工具调用/AB 测试/Prompt 模板/实验
│   └── 开发者资源     文档/EdgeRouter/插件/画像 API 管理/知识库管理后台/知识库 API 控制台
├── 业务模块（动态装载，受模块开关控制）
│   ├── /openllm   模型管理/本地模型/模型对比/开源市场/收藏/AI 应用/Playground/对话/推荐/报表趋势
│   ├── /knowledge 知识库列表与详情/RAG 对话
│   ├── /memory    记忆列表/详情/搜索/会话/图谱/衰减/写入
│   └── /portrait  总览/列表/详情/搜索/标签/规则 ＋ **/portrait/dps/**（模板族/版本/预检/模板包/血缘/措施/评分/标注/标签体系）
└── /personal/settings
```

> v1.4.11 收口：DPS 模板化 12 页原为顶部 `/dps/**` 静态路由（无菜单项、不受模块开关约束），
> 已归位为画像模块的 `dps/*` 子路由（`/portrait/dps/**`），随 portrait 模块启停并进入模块导航；
> 旧 `/dps/**` 路径由 `legacyRedirects` 承接（9 条，其余子路径由父路径回退）。

上收清单（v1.4.11 实际迁移，`git mv` 保留历史）：

| 原位置 | 新位置 |
|---|---|
| `modules/openllm/pages/Providers.vue`、`Categories.vue`、`Routing.vue`、`DownloadManagerView.vue`、`ToolCallMonitorView.vue`、`AbTestView.vue`、`PromptTemplatesView.vue`、`PromptExperimentsView.vue`、`GenericPage.vue` | `pages/platform/governance/**` |
| `modules/portrait/pages/DpsPermissionView.vue` | `pages/platform/identity/` |
| `modules/portrait/pages/DpsRateLimitView.vue` | `pages/platform/config/` |
| `modules/portrait/pages/DpsMonitorView.vue` | `pages/platform/observability/` |
| `modules/portrait/pages/DpsApiManageView.vue` | `pages/platform/developers/` |
| `modules/knowledge/pages/KnowledgeAdminView.vue`、`KnowledgeConsoleView.vue` | `pages/platform/developers/` |

### 8.3 模块开关语义（即时生效）

- 后端契约不变：`PATCH /modules/{id}` 返回 `effective=next_login` 并写审计留痕；
- 前端在切换成功后执行 `moduleRegistry.reload(permissions)`：
  1. 重新拉取 `/modules` 并重建注册表（权限过滤）；
  2. `syncModuleRoutes(enabledIds)` 先 `router.removeRoute(id)` 卸载停用模块，再按目标集合重装启用模块；
  3. 侧栏「业务模块」分组随注册表即时增删。
- 公共功能域新增 `meta.dependsOn`：治理页声明所依赖的业务模块；模块停用时
  菜单叶子隐藏，直链导航被守卫拦到 `/forbidden`（与权限门禁同源）。
- 同步失败不回滚后端结果，仅提示“请刷新页面”（`console.warn` 留痕）。

### 8.4 统一页面骨架

新增 `src/components/page/`：

| 组件 | 职责 |
|---|---|
| `PageContainer.vue` | 页面外壳：统一纵向间距 + 页头 + 内容插槽 |
| `PageHeader.vue` | 标题/描述/返回/右侧操作区（`actions`）/标题旁元信息（`meta`） |
| `FilterBar.vue` | 筛选区：左侧条件插槽 + 右侧操作插槽，统一边框与内边距 |
| `EmptyState.vue` | 统一空态（描述 + 可选操作插槽） |

排布规范：页头 → 筛选区 → 内容卡（表格/卡片）→ 分页；主操作固定在页头右侧；
间距统一 16px；空态统一用 `EmptyState`；表格统一加 `ob-table-scroll`。

阶段一已套用：仪表盘、模块开关页。阶段二已套用：统一监控、统一日志。阶段三：公共功能五域 **37 页**全部套用
`PageContainer`。**阶段四（本轮收口）：四个业务模块 39 页全部套用**（openllm 11 / portrait 18（含 DPS 12）/
memory 7 / knowledge 3），全站合计 76 页共用同一页头与间距规范；`.page-toolbar` 由 20+ 份 scoped 规则
收敛为 `core/styles/layout.css` 中的**单份全局类**。

### 8.4.1 启动与首屏（生产级要求）

| 问题 | 处置 |
|---|---|
| 首帧导航等待期白屏（实测 32s） | `App.vue` 在 `route.matched` 为空时渲染启动骨架（`data-test="app-boot"`），不再白屏 |
| `bootstrapModuleRoutes` 阻塞 `app.mount` | 预热最多等待 2500ms，超时先挂载，守卫在导航阶段继续装载 |
| `/auth/me` 与 `/modules` 串行（各 ~8s） | 启动即 `registry.prefetch()` 并行预取模块清单；`init` 复用同一 Promise |
| 预热与守卫重复请求 | `loadMe` / `init` 均加在途去重（模块级 Promise） |
| 注册表加载失败导致路由启动异常 | 守卫内 try/catch，失败降级为空模块并允许导航（`console.warn` 留痕） |
| 注册表晚于导航就绪 | `init` 成功后立即 `syncModuleRoutes`，模块页随即可达 |

实测（本机 dev，后端 `/auth/me`、`/modules` 单次约 8s，并发时可达 15~35s）：

| 阶段 | 首屏表现 |
|---|---|
| 改造前 | 白屏 32.6s，控制台 `timeout of 15000ms exceeded` + `Unexpected error when starting the router` |
| 骨架 + 预热 2.5s 上限 | 骨架 2.8s 上屏（不再白屏），控制台 0 error |
| 并行预取 + 在途去重 + 清单缓存 | 骨架 2.8s；`/auth/me` 与 `/modules` 同时发起（起始差 0~2ms）；后端超时后仅重试 1 次 `/modules` |

**结论**：前端已完成其边界内的治理。8s 级耗时已由后端侧定位并处置（详见 §8.8），
改造后同一台机器实测热态：`/auth/me` 中位 91ms（44~124ms）、`/modules` 中位 81ms（38~150ms），
首屏不再依赖超时重试。

### 8.5 旧路径兼容

`core/router/legacyRedirects.ts` 在 v1.4.11 累计新增 28 条精确映射（`/openllm/providers`、`/openllm/downloads`、
`/openllm/routing/*`、`/openllm/prompt-*`、`/openllm/ab-tests`、`/openllm/tool-calls`、
`/portrait/{permissions,rate-limit,monitor,api-manage,reports,batch}`、`/knowledge/{admin,console}`、
`/dps/*` 共 9 条等），另加一条 `/dps/:pathMatch(.*)*` 前缀兜底（覆盖 `/:code/edit` 等动态子路径）；
函数式 redirect 统一保留 query/hash，禁 404。

**v1.12.0 补充（旧登录入口）**：`/login` 未在路由表注册，直访会触发首帧
`[Vue Router warn] No match found` 并由守卫兜底跳转（且可能生成 `redirect=/login` 自我回跳链）。
现于 `staticRoutes` 增加 `/login → /auth/login` 的顶层重定向（保留 query/hash），
解析阶段即命中；未登录访问落到 `/auth/login` 并保留显式 `redirect` 参数，已登录访问按守卫回落
`/dashboard`。回归用例见 `tests/router-nav.spec.ts` S6-T2-5（2 条）。

### 8.6 验证

| 项 | 结果 |
|---|---|
| `vue-tsc --noEmit` | 通过（0 错误，收口全量改动后复跑） |
| `vitest run --no-file-parallelism` | 21 文件 / **250 用例全通过**（串行执行，无超时；并行跑在宿主满载时会出现 3 条超时，属环境噪声）。**v1.8.0 代理超时改动后复跑仍为 250/250** |
| `vite build` | 构建成功（3079 modules transformed）；**v1.8.0 复跑成功**（`✓ built in 39.33s`） |
| 路由契约 | 菜单 ⊆ 路由、routes−菜单 ⊆ 白名单、旧路径全量可达（`nav-consistency` 21 条、`platform-ia` 21 条全通过） |
| **全页面走查** | `scripts/ui_e2e_all_services.mjs` 遍历 **77 页**：**PASS 77 / FAIL 0**（无 console error/warn、无 pageerror、无渲染兜底），逐页截图见 `doc/test/evidence/ui-preview/`（`index.html` 为预览页） |

### 8.7 遗留（阶段二之后）

- ~~页面级加载/错误态统一到 `useAsyncState` + 统一错误条（**观察项**：上游挂起时记忆列表会长时间停留在 loading，需客户端超时兜底）~~ —— **客户端超时兜底已落地（v1.8.0）**：代理类端点 8s 硬超时，见 §8.9 第 14 项；`useAsyncState` 统一仍为后续项；
- 面包屑与详情页页签规范落地；
- 4 个占位页（模型部署、链路追踪、预算管理、应用调用记录）待上游接口就绪后转真实页面，入口已挂在统一监控/治理域内；
- 环境前置：`Redis(6380)` / `Qdrant(6333)` 已纳入 `doc/tmp/start-all-services.ps1` 常驻编排（local 模式下起 `openmemory`/`openrag` 自动连带拉起）；**Neo4j 已补齐**——社区版 5.26.16 以 Windows 服务 `neo4j` 常驻（Bolt 7687 / HTTP 7474，认证开启，Auto 启动），详见《DevLogReport》v1.6.0 §2.9。**记忆模块 6 页已复跑：PASS 6 / FAIL 0**（降级态消失，截图见 `doc/test/evidence/ui-preview-memory/`），OpenMemory 启动故障的根因与修复见 §2.10。

### 8.8 后端 8s 级耗时的定位与处置（跨前后端）

前端首屏耗时问题溯源到后端两条鉴权接口，排查结论如下（证据与改动清单见
《OpenBase-DevLogReport-v1.4.11》§3）：

| 成分 | 实测 | 处置 |
|---|---|---|
| Redis 不可达（`6380` 连接超时） | 每次缓存调用阻塞 socket 超时，多调用叠加至 8s 级 | 缓存层加**熔断冷却**（失败即停用 300s，`OPENBASE_REDIS_COOLDOWN_SECONDS` 可调） |
| 同一请求内主体验证**双读**（中间件 + 依赖层） | 每请求多一次 `users` 读库（Redis 熔断后即每次落库） | 中间件标注 `verified_principal_subject`，依赖层同主体跳过重复校验 |
| 登录 bcrypt 校验 | 1.1~1.9s/次（`rounds=12`，本机 CPU 满载） | 保留强度；属可接受登录成本，不在热路径 |
| DB 连接池 | 未显式配置，长连接易失效 | `pool_size=10/max_overflow=20/pool_timeout=10/pool_recycle=1800/pool_pre_ping` |
| 宿主资源 | CPU 100%、可用内存 668MB/12GB、安全软件常驻 | 新建 PG 连接 0.6~6s、进程启动 1~16s → 抖动主因；**非应用缺陷**，需清理宿主负载 |

验收：改造后 `/auth/me`、`/modules`、`/tenants` 热态 P50 分别为 91 / 81 / 57ms，
`/health` 12ms；连续 8 次采样无 ≥1s 样本（宿主高负载时仍可能出现秒级离群值，已如实登记）。

### 8.9 公共域收口记录（缺陷修复与一致性对齐）

| # | 问题 | 处置 | 落点 |
|:-:|------|------|------|
| 1 | `记忆管理席位` 未声明 `dependsOn`，记忆模块关闭后仍显示 | 路由 + 菜单叶子补 `dependsOn: 'memory'`（双门禁） | `pages/platform/routes.ts`、`core/layouts/AppLayout.vue` |
| 2 | `gateway` 已迁入公共功能，但模块开关页仍提供可切换项（切换对前端无效，属误导） | 开关页对 `gateway` 只读处理：过滤出可切换列表，并给出「已迁入公共功能、页面常驻」提示 | `pages/platform/config/ModuleSwitchView.vue` |
| 3 | `providers/register` 为独立占位页，而提供商新增已是列表页内嵌对话框 | 下线该路由，旧直达链接收敛到 `/platform/governance/providers` | `pages/platform/routes.ts`、`core/router/legacyRedirects.ts` |
| 4 | 画像「分析报表 / 批量任务」复用列表组件，点击后与画像列表完全相同（假页面） | 下线两条路由与菜单项，旧链接回落到 `/portrait/list`，待上游专用接口后再成页 | `modules/portrait/index.ts`、`legacyRedirects.ts` |
| 5 | 记忆模块的 `ApiGateway.vue`、`MemoryMonitorView.vue` 已是死文件（路由早前迁出） | 删除，避免后续误引用 | `modules/memory/pages/` |
| 6 | 占位页文案停留在「v1.2.0 已规划」，且 3 条占位路由无任何入口 | 占位页改为统一样式的结果页（明确「未交付 + 上游依赖」）；在统一监控页提供链路追踪/预算管理/应用调用记录入口 | `pages/platform/governance/GenericPage.vue`、`observability/Monitoring.vue` |
| 7 | 公共域页面各自 `*-page` 私有布局（69 处） | 五域 37 页统一套 `PageContainer`，页头标题/描述集中定义 | `pages/platform/**` |
| 8 | DPS 模板化 12 页挂在顶部 `/dps/**` 静态路由：无菜单入口、不受模块开关约束 | 归位为画像模块 `dps/*` 子路由（`/portrait/dps/**`），进入模块导航并随 portrait 启停；旧前缀（含动态子路径）重定向承接 | `modules/portrait/index.ts`、`core/router/index.ts`、`legacyRedirects.ts` |
| 9 | `.page-toolbar` 在 20+ 页面各写一份 scoped 样式 | 收敛为 `core/styles/layout.css` 单份全局类（纵向间距交由 `PageContainer` 的 16px gap） | `core/styles/layout.css`、各页面 `<style>` |
| 10 | `modules/knowledge/pages/Settings.vue` 已无路由引用（`/knowledge/settings` 早已重定向到全局配置） | 删除死文件 | `modules/knowledge/pages/` |
| 11 | 业务模块 39 页仍为各自私有布局 | 全部套用 `PageContainer`（openllm 11 / portrait 18 / memory 7 / knowledge 3） | `modules/*/pages/**` |
| 12 | **模块页丢失全局侧栏**：模块路由以顶层路由挂载，进入任一业务模块页后左侧导航消失，无法回到公共功能 | `router.addRoute('root', ...)` 把模块路由挂到 AppLayout 之下，模块子导航渲染在内容区，侧栏/顶栏常驻 | `core/router/index.ts` |
| 13 | 知识库 API 控制台首屏触发 ECharts 警告（图表在未激活页签内初始化，容器尺寸为 0） | 增加尺寸守卫 + `watch(activeTab)` 在切到「性能监控」后再渲染 | `pages/platform/developers/KnowledgeConsoleView.vue` |
| 14 | 上游挂起时列表页长时间停留 loading（默认超时 15s，用户无反馈） | 代理类端点（`/memory-proxy/`、`/rag-proxy/`、`/dps-proxy/`、`/llm-proxy/`、`/gateway/`）超时收敛到 **8s**，让页面尽早进入「可重试」错误态；流式调用显式 120s 不受影响 | `core/api/http.ts` |

---

### 8.10 OpenMemory 前端对齐（v7.5.0~v7.8.0，v1.11.0）

**背景**：OpenMemory 在 v7.5.0~v7.8.0 完成异步图投影、删除一致性、检索质量控制与图链路指标；统一前端记忆模块此前仍使用 mock 图谱与有限检索策略，需对齐真实能力。

| 页面 | 变更 |
|---|---|
| 记忆图谱 `MemoryGraph.vue` | 移除 TD-13-18 mock 实体/关系与本地增删；改为 `GET /memory-proxy/graph/overview` 真实数据（`:Memory` / `:Entity` / `MENTIONS`），新增规模统计（记忆/实体/关系/待投影/死信）、实体显示开关、记忆节点点击进详情、空图与错误态 |
| 记忆搜索 `MemorySearch.vue` | 策略新增 `graph` / `temporal` / `fusion`；新增「命中方式」列（记忆命中 / 实体节点）与 `matched_entity`；孤立实体（`entity:*`）不提供详情入口；图谱策略显示语义说明 |
| 写入记忆 `MemoryWrite.vue` | 新增重要度滑杆（`metadata.importance`，默认 0.6），与标签合并为 metadata 一次提交；补充异步投影与分层说明 |
| 记忆列表 `MemoryList.vue` | 删除模式可选软删/硬删并透传 `mode`；类型筛选对齐 `persistent/session/episode`；删除提示说明图投影同步清理 |

**代理契约**：`GET /api/v1/memory-proxy/graph/overview?limit=120`（10~300）→ 上游 `GET /api/v1/graph/overview`，响应统一 `{code,message,data}` 信封，`data` 为 `{nodes, edges, stats}`；跨租户 fail-closed，图库不可用返回 503。

**兼容性**：仅新增只读端点与页面字段展示，不改变既有响应结构；旧 `/memory/*` 路由与 `legacyRedirects` 不变。

**验证**：`memory-graph-v180.spec.ts`（3 例）与 `memory-search-v180.spec.ts`（1 例）通过；`vue-tsc --noEmit` 通过；OpenBase `test_memory_proxy.py` 17 例通过（含 overview 透传）；真实 Neo4j overview 返回 200（20 记忆 + 27 实体、99 条 MENTIONS 边）。服务级浏览器走查：图谱页统计 `1011/1038/599/0/0`、渲染 247 节点/599 边；搜索页图谱策略命中 1 条且来源=graph、命中方式=记忆命中；写入页重要度滑杆（0~1，默认 0.60）正常；三页控制台 0 error。

### 8.11 开发代理上游不可达语义（v1.13.0）

**问题**：后端重启/未启动时，Vite `http-proxy` 对上游连接失败返回**空 body 的 500**，浏览器与日志会把「上游未就绪」误判为 OpenBase 服务端 5xx（`module registry init failed ... status code 500`）。

**设计**：

- `/api` 代理（`server` 与 `preview` 共用）注册 `error` 处理器，经 `src/core/api/devProxy.ts` 的 `handleDevProxyError` 统一输出 **503 + JSON**：`{code:"SYS_UPSTREAM_UNAVAILABLE", message:"OpenBase API 尚未就绪或不可达，请稍后重试", data:null}`。
- 响应头已发送时只结束响应体；响应已结束时不再写入；非 `ServerResponse`（socket）场景安全跳过。
- 与前端 `describeError` 的「5xx 可重试」呈现一致，同时保留「后端未起」与「后端内部错误」的可区分性。

**边界**：仅影响本地开发/预览代理，生产由 Nginx/网关承接；OpenBase `/api/v1/modules` 读路径的 DB 降级逻辑（回退内存注册表）保持不变。

**验证**：`tests/dev-proxy-v180.spec.ts` 4 例通过；后端停止时 `5173/api/v1/modules`、`/api/v1/auth/login` 均返回 503 JSON（修复前为空 500）。

### 8.12 OpenLLM 聚合通道与来源映射（v1.14.0）

**背景**：全栈功能审计（见《OpenBase-全栈后端能力缺口清单-v1.0.0》）发现 52 页无后端调用；其中「AI 能力治理」域的上游能力（providers/plugins/routing/monitoring 等）实际存在于 OpenLLM，但经 OpenBase 通用代理访问时统一返回 **401**。

**根因（两段）**：

1. 通用代理 `/api/v1/proxy/{system}/{path}` 出站来源固定为 `TARGET_SYSTEM_GENERIC`（`openbase-generic-proxy`），而下游 `TRUSTED_PROXY_SOURCES` 只登记各自代理名 → OpenLLM 判定为「非白名单来源携带身份头」，**忽略身份头 → 401**；
2. 身份头被采信后，OpenLLM 原生 `/api/v1/*` 走 `get_current_active_user_or_api_key` 双通道，**仍需要 `Authorization: Bearer <OpenLLM API Key>`**；通用代理此前不透传任何凭据 → **401「无法验证凭据」**。

**设计**：

- **来源按系统映射**：`openllm → openbase-llm-proxy`、`openrag → -rag-`、`openmemory → -memory-`、`dps → -dps-`，未知系统回落 generic。安全性不变——代理入口已完成 JWT/服务 Key 认证与权限校验，来源常量只表达「谁转发的」。
- **上游凭据注入**：仅 `system=openllm` 注入 `Authorization: Bearer <OpenLLM API Key>`，选 Key 规则复用 `llm_proxy._select_llm_api_key`（按出站 `X-Tenant-ID` 取租户级 Key，未命中回落全局 Key），保证单一事实源；其余系统不注入，避免越权携带 OpenLLM Key。
- **前端接入面**：新增 `src/core/api/governance.ts`，统一以 `/proxy/openllm/api/v1/<domain>` 访问，返回上游原生结构（非 OpenBase 信封）。
- **首批域**：`providers`（提供商管理）完成端到端真实化——列表/新增/编辑/删除/启停 + 模型数统计，假动作（随机延迟「测试连接」、随机「同步模型」）移除。

**边界**：

- OpenLLM 侧仍使用 `get_current_active_user`（仅 JWT）的路由（plugins/model-categories/routing/monitoring 等）即使凭据就绪也返回 401，属**上游授权依赖改造**，按缺口清单 R3~R5 分批推进；
- `local-models`、`models/favorites|compare`、`open-models/popular` 在 10s 代理超时内未返回（502），属上游耗时问题（R6）；
- API Key 通道解析出的是 **Key 所属用户**，非终端用户；终端身份由 `X-User-*` 头供下游审计。

**验证**：`tests/test_proxy_target_system_v190.py` 8 例（映射 4 组 + 未知回落 + 装配透传 + 凭据注入/不注入）；`tests/providers-v190.spec.ts` 4 例；55 条 proxy/protocol 相关后端用例通过；浏览器实测提供商页 3 张卡片、模型数 3、控制台 0 error；`PUT /providers/{id}` 等值更新 200。

### 8.13 A 类页面接线（R1，v1.15.0）

**范围**：缺口清单 R1——「后端已有端点、页面仍用 mock」的三页。原则：**不伪造成功**，后端不具备的能力显式降级并登记缺口。

| 页面 | 契约 | 设计要点 |
|------|------|----------|
| 用户管理 | `GET/POST /users`、`PUT /users/{id}`、`PUT /users/{id}/role`、`DELETE /users/{id}` | 后端返回**裸数组**（非信封）；`status` 为 `0/1`；`roles[]` 取首元素展示、分配走独立端点；新建必填 `display_name`；角色下拉使用五码标准集合（admin/org_admin/org_member/user/viewer）；内置 `admin` 禁止停用与删除 |
| API 密钥 | `GET/POST /auth/api-keys`、`DELETE /auth/api-keys/{raw_key}` | 列表不含明文与 id；创建响应一次性返回 `key`，仅本会话内存保存用于复制与吊销；其余历史记录「吊销」置禁用并说明原因（后端按明文定位）；移除后端不存在的模型权限/速率/过期字段 |
| EdgeRouter | `/proxy/openllm/api/v1/edge/{status,health,adapters,organizations,quotas/{org},audit/logs}` | 概览、组织、适配器、审计四类真实数据；组织新增/编辑与配额调整走真实 `POST/PUT`；适配器只读（注销影响运行态，需运维窗口）；配额以组织为维度，无组织时给引导而非空表 |

**新增模块**：`core/api/users.ts`、`core/api/apiKeys.ts`、`governance.ts#edgeApi`。

**边界与已知缺口**：

- ~~服务 Key 缺 `key_id` → 历史密钥无法前端吊销~~ **已在 R2（v1.16.0）闭环**：`ApiKeyOut.id` + `DELETE /auth/api-keys/by-id/{id}`；
- Edge 组织为 OpenLLM 进程内存存储，重启清空；
- 配额无组织时无数据（已给引导文案）；
- **上游并发缺陷规避**：OpenLLM 同步端点并发访问 `scoped_session` 会抛 `InvalidRequestError`（并发必有一路 500）。提供商页的模型数改为串行拉取 + 逐条容错；根因修复归 OpenLLM（缺口清单 §7 第 5 项 / R2）。

**验证**：`tests/r1-wiring-v191.spec.ts` 10 例；关联回归 4 文件 40 例；`vue-tsc --noEmit` 0 错误；密钥「创建 → 列表无明文 → 吊销」接口全链路；三页浏览器实测 0 error。

### 8.14 C 类列表补齐与服务 Key id 化（R2，v1.16.0）

**背景**：缺口清单 C 类——三个列表端点缺失（`GET /configs`、`/test-records`、`/test-runs` 均 405），服务 Key 列表无稳定 id 导致吊销必须依赖明文。

**后端契约（新增）**

| 端点 | 返回 | 说明 |
|------|------|------|
| `GET /api/v1/configs?prefix=&level=` | `{items:[{key,value,level}], total}` | key 并集 = DB ∪ 运行时 ∪ 代码默认值；`level` 为最高优先级来源级别 |
| `GET /api/v1/test-records?run_id=&case_id=&result=&skip=&limit=` | `{items,total,skip,limit}` | 倒序；`limit` 上限 500 |
| `GET /api/v1/test-runs?skip=&limit=` | `{items:[{id,title,scope,operator,created_at,record_count}],total}` | 供页面轮次下拉 |
| `DELETE /api/v1/auth/api-keys/by-id/{key_id}` | `{revoked:key_id}` | 未知 id → 404 `BIZ_404`；`ApiKeyOut` 增 `id` |

**前端接线**

- `core/api/configs.ts`（新）：`list/set/versions/rollback`；`core/api/testing.ts` 扩 `listRuns/listRecords`；`core/api/apiKeys.ts` 增 `revokeById`。
- 全局配置：列表 + 关键字/级别过滤 + 编辑（值按 JSON/布尔/数字解析）+ 版本抽屉 + 回滚 + 导入（逐条真实写入）/导出。
- 测试记录：轮次下拉（进入自动选最新一轮并加载 summary）+ 手填 run_id 兜底 + 开新一轮后刷新。
- API 密钥：吊销改 `by-id`，解除「历史密钥不可吊销」。

**跨仓修复（OpenLLM v1.9.2）**：`get_db` 由 `scoped_session` 改为每请求独立 Session，消除同步端点线程池下的跨线程会话复用（`InvalidRequestError`），并发 500 根因闭环。

**边界**：`GET /configs` 暂无分页（默认值较多时列表较长）；测试记录内存上限 5000 条。

### 8.15 B 类首批：双通道鉴权与插件/模型分类（R3，v1.17.0）

**问题**：OpenLLM `plugins`、`model_categories` 路由族依赖 `get_current_active_user`（JWT-only）或 `app.api.auth.get_current_user`，经 OpenBase 通用代理（API Key 通道）恒返 401，导致「插件管理」「模型分类」两页只能停留在 mock。

**上游改造（OpenLLM v1.9.3）**：

- `plugins.py` 8 处、`model_categories.py` 13 处依赖统一改为 `get_current_active_user_or_api_key`；
- 双通道语义：`Bearer sk-openllm-*` 走 API Key 通道，其余走 JWT 通道（复用既有 `get_gateway_identity` 分流规则）；
- 写操作仍受 `require_permission` 约束（plugins），model_categories 原本即“已认证即可写”，本次不额外放宽。

**前端接线**：

| 页面 | 端点 | 交互 |
|------|------|------|
| 插件管理 | `/plugins`（类型/状态过滤）、`/plugins/tools`、`/plugins/{id}/enable`、`/plugins/{id}/disable`、`/plugins/{id}/health`、`/plugins/register`、`DELETE /plugins/{id}` | 列表 + 工具清单 + 启停开关 + 注册 + 健康检查抽屉；系统插件禁删 |
| 模型分类 | `/model-categories/tree`、`/model-categories/{id}/models` | 分类树拍平后按维度（capability/scene/architecture/scale）出标签云，选中分类加载模型分页；维度切换自动选首个分类 |

**边界**：

- 空数据显示真实空态，前端不内置 mock；演示数据应来自 OpenLLM 种子脚本；
- 分类仅展示上游已有维度，缺少维度时给「该维度暂无分类」提示；
- 健康检查依赖上游插件运行时状态，异常时以错误提示呈现，不伪造指标。

**验证**：OpenLLM 新增 6 例 + 既有 34 例回归；前端 8 例；`vue-tsc` 0 错误；聚合端点 4/4 200（改造前 401）。

### 8.16 B 类第二批：观察域双通道与六页接线（R4，v1.18.0）

**问题**：观察域路由族（`monitoring/*`、`traces`、`alerts`、`budgets`、`usage`、`billing`、`billing_v2`）依赖 JWT-only，经通用代理（API Key 通道）恒返 401；成本、告警、用量、计费四页为「契约 mock」，链路追踪、预算管理仍是 `GenericPage` 占位。

**上游改造（OpenLLM v1.9.4）**：7 个路由文件共 46 处依赖改为 `get_current_active_user_or_api_key`；`monitoring.py` 的 `current_user.get("id")` 随依赖返回 ORM `User` 改为 `getattr`；`POST /billing/bills`、`POST /billing/plans` 保持 `require_permission(PERM_BILLING_WRITE)`，不因双通道放宽写权限。

**前端接线**：

| 页面 | 端点 | 交互 |
|------|------|------|
| 成本分析 | `/monitoring/costs`、`/monitoring/costs/optimization-suggestions`、`/budgets` | 一次取 model/provider/user 三维度本地切换饼图；预算列表 + 新建；优化建议只读展示 |
| 告警中心 | `/alerts/rules`（GET/POST/PUT/DELETE）、`/alerts`、`/alerts/{id}/resolve`、`/alerts/{id}/acknowledge` | 规则增删改查 + 启停；告警历史服务端分页 + 状态筛选；确认/解决 |
| 链路追踪（新建页） | `/monitoring/traces/statistics`、`/monitoring/traces`、`/monitoring/traces/{id}` | 统计卡 + 状态/模型筛选 + 分页 + Span 详情抽屉 |
| 预算管理（新建页） | `/budgets`、`/budgets/{id}/status` | 列表 + 新建 + 状态抽屉（剩余/预测/剩余天数） |
| 用量统计 | `/usage/summary`、`/usage/trends`、`/usage/detail` | 统计卡 + 趋势图 + 明细（最近 200 条页内筛选/分页）+ CSV 导出 |
| 计费 | `/billing/usage/statistics`、`/billing/quotas`、`/billing/bills`、`/usage/trends` | 统计卡 + 消费趋势 + 配额表 + 账单表 + 账单详情 JSON |

**API 客户端**：全部收敛在 `src/core/api/governance.ts` 的 `monitoringApi` / `alertsApi` / `budgetsApi` / `tracesApi` / `usageApi` / `billingApi`，统一走 `OPENLLM = '/proxy/openllm/api/v1'`，响应直取上游原生结构。

**边界**：

- 空数据展示真实空态，前端不内置 mock；
- 成本页移除「一键应用优化建议」（上游无应用端点），不做本地假成功；
- `monitoring_metrics.tenant_id` 列未写入，指标类端点暂为全局口径（缺口已登记）；`alerts`/`budgets`/`usage`/`billing`/`traces` 由上游按 `current_user.organization_id` 过滤。

**验证**：OpenLLM 新增 15 例 + R3 6 例回归；前端 17 例；`vue-tsc` 0 错误；前端全量 306 例通过；聚合端点与浏览器实测因 OpenLLM 无法启动待复核。

### 8.17 B 类第三批：治理与 RBAC 双通道与七页接线（R5，v1.19.0）

**问题**：治理与 RBAC 路由族（`roles`、`workspaces`、`virtual-keys`、`routing/semantic`、`routing/cascade`、`routing/circuit-breakers`、`routing/ab-tests`、`prompt-templates`、`prompt-experiments`、`prompt/assembly`、`tool-calls`）依赖 JWT-only，经通用代理（API Key 通道）恒返 401；相关七页为「契约 mock」。

**上游改造（OpenLLM v1.9.5）**：11 个路由文件统一改为 `get_current_active_user_or_api_key`；新增 `GET /roles/permissions/catalog` 权限目录（供角色权限分配选择）；`require_permission` 守卫本身已走双通道，角色写类端点权限档位不变。

**前端接线**：

| 页面 | 端点 | 交互 |
|------|------|------|
| 角色与权限 | `/roles`（GET/POST/PUT/DELETE）、`/roles/{id}`、`/roles/{id}/permissions`、`/roles/permissions/catalog` | 角色 CRUD + 启停；权限目录勾选保存；系统角色禁改/禁删 |
| 工作空间 | `/workspaces`（GET/POST/DELETE）、`/workspaces/{id}/members`、`/workspaces/{id}/resources`、`/virtual-keys`（GET/POST/rotate） | 列表/新建/删除 + 成员增删 + 资源统计；Virtual Key 创建/轮换（完整 Key 只显示一次） |
| 路由策略 | `/routing/semantic`（CRUD/启停/test/cache stats/clear）、`/routing/circuit-breakers`（列表/reset） | 语义路由 CRUD + 测试 + 缓存；熔断器仅重置（上游无手动开闭） |
| 工具调用监控 | `/tool-calls`（GET）、`/tool-calls/{id}` | 状态/工具名筛选 + 服务端分页；输入/输出详情 |
| Prompt 模板 | `/prompt-templates`（CRUD/versions/rollback/import） | 列表/新建/编辑/删除/版本/回滚/导入；系统模板只读 |
| Prompt 实验 | `/prompt-experiments`（list/create/start/complete/report/delete） | ≥2 变体创建；启动/完成；报表推荐 |
| A/B 测试 | `/routing/ab-tests`（list/create/pause/resume/complete/delete/report） | 流量拆分创建；暂停/恢复/完成；分组指标与显著性 |

**API 客户端**：新增 `rolesApi` / `workspacesApi` / `virtualKeysApi` / `routingApi` / `circuitBreakersApi` / `toolCallsApi` / `promptTemplatesApi` / `promptExperimentsApi` / `abTestsApi`，仍收敛于 `src/core/api/governance.ts`。

**边界**：

- 空数据展示真实空态，前端不内置 mock；
- 移除上游不存在的能力：熔断器「手动开启/关闭」、工具调用「取消单条调用」、A/B「版本/归档」、Prompt 模板「启用开关」；
- 成员添加按用户 UUID（上游无按用户名邀请端点）；系统角色/系统模板的保护由前端同步上游约束。

**验证**：OpenLLM 新增 30 例 + R4 15 例回归；前端 15 例；`vue-tsc` 0 错误；前端全量 321 例通过；聚合端点与浏览器实测因 OpenLLM 无法启动待复核。

### 8.18 D 类性能：本地资源超时治理与两页接线（R6，v1.20.0）

**问题**：`local-models` 的轻量探测（`/api/tags`、`/api/ps`）沿用 300s 读 / 10s 连接超时，Ollama 不可达时 GPU/本地模型页等待 10s；`open-models` 仍为 JWT-only；收藏列表与下载任务列表存在逐条回查（N+1）。

**上游改造（OpenLLM v1.9.6）**：

- `OLLAMA_PROBE_TIMEOUT`（read 5s / connect 2s）用于 `/api/tags`（列表/健康检查）与 `/api/ps`（状态/GPU）；拉取模型长任务超时不变；
- `open-models` 全部路由改 `get_current_active_user_or_api_key`；
- `get_favorites` 与 `get_all_download_tasks` 改为单次 `IN` 批量查询；下载任务额外批量补 `model_name`。

**前端接线**：

| 页面 | 端点 | 交互 |
|------|------|------|
| GPU 资源 | `/local-models/gpu-allocation/status`、`/local-models/gpu-info` | GPU 卡（利用率/显存/占用模型）+ Ollama 运行中模型；不可用时展示上游 `message` 降级提示 |
| 下载管理 | `/open-models/downloads`、`pause|resume|cancel-download`、`download`、`deploy` | 服务端分页/状态筛选；暂停/恢复/取消/重试/部署 |

**API 客户端**：新增 `localModelsApi` 与 `openModelsApi`，收敛于 `src/core/api/governance.ts`。

**边界**：

- 移除无上游数据源的 GPU 温度/功耗与随机趋势图，不做假数据；
- 上游无「删除下载任务」端点，页面不提供删除；
- 「重试」通过重新创建下载任务实现（无独立 retry 端点）。

**验证**：OpenLLM 新增 13 例；前端 7 例；`vue-tsc` 0 错误；前端全量 328 例通过；运行态耗时与聚合端点实测因 OpenLLM 无法启动待复核。

### 8.19 E 类产品裁定与五页收敛（R7，v1.21.0）

**裁定原则**：有真实端点且能形成闭环的页面落地；无端点或仅形态演示的页面收敛/不建设，并在页面显式说明，不以 mock 填充。

**落地页面**：

| 页面 | 数据源 | 说明 |
|------|--------|------|
| 仪表盘 | `/users`、`/proxy/openllm/api/v1/monitoring/dashboard` | 客户端聚合；单源失败显示「—」并提示 |
| 统一监控 | `/monitoring/dashboard`、`/alerts?status=firing` | KPI + 请求量/延迟双轴曲线 + 最新告警 |
| 个人设置 | `GET/PUT /auth/me`、`POST /auth/change-password` | 资料与密码；通知偏好显式未开放 |
| 模型部署（新建页） | `/open-models`、`/{id}/deploy|deploy-status|logs|stop` | 部署参数、状态与日志抽屉 |
| 画像系统监控 | `/dps-proxy/health` | 仅健康；指标/告警规则标注未开放 |

**OpenBase 后端契约**：`MeResponse` 扩展 `display_name/email/phone`；`PUT /auth/me` 仅更新传入字段并校验邮箱；`POST /auth/change-password` 校验旧密码与强度，成功后更新 `password_hash`。

**不建设/保留**：注册/找回密码、画像数据权限、画像接口限流、画像 API 管理（无端点）；应用调用记录、知识库 API 控制台、文档中心（保留现状）。

**验证**：OpenBase 后端 6 例；前端 9 例；`vue-tsc` 0 错误；前端全量 337 例通过；聚合端点与页面级实测因服务不可启动待复核。

### 8.20 OpenLLM 四页真实接线与监控口径（v1.10.0，v1.22.0）

**接线范围**（统一前端 `src/modules/openllm/pages/**`）：

| 页面 | API 层方法 | 端点 | 关键约束 |
|------|-----------|------|----------|
| 本地模型 | `localModelsApi.list/available/serviceStatus/pull/remove/start/stop/update`、`gpuInfo/gpuAllocation` | `/local-models`、`/available`、`/status`、`/pull`、`/{name}`(DELETE)、`/{name}/start|stop|update`、`/gpu-info`、`/gpu-allocation/status` | 运行态由 `gpu-info.running_models` 判定；拉取目标改为文本输入（避免空下拉在无数据时递归渲染） |
| 模型对比 | `openModelsApi.list` + `modelCompareApi.compare` | `/open-models`、`/models/compare` | 模型池取上游列表；对比结论读 `comparison.advantages`，2~4 个模型 |
| 开源市场 | `openModelsApi.list/startDownload` | `/open-models`、`/open-models/{model_id}/download` | 来源筛选为文本匹配；分页仅保留页码（移除页大小下拉） |
| 我的收藏 | `favoritesApi.list/folders/remove` + `openModelsApi.startDownload` | `/models/favorites`、`/models/favorite-folders`、`/models/{model_id}/favorite`(DELETE) | 分组来自 `folder_name`；下载复用开源模型下载端点 |

**API 层**：`src/core/api/governance.ts` 内 `localModelsApi` 扩展 8 个方法，新增 `favoritesApi`、`modelCompareApi` 与 `LlmLocalModelItem`/`LlmAvailableModel`/`LlmFavorite`/`LlmModelCompareResult` 类型。

**监控口径变化**（与后端同步）：统一监控的 `error_rate` 由 `错误行数 ÷ 请求行数` 改为 `Σerror.value ÷ Σrequest.value`，前端无需改动，但展示值会从虚高（29%~31%）回到真实量级。

**错误态**：四页均有加载态与错误提示条（`data-test` 定位），失败时不清空已有数据（`Promise.allSettled` 单源降级仅用于本地模型页三接口组合）。

**验证**：前端新增 8 例（`tests/r8-openllm-pages-v1100.spec.ts`）；前端全量 345/345；`vue-tsc` 0 错误；四页 mock 常量 0 处。

### 8.21 个人设置通知偏好（v1.10.1，v1.23.0）

**数据源**：`GET/PUT /api/v1/auth/notification-preferences`（OpenBase 自有端点，非代理）。

**表单结构**：

| 字段 | 控件 | 约束 |
|------|------|------|
| `in_app` / `email` / `webhook` | 开关 | 默认 站内=开、邮件/Webhook=关 |
| `webhook_url` | 输入框（仅 `webhook=true` 时显示） | 需 http(s)；启用 Webhook 时必填 |
| `events.alert/approval/system` | 复选 | 默认全开；未知键后端拒绝 400 |

**交互**：进入页面与资料并行加载（`Promise.allSettled` 语义的独立 try/catch，单侧失败不阻断另一侧）；保存前本地校验 Webhook 协议，保存后回填服务端返回值；错误条 `data-test="notify-error"`。

**禁则**：不在前端伪造通知渠道可用性；Webhook 仅为配置项，实际投递能力由后端另行建设（本版不承诺投递）。

**验证**：`tests/r9-notify-prefs-v1101.spec.ts` 4 例；前端全量 349/349；`vue-tsc` 0 错误。

## 9. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| **v1.23.0** | 2026-10-23 | 研发（AI 辅助） | 新增 §8.21：个人设置通知偏好真实读写（站内/邮件/Webhook + 事件开关，Webhook 协议校验）；前端全量 349 例通过。 |
| **v1.22.0** | 2026-10-23 | 研发（AI 辅助） | 新增 §8.20：OpenLLM 本地模型/模型对比/开源市场/我的收藏四页真实接线（0 mock）；同步监控错误率口径说明；前端全量 345 例通过。 |
| **v1.21.0** | 2026-10-23 | 研发（AI 辅助） | 新增 §8.19：R7 E 类产品裁定——仪表盘、统一监控、个人设置、模型部署、画像系统监控（健康）落地；OpenBase 新增资料更新与改密端点；其余 E 类页面不建设/保留；前端全量 337 例通过。 |
| **v1.20.0** | 2026-10-23 | 研发（AI 辅助） | 新增 §8.18：R6 D 类性能——Ollama 轻量探测改短超时、`open-models` 改双通道、收藏/下载任务 N+1 批量化；GPU 资源与下载管理两页接真实端点并移除 mock。 |
| **v1.19.0** | 2026-10-23 | 研发（AI 辅助） | 新增 §8.17：R5 B 类第三批——OpenLLM 治理与 RBAC 11 文件改双通道并新增权限目录端点；角色/工作空间/路由策略/熔断器/工具调用/Prompt 模板/Prompt 实验/A-B 测试七页（8 路由）接真实端点，移除假开闭/假调用链/假版本等动作。 |
| **v1.18.0** | 2026-10-23 | 研发（AI 辅助） | 新增 §8.16：R4 B 类第二批——OpenLLM 观察域 7 文件 46 处依赖改双通道；成本/告警/链路/预算/用量/计费六页接真实端点，链路与预算由 `GenericPage` 改为真实页；移除成本页假应用动作；登记指标表租户过滤缺口。 |
| **v1.17.0** | 2026-10-23 | 研发（AI 辅助） | 新增 §8.15：R3 B 类首批——OpenLLM `plugins`/`model_categories` 改双通道鉴权，插件管理（列表/工具/启停/注册/健康）与模型分类（树/标签云/分类模型分页）两页接真实端点并移除 mock。 |
| **v1.16.0** | 2026-10-23 | 研发（AI 辅助） | 新增 §8.14：R2 C 类列表补齐（`GET /configs`、`/test-records`、`/test-runs`）与服务 Key `id`/`by-id` 吊销；全局配置与测试记录两页接线；跨仓修复 OpenLLM `get_db` 并发缺陷。§8.13 的服务 Key 缺口标记闭环。 |
| **v1.15.0** | 2026-10-23 | 研发（AI 辅助） | 新增 §8.13：A 类三页接线（R1）——用户管理 `/users`、API 密钥 `/auth/api-keys`、EdgeRouter `/edge/**`；明确「不伪造成功」原则、字段映射与三项已知缺口（服务 Key 无 id、Edge 组织内存态、配额无组织引导）。 |
| **v1.14.0** | 2026-10-22 | 研发（AI 辅助） | 新增 §8.12：OpenLLM 聚合通道与来源映射——通用代理出站来源按被代理系统映射（修 401 根因）、仅 openllm 注入 API Key（修第二段 401）、新增 `core/api/governance.ts`，提供商管理页端到端真实化；同步缺口清单与后续轮次路线。 |
| **v1.13.0** | 2026-10-22 | 研发（AI 辅助） | 新增 §8.11：开发代理上游不可达时由空 500 改为 503 JSON（`SYS_UPSTREAM_UNAVAILABLE`），避免误判服务端故障；补 4 例单测与实测记录。 |
| **v1.12.0** | 2026-10-22 | 研发（AI 辅助） | §8.5 补充：新增 `/login → /auth/login` 顶层重定向，消除首帧 `No match found` 告警与 `redirect=/login` 自我回跳；补 S6-T2-5 两条回归用例并通过浏览器实测。 |
| **v1.11.0** | 2026-10-22 | 研发（AI 辅助） | 新增 §8.10：记忆模块对齐 OpenMemory v7.5.0~v7.8.0——图谱页接真实 `graph/overview`（替换 mock）、搜索页补图谱策略与命中语义、写入页补重要度分层、列表页补软/硬删除模式；含代理契约、兼容性与验证记录。 |
| **v1.10.0** | 2026-10-22 | 研发（AI 辅助） | **记忆模块降级态闭环**：§8.7 更新——OpenMemory 启动故障已定位（Qdrant 客户端 5s 默认超时 → `ReadTimeout`）并修复（超时可配置，默认 30s；OpenMemory 提交 `c73b7c1`），记忆模块 6 页复跑 **PASS 6 / FAIL 0**；细节见《DevLogReport》v1.6.0 §2.10。 |
| **v1.9.0** | 2026-10-22 | 研发（AI 辅助） | **环境前置补齐**：§8.7 更新——Neo4j 已以社区版 5.26.16 Windows 服务常驻（Bolt 7687 / HTTP 7474、认证开启、Auto），记忆模块降级态的根因已消除（细节见《DevLogReport》v1.5.0 §2.9）；`Redis/Qdrant` 维持编排脚本常驻结论不变。 |
| **v1.8.0** | 2026-10-22 | 研发（AI 辅助） | **请求超时兜底与本地基础设施编排**：① §8.9 新增第 14 项——代理类端点（memory/rag/dps/llm/gateway）超时由 15s 收敛到 **8s**，上游挂起时列表页尽早进入可重试错误态（流式调用 120s 不受影响）；② §8.7 关闭「loading 兜底」观察项，并把 `Redis(6380)`/`Qdrant(6333)` 纳入 `start-all-services.ps1` 常驻编排（新增 `TcpProbe` 探测与 local 模式依赖连带）；③ §8.6 复跑 `vitest` 250/250、`vite build` 成功。 |
| **v1.7.0** | 2026-10-22 | 研发（AI 辅助） | **全页面走查与两处走查缺陷修复**：① 走查 77 页（PASS 77/FAIL 0）并生成逐页截图与预览页；② §8.9 新增第 12~13 项——模块路由改挂 AppLayout 之下（修复业务模块页丢失全局侧栏）、知识库控制台 ECharts 隐藏页签初始化告警；③ §8.6 增加走查口径与结论；④ §8.7 登记环境前置（OpenMemory 依赖 Neo4j）与 loading 兜底观察项。 |
| **v1.6.0** | 2026-10-21 | 研发（AI 辅助） | **业务模块收口（阶段四）**：① §8.2 把 DPS 模板化 12 页从顶部 `/dps/**` 静态路由归位到画像模块 `/portrait/dps/**`（进入模块导航、随 portrait 启停）；② §8.4 业务模块 39 页全部套用 `PageContainer`，全站 76 页统一页头与间距；③ §8.5 累计 28 条精确重定向 + `/dps/:pathMatch(.*)*` 前缀兜底；④ §8.9 增补第 8~11 项（DPS 归位、`.page-toolbar` 全局化、删除 `knowledge/Settings.vue` 死文件、业务模块页骨架）；⑤ §8.7 遗留收窄为 `useAsyncState`、面包屑与 4 个占位页。 |
| **v1.5.0** | 2026-10-21 | 研发（AI 辅助） | **公共域收口（阶段三）**：① §8.4 公共功能五域 **37 页全部套用 `PageContainer`**；② 新增 §8.9 收口记录（7 项）——记忆席位补 `dependsOn`、gateway 开关只读化、`providers/register` 下线并收敛重定向、画像「分析报表/批量任务」假页下线、删除 2 个死文件、占位页统一为结果页并补入口；③ §8.7 遗留收窄为业务模块页（42 页）与 `useAsyncState` 统一。 |
| **v1.4.0** | 2026-10-21 | 研发（AI 辅助） | **阶段二推进 + 后端耗时收口**：① §8.4 补充阶段二已套用页面（统一监控、统一日志）与页头操作区上移口径；② 新增 §8.8「后端 8s 级耗时的定位与处置」——Redis 不可达熔断（冷却 300s）、主体验证请求内去重、连接池加固、宿主资源瓶颈（新建 PG 连接 0.6~6s）四项成分与验收数据；③ §8.4.1 结论回写为热态实测（`/auth/me` P50 91ms、`/modules` P50 81ms），删除「剩余 25s 由后端造成」的过期表述；④ §8.7 遗留按阶段二完成情况收窄。 |
| **v1.3.0** | 2026-10-21 | 研发（AI 辅助） | **v1.4.11 公共功能域重组与统一页面骨架**：① 新增 §8 信息架构（公共功能五域 + 业务模块），把提供商/路由/部署/下载/工具调用/AB 测试/Prompt 资产与 DPS 权限/限流/监控/API 管理、知识库管理后台/控制台共 15 个页面 `git mv` 上收至 `pages/platform/**`；② 模块开关改为**前端即时生效**（`moduleRegistry.reload` + `syncModuleRoutes` 卸载/重装路由），新增 `meta.dependsOn` 双门禁（菜单隐藏 + 直链 403）；③ 新增 `components/page/` 四件套页面骨架并在仪表盘/模块开关页落地；④ `legacyRedirects` 补 17 条旧路径；⑤ 验证：`vue-tsc` 0 错误、`vitest` 250/250、`vite build` 成功；⑥ 首屏治理：启动骨架 + 预热 2.5s 上限 + 模块清单并行预取 + `loadMe/init` 在途去重，消除实测 32s 白屏。 |
| **v1.2.0** | 2026-09-29 | FA-OpenBase-Dev | **D-1410-03 回写（G2 缺陷闭环 ＋ 页面 8 → 12）**：① **§2 路由表全量重写** —— 原将 P-01 写为 `#1 #2 #3`（实为导出／导入／版本对比）**撞号且语义错误**，现改为 **P-01↔#11·#12·#15·#16**，并新增 **P-09 画像模板新建／编辑（#12·#13·#14，`extends` 继承选择）／P-10 标注模板管理（#17·#18·#19·#21）／P-11 标注模板字段与归属（#12·#18·#20，**无"解除归属"按钮**）／P-12 标签体系查看（#21·#22）**；② **§3.1 方法表全量重写** —— 原编号系统性错位（`listTemplates`→#1 实为导出），现按 API 文档编号分「契约 10 新增」「补代理 12」两段列 **22 方法 ＋ 2 跨上游方法**；③ §4 页面数 8 → **12**；错误码分工补 **P-09~P-11** 与新增 409 语义（`code` 已存在／存在 N 条关联标注）；④ 声明既有画像 2 页不改。 |
| v1.1.0 | 2026-09-29 | FA-OpenBase-Dev | 按「原型必须与前端既有设计风格一致」要求增补 §6 两行强制约束：**原型一致性（照搬 `tokens.css` `--ob-*` 变量 ＋ 模拟 Element Plus 视觉 ＋ 对齐 `AppLayout.vue` 布局，禁止自创主题）**；**页面落点 `openbase-ui/src/modules/portrait/pages/`，命名沿用 `Dps*View.vue`，不新建模块、不改既有页面**。 |
| v1.0.0 | 2026-09-29 | FA-OpenBase-Dev | 初始创建（Step 2 §2.5b 产出）：**架构总览**（沿用 core／modules／pages 分层，标注本版扩展点）；**路由设计 8 条**（页面↔端点映射）；**数据层设计**（`dps.ts` 扩展 14 个方法，含 **AI 复核跨两上游**；mock 真实化；组合式函数承载页面状态，**不新增全局 store**）；**状态与错误呈现架构**（错误码映射表 **7 类 ＋ 兜底**）；**构建与产物**（不改构建链）；**与设计系统关系**（不改 tokens）；**风险 4 项**（2 项 P1）。状态 [Review]。 |

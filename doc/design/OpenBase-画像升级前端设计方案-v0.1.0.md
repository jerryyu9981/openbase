# OpenBase 画像升级前端设计方案

| 项 | 内容 |
|---|---|
| 文档编号 | OB-DESIGN-PORTRAIT-FE |
| 版本 | v0.1.0 |
| 状态 | [Review] |
| 适用系统 | openbase-ui（Vue 3 + Element Plus + Vite），画像/DPS 模块 |
| 关联文档 | 《OpenBase-画像命名与数据链路一体化设计 v0.2.0》 |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-22 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v0.1.0 | 2026-11-22 | 首次编制：命名中文化与编码自动生成、引入中心、任务中心的前端页面/组件/交互/API/测试设计 | AI 编码代理 |

## 1. 概述

### 1.1 目标

把后端 v0.2.0 方案落到前端，交付三部分：

1. **命名体验**：画像模块所有模板、标签、字段、维度、评分项默认显示中文；中文名输入后自动生成英文 code，可人工覆盖。
2. **引入体验**：新增「数据接入中心」，支持文件导入、数据源同步的任务化操作，含字段映射、校验预览、任务进度与错误行。
3. **任务可见**：新增「任务中心」，统一展示引入、标注、画像计算三类任务及触发来源，支持失败重试与 stale 画像重算。

### 1.2 范围

| 阶段 | 前端范围 |
|---|---|
| P1 | 命名中文化、code 自动生成、术语字典、历史缺名提示 |
| P2 | 数据接入中心（数据源/导入任务/同步任务）、字段映射、任务详情 |
| P3 | 任务中心（三段视图）、触发来源标识、计算任务重试、stale 重算入口 |

非范围：后端管线实现、调度器实现、权限模型重构、移动端适配。

## 2. 设计原则

1. **中文优先**：任何实体主展示为中文名；code 仅作次要信息（灰色副标题/悬停/复制）。
2. **默认正确**：新建表单 code 自动生成且只读，用户无需理解编码规则；需要时可显式开启手动覆盖。
3. **任务化可见**：引入、标注、画像计算都以「任务」呈现，有状态、进度、错误与重试。
4. **不阻断主流程**：AI 适配器缺失、映射失败、权限不足均降级为人工路径，不出现死路。
5. **渐进披露**：列表页只保留关键列；映射、错误行、触发链等细节放抽屉/详情页。

## 3. 现状与改造清单

| 页面/组件 | 现状 | 改造 |
|---|---|---|
| `DpsTemplateListView.vue` | 模板列已用 `NameCodeLabel`；维度副标题 `dim.code`、健康区 `BLOCK` | 维度改中文名主显；`BLOCK`→「阻断」；新增「中文名缺失」筛选 |
| `DpsTemplateWorkbenchView.vue` / `DpsTemplateEditView.vue` | `code` 与 `name` 双输入，code 必填且不可改 | code 改为自动生成 + 手动覆盖；`name` 必填并中文校验提示 |
| `DpsAnnotationTemplateView.vue` / `DpsAnnotationFieldView.vue` | 模板已用名称组件；字段以 `key` 为主 | 字段增加中文名主列 + key 副显；新建字段自动生成 key |
| `DpsAnnotationWorkbenchView.vue` | 队列、字段、审核均已可用 | 字段标签改中文名；新增「由引入生成」来源标识与筛选 |
| `DpsTagSystemView.vue` | `data.code` 直接展示 | 标签分类/标签值改中文名主显；code 进 tooltip |
| `DpsScoringConsistencyView.vue` | `{{ row.code }}` 直接展示 | 改名称主列，code 次列 |
| `DpsScoringTypeView.vue` / `DpsMeasureView.vue` | 部分英文枚举 | 枚举中文化，名称主显 |
| `Tags.vue`（标签管理） | 分类名称已是中文 | 标签值与 code 统一名称组件；新增搜索同时匹配 name/code |
| 新增：数据接入中心 | 无页面（后端接口亦为半成品） | `/portrait/dps/ingest`：数据源 / 导入任务 / 同步任务三 Tab |
| 新增：任务中心 | 无统一视图 | `/portrait/dps/task-center`：引入 / 标注 / 画像计算三 Tab |

## 4. 信息架构与路由

### 4.1 路由（`src/modules/portrait/index.ts`）

```ts
{ path: 'dps/ingest', name: 'dps-ingest', component: () => import('./pages/DpsIngestCenterView.vue'), meta: { title: '数据接入中心' } },
{ path: 'dps/ingest/tasks/:id', name: 'dps-ingest-task-detail', component: () => import('./pages/DpsIngestTaskDetailView.vue'), meta: { title: '引入任务详情' } },
{ path: 'dps/task-center', name: 'dps-task-center', component: () => import('./pages/DpsTaskCenterView.vue'), meta: { title: '任务中心' } },
```

### 4.2 菜单（`navItems` 新增分组，置于「标签」之前）

```ts
{
  label: '数据接入',
  items: [
    { path: '/portrait/dps/ingest', title: '数据接入中心' },
    { path: '/portrait/dps/task-center', title: '任务中心' },
  ],
}
```

菜单顺序体现链路：**接入 → 标签/标注 → 画像模板 → 画像结果**。

### 4.3 页面布局

- **数据接入中心**：顶部主操作「上传文件导入」「新建数据源」；Tab①数据源（表格：名称/类型/状态/最近同步/操作）、Tab②导入任务（表格：文件名/格式/状态/成功/失败/创建人/时间）、Tab③同步任务（数据源/模式/周期/下次执行/状态）。
- **引入任务详情**：左侧进度与统计卡，右侧错误行表格（行号/字段/原因），顶部「重试失败行」「导出错误 CSV」。
- **任务中心**：三 Tab 共用任务表格骨架（类型/对象/触发来源/状态/耗时/操作），顶部筛选：时间范围、状态、触发来源。

## 5. 组件设计

### 5.1 `NameCodeLabel` v2（升级现有组件）

```ts
props: {
  name?: string
  code?: string
  nameSource?: 'manual' | 'auto' | 'fallback'
  showCode?: 'auto' | 'always' | 'never'   // 默认 auto：两者不同才显示
  size?: 'sm' | 'md'                        // 表格用 sm，详情用 md
  copyable?: boolean                        // 悬停显示复制 code
}
```

渲染规则：

| 场景 | 展示 |
|---|---|
| name 非空 | 主：name；次：code（灰色小字，可复制） |
| name 空、code 非空 | 主：`待补中文名`（灰色斜体，附 tooltip code）；点击跳转编辑 |
| 两者皆空 | 主：`—` |
| name === code | 只显示一次 |

### 5.2 `CodeField`（新增，`src/modules/portrait/components/CodeField.vue`）

```ts
props: {
  name: string                 // 中文名，用于生成
  modelValue?: string          // 当前 code
  existingCodes?: string[]     // 本地预校验集合（可选）
  disabled?: boolean           // 编辑态只读
}
emits: { 'update:modelValue': [string]; conflict: [string] }
```

行为：

1. `name` 变化后 300ms 防抖生成 code（`useCodeFromName`）。
2. 默认只读，右侧显示「手动覆盖」链接；点击转为可编辑，并保留「恢复自动」。
3. 格式校验：`^[a-z][a-z0-9_]{1,63}$`；失焦与提交前双校验。
4. 冲突：本地命中 `existingCodes` 或后端 409 → 红框 + 「编码已存在，请修改名称或手动覆盖」。

### 5.3 `useCodeFromName`（新增，`src/modules/portrait/composables/useCodeFromName.ts`）

```
中文名 → trim → 去标点/空白 → pinyin-pro 全拼（非中文保留字母数字）
      → 小写 → 非 [a-z0-9] 转 "_" → 合并连续 "_" → 去首尾 "_"
      → 截断 64 → 唯一化（_2/_3...）
```

示例：`犯罪记录` → `fan_zui_ji_lu`；`犯罪记录（补充）` → `fan_zui_ji_lu_bu_chong`；重码 → `fan_zui_ji_lu_2`。

### 5.4 `TermSelect`（新增）

远程搜索下拉，`keyword` 同时匹配 `name`/`code`；选项渲染 `NameCodeLabel`；选中回传 `{ code, name }`。用于标签、模板、评分项的选择器。

### 5.5 `TaskStatusTag` / `TriggerSourceTag`（新增）

| 状态 | 文案/颜色 |
|---|---|
| queued | 排队中（info） |
| running | 执行中（primary，带 loading） |
| success | 成功（success） |
| partial | 部分成功（warning） |
| failed | 失败（danger） |
| retrying | 重试中（warning） |

触发来源：`approval`→审核通过、`ingest`→数据引入、`schedule`→定时任务、`manual`→手动刷新（统一 `TriggerSourceTag`）。

### 5.6 `MappingTable`（新增，导入向导第二步）

- 左列「源字段」（文件表头），右列「标准字段」（下拉，必选项），自动按中文表头/同名列匹配。
- 必填字段未映射时禁止下一步；支持「保存为映射模板」。

### 5.7 `IngestTaskDrawer` / `DpsIngestTaskDetailView`

任务详情抽屉用于列表页快速查看；独立详情页承载错误行、重试与导出。

## 6. 关键交互

### 6.1 新建模板（P1）

```
输入中文名 → 300ms 后 code 自动填充（只读）
  ├─ 无冲突 → 「保存」可用
  └─ 冲突   → 红框提示，提供「手动覆盖」
保存成功 → 跳转工作台，顶部提示「编码已自动生成：fan_zui_ji_lu」
```

### 6.2 文件导入（P2）

```
上传（CSV/XLSX/JSON，≤20MB）
 → 解析预览（前 20 行 + 列识别）
 → 字段映射（自动匹配，缺失必填项阻断）
 → 校验报告（总数/有效/缺失必填/重复）
 → 执行（可选「仅校验不写入」dry_run）
 → 生成任务 → 详情页轮询进度 → 完成后可查看错误行/导出
```

### 6.3 数据源同步（P2）

```
新建数据源（HTTP / 数据库 / 文件目录）→ 测试连接
 → 建同步任务（全量/增量 + 周期：手动/每日/自定义 cron）
 → 「立即同步」生成任务 → 任务中心可见
```

### 6.4 标注与画像（P3）

- 引入生成的人工任务进入现有作业台「待处理」，队列增加「来源=引入」标签与筛选。
- AI 候选复用 `AI 候选复核` 页，增加「批次」维度。
- 审核通过后，画像页顶部显示「已触发增量重算」提示；任务中心可查 `trigger_source=approval`。
- 任务中心「画像计算」Tab 对 stale 画像提供「重新计算」批量操作。

## 7. 数据层与 API 契约（前端）

### 7.1 新增/变更接口（经 openbase 代理 `/api/v1/dps-proxy`）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/ingest/preview` | 上传文件解析预览（multipart，返回列/样例/建议映射） |
| POST | `/ingest/execute` | 提交导入（文件或数据源任务），返回 `task_id` |
| GET | `/ingest/tasks` | 任务列表（type/status/时间分页） |
| GET | `/ingest/tasks/{id}` | 任务详情（进度、错误行、统计） |
| POST | `/ingest/tasks/{id}/retry` | 重试失败行 |
| GET | `/ingest/tasks/{id}/errors.csv` | 导出错误行 |
| GET/POST | `/datasources` | 数据源列表/新建 |
| POST | `/datasources/{id}/test` | 测试连接 |
| POST | `/datasources/{id}/sync` | 立即同步 |
| GET | `/calc-tasks` | 画像计算任务列表 |
| POST | `/calc-tasks/{id}/retry` | 重试计算任务 |
| GET/PUT | `/config/ingest-policy` | 标注/画像触发策略 |

模板创建接口变更：`code` 可选；`name` 必填。

### 7.2 类型（`src/core/api/dps.ts` 扩展）

```ts
export type TaskStatus = 'queued' | 'running' | 'success' | 'partial' | 'failed' | 'retrying'
export type TriggerSource = 'approval' | 'ingest' | 'schedule' | 'manual'
export interface IngestTask { id: string; type: 'import' | 'sync'; format?: string; status: TaskStatus; total: number; processed: number; success: number; failed: number; created_at: string; finished_at?: string; trigger_source: TriggerSource }
export interface MappingItem { source: string; target: string; required: boolean }
export interface Datasource { id: string; name: string; kind: 'http' | 'db' | 'file'; status: 'ok' | 'error'; last_sync_at?: string }
export interface CalcTask { id: string; person_id: string; template_code: string; trigger_source: TriggerSource; status: TaskStatus; retry_count: number; last_calc_at?: string }
```

### 7.3 错误码映射

| code | 前端表现 |
|---|---|
| `BIZ_ENTITY_CODE_CONFLICT`(409) | CodeField 红框提示 |
| `PARAM_NAME_REQUIRED`(400) | name 输入框下方提示 |
| `BIZ_INGEST_MAPPING_INVALID`(400) | 映射步骤阻断，标红缺失项 |
| `BIZ_INGEST_TENANT_MISSING`(400) | 顶部 Alert「请先选择租户」 |
| 403 | 页面级空态「无权限，请联系管理员」 |

## 8. 文案与术语规范

- 新增 `src/core/i18n/portraitTerms.ts`：枚举 → 中文映射（任务状态、触发来源、健康度、标注状态、来源优先级）。
- 术语表（统一用词）：模板族 / 标注模板 / 标注字段 / 维度 / 评分项 / 标签分类 / 标签值 / 说明 / 引入 / 同步。
- 禁止在模板中硬编码英文枚举；缺失词条时显示原值并在开发环境 console warn（不进入生产 warn）。

## 9. 权限与多租户

- 使用 `auth.hasPermission()`：`dps:view`（只读）、`dps:annotate`（标注/复核）、`dps:manage`（模板/数据源/任务重试）。
- 按钮级控制：无权限时隐藏写操作；页面级 403 显示空态。
- 所有列表请求携带租户上下文；切换租户后清空任务筛选与缓存。

## 10. 异常、空态与降级

| 场景 | 表现 |
|---|---|
| 列表加载 | 骨架屏（表格 8 行） |
| 无数据 | 空态 + 主操作引导（如「上传第一个文件」） |
| 名称缺失 | 「待补中文名」+ 编辑跳转，不阻塞 |
| AI 适配器缺失 | 标注模式自动降级「纯人工」，页面提示 |
| 任务失败 | 详情页错误行 + 重试按钮；列表状态 danger |
| 轮询超时 | 停止轮询，显示「刷新」按钮，不重复弹错 |

## 11. 性能

- 任务列表 10s 轮询，详情 2s；页面隐藏（`visibilitychange`）暂停轮询；进入终态自动停止。
- 导入预览仅解析前 20 行；大文件上传使用进度条与分片（P2 可先单请求）。
- 列表超过 200 行启用分页（默认 20/页），不做前端全量渲染。
- code 生成防抖 300ms；搜索 400ms 防抖。

## 12. 可访问性与响应式

- 所有表单 label 与输入关联；错误提示使用 `aria-invalid` 与 `role="alert"`。
- 任务状态同时用文字 + 颜色，不仅靠颜色区分。
- 最小可用宽度 1280；表格列过多时横向滚动，操作列固定右侧。

## 13. 兼容与灰度

- 新增页面通过模块开关控制可见（portrait 模块内）。
- `showCode` 默认 `auto`，老页面行为不变；新页面统一 `sm` 尺寸。
- 引入/任务中心入口可通过 feature flag 隐藏，后端未就绪时不影响现有页面。

## 14. 测试设计

| 层级 | 用例 |
|---|---|
| Vitest | `useCodeFromName`（中文/英文混合/标点/超长/冲突）、`NameCodeLabel`（4 种渲染）、`CodeField`（自动/覆盖/冲突）、`MappingTable`（自动匹配/必填阻断）、`TaskStatusTag` |
| Playwright | `naming-autogen.spec`（新建模板不填 code 成功）、`ingest-import.spec`（上传→映射→执行，mock 接口）、`task-center.spec`（三段 Tab/重试）、关键页回归（中文主显、无 console warn） |
| 视觉 | 3 个新页面 1440×900 基线截图 |
| 可访问性 | 表单 label、错误提示、键盘可达 |

## 15. 分阶段交付与验收

| 阶段 | 交付 | 验收 |
|---|---|---|
| P1 | 组件升级、术语字典、模板/字段/标签/评分项中文化、code 自动生成 | 无裸 code 主展示；不填 code 可保存；冲突提示正确；vitest 与关键页 E2E 通过 |
| P2 | 数据接入中心、上传向导、映射、任务详情、错误导出 | 上传→映射→执行全流程可走通；重复导入幂等；错误行可导出 |
| P3 | 任务中心三段视图、触发来源、重试、stale 重算 | 三类任务可查；重试生效；stale 画像可批量重算 |

## 16. 文件级改造清单

| 类型 | 文件 |
|---|---|
| 新增页面 | `DpsIngestCenterView.vue`、`DpsIngestTaskDetailView.vue`、`DpsTaskCenterView.vue` |
| 新增组件 | `CodeField.vue`、`TermSelect.vue`、`TaskStatusTag.vue`、`TriggerSourceTag.vue`、`MappingTable.vue`、`IngestTaskDrawer.vue` |
| 新增组合式 | `useCodeFromName.ts`、`useTaskPolling.ts` |
| 升级组件 | `components/common/NameCodeLabel.vue` |
| 改造页面 | `DpsTemplateWorkbenchView.vue`、`DpsTemplateEditView.vue`、`DpsTemplateListView.vue`、`DpsAnnotationFieldView.vue`、`DpsAnnotationTemplateView.vue`、`DpsAnnotationWorkbenchView.vue`、`DpsTagSystemView.vue`、`DpsScoringConsistencyView.vue`、`DpsScoringTypeView.vue`、`DpsMeasureView.vue`、`Tags.vue` |
| 路由/菜单 | `src/modules/portrait/index.ts` |
| API/类型 | `src/core/api/dps.ts` |
| 术语 | `src/core/i18n/portraitTerms.ts` |
| 测试 | `tests/*.spec.ts`（组件）、`tests/e2e/naming-autogen.spec.ts`、`tests/e2e/ingest-import.spec.ts`、`tests/e2e/task-center.spec.ts` |

## 17. 风险与开放问题

| 编号 | 风险/问题 | 处置 |
|---|---|---|
| FR-1 | 拼音生成 code 可读性差或重码 | 允许手动覆盖；冲突后缀；高频实体维护别名 |
| FR-2 | 后端接口未就绪导致新页面空转 | feature flag + 明确空态；接口按本设计先行 mock |
| FR-3 | 任务轮询造成请求压力 | 分层轮询 + 页面隐藏暂停 + 终态停止 |
| FR-4 | 历史数据缺中文名影响观感 | 统一「待补中文名」样式，配合后端补名脚本 |
| FR-5 | 权限码未定 | 先按 `dps:view/annotate/manage` 约定，联调时对齐后端权限目录 |

# OpenBase 画像命名与数据链路一体化升级方案

| 项 | 内容 |
|---|---|
| 文档编号 | OB-DESIGN-PORTRAIT-UNIFIED |
| 版本 | v1.0.0 |
| 状态 | [Review] |
| 适用系统 | OpenBase（openbase-ui 画像模块）、DPS、OpenLLM 回写链路 |
| 替代文档 | 《画像命名与数据链路一体化设计 v0.3.0》《画像升级前端设计方案 v0.2.0》（已归档） |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-22 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-22 | 合并前后端两份方案；新增方案评估、多画像生产系统适用性评估、生产化差距与演进路线 | AI 编码代理 |

## 1. 摘要（一页看懂）

| 维度 | 结论 |
|---|---|
| 命名 | 中文名默认主显；英文 code 由中文自动生成（拼音），可人工覆盖，创建后不可改 |
| 引入 | 对外 **5 个入口**、内部 **1 条 `ingest_pipeline`**、**3 类适配器**（实时回写 / 批量 / 人工） |
| 调度 | 独立 `dps-worker`（APScheduler + PG advisory lock + 心跳）；cron/interval 可配，支持重叠、错过、重试、熔断 |
| 标注 | **3 种模式**：纯人工、AI 预标注+人工复核、规则高置信自动（白名单）；引入只建任务、不自动通过 |
| 画像 | **4 种触发**：审核通过增量（默认）、引入即算（默认关）、定时增量/全量（建议开增量）、手动刷新 |
| 前端 | 新增数据接入中心、任务中心；组件化命名/编码/调度/任务状态；任务状态与触发来源全链路可见 |
| 总体判断 | 作为「单主体（person）+ 多模板」生产系统**适合**，需补齐 6 项生产化能力；作为「多主体类型」统一平台**需先做主体模型泛化** |

## 2. 背景、目标与范围

### 2.1 背景

画像模块存在两类断点：

1. **命名**：部分页面裸展示英文 code；code 全靠手填，创建后不可改，运营理解成本高。
2. **链路**：批量导入与数据源同步只拉取/校验、不落库；标注不随引入产生；画像只在审核通过或手动调用时计算，无定时调度与任务补偿。

### 2.2 目标

| 编号 | 目标 | 可验证结果 |
|---|---|---|
| G-1 | 中文默认展示 | 页面无裸 code 主展示；缺名显示「待补中文名」 |
| G-2 | 中文名自动生成英文 code | 新建不填 code 可提交；冲突有明确提示 |
| G-3 | 引入可落库并按策略生成标注任务 | 导入/同步后 profile 与标注任务可查询 |
| G-4 | 引入与画像可定时、可补偿 | cron/interval 生效；重启任务续跑 |
| G-5 | 全链路任务可见 | 引入/标注/画像三类任务可查、可重试 |

### 2.3 范围与非目标

- 范围：DPS 后端引入/标注/画像链路、调度 worker、openbase-ui 画像模块。
- 非目标：不重构评分算法；不改已有 `template_code` 语义；不引入消息中间件；本期不做多主体类型泛化（列为 P0 生产化前置）。

## 3. 现状与差距

### 3.1 命名

| 现状 | 证据 |
|---|---|
| `NameCodeLabel` 已实现 name 优先、缺名回退 code | `openbase-ui/src/components/common/NameCodeLabel.vue:L11-L35` |
| 模板列表、标注模板、标签绑定已接入 | `DpsTemplateListView.vue:L131-L134`、`DpsAnnotationTemplateView.vue:L34`、`TagBindingTable.vue:L22-L29` |
| 仍裸展示英文：评分一致性、标签体系、维度副标题、健康区 `BLOCK` | `DpsScoringConsistencyView.vue:L92`、`DpsTagSystemView.vue:L57`、`DpsTemplateListView.vue:L420`、`L159-L168` |
| code 与 name 双输入、code 创建后不可改、无生成逻辑 | `DpsTemplateEditView.vue:L14-L22`、`L188-L198` |
| 后端模板已有 `name` / `name_source` | `openbase-ui/src/core/api/dps.ts:L62-L90` |

### 3.2 引入

| 方式 | 行为 | 落库 | 证据 |
|---|---|---|---|
| OpenLLM 抽取回写 | 抽取 memory/rag/profile → 写回队列 → DPS 计算/写入 | 是 | `OpenLLM/backend/app/api/writeback.py:L218`、`edgerouter/adapters/dps_client.py:L183-L233` |
| 数据源同步 | 拉取+清洗+计数 | **否** | `DPS/src/engines/datasource_engine.py:L201-L243` |
| 批量导入 | 预览/执行 | **否**（「模拟」） | `DPS/src/engines/batch_engine.py:L169-L171` |
| 身份生命周期事件 | 阻断集/权限绑定 | 仅状态 | `DPS/src/engines/identity_event_engine.py:L322+` |
| 人工/AI 标注 | 工作台提交、AI 候选 | 是 | `annotation_template_engine.py:L787-L825`、`ai_annotation_engine.py:L138-L220` |

### 3.3 标注与画像

- 标注：仅人工提交或 AI 候选（`pending` 复核），**不随引入产生**。
- 画像：审核通过 → 标签联动 → 去抖 5s 入队 → `BackgroundTasks` 计算；以及 `POST /portrait/calculate` 手动/上游调用。
- **无内置定时器**；`portrait_calc_task` 无常驻 worker，重启可能遗留 pending。

### 3.4 差距清单

| 编号 | 差距 | 影响 |
|---|---|---|
| GAP-1 | 引入不落库 | 配了数据源也不出画像 |
| GAP-2 | 引入与标注无编排 | 数据到位仍需逐条人工建标注 |
| GAP-3 | 无定时增量/全量 | 未被事件覆盖的画像长期 stale |
| GAP-4 | 计算任务无补偿 | 重启丢任务 |
| GAP-5 | 任务状态存内存 | 不可审计、重启丢失 |
| GAP-6 | code 手填 + 裸展示 | 命名不统一 |
| GAP-7 | **主体模型 person 中心** | 多画像类型（企业/设备/内容）无法直接复用 |

## 4. 总体架构

```
[5 入口]  实时回写(OpenLLM) | 身份事件 | 文件导入 | 数据源同步 | 人工/API
              │                  │            │            │            │
              └──────────── 3 类适配器 ───────┴────────────┘            │
                                   │                                  │
                         ┌─────────▼──────────┐                       │
                         │   ingest_pipeline  │◄──────────────────────┘
                         │ 读取→映射→校验     │
                         │ →profile upsert    │
                         │ →生成标注任务      │
                         │ →画像入队          │
                         │ →任务留痕          │
                         └──────┬──────┬──────┘
                                │      │
                    ┌───────────▼─┐  ┌─▼──────────────┐
                    │ annotation  │  │ portrait_calc  │
                    │   task      │  │     task       │
                    └──────┬──────┘  └────┬───────────┘
                           │ 审核 approved │
                           └──────┬───────┘
                                  ▼
                     PortraitEngine.calculate_portrait
                                  │
                     attributes_json / 六维 / 标签
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │ 前端：数据接入中心 / 任务中心 / 模板与标注 / 画像结果 │
        └───────────────────────────────────────────────────┘
调度：dps-worker（APScheduler + advisory lock）→ 定时投递 sync_task / calc_task
```

## 5. 命名与编码

### 5.1 规范

1. 展示：`name`（中文）＞ `display_name` ＞ `code`（次要/悬停）；皆空显示「待补中文名」。
2. code：`^[a-z][a-z0-9_]{1,63}$`，由中文名拼音生成，冲突追加 `_2/_3`，创建后不可改。
3. `name_source`：`manual` / `auto` / `fallback`，覆盖模板、分类、标签分类/值、字段、维度、评分项。

### 5.2 生成与兜底

- 前端 `useCodeFromName`（pinyin-pro）：去噪 → 全拼 → 小写 → 非字母数字转 `_` → 合并/去首尾 → 截断 64 → 去重。
- 后端 `pypinyin` 同规则兜底：`code` 为空时生成；冲突返回 409 `BIZ_ENTITY_CODE_CONFLICT`。
- 交互：新建默认自动且只读，可「手动覆盖」；编辑态只读。
- 历史数据：空名补名脚本 + 人工确认，`name_source=fallback` 标记，不阻塞。

### 5.3 前端落点

`NameCodeLabel` v2（name/code/nameSource/showCode/size/copyable）+ `CodeField` + 术语字典 `portraitTerms.ts`；表格「名称」主列 + code 次列；搜索同时匹配 name/code。

## 6. 数据引入

### 6.1 五入口与管线

| # | 入口 | 适配器 | 触发 | 现状 | 目标 |
|---|---|---|---|---|---|
| 1 | OpenLLM 抽取回写 | 实时回写型 | 被动·近实时 | 已实现 | 纳入管线 |
| 2 | 身份生命周期事件 | 事件型（状态） | 被动·事件 | 已实现 | 保留，不产画像数据 |
| 3 | 批量文件导入 | 批量型 | 手动 | 模拟不落库 | P2 落库 |
| 4 | 数据源同步（HTTP/DB/文件） | 批量型 | 手动/定时 | 仅拉取 | P2 落库+增量 |
| 5 | 人工/API 单条写入 | 人工型 | 按需 | 已实现 | 纳入管线 |

管线：`读取 → 字段映射 → 校验 → profile upsert → 生成标注任务 → 画像入队 → 任务留痕`。

### 6.2 定时任务配置

**部署**：独立 `dps-worker`（无端口、心跳），orchestrator 以 worker 拉起；APScheduler + PG advisory lock 单实例 + `locked_until` 行级租约；API 进程不调度。

**配置模型 `datasource_schedule`（一数据源一配置）**：

| 字段 | 默认 | 说明 |
|---|---|---|
| `enabled` | false | 启停 |
| `mode` | manual | manual / interval / cron |
| `cron_expr` / `interval_seconds` | — | 5 段 cron；间隔 ≥300s |
| `timezone` | Asia/Shanghai | DB 存 UTC |
| `overlap_policy` | skip | skip / queue / replace |
| `missed_policy` | run_once | 停机跨点补一次 / 跳过 |
| `max_retry` / `retry_backoff_seconds` | 3 / 60 | 指数退避 |
| `timeout_seconds` | 1800 | 上限 3600 |
| `batch_size` / `jitter_seconds` | 1000 / 30 | 分批与防打堆 |
| `last_status` / `next_run_at` / `locked_until` | — | 运行时回写 |

**语义**：到点只投递 `sync_task(trigger_source=schedule)`；增量水位 `last_success_at - 5min` 幂等 upsert；连续 3 次失败自动停用（熔断）；启动扫描 `next_run_at < now` 按 `missed_policy` 处理；过期租约任务回到 queued。

**护栏**：全局并发 2、同源串行、配置变更审计、超时上限。

**接口**：`GET/PUT /datasources/{id}/schedule`、`POST .../preview`（未来 5 次）、`.../pause|resume`、`POST .../sync`、`GET /sync-runs`。

### 6.3 前端交互

数据接入中心三 Tab（数据源 / 导入任务 / 同步任务）；导入向导四步（上传→映射→校验→执行）；`ScheduleEditor` + `CronInput` 支持手动/间隔/每日/每周/高级 Cron，实时校验 + 未来 5 次预览 + 暂停恢复 + 连续失败提示。

## 7. 标注

| 模式 | 触发 | 现状 | 默认 |
|---|---|---|---|
| A 纯人工 | 工作台按需 | 唯一实际方式 | 保留兜底 |
| B AI 预标注 + 人工复核 | 引入后生成 `pending` | 引擎已有、未接引入 | 开启 |
| C 规则高置信自动 | 命中规则直接 approved | 未实现 | 仅白名单字段 |

配置：`auto_annotate_on_ingest`（默认 on，**只建任务不自动通过**）、`annotation_mode=manual|ai_candidate`（默认 ai_candidate，缺适配器降级 manual）、`annotation_template_match`。去重键 `(tenant, person, template, ingest_batch)`。

## 8. 画像计算与触发

| 触发 | 默认 | 执行 |
|---|---|---|
| 审核通过增量 | 开 | 去抖 5s + 后台任务 |
| 手动/上游刷新 | 开 | `POST /portrait/calculate` |
| 引入即算 | 关 | 管线入队（轻量） |
| 定时增量/全量 | 建议开增量 | `dps-worker` 扫描变更集/stale |

补偿：`portrait_calc_task` 增加 `trigger_source/locked_until/retry_count/last_error`；worker 每 5 分钟重领超时 pending；DB 抢占保证单执行。

## 9. 前端设计

### 9.1 信息架构

新增「数据接入」菜单分组（数据接入中心、任务中心），菜单顺序：接入 → 标签/标注 → 画像模板 → 画像结果。新增路由 `/portrait/dps/ingest`、`/portrait/dps/ingest/tasks/:id`、`/portrait/dps/task-center`。

### 9.2 页面

| 页面 | 内容 |
|---|---|
| 数据接入中心 | 数据源（类型/状态/最近同步/调度）、导入任务（文件/格式/成功失败）、同步任务（模式/周期/下次执行） |
| 引入任务详情 | 进度统计、错误行表格、重试失败行、导出错误 CSV |
| 任务中心 | 引入 / 标注 / 画像计算三 Tab；筛选时间、状态、触发来源；stale 批量重算 |

### 9.3 组件

`NameCodeLabel` v2、`CodeField`、`TermSelect`、`TaskStatusTag`、`TriggerSourceTag`、`MappingTable`、`IngestTaskDrawer`、`ScheduleEditor`、`CronInput`；组合式 `useCodeFromName`、`useTaskPolling`。

### 9.4 状态与体验

骨架屏、空态引导、缺名提示、AI 缺失降级、任务失败重试、轮询超时停止；状态用文字+颜色；错误提示 `role="alert"`；1280 最小宽度。

### 9.5 性能与权限

列表 10s / 详情 2s 轮询，页面隐藏暂停，终态停止；code 生成防抖 300ms、搜索 400ms；分页 20/页。权限 `dps:view/annotate/manage`，无权限只读/空态；租户切换清空筛选与缓存。

## 10. 数据模型与接口

### 10.1 模型变更

| 对象 | 变更 |
|---|---|
| 模板/分类/标签/字段/维度/评分项 | 新增 `name`、`name_source`；`name` 必填校验 |
| `import_task` / `datasource` / `sync_task` | 内存迁表；状态/统计/错误/时间 |
| `datasource_schedule`（新增） | 一数据源一调度配置（字段见 6.2） |
| `annotation_task` | 增加 `ingest_batch_id`、`generated_by(manual|ingest|ai)` |
| `portrait_calc_task` | 增加 `trigger_source`、`locked_until`、`retry_count`、`last_error` |
| **（生产化预留）** `profile` / 标注 / 计算任务 | 增加 `subject_type`（默认 person）+ `subject_id`，为多画像类型泛化预留 |

迁移要求：幂等 DDL（`IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`），PG 与 SQLite 双形态；新增列有默认值。

### 10.2 接口

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/portrait/templates`、`PUT /portrait/templates/{code}` | `code` 可选、`name` 必填 |
| POST | `/ingest/preview`、`/ingest/execute` | 预览/执行引入 |
| GET | `/ingest/tasks`、`/ingest/tasks/{id}` | 任务列表/详情 |
| POST | `/ingest/tasks/{id}/retry`、`GET .../errors.csv` | 重试/导出 |
| GET/POST | `/datasources`、`POST /{id}/test`、`POST /{id}/sync` | 数据源 |
| GET/PUT | `/datasources/{id}/schedule`、`POST .../preview|pause|resume` | 调度 |
| GET | `/sync-runs` | 调度历史 |
| GET | `/calc-tasks`、`POST /calc-tasks/{id}/retry` | 画像任务 |
| GET/PUT | `/config/ingest-policy` | 标注/画像策略 |

错误码：`BIZ_ENTITY_CODE_CONFLICT(409)`、`PARAM_NAME_REQUIRED(400)`、`BIZ_INGEST_MAPPING_INVALID(400)`、`BIZ_INGEST_TENANT_MISSING(400)`、`PARAM_CRON_INVALID`、`PARAM_INTERVAL_TOO_SMALL`、`PARAM_SCHEDULE_WINDOW_INVALID`（均 400）。

## 11. 非功能设计

| 维度 | 设计 |
|---|---|
| 幂等 | 引入 `(tenant, subject, batch)`；标注 `(tenant, subject, template, batch)`；计算时间桶 + 幂等键 |
| 多租户 | 新增表全部带 `tenant_id`，强过滤；租户切换清缓存 |
| 性能 | 分批 1000；去抖；分页扫描；列表/详情分级轮询 |
| 安全 | payload 不含密钥；日志脱敏；错误只记行号与原因；权限分级 |
| 可观测 | 任务表 + 三段时间 + 心跳/熔断/跳过原因；`checkall` 纳入 worker 探针 |

## 12. 实施计划

| 阶段 | 内容 | 验收 |
|---|---|---|
| P1 命名与编码 | 组件升级、术语中文化、code 自动生成、历史补名 | 无裸 code；不填 code 可提交；冲突提示；测试通过 |
| P2 引入落库与标注生成 | `ingest_pipeline`、导入/同步真实落库、任务表、自动建标注 | profile/标注可查；幂等；任务中心可查 |
| P3 调度与补偿 | `dps-worker`、cron/interval、错过/重叠/熔断、计算补偿、监控 | 定时生效；重启续跑；stale 清零 |
| P4 生产化加固（新增） | 主体泛化、数据质量规则、PII、回填、告警/SLO、压测、字段级权限 | 见 §14.3 清单 |

## 13. 方案评估

### 13.1 多维评分（5 分制，定性）

| 维度 | 评分 | 依据 |
|---|---|---|
| 业务价值 | 5 | 直击裸英文、手填 code、引入不落库、无定时四个真实断点 |
| 架构一致性 | 4 | 单管线 + 多适配器，符合 CDP/Feature Store 通行模式 |
| 实现复杂度 | 3 | 中等：worker + 任务表 + 3 页面 + 9 组件；不引入中间件，运维可控 |
| 风险可控 | 4 | 开关灰度；引入只建任务；画像默认保守 |
| 可运维性 | 3.5 | 任务中心/心跳/熔断已补；缺告警集成、SLO、容量模型 |
| 可扩展性 | 3 | DB 任务表 + APScheduler 适合中小规模；大规模需外置调度/流式 |
| 数据治理 | 3 | 有审计/幂等/租户；缺 PII 分级、血缘、保留与质量规则引擎 |
| 前端体验 | 4.5 | 中文优先、自动编码、任务可见，贴合运营使用 |

**综合结论**：加权约 **3.9/5**，属于「中小规模生产可用、需补齐生产化能力」的方案；不建议在未做主体泛化前直接作为多业务线统一画像平台。

### 13.2 优势

1. 一个管线收口 5 个入口，避免每条链路各写一套落库逻辑。
2. 调度与 API 进程分离，单实例锁 + 行级租约，重启可恢复。
3. 默认策略保守（引入不自动通过、引入即算关闭），坏数据不会直接污染画像。
4. 前端把命名、编码、任务、调度都做成可理解的操作界面，降低运营门槛。
5. 与主流 CDP / Feature Store / 标注平台的最小交集一致，演进路径清晰。

### 13.3 不足与代价

1. **主体模型仍是 person 中心**，多画像类型需额外改造（最高优先级风险）。
2. 任务表 + 轮询在超大规模下有积压与 DB 压力，需要分片/外置调度。
3. 缺数据质量规则引擎与血缘，脏数据只能靠校验与人工复核兜底。
4. 缺 PII 分级/保留/删除策略，合规场景需补。
5. 无回填/重放 UI 与 point-in-time 版本，历史追溯能力弱。
6. 拼音生成 code 的可读性与重码需运营磨合。

## 14. 多画像生产系统适用性评估

### 14.1 先区分两种「多」

| 形态 | 含义 | 本方案适配度 |
|---|---|---|
| 多模板（同一主体） | 同一个人有风险、偏好、价值等多套画像 | **高**：`template_code` 已支持，无需改造 |
| 多主体类型 | 人 / 企业 / 设备 / 内容 等不同实体 | **中低**：当前 `person_id` 贯穿模型与接口，需泛化 |

### 14.2 不同画像域适配矩阵

| 画像域 | 主体粒度 | 数据特征 | 适配度 | 需要的增强 |
|---|---|---|---|---|
| 客户/个人画像 | person | 事件流 + 批量 | 高 | 无（现状路径） |
| 员工/组织画像 | employee/org | 批量、权限敏感 | 中高 | 字段级权限、PII 分级 |
| 企业画像 | org | 批量、关系多 | 中 | `subject_type/subject_id`、关系图谱、企业合并 |
| 设备画像 | device | 高频时序 | 中低 | 时序存储、窗口聚合、流式接入 |
| 内容/商品画像 | content/item | 批量 + 向量 | 中 | 多模态字段、embedding 类型、向量检索 |

### 14.3 生产化差距（按优先级）

| 优先级 | 差距 | 处置 |
|---|---|---|
| P0 | 主体类型泛化 | `profile`/标注/计算任务/接口加 `subject_type`（默认 person）+ `subject_id`；模板绑定主体类型；前端加类型切换 |
| P0 | 数据质量规则 | 引入阶段增加必填/枚举/范围/唯一性规则与隔离区，坏数据不进入画像 |
| P0 | PII 与合规 | 字段分级、脱敏展示、保留期、删除（被遗忘权）、访问审计 |
| P1 | 回填/重放 | 按时间窗/批次重放；`point-in-time` 快照与版本号 |
| P1 | 告警与 SLO | 失败率、积压、延迟、stale 比例接入告警；定义 SLO |
| P1 | 容量与压测 | 导入吞吐、单次重算耗时、并发任务上限的基准测试 |
| P2 | 字段级权限 | 租户内按角色/字段授权，敏感字段默认隐藏 |
| P2 | 血缘 | 字段值 ← 标注 ← 引入批次 的可追溯链路 |
| P2 | 质量度量 | 标注一致性（抽检、Cohen's kappa）、画像完整率 |

### 14.4 规模阈值建议

| 规模 | 时效要求 | 建议架构 |
|---|---|---|
| < 100 万实体 | T+1 / 小时级 | 本方案（DB 任务表 + `dps-worker`）足够 |
| 100 万 – 1000 万 | 分钟级 | 本方案 + 分区表、批量 upsert、任务分片、读写分离 |
| > 1000 万 或 秒级 | 实时 | 引入 Kafka/Flink 或 Spark、特征存储（Feast）、分布式调度（Airflow/Dagster/K8s CronJob） |

### 14.5 结论

- **适合**：单主体（person）+ 多模板、实体规模百万级以内、T+1 或小时级时效的生产画像系统；补齐 §14.3 的 P0/P1 后可作为正式生产方案。
- **有条件适合**：企业/员工画像——先完成 `subject_type` 泛化与字段级权限。
- **暂不适合**：设备/内容等高频时序、千万级实体、秒级时效场景——需演进到流式 + 特征存储架构。
- **建议路径**：v1 以个人画像单主体上线验证管线；v2 泛化主体与治理能力；v3 按规模引入流式与分布式调度。

## 15. 验收标准

| 类别 | 标准 |
|---|---|
| 功能 | 不填 code 可建模板；导入落库并生成标注；三类任务可查可重试；定时任务按 cron 触发 |
| 一致性 | 中文主显无遗漏；枚举无裸英文；code 与 name 一一对应 |
| 可靠性 | 重启后续跑；重复导入幂等；连续失败熔断可见 |
| 性能 | 1000 行导入在可接受时间内完成；列表/详情轮询不造成明显压力（压测报告为准） |
| 安全 | 无密钥/隐私入日志；权限不足不可写；租户隔离验证通过 |

## 16. 风险与开放问题

| 编号 | 风险 | 处置 |
|---|---|---|
| R-1 | 多主体改造成本被低估 | 先加预留列、后做泛化；单独评估 v2 范围 |
| R-2 | 脏数据直接进画像 | 引入只建任务、dry_run、质量规则隔离区 |
| R-3 | 大规模任务积压 | 分片 + 并发上限 + 外置调度演进 |
| R-4 | 拼音 code 重码/不可读 | 人工覆盖 + 别名表 + 冲突后缀 |
| R-5 | 历史缺名影响观感 | 「待补中文名」样式 + 补名脚本 |
| R-6 | 权限码未定 | 先按 `dps:view/annotate/manage`，联调对齐 |

## 17. 附录：证据索引

| 主题 | 路径 |
|---|---|
| 中文名组件 | `openbase-ui/src/components/common/NameCodeLabel.vue` |
| 模板编辑 | `openbase-ui/src/modules/portrait/pages/DpsTemplateEditView.vue` |
| 批量导入（模拟） | `DPS/src/engines/batch_engine.py:L134-L195` |
| 数据源同步（不落库） | `DPS/src/engines/datasource_engine.py:L201-L243` |
| 审核→重算 | `DPS/src/rest_api/routes/routes_profiles.py:L1720-L1730` |
| 去抖调度 | `DPS/src/engines/portrait/recalc_scheduler.py` |
| 重算开关 | `DPS/src/config.py:L123-L129` |
| OpenLLM 回写 | `OpenLLM/backend/app/api/writeback.py`、`edgerouter/adapters/dps_client.py` |
| worker 模式参考 | `OpenBase/scripts/service-orchestrator.ps1`（`openmemory-graph-worker`：心跳 + advisory lock） |

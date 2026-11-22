# OpenBase 画像命名与数据链路一体化设计

| 项 | 内容 |
|---|---|
| 文档编号 | OB-DESIGN-PORTRAIT-NAMING-INGEST |
| 版本 | v0.2.0 |
| 状态 | [Review] |
| 适用系统 | OpenBase（openbase-ui 画像模块）、DPS、OpenLLM 回写链路 |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-22 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v0.1.0 | 2026-11-22 | 首次编制：中文优先展示与英文编码自动生成、数据引入/标注/画像触发一体化方案 | AI 编码代理 |
| v0.2.0 | 2026-11-22 | 补充「5 入口 / 1 管线 / 3 标注模式 / 4 画像触发」全景与同类系统对比；明确引入后只建任务不自动通过、画像默认审核增量+每日兜底 | AI 编码代理 |

## 1. 背景与目标

### 1.1 背景

画像模块当前存在两类体验与链路问题：

1. **命名不一致**：部分页面已用「中文名优先」组件，但评分一致性、标签体系、维度副标题等仍直接展示英文 code；模板/标签/字段的英文 code 全靠用户手填，且创建后不可修改。
2. **链路不闭环**：批量导入与数据源同步只做拉取/校验、不落库；标注任务不会随数据引入自动产生；画像仅在审核通过或手动调用时计算，DPS 进程内无定时调度与任务补偿。

### 1.2 目标

| 编号 | 目标 | 可验证结果 |
|---|---|---|
| G-1 | 画像模块所有模板、标签、字段、维度、评分项默认展示中文名 | 页面无裸英文 code 主展示；缺名时显示「待补中文名」 |
| G-2 | 填入中文名后自动生成英文 code，允许人工覆盖 | 新建表单 code 自动填充；不填 code 也可提交；冲突有明确提示 |
| G-3 | 数据引入可落库并按策略生成标注任务 | 导入/同步完成后 profile 与标注任务可查询 |
| G-4 | 画像触发方式明确且可配置 | 审核通过/引入即算/定时/手动四类触发可开关、可审计 |
| G-5 | 遗留任务可补偿 | 进程重启后 pending/failed 计算任务可自动重试 |

### 1.3 非目标

- 不重构画像评分算法与模板维度模型。
- 不改变现有 `template_code` 语义与已有数据主键。
- 不引入消息中间件（继续复用 DB 任务表 + 后台执行器）。

### 1.4 方案全景（一页看懂）

| 维度 | 数量 | 内容 |
|---|---|---|
| 数据引入入口 | **5** | ① OpenLLM 抽取回写 ② 身份生命周期事件 ③ 批量文件导入 ④ 数据源同步 ⑤ 人工/API 单条写入 |
| 内部管线 | **1** | `ingest_pipeline`：读取→字段映射→校验→profile upsert→生成标注任务→画像入队→任务留痕 |
| 适配器类型 | **3** | 实时回写型 / 批量型 / 人工型 |
| 标注模式 | **3** | A 纯人工；B AI 预标注 + 人工复核；C 规则高置信自动（仅白名单字段） |
| 画像触发 | **4** | 审核通过增量 / 引入即算 / 定时增量与全量 / 手动刷新 |

默认组合：**引入后只建标注任务、不自动通过**；画像以「审核通过增量 + 每日增量兜底」为主，引入即算与全量默认关闭。

## 2. 现状分析

### 2.1 中文展示与编码

| 现状 | 证据 |
|---|---|
| `NameCodeLabel` 已实现 name 优先、缺名回退 code | `openbase-ui/src/components/common/NameCodeLabel.vue:L11-L35` |
| 模板列表、标注模板、标签绑定已接入 | `DpsTemplateListView.vue:L131-L134`、`DpsAnnotationTemplateView.vue:L34`、`TagBindingTable.vue:L22-L29` |
| 仍直接展示英文：评分一致性、标签体系、维度副标题、健康区 `BLOCK` | `DpsScoringConsistencyView.vue:L92`、`DpsTagSystemView.vue:L57`、`DpsTemplateListView.vue:L420`、`L159-L168` |
| 模板 code 与 name 为两个独立表单项，code 创建后不可改 | `DpsTemplateEditView.vue:L14-L22`、`L188-L198` |
| 无任何中文→英文生成逻辑，前端无拼音依赖 | `openbase-ui/package.json` 无 pinyin 相关依赖 |
| 后端模板已有 `name` / `name_source(manual|fallback)` | `openbase-ui/src/core/api/dps.ts:L62-L90` |

### 2.2 数据引入

| 方式 | 行为 | 是否落库 | 证据 |
|---|---|---|---|
| OpenLLM 抽取回写 | 会话抽取 memory/rag/profile → 写回队列 → DPS `POST /portrait/calculate` + `PUT /portrait/{person_id}` | 是 | `OpenLLM/backend/app/api/writeback.py:L218`、`edgerouter/adapters/dps_client.py:L183-L233` |
| 数据源同步（HTTP/DB/文件） | 建数据源 → 建同步任务 → `execute_sync` 拉取+清洗 | **否**（仅计数） | `DPS/src/engines/datasource_engine.py:L201-L243` |
| 批量导入 | `/batch/import` 预览/执行 | **否**（注释「批量插入（模拟）」） | `DPS/src/engines/batch_engine.py:L169-L171` |
| 身份生命周期事件 | push/pull → `apply_event` 幂等消费 | 仅阻断集/权限绑定 | `DPS/src/engines/identity_event_engine.py:L322+` |
| 人工/AI 标注 | 标注工作台提交、AI 候选（`pending`） | 是 | `annotation_template_engine.py:L787-L825`、`ai_annotation_engine.py:L138-L220` |

### 2.3 标注与画像触发

- **标注**：不随引入自动产生；仅人工提交或 AI 候选（需人工复核）。
- **画像触发**：
  1. 审核通过 → 标签联动 → T-DM-05 去抖入队（默认 5 秒桶）→ `BackgroundTasks` 执行计算并写 `attributes_json`；`routes_profiles.py:L1720-L1730`、`recalc_scheduler.py:L43-L89`、`config.py:L123-L129`。
  2. 手动/上游调用 `POST /portrait/calculate`、`/portrait/generate`。
- **无定时任务**：DPS 进程内未发现 APScheduler/cron；`portrait_calc_task` 无常驻 worker，仅靠当次请求后台任务执行。

### 2.4 缺口清单

| 编号 | 缺口 | 影响 |
|---|---|---|
| GAP-1 | 引入链路不落库（批量导入、数据源同步） | 配了数据源也不会出画像 |
| GAP-2 | 引入与标注任务无编排 | 数据到位后仍需人工逐条建标注 |
| GAP-3 | 无定时增量/全量重算 | 未被审核事件覆盖的画像长期 stale |
| GAP-4 | 计算任务无补偿扫描 | 重启后 pending/failed 任务丢失 |
| GAP-5 | 数据源/导入任务状态存内存 | 重启丢失，不可审计 |
| GAP-6 | 英文 code 手填且部分页面裸展示 | 命名不统一、易出错 |

### 2.5 同类系统对比与借鉴

| 体系 | 引入方式 | 标注/加工 | 画像/特征计算 | 借鉴点 |
|---|---|---|---|---|
| CDP（Segment/RudderStack/Snowplow） | 实时事件流 + 批量回填 | 规则分群、受众定义 | 实时属性 + 批汇总 | 双通道统一实体模型 |
| Feature Store（Feast/Tecton） | 离线批 + 在线流 | 特征定义即代码 | batch / stream / on-demand，point-in-time | 分层计算 + 版本与回填 |
| 标注平台（Label Studio/Snorkel/Scale） | 导入→任务分片 | 人工 + AI 预标注 + 审核抽检 | 不产出画像 | 任务化、人机协同、可重跑 |
| 大厂标签画像平台 | 埋点/业务库/导入 | 规则、统计、模型标签 | 离线 T+1 + 实时标签 | 标签目录与术语治理 |
| LLM 记忆（Mem0/Zep/Letta） | 写入时抽取事实 | 自动抽取 + 冲突合并 | 异步 consolidation | 异步汇总、按需读取 |

共性结论（对本方案的校验）：

1. 均为双通道（实时/事件 + 批量回填），最终落同一实体模型；
2. 计算分层（流式→微批→全量），结果带版本与时间点，支持回填；
3. 标注任务化、人机协同，任务生成与数据引入解耦，可重跑；
4. 任务表 + 幂等键 + 补偿扫描是底线配置；
5. 命名治理（中文名 + code + 别名 + 术语字典）为标配。

## 3. 总体方案

### 3.1 命名与编码规范

1. **展示优先级**：`name`（中文）> `display_name` > `code`（仅次要灰色/悬停展示）；三者皆空显示「待补中文名」。
2. **code 规则**：小写 snake_case，`[a-z][a-z0-9_]{1,63}`；由中文名生成，冲突追加 `_2`、`_3`；创建后不可改（沿用现状）。
3. **name_source**：`manual`（人工填写）/`auto`（由 code 或历史英文回填的中文）/`fallback`（缺名，展示层降级）。所有命名实体（模板、分类、标签分类/值、字段、维度、评分项）统一新增 `name` 与 `name_source`。

### 3.2 英文编码自动生成

**前端**：新增组合式函数 `useCodeFromName`：

```
中文名 → 去空白/标点 → 拼音（pinyin-pro，全拼）→ 小写 → 非字母数字转 "_"
      → 合并重复下划线 → 截断 64 → 与现有 code 集合去重（追加 _2...）
```

- 新建表单：`name` 输入即生成 `code`，`code` 默认只读；提供「手动覆盖」开关。
- 编辑表单：`code` 只读；修改 `name` 不改变 `code`。
- 提交前做本地格式与唯一性预校验，冲突提示「编码已存在，请修改名称或手动覆盖」。

**后端兜底**：`POST/PUT` 创建接口若 `code` 为空，使用 `pypinyin` 按同一规则生成；仍冲突返回 409（错误码 `BIZ_ENTITY_CODE_CONFLICT`）。保证 API/MCP/脚本调用同样满足「中文必填、英文自动」。

**迁移**：为历史 `name` 为空的模板/标签/维度/评分项补中文名脚本（人工确认清单），`name_source` 标记；`code` 不迁移、不改写。

### 3.3 中文展示统一

- 画像模块统一使用 `NameCodeLabel`；表格增加「名称」主列 + code 次列（可隐藏）。
- 枚举中文化：`BLOCK/warn/gap`、`manual/ai/legacy`、`pending/approved/rejected`、`source_precedence` 等进入 `zh-CN` 字典，不在模板内硬编码英文。
- 搜索：`keyword` 同时匹配 `name` 与 `code`（模板列表已支持，扩展到标签/字段）。
- 健康区文案：`BLOCK` → 「阻断」、`告警/缺口/健康` 保持中文。

### 3.4 数据引入统一管线

对外 **5 个入口**，内部 **1 条管线 + 3 类适配器**：

| # | 入口 | 适配器 | 触发方式 | 现状 | 目标 |
|---|---|---|---|---|---|
| 1 | OpenLLM 抽取回写 | 实时回写型 | 被动·近实时 | 已实现 | 纳入管线 |
| 2 | 身份生命周期事件 | 事件型（状态） | 被动·事件 | 已实现（仅状态） | 保留，不产画像数据 |
| 3 | 批量文件导入（CSV/Excel/JSON） | 批量型 | 手动 | 模拟，不落库 | P2 真实落库 |
| 4 | 数据源同步（HTTP/DB/文件） | 批量型 | 手动/定时 | 仅拉取，不落库 | P2 落库 + 增量 |
| 5 | 人工/API 单条写入（工作台、MCP） | 人工型 | 按需 | 已实现 | 纳入管线 |

新增 `ingest_pipeline`（DPS Service 层），上述入口统一走以下步骤：

```
① 读取（CSV/JSON/Excel/HTTP/DB/回写 payload）
② 字段映射（field_mapping，中文表头→标准字段）
③ 校验（必填/类型/租户）
④ profile upsert（person_id + tenant 幂等，写 attributes_json / 六维）
⑤ 标注任务生成（按模板匹配 + 策略，见 3.5）
⑥ 画像入队（按策略，见 3.6）
⑦ 任务与错误留痕（import_task / sync_task / annotation_task / calc_task）
```

- 批量导入与数据源同步的「执行」由模拟改为真实调用 `ingest_pipeline`；支持 `dry_run` 预览。
- 引入任务、同步任务状态**落库**（替换内存字典），字段含 `status/total/processed/errors/last_error/created_at`。

### 3.5 标注任务生成策略

新增配置（模板或全局）：

| 配置 | 取值 | 默认 | 说明 |
|---|---|---|---|
| `auto_annotate_on_ingest` | on/off | on | 引入成功后按模板匹配**只建任务**，不自动通过 |
| `annotation_mode` | manual / ai_candidate | ai_candidate | AI 候选强制 `pending`，人工复核后生效；未配置适配器时自动降级 manual |
| `annotation_template_match` | 模板 code 列表/维度规则 | 空 | 决定用哪个标注模板生成任务 |

标注实施模式：

| 模式 | 触发时机 | 现状 | 建议默认 |
|---|---|---|---|
| A. 纯人工标注 | 人工在工作台按需创建 | 唯一实际方式 | 保留（兜底） |
| B. AI 预标注 + 人工复核 | 引入后自动生成 `pending` 候选，人工确认生效 | 引擎已有，未接入引入链路 | 默认开启 |
| C. 规则高置信自动 | 结构化字段命中规则直接 `approved`，低置信转人工 | 未实现 | 仅白名单字段开启 |

去重键：`(tenant_id, person_id, template_code, ingest_batch_id)`，避免重复生成。

### 3.6 画像触发矩阵

现状仅 2 种（审核通过、手动/上游），目标扩展为 4 种：

| 触发 | 配置 | 默认 | 执行方式 |
|---|---|---|---|
| 审核通过增量重算 | `tag_change_recalc_enabled` | on | 去抖 5s + 后台任务（现状） |
| 引入即算 | `portrait_calc_on_ingest` | off | 管线第 ⑥ 步入队 |
| 定时增量/全量 | `portrait_schedule_cron` | 建议 `0 2 * * *` | 新增调度器扫描 stale/变更集 |
| 手动刷新 | 接口 | on | `POST /portrait/calculate` |

**调度与补偿**：

- 引入 APScheduler（进程内单实例）或复用 OpenBase 定时编排，执行：① 每日增量重算；② 每 5 分钟补偿扫描 `portrait_calc_task` 中超时 `pending`/`failed`（按 `retry_count` 上限）。
- 多实例部署时通过 DB 抢占（`UPDATE ... WHERE status='pending' AND locked_until < now`）保证单执行。

## 4. 数据模型变更

| 对象 | 变更 |
|---|---|
| `portrait_template` / `template_category` | 新增 `name_source`；`name` 必填校验 |
| 标签分类/标签值、标注模板字段、维度、评分项 | 新增 `name`、`name_source`（缺省 fallback） |
| `import_task` | 由内存迁表：`id/tenant_id/format/status/total/processed/error_count/created_at/finished_at` |
| `datasource`、`sync_task` | 由内存迁表；`sync_config` JSON、`last_sync_at`、`next_run_at` |
| `annotation_task`（或复用 annotation） | 增加 `ingest_batch_id`、`generated_by(manual|ingest|ai)` |
| `portrait_calc_task` | 增加 `trigger_source(approval|ingest|schedule|manual)`、`locked_until`、`last_error` |

迁移要求：幂等 DDL（`IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`），PG 与 SQLite 双形态；新增列均给默认值，兼容旧数据。

## 5. 接口变更

| 接口 | 变更 |
|---|---|
| `POST /portrait/templates`、`PUT /portrait/templates/{code}` | `code` 改为可选；为空则服务端生成；新增 `name` 必填校验 |
| 标签/字段/评分项创建接口 | 同上，新增 `name` |
| `POST /batch/import/{id}/execute` | 改为真实落库；新增 `dry_run` 参数 |
| `POST /datasources/{id}/sync`（新增） | 触发同步并落库；返回任务 ID |
| `POST /portrait/ingest`（建议新增） | 统一引入入口：payload + mapping + 策略 |
| `GET /portrait/calc-tasks`（建议新增） | 计算任务状态与重试 |
| 配置接口 | 新增 `auto_annotate_on_ingest`、`annotation_mode`、`portrait_calc_on_ingest`、`portrait_schedule_cron` |

错误码：`BIZ_ENTITY_CODE_CONFLICT(409)`、`PARAM_NAME_REQUIRED(400)`、`BIZ_INGEST_MAPPING_INVALID(400)`、`BIZ_INGEST_TENANT_MISSING(400)`。

## 6. 关键时序

**引入 → 标注 → 画像**

```
调用方 → ingest_pipeline → profile upsert
                        → (策略) 生成 annotation_task(pending)
                        → (策略) 入队 portrait_calc_task
标注工作台 → review(approved) → 标签联动 → 去抖入队 → 后台计算 → attributes_json
调度器 → 扫描 stale/变更集 → 入队 → worker 执行 → 更新 last_calc_at/version
```

**审核 → 重算（现状保持）**

```
POST /portrait/annotations/{id}/review(approved)
  → _sync_tags_after_approval
  → _schedule_recalc_after_tags(去抖 5s)
  → BackgroundTasks _run_calc_task → PortraitEngine.calculate_portrait
  → _persist_template_namespace / 六维列
```

## 7. 非功能设计

- **幂等**：引入按 `(tenant, person, batch)` 去重；标注任务按 `(tenant, person, template, batch)` 唯一；计算任务沿用 `idempotency_key` 时间桶。
- **多租户**：所有新增表带 `tenant_id`，查询强制租户过滤。
- **性能**：引入分批（1000/批）；画像重算按 person+template 去抖；定时任务分页扫描，避免全表锁。
- **安全**：引入 payload 不含密钥；日志脱敏；任务错误只记录行号与原因，不落完整原文。
- **可观测**：任务表 + 运行监控页展示「引入/标注/画像」三段状态与失败原因。

## 8. 兼容与迁移

1. `code` 仍为唯一键，历史 code 不变；新实体允许自动生成。
2. 所有新增列可空/有默认值；旧接口不传 `name` 时行为不变（展示层回退 code，并标记 fallback）。
3. 引入管线以开关控制：`ingest_persist_enabled` 默认关闭，灰度验证后开启。
4. 定时调度默认关闭，配置 cron 后生效，避免影响现有环境。

## 9. 分阶段实施

| 阶段 | 内容 | 验收 |
|---|---|---|
| P1 命名与编码 | `NameCodeLabel` 全量接入、枚举中文化、`useCodeFromName` + 后端 pypinyin 兜底、历史名称补齐脚本 | 页面无裸 code 主展示；新建不填 code 可提交；冲突提示正确；E2E/vitest 通过 |
| P2 引入落库与标注生成 | `ingest_pipeline`、批量导入/数据源真实落库、任务落库、`auto_annotate_on_ingest` | 导入后 profile 与标注任务可查询；重复导入幂等；任务中心可查引入/标注/画像三类任务 |
| P3 画像调度与补偿 | 触发矩阵配置、APScheduler/编排、`portrait_calc_task` 补偿 worker、监控页 | 定时重算生效；重启后任务可续跑；stale 画像清零 |

## 10. 风险与开放问题

| 编号 | 风险/问题 | 处置建议 |
|---|---|---|
| R-1 | 拼音生成 code 可能出现不可读长串或重码 | 长度截断 + 冲突后缀；允许人工覆盖；对高频实体维护别名表 |
| R-2 | 引入落库后脏数据直接进画像 | 引入只建任务不自动通过；先 dry_run 与校验报告 |
| R-3 | 定时全量重算成本高 | 只做增量（按 updated_at/变更集），全量限手动 |
| R-4 | 多实例调度重复执行 | DB 抢占 + 唯一幂等键 |
| R-5 | 历史数据无中文名 | 迁移脚本 + 运营确认清单，缺失标记 fallback 而非阻塞 |

## 11. 附录：证据索引

| 主题 | 路径 |
|---|---|
| 中文名组件 | `openbase-ui/src/components/common/NameCodeLabel.vue` |
| 模板编辑（code/name） | `openbase-ui/src/modules/portrait/pages/DpsTemplateEditView.vue` |
| 批量导入（模拟） | `DPS/src/engines/batch_engine.py:L134-L195` |
| 数据源同步（不落库） | `DPS/src/engines/datasource_engine.py:L201-L243` |
| 审核→重算 | `DPS/src/rest_api/routes/routes_profiles.py:L1720-L1730` |
| 去抖调度 | `DPS/src/engines/portrait/recalc_scheduler.py` |
| 重算开关 | `DPS/src/config.py:L123-L129` |
| OpenLLM 回写 | `OpenLLM/backend/app/api/writeback.py`、`edgerouter/adapters/dps_client.py` |

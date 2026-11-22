# OpenBase 画像优化升级实施方案

| 项 | 内容 |
|---|---|
| 文档编号 | OB-IMPL-PORTRAIT-UPGRADE |
| 版本 | v1.0.0 |
| 状态 | [Review] |
| 上游文档 | 《画像命名与数据链路一体化升级方案 v1.1.0》《画像 P0 前置评估报告 v1.1.0》 |
| 实施范围 | DPS 后端（DDL/引擎/API/worker）、openbase-ui 画像模块 |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-22 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-22 | 基于现有 DPS 成果编制：能力基线、差距映射、批次计划、DDL/API/前端清单、迁移与验收 | AI 编码代理 |

## 1. 实施原则

1. **复用优先**：不重建已有模板族、标注、标签、历史、任务能力，只做扩展。
2. **增量兼容**：DDL 全部 `IF NOT EXISTS / ADD COLUMN IF NOT EXISTS`；`person_id` 不变；旧接口行为不变。
3. **开关灰度**：PII、数据权限、进度画像、调度均以 env 开关控制，先 `warn` 后 `enforce`。
4. **双形态**：PostgreSQL 与 SQLite DDL 同步维护，迁移幂等。
5. **任务留痕**：所有引入/标注/计算/调度动作落任务表，可重试、可审计。

## 2. 现有能力基线（复用清单）

| 能力 | 现有实现 | 复用方式 |
|---|---|---|
| 模板族 | `portrait_template`、`portrait_template_category`、`component`、`history`、package/version/preflight/diff/rollback | 两类画像用「模板分类 + 新增 `profile_family`」区分，不新建模板体系 |
| 画像计算 | `engines/portrait/{core,crud}.py`、`PortraitEngine.calculate_portrait`、六维评分 | 复用；新增进度维度由模板评分项承接 |
| 计算任务 | `platform.portrait_calc_task`（幂等键、retry_count、status） | 加 `trigger_source`、`locked_until`；新增补偿 worker |
| 去抖调度 | `engines/portrait/recalc_scheduler.py`、`config.tag_change_recalc_*` | 保留；接入统一任务触发来源 |
| 标注 | `annotation`（复核级别/claim）、`annotation_template_engine`、`ai_annotation_engine`、工作台 | 加 `generated_by`、`ingest_batch_id`；进度类标签走规则 |
| 标签体系 | `tag_definition`、`tag_value`、`profile_tag`、`profile_tag_relation` | 直接复用；进度标签作为普通标签值 |
| 历史/趋势 | `profile_history`（version/snapshot/change_reason）、`/portrait/version`、`/compare`、`/trend`、lineage | **扩展 `profile_history`** 增加周期与快照类型，不新建 `profile_snapshot` |
| 身份与组织 | `organization`（code/name/status/config）、身份域 `org_code`、`init_org_schema` | 扩展组织树字段；新增成员关系表 |
| 审计 | `audit_log_engine`（敏感键脱敏、IP 掩码） | 扩展读/导出/删除审计事件 |
| 引入 | `batch_engine`（模拟）、`datasource_engine`（拉取不落库）、`sync_task` 表 | 新建 `ingest_engine`，复用 `sync_task` 并扩展 |
| MCP | `mcp_server/tools.py` | 复用统一响应序列化（含脱敏） |

## 3. 差距 → 改造映射

| 目标 | 现状差距 | 改造点 |
|---|---|---|
| 政务 PII | 仅密钥/IP 脱敏；`/portrait/list` 返回完整 `attributes_json` | 新增 `field_classification` + 统一序列化器 + 字段级权限 + 导出/日志纪律 |
| 组织权限 | 仅 tenant 过滤；`organization` 无层级；无数据范围 | `organization` 加 `parent_code/path/level`；新增 `org_member`；中间件注入 `data_scope` |
| 业务进度 | 无事项实体、无周期快照 | 新增 `business_item`、`progress_snapshot`；新增 `progress_engine`；模板加 `profile_family` |
| 审计 | 只审计部分管理动作 | 扩展读/导出/删除/权限变更审计；保留期配置 |
| 命名编码 | code 手填、部分裸英文 | 复用 `NameCodeLabel`，新增 `CodeField`/`useCodeFromName`；后端拼音兜底 |
| 引入落库 | 导入/同步不落库、任务在内存 | 新增 `ingest_engine` + `import_task` 表；复用 `sync_task` |
| 定时调度 | 无调度器 | 新增 `dps-worker`（APScheduler + advisory lock）+ `datasource_schedule` |

## 4. 批次计划

依赖顺序：**批次 0 → 1 → 2 →（3 与 5 可并行）→ 4 → 6**。

### 批次 0：基座与开关（前置）

- DDL 迁移框架：新增 `ddl/schema_v2_18_upgrade.py`，统一注册 PG/SQLite 语句。
- 配置项（`config.py`）：
  - `DPS_PII_MODE=off|warn|enforce`（默认 warn）
  - `DPS_DATA_SCOPE_MODE=off|warn|enforce`（默认 warn）
  - `DPS_PROGRESS_ENABLED=true|false`（默认 false）
  - `DPS_SCHEDULER_ENABLED=true|false`（默认 false）
  - `DPS_INGEST_PERSIST_ENABLED=true|false`（默认 false）
- 统一响应序列化入口：`src/security/pii_serializer.py`（先透传，后续挂规则）。
- 完成标准：迁移在 PG/SQLite 均可重复执行；开关关闭时行为与现状一致。

### 批次 1：政务 PII（P0-1）

- 新增表：`field_classification`。
- 新增模块：`src/security/pii.py`（分级、掩码、字段路径解析）。
- 改造读路径：
  - `/portrait/list`、`/portrait/{person_id}/dimension-details`、`/portrait/annotations*`、MCP `tools.py` 统一走 `pii_serializer`。
  - L3 默认掩码，L4 默认剔除；`dps:pii:view` 才返回明文。
- 导出与日志：错误行 CSV 强制脱敏；日志白名单禁止 payload。
- 前端：`PiiMaskedField.vue`；详情页按后端返回值渲染，不再自行拼字段。
- 完成标准：默认配置下 `attributes_json` 中手机/证件/姓名按规则掩码；无权限不可见明文；脱敏用例通过。

### 批次 2：组织数据权限（P0-2）

- 扩展 `organization`：`parent_code`、`path`、`level`、`sort_order`。
- 新增 `org_member`：`person_id`、`org_code`、`position`、`is_primary`、`valid_from/to`。
- 新增 `src/security/data_scope.py`：`self|org|org_subtree|all`，从身份头 `org_code` + 角色推导。
- 改造：`/portrait/list`、`/portraits/search`、`/portrait/statistics`、导出统一注入组织范围条件。
- 前端：`OrgTreeSelect.vue`；列表/看板增加「范围」切换与越权空态。
- 完成标准：上级可见下级、平级不可见、跨部门专班按 ACL 可见；越权返回空集而非报错。

### 批次 3：业务进度模型（P0-3）

- 新增表：`business_item`、`progress_snapshot`。
- 扩展：`profile_history`（`period_type/period_key/snapshot_type/template_code`）；`portrait_template` 加 `profile_family`（`persona|business_progress`，默认 persona）。
- 新增 `src/engines/progress_engine.py`：
  - 事项入库/更新 → 责任人映射（`org_member`）→ 周期聚合 → `progress_snapshot`。
  - 生成进度标签（规则）→ 触发画像重算（复用 `portrait_calc_task`）。
- 模板：新增「业务进度画像」分类与默认模板（事项完成率、按时率、逾期天数、质量分、工作量）。
- 前端：`BusinessItemTable.vue`、`ProgressTrend.vue`；详情页新增「进度」页签。
- 完成标准：导入事项后可按日/周生成快照与进度画像；趋势可查；口径字典可配置。

### 批次 4：审计留痕（P0-4）

- 扩展 `audit_log_engine` 事件类型：`portrait_read`、`portrait_export`、`subject_delete`、`scope_change`。
- 记录要素：操作人、租户、组织、对象、字段级别、行数、结果。
- 保留期：`DPS_AUDIT_RETENTION_DAYS`（默认 180，按等保要求可调）。
- 查询：`GET /audit/logs?action=&from=&to=`（仅管理员）。
- 完成标准：读取/导出/删除都有审计；导出含字段级别与行数；保留期任务可执行。

### 批次 5：命名编码与引入落库（P1/P2）

- 命名：`NameCodeLabel` v2、`CodeField`、`useCodeFromName`；后端 `pypinyin` 兜底 + 409 冲突。
- 引入：新增 `ingest_engine.py` + `import_task` 表；`batch_engine`/`datasource_engine` 改为落库并生成标注任务。
- 任务中心：`/ingest/tasks`、`/ingest/tasks/{id}`、重试、错误 CSV（脱敏）。
- 完成标准：不填 code 可建模板；导入落库；任务可查可重试；幂等。

### 批次 6：调度与补偿（P3）

- 新增 `datasource_schedule`；`sync_task` 加 `trigger_source/locked_until`；`portrait_calc_task` 加 `trigger_source/locked_until`。
- 新增 `src/worker/scheduler.py`：APScheduler + PG advisory lock + 心跳；`scripts/service-orchestrator.ps1` 注册 `dps-worker`。
- 补偿：每 5 分钟重领过期任务；连续失败熔断。
- 前端：`ScheduleEditor.vue`、`CronInput.vue`；未来 5 次预览。
- 完成标准：cron/interval 生效；重启续跑；重叠/错过/熔断策略生效。

## 5. DDL 变更清单

> PG 与 SQLite 各一份；以下为 PG 语义，SQLite 用 TEXT/INTEGER 对应。全部幂等。

```sql
-- 组织树
ALTER TABLE organization ADD COLUMN IF NOT EXISTS parent_code VARCHAR(50);
ALTER TABLE organization ADD COLUMN IF NOT EXISTS path VARCHAR(500);
ALTER TABLE organization ADD COLUMN IF NOT EXISTS level INTEGER DEFAULT 1;
ALTER TABLE organization ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0;

CREATE TABLE IF NOT EXISTS org_member (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id VARCHAR(100) NOT NULL,
  org_code VARCHAR(50) NOT NULL,
  position VARCHAR(100),
  is_primary BOOLEAN DEFAULT FALSE,
  valid_from DATE,
  valid_to DATE,
  tenant_id UUID,
  UNIQUE (tenant_id, person_id, org_code, valid_from)
);

-- PII 分级
CREATE TABLE IF NOT EXISTS field_classification (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type VARCHAR(50) NOT NULL,      -- profile / annotation / import_task ...
  field_path VARCHAR(200) NOT NULL,      -- attributes_json.phone
  level SMALLINT NOT NULL,               -- 1..4
  mask_rule VARCHAR(50),                 -- phone / id_card / name / email
  retention_days INTEGER,
  tenant_id UUID,
  UNIQUE (tenant_id, entity_type, field_path)
);

-- 业务事项与进度
CREATE TABLE IF NOT EXISTS business_item (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_no VARCHAR(100) NOT NULL,
  item_type VARCHAR(50),
  title VARCHAR(300),
  owner_person_id VARCHAR(100),
  org_code VARCHAR(50),
  source_system VARCHAR(100),
  deadline TIMESTAMPTZ,
  status VARCHAR(30),
  milestones JSONB DEFAULT '[]',
  tenant_id UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (tenant_id, source_system, item_no)
);

CREATE TABLE IF NOT EXISTS progress_snapshot (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id VARCHAR(100) NOT NULL,
  org_code VARCHAR(50),
  period_type VARCHAR(10) NOT NULL,      -- day / week / month
  period_key VARCHAR(20) NOT NULL,       -- 2026-11-22 / 2026-W47
  item_count INTEGER DEFAULT 0,
  completed INTEGER DEFAULT 0,
  on_time_rate NUMERIC(5,4),
  overdue_days INTEGER DEFAULT 0,
  quality_score NUMERIC(5,2),
  workload NUMERIC(10,2),
  tenant_id UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (tenant_id, person_id, period_type, period_key)
);

-- 画像历史扩展（复用 profile_history）
ALTER TABLE profile_history ADD COLUMN IF NOT EXISTS period_type VARCHAR(10);
ALTER TABLE profile_history ADD COLUMN IF NOT EXISTS period_key VARCHAR(20);
ALTER TABLE profile_history ADD COLUMN IF NOT EXISTS snapshot_type VARCHAR(20) DEFAULT 'event';
ALTER TABLE profile_history ADD COLUMN IF NOT EXISTS template_code VARCHAR(100);
CREATE INDEX IF NOT EXISTS ix_profile_history_period
  ON profile_history (profile_id, snapshot_type, period_key);

-- 模板族
ALTER TABLE portrait_template ADD COLUMN IF NOT EXISTS profile_family VARCHAR(30) DEFAULT 'persona';

-- 任务与调度
ALTER TABLE sync_task ADD COLUMN IF NOT EXISTS trigger_source VARCHAR(20) DEFAULT 'manual';
ALTER TABLE sync_task ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;
ALTER TABLE portrait_calc_task ADD COLUMN IF NOT EXISTS trigger_source VARCHAR(20) DEFAULT 'manual';
ALTER TABLE portrait_calc_task ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS datasource_schedule (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  datasource_id UUID NOT NULL REFERENCES datasource_config(id),
  enabled BOOLEAN DEFAULT FALSE,
  mode VARCHAR(10) DEFAULT 'manual',
  cron_expr VARCHAR(100),
  interval_seconds INTEGER,
  timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
  start_at TIMESTAMPTZ,
  end_at TIMESTAMPTZ,
  overlap_policy VARCHAR(10) DEFAULT 'skip',
  missed_policy VARCHAR(10) DEFAULT 'run_once',
  max_retry INTEGER DEFAULT 3,
  retry_backoff_seconds INTEGER DEFAULT 60,
  timeout_seconds INTEGER DEFAULT 1800,
  batch_size INTEGER DEFAULT 1000,
  jitter_seconds INTEGER DEFAULT 30,
  last_status VARCHAR(20),
  next_run_at TIMESTAMPTZ,
  locked_until TIMESTAMPTZ,
  tenant_id UUID,
  UNIQUE (tenant_id, datasource_id)
);

-- 导入任务
CREATE TABLE IF NOT EXISTS import_task (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_name VARCHAR(300),
  file_format VARCHAR(20),
  total_rows INTEGER DEFAULT 0,
  success_rows INTEGER DEFAULT 0,
  failed_rows INTEGER DEFAULT 0,
  status VARCHAR(20) DEFAULT 'pending',
  errors_json JSONB DEFAULT '[]',
  trigger_source VARCHAR(20) DEFAULT 'manual',
  tenant_id UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  finished_at TIMESTAMPTZ
);

-- 标注扩展
ALTER TABLE annotation ADD COLUMN IF NOT EXISTS generated_by VARCHAR(20) DEFAULT 'manual';
ALTER TABLE annotation ADD COLUMN IF NOT EXISTS ingest_batch_id VARCHAR(64);
```

## 6. API 变更清单

| 方法 | 路径 | 批次 | 说明 |
|---|---|---|---|
| GET/PUT | `/admin/field-classifications` | 1 | 字段分级维护 |
| GET | `/portrait/list`（改） | 1/2 | 增加脱敏与组织范围过滤 |
| GET/POST/PUT | `/orgs`、`/orgs/tree` | 2 | 组织树维护 |
| GET/PUT | `/orgs/{code}/members` | 2 | 成员与岗位 |
| POST/GET | `/business-items` | 3 | 事项入库/查询 |
| GET | `/progress/{person_id}`、`/progress/org/{org_code}` | 3 | 进度与趋势 |
| GET | `/portrait/{person_id}/snapshots` | 3 | 周期快照（复用 history） |
| GET | `/audit/logs` | 4 | 读取/导出/删除审计查询 |
| POST | `/ingest/preview`、`/ingest/execute` | 5 | 引入预览/执行 |
| GET | `/ingest/tasks`、`/ingest/tasks/{id}` | 5 | 任务列表/详情 |
| POST | `/ingest/tasks/{id}/retry` | 5 | 失败重试 |
| GET/PUT | `/datasources/{id}/schedule` | 6 | 调度配置 |
| POST | `/datasources/{id}/schedule/preview`、`pause`、`resume` | 6 | 预览/暂停/恢复 |

错误码新增：`PARAM_CRON_INVALID`、`PARAM_INTERVAL_TOO_SMALL`、`PARAM_SCHEDULE_WINDOW_INVALID`、`BIZ_SCOPE_FORBIDDEN`、`BIZ_PII_FORBIDDEN`。

## 7. 前端改造清单

| 文件/组件 | 批次 | 改造 |
|---|---|---|
| `core/api/dps.ts` | 1-6 | 新增类型：PII、组织、进度、任务、调度 |
| `PortraitList.vue` | 2 | 组织范围切换、画像族 Tab（人物/业务进度） |
| `PortraitDetail.vue` | 1/3 | 敏感字段掩码渲染、进度页签与趋势图 |
| 新增 `OrgTreeSelect.vue` | 2 | 组织树选择 |
| 新增 `PiiMaskedField.vue` | 1 | 掩码展示与「申请查看」 |
| 新增 `BusinessItemTable.vue`、`ProgressTrend.vue` | 3 | 事项与趋势 |
| 新增 `IngestTasksView.vue`、`TaskDetailView.vue` | 5 | 引入任务中心 |
| 新增 `ScheduleEditor.vue`、`CronInput.vue` | 6 | 调度配置 |
| `NameCodeLabel.vue`、新增 `CodeField.vue`、`useCodeFromName.ts` | 5 | 中文优先与编码生成 |

## 8. 测试与验收

| 层级 | 覆盖 |
|---|---|
| 单元 | 掩码规则、字段路径解析、data_scope 推导、进度聚合、cron 校验、幂等键 |
| 集成 | 引入→profile→标注→计算；组织越权；PII 读路径；调度触发与重试 |
| 迁移 | PG/SQLite 重复执行；旧接口回归；回填校验 |
| E2E | 组织切换、掩码展示、进度趋势、任务中心、调度编辑器 |
| 安全 | 日志无 PII、导出脱敏、越权空集、审计可查 |

批次验收以「开关关闭=现状不变、开关开启=新增能力可用」为统一标准。

## 9. 风险与回滚

| 风险 | 处置 |
|---|---|
| 迁移破坏旧库 | 全部增量 DDL；SQLite/PG 双跑；先备份 |
| 脱敏影响业务 | `warn` 模式先观察；按字段逐步 `enforce` |
| 组织范围误伤 | 默认 `self` 或 `org`，管理员可 `all`；灰度租户 |
| 进度口径不一致 | 先试点 1–2 类事项；口径字典与 DQ 规则先行 |
| 调度重复执行 | advisory lock + `locked_until` + 幂等键 |
| 回滚 | 关闭对应 env 开关；DDL 只增不删，无需回滚结构 |

## 10. 附录：现有文件索引

| 主题 | 路径 |
|---|---|
| profile / organization / sync_task | `DPS/src/ddl/schema_root.py` |
| 模板族 / calc task | `DPS/src/ddl/schema_portrait.py` |
| profile_history / annotation / 标签关联 | `DPS/src/ddl/schema_profile_dependents.py` |
| 画像计算 | `DPS/src/engines/portrait/core.py`、`crud.py` |
| 去抖与重算开关 | `DPS/src/engines/portrait/recalc_scheduler.py`、`config.py:L123-L132` |
| 标注引擎 | `DPS/src/engines/annotation_template_engine.py`、`ai_annotation_engine.py` |
| 引入（现状） | `DPS/src/engines/batch_engine.py`、`datasource_engine.py` |
| 审计 | `DPS/src/engines/audit_log_engine.py` |
| 画像 API | `DPS/src/rest_api/routes/routes_profiles.py` |
| MCP | `DPS/src/mcp_server/tools.py` |
| 前端画像页面 | `openbase-ui/src/modules/portrait/` |
| 前端 API 类型 | `openbase-ui/src/core/api/dps.ts` |

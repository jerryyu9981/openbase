# 波次 B（2.19.0）引入与权限 —— 实施规格

| 项 | 内容 |
|---|---|
| 文档编号 | OB-SPEC-PORTRAIT-WAVE-B |
| 版本 | v1.0.0 |
| 状态 | [Approved] |
| 上游文档 | 《OpenBase-画像优化升级三波次发布实施计划 v1.0.2》§4、《OpenBase-画像优化升级实施方案 v1.0.3》批次 2/5 |
| 目标版本 | DPS 2.19.0 / OpenBase 前端随版本 |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-23 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-23 | 首次编制：B-01~B-11 决策级规格、文件清单、验收与回滚；同日评审通过并进入实现 | AI 编码代理 |

## 1. 范围与不变量

**范围**：组织树与成员、数据范围引擎、PII enforce、引入落库与标注自动生成、引入任务中心前端。

**不变量**：
1. 所有开关默认保持兼容：`DPS_DATA_SCOPE_MODE=off`、`DPS_INGEST_PERSIST_ENABLED=false` 时行为与 2.18.x 一致。
2. `DPS_PII_MODE` 默认由 `warn` 切换为 `enforce`（B-05 明确要求）；持有 `dps:pii:view` 的角色仍见 L3 明文，`dps:pii:high` 才见 L4。
3. DDL 只增不删；迁移幂等（PG `IF NOT EXISTS`，SQLite 先探测 `PRAGMA table_info`）。
4. 多租户：新增表读写均带 `tenant_id` 谓词；缺上下文时沿用既有 fail-closed 口径。
5. 越权返回空集，不返回 403（数据范围语义）。

## 2. B-01 组织树扩展与回填

### 2.1 DDL 单一来源
新增 `DPS/src/ddl/upgrade_utils.py`（提取自 v2.18 的公共幂等工具）：
- `backend_dialect(database) -> "pg"|"sqlite"`
- `sqlite_table_columns(database, table) -> set[str]`
- `ensure_column(database, dialect, table, column, pg_type, sqlite_type) -> bool`

`DPS/src/ddl/schema_v2_18_upgrade.py` 改为从 `upgrade_utils` 导入上述函数（行为不变，A 波测试继续通过）。

新增 `DPS/src/ddl/schema_v2_19_upgrade.py`：
- `SCHEMA_VERSION = "2.19.0"`
- `ORGANIZATION_COLUMNS_V2_19`：`parent_code VARCHAR(50)`、`path VARCHAR(500)`、`level INTEGER DEFAULT 1`、`sort_order INTEGER DEFAULT 0`
- `TABLES_V2_19`：`org_member`、`import_task`
- `TABLE_COLUMNS_V2_19`：`annotation.generated_by`、`annotation.ingest_batch_id`、`sync_task.watermark`
- `ensure_v2_19_upgrade(database) -> dict`：建表 → 组织补列 → 标注/同步任务补列；返回摘要并 INFO 留痕。

`org_member`（PG / SQLite 双份）：
| 列 | PG | SQLite |
|---|---|---|
| id | UUID PK default gen_random_uuid() | TEXT PK |
| person_id | VARCHAR(100) NOT NULL | TEXT NOT NULL |
| org_code | VARCHAR(50) NOT NULL | TEXT NOT NULL |
| position | VARCHAR(100) | TEXT |
| is_primary | BOOLEAN DEFAULT FALSE | INTEGER DEFAULT 0 |
| valid_from | DATE | TEXT |
| valid_to | DATE | TEXT |
| tenant_id | UUID | TEXT |
| created_at | TIMESTAMPTZ DEFAULT NOW() | TEXT DEFAULT CURRENT_TIMESTAMP |
| UNIQUE | (tenant_id, person_id, org_code, valid_from) | 同左 |

`import_task`：
`id, file_name, file_format, total_rows, success_rows, failed_rows, status, errors_json, trigger_source, tenant_id, created_at, finished_at`（JSONB/TEXT 对应）。

`DPS/src/database.py`：在 `ensure_v2_18_upgrade(self)` 之后调用 `ensure_v2_19_upgrade(self)`。

### 2.2 回填脚本
新增 `DPS/scripts/backfill_org_tree.py`：
- 默认 `--dry-run`，`--apply` 才写库；
- 规则：根节点 `parent_code is null` → `path=code, level=1`；子节点 `path=parent.path + "/" + code`，`level=parent.level+1`；环/孤儿 → WARN 并跳过；
- 只 UPDATE `path/level` 与现状不同的行；输出 `scanned/updated/skipped/orphans` 摘要。

## 3. B-02 成员与 `/orgs/*` API

新增 `DPS/src/engines/org_engine.py`：
- `list_orgs(tenant_id=None) -> list[dict]`：`SELECT id,name,code,status,parent_code,path,level,sort_order FROM organization ORDER BY level, sort_order, code`（带 tenant 过滤时经 tenant.org_id 约束，缺省保持既有单租户行为）。
- `get_tree(tenant_id=None) -> list[dict]`：由 `parent_code` 组装嵌套 `children`；无父节点者为根。
- `list_members(org_code, include_expired=False)`：按 `valid_to` 过滤；返回 `person_id/position/is_primary/valid_from/valid_to`。
- `upsert_members(org_code, members, tenant_id=None)`：逐条 upsert；`is_primary=True` 时先将同 person 其他成员记录置 `is_primary=0`；唯一键冲突按更新处理。
- `resolve_org_ids(codes) -> list[str]`、`org_path(org_code) -> str|None`、`member_org_codes(person_id) -> list[str]`。
- 所有 SQL 参数化，禁止字符串拼接用户输入。

新增 `DPS/src/rest_api/routes/routes_orgs.py`：
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/orgs` | 组织平铺列表 |
| GET | `/orgs/tree` | 组织树 |
| GET | `/orgs/{code}/members` | 成员列表 |
| PUT | `/orgs/{code}/members` | 批量维护成员（body: `{members:[...]}`） |

响应统一 `{code:200,message:"success",data:...}`；参数错误抛 `HTTPException(400, "PARAM_..." )`。

注册：`DPS/src/rest_api/routes/__init__.py::_build_prefixed_router` 在 `admin_router` 之前加入 `orgs_router`（静态段无冲突）。

权限：`permission_middleware.PATH_RESOURCE_MAP` 增加 `"orgs": "organization"`；`permission_engine.PRESET_PERMISSIONS` 已含 `organization:read`，写动作 `PUT` 判 `organization:update`，需在 `PRESET_PERMISSIONS` 增加 `("organization", "update")`，并授予 admin。

## 4. B-03 / B-04 数据范围

新增 `DPS/src/security/data_scope.py`：
- `DataScope` 枚举：`SELF/ORG/ORG_SUBTREE/ALL`。
- `resolve_scope(role: str|None) -> DataScope`：`super_admin/admin → ALL`；`operator → ORG_SUBTREE`；`readonly → ORG`；缺省 `ORG`。
- ContextVar `_scope_context`：`mode, scope, org_id, org_code, person_id, user_id`；`set_scope_context/get_scope_context/clear_scope_context`。
- `async build_scope_predicate(column="org_id") -> tuple[list[str], list[Any]]`：
  - `mode in (off, warn)` → `([], [])`；`warn` 额外 `logger.warning("DATA_SCOPE_WOULD_LIMIT ...")`（只记 code/scope，不记数据）。
  - `ALL` → `([], [])`。
  - `ORG`：有 `org_code` → `column IN (SELECT id FROM organization WHERE code = ?)`；否则有 `org_id` → `column = ?`。
  - `ORG_SUBTREE`：先经 `org_engine.org_path(org_code)` 取 `path`；子句 `column IN (SELECT id FROM organization WHERE code = ? OR path = ? OR path LIKE ?)`（`path LIKE f"{path}/%"`）。
  - `SELF`：`person_id = ?`（取上下文 `person_id`）。
  - `enforce` 且缺少定位信息 → `["1 = 0"]`（越权空集）。

`DPS/src/engines/query_engine.py`：
- `_build_where_clauses` 末尾追加 `await build_scope_predicate()` 的子句与参数（覆盖 `search_portraits`、`advanced_search`、`get_statistics`）。
- `_build_stats_cache_key` 纳入 scope 指纹（`mode/scope/org_id/org_code` 的 SHA1），防止跨范围缓存串读。

`DPS/src/middleware/permission_middleware.py`：
- 新增 `_apply_scope_context(request)`：`org_id = request.state.org_id or X-Org-ID`；`org_code = X-Org-Code`；`role = get_user_role()`；`person_id = X-Person-ID or user_id`；`scope = resolve_scope(role)`；`set_scope_context(...)`。
- 在 `dispatch` 的 `call_next` 前设置，`finally` 中 `clear_scope_context()`；`warn` 模式只记录不拦截。

## 5. B-05 PII enforce

`DPS/src/config.py`：`pii_mode` 默认值改为 `"enforce"`（保留 `DPS_PII_MODE` 覆盖）；注释说明回滚到 `warn`。

`DPS/src/security/pii_serializer.py`：
- `serialize_record(record, entity_type, mode=None, allow_l3=False, allow_l4=False)`：
  - `enforce` 下 L3：`allow_l3` 时透传，否则掩码；L4：`allow_l4` 时透传，否则剔除。
- 新增 `async viewer_flags(user_id) -> tuple[bool, bool]`：调用 `permission_engine.get_user_permissions`，识别 `dps:pii:view` / `dps:pii:high`；引擎缺失 → `(False, False)`。
- 新增 `async serialize_records_for_user(records, entity_type, user_id)`：按 `viewer_flags` 计算模式与放行位；`off` 原样返回。
- `serialize_records` 同步版保留，新增 `allow_l3/allow_l4` 透传。

`DPS/src/engines/permission_engine.py`：
- `PRESET_PERMISSIONS` 增加 `("dps:pii", "view")`、`("dps:pii", "high")`、`("organization", "update")`。
- `admin`：`dps:pii:view`、`dps:pii:high`、`organization:update`；`operator`：`dps:pii:view`；`readonly`：无。

`DPS/src/rest_api/routes/routes_profiles.py`：
- `/portrait/list` 增加 `request: Request`，改用 `await serialize_records_for_user(items, "profile", 当前用户)`。
- 画像详情、`dimension-details`、标注列表/详情读路径同样接入（`entity_type="annotation"` 的字段为 `fields.*`）。
- 日志不得出现字段值；错误只记字段路径。

`DPS/src/engines/ingest_engine.py`：错误行落库与返回前统一走 `serialize_records_for_user(entity_type="profile")`，确保错误 CSV 不含明文。

## 6. B-06 / B-07 / B-08 引入落库

新增 `DPS/src/engines/ingest_engine.py`：
- `create_task(file_name, file_format, file_path, field_mapping, trigger_source="manual", tenant_id=None) -> dict`：写 `import_task`（status=pending）。
- `preview(file_path, file_format, field_mapping, limit=10, entity_type="profile") -> dict`：读取前 N 行 → 字段映射 → 脱敏（`serialize_records_for_user`）→ 返回 `{rows, total_sampled, mapping}`。
- `execute(task_id, profile_template_code=None, annotation_template_code=None) -> dict`：
  1. 任务不存在 → `{"status":"error"}`；已 `completed` → 返回既有摘要（幂等）。
  2. 读取全量行，逐行映射与校验（缺 `person_id` 记错误行）。
  3. 按 `(person_id, tenant_id)` upsert `profile`：存在则 `UPDATE name/attributes_json/updated_at`，不存在则 `INSERT`；`attributes_json` 写入 `mapped["attributes"]` 或其余字段集合。
  4. 更新 `import_task` 计数与 `errors_json`（错误记录已脱敏）。
  5. `annotation_template_code` 非空且任务成功 → `generate_annotation_tasks(...)`。
- `generate_annotation_tasks(batch_id, profile_template_code, annotation_template_code, person_ids)`：
  - 查 `annotation_template`（`code=? AND status='active'` 且 `template_code=profile_template_code`）；
  - 对每个 profile 以 `ingest_batch_id+batch_id` 幂等插入 `annotation`：`review_status='pending'`、`generated_by='ingest'`、`content='引入任务自动生成，待人工标注'`、`annotation_type='ingest'`、`payload='{}'`；
  - 不自动通过审核。
- `list_tasks(status=None, page=1, page_size=20)`、`get_task(task_id)`、`retry_task(task_id)`（清空错误并重新执行）、`get_errors(task_id)`（脱敏）。

新增 `DPS/src/rest_api/routes/routes_ingest.py`：
| 方法 | 路径 |
|---|---|
| POST | `/ingest/preview` |
| POST | `/ingest/execute` |
| GET | `/ingest/tasks` |
| GET | `/ingest/tasks/{task_id}` |
| POST | `/ingest/tasks/{task_id}/retry` |
| GET | `/ingest/tasks/{task_id}/errors` |

注册：`_build_prefixed_router` 增加 `ingest_router`；`PATH_RESOURCE_MAP` 增加 `"ingest": "batch"`，复用 `batch:create/read` 权限点。

`DPS/src/engines/batch_engine.py`：
- `execute_import`：`settings.ingest_persist_enabled` 为真时委托 `IngestEngine`（共享 file_path/mapping），并回写内存任务状态；为假保持现有模拟路径。
- `create_import_task`：开关为真时同步创建 `import_task` 并记录 `persisted_task_id`。

`DPS/src/engines/datasource_engine.py`：
- 新增 `async _persist_sync_task(task, watermark=None)`：开关为真时 upsert `sync_task`（`id/datasource_id/target_table/sync_mode/status/last_sync_at/records_synced/error_message/org_id/tenant_id/watermark`）。
- `create_sync_task` / `execute_sync` / 状态更新处调用；`watermark` 取本轮数据的最大 `updated_at` 或 `None`。
- 表缺失或 DB 未初始化 → WARN 并跳过（不阻断既有内存路径）。

## 7. B-09 / B-10 前端与 OpenBase 代理

### 7.1 OpenBase 代理（`openbase/modules/dps_proxy/__init__.py`）
- 新增 `_v2_upstream_path(path) -> f"/api/v2/{path}"`（与 `_portrait_upstream_path` 并列）。
- 新增端点（均 `Depends(get_current_user)`，经 `_build_identity_headers` 注入身份）：
  - `GET /orgs`、`GET /orgs/tree`、`GET /orgs/{code}/members`、`PUT /orgs/{code}/members`
  - `POST /ingest/preview`、`POST /ingest/execute`
  - `GET /ingest/tasks`、`GET /ingest/tasks/{task_id}`、`POST /ingest/tasks/{task_id}/retry`、`GET /ingest/tasks/{task_id}/errors`
- 路由顺序：`/ingest/tasks`、`/ingest/preview` 等静态段先于 `/ingest/tasks/{task_id}` 注册。

### 7.2 前端
- `openbase-ui/src/core/api/dps.ts`：新增类型 `DpsOrgNode`、`DpsOrgMember`、`DpsIngestTask`、`DpsIngestPreview`；方法 `listOrgs/getOrgTree/listOrgMembers/upsertOrgMembers/previewIngest/executeIngest/listIngestTasks/getIngestTask/retryIngestTask/getIngestTaskErrors`，全部走 `/api/v1/dps-proxy/*`。
- 新增 `components/common/OrgTreeSelect.vue`：`el-tree-select`，props `modelValue/orgs/placeholder`，emit `update:modelValue`。
- 新增 `components/common/PiiMaskedField.vue`：props `value/masked/level`；掩码时显示值并附「申请查看」提示，不自行解密。
- 新增 `modules/portrait/components/MappingTable.vue`：字段映射表格（源字段/目标字段/示例值）。
- 新增 `modules/portrait/pages/IngestTasksView.vue`：三 Tab（全部/进行中/失败）、任务表、跳转详情、重试。
- 新增 `modules/portrait/pages/TaskDetailView.vue`：任务摘要、错误行表、错误 CSV 下载（后端已脱敏）、重试。
- `modules/portrait/pages/PortraitList.vue`：增加组织范围选择 `OrgTreeSelect`；姓名列改用 `PiiMaskedField`；越权空态提示。
- `modules/portrait/index.ts`：新增路由 `dps/ingest-tasks`、`dps/ingest-tasks/:id`，并加入导航「引入任务」。

## 8. 版本与留痕

- `DPS/src/config.py`、`src/__init__.py`、`src/mcp_server/constants.py` 版本升 `2.19.0`。
- 新增 `DPS/doc/development/DPS-画像波次B引入与权限-DevLogReport-v1.0.0.md`。
- 更新 `OpenBase/doc/design/OpenBase-画像优化升级三波次发布实施计划-v1.0.2.md` → `v1.0.3`，修订历史记录 B 波交付。
- 偏差（`sync_task.watermark` 不在原 DDL 清单）在 DevLogReport「偏差记录」中说明。

## 9. 验收与测试

### 9.1 自动化
- 新增 `DPS/src/tests/test_v2_19_wave_b.py`：
  - DDL 幂等（连续执行两次，列/表存在且摘要稳定）；
  - 组织树回填（根/子/孤儿）；
  - `org_member` 一人多岗、主岗唯一；
  - `data_scope` 四种范围谓词；`enforce` 缺 org → 空集；`off` 无额外谓词；
  - `query_engine` 列表在 `enforce` 下注入范围条件、缓存键含 scope；
  - PII：默认 `enforce` 下 L3 掩码、L4 剔除；`dps:pii:view` 见 L3 明文、仍不见 L4；
  - ingest：预览脱敏、执行落库、重复执行幂等、错误行定位且脱敏；
  - 标注自动生成：`pending` + `generated_by='ingest'`，重复执行不重复插入。
- 回归：`test_v2_18_wave_a.py`、`test_portrait_list_route.py`、`test_tenant_isolation.py`、`test_batch_async.py`。
- 静态：`python -m ruff check src`、`python -m flake8 src --max-line-length=120 --extend-ignore=E203,W503`。
- 前端：`npm run build`；OpenBase 代理测试 `pytest tests/test_dps_proxy*.py`。

### 9.2 人工门禁
- 功能：组织树/成员可查可维护；导入落库且幂等；标注任务自动生成；范围切换生效。
- 安全：默认掩码；导出/错误 CSV 无明文；日志无 PII；跨租户不可见。
- 兼容：`data_scope=off`、`ingest_persist=false` 时行为与 2.18.x 一致。
- 文档与推送：版本、修订历史、DevLogReport 齐全；两仓推送三远程。

## 10. 回滚

`DPS_DATA_SCOPE_MODE=off` → `DPS_PII_MODE=warn` → `DPS_INGEST_PERSIST_ENABLED=false`；停止新增写入，保留表与列，不做 DDL 回退。

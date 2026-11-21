# Spec：后端 T-DM-01~06 数据画像领域模型治理

| 项 | 内容 |
|---|---|
| 文档编号 | OpenBase-SPEC-DM-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | **[Approved] 已批准并实施** |
| 日期 | 2026-11-21 |
| 依据 | 《OpenBase-数据画像领域模型与关联关系设计说明》v1.1.1 §6（T-DM-01~06） |
| 范围 | DPS 后端（`D:\Trae CN\myproject\Dev\DPS`）＋ OpenBase 代理/前端适配 |
| 版本基线 | DPS 2.17.0；OpenBase 后端 1.8.0；OpenBase UI 1.9.1 |

## 1. 目标与边界

**目标**：按设计文档 §6 完成 T-DM-01~06 六项后端治理能力，补齐「停用门禁、版本失效、单一事实源、来源优先级、自动重算、维度词表跨层校验」，并完成 OpenBase 代理与前端的最小适配。

**不做**：不改默认六维画像口径与存储位置；不反转“标注模板 → 画像模板”归属；不引入消息中间件；不重构模板目录/子模板等并行在建能力。

## 2. 决策总览

| 任务 | 核心改动 | 开关（env） | 默认值 | 失败策略 |
|---|---|---|---|---|
| T-DM-01 | 提交门禁校验父画像模板 active；停用返回受影响数 | `DPS_ENFORCE_ACTIVE_PARENT` | `true` | 门禁开启 → 400 |
| T-DM-02 | 命名空间写入 `template_version`；读取派生 `stale` | 无（派生） | — | 缺版本按 stale=true |
| T-DM-03 | 保存期校验 `tag_bindings` 与评分规则一致 | `DPS_TAG_BINDING_CONSISTENCY` | `warn` | warn 不阻断；reject → 400 |
| T-DM-04 | 模板级 `source_precedence` 驱动择优 | 无（模板配置） | 不配置＝现状 | 配置非法 → 400 |
| T-DM-05 | 标签写入后按 person+template 去抖自动重算 | `DPS_TAG_CHANGE_RECALC_ENABLED` / `DPS_TAG_CHANGE_RECALC_DEBOUNCE_SECONDS` / `DPS_TAG_CHANGE_RECALC_MAX_RETRIES` | `true` / `5` / `2` | 失败重试后置 failed 并 ERROR 告警 |
| T-DM-06 | 保存期校验模板维度 ∈ 标签分类 `dimension_code` | `DPS_DIMENSION_VOCABULARY_CHECK` | `warn` | warn 不阻断；reject → 400 |

**向后兼容**：T-DM-03/04/06 未配置时行为与现状一致（warn 仅告警、不改变返回值中的既有字段）；T-DM-02 仅新增字段；T-DM-01 默认开启属于设计确认的行为收紧，提供开关回退。

## 3. 详细设计

### T-DM-01 停用画像模板的采集门禁

**文件**：`DPS/src/config.py`、`DPS/src/engines/annotation_template_engine.py`、`DPS/src/engines/template_engine.py`、`DPS/src/rest_api/routes/routes_profiles.py`

1. `config.py`（Settings）新增：
   - `enforce_active_parent: bool = os.getenv("DPS_ENFORCE_ACTIVE_PARENT", "true").lower() == "true"`
2. `AnnotationTemplateEngine.validate_annotation_submission`：
   - 在现有“标注模板存在/active/归属匹配”校验之后，若 `settings.enforce_active_parent` 为真，调用 `_assert_active_portrait_template(annotation_template["template_code"])`。
   - 复用现有异常文案（`归属的画像模板未激活: {code}（status=...）`），路由层已映射为 400。
3. `TemplateEngine` 新增公开方法：
   - `async def count_active_annotation_templates(self, code: str) -> int`：`SELECT COUNT(*) FROM annotation_template WHERE template_code = ? AND status = 'active'`，表缺失时返回 0（try/except 同 `_count_template_references`）。
4. `routes_profiles.py::_set_portrait_template_status`：
   - 停用（`status != "active"`）时调用上述方法，响应 `data` 追加：
     - `affected_annotation_templates: int`
     - `parent_gate_enforced: bool`（读设置）
   - 激活路径不追加该字段（保持现状）。
5. 历史标注只读查询、已提交数据不回滚。

### T-DM-02 模板版本对齐与画像 stale 标记

**文件**：`DPS/src/rest_api/routes/routes_profiles.py`

1. `_persist_template_namespace(person_id, template_code, payload)`：
   - 命名空间对象新增 `"template_version": payload.get("template_version")`（未取到则 `None`）。
2. `_execute_calc`：
   - 模板分支中从 `registry.get(template_code)` 取 `version`，写入 `payload["template_version"]`。
3. 新增纯函数（同文件）：
   ```python
   def _mark_namespace_stale(namespace: dict, current_version: Optional[str]) -> dict:
       """按当前模板版本派生 stale / stale_reason（不写库）。"""
   ```
   - `current_version is None` → `stale=True, stale_reason="template_missing"`
   - `namespace.template_version` 缺失 → `stale=True, stale_reason="version_unknown"`
   - 两者不等 → `stale=True, stale_reason="version_mismatch"`
   - 相等 → `stale=False`
   - 返回浅拷贝，不改原对象。
4. `GET /portrait/{person_id}` 与 `GET /portrait/by-external/{external_id}` 的 `template_code` 分支：
   - 查询当前模板版本（`TemplateEngine.get_template`，失败视为 `None`）；
   - `result["result_namespace"] = _mark_namespace_stale(namespace, current_version)`；
   - `result["stale"]`、`result["template_version"]`（命名空间版本）、`result["current_template_version"]`。
5. `GET /portrait/list` 新增可选参数：
   - `template_code: Optional[str] = Query(None)`
   - `stale: Optional[bool] = Query(None)`
   - 仅当传入 `template_code` 时，对每个 item 的 `attributes[template_code]` 计算 `item["stale"]`；`stale` 参数用于过滤（内存过滤，分页参数语义不变，过滤后按原分页切片前的全量集过滤——实现上先按 `result.items` 过滤再返回 `total=len(filtered)`）。
   - 传入 `stale` 但未传 `template_code` → 400（`stale 过滤必须同时指定 template_code`）。
6. 重算成功即写入新版本，`stale` 自然为 false；历史版本查询逻辑不变。

### T-DM-03 标签→维度绑定单一事实源

**文件**：`DPS/src/engines/template_engine.py`、`DPS/src/rest_api/routes/routes_profiles.py`

1. 新增纯函数（`template_engine.py` 模块级）：
   ```python
   def check_binding_rule_alignment(
       dimension_config: Any, tag_bindings: Any,
   ) -> list[dict]:
       """绑定维度/标签与评分规则的一致性差异（只读，不抛异常）。"""
   ```
   规则：
   - 评分事实源集合 = 所有 `dimension_config.dimensions[].rules[].tag_code`（去空）。
   - 维度集合 = `dimensions[].code`。
   - 每条 binding 的 `dimensions[]` 不在维度集合 → issue `{type:"binding_dimension_missing", severity:"WARN", dimension}`。
   - 若 binding 条目带 `tag_code` 且不在事实源集合 → issue `{type:"binding_tag_not_in_rules", severity:"WARN", tag_code}`。
   - 绑定引用的标注模板字段（`target_dimension` + `tag_key|key`）生成的 `tag_code` 不在事实源集合 → issue `{type:"producer_tag_not_consumed", severity:"WARN", tag_code, annotation_template}`。该部分需要 DB 读取标注模板字段，放在 async 方法中完成。
2. `TemplateEngine` 新增：
   ```python
   async def collect_binding_alignment(self, dimension_config, tag_bindings) -> list[dict]
   ```
   - 读取 binding 指向的标注模板 `field_schema`，合并上述纯函数结果。
3. `create_template` / `update_template` 保存期：
   - 调用 `collect_binding_alignment`；
   - 按 `settings.tag_binding_consistency`：
     - `reject` 且 issues 非空 → `TemplateValidationError("tag_bindings 与评分规则不一致: ...")`
     - `warn` 且 issues 非空 → `logger.warning(...)`，返回对象附 `"warnings": issues`
     - `off` → 跳过
   - 返回 dict 增加 `warnings`（仅 warn 模式且存在差异时）。
4. `GET /portrait/templates/{code}/preflight` 返回体追加 `binding_rule_alignment`（调用 `collect_binding_alignment`，只读）。
5. 文档/OpenAPI 说明补充字段语义：`tag_bindings` 仅治理/证据，评分只认 `dimension_config.rules[].tag_code`。

### T-DM-04 来源优先级显式化

**文件**：`DPS/src/engines/portrait/crud.py`、`DPS/src/engines/portrait/core.py`、`DPS/src/engines/template_engine.py`、`DPS/src/rest_api/routes/routes_profiles.py`

1. `crud.py`：
   ```python
   def pick_preferred_tags(rows, precedence: list[str] | None = None) -> dict[str, Any]
   ```
   - 未配置时完全沿用 `_SOURCE_PRIORITY`（manual_annotation=2 / legacy=0 / 其他=1）与 `created_at` 最新。
   - 配置时按 `precedence` 顺序映射优先级（索引越大越优先；未列出的来源优先级 0），同优先级取 `created_at` 最新。
   - 被选中行浅拷贝并附 `preferred_reason`：`"source_precedence"` 或 `"default"`，`preferred_source` 为来源名（供可解释性消费，不参与评分）。
2. `_get_existing_tags(person_id, precedence=None)`、`_get_tags_by_dimension(person_id, dimension, include_score=False, precedence=None)` 透传。
3. `calculate_portrait(..., source_precedence: list[str] | None = None)` 透传给上述两处。
4. `resolve_dimensions` 不承载 priority；`_execute_calc` 从模板 `dimension_config.source_precedence` 读取（`list[str]`，元素非空字符串，否则 400 `source_precedence 非法`），传入 `calculate_portrait`，并在 payload 回显 `source_precedence`。
5. 未配置时 `source_precedence` 不在 payload 中出现，保证响应向后兼容。

### T-DM-05 标签变更自动触发重算

**文件**：`DPS/src/config.py`、`DPS/src/ddl/schema_portrait.py`、`DPS/src/engines/portrait/recalc_scheduler.py`（新增）、`DPS/src/rest_api/routes/routes_profiles.py`

1. `config.py` 新增：
   - `tag_change_recalc_enabled: bool`（`DPS_TAG_CHANGE_RECALC_ENABLED`，默认 true）
   - `tag_change_recalc_debounce_seconds: int`（默认 5）
   - `tag_change_recalc_max_retries: int`（默认 2）
2. `schema_portrait.py`：`portrait_calc_task`（PG/SQLite 两份）新增 `retry_count INTEGER NOT NULL DEFAULT 0`。
3. 新增模块 `engines/portrait/recalc_scheduler.py`：
   ```python
   async def enqueue_tag_change_recalc(
       person_id: str, template_code: str, tenant_id: Optional[str], *, now: Optional[datetime] = None,
   ) -> dict:
   ```
   - 开关关闭 → `{"enqueued": False, "reason": "disabled"}`
   - `bucket = int(now.timestamp() // max(1, debounce_seconds))`
   - `idempotency_key = sha256(f"{tenant or ''}:{person_id}:{template_code}:auto:{bucket}")`
   - 命中同键且 `status != 'failed'` 的任务 → `{"enqueued": False, "reused": True, "task_id": ...}`
   - 否则插入 `portrait_calc_task(status='pending', retry_count=0)` → `{"enqueued": True, "task_id": ...}`
4. `_run_calc_task` 失败分支：
   - 读取 `retry_count`；若 `< settings.tag_change_recalc_max_retries` → `retry_count += 1` 并重试一次计算（循环上限即最大重试数）；仍失败置 `failed` 并 `logger.error`（告警留痕）。
5. `_apply_annotation_review`：
   - 新增可选参数 `background_tasks: Optional[BackgroundTasks] = None`；
   - `approved` 且 `tag_sync` 成功（`tag_sync` 非空）且模板 code 存在时调用 `enqueue_tag_change_recalc`；
   - 入队成功且 `background_tasks` 存在 → `background_tasks.add_task(_run_calc_task, task_id, person_id, template_code)`；
   - 响应增加 `recalc: dict`（enqueued/reused/task_id/reason）。
   - `person_id` 取 `tag_sync.person_id` 或联动上下文。
6. 单条与批量复核端点均透传 `BackgroundTasks`。

### T-DM-06 维度词表跨层保存期校验

**文件**：`DPS/src/engines/template_engine.py`、`DPS/src/rest_api/routes/routes_profiles.py`、`DPS/src/config.py`

1. `config.py` 新增 `dimension_vocabulary_check: str = os.getenv("DPS_DIMENSION_VOCABULARY_CHECK", "warn").lower()`，合法值 `off|warn|reject`。
2. `TemplateEngine` 新增：
   ```python
   async def collect_dimension_vocabulary_gaps(self, dimension_config: Any) -> list[dict]
   ```
   - 取模板维度 code 集合；
   - `SELECT DISTINCT dimension_code FROM tag_category`（表/列缺失 → 返回空，视为未配置词表，不阻断存量）；
   - 未命中的维度 → `{type:"dimension_not_in_tag_category", severity:"WARN", dimension_code}`。
3. `create_template` / `update_template` 保存期：
   - `off` 跳过；`warn` → 合并到返回 `warnings`；`reject` 且缺口非空 → `TemplateValidationError`。
4. `GET /portrait/templates/{code}/preflight` 追加 `dimension_vocabulary_gaps`（只读）。

## 4. 跨仓适配（OpenBase）

**文件**：`OpenBase/openbase/modules/dps_proxy/__init__.py`

1. `GET /api/v1/dps-proxy/portrait/list`（现有代理列表路由）新增查询参数透传：
   - `template_code`、`stale`（与 DPS `GET /portrait/list` 同名同义）。
2. 停用/回滚/详情/计算代理已存在（`/templates/{code}/deactivate`、`/templates/{code}/rollback`、`/portraits/calculate`），仅需回归验证响应新增字段可透传，不新增路由。
3. 不改变现有 22+12 条代理路由的路径、权限与错误体语义。

**测试**：`OpenBase/tests/test_dps_proxy_list_stale.py`（新增）覆盖 `stale` 参数透传与上游 400 保真。

## 5. 前端最小适配

**文件**：`OpenBase/openbase-ui/src/modules/portrait/pages/PortraitList.vue`、`OpenBase/openbase-ui/src/modules/portrait/pages/DpsTemplateListView.vue`

1. 画像结果页：
   - 「列设置」新增 `stale` 列（默认可见），展示 `stale=true` 时标签「口径已过期」并附 `stale_reason` tooltip；
   - 工具栏新增「仅看过期」开关，调用列表时带 `template_code`（默认模板 code，前端常量 `dps-correction-v1`）与 `stale=true`。
2. 画像模板页：
   - 停用确认框展示接口返回的 `affected_annotation_templates`（“将影响 N 个标注模板的提交”）；
   - `parent_gate_enforced=false` 时提示门禁已关闭。
3. 新增/更新前端用例：
   - `tests/portrait-list-stale.spec.ts`：stale 列渲染、仅看过期请求参数；
   - `tests/portrait-template-deactivate-impact.spec.ts`：受影响数提示。

## 6. 测试计划

| 层 | 文件 | 覆盖 |
|---|---|---|
| DPS 单测 | `DPS/src/tests/test_dm_domain_model_v2_17.py`（新增） | T-DM-01~06 全部验收点；含开关开/关、warn/reject、去抖合并、版本 stale 链路 |
| DPS 回归 | `DPS/src/tests/test_annotation_template_v2_10.py` 等既有用例 | 默认行为不回归 |
| OpenBase | `OpenBase/tests/test_dps_proxy_list_stale.py`（新增） | 代理参数透传/错误保真 |
| 前端 | 上述两个 spec | 展示与请求参数 |

**验证命令**（串行、禁用仓库 addopts）：

```powershell
# DPS
D:\Python\python.exe -m pytest src/tests/test_dm_domain_model_v2_17.py -o addopts="" -p no:cacheprovider
D:\Python\python.exe -m pytest src/tests -o addopts="" -p no:cacheprovider
# OpenBase
D:\Python\python.exe -m pytest tests/test_dps_proxy_list_stale.py -o addopts=""
D:\Python\python.exe -m pytest tests -o addopts=""
# 前端
cd openbase-ui; node node_modules/vitest/vitest.mjs run tests/portrait-list-stale.spec.ts tests/portrait-template-deactivate-impact.spec.ts; npm run build
```

## 7. 回滚方案

| 任务 | 回滚 |
|---|---|
| 01 | `DPS_ENFORCE_ACTIVE_PARENT=false` 即恢复旧提交行为；响应新增字段无破坏 |
| 02 | 新增字段为派生；无需回滚数据。前端关闭「仅看过期」即可 |
| 03 | `DPS_TAG_BINDING_CONSISTENCY=warn/off` 降低强度 |
| 04 | 删除模板 `source_precedence` 即恢复默认择优 |
| 05 | `DPS_TAG_CHANGE_RECALC_ENABLED=false` 关闭自动任务；新增列有默认值，可保留 |
| 06 | `DPS_DIMENSION_VOCABULARY_CHECK=off/warn` |

## 8. 交付物与留痕

- 设计文档升版 v1.1.1：T-DM-01~06 状态改为「已实施」，补修订历史。
- 开发记录、测试报告、部署报告各一份（按项目文档规范命名）。
- 版本：DPS 2.16.0 → 2.17.0；OpenBase 后端 1.7.0 → 1.8.0；前端 1.9.0 → 1.9.1。
- 两仓分别提交并推送 origin/backup/github 三远程。

## 9. 批准清单

- [ ] 认可 6 项任务的实现点与开关默认值
- [ ] 认可 T-DM-01 默认开启（行为收紧）并提供回退开关
- [ ] 认可 T-DM-02 以 `template_version` 派生 `stale`、不改表结构
- [ ] 认可 T-DM-03/06 默认 `warn`、可切 `reject`
- [ ] 认可 T-DM-05 以时间桶去抖 + 复用 `portrait_calc_task` 幂等键
- [ ] 批准后按 `tasks.md` 顺序执行

# 批次 2 实施规格（R1 / R3 长期 / R6 / R8）

| 项 | 内容 |
|---|---|
| **版本** | v1.0.2 |
| **状态** | [Final] |
| **适用范围** | OpenBase / OpenLLM / OpenMemory / OpenRAG / DPS |
| **依据** | 《OpenBase-四基础子系统全链路贯通修复方案-v1.0.0》v1.4.0 §4 批次 2；《…审计报告-v1.0.0》R1/R3/R6/R8 |
| **作者** | 架构组 |
| **日期** | 2026-11-12 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-12 | 首版：批次 2 四项（R1/R3 长期/R6/R8）的现状核对、逐文件改动、契约、验证与回滚 | 架构组 |
| v1.0.1 | 2026-11-12 | 确认四项决策：R1 复用现有 `version`；R3 门户默认 `async=true`；四项一次做完；文档落位保持 `doc/design/批次2-全链路贯通修复/` | 架构组 |
| v1.0.2 | 2026-11-12 | 按规格完成实施：R8/R6/R1/R3 全部代码与用例落地；补充实现期偏差（R6 tag 用文本近似匹配、无需 `cast`；R3 `result_json` 用 TEXT） | 架构组 |

---

## 1. 现状核对（已读源码结论）

| 条目 | 现状 | 缺口 |
|---|---|---|
| R8 | OpenRAG 已有 `POST /api/v1/collections/{cid}/documents/{id}/reindex`（`OpenRAG/src/openrag/api/routes/documents.py:492-538`），状态回 `PENDING` | OpenBase `rag_proxy` 无该代理路由；前端无重试入口；无重复提交限流 |
| R6 | OpenBase `memory_list` 以 `POST /recall`（top_k=500）+ 本地过滤分页（`openbase/modules/proxy/memory_proxy.py:417-484`） | OpenMemory 无原生分页列表；`total` 不稳定 |
| R1 | DPS `PUT /api/v2/portrait/{id}` 整体覆盖 `attributes_json`（`DPS/src/rest_api/routes/routes_profiles.py:1812-1839,1648-1650`），已有 `version` 乐观锁；OpenLLM 回写走 PUT（`OpenLLM/backend/app/edgerouter/adapters/profile.py:403-453`） | 无 PATCH 深合并；回写无冲突重放 |
| R3 长期 | DPS `POST /portrait/calculate` 同步执行（`routes_profiles.py:127-162`） | 无 202 + task_id、无任务查询、无幂等 |

**与方案原文的偏差（需批准）**：R1 复用 DPS 既有 `profile.version` 乐观锁，不新增 `attributes_version` 列（避免 DDL 迁移与双版本语义冲突）；R3 任务表使用 TEXT 存 `result_json`（PG/SQLite 通用）。两项偏差在实现记录中留痕。

---

## 2. R8 索引失败重试

### 2.1 OpenRAG（限流）

文件：`OpenRAG/src/openrag/api/routes/documents.py`

1. 模块级新增（放在 `reindex_document` 之前）：

```python
import threading, time
REINDEX_COOLDOWN_SECONDS = 60
_reindex_last_submitted: dict[tuple[str, str], float] = {}
_reindex_lock = threading.Lock()
```

2. `reindex_document` 内、scope 校验通过后：

- 以 `(tenant_code, document_id)` 为键，在 `_reindex_lock` 内判断距上次提交是否 `< REINDEX_COOLDOWN_SECONDS`；
- 命中则 `raise HTTPException(status_code=429, detail={"error": "BIZ_REINDEX_THROTTLED", "message": "重试过于频繁，请 60 秒后再试"})`；
- 提交后台任务前在同一锁内写入 `time.monotonic()`。

3. 不改索引任务本身；`doc_id` 不变。

### 2.2 OpenBase 代理

文件：`openbase/modules/rag_proxy/__init__.py`

新增路由（与 527-543 的文档详情路由同款转发助手）：

```python
@router.post("/collections/{collection_id}/documents/{document_id}/reindex")
async def rag_document_reindex(collection_id: str, document_id: str, request: Request, _user: dict = Depends(get_current_user)) -> JSONResponse:
    """重建索引（POST /api/v1/collections/{cid}/documents/{did}/reindex，R8）."""
    return await <同文件既有转发函数>(
        "POST",
        f"/api/v1/collections/{collection_id}/documents/{document_id}/reindex",
        request=request, user=_user,
    )
```

- 上游 429 原样透传（前端按 429 展示限流提示）。
- 审计：结构化日志 `rag.document.reindex`（document_id、collection_id、tenant、subject、request_id）。

### 2.3 前端

- `openbase-ui/src/core/api/rag.ts`：新增

```ts
async retryDocument(collectionId: string, documentId: string): Promise<unknown> {
  const { data } = await http.post<{ code: number; data: unknown }>(
    `/rag-proxy/collections/${encodeURIComponent(collectionId)}/documents/${encodeURIComponent(documentId)}/reindex`,
  )
  return data.data
}
```

- `openbase-ui/src/pages/platform/developers/KnowledgeAdminView.vue`：文档表格操作列新增「重试」按钮，仅在 `row.status ∈ {error, failed, ERROR, FAILED}` 显示；点击调用 `ragApi.retryDocument(currentDocCollectionId.value, row.id)`，成功提示后复用既有轮询刷新；429 时提示「重试过于频繁，请稍后再试」。

### 2.4 验收

- `ERROR` 文档重试后 `PENDING → SUCCEEDED`，`doc_id` 不变；
- 60 秒内二次重试返回 429；
- 跨租户重试返回 404。

---

## 3. R6 记忆列表原生分页

### 3.1 OpenMemory 存储层

文件：`OpenMemory/src/openmemory/storage/relational_store.py`（在 `list_all_memories` 后新增）

```python
async def list_memories_paginated(
    self,
    scope: dict[str, Any] | None,
    *,
    memory_type: str | None = None,
    tag: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """按归属域原生分页列出活跃记忆（R6）。"""
```

- `resolved = self._prepare_scope(scope, method="list_memories_paginated")`（fail-closed，`org_wide` 语义与 `get_memory_metadata` 一致）；
- 过滤：`is_active == True`；`tenant_code == resolved["tenant_code"]`（非 None 时）；`owner == resolved["owner"]`（resolved 含 owner 且未 org_wide 时）；
- `memory_type` 精确匹配；
- `tag`：`cast(MemoryMetadataTable.metadata_json, String).like(f'%"{tag}"%')`（PG TEXT/JSONB 与 SQLite 通用，注释说明为近似匹配）；
- `total`：同过滤条件的 `select(func.count()).select_from(...)`；
- `items`：`order_by(updated_at.desc(), id.asc()).offset(offset).limit(limit)`，用 `_metadata_row_to_dict` 归一；
- 返回 `{"items": [...], "total": int, "offset": offset, "limit": limit}`。

### 3.2 OpenMemory 服务层

- `memory/session_persistent.py` `PersistentMemory` 新增：

```python
async def list_memories(self, scope, *, memory_type=None, tag=None, offset=0, limit=20) -> dict[str, Any]:
    fn = getattr(self._metadata_store, "list_memories_paginated", None)
    if fn is None:
        raise NotImplementedError("metadata_store 不支持原生记忆分页")
    return await fn(scope, memory_type=memory_type, tag=tag, offset=offset, limit=limit)
```

- `memory/service.py` `MemoryService` 新增同名薄封装，委托 `self._dual_memory.persistent_store.list_memories`。

### 3.3 OpenMemory 控制器

文件：`OpenMemory/src/openmemory/api/controllers.py`

新增（放在 `get_memory` 之前）：

```python
@router.get("/memories")
async def list_memories(
    http_request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    memory_type: str | None = Query(None),
    tag: str | None = Query(None),
    service: MemoryService = Depends(get_memory_service),
) -> dict[str, Any]:
```

- `scope = _memory_scope(http_request)`；
- 调 `service.list_memories(...)`；
- 每条归一：`memory_id` ← `id`，`tags` ← `metadata.tags or []`；
- 返回 `{"data": {"items": [...], "total": ..., "offset": ..., "limit": ...}}`；
- `NotImplementedError` → `HTTPException(501, {"error": "LIST_NOT_IMPLEMENTED", ...})`。

### 3.4 OpenBase 代理改造

文件：`openbase/modules/proxy/memory_proxy.py` `memory_list`

1. 先请求 `GET /api/v1/memories`，参数 `offset=(page-1)*page_size`、`limit=page_size`、`memory_type`、`tag`；
2. 200 且 `body["data"]["items"]` 存在 → 直接组装现有信封 `{code,message,data:{items,total,page,page_size},timestamp}` 返回；
3. 404 / 405 / 501 → 回退现有 recall 适配逻辑（保持原样，作为兼容路径）；
4. 其余错误原样映射。

### 3.5 验收

- 1000 条记忆下任意页 `items` 数量恒定，`total` 稳定等于真实条数；
- 翻页无重复/漏项；
- 上游不支持时自动回退 recall，行为不劣化。

---

## 4. R1 画像深合并 + 乐观锁

### 4.1 DPS 新增 PATCH

文件：`DPS/src/rest_api/routes/routes_profiles.py`

1. 新增纯函数：

```python
def _deep_merge_attributes(existing: dict[str, Any], patch: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """dict 递归合并；list 去重追加；标量覆盖；None 删除该键；返回 (merged, diff_paths)。"""
```

- `patch["__delete__"]`（list[str]，点分路径）先执行删除，再合并其余键；
- `diff_paths` 记录发生变化的点分路径（不记录值）；
- 不修改入参（深拷贝）。

2. 新增路由（置于 `PUT /portrait/{person_id}` 之后）：

```python
@router.patch("/portrait/{person_id}")
async def api_patch_portrait(
    person_id: str,
    data: Dict[str, Any],
    if_match: Optional[str] = Header(None, alias="If-Match"),
    x_org_id: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None),
):
```

逻辑：

- `person_updates, attributes = _parse_portrait_update_body(data)`；
- `existing = await _fetch_portrait_row(person_id, tenant_id)`；缺失 → 404「画像不存在」；
- `If-Match` 存在且 `int(if_match) != int(existing["version"])` → `BaseError(DpsErrorCode.BIZ_VERSION_CONFLICT, detail={person_id, tenant_code, expected_version, current_version})`；
- `attributes is None` 时仅更新 person；
- 否则 `current = _decode_json_value(existing["attributes_json"]) or {}`，`merged, diff_paths = _deep_merge_attributes(current, attributes)`；
- `before_hash = sha256(canonical(current))`，`after_hash = sha256(canonical(merged))`；
- 调 `_persist_portrait_update(person_id, person_updates, merged, org_id, tenant_id)`（其内部 `WHERE version` 保证并发安全，冲突仍返回 409）；
- 结构化日志：`profile.patch`（person_id、tenant、before_hash、after_hash、diff_paths、request_id 若可得）；
- 返回 envelope，`data` 追加 `attributes_version`（= 更新后 `version`）。

3. `_persist_portrait_update` 响应 `data` 增加 `"version": next_version`（附加字段，不破坏既有消费方）。

### 4.2 OpenBase 代理

文件：`openbase/modules/dps_proxy/__init__.py`

新增（紧跟 395-420 的 PUT 路由）：

```python
@router.patch("/portraits/{person_id}")
async def dps_portrait_patch(person_id: str, payload: dict[str, Any], request: Request, _user: dict = Depends(get_current_user)) -> JSONResponse:
    headers = _build_identity_headers(_user, request)
    if_match = request.headers.get("If-Match")
    if if_match:
        headers = {**headers, "If-Match": if_match}
    return await _forward("PATCH", f"/api/v2/portrait/{person_id}", json_body=payload, headers=headers, request=request)
```

### 4.3 OpenLLM 合并回写

1. `OpenLLM/backend/app/edgerouter/adapters/dps_client.py` `profile_update` 增加关键字参数 `patch: bool = False, if_match: int | str | None = None`；`patch=True` 时方法用 `PATCH`；`if_match` 非空时 headers 追加 `If-Match`。
2. `OpenLLM/backend/app/edgerouter/adapters/profile.py` `_update_profile_real`：
   - 读配置 `PROFILE_WRITEBACK_MERGE`（默认 `True`，加到现有 Settings 类，环境变量 `PROFILE_WRITEBACK_MERGE`）；
   - 开启时先 `profile_update(..., patch=True)`；
   - 捕获 `ComponentUnavailableError` 且消息含 `409` 或 `BIZ_VERSION_CONFLICT` → 重读一次（`profile_update(..., patch=True)`，DPS 侧每次重新读合并）并记 `writeback=conflict_retry`；仍失败则记 `writeback=conflict` 并返回 `{"ok": False, "skipped": "conflict"}`，不阻塞对话；
   - 关闭时保持现有 PUT 路径不变。
3. 成功/跳过/冲突均在日志中标注 `writeback=merged|conflict|conflict_retry|skipped|put`。

### 4.4 验收

- 同 person 先 `{tags:["A"]}` 后 `{tags:["B"]}` → GET `{tags:["A","B"]}`；
- 两个模板命名空间互不覆盖；
- 并发写触发 409，重放后成功，日志含 `conflict_retry`；
- `PROFILE_WRITEBACK_MERGE=false` 时行为与现网一致。

---

## 5. R3 长期 画像异步计算（202 + task_id）

### 5.1 DPS 任务表

文件：`DPS/src/ddl/schema_portrait.py` 新增 `"portrait_calc_task"` DDL（PG + SQLite 两方言）：

```sql
CREATE TABLE IF NOT EXISTS portrait_calc_task (
  id TEXT PRIMARY KEY,
  person_id TEXT NOT NULL,
  tenant_id TEXT,
  template_code TEXT,
  status TEXT NOT NULL,             -- pending|running|succeeded|failed
  idempotency_key TEXT NOT NULL,
  data_version INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  result_json TEXT,
  created_at TEXT/TIMESTAMPTZ NOT NULL,
  started_at TEXT/TIMESTAMPTZ,
  finished_at TEXT/TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_portrait_calc_task_idem ON portrait_calc_task(idempotency_key);
CREATE INDEX IF NOT EXISTS ix_portrait_calc_task_person ON portrait_calc_task(person_id, created_at);
```

`DPS/src/database.py`：在 `_init_schema`（PG）与 `_init_sqlite_schema` 各追加一次 `portrait_ddl("portrait_calc_task", <DIALECT>)`。

### 5.2 DPS 路由

文件：`DPS/src/rest_api/routes/routes_profiles.py`

1. 抽取 `async def _execute_calc(person_id: str, template_code: str | None) -> dict[str, Any]`：复用现 142-162 的计算 + 模板命名空间持久化逻辑。
2. `api_calculate_portrait` 增加查询参数 `async_mode: bool = Query(False, alias="async")`：
   - `False`：行为与现网一致；
   - `True`：
     - `data_version = int(current_profile.version or 0)`（无画像按 0）；
     - `idem = sha256(f"{tenant}:{person_id}:{template_code or ''}:{data_version}")`；
     - 查 `status != 'failed'` 且 `idempotency_key=idem` 的最后一条 → 直接返回 202 同 task_id；
     - 否则插入 `id`（uuid4 hex）、`status='pending'`、`created_at=now`；
     - `background_tasks.add_task(_run_calc_task, task_id, person_id, template_code)`；
     - 返回 `{"code": 202, "message": "accepted", "data": {"task_id": ..., "status": "pending"}}`。
3. `_run_calc_task(task_id, person_id, template_code)`：`running` + `started_at` → `_execute_calc` → `succeeded` + `result_json` + `finished_at`；异常 → `failed` + `error`（截断 500 字）+ `finished_at`，结构化日志；单次失败不重试（后台任务由调用方决定重试）。
4. 新增（放在动态 `/portrait/{person_id}` 之前）：
   - `GET /portrait/tasks/{task_id}` → 任务详情（含 `result` 解析后的 JSON）；
   - `GET /portrait/{person_id}/tasks?status=` → 最近 20 条。
5. `from fastapi import BackgroundTasks` 补充导入。

### 5.3 OpenBase 门户

文件：`openbase/modules/dps_proxy/__init__.py`

1. `dps_portrait_calculate`：当 `get_settings().dps_calc_async_default` 为真且 payload 未显式含 `"async"` 时，转发体注入 `{"async": True}`。
2. 新增 `GET /portraits/tasks/{task_id}` → `_forward("GET", f"/api/v2/portrait/tasks/{task_id}", ...)`，需放在 `/portraits/{person_id}` 路由之前声明（避免 `person_id="tasks"` 误匹配）。
3. `openbase/settings.py` 新增 `dps_calc_async_default: bool = True`。

### 5.4 前端

文件：`openbase-ui/src/core/api/dps.ts`

1. `calculatePortrait(payload)`：保持现有 504 提示；返回体若含 `task_id` 原样返回。
2. 新增 `getPortraitTask(taskId)` → `GET /dps-proxy/portraits/tasks/{id}`。
3. 新增 `waitPortraitTask(taskId, { intervalMs = 2000, timeoutMs = 60000 })`：2s 轮询，超时抛「计算超时，请在详情页刷新确认」。
4. 当前无页面调用 `calculatePortrait`，本轮不新增 UI 调用点（避免死代码）；页面接入时直接使用上述 helper（在实现记录注明）。

### 5.5 验收

- 10s 以上计算返回 202+task_id，最终 `succeeded` 且结果可查；
- 同参数重复提交只产生 1 条非失败任务；
- `async=false` 行为与现网一致；
- 门户默认异步，前端 helper 可在 60s 内完成轮询。

---

## 6. 验证方案

| 仓 | 命令 |
|---|---|
| OpenBase | `D:\venvs\openbase\Scripts\ruff.exe check openbase tests`；`D:\venvs\openbase\Scripts\python.exe -m pytest tests -q`（定向新增用例） |
| OpenBase 前端 | `openbase-ui` 下 `.\node_modules\.bin\vue-tsc.cmd --noEmit` |
| DPS | `python -m pytest src/tests -q`（定向新增用例） |
| OpenMemory | `python -m pytest tests -q`（定向新增用例） |
| OpenRAG | `python -m pytest tests -q`（定向新增用例） |
| OpenLLM | `python -m pytest backend/tests -q`（定向新增用例） |

已知既有噪声：OpenBase `tests/test_settings.py::test_dps_upstream_defaults_aligned_to_source_port` 在全量串跑时偶发环境/顺序污染，单跑通过，与本批次无关。

## 7. 回滚

| 条目 | 回滚方式 |
|---|---|
| R8 | 移除门户 reindex 路由与前端按钮；OpenRAG 限流常量置 0 |
| R6 | 门户 `memory_list` 回退 recall 分支（代码保留），OpenMemory 新端点不调用即无影响 |
| R1 | `PROFILE_WRITEBACK_MERGE=false`；DPS PATCH 无调用方即无影响 |
| R3 | `dps_calc_async_default=false`（门户回同步）；任务表保留 |

## 8. 交付纪律

- 每仓独立 commit，提交信息 `feat(<repo>): 批次2 <条目> …`；
- 文档留痕：本规格 + 修复方案文档升版本（v1.4.0 → v1.5.0）并追加修订历史；
- 推送三远程（origin/backup/github），分支 main；
- 不包含用户既有改动：`openbase-ui/src/core/api/llm.ts`、`Playground.vue`、`scripts/service-orchestrator.ps1`。

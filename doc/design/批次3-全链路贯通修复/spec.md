# 批次 3 全链路贯通修复规格说明（R7 / R9 / R2）

| 项 | 内容 |
|---|---|
| **版本** | v1.1.0 |
| **状态** | [Review] |
| **适用范围** | OpenBase / OpenLLM / DPS / OpenRAG |
| **上游依据** | 《OpenBase-四基础子系统全链路贯通审计报告-v1.0.0》R7/R9/R2；《全链路贯通修复方案-v1.5.0》§0 批次 3 |
| **作者** | 架构组 |
| **日期** | 2026-11-12 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-12 | 首版：批次 3 三项（R7 裁剪策略可配、R9 画像 person_id 口径、R2 知识库唯一事实源）的改动文件、接口契约、开关、验证与回滚 | 架构组 |
| v1.1.0 | 2026-11-12 | 实施完成：R7/R9/R2 落地、验证结果与 7 项偏差（仅 external_id 更新、documents 无 /text、代理响应 dict、配置/脚本实际路径、门户测试复用、前端延后）；详见 `tasks.md` 实施记录 | 架构组 |

---

## 1. 范围与总原则

本批次只做三件事，按风险从低到高依次实施：

| 顺序 | 编号 | 目标 | 改动仓 |
|---|---|---|---|
| 1 | R7 | 上下文裁剪策略可配 + 响应回显 `context_meta` | OpenLLM、OpenBase |
| 2 | R9 | 画像 `external_id` 映射与 by-external 查询 | DPS、OpenBase、OpenLLM |
| 3 | R2 | OpenRAG 成为知识库唯一事实源（代理化 → 迁移 → 只读） | OpenLLM（消费 OpenRAG 既有接口，OpenRAG 零改动） |

统一约束（继承方案 §0）：

1. 新增配置项一律**默认保持现网行为**：`OPENLLM_KB_PROXY_ENABLED=false`、`OPENLLM_KB_READONLY=false`；R7/R9 为纯增量字段与端点，不改变既有默认语义。
2. 错误响应保持 `{code, message, detail, request_id}`（DPS 保持既有 `BaseError` 信封）。
3. 不提交用户既有未提交改动（`openbase-ui/src/core/api/llm.ts`、`Playground.vue`、`scripts/service-orchestrator.ps1` 等）。
4. 数据库变更幂等（PG `IF NOT EXISTS` / SQLite PRAGMA 探测后 ALTER）。
5. 本批次不做前端页面改动；R7 的"可配"通过 API 契约提供，门户设置页展示留待批次 4（避免与用户未提交的前端文件冲突）。

---

## 2. R7 上下文裁剪策略可配

> **[已实现 v1.1.0｜批次 3]** `history.py` 新增 `build_history_selection`（四策略 +
> 统计），`build_history_ctx` 增加 `strategy/preserve_recent_n`；网关
> `OpenLLMChatRequest.context_policy` + `_resolve_context_policy`（非法 4003），
> 同步 `data.context_meta`、流式 `event: routing` 回显；门户
> `_validate_context_policy`（400 `PARAM_INVALID`）+ `_with_context_meta`
> （上游缺失时补 `source=openbase-default, applied=false`）。不传策略时与旧实现
> 逐字一致（单测断言）。前端设置页展示按 §1 约定延后至批次 4。

### 2.1 现状与目标

现状：OpenLLM 仅按 token 预算"丢最旧保最近"（`backend/app/edgerouter/orchestration/history.py::build_history_ctx`），策略对调用方不可见、不可选。
目标：门户 chat 请求可带 `context_policy`，OpenLLM 按策略裁剪，响应回显 `context_meta`；不传时行为与现网**逐字一致**。

### 2.2 接口契约

请求（OpenLLM `/openllm/v1/chat`、`/openllm/v1/chat/stream`；门户 `/api/v1/llm-proxy/chat`、`/chat/stream` 原样透传）：

```json
{
  "model": "qwen3-8b",
  "messages": [{"role": "user", "content": "..."}],
  "session_id": "s-1",
  "context_policy": {
    "strategy": "recent | head_tail | system_priority | summarize_old",
    "max_tokens": 2048,
    "preserve_recent_n": 4
  }
}
```

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `strategy` | string | 否 | 缺省 `recent`；不在白名单 → 4003 `context_policy.strategy 不支持: <值>` |
| `max_tokens` | int | 否 | 缺省沿用现有窗口预算；`<=0` 或非整数 → 4003 |
| `preserve_recent_n` | int | 否 | 仅 `system_priority` 使用；`<0` → 4003 |

响应新增（同步 `data.context_meta`；流式在 `event: routing` 事件的 data 内）：

```json
{
  "context_meta": {
    "strategy": "summarize_old",
    "budget_tokens": 2048,
    "history_messages": 12,
    "included_messages": 5,
    "dropped_messages": 7,
    "history_tokens": 1730,
    "summarized": true,
    "source": "openllm"
  }
}
```

### 2.3 改动清单

**OpenLLM**

1. `backend/app/edgerouter/orchestration/history.py`
   - `build_history_ctx(messages, *, max_tokens=None, count_tokens=None, strategy="recent")` 新增 `strategy` 参数。
   - 新增私有函数：
     - `_trim_recent(entries, budget, count_tokens)`：现有"丢最旧"逻辑，抽出复用。
     - `_trim_head_tail(entries, budget, count_tokens)`：保留首 1/4 与末 3/4，超预算先丢中段、再丢头部。
     - `_trim_system_priority(entries, budget, count_tokens, preserve_recent_n=4)`：先保留最近 N 条与全部 `system`，其余按新旧从旧到新丢弃。
     - `_summarize_old(entries, budget, count_tokens)`：保留最近消息至预算 80%，其余压缩为一行 `system: [早期对话摘要] 共 N 条已省略`（确定性压缩，不调用 LLM）。
   - 缺失/未知 `strategy` 一律回落 `recent`（网关层已前置校验，此处为防御）。
2. `backend/app/api/openllm_gateway.py`
   - `OpenLLMChatRequest`（约 1838 行）新增 `context_policy: dict[str, Any] | None`。
   - 新增 `CONTEXT_POLICY_STRATEGIES` 常量与 `_resolve_context_policy(chat_req) -> dict[str, Any]`：校验并返回 `{strategy, max_tokens, preserve_recent_n}`，非法抛 `GatewayError(4003, ...)`。
   - `_build_history_for_request(chat_req)`（约 2117 行）返回 `tuple[str | None, dict[str, Any]]`：文本 + `context_meta`（`budget_tokens/history_messages/included_messages/dropped_messages/history_tokens/summarized/source="openllm"`）。
   - `_normalize_request(...)`（约 2195 行）返回值扩为 6 元组（新增 `context_meta`）；同步更新 3783、4092 两处解包。
   - 同步路径：`data["context_meta"] = context_meta`（约 4009 行 `data` 组装处）；`raw_results` 模式同样携带。
   - 流式路径：`openllm_chat_stream` 组装 routing 事件处（约 4110-4180）在事件 data 内加入 `context_meta`。
3. 新增测试 `backend/tests/unit/test_context_policy.py`：
   - 四种策略分别断言裁剪结果与 meta；
   - 非法 strategy / max_tokens / preserve_recent_n → 4003；
   - 不传 `context_policy` 时输出与旧逻辑逐字一致（回归）。

**OpenBase**

4. `openbase/modules/llm_proxy/__init__.py`
   - 新增 `_validate_context_policy(payload: dict) -> dict | None`：非 dict → `BaseError(ErrorCode.PARAM_INVALID, "context_policy 必须是对象")`；strategy/max_tokens/preserve_recent_n 白名单与范围校验（与 OpenLLM 同口径）。
   - `llm_chat` 与 `llm_chat_stream` 转发前调用校验。
   - 新增 `_with_context_meta(response: JSONResponse, policy: dict | None) -> JSONResponse`：2xx 且 `data` 为 dict 且缺 `context_meta` 时补 `{"strategy": <policy.strategy 或 "recent">, "applied": false, "source": "openbase-default"}`；其余原样返回。仅作用于两个 chat 端点。
5. 新增测试 `tests/test_llm_proxy_context_policy.py`：白名单校验、非法参数 400 PARAM_INVALID、上游 `context_meta` 原样透传、缺失时门户补默认值。

### 2.4 验收

- 传 `context_policy.strategy=head_tail` 时 `context_meta.strategy == "head_tail"`，且历史段含首尾内容；
- 不传 `context_policy` 时响应 `context_meta.strategy == "recent"` 且历史段与批次 2 结果一致；
- 非法策略门户直接 400 `PARAM_INVALID`，不发起上游请求。

### 2.5 回滚

删除请求体字段即回退；`context_meta` 为新增字段，旧消费方无感知。无数据库变更。

---

## 3. R9 画像 person_id 口径（external_id 映射）

> **[已实现 v1.1.0｜批次 3]** DPS `profile.external_id` 列 + 部分唯一索引
> `uq_profile_org_external`（PG `IF NOT EXISTS` / SQLite PRAGMA 探测），写路径
> 落列并应用层前置校验 + 唯一索引兜底（409 `BIZ_EXTERNAL_ID_CONFLICT`），新增
> `GET /api/v2/portrait/by-external/{external_id}`（静态段先于动态段，租户隔离，
> 404 不泄露存在性）。门户新增 `GET /portraits/by-external/{external_id}` 代理；
> OpenLLM 画像回写携带 `external_id`（subject_id → external_user_id → 不携带）。
> **偏差**：允许"仅 external_id"的更新请求（便于单独登记映射）。

### 3.1 现状与目标

现状：OpenLLM 以 `external_user_id` 读写 DPS 画像，门户以 DPS `person_id` 查询，二者是否同空间未定；聊天回写的画像可能在门户查不到。
目标：DPS `profile` 增加 `external_id` 映射列与 by-external 查询端点；门户新增同口径代理；OpenLLM 回写时携带 `external_id`；`person_id` 语义保持不变（零迁移双写）。

### 3.2 接口契约

**DPS**

- 写入：`PUT/PATCH /api/v2/portrait/{person_id}` 请求体新增顶层可选字段 `external_id`（字符串，≤200）。

```json
{
  "external_id": "u-10086",
  "person": {"name": "张三"},
  "business": {"attributes": {"tags": ["A"]}}
}
```

  - `external_id` 缺省 → 不写该列（现网行为不变）；
  - 同 `org_id` 下 `external_id` 已被其他 `person_id` 占用 → 409 `BIZ_EXTERNAL_ID_CONFLICT`（`detail` 含 `external_id` 与已占用 `person_id`）。
- 查询：`GET /api/v2/portrait/by-external/{external_id}`
  - 200：与 `GET /portrait/{person_id}` 同构（含解析后的 `attributes`）；
  - 404：`画像不存在`（未登记映射或已软删）；
  - 租户过滤：有 `x_tenant_id` 时按 `tenant_id` 限定。
  - **注册顺序**：必须位于 `/portrait/{person_id}`（约 1548 行）之前（静态段优先，复用既有路由顺序约定）。

**OpenBase**

- `GET /api/v1/dps-proxy/portraits/by-external/{external_id}` → 上游 `/api/v2/portrait/by-external/{external_id}`，四头透传，响应适配规则不变。
- 既有 `GET /portraits/{person_id}` 语义不变（向后兼容）。

**OpenLLM**

- 画像写回（`backend/app/edgerouter/adapters/profile.py` 的 `_update_profile_real` / `dps_client.profile_update`）请求体新增 `external_id`：
  - 取值优先级：`identity.subject_id` → `identity.external_user_id`；两者皆空则不携带（不写列）；
  - `person_id` 仍取现有 `external_user_id`（读写同键，不变）。

### 3.3 改动清单

**DPS**

1. `src/ddl/schema_root.py`：`PROFILE_PG` 增加 `external_id VARCHAR(200)`；`PROFILE_SQLITE` 增加 `external_id TEXT`。
2. `src/database.py`：新增幂等迁移 `_ensure_profile_external_id()`（在既有 profile 索引复核函数附近调用）：
   - PG：`ALTER TABLE platform.profile ADD COLUMN IF NOT EXISTS external_id VARCHAR(200)`；`CREATE UNIQUE INDEX IF NOT EXISTS uq_profile_org_external ON platform.profile(org_id, external_id) WHERE external_id IS NOT NULL`；
   - SQLite：`PRAGMA table_info(profile)` 无列则 `ALTER TABLE profile ADD COLUMN external_id TEXT`；`CREATE UNIQUE INDEX IF NOT EXISTS uq_profile_org_external ON profile(org_id, external_id) WHERE external_id IS NOT NULL`。
3. `src/identity/error_codes.py`：新增 `BIZ_EXTERNAL_ID_CONFLICT = "BIZ_EXTERNAL_ID_CONFLICT"` 及消息映射（"external_id 已被其它 person 占用"）。
4. `src/rest_api/routes/routes_profiles.py`：
   - `_TOP_LEVEL_WHITELIST` 增加 `"external_id"`；新增 `_validate_external_id(value) -> Optional[str]`（类型/长度校验，非法 400）。
   - `_parse_portrait_update_body` 返回 `(person_updates, attributes, external_id)`；同步更新 PUT / PATCH 调用点。
   - `_persist_portrait_update(..., external_id: Optional[str] = None)`：UPDATE 时一并写列；行不存在时走既有插入路径并落列；唯一冲突 → `BaseError(DpsErrorCode.BIZ_EXTERNAL_ID_CONFLICT)`。
   - 新增 `GET /portrait/by-external/{external_id}`（置于动态路由之前）：`SELECT * FROM profile WHERE external_id = ? AND status != 'deleted'`（+ tenant），解码 `attributes`，返回同构响应。
5. 新增测试 `src/tests/test_batch3_r9_external_id.py`：写入落列、唯一冲突 409、by-external 命中/404/租户隔离、不传 `external_id` 行为不变。

**OpenBase**

6. `openbase/modules/dps_proxy/__init__.py`：新增 `GET /portraits/by-external/{external_id}`（置于 `/portraits/{person_id}` 之前，避免被动态段捕获），复用 `_forward` 与 `_build_identity_headers`。
7. 新增测试 `tests/test_dps_proxy_external_id.py`：路由转发路径、身份头透传、上游 404 原样映射。

**OpenLLM**

8. `backend/app/edgerouter/adapters/profile.py`：写回 payload 增加 `external_id`（取值规则见 §3.2）；`backend/app/edgerouter/adapters/dps_client.py`（若签名在客户端侧）透传该字段。
9. 扩展 `backend/tests/unit/` 既有 profile 写回测试：断言 payload 含 `external_id`，source 为空时不含。

### 3.4 验收

- 同一用户聊天回写后，门户 `GET /portraits/by-external/<external_id>` 可查到标签；
- 两个不同 `person_id` 抢同一 `external_id` → 第二次 409 `BIZ_EXTERNAL_ID_CONFLICT`；
- 不传 `external_id` 的既有调用行为、响应结构完全不变；
- 租户 B 用租户 A 的 `external_id` 查询 → 404。

### 3.5 回滚

列与索引保留（可空，不影响旧逻辑）；门户新端点无调用方即无影响；OpenLLM 停止携带 `external_id` 即回退。

---

## 4. R2 双知识库 → OpenRAG 唯一事实源

> **[已实现 v1.1.0｜批次 3]** OpenLLM 新增
> `OPENLLM_KB_PROXY_ENABLED=false` / `OPENLLM_KB_READONLY=false` /
> `OPENLLM_KB_TIMEOUT=5.0`、`KbIdMap` 映射表、`KbOpenRAGBridge` 服务层、
> OpenRAG 客户端集合/文档方法、知识库与文档路由代理分支（`Deprecation`/`Sunset`
> 头、只读 410 `BIZ_KB_MIGRATED`、上游不可用 503）与
> `backend/scripts/migrate_kb_to_openrag.py`（幂等 + dry-run + 对账）。
> **偏差**：仓内文档路由无 `/text` 端点 → 上传按 UTF-8 文本提取后调用上游文本
> 入库（非文本 422）；代理响应直接返回旧字段 `dict`（`id: str`），未新增
> Pydantic 模型；OpenRAG 本批次零改动。

### 4.1 决策

OpenRAG 为知识库唯一事实源（登记 ADR）；OpenLLM 自带 `knowledge_bases`/`documents` 不再作为独立存储。本批次落地"代理化 + 迁移脚本 + 只读开关"三件，OpenRAG **零代码改动**（仅消费既有 `/api/v1/collections*` 与 `/documents*`）。

### 4.2 开关

| 配置 | 默认 | 语义 |
|---|---|---|
| `OPENLLM_KB_PROXY_ENABLED` | `false` | `true` 时知识库路由改走 OpenRAG；`false` 保持本地实现（现网） |
| `OPENLLM_KB_READONLY` | `false` | `true` 且代理关闭时，本地写端点返回 410 `BIZ_KB_MIGRATED` |
| `OPENLLM_KB_TIMEOUT` | `5.0` | 知识库代理调用 OpenRAG 超时（秒） |

### 4.3 映射表

新表 `kb_id_map`（OpenLLM 本地库，仅作 legacy→OpenRAG 映射，不存业务数据）：

| 列 | 类型 | 约束 |
|---|---|---|
| `id` | VARCHAR(36) | PK |
| `legacy_kb_id` | VARCHAR(36) | UNIQUE NOT NULL |
| `collection_id` | VARCHAR(64) | NOT NULL |
| `tenant_code` | VARCHAR(64) | NOT NULL |
| `created_at` | DATETIME | NOT NULL |

唯一键 `legacy_kb_id`；查询 `(tenant_code, collection_id)` 建普通索引。

### 4.4 代理语义（`OPENLLM_KB_PROXY_ENABLED=true`）

| OpenLLM 端点 | OpenRAG 上游 | 说明 |
|---|---|---|
| `GET /knowledge-bases` | `GET /api/v1/collections?page=&page_size=` | 输出保持旧 schema（`id` 用 OpenRAG collection id；`tenant_id` 取当前组织） |
| `POST /knowledge-bases` | `POST /api/v1/collections` | 请求字段映射：`name/description/embedding_model/chunk_strategy/chunk_size/chunk_overlap` → 同名；`embedding_dimension` 取配置默认 1024；成功后写 `kb_id_map` |
| `GET /knowledge-bases/{kb_id}` | `GET /api/v1/collections/{cid}` | `kb_id` 先经映射表解析；未映射且形如 collection id 时直接透传 |
| `PUT /knowledge-bases/{kb_id}` | `PUT /api/v1/collections/{cid}` | 字段白名单同上 |
| `DELETE /knowledge-bases/{kb_id}` | `DELETE /api/v1/collections/{cid}` | 成功后清理映射行 |
| `GET /knowledge-bases/{kb_id}/stats` | `GET /api/v1/collections/{cid}/stats` | 映射为旧 `KnowledgeBaseStats` |
| `GET /documents?kb_id=` | `GET /api/v1/collections/{cid}/documents?page=&page_size=` | 映射为旧 `DocumentResponse` |
| `POST /documents/text`（若该端点存在） | `POST /api/v1/collections/{cid}/documents/text` | 文本入库 |
| `DELETE /documents/{doc_id}` | `DELETE /api/v1/collections/{cid}/documents/{doc_id}` | 删除 |

- **首次访问按 `(tenant, name)` 查库/建库**：`resolve_collection(tenant_code, name, legacy_kb_id)` 先查 `kb_id_map`，未命中则调用 `GET /api/v1/collections?page_size=100` 按 `name` 精确匹配；仍无则 `POST /api/v1/collections` 建库；最后写映射。
- 旧接口响应头：代理命中时统一加 `Deprecation: true` 与 `Sunset: Thu, 31 Dec 2026 23:59:59 GMT`。
- 上游不可用 → 503 `SYS_UPSTREAM_ERROR`（不静默回退本地，避免双源分裂）。
- 响应 schema 兼容：`KnowledgeBaseResponse` 的 `id/tenant_id` 为 UUID；OpenRAG collection id 若为非 UUID 字符串，则代理模式下改用 `str` 响应模型（新增 `KnowledgeBaseProxyResponse`，字段同名、`id: str`），并在此文件登记该偏差。

### 4.5 只读下线（`OPENLLM_KB_READONLY=true` 且代理关闭）

本地 `POST/PUT/DELETE /knowledge-bases*` 与文档写入端点返回：

```json
{"detail": {"code": "BIZ_KB_MIGRATED", "message": "知识库已迁移至 OpenRAG，本地写入已下线"}}
```

HTTP 410。

### 4.6 改动清单

**OpenLLM**

1. `backend/app/settings.py`：新增 §4.2 三个配置。
2. 新增 `backend/app/models/kb_id_map.py`：`KbIdMap` ORM 模型（表结构见 §4.3）。
3. `backend/app/db/session.py`：在 `create_all` 前导入 `KbIdMap`（确保建表；幂等）。
4. 新增 `backend/app/services/kb_openrag_bridge.py`：
   - `KbOpenRAGBridge` 类：`resolve_collection`、`list_collections`、`create_collection`、`get_collection`、`update_collection`、`delete_collection`、`collection_stats`、`list_documents`、`ingest_text`、`delete_document`；
   - 会话级 `AsyncClient` 复用（进程级单例，超时取 `OPENLLM_KB_TIMEOUT`）；
   - `ComponentUnavailableError` → `HTTPException(503, ...)`。
5. `backend/app/edgerouter/adapters/openrag_client.py`：补齐 `create_collection/get_collection/update_collection/delete_collection/get_collection_stats/list_documents/delete_document` 方法（复用 `_request` + `_raise_business_error` + `_extract_items`）。
6. `backend/app/api/knowledge_bases.py`：每个端点开头 `if settings.OPENLLM_KB_PROXY_ENABLED: return await _proxy_*`；写端点先判 `OPENLLM_KB_READONLY` → 410。
7. `backend/app/api/documents.py`（OpenLLM 文档路由所在文件）：同样的代理/只读分支。
8. 新增 `backend/scripts/migrate_kb_to_openrag.py`：
   - 遍历 `KnowledgeBase` → `resolve_collection` → 遍历其 `Document`；
   - 按 `content_hash` 去重后调用 `/documents/text` 重放入库，轮询状态（上限 120s）；
   - 写 `kb_id_map`；输出对账报告 JSON（`collections/documents/chunks`）；
   - 幂等：重复执行命中映射与 `content_hash` 去重；`--dry-run` 只统计不写；
   - 退出码：`local_doc_count != openrag_doc_count` → 2（不进入只读切换）。
9. 新增测试：
   - `backend/tests/unit/test_kb_proxy_mode.py`：开关关闭走本地、开启走 fake bridge、503 映射、410 只读、Deprecation 头；
   - `backend/tests/unit/test_kb_id_map.py`：映射写入/查询幂等。

### 4.7 验收

- 代理开启后，门户 `GET /rag-proxy/collections` 与 OpenLLM `GET /knowledge-bases` 在同 tenant 下集合名与 id 一致；
- 同一文档重复迁移不产生重复 document（`content_hash` 去重）；
- `OPENLLM_KB_PROXY_ENABLED=false` 时全部既有测试通过（现网行为零变化）；
- 只读开关下本地写端点返回 410 `BIZ_KB_MIGRATED`。

### 4.8 回滚

`OPENLLM_KB_PROXY_ENABLED=false` 即回退本地实现；`kb_id_map` 保留无副作用；迁移脚本不删除本地数据。

---

## 5. 实施顺序与门禁

1. R7（纯增量）→ 验证 → 提交推送；
2. R9（DDL + 端点，幂等迁移）→ 验证 → 提交推送；
3. R2（开关 + 代理 + 脚本）→ 验证 → 提交推送；
4. 方案文档升 v1.6.0 并追加修订历史；各仓分别提交，只 add 明确文件。

## 6. 验证命令

```bash
# OpenBase
D:\venvs\openbase\Scripts\ruff.exe check openbase tests
D:\venvs\openbase\Scripts\python.exe -m pytest tests

# DPS（规避缺失 pytest-cov）
D:\venvs\openbase\Scripts\python.exe -m pytest src/tests/test_batch3_r9_external_id.py -o addopts=""

# OpenLLM
D:\venvs\openllm\Scripts\python.exe -m pytest backend/tests/unit/test_context_policy.py backend/tests/unit/test_kb_proxy_mode.py
D:\venvs\openllm\Scripts\python.exe -m py_compile backend/scripts/migrate_kb_to_openrag.py

# OpenRAG（本期零改动，仅语义确认）
python -m py_compile src/openrag/api/routes/collections.py src/openrag/api/routes/documents.py
```

## 7. 风险与假设

| 风险 | 影响 | 处置 |
|---|---|---|
| OpenLLM 本地 KB/document 路由与预期文件不一致 | 代理分支遗漏端点 | 开工时以 `app/api` 路由注册表核对；遗漏端点登记为批次 4 补充 |
| OpenRAG collection id 非 UUID | 旧响应模型校验失败 | 代理模式使用 `KnowledgeBaseProxyResponse(id: str)`（§4.4） |
| `external_id` 被多个 person 复用 | 写入 409 | 应用层先行校验 + 唯一索引兜底 |
| `context_policy=max_tokens` 过大 | 超窗 | 上限 200000；超过 → 4003 |
| DPS 存量库未跑迁移 | by-external 查询列缺失 | `database.py` 启动幂等迁移；缺失时端点返回 503 并记录 ERROR |

## 8. 假设

- 门户登录用户可解析出 `external_id`（由统一身份上下文提供）；无法解析时门户调用方仍可用 `person_id` 端点。
- OpenRAG 现有 `/api/v1/collections` 与 `/documents` 契约稳定，无需本批次改动。

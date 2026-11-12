# OpenBase 四基础子系统全链路贯通修复方案

| 项 | 内容 |
|---|---|
| **版本** | v1.6.0 |
| **状态** | [Review] |
| **适用范围** | OpenBase / OpenLLM / OpenMemory / OpenRAG / DPS |
| **依据** | 《OpenBase-四基础子系统全链路贯通审计报告-v1.0.0》R1–R9 |
| **作者** | 架构组 |
| **日期** | 2026-11-12 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-12 | 首版：R1–R9 逐项方案、改动清单、迁移与灰度、验收标准、实施批次 | 架构组 |
| v1.1.0 | 2026-11-12 | 新增 R5 专项：租户漂移成因（含 OpenBase 兜底码与三系统缺省差异）、三类可复现场景、原三态方案的 4 项盲区与修正后的 L1–L4 分层方案、风险矩阵与验收判据 | 架构组 |
| v1.2.0 | 2026-11-12 | 裁定 R5 采用「OpenBase 入口强制」为主方案：复用 Q5 登录门禁，补齐 JWT/agent/service-key/MCP 四条通道的请求级守卫；出站三态降为观测与兜底清理；补充 5 项缺口、落地改动点与切换顺序 | 架构组 |
| v1.3.0 | 2026-11-12 | 将入口守卫实现方案完整整合进本方案（§7.7.2 定稿、§7.7.5 任务清单、§7.7.6 验收矩阵、§7.7.7 实施状态）：确认三态默认 `auto`（生产自动 `enforce`）、MCP 静态 Key 改受信来源判定（G4）、生产出清 per-target 兜底（G5，`default_tenant_code: null` 清空）、agent 创建强制租户（G2）；同步更新批次、端到端验收矩阵与配置附录。原独立 Spec 已并入，不再单独维护 | 架构组 |
| v1.4.0 | 2026-11-12 | 批次 1 实施记录：R5 入口守卫 T1–T6 完成（`tenant_guard` 三态、settings 配置与生产门禁、JWT/`sk-agent`/服务 Key/MCP 四通道、agent 创建租户解析、单测）；R4 后端记忆 PATCH 代理与前端编辑入口完成；R3 短期 `dps_calc_timeout`（默认 30s）与 504 可读提示完成。`ruff check openbase tests` 全通过 | 架构组 |
| v1.5.0 | 2026-11-12 | 批次 2 实施记录：R8 OpenRAG 重试限流 + 门户代理 + 前端重试；R6 OpenMemory `GET /memories` 原生分页 + 门户直连（不支持回退 recall）；R1 DPS `PATCH /portrait/{id}` 深合并 + If-Match（复用既有 `version`）+ OpenLLM 合并回写与 409 重放；R3 长期 `portrait_calc_task` 任务表 + `calculate?async=true` 202/task_id 幂等 + 任务查询 + 门户默认异步与前端轮询 helper。规格见 `doc/design/批次2-全链路贯通修复/spec.md` | 架构组 |
| v1.6.0 | 2026-11-12 | 批次 3 实施记录：R7 上下文裁剪四策略（`context_policy`/`context_meta`，默认行为不变）；R9 DPS `profile.external_id` 列 + 部分唯一索引 + `by-external` 端点、门户代理、OpenLLM 回写携带；R2 OpenLLM 知识库可开关代理 OpenRAG（`OPENLLM_KB_PROXY_ENABLED=false` 默认）、`kb_id_map`、迁移脚本与只读 410。规格/任务/偏差见 `doc/design/批次3-全链路贯通修复/` | 架构组 |

---

## 0. 方案总览

| 编号 | 问题 | 方案要点 | 改动仓 | 批次 |
|---|---|---|---|---|
| R4 | 记忆编辑入口缺失 | 门户新增 PATCH 代理 + 前端编辑表单 | OpenBase | 1 |
| R3 | 画像计算同步超时 | 门户放宽超时（短期）+ DPS 异步任务（长期） | OpenBase / DPS | 1 / 2 |
| R5 | 租户缺省行为不一致 | **入口强制**（OpenBase 三态入口守卫，生产 `enforce`）+ 生产出清出站兜底 + 三系统 fail-closed 纵深 | OpenBase（主）+ 三系统 | 独立轨道：1（shadow）→ 3（enforce） |
| R1 | 画像覆盖写丢字段 | DPS 新增 PATCH 深合并 + 版本乐观锁；OpenLLM 改用 PATCH | DPS / OpenLLM | 2 |
| R6 | 记忆列表口径不准 | OpenMemory 原生分页 + 门户直连 | OpenMemory / OpenBase | 2 |
| R8 | 索引失败无重试 | OpenRAG 新增 reindex + 门户重试入口 | OpenRAG / OpenBase | 2 |
| R2 | 双知识库事实源 | 裁定 OpenRAG 唯一源；OpenLLM KB 转代理 → 迁移 → 只读下线 | OpenLLM / OpenRAG | 3 |
| R9 | 画像 person_id 口径 | DPS external_id 映射 + by-external 查询 | DPS / OpenBase | 3 |
| R7 | 裁剪策略不可配 | 门户透传 context_policy + 响应回显 context_meta | OpenBase / OpenLLM | 3 |

统一约束（所有条目适用）：

1. 错误响应保持 `{code,message,detail,request_id}`；新增错误码遵循既有前缀（PARAM/BIZ/PERM/SYS）。
2. 所有写操作必须落审计（主体、tenant、动作、前后差异摘要）。
3. 新增可配置项一律"默认保持现网行为"，通过开关灰度。
4. 数据库变更幂等（`WHERE NOT EXISTS` / `create_all`），多租户查询必须带 tenant 过滤。
5. 入口认证后的主体必须携带租户：三态 `off|shadow|enforce`，默认 `auto`（生产 `enforce`）；四认证通道（JWT/`sk-agent`/服务 Key/MCP）与 agent 创建统一受守卫约束（§7.7）。

---

## R1 画像回写覆盖 → 深合并 + 乐观锁

> **[已实现 v1.5.0｜批次 2]** DPS 新增 `PATCH /api/v2/portrait/{person_id}`：
> `business.attributes` 深合并（dict 递归 / list 去重追加 / 标量覆盖 / `null` 删除 /
> `__delete__` 点分路径），可选 `If-Match` 校验既有 `profile.version`（不符 409
> `BIZ_VERSION_CONFLICT`），结构化日志记 before/after 哈希与 diff_paths；响应附加
> `attributes_version`。门户新增 `PATCH /api/v1/dps-proxy/portraits/{person_id}` 透传
> `If-Match`；OpenLLM 回写默认 PATCH（`PROFILE_WRITEBACK_MERGE=true`），409 重放一次，
> 仍冲突则标记 `writeback=conflict` 跳过、不阻塞对话。**偏差**：复用既有 `version`
> 列，未新增 `attributes_version` 列（避免 DDL 迁移与双版本语义）。

### 根因

DPS `PUT /api/v2/portrait/{person_id}` 对 `business.attributes` 采用整体覆盖（`DPS/src/rest_api/routes/routes_profiles.py:1421-1422` 设计约束明示）；OpenLLM 回写直接映射增量后 PUT（`OpenLLM/backend/app/edgerouter/adapters/profile.py:403-424`），无读-改-写。

### 方案（推荐 A，B 为兜底）

**A. DPS 新增 PATCH 合并语义（推荐）**

1. DPS `routes_profiles.py` 新增 `PATCH /portrait/{person_id}`：
   - 请求 `{"business": {"attributes": {...}}, "person": {...}}`，`person` 仍走白名单（name/status/scores）。
   - `business.attributes` **深合并**规则：dict 递归合并；list 按元素去重追加；标量覆盖；`null` 表示删除该键（需显式 `__delete__` 列表可选）。
   - 响应返回合并后的 `data.attributes` 与 `attributes_version`。
2. 并发控制：新增列 `profile.attributes_version BIGINT NOT NULL DEFAULT 0`；请求头 `If-Match: <version>`，不匹配返回 409 `BIZ_PROFILE_VERSION_CONFLICT`；无 If-Match 时按最后一次写胜出（兼容）。
3. 审计：写入 `audit_operation_log`，payload 记录 `{before_hash, after_hash, diff_paths}`（不记全量内容）。
4. OpenLLM 改造：
   - `dps_client.profile_update(..., merge: bool = False)`，`merge=True` 时按 PATCH 发送并带 `If-Match`（先 `profile_read` 取 version）。
   - `adapters/profile.py:_update_profile_real` 改走 merge 分支；保留 `PROFILE_WRITEBACK_MERGE` 开关（默认 true，异常回退 PUT 并告警）。
   - 409 时重读 + 重放一次；仍冲突则记 `writeback=conflict` 交后台任务，不阻塞对话。

**B. 兜底方案（不改 DPS 语义）**：OpenLLM 先 GET 合并再 PUT + `If-Unmodified-Since`。缺点：并发窗口仍在，仅作 A 未上线前的临时措施。

### 验收

- 同 person 先写 `{tags:["A"]}` 再写 `{tags:["B"]}` → GET 返回 `{tags:["A","B"]}`。
- 两个模板命名空间互不覆盖；并发写触发 409 且重试后成功，审计含 conflict 记录。
- 开关关闭时行为与现网一致。

### 回滚

`PROFILE_WRITEBACK_MERGE=false` 即回退 PUT；DPS PATCH 路由可保留（无调用方即无影响）。

---

## R6 `/memories` 列表原生分页

> **[已实现 v1.5.0｜批次 2]** OpenMemory 新增 `GET /api/v1/memories`（`offset/limit/
> memory_type/tag`，scope fail-closed，返回 `data.items/total`）；`RelationalStore`
> 新增 `list_memories_paginated`（同过滤条件计数 + 稳定排序），`PersistentMemory` /
> `MemoryService` 薄封装，上游无能力时抛 `NotImplementedError` → 501。门户
> `memory_list` 优先直连原生分页，404/405/501 自动回退原 recall 适配路径，响应信封不变。

## R8 索引失败重试

> **[已实现 v1.5.0｜批次 2]** OpenRAG 既有 reindex 路由增加 60 秒冷却限流
> （同租户同文档重复提交返回 429 `BIZ_REINDEX_THROTTLED`）；门户 `rag_proxy` 新增
> `POST /collections/{cid}/documents/{did}/reindex` 代理并记录 `rag.document.reindex`；
> 前端知识库管理页对 `FAILED/ERROR` 文档展示「重试」，429 提示冷却。

## R2 双知识库 → OpenRAG 唯一事实源

> **[已实现 v1.6.0｜批次 3]** OpenLLM 新增 `OPENLLM_KB_PROXY_ENABLED=false` /
> `OPENLLM_KB_READONLY=false` / `OPENLLM_KB_TIMEOUT=5.0`、`kb_id_map` 映射表、
> `KbOpenRAGBridge`、OpenRAG 客户端集合/文档方法、知识库与文档路由代理分支
> （`Deprecation`/`Sunset` 头、只读 410 `BIZ_KB_MIGRATED`、上游不可用 503）及
> `backend/scripts/migrate_kb_to_openrag.py`（幂等 + dry-run + 对账，失败退出码 2）。
> **偏差**：仓内文档路由无 `/text` 端点，上传按 UTF-8 文本提取后调用 OpenRAG 文本
> 入库（非文本 422）；代理响应直接返回旧字段 `dict`（`id: str`）；OpenRAG 零改动。

### 决策

裁定 **OpenRAG 为知识库唯一事实源**（需架构组在 ADR 中登记）；OpenLLM 自带 `knowledge_bases`/`documents` 不再作为独立存储。

### 方案（三步走，可独立回滚）

1. **代理化（不改数据）**：`OpenLLM/backend/app/api/knowledge_bases.py` 的路由内部改为调用 OpenRAG 客户端；新增映射表 `kb_id_map(legacy_kb_id, collection_id, tenant_code)`，首次访问按 `(tenant, name)` 在 OpenRAG 查库/建库。
   - 响应结构保持旧 schema（前端零改动）。
   - 旧接口加响应头 `Deprecation: true`、`Sunset: <日期>`。
2. **数据迁移**：新增 `OpenLLM/scripts/migrate_kb_to_openrag.py`（幂等）
   - 遍历本地 KB → 按 `(tenant_code, name)` 在 OpenRAG 建/查 collection；
   - 文档按 `content_hash` 去重后调用 `/api/v1/collections/{id}/documents` 重放入库，轮询状态；
   - 写 `kb_id_map`，输出对账报告（collection 数、文档数、chunk 数）。
   - 迁移完成后校验：`local_doc_count == openrag_doc_count`，不一致不进入第 3 步。
3. **只读下线**：本地写入路径置 `410 BIZ_KB_MIGRATED`（或转发），本地向量库停止写入；保留只读 30 天，之后删除模型与表。

### 验收

- 门户与 OpenLLM 页在同 tenant 下 collection 列表完全一致；
- 同一文档只产生一份 chunk（Qdrant 计数一致），检索 Top-K 结果一致；
- 迁移脚本重复执行不产生重复数据（幂等）。

### 风险

历史文档解析差异可能导致 chunk 数不一致 → 以"检索结果集一致"为准，chunk 数仅告警；迁移期间双写关闭，避免分裂。

---

## R3 画像计算 → 超时兜底 + 异步任务

> **[已实现 v1.4.0｜短期]** 门户代理新增 `settings.dps_calc_timeout`（默认 30s），
> `_timeout("dps", "/portraits/calculate")` 单列取值；前端 `calculatePortrait` 对 504
> 返回可读提示「计算可能已提交，请在详情页刷新确认」。
>
> **[已实现 v1.5.0｜批次 2・长期]** DPS 新增任务表 `portrait_calc_task`（幂等键唯一索引）
> 与 `POST /portrait/calculate?async=true` → 202 `{task_id,status}`；幂等键
> `sha256(tenant:person:template:data_version)`，非 failed 任务复用；后台任务
> `pending→running→succeeded|failed` 落状态与 `result_json`；新增
> `GET /portrait/tasks/{task_id}` 与 `GET /portrait/{person_id}/tasks?status=`。
> 门户 `dps_calc_async_default=true` 时默认注入 `async:true`，新增
> `GET /portraits/tasks/{task_id}` 代理；前端 `dps.ts` 提供 `getPortraitTask` /
> `waitPortraitTask`（2s 轮询 / 60s 超时）。**偏差**：`result_json` 用 TEXT（PG/SQLite 通用）。

### 方案

**短期（批次 1，1 处改动）**

`OpenBase/openbase/modules/proxy/__init__.py:95-105` 的 `SLOW_PATH_HINTS` 增加 `"/portraits/calculate"`，并新增 `DPS_CALC_TIMEOUT`（默认 30s）对该路径生效；门户对 504 返回可读提示"计算可能已提交，请在详情页刷新确认"。

**长期（批次 2）**

1. DPS 新增 `POST /portrait/calculate?async=true` → `202 {"task_id": "..."}`；
2. 任务表 `portrait_calc_task(id, person_id, template_code, status, error, created_at, started_at, finished_at, data_version)`；
3. 幂等键 `sha256(person_id + template_code + data_version)`，重复提交返回同一 task（`status` 非 failed 时）；
4. 新增 `GET /portrait/tasks/{task_id}` 与 `GET /portrait/{person_id}/tasks?status=`；
5. 消费端复用现有后台任务机制（同文档索引 worker 模式），超时 120s，失败重试 1 次后置 failed；
6. 门户 `portraits/calculate` 默认 `async=true`，前端 2s 轮询，60s 超时提示。

### 验收

- 10s 以上计算返回 202+task_id，最终 `succeeded` 且详情可查；
- 同参数重复提交只产生 1 条任务、1 次计算；
- 同步模式（`async=false`）行为与现网一致。

### 回滚

门户切回同步调用即可；任务表保留不影响主链。

---

## R4 记忆编辑入口（门户 PATCH 代理）

> **[已实现 v1.4.0]** 后端新增 `PATCH /api/v1/memory-proxy/memories/{id}`（字段白名单
> `content/memory_type/metadata/owner/allow_ownership_change`，未知字段丢弃并 WARN，
> 空白名单 400 `PARAM_INVALID`，审计记 `memory.update`）；前端 `MemoryDetail.vue`
> 增加「编辑」弹窗（内容/类型/元数据 JSON/归属用户 + 二次确认开关）。

### 方案

1. `OpenBase/openbase/modules/proxy/memory_proxy.py` 新增：

```
PATCH /api/v1/memory-proxy/memories/{memory_id}
→ 上游 PATCH /api/v1/memories/{memory_id}
```

- 请求 DTO 白名单：`content`、`memory_type`、`metadata`、`owner`、`allow_ownership_change`；其余字段丢弃并记录 WARN。
- 成功码：上游 200；错误映射：404→`NOT_FOUND`、400→透传 `MEMORY_OWNERSHIP_CHANGE_FORBIDDEN` / `SCOPE_REQUIRED`、403→`PERM_DENIED`、其他 5xx→`SYS_UPSTREAM_ERROR`。
- 透传头沿用 `_build_headers`（X-API-Key、JWT、四维身份、X-Request-Id）。

2. 前端：记忆详情页增加"编辑"抽屉（content/类型/元数据），owner 变更需二次确认复选框；保存后局部刷新列表行。
3. 审计：门户记 `memory.update`（memory_id、变更字段名、主体、tenant），不记内容全文。

### 验收

- 门户改内容后 `GET /memories/{id}` 生效；未勾选授权改 owner 返回 400 且库内不变；
- 跨租户 PATCH 返回 404（不泄露存在性）；
- 审计可按 request_id 串起门户与 OpenMemory 两侧日志。

### 测试

- 单测：路由转发参数、白名单过滤、5 类错误映射；
- 契约测试：以真实 OpenMemory 契约桩校验字段名与状态码。

---

## R5 租户缺省 → 出站三态强制

> **v1.3.0 说明**：本节为出站侧历史方案。R5 主方案已由 §7.7「入口强制」取代；出站三态降为 L3 纵深防御与兜底清理，`OUTBOUND_TENANT_ENFORCE` 保留但不再作为主开关。

### 方案

1. `OpenBase/openbase/modules/protocol_headers/inject.py` 的 `build_outbound_headers` 增加参数 `require_tenant: bool = False`；写路径调用点（chat、remember、documents 上传、portrait 写）传 `True`。
2. 配置 `OUTBOUND_TENANT_ENFORCE` 三态：`off`（现网）/`shadow`（只计数+WARN，不拦截）/`enforce`（缺 `X-Tenant-ID` → 400 `PARAM_TENANT_REQUIRED`，不发起上游请求）。
3. 指标：`openbase_outbound_tenant_missing_total{system="openmemory|openrag|dps|openllm",path_class="write|read"}`；shadow 期观察 7 天后切 enforce。
4. 三系统对齐：
   - OpenRAG：生产禁用"保留码兜底"（配置 `OPENRAG_ALLOW_RESERVED_TENANT=false`）；
   - OpenMemory：`require_tenant=true` 时缺头拒写（现为 default 兜底）；
   - DPS：维持 fail-closed，仅补 `PARAM_TENANT_REQUIRED` 错误码一致性。
5. 读路径：普通用户缺租户头 fail-closed；平台管理员允许显式 `X-Tenant-ID` 指定。

### 验收

- enforce 下无租户头写请求 100% 被门户拒绝并计入指标；
- 三系统对同一请求的归属 tenant 在审计日志中一致；
- shadow 期无新增 5xx。

### 风险与回滚

内部调用方（脚本/定时任务）可能未带租户头 → shadow 期先补齐调用方；异常时切回 `off` 即时恢复。

---

## R5-专项：租户漂移成因与方案可行性评估

### 7.1 漂移不是"漏传"，而是三套缺省语义并存

**OpenBase 出站侧（已有显式兜底，非空值）**

| 证据 | 语义 |
|---|---|
| `openbase/settings.py:105-121` | 内置登记基线：`rag` 保留码 `{default, openrag-local}`、兜底码 `tenant-1`；`memory` 兜底码 `tenant-1`；**`llm`/`dps` 无兜底码**（缺租户时不发头） |
| `protocol_headers/inject.py:179` | `tenant_value = identity.effective_tenant_code or default_tenant` |
| 同文件 `:184-197` | `tenant_value` 非空才写 `X-Tenant-ID`/`X-Org-ID`；空则**整头省略** |
| 同文件 `:211-216` | 主体键 `subject_id = {tenant}_{user}`，用**未互译**的 tenant → tenant 变化即主体键变化 |
| `protocol_headers/code_space.py:50-54,92-106` | 保留码 → 兜底码的"值改写"映射（`reserved_map`） |
| `modules/auth/__init__.py:305-315` | 登录时未绑定租户：有兜底码 → 用兜底；`require_tenant_on_login && production` 才拒签；否则返回 `None`（`unbound`） |
| `openbase/settings.py:476` | `require_tenant_on_login` **默认 false** |

四个代理的入参差异（`grep default_tenant=`）：`memory_proxy:117`、`rag_proxy:166` 传兜底码；**`llm_proxy` 与 `dps_proxy` 的 LLM 通道不传**（dps 传 `dps_default_tenant_id`，默认空串）。

**下游侧（三套不同缺省）**

| 系统 | 缺 `X-Tenant-ID` 时行为 | 证据 |
|---|---|---|
| OpenMemory | 回落 `"default"` | `api/middleware/tenant_context.py:113-117` |
| OpenRAG | `IdentityContext.tenant_code` 回落 `"default"`；另有四态 `resolve_tenant_code`（missing/reserved/registered/unknown），是否拒绝由调用点决定 | `identity/context.py:78,104`；`identity/tenant_registry.py:95-125` |
| DPS | `tenant_context_required` 默认 false；**production + 多租户时启动门禁强制为 true** → fail-closed | `DPS/src/config.py:123-125,434-455` |
| OpenLLM | 缺租户 → org 别名回退（M1）；`TENANT_SCOPE_ENFORCE` 开启或 `enforce=True` 时抛 `PARAM_TENANT_IDENTITY_MISSING`；保留码写拒绝 | `identity/namespace.py:250-252,270-291` |

结论：**同一"无租户声明"的主体，经门户后 memory/rag 落 `tenant-1`、llm 省略头（OpenLLM 走 org/default）、dps 省略头（生产直接 400）**。这就是漂移的根因，且是既有设计的兼容语义，不是单点 bug。

### 7.2 四类可复现场景

| 场景 | 触发 | 结果 |
|---|---|---|
| S1 无租户主体 | agent 主体 / 未绑定租户的用户 / 内部服务调用 | memory/rag 落 `tenant-1`；llm 落 org 别名或 default；dps 生产 400。同一用户记忆主体键 `tenant_user` 与画像/知识库归属不一致 |
| S2 保留码存量 | OpenRAG 存量行 `tenant_code in ('default','openrag-local')` | 门户读取时 `reserved_map` 改写为 `tenant-1` → **读取静默为空**；经门户新写又落 `tenant-1` → 同一知识库分裂为双域 |
| S3 异步写回 | 请求本身无租户，OpenLLM 写回队列携带空租户 | 回调重试无法补齐；各系统按自身兜底落库，审计主体与数据归属不一致 |
| S4 旁路调用 | `scripts/*`、cron、MCP、跨仓脚本直连四系统 | 完全绕过门户注入；enforce 后不会 400，仍按各自默认/或直接 400，行为不可控 |

### 7.3 原三态方案（A）可行性评估

**可行，但单独实施无效。** 评分：

| 维度 | 评估 | 说明 |
|---|---|---|
| 技术可行性 | 高 | 注入点单一（`build_outbound_headers`），四系统均已有租户开关/门禁，无需改协议 |
| 改动面 | 中 | OpenBase 1 处注入 + 4 个调用点传参 + 3 仓配置；无 schema 变更 |
| 可回滚性 | 高 | `off` 即恢复；系统侧开关独立 |
| 有效性 | **低（原样实施）** | 见下 4 个盲区 |
| 数据风险 | 高 | 存量 `default`/`openrag-local`/`tenant-1` 与主体键分身 |

**盲区 1（致命）：兜底码让 enforce 永远不可达。**
`memory`/`rag` 内置 `default_tenant_code="tenant-1"`，`inject.py:179` 会把空租户补成 `tenant-1`，随后 `:184` 判定非空正常发头 → `require_tenant=True` 也不会触发 400。**必须在同批次把 `BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET` 的 rag/memory 置空（或按环境关闭）**，否则三态开关是装饰性的。这是原方案最大的遗漏。

**盲区 2：入口不强制。**
登录面 `require_tenant_on_login` 默认 false，未绑定用户可直接拿到无租户 Token；出站再拦只是把问题推迟到"用户点了功能才报错"。且 `agent`/服务主体没有登录面，只能靠服务租户分配。

**盲区 3：旁路与异步不在守护范围。**
cron、脚本、MCP、OpenLLM 写回队列都不经过门户出站函数。enforce 只保护"门户在线流量"，S3/S4 仍漂移。

**盲区 4：改归属会造成"数据分身"。**
主体键与命名空间均以 tenant 为前缀（`inject.py:211-216`、`OpenLLM/identity/namespace.py:117`）。把某个用户从 `tenant-1` 切到真实租户，等于换了一个主体：旧记忆/画像/知识库归属不可见，且不会自动迁移。

### 7.4 修正后的分层方案（L1–L4）

| 层 | 措施 | 具体改动 | 通过判据 |
|---|---|---|---|
| **L1 入口** | 认证层强制租户 | OpenBase `require_tenant_on_login` 生产置 true；`users.tenant_id` 补齐；`agent`/服务主体分配 **service tenant**；未绑定拒签（`AUTH_FORBIDDEN, reason=tenant_unbound`） | 新增 Token 100% 含 `tenant_code`；无 `unbound` 登录 |
| **L2 出站** | 三态开关 + 去兜底 | `build_outbound_headers(require_tenant=...)`；`OUTBOUND_TENANT_ENFORCE=off|shadow|enforce`；**rag/memory 兜底码置空**；写路径传 `require_tenant=True` | shadow 期 `tenant_missing_total` 归零；enforce 下缺头 400 |
| **L3 系统** | 深水区 fail-closed | OpenMemory `require_tenant`（生产 true，不回落 default）；OpenRAG 保留码仅迁移只读窗口可写；DPS 保持现有生产门禁；OpenLLM `TENANT_SCOPE_ENFORCE=true` | 绕过门户直连写无租户 → 全部 4xx |
| **L4 数据** | 存量盘点与迁移 | 统计 `memory_metadata`/OpenRAG collections,documents/DPS person 中 `default|openrag-local|tenant-1` 行；按 owner 映射真实租户（重算主体键）或显式归入 `legacy` 只读租户；迁移期双读比对 | 迁移前后可见性 100%；抽样 100 条归属一致 |

落地顺序（每步都有独立回滚）：

1. shadow + 数据盘点（只读，7 天）；
2. L1 登录强制 + 服务租户分配（拨测新用户）；
3. L2 清空 rag/memory 兜底码 → 切 enforce；
4. L3 系统侧收紧；
5. L4 存量迁移完成后移除 `legacy` 通道。

### 7.5 风险矩阵

| 风险 | 触发点 | 影响 | 缓解 |
|---|---|---|---|
| 存量读不到 | 清空兜底码后，旧 `tenant-1` 数据不再被默认命中 | 用户看到空列表 | 迁移前双读；迁移窗口内 `legacy` 只读兜底；按 tenant 计数对账 |
| 数据分身 | 主体键随 tenant 变化 | 记忆/画像重复或丢失 | 迁移时重算 `{tenant}_{user}` 并合并；禁止单独改 tenant 列 |
| 内部调用断裂 | cron/脚本/MCP 无租户 | 4xx，任务失败 | 服务主体白名单 + service tenant；按 path_class 分批 |
| SSE 已开流才拒绝 | 校验放在建连之后 | 前端收到半截流 | 校验必须在 `build_outbound_headers`（发请求前）完成；流式入口补集成测试 |
| 测试环境误伤 | 开关按环境配置 | 单机/CI 大量 400 | `env!=production` 保持 off；配置启动校验 |

### 7.6 可行性结论

> **v1.3.0 说明**：R5 主方案已于 v1.2.0 调整为「入口强制」（§7.7）；本节结论保留为出站侧（L3）补充依据。

- **原方案 A（出站三态）技术可行但不足以闭环**：不解决入口、旁路、异步与存量分身，且被内置兜底码屏蔽。
- **修正方案（L1+L2+L3+L4）可闭环**，改动集中在配置与 1 个注入函数，无协议/表结构破坏，回滚粒度清晰。
- **前置依赖**：用户租户绑定率、服务主体清单、存量 `default`/`tenant-1` 数据量三项盘点结论；未完成前只能停在 shadow。
- **建议**：R5 从"批次 1 的 shadow"升级为独立小版本推进，shadow 与 L4 盘点并行，避免 enforce 打开后出现"看得见 400、看不见数据"的二次故障。

### 7.7 裁定与实现设计（v1.2.0 裁定 / v1.3.0 整合）：以 OpenBase 入口强制为主

**结论：可行，且已有部分基座，不需要等出站三态。** 生产环境已具备"登录必须绑定租户"的启动门禁（Q5，2026-10-17 裁定）：

- `openbase/settings.py:1444-1470`：production 下 `require_tenant_on_login` 必须为 true，且 `default_tenant_code` 必须为空，否则拒绝启动；
- JWT 全量携带 `tenant_code` claim（`modules/auth/jwt.py:187,234`）；
- `get_current_user` 已把 `tenant_code` 放入主体上下文（`core/deps/auth.py:370-393`）。

因此无需新建"出站拦截"，只需把入口守卫补齐到**全部四条认证通道**。

#### 7.7.1 剩余 5 个缺口（按风险排序）

| # | 缺口 | 证据 | 后果 |
|---|---|---|---|
| G1 | JWT 通道不校验租户 | `core/deps/auth.py:374` 仅透传 `payload.get("tenant_code")`，为 `None` 也放行 | 旧 token / 关闭门禁的环境可直达业务端点，出站再被兜底码掩盖 |
| G2 | agent 主体租户可空 | `modules/identity/agent_keys.py:292-299` 直接透传 `user.tenant_code` | agent 归属用户未绑定时，以空租户写入四系统 |
| G3 | `/proxy` 服务 Key 双通道无租户守卫 | `core/deps/auth.py:108` 将其列入 `PUBLIC_PREFIXES`；`modules/proxy/__init__.py:377` 提示需 k03 白名单 | 服务 Key 调用绕过 JWT 门禁，租户来源不明 |
| G4 | MCP 凭据采信客户端租户头 | `modules/mcp/credentials.py:257-260` 直接取 `X-Tenant-Id` | 客户端可伪造租户读写记忆/知识库 |
| G5 | 出站内置兜底未被生产门禁覆盖 | `settings.py:105-121` 的 per-target `default_tenant_code="tenant-1"` 不在 Q5 校验范围 | 入口强制后，脚本/cron/内部调用的空租户仍被静默改写为 `tenant-1` |

补充说明：`TenantMiddleware` **不能作为强制点**——它在 `AuthMiddleware` 之前执行（`openbase/__init__.py:52-63` 注册顺序），且直接读取客户端 `X-Tenant-Id`（`modules/tenant/__init__.py:66-79`）；它只能用于 DB schema 路由，安全边界须由认证后的主体上下文定义。

#### 7.7.2 落地改动（v1.3.0 定稿）

1. 新增 `openbase/modules/identity/tenant_guard.py`：
   - 三态：`off`（不校验）/ `shadow`（计数 + WARN，放行）/ `enforce`（403）；
   - `ensure_tenant_bound(principal, request, *, channel)`：有效租户 = `tenant_code or tenant_id`，兼容 `Mapping`（JWT/agent/服务 Key dict）与属性式主体（`MCPCredential`）；
   - `ensure_agent_tenant_bound(tenant_id, *, operator_tenant_id)`：创建 agent 时的归属租户解析（三态生效）；
   - 进程内缺失计数 `missing_tenant_total()` + 结构化 WARN（`extra` 仅含 `channel/path/method/request_id`，不记凭证）。
2. 四个认证通道（覆盖全部入口）：
   - `core/deps/auth.py:get_current_user` 两处 return 前（JWT + `sk-agent`）→ 覆盖业务路由；
   - `core/deps/auth.py:get_proxy_identity` 服务 Key 分支 → 覆盖 `/proxy` 全部方法；
   - `modules/mcp/credentials.py:require_mcp_credential`：三分支统一构造后**单点守卫**（`tools/list`、`tools/call` 同依赖，天然双保险）；
   - stdio 宿主通道不在范围（本地受信、无 `Request`）。
3. 配置：`entry_tenant_enforce: str = "auto"`（`OPENBASE_ENTRY_TENANT_ENFORCE`）：
   - `auto`：production → `enforce`，其余 → `off`（默认值：生产自动强制，非生产零行为变化）；
   - 合法值 `auto|off|shadow|enforce`；非法值启动即失败。
4. 门禁扩展（`validate_production_login_tenant_policy`，追加在既有两条之后）：
   - 生产入口模式必须解析为 `enforce`；
   - 生产禁止任何 per-target 出站兜底码（G5）；通过 `OPENBASE_PROXY_CODE_MAP` 的 `"default_tenant_code": null` 显式清空内置基线（rag/memory 的 `tenant-1`）。
5. 主体创建侧（G2）：`modules/identity/__init__.py:create_agent` 经 `ensure_agent_tenant_bound` 解析归属租户（请求值优先，其次操作者租户）；`enforce` 下仍为空 → `400 PARAM_INVALID`（`detail.reason=tenant_unbound`），`off/shadow` 保持兼容。
6. MCP 租户来源（G4）：静态 Key 不再直接读客户端 `X-Tenant-Id`，改由 `get_current_tenant` 解析（仅 `X-Proxy-Source` 受信时采纳）。
7. 错误语义：
   - 主体无租户 → `403 AUTH_FORBIDDEN, detail.reason=tenant_unbound`（与登录拒签一致）；
   - 受信代理头租户与令牌租户不一致 → `403 PERM_TENANT_MISMATCH`（沿用既有校验，不在本次新增）；
   - 不接受"客户端头覆盖令牌"作为提权路径。
8. 旧 token：复用既有 token 版本机制（`enforce_token_version`）在轮换窗口内强制重签，避免无 `tenant_code` 的历史 token 长期滞留（不新增代码）。

#### 7.7.3 切换顺序与判据

1. `shadow`：按 `channel=jwt|sk-agent|service-key|mcp` 统计 24h，目标 0；
2. 补录：agent 绑定租户、服务 Key 绑定租户、MCP 服务端租户配置；
3. `enforce`（生产）；同时清理出站 per-target 兜底（G5）；
4. 旧 token 重签窗口结束（观察 `tenant_unbound` 归零且无 401 尖峰）；
5. L4 存量盘点迁移仍必须执行——入口强制只保证"新写入归属正确"，历史 `default`/`openrag-local`/`tenant-1` 数据不会自动可见。

#### 7.7.4 边界与残余风险

- 子系统直连（绕过 OpenBase）不在入口守护范围：需 API Key 绑定租户 + 网络策略，作为 L3 纵深防御，不作为主方案。
- 多租户管理员跨租户操作：保留显式 `X-Tenant-ID`，但要求受信来源 + 权限校验，并审计 `tenant_switch` 动作。
- 非生产环境保持 `off`，避免单机/CI 大量 403；但集成测试需覆盖 `enforce` 分支。

#### 7.7.5 实现任务清单（v1.3.0）

| 任务 | 文件 | 变更 | 验收 |
|---|---|---|---|
| T1 守卫模块 | `openbase/modules/identity/tenant_guard.py`（新增） | 三态解析、`ensure_tenant_bound`、`ensure_agent_tenant_bound`、缺失计数、结构化 WARN | 单测覆盖 off/shadow/enforce 与有租户放行 |
| T2 配置与门禁 | `openbase/settings.py` | `entry_tenant_enforce="auto"`、`resolve_entry_tenant_enforce_mode`、模型校验、`parse_proxy_code_map` 支持 `null`、生产门禁第 3/4 条 | 模式解析与门禁单测 |
| T3 业务认证通道 | `openbase/core/deps/auth.py` | `get_current_user`（JWT + `sk-agent`）、`get_proxy_identity`（服务 Key）接入守卫（局部导入防循环） | 有/无租户主体行为符合三态 |
| T4 MCP 通道 | `openbase/modules/mcp/credentials.py` | 静态 Key 租户改 `get_current_tenant`；三分支末尾统一守卫 | 非受信 `X-Tenant-Id` 不采纳 |
| T5 主体创建治理 | `openbase/modules/identity/__init__.py` | `create_agent` 经 `ensure_agent_tenant_bound` 解析归属租户 | `enforce` 下无租户创建 → `400 PARAM_INVALID` |
| T6 测试 | `tests/test_entry_tenant_guard.py`（新增）、`tests/test_q5_q6_decisions.py`（更新） | 覆盖 T1–T5 的验收点 | 定向用例 + 全量回归通过 |
| T7 文档留痕 | 本方案 + 审计报告 | 版本与修订历史同步 | 版本一致、无重复事实源 |

验证命令：

```powershell
D:\venvs\openbase\Scripts\ruff.exe check openbase tests
python -m pytest tests/test_entry_tenant_guard.py tests/test_q5_q6_decisions.py tests/test_mcp_edge_credentials.py tests/test_identity_t1.py tests/test_proxy_auth.py -q
python -m pytest tests
```

#### 7.7.6 入口守卫验收矩阵

| 场景 | 期望 |
|---|---|
| `off` + 空租户主体 | 放行，缺失计数不变 |
| `shadow` + 空租户主体 | 放行，计数 +1，WARN 含 `channel`（不含凭证） |
| `enforce` + 空租户主体 | `403 AUTH_403`，`detail.reason=tenant_unbound` |
| 有租户主体（任一通道） | 行为与现网一致，不计数 |
| `auto` 解析 | production → `enforce`；development → `off`；非法值 → 启动失败 |
| 生产门禁 | 入口模式非 `enforce`，或存在 per-target 兜底码 → 拒绝启动 |
| 兜底清空 | `default_tenant_code: null` 后 `resolve_target_code_space` 返回 `None`，门禁通过 |
| MCP 伪造租户 | 非受信来源 `X-Tenant-Id` 不采纳（`credential.tenant_code` 为空） |
| agent 创建 | `enforce` 下无 `tenant_id` 且操作者无租户 → `400 PARAM_INVALID`；`off/shadow` 兼容 |

#### 7.7.7 实施状态与推进顺序

- **当前状态**：批次 1 已完成（v1.4.0）：T1–T6 落地并与 R4、R3 短期同批交付；生产切换（`enforce`）仍按 §7.7.3 顺序待执行。
- **推进顺序**：T1/T2/T6（守卫 + 配置 + 单测，`off/shadow`）→ T3/T4/T5（四通道接入 + 创建治理）→ 生产 `shadow` 观察 → 配置清空出站兜底并启用 `enforce` → 旧 token 重签窗口 → L4 存量盘点迁移。
- **回滚**：非生产 `OPENBASE_ENTRY_TENANT_ENFORCE=off`；生产需整体回退版本（启动门禁不允许生产停留 `off`）。

---

## R6 记忆列表 → 原生分页

### 方案

1. OpenMemory 新增 `GET /api/v1/memories`：
   - 参数：`user_id`、`session_id`、`memory_type`、`is_active`、`created_after`、`offset`、`limit`（≤100）；
   - 响应：`{items: [MemoryResult], total, has_more}`；
   - 排序固定 `created_at DESC, id DESC`；查询参数化并强制 tenant/owner 过滤。
2. Service 层新增 `list_memories(scope, filters, offset, limit)`；Repository 增加 count 查询（同一 where 条件，避免 total 与 items 不一致）。
3. 门户 `memory_proxy` 的 `/memories` 改为直连该接口，保留旧 recall 兜底（`OPENBASE_MEMORY_LIST_MODE=page|recall`）。

### 验收

- 1000 条记忆下任意页 `items` 数量恒定、`total` 稳定；
- 列表 P95 < 300ms（同机）；
- 租户/owner 过滤正确，跨租户不返回任何行。

### 回滚

切回 `recall` 模式即恢复现网行为。

---

## R8 索引失败 → reindex + 重试入口

### 方案

1. OpenRAG 新增 `POST /api/v1/collections/{collection_id}/documents/{document_id}/reindex`：
   - 前置：collection 域校验（同 `query._verify_collection_in_scope`）；
   - 行为：文档状态置 `PENDING`、清理旧 chunk、复用现有索引任务（`documents.py:324-361`）；
   - 幂等/限流：同 doc 处理中返回 `409 BIZ_DOC_INDEXING`；同 doc 重试间隔 ≥60s，超限 `429`。
2. 门户 `rag_proxy` 新增对应代理路由；文档详情页在 `status=ERROR` 时展示"重试索引"按钮与最近错误原因。
3. 指标：`openrag_reindex_total{result="accepted|conflict|rate_limited"}`。

### 验收

- `ERROR` 文档点击重试 → `PENDING → SUCCEEDED`，`doc_id` 不变，chunk 数恢复；
- 60s 内重复点击返回 429，且不产生重复索引任务；
- 跨租户重试返回 404。

### 回滚

隐藏门户按钮即可；OpenRAG 新路由无副作用。

---

## R9 画像 person_id 口径 → external_id 映射

> **[已实现 v1.6.0｜批次 3]** DPS `profile.external_id` 列 + 部分唯一索引
> `uq_profile_org_external`（PG/SQLite 幂等迁移），PUT/PATCH 顶层 `external_id`
> 落列（同 org 冲突 409 `BIZ_EXTERNAL_ID_CONFLICT`），新增
> `GET /api/v2/portrait/by-external/{external_id}`；门户新增
> `GET /api/v1/dps-proxy/portraits/by-external/{external_id}`；OpenLLM 画像回写
> 携带 `external_id`（subject_id → external_user_id → 不携带）。
> **偏差**：允许仅 `external_id` 的更新请求（单独登记映射）。

### 方案

1. DPS `profile` 表新增 `external_id VARCHAR(128)`，唯一索引 `(org_id, external_id)`（幂等迁移）。
2. 新增 `GET /portrait/by-external/{external_id}`：按 `X-Org-ID` + external_id 查；无记录 404 `NOT_FOUND`。
3. 计算/写入：`POST /portrait/calculate`、`PATCH/PUT /portrait/{person_id}` 支持 `external_id` 作为 person_id 解析（先查映射，再落 person_id）。
4. 回填：现有 OpenLLM 回写产生的 person_id 与 external_id 同值 → 迁移脚本 `UPDATE profile SET external_id = person_id WHERE external_id IS NULL AND person_id ~ '^[A-Za-z0-9_-]+$'`（按实际生成规则裁剪）。
5. 门户画像页：登录用户查自己时走 `by-external`；管理员查他人沿用 `person_id`。

### 验收

- 同一用户聊天回写的标签，可在门户按登录身份查到；
- `person_id ↔ external_id` 双向可解析；重复 external_id 插入被唯一索引拒绝；
- 灰度期双读一致（by-external 与 person_id 命中同一条）。

### 风险

历史数据中 external_id 生成规则不统一 → 先抽样比对 100 条再全量回填；保留 `person_id` 主键不变，避免外键级联。

---

## R7 上下文裁剪策略 → 透传 + 回显

> **[已实现 v1.6.0｜批次 3]** OpenLLM `build_history_ctx` 支持
> `recent/head_tail/system_priority/summarize_old` 四策略与
> `build_history_selection` 统计；网关 `context_policy` 校验（非法 4003）并在同步
> `data.context_meta` / 流式 routing 事件回显；门户前置校验（400 `PARAM_INVALID`）
> 并在上游缺失时补 `context_meta` 默认值。不传策略时与旧实现逐字一致。
> 前端设置页展示延后至批次 4。

### 方案

1. `llm_proxy` chat DTO 增加可选 `context_policy`：

```json
{"strategy": "recent|head_tail|system_priority|summarize_old",
 "max_tokens": 4096, "preserve_system": true}
```

   - 校验白名单与 `max_tokens` 上限；缺省不传 → 保持 OpenLLM 现行为。
2. OpenLLM `/openllm/v1/chat` 读取该字段并调用 `context/manage`（`context.py:41-59`），在响应 `meta.context` 回显 `{strategy, before_tokens, after_tokens, dropped_messages, summarized}`。
3. 门户设置页展示当前租户默认策略（只读），管理员可改；改动记审计。

### 验收

- 传 `summarize_old` 时响应 `meta.context.summarized=true`，且总 token 低于上限；
- 不传时响应/日志与现网一致（无新增字段或字段为 null）；
- 非法策略返回 400 `PARAM_INVALID_CONTEXT_POLICY`。

---

## 4. 实施批次与依赖

| 批次 | 条目 | 依赖 | 产出 |
|---|---|---|---|
| 批次 1（低风险、快速见效） | R4、R3 短期、**R5 入口守卫 T1–T6（代码 + `shadow`）** | 无 | 门户 PATCH、30s 超时、守卫三态与缺租户计数（`jwt/sk-agent/service-key/mcp/agent-create`） |
| 批次 2（数据正确性） | R1、R6、R8、R3 长期 | R1 需 DPS 迁移列；R6 需 OpenMemory 新接口 | 合并写、原生分页、索引重试、异步计算 |
| 批次 3（结构收敛） | R2、R9、R7、**R5 入口 `enforce` + G5 兜底清理 + G2 agent 租户治理** | 用户/服务 Key/agent 绑定盘点；旧 token 重签窗口；R2 需 ADR 裁定与迁移窗口 | 单一 KB 源、person 映射、策略可配、入口强制 |
| 独立轨道（贯穿批次 1–3） | R5 L3–L4（出站纵深 + 存量迁移） | 服务主体清单、存量 `default`/`openrag-local`/`tenant-1` 数据量盘点 | 租户归属统一，见 R5-专项与 §7.7 |

跨仓改动需保持"先加能力、后切开关、再删旧路径"的顺序；每批完成后按报告第 4 节联调清单回归。

---

## 5. 端到端验收矩阵（回归用）

| 场景 | 步骤 | 期望 |
|---|---|---|
| 上下文多轮 | 同 session 两轮 chat | 第二轮引用首轮事实；conversations 4 条 |
| 记忆增改查 | remember → PATCH → recall | 修改生效；审计含 update |
| 知识库闭环 | 建库→上传→轮询→检索→失败重试 | 状态 PENDING→SUCCEEDED；检索带引用；重试可用 |
| 画像合并 | 两次 chat 产生不同标签 | 标签共存，无覆盖；冲突可重试 |
| 租户隔离 | 跨租户读写 | 读 404 / 写 400，三系统一致 |
| 超时兜底 | 触发 >10s 计算 | 202+task 或 30s 内完成，无 504 |
| 双源一致性（R2 后） | 门户与 OpenLLM 列表对比 | collection 与文档数一致 |
| 入口租户（`off/shadow`） | 无租户 JWT / `sk-agent` / 服务 Key / MCP 调用 | 放行；`shadow` 下缺失计数递增并留 WARN |
| 入口租户（`enforce`） | 上述四通道无租户调用 | `403 AUTH_403`，`detail.reason=tenant_unbound`；有租户调用不受影响 |
| 生产启动门禁 | 入口模式非 `enforce` / 存在 per-target 兜底 | 拒绝启动并给出配置指引 |
| agent 创建 | `enforce` 下无 `tenant_id` 且操作者无租户 | `400 PARAM_INVALID`（`detail.reason=tenant_unbound`） |

---

## 6. 附录：接口变更汇总

| 仓 | 方法 | 路径 | 类型 | 说明 |
|---|---|---|---|---|
| DPS | PATCH | `/api/v2/portrait/{person_id}` | 新增 | 深合并 attributes + If-Match |
| DPS | POST | `/api/v2/portrait/calculate?async=true` | 增强 | 返回 task_id |
| DPS | GET | `/api/v2/portrait/tasks/{task_id}` | 新增 | 任务状态 |
| DPS | GET | `/api/v2/portrait/by-external/{external_id}` | 新增 | 外部 ID 查询 |
| OpenMemory | GET | `/api/v1/memories` | 新增 | 原生分页列表 |
| OpenRAG | POST | `/api/v1/collections/{id}/documents/{doc_id}/reindex` | 新增 | 重建索引 |
| OpenBase | PATCH | `/api/v1/memory-proxy/memories/{id}` | 新增 | 记忆编辑代理 |
| OpenBase | POST | `/api/v1/rag-proxy/collections/{id}/documents/{doc_id}/reindex` | 新增 | 重试索引代理 |
| OpenBase | POST | `/api/v1/llm-proxy/chat` | 增强 | 可选 context_policy |
| OpenLLM | POST | `/openllm/v1/chat` | 增强 | 响应回显 meta.context |

### 6.1 配置项变更（v1.3.0）

| 配置 | 默认 | 说明 |
|---|---|---|
| `OPENBASE_ENTRY_TENANT_ENFORCE` | `auto` | `auto｜off｜shadow｜enforce`；`auto`：production → `enforce`、其余 → `off`；非法值启动失败 |
| `OPENBASE_PROXY_CODE_MAP`（语义扩展） | 空 | `targets.<t>.default_tenant_code: null` 表示清空该目标内置兜底（生产门禁要求） |

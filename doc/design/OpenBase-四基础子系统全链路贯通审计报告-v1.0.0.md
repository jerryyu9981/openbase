# OpenBase 四基础子系统全链路贯通审计报告

| 项 | 内容 |
|---|---|
| **版本** | v1.0.0 |
| **状态** | [Review] |
| **审计对象** | OpenBase（门户/网关）× OpenLLM（推理）× OpenMemory（记忆）× OpenRAG（知识库）× DPS（画像） |
| **审计方式** | 五仓源码静态核对 + 跨仓契约逐字段对照（未含运行期联调） |
| **作者** | 架构组 |
| **日期** | 2026-11-12 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-12 | 首版：四类能力（上下文/记忆/知识库/画像）全链路核对，输出 5 项 P1、4 项 P2 及针对性方案 | 架构组 |

---

## 1. 总体结论

**契约级主链已贯通，运行期存在 5 个 P1 断点/风险。** 四类能力在 OpenBase 都有对外入口，且 OpenLLM 网关注释了「画像注入 → 记忆召回 → 知识库检索 → 推理 → 三路写回」的编排闭环。但以下问题会导致「看似通、实则丢数据/不可达/双事实源」：

| 编号 | 级别 | 结论 | 一句话影响 |
|---|---|---|---|
| R1 | P1 | 画像回写为**覆盖写** | 增量标签会抹掉同 person 的其他 attributes |
| R2 | P1 | **双知识库事实源** | OpenLLM 自带 KB 与 OpenRAG 数据互不可见 |
| R3 | P1 | DPS 计算**同步**执行 | 大画像计算超 OpenBase 10s 超时 → 504 |
| R4 | P1 | 记忆**编辑入口缺失** | OpenMemory 有 PATCH，OpenBase 无代理路由 |
| R5 | P1 | 缺租户头时**三系统行为不一致** | default / 保留码兜底 / fail-closed，存在串租与"归属漂移" |
| R6–R9 | P2 | 列表口径、裁剪策略、索引重试、person_id 口径 | 影响体验与可运维性，不阻断主链 |

### 1.1 贯通矩阵

| 能力 | OpenBase 入口 | 承载子系统 | 状态 | 断点 |
|---|---|---|---|---|
| 上下文 | `/api/v1/llm-proxy/chat`、`/conversations` | OpenLLM（conversations + 裁剪） | 贯通 | 裁剪策略不可配（R7） |
| 记忆 | `/api/v1/memory-proxy/*` | OpenMemory 8020 | 部分贯通 | 无编辑入口（R4）、列表口径（R6） |
| 知识库 | `/api/v1/rag-proxy/*` | OpenRAG 8010 | 贯通（单源） | 与 OpenLLM 自带 KB 双源（R2）、无重试入口（R8） |
| 画像 | `/api/v1/dps-proxy/*` | DPS 8030 | 部分贯通 | 覆盖写（R1）、同步超时（R3）、person_id 口径（R9） |

---

## 2. 链路核对（证据）

### 2.1 上下文链路

`openbase-ui` 在 chat 请求体注入 `session_id`（`openbase-ui/src/core/session.ts:67-72`，显式 `session_id` 优先，否则取本地会话）→ `llm-proxy` 原样转发（`openbase/modules/llm_proxy/__init__.py:343-419`）→ OpenLLM `/openllm/v1/chat` 以 `chat_req.session_id` 取历史（`OpenLLM/backend/app/api/openllm_gateway.py` 内 `history_ctx`）→ 会话消息落 `/api/v1/conversations/{id}/messages`（`conversations.py:176-219`）。

结论：**多轮上下文贯通**。裁剪由 OpenLLM `context/manage` 的 `recent/head_tail/system_priority/summarize_old` 策略承担（`context.py:41-59`），但 OpenBase 未暴露该参数（R7）。

### 2.2 记忆链路

- 读：OpenLLM 网关 `_recall_memories` → OpenMemory `/api/v1/recall`（真实契约 Real 模式）。
- 写：回写回调 → `/api/v1/remember`；OpenMemory 侧走 async 模式 outbox → `EmbeddingWorker` → Qdrant；会话过期由 `scripts/session_promote_worker.py` + cron 驱动。
- 门户直连：`memory_proxy` 提供 `remember/recall/forget/memories/sessions/decay/graph/monitor/health`（`openbase/modules/proxy/memory_proxy.py:291-645`），并注入 `X-API-Key`、透传原 JWT、身份四头（同文件 `:82-122`）。

缺口：OpenMemory 已提供 `PATCH /api/v1/memories/{memory_id}`（`OpenMemory/src/openmemory/api/controllers.py:615`），**OpenBase memory-proxy 无对应路由** → 门户无法纠错/改归属，记忆闭环只有"增删查"没有"改"。

### 2.3 知识库链路

门户：`rag_proxy` 覆盖 collections CRUD、documents 上传/列表/详情/删除、`query`、`query/stream`、`query/retrieve`（`openbase/modules/rag_proxy/__init__.py:435-622`），上游路径与 OpenRAG 注册路径逐一对应（`OpenRAG/src/openrag/api/routes/query.py:164` 的 `POST /{collection_id}/retrieve` 等）。

OpenRAG 侧：创建库按 `tenant_code` 查重并同步建向量集合（`collections.py:142-190`）；上传 → 去重 → 异步索引 → 失败置 `ERROR`（`documents.py:124-201,324-361`）；检索前 `_verify_collection_in_scope` 做域校验（`query.py:19-43`），跨域统一 404（fail-closed）。

OpenLLM 侧：chat 的 RAG 检索与回灌均走 OpenRAG 真实契约（`edgerouter/adapters/openrag_client.py`：`/api/v1/collections/{id}/query/retrieve`、`/api/v1/documents/text`、`/api/v1/documents/{id}`）。**但 OpenLLM 同时保留自建 `knowledge_bases`/`documents`（`OpenLLM/backend/app/api/knowledge_bases.py`，本地向量库）** → 双事实源（R2）。

### 2.4 画像链路

门户：`dps_proxy` 提供 `/portraits`、`/portraits/{id}`、`/portraits/calculate`、PUT 等（`openbase/modules/dps_proxy/__init__.py:347-414`），与 DPS `/api/v2/portrait/*` 对齐（`DPS/src/rest_api/routes/routes_profiles.py:127-162,165,1410-1449`）。

OpenLLM 侧：chat 前注入画像上下文，chat 后 `_profile_writeback` → `PUT /api/v2/portrait/{person_id}`（`writeback.py:215-245`、`edgerouter/adapters/profile.py:403-424`）。

角色契约已收敛：DPS 入站码表覆盖 OpenBase 透传码 `admin/org_admin/user/org_member/viewer`（`DPS/src/identity/role_map.py:49-58`）；OpenMemory 侧同样按 OpenBase 码映射。

---

## 3. 问题清单与针对性解决方案

### R1（P1）画像回写整体覆盖，存在字段丢失

**现象**：DPS `PUT /api/v2/portrait/{person_id}` 的 `business.attributes` 采用整体覆盖写、不 merge（`DPS/src/rest_api/routes/routes_profiles.py:1421-1422` 设计约束明示）；OpenLLM 回写直接把增量 `updates` 映射后 PUT（`adapters/profile.py:403-424`），无读-改-写。

**影响**：两个模板命名空间（`attributes_json[template_code]`）或人工维护标签会被单次对话回写抹掉；且并发回写互相覆盖。

**方案**：
1. `dps_client.profile_update` 前增加 `GET /api/v2/portrait/{person_id}`，将 `updates.business.attributes` 与现有 attributes 深合并（保留未提交键），并带上 `updated_at` 做乐观锁（DPS 增加 `If-Unmodified-Since`/版本列校验，冲突返回 409）。
2. 或由 DPS 提供 `PATCH` 语义端点（深合并 + 字段级审计），OpenLLM 改用 PATCH；PUT 保留整体覆盖供管理端使用。
3. 回写失败保持现有"跳过不伪造"语义，但在响应/日志中标注 `writeback=merged|conflict|skipped`。

**验收**：同一 person 写入 `{tags:[A]}` 后再写 `{tags:[B]}`，`GET` 返回 `{tags:[A,B]}`；并发两次写触发一次 409 且重试后合并成功；attributes 差异快照写入审计。

### R2（P1）双知识库事实源

**现象**：OpenLLM 拥有独立 `knowledge_bases`/`documents` 与本地向量库（`OpenLLM/backend/app/api/knowledge_bases.py:33-211`），同时 chat 检索走 OpenRAG；OpenBase 门户只对接 OpenRAG（`rag_proxy`）。

**影响**：用户在 OpenLLM 页面建的库不会出现在门户；门户建的库聊天检索可见但 OpenLLM 页面不可见；两套向量化/权限/生命周期策略并行。

**方案**：
1. 裁定唯一事实源 = OpenRAG；OpenLLM `knowledge_bases` 路由标记 `deprecated`，内部改为 OpenRAG 客户端代理（保留路径，避免前端 404）。
2. 迁移：一次性脚本把 OpenLLM KB/document 元数据映射到 OpenRAG collection/document（按 tenant 建 collection，文档重放 `/documents` 异步索引），迁移后下线本地向量库写入。
3. 门户 `rag-proxy` 保持唯一入口；OpenLLM 页面改为调用 OpenBase `rag-proxy` 或直接 OpenRAG。

**验收**：门户与 OpenLLM 页面看到同一 collection 列表（同 tenant 下完全一致）；新建文档只产生一份 chunk（Qdrant 计数一致）；旧 KB 接口返回 200 且数据来自 OpenRAG。

### R3（P1）DPS 画像计算同步执行，超时风险

**现象**：`POST /portrait/calculate` 在请求内 `await portrait_engine.calculate_portrait`（`routes_profiles.py:151-162`）；OpenBase `dps_proxy` 使用统一上游超时（`dps_proxy/__init__.py:282` 传 `timeout`，来源为模块配置），默认量级 10s。

**影响**：批量/全维计算超过超时 → 门户 504，且**计算可能已成功**，用户重试造成重复计算；无任务态可查。

**方案**（按改动成本排序）：
1. 短期：OpenBase 对 `portraits/calculate` 路径单独放宽到 30s（复用 `proxy/__init__.py:95-105` 的 `SLOW_PATH_HINTS` 机制），并对 504 提示"可能已提交"。
2. 中期：DPS 增加异步计算 `POST /portrait/calculate?async=true` → 返回 `task_id`，新增 `GET /portrait/tasks/{task_id}`；门户轮询并展示进度。
3. 幂等：以 `(person_id, template_code, data_version)` 做计算去重，重复提交返回同一 task。

**验收**：10s 以上计算返回 202+task_id 且最终可查到结果；同参数重复提交不产生重复计算记录。

### R4（P1）记忆编辑闭环缺失

**现象**：OpenMemory 支持 `PATCH /api/v1/memories/{memory_id}`（含 owner 变更守卫 `MEMORY_OWNERSHIP_CHANGE_FORBIDDEN`，v1.3.2 R2）；OpenBase `memory_proxy` 无 PATCH 路由（`memory_proxy.py:291-645` 仅 GET/POST）。

**影响**：门户记忆页只能新增/删除/查询，无法纠错内容或调整归属；与"记忆全生命周期"要求不符。

**方案**：
1. 新增 `@router.patch("/memories/{memory_id}")` 转发 `/api/v1/memories/{memory_id}`，请求体白名单与 OpenMemory DTO 对齐（`content/memory_type/metadata/owner` + `allow_ownership_change`）。
2. 错误映射：404→`NOT_FOUND`、400 `MEMORY_OWNERSHIP_CHANGE_FORBIDDEN`/`SCOPE_REQUIRED` 原样透传 code、其余 500→`UPDATE_FAILED`。
3. 前端记忆详情页加"编辑"表单，owner 变更需二次确认勾选。

**验收**：门户改内容后 `GET /memories/{id}` 生效；未勾选授权改 owner 返回 400 且库内不变；审计日志含 update 动作与主体。

### R5（P1）缺租户头时三系统行为不一致

**现象**：门户出站统一由 `protocol_headers/inject.py:102-150,172-248` 注入四头，但缺失时各系统兜底不同——OpenMemory 落 `default`；OpenRAG 有"保留码兜底/租户码对齐"（`rag_proxy/__init__.py:126-170`）；DPS 角色绑定 fail-closed。

**影响**：同一请求在三个子系统可能落到不同归属域；若门户漏注入，数据写入 `default` 形成跨租可见面。

**方案**：
1. `build_outbound_headers` 增加强校验开关：对 `chat/remember/documents/portrait-write` 等写路径，缺 `X-Tenant-ID` 直接 400 `PARAM_TENANT_REQUIRED`（不进入上游）。
2. 读路径缺租户头时按角色限定：平台管理员可用 `X-Tenant-ID` 显式选择，普通用户 fail-closed。
3. 三系统统一 `default` 语义仅用于本地单机开发（`ENV=dev` 且显式开关），生产禁用。
4. 观测：缺租户头计数指标 + 审计事件，灰度一周后转强制。

**验收**：生产配置下无租户头的写请求 100% 被门户拒绝；三系统对同一请求的 tenant 归属一致（审计日志可比对）。

### R6（P2）`/memories` 列表基于 recall + 本地分页

**现象**：门户列表通过 `recall` 召回后本地过滤/分页（`memory_proxy.py:361` 起）。

**影响**：`total` 与翻页不稳定；记忆量大时 recall 压力放大。

**方案**：OpenMemory 增加 `GET /api/v1/memories?offset&limit&filters` 原生分页（返回 `items/total`），proxy 直连；过渡期返回 `has_more` 而非伪 total。

**验收**：1000 条记忆下任意页 `items` 数量恒定、`total` 稳定；列表 P95 < 300ms。

### R7（P2）上下文裁剪策略不可配、不可见

**现象**：OpenLLM 提供 `POST /api/v1/context/manage`（`context.py:41-59`），门户未透传；聊天裁剪仅由 OpenLLM 内部决定。

**影响**：长会话截断行为对用户不透明，无法按租户/场景调优（成本 vs 效果）。

**方案**：`llm_proxy` chat 请求体增加可选 `context_policy`（`recent|head_tail|system_priority|summarize_old` + 预算 token），透传到 OpenLLM；默认保持现状；门户设置页提供只读展示 + 管理员可改。

**验收**：传 `context_policy=summarize_old` 时 OpenLLM 走摘要分支（日志/响应标注）；不传时行为与现今一致。

### R8（P2）知识库索引失败无重试入口

**现象**：OpenRAG 后台索引失败把文档置 `ERROR`（`documents.py:324-361`），门户 `rag_proxy` 只有上传/查询/删除，无重建索引路由。

**影响**：解析失败需人工删档重传，文档 ID 与外部引用断链。

**方案**：OpenRAG 增加 `POST /api/v1/collections/{id}/documents/{doc_id}/reindex`（复用现有索引任务，状态回 `PENDING`），门户暴露对应代理 + 详情页"重试"按钮；限制每分钟重试次数。

**验收**：`ERROR` 文档点击重试后状态流转 `PENDING→SUCCEEDED`，doc_id 不变；重复重试触发限流 429。

### R9（P2）画像 person_id 口径待联调确认

**现象**：OpenLLM 读/写画像使用 `external_user_id`（注释称"读写同键，`openllm_gateway.py:1178`"）；门户画像页按 DPS `person_id` 查询/计算。若 DPS 主键与外部用户 ID 不是同一空间，则"聊天写回的画像"在门户查不到。

**方案**：DPS 增加 `external_id` 映射列（唯一索引 `(org_id, external_id)`），`GET /portrait/by-external/{external_id}`；OpenBase 门户画像查询统一走该端点；迁移期双写。

**验收**：同一用户聊天后回写的标签，在门户按登录用户可查到；`person_id` 与 `external_id` 双向可解析。

---

## 4. 联调验证清单（建议按序执行）

| # | 目标 | 操作 | 通过标准 |
|---|---|---|---|
| 1 | 上下文 | 同一 `session_id` 连发 2 轮 chat | 第 2 轮回答引用第 1 轮事实；`/conversations/{id}/messages` 有 4 条 |
| 2 | 记忆读 | chat 后 `GET /memory-proxy/recall` 同 user | 召回含本轮事实；OpenMemory `embedding_outbox` 终态 done |
| 3 | 记忆写/改 | `PATCH /memory-proxy/memories/{id}` | 内容更新生效、审计可见（R4 完成后） |
| 4 | 知识库 | 建库→上传→轮询文档状态→`query/retrieve` | 文档 `SUCCEEDED`，检索命中且带 doc/chunk 引用 |
| 5 | 知识库隔离 | 用租户 B 查租户 A 的 collection | 404（不得 200） |
| 6 | 画像读 | `POST /dps-proxy/portraits/calculate` → `GET /portraits/{id}` | 返回六维 + attributes |
| 7 | 画像写 | 聊天两次，分别产生标签 A、B | `GET` 同时含 A、B（R1 完成后） |
| 8 | 租户缺省 | 去掉 `X-Tenant-ID` 调写接口 | 400 `PARAM_TENANT_REQUIRED`（R5 完成后） |

---

## 5. 结论

- **上下文**：贯通，仅缺策略可配（R7，P2）。
- **记忆**：读写编链已通（含异步 embedding、outbox、session 生命周期），门户缺"改"（R4，P1）。
- **知识库**：门户与 OpenRAG 契约逐条对齐、租户校验 fail-closed；主要风险是与 OpenLLM 自带 KB 的双源（R2，P1）。
- **画像**：读/算/写入口齐全、角色双码面已收敛；风险集中在覆盖写（R1）、同步超时（R3）、person_id 口径（R9）。

建议排期：R1 → R4 → R5 → R3（短期超时兜底）→ R2 → R7/R8/R6/R9。

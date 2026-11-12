# 批次 5：统一前端四子系统全生命周期补齐（规格）

| 项 | 内容 |
|---|---|
| **版本** | v1.2.0 |
| **状态** | [Final]（已实施并验证，含 5.1 增量） |
| **适用范围** | OpenBase（`openbase` 门户后端 rag_proxy / dps_proxy、`openbase-ui` 统一前端） |
| **上游依据** | 批次 2/3/4 全链路贯通修复规格；《OpenBase-四基础子系统全链路贯通审计报告-v1.0.0》；门户代理现有端点（以代码为准） |
| **作者** | 架构组 |
| **日期** | 2026-11-13 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-13 | 首版：以门户既有代理端点为准，盘点上下文（会话）/记忆/画像/知识库四子系统的前端生命周期缺口，定义补齐范围、接口契约、页面改动、验收标准与验证命令 | 架构组 |
| v1.1.0 | 2026-11-13 | 实施完成：T1~T10 全部交付；补记实施偏差（会话 API 独立文件、radio value、删除确认方式、监控指标渲染口径等）；验证结果 41 项前端用例、157 项后端用例、ruff/vue-tsc 0 错误 | 架构组 |
| v1.2.0 | 2026-11-13 | 批次 5.1：补齐画像 DELETE 端点（DPS 软删除 + 门户代理 + 前端入口），关闭 §1.2 与 D7 登记的「画像无删除」缺口；新增 §11 | 架构组 |

---

## 1. 范围与约束

### 1.1 目标

以 OpenBase 门户后端**已存在**的 `/api/v1/llm-proxy`、`/api/v1/memory-proxy`、`/api/v1/dps-proxy`、`/api/v1/rag-proxy` 接口为基线，补齐 `openbase-ui` 中四个业务子系统的**全生命周期**操作（列表 → 详情 → 创建 → 更新 → 检索/运行 → 删除/归档 → 监控），使统一前端上每个子系统的生命周期闭环、无假数据、无断头路。

### 1.2 不含（明确不做）

| 项 | 原因 |
|---|---|
| 新增记忆/LLM 代理端点 | 现有端点已覆盖生命周期，缺口仅在前端 |
| 画像删除（DELETE） | ~~门户 `dps_proxy` 与上游 DPS `routes_profiles.py` 均无画像 DELETE，后端无此语义，不做前端入口~~ **已由批次 5.1 补齐（见 §11，v1.2.0）** |
| 记忆「组织事实源」治理页 | 本批次只做记忆运行时监控，不做组织治理 |
| 修改 `openbase-ui/src/modules/openllm/pages/Playground.vue` | 该文件含批次 4 未提交改动，本批次不触碰（见 §1.3） |
| 生产环境 `enforce` 开关、跨租户策略调整 | 与全生命周期无关，沿用既有基线 |

### 1.3 提交边界（重要）

1. `openbase-ui/src/core/api/llm.ts` 与 `Playground.vue` 在工作区含批次 4 遗留未提交改动（批次 4 规格 §1 约束 3 明令不入库）。本批次**不修改、不提交**这两个文件。
2. 会话生命周期新增的两个 API（会话详情、追加消息）放入**新文件** `openbase-ui/src/core/api/conversation.ts`，避免污染 `llm.ts` 的未提交改动。
3. 不触碰 `scripts/service-orchestrator.ps1` 等无关未提交改动。
4. 本批次仅提交：`openbase/modules/rag_proxy/__init__.py`、`openbase/modules/dps_proxy/__init__.py`、对应后端测试、前端 `core/api/conversation.ts`、`core/api/rag.ts`、`core/api/dps.ts`、`modules/memory/index.ts`、`modules/memory/pages/MemoryMonitor.vue`、`modules/openllm/pages/Conversations.vue`、`modules/portrait/pages/PortraitList.vue`、`modules/portrait/pages/PortraitDetail.vue`、`modules/knowledge/pages/KnowledgeDetail.vue`、前端测试与本文档。

### 1.4 统一约束

- 前端不直连上游服务、不构造身份头、不做权限判定（沿用既有禁则）。
- 错误展示统一走 `describeError`（`@/core/api/error`），错误信封保持 `{code, message, detail, request_id}`。
- 新增代码中文注释；命名遵循仓库既有约定（组件 PascalCase、函数 camelCase、常量 UPPER_SNAKE_CASE）。
- 轮询必须有超时与终止条件，不得无限轮询。
- 文档每次更新同步升版本并追加修订历史。

---

## 2. 现状盘点（以代码为准）

### 2.1 后端代理端点（已有）

| 子系统 | 端点（门户路径） | 说明 |
|---|---|---|
| 上下文 | `GET /llm-proxy/conversations` | 会话列表 |
| 上下文 | `POST /llm-proxy/conversations` | 新建会话 |
| 上下文 | `GET /llm-proxy/conversations/{id}` | 会话详情（**前端未使用**） |
| 上下文 | `DELETE /llm-proxy/conversations/{id}` | 删除会话 |
| 上下文 | `POST /llm-proxy/conversations/{id}/archive` | 归档/取消归档 |
| 上下文 | `POST /llm-proxy/conversations/{id}/messages` | 追加消息（**前端未使用**） |
| 上下文 | `GET /llm-proxy/conversations/{id}/messages` | 消息列表 |
| 记忆 | `POST /memory-proxy/remember`、`/recall`、`/forget` | 写入/召回/遗忘 |
| 记忆 | `GET/PATCH /memory-proxy/memories`、`/memories/{id}` | 列表/详情/更新 |
| 记忆 | `GET/POST /memory-proxy/sessions`、`/sessions/{id}/terminate` | 会话管理 |
| 记忆 | `GET /memory-proxy/graph/overview` | 图谱 |
| 记忆 | `GET/PUT /memory-proxy/decay/config` | 衰减配置 |
| 记忆 | `GET /memory-proxy/monitor` | 运行监控（**前端未使用**） |
| 记忆 | `GET /memory-proxy/health`、`/health/readiness`、`/health/liveness` | 健康探针（**前端未使用**） |
| 画像 | `GET /dps-proxy/portraits` | 列表 |
| 画像 | `GET /dps-proxy/portraits/{person_id}` | 详情 |
| 画像 | `GET /dps-proxy/portraits/by-external/{external_id}` | 按外部 ID 查询（**前端未使用**） |
| 画像 | `POST /dps-proxy/portraits/calculate` | 计算（**前端未使用**） |
| 画像 | `GET /dps-proxy/portraits/tasks/{task_id}` | 异步任务（**前端未使用**） |
| 画像 | `PUT /dps-proxy/portraits/{person_id}` | 整体更新 |
| 画像 | `PATCH /dps-proxy/portraits/{person_id}` | 增量更新（支持 `If-Match`，**前端未使用**） |
| 知识库 | `GET/POST /rag-proxy/collections` | 列表/创建 |
| 知识库 | `GET/DELETE /rag-proxy/collections/{id}` | 详情/删除 |
| 知识库 | `PUT /rag-proxy/collections/{id}` | **缺失**（上游 OpenRAG 已有 `PUT /{collection_id}`，支持 `rebuild`） |
| 知识库 | `POST/GET/DELETE /rag-proxy/collections/{cid}/documents[/{did}]` | 上传/列表/详情/删除 |
| 知识库 | `POST /rag-proxy/collections/{cid}/documents/{did}/reindex` | 重建索引 |
| 知识库 | `POST /rag-proxy/collections/{cid}/query`、`/query/stream`、`/query/retrieve` | 问答/流式/纯检索 |

### 2.2 前端页面缺口

| 子系统 | 现有页面 | 缺口 |
|---|---|---|
| 上下文 | `Conversations.vue`（列表/新建/归档/删除/流式聊天） | 打开会话**不加载历史消息**；流式回复**不回写会话**；无会话详情查看 |
| 记忆 | `MemoryList/Detail/Search/Sessions/Graph/Decay/Write` | **无监控页**（monitor/health 三探针未接入） |
| 画像 | `PortraitList/Detail/Search/Tags/Overview/Rules/Dps*` | 无「计算画像」入口；无「按外部 ID 查询」；详情无属性编辑（PATCH） |
| 知识库 | `KnowledgeList/ChatView` | `KnowledgeDetail.vue` **为静态假数据**（硬编码 3 条文档、本地假检索）；无集合更新入口 |

---

## 3. 需求（用户故事 + 验收标准）

### 3.1 上下文（会话）生命周期

- **US-CTX-1**：作为用户，我打开历史会话时希望看到完整消息记录，以便继续阅读上下文。
- **US-CTX-2**：作为用户，我希望在会话抽屉里继续对话，且新消息持久化到该会话，下次打开仍可见。
- **US-CTX-3**：作为用户，我希望流式回复失败时得到明确提示，且不丢失已输入内容。

验收标准：

| 编号 | 验收标准 |
|---|---|
| AC-CTX-1 | 点击「查看/继续对话」后并发加载 `GET /conversations/{id}` 与 `GET /conversations/{id}/messages`，抽屉展示历史消息（user/assistant/system 角色区分、空态提示）。 |
| AC-CTX-2 | 抽屉发送消息后：用户消息与助手回复分别经 `POST /conversations/{id}/messages` 回写（`{role, content, model_name?}`）；回写失败仅提示、不阻断。 |
| AC-CTX-3 | 消息加载中展示 loading；加载失败展示 `describeError` 提示条 + 重试；不得出现空白无反馈。 |
| AC-CTX-4 | 归档会话不参与续聊（后端 400 时前端提示「会话已归档，请先取消归档」）。 |

### 3.2 记忆运行监控

- **US-MEM-1**：作为运维/管理员，我希望在统一前端查看记忆服务的存活、就绪与运行指标，以便定位异常。

验收标准：

| 编号 | 验收标准 |
|---|---|
| AC-MEM-1 | 新增路由 `/memory/monitor` 与菜单「运行监控」，`nav-consistency` 断言通过。 |
| AC-MEM-2 | 页面并发请求 `GET /memory-proxy/health`、`/health/readiness`、`/health/liveness`，分别展示状态徽标。 |
| AC-MEM-3 | 支持 `range` 选择（`1h/24h/7d`）并请求 `GET /memory-proxy/monitor?range=`，展示返回指标（键值 + 数组型序列）。 |
| AC-MEM-4 | 单个探针失败不影响其余展示；失败项展示「不可达」与可重试按钮。 |

### 3.3 画像全生命周期

- **US-POR-1**：作为用户，我希望对指定主体发起画像计算，并看到异步进度与结果。
- **US-POR-2**：作为用户，我希望按业务外部 ID 直接定位画像。
- **US-POR-3**：作为用户，我希望在详情页增量编辑画像属性，并避免并发覆盖。

验收标准：

| 编号 | 验收标准 |
|---|---|
| AC-POR-1 | 列表页提供「计算画像」对话框（`person_id` 必填、`template_code` 选填）；调用 `POST /portraits/calculate`。 |
| AC-POR-2 | 计算返回 `task_id` 时按 2s 间隔、60s 超时轮询 `GET /portraits/tasks/{task_id}`；成功刷新列表，失败/超时给出可读提示；返回同步结果时直接提示并刷新。 |
| AC-POR-3 | 列表页提供「按外部 ID 查询」：调用 `GET /portraits/by-external/{external_id}`，命中后跳转 `/portrait/{person_id}`，未命中展示「未找到」。 |
| AC-POR-4 | 详情页展示画像 `version`；「编辑属性」抽屉提交 `PATCH /portraits/{person_id}`，请求体 `{business:{attributes:{...}}}`，并携带 `If-Match: <version>`。 |
| AC-POR-5 | 属性 JSON 非法时前端拦截并提示；409 `BIZ_VERSION_CONFLICT` 时提示「版本已变更，已刷新最新数据」并重新加载。 |
| AC-POR-6 | 不提供画像删除入口（后端无 DELETE），页面上不做误导性按钮。 |

### 3.4 知识库全生命周期

- **US-KB-1**：作为用户，我希望知识库详情页展示真实的集合信息与文档列表（含处理状态）。
- **US-KB-2**：作为用户，我希望上传文档后能自动跟踪解析/向量化直至完成或失败。
- **US-KB-3**：作为用户，我希望对单个文档重建索引、删除文档。
- **US-KB-4**：作为用户，我希望在检索台做纯检索与 RAG 问答。
- **US-KB-5**：作为用户，我希望修改知识库的分块配置与描述，并在影响存量时得到确认提示。

验收标准：

| 编号 | 验收标准 |
|---|---|
| AC-KB-1 | 详情页不再含任何硬编码文档/检索结果；集合信息来自 `GET /collections/{id}`。 |
| AC-KB-2 | 文档列表来自 `GET /collections/{cid}/documents`，状态映射 `PENDING/PROCESSING/COMPLETED/FAILED` → 待处理/处理中/完成/失败。 |
| AC-KB-3 | 上传经 `POST /collections/{cid}/documents`（multipart），拿到 `document_id` 后轮询 `GET /collections/{cid}/documents/{did}`（2s，最长 120s），终态后刷新列表。 |
| AC-KB-4 | 「重建索引」调用 `POST .../reindex`，429 时提示「操作过于频繁，请 60 秒后重试」。 |
| AC-KB-5 | 「删除文档」调用 `DELETE .../documents/{did}`，二次确认后刷新。 |
| AC-KB-6 | 检索台支持「纯检索」（`POST .../query/retrieve`）与「RAG 问答」（`POST .../query`）两种模式，结果区分展示（片段/评分 vs 答案/来源）。 |
| AC-KB-7 | 集合编辑提交 `PUT /rag-proxy/collections/{id}`；修改 `chunk_strategy/chunk_size/chunk_overlap` 时弹确认「将触发存量文档重建」，确认后携带 `rebuild=true`。 |
| AC-KB-8 | 取消硬编码的 `agentMode` 选择（上游 `/query` 契约无该字段），避免无效参数。 |

---

## 4. 关键业务流程

### 4.1 会话查看与续聊

1. 列表点击「查看/继续对话」→ 打开抽屉，同时请求会话详情与消息列表。
2. 消息按 `created_at` 升序渲染；`role` 决定气泡方向。
3. 输入并发送：先本地追加用户气泡 → `llm-proxy/chat/stream` 流式聚合 → 结束后本地追加助手气泡。
4. 回写：`appendMessage(role=user)` 与 `appendMessage(role=assistant)` 各自独立 best-effort；失败汇总一条 WARN 提示。
5. 关闭抽屉清空本轮临时状态（不缓存半截消息）。

### 4.2 记忆监控

1. 进入页面并发拉取三个探针 + 监控指标。
2. 探针响应映射：`status` 字段存在且为 `ok/healthy/ready` → 正常；非 2xx 或网络错误 → 不可达。
3. `range` 变更仅重拉监控指标，不重拉探针。

### 4.3 画像计算与编辑

1. 计算：`POST /portraits/calculate`，`body={person_id, template_code?}`；门户按设置默认 `async=true` 并以 **query 参数**转发上游。
2. 响应含 `task_id` → 轮询任务；`succeeded` → 刷新列表；`failed` → 展示 `error`。
3. 编辑：读取详情 `version` → 提交 PATCH（`If-Match`）→ 成功刷新；409 → 冲突提示 + 重新加载。

### 4.4 知识库详情

1. 进入页面：`getCollection` + `listDocuments`。
2. 上传：`el-upload` 自定义 `http-request` → 上传 → 轮询单文档状态 → 刷新列表。
3. 检索/问答：模式切换；结果分别渲染。
4. 编辑集合：对话框预填当前配置 → 提交 PUT → 刷新集合信息；分块字段变更时确认 `rebuild=true`。

---

## 5. 接口与数据模型

### 5.1 后端新增/修改

#### 5.1.1 `openbase/modules/rag_proxy/__init__.py`

新增请求模型：

```python
class CollectionUpdate(BaseModel):
    """更新知识库请求体（对齐 OpenRAG CollectionUpdate；embedding 字段不在线变更）. """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    chunk_strategy: str | None = None
    chunk_size: int | None = Field(default=None, ge=100, le=8192)
    chunk_overlap: int | None = Field(default=None, ge=0, le=1024)
    reranker: str | None = None
    retrieval_strategy: str | None = None
    metadata: dict[str, Any] | None = None
```

新增路由（紧随 `rag_collection_detail` 之后，保持路径顺序）：

```python
@router.put("/collections/{collection_id}")
async def rag_collection_update(
    collection_id: str,
    payload: CollectionUpdate,
    request: Request,
    rebuild: bool = Query(False),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """更新知识库（PUT /api/v1/collections/{id}?rebuild=，上游 404/409 透传）."""
    params = {"rebuild": "true"} if rebuild else None
    return await _forward(
        "PUT", f"/api/v1/collections/{collection_id}",
        json_body=payload.model_dump(exclude_none=True, exclude_unset=True),
        params=params,
        request=request, user=_user,
    )
```

约定：
- `embedding_model/embedding_dimension` 不暴露给前端在线修改（上游 409 语义），避免误导。
- 上游 404（跨域不可见）与 409（名称冲突/embedding 变更）由 `_forward` 原样透传，前端按 `describeError` 呈现。

#### 5.1.2 `openbase/modules/dps_proxy/__init__.py`

修正异步参数通道：上游 DPS `POST /api/v2/portrait/calculate` 的 `async` 是 **query 参数**（`async_mode: bool = Query(False, alias="async")`），当前门户注入到 JSON body，导致异步永远不生效。

改动：

```python
@router.post("/portraits/calculate")
async def dps_portrait_calculate(
    payload: dict[str, Any],
    request: Request,
    async_: bool | None = Query(None, alias="async"),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像计算（query ``async`` 透传；缺省按 dps_calc_async_default）. """
    headers = _build_identity_headers(_user, request)
    body = dict(payload)
    body.pop("async", None)
    effective_async = async_ if async_ is not None else get_settings().dps_calc_async_default
    return await _forward(
        "POST", "/api/v2/portrait/calculate",
        json_body=body,
        params={"async": "true" if effective_async else "false"},
        headers=headers,
        request=request,
    )
```

### 5.2 前端接口封装

#### 5.2.1 新增 `openbase-ui/src/core/api/conversation.ts`

```typescript
export interface ConversationMessage {
  id?: string
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
  model_name?: string
  token_count?: number
  created_at?: string
}

export const conversationApi = {
  async getConversation(conversationId: string): Promise<Record<string, unknown>>, // GET /llm-proxy/conversations/{id}
  async appendMessage(conversationId: string, payload: { role: string; content: string; model_name?: string }): Promise<ConversationMessage>, // POST /llm-proxy/conversations/{id}/messages
}
```

#### 5.2.2 `openbase-ui/src/core/api/rag.ts` 追加

```typescript
export interface RagCollectionUpdate {
  name?: string
  description?: string
  chunk_strategy?: string
  chunk_size?: number
  chunk_overlap?: number
  reranker?: string
  retrieval_strategy?: string
  metadata?: Record<string, unknown>
}

async updateCollection(collectionId: string, payload: RagCollectionUpdate, rebuild = false): Promise<RagCollection>
// PUT /rag-proxy/collections/{id}，rebuild 为 true 时 params={rebuild:true}
```

#### 5.2.3 `openbase-ui/src/core/api/dps.ts` 追加

```typescript
async getPortraitByExternal(externalId: string): Promise<DpsPortrait>
// GET /dps-proxy/portraits/by-external/{external_id}

async updatePortrait(personId: string, body: Record<string, unknown>, version?: number): Promise<DpsPortrait>
// PATCH /dps-proxy/portraits/{person_id}，version 存在时携带 If-Match
```

---

## 6. 前端页面与路由改动

| 文件 | 改动 |
|---|---|
| `modules/memory/index.ts` | 新增路由 `{ path: 'monitor', name: 'memory-monitor', … }`；菜单新增「运行监控」`/memory/monitor` |
| `modules/memory/pages/MemoryMonitor.vue`（新） | 三探针状态卡 + `range` 选择 + 监控指标渲染 + 刷新/重试；`data-test`：`memory-monitor-page`、`monitor-range`、`monitor-refresh`、`health-card-{health\|readiness\|liveness}` |
| `modules/openllm/pages/Conversations.vue` | 打开抽屉加载历史；回写消息；加载态/错误条；归档态提示 |
| `modules/portrait/pages/PortraitList.vue` | 「计算画像」对话框（`person_id`/`template_code`、异步轮询）；「按外部 ID 查询」输入 + 按钮 |
| `modules/portrait/pages/PortraitDetail.vue` | 展示 `version`；「编辑属性」抽屉（JSON）→ PATCH（`If-Match`）；409 处理 |
| `modules/knowledge/pages/KnowledgeDetail.vue` | **整体重写**：真实集合信息、文档列表/上传/轮询/重建/删除、检索与问答双模式、集合编辑（`rebuild` 确认） |

`nav-consistency.spec.ts`：`monitor` 进入菜单，无需加入非菜单白名单；其余新增均为页面内弹窗/抽屉，不新增路由。

---

## 7. 非功能需求

| 项 | 要求 |
|---|---|
| 兼容性 | 不新增 npm/pip 依赖；沿用 Element Plus + vue-router + Pinia 既有栈 |
| 性能 | 页面首屏并发请求；轮询间隔 ≥2s，均有超时（画像 60s、文档 120s） |
| 可靠性 | 单请求失败降级为局部提示，不整页崩溃；轮询可取消（组件卸载/关闭抽屉） |
| 安全 | 不记录令牌；JSON 编辑仅提交到本租户主体上下文；不构造身份头 |
| 可维护性 | 状态映射与轮询逻辑集中为页面内小函数；错误统一 `describeError` |
| 可观测性 | 页面操作失败仅提示用户，不打印敏感信息（禁止 `console.log` 请求体） |

---

## 8. 验收标准（汇总）

| 子系统 | 验收编号 | 通过条件 |
|---|---|---|
| 上下文 | AC-CTX-1~4 | 历史加载、消息回写、错误处理、归档态提示全部可用 |
| 记忆 | AC-MEM-1~4 | 监控路由/菜单可导航，三探针与 monitor 指标真实渲染 |
| 画像 | AC-POR-1~6 | 计算（异步/同步）、外部 ID 查询、PATCH 编辑（含 409）可用；无删除入口 |
| 知识库 | AC-KB-1~8 | 无假数据；文档全生命周期 + 双模式检索 + 集合更新可用 |
| 质量门禁 | — | `ruff` 0 错误；后端定向 pytest 全通过；`vue-tsc --noEmit` 0 错误；新增/受影响 vitest 全通过（含 `nav-consistency`） |

验证命令：

```powershell
# 后端静态检查与定向测试
D:\venvs\openbase\Scripts\ruff.exe check openbase tests
$env:OPENBASE_REDIS_URL='redis://127.0.0.1:6399/0'
D:\venvs\openbase\Scripts\python.exe -m pytest tests/test_rag_proxy.py tests/test_dps_proxy.py tests/test_dps_proxy_routes_v1410.py -q

# 前端类型与测试
cd "d:\Trae CN\myproject\Dev\OpenBase\openbase-ui"
.\node_modules\.bin\vue-tsc.cmd --noEmit
.\node_modules\.bin\vitest.cmd run tests/nav-consistency.spec.ts tests/knowledge-lifecycle.spec.ts tests/memory-monitor.spec.ts tests/portrait-lifecycle.spec.ts tests/conversation-lifecycle.spec.ts
```

---

## 9. 风险、假设与约束

| 风险 | 影响 | 缓解 |
|---|---|---|
| 上游 DPS 异步参数语义为 query（已核对） | 当前门户默认异步实际未生效 | §5.1.2 修正 + 单测断言 query 参数与 body 不含 `async` |
| OpenRAG `PUT` 对分块变更触发存量重建 | 大知识库重建耗时 | 前端二次确认 + `rebuild` 显式传参；不做自动轮询重建进度（上游无该端点） |
| 画像详情响应结构可能与 `attributes` 假设不一致 | 编辑抽屉预填为空 | 预填优先 `profile.attributes`，为空时展示 `{}` 并允许手填；失败按 400 提示 |
| `el-upload` 自定义 `http-request` 与 multipart 头冲突 | 上传失败 | 复用 `ragApi.uploadDocument`（内部构造 FormData，不手写 boundary） |
| `Conversations.vue` 依赖 `llm.ts` 未提交改动 | 提交边界冲突 | 新 API 放 `conversation.ts`；不改 `llm.ts` / `Playground.vue` |
| 无画像 DELETE | 生命周期缺「删除」 | 明确登记为后端缺口，不在前端提供入口 |

假设：

1. 门户 `/api/v1/*-proxy` 端点路径与响应信封与代码现状一致（规格编写时已逐条核对）。
2. OpenRAG `CollectionUpdate` 字段名与门户一致（`chunk_strategy/chunk_size/chunk_overlap/reranker/retrieval_strategy/metadata`）。
3. 会话消息接口要求 `role ∈ {system,user,assistant,tool}`、`content` 非空（OpenLLM `MessageCreate`）。

---

## 10. 附录

### 10.1 关键文件清单

- 后端：`openbase/modules/rag_proxy/__init__.py`、`openbase/modules/dps_proxy/__init__.py`、`tests/test_rag_proxy.py`、`tests/test_dps_proxy.py`
- 前端 API：`openbase-ui/src/core/api/conversation.ts`（新）、`rag.ts`、`dps.ts`
- 前端页面：`modules/memory/pages/MemoryMonitor.vue`（新）、`modules/memory/index.ts`、`modules/openllm/pages/Conversations.vue`、`modules/portrait/pages/PortraitList.vue`、`modules/portrait/pages/PortraitDetail.vue`、`modules/knowledge/pages/KnowledgeDetail.vue`
- 前端测试：`openbase-ui/tests/{knowledge-lifecycle,memory-monitor,portrait-lifecycle,conversation-lifecycle}.spec.ts`

### 10.2 术语

| 术语 | 含义 |
|---|---|
| 生命周期 | 列表、详情、创建、更新、检索/运行、删除/归档、监控的完整操作链 |
| 探针 | `health` / `readiness` / `liveness` 三个健康端点 |
| 重建索引 | 对已上传文档重新分块/向量化（`reindex`） |
| 增量更新 | 画像 `PATCH` 深合并语义（dict 递归、list 去重追加、null 删除） |

### 10.3 实施记录与偏差（v1.1.0）

| 编号 | 偏差 / 决策 | 原因 |
|---|---|---|
| D1 | 会话新增 API 落在 `core/api/conversation.ts`，未并入 `llm.ts` | 遵守 §1.3 提交边界，避免污染 `llm.ts` 既有未提交改动 |
| D2 | 知识库检索台模式按钮由 `label` 改为 `value` | Element Plus 3.0 将弃用 `label` 作为值，消除运行时告警 |
| D3 | 文档删除使用 `ElMessageBox.confirm`，未用 `el-popconfirm` | 统一警示文案与错误处理，且便于自动化验证 |
| D4 | 记忆监控指标按「标量→描述列表、结构化→JSON 块」渲染 | `memory-proxy/monitor` 未固定 schema，避免假设字段 |
| D5 | 画像计算异步参数由 body 改为 query（后端修正） | 上游 DPS `async` 为 `Query(alias="async")`，原实现异步不生效 |
| D6 | 画像详情编辑仅提交 `business.attributes`，`If-Match` 取详情 `version` | 对齐 DPS PATCH 深合并契约与乐观锁 |
| D7 | 未提供画像删除入口 | 门户与上游 DPS 均无 DELETE，登记为后端缺口 |
| D8 | 集合更新不暴露 `embedding_*` 字段 | 上游此类变更返回 409，暴露会造成必然失败的入口 |
| D9 | `openbase-ui/tests/knowledge-lifecycle.spec.ts` 上传步骤通过 `ElUpload.props('httpRequest')` 直接调用 | 文件选择器无法在 happy-dom 中交互，直接验证上传→轮询链路 |

验证汇总：`ruff check openbase tests` 全通过；后端定向 pytest 157 passed；`vue-tsc --noEmit` 0 错误；前端 5 个 spec 共 41 passed（含 `nav-consistency` 21 例）。

---

## 11. 增量变更：画像 DELETE 端点（批次 5.1，v1.2.0）

### 11.1 背景

批次 5 盘点时登记缺口（§1.2 与 D7）：门户与上游 DPS 均无画像 DELETE，前端无法完成「删除」生命周期。本次按用户要求补齐，语义定为**软删除**（保留审计）。

### 11.2 端点契约

| 层 | 端点 | 行为 |
|---|---|---|
| 上游 DPS | `DELETE /api/v2/portrait/{person_id}` | 软删除：`status='deleted'`；租户取 contextvar 回退 `X-Tenant-ID`；重复删除返回 200 + `already_deleted=true`；不存在/跨租户 404 |
| 门户 | `DELETE /api/v1/dps-proxy/portraits/{person_id}` | 转发上游并注入统一身份头；状态码与错误码原样透传 |
| 前端 | `dpsApi.deletePortrait(personId)` | 列表行「删除」与详情「删除画像」入口，二次确认后调用；成功后刷新列表/返回列表 |

不做硬删除：`annotation`/`profile_history` 等审计数据强关联，物理删除会破坏审计链。

### 11.3 验收标准

| 编号 | 验收标准 |
|---|---|
| AC-DEL-1 | 软删除后 `GET /portraits/{id}` 与列表均不再返回该画像（`status != 'deleted'` 过滤）。 |
| AC-DEL-2 | 重复删除幂等（200 + `already_deleted=true`），不产生第二次写入。 |
| AC-DEL-3 | 跨租户删除返回 404，且原租户数据保持 `active`（租户隔离）。 |
| AC-DEL-4 | 前端列表/详情删除均需二次确认；成功后列表刷新、详情返回 `/portrait`；404 提示「画像不存在或已被删除」。 |

### 11.4 验证记录

| 范围 | 命令 | 结果 |
|---|---|---|
| DPS | `pytest src/tests/test_batch2_r1_patch_merge.py src/tests/test_batch5_1_portrait_delete.py -q` | 11 passed（新增 4 例：软删除可见性/幂等/404/租户隔离） |
| 门户 | `pytest tests/test_dps_proxy.py -q` | 44 passed（新增 3 例：DELETE 转发/404 透传/幂等透传） |
| 前端 | `vitest run tests/portrait-lifecycle.spec.ts` | 8 passed（新增 2 例：列表删除/详情删除） |
| 静态 | `ruff check`（门户）、`vue-tsc --noEmit` | 0 错误（DPS 存量文件其余告警为历史遗留） |

# OpenBase 系统架构设计文档 - v1.4.4

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.4 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | SA-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/design/ |

---

## 1. 设计目标与范围

| 项 | 内容 |
|----|------|
| 设计范围 | FR-144-01~09（OpenRAG 服务接入 + 认证边界 + rag-proxy 转发 + 前端 2 页真实化 + 联调收尾） |
| 前置验证 | OpenRAG v1.8.0 实际代码核验通过：HTTP API 无认证（仅 MCP 通道有）；核心端点（知识库/文档/查询）；{code,message,data} + {detail} 双错误格式；SSE start→token→done；`OPENRAG_API_PORT` env 覆盖默认 8000；`/api/v1/system/health` 健康检查；OpenAPI 无条件开放；v1.3 双前缀路由（规避） |
| 约束 | 分层架构（Controller/Service/Repository）、错误码统一 BaseError、SQLAlchemy 参数化、结构化日志、向后兼容既有端点（llm_proxy/memory_proxy/网关服务发现） |

## 2. 系统架构

### 2.1 总体架构（v1.4.4 目标态）

```
统一前端（OpenBase frontend，Vue3）
  │  OpenBase JWT（get_current_user）
  ▼
OpenBase 后端（FastAPI，:8000）
  ├─ auth 模块：登录/签发 JWT（既有）
  ├─ llm_proxy 模块：/api/v1/llm-proxy/*（既有，OpenLLM 8001）
  ├─ rag_proxy 模块：/api/v1/rag-proxy/*（v1.4.4 新增）◀── 本版本核心
  │     ├─ 认证：OpenBase JWT 门禁（唯一认证入口，未认证 401）
  │     ├─ 转发：无上游认证注入（OpenRAG 无认证）
  │     ├─ 统一响应：{code,message,data,timestamp}（非 SSE 端点）
  │     ├─ 错误归一化：{code,message,data} + {detail} → 统一提取透传
  │     └─ SSE 透传：start→token→done 逐事件转发（query/stream）
  │
  │  http://127.0.0.1:8010（rag_upstream_base）
  ▼
OpenRAG 后端（FastAPI，:8010，独立部署，v1.8.0）
  ├─ 知识库 /api/v1/collections*（列表/详情/创建/删除）
  ├─ 文档 /api/v1/collections/{cid}/documents*（上传异步/列表/删除）
  ├─ 查询 /api/v1/collections/{cid}/query*（RAG 查询/SSE 流式/检索）
  ├─ 健康 /api/v1/system/health（PG+Qdrant）
  └─ 基础设施：PostgreSQL（或 SQLite）/ Qdrant /（可选 ES/Redis）
```

### 2.2 模块挂载设计

| 项 | 内容 |
|----|------|
| 新增模块 | `openbase/modules/rag_proxy/`（包，`__init__.py` 导出 `router`，前缀 `/api/v1/rag-proxy`，tags=["rag-proxy"]） |
| 启用方式 | `demo_app.py` enable_module 列表追加 `"rag_proxy"`（init_app 自动 import + include_router） |
| 配置项 | `settings.py` 新增 `rag_upstream_base`（默认 `http://127.0.0.1:8010`）/ `rag_upstream_timeout`（20.0）/ `rag_stream_timeout`（120.0）；无 rag_api_key（OpenRAG 无认证） |
| 结构 | 对标 `llm_proxy.py`：`_forward`（转发 + 统一响应）/ `_adapt_response`（统一响应 + {detail} 归一化）/ `_forward_sse`（流式透传）；新增 `_forward_multipart`（文档上传文件透传） |

## 3. 关键架构决策（ADR）

### ADR-144-01 rag-proxy 模块设计（独立模块 vs 扩展既有 proxy/llm_proxy）

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | 新建独立模块 `openbase/modules/rag_proxy/`（路由前缀 `/api/v1/rag-proxy`），不并入 llm_proxy 或通用 proxy |
| 理由 | ① 路由前缀独立（rag-proxy vs llm-proxy）避免认证/转发逻辑耦合；② 上游契约不同（OpenRAG 无认证 + {detail} 错误 + start/token/done SSE），独立模块便于按契约演进；③ 模块启停独立（enable_module） |
| 备选 | A. 扩展 llm_proxy → 否决：跨系统契约混淆（OpenLLM 有认证 vs OpenRAG 无认证）；B. 扩展通用 proxy 通道 → 否决：无法承载 SSE 透传与 {detail} 归一化专用逻辑 |
| 风险 | 模块数量增加 → 注册清单维护成本，随版本演进可控 |

### ADR-144-02 认证边界（OpenBase 唯一认证入口）

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | rag-proxy 全部端点要求 OpenBase JWT（get_current_user，未认证 401）；**无上游认证注入**（OpenRAG HTTP API 无认证，代码核验）；OpenRAG 侧认证体系落地登记任务书（M1），后续版本实施 |
| 理由 | ① OpenRAG 无认证是代码事实（设计文档 v2.1.2 声称 API Key 但未实现）；② OpenBase 作为统一入口汇聚认证是既有模式（OpenMemory/OpenLLM 均经 OpenBase 汇聚）；③ 本版本不扩 OpenRAG 代码（登记任务书，独立会话实施） |
| 备选 | A. 在 OpenRAG 侧实现 API Key 认证 → 延后（任务书 M1，需 OpenRAG 代码改动）；B. 前端直连 OpenRAG → 否决：无认证暴露 + 多入口 |
| 风险 | OpenRAG 能力在 OpenBase 网关后受保护（代理层兜底）；若 OpenRAG 直接暴露到公网则有风险 → 部署约束（仅内网访问，运维手册注明） |

### ADR-144-03 错误归一化与 SSE 透传方案

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | 错误归一化：非 SSE 端点统一响应 {code,message,data,timestamp}，错误提取顺序 body.code > body.detail.error/code > body.detail（字符串）> HTTP 状态码（覆盖 OpenRAG 双格式）。SSE 端点（query/stream）逐事件透传 start→token→done，不缓冲不包装 |
| 理由 | ① OpenRAG 成功用 {code,message,data}、错误大量用 FastAPI {detail}，需归一化供前端统一解析；② SSE 事件语义（start/token/done）需原样透传（统一响应包装会破坏协议） |
| 备选 | A. 前端分别解析两种错误格式 → 否决：前端耦合上游错误细节；B. SSE 聚合 JSON → 否决：丧失流式体验 |
| 风险 | 上游错误格式漂移 → 联调验证 + 任务书登记 |

### ADR-144-04 前端 2 页真实化方式

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | 直接改造既有 OpenRAG 前端页（知识库管理页/RAG 对话页），数据源从 mock 切换为调用 OpenBase rag-proxy；新增统一 API 层封装（`src/core/api/rag.ts`，走既有 http.ts）；文档上传异步 PENDING → 轮询状态展示；SSE 流式渲染复用 parseSseStream 工具（扩展事件类型） |
| 理由 | ① 复用既有页面 UI 骨架；② 走 OpenBase proxy 保证前端不直连 OpenRAG（AC-144-04-3）；③ parseSseStream 已实现通用 SSE 解析（event/data），扩展 start/token/done 事件分发即可 |
| 备选 | 重建新页面 → 否决：重复 UI 工作；前端直连 OpenRAG 8010 → 否决：无认证暴露 + CORS + 双入口 |
| 风险 | 文档上传解析/向量化依赖 embedding/LLM 模型可用性（OQ-144-2）→ 联调确认，失败态前端提示 |

## 4. 数据模型设计

**结论：本版本无新增 OpenBase 本地数据表。**

| 数据 | 归属 | 说明 |
|------|------|------|
| OpenRAG 知识库/文档/查询数据 | OpenRAG 上游（PG/SQLite + Qdrant） | OpenBase 只经 proxy 读写消费，不落本地库 |
| rag_upstream_* 配置 | OpenBase settings/.env | 配置项（rag_upstream_base/timeout/stream_timeout） |
| 审计日志 | OpenBase audit 模块（既有） | proxy 转发关键操作记录审计 |

> 数据库设计不适用说明：无 DDL/迁移/索引设计；既有库表无变更。详见设计评审记录 §不适用项。

## 5. API 设计摘要（详见《OpenBase-API接口设计文档-v1.4.4.md》）

| 方法 | OpenBase 路径 | 上游目标 | 响应 |
|------|---------------|----------|------|
| GET/POST | /api/v1/rag-proxy/collections | /api/v1/collections | 统一 JSON |
| GET/DELETE | /api/v1/rag-proxy/collections/{id} | /api/v1/collections/{id} | 统一 JSON |
| POST | /api/v1/rag-proxy/collections/{cid}/documents | /collections/{cid}/documents | 统一 JSON（multipart） |
| GET/DELETE | /api/v1/rag-proxy/collections/{cid}/documents[/{did}] | 同上游 | 统一 JSON |
| POST | /api/v1/rag-proxy/collections/{cid}/query | /collections/{cid}/query | 统一 JSON |
| POST | /api/v1/rag-proxy/collections/{cid}/query/stream | /collections/{cid}/query/stream | SSE 逐事件 |
| POST | /api/v1/rag-proxy/collections/{cid}/query/retrieve | /collections/{cid}/query/retrieve | 统一 JSON |
| GET | /api/v1/rag-proxy/health | /api/v1/system/health | 统一 JSON |

## 6. 安全设计

| 项 | 方案 |
|----|------|
| 认证边界 | OpenBase JWT 唯一前端入口（get_current_user）；rag-proxy 未认证 401；无上游认证注入 |
| 网络暴露 | OpenRAG 8010 仅本机/内网访问（部署约束，运维手册注明）；公网只能经 OpenBase rag-proxy |
| 输入校验 | proxy 端点入参沿用 Pydantic schema（multipart 文件大小/类型校验透传上游规则） |
| 审计 | proxy 转发关键操作记录审计日志（user_id/端点/HTTP 状态），复用 audit 中间件 |
| 错误处理 | OpenBase 侧 BaseError（AUTH_/SYS_ 前缀）；上游 {detail} 归一化透传 |

## 7. 可观测性

| 项 | 方案 |
|----|------|
| 日志 | rag_proxy 模块结构化日志（logger "openbase.rag_proxy"，extra：path/upstream_status/duration_ms）；不记录 Authorization |
| 指标 | 复用 observability 模块（http 指标挂 path 标签） |
| 追踪 | 转发请求透传 trace 上下文（如有 OTel）；SSE 会话记录 request_id |
| 排障 | 上游不可达 WARN 日志；错误归一化使前端可定位（detail 透传） |

## 8. 一致性约束（对既有架构）

| 约束 | 落实 |
|------|------|
| 分层架构 | rag-proxy 为 Controller 层（路由 + 转发），无业务逻辑层需求；不直接操作 DB |
| 错误码 | OpenBase 侧 BaseError；上游错误归一化不改写 |
| 命名 | 模块 snake_case（rag_proxy）；路由 kebab（rag-proxy）；配置 rag_* 前缀 |
| 日志 | logging + extra，禁止 print |
| 并发 | httpx.AsyncClient 每请求独立（对标 llm_proxy）；SSE 流式超时控制 |

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | SA-OpenBase-Dev | 初始创建：rag_proxy 模块架构（ADR-144-01~04：模块设计/认证边界/错误归一化与 SSE/前端改造）、模块挂载、数据模型不适用、安全/可观测/一致性约束 |

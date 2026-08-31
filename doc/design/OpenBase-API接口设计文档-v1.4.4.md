# OpenBase API 接口设计文档 - v1.4.4

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

## 1. 接口总览

本版本新增 OpenBase 侧 `rag-proxy` 路由族（前缀 `/api/v1/rag-proxy`），全部端点要求 **OpenBase JWT 认证**（`get_current_user`，未认证 401）。**无上游认证注入**（OpenRAG 无认证，OpenBase 为唯一认证入口）。

| # | 方法 | 路径 | 说明 | 上游 | 响应类型 |
|---|------|------|------|------|---------|
| 1 | GET | /api/v1/rag-proxy/collections | 知识库列表 | /api/v1/collections | 统一 JSON |
| 2 | POST | /api/v1/rag-proxy/collections | 创建知识库 | /api/v1/collections | 统一 JSON |
| 3 | GET | /api/v1/rag-proxy/collections/{collection_id} | 知识库详情 | /api/v1/collections/{id} | 统一 JSON |
| 4 | DELETE | /api/v1/rag-proxy/collections/{collection_id} | 删除知识库 | /api/v1/collections/{id} | 统一 JSON |
| 5 | POST | /api/v1/rag-proxy/collections/{collection_id}/documents | 文档上传（multipart，异步） | /collections/{cid}/documents | 统一 JSON |
| 6 | GET | /api/v1/rag-proxy/collections/{collection_id}/documents | 文档列表 | /collections/{cid}/documents | 统一 JSON |
| 7 | DELETE | /api/v1/rag-proxy/collections/{collection_id}/documents/{document_id} | 删除文档 | /collections/{cid}/documents/{did} | 统一 JSON |
| 8 | POST | /api/v1/rag-proxy/collections/{collection_id}/query | RAG 查询 | /collections/{cid}/query | 统一 JSON |
| 9 | POST | /api/v1/rag-proxy/collections/{collection_id}/query/stream | RAG 流式 | /collections/{cid}/query/stream | SSE 逐事件 |
| 10 | POST | /api/v1/rag-proxy/collections/{collection_id}/query/retrieve | 纯检索 | /collections/{cid}/query/retrieve | 统一 JSON |
| 11 | GET | /api/v1/rag-proxy/health | 上游健康 | /api/v1/system/health | 统一 JSON |

## 2. 统一响应契约

### 2.1 成功响应（非 SSE）

```json
{
  "code": 0,
  "message": "success",
  "data": { "..." : "上游 data 字段（网关结构）或完整响应体（非网关结构）" },
  "timestamp": "2026-08-30T08:00:00+00:00"
}
```

### 2.2 错误响应（非 SSE，{detail} 归一化）

```json
{
  "code": 404,
  "message": "知识库不存在: xxx",
  "data": null,
  "timestamp": "2026-08-30T08:00:00+00:00"
}
```

> 提取顺序：`body.code`（非 0）→ `body.detail.error/code`（dict）→ `body.detail`（str）→ `body.error.code` → HTTP 状态码。

### 2.3 SSE 响应（query/stream）

`Content-Type: text/event-stream`，事件原样透传：

```
event: start
data: {"query": "..."}

event: token
data: {"delta": "答案片段"}

event: done
data: {"answer": "完整答案", "sources": [...]}

event: error
data: {"message": "..."}
```

## 3. 端点详细定义

### 3.1 知识库族（1~4）

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT |
| 列表参数 | page: int default 1；page_size: int default 20 |
| 创建请求体 | {name: string（必填，重复 409）, description?, chunk_strategy?, chunk_size? (default 512), chunk_overlap? (default 50)} |
| 成功 data | 上游对象/分页结果 |
| 失败 | 409 名称冲突 / 404 不存在 → 归一化透传 |

### 3.2 文档族（5~7）

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT |
| 上传 | multipart/form-data：file 字段（必填）；`_forward_multipart` 透传；返回 {status: PENDING, document_id} |
| 列表参数 | page/page_size/status_filter |
| 轮询 | GET /documents/{did} → status: PENDING/PROCESSING/COMPLETED/FAILED |
| 失败 | 404 文档/知识库不存在 → 归一化透传 |

### 3.3 查询族（8~10）

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT |
| 查询请求体 | {query: string（必填）, top_k?, filters?, stream?（stream 端点强制 true）} |
| 流式 | POST query/stream → SSE start/token/done 逐事件透传 |
| 检索 | POST query/retrieve → {items: [{chunk_id, content, score, retrieval_channel, ...}], total} |
| 失败 | 404 知识库不存在 / 500 查询失败 → 归一化透传 |

### 3.4 健康（11）

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT |
| 上游 | GET /api/v1/system/health（免鉴权） |
| 成功 data | {status: healthy/degraded/unhealthy, components: {postgresql, qdrant, ...}} |
| 失败 | 上游不可达 → 502 级（SYS_UPSTREAM_ERROR） |

## 4. 错误码表（OpenBase 侧）

| 错误码 | 含义 | HTTP | 场景 |
|--------|------|:---:|------|
| AUTH_UNAUTHORIZED | 未认证 | 401 | 无/无效 OpenBase JWT |
| SYS_UPSTREAM_ERROR | 上游不可达 | 502 | OpenRAG 连接失败/超时 |
| PARAM_INVALID | 参数缺失 | 422 | query/name/file 必填缺失 |

> 上游错误（409/404/500 + {detail}）归一化后透传 code/message，不映射为 OpenBase 错误码表。

## 5. 契约对齐记录（前后端）

| 检查项 | 结果 |
|--------|------|
| 前端页面 ↔ 后端 API | 知识库管理页 → 端点 1~7 + 11；RAG 对话页 → 端点 8~10 |
| 统一响应解析 | 前端 http.ts 已有统一响应处理，rag-proxy 响应兼容 |
| SSE 消费 | parseSseStream 扩展事件类型（start/token/done/error） |
| 鉴权 | 全部端点 OpenBase JWT，前端走既有 auth store |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | SA-OpenBase-Dev | 初始创建：rag-proxy 11 端点契约（统一响应/{detail} 归一化/SSE 透传/文档异步）+ 前后端契约对齐记录 |

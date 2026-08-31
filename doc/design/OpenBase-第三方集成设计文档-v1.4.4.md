# OpenBase 第三方集成设计文档 - v1.4.4

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

## 1. 集成对象与契约基线

| 项 | 内容 |
|----|------|
| 集成系统 | OpenRAG v1.8.0（`D:\Trae CN\myproject\Dev\OpenRAG`，独立部署，端口 8010） |
| 集成通道 | OpenRAG HTTP API（`/api/v1/*` 标准路由；**规避 v1.3 双前缀路由 /api/v1/api/v1/***） |
| 前置核验 | 后端代码核验（src/openrag/main.py + api/routes/*）：无认证、端点清单、双错误格式、SSE 事件、健康检查 |

## 2. 认证边界设计

| 项 | 内容 |
|----|------|
| OpenRAG 现状 | HTTP API **无认证**（无 JWT/API Key/登录端点；仅 MCP 通道有 Bearer Token） |
| OpenBase 侧 | rag-proxy 全部端点 OpenBase JWT 门禁（get_current_user，未认证 401）= **唯一认证入口** |
| 上游注入 | 无（不注入任何认证头，与 OpenLLM API Key Bearer 注入形成差异） |
| OpenRAG 侧补强 | 登记任务书 M1（认证体系落地），后续独立会话实施 |
| 部署约束 | OpenRAG 8010 仅本机/内网访问（公网只能经 rag-proxy） |

## 3. 端点映射设计（rag-proxy ↔ OpenRAG）

| OpenBase rag-proxy 端点 | 上游 OpenRAG 端点 | 说明 |
|--------------------------|--------------------|------|
| GET /api/v1/rag-proxy/collections | GET /api/v1/collections?page=&page_size= | 知识库列表（分页） |
| POST /api/v1/rag-proxy/collections | POST /api/v1/collections | 创建知识库（name 重复 409） |
| GET /api/v1/rag-proxy/collections/{id} | GET /api/v1/collections/{id} | 知识库详情 |
| DELETE /api/v1/rag-proxy/collections/{id} | DELETE /api/v1/collections/{id} | 删除知识库（含向量） |
| POST /api/v1/rag-proxy/collections/{cid}/documents | POST /api/v1/collections/{cid}/documents | 文档上传（multipart，异步 PENDING） |
| GET /api/v1/rag-proxy/collections/{cid}/documents | GET /api/v1/collections/{cid}/documents | 文档列表（status_filter） |
| DELETE /api/v1/rag-proxy/collections/{cid}/documents/{did} | DELETE /api/v1/collections/{cid}/documents/{did} | 删除文档（含分块向量） |
| POST /api/v1/rag-proxy/collections/{cid}/query | POST /api/v1/collections/{cid}/query | RAG 查询（检索+生成） |
| POST /api/v1/rag-proxy/collections/{cid}/query/stream | POST /api/v1/collections/{cid}/query/stream | RAG 流式（SSE start/token/done） |
| POST /api/v1/rag-proxy/collections/{cid}/query/retrieve | POST /api/v1/collections/{cid}/query/retrieve | 纯检索（items 数组） |
| GET /api/v1/rag-proxy/health | GET /api/v1/system/health | 健康透传（PG+Qdrant） |

## 4. 响应与错误归一化设计

### 4.1 统一响应适配（非 SSE 端点）

| 上游状态 | OpenBase 响应 |
|----------|---------------|
| 2xx（{code:0,message,data}） | {code:0, message:"success", data:<上游 data>, timestamp} |
| 2xx（非网关结构，直接对象） | {code:0, message:"success", data:<上游 body>, timestamp} |
| 4xx/5xx（{code,message,data} 业务错误） | {code:<上游 code>, message, data:null, timestamp} |
| 4xx/5xx（{detail: "xxx"} 或 {detail:{...}}） | {code:<提取>，message:<detail>, data:null, timestamp} |
| 网络不可达 | BaseError(SYS_UPSTREAM_ERROR) → 502 |

### 4.2 错误归一化提取顺序

```
body.code（非 0）→ body.detail.error/code（dict）→ body.detail（str）→ body.error.code → HTTP 状态码
```

### 4.3 SSE 事件透传（query/stream）

```
上游事件序列：
  event: start     ← 检索开始（data 含 query 信息）
  event: token     ← 生成 token（重复 N 次）
  event: done      ← 结束（data 含完整结果）
  异常 event: error ← 错误
proxy 行为：httpx AsyncClient stream 逐事件读取 → StreamingResponse 逐事件写回
（Content-Type: text/event-stream；不缓冲；不包装；保序）
```

## 5. 文档上传异步设计（关键流程）

| 步骤 | 说明 |
|------|------|
| 1 | 前端 POST rag-proxy/collections/{cid}/documents（multipart file） |
| 2 | proxy `_forward_multipart` 透传文件 → OpenRAG 后台异步任务（解析→分块→向量化） |
| 3 | 上游返回 {status: PENDING, document_id}（sha256 去重） |
| 4 | 前端轮询 GET rag-proxy/collections/{cid}/documents/{did}（间隔 ~2s） |
| 5 | status: PROCESSING → COMPLETED（chunks 生成）或 FAILED（解析/向量化错误） |

## 6. 配置设计

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `rag_upstream_base` | `http://127.0.0.1:8010` | OpenRAG 上游基地址（8010 端口） |
| `rag_upstream_timeout` | `20.0` | 非流式请求超时（秒） |
| `rag_stream_timeout` | `120.0` | SSE 流式读超时（秒） |
| `rag_document_poll_interval` | `2.0` | 文档轮询间隔（秒，前端侧常量） |

## 7. 依赖与版本兼容

| 依赖 | 版本 | 说明 |
|------|------|------|
| OpenRAG 后端 | v1.8.0 | 对接基线（无认证/端点/错误/SSE 契约以上表为准） |
| httpx | 既有（llm_proxy 已用） | 转发客户端 + stream 模式 |
| fastapi StreamingResponse | 既有 | SSE 响应载体 |
| OpenBase settings | v1.4.3 基线 | 新增 rag_* 配置块 |

## 8. 风险与开放问题

| 项 | 级别 | 缓解 |
|----|:---:|------|
| OpenRAG 无认证（公网暴露风险） | P1 | rag-proxy JWT 门禁 + 部署约束（8010 仅内网） |
| 文档解析/向量化依赖模型可用性 | P2 | 联调确认 embedding/LLM 配置；失败态前端提示（OQ-144-2） |
| 错误格式漂移 | P2 | 归一化提取顺序文档化 + 联调验证 |
| v1.3 双前缀路由 | P2 | 规避（仅用 /api/v1 标准路由） |
| OpenRAG 认证落地方式 | P2 | 任务书 M1 登记（OQ-144-1） |

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | SA-OpenBase-Dev | 初始创建：OpenRAG v1.8.0 认证边界（无上游认证）、端点映射（11 端点）、错误归一化与 SSE 透传、文档异步设计、配置、风险 |

# OpenBase API 接口设计文档 - v1.4.3

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.3 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | SA-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/design/ |

---

## 1. 接口总览

本版本新增 OpenBase 侧 `llm-proxy` 路由族（前缀 `/api/v1/llm-proxy`），全部端点要求 **OpenBase JWT 认证**（`get_current_user`，未认证 401）。proxy 内层注入 OpenLLM 认证（主通道 `Authorization: Bearer <llm_api_key>`）。

| # | 方法 | 路径 | 说明 | 上游 | 响应类型 |
|---|------|------|------|------|---------|
| 1 | GET | /api/v1/llm-proxy/models | 模型列表 | /openllm/v1/models | 统一 JSON |
| 2 | GET | /api/v1/llm-proxy/models/{model_id} | 模型详情 | /api/v1/providers/models/{model_id} | 统一 JSON |
| 3 | POST | /api/v1/llm-proxy/chat | 对话（非流式） | /openllm/v1/chat | 统一 JSON |
| 4 | POST | /api/v1/llm-proxy/chat/stream | 对话流式 | /openllm/v1/chat/stream | SSE 逐事件 |
| 5 | GET | /api/v1/llm-proxy/health | 上游健康 | /openllm/v1/health | 统一 JSON |
| 6 | GET | /api/v1/llm-proxy/conversations | 会话列表 | /api/v1/conversations | 统一 JSON |
| 7 | POST | /api/v1/llm-proxy/conversations | 新建会话 | /api/v1/conversations | 统一 JSON |
| 8 | GET | /api/v1/llm-proxy/conversations/{id} | 会话详情 | /api/v1/conversations/{id} | 统一 JSON |
| 9 | DELETE | /api/v1/llm-proxy/conversations/{id} | 软删除会话 | /api/v1/conversations/{id} | 统一 JSON |
| 10 | POST | /api/v1/llm-proxy/conversations/{id}/archive | 归档/取消归档 | /api/v1/conversations/{id}/archive | 统一 JSON |
| 11 | POST | /api/v1/llm-proxy/conversations/{id}/messages | 追加消息 | /api/v1/conversations/{id}/messages | 统一 JSON |
| 12 | GET | /api/v1/llm-proxy/conversations/{id}/messages | 消息列表 | /api/v1/conversations/{id}/messages | 统一 JSON |

## 2. 统一响应契约

### 2.1 成功响应（非 SSE）

```json
{
  "code": 0,
  "message": "success",
  "data": { "...": "上游响应体" },
  "timestamp": "2026-08-30T08:00:00+00:00"
}
```

### 2.2 错误响应（非 SSE）

```json
{
  "code": 1001,
  "message": "authentication failed",
  "data": null,
  "timestamp": "2026-08-30T08:00:00+00:00"
}
```

`data` 仅在透传 `retry_after` 时非空：`{"retry_after": 30}`。

### 2.3 SSE 响应（/chat/stream）

`Content-Type: text/event-stream`，事件原样透传（无包装）：

```
event: routing
data: {"model": "qwen2.5-7b", "components": ["llm"]}

event: chunk
data: {"delta": "你好"}

event: done
data: {"usage": {"total_tokens": 120}}
```

## 3. 端点详细定义

### 3.1 GET /api/v1/llm-proxy/models

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT（Bearer） |
| 请求参数 | 无 |
| 上游 | GET /openllm/v1/models（注入 Authorization: Bearer sk-openllm-...） |
| 成功 data | `{"models": [{"id": "...", "object": "model", "created": 0, "owned_by": "..."}]}`（上游原样） |
| 失败 | 1001→401 / 1003→429 / 5001→500 透传 |

### 3.2 GET /api/v1/llm-proxy/models/{model_id}

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT |
| 路径参数 | model_id: string（必填） |
| 上游 | GET /api/v1/providers/models/{model_id}（JWT 通道 → 本版本由 llm_api_key 通道评估，或降级返回网关模型列表过滤） |
| 成功 data | 模型对象（上游 Pydantic 直出，proxy 适配进 data） |
| 失败 | 2001→404 透传 |

### 3.3 POST /api/v1/llm-proxy/chat

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT |
| 请求体 | `{model: string, messages: [{role, content}], stream?: false, ...OpenLLM 网关参数}`（透传校验 model/messages 必填） |
| 上游 | POST /openllm/v1/chat（API Key 注入） |
| 成功 data | OpenLLM 网关响应体（choices/usage 等） |
| 失败 | 4001~4005→400 / 1004→404 / 1003→429 / 5001→500 透传 |

### 3.4 POST /api/v1/llm-proxy/chat/stream（SSE）

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT |
| 请求体 | `{model: string, messages: [{role, content}], stream: true}` |
| 上游 | POST /openllm/v1/chat/stream（API Key 注入） |
| 响应 | SSE 逐事件透传（routing → chunk×N → done），Content-Type: text/event-stream |
| 失败 | 连接期 4xx 返回统一 JSON 错误；流中断 → 连接关闭 |

### 3.5 GET /api/v1/llm-proxy/health

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT |
| 上游 | GET /openllm/v1/health（免鉴权） |
| 成功 data | `{"status": "...", "version": "...", "components": {...}}` |
| 失败 | 上游不可达 → 502 级（code=SYS_UPSTREAM_ERROR 语义） |

### 3.6 会话端点族（6~12）

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT |
| 上游 | /api/v1/conversations*（**JWT 通道**，见第三方集成设计 §3 风险与降级） |
| 查询参数（列表） | status: optional；skip: int default 0；limit: int default 20（≤100） |
| 请求体（新建） | `{title?: string, model?: string, system_prompt?: string, ...}` |
| 成功 data | 上游对象（会话/消息数组） |
| 失败 | 401/404/500 透传；通道阻塞时按降级方案处理 |

## 4. 错误码表（OpenBase 侧）

| 错误码 | 含义 | HTTP | 场景 |
|--------|------|:---:|------|
| AUTH_UNAUTHORIZED | 未认证 | 401 | 无/无效 OpenBase JWT |
| AUTH_TOKEN_INVALID | Token 无效 | 401 | JWT 解析失败 |
| SYS_UPSTREAM_ERROR | 上游不可达 | 502 | OpenLLM 连接失败/超时 |
| PARAM_INVALID | 参数缺失 | 422 | model/messages 必填缺失 |

> 上游 OpenLLM 错误码（1001/1003/1004/2001/5001/4001~4005）原样透传至响应 code 字段，不映射为 OpenBase 错误码表（保持上游语义）。

## 5. 契约对齐记录（前后端）

| 检查项 | 结果 |
|--------|------|
| 前端页面 ↔ 后端 API | 模型管理页 → 端点 1/2；对话管理页 → 端点 6~12 + 3/4 |
| 统一响应解析 | 前端 http.ts 已有统一响应处理（code/message/data），llm-proxy 响应兼容 |
| SSE 消费 | 前端 fetch-stream/EventSource 解析 event: routing/chunk/done，需新增解析封装 |
| 鉴权 | 全部端点 OpenBase JWT，前端走既有 auth store |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | SA-OpenBase-Dev | 初始创建：llm-proxy 12 端点契约（统一响应/错误码/SSE 透传/会话降级）+ 前后端契约对齐记录 |

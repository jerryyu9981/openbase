# OpenBase 第三方集成设计文档 - v1.4.3

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

## 1. 集成对象与契约基线

| 项 | 内容 |
|----|------|
| 集成系统 | OpenLLM v2.13.0（`D:\Trae CN\myproject\Dev\OpenLLM`，独立部署，端口 8001） |
| 集成通道 | OpenLLM 统一网关 `/openllm/v1/*`（推荐通道）+ 业务 API `/api/v1/*`（会话等） |
| 前置核验 | 后端代码核验（backend/app/api/*）：认证双通道、统一网关响应、SSE 事件、健康检查、错误码体系 |

## 2. 认证适配设计

### 2.1 OpenLLM 认证契约（事实）

| 通道 | 端点 | 机制 | 契约要点 |
|------|------|------|----------|
| JWT | POST /api/v1/auth/login | HS256，SECRET_KEY env，Access 15min | payload `{sub: user.id, role, exp, type:"access"}` |
| API Key | - | `sk-openllm-` 前缀 + 32 hex；**仅 `Authorization: Bearer` 传递（不支持 X-API-Key 头）** | sha256(key) 比对 key_hash + is_valid() 校验 |
| 统一网关 | /openllm/v1/* | 双通道：token 以 `sk-openllm-` 开头走 API Key，否则 JWT | 失败统一 `401 + {code:1001,...}` |

### 2.2 OpenBase 侧适配方案（本版本）

| 项 | 方案 |
|----|------|
| 主通道 | OpenBase 持有服务级 API Key → proxy 注入 `Authorization: Bearer <llm_api_key>` |
| Key 来源 | 联调前在 OpenLLM 创建（`POST /api/v1/auth/api-keys`）或复用已有；配置于 OpenBase `.env` |
| 身份头 | OpenLLM 主平台 API 不读 X-Org-ID/X-User-ID（EdgeRouter 层约定），本版本不注入额外身份头（用户级鉴权受限 → TD-新增-010） |
| JWT 共享 | 不实现（P2 评估，见 ADR-143-02） |

## 3. 端点映射设计（llm-proxy ↔ OpenLLM）

| OpenBase llm-proxy 端点 | 上游 OpenLLM 端点 | 说明 |
|--------------------------|--------------------|------|
| GET /api/v1/llm-proxy/models | GET /openllm/v1/models | 模型列表（统一响应 {code:0,message,data:{models:[...]}}） |
| GET /api/v1/llm-proxy/models/{model_id} | GET /api/v1/providers/models/{model_id} | 模型详情（上游 Pydantic 直出，proxy 适配 data 字段） |
| POST /api/v1/llm-proxy/chat | POST /openllm/v1/chat | 对话聚合端点（mode/model/messages，非流式） |
| POST /api/v1/llm-proxy/chat/stream | POST /openllm/v1/chat/stream | 对话流式（SSE 逐事件透传） |
| GET /api/v1/llm-proxy/health | GET /openllm/v1/health | 网关健康（免鉴权上游，proxy 侧仍要求 OpenBase JWT） |
| GET /api/v1/llm-proxy/conversations | GET /api/v1/conversations?status=&skip=&limit= | 会话列表（JWT 通道，proxy 注入 API Key 注意：该端点需 JWT 鉴权） |
| POST /api/v1/llm-proxy/conversations | POST /api/v1/conversations | 新建会话 |
| GET /api/v1/llm-proxy/conversations/{id} | GET /api/v1/conversations/{id} | 会话详情 |
| DELETE /api/v1/llm-proxy/conversations/{id} | DELETE /api/v1/conversations/{id} | 软删除会话 |
| POST /api/v1/llm-proxy/conversations/{id}/archive | POST /api/v1/conversations/{id}/archive | 归档/取消归档 |
| POST /api/v1/llm-proxy/conversations/{id}/messages | POST /api/v1/conversations/{id}/messages | 追加消息 |
| GET /api/v1/llm-proxy/conversations/{id}/messages | GET /api/v1/conversations/{id}/messages | 消息列表 |

> **认证通道差异处理（重要）**：模型/对话/健康端点走统一网关 `/openllm/v1/*`（API Key 通道可用）；**会话端点 `/api/v1/conversations*` 为 JWT 通道**（依赖 get_current_active_user）。本版本策略：
> - 优先评估：会话端点经 OpenLLM 平台 JWT 通道访问——需 OpenBase 持有 OpenLLM 平台用户凭据（登录换取 access_token，15min 过期需刷新），复杂度高；
> - 备选：会话端点改用 OpenLLM 开放的其他通道或本版本**会话页以 OpenLLM API Key 可访问的通道降级实现**（如聊天记录查询走统一网关能力）；
> - 联调确认后定稿；若 JWT 通道阻塞，会话管理页降级为「模型列表 + 对话发起（统一网关）」，会话历史展示缺口登记任务书（BL-143-06）。

## 4. 响应与错误码适配设计

### 4.1 统一响应适配（非 SSE 端点）

| 上游状态 | OpenBase 响应 |
|----------|---------------|
| 2xx | `{code:0, message:"success", data:<上游响应体>, timestamp}` |
| 4xx/5xx | `{code:<上游错误码>, message:<上游 message>, data:{retry_after?}, timestamp}` |
| 网络不可达 | BaseError(SYS_UPSTREAM_ERROR) → 502 级 |

### 4.2 错误码透传映射

| OpenLLM 网关错误码 | 含义 | HTTP 映射 | OpenBase 透传 |
|--------------------|------|:---:|---------------|
| 1001 | 未认证/Token 失效 | 401 | code=1001 |
| 1003 | 限流超限 | 429 | code=1003，透传 retry_after |
| 1004 | 无可用模型 | 404 | code=1004 |
| 2001 | 资源不存在 | 404 | code=2001 |
| 5001 | 内部错误 | 500 | code=5001 |

提取顺序（对标 memory_proxy）：`body.error` > `body.code` > `detail.error/code/status` > HTTP 状态码。

### 4.3 SSE 事件透传（/chat/stream）

```
上游事件序列：
  event: routing     ← 路由决策（组件选择）
  event: chunk       ← 内容增量（重复 N 次，data 为 delta）
  event: done        ← 结束（data 含 usage/成本）
proxy 行为：httpx AsyncClient stream 逐事件读取 → StreamingResponse 逐事件写回
（Content-Type: text/event-stream；不缓冲；不包装；保序）
异常：上游断开 → 透传关闭 + 日志 WARN（含已发送事件数）；不重放
```

## 5. 配置设计

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `llm_api_key` | 空（.env 必填） | OpenLLM 服务 API Key（sk-openllm- 前缀） |
| `llm_upstream_base` | `http://127.0.0.1:8001` | OpenLLM 统一网关基地址 |
| `llm_upstream_timeout` | `20.0` | 非流式请求超时（秒） |
| `llm_stream_timeout` | `120.0` | SSE 流式读超时（秒），与连接超时分离 |
| `llm_jwt_username/password` | 空（可选） | 会话端点 JWT 通道备用凭据（联调确认后启用，P2） |

## 6. 依赖与版本兼容

| 依赖 | 版本 | 说明 |
|------|------|------|
| OpenLLM 后端 | v2.13.0 | 对接基线，认证/端点/响应契约以上表为准 |
| httpx | 既有（memory_proxy 已用） | 转发客户端，新增 stream 模式使用 |
| fastapi StreamingResponse | 既有 | SSE 响应载体 |
| OpenBase settings | v1.4.2 基线 | 新增 llm_* 配置块 |

## 7. 风险与开放问题

| 项 | 级别 | 缓解 |
|----|:---:|------|
| 会话端点 JWT 通道阻塞 | P1 | 降级方案（模型列表 + 对话发起 + 缺口登记任务书）；联调前置验证 |
| OpenLLM 模型写操作能力差异 | P2 | 写操作降级/禁用，登记任务书 |
| API Key 单通道用户级鉴权受限 | P2 | 已归集 TD-新增-010 |
| SSE 事件格式版本漂移 | P2 | 联调专项验证 routing/chunk/done；格式变化登记任务书 |

## 8. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | SA-OpenBase-Dev | 初始创建：OpenLLM v2.13.0 认证适配（API Key 主通道）、端点映射（统一网关 + 会话 API）、响应/错误码/SSE 适配、配置设计、会话端点 JWT 通道风险与降级方案 |

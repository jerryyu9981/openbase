# OpenBase 非功能设计说明 - v1.4.3

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

## 1. 性能设计

| 项 | 目标 | 设计措施 |
|----|------|----------|
| llm-proxy 非流式转发 | P95 ≤ 500ms（不含 OpenLLM 处理） | httpx AsyncClient 连接复用；无中间聚合/重编码；超时 llm_upstream_timeout=20s |
| 模型列表 | P95 ≤ 300ms | 直接透传 /openllm/v1/models；不做本地缓存（本版本数据量小，后续按需加 cache） |
| SSE 首包 | P95 ≤ 1s | 逐事件转发不缓冲；stream 读超时分离（llm_stream_timeout=120s） |
| 并发 | 支持 50 并发 proxy 请求 | 每请求独立 AsyncClient（对标 memory_proxy，无共享状态竞争） |

## 2. 安全设计

| 项 | 方案 |
|----|------|
| 认证 | OpenBase JWT 唯一前端入口；proxy 内层注入 OpenLLM API Key；未认证 401 |
| 密钥 | llm_api_key 仅 settings/.env；.env* 排除 git；不落日志/前端 bundle；日志禁止记录 Authorization 头完整值 |
| 授权 | 本版本 proxy 端点沿用登录用户可访问（无新增细粒度权限点）；OpenLLM 侧用户级鉴权受限 → TD-新增-010 |
| 输入校验 | Pydantic schema：chat/chat-stream 校验 model/messages 必填；conversations 列表参数校验（skip ≥0、limit ≤100） |
| 审计 | proxy 关键操作审计（user_id/端点/HTTP 状态），复用 audit 中间件；SSE 会话记录 request_id |
| 注入防护 | 转发参数经 schema 约束后传递，不透传原始请求体中的控制字段（上游路径不可由调用方拼接） |
| 限流 | OpenLLM 侧 1003 限流错误透传（retry_after），OpenBase 侧沿用既有限流框架（如有） |

## 3. 可观测性设计（对照 observability-standards 4 条标准）

| 标准 | 落实 |
|------|------|
| 结构化日志 | llm_proxy 日志含 service="openbase"、module="llm_proxy"、path、upstream_status、duration_ms；JSON 格式沿用 observability 模块；禁止密钥/完整请求体 |
| 14 种关键指标 | 复用既有 http_requests_total / http_request_duration_seconds（path 标签 llm-proxy）；新增 llm_proxy_upstream_errors_total（上游错误计数） |
| OTLP 追踪 | 转发请求尽量透传 traceparent（上游 OpenLLM 支持 OTel 时）；SSE 会话以 request_id 关联日志 |
| Dashboard | 网关服务视图（gateway/services）已含 openllm 实例健康；本版本在监控可读范围内补充 llm-proxy 错误统计展示（联调期按需） |

## 4. 兼容性设计

| 项 | 方案 |
|----|------|
| 既有 OpenMemory proxy | 不受影响（独立模块 llm_proxy，不触碰 memory_proxy 路由） |
| 网关服务发现 | openllm 循环探测沿用，不改造发现机制（仅新增业务转发） |
| 前端 | 2 页改造不改变路由/菜单结构；其他 OpenLLM 页面保持现状 |
| OpenLLM 契约 | SSE 事件格式以 /openllm/v1/chat/stream（routing/chunk/done）为基线；上游变更登记任务书 |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | SA-OpenBase-Dev | 初始创建：性能（P95/SSE 首包/并发）、安全（认证/密钥/审计）、可观测性（日志/指标/追踪/Dashboard）、兼容性（OpenMemory proxy/网关/前端） |

# OpenBase 非功能设计说明 - v1.4.4

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

## 1. 性能设计

| 项 | 目标 | 设计措施 |
|----|------|----------|
| rag-proxy 非流式转发 | P95 ≤ 500ms（不含 OpenRAG 处理） | httpx AsyncClient 连接复用；超时 rag_upstream_timeout=20s |
| 知识库列表 | P95 ≤ 300ms | 直接透传；不做本地缓存（数据量小） |
| SSE 首包（start） | P95 ≤ 1s | 逐事件转发不缓冲；stream 读超时分离（rag_stream_timeout=120s） |
| 文档上传 | 上传响应 ≤2s（异步处理在 OpenRAG 侧） | multipart 直传；状态轮询 2s 间隔 |
| 并发 | 支持 50 并发 proxy 请求 | 每请求独立 AsyncClient（对标 llm_proxy） |

## 2. 安全设计

| 项 | 方案 |
|----|------|
| 认证 | OpenBase JWT 唯一入口（rag-proxy 未认证 401）；无上游认证注入 |
| 网络边界 | OpenRAG 8010 仅本机/内网（部署约束）；公网只能经 rag-proxy |
| 输入校验 | Pydantic schema（query/name 必填；文件大小/类型透传上游规则） |
| 审计 | proxy 关键操作审计（user_id/端点/HTTP 状态）；不记录 Authorization 完整值 |
| 错误处理 | BaseError（AUTH_/SYS_ 前缀）；{detail} 归一化透传 |
| 密钥 | 无上游密钥（OpenRAG 无认证）；.env* 排除 git（沿用） |

## 3. 可观测性设计（对照 observability-standards 4 条标准）

| 标准 | 落实 |
|------|------|
| 结构化日志 | rag_proxy 日志含 service/module="rag_proxy"/path/upstream_status/duration_ms；JSON 格式沿用 |
| 14 种关键指标 | 复用 http_requests_total / http_request_duration_seconds（path 标签 rag-proxy） |
| OTLP 追踪 | 转发请求透传 traceparent（上游 OpenRAG 支持时）；SSE 会话 request_id 关联 |
| Dashboard | 网关服务视图（含 rag 实例健康）；llm-proxy 既有展示不动 |

## 4. 兼容性设计

| 项 | 方案 |
|----|------|
| 既有 llm_proxy / memory_proxy | 不受影响（独立模块 rag_proxy，路由不冲突） |
| 网关服务发现 | rag 服务循环探测沿用（不改造发现机制） |
| 前端 | 2 页改造不改变路由/菜单结构；其他 OpenRAG 页面保持现状 |
| OpenRAG 契约 | 错误归一化 + SSE 事件以 /api/v1 标准路由为基线；v1.3 双前缀规避 |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | SA-OpenBase-Dev | 初始创建：性能（P95/SSE 首包/文档异步）、安全（JWT 唯一入口/网络边界）、可观测性、兼容性 |

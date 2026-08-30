# OpenBase 系统架构设计文档 - v1.4.3

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

## 1. 设计目标与范围

| 项 | 内容 |
|----|------|
| 设计范围 | FR-143-01~09（OpenLLM 服务接入 + 认证适配 + llm-proxy 转发 + 前端 2 页真实化 + 联调收尾） |
| 前置验证 | OpenLLM v2.13.0 实际代码核验通过：`PORT` env 可覆盖默认 8000；认证双通道（JWT `/api/v1/auth/login` HS256/SECRET_KEY + API Key `sk-openllm-` 仅 `Authorization: Bearer`）；统一网关 `/openllm/v1/*` 响应 `{code,message,data,request_id}`；SSE 事件 `routing→chunk→done`；健康检查 `/health`、`/openllm/v1/health`；网关错误码 1001/1003/1004/2001/5001 |
| 约束 | 分层架构（Controller/Service/Repository）、错误码统一 BaseError、SQLAlchemy 参数化、结构化日志、向后兼容既有端点（OpenMemory proxy / 网关服务发现 / 既有前端页） |

## 2. 系统架构

### 2.1 总体架构（v1.4.3 目标态）

```
统一前端（OpenBase frontend，Vue3）
  │  OpenBase JWT（get_current_user）
  ▼
OpenBase 后端（FastAPI，:8000）
  ├─ auth 模块：登录/签发 JWT（既有，含 sub/org_id/role）
  ├─ gateway 模块：服务发现骨架（openllm 循环探测，既有）
  ├─ proxy 模块：/api/v1/memory-proxy/*（既有，OpenMemory 8020）
  ├─ llm_proxy 模块：/api/v1/llm-proxy/*（v1.4.3 新增）◀── 本版本核心
  │     ├─ 认证注入：Authorization: Bearer <llm_api_key>（OpenBase 持有）
  │     ├─ 统一响应：{code,message,data,timestamp}（非 SSE 端点）
  │     ├─ 错误透传：1001→401 / 1003→429 / 1004→404 / 2001→404 / 5001→500
  │     └─ SSE 透传：routing→chunk→done 逐事件转发（流式端点）
  │
  │  http://127.0.0.1:8001（llm_upstream_base）
  ▼
OpenLLM 后端（FastAPI，:8001，独立部署，v2.13.0）
  ├─ 统一网关 /openllm/v1/*（双通道鉴权：API Key 或 JWT）
  │     ├─ GET  /openllm/v1/models          （模型列表）
  │     ├─ POST /openllm/v1/chat            （聚合对话，非流式）
  │     ├─ POST /openllm/v1/chat/stream     （对话流式 SSE）
  │     └─ GET  /openllm/v1/health          （网关健康）
  ├─ 业务 API /api/v1/*
  │     ├─ GET  /api/v1/providers/models/{model_id}（模型详情）
  │     └─ /api/v1/conversations*（会话 CRUD，对话管理页）
  └─ 基础设施：PostgreSQL / Redis / ClickHouse（OpenLLM 自持）
```

### 2.2 模块挂载设计

| 项 | 内容 |
|----|------|
| 新增模块 | `openbase/modules/llm_proxy/`（包，`__init__.py` 导出 `router`，前缀 `/api/v1/llm-proxy`，tags=["llm-proxy"]） |
| 启用方式 | `demo_app.py` enable_module 列表追加 `"llm_proxy"`（`init_app` 自动 import + include_router，见 `openbase/__init__.py` 装配循环） |
| 配置项 | `settings.py` 新增 `llm_api_key` / `llm_upstream_base`（默认 `http://127.0.0.1:8001`）/ `llm_upstream_timeout`（默认 20.0），对标既有 `memory_*` 配置块 |
| 结构 | 对标 `memory_proxy.py` 三函数拆分：`_extract_identity`（OpenBase JWT 校验）/ `_build_upstream_headers`（Bearer 注入）/ `_forward` + `_adapt_response`（转发 + 统一响应），新增 `_forward_sse`（流式透传） |

## 3. 关键架构决策（ADR）

### ADR-143-01 llm-proxy 模块设计（独立模块 vs 扩展既有 proxy）

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | 新建独立模块 `openbase/modules/llm_proxy/`（路由前缀 `/api/v1/llm-proxy`），不并入既有 `proxy` 模块（该模块承载 OpenMemory memory-proxy 与通用 /api/v1/proxy/{system}/{path} 通道） |
| 理由 | ① 路由前缀独立（llm-proxy vs memory-proxy）避免鉴权/转发逻辑耦合；② OpenLLM 认证契约（Bearer sk-openllm-）与 OpenMemory（X-API-Key + JWT）不同，独立模块便于按契约演进；③ 模块启停独立（enable_module），不影响既有 proxy 回归 |
| 备选 | A. 扩展通用 /api/v1/proxy/{system}/{path} → 否决：通用通道无法承载 SSE 流式透传与统一响应适配的专用逻辑，且与既有前端调用约定耦合；B. 并入 memory_proxy.py → 否决：跨系统契约混淆，违反单一职责 |
| 风险 | 模块数量增加 → 注册清单维护成本，随版本演进可控（demo_app enable_module 列表显式管理） |

### ADR-143-02 认证通道决策（API Key 单通道 vs JWT 共享签发）

| 项 | 内容 |
|----|------|
| 状态 | 已接受（主通道 API Key；JWT 共享登记 P2） |
| 决策 | OpenBase 持有 OpenLLM 服务级 API Key（`sk-openllm-` 前缀），proxy 转发时注入 `Authorization: Bearer <llm_api_key>`。JWT 共享签发（共享 SECRET_KEY + 用户映射）仅调研登记（OQ-143-1 → TD-新增-010），本版本不实现 |
| 理由 | ① OpenLLM 统一网关 `/openllm/v1/*` 支持 API Key 通道且响应统一；② OpenLLM 平台 JWT 的 sub=OpenLLM user.id，与 OpenBase 用户体系无映射，共享签发需用户同步机制（复杂度高）；③ API Key 单通道可满足本版本"模型列表/对话真实闭环"验收目标 |
| 备选 | JWT 共享签发（共享 SECRET_KEY，OpenBase 代签 OpenLLM 格式 JWT）→ 延后：需用户映射表/同步机制，且 OpenLLM 平台 JWT 15 分钟过期需刷新链路，复杂度超出本版本范围；风险登记 TD-新增-010 |
| 风险 | 用户级鉴权深度受限（无法按 OpenBase 用户区分 OpenLLM 侧权限/用量归属）→ 已登记 TD-新增-010，后续对接线版本评估；Key 泄露 → .env 管理 + 不落日志/前端 |

### ADR-143-03 SSE 流式透传方案

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | 对话流式端点（`POST /api/v1/llm-proxy/chat/stream`）采用逐事件透传：proxy 以 httpx.AsyncClient stream 方式读取上游 SSE（`event: routing` → `event: chunk` ×N → `event: done`），逐事件写回下游 `StreamingResponse(media_type="text/event-stream")`，不缓冲、不包装、不二次编码 |
| 理由 | ① 上游事件语义（routing/chunk/done）需原样透传供前端消费；② 统一响应包装会破坏 SSE 协议（无法 {code,message,data} 包裹事件流）；③ 逐事件转发最小化延迟，符合"首包 ≤1s"非功能指标 |
| 备选 | A. 聚合为一次性 JSON → 否决：丧失流式体验，违反 FR-143-04 验收（SSE 事件完整）；B. 服务端缓冲事件后统一返回 → 否决：延迟不可控；C. 前端直连 OpenLLM → 否决：密钥暴露 |
| 风险 | 上游中断 → 透传连接断开 + 记录错误事件，前端重试机制兜底；超时 → llm_upstream_timeout 按流场景放宽（读流超时与连接超时分离） |

### ADR-143-04 前端 2 页真实化方式

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | 直接改造既有 `Models.vue` / `Conversations.vue`（保留页面结构/交互/组件），数据源从本地 mock 切换为调用 OpenBase llm-proxy 真实 API；新增统一 API 层封装（`src/core/api/llm.ts`，走既有 http.ts 网关） |
| 理由 | ① 两页已有完整 UI 骨架（表格/搜索/筛选/对话框），改造成本低于重建；② 走 OpenBase proxy 保证前端不接触密钥（FR-143-04-3）；③ 复用既有 http.ts 鉴权/错误处理链路 |
| 备选 | 重建新页面 → 否决：重复 UI 工作且破坏既有视觉一致性；前端直连 OpenLLM 8001 → 否决：密钥暴露 + CORS + 双认证入口 |
| 风险 | OpenLLM 端模型写操作（新增/编辑/删除）能力差异 → 本版本写操作降级（仅列表/详情 + 新建会话/归档/删除会话按能力适配），缺口登记任务书（BL-143-06） |

## 4. 数据模型设计

**结论：本版本无新增 OpenBase 本地数据表。**

| 数据 | 归属 | 说明 |
|------|------|------|
| OpenLLM 模型/会话数据 | OpenLLM 上游（PG/Redis） | OpenBase 只经 proxy 读写消费，不落本地库 |
| llm_api_key 配置 | OpenBase settings/.env | 配置项（非数据表），`llm_api_key`/`llm_upstream_base`/`llm_upstream_timeout` |
| 审计日志 | OpenBase audit 模块（既有） | proxy 转发关键操作记录审计，沿用既有审计表 |

> 数据库设计不适用说明：无 DDL/迁移/索引设计；既有库表无变更。详见设计评审记录 §不适用项。

## 5. API 设计摘要（详见《OpenBase-API接口设计文档-v1.4.3.md》）

| 方法 | OpenBase 路径 | 上游目标 | 响应 |
|------|---------------|----------|------|
| GET | /api/v1/llm-proxy/models | GET /openllm/v1/models | 统一 {code,message,data,timestamp} |
| GET | /api/v1/llm-proxy/models/{model_id} | GET /api/v1/providers/models/{model_id} | 统一包装（上游 Pydantic 直出 → 适配 data） |
| POST | /api/v1/llm-proxy/chat | POST /openllm/v1/chat | 统一包装 |
| POST | /api/v1/llm-proxy/chat/stream | POST /openllm/v1/chat/stream | SSE 逐事件透传 |
| GET | /api/v1/llm-proxy/health | GET /openllm/v1/health | 统一包装 |
| GET/POST/DELETE | /api/v1/llm-proxy/conversations[/{id}[/messages|/archive]] | /api/v1/conversations* | 统一包装 |

## 6. 安全设计

| 项 | 方案 |
|----|------|
| 认证边界 | OpenBase JWT 唯一前端入口（get_current_user）；proxy 内层注入 OpenLLM API Key；前端永不接触 llm_api_key |
| 密钥管理 | llm_api_key 经 settings/.env 配置；.env* 排除 git（AGENTS.md §6）；不落日志（结构化日志禁止记录 Authorization 头）；不落前端 bundle |
| 输入校验 | proxy 端点入参沿用 Pydantic schema（dict[str, Any] 转发场景校验上层字段）；SSE 端点参数校验（model/messages 必填） |
| 审计 | proxy 转发关键操作记录审计日志（user_id/目标端点/HTTP 状态），复用 audit 中间件 |
| 错误处理 | OpenBase 侧错误统一 BaseError（AUTH_/SYS_ 前缀）；上游错误按网关错误码映射透传 |

## 7. 可观测性

| 项 | 方案 |
|----|------|
| 日志 | llm_proxy 模块结构化日志（logger "openbase.llm_proxy"，extra 字段：path/upstream_status/duration_ms），不记录密钥与完整请求体 |
| 指标 | 复用 observability 模块指标框架：proxy 转发计数/延迟（可挂 http_request_duration_seconds 标签 path=llm-proxy） |
| 追踪 | 转发请求透传 trace 上下文（如有 OTel 启用）；SSE 会话记录 request_id 关联 |
| 排障 | 上游不可达 WARN 日志（含错误摘要）；错误码透传使前端/调用方可定位 |

## 8. 一致性约束（对既有架构）

| 约束 | 落实 |
|------|------|
| 分层架构 | llm-proxy 为 Controller 层（路由 + 转发），无业务逻辑层需求（对接类模块）；不直接操作 DB |
| 错误码 | OpenBase 侧 BaseError（AUTH_UNAUTHORIZED/SYS_UPSTREAM_ERROR 等）；上游错误码透传不改写 |
| 命名 | 模块 snake_case（llm_proxy）；路由 kebab（llm-proxy）；配置 llm_* 前缀与 memory_* 一致 |
| 日志 | logging + extra，禁止 print |
| 并发 | httpx.AsyncClient 每请求独立（对标 memory_proxy），SSE 流式连接超时控制 |

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | SA-OpenBase-Dev | 初始创建：llm_proxy 模块架构（ADR-143-01~04：模块设计/认证通道/SSE 透传/前端改造）、模块挂载、数据模型不适用说明、安全/可观测性/一致性约束 |

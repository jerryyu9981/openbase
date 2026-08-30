# OpenBase-OpenLLM对接完善任务书-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-LLM-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Draft] |
| 日期 | 2026-08-30 |
| 作者 | AD-OpenBase-Dev |
| 版本主题 | OpenLLM 侧对接完善：会话/模型管理 API Key 通道、身份头支持、SSE 格式统一、安全补强 |
| 适用范围 | OpenLLM 项目（D:\Trae CN\myproject\Dev\OpenLLM），由独立会话据此实施 |

> 本任务书供另一个会话专据此完善 OpenLLM。所有修改项均含现状、目标、涉及文件、实现要点、验收标准与验证方法，可直接照单执行。对应 OpenBase 版本 Backlog BL-143-06（P2）。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-08-30 | AD-OpenBase-Dev | 初始版本：梳理 OpenBase（v1.4.3）对接 OpenLLM v2.13.0 仍需完善的 M1~M6 项 |

---

## 1. 背景与目标

OpenBase（v1.4.3）启动 OpenLLM 系统对接（VC-011 对接线第 1 站）：OpenBase 以 llm-proxy 转发访问 OpenLLM 统一网关 `/openllm/v1/*`（模型列表/对话/SSE 流式）与业务 API（模型详情/会话管理），认证采用 **API Key 单通道**（`Authorization: Bearer sk-openllm-`，OpenLLM 不支持 X-API-Key 头）。

对照 OpenLLM v2.13.0 实际代码逐项核验后，OpenLLM 侧仍有 1 处阻塞项（会话端点无 API Key 通道）、2 处能力缺口（模型写操作鉴权、身份头支持）和 3 项建议优化。本任务书定义这些修改的精确方案，目标是把 OpenLLM 打造成与 OpenBase 对接规范完全对齐的生产可用服务。

## 2. 对接现状总览

| 类别 | 状态 | 说明 |
|------|:---:|------|
| 统一网关（/openllm/v1/models、/chat、/chat/stream、/health） | ✅ 已核验可用 | 双通道鉴权（API Key/JWT），统一响应 {code,message,data,request_id}，错误码 1001/1003/1004/2001/5001 |
| API Key 认证（sk-openllm-，Bearer） | ✅ 已核验可用 | 前缀 + 32 hex；sha256 哈希比对 + is_valid() 校验；chat/chat-stream/网关端点可用 |
| API Key 创建（POST /api/v1/auth/api-keys） | ✅ 无需修改 | 任意登录用户可创建（非管理员），返回一次性明文 secret |
| 健康检查（/health、/api/v1/status、/metrics） | ✅ 无需修改 | 生产环境（DEBUG=false）免鉴权可用 |
| 会话管理（/api/v1/conversations*） | ⚠️ 阻塞 | **全部 JWT 鉴权（get_current_active_user），无 API Key 通道**（M1） |
| 模型管理写操作（providers 模型 CRUD） | ⚠️ 待完善 | 写端点需管理员 JWT，且创建/更新/删除路由不统一（M2） |
| 模型详情（GET /api/v1/providers/models/{model_id}） | ⚠️ 待确认 | 路由顺序存在 /providers/models/all 被 /{provider_id}/models 遮蔽隐患（422）（M2 附带） |
| 身份头支持（X-User-ID/X-Org-ID/X-Tenant-ID） | ⚠️ 待完善 | 主平台 API 不读（仅 EdgeRouter 层），用户级审计/租户归属受限（M3） |
| SSE 事件格式 | ⚠️ 待完善 | 三套并存：OpenAI 透传 / SSEEvent token-done / 网关 routing-chunk-done（M4） |
| local_models 鉴权 | ⚠️ 安全缺口 | 全部端点无鉴权（含 SSE 拉流、模型启停/删除）（M5） |
| openapi.json / docs 开放 | ⚠️ 待完善 | DEBUG=false 时 /docs、/openapi.json、/redoc 全部 404（M6） |

## 3. 待完善项详细方案

### M1 会话端点支持 API Key 鉴权（阻塞，P1）

**现状**：`backend/app/api/conversations.py`（前缀 `/conversations` → `/api/v1/conversations`）全部 9 个端点使用 JWT 依赖 `get_current_active_user`（`backend/app/services/auth_service.py` L220），无任何端点支持 API Key。OpenBase 走 API Key 单通道时对话管理页（会话列表/新建/详情/归档/删除/消息）全部不可访问。

**目标**：conversations 端点兼容 API Key 鉴权，对标 chat 系端点（chat.py / chat_stream.py 使用 `get_api_key_user`，auth_service.py L260），使 OpenBase llm-proxy 可经 API Key 访问会话管理。

**涉及文件**：
- `backend/app/api/conversations.py`（修改鉴权依赖）
- `backend/app/services/auth_service.py`（复用现成 get_api_key_user，无需改）
- `backend/app/schemas/conversation.py`（如需在响应中补充 user 归属字段）

**实现要点**：
1. 为 conversations 路由增加**双通道鉴权依赖**：新建 `get_current_user_or_api_key`（或 `get_current_active_user_or_api_key`），逻辑：`Authorization: Bearer <token>` → 若 token 以 `sk-openllm-` 开头走 `get_api_key_user`（返回 API Key 关联用户），否则走 `get_current_active_user`（JWT）。
2. 替换 conversations.py 全部 9 个端点的 `Depends(get_current_active_user)` 为双通道依赖。
3. 身份归属：API Key 通道下 `request.user` 为用户实体（API Key 关联 user_id）；会话创建/列表按当前用户过滤逻辑不变（API Key 关联用户即归属用户）。
4. 参考实现：`backend/app/api/openllm_gateway.py` L737-786 `get_gateway_identity`（双通道分流逻辑已存在，可抽取复用或复制模式）。

**验收标准**：
- 用 API Key（`Authorization: Bearer sk-openllm-xxx`）请求 `GET /api/v1/conversations`、`POST /api/v1/conversations`、`GET/DELETE /api/v1/conversations/{id}`、`POST /{id}/archive`、`GET/POST /{id}/messages` 全部返回 200（非 401）。
- JWT 通道回归：`get_current_active_user` 场景行为不变（既有测试通过）。
- 未认证/无效 Key 仍返回 401。

**验证方法**：`python -m pytest backend/tests`（新增 conversations API Key 用例）；再经 OpenBase proxy `GET /api/v1/llm-proxy/conversations` 验证 200 + 真实会话数据。

---

### M2 模型管理写操作 API Key 通道 + 路由统一（P1/P2）

**现状**：`backend/app/api/providers.py`（前缀 `/providers` → `/api/v1/providers`）写操作（创建/更新/删除模型、创建/更新/删除提供商）均要求管理员 JWT（`get_current_admin_user`，auth_service.py L240），API Key 通道不可用；且模型创建是嵌套路由 `POST /providers/{provider_id}/models`，更新/删除是扁平路由 `PUT/DELETE /providers/models/{model_id}`（路径不统一）。另：`GET /providers/models/all`（L245）定义在动态路由 `/{provider_id}/models`（L174）之后，存在被遮蔽 → `provider_id="models"` 非 UUID → 422 的隐患。

**目标**：模型管理写操作支持 API Key 通道（经 API Key 关联用户校验权限）；修复路由遮蔽隐患；统一模型写操作路径风格（可选）。

**涉及文件**：
- `backend/app/api/providers.py`（鉴权依赖 + 路由顺序）
- `backend/app/services/auth_service.py`（如需新增 `get_admin_user_or_api_key`）

**实现要点**：
1. 写端点（POST/PUT/DELETE 模型与提供商）新增双通道依赖 `get_admin_user_or_api_key`：API Key 通道下校验 API Key 关联用户 `is_admin()`（或按 Key 的 permissions 字段校验 model:write 权限——API Key 模型已有 `permissions` 字段可扩展）。
2. 路由顺序修复：将 `GET /providers/models/all` 与 `GET /providers/models/{model_id}` 静态段注册提前至 `/{provider_id}/models` 之前（对标 main.py L403-406 provider_registration 先注册的处理方式），消除 422 遮蔽。
3. 路径统一（建议）：模型写操作统一为扁平路由 `POST /providers/models`（body 含 provider_id）与 `PUT/DELETE /providers/models/{model_id}`，保留旧嵌套路由兼容（deprecated 标注）。

**验收标准**：
- 用 API Key 创建模型（POST /providers/{id}/models）返回 200/201；更新/删除（PUT/DELETE /providers/models/{id}）生效。
- `GET /api/v1/providers/models/all` 返回 200（遮蔽修复，非 422）。
- JWT 管理员通道回归无变化；非管理员 Key 写操作返回 403。

**验证方法**：`python -m pytest backend/tests/test_supported_models.py backend/tests`（新增写操作用例）；经 OpenBase proxy 创建/编辑/删除模型验证真实落库。

---

### M3 主平台身份头支持（X-User-ID/X-Org-ID，P2，TD-新增-010 偿还路径）

**现状**：主平台 API 无任何中间件基于 X-Org-ID/X-User-ID/X-Tenant-ID 做租户隔离或审计归属（`backend/main.py` L342-377 挂载的 AuditMiddleware/RateLimitMiddleware/MetricsMiddleware 均不读这三个头，唯一例外是 MetricsMiddleware L102 将 X-Tenant-ID 作为指标标签备用值）。OpenBase 对接后，审计日志（audit.py 取 request.state.user_id）无法区分 OpenBase 侧真实调用用户（API Key 通道全部归为 Key 关联用户）。

**目标**：主平台中间件支持从请求头解析身份上下文（X-User-ID/X-Org-ID），供审计归属与（可选）租户隔离，使 OpenBase 用户级审计可用（偿还 TD-新增-010 的路径之一）。

**涉及文件**：
- `backend/app/middleware/audit.py`（审计归属扩展）
- `backend/app/middleware/identity.py`（新增身份上下文中间件，可选）
- `backend/main.py`（中间件注册）

**实现要点**：
1. 新增轻量身份中间件（或扩展 AuditMiddleware）：读取 `X-User-ID` / `X-Org-ID` / `X-Tenant-ID` 头，写入 `request.state.external_user_id` / `request.state.external_org_id`（仅在 API Key 通道下生效，避免覆盖 JWT 身份）。
2. `AuditMiddleware` 审计记录扩展字段：`external_user_id` / `external_org_id`（API Key 调用时记录来源用户，可审计 OpenBase 侧真实用户）。
3. 可选（租户隔离）：敏感端点（如 conversations/providers 列表）在 API Key 通道下按 X-Tenant-ID 过滤数据（若需多租户隔离；当前 OpenBase 单租户场景可先只做审计字段）。

**验收标准**：
- 经 OpenBase proxy（注入 X-User-ID/X-Org-ID）调用会话/模型端点，审计日志中出现 external_user_id 字段且值正确。
- JWT 通道下不覆盖原生身份（request.state.user 优先）。
- 既有审计测试无回归。

**验证方法**：`python -m pytest backend/tests/test_audit_logs_enhanced.py`；联调时经 OpenBase proxy 调用后查审计记录确认字段。

---

### M4 SSE 事件格式统一（P2）

**现状**：7 个 SSE 端点 3 套格式并存：格式 A（OpenAI 透传 `data:`/`data: [DONE]`，chat.py L85/L227）、格式 B（SSEEvent `event: token|done|error|function_call|usage|metadata`，chat_stream.py + `backend/app/services/sse_adapter.py`）、格式 C（网关自定义 `event: routing→chunk→done`，openllm_gateway.py L1753）、格式 D（Ollama 原始 `data:` + `{"status":"done"}`，local_models.py）。OpenBase 以格式 C 为基线可兼容，但客户端需按端点分别适配。

**目标**：统一 SSE 事件格式（以格式 C `routing/chunk/done` 或格式 B `SSEEvent` 为统一标准），输出文档化契约；或至少统一事件命名与字段结构。

**涉及文件**：
- `backend/app/services/sse_adapter.py`（统一适配层）
- `backend/app/api/chat.py`、`chat_stream.py`、`openllm_gateway.py`（输出端对齐）

**实现要点**：
1. 选定统一事件格式（建议沿用格式 B 的 SSEEvent 枚举：routing/chunk/done/error/usage，将格式 C 的 routing 语义并入）。
2. chat/completions 流式输出（格式 A）经 sse_adapter 转统一格式（保持 OpenAI 兼容模式可配置关闭）。
3. 输出《SSE 事件契约文档》（事件名/字段/顺序/终止语义），供对接方（OpenBase llm-proxy、前端 parseSSEStream）引用。

**验收标准**：
- 统一后各 SSE 端点事件命名一致（routing/chunk/done/error/usage），字段结构一致。
- OpenAI 兼容模式（如有）行为不回归。
- OpenBase proxy 透传无需按端点特判（单一解析器可用）。

**验证方法**：新增 SSE 契约测试（断言事件序列与字段）；经 OpenBase proxy 分别请求 chat/chat-stream/网关流式端点，单一 parseSSEStream 解析全部通过。

---

### M5 local_models 端点鉴权补强（P2，安全）

**现状**：`backend/app/api/local_models.py`（前缀 `/local-models` → `/api/v1/local-models`）全部端点**无鉴权依赖**（无 Depends），含 POST /pull（SSE 拉流）、DELETE /{model_name}、POST /{model_name}/start、/stop、/update、PUT /{model_name}/gpu-schedule 等。OpenLLM 8001 若暴露至非本机网络存在未授权操作风险。

**目标**：local_models 全部端点补充鉴权（建议 JWT 活跃用户 `get_current_active_user`，敏感操作（删除/启停）管理员），与平台其他端点一致。

**涉及文件**：
- `backend/app/api/local_models.py`（全部端点加 Depends）
- `backend/app/services/auth_service.py`（复用现成依赖）

**实现要点**：
1. 只读/拉取类端点（GET 列表/详情、POST /pull）加 `Depends(get_current_active_user)`。
2. 操作类端点（DELETE、start/stop/update、gpu-schedule）加 `Depends(get_current_admin_user)`（或角色校验）。
3. 保留 Ollama 内部回调/本机访问白名单（如有）——确认 pull 过程中 Ollama 回连不被误伤。

**验收标准**：
- 未认证请求 local_models 全部端点返回 401。
- 普通用户可 GET/pull；管理员可删除/启停。
- 既有本地模型功能（Ollama 适配器）无回归。

**验证方法**：`python -m pytest backend/tests/test_local_models_api.py backend/tests/test_ollama_adapter.py`（新增鉴权用例）。

---

### M6 openapi.json 生产环境开放策略（P2）

**现状**：`backend/main.py` L334-336：`docs_url/redoc_url/openapi_url = None if not settings.DEBUG`，生产（DEBUG=false）下 /docs、/redoc、/openapi.json 全部 404。OpenBase 对接契约核验/自动化测试依赖 openapi.json 时受限。

**目标**：生产环境提供受控的 openapi.json（建议保留 openapi_url，关闭 docs/redoc 或加鉴权），便于对接方契约核验。

**涉及文件**：
- `backend/app/core/config.py`（新增配置项，如 `OPENAPI_PUBLIC`）
- `backend/main.py`（openapi_url 条件注册）

**实现要点**：
1. 新增配置 `OPENAPI_PUBLIC: bool = Field(default=False)`（生产默认关闭）。
2. `openapi_url="/openapi.json" if (settings.DEBUG or settings.OPENAPI_PUBLIC) else None`；docs/redoc 维持 DEBUG 控制。
3. 若需更严格：openapi.json 端点加 API Key 鉴权（自定义 get_openapi 路由）。

**验收标准**：
- `OPENAPI_PUBLIC=true` 时生产环境 `GET /openapi.json` 200。
- 默认（false）行为不变（404）；/docs、/redoc 生产仍 404。

**验证方法**：设置 `DEBUG=false OPENAPI_PUBLIC=true` 启动，curl /openapi.json 200；OpenBase 契约核验脚本可拉取。

---

## 4. 实施顺序与依赖

| 顺序 | 项 | 依赖 | 说明 |
|:---:|-----|------|------|
| 1 | M1 会话 API Key 通道 | 无 | 阻塞项，优先；解锁对话管理页会话闭环 |
| 2 | M2 模型写操作 + 路由修复 | 无 | 独立；解锁模型管理页写操作 |
| 3 | M3 身份头支持 | 无 | 独立；审计归属增强（TD-新增-010 偿还路径） |
| 4 | M6 openapi.json 开放 | 无 | 独立小改；便于契约核验 |
| 5 | M4 SSE 格式统一 | 无 | 改动面较大（3 处输出端 + 适配层），建议独立会话 |
| 6 | M5 local_models 鉴权 | 无 | 独立安全补强 |

建议一个会话内按 1→2→3→6 完成核心项，4/5 视资源安排；每项完成后跑对应测试与真实验证再进入下一项。M1 完成后即可解除 OpenBase v1.4.3 对话管理页的通道阻塞（降级方案可撤销）。

## 5. 全量回归验证清单

修改完成后，在 OpenLLM 项目内执行：

| 命令 | 预期 |
|------|------|
| `python -m pytest backend/tests -q` | 全部通过（新增用例 + 既有回归） |
| `python -m ruff check backend/app` | All checks passed（0 错误） |

联调回归（OpenBase 8000 + OpenLLM 8001）：

| 场景 | 命令/操作 | 预期 |
|------|-----------|------|
| 会话列表 | OpenBase proxy `GET /api/v1/llm-proxy/conversations` | 200 + 真实会话数据 |
| 新建/归档/删除会话 | proxy POST / archive / DELETE | 200，落库生效 |
| 模型写操作 | proxy POST /providers/{id}/models 创建 → GET 可见 | 200/201 + 列表可见 |
| 模型详情 | proxy `GET /api/v1/llm-proxy/models/{model_id}` | 200（路由遮蔽已修复） |
| SSE 流式对话 | proxy `POST /api/v1/llm-proxy/chat/stream` | routing/chunk/done 事件完整 |
| 审计归属 | 经 proxy 注入 X-User-ID 调用后查审计日志 | external_user_id 字段正确 |
| 安全回归 | 未认证访问 local_models 端点 | 401 |

## 6. 风险与注意事项

- **双通道鉴权影响面**：M1/M2 引入 API Key 通道后，需确保既有 JWT 通道行为完全不变（新增依赖而非替换），避免权限降级。
- **路由顺序修复**：M2 静态/动态路由重排需回归全部 providers 端点（GET /providers/all、GET /providers/{id}/models、GET /providers/models/all 互不遮蔽）。
- **身份头信任边界**：M3 身份头仅在 API Key 通道下生效，**不得信任来自公网的 X-User-ID 覆盖 JWT 身份**（防身份伪造）；若外部可直接访问 OpenLLM，需可信代理（OpenBase）剥离外部头。
- **SSE 兼容风险**：M4 格式统一若保留 OpenAI 兼容输出，需双模式测试（OpenAI 客户端 + OpenBase 网关客户端）。
- **本地模型功能回归**：M5 补鉴权可能影响 Ollama 集成脚本/CI（如拉模型流程），需在测试环境先行验证。
- **文档单一事实源**：本任务书为 OpenLLM 侧对接完善的唯一执行依据；修改完成后在 OpenLLM 项目内同步 DevLogReport 修订历史并回填本任务书状态列（待补充状态追踪表：M1~M6 各自 PENDING/IN_PROGRESS/DONE/VERIFIED）。

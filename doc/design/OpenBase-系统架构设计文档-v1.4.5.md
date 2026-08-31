# OpenBase 系统架构设计文档 - v1.4.5

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.5 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | SA-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 存放 | doc/design/ |

---

## 1. 设计目标与范围

| 项 | 内容 |
|----|------|
| 设计范围 | FR-145-01~06（DPS 服务接入 + 认证边界与身份头注入 + dps-proxy 转发 + 前端 2 页真实化 + 联调收尾） |
| 前置验证 | DPS v2.7.1 实际代码核验通过：FastAPI 入口 `src/rest_api/app.py`；端口变量 `API_PORT`（默认 8000）；Header 身份认证（X-Org-ID/X-Tenant-ID/X-User-ID 必传 + RBAC 中间件，组织/租户须预存在库）；`/api/v2/auth/login` 未实现（仅白名单）；核心端点（画像/标签/报表/批量/审计）；成功 `{code:200,message,data}` + 404 `{detail}`；健康 `/health/liveness`（白名单）；无 SSE 端点；`/api/v1/*` 与 `/api/v2/*` 双挂载 |
| 约束 | 分层架构（Controller/Service/Repository）、错误码统一 BaseError、SQLAlchemy 参数化、结构化日志、向后兼容既有端点（llm_proxy/rag_proxy/memory_proxy/网关服务发现）；四维身份专项挂起（本版本身份头用既有 JWT 字段） |

## 2. 系统架构

### 2.1 总体架构（v1.4.5 目标态）

```
统一前端（OpenBase frontend，Vue3）
  │  OpenBase JWT（get_current_user）
  ▼
OpenBase 后端（FastAPI，:8000）
  ├─ auth 模块：登录/签发 JWT（既有，payload: sub/tenant_id/org_id/role）
  ├─ llm_proxy 模块：/api/v1/llm-proxy/*（既有，OpenLLM 8001）
  ├─ rag_proxy 模块：/api/v1/rag-proxy/*（既有，OpenRAG 8010）
  ├─ dps_proxy 模块：/api/v1/dps-proxy/*（v1.4.5 新增）◀── 本版本核心
  │     ├─ 认证：OpenBase JWT 门禁（唯一认证入口，未认证 401）
  │     ├─ 身份头注入：X-User-ID/X-Tenant-ID/X-Org-ID/X-User-Role（JWT → 四头，映射兜底）
  │     ├─ 转发：无上游密钥注入（DPS Header 身份认证）
  │     ├─ 统一响应：{code,message,data,timestamp}（非 SSE 端点）
  │     └─ 错误归一化：{code,message,data} + {detail} → 统一提取透传
  │
  │  http://127.0.0.1:8030（dps_upstream_base）
  ▼
DPS 后端（FastAPI，:8030，独立部署，v2.7.1）
  ├─ 画像 /api/v2/portrait*（计算/列表/详情/风险评估等）
  ├─ 标签 /api/v2/tags*（分类/值管理）
  ├─ 报表 /api/v2/reports*（概览/维度/趋势）
  ├─ 批量 /api/v2/batch*（导入/导出任务）
  ├─ 审计 /api/v2/audit*（日志/导出）
  ├─ 健康 /health/liveness（白名单免鉴权）
  └─ 基础设施：PostgreSQL（或 SQLite 降级）/ Redis（可选）
```

### 2.2 模块挂载设计

| 项 | 内容 |
|----|------|
| 新增模块 | `openbase/modules/dps_proxy/`（包，`__init__.py` 导出 `router`，前缀 `/api/v1/dps-proxy`，tags=["dps-proxy"]） |
| 启用方式 | `demo_app.py` enable_module 列表追加 `"dps_proxy"`（init_app 自动 import + include_router） |
| 配置项 | `settings.py` 新增 `dps_upstream_base`（默认 `http://127.0.0.1:8030`）/ `dps_upstream_timeout`（20.0）/ `dps_default_org_id` / `dps_default_tenant_id` / `dps_org_map` / `dps_tenant_map`（可选映射 JSON）；无 dps_api_key |
| 结构 | 对标 `rag_proxy.py`：`_forward`（转发 + 统一响应）/ `_adapt_response`（统一响应 + {detail} 归一化）/ `_build_identity_headers`（四头构造注入，新增）；无 SSE 透传（DPS 无流式） |

## 3. 关键架构决策（ADR）

### ADR-145-01 dps-proxy 模块设计（独立模块 vs 扩展既有 proxy）

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | 新建独立模块 `openbase/modules/dps_proxy/`（路由前缀 `/api/v1/dps-proxy`），不并入 rag_proxy 或通用 proxy |
| 理由 | ① 路由前缀独立（dps-proxy）避免认证/转发逻辑耦合；② 上游契约不同（DPS Header 身份认证 + 无 SSE + 无密钥），独立模块便于按契约演进；③ 模块启停独立（enable_module） |
| 备选 | A. 扩展 rag_proxy → 否决：跨系统契约混淆（OpenRAG 无认证 vs DPS Header 身份 + 无 SSE）；B. 扩展通用 proxy 通道 → 否决：无法承载身份头注入专用逻辑 |
| 风险 | 模块数量增加 → 注册清单维护成本，随版本演进可控 |

### ADR-145-02 认证边界与身份头注入（OpenBase 唯一认证入口 + 四头构造）

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | dps-proxy 全部端点要求 OpenBase JWT（get_current_user，未认证 401）；**身份头注入**：按需求 §3 映射规则从 OpenBase JWT/用户上下文构造四头（X-User-ID←sub、X-Tenant-ID←tenant_id、X-Org-ID←org_id、X-User-Role←role）注入上游；JWT 字段缺失时用 `dps_default_*` 兜底，映射表 `dps_org_map`/`dps_tenant_map` 支持 OpenBase→DPS 值转换；DPS 侧认证体系落地登记任务书 |
| 理由 | ① DPS Header 身份认证是代码事实（四头必传 + RBAC 校验）；② OpenBase 作为统一入口汇聚认证是既有模式（OpenMemory/OpenLLM/OpenRAG 均经 OpenBase）；③ 本版本不扩 DPS 代码（登记任务书，独立会话实施） |
| 备选 | A. 前端直传四头 → 否决：身份可伪造 + 多入口；B. DPS 侧实现标准登录 → 延后（任务书，需 DPS 代码改动） |
| 风险 | 组织/租户映射不成立（OQ-145-1）→ 联调确认 + 映射表兜底；DPS 组织/租户须预存在库 → 种子数据任务（BL-145-01） |

### ADR-145-03 错误归一化方案

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | 非 SSE 端点统一响应 {code,message,data,timestamp}；错误提取顺序 body.code（非 200）> body.detail（str/dict/list）> HTTP 状态码（覆盖 DPS 成功 {code:200,message,data} + FastAPI {detail} 双格式） |
| 理由 | ① DPS 成功用 {code:200,message,data}、404 用 FastAPI {detail}，需归一化供前端统一解析；② 无 SSE 端点（DPS 无流式），不需 SSE 透传逻辑 |
| 备选 | A. 前端分别解析两种错误格式 → 否决：前端耦合上游错误细节 |
| 风险 | 上游错误格式漂移 → 联调验证 + 任务书登记 |

### ADR-145-04 前端画像页真实化方式

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | 直接改造既有 DPS 画像模块前端页（画像列表页/画像详情页），数据源从 mock 切换为调用 OpenBase dps-proxy；新增统一 API 层封装（`src/core/api/dps.ts`，走既有 http.ts） |
| 理由 | ① 复用既有页面 UI 骨架；② 走 OpenBase proxy 保证前端不直连 DPS（AC-145-04-3）；③ 无 SSE（前端不需流式消费） |
| 备选 | 重建新页面 → 否决：重复 UI 工作；前端直连 DPS 8030 → 否决：身份头暴露 + 多入口 |
| 风险 | 画像计算依赖 AI 模型服务（OQ-145-2）→ 联调确认，失败态前端提示 |

## 4. 数据模型设计

**结论：本版本无新增 OpenBase 本地数据表。**

| 数据 | 归属 | 说明 |
|------|------|------|
| DPS 画像/标签/报表数据 | DPS 上游（PG/SQLite） | OpenBase 只经 proxy 读写消费，不落本地库 |
| dps_upstream_* 配置 | OpenBase settings/.env | 配置项（dps_upstream_base/timeout/default_* / 映射表） |
| 审计日志 | OpenBase audit 模块（既有） | proxy 转发关键操作记录审计 |

> 数据库设计不适用说明：无 DDL/迁移/索引设计；既有库表无变更。

## 5. API 设计摘要（详见《OpenBase-API接口设计文档-v1.4.5.md》）

| 方法 | OpenBase 路径 | 上游目标 | 响应 |
|------|---------------|----------|------|
| GET/POST | /api/v1/dps-proxy/portraits[/calculate] | /api/v2/portrait* | 统一 JSON |
| GET | /api/v1/dps-proxy/portraits/{person_id} | /api/v2/portrait/{person_id} | 统一 JSON |
| GET | /api/v1/dps-proxy/tags/categories | /api/v2/tags/categories | 统一 JSON |
| GET | /api/v1/dps-proxy/reports/overview | /api/v2/reports/overview | 统一 JSON |
| GET | /api/v1/dps-proxy/batch/tasks/{task_id} | /api/v2/batch/import/{task_id}/status | 统一 JSON |
| GET | /api/v1/dps-proxy/audit/logs | /api/v2/audit/logs | 统一 JSON |
| GET | /api/v1/dps-proxy/health | /health/liveness | 统一 JSON |

## 6. 安全设计

| 项 | 方案 |
|----|------|
| 认证边界 | OpenBase JWT 唯一前端入口（get_current_user）；dps-proxy 未认证 401；身份头由 proxy 构造（前端不可伪造） |
| 网络暴露 | DPS 8030 仅本机/内网访问（部署约束）；公网只能经 OpenBase dps-proxy |
| 输入校验 | proxy 端点入参沿用 Pydantic schema；person_id/task_id 为路径参数（无 SQL 面） |
| 审计 | proxy 转发关键操作记录审计日志（user_id/端点/HTTP 状态） |
| 错误处理 | OpenBase 侧 BaseError（AUTH_/SYS_ 前缀）；上游 {detail} 归一化透传 |

## 7. 可观测性

| 项 | 方案 |
|----|------|
| 日志 | dps_proxy 模块结构化日志（logger "openbase.dps_proxy"，extra：path/upstream_status/duration_ms）；不记录 Authorization 与身份头完整值 |
| 指标 | 复用 observability 模块（http 指标挂 path 标签） |
| 排障 | 上游不可达 WARN 日志；{detail} 归一化使前端可定位 |

## 8. 一致性约束（对既有架构）

| 约束 | 落实 |
|------|------|
| 分层架构 | dps-proxy 为 Controller 层（路由 + 转发），无业务逻辑层需求；不直接操作 DB |
| 错误码 | OpenBase 侧 BaseError；上游错误归一化不改写 |
| 命名 | 模块 snake_case（dps_proxy）；路由 kebab（dps-proxy）；配置 dps_* 前缀 |
| 日志 | logging + extra，禁止 print |
| 并发 | httpx.AsyncClient 每请求独立（对标 rag_proxy） |

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | SA-OpenBase-Dev | 初始创建：dps_proxy 模块架构（ADR-145-01~04：模块设计/认证边界与身份头注入/错误归一化/前端改造）、模块挂载、数据模型不适用、安全/可观测/一致性约束 |

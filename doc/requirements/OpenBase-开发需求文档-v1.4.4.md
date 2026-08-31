# OpenBase 开发需求文档 - v1.4.4

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.4 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | RA-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/requirements/ |

---

## 1. 版本概述

| 项 | 内容 |
|----|------|
| 版本主题 | OpenRAG 系统对接（1.4.x 逐个系统对接线第 2 站，共 4 站） |
| 需求来源 | 候选需求池 §1.10：R-380（VC-011，P1） |
| Backlog | BL-144-01~07（6 P1 + 1 P2），见《OpenBase-本版本Backlog-v1.4.4.md》 |
| 基线 | v1.4.3（Step 5 已部署发布，全流程闭环） |
| 关键外部依据 | OpenRAG v1.8.0（`D:\Trae CN\myproject\Dev\OpenRAG`）；v1.4.3 R-379 对接模式（差异：OpenRAG 上游无认证） |

## 2. 业务目标

| 目标 ID | 业务目标 | 用户目标 | 成功指标（映射 Step 0 G1~G5） |
|---------|----------|----------|-------------------------------|
| BO-144-1 | OpenRAG 服务就绪 | 运维可一键启动双系统 | G1：8010 健康检查通过、依赖可用、无端口冲突 |
| BO-144-2 | 认证边界打通 | 用户用 OpenBase 凭据访问 OpenRAG 能力 | G2：rag-proxy 未认证 401；OpenRAG 认证补强登记任务书 |
| BO-144-3 | 知识库/RAG 能力经 OpenBase 代理开放 | 前端/调用方不直连 OpenRAG | G3：≥6 proxy 端点、统一响应、{detail} 归一化、SSE 透传 |
| BO-144-4 | 知识库管理/RAG 对话页真实化 | 用户可走查真实知识库与 RAG 对话 | G4：2 页真实 API |
| BO-144-5 | 双系统联调闭环 | 集成工程师验收通过 | G5：知识库→文档→RAG 查询闭环、回归 ≥95%、覆盖率 ≥80% |

## 3. 功能需求

### 3.1 BL-144-01 OpenRAG 服务部署（P1，Phase 1）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 运维, I want 以 OPENRAG_API_PORT=8010 启动 OpenRAG v1.8.0 后端, so that OpenRAG 与 OpenBase（8000）并存且可真实访问 |
| 功能描述 | 基于本机 OpenRAG 项目（`D:\Trae CN\myproject\Dev\OpenRAG`）部署：`src/openrag/main.py` 以环境变量 `OPENRAG_API_PORT=8010` 启动（默认 8000 被覆盖，注意配置前缀 OPENRAG_）；健康检查 `GET /api/v1/system/health`（PG+Qdrant 核心组件，SQLite 可降级）；OpenAPI 文档无条件开放（/docs 可用，优于 OpenLLM）；端口冲突检测与治理（8000 已被 OpenBase 占用时 OpenRAG 必须使用 8010） |
| 验收标准 | AC-144-01-1 OpenRAG 8010 启动成功且 `/api/v1/system/health` 返回 200（status=healthy 或 degraded 但核心组件可用）；AC-144-01-2 `/docs` 可访问（openapi.json 可用，供契约核验）；AC-144-01-3 数据库依赖可用（PG 或 SQLite 降级）+ Qdrant 可用；AC-144-01-4 OpenBase 8000 与 OpenRAG 8010 并存无冲突 |

### 3.2 BL-144-02 认证边界（P1，Phase 2）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 平台管理员, I want OpenBase 统一认证门禁保护 rag-proxy, so that OpenRAG 无认证的能力不暴露给未授权调用方 |
| 功能描述 | **现状事实**：OpenRAG v1.8.0 HTTP API 无认证（设计文档《OpenRAG-API接口设计文档-v2.1.2》声称 API Key 认证但代码未实现——认证仅 MCP 通道有）。本版本方案：OpenBase rag-proxy 为**唯一认证入口**（OpenBase JWT get_current_user 门禁，未认证 401）；无上游密钥注入（与 OpenLLM 不同）；OpenRAG 侧认证体系落地登记任务书（M 级事项），后续版本实施 |
| 验收标准 | AC-144-02-1 rag-proxy 未认证请求返回 401（AUTH_401）；AC-144-02-2 认证后请求正常转发（200）；AC-144-02-3 OpenRAG 侧认证补强需求已登记任务书（状态/验收建议完整） |

### 3.3 BL-144-03 rag-proxy 转发适配（P1，Phase 2）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 前端/调用方, I want 通过 OpenBase rag-proxy 访问 OpenRAG 知识库/RAG 能力, so that 无需直连 OpenRAG 且认证统一 |
| 功能描述 | OpenBase 侧新增 `rag_proxy` 模块（对标 llm_proxy 模式）：核心端点转发——知识库列表（GET /api/v1/collections?page=&page_size=）、知识库详情（GET /collections/{id}）、知识库创建（POST /collections）、知识库删除（DELETE /collections/{id}）、文档上传（POST /collections/{cid}/documents，multipart，异步返回 PENDING）、文档列表/删除（GET/DELETE /collections/{cid}/documents[/{did}]）、RAG 查询（POST /collections/{cid}/query）、RAG 流式（POST /collections/{cid}/query/stream，SSE start→token→done）、纯检索（POST /collections/{cid}/query/retrieve）；统一响应 {code,message,data,timestamp} 适配；**错误归一化**：OpenRAG 两种错误格式（{code,message,data} 与 FastAPI {detail}）统一提取（body.code > body.detail.error/code > HTTP 状态码）；SSE 逐事件透传（不包装）；未认证 401 |
| 验收标准 | AC-144-03-1 核心业务端点经 OpenBase 代理 ≥6 个（知识库列表/详情/创建/删除、文档上传/列表/删除、RAG 查询/检索，允许等价映射）；AC-144-03-2 响应统一适配（2xx 返回 {code:0,message:"success",data,timestamp}）；AC-144-03-3 {detail} 错误归一化正确（404 知识库不存在 → 响应 code 提取 detail，HTTP 404）；AC-144-03-4 RAG 流式端点 SSE 逐事件透传（start/token/done 事件完整）；AC-144-03-5 未认证请求 401；AC-144-03-6 上游不可达返回 502 级错误（SYS_UPSTREAM_ERROR） |

### 3.4 BL-144-04 前端 2 页真实化（P1，Phase 3）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 用户, I want 在统一前端查看真实知识库与 RAG 对话, so that OpenRAG 能力可视化可走查 |
| 功能描述 | OpenRAG 模块前端 2 页 mock 替换真实 API（走 OpenBase rag-proxy，前端不直连 OpenRAG）：知识库管理页（知识库列表真实数据 + 新建/详情/删除 + 文档上传（异步 PENDING → 轮询状态展示）/文档列表/删除）；RAG 对话页（选择知识库 → 提问 → SSE 流式回复展示 + 来源引用（retrieve 结果）） |
| 验收标准 | AC-144-04-1 知识库管理页展示真实数据（经 proxy，非 mock）；AC-144-04-2 RAG 对话页真实流式回复（经 proxy，SSE 事件渲染）；AC-144-04-3 前端代码无 OpenRAG 上游地址硬编码（全部经 proxy）；AC-144-04-4 两页加载失败有错误提示与重试（非白屏） |

### 3.5 BL-144-05 双系统联调（P1，Phase 4）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 集成工程师, I want OpenBase 统一认证 → OpenRAG 知识库→文档→RAG 查询真实闭环, so that 对接完成可验收 |
| 功能描述 | 联调闭环：登录（OpenBase）→ rag-proxy → 知识库创建真实落库 → 文档上传（PENDING → 轮询完成）→ RAG 查询（检索 + 生成，含 SSE 流式）真实返回；集成测试（API 级）+ UAT 走查（页面级）；联调发现的 OpenRAG 侧缺口登记任务书（BL-144-06） |
| 验收标准 | AC-144-05-1 知识库创建经 proxy 真实落库（200 + 返回 collection_id）；AC-144-05-2 文档上传返回 PENDING 且轮询后状态变为完成（chunks 生成）；AC-144-05-3 RAG 查询经 proxy 真实返回（retrieve 命中 items + 生成回复）；AC-144-05-4 RAG 流式 SSE 事件完整（start/token/done）；AC-144-05-5 UAT 走查通过（页面级，知识库管理 + RAG 对话） |

### 3.6 BL-144-06 对接完善任务书（P2，Phase 4）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 集成工程师, I want 联调发现的 OpenRAG 侧缺口登记成任务书, so that 后续可独立会话专项完善 |
| 功能描述 | 复用《OpenBase-OpenLLM对接完善任务书-v1.0.0》模式，输出《OpenBase-OpenRAG对接完善任务书》：认证体系落地（M1）、错误格式统一（M2）、文档上传状态细化（M3）、v1.3 双前缀清理（M4）等逐项登记（状态/优先级/验收建议） |
| 验收标准 | AC-144-06-1 任务书文档产出（命名规范、逐项状态表、M 级事项编号）；AC-144-06-2 联调发现缺口 100% 登记（无遗漏） |

### 3.7 BL-144-07 收尾与还债（P1，Phase 4）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 开发者, I want 全量回归与覆盖率一键执行, so that 发布质量可量化 |
| 功能描述 | 复用 v1.4.3 测试基座与回归脚本化：全量 pytest（`python -m pytest tests`）、ruff 静态检查、覆盖率（`python -m pytest --cov=openbase`）；Step 4/5 文档产出；版本发布（Release Note、git tag v1.4.4、双远程推送） |
| 验收标准 | AC-144-07-1 全量回归通过率 ≥95%（无 P0/P1 未闭环）；AC-144-07-2 覆盖率 ≥80%；AC-144-07-3 Step 4/5 文档齐备且发布闭环（tag v1.4.4 推送） |

## 4. 业务流程与逻辑

### 4.1 OpenRAG 对接主流程

```
运维启动 OpenRAG（OPENRAG_API_PORT=8010）→ /api/v1/system/health 健康检查通过
  → OpenBase 配置 rag_upstream_base=http://127.0.0.1:8010
  → 用户登录 OpenBase（JWT）
  → 前端请求 OpenBase rag-proxy（携带 OpenBase JWT）
  → proxy 校验 JWT（未认证 401）→ 转发 OpenRAG 8010（无上游认证注入）
  → 知识库列表/详情/创建、文档上传（异步 PENDING→轮询）、RAG 查询（含 SSE）
  → proxy 统一响应 {code,message,data,timestamp}（SSE 端点逐事件透传）→ 前端
```

### 4.2 认证边界决策

```
OpenRAG HTTP API 无认证（代码事实）：
  ├─ 本版本：OpenBase rag-proxy = 唯一认证入口（JWT 门禁）
  │    └─ 前端/调用方 → OpenBase JWT → proxy → OpenRAG（无上游认证）
  └─ 后续：OpenRAG 侧认证体系落地（任务书 M1）
       设计文档声称 API Key 认证但代码未实现 → 需 OpenRAG 侧实现
       （或 OpenBase 前移网关统一管理）
```

### 4.3 文档上传异步流程

```
前端 POST rag-proxy/collections/{cid}/documents（multipart）
  → proxy 转发 OpenRAG → 返回 {status: PENDING, document_id}
  → 前端轮询 GET rag-proxy/collections/{cid}/documents/{did}
  → status: PROCESSING → COMPLETED（chunks 生成）或 FAILED（解析/向量化失败）
```

### 4.4 RAG 流式（SSE）透传逻辑

```
前端 POST rag-proxy/collections/{cid}/query/stream
  → proxy 校验 JWT → OpenRAG /collections/{cid}/query/stream
  → SSE 事件：event: start → event: token（重复） → event: done（完整结果）
  → proxy 逐事件透传（不缓冲、不包装）→ 前端消费
  → 异常：event: error 透传
```

## 5. 数据模型与接口定义

### 5.1 配置项（OpenBase settings 新增）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `rag_upstream_base` | `http://127.0.0.1:8010` | OpenRAG 上游基地址（8010 端口） |
| `rag_upstream_timeout` | `20.0` | 非流式请求超时（秒） |
| `rag_stream_timeout` | `120.0` | SSE 流式读超时（秒） |
| `rag_document_poll_interval` | `2.0` | 文档上传异步状态轮询间隔（秒，前端侧） |

> 无 `rag_api_key`（OpenRAG 无认证，OpenBase 唯一认证入口）。

### 5.2 OpenBase rag-proxy 接口规范（本版本新增）

| 方法 | OpenBase 路径 | 上游目标 | 说明 | 认证 |
|------|---------------|----------|------|------|
| GET | /api/v1/rag-proxy/collections | GET /api/v1/collections | 知识库列表 | OpenBase JWT |
| POST | /api/v1/rag-proxy/collections | POST /api/v1/collections | 创建知识库 | OpenBase JWT |
| GET | /api/v1/rag-proxy/collections/{id} | GET /api/v1/collections/{id} | 知识库详情 | OpenBase JWT |
| DELETE | /api/v1/rag-proxy/collections/{id} | DELETE /api/v1/collections/{id} | 删除知识库 | OpenBase JWT |
| POST | /api/v1/rag-proxy/collections/{cid}/documents | POST /api/v1/collections/{cid}/documents | 文档上传（multipart，异步 PENDING） | OpenBase JWT |
| GET | /api/v1/rag-proxy/collections/{cid}/documents | GET /api/v1/collections/{cid}/documents | 文档列表 | OpenBase JWT |
| DELETE | /api/v1/rag-proxy/collections/{cid}/documents/{did} | DELETE /api/v1/collections/{cid}/documents/{did} | 删除文档 | OpenBase JWT |
| POST | /api/v1/rag-proxy/collections/{cid}/query | POST /api/v1/collections/{cid}/query | RAG 查询（检索+生成） | OpenBase JWT |
| POST | /api/v1/rag-proxy/collections/{cid}/query/stream | POST /api/v1/collections/{cid}/query/stream | RAG 流式（SSE start/token/done） | OpenBase JWT |
| POST | /api/v1/rag-proxy/collections/{cid}/query/retrieve | POST /api/v1/collections/{cid}/query/retrieve | 纯检索 | OpenBase JWT |
| GET | /api/v1/rag-proxy/health | GET /api/v1/system/health | 上游健康透传 | OpenBase JWT |

> proxy 内部：校验 OpenBase JWT → 转发 OpenRAG 8010（无认证注入）；非 SSE 端点统一 {code,message,data,timestamp}；SSE 端点逐事件透传；{detail} 错误归一化。

### 5.3 错误归一化映射

| OpenRAG 错误形态 | 提取 | OpenBase 响应 |
|------------------|------|---------------|
| {code: 非0, message, data, timestamp} | body.code / body.message | code 透传 + HTTP 对应 |
| {detail: "知识库不存在: xxx"} | detail 字符串 | code=HTTP 状态码，message=detail |
| {detail: {error/code, message}} | detail.error/code + message | code 提取 + message |
| 网络不可达 | - | BaseError(SYS_UPSTREAM_ERROR) → 502 |

## 6. 非功能需求

| 类别 | 指标 |
|------|------|
| 性能 | rag-proxy 非流式转发 P95 ≤ 500ms（不含 OpenRAG 处理）；SSE 首包（start 事件）P95 ≤ 1s；知识库列表 P95 ≤ 300ms |
| 安全 | OpenBase JWT 唯一认证入口（rag-proxy 未认证 401）；无上游密钥注入（OpenRAG 无认证）；请求头不记录完整 Authorization；日志脱敏 |
| 可靠性 | 上游不可达 502（SYS_UPSTREAM_ERROR）；SSE 中断可重试；错误统一 BaseError 格式（OpenBase 侧） |
| 兼容性 | 前端不直连 OpenRAG；SSE 事件格式（start/token/done）与 llm-proxy（routing/chunk/done）互不冲突；既有 llm_proxy/网关无回归 |
| 可维护性 | rag_proxy 模块结构对标 llm_proxy（认证门禁/转发/响应适配/SSE 透传四函数拆分）；配置集中 settings（rag_* 前缀） |

## 7. 数据需求

| 实体/数据 | 说明 | 来源 | 生命周期 |
|-----------|------|------|----------|
| OpenRAG 知识库数据 | 知识库列表/详情（经 proxy 读写） | OpenRAG 上游 | 运行时读写，不落 OpenBase 库（OpenRAG PG/SQLite 持久化） |
| OpenRAG 文档数据 | 文档上传/列表/状态（经 proxy 读写） | OpenRAG 上游 | 运行时读写，不落 OpenBase 库 |
| RAG 检索/生成结果 | 查询结果（经 proxy 只读消费） | OpenRAG 上游 | 运行时读取 |

> 本版本无新增 OpenBase 本地数据表；数据全部消费 OpenRAG 上游。

## 8. 权限与安全需求

| 需求 | 说明 |
|------|------|
| 认证边界 | OpenBase JWT 为唯一前端入口认证（rag-proxy get_current_user）；OpenRAG 无上游认证（代理层兜底）；前端永不直连 OpenRAG |
| 权限控制 | rag-proxy 端点要求已登录用户；本版本不新增细粒度权限点（沿用 RBAC） |
| 审计 | proxy 转发关键操作记录审计日志（user_id/目标端点/HTTP 状态）；不记录 Authorization 完整值 |
| 安全合规 | 密钥不入 git（.env* 排除）；日志脱敏；输入校验沿用 Pydantic schema |

## 9. UI/UX 需求

| 页面 | 需求 |
|------|------|
| 知识库管理页 | 真实知识库列表（名称/描述/分块策略/状态/文档数）；新建/详情/删除；文档上传（文件选择 → PENDING → 状态轮询展示）；加载态/错误态（错误提示 + 重试） |
| RAG 对话页 | 知识库选择 → 提问输入 → SSE 流式回复增量渲染；来源引用展示（retrieve items：chunk content + score）；流式中止按钮；加载态/错误态 |
| 一致性 | 沿用统一前端 Design Token 与组件库；交互模式与 v1.4.3 对话管理页一致 |

## 10. 接口与集成需求

| 集成对象 | 方向 | 契约要点 |
|----------|------|----------|
| OpenRAG 知识库 API（/api/v1/collections*） | OpenBase→OpenRAG | 无认证；{code,message,data,timestamp} 成功 + {detail} 错误；分页参数 page/page_size |
| OpenRAG 文档 API（/collections/{cid}/documents*） | OpenBase→OpenRAG | multipart 上传；异步 PENDING→轮询；sha256 去重 |
| OpenRAG 查询 API（/collections/{cid}/query*） | OpenBase→OpenRAG | RAG 查询/检索/SSE 流式（start/token/done）；retrieve 返回 items 数组 |
| OpenRAG 健康（/api/v1/system/health） | OpenBase→OpenRAG | 运维探测；免鉴权 |
| OpenBase 前端 | 前端→OpenBase proxy | OpenBase JWT；统一响应；SSE 逐事件透传 |
| 网关服务发现（现有骨架） | OpenBase 内部 | rag 服务注册/探测沿用（不改造发现机制） |

## 11. 约束、边界和排除项

| 项 | 内容 |
|----|------|
| 排除 | DPS 对接（v1.4.5）；四系统统一集成测试（v1.5）；R-376/R-377（v1.5） |
| 排除 | OpenRAG 前端功能补全（R-313~R-317 历史条目）——本版本仅接入核心可走查页（知识库管理/RAG 对话 2 页） |
| 排除 | OpenRAG 侧认证体系落地（本版本 OpenBase JWT 门禁兜底，认证实现登记任务书 M1） |
| 约束 | 不得扩大 Step 0 已批准范围（R-380 拆解 7 条 Backlog 为界） |
| 约束 | 技术约束：OpenRAG 无认证（不注入上游密钥）；错误 {detail} 归一化；v1.3 双前缀路由规避（仅用 /api/v1 标准路由）；文档上传异步（轮询） |
| 假设 | OpenRAG 后端本机可启动（PG 或 SQLite 降级 + Qdrant）；OpenRAG 存在可用的向量数据库（Qdrant） |
| 开放问题 | OQ-144-1：OpenRAG 认证体系落地方式（OpenRAG 侧实现 vs OpenBase 网关前移）——登记任务书 M1，后续评估；OQ-144-2：文档上传解析/向量化依赖模型可用性（需 OpenRAG 配置 embedding/LLM 提供商）——联调确认 |

## 12. 优先级确认

| Backlog ID | 优先级 | 需求 | 本版本范围 |
|-----------|:------:|------|-----------|
| BL-144-01 | P1 | OpenRAG 服务部署 | 必须（M1） |
| BL-144-02 | P1 | 认证边界 | 必须（M2） |
| BL-144-03 | P1 | rag-proxy 转发适配 | 必须（M2） |
| BL-144-04 | P1 | 前端 2 页真实化 | 必须（M3） |
| BL-144-05 | P1 | 双系统联调 | 必须（M4） |
| BL-144-06 | P2 | 对接完善任务书 | 应当（与 05 合并执行） |
| BL-144-07 | P1 | 收尾与还债 | 必须（M4） |

## 13. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | RA-OpenBase-Dev | 初始创建：R-380 拆解 7 条 Backlog 功能需求（AC-144-01~07）、业务流程（对接/认证边界/文档异步/SSE）、接口规范（11 端点 + 错误归一化）、非功能/数据/权限/UI/接口需求、约束排除项、优先级确认 |

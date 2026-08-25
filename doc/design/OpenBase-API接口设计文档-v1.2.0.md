# OpenBase API 接口设计文档 - v1.2.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.2.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 适用环境 | Dev / Test / Pro |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 存放 | doc/design/ |

> 本版本 API 设计以**统一鉴权契约 + 四系统特色 API 代理 + AI 应用增量 API** 为核心。后端底座 API（auth/notifications/mcp 等 v1.0.0~v1.1.0 已稳定）作为契约事实源，经 openapi.json 生成前端客户端。

## 1. 统一响应与错误契约（RT-204）

| 项 | 契约 |
|----|------|
| 成功 | `{code: 0, message: "ok", data: T}`（分页：`data:{items,total,page,page_size}`） |
| 错误 | `{code, message, detail, request_id}`；code 前缀：AUTH/PERM/PARAM/BIZ/SYS/STORAGE |
| 鉴权 | Authorization: Bearer {access_token}；401 触发静默刷新（refresh_token），失败跳登录 |
| 幂等 | 写操作支持 Idempotency-Key 头（可选） |
| 版本 | 路径前缀 /api/v1（DPS 特色代理保持 /api/v2 透传） |

## 2. 认证接口

| 方法 | 路径 | 说明 | 请求 | 响应 |
|------|------|------|------|------|
| POST | /api/v1/auth/login | 登录（基线 admin/admin123） | {username,password} | {access_token, refresh_token, user{id,username,roles,permissions}} |
| POST | /api/v1/auth/refresh | 刷新 | {refresh_token} | {access_token} |
| POST | /api/v1/auth/logout | 登出 | - | - |
| GET | /api/v1/auth/me | 当前用户+权限 | - | {id,username,roles,permissions} |

## 3. 四系统特色 API 代理（RT-204/205~208）

代理统一形态：`/api/v1/proxy/{system}/*`，后端校验 JWT 后按路由表转发四系统原生 API，响应统一包装为 ErrorResponse 契约（透传数据体）。

### 3.1 OpenLLM 代理（/api/v1/proxy/openllm/*）

| 域 | 代理端点 | 后端目标 |
|----|---------|---------|
| 对话 | /conversations（列表/详情/导出/批量删除）、/chat/stream（SSE 透传） | OpenLLM /api/v1、/openllm/v1 |
| 用量 | /usage/trends、/usage/export | OpenLLM /api/v1/usage/* |
| 监控 | /monitoring/metrics、/monitoring/traces、/billing/cost-analysis、/budgets、/alerts | OpenLLM /api/v1/* |
| 模型 | /models（CRUD）、/models/local（Ollama）、/providers、/providers/register、/api-keys、/deploy、/gpu、/adapters | OpenLLM /api/v1、/edgerouter/* |
| 健康 | /health | OpenLLM /openllm/v1/health |

### 3.2 OpenRAG 代理（/api/v1/proxy/openrag/*）

| 域 | 代理端点 | 后端目标 |
|----|---------|---------|
| 知识库 | /collections（CRUD） | OpenRAG /api/v1/collections |
| 文档 | /collections/{id}/documents（上传/批量/列表/reindex） | OpenRAG /api/v1/* |
| 索引 | /collections/{id}/index/build | OpenRAG /api/v1/* |
| 检索 | /query、/query/stream（SSE）、/retrieve | OpenRAG /api/v1/* |

### 3.3 OpenMemory 代理（/api/v1/proxy/openmemory/*）

| 域 | 代理端点 | 后端目标 |
|----|---------|---------|
| 记忆 | /memories（CRUD/search）、/remember、/forget、/improve | OpenMemory /api/v1/* |
| 召回 | /recall、/recall/traces/{trace_id} | OpenMemory /api/v1/* |
| 衰减 | /decay/config | OpenMemory /api/v1/* |
| 会话 | /sessions（列表/终止） | OpenMemory /api/v1/* |
| 图谱/多模态 | /memories/graph、/memories/image、/audio/transcribe | OpenMemory /api/v1/* |

### 3.4 DPS 代理（/api/v1/proxy/dps/*，透传 /api/v2）

| 域 | 代理端点 | 后端目标 |
|----|---------|---------|
| 画像 | /profiles（CRUD/search/tags） | DPS /api/v2/profiles* |
| 标签 | /tags/categories、/tags/values、/tags/stats | DPS /api/v2/tags* |
| 报表 | /reports/overview|dimensions|tags|trends|orgs|export | DPS /api/v2/reports* |
| 批量 | /batch/import（preview/execute/status/errors）、/batch/export | DPS /api/v2/batch* |

### 3.5 代理路由表与契约收敛

- 路由表存于 config 模块（YAML 配置 system→base_url→路径映射→鉴权凭据引用），密钥不落前端
- Step 2 已按四系统 OpenAPI 盘点：知识库 29 / 记忆 50 / 画像 52 端点，上表为核心收敛清单；超出部分登记 backlog（语义路由/A-B 测试/插件/配置中心/Webhook/计费等）

## 4. AI 应用增量 API（全新补建，RT-205）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | /api/v1/ai-apps | 应用列表/创建 |
| GET/PUT/DELETE | /api/v1/ai-apps/{id} | 应用详情/更新/删除 |
| POST | /api/v1/ai-apps/{id}/publish | 发布（版本递增） |
| POST | /api/v1/ai-apps/{id}/unpublish | 下架 |
| GET | /api/v1/ai-apps/{id}/versions | 版本列表 |
| GET | /api/v1/ai-apps/{id}/calls | 调用记录（分页/筛选） |

请求体示例（创建/更新）：`{name, description, model_config:{provider, model, parameters:{temperature,top_p,max_tokens}}, prompt_template_id?, status}`。

## 5. 动态模块相关 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/modules | 模块注册表（id/name/route_prefix/permission/status） |
| GET | /api/v1/modules/{id} | 模块详情（含入口/权限标识） |

模块挂载信息由后端下发，前端 ModuleRegistry 据此注入路由与菜单（RT-203）。

## 6. 契约生成与校验（RT-204）

| 项 | 设计 |
|----|------|
| 生成 | 后端 openapi.json → openapi-typescript → src/core/api/types（CI 内自动） |
| 校验 | 前端类型与后端 openapi.json diff 检查（CI 门禁），0 缺口 |
| 对齐检查 | 前端页面清单 ↔ 后端 API 交叉验证（prototype-coverage + backend-coverage 输出） |

## 7. SSE 透传说明（RT-205 对话监控）

- 前端 EventSource/fetch-stream 对接代理 `/api/v1/proxy/openllm/chat/stream`（OpenLLM routing→chunk→done 事件序列透传）
- 监控类页面采用轮询（10s/30s/60s 分级），不建立独立 SSE 通道（对齐 OpenLLM 现状）

## 8. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | AA-OpenBase-Dev | 初始创建：统一契约/认证/四系统代理/AI 应用增量/动态模块 API/契约生成校验 |

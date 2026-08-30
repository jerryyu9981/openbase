# OpenBase 开发需求文档 - v1.4.3

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.3 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | RA-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/requirements/ |

---

## 1. 版本概述

| 项 | 内容 |
|----|------|
| 版本主题 | OpenLLM 系统对接（1.4.x 逐个系统对接线第 1 站，共 4 站） |
| 需求来源 | 候选需求池 §1.9：R-379（VC-011，P1） |
| Backlog | BL-143-01~07（6 P1 + 1 P2），见《OpenBase-本版本Backlog-v1.4.3.md》 |
| 基线 | v1.4.2（Step 5 已部署发布，全流程闭环） |
| 关键外部依据 | OpenLLM v2.13.0 后端（`D:\Trae CN\myproject\Dev\OpenLLM`）；v1.4.2 R-378 OpenMemory 对接模式（双层认证共享 + proxy 转发 + 前端真实化 + 联调） |

## 2. 业务目标

| 目标 ID | 业务目标 | 用户目标 | 成功指标（映射 Step 0 G1~G5） |
|---------|----------|----------|-------------------------------|
| BO-143-1 | OpenLLM 服务就绪，与 OpenBase 并存 | 运维可一键启动双系统 | G1：8001 健康检查通过、依赖可用、无端口冲突 |
| BO-143-2 | 统一认证通道打通 | 用户用 OpenBase 凭据即可访问 OpenLLM 能力 | G2：认证注入正确、密钥配置可复现 |
| BO-143-3 | 模型与对话能力经 OpenBase 代理开放 | 前端/调用方不接触 OpenLLM 密钥 | G3：≥5 proxy 端点、统一响应、错误透传、SSE 兼容 |
| BO-143-4 | 模型管理/对话管理页真实化 | 用户可走查真实模型与对话数据 | G4：2 页真实 API、无密钥接触 |
| BO-143-5 | 双系统联调闭环，为对接线定基线 | 集成工程师验收通过 | G5：登录→模型列表→对话闭环、回归 ≥95%、覆盖率 ≥80% |

## 3. 功能需求

### 3.1 BL-143-01 OpenLLM 服务部署（P1，Phase 1）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 运维, I want 以 PORT=8001 启动 OpenLLM v2.13.0 后端, so that OpenLLM 与 OpenBase（8000）并存且可真实访问 |
| 功能描述 | 基于本机 OpenLLM 项目（`D:\Trae CN\myproject\Dev\OpenLLM`）部署：`backend/main.py` 以环境变量 PORT=8001 启动（默认 8000 被覆盖），HOST 默认 0.0.0.0；健康检查端点 `/health`（PostgreSQL + Redis 探测）与 `/openllm/v1/health`（网关健康）可用；PG/Redis 依赖可用；端口冲突检测与治理（8000 已被 OpenBase 占用时 OpenLLM 必须使用 8001） |
| 验收标准 | AC-143-01-1 OpenLLM 8001 启动成功且 `/health` 返回 200（status=healthy）；AC-143-01-2 `/openllm/v1/health` 返回 200（code=0, data.status）；AC-143-01-3 PG/Redis 依赖检查通过（/health details 均 healthy）；AC-143-01-4 OpenBase 8000 与 OpenLLM 8001 并存无冲突（双服务健康检查均通过） |

### 3.2 BL-143-02 认证适配（P1，Phase 2）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 集成工程师, I want OpenBase 与 OpenLLM 认证契约对齐, so that 调用方经 OpenBase 统一认证即可访问 OpenLLM 能力 |
| 功能描述 | 认证契约调研确认（OpenLLM v2.13.0 事实）：JWT 通道 `POST /api/v1/auth/login`（HS256，SECRET_KEY 环境变量，Access 15min）；API Key 通道 `sk-openllm-` 前缀且**仅支持 Authorization: Bearer 头传递**（不支持 X-API-Key 头）；统一网关 `/openllm/v1/*` 双通道鉴权（API Key 优先，否则 JWT）。OpenBase 侧认证适配方案：主通道为 OpenBase 持有 OpenLLM 服务级 API Key（sk-openllm-），proxy 转发时注入 `Authorization: Bearer <sk-openllm-...>`；JWT 通道作为备选（需共享 SECRET_KEY + 用户映射，复杂度高，本版本 P2 评估）。密钥通过 settings/.env 配置（`llm_api_key`），不硬编码、不落前端、不落日志 |
| 验收标准 | AC-143-02-1 认证契约调研记录完成（JWT/API Key 双通道、Bearer 传递方式、网关错误码体系 1001/1003/1004/2001/5001 确认）；AC-143-02-2 使用 OpenBase 持有的 OpenLLM API Key 请求 `/openllm/v1/models` 返回 200（非 401）；AC-143-02-3 密钥配置化（settings 新增 `llm_api_key`/`llm_upstream_base`/`llm_upstream_timeout`，.env 可覆盖），代码无硬编码密钥；AC-143-02-4 未认证请求 proxy 返回 401（OpenBase 侧统一拦截） |

### 3.3 BL-143-03 llm-proxy 转发适配（P1，Phase 2）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 前端/调用方, I want 通过 OpenBase llm-proxy 访问 OpenLLM 模型与对话能力, so that 无需持有 OpenLLM 密钥且认证统一 |
| 功能描述 | OpenBase 侧新增 `llm_proxy` 模块（对标 `memory_proxy.py` 模式）：核心端点转发——模型列表（GET `/openllm/v1/models`）、模型详情（GET `/api/v1/providers/models/{model_id}`，JWT 通道或网关等价端点）、对话（POST `/openllm/v1/chat`）、对话流式（POST `/openllm/v1/chat/stream`，SSE 事件 routing→chunk→done 透传）、健康（GET `/openllm/v1/health`）；统一响应 `{code,message,data,timestamp}` 适配；错误透传（网关错误码 1001→401、1003→429、1004→404、2001→404、5001→500，提取顺序 body.error > body.code > HTTP 状态码）；SSE 流式透传兼容（无统一响应包装，逐事件透传）；未认证请求 401 |
| 验收标准 | AC-143-03-1 核心业务端点经 OpenBase 代理 ≥5 个（模型列表/模型详情/对话/对话流式/健康，允许等价端点映射）；AC-143-03-2 响应统一适配（2xx 返回 {code:0,message:"success",data,timestamp}，data 为上游完整响应）；AC-143-03-3 错误透传正确（上游 1001/2001 等错误码映射到响应 code 与正确 HTTP 状态）；AC-143-03-4 对话流式端点 SSE 逐事件透传（routing/chunk/done 事件完整，浏览器可消费）；AC-143-03-5 未认证请求 401；AC-143-03-6 上游不可达时返回 502 级错误（SYS_UPSTREAM_ERROR 语义） |

### 3.4 BL-143-04 前端 2 页真实化（P1，Phase 3）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 用户, I want 在统一前端查看真实模型列表与对话管理数据, so that OpenLLM 能力可视化可走查 |
| 功能描述 | OpenLLM 模块前端 2 页 mock 替换真实 API（走 OpenBase llm-proxy，前端不接触 OpenLLM 密钥）：模型管理页（`Models.vue`）——模型列表真实数据（名称/Provider/类型/能力/定价/状态），新增/编辑/删除按 OpenLLM 能力范围适配（本版本以列表/详情为主，写操作按 OpenLLM 端点能力评估）；对话管理页（`Conversations.vue`）——会话列表真实数据（标题/模型/消息数/时间/Token）、新建会话/进入聊天/归档/删除（映射 OpenLLM `/api/v1/conversations` 系列端点，经 proxy 转发） |
| 验收标准 | AC-143-04-1 模型管理页展示真实模型数据（经 proxy，非 mock）；AC-143-04-2 对话管理页展示真实会话数据（经 proxy，非 mock）；AC-143-04-3 前端代码无 OpenLLM 密钥（无 sk-openllm- 常量、无上游地址硬编码）；AC-143-04-4 两页数据加载失败时有错误提示与重试（非白屏） |

### 3.5 BL-143-05 双系统联调（P1，Phase 4）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 集成工程师, I want OpenBase 统一认证 → OpenLLM 模型列表/对话真实闭环, so that 对接完成可验收 |
| 功能描述 | 联调闭环：登录（OpenBase）→ 前端经 llm-proxy → OpenLLM 模型列表真实展示 → 发起对话（含 SSE 流式）→ 会话落库可查；集成测试（API 级）+ UAT 走查（页面级）；联调发现的 OpenLLM 侧占位/缺口登记任务书（BL-143-06） |
| 验收标准 | AC-143-05-1 登录后模型列表经 proxy 真实返回（200，数据非 mock）；AC-143-05-2 对话请求经 proxy 真实完成（非流式返回 200 + choices；流式 SSE 事件完整）；AC-143-05-3 会话创建/列表经 proxy 真实落库与查询；AC-143-05-4 集成测试用例全部通过（API 级）；AC-143-05-5 UAT 走查通过（页面级，模型管理 + 对话管理） |

### 3.6 BL-143-06 对接完善任务书（P2，Phase 4）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 集成工程师, I want 联调发现的 OpenLLM 侧缺口登记成任务书, so that 后续可在独立会话专项完善 |
| 功能描述 | 复用《OpenBase-OpenMemory对接完善任务书-v1.0.0》模式，输出《OpenBase-OpenLLM对接完善任务书》：联调发现的 OpenLLM 侧占位/缺口/契约差异逐项登记（状态/优先级/验收建议），作为后续版本（v1.4.x 或对接线后续站）输入 |
| 验收标准 | AC-143-06-1 任务书文档产出（命名规范、逐项状态表、M 级事项编号）；AC-143-06-2 联调发现缺口 100% 登记（无遗漏） |

### 3.7 BL-143-07 收尾与还债（P1，Phase 4）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 开发者, I want 全量回归与覆盖率一键执行, so that 发布质量可量化 |
| 功能描述 | 复用 v1.4.2 测试基座与回归脚本化：全量 pytest（`python -m pytest tests`）、ruff 静态检查（`python -m ruff check openbase tests`）、覆盖率（`python -m pytest --cov=openbase`）；Step 4/5 文档产出；版本发布（Release Note、git tag v1.4.3、双远程推送） |
| 验收标准 | AC-143-07-1 全量回归通过率 ≥95%（无 P0/P1 未闭环）；AC-143-07-2 覆盖率 ≥80%；AC-143-07-3 Step 4/5 文档齐备且发布闭环（tag v1.4.3 推送） |

## 4. 业务流程与逻辑

### 4.1 OpenLLM 对接主流程

```
运维启动 OpenLLM（PORT=8001）→ /health 健康检查通过
  → OpenBase 配置 llm_api_key / llm_upstream_base=http://127.0.0.1:8001
  → 用户登录 OpenBase（JWT）
  → 前端请求 OpenBase llm-proxy（携带 OpenBase JWT）
  → proxy 注入 Authorization: Bearer sk-openllm-...（OpenBase 持有）
  → OpenLLM 统一网关 /openllm/v1/* 校验 API Key
  → 模型列表/详情/对话（含 SSE 流式）真实返回
  → proxy 统一响应 {code,message,data,timestamp}（SSE 端点逐事件透传）→ 前端
```

### 4.2 认证决策分支（BL-143-02）

```
OpenBase 侧访问 OpenLLM：
  ├─ 主通道（本版本实现）：API Key 注入
  │    OpenBase 持有 sk-openllm- 服务 Key → Authorization: Bearer 注入
  │    （OpenLLM 不支持 X-API-Key 头，必须 Bearer）
  └─ 备选通道（P2 评估）：JWT 共享
       需共享 SECRET_KEY + OpenLLM 平台用户映射 → 复杂度高，本版本仅调研登记
```

### 4.3 对话流式（SSE）透传逻辑

```
前端 POST /api/v1/llm-proxy/chat/stream（OpenBase JWT）
  → proxy 注入 API Key → OpenLLM /openllm/v1/chat/stream
  → SSE 事件：event: routing → event: chunk（重复） → event: done
  → proxy 逐事件透传（不包装、不缓冲）→ 前端 EventSource/fetch-stream 消费
  → 上游中断/异常：透传 error 事件或断开连接，前端可重试
```

## 5. 数据模型与接口定义

### 5.1 配置项（OpenBase settings 新增）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `llm_api_key` | 空（.env 必填） | OpenBase 持有的 OpenLLM 服务 API Key（sk-openllm- 前缀） |
| `llm_upstream_base` | `http://127.0.0.1:8001` | OpenLLM 上游基地址（8001 端口） |
| `llm_upstream_timeout` | `20.0` | 上游请求超时（秒），SSE 场景需放宽/按流处理 |

### 5.2 OpenBase llm-proxy 接口规范（本版本新增）

| 方法 | OpenBase 路径 | 上游目标 | 说明 | 认证 |
|------|---------------|----------|------|------|
| GET | /api/v1/llm-proxy/models | GET /openllm/v1/models | 模型列表 | OpenBase JWT |
| GET | /api/v1/llm-proxy/models/{model_id} | GET /api/v1/providers/models/{model_id}（等价映射） | 模型详情 | OpenBase JWT |
| POST | /api/v1/llm-proxy/chat | POST /openllm/v1/chat | 对话（聚合端点，非流式） | OpenBase JWT |
| POST | /api/v1/llm-proxy/chat/stream | POST /openllm/v1/chat/stream | 对话流式（SSE 逐事件透传） | OpenBase JWT |
| GET | /api/v1/llm-proxy/health | GET /openllm/v1/health | 上游健康透传 | OpenBase JWT |
| GET/POST | /api/v1/llm-proxy/conversations[/{id}[/messages]] | /api/v1/conversations* | 会话列表/详情/消息（对话管理页） | OpenBase JWT |

> proxy 内部：注入 `Authorization: Bearer <llm_api_key>` → 转发 OpenLLM 8001；非 SSE 端点统一 `{code,message,data,timestamp}` 响应；SSE 端点逐事件透传。

### 5.3 上游错误码映射

| OpenLLM 网关错误码 | 含义 | OpenBase 侧映射 |
|--------------------|------|-----------------|
| 1001 | 未认证/Token 失效 | code=1001，HTTP 401 |
| 1003 | 限流超限 | code=1003，HTTP 429 |
| 1004 | 无可用模型 | code=1004，HTTP 404 |
| 2001 | 资源不存在 | code=2001，HTTP 404 |
| 5001 | 内部错误 | code=5001，HTTP 500 |

## 6. 非功能需求

| 类别 | 指标 |
|------|------|
| 性能 | llm-proxy 非流式转发 P95 延迟 ≤ 500ms（不含 OpenLLM 处理）；SSE 首包（routing 事件）P95 ≤ 1s；模型列表接口 P95 ≤ 300ms |
| 安全 | OpenLLM API Key 不落前端/不落日志/不硬编码（settings + .env）；OpenBase JWT 鉴权统一拦截（proxy 未认证 401）；请求头不记录完整 Authorization |
| 可靠性 | 上游不可达返回 502 级错误（SYS_UPSTREAM_ERROR），不崩溃；SSE 中断可重试；错误统一 BaseError 格式 {code,message,detail,request_id}（OpenBase 侧） |
| 兼容性 | 前端不接触 OpenLLM 密钥；SSE 事件格式（routing/chunk/done）与 OpenAI 流式（chat/completions）不冲突；既有 OpenMemory proxy / 网关服务发现无回归 |
| 可维护性 | llm-proxy 代码结构对标 memory_proxy（认证注入/转发/响应适配三函数拆分）；配置项集中 settings；模块注册进 enabled modules |

## 7. 数据需求

| 实体/数据 | 说明 | 来源 | 生命周期 |
|-----------|------|------|----------|
| OpenLLM 模型数据 | 模型列表/详情（只读消费） | OpenLLM 上游 | 运行时读取，不落 OpenBase 库 |
| OpenLLM 会话数据 | 会话列表/详情/消息（经 proxy 读写） | OpenLLM 上游 | 运行时读写，不落 OpenBase 库（OpenLLM 侧 PG 持久化） |
| llm_api_key | OpenLLM 服务密钥 | .env 配置 | 仅 OpenBase 后端持有，随配置生命周期管理 |

> 本版本无新增 OpenBase 本地数据表；数据全部消费 OpenLLM 上游（OpenLLM 自身 PG/Redis 持久化）。

## 8. 权限与安全需求

| 需求 | 说明 |
|------|------|
| 认证边界 | OpenBase JWT 为唯一前端入口认证；proxy 内层注入 OpenLLM API Key；前端永不接触 llm_api_key |
| 权限控制 | proxy 端点要求已登录用户（get_current_user）；本版本不新增细粒度权限点（沿用现有 RBAC 体系，admin 可管理、登录用户可访问） |
| 审计 | proxy 转发关键操作记录审计日志（调用方 user_id、目标端点、HTTP 状态）；不记录 Authorization 头完整值 |
| 安全合规 | 密钥不入 git（.env* 排除，AGENTS.md §6）；日志脱敏；输入校验沿用 Pydantic schema |

## 9. UI/UX 需求

| 页面 | 需求 |
|------|------|
| 模型管理页（Models.vue） | 真实数据表格（名称/Provider/类型/能力/定价/状态）；搜索/状态筛选保留；新增/编辑/删除按 OpenLLM 能力适配（本版本以列表/详情为主）；加载态与错误态（错误提示 + 重试） |
| 对话管理页（Conversations.vue） | 真实会话列表（标题/模型/消息数/时间/Token）；新建会话/进入聊天（含 SSE 流式展示）/归档/删除；加载态与错误态 |
| 一致性 | 沿用统一前端 Design Token 与组件库（el-table/el-dialog/el-tag）；页面工具栏样式与 v1.4.2 记忆管理页一致 |

## 10. 接口与集成需求

| 集成对象 | 方向 | 契约要点 |
|----------|------|----------|
| OpenLLM 统一网关（/openllm/v1/*） | OpenBase→OpenLLM | 双通道鉴权（本版本 API Key 通道）；统一响应 {code,message,data}；错误码 1001/1003/1004/2001/5001；SSE 事件 routing/chunk/done |
| OpenLLM 会话 API（/api/v1/conversations） | OpenBase→OpenLLM | JWT 通道；标准 REST（列表/详情/创建/归档/删除/消息）；响应为 Pydantic 模型直出（非统一包装），proxy 侧需适配 |
| OpenLLM 健康（/health、/openllm/v1/health） | OpenBase→OpenLLM | 运维探测；免鉴权 |
| OpenBase 前端 | 前端→OpenBase proxy | OpenBase JWT；统一响应 {code,message,data,timestamp}；SSE 逐事件透传 |
| 网关服务发现（现有骨架） | OpenBase 内部 | openllm 服务注册/探测沿用，本版本扩展业务转发能力（不改造发现机制） |

## 11. 约束、边界和排除项

| 项 | 内容 |
|----|------|
| 排除 | OpenRAG/DPS 对接（v1.4.4/v1.4.5）；四系统统一集成测试（v1.5）；R-376/R-377（v1.5） |
| 排除 | OpenLLM 全部前端功能补全（R-301~R-312 等历史条目）——本版本仅接入核心可走查页（模型/对话 2 页） |
| 排除 | JWT 共享签发方案落地（P2 评估，仅调研登记，不实现） |
| 约束 | 不得扩大 Step 0 已批准范围（R-379 拆解 7 条 Backlog 为界） |
| 约束 | 技术约束：OpenLLM API Key 仅 Bearer 传递（不支持 X-API-Key 头）；SSE 事件格式以 /openllm/v1/chat/stream 为准 |
| 假设 | OpenLLM 后端本机可启动（PG/Redis 依赖可用）；OpenLLM 侧已存在可用服务级 API Key（或可创建） |
| 开放问题 | OQ-143-1：OpenLLM 平台 JWT 用户映射（sub=OpenLLM user.id）与 OpenBase 用户体系的对应关系——本版本走 API Key 通道规避，后续版本评估；OQ-143-2：模型写操作（新增/编辑/删除）依赖 OpenLLM 端点能力，联调确认后纳入任务书或 P2 |

## 12. 优先级确认

| Backlog ID | 优先级 | 需求 | 本版本范围 |
|-----------|:------:|------|-----------|
| BL-143-01 | P1 | OpenLLM 服务部署 | 必须（M1） |
| BL-143-02 | P1 | 认证适配 | 必须（M2） |
| BL-143-03 | P1 | llm-proxy 转发适配 | 必须（M2） |
| BL-143-04 | P1 | 前端 2 页真实化 | 必须（M3） |
| BL-143-05 | P1 | 双系统联调 | 必须（M4） |
| BL-143-06 | P2 | 对接完善任务书 | 应当（与 05 合并执行） |
| BL-143-07 | P1 | 收尾与还债 | 必须（M4） |

## 13. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | RA-OpenBase-Dev | 初始创建：R-379 拆解 7 条 Backlog 功能需求（AC-143-01~07）、业务流程、接口规范、非功能/数据/权限/UI/接口需求、约束排除项、优先级确认 |

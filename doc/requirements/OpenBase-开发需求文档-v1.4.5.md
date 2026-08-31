# OpenBase 开发需求文档 - v1.4.5

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.5 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | RA-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 存放 | doc/requirements/ |

---

## 1. 版本概述

| 项 | 内容 |
|----|------|
| 版本主题 | DPS 系统对接（1.4.x 逐个系统对接线第 3 站，共 4 站） |
| 需求来源 | 候选需求池 §1.11：R-381（VC-011，P1） |
| Backlog | BL-145-01~06（6 P1），见《OpenBase-本版本Backlog-v1.4.5.md》 |
| 基线 | v1.4.4（Step 5 已部署发布，全流程闭环） |
| 关键外部依据 | DPS v2.7.1（`D:\Trae CN\myproject\Dev\DPS`，调研实测）；v1.4.4 R-380 对接模式（差异：DPS Header 身份认证 + 无 SSE） |

## 2. 业务目标

| 目标 ID | 业务目标 | 用户目标 | 成功指标（映射 Step 0 G1~G5） |
|---------|----------|----------|-------------------------------|
| BO-145-1 | DPS 服务就绪 | 运维可一键启动双系统 | G1：8030 健康检查通过、无端口冲突 |
| BO-145-2 | 认证边界打通 | 用户用 OpenBase 凭据访问 DPS 能力 | G2：dps-proxy 未认证 401；身份头注入正确；DPS 认证补强登记任务书 |
| BO-145-3 | 画像/RAG 能力经 OpenBase 代理开放 | 前端/调用方不直连 DPS | G3：≥6 proxy 端点、统一响应、{detail} 归一化 |
| BO-145-4 | 画像模块页真实化 | 用户可走查真实画像数据 | G4：2 页真实 API |
| BO-145-5 | 双系统联调闭环 | 集成工程师验收通过 | G5：画像→标签→报表闭环、回归 ≥95%、覆盖率 ≥80% |

## 3. 身份头映射预研结论（Step 0 评审要求的 Step 1 关键输入）

DPS HTTP API 要求请求必带 `X-Org-ID` + `X-Tenant-ID` + `X-User-ID`（Header 身份直传 + RBAC 中间件），组织/租户须预存在库。OpenBase 侧身份来源（代码核验）：

| DPS 请求头 | OpenBase 来源 | 类型 | 说明 |
|-----------|--------------|------|------|
| X-User-ID | `get_current_user()["id"]`（JWT sub） | int→str | OpenBase 用户 ID |
| X-Tenant-ID | JWT payload `tenant_id`（缺省回退 `org_id`） | str | 租户标识 |
| X-Org-ID | JWT payload extra `org_id`（= 登录用户 tenant_value） | str | 组织标识；缺省回退 tenant_id |
| X-User-Role | JWT payload extra `role`（缺省 "user"） | str | 角色（可选） |

> **映射规则**：dps-proxy 从 OpenBase JWT/用户上下文构造四头注入上游（对标 memory-proxy 身份头注入模式）；OpenBase 组织=租户同值语义 → DPS 侧组织/租户实体须预建（种子数据，BL-145-01）或配置映射表（dps_org_map/dps_tenant_map）对齐；联调确认 1:1 直传可行性，不成立时配置化兜底（OQ-145-1）。

## 4. 功能需求

### 4.1 BL-145-01 DPS 服务部署（P1，Phase 1）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 运维, I want 以 API_PORT=8030 启动 DPS v2.7.1 后端, so that DPS 与 OpenBase（8000）并存且可真实访问 |
| 功能描述 | 基于本机 DPS 项目部署：`cd src; python -m uvicorn rest_api.app:app`（PYTHONPATH=src），环境变量 `API_PORT=8030` 覆盖默认 8000（注意 DPS 端口变量名为 API_PORT，无 PORT/DPS_API_PORT）；健康检查 `/health/liveness`（+ `/health/readiness`，白名单免鉴权）；组织/租户种子数据（platform.organization/tenant active 状态）供身份头校验；SQLITE_FALLBACK 可用（数据库降级） |
| 验收标准 | AC-145-01-1 DPS 8030 启动成功且 `/health/liveness` 返回 200（status=healthy）；AC-145-01-2 `/health/readiness` 可用（database/redis 检查）；AC-145-01-3 组织/租户种子数据就绪（身份头校验通过前提）；AC-145-01-4 OpenBase 8000 与 DPS 8030 并存无冲突 |

### 4.2 BL-145-02 认证边界与身份头注入（P1，Phase 2）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 平台管理员, I want OpenBase 统一认证门禁保护 dps-proxy 并自动注入身份头, so that DPS Header 身份认证的能力不暴露给未授权调用方 |
| 功能描述 | **现状事实**：DPS HTTP API 无标准登录（`/api/v2/auth/login` 仅白名单未实现），认证为「Header 身份直传 + RBAC 中间件」——X-Org-ID/X-Tenant-ID/X-User-ID 必传且组织/租户须存在。本版本方案：OpenBase dps-proxy 为**唯一认证入口**（OpenBase JWT get_current_user 门禁，未认证 401）；**身份头注入**：按 §3 映射规则从 OpenBase JWT/用户上下文构造 X-User-ID/X-Tenant-ID/X-Org-ID（+X-User-Role）注入上游；DPS 侧认证体系落地登记任务书 |
| 验收标准 | AC-145-02-1 dps-proxy 未认证请求返回 401（AUTH_401）；AC-145-02-2 认证后请求正常转发且四头注入正确（上游校验通过）；AC-145-02-3 DPS 侧认证补强需求已登记任务书 |

### 4.3 BL-145-03 dps-proxy 转发适配（P1，Phase 2）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 前端/调用方, I want 通过 OpenBase dps-proxy 访问 DPS 画像能力, so that 无需直连 DPS 且认证统一 |
| 功能描述 | OpenBase 侧新增 `dps_proxy` 模块（对标 rag_proxy 模式，差异：无 SSE 透传 + 身份头注入）：核心端点转发——画像列表（GET /portrait/list）、画像详情（GET /portrait/{person_id}）、画像计算（POST /portrait/calculate）、标签分类（GET /tags/categories）、报表概览（GET /reports/overview）、批量任务状态（GET /batch/import/{task_id}/status）、审计日志（GET /audit/logs）、健康透传（GET /health/liveness）；统一响应 {code,message,data,timestamp} 适配；**错误归一化**：DPS 成功 `{code:200,message,data}` 与 FastAPI `{detail}`（404 例外）统一提取（body.code > body.detail > HTTP 状态码）；未认证 401；身份头注入（§3） |
| 验收标准 | AC-145-03-1 核心业务端点经 OpenBase 代理 ≥6 个；AC-145-03-2 响应统一适配（2xx 返回 {code:0,message:"success",data,timestamp}）；AC-145-03-3 {detail} 错误归一化正确（404 → 响应 code 提取 detail，HTTP 404）；AC-145-03-4 未认证请求 401；AC-145-03-5 上游不可达返回 502 级错误（SYS_UPSTREAM_ERROR） |

### 4.4 BL-145-04 前端画像页真实化（P1，Phase 3）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 用户, I want 在统一前端查看真实画像数据, so that DPS 画像能力可视化可走查 |
| 功能描述 | DPS 画像模块核心页 mock 替换真实 API（走 OpenBase dps-proxy，前端不直连 DPS）：画像列表页（真实画像列表 + 加载/错误态）、画像详情页（画像维度展示 + 标签 + 风险等级） |
| 验收标准 | AC-145-04-1 画像列表页展示真实数据（经 proxy，非 mock）；AC-145-04-2 画像详情页真实展示（经 proxy）；AC-145-04-3 前端代码无 DPS 上游地址硬编码（全部经 proxy）；AC-145-04-4 两页加载失败有错误提示与重试（非白屏） |

### 4.5 BL-145-05 双系统联调（P1，Phase 4）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 集成工程师, I want OpenBase 统一认证 + 身份头注入 → DPS 画像→标签→报表真实闭环, so that 对接完成可验收 |
| 功能描述 | 联调闭环：登录（OpenBase）→ dps-proxy → 身份头注入 → 画像列表真实返回 → 画像详情 → 标签分类 → 报表概览真实返回；集成测试（API 级）+ UAT 走查（页面级）；联调发现的 DPS 侧缺口登记任务书（BL-145-06） |
| 验收标准 | AC-145-05-1 画像列表经 proxy 真实返回（200 + items）；AC-145-05-2 画像详情经 proxy 真实返回（维度数据）；AC-145-05-3 标签/报表经 proxy 真实返回；AC-145-05-4 UAT 走查通过（页面级） |

### 4.6 BL-145-06 收尾与还债（P1，Phase 4）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 开发者, I want 全量回归、覆盖率与还债一键执行, so that 发布质量可量化 |
| 功能描述 | 复用 v1.4.4 测试基座与回归脚本化：全量 pytest、ruff 静态检查、覆盖率（--cov）；**还债 TD-新增-011**：llm.ts sendChatStream 对齐 rag.ts 的 fetch adapter（修复浏览器端 SSE 假流式，验证 routing/chunk/done 逐事件渲染）；Step 4/5 文档产出；版本发布（Release Note、git tag v1.4.5、双远程推送） |
| 验收标准 | AC-145-06-1 全量回归通过率 ≥95%（无 P0/P1 未闭环）；AC-145-06-2 覆盖率 ≥80%；AC-145-06-3 TD-新增-011 还债完成（llm.ts SSE 真流式验证）；AC-145-06-4 Step 4/5 文档齐备且发布闭环（tag v1.4.5 推送） |

## 5. 业务流程与逻辑

### 5.1 DPS 对接主流程

```
运维启动 DPS（API_PORT=8030）→ /health/liveness 健康检查通过
  → OpenBase 配置 dps_upstream_base=http://127.0.0.1:8030 + 身份映射配置
  → 用户登录 OpenBase（JWT：sub/tenant_id/org_id/role）
  → 前端请求 OpenBase dps-proxy（携带 OpenBase JWT）
  → proxy 校验 JWT（未认证 401）→ 构造四头（X-User-ID/X-Tenant-ID/X-Org-ID/X-User-Role）注入
  → 转发 DPS 8030 → 画像列表/详情、标签、报表真实返回
  → proxy 统一响应 {code,message,data,timestamp}（{detail} 归一化）→ 前端
```

### 5.2 认证边界决策

```
DPS HTTP API 无标准登录（Header 身份直传 + RBAC）：
  ├─ 本版本：OpenBase dps-proxy = 唯一认证入口（JWT 门禁 + 身份头注入）
  │    └─ 前端/调用方 → OpenBase JWT → proxy 构造四头 → DPS（身份校验）
  └─ 后续：DPS 侧认证体系落地（任务书登记）
       组织/租户校验依赖种子数据或映射表（OQ-145-1）
```

## 6. 数据模型与接口定义

### 6.1 配置项（OpenBase settings 新增）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `dps_upstream_base` | `http://127.0.0.1:8030` | DPS 上游基地址（8030 端口） |
| `dps_upstream_timeout` | `20.0` | 非流式请求超时（秒） |
| `dps_default_org_id` | `""` | X-Org-ID 兜底值（JWT org_id 缺失时） |
| `dps_default_tenant_id` | `""` | X-Tenant-ID 兜底值（JWT tenant_id 缺失时） |
| `dps_org_map` | `""` | 组织映射表（OpenBase→DPS，JSON，可选） |
| `dps_tenant_map` | `""` | 租户映射表（OpenBase→DPS，JSON，可选） |

> 无 `dps_api_key`（DPS Header 身份认证，无密钥通道）。

### 6.2 OpenBase dps-proxy 接口规范（本版本新增）

| 方法 | OpenBase 路径 | 上游目标 | 说明 | 认证 |
|------|---------------|----------|------|------|
| GET | /api/v1/dps-proxy/portraits | GET /api/v2/portrait/list | 画像列表 | OpenBase JWT |
| GET | /api/v1/dps-proxy/portraits/{person_id} | GET /api/v2/portrait/{person_id} | 画像详情 | OpenBase JWT |
| POST | /api/v1/dps-proxy/portraits/calculate | POST /api/v2/portrait/calculate | 画像计算 | OpenBase JWT |
| GET | /api/v1/dps-proxy/tags/categories | GET /api/v2/tags/categories | 标签分类 | OpenBase JWT |
| GET | /api/v1/dps-proxy/reports/overview | GET /api/v2/reports/overview | 报表概览 | OpenBase JWT |
| GET | /api/v1/dps-proxy/batch/tasks/{task_id} | GET /api/v2/batch/import/{task_id}/status | 批量任务状态 | OpenBase JWT |
| GET | /api/v1/dps-proxy/audit/logs | GET /api/v2/audit/logs | 审计日志 | OpenBase JWT |
| GET | /api/v1/dps-proxy/health | GET /health/liveness | 上游健康透传 | OpenBase JWT |

> proxy 内部：校验 OpenBase JWT → 构造四头注入 → 转发 DPS 8030；非 SSE 端点统一 {code,message,data,timestamp}；{detail} 错误归一化。

### 6.3 错误归一化映射

| DPS 错误形态 | 提取 | OpenBase 响应 |
|--------------|------|---------------|
| {code: 非200, message, data} | body.code / body.message | code 透传 + HTTP 对应 |
| {detail: "xxx"}（FastAPI 404） | detail 字符串 | code=HTTP 状态码，message=detail |
| 网络不可达 | - | BaseError(SYS_UPSTREAM_ERROR) → 502 |

## 7. 非功能需求

| 类别 | 指标 |
|------|------|
| 性能 | dps-proxy 非流式转发 P95 ≤ 500ms（不含 DPS 处理）；画像列表 P95 ≤ 300ms |
| 安全 | OpenBase JWT 唯一认证入口（dps-proxy 未认证 401）；身份头由 OpenBase 侧构造（不透传前端自定义）；日志脱敏 |
| 可靠性 | 上游不可达 502（SYS_UPSTREAM_ERROR）；错误统一 BaseError 格式 |
| 兼容性 | 前端不直连 DPS；既有 llm_proxy/rag_proxy/网关无回归；DPS 无 SSE（不适用 SSE 透传） |
| 可维护性 | dps_proxy 模块结构对标 rag_proxy（认证门禁/转发/响应适配三函数）；配置集中 settings（dps_* 前缀） |

## 8. 数据需求

| 实体/数据 | 说明 | 来源 | 生命周期 |
|-----------|------|------|----------|
| DPS 画像/标签/报表数据 | 画像计算/查询/标签/报表（经 proxy 读写消费） | DPS 上游 | 运行时读写，不落 OpenBase 库 |
| 身份映射数据 | 组织/租户种子 + 映射表（dps_org_map/dps_tenant_map） | DPS + OpenBase 配置 | 部署时配置 |

> 本版本无新增 OpenBase 本地数据表。

## 9. 权限与安全需求

| 需求 | 说明 |
|------|------|
| 认证边界 | OpenBase JWT 为唯一前端入口认证（dps-proxy get_current_user）；身份头由 proxy 构造注入（前端不可伪造） |
| 权限控制 | dps-proxy 端点要求已登录用户；本版本不新增细粒度权限点（沿用 RBAC） |
| 审计 | proxy 转发关键操作记录审计日志（user_id/目标端点/HTTP 状态） |
| 安全合规 | 密钥不入 git；日志脱敏；身份头不记录完整值（X-User-Role 等可记录角色） |

## 10. UI/UX 需求

| 页面 | 需求 |
|------|------|
| 画像列表页 | 真实画像列表（姓名/标签/风险等级/更新时间）；加载态/错误态（错误提示 + 重试） |
| 画像详情页 | 画像维度展示（六维雷达数据 + 标签 + 风险等级 + 关联信息）；加载态/错误态 |
| 一致性 | 沿用统一前端 Design Token 与组件库 |

## 11. 接口与集成需求

| 集成对象 | 方向 | 契约要点 |
|----------|------|----------|
| DPS 画像 API（/api/v2/portrait*） | OpenBase→DPS | Header 身份认证（四头注入）；{code:200,message,data} 成功 + {detail} 404 |
| DPS 标签/报表 API（/api/v2/tags、/reports） | OpenBase→DPS | 同上 |
| DPS 批量/审计（/api/v2/batch、/audit） | OpenBase→DPS | 同上 |
| DPS 健康（/health/liveness） | OpenBase→DPS | 免鉴权（白名单） |
| OpenBase 前端 | 前端→OpenBase proxy | OpenBase JWT；统一响应 |
| OpenBase JWT 身份 | OpenBase 内部 | sub/tenant_id/org_id/role → 四头注入（§3） |

## 12. 约束、边界和排除项

| 项 | 内容 |
|----|------|
| 排除 | 四系统统一集成测试（v1.5）；R-376/R-377（v1.5） |
| 排除 | DPS 前端功能补全（R-322~R-326/R-331/R-359 历史条目）——本版本仅接入核心可走查页（画像列表/详情 2 页） |
| 排除 | DPS 侧认证体系落地（本版本 OpenBase JWT 门禁 + 身份头注入兜底，认证实现登记任务书） |
| 排除 | 四维身份专项（已挂起）——本版本身份头注入用既有 JWT 字段，四维统一方案专项处理 |
| 约束 | 不得扩大 Step 0 已批准范围（R-381 拆解 6 条 Backlog 为界） |
| 约束 | 技术约束：DPS 端口变量 API_PORT（非 PORT）；Header 身份认证（四头必传）；无 SSE；{detail} 归一化 |
| 假设 | DPS 后端本机可启动（SQLite 降级）；DPS 组织/租户可种子（联调确认） |
| 开放问题 | OQ-145-1：组织/租户映射方式（1:1 直传 vs 映射表）——联调确认；OQ-145-2：DPS AI 画像计算依赖模型服务（AI_MODEL_SERVICE_URL）——联调确认 |

## 13. 优先级确认

| Backlog ID | 优先级 | 需求 | 本版本范围 |
|-----------|:------:|------|-----------|
| BL-145-01 | P1 | DPS 服务部署 | 必须（M1） |
| BL-145-02 | P1 | 认证边界与身份头注入 | 必须（M2） |
| BL-145-03 | P1 | dps-proxy 转发适配 | 必须（M2） |
| BL-145-04 | P1 | 前端画像页真实化 | 必须（M3） |
| BL-145-05 | P1 | 双系统联调 | 必须（M4） |
| BL-145-06 | P1 | 收尾与还债 | 必须（M4） |

## 14. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | RA-OpenBase-Dev | 初始创建：R-381 拆解 6 条 Backlog 功能需求（AC-145-01~06）、身份头映射预研结论（§3）、业务流程（对接/认证边界）、接口规范（8 端点 + 错误归一化）、非功能/数据/权限/UI/接口需求、约束排除项、优先级确认 |

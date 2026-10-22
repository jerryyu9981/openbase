# 全栈功能级审计汇总（生成物）

- 审计时间：2026-10-22T17:59:06.703Z ~ 2026-10-22T18:02:27.436Z
- 前端地址：http://127.0.0.1:5173
- 页面总数：77；PASS 76 / FAIL 1
- API 失败次数：1

## 一、失败端点聚合

| 端点 | 命中次数 |
| --- | --- |
| GET /api/v1/llm-proxy/conversations → 500 | 1 |

## 二、逐页 API 调用面

| 服务 | 页面 | 结果 | 调用的接口 | 失败 | 交互 |
| --- | --- | --- | --- | --- | --- |
| openbase | 仪表盘<br>`/dashboard` | PASS | （无） | - | - |
| openbase | 租户管理<br>`/platform/identity/tenants` | PASS | GET /api/v1/tenants | - | - |
| openbase | 角色与权限<br>`/platform/identity/roles` | PASS | （无） | - | - |
| openbase | 组织/团队/用户<br>`/platform/identity/org` | PASS | GET /api/v1/users | - | - |
| openbase | 工作空间<br>`/platform/identity/workspaces` | PASS | （无） | - | - |
| openbase | 用户管理<br>`/platform/identity/users` | PASS | GET /api/v1/users | - | button:刷新 |
| openbase | 记忆管理席位<br>`/platform/identity/memory-admin` | PASS | GET /api/v1/memory-proxy/monitor<br>GET /api/v1/memory-proxy/memories | - | tab:记忆概览<br>tab:运行监控<br>tab:记忆维护 |
| openbase | 注册/找回密码<br>`/platform/identity/auth-ext` | PASS | （无） | - | tab:注册<br>tab:找回密码<br>button:重置密码 |
| openbase | 画像数据权限<br>`/platform/identity/dps-permissions` | PASS | （无） | - | - |
| openbase | 全局配置<br>`/platform/config/general` | PASS | （无） | - | button:刷新 |
| openbase | 模块开关<br>`/platform/config/modules` | PASS | （无） | - | button:刷新 |
| openbase | API 密钥<br>`/platform/config/api-keys` | PASS | GET /api/v1/auth/api-keys | - | button:刷新<br>button:详情 |
| openbase | 画像接口限流<br>`/platform/config/rate-limits` | PASS | （无） | - | - |
| openbase | 日志中心<br>`/platform/observability/logs` | PASS | GET /api/v1/logs/search<br>GET /api/v1/logs/facets | - | button:检索<br>button:重置 |
| openbase | 测试记录<br>`/platform/observability/test-records` | PASS | （无） | - | - |
| openbase | 统一监控<br>`/platform/observability/monitoring` | PASS | （无） | - | - |
| openbase | 成本分析<br>`/platform/observability/monitoring/costs` | PASS | （无） | - | - |
| openbase | 告警中心<br>`/platform/observability/monitoring/alerts` | PASS | （无） | - | tab:告警规则<br>tab:告警历史<br>button:详情<br>button:详情<br>button:详情<br>button:详情<br>button:详情 |
| openbase | 链路追踪<br>`/platform/observability/monitoring/traces` | PASS | （无） | - | - |
| openbase | 预算管理<br>`/platform/observability/monitoring/budgets` | PASS | （无） | - | - |
| openbase | GPU 资源<br>`/platform/observability/gpu` | PASS | （无） | - | - |
| openbase | 用量统计<br>`/platform/observability/usage` | PASS | （无） | - | button:查询 |
| openbase | 计费<br>`/platform/observability/billing` | PASS | （无） | - | button:详情<br>button:详情<br>button:详情 |
| openbase | 服务发现与编排<br>`/platform/observability/service-discovery` | PASS | GET /api/v1/services | - | button:刷新<br>button:连通性检测 |
| openbase | 聚合网关测试<br>`/platform/observability/gateway-test` | PASS | （无） | - | button:重置 |
| openbase | 应用调用记录<br>`/platform/observability/app-calls` | PASS | （无） | - | - |
| openbase | 画像系统监控<br>`/platform/observability/dps-monitor` | PASS | （无） | - | - |
| openbase | 提供商管理<br>`/platform/governance/providers` | PASS | GET /api/v1/proxy/openllm/api/v1/providers<br>GET /api/v1/proxy/openllm/api/v1/providers/11111111-1111-1111-1111-111111111102/models<br>GET /api/v1/proxy/openllm/api/v1/providers/11111111-1111-1111-1111-111111111103/models<br>GET /api/v1/proxy/openllm/api/v1/providers/11111111-1111-1111-1111-111111111101/models | - | button:刷新 |
| openbase | 模型分类<br>`/platform/governance/model-categories` | PASS | （无） | - | - |
| openbase | 路由策略<br>`/platform/governance/routing` | PASS | （无） | - | tab:路由策略<br>tab:熔断器 |
| openbase | 熔断器<br>`/platform/governance/circuit-breakers` | PASS | （无） | - | tab:路由策略<br>tab:熔断器 |
| openbase | 模型部署<br>`/platform/governance/deploy` | PASS | （无） | - | - |
| openbase | 下载管理<br>`/platform/governance/downloads` | PASS | （无） | - | button:刷新 |
| openbase | 工具调用监控<br>`/platform/governance/tool-calls` | PASS | （无） | - | button:查询<br>button:刷新 |
| openbase | A/B 测试<br>`/platform/governance/ab-tests` | PASS | （无） | - | button:详情<br>button:详情<br>button:详情 |
| openbase | Prompt 模板<br>`/platform/governance/prompt-templates` | PASS | （无） | - | - |
| openbase | Prompt 实验<br>`/platform/governance/prompt-experiments` | PASS | （无） | - | - |
| openbase | 文档中心<br>`/platform/developers/docs` | PASS | （无） | - | - |
| openbase | EdgeRouter 与适配器<br>`/platform/developers/edgerouter` | PASS | GET /api/v1/proxy/openllm/api/v1/edge/status<br>GET /api/v1/proxy/openllm/api/v1/edge/health<br>GET /api/v1/proxy/openllm/api/v1/edge/adapters<br>GET /api/v1/proxy/openllm/api/v1/edge/organizations<br>GET /api/v1/proxy/openllm/api/v1/edge/audit/logs | - | tab:概览<br>tab:组织管理<br>tab:配额管理<br>tab:适配器管理<br>tab:路由审计<br>button:刷新 |
| openbase | 插件管理<br>`/platform/developers/plugins` | PASS | （无） | - | - |
| openbase | 画像 API 管理<br>`/platform/developers/dps-api` | PASS | （无） | - | - |
| openbase | 知识库管理后台<br>`/platform/developers/knowledge-admin` | PASS | GET /api/v1/rag-proxy/collections<br>GET /api/v1/rag-proxy/health | - | button:刷新 |
| openbase | 知识库 API 控制台<br>`/platform/developers/knowledge-console` | PASS | （无） | - | tab:概览<br>tab:API 调试器<br>tab:接口文档<br>tab:性能监控 |
| openbase | 个人设置<br>`/personal/settings` | PASS | （无） | - | - |
| openllm | 模型管理<br>`/openllm/models` | PASS | GET /api/v1/llm-proxy/models | - | button:详情<br>button:详情<br>button:详情<br>button:详情<br>button:详情<br>button:详情<br>button:详情<br>button:详情<br>button:详情 |
| openllm | 本地模型<br>`/openllm/models/local` | PASS | （无） | - | - |
| openllm | 模型对比<br>`/openllm/models/comparison` | PASS | （无） | - | - |
| openllm | 开源模型市场<br>`/openllm/models/market` | PASS | （无） | - | button:查询 |
| openllm | 我的收藏<br>`/openllm/favorites` | PASS | （无） | - | tab:对话模型 (3)<br>tab:多模态 (2)<br>tab:Embedding (2)<br>tab:代码生成 (1) |
| openllm | AI 应用<br>`/openllm/apps` | PASS | GET /api/v1/ai-apps | - | - |
| openllm | 创建应用<br>`/openllm/apps/new` | PASS | （无） | - | - |
| openllm | Playground<br>`/openllm/playground` | PASS | GET /api/v1/llm-proxy/models | - | - |
| openllm | 对话管理<br>`/openllm/conversations` | FAIL | GET /api/v1/llm-proxy/models<br>GET /api/v1/llm-proxy/conversations | GET /api/v1/llm-proxy/conversations → 500 | - |
| openllm | 模型对比推荐<br>`/openllm/recommend` | PASS | （无） | - | button:检索 |
| openllm | 报表趋势<br>`/openllm/reports-trend` | PASS | （无） | - | - |
| openrag | 知识库<br>`/knowledge/list` | PASS | GET /api/v1/rag-proxy/collections | - | button:刷新 |
| openrag | RAG 对话<br>`/knowledge/chat` | PASS | GET /api/v1/rag-proxy/collections | - | button:刷新列表 |
| openmemory | 记忆列表<br>`/memory/list` | PASS | GET /api/v1/memory-proxy/memories | - | - |
| openmemory | 记忆搜索<br>`/memory/search` | PASS | （无） | - | button:搜索 |
| openmemory | 会话管理<br>`/memory/sessions` | PASS | GET /api/v1/memory-proxy/sessions | - | button:刷新 |
| openmemory | 记忆图谱<br>`/memory/graph` | PASS | （无） | - | - |
| openmemory | 衰减配置<br>`/memory/decay` | PASS | GET /api/v1/memory-proxy/decay/config | - | button:重置 |
| openmemory | 写入记忆<br>`/memory/write` | PASS | （无） | - | button:重置 |
| dps | 数据总览<br>`/portrait/overview` | PASS | GET /api/v1/dps-proxy/portraits<br>GET /api/v1/dps-proxy/reports/overview | - | - |
| dps | 画像列表<br>`/portrait/list` | PASS | GET /api/v1/dps-proxy/portraits<br>GET /api/v1/dps-proxy/health<br>GET /api/v1/dps-proxy/reports/overview | - | button:画像查询 |
| dps | 画像搜索<br>`/portrait/search` | PASS | GET /api/v1/dps-proxy/portraits | - | button:查询<br>button:重置 |
| dps | 标签管理<br>`/portrait/tags` | PASS | GET /api/v1/dps-proxy/tags/categories | - | button:刷新 |
| dps | 规则引擎<br>`/portrait/rules` | PASS | （无） | - | tab:画像规则<br>tab:执行任务 |
| dps | 模板族管理<br>`/portrait/dps/templates` | PASS | GET /api/v1/dps-proxy/templates | - | button:查询<br>button:重置 |
| dps | 画像模板新建<br>`/portrait/dps/templates/new` | PASS | GET /api/v1/dps-proxy/templates | - | - |
| dps | 模板包导出/导入<br>`/portrait/dps/template-packages` | PASS | （无） | - | tab:导出<br>tab:导入 |
| dps | 标签血缘反查<br>`/portrait/dps/lineage` | PASS | （无） | - | - |
| dps | 措施建议<br>`/portrait/dps/measures` | PASS | （无） | - | button:查询建议 |
| dps | 评分类型<br>`/portrait/dps/scoring-types` | PASS | GET /api/v1/dps-proxy/scoring-types | - | button:查询 |
| dps | AI 标注候选与复核<br>`/portrait/dps/annotation-adapters` | PASS | （无） | - | - |
| dps | 标注模板管理<br>`/portrait/dps/annotation-templates` | PASS | GET /api/v1/dps-proxy/annotation-templates | - | button:查询<br>button:重置 |
| dps | 标签体系查看<br>`/portrait/dps/tags` | PASS | GET /api/v1/dps-proxy/tags/categories<br>GET /api/v1/dps-proxy/labels | - | - |

## 三、无后端调用页面（前端契约 mock / 静态）

- [openbase] 仪表盘 `/dashboard`
- [openbase] 角色与权限 `/platform/identity/roles`
- [openbase] 工作空间 `/platform/identity/workspaces`
- [openbase] 注册/找回密码 `/platform/identity/auth-ext`
- [openbase] 画像数据权限 `/platform/identity/dps-permissions`
- [openbase] 全局配置 `/platform/config/general`
- [openbase] 模块开关 `/platform/config/modules`
- [openbase] 画像接口限流 `/platform/config/rate-limits`
- [openbase] 测试记录 `/platform/observability/test-records`
- [openbase] 统一监控 `/platform/observability/monitoring`
- [openbase] 成本分析 `/platform/observability/monitoring/costs`
- [openbase] 告警中心 `/platform/observability/monitoring/alerts`
- [openbase] 链路追踪 `/platform/observability/monitoring/traces`
- [openbase] 预算管理 `/platform/observability/monitoring/budgets`
- [openbase] GPU 资源 `/platform/observability/gpu`
- [openbase] 用量统计 `/platform/observability/usage`
- [openbase] 计费 `/platform/observability/billing`
- [openbase] 聚合网关测试 `/platform/observability/gateway-test`
- [openbase] 应用调用记录 `/platform/observability/app-calls`
- [openbase] 画像系统监控 `/platform/observability/dps-monitor`
- [openbase] 模型分类 `/platform/governance/model-categories`
- [openbase] 路由策略 `/platform/governance/routing`
- [openbase] 熔断器 `/platform/governance/circuit-breakers`
- [openbase] 模型部署 `/platform/governance/deploy`
- [openbase] 下载管理 `/platform/governance/downloads`
- [openbase] 工具调用监控 `/platform/governance/tool-calls`
- [openbase] A/B 测试 `/platform/governance/ab-tests`
- [openbase] Prompt 模板 `/platform/governance/prompt-templates`
- [openbase] Prompt 实验 `/platform/governance/prompt-experiments`
- [openbase] 文档中心 `/platform/developers/docs`
- [openbase] 插件管理 `/platform/developers/plugins`
- [openbase] 画像 API 管理 `/platform/developers/dps-api`
- [openbase] 知识库 API 控制台 `/platform/developers/knowledge-console`
- [openbase] 个人设置 `/personal/settings`
- [openllm] 本地模型 `/openllm/models/local`
- [openllm] 模型对比 `/openllm/models/comparison`
- [openllm] 开源模型市场 `/openllm/models/market`
- [openllm] 我的收藏 `/openllm/favorites`
- [openllm] 创建应用 `/openllm/apps/new`
- [openllm] 模型对比推荐 `/openllm/recommend`
- [openllm] 报表趋势 `/openllm/reports-trend`
- [openmemory] 记忆搜索 `/memory/search`
- [openmemory] 记忆图谱 `/memory/graph`
- [openmemory] 写入记忆 `/memory/write`
- [dps] 规则引擎 `/portrait/rules`
- [dps] 模板包导出/导入 `/portrait/dps/template-packages`
- [dps] 标签血缘反查 `/portrait/dps/lineage`
- [dps] 措施建议 `/portrait/dps/measures`
- [dps] AI 标注候选与复核 `/portrait/dps/annotation-adapters`

## 四、静默页面（无调用且无可交互动作）

- [openbase] 仪表盘 `/dashboard`
- [openbase] 角色与权限 `/platform/identity/roles`
- [openbase] 工作空间 `/platform/identity/workspaces`
- [openbase] 画像数据权限 `/platform/identity/dps-permissions`
- [openbase] 画像接口限流 `/platform/config/rate-limits`
- [openbase] 测试记录 `/platform/observability/test-records`
- [openbase] 统一监控 `/platform/observability/monitoring`
- [openbase] 成本分析 `/platform/observability/monitoring/costs`
- [openbase] 链路追踪 `/platform/observability/monitoring/traces`
- [openbase] 预算管理 `/platform/observability/monitoring/budgets`
- [openbase] GPU 资源 `/platform/observability/gpu`
- [openbase] 应用调用记录 `/platform/observability/app-calls`
- [openbase] 画像系统监控 `/platform/observability/dps-monitor`
- [openbase] 模型分类 `/platform/governance/model-categories`
- [openbase] 模型部署 `/platform/governance/deploy`
- [openbase] Prompt 模板 `/platform/governance/prompt-templates`
- [openbase] Prompt 实验 `/platform/governance/prompt-experiments`
- [openbase] 文档中心 `/platform/developers/docs`
- [openbase] 插件管理 `/platform/developers/plugins`
- [openbase] 画像 API 管理 `/platform/developers/dps-api`
- [openbase] 个人设置 `/personal/settings`
- [openllm] 本地模型 `/openllm/models/local`
- [openllm] 模型对比 `/openllm/models/comparison`
- [openllm] 创建应用 `/openllm/apps/new`
- [openllm] 报表趋势 `/openllm/reports-trend`
- [openmemory] 记忆图谱 `/memory/graph`
- [dps] 标签血缘反查 `/portrait/dps/lineage`
- [dps] AI 标注候选与复核 `/portrait/dps/annotation-adapters`
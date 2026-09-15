# OpenBase 路径归属矩阵 - v1.4.6（脚本生成）

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.6 |
| 生成方式 | openbase-ui/scripts/gen_ownership_matrix.mjs（脚本程序化提取，禁人工转写） |
| 生成日期 | 2026-09-15 |
| 来源 | src/core/router/index.ts + src/pages/platform/routes.ts + src/pages/personal/routes.ts + src/modules/<模块>/index.ts + src/core/router/legacyRedirects.ts（重定向唯一事实源） |

## 统计

- 路由条数（不含参数化详情页）：106（声明路由 76 + 旧路径承接条目 30）
- 需重定向（旧路径保持可达）：32
- 平台四域目标页（迁移/归域）：26
- 业务模块本色页（不迁移）：43
- 未登记路径：0（应为 0，AC-146-11-2）
- 个人域目标页（迁移/归域）：1
- 全局静态页（保留，不迁移）：4
- 与 src/core/router/legacyRedirects.ts 条目差异：0（应为 0，重定向单一事实源自校验）

## 全量四列矩阵

| 现路径 | 组件 | 目标域 | 目标路径 | 需重定向 | 说明 |
|--------|------|--------|----------|:--------:|------|
| /platform/config/api-keys | ApiKeys | config | /platform/config/api-keys | 否 | 平台四域目标页（归域） |
| /platform/config/general | ConfigManageView | config | /platform/config/general | 否 | 平台四域目标页（归域） |
| /platform/config/modules | ModuleSwitchView | config | /platform/config/modules | 否 | 平台四域目标页（归域） |
| /platform/developers/docs | DocCenterView | developers | /platform/developers/docs | 否 | 平台四域目标页（归域） |
| /platform/developers/edgerouter | EdgeRouterView | developers | /platform/developers/edgerouter | 否 | 平台四域目标页（归域） |
| /platform/developers/plugins | PluginsView | developers | /platform/developers/plugins | 否 | 平台四域目标页（归域） |
| /platform/identity/auth-ext | AuthExt | identity | /platform/identity/auth-ext | 否 | 平台四域目标页（归域） |
| /platform/identity/memory-admin | MemoryAdminView | identity | /platform/identity/memory-admin | 否 | 平台四域目标页（归域） |
| /platform/identity/org | OrgTeamsUsersView | identity | /platform/identity/org | 否 | 平台四域目标页（归域） |
| /platform/identity/roles | RolesView | identity | /platform/identity/roles | 否 | 平台四域目标页（归域） |
| /platform/identity/tenants | SystemTenants | identity | /platform/identity/tenants | 否 | 平台四域目标页（归域） |
| /platform/identity/users | UsersView | identity | /platform/identity/users | 否 | 平台四域目标页（归域） |
| /platform/identity/workspaces | WorkspacesView | identity | /platform/identity/workspaces | 否 | 平台四域目标页（归域） |
| /platform/observability/app-calls | GenericPage | observability | /platform/observability/app-calls | 否 | 平台四域目标页（归域） |
| /platform/observability/billing | BillingView | observability | /platform/observability/billing | 否 | 平台四域目标页（归域） |
| /platform/observability/gateway-test | GatewayAggregateView | observability | /platform/observability/gateway-test | 否 | 平台四域目标页（归域） |
| /platform/observability/gpu | GpuMonitorView | observability | /platform/observability/gpu | 否 | 平台四域目标页（归域） |
| /platform/observability/logs | LogsView | observability | /platform/observability/logs | 否 | 平台四域目标页（归域） |
| /platform/observability/monitoring | Monitoring | observability | /platform/observability/monitoring | 否 | 平台四域目标页（归域） |
| /platform/observability/monitoring/alerts | Alerts | observability | /platform/observability/monitoring/alerts | 否 | 平台四域目标页（归域） |
| /platform/observability/monitoring/budgets | GenericPage | observability | /platform/observability/monitoring/budgets | 否 | 平台四域目标页（归域） |
| /platform/observability/monitoring/costs | Costs | observability | /platform/observability/monitoring/costs | 否 | 平台四域目标页（归域） |
| /platform/observability/monitoring/traces | GenericPage | observability | /platform/observability/monitoring/traces | 否 | 平台四域目标页（归域） |
| /platform/observability/service-discovery | GatewayServicesView | observability | /platform/observability/service-discovery | 否 | 平台四域目标页（归域） |
| /platform/observability/test-records | SystemTestRecords | observability | /platform/observability/test-records | 否 | 平台四域目标页（归域） |
| /platform/observability/usage | Usage | observability | /platform/observability/usage | 否 | 平台四域目标页（归域） |
| /personal/settings | SettingsView | personal | /personal/settings | 否 | 个人域目标页（归域） |
| /knowledge/admin | KnowledgeAdminView | 业务模块 | — | 否 | 本色，不迁移 |
| /knowledge/chat | ChatView | 业务模块 | — | 否 | 本色，不迁移 |
| /knowledge/console | KnowledgeConsoleView | 业务模块 | — | 否 | 本色，不迁移 |
| /knowledge/list | KnowledgeList | 业务模块 | — | 否 | 本色，不迁移 |
| /memory/decay | MemoryDecay | 业务模块 | — | 否 | 本色，不迁移 |
| /memory/graph | MemoryGraph | 业务模块 | — | 否 | 本色，不迁移 |
| /memory/list | MemoryList | 业务模块 | — | 否 | 本色，不迁移 |
| /memory/search | MemorySearch | 业务模块 | — | 否 | 本色，不迁移 |
| /memory/sessions | MemorySessions | 业务模块 | — | 否 | 本色，不迁移 |
| /memory/write | MemoryWrite | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/ab-tests | AbTestView | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/apps | Apps | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/apps/new | AppForm | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/conversations | Conversations | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/deploy | GenericPage | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/downloads | DownloadManagerView | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/favorites | Favorites | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/models | Models | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/models/categories | Categories | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/models/comparison | Comparison | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/models/local | LocalModels | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/models/market | ModelMarketView | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/playground | Playground | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/prompt-experiments | PromptExperimentsView | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/prompt-templates | PromptTemplatesView | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/providers | Providers | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/providers/register | GenericPage | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/recommend | P2RecommendView | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/reports-trend | P2ReportTrendView | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/routing/circuit-breakers | Routing | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/routing/strategies | Routing | 业务模块 | — | 否 | 本色，不迁移 |
| /openllm/tool-calls | ToolCallMonitorView | 业务模块 | — | 否 | 本色，不迁移 |
| /portrait/api-manage | DpsApiManageView | 业务模块 | — | 否 | 本色，不迁移 |
| /portrait/batch | PortraitList | 业务模块 | — | 否 | 本色，不迁移 |
| /portrait/list | PortraitList | 业务模块 | — | 否 | 本色，不迁移 |
| /portrait/monitor | DpsMonitorView | 业务模块 | — | 否 | 本色，不迁移 |
| /portrait/overview | Overview | 业务模块 | — | 否 | 本色，不迁移 |
| /portrait/permissions | DpsPermissionView | 业务模块 | — | 否 | 本色，不迁移 |
| /portrait/rate-limit | DpsRateLimitView | 业务模块 | — | 否 | 本色，不迁移 |
| /portrait/reports | PortraitList | 业务模块 | — | 否 | 本色，不迁移 |
| /portrait/rules | Rules | 业务模块 | — | 否 | 本色，不迁移 |
| /portrait/search | PortraitSearch | 业务模块 | — | 否 | 本色，不迁移 |
| /portrait/tags | Tags | 业务模块 | — | 否 | 本色，不迁移 |
| /auth/login | Login | 全局静态页 | — | 否 | 保留（登录页） |
| /auth/oidc/callback | OidcCallback | 全局静态页 | — | 否 | 保留（OIDC 回调页） |
| /dashboard | Dashboard | 全局静态页 | — | 否 | 保留（登录后默认页） |
| /forbidden | Forbidden | 全局静态页 | — | 否 | 保留（403 无权限页） |
| /gateway/aggregate | GatewayAggregateView | observability | /platform/observability/gateway-test | **是** | 旧路径，legacyRedirects.ts 承接（禁 404） |
| /gateway/services | GatewayServicesView | observability | /platform/observability/service-discovery | **是** | 旧路径，legacyRedirects.ts 承接（禁 404） |
| /knowledge/settings | — | config | /platform/config/general | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /knowledge/users | — | identity | /platform/identity/users | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /memory/admin | — | identity | /platform/identity/memory-admin | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /memory/api-gateway | — | observability | /platform/observability/service-discovery | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /memory/monitor | — | observability | /platform/observability/monitoring | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /openllm/adapters | — | developers | /platform/developers/edgerouter | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /openllm/api-keys | — | config | /platform/config/api-keys | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /openllm/apps/calls | — | observability | /platform/observability/app-calls | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /openllm/auth-ext | — | identity | /platform/identity/auth-ext | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /openllm/gpu | — | observability | /platform/observability/gpu | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /openllm/monitoring | — | observability | /platform/observability/monitoring | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /openllm/monitoring/alerts | — | observability | /platform/observability/monitoring/alerts | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /openllm/monitoring/budgets | — | observability | /platform/observability/monitoring/budgets | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /openllm/monitoring/costs | — | observability | /platform/observability/monitoring/costs | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /openllm/monitoring/traces | — | observability | /platform/observability/monitoring/traces | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /openllm/plugins | — | developers | /platform/developers/plugins | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /openllm/settings | — | personal | /personal/settings | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /openllm/usage | — | observability | /platform/observability/usage | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /portrait/dps-monitor | — | observability | /platform/observability/monitoring | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /system/audit | — | observability | /platform/observability/logs | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /system/billing | — | observability | /platform/observability/billing | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /system/config | — | config | /platform/config/general | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /system/docs | — | developers | /platform/developers/docs | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /system/edgerouter | — | developers | /platform/developers/edgerouter | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /system/logs | — | observability | /platform/observability/logs | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /system/org | — | identity | /platform/identity/org | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /system/roles | — | identity | /platform/identity/roles | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /system/tenants | — | identity | /platform/identity/tenants | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /system/test-records | — | observability | /platform/observability/test-records | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |
| /system/workspaces | — | identity | /platform/identity/workspaces | **是** | 旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404） |

> 注 1：参数化路由（如 `:id` 详情页）按既有语义保留在各自模块，不参与迁移。
> 注 2：全局静态页（/dashboard、/auth/login、/auth/oidc/callback、/forbidden）不迁移、不重定向；纳入矩阵并归类（非静默排除），以保证「未登记路径 = 0」可核对。
> 注 3：「目标域 / 目标路径 / 需重定向」三列由 src/core/router/legacyRedirects.ts 程序化推导，脚本内不重复维护基线。

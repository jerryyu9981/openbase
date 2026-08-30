# OpenBase 前端架构设计文档 - v1.4.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | FA-OpenBase-Dev |
| 创建日期 | 2026-08-28 |
| 存放 | doc/design/ |

> 本文档为 v1.4.0 版本设计增量，继承《OpenBase 前端架构设计文档-v1.2.0/v1.3.0.md》的底座架构（Vue3 + Ant Design Vue + vue-vben-admin + 动态模块 + 请求层）。本版本核心：26 项新增页面（OpenLLM 16 + OpenRAG 2 + OpenMemory 1 + DPS 4 + P2 1 + 网关管理 2），全部复用底座，不新建框架。

## 1. 架构继承与增量

| 层 | v1.3.0 基线 | v1.4.0 增量 |
|----|------------|------------|
| 底座 | 布局壳/Design Token/路由/状态/鉴权（已验证） | 无改动 |
| 请求层 | /api/v1/proxy/* 封装（JWT + SSE + 402/502 处理） | 新增网关 API 调用封装（`/api/v1/services`、`/api/v1/gateway/*`） |
| 组件库 | 公共组件（表格/表单/弹窗/图表 ECharts） | 复用；新增网关专用组件（HealthBadge/InstanceTable/AggregateTestPanel） |
| 路由 | 静态（公共模块）+ 动态（业务域模块） | 新增页面注册为静态路由（系统管理分组）或动态模块路由（网关管理分组） |
| 状态管理 | Pinia（auth/app/动态模块） | 复用；新增网关 store（serviceRegistry/aggregate） |

## 2. 页面路由设计（26 项）

| 分组 | 路由前缀 | 页面 | DT-ID |
|------|---------|------|-------|
| OpenLLM-模型中心 | /openllm/market | ModelMarketView 模型市场 | DT-14-01 |
| OpenLLM-模型中心 | /openllm/downloads | DownloadManagerView 下载管理 | DT-14-02 |
| OpenLLM-监控 | /openllm/gpu | GpuMonitorView GPU 监控 | DT-14-03 |
| OpenLLM-AI 应用 | /openllm/prompt-templates | PromptTemplatesView | DT-14-04 |
| OpenLLM-AI 应用 | /openllm/prompt-experiments | PromptExperimentsView | DT-14-05 |
| OpenLLM-系统管理 | /openllm/plugins | PluginsView | DT-14-06 |
| OpenLLM-监控 | /openllm/tool-calls | ToolCallMonitorView | DT-14-07 |
| OpenLLM-AI 应用 | /openllm/ab-tests | AbTestView | DT-14-08 |
| 系统管理 | /system/roles | RolesView | DT-14-09 |
| 系统管理 | /system/org | OrgTeamsUsersView | DT-14-10 |
| 系统管理 | /system/workspaces | WorkspacesView | DT-14-11 |
| 系统管理 | /system/config | ConfigManageView | DT-14-12 |
| 系统管理 | /system/audit | AuditLogsView | DT-14-13 |
| 系统管理 | /system/edgerouter | EdgeRouterView | DT-14-14 |
| 系统管理 | /system/docs | DocCenterView | DT-14-15 |
| 系统管理 | /system/billing | BillingView | DT-14-16 |
| OpenRAG-管理 | /openrag/admin | RagAdminOverviewView | DT-14-17 |
| OpenRAG-控制台 | /openrag/console | RagConsoleView | DT-14-18 |
| OpenMemory-运维 | /openmemory/ops | MemoryOpsView | DT-14-19 |
| DPS-治理 | /dps/rate-limit | RateLimitView | DT-14-20 |
| DPS-治理 | /dps/api-manage | ApiManageView | DT-14-21 |
| DPS-治理 | /dps/permission | PermissionView | DT-14-22 |
| DPS-监控 | /dps/monitor | SysMonitorView | DT-14-23 |
| P2-辅助 | /p2/assist | P2AssistView（对比推荐/内容库/报表趋势/排名） | DT-14-24 |
| 网关管理 | /gateway/services | GatewayServicesView 服务列表 | DT-14-25 |
| 网关管理 | /gateway/aggregate | GatewayAggregateView 聚合测试 | DT-14-26 |

## 3. 组件设计

### 3.1 复用组件（底座既有）

| 组件 | 用途 |
|------|------|
| BasicTable / BasicForm / BasicModal | 26 项页面列表/表单/弹窗基座 |
| StatusBadge | 状态展示（启停/健康/进度） |
| ECharts 封装（Line/Bar/Pie/Radar） | GPU 趋势/Prompt 报表/计费趋势/DPS 监控 |
| FileUpload | 文档上传（文档中心） |

### 3.2 新增组件（本版本）

| 组件 | 位置 | 说明 |
|------|------|------|
| `HealthBadge.vue` | components/gateway/ | 实例健康徽标（healthy/unhealthy/unknown 三态 + 颜色） |
| `InstanceTable.vue` | components/gateway/ | 服务实例表（system/host:port/weight/健康/心跳时间），30s 轮询刷新 |
| `AggregateTestPanel.vue` | components/gateway/ | 聚合测试面板（步骤配置表单 + 发送 + 结果/错误展示） |
| `TaskQueueTable.vue` | components/common/ | 下载任务队列（进度条/暂停恢复/重试） |
| `VirtualKeyPanel.vue` | components/workspace/ | Virtual Key 列表（创建/轮换/删除） |

## 4. 状态设计（Pinia）

| store | 说明 |
|-------|------|
| `useGatewayStore` | 服务注册表（systems/instances/health）+ 聚合执行状态；`fetchServices()` / `fetchHealth()` / `pingAll()`（30s 轮询由网关管理页触发） |
| 复用 store | auth/user/app/dict 等底座 store 不变 |

## 5. 请求层设计

| 封装 | 说明 |
|------|------|
| `api/gateway.ts` | `/api/v1/services` CRUD + `/api/v1/gateway/health|ping|aggregate` 调用封装（注入 JWT，统一错误处理） |
| 复用 `api/proxy.ts` | 四系统 `/api/v1/proxy/{system}/*` 调用（26 项页面数据源） |
| SSE | 对话/事件流复用 v1.3.0 SSE 透传封装 |

## 6. 构建与部署

| 项 | 说明 |
|----|------|
| 构建 | 沿用统一前端构建（Vite + 多环境配置）；新增页面为普通静态路由，无构建级开关 |
| 部署 | 静态资源随统一前端发布；网关管理页依赖 OpenBase 后端网关 API（Dev 起联调） |
| 质量门禁 | 新增页面测试 100%、覆盖率 ≥80%、Lint 0（vitest + eslint + stylelint） |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-28 | FA-OpenBase-Dev | 初始创建：26 项页面路由设计 + 新增组件（HealthBadge/InstanceTable/AggregateTestPanel 等）+ 网关 store 与请求层封装 |
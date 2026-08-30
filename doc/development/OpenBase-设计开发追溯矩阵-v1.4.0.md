# OpenBase 设计开发追溯矩阵 - v1.4.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-08-28 |
| 存放 | doc/development/ |

---

## 1. 设计开发追溯（DT-ID → TD-ID → 文件映射）

> 本矩阵为 Step 3 编码逐项指引。开发按 Phase 分批：Phase 8（网关后端）先行实现并验证，前端 26 项页面随后续 Phase 分批推进（对应 Phase 计划 P8/P9 网关 + P1~P5 前端）。

### Phase 8 网关后端（本次实现范围）

| TD-ID | 设计项（DT-ID） | 需求（RT-ID） | 涉及文件（新建/修改） | 状态 |
|-------|----------------|--------------|----------------------|:---:|
| TD-14-25 | 后端实例服务发现（DT-14-25） | RT-425 | 新建 `openbase/modules/gateway/__init__.py`、`discovery.py`、`registry.py`、`probe.py`、`load_balance.py`、`router.py`、`schemas.py`、`providers/__init__.py`、`providers/config_probe.py` | 待实现 |
| TD-14-26 | 聚合编排（DT-14-26） | RT-426 | 新建 `openbase/modules/gateway/aggregate.py`；修改 `openbase/modules/gateway/router.py` | 待实现 |
| TD-14-N3 | 错误码与权限点（DT-14-N3） | RT-N403 | 修改 `openbase/core/errors/codes.py`（新增 SYS_TIMEOUT/PARAM_AGGREGATE_STEP_INVALID/BIZ_AGGREGATE_PARTIAL_FAILURE/PERM_GATEWAY_*）；修改 `openbase/modules/auth/rbac.py`（权限点注册） | 待实现 |
| TD-14-N5 | proxy 集成（DT-14-N5） | RT-N405 | 修改 `openbase/modules/proxy/__init__.py`（`_resolve_base_url` → DiscoveryRegistry.pick + gateway 开关）；修改 `openbase/demo_app.py`（enable_module("gateway")）；修改 `openbase/modules/versions.json` | 待实现 |

### Phase 1 前端（OpenLLM 首批 + 网关管理页，本次交付）

| TD-ID | 页面（DT-ID） | 需求（RT-ID） | 涉及文件 | 状态 |
|-------|--------------|--------------|---------|:---:|
| TD-14-01 | 开源模型市场（DT-14-01） | RT-401 | openbase-ui/src/modules/openllm/pages/ModelMarketView.vue（新建）+ index.ts 路由替换 | ✅ |
| TD-14-02 | 下载管理（DT-14-02） | RT-402 | openbase-ui/src/modules/openllm/pages/DownloadManagerView.vue（新建）+ 路由新增 | ✅ |
| TD-14-03 | GPU 监控（DT-14-03） | RT-403 | openbase-ui/src/modules/openllm/pages/GpuMonitorView.vue（新建）+ 路由替换 | ✅ |
| TD-14-04 | Prompt 模板（DT-14-04） | RT-404 | openbase-ui/src/modules/openllm/pages/PromptTemplatesView.vue（新建）+ 路由替换 | ✅ |
| TD-14-25f | 网关服务列表 + 聚合测试（DT-14-25~26） | RT-425~426 | openbase-ui/src/modules/gateway/*（新建 4 文件：index.ts/GatewayServicesView/GatewayAggregateView）+ core/api/gateway.ts + router 注册 | ✅ |
| TD-14-09 | 角色权限（DT-14-09） | RT-409 | openbase-ui/src/modules/openllm/pages/RolesView.vue + /system/roles 路由 | ✅ |
| TD-14-10 | 组织/团队/用户（DT-14-10） | RT-410 | openbase-ui/src/modules/openllm/pages/OrgTeamsUsersView.vue + /system/org 路由 | ✅ |
| TD-14-11 | 工作空间（DT-14-11） | RT-411 | openbase-ui/src/modules/openllm/pages/WorkspacesView.vue + /system/workspaces 路由 | ✅ |
| TD-14-12 | 配置管理（DT-14-12） | RT-412 | openbase-ui/src/modules/openllm/pages/ConfigManageView.vue + /system/config 路由 | ✅ |
| TD-14-13 | 审计日志（DT-14-13） | RT-413 | openbase-ui/src/modules/openllm/pages/AuditLogsView.vue + /system/audit 路由 | ✅ |
| TD-14-14 | EdgeRouter（DT-14-14） | RT-414 | openbase-ui/src/modules/openllm/pages/EdgeRouterView.vue + /system/edgerouter 路由 | ✅ |
| TD-14-15 | 文档中心（DT-14-15） | RT-415 | openbase-ui/src/modules/openllm/pages/DocCenterView.vue + /system/docs 路由 | ✅ |
| TD-14-16 | 计费三页（DT-14-16） | RT-416 | openbase-ui/src/modules/openllm/pages/BillingView.vue + /system/billing 路由 | ✅ |
| TD-14-05~08 | OpenLLM 其余 4 页（Prompt 实验/插件/工具/A-B） | RT-405~408 | 待后续 Phase | 待排期 |
| TD-14-17 | OpenRAG 管理概览+知识库后台（DT-14-17） | RT-417 | openbase-ui/src/modules/knowledge/pages/KnowledgeAdminView.vue + /knowledge/admin 路由 | ✅ |
| TD-14-18 | OpenRAG 控制台（DT-14-18） | RT-418 | openbase-ui/src/modules/knowledge/pages/KnowledgeConsoleView.vue + /knowledge/console 路由 | ✅ |
| TD-14-19 | OpenMemory 监控+API 测试+设置（DT-14-19） | RT-419 | openbase-ui/src/modules/memory/pages/MemoryMonitorView.vue + /memory/monitor 路由 | ✅ |
| TD-14-20 | DPS 限流管理（DT-14-20） | RT-420 | openbase-ui/src/modules/portrait/pages/DpsRateLimitView.vue + /portrait/rate-limit 路由 | ✅ |
| TD-14-21 | DPS API 管理（DT-14-21） | RT-421 | openbase-ui/src/modules/portrait/pages/DpsApiManageView.vue + /portrait/api-manage 路由 | ✅ |
| TD-14-22 | DPS 权限管理（DT-14-22） | RT-422 | openbase-ui/src/modules/portrait/pages/DpsPermissionView.vue + /portrait/permissions 路由 | ✅ |
| TD-14-23 | DPS 系统监控（DT-14-23） | RT-423 | openbase-ui/src/modules/portrait/pages/DpsMonitorView.vue + /portrait/monitor 路由 | ✅ |
| TD-14-24 | P2 对比推荐/报表（DT-14-24） | RT-424 | openbase-ui/src/modules/openllm/pages/P2RecommendView.vue + P2ReportTrendView.vue + /openllm/recommend\|reports-trend 路由 | ✅ |

### 测试计划（TDD）

| 测试文件 | 覆盖 TD | 用例要点 | 状态 |
|---------|---------|---------|:---:|
| tests/test_gateway.py（后端） | TD-14-25/26/N3/N5 | 注册/列表/下线；探测剔除恢复；加权轮询；聚合；错误码；proxy 兜底 | ✅ 14/14 |
| openbase-ui/tests/gateway-api.spec.ts（前端） | TD-14-25f | gatewayApi 6 方法契约 | ✅ 6/6 |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-28 | AD-OpenBase-Dev | 初始创建：Phase 8 网关后端 TD 映射（9 新建 + 4 修改）+ Subtask CheckList + 测试计划 |
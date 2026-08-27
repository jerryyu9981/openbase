# OpenBase 系统架构设计文档 - v1.3.0（统一前端功能补全版本设计）

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.3.0 |
| 文档版本 | v1.0.0 |
| 类型 | 版本设计（继承总体架构约定，记录本版本增量） |
| 状态 | [Review] |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-08-27 |
| 存放 | doc/design/ |

> 本文档为 v1.3.0 版本设计增量，继承《OpenBase 系统架构设计文档》（总体架构）与 v1.2.0 版本设计的分层、模块与治理约定，不推翻总体架构。v1.3.0 核心：前端 32 项功能补齐完整 + 基座与后端调试完整 + 四系统对接挂起分批（VC-005）。

## 1. 设计入场检查

| 检查项 | 输入 | 结果 |
|--------|------|------|
| 需求批准 | 需求评审记录 v1.3.0（v1.0.2 通过，含 VC-004/VC-005 复审） | ✅ |
| 需求追溯矩阵 | OpenBase-需求追溯矩阵-v1.3.0.md（35 RT） | ✅ |
| 需求评估审计 | 需求评估报告 v1.3.0（v1.0.2 通过） | ✅ |
| 需求基线 | OpenBase-需求基线及设计移交说明-v1.3.0.md（v1.0.3） | ✅ |
| 阶段审计 | 阶段审计报告 Stage1-v1.3.0（v1.0.2 通过） | ✅ |
| 轨道选择 | 整体 🎯 + 后端 ⚙️ + 前端 🎨 + 第三方集成 🔗 | ✅ 已确定 |

## 2. 需求-设计追溯（DT-ID）

| DT-ID | 设计项 | RT-ID | 设计章节 |
|-------|--------|-------|---------|
| DT-13-01 | 提供商管理 CRUD 设计（复用 OpenLLM ProvidersView） | RT-301 | §5.1 |
| DT-13-02 | 模型管理 CRUD + 定价设计（复用 ModelsView/ModelDrawer） | RT-302 | §5.1 |
| DT-13-03 | 本地模型设计（复用 LocalModelsView/GpuInfoPanel） | RT-303 | §5.1 |
| DT-13-04 | 注册/找回密码设计（登录旁路） | RT-304 | §5.1 |
| DT-13-05 | 个人设置设计 | RT-305 | §5.1 |
| DT-13-06 | 用量统计设计（复用 UsageView/UsageTrends） | RT-306 | §5.1 |
| DT-13-07 | 对话管理（流式）设计（复用 PlaygroundView/chat 组件） | RT-307 | §5.1 |
| DT-13-08 | 监控仪表盘补全设计（复用 monitoring 4 视图） | RT-308 | §5.1 |
| DT-13-09 | API 密钥管理设计（复用 ApiKeysView/CreateKeyDialog） | RT-309 | §5.1 |
| DT-13-10 | 告警管理设计（复用 AlertsView） | RT-310 | §5.1 |
| DT-13-11 | 成本分析 + 预算设计（复用 CostsView） | RT-311 | §5.1 |
| DT-13-12 | 路由策略 + 熔断器设计（复用 routing 组件群） | RT-312 | §5.1 |
| DT-13-13 | RAG 对话（流式 + 来源追踪）设计（参照 OpenRAG StreamingText/SourceTrace） | RT-313 | §5.2 |
| DT-13-14 | 知识库列表设计（参照 KnowledgePage） | RT-314 | §5.2 |
| DT-13-15 | 知识库详情设计（参照 ChunkPreview/ScoreBar） | RT-315 | §5.2 |
| DT-13-16 | OpenRAG 用户管理设计（参照 AdminUsersPage） | RT-316 | §5.2 |
| DT-13-17 | OpenRAG 系统配置设计（参照 AdminConfigPage） | RT-317 | §5.2 |
| DT-13-18 | 记忆列表设计（参照 MemoryList/DecayWeightColumn） | RT-318 | §5.3 |
| DT-13-19 | 记忆详情设计（参照 WaypointTimeline） | RT-319 | §5.3 |
| DT-13-20 | 知识图谱（D3）设计（参照 GraphView d3 forceSimulation） | RT-320 | §5.3, ADR-13-03 |
| DT-13-21 | 会话管理设计（参照 Sessions） | RT-321 | §5.3 |
| DT-13-22 | 画像管理（六维雷达）设计（参照 portrait.html + 雷达图） | RT-322 | §5.4 |
| DT-13-23 | 标签管理设计（参照 tag.html） | RT-323 | §5.4 |
| DT-13-24 | 报表中心设计（参照 report.html + ECharts） | RT-324 | §5.4 |
| DT-13-25 | 搜索分析（混合检索）设计（参照 search.html） | RT-325 | §5.4 |
| DT-13-26 | 审计日志设计（参照 audit-log.html） | RT-326 | §5.4 |
| DT-13-27 | 前端代理链路接入（基座侧请求层封装 + 对接挂起清单） | RT-327 | §6, §8 |
| DT-13-28 | 代理层 402 错误码统一处理 | RT-328 | §6.2 |
| DT-13-29 | 我的收藏设计（复用收藏逻辑） | RT-329 | §5.1 |
| DT-13-30 | 模型分类/对比设计（复用 ModelCategoriesView/ModelComparisonView） | RT-330 | §5.1 |
| DT-13-31 | OpenMemory 仪表盘设计（参照 Dashboard/recharts→ECharts） | RT-331 | §5.3 |
| DT-13-32 | DPS 数据总览设计（参照 dashboard.html） | RT-332 | §5.4 |
| DT-13-N1 | 非功能设计（性能/兼容/维护/可观测/质量） | RT-N301 | §7 |
| DT-13-N2 | 数据设计（契约 mock/状态管理/导出） | RT-N302 | §7 |
| DT-13-N3 | 权限与安全设计（JWT/RBAC/密钥保护） | RT-N303 | §7 |

**覆盖率：35/35 = 100%**

## 3. 总体架构（v1.3.0 增量）

```
┌─────────────────────────────────────────────────────────────┐
│                 统一前端（OpenBase UI v1.3.0）                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 公共底座（基座，本次必须调试完整）：登录/鉴权/RBAC/路由/   │ │
│  │ 动态模块/公共组件/公共页面 —— 与 OpenBase 后端联调 100%    │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │ 请求层：/api/v1/proxy/{system}/* 封装（JWT 注入 + SSE）   │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │ 业务模块（前端完整 32 项，四系统对接挂起按契约 mock）      │ │
│  │  OpenLLM(12+2) │ OpenRAG(5) │ OpenMemory(4+1) │ DPS(5+1) │ │
│  └───────────────────────────────┬─────────────────────────┘ │
│        基座真实调用               │ 四系统 mock/对接挂起       │
└───────────┬───────────────────────┴─────────────────────────┘
            │ JWT（基座经 OpenBase auth/RBAC）
┌───────────▼─────────────────────────────────────────────────┐
│              OpenBase 后端（v1.1.0~v1.2.0 稳定底座）           │
│  auth(登录/刷新/RBAC)  notifications  audit  tenant  config   │
│  [v1.3.0 增量] proxy(代理层) 402 错误码定义(BIZ_MODEL_QUOTA)   │
└─────────────────────────────────────────────────────────────┘
        │ 四系统对接（VC-005 挂起：前端 mock 先行，后续按需分批）
┌───────────────┬───────────────┬───────────────┬──────────────┐
│    OpenLLM    │    OpenRAG    │   OpenMemory  │     DPS      │
└───────────────┴───────────────┴───────────────┴──────────────┘
```

**架构要点（v1.3.0 增量）**：
1. **基座闭环**：公共底座（登录/鉴权/RBAC/动态模块/公共页面）与 OpenBase 后端真实联调，形成可独立验收的统一底座闭环。
2. **前端完整**：32 项功能页面全部真实实现（占位页清零），分层复用独立前端代码。
3. **对接挂起**：四系统页面按契约 mock 先行，对接批次清单登记（§8），后续按需分批与后端 API 调试，不阻塞前端交付。

## 4. 技术选型 ADR

### ADR-13-01 分层复用策略（G3 实现方式）

| 项 | 内容 |
|----|------|
| 决策标题 | 统一前端功能补齐采用"分层复用"实现方式 |
| 上下文 | 四系统独立前端技术栈：OpenLLM（Vue3+EP+ECharts，与 openbase-ui 100% 一致）、OpenRAG（React 18 无组件库）、OpenMemory（React+antd+recharts+d3）、DPS（HTML 原型）；直接拷贝可大幅提速 |
| 备选方案 | A. 全部重新实现（工作量大、违背"以已验证功能为基线"）；B. 分层复用（推荐） |
| 决策 | ①组件级直接拷贝：OpenLLM 公共组件/图表（MetricCard/CostChart）/axios 封装/样式体系；②页面级参照迁移：OpenLLM 模型中心/监控/系统管理整组页面（仅改请求层基址/路由注册/布局壳）；③交互级参照重写：OpenRAG 流式/SourceTrace、OpenMemory d3 图谱、DPS 后台结构 → Vue |
| 已知后果 | OpenLLM 的 vue-echarts 需转 ECharts 原生；React 组件需手工改写；拷贝代码需过 lint 与测试门禁 |

### ADR-13-02 基座与四系统对接策略（VC-005）

| 项 | 内容 |
|----|------|
| 决策标题 | v1.3.0 交付策略：基座调试完整 + 四系统对接挂起 |
| 上下文 | 用户业务输入：前端完整后，除基座外四系统对接调试挂起，按需分批 |
| 备选方案 | A. 四系统全量对接联调（依赖四系统 Dev 实例与契约稳定，周期不可控）；B. 基座调试 + 对接挂起分批（推荐） |
| 决策 | 基座功能与 OpenBase 后端联调 100% 通过；四系统前端按契约 mock，对接批次清单（§8）按需执行 |
| 已知后果 | 四系统页面数据为 mock，功能验收以交互/状态/流程为主；对接批次为后续补丁/版本 |

### ADR-13-03 知识图谱渲染技术（RT-320）

| 项 | 内容 |
|----|------|
| 决策标题 | 记忆知识图谱采用 D3 力导向图 |
| 上下文 | openbase-ui 实际未安装 D3；OpenMemory GraphView 已有 d3 forceSimulation 现成逻辑（约 60 行可移植）；需求要求缩放/拖拽/联动搜索/点击跳转 |
| 备选方案 | A. 引入 D3（推荐，OpenMemory 逻辑直接移植，满足交互要求）；B. ECharts graph 系列（无需新依赖，但力导向交互定制受限） |
| 决策 | 引入 D3（npm d3），移植 OpenMemory GraphView 力导向逻辑为 Vue 组件（MemoryGraph.vue） |
| 已知后果 | 新增依赖 d3（约 280KB）；需补充缩放/拖拽事件测试 |

## 5. 模块设计（前端补全）

### 5.1 OpenLLM 模块（DT-13-01~12, 29~30）

| 设计项 | 页面 | 复用来源 | 数据策略 |
|--------|------|---------|---------|
| 提供商管理 | Providers.vue（补全 CRUD/测试连接/同步/启停） | OpenLLM ProvidersView/ProviderDrawer | 契约 mock（对接挂起） |
| 模型管理+定价 | Models.vue（补全编辑/定价/能力/筛选） | OpenLLM ModelsView/ModelDrawer | 契约 mock |
| 本地模型 | LocalModels.vue（补全仓库/GPU/更新） | OpenLLM LocalModelsView/GpuInfoPanel | 契约 mock |
| 注册/找回密码 | Auth 旁路页面 | OpenLLM auth 流程 | **基座真实调用** |
| 个人设置 | Settings 页面 | OpenLLM SettingsView | **基座真实调用** |
| 用量统计 | Usage.vue（趋势/导出/明细） | OpenLLM UsageView/UsageTrends | 契约 mock |
| 对话管理 | Conversations.vue（补全流式/新建/归档） | OpenLLM PlaygroundView/chat 组件 | 契约 mock（SSE 模拟） |
| 监控仪表盘 | Monitoring.vue（补全成本/错误率/告警列表） | OpenLLM monitoring 4 视图 | 契约 mock |
| API 密钥 | ApiKeys.vue | OpenLLM ApiKeysView/CreateKeyDialog | 契约 mock |
| 告警管理 | Alerts.vue | OpenLLM AlertsView | 契约 mock |
| 成本+预算 | Costs.vue | OpenLLM CostsView | 契约 mock |
| 路由+熔断 | Routing.vue | OpenLLM routing 组件群 | 契约 mock |
| 我的收藏 | Favorites.vue | OpenLLM 收藏逻辑 | 契约 mock |
| 模型分类/对比 | Categories.vue / Comparison.vue | OpenLLM ModelCategoriesView/ModelComparisonView | 契约 mock |

### 5.2 OpenRAG 模块（DT-13-13~17）

| 设计项 | 页面 | 复用来源 | 数据策略 |
|--------|------|---------|---------|
| RAG 对话 | RagChat.vue（流式+SourceTrace+附件） | OpenRAG StreamingText/SourceTrace/Upload | 契约 mock（SSE 模拟） |
| 知识库列表 | KnowledgeList.vue（补全状态/进度/上传） | OpenRAG KnowledgePage | 契约 mock |
| 知识库详情 | KnowledgeDetail.vue（补全分块预览/ScoreBar） | OpenRAG ChunkPreview/ScoreBar | 契约 mock |
| 用户管理 | RagUsers.vue | OpenRAG AdminUsersPage | 契约 mock |
| 系统配置 | RagConfig.vue（四分区） | OpenRAG AdminConfigPage | 契约 mock |

### 5.3 OpenMemory 模块（DT-13-18~21, 31）

| 设计项 | 页面 | 复用来源 | 数据策略 |
|--------|------|---------|---------|
| 记忆列表 | MemoryList.vue（补全添加/衰减权重/分页） | OpenMemory MemoryList/DecayWeightColumn | 契约 mock |
| 记忆详情 | MemoryDetail.vue（补全关联/统计/hard 删除） | OpenMemory WaypointTimeline | 契约 mock |
| 知识图谱 | MemoryGraph.vue（D3 力导向） | OpenMemory GraphView d3 逻辑 | 契约 mock |
| 会话管理 | MemorySessions.vue | OpenMemory Sessions | 契约 mock |
| 仪表盘 | MemoryDashboard.vue（健康卡+趋势） | OpenMemory Dashboard（recharts→ECharts） | 契约 mock |

### 5.4 DPS 模块（DT-13-22~26, 32）

| 设计项 | 页面 | 复用来源 | 数据策略 |
|--------|------|---------|---------|
| 画像管理 | PortraitList.vue（补全六维雷达/风险） | DPS portrait.html + ECharts radar | 契约 mock |
| 标签管理 | PortraitTags.vue（分类树/计算规则） | DPS tag.html | 契约 mock |
| 报表中心 | PortraitReports.vue（指标/导出） | DPS report.html + ECharts | 契约 mock |
| 搜索分析 | PortraitSearch.vue（混合检索结果卡） | DPS search.html | 契约 mock |
| 审计日志 | PortraitAudit.vue（筛选/导出） | DPS audit-log.html | 契约 mock |
| 数据总览 | PortraitDashboard.vue（KPI/图表） | DPS dashboard.html + ECharts | 契约 mock |

## 6. 后端设计（v1.3.0 增量）

### 6.1 基座调试（DT-13-27）

| 项 | 内容 |
|----|------|
| 范围 | 登录/鉴权/RBAC/动态模块/公共页面与 OpenBase 后端联调（auth API、user/role/permission API、services 发现 API） |
| 验收 | 基座 E2E：登录→Token 刷新→RBAC 权限→动态模块显隐 全链路通过 |

### 6.2 代理层 402 错误码（DT-13-28）

| 项 | 内容 |
|----|------|
| 错误码 | 新增 `BIZ_MODEL_QUOTA`（HTTP 402），映射"模型服务余额不足" |
| 代理层行为 | 上游 402 → 代理层包装统一 ErrorResponse `{code: "BIZ_MODEL_QUOTA", message: "模型服务余额不足，请联系管理员充值", detail, request_id}`，HTTP 保持 402 |
| 前端行为 | 请求层拦截 402 → 全局 ElMessage 提示 + 不暴露原始错误 |
| 日志 | 402 包装仅记录 request_id/错误码，不记录敏感信息（AC-328-4） |

## 7. 非功能/数据/安全设计（DT-13-N1~N3）

| 类别 | 设计 |
|------|------|
| 性能 | 列表页 P50<1.5s/P99<3s；流式首字 P50<1s；代理透传额外延迟<100ms |
| 兼容性 | Chrome/Edge 最新两大版本；≥1280 无横向溢出（沿用 v1.2.0 响应式） |
| 可维护性 | 复用公共组件库（表格/表单/弹窗/图表封装）；组件测试覆盖 ≥80% |
| 可观测性 | 请求带 request_id；错误统一 ErrorResponse；SSE 链路可追踪 |
| 数据 | 基座真实数据；四系统按契约 mock（mock 数据格式与真实 API 契约字段一致，对接时无缝替换）；导出 UTF-8 |
| 安全 | JWT 双层鉴权；破坏性操作二次确认；API Key 仅展示一次；密钥脱敏；日志不落敏感信息 |

## 8. 四系统对接挂起清单（DT-13-27 配套，VC-005）

| 批次 | 系统 | 对接内容 | 前置 | 状态 |
|------|------|---------|------|------|
| 待定 | OpenLLM | 模型中心/对话/监控/系统管理真实 API 对接 | OpenLLM Dev 实例（8001）+ 契约核对 | 挂起 |
| 待定 | OpenRAG | RAG 对话/知识库/用户/配置真实 API 对接 | OpenRAG Dev 实例（8010） | 挂起 |
| 待定 | OpenMemory | 记忆/图谱/会话/仪表盘真实 API 对接 | OpenMemory Dev 实例（8020） | 挂起 |
| 待定 | DPS | 画像/标签/报表/搜索/审计真实 API 对接 | DPS Dev 实例（8030） | 挂起 |

> 对接批次按用户需要分批启动；启动批次时执行：契约核对（逐页对照独立前端实际调用）→ 请求层切真实基址 → 联调 → 回归。批次启动须登记单版本范围变更或补丁记录。

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-27 | AA-OpenBase-Dev | 初始创建：v1.3.0 系统架构增量设计（入场检查 + 35 DT-ID 追溯 + 总体架构 + ADR-13-01/02/03 + 模块设计 + 402 错误码 + 对接挂起清单） |

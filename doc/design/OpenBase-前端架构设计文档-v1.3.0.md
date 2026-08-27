# OpenBase 前端架构设计文档 - v1.3.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.3.0 |
| 文档版本 | v1.0.0 |
| 类型 | 版本设计（继承 v1.2.0 前端架构约定，记录本版本增量） |
| 状态 | [Review] |
| 作者 | FA-OpenBase-Dev |
| 创建日期 | 2026-08-27 |
| 存放 | doc/design/ |

> 本文档为 v1.3.0 前端架构增量，继承 v1.2.0 前端架构（统一底座/动态模块/请求层/公共组件库/响应式），记录本版本"前端完整 + 基座调试 + 四系统对接挂起"的设计。

## 1. 前端架构总览（v1.3.0）

```
openbase-ui（Vue3.5 + Element Plus + ECharts [+D3] + Pinia + vue-router + axios）
│
├─ 公共底座（基座，本次调试完整）
│   ├─ 登录/鉴权（auth API 真实调用）
│   ├─ 路由守卫 + 动态模块注册（services 发现）
│   ├─ 布局壳（侧边栏/顶栏/响应式断点）
│   ├─ 公共组件库（表格/表单/弹窗/图表封装）
│   └─ 公共页面（用户/角色/权限/工作台）
│
├─ 请求层（v1.3.0 增量：代理封装）
│   └─ http.ts：/api/v1/proxy/{system}/{path} 基址封装 + JWT 注入
│       + 统一错误处理（402 → BIZ_MODEL_QUOTA 友好提示）+ SSE 透传支持
│
└─ 业务模块（前端完整 32 项，四系统对接挂起按契约 mock）
    ├─ openllm（12 P0 + 2 P1）：模型中心/对话/监控/系统管理/收藏/分类对比
    ├─ knowledge（5）：RAG 对话/知识库列表/详情/用户/配置
    ├─ memory（4+1）：记忆列表/详情/图谱(D3)/会话/仪表盘
    └─ portrait（5+1）：画像/标签/报表/搜索/审计/数据总览
```

## 2. 分层复用设计（G3，ADR-13-01 落地）

| 层级 | 复用方式 | 来源 | 改造点 |
|------|---------|------|--------|
| ① 组件级拷贝 | 公共组件/图表组件（MetricCard/CostChart）、axios 封装、样式体系直接迁移 | OpenLLM | vue-echarts→ECharts 原生；适配公共组件库规范 |
| ② 页面级迁移 | 模型中心/监控/系统管理整组页面拷贝 | OpenLLM | 请求层基址→/api/v1/proxy/openllm/*；路由→动态模块注册；布局壳→统一底座 |
| ③ 交互级重写 | SSE 流式/来源追踪/检索得分（RAG）；d3 图谱（记忆）；后台页面结构（DPS） | OpenRAG/OpenMemory/DPS | React→Vue 改写；HTML→Vue 组件；交互以独立前端为基线 |

## 3. 请求层设计（DT-13-27）

| 项 | 设计 |
|----|------|
| 基址封装 | `http.ts` 导出 `proxyRequest(system, path, options)`，基址 `/api/v1/proxy/{system}` |
| JWT 注入 | 请求拦截器注入 `Authorization: Bearer <ob_access_token>`；401 触发刷新/跳登录 |
| 错误处理 | 统一 ErrorResponse 解析；402 → `BIZ_MODEL_QUOTA` 全局提示"模型服务余额不足" |
| SSE 支持 | `fetch` + `ReadableStream` 封装 `streamProxy(system, path, body)`，供流式对话/图谱数据使用 |
| mock 策略 | 四系统模块经 `MOCK_FLAG`（构建配置）切换 mock/真实；mock 数据结构与契约字段一致（AC-327-5） |

## 4. 路由与模块注册

| 项 | 设计 |
|----|------|
| 基座路由 | 静态路由（/auth/login、/dashboard、/settings 等），真实 API |
| 业务模块路由 | 沿用 v1.2.0 动态模块注册（mountModuleRoutes），新增页面挂载到对应模块 index.ts |
| 占位页清理 | 24 个占位路由全部替换为真实组件（30/30 前端完整） |

## 5. 状态与数据设计（DT-13-N2）

| 项 | 设计 |
|----|------|
| 列表状态 | 筛选/分页本地维护 + query 同步（刷新可恢复） |
| 图表数据 | 统一 ECharts option 工厂（继承公共图表封装），mock 数据按契约结构 |
| 图谱数据 | MemoryGraph.vue 接收 nodes/edges 契约结构，D3 forceSimulation 渲染 |

## 6. 组件清单（新增/改造 30 页）

| 模块 | 新增组件 |
|------|---------|
| openllm | Providers.vue(改造)、Models.vue(改造)、LocalModels.vue(改造)、AuthExt.vue(注册/找回)、Settings.vue(新增)、Usage.vue(新增)、Conversations.vue(改造)、Monitoring.vue(改造)、ApiKeys.vue(新增)、Alerts.vue(新增)、Costs.vue(新增)、Routing.vue(新增)、Favorites.vue(新增)、Categories.vue(新增)、Comparison.vue(新增) |
| knowledge | RagChat.vue(新增)、KnowledgeList.vue(改造)、KnowledgeDetail.vue(改造)、RagUsers.vue(新增)、RagConfig.vue(新增) |
| memory | MemoryList.vue(改造)、MemoryDetail.vue(改造)、MemoryGraph.vue(新增,D3)、MemorySessions.vue(新增)、MemoryDashboard.vue(新增) |
| portrait | PortraitList.vue(改造)、PortraitTags.vue(新增)、PortraitReports.vue(新增)、PortraitSearch.vue(新增)、PortraitAudit.vue(新增)、PortraitDashboard.vue(新增) |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-27 | FA-OpenBase-Dev | 初始创建：v1.3.0 前端架构增量（分层复用设计、请求层代理封装、路由/状态设计、30 页组件清单） |

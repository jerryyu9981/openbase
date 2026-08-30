# OpenBase 系统架构设计文档 - v1.4.0（统一前端完备 + 统一网关增强版本设计）

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.0 |
| 文档版本 | v1.0.0 |
| 类型 | 版本设计（继承总体架构约定，记录本版本增量） |
| 状态 | [Review] |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-08-28 |
| 存放 | doc/design/ |

> 本文档为 v1.4.0 版本设计增量，继承《OpenBase 系统架构设计文档》（总体架构）与 v1.3.0 版本设计的分层、模块与治理约定，不推翻总体架构。v1.4.0 核心：P1 建议保留项全量补齐 + P2 项保留实现 + 统一网关增强阶段一（服务发现/聚合编排，VC-006）；生态工具链挂起（VC-007）。

## 1. 设计入场检查（2.0）

| 检查项 | 输入 | 结果 |
|--------|------|------|
| 需求批准 | 需求评审记录 v1.4.0（v1.0.0 通过）+ 需求基线 v1.4.0-RB1 | ✅ |
| 需求追溯矩阵 | OpenBase-需求追溯矩阵-v1.4.0.md（31 RT） | ✅ |
| 需求评估审计 | 需求评估报告 v1.4.0（v1.0.0 通过） | ✅ |
| 阶段审计 | 阶段审计报告 Stage1-v1.4.0（v1.0.0 通过） | ✅ |
| Step 0 输入 | 单版本规划 v1.4.0（v1.0.2）+ Backlog 26 项 + Phase P1~P9 + 评审记录 [Approved] | ✅ |
| 轨道选择 | 整体 🎯 + 后端 ⚙️ + 前端 🎨 + 第三方集成 🔗 | ✅ 已确定（四系统经代理对接属集成轨道） |

## 2. 需求-设计追溯（DT-ID，2.1）

| DT-ID | 设计项 | RT-ID | 设计章节 |
|-------|--------|-------|---------|
| DT-14-01 | 开源模型市场设计 | RT-401 | §5.1 |
| DT-14-02 | 下载管理设计 | RT-402 | §5.1 |
| DT-14-03 | GPU 监控设计 | RT-403 | §5.1 |
| DT-14-04 | Prompt 模板设计 | RT-404 | §5.1 |
| DT-14-05 | Prompt 实验设计 | RT-405 | §5.1 |
| DT-14-06 | 插件管理设计 | RT-406 | §5.1 |
| DT-14-07 | 工具调用监控设计 | RT-407 | §5.1 |
| DT-14-08 | A/B 测试设计 | RT-408 | §5.1 |
| DT-14-09 | 角色权限设计 | RT-409 | §5.1 |
| DT-14-10 | 组织/团队/用户管理设计 | RT-410 | §5.1 |
| DT-14-11 | 工作空间设计 | RT-411 | §5.1 |
| DT-14-12 | 配置管理设计 | RT-412 | §5.1 |
| DT-14-13 | 审计日志设计 | RT-413 | §5.1 |
| DT-14-14 | EdgeRouter 设计 | RT-414 | §5.1 |
| DT-14-15 | 文档中心设计 | RT-415 | §5.1 |
| DT-14-16 | 计费三页设计 | RT-416 | §5.1 |
| DT-14-17 | OpenRAG 管理概览+知识库后台设计 | RT-417 | §5.2 |
| DT-14-18 | OpenRAG 控制台设计 | RT-418 | §5.2 |
| DT-14-19 | OpenMemory 监控/API 测试/设置设计 | RT-419 | §5.3 |
| DT-14-20 | DPS 限流管理设计 | RT-420 | §5.4 |
| DT-14-21 | DPS API 管理设计 | RT-421 | §5.4 |
| DT-14-22 | DPS 权限管理设计 | RT-422 | §5.4 |
| DT-14-23 | DPS 系统监控设计 | RT-423 | §5.4 |
| DT-14-24 | P2 项设计 | RT-424 | §5.5 |
| DT-14-25 | 后端实例服务发现设计（gateway 模块） | RT-425 | §4.2, §5.6 |
| DT-14-26 | 聚合编排设计（聚合端点） | RT-426 | §4.3, §5.6 |
| DT-14-N1 | 非功能设计（性能/可靠性/兼容/质量/可观测） | RT-N401 | §7 |
| DT-14-N2 | 数据设计（ServiceInstance/配置键） | RT-N402 | §6 |
| DT-14-N3 | 权限与安全设计（gateway 权限点） | RT-N403 | §8 |
| DT-14-N4 | UI/UX 设计 | RT-N404 | §5.7 |
| DT-14-N5 | 接口与集成设计（网关 API/四系统对接） | RT-N405 | §4.4 |

**覆盖率：31/31 = 100%**

## 3. 总体架构（v1.4.0 增量）

```
┌─────────────────────────────────────────────────────────────┐
│                 统一前端（OpenBase UI v1.4.0）                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 公共底座（继承 v1.3.0 已验证）：登录/鉴权/RBAC/路由/动态   │ │
│  │ 模块/公共组件/公共页面                                    │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │ 请求层：/api/v1/proxy/{system}/* 封装（JWT 注入 + SSE）   │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │ 新增业务页面（26 项）：OpenLLM 16 │ OpenRAG 2 │          │ │
│  │ OpenMemory 1 │ DPS 4 │ P2 1 │ 网关管理 2（服务列表/聚合）  │ │
│  └───────────────────────────────┬─────────────────────────┘ │
└───────────┬───────────────────────┴─────────────────────────┘
            │ JWT（经 OpenBase auth/RBAC）
┌───────────▼─────────────────────────────────────────────────┐
│              OpenBase 后端（v1.4.0 增量）                      │
│  auth  notifications  audit  tenant  config  scheduler        │
│  proxy（改造：_resolve_base_url → DiscoveryRegistry.pick）     │
│  [新增] gateway 模块（服务发现 + 聚合编排，阶段一零依赖）        │
└───────────────────────────┬─────────────────────────────────┘
        │ 健康探测（scheduler interval job）│ 代理转发
┌───────▼────────┬────────▼───────┬───────▼───────┬───────────┐
│    OpenLLM     │    OpenRAG     │   OpenMemory  │    DPS    │
│  (8001)        │  (8010)        │  (8020)       │  (8030)   │
└────────────────┴────────────────┴───────────────┴───────────┘
```

**架构要点（v1.4.0 增量）**：
1. **网关能力归属 OpenBase**：统一网关（服务发现/路由转发/聚合）全部落在 OpenBase 网关层，四系统保持单体分层（多单体 + 统一网关，非微服务化）。
2. **gateway 模块新增**：DiscoveryProvider 适配器接口 + ConfigProbeProvider（阶段一默认）→ DiscoveryRegistry 内存注册表 → scheduler 健康探测 → proxy 动态解析；聚合端点 `/api/v1/gateway/aggregate` 代码式并发。
3. **零新增依赖**：复用现有 scheduler（APScheduler）+ config（ConfigStore 热加载）+ proxy（转发/错误包装），阶段一不引入 Nacos/DSL。
4. **向后兼容**：`PROXY_SYSTEMS` 静态表兜底；`gateway.discovery.enabled=false` 回退 v1.3.0 行为。

<!-- SECTION_4 -->

## 4. 后端架构设计（2.4a/2.5a，⚙️）

### 4.1 模块结构

```
openbase/modules/gateway/
├── __init__.py            # gateway 模块入口（FastAPI 路由挂载 + 生命周期）
├── discovery.py           # DiscoveryProvider 抽象接口 + create_provider 工厂（对齐技术方案 §3.6）
├── registry.py            # DiscoveryRegistry 内存注册表（线程安全读写锁 + TTL 心跳）
├── providers/
│   ├── __init__.py
│   └── config_probe.py    # ConfigProbeProvider（阶段一默认：config 驱动 + scheduler 探测）
├── probe.py               # 健康探测逻辑（probe_all：GET {host}:{port}/health，连续 3 次失败剔除 + 冷却 60s）
├── load_balance.py        # 加权轮询（weight 分配 + 剔除避开故障实例）
├── aggregate.py           # 聚合编排（asyncio.gather 并发调 /proxy + 超时/部分失败策略）
├── router.py              # /api/v1/services + /api/v1/gateway/* 路由（JWT + gateway:* 权限）
└── schemas.py             # Pydantic 请求/响应模型（ServiceRegister/ServiceList/AggregateRequest）
```

### 4.2 服务发现设计（DT-14-25，RT-425）

| 设计项 | 内容 |
|--------|------|
| DiscoveryProvider | 抽象接口：`list_instances(system)` / `register(instance)` / `deregister(system, instance_id)` / `probe_all()`；`create_provider(kind)` 工厂（config 默认 / nacos 阶段二） |
| ConfigProbeProvider | 阶段一实现：实例来源三选一（动态注册 API POST /api/v1/services > config 键 `proxy.{system}.instances` 热加载 > 静态表 PROXY_SYSTEMS 兜底） |
| DiscoveryRegistry | 内存表（system → list[ServiceInstance]），线程安全读写锁；实例 TTL 60s 无心跳自动移除 |
| 健康探测 | 复用 scheduler 模块：`get_scheduler().add_job(probe_all, trigger="interval", seconds=10, id="gateway_probe")`；探测路径 `GET {host}:{port}/health`（可配 `gateway.discovery.health_path`）；连续 3 次失败 → healthy=false 剔除（冷却 60s）；冷却后成功 1 次恢复 |
| 转发级熔断 | 请求转发 5xx/超时 → `consecutive_failures+1`，≥3 剔除（请求级兜底，不等下一轮探测） |
| 负载均衡 | 加权轮询（weight 高者分配更多）；剔除后自动避开故障实例；全不可用回退 config 兜底实例 → 仍不可用 `SYS_502`（现有包装不变） |
| proxy 改造 | `_resolve_base_url(system)` → `DiscoveryRegistry.pick(system)`（优先动态实例；未启用 discovery 时保持静态表行为） |
| 配置键 | `gateway.discovery.enabled`（默认 true）/`interval`（默认 10）/`health_path`（默认 /health）/`ttl`（默认 60）；`proxy.{system}.instances` |

### 4.3 聚合编排设计（DT-14-26，RT-426）

| 设计项 | 内容 |
|--------|------|
| 端点 | `POST /api/v1/gateway/aggregate`（代码式，阶段一） |
| 请求模型 | `AggregateRequest`：steps[]（system/path/method/headers/body/timeout_ms）+ 整体 timeout_ms（默认 5000）+ on_partial_failure（return_errors 默认/strict/best_effort）+ mapping（结果合并规则） |
| 执行器 | FastAPI 聚合端点内 `asyncio.gather` 并发调 `/api/v1/proxy/{system}/{path}`（复用代理链路与鉴权）；信号量限流（默认并发 8） |
| 超时 | 单步超时按部分失败策略处理；整体超时返回 `SYS_TIMEOUT`（503） |
| 部分失败 | `return_errors`：成功步骤数据 + errors 数组；`strict`：任一步失败整体失败；`best_effort`：失败步骤返回 null 占位 |
| 合并 | mapping 显式指定目标字段（zip 模式，避免隐式覆盖）；未映射字段丢弃 |
| 安全 | 仅转发至已注册系统白名单（防 SSRF）；DSL 注册表 `gateway.aggregates.*` 阶段二预留 |
| 阶段二预留 | DSL 执行器接口（输入 DSL/请求 → 输出合并结果）稳定，可无缝替换为 DSL 或 GraphQL |

### 4.4 接口与集成设计（DT-14-N5，RT-N405）

| 集成点 | 设计 |
|--------|------|
| 四系统对接 | 全部页面功能经 `/api/v1/proxy/{system}/*` 对接既有 API（沿用 v1.3.0 代理链路与 402/502 统一包装） |
| scheduler 复用 | 健康探测 interval job 随网关启动注册，随模块启停 |
| config 复用 | `gateway.discovery.*` / `gateway.aggregates.*` / `proxy.{system}.instances` 键复用 ConfigStore 热加载/版本回滚 |
| auth/rbac | 新增权限点 `gateway:register` / `gateway:view` / `gateway:aggregate` |
| observability | 指标：实例数/健康率/探测耗时/聚合请求数/聚合耗时/部分失败数；日志带 request_id |
| 向后兼容 | `PROXY_SYSTEMS` 静态表兜底；未启用 discovery 行为与 v1.3.0 完全一致；`/api/v1/modules` 前端模块发现不受影响 |

<!-- SECTION_5 -->

## 5. 前端架构设计摘要（2.5b，🎨）

> 前端详细设计见《OpenBase-前端架构设计文档-v1.4.0.md》。统一前端沿用 v1.2.0/v1.3.0 底座（Vue3 + Ant Design Vue + vue-vben-admin），本版本新增 26 项页面，全部复用底座组件与请求层。

### 5.1 OpenLLM 域（DT-14-01~16，16 页）

| DT | 页面 | 复用/参照 | 关键交互 |
|----|------|-----------|---------|
| DT-14-01 | ModelMarketView 模型市场 | 参照独立前端 market 页 | 分类/搜索/下载触发 |
| DT-14-02 | DownloadManagerView 下载管理 | 新建 | 任务队列/暂停恢复/重试 |
| DT-14-03 | GpuMonitorView GPU 监控 | 复用 v1.3.0 GpuInfoPanel | 卡列表/趋势图（ECharts） |
| DT-14-04 | PromptTemplatesView | 新建 | 模板 CRUD/导入/版本 |
| DT-14-05 | PromptExperimentsView | 新建 | 实验/变体/报表 |
| DT-14-06 | PluginsView | 新建 | 插件启停/工具查看 |
| DT-14-07 | ToolCallMonitorView | 新建 | 调用链/取消 |
| DT-14-08 | AbTestView | 新建 | 实验列表/状态 |
| DT-14-09 | RolesView | 复用 v1.2.0 角色权限 | CRUD/权限清单 |
| DT-14-10 | OrgTeamsUsersView | 新建 | 组织树/团队/用户 |
| DT-14-11 | WorkspacesView | 新建 | CRUD/成员/Virtual Key |
| DT-14-12 | ConfigManageView | 新建 | 配置/热加载/导入导出 |
| DT-14-13 | AuditLogsView | 复用审计日志组件 | 多维筛选/报表 |
| DT-14-14 | EdgeRouterView | 新建 | 组织/配额/适配器/审计 |
| DT-14-15 | DocCenterView | 新建 | 分组文档/搜索 |
| DT-14-16 | BillingView | 新建 | 概览/账单/配额告警 |

### 5.2 OpenRAG 域（DT-14-17~18，2 页）

| DT | 页面 | 关键交互 |
|----|------|---------|
| DT-14-17 | RagAdminOverviewView 管理概览 + 知识库后台 | KPI 卡/列表/后台删除（二次确认） |
| DT-14-18 | RagConsoleView 控制台 | API 调试器/接口文档/性能监控 |

### 5.3 OpenMemory 域（DT-14-19，1 页）

| DT | 页面 | 关键交互 |
|----|------|---------|
| DT-14-19 | MemoryOpsView 系统监控 + API 测试 + 设置 | 健康指标/调试器/测试连接 |

### 5.4 DPS 域（DT-14-20~23，4 页）

| DT | 页面 | 关键交互 |
|----|------|---------|
| DT-14-20 | RateLimitView 限流管理 | 配额/规则/熔断状态 |
| DT-14-21 | ApiManageView API 管理 | 端点 CRUD/调试/版本/错误码/导出 |
| DT-14-22 | PermissionView 权限管理 | 角色/权限矩阵/租户 |
| DT-14-23 | SysMonitorView 系统监控 | 依赖健康/QPS/内存 CPU/告警 |

### 5.5 P2 项（DT-14-24，1 页）

| DT | 页面 | 关键交互 |
|----|------|---------|
| DT-14-24 | P2 辅助页（对比推荐/内容库/报表趋势/排名） | 按"可用"标准实现（P2） |

### 5.6 网关管理域（DT-14-25~26，2 页）

| DT | 页面 | 关键交互 |
|----|------|---------|
| DT-14-25 | GatewayServicesView 服务列表 | 实例/健康徽标/权重；健康状态实时刷新（轮询）；注册/下线入口（gateway:register） |
| DT-14-26 | GatewayAggregateView 聚合测试 | 聚合测试入口（步骤配置/发送/结果展示）；网关健康看板 |

### 5.7 UI/UX 设计约束（DT-14-N4，RT-N404）

| 项 | 约束 |
|----|------|
| 布局 | 全部新页面沿用统一前端底座（布局/Design Token/公共组件） |
| 状态 | 列表页含加载/空态/错误态；删除/启停二次确认 + 结果反馈 |
| 网关管理页 | 健康状态实时刷新（30s 轮询）；服务列表含健康徽标与权重展示 |
| 响应式 | ≥1280 桌面 / 768-1280 平板断点适配 |

## 6. 数据模型设计（DT-14-N2，RT-N402）

```python
# gateway/discovery.py —— ServiceInstance（对齐技术方案 §3.2）
@dataclass
class ServiceInstance:
    system: str            # openllm / openrag / openmemory / dps
    instance_id: str       # 实例唯一 ID（如 host:port）
    host: str
    port: int
    weight: int = 1        # 负载权重（加权轮询）
    healthy: bool = True
    last_heartbeat: float = 0.0
    consecutive_failures: int = 0   # 连续失败计数（熔断剔除）
    meta: dict = field(default_factory=dict)
```

| 设计项 | 内容 |
|--------|------|
| 注册表 | DiscoveryRegistry 内存态（system → list[ServiceInstance]）+ config 持久化兜底；网关重启后从 config 恢复静态实例，探测 30s 内重建动态实例 |
| 配置键 | `gateway.discovery.*`（enabled/interval/health_path/ttl）、`gateway.aggregates.*`（DSL 注册表阶段二预留）、`proxy.{system}.instances` |
| 无 DB 变更 | 本版本网关无新增数据库表（注册表内存态）；四系统对接沿用既有 API 契约 |

## 7. 非功能与可观测性设计（DT-14-N1，RT-N401）

| 维度 | 设计 |
|------|------|
| 性能 | 发现解析 <1ms（内存表）；聚合 P99 ≤ 1.5× 最慢子请求；整体超时 5000ms 硬限制；聚合信号量并发 8 |
| 可靠性 | 连续 3 次失败剔除 + 冷却 60s + 请求级熔断兜底；`gateway.discovery.enabled=false` 回退静态表 |
| 可观测性（网关） | 日志结构化 JSON（traceId/spanId/service/module/message，复用 observability 标准）；指标：`gateway_instance_count` / `gateway_health_rate` / `gateway_probe_duration` / `gateway_aggregate_requests_total` / `gateway_aggregate_duration` / `gateway_aggregate_partial_failures_total` |
| 可观测性（四系统页面） | 沿用 v1.3.0 既有埋点与错误码规范；前端错误经请求层统一上报 |
| 兼容性 | `/api/v1/proxy/{system}/{path}` 与 `/api/v1/modules` 行为不变；静态表兜底 |

## 8. 安全设计（DT-14-N3，RT-N403）

| 设计项 | 内容 |
|--------|------|
| 权限点 | 新增 `gateway:register`（注册/下线）、`gateway:view`（查看）、`gateway:aggregate`（聚合执行）；全部网关端点 JWT 鉴权 |
| 防 SSRF | 聚合请求仅转发至已注册系统白名单；禁止任意 URL 代理 |
| 输入校验 | Pydantic schema 校验（ServiceRegister/AggregateRequest）；超时/并发上限硬限制 |
| 审计 | 实例注册/下线、聚合执行记录审计日志（含 request_id）；敏感数据（密钥/令牌）不落日志 |
| 复用 | 沿用 auth/RBAC 双层鉴权与多租户隔离（tenant 过滤） |

## 9. 部署与环境设计（2.7）

> 详细部署见《OpenBase-部署架构草案-v1.4.0.md》。

| 环境 | 网关配置要点 |
|------|-------------|
| Dev | `gateway.discovery.enabled=true`；四系统 Dev 实例默认静态表（127.0.0.1:8001/8010/8020/8030），探测自动感知 |
| Test | 同 Dev；可配置多实例验证剔除/恢复 |
| Pro | 同 Test；实例经 config 或动态注册维护；回滚开关 `gateway.discovery.enabled=false` |

## 10. ADR 决策记录（2.3）

| ADR | 决策 | 依据 |
|-----|------|------|
| ADR-网关-001 | 服务发现分阶段演进（config+scheduler 零依赖 → Nacos 阶段二） | 已接受（技术方案 §11），本版本继承执行 |
| ADR-网关-002 | 聚合先代码式（asyncio.gather）后 DSL/GraphQL | 已接受（技术方案 §11），本版本继承执行 |
| ADR-14-01 | 网关模块独立于 proxy 模块新增（不侵入 proxy 结构，仅改 `_resolve_base_url` 一处） | 最少改动优先；gateway 归网关域，proxy 归转发域 |
| ADR-14-02 | 26 项前端页面全部复用统一前端底座与请求层，不新建独立框架 | 继承 v1.2.0/v1.3.0 已验证架构 |

## 11. 风险与开放问题

| 风险/问题 | 级别 | 处置 |
|-----------|------|------|
| 四系统 P1 功能 API 契约与独立前端实现偏差 | P1 | 契约核对先行（RT-N402-1），缺口登记 v1.4.x 补 |
| 网关探测误判致流量抖动 | P1 | 连续 3 次失败才剔除 + 冷却期；探测与请求双通道（R-404） |
| 网关能力与四系统对接批次并行 | P2 | gateway 仅改造 OpenBase 层，四系统零侵入（R-405） |
| 测试基座挂起致覆盖率门槛降低 | P2 | 本版本仍执行测试 100%/覆盖率 ≥80%（R-406） |
| 开放问题：聚合 mapping 复杂场景（嵌套/多源）阶段一仅支持 zip 字段映射 | P3 | 阶段二 DSL 扩展 |

## 12. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-28 | AA-OpenBase-Dev | 初始创建：v1.4.0 版本设计增量——gateway 模块（DiscoveryProvider/DiscoveryRegistry/scheduler 探测/加权轮询/聚合端点）+ proxy 改造 + 26 项前端页面设计 + 数据/安全/部署/可观测设计 + ADR-14-01/02（继承 ADR-网关-001/002） |


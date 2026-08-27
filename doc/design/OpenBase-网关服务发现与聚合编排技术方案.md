# OpenBase 网关服务发现与聚合编排技术方案

| 项目 | 内容 |
|------|------|
| 文档名称 | OpenBase 网关服务发现与聚合编排技术方案 |
| 文档版本 | v1.0.0 |
| 状态 | [Draft]（待评审） |
| 作者 | OpenBase 平台组 |
| 日期 | 2026-08-28 |
| 存放 | doc/design/ |
| 关联 | 《OpenBase 系统使用指南》《系统架构设计文档》《部署架构草案》 |

---

## 1. 背景与目标

### 1.1 现状

OpenBase 统一代理（proxy 模块，v1.2.0+）已实现**静态路由表转发**：

```python
PROXY_SYSTEMS = {
    "openllm":     {"base_url": "http://127.0.0.1:8001", "timeout": 10.0},
    "openrag":     {"base_url": "http://127.0.0.1:8010", "timeout": 10.0},
    "openmemory":  {"base_url": "http://127.0.0.1:8020", "timeout": 10.0},
    "dps":         {"base_url": "http://127.0.0.1:8030", "timeout": 10.0},
}
```

限制：无服务发现（实例变更需手工改配置）、无健康感知（转发失败才暴露）、无聚合编排（跨系统取数需调用方多次请求自行拼装）。

### 1.2 目标

| 编号 | 目标 | 验收标准 |
|:---:|------|---------|
| G1 | 服务发现：四系统实例动态感知 | 实例上线/下线 ≤30s 内被感知；无需重启网关 |
| G2 | 健康感知与故障转移 | 故障实例自动剔除，请求自动转发健康实例，成功率 ≥99% |
| G3 | 聚合编排：跨系统一次取数 | 声明式编排 DSL 一次请求合并多系统数据，P99 ≤ 1.5× 最慢子请求 |
| G4 | 向后兼容 | 现有 `/api/v1/proxy/{system}/{path}` 行为不变，配置兜底可用 |

### 1.3 范围

- 包含：服务发现注册/发现/健康探测/负载均衡、聚合编排 DSL 与执行器、网关管理 API
- 不包含：四系统自身改造（零侵入，仅提供注册 SDK/脚本可选）

---

## 2. 总体架构

```
┌────────────────────────── OpenBase 网关（新增/改造） ──────────────────────────┐
│                                                                               │
│  ┌────────────┐  ┌─────────────────────────────┐  ┌────────────────────────┐  │
│  │ 接入层       │  │ 发现层（Service Registry）    │  │ 聚合层（BFF）            │  │
│  │ JWT/租户/限流│─▶│  ● DiscoveryRegistry（内存）  │  │  ● 编排执行器（DSL）      │  │
│  │ request_id  │  │  ● 健康探测（定时 + 惰性）     │─▶│  ● 顺序/并行/条件/合并    │  │
│  └────────────┘  │  ● 负载均衡（加权轮询 + 剔除）  │  │  ● 超时/熔断/部分失败     │  │
│                  └────────────┬────────────────┘  └────────────┬───────────┘  │
│                               │                                 │              │
│        ┌──────────────────────▼─────────────────────────────────▼─────┐       │
│        │             路由/转发层（改造现有 proxy 模块）                     │       │
│        │  _resolve_base_url → DiscoveryRegistry 动态解析                │       │
│        │  402/502 统一包装（保持不变）                                    │       │
│        └──────────────────────┬───────────────────────────────────────┘       │
└───────────────────────────────┼───────────────────────────────────────────────┘
                                ▼
        ┌──────────┬──────────┬──────────┬──────────┐
        │ OpenLLM  │ OpenRAG  │ OpenMemory│  DPS    │
        │ 8001     │ 8010     │ 8020     │ 8030    │
        └──────────┴──────────┴──────────┴──────────┘
```

---

## 3. 服务发现方案

### 3.1 技术选型对比

| 方案 | 依赖 | 动态注册 | 健康感知 | 适用场景 | 结论 |
|------|:---:|:---:|:---:|---------|:---:|
| **模式一：配置 + 健康探测**（推荐默认） | 零新增依赖 | 配置即注册 | 网关主动探测 | 轻量部署、内存模式、中小规模 | ✅ 默认 |
| 模式二：Nacos 注册中心 | Nacos 服务端 | SDK 自动注册 | Nacos 心跳 | 企业级、多实例、云环境 | ✅ 可选增强 |
| Consul / etcd | 对应服务端 | SDK | 服务端健康检查 | 同 Nacos | 备选 |
| K8s DNS（headless Service） | K8s | 自动 | 就绪探针 | 容器化部署 | 备选 |

**决策**：采用**双模式可插拔**设计——默认模式一（零依赖、配置驱动 + 网关健康探测），企业级场景切换模式二（Nacos 注册中心），两者数据模型一致，仅替换注册来源。

### 3.2 数据模型

```python
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
    meta: dict = field(default_factory=dict)   # 扩展元数据
```

### 3.3 注册与发现机制（模式一）

```
四系统实例                          OpenBase 网关
   │ 启动时（可选）                     │
   │──POST /api/v1/gateway/services──▶ │ 注册实例（携带 system/host/port/weight）
   │                                   │
   │        轮询：GET /api/v1/gateway/services/{system} 返回实例列表
   │◀──────────────────────────────────│
   │        健康探测：GET {host}:{port}/health（每 10s，3 次失败剔除）
   │◀──────────────────────────────────│
   │        配置兜底：configs 键 proxy.{system}.instances 作为静态兜底
```

**注册方式**（三选一，优先级递减）：

| 优先级 | 方式 | 说明 |
|:---:|------|------|
| 1 | 动态注册 API | 四系统启动时调用 `POST /api/v1/gateway/services`（带 JWT），网关维护实例表 |
| 2 | 配置驱动 | config 模块写 `proxy.{system}.instances=[{"host","port","weight"}]`，网关监听配置变更刷新 |
| 3 | 静态默认表 | 现有 `PROXY_SYSTEMS` 兜底（保持向后兼容） |

### 3.4 健康探测与故障转移

| 项 | 设计 |
|----|------|
| 探测周期 | 每 10s 一轮（可配 `gateway.discovery.interval`） |
| 探测路径 | `GET {host}:{port}/health`（可配 `gateway.discovery.health_path`），2xx 视为健康 |
| 失败剔除 | 连续 3 次失败 → `healthy=false`，从候选池移除（进入冷却 60s） |
| 恢复 | 冷却期后重新探测，成功 1 次即恢复 |
| 转发失败熔断 | 请求转发 5xx/超时 → 该实例 `consecutive_failures+1`，≥3 剔除（请求级兜底，不等下一轮探测） |
| 负载均衡 | 加权轮询（weight 高者分配更多请求）；剔除后自动避开故障实例 |
| 全不可用 | 回退配置兜底实例；仍不可用 → `SYS_502`（现有包装不变） |

### 3.5 动态刷新

- **定时刷新**：探测结果每轮写入 DiscoveryRegistry（内存表，线程安全读写锁）
- **配置变更事件**：config 模块写入/删除 `proxy.{system}.instances` 时触发刷新
- **实例下线**：注册实例超过 TTL（默认 60s 无心跳）自动移除

---

## 4. 聚合编排方案（BFF）

### 4.1 编排方式选型

| 方式 | 优点 | 缺点 | 结论 |
|------|------|------|:---:|
| **声明式 DSL（JSON）**（推荐） | 安全（无代码注入）、可配置化、可审计 | 表达能力受限（可用算子弥补） | ✅ 默认 |
| 代码式编排（Python） | 表达力强 | 需发布代码、安全风险 | 备选（高级场景） |
| 图编排（DAG） | 复杂流程 | 实现重 | 后续演进 |

**决策**：声明式 DSL 优先，提供顺序/并行/条件/合并四类算子覆盖 90% 聚合场景；保留 Python 回调扩展点。

### 4.2 编排 DSL 设计

```json
{
  "id": "kb-dashboard",
  "version": "1",
  "timeout_ms": 5000,
  "on_partial_failure": "return_errors",      // return_errors | strict | best_effort
  "steps": [
    {
      "id": "kb-list",
      "type": "request",
      "method": "GET",
      "system": "openrag",
      "path": "/kb/list",
      "headers": {"X-Tenant-Id": "${ctx.tenant}"},
      "timeout_ms": 2000
    },
    {
      "id": "usage",
      "type": "request",
      "method": "GET",
      "system": "openllm",
      "path": "/usage/summary",
      "timeout_ms": 2000
    },
    {
      "id": "merge",
      "type": "merge",
      "inputs": ["kb-list", "usage"],
      "mode": "zip",                          // zip | concat | json_merge
      "mapping": {
        "knowledge_bases": "${kb-list.data}",
        "usage": "${usage.data}"
      }
    }
  ],
  "output": "merge"
}
```

### 4.3 算子（Step 类型）规范

| 算子 | type | 参数 | 行为 |
|------|------|------|------|
| 请求 | `request` | method/system/path/headers/body/timeout_ms | 经网关转发（复用代理链路与鉴权） |
| 顺序 | `sequence` | steps[] | 前序成功后执行后序；失败短路 |
| 并行 | `parallel` | steps[], concurrency | `asyncio.gather` 并发；单步超时/失败不影响其他 |
| 条件 | `if` | condition（JSONPath 表达式）/then/else | 按上下文条件分支 |
| 合并 | `merge` | inputs[]/mode/mapping | 汇总多步结果（zip/concat/json_merge） |
| 变量引用 | - | `${ctx.xxx}` / `${stepId.data.xxx}` | 上下文与步骤结果引用 |

### 4.4 并发、超时与部分失败

| 项 | 设计 |
|----|------|
| 并发控制 | `asyncio.gather` + 信号量限流（默认并发 8，可配）；避免连接池打满 |
| 整体超时 | DSL `timeout_ms`（默认 5000ms），超时返回 `SYS_TIMEOUT`（503） |
| 单步超时 | 每步独立 `timeout_ms`，超时按部分失败策略处理 |
| 部分失败策略 | `strict`：任一步失败整体失败；`return_errors`：成功步骤数据 + errors 数组（推荐默认）；`best_effort`：失败步骤返回 null 占位 |
| 熔断 | 下游实例连续失败进入熔断（复用 3.4 剔除机制），编排自动跳过 |

### 4.5 响应合并规则

| mode | 语义 | 适用 |
|------|------|------|
| `zip` | 字段映射合并为单个 JSON | 仪表盘聚合（最常用） |
| `concat` | 数组拼接 | 多源列表合并 |
| `json_merge` | 递归 JSON 合并 | 配置/快照聚合 |

冲突处理：`mapping` 显式指定目标字段，避免隐式覆盖；未映射字段丢弃。

### 4.6 缓存策略（可选）

- 聚合结果按 DSL id + 参数哈希缓存（TTL 可配，默认关闭）
- 幂等 GET 聚合可开缓存；含 POST 的编排默认不缓存

---

## 5. 网关管理 API 设计

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| GET | `/api/v1/gateway/services` | 服务实例列表（含健康状态） | Bearer |
| GET | `/api/v1/gateway/services/{system}` | 指定系统实例列表 | Bearer |
| POST | `/api/v1/gateway/services` | 四系统实例注册 | Bearer + `gateway:register` |
| DELETE | `/api/v1/gateway/services/{system}/{instance_id}` | 实例下线 | Bearer |
| GET | `/api/v1/gateway/health` | 网关发现层健康状态 | Bearer |
| POST | `/api/v1/gateway/aggregate` | 聚合编排执行（body=DSL） | Bearer |
| GET | `/api/v1/gateway/aggregate/{dsl_id}` | 查询已注册 DSL 定义 | Bearer |
| POST | `/api/v1/gateway/aggregate/{dsl_id}` | 执行已注册 DSL | Bearer |
| GET | `/api/v1/gateway/ping` | 四系统连通性一键检测 | Bearer |

聚合 DSL 注册表存储于 config 模块（键 `gateway.aggregates.{dsl_id}`），支持热更新。

---

## 6. 与现有模块集成

| 模块 | 改造点 |
|------|--------|
| proxy | `_resolve_base_url(system)` → `DiscoveryRegistry.pick(system)`（实例加权轮询）；保留 config 兜底；402/502 包装不变 |
| config | 新增配置键：`gateway.discovery.*`（interval/health_path/ttl）、`gateway.aggregates.*`（DSL 注册表）；复用现有版本/回滚能力 |
| auth/rbac | 新增权限点：`gateway:register`、`gateway:aggregate`、`gateway:view` |
| observability | 指标：实例数/健康率/探测耗时/聚合请求数/聚合耗时/部分失败数；日志带 request_id |
| frontend | 新增"网关管理"页（服务列表/健康状态/聚合 DSL 管理） |

**向后兼容**：`PROXY_SYSTEMS` 静态表保留为最终兜底；未启用 discovery 时行为与 v1.3.0 完全一致。

---

## 7. 非功能设计

| 维度 | 目标 |
|------|------|
| 性能 | 发现解析开销 <1ms（内存表）；聚合 P99 ≤ 1.5× 最慢子请求；单网关并发 ≥ 500 |
| 安全 | 全部端点 JWT 鉴权；DSL 白名单校验（仅允许已注册 DSL，防注入）；超时/并发上限硬限制 |
| 可观测 | RED 指标（Rate/Errors/Duration）；实例健康状态上报 observability |
| 高可用 | DiscoveryRegistry 内存态 + config 持久化兜底；网关重启后从 config 恢复静态实例，探测 30s 内重建动态实例 |

---

## 8. 实施计划

| Phase | 内容 | 交付物 | 周期 |
|:---:|------|--------|:---:|
| P1 | 服务发现模式一（注册 API + 健康探测 + 加权轮询 + 剔除） | proxy 改造 + gateway 管理 API + 测试 | 2 周 |
| P2 | 聚合编排（DSL 解析器 + 执行器：顺序/并行/条件/合并 + 部分失败） | aggregate API + DSL 注册表 + 测试 | 2 周 |
| P3 | 模式二 Nacos 注册中心接入（可选增强） | nacos 适配器 + 配置切换 | 1 周 |
| P4 | 网关管理前端页面 + 可观测指标 + 运维文档 | 页面 + 指标 + 更新《系统使用指南》 | 1 周 |
| P5 | 全量回归 + 部署验证 + 审计 | 测试报告 + 发布 | 1 周 |

**合计约 7 周**，建议随 v1.4.0 排期（与 P1/P2 补全项并行）。

---

## 9. 风险与回退

| 风险 | 级别 | 缓解 |
|------|:---:|------|
| 探测误判导致流量抖动 | P1 | 连续 3 次失败才剔除 + 冷却期；探测与请求双通道 |
| DSL 编排复杂度失控 | P1 | 四类算子约束 + DSL 长度/嵌套深度限制 + 注册表白名单 |
| Nacos 接入增加部署复杂度 | P2 | 默认模式一零依赖；Nacos 作为可选开关 |
| 向后兼容破坏 | P0 | 静态表兜底保留 + 全量回归现有 proxy 用例 |

**回退**：关闭 `gateway.discovery.enabled=false` 即回退 v1.3.0 静态转发行为；聚合 DSL 未注册时 aggregate API 直接 404，不影响现有功能。

---

## 10. 附录：典型编排 DSL 示例（跨系统仪表盘）

```json
{
  "id": "dashboard",
  "timeout_ms": 4000,
  "on_partial_failure": "return_errors",
  "steps": [
    {"id": "models", "type": "request", "method": "GET", "system": "openllm", "path": "/models", "timeout_ms": 2000},
    {"id": "kbs",    "type": "request", "method": "GET", "system": "openrag", "path": "/kb/list", "timeout_ms": 2000},
    {"id": "mem",    "type": "request", "method": "GET", "system": "openmemory", "path": "/memories/stats", "timeout_ms": 2000},
    {"id": "merge",  "type": "merge", "inputs": ["models", "kbs", "mem"], "mode": "zip", "mapping": {
      "model_count": "${models.data.total}",
      "kb_count": "${kbs.data.total}",
      "memory_count": "${mem.data.total}"
    }}
  ],
  "output": "merge"
}
```

调用：`POST /api/v1/gateway/aggregate`（body 为上述 DSL）→ 一次返回跨三系统的汇总数据。

---

## 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-28 | OpenBase 平台组 | 初始创建：服务发现（双模式可插拔 + 健康探测 + 负载均衡）与聚合编排（声明式 DSL + 四算子 + 部分失败）技术方案 |

# OpenBase 部署架构草案 - v1.4.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-08-28 |
| 存放 | doc/design/ |

---

## 1. 部署拓扑（v1.4.0 增量）

```
                        ┌─────────────────────────────┐
                        │  统一前端（静态资源 Nginx）    │
                        │  openbase-ui v1.4.0（26 新页）│
                        └──────────────┬──────────────┘
                                       │ JWT + /api/v1/*
                        ┌──────────────▼──────────────┐
                        │  OpenBase 后端（FastAPI）      │
                        │  [v1.4.0] gateway 模块        │
                        │  ├─ /api/v1/services          │
                        │  ├─ /api/v1/gateway/*         │
                        │  ├─ scheduler 健康探测 job     │
                        │  └─ proxy（DiscoveryRegistry） │
                        └──┬───────┬───────┬───────┬────┘
                           │探测/转发│       │       │
                    ┌──────▼──┐ ┌──▼──────┐ ┌─▼──────┐ ┌─▼──────┐
                    │ OpenLLM │ │ OpenRAG │ │Memory  │ │  DPS   │
                    │ 8001    │ │ 8010    │ │ 8020   │ │ 8030   │
                    └─────────┘ └─────────┘ └────────┘ └────────┘
```

## 2. 环境配置矩阵

| 配置键 | Dev | Test | Pro |
|--------|-----|------|-----|
| `gateway.discovery.enabled` | true | true | true |
| `gateway.discovery.interval` | 10s | 10s | 10s |
| `gateway.discovery.health_path` | /health | /health | /health |
| `gateway.discovery.ttl` | 60s | 60s | 60s |
| `proxy.openllm.instances` | `[{"host":"127.0.0.1","port":8001}]` | 多实例可配 | 多实例可配 |
| `proxy.openrag.instances` | 同上（8010） | 同左 | 同左 |
| `proxy.openmemory.instances` | 同上（8020） | 同左 | 同左 |
| `proxy.dps.instances` | 同上（8030） | 同左 | 同左 |
| 静态表兜底 `PROXY_SYSTEMS` | 保留（默认值） | 保留 | 保留 |

## 3. 部署要点

| 项 | 说明 |
|----|------|
| 组件部署 | gateway 模块随 OpenBase 后端同进程部署（FastAPI app 挂载路由 + 生命周期注册 scheduler job），无独立进程/容器 |
| scheduler 集成 | 网关启动时注册健康探测 interval job（`id="gateway_probe"`），随模块启停；复用现有 scheduler 封装 |
| 实例注册方式 | 阶段一推荐 config 驱动（`proxy.{system}.instances` 热加载）+ 动态注册 API（四系统启动时 POST /api/v1/services）双通道 |
| 前端部署 | 26 项新页面随统一前端构建产物发布；网关管理页依赖后端网关 API |
| 数据库 | 无新增表（网关注册表内存态 + config 持久化兜底） |

## 4. 验证清单（部署后）

| # | 验证项 | 通过标准 |
|---|--------|---------|
| 1 | 网关 API 可用 | GET /api/v1/gateway/health 返回 200 + 实例信息 |
| 2 | 实例感知 | 停止/启动某系统后 ≤30s 内服务列表健康状态变化 |
| 3 | 故障剔除 | 连续 3 次探测失败实例从候选池移除，请求避开 |
| 4 | 聚合可用 | POST /api/v1/gateway/aggregate 聚合 2 系统数据返回正确 |
| 5 | 向后兼容 | 关闭 discovery 后 /api/v1/proxy/* 行为与 v1.3.0 一致 |
| 6 | 前端页面 | 26 项新页面可访问，网关管理页健康状态实时刷新 |

## 5. 回滚方案

| 场景 | 动作 |
|------|------|
| 网关探测导致流量异常 | 设 `gateway.discovery.enabled=false` 回退静态表（v1.3.0 行为），无需重启代码 |
| 前端页面回归 | 静态资源版本回退 |
| 聚合 API 异常 | 聚合端点为新增能力，直接禁用不影响既有 proxy |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-28 | AA-OpenBase-Dev | 初始创建：网关模块随 OpenBase 后端同进程部署 + 环境配置矩阵 + 部署验证清单 + 回滚方案 |
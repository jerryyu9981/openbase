# OpenBase API 接口设计文档 - v1.4.0

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

## 1. 设计范围

本版本 API 设计涵盖：①统一网关新增 API（服务发现 `/api/v1/services` + 网关管理 `/api/v1/gateway/*`，对齐《网关服务发现与聚合编排技术方案》§5）；②四系统对接沿用既有代理链路（`/api/v1/proxy/{system}/*`，契约以独立前端已验证实现为基线）。本版本无四系统后端新 API。

## 2. 统一网关 API（DT-14-25~26，RT-425~426）

### 2.1 服务发现 API（/api/v1/services）

| 方法 | 路径 | 说明 | 鉴权 | 请求 | 响应 |
|------|------|------|:---:|------|------|
| GET | `/api/v1/services` | 全部服务实例列表（含健康状态） | Bearer + `gateway:view` | - | `{code:0, data:{systems:[{system, instances:[ServiceInstance]}]}}` |
| GET | `/api/v1/services/{system}` | 指定系统实例列表 | Bearer + `gateway:view` | - | `{code:0, data:{instances:[ServiceInstance]}}` |
| POST | `/api/v1/services` | 实例注册（四系统启动时调用） | Bearer + `gateway:register` | `{system, instance_id?, host, port, weight?=1, meta?}` | `{code:0, data:{instance_id}}` |
| DELETE | `/api/v1/services/{system}/{instance_id}` | 实例下线 | Bearer + `gateway:register` | - | `{code:0}` |
| GET | `/api/v1/gateway/health` | 网关发现层健康状态 | Bearer + `gateway:view` | - | `{code:0, data:{systems:[{system, healthy, instance_count, health_rate}]}}` |
| GET | `/api/v1/gateway/ping` | 四系统连通性一键检测 | Bearer + `gateway:view` | - | `{code:0, data:{results:[{system, reachable, latency_ms}]}}` |

**ServiceInstance 响应模型**：

```json
{
  "system": "openllm",
  "instance_id": "127.0.0.1:8001",
  "host": "127.0.0.1",
  "port": 8001,
  "weight": 1,
  "healthy": true,
  "last_heartbeat": 1756350000.123,
  "consecutive_failures": 0,
  "meta": {}
}
```

### 2.2 聚合编排 API（/api/v1/gateway/aggregate）

| 方法 | 路径 | 说明 | 鉴权 | 请求 | 响应 |
|------|------|------|:---:|------|------|
| POST | `/api/v1/gateway/aggregate` | 聚合编排执行（代码式，阶段一） | Bearer + `gateway:aggregate` | `AggregateRequest` | `{code:0, data:{result}, errors?}` |

**AggregateRequest 请求模型（阶段一代码式）**：

```json
{
  "timeout_ms": 5000,
  "on_partial_failure": "return_errors",
  "steps": [
    {"id": "models", "system": "openllm", "path": "/models", "method": "GET", "timeout_ms": 2000},
    {"id": "kbs", "system": "openrag", "path": "/kb/list", "method": "GET", "timeout_ms": 2000}
  ],
  "mapping": {
    "model_count": "${models.data.total}",
    "kb_count": "${kbs.data.total}"
  }
}
```

**响应模型**：

```json
{
  "code": 0,
  "data": {
    "model_count": 12,
    "kb_count": 5
  },
  "errors": []
}
```

**错误码**（网关域）：`SYS_TIMEOUT`（503，整体超时）、`PARAM_AGGREGATE_STEP_INVALID`（步骤非法）、`BIZ_AGGREGATE_PARTIAL_FAILURE`（部分失败，含 errors 明细）。

### 2.3 阶段二预留（本版本不实现）

- `GET /api/v1/gateway/aggregate/{dsl_id}`（查询已注册 DSL 定义）
- `POST /api/v1/gateway/aggregate/{dsl_id}`（执行已注册 DSL）
- DSL 注册表存储于 config 键 `gateway.aggregates.*`

## 3. 四系统对接 API（DT-14-N5，RT-N405）

沿用 v1.3.0 代理链路：统一前端请求 `GET/POST /api/v1/proxy/{system}/{path}?{query}`（system ∈ openllm/openrag/openmemory/dps），OpenBase 代理层转发至四系统真实 API，返回统一包装 `{code, message, detail, request_id}`；SSE 流式透传（对话/事件流）；四系统不可用返回 502 统一包装（`SYS_502`），配额类返回 402（`BIZ_MODEL_QUOTA`）。

**契约基线**：以独立前端已验证实现为基线逐项核对（RT-N402-1），缺口登记 v1.4.x 补。

## 4. 错误码规范（网关域增量）

| 错误码 | HTTP | 场景 |
|--------|:---:|------|
| `SYS_TIMEOUT` | 503 | 聚合整体超时 |
| `PARAM_AGGREGATE_STEP_INVALID` | 400 | 聚合步骤非法（系统不在白名单/路径非法） |
| `BIZ_AGGREGATE_PARTIAL_FAILURE` | 200 | 部分步骤失败（return_errors 策略，data 含成功部分 + errors 明细） |
| `PERM_GATEWAY_REGISTER` | 403 | 无 gateway:register 权限 |
| `PERM_GATEWAY_AGGREGATE` | 403 | 无 gateway:aggregate 权限 |
| `PERM_GATEWAY_VIEW` | 403 | 无 gateway:view 权限 |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-28 | AA-OpenBase-Dev | 初始创建：网关 API 设计（/api/v1/services + /api/v1/gateway/* 契约与错误码）+ 四系统对接沿用代理链路说明 |
# OpenBase API 接口设计文档 - v1.4.5

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.5 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | SA-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 存放 | doc/design/ |

---

## 1. 接口总览

本版本新增 OpenBase 侧 `dps-proxy` 路由族（前缀 `/api/v1/dps-proxy`），全部端点要求 **OpenBase JWT 认证**（`get_current_user`，未认证 401）。**身份头注入**（DPS Header 身份认证）：proxy 从 OpenBase JWT/用户上下文构造四头注入上游，前端不可自定义。

| # | 方法 | 路径 | 说明 | 上游 | 响应类型 |
|---|------|------|------|------|---------|
| 1 | GET | /api/v1/dps-proxy/portraits | 画像列表 | /api/v2/portrait/list | 统一 JSON |
| 2 | GET | /api/v1/dps-proxy/portraits/{person_id} | 画像详情 | /api/v2/portrait/{person_id} | 统一 JSON |
| 3 | POST | /api/v1/dps-proxy/portraits/calculate | 画像计算 | /api/v2/portrait/calculate | 统一 JSON |
| 4 | GET | /api/v1/dps-proxy/tags/categories | 标签分类 | /api/v2/tags/categories | 统一 JSON |
| 5 | GET | /api/v1/dps-proxy/reports/overview | 报表概览 | /api/v2/reports/overview | 统一 JSON |
| 6 | GET | /api/v1/dps-proxy/batch/tasks/{task_id} | 批量任务状态 | /api/v2/batch/import/{task_id}/status | 统一 JSON |
| 7 | GET | /api/v1/dps-proxy/audit/logs | 审计日志 | /api/v2/audit/logs | 统一 JSON |
| 8 | GET | /api/v1/dps-proxy/health | 上游健康 | /health/liveness | 统一 JSON |

## 2. 身份头注入规范

| 上游头 | 来源 | 优先级 | 说明 |
|--------|------|:------:|------|
| X-User-ID | `get_current_user()["id"]`（JWT sub） | 1 | int→str 注入 |
| X-Tenant-ID | JWT payload `tenant_id` → `dps_default_tenant_id` → 映射表 `dps_tenant_map` | 1→2→3 | 值转换（映射表命中优先） |
| X-Org-ID | JWT payload extra `org_id` → `dps_default_org_id` → 映射表 `dps_org_map` | 1→2→3 | 值转换（映射表命中优先） |
| X-User-Role | JWT payload extra `role`（缺省 "user"） | 1 | 可选透传 |

> 映射规则：映射表 `dps_org_map`/`dps_tenant_map` 为 JSON（OpenBase 值 → DPS 值），命中则转换；未配置或未命中则直传原值；原值缺失用 `dps_default_*` 兜底。联调确认 1:1 直传可行性（OQ-145-1）。

## 3. 统一响应契约

### 3.1 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": { "..." : "上游 data 字段（网关结构）或完整响应体（非网关结构）" },
  "timestamp": "2026-08-31T08:00:00+00:00"
}
```

### 3.2 错误响应（{detail} 归一化）

```json
{
  "code": 404,
  "message": "画像不存在: xxx",
  "data": null,
  "timestamp": "2026-08-31T08:00:00+00:00"
}
```

> 提取顺序：`body.code`（非 0）→ `body.detail.error/code`（dict）→ `body.detail`（str）→ `body.detail`（list 提取 msg）→ HTTP 状态码。

## 4. 端点详细定义

### 4.1 画像族（1~3）

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT + 四头注入 |
| 列表参数 | page: int default 1；page_size: int default 20（透传上游） |
| 详情 | person_id 路径参数 |
| 计算请求体 | {person_id?, data?, ...}（透传上游契约，proxy 不强制 schema） |
| 成功 data | 上游对象/分页结果 |

### 4.2 标签/报表族（4~5）

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT + 四头注入 |
| 标签分类 | GET 透传 |
| 报表概览 | GET 透传 |

### 4.3 批量/审计族（6~7）

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT + 四头注入 |
| 批量任务状态 | task_id 路径参数 |
| 审计日志 | GET 透传（可选分页参数） |

### 4.4 健康（8）

| 项 | 内容 |
|----|------|
| 认证 | OpenBase JWT |
| 上游 | GET /health/liveness（DPS 白名单免鉴权） |
| 成功 data | {status: healthy/unhealthy, checks, version, timestamp} |
| 失败 | 上游不可达 → 502 级（SYS_UPSTREAM_ERROR） |

## 5. 错误码表（OpenBase 侧）

| 错误码 | 含义 | HTTP | 场景 |
|--------|------|:---:|------|
| AUTH_UNAUTHORIZED | 未认证 | 401 | 无/无效 OpenBase JWT |
| SYS_UPSTREAM_ERROR | 上游不可达 | 502 | DPS 连接失败/超时 |
| PARAM_INVALID | 参数缺失 | 422 | 必填参数缺失（proxy 侧 schema 校验） |

> 上游错误（404/422/500 + {detail}）归一化后透传 code/message，不映射为 OpenBase 错误码表。

## 6. 契约对齐记录（前后端）

| 检查项 | 结果 |
|--------|------|
| 前端页面 ↔ 后端 API | 画像列表页 → 端点 1/2/8；画像详情页 → 端点 2/4/8 |
| 统一响应解析 | 前端 http.ts 已有统一响应处理，dps-proxy 响应兼容 |
| 鉴权 | 全部端点 OpenBase JWT，前端走既有 auth store |
| 无 SSE | 前端无需流式消费（DPS 无 SSE） |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | SA-OpenBase-Dev | 初始创建：dps-proxy 8 端点契约（统一响应/{detail} 归一化/身份头注入规范）+ 前后端契约对齐记录 |

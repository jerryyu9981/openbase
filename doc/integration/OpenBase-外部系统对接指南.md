# OpenBase 外部系统使用与对接指南

| 项目 | 内容 |
|------|------|
| 文档名称 | OpenBase 外部系统使用与对接指南 |
| 文档版本 | v1.0.0 |
| 适用版本 | OpenBase v1.3.0 |
| 状态 | [Final] |
| 作者 | OpenBase 平台组 |
| 日期 | 2026-08-27 |
| 存放 | doc/integration/ |

---

## 1. 平台概述

OpenBase 是统一基础设施公共底座，为四系统（OpenLLM / OpenRAG / OpenMemory / DPS）及未来类似系统提供：统一认证鉴权、多租户隔离、统一代理接入、统一错误码、统一日志与请求追踪。

### 1.1 对接架构

```
┌─────────────┐     ┌──────────────────────────────────────────┐
│  外部系统     │────▶│  OpenBase（基址 http://<host>:8000）        │
│  (OpenLLM/  │     │  ├─ /api/v1/auth/*      认证与鉴权          │
│   OpenRAG/  │     │  ├─ /api/v1/tenants/*   多租户与配额         │
│   OpenMemory│     │  ├─ /api/v1/proxy/{system}/*  系统代理接入    │
│   /DPS/第三方)│    │  └─ 统一响应/错误码/日志/request_id          │
└─────────────┘     └──────────────────────────────────────────┘
```

### 1.2 对接方式

| 方式 | 适用场景 | 说明 |
|------|---------|------|
| 方式 A：直接调用 OpenBase API | 独立系统/前端接入认证与基础能力 | 调 auth/tenants 等基座接口 |
| 方式 B：经统一代理接入 | 通过 OpenBase 访问四系统后端 | `/api/v1/proxy/{system}/{path}` 透传 |
| 方式 C：统一前端集成 | 作为动态模块注册进统一前端 | 路由懒加载 + 导航注册 + RBAC 权限 |

---

## 2. 快速开始

### 2.1 环境要求

| 依赖 | 说明 |
|------|------|
| Python ≥ 3.10 | 后端运行环境 |
| Node.js ≥ 18 | 前端构建环境 |
| PostgreSQL | 生产数据库（可选，内存降级可用） |
| Redis | 缓存（可选，不可用时自动降级） |

### 2.2 启动服务

```bash
# 后端（端口 8000）
python -m uvicorn openbase.demo_app:app --port 8000

# 前端（端口 5173，/api 代理 → 8000；生产用 Nginx 托管 dist/ + 反代 /api）
cd openbase-ui && npx vite preview --port 5173
```

### 2.3 默认账号

| 账号 | 密码 | 权限 |
|------|------|------|
| admin | admin123 | 管理员（permissions=["*"]） |

> ⚠️ 生产环境必须修改默认密码并配置真实数据库。

---

## 3. 认证与鉴权

### 3.1 登录获取 Token

```
POST /api/v1/auth/login
Content-Type: application/json

{"username": "admin", "password": "admin123"}
```

成功响应：

```json
{
  "code": 0,
  "data": {
    "access_token": "<JWT>",
    "refresh_token": "<JWT>",
    "token_type": "bearer"
  },
  "traceId": "req-xxx"
}
```

### 3.2 Token 使用

所有受保护接口（除 `/auth/login` 等公开接口外）必须携带：

```
Authorization: Bearer <access_token>
```

### 3.3 刷新 Token

```
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>
```

### 3.4 当前用户信息

```
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

响应示例：

```json
{
  "code": 0,
  "data": {
    "username": "admin",
    "permissions": ["*"],
    "tenants": []
  },
  "traceId": "req-xxx"
}
```

### 3.5 多租户上下文（X-Tenant-Id）

多租户系统请求需携带租户头，OpenBase 通过 `TenantMiddleware` 从以下位置提取租户：

| 优先级 | 来源 | 示例 |
|:---:|------|------|
| 1 | Header | `X-Tenant-Id: tenant_a`、`X-User-Id: u1` |
| 2 | Path 参数 | `/api/v1/.../{tenant_id}/...` |
| 3 | Query 参数 | `?tenant_id=tenant_a` |

查询当前租户上下文：

```
GET /api/v1/tenants/context
X-Tenant-Id: tenant_a
X-User-Id: u1
Authorization: Bearer <token>
```

```json
{"code": 0, "data": {"tenant": "tenant_a", "user": "u1"}, "traceId": "req-xxx"}
```

> 无 Token 访问返回 401；租户上下文在请求结束时自动清理。

---

## 4. 统一 API 规范

### 4.1 基址

| 环境 | 基址 |
|------|------|
| 本地 Dev | `http://127.0.0.1:8000/api/v1` |
| 生产 | `https://<domain>/api/v1` |

### 4.2 统一响应格式

**成功**：

```json
{ "code": 0, "data": { ... }, "traceId": "req-xxx" }
```

**失败**（统一错误响应）：

```json
{
  "code": "BIZ_MODEL_QUOTA",
  "message": "模型服务余额不足，请联系管理员充值",
  "detail": "upstream payment required",
  "request_id": "req-xxx"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 错误码（见 §4.3）；HTTP 200 时可能为 `0` |
| message | string | 人类可读错误信息 |
| detail | string | 详细原因（可选） |
| request_id | string | 请求追踪 ID（日志排障用） |

### 4.3 错误码表

| 错误码 | HTTP | 含义 | 处理建议 |
|--------|:---:|------|---------|
| `AUTH_401` | 401 | 未认证（token 缺失/失效） | 重新登录或刷新 token |
| `AUTH_403` | 403 | 无权限（RBAC 拒绝） | 检查账号权限 |
| `AUTH_404` | 404 | 认证目标不存在 | 检查请求 |
| `PERM_*` | 403 | 权限不足 | 联系管理员授权 |
| `PARAM_*` | 422 | 参数校验失败 | 按 detail 修正参数 |
| `BIZ_404` | 404 | 业务资源不存在 | 检查资源 ID |
| `BIZ_MODEL_QUOTA` | **402** | 模型服务余额不足 | 联系提供商充值或检查配额 |
| `BIZ_TENANT_EXISTS` | 409 | 租户编码已存在 | 更换租户编码 |
| `BIZ_TENANT_NOT_FOUND` | 404 | 租户不存在 | 检查租户编码 |
| `SYS_502` | 502 | 上游系统不可达 | 检查上游服务（OpenLLM:8001 等） |
| `SYS_500` | 500 | 系统内部错误 | 携带 request_id 反馈 |

### 4.4 请求追踪

每个响应携带 `traceId`/`request_id`，日志中按此 ID 串联全链路。排障时请提供该 ID。

---

## 5. 多租户与配额管理 API

### 5.1 租户管理

```
# 创建租户（需管理员权限）
POST /api/v1/tenants

# 租户列表
GET /api/v1/tenants

# 租户详情
GET /api/v1/tenants/{tenant_code}
```

### 5.2 配额管理

```
# 设置配额
POST /api/v1/tenants/{tenant}/quota?resource=models&limit=100

# 查询配额与用量
GET /api/v1/tenants/{tenant}/quota?resource=models
```

响应示例：

```json
{"code": 0, "data": {"tenant": "tenant_a", "resource": "models", "limit": 100, "usage": 0, "allowed": true}}
```

> 配额资源：`models`（模型数）/ `tokens`（Token 配额）/ `seats`（席位）。`usage >= limit` 时 `allowed=false`。

---

## 6. 四系统代理接入（方式 B）

### 6.1 代理路由规则

```
GET/POST /api/v1/proxy/{system}/{path}?{query}
Authorization: Bearer <token>
```

| 参数 | 说明 | 可用值 |
|------|------|--------|
| system | 目标系统 | openllm / openrag / openmemory / dps |
| path | 目标系统 API 路径 | 如 `chat/stream`、`kb/list` |
| query | 透传给上游的查询参数 | - |

### 6.2 代理行为

| 场景 | 行为 |
|------|------|
| 上游 200 | 原样透传上游 JSON |
| 上游 **402** | 统一包装为 `BIZ_MODEL_QUOTA`（HTTP 402），**不暴露上游原始响应** |
| 上游 502/不可达 | 统一包装为 `SYS_502`（HTTP 502） |
| 无 token | 401 拦截 |

### 6.3 代理调用示例

```bash
# 调用 OpenLLM 健康检查
curl -X GET "http://127.0.0.1:8000/api/v1/proxy/openllm/health" \
  -H "Authorization: Bearer $TOKEN"

# 调用 OpenRAG 知识库列表
curl -X GET "http://127.0.0.1:8000/api/v1/proxy/openrag/kb/list" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: tenant_a"

# 调用 OpenLLM 流式对话（SSE）
curl -N -X POST "http://127.0.0.1:8000/api/v1/proxy/openllm/chat/stream" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "你好"}]}'
```

---

## 7. 对接代码示例

### 7.1 Python（httpx/requests）

```python
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

def login(username: str, password: str) -> str:
    resp = httpx.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    resp.raise_for_status()
    return resp.json()["data"]["access_token"]

def call_proxy(token: str, system: str, path: str, method: str = "GET", **kwargs):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/proxy/{system}/{path}"
    resp = httpx.request(method, url, headers=headers, **kwargs)
    if resp.status_code == 402:      # 余额不足
        body = resp.json()
        raise RuntimeError(f"模型余额不足: {body['code']} - {body['message']}")
    if resp.status_code == 502:      # 上游不可达
        raise RuntimeError(f"上游系统不可达: {resp.json()['message']}")
    resp.raise_for_status()
    return resp.json()

token = login("admin", "admin123")
data = call_proxy(token, "openllm", "health")
print(data)
```

### 7.2 前端（axios 封装）

```typescript
// api/client.ts —— OpenBase 对接客户端
import axios from 'axios'

const client = axios.create({ baseURL: '/api/v1' })

// Token 注入
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('ob_access_token')
  const tenant = localStorage.getItem('ob_tenant_id')
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (tenant) config.headers['X-Tenant-Id'] = tenant
  return config
})

// 统一错误处理（含 402 余额不足）
client.interceptors.response.use(
  (resp) => resp.data,
  (error) => {
    const body = error.response?.data
    if (error.response?.status === 402) {
      // BIZ_MODEL_QUOTA：提示用户联系管理员充值
      ElMessage.error(body?.message || '模型服务余额不足')
    } else if (body?.request_id) {
      console.error(`请求失败 request_id=${body.request_id}`)
    }
    return Promise.reject(error)
  }
)

export default client

// 使用示例
// const models = await client.get('/proxy/openllm/models')
// const me = await client.get('/auth/me')
```

---

## 8. 安全指南

| 项 | 要求 |
|----|------|
| Token 存储 | 前端存 localStorage（`ob_access_token`/`ob_refresh_token`），生产建议 HttpOnly Cookie + HTTPS |
| 密钥管理 | API Key/密码不得出现在日志、代码仓库、前端代码；使用环境变量或密钥管理服务 |
| HTTPS | 生产环境强制 TLS；禁止明文传输 Token |
| 日志脱敏 | 禁止记录：密码、令牌、密钥、完整请求体、个人隐私 |
| 输入校验 | 所有外部输入经 Pydantic 校验；防止 SQL 注入/XSS（平台已内置） |
| 权限 | 按 RBAC 最小权限分配；多租户数据操作必须带 tenant 过滤 |

---

## 9. 限流与配额

| 机制 | 说明 |
|------|------|
| 租户配额 | 平台级配额（models/tokens/seats），超额 `allowed=false` |
| 限流 | 生产环境按租户配置 RPS 限流（Nginx/网关层） |

---

## 10. 常见问题排查（FAQ）

| 现象 | 原因 | 处理 |
|------|------|------|
| 401 未认证 | token 缺失/过期 | 重新登录或调 `/auth/refresh` |
| 403 无权限 | RBAC 权限不足 | 联系管理员授权 |
| **402 余额不足** | 模型提供商账户余额耗尽 | 联系提供商充值；前端展示"模型服务余额不足" |
| 502 上游不可达 | 目标系统（OpenLLM:8001 等）未启动 | 启动对应系统后重试 |
| 登录慢（5-10s） | bcrypt 计算（内存模式） | 正常现象；或升级数据库存储 |
| 日志提示 database/redis fallback | PG/Redis 未启动 | 启动依赖服务后重启后端 |
| request_id 排查 | 报错时提供 request_id | 日志中 `grep <request_id>` 定位全链路 |

---

## 11. 版本兼容

| OpenBase 版本 | 变更 |
|--------------|------|
| v1.0.0 | 基座初始化（auth/租户/代理） |
| v1.1.0 | 统一前端四模块接入 |
| v1.2.0 | E2E 缺陷修复、基座完善 |
| **v1.3.0（当前）** | 前端完整 30 页 + 基座调试完整 + 402 错误码 + 租户管理页面；四系统对接挂起分批 |

> 对接约定以本文档为准；API 契约变更会同步更新本文档版本。

# OpenBase 外部系统使用与对接指南（全版本）

| 项目 | 内容 |
|------|------|
| 文档名称 | OpenBase 外部系统使用与对接指南（全版本） |
| 文档版本 | v1.1.0 |
| 适用版本 | OpenBase v1.0.0 ~ v1.3.0（长期维护，随版本演进） |
| 状态 | [Final] |
| 作者 | OpenBase 平台组 |
| 日期 | 2026-08-27 |
| 存放 | doc/integration/ |

> 本文档为**全版本长期文档**：覆盖 OpenBase 自 v1.0.0 起的全部对外能力与 API，各版本新增/变更通过"版本演进"与"版本兼容"章节追踪。对接方无需回看单版本文档。

---

## 1. 平台概述

OpenBase 是统一基础设施公共底座，为四系统（OpenLLM / OpenRAG / OpenMemory / DPS）及未来类似系统提供：统一认证鉴权、多租户隔离、统一代理接入、统一错误码、统一日志与请求追踪、组织/配置/通知/审计/可观测等平台级能力。

### 1.1 能力全景

| 能力域 | 模块 | 说明 | 引入版本 |
|--------|------|------|:---:|
| 认证与 RBAC | auth | 登录/刷新/当前用户 + 权限管理 | v1.0.0 |
| 多租户 | tenant | 租户上下文注入 + 配额管理 | v1.0.0 |
| 组织架构 | org | 部门 CRUD + 树查询 | v1.0.0 |
| 配置中心 | config | 配置读写/版本/回滚 | v1.0.0 |
| 通知 | notify | 通知创建/列表/SSE 流 | v1.0.0 |
| 审计 | audit | 审计记录查询 | v1.0.0 |
| 可观测 | observability | 运行状态 | v1.0.0 |
| AI 应用 | ai_apps | 应用 CRUD/发布/版本/调用 | v1.2.0 |
| 统一代理 | proxy | 四系统后端统一接入（402/502 包装） | v1.2.0（402 v1.3.0） |
| 动态模块 | frontend | 统一前端模块注册发现 | v1.2.0 |
| 租户管理 UI | frontend | 租户管理页面（前端） | v1.3.0 |

### 1.2 对接架构

```
┌─────────────┐     ┌────────────────────────────────────────────────┐
│  外部系统     │────▶│  OpenBase（基址 http://<host>:8000）              │
│  (OpenLLM/  │     │  /api/v1/auth/*        认证/RBAC                │
│   OpenRAG/  │     │  /api/v1/tenants/*     多租户/配额               │
│   OpenMemory│     │  /api/v1/org/*         组织架构                  │
│   /DPS/第三方)│    │  /api/v1/configs/*     配置中心                  │
│            │     │  /api/v1/notifications/*  通知                   │
│            │     │  /api/v1/audit/*        审计                     │
│            │     │  /api/v1/ai-apps/*      AI 应用                   │
│            │     │  /api/v1/modules/*      动态模块                  │
│            │     │  /api/v1/proxy/{system}/*  系统代理接入            │
│            │     │  /api/v1/observability/*  可观测                  │
│            │     └─ 统一响应/错误码/日志/request_id                  │
└─────────────┘     └────────────────────────────────────────────────┘
```

### 1.3 对接方式

| 方式 | 适用场景 | 说明 | 版本 |
|------|---------|------|:---:|
| A：直接调用 OpenBase API | 独立系统/前端接入平台能力 | 认证/租户/配置/通知/审计等 | v1.0.0+ |
| B：统一代理接入 | 通过 OpenBase 访问四系统后端 | `/api/v1/proxy/{system}/{path}` | v1.2.0+ |
| C：统一前端集成 | 作为动态模块注册进统一前端 | 路由懒加载 + 导航 + RBAC | v1.2.0+ |

---

## 2. 版本演进

| 版本 | 主题 | 对外能力变化 | 兼容性 |
|------|------|-------------|:---:|
| v1.0.0 | 基座初始化 | auth/tenant/org/config/notify/audit/observability 上线 | - |
| v1.1.0 | 统一前端四模块接入 | 前端接入（方式 C 雏形） | 向后兼容 |
| v1.2.0 | E2E 缺陷修复 + 基座完善 | 新增 ai_apps/proxy/frontend（方式 B/C 完整化） | 向后兼容 |
| **v1.3.0** | 前端完整 + 基座调试 | 402 错误码（BIZ_MODEL_QUOTA）、租户管理 UI、前端 30 页完整 | 向后兼容 |

> 平台遵循语义化版本：破坏性变更升主版本，新增能力升次版本。v1.0.0→v1.3.0 无破坏性变更，对接方可平滑升级。

---

## 3. 快速开始

### 3.1 环境要求

| 依赖 | 说明 |
|------|------|
| Python ≥ 3.10 | 后端运行环境 |
| Node.js ≥ 18 | 前端构建环境 |
| PostgreSQL | 生产数据库（可选，内存降级可用） |
| Redis | 缓存（可选，不可用时自动降级） |

### 3.2 启动服务

```bash
# 后端（端口 8000）
python -m uvicorn openbase.demo_app:app --port 8000

# 前端（端口 5173，/api 代理 → 8000；生产用 Nginx 托管 dist/ + 反代 /api）
cd openbase-ui && npx vite preview --port 5173
```

### 3.3 默认账号

| 账号 | 密码 | 权限 |
|------|------|------|
| admin | admin123 | 管理员（permissions=["*"]） |

> ⚠️ 生产环境必须修改默认密码并配置真实数据库。

---

## 4. 认证与鉴权

### 4.1 登录获取 Token

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

### 4.2 Token 使用

所有受保护接口必须携带：`Authorization: Bearer <access_token>`

### 4.3 刷新 Token

```
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>
```

### 4.4 当前用户信息

```
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

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

### 4.5 权限（RBAC）

权限按 `resource:action` 命名（如 `user:list`）。`permissions` 含 `*` 表示超级权限。需要权限的接口返回 403。

### 4.6 多租户上下文（X-Tenant-Id）

| 优先级 | 来源 | 示例 |
|:---:|------|------|
| 1 | Header | `X-Tenant-Id: tenant_a`、`X-User-Id: u1` |
| 2 | Path 参数 | `/api/v1/.../{tenant_id}/...` |
| 3 | Query 参数 | `?tenant_id=tenant_a` |

查询当前租户上下文：

```
GET /api/v1/tenants/context
X-Tenant-Id: tenant_a  X-User-Id: u1  Authorization: Bearer <token>
```

---

## 5. 统一 API 规范

### 5.1 基址

| 环境 | 基址 |
|------|------|
| 本地 Dev | `http://127.0.0.1:8000/api/v1` |
| 生产 | `https://<domain>/api/v1` |

### 5.2 统一响应格式

**成功**：`{ "code": 0, "data": { ... }, "traceId": "req-xxx" }`

**失败**（统一错误响应）：

```json
{
  "code": "BIZ_MODEL_QUOTA",
  "message": "模型服务余额不足，请联系管理员充值",
  "detail": "upstream payment required",
  "request_id": "req-xxx"
}
```

### 5.3 错误码表（全版本累计）

| 错误码 | HTTP | 含义 | 引入版本 | 处理建议 |
|--------|:---:|------|:---:|---------|
| `AUTH_401` | 401 | 未认证 | v1.0.0 | 重新登录/刷新 token |
| `AUTH_403` | 403 | 无权限 | v1.0.0 | 检查 RBAC 权限 |
| `AUTH_404` | 404 | 认证目标不存在 | v1.0.0 | 检查请求 |
| `PERM_*` | 403 | 权限不足 | v1.0.0 | 联系管理员 |
| `PARAM_*` | 422 | 参数校验失败 | v1.0.0 | 按 detail 修正 |
| `BIZ_404` | 404 | 业务资源不存在 | v1.0.0 | 检查资源 ID |
| `BIZ_TENANT_EXISTS` | 409 | 租户编码已存在 | v1.0.0 | 更换编码 |
| `BIZ_TENANT_NOT_FOUND` | 404 | 租户不存在 | v1.0.0 | 检查编码 |
| `BIZ_CONFIG_CONFLICT` | 409 | 配置冲突 | v1.0.0 | 检查配置键 |
| `STORAGE_FILE_NOT_FOUND` | 404 | 存储文件不存在 | v1.0.0 | 检查文件 |
| `BIZ_MODEL_QUOTA` | **402** | 模型服务余额不足 | **v1.3.0** | 充值/检查配额 |
| `SYS_502` | 502 | 上游系统不可达 | v1.2.0 | 启动上游系统 |
| `SYS_500` | 500 | 系统内部错误 | v1.0.0 | 带 request_id 反馈 |

### 5.4 请求追踪

每个响应携带 `traceId`/`request_id`，日志按此 ID 串联全链路。排障请提供该 ID。

---

## 6. API 参考全集（10 模块）

### 6.1 认证 auth（v1.0.0+）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| POST | `/api/v1/auth/login` | 登录获取 Token | 公开 |
| POST | `/api/v1/auth/refresh` | 刷新 Token | Bearer(refresh) |
| GET | `/api/v1/auth/me` | 当前用户信息 | Bearer |

### 6.2 多租户 tenant（v1.0.0+）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| GET | `/api/v1/tenants/context` | 当前租户上下文 | Bearer + X-Tenant-Id |
| POST | `/api/v1/tenants/{tenant}/quota?resource=&limit=` | 设置配额 | Bearer |
| GET | `/api/v1/tenants/{tenant}/quota?resource=` | 查询配额/用量 | Bearer |

配额资源：`models` / `tokens` / `seats`。响应 `{"tenant","resource","limit","usage","allowed"}`。

### 6.3 组织架构 org（v1.0.0+）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| POST | `/api/v1/org/departments` | 创建部门 | Bearer |
| GET | `/api/v1/org/departments` | 部门列表 | Bearer |
| GET | `/api/v1/org/departments/tree` | 部门树 | Bearer |
| DELETE | `/api/v1/org/departments/{dep_id}` | 删除部门 | Bearer |

### 6.4 配置中心 config（v1.0.0+）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| POST | `/api/v1/configs` | 写入配置 | Bearer |
| GET | `/api/v1/configs/{key}` | 读取配置 | Bearer |
| GET | `/api/v1/configs/{key}/versions` | 配置版本历史 | Bearer |
| POST | `/api/v1/configs/{key}/rollback` | 回滚配置 | Bearer |

### 6.5 通知 notify（v1.0.0+）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| POST | `/api/v1/notifications` | 创建通知 | Bearer |
| GET | `/api/v1/notifications` | 通知列表 | Bearer |
| GET | `/api/v1/notifications/stream` | 通知 SSE 流 | Bearer |

### 6.6 审计 audit（v1.0.0+）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| GET | `/api/v1/audit/health` | 审计健康 | 公开 |
| GET | `/api/v1/audit/records` | 审计记录 | Bearer |

### 6.7 可观测 observability（v1.0.0+）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| GET | `/api/v1/observability/status` | 运行状态 | Bearer |

### 6.8 AI 应用 ai_apps（v1.2.0+）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| GET | `/api/v1/ai-apps` | 应用列表 | Bearer |
| POST | `/api/v1/ai-apps` | 创建应用 | Bearer |
| GET | `/api/v1/ai-apps/{app_id}` | 应用详情 | Bearer |
| PUT | `/api/v1/ai-apps/{app_id}` | 更新应用 | Bearer |
| DELETE | `/api/v1/ai-apps/{app_id}` | 删除应用 | Bearer |
| POST | `/api/v1/ai-apps/{app_id}/publish` | 发布应用 | Bearer |
| POST | `/api/v1/ai-apps/{app_id}/unpublish` | 取消发布 | Bearer |
| GET | `/api/v1/ai-apps/{app_id}/versions` | 版本列表 | Bearer |
| GET | `/api/v1/ai-apps/{app_id}/calls` | 调用记录 | Bearer |

### 6.9 动态模块 frontend（v1.2.0+）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| GET | `/api/v1/modules` | 已启用模块列表 | Bearer |
| GET | `/api/v1/modules/{module_id}` | 模块详情 | Bearer |

### 6.10 统一代理 proxy（v1.2.0+，402 v1.3.0）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| 任意 | `/api/v1/proxy/{system}/{path}` | 透传访问四系统后端 | Bearer |

---

## 7. 四系统代理接入（方式 B）

### 7.1 路由规则

```
GET/POST /api/v1/proxy/{system}/{path}?{query}
Authorization: Bearer <token>
X-Tenant-Id: <tenant>        # 可选，多租户
```

| system | 说明 |
|--------|------|
| openllm | OpenLLM 后端（端口 8001） |
| openrag | OpenRAG 后端 |
| openmemory | OpenMemory 后端 |
| dps | DPS 后端 |

### 7.2 代理行为（v1.3.0）

| 场景 | 行为 |
|------|------|
| 上游 200 | 原样透传上游 JSON |
| 上游 **402** | 统一包装 `BIZ_MODEL_QUOTA`（HTTP 402），不暴露上游原始响应 |
| 上游 502/不可达 | 统一包装 `SYS_502`（HTTP 502） |
| 无 token | 401 拦截 |

### 7.3 代理调用示例

```bash
# OpenLLM 健康检查
curl -X GET "http://127.0.0.1:8000/api/v1/proxy/openllm/health" -H "Authorization: Bearer $TOKEN"

# OpenRAG 知识库列表
curl -X GET "http://127.0.0.1:8000/api/v1/proxy/openrag/kb/list" -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: tenant_a"

# OpenLLM 流式对话（SSE）
curl -N -X POST "http://127.0.0.1:8000/api/v1/proxy/openllm/chat/stream" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "你好"}]}'
```

> ⚠️ v1.3.0 起四系统前端已完整（契约 mock），**后端实际对接按批次推进**（TD-006/007 跟踪）。代理层已验证可用（502 包装实测通过），对接批次启动时直接可用。

---

## 8. 统一前端集成（方式 C）

### 8.1 模块注册

外部系统前端作为动态模块接入统一前端：在 `openbase-ui/src/modules/{module}/index.ts` 导出 `routes`（vue-router 路由）+ `navItems`（侧边导航），核心路由加载器自动懒加载。

### 8.2 权限控制

路由 meta 标记模块权限；`permissions.includes('*') || permissions.includes(module.permission)` 校验，未授权跳回 `/dashboard`。

### 8.3 请求客户端

统一使用 `@/core/api/http.ts`（自动注入 JWT + `/api/v1` 基址 + 401 刷新重试）。对接四系统后端走 `proxy` 路径。

---

## 9. 代码示例

### 9.1 Python（httpx，完整封装）

```python
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

class OpenBaseClient:
    def __init__(self, username: str, password: str, tenant: str | None = None):
        self._tenant = tenant
        self._token = self._login(username, password)

    def _login(self, username: str, password: str) -> str:
        resp = httpx.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
        resp.raise_for_status()
        return resp.json()["data"]["access_token"]

    def _headers(self) -> dict:
        headers = {"Authorization": f"Bearer {self._token}"}
        if self._tenant:
            headers["X-Tenant-Id"] = self._tenant
        return headers

    def call(self, method: str, path: str, **kwargs):
        resp = httpx.request(method, f"{BASE_URL}/{path}", headers=self._headers(), **kwargs)
        if resp.status_code == 402:
            raise RuntimeError(f"模型余额不足: {resp.json()['message']}")
        if resp.status_code == 502:
            raise RuntimeError(f"上游不可达: {resp.json()['message']}")
        resp.raise_for_status()
        return resp.json()

client = OpenBaseClient("admin", "admin123", tenant="tenant_a")
data = client.call("GET", "proxy/openllm/health")
print(data)
```

### 9.2 前端（axios 封装）

```typescript
import axios from 'axios'

const client = axios.create({ baseURL: '/api/v1' })

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('ob_access_token')
  const tenant = localStorage.getItem('ob_tenant_id')
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (tenant) config.headers['X-Tenant-Id'] = tenant
  return config
})

client.interceptors.response.use(
  (resp) => resp.data,
  (error) => {
    const body = error.response?.data
    if (error.response?.status === 402) {
      // BIZ_MODEL_QUOTA：提示联系管理员充值
      ElMessage.error(body?.message || '模型服务余额不足')
    } else if (body?.request_id) {
      console.error(`请求失败 request_id=${body.request_id}`)
    }
    return Promise.reject(error)
  }
)
export default client
```

---

## 10. 安全指南

| 项 | 要求 |
|----|------|
| Token 存储 | 前端 localStorage（`ob_access_token`/`ob_refresh_token`）；生产建议 HttpOnly Cookie + HTTPS |
| 密钥管理 | API Key/密码不得出现在日志、仓库、前端代码；使用环境变量或密钥管理服务 |
| HTTPS | 生产强制 TLS；禁止明文传输 Token |
| 日志脱敏 | 禁止记录：密码、令牌、密钥、完整请求体、个人隐私 |
| 输入校验 | 所有外部输入经 Pydantic 校验（平台内置 SQL 注入/XSS 防护） |
| 权限 | RBAC 最小权限；多租户数据操作必须带 tenant 过滤 |

---

## 11. 限流与配额

| 机制 | 说明 |
|------|------|
| 租户配额 | `models`/`tokens`/`seats` 平台级配额，超额 `allowed=false`（v1.0.0+） |
| 上游余额 | 模型提供商余额不足 → 402（v1.3.0+） |
| 生产限流 | 按租户配置 RPS（Nginx/网关层） |

---

## 12. 常见问题排查（FAQ）

| 现象 | 原因 | 处理 |
|------|------|------|
| 401 未认证 | token 缺失/过期 | 重新登录或 `/auth/refresh` |
| 403 无权限 | RBAC 不足 | 联系管理员授权 |
| **402 余额不足** | 模型提供商余额耗尽 | 充值；前端展示"模型服务余额不足" |
| 502 上游不可达 | 目标系统未启动 | 启动对应系统后重试 |
| 登录慢（5-10s） | bcrypt 计算（内存模式） | 正常；或升级数据库存储 |
| database/redis fallback | PG/Redis 未启动 | 启动依赖后重启后端 |
| 404 接口不存在 | 版本不匹配 | 对照本文档 §6 API 参考全集核对版本 |
| request_id 排查 | 报错时提供 | 日志 `grep <request_id>` 定位全链路 |

---

## 13. 版本兼容与变更记录

| OpenBase 版本 | 新增/变更 | 破坏性变更 |
|--------------|----------|:---:|
| v1.0.0 | auth/tenant/org/config/notify/audit/observability 上线 | - |
| v1.1.0 | 统一前端四模块接入（方式 C 雏形） | 无 |
| v1.2.0 | ai_apps/proxy/frontend 上线；E2E 缺陷修复 | 无 |
| v1.3.0 | `BIZ_MODEL_QUOTA`(402) 错误码；代理 402 统一包装；租户管理 UI；前端 30 页完整 | 无 |

> 升级建议：v1.2.0 → v1.3.0 为向后兼容增量，直接升级即可；对接方新增处理 402 响应（见 §9 代码示例）。

---

## 14. 术语表

| 术语 | 说明 |
|------|------|
| 基座 | OpenBase 公共底座（认证/租户/代理等平台能力） |
| 四系统 | OpenLLM / OpenRAG / OpenMemory / DPS |
| 代理 | `/api/v1/proxy/{system}/*` 统一接入通道 |
| 动态模块 | 注册进统一前端的独立系统模块（方式 C） |
| 租户配额 | 按租户的资源限额（models/tokens/seats） |
| request_id | 全链路请求追踪 ID |

---

## 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-27 | OpenBase 平台组 | 初始创建（对应 v1.3.0 单版本对接） |
| v1.1.0 | 2026-08-27 | OpenBase 平台组 | 升级为全版本长期文档：新增版本演进、API 参考全集（10 模块 30+ 接口）、全版本错误码、版本兼容记录、方式 C 集成、术语表 |

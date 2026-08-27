# OpenBase 对接实操指南（三种接入方式：步骤与示例代码）

| 项目 | 内容 |
|------|------|
| 文档名称 | OpenBase 对接实操指南（三种接入方式：步骤与示例代码） |
| 文档版本 | v1.0.0 |
| 适用版本 | OpenBase v1.3.0 |
| 状态 | [Final] |
| 作者 | OpenBase 平台组 |
| 日期 | 2026-08-27 |
| 存放 | doc/integration/ |
| 配套文档 | 《OpenBase 外部系统使用与对接指南（全版本）》（API 参考全集） |

> 本文档是**实操手册**：聚焦三种接入方式的详细步骤与可直接复制的示例代码。API 契约细节见配套全版本指南。

---

## 0. 前置准备

| 项 | 值 |
|----|-----|
| 后端基址 | `http://127.0.0.1:8000`（生产：`https://<domain>`） |
| 测试账号 | admin / admin123（管理员，permissions=["*"]） |
| 工具 | curl / Python 3.10+（httpx）/ Node.js 18+ |
| 统一前端目录 | `openbase-ui/`（方式 C 需要） |

---

## 1. 方式 A：直接调用 OpenBase API（使用平台能力）

**用途**：外部系统后端接入 OpenBase 的公共服务——统一认证、多租户、配置中心、通知、审计、AI 应用等。适用任何需要平台能力的系统。

### 1.1 步骤

| 步骤 | 操作 | 说明 |
|:---:|------|------|
| 1 | 确认基址与账号 | 平台地址 + 有效账号（联系平台管理员开通） |
| 2 | 登录获取 Token | `POST /api/v1/auth/login` 换取 access_token |
| 3 | 携带 Token 调用 API | 请求头 `Authorization: Bearer <token>` |
| 4 | Token 过期刷新 | `POST /api/v1/auth/refresh`（用 refresh_token） |
| 5 | 统一错误处理 | 按错误码表处理（401 重登 / 403 权限 / 402 余额等） |

### 1.2 步骤 2：登录获取 Token

**curl**：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
# 响应：{"code":0,"data":{"access_token":"<JWT>","refresh_token":"<JWT>",...},"traceId":"req-xxx"}
```

**Python（httpx）**：

```python
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

def login(username: str, password: str) -> dict:
    resp = httpx.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    resp.raise_for_status()
    data = resp.json()["data"]
    print(f"登录成功，access_token 长度={len(data['access_token'])}")
    return data  # {"access_token", "refresh_token", "token_type"}

tokens = login("admin", "admin123")
```

**Node.js（axios）**：

```javascript
const axios = require('axios')
const BASE_URL = 'http://127.0.0.1:8000/api/v1'

async function login(username, password) {
  const { data } = await axios.post(`${BASE_URL}/auth/login`, { username, password })
  console.log('登录成功，token 长度 =', data.data.access_token.length)
  return data.data
}

login('admin', 'admin123')
```

### 1.3 步骤 3~4：调用 API 与刷新 Token

**curl**：

```bash
TOKEN="<access_token>"
# 当前用户
curl -X GET "http://127.0.0.1:8000/api/v1/auth/me" -H "Authorization: Bearer $TOKEN"
# 租户上下文（多租户）
curl -X GET "http://127.0.0.1:8000/api/v1/tenants/context" \
  -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: tenant_a" -H "X-User-Id: u1"
# 刷新 Token
curl -X POST "http://127.0.0.1:8000/api/v1/auth/refresh" -H "Authorization: Bearer <refresh_token>"
```

**完整 Python 客户端**（含 Token 刷新与统一错误处理）：

```python
import httpx

class OpenBaseClient:
    """OpenBase 方式 A 对接客户端（登录/刷新/统一错误处理/多租户）"""

    def __init__(self, base_url: str, username: str, password: str, tenant: str | None = None):
        self._base = f"{base_url}/api/v1"
        self._tenant = tenant
        self._tokens = self._login(username, password)

    # ---- 认证 ----
    def _login(self, username: str, password: str) -> dict:
        resp = httpx.post(f"{self._base}/auth/login", json={"username": username, "password": password})
        self._raise_for_status(resp)
        return resp.json()["data"]

    def _refresh(self) -> None:
        resp = httpx.post(f"{self._base}/auth/refresh", headers={"Authorization": f"Bearer {self._tokens['refresh_token']}"})
        self._raise_for_status(resp)
        self._tokens = resp.json()["data"]

    # ---- 请求 ----
    def _headers(self) -> dict:
        headers = {"Authorization": f"Bearer {self._tokens['access_token']}"}
        if self._tenant:
            headers["X-Tenant-Id"] = self._tenant
        return headers

    def call(self, method: str, path: str, **kwargs):
        resp = httpx.request(method, f"{self._base}/{path}", headers=self._headers(), **kwargs)
        if resp.status_code == 401:          # Token 失效 → 自动刷新重试一次
            self._refresh()
            resp = httpx.request(method, f"{self._base}/{path}", headers=self._headers(), **kwargs)
        self._raise_for_status(resp)
        return resp.json()

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            body = resp.json()
            raise RuntimeError(f"[{resp.status_code}] {body.get('code')} {body.get('message')} request_id={body.get('request_id')}")

# 使用示例
client = OpenBaseClient("http://127.0.0.1:8000", "admin", "admin123", tenant="tenant_a")
me = client.call("GET", "auth/me")            # 当前用户
ctx = client.call("GET", "tenants/context")   # 租户上下文
apps = client.call("GET", "ai-apps")          # AI 应用列表
print(me, ctx, apps)
```

### 1.4 方式 A 可调用的平台 API（摘录）

| 能力 | 路径 | 方法 |
|------|------|------|
| 认证 | `/auth/login`、`/auth/refresh`、`/auth/me` | POST/POST/GET |
| 租户 | `/tenants/context`、`/tenants/{t}/quota` | GET/POST/GET |
| 组织 | `/org/departments`、`/org/departments/tree` | GET/POST/DELETE |
| 配置 | `/configs`、`/configs/{key}/versions`、`/configs/{key}/rollback` | GET/POST |
| 通知 | `/notifications`、`/notifications/stream` | GET/POST |
| 审计 | `/audit/records` | GET |
| AI 应用 | `/ai-apps`（CRUD + publish/unpublish/versions/calls） | GET/POST/PUT/DELETE |
| 动态模块 | `/modules`、`/modules/{id}` | GET |

---

## 2. 方式 B：统一代理接入（访问四系统后端）

**用途**：通过 OpenBase 代转发访问四系统（OpenLLM / OpenRAG / OpenMemory / DPS）后端接口。调用方**不直连四系统**，统一走 OpenBase 网关（统一鉴权、统一错误码、统一追踪）。

### 2.1 步骤

| 步骤 | 操作 | 说明 |
|:---:|------|------|
| 1 | 确认目标系统与路径 | `system` ∈ {openllm, openrag, openmemory, dps}，`path` 为目标系统 API 路径 |
| 2 | 获取 Token | 同方式 A 步骤 2 |
| 3 | 构造代理请求 | `GET/POST /api/v1/proxy/{system}/{path}` + Bearer + 可选 X-Tenant-Id |
| 4 | 处理包装错误 | 402（余额不足）/ 502（上游不可达）已统一包装，直接按错误码处理 |
| 5 | 流式接口（SSE） | `chat/stream` 类接口以流方式消费 |

### 2.2 基本调用

**curl**：

```bash
TOKEN="<access_token>"

# OpenLLM 健康检查（GET）
curl -X GET "http://127.0.0.1:8000/api/v1/proxy/openllm/health" \
  -H "Authorization: Bearer $TOKEN"

# OpenRAG 知识库列表（GET + 租户头）
curl -X GET "http://127.0.0.1:8000/api/v1/proxy/openrag/kb/list" \
  -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: tenant_a"

# OpenLLM 对话（POST JSON）
curl -X POST "http://127.0.0.1:8000/api/v1/proxy/openllm/chat/completions" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"你好"}]}'
```

**Python（httpx）**：

```python
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"
TOKEN = "<access_token>"   # 见方式 A 获取

def proxy_call(system: str, path: str, method: str = "GET", tenant: str | None = None, **kwargs):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if tenant:
        headers["X-Tenant-Id"] = tenant
    url = f"{BASE_URL}/proxy/{system}/{path}"
    resp = httpx.request(method, url, headers=headers, **kwargs)
    if resp.status_code == 402:
        raise RuntimeError(f"模型余额不足: {resp.json()['message']} (request_id={resp.json().get('request_id')})")
    if resp.status_code == 502:
        raise RuntimeError(f"上游系统不可达: {resp.json()['message']}")
    resp.raise_for_status()
    return resp.json()

data = proxy_call("openllm", "health")
print(data)
```

### 2.3 流式对话（SSE）示例

**Python（httpx 流式）**：

```python
import httpx

TOKEN = "<access_token>"
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "讲一个笑话"}]}

with httpx.stream("POST", "http://127.0.0.1:8000/api/v1/proxy/openllm/chat/stream",
                  headers=headers, json=payload, timeout=60) as resp:
    if resp.status_code == 402:
        raise RuntimeError(f"余额不足: {resp.json()['message']}")
    for line in resp.iter_lines():
        if line.startswith("data:"):
            print(line[5:].strip())   # 逐条输出流式内容
```

**前端（axios 流式消费）**：

```typescript
// 通过统一客户端携带 Token 发起流式请求
import client from '@/core/api/http'   // 已注入 JWT + /api/v1 基址

async function streamChat(messages: { role: string; content: string }[]) {
  const resp = await fetch('/api/v1/proxy/openllm/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('ob_access_token')}` },
    body: JSON.stringify({ model: 'gpt-4o-mini', messages }),
  })
  if (resp.status === 402) { ElMessage.error('模型服务余额不足，请联系管理员充值'); return }
  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const chunk = decoder.decode(value)
    // 处理 SSE 行：按 "data:" 前缀解析增量内容并追加到界面
    console.log(chunk)
  }
}
```

### 2.4 代理行为速查（v1.3.0）

| 上游状态 | 调用方收到 | 处理 |
|:---:|:---:|------|
| 200 | 原样透传 | 正常解析 |
| **402** | `BIZ_MODEL_QUOTA` + HTTP 402 | 提示用户充值/检查配额 |
| 502/不可达 | `SYS_502` + HTTP 502 | 检查上游系统是否启动 |
| 未带 Token | 401 | 先登录 |

---

## 3. 方式 C：统一前端集成（把页面并入统一门户）

**用途**：四系统前端团队把独立前端页面注册为动态模块，用户登录统一前端一次即可操作全部系统（统一登录、统一侧边栏、统一 RBAC）。

### 3.1 步骤

| 步骤 | 操作 | 说明 |
|:---:|------|------|
| 1 | 创建模块目录 | `openbase-ui/src/modules/{moduleId}/`（如 `openllm`） |
| 2 | 编写 `index.ts` | 导出 `routes`（vue-router 路由）+ `navItems`（侧边导航） |
| 3 | 编写页面组件 | Vue3 `<script setup lang="ts">` + Element Plus |
| 4 | 注册路由加载器 | 在 `src/core/router/index.ts` 的 `moduleRouteLoaders` 注册模块 |
| 5 | 配置权限 | 路由 meta 标记权限；`moduleRegistry` 校验 |
| 6 | 构建验证 | `npx vue-tsc --noEmit` + `npx vite build` |

### 3.2 步骤 2：模块 index.ts 模板

```typescript
// src/modules/{moduleId}/index.ts —— 模块注册模板
import type { RouteRecordRaw } from 'vue-router'

/** 模块路由（懒加载页面组件） */
export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/{moduleId}/list' },
  { path: 'list', name: '{moduleId}-list',
    component: () => import('./pages/ListPage.vue'), meta: { title: '列表' } },
  { path: ':id', name: '{moduleId}-detail',
    component: () => import('./pages/DetailPage.vue'), meta: { title: '详情' } },
]

/** 板块导航（显示在模块页侧边栏） */
export const navItems = [
  { label: '{模块名}', items: [{ path: '/{moduleId}/list', title: '列表页' }] },
]
```

### 3.3 步骤 3：页面组件模板

```vue
<!-- src/modules/{moduleId}/pages/ListPage.vue -->
<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索" clearable style="width: 200px" />
      <el-button type="primary" data-test="create-item" @click="dialogVisible = true">新建</el-button>
    </div>
    <el-table :data="items" stripe>
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/{moduleId}/${row.id}`)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const keyword = ref('')
const dialogVisible = ref(false)
const items = ref([{ id: 1, name: '示例数据', status: 'active' }])
</script>
```

### 3.4 步骤 4：注册路由加载器

```typescript
// src/core/router/index.ts（在 moduleRouteLoaders 中追加）
const moduleRouteLoaders: Record<string, () => Promise<{ routes: RouteRecordRaw[]; navItems?: unknown[] }>> = {
  openllm: () => import('@/modules/openllm'),
  knowledge: () => import('@/modules/knowledge'),
  memory: () => import('@/modules/memory'),
  portrait: () => import('@/modules/portrait'),
  // 新模块追加：
  // yourmod: () => import('@/modules/yourmod'),
}
```

### 3.5 步骤 5：使用统一请求客户端（对接四系统后端走代理）

```typescript
// src/modules/{moduleId}/pages/ListPage.vue 中请求数据
import client from '@/core/api/http'   // 已注入 JWT/租户头/401 刷新

async function loadList() {
  const data = await client.get('/proxy/openllm/models')   // 走方式 B 代理
  items.value = data.data
}
```

### 3.6 方式 C 完整落地示例（参考 openllm 模块）

现有模块结构可作模板直接复制：

```
src/modules/openllm/
├── index.ts                  # 路由 + 导航（见 3.2 模板）
└── pages/
    ├── Models.vue            # 模型管理
    ├── Providers.vue         # 提供商管理
    └── ...                   # 其余页面
```

---

## 4. 三种方式选型速查

| 你的身份 | 需求 | 选型 |
|---------|------|------|
| 第三方系统后端 | 复用平台能力（登录/租户/配置） | **方式 A** |
| 统一前端 | 调用四系统后端业务接口 | **方式 B** |
| 四系统前端团队 | 页面并入统一门户 | **方式 C**（内部再走方式 B 调后端） |
| 四系统完整接入 | 平台能力 + 后端被代理 + 前端集成 | **A + B + C** 三件套 |

## 5. 常见错误对照（对接期排障）

| 现象 | 原因 | 修复 |
|------|------|------|
| 401 | Token 缺失/过期 | 重新登录；客户端自动刷新（见 1.3 Python 客户端） |
| 403 | RBAC 权限不足 | 联系管理员为账号授权 |
| 402 | 模型提供商余额不足 | 充值；前端提示"模型服务余额不足" |
| 502 | 上游系统未启动 | 启动目标系统（openllm:8001 等）后重试 |
| 404 | 路径拼错/版本不符 | 对照全版本指南 §6 API 参考全集 |
| CORS | 跨域访问 | 生产经 Nginx 同域反代 `/api` |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-27 | OpenBase 平台组 | 初始创建：三种接入方式（A 直接调用 / B 代理接入 / C 前端集成）详细步骤 + 可复制示例代码（curl/Python/Node/前端） |

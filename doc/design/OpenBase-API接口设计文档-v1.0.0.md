# OpenBase API 接口设计文档 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.1 |
| 状态 | [Review] |
| 适用环境 | Dev / Test / Pro |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 最后更新 | 2026-08-25 |
| 关联需求 | FR-CORE-003/004、FR-MOD-001~006、FR-SUP-001~005、FR-PRO-006、IF 接口需求 |

---

## 1. 接口设计总则

### 1.1 统一约定

| 项 | 约定 |
|----|------|
| 基础路径 | `/api/v1`（管理接口） |
| 成功响应 | 直接返回资源（response_model 序列化，REST 风格） |
| 错误格式 | `{code, message, detail, request_id}`（统一错误码） |
| 分页约定 | `?page=1&page_size=20` → `{items: [], total: N, page: 1, page_size: 20}` |
| 排序约定 | `?sort=created_at&order=desc` |
| 搜索约定 | `?search=关键词`（按白名单字段模糊匹配） |
| 时间格式 | ISO 8601（UTC，`2026-08-25T08:00:00Z`） |
| 文档 | FastAPI 自动生成 OpenAPI（/docs、/openapi.json） |

> 说明（v1.0.0 实现确认）：成功响应采用 REST 风格直接返回资源对象（由 FastAPI response_model 序列化），错误响应统一为 `{code, message, detail, request_id}` 结构（由统一异常处理器保证）。

### 1.2 错误码体系（FR-CORE-004）

| 错误码段 | 含义 | 示例 |
|---------|------|------|
| AUTH_xxx | 鉴权/授权 | AUTH_401（未认证）、AUTH_403（无权限）、AUTH_429（限流） |
| PARAM_xxx | 参数校验 | PARAM_422（参数错误） |
| BIZ_xxx | 业务错误 | BIZ_TENANT_EXISTS（租户已存在） |
| SYS_xxx | 系统错误 | SYS_500（内部错误） |
| STORAGE_xxx | 存储错误 | STORAGE_404（文件不存在） |

### 1.3 鉴权方式（双接口体系，FR-PRO-006）

| 接口类 | 认证 | 说明 |
|--------|------|------|
| 管理接口 | 用户级 JWT（Bearer Token） | `Authorization: Bearer <access_token>`；RBAC 权限点校验 |
| AI 服务接口 | 服务级 API Key | MCP 工具调用使用服务级 Key（机器对机器） |

## 2. 管理接口设计

### 2.1 认证接口（auth 模块）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | /api/v1/auth/login | 账号密码登录 | 公开 |
| POST | /api/v1/auth/refresh | 刷新 Token | 公开（refresh token） |
| POST | /api/v1/auth/logout | 登出 | 登录用户 |
| GET | /api/v1/auth/me | 当前用户信息（含角色/权限点） | 登录用户 |

**login 请求/响应**：

```json
// POST /api/v1/auth/login
{ "username": "admin", "password": "***" }

// 200
{
  "code": 0, "message": "ok",
  "data": {
    "access_token": "eyJ...", "token_type": "bearer",
    "expires_in": 7200, "refresh_token": "eyJ...", "refresh_expires_in": 604800
  },
  "request_id": "req-001"
}
```

### 2.2 用户/角色/权限接口（auth 模块 RBAC）

| 方法 | 路径 | 说明 | 权限点 |
|------|------|------|--------|
| GET | /api/v1/users | 用户列表（分页/搜索） | user:list |
| POST | /api/v1/users | 创建用户 | user:create |
| PUT | /api/v1/users/{id} | 编辑用户 | user:update |
| DELETE | /api/v1/users/{id} | 删除用户（软删） | user:delete |
| POST | /api/v1/users/{id}/disable | 禁用用户 | user:update |
| POST | /api/v1/users/{id}/reset-password | 重置密码 | user:update |
| GET | /api/v1/roles | 角色列表 | role:list |
| POST | /api/v1/roles | 创建角色 | role:create |
| PUT | /api/v1/roles/{id} | 编辑角色（含权限点分配） | role:update |
| DELETE | /api/v1/roles/{id} | 删除角色 | role:delete |
| GET | /api/v1/permissions | 权限点列表 | permission:list |

### 2.3 租户接口（tenant 模块）

| 方法 | 路径 | 说明 | 权限点 |
|------|------|------|--------|
| GET | /api/v1/tenants | 租户列表 | tenant:list |
| POST | /api/v1/tenants | 创建租户 | tenant:create |
| PUT | /api/v1/tenants/{id} | 编辑租户（隔离级别/配额） | tenant:update |
| POST | /api/v1/tenants/{id}/disable | 禁用租户 | tenant:update |
| GET | /api/v1/tenants/{id}/quota | 租户配额详情 | tenant:list |

### 2.4 组织架构接口（org 模块）

| 方法 | 路径 | 说明 | 权限点 |
|------|------|------|--------|
| GET | /api/v1/org/departments | 部门树 | org:list |
| POST | /api/v1/org/departments | 创建部门 | org:create |
| PUT | /api/v1/org/departments/{id} | 编辑部门 | org:update |
| DELETE | /api/v1/org/departments/{id} | 删除部门 | org:delete |
| PUT | /api/v1/org/departments/{id}/users | 部门-用户关联 | org:update |

### 2.5 数据字典接口（dict 模块）

| 方法 | 路径 | 说明 | 权限点 |
|------|------|------|--------|
| GET | /api/v1/dicts | 字典类型列表 | dict:list |
| POST | /api/v1/dicts | 创建字典类型 | dict:create |
| PUT | /api/v1/dicts/{id} | 编辑字典类型 | dict:update |
| GET | /api/v1/dicts/{type}/items | 字典项列表（前端联动） | dict:list |
| POST | /api/v1/dicts/{type}/items | 创建字典项 | dict:create |
| PUT | /api/v1/dicts/items/{id} | 编辑字典项 | dict:update |
| DELETE | /api/v1/dicts/items/{id} | 删除字典项 | dict:delete |

### 2.6 定时任务接口（scheduler 模块）

| 方法 | 路径 | 说明 | 权限点 |
|------|------|------|--------|
| GET | /api/v1/schedules | 任务列表 | schedule:list |
| POST | /api/v1/schedules | 创建任务 | schedule:create |
| PUT | /api/v1/schedules/{id} | 编辑任务 | schedule:update |
| POST | /api/v1/schedules/{id}/start | 启动任务 | schedule:update |
| POST | /api/v1/schedules/{id}/stop | 停止任务 | schedule:update |
| DELETE | /api/v1/schedules/{id} | 删除任务 | schedule:delete |
| GET | /api/v1/schedules/{id}/logs | 执行日志 | schedule:list |

### 2.7 文件接口（storage 模块）

| 方法 | 路径 | 说明 | 权限点 |
|------|------|------|--------|
| POST | /api/v1/files | 上传文件（multipart） | file:upload |
| GET | /api/v1/files/{id} | 下载/预览文件 | file:download |
| GET | /api/v1/files | 文件列表 | file:list |
| DELETE | /api/v1/files/{id} | 删除文件 | file:delete |

### 2.8 通知接口（notify 模块）

| 方法 | 路径 | 说明 | 权限点 |
|------|------|------|--------|
| GET | /api/v1/notifications | 通知列表 | notify:list |
| GET | /api/v1/notifications/stream | SSE 推送流 | 登录用户 |
| POST | /api/v1/notifications/{id}/read | 标记已读 | 登录用户 |
| POST | /api/v1/notifications/read-all | 全部已读 | 登录用户 |

### 2.9 配置中心接口（config 模块）

| 方法 | 路径 | 说明 | 权限点 |
|------|------|------|--------|
| GET | /api/v1/configs | 配置列表 | config:list |
| POST | /api/v1/configs | 创建/更新配置 | config:create |
| GET | /api/v1/configs/{key} | 配置详情 | config:list |
| POST | /api/v1/configs/{key}/reload | 热加载 | config:update |
| GET | /api/v1/configs/{key}/versions | 版本历史 | config:list |
| POST | /api/v1/configs/{key}/rollback | 回滚到版本 | config:update |

### 2.10 健康检查（audit 模块）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查（200=在线） |

## 3. AI 服务接口设计

### 3.1 MCP 工具接口（mcp 模块，服务级 API Key）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /mcp/tools/list | 工具清单（可缓存） | 服务级 API Key |
| POST | /mcp/tools/call | 工具调用 | 服务级 API Key |
| GET | /mcp/schema | MCP 协议 schema | 服务级 API Key |

> 四系统特色工具（OpenRAG 检索、OpenMemory 记忆、DPS 画像）经 openbase mcp 模块统一暴露，工具定义由各系统以 decorator 声明。

## 4. 通用 CRUD 接口（BaseCRUDRouter 生成，FR-TOOL-002）

BaseCRUDRouter 基于 Pydantic schema 自动生成标准 CRUD 接口：

| 方法 | 路径（模板） | 说明 |
|------|-------------|------|
| GET | /{resource} | 列表（分页/搜索/排序） |
| GET | /{resource}/{id} | 详情 |
| POST | /{resource} | 创建 |
| PUT | /{resource}/{id} | 更新 |
| DELETE | /{resource}/{id} | 删除 |

**生成规则**：路由前缀由模块声明；schema 从模型自动推导；权限点按资源自动生成（{resource}:list/create/update/delete）。

## 5. 接口与 v1.2.0 前端契约对齐

> 管理接口设计已预留给 v1.2.0 统一前端公共模块调用（对应统一前端需求设计说明 FR-UF-006~009）。

| 前端模块 | 对应接口 | 对齐要点 |
|---------|---------|---------|
| 登录/鉴权（FR-UF-006） | /api/v1/auth/* | 登录/刷新/登出/me |
| 用户/角色/权限（FR-UF-007） | /api/v1/users、/roles、/permissions | RBAC 页面 CRUD |
| 租户管理（FR-UF-008） | /api/v1/tenants | 租户 CRUD |
| 字典/任务/文件/通知（FR-UF-009） | /api/v1/dicts、/schedules、/files、/notifications | 联动/列表/SSE |
| 服务发现（FR-UF-011） | /health + 网关 /api/v1/services | 健康状态聚合（v1.2.0 网关提供） |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-08-25 | AA-OpenBase-Dev | 初始创建：接口总则（响应/错误码/鉴权）、9 组管理接口（auth/users/roles/permissions/tenants/org/dicts/schedules/files/notifications/configs）、AI 服务接口（MCP）、BaseCRUDRouter 通用接口、v1.2.0 前端契约对齐 |
| v1.0.1 | 2026-08-25 | AA-OpenBase-Dev | 实现确认（开发阶段）：成功响应格式由 {code,data} 包装调整为 REST 风格直接返回资源（response_model 序列化），错误响应保持统一 {code,message,detail,request_id}；分页响应结构同步调整（去掉 data 包装）；login 示例同步 |

# OpenBase 架构设计文档 - v1.4.2

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.2 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | SA-OpenBase |
| 创建日期 | 2026-08-29 |
| 存放 | doc/design/ |

---

## 1. 设计目标与范围

| 项 | 内容 |
|----|------|
| 设计范围 | FR-142-01~10（租户/用户管理 + OpenMemory 对接 + 测试基座） |
| 前置验证 | OpenMemory v6.8.0 实际代码核验通过：`X-API-Key` 中间件保护 `/api/v1`、JWT 校验 `gateway.jwt_secret`（HS256）、`/health` 免鉴权、统一响应 {code,message,data,timestamp} |
| 约束 | 分层架构（Controller/Service/Repository）、错误码统一 BaseError、SQLAlchemy 参数化、结构化日志、向后兼容既有端点 |

## 2. 系统架构

### 2.1 总体架构（Phase 2 目标态）

```
统一前端（OpenBase frontend）
  │  JWT（OpenBase 签发，含 sub/org_id/role）
  ▼
OpenBase 后端（FastAPI，:8000）
  ├─ auth 模块：登录/签发 JWT（扩展 Payload）+ 服务 Key（X-API-Key 通道）
  ├─ tenant 模块：租户 CRUD + 配额（Phase 1 新增）
  ├─ users 模块：用户 CRUD + 角色（Phase 1 新增）
  ├─ proxy 模块：/api/v1/memory-proxy/* 转发（Phase 2 新增）
  │     ├─ 注入 X-API-Key（OpenBase 持有）
  │     └─ 透传 JWT（Bearer）
  ▼
OpenMemory 后端（FastAPI，:8020，独立部署）
  ├─ 第一层：api_key_middleware（X-API-Key 校验，/api/v1 保护）
  ├─ 第二层：APIGateway（Bearer JWT 校验，gateway.jwt_secret 共享密钥 + HS256）
  └─ 记忆核心：remember/recall/forget/memories（Qdrant + Neo4j + Redis + PG）
```

### 2.2 关键架构决策（ADR）

#### ADR-142-01 OpenMemory 服务部署方式

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | OpenMemory v6.8.0 以独立服务部署（本机进程/容器），API 端口 **8000 → 8020**（避免与 OpenBase :8000 冲突）；配置 `OPENMEMORY_SERVER__API_KEY`；共享基础设施（Qdrant 6333/Neo4j 7687/Redis 6380/PG 5432）沿用 .env.shared-infra |
| 理由 | OpenMemory 是独立完整服务（FastAPI + Qdrant + Neo4j + Redis + PG），OpenBase 只作对接方不内嵌；端口错开保证双服务共存 |
| 备选 | docker compose 一键部署（官方支持）vs 本地进程（uvicorn）→ 以 .env.shared-infra 一致的本地/共享基础设施为准，启动方式在部署脚本中封装 |

#### ADR-142-02 JWT 跨系统信任（密钥共享）

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | OpenBase 与 OpenMemory 共享同一 JWT 签名密钥：OpenBase auth 签发（HS256）→ OpenMemory `gateway.jwt_secret` 校验。密钥经环境变量配置（`OPENMEMORY_GATEWAY__JWT_SECRET` 与 OpenBase 侧密钥同一来源），不落 git |
| Payload 契约 | `sub`（user_id）、`username`、`org_id`（tenant_id）、`role`（admin/org_admin/org_member/viewer）、`exp` |
| 理由 | OpenMemory 官方认证模型即"JWT 由您的身份认证系统签发"；共享密钥是文档化方案，避免双系统各持用户体系 |
| 风险 | 密钥泄露 → 全系统信任受损。缓解：.env* 排除 git、密钥轮换机制文档化（沿用 v1.4.1 密钥管理约定） |

#### ADR-142-03 proxy 转发适配方案

| 项 | 内容 |
|----|------|
| 状态 | 已接受 |
| 决策 | 复用 v1.4.1 proxy 通道能力，新增 `/api/v1/memory-proxy/*` 路由：OpenBase 侧注入 `X-API-Key`（OpenBase 服务 Key 持有）+ 透传用户 JWT（Bearer）；响应统一适配 {code,message,data,timestamp}；错误码透传（200005 缺少 Key/200001 JWT 无效等） |
| 理由 | 前端不接触 OpenMemory 密钥（安全）；认证统一由 OpenBase 汇聚；双通道与 v1.4.1 认证模型一致 |
| 备选 | 前端直连 OpenMemory（CORS + 前端持 Key）→ 否决：Key 泄露风险，违背最小权限 |

## 3. 数据模型设计（Phase 1）

### 3.1 Tenant（租户）

| 字段 | 类型 | 约束 |
|------|------|------|
| id | String/UUID | 主键 |
| code | String | 唯一，业务标识 |
| name | String | 必填 |
| status | Enum(active/disabled) | 默认 active |
| quota_config | JSON | 配额配置（与 QuotaManager 衔接） |
| created_at / updated_at | DateTime | 审计 |

### 3.2 User（用户）

| 字段 | 类型 | 约束 |
|------|------|------|
| id | String/UUID | 主键 |
| username | String | 唯一 |
| password_hash | String | bcrypt/argon2，不落日志 |
| status | Enum(active/disabled) | 默认 active |
| role | Enum(admin/org_admin/org_member/viewer) | RBAC 依据 |
| tenant_id | FK→Tenant | 多租户关联（可空=全局） |
| created_at / updated_at | DateTime | 审计 |

> 迁移约束：users 表扩展向后兼容（既有 admin/viewer 种子迁移），login/refresh/me 链路不动。

## 4. 接口契约设计

### 4.1 Phase 1 接口（租户/用户管理）

| 方法 | 路径 | 请求 | 响应 | 权限 |
|------|------|------|------|------|
| POST | /api/v1/tenants | {code,name,quota_config} | TenantOut | admin |
| GET | /api/v1/tenants | 分页参数 | list[TenantOut] | admin |
| GET | /api/v1/tenants/{tenant_id} | - | TenantOut | admin |
| PUT | /api/v1/tenants/{tenant_id} | {name,status,quota_config} | TenantOut | admin |
| DELETE | /api/v1/tenants/{tenant_id} | - | {code:0}（停用语义） | admin |
| PUT | /api/v1/tenants/{tenant_id}/quota | {quota_config} | TenantOut | admin |
| POST | /api/v1/users | {username,password,role,tenant_id} | UserOut | admin/org_admin |
| GET | /api/v1/users | 分页/筛选 | list[UserOut] | admin/org_admin |
| PUT | /api/v1/users/{user_id} | {status/基础字段} | UserOut | admin/org_admin |
| PUT | /api/v1/users/{user_id}/role | {role} | UserOut | admin |
| DELETE | /api/v1/users/{user_id} | - | {code:0}（停用语义） | admin |

错误码：PARAM（参数）/PERM（越权 403）/BIZ（业务）/SYS（系统），统一 BaseError 格式 {code,message,detail,request_id}。

### 4.2 Phase 2 接口（OpenMemory 对接）

| 方法 | 路径（OpenBase proxy） | 上游（OpenMemory 8020） | 认证 |
|------|------------------------|------------------------|------|
| POST | /api/v1/memory-proxy/remember | POST /api/v1/remember | OpenBase JWT（proxy 注入 X-API-Key） |
| POST | /api/v1/memory-proxy/recall | POST /api/v1/recall | 同上 |
| POST | /api/v1/memory-proxy/forget | POST /api/v1/forget | 同上 |
| GET | /api/v1/memory-proxy/memories | GET /api/v1/memories | 同上 |
| GET | /api/v1/memory-proxy/memories/{memory_id} | GET /api/v1/memories/{id} | 同上 |

proxy 内部契约：注入 `X-API-Key: {OpenBase 服务 Key}` + `Authorization: Bearer {用户 JWT}`；响应透传统一 {code,message,data,timestamp}；HTTP 超时 30s；OpenMemory 熔断错误（500002）按语义透传。

## 5. 与既有架构的衔接

| 项 | 衔接说明 |
|----|---------|
| 认证体系 | 复用 v1.4.1 auth（JWT + 服务 Key 双通道）；JWT Payload 扩展 sub/org_id/role |
| 分层架构 | 新增模块遵循 Controller（路由校验）/Service（编排）/Repository（SQLAlchemy 参数化）三层 |
| 错误码 | 新增端点全部 BaseError（错误码前缀 AUTH/PERM/PARAM/BIZ/SYS/STORAGE） |
| proxy 基础 | 复用 v1.4.1 /api/v1/proxy 双通道认证依赖（get_proxy_identity） |
| 多租户 | Tenant CRUD 与既有 context/quota 端点并存；配额 QuotaManager 保持内存态（本版本不迁移 schema 隔离） |
| 日志审计 | 审计上下文（tenant_id/operator_id）沿用 R-370 注入；OpenMemory 调用记审计 |

## 6. 非功能设计

| 类别 | 设计 |
|------|------|
| 性能 | proxy 连接池 + 超时 30s；CRUD 分页默认 20 |
| 安全 | 密码哈希、JWT 密钥配置化不落 git、X-API-Key 不落前端/日志、RBAC 权限校验 |
| 可观测 | 结构化日志（extra 字段）、proxy 调用计时、OpenMemory 错误码透传 |
| 兼容 | 既有端点零回归；前端既有页面零破坏 |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-29 | SA-OpenBase | 初始创建：两 Phase 架构（租户/用户管理 + OpenMemory 对接），ADR-142-01/02/03（部署 8020 / JWT 密钥共享 / proxy 适配），数据模型 + 接口契约，前置验证（OpenMemory 实际代码核验）通过 |

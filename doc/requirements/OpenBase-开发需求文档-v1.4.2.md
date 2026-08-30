# OpenBase 开发需求文档 - v1.4.2

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.2 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | RA-OpenBase |
| 创建日期 | 2026-08-29 |
| 存放 | doc/requirements/ |

---

## 1. 版本概述

| 项 | 内容 |
|----|------|
| 版本主题 | 四维身份管理基础（租户/用户）+ OpenMemory 对接（两 Phase） |
| 需求来源 | 候选需求池 §1.8：R-374（VC-008）/ R-375（VC-008）/ R-378（VC-010） |
| 基线 | v1.4.1（Step 5 已部署发布，全流程闭环） |
| 关键外部依据 | 《OpenMemory-对接使用指南-v6.8.0.md》（双层认证：X-API-Key + JWT{sub,org_id,role}） |

## 2. 功能需求

### 2.1 R-374 租户管理（P1，Phase 1）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 平台管理员, I want 创建/编辑/停用租户并配置配额, so that 多租户域可真实管理（替换占位 mock） |
| 功能描述 | 租户 CRUD API（create/list/get/update/deactivate/quota 读写）+ 管理界面（SystemTenants.vue 替换）；数据落库，向后兼容既有 context/quota 端点与内存 QuotaManager |
| 验收标准 | AC-142-01-1 租户创建/列表/详情/编辑/停用 API 可用且数据落库；AC-142-01-2 配额读写与 QuotaManager 衔接生效；AC-142-01-3 既有 /api/v1/tenants/context、{tenant}/quota 无回归；AC-142-01-4 租户管理界面 100% 替换 mock，全链路可用 |

### 2.2 R-375 用户管理（P1，Phase 1）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 平台管理员, I want 创建/启停用户并分配角色, so that 用户实体可真实管理且认证/授权闭环（替换占位 mock） |
| 功能描述 | 用户 CRUD API（create/list/get/update/启停/角色分配）+ 管理界面（OrgTeamsUsersView 用户部分替换）；向后兼容既有 login/refresh/me 链路，种子数据（admin/viewer）迁移 |
| 验收标准 | AC-142-02-1 用户创建/列表/详情/编辑/启停/角色分配 API 可用且数据落库；AC-142-02-2 新用户可登录且权限按角色生效；AC-142-02-3 既有 admin/viewer 登录无回归；AC-142-02-4 用户管理界面 100% 替换 mock |

### 2.3 R-378 OpenMemory 对接（P1，Phase 2）

#### 2.3.1 BL-142-05 OpenMemory 服务部署

| 项 | 内容 |
|----|------|
| 用户故事 | As a 运维, I want 启动 OpenMemory v6.8.0 服务, so that 记忆能力真实可用 |
| 功能描述 | 基于本机 OpenMemory 项目（D:\Trae CN\myproject\Dev\OpenMemory）部署启动：API 端口 8000→8020（避免与 OpenBase 冲突）、OPENMEMORY_SERVER__API_KEY 配置、Qdrant/Neo4j/Redis/PG 依赖就绪 |
| 验收标准 | AC-142-03-1 OpenMemory 8020 健康检查 200（status=healthy，version=6.8.0）；AC-142-03-2 免鉴权端点（/health、/docs）可访问；AC-142-03-3 基础设施依赖（Qdrant/Neo4j/Redis/PG）healthy |

#### 2.3.2 BL-142-06 认证适配（JWT 完整签发 + 密钥共享）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 外部系统/前端, I want OpenBase 统一签发含 sub/org_id/role 的 JWT, so that OpenMemory 业务层认证通过 |
| 功能描述 | OpenBase auth 登录/签发 JWT 扩展 Payload（sub=user_id、org_id=tenant_id、role=角色）；JWT 签名密钥与 OpenMemory 服务端配置一致（环境变量共享）；服务 Key 通道持有 X-API-Key |
| 验收标准 | AC-142-04-1 登录签发 JWT 含 sub/org_id/role 字段且与用户/租户/角色数据一致；AC-142-04-2 使用该 JWT 请求 OpenMemory 业务端点认证通过（非 401）；AC-142-04-3 密钥配置化，OpenBase 与 OpenMemory 共享同一签名密钥配置项 |

#### 2.3.3 BL-142-07 proxy 转发适配

| 项 | 内容 |
|----|------|
| 用户故事 | As a 前端/调用方, I want 通过 OpenBase proxy 访问 OpenMemory, so that 无需持有 OpenMemory 密钥且认证统一 |
| 功能描述 | OpenBase 侧代理路由（如 /api/v1/memory-proxy/*）：注入 X-API-Key + 转发用户 JWT（Bearer）；统一响应 {code,message,data,timestamp} 适配；错误码透传（200005/200001 等） |
| 验收标准 | AC-142-05-1 proxy 路由可转发 remember/recall/forget/list 等核心操作；AC-142-05-2 请求头正确注入 X-API-Key + Bearer JWT；AC-142-05-3 响应格式统一适配，错误码透传；AC-142-05-4 未认证请求 401 |

#### 2.3.4 BL-142-08 OpenMemory 前端 2 页真实化

| 项 | 内容 |
|----|------|
| 用户故事 | As a 用户, I want 在统一前端查看真实记忆列表与详情, so that 记忆数据可视化可操作 |
| 功能描述 | OpenMemory 记忆列表页/详情页 mock 替换真实 API（走 OpenBase proxy，前端不接触 X-API-Key） |
| 验收标准 | AC-142-06-1 记忆列表页展示真实数据（分页/标签/类型过滤）；AC-142-06-2 记忆详情页展示完整字段；AC-142-06-3 前端不持有 X-API-Key（全部经 proxy） |

#### 2.3.5 BL-142-09 双系统联调

| 项 | 内容 |
|----|------|
| 用户故事 | As a 集成工程师, I want OpenBase 统一认证 → OpenMemory 记忆真实读写闭环, so that 对接完成可验收 |
| 功能描述 | 联调：登录（OpenBase）→ JWT 签发 → proxy → OpenMemory remember/recall/forget/list 真实闭环；集成测试 + UAT 走查 |
| 验收标准 | AC-142-07-1 remember 存储成功（返回 memory_id）；AC-142-07-2 recall 召回命中（score/total 正确）；AC-142-07-3 forget 删除生效（deleted_count）；AC-142-07-4 list 分页正确；AC-142-07-5 UAT 走查通过（页面级） |

### 2.4 还债：TD-新增-009 测试基座修复（P1，Phase 3 收尾）

| 项 | 内容 |
|----|------|
| 用户故事 | As a 开发者, I want 全量 pytest 可一键执行, so that 回归不再因本机环境崩溃 |
| 功能描述 | 修复全量 pytest 本机崩溃（测试基座批次：脚本化回归执行），恢复 `python -m pytest tests` 可用 |
| 验收标准 | AC-142-08-1 全量 pytest 一键执行通过；AC-142-08-2 回归脚本化（README/脚本记录） |

## 3. 业务流程与逻辑

### 3.1 四维管理（Phase 1）流程

```
管理员登录 → 租户管理（创建租户/配额）→ 用户管理（创建用户/分配角色）
         → 新用户登录 → JWT 签发（sub/org_id/role 完整）
```

### 3.2 OpenMemory 对接（Phase 2）流程

```
用户登录（OpenBase，JWT 含 sub/org_id/role）
  → 前端请求 OpenBase proxy（携带 JWT）
  → proxy 注入 X-API-Key（OpenBase 持有）+ 透传 JWT
  → OpenMemory 第一层校验 X-API-Key（网关层）
  → OpenMemory 第二层校验 JWT（业务层，用户身份/角色/租户）
  → remember/recall/forget/list 真实读写 → 统一响应 {code,message,data,timestamp} 返回前端
```

## 4. 数据模型与接口定义

### 4.1 核心实体（Phase 1）

| 实体 | 关键属性 | 约束 |
|------|---------|------|
| Tenant | id、code、name、status(active/disabled)、quota 配置、created_at | code 唯一；status 默认 active |
| User | id、username、password_hash、status(active/disabled)、role、tenant_id、created_at | username 唯一；role 枚举（admin/org_admin/org_member/viewer）；密码哈希存储 |

### 4.2 接口规范（Phase 1）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST/GET | /api/v1/tenants | 创建/列表租户 | admin |
| GET/PUT/DELETE | /api/v1/tenants/{tenant_id} | 详情/编辑/停用 | admin |
| PUT | /api/v1/tenants/{tenant_id}/quota | 配额读写 | admin |
| POST/GET | /api/v1/users | 创建/列表用户 | admin/org_admin |
| GET/PUT/DELETE | /api/v1/users/{user_id} | 详情/编辑/启停 | admin/org_admin |
| PUT | /api/v1/users/{user_id}/role | 角色分配 | admin/org_admin |

### 4.3 接口规范（Phase 2，OpenMemory 对接）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /api/v1/memory-proxy/remember | 存储记忆 | OpenBase JWT |
| POST | /api/v1/memory-proxy/recall | 召回记忆 | OpenBase JWT |
| POST | /api/v1/memory-proxy/forget | 删除记忆 | OpenBase JWT |
| GET | /api/v1/memory-proxy/memories | 记忆列表（分页） | OpenBase JWT |
| GET | /api/v1/memory-proxy/memories/{memory_id} | 记忆详情 | OpenBase JWT |

> proxy 内部：注入 X-API-Key（OpenBase 持有）+ 透传 JWT → 转发 OpenMemory 8020；响应统一 {code,message,data,timestamp}。

## 5. 非功能需求

| 类别 | 指标 |
|------|------|
| 性能 | proxy 转发 P95 延迟 ≤ 500ms（不含 OpenMemory 处理）；管理 CRUD 接口 P95 ≤ 300ms |
| 安全 | 密码哈希存储（不落日志）；X-API-Key 不落前端/不落日志；JWT 密钥配置化不硬编码；RBAC 校验（admin 通配 + 角色控制） |
| 可靠性 | OpenMemory 依赖不可用时报错透传（熔断/降级按 OpenMemory 语义）；管理接口错误统一 BaseError 格式 {code,message,detail,request_id} |
| 兼容性 | 既有 login/refresh/me、tenant context/quota 端点零回归；前端既有页面零破坏 |
| 可维护性 | 分层架构（Controller/Service/Repository）；SQLAlchemy 参数化；结构化日志 |

## 6. 验收标准汇总

| 验收组 | 方法 | 通过标准 |
|--------|------|---------|
| 租户/用户管理（AC-142-01/02） | API 测试 + 界面走查 | CRUD 全链路可用、数据落库、权限生效、mock 100% 替换 |
| OpenMemory 部署（AC-142-03） | 健康检查 + 依赖探测 | 8020 healthy，依赖 healthy |
| 认证适配（AC-142-04） | 集成测试 | JWT 含 sub/org_id/role，OpenMemory 认证通过 |
| proxy（AC-142-05） | 集成测试 | 双通道注入、响应适配、401 拦截 |
| 前端真实化（AC-142-06） | 界面走查 | 2 页真实数据，前端无 Key |
| 联调闭环（AC-142-07） | 真实环境联调 + UAT | remember/recall/forget/list 闭环 |
| 质量门禁 | 回归 + 覆盖率 | 全量回归 ≥95%，核心新代码覆盖率 ≥80%，ruff 0 |

## 7. 风险、假设与约束

| 类型 | 项 | 应对 |
|------|-----|------|
| 风险 | OpenMemory 8020 端口冲突/服务启动失败 | 部署配置覆盖；docker-compose 或进程方式备选 |
| 风险 | JWT 密钥共享导致跨系统信任面扩大 | 密钥仅配置化共享，不落 git（.env* 排除）；最小权限角色 |
| 风险 | 租户 schema 隔离与内存 QuotaManager 衔接 | CRUD 与配额管理器解耦，schema 隔离保持现状 |
| 风险 | 用户表扩展影响既有登录 | 向后兼容迁移，登录/me 不动 |
| 假设 | OpenMemory 项目本机可正常部署启动（docker/进程） | 启动预检先行（Step 2 架构设计前置验证） |
| 假设 | OpenMemory v6.8.0 指南所述 API 与项目实际一致 | 以实际 OpenAPI（/openapi.json）核验为准 |
| 约束 | 四系统其余（OpenLLM/OpenRAG/DPS）对接继续挂起，本版本仅 OpenMemory | 范围边界明确 |

## 8. 附录

### 8.1 术语表

| 术语 | 说明 |
|------|------|
| 四维身份 | 租户（Tenant）/用户（User）/团队（Team）/智能体（Agent）四个身份维度 |
| 双层认证 | OpenMemory v6.8.0 强制：X-API-Key（网关层）+ Bearer JWT（业务层） |
| proxy | OpenBase 统一网关转发通道（v1.4.1 已有 /api/v1/proxy 基础） |

### 8.2 参考资料

| 资料 | 版本 |
|------|------|
| 《OpenMemory-对接使用指南》 | v6.8.0（用户上传，2026-08-29） |
| 单版本规划 v1.4.2 | v1.2.0 [Approved] |
| 本版本 Backlog v1.4.2 | v1.0.0 |
| Phase 迭代计划 v1.4.2 | v1.0.0 |

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-29 | RA-OpenBase | 初始创建：R-374 租户管理/R-375 用户管理/R-378 OpenMemory 对接（5 子项）+ TD-新增-009 还债，验收标准 AC-142-01~08 |

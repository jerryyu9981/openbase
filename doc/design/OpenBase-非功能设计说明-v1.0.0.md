# OpenBase 非功能设计说明 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 适用环境 | Dev / Test / Pro |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 最后更新 | 2026-08-25 |
| 关联需求 | NFR-001~NFR-013、SR-001~SR-009 |

---

## 1. 安全设计

### 1.1 威胁建模（安全设计评审，对应 SR 需求）

| 威胁 | 场景 | 缓解设计 | 对应 SR |
|------|------|---------|---------|
| T-001 认证绕过 | 未认证访问管理接口 | 统一 JWT 校验（get_current_user 依赖）+ 401 | SR-001 |
| T-002 越权访问 | 低权限访问高权限接口 | RBAC 权限点校验（权限点注解）+ 403 | SR-002 |
| T-003 跨租户访问 | A 租户访问 B 租户数据 | EdgeRouter 租户上下文 + Schema 隔离 | SR-007 |
| T-004 密码泄露 | 数据库泄露密码明文 | bcrypt 哈希 + 密码强度校验 | SR-004 |
| T-005 密钥泄露 | 配置密钥明文存储 | 加密存储（Fernet/AES）+ 权限控制 | SR-005 |
| T-006 审计缺失 | 敏感操作无记录 | AuditLog 全量记录敏感操作 | SR-006 |
| T-007 MCP 工具滥用 | 未授权调用 AI 工具 | 服务级 API Key + 工具鉴权 | SR-008 |
| T-008 依赖漏洞 | 第三方库已知漏洞 | 依赖审计（pip-audit）+ 版本锁定 | SR-009 |

### 1.2 数据分类分级

| 级别 | 数据 | 保护要求 |
|------|------|---------|
| L3 机密 | 密码哈希、密钥、refresh_token | 加密存储、最小访问 |
| L2 敏感 | 用户 PII（邮箱/手机）、租户配置 | 权限控制、审计 |
| L1 普通 | 字典/任务/通知等业务数据 | 常规权限 |

### 1.3 安全需求追溯（SR-001~SR-009 全部有设计覆盖）

| SR ID | 设计落地 |
|-------|---------|
| SR-001 | auth 模块 JWT 统一鉴权 + core/deps get_current_user |
| SR-002 | auth 模块 RBAC 权限点 + API 权限注解 |
| SR-003 | 双接口体系：管理接口 JWT / AI 接口 API Key 隔离 |
| SR-004 | bcrypt 密码哈希 |
| SR-005 | config 模块密钥加密存储 |
| SR-006 | audit 模块审计日志 |
| SR-007 | tenant 模块 Schema 隔离 + 配额 + 限流 |
| SR-008 | mcp 模块工具鉴权 |
| SR-009 | CI 依赖审计 + 版本锁定 |

## 2. 性能与容量设计

### 2.1 性能目标（NFR-001~003）

| 指标 | 目标 | 设计支撑 |
|------|------|---------|
| 多租户路由延迟 | < 1ms | EdgeRouter 中间件轻量（search_path 切换） |
| 中间件附加延迟 | < 5ms | 审计/限流中间件异步非阻塞 |
| CRUD 生成接口等价 | 延迟差 < 5% | BaseCRUDRouter 直连 ORM，无额外包装 |

### 2.2 瓶颈路径与设计

| 路径 | 瓶颈风险 | 设计 |
|------|---------|------|
| 鉴权链 | JWT 解析 + DB 查询用户 | JWT 无状态校验 + 用户缓存（Redis，TTL 5min） |
| 多租户 | Schema 切换开销 | search_path 连接级切换（每请求一次） |
| 字典查询 | 高频读 | Redis 缓存（TTL 5min）+ 变更失效 |
| 文件上传 | 大文件内存占用 | 流式上传（分块） |
| SSE 通知 | 长连接 | Redis pub/sub + 连接管理 |

### 2.3 容量估算（MVP 基线）

| 项 | 估算 | 说明 |
|----|------|------|
| 并发用户 | 50 并发 | 单系统管理面 |
| QPS | 100 峰值 | 管理接口 |
| 数据量 | 10 万级 | 审计日志按月归档 |
| 存储 | 文件 100GB 基线 | 本地/MinIO 扩展 |

## 3. 可观测性设计（observability-standards 对齐）

### 3.1 日志结构（结构化 JSON）

| 字段 | 说明 |
|------|------|
| timestamp | ISO 8601 UTC |
| level | DEBUG/INFO/WARN/ERROR |
| trace_id / span_id | OTel 关联 |
| service | openbase-{module} |
| module | auth/tenant/audit/... |
| message | 日志消息 |
| request_id | 请求关联 |

### 3.2 关键指标（14 种，NFR-013）

| 指标 | 类型 | 说明 |
|------|------|------|
| http_requests_total | Counter | 请求总量（按 method/status 分） |
| http_request_duration_seconds | Histogram | 请求延迟 |
| db_query_duration_seconds | Histogram | DB 查询延迟 |
| db_query_total | Counter | DB 查询量 |
| cache_hit_total / cache_miss_total | Counter | 缓存命中/未命中 |
| cache_operation_duration_seconds | Histogram | 缓存操作延迟 |
| auth_login_total | Counter | 登录尝试（按结果分） |
| auth_token_refresh_total | Counter | Token 刷新量 |
| mcp_tools_called_total | Counter | MCP 工具调用量 |
| tenant_quota_usage | Gauge | 租户配额使用 |
| scheduler_job_duration_seconds | Histogram | 任务执行时长 |
| scheduler_job_status_total | Counter | 任务执行结果 |
| notification_pushed_total | Counter | 通知推送量 |
| audit_log_written_total | Counter | 审计日志写入量 |

### 3.3 链路追踪（OTLP）

| 项 | 设计 |
|----|------|
| 协议 | OTLP（OpenTelemetry Python SDK） |
| 传播 | W3C TraceContext |
| 采样 | 生产默认 10%，错误追踪 100% |
| 平台 | Langfuse（OTLP 端点）+ 可选 OTLP Collector |

### 3.4 Dashboard（6 个必备）

| Dashboard | 内容 |
|-----------|------|
| Service Overview | 请求量/延迟/错误率总览 |
| Resource | 内存/CPU/连接池 |
| Dependencies | DB/Redis 延迟与错误 |
| Business | 登录/租户/MCP/任务业务指标 |
| Errors | 错误码分布与排障 |
| Alert History | 告警历史 |

### 3.5 告警规则（示例）

| 规则 | 条件 | 级别 |
|------|------|------|
| 错误率突增 | 5xx 占比 > 5%（5min） | P1 |
| 延迟超限 | P99 > 500ms（5min） | P1 |
| 登录失败激增 | 401 率 > 20%（5min） | P1 |
| 租户配额超限 | quota_usage > 90% | P2 |
| 服务不可用 | /health 失败 | P0 |

## 4. 缓存与消息设计

### 4.1 Redis 键设计

| 键 | 类型 | TTL | 说明 |
|----|------|-----|------|
| openbase:user:{id} | String(JSON) | 5min | 用户信息缓存 |
| openbase:dict:{type} | Hash | 5min | 字典项缓存 |
| openbase:config:{key} | String | 热加载无 TTL | 配置缓存（变更失效） |
| openbase:sse:channel:{tenant} | Pub/Sub | - | SSE 通知通道 |
| openbase:ratelimit:{scope}:{key} | Counter | 窗口 | 限流计数 |
| openbase:refresh:{user_id} | String | 7d | refresh token 状态 |

### 4.2 缓存策略

| 数据 | 策略 | 失效 |
|------|------|------|
| 用户信息 | 写穿（更新时失效） | 更新/禁用时删除 |
| 字典项 | 写穿 | 字典变更时删除 |
| 配置 | 写穿 + 版本号 | 配置更新时失效并热加载 |

### 4.3 消息/事件

| 事件 | 通道 | 消费方 | 幂等 |
|------|------|--------|------|
| 通知推送 | Redis pub/sub | notify SSE | 消息 ID 去重 |
| 配置变更 | Redis pub/sub（或 watcher） | config 热加载 | 版本号 |
| 任务执行 | APScheduler 内存调度 | scheduler | 执行锁（Redis SETNX） |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-08-25 | AA-OpenBase-Dev | 初始创建：安全设计（威胁建模 8 项/数据分级/需求追溯）、性能容量设计（目标/瓶颈/容量估算）、可观测性设计（日志/14 指标/OTLP/6 Dashboard/告警）、缓存与消息设计（Redis 键/策略/事件） |

# OpenBase 版本发布说明（Release Note）- v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.0.0 |
| 发布类型 | 首个可用底座（Initial Release） |
| 发布日期 | 2026-08-25 |
| 状态 | [Final] |
| 存放 | doc/operation/ |

---

## 概述

OpenBase v1.0.0 是四系统（OpenLLM / OpenRAG / OpenMemory / DPS）统一基础设施公共底座框架的首个可用版本，提供框架内核、11 个业务模块、工具链与共享基础设施接入能力。

## 新特性

### 框架内核（core）
- 基础模型（User/Role/Permission/Tenant/Department/AuditLog + 业务模型 8 张表）
- 异步数据库会话（SQLAlchemy async + openbase schema 隔离）
- 统一鉴权中间件（JWT 门禁 + 白名单公开路径）
- 统一错误码与响应契约（ErrorResponse 注入 OpenAPI）
- 配置驱动模块装配（enable/disable_module）

### 业务模块（11 个）
- auth：JWT 登录/刷新 + RBAC 数据库权限矩阵 + bcrypt 配置化 + Redis 用户缓存
- tenant：EdgeRouter 上下文解析 + 配额（OpenMemory 抽取）
- audit：审计中间件 + 记录查询（OpenLLM 抽取）
- observability：OTel + Langfuse 配置（OpenMemory 抽取）
- config：三级配置合并 + 版本回滚 + DB 持久化（OpenRAG 抽取）
- mcp：MCPServer + 服务级 API Key 鉴权（OpenRAG 抽取）
- org/dict/scheduler/storage/notify：全模块数据库落库 + Redis 缓存（dict）

### 基础设施接入
- PostgreSQL 共享库（openbase schema 隔离，17 张表幂等建表）
- Redis（用户/dict 缓存 TTL 5min + notify 广播，失败自动降级）
- 数据库优先 + 内存回退（基础设施不可达时系统可用）

### 工具链
- openbase-cli（create-project/module/crud）
- BaseCRUDRouter（通用 CRUD 生成）

## 质量指标

| 指标 | 值 |
|------|-----|
| 测试用例 | 105 个全通过 |
| 覆盖率 | 90% |
| ruff | 0 错误 |
| 真实基础设施集成 | 22/22（PG 16 + PG/Redis 6） |

## 已知限制

| 项 | 说明 | 计划 |
|----|------|------|
| 生产环境部署 | 本版本 Dev 发布 | v1.1.0（蓝绿/金丝雀） |
| OTLP 告警通道 | 监控接入 | v1.1.0 |
| 四系统回灌 | 代码抽取后回灌验证 | v1.1.0 |
| 统一前端 | 无前端页面 | v1.2.0 |

## 兼容性

- Python >= 3.10（3.11+ 推荐）
- PostgreSQL 14+（asyncpg 驱动）
- Redis 6+（可选，降级可用）

## 升级/安装

```bash
pip install -e .
# 环境变量：OPENBASE_DB_URL / OPENBASE_REDIS_URL / OPENBASE_JWT_SECRET / OPENBASE_MCP_API_KEYS
uvicorn openbase.demo_app:app --port 8765
```

## 修订历史

| 版本 | 日期 | 摘要 |
|------|------|------|
| v1.0.0 | 2026-08-25 | 首个可用底座：内核 + 11 模块 + 工具链 + 数据库/缓存接入 + 四项风险清除 + RBAC 服务层 |

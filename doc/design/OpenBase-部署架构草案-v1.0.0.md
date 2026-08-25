# OpenBase 部署架构草案 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Draft] |
| 适用环境 | Dev / Test / Pro |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 最后更新 | 2026-08-25 |

---

## 1. 部署形态

OpenBase 为代码级复用底座（PyPI 包），不独立部署服务；部署对象为**依赖 OpenBase 的业务系统**。本草案定义各业务系统集成 OpenBase 后的部署拓扑与依赖基础设施。

```
┌────────────────────────────────────────────┐
│ 业务系统容器（如 OpenLLM）                  │
│  ┌────────────────────────────────────┐   │
│  │ 业务系统特色服务（编排/路由/回写）   │   │
│  │  + openbase 包（内嵌底座）          │   │
│  └────────────────────────────────────┘   │
└──────────────────┬─────────────────────────┘
                   │
┌──────────────────▼─────────────────────────┐
│ 共享基础设施（部署编排管理）                │
│  PostgreSQL（多租户 Schema）               │
│  Redis（缓存/会话/SSE pub-sub）            │
│  Langfuse（可观测，OTLP 对接）             │
│  Prometheus + Grafana（指标/告警）         │
└────────────────────────────────────────────┘
```

## 2. 环境规划

| 环境 | 用途 | 基础设施 | 说明 |
|------|------|---------|------|
| Dev | 开发联调 | 本地 Docker Compose（PG/Redis）+ 可选 Langfuse | openbase 以源码安装（pip install -e） |
| Test | 集成测试 | 独立 PG/Redis + Langfuse + Prometheus/Grafana | 与 Dev 隔离 |
| Pro | 生产 | 高可用 PG/Redis + Langfuse + Grafana | 多副本 |

## 3. 服务端口约定

| 服务 | 端口 | 说明 |
|------|------|------|
| 业务系统 API | 8000（示例，各系统自定义） | FastAPI 应用 |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存/会话 |
| Langfuse | 3000（UI）/ 4318（OTLP） | 可观测 |
| Prometheus | 9090 | 指标采集 |
| Grafana | 3001 | 仪表盘 |

## 4. 环境配置（.env 约定）

```
# 数据库
OPENBASE_DB_URL=postgresql+asyncpg://user:pass@host:5432/openbase
# Redis
OPENBASE_REDIS_URL=redis://host:6379/0
# 可观测
OPENBASE_OTLP_ENDPOINT=http://langfuse:4318
OPENBASE_OTEL_ENABLED=true
OPENBASE_LANGFUSE_ENABLED=true
# 鉴权
OPENBASE_JWT_SECRET=***（加密配置）
OPENBASE_JWT_EXPIRE=7200
OPENBASE_REFRESH_EXPIRE=604800
# 多租户
OPENBASE_TENANT_MODE=schema
# 文件存储
OPENBASE_STORAGE_BACKEND=local|minio|s3
```

## 5. 健康检查与就绪

| 检查 | 说明 |
|------|------|
| /health | 业务系统存活检查（openbase audit 模块提供） |
| 数据库就绪 | 启动时连接检查 + Alembic 迁移 |
| Langfuse 依赖 | 可降级（仅 OTel，见 RQ-002） |

## 6. 部署步骤（业务系统集成）

```
① pip install openbase（或依赖引入）
② 配置 .env（数据库/Redis/可观测）
③ alembic upgrade head（公共 Schema + 租户模板迁移）
④ uvicorn 启动业务系统（含 openbase 模块）
⑤ /health 检查通过
```

## 7. 回滚策略

| 场景 | 回滚动作 |
|------|---------|
| openbase 版本问题 | 回退 pyproject 中 openbase 版本号，重新部署 |
| 数据库迁移问题 | Alembic downgrade + 数据修复 |
| 配置错误 | config 模块版本回滚（保留 ≥10 版） |

## 8. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-08-25 | AA-OpenBase-Dev | 初始创建：部署形态（代码级底座）、三环境规划、端口约定、环境配置、健康检查、部署步骤、回滚策略 |

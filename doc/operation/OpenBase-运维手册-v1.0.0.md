# OpenBase 运维手册 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Approved] |
| 作者 | OE-OpenBase-Dev |
| 日期 | 2026-08-25 |
| 存放 | doc/operation/ |

---

## 1. 服务概述

| 项 | 内容 |
|----|------|
| 服务名 | openbase（统一基础设施底座） |
| 入口 | uvicorn openbase.demo_app:app |
| 端口 | 8765（Dev） |
| 依赖 | PostgreSQL（192.168.0.151:5432/nuct）+ Redis（6380，可选降级） |

## 2. 启动与停止

```powershell
# 启动（环境变量注入）
$env:OPENBASE_DB_URL = "postgresql+asyncpg://...@192.168.0.151:5432/nuct"
$env:OPENBASE_REDIS_URL = "redis://:...@192.168.0.151:6380/0"
$env:OPENBASE_JWT_SECRET = "<生产密钥>"
python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8765

# 停止
Stop-Process -Name python  # 或任务管理器结束对应进程
```

## 3. 健康检查与排障

| 操作 | 命令 | 预期 |
|------|------|------|
| 健康检查 | GET /health | {"status":"ok"} |
| 登录验证 | POST /api/v1/auth/login | 200 + token |
| 查看日志 | uvicorn 控制台（结构化日志） | 无 ERROR 堆积 |
| Redis 降级 | 日志含 "redis unavailable" | 功能正常（缓存禁用） |
| DB 降级 | 日志含 "fallback to memory" | 登录/业务降级内存（生产建议禁用） |

**常见故障**：
- 端口占用：换端口或释放占用进程
- 数据库连接失败：检查 PG 连通性（192.168.0.151:5432）与 openbase schema 权限
- Redis 未启动：不影响功能，缓存自动禁用（日志警告）
- 登录失败：确认 admin 用户存在（openbase.users）且密码正确

## 4. 数据库运维

| 项 | 内容 |
|----|------|
| Schema | openbase（共享库 nuct 内隔离） |
| 表 | 17 张（auth/dict/config/scheduler/storage/notify/audit） |
| 备份 | 依赖共享库整体备份策略（PG dump，每日） |
| 迁移 | 幂等 SQL（create_all + 种子），重跑安全 |

## 5. 缓存运维（Redis）

| 键前缀 | 用途 | TTL |
|--------|------|-----|
| openbase:user:* | 用户缓存 | 300s |
| openbase:dict:*:items | 字典项缓存 | 300s |
| openbase:notify:* | SSE 广播 | - |

缓存键自动过期；配置变更自动失效（dict 写入/删除时 delete 键）。

## 6. 安全运维

| 项 | 内容 |
|----|------|
| JWT Secret | 生产必须覆盖默认值（环境变量 OPENBASE_JWT_SECRET） |
| MCP API Key | 生产必须覆盖（OPENBASE_MCP_API_KEYS） |
| 敏感文件 | .env* 不入库（gitignore） |
| 权限 | 业务接口 JWT；MCP 工具 API Key |

## 7. 运维移交清单

| 项 | 状态 |
|----|------|
| 运维联系人 | OE-OpenBase-Dev（当前） |
| SLA/SLO | 健康检查 200（99.9% 目标）；P99 < 2s |
| 排障手册 | 本章节 §3 |
| 回滚 | 见回滚方案 v1.0.0 |

## 8. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | OE-OpenBase-Dev | 初始创建：服务概述/启停/排障/数据库/缓存/安全运维/移交清单 |

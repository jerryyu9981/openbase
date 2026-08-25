# OpenBase 部署执行报告 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Approved] |
| 作者 | DO-OpenBase-Dev |
| 日期 | 2026-08-25 |
| 存放 | doc/operation/ |

---

## 1. 部署信息

| 项 | 值 |
|----|-----|
| 目标环境 | Dev（192.168.0.151 共享基础设施） |
| 部署方式 | 源码直接部署（uvicorn） |
| 待部署版本 | v1.0.0（git commit 4c2edd8，tag v1.0.0） |
| 部署时间 | 2026-08-25 |

## 2. 部署执行记录

| 步骤 | 命令 | 结果 |
|------|------|------|
| 1. 版本确认 | `git rev-parse main` → 4c2edd8 | ✅ |
| 2. Tag 验证 | `git ls-remote origin/backup refs/tags/v1.0.0` → 三处一致 | ✅ |
| 3. 环境变量注入 | OPENBASE_DB_URL / REDIS_URL / JWT_SECRET | ✅ |
| 4. 服务启动 | `uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8765` | ✅ "Application startup complete" |
| 5. 数据库初始化 | 启动自动建 schema/表 + 种子 admin + 恢复配置 | ✅（幂等） |
| 6. Redis 接入 | 缓存客户端连接（2s 超时，失败降级） | ✅ |

## 3. 数据库变更执行

| 项 | 内容 |
|----|------|
| 建表 | openbase schema 17 张表（幂等 create_all） |
| 种子 | admin 用户 + admin 角色 + * 权限 + user_role/role_permission 关联（幂等） |
| 配置恢复 | ConfigStore.hydrate（configs/config_versions） |
| 回滚说明 | 全部幂等 SQL，可重复执行；无破坏性变更 |

## 4. 构建与制品

| 项 | 内容 |
|----|------|
| 构建验证 | `pip install -e . --no-build-isolation` → 退出码 0 |
| 依赖锁定 | pyproject.toml（requires-python >=3.10） |
| 敏感配置 | .env* 未提交（gitignore），密钥经环境变量注入 |

## 5. 部署验证摘要

部署后执行上线验证 13 项全部通过（health/login/鉴权/dict/config/MCP/OpenAPI/Redis），详见上线检查报告 v1.0.0。

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | DO-OpenBase-Dev | 初始创建：v1.0.0 Dev 环境部署执行记录，数据库幂等初始化，上线验证 13/13 通过 |

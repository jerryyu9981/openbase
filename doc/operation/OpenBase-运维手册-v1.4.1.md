# OpenBase 运维手册 - v1.4.1

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.1 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | OE-OpenBase-Pro |
| 创建日期 | 2026-08-29 |
| 存放 | doc/operation/ |

---

## 1. 系统概述

| 项 | 说明 |
|----|------|
| 功能简介 | 四系统统一基础设施公共底座（认证汇聚/RBAC/多租户/网关/存储/审计） |
| 技术栈 | Python 3.10 + FastAPI + SQLAlchemy(async) + Vue3 + Vite |
| 关键新增（v1.4.1） | 服务级 API Key 认证（签发/认证/吊销）+ proxy 双通道 + S3/MinIO 存储 |

## 2. 服务管理

| 服务 | 启动命令 | 端口 | 健康检查 |
|------|---------|:----:|---------|
| 后端 | `uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000`（需加载 .env.shared-infra） | 8000 | `GET /health` |
| 前端 | `cd openbase-ui && npm run dev` | 5173/5174 | `GET /` |

## 3. 环境与配置

| 配置 | 位置 |
|------|------|
| 共享基础设施连接 | `.env.shared-infra`（PG/Redis/MinIO/ChromaDB/Qdrant/Neo4j，192.168.0.151） |
| 模块启停 | `openbase/settings.py`（AVAILABLE_MODULES + enable_module） |
| 存储后端切换 | `storage_backend=local\|minio\|s3` + `MINIO_*` 环境变量 |

## 4. 监控与告警

| 项 | 现状 |
|----|------|
| 日志 | 后端启动日志（uvicorn stdout）+ 结构化 logging（extra） |
| 审计 | audit 模块记录 API 调用（含 tenant_id/operator_id） |
| 指标/告警 | OTel/告警接入属 B 类（v1.5+），当前未启用 |

## 5. 常见问题处理

| 问题 | 排查/处理 |
|------|----------|
| 8000 端口被占用 | 查找占用进程（Get-NetTCPConnection -LocalPort 8000）并停止后重启 |
| 服务 Key 重启后失效 | 内存存储特性（P2 债务）；生产接 DB 前需重新签发 |
| proxy 返回 502 SYS_502 | 四系统未启动（对接挂起），预期行为；认证层已通过 |
| 前端 5173 占用 | Vite 自动切换端口，以启动日志为准 |
| PG 连接失败 | 检查 192.168.0.151 可达性 + POSTGRES_URL 配置 |

## 6. 运维移交清单

| 项 | 移交说明 |
|----|---------|
| 服务启动脚本 | 发布计划 §5 发布步骤（启动命令/环境加载） |
| 回滚路径 | 回滚方案 v1.4.1（git checkout v1.4.0 + 重启） |
| 数据说明 | 数据运维说明 v1.4.1（无迁移；种子用户；服务 Key 内存态） |
| 已知限制 | 服务 Key 无持久化（P2）；S3 生产验证待 MinIO 全量接入；四系统对接挂起 |
| 联系人 | PM-OpenBase-Dev（用户）；DO-OpenBase-Test |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-29 | OE-OpenBase-Pro | 初始创建：v1.4.1 运维手册（服务管理/常见问题/移交清单） |

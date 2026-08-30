# OpenBase 部署执行报告 - v1.4.1

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.1 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | DO-OpenBase-Test |
| 创建日期 | 2026-08-29 |
| 存放 | doc/operation/ |

---

## 1. 部署概述

| 项 | 值 |
|----|-----|
| 部署环境 | Dev（本机 127.0.0.1） |
| 部署版本 | v1.4.1（代码含 TD-141-01~09） |
| 部署时间 | 2026-08-29 |
| 部署方式 | 源码直接部署（uvicorn + Vite），无容器 |
| 部署负责人 | DO-OpenBase-Test |

## 2. 环境配置说明

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 后端端口 | 127.0.0.1:8000 | uvicorn openbase.demo_app:app |
| 前端端口 | localhost:5174 | Vite（5173 被占用自动切换） |
| PostgreSQL | 192.168.0.151:5432/nuct（openbase schema） | .env.shared-infra POSTGRES_URL |
| Redis | 192.168.0.151:6380 | .env.shared-infra REDIS_URL |
| MinIO | 192.168.0.151:9000 | .env.shared-infra MINIO_ENDPOINT |
| 四系统 | 8001/8010/8020/8030 未启动 | proxy 上游 502 为预期（对接挂起） |
| 密钥管理 | .env.shared-infra 不入 git（.gitignore） | 无密钥泄露 |

## 3. 构建与制品记录

| 项 | 说明 |
|----|------|
| 构建命令 | 后端：无构建步骤（源码直跑）；前端：Vite dev（npm run dev） |
| 静态检查 | `python -m ruff check openbase tests` → All checks passed |
| 测试验证 | pytest 91/91（12 文件）+ 真实环境 4/4 + UAT 14/14 |
| 制品校验 | OpenAPI 含 `/api/v1/auth/api-keys`、`/api/v1/proxy/{system}/{path}` 路由 |
| 版本标识 | openbase 包 __version__ 1.0.0（项目发布版本 v1.4.1） |

## 4. 部署执行记录

| 步骤 | 命令/操作 | 结果 |
|:----:|-----------|:----:|
| 1 | 停止旧进程（PID 47516，旧代码 v1.4.0 走查遗留，占用 8000） | ✅ 端口释放 |
| 2 | `Get-Content .env.shared-infra ... SetEnvironmentVariable` + `uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000` | ✅ Uvicorn running |
| 3 | `cd openbase-ui && npm run dev` | ✅ Vite ready（5174） |
| 4 | `GET /health` | ✅ 200 |
| 5 | OpenAPI 路由核对 | ✅ api-keys + proxy 路由存在 |
| 6 | UAT 冒烟复跑 | ✅ 14/14 PASS |

## 5. 部署验证结果

| 验证项 | 结果 | 关联 TT-ID |
|--------|:----:|-----------|
| 登录 admin（真实 PG） | ✅ | TT-v1.4.1-001 |
| 服务 Key 签发/列表/吊销 | ✅ | TT-v1.4.1-003/017 |
| proxy 双通道认证（X-API-Key/Bearer/JWT） | ✅ | TT-v1.4.1-041~044/046 |
| 越权/越 scope 拒绝（401/403） | ✅ | TT-v1.4.1-018/045 |
| 四维身份头 | ✅ | TT-v1.4.1-013 |
| 前端页面可达（5174） | ✅ | 走查 7 步 |

## 6. 问题记录

| 问题 | 处置 |
|------|------|
| 8000 端口被旧进程占用 | 停止旧进程后重新部署（部署前端口核验） |
| 5173 端口被占用 | Vite 自动切换 5174（不影响部署） |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-29 | DO-OpenBase-Test | 初始创建：v1.4.1 部署执行（Dev 环境源码部署，验证全通过） |

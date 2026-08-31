# OpenBase 运维手册 - v1.4.5

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.5 |
| 文档版本 | v1.0.0 |
| 状态 | [Final] |
| 作者 | OP-OpenBase-Dev |
| 创建日期 | 2026-09-01 |
| 存放 | doc/operation/ |

---

## 1. 服务清单

| 服务 | 端口 | 启动命令 | 健康检查 |
|------|:---:|----------|----------|
| OpenBase 后端 | 8000 | `python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000` | 登录 API / /openapi.json |
| DPS 后端 | 8030 | `$env:API_PORT='8030'; $env:SQLITE_FALLBACK='true'; python -m uvicorn rest_api.app:app --app-dir src` | /health/liveness（经 dps-proxy） |
| OpenBase 前端 | 5173 | `npm run dev`（openbase-ui） | GET / |

## 2. 关键配置（settings / .env）

| 配置 | 默认值 | 说明 |
|------|--------|------|
| dps_upstream_base | http://127.0.0.1:8030 | DPS 上游地址 |
| dps_upstream_timeout | 20.0 | 上游超时（秒） |
| dps_default_org_id / dps_default_tenant_id | "" | 身份头兜底值（JWT 缺字段时） |
| dps_org_map / dps_tenant_map | "" | 组织/租户映射表（JSON，OpenBase 值 → DPS 值） |

## 3. 常见故障与排障

| 故障 | 现象 | 排障 |
|------|------|------|
| DPS 上游不可达 | dps-proxy 返回 502 SYS_502 "unreachable" | 检查 DPS 8030 是否启动（config.settings 缺陷见任务书 M4） |
| 401 未认证 | dps-proxy 全部端点 401 | 检查 OpenBase JWT 是否过期（前端重新登录） |
| 身份头缺 org/tenant | 上游 403（组织/租户无效） | 检查 JWT payload 是否含 org_id/tenant_id；配置 dps_default_* / 映射表 |
| 前端画像页 502 | 画像列表/详情错误提示 502 | DPS 未就绪（H 类）；DPS 就绪后刷新 |

## 4. 日志与监控

| 项 | 说明 |
|----|------|
| 日志 | 结构化日志（logging + extra）；dps_proxy logger "openbase.dps_proxy"（path/upstream_status/duration_ms） |
| 指标 | observability 模块（http 指标挂 path 标签） |
| 审计 | proxy 转发关键操作记录审计日志 |

## 5. 告警（Pro 部署时）

| 级别 | 规则 | 通道 |
|------|------|------|
| P0 | dps-proxy 错误率 >1% 或健康检查失败 | 15 分钟电话 |
| P1 | 上游不可达 502 持续 >5 分钟 | 1 小时 IM |
| P2 | 画像接口 P99 超基线 50% | 24 小时 IM |

## 6. 版本升级指引

| 步骤 | 操作 |
|------|------|
| 1 | `git pull origin main` + `git checkout v1.4.5`（或新 tag） |
| 2 | 核对 .devflow/project-config.json 版本号 |
| 3 | 重启服务（后端 + 前端 build） |
| 4 | 上线验证（对照上线检查报告清单） |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-01 | OP-OpenBase-Dev | 初始创建：服务清单/配置/故障排障（含 M4）/日志监控/告警/升级指引 |

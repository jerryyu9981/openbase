# OpenBase 第三方集成设计文档 - v1.4.5

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.5 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | SA-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 存放 | doc/design/ |

---

## 1. 集成对象

| 项 | 内容 |
|----|------|
| 集成系统 | DPS（Data Portrait System，数据画像系统）v2.7.1 |
| 项目路径 | D:\Trae CN\myproject\Dev\DPS |
| 技术栈 | Python + FastAPI + Uvicorn；入口 src/rest_api/app.py |
| 端口 | API_PORT（默认 8000 → 规划 8030）；MCP 8013（不接入） |
| 数据库 | PostgreSQL（默认）/ SQLite 降级（SQLITE_FALLBACK=true） |

## 2. 认证契约（DPS 侧）

| 项 | 内容 |
|----|------|
| 认证形态 | Header 身份直传 + RBAC 中间件（X-Org-ID/X-Tenant-ID/X-User-ID 必传；X-User-Role 默认 "user"） |
| 中间件 | TenantMiddleware（缺失 401；组织/租户无效 403）+ PermissionMiddleware（无权限 403） |
| 白名单 | /health*、/metrics、/api/v2/auth/login、/api/v2/organizations、/api/v2/permissions/check |
| 组织/租户校验 | platform.organization/tenant 表 active 状态 |
| 本版本方案 | OpenBase dps-proxy 唯一认证入口（JWT 门禁）+ 身份头注入（四头构造，需求 §3 / API 设计 §2） |

## 3. 端点映射（OpenBase → DPS）

| OpenBase 路径 | DPS 上游路径 | 说明 |
|---------------|-------------|------|
| GET /api/v1/dps-proxy/portraits | GET /api/v2/portrait/list | 画像列表（分页） |
| GET /api/v1/dps-proxy/portraits/{person_id} | GET /api/v2/portrait/{person_id} | 画像详情 |
| POST /api/v1/dps-proxy/portraits/calculate | POST /api/v2/portrait/calculate | 画像计算 |
| GET /api/v1/dps-proxy/tags/categories | GET /api/v2/tags/categories | 标签分类 |
| GET /api/v1/dps-proxy/reports/overview | GET /api/v2/reports/overview | 报表概览 |
| GET /api/v1/dps-proxy/batch/tasks/{task_id} | GET /api/v2/batch/import/{task_id}/status | 批量任务状态 |
| GET /api/v1/dps-proxy/audit/logs | GET /api/v2/audit/logs | 审计日志 |
| GET /api/v1/dps-proxy/health | GET /health/liveness | 健康透传（白名单） |

## 4. 响应与错误契约

| 形态 | 处理 |
|------|------|
| 成功 {code:200, message:"success", data} | data 提取 → OpenBase {code:0, message:"success", data, timestamp} |
| 404 {detail: "..."}（FastAPI） | code=404 + message=detail 归一化 |
| 中间件错误 {code:401/403, message, data} | code/message 透传 |
| 网络不可达 | BaseError(SYS_UPSTREAM_ERROR) → 502 |

## 5. 集成风险与任务书登记

| 风险 | 级别 | 缓解 | 登记 |
|------|:---:|------|:---:|
| 组织/租户映射（OpenBase 值 ↔ DPS 实体） | P1 | 种子数据 + dps_org_map/dps_tenant_map 映射表（OQ-145-1） | 任务书 M1 |
| DPS 无标准登录（login 白名单未实现） | P1 | OpenBase JWT 门禁 + 身份头注入兜底 | 任务书 M1 |
| 画像计算依赖 AI 模型服务 | P2 | 联调确认（OQ-145-2） | 任务书 M2 |
| 响应格式混合（{code,message,data} + {detail}） | P2 | proxy {detail} 归一化 | 任务书 M2 |
| /api/v1 与 /api/v2 双挂载 | P2 | 统一走 /api/v2 标准路由 | 任务书 M3 |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | SA-OpenBase-Dev | 初始创建：DPS 集成对象/认证契约/端点映射/响应错误契约/风险登记（M1~M3） |

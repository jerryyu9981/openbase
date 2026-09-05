# OpenBase-DPS对接使用指南-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-DPS-GUIDE-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Review] |
| 日期 | 2026-09-05 |
| 作者 | AD（跨项目分析） |
| 适用范围 | OpenBase（8000）统一网关消费者（前端 portrait 页、OpenLLM 画像读写）、DPS（8030 受管 / 8000 直连）运维与联调 |

> 本文档定义经 OpenBase `/api/v1/dps-proxy` 消费 DPS 画像能力的方式：入口与身份、端点契约、错误与降级语义、种子、联调方法。契约事实基于 2026-09-04~05 实证与 OpenAPI（81 个 v1/v2 路径）核对。本指南与《OpenBase-DPS对接完善任务书》v1.9.0、《OpenBase-存量测试对齐任务清单》v1.1.0 配套。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-05 | AD（跨项目分析） | 初始版本：入口与身份、端点契约对照、错误/降级、种子、联调与配置 |

---

## 1. 入口与身份

- 网关入口：OpenBase `http://127.0.0.1:8000`，dps-proxy 前缀 `/api/v1/dps-proxy`。
- DPS 直连（运维/调试）：受管 8030（编排），源码默认 8000；健康 `/health/liveness`。
- 认证：调用 dps-proxy 需 `Authorization: Bearer <OpenBase JWT>`（登录 `/api/v1/auth/login` 或 OIDC `/api/v1/auth/oidc/*` 获取）。
- 身份头（dps-proxy 自动注入，客户端无需传）：`X-User-ID`、`X-Tenant-ID`、`X-Org-ID`、`X-User-Role`。租户键优先 `tenant_code` claim（v1.9.0 起增量签发），旧令牌自动回退数值链；`dps_tenant_map/dps_org_map` 支持按 code 键值转换，未命中走 `dps_default_*`。
- 直连 DPS（绕过网关）必须自带头与角色绑定一致：`X-User-ID`（须在 `platform.user_roles` 有绑定）、`X-User-Role`、`X-Org-ID`、`X-Tenant-ID`；无绑定 → 403（fail-closed）；缺头 → 401。

## 2. 端点-契约对照（dps-proxy → DPS /api/v2）

| proxy 端点 | DPS v2 目标 | 请求契约 | 说明 |
|---|---|---|---|
| GET /portraits | GET /api/v2/portrait/list | query: page(默认1)、page_size(默认20) | 画像列表 |
| GET /portraits/{person_id} | GET /api/v2/portrait/{person_id} | path | 画像详情（person 子集列 + attributes_json→business + tags） |
| POST /portraits/calculate | POST /api/v2/portrait/calculate | body 透传（person_id/tenant_id/input_text 实测形态） | 画像计算 |
| PUT /portraits/{person_id} | PUT /api/v2/portrait/{person_id} | body {person{name?,status?,scores?}, business{attributes?}}；person 仅白名单列，attributes 整体覆盖 | 画像更新（version 自增 + profile_history 快照 + 缓存失效） |
| GET/POST /tags/categories | /api/v2/tags/categories | body/路径透传 | 标签分类管理 |
| PUT/DELETE /tags/categories/{id} | /api/v2/tags/categories/{id} | 路径透传 | 同上 |
| GET /reports/overview | GET /api/v2/reports/overview | 无额外参数 | 报表概览 |
| GET /batch/tasks/{task_id} | GET /api/v2/batch/import/{task_id}/status | path | 批量导入任务状态 |
| GET /audit/logs | GET /api/v2/audit/logs | query: start_time/end_time/user_id/resource_type/action/page/page_size | 审计日志 |
| GET /health | /health/liveness | 免鉴权 | 上游健康透传 |

未开放面（dps-proxy 不转发；如需开放按规划评估）：risk-assess、annotate、associate、statistics、trend、track、version、compare、search、suggestions、画像 tags（person 级）、ai:analyze/detect/predict、generate、labels、reports 扩展（dimensions/organizations/tags/trend）、streams、permissions、organizations、tenants、batch export。

## 3. 响应与错误语义

- 统一 envelope（dps-proxy 归一）：2xx `{code: 0, message: "success", data: {...}, timestamp}`；非 2xx `{code: <上游错误码|HTTP>, message, data, timestamp}`。
- 画像更新响应 data 形态：`{person_id, updated(ISO), attributes}`（PUT 后读回整体 JSON）。
- `/api/v1/portrait/*` 写（旧 v1 面）恒 403：v2 为唯一写面，勿使用 v1 前缀写。
- 上游不可达：连续失败 < `dps_degrade_threshold`（默认 3）→ 统一 SYS 502；达阈值 → **503 envelope `{degraded: true, consecutive_failures, last_error}` + 响应头 `X-DPS-Upstream-Degraded: true`**；探活恢复后自动正常（fail-open 语义保持）。

## 4. 数据源与种子（DPS 侧）

- 数据源：受管环境强制共享 PostgreSQL（编排注入 `.env.shared-infra` 的 POSTGRES_URL + `SQLITE_FALLBACK=false`）；schema `platform.*`（27 表），启动 init_schema 幂等建表。
- 一键种子（幂等，可重复执行）：

```powershell
python D:\Trae CN\myproject\Dev\DPS\scripts\seed-shared-infra.py
```

预置：org（10000000-...-0001）、tenant（20000000-...-0001）、roles（super_admin/org_admin/user 等 6）、绑定 `1:super_admin`（env `DPS_DEMO_USER_ROLES` 可覆盖为 `uid:role,uid:role`）、画像样本 3 条（person_id 命名 `{tenant_code}_{user_ref}_NN`，external 语义对齐）。

直连联调四头示例（种子数据）：`X-Org-ID=10000000-0000-0000-0000-000000000001`、`X-Tenant-ID=20000000-0000-0000-0000-000000000001`。

## 5. 联调方法

1. 起服：`scripts/service-orchestrator.ps1 -Action start`（五件套 + 前端；DPS 8030 探活 `/health/liveness`）。
2. 登录拿令牌：`POST /api/v1/auth/login`（本地账号）或 OIDC 授权码；Bearer 调 dps-proxy。
3. 冒烟 S4 组（清单 v1.1.0）：list/get/calculate/PUT/重启存活/降级/审计；真实模式画像端到端用例归冒烟 P9。
4. 直连 DPS 验证写链：PUT → GET 确认 version 递增；查 `platform.profile_history` 快照行。
5. 观测降级：停 DPS 单服务后连续请求 dps-proxy，≥3 次失败观察 503 + `X-DPS-Upstream-Degraded`；重启 DPS 后自动恢复。

## 6. 配置项速查

| 项 | 默认 | 说明 |
|---|---|---|
| OpenBase `dps_upstream_base` | http://127.0.0.1:8000 | dps-proxy/通用 proxy 上游地址；编排覆盖为 8030（env OPENBASE_DPS_UPSTREAM_BASE） |
| OpenBase `dps_health_check_enabled` | true | 惰性探活开关 |
| OpenBase `dps_health_interval` | 30.0s | 探活节流间隔 |
| OpenBase `dps_degrade_threshold` | 3 | 连续失败降级阈值（env OPENBASE_DPS_DEGRADE_THRESHOLD） |
| OpenBase `dps_tenant_map/dps_org_map` | "" | JSON 映射（code 键优先语义） |
| OpenBase `dps_default_tenant_id/dps_default_org_id` | "" | 兜底值（空则带头原值） |
| DPS `API_PORT` | 8000 | 受管覆盖 8030 |
| DPS `DATABASE_URL` | 本地默认 | 受管注入共享 POSTGRES_URL |
| DPS `SQLITE_FALLBACK` | false | 禁止静默 SQLite 回退（受管） |
| DPS `PERMISSION_ENABLED` | true | 权限校验（绑定缺省 fail-closed） |
| DPS `DPS_DEMO_USER_ROLES` | 1:super_admin | 种子角色绑定覆盖 |

## 7. 版本与配套

- 决策上下文：《四件套身份隔离治理评审》v1.5.0（R3~R5）、《真实契约落地与沉淀收敛立项方案》v1.2.0、《OpenBase-DPS对接完善任务书》v1.9.0。
- 本文档随端点/契约变更升版并同步修订历史；每版本需以冒烟 S4 与 OpenAPI 对照复核。

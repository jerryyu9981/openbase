# OpenBase-DPS对接完善任务书-v1.7.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-DPS-v1.7.0 |
| 版本 | v1.7.0 |
| 状态 | [Review] |
| 日期 | 2026-09-05 |
| 作者 | AD（跨项目分析） |
| 版本主题 | OpenBase 与 DPS 对接全量清理：运行形态、端点契约、身份映射、数据模型、可用性、文档与验收（P1/P2/P3.1/P3.2/P5/P6/P7 已实施；P4 对照完成；P8/P9 待办） |
| 适用范围 | OpenBase（8000，dps-proxy 模块）与 DPS（src/rest_api v2，默认 8000；编排 8030），由独立会话据此实施 |

> 本任务书供另一个会话专据此完善 OpenBase 与 DPS 的对接。所有修改项均含现状、目标、涉及文件、实现要点、验收标准与验证方法，可直接照单执行。事实锚点基于 2026-09-04 真实验证与两仓库代码核对；凡标注"需复核"处为执行前须在目标环境再确认的开放项。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-05 | AD（跨项目分析） | 初始版本：OpenBase-DPS 对接现状盘点与待完善项 P1~P9 详细方案、实施顺序、回归清单、风险登记 |
| v1.1.0 | 2026-09-05 | AD（跨项目分析） | P3 拆分子项（P3.1 OpenBase 增量 code / P3.2 DPS 去硬绑 / P3.3 全量 code 化=治理 P1-2/P1-3） |
| v1.2.0 | 2026-09-05 | AD（跨项目分析） | 实施回填：P1 编排强制共享 PG（0499838）、P2 地址收敛（aae1de7）、P3.1 tenant_code 增量（1074751） |
| v1.3.0 | 2026-09-05 | AD（跨项目分析） | P3.2/P7 实施回填：硬绑移除核对（v2.8.1 无残留）；seed-shared-infra.py 共享 PG 幂等实跑 |
| v1.4.0 | 2026-09-05 | AD（跨项目分析） | P5 实施回填：写链 v2.8.1 已实现 + 真实 PG 实证（version 9、profile_history 7 行同步） |
| v1.5.0 | 2026-09-05 | AD（跨项目分析） | P4 端点-契约对照回填（OpenAPI 实证 81 路径 + 10 端点映射表；/profile/v1 决策待办） |
| v1.6.0 | 2026-09-05 | AD（跨项目分析） | P6 实施回填：dps-proxy 连续失败降级 503（22d369f）；dps_degrade_threshold 配置化 |
| v1.7.0 | 2026-09-05 | AD（跨项目分析） | 整文件重建：汇总 P1~P7 实施状态与 P4 对照/P6 降级记录；P8/P9 待办；本文件编辑期多次遭外部进程回滚，本版为单一事实源基线 |

---

## 1. 背景与目标

OpenBase 以 JWT 门禁 + 专属 proxy 聚合下游，DPS（数据画像系统）经 `/api/v1/dps-proxy` 暴露给统一前端。已完成：R-381 dps-proxy 主体、P0-3 端口与惰性探活、Phase C 画像持久化演进（`attributes_json` + `PUT /api/v2/portrait/{person_id}`）。真实验证（2026-09-04 冒烟 S4）暴露：DPS 运行态 500、空库、沙箱写限制、PG 方言与身份映射待收敛。本任务书把 OpenBase↔DPS 对接按"生产可用"标准清理一遍。

目标态：前端（portrait 页）与 OpenLLM（`OPENLLM_DPS_REAL`）均经 dps-proxy 获得一致、持久、按租户隔离、可观测的画像能力；DPS 数据源与 Schema 闭环；身份键同形；写链真实可用；降级可感知；冒烟全绿。

## 2. 对接现状总览（v1.0.0 基线快照；最新状态以 §3 记录与状态追踪表为准）

| 类别 | 状态 | 说明 |
|------|:---:|------|
| dps-proxy 网关入口与端点面 | ✅ 已完成 | 10 端点：画像 list/get/calculate/update、tags/categories 系列、reports/overview、batch/import status、audit/logs、health |
| 身份头注入与映射表 | ✅ P3.1 已实施 | 四头注入 + 增量 tenant_code claim（code 优先、数值兜底）+ 映射表 code 键 |
| DPS 运行形态与数据源 | ✅ P1 已闭环 | 编排强制共享 PG（DATABASE_URL + SQLITE_FALLBACK=false）；platform schema 27 表 |
| PG 方言适配 | ✅ 已验证 | database._pg_translate（qmark→$n）；快照 SQL 真实 PG 实证 |
| 画像读写契约 | ✅ P5 已实证 | PUT→version 递增 + profile_history 快照 + 缓存失效；/api/v1 写恒 403（契约） |
| 健康与可用性 | ✅ P6 已实施 | 惰性探活 + 连续失败降级 503（dps_degrade_threshold）；DPS 侧 fail-open 归治理 P2-2 |
| 数据与种子 | ✅ P7 已实施 | seed-shared-infra.py 幂等预置 org/tenant/roles/bindings/profile |
| 文档 | ⚠️ 缺失 | 对接使用指南未成文（P8） |
| 冒烟与回归 | ⚠️ 部分 | 回归子集通过；P9 冒烟门禁未执行 |

## 3. 待完善项详细方案

### P1 DPS 运行数据源与 Schema 初始化闭环 — ✅ 已实施

**实施与验证（v1.2.0，commit 0499838）**：编排注入共享 POSTGRES_URL + SQLITE_FALLBACK=false + 探活 /health/liveness；共享库 platform schema 27 表实证。

### P2 端口与地址收敛（三处一致）— ✅ 已实施

**实施与验证（v1.2.0，commit aae1de7）**：PROXY_SYSTEMS['dps'] 收敛 get_settings().dps_upstream_base；默认 8000 / 编排覆盖 8030 两态正确；test_settings+test_dps_proxy 27 passed。

### P3 身份四头与映射键收敛（治理 Q2/Q3）— 🔶 P3.1/P3.2 已实施

- **P3.1（v1.2.0，commit 1074751）**：auth `_resolve_tenant_code`（tenants.id→code，失败 WARN 不阻断）；login/refresh/oidc 增量签发 `tenant_code`；dps-proxy 头链 `tenant_code → user.tenant_id → jwt.org_id → dps_default_*`，X-Org-ID 在 code 存在时同形。验证：三态断言 + 50 passed。
- **P3.2（v1.3.0，DPS v2.8.1 核对）**：启动硬绑已移除（app.py L137-139 / main.py L179 仅注释，grep 无残留）；角色绑定由种子显式写入（seed-shared-infra.py DEFAULT_USER_BINDINGS="1:super_admin"，env DPS_DEMO_USER_ROLES 覆盖）；未绑定 fail-closed 403 待冒烟实证。
- **P3.3（跨仓，待立项）**：全量对外租户键切 code = 治理 P1-2/P1-3 范围。

### P4 端点面契约对齐与补齐 — 🔶 对照完成（实施待决策）

**对照（v1.5.0，2026-09-05 OpenAPI 实证 81 个 v1/v2 路径）**：

| proxy 端点 | DPS v2 目标 | 请求契约 |
|---|---|---|
| GET /portraits | GET /api/v2/portrait/list | page=1、page_size=20 透传 |
| GET /portraits/{pid} | GET /api/v2/portrait/{person_id} | path 参数 |
| POST /portraits/calculate | POST /api/v2/portrait/calculate | body 透传（person_id/tenant_id/input_text 实测） |
| PUT /portraits/{pid} | PUT /api/v2/portrait/{person_id} | body {person{白名单列},business{attributes}}（实证） |
| GET/POST /tags/categories、PUT/DELETE /tags/categories/{id} | /api/v2/tags/categories 系列 | body/路径透传 |
| GET /reports/overview | GET /api/v2/reports/overview | 无额外参数 |
| GET /batch/tasks/{id} | GET /api/v2/batch/import/{task_id}/status | path 参数 |
| GET /audit/logs | GET /api/v2/audit/logs | start_time/end_time/user_id/resource_type/action/page/page_size |
| GET /health | /health/liveness | 白名单免鉴权 |

**登记**：错误 envelope 由 `_adapt_response` 归一（2xx code=0；错误提取 body.code→detail→HTTP）。未开放面（默认不开，前端规划需要时再开放）：risk-assess/annotate/associate/statistics/trend/track/version/compare/search/suggestions/画像 tags/ai:* /generate/labels/reports 扩展/streams/permissions/organizations/tenants/batch export。**/profile/v1 决策待办**：建议 OpenLLM ProfileAdapter real 映射 GET/PUT /portraits/{pid}（OpenLLM 仓另立实施项 + 前端对齐）。

### P5 画像数据模型与写链 — ✅ 已实施

**实施与验证（v1.4.0，DPS v2.8.1 + 真实 PG）**：`_record_profile_history_snapshot`（routes_profiles.py L517+）于 `_persist_portrait_update` 后写快照（L642-646，失败不阻塞）；version 服务端自增；`cache.invalidate_portrait` 失效。实测：样本 person_id 连续两次 PUT 均 200，version→9，profile_history 7 行 max(version)=9 同步；qmark 快照 SQL 经 _pg_translate 在 PG 正常。登记：/api/v1 写恒 403（契约）；annotation/track 非主写链维持现状。

### P6 可用性与降级治理 — ✅ 已实施

**实施与验证（v1.6.0，commit 22d369f）**：settings `dps_degrade_threshold`（默认 3，env OPENBASE_DPS_DEGRADE_THRESHOLD）；dps-proxy `_forward` 连接失败连续计数，达阈值返回 503 envelope{degraded:true, consecutive_failures, last_error} + X-DPS-Upstream-Degraded 头；探活恢复/成功自动归零；阈值内保持 SYS_502（fail-open）。验证：两段式行为断言 + 27 passed。残余：DPS 侧 DB 故障/权限引擎 fail-open 归治理 P2-2。

### P7 种子与演示数据预置 — ✅ 已实施

**实施与验证（v1.3.0）**：seed-shared-infra.py 共享 PG 幂等实跑 org=1/tenant=1/roles=6/user_roles=1（1:super_admin）/profile=3；重跑 0 新增。编排一键集成（启动后自动种子）可选登记。

### P8 文档与契约沉淀 — 待办

产出《OpenBase-DPS 对接使用指南 v1.0.0》（端点清单、身份头、错误 envelope、种子、联调、端口约定），参照 OpenMemory 指南体例并与治理/立项文档交叉引用。验收：可指导新会话独立完成 P9 冒烟。

### P9 验收与冒烟扩展 — 待办（门禁）

冒烟 S4 组全绿 + 回归套件通过：S4 扩展（重启存活、双租户隔离、version/history、停服降级、漂移重算 P1）；DPS/OpenBase/OpenLLM 回归命令 0 失败；编排起服健康 + DPS 表存在性断言。

## 4. 实施顺序与依赖

| 顺序 | 项 | 依赖 | 状态 |
|:---:|-----|------|------|
| 1 | P1 运行数据源与 Schema 闭环 | 共享 PG | ✅（0499838） |
| 2 | P2 端口地址收敛 | 无 | ✅（aae1de7） |
| 3 | P6 可用性降级 | P1 | ✅（22d369f） |
| 4 | P3 身份四头与映射收敛 | P1、P2 | 🔶 P3.1（1074751）/P3.2（v2.8.1）已实施；P3.3 待立项 |
| 5 | P7 种子与演示数据 | P3 | ✅（v1.3.0 实证） |
| 6 | P5 画像数据模型与写链 | P1、P3 | ✅（v2.8.1 + v1.4.0 实证） |
| 7 | P4 端点面契约对齐 | P5 | 🔶 对照完成；/profile/v1 决策待办 |
| 8 | P8 文档 | P1~P7 定稿 | 待办 |
| 9 | P9 验收与冒烟 | P1~P8 | 待办（门禁） |

## 5. 全量回归验证清单

| 命令 | 预期 |
|------|------|
| DPS：`python -m pytest src/tests -q`（受影响子集先行） | 0 失败（沙箱写限制用例按真实环境处理） |
| OpenBase：`python -m pytest tests -q` | 0 失败（dps-proxy/settings/gateway/auth 子集基线通过） |
| OpenLLM：profile/writeback 相关子集（DPS_REAL=true） | 0 失败 |
| 编排：service-orchestrator.ps1 start | 五服务健康；DPS 表存在性断言通过 |
| 冒烟 S4 组（清单 v1.1.0） | 全部 PASS（P1 级登记项除外） |

## 6. 风险与注意事项

- **沙箱写限制（环境）**：沙箱禁止写 DPS dps.db 等；共享 PG 已规避（P1）。
- **PG 方言**：_pg_translate 已落地并实证（P5 快照 SQL）。
- **权限默认开启**：硬绑已移除，绑定由种子显式写入；未绑定 fail-closed 待冒烟实证（P9）。
- **/api/v1 写恒 403**：既有契约；v2 为唯一写面。
- **文档单一事实源**：本任务书为 OpenBase-DPS 侧唯一执行依据；本文件编辑期多次遭外部进程回滚，v1.7.0 起以整文件重建内容为基线，后续更新建议一次整写。
- **/profile/v1 决策**：涉 OpenLLM 仓与前端，需对齐后另立实施项。

### 状态追踪表

| 项 | 状态 | 验证日期 | 备注 |
|:---:|------|:---:|------|
| P1 运行数据源与 Schema 闭环 | ✅ 已实施 | 2026-09-05 | 编排共享 PG（0499838）；27 表实证 |
| P2 端口地址收敛 | ✅ 已实施 | 2026-09-05 | PROXY_SYSTEMS['dps'] 同源（aae1de7） |
| P3 身份四头与映射收敛 | ✅ P3.1/P3.2 已实施 | 2026-09-05 | 1074751；v2.8.1 无硬绑残留 |
| P4 端点面契约对齐 | 🔶 对照完成 | 2026-09-05 | OpenAPI 81 路径实证；/profile/v1 待决策 |
| P5 画像数据模型与写链 | ✅ 已实施 | 2026-09-05 | version 9、快照 7 行同步实证 |
| P6 可用性降级 | ✅ 已实施 | 2026-09-05 | 连续失败 503（22d369f） |
| P7 种子与演示数据 | ✅ 已实施 | 2026-09-05 | seed 幂等实跑（roles 6/user_roles 1/profile 3） |
| P8 文档与契约沉淀 | 待办 | - | 对接使用指南 v1.0.0 |
| P9 验收与冒烟扩展 | 待办 | - | 门禁 |

**遗留事项**：P3.3 随治理 P1-2/P1-3 立项；/profile/v1 映射决策（OpenLLM 仓）；P8/P9 待办；冒烟 S4 全绿与真实联调（未绑定 fail-closed 实证、dps_tenant_map code 键部署值）待执行；DPS 侧 fail-open 归治理 P2-2。

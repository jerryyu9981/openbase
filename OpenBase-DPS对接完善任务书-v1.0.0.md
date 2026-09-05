# OpenBase-DPS对接完善任务书-v1.3.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-DPS-v1.3.0 |
| 版本 | v1.3.0 |
| 状态 | [Review] |
| 日期 | 2026-09-05 |
| 作者 | AD（跨项目分析） |
| 版本主题 | OpenBase 与 DPS 对接全量清理：运行形态、端点契约、身份映射、数据模型、可用性、文档与验收（P1/P2/P3.1/P3.2/P7 已实施） |
| 适用范围 | OpenBase（8000，dps-proxy 模块）与 DPS（src/rest_api v2，默认 8000；编排 8030），由独立会话据此实施 |

> 本任务书供另一个会话专据此完善 OpenBase 与 DPS 的对接。所有修改项均含现状、目标、涉及文件、实现要点、验收标准与验证方法，可直接照单执行。事实锚点基于 2026-09-04 真实验证与两仓库代码核对；凡标注"需复核"处为执行前须在目标环境再确认的开放项。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-05 | AD（跨项目分析） | 初始版本：OpenBase-DPS 对接现状盘点（表 2）与待完善项 P1~P9 详细方案、实施顺序、回归清单、风险登记 |
| v1.1.0 | 2026-09-05 | AD（跨项目分析） | P3 拆分子项（P3.1 OpenBase 增量 code / P3.2 DPS 去硬绑 / P3.3 全量 code 化=治理 P1-2/P1-3） |
| v1.2.0 | 2026-09-05 | AD（跨项目分析） | 实施回填：P1 编排强制共享 PG（0499838）、P2 地址收敛（aae1de7）、P3.1 tenant_code 增量（1074751） |
| v1.3.0 | 2026-09-05 | AD（跨项目分析） | P3.2/P7 实施回填：硬绑移除核对（v2.8.1 无残留）；seed-shared-infra.py 共享 PG 幂等实跑（roles 6/user_roles 1/profile 3）；元信息/状态表/§3 P3.x 同步（本次整文件重建） |

---

## 1. 背景与目标

OpenBase 以 JWT 门禁 + 专属 proxy 聚合下游，DPS（数据画像系统）经 `/api/v1/dps-proxy` 暴露给统一前端。已完成：R-381 dps-proxy 主体（画像列表/详情/计算/更新、标签、报表、批量、审计、健康透传）、P0-3 端口与惰性探活、Phase C 画像持久化演进（`attributes_json` + `PUT /api/v2/portrait/{person_id}`）、健康检查白名单。真实验证（2026-09-04 冒烟 S4）暴露：DPS 运行态 500（calc/get/PUT）、空库、沙箱写限制、PG 方言与身份映射待收敛。本任务书把 OpenBase↔DPS 对接按"生产可用"标准清理一遍，形成可执行清单。

目标态：五件套统一出口下，前端（portrait 页）与 OpenLLM（画像读/写回调，`OPENLLM_DPS_REAL`）均经 dps-proxy 获得一致、持久、按租户隔离、可观测的画像能力；DPS 数据源与 Schema 初始化闭环；身份键全链路同形；写链真实可用；冒烟全绿。

## 2. 对接现状总览（v1.0.0 基线快照；最新状态见 §3 实施记录与状态追踪表）

| 类别 | 状态 | 说明 |
|------|:---:|------|
| dps-proxy 网关入口与端点面 | ✅ 已完成 | prefix /api/v1/dps-proxy；GET /portraits、GET /portraits/{pid}、POST /portraits/calculate、PUT /portraits/{pid}、GET/POST /tags/categories、PUT/DELETE /tags/categories/{id}、GET /reports/overview、GET /batch/tasks/{id}、GET /audit/logs、GET /health（上游 /health/liveness） |
| 身份头注入与映射表 | ⚠️ 部分（v1.3.0 见 P3.1 已实施） | 四头注入 + dps_org_map/dps_tenant_map 值转换 + dps_default_* 兜底；v1.3.0 起签发含增量 tenant_code、dps-proxy code 优先 |
| DPS 运行形态与数据源 | ⚠️ 基线未闭环（v1.3.0 已闭环） | v1.3.0 起编排强制共享 PG（DATABASE_URL 注入 + SQLITE_FALLBACK=false），platform schema 27 表实证 |
| PG 方言适配 | ⚠️ 部分 | database.py 已加 _pg_translate（qmark→$n）；PG 冷路径写链待验证 |
| 画像读写契约 | ⚠️ 部分 | 读/写 v2 已代理持久化（attributes_json）；写链历史缺陷（annotation/version/track 疑死代码）待 P5 复核；/api/v1 写恒 403（文档化） |
| 健康与可用性 | ✅ 部分 | dps_upstream_base 探活惰性 fail-open；P2 起 PROXY_SYSTEMS['dps'] 同源；DPS fail-open 两处未治理（P6） |
| 数据与种子 | ⚠️ 基线缺失（v1.3.0 已实施） | v1.3.0 起 seed-shared-infra.py 幂等预置 org/tenant/roles/bindings/profile（实跑验证） |
| 冒烟与回归 | ⚠️ 部分 | 冒烟清单 S4 组已定义；回归基线已具备；P9 门禁未执行 |
| 文档 | ⚠️ 缺失 | 对接使用指南未成文（P8） |

## 3. 待完善项详细方案

### P1 DPS 运行数据源与 Schema 初始化闭环

**现状**：DPS 以 rest_api.app（8030）运行，无有效 PG 配置时静默回退 SQLite `./dps.db`（cwd 相对）；沙箱写限制下建表抛 `sqlite3.OperationalError: disk I/O error`，库 0 张表，画像请求全部 500；`/health` 不依赖表故服务显示"健康"（2026-09-04 实证）。

**目标**：DPS 在任何受管环境启动即获得可用 Schema；数据源选择显式化，杜绝"看似健康实则空库"。

**涉及文件**：DPS `src/config.py`、`src/database.py`、`src/rest_api/app.py`；OpenBase `scripts/service-orchestrator.ps1`；共享基础设施 `.env.shared-infra`。

**实现要点**：
1. 确定受管数据源并写入部署配置：共享 PG（`DATABASE_URL` 显式配置、`SQLITE_FALLBACK=false`）；禁止"默认值不可达→静默回退"路径（回退 WARN + init_schema 失败 fail-fast 或健康含表存在性）。
2. 启动序列：`initialize + init_schema` 后置表存在性断言；失败日志含具体异常。
3. `init_schema` 幂等补齐 `attributes_json` 等演进列（PG/SQLite 两分支已具备）。
4. 编排显式注入 `DATABASE_URL` 与端口 env。

**验收标准**：受管启动后 schema 表 > 20（含 profile/attributes_json）；calc/get/PUT 200；数据库不可写时启动明确 ERROR；重启数据保留。

**验证方法**：编排 stop/start 后冒烟 S4；表清单脚本核对；重启存活用例。

**实施与验证结果（v1.2.0）**：✅ 已实施（OpenBase commit 0499838）：编排注入共享 POSTGRES_URL + SQLITE_FALLBACK=false + 探活 /health/liveness；共享库 platform schema 27 表实证（DPS PID 9528 健康）。

### P2 端口与地址收敛（三处一致）

**现状**：DPS `config.api_port` 默认 8000；`settings.dps_upstream_base` 默认 8000（编排 env 覆盖 8030）；`PROXY_SYSTEMS["dps"]` 曾硬编码 8030（已修）。

**目标**：端口单一事实源：代码默认 8000、受管部署 8030（编排约定），消除双地址。

**涉及文件**：OpenBase `openbase/modules/proxy/__init__.py`、`openbase/settings.py`、`scripts/service-orchestrator.ps1`；冒烟 `smoke.env`。

**实现要点**：
1. `PROXY_SYSTEMS["dps"]["base_url"]` 引用 `settings.dps_upstream_base`（去掉硬编码）。
2. 编排 health 探活统一 `/health/liveness`。
3. DPS `API_PORT=8030` 部署 env 显式（源码默认 8000 不动）。

**验收标准**：三处同值；`GET /api/v1/dps-proxy/health` 200。

**验证方法**：grep 8030/8000 引用核对；起服探活。

**实施与验证结果（v1.2.0）**：✅ 已实施（OpenBase commit aae1de7）：PROXY_SYSTEMS['dps'] 收敛 get_settings().dps_upstream_base；默认 8000 / 编排覆盖 8030 两态取值正确；test_settings+test_dps_proxy 27 passed。

### P3 身份四头与映射键收敛（治理 Q2/Q3 落实施）

**现状**：dps-proxy 注入 X-User-ID（裸 sub）、X-Tenant-ID/X-Org-ID（同值 tenants.id）+ 映射表 + dps_default_*；DPS 侧 org/tenant 为 UUID 实体。治理决策：Q2 org 头退役兼容别名、tenant 为唯一租户键；Q3 对外租户键统一 tenants.code。

**目标**：签发/透传使用 tenants.code；映射表 code 键语义；X-User-Role 与 DPS RBAC 对齐；移除 id=1 硬绑依赖。

**涉及文件**：OpenBase `openbase/modules/dps_proxy/__init__.py`、`openbase/modules/auth`（claims）、`openbase/settings.py`；DPS `src/rest_api/app.py`、`src/middleware/permission_middleware.py`、engines（organization/tenant manager）。

**实现要点**：
1. 签发增量 `tenant_code` claim（org_id 兼容保留）；dps-proxy 头链 code 优先、数值兜底。
2. DPS 去启动硬绑，角色绑定由显式种子写入；未绑定 fail-closed。
3. X-User-Role 与 DPS roles 表对齐；跨租户隔离冒烟。

**验收标准**：同一用户经 OpenBase 登录后 dps-proxy 返回其租户数据；映射表按 code 配置生效；伪造 X-User-ID=1 不再自动 super_admin。

**验证方法**：2 用户 2 租户用例；DPS/OpenBase 单测。

### P3.x 拆分与实施记录（v1.1.0~v1.3.0）

**拆分（v1.1.0）**：
- P3.1（OpenBase 单仓）：签发增量 `tenant_code` claim + dps-proxy 映射表 code 键（code 优先、数值兜底，OpenMemory/llm_proxy 消费的 org_id 不受影响）。
- P3.2（DPS）：去启动硬绑 X-User-ID=1→super_admin；与 P7 绑定种子同批。
- P3.3（跨仓）：全量对外租户键切 code = 治理 P1-2/P1-3 立项范围。

**P3.1 已实施（v1.2.0，OpenBase commit 1074751）**：auth 新增 `_resolve_tenant_code`（tenants.id→code，失败 WARN 不阻断）；login/refresh/oidc 增量写 `tenant_code`；dps_proxy `_build_identity_headers` 头链 `tenant_code → user.tenant_id → jwt.org_id → dps_default_*`，X-Org-ID 在 code 存在时同形。验证：三态断言 + test_settings/test_dps_proxy/test_gateway/test_auth* 50 passed。残余：OIDC bound 依赖 DB；dps_tenant_map/dps_org_map code 键部署值待联调写入。

**P3.2 已实施核对（v1.3.0）**：DPS v2.8.1 已移除 "X-User-ID=1→super_admin" 启动硬绑（rest_api/app.py L137-139、main.py L179 仅注释，全仓 grep 无残留绑定代码）。角色绑定改由显式种子写入（seed-shared-infra.py DEFAULT_USER_BINDINGS="1:super_admin"，env DPS_DEMO_USER_ROLES 可覆盖）；未绑定用户 fail-closed 403 语义待冒烟 S4 实证。与 P7 同批完成。

### P4 端点面契约对齐与补齐

**现状**：dps-proxy 现暴露 10 端点映射 DPS /api/v2；DPS 侧更多 v2 能力未开放；/api/v1 写恒 403（文档化）；OpenLLM ProfileAdapter 真实模式依赖 /profile/v1 读语义需与 v2 端口面对齐（待复核废弃 stub 契约）。

**目标**：对外端点面 = 前端/OpenLLM 最小集 + 契约一致（错误 envelope、分页、body 透传）。

**涉及文件**：OpenBase `openbase/modules/dps_proxy/__init__.py`；DPS `src/rest_api/routes/routes_profiles.py`；立项方案 §7.4。

**实现要点**：端点-契约对照表；profile 读映射（OPENLLM_DPS_REAL get 语义）；/api/v1 写下线或明确 403 契约；错误 envelope 映射。

**验收标准**：开放端点逐一 200 且字段契约一致；profile 读映射端到端。

**验证方法**：冒烟 S4-5 契约对照；OpenLLM profile 用例。

### P5 画像数据模型与写链

**现状**：attributes_json 双后端与 PUT 持久化已实现（Phase C）；写链历史缺陷（storage_engine 落库 + annotation/version/track 联动疑死代码，routes_profiles.py L359 注释）待复核；/api/v1 PUT 恒 403。

**目标**：PUT 更新 → profile 行 + version/history 记录 + 缓存失效 + 行级审计。

**涉及文件**：DPS `src/engines/portrait/crud.py`、`portrait_engine.py`、`storage_engine.py`、`version_manager.py`、`src/rest_api/routes/routes_profiles.py`。

**实现要点**：PUT 后写 profile_history 并递增 version（幂等快照）；缓存失效核对；死代码修复或显式登记废弃；audit 落 UPDATE（owner 来自 contextvar）。

**验收标准**：PUT→GET 新值；profile_history 快照行 + version 递增；缓存即时失效；audit 可见。

**验证方法**：PUT→GET→重启→GET；查表；冒烟 S4-2/S4-4。

### P6 可用性与降级治理

**现状**：dps-proxy 探活 fail-open（仅 WARN）；DPS DB 故障与权限引擎未初始化两处 fail-open 未治理（P2-2）。

**目标**：DPS 不可用时有明确降级提示且不拖垮 OpenBase；恢复自动跟随。

**涉及文件**：OpenBase `openbase/modules/dps_proxy/__init__.py`；DPS middleware、health_check_engine。

**实现要点**：连续失败 N 次降级提示；DPS fail-open 默认 fail-closed 或显式 FAIL_OPEN env；健康含表存在性维度。

**验收标准**：停 DPS → 明确降级响应；恢复自动正常。

**验证方法**：编排停 DPS 复测（人工场景）。

### P7 种子与演示数据预置

**现状（v1.0.0 基线）**：seed_demo.py 为 SQLite 专用；dps_org_map/dps_tenant_map 无对应数据；启动硬绑 user=1。

**目标**：一键幂等预置演示租户/组织/画像样本 + 角色绑定，demo 登录后 dps-proxy 全链路可用。

**涉及文件**：DPS `scripts/seed-shared-infra.py`（PG 幂等种子，已存在）；OpenBase 编排（可选集成）。

**实现要点**：
1. 种子幂等：org/tenant（固定 UUID + ON CONFLICT）、roles（org_admin/user）、user_roles 绑定（默认 1:super_admin，env 覆盖）、画像样本 3 条（person_id 命名 `{tenant_code}_{user_ref}_NN` 对齐 external 语义）。
2. 编排启动后可选执行种子。

**验收标准**：新环境一键种子后 demo 登录 dps-proxy 返回样本；重复执行不产生重复行；无硬绑 user=1 也能按绑定角色操作。

**验证方法**：清库 → 起服+种子 → 冒烟 S4；重复执行核对。

**实施与验证结果（v1.3.0）**：✅ 已实施（实跑验证）：seed-shared-infra.py 共享 PG 幂等实跑 org=1/tenant=1/roles=6/user_roles=1（1:super_admin）/profile=3；重跑 0 新增。编排一键集成（启动后自动种子）可选登记。

### P8 文档与契约沉淀

**现状**：无 OpenBase-DPS 对接说明文档。

**目标**：产出《OpenBase-DPS 对接使用指南 v1.0.0》（端点清单、身份头、错误 envelope、种子、联调、端口约定）。

**涉及文件**：OpenBase 文档目录（新建）；本任务书修订历史。

**实现要点**：参照 OpenMemory 指南体例；与治理/立项文档交叉引用。

**验收标准**：文档可指导新会话独立完成 P9 冒烟。

**验证方法**：按文档执行冒烟 S4。

### P9 验收与冒烟扩展

**现状**：冒烟 S4 组已定义；真实 PG 下未全绿；回归基线已具备。

**目标**：冒烟 S4 全绿 + 回归套件通过（门禁）。

**涉及文件**：冒烟清单 v1.1.0（S4 组）与 smoke_runner.py。

**实现要点**：S4 扩展（重启存活、双租户隔离、version/history、停服降级、漂移重算 P1）；回归命令固化。

**验收标准**：冒烟 S4 全 PASS（P1 级登记不阻塞）；三条回归 0 失败。

**验证方法**：按清单执行并回填记录。

## 4. 实施顺序与依赖

| 顺序 | 项 | 依赖 | 状态 |
|:---:|-----|------|------|
| 1 | P1 运行数据源与 Schema 闭环 | 共享 PG | ✅ 已实施（0499838） |
| 2 | P2 端口地址收敛 | 无 | ✅ 已实施（aae1de7） |
| 3 | P6 可用性降级 | P1 | 待办 |
| 4 | P3 身份四头与映射收敛 | P1、P2 | 🔶 P3.1（1074751）/P3.2（v2.8.1 核对）已实施；P3.3=治理 P1-2/P1-3 待立项 |
| 5 | P7 种子与演示数据 | P3 | ✅ 已实施（v1.3.0 实跑验证） |
| 6 | P5 画像数据模型与写链 | P1、P3 | 待办 |
| 7 | P4 端点面契约对齐 | P5 | 待办 |
| 8 | P8 文档 | P1~P7 定稿 | 待办 |
| 9 | P9 验收与冒烟 | P1~P8 | 待办（门禁） |

建议分组：A 批=P1/P2/P6；B 批=P3/P7（已完）；C 批=P5/P4；D 批=P8/P9。

## 5. 全量回归验证清单

| 命令 | 预期 |
|------|------|
| DPS：`python -m pytest src/tests -q`（受影响子集先行） | 0 失败（沙箱写限制用例按真实环境处理） |
| OpenBase：`python -m pytest tests -q` | 0 失败（含 dps-proxy/settings/gateway/auth 子集） |
| OpenLLM：profile/writeback 相关子集（DPS_REAL=true 用例） | 0 失败 |
| 编排：service-orchestrator.ps1 start | 五服务健康；DPS 表存在性断言通过 |
| 冒烟 S4 组（清单 v1.1.0） | 全部 PASS（P1 级登记项除外） |

联调场景：demo 登录 → dps-proxy calc 200 → PUT → GET 新值 → 重启 → 复读 → 跨租户隔离 → audit 可见。

## 6. 风险与注意事项

- **沙箱写限制（环境）**：沙箱禁止写 DPS dps.db 等文件；真实环境/放行规则可复验（P1 已用共享 PG 规避）。
- **PG 方言**：database.py::_pg_translate 已落地（qmark→$n）；PG 冷路径写链待 P5 在真实 PG 验证。
- **权限默认开启**：PERMISSION_ENABLED 默认 true；硬绑已移除，绑定由种子显式写入（P3.2/P7 完成）；未绑定 fail-closed 待冒烟实证。
- **/api/v1 写恒 403**：既有设计（文档化）；v2 为唯一写面。
- **写链死代码判定需复核**：修复与废弃二选一并记录理由（P5）。
- **文档单一事实源**：本任务书为 OpenBase-DPS 侧唯一执行依据；每项完成后回填状态表并同步修订历史。本文件曾在编辑期遭外部进程回滚，v1.3.0 起以整文件重建为准。

### 状态追踪表

| 项 | 状态 | 验证日期 | 备注 |
|:---:|------|:---:|------|
| P1 运行数据源与 Schema 闭环 | ✅ 已实施 | 2026-09-05 | 编排强制共享 PG（0499838）；platform schema 27 表实证 |
| P2 端口地址收敛 | ✅ 已实施 | 2026-09-05 | PROXY_SYSTEMS['dps'] 同源 settings.dps_upstream_base（aae1de7） |
| P3 身份四头与映射收敛 | ✅ P3.1/P3.2 已实施 | 2026-09-05 | P3.1（1074751）；P3.2 DPS v2.8.1 无硬绑残留；P3.3=治理 P1-2/P1-3 待立项 |
| P4 端点面契约对齐 | 待办 | - | 含 /profile/v1 读映射决策 |
| P5 画像数据模型与写链 | 待办 | - | version/history 复核 |
| P6 可用性降级 | 待办 | - | fail-open 治理 |
| P7 种子与演示数据 | ✅ 已实施 | 2026-09-05 | seed-shared-infra.py 幂等实跑：org/tenant 各1、roles 6、user_roles 1、profile 3；重跑 0 新增 |
| P8 文档与契约沉淀 | 待办 | - | 对接使用指南 v1.0.0 |
| P9 验收与冒烟扩展 | 待办 | - | 门禁 |

**遗留事项**：P3.3（对外租户键全量 code 化）随治理 P1-2/P1-3 立项；P5/P6/P4/P8/P9 待办；冒烟 S4 全绿与真实联调（含未绑定 fail-closed 实证、dps_tenant_map code 键部署值）待执行。

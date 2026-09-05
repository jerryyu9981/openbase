# OpenBase-DPS对接完善任务书-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-DPS-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Draft] |
| 日期 | 2026-09-05 |
| 作者 | AD（跨项目分析） |
| 版本主题 | OpenBase 与 DPS 对接全量清理：运行形态、端点契约、身份映射、数据模型、可用性、文档与验收 |
| 适用范围 | OpenBase（8000，dps-proxy 模块）与 DPS（src/rest_api v2，默认 8000；编排 8030），由独立会话据此实施 |

> 本任务书供另一个会话专据此完善 OpenBase 与 DPS 的对接。所有修改项均含现状、目标、涉及文件、实现要点、验收标准与验证方法，可直接照单执行。事实锚点基于 2026-09-04 真实验证与两仓库代码核对；凡标注"需复核"处为执行前须在目标环境再确认的开放项。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-05 | AD（跨项目分析） | 初始版本：OpenBase-DPS 对接现状盘点（表 2）与待完善项 P1~P9 详细方案、实施顺序、回归清单、风险登记 |

---

## 1. 背景与目标

OpenBase 以 JWT 门禁 + 专属 proxy 聚合下游，DPS（数据画像系统）经 `/api/v1/dps-proxy` 暴露给统一前端。已完成：R-381 dps-proxy 主体（画像列表/详情/计算/更新、标签、报表、批量、审计、健康透传）、P0-3 端口与惰性探活、Phase C 画像持久化演进（`attributes_json` + `PUT /api/v2/portrait/{person_id}`）、健康检查白名单。真实验证（2026-09-04 冒烟 S4）暴露：DPS 运行态 500（calc/get/PUT）、空库、沙箱写限制、PG 方言与身份映射待收敛。本任务书把 OpenBase↔DPS 对接按"生产可用"标准清理一遍，形成可执行清单。

目标态：五件套统一出口下，前端（portrait 页）与 OpenLLM（画像读/写回调，`OPENLLM_DPS_REAL`）均经 dps-proxy 获得一致、持久、按租户隔离、可观测的画像能力；DPS 数据源与 Schema 初始化闭环；身份键全链路同形；写链真实可用；冒烟全绿。

## 2. 对接现状总览

| 类别 | 状态 | 说明 |
|------|:---:|------|
| dps-proxy 网关入口与端点面 | ✅ 已完成 | prefix /api/v1/dps-proxy；GET /portraits、GET /portraits/{pid}、POST /portraits/calculate、PUT /portraits/{pid}、GET/POST /tags/categories、PUT/DELETE /tags/categories/{id}、GET /reports/overview、GET /batch/tasks/{id}、GET /audit/logs、GET /health（上游 /health/liveness） |
| 身份头注入与映射表 | ⚠️ 部分 | 四头 X-User-ID / X-Tenant-ID / X-Org-ID / X-User-Role 注入 + dps_org_map / dps_tenant_map 值转换 + dps_default_* 兜底；但租户键形态（tenants.id 数字 vs tenants.code）与映射表语义错位（治理 Q3 已决策切 code，未实施） |
| DPS 运行形态与数据源 | ❌ 未闭环 | 编排以 rest_api.app（8030）启动；默认 database_url 指向本地 localhost:5432/dps_db（不可达）→ 静默回退 SQLite ./dps.db；沙箱写限制下 init_schema 抛 disk I/O error → 0 张表 → 画像请求 500（2026-09-04 实证） |
| PG 方言适配 | ⚠️ 部分 | database.py 已加 _pg_translate（qmark→$n，2026-09-04）；真实 PG 联调未执行；PG 冷路径（占位符之外的存储写链）待验证 |
| 画像读写契约 | ⚠️ 部分 | 读：v2 portrait/list、get、calculate 已代理且真实可用（SQLite 可跑时）；写：PUT /api/v2/portrait/{person_id} 已实现持久化（attributes_json 幂等演进）；写链历史缺陷（storage_engine / annotation / version / track 疑似死代码，需复核）未修复；/api/v1 写恒 403（已文档化） |
| 健康与可用性 | ✅ 部分 | dps_upstream_base 默认 8000 + dps_health_check_enabled/interval + 惰性探活（fail-open 仅 WARN）；但 PROXY_SYSTEMS["dps"] 通用通道仍默认 8030（需复核统一）；DPS DB 故障 fail-open 与权限引擎未初始化 fail-open 两处未治理 |
| 数据与种子 | ❌ 缺失 | seed_demo 组织/租户/画像样本与 OpenBase 演示登录的绑定关系未形成一键预置；DPS 启动硬绑 X-User-ID=1 为 super_admin（治理 R3 遗留） |
| 冒烟与回归 | ⚠️ 部分 | 冒烟清单 S4 组（calc/get/PUT/重启存活/四头归属/降级）已定义；真实 PG 或可写库下未全绿；自动化回归（DPS pytest 子集 + OpenBase 26 passed + OpenLLM profile 用例）已具备基线 |
| 文档 | ⚠️ 缺失 | OpenBase-DPS 对接说明（端点清单/身份头/错误 envelope/种子/联调方法）未成文 |

## 3. 待完善项详细方案

### P1 DPS 运行数据源与 Schema 初始化闭环

**现状**：DPS 以 rest_api.app（8030）运行，无有效 PG 配置时静默回退 SQLite `./dps.db`（cwd 相对）；沙箱写限制下建表抛 `sqlite3.OperationalError: disk I/O error`，库 0 张表，画像请求全部 500；`/health` 不依赖表故服务显示"健康"（2026-09-04 实证）。

**目标**：DPS 在任何受管环境启动即获得可用 Schema；数据源选择显式化，杜绝"看似健康实则空库"。

**涉及文件**：DPS `src/config.py`、`src/database.py`、`src/rest_api/app.py`；OpenBase `scripts/service-orchestrator.ps1`；共享基础设施 `.env.shared-infra`。

**实现要点**：
1. 确定受管数据源二选一并写入部署配置：A. 共享 PG（192.168.0.151，新建 dps_db 库 + platform schema，`DATABASE_URL` 显式配置、`SQLITE_FALLBACK=false`）；B. 本地可写 SQLite（放行目录写权限，`SQLITE_FALLBACK=true` 显式）。禁止"默认值不可达→静默回退"路径：回退必须 WARN 且随后 init_schema 失败时启动 fail-fast（或健康检查含表存在性探测）。
2. 启动序列核对：`rest_api/app.py`（约 L232-235）`initialize + init_schema` 后置表存在性断言；失败日志含具体异常并阻断/标记 degraded。
3. `init_schema` 幂等补齐 `attributes_json` 等演进列（已有 PG/SQLite 两分支，复核 SQLite 分支 PRAGMA 探测在空库+写限制下可诊断）。
4. 编排脚本为 DPS 显式注入 `DATABASE_URL`（与共享基础设施一致）与端口 env，去掉对本地默认的依赖。

**验收标准**：
- 受管启动后 `SELECT count(*) FROM sqlite_master WHERE type='table'`（或 PG information_schema）> 20，含 profile/attributes_json 列。
- calc/get/PUT 返回 200（非 500）。
- 数据库不可写时启动日志出现明确 ERROR（含 disk I/O error 原由），健康探针可暴露 degraded。
- 重启后数据保留（写一行 → 重启 → 读到）。

**验证方法**：编排 stop/start 后执行冒烟 S4 组；`t_dbcheck` 式脚本核对表清单；重启存活用例。

### P2 端口与地址收敛（三处一致）

**现状**：DPS 源码 `config.api_port` 默认 8000；OpenBase `settings.dps_upstream_base` 默认 8000（P0-3 已改，编排 ps1 覆盖 8030）；`PROXY_SYSTEMS["dps"]`（modules/proxy/__init__.py L37）通用通道仍写 8030；冒烟脚本另按 8030 配置。

**目标**：端口单一事实源：受管部署统一为 8030（编排约定），代码默认与文档同步标注；消除通用 proxy 通道与 dps-proxy 双地址。

**涉及文件**：OpenBase `openbase/settings.py`、`openbase/modules/proxy/__init__.py`、`scripts/service-orchestrator.ps1`；冒烟 `smoke.env`。

**实现要点**：
1. `PROXY_SYSTEMS["dps"]["base_url"]` 改为引用 `settings.dps_upstream_base` 或显式 env（去掉硬编码 8030）。
2. 编排 ps1 注释与 health 探活路径统一为 `/health/liveness`（dps-proxy 透传目标已一致）。
3. DPS `API_PORT` 在部署 env 显式设置 8030，源码默认保持 8000 不动（文档注明本地直连 8000 / 编排 8030）。

**验收标准**：三处地址同值（`dps_upstream_base`、`PROXY_SYSTEMS["dps"]`、编排启动端口）；`GET /api/v1/dps-proxy/health` 200。

**验证方法**：grep 全仓 8030/8000 引用清单核对；编排起服后探活。

### P3 身份四头与映射键收敛（治理 Q2/Q3 落实施）

**现状**：dps-proxy 注入 `X-User-ID`（裸 sub，数字 id）、`X-Tenant-ID` / `X-Org-ID`（同值签发 tenants.id）+ `dps_org_map/dps_tenant_map` 值转换 + `dps_default_*` 兜底；DPS 侧 org/tenant 为 UUID 库实体、启动硬绑 X-User-ID=1 为 super_admin。治理决策：Q2 不拆分 org、tenant 为唯一租户键、org 头退役兼容别名；Q3 对外租户键统一 tenants.code。

**目标**：OpenBase 签发与 dps-proxy 透传使用 tenants.code 作租户键；dps_org_map/dps_tenant_map 语义修正或停用；X-User-Role 与 DPS RBAC 绑定一致；移除对"id=1 硬绑"的依赖。

**涉及文件**：OpenBase `openbase/modules/dps_proxy/__init__.py`、`openbase/modules/auth`（签发 claims）、`openbase/settings.py`；DPS `src/rest_api/app.py`（启动绑定）、`src/middleware/permission_middleware.py`、`src/engines/organization_manager.py`、`src/engines/tenant_manager.py`。

**实现要点**：
1. 签发处 `X-Tenant-ID`/`X-Org-ID` 携带 tenants.code；dps-proxy `_apply_map` 键按 code 语义；存量数字 id 兼容仅限过渡（WARN 日志）。
2. DPS 绑定：去掉仅按 X-User-ID=1 的启动硬绑，改为按 `(org/tenant code + user 标识)` 从绑定表/种子解析角色；OpenBase 登录/demo 种子负责写绑定。
3. 明确 X-User-Role 取值集合与 DPS `roles` 表对齐（super_admin/org_admin/user），缺省 fail-closed 语义评审（当前未知 org 403、缺头 401 保留）。
4. OpenLLM 侧 external person_id（治理 P0-2 已支持 X-Proxy-Source 解析）与 DPS person_id 语义核对：画像写回按 tenant 隔离落点一致。

**验收标准**：
- 同一用户经 OpenBase 登录后 dps-proxy calc/get 返回其租户数据；跨租户互不可见。
- 映射表按 code 配置生效（不再永不命中）；未映射值走 dps_default_* 且可审计。
- 伪造 X-User-ID=1 不再自动获得 super_admin（须带角色绑定）。

**验证方法**：构造 2 用户 2 租户用例（沿用冒烟 S6 跨链路思路）；DPS/OpenBase 单测补充。

### P4 端点面契约对齐与补齐

**现状**：dps-proxy 现暴露 10 端点，映射 DPS `/api/v2`；DPS routes_profiles 等文件含更多 v2 能力（risk-assess、annotate、version、compare、trend、associate、labels、generate、statistics、track、ai/analyze 等）未在 proxy 开放；`/api/v1` 写恒 403（已文档化）；OpenLLM ProfileAdapter 真实模式依赖 `/profile/v1` 读语义，与 DPS v2 端口面不一致（需复核是否废弃 stub 契约）。

**目标**：明确 dps-proxy 对外端点面 = 前端/OpenLLM 所需最小集 + 契约一致性（错误 envelope、分页、body 透传）。

**涉及文件**：OpenBase `openbase/modules/dps_proxy/__init__.py`；DPS `src/rest_api/app.py`、`src/rest_api/routes/routes_profiles.py`；立项文档《真实契约落地与沉淀收敛立项方案》§7.4。

**实现要点**：
1. 核对每个 proxy 端点与 DPS v2 端点的请求/响应契约（分页参数、envelope 字段），输出端点-契约对照表（P8 文档化）。
2. 决策并实施：a) 画像详情/计算供 OpenLLM profile 读映射（`OPENLLM_DPS_REAL` 的 get 语义）；b) `/api/v1` 写端点正式下线或明确恒 403 契约；c) 风险画像/标注等能力是否开放由前端规划决定（默认不开，登记即可）。
3. DPS 错误 envelope 与 OpenBase 网关 envelope 转换核对（现 `_forward` 透传非网关结构如 /health；画像错误码需映射为可读 message）。

**验收标准**：开放端点逐一 200 且字段契约一致；不开放能力有明确 404/403 与文档；profile 读映射端到端（OpenLLM real 模式 → proxy → v2 → 返回画像段）。

**验证方法**：冒烟 S4 扩展（S4-5 契约对照）、OpenLLM profile 用例（`OPENLLM_DPS_REAL=true`）。

### P5 画像数据模型与写链

**现状**：`attributes_json` 双后端演进已实现；PUT 白名单/scores 映射/contextvar 归属/缓存失效已实现（Phase C）；但 DPS 历史写链（storage_engine 落库 + annotation/version/track 联动）疑为死代码（routes_profiles.py 注释 L359），画像写后 version/history 是否真实记录需复核；`/api/v1` PUT 恒 403。

**目标**：画像写链真实、一致、可追踪：PUT 更新 → profile 行 + version/history 记录 + 缓存失效。

**涉及文件**：DPS `src/engines/portrait/crud.py`、`src/engines/portrait_engine.py`、`src/engines/storage_engine.py`、`src/engines/version_manager.py`、`src/rest_api/routes/routes_profiles.py`（PUT 处理）。

**实现要点**：
1. 复核 PUT 处理器：attributes_json 更新后是否写入 `profile_history` 并递增 version；缺则补（幂等、快照）。
2. 复核 cache 失效键（person/org/tenant 维度）与读路径一致。
3. 写链死代码（annotation/version/track 引擎的独立落库入口）修复或显式登记废弃（二选一，需记录理由）。
4. profile 行级审计（audit/logs）落一条 UPDATE 记录（owner 来自 contextvar）。

**验收标准**：PUT 后 GET 返回新 attributes；`profile_history` 新增快照行且 version 递增；缓存立即失效；audit/logs 可见该次更新（带身份头）。

**验证方法**：真实环境 PUT→GET→重启→GET；PG/SQLite 直接查表；冒烟 S4-2/S4-4。

### P6 可用性与降级治理

**现状**：dps-proxy 健康探活 fail-open（仅 WARN）；DPS 侧 DB 故障 fail-open 与权限引擎未初始化 fail-open（治理 R5 登记，P2-2）；探活间隔 30s；前端 portrait 页对 500 的提示依赖通用错误码。

**目标**：DPS 不可用时上游可视化降级提示且不拖垮 OpenBase；恢复自动跟随探活。

**涉及文件**：OpenBase `openbase/modules/dps_proxy/__init__.py`（探活节流/状态缓存）；DPS `src/middleware/`、`src/engines/health_check_engine.py`。

**实现要点**：
1. dps-proxy 维护"最近探活状态"，连续失败 N 次后在响应/日志给出明确降级提示（仍 fail-open 转发，保持与前端约定）。
2. DPS 两处 fail-open（DB 故障、权限引擎未初始化）决策：默认 fail-closed（403/503）或显式配置 `FAIL_OPEN` env（登记到部署基线）。
3. 健康检查增加表存在性/初始化状态维度（联动 P1）。

**验收标准**：停 DPS → dps-proxy 请求返回明确降级（503 或 envelope degraded 提示），OpenBase 其余通道不受影响；恢复后自动正常。

**验证方法**：编排停 DPS 单服务复测（人工场景，登记冒烟 S5-6 风格）。

### P7 种子与演示数据预置

**现状**：DPS seed_demo.py 存在但未与 OpenBase demo 登录/共享租户 code 对齐；dps_org_map/dps_tenant_map 若按 code 配置现无对应数据；启动硬绑 user=1。

**目标**：一键预置演示租户/组织/画像样本 + 角色绑定，使 OpenBase 演示账号（admin 等）登录后 dps-proxy 全链路可用。

**涉及文件**：DPS `src/seed_demo.py`、`src/rest_api/app.py`；OpenBase `scripts/`（演示种子）；共享 `.env.shared-infra`。

**实现要点**：
1. 种子脚本幂等：org（code 对齐租户 code）、tenant、super_admin/org_admin 绑定、2~3 个画像样本（attributes_json 样例）。
2. OpenBase 演示用户（users 表 admin 等）与 DPS 绑定表通过（X-User-ID 语义）关联；明确 person_id 命名（建议 `{tenant_code}_{user_ref}`，与治理 P0-2 external 一致，需复核）。
3. 编排启动后可选执行种子（幂等）。

**验收标准**：新环境一键种子后，demo 登录 → dps-proxy /portraits 返回样本；PUT 后可读回；无硬绑 user=1 也能按绑定角色操作。

**验证方法**：清库 → 编排起服+种子 → 冒烟 S4 全绿；重复执行种子不产生重复行。

### P8 文档与契约沉淀

**现状**：无 OpenBase-DPS 对接说明文档。

**目标**：产出《OpenBase-DPS 对接使用指南 v1.0.0》（端点清单、身份头、错误 envelope、种子、联调方法、端口约定），并纳入版本管理。

**涉及文件**：OpenBase 文档目录（新建）；本任务书修订历史。

**实现要点**：
1. 文档结构参照 OpenMemory 指南体例：入口与身份、端点-契约对照表、错误码、降级语义、种子、冒烟方法、修订历史。
2. 与治理/立项文档交叉引用（R3~R5 决策、Phase C 契约）。

**验收标准**：文档可指导新会话独立完成 P9 冒烟；端点-契约对照与代码一致。

**验证方法**：按文档执行一遍冒烟 S4。

### P9 验收与冒烟扩展

**现状**：冒烟清单 S4 组已定义；真实可写库下未全绿；回归基线（DPS pytest 子集 / OpenBase 26 / OpenLLM profile）已具备。

**目标**：冒烟 S4 组全绿 + 回归套件通过，作为本任务书验收门禁。

**涉及文件**：冒烟清单《真实联调冒烟清单》v1.1.0（S4 组）与 smoke_runner.py。

**实现要点**：
1. S4 扩展用例：P1 重启存活、P3 双租户隔离、P5 version/history、P6 停服降级、S4-4 漂移重算（P1 级）。
2. 回归命令固化：DPS `python -m pytest src/tests -q`（或受影响子集）、OpenBase `python -m pytest tests -q`、OpenLLM profile/writeback 相关子集。

**验收标准**：冒烟 S4 全部 PASS（P1 级项登记不阻塞）；三条回归命令 0 失败。

**验证方法**：按清单执行并回填执行记录。

## 4. 实施顺序与依赖

| 顺序 | 项 | 依赖 | 说明 |
|:---:|-----|------|------|
| 1 | P1 运行数据源与 Schema 闭环 | 环境写权限或 PG 决策 | 前置阻塞项；无可用库其余项无法真实验证 |
| 2 | P2 端口地址收敛 | 无 | 快赢，配置级 |
| 3 | P6 可用性降级 | P1 | 依赖健康状态语义 |
| 4 | P3 身份四头与映射收敛 | P1、P2 | 治理 Q2/Q3 落地；依赖真实多租户库 |
| 5 | P7 种子与演示数据 | P3 | 依赖租户键语义定案 |
| 6 | P5 画像数据模型与写链 | P1、P3 | 依赖可写库与身份归属 |
| 7 | P4 端点面契约对齐 | P5 | 依赖写链确认后开放面才稳定 |
| 8 | P8 文档 | P1~P7 方案定稿 | 可随实施并行起草，验收前定稿 |
| 9 | P9 验收与冒烟 | P1~P8 | 门禁 |

建议分组：A 批=P1/P2/P6（部署基线）；B 批=P3/P7；C 批=P5/P4；D 批=P8/P9。每批完成后跑对应回归再进入下一批。

## 5. 全量回归验证清单

修改完成后执行：

| 命令 | 预期 |
|------|------|
| DPS：`python -m pytest src/tests -q`（受影响子集先行） | 0 失败（沙箱写限制用例按真实环境处理） |
| OpenBase：`python -m pytest tests -q` | 0 失败（含 dps-proxy 26 基线） |
| OpenLLM：profile/writeback 相关子集（DPS_REAL=true 用例） | 0 失败 |
| 编排：service-orchestrator.ps1 start | 五服务健康；DPS 表存在性断言通过 |
| 冒烟 S4 组（清单 v1.1.0） | 全部 PASS（P1 级登记项除外） |

联调场景：demo 登录 → dps-proxy calc 200 → PUT → GET 新值 → 重启 → 复读 → 跨租户隔离 → audit 可见。

## 6. 风险与注意事项

- **沙箱写限制（环境）**：本会话沙箱禁止写 DPS `dps.db` 等文件（disk I/O error），自动化验证受限；真实环境或放行规则后可复验（P1 前置）。
- **PG 方言**：`database.py::_pg_translate`（qmark→$n，含引号/JSON 运算符保护）已落地，PG 部署必需；PG 冷路径其余部分（写链）需在真实 PG 联调中验证。
- **权限默认开启 + 硬绑**：PERMISSION_ENABLED 默认 true；X-User-ID=1 硬绑 super_admin 属治理 R3 遗留，P3 必须处理，防止伪造提权。
- **/api/v1 写恒 403**：为既有设计（文档化），勿误判为缺陷；v2 为唯一写面。
- **写链死代码判定需复核**：storage_engine/annotation/version/track 的独立落库入口在实施时以实际代码复核为准，修复与废弃二选一并记录理由。
- **端口双通道**：dps-proxy（专属）与 PROXY_SYSTEMS["dps"]（通用）并存，P2 统一前勿在两处改不同地址。
- **文档单一事实源**：本任务书为 OpenBase-DPS 侧对接完善的唯一执行依据；每项完成后回填"状态追踪表"并同步修订历史（版本管理规范）。

### 状态追踪表

| 项 | 状态 | 验证日期 | 备注 |
|:---:|------|:---:|------|
| P1 运行数据源与 Schema 闭环 | 待办 | - | 环境写权限或共享 PG 决策前置 |
| P2 端口地址收敛 | 待办 | - | 配置级快赢 |
| P3 身份四头与映射收敛 | 待办 | - | 治理 Q2/Q3 落地 |
| P4 端点面契约对齐 | 待办 | - | 含 /profile/v1 读映射决策 |
| P5 画像数据模型与写链 | 待办 | - | version/history 复核 |
| P6 可用性降级 | 待办 | - | fail-open 治理 |
| P7 种子与演示数据 | 待办 | - | 一键幂等预置 |
| P8 文档与契约沉淀 | 待办 | - | 对接使用指南 v1.0.0 |
| P9 验收与冒烟扩展 | 待办 | - | 门禁 |

**遗留事项**：真实 PG（共享基础设施）联调与写链复核需在可写环境中执行；P0-3 探活与 P2-2 fail-open 治理跨治理路线图联动（治理文档 v1.5.0 §8/§9.2 L-1）。

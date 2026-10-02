# OpenBase 部署执行与上线检查报告 - v1.4.10

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **本仓**（`openbase` 后端 ＋ `openbase-ui` 前端） |
| 版本号 | **v1.4.10**（承接型小版本「DPS 模板化能力对接深化」） |
| 文档 | 部署执行报告 ＋ 上线检查报告（Step 5 产出 5／7） |
| 文档版本 | v1.0.0 |
| 状态 | **[Released]（Dev 环境部署 ＋ 上线验证通过；tag `v1.4.10` 已推送 origin＋backup＋github 三远程）** |
| 部署日期 | 2026-10-02 |
| 目标环境 | **Dev**（Test/Pro 未涉及） |
| 发布负责人 | DO-OpenBase-Dev（部署）／AU-OpenBase-Dev（审计） |
| 上游依据 | 《OpenBase-发布入场检查记录与发布计划-v1.4.10》v1.0.0；《OpenBase-回滚方案与运维手册-v1.4.10》v1.0.0；《OpenBase-测试报告-v1.4.10》v2.0.0 |

## 0. 结论摘要

| 环节 | 结论 |
|------|:----:|
| 5.1 版本与制品确认 | ✅ 通过（`main` @ `c2c06b1`；工作区洁净；前端制品重建 **4m22s**） |
| 5.2 环境与配置核验 | ✅ 通过（`/health` 200；`/openapi.json` 144 路径；**无 DB 迁移**） |
| 5.3 缓存与消息运维 | ✅ 通过（**不适用**：本版无缓存/消息层变更） |
| 5.4 部署执行（Dev） | ✅ 通过（`Application startup complete`；日志 `version=c2c06b1` 命中发布提交） |
| 5.5 上线验证 | ✅ 通过（**11 项**：存活/契约/鉴权 fail-closed/降级保真）；**真实上游联调受环境阻断**（见 §6，如实登记） |
| 5.6 监控 / 日志 / 告警 | ✅ 通过（**结构化 JSONL** 落盘）；告警**不适用（声明）** |
| 5.7 性能上线检查 | ✅ 通过（`/health` **P50 12.4 ms / P95 90.4 ms**；含 1 次冷态尖峰 3515 ms，已定位） |
| 5.7 安全上线检查 | ✅ 通过（无令牌/坏令牌均 **401**；响应与日志**零凭据**） |
| 5.8 回滚预案与核验 | ✅ 通过（路径 ①②③ 可用；④⑤⑥ 因无迁移/无开关声明不适用） |
| 5.9 运维移交 | ✅ 通过（运维手册 ＋ 联系人 ＋ 排障命令 ＋ SLO 建议） |
| **总判定** | **✅ 上线通过（Dev）**；**无阻塞性问题**；登记环境类 1 项、遗留与硬化项 4 项 |

## 1. 发布版本与制品确认（5.1）

| 项 | 值 |
|----|-----|
| 提交 | 本仓 `main` @ **`c2c06b1`**（**应用代码快照**，工作区洁净）→ 发布文档收口 **`2c45a32`**（＝tag 指向） |
| 回退目标 | `v1.4.9` = **`ca268f731b33ea04e30a5b7e6a7af2ca4cfbe686`** |
| Tag | **`v1.4.10`（annotated）** —— 三远程同对象 **`1f383c85d2aa1c959b793fb2831b2ce27587fabd`**；**应用代码面与 `c2c06b1` 逐字一致**（diff 为空） |
| 变更面 | `git diff --stat v1.4.9..HEAD -- openbase openbase-ui` → **24 files changed, 3859 insertions(+), 11 deletions(-)**（`dps_proxy/__init__.py` +508／`llm_proxy/__init__.py` +2−1／前端 DPS 页面·数据层·路由／测试） |
| 制品形态 | 后端：Python 源码（语法门禁 `python -m compileall`）；前端：静态制品 `openbase-ui/dist` |
| 前端构建 | `npm run build`（`vue-tsc --noEmit && vite build`）→ **✓ built in 4m 22s**；`dist/index.html` 475 B（2026-10-02 13:36:01）；证据 `doc/release/evidence/v1410/openbase-ui-build-20261002.txt` |
| Tag | **`v1.4.10`（annotated）** —— 已推送 origin＋backup＋github 三远程，**四处同 hash** |
| 版本号一致性 | `.devflow/project-config.json` → `version=1.4.10`／`lastRelease=v1.4.10`；`.devflow/state.json` → `currentPhase=v1_4_10_step_5_closed`；`devflow-plugin/devflow-config.json` **不存在 ⇒ 不适用** |

## 2. 部署执行（5.4）

| 项 | 内容 |
|----|------|
| 部署方式 | Dev **直接部署**（`cicd-pipeline-management`：Dev 直接部署；后端单进程 `uvicorn`，前端静态制品） |
| 后端执行命令 | `python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000 --log-level info`（cwd＝仓根） |
| 启动证据 | 结构化日志 `service.start`（`version=c2c06b1`、`env=dev`、`log_path=logs\openbase\openbase-20261002.jsonl`），随后 `/health` 与 `/openapi.json` 均 200 |
| 命中当前版本 | 日志 `version` 字段＝**`c2c06b1`**（＝发布提交）⇒ **实例加载的即发布提交** |
| DB 初始化 | `database init failed, fallback to memory: connection was closed in the middle of operation` ⇒ **按既有降级设计**回退内存演示用户（`fallback: memory demo user seeded`），服务不中断 |
| 前端部署 | 制品重建成功（§1）；Dev 亦可由 `npm run dev -- --strictPort`（127.0.0.1:5173）提供 |
| 部署产物（证据） | `doc/release/evidence/v1410/openbase-deploy-verify-20261002.json`（11 项上线验证）／`dps-proxy-integration-step5-20261002-052459.json`（上游口径与联调）／`openbase-ui-build-20261002.txt`／`openbase-health-latency-20261002.txt` |

## 3. 环境与配置核验（5.2）

| 项 | 实测 |
|----|------|
| 存活 | `GET /health` → **200** `{"status":"ok"}` |
| 契约面 | `GET /openapi.json` → **200**，`title=OpenBase`，`version=1.0.0`（框架版本），**`paths` 计数 144**，其中 `dps-proxy` **26** 条（覆盖 v1.4.10 的 10 契约新增 ＋ 12 补代理） |
| 上游 | **DPS v2.12.1 @ 127.0.0.1:8030**；`/health/liveness` → **200**、`version=2.12.1`；`/health/readiness` → **200 `degraded`**（`database=healthy(sqlite)`、`redis=degraded`） |
| 共享 PostgreSQL | `192.168.0.151:5432` **连接不稳定**（`asyncpg ConnectionDoesNotExistError`）⇒ 本仓走内存降级、DPS 走 `SQLITE_FALLBACK=true`（环境类，非本版代码缺陷） |
| 数据库迁移 | **无 DDL/DML** ⇒《数据运维说明》**不适用**（声明） |
| 环境变量 / 配置面 | 本版**不新增运行时开关**；配置项未变动 |

## 4. 缓存与消息运维（5.3）

| 项 | 实测 |
|----|------|
| 缓存预热 | **无该步骤**（本版不引入缓存层变更）⇒ **不适用（声明）** |
| 消息／队列 | 本版不引入消息链路 ⇒ **不适用（声明）** |
| 幂等 | `dps_proxy` 为**无状态透传**（不落库、无写入队列）⇒ 回滚无数据一致性风险 |

## 5. 上线验证（5.5 · **含关联 TT-ID**）

**验证执行**：`python doc/release/evidence/v1410/…`（探针脚本见《发布入场检查记录与发布计划》§5；证据 `openbase-deploy-verify-20261002.json`）

| # | 验证项 | 方式 | 实测结果 | 关联 TT-ID | 结论 |
|:-:|--------|------|----------|------------|:----:|
| 1 | 服务存活 | `GET /health` | **200** `{"status":"ok"}` | TT-v1.4.10-001 | ✅ |
| 2 | 契约面完整 | `GET /openapi.json` | **200**；`paths=144` | TT-v1.4.10-002 | ✅ |
| 3 | v1.4.10 端点可见 | 统计 `dps-proxy` 路径 | **26 条**（含 `templates/{code}/preflight`、`diff`、`lineage/*` 等新增） | TT-v1.4.10-003 | ✅ |
| 4 | 鉴权 fail-closed（无令牌） | `GET /api/v1/dps-proxy/templates` | **401** `AUTH_401 missing bearer token` | TT-v1.4.10-004 | ✅ |
| 5 | 鉴权 fail-closed（坏令牌） | 同上 ＋ `Authorization: Bearer invalid-token` | **401** `AUTH_401 invalid or expired token` | TT-v1.4.10-005 | ✅ |
| 6 | 既有端点鉴权面 | `GET /api/v1/dps-proxy/{health,portraits,tags/categories,reports/overview}` | 均 **401**（无令牌）⇒ 门禁对既有与新端点一致 | TT-v1.4.10-006 | ✅ |
| 7 | 上游存活透传 | 经代理 `GET /api/v1/dps-proxy/health` | 透传上游响应（**错误保真**语义成立） | TT-v1.4.10-007 | ✅ |
| 8 | 前端制品可构建 | `npm run build` | **✓ built in 4m 22s**，`dist/index.html` 生成 | TT-v1.4.10-008 | ✅ |
| 9 | 前端静态制品可托管 | `dist/` 产物面 | 产物齐备（`index.html` ＋ 分包 assets） | TT-v1.4.10-009 | ✅ |
| 10 | 日志落盘与结构化 | `logs/openbase/openbase-20261002.jsonl` | **结构化 JSONL**（`ts`/`level`/`service`/`module`/`message`/`env`/`version`/`request_id`） | TT-v1.4.10-010 | ✅ |
| 11 | 上游版本口径（跨仓） | `GET http://127.0.0.1:8030/health/liveness` | **200**、**`version=2.12.1`** ⇒ DPS 回执附条件项**闭合** | TT-v1.4.10-011 | ✅ |

**上线验证结论**：**11/11 通过**；**无失败项**。

## 6. 真实上游联调（OpenBase → DPS v2.12.1）—— **环境受限，如实登记**

**执行**：`doc/release/evidence/v1410/dps-proxy-integration-step5-20261002-052459.json`

| 项 | 结果 |
|----|------|
| OpenBase 侧门禁 | ✅ 无令牌 → **401 fail-closed**（`AUTH_401 missing bearer token`） |
| 带令牌经代理访问 DPS | ⚠️ 全部返回 **401/透传错误体** |
| 直连 DPS 归因（受信来源已配） | **403 `{"code":403,"message":"组织不存在"}`** ⇒ **DPS 侧数据库缺少组织/租户种子** |
| 根因 | 共享 PostgreSQL `192.168.0.151:5432` 连接被中断 ⇒ DPS 以 **`SQLITE_FALLBACK=true` 空库**启动 ⇒ `dps-org-001`／`dps-tenant-001` 等种子缺失 ⇒ DPS 身份/权限门禁拒绝 |
| 定性 | **环境类（非本版代码缺陷、非本仓缺陷）**：本仓视角为**透传方**，改动面 = 0；`dps-proxy` 的**错误保真**（上游错误体逐字透传）在本轮被反向验证成立 |
| 权威集成证据 | **Step 4 真实上游集成**（DPS **v2.12.0**，PG 模式、种子齐备）：17 用例逐条留痕，未知 code **preflight→404**、**diff→404**、`templates`→**200** 等 —— 见 `doc/test/evidence/v1410/dps-proxy-integration-20261001-103215.txt` |
| 补验计划 | 共享 PG 稳定窗口恢复 DPS 种子数据后复跑本探针（**不阻断本版发布**，Step 4 已成立解） |

## 7. 监控 / 日志 / 告警检查（5.6）

| 检查项 | 实测 | 结论 |
|--------|------|:----:|
| 日志格式 | **结构化 JSONL**：`ts`／`level`／`service`／`module`／`message`／`env`／`version`／`request_id`（符合 `observability-standards`：timestamp/level/service/module/message/env ↔ 本项目 `service`/`request_id`） | ✅ |
| 日志落点 | `logs/openbase/openbase-<YYYYMMDD>.jsonl`（进程启动即装配） | ✅ |
| 版本可追溯 | 每行含 `version` 字段（本轮＝发布提交 `c2c06b1`） | ✅ |
| 健康面 | `/health` 暴露存活语义；`/openapi.json` 可做契约面巡检 | ✅ |
| 上游可观测 | 上游不可达 → 结构化 `dps-proxy upstream unreachable`；达阈值 → `503` 显式降级 ＋ 响应头 `X-DPS-Upstream-Degraded` | ✅ |
| 日志敏感面 | 模式扫描：**零凭据**（仅出现语义词 `token`／`bearer`，非密钥值） | ✅ |
| 告警规则 | 本仓**未接入告警系统**（无 Alertmanager／通知通道） | ⛔ **不适用（声明）**；阈值与 SLO 建议见《回滚方案与运维手册-v1.4.10》§9 |
| Trace / 日志关联 | 每行带 `request_id`（无请求时为 `-`），可与错误响应 `request_id` 串联排障 | ✅ |

## 8. 性能上线检查（5.7a）

| 接口 | 轮次 | MIN | **P50** | **P95** | MAX | 说明 |
|------|:----:|:---:|:-------:|:-------:|:---:|------|
| `GET /health` | 25 | 3.4 ms | **12.4 ms** | **90.4 ms** | 3515.1 ms | 平均值 167.4 ms；MAX 为**单次冷态尖峰**（首次执行路径/GC），非周期性 |

**证据**：`doc/release/evidence/v1410/openbase-health-latency-20261002.txt`（25 个样本逐点留痕）。

**结论**：Dev 无 SLA 承诺，本表作为**基线**供后续版本比对（判定口径：P99 不得超基线 ×1.5）。**无阻塞性能退化**。
**说明**：本版**性能压测（压载 P99）为 Step 4 遗留条件项**（需稳定上游），本轮**未做压载**，如实登记、不计入通过。

## 9. 安全上线检查（5.7b）

| 检查项 | 实测 | 结论 |
|--------|------|:----:|
| 未鉴权访问 | 无令牌 → **401** `AUTH_401` | ✅ |
| 无效令牌 | `Bearer invalid-token` → **401** `invalid or expired token` | ✅ |
| 鉴权覆盖面 | 新端点与既有端点**一致** fail-closed | ✅ |
| 响应敏感面 | 6 类模式（password／secret／api_key／`sk-`／`authorization: bearer`／jwt）在响应体中命中 **0**（仅语义词 `token`／`bearer` 出现于错误**文案**） | ✅ |
| 日志敏感面 | **零凭据**（同 §7） | ✅ |
| TLS | Dev 本地 HTTP ⇒ **不适用（声明）**；TLS 由部署架构在 Test/Pro 要求 | ⛔ 不适用 |
| CORS | 业务响应未发现通配 `Access-Control-Allow-Origin` | ✅ |
| 依赖风险 | 复用 Step 4 依赖清单核对；无阻塞项 | ✅ |

## 10. 回滚预案与核验（5.8）

| 项 | 结果 |
|----|------|
| 预案完整性 | ✅ 触发条件 ＋ 路径分类（①前端制品／②后端代码／③整版）＋ 审批人 ＋ **15 分钟验证门禁** ＋ **验证清单含关联 TT-ID** |
| 路径核验 | ✅ `v1.4.9` tag 存在（`ca268f73…`）；变更面可整段 revert；**无 DB／配置遗留** |
| 数据回滚 | ⛔ **不适用（声明）**：本版无 DDL/DML |
| 配置回滚 | ⛔ **不适用（声明）**：本版无运行时开关 |
| 蓝绿／金丝雀自动回滚 | ⛔ **不适用（声明）**：Dev 单进程直接部署 |
| 裁定 | **回滚预案成立**，无需回滚（本轮未触发） |

## 11. 运维移交（5.9）

| 移交物 | 内容 | 状态 |
|--------|------|:----:|
| 运维手册 | 《OpenBase-回滚方案与运维手册-v1.4.10》§7~§11 | ✅ |
| 联系人 | DO-OpenBase-Dev／TE-OpenBase-Test／AU-OpenBase-Dev／PM-OpenBase-Dev | ✅ |
| 常见故障与排障命令 | 6 类（DB 降级／`SYS_502`／503 降级／DPS 401 未配受信来源／DPS 403 组织不存在／前端透传错误） | ✅ |
| SLA／SLO（建议） | 可用性 ≥99.9%、错误率 ≤1%、P99 ≤基线×1.5、降级率 ≤1% | ✅ |
| 上线后必做 | 观察 15 分钟健康与错误率；确认 `logs/openbase/*.jsonl` 持续写入 | ✅ |

## 12. 遗留与改进项（如实登记）

| # | 项 | 定性 | 处置 |
|:-:|----|------|------|
| 1 | **共享 PostgreSQL 连接抖动** ⇒ 本仓内存降级、DPS SQLite 空库 | **环境类** | 待共享库稳定窗口恢复；本仓降级为既有设计，**非本版缺陷** |
| 2 | **真实上游联调受阻**（DPS 空库 ⇒ 403「组织不存在」） | **环境类**（受限） | 见 §6；**Step 4 已成立解**（DPS v2.12.0 PG 模式 17 用例留痕）；**不阻断发布** |
| 3 | **性能压载（P99）未做** | **条件（P1）** | Step 4 遗留条件项；本版仅给热态基线，**不计入通过** |
| 4 | 真实 S3 用例 4 例跳过（`OPENBASE_TEST_REAL_INFRA=1` 未设） | 条件（P3） | 真实基础设施窗口执行 |
| 5 | 告警系统未接入／TLS（Dev） | ⛔ **不适用（声明）** | 阈值与 TLS 由 Test/Pro 承担 |
| 6 | 前端 `element-plus`／`echarts` 分包 >1 MB（gzip 337／343 kB） | 硬化建议（非阻塞） | 后续版本按需做手动分包／按需引入 |

## 13. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-10-02 | DO-OpenBase-Dev | 初始创建：发布版本与制品确认（`c2c06b1`、回退目标 `ca268f73`、前端制品重建 4m22s）、**部署执行（Dev 直接部署；日志 `version=c2c06b1` 命中发布提交；DB 降级如实留痕）**、环境与配置核验（`/health` 200／`/openapi.json` 144 路径／`dps-proxy` 26 条／无 DB 迁移）、缓存与消息**不适用声明**、**上线验证 11 项全部通过（含关联 TT-ID）**、**真实上游联调环境受限如实登记（DPS 空库 ⇒ 403「组织不存在」）**、监控日志告警检查（结构化 JSONL／零凭据；告警不适用）、**性能基线（P50 12.4 ms／P95 90.4 ms）**、安全上线检查（401×2／零敏感）、**回滚预案与核验（15 分钟门禁）**、运维移交、遗留 6 项。**总判定：上线通过（Dev）**。状态 **[Released]**。 |

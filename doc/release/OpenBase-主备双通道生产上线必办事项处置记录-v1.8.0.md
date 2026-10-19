# OpenBase-主备双通道生产上线必办事项处置记录-v1.8.0

| 项目 | 内容 |
|------|------|
| 记录名称 | 主备双通道生产上线必办事项（S1~S5 / G1~G7）处置记录 |
| 记录编号 | OB-GOLIVE-CHANNEL-AB-DISPOSITION-v1.8.0 |
| 版本 | **v1.8.0** |
| 状态 | **[Approved]**（G3/G4/G5/G6/G5-OBS/G7 闭环；G1/G2 运维侧待下发；G7 B 通道注入完成、端到端复核待共享 PG 恢复） |
| 编制日期 | 2026-10-16 |
| 编制人 | AA/PM-OpenBase-Dev |
| 处置依据 | 《OpenBase-主备双通道生产上线必办事项清单-v2.2.0》（OB-GOLIVE-CHANNEL-AB-v2.2.0） |
| 处置日期 | 2026-10-16（v1.0.0）/ 2026-10-18（v1.1.0 真实面 / v1.2.0 双签与立项 / v1.3.0 G5-OBS 实施 / v1.4.0 审批单风险补充 / v1.5.0 G4 双签闭环 / v1.6.0 G5-OBS 闭环 / v1.7.0 G7 闭环 / v1.8.0 G7 B 通道注入） |
| 关联交付 | 《OpenBase-主备双通道生产上线回滚方案-v1.0.0》（S2）；《G4-T4-2 A 直连豁免行双签审批单-v1.7.0》（[Approved]）；《G5-OBS Memory 跨租户隔离修复立项方案-v1.1.0》；《OpenBase-G5-OBS迁移窗口执行单-v1.1.2》（[Final]）；《OpenBase-G7-D20跨租户APIKey裁定与生产验证记录-v1.1.0》（[Approved]） |

## 修订历史

| 版本 | 日期 | 编制人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-16 | AA/PM-OpenBase-Dev | 首次产出：S1~S5 / G1~G6 的逐项处置结论、已完成项证据、阻塞项的**执行手册**（步骤/命令/判据/证据落点）与阻塞条件 |
| v1.1.0 | 2026-10-18 | OpenBase 架构组 | G3/G5/G6 真实运行态执行并闭环；G4 机器面（矩阵/读写等价/K14）闭环；新增观测项 G5-OBS；Q5/Q6/Q7 裁定落地 |
| v1.2.0 | 2026-10-18 | OpenBase 架构组 | 产出 G4-T4-2 双签审批单（[待签署]）；G5-OBS 立项为跨仓小版本迭代并明确版本/迁移/验收/回滚 |
| v1.3.0 | 2026-10-18 | OpenBase 架构组 | G5-OBS T1~T4 实施：OpenLLM 2.18.0 / OpenMemory 7.3.2、单测 40 + 6 passed、目标库 dry-run 279/37/242；T5/T6 待迁移窗口 |
| v1.4.0 | 2026-10-18 | OpenBase 架构组 | G4-T4-2 审批单升 v1.1.0：增补 A 直连豁免风险点（R1~R8）、逐端点映射、签署前 8 项机械核对；同步清单引用至 v1.5.0 |
| v1.5.0 | 2026-10-18 | OpenBase 架构组 | G4 闭环：审批单升 v1.7.0 `[Approved]`（双签 + §7.1 生效记录）；补记 P5~P8 窗口证据（Prometheus target UP、防火墙规则、K07 矩阵 v1.3.0 gaps=0、告警 5 条、四服务回环监听）；清单引用同步至 v1.7.0 |
| v1.6.0 | 2026-10-19 | OpenBase 架构组 | **G5-OBS 闭环**：MQ1=A/MQ3=A；T5 迁移批次 0113（41 行）+ 0132（1 行）、verify/幂等 PASS；T6 开启；AC-MT-2~6 全 PASS；新增 **G7**（D20 跨租户 API Key 写冲突待裁定）；清单引用同步至 v2.0.0 |
| v1.7.0 | 2026-10-19 | OpenBase 架构组 | **G7 闭环（方案 ①）**：OpenLLM 建 `tenant-1` 租户 + `svc-tenant-1` 服务账号 + 租户级 API Key；生产 8001 在 D20 开启下三路回写 PASS；产出《G7 裁定与生产验证记录-v1.0.0》；清单引用同步至 v2.1.0 |
| v1.8.0 | 2026-10-19 | OpenBase 架构组 | G7 后续：OpenBase B 通道新增 `OPENBASE_LLM_API_KEYS_BY_TENANT` 按租户选 Key；本地 `.env` 注入、单测 33/73 passed、进程内选择 PASS；端到端转发复核因共享 PG 不可达登记待补跑；G7 记录升 v1.1.0、清单引用同步 v2.2.0 |

---

## 0. 处置总览

| 项 | 事项 | 本批结论 | 证据 / 指针 |
|:--:|------|:--------:|-------------|
| **G1** | 三 REAL 开关置真 | **仓库侧 ✅ 已办**（载体补齐）；运维侧 ⬜ 待下发 | OpenLLM `9948d22`；§G1 |
| **G2** | 生产门禁 5 组开关置真 | **仓库侧 ✅ 已办**（根模板已含 5 组；本批补本地缺省声明）；运维侧 ⬜ 待下发 | OpenLLM `9948d22`；§G2 |
| **G3** | L2-1 主备切换演练（真实） | ✅ **PASS**（S7-T3-1~4） | `doc/test/evidence/s7/l2-1/failover-drill.json`、`drill-report.md` |
| **G4** | L2-2 通道矩阵终验（真实） | ✅ **PASS**（T4-1/3/4 PASS + T4-2 双签完成）；审批单 v1.7.0 `[Approved]`，2026-10-18 生效 | `doc/test/evidence/s7/l2-2/**`；《OpenBase-G4-T4-2-A直连豁免行双签审批单-v1.7.0》 |
| **G5** | 回写链路真实面 | ✅ **PASS**（三路落地 + async 复投幂等）；观测项 G5-OBS 已闭环 | `doc/test/evidence/s7/g5/**`；《OpenBase-G5-OBS迁移窗口执行单-v1.1.2》 |
| **G6** | 回写 `profile` 真实化 | ✅ **PASS**（真实 DPS + `extract_targets`） | 同上 |
| **G7** | D20 跨租户 API Key 写冲突 | ✅ **PASS（方案 ①）**：租户级服务 Key + 生产实例三路写入；OpenBase B 通道注入完成（端到端复核待共享 PG） | `doc/test/evidence/s7/g5/g7-production-writeback.json`、`g7-openbase-key-injection.json`；《G7 裁定与生产验证记录-v1.1.0》 |
| **G5-OBS** | memory 跨租户隔离修复 | ✅ **已闭环**（T5/T6/AC-MT-2~6） | `doc/test/evidence/s7/g5/ac-mt-*.json` |
| **S1** | 接管审计开关评估 | ✅ 已评估并落载体（建议审批后开启） | §S1 |
| **S2** | 回滚方案与演练 | ✅ 方案已产出；演练待窗口 | §S2 |
| **S3** | `channel_report` 接监控 | ✅ 已评估（`/health` 段落已可机读） | §S3 |
| **S4** | 发布强制核验执行 | ✅ 清单/矩阵已就绪；执行待目标环境 | §S4 |
| **S5** | 台账与文档状态同步 | ✅ 本批文档集已同步（清单 v2.2.0 / 本记录 v1.8.0） | §S5 |

> **说明（纪律）**：凡需真实运行态/运维窗口的项，**一律如实登记为未闭环，不填 PASS**；所有已完成项均给出**可核验证据**。

---

## G1 —— 三 REAL 开关置真

**处置（仓库侧，已完成）**：OpenLLM 提交 **`9948d22`**（2 文件 / +39 −3）
- 仓库根 `.env.example`（生产 profile）新增「**通道 B 数据面**」块：
  `OPENMEMORY_ENABLED=true` / `OPENRAG_ENABLED=true` / `DPS_ENABLED=true` + 三个 `*_BASE_URL` 占位，且 `OPENLLM_OPENMEMORY_REAL=true` / `OPENLLM_OPENRAG_REAL=true` / `OPENLLM_DPS_REAL=true`；
- `backend/.env.example`（本地 profile）补同名三键本地缺省 `false` + 注释；
- 两文件 `APP_VERSION` 由 `2.17.1` 对齐为 **`2.17.10`**（消除模板版本漂移）。

**待办（运维侧）**：目标环境 `.env`（被 `.gitignore` 排除）按上式显式置真。
**通过判据**：运行态调用**真实契约端点**（`/api/v1 remember/recall`、`/api/v1 search/ingest`、真实 DPS），**非** `/openmemory/v1`、`/openrag/v1` stub；`/health` 三组件 `ok`。

## G2 —— 生产门禁 5 组开关置真

**处置（仓库侧，已完成）**：
- 仓库根 `.env.example` 既有「生产启动门禁」块，已含 **5 组 = true**（`ENFORCE_INBOUND_IDENTITY_HEADERS` / `TENANT_SCOPE_ENFORCE` / `TENANT_HEADER_CONSISTENCY_ENFORCE` / `QUOTA_MISSING_FAIL_CLOSED` / `RBAC_PERMISSION_ENFORCE`）；
- 本批在 `backend/.env.example` **补齐 4 组门禁的本地缺省声明**（`false` + 指向根模板）——**修复了此前本地模板缺声明的载体缺口**。

**待办（运维侧）**：目标环境 `.env` 置真。
**通过判据**：`ENV=production` 下应用**正常启动**（未置真即按门禁拒绝启动）；启动日志无门禁告警。

## G3 —— L2-1 主备切换演练（真实运行态）

**为何未在本机执行**：需**真实运行态 + 可注故障窗口**；且既定纪律「**禁停服注入**」，本机沙箱不可完成。
**可复用资产**：`scripts/service-orchestrator.ps1`（受管编排唯一入口）、`scripts/run_smoke_s0_s6.ps1` / `scripts/verify_mtauth_realface.ps1`（F-10 改造后经编排入口）、`doc/tmp/run_ra06_failclosed.ps1`（**非破坏性注入范式**：探针实例 DSN 不可达 + 专用端口 + 一命令内「起→探→停」）。
**执行手册（联调窗口）**：
1. 经编排器起「探针实例」（专用端口），共享服务与共享 PG 不受影响；
2. **场景①（B 断 → A 接管）**：注入「最终 LLM 不可达」（探针实例指向不可达上游）→ 断言 `bypass_orchestration=true`、`routing_recommendation=use_a_direct`、**写路径为 `skipped`（T11 暂停回写）**；
3. **场景②（A 断 → B 维持）**：注入 A 侧组件连续失败达阈值 → 断言主通道仍为 B；
4. 恢复注入，复跑基线用例确认无残留。
**判据 / 证据**：S7-T3-1~4；证据落 `doc/test/evidence/s7/l2-1/**`。

## G4 —— L2-2 通道矩阵终验（真实运行态）

**沙箱基线（已有）**：OpenLLM `backend/scripts/smoke_l3_2.py` 沙箱面实跑**聚合退出码 0**（单主路径 / **A-B 等价三系统** / **L2-2 矩阵 17 行** / 403 矩阵 / 跨域不可见 / org 别名防串域 / 保留码拒写 / `REAL_*` 零耦合）。
**执行环境**：已在当前可用全栈环境（`192.168.0.157`）完成四仓运行态 + 真实头语义终验。
**执行手册**：以 S4-T8 `matrix_rows` 为基座，逐行（每子系统 × A/B × 头语义）真实双签；**写路径等价**（A 不承载写 / B 承载）；**K14 幂等**（复投不重复执行）。
**判据 / 证据**：S7-T4-1~4；证据落 `doc/test/evidence/s7/l2-2/**`。

**双签前置（v1.4.0 补充）**：审批单 v1.1.0 §5 已列 A 直连豁免风险 R1~R8（身份旁路/端点测绘/指标泄露/探活伪造/审计归因/配置漂移/到期失控/资源滥用），签署前须完成 §8 的 8 项机械核对并留证；未留证不得签「同意」。

**闭环记录（v1.5.0，2026-10-18）**：

1. **P5 告警/抓取前置**：Prometheus 3.13.4 以 Bearer token 抓取 `openllm`，target `UP`（`up=1`，无 401/403）；豁免告警规则 5 条已加载（`health=ok`）。
2. **P6 网络面**：三 Profile 启用且默认入站 Block；`OpenBase-Security-8001-In`/`8020-In` 仅允许 `127.0.0.1`；OpenLLM / OpenRAG / OpenMemory / DPS 四服务实测 HEALTHY 且 `wildcard_bindings=0`。
3. **P7 K07 终验**：补登记 16 个新增业务端点，矩阵升 v1.3.0（370 行），`gaps=0 / uncovered=0 / exemption_without_approval=0`；隔离用例 792 passed；OpenLLM `93ac545`。
4. **P8 双签**：审批单 v1.6.0 完成技术/发布双签，v1.7.0 回填 §7.1 生效记录（2026-10-18 生效，复核 2026-12-01，到期 2026-12-31）；G4-T4-2 关闭。
5. **证据**：`doc/test/evidence/s7/security/exempt-hardening/window-20261018/`（`p5-prometheus.json`、`p6-firewall.json`、`p6-network.json`、`p7-k07.json`、`p8-alerts.json`、`summary.json`）。

## G5 —— 回写链路真实面

**契约（已就绪）**：`POST /openllm/v1/writeback` 三路（`memory` / `rag` / `profile`）；**幂等**（`session_id + seq + target`）；**异步队列 + 指数退避 ≤3 次**；未知 target 字段先行校验。
**为何未在本机执行**：需**真实上游运行态**；原 S4-4（回写队列就绪性/环境）、S6-3（主通道沉淀依赖 LLM/回写）为 PENDING。
**执行手册**：起全栈 → 三路各投一次（`sync` 模式便于判据）→ 断言三路均落真实上游；复投断言 `duplicated=true` 且不重复执行；故障注入断言退避 + 死信可视。
**判据 / 证据**：三路运行态留证（回写响应 + 上游落库）。

## G6 —— 回写 `profile` 路由真实化

**为何未在本机执行**：配置注记「**DPS Mock 先行**」，需真实 DPS。
**执行手册**：`DPS_ENABLED=true` + `DPS_BASE_URL` + `OPENLLM_DPS_REAL=true`；探针断言 `profile` 回写打到**真实 DPS**（非 Mock），`extract_targets` 生效。

## S1 —— 接管审计开关评估

**结论**：**建议生产开启**（以获得 B→A 接管统计口径），**但须先完成动作码审批**——动作码 `channel_failover_b_to_a` **属暂定、待单独立项审批**。
**处置**：已在 OpenLLM 根 `.env.example` 生产块列出 `CHANNEL_AUDIT_ENABLED`（值 `false` + 说明），并同步 `backend/.env.example`；**默认关 ⇒ 出厂行为与现行逐字一致**（不改变既有默认）。

## S2 —— 回滚方案与演练

**处置**：✅ 已产出《OpenBase-主备双通道生产上线回滚方案-v1.0.0》（本批交付，含开关级 / 通道级 / 版本级三级回滚 + 验证判据 + 风险边界）。
**演练**：⬜ 待联调窗口按方案 §6 演练并留证。

## S3 —— `channel_report` 接入监控

**结论**：**无需改代码**——`/openllm/v1/health` 已含 `channel` 段落（偏好 / 主通道 / 单主路径 / `healthy_b` / 演练窗口 / 自动开关；异常降级 `unavailable`）＋ `components.*.channel`，**可机读**；「该走哪条路」已有**单一事实源**。
**处置**：登记为**运维观测项**——建议将 `channel` 段落与 `components.*` 纳入监控采集，对「组件降级」「LLM 不可达」配置告警。

## S4 —— 发布强制核验执行

**处置**：✅ 清单/矩阵**已就绪**——《续接指南》§10.3「生产必需开关矩阵」（含 OpenLLM **5 组强耦合启动门禁**）已定为**发布强制核验项**；本批 `.env.example` 生产块使核验项**逐项可对照**。
**执行**：⬜ 待目标环境按 §10.3 逐项核验并留证（把「拒绝启动」提前到发布门禁）。

## S5 —— 台账与文档状态同步

**处置**：✅ 本批文档集已同步——清单 v1.5.0、本处置记录 v1.4.0、回滚方案 v1.0.0；续接指南 §10.3/§10.4（v1.0.24）此前已同步。
**残留**：上游台账 §10.3 未决项行、S7 段 B 面（L2-1/L2-2）状态回写 —— 建议**随联调窗口闭合时一并回写**，避免中途多次改动（如实登记）。

---

## G3~G6 真实面执行结果（2026-10-18）

| 项 | 命令 / 资产 | 结果 | 证据 |
|:--:|-------------|------|------|
| **G3** | `scripts/drill_l2_1_failover.py`（驱动 OpenLLM `ChannelStateManager`） | **PASS**：S7-T3-1 B断→A接管（写仅在 A、B 写被拒）；S7-T3-2 A断→B维持；S7-T3-3 单主路径；S7-T3-4 报告字段齐备；退出码 0 | `doc/test/evidence/s7/l2-1/failover-drill.json`、`drill-report.md` |
| **G4** | `scripts/dual_channel_e2e.py` + `scripts/finalize_l2_2_matrix.py --matrix matrix-rows-base.json --check-read-ab --check-write-ab --k14` | **机器面 PASS**：T4-1（17 行、缺口 0）、T4-3（OpenRAG 9/9、OpenLLM 6/6、DPS 18/18、OpenMemory PASS_EMPTY）、T4-4（B→A 可见、A 写 403 期望拒绝、K14 同名行=1）；**T4-2 人工双签待窗口**，整体按纪律保留 PENDING | `doc/test/evidence/s7/l2-2/read-path-ab-equivalence.json`、`write-path-equivalence.json`、`k14-idempotency.json`、`matrix-finalize.json` |
| **G5** | `scripts/writeback_realface.py`（HTTP 三路 sync + 异步复投） | **PASS**：memory/rag/profile `accepted=true`；memory recall 命中、rag documents 命中、profile 命中；异步复投三路 `duplicated=true`；`/openllm/v1/health` 三组件 `ok`、`primary_channel=b`、`single_primary=true` | `doc/test/evidence/s7/g5/writeback-realface.json` |
| **G6** | 同上（profile 段） | **PASS**：真实 DPS `GET /api/v2/portrait/tenant-1_1` 返回 `attributes_json` 含探针标记；`extract_targets=[person,business]` 生效 | 同上 |

**观测项（不阻断 G5 判据；2026-10-19 已闭环）**

| 编号 | 观测 | 影响 | 处置 |
|:----:|------|------|------|
| **G5-OBS** | OpenMemory 回写落库域实测为 `default`（`owner=tenant-1_1`）：OpenMemory 适配器客户端为进程级共享头，未按请求透传 `X-Tenant-ID` | 三路"真实落地"成立；但 B 通道 memory 的**跨租户隔离**未生效（同一实例内按 owner 隔离） | ✅ **已闭环**：T5 迁移（41+1 行）+ T6 开关 + AC-MT-2~6 全 PASS；详见下节与《OpenBase-G5-OBS迁移窗口执行单-v1.1.2》[Final] |

### G5-OBS 执行结果（2026-10-19）

| 项 | 结果 | 证据 |
|:--:|------|------|
| 裁定 | MQ1=A（242 条不可解析行保留 `default`）、MQ3=A（迁移期暂停写回） | 执行单 §2 |
| T5 迁移 | 批次 `g5obs-20261019-0113`：`updated_rows=41`；verify `tenant-1:41`、`leftover_default=0`、`passed=true`；幂等复跑 `0` 行 | `doc/test/evidence/s7/g5/migration-{apply,verify,idem}-g5obs-20261019-0113.json` |
| T5 收口 | T6 开启后新增 `default` 1 行，批次 `g5obs-20261019-0132` 迁移 `1` 行；verify PASS；幂等 `0` 行 | `migration-{apply,verify,idem}-g5obs-20261019-0132.json` |
| T6 开关 | 生产 overlay 注入 `OPENMEMORY_TENANT_HEADERS=true`；OpenMemory 受信来源含 `openbase-orchestrator` | `start-openllm-prod.ps1`、`start-all-services.ps1` |
| AC-MT-2 | 直查 `public.memory_metadata`：2 行 `tenant_code=tenant-1`、`owner=tenant-1_user-1` | `ac-mt-2.json` |
| AC-MT-3 | tenant-1 命中 1 条；tenant-2 同 query 返回 0 条 | `ac-mt-3.json` |
| AC-MT-4 | B 写 → A 读同域命中；DB `tenant_code=tenant-1`、`owner=tenant-1_1` | `ac-mt-4.json` |
| AC-MT-5 | 三路 `accepted=true`；async 首投 `duplicated=false`、复投三路 `duplicated=true`；memory/rag 落 `tenant-1`、profile 落 `tenant-1_1` | `ac-mt-5.json` |
| AC-MT-6 | 批次 `…-0132` verify PASS、二次 apply `0` 行 | `ac-mt-6.json` |
| 缺陷修复 | 迁移脚本首次 apply 的 `UndefinedTableError`（D-3）：`ensure_schema()` 调整到批次查重之前 | OpenMemory `scripts/migrate_memory_tenant_domain.py` |

**新发现（升级为阻断项 G7）**：生产 `ENV=production` + `TENANT_HEADER_CONSISTENCY_ENFORCE=true` 下，归属 `default-tenant` 的 API Key 携带 `X-Tenant-ID=tenant-1` 调用 `/openllm/v1/writeback` 返回 **403「入站租户标识与 API Key 归属租户不一致」**。AC-MT-4/5 因此在**隔离探针实例 8012**（`ENV=staging`、仅关闭 D20、其余真实数据面开关与生产一致）完成，证据 JSON 已标注 `openllm_base` 与 `probe_note`。

### G7 处置结果（2026-10-19，方案 ①）

| 项 | 结果 |
|:--:|------|
| 裁定 | 方案 ①：按租户发放归属一致的 API Key，**保持 D20 强制开启**；不采纳放宽策略 |
| 租户 | OpenLLM 新增 `tenant_code=tenant-1`（`ae2130a8-14fe-4606-a5cf-09ce75d3d1f1`），与 OpenBase 同码 |
| 服务账号 | `svc-tenant-1`（`org_admin`），归属上述租户 |
| API Key | `g7-tenant-1-service`（前缀 `sk-openllm-4010c`）；重复执行时已撤销上一把密钥 |
| DPS 映射 | 生产 overlay 的 `DPS_ORG_CODE_MAP` / `DPS_TENANT_CODE_MAP` 增加该租户 UUID → DPS org/tenant |
| 生产验证 | 8001 在 D20 开启下三路回写 200、`accepted` 全 true；memory/rag 落 `tenant-1`、profile 落 `tenant-1_1`；四组件 ok |
| 证据 | `doc/test/evidence/s7/g5/g7-production-writeback.json` |
| OpenBase 注入 | 新增 `OPENBASE_LLM_API_KEYS_BY_TENANT` + llm-proxy 按 `X-Tenant-ID` 选 Key；本地 `.env` 已注入；单测 33/73 passed、进程内选择 PASS；端到端转发待共享 PG 恢复 |
| 注入证据 | `doc/test/evidence/s7/g5/g7-openbase-key-injection.json` |
| 交接 | 密钥明文与服务账号口令仅落 `doc/tmp/g7/handoff.txt`（不入库），OPS 注入后须轮换 |

> 结论：**G7 PASS**。OpenBase B 通道已新增 `OPENBASE_LLM_API_KEYS_BY_TENANT` 并按出站 `X-Tenant-ID` 选 Key（未配置回落全局），本地注入与进程内选择验证 PASS；端到端 llm-proxy 转发复核因共享 PG 不可达暂阻塞，待基础设施恢复后补跑。OPS 待办为真实生产环境密钥注入/轮换与 DPS 码表登记；不改变既定 D20 安全语义。

### 回归与静态检查（v1.1.0 批次）

| 项 | 结果 |
| --- | --- |
| OpenBase | Q5/Q6 新增 9 例 + Q1/R1 回归 **19 passed** |
| OpenLLM | 回写身份透传新增 2 例 + 网关/画像回归 **36 passed**；模型列表/白名单 **49 + 27 passed** |
| DPS | Q7/Q1/B2/版本契约/fail-closed **46 passed** |
| 运行态 | OpenLLM `2.17.15`、DPS `2.12.5`；七服务健康 |

---

## 附：本批交付清单

| 交付 | 位置 | 说明 |
|------|------|------|
| OpenLLM `.env.example` 生产 profile 补齐 | OpenLLM `9948d22`（`.env.example` + `backend/.env.example`） | G1/G2 载体补齐 + 版本对齐 2.17.10 |
| G3/G4/G5 演练脚本 | `scripts/drill_l2_1_failover.py`、`scripts/dual_channel_e2e.py`、`scripts/finalize_l2_2_matrix.py`、`scripts/writeback_realface.py` | 真实运行态执行与证据生成 |
| G4-T4-2 双签审批单 | 《OpenBase-G4-T4-2-A直连豁免行双签审批单-v1.1.0》 | A 直连/健康管理面豁免行清单、对账、**R1~R8 风险分析**、签署前机械核对、双签栏 |
| G5-OBS 立项方案 | 《OpenBase-G5-OBS-Memory跨租户隔离修复立项方案-v1.1.0》 | 根因、跨仓小版本改动、迁移、验收、回滚 + T1~T4 实施记录 |
| G5-OBS 迁移执行单 | 《OpenBase-G5-OBS迁移窗口执行单-v1.1.2》（[Final]） | MQ1/MQ3 裁定、T5 两批次执行、T6 灰度、AC-MT-2~6、D20 冲突发现与回滚 |
| G5-OBS 运行态证据 | `doc/test/evidence/s7/g5/migration-*.json`、`ac-mt-{2,3,4,5,6}.json` | 迁移、落域、跨租户不可见、B/A 同域、三路回写、幂等 |
| OpenMemory 迁移脚本修复 | OpenMemory `scripts/migrate_memory_tenant_domain.py` | D-3：`ensure_schema()` 前置到批次查重之前 |
| G7 裁定与验证记录 | 《OpenBase-G7-D20跨租户APIKey裁定与生产验证记录-v1.1.0》（[Approved]） | 方案 ①、租户/服务账号/Key、DPS 映射、生产实例三路验证、B 通道注入、交接与回滚 |
| G7 运行态证据 | `doc/test/evidence/s7/g5/g7-production-writeback.json` | D20 开启下的三路落域与组件健康 |
| G7 注入证据 | `doc/test/evidence/s7/g5/g7-openbase-key-injection.json` | 租户级 Key 选择、单测、进程内验证与运行时阻塞说明 |
| 本处置记录 | 本文件 | S1~S5 / G1~G7 逐项处置 + 真实面执行结果 |

---

**记录状态**：[Approved]（G3/G4/G5/G6/G5-OBS/G7 已闭环；G1/G2 待运维下发；G7 B 通道注入完成，端到端复核待共享 PG 恢复，真实生产密钥注入/轮换与 DPS 码表登记待 OPS）

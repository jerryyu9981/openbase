# OpenBase-主备双通道生产上线必办事项处置记录-v1.2.0

| 项目 | 内容 |
|------|------|
| 记录名称 | 主备双通道生产上线必办事项（S1~S5 / G1~G6）处置记录 |
| 记录编号 | OB-GOLIVE-CHANNEL-AB-DISPOSITION-v1.2.0 |
| 版本 | **v1.2.0** |
| 状态 | **[Approved]**（G3/G5/G6 闭环；G4 待双签；G5-OBS 已立项跨仓小版本） |
| 编制日期 | 2026-10-16 |
| 编制人 | AA/PM-OpenBase-Dev |
| 处置依据 | 《OpenBase-主备双通道生产上线必办事项清单-v1.3.0》（OB-GOLIVE-CHANNEL-AB-v1.3.0） |
| 处置日期 | 2026-10-16（v1.0.0）/ 2026-10-18（v1.1.0 真实面执行 / v1.2.0 双签与立项） |
| 关联交付 | 《OpenBase-主备双通道生产上线回滚方案-v1.0.0》（S2）；《G4-T4-2 A 直连豁免行双签审批单-v1.0.0》；《G5-OBS Memory 跨租户隔离修复立项方案-v1.0.0》 |

## 修订历史

| 版本 | 日期 | 编制人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-16 | AA/PM-OpenBase-Dev | 首次产出：S1~S5 / G1~G6 的逐项处置结论、已完成项证据、阻塞项的**执行手册**（步骤/命令/判据/证据落点）与阻塞条件 |
| v1.1.0 | 2026-10-18 | OpenBase 架构组 | G3/G5/G6 真实运行态执行并闭环；G4 机器面（矩阵/读写等价/K14）闭环；新增观测项 G5-OBS；Q5/Q6/Q7 裁定落地 |
| v1.2.0 | 2026-10-18 | OpenBase 架构组 | 产出 G4-T4-2 双签审批单（[待签署]）；G5-OBS 立项为跨仓小版本迭代并明确版本/迁移/验收/回滚 |

---

## 0. 处置总览

| 项 | 事项 | 本批结论 | 证据 / 指针 |
|:--:|------|:--------:|-------------|
| **G1** | 三 REAL 开关置真 | **仓库侧 ✅ 已办**（载体补齐）；运维侧 ⬜ 待下发 | OpenLLM `9948d22`；§G1 |
| **G2** | 生产门禁 5 组开关置真 | **仓库侧 ✅ 已办**（根模板已含 5 组；本批补本地缺省声明）；运维侧 ⬜ 待下发 | OpenLLM `9948d22`；§G2 |
| **G3** | L2-1 主备切换演练（真实） | ✅ **PASS**（S7-T3-1~4） | `doc/test/evidence/s7/l2-1/failover-drill.json`、`drill-report.md` |
| **G4** | L2-2 通道矩阵终验（真实） | 🟡 **机器面 PASS**（T4-1/3/4）；双签审批单已产出（[待签署]） | `doc/test/evidence/s7/l2-2/**`；《OpenBase-G4-T4-2-A直连豁免行双签审批单-v1.0.0》 |
| **G5** | 回写链路真实面 | ✅ **PASS**（三路落地 + 复投幂等）；观测项 G5-OBS 已立项 | `doc/test/evidence/s7/g5/writeback-realface.json`；《OpenBase-G5-OBS-Memory跨租户隔离修复立项方案-v1.0.0》 |
| **G6** | 回写 `profile` 真实化 | ✅ **PASS**（真实 DPS + `extract_targets`） | 同上 |
| **S1** | 接管审计开关评估 | ✅ 已评估并落载体（建议审批后开启） | §S1 |
| **S2** | 回滚方案与演练 | ✅ 方案已产出；演练待窗口 | §S2 |
| **S3** | `channel_report` 接监控 | ✅ 已评估（`/health` 段落已可机读） | §S3 |
| **S4** | 发布强制核验执行 | ✅ 清单/矩阵已就绪；执行待目标环境 | §S4 |
| **S5** | 台账与文档状态同步 | ✅ 本批文档集已同步（清单 v1.2.0 / 本记录 v1.1.0） | §S5 |

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
**为何未在本机执行**：真实面终验需**四仓运行态 + 真实头语义**。
**执行手册**：以 S4-T8 `matrix_rows` 为基座，逐行（每子系统 × A/B × 头语义）真实双签；**写路径等价**（A 不承载写 / B 承载）；**K14 幂等**（复投不重复执行）。
**判据 / 证据**：S7-T4-1~4；证据落 `doc/test/evidence/s7/l2-2/**`。

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

**处置**：✅ 本批文档集已同步——清单 v1.0.0、本处置记录 v1.0.0、回滚方案 v1.0.0；续接指南 §10.3/§10.4（v1.0.24）此前已同步。
**残留**：上游台账 §10.3 未决项行、S7 段 B 面（L2-1/L2-2）状态回写 —— 建议**随联调窗口闭合时一并回写**，避免中途多次改动（如实登记）。

---

## G3~G6 真实面执行结果（2026-10-18）

| 项 | 命令 / 资产 | 结果 | 证据 |
|:--:|-------------|------|------|
| **G3** | `scripts/drill_l2_1_failover.py`（驱动 OpenLLM `ChannelStateManager`） | **PASS**：S7-T3-1 B断→A接管（写仅在 A、B 写被拒）；S7-T3-2 A断→B维持；S7-T3-3 单主路径；S7-T3-4 报告字段齐备；退出码 0 | `doc/test/evidence/s7/l2-1/failover-drill.json`、`drill-report.md` |
| **G4** | `scripts/dual_channel_e2e.py` + `scripts/finalize_l2_2_matrix.py --matrix matrix-rows-base.json --check-read-ab --check-write-ab --k14` | **机器面 PASS**：T4-1（17 行、缺口 0）、T4-3（OpenRAG 9/9、OpenLLM 6/6、DPS 18/18、OpenMemory PASS_EMPTY）、T4-4（B→A 可见、A 写 403 期望拒绝、K14 同名行=1）；**T4-2 人工双签待窗口**，整体按纪律保留 PENDING | `doc/test/evidence/s7/l2-2/read-path-ab-equivalence.json`、`write-path-equivalence.json`、`k14-idempotency.json`、`matrix-finalize.json` |
| **G5** | `scripts/writeback_realface.py`（HTTP 三路 sync + 异步复投） | **PASS**：memory/rag/profile `accepted=true`；memory recall 命中、rag documents 命中、profile 命中；异步复投三路 `duplicated=true`；`/openllm/v1/health` 三组件 `ok`、`primary_channel=b`、`single_primary=true` | `doc/test/evidence/s7/g5/writeback-realface.json` |
| **G6** | 同上（profile 段） | **PASS**：真实 DPS `GET /api/v2/portrait/tenant-1_1` 返回 `attributes_json` 含探针标记；`extract_targets=[person,business]` 生效 | 同上 |

**观测项（不阻断 G5 判据，但需后续迭代）**

| 编号 | 观测 | 影响 | 处置 |
|:----:|------|------|------|
| **G5-OBS** | OpenMemory 回写落库域实测为 `default`（`owner=tenant-1_1`）：OpenMemory 适配器客户端为进程级共享头，未按请求透传 `X-Tenant-ID` | 三路"真实落地"成立；但 B 通道 memory 的**跨租户隔离**未生效（同一实例内按 owner 隔离） | **已立项**：《OpenBase-G5-OBS-Memory跨租户隔离修复立项方案-v1.0.0》——跨仓小版本（OpenLLM 2.18.0 / OpenMemory 7.3.2 / OpenBase 验收）；开关默认 `false`，先迁移后开启 |

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
| G4-T4-2 双签审批单 | 《OpenBase-G4-T4-2-A直连豁免行双签审批单-v1.0.0》 | A 直连/健康管理面豁免行清单、对账、双签栏 |
| G5-OBS 立项方案 | 《OpenBase-G5-OBS-Memory跨租户隔离修复立项方案-v1.0.0》 | 根因、跨仓小版本改动、迁移、验收、回滚 |
| 本处置记录 | 本文件 | S1~S5 / G1~G6 逐项处置 + 真实面执行结果 |

---

**记录状态**：[Approved]（G4 双签为唯一发布阻断残留；G5-OBS 已立项跟踪）

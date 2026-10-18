# OpenBase-主备双通道生产上线必办事项清单-v1.8.0

| 项目 | 内容 |
|------|------|
| 清单名称 | 主备双通道（B 主通道 / A 备用直连）生产上线必办事项清单 |
| 清单编号 | OB-GOLIVE-CHANNEL-AB-v1.8.0 |
| 版本 | **v1.8.0** |
| 状态 | **[处置中]**（G3/G4/G5/G6 已闭环；G1/G2 窗口环境已验证、生产 `.env` 待 OPS 下发；G5-OBS T5/T6 待裁定） |
| 编制日期 | 2026-10-16 |
| 编制人 | AA/PM-OpenBase-Dev |
| 适用范围 | 经统一前端 / 智能体发起的会话，经 **OpenLLM 主通道 B**（编排 + 三基础设施取数/回写）与 **OpenBase 备用直连 A** 两条通道上生产前的必办事项 |
| 判据来源 | 《OpenBase-统一身份与主备双通道贯通总体方案》；《OpenBase-问题跟踪记录-v1.4.8》§4AD/§4AH（通道口径）；《OpenBase-上下文精装配与组件通道优化收口方案-v1.6.0》（W1~W4 + T1~T15）；《OpenBase-S7-全域门禁与总收官报告/测试报告-v1.0.0》；《OpenBase-五系统多租户与授权集成总览与续接指南-v1.0.0》§10.3（生产必需开关矩阵） |
| 关联验收单 | 《OpenBase-主备双通道生产上线验收确认单-v1.0.0》 |
| 关联处置记录 | 《OpenBase-主备双通道生产上线必办事项处置记录-v1.5.0》 |
| 关联回滚方案 | 《OpenBase-主备双通道生产上线回滚方案-v1.0.0》 |

## 修订历史

| 版本 | 日期 | 编制人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-16 | AA/PM-OpenBase-Dev | 首次产出：Go/No-Go 阻断项（G1~G6）与建议项（S1~S5），逐项给出责任方、载体/命令、通过判据 |
| v1.1.0 | 2026-10-17 | OpenBase 架构组 | 增补「G1/G2 发布前机械校验」块（R3：`verify_dps_code_map.py` 三项校验 + 4 项勾选）；状态说明同步 |
| v1.2.0 | 2026-10-18 | OpenBase 架构组 | G3/G5/G6 真实运行态闭环；G4 机器面（矩阵/读写等价/K14）闭环、仅余 A 直连豁免行人工双签；新增 G5 观测项（memory 落库域）；Q5/Q6/Q7 裁定落地 |
| v1.3.0 | 2026-10-18 | OpenBase 架构组 | 产出《G4-T4-2 A 直连豁免行双签审批单-v1.0.0》；G5-OBS 立项为跨仓小版本迭代（《Memory 跨租户隔离修复立项方案-v1.0.0》） |
| v1.4.0 | 2026-10-18 | OpenBase 架构组 | G5-OBS 实施 T1~T4：OpenLLM 2.18.0 开关与按请求头、OpenMemory 7.3.2 迁移脚本；目标库 dry-run 279/37/242；T5/T6 待迁移窗口批准 |
| v1.5.0 | 2026-10-18 | OpenBase 架构组 | G4-T4-2 审批单升 v1.1.0：增补 A 直连豁免风险点（R1~R8）、逐端点风险映射与签署前机械核对项；G4 行与处置进展同步引用 |
| v1.6.0 | 2026-10-18 | OpenBase 架构组 | G4 闭环：T4-2 双签完成（审批单 v1.6.0 `[Approved]`）；同步 P7 矩阵 v1.3.0、告警规则与四服务回环监听证据；G4 行转 ✅ PASS |
| v1.7.0 | 2026-10-18 | OpenBase 架构组 | 审批单升 v1.7.0（回填 §7.1 生效记录：生效 2026-10-18、有效期至 2026-12-31、复核日 2026-12-01）；G4 引用与处置记录引用同步至 v1.5.0 |
| v1.8.0 | 2026-10-18 | OpenBase 架构组 | G1/G2 窗口环境验证：production 模式启动成功（2.19.1）、三组件 ok、6 个反例拒绝（证据 `window-20261018-prod/`）；新增 G1/G2 下发清单与 G5-OBS 迁移执行单；G5-OBS 维持 T5/T6 待裁定 |

---

## 0. 阅读约定

- **类型**：`阻断`＝Go/No-Go 门槛，未闭环**不得上线**；`建议`＝非阻断，登记跟踪即可。
- **责任方**：`LL`＝OpenLLM 仓；`OM`＝OpenMemory；`RG`＝OpenRAG；`DPS`；`OPS`＝运维/发布；`OB`＝OpenBase 治理仓。
- **通过判据**：须**可观测/可留证**（探针、证据 JSON、`/health` 字段、审计日志），禁止「口头确认」。

---

## 1. 阻断项（Go / No-Go）

| # | 事项 | 责任方 | 载体 / 命令 | 通过判据 | 状态 |
|:-:|------|:------:|-------------|---------|:----:|
| **G1** | **三 REAL 开关置真**——`OPENLLM_OPENRAG_REAL` / `OPENLLM_OPENMEMORY_REAL` / `OPENLLM_DPS_REAL` 及 `OPENMEMORY_ENABLED` / `DPS_ENABLED` 在**目标环境 `.env` 显式置 `true`**（代码默认全 `False` ⇒ 走 stub） | LL / OPS | OpenLLM `.env.example` + 运维手册「生产环境启动门禁」；`.env`（不入库，运维下发） | 运行态确认**真实契约端点**被调用（`/api/v1 remember/recall`、`/api/v1 search/ingest`、DPS 真实契约），**非** `/openmemory/v1`、`/openrag/v1` stub；`/health` 三组件 `ok` | 🟡 **窗口已验证**：production 模式下三组件均 ok；生产主机 `.env` 待 OPS 下发 |
| **G2** | **生产门禁 5 组开关置真**——`ENFORCE_INBOUND_IDENTITY_HEADERS` / `RBAC_PERMISSION_ENFORCE` / `TENANT_SCOPE_ENFORCE` / `TENANT_HEADER_CONSISTENCY_ENFORCE` / `QUOTA_MISSING_FAIL_CLOSED` | LL / OPS | 同 G1 载体 | `ENV=production` 下应用**正常启动**（未置真即按门禁**拒绝启动**）；启动日志无门禁告警 | 🟡 **窗口已验证**：production 启动成功；6 个反例全部拒绝；生产 `.env` 待 OPS 下发 |
| **G3** | **L2-1 主备切换演练（真实运行态）**——`B 断 → A 接管` / `A 断 → B 维持` 双场景 | OPS / OB | 联调窗口注故障 + 切换演练脚本；判据 S7-T3-1~4 | 双场景演练报告留证：B 断时 `bypass_orchestration=true`、改走 A 直连且**写路径暂停**；A 断时 B 维持 | ✅ **PASS**（S7-T3-1~4；证据 `doc/test/evidence/s7/l2-1/**`） |
| **G4** | **L2-2 通道矩阵终验（真实运行态）**——每子系统 × A/B × **头语义**矩阵 + **写路径等价** + **K14 幂等** | OB / LL | 以 S4-T8 `matrix_rows` 为基座；判据 S7-T4-1~4；证据落 `doc/test/evidence/s7/l2-2/**` | 矩阵逐行真实双签通过；写路径 A/B 等价（A 不承载写，B 承载）；幂等复投不重复执行 | ✅ **PASS**：T4-1/3/4 PASS + T4-2 双签完成（审批单 v1.7.0 `[Approved]`，生效记录见 §7.1） |
| **G5** | **回写链路真实面**——`POST /openllm/v1/writeback` 三路（`memory` / `rag` / `profile`）真实上游落地 | LL / OM / RG / DPS | 回写队列就绪性（原 S4-4）+ 主通道沉淀（原 S6-3）；幂等键 `session_id + seq + target` | 三路均落真实上游并留证；重复投递返回 `duplicated=true` 且不重复执行；失败按指数退避 ≤3 次 + 死信可视 | ✅ **PASS**（三路 accepted=true；复投三路 duplicated=true；证据 `doc/test/evidence/s7/g5/**`） |
| **G6** | **回写 `profile` 路由真实化确认**——当前注记「DPS Mock 先行」，须确认真实 DPS 契约已生效 | LL / DPS | 配置注释与运行态探针 | `profile` 回写打到**真实 DPS**（非 Mock）；`extract_targets` 生效 | ✅ **PASS**（`person_id=tenant-1_1`，`attributes_json` 写入探针标记；证据同上） |

> **Go 判定**：G1~G6 **全部通过**方可进入发布；任一未闭环 ⇒ **No-Go**。

> **处置进展（2026-10-18，详见《处置记录》v1.5.0）**：
> - **G1 / G2**：仓库侧载体已补齐；**窗口环境已验证**（production 模式启动成功、三组件 ok、6 个反例拒绝）；**生产主机 `.env` 下发待 OPS**。下发清单见《OpenBase-G1G2生产环境变量下发清单-v1.0.0》。
> - **G3**：✅ 已跑 `scripts/drill_l2_1_failover.py`（驱动 OpenLLM 真实通道状态机）→ S7-T3-1~4 **全 PASS**。
> - **G4**：✅ **已闭环**。`dual_channel_e2e.py` 四子系统读等价 PASS、写路径 B→A 可见、A 写被拒（期望）、K14 同名行=1；`finalize_l2_2_matrix.py` T4-1/3/4 PASS；T4-2 双签完成——《G4-T4-2 A 直连豁免行双签审批单-v1.7.0》`[Approved]`（2026-10-18 生效，有效期至 2026-12-31，下次复核 2026-12-01）。
> - **G5 / G6**：✅ `scripts/writeback_realface.py` 三路 sync 回写 `accepted` 全 true；memory/rag/profile 均真实落地；异步复投三路 `duplicated=true`；profile 落 `person_id=tenant-1_1`（真实 DPS）。
> - **观测项 G5-OBS**：OpenMemory 回写落库域实测为 `default`（客户端共享头未透传 per-request `X-Tenant-ID`）。**立项方案已升 v1.1.0 [Approved]**：T1~T4 已实施（OpenLLM 2.18.0 / OpenMemory 7.3.2；单测 40 + 6 passed；目标库 dry-run：default 279 行、可迁移 37、不可解析 242）；**T5 迁移执行 / T6 开关开启待迁移窗口显式批准**，开启前运行态默认值不变。迁移执行单见《OpenBase-G5-OBS迁移窗口执行单-v1.0.0》（MQ1/MQ3 待裁定）。
> - **S1~S5**：维持 v1.1.0 结论。

### G1 / G2 发布前机械校验（R3，2026-10-17）

发布窗口按下列 4 项逐条执行并留存输出（任一失败即 **No-Go**）：

- [ ] 目标环境 `.env` 已下发：`OPENBASE_DPS_CODE_MAP`、`OPENBASE_DPS_ORG_MAP`/`_TENANT_MAP`（UUID 别名）、`DPS_ORG_CODE_MAP`/`DPS_TENANT_CODE_MAP`（运维签字）
- [ ] 两仓互译表由登记式**生成**而非手抄：`python scripts/gen_dps_code_map.py --format env`
- [ ] 机械校验通过：`python scripts/verify_dps_code_map.py --strict` → `RESULT: PASS`（附输出）
- [ ] OpenLLM 启动日志无 `启动自检｜DPS` 告警，且抽样一次 explicit `rag` 请求 `degraded` 为空

> 校验脚本三项判据：①结构（登记式解析/必填/冲突）；②一致性（登记式期望 ⊆ OpenLLM 两表，
> 允许额外 UUID 别名键）；③存在性（共享 PG 中 org/tenant 存在且 active）。

## 2. 建议项（非阻断，登记跟踪）

| # | 事项 | 责任方 | 说明 |
|:-:|------|:------:|------|
| **S1** | 接管审计开关评估开启（`CHANNEL_AUDIT_ENABLED`，默认 `False`） | LL / OPS | 开启后 B→A 接管留结构化审计（动作码 `channel_failover_b_to_a` 属暂定，须按仓库惯例显式开启）；不开启则出厂行为与现行逐字一致 |
| **S2** | **回滚方案与演练**——主备切换回滚、门禁/开关回退路径 | OPS | 参照已有回滚方案体例；确认开关置真后可回退且不影响既有单租户路径 |
| **S3** | **观测与告警就绪**——`channel_report`（通道/终点/组件/降级维度）接入监控 | OPS | `channel_report` 已使「该走哪条路」**可机读**；建议将其纳入监控与告警（组件降级、LLM 不可达） |
| **S4** | 发布强制核验执行——按《续接指南》§10.3「生产必需开关矩阵」逐项核验 | OPS / OB | 把「拒绝启动」提前到发布门禁，避免部署当场失败 |
| **S5** | 台账与文档状态同步 | OB | 台账 §10.3 未决项行、S7 段 B 面（L2-1/L2-2）状态回写 |

## 3. 与本次走查遗留的关系（不阻断本清单）

| 遗留项 | 状态 | 与本清单关系 |
|--------|:----:|-------------|
| 生产强制期实际翻转（退役面 13 模块） | ⬜ 挂起 | 与 **G2** 耦合（同为启动门禁判据）；生产置真即受门禁约束 |
| OpenRAG `.devflow/config.json::projectVersion` | ⏳ 登记 | 无关 |
| 其余 444 个非 `.py` 文本 BOM | ⏳ 维持 | 无关 |
| DPS 自身 IAM 演进 | ⬜ 规划中 | 无关 |
| T4（诚实降级）运行态段 | ⛔ BLOCKED | 建议随 **G3/G4** 联调窗口一并对齐 |

## 4. 使用方式

1. 逐项执行 §1 阻断项，**每项留证**（探针输出 / 证据 JSON / `/health` 字段 / 演练报告）；
2. 全通过后，填写《主备双通道生产上线验收确认单》§2 逐项结果并签署；
3. §2 建议项按跟踪续办，**不阻塞**上线；
4. 任一阻断项未通过 ⇒ 回到对应责任方修复后重跑该项判据。

---

**清单状态**：[处置中]（G3/G4/G5/G6 已闭环；G1/G2 与 G5-OBS 待运维窗口）

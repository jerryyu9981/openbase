# OpenBase 发布强制核验执行记录（生产必需开关矩阵 · S4）

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.3.0 |
| 状态 | [Review]（待 OPS 复核签字） |
| 日期 | 2026-10-24 |
| 执行人 | 研发（AI 辅助） |
| 上游依据 | 《OpenBase-主备双通道生产上线必办事项清单-v2.2.0》S2/S4；《OpenBase-五系统多租户与授权集成总览与续接指南-v1.0.0》§10.3（裁定③④） |
| 判据 | carrier 核验逐项 PASS；生产发布另须以 `--env-file` 核验目标环境下发值 |

---

## 1. 结论

| 项 | 结论 |
|----|------|
| S4 发布强制核验（仓库侧） | **已执行且全绿**：`9 项 / PASS 9 / FAIL 0`（矩阵 v1.1.0 + 脚本 + 15 例单测） |
| XR-OPS-07（初版登记为 P1 阻断） | **已闭环**：经根因复核为**门禁语义误判**（模板开发默认值被当作生产值），非 OpenMemory 配置缺陷 |
| 生产下发核验 | **下发单已就绪（待 OPS 执行）**：《OpenBase-生产环境配置下发单-XR-OPS-07-v1.0.0》（编号 XR-OPS-07-ENV-001）已给出备份/覆盖/`--env-file` 核验/重启/回滚/回执步骤；本地演练 **PASS**，本机开发 `.env` 实测 **FAIL（未下发）** 作为缺口证据 |
| S2 回滚演练 | **离线段已演练（2026-10-24）**：L1/L2/L3 共 `11 PASS / 3 PENDING / 0 FAIL`（PENDING 均为需生产运行态/注故障窗口的实机段）；详见《OpenBase-S2-三级回滚演练报告-v1.0.0》与 `doc/test/evidence/s2/**` |

> 判定：仓库侧核验能力就绪且矩阵全绿；**生产发布仍以 OPS 的 `--env-file` 核验结果为准**（本记录不代替生产环境核验）。

## 2. 执行方式

```bash
# 仓库载体核验（默认）
python scripts/verify_production_switches.py --json doc/test/evidence/release/switch-matrix-20261023-r2.json

# 生产下发核验（发布/上线时必做）
python scripts/verify_production_switches.py --env-file <目标环境 .env> --repo OpenMemory
python scripts/verify_production_switches.py --env-file <目标环境 .env> --repo OpenLLM
```

- 矩阵唯一事实源：`config/production_switch_matrix.json`（v1.1.0）
- 退出码：`0` = 全部 PASS；`1` = 存在 FAIL（禁止发布）

## 3. 矩阵两种核验模式（v1.1.0 引入）

| 模式 | 适用 | 判据 |
|------|------|------|
| `template_value` | OpenLLM / DPS | 仓库载体（`.env.example` / 部署文档）必须登记**生产值**（如 `=true`） |
| `documented_override` | OpenMemory | 模板可保留**开发默认值**（不翻转既有 M1 行为），但密钥行邻近 8 行内必须写明「生产必须置 true」；同时 `runtime_gate` 指向的运行期守卫必须存在 |

> 设计理由：OpenMemory 的 `require_tenant_scope` 默认 `False` 是**刻意的开发/单租户默认**（变更记录 v1.0.0 §43），翻转模板会破坏 M1；其生产安全由 `validate_identity_trust_policy` 在「生产 ∧ M2 ∧ 未开启」时**拒绝启动**兜底（fail-closed，部署当场失败而非静默 fail-open）。因此正确判据是「模板登记 + 生产覆盖文档化 + 运行期守卫存在」，生产值本身由 `--env-file` 核验。

## 4. 逐项结果（2026-10-23，矩阵 v1.1.0）

| # | 仓 | 检查项 | 载体 | 结果 |
|:-:|----|--------|------|:----:|
| 1 | OpenLLM | `ENFORCE_INBOUND_IDENTITY_HEADERS` | `.env.example` | PASS |
| 2 | OpenLLM | `RBAC_PERMISSION_ENFORCE` | `.env.example` | PASS |
| 3 | OpenLLM | `TENANT_SCOPE_ENFORCE` | `.env.example` | PASS |
| 4 | OpenLLM | `TENANT_HEADER_CONSISTENCY_ENFORCE` | `.env.example` | PASS |
| 5 | OpenLLM | `QUOTA_MISSING_FAIL_CLOSED` | `.env.example` | PASS |
| 6 | OpenMemory | `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE` | `.env.example`（默认 `false` + 生产覆盖注释） | PASS |
| 7 | OpenMemory | `runtime_gate` | `src/openmemory/utils/config.py` | PASS |
| 8 | DPS | `TENANT_CONTEXT_REQUIRED` | `doc/operation/DPS-部署文档-v2.1.0.md` | PASS |
| 9 | OpenBase | 无新增生产开关 | — | PASS（豁免） |

证据：`doc/test/evidence/release/switch-matrix-20261023-r2.json`（初版 r1 保留为误判现场）。

## 5. XR-OPS-07 根因与闭环

| 项 | 内容 |
|----|------|
| 初判（r1） | OpenMemory `.env.example` 中 `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=false`，与 §10.3「载体置真」不一致 → 判定 P1 阻断 |
| 根因复核 | ① 该默认值为**刻意保留**（变更记录 §43「不翻转默认」，M1/开发态不受影响）；② 生产 M2 未置真时 `validate_identity_trust_policy` **拒绝启动**（`src/openmemory/utils/config.py:498-535`），不存在 fail-open；③ 初版门禁把「模板默认值」等同于「生产下发值」，属**判据错误** |
| 闭环动作 | 矩阵升 v1.1.0 引入 `documented_override` + `runtime_gate`；门禁新增「生产覆盖注释存在性」与「运行期守卫存在性」两项机械校验（移除注释或守卫 → 立即 FAIL） |
| 残余要求 | 生产 `.env` 必须 `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=true`，由 OPS 以 `--env-file` 核验并回填本节。**当前状态：待 OPS 执行**；下发单 `XR-OPS-07-ENV-001` 已就绪；本地演练 PASS（`switch-envfile-rehearsal-20261024.json`），开发 `.env` 未下发 FAIL（`switch-envfile-local-20261024.json`） |

## 6. S2 回滚演练（离线段已执行，实机段待 OPS）

依据《OpenBase-主备双通道生产上线回滚方案-v1.0.0》§3~§6 执行，报告：《OpenBase-S2-三级回滚演练报告-v1.0.0》。

| 级别 | 离线段（本机可判定） | 实机段（待 OPS） |
|:----:|---------------------|------------------|
| L1 开关级 | **PASS**：OpenLLM 生产门禁组 15 例、OpenBase 生产门禁 14 例、OpenMemory 强制段 7 例，均验证「开关回落 → 拒绝启动 / 置真 → 可装配」；`--env-file` 双向核验 PASS | 备份 `.env` → 置回 → `service-orchestrator.ps1` 重启 → `/health` → 恢复 |
| L2 通道级 | **PASS**：真实 `ChannelStateManager` 驱动 B→A 接管、A 断维持、单主路径、回切与审计 6 动作（`failover-drill.json` 退出码 0） | 按 `channel_report` 复位并验证写路径恢复（V2/V3） |
| L3 版本级 | **PASS**：回退目标定位（`e2c4f25` / `v1.4.10`）、worktree 检出可执行、纯代码回滚（无迁移）、`verify_release` 单测 18 passed | 镜像回切 + 回滚后 15 分钟内 `verify_release.py` 无 FAIL |

登记发现：**D-01** 旧基线版本号三处不统一（`pyproject`/`__init__` 1.0.0、UI 1.3.0；三处统一始于 `1ba1445`）⇒ L3 回退后须人工核对「部署镜像版本 vs 代码声明版本」；**D-02** L2 演练器跨仓配置面约束已修复（`scripts/drill_l2_1_failover.py` 切至 OpenLLM 仓根后驱动）。

> 生产实机段共 4 项，本环境无部署面，**不填 PASS**；回填后本记录升版并转 [Approved]。

## 7. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.3.0 | 2026-10-24 | 研发（AI 辅助） | **S2 离线段演练回填**：L1/L2/L3 `11 PASS / 3 PENDING / 0 FAIL`；新增《OpenBase-S2-三级回滚演练报告-v1.0.0》与 `doc/test/evidence/s2/**`；登记 D-01（旧基线版本号不统一）、D-02（L2 演练器跨仓配置面约束，已修复）；生产实机段 4 项待 OPS |
| v1.2.0 | 2026-10-24 | 研发（AI 辅助） | **OPS 配置下发就绪**：新增《生产环境配置下发单-XR-OPS-07-v1.0.0》（备份/覆盖/`--env-file` 核验/重启/回滚/回执）；本地演练 PASS、开发 `.env` 未下发 FAIL 证据归档；生产执行仍待 OPS 回填 |
| v1.1.0 | 2026-10-23 | 研发（AI 辅助） | **XR-OPS-07 闭环**：矩阵升 v1.1.0（`documented_override` + `runtime_gate`），修正「模板默认值≠生产值」判据错误；复跑 9/9 PASS；补生产 `--env-file` 核验要求与根因说明 |
| v1.0.0 | 2026-10-23 | 研发（AI 辅助） | 初始创建：S4 仓库侧核验执行（7 PASS / 1 FAIL），登记 OpenMemory 载体漂移为 XR-OPS-07；S2 待 OPS 窗口 |

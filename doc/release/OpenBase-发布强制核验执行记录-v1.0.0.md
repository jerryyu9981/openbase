# OpenBase 发布强制核验执行记录（生产必需开关矩阵 · S4）

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.1.0 |
| 状态 | [Review]（待 OPS 复核签字） |
| 日期 | 2026-10-23 |
| 执行人 | 研发（AI 辅助） |
| 上游依据 | 《OpenBase-主备双通道生产上线必办事项清单-v2.2.0》S2/S4；《OpenBase-五系统多租户与授权集成总览与续接指南-v1.0.0》§10.3（裁定③④） |
| 判据 | carrier 核验逐项 PASS；生产发布另须以 `--env-file` 核验目标环境下发值 |

---

## 1. 结论

| 项 | 结论 |
|----|------|
| S4 发布强制核验（仓库侧） | **已执行且全绿**：`9 项 / PASS 9 / FAIL 0`（矩阵 v1.1.0 + 脚本 + 15 例单测） |
| XR-OPS-07（初版登记为 P1 阻断） | **已闭环**：经根因复核为**门禁语义误判**（模板开发默认值被当作生产值），非 OpenMemory 配置缺陷 |
| 生产下发核验 | **待 OPS**：发布时须对目标环境 `.env` 执行 `--env-file` 模式，确认 OpenMemory 生产值 `true` |
| S2 回滚演练 | **未执行**（需 OPS 运行态与注故障窗口；回滚方案 v1.0.0 已存在） |

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
| 残余要求 | 生产 `.env` 必须 `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=true`，由 OPS 以 `--env-file` 核验并回填本节 |

## 6. S2 回滚演练（待 OPS）

参照《OpenBase-主备双通道生产上线回滚方案-v1.0.0》执行，需记录：

1. 开关级回退：三 REAL 与 5 组门禁开关置假后，服务以非强制态启动且既有单租户路径不受影响；
2. 通道级回退：B 通道断开 → A 直连只读接管（写路径拒绝）；
3. 版本级回退：上一镜像回切后 `verify_release.py` 无 FAIL。

> 以上需真实运行态与注故障窗口；本环境无部署面，**不填 PASS**。

## 7. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.1.0 | 2026-10-23 | 研发（AI 辅助） | **XR-OPS-07 闭环**：矩阵升 v1.1.0（`documented_override` + `runtime_gate`），修正「模板默认值≠生产值」判据错误；复跑 9/9 PASS；补生产 `--env-file` 核验要求与根因说明 |
| v1.0.0 | 2026-10-23 | 研发（AI 辅助） | 初始创建：S4 仓库侧核验执行（7 PASS / 1 FAIL），登记 OpenMemory 载体漂移为 XR-OPS-07；S2 待 OPS 窗口 |

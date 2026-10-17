# OpenBase-G4-T4-2 A 直连豁免行双签审批单-v1.0.0

| 项目 | 内容 |
|------|------|
| 审批单编号 | OB-GOLIVE-G4-T4-2-DS-v1.0.0 |
| 版本 | **v1.0.0** |
| 状态 | **[待签署]**（技术签字 / 发布签字均未完成，签署后转 [Approved]） |
| 关联清单 | 《OpenBase-主备双通道生产上线必办事项清单-v1.2.0》G4（T4-2） |
| 关联处置记录 | 《OpenBase-主备双通道生产上线必办事项处置记录-v1.1.0》 |
| 关联判据 | S7-T4-2「管理面/探活 A 直连豁免行显式标注（与 K07 端点矩阵豁免行对账一致）」 |
| 关联矩阵 | OpenLLM `doc/design/OpenLLM-K07-端点过滤矩阵填报-v1.0.0.md`；OpenBase《端点过滤矩阵模板-v1.0》v1.0.1 |
| 关联证据 | `doc/test/evidence/s7/gate/k07-finalize.json`；`doc/test/evidence/s7/l2-2/matrix-finalize.json`；`read-path-ab-equivalence.json`、`write-path-equivalence.json`、`k14-idempotency.json` |
| 编制日期 | 2026-10-18 |
| 编制人 | OpenBase 架构组 |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次产出：G4-T4-2 A 直连/健康管理面豁免行清单、对账结果、判据核对与双签栏 |

---

## 1. 审批范围（严格限定）

本审批单仅覆盖 **L2-2 通道矩阵中「管理面/探活 A 直连」豁免行**，即各子系统
`GATE_EXEMPT_PATH_PREFIXES`（`/health`、`/metrics`、`/docs`、`/redoc`、`/openapi.json`）
命中的端点行。**不覆盖**：

- 业务面端点（须有隔离用例，缺口/未覆盖清零，另行门禁）；
- DPS 认证/组织类豁免行（k07-finalize 显示 35 条豁免字段不合规，见 §4 独立项）；
- 任何写路径（写路径 A/B 等价已由 G4-T4-4 证据闭环）。

## 2. A 直连豁免行清单

### 2.1 OpenLLM（真实填报，5 行）

| # | 方法 | 端点 | 端点类别 | 身份头 | 豁免 ticket | 审批人 | 到期/复核 | 状态 |
|:-:|:----:|------|---------|--------|-------------|--------|-----------|------|
| 1 | GET | `/health` | 健康管理 | 忽略（服务密钥自身认证） | T-健康直连 | AD-OpenLLM-Dev | 2026-12-31 | A直连豁免 |
| 2 | GET | `/metrics` | 健康管理 | 忽略 | T-健康直连 | AD-OpenLLM-Dev | 2026-12-31 | A直连豁免 |
| 3 | GET | `/docs` | 健康管理 | 忽略 | T-健康直连 | AD-OpenLLM-Dev | 2026-12-31 | A直连豁免 |
| 4 | GET | `/redoc` | 健康管理 | 忽略 | T-健康直连 | AD-OpenLLM-Dev | 2026-12-31 | A直连豁免 |
| 5 | GET | `/openapi.json` | 健康管理 | 忽略 | T-健康直连 | AD-OpenLLM-Dev | 2026-12-31 | A直连豁免 |

> 说明：K07 填报主表聚焦端点集列出其中 4 行（`/redoc` 由 `GATE_EXEMPT_PATH_PREFIXES`
> 同源覆盖，未在聚焦表单列）；`k07-finalize.json` 统计 OpenLLM 豁免行 **5 行、全部有效**。

### 2.2 其余子系统（对账统计，明细以各仓 K07 矩阵为准）

| 系统 | A 直连/健康管理豁免行 | 有效 | 无效 | 来源 |
|------|:---------------------:|:----:|:----:|------|
| OpenRAG | 10 | 10 | 0 | `k07-finalize.json`（openrag 段） |
| OpenMemory | 5 | 5 | 0 | `k07-finalize.json`（openmemory 段） |
| OpenLLM | 5 | 5 | 0 | `k07-finalize.json`（openllm 段）+ 本单 §2.1 |
| OpenBase | 1（模板样例） | 1 | 0 | `k07-finalize.json`（openbase 段，role=template） |

## 3. 判据核对（S7-T4-2）

| 判据项 | 结果 | 证据 |
|--------|:----:|------|
| A 直连豁免行**显式标注**（端点 + 类别 + ticket + 审批人 + 到期/复核） | ✅ | §2.1、OpenLLM K07 矩阵 §2 |
| 与 K07 端点矩阵**逐行对账一致** | ✅ | `k07-finalize.json`：exempt_rows/exempt_valid 与 §2.1 一致 |
| 豁免**在有效期**（到期 2026-12-31，晚于拟发布窗口） | ✅ | §2.1 |
| 豁免**有审批人**（AD-OpenLLM-Dev） | ✅（待本单双签确认） | §2.1 |
| L2-2 矩阵读写等价/K14（T4-1/3/4） | ✅ | `matrix-finalize.json`（T4-1/3/4 PASS） |

## 4. 独立项（不纳入本单批准、但必须跟踪）

| 编号 | 事项 | 现状 | 处置 |
|:----:|------|------|------|
| K07-DPS-AUTH | DPS 认证/组织类 35 条豁免行字段不合规（`exempt_invalid=35`，缺 ticket/审批人/到期） | `k07-finalize.json` 2026-09-11 记录为 FAIL | 由 DPS 仓按 K07 统一契约补齐（ticket/approver/expires_at），单列整改；**不属 A 直连豁免行范围** |

## 5. 双签栏

> 签署即表示：确认 §2.1 的 A 直连豁免行与 K07 矩阵一致、豁免在有效期且有审批人；
> 同意 G4-T4-2 以「A 直连豁免行显式登记 + 双签」闭合。**任一签署方未签，G4 维持 No-Go。**

| 角色 | 职责 | 姓名 / 工号 | 结论（同意 / 有条件同意 / 不同意） | 签署日期 |
|------|------|-------------|-----------------------------------|----------|
| **技术签字**（OpenBase 架构组） | 确认豁免行与 K07 矩阵、L2-2 证据一致 |  |  |  |
| **发布签字**（OPS / 发布负责人） | 确认豁免在有效期、风险可接受、可发布 |  |  |  |

**有条件同意时的附加条件**（逐条列明，未满足则不生效）：

1.
2.

## 6. 生效、失效与复核

- **生效条件**：双签齐备且结论均为「同意」或「有条件同意（条件已闭环）」。
- **有效期**：至 **2026-12-31**（与豁免复核日一致）；到期前 30 天须复核续期。
- **立即失效**：任一豁免行新增/删除/变更、`GATE_EXEMPT_PATH_PREFIXES` 变更、
  豁免 ticket/审批人变更、或 L2-2 矩阵证据被后续运行态推翻。
- **复核责任**：OpenBase 架构组（技术面）+ OPS（发布面）。

## 7. 附件与引用

1. `doc/test/evidence/s7/gate/k07-finalize.json`（K07 真实导出终验）
2. `doc/test/evidence/s7/l2-2/matrix-finalize.json`（T4-1/3/4 判定）
3. `doc/test/evidence/s7/l2-2/read-path-ab-equivalence.json`
4. `doc/test/evidence/s7/l2-2/write-path-equivalence.json`
5. `doc/test/evidence/s7/l2-2/k14-idempotency.json`
6. OpenLLM `doc/design/OpenLLM-K07-端点过滤矩阵填报-v1.0.0.md`
7. OpenBase《OpenBase-端点过滤矩阵模板-v1.0》v1.0.1

---

**审批单状态**：[待签署]（双签完成后由编制人回写状态并同步清单 v1.2.0 → G4 结项）

# OpenBase-G4-T4-2 A 直连豁免行双签审批单-v1.2.0

| 项目 | 内容 |
|------|------|
| 审批单编号 | OB-GOLIVE-G4-T4-2-DS-v1.2.0 |
| 版本 | **v1.2.0** |
| 状态 | **[待签署]**（P8 前置核对完成：P7 全量门禁 `FAIL_DRIFT`，暂不具备签署条件；详见 §8.1） |
| 关联清单 | 《OpenBase-主备双通道生产上线必办事项清单-v1.5.0》G4（T4-2） |
| 关联处置记录 | 《OpenBase-主备双通道生产上线必办事项处置记录-v1.4.0》 |
| 关联判据 | S7-T4-2「管理面/探活 A 直连豁免行显式标注（与 K07 端点矩阵豁免行对账一致）」 |
| 关联矩阵 | OpenLLM `doc/design/OpenLLM-K07-端点过滤矩阵填报-v1.0.0.md`；OpenBase《端点过滤矩阵模板-v1.0》v1.0.1 |
| 关联证据 | `doc/test/evidence/s7/gate/k07-finalize.json`；`doc/test/evidence/s7/l2-2/matrix-finalize.json`；`read-path-ab-equivalence.json`、`write-path-equivalence.json`、`k14-idempotency.json` |
| 编制日期 | 2026-10-18 |
| 编制人 | OpenBase 架构组 |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次产出：G4-T4-2 A 直连/健康管理面豁免行清单、对账结果、判据核对与双签栏 |
| v1.1.0 | 2026-10-18 | OpenBase 架构组 | 增补 §5「A 直连豁免风险点」（R1~R8 风险清单、逐端点风险映射、控制措施与残余风险）与 §8「签署前机械核对项」；原 §5/§6/§7 顺延为 §6/§7/§9 |
| v1.2.0 | 2026-10-18 | OpenBase 架构组 | 回填 §8 签署前机械核对结果（7 项满足 / 1 项部分 / 2 项未留证）；新增 §8.1 P8 执行结论；§2.2 OpenMemory 豁免行按 `k07-finalize.json` 修正为 9；登记 P7 `FAIL_DRIFT`（16 个新增业务端点未注册） |

---

## 1. 审批范围（严格限定）

本审批单仅覆盖 **L2-2 通道矩阵中「管理面/探活 A 直连」豁免行**，即各子系统
`GATE_EXEMPT_PATH_PREFIXES`（`/health`、`/metrics`、`/docs`、`/redoc`、`/openapi.json`）
命中的端点行。**不覆盖**：

- 业务面端点（须有隔离用例，缺口/未覆盖清零，另行门禁）；
- DPS 认证/组织类豁免行（k07-finalize 显示 35 条豁免字段不合规，见 §4 独立项）；
- 任何写路径（写路径 A/B 等价已由 G4-T4-4 证据闭环）。

> §5 的风险分析同样**仅针对上述豁免行**，不构成对业务面端点的风险评估。

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
| OpenMemory | 9 | 9 | 0 | `k07-finalize.json`（openmemory 段） |
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

## 5. A 直连豁免风险点（v1.1.0 新增）

### 5.1 风险成因

`IdentityGate` 对豁免路径采取**前缀匹配 + 直接放行**：

```python
if path.startswith(GATE_EXEMPT_PATH_PREFIXES):
    # 健康/管理面 A 直连豁免（忽略身份头，K07 对账；不裁决不剥除）
    await self.app(scope, receive, send)
    return
```

见 OpenLLM `app/middleware/identity_gate.py`。其语义是：命中即**不做身份裁决、不剥除身份头**，
也不进入受信主体解析。该设计使健康/探活可在无主体上下文时被 A 直连调用，代价是这批端点
天然脱离 M2 身份强校验与主体级审计。

### 5.2 风险清单

| 编号 | 风险点 | 触发条件 | 影响 | 等级 | 现有控制 | 残余风险 / 签署前提 |
|:----:|--------|---------|------|:----:|---------|-------------------|
| **R1** | **身份旁路与前缀误命中** | 前缀匹配（非精确匹配）；未来在 `/health*`、`/metrics*` 等前缀下新增路由会被**静默纳入豁免** | 新业务端点意外脱离强校验，形成未登记的身份旁路 | **高** | 豁免集合单点定义（`GATE_EXEMPT_PATH_PREFIXES`）；K07 对账覆盖当前端点集 | 当前端点集无越界路由；**须**在发布门禁执行「豁免前缀 ↔ 审批单登记项」机械 diff；新增路由须重跑 K07 |
| **R2** | **端点与 Schema 测绘** | `/openapi.json`、`/docs`、`/redoc` 无认证可达 | 攻击面完整暴露（OpenLLM 351 端点 / 278 路径），加速定向攻击与参数构造 | **高** | 仅内网部署为既定前提；A 直连经 OpenBase 代理 | **须**生产关闭 `/docs`、`/redoc`，`/openapi.json` 限制内网 ACL；否则不得签「同意」 |
| **R3** | **指标数据泄露** | `/metrics` 无认证可达 | 暴露请求量、错误分布、依赖延迟、实例拓扑；若指标含 path/tenant 标签则进一步泄露租户信息 | **中** | 指标不落主体身份；部署侧内网 | **须** `/metrics` 网络 ACL 或专用只读 token，并确认指标标签不含租户/主体标识 |
| **R4** | **健康信息泄露与探活伪造** | `/health` 返回组件状态、依赖可达性、版本号 | ①对外泄露内部依赖拓扑与版本；②不可信来源可高频探活，影响通道状态机对 B/A 可用性的判断 | **中** | `channel_report` / `bypass_orchestration` 为机读结论；`auto_failover` 默认关闭 | 建议健康聚合结果仅对受信来源返回明细，非受信来源仅返回 `status` 粗粒度；探活来源加白名单 |
| **R5** | **审计归因缺失** | 豁免行不进入受信主体解析 | 审计日志与 `channel_report` 中该类请求无主体归属，异常探测无法归因到租户/用户 | **中** | `AuditMiddleware` 先于 `IdentityGate` 执行，仍记录请求与来源 | 建议豁免命中记 WARN + 来源 IP + `request_id`（不落身份）；监控侧建立调用量基线 |
| **R6** | **豁免集合配置漂移** | `GATE_EXEMPT_PATH_PREFIXES` 被修改或新增 | 豁免面自动扩大，审批单 §2.1 与实际不符，且无运行时告警 | **中** | 本单 §7「立即失效」条款；K07 可复跑 | **须**将 §8 机械核对纳入发布门禁；前缀变更须走同一审批单重签 |
| **R7** | **到期失效失控** | 2026-12-31 到期后未复核 | 豁免在无有效审批状态下继续生效 | **中** | §7 约定 30 天前复核 | 目前**无自动化到期拦截**；须配置到期告警，或由门禁在到期后 fail-closed |
| **R8** | **无认证探活的资源滥用** | 无身份强制的 `/health`、`/metrics` 被高频调用 | 探活本身轻量，但高频请求可放大依赖探测与日志写入 | **低** | 网关层限流（如启用）；内网部署 | 建议对豁免路径设独立限流阈值 |

### 5.3 逐端点风险映射

| 端点 | 暴露内容 | 主要风险 | 必需控制 |
|------|---------|---------|---------|
| `/health` | 组件状态、依赖可达性、版本 | R4、R5、R8 | 非受信来源返回粗粒度；来源白名单；调用量告警 |
| `/metrics` | 请求量、错误率、延迟、实例信息 | R3、R5、R8 | ACL / 专用 token；标签脱敏；独立限流 |
| `/docs` | 交互式 API 文档 | R2 | 生产关闭 |
| `/redoc` | 交互式 API 文档 | R2 | 生产关闭 |
| `/openapi.json` | 全量端点 + Schema | R2 | 内网 ACL；禁止公网 |

### 5.4 控制措施状态

**已具备（仓库侧可验证）**

1. 豁免集合单点定义于 `GATE_EXEMPT_PATH_PREFIXES`，K07 矩阵与其同源对账（单测 `test_exempt_prefixes_aligned_with_identity_gate` 守护）
2. `k07-finalize.json`：四子系统 `exempt_invalid=0`（DPS 认证类单列 §4）
3. L2-2 读写等价 + K14 幂等证据闭环（T4-1/3/4 PASS）
4. A 通道**只读**，写请求 403 属设计预期，不产生脏数据
5. 前端不直连三基础设施，统一经 OpenBase 代理

**签署前必须满足（OPS 提供证据，缺一不得签「同意」）**

1. 三基础设施与 OpenLLM 仅内网监听（或安全组/ACL 白名单），无公网入口
2. 生产环境 `/docs`、`/redoc` 已关闭
3. `/metrics` 已配置网络 ACL 或专用只读 token
4. 豁免路径调用量告警已配置（基线 + 阈值）
5. 豁免到期（2026-12-31）告警已配置

**建议（不阻断签署，纳入跟踪）**

1. 健康聚合对非受信来源降级为粗粒度返回
2. 豁免命中记 WARN（来源 IP + `request_id`）
3. 豁免路径独立限流
4. `GATE_EXEMPT_PATH_PREFIXES` 改为精确匹配或增加路由注册期断言

### 5.5 风险结论

- 在 §5.4「签署前必须满足」5 项全部留证的前提下，本豁免行残余风险为 **中**，可接受；
- 任一项未满足，残余风险升为 **高**，签署方**不得**给出「同意」，最多「有条件同意」并明确条件闭环时间；
- R1/R6 属结构性风险，不随部署环境改变，须以机械核对长期守护。

## 6. 双签栏

> 签署即表示：确认 §2.1 的 A 直连豁免行与 K07 矩阵一致、豁免在有效期且有审批人；
> 已阅读 §5 风险分析，并确认 §5.4「签署前必须满足」各项已留证；
> 同意 G4-T4-2 以「A 直连豁免行显式登记 + 风险明示 + 双签」闭合。
> **任一签署方未签，或 §5.4 前置项未留证，G4 维持 No-Go。**

| 角色 | 职责 | 姓名 / 工号 | 结论（同意 / 有条件同意 / 不同意） | 签署日期 |
|------|------|-------------|-----------------------------------|----------|
| **技术签字**（OpenBase 架构组） | 确认豁免行与 K07 矩阵、L2-2 证据一致；确认 §5 风险分析与控制措施技术成立 |  |  |  |
| **发布签字**（OPS / 发布负责人） | 确认 §5.4 前置控制已留证、残余风险可接受、可发布 |  |  |  |

**有条件同意时的附加条件**（逐条列明，未满足则不生效）：

1.
2.

## 7. 生效、失效与复核

- **生效条件**：双签齐备且结论均为「同意」或「有条件同意（条件已闭环）」。
- **有效期**：至 **2026-12-31**（与豁免复核日一致）；到期前 30 天须复核续期。
- **立即失效**：任一豁免行新增/删除/变更、`GATE_EXEMPT_PATH_PREFIXES` 变更、
  豁免 ticket/审批人变更、§5.4 前置控制失效、或 L2-2 矩阵证据被后续运行态推翻。
- **复核责任**：OpenBase 架构组（技术面）+ OPS（发布面）。

## 8. 签署前机械核对项（2026-10-18 回填）

| # | 核对项 | 结果 | 证据 |
|:-:|--------|:----:|------|
| 1 | `GATE_EXEMPT_PATH_PREFIXES` 与 §2.1 五项逐一相等（集合 diff 为空） | ✅ | `verify_exempt_endpoints.py`：`code_routes` 与 `registry_routes` 均为 `/docs,/health,/metrics,/openapi.json,/redoc` |
| 2 | `k07-finalize.json` 状态 `PASS`，四子系统 `exempt_invalid=0` | ✅ | `s7/gate/k07-finalize.json`：openbase 1/1、openrag 10/10、openmemory 9/9、openllm 5/5，DPS 35 单列 |
| 3 | `matrix-finalize.json` 中 S7-T4-1/3/4 均为 `PASS` | ✅ | `s7/l2-2/matrix-finalize.json`（T4-2 仍 PENDING，由本单闭合） |
| 4 | 三基础设施 + OpenLLM 监听地址/安全组证据（无公网入口） | ⚠️ 部分 | `p6-network.json`/`p6-firewall.json`：8001/8020 回环绑定、Domain/Private/Public 已启用且默认入站 Block；OpenRAG/DPS 目标环境待 OPS |
| 5 | 生产 `/docs`、`/redoc` 关闭证据 | ✅ | `p3-startup.json`：`/docs=404`、`/openapi.json=404` |
| 6 | `/metrics` 访问控制证据（ACL 或专用 token） | ✅ | `p5-prometheus.json`：无 token 401、Bearer/X-Metrics-Token 200、Prometheus target UP |
| 7 | 豁免路径调用量告警配置截图/配置片段 | ❌ 未留证 | 需 OPS 提供告警规则与阈值 |
| 8 | 豁免到期（2026-12-31）告警配置截图/配置片段 | ❌ 未留证 | 代码侧已实现到期 fail-closed（H7）；告警规则待 OPS 配置 |

### 8.1 P8 执行结论

1. **P7 全量门禁**：`FAIL_DRIFT`。当前代码实时导出 367 操作，较 2026-09-11 基线新增 16 个未注册隔离用例的业务端点（writeback / prompt assembly / trace export），与豁免行无关，但 AC-T12-2 门禁拒绝。
2. **豁免面判据**：全部满足（§8 第 1/2/3/5/6 项）。
3. **未留证项**：第 4 项目标环境网络证据（部分）、第 7/8 项告警配置（缺失）。
4. **结论**：**暂不具备双签条件**，审批单维持 `[待签署]`。需先完成「16 个新端点注册 + 矩阵 v1.3.0 复跑」与「告警配置留证」，再由技术与发布签字人签署。

详见《OpenBase-P7-K07终验报告-v1.0.0》§6 处置选项 A/B。

## 9. 附件与引用

1. `doc/test/evidence/s7/gate/k07-finalize.json`（K07 真实导出终验）
2. `doc/test/evidence/s7/l2-2/matrix-finalize.json`（T4-1/3/4 判定）
3. `doc/test/evidence/s7/l2-2/read-path-ab-equivalence.json`
4. `doc/test/evidence/s7/l2-2/write-path-equivalence.json`
5. `doc/test/evidence/s7/l2-2/k14-idempotency.json`
6. OpenLLM `doc/design/OpenLLM-K07-端点过滤矩阵填报-v1.0.0.md`
7. OpenBase《OpenBase-端点过滤矩阵模板-v1.0》v1.0.1
8. OpenLLM `backend/app/middleware/identity_gate.py`（豁免判定实现）
9. OpenLLM `backend/app/identity/channel.py`（`bypass_orchestration` 判定）

---

**审批单状态**：[待签署]（P8 前置核对完成；待 P7 门禁清零与告警留证后由双签人签署，再同步清单 v1.5.0 → G4 结项）

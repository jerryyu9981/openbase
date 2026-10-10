# OpenBase-五系统多租户与授权集成总览与续接指南-v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）及四套自研后端系统（OpenLLM / OpenRAG / OpenMemory / DPS） |
| 文档编号 | OB-DESIGN-MTAUTH-OVERVIEW-v1.0.0 |
| 文档版本 | **v1.0.3**（文件名版本＝首次定稿版本；内容版本以本字段与修订历史承载） |
| 状态 | **[Review]**（本文为**汇总视图**，不引入新结论；一切结论以其上游单一事实源为准） |
| 作者 | AA/PM-OpenBase-Dev |
| 创建日期 | 2026-10-09 |
| 存放 | doc/design/ |
| 定位 | 面向「**后续迭代**」与「**新系统接入**」的总览与续接指南：一页看懂五系统的多租户与授权集成方案、契约、落地情况与未决项 |
| 上游单一事实源 | 《OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0》（台账，内容版本 **v1.9.4**）；《OpenBase-协议头规范-v1.1》；《OpenBase-统一身份与主备双通道贯通总体方案-v1.0.0》；《OpenBase-统一身份最小特征集与隔离模型设计-v1.0.0》；《OpenBase-四维身份透传契约-v1.1.0》；《OpenBase-R387-跨域租户码对齐设计与收口实施记录》 |
| 边界 | 本文**不改写**上游台账结论；若与上游冲突，以上游为准。台账 §9.1 为派单分发时快照，行状态请以 §5.1 / §10.3 的**回填值**为准 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.3 | 2026-10-09 | AA/PM-OpenBase-Dev | 状态刷新：§4.1 批次表 C3 由「未实施」更新为「**第一阶段（契约与登记）已完成**」；§7.1 未决项 7 同步；新增契约制品 `config/identity_exemptions.json`（豁免治理单一事实源） |
| v1.0.2 | 2026-10-09 | AA/PM-OpenBase-Dev | 状态刷新：§4.1 批次表 C4/C5 由「已写入规范、未落地」更新为「**OpenLLM 已落地**」；§7.1 未决项 4/5 同步；登记 OpenLLM `daea828`（v2.16.3，23 passed） |
| v1.0.1 | 2026-10-09 | AA/PM-OpenBase-Dev | 状态刷新：§4.3 增补「强制期模块级灰度」开关行；§7.1 未决项 1 更新为「灰度机制已就位、实际翻转待运行环境」；登记 OpenLLM `6f06198`（v2.16.2，20 passed） |
| v1.0.0 | 2026-10-09 | AA/PM-OpenBase-Dev | 初始创建：五系统六维横评要点、三源模板与两段式架构、四批路线执行情况总览、接入契约清单与新系统接入 CheckList、未决项与后续迭代建议、风险与教训登记 |

---

## §1 一句话结论

集成形态定为「**中枢签发与准入 + 目标域细粒度裁决**」两段式：

> **OpenBase 作唯一身份权威与模块级准入；四仓作数据面细粒度裁决（档位 + 行控）。中间以「统一协议契约 + 统一码空间登记 + 统一错误码映射」连接。四仓不各自签发身份、不各自定义租户码语义。**

模板不选单一系统，采纳**三源模板**：

| 来源 | 贡献 | 采纳内容 |
|------|------|---------|
| **OpenMemory** | 授权与隔离维度最完整 | 授权模型主模板：RBAC + ABAC + 行控豁免治理 + 档位 + 双维行控 + 物理命名空间；**生产强制写成启动门禁** |
| **DPS** | 租户治理最完整 | 租户治理主模板：真实组织/租户表 + 存在与启停校验 + 码↔UUID 双形态规范化 + 401/403 语义 |
| **OpenBase** | 集成中枢 | 唯一身份权威 + 统一权限码体系 + 跨系统映射登记 + 唯一出站装配点 |

---

## §2 五系统现状横评（六维）

### 2.1 定位与短板（一句话）

| 系统 | 定位 | 主要短板（收口前） |
|------|------|-------------------|
| **OpenBase** | 集成与准入中枢（保留主导权） | `token_version` 吊销未强制、主体验证 DB 不可达 fail-open、入站头过渡期未退出 |
| **OpenLLM** | 欠账最多、优先收口 | **双套 RBAC 均未接线**（审计假象，P0）；主 JWT 无租户 claim；无租户标识不拒绝 |
| **OpenRAG** | 需补治理与接线 | **无租户注册表**；`RBACEngine` 未接线；无入站 JWT（靠网关） |
| **OpenMemory** | 授权主模板 | 无吊销能力；组织策略内存 + DB 双源有漂移风险 |
| **DPS** | 租户治理主模板 | `X-API-Key` 语义陷阱（非凭证）；无吊销；演示用户硬编码、无用户表 |

### 2.2 六维关键差异（浓缩）

| 维度 | 关键判读 |
|------|---------|
| **认证** | 仅 OpenBase 与 OpenMemory 具备「两种凭证叠加（AND）」与「吊销」；OpenRAG 连入站 JWT 都没有；**DPS 的 `X-API-Key` 不承担认证**（语义陷阱） |
| **受信入站** | **四仓是同构设计的多次落地**（同一白名单 + 四身份头 + 三开关），差异只在「生产是否强制」；**仅 OpenMemory 把生产强制写成启动门禁** |
| **多租户** | 事实源在 OpenBase（`tenants.code`），但**执行权威分散**；OpenRAG 无租户表；DPS 与 OpenBase 各有真表且**码空间隔离**（靠 `dps_code_map` 桥接，即 R-387 同源问题） |
| **授权** | **最大欠账 = 「存在但未接线的授权引擎」**（OpenLLM 两套、OpenRAG 一套）→ 审计误以为「有 RBAC」，实际路由仅管理员粗判（典型设计-实现偏差） |
| **失败语义** | 「过渡期 fail-open（忽略 + 标注 + WARN）」是四仓**有意过渡段**；风险在于**缺统一退出计划与生产门禁**；OpenMemory / DPS 的 fail-closed 倾向最强 |
| **数据模型与错误码** | 响应体：OpenBase / OpenMemory / DPS **三家同构**（`{code,message,detail,request_id}`）；OpenRAG / OpenLLM 各一套（短码 + 数值码）。**语义相同、字面量不同**，跨系统排障需归因矩阵 |

---

## §3 目标架构与设计原则

### 3.1 五条设计原则

| # | 原则 | 要点 |
|:-:|------|------|
| P1 | **单一身份权威** | 只有 OpenBase 签发主体；四仓只做「受信入站 + 本地档位解释」 |
| P2 | **协议契约唯一** | 四头 + 链路口 + 白名单 + 三开关为强制契约，默认值与生产强制统一 |
| P3 | **码空间登记唯一** | `tenants.code` 为唯一事实源；各目标域「可接受码 / 保留码 / 兜底码 / 映射」以**登记表**声明，**禁止散落字面量** |
| P4 | **两段式授权职责** | 网关侧做模块级准入（权限码 `module:action`）；目标侧做数据面细粒度裁决（档位 + 行控/所有权）；两侧共用同一「角色档位」语义 |
| P5 | **拒绝可观测统一** | 统一错误码命名空间 + 统一响应体 + 归因矩阵（网关码优先，上游 4xx/5xx 归上游） |

### 3.2 目标架构（四层）

```
L1 身份权威层（OpenBase 独占）
   · 凭证：本地 JWT / OIDC / ob_k_ 服务 Key / sk-agent-*
   · 主体模型：subject_type{user,agent,service,guest} + credential_type
   · 吊销：token_version（强制）+ agent key status + 生命周期状态机
   · 权限码权威：module:action + "*"；角色→权限映射（种子幂等）

L2 协议契约层（五系统共同遵守；OpenBase 为唯一出站装配点）
   · 四头 + X-Proxy-Source + X-Request-Id；白名单；strip/enforce/org-alias
   · 角色档位统一：readonly < readwrite < manage
   · 生产门禁统一：生产必须 enforce=True（照搬 OpenMemory 启动校验）

L3 码空间登记层（OpenBase 登记，目标域执行）
   · proxy_code_map{ target, source_of_truth, mappings[], accepted_codes,
                    reserved_codes, default_code }
   · 由 dps_code_map 通用化而来；R-387 的「按目标登记」并入此表

L4 数据面裁决层（各目标域自治，OpenBase 不越权）
   · 租户治理：租户注册表 + 状态（存在/启停）→ 照搬 DPS 语义
   · 数据面授权：档位守卫 + 行控 (tenant_code[, owner]) + 豁免治理
   · 目标域可保留自有 RBAC/ABAC，但【必须接线】
```

### 3.3 关键设计决策（D1~D6）

| # | 决策 | 结论 |
|:-:|------|------|
| D1 | 身份权威归属 | **OpenBase 独占**（各仓自治会导致主体语义分裂） |
| D2 | 授权职责划分 | **两段式**（网关全权会让网关须懂各域数据规则；目标域全权会缺模块级准入） |
| D3 | 租户治理模型 | **OpenBase 权威 + 目标域登记（同步）**（DPS 已真有表不能废弃；OpenRAG/OpenMemory 缺注册表需补） |
| D4 | 档位语义 | **统一档位 readonly/readwrite/manage + 登记式锚点表**（四仓已同构三档，只差统一锚点与线上接线） |
| D5 | 豁免治理 | **上升为通用机制**（票据 + 审批人 + 有效期 + 审计），与 OpenBase `k03_bypass_whitelist` 合并为一种 |
| D6 | 错误码统一 | **统一码 + 目标域短码映射表**（不改上游行为，避免跨仓破坏性变更） |

---

## §4 执行情况总览（截至 2026-10-09）

### 4.1 批次总览

| 批次 | 项 | 内容 | 状态 |
|:----:|:--:|------|:----:|
| **A** | A1 | `dps_code_map` 登记模式通用化为 `proxy_code_map`（保留码/兜底码/覆盖/校验单一入口） | ✅ 已完成 |
| **A** | A2 | R-387「按目标登记」并入 `proxy_code_map`，删除散落配置项 | ✅ 已完成 |
| **A** | A3 | 统一**角色档位锚点表**（登记式 JSON）供四仓消费 | ✅ 已完成 |
| **A** | A4 | 统一**错误码映射表**（对齐 R-384 归因矩阵） | ✅ 已完成 |
| **A** | A5 | 统一**协议契约与开关默认值**说明（含生产强制与过渡期退出计划） | ✅ 已完成 |
| **B** | B1 | **OpenLLM** 双 RBAC 收口：保留 DB RBAC 并接入路由；配置式 RBAC 显式 deprecated | ✅ 已闭环 · 已验收 |
| **B** | B1 配套 | 权限播种 + 影子期观测制品；**前置 DDL 与数据播种解耦**；播种制品**已在共享库执行完成** | ✅ 已闭环（2026-10-09） |
| **B** | B2 | **OpenRAG** `RBACEngine` 收口：**明确弃用而非接线**（消除「有引擎未用」假象） | ✅ 已闭环 |
| **B** | B3 | **四仓**统一档位锚点落地与线上接线 + 负向用例 | ⬜ **未启动**（随 B1 强制期推进） |
| **B** | B4 | **OpenBase** `token_version` 吊销生产强制；主体验证 DB 不可达按环境门控 | ✅ 已闭环 |
| **C** | C1-a | **OpenMemory** 组织码登记（`default` / `tenant-1` / `tenant-2`），统一码空间终态切换 | ✅ 已闭环 · 已验收（12/12 PASS） |
| **C** | C1-b | **OpenRAG** 配置驱动租户注册表 + 单一校验入口（不建表） | ✅ 已闭环 |
| **C** | C1-c | **OpenLLM** 缺租户标识不再静默回退 + 主 JWT 补 `tenant_code`（向后兼容） | ✅ 已闭环 |
| **C** | C1-d | 码值规范化统一（照搬 DPS 双形态解析 + 回填） | ⬜ 未实施（P2，待排期） |
| **C** | C2 | 码值规范化推广为通用能力 | ⬜ 未实施（随 C 批） |
| **C** | C3 | 豁免治理统一（票据+审批人+有效期，以 OpenMemory 为模板，与 `k03_bypass_whitelist` 合并） | 🟡 **第一阶段（契约与登记）已完成（2026-10-09）**：`config/identity_exemptions.json`（统一必填字段 + R1~R5 + 三实现映射与差距）；**查出 OpenBase k03 的 `expires_at` 为死字段**（条目永不失效）、且无 ticket/approver；第二/三阶段（OpenBase 收紧、各仓对齐）待批 |
| **C** | C4 | 生产门禁统一（生产必须 enforce / fail-closed 写成启动校验） | ✅ **OpenLLM 已落地（2026-10-09，`daea828`/v2.16.3）**：`get_settings()` 生产门禁（`ENV=production` 且 `ENFORCE_INBOUND_IDENTITY_HEADERS=false` → 拒绝），3 例用例；**其余三仓未落地**（OpenMemory 需口径对齐） |
| **C** | C5 | 过渡期退出计划（设定退出条件与版本） | ✅ **OpenLLM 已落地（2026-10-09）**：以 C4 生产门禁作为**机械截止手段**（生产即强制退出过渡态，规避「永久停留」）；规范 v1.1 §4.2 仍为通用口径，其余仓待各自批次 |
| **D** | D1 | 跨系统授权一致性矩阵（端点 × 主体 × 档位 × 租户 → 期望码） | ✅ 已完成 |
| **D** | D2 | 自动化门禁脚本（协议头/档位锚点/码空间/错误码映射一致性） | ✅ 已完成（复跑 0 FAIL，已纳入回归） |
| **D** | D3 | 负向用例集（匿名写/跨租户读/保留码入站/未受信带头/档位不足） | ⬜ **未启动** |

### 4.2 关键交付物与证据

| 项 | 交付物 / 证据 | 验证结论 |
|----|--------------|---------|
| A1/A2 | `openbase/settings.py`（内置基线 + `proxy_code_map` + 三纯函数）、`openbase/modules/protocol_headers/code_space.py`、编排器改声明 `OPENBASE_PROXY_CODE_MAP` | `ruff` 0 告警；全量回归 **1147 passed / 0 failed / 4 skipped**；行为等值（兜底值未变） |
| A3 | `config/role_tier_anchors.json`（含四仓现状与差异登记） | 被 D2 门禁静态校验 |
| A4 | `config/error_code_map.json`（11 条 + 归因规则） | 44 条字面量全部命中；首跑即抓出 6 条未核实值并修正为 `null` |
| A5 | `doc/design/OpenBase-协议头规范-v1.1.md` | 新增 §2.1 码空间登记 / §3.1 档位契约 / §4.1 生产门禁 / §4.2 过渡期退出计划 |
| B1 | OpenLLM `backend/app/identity/rbac_guard.py`（`require_permission` + 写类档位守卫 + 两段开关）、**15 个端点**接入、`edgerouter/auth/rbac.py` 弃用登记 | 端点级正负用例 **16 passed**（13 原有 + 3 通配护栏）；档位锚点与 `role_tier_anchors.json` 逐项一致 |
| B1 配套 | `doc/design/generated/rbac_seed_ddl.sql`（前置结构变更）、`rbac_seed.sql`（纯 DML）、`rbac_seed_manifest.json`；生成器 `scripts/rbac_permission_seed.py`；影子期观测 `scripts/rbac_shadow_observe.py` | 生成器 TDD 11 例 + `ruff` 全绿 + 重跑 diff=0；**已在共享库执行**：roles=5 / permissions=27 / role_permissions=34 / user_roles=0，幂等复跑新增 0 行 |
| B2 | OpenRAG `rbac_engine.py` 静态登记 `DEPRECATED` / `DEPRECATED_REASON` / `REPLACEMENT_PATH` + 类标记 `__deprecated__` | 11 例（含「请求路径零引用」护栏）；基线 failed/errors **47/40 → 47/40 零增长** |
| B4 | OpenBase 主体验证 DB 不可达**按环境门控** + `OPENBASE_PRINCIPAL_DB_DEGRADED_POLICY` + `token_version` 生产强制 | 全量 **1176 passed / 5 failed / 4 skipped**；生产误配 `allow` 拒绝启动 |
| C1-a | 编排器声明 `OPENMEMORY_RBAC__ORG_POLICIES`（**未改 OpenMemory 仓代码、未放宽其 fail-closed**）+ 本仓统一码空间终态切换 | **12/12 PASS**；受信入站 `tenant-1` 由 403 转 200；未登记码仍 403 |
| C1-b | OpenRAG 配置驱动租户注册表 + 单一校验入口 | 21 例；基线失败数零变化；保留码防护未放宽 |
| C1-c | OpenLLM 缺租户标识显式化 + 主 JWT 补 `tenant_code` | 16 例；复跑 B1 未破坏 |
| D1 | `config/auth_consistency_matrix.json`（17 格 × 6 系统 × 8 不变式） | 逐格标注 evidence 类型 |
| D2 | `scripts/cross_repo_auth_gate.py`（9 项检查） | **复跑 0 FAIL**；纳入回归 `tests/test_cross_repo_auth_gate.py`（4 例，无兄弟仓时自动跳过） |

### 4.3 生产门禁与两段推进口径（现状）

| 系统 | 影子/观察段 | 强制段开关 | 当前默认 |
|------|------------|-----------|---------|
| OpenLLM（B1） | `RBAC_PERMISSION_SHADOW`（只审计不拒绝，日志 `rbac_decision=would_deny`） | `RBAC_PERMISSION_ENFORCE` | SHADOW=**True** / ENFORCE=**False** |
| OpenLLM（B1 灰度） | 未纳入灰度白名单的模块仍走影子期 | **`RBAC_PERMISSION_ENFORCE_MODULES`**（灰度白名单；空=全部模块） | 默认**空**；建议顺序 `user → role → knowledge_base → conversation`；**单模块可独立回滚** |
| OpenBase（B4） | 非生产：allow + WARN + 留痕 | 生产：fail-closed 503 + 显式白名单 | `OPENBASE_PRINCIPAL_DB_DEGRADED_POLICY` 按环境推导 |
| 其余四仓 | 过渡期「忽略 + 标注 + WARN」 | 生产 enforce（C4 目标） | 仅 OpenMemory 已写成启动强制 |

> **代价提示**：B1 的强制期前置（DB 权限矩阵已播种 + **20 例**通过 + **模块级灰度机制**已就位）**已具备**，但**实际翻转尚未执行**（本机无运行中的 OpenLLM 服务、无影子期 `would_deny` 日志，出口门禁「消化率 100% 且无未归类调用方」无法判定）；开启属运行时变更，需单独批准。

---

## §5 接入契约清单（新系统接入必须消费）

> 新系统（第五仓及以后）只要遵循本节，即可与现有五系统对齐；**禁止各自另立一套**。

### 5.1 身份与链路协议（L2）

| 类别 | 契约 |
|------|------|
| **四身份头** | `X-User-ID` / `X-Tenant-ID` / `X-Org-ID` / `X-User-Role`（可选扩展 `X-Agent-Id`） |
| **链路口** | `X-Proxy-Source`（受信来源标识）/ `X-Request-Id`（透传全链路） |
| **受信来源常量** | `openbase-{llm,rag,memory,dps}-proxy`；编排器 `openbase-orchestrator` |
| **三开关** | `strip`（剥离入站身份头）/ `enforce`（强制校验）/ `org-alias`（组织别名）——**默认均 False** |
| **非受信带头默认行为** | 忽略 + 标注（`identity_headers_ignored`）+ WARN 放行 |
| **生产要求** | 生产**必须** `enforce=True`（照搬 OpenMemory `validate_*_policy` 启动校验）；误配拒绝启动 |
| **过渡期退出** | 「忽略 + 标注 + WARN」须设定退出条件与版本（协议头规范 v1.1 §4.2：**两个版本内强制**） |

### 5.2 角色档位（L2 / L4 共用）

- 档位序：**`readonly` < `readwrite` < `manage`**（写类方法要求 ≥ `readwrite`）。
- 锚点单一事实源：`config/role_tier_anchors.json`（新系统**只消费，不另立**）。
- 现网锚点：`admin → manage`；`org_admin → readwrite`；`user` / `org_member` / `viewer → readonly`。
- **未映射角色码必须 fail-closed**（403 `ROLE_UNMAPPED`），禁止静默降级 `readonly`。

### 5.3 权限码与失败语义（L1 / L4）

| 类别 | 契约 |
|------|------|
| 权限码口径 | **`module:action`**（如 `user:read` / `role:admin` / `conversation:write`）；管理类通配 `*` |
| 通配语义 | `*` **只在权限判定（G1）中作「放行全部」**，**不参与档位校验（G3）**——`readonly` 角色持 `*` 写仍 403 |
| 服务账号/匿名写 | 必须绑定主体；白名单外 fail-closed，统一码 `PERM_SERVICE_KEY_WRITE_DENIED` |
| 统一响应体 | `{code, message, detail, request_id}` |
| 错误码命名空间 | `AUTH_*` / `PERM_*` / `BIZ_*` / `SYS_*` / `PARAM_*` / `STORAGE_*` |
| 错误码映射 | `config/error_code_map.json`（目标域短码 ↔ 统一语义码 ↔ 归因层），**不改上游行为** |

### 5.4 租户与码空间（L3 / L4）

| 类别 | 契约 |
|------|------|
| 事实源 | `tenants.code`（OpenBase 为权威）；目标域**登记同步** |
| 登记方式 | `OPENBASE_PROXY_CODE_MAP` / `proxy_code_map{target, accepted_codes, reserved_codes, default_code, mappings[]}`——**禁止散落字面量** |
| 保留码 | 各目标域声明；**保留码必须拒绝**（如强校验期 400） |
| 兜底码约束 | **兜底码不得为该目标的保留码**，且须已被目标系统登记（不变式 I7） |
| 未知租户语义 | 照搬 DPS：**401 缺标识 / 403 组织不存在或停用**（不得静默回落） |
| 逐目标示例 | memory：`{default, tenant-1, tenant-2}`；llm / rag：保留码 `{default, openrag-local}` |

### 5.5 数据落点（共享基础设施实测口径）

> **局域网内共享基础设施为唯一数据库**：`192.168.0.151:5432/nuct`（PostgreSQL 14.23）。

| 系统 | 库/schema | 权限模型要点 |
|------|-----------|-------------|
| OpenBase | `openbase` schema | `roles`/`permissions`/`user_role`/`role_permission`；关联表键类型 **bigint** |
| OpenLLM | `public` schema | `roles`/`permissions`/`role_permissions`/`user_roles`；主键 **uuid**；`permissions` 四字段并存（`code`/`resource_type`/`action`/`scope`） |
| 第三方 | `platform` schema | 权限模型与上二者**互不相同** |

**跨系统数据变更纪律**（教训登记）：变更前**必须先核实目标表结构与库落点**；本次已就此把生成期**档案校验 + 落点断言**内置到播种生成器，使「写错 schema / 键类型不符」成为**生成期硬失败**。

---

## §6 新系统接入 CheckList

> 适用：第五仓及以后的任何自研后端系统。建议按序执行，每步产出可验证证据。

### 阶段一：受信入站与身份解释（L2）

- [ ] 接入**四身份头 + 链路口**，实现 `X-Proxy-Source` 白名单校验。
- [ ] 实现**三开关**（strip / enforce / org-alias），默认 `False`，并在日志中标注「忽略 + 标注 + WARN」。
- [ ] 实现**本地档位解释**：消费 `config/role_tier_anchors.json`，**未映射角色 fail-closed**。
- [ ] 生产环境**启用启动门禁**：生产必须 `enforce=True`，否则拒绝启动。

### 阶段二：租户治理（L3 / L4）

- [ ] 接入**租户注册表**（或订阅 OpenBase 权威源），实现「存在 + 启停」校验。
- [ ] 缺租户标识/未登记租户 → **显式 401/403**，**禁止静默回落保留码**。
- [ ] 声明本目标的**保留码 / 兜底码 / 可接受码**，登记到 `proxy_code_map`（禁止散落字面量）。
- [ ] 兜底码不得为本目标保留码（不变式 I7）。

### 阶段三：授权接线（L4，**必须真实接线**）

- [ ] 选定**一套**授权引擎并**接入请求路径**（另存的一套必须显式弃用登记：`DEPRECATED` + 替代路径）。
- [ ] 路由挂载权限码判定（`module:action`），覆盖**受保护端点 100%**。
- [ ] 写类方法叠加**档位守卫**（≥ `readwrite`）。
- [ ] 服务账号/匿名写 fail-closed（`PERM_SERVICE_KEY_WRITE_DENIED`）。
- [ ] 端点级**正负用例**（有码 2xx / 缺码 403、readonly 写 403、未映射 403），断言**非软断言**。
- [ ] 两段推进开关（影子期 → 强制期），影子期输出「将被拒」结构化日志。

### 阶段四：契约对齐与门禁

- [ ] 统一响应体 `{code, message, detail, request_id}`；错误码按命名空间，并在 `config/error_code_map.json` 登记映射。
- [ ] 纳入跨仓静态门禁 `scripts/cross_repo_auth_gate.py`（协议头/档位锚点/码空间/错误码映射 9 项检查）。
- [ ] 补**负向用例集**（匿名写 / 跨租户读 / 保留码入站 / 未受信带头 / 档位不足）。
- [ ] 授权接线覆盖率写入设计评审；D1 一致性矩阵**零「未定义」格**。

---

## §7 未决项与后续迭代建议

### 7.1 未决项（按优先级）

| # | 项 | 建议时机 | 阻塞关系 |
|:-:|----|---------|---------|
| 1 | **B1 强制期开启**——前置**已具备**（权限矩阵已播种 + 20 例通过 + **灰度机制已就位**：`RBAC_PERMISSION_ENFORCE_MODULES`，OpenLLM `6f06198`/v2.16.2） | 先跑影子期至消化率 100%，再按 `user → role → knowledge_base → conversation` **逐模块开强制**（单模块可独立回滚） | ⚠️ **待运行环境**：本机无运行服务与影子期日志，翻转不可执行 |
| 2 | **B3 四仓档位锚点落地** + 负向用例 | 随 B1 强制期推进 | 依赖 A3 制品（已具备） |
| 3 | **D3 负向用例集**（五仓统一覆盖率） | 随 B3 一并收口 | 依赖 B3 |
| 4 | **C4 生产门禁落地**（各仓启动校验） | 🟡 **OpenLLM 已落地**（`daea828`/v2.16.3）；其余三仓待各自批次 | 规范已就绪（协议头规范 v1.1 §4.1） |
| 5 | **C5 过渡期退出**（两个版本内强制） | 🟡 **OpenLLM 已落地**（以 C4 门禁作机械截止）；其余仓待各自批次 | 规范已就绪（协议头规范 v1.1 §4.2） |
| 6 | **C1-d / C2 码值规范化**（DPS 双形态解析推广） | P2，待排期 | 无硬阻塞 |
| 7 | **C3 豁免治理统一**（票据+审批人+有效期） | 🟡 第一阶段✅（契约制品已产出）；第二/三阶段待批 | 以 OpenMemory 豁免为模板 |
| 8 | **DPS 自身 IAM 演进**（吊销 / 用户表 / `X-API-Key` 语义澄清） | 其版本规划排期 | 依赖 OpenBase 总线 |
| 9 | **OpenMemory 组织策略双源漂移**（内存 `_org_registry` + DB 表） | 另批 | P1 |

### 7.2 迭代建议

1. **先收口强制期，再扩面**：B1 强制期是当前收益最大的动作（消除「有 RBAC 不生效」的审计假象），且前置条件已全部具备。
2. **门禁先行**：任何新增仓/新增端点，先过 `cross_repo_auth_gate.py` 与 D1 矩阵，避免契约再次漂移。
3. **契约变更走登记**：凡涉及头名/档位/码空间/错误码，**必须改登记表并过门禁**，禁止仓内硬编码。
4. **过渡态必须有截止**：任何「忽略 + WARN」的兼容分支都要写退出条件与版本（C5），否则会永久停留。
5. **跨系统写操作前先探明落点**：沿用「先侦察后执行」纪律（已内置为生成期硬失败机制）。

---

## §8 证据与索引

| 主题 | 首选查阅 |
|------|---------|
| 台账（唯一事实源，内容版本 v1.9.4） | 《OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0》§1 结论 / §2 六维比对 / §3 模板选型 / §4 架构 / §5 差距 / §6 四批路线 / §7 裁定 / §9 派单台账 / §10 跨仓实施记录 |
| B1 派单与回执（含播种交付与执行回执） | 《OpenBase-B1派单-OpenLLM授权接线-v1.0.0》§6.2 / §6.3 |
| 播种执行前置与决策点 D1~D4 | 《OpenBase-B1-播种SQL评审与执行预检说明-v1.1.0》 |
| 生产化配套（播种 + 影子期观测） | 《OpenBase-B1-生产化配套-权限播种与影子期观测-v1.2.0》 |
| 协议契约（头/档位/门禁/退出计划） | 《OpenBase-协议头规范-v1.1》 |
| 派单件 | `doc/planning/OpenBase-C1派单-租户注册表对齐-v1.0.0.md` |
| 机械可校验制品 | `config/role_tier_anchors.json`、`config/error_code_map.json`、`config/auth_consistency_matrix.json`、`scripts/cross_repo_auth_gate.py` |
| 播种制品 | `doc/design/generated/rbac_seed_ddl.sql`、`rbac_seed.sql`、`rbac_seed_manifest.json`；目标仓镜像 `OpenLLM/backend/scripts/rbac_seed/` |

---

## §9 风险与教训登记

### 9.1 已知风险

| # | 风险 | 等级 | 缓解 |
|:-:|------|:----:|------|
| R1 | 跨仓改造工期不可控（各仓各自立项） | 高 | A/D 批本仓可独立交付；B/C 批拆到单仓最小可交付单元 |
| R2 | 强制 fail-closed 后暴露存量「无档位/无租户」调用方 | 高 | 先影子期（只审计不拒绝）→ 再强制；保留带有效期的豁免白名单 |
| R3 | 统一码空间触发数据可见性变化（R-387 已实测：`default` 桶不可达） | 中 | 逐目标登记 + 后果登记 + 一键回滚（已有先例） |
| R4 | 错误码映射表与上游实际码漂移 | 中 | D2 门禁静态校验 + 上游 `detail` 契约 |
| R5 | RBAC 收口改动既有行为 | 中 | 先补负向用例与影子观测，再切换 |

### 9.2 教训登记（可复用的工程纪律）

| # | 教训 | 规则化 |
|:-:|------|--------|
| L1 | **配置源优先级**：`.env` 优先于代码默认值，改默认值而未改 `.env` 会导致验收失败 | 凡 `Settings` 默认值变更，**必须同时检索并修改 `.env*` 同名覆盖项**；`config_default` 类变更的验收须含「有效值断言」（读实例值） |
| L2 | **跨系统数据变更前必须核实目标表结构与库落点** | 生成器内置**档案校验 + 落点断言**，使错 schema / 键类型不符成为**生成期硬失败** |
| L3 | **`pg_constraint` 不含索引型唯一约束** | 核查 `ON CONFLICT (col)` 前提时须查 `pg_indexes`（`ix_roles_code` / `ix_permissions_code` 即为索引型唯一约束），勿据 `pg_constraint` 误判为「缺失」 |
| L4 | **窄口径验证会掩盖整组失败** | 凡触及鉴权主链路的改动，验收**必须以全量回归为判据**，不得以筛选后的子集宣称通过 |
| L5 | **测试环境机制先查仓内既有约定** | 本仓 `OPENLLM_TEST_EXTRAS` 早已预留 cp313 原生扩展目录，无需外部造环境 |

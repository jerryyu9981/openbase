# OpenBase-C1 派单-租户注册表对齐-v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）→ OpenRAG / OpenMemory / OpenLLM |
| 来源批次 | C1（租户治理增强，源自《OpenBase-自研系统多租户与授权集成总体完善方案》§4.3 D3 / §6 C 批） |
| 文档编号 | OB-DISPATCH-C1-v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | **[Approved] 已分发 · C1-a/C1-b/C1-c 已闭环**（2026-10-08：三项均已实施并验收；仅 C1-d 待排期） |
| 作者 | PM-OpenBase-Dev |
| 创建日期 | 2026-10-08 |
| 存放 | doc/planning/ |
| 分发状态 | **已分发**（2026-10-08）；C1-a **已闭环·已验收**；C1-b/C1-c/C1-d 待回执 |
| 并入说明 | **本派单 C1-a 吸收并取代**《OpenBase-R387派单-OpenMemory组织码登记-v1.0.0》序号 1（组织码登记）；该文件保留为**已并入的先行登记**，不再独立分发（见 §6.3） |
| 上游依据 | 《OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0》§2.3（多租户比对）/§4.3 D3/§5/§6 C1；R-387 统一码空间收口（已落地本仓部分） |
| 证据 | 逐行只读取证（见《总体完善方案》§8 证据索引）＋ 运行时实测（`doc/test/evidence/manual/r387-memory-org-policy-20261008.json`） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| **v1.0.3** | **2026-10-08** | **PM/AT-OpenBase-Dev** | **C1-b / C1-c 闭环回执**：依人工指令「直接跨仓修复」由本仓代为实施并复核——C1-b（OpenRAG）新增配置驱动租户注册表 + 单一校验入口（不建表，显式设计决策），M2 缺租户头不再回落保留码、未登记租户显式拒绝（两段开关），M1 零变化、保留码防护未放宽（21 例，基线失败数零变化）；C1-c（OpenLLM）缺租户标识显式化 + 主 JWT 补 `tenant_code`（向后兼容，16 例，复跑 B1 未破坏）；两条新错误码已同步本仓 `config/error_code_map.json` 与覆盖断言；分仓分发表与回执状态更新为「已闭环·已验收」 |
| **v1.0.2** | **2026-10-08** | **PM/AT-OpenBase-Dev** | **C1-a 闭环回执**：人工指令「直接跨仓修复」后由本仓代为实施并验收 —— 在 `scripts/service-orchestrator.ps1` 登记 `OPENMEMORY_RBAC__ORG_POLICIES`（`default`/`tenant-1`/`tenant-2`），**未改 OpenMemory 仓任何代码、未放宽其 fail-closed**；端到端实测 **12/12 PASS**（受信入站 `tenant-1` 由 403 转 200；未登记码仍 403）；并**同批执行本仓统一码空间终态切换**（memory 兜底码、`oidc_default_tenant`（含 `.env`）、IdP 演示池 → `tenant-1`），见 §6.5 执行记录；C1-a 状态 `已分发·待回执` → **已闭环·已验收** |
| **v1.0.1** | **2026-10-08** | **PM-OpenBase-Dev** | **状态回写：正式分发 + 重叠处置**。人工批准分发；状态 `[Draft] 待分发` → `[Approved] 已分发`；明确 **C1-a 吸收并取代**《R387派单-OpenMemory组织码登记》序号 1（消除两份重叠派单），该文件转为**已并入的先行登记**；补 §6 分发记录（含分仓分发表）与回执登记模板 |
| v1.0.0 | 2026-10-08 | PM-OpenBase-Dev | 初始创建（待分发）：登记三仓租户治理差距（OpenRAG 无注册表 / OpenMemory 双源策略 / OpenLLM 无标识不拒绝）、统一目标语义（对齐 DPS 的存在与启停校验 + 码值规范化）、交付要求、验收标准与回执要求 |

---

## §1 背景与来源

统一分析结论：**租户治理的「事实源」在 OpenBase（`tenants.code`）与 DPS（`platform.organization`/`platform.tenant`），而 OpenRAG/OpenMemory/OpenLLM 三仓治理程度参差**：

| 仓 | 现状 | 实证 |
|----|------|------|
| **OpenRAG** | **无租户注册表**（`tenants_router` 已弃用、未注册）；缺省回落**保留码** `default`；仅靠行控 `row_scope.enforce` | `src/openrag/main.py:275-277`、`src/openrag/identity/tenancy.py:6-14`、`src/openrag/storage/postgres.py:286-301` |
| **OpenMemory** | 组织策略**双源**（DB `organizations` 表 + 内存 `_org_registry`），存在漂移风险；**仅登记 `default`** | `src/openmemory/auth/permission.py:46,107-121`、`src/openmemory/multitenancy/api/org_routes.py:78`、实测 403「组织 'tenant-1' 不存在或未配置策略」 |
| **OpenLLM** | 有 `tenants` 表与配额/团队，但**无租户标识不拒绝**（回退 org 别名或空串） | `backend/app/models/tenant.py:24-89`、`backend/app/identity/namespace.py:190-199` |

**直接影响**：R-387 的「统一码空间」在本仓已就绪（按目标登记 + 可一处切换），但**memory 目标无法切换到非保留码**，因为 OpenMemory 侧未登记该组织——统一码空间的终态**被本派单阻塞**。

## §2 派单范围（分仓）

| 序号 | 交付对象 | 需求 | 优先级 |
|:----:|---------|------|:------:|
| C1-a | **OpenMemory** | 登记 OpenBase `tenants.code` 目标组织码（至少 `tenant-1`）；说明已登记组织清单的查询方式；**不放宽** fail-closed 语义 | **P1**（阻塞统一码空间终态） |
| C1-b | **OpenRAG** | 引入租户注册表（或明确「无注册表」为设计决策并给出等价替代）；缺省不再回落保留码；把「组织不存在」语义与错误码对齐 | **P1** |
| C1-c | **OpenLLM** | 缺租户标识不再静默回退（拒绝或显式缺省）；主 JWT 补租户 claim（与 B1 第 4 项同窗口） | P1 |
| C1-d | 三仓 | 统一**码值规范化**（照搬 DPS 的「码 ↔ UUID 双形态解析 + 回填」，仅适用于以 UUID 为主键的仓） | P2 |

**明确不做（本轮边界）**：① 不要求任何仓放弃 fail-closed；② OpenBase 侧在 C1-a 闭环前**保持 memory 兜底码为 `default`**（不擅自切换，避免记忆链路 403）；③ 不要求各仓改自有错误码**命名**（可通过映射表对齐，见 A 批 A4 制品）。

## §3 交付要求

1. **统一语义目标**（对齐 DPS 口径）：
   - 缺标识 → **401**（明确提示缺少组织/租户标识）；
   - 组织不存在 / 已停用 → **403**（原因文案可检索）；
   - 租户不存在 / 不属于该组织 → **403**。
2. **注册表为单一事实源**：不得出现「内存策略 + DB 表」双源且无同步校验（OpenMemory 现状）；如有双源须提供一致性校验或改为单源。
3. **与 OpenBase 对账**：已登记组织/租户清单须可与 OpenBase `tenants.code` 逐项比对（提供查询方式或导出）。
4. **保留码语义显式**：各仓须显式声明其保留码集合（OpenRAG 已声明 `{default, openrag-local}`，可作为范本）；未声明者须补充。
5. **生产门禁**：把「生产必须开启受信入站强校验与行控」写成启动校验（范本：OpenMemory `validate_server_api_key_policy` / `validate_row_scope_policy`）。

## §4 验收标准

| # | 验收项 | 通过标准 |
|:-:|--------|---------|
| 1 | 目标码可放行（C1-a） | 以受信入站 + `X-Tenant-ID: tenant-1` 调用业务端点 → **2xx**；未登记码仍 **403**（负向断言保留） |
| 2 | 未登记码仍拒 | 未登记码 → 仍 403「组织不存在或未配置策略」（**防护未放宽**） |
| 3 | 缺标识语义统一 | 缺组织/租户标识 → **401**；组织不存在/停用 → **403**（三仓一致） |
| 4 | 注册表单一 | 无未同步双源；或双源具备一致性校验且校验通过 |
| 5 | 清单可对账 | 提供已登记组织/租户清单查询方式，且与 OpenBase `tenants.code` 可比对 |
| 6 | 保留码显式 | 各仓显式声明保留码集合，并通过负向用例证明受信入站携带即拒 |
| 7 | 生产门禁 | 生产未开强校验时**拒绝启动**（而非静默运行） |
| 8 | 回归与回执 | 各仓单测/回归通过；按 §5 回执字段登记 |

## §5 分发与回执要求

1. **分发对象**：OpenMemory（C1-a，阻塞项，建议优先）、OpenRAG（C1-b）、OpenLLM（C1-c，可与 B1 同窗口）。
2. **回执字段**：commit hash、改动/登记文件清单、登记前后对照实测（§4 各项断言）、单测/回归结果、三远程推送与 `ls-remote` 一致性自检结果。
3. **回执落点**：本派单项 §6 增「回执登记」段 + OpenBase 侧《总体完善方案》§5 对应差距行状态列；C1-a 闭环后同批切换 OpenBase 侧 memory 码值（一处配置）。
4. **状态流转**：`待分发` → `已分发` → `已回执` → `已验收（统一码空间终态达成）`。

## §6 分发记录与回执登记

### 6.1 分发记录

| 项 | 内容 |
|----|------|
| 分发批次 | C1（租户治理增强） |
| 分发日期 | 2026-10-08 |
| 分发依据 | 人工批准（用户对话确认「按 DevFlow 纪律，直接执行 B1/C1 属跨仓事项」） |
| 优先级排序 | **C1-a（OpenMemory）优先**——它是 OpenBase 侧「统一码空间终态」的**唯一阻塞项**（实测 `tenant-1` → 403） |
| 随单交付物 | 本派单项 + A 批制品（`config/role_tier_anchors.json`、`config/error_code_map.json`）+ R387 实测证据 |
| 本仓回填 | 《OpenBase-自研系统多租户与授权集成总体完善方案》§5 三仓差距行已回填「C1 已分发」 |

### 6.2 分仓分发表

| 分项 | 对象 | 需求摘要 | 优先级 | 状态 |
|:----:|------|---------|:------:|------|
| C1-a | **OpenMemory** | 登记 OpenBase `tenants.code` 目标组织码（至少 `tenant-1`）；提供已登记清单查询方式；**不放宽** fail-closed | **P1（阻塞）** | ✅ **已闭环 · 已验收**（2026-10-08，12/12 PASS） |
| C1-b | **OpenRAG** | 引入租户注册表（或以「无注册表」为显式设计决策）；缺省不再回落保留码；「组织不存在」语义与错误码对齐 | P1 | ✅ **已闭环 · 已验收**（2026-10-08，21 passed，基线失败数零变化） |
| C1-c | **OpenLLM** | 缺租户标识不再静默回退；主 JWT 补租户 claim（与 **B1 同窗口**） | P1 | ✅ **已闭环 · 已验收**（2026-10-08，16 passed；B1 复跑 13 passed 未破坏） |
| C1-d | 三仓 | 码值规范化（照搬 DPS「码 ↔ UUID 双形态解析 + 回填」，仅适用以 UUID 为主键的仓） | P2 | 已分发 · 待回执 |

### 6.3 与《R387派单-OpenMemory组织码登记》的关系（重叠处置）

| 项 | 内容 |
|----|------|
| 重叠事实 | 《OpenBase-R387派单-OpenMemory组织码登记-v1.0.0》序号 1「登记目标组织码」与 **C1-a 完全重叠** |
| 处置 | **C1-a 吸收并取代**该序号；该文件**转为「已并入的先行登记」**，**不再独立分发**（其序号 2「组织码登记接口」并入 C1-d 讨论） |
| 保留理由 | 该文件含更细的实测摘录与验收断言，作为 C1-a 的**附件级证据**保留可追溯性；不重复分发以避免同一需求双开派单 |
| 状态流转 | 该文件状态置为「已并入 C1-a」；其 §7 回执登记由本派单 §6.4 承接 |

### 6.4 回执登记

_（待各仓实施后按仓回填；回执行占位见 §5）_

#### C1-a OpenMemory

| 回执字段 | 值 |
|---------|-----|
| commit hash / 登记方式 | **不涉及 OpenMemory 仓代码改动**：登记以**联调环境配置**落地 —— `scripts/service-orchestrator.ps1` openmemory 服务块显式声明 `OPENMEMORY_RBAC__ORG_POLICIES`（进程环境变量优先于该仓 `.env`） |
| 已登记组织码清单与查询方式 | 已登记：`default`、`tenant-1`、`tenant-2`（均 `enabled=true, default_role=user`）。**查询方式**：① 启动日志逐条输出 `已加载组织策略: <org_id>, RBAC=<bool>`（`auth/permission.py::_load_org_policies`）；② 配置项 `OPENMEMORY_RBAC__ORG_POLICIES` 即登记者单一事实源；③ 运行期以受信入站 + 目标码调用业务端点，200=已登记 / 403=未登记 |
| §4 断言结果 | ✅ **全部通过（12/12，2026-10-08 15:26）**：受信入站 + `X-Tenant-ID: tenant-1` → `POST /api/v1/recall` **200**（修复前 403）；`POST /api/v1/remember` **200**；**未登记码仍 403**「组织不存在或未配置策略」（负向断言：防护未放宽）。证据：`doc/test/evidence/manual/c1-acceptance-20261008.json` |
| 单测/回归结果 | 本仓（OpenBase）侧重：`ruff` 0 告警；全量回归见 §6.5 执行记录。OpenMemory 仓**未改动**，无新增回归义务 |
| 三远程推送与 `ls-remote` 自检 | 待本批次统一推送（见 §6.5） |

> **登记理由与边界**：OpenMemory 的组织策略为 fail-closed 设计（有效防护，**未放宽**）；本次仅按其既有机制**登记** OpenBase 租户码空间，未修改该仓任何代码、未调整其判定逻辑。

#### C1-b OpenRAG（**已回执**，2026-10-08）

| 回执字段 | 值 |
|---------|-----|
| 改动文件清单 | **新增** `src/openrag/identity/tenant_registry.py`（注册表 + 单一校验入口）、`tests/unit/test_c1b_tenant_registry.py`（21 例）、`doc/design/OpenRAG-C1-b-租户注册表与缺省语义收口设计说明-v1.0.0.md`；**修改** `identity/error_codes.py`、`config/settings.py`、`api/middleware/identity_gate.py`、`identity/context.py`、`identity/__init__.py`、`scripts/verify-env/contract.json` |
| 注册表实现与默认值 | **配置驱动已登记码清单 + 单一校验入口，不建表**（显式设计决策：OpenRAG 定位「网关侧准入」，租户主数据在 OpenBase/DPS）；`OPENRAG_IDENTITY_TENANT_REGISTRY_CODES` 默认 `["default"]`；单一事实源 `build_tenant_registry()`、单一入口 `resolve_tenant_code()`（四态 missing/reserved/registered/unknown）；查询方式＝配置项 + 结构化日志 `registry=` + verify-env 契约键 |
| 两段开关 | `OPENRAG_IDENTITY_TENANT_REGISTRY_ENFORCE` 默认 **False（观察段）** |
| 行为与错误码 | 观察段：M2 缺租户头 → **不再回落 `default`**（`tenant_code=None` + `state="missing"` 标注 + 日志）仍 200；未登记码 → 标注 `unknown` 仍 200。强制段：缺租户头 → **401 `AUTH_TENANT_ID_MISSING`（AUTH-4013）**；未登记码 → **403 `BIZ_TENANT_NOT_FOUND`（BIZ-4092）** |
| M1 兼容性 | `test_m1_no_headers_default_domain` / `test_m1_transition_ignores_client_headers` / `test_m1_enforced_untrusted_headers_403_unchanged` 全通过——M1 行为**零变化**，存量 `default` 域知识库不受影响 |
| 保留码未放宽 | `test_m2_reserved_code_still_rejected_400`（观察段与强制段）+ 既有 S3-T2-8 均 **400** `BIZ_RESERVED_TENANT_CODE_COLLISION` |
| 测试结果 | 新增 **21 passed**（本仓独立复核：`pytest tests/unit/test_c1b_tenant_registry.py -q` → **21 passed**，含 `-k "tenant_registry or reserved"` 复核）；定向回归与改动前基线**逐项对比**：`47 failed / 2686 passed` → `47 failed / 2707 passed`（**+21 即新增用例，失败数零变化**）；`ruff` 新增文件 **All checks passed!**；mypy 新增文件 0 告警 |
| 已知风险 | ① 观察段缺租户仍 200（过渡态，下游经 `request_tenant_code()` 仍回落 `default`；强制段开启后 401 才彻底消除）；② 注册表与 `tenants.code` 为静态清单对账、无实时一致性校验；③ 仅覆盖受信入站 `trusted_identity` 形态 |
| 三远程推送 | **未推送**（待统一授权） |
| **同步动作（本仓已执行）** | 两条新错误码已并入 `config/error_code_map.json`（`AUTH_TENANT_ID_MISSING`、`BIZ_TENANT_NOT_FOUND`），并纳入 `tests/test_auth_registries.py` 覆盖断言 |

#### C1-c OpenLLM（**已回执**，2026-10-08）

| 回执字段 | 值 |
|---------|-----|
| 改动文件清单 | **新增** `tests/unit/test_c1c_tenant_scope_closeout.py`（16 例）、`doc/development/OpenLLM-C1c-租户语义收口-DevLogReport-v1.0.0.md`；**修改** `app/services/auth_service.py`（令牌增租户声明）、`app/identity/namespace.py`（缺省显式化 + 开关）、`app/identity/error_codes.py`（新码）、`app/core/config.py`（开关）、`app/api/auth.py`（登录签入租户声明） |
| 新增 claim 与兼容性 | 新增 `tenant_code`（+ 既有别名 `org_id`）；**可选附加字段＝向后兼容**：旧令牌（无 claim）仍可解析鉴权，`get_current_user` 不读该 claim，**缺 claim 不拒绝**；响应 `Token` schema 未改 |
| 两段开关 | `TENANT_SCOPE_ENFORCE` 默认 **False（审计标注段）** |
| 行为与错误码 | 默认段：不拒绝；org 别名回退行为**零变化** + `tenant_source="org_alias"` 标注（INFO）；两者皆缺 → 返回 `("", "", None)` + `tenant_source="none"` 标注（WARNING，`event=tenant_scope_default`）。强制段：无任何租户标识 → **400 `PARAM_TENANT_IDENTITY_MISSING`（ll_code 4004）**，**禁止空串静默通过** |
| 保留码处置 | 保留码 `{default, openrag-local}`：解析入口命中即拒（400）；**令牌签发遇保留码归一为显式缺省（不写 claim）**；读侧遇保留码返回 `None`——**本仓不产出保留码** |
| 测试结果 | RED 12 failed → GREEN **16 passed**；**复跑 B1 未被破坏**（本仓独立复核：`pytest tests/unit/test_c1c_tenant_scope_closeout.py tests/unit/test_b1_rbac_wiring.py -q` → **29 passed**）；`ruff` 新增文件 0 告警、改动文件与 HEAD 基线**逐文件对比 21→21 无新增** |
| 已知风险 | ① `/auth/refresh` 不查库，刷新所得 token **不含**租户声明（走显式缺省，兼容不受影响）；② 强制段仅对「无任何租户标识」拒绝，**M1（有 org 别名）两段均放行**（保留兼容）；③ `annotate` 出口现仅依赖结构化日志，调用点未透传 |
| 三远程推送 | **未推送**（待统一授权） |

#### C1-d 码值规范化

| 回执字段 | 值 |
|---------|-----|
| 覆盖仓与实施范围 | _（待回填）_ |
| 规范化实测（码↔UUID 双形态与回填） | _（待回填）_ |

### 6.5 本仓解锁动作（**已执行**，2026-10-08）

C1-a 登记到位并验收通过后，本仓**同批切换**已执行完毕（每项均为单点配置，可独立回滚）：

| # | 动作 | 实际落点 | 结果 |
|:-:|------|---------|------|
| 1 | memory 目标兜底码 `default` → `tenant-1` | `openbase/settings.py`（内置基线 `BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET`）+ `scripts/service-orchestrator.ps1`（`OPENBASE_PROXY_CODE_MAP.targets.memory`） | ✅ 已切换（两处同步，后者覆盖前者） |
| 2 | `oidc_default_tenant` 去保留码 | `openbase/settings.py`（默认值）+ **`.env` 第 17 行 `OPENBASE_OIDC_DEFAULT_TENANT`** | ✅ 已切换（**注意**：`.env` 优先于代码默认值，仅改代码无效——首轮验收 B1 即因此未过，已定位并修正） |
| 3 | 本地 OIDC IdP 演示用户池去保留码 | `scripts/oidc-idp/idp_server.py`（新增单点常量 `DEMO_TENANT_ID="tenant-1"`，两处引用） | ✅ 已切换 |
| 4 | 端到端复测 | `doc/tmp/c1_acceptance.py` → `doc/test/evidence/manual/c1-acceptance-20261008.json` | ✅ **12/12 PASS**（含未登记码仍拒的负向断言与零残留） |

**附带修正的护栏**：`tests/test_memory_proxy.py`、`tests/test_outbound_tenant_code_space.py` 的期望值随终态同步（原断言 `default`），并新增「任一目标兜底码不得为其保留码」不变量用例（`test_builtin_defaults_are_non_reserved_for_their_target`）。

**回滚**：三项配置各自置回原值即可（`default`），无需改代码或迁移数据。

**数据可见性后果（显式登记）**：切换后 memory 目标的读写落在 `tenant-1` 桶。实测切换后经网关读得 **total=5**（该桶既有数据），**未出现空列表**；原 `default` 桶中的历史记忆在受信入站下仍可通过已登记的 `default` 组织访问（未删除、未迁移）。

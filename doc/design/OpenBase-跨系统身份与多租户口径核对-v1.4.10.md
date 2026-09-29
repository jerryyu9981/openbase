# OpenBase 跨系统身份与多租户口径核对 - v1.4.10

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 文档版本 | v1.0.0 |
| 状态 | **[Review]（待设计评审）** |
| 版本号 | **v1.4.10**（承接型小版本：DPS 模板化能力对接深化） |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-09-29 |
| 触发 | **设计裁定 A-1410-02**（`X-Org-ID` 兼容别名收敛口径）—— 用户指示：「涉及多租户系统的设计问题，**以 OpenBase 侧为基准**，同时核对 **DPS、记忆（OpenMemory）、知识库（OpenRAG）** 侧各自做法，尽可能统一到 OpenBase 基准」 |
| 方法 | 四仓**代码级核对**（只报事实、附文件与行号；不臆测） |
| 存放 | `doc/design/` |

---

## 1. OpenBase 基准定义（单点事实源）

| 项 | 基准 | 证据 |
|----|------|------|
| **身份头** | 四头：`X-User-ID`／`X-Tenant-ID`／`X-Org-ID`／`X-User-Role`（＋ 委托/执行者标注，R-H1-1 校验集） | `openbase/modules/protocol_headers/constants.py:10-11,38` |
| **隔离键** | **`tenant_code` 单一隔离键** | 同上（org 不参与隔离） |
| **`X-Org-ID` 语义** | **退役兼容别名（OB-8）** —— 值 = `X-Tenant-ID`（tenant 同源）；兼容期可由**显式别名值映射**覆盖 | `constants.py:38`；`identity_context.py:47,139`；`inject.py:12-13` |
| **值映射能力** | `org_value_map` / `tenant_map`（`tenant_code → dps_org_id / dps_tenant_id`），**默认空表** | `protocol_headers/dps_code_map.py:48,245-252` |
| **一致性门禁** | 强模式开启且出站 `X-Org-ID ≠ X-Tenant-ID` → **403** | `inject.py:138` |
| **委托/执行者** | `identity_context` 含 `delegated`（委托时 `subject_id` 取委托主体） | `openbase/modules/dps_proxy/__init__.py:89-92` |

> **基准一句话**：**`tenant_code` 是唯一隔离维度；`X-Org-ID` 不是独立维度，而是 tenant 的（可映射的）别名。**

---

## 2. 四系统横向核对（代码级）

### 2.1 头集

| 系统 | 身份头 | 控制头 | 服务密钥头 | 与基准差异 |
|------|--------|--------|-----------|:----------:|
| **OpenBase（基准）** | `X-User-ID`／`X-Tenant-ID`／`X-Org-ID`／`X-User-Role` | `X-Proxy-Source`／`X-Request-Id` | — | — |
| OpenRAG | 上述四头 ＋ **`X-Agent-Id`**（身份头集 5 个） | 同上 | `X-API-Key` | ＋agent 头 |
| OpenMemory | 上述四头 ＋ **`X-Agent-Id`**（同 RAG） | 同上 | `X-API-Key` | ＋agent 头 |
| DPS | 上述四头 ＋ **`X-Agent-Id`**（身份头集 5 个） | 同上 | `X-API-Key` | ＋agent 头 |

> **结论**：头名 **四家完全一致** ✅；三家多了 `X-Agent-Id`（agent 主体场景）。

### 2.2 隔离语义与 org 定位（**核心差异所在**）

| 系统 | 隔离键 | `X-Org-ID` 定位 | org 是否独立维度 | 证据 |
|------|--------|-----------------|:----------------:|------|
| **OpenBase（基准）** | `tenant_code` | **退役别名**（=tenant） | ❌ 否 | `constants.py:38`；`inject.py:12-13` |
| OpenRAG | `tenant_code` | 写入独立字段 **`org_alias`**，**不作过滤键** | ❌ 否（默认） | `identity_gate.py:252,280`；`context.py:48`；`settings.py:297-300`（`enforce_org_alias` 默认 **False**，注释明确「S3 新隔离键一律 `tenant_code`」） |
| OpenMemory | `tenant_code` | **退役别名**（=tenant），回退顺序 `X-Tenant-ID → X-Org-ID` | ❌ 否 | `tenant_context.py:98,120-123`；`controllers.py:1184-1186` |
| **DPS** | `tenant_id` | **独立组织标识**，与 tenant **两级层次且两者均必填** | ✅ **是** | `ddl/schema_root.py:58-105`（`organization` ＋ `tenant(org_id→FK)`）；`tenant_middleware.py:157-169,282-314`；缺任一 → **401** |

> **结论**：**OpenBase／OpenRAG／OpenMemory 三家语义已一致**（org 非独立维度）；**DPS 是唯一偏离者**（org 独立、必填、参与"租户须归属组织"校验）。

### 2.3 默认值与保留码

| 系统 | 默认租户 | 保留码碰撞 | 证据 |
|------|----------|-----------|------|
| OpenBase | （沿用既有 proxy 口径） | 强模式不一致 → 403 | `inject.py:138` |
| OpenRAG | `default` | 受信 `X-Tenant-ID ∈ {default, openrag-local}` → **400** | `tenancy.py:6-21`；`identity_gate.py:228-239` |
| OpenMemory | `default` | `enforce_org_alias` 时不一致 → **403 `BIZ_ORG_ALIAS_MISMATCH`** | `inbound_gate.py:17`；`identity_gate.py:167-180` |
| DPS | 保留码 `{default, dps-local}`（M1 本地可用，M2 命中 → 400） | 同左 | `constants.py:46-47`；`tenant_middleware.py:174-176` |

### 2.4 principal 模型

| 系统 | principal 键 | effective | 委托 | agent |
|------|-------------|-----------|:----:|:-----:|
| OpenBase | subject／tenant（＋ org 别名位）／role | ✅ | ✅ **有**（`delegated`） | ✅ |
| OpenRAG | `subject_id`／`subject_type`／`tenant_code`／`role`／`auth_method`（**5 键**） | 4 键 | 恒 None | ✅ |
| OpenMemory | 同 RAG（**5 键**） | 同 | 恒 None | ✅ |
| **DPS** | 同 ＋ **`org_code`** ＋ **`proxy_source`**（**7 键**） | 5 键 | 恒 None | ✅ |

---

## 3. 统一方案（以 OpenBase 为基准）

### 3.1 基准条款（建议固化为跨系统身份口径）

| # | 条款 | 现状符合度 |
|:-:|------|-----------|
| **B1** | **`tenant_code` 是唯一隔离维度**；任何系统不得新增第二隔离键 | OpenBase／RAG／Memory ✅；**DPS 内部有 org 层次但不作对外隔离键**（其对外隔离仍按 tenant_id） |
| **B2** | **`X-Org-ID` 为 tenant 的兼容别名**，语义**不等于**独立组织维度 | OpenBase／RAG／Memory ✅；**DPS 偏离**（见 §3.2 处置） |
| **B3** | 头名与大小写统一为四头 ＋ `X-Agent-Id`（agent 场景）＋ 控制头两个 | **四家已一致** ✅ |
| **B4** | **别名一致性门禁**：强模式下 `X-Org-ID ≠ X-Tenant-ID` 应显式拒绝（403），不得静默 | OpenBase（403）／OpenMemory（403）✅；OpenRAG `enforce_org_alias` 默认关闭（可开） |
| **B5** | **真 org 值经映射表提供**（`org_value_map`），而非把 org 变成必填维度 | OpenBase 已具备 ✅ |

### 3.2 DPS 偏离的处置（**推荐：对外遵循基准，内部模型不动**）

| 方案 | 说明 | 评价 |
|:----:|------|:----:|
| A | 改造 DPS 去掉 org 必填与两级校验 | ❌ 破坏 DPS 既有 `organization/tenant` 数据模型与外键，成本高、风险大 |
| **B（推荐）** | **DPS 内部保留两级模型；对外接口由 OpenBase 侧 `org_value_map` 传真 org 值**（把"别名"填成 DPS 认可的真实 org），DPS 的必填与归属校验照常通过 | ✅ **零改造**、语义自洽（别名可映射是基准 B5 的既有能力） |
| C | 把 org 升格为四系统统一的第二维度 | ❌ 与三家现状冲突，违背"以 OpenBase 为基准" |

**方案 B 的落地要点**：
1. OpenBase 侧 `dps_proxy` 注入时，**优先取 `org_value_map[tenant_code]`**（命中则填真 org），未命中则回落 `= tenant_code`（现状）；
2. DPS 侧 `organization`／`tenant` 表须**预置对应记录**（联调前置）；
3. 保留强模式门禁（不一致 → 403）作为**防错**，但需确认其与映射机制不互斥。

### 3.3 本版（v1.4.10）动作

| # | 动作 | 类型 | 责任 |
|:-:|------|------|------|
| 1 | **核对 `org_value_map` 配置现状** —— ✅ **已实证：未配置**（`.env` 中 6 个相关键均缺失；配置源为 `settings.dps_code_map_entries()` ＋ `dps_org_map`／`dps_tenant_map`，见 `dps_proxy/__init__.py:96-113`）⇒ **列为联调前置**（§4-#1） | 联调前置 | AA / DO |
| 2 | 10 端点调用沿用既有四头注入口径，**不新增隔离键** | 设计遵从 | AA |
| 3 | 差异登记：DPS 的 `X-User-Role` 默认 `"user"`、principal 7 键；RAG／Memory 的 `enforce_org_alias` 默认值 | 文档留痕 | AA |
| 4 | **不本版收敛**：把"org 维度统一"作为**跨系统治理项**登记候选需求（若确需真实组织维度再立版本） | 范围纪律 | PM |

---

## 4. 风险与开放项

| # | 项 | 级别 | 说明 |
|:-:|----|:----:|------|
| 1 | **`org_value_map` 未配置** —— ✅ **已实证（2026-09-29）**：OpenBase `.env` 中 **6 个相关键全部缺失**（`DPS_ORG_MAP`／`DPS_TENANT_MAP`／`DPS_DEFAULT_ORG_ID`／`DPS_DEFAULT_TENANT_ID`／`ENFORCE_ORG_ALIAS`／`DPS_CODE_MAP`）⇒ 别名映射为**空表回落**，出站 `X-Org-ID` **= tenant 值** | **P1** | **联调前置**：由 OpenBase 侧配置 `dps_code_map`（或 `dps_org_map`／`dps_tenant_map`）给出 DPS 认可的**真实 org／tenant 值**，并预置 DPS `organization`／`tenant` 记录；**未配置则联调大概率 401／归属校验失败** |
| 2 | 强模式门禁与映射机制**互斥** —— ✅ **已确认（2026-09-29 读码）**：`inject.py:198-208` 中 `enforce_org_alias=True` 时**要求 `X-Org-ID == X-Tenant-ID`**（错误 hint 明确写「configure dps_code_map with **dps_org_id == dps_tenant_id**」）⇒ 与「传真 org」**互斥** | **P2 → 已升为设计约束** | **本版须保持 `enforce_org_alias=False`**（代码默认 False，`.env` 未设 ⇒ 当前即兼容段）⇒ **映射传真 org 方可生效**；若误开强模式，DPS 联调会因 `org ≠ tenant` **直接 403**。且 DPS 侧 org／tenant 本就是**不同 code**（演示码 `dps-org-001` vs `dps-tenant-001`）⇒「org == tenant」方案在 DPS 侧不可行，**只能走映射传真** |
| 3 | RAG／Memory 的 `enforce_org_alias` 默认关闭 ⇒ 别名不一致时**静默通过** | P2 | 与基准 B4「不得静默」有张力 ⇒ 登记候选需求（跨系统治理） |
| 4 | DPS 内部 org 层次 vs 基准单维度 | P2 | 已按 §3.2 方案 B 处置（对外遵循基准），**不改造其内部模型** |

---

## 5. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| **v1.1.0** | 2026-09-29 | **AA-OpenBase-Dev** | **`org_value_map` 配置现状实证**：查 OpenBase `.env` ⇒ **6 个相关配置键全部缺失**（`DPS_ORG_MAP`／`DPS_TENANT_MAP`／`DPS_DEFAULT_ORG_ID`／`DPS_DEFAULT_TENANT_ID`／`ENFORCE_ORG_ALIAS`／`DPS_CODE_MAP`）⇒ 别名映射为**空表回落**、出站 `X-Org-ID` = tenant 值。配置链路已定位：`dps_proxy/__init__.py:96-113` ← `settings.dps_code_map_entries()` ＋ `dps_org_map`／`dps_tenant_map`（`default_role="user"` 与 DPS 侧一致）。§3.3-#1 与 §4-#1 同步由「须实证」更新为「**已实证：未配置**」，并明确**联调前置**（配置真实 org／tenant 值 ＋ 预置 DPS `organization`／`tenant` 记录） |
| v1.0.0 | 2026-09-29 | AA-OpenBase-Dev | 初始创建（设计裁定 **A-1410-02** 落地）：**OpenBase 基准定义 6 项**（隔离键／org 别名语义／值映射／一致性门禁／委托）；**四系统代码级核对 4 张表** —— 头集（**四家头名完全一致**，三家多 `X-Agent-Id`）／**隔离语义（OpenBase＋RAG＋Memory 三家已一致，DPS 为唯一偏离者）**／默认值与保留码／principal 模型（5 键 vs DPS 7 键）；**统一方案**（基准条款 B1~B5 ＋ DPS 偏离处置**推荐方案 B**：对外遵循基准、内部模型不动、经 `org_value_map` 传真 org）；**本版动作 4 项**（含「不本版收敛」的范围纪律）；**风险与开放项 4 项**（含 P1：`org_value_map` 配置须实证）。状态 [Review]。 |

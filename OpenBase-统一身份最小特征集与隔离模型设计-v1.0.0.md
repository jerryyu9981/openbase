# OpenBase-统一身份最小特征集与隔离模型设计-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-IDENT-MIN-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Review] |
| 日期 | 2026-09-06 |
| 作者 | AD（跨项目分析） |
| 版本主题 | 面向"五系统可独立使用、可协同使用、数据完全隔离"的统一身份建模：实体与特征逐项判定，输出最小必须集与数据隔离键设计 |
| 适用范围 | OpenBase / OpenLLM / OpenRAG / OpenMemory / DPS + 智能体（Agent） |
| 上游依据 | 统一身份与主备双通道总体方案 v1.0.0（U1 设计前置）；治理评审 v1.6.0（Q2/Q3/Q4、R-375）；联调复盘 v1.0.0（根因 4.3 身份键语义多义） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-06 | AD（跨项目分析） | 初始版本：使用模式分析、身份实体判定（必须/可选/非必须）、最小特征集、数据隔离键设计、兼容规则 |

---

## 1. 目的与问题

五系统（OpenBase/OpenLLM/OpenRAG/OpenMemory/DPS）既需**独立使用**（单系统对外交付），也需**协同使用**（经 OpenBase 统一编排），且无论哪种模式，**不同业务方的数据必须完全隔离、不串号**。

本设计回答一个问题：在 Agent（智能体）、Tenant（租户）、Org（组织）、Team（团队）、User（用户）、Role（角色）及各类外部/业务对象中，**哪些身份实体与特征是必须的**（去掉会破坏隔离或协同），哪些是可选的（按需扩展），哪些是非必须的（引入即过度建模）。

## 2. 使用模式与约束推导

| 模式 | 典型形态 | 对身份建模的约束 |
|------|---------|-----------------|
| M1 独立 | OpenLLM/OpenMemory 单独部署并对外服务（自带用户/API Key） | 系统必须能在**没有 OpenBase 统一层**时自足认证与隔离 |
| M2 协同 | 经 OpenBase 统一登录进入任意模块（前端/Agent/对话编排）；同一用户跨系统取回自己的记忆/画像/知识 | 跨系统必须能**串接同一主体**并共享同一**数据域键**，身份头/claim 一致 |
| M3 混合 | 部分系统独立、部分经 OpenBase；后续全部并入 | 最小特征集必须同时支持 M1/M2，不因并入而迁移重写 |
| 隔离约束 | 域 A 与域 B 的任何主体不可读对方数据（行级/分区级过滤） | 需要一个**唯一的、库行/命名空间可携带的数据域键** |

推导结论（三条设计约束）：
1. **域键唯一化**：数据隔离键全局只有一个稳定值（否则 M1 与 M2 的库行无法对账）。
2. **主体键可串接**：同一自然人/服务在五系统必须映射到同一主体键（否则记忆/画像/权限串不起来）。
3. **授权可映射**：各系统权限引擎允许不同（细粒度保留），但粗粒度语义（管理/读写）可互译，隔离不受角色定义差异影响。

## 3. 候选身份实体逐项判定

| 实体 | 定义（本体系） | 判定 | 理由 |
|------|---------------|------|------|
| **User（用户）** | 认证主体：自然人/系统账号（本地、OIDC、服务账号），OpenBase 唯一控制面 | **必须** | 认证与归属的最小主体；五系统数据行（记忆/会话/画像写链/审计）都以 user 为属主或操作者 |
| **Tenant（租户）** | 业务数据域/组织边界；对外键 = `tenants.code`（Q3） | **必须** | 唯一的数据域隔离键。Q2 定案"org 头退役为兼容别名、tenant 即组织"，故租户=组织语义合一 |
| **Org（组织）** | 与 tenant 同值的旧概念（X-Org-ID） | **非必须** | Q2 已判退役：无独立产品诉求；保留为兼容别名（头/映射表接受 org 值但语义=tenant），不作为新数据键 |
| **Team（团队）** | 租户内授权/资源分组（组级读写） | **可选（扩展点）** | 当前无"组级数据隔离/组授权"诉求（YAGNI）；如需要，作为 OpenBase 授权层的分组属性（role 作用域限定 team_id），不进入数据隔离键 |
| **Agent（智能体）** | 无人工介入的程序主体（Agent/MCP/自动化） | **必须作为子类型**（非独立实体） | Agent 需要一个**主体身份**才能被审计、限流、隔离（行为同 user）；建模为 User 的服务/受信子类型（`subject_type=user|agent` + 凭据类型 API Key/受信源），复用同一套身份/域/角色模型——引入独立实体反而制造第二个身份面 |
| **Role（角色）** | 权限集合（可赋给 user/agent） | **必须（授权面）** | 决定"能做什么"；隔离本身不依赖角色，但没有角色无法做受控共享与最小权限 |
| 业务对象（画像 person、知识文档、记忆条目、会话） | 非身份实体 | **不建模为身份** | 但**必须携带归属键**（见 §5），否则无法隔离 |

关键判定语义：
- **隔离不需要 Org/Team 实体**：隔离只需"域键（tenant_code）+ 属主（user_id/service）"两把钥匙。
- **协同不需要独立 Agent 实体**：Agent 是带密钥的受信主体，身份面与 user 同构。
- **权限的"角色"在各系统可不同粒度**：跨系统只约定粗粒度互译（见 §6），不强制同一张角色表。

## 4. 最小必须特征集（字段级）

### 4.1 主体（User/Agent 共用）

| 特征 | 语义 | JWT claim / 头 | 必带场景 | 备注 |
|------|------|----------------|---------|------|
| `user_id`（主体键） | 平台内唯一主体 id（sub） | `sub` / `X-User-ID` | M1+M2 | 串接键；DPS/记忆等以它做属主/操作者 |
| `subject_type` | user / agent | `sub_type`（可选 claim） | M2 审计 | agent 凭据=API Key/受信源，user 凭据=密码/OIDC |
| `username / name` | 展示与登录名 | `username` | M1 | 不承担隔离 |
| `status` | active/suspended/deactivated | （服务端校验） | M1+M2 | 生命周期门禁（U1） |
| 凭据（密码哈希/API Key/IdP 绑定） | 认证材料 | — | M1 | OpenBase 唯一持有；子系统不再自建登录 |

### 4.2 域（数据隔离键）

| 特征 | 语义 | claim / 头 | 必带场景 | 备注 |
|------|------|-----------|---------|------|
| `tenant_code` | 唯一数据域键（组织=租户） | `tenant_code`（新令牌增量签发）/ `X-Tenant-ID` | M1+M2 | **唯一必须的隔离键**；库行、命名空间、头、映射表全部用它 |
| （兼容）`org_id` | = tenant 旧值 | `org_id` / `X-Org-ID` | 兼容期 | Q2 退役为别名；服务端归一为 tenant_code 后不落新库行 |

### 4.3 授权

| 特征 | 语义 | 承载 | 必带场景 | 备注 |
|------|------|------|---------|------|
| `roles` | 粗粒度角色集合（admin/editor/viewer 等） | JWT `role(s)` / `X-User-Role` | M1+M2 | 跨系统只互译粗粒度语义；系统内细粒度权限引擎保留 |

### 4.4 审计/来源（必须但轻量）

| 特征 | 语义 | 必带场景 | 备注 |
|------|------|---------|------|
| `source` | 登录来源（local/oidc/agent-key/proxy） | M2 审计 | llm-proxy 已带 X-Proxy-Source（防伪造白名单） |
| `request_id` | 链路贯穿 | M2 | 统一 request_id/身份透传（U4） |

### 4.5 结论式清单（可直接实现的最小集）

```
主体（User/Agent 同一模型）：
  subject_key = user_id(UUID/数字 sub)         # 必带
  subject_type = user | agent                   # agent 必带；user 缺省
  credential    = password | oidc | api_key     # 三者其一
  display       = username/name/email           # 必带（展示）
  status        = active|suspended|deactivated  # 必带（门禁）
域（数据隔离）：
  domain_key = tenant_code                       # 唯一隔离键，必带
授权：
  coarse_roles = [role_codes]                    # 必带；细粒度在系统内
审计：
  source / request_id                           # 必带（协作模式）
可选扩展（缺省不建）：team_id（组授权）、org_id 兼容别名、外部业务对象注册表
非必须：独立 Agent 实体、独立 Org 实体、per-系统独立用户注册
```

## 5. 数据隔离键设计（五系统现状 → 目标）

| 系统 | 现状（实证） | 目标（统一域键 tenant_code + 属主 user_id） |
|------|-------------|-------------------------------------------|
| OpenBase | tenants.id/code + users + roles；JWT 签发 tenant_code（P3.1） | 保持；tenant_code 进入全部签发（login 亦签发，闭环存量） |
| OpenLLM | org 前缀/namespace 形态；DPS/记忆组件出站带 REAL_* 兜底 | 出站身份头统一：`X-User-ID=user_id`、`X-Tenant-ID=tenant_code`（org 头兼容期同值） |
| OpenRAG | Collection/Document **无 org 字段（裸 uuid，隔离缺口）** | 文档/集合补 `tenant_code` 归属列 + 查询强制过滤（P0-2 系遗留缺口，随 U2 立项） |
| OpenMemory | user_id 可选、org 可选、namespace 前缀 | 行级归属 `(tenant_code, user_id)` 必带 + 查询过滤（sessions 等端点归 P2-2 Phase2） |
| DPS | platform.organization/tenant 实体 + 中间件校验（code/UUID 双形态）+ user_roles | org/tenant 归一为 tenants.code 语义；person 对象归属 tenant（已有）+ 绑定由 OpenBase 总线驱动（U2） |

隔离规则（全系统统一）：
- 读/写/列/审计：行必须命中 `tenant_code == 当前域`，属主 `user_id == 当前主体` 或系统服务豁免（agent 按其归属域）。
- schema 级（共享 PG）保持 openbase/platform 分 schema；业务数据域隔离一律行级/前缀级（支持 M1 单库部署与 M2 共享库两种拓扑，隔离键不变）。

## 6. 独立（M1）与协同（M2）兼容规则

1. **M1 单系统独立**：系统本地自带最小主体/域（user_id + tenant_code 可本地自管，如 OpenMemory 无 OpenBase 时用本地 user/tenant）；**一旦接入 OpenBase（M2）**，本地身份被 OpenBase 覆盖为同构键（不迁移数据，只切换签发/校验源）。
2. **键不迁移**：本地已有行若以 org/裸 uuid 存，接入时补 tenant_code 归属列（增量迁移，W1-4 范式），不改主键。
3. **跨系统粗粒度角色互译表**：admin/editor/viewer（OpenBase）↔ super_admin/org_admin/user（DPS）↔ 各系统既有角色——只映射"管理/读写"两档语义，细粒度权限不入互译。
4. **agent 凭据**：agent 经 OpenBase 发放（API Key + 受信源 X-Proxy-Source），任何系统对 agent 请求按 agent 归属域隔离，视同 user 处理。

## 7. 与在途决策/文档衔接

- 治理评审 Q2（tenant=org 唯一）、Q3（code 对外）、Q4/M3（external/agent 可信源）：本设计是它们的**落库化**（把结论变成最小字段集）。
- 统一总体方案 U1（身份对象与生命周期状态机）：本设计是其数据模型输入；U1 实现按 §4.5 最小集建模，Team/Org 只留扩展点。
- 复盘根因 4.3（external 一值多义）：本设计明确 user_id（主体键）与业务对象键分离；画像 person_id 走业务对象注册表，不再用 external_user_id 兼任。
- P2-1（统一身份协议头）、P2-2（fail-closed/sessions 归属）：按本设计 §5 目标列实施。

## 8. 结论清单

**必须（五系统独立/协同/隔离的充分必要集）**：
1. 主体：`user_id`（User 与 Agent 同一模型，agent 为受信子类型）；
2. 域：`tenant_code`（组织=租户的唯一数据隔离键）；
3. 授权：`coarse_roles`（系统内细粒度保留，跨系统只互译粗粒度）；
4. 生命周期：`status`（active/suspended/deactivated 门禁）；
5. 归属：所有业务数据行携带 `(tenant_code, owner_user_id)`。

**可选（有诉求再启用，不预建）**：Team（组授权）、Org 兼容别名（过渡期）、外部业务对象注册表（画像 person 等）、细粒度角色互译扩展。

**非必须（判定为过度建模）**：独立 Agent 身份实体、独立 Org 隔离实体、per-系统重复用户注册。

## 9. 待评审问题

- Q1：Team 若未来需要"组级数据隔离"（而非仅组授权），隔离键是否要加 team 维？——本设计建议保持两键隔离，组只做授权层；如业务确有组隔离再升级为 `tenant_code+team_code` 复合键（预留列位）。
- Q2：Agent 与 User 是否需要不同 `display/credential` 约束（agent 无密码仅 key）——建议启用服务账号策略（不可密码登录、强制 key 轮换）。
- Q3：独立模式（M1）下 tenant_code 由谁发放（本地种子即可），接入 OpenBase 后是否允许历史本地 code 与 OpenBase code 冲突——建议以 OpenBase 为准统一重映射并在迁移清单记录。

评审通过后，本设计作为《统一身份与主备双通道贯通总体方案》U1 的数据模型基线进入立项实施。

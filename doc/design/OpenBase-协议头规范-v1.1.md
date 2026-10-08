# OpenBase 协议头规范 v1.1

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-P21-SPEC-HDRS-v1.1.0 |
| 版本 | **v1.1.0** |
| 状态 | **[Review]**（v1.1 增量待人工确认；v1.0 部分为 [Approved] 承接，未改动） |
| 日期 | 2026-10-08 |
| 上游正文 | 《OpenBase-P2-1-统一身份协议头与信任链收口设计草案》v1.0.0 §3；v1.0 正文（OB-INTG-P21-SPEC-HDRS-v1.0.0） |
| v1.1 变更来源 | 《OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0》§6 **A 批 A5**；A 批 A1/A2（`OPENBASE_PROXY_CODE_MAP` 统一码空间登记）、A3（`config/role_tier_anchors.json`）、A4（`config/error_code_map.json`）；R-387 收口实测 |
| 适用范围 | OpenBase 主仓及 S2/S3/S4/S5 各子系统仓 K02 落地唯一依据 |

> 本规范为「统一身份协议头」的**单一事实正文**。凡各仓实现/移植/联调，一律以本规范为准；
> OpenBase 仓内共享常量/校验函数参考实现位于 `openbase/modules/protocol_headers/`
> （constants.py / validate.py / inject.py / identity_context.py / role_map.py / **code_space.py**），
> 对外以「文档 + 常量/校验参考实现」为移植基线。

> **v1.1 变更摘要**：① 新增 **§2.1 出站租户码空间登记**（按目标登记的保留码/兜底码，`OPENBASE_PROXY_CODE_MAP`）；
> ② 新增 **§3.1 角色档位契约**（`readonly < readwrite < manage`，`config/role_tier_anchors.json` 为锚点单一事实源）；
> ③ 新增 **§4.1 开关默认值与生产门禁统一要求** 与 **§4.2 过渡期退出计划**；
> ④ §5 出站行为矩阵按 A 批实现回写（memory-proxy 兜底码改由登记表给出、X-Org-ID 语义修正）；
> ⑤ §7 错误码扩充跨系统实测码并接入 A4 映射表；⑥ §8 常量表补充 A 批制品索引。
> **v1.0 已批准内容未作实质修改**，仅在被新机制取代之处标注「【v1.1 回写】」。

---

## 1. 头清单与语义定义

规范头集（本规范管辖）：

| 头名 | 语义 | 类型/必带 | 取值源（OpenBase 侧） | 备注 |
|------|------|-----------|----------------------|------|
| `X-User-ID` | 请求**有效主体** sub（委托时为 delegated.subject_id） | string ≤128 / 身份可解析时必带 | 签发上下文（JWT sub / agent users.id / 受信编排透传） | 主体系引键 |
| `X-Tenant-ID` | **唯一隔离键** tenant_code | string ≤64 / **受信入站写路径必带**（见 §2.1） | 统一上下文 tenant_code（JWT claim/主体行冗余列）；委托时 = 委托域；缺省按目标登记兜底 | 数据面域过滤唯一键 |
| `X-Org-ID` | **退役兼容别名**，值恒 = X-Tenant-ID（或显式别名表命中值） | string ≤64 / 兼容期可选 | 别名收敛后与 tenant_code 同值 | **不得承担独立取值链** |
| `X-User-Role` | 有效主体粗粒度角色 | string ≤64 / 可解析时必带 | 统一上下文 role；发往互译系统时经 OB-12 互译表转目标角色码 | 现役码 admin/org_admin/org_member/viewer；**档位解释见 §3.1** |
| `X-Proxy-Source` | 最后出口代理/编排**来源标识** | string ≤64 / 必带 | 来源标识常量包（`protocol_headers/constants.py`） | 白名单校验主体；入站非白名单携带即伪造 |
| `X-Request-Id` | 链路贯穿请求 ID | string ≤64 / 必带 | OpenBase 审计中间件生成 `req-{12hex}`；受信来源入站可透传复用 | 审计串联键 |
| `X-Agent-Id` | **执行者 principal 标注**（agent 主体 users.id；委托场景 = 执行 agent） | string ≤64 / agent 或委托场景必带 | 统一上下文 subject_type=agent 时的 principal id | 委托两层在下游可见 |
| `X-On-Behalf-Of` | 委托引用头（形态 B，可选扩展） | string ≤512 / 可选 | 仅受信编排/OpenBase 委托签发链注入 | 默认不启用 |
| `X-API-Key` | 上游服务级 API Key | string / 按 proxy 现状 | settings 上游 key | **非身份头**；注意 OpenLLM 目前以 `Authorization: Bearer` 承载自有 API Key（§5 注 2） |

**出站身份头集合**：`X-User-ID/X-Tenant-ID/X-Org-ID/X-User-Role/X-Proxy-Source/X-Request-Id`，
agent 与委托场景追加 `X-Agent-Id`。

## 2. 取值规则：来源优先级

出站头取值**只允许来自「签发上下文」**，禁止从客户端原始头、配置文件默认值、
二次 JWT 解码结果直接取值。统一解析链：

```text
0. 入站裁剪（entry gate）：非受信来源携带的身份头一律不作为事实源——
   过渡期审计标注（identity_headers_ignored）；剥离期物理剥除；门禁后 403。
1. 认证通道判定（与 get_current_user/get_proxy_identity 同构）：
   a. 受信编排透传（X-Proxy-Source ∈ TRUSTED_PROXY_SOURCES 且携带四头）
      → 主体/域上下文 = 透传头值（完整来源链记审计 proxy_chain）。
   b. Bearer JWT（user/agent 主体验证通过）→ principal = {sub, subject_type,
      tenant_code, role, tvn, on_behalf_of}。
   c. Bearer/X-API-Key sk-agent-* → principal = resolve_agent_principal 返回主体。
   d. Bearer ob_k_* / X-API-Key 服务 Key → 服务账号语义：受信源配置绑定 → 服务主体；
      未绑定 → 拒绝匿名业务写（K03）。
2. 委托覆盖（最高优先，仅叠加于 b/c 的 agent principal 之上）：
   上下文含 on_behalf_of → 有效身份 = 委托目标：
   X-User-ID = delegated.subject_id；X-Tenant-ID/X-Org-ID = delegated.tenant_code；
   X-User-Role = delegated.role；X-Agent-Id = 执行 agent users.id。
3. 无委托 → 有效身份 = principal 自身。
4. 角色出站翻译：发往配置了互译表的系统时 X-User-Role 经互译表映射；映射缺失 → fail-closed。
5. 租户码目标域对齐（【v1.1 新增，见 §2.1】）：出站前按**目标域登记**做保留码归一与缺省兜底，
   保证发往任一目标的 `X-Tenant-ID` 落在该目标**可接受码空间**内。
```

优先级一句话：**受信编排透传头 >（agent 委托上下文 >）JWT/服务 Key 解析出的统一主体
上下文 > 目标域登记兜底码 >（兼容别名）**。任何一层缺失都不得回退到「客户端自带头」。

### 2.1 出站租户码空间登记（v1.1 新增）

**问题**：同一租户码在不同下游语义相反（实测）：`default` 对 OpenRAG 是**受信入站禁用保留码**
（携带即 400 `BIZ_RESERVED_TENANT_CODE_COLLISION`），对 OpenMemory 却是**唯一已登记组织码**
（`tenant-1`/`tenant-2` 返回 403「组织不存在或未配置策略」）。故「统一码空间」**不能是单一值硬套**，
必须**按目标登记**。

**登记结构**（OpenBase 侧单一入口）：

| 登记项 | 语义 | OpenBase 侧位置 |
|--------|------|----------------|
| 保留码集合 `reserved_codes` | 该目标**禁止入站携带**的码；主体码命中即归一为兜底码 | 内置基线 `OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET`（rag=`{default, openrag-local}`，其余空集） |
| 兜底码 `default_tenant_code` | 主体**无租户声明**时补的码（须非空且非保留码）；**不声明 = 该目标不进兜底**（省略头） | 内置基线 `BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET`（rag=`tenant-1`、memory=`default`；llm/dps 不设） |
| 覆盖 | 按目标按字段覆盖内置基线 | `OPENBASE_PROXY_CODE_MAP`（JSON 环境变量） |
| 运行期解析 | 唯一取值入口（含二次防线） | `protocol_headers/code_space.py::get_target_code_space(target)` |
| 校验 | 启动期 + 运行期同一组纯函数 | `settings.parse_proxy_code_map` / `resolve_target_code_space` / `validate_target_code_space` |

**覆盖表 Schema**：

```json
{
  "schema_version": 1,
  "source_of_truth": "openbase.tenants.code",
  "targets": {
    "<target>": { "reserved_codes": ["..."], "default_tenant_code": "..." }
  }
}
```

**强制要求**：

1. **唯一事实源**：`source_of_truth` 恒为 `openbase.tenants.code`；兜底码须为该空间的已登记值（不得凭空造码）。
2. **禁止散落字面量**：各 proxy **不得**在代码内写死目标码值，一律经 `code_space` 取值。
3. **fail-fast**：覆盖表非法（JSON/结构）、兜底码为空、或命中该目标保留码 → **启动即拒绝**（不得留到调用期才 400/403）。
4. **上游登记约束**：兜底码还须为该目标**上游已注册**的码值，未登记前**不得切换**，否则即时 403。
   实测例（2026-10-08）：OpenMemory 按组织策略 fail-closed，曾**仅登记 `default`**（`tenant-1` → 403）；
   经 **C1-a 跨仓登记**（`OPENMEMORY_RBAC__ORG_POLICIES` 增加 `tenant-1`/`tenant-2`）后，
   才具备把 memory 兜底码切换到 `tenant-1` 的前提。**登记属目标域职责，本规范只约束"未登记不得切换"。**
5. **变更留痕**：码空间口径变更须同步更新本文 §2.1、登记表与护栏用例（`tests/test_outbound_tenant_code_space.py`、`tests/test_bl147_trust_env_wiring.py`）。

## 3. 格式约束

| 约束 | 值 |
|------|-----|
| 长度上限 | X-User-ID ≤128；X-Tenant-ID/X-Org-ID/X-User-Role/X-Proxy-Source/X-Request-Id/X-Agent-Id/X-Team-Id ≤64；X-On-Behalf-Of ≤512 |
| 字符集 | 禁止 CR/LF/`\x00`（防头注入）；空头值禁止 |
| 角色值域 | 现役码：admin / org_admin / org_member / viewer（互译目标码见 OB-12 配置）；**档位解释见 §3.1** |
| 校验函数 | `protocol_headers.validate.validate_identity_headers`（非法 → 400 `PARAM_HEADER_FORMAT_INVALID`） |

### 3.1 角色档位契约（v1.1 新增）

为避免各目标域**自行解释角色码**，统一档位语义（`config/role_tier_anchors.json` 为锚点单一事实源）：

| 档位 | 序 | 语义 |
|------|:--:|------|
| `readonly` | 1 | 只读：允许读类方法（GET/HEAD/OPTIONS） |
| `readwrite` | 2 | 读写：在读类基础上允许写类方法（POST/PUT/PATCH/DELETE） |
| `manage` | 3 | 管理：读写 + 管理类操作（角色/权限/生命周期/豁免） |

**锚点**：`admin → manage`；`org_admin → readwrite`；`user` / `org_member` / `viewer` → `readonly`。

**强制要求**：

1. **未映射角色码 → fail-closed**（403 `ROLE_UNMAPPED`），**禁止**静默降级为 `readonly`。
2. 写类方法要求 **≥ `readwrite`**；档位不足 → 403 `PERM_FORBIDDEN`。
3. 各目标域可保留自有档位**枚举名**（如 OpenMemory `READ/READWRITE/MANAGE`），但**序与语义必须与本表一致**。
4. 档位守卫必须**真实接入请求路径**（存在但未接线视为未实现）。
5. 角色码集合须以锚点表为准；已知不一致（OpenBase 种子含 `user`、出站允许集合含 `org_member`）须并集后统一。

## 4. 校验矩阵（K02 M1 行为矩阵）

| 请求形态（下游视角） | X-Proxy-Source | 身份头 | 下游行为 |
|---------------------|----------------|--------|----------|
| 白名单来源 + 带身份头 | ∈ 白名单 | 有 | **信任**：按身份头解析主体/域/角色 |
| 白名单来源 + 无身份头 | ∈ 白名单 | 无 | 自身认证（API Key/本地登录）后按自身域处理 |
| 非白名单 + 带身份头 | ∉ 白名单/缺失 | 有 | **403**（伪造头；`PERM_UNTRUSTED_IDENTITY_HEADER`） |
| 非白名单 + 无身份头 | 缺失 | 无 | 自身认证（独立模式 API Key）；不采信任何身份语义 |

OpenBase 侧分段上线（两段式）：

| 阶段 | 开关 | 行为 |
|------|------|------|
| 过渡期（默认） | `strip_inbound_identity_headers=false`；`enforce_inbound_identity_headers=false` | 非受信来源带头 → 不采信 + 审计标注 `identity_headers_ignored` + WARN |
| 剥离期 | `strip_inbound_identity_headers=true` | 非受信来源身份头物理剥除后继续自身认证 |
| 强校验期 | `enforce_inbound_identity_headers=true` | 非受信来源带头 → 403 `PERM_UNTRUSTED_IDENTITY_HEADER` |

出站严格开关：`enforce_proxy_identity_headers`（默认 false）；别名强模式：`enforce_org_alias`（默认 false）。

### 4.1 开关默认值与生产门禁统一要求（v1.1 新增）

五系统现状同构但**默认值与生产强制不一致**；v1.1 统一要求如下：

| 要求 | 内容 |
|------|------|
| 默认值统一 | 过渡期三开关**默认 false**（保持兼容）；`role_fail_closed` 类开关**默认 true**（fail-closed 优先） |
| **生产强制** | **生产环境必须** `enforce_inbound_identity_headers=true` 且行控/租户校验策略开启；未满足 → **拒绝启动**（不得静默运行） |
| 范本 | OpenMemory `validate_server_api_key_policy` / `validate_row_scope_policy`（生产门禁的参考实现） |
| 适用范围 | 五系统（OpenBase 及四仓）各自落地启动校验；OpenBase 侧为**要求方与校验方**（D 批门禁脚本核对） |

### 4.2 过渡期退出计划（v1.1 新增）

「非受信带头 → 忽略 + 标注 + WARN」是**有意过渡态**，不得永久停留。强制要求：

1. 各仓须为过渡态设定**退出条件与目标版本**（建议两个版本内进入强校验期）。
2. 退出前须完成**影子期观测**：输出「若开启强校验将被拒」的清单，逐个消化调用方。
3. 退出动作 = 置 `enforce_inbound_identity_headers=true`（及对应行控策略），并保留一键回滚开关。
4. 退出状态须登记在各仓文档与 OpenBase 侧《总体完善方案》§5 差距清单。

## 5. 出站行为矩阵（代理族注入矩阵）

| proxy | X-User-ID | X-Tenant-ID | X-Org-ID | X-User-Role | X-Proxy-Source | X-Request-Id |
|-------|-----------|-------------|----------|-------------|----------------|--------------|
| dps-proxy | 有效 sub | tenant_code 优先链 → 显式兜底 → 值映射 | 别名（=tenant 语义） | 有效角色（缺省 user）→ 互译（DPS） | `openbase-dps-proxy` | ✓ |
| llm-proxy | 有效 sub | 有效 tenant_code（**不设兜底**，缺省不注入） | 别名 | ✓ | `openbase-llm-proxy` | ✓ |
| rag-proxy | 有效 sub | 有效 tenant_code → **保留码归一/登记兜底**（默认 `tenant-1`）【v1.1 回写】 | 别名（=归一后 tenant） | ✓ | `openbase-rag-proxy` | ✓ |
| memory-proxy | 有效 sub | 有效 tenant_code → **登记兜底**（默认 `default`）【v1.1 回写】 | 别名（=tenant，**不再是 `openbase-default` 独立兜底**）【v1.1 回写】 | ✓ | `openbase-memory-proxy` | ✓ |
| 通用 /proxy | JWT 有效 sub；ob_k_ 服务账号通道来源标注 | ✓ | 别名 | ✓ | `openbase-generic-proxy` | ✓ |

agent 与委托场景追加 X-Agent-Id = 执行 agent principal。

**注 1**：所有 proxy 的租户码一律经 `code_space.get_target_code_space(target)` 取值（§2.1），
不得在 proxy 内写死码值。

**注 2（契约差异登记，非本规范授权）**：OpenLLM 主应用以 `Authorization: Bearer sk-openllm-*`
承载自有 API Key，且其入站不读 `X-API-Key`；与其他三仓（`X-API-Key` 通道）**不一致**，
登记为待收口项（见 B1 派单）。

## 6. 委托头形态

- **形态 A（默认）**：委托块承载于 JWT `on_behalf_of` claim；出站四头承载委托
  有效身份，X-Agent-Id 承载执行 agent principal；memory-proxy「透传原 JWT」场景 claim
  原样携带。
- **形态 B（X-On-Behalf-Of，可选扩展）**：base64url(compact JSON) 头；**仅白名单来源
  可携带**，且与 JWT claim 须一致（否则 403）。不建议启用。
- **唯一签发**：on_behalf_of 上下文只由 `delegation.issue_delegated_token_pair` /
  `build_on_behalf_of_claim` 或受信编排签发；校验走 `verify_delegation` /
  `verify_request_delegation`（域不变式/嵌套链逐跳）。

## 7. 错误码

| 错误码 | HTTP | 语义 | 触发 |
|--------|------|------|------|
| `PERM_UNTRUSTED_IDENTITY_HEADER` | 403 | 非受信来源携带身份头 | 门禁后入口校验 / 下游 K02 落地 |
| `PERM_DELEGATION_VERIFY_UNAVAILABLE` | 403 | 委托请求 + DB 不可达/行缺失无法证明不变式 | verify_principal 委托分支 |
| `PARAM_HEADER_FORMAT_INVALID` | 400 | 规范头格式/类型非法 | validate_identity_headers |
| `PERM_SERVICE_KEY_WRITE_DENIED` | 403 | 未绑定服务账号的服务密钥/匿名业务写被拒 | /proxy 写路径（四仓同族出现） |
| `BIZ_ORG_ALIAS_MISMATCH` | 403 | X-Org-ID ≠ X-Tenant-ID 别名（强模式） | 入口校验/出站装配（开关化） |
| `ROLE_UNMAPPED` | 403 | 角色码未映射（fail-closed）【v1.1 新增】 | 目标域档位解释（§3.1） |
| `BIZ_RESERVED_TENANT_CODE_COLLISION` | 400 | 受信入站携带该目标保留租户码【v1.1 新增】 | 目标域保留码校验（§2.1） |
| `AUTH_PRINCIPAL_DISABLED` | 401 | 主体已停用/吊销【v1.1 新增】 | 主体验证/生命周期 |

统一错误体：`{code, message, detail, request_id}`。**各目标域字面量码与统一语义码的映射见
`config/error_code_map.json`（A 批 A4 制品）**——本规范不要求上游改码，以映射对齐可观测性。

403 样例：

```json
{
  "code": "PERM_UNTRUSTED_IDENTITY_HEADER",
  "message": "identity headers from untrusted source",
  "detail": {"proxy_source": "spoofed-origin", "headers": ["X-User-ID"]},
  "request_id": "req-3f9a1c02d4e7"
}
```

## 8. 来源标识常量与 A 批制品索引（单一事实源）

| 常量 | 值 | 说明 |
|------|-----|------|
| `PROXY_SOURCE_DPS` | `openbase-dps-proxy` | dps-proxy 出站 |
| `PROXY_SOURCE_LLM` | `openbase-llm-proxy` | llm-proxy 出站（值不变，下游白名单零迁移） |
| `PROXY_SOURCE_RAG` | `openbase-rag-proxy` | rag-proxy 出站 |
| `PROXY_SOURCE_MEMORY` | `openbase-memory-proxy` | memory-proxy 出站 |
| `PROXY_SOURCE_GENERIC` | `openbase-generic-proxy` | 通用 /proxy 出站 |
| `PROXY_SOURCE_ORCHESTRATOR` | `openbase-orchestrator` | 受信编排层（可选注册） |

受信来源配置：settings `trusted_proxy_sources`（逗号分隔）；默认空 = 不信任外部携带身份头。
全仓仅一种取值（import `protocol_headers/constants.py`）。

**A 批制品索引（v1.1 新增）**：

| 制品 | 位置 | 用途 |
|------|------|------|
| 码空间登记 | `openbase/settings.py`（内置基线）+ `OPENBASE_PROXY_CODE_MAP`（覆盖） | §2.1 |
| 码空间运行期入口 | `openbase/modules/protocol_headers/code_space.py` | §2.1 |
| 角色档位锚点表 | `config/role_tier_anchors.json` | §3.1 |
| 错误码映射表 | `config/error_code_map.json` | §7 |

## 9. 双通道不变式

同一动作同一时刻仅一条主路径；无论 A（OpenBase 直连）还是 B（经 OpenLLM 编排）到达
子系统，头集合、来源标识白名单值、身份语义一致。B 通道出站若由编排层注入，其
X-Proxy-Source 须登记在子系统白名单且不得以 REAL_* 兜底值充当业务请求身份。

## 10. 示例

```
例 1：普通用户经 dps-proxy 读画像（JWT sub=123, tenant_code=acme, role=org_admin）
X-User-ID: 123
X-Tenant-ID: acme
X-Org-ID: acme
X-User-Role: org_admin
X-Proxy-Source: openbase-dps-proxy
X-Request-Id: req-3f9a1c02d4e7

例 2：agent(users.id=7, tenant=acme) 代表 user(88) 经 llm-proxy 对话（on_behalf_of）
X-User-ID: 88
X-Tenant-ID: acme
X-Org-ID: acme
X-User-Role: viewer
X-Agent-Id: 7
X-Proxy-Source: openbase-llm-proxy
X-Request-Id: req-6b21dd08e933

例 3（v1.1）：主体无租户声明的用户经 rag-proxy 检索（登记：rag 保留码={default,openrag-local}、
兜底码=tenant-1）——出站租户码不得为空、不得为保留码
X-User-ID: 1
X-Tenant-ID: tenant-1        # 主体无声明 → 登记兜底码（非保留）
X-Org-ID: tenant-1
X-User-Role: admin
X-Proxy-Source: openbase-rag-proxy
X-Request-Id: req-1c7be40a92f5
```

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-07 | P2-1 设计组 | 初始版本（由 P2-1 设计草案 §3 裁出独立成文；头语义/取值优先级/格式/校验矩阵/出站行为矩阵/错误码/示例） |
| v1.0.1 | 2026-09-08 | P2-1 开发组 | 评审状态回写：P2-1 S1b 段评审通过（用户对话确认 Q-D-1~3 与「按这个方案来」），[Draft] → [Approved]；发布物齐备核对登记（T3-1） |
| **v1.1.0** | **2026-10-08** | **AA/AT-OpenBase-Dev（A 批 A5）** | **A 批契约统一增量**：新增 §2.1 出站租户码空间登记（按目标登记 + `OPENBASE_PROXY_CODE_MAP` + fail-fast + 上游登记约束）与 §3.1 角色档位契约（`readonly/readwrite/manage` + 锚点表 + 未映射 fail-closed + 守卫须真实接线）；新增 §4.1 开关默认值与**生产门禁统一要求**（生产必须 enforce，未满足拒绝启动）与 §4.2 **过渡期退出计划**（设退出条件与版本 + 影子期观测）；§4 补 `enforce_org_alias`；§5 按 A 批实现回写（llm 不设兜底、rag 保留码归一/登记兜底、memory 兜底与 X-Org-ID 语义修正）并新增 OpenLLM API Key 承载差异登记；§7 扩充 `ROLE_UNMAPPED`/`BIZ_RESERVED_TENANT_CODE_COLLISION`/`AUTH_PRINCIPAL_DISABLED` 并接入 A4 映射表；§8 增 A 批制品索引；§10 增登记兜底示例。v1.0 已批准内容未作实质修改，被取代处标注【v1.1 回写】 |

# OpenBase 协议头规范 v1.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-P21-SPEC-HDRS-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Draft]（随 P2-1 S1b 段评审后转 [Approved]） |
| 日期 | 2026-09-07 |
| 上游正文 | 《OpenBase-P2-1-统一身份协议头与信任链收口设计草案》v1.0.0 §3（本文为 §3 裁出的独立规范正文） |
| 适用范围 | OpenBase 主仓及 S2/S3/S4/S5 各子系统仓 K02 落地唯一依据 |

> 本规范为「统一身份协议头 v1.0」的**单一事实正文**。凡各仓实现/移植/联调，一律以
> 本规范为准；OpenBase 仓内共享常量/校验函数参考实现位于
> `openbase/modules/protocol_headers/`（constants.py/validate.py/inject.py/identity_context.py/
> role_map.py），对外以「文档 + 常量/校验参考实现」为移植基线。

## 1. 头清单与语义定义

规范头集（本规范 v1.0 管辖）：

| 头名 | 语义 | 类型/必带 | 取值源（OpenBase 侧） | 备注 |
|------|------|-----------|----------------------|------|
| `X-User-ID` | 请求**有效主体** sub（委托时为 delegated.subject_id） | string ≤128 / 身份可解析时必带 | 签发上下文（JWT sub / agent users.id / 受信编排透传） | 主体系引键 |
| `X-Tenant-ID` | **唯一隔离键** tenant_code | string ≤64 / 必带 | 统一上下文 tenant_code（JWT claim/主体行冗余列）；委托时 = 委托域 | 数据面域过滤唯一键 |
| `X-Org-ID` | **退役兼容别名**，值恒 = X-Tenant-ID（或显式别名表命中值） | string ≤64 / 兼容期可选 | 别名收敛后与 tenant_code 同值 | **不得承担独立取值链** |
| `X-User-Role` | 有效主体粗粒度角色 | string ≤64 / 可解析时必带 | 统一上下文 role；发往互译系统时经 OB-12 互译表转目标角色码 | OpenBase 现役码 admin/org_admin/org_member/viewer |
| `X-Proxy-Source` | 最后出口代理/编排**来源标识** | string ≤64 / 必带 | 来源标识常量包（`protocol_headers/constants.py`） | 白名单校验主体；入站非白名单携带即伪造 |
| `X-Request-Id` | 链路贯穿请求 ID | string ≤64 / 必带 | OpenBase 审计中间件生成 `req-{12hex}`；受信来源入站可透传复用 | 审计串联键 |
| `X-Agent-Id` | **执行者 principal 标注**（agent 主体 users.id；委托场景 = 执行 agent） | string ≤64 / agent 或委托场景必带 | 统一上下文 subject_type=agent 时的 principal id | 委托两层在下游可见 |
| `X-On-Behalf-Of` | 委托引用头（形态 B，可选扩展） | string ≤512 / 可选 | 仅受信编排/OpenBase 委托签发链注入 | v1.0 默认不启用 |
| `X-API-Key` | 上游服务级 API Key | string / 按 proxy 现状 | settings 上游 key | 非身份头 |

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
4. 角色出站翻译：发往配置了互译表的系统（起步 DPS）时 X-User-Role 经互译表映射；
   映射缺失 → fail-closed。
```

优先级一句话：**受信编排透传头 >（agent 委托上下文 >）JWT/服务 Key 解析出的统一主体
上下文 > 显式默认值（仅兼容别名/兜底）**。任何一层缺失都不得回退到「客户端自带头」。

## 3. 格式约束

| 约束 | 值 |
|------|-----|
| 长度上限 | X-User-ID ≤128；X-Tenant-ID/X-Org-ID/X-User-Role/X-Proxy-Source/X-Request-Id/X-Agent-Id/X-Team-Id ≤64；X-On-Behalf-Of ≤512 |
| 字符集 | 禁止 CR/LF/`\x00`（防头注入）；空头值禁止 |
| 角色值域 | OpenBase 现役码：admin / org_admin / org_member / viewer（互译目标码见 OB-12 配置） |
| 校验函数 | `protocol_headers.validate.validate_identity_headers`（非法 → 400 `PARAM_HEADER_FORMAT_INVALID`） |

## 4. 校验矩阵（K02 M1 行为矩阵）

| 请求形态（下游视角） | X-Proxy-Source | 身份头 | 下游行为 |
|---------------------|----------------|--------|----------|
| 白名单来源 + 带身份头 | ∈ 白名单 | 有 | **信任**：按身份头解析主体/域/角色 |
| 白名单来源 + 无身份头 | ∈ 白名单 | 无 | 自身认证（API Key/本地登录）后按自身域处理 |
| 非白名单 + 带身份头 | ∉ 白名单/缺失 | 有 | **403**（伪造头；`PERM_UNTRUSTED_IDENTITY_HEADER`） |
| 非白名单 + 无身份头 | 缺失 | 无 | 自身认证（独立模式 API Key）；不采信任何身份语义 |

OpenBase 侧分段上线（试点，两段式）：

| 阶段 | 开关 | 行为 |
|------|------|------|
| 过渡期（默认） | `strip_inbound_identity_headers=false`；`enforce_inbound_identity_headers=false` | 非受信来源带头 → 不采信 + 审计标注 `identity_headers_ignored` + WARN |
| 剥离期 | `strip_inbound_identity_headers=true` | 非受信来源身份头物理剥除后继续自身认证 |
| 强校验期 | `enforce_inbound_identity_headers=true` | 非受信来源带头 → 403 `PERM_UNTRUSTED_IDENTITY_HEADER` |

出站严格开关：`enforce_proxy_identity_headers`（默认 false）。

## 5. 出站行为矩阵（代理族注入矩阵）

| proxy | X-User-ID | X-Tenant-ID | X-Org-ID | X-User-Role | X-Proxy-Source | X-Request-Id |
|-------|-----------|-------------|----------|-------------|----------------|--------------|
| dps-proxy | 有效 sub | tenant_code 优先链 → 显式兜底 → 值映射 | 别名（=tenant 语义） | 有效角色（缺省 user）→ 互译（DPS） | `openbase-dps-proxy` | ✓ |
| llm-proxy | 有效 sub | ✓（P2-1 补齐） | 别名 | ✓（P2-1 补齐） | `openbase-llm-proxy` | ✓ |
| rag-proxy | 有效 sub（P2-1 补齐） | ✓（补齐） | 别名 | ✓（补齐） | `openbase-rag-proxy` | ✓ |
| memory-proxy | 有效 sub | 显式兜底 default | 显式兜底 openbase-default | ✓（P2-1 补齐） | `openbase-memory-proxy` | ✓ |
| 通用 /proxy | JWT 有效 sub；ob_k_ 服务账号通道来源标注 | ✓ | 别名 | ✓ | `openbase-generic-proxy` | ✓ |

agent 与委托场景追加 X-Agent-Id = 执行 agent principal。

## 6. 委托头形态

- **形态 A（v1.0 默认）**：委托块承载于 JWT `on_behalf_of` claim；出站四头承载委托
  有效身份，X-Agent-Id 承载执行 agent principal；memory-proxy「透传原 JWT」场景 claim
  原样携带。
- **形态 B（X-On-Behalf-Of，可选扩展）**：base64url(compact JSON) 头；**仅白名单来源
  可携带**，且与 JWT claim 须一致（否则 403）。v1.0 不建议启用。
- **唯一签发**：on_behalf_of 上下文只由 `delegation.issue_delegated_token_pair` /
  `build_on_behalf_of_claim` 或受信编排签发；校验走 `verify_delegation` /
  `verify_request_delegation`（域不变式/嵌套链逐跳）。

## 7. 错误码

| 错误码 | HTTP | 语义 | 触发 |
|--------|------|------|------|
| `PERM_UNTRUSTED_IDENTITY_HEADER` | 403 | 非受信来源携带身份头 | 门禁后入口校验 / 下游 K02 落地 |
| `PERM_DELEGATION_VERIFY_UNAVAILABLE` | 403 | 委托请求 + DB 不可达/行缺失无法证明不变式 | verify_principal 委托分支 |
| `PARAM_HEADER_FORMAT_INVALID` | 400 | 规范头格式/类型非法 | validate_identity_headers |
| `PERM_SERVICE_KEY_WRITE_DENIED` | 403 | 未绑定服务账号的 ob_k_/X-API-Key 匿名业务写被拒 | /proxy 写路径 |
| `BIZ_ORG_ALIAS_MISMATCH` | 403 | X-Org-ID ≠ X-Tenant-ID 别名（强模式） | 入口校验/出站装配（开关化） |

统一错误体：`{code, message, detail, request_id}`。

403 样例：

```json
{
  "code": "PERM_UNTRUSTED_IDENTITY_HEADER",
  "message": "identity headers from untrusted source",
  "detail": {"proxy_source": "spoofed-origin", "headers": ["X-User-ID"]},
  "request_id": "req-3f9a1c02d4e7"
}
```

## 8. 来源标识常量（单一事实源）

| 常量 | 值 | 说明 |
|------|-----|------|
| `PROXY_SOURCE_DPS` | `openbase-dps-proxy` | dps-proxy 出站 |
| `PROXY_SOURCE_LLM` | `openbase-llm-proxy` | llm-proxy 出站（值不变，下游白名单零迁移） |
| `PROXY_SOURCE_RAG` | `openbase-rag-proxy` | rag-proxy 出站 |
| `PROXY_SOURCE_MEMORY` | `openbase-memory-proxy` | memory-proxy 出站 |
| `PROXY_SOURCE_GENERIC` | `openbase-generic-proxy` | 通用 /proxy 出站 |
| `PROXY_SOURCE_ORCHESTRATOR` | `openbase-orchestrator` | 受信编排层（可选注册） |

受信来源配置：settings `trusted_proxy_sources`（逗号分隔）；默认空 = 不信任外部携带
身份头。全仓仅一种取值（import `protocol_headers/constants.py`）。

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
```

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-07 | P2-1 设计组 | 初始版本（由 P2-1 设计草案 §3 裁出独立成文；头语义/取值优先级/格式/校验矩阵/出站行为矩阵/错误码/示例） |

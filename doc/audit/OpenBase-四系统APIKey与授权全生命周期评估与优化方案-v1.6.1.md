# OpenBase 四系统 API Key 与授权全生命周期评估与优化方案

| 项目 | 内容 |
|---|---|
| 文档编号 | AUDIT-AUTH-20261029 |
| 版本 | v1.6.1 |
| 状态 | [Review] |
| 适用场景 | **AI 边缘终端为主**（多终端、算力/存储受限、网络间歇、本地推理、现场物理暴露）；政务强合规项暂缓 |
| 适用环境 | Dev（本地全栈）／Pro（共享 PG 主备 + Redis） |
| 评估对象 | OpenBase（统一底座）、OpenLLM、OpenRAG、OpenMemory、DPS |
| 评估方式 | 代码静态审计（AI 辅助），关键结论均附 `文件:行号`，可逐条复核；未做真实渗透测试 |
| 评估日期 | 2026-10-29 |
| 作者 | FA-OpenBase-Dev（AI 辅助） |

---

## 1. 结论摘要

**总体判断：功能闭环"能用"，但生命周期"不完整"，且中心/边缘职责存在明显重复与断层。**

| 维度 | 评分 | 说明 |
|---|:--:|---|
| 开户 → 授权（身份面） | ★★★☆ | 租户/用户/RBAC/主体状态机齐全，但 admin 硬编码绕过、列表缺租户过滤 |
| 密钥签发 → 分发（服务面） | ★★☆☆ | `ob_k_*` 无过期/无轮换/无 last_used；`sk-agent-*` 较完整；三套 Key 并存 |
| 使用 → 校验（数据面） | ★★☆☆ | 下游普遍"单静态 Key + 信任代理头"，且默认非强制；OpenLLM 可被伪造 `X-User-Role` |
| 轮换 → 吊销（生命周期） | ★☆☆☆ | 吊销不联动下游；RAG/OM/DPS 静态 Key 无吊销概念；OM 轮换接口形同虚设 |
| 审计 → 归因 | ★★☆☆ | 请求级审计有，但 Key 签发/吊销不落审计库，OpenLLM 审计不含 Key 身份 |
| offboarding（销户回收） | ★★☆☆ | purge 回收 agent Key，但 `ob_k_` 不回收、不发 Key 事件 |

**最需要先处理的 5 件事（P0）**

1. **OpenLLM 可被直连伪造 `X-User-Role` 提权**（`backend/app/identity/rbac_guard.py:194-196`）：角色解析在无受信 `state.identity` 时回退读原始请求头。
2. **服务 Key 的租户 scope 不生效**：`require_api_key` 校验时 `tenant_id=None`（`openbase/core/deps/auth.py:539`），`scope.tenants` 形同虚设。
3. **跨租户可见/可管**：服务 Key、用户、agent、租户等列表无 tenant 过滤（`openbase/modules/auth/service_keys.py:103`、`modules/users/__init__.py:208`、`modules/identity/agents.py:99`、`modules/tenant/__init__.py:311`）。
4. **Key 签发/吊销无审计落库**（`openbase/modules/auth/service_keys.py:94-97,170-173`）：无法回答"谁在何时给谁发了哪把 Key"。
5. **`username=="admin"` 硬编码通配**（`openbase/modules/auth/__init__.py:741`、`modules/identity/__init__.py:137`、`modules/tenant/__init__.py:219`）：绕过 RBAC，且与"最小权限"目标冲突。

**目标架构建议**：**控制面收敛到 OpenBase（唯一身份与密钥事实源）+ 双模数据面**——经 OpenBase 代理时用身份头，**下游通过自有 API/MCP 独立对外时用 OpenBase 签发的可验证凭证（JWKS 离线验签 + 自省/吊销事件兜底）**；下游不保留独立的"用户/租户主数据"，但保留本地凭证验证适配层。

---

## 2. 评估范围与方法

| 仓库 | 审计范围 |
|---|---|
| OpenBase | `openbase/modules/auth`、`identity`、`proxy`、`llm_proxy`、`rag_proxy`、`dps_proxy`、`users`、`tenant`、`audit`、`core/deps/auth.py`、`core/db/init.py`、`settings.py` |
| OpenLLM | `backend/app/api/auth.py`、`services/auth_service.py`、`models/api_key.py`、`identity/*`、`middleware/*`、`config.py` |
| OpenRAG | `src/openrag/api/middleware/*`、`identity/*`、`routes/*`、`storage/*` |
| OpenMemory | `src/openmemory/gateway/*`、`api/middleware/*`、`admin/*`、`auth/*`、`storage/*` |
| DPS | `src/rest_api/routes/routes_auth.py`、`src/engines/permission_engine.py`、`src/middleware/*`、`src/identity/*` |

方法：按"生命周期七环节"逐环节核对实现，再按"能力 × 系统"做分工矩阵，最后形成风险清单与分阶段方案。

---

## 3. 全生命周期现状（逐环节）

### 3.1 开户（租户 / 用户 / 角色）

| 能力 | 现状 | 证据 |
|---|---|---|
| 租户创建 | OpenBase `POST /tenants`，需 `tenant:manage`；admin 用户名硬编码放行 | `openbase/modules/tenant/__init__.py:212-231,219` |
| 用户创建 / 角色分配 | OpenBase `users` 模块 CRUD + 角色替换 | `openbase/modules/users/__init__.py:165-199,292-308` |
| 主体状态机 | 5 态（active/suspended/…/purged）统一迁移 + 同事务 outbox | `openbase/modules/identity/state_machine.py:22-48`、`lifecycle.py:150-257` |
| 事件下发 | 仅 `user.*` 事件（outbox + `/identity/events` + Redis 频道） | `identity/events.py:28-36`、`identity/__init__.py:629-701` |
| 下游用户体系 | OpenLLM/RAG/OM/DPS **各自保留本地 users 表与 CRUD**；DPS 仍保留本地密码登录并自签 JWT | `OpenLLM/backend/app/api/auth.py:36-97`、`OpenRAG/src/openrag/routes/users.py:26`、`OpenMemory/.../admin/routes.py`、`DPS/src/rest_api/routes/routes_auth.py:146-169` |

**结论**：开户"主责在 OpenBase"，但下游"影子用户/影子组织"未下线，导致同一主体在 5 个系统各有一份状态，天然存在不一致。

### 3.2 授权（RBAC / 租户隔离）

| 项 | 现状 | 证据 |
|---|---|---|
| RBAC 主实现 | OpenBase：payload → DB `user_role → role_permission`，支持 `*` | `modules/auth/rbac.py:75-95,109-167` |
| 权限点分配 | 种子：`org_admin` 得 `auth:api-keys:*`；`identity:*` 仅 admin | `core/db/init.py:185-194,213-224` |
| 下游角色解释 | OpenRAG/OpenMemory/DPS **各有一份角色码映射**（易漂移） | `OpenRAG/.../role_gate.py:59-65`、`OpenMemory/.../identity/role_map.py:37-68`、`DPS/src/identity/role_map.py:40-49` |
| 租户隔离 | OpenBase 多处列表未过滤；OpenLLM/RAG/OM 数据层有隔离但依赖入参；DPS 头与身份上下文双源不互校 | 见 §5 风险 R3/R6 |

### 3.3 密钥签发

| Key 类型 | 签发 | 存储 | 过期 | 轮换 | 证据 |
|---|---|---|---|---|---|
| 服务 Key `ob_k_*`（OpenBase） | `POST /auth/api-keys`，需 `auth:api-keys:manage` | `service_api_keys`，仅 sha256 | ❌ 无 | ❌ 无 | `modules/auth/__init__.py:752-780`、`service_keys.py:67-98`、`models/base.py:175-206` |
| agent Key `sk-agent-*`（OpenBase） | `POST /identity/agents/{id}/keys` | `agent_api_keys`，sha256 + `expires_at` + `last_used_at` | ✅ 可选 | 手工作废重签 | `modules/identity/__init__.py:307`、`base.py:142-172`、`agent_keys.py:117-179` |
| OpenLLM Key `sk-openllm-*` | 本地用户自助签发 | `api_keys`（org/team/user/permissions/rate_limit/expires/usage/last_used） | ✅ 可空 | ❌ 无 | `OpenLLM/backend/app/api/auth.py:190-214`、`models/api_key.py:21-59` |
| OpenRAG | **无签发**，仅环境常量 `service_api_key` | 配置 | — | — | `OpenRAG/src/openrag/api/middleware/api_key.py:59-90` |
| OpenMemory | 静态 `api_key` + `/admin/keys/rotate`（内存 dict、明文） | 内存/配置 | 名义有，实际不校验 | 形式化，不回写网关 | `OpenMemory/.../admin/service.py:60-131`、`gateway/gateway.py:86-98` |
| DPS | `service_api_keys`（sha256 + active） | DB | ❌ 无 | ❌ 无 | `DPS/src/engines/permission_engine.py:238-252` |
| MCP | 配置内明文 Key | 配置 | — | — | `openbase/modules/mcp/__init__.py:25-35` |

**结论**：**四套密钥体系**（`ob_k_` / `sk-agent-` / 各系统本地 Key / 配置静态 Key）并存，生命周期能力参差。

### 3.4 分发与使用

| 通道 | 机制 | 证据 |
|---|---|---|
| 浏览器 → OpenBase | JWT（2h/7d）+ 刷新，`tvn` 版本吊销 | `modules/auth/jwt.py:141-202`、`lifecycle.py:179-182` |
| OpenBase → OpenLLM | 代理注入 `Authorization: Bearer sk-openllm-*` + 身份头 | `modules/llm_proxy/__init__.py:128-129` |
| OpenBase → OpenRAG/OpenMemory | 代理注入 `X-API-Key`（各自静态 Key）+ 身份头 | `rag_proxy/__init__.py:154-155`、`proxy/memory_proxy.py:104` |
| OpenBase → DPS | 身份头 + `role_intertranslate` | `modules/dps_proxy/__init__.py:96-122` |
| 外部 → OpenBase | 服务 Key：`X-API-Key` 优先 / `Bearer ob_k_*` 回退 | `core/deps/auth.py:516-543` |

关键事实：
- OpenBase 出站头统一由 `build_outbound_headers` 装配（`X-User-ID/X-Tenant-ID/X-Org-ID/X-Subject-ID/X-User-Role/X-Proxy-Source`），`ob_k_` 通道可映射服务账号主体（`modules/proxy/__init__.py:196-237`）。
- 下游对身份头的信任完全依赖 `TRUSTED_PROXY_SOURCES` 白名单；**三仓默认列表为空、enforce 默认 false**（`OpenLLM/backend/app/config.py:110-112`、`OpenRAG/src/openrag/config/settings.py:281-284`、`DPS/src/identity/constants.py:31-34`）。

### 3.5 校验

| 系统 | 校验方式 | 缺口 |
|---|---|---|
| OpenBase | JWT：签名 + `verify_principal`（状态/`tvn`）+ Redis 60s 快照；服务 Key：每请求查库 | 服务 Key 校验 `tenant_id=None` → 租户 scope 不生效 |
| OpenLLM | `Bearer sk-openllm-` → 查库（sha256）；否则 JWT（本地 SECRET_KEY）；支持信任代理头 | 角色解析回退读 `X-User-Role`（可伪造）；Key 级 permissions/rate_limit 未生效 |
| OpenRAG | 静态 Key 常数时间比较 + 代理头四态门禁 | 无 Key 生命周期；默认不强制信任校验 |
| OpenMemory | 单静态 Key；HS256 共享密钥；`allow_unverified_gateway_token` 可放行未验签 | 轮换无效；未验签放行 |
| DPS | 本地 JWT（默认占位密钥）+ `service_api_keys` + 代理头门禁 + RBAC 引擎 | 身份上下文与租户上下文双源不互校；事件未达 → 授权陈旧 |

### 3.6 轮换与吊销

- OpenBase：服务 Key 吊销**立即生效**（每请求查库），但不通知下游、不发事件；agent Key 吊销即时。
- OpenLLM：吊销即时（每请求查库），但只有本地用户能吊销自己的 Key；OpenBase 侧无联动。
- OpenRAG：无吊销概念（改配置需重启）。
- OpenMemory：`/admin/keys/rotate` 只改内存对象，网关不重载 → **实际无效**。
- DPS：`service_api_keys.active` 只有手工置否。

**结论**：**吊销是"单点生效"，不是"全链路生效"**；密钥泄漏时无法在分钟级完成全网失活。

### 3.7 审计与 offboarding

| 项 | 现状 | 证据 |
|---|---|---|
| 请求级审计 | 有（含 401 错误码、敏感头过滤） | `openbase/modules/audit/__init__.py:153-162,577-583` |
| Key 签发/吊销审计 | **仅 logger，无 AuditLog 行** | `modules/auth/service_keys.py:94-97,170-173`、`identity/agent_keys.py:76,91` |
| OpenLLM 审计 | 剥 `Authorization`，**不记 key_id** → 越权不可归因 | `OpenLLM/backend/app/middleware/audit.py:295-301` |
| RAG/OM/DPS Key 失败审计 | 基本缺失（RAG 仅 info，DPS 仅 WARN，OM 无） | 见 §4 |
| offboarding | purge 回收 `agent_api_keys`，但 `ob_k_` 不回收、不发 Key 事件 | `identity/purge.py:110-113` |

---

## 4. 系统分工矩阵

图例：**主**=主责实现；**重**=重复实现；**缺**=应具备但缺失；— 无关。

| 能力 | OpenBase | OpenLLM | OpenRAG | OpenMemory | DPS |
|---|:--:|:--:|:--:|:--:|:--:|
| 租户/用户主数据 | **主** | 重 | 重/缺 | 重/缺 | 重 |
| 登录 / 令牌签发 | **主**（JWT + OIDC） | 重（本地密码） | — | 重（共享密钥） | 重（本地密码） |
| 用户 RBAC 权限点 | **主** | 重（本地 roles） | 重（RoleGate） | 重（role_map） | 重（`user_roles`） |
| 服务凭证签发 | **主**（`ob_k_`/`sk-agent-`） | 重（`sk-openllm-`） | 缺 | 缺（内存 rotate） | 重（`service_api_keys`） |
| 凭证校验（入站） | **主** | 本地实现 | 静态 Key | 静态 Key | 本地实现 |
| 身份头注入（出站） | **主** | — | — | — | — |
| 信任代理白名单 | **主**（来源常量） | 副本 | 副本 | 副本 | 副本 |
| 租户隔离（数据层） | 部分 | 部分 | 部分 | 部分 | 部分 |
| 审计（安全事件） | 部分 | 部分 | 缺 | 缺 | 缺 |
| 密钥轮换/吊销联动 | 缺 | 缺 | 缺 | 缺 | 缺 |
| offboarding 回收 | 部分 | 缺 | 缺 | 缺 | 缺 |

**重复清单（建议收敛）**

1. 用户/租户 CRUD：OpenLLM、OpenRAG、OpenMemory、DPS 各一套。
2. 角色码解释：`OpenRAG role_gate`、`OpenMemory role_map`、`DPS ROLE_TO_ANCHOR` 三份 + OpenBase 一份。
3. 四态入站门禁与身份头常量：OpenBase/OpenLLM/OpenRAG/DPS 各一份副本。
4. 服务凭证：`ob_k_`、`sk-agent-`、`sk-openllm-`、RAG/OM 静态 Key、DPS `service_api_keys`、MCP 明文 Key —— 共 6 类。

**断层清单（建议补齐）**

1. OpenBase 吊销/轮换不传播 → 下游无法感知。
2. 下游静态 Key 无生命周期 → 泄漏后只能改配置重启。
3. DPS 未接 OpenBase 令牌吊销（本地自签 JWT）→ 销户后令牌仍有效直至过期。
4. Key 事件缺失（`user.*` 之外无 `service_key.*` / `agent_key.*`）。
5. 下游审计不含 Key 身份 → 无法做"谁用哪把 Key 做了什么"的归因。

---

## 5. 风险清单（按严重度）

| 编号 | 级别 | 风险 | 证据 | 影响 |
|---|---|---|---|---|
| R1 | **P0** | OpenLLM 角色解析回退读取原始 `X-User-Role`，直连可提权 | `OpenLLM/backend/app/identity/rbac_guard.py:184-198` | 任意能直连 8001 的调用者伪造写权限 |
| R2 | **P0** | `ob_k_` 的 `scope.tenants` 不生效（校验时 `tenant_id=None`） | `openbase/core/deps/auth.py:536-540` | 租户级 Key 可跨租户调用 |
| R3 | **P0** | 服务 Key / 用户 / agent / 租户列表无 tenant 过滤 | `service_keys.py:100-104`、`users/__init__.py:208`、`agents.py:99`、`tenant/__init__.py:311` | 跨租户可见、可吊销、可管理 |
| R4 | **P0** | Key 签发/吊销无审计落库 | `service_keys.py:94-97,170-173` | 无法定责与合规取证 |
| R5 | **P1** | `username=="admin"` 硬编码通配 | `modules/auth/__init__.py:741` 等 3 处 | 绕过 RBAC；改名/多管理员场景失效 |
| R6 | **P1** | 下游信任白名单默认空 + enforce=false，漏配即降级 | `OpenRAG config/settings.py:281-284` 等 | 生产误配后身份头失效或过度信任 |
| R7 | **P1** | OpenMemory 轮换无效 + 允许未验签 token | `admin/service.py:60-131`、`gateway/gateway.py:151-180` | 轮换形同虚设；可伪造网关令牌 |
| R8 | **P1** | OpenLLM Key 级 permissions/rate_limit 不生效 | `OpenLLM/backend/app/services/auth_service.py:226-255` 等 | 最小权限与限流承诺失效 |
| R9 | **P1** | `ob_k_` 无过期/轮换/last_used | `models/base.py:175-206` | 长期有效凭证，泄漏窗口无限 |
| R10 | **P1** | 吊销不联动下游、无 Key 事件 | `identity/events.py:28-36` | 泄漏后全网失活需人工多仓操作 |
| R11 | **P2** | agent `last_used_at` 写入但请求会话无 commit（疑似不落库） | `agent_keys.py:159`、`core/db/session.py:100-108` | 用量审计失真 |
| R12 | **P2** | `expires_at` naive/aware 直接比较 | `agent_keys.py:149` | 时区异常导致误判过期/500 |
| R13 | **P2** | 按明文吊销回显 Key 且不校验命中 | `auth/__init__.py:813-823` | 明文进入日志/前端；误以为自己已吊销 |
| R14 | **P2** | `PUBLIC_PREFIXES` 用 `startswith` 前缀匹配 | `core/deps/auth.py:101-116` | 相似前缀路径可能跳过中间件门禁 |
| R15 | **P2** | 非生产响应采集掩码键不含 `key`/`raw_key` | `core/mask.py:61-77`、`settings.py:651-653` | 排障场景可能记录明文 Key |
| R16 | **P2** | MCP API Key 明文存配置 | `modules/mcp/__init__.py:25-35` | 配置泄漏即凭证泄漏 |
| R17 | **P2** | OpenLLM 本地 `users/tenants/teams` 与 OpenBase 双主 | `OpenLLM/backend/app/api/auth.py:36-97` | 状态不一致，销户不彻底 |
| R18 | **P1** | 双模接入下"代理路径 vs 直连路径"鉴权可能分叉（两套角色/权限解释） | 现状：代理靠身份头、直连各仓自判 | 同一令牌两种结果，越权或误拒 |
| R19 | **P1** | 离线验签无法即时感知吊销 | 当前无 JWKS/自省/吊销列表 | 销户后令牌最长存活至 `exp` |
| R20 | **P2** | MCP 传输（stdio/HTTP）凭证注入无统一约定 | OpenBase `modules/mcp/__init__.py:25-35` 仍为配置明文 Key | 本地进程长期凭证泄漏、工具级越权 |
| R21 | **P2** | 下游缓存 claims/权限导致降权延迟 | OpenLLM/RAG/OM 均无统一失效机制 | 权限收回后仍可写一段时间 |

---

## 6. 目标架构（建议）

### 6.1 四条设计原则

1. **单一事实源**：租户、用户、角色、凭证（`ob_k_`/`sk-agent-`）只在 OpenBase 签发与治理；下游不落用户、不签令牌。
2. **控制面与数据面分离**：控制面（签发/轮换/吊销）在 OpenBase；数据面（每次调用校验）由下游用统一验证适配层完成。
3. **双模接入、同一判定**：**经 OpenBase 代理**（身份头）与**下游自有 API/MCP 直连**（OpenBase 签发的可验证凭证）必须得到**同一鉴权结论**，不允许两套权限语义。
4. **默认安全**：租户必带、权限必判、审计必记 `key_id`、凭证必过期、直连必验签。

### 6.2 目标链路（双模）

**路径 A：经 OpenBase 代理（内部/前端聚合）**

```
浏览器/内部调用
   │ 用户 JWT（OpenBase 签发，tvn 吊销）／服务 Key ob_k_*（租户 scope + 过期）
   ▼
OpenBase 网关（/api/v1/proxy|llm-proxy|rag-proxy|dps-proxy|memory-proxy）
   │ 鉴权 + 租户解析 + 服务账号映射 + K03 写白名单
   │ 注入身份头（X-User-ID / X-Tenant-ID / X-Org-ID / X-User-Role / X-Proxy-Source）
   │ 注入下游上游凭证（sk-openllm-* / 服务 Key）
   ▼
下游系统：来源白名单（强制）+ 身份头采纳 + 租户过滤 + 审计（记 key_id/subject/tenant）
```

**路径 B：下游 API / MCP 独立对外（直连）**

```
外部调用方（第三方应用 / AI Agent / MCP Client）
   │ OpenBase 签发的「系统受众令牌」或「服务 Key」
   ▼
下游系统（OpenLLM / OpenRAG / OpenMemory / DPS / 各自 MCP Server）
   │ ① 验签（JWKS 公钥，离线）→ 校验 aud/exp/tenant/scope
   │ ② 吊销敏感操作：自省（introspection，带 30~60s 本地缓存）或订阅 Key 事件
   │ ③ 统一 claims → 与路径 A 相同的权限判定
   ▼
下游业务 + 审计（记 key_id/subject/tenant/entry=direct）
```

### 6.3 三种方案对比与推荐

| 方案 | 做法 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| A 去中心化 | 各系统保留自己的 Key 与用户 | 改动小 | 生命周期永远对齐不了，审计割裂 | 不推荐 |
| B 单一密钥中心 | OpenBase 统一签发/轮换/吊销；下游只校验 | 生命周期完整、审计统一 | 下游需改造、上线期需双跑 | **推荐（控制面）** |
| C 网关集中鉴权 | 所有调用只经 OpenBase 网关，下游不对外 | 最强收敛 | **与"下游 API/MCP 可独立对外使用"的既定需求冲突**；单点可用性压力 | 不可作为唯一路径（仅作内部聚合路径） |

推荐组合：**B（控制面）+ 双模数据面**——代理路径保留（内部聚合/前端），直连路径由下游用"OpenBase 凭证验证适配层"实现；两条路径共用同一 claims 与权限判定。

### 6.4 下游独立接入（API + MCP）设计

#### 6.4.1 凭证形态与受众

| 凭证 | 用途 | 受众（aud） | 形态 |
|---|---|---|---|
| 用户访问令牌（JWT，非对称签名） | 第三方以"某用户"身份调用某系统 | `openllm` / `openrag` / `openmemory` / `dps`（可多值） | `Authorization: Bearer <JWT>` |
| 服务访问令牌（短时，由 `ob_k_*` 换取） | 第三方系统级调用（无人参与） | 同上 | `Authorization: Bearer <JWT>`，`sub=svc:<key_id>` |
| 服务 Key `ob_k_*` | 直接作为长期凭证（兼容既有） | `scope.system` | `X-API-Key` 或 `Bearer ob_k_*`（下游统一按 Key 处理） |
| agent Key `sk-agent-*` | Agent 主体直连 | 主体绑定系统 | `Authorization: Bearer sk-agent-*` |

**统一约束**：所有直连凭证必须带 `tenant_code`、`aud`、`exp`；`aud` 不含目标系统 → 403（防止"一把 Key 打通全部系统"）。

#### 6.4.2 验证契约（OpenBase 提供，下游实现）

| 端点 | 方法 | 说明 |
|---|---|---|
| `GET /.well-known/jwks.json` | 公开 | 公钥集（支持 `kid` 轮换，保留旧公钥 ≥ 2×令牌 TTL） |
| `POST /api/v1/auth/introspect` | 受信网络/双向 TLS | RFC 7662 风格：入参 `token`，返回 `active/aud/tenant/scope/sub/exp`；下游本地缓存 30~60s |
| `GET /api/v1/auth/revocations?since=` | 受信网络 | 增量吊销列表（Key 哈希前缀 + 令牌 `jti`），供无法自省的环境拉取 |
| 事件 `service_key.*` / `agent_key.*` / `user.*` | outbox/Redis | 下游订阅后主动失效本地缓存 |

**验证顺序（下游适配层）**：验签（JWKS）→ `aud` 命中 → `exp/nbf` → 租户必带 → 自省或本地吊销缓存 → scope/权限点 → 业务。

#### 6.4.3 MCP 接入的特殊约定

| 传输 | 凭证传递 | 说明 |
|---|---|---|
| Streamable HTTP / SSE | `Authorization: Bearer <JWT>` 或 `X-API-Key` | 与 REST 同一适配层；MCP 工具调用按 `scope.tools` 做二级过滤 |
| stdio（本地进程） | 启动时由宿主注入短期令牌（env/文件，不落日志） | 视为本地可信边界，仍需校验 `exp/aud`，禁止无限期凭证 |

MCP 侧补充：工具级权限（`tools/list` 过滤、`tools/call` 二次校验）须与 REST 使用同一 claims；MCP Server 不接受"无凭证的本地调用"以外的匿名请求。

#### 6.4.4 与代理路径的一致性

- 代理路径注入的身份头与直连路径解析出的 claims **字段同名同义**（`subject_id/tenant_code/org_id/role/scopes`）。
- 下游权限判定只读"身份上下文对象"，不区分来源；仅审计字段 `entry=proxy|direct` 不同。
- 一致性验收：同一令牌经代理与直连调用同一接口，必须返回相同状态码与业务结果（见 §8）。

---

## 7. 分阶段优化方案

### 7.1 P0（立即修复，1~3 天，纯改代码不加新能力）

| # | 事项 | 落地位置 | 验收 |
|---|---|---|---|
| P0-1 | 下游角色解析**禁止**读原始 `X-User-Role`；仅在 `state.identity.trusted=true` 时采纳 | `OpenLLM/backend/app/identity/rbac_guard.py:184-198`；RAG/OM/DPS 同类路径 | 直连伪造头 → 403/降为最小档 |
| P0-2 | `require_api_key` 传入请求租户（`X-Tenant-ID` 或 JWT `tenant_code`），`scope.tenants` 生效 | `openbase/core/deps/auth.py:536-540` | 租户 Key 跨租户调用 → 403 |
| P0-3 | 服务 Key / 用户 / agent / 租户列表按当前租户过滤（admin 全局除外，需显式权限） | `service_keys.py:100-104`、`users/__init__.py:208`、`agents.py:99`、`tenant/__init__.py:311` | 跨租户不可见 |
| P0-4 | Key 签发/吊销写 `AuditLog`（含 key_id、name、scope、operator、request_id，不含明文） | `service_keys.py:67-98,107-173`、`agent_keys.py:44-113` | 审计表可按 key_id 检索 |
| P0-5 | 收敛 `username=="admin"` 硬编码：改为"内置超管主体 + 显式权限点" | 3 处调用点 + 种子 | admin 仍可用，但走 RBAC 显式权限 |
| P0-6 | 按明文吊销不回显明文；未命中返回 404 | `auth/__init__.py:813-823` | 响应无明文 |
| P0-7 | agent `last_used_at` 落库（提交事务） | `identity/agent_keys.py:159` | 刷新后可见更新 |
| P0-8 | `expires_at` 统一按 UTC aware 比较 | `agent_keys.py:149` | 边界用例通过 |
| P0-9 | `PUBLIC_PREFIXES` 改为路径段匹配（`== prefix` 或 `startswith(prefix + "/")`） | `core/deps/auth.py:101-116` | 相似前缀不再跳过门禁 |
| P0-10 | 掩码键补齐 `key`/`raw_key`/`secret` | `core/mask.py:61-77` | 采集内容无明文 |

### 7.2 P1（本迭代，控制面统一）

| # | 事项 | 要点 |
|---|---|---|
| P1-1 | `ob_k_` 增加 `expires_at`、`last_used_at`、`rotated_from`、`tenant_code` 列 | 迁移走 `create_all` + 幂等列补齐；签发默认 90 天 |
| P1-2 | 新增轮换端点 `POST /auth/api-keys/{id}/rotate`（旧 Key 宽限期可配） | 双 Key 并存窗口 + 到期自动失效 |
| P1-3 | Key 事件化：`service_key.*` / `agent_key.*` 写入 outbox，随 `/identity/events` 下发 | 下游可订阅做缓存失效/告警 |
| P1-4 | OpenBase 提供**可离线验证**的签发能力：非对称签名（RS256/ES256）+ `/.well-known/jwks.json` + `POST /auth/introspect` + `GET /auth/revocations`；HS256 保留为过渡 | 令牌含 `aud/tenant_code/scope/jti`；`kid` 轮换 |
| P1-5 | 下游统一**凭证验证适配层**（共享 SDK 或逐仓薄封装）：JWKS 验签 → `aud/exp/tenant` → 自省/吊销缓存 → 身份上下文；**代理路径与直连路径共用同一判定** | OpenLLM/RAG/OM/DPS 各接一次，禁止各写一套 |
| P1-6 | RAG/OM/DPS 入站**静态 Key 收敛为应急 bypass**（默认关闭、必带过期、必审计）；DPS 停用本地密码登录，改 JWKS/自省 | 保留迁移期开关 |
| P1-7 | OpenLLM 本地 Key 纳管：由 OpenBase 代签或明确标注"仅 OpenBase 代理内部使用"，禁止第三方直连持有 | 消除双主 |
| P1-8 | 下游审计记录 `key_id`/`subject`/`tenant`/`entry=proxy\|direct`（不含明文） | OpenLLM 优先 |
| P1-9 | 下游信任策略默认 fail-closed：`TRUSTED_PROXY_SOURCES` 为空时拒绝带身份头请求 | 三仓默认值调整 |

### 7.3 P2（后续迭代，治理与体验）

1. **统一角色字典**：OpenBase 发布角色码 → 下游仅做映射表（单一 JSON 契约），删除三份硬编码。
2. **密钥配额与限流**：按 Key 维度限速/限额（OpenLLM 已有表结构，补鉴权读点）。
3. **审计对账**：日对账任务（签发数=有效数+吊销数+过期数；下游拒绝数与网关审计数比对）。
4. **密钥托管**：KMS/加密列（至少落库加密 + 明文仅内存），MCP Key 迁移到 `ob_k_`。
5. **自动轮换**：按 90 天到期前 7 天提醒 + 一键轮换；服务账号 Key 支持双活。
6. **SSO 全覆盖**：DPS/OpenLLM 全面接 OIDC，删除本地密码；**直连 API/MCP 入口保留**，但凭证统一由 OpenBase 签发。

---

## 8. 验收标准

| 维度 | 指标 |
|---|---|
| 功能 | 开户→授权→签发→调用→轮换→吊销→销户 7 环节均有自动化用例；销户后 5 分钟内全网令牌/Key 失效 |
| 安全 | 伪造 `X-User-Role`/`X-User-ID` 直连 → 403；跨租户访问 → 403；明文 Key 不出现在日志/审计/响应 |
| 可审计 | 任意 Key 可反查"签发人/时间/scope/最近使用/吊销人/吊销时间" |
| 双模一致 | 同一令牌经**代理路径**与**直连 API/MCP 路径**调用同一接口，返回相同状态码与业务结果；直连验签（JWKS）不依赖 OpenBase 在线，敏感操作靠自省/吊销缓存 |
| 独立接入 | 下游 API/MCP 在 OpenBase 不可用时仍可验签放行（离线公钥）；OpenBase 恢复后自动收敛吊销状态 |
| 运维 | Key 到期前 7 天告警；轮换零中断（双 Key 窗口）；吊销全链路生效 ≤1 分钟 |
| 回归 | `pytest tests` 全绿；新增 `tests/test_auth_lifecycle_*`（≥20 例）；`ruff` 0 错误 |

---

## 9. 实施风险与依赖

| 风险 | 说明 | 缓解 |
|---|---|---|
| 下游改造面大 | RAG/OM/DPS 需改中间件与配置 | 分仓灰度、保留 bypass Key 开关 |
| 双跑期不一致 | 新旧 Key 并存 | 双写窗口 + 订阅 Key 事件 |
| 单点依赖 | 全部流量经 OpenBase | 网关多实例 + 下游兜底校验 |
| 现网数据 | 历史 Key 无过期字段 | 迁移默认值 + 到期批量通知 |
| 测试环境 | RAG/OM/DPS 测试覆盖薄 | 先补契约测试再改实现 |

---

## 10. 附录 A：AI 边缘终端场景的裁剪与轻量落地

> 结论：**不做政务级大改造**。保留"单一身份源 + 双模接入"骨架，按边缘约束做三层轻量落地；国密/密评、统一身份平台、三权分立、集中审计平台、信创与灾备**暂缓**（仅在政务交付时启用）。

### 10.1 场景约束

| 约束 | 对安全设计的影响 |
|---|---|
| 终端数量多、算力/存储有限 | 验证必须轻量（本地缓存 + 定期同步），不做重 RBAC 计算 |
| 网络间歇/可能长期离线 | 不能每请求回源 OpenBase；需要离线宽限与本地策略缓存 |
| 本地推理（OpenLLM 边缘） | 模型与固件需签名校验；推理日志本地缓冲后上报 |
| 现场物理暴露 | 密钥需安全存储（TPM/安全元件），丢失需可远程失活 |
| 多租户/多站点 | 站点网关做本地鉴权汇聚，减少终端直连控制面 |

### 10.2 E0（立即，仍属"小改动"）

1. **设备身份化**：每台终端 = `subject_type=agent` 主体 + `sk-agent-*` 凭证（带 `expires_at`、`last_used_at`），禁止终端共享同一服务 Key。
2. **下游直连禁止读原始 `X-User-Role`**（R1）：边缘直连场景同样必须修。
3. **租户与 scope 生效**（R2）：站点/租户 Key 不可跨站点调用。
4. **Key 签发/吊销审计落库**（R4）+ 终端侧日志本地环形缓冲、联网批量上报。
5. **admin 硬编码收敛**（R5）：改为显式超管权限点，便于交付审计。
6. **离线宽限策略**：本地缓存"主体状态 + 权限 + 吊销位"（TTL 可配，默认 15 分钟；离线最长宽限 72 小时，超期拒绝写操作、只读降级）。
7. **一键吊销**：控制面吊销后，在线终端 ≤60s 生效；离线终端在下次联网/OTA 时收敛。

### 10.3 E1（下一步，中等改动）

- 非对称签名令牌（RS256；**国密 SM2 作为可插拔算法，政务交付再开启**）+ 边缘缓存 JWKS（`kid` 轮换）。
- 吊销增量同步：`GET /auth/revocations?since=`，随 OTA/心跳拉取；站点网关缓存并广播给终端。
- MCP 边缘服务：HTTP 走 Bearer、stdio 由宿主注入短期令牌；工具级 `scope.tools` 过滤。
- 设备配额与异常告警（同一 Key 多 IP、异地登录、调用量突增）。

### 10.4 E2（按需）

- TPM/安全元件存私钥；固件与模型签名校验；远程擦除；安全启动。
- 数据落盘加密（本地 SQLite/缓存）；日志防篡改（链式哈希）。

### 10.5 暂缓项（政务交付时再启用）

| 项 | 暂缓原因 | 启用触发 |
|---|---|---|
| 国密算法与密评 | 需密码机与测评，成本高 | 政务项目立项/等保定级 |
| 统一身份认证平台对接 | 当前无外部 IdP | 接入省级/部门统一认证 |
| 三权分立 + ABAC | 边缘场景角色简单 | 多部门数据共享 |
| 集中审计平台 / 留存≥6 个月 | 无独立审计系统 | 等保测评要求 |
| 信创适配 / 异地灾备 | 非边缘首要矛盾 | 国产化目录/容灾要求 |

### 10.6 三套编号的关系（R / P / E 追溯矩阵）

**先分清三套编号的定位：**

| 编号 | 是什么 | 回答的问题 |
|---|---|---|
| **R1~R21** | **风险台账**（发现的问题/缺陷） | "系统现在有什么问题？" |
| **P0 / P1 / P2** | **通用场景的修复排期**（企业/平台视角） | "这些问题按什么优先级修？" |
| **E0 / E1 / E2** | **AI 边缘终端场景的执行计划**（对 P 的裁剪与重排） | "在当前交付形态下，先做什么、后做什么、什么暂缓？" |

**三者不是三套工作**：同一风险只修一次；P 与 E 是同一批修复的两种排期视角，E 为最终执行口径（当前场景是边缘终端），P 保留为通用基线。

| 风险 / 事项 | 内容 | 通用排期 | 边缘执行 | 备注 |
|---|---|---|---|---|
| R1 | 下游伪造 `X-User-Role` 提权 | P0-1 | **E0** | 直连场景必修 |
| R2 | 服务 Key 租户 scope 失效 | P0-2 | **E0** | |
| R4 | Key 签发/吊销无审计 | P0-4 | **E0** | 边缘侧加本地日志缓冲 |
| R5 | `admin` 硬编码通配 | P0-5 | **E0** | |
| R3 | 列表无租户过滤 | P0-3 | **E0** | 管理面一并修 |
| R13/R14/R15 | 明文吊销回显 / 前缀匹配 / 掩码缺键 | P0-6/9/10 | **E0** | 低成本顺带修 |
| 边缘专属 | 设备身份化、离线宽限、一键吊销 | — | **E0** | 新增项，不属于 R 台账 |
| R9 | `ob_k_` 无过期/轮换 | P1-1/2 | **E1** | 先做到期与轮换端点 |
| R10 | 吊销不联动下游 | P1-3 | **E1** | Key 事件 + 增量吊销 |
| R18/R19 | 双模判定分叉 / 吊销延迟 | §6.4 | **E1** | JWKS 缓存 + 自省/吊销列表 |
| R6 | 下游信任白名单默认空 | P1-9 | **E1** | 边缘站点网关统一置为 fail-closed |
| R7/R8 | OM 轮换无效 / OpenLLM 权限不生效 | P1-6/7 | **E1** | 静态 Key 收敛的前置 |
| R11/R12 | `last_used` 未落库 / 时区比较 | P2 / P0-8 | **E1** | 随设备身份一起修 |
| R21 | claims 缓存导致降权延迟 | P2 | **E1** | 与吊销缓存同一机制 |
| R20/R16 | MCP 凭证约定 / 明文 Key | P2 | **E2** | 与安全存储一起做 |
| R17 | OpenLLM 本地用户双主 | P1-7 | **E2** | 边缘可延后 |
| 政务合规项 | 国密密评 / 统一身份 / 三权分立 / 集中审计 / 信创灾备 | 不适用 | **暂缓** | 非 R 台账项，政务交付再启用 |

### 10.7 E0 实施结果（v1.3.0，2026-10-29）

> 范围：仅 E0 七项轻量落地；E1/E2 与政务强合规项未动。全部改动均配套回归用例，且不改变既有对外契约（`/auth/me` 的超管判定改为显式权限点，见 E0-5 说明）。

| # | E0 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|---|
| 1 | 设备身份化 | 终端按设备签发 `sk-agent-*`（支持 `expires_at`，`last_used_at` 认证即落库）；未设有效期签发时输出运维提示（引导终端独立凭据、禁止共享服务 Key） | `identity/agent_keys.py`、`identity/__init__.py` | `tests/test_identity_t1.py::test_e0_1_*`、`::test_e0_7_*` |
| 2 | 下游直连禁止读原始 `X-User-Role`（R1） | `resolve_role_code` 删除请求头回退，仅采信 `state.identity` / 验签 JWT `role` / 本地会话角色 | OpenLLM `app/identity/rbac_guard.py` | OpenLLM `tests/unit/test_b1_rbac_wiring.py::TestE0DirectHeaderRoleNotTrusted` |
| 3 | 租户与 scope 生效（R2） | `require_api_key` 解析生效租户（受信 `X-Tenant-Id` → JWT `tenant_code`），租户受限 Key 未声明租户即 403 `PERM_API_KEY_SCOPE`（`reason=tenant_required`），跨站点拒绝 | `core/deps/auth.py` | `tests/test_proxy_auth.py::test_tenant_scoped_key_*`、`::test_untrusted_tenant_header_is_not_trusted` |
| 4 | Key 签发/吊销审计落库（R4） | 服务 Key 与 agent Key 的签发/吊销同事务写 `AuditLog`（`auth.service_key.issue/revoke`、`identity.agent_key.issue/revoke`，含 key_id/name/scope/操作人/request_id；不含明文与哈希） | `modules/auth/service_keys.py`、`modules/identity/agent_keys.py`、`modules/auth/__init__.py`、`modules/identity/__init__.py` | `tests/test_api_keys_api.py::test_api_key_lifecycle_writes_audit_without_plaintext`、`tests/test_identity_t1.py::test_e0_4_*` |
| 5 | admin 硬编码收敛（R5） | 新增显式超管权限点 `system:superadmin`（种子并授予内置 admin 角色）；管理面统一走 `ensure_user_permission`（payload + DB 矩阵 + 内置 admin 角色锚点），删除 5 处 `username=="admin"` 判定；`/auth/me` 按超管权限点回填 `*` | `modules/auth/rbac.py`、`core/db/init.py`、`identity/migration.py`、`auth/__init__.py`、`identity/__init__.py`、`tenant/__init__.py`、`users/__init__.py` | `tests/test_security.py::test_superadmin_permission_point_replaces_username_hardcode`、`tests/test_ui_increments.py::test_auth_me_returns_wildcard_for_admin` |
| 6 | 离线宽限策略 | 新增 `principal_cache_ttl_seconds`（默认 900s）与 `principal_offline_grace_hours`（默认 72h）；成功校验写 Redis 时间标记；DB 不可达/行缺失时——宽限内放行（留痕 `offline_grace`），超期写操作 fail-closed（503/401）、只读降级放行（留痕 `offline_grace_readonly`）；显式 reject 策略与白名单优先级不变 | `settings.py`、`identity/verification.py`、`core/deps/auth.py` | `tests/test_b4_security_hardening.py::test_e0_6_*` |
| 7 | 一键吊销 | agent Key 每请求查库校验（吊销即 401）；`last_used_at` 认证后显式提交；吊销时清理该主体 principal 快照缓存 | `identity/agent_keys.py` | `tests/test_identity_t1.py::test_t1_6_*`、`::test_e0_7_*` |

**兼容与残余**

- E0-5 行为差异：仅用户名 `admin`（无 admin 角色、无 `system:superadmin` 权限）的 JWT 不再自动获得通配权限——与「改名/多管理员场景失效」的整改目标一致；内置 admin 角色与 DB 种子 `*` 均不受影响。
- E0-6 依赖 Redis 时间标记；Redis 不可用时无标记 → 沿用既有环境/策略口径（不新增放行）。
- 未纳入本轮（按矩阵留 E1）：`ob_k_` 过期/轮换（R9）、吊销事件联动下游（R10）、agent Key `expires_at` 时区归一（R12）、列表租户过滤（R3）、明文吊销回显/前缀匹配/掩码键（R13/R14/R15）等。
- 环境提示：OpenLLM 本机 venv 的 `httpx` 需为 `0.26.0`（`requirements.txt` 钉版）否则 `starlette.TestClient` 端点用例不可执行；本轮已按钉版恢复该 venv 依赖。

### 10.8 E1 实施结果（v1.4.0，2026-10-29）

> 范围：E1 第 1~4 项（过期/轮换、Key 事件化、到期时区归一、列表租户过滤与低成本项）。第 5 项（非对称签名 JWT + JWKS + 自省/吊销列表）改动面大，单独评估后再排期。

| # | E1 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|---|
| 1 | `ob_k_` 过期/轮换（R9） | 新增 `expires_at`/`last_used_at`/`rotated_from`/`tenant_code` 列（存量库幂等 ALTER）；签发默认 90 天（`service_key_ttl_days`）；新增 `POST /auth/api-keys/{key_id}/rotate`（旧 Key 宽限 24h 默认、可覆盖，到期自动失效，双 Key 零中断）；校验按到期拒绝，认证通过记录 `last_used_at` | `core/models/base.py`、`identity/migration.py`、`modules/auth/service_keys.py`、`modules/auth/__init__.py`、`core/deps/auth.py`、`settings.py` | `tests/test_api_keys_api.py::test_e1_1_*`、`tests/test_proxy_auth.py::test_expired_api_key_rejected_at_proxy`、`::test_rotated_key_grace_zero_switches_immediately` |
| 2 | Key 事件化（R10） | 新增 `service_key.issued/rotated/revoked`、`agent_key.issued/revoked` 事件类型（与 user.* 分集，`ALL_VALID_EVENT_TYPES` 统一校验），签发/吊销/轮换同事务写 outbox，随 `GET /identity/events` 下发（下游可做缓存失效/告警）；载荷仅元数据（key_id/kind/name/scope），不含明文与哈希 | `identity/events.py`、`modules/auth/service_keys.py`、`identity/agent_keys.py` | `tests/test_api_keys_api.py::test_e1_2_service_key_events_enqueued`、`tests/test_identity_t1.py::test_e1_2_agent_key_events_enqueued` |
| 3 | 到期时区归一（R12/P0-8） | 新增 `core/timeutil.py`（`utc_now`/`as_utc`）；agent Key 与 service Key 的 `expires_at` 写入归一为 UTC aware、比较前归一，消除 SQLite naive/aware `TypeError` | `core/timeutil.py`、`identity/agent_keys.py`、`modules/auth/service_keys.py` | `tests/test_identity_t1.py::test_e1_3_expired_agent_key_rejected` |
| 4a | 列表租户过滤（R3） | 新增 `tenant_filter_code`（超管=None 不过滤 / 无绑定="" 不可见）；服务 Key 列表按归属租户过滤；用户/租户列表按调用方租户过滤；agent Key 读/写/吊销按租户隔离（跨租户 404，不泄露存在性） | `modules/auth/rbac.py`、`modules/auth/__init__.py`、`modules/users/__init__.py`、`modules/tenant/__init__.py`、`identity/agents.py`、`identity/__init__.py` | `tests/test_api_keys_api.py::test_e1_4_service_key_list_tenant_filter`、`tests/test_tenant_admin.py::test_e1_4_*`、`tests/test_security.py::test_e1_4_tenant_filter_code_semantics` |
| 4b | 低成本项（R13/R14/R15） | 明文吊销不回显明文（仅稳定 id）、未命中 404；`PUBLIC_PREFIXES` 改为路径段匹配（相似前缀不再误放行）；脱敏器补齐裸键 `key`/`raw_key`/`secret`（精确匹配，不误伤 `key_id`） | `modules/auth/__init__.py`、`core/deps/auth.py`、`core/mask.py` | `tests/test_api_keys_api.py::test_e1_4_revoke_by_raw_no_plaintext_echo_and_404`、`tests/test_security.py::test_e1_4_public_prefix_requires_path_segment`、`tests/test_mask.py::test_e1_4_exact_bare_key_names_are_masked` |

**兼容与残余**

- 存量 `ob_k_` 无到期时间（NULL）= 不过期，避免升级即全量失效；新签发默认 90 天，轮换可逐步收敛。
- 轮换宽限 24h 为默认值，可按 Key 传 `grace_hours`（0 = 立即切换）；旧 Key 到期时间只收紧不延长。
- Key 事件为 outbox 主通道（pending → dispatcher 投递 → published），`GET /identity/events` 仅返回 published 事件。
- 未纳入本轮：非对称签名 JWT/JWKS/自省/吊销列表（E1-5，建议单独排期）；下游静态 Key 收敛（R7/R8）、OM 轮换修复（R7）、设备配额与异常告警仍在 E1/E2 后续项。

### 10.9 E1-5A 实施结果（v1.5.0，2026-10-29）

> 范围裁定（人工确认）：**路径 A —— 控制面先行**。本轮只做 OpenBase 控制面（E1-5A），下游 OpenLLM → OpenMemory → OpenRAG/DPS 的逐仓接入为 **E1-5B**，本轮不做。
> 密钥形态裁定：**PEM 文件只读挂载 + 双验签过渡**。私钥经 `OPENBASE_JWT_RSA_PRIVATE_KEY_PATH` 挂载（禁止内联），新签发一律 RS256，存量 HS256 双验签过渡。

| # | E1-5A 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|---|
| 1 | RS256 签发 | 配置私钥后新签发一律 RS256（`kid` 头 + `iss`/`aud` claim）；未配置时保持原 HS256 形态（**HS256 不注入 iss/aud**，避免破坏既有直接解码方） | `core/security/jwt_keys.py`、`modules/auth/jwt.py`、`settings.py` | `tests/test_jwt_rs256.py::test_rs256_signing_carries_kid_and_standard_claims`、`::test_rs256_roundtrip_access_and_refresh_types` |
| 2 | 多 kid 验签 / 算法白名单 | 验签算法白名单 `{RS256, jwt_algorithm}`（拒绝 `alg=none`、拒绝算法混淆）；RS256 按 `kid` 选内置 JWKS 公钥，未知 kid fail-closed；HS256 回落 `jwt_secret`/`jwt_secret_previous` 宽限 | `modules/auth/jwt.py`、`core/security/jwt_keys.py` | `::test_rs256_rejects_unknown_kid`、`::test_hs256_token_cannot_pass_as_rs256`、`::test_legacy_hs256_token_still_verifies_during_transition` |
| 3 | JWKS 发布 | 新增公开端点 `GET /.well-known/jwks.json`（仅公钥分量 kty/n/e，`use=sig`），签发公钥由私钥派生自动发布；`jwt_jwks_public_keys` 可登记历史/过渡 kid 公钥（JSON 或 `@文件`），支持平滑换钥 | `modules/auth/token_api.py`、`core/deps/auth.py`、`core/security/jwt_keys.py` | `tests/test_jwt_rs256.py::test_jwks_document_exposes_public_material_only`、`::test_extra_public_key_registered_and_verifiable`、`tests/test_auth_token_api.py::test_jwks_is_public_and_exposes_rs256_key` |
| 4 | 令牌内省 | 新增 `POST /api/v1/auth/introspect`（RFC 7662 语义）：服务 Key 鉴权（scope `system` 含 `auth`/`*`）+ 验签 + 主体状态/token 版本核查；无效/过期/类型不符返回 `active=false` 与 `reason`，**不做结果缓存**（吊销必须即时可见） | `modules/auth/token_api.py`、`core/deps/auth.py` | `tests/test_auth_token_api.py::test_introspect_reports_active_token`、`::test_introspect_verifies_principal_state_and_token_version`、`::test_introspect_token_type_mismatch` |
| 5 | 吊销增量 | 新增 `GET /api/v1/auth/revocations?since=&limit=`（服务 Key 鉴权）：按各表 `updated_at` 升序增量下发主体 `token_version`/状态、服务 Key、agent Key 变化，返回 `next_since` 游标；单页上限 `jwt_revocations_page_limit`（默认 500） | `modules/auth/token_api.py`、`settings.py` | `tests/test_auth_token_api.py::test_revocations_snapshot_shape_and_incremental_cursor`、`::test_revocations_requires_service_key` |
| 6 | 配置门禁 | 新增 `jwt_rsa_private_key_path`/`jwt_signing_kid`/`jwt_issuer`/`jwt_audience`/`jwt_jwks_public_keys`/`jwt_require_rs256`/`jwt_revocations_page_limit`；配私钥必填 kid 且文件须可解析为 RSA 私钥；`jwt_require_rs256=true` 缺配置即拒绝启动 | `settings.py`、`core/security/jwt_keys.py` | `tests/test_jwt_rs256.py::test_require_rs256_without_key_rejected`、`::test_private_key_without_kid_rejected`、`::test_missing_private_key_file_rejected`、`::test_invalid_extra_public_keys_rejected`、`::test_revocations_page_limit_must_be_positive` |

**兼容与残余**

- 过渡策略：本轮不改变默认行为 —— 未配置 PEM 时 HS256 签发/验签与升级前完全一致（存量令牌与既有直接解码方零影响）；配置 PEM 后新签发 RS256，同时仍接受 HS256 存量令牌。
- 双验签窗口收口：确认全量令牌换发后可移除 `jwt_secret*` 与 `jwt_jwks_public_keys` 中的历史 kid，并将 `jwt_require_rs256` 置 true（生产第二段门禁）。
- 换钥流程：替换 PEM 文件即生效（按 `mtime` 缓存失效，无需重启）；旧 kid 公钥在 JWKS 保留至存量令牌过期。
- **未纳入本轮（E1-5B，下游逐仓灰度）**：OpenLLM / OpenMemory / OpenRAG / DPS 的 JWKS 拉取与本地验签、内省/吊销增量对齐、部署编排（环境变量与 PEM 挂载）。
- 内省无缓存属有意取舍：高频批量场景应调用 revocations 增量对齐，避免逐令牌读库。

### 10.10 E1-5B 实施结果（v1.6.0，2026-10-29）

> 范围：E1-5A 交付的 JWKS / 内省 / 吊销增量在下游逐仓接入，按裁定顺序 **OpenLLM → OpenMemory → OpenRAG → DPS** 推进。四仓统一实现「本地验签 OpenBase RS256 令牌 + 保留本仓 HS256 存量通道」，配置默认留空 = 不启用（升级零行为变化）。

| 仓库 | 落点 | 行为差异 | 验证证据 |
|---|---|---|---|
| OpenLLM | `backend/app/security/openbase_jwt.py`（新）；接入 `services/auth_service.get_current_user` 与 `/openllm` 网关 JWT 通道（`api/openllm_gateway.py`） | 本仓 HS256 优先，失败回落 OpenBase RS256；`sub` 需经 `OPENBASE_SUBJECT_MAP` 映射为本地 User UUID，未命中即 401（`OPENBASE_TRUST_LOCAL_SUBJECT` 仅同库部署开启）；PEM 私钥不落本仓（只验签） | `backend/tests/unit/security/test_openbase_jwt.py`（12 项）+ 既有 jwt/gateway/auth 单测回归（72 项通过；`test_gateway_401_format.py` 7 项为**基线既有**不一致，非本次改动） |
| OpenMemory | `src/openmemory/gateway/openbase_jwks.py`（新）；`gateway/gateway.py::_decode_jwt` 分流；`utils/config.py` / `api/server.py` 配置透传 | RS256 优先于既有共享密钥通道；`tenant_code` 归一为 `tenant_id`；无本地用户映射（按 `sub` 隔离） | `tests/unit/test_gateway_openbase_jwks.py`（8 项）+ `test_gateway.py`（14 项） |
| OpenRAG | `src/openrag/api/middleware/openbase_jwt.py`（新）；`api_key.py` 前置 Bearer 验签；`identity_gate.py` 派生 principal；`main.py` / `settings.py` 装配 | 新增可选 Bearer 通道（原仅 X-API-Key）；验签通过写 `jwt_principal` 并派生 `auth_method=jwt`，失败回落 X-API-Key；未配置时行为不变 | `tests/unit/api/test_openbase_jwt_bearer.py`（11 项）+ 既有 API Key 中间件（9 项） |
| DPS | `src/identity/openbase_jwt.py`（新）；`rest_api/routes/routes_auth.py::_decode_token` 回落；`src/config.py` 新增 `DPS_OPENBASE_*` | 本仓 HS256 优先，OpenBase RS256 回落；`sub` 经 `DPS_OPENBASE_SUBJECT_MAP` 映射、`tenant_code` 归一为 `org_id`；不映射 `tvn → tv`（吊销以 OpenBase 为权威） | `src/tests/test_e15b_openbase_jwt.py`（9 项）+ IAM 会话版本/DB 用户回归（12 项） |

**统一契约（四仓一致）**

- 仅接管 `alg=RS256`；JWKS 按 `kid` 选公钥，未知 kid 强制刷新一次后拒绝；TTL 缓存默认 300s；`iss=openbase`、`aud=openbase-api`、`exp` 强校验（含 leeway）。
- 配置缺失（JWKS URL 为空）= 通道关闭，行为与升级前完全一致。
- 主体映射失败一律拒绝（fail-closed），不做"猜测式"用户名回退。
- 日志只记录失败原因，不记录令牌内容。

**兼容与残余**

- 双验签过渡：四仓均保留各自 HS256 通道；待 OpenBase 全量 RS256 换发后可关闭 HS256 通道。
- 内省/吊销增量：OpenBase 已提供 `POST /api/v1/auth/introspect` 与 `GET /api/v1/auth/revocations`；下游本轮**未**接入轮询（以离线验签 + 短 TTL 令牌为主，吊销由 OpenBase 侧即时生效兜底），后续按需接入。
- 部署编排（PEM 只读挂载、下游 `*_OPENBASE_JWKS_URL` 注入、`*_SUBJECT_MAP` 映射）由部署配置执行；本轮仅在各仓 `.env.example` / 环境配置说明登记，OpenBase 仓内无统一 compose 文件。
- 待裁定：OpenBase **终端用户**令牌直连下游的主体映射策略（显式映射表 vs 同库信任）；当前默认要求显式映射，未配置即拒绝。

**补充（v1.6.1，2026-10-30）：OpenLLM 验签入口收口**

- 新增 `services/auth_service.verify_bearer_token` 统一入口（本仓 HS256 优先 → 失败回落 OpenBase RS256/JWKS），`get_current_user` 与 WebSocket 认证改用该入口（原先仅 HTTP 依赖与服务网关两处覆盖）。
- `edgerouter/auth/jwt_handler.py::verify_token` 增加 RS256 分支：`/api/v1/auth/verify`、edge router 自建 handler 同步获得 OpenBase 验签能力；HS256 路径逐字不变。
- `refresh_token` 链保持只接受本仓 `type=refresh`，OpenBase 令牌（`type=access`）无法用于换发本仓 token（防越权）。
- 网关删除已冗余的二次回落（能力下沉后单一入口）。
- 验证：`tests/unit/edgerouter/test_jwt_handler.py` 新增 4 项、`tests/unit/security/test_openbase_jwt.py` 新增 3 项；auth_service / 网关 / jwt_redis 回归 95 项通过；`test_gateway_401_format.py` 7 项仍为基线既有不一致。

## 11. 修订历史

| 版本 | 日期 | 作者 | 说明 |
|---|---|---|---|
| v1.0.0 | 2026-10-29 | FA-OpenBase-Dev（AI 辅助） | 首版：四系统 API Key 与授权全生命周期静态审计（7 环节 + 分工矩阵 + 17 项风险 + P0/P1/P2 方案 + 验收标准） |
| v1.1.0 | 2026-10-29 | FA-OpenBase-Dev（AI 辅助） | 纳入"下游 API/MCP 可独立对外使用"约束：目标架构改为**单一控制面 + 双模数据面**（代理路径 + 直连验证适配层）；新增 §6.4 凭证形态/受众、JWKS/自省/吊销列表契约、MCP 传输约定与双模一致性；P1 计划重排（离线验签能力 + 下游统一适配层）；新增 R18~R21 风险与"双模一致/独立接入"验收项 |
| v1.2.0 | 2026-10-29 | FA-OpenBase-Dev（AI 辅助） | 明确适用场景为 **AI 边缘终端**：新增 §10 附录 A（场景约束、E0/E1/E2 轻量落地、离线宽限与一键吊销、政务强合规项暂缓及启用触发条件）；不改动既有风险清单与 P0 项 |
| v1.2.1 | 2026-10-29 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.6「R / P / E 三套编号关系与追溯矩阵」：明确 R=风险台账、P=通用修复排期、E=边缘场景执行计划，同一风险只修一次；逐条给出风险到 E0/E1/E2/暂缓的映射 |
| v1.3.0 | 2026-10-29 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.7「E0 实施结果」：七项轻量落地逐条记录落点与回归证据（E0-2 OpenLLM 移除 `X-User-Role` 回退；E0-3 服务 Key 租户 scope；E0-4 Key 生命周期审计落库；E0-5 `system:superadmin` 显式超管；E0-6 离线宽限 72h/缓存 900s；E0-7 last_used 提交与吊销缓存清理；E0-1 设备凭据有效期提示），并登记行为差异、残余（E1）与环境提示 |
| v1.4.0 | 2026-10-29 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.8「E1 实施结果（第 1~4 项）」：`ob_k_` 默认 90 天到期 + 轮换端点（宽限 24h）+ 认证记录 last_used；Key 生命周期事件（service_key.*/agent_key.*）入 outbox 并随 `/identity/events` 下发；到期时间 UTC 归一；列表按租户过滤（服务 Key/用户/租户/agent）与低成本项（明文吊销不回显、路径段白名单、掩码补裸键）；登记兼容策略与残余（E1-5 JWKS/自省单独排期） |
| v1.5.0 | 2026-10-29 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.9「E1-5A 实施结果」：按裁定路径 A 落地控制面非对称签名 —— RS256 签发（kid/iss/aud）+ 多 kid JWKS + 算法白名单双验签（HS256 存量过渡）+ `GET /.well-known/jwks.json` + `POST /api/v1/auth/introspect` + `GET /api/v1/auth/revocations` 增量；新增 RS256 配置门禁与 `jwt_require_rs256` 启动检查；登记兼容策略与残余（E1-5B 下游逐仓接入本轮不做） |
| v1.6.0 | 2026-10-29 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.10「E1-5B 实施结果」：OpenLLM / OpenMemory / OpenRAG / DPS 四仓接入 OpenBase RS256/JWKS 本地验签（统一契约：kid 选择、未知 kid 强制刷新、iss/aud/exp 强校验、主体映射 fail-closed、默认留空不启用），各仓保留 HS256 存量通道；登记双验签过渡、内省/吊销增量未接入下游、部署编排边界与「用户令牌直连映射」待裁定项 |
| v1.6.1 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | §10.10 补充「OpenLLM 验签入口收口」：新增 `auth_service.verify_bearer_token` 统一入口覆盖 HTTP 依赖与 WebSocket；RS256 分支下沉 `JWTHandler.verify_token`（`/api/v1/auth/verify`、edge router 同步生效）；refresh 链拒绝 OpenBase 令牌换发；删除网关冗余二次回落；登记新增 7 项用例与回归结果 |

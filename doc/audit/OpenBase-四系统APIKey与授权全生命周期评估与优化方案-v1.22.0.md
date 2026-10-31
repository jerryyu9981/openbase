# OpenBase 四系统 API Key 与授权全生命周期评估与优化方案

| 项目 | 内容 |
|---|---|
| 文档编号 | AUDIT-AUTH-20261029 |
| 版本 | v1.22.0 |
| 状态 | [Review] |
| 适用场景 | **AI 边缘终端为主**（多终端、算力/存储受限、网络间歇、本地推理、现场物理暴露）；政务项中纯软件部分已实施（E3），硬件/密评项暂缓 |
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
- MCP 边缘服务：HTTP 走 Bearer、stdio 由宿主注入短期令牌；工具级 `scope.tools` 过滤。**（v1.8.0 已落地，见 §10.12）**
- 设备配额与异常告警（同一 Key 多 IP、异地登录、调用量突增）。**（v1.8.0 已落地，见 §10.12）**

### 10.4 E2（按需）

- TPM/安全元件存私钥；固件与模型签名校验；远程擦除；安全启动。**（依赖终端宿主能力，未代码化；控制面吊销/封禁已具备，见 §10.13）**
- 数据落盘加密（本地 SQLite/缓存）；日志防篡改（链式哈希）。**（日志链式哈希 v1.9.0 已落地、多实例写入串行化 v1.10.0 已闭合；本地落盘加密依赖终端代理，见 §10.13）**
- 政务项原「暂缓」部分中纯软件可完成项（国密可插拔、统一 IdP 抽象、三权分立/ABAC、集中审计导出与留存）已作为 **E3 落地（v1.11.0，见 §10.14）**；硬件/密评/平台联调项仍暂缓（见 §10.5）。

### 10.5 政务项：E3 可软件落地部分（v1.11.0 已实施）

原「暂缓项」按「纯软件可完成 / 依赖硬件或密评」二分重排。**可软件部分已作为 E3 落地**
（见 §10.14），不再整体挂起；仍需硬件、密码机或第三方测评的部分继续保持暂缓。

| 项 | 原暂缓原因 | E3 处理（v1.11.0） | 仍需暂缓的部分 |
|---|---|---|---|
| 国密算法 | 需密码机与密评 | **签名算法注册表可插拔**：HS256/RS256 已接线，SM2 登记为预留位；配置 SM2/未知算法即启动拒绝（fail-fast，禁静默降级） | 真实 SM2 签名原语接线（gmssl/密码机）与密评 |
| 统一身份认证平台 | 当前无外部 IdP | **IdP Provider 抽象层**：多 Provider JSON 登记 + 启动门禁 + 只读视图（绝不下发 `client_secret`）；既有单 IdP `oidc_*` 行为不变 | 与省级/部门平台的实际联调与证书交换 |
| 三权分立 + ABAC | 边缘场景角色简单 | **职责互斥校验 + ABAC 判定**：`system_admin`/`security_admin`/`audit_admin` 两两互斥（权限点基线不重叠）；ABAC deny-overrides、跨租户默认拒绝、无命中回落 RBAC；试算与职责清单端点 | 组织级角色授予流程改造与全量策略运营 |
| 集中审计平台 / 留存 | 无独立审计系统 | **集中审计导出与留存**：NDJSON 流式导出（条数受配置上限约束，含链式哈希可离线复核）；按留存天数清理（默认 dry-run、删头不断链、`0` 表示未启用并拒绝清理） | 独立审计平台对接、等保测评要求的留存介质与异地备份 |
| 信创适配 / 异地灾备 | 非边缘首要矛盾 | 未处理 | 国产化目录/容灾要求（依赖基础设施） |

### 10.6 三套编号的关系（R / P / E 追溯矩阵）

**先分清三套编号的定位：**

| 编号 | 是什么 | 回答的问题 |
|---|---|---|
| **R1~R21** | **风险台账**（发现的问题/缺陷） | "系统现在有什么问题？" |
| **P0 / P1 / P2** | **通用场景的修复排期**（企业/平台视角） | "这些问题按什么优先级修？" |
| **E0 / E1 / E2 / E3** | **AI 边缘终端场景的执行计划**（对 P 的裁剪与重排；E3 = 政务项中可纯软件落地部分） | "在当前交付形态下，先做什么、后做什么、什么暂缓？" |

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
| R20/R16 | MCP 凭证约定 / 明文 Key | P2 | **E2** | 与安全存储一起做；**v1.9.0 已闭合**（摘要/文件注入） |
| R17 | OpenLLM 本地用户双主 | P1-7 | **E2** | 边缘可延后；**v1.9.0 已闭合**（身份权威开关） |
| 政务合规项 | 国密密评 / 统一身份 / 三权分立 / 集中审计 / 信创灾备 | 不适用 | **E3（软件部分）/ 暂缓（硬件与密评）** | 非 R 台账项；可软件落地部分 v1.11.0 已实施，见 §10.14 |

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

### 10.11 E1-5C 实施结果（v1.7.0，2026-10-30）

> 范围（按 §10.3 E1 计划顺序推进）：**吊销增量同步**在四仓落地 + 控制面游标语义修复。MCP 边缘凭证、设备配额与异常告警仍为 E1 后续项。

| 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| 游标语义修复 | `next_since` 回退 1ms（同一毫秒内多行更新的边界不漏读；重复由消费端按主键幂等覆盖） | OpenBase `modules/auth/token_api.py` | `tests/test_auth_token_api.py::test_revocations_snapshot_shape_and_incremental_cursor`（新增不变量断言） |
| OpenLLM 吊销对齐 | `subject_revoked()`：状态非 `active` 或快照 `token_version` 高于令牌 `tvn` → 拒绝；同步失败沿用旧快照（离线可用）；`OPENBASE_REVOCATION_STRICT` 严格模式 | `app/security/openbase_jwt.py`、`app/core/config.py` | `tests/unit/security/test_openbase_jwt.py`（+4 项，合计 19 项） |
| OpenMemory 吊销对齐 | `OpenBaseRevocationSync`（实例级，网关配置驱动）；RS256 分流后判定 | `gateway/openbase_jwks.py`、`gateway/gateway.py`、`utils/config.py`、`api/server.py` | `tests/unit/test_gateway_openbase_jwks.py`（+3 项，合计 11 项） |
| OpenRAG 吊销对齐 | `OpenBaseRevocationSync` 注入 `OpenBaseJwtVerifier`，验签后判定 | `api/middleware/openbase_jwt.py`、`config/settings.py`、`main.py` | `tests/unit/api/test_openbase_jwt_bearer.py`（+3 项，合计 14 项） |
| DPS 吊销对齐 | 模块级吊销快照 + `verify_for_local` 判定；新增 4 项 `DPS_OPENBASE_*` 配置 | `identity/openbase_jwt.py`、`config.py`、`doc/release/DPS-环境配置说明-v2.8.0.md` | `src/tests/test_e15b_openbase_jwt.py`（+3 项，合计 12 项；IAM 回归 12 项） |

**统一判定口径**：状态非 `active` → 拒绝；快照 `token_version` > 令牌 `tvn` → 拒绝（降权即时生效）；快照未命中 → 默认放行（边缘离线可用，短 TTL 令牌兜底），`*_REVOCATION_STRICT=true` 时拒绝。

**残余**

- 下游同步为**请求触发的惰性拉取**（按间隔节流），无独立后台线程：无流量时不同步；如需空闲期收敛，后续补调度任务。
- E1 §10.3 第 3/4 条（MCP 边缘凭证与工具级 `scope.tools`、设备配额与异常告警）以及 R6 下游信任白名单 fail-closed、R7/R8 静态 Key 收敛仍待排期。**（v1.8.0 已全部闭合，见 §10.12）**

### 10.12 E1-6/E1-7 实施结果（v1.8.0，2026-10-30）

> 范围（§10.3 第 3/4 条 + §10.6 中 R6/R7/R8 三项）：MCP 边缘凭证与工具级授权、Key 异常告警、四仓生产 fail-closed 门禁、OpenMemory 轮换闭环、OpenLLM Key 权限与配额生效。E2 与政务强合规项未动。

| 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| E1-6 MCP 边缘凭证 | HTTP 通道三形态：静态 `X-API-Key`（存量兼容）→ 服务 Key `ob_k_*`（`scope.system` 含 `mcp`）→ 短期 JWT（`type=access`，`Authorization: Bearer`）；stdio 通道由宿主注入 `OPENBASE_MCP_TOKEN_FILE`（优先）或 `OPENBASE_MCP_TOKEN`，缺失/非 access/过期一律 401（fail-closed） | OpenBase `modules/mcp/credentials.py`（新）、`modules/mcp/__init__.py`、`modules/mcp/stdio.py`（新） | `tests/test_mcp_edge_credentials.py`（6 项）+ `test_three_modules.py` / `test_obs_mcp.py` 回归 25 项 |
| E1-6 工具级授权 | `scope.tools` 白名单：`tools/list` 按白名单过滤；`tools/call` 二次校验——HTTP 层 403 `PERM_API_KEY_SCOPE`，JSON-RPC 层 `isError=true` + 协议码 `-32001`；`tools=None` 表示不限（静态 Key 存量语义），`*` 通配 | 同上 | 同上（含越权调用、system 不含 mcp、JWT scope 用例） |
| E1-6 Key 异常告警 | 进程内窗口检测三类信号：`multi_ip`（窗口内不同 IP 数超阈值）、`ip_prefix_change`（IP 网段跳变，作为异地登录近似）、`rate_spike`（60s 调用量超阈值）；同类告警冷却抑制；**只告警不阻断认证**；落 `AuditLog`（`auth.service_key.anomaly`）+ 结构化 WARN，写库失败回滚且不影响请求 | OpenBase `modules/auth/key_anomaly.py`（新）、`core/deps/auth.py`、`settings.py`（6 项配置：开关/窗口 900s/多 IP 3/限速 600 rpm/冷却 300s/是否采信 XFF 默认 False） | `tests/test_key_anomaly.py`（7 项：网段归一、多 IP、网段跳变、突增+冷却、开关、审计写入、写入失败回滚）+ `test_rbac_deps` / `test_auth` / `test_inbound_header_gate` 回归 |
| R6 四仓生产门禁 | 生产 profile 漏配即拒绝启动：OpenLLM `TRUSTED_PROXY_SOURCES` 非空；OpenRAG `enforce_inbound_identity_headers=true` + `trusted_proxy_sources` 非空 + `role_fail_closed=true`；DPS enforce 已开时 `TRUSTED_PROXY_SOURCES` 非空；OpenMemory 同款口径并入 `validate_gateway_security_policy` | OpenLLM `app/core/config.py`；OpenRAG `config/settings.py`、`main.py`；DPS `src/config.py`；OpenMemory `utils/config.py`、`api/server.py` | OpenLLM `tests/unit/test_r6_r8_api_key_failclosed.py`（23 项，含 R8）；OpenRAG `tests/unit/test_c4_production_gate.py`（11 项）；DPS `src/tests/test_r6_trusted_proxy_fail_closed.py`（5 项）+ `test_c4_production_gate.py`（6 项）；OpenMemory `tests/unit/test_gateway_openbase_jwks.py`（22 项） |
| R7 OpenMemory 轮换闭环 | 轮换记录**摘要落盘**（仅 SHA-256，原子替换 + 0600 权限尽力设置），先落盘后提交内存状态（持久化失败不产生"假轮换"）；`rotated` 记录 5 分钟宽限期内仍可用；`verify_key()` 供路由 / API Key 中间件 / 网关同源校验；网关新增 `managed_api_key_validator` 注入；生产三拒绝（`allow_unverified_gateway_token`、`oidc_mode=gateway` 无验签材料、无 API Key） | OpenMemory `admin/service.py`、`admin/routes.py`、`api/server.py`、`gateway/gateway.py`、`utils/config.py`、`.env.example` | `tests/unit/test_gateway_openbase_jwks.py`（+8，合计 22 项） |
| R8 OpenLLM Key 权限与配额 | 认证通过后写 `request.state.api_key`（id + permissions）；`rbac_guard.api_key_permissions/api_key_permits` 支持 `*`、精确码、`module:*`、read/write 粗粒度，作为**权限上限先于 `is_admin()` 放行**；`rate_limit` 按 Key 令牌桶（`rate_limit` 摘要缓存 300s、键 `requests_per_minute`、容量/填充 = rpm）覆盖用户级默认额度，超限 429 + `Retry-After` | OpenLLM `app/services/auth_service.py`、`app/identity/rbac_guard.py`、`app/middleware/rate_limit.py` | `tests/unit/test_r6_r8_api_key_failclosed.py`（23 项，与 R6 共用文件） |

**统一口径**

- 生产门禁一律在**装配期**抛出（`RuntimeError` / `ValueError`），拒绝以"仅 WARN"的形式带病启动；非生产行为不变。
- 异常检测与配额缓存均为**单进程内存**实现，不做跨实例共享；失败路径统一降级（告警记录失败不影响认证，配额缓存未命中回退用户级默认）。
- MCP 令牌只校验 `type=access` 且必须带 `exp`；不校验 `tvn`（终端离线宽限由令牌短 TTL 兜底）。

**残余**

- MCP 工具级权限**仅作用于 MCP 路由**（`/mcp/tools*`、`/mcp/json-rpc`）；OpenBase 其他管理端点不受 `scope.tools` 约束。静态 `settings.mcp_api_keys` 维持"不限工具"存量语义，未强制绑定 `scope.tools`。
- 异常检测为进程内滑动窗口 + 冷却，**不跨实例、不持久化**；多实例部署需中心化聚合（与集中审计平台一并排期）。异地登录以 IP 网段跳变为近似，非地理定位；默认不采信 `X-Forwarded-For`，仅部署在受信代理后才可开启 `key_anomaly_trust_forwarded_for`。
- OpenLLM Key 配额缓存为单进程内存，多进程各自计数；跨实例精确配额需 Redis 令牌桶（后续）。
- OpenMemory 落盘只存摘要：进程重启后 `get_active_key()` 不再返回 active 明文（返回 `None`），运维须在轮换响应中即时登记新密钥。
- 验证边界：OpenRAG 全量 pytest 因运行环境缺 `structlog` 无法收集，本仓门禁用「命名空间 stub 装载 `settings.py`」的等价断言验证（11 项通过），未伪造全量通过；OpenLLM 全量 unit 存在既有环境性失败（`SECRET_KEY` 空、PostgreSQL 5432 不可用等），均未命中本次改动路径。

### 10.13 E2 实施结果（v1.9.0 / v1.10.0，2026-10-30）

> 范围（§10.4 E2 + §10.6 中 R16/R17/R20）：审计日志链式哈希（防篡改）、MCP 静态 Key 去明文、OpenLLM 身份权威收敛。**硬件/终端宿主项（TPM、安全启动、固件与模型签名、本地落盘加密、远程擦除）未代码化**，理由与替代控制见文末。

| 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| 审计日志防篡改（链式哈希） | `AuditLog` 增 `prev_hash` / `entry_hash`（String(64)，可空）；新增 `before_flush` 监听器统一为全部 17 处插入点计算链式摘要（`entry_hash = sha256(prev_hash | canonical_payload)`）；规范化序列化（固定字段序 + `sort_keys` + 紧凑分隔符）；新增 `GET /api/v1/audit/chain/verify?limit=1..10000`（超管权限点 `system:superadmin`）返回 `ok/checked/first_broken_id/reason` | OpenBase `core/db/audit_chain.py`（新）、`core/models/base.py`、`core/models/__init__.py`、`modules/audit/__init__.py` | `tests/test_audit_chain.py`（8 项：连续链、篡改定位、删行断裂、遗留 NULL 行跳过、同批 flush 链、空表）+ 审计相关回归 53 项 + `test_api_keys/test_db_modules/test_app/test_logs_endpoints_api` 79 项 |
| 审计链多实例写入串行化 | flush 前**先取 PostgreSQL 事务级 advisory lock**（`pg_advisory_xact_lock(:lock_key)`，锁键 `AUDIT_CHAIN_LOCK_KEY`，随事务提交/回滚自动释放），再读末条哈希并插入，使「读后写」在多实例/多进程下严格串行；非 PostgreSQL 方言（SQLite 单写者）不取锁直接放行；锁键为绑定参数，不拼接 SQL | OpenBase `core/db/audit_chain.py` | `tests/test_audit_chain.py`（新增 3 项：SQLite 放行、PG 分支参数化 SQL、flush 钩子「先锁后读」顺序）+ 审计链/审计相关/Key 相关回归 126 项 |
| R16/R20 MCP 静态 Key 去明文 | 静态 Key 三来源：明文 `OPENBASE_MCP_API_KEYS`（**仅开发**）、摘要 `OPENBASE_MCP_API_KEY_HASHES`（SHA-256，生产推荐）、宿主注入文件 `OPENBASE_MCP_API_KEYS_FILE`（每行一个，`#` 注释，mtime 缓存 + 锁）；摘要比对用 `hmac.compare_digest`（不用 `in`）；**生产门禁三条**：禁止 `dev-mcp-key`、禁止任何明文 Key、摘要与文件至少其一 | OpenBase `settings.py`、`modules/mcp/credentials.py` | `tests/test_mcp_edge_credentials.py`（原 6 + 新增 6：摘要命中/错误 Key、文件注入与重载、文件不可读降级、生产拒绝明文、生产缺来源、摘要格式非法）+ `test_three_modules` / `test_obs_mcp` 回归 |
| R17 OpenLLM 身份双主收敛 | 新增 `IDENTITY_AUTHORITY`（`local` 默认 / `openbase`）；`openbase` 下 `/auth/login`、`/auth/register`、`/auth/refresh`、`/auth/change-password` 一律 403（本地开户/口令登录/令牌换发关闭，身份唯一来源为 OpenBase JWT）；一致性门禁：`openbase` 必须配置 `OPENBASE_JWKS_URL`（与环境无关，杜绝切换后无身份来源）；默认 `local` 行为零变化 | OpenLLM `backend/app/core/config.py`、`backend/app/api/auth.py` | `backend/tests/unit/test_r17_identity_authority.py`（9 项）+ `test_auth_api.py` 24 项 + 配置/兼容门禁 67 项回归 |
| 既有失败用例修正 | `tests/test_settings.py` 两条生产构造用例原即失败（生产默认 `dev-mcp-key` 触发 E1-6 门禁）；补显式 MCP 凭证来源后恢复绿色（断言意图不变） | OpenBase `tests/test_settings.py` | `tests/test_settings.py` 全通过 |

**统一口径**

- 链式哈希在 `Session.before_flush` 单点挂钩，插入点零改动；`id` 不参与哈希（自增主键写入前不可知），行序完整性由 `prev_hash` 链承担。
- 多实例写入以 PostgreSQL 事务级 advisory lock 串行化（v1.10.0）：取锁 → 读末条哈希 → 插入在同一事务内完成，事务结束自动释放；锁粒度是「整条链」而非单表，审计写入本为低频事件，不构成吞吐瓶颈。SQLite 部署沿用单写者模型，不取锁。
- 存量库兼容：启用前历史行两列为 NULL，校验时跳过；两列由初始化链 `init_database` 末尾的幂等迁移自动补齐（v1.12.0 §10.15），生产升级无需手工执行 DDL。
- 生产 MCP 门禁与既有 `dev-mcp-key` 拒绝口径叠加：生产要么只存摘要、要么用宿主注入文件，配置泄漏不再等于凭证泄漏。
- 身份权威开关默认 `local`，升级零行为变化；切换 `openbase` 后本地身份表只停写不删，销户以 OpenBase 为准。

**残余（未在本轮闭合）**

- ~~审计链**多实例并发写入**为「读末条哈希 → 插入」语义，存在链分叉可能~~ → **v1.10.0 已闭合**：PostgreSQL 事务级 advisory lock 串行化「读末条 + 插入」，多实例/多进程写入保持单链；非 PG（SQLite）依赖其单写者模型。仅余一项部署约束：同一链条的写入必须连接**同一 PostgreSQL 实例**（主备切换后新主已接管全链，链仍连续；跨库分片写入不适用本机制）。
- 终端宿主项：TPM/安全元件存私钥、安全启动、固件与模型签名校验、终端本地 SQLite/缓存落盘加密、远程擦除——这些能力位于终端代理/宿主固件，不在本四仓代码范围。控制面已提供替代控制：主体吊销与封禁（E0-7/E1 Key 事件）、令牌短 TTL 与吊销增量同步（E1-5C）、JWKS 离线验签（E1-5B）；终端本地擦除需终端代理在下一次联网/OTA 时执行删除并上报。
- MCP 静态 Key 文件为明文注入（0600），读取后仅进程内保存；如需 Root of Trust 级保护，仍依赖 E2 的 TPM 宿主项。
- OpenLLM `local` 模式下本地 `users/tenants/teams` 仍为主数据（默认路径）；生产应采用 `openbase` 模式并在部署编排中固定该开关。

### 10.14 E3 实施结果（v1.11.0，2026-10-30）

> 范围（原 §10.5 暂缓项中**纯软件可完成**的部分）：三权分立 + ABAC、集中审计导出与留存、SM2 可插拔预留、统一 IdP Provider 抽象层。**不改动既有鉴权主路径**：`require_permission` / `ensure_user_permission` 行为不变，ABAC 以「试算 + 策略接入点」形态提供；单 IdP `oidc_*` 配置行为不变。需要密码机、密评、第三方平台联调、信创/灾备基础设施的部分仍暂缓（见 §10.5）。

| 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| E3-1 三权分立 | 三职责 `system_admin` / `security_admin` / `audit_admin` 两两互斥；`conflicting_duty_pairs` 列冲突对、`assert_separation_of_duties` 冲突即抛 `SeparationOfDutiesError`（fail-closed）；三职责权限点基线互不重叠；`GET /api/v1/auth/access/duties` 暴露职责与基线（需 `security:admin` 或超管） | OpenBase `modules/auth/access_control.py`（新）、`modules/auth/access_api.py`（新）、`modules/auth/__init__.py`（挂载） | `tests/test_e3_governance.py`（冲突对/三职责互斥/基线不重叠/职责端点） |
| E3-1 ABAC | 策略 JSON 数组（`OPENBASE_ABAC_POLICIES`）；规则字段 `effect/permission/roles/tenant/cross_tenant`；判定语义 **deny-overrides** → 跨租户默认拒绝（仅显式 `cross_tenant` 放行）→ allow → `not_applicable`（回落 RBAC）；非法 JSON/字段在**所有环境**启动拒绝；`POST /api/v1/auth/access/check` 试算并返回可解释 `reason` | 同上 + `settings.py`（`_validate_e3_governance_configuration`） | 同上（deny 覆盖、allow、无命中、跨租户默认拒绝/显式放行、角色与租户约束、试算端点、启动门禁） |
| E3-2 集中审计导出 | `GET /api/v1/audit/export`：NDJSON 流式（`StreamingResponse`，按 `id` 升序逐行输出），参数 `since/until/limit`；单次条数上限取 `OPENBASE_AUDIT_EXPORT_MAX_ROWS`（默认 10000），超限返回 `PARAM_INVALID`；时间区间倒置拒绝；每行含 `prev_hash`/`entry_hash` 可离线复核；权限与链校验同源（`system:superadmin`） | OpenBase `modules/audit/__init__.py` + `settings.py` | `tests/test_e3_governance.py`（流式行序/`X-Row-Limit`/since 过滤/超限/区间倒置） |
| E3-2 审计留存清理 | `POST /api/v1/audit/retention/purge`：`dry_run` 默认 `true`（只统计）；`OPENBASE_AUDIT_RETENTION_DAYS=0` 表示未启用并**拒绝**清理（`BIZ_CONFIG_CONFLICT`）；非 0 必须 ≥30 天（责任期下限，启动门禁）；删除仅针对 `created_at < cutoff` 的最旧头部行，**删头不断链**（链校验从剩余首行重新起算）；操作落结构化 INFO 日志 | 同上 + `settings.py` | 同上（未启用拒绝、dry-run 计数、真实删除、清理后 `verify_audit_chain` 仍 `ok`） |
| E3-3 SM2 可插拔 | 签名算法注册表：`HS256`/`RS256` 可用、`SM2` 登记为预留不可用（需 `gmssl`/密码机原语）；`register_signature_algorithm` 支持显式 `replace`；启动门禁 `_validate_signature_algorithm`：未知算法或不可用算法（含 SM2）即拒绝启动，**绝不静默降级** | OpenBase `core/security/signature_algorithms.py`（新）、`settings.py` | 同上（注册表可用性、SM2 断言拒绝、未知算法、重复登记语义、settings 门禁） |
| E3-4 IdP Provider 抽象 | `OPENBASE_IDP_PROVIDERS`（JSON 数组）登记多 Provider：`name/discovery_url/client_id/client_secret/redirect_uri/scopes/profile/claim_role/default_tenant`；启动门禁校验 JSON 合法、名称唯一、必填项齐全、`profile` ∈ {`generic`,`keycloak`}；`GET /api/v1/auth/idp/providers` 只读视图（登录用户可读），**绝不下发 `client_secret`**，仅暴露 `has_client_secret`；默认留空 = 仅既有单 IdP `oidc_*` | OpenBase `modules/auth/idp_registry.py`（新）、`modules/auth/__init__.py`（挂载）、`settings.py` | 同上（合法/非法解析、名称唯一、profile 校验、视图无密钥、端点无明文） |

**新增配置项（均有默认值，缺省行为零变化）**

| 配置 | 默认 | 语义 |
|---|---|---|
| `OPENBASE_ABAC_POLICIES` | 空 | ABAC 策略 JSON 数组；空 = 无属性策略（判定回落 RBAC） |
| `OPENBASE_AUDIT_RETENTION_DAYS` | `0` | `0` = 不清理；非 0 必须 ≥30 |
| `OPENBASE_AUDIT_EXPORT_MAX_ROWS` | `10000` | 单次导出条数上限（正整数） |
| `OPENBASE_IDP_PROVIDERS` | 空 | 多 IdP Provider 登记 JSON 数组 |

**统一口径**

- ABAC 是**前置判定/试算**能力，不替代 RBAC：返回 `not_applicable` 时由 RBAC 继续判定；策略接入点可由后续管理面按需调用，本轮不改既有端点鉴权链。
- 三权分立提供**校验函数与基线**，角色授予入口的强制调用属于组织流程改造（本轮未强制接入 `role:grant` 路径，避免改变既有行为）。
- 审计导出/清理均走 `get_db` 请求级会话与 SQLAlchemy 参数化查询，不拼 SQL；清理为不可逆操作，默认 dry-run 且权限与链校验同源。
- SM2 与 IdP 均为**登记层**：真实签名原语、外部平台联调、证书交换不在本仓代码范围，配置到即 fail-fast 而非假装可用。

**残余（未在本轮闭合）**

- SM2 **仅登记未接线**：`JWT` 签发/验签仍只有 HS256/RS256；启用国密需接入 `gmssl`/密码机原语并补标准映射（JWS 未定义 SM2）。
- IdP Provider **仅登记与只读展示**：多 Provider 的登录路由选择、回调分流、租户映射仍走既有单 IdP `oidc_*` 流程；与省级平台的实际联调、证书轮换未做。
- ~~ABAC 策略**无管理写端点**（本轮只读试算/自检），策略变更走配置下发；策略规模增长后需要独立的策略 CRUD 与生效审计~~ → **v1.13.0 已闭合**（§10.16）：新增 `abac_policy_rules` 表与 `/api/v1/auth/access/policies` CRUD，写入与审计同事务；``OPENBASE_ABAC_POLICIES`` 配置基线保留为只读兜底，两者合并判定。
- 三权分立**未强制接入角色授予路径**：`role:grant` 当前不调用 `assert_separation_of_duties`，组织侧需在授权流程中显式校验（后续可加管理面门禁）。
- 留存清理为**同一数据库内的按时间删除**：跨库归档、对象存储冷备、审计介质合规留存（等保≥6 个月）仍需集中审计平台/基础设施配合。
- 验证边界：E3 新增 4 个模块与审计导出/清理端点以**文件型 SQLite + 依赖覆写**验证（`tests/test_e3_governance.py` 23 项），未做真实 PG 多实例并发导出压测；本文件与相关回归（E3 新增 + `test_settings` + `test_audit_chain` 共 53 项，审计/鉴权相关回归 75 项）全部通过，ruff 0 错误。

### 10.15 A3 存量迁移闭环（v1.12.0，2026-10-30）

> 目的：闭合 §10.13 登记的「存量库 `audit_logs` 两列需手工执行 DDL」残余（ER-27），让生产升级路径不依赖人工 DDL，避免升级窗口漏执行导致链校验不可用。

| 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| A3-1 幂等补列 | 初始化链末尾的 `apply_identity_migration` 新增 `audit_logs` 增量列补齐（`_AUDIT_CHAIN_NEW_COLUMNS`：`prev_hash` / `entry_hash`，`VARCHAR(64)` 可空）；以 `inspect.get_columns()` 判定列存在性，缺列才 `ALTER TABLE ... ADD COLUMN`，重放时 `columns_added` 为空 | `openbase/modules/identity/migration.py` | `tests/test_identity_t1.py`（存量库补列 + 重放幂等 + 历史行保持 NULL） |
| A3-2 PG schema 限定 | 复用 `_qualify(schema, table)`，PG 语句为 `ALTER TABLE "openbase".audit_logs ADD COLUMN ...`，既有 schema 隔离与 SQLite（`schema=None`）分支不变 | 同上 | `tests/test_identity_t1.py`（FakeConn 断言带 schema 限定 SQL） |
| A3-3 注释与初始化链同源 | `AuditLog` 模型注释由「手工 DDL」改为「初始化链自动补列」；迁移模块 docstring 登记新增列项 | `openbase/core/models/base.py`、`openbase/modules/identity/migration.py` | ruff 0 错误 + 相关回归全通过 |

**统一口径**

- 两列可空、存量行保持 NULL：链校验按「跳过 NULL」语义，升级后即可启用校验，无需回填历史数据（回填会破坏历史完整性语义）。
- 迁移内联于 `init_database`（`create_tables → 基础种子 → apply_identity_migration`），应用启动与建库脚本共用同一入口，不存在「迁移需另行调用」的漂移。
- 生产升级无需手工 DDL；若运维在不动应用的窗口预置同名列，迁移因列已存在而跳过，两种路径可安全共存。

**残余**

- 真实 PG 存量库升级仅以文件型 SQLite + FakeConn 语句断言验证，未做生产 PG 演练；该演练由 A1-12 验收项覆盖（预生产快照 → 启动即补列 → 链校验 `ok`）。

### 10.16 ABAC 策略写端点（ER-24 闭合，v1.13.0，2026-10-30）

> 目的：闭合 §10.14 登记的「ABAC 无管理写端点，策略变更只能走配置下发」残余。判定语义保持不变，新增的只是**运行期策略存储与变更留痕**。

| 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| 策略持久化 | 新表 `abac_policy_rules`（`name` 唯一 / `effect` / `permission` / `roles` / `tenant` / `cross_tenant` / `enabled` / `version` / 操作人与时间戳）；`create_all` 幂等建表，随初始化链生效，无手工 DDL | `openbase/core/models/base.py`（`AbacPolicyRule`）、`openbase/core/models/__init__.py` | `tests/test_e3_governance.py`（建表后 CRUD 全链路） |
| 合并判定 | `/check` 与判定层改为「DB 启用行 ∪ `OPENBASE_ABAC_POLICIES` 基线」；deny-overrides、跨租户默认拒绝、无命中 `not_applicable` 回落 RBAC 全部不变；`enabled=false` 不参与判定 | `openbase/modules/auth/abac_policy_store.py`（新）、`access_api.py` | 同上（deny 覆盖基线 allow；停用即失效） |
| 写端点 | `GET/POST/PUT/DELETE /api/v1/auth/access/policies`：均需 `security:admin` 或超管；字段校验复用配置解析口径（`parse_abac_rules`）；名称重复 `BIZ_CONFLICT`、缺失 `BIZ_NOT_FOUND`、非法字段 `PARAM_INVALID`；更新时 `version` 自增 | `openbase/modules/auth/access_api.py` | 同上（CRUD、409/404/400、版本自增） |
| 变更留痕 | 新增/更新/删除与 `AuditLog` 同事务提交（`access.abac_policy.create/update/delete`，`resource=abac_policy`），审计失败即整体回滚，不产生「策略已改无留痕」 | `abac_policy_store.py` | 同上（三类动作按序入库） |

**统一口径**

- **默认零行为变化**：表内无规则时判定结果与仅用配置完全一致；配置基线仍是启动期门禁来源，运行期策略不替代它。
- 策略表只承载**运行期新增**规则，配置文件不做回写；两条路径同时存在时以判定语义（而非顺序）决定结果。
- 每次变更都带操作人（非数字主体记 `None` 但审计仍留痕）与 `version`，便于管理面做覆盖检测与追溯。

**残余**

- 策略**变更审批流**（双人复核）未实现：当前仅单点授权 + 审计留痕，四眼原则需接入组织流程或后续审批端点。
- 策略规模与命中性能未做压测：规则全量加载后线性判定，规则量级增长到千条以上需引入索引/缓存策略。
- 验证边界：仍以文件型 SQLite + 依赖覆写验证（`tests/test_e3_governance.py` 新增 3 项），未做真实 PG 多实例并发写策略压测。

### 10.17 OIDC P1 安全硬化（v1.14.0，2026-10-30）

> 目的：不改动 OIDC 主体流程（授权码交换 / JIT 建号 / 角色白名单 / 状态机拦截），补齐上线前必须解决的安全与多实例缺口：state 仅进程内存且无 TTL、缺少 nonce/PKCE、验签算法写死 `RS256`。

| 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| state 一次性 + TTL | 新增 `OidcStateStore`：优先 Redis（`SET EX` 写入、`GETDEL` 原子消费）；Redis 不可用回退进程内字典（线程锁 + 到期清理 + 单次弹出）；state 缺失/过期/重复消费统一 400 | `openbase/modules/auth/oidc_state.py`（新）、`oidc.py` | `tests/test_oidc_hardening.py`（一次性消费、TTL 过期） |
| nonce | authorize 下发 `nonce` 并与 state 同存；callback 校验 ID Token `nonce`，缺失或不一致 → 401 `AUTH_401_INVALID` | `oidc.py` | 同上（匹配/不匹配/缺失）+ `test_oidc_gateway` 全链路 |
| PKCE | 默认开启 S256：authorize 携带 `code_challenge` / `code_challenge_method=S256`，callback 换 token 携带 `code_verifier`；`OPENBASE_OIDC_PKCE_ENABLED=false` 可对不支持 IdP 关闭 | `oidc.py`、`settings.py` | RFC 7636 附录 B 向量 + 两条全链路用例 |
| 算法白名单 | `OPENBASE_OIDC_SIGNING_ALGORITHMS`（默认 `RS256`）与 discovery `id_token_signing_alg_values_supported` 取交集；无交集拒绝换取令牌，配置未接线算法（含 SM2）启动即拒绝 | `oidc.py`、`settings.py`（`OIDC_ID_TOKEN_ALGORITHMS` / `_validate_oidc_hardening_configuration`） | 同上（交集/无交集/启动门禁） |
| 错误码统一 | OIDC 端点由 `HTTPException` 改为 `BaseError`：未启用 `BIZ_404`(404)、state/参数非法 `PARAM_INVALID`(400)、上游失败 `SYS_502`(502)，响应统一 `{code,message,detail,request_id}` | `oidc.py` | 同上（错误码与响应键集断言） |

**新增配置（均有默认值，缺省行为零变化）**

| 配置 | 默认 | 语义 |
|---|---|---|
| `OPENBASE_OIDC_STATE_TTL_SECONDS` | `600` | state 一次性消费有效期（正整数） |
| `OPENBASE_OIDC_PKCE_ENABLED` | `true` | PKCE S256 开关（不支持 PKCE 的 IdP 可关闭） |
| `OPENBASE_OIDC_SIGNING_ALGORITHMS` | `RS256` | ID Token 验签算法白名单（RS/ES 系列，逗号分隔，须与 IdP 声明取交集） |

**统一口径**

- 保留既有 `_bind_or_create_user` / `_ensure_roles` / 状态机拦截 / `issue_token_pair` 全部不变，只在外围增加校验，不重写 OIDC 主体。
- Redis 不可用时 state 回退进程内：单实例可用；多实例回调可能落到未持有 state 的实例而失败（WARN 留痕），多实例部署须保证 Redis 可用。
- nonce 为强制校验（授权请求下发即要求 ID Token 回写），不提供降级开关，避免静默失去重放防护。
- 既有拟真回调用例（`test_identity_t2` T2-6 三项、`test_identity_t3` T3-3）同步适配一次性 state：改为 `get_state_store().issue(...)` 登记 nonce，桩 `exchange_code` 接受 `code_verifier` 关键字，断言目标（停用拦截 / claims 齐备）不变。

**残余**

- 多 Provider 登录路由已由 §10.18（v1.15.0）接入（`provider` 查询参数 + state 携带 Provider）；单 IdP `oidc_*` 语义保持零变化。
- 签名算法仅覆盖 python-jose 已接线的 RS/ES 系列；SM2 仍未接线（见 E3-3）。
- IdP 侧登出已由 §10.19（v1.16.0）接入前端信道 `end_session`（本地 `token_version` 递增 + 可选登出 URL）；**back-channel logout（IdP 主动通知网关）仍未实现**。
- token endpoint 认证方式已由 §10.20（v1.17.0）扩展为 `client_secret_post` / `client_secret_basic` / mTLS（默认 post，零行为变化）。
- 验证边界：以 mock IdP + 文件型 SQLite 验证（新增 12 项，OIDC 相关共 30 项通过），未做真实 IdP 联调（由 A1 清单覆盖）。

### 10.18 多 Provider 登录路由（v1.15.0，2026-10-30）

> 目的：把 E3-4 已登记的 `OPENBASE_IDP_PROVIDERS` 从「只读视图」推进到真实登录流程——同一网关可同时对接多个 IdP（政务统一身份平台 / 企业 IdP），而单 IdP `oidc_*` 路径零行为变化。

| 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| authorize 选择 Provider | `GET /api/v1/auth/oidc/authorize` 新增可选 `provider` 查询参数；指定时按 Provider 声明的 discovery / client_id / secret / 回调 / scopes 构建授权 URL | `oidc.py`（`_resolve_oidc_client` / `_get_provider_client`） | `tests/test_oidc_multi_provider.py`（URL 端点与 client_id 断言） |
| 客户端按需构建与缓存 | Provider 客户端按名称缓存；Provider 声明变更（dataclass 等值比较）即重建，避免缓存旧凭据 | `oidc.py`（`_provider_clients`） | 同上 |
| state 携带 Provider | state 载荷新增 `provider` 名，与 nonce / code_verifier 同一生命周期（一次性 + TTL） | `oidc.py`、`oidc_state.py`（复用） | 同上（`consume` 断言 provider/nonce） |
| callback 还原 Provider | 回调按 state 中的 Provider 还原客户端；profile / claim_role / default_tenant 取自 Provider 声明，JIT 绑定按 issuer 天然隔离不同 IdP 主体 | `oidc.py`（`oidc_callback`） | 同上（全链路 corp-idp → 统一 JWT claims + `/auth/me`） |
| 未登记口径 | 指定 provider 但**未登记任何 Provider** → 400 `PARAM_INVALID`；名称未登记 → 400 `PARAM_INVALID`（不得静默回落单 IdP） | `oidc.py` | 同上（两条负向用例） |
| 单 IdP 零变化 | 不传/传空 `provider` 仍走既有 `oidc_*` 单客户端路径（含 authorize 响应结构，仅在 Provider 模式追加 `provider` 字段） | `oidc.py` | 既有 `test_oidc_gateway.py` 全链路回归通过 |

**新增配置**

无新增配置项；复用 `OPENBASE_IDP_PROVIDERS`（JSON 数组，启动门禁见 §10.14 / E3-4）与既有 `OPENBASE_OIDC_*`（PKCE / 算法 / 前端回调等全局项仍由 `oidc_*` 控制）。

**统一口径**

- 全局 `oidc_enabled` 仍为 OIDC 功能总开关；Provider 模式在其之上再要求 discovery / client_id 齐备。
- Provider 未声明 `redirect_uri` 时回退全局 `oidc_redirect_uri`（所有回调仍落在同一网关端点，state 决定实际 Provider）。
- Provider 声明的 `client_secret` 仅存于配置，不下发只读视图（§10.14 `public_provider_views` 口径不变）。

**残余**

- Provider 区间主体隔离依赖 issuer（`OidcIdentity` 唯一键 `(issuer, sub)`）；同一 issuer 下多 client 仍视为同一身份空间，需 IdP 侧保证 issuer 唯一。
- Provider 级 PKCE / 签名算法不支持独立配置（沿用全局 `oidc_pkce_enabled` / `oidc_signing_algorithms`）。
- 验证边界：两个 mock IdP（9012/9013）+ 降级直签路径，未做真实政务/企业 IdP 双环境联调。

### 10.19 IdP 登出联动（v1.16.0，2026-10-30）

> 目的：闭合 §10.17 登记的「IdP 登出后本地 refresh 仍有效」残余——登出时本地即时吊销，并可按需返回 IdP `end_session` 地址，使浏览器会话与网关令牌同时结束。

| 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| 登出端点 | 新增 `POST /api/v1/auth/oidc/logout`（需登录态）；可选 `provider` / `post_logout_redirect_uri` 查询参数 | `oidc.py`（`oidc_logout`） | `tests/test_oidc_multi_provider.py` |
| 本地即时吊销 | 本地主体（数字 `sub`）`token_version += 1` 并提交；强校验开启后存量 access / refresh 立即失效；DB 不可达 / OIDC 直签字符串主体 → 跳过（返回 `token_version: null`，仍完成登出） | `oidc.py`（`_revoke_local_tokens`） | 同上（递增 / 非数字主体跳过） |
| IdP 会话登出 | 取 discovery `end_session_endpoint` 拼接 `client_id`（可选 `post_logout_redirect_uri`）；IdP 未声明或不可达 → `idp_logout_url: null`（尽力而为，不回滚本地吊销） | `oidc.py`（`build_logout_url`） | 同上（Provider 登出 URL 断言） |
| 错误口径 | 未登录 → 401；`provider` 未登记 → 400 `PARAM_INVALID`；指定 Provider 但 OIDC 未启用 → 404（均在吊销前判定，不产生半登出态） | `oidc.py` | 同上（未鉴权 / 未知 Provider） |

**新增配置**

无新增配置项（复用 `OPENBASE_IDP_PROVIDERS` 与 `OPENBASE_OIDC_*`）。

**统一口径**

- 前端凭据（localStorage）清除仍由调用方负责；本端点不维护服务端黑名单。
- `token_version` 递增的即时失效效果依赖 `OPENBASE_ENFORCE_TOKEN_VERSION=true`（生产门禁已强制，见 A2 §2.3）；非生产未开启时新版令牌仍可续签，但旧 refresh 在主体版本校验路径下不再兼容。
- 不实现 IdP 主动回调的 **back-channel logout**：需 IdP 侧配置 logout token 与网关回调端点，列为残余。

**残余**

- back-channel logout（IdP 主动通知）未实现，IdP 直接注销会话时网关侧令牌仍依赖本地登出或过期。
- 未保存 IdP 侧 `id_token_hint`，部分 IdP 可能要求该参数才能静默登出（如需可在前端回调时留存 ID Token 后透传）。
- 验证边界：mock IdP 校验 URL 构造与本地吊销分支，未做真实 IdP 登出联调。

### 10.20 token 端点认证方式扩展（v1.17.0，2026-10-31）

> 目的：闭合 §10.17 登记的「token endpoint 仅 `client_secret_post`」残余——按 IdP 实际要求支持 HTTP Basic 与 mTLS 客户端认证，默认 post 保持零行为变化。

| 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| 认证方式配置 | 新增 `OPENBASE_OIDC_TOKEN_AUTH_METHOD`（`client_secret_post` / `client_secret_basic` / `mtls`，默认 post），取值归一为小写 | `settings.py` | `tests/test_oidc_token_auth.py`（门禁用例） |
| client_secret_basic | 凭据经 `Authorization: Basic`（httpx `BasicAuth`），表单**不重复**携带 `client_id` / `client_secret`（RFC 6749 §2.3.1） | `oidc.py`（`token_payload` / `token_request_options`） | 同上（载荷断言 + mock IdP 记录到 basic 全链路） |
| mTLS | 客户端证书 / 私钥（PEM）经 httpx `cert` 装配，可选 CA 经 `verify`；表单仅带 `client_id`（RFC 8705） | `oidc.py`（`token_request_options`） | 同上（请求选项装配单元用例） |
| 默认 post | 未配置时表单携带 `client_id` + `client_secret`，请求选项为空（既有行为完全不变） | `oidc.py` | 同上（默认 post 全链路） |
| 启动门禁 | 方式非法 → 拒绝启动；mtls 缺证书/私钥路径或文件不存在 → 拒绝启动（含可选 CA 文件） | `settings.py`（`_validate_oidc_token_auth_configuration`） | 同上（4 项门禁用例） |

**新增配置**

| 项 | 默认 | 说明 |
|---|---|---|
| `OPENBASE_OIDC_TOKEN_AUTH_METHOD` | `client_secret_post` | token 端点客户端认证方式；`client_secret_basic` / `mtls` 按 IdP 要求选择 |
| `OPENBASE_OIDC_CLIENT_CERT_PATH` | 空 | mTLS 客户端证书（PEM；证书与私钥合并为一个文件时只需本项） |
| `OPENBASE_OIDC_CLIENT_KEY_PATH` | 空 | mTLS 客户端私钥（PEM） |
| `OPENBASE_OIDC_CLIENT_CA_PATH` | 空 | 可选：校验 IdP token 端点的 CA 包（留空用系统默认信任库） |

**统一口径**

- 认证方式为**全局配置**（同一网关对所有 Provider 采用同一方式）；多 Provider 若需差异化认证，需后续在 Provider 声明中扩展字段。
- mTLS 只覆盖 token 端点请求；授权端点为浏览器重定向，不参与双向 TLS。
- `mtls` 的证书/私钥/CA 路径在启动时校验存在性，运行期不重复探测（挂载变更需重启）。

**残余**

- `tls_client_auth` 已由 §10.22 闭合。
- mTLS 未做真实双向 TLS 端到端联调（测试覆盖请求选项装配与启动门禁；链路验证依赖 A1 真实 IdP 联调）。
- 验证边界：mock IdP 端口 9014，覆盖 post / basic 全链路；mTLS 族为单元级验证。
- `private_key_jwt` 已由 §10.21 闭合。

### 10.21 private_key_jwt 客户端断言（v1.18.0，2026-10-31）

> 目的：闭合 §10.20 登记的「未实现 `private_key_jwt`」残余——面向仅接受 RFC 7523 JWT 客户端断言、不支持共享密钥的 IdP，默认配置与其他方式零行为变化。

| 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| 认证方式配置 | `OPENBASE_OIDC_TOKEN_AUTH_METHOD` 追加 `private_key_jwt`（取值仍归一为小写） | `settings.py`（`OIDC_TOKEN_AUTH_METHODS`） | `tests/test_oidc_token_auth.py`（门禁用例） |
| 客户端断言 | 表单携带 `client_id` + `client_assertion_type`（固定 URN `urn:ietf:params:oauth:client-assertion-type:jwt-bearer`）+ `client_assertion`；断言 RS256 签名，`iss`/`sub` = `client_id`，`aud` = discovery 的 token 端点，带 `iat`/`exp`（300s）与 `jti` | `oidc.py`（`_build_client_assertion` / `token_payload`） | 同上（断言 claims/header 解码校验 + mock IdP 断言验签全链路） |
| 签名私钥 | `OPENBASE_OIDC_CLIENT_PRIVATE_KEY_PATH`（PEM 只读挂载，禁止入库/入日志）；可选 `OPENBASE_OIDC_CLIENT_ASSERTION_KID` 写入 JWT header `kid`（multi-key IdP 轮换用） | `settings.py` / `oidc.py` | 同上（header `kid` 断言） |
| 请求选项 | 认证材料全部在表单，httpx 请求选项为空（与默认 post 同） | `oidc.py`（`token_request_options`） | 同上 |
| 启动门禁 | `private_key_jwt` 缺私钥路径或文件不存在 → 拒绝启动 | `settings.py`（`_validate_oidc_token_auth_configuration`） | 同上（3 项门禁用例，含大写/带空白归一） |

**新增配置**

| 项 | 默认 | 说明 |
|---|---|---|
| `OPENBASE_OIDC_CLIENT_PRIVATE_KEY_PATH` | 空 | `private_key_jwt` 必填：断言签名私钥（PEM，只读挂载） |
| `OPENBASE_OIDC_CLIENT_ASSERTION_KID` | 空 | 可选：写入断言 JWT header 的 `kid`（留空不带） |

**统一口径**

- 断言算法固定 `RS256`（与 IdP 公钥登记一致；不引入额外算法配置，避免与 ID Token 算法白名单混淆）。
- 断言每次 token 请求现签现用，`jti` 随机、有效期 300s；私钥每次读取文件，不常驻内存（挂载轮换无需重启即可生效）。
- 该方式不发送 `client_secret`；IdP 必须登记本客户端公钥。

**残余**

- 断言算法不支持 ES256 等非 RSA 曲线（如需按 IdP 要求扩展，再增配置项）。
- 未做真实 IdP 的 `private_key_jwt` 联调（测试用 mock IdP 验签断言，链路验证依赖 A1 真实 IdP）。
- 验证边界：mock IdP 端口 9014，断言签名与受众校验在全链路中执行。

### 10.22 tls_client_auth 客户端认证（v1.19.0，2026-10-31）

> 目的：闭合 §10.20 登记的「未实现 `tls_client_auth`」残余——RFC 8705 §2.1 的 PKI 证书方式：IdP 以证书 subject DN（或 SAN）绑定客户端身份，证书由受信 CA 签发，可在不修改 IdP 登记的前提下轮换证书（同一 subject）。

| 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| 认证方式配置 | `OPENBASE_OIDC_TOKEN_AUTH_METHOD` 追加 `tls_client_auth`（取值仍归一为小写）；与 `mtls` 同属「需客户端证书」族（`OIDC_CERTIFICATE_TOKEN_AUTH_METHODS`） | `settings.py`（`OIDC_TOKEN_AUTH_METHODS` / `OIDC_CERTIFICATE_TOKEN_AUTH_METHODS`） | `tests/test_oidc_token_auth.py`（载荷/门禁用例） |
| 传输装配 | 复用 mTLS 传输：httpx `cert`（证书+私钥）+ 可选 `verify`（CA）；请求形态按 RFC 8705 §2 携带 `client_id`、不发送 `client_secret` | `oidc.py`（`token_request_options` / `token_payload`） | 同上（请求选项与载荷断言） |
| subject 绑定校验 | 新增 `OPENBASE_OIDC_CLIENT_CERT_SUBJECT`（RFC 4514 DN 字符串）；配置后启动期加载证书并比对 subject（分隔符空白与大小写不敏感），不匹配即拒启 | `settings.py`（`_client_certificate_subject` / `_normalize_distinguished_name` / 门禁） | 同上（匹配通过、不匹配拒启、非 PEM 拒启） |
| 启动门禁 | `tls_client_auth` 缺证书/私钥路径、文件不存在、证书不可解析、subject 不匹配 → 拒绝启动 | `settings.py`（`_validate_oidc_token_auth_configuration`） | 同上（4 项门禁用例） |

**新增配置**

| 项 | 默认 | 说明 |
|---|---|---|
| `OPENBASE_OIDC_CLIENT_CERT_SUBJECT` | 空 | 可选：期望的客户端证书 subject DN（如 `CN=openbase-gateway,O=Example`）；留空则跳过本地比对（IdP 侧仍执行绑定） |

**统一口径**

- `mtls` 与 `tls_client_auth` 传输装配完全相同，差异在 IdP 的证书登记方式：`mtls` 对应自签证书/公钥登记（RFC 8705 §2.2 `self_signed_tls_client_auth` 族的传输侧），`tls_client_auth` 对应 PKI 证书 + subject/SAN 登记；二者均按 RFC 8705 §2 在表单携带 `client_id`。
- subject 比对为**启动期本地预检**，用于提前暴露证书/配置错位；最终绑定仍以 IdP 校验为准（DN 规范化差异可能导致本地宽松通过，不影响 IdP 判定）。
- 证书与私钥按 PEM 只读挂载，禁止入库/入日志；CA 留空时使用系统信任库。

**残余**

- ~~未实现 SAN 型绑定的本地预检（`tls_client_auth_san_dns/_uri/_ip/_email`，均属 IdP 侧登记字段）。~~ → v1.20.0 §10.23 C-01 已闭合。
- 未做真实双向 TLS 端到端联调（本地预检 + 传输选项断言为当前验证边界；真实链路依赖 A1 真实 IdP 联调）。
- 验证边界：mock IdP 端口 9014，不承担 TLS 握手；`tls_client_auth` 为单元级验证。

### 10.23 OIDC 残余闭合（P1 批次 C-01~C-05，v1.20.0，2026-10-31）

> 目的：按《残余项统一处置方案 v1.0.2》§3.1 推进 P1 批次，闭合 §10.22/§10.21/§10.19 登记的 5 项 OIDC 残余。全部新增配置**缺省即零行为变化**，且均进入启动门禁。

| 编号 | 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|---|
| C-01 | `tls_client_auth` SAN 型绑定本地预检 | 新增 `OPENBASE_OIDC_CLIENT_CERT_SAN_DNS` / `_URI` / `_IP` / `_EMAIL` 四项期望值；配置后启动期解析证书 SAN 并逐项比对（DNS/EMAIL 大小写不敏感、IP 经 `ipaddress` 归一、URI 精确匹配；期望值须在对应类型 SAN 中存在，证书无 SAN 即拒启）；四项全空则跳过（IdP 侧仍为准） | `settings.py`（`_certificate_san_values` / `_san_value_matches` / `_load_client_certificate` / 门禁） | `tests/test_oidc_p1_residuals.py`（DNS 大小写命中、DNS/IP 不匹配拒启、四类 SAN 全命中、证书无 SAN 拒启、全空跳过，6 例） |
| C-02 | `private_key_jwt` 断言算法扩展 | 新增 `OPENBASE_OIDC_CLIENT_ASSERTION_ALGORITHM`（默认 `RS256`，可选 `ES256` / `ES384`）；启动期校验私钥类型与曲线（RS\* 须 RSA；ES256 须 EC P-256；ES384 须 EC P-384；非 PEM 不可解析即拒启）；断言 JWT header 按所选算法编码 | `settings.py`（`_assert_private_key_matches_algorithm` / `OIDC_CLIENT_ASSERTION_ALGORITHMS`）、`oidc.py`（`assertion_algorithm()` / `_build_client_assertion`） | 同文件（默认 RS256、HS256 拒启、RS256+EC 拒启、ES256+RSA 拒启、P-256/P-384 匹配与错配、非 PEM 拒启、断言算法落地，7 例） |
| C-03 | 回调保存 ID Token 并在登出透传 | 授权码回调成功后按 `client_id + 主体 sub` 保存 ID Token（Redis 优先 + 进程内兜底，TTL 取 `refresh_expire_seconds`），并以 `sid` / IdP `sub` 建索引；RP-Initiated Logout 时读取并按 issuer 校验后作为 `id_token_hint` 透传，登出成功后清除 | `openbase/modules/auth/oidc_logout.py`（`OidcLogoutStore`）、`oidc.py`（`oidc_callback` / `build_logout_url` / `oidc_logout`） | 同文件（存储 roundtrip/issuer 校验/sid 索引/TTL=0、回调保存→登出带 hint→登出后清除，5 例） |
| C-04 | back-channel logout 端点 | 新增 `POST /api/v1/auth/oidc/backchannel-logout`（RFC 8471）：按未验签 `iss`/`aud` 定位候选 IdP（无候选或 IdP 未声明支持 → 404 `BIZ_NOT_FOUND`），验签（算法取 discovery `backchannel_logout_signing_alg_values_supported` → 回退 ID Token 算法白名单），校验 `events` / 无 `nonce` / `jti` 一次性（Redis `set(nx)` + 进程内兜底）/ `sub` 或 `sid`；按 `sid`/IdP `sub` 映射本地主体并吊销其令牌，DB 不可达时如实返回 `revoked=false` | `openbase/modules/auth/oidc.py`（`_verify_logout_token` / `_validate_logout_claims` / `_read_logout_token` / 路由）、`oidc_logout.py`（`consume_jti` / `subject_for_sid` / `subject_for_idp_sub`） | 同文件（有效 200、JSON body、jti 重放 400、events/nonce/jti/sub\|sid 缺失 400、坏签名 400、IdP 不支持 404、未知 issuer 404、仅 sid、Provider 分支，10 例） |
| C-05 | Provider 级 PKCE / 签名算法 / 认证方式 | `OPENBASE_IDP_PROVIDERS` 条目新增 `pkce_enabled` / `signing_algorithms` / `token_auth_method` 三字段（布尔型 PKCE、算法大写去重且须已接线、认证方式须在 `OIDC_TOKEN_AUTH_METHODS` 内），非法值构造即 `ValueError`；未声明字段回落全局配置；Provider 客户端按 dataclass 等值缓存失效 | `openbase/modules/auth/idp_registry.py`（`IdpProviderConfig` / `_normalized_signing_algorithms` / `public_provider_views`）、`oidc.py`（`OIDCClient` 覆盖与回落） | 同文件（解析/归一、非法值拒绝、覆盖与回落、缓存重建、PKCE 关闭不带 challenge，7 例；另加 4 例断言辅助 = 共 39 例通过） |

**新增配置（缺省零行为变化）**

| 项 | 默认 | 说明 |
|---|---|---|
| `OPENBASE_OIDC_CLIENT_CERT_SAN_DNS` / `_URI` / `_IP` / `_EMAIL` | 空 | 可选：`tls_client_auth` 期望的证书 SAN 值；配置后启动期比对，任一不匹配即拒启；全空跳过本地预检 |
| `OPENBASE_OIDC_CLIENT_ASSERTION_ALGORITHM` | `RS256` | `private_key_jwt` 断言签名算法，可选 `RS256` / `ES256` / `ES384`；与私钥类型/曲线错配或非 PEM 即拒启 |

**门禁变化**

- 启动门禁 #6（`_validate_oidc_token_auth_configuration`）在原「证书存在性 + subject 比对 + 私钥存在性」之上，追加 **SAN 逐项比对** 与 **断言算法枚举 + 私钥类型/曲线校验**；非法值仍为「所有环境拒绝启动」。
- 断言算法与 ID Token 验签白名单解耦：前者只作用于客户端断言，后者仍由 `OPENBASE_OIDC_SIGNING_ALGORITHMS ∩ discovery` 决定。

**验证与门禁结论**

| 项 | 结果 |
|---|---|
| 用例 | `python -m pytest tests/test_oidc_p1_residuals.py` → **39 passed** |
| 静态检查 | 本环境 `.venv-test` 未安装 `ruff`（`No module named ruff`），**待具备环境补跑**；已在此如实登记 |
| 零行为变化 | 新增配置全部留空/默认时不改变既有链路（SAN 全空跳过、断言算法默认 RS256 等同 v1.18.0 行为、Provider 三字段留空回落全局） |
| 安全 | 私钥/证书/ID Token 均不落日志；存储键前缀 `openbase:` 且 TTL 到期即失效；jti 一次性防重放 |
| 降级 | Redis 不可用时登出存储与 jti 窗口回退进程内（单实例语义，跨实例依赖 Redis） |

**残余**

- 未做真实 IdP 的 SAN 绑定 / 断言算法 / back-channel logout 联调（归 A1 真实 IdP 联调项 V-13）。
- 跨实例 back-channel 去重与 hint 共享依赖 Redis（单实例降级为进程内）。
- C-03 的存储键采用「`client_id` + 统一主体 `sub`，issuer 内嵌 value」的等价实现，与《残余项统一处置方案》登记的 `issuer+sub+client_id` 键语义等价。

### 10.24 Key 生命周期残余闭合（P2 批次 C-06~C-10，v1.21.0，2026-10-31）

> 目的：按《残余项统一处置方案 v1.0.3》§3.2 推进 P2 批次，闭合 §10.12、§7.3 登记的 5 项 Key/授权运维残余。全部新增配置**缺省即零行为变化**，新增配置进启动门禁，新增端点沿用统一 `BaseError` 错误契约。

| 编号 | 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|---|
| C-06 | 静态 MCP Key 工具白名单 | 新增 `OPENBASE_MCP_API_KEY_TOOLS`（JSON 对象：键 = 静态 Key 的 SHA-256 摘要或明文别名，值 = 工具名数组；显式 `*` 表示全量）；命中静态 Key 后凭证携带 `tools` 白名单，未命中映射保持「不限工具」；非法 JSON / 非对象 / 空键 / 空数组 / 非字符串项在启动期即拒启 | `settings.py`（`parse_mcp_api_key_tools` + `_validate_mcp_edge_configuration`）、`modules/mcp/credentials.py`（`_match_static_key` / `_static_key_tools`） | `tests/test_p2_residuals.py`（空值/非法参数化/归一、摘要命中、明文别名、无映射保持不限、`*` 通配，8 例） |
| C-07 | Key 异常检测跨实例聚合 | 生产路径（`now is None`）优先 Redis 聚合：速率 `INCR` + 首次 `EXPIRE 60s`；IP 集合 `SADD` + `EXPIRE(window)` + `SCARD`/`SMEMBERS`；冷却键 `SET NX EX` 跨实例共享。Redis 不可达或调用异常时 WARN 并回退既有进程内滑动窗口；告警仍只告警不阻断 | `modules/auth/key_anomaly.py`（`_observe_redis` / `_redis_cooldown_allows` / `KeyAnomalyTracker.observe`） | 同文件（跨实例网段跳变 + 多 IP、跨实例速率突增、Redis 不可用回退、TTL 断言，4 例） |
| C-08 | 到期提醒与只读清单 | 新增只读端点 `GET /api/v1/auth/api-keys/expiring?within_days=`（默认 7、范围 1~365；返回有效且到期 ≤N 天与已过期 Key，按租户过滤）；`ServiceKeyService.emit_expiring_events` 投递 `service_key.expiring` 事件（Key + 日期去重：Redis `SET NX EX` 36h，不可用回退进程内集合）；轮换复用既有端点，不新增写路径 | `modules/auth/service_keys.py`（`list_expiring` / `emit_expiring_events` / `_claim_expiring_notification`）、`modules/auth/__init__.py`（端点）、`modules/identity/events.py`（事件枚举） | 同文件（到期/已过期/远期/无到期/跨租户过滤、同日去重与 Outbox 载荷，6 例） |
| C-09 | 审计对账（Key 侧） | `ServiceKeyService.reconcile` 统计签发/有效/吊销/过期四类计数，判定 `签发数 = 有效数 + 吊销数 + 过期数`；平衡 INFO、不平衡 ERROR，并写 `AuditLog(action=auth.service_key.reconcile)` 留痕；不做跨系统拒绝数比对（依赖 K-03） | `modules/auth/service_keys.py`（`reconcile` / `ACTION_SERVICE_KEY_RECONCILE`） | 同文件（平衡返回 balanced=True、置一条非终态制造不平衡返回 balanced=False 且审计落库，1 例） |
| C-10 | 统一角色字典契约端点 | 新增只读端点 `GET /api/v1/auth/roles/contract`（登录可读）：输出 `schema_version` / `source` / `unknown_code_policy=fail-closed` / `tiers` / `anchors` / `canonical_role_codes` / `local_role_aliases` / `roles`（角色码、档位、是否已映射、权限点）；锚点优先读 `config/role_tier_anchors.json`，读失败回落内置基线；DB 不可达时仅返回 canonical 码仍可读；响应不含任何密钥/密码 | `modules/auth/role_contract.py`（`build_role_contract` / `load_role_permissions`）、`modules/auth/__init__.py`（端点） | 同文件（结构/档位/权限点、未知码 `tier=None,mapped=False`、无敏感字段、DB 回退，3 例） |

**新增配置（缺省零行为变化）**

| 项 | 默认 | 说明 |
|---|---|---|
| `OPENBASE_MCP_API_KEY_TOOLS` | 空 | 静态 MCP Key 工具白名单 JSON；空 = 全部静态 Key 保持「不限工具」；生产建议显式绑定工具数组或显式 `*`；非法结构启动即拒启 |

**验证与门禁结论**

| 项 | 结果 |
|---|---|
| 用例 | `python -m pytest tests/test_p2_residuals.py` → **20 passed** |
| 回归 | Key 异常/API Key/Key API/MCP 凭证/观测 MCP/身份事件 7 套 **99 passed**；`test_identity_t5` **8 passed** |
| 静态检查 | 本环境未安装 `ruff`（`No module named ruff`），**待具备环境补跑**；已如实登记 |
| 零行为变化 | 白名单空 → `tools=None`；Redis 正常/异常两路径均保持「只告警不阻断」；到期清单与会话/对账均为只读；角色契约端点不新增写路径 |
| 安全 | 白名单比对沿用常量时间比较；日志不含 Key 明文/摘要原文；对账审计仅落计数；契约响应不含密钥/密码 |

**残余**

- 跨实例异常聚合与到期去重依赖 Redis 可达；单实例降级为进程内语义（与 §11 风险口径一致）。
- 对账仅覆盖 Key 侧计数自洽，跨系统拒绝数比对依赖 K-03；对账尚未挂调度，按 D-06 编排项接入。
- 角色契约的锚点来自仓库内配置文件，组织级角色字典同步仍归 P3 治理批次（G 类）。

### 10.25 P3 治理残余闭合（G-01~G-03，v1.22.0，2026-10-31）

> 目的：按《残余项统一处置方案 v1.0.4》§4.1 推进 P3 批次，闭合 §10.14、§10.16 登记的 3 项治理残余（ER-25 及 ABAC 复核/规模两项）。全部新增配置**缺省即零行为变化**，新增配置进启动门禁，新增错误码沿用统一四键契约。

| 编号 | 事项 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|---|
| G-01 | ABAC 变更双人复核（裁定 B：事后审计） | 不新增审批表/端点，保留 `security:admin` 超管直改。审计 `detail` 固定写入 `review_mode="post_audit"`；update/delete 额外携带变更前快照 `previous`（policy_id/name/effect/permission/roles/tenant/cross_tenant/enabled/version），实现改前→改后可还原；变更提交后输出结构化 WARN `abac policy changed without dual review; post-audit required`（extra 仅 `policy_id`/`version`/`actor_id`/`action`），双人复核由组织流程消费审计记录完成 | `modules/auth/abac_policy_store.py`（`ABAC_CHANGE_REVIEW_MODE` / `_audit_detail` / `_append_audit` / `_warn_post_audit`） | `tests/test_p3_governance.py`（create/update/delete 三动作审计标记与快照、3 条 WARN 捕获） |
| G-02 | 三权分立强制接入角色授予（ER-25） | 新增统一准入 `ensure_role_grant_allowed(existing_role_codes, granted_role_codes, *, replace=False)`：按「结果角色集」调用既有 `conflicting_duty_pairs`，冲突抛 `BaseError(PERM_DUTY_CONFLICT)`（HTTP 409），文案列出互斥对；`replace=True` 取新授予集（可整改历史冲突），`replace=False` 取既有 ∪ 新增（OIDC 增量映射语义）。接入四条授予路径：用户创建、用户改派、agent 创建（替换语义）、OIDC 角色映射（增量语义） | `core/errors/codes.py`（`PERM_DUTY_CONFLICT` + 409 映射）、`modules/auth/access_control.py`（`ensure_role_grant_allowed`）、`modules/users/__init__.py`、`modules/identity/agents.py`、`modules/auth/oidc.py` | 同文件（冲突抛错与 409 映射、并集新增冲突、`replace=True` 整改历史冲突，3 例） |
| G-03 | ABAC 策略规模与命中性能基线 | `evaluate_abac` 新增可选 `soft_limit` / `warn_ms` 参数（缺省惰性读 `get_settings()`，读取异常回退模块常量 `1000` / `50`）；以 `time.perf_counter` 计时：生效规则数超阈值输出 WARN `abac rule set exceeds soft limit; consider index/cache`（extra `rule_count`/`soft_limit`），单次判定超阈值输出 WARN `abac evaluation slow; consider index/cache`（extra `elapsed_ms`/`rule_count`/`warn_ms`）；判定语义（deny-overrides / 跨租户默认拒绝 / 无命中回落 RBAC）完全不变，告警不阻断 | `settings.py`（`abac_rule_soft_limit` / `abac_evaluation_warn_ms` + `_validate_e3_governance_configuration` 非正拒启）、`modules/auth/access_control.py`（`DEFAULT_ABAC_RULE_SOFT_LIMIT` / `DEFAULT_ABAC_EVALUATION_WARN_MS` / `_abac_baseline_thresholds`） | 同文件（超规则数告警、慢判定告警、阈值内静默、非正阈值拒启，4 例） |

**新增配置（缺省零行为变化）**

| 项 | 默认 | 说明 |
|---|---|---|
| `OPENBASE_ABAC_RULE_SOFT_LIMIT` | `1000` | 生效规则数超阈值即 WARN（提示索引/缓存），不阻断判定；非正整数拒启 |
| `OPENBASE_ABAC_EVALUATION_WARN_MS` | `50` | 单次判定耗时超阈值即 WARN，不阻断判定；非正整数拒启 |

**验证与门禁结论**

| 项 | 结果 |
|---|---|
| 用例 | `python -m pytest tests/test_p3_governance.py` → **8 passed** |
| 回归 | `test_e3_governance` / `test_users_admin` / `test_settings` / `test_oidc_p1_residuals` / `test_identity_t5` / `test_p3_governance` / `test_p2_residuals` 合计 **127 passed**（275.72s） |
| 静态检查 | 本环境未安装 `ruff`（`No module named ruff`），**待具备环境补跑**；已如实登记 |
| 零行为变化 | 两项阈值默认 1000/50 仅在超限时告警；既定 HTTP 授予路径为单角色且 `ALLOWED_ROLES` 不含职责码，`ensure_role_grant_allowed` 恒不冲突；OIDC 白名单 `admin/org_admin/user/viewer` 不含职责码，增量映射不新增拒绝 |
| 安全 | 审计与 WARN 仅记录策略标识/版本/操作者 id/计数，不含策略全文、凭据或证书；`PERM_DUTY_CONFLICT` 文案不含主体现有角色明细之外的信息 |

**残余**

- G-01 为事后审计口径，**无审批前置**：强制「第二人签字」需另建审批流（本次经裁定不建），现阶段依赖组织流程定期复核 `review_mode=post_audit` 审计记录。
- G-02 只覆盖本仓授予路径；下游四仓的角色映射替换仍归 K-04。若未来新增多角色批量授予的 HTTP 端点，须按 `replace=False` 并集语义接入本准入。
- G-03 仅提供告警，不做索引/缓存优化；真实规模下的判定耗时压测归 P4 的 V 类实测（V-12 等）。

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
| v1.7.0 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.11「E1-5C 实施结果」：吊销增量同步在四仓落地（状态/版本判定、同步失败沿用旧快照、严格模式开关），控制面 `next_since` 回退 1ms 修复同毫秒漏读；登记惰性同步（无后台线程）与 E1 剩余项（MCP 边缘凭证、配额告警、R6/R7/R8） |
| v1.8.0 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.12「E1-6/E1-7 实施结果」，闭合 E1 剩余项：MCP 边缘凭证三形态 + stdio 令牌注入 + 工具级 `scope.tools` 过滤；Key 异常告警（多 IP / 网段跳变 / 调用量突增，只告警不阻断，落审计）；R6 四仓生产 fail-closed 门禁（受信来源与角色口径漏配即拒启）；R7 OpenMemory 轮换闭环（摘要落盘 + 宽限期 + 网关同源校验 + 生产三拒绝）；R8 OpenLLM Key 权限上限与按 Key 配额限流；登记残余（单进程窗口/内存配额、MCP 工具级仅作用 MCP 路由、OpenRAG 全量收集受限） |
| v1.9.0 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.13「E2 实施结果」：审计日志链式哈希（`prev_hash`/`entry_hash` + `before_flush` 单点挂钩覆盖 17 处插入点 + 超管链校验端点）；R16/R20 MCP 静态 Key 去明文（摘要列表 / 宿主注入文件 + 生产三条门禁）；R17 OpenLLM 身份权威开关（`IDENTITY_AUTHORITY=openbase` 关闭本地开户/登录/换发并要求 JWKS）；修正 2 条既有 settings 用例；登记残余（多实例链分叉、TPM/安全启动/本地落盘加密/远程擦除依赖终端宿主） |
| v1.10.0 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 闭合 §10.13 登记的审计链并发残余：flush 前先取 PostgreSQL 事务级 advisory lock（`pg_advisory_xact_lock`，锁键参数化绑定）再读末条哈希并插入，多实例写入串行不叉链；非 PG 方言放行；新增 3 项用例（SQLite 放行 / PG 参数化 SQL / 先锁后读顺序），审计链与审计/Key 相关回归 126 项通过；§10.4 E2 与 §10.13 残余同步标注 |
| v1.11.0 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.14「E3 实施结果」并重排 §10.5：政务暂缓项中**纯软件可完成**部分落地——E3-1 三权分立（三职责两两互斥 + 权限点基线不重叠）与 ABAC（deny-overrides / 跨租户默认拒绝 / 无命中回落 RBAC，试算与职责端点）；E3-2 审计 NDJSON 流式导出（条数上限 + 链式哈希可离线复核）与留存清理（默认 dry-run、`0` 未启用即拒绝、删头不断链）；E3-3 签名算法注册表（HS256/RS256 可用、SM2 预留不可用，配置即 fail-fast）；E3-4 统一 IdP Provider 多登记（启动门禁 + 只读视图不含 `client_secret`）；新增 4 配置项；残余（SM2 未接线、IdP 未切换多 Provider 流程、ABAC 无写端点、SoD 未强制接入授予路径、留存未接集中审计平台）与 SQLite 验证边界如实登记 |
| v1.12.0 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.15「A3 存量迁移闭环」：初始化链 `apply_identity_migration` 幂等补齐 `audit_logs.prev_hash` / `entry_hash` 两列（`inspect` 列存在性判定 + PG schema 限定 ALTER），消除 §10.13 登记的「生产升级需手工 DDL」残余（ER-27）；同步改写模型注释与 §10.13 统一口径；新增 2 项用例（SQLite 存量库补列/重放幂等/历史行 NULL、PG schema 限定 SQL），`test_identity_t1` + `test_db_init` + `test_audit_chain` 全部通过，ruff 0 错误；修正 `test_identity_t6` 静态扫描的过期禁用词（E3-2 人工留存清理与 `audit_retention_days` 配置属显式端点，不属自动限期清除）；A1 验收清单升 v1.0.1（A1-12 改为「启动即补列」口径） |
| v1.13.0 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.16「ABAC 策略写端点」并闭合 §10.14 登记的 ER-24：`abac_policy_rules` 表（名称唯一/启用开关/版本自增）+ `/api/v1/auth/access/policies` CRUD（`security:admin`，字段校验复用配置口径，409/404/400 三态）；`/check` 改为「DB 启用行 ∪ 配置基线」合并判定，deny-overrides 与跨租户默认拒绝语义不变、缺省零行为变化；写入与 `AuditLog` 同事务（`access.abac_policy.*`，审计失败即回滚）；新增 3 项用例，`test_e3_governance` 26 项与相关回归全通过，ruff 0 错误；登记残余（无审批流/无规则规模压测/SQLite 验证边界）；A2 清单升 v1.0.1（ABAC 增运行期策略说明） |
| v1.14.0 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.17「OIDC P1 安全硬化」：state 从进程内 dict 改为一次性存储（Redis 优先 + TTL + 锁，Redis 不可用回退内存）；授权码流补 nonce 校验与 PKCE S256（默认开启）；ID Token 验签算法由硬编码 RS256 改为配置白名单 ∩ IdP discovery 声明（未接线算法含 SM2 启动即拒绝）；OIDC 端点错误由 `HTTPException` 收敛为 `BaseError` 统一四键契约；新增 3 配置项与启动门禁；新增 12 项用例，OIDC 相关 30 项全部通过，ruff 0 错误；登记残余（多 Provider 路由未接、IdP 登出未联动、client_secret_basic/mTLS 未支持、真实 IdP 联调待 A1） |
| v1.15.0 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.18「多 Provider 登录路由」：`GET /auth/oidc/authorize` 支持 `provider` 参数，按 `OPENBASE_IDP_PROVIDERS` 声明构建/缓存 Provider 客户端；state 载荷记录 Provider 名，callback 依 state 还原客户端（profile/claim_role/default_tenant 取自 Provider）；未登记/未知 Provider 统一 400 `PARAM_INVALID`；不指定 provider 的单 IdP 路径零行为变化；新增 5 项用例，OIDC 三套用例全通过，ruff 0 错误 |
| v1.16.0 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.19「IdP 登出联动」：`POST /auth/oidc/logout` 本地 `token_version` 递增即时吊销存量令牌，按 Provider/单 IdP discovery 返回 `end_session` 登出 URL（IdP 未声明/不可达则为 null，不回滚本地吊销）；未鉴权 401、未知 Provider 400、未启用 404 均在吊销前判定；新增 4 项用例（未鉴权 / 未知 Provider / Provider 登出 URL / 本地版本递增与直签主体跳过），`test_oidc_multi_provider` 9 项全通过，ruff 0 错误 |
| v1.17.0 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.20「token 端点认证方式扩展」：`OPENBASE_OIDC_TOKEN_AUTH_METHOD` 支持 `client_secret_post`（默认）/ `client_secret_basic`（RFC 6749 §2.3.1，表单不重复携带凭据）/ `mtls`（RFC 8705，客户端证书 + 可选 CA）；新增 3 项 mTLS 证书路径配置与启动门禁（非法方式、缺路径、文件不存在均拒启）；新增 9 项用例（post/basic 载荷、mTLS 请求选项、post/basic 全链路、4 项门禁），OIDC 三套用例通过，ruff 0 错误 |
| v1.18.0 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.21「private_key_jwt 客户端断言」并闭合 §10.20 该项残余：`OPENBASE_OIDC_TOKEN_AUTH_METHOD` 追加 `private_key_jwt`（RFC 7523，`client_assertion_type` 固定 URN、RS256 断言 `iss`/`sub`=client_id、`aud`=token 端点、300s + `jti`）；新增 `OPENBASE_OIDC_CLIENT_PRIVATE_KEY_PATH` 与可选 `_ASSERTION_KID`，缺私钥路径/文件不存在拒启；新增 5 项用例（断言 claims/header、mock IdP 验签全链路、3 项门禁），OIDC 四套用例（含 settings/auth）52 项通过，ruff 0 错误；登记残余（断言算法仅 RS256、真实 IdP 未联调） |
| v1.19.0 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.22「tls_client_auth 客户端认证」并闭合 §10.20 该项残余：认证方式追加 `tls_client_auth`（RFC 8705 §2.1 PKI 证书），与 `mtls` 共用传输装配（承载 `client_id`、不发 `client_secret`）；新增 `OPENBASE_OIDC_CLIENT_CERT_SUBJECT` 启动期 subject DN 预检（分隔符空白/大小写不敏感，不匹配或非 PEM 拒启）；新增 5 项用例（载荷/传输选项、subject 匹配/不匹配、非 PEM 证书），OIDC 四套（含 settings/auth）57 项通过，ruff 0 错误；登记残余（SAN 型绑定本地预检未实现、真实双向 TLS 未联调） |
| v1.20.0 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.23「OIDC 残余闭合（P1 批次 C-01~C-05）」，闭合 §10.22/§10.21/§10.19 登记的 5 项残余：C-01 `tls_client_auth` SAN 型绑定本地预检（新增 `OPENBASE_OIDC_CLIENT_CERT_SAN_DNS/_URI/_IP/_EMAIL`）；C-02 `private_key_jwt` 断言算法扩至 `RS256`/`ES256`/`ES384` 并校验私钥类型/曲线（新增 `OPENBASE_OIDC_CLIENT_ASSERTION_ALGORITHM`）；C-03 回调保存 ID Token 并在登出透传 `id_token_hint`；C-04 新增 RFC 8471 `POST /api/v1/auth/oidc/backchannel-logout`（验签 + events/jti 一次性 + 404 语义）；C-05 Provider 级 PKCE/签名算法/认证方式覆盖与回落；新增 6 配置项全部缺省零行为变化并进启动门禁；`tests/test_oidc_p1_residuals.py` **39 passed**（本环境 ruff 未安装，待补跑）；同步升版《残余项统一处置方案 v1.0.2》与 A2 清单 v1.0.8 |
| v1.21.0 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.24「Key 生命周期残余闭合（P2 批次 C-06~C-10）」，闭合 §10.12 与 §7.3 登记的 5 项残余：C-06 静态 MCP Key 工具白名单（`OPENBASE_MCP_API_KEY_TOOLS`，缺省不限工具）；C-07 Key 异常检测改 Redis 跨实例聚合（`INCR`/`SADD`/`SCARD` + 共享冷却，Redis 不可用回退进程内，仍只告警不阻断）；C-08 新增只读到期清单端点与 `service_key.expiring` 事件（Key+日去重）；C-09 Key 侧审计对账（`签发 = 有效 + 吊销 + 过期`，差异写审计告警）；C-10 新增 `GET /api/v1/auth/roles/contract` 统一角色字典契约端点；新增 1 配置项缺省零行为变化并进启动门禁；`tests/test_p2_residuals.py` **20 passed**（回归 99 + 8，本环境 ruff 未安装待补跑）；同步升版《残余项统一处置方案 v1.0.3》与 A2 清单 v1.0.9 |
| v1.22.0 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | 新增 §10.25「P3 治理残余闭合（G-01~G-03）」，闭合 §10.14/§10.16 登记的 3 项治理残余：G-01 按人工裁定 B 落地「超管直改 + 事后审计」（审计 `review_mode=post_audit` + update/delete 改前快照 + WARN，不新增审批表/端点）；G-02 新增 `ensure_role_grant_allowed` 并接入用户创建/改派、agent 创建、OIDC 角色映射，冲突返回 409 `PERM_DUTY_CONFLICT`（闭合 ER-25）；G-03 新增 `OPENBASE_ABAC_RULE_SOFT_LIMIT`（1000）与 `OPENBASE_ABAC_EVALUATION_WARN_MS`（50），超规则数/超耗时输出结构化 WARN，判定语义不变；新增 2 配置项缺省零行为变化并进启动门禁；`tests/test_p3_governance.py` **8 passed**（回归 127 passed，本环境 ruff 未安装待补跑）；同步升版《残余项统一处置方案 v1.0.4》与 A2 清单 v1.1.0 |

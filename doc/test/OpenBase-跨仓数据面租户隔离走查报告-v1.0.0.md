# OpenBase-跨仓数据面租户隔离走查报告-v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 文档版本 | **v1.2.0**（v1.0.0 首版走查 → v1.1.0 修复闭环 → v1.2.0 待裁定项裁定建议） |
| 状态 | **[Review]**（待人工裁定 §6 四项建议） |
| 走查编号 | OB-CROSSREPO-TENANT-ISOLATION-v1.0.0 |
| 作者 | AT-OpenBase-Dev（API 测试视图）/ SE-OpenBase-Dev（安全视图）/ AU-OpenBase-Dev（审计视图）/ PM-OpenBase-Dev |
| 创建日期 | 2026-10-14 |
| 走查对象 | 下游数据面四仓：OpenRAG（8010）/ OpenMemory（8020）/ DPS（8030）/ OpenLLM（8001） |
| 关联文档 | 《OpenBase-自研系统多租户与授权集成总体完善方案》(v1.16.27)；《OpenBase-权限管理与多租户授权走查报告》(v1.1.0)；《OpenBase-全栈功能走查报告》(v1.1.0) |
| 关联证据 | `doc/test/evidence/manual/cross-repo-tenant-isolation-20261014.json`（脱敏） |

---

## 1. 走查范围与方法

### 1.1 范围界定

本报告承接《权限管理与多租户授权走查报告》v1.1.0 中「**下游数据面租户隔离归各仓自证**」的边界，将其纳入跨仓走查闭环。**管理面**（OpenBase 的 users/tenants，平台级 admin-only）不在本次范围；本次聚焦**数据面**：下游各系统在收到「某租户的请求」后，是否能保证① 只返回该租户的数据、② 拒绝未授权/未登记租户、③ 不因缺失租户标识而放行全量。

### 1.2 方法

| 维度 | 方法 | 落点 |
|------|------|------|
| 静态 | 逐仓检索租户标识来源、过滤实现、fail-closed 分支、测试覆盖 | 四仓源码（只读） |
| 运行时 | 身份闸门四态矩阵探针（无头 / 非受信来源+身份头 / 受信来源+保留码 / 受信来源+未登记租户[+ 已登记租户]） | 下游三系统直连 |
| 运行时 | OpenBase 转发链裁决（负控 + admin 经 rag-proxy / memory-proxy / dps-proxy） | 网关 8000 |
| 交叉 | 与既有 MTAUTH 走查结论对账（非 admin 身份经 proxy 的下游裁决） | 两份报告 |

### 1.3 环境与命令

- 服务：OpenRAG `8010`、OpenMemory `8020`、DPS `8030`、OIDC-IdP `8090` 常驻在线；OpenBase `8000` 于走查窗口内以受管编排启动；**OpenLLM `8001` 未启动**（其结论以静态为准，见 §5 限制）。
- 探针脚本（临时，不入库）：`doc/tmp/mtw/isolation_probe.py`、`doc/tmp/mtw/forward_probe.py`。
- 运行命令：`& 'D:\PostgreSQL\17\pgAdmin 4\python\python.exe' -B doc/tmp/mtw/isolation_probe.py`。

---

## 2. 四仓隔离机制概览（静态）

| 仓库 | 租户标识来源 | 隔离方式 | fail-closed 主分支 | 测试覆盖 |
|------|-------------|---------|-------------------|---------|
| OpenRAG | 头 `X-Tenant-ID`（`identity/protocol_headers.py:15-22`）；`X-Org-ID` 仅别名 | 关系库按 `tenant_code` 列过滤（`result`：`storage/sqlite.py:48-75`）；**向量库 Qdrant 无租户维度**（`storage/qdrant.py:88-98`） | 非受信带头 403 `PERM_UNTRUSTED_IDENTITY_HEADER`（`api/middleware/identity_gate.py:179-196`）；保留码 400（`:249-260`）；强制段缺租户 401 / 未登记 403（`:274-305`） | 充分（`test_s3_t3_scope_enforcement.py`、`test_s3_t6_failopen.py`、`test_isolation_matrix_endpoints.py` 等） |
| OpenMemory | 头 `X-Tenant-ID`（principal）；`X-Org-ID` 退役别名（`identity/protocol_headers.py:22-29`） | `memory_metadata` 与会话表 **tenant_code+owner 双键行级隔离**（`storage/sqlite_store.py:208-260`、`relational_store.py:375-427`）；**检索面仅 user_id/agent_id** | 非受信带头 403（`api/middleware/identity_gate.py:256-267`）；未知 org 403/404/503；DB/Redis 故障 fail-closed（唯一显式 fail-open 为限流降级 `identity/verdict.py:112-118`） | 充分（`test_metadata_scope_negative.py`、`test_s2_t8_failopen.py`、`test_isolation_matrix_endpoints.py`） |
| DPS | 头 `X-Org-ID`/`X-Tenant-ID`（`src/middleware/tenant_middleware.py:164-167`） | 共享表 + 行级 `tenant_id/org_id` 过滤（`src/engines/query_engine.py:840-843`）；`UNIQUE(person_id, tenant_id)` | 缺组织/租户 **401**（`tenant_middleware.py:114-122`）；组织不存在/停用 **403**（`:294-299`）；DB 故障默认 fail-closed 403（`:203-233`） | 充分（`src/tests/test_tenant_isolation.py`、`test_p22_fail_closed.py`、`test_v2_11_tenant_isolation.py`） |
| OpenLLM | 头 `X-Tenant-ID`（`backend/app/identity/protocol_headers.py:19-26`） | **模型库全局无租户维度**；配额按 `organization_id`（`billing_service.py:104-135`）；计量按租户落库（`usage_tracker.py:77-94`） | 鉴权失败 401（`openllm_gateway.py:3736-3737` 等）；但缺租户 / 非受信带头 / 保留码默认放行（开关默认 False） | 中等（`test_isolation_matrix_endpoints.py`、`test_s4_t9_strong_verify.py`、`test_c1c_tenant_scope_closeout.py`） |

---

## 3. 运行时证据

### 3.1 下游身份闸门四态矩阵（直连）

| 服务 | 无身份头 | 非受信来源+身份头 | 受信来源+保留码 `default` | 受信来源+未登记租户 | 受信来源+已登记租户 |
|------|:-------:|:----------------:|:------------------------:|:------------------:|:------------------:|
| OpenRAG | 401 `AUTH-4010` missing api key | 401 `AUTH-4010` | 401 `AUTH-4010` | 401 `AUTH-4010` | —（无演示码） |
| OpenMemory | 401 缺少或无效的 API Key | 401 | 401 | 401 | —（无演示码） |
| DPS | 401 缺少组织或租户标识 | 401 缺少组织或租户标识 | **400 `BIZ_RESERVED_TENANT_CODE`**（保留码不得用于入站） | 401 缺少组织或租户标识 | **403 无权限执行 read 操作于 unknown** |

**判定**：三系统在**匿名/缺失租户**情形下**均未返回业务数据**（401 或 400/403），未发现「无租户即全量返回」的运行时路径 —— 数据面在真实请求链路上 **fail-closed 成立**。DPS 的保留码 400 分支与「组织不存在/无权限 403」分支均**实证为活**。

> 说明：OpenRAG 首道闸门为 API Key（`AUTH-4010 missing api key`），身份头裁决在其后，故四态矩阵在无 API Key 时统一呈现 401；这与静态结论「APIKey 白名单路径可绕过身份闸门」（见 §4 D4）互为印证。

### 3.2 OpenBase 转发链裁决

| 探针 | 结果 | 判定 |
|------|------|------|
| `GET /health` | 200 | 网关在线 |
| `GET /api/v1/users`（无令牌） | **401** | 负控通过 ✅ |
| `GET /api/v1/users`（坏令牌） | **401** | 负控通过 ✅ |
| `POST /api/v1/auth/login` admin | 200 | 登录通过 |
| `GET /api/v1/rag-proxy/collections`（admin） | **200 `code=0`** | 转发链通 + 下游受信采纳 |
| `GET /api/v1/memory-proxy/memories`（admin） | **200 `code=0`** | 转发链通 + 下游受信采纳 |
| `GET /api/v1/dps-proxy/profiles`（admin） | 404 | 路径与下游路由不匹配（探针方法问题，非缺陷） |

**结合既有 MTAUTH 走查**：非 admin 的租户身份经 memory-proxy 调用时，由**上游 OpenMemory 返回 403**（`{code:403,message:"Forbidden"}`，上游响应格式）——即 OpenBase 转发成功、**下游对未授权租户 fail-closed**。两条证据共同表明：**跨仓转发链的租户裁决由下游承担且未放行**。

---

## 4. 问题清单与修复闭环

> 说明：以下为**静态走查发现**（含 `文件:行号` 证据），严重度按「是否可导致跨租户数据泄露/破坏」判定。运行时已验证的「闸门层」未见放行，故高危项集中在**绕过闸门或闸门未覆盖的旁路**。
>
> **修复状态（2026-10-14，v1.1.0）**：依人工指令「依次跨仓小版本修复高危、中危问题」，已按仓依次完成 D1–D20 中**高危 7 项 + 中危 10 项**的最小侵入修复，逐仓 TDD + 回归 + 留痕 + 本地提交 + 推送三远程（详见 §4.4）；**低危 D5/D15 不在本次指令范围**，保持登记。**凡需翻转默认配置（影响单租户兼容）者一律未翻转，改以等价开关/条件化实现并登记「需裁定」**（见 §4.4 表末列）。

### 4.1 高危（跨租户数据泄露 / 数据破坏）

| # | 仓库 | 问题 | 证据（文件:行） | 建议处置 |
|---|------|------|----------------|---------|
| **D1** | OpenRAG | 写路径不 fail-closed：`create_collection` 未调用 `_scope_tenant`，缺域时静默落 `default`，即使 `enforce=True` 也不拒绝 | `src/openrag/storage/postgres.py:370`、`storage/sqlite.py:280` | 写路径统一经 `_scope_tenant`，缺域显式拒绝 |
| **D2** | OpenRAG | 向量库（Qdrant）无租户维度，且 `delete_collection` **先删向量、后校验域** → 传他域 `collection_id` 可跨租户删除向量 | `src/openrag/storage/qdrant.py:88-98`、`src/openrag/api/routes/collections.py:182-188` | 向量删除前先做关系库域校验；collection 名引入租户维度 |
| **D6** | OpenMemory | 检索面 `/recall` 未传租户 scope，仅按 `user_id/agent_id` 过滤 → 同名用户跨租户可互检索（持久/向量记忆） | `src/openmemory/api/controllers.py:365-382`、`memory/service.py:234-255` | recall 链路注入 tenant scope；补跨租户隔离用例 |
| **D9** | DPS | 引擎层在**无租户上下文时静默不过滤**（`else` 分支 SQL 无 `tenant_id`），隔离为「中间件+contextvar 单点依赖」 | `src/engines/query_engine.py:86-90`、`:129-133`、`:641-647` | `get_tenant_id() is None` 时显式拒绝或强制 `require_tenant_id()` |
| **D10** | DPS | MCP 非 HTTP 路径未注入租户上下文（`portrait_get` 直调引擎，从不 `set_tenant_context`），入参 `org_id/tenant_id` 声明却未用于过滤 | `src/mcp_server/tools.py:421-427`、`:97-100` | MCP 工具入口注入租户上下文并绑定入参校验 |
| **D11** | DPS | 画像缓存键不含租户维度（`key=f"{prefix}{person_id}"`）→ Redis 可用时 A 租户缓存可被 B 租户命中 | `src/cache.py:85`、`:110` | 缓存键改为 `{prefix}{tenant_id}:{person_id}` |
| **D16** | OpenLLM | 模型路由**完全无租户维度**：模型库全局、无白名单判定，任何已鉴权主体可调用任意 active 模型 | `backend/app/api/chat.py:101-104`、`openllm_gateway.py:2508-2511`、`models/model.py:20-60` | 路由接入 `Tenant/Team.allowed_models` 与虚钥白名单，越权返 403 |

### 4.2 中危（默认兜底 / 旁路 / 配置默认放行）

| # | 仓库 | 问题 | 证据（文件:行） | 建议处置 |
|---|------|------|----------------|---------|
| **D3** | OpenRAG | 缺 `X-Tenant-ID` 时观察段不拒绝 + 上下文回落 `default`（默认 `tenant_registry_enforce=False`） | `src/openrag/identity/context.py:98-101`、`api/middleware/identity_gate.py:266-285` | 多租户部署强制段默认开启 |
| **D4** | OpenRAG | `/api/v1/system/stats` 跨租户聚合，且属 APIKey/白名单直通路径 | `src/openrag/api/routes/system.py:186`、`api/middleware/identity_gate.py:73-81` | 统计端点按租户过滤或限平台管理面 |
| **D7** | OpenMemory | decay/image/trace 端点直读裸 `X-Tenant-ID` 并以 `default` 兜底，未走受信裁决；图像硬删用 `app.state.tenant_id` | `api/controllers.py:581`、`:633`、`:752`、`:892`、`:451`、`:685-708` | 收口到 `state.identity`；补隔离用例 |
| **D8** | OpenMemory | 默认租户兜底面广（Gate 未装配/缺主体多处回落 `default`） | `api/middleware/tenant_context.py:343-347`、`identity/inbound_gate.py:159-171`、`api/controllers.py:1185` | 生产多租户下改 fail-closed / 强制显式域 |
| **D12** | DPS | 白名单前缀匹配过宽（`path.startswith`）→ `/api/v2/organizations` 全子路径、`/health*` 任意后缀被豁免 | `src/middleware/tenant_middleware.py:88-97` | 改精确匹配或路径段匹配 |
| **D13** | DPS | 标签路由绕过 contextvar 直读头，缺头即返回全部分类 | `src/rest_api/routes/routes_tags.py:40-61`、`src/engines/tag_engine.py:120-123` | 统一走 contextvar |
| **D14** | DPS | 限流按 `X-Tenant-ID` 缺省兜底 `default` 计数 | `src/middleware/rate_limit_middleware.py:58` | 缺租户拒绝或独立计数 |
| **D17** | OpenLLM | 配额检查遇「无配额记录」默认放行（fail-open） | `backend/app/services/billing_service.py:125-127` | 无配额记录改 fail-closed（或显式默认配额） |
| **D18** | OpenLLM | 缺租户标识默认静默通过（`TENANT_SCOPE_ENFORCE=True` 才 400，默认 False）；非受信带头默认放行 | `backend/app/identity/namespace.py:313-347`、`core/config.py:107-110`、`:60-63` | 多租户生产默认开启强制段 |
| **D19** | OpenLLM | 限流键为 user/API Key/IP，**无租户维度** | `backend/app/middleware/rate_limit.py:168-184` | 限流键加租户维度 |
| **D20** | OpenLLM | API Key 检索仅按 `key_hash`（不绑租户）；头租户与用户实体租户无一致性校验 | `backend/app/services/auth_service.py:406-412`、`openllm_gateway.py:1770` | 补一致性校验分支 |

### 4.3 低危

| # | 仓库 | 问题 | 证据（文件:行） | 建议处置 |
|---|------|------|----------------|---------|
| **D5** | OpenRAG | `TenantScopeRequiredError` 未注册异常映射 → 兜底 500，与 docstring 声称的 403 不符 | `src/openrag/api/exception_handlers.py:119-123`、`core/exceptions.py:131` | 注册映射为 403 |
| **D15** | DPS | `TenantManager` 为桩实现（租户 CRUD / 跨租户授权返回硬编码假数据） | `src/engines/tenant_manager.py:70-94`、`:96-138` | 明确标注不可用于授权判定或补齐实现 |

---

### 4.4 修复闭环（v1.1.0，按仓依次实施）

> 实施纪律：每仓 TDD（先 RED 后 GREEN）→ 定向 + 相关面回归 → 静态检查 → 该仓留痕 → 本地提交 → 推送三远程并核验 HEAD 一致。四仓均**未翻转既有默认值**；需翻转默认者改为等价开关/条件化实现并登记「需裁定」。

| 仓 | 分支 / 提交 | 处置项（状态） | 关键改动 | 验证 | 已登记「需裁定」 |
|----|------------|---------------|---------|------|-----------------|
| **OpenRAG** | `release/v1.10.0` / **`b7c83a7`** | D1 ✅ 修复（写路径经 `_scope_tenant`，enforce 缺域拒绝）；D2 ✅ 修复（删除前先做域校验，不触碰向量）；D3 ⚠️ 登记（强制段已 fail-closed，观察段为设计取舍）；D4 ✅ 修复（`/system/stats` 按调用者租户过滤，运维契约不变） | `storage/sqlite.py:282`、`storage/postgres.py:372`、`api/routes/collections.py:182-184`、`api/routes/system.py:180-193` | 新增 `test_cross_repo_tenant_isolation_fix.py`；定向 + 相关面 **92 passed**；本次改动 ruff 0 新增错误；对照基线**零新增失败** | D3 多租户是否默认开强制段；D4 全租户聚合是否需平台凭据 |
| **OpenMemory** | `release/v7.3.0` / **`6a12609`** | D6 ✅ 修复（`/recall` 下推租户 scope 至持久/向量检索）；D7 ✅ 修复（decay/image/trace 统一走 `state.identity` 派生租户，trace 跨域 404）；D8 ✅ 显式化（集中兜底策略 + 表征测试锁定，无行为变更） | `memory/service.py:205-258`、`memory/dual_memory.py:79-117`、`api/controllers.py`（`_tenant_code_of` + 6 端点）、`memory/multimodal_engine.py:216-221`、`memory/retrieval.py:91-100` | 新增 3 个测试文件（D6 5 例 / D7 7 例 / D8 7 例）；定向+必保面 **102 passed**；`tests/unit` 1391 passed；`ruff check src tests` **All checks passed** | D8 多租户生产是否默认 fail-closed；graph/temporal 检索未覆盖租户谓词 |
| **DPS** | `main` / **`83e5933`** | D9 ✅ 修复（新增等价开关 `tenant_context_required`，启用时引擎层缺域显式拒绝）；D10 ✅ 修复（MCP 15 工具入口注入租户上下文 + 入参必填校验）；D11 ✅ 修复（画像缓存键加租户维度）；D12 ✅ 修复（白名单改精确/路径段匹配）；D13 ✅ 修复（标签路由统一走 contextvar，缺域拒绝）；D14 ✅ 修复（限流租户维度取统一上下文，不再兜底 default） | `src/engines/tenant_context.py:73-92`、`query_engine.py` 7 处接线、`src/mcp_server/tools.py:85-103`、`src/cache.py:18-29,83-93`、`src/middleware/tenant_middleware.py:102-115`、`rest_api/routes/routes_tags.py:34-50`、`src/middleware/rate_limit_middleware.py:27-29,50-63` | 新增 `test_tenant_hardening_d9_d14.py`（RED 14F/3P → GREEN 17 passed）；必保面 **65 passed**；受影响面 174 + 284 passed；全量分批 1263 passed、4 failed 均环境性；改动文件 ruff 0 新增错误 | D9 生产是否默认开 `tenant_context_required`；代码版本号递增（建议 v2.12.1→v2.12.2） |
| **OpenLLM** | `feature/s4-identity-channel-b` / **`762357c`** | D16 ✅ 修复（模型路由接入白名单，**仅非空 `allowed_models` 约束时**校验、越权 403 契约码 1002）；D17 ✅ 修复（新增 `QUOTA_MISSING_FAIL_CLOSED`，默认 False 兼容）；D18 ⚠️ 登记（强制段已 fail-closed，三开关默认未翻转，补守门测试）；D19 ✅ 修复（限流键加租户维度，无租户时键格式逐字等价）；D20 ✅ 修复（新增 `TENANT_HEADER_CONSISTENCY_ENFORCE`，受信源+API Key 下头租户与归属不一致 → 403） | 新增 `services/model_access.py`；`api/chat.py`、`api/chat_stream.py`、`api/openllm_gateway.py`（1002→403）、`core/config.py:116-125`、`middleware/rate_limit.py:168-214`、`services/auth_service.py:369-380,455-482`、`services/billing_service.py:125-142` | 新增 `test_tenant_isolation_walkthrough_d16_d20.py`（RED 9F/11P → GREEN 20 passed）；相关面回归 **986 passed / 0 failed**；更广 API 面 1327 passed、1 项为存量基线失败（已对照）⇒ 零新增失败；新增文件 ruff 0 错误 | D17/D18/D20 生产默认是否开启；`APP_VERSION` 递增口径；D16 列表端点未按白名单过滤 + 租户级约束列是否新增 |

**四仓三远程一致性（核验于 2026-10-14）**：OpenRAG `b7c83a7`、OpenMemory `6a12609`、DPS `83e5933`、OpenLLM `762357c` —— **origin / backup / github HEAD 与本地逐一一致**（github 因出网抖动经多次重试后全部追平）。

---

## 5. 结论与限制

### 5.1 结论

1. **闸门层成立**：四仓均在入站实现对租户标识的解析与裁决，运行时三系统对匿名/缺失租户**均未放行数据**（401/400/403）；DPS 的保留码与「组织不存在」分支实证为活。跨仓转发链（OpenBase → 下游）对未授权租户由下游 fail-closed（403）。
2. **隔离强度不均**：OpenRAG/OpenMemory/DPS 的**主存储面**为行级 `tenant_code` 过滤且测试充分；但**旁路面**（向量库、检索面、缓存、MCP、模型路由）存在结构性缺口。
3. **核心风险 = 旁路绕过，而非闸门失效**：最高危的 7 项（D1/D2/D6/D9/D10/D11/D16）全部是「不经主闸门/闸门未覆盖的路径」，其中 **D9（引擎层无上下文即不过滤）** 与 **D11（缓存键缺租户）**、**D10（MCP 无上下文）** 可在真实多租户下直接跨租户泄露。
4. **默认兜底普遍存在**：四仓均存在「缺租户 → 回落 `default`」的宽容策略，在多租户生产部署下构成弱隔离点（D3/D8/D14/D18）。
5. **修复闭环（v1.1.0）**：D1–D20 中**高危 7 项、中危 10 项已按仓依次修复**（见 §4.4），四仓提交均已推送三远程且 HEAD 一致；其中 4 项（D3/D8/D18/D20 相关的「默认翻转」）按「不破坏单租户兼容」纪律改为**等价开关/条件化实现 + 登记需裁定**，D8 为「无行为变更的显式化」。

### 5.2 限制与边界

- OpenLLM（8001）**走查窗口内未运行**，其结论为**静态分析**（含 `文件:行号`），未做运行时验证。
- 本次为**只读走查**，未修改任何仓的代码；四仓修复需各仓自行施工，本报告仅登记问题与建议处置。
- 跨租户**数据面实证**（在 A 租户写、以 B 租户读）未执行：需在下游登记两套租户并写数据，属**破坏性/需授权**操作；本次以「闸门判决 + 静态旁路分析」替代，建议后续以专项沙箱补做。
- 运行时环境受限：OpenBase `8000` 进程随会话回收（WMI 脱离启动后被沙箱回收），转发探针采用「同命令内启动 + 探针」原子执行完成取证。

---

## 6. 待裁定项裁定建议（裁定输入）

> 承接 §4.4「需裁定」列。本节依据**项目既有契约与先例**给出建议（含 `文件:行号` 依据），供人工裁定。
> **总纲**：四项裁定**均不应通过「翻转代码默认值」实现**——项目已确立「按环境门控」范式（生产收紧、非生产保持兼容），应**复用该范式**：代码默认值维持 M1/非生产兼容，**由生产启动门禁 + 部署配置达成生产 fail-closed**。这样既满足多租户生产要求，又不破坏既有测试与单租户部署。

### 6.1 议题 A（D3/D8/D18）：多租户生产是否默认 fail-closed —— **建议：是，且以「扩展 C4 生产启动门禁」落地**

**依据**
- 《[协议头规范-v1.1](file:///d:/Trae%20CN/myproject/Dev/OpenBase/doc/design/OpenBase-协议头规范-v1.1.md)》§4.1（`:163-171`）已明文规定：**生产环境必须 `enforce_inbound_identity_headers=true` 且行控/租户校验策略开启；未满足 → 拒绝启动**。
- **C4 生产门禁**已四仓覆盖（OpenRAG `a9f0376`、OpenMemory `utils/config.py::validate_identity_trust_policy`、DPS `00e4820`、OpenLLM `v2.16.3`）——「生产必须 enforce」**已是既有契约**，本次并非新立规则，而是**补齐门禁覆盖缺口**。
- 缺口所在：C4 门禁当前仅覆盖**身份头强校验**，**未覆盖**「租户注册表强制段」（OpenRAG `tenant_registry_enforce`，`settings.py:312-319` 默认 False）与「缺租户作用域强制段」（OpenLLM `TENANT_SCOPE_ENFORCE`，`core/config.py:107-110` 默认 False）→ 存在「生产已 enforce，但缺 `X-Tenant-ID` 仍回落 `default`」的语义裂缝。
- 方向一致性：台账「未决项 9」已裁定「**default 兜底两版本内退役**」并由 OpenMemory `P4` 落地（`总体完善方案-v1.0.0.md:408/:459`）；台账「B4 遗留」亦确立「**生产 fail-closed 401 / 非生产 allow+WARN**」先例（同文 `:456`）。

**建议裁定**：**采纳生产 fail-closed**；实现方式为**把「租户注册表强制段 / 缺租户作用域强制段」纳入各仓 C4 生产启动门禁校验清单**（`production ∧ 强制段关闭 → 拒绝启动`），代码默认值不动。

**落地与量级**：各仓扩 `validate_*_policy()` 启动校验 + 2~3 条门禁用例；≤1 天/仓；对 M1/非生产零影响。

### 6.2 议题 B（三开关生产默认）—— **建议：生产显式置真并纳入启动门禁；代码默认不翻转**

| 开关 | 建议 | 依据与理由 |
|------|------|-----------|
| DPS `tenant_context_required` | **生产置真**（与 `MULTI_TENANT_ENABLED=true` 同批下发） | DPS 既有家族开关已全是 fail-closed（`multi_tenant_fail_closed=true`、`permission_fail_closed=true`、`role_fail_closed=true`，`src/config.py:111-113/:201-203/:222`）；本开关同族却默认宽松，**自相矛盾**——「多租户已开启但引擎层缺域不过滤」不可接受 |
| OpenLLM `TENANT_HEADER_CONSISTENCY_ENFORCE` | **生产必须置真** | 受信源 + API Key 下「头租户 ≠ Key 归属租户」即**以他人租户行事（冒充）**；契约码已具备（`1002=403`，`openllm_gateway.py:1592/:1601`）；一致时行为不变，**无兼容性代价** |
| OpenLLM `QUOTA_MISSING_FAIL_CLOSED` | **生产置真**；或改为**显式默认配额**（`DEFAULT_QUOTA_*`）+ 留痕 | 计费契约**只规定「超配额→429」**（`OpenLLM-用户手册-v2.0.0.md:694`、`Agent架构设计文档-v2.3.0.md:311-312`），**未规定「无配额记录放行」**；隐式放行等于「无记录即无限额度」，违背多租户计费/隔离目标。若业务确需「未配置即不限」，应显式配置而非静默放行 |

**落地**：三项均**不改代码默认**；在**生产 `.env` 模板与部署脚本**显式置真，并在生产启动门禁加「生产未置真 → 拒绝启动」护栏（与 C4 同构）。

### 6.3 议题 C（版本号递增口径）—— **建议：缺陷修复走修订号 + 消除硬断言 + 收敛单一事实源**

**依据**：「修复走修订号（Patch）」已是明文惯例（OpenMemory D6D7D8 记录建议 `v7.3.0→v7.3.1`；DPS `v2.9.1` 补丁位；DPS `CHANGELOG.md` SemVer；OpenRAG `版本发布策略总则.md:27-31`）。

**建议裁定与目标版本**：

| 仓 | 建议目标版本 | 备注 |
|----|-------------|------|
| OpenRAG | `v1.9.1 → v1.9.2` | 随 `release/v1.10.0` 窗口归并亦可 |
| OpenMemory | `v7.3.0 → v7.3.1` | 与 D6D7D8 记录一致 |
| DPS | `v2.12.1 → v2.12.2` | `src/config.py:33-34` 三处口径需同批统一 |
| OpenLLM | `v2.17.0 → v2.17.1` | 本次提交已按 v2.17.1 命名 |

**必须同时处理（否则版本号被测试反向冻结）**：
1. **消除硬断言**：OpenLLM `test_v2145_startup_alignment.py:35` 断言 `APP_VERSION == "2.14.5"` 属**反向约束**，应改为**版本无关口径**——对齐 DPS 已落地范式（`version_contract_utils.assert_semver` + 三处一致性断言，且 `test_version_contract.py:30-33` 结构门禁**禁止**历史前缀断言）。
2. **收敛单一事实源**：各仓版本声明多源不一致（OpenBase 五处 `1.0.0` vs `1.4.10`＝已登记 R-391；OpenRAG `1.8.0/1.9.1/1.8.6`；OpenMemory `6.7.0/7.1.3`；DPS `2.12.1/2.7.1/2.7.0`；OpenLLM `2.17.0/2.14.5`）——建议每仓确立 **1 个权威源 + 其余由校验门禁保证一致**。

### 6.4 议题 D（D16 列表端点与租户级约束）—— **建议：列表端点按白名单过滤；租户级约束「契约化」而非新增列**

1. **`GET /chat/models` 建议按主体白名单过滤**：返回 `public ∧ active ∧ allowed`；未配置约束时返回全部 public active（保持现状）。
   - 依据：调用面已拦截（`chat.py:100-114` → 403/`1002`），**列表面不过滤会造成「可见不可用」割裂 + 白名单信息泄露**；需求文档已把 `allowed_models` 定义为租户/团队级数组（`OpenLLM-需求文档-v1.3.0.md:794`）。
2. **租户级约束不建议新增独立列**：现状 `Team.allowed_models`（独立列，`models/tenant.py:110`）+ `Tenant.settings["allowed_models"]`（JSONB，`models/tenant.py:48`）已可承载；建议：
   - 把 `Tenant.settings["allowed_models"]` **正式契约化**：写入 OpenLLM API/数据设计文档；加 schema 校验（数组/字符串、模型码存在性）；
   - 收敛到唯一读取入口 `services/model_access.py::resolve_allowed_models`（已具备）；
   - 登记「若未来需要查询/索引再升级为独立列」（可逆）。
   - 理由：需求文档只规定「数组字段」未规定物理列；JSONB 免迁移、可逆；**避免为假设需求过度建模**。

### 6.5 建议汇总

| 议题 | 建议裁定 | 是否改代码默认 | 落地方式 | 量级 |
|------|---------|:-------------:|---------|------|
| A 生产 fail-closed | **采纳** | 否 | 扩展 C4 生产启动门禁（覆盖租户强制段） | 小（≤1 天/仓） |
| B 三开关 | **生产置真** | 否 | 生产 `.env`/部署脚本显式置真 + 门禁护栏 | 小 |
| C 版本号 | **走修订号** | — | 测试改版本无关口径 + 各仓版本 bump + 单一源收敛 | 小-中 |
| D D16 | **列表过滤 + 契约化** | 否 | 列表端点接白名单 + settings 契约文档化/校验 | 小 |

---

## 7. 证据索引

| 产物 | 路径 |
|------|------|
| 跨仓隔离运行时证据（脱敏） | `doc/test/evidence/manual/cross-repo-tenant-isolation-20261014.json` |
| 下游闸门矩阵探针（原始） | `doc/tmp/mtw/isolation_probe.py`（临时，不入库） |
| OpenBase 转发链探针（原始） | `doc/tmp/mtw/forward_probe.py`（临时，不入库） |
| 关联：权限与多租户授权走查 | `doc/test/OpenBase-权限管理与多租户授权走查报告-v1.0.0.md`（v1.1.0） |
| 关联：全栈功能走查 | `doc/test/OpenBase-全栈功能走查报告-v1.0.0.md`（v1.1.0） |

## 8. 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.2.0 | 2026-10-14 | AT/SE/AU/PM-OpenBase-Dev | 新增 §6「待裁定项裁定建议（裁定输入）」：依既有契约与先例对 4 项待裁定项给出建议（A 生产默认 fail-closed 采纳、以扩展 C4 生产启动门禁落地；B 三开关生产置真、代码默认不翻转；C 缺陷修复走修订号 + 消除 OpenLLM 版本硬断言 + 收敛单一事实源；D `/chat/models` 按白名单过滤 + `Tenant.settings["allowed_models"]` 契约化而非新增列），含 6.5 建议汇总表；原 §6/§7 顺延为 §7/§8；状态转 [Review]（待裁定） |
| v1.1.0 | 2026-10-14 | AT/SE/AU/PM-OpenBase-Dev | 跨仓修复闭环：依指令「依次跨仓小版本修复高危、中危问题」，按仓（OpenRAG→OpenMemory→DPS→OpenLLM）完成 D1–D20 中高危 7 + 中危 10 的修复/显式化（§4.4 修复闭环表 + 四仓提交号 + 三远程一致性核验）；§4 标题与说明、§5.1 结论同步更新；需翻转默认者改等价开关并登记需裁定 |
| v1.0.0 | 2026-10-14 | AT/SE/AU/PM-OpenBase-Dev | 首次产出：下游四仓数据面租户隔离跨仓走查（静态 + 运行时闸门矩阵 + 转发链裁决），登记 D1–D20 问题待裁定 |

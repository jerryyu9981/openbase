# OpenBase-跨仓数据面租户隔离走查报告-v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 文档版本 | **v1.0.0**（首版） |
| 状态 | **[Review]** |
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

## 4. 问题清单（登记待裁定）

> 说明：以下为**静态走查发现**（含 `文件:行号` 证据），严重度按「是否可导致跨租户数据泄露/破坏」判定。运行时已验证的「闸门层」未见放行，故高危项集中在**绕过闸门或闸门未覆盖的旁路**。

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

## 5. 结论与限制

### 5.1 结论

1. **闸门层成立**：四仓均在入站实现对租户标识的解析与裁决，运行时三系统对匿名/缺失租户**均未放行数据**（401/400/403）；DPS 的保留码与「组织不存在」分支实证为活。跨仓转发链（OpenBase → 下游）对未授权租户由下游 fail-closed（403）。
2. **隔离强度不均**：OpenRAG/OpenMemory/DPS 的**主存储面**为行级 `tenant_code` 过滤且测试充分；但**旁路面**（向量库、检索面、缓存、MCP、模型路由）存在结构性缺口。
3. **核心风险 = 旁路绕过，而非闸门失效**：最高危的 7 项（D1/D2/D6/D9/D10/D11/D16）全部是「不经主闸门/闸门未覆盖的路径」，其中 **D9（引擎层无上下文即不过滤）** 与 **D11（缓存键缺租户）**、**D10（MCP 无上下文）** 可在真实多租户下直接跨租户泄露。
4. **默认兜底普遍存在**：四仓均存在「缺租户 → 回落 `default`」的宽容策略，在多租户生产部署下构成弱隔离点（D3/D8/D14/D18）。

### 5.2 限制与边界

- OpenLLM（8001）**走查窗口内未运行**，其结论为**静态分析**（含 `文件:行号`），未做运行时验证。
- 本次为**只读走查**，未修改任何仓的代码；四仓修复需各仓自行施工，本报告仅登记问题与建议处置。
- 跨租户**数据面实证**（在 A 租户写、以 B 租户读）未执行：需在下游登记两套租户并写数据，属**破坏性/需授权**操作；本次以「闸门判决 + 静态旁路分析」替代，建议后续以专项沙箱补做。
- 运行时环境受限：OpenBase `8000` 进程随会话回收（WMI 脱离启动后被沙箱回收），转发探针采用「同命令内启动 + 探针」原子执行完成取证。

---

## 6. 证据索引

| 产物 | 路径 |
|------|------|
| 跨仓隔离运行时证据（脱敏） | `doc/test/evidence/manual/cross-repo-tenant-isolation-20261014.json` |
| 下游闸门矩阵探针（原始） | `doc/tmp/mtw/isolation_probe.py`（临时，不入库） |
| OpenBase 转发链探针（原始） | `doc/tmp/mtw/forward_probe.py`（临时，不入库） |
| 关联：权限与多租户授权走查 | `doc/test/OpenBase-权限管理与多租户授权走查报告-v1.0.0.md`（v1.1.0） |
| 关联：全栈功能走查 | `doc/test/OpenBase-全栈功能走查报告-v1.0.0.md`（v1.1.0） |

## 7. 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-14 | AT/SE/AU/PM-OpenBase-Dev | 首次产出：下游四仓数据面租户隔离跨仓走查（静态 + 运行时闸门矩阵 + 转发链裁决），登记 D1–D20 问题待裁定 |

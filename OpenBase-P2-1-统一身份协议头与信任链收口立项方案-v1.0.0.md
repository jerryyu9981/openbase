# OpenBase-P2-1-统一身份协议头与信任链收口立项方案-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-P21-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Draft] |
| 日期 | 2026-09-07 |
| 作者 | AD（跨项目分析） |
| 版本主题 | P2-1 立项：四头/委托头唯一签发规范与信任链收口（K01/K03/K02 规范 v1.0/K07 模板）、OB-6 服务账号受信通道与 agent 审计贯穿（L3-1 前置）、OB-12 角色互译表起步、OB-8 code 化收口、OB-13 审计贯穿（OpenBase 侧）、OB-9 verify-env 雏形并入 |
| 适用范围 | OpenBase 主仓（proxy 族出站/入口中间件、身份头规范、服务账号受信通道、审计、verify-env 雏形、端点矩阵模板）；对外契约面（协议头规范 v1.0 与端点矩阵模板供 S2/S3/S4/S5 各子系统段落地；DPS 角色互译配合）；文档面（S2-S7 各段填报矩阵、S7 终验引用） |
| 上游依据 | 《多系统联调联试分阶段版本规划（子系统纵切）》v1.3.0（S1b 范围与门禁、§5 任务分布、Q-4 B 主 A 备口径）；《数据隔离实现任务卡》v1.2.0（K01/K02/K03/K07、K08 移交、SYS-1、RA 组、升级项 OB-3/6/7/8/9/10/12/13、L3-1）；《统一身份最小特征集与隔离模型设计》v1.3.0（§4.4 审计、§6.3 角色互译、§10.2 Q2、§11.3 委托、§12.1 R-H1-1/2/3/4、§12.5 R-M2-1、§12.7 R-M4、§12.9 R-L1-1）；《OpenBase-U1-统一身份收口设计草案》v1.1.0 与《U1 立项方案》v1.1.0（U1 实施记录：T4 遗留「委托头全局唯一签发规范移交 S1b」、verify_principal 对 DB 不可达/行缺失 fail-open 及委托场景裁定待 S1b 信任链矩阵）；《多系统对接联调问题复盘与根治方案》v1.1.0（§5 S1 配置源/S2 契约轨、根因 4.1/4.2/4.3）；《OpenBase-U1-统一身份收口立项方案》v1.0.0 与《OpenBase-P2-2-隔离与fail-open收口立项方案》v1.0.0（立项方案格式参考：元信息表/修订历史/章节结构） |

> 立项依据：分阶段规划 v1.3.0 S1b「OpenBase 协议与服务段（P2-1+服务账号域，原则②③规范落点）」——流程为起草 P2-1 立项（四头/委托头唯一签发、信任链、禁旁路、端点矩阵模板）→ 批准 → 实施；卡序 K01 → K03 → K02 规范 v1.0 发布（供 S2-S5 落地）+ K07 模板发布；升级项 OB-6（L3-1 前置）、OB-8/OB-12/OB-13、OB-7 配合（S7 终验）、OB-9 verify-env 雏形、OB-10 前端壳牵头（S6 落地）；段门禁 = 非白名单带头 403（OpenBase 侧）+ 协议头规范 v1.0 发布 + 服务账号发放/吊销用例全绿 + 端点矩阵模板评审通过。本方案将该段转为可执行立项，原则沿用最小集 v1.3.0 定案（tenant_code 唯一隔离键、入口同构性 R-H1 规则、Q2 Agent 服务账号强约束、Q-4 B 主 A 备、org 头退役为兼容别名）与任务卡 K01/K02/K03/K07 定义。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-07 | AD（跨项目分析） | 初始版本：背景与目标（承接核心原则②③与 S1b 的差距实证）、现状盘点（代码证据 + 行号落点清单）、范围与定案（K01/K03/K02/K07/OB-6/OB-12/OB-8/OB-13/OB-7/OB-9/OB-10）、任务分解（T1~T10，含 P2-1↔U1/P2-2 边界防重复）、验收标准、非目标与边界、影响面与兼容、风险与依赖、里程碑与五步流程衔接 |

---

## 1. 背景与目标

本立项承接**核心原则②「直连+经 OpenLLM 主备双通道（默认 B 主 A 备，Q-4）」与核心原则③「前端与智能体统一经 OpenBase」**（规划 v1.3.0 §1.1），并落实最小集 §12.1「入口同构性与身份头信任链（H1）」与任务卡 K01/K02/K03/K07 定义。目标：让 X-User-ID/X-Tenant-ID/X-User-Role/X-Proxy-Source（下称**四头**，X-Org-ID 退役为兼容别名）与委托头在 OpenBase 侧**唯一签发、全链透传、白名单校验、可审计、端点全覆盖**，消灭各 proxy 出站头不一致与服务调用身份面未归一导致的隔离旁路与审计断链。

### 1.1 差距实证表（现状 → 目标，代码证据见 §2）

| # | 差距（实证） | 后果 | 对应卡/升级项 |
|---|-------------|------|--------------|
| G-P1 | **各 proxy 出站头不一致**：dps-proxy 注入四头（缺 X-Proxy-Source）；memory-proxy 注入三头（X-Org-ID/X-User-ID/X-Tenant-ID，缺 X-User-Role/X-Proxy-Source）；llm-proxy 注入 X-User-ID/X-Org-ID/X-Proxy-Source（缺 X-Tenant-ID/X-User-Role）；rag-proxy 零身份头（仅 X-API-Key） | 同一条入口对四个子系统呈现四种身份语义，下游无法统一按信任链解析；OpenRAG 侧无身份可隔离（隔离缺口与 R-H3 关联） | K01 / OB-3 |
| G-P2 | **无统一信任链**：OpenBase 仓无 `TRUSTED_PROXY_SOURCES` 配置键与共享校验函数/常量包；X-Proxy-Source 仅 llm-proxy 注入且来源标识为模块内常量 `openbase-llm-proxy`（写死） | 来源标识不归一 → 各功能系统白名单各自维护、取值漂移（复盘根因 4.1：TRUSTED_PROXY_SOURCES 两写法）；伪造头无法被统一剥离 | K01/K02 / OB-3、SYS-1 |
| G-P3 | **服务调用身份面未归一**：通用 `/api/v1/proxy/{system}` 通道（ob_k_ 服务 Key 回退认证）纯转发、不注入身份头；sk-agent-* 主体在 llm/memory proxy 的二次 JWT 解码路径上不被识别（见 §2.3）；`REAL_*`/服务兜底不作为业务身份（R-L1-1 部分就绪但通道未收口） | 服务/agent 直连写子系统不可审计、不可按主体域隔离（复盘根因 4.3 重演面） | K03 / OB-6（L3-1 前置） |
| G-P4 | **审计身份字段未贯穿**：audit_logs 具备 user_id/tenant_id/request_id 与 team_id/agent_id extra 位，但无统一 principal+delegated 两层字段与 X-Proxy-Source 来源字段贯穿各 proxy 出站；子系统侧审计不落同一 request_id/身份字段 | 委托/服务账号动作无法在 OpenBase 侧留痕回溯（最小集 §4.4 审计必带项未闭环） | OB-13（OpenBase 侧，U4 联动） |
| G-P5 | **角色互译缺映射**：无 admin/editor/viewer（OpenBase 语义档）↔ 各子系统既有角色的配置化互译表（最小集 §6.3） | 跨系统授权语义漂移（同一操作在 DPS 被当 create、在 OpenBase 是读），联调 P1-1 画像 403 类问题复发 | OB-12（起步 OpenBase↔DPS，Q-D 待评审） |
| G-P6 | **org 头未退役**：X-Org-ID 仍在 dps/memory/llm 出站注入并承担租户/组织取值（org_id 兼容别名），未收敛为 `org==tenant_code` 别名语义；dps org/tenant code→UUID 映射无生产化基线 | 双键并存易双向混淆（复盘根因 4.3）；新数据写入可能落 org 语义旧轨 | OB-8（P1-2/P1-3 code 化收口） |
| G-P7 | **verify-env 雏形缺位**：仓内无 `scripts/verify-env.ps1`，config 契约清单（键/种子值/端口/URL/白名单矩阵/映射对账）未建 | 部署即真相无自检约束（复盘根因 4.1，配置漂移类故障 40%） | OB-9（雏形并入本立项；完整版 R3/S7） |

### 1.2 目标态（本立项完成后达成）

1. **唯一签发**：四头/委托头仅由 OpenBase（签发上下文）或受信编排层（白名单内）注入；出站头取值仅来自签发上下文（JWT claim/subject 快照），客户端伪造头一律剥离（R-H1-1）。
2. **全链透传**：X-Proxy-Source 全 proxy 族出站透传并进入审计；来源标识常量/校验函数以共享包形式单一发布，全仓/全编排仅一种取值（K01 验收）。
3. **信任链矩阵化**：verify_principal 对 DB 不可达/行缺失/委托场景的 fail-open 裁定落表并实现（K03）；非白名单来源携带身份头 → 403（OpenBase 侧试点 + 规范发布）（R-H1-2/R-H2-3 补强）。
4. **服务账号通道收口**：sk-agent-* 主体经任一 proxy 出站均携带主体域身份头与 X-Proxy-Source，业务面无匿名直连写（OB-6，L3-1 前置）。
5. **规范与模板发布**：协议头规范 v1.0（文档 + 共享校验函数/常量包）与端点-过滤矩阵模板 v1.0（含填报流程）在 S1b 发布，供 S2-S5 落地、S7 终验（K02/K07）。
6. **角色互译与 code 收口**：OpenBase↔DPS 粗粒度角色互译配置化并映射测试绿；X-Org-ID 退役为别名收敛、dps org/tenant code→UUID 映射生产化基线（OB-12/OB-8）。
7. **审计贯穿（OpenBase 侧）**：request_id + 两层身份（principal/delegated）+ 来源字段透传落库（OB-13）。
8. **verify-env 雏形可用**：编排 start 时对配置单源/白名单矩阵/映射/code 对账自检 fail-fast（OB-9 雏形）。

---

## 2. 现状盘点（代码证据，2026-09-07 核对）

> 本节约为 P2-1 设计前置盘点，登记为**行号落点清单**。路径为仓相对路径（仓库根：`D:\Trae CN\myproject\Dev\OpenBase`），行号以盘点时 `HEAD=2f9b5fd` 代码为准（U1 T1~T7 已合入，identity 模块存在）。

### 2.1 proxy 族出站身份头注入现状

| proxy | 文件:行号（注入函数） | 入站认证 | 出站注入（现状） | 缺失头 / 备注 |
|-------|----------------------|---------|-----------------|--------------|
| 通用 proxy | `openbase/modules/proxy/__init__.py:67-120`（`proxy` 路由，认证依赖 L72 `get_proxy_identity`） | JWT 优先 + 服务 Key 回退（双通道） | **纯转发**：仅透传 Content-Type/Accept（L84-87）；不注入任何身份头 | 全缺。ob_k_ 服务 Key 通道亦不带身份（服务身份面缺口，G-P3） |
| dps-proxy | `openbase/modules/dps_proxy/__init__.py:90-135`（`_build_identity_headers`） | JWT（`get_current_user`） | **四头齐全**：X-User-ID←user.id、X-Tenant-ID/X-Org-ID←tenant_raw/org_raw 链（tenant_code→tenant_id→org_id→dps_default→映射表，L118-129）、X-User-Role←role；委托分支 L101-115 取委托域值 | **无 X-Proxy-Source**；每次单独 `_jwt_payload`（L60-71）二次解码 Authorization 头（sk-agent 解码为 None → 回落默认链） |
| llm-proxy | `openbase/modules/llm_proxy/__init__.py:96-120`（`_build_upstream_headers`）+ `_extract_identity`（L62-93，委托覆盖 L85-93） | JWT（`get_current_user`） | Authorization Bearer llm_api_key（L108-112）；X-User-ID=L116、**X-Proxy-Source=L117（唯一注入来源标识者，常量 `PROXY_SOURCE_IDENTIFIER="openbase-llm-proxy"` L41）**、X-Org-ID=L118-119；匿名/服务调用不带身份头（L114-115） | **无 X-Tenant-ID/X-User-Role**；org 头未退役；来源标识为模块内写死常量（G-P2） |
| rag-proxy | `openbase/modules/rag_proxy/__init__.py:82-96`（`_build_upstream_headers`） | JWT（`get_current_user`） | 仅 X-API-Key（rag_api_key，可空不注入 L94-95） | **零身份头**（无 X-User-ID/X-Tenant-ID/X-Org-ID/X-User-Role/X-Proxy-Source）——OpenRAG 侧无身份可隔离（G-P1 最重） |
| memory-proxy | `openbase/modules/proxy/memory_proxy.py:87-108`（`_build_upstream_headers`）+ `_extract_identity`（L50-84，委托分支 L68-77） | JWT（`get_current_user`） | X-API-Key（L103）+ Authorization Bearer **原 JWT 透传**（L104，OpenMemory 双层认证）+ X-Org-ID（缺省 `openbase-default` L105）+ X-User-ID（L106）+ X-Tenant-ID（缺省 `default` L107） | **无 X-User-Role/X-Proxy-Source**；org/tenant 有硬编码缺省兜底；透传原 JWT 属信任链特殊通道（下游需白名单对齐） |

**共同结构问题**：dps/llm/memory 各自从 `Authorization` 头**二次解码 JWT**（dps L60-71、llm L62-93、memory L50-84）取 extra 字段，而非直接消费 `get_current_user`（`core/deps/auth.py:156-233`）已返回的主体 dict——三处解码逻辑重复、取值链各写一份；`sk-agent-*` 凭据（`agent_keys.py:116-165` 可解析出主体含 tenant_code/subject_type/roles）在这三条二次解码路径上不被识别（llm/memory 直接 401/空身份，dps 回落默认映射链）。这即 K01「proxy 层删除各自为政的头组装，改读统一上下文」的直接改造面。

### 2.2 入口/依赖层身份头读取现状（OpenBase 侧入站）

| 落点 | 文件:行号 | 现状行为 |
|------|-----------|---------|
| `AuthMiddleware.dispatch` | `core/deps/auth.py:75-108` | PUBLIC_PREFIXES（L57-73，含 `/api/v1/proxy`）；sk-agent-* 令牌放行至依赖层（L91-94）；每请求经 `_verify_request_principal`（L110-128，仅数字 sub 开 DB 会话）跑共享主体验证器 |
| `get_current_user` | `core/deps/auth.py:156-233` | sk-agent → `resolve_agent_principal`（L177-180）；JWT → `verify_principal`（L194）；返回主体 dict（含 tenant_code/subject_type/role/on_behalf_of/delegated，L214-233） |
| `get_current_tenant` | `core/deps/auth.py:236-255` | **优先取入站 `X-Tenant-Id` 头（L244-246），其次 JWT**——入站头高于 JWT，客户端可自带头覆盖，属信任链收口对象（K02 OpenBase 侧试点） |
| `get_identity_context` | `core/deps/auth.py:277-313` | 读入站 X-User-Id/X-Tenant-Id/X-Team-Id/X-Agent-Id（L282-285），JWT 回退；供审计 extra（team/agent 位）——入站身份头当前仅用于上下文/审计，未做来源白名单校验 |
| `get_proxy_identity` / `require_api_key` | `core/deps/auth.py:370-387` / `318-367` | X-API-Key 头或 Bearer `ob_k_*` → `require_api_key`（L385-386）；scope 校验按路径 system（L352-357）；其余 JWT。**无身份头注入、无来源标识绑定** |

### 2.3 服务 Key 信任面（ob_k_ 与 sk-agent-*）

| 凭据面 | 落点 | 信任面现状 |
|--------|------|-----------|
| `ob_k_*`（既有服务 Key） | `openbase/modules/auth/api_keys.py`：KEY_PREFIX L19；ApiKeyStore 内存存储（L30-31）、create L35-63、verify L76-105（scope=system/tenants）、revoke L65-72、list L107-115、sha256 `_hash` L117-120 | **非 DB 持久化、无主体语义（不挂 sub/域/角色/状态）**。信任面 = `/api/v1/proxy/{system}` 双通道（proxy/__init__.py:72）与 MCP 层；`/proxy` 通道纯转发不带身份头（§2.1）。**本立项不改造其鉴权语义（兼容存量），服务账号形态由 sk-agent-* 承担（OB-6）** |
| `sk-agent-*`（agent 主体密钥，U1 T1 已落地） | `openbase/modules/identity/agent_keys.py`：AGENT_KEY_PREFIX L25；issue L48-76、revoke L79-91、list L94-101；`resolve_agent_principal` L116-165（按 key_hash 查库、状态/过期/active 门禁、挂角色） | **DB 持久化、主体化（subject_type=agent）、状态门禁齐备**。信任面缺口：① 中间件放行（auth.py:91-94）+ `get_current_user` 识别，但 **llm/memory proxy 二次 JWT 解码不识别 sk-agent**（G-P3）；② agent 出站身份头/来源标识/审计贯穿未收口（OB-6 本立项范围） |

### 2.4 委托出站头现状（U1 T4 遗留）

- U1 已完成（`identity/delegation.py`）：on_behalf_of claim 结构（L47-51）、`delegated_claim_from_payload`（L188-200）、域不变式校验器 `verify_delegation`（L213-336）、每请求重校验 `verify_request_delegation`（L339-375）、委托签发链 `issue_delegated_token_pair`（L431-496，无 HTTP 端点挂载，供受信通道调用）。
- dps/memory/llm 三个 proxy 已消费委托域值做出站头（dps L101-115、memory L68-77、llm L85-93）。
- **R2 边界（delegation.py L22-23 明示）**：委托头（X-Proxy-Source 等）的**全局唯一签发规范 / 信任链矩阵**移交 P2-1（S1b）——本立项承接（K01 委托头唯一签发 + 信任链矩阵）。

### 2.5 verify_principal fail-open 现状与 redis 降级

- `identity/verification.py` `verify_principal`（L167-249）：
  - sub 非数字（OIDC 直签/外域）→ 放行（L193-195）；
  - **DB 读不可达 → WARN + 放行（fail-open 过渡窗口，L197-208，与 login 内存降级一致）**；
  - **主体行缺失：purge 墓碑命中 → 401（L215-220）；无墓碑 → 放行（L221-225，OIDC 直签/降级内存用户过渡语义）**；
  - 状态门禁默认生效（L227-228）、版本强校验受 `enforce_token_version` 开关（默认关，L233-243）、委托逐跳重校验（L245-248）。
- 该两处 fail-open（DB 不可达/行缺失）与委托场景 DB 故障下的裁定，**待 S1b 信任链矩阵定案**（K03，见 §3.2 裁定结论建议表）。
- `core/cache/redis_client.py`：get_client 懒初始化 + 不可用返回 None（L32-61）；cache_get/cache_set/cache_delete 失败静默降级（L64-119）；publish 双形态（本地处理器 + Redis 广播，L149-186）。信任链校验若依赖 Redis 状态缓存，须按「缓存不可用 = 直读 DB/拒」设计，避免两级降级叠加不可审计。

### 2.6 盘点结论 → 立项改造面映射

| 立项差距 | 实证锚点（§2.1/2.2/2.3/2.4/2.5） | 对应章节 |
|---------|----------------------------------|---------|
| G-P1 proxy 头不一致 | dps L90-135 / llm L96-120 / rag L82-96 / memory L87-108 | §3.1（K01） |
| G-P2 无统一信任链 | 仅 llm L41 有来源常量；无共享校验/常量包 | §3.1/§3.3（K01/K02） |
| G-P3 服务身份面未归一 | /proxy 纯转发（L84-93）；sk-agent 不被 llm/memory 识别（二次解码） | §3.2/§3.5（K03/OB-6） |
| G-P4 审计未贯穿 | audit_logs 字段面（U1 草案 §1.1）与 proxy 出站无来源/两层身份 | §3.8（OB-13） |
| G-P5 角色互译缺映射 | 无配置化互译表；复盘 P1-1 画像 403 | §3.6（OB-12） |
| G-P6 org 头未退役 | dps L118-129 org 链 / memory L98-99 org 兜底 / llm L118-119 | §3.7（OB-8） |
| G-P7 verify-env 缺位 | 仓内无 verify-env 脚本/契约清单 | §3.9（OB-9） |

---

## 3. 范围与定案

### 3.1 K01 四头/委托头唯一签发规范（任务卡 K01 / 升级项 OB-3，R-H1-1）

**定案：统一由 OpenBase 签发注入 + 全 proxy 族出站对齐；X-Proxy-Source 全链透传。**

- **唯一注入点**：X-User-ID/X-Tenant-ID/X-User-Role/X-Proxy-Source 仅由 OpenBase（网关/proxy 签发上下文）或受信编排层（TRUSTED_PROXY_SOURCES 白名单内）注入（R-H1-1）。客户端/前端直连 OpenBase 携带身份头一律不作为事实源：**入站身份头剥离或审计标注**（对齐 §2.2 入站读取现状收口）。
- **取值统一**：出站头改读 `get_current_user` 返回的**统一主体上下文**（含 tenant_code/subject_type/role/on_behalf_of），删除 dps/llm/memory 三处各自为政的 JWT 二次解码（dps L60-71、llm L62-93、memory L50-84）；抽共享头组装函数（新模块 `openbase/core/identity_headers.py` 或并入 `identity/`），全 proxy 族复用。
- **委托头唯一签发**：承接 U1 T4 遗留（delegation.py L22-23）：委托 claim（on_behalf_of）的序列化与出站委托头（X-委托语义头 + X-Proxy-Source）**只由 OpenBase 经 `issue_delegated_token_pair`/受信编排签发**；出站取值恒为委托域（已在三个 proxy 落地，本项固化规范与用例）。
- **来源标识单一写法**：`X-Proxy-Source` 取值统一为受管配置/常量包（现状仅 llm L41 `openbase-llm-proxy`），发布「来源标识常量包」供本仓与各功能系统白名单引用；`TRUSTED_PROXY_SOURCES` 全仓仅一种取值（K01 验收断言：静态扫描 1 个事实源）。

### 3.2 K03 禁旁路 + verify_principal fail-open 裁定（任务卡 K03 / 升级项 OB-3，R-H1-4）

**定案：业务面禁止匿名直连子系统写路径；受信来源白名单化；verify_principal 委托与 DB 故障场景 fail-open 裁定给出结论建议（评审确认）。**

- **旁路盘点**：扫描 OpenBase 仓全部业务写路径与 `/proxy` 通用通道调用点，产出「绕过 OpenBase 直连子系统/匿名服务写」清单（K03 步骤①）；对旁路写路径加白名单与审计，或改走受信通道（服务账号/sk-agent + proxy 出站头）。
- **服务 Key 通道收口**：ob_k_ 服务 Key 鉴权语义保留（兼容存量），但其 `/proxy` 出站行为与主体身份绑定关系显式化（服务调用 = 服务账号语义，见 OB-6）；业务数据写不允许匿名 ob_k_ 直穿不落身份。
- **verify_principal fail-open 裁定结论建议表**（评审确认后编码）：

| # | 场景 | 现状（代码证据） | 风险 | 裁定建议 |
|---|------|------------------|------|---------|
| V-1 | 本地数字主体 JWT + DB 读不可达 | 放行（verification.py L197-208） | suspend/deactivate 吊销即时性在 DB 故障窗口失效 | **维持 fail-open 过渡（与 U1 login 内存降级一致）**：放行但 audit WARN 计数 + 出站头可带降级标注位（若规范含）；DB 恢复即恢复强校验。不改为 fail-closed（DB 抖动全站不可用，且数据面域过滤由 JWT 自带 claims 承担，不依赖 DB） |
| V-2 | 本地数字主体行缺失（无 purge 墓碑） | 放行（L221-225） | 已 purge/deactivated 未留墓碑时存量 token 复活窗口 | **维持 fail-open 过渡 + 收紧**：与 V-1 同语义放行，但**禁止此类请求携带 on_behalf_of**；S7 前 verify-env 复核审计；purge 墓碑路径已 401（L215-220）不回退 |
| V-3 | 委托请求（on_behalf_of）+ DB 不可达 | 目标存在/域校验不可证（delegation.py L289-319 依赖 session） | 委托属高权越权面（R-M4），无法证明目标即放行 = 越权面打开 | **fail-closed（403 PERM_FORBIDDEN/临时不可用语义）**：无法证明委托不变式即拒绝——与 P2-2 D1/D2 同构（授权面异常不静默放行） |
| V-4 | 状态/版本缓存（Redis）不可达 | 直读 DB（缓存命中失败视未命中，verification.py L61-71） | 无（已兜底直读） | 维持：缓存仅是加速，非信任源；信任判定一律以 DB 为准（S1b 信任链矩阵钉死） |
| V-5 | 非白名单来源携带身份头（下游子系统侧） | R-H1-2；各系统中间件待 K02 | 伪造头越权 | **403 本体由 K02 规范发布，本立项 OpenBase 侧试点 + 规范输出**；S2-S5 按规范落地 |

### 3.3 K02 协议头规范 v1.0（任务卡 K02（规范部分）/ SYS-1，R-H1-2，供 S2/S3/S5 落地）

**定案：本立项产出并发布协议头规范 v1.0（供 S2-S5 落地执行，不在本立项改各子系统）。**

- 规范内容：四头/委托头/X-Proxy-Source 的**头语义、取值规则、校验规则、白名单行为矩阵**（白名单+头=信任 / 白名单无头=自身认证 / 非白名单带头=403 / 非白名单无头=自身 API Key 认证，M1 语义）、错误码与 403 响应形态、双通道（A 直连/B 经 OpenLLM）下的头不变式（Q-4 B 主 A 备口径：同一动作同一时刻仅一条主路径，头语义不因通道而异）。
- **发布物形态 = 文档 + 共享校验函数/常量包**：
  1. 规范文档（S2/S3/S4/S5 各仓 K02 落地的唯一依据）；
  2. 共享校验函数/常量包（本仓发布：头常量、来源标识常量、`validate_identity_headers`/`assert_trusted_source` 参考实现 + 单元测试），各子系统仓移植或经编排注入；
  3. 双通道等价用例前置（通道 A/B 对同一对象返回一致、跨域 403/404，K09/§12.1 验收要点引用）。
- OpenBase 侧试点：`get_current_tenant`（auth.py L244-246）入站 X-Tenant-Id 优先级收口、`get_identity_context`（L282-285）入站头来源校验（非受信来源带头 → 剥除或 403/仅审计）——**非白名单带头 403（OpenBase 侧）为 S1b 门禁项**。

### 3.4 K07 端点-过滤矩阵模板 v1.0（任务卡 K07 / SYS-1，R-M2-1）

**定案：本立项发布模板与填报流程；各子系统段填报、S7 终验。**

- 模板：按端点类别（CRUD/列表分页/搜索/统计聚合/导出/回调异步读/批量，R-M2-1）× 过滤覆盖（域过滤/属主过滤/白名单来源）三态矩阵 + 缺口标注 + 隔离测试注册位；每系统导出 openapi 端点清单自动核对（K07 步骤①）。
- 填报流程：**S1b 发布模板 → S2（OpenMemory）/S3（OpenRAG）/S4（OpenLLM）/S5（DPS）各段随 K02 落地填报 → S7 RA-06 终验**（矩阵缺口清零，新增端点无隔离用例不放行）。
- 产出：`端点-过滤矩阵模板 v1.0`（文档 + 模板表 + 核对脚本骨架）。

### 3.5 OB-6 服务账号收口（Q2-S6 / L3-1 前置）

**定案：agent 密钥面（sk-agent-* 发放/轮换/吊销/状态）已在 U1 T1 落地，本立项收口「受信来源通道 + agent 审计贯穿」，作为 L3-1（Agent 端到端，S7）前置。**

- 受信来源通道：sk-agent-* 主体经任一 proxy（llm/rag/memory/dps）出站时携带**主体域身份头 + X-Proxy-Source**（消除 §2.3 二次解码不识别的缺口，统一改读 `get_current_user` 主体 dict）。
- 禁匿名直连：服务/agent 对 DPS/OpenMemory/OpenRAG/OpenLLM 的业务写必须走 OpenBase 受信通道（proxy/服务账号），不带匿名通道（K03 + Q2-S4）。
- agent 审计贯穿：出站审计带 agent_id + source + 域 + 动作（Q2-S5/S6）；停用即全部 sk-agent-* key 失效联动（U1 已实现，本立项回归断言）。
- L3-1 端到端在 S7 全链核验（agent key→四头→各系统白名单→域隔离；未授权 403）——本立项只做前置通道，不做端到端（边界见 §6）。

### 3.6 OB-12 角色互译表（最小集 §6.3，Q-D 待评审）

**定案：以「语义档（管理/读写/只读）」为锚的配置化互译表 + 映射测试；起步范围 OpenBase↔DPS；含待评审 Q-D。**

- 互译原则：只映射粗粒度语义，细粒度权限不入互译（§6.3-3）；无映射的角色/请求 fail-closed（告警 + 拒绝或降级提示，不静默）。
- 起步映射建议（评审确认，Q-D）：OpenBase `admin`（管理档）↔ DPS `super_admin`；OpenBase `org_admin`（读写/域管理档）↔ DPS `org_admin`；OpenBase `viewer`/`org_member`（只读档）↔ DPS `user`。OpenBase 语义档 `editor` 与现仓角色 code 集的对应（admin/org_admin/org_member/viewer 为现役 code）在设计阶段对账定稿。
- 落地：映射配置表（配置化，含版本与校验）+ 映射测试（各档语义用例绿）+ 无映射角色用例（fail-closed 断言）。
- **Q-D 记录**：初始映射范围是否仅 OpenBase↔DPS 两档语义起步（其余系统接入时扩展）——本方案建议「是」（最小起步），标注待评审。

### 3.7 OB-8 code 化收口（P1-2/P1-3）

**定案：X-Org-ID 退役为别名收敛；dps org/tenant code→UUID 映射生产化基线。**

- X-Org-ID 别名收敛：出站 X-Org-ID 只允许 = tenant_code（或显式别名表映射）的兼容别名，不再承担独立取值链（dps L124-129 org_raw 链收敛）；下游读取按 tenant_code 语义归一（最小集 §4.2 兼容 org_id）。
- dps org/tenant code→UUID 映射生产化：盘点并固化为生产化基线（与 `dps_org_map`/`dps_tenant_map`（settings L181-185）对账），以 OpenBase `tenants.code` 为唯一事实源；冲突检测（R-L3-1 形态）登记对接入清单。
- 注：DPS 侧库级迁移（K18/U2）不在本立项；本立项收 OpenBase 侧出站与映射基线的「code 化」表述。

### 3.8 OB-13 审计贯穿（§4.4，U4 联动）

**定案：request_id + 两层身份透传落库（OpenBase 侧字段贯穿）；与 U4 联动边界在文档标注。**

- OpenBase 侧：audit_logs 记录 `request_id` + 主体两层（principal/delegated）+ X-Proxy-Source 来源 + 域（detail 扩展，对齐 U1 草案 §7.3 委托两层审计与 §1.1 audit_logs 既有字段）。
- proxy 出站审计贯穿：各 proxy 转发动作落审计（或经请求中间件统一落）含 request_id/身份/来源，保证「子系统侧审计 + OpenBase 侧审计」可经 request_id 串联。
- **U4 联动边界**：U4（全链路审计/审计工作台）定义子系统侧字段落地与工作台；本立项只收 OpenBase 侧字段贯穿与 request_id 生成/透传钩子，子系统侧落库随 S2-S5/U4（见 §6 B-4）。

### 3.9 OB-7 / OB-9 / OB-10 标注

| 升级项 | 规划定位 | 本立项处置 |
|--------|---------|-----------|
| OB-9 verify-env 自检 | 复盘 S1 配置源；规划 §5「S1b 雏形 / S7 收官」 | **并入本立项（雏形任务 T9）**：config 契约清单（键/种子值/端口/URL/白名单矩阵/映射对账）首个版本 + `scripts/verify-env.ps1` 雏形（编排 start 比对 fail-fast）；完整版（多仓对齐 + openbase_test 库等）外移 R3/S7 |
| OB-7 存储账号分离 | 任务卡 K13；R2/U2；S7 终验 | **外移，不纳入本立项执行**：仅登记配合（本立项 verify-env 雏形含「连接账号/schema」检查位，K13 本身在 R2/U2 + S7） |
| OB-10 前端壳 | UI-E2E P3；S6/R4 | **外移**：前端导航壳属 S6 前端段/FE-JT 工作，本立项不实施（仅登记牵头行） |

---

## 4. 任务分解（T1~T10）

依赖顺序总览：`T1(K01) → T2(K03) → T3(K02 规范发布+OpenBase 试点) → T4(K07 模板)`；T5(OB-6)/T6(OB-12)/T7(OB-8)/T9(OB-9) 在 T1 定案后并行；T8(OB-13) 依赖 T1 出站头与 T5 来源标识；T10（回归与段门禁）贯穿收口。卡序对齐规划 S1b（K01 → K03 → K02 规范 + K07 模板）。

| 任务 | 对应卡/升级项 | 系统 | 内容 | 依赖 |
|------|--------------|------|------|------|
| **T1** 四头/委托头唯一签发与出站对齐 | K01 / OB-3 | OpenBase | 统一主体上下文取值（删三处 JWT 二次解码，改读 `get_current_user` dict）；共享头组装函数 + 来源标识常量包；dps 补 X-Proxy-Source、memory 补 X-User-Role/X-Proxy-Source、llm 补 X-Tenant-ID/X-User-Role、rag 补全部身份头；委托头唯一签发规范固化（U1 T4 遗留移交）；入站身份头剥离（非受信来源） | U1 claims 就绪（tenant_code/sub_type/tvn/role，已交付）；T1 无 P2-1 内前置 |
| **T2** 禁旁路 + fail-open 裁定落地 | K03 / OB-3 | OpenBase | 业务写路径/`/proxy` 直连调用点盘点；旁路清单收口（白名单 + 审计或改受信通道）；verify_principal fail-open 裁定（§3.2 V-1~V-5）评审确认后编码（V-3 委托 DB 故障 fail-closed）；审计 WARN 指标 | T1（白名单/来源标识定案部分） |
| **T3** 协议头规范 v1.0 + OpenBase 试点 | K02(规范) / SYS-1 | OpenBase + 发布物 | 规范文档（头语义/取值/校验/行为矩阵/错误码/双通道不变式）；共享校验函数/常量包（参考实现 + 单测）；OpenBase 侧试点（get_current_tenant 入站 X-Tenant-Id 优先级收口、get_identity_context 入站头校验、非白名单带头 403） | T1（头规范基线）；试点依赖 T2 白名单 |
| **T4** 端点-过滤矩阵模板 v1.0 | K07 / SYS-1 | OpenBase（模板发布） | 模板表（端点类别×过滤覆盖三态）+ 填报流程 + openapi 自动核对脚本骨架；S2-S5 填报跟踪表登记；S7 终验钩子 | T3（类别与过滤语义一致） |
| **T5** OB-6 服务账号受信通道 + agent 审计贯穿 | OB-6 / Q2-S6 / L3-1 前置 | OpenBase | sk-agent-* 主体经四 proxy 出站身份头/来源标识齐全（消除二次解码缺口）；服务账号禁匿名直连断言；agent 出站审计（agent_id+source+域+动作）；U1 agent 密钥面回归不破坏 | T1、T3（来源标识） |
| **T6** OB-12 角色互译表（起步） | OB-12 / 最小集 §6.3 | OpenBase + DPS（映射测试配合点） | 配置化互译表（OpenBase↔DPS，语义档锚）；映射测试绿；无映射角色 fail-closed 用例；Q-D 评审记录 | —（T1 后可并行） |
| **T7** OB-8 code 化收口 | OB-8 / P1-2/P1-3 | OpenBase | X-Org-ID 别名收敛（org_raw 链收为 tenant_code/别名表）；dps org/tenant code→UUID 映射生产化基线 + 对账报告 | T1、T3 |
| **T8** OB-13 审计贯穿（OpenBase 侧） | OB-13 / §4.4 | OpenBase | audit_logs 补 request_id + principal/delegated 两层 + 来源字段（detail 扩展）；proxy 出站审计钩子（request_id 透传）；与 U4 边界文档 | T1、T5 |
| **T9** OB-9 verify-env 雏形 | OB-9（雏形）/ 复盘 S1 | OpenBase | config 契约清单首个版本；`scripts/verify-env.ps1`（编排 start 比对 config 单源/端口/URL/白名单矩阵/映射/code 对账，WARN→后续 fail-fast）；连接账号/schema 检查位（配合 OB-7 登记） | T3（白名单矩阵事实源） |
| **T10** 回归与段门禁收口 | K01/K03/K02/K07 + OB-6/8/9/12/13 / RA-06 联动 | OpenBase | 全量回归（proxy 行为/存量测试）；台账回写（任务卡 K01/K03 已立项、K02 规范已发布、K07 模板已发布；升级项 OB-3/6/8/9/12/13 状态）；S1b 段门禁自检 | T1-T9 |

**P2-1 ↔ U1 / P2-2 边界防重复（U1 已交付项不重复实施）**：

| 已交付/在途 | 承接方 | 本立项不重复实施 |
|-------------|--------|------------------|
| Principal 模型 + sk-agent-* 密钥面（U1 T1）；状态机 + login tenant_code（U1 T2）；token 版本号吊销 + verify_principal（U1 T3）；委托 claim/校验器/逐跳重校验骨架（U1 T4）；L1-1 事件源（U1 T5）；L1-2 purge（U1 T6） | U1（S1a，已完成） | 主体模型、密钥发放/轮换/吊销 API、状态门禁/版本强校验、委托域校验骨架——本立项只**消费其 claim/主体上下文/校验器输出**，不重建 |
| 委托头全局唯一签发规范 + 信任链矩阵 | U1 T4 遗留 → **P2-1（S1b）** | 本立项 K01/K03 承接（§3.1/3.2） |
| verify_principal 对 DB 不可达/行缺失 fail-open 与委托场景裁定 | 待 **P2-1（S1b）信任链矩阵** | 本立项 K03 裁定（§3.2） |
| DPS fail-closed（RA-03/T1/T2）、X-User-ID=1 绑定核销（RA-04/T4） | P2-2（S0，DPS 仓） | DPS 中间件本体不回改；本立项只保证正常路径头语义不变 |
| OpenMemory sessions 归属（RA-05/T3）/骨架（K05）/唯一（K06） | P2-2（S0，OpenMemory 仓） | 本立项不触碰 OpenMemory 数据面 |

---

## 5. 验收标准

| 任务 | 验收 |
|------|------|
| T1（K01） | **全 proxy 出站头与协议头规范一致矩阵测试绿**（dps/llm/rag/memory 四头+来源标识逐一断言）；出站请求头仅来自签发上下文（客户端伪造头注入用例 → 剥离/拒绝）；`TRUSTED_PROXY_SOURCES`/来源标识全仓仅一种取值（静态扫描 0 处第二写法）；X-Proxy-Source 全链透传用例绿；委托出站头唯一签发规范文档化 |
| T2（K03） | 业务面无「未审计直连写」路径（扫描报告 0 高危项）；旁路清单收口留痕；**verify-env 裁定落地用例**：V-1/V-2 放行+WARN 计数、V-3 委托+DB 故障 → 403（fail-closed）、V-4 缓存不可达直读 DB、V-5 OpenBase 侧非白名单带头 403 |
| T3（K02） | **协议头规范 v1.0 发布物齐备**（规范文档 + 共享校验函数/常量包 + 参考单测）；规范评审通过（S1b 门禁）；OpenBase 侧试点：非白名单带头 403 用例绿、get_current_tenant 入站 X-Tenant-Id 不再无校验覆盖 JWT |
| T4（K07） | **端点矩阵模板评审通过**（S1b 门禁）；模板 + 填报流程 + 核对脚本骨架齐备；S2-S5 填报跟踪表登记完成 |
| T5（OB-6） | **服务账号受信源用例全绿**（sk-agent 经 llm/rag/memory/dps 出站头齐全且域正确）；agent 匿名直连写子系统 → 拒绝（0 可达）；agent 出站审计含 agent_id+source+域；U1 agent 密钥面回归全绿 |
| T6（OB-12） | **角色互译映射测试绿**（OpenBase↔DPS 起步语义档）；无映射角色请求 fail-closed 断言；Q-D 评审结论记录 |
| T7（OB-8） | X-Org-ID 别名收敛断言（出站 org==tenant_code 或别名表命中）；dps code→UUID 生产化映射基线对账报告 0 未决 |
| T8（OB-13） | **审计字段贯穿断言**（audit_logs 含 request_id + principal/delegated 两层 + 来源；抽样比对一致）；proxy 出站审计钩子用例绿；U4 联动边界文档化 |
| T9（OB-9） | **verify-env 雏形自检脚本可用**（编排 start 比对 config 单源/白名单矩阵/映射/code，故障可定位）；契约清单首个版本登记 |
| T10 | `python -m pytest tests` 全绿；`python -m ruff check openbase tests` 0 错误；覆盖率 ≥90%；台账回写完成；**S1b 段门禁全绿**：协议头规范 v1.0 发布 + 非白名单带头 403（OpenBase 侧）+ 服务账号发放/吊销（受信源）用例全绿 + verify-env 雏形可用 + 端点矩阵模板评审通过 |

---

## 6. 非目标与边界

本立项**不包含**以下事项（明确归他项，避免范围蔓延）：

| # | 事项 | 归属 |
|---|------|------|
| B-1 | K02 白名单身份头下游校验在真实子系统侧落地（OpenRAG/OpenMemory/DPS/OpenLLM 各仓中间件矩阵测试） | S1b 发布规范 v1.0 后 **S2/S3/S4/S5** 各段落地 |
| B-2 | 存储账号权限分离（任务卡 K13 / OB-7） | R2/U2 + **S7 终验**（本立项仅 verify-env 检查位登记配合） |
| B-3 | L3-1 Agent 端到端贯通（agent key→四头→各系统白名单→域隔离全链核验） | **S7 总收官**（本立项只做 OB-6 前置通道） |
| B-4 | U4 全链路审计（子系统侧审计字段落库、审计工作台、openbase_test 基建） | U4/R3（本立项只收 OpenBase 侧字段与 request_id 钩子） |
| B-5 | 前端壳（OB-10/FE-3）、前端统一入口加固 | **S6 前端段**/R4 |
| B-6 | 真实子系统侧 code 化迁移（K18 DP-2、K16/K17、表级归属迁移 R-L2-1）、角色细粒度互译扩展 | U2 / 子系统段 S2/S3/S4/S5 / R2 |
| B-7 | verify-env 完整版（多仓对齐、openbase_test 专用库、run_tests.ps1 固化、沙箱清单） | R3/S7（复盘 S1/S4 承接） |
| B-8 | REAL_* 兜底限期移除（R-L1-1 完整版）、OpenLLM 编排透传（K09/K15） | S4（LL 段）/R2 |
| B-9 | ob_k_ 服务 Key 主体化改造（改为 DB 持久化/挂主体） | 本立项**不做**（兼容存量）；服务账号形态由 sk-agent-* 承担（OB-6） |
| B-10 | Team/子租户隔离扩展、OIDC JIT 去重重构、主备切换演练（L2-1/L2-2 终验） | 扩展点 / S4 / S7 |

边界约定：本立项只动 OpenBase 主仓（出站头组装/入口校验/信任链裁定/规范与模板发布/服务账号通道/角色互译配置/审计字段/verify-env 雏形），不改造各功能系统业务数据层与中间件本体。

---

## 7. 影响面与兼容

### 7.1 对既有 proxy 行为的影响

- 出站头组装由「各自为政（dps/llm/memory 三处 JWT 二次解码）」收敛为「共享函数读统一主体上下文」。**值语义不变**（同一 JWT 的主体域/角色），仅补齐缺失头（llm 补 X-Tenant-ID/X-User-Role、memory 补 X-User-Role/X-Proxy-Source、rag 补全部身份头、dps 补 X-Proxy-Source）。
- 过渡策略：**先加头（下游无白名单强校验时不改变既有放行行为）→ 后强校验/剥离（S1b 门禁后）**两段式；新增头对未启用白名单校验的下游为幂等附加，不构成 403 回归面；下游 K02 上线前，`X-Proxy-Source` 仅进审计不改变行为。
- 兼容开关：`enforce_proxy_identity_headers`（出站全量对齐）与 `strip_inbound_identity_headers`（入站剥离，默认关→S1b 门禁开启）两个 settings 布尔，便于回滚。

### 7.2 对服务 Key 与存量调用方的影响

- **ob_k_***：鉴权语义与 `/proxy` 通用通道行为不回改（兼容存量脚本/调用方）；服务账号场景改走 sk-agent-*（主体化）。若存量调用方依赖 ob_k_ 经 `/proxy` 匿名直穿，属「匿名直连」缺口 → K03 收口清单登记并给出迁移指引（换 sk-agent 服务账号 + 出站身份头）。
- **sk-agent-***：新增经 llm/memory proxy 的识别能力（现 dps 部分可用、llm/memory 不可用），属能力补足非破坏；agent 主体身份头随出站注入后，下游若已启用白名单按来源放行，行为一致。
- **存量调用方（前端/脚本）**：若此前依赖「客户端自行携带 X-Tenant-Id/X-User-ID 头被 OpenBase 采信」——入站头收口后不再作为事实源（剥除或 403）。影响面按端点清单化并在发布说明标注；迁移期（剥除默认关）先审计告警再强校验。

### 7.3 X-Org-ID 别名收敛与双通道口径（Q-4）

- 出站 X-Org-ID 收敛为 tenant_code 别名；下游（DPS/OpenMemory/OpenLLM）org 语义读取在过渡期保持兼容（org==tenant 同值），别名表驱动；不落 org 语义新库行（最小集 §4.2）。
- 头规范与 S4 通道矩阵按 **Q-4「B（经 OpenLLM）主 / A（OpenBase 直连）备」** 口径实现：同一动作同一时刻仅一条主路径，A/B 通道携带的头语义/来源标识不变式一致（L2-1 切换时头可追溯、不因通道改变身份语义）。

### 7.4 对既有 JWT/verify_principal 的影响

- 不改 U1 已定案 claim 与校验语义；V-1/V-2 维持 fail-open 过渡、V-3 委托 fail-closed 为**新增收紧分支**（仅委托请求受 DB 故障影响），正常委托路径（DB 可用）行为不变（跨界仍 403）。
- 审计 detail 扩展为向后兼容（新增字段，不删既有 user_id/tenant_id/request_id）。

---

## 8. 风险与依赖

### 8.1 依赖

- **R1（S1b 门禁/规划）**：本立项即 S1b 唯一实施载体；K02 规范 v1.0 发布时间决定 S2-S5 排期（规划 §4：S2/S3/S5 的 K02 按 S1b 发布的 v1.0 规范执行）——规范发布为段内关键路径。
- **R2（Q-4 B 主 A 备口径）**：头规范与 S4 通道矩阵（L2-1/L2-2）须同口径（§7.3）；S4 前规范冻结，变更走评审。
- **R3（S1a/U1 已收口面）**：U1 已交付 claims（tenant_code/sub_type/tvn/role）与 verify_principal 为本立项事实源；不冲突、不重做；委托头唯一签发以 U1 delegation.py 骨架为底座。
- **R4（P2-2/S0 已收口面）**：DPS fail-closed 正常路径依赖四头，本立项出站头值语义不变，段门禁互证（不破坏 S0 已收口隔离用例）。
- **R5（外部配合点）**：OB-12 映射测试需要 DPS 侧角色对账配合；K07 填报需要 S2-S5 各仓在对应段执行；S7 终验依赖各段完成。

### 8.2 风险与缓解

| # | 风险 | 缓解 |
|---|------|------|
| 1 | 出站头增补/入站头收口被下游或存量调用方误判（新增 X-User-Role/X-Tenant-ID 至 llm/rag、org 头语义收敛） | 两段式（先加头后强校验）；settings 回滚开关（§7.1）；与 S2-S5 侧 K02 时间窗对齐：规范先发、代码对齐与下游落地同批串行；发布说明影响清单 |
| 2 | 委托请求 DB 故障 fail-closed（V-3）误拒正常委托（DB 抖动窗口） | 与 dps-proxy 探活/编排 DB_FAIL_FAST 双保险协同；故障窗口由探活感知与告警；fail-closed 仅限委托分支，普通请求不受影响（V-1 维持放行） |
| 3 | verify-env 雏形 fail-fast 误报阻断编排启动 | 雏形先「比对 + WARN + 报告」，S1b 门禁要求「可用」而非全量阻断；fail-fast 语义随 R3 完整版收紧 |
| 4 | rag/memory 新增身份头时，对应仓中间件尚未接受（未启用白名单） | 规范 v1.0 与各段 K02 落地解耦：本立项仅 OpenBase 侧出站 + 试点，真实子系统 403 强校验在各段自行落地（非本立项代码面） |
| 5 | 审计字段扩展写放大（audit_logs detail JSON） | 控制 detail 体积（截断/采样策略登记）；request_id 与两层身份为结构化列优先；批量/回调端点审计降频配置化 |
| 6 | 入站头收口影响审计/上下文既有消费（X-Tenant-Id 优先级翻转） | get_current_tenant 收口与 get_identity_context 校验分开两段上线；先剥除审计告警、后强校验；相关端点清单化回归 |

---

## 9. 里程碑与五步流程衔接

本立项为规划 S1b（OpenBase 协议与服务段，P2-1+服务账号域）的唯一实施载体，严格走「需求 → 设计 → 开发 → 测试 → 部署」五步与人工门禁；每步产出经批准后方进入下一步（用户五步流程规则）。

| 步骤 | 输入 | 活动与产出 | 门禁 |
|------|------|-----------|------|
| ① 需求 | 本方案（[Draft]） | 立项方案评审 → [Review] → [Approved]；对齐 S1b 范围与 Q-4/Q-5 定案、§3.2 裁定表评审确认 | 人工批准进入设计 |
| ② 设计 | 批准的需求 | P2-1 设计评审：协议头规范 v1.0 文档（头语义/取值/校验/行为矩阵/错误码）；共享校验函数/常量包设计；角色互译映射表（OB-12，Q-D 结论）；端点-过滤矩阵模板 v1.0；落点清单（§2 行号 + 实现补充盘点）；verify_principal 裁定落地设计（V-1~V-5）；verify-env 雏形清单 | 与需求文档/任务卡比对无遗漏（K01/K03/K02/K07/OB-6/8/12/13/9）；人工批准进入开发 |
| ③ 开发 | 批准的设计 | TDD（RED→GREEN）按 T1→T10；遵循 AGENTS.md（分层/错误码/结构化日志/参数化查询）；`python -m ruff check openbase tests` 0 错误 | 实现与设计一致（追溯矩阵）；人工批准进入测试 |
| ④ 测试 | 开发成果 | 单测 + 集成 + 矩阵测试（出站头一致性/白名单 403/映射测试/审计贯穿断言/verify-env 用例）；`python -m pytest tests` 全绿、覆盖率 ≥90%；回归存量 proxy/服务 Key/调用方（§7） | 测试回溯覆盖 §5 全部验收项；人工批准进入部署 |
| ⑤ 部署 | 测试通过 | 幂等迁移（无表结构变更预期，若涉及 audit detail 扩展列则 W1-4 幂等）；两段式发布（先加头/后强校验）；存量调用方影响清单公示；台账回写（任务卡 K01/K03→已立项、K02 规范 v1.0 已发布、K07 模板已发布；升级项 OB-3/6/8/9/12/13 状态） | **S1b 段门禁全绿**：协议头规范 v1.0 发布 + 非白名单带头 403（OpenBase 侧）+ 服务账号受信源用例全绿 + verify-env 雏形可用 + 端点矩阵模板评审通过 → 进入 S2 |

- **测试策略**：TDD（RED→GREEN）贯穿；单元（头组装/校验函数/常量包/裁定分支/互译表）→ 集成（proxy 出站/入口试点/审计）→ 矩阵测试（四 proxy × 四头 × 来源标识）→ 回归（存量 proxy/服务 Key/调用方）。
- **里程碑引用**：本立项属 R1 批次（身份与隔离收口）+ S1b 段；完成即 S1b 收官，随后 S2（OpenMemory）按规范落地 K02 并填报 K07。S7 总收官 RA-06 门禁引用本立项 §5 断言与矩阵/模板终验（K07、SYS-1、L3-1）。

---

## 附录 A：术语对照

| 术语 | 说明 |
|------|------|
| 四头 | X-User-ID / X-Tenant-ID / X-User-Role / X-Proxy-Source（信任链规范头）；X-Org-ID 为退役兼容别名（OB-8 收敛） |
| 委托头 | on_behalf_of 委托 claim 的出站承载头/语义，唯一由 OpenBase 签发（U1 T4 遗留移交） |
| TRUSTED_PROXY_SOURCES | 受信来源白名单（最小集 §12.1 R-H1-1/2；K02 行为矩阵） |
| ob_k_ | 既有服务 Key（内存态，本立项兼容保留，不主体化） |
| sk-agent-* | agent 主体服务密钥（U1 T1 落地；本立项收口受信通道与审计，OB-6） |
| verify-env | 启动配置自检（复盘 S1；OB-9 雏形并入本立项） |
| S1b 段门禁 | 协议头规范 v1.0 发布 + 非白名单带头 403（OpenBase 侧）+ 服务账号用例全绿 + verify-env 可用 + 端点矩阵模板评审通过 |

## 附录 B：参考既有文件清单（盘点实证）

- 代码：`openbase/modules/dps_proxy/__init__.py`、`llm_proxy/__init__.py`、`rag_proxy/__init__.py`、`proxy/memory_proxy.py`、`proxy/__init__.py`、`core/deps/auth.py`、`core/cache/redis_client.py`、`modules/auth/api_keys.py`、`modules/identity/{verification,delegation,agent_keys,__init__}.py`（行号以 HEAD=2f9b5fd 为准）
- 文档：`OpenBase-多系统联调联试分阶段版本规划-子系统纵切-v1.0.0.md`（v1.3.0）、`OpenBase-数据隔离实现任务卡-v1.0.0.md`（v1.2.0）、`OpenBase-统一身份最小特征集与隔离模型设计-v1.0.0.md`（v1.3.0）、`OpenBase-U1-统一身份收口设计草案-v1.0.0.md`（v1.1.0）、`OpenBase-U1-统一身份收口立项方案-v1.0.0.md`（v1.1.0）、`OpenBase-多系统对接联调问题复盘与根治方案-v1.0.0.md`（v1.1.0）、`OpenBase-P2-2-隔离与fail-open收口立项方案-v1.0.0.md`、`OpenBase-多系统对接-文档体系与升级路线规划-v1.0.0.md`

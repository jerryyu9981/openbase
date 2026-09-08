# OpenBase-P2-1-统一身份协议头与信任链收口设计草案-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-P21-DESIGN-v1.0.0 |
| 版本 | v1.1.0 |
| 状态 | [Approved]（2026-09-08 经人工批准：按草案进入开发阶段；批次 1/2（T1~T6）与批次 3（T7~T10）实施完成，S1b 收官，见 P2-1 DevLogReport v1.0.0） |
| 日期 | 2026-09-07 |
| 作者 | P2-1 设计组（TS/AD） |
| 版本主题 | P2-1 设计草案：四头/委托头/X-Proxy-Source/X-Request-Id 协议头规范 v1.0（K02 规范正文）、共享常量/校验函数包（`openbase/modules/protocol_headers/`）、K07 端点-过滤矩阵模板 v1.0、K03 禁旁路与信任链裁定落地（V-1~V-5 定案）、OB-12 角色互译配置（Q-D 记录）、OB-8 code 化收口、OB-13 审计贯穿（OpenBase 侧）、OB-6 服务账号受信源收口、OB-9 verify-env 雏形、T1~T10 TDD 断言清单、落点/迁移/风险/里程碑 |
| 适用范围 | OpenBase 主仓（proxy 族出站/入口中间件、身份头规范与共享包、信任链裁定、服务账号受信通道、审计贯穿、verify-env 雏形、端点矩阵模板）；对外契约面（协议头规范 v1.0 与 K07 模板随 S1b 发布，供 S2/S3/S5 各子系统段照做；DPS 角色互译配合）；文档面（S2-S7 各段填报矩阵、S7 RA-06 终验引用） |
| 上游依据 | 《OpenBase-P2-1-统一身份协议头与信任链收口立项方案》v1.0.0（OB-INTG-P21-v1.0.0，2026-09-07 已批准；§2 现状盘点代码证据行号、§3 范围定案含 V-1~V-5 裁定建议表、§4 任务分解 T1~T10、§5 验收、§6 边界、§7 影响兼容、§9 里程碑门禁）；《OpenBase-U1-统一身份收口设计草案》v1.1.0（[Approved]，U1 实施后最终状态：U1 移交项与模式参照）；《统一身份最小特征集与隔离模型设计》v1.3.0（§4.4 审计、§6.3 角色互译、§12.1 R-H1、§12.5 R-M2、§12.7 R-M4、§12.9 R-L1-1）；《多系统联调联试分阶段版本规划（子系统纵切）》v1.3.0（S1b 门禁、Q-4 B 主 A 备口径）；《OpenBase-P2-2-隔离与fail-open收口立项方案》v1.0.0（V-3/D1/D2 授权面 fail-closed 同构参照） |

> 设计输入纪律：本草案为五步流程「② 架构与设计」阶段的 P2-1 设计产出（立项方案 §9 步骤②）。内容以「OpenBase 仓真实代码盘点结果（HEAD=914f00b）」为落点基线（§2），与需求文档（立项方案 T1~T10 及 §5 验收标准）逐项比对，保证响应无遗漏（§1 覆盖矩阵）；协议头规范 v1.0 正文即 §3，可按 K02 发布物要求整体裁出；经人工批准后方进入开发阶段（T1~T10，TDD RED→GREEN）。

> **批准注记（v1.1.0）**：日期 2026-09-08；批准内容「按草案进入开发阶段」（用户对话确认 Q-D-1~3 与「按这个方案来」，流程批准登记）；状态由 [Draft] 更新为 [Approved]。T1~T6 已按 §10 TDD 断言清单（RED→GREEN）实施并提交（批次 1/2：25b65d7/51c6657/09f28fa/9a0aa49）；T7~T10 批次 3 收口完成（T7/T8/T9 代码提交见 git log；T10 回归/门禁/台账回写见 P2-1 DevLogReport v1.0.0 与测试报告 v1.0.0），S1b 收官、移交 S2-S5。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-07 | P2-1 设计组 | 初始版本：现状落点清单（HEAD=914f00b 代码证据）；需求覆盖矩阵（T1~T10）；协议头规范 v1.0 详细设计（头语义/取值优先级/格式约束/校验规则/代理族出站注入矩阵/委托头/示例）与 K02 发布物结构；K07 端点-过滤矩阵模板 v1.0；K03 禁旁路与 V-1~V-5 信任链裁定定案（含过渡豁免白名单清单机制）；OB-12 角色互译配置（Q-D 记录）；OB-8 code 化收口；OB-13 审计贯穿；OB-6 服务账号受信源收口 + OB-9 verify-env 雏形（OB-7/OB-10 外移说明）；T1~T10 实现步骤与 TDD RED 断言清单（覆盖立项 §5 验收逐条）；落点清单、迁移/兼容、风险、里程碑 |
| v1.1.0 | 2026-09-08 | P2-1 开发组 | 状态回写（批准注记）：2026-09-08 经人工批准「按草案进入开发阶段」（依据：用户对话确认 Q-D-1~3 与「按这个方案来」）；[Draft] → [Approved]；登记批次 1/2 提交链（25b65d7/51c6657/09f28fa/9a0aa49，T1~T6）与批次 3 收口（T7~T10）引用 |

---

## 1. 设计输入、范围与需求覆盖矩阵

### 1.1 范围锚定（承接立项 §3 定案，逐条引用不再重议）

| 立项定案 | 本草案承接位置 |
|---------|---------------|
| K01 四头/委托头唯一签发 + X-Proxy-Source 全链透传（§3.1） | §3 协议头规范 v1.0（取值/注入/校验）、§10 T1 |
| K03 禁旁路 + verify_principal fail-open 裁定（§3.2，V-1~V-5 建议表） | §5 裁定定案（V-1~V-5 → D-V1~D-V5）、§10 T2 |
| K02 协议头规范 v1.0（规范发布 + OpenBase 侧试点，§3.3） | §3（规范正文）+ §3.9（发布物）+ §10 T3 |
| K07 端点-过滤矩阵模板 v1.0（§3.4） | §4 模板 + §10 T4 |
| OB-6 服务账号受信源收口（§3.5，L3-1 前置） | §9.1 + §10 T5 |
| OB-12 角色互译表（§3.6，Q-D 待评审） | §6 + §10 T6 |
| OB-8 code 化收口（§3.7） | §7 + §10 T7 |
| OB-13 审计贯穿 OpenBase 侧（§3.8，U4 联动边界） | §8 + §10 T8 |
| OB-9 verify-env 雏形并入 / OB-7 外移配合 / OB-10 外移牵头（§3.9） | §9.2/§9.3 + §10 T9 |
| 边界 B-1~B-10（§6）；影响兼容（§7）；风险依赖（§8） | §11.2/§11.3 与各章「边界」小节复核 |

### 1.2 U1 实施后最终状态（模式参照，不重复实施）

U1 已交付（S1a，v1.1.0 [Approved]，T1~T7 合入；本草案仅**消费**其产物，不重建）：

- Principal 模型（`users.subject_type/status_state/token_version/tenant_code` 等增量列）、`agent_api_keys` 密钥面、单一签发器 `issue_token_pair`（含 `tenant_code/sub_type/tvn/role` 全量 claim）——见 `core/models/base.py`、`identity/agent_keys.py`、`auth/jwt.py`。
- 生命周期状态机（`identity/state_machine.py`）、token 版本号吊销（`identity/verification.py` `verify_principal`）、login 100% tenant_code 闭环。
- on_behalf_of 委托 claim + 域不变式校验器（`identity/delegation.py`：`verify_delegation`/`verify_request_delegation`/`issue_delegated_token_pair`/`delegated_claim_from_payload`）。
- **U1 T4 遗留移交项（R2 边界）**：`delegation.py` 头注释 L22-23 明示「委托头（X-Proxy-Source 等）的全局唯一签发规范 / 信任链矩阵留 P2-1（S1b）」；`DevLogReport` S1b-1 行登记同口径——本草案 §3.6/§5.3/§10 T1-T2 承接。
- U1 草案 §7.3 委托审计两层（principal+delegated）、§8 事件载荷 `request_id` 预留、§1.1 `audit_logs` 既有字段面（user_id/tenant_id/request_id/detail JSON）为 OB-13 扩展底座（§8）。

### 1.3 最小特征集与纵切规划引用

- 最小集 §12.1 R-H1-1/2/3/4（唯一注入点/下游校验/编排透传/禁旁路）、§12.5 R-M2-1（端点类别全覆盖）、§12.7 R-M4（委托不跨界）、§12.9 R-L1-1（豁免=服务账号/受信编排；REAL_* 限期移除）、§4.4（审计 source/request_id）、§6.3（粗粒度角色互译）——规则→设计锚点映射见附录 B。
- 纵切 v1.3.0 S1b 段定义与门禁（非白名单带头 403 OpenBase 侧 / 协议头规范 v1.0 发布 / 服务账号发放与吊销用例全绿 / 端点矩阵模板评审通过）——本草案 §10 T10/§11.4 收敛；Q-4「默认 B（经 OpenLLM）主、A（OpenBase 直连）备」口径贯穿 §3.7（双通道不变式）与 §11.2。

### 1.4 需求覆盖矩阵（与立项 T1~T10 及 §5 验收逐项对齐）

| 立项任务 | 本草案设计章节 | TDD 断言 |
|---------|---------------|---------|
| T1（K01 唯一签发/出站对齐） | §3.1-3.6、§3.9 | §10 T1（T1-1~T1-12） |
| T2（K03 禁旁路/裁定落地） | §5 | §10 T2（T2-1~T2-10） |
| T3（K02 规范发布 + OpenBase 试点） | §3.9、§5.4 | §10 T3（T3-1~T3-9） |
| T4（K07 模板） | §4 | §10 T4（T4-1~T4-5） |
| T5（OB-6 服务账号受信源） | §9.1 | §10 T5（T5-1~T5-7） |
| T6（OB-12 角色互译） | §6 | §10 T6（T6-1~T6-6） |
| T7（OB-8 code 化收口） | §7 | §10 T7（T7-1~T7-7） |
| T8（OB-13 审计贯穿） | §8 | §10 T8（T8-1~T8-7） |
| T9（OB-9 verify-env 雏形） | §9.2 | §10 T9（T9-1~T9-6） |
| T10（回归与 S1b 段门禁） | §11.2/§11.4 | §10 T10（T10-1~T10-6） |

---

## 2. 现状落点清单（代码盘点行号，HEAD=914f00b 核对）

> 仓库根：`D:\Trae CN\myproject\Dev\OpenBase`。**行号以本草案撰写时 `HEAD=914f00b` 代码为准**（立项方案盘点标注 `HEAD=2f9b5fd`；两提交间仅合入文档提交 914f00b，代码零变更，故本清单行号与立项 §2 盘点一致，可直接对读）。路径均为仓相对路径。

### 2.1 proxy 族出站身份头注入现状（设计改造对象）

| proxy | 文件:行号（注入/取值函数） | 出站注入（现状） | 缺失/问题（本草案目标修正锚点） |
|-------|---------------------------|------------------|-------------------------------|
| 通用 proxy | `openbase/modules/proxy/__init__.py:67-120`（`proxy` 路由，`get_proxy_identity` L72） | **纯转发**：仅透传 Content-Type/Accept（L84-87），不注入任何身份头 | 全缺（G-P3 服务身份面；本草案 §3.5 通用 proxy 行：ob_k_/JWT 均补 X-Proxy-Source + 有效身份头，服务账号形态见 §9.1） |
| dps-proxy | `openbase/modules/dps_proxy/__init__.py:90-135`（`_build_identity_headers`）；`_jwt_payload` L60-71（二次解码） | 四头 X-User-ID/X-Tenant-ID/X-Org-ID/X-User-Role；委托分支 L101-115 取委托域值；tenant_raw/org_raw 链 L116-129（tenant_code→user.tenant_id→org_id→dps_default_*→映射表） | **无 X-Proxy-Source**；二次解码（sk-agent → 解码 None → 回落默认链）；org 头独立取值链未退役（§3.5/§7） |
| llm-proxy | `openbase/modules/llm_proxy/__init__.py:41`（`PROXY_SOURCE_IDENTIFIER="openbase-llm-proxy"` 模块内写死常量）；`_extract_identity` L62-93（二次解码+委托覆盖 L85-93）；`_build_upstream_headers` L96-120 | X-User-ID（L116）、X-Proxy-Source（L117，唯一注入来源标识者）、X-Org-ID（L118-119）；匿名/服务调用不带身份头（L114-115） | **无 X-Tenant-ID/X-User-Role**；来源标识为模块内常量（§3.3/§3.9 单一事实源收口）；二次解码（sk-agent 不识别，§2.3） |
| rag-proxy | `openbase/modules/rag_proxy/__init__.py:82-96`（`_build_upstream_headers`） | 仅 X-API-Key（L94-95，可空不注入） | **零身份头**（G-P1 最重；§3.5 补 X-User-ID/X-Tenant-ID/X-User-Role/X-Org-ID(别名)/X-Proxy-Source） |
| memory-proxy | `openbase/modules/proxy/memory_proxy.py:50-84`（`_extract_identity` 二次解码，委托 L68-77）；`_build_upstream_headers` L87-108 | X-API-Key（L103）+ 透传原 JWT（L104，OpenMemory 双层认证）+ X-Org-ID（缺省 `openbase-default` L98/L105）+ X-User-ID（L106）+ X-Tenant-ID（缺省 `default` L99/L107） | **无 X-User-Role/X-Proxy-Source**；org/tenant 硬编码缺省兜底；sk-agent 无 JWT → 二次解码 401（G-P3 重演面，§9.1 D-OB6-3） |

**共同结构问题（T1 直接改造面）**：dps/llm/memory 三处各自从 `Authorization` 头二次解码 JWT（dps L60-71、llm L62-93、memory L50-84）取 extra 字段，而非消费 `get_current_user`（`core/deps/auth.py:156-233`）返回的统一主体 dict（已含 tenant_code/subject_type/role/on_behalf_of/delegated，L214-233）；`sk-agent-*` 凭据在三处二次解码路径上不被识别。目标 = 抽共享头组装函数（§3.9 共享包）读统一上下文，删除三处二次解码。

### 2.2 入口/依赖层身份头读取现状（OpenBase 侧入站收口对象）

| 落点 | 文件:行号 | 现状行为 | 本草案处置 |
|------|-----------|---------|-----------|
| `AuthMiddleware.dispatch` | `core/deps/auth.py:75-108` | PUBLIC_PREFIXES L57-73（含 `/api/v1/proxy`）；sk-agent-* 令牌放行至依赖层（L91-94）；每请求 `_verify_request_principal`（L110-128，仅数字 sub 开 DB 会话） | 追加「入站身份头来源校验」钩子（非受信来源带头 → 剥除审计或 403，开关化，§5.4/§10 T3）；request.state 透传 identity 上下文供审计（§8） |
| `get_current_user` | `core/deps/auth.py:156-233` | sk-agent → `resolve_agent_principal`（L177-180）；JWT → `verify_principal`（L194）；返回主体 dict（L214-233） | **作为统一上下文唯一事实源**；代理族出站改读本返回值（§3.2/§3.9）；sk-agent 路径识别已具备（§9.1） |
| `get_current_tenant` | `core/deps/auth.py:236-255` | **优先取入站 `X-Tenant-Id` 头（L244-246），其次 JWT**——客户端可自带头覆盖 | 试点收口：入站头仅在受信来源（TRUSTED_PROXY_SOURCES）时优先，否则以 JWT/上下文为准；`strip_inbound_identity_headers` 开启后剥除（§3.4/§10 T3） |
| `get_identity_context` | `core/deps/auth.py:277-313` | 读入站 X-User-Id/X-Tenant-Id/X-Team-Id/X-Agent-Id（L282-285），JWT 回退；供审计 extra | 同一来源校验；来源字段进入审计（§5.4/§8） |
| `get_proxy_identity`/`require_api_key` | `core/deps/auth.py:370-387` / L318-367 | X-API-Key 或 Bearer `ob_k_*` → 服务 Key 认证（scope 按路径 system）；其余 JWT。无身份头注入、无来源标识绑定 | 通用 proxy 出站经统一 builder 补头（§3.5）；ob_k_ 服务账号语义映射（§5.2 D-V6/§9.1） |

### 2.3 服务 Key 信任面（ob_k_ 与 sk-agent-*）

| 凭据面 | 落点 | 现状 | 本草案处置 |
|--------|------|------|-----------|
| `ob_k_*` 既有服务 Key | `openbase/modules/auth/api_keys.py`：KEY_PREFIX L19；create L35-63、revoke L65-72、verify L76-105、list L107-115、`_hash` L117-120 | 内存态、无主体语义（不挂 sub/域/角色/状态）、scope=system/tenants | 鉴权语义与 `/proxy` 通道不回改（B-9 兼容存量）；K03 收口其「匿名直穿」为显式服务账号通道或豁免白名单（§5.2/§5.4）；服务账号主体形态由 sk-agent-* 承担 |
| `sk-agent-*` agent 密钥（U1 T1 已落地） | `openbase/modules/identity/agent_keys.py`：`resolve_agent_principal` L116-165 | DB 持久化、主体化（subject_type=agent）、状态门禁齐备；返回含 tenant_code/roles/status_state/auth_method | 四 proxy 出站头/来源标识齐全（消除二次解码缺口，§3.2/§9.1）；agent 审计贯穿（§8/§9.1）；回归 U1 密钥面不破坏（§10 T5-7） |

### 2.4 委托出站现状（U1 T4 遗留接续）

- `identity/delegation.py`：on_behalf_of claim 结构（L47-51）、`delegated_claim_from_payload`（L188-200）、`verify_delegation`（L213-336，含 DB session 依赖 L289-319）、`verify_request_delegation`（L339-375）、`enqueue_delegation_audit`（L378-428，detail 两层）、`issue_delegated_token_pair`（L431-496）。
- dps/memory/llm 三 proxy 已消费委托域值做出站头（dps L101-115、memory L68-77、llm L85-93）。
- **遗留**：委托头全局唯一签发规范 / 信任链矩阵 / DB 故障下委托裁定（V-3）→ 本草案 §3.6/§5.3/§5.1 承接。

### 2.5 verify_principal fail-open 现状与 Redis 降级（V-1~V-5 裁定改造点）

- `identity/verification.py` `verify_principal`（L167-249）：
  - sub 非数字（OIDC 直签/外域）→ 放行（L193-195）；
  - **DB 读不可达 → WARN + 放行（fail-open，L197-208）**；
  - **主体行缺失：purge 墓碑命中 → 401（L215-220）；无墓碑 → 放行（L221-225）**；
  - 状态门禁默认生效（L227-228）、版本强校验受 `enforce_token_version` 开关（默认关，L233-243）、委托逐跳重校验（L245-248）。
  - 本草案改造：DB 故障分支区分「是否携带 on_behalf_of」→ 委托请求 fail-closed（§5.1 D-V3）；行缺失无墓碑且带委托 → fail-closed（§5.1 D-V2）；快照缓存命中不依赖 DB 的普通请求保持 V-1 放行语义。
- `core/cache/redis_client.py`：懒初始化 + 不可用返回 None（L32-61）、cache 失败静默降级（L64-119）、publish 双形态（L149-186）。信任链判定一律以 DB 为准（V-4 钉死，§5.1 D-V4）。

### 2.6 审计与配置现状（OB-13/OB-9 改造点）

| 落点 | 文件:行号 | 现状 | 本草案处置 |
|------|-----------|------|-----------|
| `audit_logs` 表 | `core/models/base.py:445-462` | 字段：user_id/tenant_id/action/resource/resource_id/ip/user_agent/**request_id(not null)**/detail(JSON)/created_at | detail 扩展身份 schema（§8.2）；request_id 已具备（结构列）；不新增列（§8 决策 D-OB13-1） |
| 请求审计中间件 | `modules/audit/__init__.py`：`AuditMiddleware.dispatch` L222-244、`_record` L246-267；`APICallRecord` L31-50；`build_audit_record` L53-98 | 内存环形缓冲（5000 条）；request_id 生成 `req-{12hex}`（L227）；`X-Request-Id` 响应头（L243）；extra 仅 team_id/agent_id 占位 | 追加 principal/delegated/proxy_source/auth_method 字段（§8.3）；identity 上下文经 request.state 注入（AuthMiddleware 联动） |
| 委托/生命周期 DB 审计 | `identity/delegation.py` L378-428；`identity/lifecycle.py`（L55+ 各 action） | detail 两层 principal+delegated 已在委托签发落库 | schema 统一到 §8.2 `audit_identity` 契约，代理出站/agent 动作复用 |
| settings 映射与缺省 | `openbase/settings.py`：`dps_default_org_id` L181、`dps_default_tenant_id` L182、`dps_org_map` L184、`dps_tenant_map` L185；既有代理/上游键 L148-164 | 字符串 JSON 映射；无版本/校验 | §7.2 生产化基线（结构/校验/默认值策略）；§3.9 新增协议头相关键 |
| verify-env | 仓内无 `scripts/verify-env.ps1`/契约清单 | — | §9.2 雏形（T9） |

### 2.7 角色码现状（OB-12 锚点）

- OpenBase 现役角色码：`ALLOWED_ROLES = ("admin","org_admin","org_member","viewer")`（`modules/users/__init__.py:39`）；agent 可授角色同集（`identity/agents.py:27`）；委托角色阶 ROLE_RANK（`identity/delegation.py:60-65`，viewer<org_member<org_admin<admin）。OIDC 角色白名单 admin/org_admin/user/viewer（`auth/oidc.py:198`）。
- **无 `editor` code**：立项 §3.6 的「editor 语义档」须对账到现役 code（§6.2 对账结论：editor 读写/域管理档 ↔ 现役 `org_admin`，Q-D 记录）。

---

## 3. 协议头规范 v1.0 详细设计（K02 规范正文，供 S2/S3/S5 直接照做）

> 本节为「协议头规范 v1.0」的**单一事实正文**，发布时可整体裁出为独立规范文档（§3.9 发布物-文档形态）。凡 OpenBase 仓内实现、各子系统仓移植/落地，一律以本节为准。

### 3.1 头清单与语义定义

**规范头集（本规范 v1.0 管辖）**：

| 头名 | 语义 | 类型/必带 | 取值源（OpenBase 侧） | 备注 |
|------|------|-----------|----------------------|------|
| `X-User-ID` | 请求**有效主体** sub（字符串；委托时为 delegated.subject_id） | string ≤128 / 必带（身份可解析时） | 签发上下文（JWT sub / agent users.id / 受信编排透传） | 主体系引键；DPS/记忆等做属主/操作者 |
| `X-Tenant-ID` | **唯一隔离键** tenant_code | string ≤64 / 必带 | 统一上下文 tenant_code（JWT claim/主体行冗余列）；委托时 = 委托域 | 数据面域过滤唯一键（最小集 §5） |
| `X-Org-ID` | **退役兼容别名**，值恒 = X-Tenant-ID（或显式别名表命中值） | string ≤64 / 兼容期可选 | 别名收敛后与 tenant_code 同值（§7.1） | **不得承担独立取值链**；下游按 tenant 语义归一 |
| `X-User-Role` | 有效主体粗粒度角色 | string ≤64 / 必带（可解析时） | 统一上下文 role；**发往互译系统时经 OB-12 互译表转目标角色码**（§3.5/§6） | OpenBase 现役码 admin/org_admin/org_member/viewer；下游语义按目标系统 |
| `X-Proxy-Source` | 最后出口代理/编排**来源标识** | string ≤64 / 必带 | 来源标识常量包（本出口代理常量，§3.3） | 白名单校验主体；入站非白名单携带即伪造 |
| `X-Request-Id` | 链路贯穿请求 ID | string ≤64 / 必带 | OpenBase 审计中间件生成 `req-{12hex}`；受信来源入站可透传复用 | 子系统审计与 OpenBase 审计串联键 |
| `X-Agent-Id` | **执行者 principal 标注**（agent 主体 users.id；委托场景 = 执行 agent，非委托且主体为 user 时缺省） | string ≤64 / agent 或委托场景必带 | 统一上下文 subject_type=agent 时的 principal id | 复用既有四维头占位（auth.py L285）；使委托两层在下游可见 |
| `X-On-Behalf-Of` | 委托引用头（**形态 B，可选扩展**；见 §3.6） | string ≤512 / 可选 | 仅受信编排/OpenBase 委托签发链注入 | v1.0 默认不启用；启用时须与 JWT on_behalf_of claim 一致 |
| `X-API-Key` | 上游服务级 API Key（代理持钥出站） | string / 按 proxy 现状 | settings 上游 key | 非身份头；延续现状（rag/memory） |

**出站身份头集合（注入矩阵全集，§3.5）**：`X-User-ID/X-Tenant-ID/X-Org-ID/X-User-Role/X-Proxy-Source/X-Request-Id`，agent 与委托场景追加 `X-Agent-Id`。

### 3.2 取值规则：来源优先级（解析链与事实源裁定）

出站头取值**只允许来自「签发上下文」（R-H1-1 唯一注入点）**，禁止从客户端原始头、配置文件默认值、二次 JWT 解码结果直接取值。统一解析链（伪代码级，实现于 §3.9 共享包 `resolve_identity`）：

```text
0. 入站裁剪（entry gate，§3.4）：非受信来源携带的身份头（X-User-ID/X-Tenant-ID/
   X-Org-ID/X-User-Role/X-Agent-Id/X-On-Behalf-Of）一律不作为事实源——审计标注
   （strip_inbound_identity_headers=False 过渡期）或剥除/403（门禁后）。
1. 认证通道判定（与 get_current_user/get_proxy_identity 同构）：
   a. 受信编排透传（X-Proxy-Source ∈ TRUSTED_PROXY_SOURCES 且携带四头）
      → principal/域上下文 = 透传头值（上游编排已解析；完整链记审计 proxy_chain）。
   b. Bearer JWT（user/agent 主体验证通过）→ principal = {sub, subject_type,
      tenant_code, role, tvn, on_behalf_of}。
   c. Bearer/X-API-Key `sk-agent-*` → principal = resolve_agent_principal 返回
      dict（agent users.id/tenant_code/roles/status）。
   d. Bearer `ob_k_*` / X-API-Key 服务 Key → 服务账号语义（§5.2 D-V6/§9.1）：
      受信源配置绑定 → 服务主体上下文；未绑定 → 拒绝业务写（K03）。
2. 委托覆盖（最高优先，仅叠加于 b/c 的 agent principal 之上）：
   上下文含 on_behalf_of（JWT claim 或形态 B 头）→ 有效身份 = 委托目标：
   X-User-ID = delegated.subject_id；X-Tenant-ID/X-Org-ID = delegated.tenant_code；
   X-User-Role = delegated.role；X-Agent-Id = principal（执行 agent）users.id。
3. 无委托 → 有效身份 = principal 自身（X-Agent-Id 缺省或等于自身 agent id）。
4. 角色出站翻译（§6/§3.5）：发往配置了互译表的系统（起步 DPS）时，X-User-Role
   值经互译表映射为目标系统角色码；映射缺失 → fail-closed（403/配置错误告警）。
```

优先级一句话：**受信编排透传头 >（agent 委托上下文 >）JWT/服务 Key 解析出的统一主体上下文 > 显式默认值（仅兼容别名/兜底，受 §7 退役约束）**。任何一层缺失都不得回退到「客户端自带头」。

### 3.3 来源标识常量与单一事实源

来源标识常量（`protocol_headers/constants.py`）唯一发布，全仓（含 proxy）只允许 import，**禁止模块内写死第二写法**（静态扫描 0 处）：

| 常量 | 值 | 说明 |
|------|-----|------|
| `PROXY_SOURCE_DPS` | `openbase-dps-proxy` | dps-proxy 出站（新增） |
| `PROXY_SOURCE_LLM` | `openbase-llm-proxy` | llm-proxy 出站（**保留既有值**，`llm_proxy/__init__.py:41` 改读常量，下游白名单零迁移） |
| `PROXY_SOURCE_RAG` | `openbase-rag-proxy` | rag-proxy 出站（新增） |
| `PROXY_SOURCE_MEMORY` | `openbase-memory-proxy` | memory-proxy 出站（新增） |
| `PROXY_SOURCE_GENERIC` | `openbase-generic-proxy` | 通用 `/proxy/{system}` 出站（新增） |
| `PROXY_SOURCE_ORCHESTRATOR` | `openbase-orchestrator` | 受信编排层（可选注册；编排如需自行出站注入身份头时使用） |

受信来源配置：settings `trusted_proxy_sources: str = ""`（逗号分隔；`openbase-dps-proxy,openbase-llm-proxy,...` 等），默认空 = 不信任任何外部携带的身份头（OpenBase 自身出口不在其列——本仓入站本就不应收到本仓 proxy 回环带身份头；若编排拓扑需要回环透传，显式列入并审计）。**TRUSTED_PROXY_SOURCES 全仓仅一种取值**：常量/配置引用点唯一（T1-6 断言）。

### 3.4 校验规则与白名单行为矩阵（防伪造机制）

**机制（两层）**：

1. **入口裁剪（OpenBase 侧，本立项试点）**：所有非公开路径在认证前后校验入站身份头来源：
   - `X-Proxy-Source` 头存在且值 ∈ `trusted_proxy_sources` → 按受信编排透传处理（§3.2-1a），四头可被采纳并进审计；
   - `X-Proxy-Source` 头存在但值 ∉ 白名单 → **伪造来源**：过渡期剥除 + WARN 审计（`strip_inbound_identity_headers=True` 时物理剥除），门禁后 `enforce_inbound_identity_headers=True` → **403**（`PERM_UNTRUSTED_IDENTITY_HEADER`）；
   - 无 `X-Proxy-Source` 但携带四头（客户端直连 OpenBase 伪造身份）→ 一律不作为事实源：审计标注 `identity_headers_ignored`；门禁后按 403 或剥除+继续自身认证（开关化，§5.4）。
2. **出站单写**：出站头由共享 builder 生成（覆盖任何入站同名头），保证「下游收到的头 = OpenBase 签发值」。

**K02 行为矩阵（M1 语义，下游子系统按本矩阵实现中间件）**：

| 请求形态（下游视角） | X-Proxy-Source | 身份头 | 下游行为 |
|---------------------|----------------|--------|----------|
| 白名单来源 + 带身份头 | ∈ 白名单 | 有 | **信任**：按四头解析主体/域/角色（R-H1-2） |
| 白名单来源 + 无身份头 | ∈ 白名单 | 无 | 自身认证（M1 API Key/本地登录）后按自身域处理 |
| 非白名单 + 带身份头 | ∉ 白名单/缺失 | 有 | **403**（伪造头，R-H1-2；S2-S5 落地本行） |
| 非白名单 + 无身份头 | 缺失 | 无 | 自身认证（M1 独立模式 API Key）；不采信任何身份语义 |

错误码/403 形态：统一错误体 `{code, message, detail, request_id}`；新增错误码登记见 §3.8（`PERM_UNTRUSTED_IDENTITY_HEADER` 403 等）。

**双通道不变式（Q-4 B 主 A 备口径）**：同一动作同一时刻仅一条主路径；无论 A（OpenBase 直连）还是 B（经 OpenLLM 编排）到达子系统，头集合、来源标识白名单值、身份语义一致（L2-1 切换时可追溯、不因通道改变身份语义）；B 通道出站若由 OpenLLM 编排层注入，其 X-Proxy-Source 须登记在子系统白名单（TRUSTED_PROXY_SOURCES）且不得以 REAL_* 兜底值充当业务请求身份（R-H1-3）。

### 3.5 代理族出站注入矩阵（现状 → 目标）

| proxy | 头 | 现状 | 目标 | 落点函数（改） |
|-------|-----|------|------|----------------|
| dps-proxy | X-User-ID | ✓（delegated 优先） | ✓ 统一上下文 | `_build_identity_headers`（dps_proxy L90-135）删除 `_jwt_payload` 二次解码，改 `protocol_headers.inject.build_outbound_headers(request, user_ctx, target="dps")` |
| | X-Tenant-ID | ✓ | ✓（tenant_code 优先链保留，删 org_id 中间态） | 同上（取值链见 §7.1） |
| | X-Org-ID | ✓（org_raw 独立链 L124-129） | ✓ = tenant_code 别名（§7.1） | 同上 |
| | X-User-Role | ✓（role/缺省 user） | ✓（→ DPS 经互译表，§6） | 同上 + §6 翻译 |
| | X-Proxy-Source | **✗** | ✓ `PROXY_SOURCE_DPS` | 同上 |
| | X-Request-Id | ✗ | ✓ 透传 request_id | 同上 |
| llm-proxy | X-User-ID | ✓ | ✓ | `_extract_identity`（L62-93）删除；`_build_upstream_headers`（L96-120）改共享 builder |
| | X-Tenant-ID | **✗** | ✓ | 同上 |
| | X-Org-ID | ✓（org_id） | ✓ 别名 | 同上 |
| | X-User-Role | **✗** | ✓ | 同上 |
| | X-Proxy-Source | ✓（常量 L41） | ✓ 改读共享常量（值不变） | 同上 |
| | X-Request-Id | ✗ | ✓ | 同上 |
| rag-proxy | 四头 | **✗ 全缺** | ✓ 全部注入 | `_build_upstream_headers`（L82-96）改共享 builder（保留 X-API-Key） |
| | X-Proxy-Source/X-Request-Id | ✗ | ✓ | 同上 |
| memory-proxy | X-User-ID | ✓ | ✓ | `_extract_identity`（L50-84）删除二次解码；`_build_upstream_headers`（L87-108）改共享 builder |
| | X-Tenant-ID | ✓（缺省 default） | ✓（缺省仅显式兜底，§3.4 后同） | 同上 |
| | X-Org-ID | ✓（缺省 openbase-default） | ✓ 别名 | 同上 |
| | X-User-Role | **✗** | ✓ | 同上 |
| | X-Proxy-Source | **✗** | ✓ `PROXY_SOURCE_MEMORY` | 同上 |
| | X-Request-Id | ✗ | ✓ | 同上 |
| 通用 proxy | 四头+来源+request_id | **✗ 全缺**（纯转发 L84-87） | ✓ 全注入（JWT 与 ob_k_ 通道均按上下文） | `proxy/__init__.py:84-87` 改 `inject` |
| 编排 B 通道 | 头集合 | S4 段（OpenLLM 编排透传 K09/K15，B-8 外移） | 与 A 通道同规范 | S4 |

**值语义不变声明（兼容契约）**：同一 JWT/同一主体下，头值语义与现状一致（仅补缺失头、统一来源标识、退役 org 独立链），不改变下游已按现状头工作的放行/过滤行为（§11.2 两段式）。

### 3.6 委托头形态与 U1 delegation.py 的衔接（K01 委托头唯一签发）

- **委托上下文唯一签发**：on_behalf_of 委托上下文只由 OpenBase 经 `delegation.py` 的 `issue_delegated_token_pair`（L431-496）/`build_on_behalf_of_claim`（L154-185）或受信编排（白名单内）签发，校验走 `verify_delegation`/`verify_request_delegation`（域不变式/嵌套链逐跳）。本规范不新增第二签发路径。
- **形态 A（v1.0 默认）**：委托块承载于 JWT `on_behalf_of` claim（U1 已定，S2/S3/S5 消费端零额外实现）；出站四头承载**委托有效身份**（delegated.subject_id/tenant_code/role），`X-Agent-Id` 承载**执行 agent principal**（委托两层在下游/审计可见可记）。memory-proxy 走「透传原 JWT」通道时 claim 原样携带，无需拆头。
- **形态 B（X-On-Behalf-Of，可选扩展）**：受信编排无法透传 JWT（如 B 通道非 Bearer 形态）时，可用 base64url(compact JSON `{subject_id, subject_type, tenant_code, role, iss, exp}`) 头注入；**仅白名单来源可携带**，且与 JWT claim（若同时存在）必须一致，否则 403。v1.0 不建议启用（避免双载体一致性成本）；随 R2/编排形态扩展评审。
- **委托审计两层**：沿用 `enqueue_delegation_audit` detail `{principal:{id,tenant_code}, delegated:{id,tenant_code,role}}`（L401-408）并统一到 §8.2 schema。

### 3.7 双通道不变式、错误码与示例

**双通道**：见 §3.4（Q-4）。**错误码（新增，登记 `core/errors/codes.py`）**：

| 错误码 | HTTP | 语义 | 触发 |
|--------|------|------|------|
| `PERM_UNTRUSTED_IDENTITY_HEADER` | 403 | 非受信来源携带身份头（V-5 定案） | 门禁后入口校验 / 下游 K02 落地 |
| `PERM_DELEGATION_VERIFY_UNAVAILABLE` | 403 | 委托请求 + DB 不可达/行缺失无法证明不变式（V-2/V-3 fail-closed） | verify_principal 委托分支 |
| `PARAM_HEADER_FORMAT_INVALID` | 400 | 规范头格式/类型非法 | validate_identity_headers |
| `PERM_SERVICE_KEY_WRITE_DENIED` | 403 | 未绑定服务账号的 ob_k_/X-API-Key 匿名业务写被拒（K03 收口后） | /proxy 与代理族写路径 |
| `BIZ_ORG_ALIAS_MISMATCH` | 403 | X-Org-ID ≠ X-Tenant-ID 别名（§7.1 强模式，开关化） | 入口校验/出站装配 |

**示例（出站头，均为 builder 生成物）**：

```
例 1：普通用户经 dps-proxy 读画像（JWT sub=123, tenant_code=acme, role=org_admin）
X-User-ID: 123
X-Tenant-ID: acme
X-Org-ID: acme
X-User-Role: org_admin
X-Proxy-Source: openbase-dps-proxy
X-Request-Id: req-3f9a1c02d4e7

例 2：agent(users.id=7, tenant_code=acme) 代表 user(88) 经 llm-proxy 对话
    （JWT 含 on_behalf_of{subject_id:88, tenant_code:acme, role:viewer}）
X-User-ID: 88
X-Tenant-ID: acme
X-Org-ID: acme
X-User-Role: viewer
X-Agent-Id: 7
X-Proxy-Source: openbase-llm-proxy
X-Request-Id: req-6b21dd08e933

例 3：ob_k_ 服务 Key（网关监控，绑定 read 服务账号）经通用 proxy 读 OpenRAG
X-User-ID: 5001            # 服务账号主体 users.id（sk/service 化，§5.2 D-V6）
X-Tenant-ID: acme
X-User-Role: viewer
X-Proxy-Source: openbase-generic-proxy
X-Request-Id: req-… 
```

### 3.8 示例/错误响应形态（下游 403 样例）

```json
{
  "code": "PERM_UNTRUSTED_IDENTITY_HEADER",
  "message": "identity headers from untrusted source",
  "detail": {"proxy_source": "spoofed-origin", "headers": ["X-User-ID"]},
  "request_id": "req-3f9a1c02d4e7"
}
```

### 3.9 K02 规范 v1.0 发布物形态（文档 + 共享校验函数/常量包）

**发布物 = 三件套（S1b 门禁项，§10 T3 验收）**：

1. **规范文档**：本文 §3 裁出为《协议头规范 v1.0》（含头语义/取值优先级/格式约束/校验矩阵/白名单行为矩阵/错误码/双通道不变式/示例），S2/S3/S4/S5 各仓 K02 落地唯一依据。
2. **共享校验函数/常量包（落点 `openbase/modules/protocol_headers/`）**：
   ```
   openbase/modules/protocol_headers/
   ├── __init__.py            # 导出 + 包说明（纯库，不注册 enable_module、无 router）
   ├── constants.py           # 头名常量、来源标识常量、受信头集合、值域/长度约束
   ├── identity_context.py    # IdentityCtx dataclass：principal/delegated/effective 解析
   ├── validate.py            # validate_identity_headers / assert_trusted_source /
   │                          #   strip_untrusted_identity_headers / classify_inbound
   ├── inject.py              # build_outbound_headers(request, user_ctx, target_system,
   │                          #   role_map=None) —— 全 proxy 唯一出站装配点
   └── role_map.py            # OB-12 互译表读写 + 语义档校验（§6，T6）
   ```
   说明：选 `modules/` 下纯库包（非业务模块，不随 enable_module 装配；等价可选 `core/protocol_headers/`，两处均不产生路由）。对外引用：各子系统仓以「文档 + 常量/校验参考实现」为移植基线（拷贝/私有打包均按本仓发布 commit 打 tag 对应），白名单配置取本包 `constants.py` 导出值；本仓保证 `python -m ruff/pytest` 覆盖。
3. **单测 + 双通道等价用例前置**：包内函数单测（`tests/test_protocol_headers_*.py`）+ 出站矩阵测试（`tests/test_proxy_outbound_matrix.py`）+ 双通道用例（A/B 对同一对象一致、跨域 403/404，K09 引用）。

**OpenBase 侧试点（同属 T3）**：`get_current_tenant`（auth.py L244-246）入站 X-Tenant-Id 优先级收口；`get_identity_context`（L282-285）入站头来源校验；门禁项「非白名单带头 403」。

---

## 4. K07 端点-过滤矩阵模板 v1.0 设计

### 4.1 模板表结构（字段定义）

模板 = 一张主表（端点行）+ 填报说明 + 核对脚本骨架。主表列定义如下（与用户指定列对齐，并入最小集 R-M2-1 端点类别维度）：

| 列 | 取值/格式 | 填报说明 |
|----|-----------|---------|
| 系统 | OpenMemory/OpenRAG/OpenLLM/DPS | 填报子系统 |
| 端点 | OpenAPI path（如 `/api/v1/collections/{id}`） | 以子系统导出的 openapi.json 为自动核对底单 |
| 方法 | GET/POST/PUT/PATCH/DELETE | 同路由多方法逐行登记 |
| 端点类别 | CRUD / 列表分页 / 搜索 / 统计聚合 / 导出 / 回调异步读 / 批量 / 健康管理 | R-M2-1 八类；健康/管理面单独标注「A 直连」 |
| 身份头需求 | 每行四列子字段：`X-User-ID`（必需/可选/忽略）、`X-Tenant-ID`（必需/可选/忽略）、`X-User-Role`（必需/可选/忽略）、`X-Proxy-Source`（必需/可选/忽略） | 声明该端点执行域/属主/角色过滤所依赖的身份头 |
| 归属过滤需求 | 三态子字段：域过滤（tenant_code，恒有）/ 属主过滤（owner，按数据语义）/ 白名单来源豁免 | 每端点标注实际过滤实现（中间件/ORM 骨架/手工 SQL） |
| 租户键 | tenant_code 取值源（头 X-Tenant-ID / JWT claim / 本地行归属列） | 供隔离测试基座断言「返回集不含他域行」 |
| 豁免审批 | 豁免登记位：`豁免?（是/否）`、`豁免 ticket`、`审批人`、`到期/复核` | 任何跳过过滤的端点必须显式豁免审批 + 审计留痕（R-H3-3） |
| 状态 | 覆盖（有过滤+有用例）/ 缺口（有过滤无用例）/ 未覆盖（无过滤）/ 豁免 | S7 终验以「缺口清零、未覆盖清零」为目标 |
| 隔离测试注册位 | 关联测试 id / 用例（跨域不可见/跨域写拒绝） | 新增端点默认配套（R-M2-2） |

### 4.2 填报说明（简则）

1. 每子系统以 openapi 导出的端点清单为底单，**逐端点**登记上表；工具生成骨架表后人工只填「身份头需求/归属过滤/豁免」三块。
2. 归属过滤描述必须指向代码事实（中间件类名、repository/DAO 基类、SQL 位置），不接受泛述。
3. 豁免行必须挂 ticket + 审批人 + 复核日期；无 ticket 的「无过滤」行一律记「未覆盖」并在 S7 前清零。
4. 每轮联调 403/越权缺陷，回填为对应端点行的「缺口」证据并补隔离用例（复盘 P1-1 画像 403 类问题闭环）。

### 4.3 S2-S5 填报流程与 S7 终验规则

| 段 | 动作 |
|----|------|
| S1b（本立项） | 发布模板文档 + 模板表（xlsx/md 双形态）+ `scripts/k07_endpoint_matrix.py` 核对脚本骨架（读 openapi.json → 生成端点骨架行）；登记 S2-S5 填报跟踪表 |
| S2/S3/S5 | OpenMemory/OpenRAG/DPS 段随 K02 落地填报本系统矩阵，L3-2 贯通冒烟引矩阵隔离用例 |
| S4 | OpenLLM 段填报；通道矩阵（L2-2）与端点矩阵的「A 直连」行对账 |
| S7 | RA-06 终验：矩阵缺口清零、未覆盖清零；豁免全部在有效期且有审批；新增端点无隔离用例不放行 |

---

## 5. K03 禁旁路与信任链裁定落地设计

### 5.1 V-1~V-5 裁定定案（建议表 → 设计决策）

> 立项 §3.2 给出「裁定建议」，本节转**设计决策（D-V1~D-V5）**并落到代码分支（T2 实现）。逐条给 fail-open/fail-closed 与触发代码路径。

| # | 场景 | 立项建议 | **设计决策（定案）** | 实现落点（改造分支） |
|---|------|---------|---------------------|---------------------|
| D-V1 | 本地数字主体 JWT + DB 读不可达 | 维持 fail-open 过渡 | **定案：fail-open + WARN 计数 + 禁委托**（与 U1 login 内存降级一致；数据面域过滤由 JWT claims 自带承担）。DB 恢复即恢复强校验；审计 WARN 指标 `principal.verify.db_degraded` 计数进 verify-env 报告 | `verification.py L197-208` 分支：仅当**无 on_behalf_of** 时返回 None（放行）；携带委托 → 走 D-V3 fail-closed |
| D-V2 | 本地数字主体行缺失（无 purge 墓碑） | 维持 fail-open + 收紧 | **定案：fail-open（无委托）+ 委托禁止**。行缺失 + 无墓碑 + 无委托 → WARN 放行（OIDC 直签/降级内存用户过渡语义不变）；**行缺失 + 携带 on_behalf_of → 403 `PERM_DELEGATION_VERIFY_UNAVAILABLE`**（委托目标存在性不可证即拒）；purge 墓碑命中 401（L215-220）不回退 | `verification.py L210-225`：snapshot=None 且 payload 含 on_behalf_of → 抛 403；否则维持 WARN 放行 |
| D-V3 | 委托请求（on_behalf_of）+ DB 不可达 | fail-closed（403） | **定案：fail-closed，403 `PERM_DELEGATION_VERIFY_UNAVAILABLE`**。无法证明委托不变式即拒绝（与 P2-2 D1/D2 授权面异常不静默放行同构）。普通请求不受影响（D-V1 维持放行） | `verification.py L197-208` 改造：`delegated_claim_from_payload` 检测委托；DB 异常 + 委托 → 403；异常告警含 request_id；进程主体验证缓存命中但委托目标需 DB 复核（delegation.py L289-319）时同规则 |
| D-V4 | 状态/版本缓存（Redis）不可达 | 维持：直读 DB | **定案：缓存仅是加速，非信任源；信任判定一律以 DB 为准**。缓存不可达 = 未命中直读 DB（现状已具备 `redis_client.py` 静默降级 + verification `_cache_get_snapshot` 兜底）；不叠加两级降级（缓存不可达不得改为放行） | 维持现状；T2 断言「Redis 停 → verify 仍按 DB 判定」（D-V4 用例） |
| D-V5 | 非白名单来源携带身份头（下游子系统侧 + OpenBase 试点） | 403（规范发布 + OpenBase 试点） | **定案：403 `PERM_UNTRUSTED_IDENTITY_HEADER`**。OpenBase 侧试点（T3 门禁）与规范发布；S2-S5 按 §3.4 行为矩阵自行落地（B-1 边界） | 入口中间件/试点依赖层（§3.4/§5.4） |

### 5.2 服务调用与 Agent 请求裁定（补齐 V-1~V-5 之外的场景）

| # | 场景 | 裁定 | 说明 |
|---|------|------|------|
| D-V6 | `ob_k_*` 服务 Key 经 `/proxy` 或代理族出站（服务调用） | **读放行 + 显式服务账号标注；业务写 fail-closed 收口（过渡白名单内写除外）** | 服务 Key 鉴权语义保留（B-9）；出站不再匿名：`get_proxy_identity` 返回后由 builder 以「服务账号上下文」（name+scope 映射）补头。未在 K03 白名单登记的**写**路径 → 403 `PERM_SERVICE_KEY_WRITE_DENIED`；迁移指引：换 sk-agent-* 服务账号 |
| D-V7 | `sk-agent-*`（Agent 请求）+ DB 不可达 | **fail-closed（401）** | agent 密钥校验依赖 DB（`resolve_agent_principal` 按 key_hash 查库），DB 不可达无法证明密钥有效 → 拒绝，不降级放行（与 D-V1 的 JWT 场景刻意不同） |
| D-V8 | Agent 经任一 proxy 出站（业务面） | 禁匿名直连；出站带主体域身份头 + X-Proxy-Source + X-Agent-Id（§9.1） | Q2-S4/S6；本草案 T5 |
| D-V9 | 受信编排透传头 + OpenBase 自身认证冲突 | 编排透传头仅在与受信来源匹配时采纳；否则剥离/403（§3.4） | R-H1-1/2；试点 T3 |

**过渡豁免白名单清单机制（K03 收口载体）**：settings/config 登记 `k03_bypass_whitelist`（JSON 数组），每条：`{id, system, method, path_pattern, reason, owner, audit, expires_at}`。规则：仅在白名单内的旧匿名写调用可在过渡期放行，逐条审计（action=`proxy.bypass_write`，detail 含 id/reason），到期或 S7 前清零；白名单外匿名业务写一律拒绝。清单随 verify-env 雏形对账（§9.2）。

### 5.3 X-Proxy-Source 全链透传与校验规则

- 出站 `X-Proxy-Source` 恒为本出口代理来源标识（重写入站同名头），防「伪造 last-hop」；
- **透传语义**：入站如为受信来源携带 X-Proxy-Source/身份头 → 采纳为上游上下文，出站重写为本代理标识，**完整来源链记审计 `proxy_chain`**（如 `["openbase-orchestrator","openbase-rag-proxy"]`，§8.3）；非受信来源入站头一律不进入链；
- agent 嵌套链（A→B→…）每跳独立校验身份与委托上下文（R-M4-2），X-Agent-Id 记录当前执行 agent，链上各跳经 request_id 串联；
- 校验函数：`assert_trusted_source(source, trusted)` 供入口与共享包调用；`proxy_chain` 由 `record_proxy_hop` 写入审计（T8）。

### 5.4 入站头收口分段上线（OpenBase 侧试点）

| 阶段 | 开关（settings） | 行为 |
|------|-----------------|------|
| 过渡期（默认） | `strip_inbound_identity_headers=false`；`enforce_inbound_identity_headers=false` | 非受信来源带头 → 不采信 + 审计标注 `identity_headers_ignored` + WARN（零破坏） |
| 剥离期 | `strip_inbound_identity_headers=true` | 非受信来源四头/委托头物理剥除后继续自身认证 |
| 强校验期（S1b 门禁后） | `enforce_inbound_identity_headers=true` | 非受信来源带头 → 403 `PERM_UNTRUSTED_IDENTITY_HEADER`；`get_current_tenant`/`get_identity_context` 不再采信客户端自带头 |

出站对齐开关：`enforce_proxy_identity_headers`（严格模式：出站头与规范不符 → 502/审计，默认 false；常规补头始终开启，属幂等附加不构成 403 回归面）。两段式与回滚细则见 §11.2。

---

## 6. OB-12 角色互译配置设计

### 6.1 语义档锚（互译只映射粗粒度，细粒度不入互译——最小集 §6.3-3）

| 语义档 | 覆盖动作 | OpenBase 现役 code | DPS 角色（起步） | 说明 |
|--------|---------|-------------------|------------------|------|
| 管理档（manage） | 平台/租户级管理 | `admin` | `super_admin` | 起步映射（Q-D） |
| 读写/域管理档（readwrite） | 域内读写 + 域管理 | `org_admin` | `org_admin` | **editor 语义档对账落点：现役 code 无 `editor`，editor（读写/域管理）档由 `org_admin` 承担**（对账结论，Q-D 记录） |
| 只读档（readonly） | 只读 | `org_member`、`viewer` | `user` | 只读语义两码收敛到 DPS user |
| （未映射角色） | — | 未知/新 code | — | **fail-closed**：告警 + 拒绝或降级提示，不静默（§6.4） |

### 6.2 配置化互译表结构（role_map.py 数据模型）

互译表为双向映射 + 语义锚的三层 JSON（配置化、带版本、可校验），落点 settings `role_intertranslate: str = ""`（JSON，示范默认值内置；生产经 .env/配置覆盖）：

```jsonc
{
  "schema_version": 1,
  "reconciled_at": "2026-09-07",
  "anchors": {                       // 语义档定义（只读参考）
    "manage":    {"rank": 3},
    "readwrite": {"rank": 2},
    "readonly":  {"rank": 1}
  },
  "systems": {
    "dps": {
      "openbase_to_target": {        // 出站翻译：OpenBase code → 目标角色码
        "admin":      {"target": "super_admin", "anchor": "manage"},
        "org_admin":  {"target": "org_admin",   "anchor": "readwrite"},
        "org_member": {"target": "user",        "anchor": "readonly"},
        "viewer":     {"target": "user",        "anchor": "readonly"}
      },
      "target_to_openbase": {        // 回译（对账/审计展示用）
        "super_admin": {"source": ["admin"]},
        "org_admin":   {"source": ["org_admin"]},
        "user":        {"source": ["org_member", "viewer"]}
      }
    }
  }
}
```

结构要点：① 以语义档 rank 校验「翻译不得越档」（如 admin→user 属降档，允许；org_member→super_admin 越档 → 配置非法）；② 每行双向可逆；③ 缺省目标 `user` 语义对未知源 code 不兜底（fail-closed）。校验函数 `validate_role_map(map)`：JSON 合法、code 集合法（现役 code/目标侧枚举）、无重复源、无越档、双向逆一致。

### 6.3 出站翻译挂点与映射测试策略

- 挂点：`protocol_headers/inject.build_outbound_headers(..., target_system, role_map)`——目标系统配置了互译表时对 `X-User-Role` 做翻译（dps-proxy 起步）；无互译表系统（llm/rag/memory v1.0）原样透传 OpenBase role 码（由下游语义自行解释）。
- 映射测试策略（T6）：
  - 档位语义用例：各档角色经翻译后目标码断言（manage→super_admin 等）；
  - 回译逆断言：`target_to_openbase` 与 `openbase_to_target` 互逆一致；
  - 越档配置拒绝（校验函数单测）；
  - **无映射角色请求 fail-closed**：源 code 不在表 → 出站装配抛配置错误/403（不静默降 viewer）；
  - DPS 侧配合：真实 DPS 角色对账（R5 外部配合点）以联调用例双签。

### 6.4 Q-D 记录（待评审遗留）

| Q-D 项 | 本设计建议 | 状态 |
|--------|-----------|------|
| Q-D-1 起步范围 | **仅 OpenBase↔DPS 两档语义起步**（manage/readonly 最低可用；readwrite 经 org_admin 对账后纳入），其余系统接入时扩展 | 待评审 |
| Q-D-2 editor 语义档 | 现役 code 无 editor；editor（读写/域管理档）由 `org_admin` 承担，`editor` 码不入互译表（避免幽灵码） | 待评审 |
| Q-D-3 未映射 fail-closed 形态 | 拒绝（403）优先于降级提示（默认 viewer） | 待评审 |

---

## 7. OB-8 code 化收口设计

### 7.1 X-Org-ID 退役为别名（兼容读取 + 新写禁止，按方案口径收敛）

- **口径**（立项 §3.7/最小集 §4.2）：org 语义 = tenant 语义；`X-Org-ID` 仅为兼容别名，出站值恒 = `X-Tenant-ID`（tenant_code）或显式别名表命中值；**不落 org 语义新库行**（OpenBase 侧无 org 新写路径；业务写一律以 X-Tenant-ID 为隔离键）。
- 代码收敛：dps-proxy `_build_identity_headers` 的 org_raw 链（L124-129）删除「独立 org_id 取值」（user.org_id/jwt.org_id 中间态），收敛为 `tenant_raw` 同源别名；llm/memory 的 X-Org-ID 同规则（llm L118-119 取 org_id → 改取 tenant_code；memory L98/L105 缺省 `openbase-default` → 仅显式别名兜底，禁止硬编码默认链参与隔离键）。
- 兼容读取：下游（DPS/OpenMemory/OpenLLM）org 语义读取在过渡期保持兼容（org==tenant 同值），别名表驱动；X-Org-ID 头保留输出（值为别名）。
- 强模式（开关化）：`enforce_org_alias`（settings，默认 false）开启后，入站/出站 X-Org-ID ≠ X-Tenant-ID → 403 `BIZ_ORG_ALIAS_MISMATCH`（防双向混淆，复盘根因 4.3）。

### 7.2 dps org/tenant code→UUID 映射生产化基线

- 结构：settings `dps_org_map`/`dps_tenant_map`（L184-185）由「自由 JSON」升级为**登记式基线** `dps_code_map`（JSON，统一 org/tenant 两维）：
  ```jsonc
  {
    "schema_version": 1,
    "source_of_truth": "openbase.tenants.code",
    "last_reconciled_at": "2026-09-07",
    "entries": [
      {"tenant_code": "acme", "dps_org_id": "<dps-uuid>", "dps_tenant_id": "<dps-uuid>",
       "reconciled_at": "2026-09-07", "status": "verified"}
    ]
  }
  ```
- 校验（`validate_dps_code_map`）：JSON 合法、`tenant_code` 须命中 `tenants.code` 或显式别名表、dps 侧 org/tenant id 非空、无重复 code、双向映射一致（`_apply_map` 已有字典命中逻辑保持）；冲突检测（R-L3-1 形态）：同一 code 映射不同 DPS 值 → 对账报告冲突项，S7 前清零。
- 默认值策略：默认无条目（空表）；`dps_default_org_id/dps_default_tenant_id` 标记 deprecated，仅作为显式兜底保留并在 verify-env 中 WARN；新租户经迁移/对账工具（`scripts/audit_dps_code_map.py`，T7）登记入基线，禁止运行期隐式新增。
- 以 OpenBase `tenants.code` 为唯一事实源（R-L3-1/Q3 冲突检测形态：接入前跑重复 code 对账 SQL → 冲突清单 → 以 OpenBase 为准重映射 → 留痕）。

---

## 8. OB-13 审计贯穿设计（OpenBase 侧）

### 8.1 设计决策

| 决策 | 内容 |
|------|------|
| D-OB13-1 | **audit_logs 不新增列（v1.0）**：request_id 已是结构列（base.py:458）；principal/delegated/proxy_source/auth_method 走 `detail` JSON 统一 schema（规避写放大；立项 §7.1-7.5 风险 5 缓解）。U4/R3 如需结构化列再评估 |
| D-OB13-2 | request_id 生成/透传钩子放 AuditMiddleware（现状 L227/L243），出站经 X-Request-Id 透传（§3.5 矩阵）；委托/生命周期/服务账号/代理动作统一带 request_id |
| D-OB13-3 | 与 U4 联动边界：本立项只收 OpenBase 侧字段贯穿与 request_id 钩子；子系统侧字段落库随 S2-S5/U4（立项 §6 B-4） |

### 8.2 audit_logs.detail 身份 schema（`audit_identity` v1）

```jsonc
{
  "identity": {
    "principal":   {"subject_id": 7, "subject_type": "agent", "tenant_code": "acme", "role": "org_admin", "auth_method": "sk-agent"},
    "delegated":   {"subject_id": 88, "subject_type": "user", "tenant_code": "acme", "role": "viewer"} | null,
    "effective":   {"subject_id": 88, "subject_type": "user", "tenant_code": "acme", "role": "viewer"},
    "proxy_source": "openbase-llm-proxy",
    "proxy_chain": ["openbase-orchestrator", "openbase-llm-proxy"],
    "request_id":  "req-6b21dd08e933",
    "org_alias":   "acme"
  }
}
```

既有 `user_id/tenant_id/action/resource/resource_id/ip/user_agent/request_id` 列保持不变（向后兼容，立项 §7.4）；`user_id` 兼容位 = principal.subject_id（agent 亦以其 users.id 落列）。委托签发审计 `enqueue_delegation_audit`（delegation.py L401-408）现有 detail 两层并入本 schema（补 auth_method/effective/proxy_source）。

### 8.3 中间件链路与代理出站审计钩子

- **入站链路**：AuthMiddleware（`core/deps/auth.py`）认证后把 `identity_context`（principal/delegated/effective/auth_method/proxy_source/identity_headers_ignored 标注）写入 `request.state.identity`；AuditMiddleware（`modules/audit/__init__.py` L222-267）`_record` 时读 `request.state` 拼 §8.2 schema 进 APICallRecord.extra/detail；DB 审计写路径（lifecycle/delegation/purge）同 schema。
- **代理出站审计钩子**：`protocol_headers/inject.build_outbound_headers` 每次装配出站头时调用 `record_proxy_hop(action="proxy.outbound", system, method, path, request_id, identity, proxy_chain)`（写 audit_logs，同一 request_id），保证「OpenBase 侧审计 + 子系统侧审计」可经 request_id 串联（U4 前置钩子）。
- **agent 出站审计**：agent 动作带 agent_id（principal）+ source + 域 + 动作（Q2-S5/S6）；sk-agent 请求即使未命中代理族（直连端点）也由入站链路落审计。

---

## 9. OB-6 服务账号受信源收口与 OB-9 verify-env 雏形

### 9.1 OB-6 服务账号受信源收口（U1 已落密钥面，本设计补通道与审计）

| 子项 | 设计 |
|------|------|
| 受信来源通道白名单 | sk-agent-* 有效通道 = ① OpenBase 自身端点（认证经 `get_current_user` → `resolve_agent_principal`）；② 四 proxy 出站（装配主体域身份头 + X-Proxy-Source + X-Agent-Id）；③ 编排受信透传（白名单）。**禁匿名直连写子系统**（业务写必须走受信通道，D-V7/D-V8） |
| 二次解码路径识别（llm/memory） | 删除 `_extract_identity`/`_jwt_payload` 二次 JWT 解码，改读统一主体 dict；sk-agent 主体验证在 `get_current_user`（auth.py L177-180）已完成，出站 builder 直接消费其 `id/tenant_code/roles/status_state/auth_method=sk-agent`（agent_keys.py L152-164）——llm/memory/dps/rag 全链路识别 agent |
| memory 双层认证的 agent 形态 | D-OB6-3：user JWT 场景保持「X-API-Key + 透传原 JWT」；**agent 场景无原 JWT**，出站 = X-API-Key + 四头 + X-Proxy-Source + X-Agent-Id（不再构造伪 JWT）；OpenMemory 侧接受白名单来源身份头由 S2 段 K02(OM) 落地（B-1 边界）；S1b 内以契约桩断言出站头集合，不依赖上游 |
| agent 审计贯穿 | §8.3：agent 动作落 audit_logs（agent_id+source+域+动作 + request_id）；停用即全部 sk-agent key 失效联动（U1 已实现）回归断言（T5-6） |
| U1 密钥面回归 | sk-agent 发放/吊销/状态门禁用例不回退（T5-7） |

### 9.2 OB-9 verify-env 雏形设计（T9）

**契约清单（首个版本）** `scripts/verify-env/contract.json`：

```jsonc
{
  "schema_version": 1,
  "sections": {
    "config_single_source": ["trusted_proxy_sources", "role_intertranslate", "dps_code_map", "jwt_secret", "db_url", "redis_url"],
    "upstreams": [{"name": "dps", "url_key": "dps_upstream_base", "health": "/health"},
                  {"name": "openllm", "url_key": "llm_upstream_base", "health": "/openllm/v1/health"},
                  {"name": "openrag", "url_key": "rag_upstream_base", "health": "/api/v1/system/health"},
                  {"name": "openmemory", "url_key": "memory_upstream_base", "health": "/health"}],
    "whitelist_matrix": {"trusted_proxy_sources": ["openbase-dps-proxy", "openbase-llm-proxy", "openbase-rag-proxy", "openbase-memory-proxy", "openbase-generic-proxy"]},
    "mapping_reconcile": ["dps_code_map"],
    "db_checks": [{"schema": "openbase", "check": "tenants.code 唯一事实源对账"}]
  }
}
```

`scripts/verify-env.ps1`：启动编排 start 时比对（config 键存在性/seed 默认值 WARN/端口 URL 可达/白名单矩阵一致/映射对账/DB 连接与账号 schema 检查位，配合 OB-7 登记）→ **WARN + 报告**（fail-fast 语义随 R3 完整版收紧；S1b 门禁要求「可用」）；退出码区分 warn/error，支持 `--fail-fast`。审计与错误定位信息写入 `verify-env-report.json`（同目录输出）。

### 9.3 OB-7 / OB-10 标注（外移说明）

| 升级项 | 规划定位 | 本草案处置 |
|--------|---------|-----------|
| OB-7 存储账号分离 | 任务卡 K13；R2/U2；S7 终验 | **外移，不纳入 T1~T10**：仅 verify-env 契约含「连接账号/schema」检查位登记配合（§9.2 `db_checks`）；K13 本身在 R2/U2 + S7 |
| OB-10 前端壳 | UI-E2E P3；S6/R4 | **外移**：前端导航壳属 S6 前端段/FE-JT 工作，本草案不实施（仅登记牵头行，见 §11.1 台账） |

---

## 10. T1~T10 实现步骤与 TDD 断言清单（RED→GREEN，编号化）

> 执行纪律：沿用 U1 草案 §11 风格——每用例**先写测试（RED，断言先行）→ 实现（GREEN）**；断言编号 `T{n}-{m}` 全文档唯一，作为验收回溯锚点。新增文件落 `tests/test_protocol_headers_*.py`、`tests/test_proxy_outbound_matrix.py`、`tests/test_inbound_header_gate.py`、`tests/test_verdict_k03.py`、`tests/test_role_intertranslate.py`、`tests/test_org_alias_code.py`、`tests/test_audit_identity_chain.py`、`tests/test_service_agent_outbound.py`、`tests/test_verify_env.py` 等（沿用现仓 `tests/test_*` 命名）。实现遵循 AGENTS.md（分层/错误码/结构化日志/参数化查询/幂等迁移）；`python -m ruff check openbase tests` 0 错误、覆盖率 ≥90%。
>
> 依赖顺序总览（立项 §4）：T1(K01) → T2(K03) → T3(K02) → T4(K07)；T5/T6/T7/T9 在 T1 定案后并行；T8 依赖 T1/T5；T10 贯穿收口。

### T1 四头/委托头唯一签发与出站对齐（K01/OB-3）

实现步骤：① 建 `protocol_headers` 共享包（constants/inject/validate）；② dps/llm/rag/memory/通用 proxy 出站装配改统一 builder（删三处二次解码）；③ 来源标识常量收口；④ 委托出站头唯一签发固化（X-Agent-Id 补 principal）；⑤ 入站非受信头标注钩子（配合 T3 试点）。

| # | RED 断言（摘录） | 覆盖立项 §5 验收 |
|---|-----------------|-----------------|
| T1-1 | **出站矩阵绿**：构造统一主体上下文（user/agent/委托三类），逐一断言 dps/llm/rag/memory/通用 proxy 出站头 = §3.5 目标矩阵（四头+来源+X-Request-Id；委托加 X-Agent-Id） | T1 全 proxy 出站头一致矩阵测试绿 |
| T1-2 | 客户端伪造头注入用例：请求带 X-User-ID=999/X-Tenant-ID=evil 经 proxy → 出站头仍取签发上下文值（剥离/不采信） | T1 出站头仅来自签发上下文 |
| T1-3 | sk-agent 主体经 llm/memory proxy 出站不再 401（二次解码路径删除）：出站头 X-User-ID=agent users.id、X-Proxy-Source=对应代理常量 | T5 服务账号出站头齐全（前置） |
| T1-4 | 委托出站：X-User-ID=delegated.subject_id、X-Tenant-ID/X-Org-ID=委托 tenant_code、X-User-Role=delegated.role、X-Agent-Id=principal agent id | T1 委托出站头唯一签发 |
| T1-5 | `llm_proxy` 来源标识改读共享常量后值仍为 `openbase-llm-proxy`（下游白名单零迁移） | T1 来源标识单一写法 |
| T1-6 | **静态扫描 0 处第二写法**：`PROXY_SOURCE_*`/`TRUSTED_PROXY_SOURCES` 仅存在于 `protocol_headers/constants.py`（对全仓 `openbase/` 断言唯一 import 源） | T1 TRUSTED_PROXY_SOURCES 全仓一种取值 |
| T1-7 | X-Proxy-Source 全链透传用例绿（受信编排→OpenBase→rag-proxy：出站来源重写为 rag 常量 + 审计 proxy_chain=[编排,rag]） | T1 X-Proxy-Source 全链透传 |
| T1-8 | rag-proxy 出站现补四头（原零身份头）；llm 补 X-Tenant-ID/X-User-Role；memory 补 X-User-Role/X-Proxy-Source；dps 补 X-Proxy-Source——逐 proxy 缺失头断言补齐 | T1 矩阵 |
| T1-9 | 无身份可解析（匿名/健康）→ 出站不注入伪身份头（健康/管理面 A 直连例外登记） | T1 语义一致性 |
| T1-10 | 通用 `/proxy` 通道出站注入身份头（JWT 与 ob_k_ 双通道均断言） | T1（G-P3 收口） |
| T1-11 | 委托头唯一签发规范文档化（§3.6 正文存在 + `issue_delegated_token_pair` 为唯一签发出口断言：静态扫描无第二处 on_behalf_of 装配） | T1 委托唯一签发规范文档化 |
| T1-12 | U1 既有测试回归绿（`test_identity_t*.py`/`test_dps_proxy`/`test_llm_proxy` 等）——出站改造不破坏值语义 | T10 存量回归 |

### T2 禁旁路 + fail-open 裁定落地（K03/OB-3）

实现步骤：① V-1~V-5 分支编码（§5.1）；② 旁路盘点脚本 + 白名单清单机制；③ WARN 指标；④ D-V6~D-V9 收口。

| # | RED 断言 | 覆盖立项 §5 验收 |
|---|---------|-----------------|
| T2-1 | **V-1**：DB 不可达 + 无委托 JWT → 放行 + WARN（`principal.verify.db_degraded` 计数 +1）；DB 恢复后下一请求恢复强校验 | T2 V-1 放行+WARN 计数 |
| T2-2 | **V-2**：行缺失无墓碑 + 无委托 → 放行 WARN；**行缺失 + on_behalf_of → 403 `PERM_DELEGATION_VERIFY_UNAVAILABLE`** | T2 V-2 放行+收紧 |
| T2-3 | **V-3**：委托请求 + DB 不可达 → 403（fail-closed）；普通请求不受影响（对照 V-1 放行） | T2 V-3 委托+DB 故障 403 |
| T2-4 | **V-4**：Redis 停 → verify 直读 DB 判定（suspend 主体仍 401） | T2 V-4 缓存不可达直读 DB |
| T2-5 | **V-5（OpenBase 试点前置）**：非白名单来源带头 → `enforce_inbound_identity_headers=true` 时 403 `PERM_UNTRUSTED_IDENTITY_HEADER` | T3 非白名单带头 403（T2 白名单就绪） |
| T2-6 | **D-V6**：未登记 ob_k_ 写路径 → 403 `PERM_SERVICE_KEY_WRITE_DENIED`；白名单（`k03_bypass_whitelist`）内写放行且逐条审计 | T2 业务面无未审计直连写 |
| T2-7 | **D-V7**：sk-agent + DB 不可达 → 401（fail-closed） | T5 agent 匿名直连拒绝（配合） |
| T2-8 | 旁路扫描报告输出 0 高危未登记项（扫描脚本对仓内写端点 + `/proxy` 调用点核对白名单） | T2 扫描报告 0 高危项 |
| T2-9 | WARN 指标可查询（verify-env 报告含 db_degraded/行缺失计数） | T2 审计 WARN 指标 |
| T2-10 | 白名单清单校验：过期条目 → verify-env WARN；审计 action=`proxy.bypass_write` 落 audit_logs | T2 收口留痕 |

### T3 协议头规范 v1.0 发布物 + OpenBase 试点（K02/SYS-1）

实现步骤：① 规范文档裁出（§3）；② 常量/校验函数包落位；③ OpenBase 试点（get_current_tenant 收口、get_identity_context 来源校验、非白名单带头 403 开关）；④ settings 键登记（trusted_proxy_sources/strip_inbound_identity_headers/enforce_inbound_identity_headers/enforce_proxy_identity_headers）。

| # | RED 断言 | 覆盖立项 §5 验收 |
|---|---------|-----------------|
| T3-1 | 发布物齐备断言：`docs/protocol-headers-v1.0.0.md`（或等价落点）存在、`protocol_headers/` 五模块存在、`constants.py` 值 = 规范表 §3.3 | T3 协议头规范 v1.0 发布物齐备 |
| T3-2 | `validate_identity_headers` 对非法格式（超长/非法字符/类型错）→ 400 `PARAM_HEADER_FORMAT_INVALID`；合法头 → 通过 | T3 共享校验函数参考单测 |
| T3-3 | `assert_trusted_source`：白名单值通过；非白名单 → False | T3 校验函数 |
| T3-4 | `classify_inbound`：白名单+带头=trusted / 白名单+无头=self_auth / 非白名单+带头=403 / 非白名单+无头=self_auth（行为矩阵 M1 断言） | K02 行为矩阵 |
| T3-5 | `get_current_tenant`：客户端自带头 + JWT → **头不再无校验覆盖 JWT**（受信来源头仍优先） | T3 试点 get_current_tenant 收口 |
| T3-6 | `get_identity_context`：非受信来源带头 → 上下文忽略该头 + 审计 `identity_headers_ignored` | T3 试点 get_identity_context 校验 |
| T3-7 | 非白名单带头 403（enforce 开）用例绿；剥离开（strip 开、enforce 关）仅剥除不 403 | T3/S1b 门禁 非白名单带头 403 |
| T3-8 | 双通道等价用例前置：A/B 通道同一对象返回一致、跨域 403/404（契约桩/联调占位） | K09/§12.1 验收要点引用 |
| T3-9 | 规范评审记录归档（评审人/结论/遗留）——S1b 门禁项 | T3 规范评审通过 |

### T4 端点-过滤矩阵模板 v1.0（K07/SYS-1）

实现步骤：① 模板文档+表（§4.1）；② openapi 核对脚本骨架；③ 填报跟踪表登记。

| # | RED 断言 | 覆盖立项 §5 验收 |
|---|---------|-----------------|
| T4-1 | 模板主表列齐全（§4.1 十列 + 端点类别枚举） | T4 模板齐备 |
| T4-2 | 核对脚本骨架：输入示例 openapi.json → 输出端点骨架行（端点/方法/类别三列自动填充） | T4 核对脚本骨架 |
| T4-3 | 填报说明文档存在且含 S2-S5 填报与 S7 终验规则 | T4 填报流程齐备 |
| T4-4 | S2-S5 填报跟踪表登记完成（四系统行 + 责任段） | T4 跟踪表登记 |
| T4-5 | 模板评审记录归档——S1b 门禁项 | T4 模板评审通过 |

### T5 OB-6 服务账号受信源收口（Q2-S6/L3-1 前置）

实现步骤：① 四 proxy 出站统一读 agent 主体 dict；② agent 出站审计；③ 禁匿名直连断言；④ U1 密钥面回归。

| # | RED 断言 | 覆盖立项 §5 验收 |
|---|---------|-----------------|
| T5-1 | sk-agent 经 dps-proxy 出站：四头 + X-Proxy-Source=`openbase-dps-proxy` + X-Agent-Id=agent id | T5 服务账号受信源用例全绿 |
| T5-2 | sk-agent 经 rag-proxy 出站：四头齐全且域正确（原零身份头现已注入） | 同上 |
| T5-3 | sk-agent 经 memory-proxy 出站不再 401，出站头集合=契约（X-API-Key+四头+来源+X-Agent-Id；无伪 JWT） | 同上（D-OB6-3） |
| T5-4 | sk-agent 经 llm-proxy 出站：X-User-ID/X-Tenant-ID/X-User-Role/来源齐全 | 同上 |
| T5-5 | **agent 匿名直连写子系统 → 拒绝（0 可达）**：未走受信通道的 sk-agent 直连写路径（若有）被 K03 白名单外拒绝 | T5 agent 匿名直连写拒绝 |
| T5-6 | agent 出站审计落库：detail.identity.principal.subject_type=agent + agent_id + proxy_source + tenant_code + action | T5 agent 出站审计含 agent_id+source+域 |
| T5-7 | U1 agent 密钥面回归全绿：sk-agent 发放/轮换/吊销/停用联动（`test_identity_t1` 等）不回退 | T5 U1 密钥面回归 |

### T6 OB-12 角色互译配置（最小集 §6.3，Q-D）

| # | RED 断言 | 覆盖立项 §5 验收 |
|---|---------|-----------------|
| T6-1 | `validate_role_map` 对合法起步表通过；越档（org_member→super_admin）、重复源、双向不一致 → 非法 | T6 映射配置校验 |
| T6-2 | 档位语义映射：dps 出站 admin→super_admin、org_admin→org_admin、org_member/viewer→user（出站 X-User-Role 断言） | T6 映射测试绿 |
| T6-3 | 回译逆一致：`target_to_openbase` 与 `openbase_to_target` 互逆 | T6 映射测试 |
| T6-4 | **无映射角色 fail-closed**：未知源 code → 出站装配抛错/403，不静默降 viewer | T6 无映射角色 fail-closed |
| T6-5 | 语义档 rank 校验（降档允许/升档拒绝） | T6 映射测试 |
| T6-6 | Q-D 评审结论记录（Q-D-1~Q-D-3 状态回写） | T6 Q-D 评审结论记录 |

### T7 OB-8 code 化收口（P1-2/P1-3）

| # | RED 断言 | 覆盖立项 §5 验收 |
|---|---------|-----------------|
| T7-1 | dps-proxy 出站 X-Org-ID == X-Tenant-ID（org_raw 独立链删除后别名断言） | T7 X-Org-ID 别名收敛 |
| T7-2 | llm/memory 出站 X-Org-ID 同源别名（不再取独立 org_id 中间态） | 同上 |
| T7-3 | `enforce_org_alias=true` 时 X-Org-ID ≠ X-Tenant-ID → 403 `BIZ_ORG_ALIAS_MISMATCH` | T7 别名强模式 |
| T7-4 | `validate_dps_code_map`：条目命中 tenants.code、dps 侧非空、无重复、双向一致 | T7 映射基线校验 |
| T7-5 | 冲突检测：同 code 双映射 → 对账报告冲突项（0 未决为门禁） | T7 dps code→UUID 对账报告 |
| T7-6 | `dps_default_org_id/tenant_id` 标记 deprecated：verify-env WARN 提示 | T7 默认值策略 |
| T7-7 | 对账报告输出且 0 未决冲突（`scripts/audit_dps_code_map.py`） | T7 对账报告 0 未决 |

### T8 OB-13 审计贯穿（OpenBase 侧）

| # | RED 断言 | 覆盖立项 §5 验收 |
|---|---------|-----------------|
| T8-1 | audit_logs.detail.identity schema 完整（principal/delegated/effective/proxy_source/proxy_chain/request_id） | T8 审计字段贯穿断言 |
| T8-2 | 委托请求代理出站审计：detail 两层 + X-Agent-Id principal 一致（抽样比对） | T8 抽样比对一致 |
| T8-3 | 代理出站审计钩子用例绿：`record_proxy_hop` 落库 action=`proxy.outbound` 且 request_id 与入站一致 | T8 proxy 出站审计钩子 |
| T8-4 | sk-agent 直连端点审计含 agent_id+source+域+动作（§8.3） | T8 agent 贯穿 |
| T8-5 | 中间件链路：AuthMiddleware 写 request.state.identity → AuditMiddleware 记录（fake 请求断言 extra/detail） | T8 中间件链路 |
| T8-6 | 既有字段不回退：user_id/tenant_id/request_id 列与委托签发审计 schema 兼容（`test_identity_t4`/lifecycle 回归） | T8 兼容 + U4 边界 |
| T8-7 | U4 联动边界文档化（§8.1 D-OB13-3 引用文件存在） | T8 U4 边界文档 |

### T9 OB-9 verify-env 雏形

| # | RED 断言 | 覆盖立项 §5 验收 |
|---|---------|-----------------|
| T9-1 | `scripts/verify-env/contract.json` 存在且 schema 校验通过 | T9 契约清单首个版本 |
| T9-2 | `scripts/verify-env.ps1` 可执行：缺键/端口不可达/白名单不一致 → WARN + 退出码区分；`--fail-fast` 置错即失败 | T9 自检脚本可用 |
| T9-3 | 白名单矩阵对账：trusted_proxy_sources 与 contract 不一致 → 报告可定位 | T9 白名单矩阵比对 |
| T9-4 | 映射对账：dps_code_map 条目与 tenants.code 抽样对账（含冲突项输出） | T9 映射/code 对账 |
| T9-5 | DB 检查位：连接 + schema（openbase）可探（配合 OB-7 登记） | T9 连接账号/schema 检查位 |
| T9-6 | 报告输出 `verify-env-report.json` 且含 WARN/ERROR 清单 | T9 故障可定位 |

### T10 回归与 S1b 段门禁收口

| # | 断言 | 覆盖立项 §5 验收 |
|---|------|-----------------|
| T10-1 | `python -m pytest tests` 全绿 | T10 |
| T10-2 | `python -m ruff check openbase tests` 0 错误 | T10 |
| T10-3 | 覆盖率 ≥90%（`python -m pytest --cov=openbase`） | T10 |
| T10-4 | 存量 proxy/服务 Key/调用方回归绿（`test_proxy_auth`/`test_dps_proxy`/`test_llm_proxy`/`test_rag_proxy`/`test_memory_proxy`/`test_api_keys*` 等） | T10 + §7 兼容 |
| T10-5 | **S1b 段门禁全绿自检**：协议头规范 v1.0 发布 + 非白名单带头 403（OpenBase 侧）+ 服务账号发放/吊销用例全绿 + verify-env 雏形可用 + 端点矩阵模板评审通过 | T10/S1b 门禁 |
| T10-6 | 台账回写（任务卡 K01/K03 已立项、K02 规范已发布、K07 模板已发布；OB-3/6/8/9/12/13 状态） | T10 台账回写 |

---

## 11. 落点清单、迁移/兼容、风险与里程碑

### 11.1 落点清单（新增/变更代码盘点，行号以 HEAD=914f00b 为准）

**变更（既有文件改造）**：

| 文件 | 行号（现状） | 变更内容 | 对应任务 |
|------|-------------|---------|---------|
| `openbase/modules/dps_proxy/__init__.py` | `_jwt_payload` L60-71、`_build_identity_headers` L90-135 | 删除二次解码；出站改 `protocol_headers.inject.build_outbound_headers`；X-Org-ID 别名化（删 org_raw 独立链 L124-129）；补 X-Proxy-Source/X-Request-Id；X-User-Role 经互译表 | T1/T6/T7 |
| `openbase/modules/llm_proxy/__init__.py` | `PROXY_SOURCE_IDENTIFIER` L41、`_extract_identity` L62-93、`_build_upstream_headers` L96-120 | 常量改读共享包（值不变）；删除二次解码；补 X-Tenant-ID/X-User-Role；X-Org-ID 别名 | T1/T7 |
| `openbase/modules/rag_proxy/__init__.py` | `_build_upstream_headers` L82-96 | 补四头 + X-Proxy-Source/X-Request-Id（保留 X-API-Key） | T1 |
| `openbase/modules/proxy/memory_proxy.py` | `_extract_identity` L50-84、`_build_upstream_headers` L87-108 | 删除二次解码（agent 识别）；补 X-User-Role/X-Proxy-Source；agent 场景不透传伪 JWT（D-OB6-3） | T1/T5 |
| `openbase/modules/proxy/__init__.py` | L67-120（headers L84-87） | 通用 proxy 出站注入身份头/来源/X-Request-Id（JWT+ob_k_ 双通道） | T1/T2 |
| `openbase/core/deps/auth.py` | PUBLIC_PREFIXES L57-73、dispatch L75-108、get_current_user L156-233、get_current_tenant L236-255、get_identity_context L277-313、require_api_key L318-367、get_proxy_identity L370-387 | 试点：入站身份头来源校验/剥除/403（开关化）；request.state.identity 写入；get_current_tenant 优先级收口；get_identity_context 来源校验 | T3/T5/T8 |
| `openbase/modules/identity/verification.py` | L167-249 | V-1/V-2/V-3 分支改造（DB 不可达/行缺失 + on_behalf_of → 403）；WARN 计数 | T2 |
| `openbase/modules/identity/delegation.py` | L22-23（R2 边界注释）、L378-428 | 审计 schema 并入 §8.2（补 effective/proxy_source/auth_method）；R2 边界注释收口 | T8 |
| `openbase/modules/audit/__init__.py` | APICallRecord L31-50、build_audit_record L53-98、dispatch L222-244、_record L246-267 | extra/detail 拼 §8.2 identity schema；X-Request-Id 出站透传钩子 | T8 |
| `openbase/settings.py` | dps 映射 L181-185 等 | 新增：trusted_proxy_sources/strip_inbound_identity_headers/enforce_inbound_identity_headers/enforce_proxy_identity_headers/enforce_org_alias/role_intertranslate/dps_code_map/k03_bypass_whitelist；`dps_default_*` 标记 deprecated | T1/T3/T6/T7/T2 |
| `openbase/core/errors/codes.py` | — | 新增 §3.8 五个错误码 | T2/T3/T7 |
| `openbase/core/models/base.py` | AuditLog L445-462 | 无 DDL（D-OB13-1）；如需 U4 结构化列留注 | T8 |

**新增**：

| 文件 | 内容 | 对应任务 |
|------|------|---------|
| `openbase/modules/protocol_headers/{__init__,constants,identity_context,validate,inject,role_map}.py` | 共享常量/校验/注入/互译表（§3.9） | T1/T3/T6 |
| `scripts/k07_endpoint_matrix.py`、`scripts/audit_dps_code_map.py`、`scripts/bypass_scan.py`、`scripts/verify-env/contract.json`、`scripts/verify-env.ps1` | K07 核对脚本、映射对账、旁路扫描、verify-env 雏形 | T4/T7/T2/T9 |
| 规范文档（由 §3 裁出，落 `doc/` 或根目录随 K02 发布） | 协议头规范 v1.0 | T3 |
| 测试文件（§10 列示 `tests/test_protocol_headers_*.py` 等） | TDD 断言载体 | T1-T10 |

**台账登记（回写引用）**：任务卡 K01/K03（已立项，P2-1）、K02 规范 v1.0（已发布，S1b）、K07 模板（已发布，S1b）；升级项 OB-3/6/8/9/12/13（本 S1b）、OB-7/OB-10（外移，见 §9.3）。

### 11.2 迁移与兼容（立项 §7 落代码面）

- **两段式**：先「加头/对齐（下游无白名单强校验时不改变放行）→ 后「强校验/剥离」（S1b 门禁后开 `enforce_inbound_identity_headers`/`strip_inbound_identity_headers`）」。新增头对未启用白名单的下游为幂等附加；`X-Proxy-Source` 在 S2-S5 K02 上线前仅进审计不改变行为。
- **开关矩阵（settings，全部可回滚）**：`enforce_proxy_identity_headers`（出站严格，默认 false）、`strip_inbound_identity_headers`（入站剥离，默认 false）、`enforce_inbound_identity_headers`（非受信带头 403，S1b 门禁开启）、`enforce_org_alias`（org 别名强模式，默认 false）。
- **ob_k_ 服务 Key**：鉴权语义与 `/proxy` 行为不回改（兼容存量脚本）；匿名直穿列入 K03 白名单过渡（D-V6）；迁移指引 = 换 sk-agent-* 服务账号 + 出站身份头。
- **sk-agent_***：识别能力补足非破坏（dps 已有、llm/memory 本次补）；agent 出站头注入后下游按白名单来源放行行为一致。
- **存量调用方（前端/脚本）**：曾依赖客户端自带头被采信的调用，在入站收口后不再作为事实源；影响面按端点清单化并在发布说明标注（过渡期先审计告警、门禁后强校验）。
- **X-Org-ID/映射**：org 头输出保留（值=别名）；dps_org_map/tenant_map 兼容读取（旧 JSON 解析兼容升级到登记式基线，见 §7.2 迁移提示）。
- **双通道**：A/B 头语义不变式一致（Q-4）；S4 前规范冻结、变更走评审（立项 R2）。

### 11.3 风险与缓解（承接立项 §8.2，落到代码面）

| # | 风险 | 缓解 |
|---|------|------|
| 1 | 出站头增补/org 收敛被下游或存量调用方误判 | 两段式 + 开关回滚；值语义不变声明（§3.5）；与 S2-S5 K02 时间窗对齐（规范先发、代码对齐与下游落地同批串行） |
| 2 | V-3 委托 DB 故障 fail-closed 误拒正常委托 | fail-closed 仅限委托分支（普通请求 V-1 放行）；告警含 request_id；与 dps-proxy 探活/编排 DB_FAIL_FAST 双保险协同 |
| 3 | 入站头收口影响审计/上下文既有消费 | get_current_tenant 收口与 get_identity_context 校验分开两段上线；先剥除审计告警、后强校验；端点清单化回归 |
| 4 | memory 双层认证 agent 场景依赖 S2 上游 | S1b 内以契约桩断言出站头（不依赖上游）；L3-1/S7 端到端依赖 S2 K02(OM) 完成（边界 B-1/B-3） |
| 5 | 审计 detail 写放大 | 结构化身份字段精简约 200B/条；批量/回调端点降频配置化；采样策略登记 |
| 6 | verify-env 误报阻断启动 | 雏形 WARN+报告；fail-fast 语义随 R3 完整版收紧（S1b 门禁只要求可用） |
| 7 | 角色互译误映射致越权/403 | 档位 rank 校验；起步仅 DPS 两~三档；映射测试绿 + 无映射 fail-closed；联调用例双签 |
| 8 | V-1/V-2 fail-open 窗口内吊销不及时 | 与 U1 tvn/状态门禁共存（DB 可用时即时）；fail-open 仅限无法确认的故障窗口；WARN 计数进 verify-env |

### 11.4 里程碑（五步流程衔接，立项 §9）

| 步骤 | 输入 | 活动与产出 | 门禁 |
|------|------|-----------|------|
| ① 需求 | P2-1 立项方案（914f00b，[Approved]） | V-1~V-5 裁定确认、范围对齐 | 人工批准（已完成） |
| ② 设计 | 批准的需求 | **本草案**（v1.0.0 [Draft]）→ 评审（协议头规范 v1.0 正文/共享包/裁定分支/V-1~V-5/互译表 Q-D/K07 模板/落点清单/verify-env 清单） | 与立项方案 T1~T10 比对无遗漏（§1.4 矩阵）；人工批准进入开发 |
| ③ 开发 | 批准的设计 | TDD（RED→GREEN）按 T1→T10（依赖序见 §10）；`ruff` 0 错误；追溯矩阵 | 实现与设计一致；人工批准进入测试 |
| ④ 测试 | 开发成果 | 单测/集成/矩阵测试（出站一致性/白名单 403/裁定 V-1~V-5/互译映射/审计贯穿/verify-env 用例）；`pytest` 全绿、覆盖率 ≥90%；存量回归（§11.2） | 测试回溯覆盖立项 §5 全部验收（§10 每断言列「覆盖验收」）；人工批准进入部署 |
| ⑤ 部署 | 测试通过 | 两段式发布（先加头/后强校验）；开关配置公示；存量调用方影响清单；台账回写 | **S1b 段门禁全绿**：协议头规范 v1.0 发布 + 非白名单带头 403（OpenBase 侧）+ 服务账号受信源用例全绿 + verify-env 雏形可用 + 端点矩阵模板评审通过 → 进入 S2 |

**里程碑引用**：本设计属 R1 批次 + S1b 段；完成即 S1b 收官；随后 S2（OpenMemory）按规范 v1.0 落地 K02 并填报 K07（§4.3）。S7 RA-06 终验引用本草案 §10 断言与矩阵/模板终验（K07/SYS-1/L3-1）。修订本草案请按版本规范升级（主.次.修订 + 修订历史登记，v1.1.0 起状态回写 [Draft]→[Review]→[Approved]）。

---

## 附录 A：术语对照

| 术语 | 说明 |
|------|------|
| 四头 | X-User-ID / X-Tenant-ID / X-User-Role / X-Proxy-Source（信任链规范头）；X-Org-ID 为退役兼容别名（OB-8 收敛，值=tenant_code） |
| 委托头 | on_behalf_of 委托上下文：形态 A = JWT claim（U1 delegation.py）；形态 B = X-On-Behalf-Of（可选扩展，白名单限定）；出站委托两层 = 四头承载 delegated 有效身份 + X-Agent-Id 承载执行 agent principal |
| TRUSTED_PROXY_SOURCES / trusted_proxy_sources | 受信来源白名单（R-H1-1/2；§3.4 行为矩阵） |
| protocol_headers 包 | 共享常量/校验/注入/互译包（§3.9），全仓唯一事实源 |
| ob_k_ | 既有服务 Key（内存态，B-9 兼容保留，不主体化；K03 白名单过渡） |
| sk-agent-* | agent 主体服务密钥（U1 T1；本立项收口受信通道与审计，OB-6） |
| 有效身份/effective | 委托时 = delegated 目标；无委托 = principal 自身（§3.2） |
| 语义档 | 管理档/读写档/只读档（OB-12 互译锚，§6.1） |
| verify-env | 启动配置自检（OB-9 雏形，§9.2） |
| S1b 段门禁 | 协议头规范 v1.0 发布 + 非白名单带头 403（OpenBase 侧）+ 服务账号用例全绿 + verify-env 可用 + 端点矩阵模板评审通过 |

## 附录 B：最小集规则 → 设计锚点映射（盘点实证）

| 最小集规则 | 本草案落点 |
|-----------|-----------|
| R-H1-1 唯一注入点 | §3.2/§3.9（inject.build_outbound_headers 单点装配） |
| R-H1-2 下游校验/403 | §3.4 行为矩阵 + D-V5 + T3/T2 断言 |
| R-H1-3 编排透传禁 REAL_* | §3.4 双通道不变式；B-8 外移 S4 |
| R-H1-4 禁旁路 | §5.2 D-V6~D-V9 + k03_bypass_whitelist |
| R-H2-3 每请求验状态 | U1 已落地（verify_principal）；本草案 V-1~V-5 裁定分支 |
| R-M2-1 端点类别全覆盖 | §4 K07 模板 |
| R-M2-2 新增端点配套用例 | §4.1 隔离测试注册位（S7 终验） |
| R-M4-1/2 委托不跨界 | §3.6（衔接 delegation.py）+ V-2/V-3 fail-closed |
| R-L1-1 豁免=服务账号/受信编排 | §5.2 D-V6 + §9.1；REAL_* 限期移除外移 S4/R2（B-8） |
| §6.3 粗粒度角色互译 | §6 OB-12 |
| §4.4 审计 source/request_id | §8 OB-13 |

## 附录 C：参考既有文件清单（盘点实证）

- 代码：`openbase/modules/proxy/__init__.py`、`proxy/memory_proxy.py`、`llm_proxy/__init__.py`、`rag_proxy/__init__.py`、`dps_proxy/__init__.py`、`core/deps/auth.py`、`core/cache/redis_client.py`、`modules/auth/api_keys.py`、`modules/audit/__init__.py`、`core/models/base.py`、`settings.py`、`core/errors/codes.py`、`modules/identity/{verification,delegation,agent_keys}.py`（行号以 HEAD=914f00b 为准）
- 文档：`OpenBase-P2-1-统一身份协议头与信任链收口立项方案-v1.0.0.md`（914f00b）、`OpenBase-U1-统一身份收口设计草案-v1.0.0.md`（v1.1.0，[Approved]）、`OpenBase-统一身份最小特征集与隔离模型设计-v1.0.0.md`（v1.3.0）、`OpenBase-多系统联调联试分阶段版本规划-子系统纵切-v1.0.0.md`（v1.3.0）、`OpenBase-P2-2-隔离与fail-open收口立项方案-v1.0.0.md`、`OpenBase-多系统对接联调问题复盘与根治方案-v1.0.0.md`（v1.1.0）、`OpenBase-U1-统一身份收口立项方案-v1.0.0.md`、`doc/development/OpenBase-U1-统一身份收口-DevLogReport-v1.0.0.md`


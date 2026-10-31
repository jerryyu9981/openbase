# OpenBase 四系统 API Key 与授权优化 —— 残余项统一处置方案

| 项目 | 内容 |
|---|---|
| 文档版本 | v1.0.3 |
| 文档状态 | [Review] |
| 适用环境 | Dev / Pre-Pro / Pro |
| 关联方案 | `doc/audit/OpenBase-四系统APIKey与授权全生命周期评估与优化方案-v1.21.0.md`（§7.2/§7.3/§10.7~§10.24） |
| 关联清单 | `doc/audit/verification/OpenBase-四系统APIKey优化-A1生产验收清单-v1.0.1.md`、`...-A2生产配置收口清单-v1.0.9.md` |
| 编号体系 | 见 §1.1（47 项台账为唯一执行主键；批次 `P1~P5`；旧分组 `A1~A5/B1~B5/C1~C6/D` 已废止） |
| 覆盖对象 | OpenBase / OpenLLM / OpenRAG / OpenMemory / DPS |
| 编写 | FA-OpenBase-Dev（AI 辅助） |
| 批准 | 待人工批准 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|---|---|---|---|
| v1.0.0 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | 首版：静态核对方案 v1.19.0 §10 各节残余、A1（12 项）与 A2（13 项门禁）清单，汇总为 C/G/K/D/V/P 六类统一台账共 47 项；按「本仓 OIDC 残余 → 本仓治理与跨实例 → 跨仓收敛 → 部署与实测 → 暂缓项」划分五批（原编号 `B1~B5`），逐项给出处置建议、验收标准与批次门禁 |
| v1.0.1 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | 应人工裁定（选项 A）：执行批次由 `B1~B5` 更名为 `P1~P5`（Phase），消除与早期对话处置分组 `A1~A5/B1~B5/C1~C6/D` 的撞名；新增 §1.1「编号体系对照」，明确 47 项台账为唯一执行主键、`P1~P5` 为唯一批次主键，旧分组编号仅作历史别名并停止引用 |
| v1.0.2 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | P1 批次（C-01~C-05）执行完成：新增 §3.1「P1 完成情况」逐项登记落点与验证证据（`tests/test_oidc_p1_residuals.py`）；§2.1 速览与 §9.1 批次表同步状态；关联方案升 v1.20.0（新增 §10.23）、A2 升 v1.0.8（新增 SAN×4 与断言算法配置） |
| v1.0.3 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | P2 批次（C-06~C-10）执行完成：新增 §3.2「P2 完成情况」逐项登记落点与验证证据（`tests/test_p2_residuals.py` 20 passed）；§2.1 速览与 §9.1 批次表同步状态；关联方案升 v1.21.0（新增 §10.24）、A2 升 v1.0.9（新增 `OPENBASE_MCP_API_KEY_TOOLS`） |

---

## 1. 目的与范围

**目的**：回答三个问题——**还剩哪些未完成**、**每项怎么处置**、**按什么批次推进并如何证明完成**。把散落在方案 §10 各节「残余」、A1 未执行验收项、A2 未落地的生产基线收敛为**唯一执行台账**。

**范围划定**

- 纳入：方案 v1.19.0 中登记为残余/未实现/待裁定/未联调的事项；A1-01~A1-12 全部未执行项；A2 生产基线与 13 项启动门禁的未执行核对；§7.2/§7.3 中尚无实施记录的 P1/P2 事项。
- 需人工裁定的 3 项（D-05 主体映射策略、G-01 ABAC 复核流程、K-01 静态 Key 收敛节奏）只登记现状与选项，不预设结论，裁定后进入对应批次。

**核对方式与边界**

- 本台账基于**静态核对**：方案 §10 各节残余 + 本仓代码检索（`openbase/**` 关键词检索：KMS/角色字典/对账/轮换提醒/back-channel/id_token_hint/SAN 均无实现）。
- 跨仓事项（OpenLLM/OpenRAG/OpenMemory/DPS）**未逐仓复核代码**，凡标 `K` 类者均以「方案未记录实施结果」为依据，执行前须逐仓核对确认。
- 本文件是残余处置的**执行台账**；方案 §10 各节保留为来源记录，执行状态只在本文件更新，避免两处漂移。

### 1.1 编号体系对照（与早期处置分组的关系）

早期对话中的处置分组 `A1~A5` / `B1~B5` / `C1~C6` / `D` 按「动作性质」划分（约 17 组措施包），**未落成文件**；本文件改为「责任归属 + 可执行性」的 47 项台账，执行批次统一命名为 `P1~P5`，避免与之撞名。

| 编号体系 | 含义 | 划分维度 | 状态 |
|---|---|---|---|
| `A1` / `A2` | 文档编号：《A1 生产验收清单》《A2 生产配置收口清单》 | 交付物名称 | 有效（勿与旧分组 `A1` 混淆） |
| 旧 `A1~A5` / `B1~B5` / `C1~C6` / `D` | 早期对话的处置措施分组 | 动作性质（立即改 / 需改造 / 治理运维 / 暂缓） | **已废止**，仅作历史别名 |
| `C-01~C-10`、`G-01~G-03`、`K-01~K-06`、`D-01~D-07`、`V-01~V-14`、`P-01~P-07` | 本文件 47 项台账 | 责任归属（本仓代码 / 治理 / 跨仓 / 部署 / 实测 / 暂缓） | **唯一执行主键** |
| `P1~P5` | 执行批次（Phase） | 依赖顺序 | **唯一批次主键** |

**对照要点**

1. **内容无遗漏**：旧分组内容已全量并入本台账；本台账新增旧方案没有的两类——`V`（已完成未实测 14 项）与 `D`（部署运维收口 7 项）。
2. **撞名处理**：旧 `B1~B5`（措施包）与本文件 `P1~P5`（批次）不再共用字母；旧 `C1~C6` 与本文件 `C-01~C-10`、旧 `D`（暂缓）与本文件 `D-01~D-07`，以「是否带连字符」区分。
3. **引用规则**：此后派单、验收与提交说明只用「类别-序号」（如 `C-02`）与「批次」（如 `P1`），不再使用旧分组编号。

---

## 2. 台账总览

| 类别 | 含义 | 数量 | 批次 |
|---|---|:--:|---|
| **C** | 本仓代码能力缺口（单仓可闭合） | 10 | P1 / P2 |
| **G** | 治理与流程（本仓可提供能力，落地依赖组织） | 3 | P3 |
| **K** | 跨仓收敛（四仓改造） | 6 | P4 |
| **D** | 部署与运维收口（配置/密钥/裁定） | 7 | P4（D-05 需裁定） |
| **V** | 已完成、未做生产实测或真实联调 | 14 | P4（V-01~V-12 可先行） |
| **P** | 暂缓（依赖硬件/密评/基础设施/外部平台） | 7 | P5（按触发条件） |

合计 47 项（C10 + G3 + K6 + D7 + V14 + P7）；其中 3 项（D-05 / G-01 / K-01）需人工裁定后方可执行，其余可在批准后按批次启动。

### 2.1 未完成项速览（直接回答「还有哪些未完成」）

| 状态 | 项数 | 编号与要点 |
|---|:--:|---|
| 已完成 · P1 本仓代码 | 5 | C-01 SAN 预检、C-02 断言算法、C-03 `id_token_hint`、C-04 back-channel logout、C-05 Provider 级配置（证据见 §3.1） |
| 已完成 · P2 本仓代码 | 5 | C-06 静态 MCP Key 工具白名单、C-07 异常跨实例聚合、C-08 到期提醒、C-09 Key 侧对账、C-10 角色契约端点（证据见 §3.2） |
| 待执行 · 治理 | 3 | G-01 ABAC 双人复核、G-02 SoD 接入 `role:grant`、G-03 策略规模基线 |
| 待执行 · 跨仓 | 6 | K-01 静态 Key 收敛、K-02 DPS 停用本地密码、K-03 下游审计补 `key_id`/`entry`、K-04 角色字典替换、K-05 配额/吊销同步增强、K-06 SSO 全覆盖 |
| 待执行 · 部署/裁定 | 7 | D-01 A1 升版、D-02 A2 基线执行、D-03 双验签收口、D-04 存量 Key 到期收敛、D-05 主体映射裁定、D-06 编排与挂载、D-07 Provider 隔离约束 |
| 待实测/联调 | 14 | V-01~V-12（对应 A1-01~A1-12，全部未执行）、V-13 真实 IdP 联调、V-14 跨仓生产实测 |
| 暂缓 · 触发式 | 7 | P-01 SM2/密评、P-02 集中审计平台、P-03 信创灾备、P-04 终端宿主项、P-05 跨库分片审计链、P-06 KMS、P-07 省级 IdP 对接 |

**结论**：待执行 16 项（G 3 + K 6 + D 7）、待实测 14 项、暂缓 7 项；C 类 10 项已全部闭合（P1 5 项 + P2 5 项），方案 §10 与 A1/A2 中**不存在未归类、未排期的悬空项**。

**立即可启动性**

- **P1（C-01~C-05）已完成**（2026-10-31，见 §3.1）；**P2（C-06~C-10）已完成**（2026-10-31，见 §3.2）；P3 仅依赖 P1/P2 已合入。
- **P4 依赖三项裁定（D-05/G-01/K-01）+ 联调环境 + 证据目录**；V-01~V-12 可先对 v1.21.0 现状并行取证。
- **P5 全部为触发式**，不进入当前排期。

---

## 3. C 类：本仓代码残余

| 编号 | 事项 | 来源 | 现状 | 处置建议 | 批次 |
|---|---|---|---|---|---|
| C-01 | `tls_client_auth` SAN 型绑定本地预检 | §10.22 残余 | 仅比对 subject DN；SAN（dns/uri/ip/email）未预检 | 新增 `OPENBASE_OIDC_CLIENT_CERT_SAN_DNS/_URI/_IP/_EMAIL`；配置后启动期解析证书 SAN 并比对，不匹配拒启；留空跳过（IdP 侧仍为准） | P1 |
| C-02 | `private_key_jwt` 非 RSA 断言算法 | §10.21 残余 | 断言固定 `RS256` | 新增 `OPENBASE_OIDC_CLIENT_ASSERTION_ALGORITHM`（`RS256` 默认，可选 `ES256`/`ES384`）；门禁校验算法已接线且私钥类型匹配（RSA/EC），不匹配拒启；与 ID Token 算法白名单保持解耦 | P1 |
| C-03 | IdP 登出 `id_token_hint` | §10.19 残余 | 未保存、未透传 | 回调成功后将 ID Token 写入 Redis（键按 `issuer+sub+client_id`，TTL 对齐 refresh 有效期）；登出时按 state/主体取回并透传；不落日志、不落库明文 | P1 |
| C-04 | back-channel logout | §10.17/§10.19 残余 | 未实现，仅前端信道登出 | 新增 `POST /api/v1/auth/oidc/backchannel-logout`：校验 logout token 签名（IdP JWKS）、`iss`/`aud`/`events`、`jti` 重放（Redis 一次性）、`sub`/`sid`；命中即递增 `token_version` 并清理 state；IdP 未登记回调地址时端点返回 404 | P1 |
| C-05 | Provider 级 PKCE/签名算法/认证方式 | §10.18 残余 | 三级均为全局唯一配置 | `IdpProviderConfig` 增可选 `pkce_enabled` / `signing_algorithms` / `token_auth_method`；缺省回落全局值，Provider 声明变更即重建客户端缓存 | P1 |
| C-06 | 静态 MCP Key 工具白名单 | §10.12 残余 | 静态 Key 维持「不限工具」 | 新增 `OPENBASE_MCP_API_KEY_TOOLS`（按 Key 摘要/别名映射白名单 JSON）；生产建议显式绑定或显式 `*`；缺省保持现状（零行为变化） | P2 |
| C-07 | Key 异常检测跨实例聚合 | §10.12 残余；A1 §1 列出的「多实例中心化配额/异常聚合」（原方案 V-10，P1 排期） | 进程内滑动窗口，不跨实例/不持久化 | Redis 计数与集合聚合（`INCR`+`EXPIRE`、`SADD`+`SCARD`），冷却键共享；Redis 不可用回退进程内（保留现行为）；告警仍只告警不阻断 | P2 |
| C-08 | 到期提醒与一键轮换运维面 | §7.3 P2-5 | 仅轮换端点，无到期提醒 | 新增只读清单端点（到期 ≤7 天/已过期，按租户过滤）+ 事件 `service_key.expiring`；轮换复用既有端点，不新增写路径 | P2 |
| C-09 | 审计对账（Key 侧） | §7.3 P2-3 | 无对账任务 | 日对账：`签发数 = 有效数 + 吊销数 + 过期数`，差异写审计告警；下游拒绝数对账依赖 K-03，先不做跨系统比对 | P2 |
| C-10 | 统一角色字典契约端点 | §7.3 P2-1 | 下游保留三份硬编码角色映射，无统一契约 | 新增只读端点 `GET /api/v1/auth/roles/contract`（登录可读，返回角色码/权限点/层级 JSON schema，不含密钥与管理数据）；下游替换见 K-04 | P2 |

**C 类统一口径**：全部缺省零行为变化；新增配置一律进启动门禁（非法即拒启）；新增端点沿用 `BaseError` 错误契约，权限点复用 `security:admin` / `system:superadmin`，不新增角色。

### 3.1 P1 完成情况（C-01~C-05，2026-10-31）

| 编号 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| C-01 | 新增 `OPENBASE_OIDC_CLIENT_CERT_SAN_DNS/_URI/_IP/_EMAIL`；配置后启动期解析证书 SAN 并逐项比对（DNS/EMAIL 大小写不敏感、IP 归一、URI 精确；AND 语义），不匹配拒启；全留空跳过 | `openbase/settings.py`（`_certificate_san_values` / `_san_value_matches` / 门禁） | `tests/test_oidc_p1_residuals.py`（DNS 大小写/不匹配、四类 SAN、IP 不匹配、证书无 SAN、留空跳过共 6 例） |
| C-02 | 新增 `OPENBASE_OIDC_CLIENT_ASSERTION_ALGORITHM`（默认 `RS256`，可选 `ES256`/`ES384`）；门禁校验算法已接线且私钥类型/曲线匹配（RSA/EC，ES384 需 SECP384R1）；运行时断言按配置算法签名，与 ID Token 算法白名单解耦 | `openbase/settings.py`（`OIDC_CLIENT_ASSERTION_ALGORITHMS` / `_assert_private_key_matches_algorithm`）；`openbase/modules/auth/oidc.py`（`assertion_algorithm` / `_build_client_assertion`） | 同文件（默认 RS256、非法 HS256、RSA/EC 双向不匹配、ES384 曲线、非 PEM、ES256 运行时验签共 7 例）；`tests/test_oidc_token_auth.py` 既有私钥门禁用例同步为真实 RSA 私钥 |
| C-03 | 回调成功后保存 ID Token（键 `client_id + 统一主体 sub`，value 内嵌 `issuer` 供取回校验；TTL 对齐 refresh 有效期）；登出时加载 discovery 后按 issuer 取回、透传 `id_token_hint` 并一次性清理；不落日志/不落库明文 | `openbase/modules/auth/oidc_logout.py`（`OidcLogoutStore`）；`openbase/modules/auth/oidc.py`（callback 保存 / logout 透传） | 同测试文件（存储 roundtrip/issuer 不匹配/TTL/sid 索引、callback 写入 → 登出 URL 携带 → 登出后清除） |
| C-04 | 新增 `POST /api/v1/auth/oidc/backchannel-logout`：按未验签 `iss`/`aud` 定位已登记客户端（含 Provider）；校验 discovery `backchannel_logout_supported`（无匹配/不支持 → 404）；按 IdP JWKS 验签并校验 `events`/禁 `nonce`/`jti`/`sub|sid`；`jti` 一次性消费防重放；按 `sub`/`sid` 映射主体递增 `token_version` | `openbase/modules/auth/oidc.py`（`_logout_candidates` / `_verify_logout_token` / `_validate_logout_claims` / 端点） | 同测试文件（有效/form 与 JSON 载荷、jti 重放、events/nonce/jti/sub|sid 参数化负向、缺 token、坏签名、IdP 不支持、未知 issuer、仅 sid、Provider 分支） |
| C-05 | `IdpProviderConfig` 增可选 `pkce_enabled` / `signing_algorithms` / `token_auth_method`（取值归一与校验）；未声明回落全局；Provider 声明变更按 dataclass 等值重建客户端缓存；authorize 按 Provider 开关决定是否下发 PKCE | `openbase/modules/auth/idp_registry.py`；`openbase/modules/auth/oidc.py`（`pkce_enabled` / `signing_algorithms` / `token_auth_method`） | 同测试文件（解析/归一、非法认证方式/算法/非布尔 PKCE、覆盖与回落、缓存重建、PKCE 关闭不带 challenge） |

**批次门禁**

| 项 | 结果 |
|---|---|
| 单测 | `python -m pytest tests/test_oidc_p1_residuals.py` → 39 passed |
| 静态检查 | 本环境未安装 `ruff`（`No module named ruff`），未能执行 `ruff check`；已按规则保持导入排序/行宽，待具备 ruff 的环境补跑 |
| 零行为变化 | 所有新增字段均有默认值；Provider 未声明时逐项回落全局；SAN/断言算法配置留空或默认 RS256 时与原行为一致 |
| 安全 | 日志与存储不含私钥、证书原文、`client_secret` 或令牌全文；hint 仅存内存/Redis 值，不写审计 |
| Redis 降级 | hint/sid/jti 在 Redis 不可用时回退进程内（带 TTL + 可重入锁），不新增放行 |

**残余（P1 边界）**

- 未做真实 IdP 的 SAN 绑定、ES256 断言与 back-channel 端到端联调（当前证据为 mock IdP 9015/9016 全链路 + 单元级证书/密钥校验）；真实链路归 V-13。
- back-channel 的 `sid → 主体` 映射依赖同一登录链路写入的索引；跨实例需 Redis 可达，否则退化为单实例语义（与 §11 风险口径一致）。
- C-03 键设计以「`client_id` + 统一主体 sub」为键、issuer 内嵌 value，等价实现方案登记的 `issuer+sub+client_id` 键，避免登出阶段无法重建 issuer 键。

### 3.2 P2 完成情况（C-06~C-10，2026-10-31）

| 编号 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| C-06 | 新增 `OPENBASE_MCP_API_KEY_TOOLS`（JSON：键=静态 Key 摘要/明文，值=工具名数组；显式 `*` 仍全量）；命中静态 Key 后凭证携带白名单，未配置映射保持「不限工具」 | `openbase/settings.py`（`parse_mcp_api_key_tools` + 门禁）；`openbase/modules/mcp/credentials.py`（`_match_static_key` / `_static_key_tools`） | `tests/test_p2_residuals.py`（空/非法/归一、摘要命中、明文别名、无映射保持不限、`*` 通配） |
| C-07 | 异常检测优先 Redis 聚合（`INCR`+`EXPIRE` 速率、`SADD`+`SCARD`/`SMEMBERS` IP 集合、`SET NX EX` 冷却键共享）；Redis 不可达/调用失败回退进程内滑动窗口；仍只告警不阻断 | `openbase/modules/auth/key_anomaly.py`（`_observe_redis` / `_redis_cooldown_allows`） | 同文件（跨实例网段跳变+多 IP、跨实例速率突增、Redis 不可用回退、TTL 断言） |
| C-08 | 新增只读端点 `GET /api/v1/auth/api-keys/expiring?within_days=`（有效且到期 ≤N 天，含已过期；按租户过滤）；`ServiceKeyService.emit_expiring_events` 投递 `service_key.expiring`（Key+日 去重：Redis `SET NX EX`，回退进程内集合）；轮换复用既有端点，不新增写路径 | `openbase/modules/auth/service_keys.py`（`list_expiring` / `emit_expiring_events`）；`openbase/modules/identity/events.py`（事件类型注册）；`openbase/modules/auth/__init__.py`（端点） | 同文件（到期/已过期/远期/无到期/跨租户过滤、事件去重与载荷 `key.key_id`） |
| C-09 | 新增日对账 `ServiceKeyService.reconcile`：`签发数 = 有效数 + 吊销数 + 过期数`，差异写审计 `auth.service_key.reconcile` 并 ERROR 日志；仅本仓台账自洽，不做跨系统比对（下游归 K-03） | `openbase/modules/auth/service_keys.py`（`reconcile`） | 同文件（平衡快照计数、未登记状态造成不平衡时 `balanced=False` 且审计 detail 留痕） |
| C-10 | 新增只读端点 `GET /api/v1/auth/roles/contract`（登录可读）：角色码/档位（`readonly<readwrite<manage`）/权限点/本地别名/未知码策略；档位与 canonical 码来自 `config/role_tier_anchors.json`（不可用回落内置基线），权限点来自 DB 只读查询（不可达返回空映射）；不含密钥/管理数据 | 新增 `openbase/modules/auth/role_contract.py`（`build_role_contract` / `load_role_permissions`）；`openbase/modules/auth/__init__.py`（端点） | 同文件（契约结构/档位/权限点/未知码 `tier=None`/无敏感字段、DB 读取回退） |

**批次门禁**

| 项 | 结果 |
|---|---|
| 单测 | `python -m pytest tests/test_p2_residuals.py` → 20 passed |
| 回归 | `test_key_anomaly` / `test_api_keys` / `test_api_keys_api` / `test_mcp_edge_credentials` / `test_obs_mcp` / `test_identity_events_list` / `test_oidc_p1_residuals` 共 99 passed；`test_identity_t5` 8 passed |
| 静态检查 | 本环境未安装 `ruff`（`No module named ruff`），未能执行 `ruff check`；已按规则保持导入排序/行宽，待具备 ruff 的环境补跑 |
| 零行为变化 | `OPENBASE_MCP_API_KEY_TOOLS` 缺省空 = 不限工具；异常检测未注入时间时优先 Redis（不可用即回退原进程内逻辑）；到期清单/对账/契约端点均为只读或独立调用，不改变既有签发/校验/轮换语义 |
| 安全 | 静态 Key 匹配仍为常量时间比较；工具白名单只输出工具名；契约端点不含密钥/令牌/用户数据；审计只记 Key 元数据与计数 |

**残余（P2 边界）**

- C-08 的 `service_key.expiring` 事件需由运维/调度器周期性调用 `emit_expiring_events`（本批未新增调度基础设施）；端点本身只读不投递事件。
- C-09 对账同为可调用能力，未接入定时任务；差异告警依赖日志/审计消费端（P-02 集中审计平台为暂缓项）。
- C-10 下游四仓替换各自硬编码角色映射归 K-04；本批只提供契约，不改下游。
- C-07 跨实例语义依赖 Redis 可达；不可达时退化为单实例窗口（不新增放行，与 §11 风险口径一致）。

---

## 4. G 类：治理与流程

| 编号 | 事项 | 来源 | 现状 | 处置建议 | 批次 |
|---|---|---|---|---|---|
| G-01 | ABAC 变更双人复核（四眼原则） | §10.16 残余 | 单点 `security:admin` 直改 + 审计 | 新增 `abac_policy_change_requests` 表与申请/审批端点：create/update/delete 默认走「申请 → 第二人 approve → 生效」；保留超管紧急直改并强制审计标记 `emergency=true`；审批人与申请人不得同一主体 | P3 |
| G-02 | 三权分立强制接入角色授予 | §10.14 残余（ER-25） | 仅提供校验函数，`role:grant` 未调用 | `role:grant` 路径调用 `assert_separation_of_duties`，冲突返回 409 `PERM_DUTY_CONFLICT`；冲突对来自既有 `conflicting_duty_pairs` 基线 | P3 |
| G-03 | ABAC 策略规模与命中性能基线 | §10.16 残余 | 全量线性判定，无压测 | 增加规则数上限告警与命中耗时结构化日志（WARN 阈值可配）；≥1000 条时输出「需索引/缓存」提示；不做压测基础设施改造 | P3 |

---

## 5. K 类：跨仓收敛（OpenLLM / OpenRAG / OpenMemory / DPS）

> 执行前须逐仓核对当前实现，本表结论以方案无实施记录为依据。

| 编号 | 事项 | 来源 | 现状 | 处置建议 | 批次 |
|---|---|---|---|---|---|
| K-01 | 下游静态 Key 收敛为应急 bypass | §7.2 P1-6 | 仅完成生产 fail-closed 门禁，静态 Key 仍为主通道 | 三仓默认关闭静态 Key 通道，仅保留应急开关（必须配置过期与审计）；切 OpenBase JWKS/服务 Key 为主通道 | P4 |
| K-02 | DPS 停用本地密码登录 | §7.2 P1-6 | 仍保留本地密码与自签 JWT | 默认关闭本地密码登录，改 JWKS 验签 + 自省；保留迁移期开关与回滚路径 | P4 |
| K-03 | 下游审计补 `key_id`/`entry` | §7.2 P1-8 | 方案无实施记录（待核对） | 四仓审计记录 `key_id`/`subject`/`tenant`/`entry=proxy\|direct`（不含明文）；OpenLLM 优先 | P4 |
| K-04 | 统一角色字典下游替换 | §7.3 P2-1 | 下游三份硬编码映射（RAG `role_gate`、OM `role_map`、DPS `ROLE_TO_ANCHOR`） | 消费 C-10 发布的角色码契约（单一 JSON schema），删除硬编码；保留映射表为过渡 | P4 |
| K-05 | 下游配额/吊销同步增强 | §10.10/§10.11/§10.12 残余 | 配额单进程；吊销惰性拉取无调度；内省未接入 | OpenLLM 配额改 Redis 令牌桶；四仓可选后台调度（空闲期收敛）；按需接入内省，不作为常规路径 | P4 |
| K-06 | SSO 全覆盖（删除本地密码） | §7.3 P2-6 | OpenLLM 有 `IDENTITY_AUTHORITY` 开关；DPS 未覆盖 | 与 K-02 合并推进；生产固定 `openbase` 模式，本地身份表停写不删 | P4（随 K-02） |

---

## 6. D 类：部署与运维收口

| 编号 | 事项 | 来源 | 现状 | 处置建议 | 批次 |
|---|---|---|---|---|---|
| D-01 | A1 清单升版 | A1 v1.0.1（关联方案 v1.12.0） | 未覆盖 OIDC 五种认证/多 Provider/登出/双向 TLS；方案版本滞后 | 升 v1.1.0：关联方案 v1.19.0，新增 V-13/V-14 验收项与 OIDC 专项步骤 | P4 前置 |
| D-02 | A2 基线执行与漂移自检 | A2 v1.0.7 §6 | 清单已齐，未在生产逐项执行 | 按 A2 §2/§3 逐项核对存在性（秘密只记「已配置/未配置」），执行 §6.2 端点核对与 §6.3 负向启动 | P4 |
| D-03 | 双验签窗口收口 | §10.9 残余 | HS256 通道仍在；`jwt_require_rs256` 未置 true | 全量令牌 RS256 换发后：移除 `jwt_secret*` 与历史 kid、置 `jwt_require_rs256=true`、负向验证 HS256 令牌被拒 | P4 |
| D-04 | 存量 `ob_k_` 到期收敛 | A1-12 步骤 3、ER-01 | 存量 Key `expires_at IS NULL`（不过期） | 导出存量清单 → 按业务分批设置到期或轮换（复用 C-08 清单端点）；批次与通知窗口由业务确认 | P4 |
| D-05 | 终端用户令牌直连下游主体映射策略 | §10.10「待裁定」 | 默认显式映射，未配置即拒绝 | **需人工裁定**：A=显式映射表（安全优先，运维成本高）/ B=同库部署信任 `sub`（成本低，依赖网络隔离）；裁定后再落部署编排 | P4 前置（需裁定） |
| D-06 | 部署编排与秘密挂载 | §10.10/§10.20/§10.21/§10.22 | 仅仓内 `.env.example` 登记，无统一编排 | 编排固化：RS256 PEM、OIDC 客户端证书/私钥/CA、断言私钥只读挂载（0600）；下游注入 JWKS/吊销/服务 Key；固定 `IDENTITY_AUTHORITY=openbase` | P4 |
| D-07 | 多 Provider 主体隔离约束 | §10.18 残余 | 依赖 IdP 保证 issuer 唯一 | 纳入部署检查项：同 issuer 多 client 视为同一身份空间；登记 Provider 前核对 issuer 唯一性 | P4 |

---

## 7. V 类：已完成、未做生产实测/联调

| 编号 | 验收项 | 对应 A1 | 说明 |
|---|---|---|---|
| V-01 | 生产配置基线与 RS256 收口 | A1-01 | 含 `require_rs256` 负向启动 |
| V-02 | JWKS 发布与四仓本地验签 | A1-02 | 含 `aud`/过期/未映射主体三类负向 |
| V-03 | 换钥与未知 kid 平滑 | A1-03 | 双 kid 并存、零中断 |
| V-04 | 吊销收敛时延（四仓） | A1-04 | 内省即时；下游惰性拉取时延记录 |
| V-05 | 审计链双实例并发 | A1-05 | 同 PG 双实例 2000 条后 `ok=true` |
| V-06 | 审计 NDJSON 导出容量 | A1-06 | 1 万行、行序、超限 400、内存峰值 |
| V-07 | 留存清理与链完整性 | A1-07 | `=0` 拒绝、dry-run、删头不断链 |
| V-08 | E3 真实权限矩阵 | A1-08 | SoD/ABAC 四判定/IdP 视图零密钥 |
| V-09 | MCP 三形态与工具授权 | A1-09 | 越权 403 / `-32001` |
| V-10 | 离线宽限与断网降级 | A1-10 | 宽限内放行、超期拒绝、无标记不放行 |
| V-11 | 四仓生产门禁负向启动 | A1-11 | 每仓逐条拒启 |
| V-12 | 存量迁移与数据核对 | A1-12 | 自动补列、NULL 跳过、回滚演练 |
| V-13 | 真实 IdP 联调（OIDC 专项） | 新增 | 多 Provider 双环境（9012/9013 桩 → 真实 IdP）、登出联动、`client_secret_post/basic`、`private_key_jwt`、`mtls`/`tls_client_auth` 真实双向 TLS、discovery 算法交集 |
| V-14 | 跨仓生产实测 | 新增 | 四仓 JWKS 验签、吊销时延、门禁负向启动、审计字段（与 V-02/V-04/V-11 同批取证） |

**判定口径**：每项只允许 `Pass / Fail / Blocked`；`Blocked` 须写明阻塞与解除条件。P0 任一 `Fail` 不得上线；P1 `Fail` 需书面豁免并签字。V-01~V-12 可对 **v1.19.0 现状**先行执行，不必等待 P1~P3；V-13/V-14 在 P1~P3 代码冻结后执行。

---

## 8. P 类：暂缓项与触发条件

| 编号 | 事项 | 暂缓原因 | 触发条件 |
|---|---|---|---|
| P-01 | SM2 真实签名原语与密评 | 需 `gmssl`/密码机与标准映射（JWS 未定义 SM2） | 政务交付要求国密；接入后按 E3-3 注册表 `replace` 接线 |
| P-02 | 集中审计平台 / 跨库归档 / 对象存储冷备 / 等保 ≥6 个月介质留存 | 依赖独立审计系统与基础设施 | 等保测评或审计平台立项 |
| P-03 | 信创适配与异地灾备 | 依赖国产化目录与容灾基础设施 | 信创验收或灾备要求 |
| P-04 | 终端宿主项（TPM/安全启动/固件与模型签名/本地落盘加密/远程擦除） | 位于终端代理/固件，不在四仓代码范围 | 终端代理交付；控制面替代控制已具备（主体吊销/封禁、短 TTL 令牌、吊销增量同步、JWKS 离线验签） |
| P-05 | 跨库分片审计链 | 当前机制要求同一 PG 实例 | 审计分片设计另立（不得以本机制跨库拼接） |
| P-06 | KMS 托管密钥 | 依赖外部 KMS 服务 | 密钥管理平台接入；在此之前沿用只读挂载 + 摘要落库 |
| P-07 | 省级/部门 IdP 证书交换与平台对接流程 | 外部平台流程，非代码 | 与 V-13 并行推进，接口以 V-13 结论为准 |

---

## 9. 分批处置计划

### 9.1 批次划分与依赖

| 批次 | 范围 | 前置 | 产出 | 门禁 |
|---|---|---|---|---|
| **P1** | C-01~C-05（OIDC 残余） | 无；已执行（2026-10-31） | 代码 + 单测 + 方案「§10.23 OIDC 残余闭合」 | 已完成：`tests/test_oidc_p1_residuals.py` 39 passed；ruff 待具备环境补跑；A2 已同步新增配置；三远程推送 |
| **P2** | C-06~C-10（MCP 白名单/跨实例/提醒/对账/角色契约） | P1；已执行（2026-10-31） | 代码 + 单测 + 方案「§10.24 Key 生命周期残余闭合」 | 已完成：`tests/test_p2_residuals.py` 20 passed（回归 99 + 8）；ruff 待具备环境补跑；A2 已同步新增 `OPENBASE_MCP_API_KEY_TOOLS`；三远程推送 |
| **P3** | G-01~G-03（治理） | P2 | 代码 + 单测 + 方案 §10.25 + A2 权限点登记 | 同上；ABAC 审批流需人工确认流程口径 |
| **P4** | K-01~K-06、D-01~D-07、V-01~V-14 | P1~P3 冻结；D-05 已裁定；联调环境与证据目录就绪 | 四仓改动 + 生产验收证据 + A1 判定汇总 | 每仓 ruff/pytest 全绿；A1 P0 全 Pass；证据归档 `evidence/a1|a2/` |
| **P5** | P-01~P-07 | 触发条件成立 | 单独立项 | 按触发方验收要求 |

**可并行性**

- V-01~V-12 与 P1~P3 **可并行**（验收对象是 v1.19.0 现状能力），但同一环境变更（D-02/D-06）需串行，避免配置漂移干扰取证。
- V-13/V-14 必须在 P1~P4（K 类）代码冻结后执行，否则结论对不上最终版本。

### 9.2 每批固定纪律

1. **先测试后实现**（TDD）：新增行为先写失败用例，再实现至 GREEN。
2. **零行为变化优先**：所有新增配置/端点缺省关闭或保持现状；变更既有判定必须单独列出并回归。
3. **文档同批留痕**：方案追加实施结果小节（§10.23 起）+ 修订历史；新增配置同步 A2；A1 受影响项同步判定口径。
4. **精确提交**：`git add` 指定文件（禁用 `git add -A`），提交后推送 origin/backup/github 三远程并 `git ls-remote` 校验一致。
5. **人工门禁**：每批完成后需人工批准方可进入下一批；仅在「需裁定 / 高影响授权 / 门禁不通过」时中断回问。

### 9.3 每批验收标准（统一）

- 功能：新增行为有自动化用例覆盖，含至少 1 条负向用例；
- 安全：新增日志/审计不含私钥、证书原文、`client_secret`、令牌全文；
- 质量：`ruff check openbase tests` 0 错误；`pytest tests` 全绿；新增模块覆盖率 ≥90%；
- 可回退：新增配置全有默认值，关闭即恢复既有行为。

---

## 10. 需人工裁定事项

| 编号 | 事项 | 选项 | 影响 |
|---|---|---|---|
| D-05 | 终端用户令牌直连下游的主体映射 | **A：显式 `*_SUBJECT_MAP`（安全优先，运维成本高）** / B：同库部署信任 `sub`（成本低，依赖网络隔离） | 决定 K 类与 P4 编排口径；未裁定前下游按现状 fail-closed |
| G-01 | ABAC 双人复核流程 | **A：申请-审批-生效（四眼，流程重）** / B：保留超管直改 + 事后审计（轻量） | 影响 P3 端点设计与组织流程 |
| K-01 | 下游静态 Key 收敛节奏 | **A：一次性切主通道** / B：双通道并行一个发布窗口后关闭 | 影响 K 类批次内回滚策略 |

> 以上三项在本方案中只登记，不预设结论；P1/P2 不依赖上述裁定，可在批准后立即启动。

---

## 11. 风险与假设

| 风险 | 说明 | 缓解 |
|---|---|---|
| 跨仓改动面大 | K 类涉及四仓中间件与配置 | 分仓灰度、保留 bypass 开关、先补契约测试 |
| 真实 IdP 不可控 | V-13 依赖外部环境与证书交换 | 先用 mock IdP 固化断言，再由联调窗口取证；Blocked 需写明解除条件 |
| 多实例依赖 Redis | C-07/C-03/C-04 的共享状态 | Redis 不可用一律回退现有行为，不新增放行 |
| A1 已知边界 | ER-25（SoD 未强制）、ER-10（惰性拉取）等 | 不把未实现项判为通过；G-02/K-05 闭合后更新边界 |
| 文档漂移 | A1/A2 版本滞后于方案 | D-01 先行升版；本文件为残余执行唯一台账 |

**假设**：四仓可修改并可运行各自测试；生产拓扑满足 A1 §2.1（同 PG 双实例、Redis 可用、JWKS 可达）；证书与私钥可只读挂载。

---

## 12. 签核

| 角色 | 姓名 | 结论 | 日期 | 备注 |
|---|---|---|---|---|
| 方案评审（架构/安全） | | | | |
| 批次执行批准（项目负责人） | | | | |
| D-05/G-01/K-01 裁定人 | | | | |

**批准后执行口径**：自 P1 起按 9.2 纪律连续推进，不再逐批重复询问；仅裁定项与高影响操作单独回问。

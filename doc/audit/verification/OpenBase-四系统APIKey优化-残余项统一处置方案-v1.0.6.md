# OpenBase 四系统 API Key 与授权优化 —— 残余项统一处置方案

| 项目 | 内容 |
|---|---|
| 文档版本 | v1.0.6 |
| 文档状态 | [Review] |
| 适用环境 | Dev / Pre-Pro / Pro |
| 关联方案 | `doc/audit/OpenBase-四系统APIKey与授权全生命周期评估与优化方案-v1.23.0.md`（§7.2/§7.3/§10.7~§10.26） |
| 关联清单 | `doc/audit/verification/OpenBase-四系统APIKey优化-A1生产验收清单-v1.1.1.md`、`...-A2生产配置收口清单-v1.1.2.md` |
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
| v1.0.4 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | P3 批次（G-01~G-03）执行完成：新增 §4.1「P3 完成情况」逐项登记落点与验证证据（`tests/test_p3_governance.py` 8 passed，回归 127 passed）；G-01 经人工裁定采用 **B 口径（超管直改 + 事后审计）**，并在 §10 登记裁定结果；§2.1 速览与 §9.1 批次表同步状态；关联方案升 v1.22.0（新增 §10.25）、A2 升 v1.1.0（新增两项 ABAC 基线） |
| v1.0.5 | 2026-11-01 | FA-OpenBase-Dev（AI 辅助） | P4 启动：完成前置项 **D-01**（A1 清单升 v1.1.0，新增 A1-13 OIDC 专项、A1-14 跨仓实测，关联方案 v1.22.0，并同步 A1-08/A1-11 判定与 §7 边界）；§2.1 速览与 §6 D-01 状态同步；关联清单更新为 A1 v1.1.0 / A2 v1.1.1。D-05/K-01 仍待裁定 |
| v1.0.6 | 2026-11-01 | FA-OpenBase-Dev（AI 辅助） | P4 批 A 执行：**裁定落定** D-05=**A（显式 `*_SUBJECT_MAP` 主体映射）**、K-01=**B（双通道并行一个发布窗口后关闭静态 Key 主通道）**；**K-03** 四仓审计补 `key_id`/`subject`/`tenant`/`entry`（OpenLLM 106 passed、OpenRAG 54 passed、OpenMemory 48 passed、DPS 72 passed）；**K-04** OpenRAG/OpenMemory 消费角色契约（契约优先 + 本地回落）、DPS 双链分别回落，各仓新增单测；新增 §5.1「P4 批 A 完成情况」、§10 登记裁定、§9.1 批次表与 §2.1 速览同步；关联方案升 v1.23.0（新增 §10.26）、A2 升 v1.1.2（新增三仓契约地址配置项）、A1 升 v1.1.1（关联方案引用同步） |

---

## 1. 目的与范围

**目的**：回答三个问题——**还剩哪些未完成**、**每项怎么处置**、**按什么批次推进并如何证明完成**。把散落在方案 §10 各节「残余」、A1 未执行验收项、A2 未落地的生产基线收敛为**唯一执行台账**。

**范围划定**

- 纳入：方案 v1.19.0 中登记为残余/未实现/待裁定/未联调的事项；A1-01~A1-12 全部未执行项；A2 生产基线与 13 项启动门禁的未执行核对；§7.2/§7.3 中尚无实施记录的 P1/P2 事项。
- 需人工裁定的 3 项（D-05 主体映射策略、G-01 ABAC 复核流程、K-01 静态 Key 收敛节奏）**已全部裁定**：G-01=B（2026-10-31）、D-05=A、K-01=B（2026-11-01）；裁定结果见 §10，并按裁定进入对应批次执行。

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
| **D** | 部署与运维收口（配置/密钥/裁定） | 7 | P4（D-05 已裁定 A） |
| **V** | 已完成、未做生产实测或真实联调 | 14 | P4（V-01~V-12 可先行） |
| **P** | 暂缓（依赖硬件/密评/基础设施/外部平台） | 7 | P5（按触发条件） |

合计 47 项（C10 + G3 + K6 + D7 + V14 + P7）；其中 3 项裁定项（D-05 / G-01 / K-01）**已于 2026-10-31 与 2026-11-01 全部裁定**（G-01=B、D-05=A、K-01=B，见 §10），不再阻塞批次推进。

### 2.1 未完成项速览（直接回答「还有哪些未完成」）

| 状态 | 项数 | 编号与要点 |
|---|:--:|---|
| 已完成 · P1 本仓代码 | 5 | C-01 SAN 预检、C-02 断言算法、C-03 `id_token_hint`、C-04 back-channel logout、C-05 Provider 级配置（证据见 §3.1） |
| 已完成 · P2 本仓代码 | 5 | C-06 静态 MCP Key 工具白名单、C-07 异常跨实例聚合、C-08 到期提醒、C-09 Key 侧对账、C-10 角色契约端点（证据见 §3.2） |
| 已完成 · P3 治理 | 3 | G-01 ABAC 变更事后审计、G-02 SoD 接入角色授予、G-03 策略规模/耗时基线（证据见 §4.1） |
| 已完成 · P4 前置 | 1 | D-01 A1 清单升 v1.1.0（2026-11-01，新增 A1-13 OIDC 专项 / A1-14 跨仓实测，关联方案 v1.22.0） |
| 已完成 · P4 批 A | 2 | K-03 四仓审计补 `key_id`/`subject`/`tenant`/`entry`、K-04 OpenRAG/OpenMemory/DPS 消费角色契约（契约优先 + 本地回落）（证据见 §5.1） |
| 待执行 · 跨仓 | 4 | K-01 静态 Key 双通道收口（已裁定 B）、K-02 DPS 停用本地密码、K-05 配额/吊销同步增强、K-06 SSO 全覆盖 |
| 待执行 · 部署/裁定 | 6 | D-02 A2 基线执行、D-03 双验签收口、D-04 存量 Key 到期收敛、D-05 显式主体映射落部署编排（已裁定 A）、D-06 编排与挂载、D-07 Provider 隔离约束 |
| 待实测/联调 | 14 | V-01~V-12（对应 A1-01~A1-12，全部未执行）、V-13 真实 IdP 联调、V-14 跨仓生产实测 |
| 暂缓 · 触发式 | 7 | P-01 SM2/密评、P-02 集中审计平台、P-03 信创灾备、P-04 终端宿主项、P-05 跨库分片审计链、P-06 KMS、P-07 省级 IdP 对接 |

**结论**：待执行 10 项（K 4 + D 6）、待实测 14 项、暂缓 7 项；C 类 10 项（P1 5 项 + P2 5 项）、G 类 3 项（P3）、D-01 前置项与 P4 批 A（K-03/K-04）已闭合，方案 §10 与 A1/A2 中**不存在未归类、未排期的悬空项**。

**立即可启动性**

- **P1（C-01~C-05）已完成**（2026-10-31，见 §3.1）；**P2（C-06~C-10）已完成**（2026-10-31，见 §3.2）；**P3（G-01~G-03）已完成**（2026-10-31，见 §4.1）。
- **P4 已启动**：D-01（A1 升版）与批 A（K-03/K-04）于 2026-11-01 完成（见 §5.1）；两项裁定已落定（D-05=A、K-01=B），批 B（K-02/K-06）可立即启动；批 C（K-01/K-05、D-02~D-07）依赖联调环境与证据目录；V-01~V-12 可先对现状并行取证。
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
| G-01 | ABAC 变更双人复核（四眼原则） | §10.16 残余 | 单点 `security:admin` 直改 + 审计 | 经人工裁定取 **B 口径**：不新增审批表/端点，保留超管直改；审计 detail 固定写入 `review_mode="post_audit"`，update/delete 附变更前快照 `previous`，并输出 WARN 提示事后复核 | P3 |
| G-02 | 三权分立强制接入角色授予 | §10.14 残余（ER-25） | 曾仅提供校验函数，`role:grant` 未调用 | 新增 `ensure_role_grant_allowed`（按「结果角色集」判定，`replace=True` 取新授予集、`replace=False` 取既有 ∪ 新增）；接入 `role:grant` 相关路径（用户创建/改派、agent 创建、OIDC 增量映射），冲突抛 409 `PERM_DUTY_CONFLICT` | P3 |
| G-03 | ABAC 策略规模与命中性能基线 | §10.16 残余 | 全量线性判定，无告警 | 新增 `OPENBASE_ABAC_RULE_SOFT_LIMIT`（默认 1000）与 `OPENBASE_ABAC_EVALUATION_WARN_MS`（默认 50）：超规则数或超耗时输出结构化 WARN（含「需索引/缓存」提示），不阻断判定；两项进启动门禁 | P3 |

### 4.1 P3 完成情况（G-01~G-03，2026-10-31）

| 编号 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|
| G-01 | 按裁定 B 落地「超管直改 + 事后审计」：新增常量 `ABAC_CHANGE_REVIEW_MODE="post_audit"`；审计 detail 固定写 `review_mode`，update/delete 附 `previous` 改前快照；策略 create/update/delete 提交后输出 `abac policy changed without dual review; post-audit required` WARN（仅标量 `policy_id`/`version`/`actor_id`，删除后不访问 ORM 实例） | `openbase/modules/auth/abac_policy_store.py` | `tests/test_p3_governance.py`（create/update/delete 审计标记与快照、3 条 WARN 捕获） |
| G-02 | 新增 `ensure_role_grant_allowed(existing, granted, replace=)` 入口，复用 `conflicting_duty_pairs` 基线；冲突抛 `BaseError(PERM_DUTY_CONFLICT)`（HTTP 409）；接入 `create_user` / `assign_role` / `create_agent_subject`（单角色替换语义）与 OIDC 角色映射（增量并集语义） | `openbase/core/errors/codes.py`；`openbase/modules/auth/access_control.py`；`openbase/modules/users/__init__.py`；`openbase/modules/identity/agents.py`；`openbase/modules/auth/oidc.py` | 同测试文件（冲突抛错与 409 映射、并集新增冲突、`replace=True` 整改历史冲突） |
| G-03 | `evaluate_abac` 增可选 `soft_limit` / `warn_ms`（默认惰性读 `get_settings()`，异常回退模块常量 1000/50）；`time.perf_counter` 计时，超规则数输出 `abac rule set exceeds soft limit; consider index/cache`，超耗时输出 `abac evaluation slow; consider index/cache`（extra 含 `elapsed_ms`/`rule_count`/阈值）；判定语义不变 | `openbase/settings.py`（两项字段 + `_validate_e3_governance_configuration` 非正拒启）；`openbase/modules/auth/access_control.py` | 同测试文件（超规则数告警、慢判定告警、阈值内静默、非正阈值拒启） |

**批次门禁**

| 项 | 结果 |
|---|---|
| 单测 | `python -m pytest tests/test_p3_governance.py` → 8 passed |
| 回归 | `test_e3_governance` / `test_users_admin` / `test_settings` / `test_oidc_p1_residuals` / `test_identity_t5` / `test_p3_governance` / `test_p2_residuals` 合计 127 passed（275.72s） |
| 静态检查 | 本环境未安装 `ruff`（`No module named ruff`），未能执行 `ruff check`；已按规则保持导入排序/行宽，待具备 ruff 的环境补跑 |
| 零行为变化 | 两项 ABAC 阈值默认 1000/50 仅在超限时告警；`ensure_role_grant_allowed` 对既有单角色授予路径（`ALLOWED_ROLES` 不含职责码）恒不冲突；OIDC 白名单不含职责码，故增量映射不会新增拒绝 |
| 安全 | WARN 与审计只记录策略标识、版本、操作者 id 与计数，不含策略全文或凭据；`PERM_DUTY_CONFLICT` 文案不含主体敏感信息 |

**残余（P3 边界）**

- G-01 为「事后审计」口径，**无审批前置**：双人复核依赖组织流程与审计消费端（人工 review 审计 `review_mode=post_audit` 记录），未实现强制第二人签字。
- G-02 未覆盖跨仓授予路径（下游角色映射归 K-04）；如未来出现多角色批量授予 HTTP 端点，须按 `replace=False` 并集语义接入。
- G-03 仅提供告警，不实现索引/缓存优化；真实规模压测归 P4 的 V 类实测。

---

## 5. K 类：跨仓收敛（OpenLLM / OpenRAG / OpenMemory / DPS）

> 执行前须逐仓核对当前实现。K-03/K-04 已于 2026-11-01 完成四仓/三仓逐仓核对与落地（见 §5.1）；K-01/K-02/K-05/K-06 仍以方案无实施记录为依据，执行前须再核对。

| 编号 | 事项 | 来源 | 现状 | 处置建议 | 批次 |
|---|---|---|---|---|---|
| K-01 | 下游静态 Key 收敛为应急 bypass | §7.2 P1-6 | 仅完成生产 fail-closed 门禁，静态 Key 仍为主通道 | 经人工裁定取 **B 口径**：双通道并行一个发布窗口后关闭静态 Key 主通道；三仓默认保持双通道，窗口结束默认关闭静态 Key 通道、仅保留带过期与审计的应急开关；切 OpenBase JWKS/服务 Key 为主通道 | P4（已裁定，批 C） |
| K-02 | DPS 停用本地密码登录 | §7.2 P1-6 | 仍保留本地密码与自签 JWT | 默认关闭本地密码登录，改 JWKS 验签 + 自省；保留迁移期开关与回滚路径 | P4（批 B） |
| K-03 | 下游审计补 `key_id`/`subject`/`tenant`/`entry` | §7.2 P1-8 | **已完成（2026-11-01）**：四仓审计 identity 由 6 核心键扩展为 10 键，`key_id=sha256(credential)[:12]`（不含明文）、`entry=proxy\|direct`，受信代理链自动判 `proxy` | 四仓审计记录 `key_id`/`subject`/`tenant`/`entry=proxy\|direct`（不含明文）；OpenLLM 优先 | P4（批 A，已完成） |
| K-04 | 统一角色字典下游替换 | §7.3 P2-1 | **已完成（2026-11-01）**：OpenRAG/OpenMemory/DPS 消费 `GET /api/v1/auth/roles/contract`（契约优先 + 本地映射回落，契约地址为空即关闭=零行为变化）；DPS 双链分别回落不互读 | 消费 C-10 发布的角色码契约（单一 JSON schema），删除硬编码；保留映射表为过渡 | P4（批 A，已完成） |
| K-05 | 下游配额/吊销同步增强 | §10.10/§10.11/§10.12 残余 | 配额单进程；吊销惰性拉取无调度；内省未接入 | OpenLLM 配额改 Redis 令牌桶；四仓可选后台调度（空闲期收敛）；按需接入内省，不作为常规路径 | P4（批 C） |
| K-06 | SSO 全覆盖（删除本地密码） | §7.3 P2-6 | OpenLLM 有 `IDENTITY_AUTHORITY` 开关；DPS 未覆盖 | 与 K-02 合并推进；生产固定 `openbase` 模式，本地身份表停写不删 | P4（批 B，随 K-02） |

### 5.1 P4 批 A 完成情况（K-03 / K-04，2026-11-01）

**裁定前置**：D-05=**A（显式 `*_SUBJECT_MAP` 主体映射）**、K-01=**B（双通道并行一个发布窗口后关闭静态 Key 主通道）**（见 §10）。批 A 只做 K-03/K-04，不触碰静态 Key 通道与主体映射部署。

| 编号 | 仓 | 实施内容 | 落点 | 验证证据 |
|---|---|---|---|---|
| K-03 | OpenLLM | `IdentityState` 增 `key_id`/`entry`（`proxy`/`direct` 常量）；`to_dict()` 输出；受信头解析固定 `entry=proxy`；`audit_identity` 核心键 6 → 10（`key_id`/`subject`/`tenant`/`entry`）；`attach_api_key_context(state, request)` 由审计中间件接入成功/失败记录 | `backend/app/identity/identity_context.py`、`backend/app/identity/audit_identity.py`、`backend/app/middleware/audit.py` | 新增 `backend/tests/unit/test_k03_audit_key_identity.py`（9 用例）；`test_s4_t10_audit_chain.py`、`test_s4_t2_identity_base.py` 断言同步为 10 键；定向回归 106 passed |
| K-03 | OpenRAG | `api_key.py` 新增 `credential_fingerprint(credential)=sha256[:12]`；JWT 分支 `api_key_entry="direct"`；API Key 通过后落 `api_key_id`（摘要）与 `api_key_entry`（bypass 直连=`direct`，受信代理=`proxy`）；`IdentityContext`/`identity_to_dict`/审计 identity 输出四键；`identity_gate._attach_auth_context` 统一三处注入 | `src/openrag/api/middleware/api_key.py`、`src/openrag/identity/context.py`、`src/openrag/identity/audit_identity.py`、`src/openrag/api/middleware/identity_gate.py` | 新增 `tests/unit/test_k03_k04_audit_contract.py`；定向回归 54 passed |
| K-03 | OpenMemory | 审计 identity 核心键 6 + `AUDIT_AUTH_KEYS` 4 = 10，`subject/tenant` 取 effective 回落 principal，`entry` 非 `proxy/direct` 归一为 `direct`；`IdentityState`/`build_identity_state` 增 `key_id`/`entry`；`server.api_key_middleware` 认证通过落 `request.state.api_key_id`；`identity_gate._attach_auth_context` 受信链判 `proxy` | `src/openmemory/identity/audit_identity.py`、`src/openmemory/identity/inbound_gate.py`、`src/openmemory/api/middleware/identity_gate.py`、`src/openmemory/api/server.py` | 新增 `tests/unit/test_k03_k04_audit_contract.py`（含 TestClient：受信 gate→`entry=proxy`、本地 gate→`entry=direct`）；定向回归 48 passed |
| K-03 | DPS | `build_audit_identity_block` 输出 10 键；`IdentityState` 增 `key_id`/`entry`；`identity_gate_middleware` 收口处 `_attach_auth_context`（取 `HEADER_API_KEY` 摘要，`proxy_source/proxy_chain` 非空判 `proxy`） | `src/identity/audit_identity.py`、`src/identity/inbound_gate.py`、`src/middleware/identity_gate_middleware.py` | 新增 `src/tests/test_k03_k04_audit_contract.py`（`_attach_auth_context` 直接单测 + 双链契约）；定向回归 72 passed |
| K-04 | OpenRAG | `role_map` 增契约层（`_CONTRACT_ENV`/`_CONTRACT_SCHEMA_VERSION=1`/TTL 300s/`_http_get_json`/`_normalize_contract`/`load_role_contract`/`apply_role_contract`/`reset_role_contract`），`interpret_openbase_role` 改用 `_active_role_tier()`（契约优先、未知码回落本地 `ROLE_TIER`）；`settings.IdentityTrustConfig.role_contract_url`（env `OPENRAG_IDENTITY_ROLE_CONTRACT_URL`，空=关闭）；`role_gate.__init__` 装载契约 | `src/openrag/identity/role_map.py`、`src/openrag/config/settings.py`、`src/openrag/api/middleware/role_gate.py` | 同测试文件；`test_s3_t9_role_mapping.py` 回归；定向 54 passed |
| K-04 | OpenMemory | `role_map` 同构契约层，`_TIER_BY_NAME={"readonly":READ,"readwrite":READWRITE,"manage":MANAGE}`；`IdentityTrustConfig.role_contract_url`（env 前缀 `OPENMEMORY_IDENTITY_`）；`identity_gate.__init__` 装载契约 | `src/openmemory/identity/role_map.py`、`src/openmemory/utils/config.py`、`src/openmemory/api/middleware/identity_gate.py` | 同测试文件（editor 未知码 403 等）；定向 48 passed |
| K-04 | DPS | `role_map` 契约层 `_contract_anchor(role_code)`；`resolve_role_anchor` = 契约锚点 or `ROLE_TO_ANCHOR`；`local_role_anchor` = 契约锚点 or `LOCAL_ROLE_TO_ANCHOR`（**两表互不读取**）；`config.identity_role_contract_url`（env `IDENTITY_ROLE_CONTRACT_URL`）；`rest_api.app.register_s5_middleware` 装载契约 | `src/identity/role_map.py`、`src/config.py`、`src/rest_api/app.py` | 同测试文件（受信链与本地链分别回落）；定向 72 passed |

**批次门禁**

| 项 | 结果 |
|---|---|
| 单测 | OpenLLM 定向回归 106 passed；OpenRAG 定向回归 54 passed；OpenMemory 定向回归 48 passed；DPS 定向回归 72 passed（解释器统一为 OpenRAG 自带 `.venv`，Python 3.11.9 / pytest 9.1.1） |
| 零行为变化 | 契约地址为空 = 契约关闭，角色判定逐码回落本地映射（OpenRAG 有专门用例实证）；审计新增 4 键为**纯追加**，不改变既有 6 键语义；`entry` 缺省归一 `direct`，无代理链时与原行为一致 |
| 安全 | `key_id` 为 `sha256(credential)[:12]` 摘要，四仓**均不记录密钥明文/令牌全文**；契约端点只含角色码/档位/权限点，不含密钥与管理数据 |
| 跨仓一致性 | 四仓审计 identity 键名与语义完全对齐（`key_id`/`subject`/`tenant`/`entry`）；三仓契约装载实现同构（同常量、同 TTL、同回落），便于后续统一运维 |
| 静态检查 | 本环境未安装 `ruff`（`No module named ruff`），`ruff check` 待具备环境补跑；已按规则保持导入排序/行宽 |
| 完整测试套件 | **未全量运行**：四仓全量套件依赖 `psycopg`/`numpy`/`jinja2` 等本机缺失依赖，本批以「定向用例 + 相关既有回归」为证据，如实登记 |

**残余（批 A 边界）**

- K-04 仅完成「消费契约 + 本地回落」；**硬编码映射表未删除**（作为过渡与回落基线保留），删除需等 D-05=A 部署编排与契约可用性验证后另行验收。
- 契约装载为**启动期一次装载 + TTL 缓存**，未实现热更新推送；契约变更需重启或等待缓存过期（TTL 300s 仅作用于显式 `force` 之外的取回节流，实际装载点仍为启动）。
- K-03 审计键落库依赖各仓既有审计写入路径可达；跨实例聚合与下游拒绝数对账仍归 K-05 / C-09 边界。
- 静态 Key 通道（K-01）、DPS 本地密码停用（K-02/K-06）**本批未触碰**，按裁定 B 留待批 B/批 C 的双通道窗口执行。

---

## 6. D 类：部署与运维收口

| 编号 | 事项 | 来源 | 现状 | 处置建议 | 批次 |
|---|---|---|---|---|---|
| D-01 | A1 清单升版 | A1 v1.0.1（关联方案 v1.12.0） | **已完成（2026-11-01）**：升 v1.1.0，关联方案 v1.22.0，新增 A1-13 OIDC 专项（对应 V-13）与 A1-14 跨仓实测（对应 V-14），并同步 A1-08 SoD/事后审计判定、A1-11 负向门禁与 §7 边界 | 已关闭（无需后续动作） | P4 前置 |
| D-02 | A2 基线执行与漂移自检 | A2 v1.0.7 §6 | 清单已齐，未在生产逐项执行 | 按 A2 §2/§3 逐项核对存在性（秘密只记「已配置/未配置」），执行 §6.2 端点核对与 §6.3 负向启动 | P4 |
| D-03 | 双验签窗口收口 | §10.9 残余 | HS256 通道仍在；`jwt_require_rs256` 未置 true | 全量令牌 RS256 换发后：移除 `jwt_secret*` 与历史 kid、置 `jwt_require_rs256=true`、负向验证 HS256 令牌被拒 | P4 |
| D-04 | 存量 `ob_k_` 到期收敛 | A1-12 步骤 3、ER-01 | 存量 Key `expires_at IS NULL`（不过期） | 导出存量清单 → 按业务分批设置到期或轮换（复用 C-08 清单端点）；批次与通知窗口由业务确认 | P4 |
| D-05 | 终端用户令牌直连下游主体映射策略 | §10.10「待裁定」 | **已裁定 A（2026-11-01）**：采用显式 `*_SUBJECT_MAP` 主体映射（安全优先）；未配置映射仍 fail-closed | 按裁定 A 落部署编排：四仓注入显式主体映射表，未映射主体拒绝；映射变更留审计 | P4（已裁定，批 C） |
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
| **P3** | G-01~G-03（治理） | P2；已执行（2026-10-31） | 代码 + 单测 + 方案「§10.25 P3 治理残余闭合」 | 已完成：`tests/test_p3_governance.py` 8 passed（回归 127 passed）；G-01 已裁定为 B 口径（事后审计）；ruff 待具备环境补跑；A2 已同步两项 ABAC 基线；三远程推送 |
| **P4** | K-01~K-06、D-01~D-07、V-01~V-14 | P1~P3 冻结；D-01 已完成；**裁定全部落定**（D-05=A / K-01=B，2026-11-01）；批 A（K-03/K-04）已完成；联调环境与证据目录就绪 | 四仓改动 + 生产验收证据 + A1 判定汇总 | 批 A 已完成：四仓定向回归 106/54/48/72 passed；后续每仓 ruff/pytest 全绿；A1 P0 全 Pass；证据归档 `evidence/a1\|a2/` |
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
| D-05 | 终端用户令牌直连下游的主体映射 | ~~A：显式 `*_SUBJECT_MAP`（安全优先，运维成本高）~~ / ~~B：同库部署信任 `sub`（成本低，依赖网络隔离）~~ | **已于 2026-11-01 裁定为 A**：采用显式 `*_SUBJECT_MAP` 主体映射（安全优先）；未配置映射一律 fail-closed；按裁定落部署编排 |
| G-01 | ABAC 双人复核流程 | ~~A：申请-审批-生效（四眼，流程重）~~ / **B：保留超管直改 + 事后审计（轻量）** | **已于 2026-10-31 裁定为 B**：不新增审批表与端点；审计 detail 固定 `review_mode="post_audit"` + 改前快照，并输出 WARN；双人复核由组织流程消费审计记录完成 |
| K-01 | 下游静态 Key 收敛节奏 | ~~A：一次性切主通道~~ / **B：双通道并行一个发布窗口后关闭** | **已于 2026-11-01 裁定为 B**：三仓保持双通道并行一个发布窗口，窗口结束默认关闭静态 Key 主通道、仅保留带过期与审计的应急开关 |

> 三项裁定**已全部落定**：G-01=B（2026-10-31，已随 P3 落地）、D-05=A、K-01=B（2026-11-01）。批 A（K-03/K-04）已按裁定先行完成；D-05=A 与 K-01=B 的执行分别归批 C（部署编排与静态 Key 通道收口）。

---

## 11. 风险与假设

| 风险 | 说明 | 缓解 |
|---|---|---|
| 跨仓改动面大 | K 类涉及四仓中间件与配置 | 分仓灰度、保留 bypass 开关、先补契约测试 |
| 真实 IdP 不可控 | V-13 依赖外部环境与证书交换 | 先用 mock IdP 固化断言，再由联调窗口取证；Blocked 需写明解除条件 |
| 多实例依赖 Redis | C-07/C-03/C-04 的共享状态 | Redis 不可用一律回退现有行为，不新增放行 |
| A1 已知边界 | ER-25（SoD 未强制）已由 P3 G-02 闭合；ER-10（惰性拉取）等仍在 | 不把未实现项判为通过；ER-25 更新为已闭合，K-05 闭合后再更新其余边界 |
| 文档漂移 | A1/A2 版本滞后于方案 | D-01 先行升版；本文件为残余执行唯一台账 |

**假设**：四仓可修改并可运行各自测试；生产拓扑满足 A1 §2.1（同 PG 双实例、Redis 可用、JWKS 可达）；证书与私钥可只读挂载。

---

## 12. 签核

| 角色 | 姓名 | 结论 | 日期 | 备注 |
|---|---|---|---|---|
| 方案评审（架构/安全） | | | | |
| 批次执行批准（项目负责人） | | | | |
| D-05/G-01/K-01 裁定人 | | | | G-01 已裁定 B（2026-10-31）；D-05 已裁定 A、K-01 已裁定 B（2026-11-01，用户裁定） |

**批准后执行口径**：自 P1 起按 9.2 纪律连续推进，不再逐批重复询问；仅裁定项与高影响操作单独回问。

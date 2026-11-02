# OpenBase 四系统 API Key 优化 —— 残余项分批推进方案

| 项目 | 内容 |
|---|---|
| 文档版本 | v1.4.0 |
| 文档状态 | [Review] |
| 适用环境 | 本机（无 Docker）/ Dev 原生进程 / Pre-Pro / Pro |
| 关联台账 | `doc/audit/verification/OpenBase-四系统APIKey优化-残余项统一处置方案-v1.4.0.md`（§2.1/§5.4/§5.5/§6/§7/§8/§9.1） |
| 关联清单 | `...-A1生产验收清单-v1.1.7.md`、`...-A2生产配置收口清单-v1.1.9.md` |
| 关联记录 | `...-D类部署取证执行记录-v1.0.4.md`（§5 E 批联动） |
| 关联方案 | `doc/audit/OpenBase-四系统APIKey与授权全生命周期评估与优化方案-v1.30.0.md`（§10.31/§10.32/§10.33） |
| 约束 | **本轮不使用 Docker**（电脑资源有限）；环境取证以原生进程 + SQLite/本机依赖为限 |
| 编写 | FA-OpenBase-Dev（AI 辅助） |
| 批准 | 待人工批准 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|---|---|---|---|
| v1.4.0 | 2026-11-02 | FA-OpenBase-Dev（AI 辅助） | **E3c：E3b 两项 Blocked 的具体解决完成**：`openllm_openbase_token_accept` —— OpenBase RS256 令牌在 OpenLLM `/api/v1/auth/me` **200**（`OPENBASE_SUBJECT_MAP` 命中 `e3c-openbase-user`），未知 kid / 错误签名 / 主体未映射 / 已过期四类 **401**；`openllm_prod_env_smoke` —— 门禁矩阵 C01 放行 + C02~C16 **15/15 拒绝**、豁免行 `EXEMPT_OK`（routes=5）、生产 ENV 合规启动 `GATES_OK`、`/health` **200**、本地登录 **401**；新增 §9.7，§9.5 两行 Blocked 改 Pass；吊销增量（E4）与生产拓扑（E5）仍 ⛔ Blocked；证据 `evidence/e3/e3c-openllm-20261102.json`（9804 B，SHA-256 `E67F523E…6B3823`） |
| v1.3.0 | 2026-11-02 | FA-OpenBase-Dev（AI 辅助） | **E3b OpenLLM R17 两向取证完成**：原生 `uvicorn` + SQLite（ENV=development）下，N1 `IDENTITY_AUTHORITY=openbase` 缺 `OPENBASE_JWKS_URL` → 启动门禁拒启 `exit=3`（`ValueError ...（R17）`）；N2 非法取值 `openid` → pydantic `ValidationError` 拒启 `exit=1`；P1 `openbase` 正向 `/health` 200、`/api/v1/auth/login` **403** 且响应含 R17 文案；P2 `local` 对照登录 **401**「用户名或密码错误」且不含 R17 文案（门禁可开可关）；新增 §9.6，更新 §9.3、§9.5；生产 ENV 全门禁与 OpenBase 令牌放行仍 ⛔ Blocked |
| v1.2.0 | 2026-11-02 | FA-OpenBase-Dev（AI 辅助） | **E3 本机生产形态执行（真实生产仍 Blocked）**：以原生 `uvicorn` 单进程（无 Docker）完成 OpenBase D-03/D-05/D-06 两向（RS256 强制生效且 HS256 令牌 401、主体映射解析 1 条、MCP 摘要/密钥文件启动放行、明文 Key 与缺 RS256 材料拒启）、DPS K-01/K-02 两向（`closed` 非应急 Key 401 `AUTH_STATIC_KEY_CHANNEL_CLOSED`、应急 bypass 放行且审计只落摘要、缺过期时间拒启、`IDENTITY_AUTHORITY=openbase` 本地登录 403 `AUTH_LOCAL_LOGIN_DISABLED`）、OpenRAG/OpenMemory K-01 门禁级 8 项策略全通过；OpenRAG/OpenMemory 整服务启动因本机缺重依赖（OpenRAG 导入原生崩溃）如实 ⛔ Blocked；新增 §9.4/§9.5，更新 §9.3 |
| v1.1.0 | 2026-11-02 | FA-OpenBase-Dev（AI 辅助） | **E1 执行完成（5/5 Pass）**：四仓模板/说明漂移全部补齐（OpenBase `.env.shared-infra` 7 键、OpenRAG/OpenMemory `.env.example` 各 3 键、DPS 环境配置说明 v2.8.3 新增 §2.5/§2.6），并修正 A2 中 DPS 键名前缀笔误；**E2 执行完成（本机口径 Pass）**：以原生 `uvicorn` 单进程（无 Docker）完成 D-02 重启两向验证、A2-01 基线、A2-03 JWKS、A2-02 端点鉴权、A2-06 日志卫生；A2-04/A2-05 与 V 类实测项按 §5 判定边界标 ⛔ Blocked；新增 §9 执行结果 |
| v1.0.0 | 2026-11-02 | FA-OpenBase-Dev（AI 辅助） | 首版：把残余项按「环境依赖」而非编号分为 E1（零环境）/ E2（本机原生）/ E3（生产窗口）/ E4（跨仓与外部 IdP）/ E5（触发式暂缓）五批；明确 D-04→K-01→D-03 串行约束与「不使用 Docker」的 E2 替代路径 |

---

## 1. 目的与原则

**目的**：在不引入 Docker 的前提下，把 32 项残余（5 项生产动作 + 14 项 A1 实测 + 6 项 A2 验收 + 7 项暂缓）按可执行性排序，逐批推进到 `Pass / Fail / Blocked` 的可复现状态。

**分批原则**

1. **按环境依赖分批**，不按编号顺序：同一环境批次内的项一次取证，避免重复搭环境。
2. **硬依赖优先**：`D-04 收敛 → K-01 closed`、`全量 RS256 换发 → D-03`、`E1 模板补齐 → E3 注入`。
3. **无环境项先做**：模板/说明补齐、验收命令脚本化，零外部依赖。
4. **判定只允许 `Pass / Fail / Blocked`**；`Blocked` 必须写明解除条件，不得以本地构造替代生产实测。
5. **秘密零泄漏**：只记键名与「已配置/未配置」，不记值、不落 PEM/证书/令牌原文。

---

## 2. 批次总览

| 批次 | 范围 | 环境前置 | 判定目标 | 产出 |
|---|---|---|---|---|
| **E1 零环境** | D-06 模板漂移 4 处；A1/A2 验收命令可执行化 | 无 | 模板与说明齐备、命令可复跑 | 模板 diff + 验收命令清单 |
| **E2 本机原生（无 Docker）** | D-02 真实重启两向 + 端点核对；V-01/02/03/05/06/07/08/09/10/11/12；A2-01~A2-06 | Python 原生进程 + SQLite + 本机 Redis（可选） | 逐项 Pass/Fail/Blocked | `evidence/a2/`、`evidence/a1/` |
| **E3 生产窗口** | D-04 → K-01 closed → D-03；D-05 注入；D-06 注入与挂载；K-02 `IDENTITY_AUTHORITY=openbase`；A1-04 | 生产会话、DBA 变更单、业务窗口 | 切换前后两向冒烟 | 变更单、收敛记录、回滚清单 |
| **E4 跨仓与外部** | V-04 跨仓时延、V-13 真实 IdP、V-14 四仓实测、D-07 issuer 判重、P-07 | 可达 IdP、四仓生产部署 | 联调与实测结论 | IdP 联调记录、issuer 清单、跨仓矩阵 |
| **E5 触发式暂缓** | P-01~P-06 | 密评/KMS/信创/审计平台立项 | 不排期 | 触发条件登记 |

---

## 3. 硬依赖与顺序

| 约束 | 原因 | 违反后果 |
|---|---|---|
| E1 先于 E3 | 模板漂移不补齐，生产注入无依据 | D-06 无法签核 |
| D-04 先于 K-01 `closed` | 存量 `ob_k_` 未收敛即关静态 Key 主通道 | 业务中断 |
| 全量令牌 RS256 换发先于 D-03 | 存量 HS256 令牌会被拒绝 | 登录面中断 |
| D-05 注入与 D-06 挂载同窗口 | 两者共用发布单与主机操作 | 主体映射缺失即 fail-closed |
| E2 先于 E4 | 本机结论是跨仓实测的基线 | 结论不可比 |

推荐顺序：**E1 → E2 → E3（D-04→K-01→D-03）→ E4 → E5 不启动**。

---

## 4. E1 执行清单（零环境）

| 编号 | 对象 | 动作 | 判定 |
|---|---|---|---|
| E1-① | OpenBase `.env.shared-infra`（未跟踪） | 增补生产基线 7 键（RS256 私钥路径/kid/require、issuer、IdP 登记、MCP 摘要、服务账号主体映射），仅键名与注释，不留真实值 | 7 键存在 |
| E1-② | OpenRAG `.env.example` | 增补 `OPENRAG_API_STATIC_KEY_CHANNEL`（默认 `dual`）与应急 bypass 两键 | 3 键存在 |
| E1-③ | OpenMemory `.env.example` | 增补 `OPENMEMORY_GATEWAY_STATIC_KEY_CHANNEL` 与应急 bypass 两键 | 3 键存在 |
| E1-④ | DPS `doc/release/DPS-环境配置说明` | 增补 `IDENTITY_AUTHORITY`（生产 `openbase`）与 `STATIC_KEY_CHANNEL`（默认 `dual`），升版并记录修订 | 2 键存在 + 升版 |
| E1-⑤ | OpenBase A2 清单 | 修正 DPS 键名前缀误写（`DPS_STATIC_KEY_CHANNEL` → `STATIC_KEY_CHANNEL`），升版 | 键名与 `src/config.py` 一致 |

**验收方式**：按 `evidence/d/d-06-template-key-check-20261101.json` 的键名清单逐项 grep；命令可复跑。

---

## 5. E2 替代路径（不使用 Docker）

| 原依赖 | 本轮替代 | 限制 |
|---|---|---|
| Docker 全栈 | 原生 `uvicorn` 单进程 + SQLite（`OPENBASE_DB_URL` 覆盖为 `sqlite:///...`）+ 进程内 state（Redis 不可用时回落） | 无双实例、无 Redis 共享态 |
| 容器内 JWKS/吊销端点 | 本机 `http://127.0.0.1:<port>/.well-known/jwks.json`、`/api/v1/auth/revocations`、`/api/v1/auth/introspect` | 仅验证本机实例 |
| 容器化负向启动 | 移走 PEM → 原生重启拒启 → 恢复 → 重启成功 | 需可重复启停本机进程 |
| 多实例审计链（V-05） | 延迟到 E3/E4（需共享 PG） | 本机 SQLite 不适用 |

**E2 判定边界**：本机原生结论只作为 `Pass（本机口径）`；凡需共享 PG/Redis、多实例、真实 IdP 的项一律 `Blocked`，解除条件写明。

---

## 6. E3 生产窗口执行清单

| 顺序 | 事项 | 前置 | 通过标准 |
|:--:|---|---|---|
| 1 | D-04 存量 Key 分批收敛 | DBA 会话 + 变更单 | `expires_at IS NULL` 剩余 0 或仅剩批准豁免行 |
| 2 | 观察一个完整 dual 窗口 | 业务确认窗口长度 | 无静态 Key 拒绝异常 |
| 3 | K-01 三仓 `STATIC_KEY_CHANNEL=closed` | 上一步通过 | 关闭态错误码可控、应急 bypass 可放行 |
| 4 | D-03 `jwt_require_rs256=true` | 全量令牌 RS256 换发完成 | HS256 令牌被拒、RS256 正常 |
| 5 | D-05 映射注入 + 两向冒烟 | 发布单 | 映射放行、未映射拒绝 |
| 6 | D-06 注入 + 只读挂载 0600 | E1 完成 | 挂载权限与端点核对记录 |
| 7 | K-02 DPS `IDENTITY_AUTHORITY=openbase` | 发布单 | 本地密码登录 403、仅受理 RS256 |

**回滚开关**：`STATIC_KEY_CHANNEL=dual`、`jwt_require_rs256=false`、`IDENTITY_AUTHORITY=local` 均为无数据迁移回退。

---

## 7. 留痕与门禁

- 每批完成：更新本方案修订历史 + 执行记录；证据落 `evidence/<批次>/`。
- 提交：精确 `git add`，`feat(auth)` 中文提交，推送 origin/backup/github 并 `git ls-remote` 校验。
- 人工门禁：每批完成后需人工批准；仅在「需裁定 / 高影响授权 / 门禁不通过」时回问。

---

## 8. 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 本机资源不足，原生进程启动失败 | E2 整体 Blocked | 降级为「构造期门禁 + 静态核对」，如实登记 |
| github 远程不可达 | 三远程不一致 | origin/backup 先行，github 待网络恢复补推 |
| 生产窗口与业务高峰冲突 | 登录/Key 中断 | 分窗口执行，保留 dual 观察期与回滚开关 |
| DPS 键名前缀误写 | 配置注入无效 | E1-⑤ 修正并复核 `src/config.py` |

---

## 9. 执行结果（2026-11-02）

> 本轮严格**不使用 Docker**；E3 已做「本机生产形态」取证，真实生产切换、E4/E5 未启动（依赖生产会话、DBA 变更单、可达 IdP），仅登记解除条件。

### 9.1 E1（零环境）— 5/5 Pass

| 编号 | 判定 | 证据/说明 |
|---|---|---|
| E1-① | ✅ Pass | `.env.shared-infra` 7 键存在（该文件不被 git 跟踪，真实值由 OPS 注入） |
| E1-② | ✅ Pass | OpenRAG `.env.example` 3 键存在 |
| E1-③ | ✅ Pass | OpenMemory `.env.example` 3 键存在 |
| E1-④ | ✅ Pass | DPS 环境配置说明升 v2.8.3，新增 §2.5/§2.6；键名与 `DPS/src/config.py:200,296` 一致（均无 `DPS_` 前缀） |
| E1-⑤ | ✅ Pass | A2 升 v1.1.6，修正 `DPS_IDENTITY_AUTHORITY`/`DPS_STATIC_KEY_CHANNEL` 笔误 |

证据：`doc/audit/verification/evidence/a2/a2-e1-template-drift-20261102.json`；执行细节见《D 类部署取证执行记录 v1.0.4》§5.1。

### 9.2 E2（本机原生，无 Docker）

| 项 | 判定 | 证据/说明 |
|---|---|---|
| D-02 负向（私钥缺失 → 拒启） | ✅ Pass（本机） | `exit=1`，`JWT RSA 私钥文件不存在或不可读` |
| D-02 正向（恢复 PEM → 启动） | ✅ Pass（本机） | `/health` 200、Uvicorn 正常监听 |
| A2-01 生产基线 | ✅ Pass（本机） | 生产形态 13 项门禁全放行 |
| A2-02 端点鉴权 | ✅ Pass（本机） | 内省/吊销增量无凭证 401 |
| A2-03 JWKS | ✅ Pass（本机） | 200、单 RSA 公钥、kid 一致、无私钥字段 |
| A2-04 / A2-05 | ⛔ Blocked | 需四仓生产部署与真实服务 Key 权限面取样 |
| A2-06 秘密卫生 | ✅ Pass（本机） | 进程日志无 PEM 头、无 JWT 密钥原文 |
| V-01/02/03/05/06/07/09/13/14 | ⛔ Blocked | 需共享 PG/Redis、多实例、四仓联调或真实 IdP |

证据：`evidence/a2/a2-d02-negative-e2native-20261102.json`、`evidence/a2/a2-e2-native-20261102.json`；执行细节见《D 类部署取证执行记录 v1.0.4》§5.2。

**E2 限制如实登记**：本机 SQLite 初始化因 PG 专用 SQL（schema/`setval`）失败，应用自动回退内存模式，故本机结论**不覆盖** DB 相关语义；多实例审计链（V-05）与共享 Redis 场景不适用。

### 9.3 E3/E4/E5

| 批次 | 状态 | 解除条件 |
|---|---|---|
| E3 生产窗口 | ⚠ 本机生产形态已执行（§9.4）；**真实生产切换 ⛔ Blocked** | 生产会话 + DBA 变更单 + 业务窗口；顺序见 §6 |
| E3b OpenLLM R17 补充取证 | ✅ 本机进程级两向已执行（§9.6）；生产 ENV 全门禁与令牌放行已由 **E3c 闭合**（§9.7）；仅吊销增量 ⛔ Blocked | E4 跨仓实测（`openllm_openbase_revocation_sync`） |
| E4 跨仓与外部 | ⛔ 未启动 | 可达 IdP + 四仓生产部署 |
| E5 触发式暂缓 | ⏸ 不启动 | 密评/KMS/信创/审计平台立项 |

### 9.4 E3 本机生产形态结果（2026-11-02）

> 执行方式：`tmp/e3-native/run_e3.py`，原生 `uvicorn` 单进程 + SQLite（DPS `SQLITE_FALLBACK=true`）；本机无 Docker。证据：`evidence/e3/e3-native-20261102.json`。

| 系统 | 事项 | 判定 | 关键观测 |
|---|---|---|---|
| OpenBase | D-03 `jwt_require_rs256=true` 正向 | ✅ Pass（本机） | 生产形态启动 200；JWKS 单 RSA 公钥、`kid=e3-native-kid`、无私钥字段；HS256 令牌访问 `/api/v1/auth/me` → **401** `AUTH_401 invalid or expired token` |
| OpenBase | D-03 负向（缺 RS256 材料） | ✅ Pass（本机） | `jwt_require_rs256=true` 且私钥路径/kid 为空 → `exit=1`，报错 `生产/门禁要求 RS256：必须同时配置 ... 否则拒绝启动` |
| OpenBase | D-05 主体映射 | ✅ Pass（配置口径） | `OPENBASE_SERVICE_ACCOUNT_SUBJECT_MAP` 解析 **1 条**；出站映射两向需真实下游代理，⛔ 留待 E4 |
| OpenBase | D-06 MCP 摘要/密钥文件 | ✅ Pass（本机） | 摘要模式启动 200；密钥文件模式启动 200；生产配置明文 `OPENBASE_MCP_API_KEYS` → `exit=1`（`生产环境禁止配置明文 MCP 静态 Key`） |
| OpenBase | D-06 只读挂载 0600 | ⛔ Blocked | Windows 本机无 POSIX mode，需主机侧挂载操作 |
| DPS | K-01 `closed` 非应急 Key | ✅ Pass（本机） | `GET /api/v2/profiles` + 非应急 `X-API-Key` → **401** `AUTH_STATIC_KEY_CHANNEL_CLOSED` |
| DPS | K-01 应急 bypass | ✅ Pass（本机） | 关闭态 + 应急 Key（未来过期）→ 不再返回关闭码；审计日志 `static_key_emergency_bypass` 出现，日志内**无明文 Key** |
| DPS | K-01 负向（缺过期时间） | ✅ Pass（本机） | 配应急 Key 但 `EMERGENCY_BYPASS_EXPIRES_AT` 为空 → `exit=1`，报错 `K-01 启动门禁：应急通道必须有明确过期时间` |
| DPS | K-02 `IDENTITY_AUTHORITY=openbase` | ✅ Pass（本机） | `POST /api/v1/auth/login` → **403**，响应含 `AUTH_LOCAL_LOGIN_DISABLED`；`/health/liveness` 200 |
| OpenRAG | K-01 策略（门禁级） | ✅ Pass（模块级 8/8） | dual 主通道启用、closed 关闭、非法值归一 dual、应急有效期/过期/错 Key 判定、缺过期拒启、closed+bypass 策略 |
| OpenRAG | 整服务启动 | ⛔ Blocked | 本机缺 aiohttp/qdrant-client/faiss/sentence-transformers，导入期原生崩溃（`0xC0000005`） |
| OpenMemory | K-01 策略（门禁级） | ✅ Pass（模块级 8/8） | 同 OpenRAG 八项全通过 |
| OpenMemory | 整服务启动 | ⛔ Blocked | 缺 qdrant-client/neo4j/sentence-transformers/openai 等重依赖，且需 PG/Redis 共享态 |

### 9.5 判定边界与 Blocked 解除条件

| 项 | 状态 | 解除条件 |
|---|---|---|
| D-04 存量 Key 收敛 | ⛔ Blocked | 生产 DBA 会话 + 变更单，按 `evidence/d/d-04-expired-key-convergence-20261101.sql` 分批执行 |
| D-05 出站映射两向冒烟 | ⛔ Blocked | 真实下游代理可达后做「映射放行 / 未映射拒绝」 |
| D-06 只读挂载 0600 | ⛔ Blocked | 生产主机侧挂载（PEM 0600、禁内联 env） |
| A2-04 四仓镜像矩阵 `iss/aud` | ⛔ Blocked | 四仓同时可达（OpenRAG/OpenMemory 本机不可启动） |
| A2-05 服务 Key 权限面最小化 | ⛔ Blocked | 真实服务 Key 注册表取样 |
| V-04/V-05/V-13 | ⛔ Blocked | 共享 PG/Redis 多实例 + 可达真实 IdP |
| OpenLLM 生产 ENV 全门禁 | ✅ Pass（本机生产基线，见 §9.7） | 已于 E3c 闭合：16 例矩阵 C01 放行 + C02~C16 拒绝、`EXEMPT_OK`、`GATES_OK`、`/health` 200 |
| OpenLLM 接受 OpenBase 令牌 | ✅ Pass（本机口径，见 §9.7）；吊销增量 ⛔ Blocked | E3c 已闭合 RS256 受理与四类负向；`openllm_openbase_revocation_sync` 归 E4 |

**结论**：凡「启动服务即可验证」的门禁与两向语义，已在本机生产形态全部跑通（OpenBase / OpenLLM / DPS / OpenRAG+OpenMemory 策略层）；剩余 Blocked 项均需**生产主机、DBA 变更单、共享中间件、四仓联调或真实 IdP**，不属代码缺口。

### 9.6 E3b OpenLLM R17 身份权威两向结果（2026-11-02）

> 背景：E3（§9.4）未覆盖 OpenLLM——其无 K-01 静态 Key 通道、非签发方，R17 在更早批次（主方案 v1.9.0）已闭合，但此前仅有单测覆盖，缺 DPS K-02 同级的真实进程两向取证。
> 执行方式：`tmp/e3b-openllm/run_e3b.py`，本机原生 `uvicorn` + SQLite（**无 Docker**，`ENV=development`）；证据 `doc/audit/verification/evidence/e3/e3b-openllm-20261102.json`（SHA-256 `370DAA5CA97D342E8FBD4401C1C1EF460091509DB3F5323DE39B1C7EA92D5C61`，7628 B）。

| 编号 | 用例 | 判定 | 关键观测 |
|---|---|---|---|
| N1 | `IDENTITY_AUTHORITY=openbase` 且 `OPENBASE_JWKS_URL` 为空（`lifespan=on` 真实启动） | ✅ Pass | `exit=3`，176.3s；`ValueError: IDENTITY_AUTHORITY=openbase 必须同时配置 OPENBASE_JWKS_URL（R17）…` + `Application startup failed` |
| N2 | `IDENTITY_AUTHORITY=openid`（非法取值） | ✅ Pass | `exit=1`，12.5s；pydantic `ValidationError`「仅允许 'local' 或 'openbase'（R17）」 |
| P1 | `openbase` 正向：`/health` 与本地登录 | ✅ Pass | `/health` **200**；`POST /api/v1/auth/login` → **403**，响应 `{"detail":"身份由 OpenBase 统一管理，本地开户/登录已关闭（R17）"}`；服务端审计同记 403 |
| P2 | `local` 对照：本地登录可达 | ✅ Pass | `/health` **200**；登录 → **401** `{"detail":"用户名或密码错误"}`，响应**不含** R17 文案（门禁可开可关） |
| — | 生产 ENV 全套启动门禁（`SECRET_KEY`/入站身份头/RBAC/租户隔离/豁免行加固） | ✅ Pass（已由 §9.7 E3c 闭合） | 生产基线门禁矩阵 16 例逐例求值 + 合规启动 `GATES_OK` |
| — | OpenBase RS256 令牌在 OpenLLM 放行 | ✅ Pass（已由 §9.7 E3c 闭合）；吊销增量 ⛔ Blocked | RS256 `/api/v1/auth/me` 200 + 四类负向 401；`openllm_openbase_revocation_sync` 归 E4 |

**方法边界（如实声明）**

- N1/N2 为 `lifespan=on` 真实启动：门禁在 `main.py` lifespan 首行无包裹求值，拒绝启动即真实代码路径。
- P1/P2 为 `lifespan=off` 起**真实 uvicorn 进程**：仅跳过插件发现/EdgeRouter/回写恢复等重型自检（本机导入耗时 2–6 分钟且插件发现阶段长尾），路由与鉴权代码路径不变；`/health` 与 `/api/v1/auth/*` 均由真实 HTTP 请求命中。
- R17 门禁与 ENV 无关（`app/core/config.py:1073` 注释），故 development ENV 下取证不削弱结论；但**不替代**生产 ENV 实测。
- 本机首跑曾因客户端读超时 5s 误记为 `null`，已以 curl/urllib 双向复现确认 403 稳定返回后修正脚本（读超时 20s、负向等待 300s），本表结果取自修正后重跑。

### 9.7 E3c：E3b 两项 Blocked 的具体解决（2026-11-02）

> 背景：§9.6 末尾两行（生产 ENV 全套启动门禁 / OpenBase RS256 令牌在 OpenLLM 放行）原判 ⛔ Blocked。本批按用户指令「执行未闭合项的具体解决」以**本机原生 `uvicorn` + SQLite（无 Docker）**、OpenBase 与 OpenLLM 双进程并起完成取证；证据 `doc/audit/verification/evidence/e3/e3c-openllm-20261102.json`（**9804 B**，SHA-256 `E67F523E830DF1E3DAFC8FF76CEA846A05201BBFC2A27289E9E860A7496B3823`）。

| 编号 | 用例 | 判定 | 关键观测 |
|---|---|---|---|
| A1 | 生效配置核对 | ✅ Pass | `EFFECTIVE authority=openbase jwks_configured=1 subject_map_configured=1 trust_local_subject=0`（仅布尔/枚举，不含映射值） |
| A2 | OpenBase 签发 RS256 | ✅ Pass | `alg=RS256`、`kid=e3c-kid`、`iss=openbase`、`aud=openbase-api`、`type=access`、`sub="1"`；JWKS 200、`key_count=1`、`private_fields=[]` |
| A3 | 正向 `/api/v1/auth/me` | ✅ Pass | **200**（1123 ms）；返回 `username=e3c-openbase-user`（`OPENBASE_SUBJECT_MAP` 映射命中） |
| A4 | 负向：未知 kid | ✅ Pass | **401** + WARN「未知 kid：'unknown-kid'」 |
| A5 | 负向：错误签名 | ✅ Pass | **401** + WARN「Signature verification failed」 |
| A6 | 负向：主体未映射 | ✅ Pass | **401** + WARN「主体未映射到本地用户」 |
| A7 | 负向：已过期 | ✅ Pass | **401** + WARN「Signature has expired」 |
| B1 | 门禁矩阵 C01 合规 | ✅ Pass | 生产基线全部门禁变量齐备即放行 |
| B2 | 门禁矩阵 C02~C16 | ✅ Pass | **15/15 逐项拒绝**且消息逐字命中（SECRET_KEY / 入站身份头 / 代理白名单 / RBAC / 租户三项 / 配额 / 豁免行 H1·H5·H6·H7 / Metrics H3 / Health H4 / 文档 H2 / R17） |
| B3 | 豁免行启动断言 | ✅ Pass | `EXEMPT_OK`（routes=5） |
| B4 | 生产 ENV 合规启动 | ✅ Pass | `GATES_OK`（`assert_startup_gates()` + `validate_production_hardening()`） |
| B5 | 运行期健康 | ✅ Pass | `/health` **200**，`status=healthy`、`version=2.19.1` |
| B6 | 本地身份通道 | ✅ Pass | 本地登录 **401**「用户名或密码错误」 |
| C1 | 吊销增量联动 | ⛔ Blocked | `openllm_openbase_revocation_sync`：`OPENBASE_REVOCATIONS_URL` + 服务 Key + 主体状态变更，归 E4 |
| C2 | 生产拓扑实测 | ⛔ Blocked | 共享 PG/Redis、多实例、真实网关，归 E5 |

**方法边界（如实声明）**

- `openllm_openbase_token_accept` 为 `Pass（本机口径）`：签发侧以 `development` ENV + RS256 私钥临时挂载运行；OpenLLM 按 `openbase` 权威真实进程受理，路由与鉴权代码路径不变。
- `openllm_prod_env_smoke` 为 `Pass（本机生产基线）`：门禁矩阵与合规启动均以 `production` ENV 独立求值，**不替代**真实生产 `.env` 注入与共享中间件实测。
- 启动方式为 `lifespan=off` 真实 uvicorn 进程 + bootstrap 显式 `init_db()` 与显式门禁求值（与 `main.py` 生产初始化同源）；两进程均执行 `init_db()` 完成 SQLite `CompatibleUUID` 替换，生产以 PG 原生 UUID 为准。
- 排障留痕：首两轮正向 401 且服务端无日志，根因是取具脚本未把 OpenBase 相关 `env` 透传给启动函数，OpenLLM 以默认 `local` 权威运行、`OPENBASE_JWKS_URL` 为空，命中 `verify_token` 首行 `if not _jwks_url(): return None` 静默返回；修复透传后日志出现 `EFFECTIVE authority=openbase jwks_configured=1`。该静默分支是否补 WARN 建议在 E4 评估，本批不改代码。

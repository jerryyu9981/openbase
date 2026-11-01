# OpenBase 四系统 API Key 优化 —— 残余项分批推进方案

| 项目 | 内容 |
|---|---|
| 文档版本 | v1.1.0 |
| 文档状态 | [Review] |
| 适用环境 | 本机（无 Docker）/ Dev 原生进程 / Pre-Pro / Pro |
| 关联台账 | `doc/audit/verification/OpenBase-四系统APIKey优化-残余项统一处置方案-v1.1.0.md`（§2.1/§5.4/§6/§7/§8/§9.1） |
| 关联清单 | `...-A1生产验收清单-v1.1.4.md`、`...-A2生产配置收口清单-v1.1.6.md` |
| 关联记录 | `...-D类部署取证执行记录-v1.0.1.md`（§5 E 批联动） |
| 约束 | **本轮不使用 Docker**（电脑资源有限）；环境取证以原生进程 + SQLite/本机依赖为限 |
| 编写 | FA-OpenBase-Dev（AI 辅助） |
| 批准 | 待人工批准 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|---|---|---|---|
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

> 本轮严格**不使用 Docker**；E3/E4/E5 未启动（依赖生产会话、DBA 变更单、可达 IdP），仅登记解除条件。

### 9.1 E1（零环境）— 5/5 Pass

| 编号 | 判定 | 证据/说明 |
|---|---|---|
| E1-① | ✅ Pass | `.env.shared-infra` 7 键存在（该文件不被 git 跟踪，真实值由 OPS 注入） |
| E1-② | ✅ Pass | OpenRAG `.env.example` 3 键存在 |
| E1-③ | ✅ Pass | OpenMemory `.env.example` 3 键存在 |
| E1-④ | ✅ Pass | DPS 环境配置说明升 v2.8.3，新增 §2.5/§2.6；键名与 `DPS/src/config.py:200,296` 一致（均无 `DPS_` 前缀） |
| E1-⑤ | ✅ Pass | A2 升 v1.1.6，修正 `DPS_IDENTITY_AUTHORITY`/`DPS_STATIC_KEY_CHANNEL` 笔误 |

证据：`doc/audit/verification/evidence/a2/a2-e1-template-drift-20261102.json`；执行细节见《D 类部署取证执行记录 v1.0.1》§5.1。

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

证据：`evidence/a2/a2-d02-negative-e2native-20261102.json`、`evidence/a2/a2-e2-native-20261102.json`；执行细节见《D 类部署取证执行记录 v1.0.1》§5.2。

**E2 限制如实登记**：本机 SQLite 初始化因 PG 专用 SQL（schema/`setval`）失败，应用自动回退内存模式，故本机结论**不覆盖** DB 相关语义；多实例审计链（V-05）与共享 Redis 场景不适用。

### 9.3 E3/E4/E5

| 批次 | 状态 | 解除条件 |
|---|---|---|
| E3 生产窗口 | ⛔ 未启动 | 生产会话 + DBA 变更单 + 业务窗口；顺序见 §6 |
| E4 跨仓与外部 | ⛔ 未启动 | 可达 IdP + 四仓生产部署 |
| E5 触发式暂缓 | ⏸ 不启动 | 密评/KMS/信创/审计平台立项 |

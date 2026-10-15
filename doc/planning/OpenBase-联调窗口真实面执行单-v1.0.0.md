# OpenBase 联调窗口「真实面」执行单

| 项 | 内容 |
|----|------|
| 文档编号 | OB-PLAN-MTAUTH-REALFACE-EXEC-v1.0.0 |
| 文档版本 | v1.2.0 |
| 状态 | [Approved]（真实面已执行，`overall_pass=true`；RA-06 余项见 §7） |
| 作者 | AA/AT/PM-OpenBase-Dev |
| 创建日期 | 2026-10-15 |
| 存放 | doc/planning/ |
| 定位 | 面向**网络稳定、各服务常驻**的联调环境，执行 MTAUTH **RA-06 五项真实面**与**下游跨租户 A 写 B 读**，回填 S7 台账与走查报告 |
| 上游依据 | 《OpenBase-S7-全域门禁与总收官报告-v1.0.0》§4.2（S7-T6-1/T6-2）、§6（遗留）；《OpenBase-跨仓数据面租户隔离走查报告-v1.0.0》v1.3.1 §5.2/§6.6；《OpenBase-五系统多租户与授权集成总览与续接指南》v1.0.4 §10 |
| 关联脚本 | `scripts/verify_mtauth_realface.ps1` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.2.0 | 2026-10-15 | AA/AT/PM-OpenBase-Dev | **真实面执行完成（沙箱内跑通）**：脚本修复「漏注入 `POSTGRES_URL`」根因后，`-StartServices -IncludeDataPlane` 一条命令 **`overall_pass=true`**（A OIDC IdP ✅ / B 吊销即时性 ✅ 旧 token 401 / C 跨租户 A 写 B 读 ✅ / D 转发链 ✅）；§7 重写为执行结果并**澄清「沙箱网络阻塞」为误判**；归档证据 `doc/test/evidence/manual/mtauth-realface-20261015.json`；状态转 [Approved] |
| v1.1.0 | 2026-10-15 | AA/AT/PM-OpenBase-Dev | 脚本升级为**跨仓一键启动**（`-StartServices`，用沙箱共享解释器 `TRAE SOLO CN\...\vm\tools\python` 可拉起六服务含 OpenLLM）；§7 更新沙箱结论（A/D PASS；B/C 换解释器后同根因仍阻塞 → 证明与解释器无关；SQLite 兜底不可行：`demo_app` 初始化 SQL 为 PG 专用） |
| v1.0.0 | 2026-10-15 | AA/AT/PM-OpenBase-Dev | 初始创建：真实面执行单（范围/前置/步骤/验收判据/证据/风险回滚）+ 沙箱内已取得的部分真实面证据登记 |

---

## 1. 目的与范围

对**沙箱内不可判定**的真实面做一次端到端执行，闭合 S7 PENDING：

| # | 真实面项 | 对应断言 | 说明 |
|:-:|---------|---------|------|
| A | OIDC IdP 真实面 | RA-06（OIDC 批次）/ S7-T6-1 | 真实 IdP 的 discovery 与 JWKS |
| B | 吊销即时性（`token_version`） | RA-06（吊销即时性）/ S6-B4 | 停用主体后旧 token 即时失效（401） |
| C | 双租户数据面（跨租户 A 写 B 读） | S6-B3 / 走查报告 §5.2 | A 租户写入后，B 租户不可见 |
| D | 跨仓转发链 | 走查报告 §3.2 | OpenBase → 下游四仓代理转发可达 |
| E | fail-closed 故障注入 | RA-06（fail-closed） | 下游不可达时按策略 fail-closed（**破坏性，需窗口许可**） |

> **不属本次**（仍按各仓自证/既有台账登记）：K07/SYS-1 端点过滤矩阵、K13 存储账号真实授权、主备切换演练（L2-1）等非本单断言。

## 2. 前置条件（**窗口准入**）

1. **网络稳定**：可稳定访问共享 PG `192.168.0.151:5432`（`nuct`）与 Redis `192.168.0.151:6380`；执行期无连接重置。
   - 判据：`Test-NetConnection 192.168.0.151 -Port 5432` 通过，且连续 10 次 `select 1` 无 `WinError 64`。
2. **服务常驻**（不得随会话回收）：`OpenBase:8000`、`OpenLLM:8001`、`OpenRAG:8010`、`OpenMemory:8020`、`DPS:8030`、`OIDC-IdP:8090`（建议以受管编排 `scripts/service-orchestrator.ps1 -Action startcheck` 拉起并保活）。
3. **凭据/参数**：admin 账号可用（默认 `admin/admin123`，如不同以 `-AdminUser/-AdminPass` 传入）；跨租户用例的两个**已在下游登记**的租户码（默认 `tenant-1`/`tenant-2`，见编排器 `OPENBASE_PROXY_CODE_MAP` 与 `OPENMEMORY_RBAC__ORG_POLICIES`）。
4. **权限/授权**：E 项（故障注入）与其可能引发的写操作须获窗口许可（属破坏性）。
5. **回滚准备**：PG/Redis 连接正常、可回退；临时对象一律带时间戳前缀。

## 3. 执行步骤

> 推荐**一条命令**跑完 A–D（服务未起时加 `-StartServices` 由脚本跨仓一键拉起六服务）：

```powershell
# 跨仓一键：启动 OpenBase/OpenLLM/OpenRAG/OpenMemory/DPS/OIDC-IdP + 全量真实面（含 A 写 B 读）
.\scripts\verify_mtauth_realface.ps1 -StartServices -IncludeDataPlane

# 服务常驻的联调环境：A + B + D
.\scripts\verify_mtauth_realface.ps1

# 含跨租户数据面（A 写 B 读，会创建临时租户/用户/集合，用后清理）
.\scripts\verify_mtauth_realface.ps1 -IncludeDataPlane

# 指定参数
.\scripts\verify_mtauth_realface.ps1 -Base http://127.0.0.1:8000 -Idp http://127.0.0.1:8090 `
    -AdminUser admin -AdminPass ****** -TenantA tenant-1 -TenantB tenant-2 -IncludeDataPlane
```

脚本内部步骤（每步记录 `observed/expected/pass`）：

| 步骤 | 动作 | 期望 |
|------|------|------|
| §1 | `GET {Idp}/.well-known/openid-configuration`、`GET {Idp}/jwks` | 200 / 200 |
| §2 | admin 登录 → 建临时用户 → 该用户登录并 `GET /auth/me` → admin `POST /identity/lifecycle/user/{id}/suspend` → **复用旧 token** `GET /auth/me` | 200 → 200 → 2xx → **401** |
| §2 清理 | `POST /identity/lifecycle/user/{id}/deactivate {confirm:true}` | 2xx |
| §3 | `GET /api/v1/rag-proxy/collections`、`GET /api/v1/memory-proxy/memories` | 200 / 200 |
| §4 | 租户 A 用户 `POST /rag-proxy/collections` → 租户 B 用户 `GET /rag-proxy/collections`、`GET /rag-proxy/collections/{A_id}` | 2xx → **不含 A 集合** → **404/403** |
| §4 清理 | A 用户 `DELETE /rag-proxy/collections/{A_id}` | 2xx |
| §5（E 项，手工） | 停某下游（如 OpenRAG）后经 `rag-proxy` 调用 | 按策略 fail-closed（预期 5xx/503 且不泄露） |

## 4. 验收判据

- **A–D 全 PASS** 记 `overall_pass=true`（脚本输出）。
- **B（吊销即时性）核心判据**：suspend 后**复用旧 token 必须 401**（`tvn` 落后被版本强校验拦截）；不得出现「旧 token 仍 200」。
- **C（A 写 B 读）核心判据**：B 租户**列举不含** A 集合，**直取 A 集合 id 得 404/403**；不得出现跨租户可见/可读。
- 任一 FAIL → 不填 PASS，登记缺陷并按 §6 回滚。

## 5. 证据归集

| 产物 | 路径 |
|------|------|
| 原始证据（JSON，含各步 observed/expected/pass） | `doc/tmp/mtw/realface-<stamp>.json`（临时，不入库） |
| 脱敏后入库证据 | `doc/test/evidence/manual/mtauth-realface-<date>.json`（**禁落 token/密钥/密码明文**） |
| 执行留痕 | 回填《S7 总收官报告》§4.2 与《跨仓数据面租户隔离走查报告》§5.2；同步《续接指南》§10 |

## 6. 风险与回滚

| 风险 | 缓解/回滚 |
|------|----------|
| 共享 PG/Redis 连接瞬态（既有 `DEF-MTAUTH-001`） | 执行前连通性预检（§2.1）；失败即中止，不重试刷写 |
| 临时租户/用户/集合残留 | 一律带时间戳前缀；按 §3 清理步骤停用/删除；失败时人工清理 |
| E 项故障注入影响在跑业务 | 仅在**专用联调窗口**执行；先备份、后恢复；不影响其他使用方 |
| 跨租户数据面误写既有租户 | 仅用**专用临时租户码**（`tenant-1`/`tenant-2` 或窗口指定），禁写既有租户 |

---

## 7. 真实面执行结果（2026-10-15）

> 通过 `scripts/verify_mtauth_realface.ps1 -StartServices -IncludeDataPlane` 在沙箱内**一条命令**完成（跨仓拉起六服务 + RA-06 真实面 + 跨租户 A 写 B 读），**`overall_pass = true`**。证据：`doc/test/evidence/manual/mtauth-realface-20261015.json`。

| 项 | 结果 | observed |
|----|------|----------|
| 跨仓一键启动 | ✅ 六服务（`openllm`/`openbase` 新起，`openrag`/`openmemory`/`dps`/`oidc-idp` 在线复用） | 均 health 200 |
| A OIDC IdP 真实面 | ✅ | discovery=200 / jwks=200 |
| B 吊销即时性（`token_version`） | ✅ | create_user=200 → me=200 → suspend=200 → **旧 token=401** |
| C 跨租户 A 写 B 读 | ✅ | A 建集合=200 → **B 列表不含 A 集合** → **B 直取 A 集合=404** |
| D 跨仓转发链 | ✅ | rag-proxy=200 / memory-proxy=200 |

**关键根因（已修复，**非环境问题**）**：OpenBase 的 DB/Redis DSN **只从进程环境解析**（`POSTGRES_URL` / `REDIS_URL`；`.env` 不参与，见 `openbase/settings.py::_resolve_db_url`），由编排器从 `.env.shared-infra` 注入。脚本首版**漏注入 `POSTGRES_URL`** → `db_url` 回落默认 `localhost:5432` → 所有 DB 写入报 `connection was closed in the middle of operation`（在 app 日志中伴随 `OSError [WinError 64]`）。**修复**：脚本启动前加载 `.env.shared-infra`（与 `service-orchestrator.ps1` 同款）→ **B/C 全绿**。

> **误判澄清**：沙箱网络对共享 PG 本**正常**（短连接 10/10 OK、持连接 idle 15s OK、普通进程 SQLAlchemy+asyncpg 读写正常）。此前「沙箱网络阻塞（WinError 64）」结论**系误判**，根因为脚本缺环境注入；`WinError 64` 源于应用连到 **localhost:5432（无 PG）** 的失败路径。

**仍 PENDING（不在本脚本内）**：E fail-closed 故障注入（破坏性，未做）、RA-06「委托跨界」项、S7-T6-2 冒烟 S0-S6 真实执行、L3-1 agent key 全链路（需 `sk-agent-*`）。

**未决（可后续增强）**：C 项以 `rag-proxy collections` 为跨租户载体（替代「记忆数据面」）；如需覆盖 OpenMemory 记忆面，另加 `memory-proxy /remember|/recall` 用例。

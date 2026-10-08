# OpenBase-R387-跨域租户码对齐设计与收口实施记录-v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 文档编号 | OB-DESIGN-R387-v1.0.0 |
| 批次 | **R387**（承接 R2 立项方案 §3 方案 B「R-387 根因消解」，为 R-387 的**设计与实施记录**） |
| 文档版本 | **v1.1.0**（文件名版本＝首次定稿版本；内容版本以本字段与修订历史承载，与《问题跟踪记录》同法） |
| 状态 | **[Review]**（设计结论已由实测判定；实施已完成并通过全量回归与端到端验收；**统一码空间的全量切换挂起于上游组织登记**，待人工批准与跨仓派单裁定） |
| 作者 | AD-OpenBase-Dev（实现）/ AT-OpenBase-Dev（验证）/ AU-OpenBase-Dev（审计视图） |
| 创建日期 | 2026-10-08 |
| 存放 | 仓库根目录（与既有 R1/P2-1/P2-2/U1 等立项/设计文档同级） |
| 上游依据 | 《OpenBase-R2-RAG写路径M2写拒绝收口立项方案-v1.0.0》§1/§3（`DEF-BE-1410-001`、三方案与推荐）；《OpenBase-CR-147-006-跨仓派单项-v1.0.0》§3.1（R-387 四项交付要求 = 本文 §2/§4/§5/§8）；《OpenBase-问题跟踪记录-v1.4.7》v1.5.5 §2 `CR-147-006`；《OpenBase-候选需求池》§1.16（R-387/R-388） |
| 本次新增证据 | `doc/test/evidence/manual/r387-outbound-header-matrix-20261008.json`（出站头矩阵）；`doc/test/evidence/manual/r387-acceptance-20261008.json`（收口验收） |
| 适用范围 | **本仓（OpenBase）**：`openbase/settings.py`、`openbase/modules/rag_proxy/`、`scripts/service-orchestrator.ps1`、`tests/` 与文档；**未改动** OpenRAG 仓任何文件，**未放宽**其保留码防护语义 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| **v1.3.0** | **2026-10-08** | AD/AT-OpenBase-Dev | **统一码空间终态达成（阻塞项 B1/B2/B3 全部闭环）**：依人工指令「直接跨仓修复」，C1-a 由本仓代为实施 —— 在 `scripts/service-orchestrator.ps1` 登记 `OPENMEMORY_RBAC__ORG_POLICIES`（`default`/`tenant-1`/`tenant-2`，**未改 OpenMemory 仓代码、未放宽其 fail-closed**）；随后**同批切换**本仓三处：memory 兜底码（内置基线 + `OPENBASE_PROXY_CODE_MAP`）、`oidc_default_tenant`（`settings.py` 默认值 **+ `.env` 第 17 行**——`.env` 优先，首轮验收即因漏改 `.env` 失败）、本地 IdP 演示池（新增 `DEMO_TENANT_ID`）；端到端验收 **12/12 PASS**（受信入站 `tenant-1` 403→200；未登记码仍 403；网关记忆读/写/删 200；RAG 不回归）；护栏用例期望值同步并新增兜底码非保留不变量 |
| **v1.2.0** | **2026-10-08** | AD/AT/AU-OpenBase-Dev | **A 批 A1/A2 变更影响登记（`OPENBASE_PROXY_CODE_MAP` 统一登记入口）**：码空间登记由「模块常量 + 2 个散落设置字段」收敛为**单一入口**——内置基线（`OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET` / `BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET`）+ `OPENBASE_PROXY_CODE_MAP` 覆盖，校验统一为 `resolve_target_code_space` / `validate_target_code_space`（启动期 + 运行期二次防线），新增运行期解析 `openbase/modules/protocol_headers/code_space.py`。**因此本文 v1.0.0/v1.1.0 中的 `OPENBASE_RAG_DEFAULT_TENANT_CODE`、`rag_default_tenant_code`、`memory_default_tenant_code` 三个标识已被取代**（详见 §13）；行为等价（兜底值不变），护栏用例已同步迁移至 `tests/test_outbound_tenant_code_space.py` |
| **v1.1.0** | **2026-10-08** | AD/AT/AU-OpenBase-Dev | **统一码空间收口（扩展，§11）**：① 实测各下游**可接受码空间**——OpenMemory 按组织策略 fail-closed，仅登记 `default`，`tenant-1`/`tenant-2` 实测 **403**（新证据 `r387-memory-org-policy-20261008.json`）；② 据此把码空间收口重塑为**「按目标登记」**（新增 `OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET` 单一事实源），并把 memory 目标出站兜底码由写死字面量 `"default"` **外提为配置项** `OPENBASE_MEMORY_DEFAULT_TENANT_CODE`（原值不变）；③ 校验升级为按目标（空值/命中本目标保留码 → 启动即拒），新增护栏 `tests/test_outbound_tenant_code_space.py`（9 例）；④ **登记阻塞项**：memory 目标全量切换与 `oidc_default_tenant`/本地 IdP 演示用户池的保留码消除**均以 OpenMemory 组织登记为前置**（跨仓，另出派单项），本仓**未擅自切换**以免造成记忆链路 403 |
| v1.0.0 | 2026-10-08 | AD/AT/AU-OpenBase-Dev | 初始版本：给出 R-387 **冲突清单**（OpenBase 码空间 vs 上游保留码）、**出站头矩阵实测**（4 形态 × 读/写）、**方案判定**（采纳「出站租户码恒对齐为非保留码」，含 3 方案对比与判定依据）、**触发条件**（T1~T4，覆盖 `CR-147-006` §3.1-3 要求）、**实施改动清单**、**验证结果**（TDD 15 例 / ruff / 全量回归 1124 passed / 端到端验收 5 PASS）、**影响面、回滚与存量数据处置**、**遗留与后续** |

---

## §1 结论摘要

**根因不是「注入身份头」，而是「注入的租户码落在 OpenRAG 保留码上或缺省」。** 出站头矩阵实测（§3）表明：受信入站 + **非保留码**（`tenant-1`）时读、写**同时 200**；而 v1.4.7 的「不注入」（方案 B）会使写类端点恒 403、`default` 或缺省租户码则恒 400。

**收口动作**：rag-proxy 出站租户码**恒对齐为非保留码**（主体码非保留则透传；保留码或缺省 → 兜底为 `OPENBASE_RAG_DEFAULT_TENANT_CODE`，默认 `tenant-1`），并恢复身份头注入；同时把「保留码」约束提升为**启动即校验**的配置护栏与用例护栏。

**验证结果**：TDD 护栏 15 例全绿；`ruff` 0 告警；全量回归 **1124 passed / 0 failed / 4 skipped**；端到端验收 **5/5 PASS**（检索链路由恒 403 转为 **200**）。

---

## §2 冲突清单（`CR-147-006` §3.1 交付要求 1）

| 码空间 | 取值 | 来源 / 语义 | 冲突判定 |
|--------|------|------------|:--------:|
| **OpenRAG 保留码** | `default`、`openrag-local` | 上游实测响应 `detail.reserved_codes`（`BIZ_RESERVED_TENANT_CODE_COLLISION`，`rg_error_code=BIZ-4091`） | **冲突源**：受信入站携带即 400 |
| OpenRAG 存量数据码 | `default` | 存量 12 个知识库 `tenant_code` 全为 `default`（smoke 制品） | **与保留码同名** → 受信入站下不可达（§8.3） |
| **OpenBase `tenants.code`** | `tenant-1`、`tenant-2`（enabled）；`t4walk2224`、`o12b223526`、`o12c223608`（status=0） | `/api/v1/tenants` 实测；为**唯一事实源**（`dps_code_map.py: SOURCE_OF_TRUTH = "openbase.tenants.code"`） | **无冲突**：均非保留码 |
| OpenBase 历史/联调兜底码 | `default` | `settings.oidc_default_tenant = "default"`；`memory_proxy.py:110 default_tenant="default"`；`inject.py:178` 缺省即省略头 | **同名冲突**：与 OpenRAG 保留码同名（RAG 面须消除） |
| OpenBase 平台管理员主体 | `admin`：`tenant_id=null`、`tenant_code=None` | `/api/v1/auth/me` 实测 | **缺省冲突**：出站省略 `X-Tenant-ID` → 上游按保留码处理 |
| 其他三系统目标码空间 | DPS 用 `dps-org-001`/`dps-tenant-001`（登记式映射 `dps_code_map`）；OpenMemory 无保留码防护 | 编排器 `Env` 注释、`dps_code_map.py` | **无冲突**（DPS 已用桥接映射；OpenMemory 无保留码语义） |

> **冲突面收敛为单一结论**：OpenRAG 是唯一设「保留码」语义的下游；本仓必须保证**发往 OpenRAG 的租户码恒为非保留码**。

---

## §3 出站头矩阵实测（判据）

直连 OpenRAG（`http://127.0.0.1:8010/api/v1/collections`，带 `X-API-Key`）逐形态实测读写：

| 变体 | 出站身份头 | 读（GET /collections） | 写（POST /collections） | 结论 |
|:----:|-----------|:---------------------:|:----------------------:|------|
| **V0** | 无（仅 `X-API-Key` + `X-Proxy-Source`）= v1.4.7 方案 B | **200**（12 项） | **403** `PERM_SERVICE_KEY_WRITE_DENIED` | 读通**写断** |
| **V1** | `X-User-ID` + `X-User-Role`，**无租户头** = 开关置 true 时 admin 的真实形态 | **400** | **400** `BIZ_RESERVED_TENANT_CODE_COLLISION` | **缺省即保留码** |
| **V2** | 受信入站 + 非保留码 `tenant-1` | **200**（2 项） | **200**（建库成功） | **读写同时通 = 唯一自洽形态** |
| **V3** | 受信入站 + 保留码 `default`（对照） | 400 | 400 | 锁定保留码契约 |

**判据**：仅 V2 同时满足「读 200 且写 200」。V1 证明**单纯恢复注入并不足够**（缺省租户头会退化为 400）——这正是必须引入「非保留兜底码」的实证理由。

证据：`doc/test/evidence/manual/r387-outbound-header-matrix-20261008.json`（含隔离与零残留断言）。

---

## §4 方案判定（`CR-147-006` §3.1 交付要求 2）

| 方案 | 内容 | 判定依据（优点） | 代价 / 风险 | 结论 |
|:----:|------|----------------|-----------|:----:|
| **① 出站租户码恒对齐为非保留码**（本仓单点） | 保留码/缺省 → 兜底为 `tenants.code` 中的非保留码；恢复注入 | 读写**同时**可用（V2 实测）；**零跨仓改动**；**不放宽**上游防护；改动单点（settings + rag_proxy + 编排器） | 存量 `default` 桶数据在受信入站下不可达（§8.3）；兜底值选取带隔离语义（见下） | ✅ **采纳并已实施** |
| ② 不改本仓，推动上游为受信代理开放保留码白名单 | 上游侧放行 | 保留 12 项可见性 | **削弱上游防护语义**（与 `CR-147-006` §2 边界声明冲突）；跨仓周期长 | ❌ 不采纳 |
| ③ 维持方案 B（不注入）+ 前端写能力降级 | 仅止损 | 零风险 | 写路径**永久不可用**，非终态 | ❌ 不采纳（R2 §3.1 已列为兜底项，不替代终态） |

**兜底值选取依据**：`tenant-1` —— ① 属 `tenants.code` 已登记值（与唯一事实源一致）；② 为 OpenBase 既有「默认兜底租户码」口径（编排器 DPS 映射 `{"tenant-1":"dps-tenant-001"}` 注释）；③ 非保留码（不触发上游 400）。该值为**配置项**（`OPENBASE_RAG_DEFAULT_TENANT_CODE`），如裁定改用其他码空间，为**单值配置变更**，无需改代码。

---

## §5 触发条件（`CR-147-006` §3.1 交付要求 3 更新）

原要求「明确何时必须由方案 B 回到注入模式」。本轮**已回到注入模式**，故触发条件改为「何时需要重新评估本对齐口径」：

| # | 触发事件 | 可观测判据 |
|:-:|---------|-----------|
| **T1′** | OpenBase 侧启用多租户真实隔离（同一部署服务多租户） | `tenants.code` 出现多于一个 enabled 租户，且业务要求按租户隔离知识库 |
| **T2′** | 需要恢复 `default` 桶存量数据可见性 | 业务提出访问既有 `default` 桶知识库的诉求（需上游支持或数据迁移，见 §8.3） |
| **T3′** | OpenRAG 变更保留码集合 | 上游返回的 `detail.reserved_codes` 与 `RAG_RESERVED_TENANT_CODES` 不一致（有护栏用例守） |
| **T4′** | 需要将同一对齐口径扩展至其他 proxy | 其他下游出现同类「码值/主体」判定差异（如 OpenMemory 引入保留码语义） |

---

## §6 实施改动清单（本仓）

| # | 文件 | 性质 | 改动要点 | 关联判据 |
|:-:|------|:----:|---------|---------|
| 1 | `openbase/settings.py` | 修改 | ① 新增模块常量 `RAG_RESERVED_TENANT_CODES = {"default","openrag-local"}`（保留码单一事实源）；② 新增字段 `rag_default_tenant_code: str = "tenant-1"`；③ 新增 `@model_validator _validate_rag_tenant_alignment`（空值/保留码 → 启动即 ValueError）；④ 重写 `rag_inject_identity_headers` 注释（明确其为应急回滚杠杆） | §3 V2 / §4 ① |
| 2 | `openbase/modules/rag_proxy/__init__.py` | 修改 | ① 新增 `_rag_tenant_alignment()`（返回兜底码 + 「保留码→兜底码」映射，非法配置 → `BaseError(PARAM_INVALID)` 运行期二次防线）；② `_build_upstream_headers` 传入 `default_tenant` / `tenant_value_map` / `org_value_map`（复用既有装配点，不改 `inject.py`）；③ 更新函数与模块注释 | §3 V1/V2 |
| 3 | `scripts/service-orchestrator.ps1` | 修改 | 撤销 `OPENBASE_RAG_INJECT_IDENTITY_HEADERS='false'` 声明（恢复注入），改为显式声明 `OPENBASE_RAG_DEFAULT_TENANT_CODE='tenant-1'`，并载明根因与约束 | §4 / §7.4 |
| 4 | `tests/test_rag_proxy_identity_policy.py` | 重写 | 10 例：保留码契约、非保留码透传、保留码归一、缺省兜底、非法兜底 fail-closed、settings 拒绝保留码/空值、回滚杠杆 2 例 | TDD RED→GREEN |
| 5 | `tests/test_bl147_trust_env_wiring.py` | 修改 | `test_openbase_declares_rag_tenant_alignment_policy`：① 编排器**不得**再声明注入关闭（判据锚定赋值行，注释提及不算违规）；② 须声明非保留兜底码 | §7.4 |
| 6 | `doc/test/evidence/manual/r387-outbound-header-matrix-20261008.json` | 新增 | 出站头矩阵 + 根因链 + 隔离/零残留 + 后果登记 | §3 |
| 7 | `doc/test/evidence/manual/r387-acceptance-20261008.json` | 新增 | 收口验收（读/建/检索/删/回读） | §7.4 |
| 8 | 本文件 | 新增 | R-387 设计与收口实施记录 | 全篇 |

---

## §7 验证结果

### 7.1 TDD（RED → GREEN）

| 阶段 | 结果 |
|------|------|
| RED | 两测试模块收集期即失败（`ImportError: cannot import name 'RAG_RESERVED_TENANT_CODES'`）——证明新护栏确实约束未实现行为 |
| GREEN | `pytest tests/test_rag_proxy_identity_policy.py tests/test_bl147_trust_env_wiring.py` → **15 passed** |

### 7.2 静态质量

`python -m ruff check openbase tests` → **All checks passed!**（0 告警）

### 7.3 全量回归

`python scripts/run_regression.py`（分组子进程隔离，规避 TD-新增-009）：

| 指标 | 结果 |
|------|------|
| 汇总 | **passed=1124  failed=0  skipped=4** |
| 涉及改动面分组 | `test_rag_proxy_identity_policy.py` 组 **19 passed**；`test_bl147_trust_env_wiring.py` 组 **20 passed**；`test_rag_proxy.py` 组 **44 passed**；`test_org_alias_code / test_protocol_headers_lib` 组 **53 passed** |
| 跳过项 | 4（`test_storage_s3_real.py`，既有环境依赖跳过，非本次引入） |

### 7.4 端到端验收（经网关，重启后）

| 步骤 | 端点 | 结果 |
|:----:|------|------|
| A1 | `GET /api/v1/rag-proxy/collections` | **200**，可见 2 项，`tenant_code=['tenant-1']` |
| A2 | `POST /api/v1/rag-proxy/collections` | **200**，`tenant_code=tenant-1` |
| A3 | `POST .../collections/{id}/query/retrieve` | **200**（**此前恒 403** —— 缺陷已消解） |
| A4 | `DELETE .../collections/{id}` | **200** |
| A5 | 回读列表 | **200**，已不含探针（零残留） |

**汇总：5/5 PASS**。证据：`doc/test/evidence/manual/r387-acceptance-20261008.json`。

---

## §8 影响面、回滚与存量数据处置

### 8.1 影响面

| 面 | 说明 |
|----|------|
| 生效范围 | **仅 rag-proxy 出站**（其余三 proxy 与通用通道未改） |
| 行为变化 | ① 恢复注入四头（`X-User-ID` / `X-Tenant-ID` / `X-Org-ID` / `X-User-Role` + 来源 + request_id）；② 租户码经对齐后恒为非保留码 |
| 上游改动 | **零**（未改 OpenRAG；保留码防护语义未放宽） |
| 隔离语义 | 读、写落在**同一非保留租户桶**（自洽）；跨租户隔离由租户码承载，与既有 `tenants.code` 口径一致 |

### 8.2 回滚

| 场景 | 动作 | 效果 |
|------|------|------|
| 应急回滚到 v1.4.7 方案 B | 置 `OPENBASE_RAG_INJECT_IDENTITY_HEADERS=false` | 回到「读通写断」（写类 403），**无需改代码/回滚数据** |
| 更换兜底码空间 | 改 `OPENBASE_RAG_DEFAULT_TENANT_CODE` 为其他 `tenants.code` 非保留码 | 读写切换到该租户桶（单值配置变更） |

### 8.3 存量数据处置（**显式登记，需裁定**）

| 项 | 内容 |
|----|------|
| 事实 | OpenRAG 存量 **12** 个知识库 `tenant_code` 全为保留码 `default`（均为 smoke 制品：`smoke_v*_kb_*` / `smoke_kb_*` / 1 个空库「技术文档」） |
| 受信入站下可达性 | **不可达**（保留码禁止入站；上游无「受信代理可携带保留码」通道） |
| 本次处置 | **不迁移、不删除**（零数据操作 → 完全可逆）；读视图由 `default` 桶切换为 `tenant-1` 桶（当前 2 项） |
| 备选（待裁定） | 若需保留这 12 项可见性，须由 OpenRAG 侧执行数据迁移（`tenant_code: default → tenant-1`）或新增受信白名单——前者属跨仓数据操作，后者削弱防护，**均不在本次范围** |
| 风险评级 | 低（制品非业务数据；且可经 §8.2 一键回滚还原可见性） |

---

## §9 遗留与后续

| # | 事项 | 说明 | 建议 |
|:-:|------|------|------|
| 1 | `memory_proxy.py:110` 原写死 `default_tenant="default"` | **v1.1.0 已处置**：外提为 `OPENBASE_MEMORY_DEFAULT_TENANT_CODE`（配置项，原值不变），并纳入按目标校验 | 见 §11 |
| 2 | `settings.oidc_default_tenant = "default"` | **v1.1.0 已登记为阻塞项**：消除该保留码会使命主租户声明变为 `tenant-1`，进而使**记忆链路 403**（OpenMemory 未登记该组织）→ 须与上游组织登记同批切换 | 见 §11.4 |
| 3 | R-388（OpenRAG 拒绝路径结构化日志） | 与本轮独立；**本轮排障仍依赖响应体 `detail`**（上游已含 `reserved_codes`，可观测性尚可） | 维持既有派单，不因本轮调整 |
| 4 | 编码 3~7 号写类端点逐条实测 | 本轮端到端已覆盖「建库 + 检索 + 删库」；上传/删文档/问答/流式问答为同出口同机制 | 视需要补测 |

---

## §11 统一码空间收口（v1.1.0 扩展）

> 触发：人工指令「纳入统一码空间收口」（2026-10-08）。目标＝把 §9 遗留项纳入同一收口框架。
> 结论：**统一码空间不能是「单一码值硬套」**——各下游的可接受码空间不同；收口形态＝
> **按目标登记 + 单一校验入口 + 可一处切换**，并在上游未登记前**不擅自切换**。

### 11.1 各目标可接受码空间实测

| 目标 | 语义 | 实测可接受 | 实测拒绝 | 依据 |
|------|------|-----------|---------|------|
| **OpenRAG** | 受信入站禁**保留码** | 非保留码（`tenant-1` 读写均 200） | `default`/`openrag-local` → **400** | §3 矩阵 |
| **OpenMemory** | 按**组织策略** fail-closed | `default`、无租户头 → 200 | `tenant-1`/`tenant-2` → **403「组织不存在或未配置策略」** | `r387-memory-org-policy-20261008.json`（新增） |
| **OpenLLM** | 未声明保留码语义 | 非空码 | — | 代码核对 + 编排器受信白名单 |
| **DPS** | 登记式映射 `dps_code_map`（目标空间码值） | `tenants.code` 已登记码 | 未登记码（其自身映射/校验） | `dps_code_map.py`、编排器 `Env` |

**关键结论**：`default` 对 OpenRAG 是**禁用保留码**，对 OpenMemory 却是**唯一已登记组织码**——同一码值在两侧语义相反。故「统一」必须按目标登记，不能全局二选一。

### 11.2 落地改动（本仓）

| # | 文件 | 性质 | 改动要点 |
|:-:|------|:----:|---------|
| 1 | `openbase/settings.py` | 修改 | ① 新增 `OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET`（**按目标登记的保留码单一事实源**；rag 非空、memory/llm/dps 为空集），`RAG_RESERVED_TENANT_CODES` 改为指向登记表的别名；② 新增 `memory_default_tenant_code: str = "default"`（把 `memory_proxy` 的写死字面量外提为配置项，**原值不变**）；③ 校验器由「仅 RAG」升级为 **`_validate_outbound_tenant_alignment`（按目标：非空 + 不命中本目标保留码）** |
| 2 | `openbase/modules/proxy/memory_proxy.py` | 修改 | `default_tenant="default"` → `default_tenant=settings.memory_default_tenant_code`；docstring 补「该值受上游组织注册约束」警示 |
| 3 | `tests/test_outbound_tenant_code_space.py` | 新增 | 9 例护栏：按目标登记结构、别名指向登记表、memory 出站可配置（改配置即改出站值）、默认值行为不变、主体码透传、空值/命中本目标保留码拒止、`default` 对 memory 合法 |
| 4 | `doc/test/evidence/manual/r387-memory-org-policy-20261008.json` | 新增 | OpenMemory 组织策略实测（可接受/拒绝码空间） |
| 5 | `doc/planning/OpenBase-R387-派单-OpenMemory组织码登记-v1.0.0.md` | 新增 | 跨仓派单项：请 OpenMemory 侧登记目标组织码（解锁全量统一） |

### 11.3 验证

| 项 | 结果 |
|----|------|
| TDD | 新增护栏 9 例（`tests/test_outbound_tenant_code_space.py`）；连同 RAG/bl147/memory 相关用例定向执行合计 **40 passed** |
| 静态质量 | `ruff check openbase tests` → **All checks passed!** |
| 全量回归 | `run_regression.py` → **passed=1133  failed=0  skipped=4**（较 v1.0.0 基线 1124 +9，即本次新增护栏；跳过项 4 为既有 `test_storage_s3_real` 环境依赖） |
| 端到端 | memory 判据不变（默认值仍为 `default`）→ 记忆链路行为零变化（未重启验证；该改动为等值外提，行为由 §11.2 #3 护栏锁定）；RAG 判据见 §7.4 |

### 11.4 阻塞项（跨仓前置，**需裁定**）

| # | 阻塞项 | 说明 | 解锁动作 |
|:-:|--------|------|---------|
| B1 | **OpenMemory 组织码未登记** | 实测 `tenant-1`/`tenant-2` → 403。故 memory 目标的兜底码曾只能是 `default`，全量统一须上游登记该组织 | ✅ **已闭环（2026-10-08，C1-a）**：在 `scripts/service-orchestrator.ps1` 登记 `OPENMEMORY_RBAC__ORG_POLICIES`（`default`/`tenant-1`/`tenant-2`），未改上游代码、未放宽 fail-closed；实测 `tenant-1` → 200、未登记码仍 403 |
| B2 | `oidc_default_tenant = "default"` | 与 B1 强耦合：改为非保留码会使命主租户声明变为 `tenant-1` → 记忆链路即时 403 | ✅ **已同批切换**：`settings.py` 默认值 + **`.env` 第 17 行**（`.env` 优先，仅改代码无效）→ `tenant-1` |
| B3 | 本地 OIDC IdP 演示用户池 `tenant_id="default"` | 同上：演示用户登入后租户声明为保留码 | ✅ **已同批对齐**：`scripts/oidc-idp/idp_server.py` 新增单点常量 `DEMO_TENANT_ID="tenant-1"` |

> **终态达成（2026-10-08）**：B1/B2/B3 全部闭环 → 身份空间与各目标空间的租户码**统一为非保留码 `tenant-1`**（rag/memory 兜底码一致），保留码 `default` 不再由本仓产出。验收：`doc/test/evidence/manual/c1-acceptance-20261008.json`（12/12 PASS）。

**本仓处置立场（已履行完毕）**：B1 未闭环前**未**擅自切换 memory 码值、**未**改 `oidc_default_tenant`、**未**改演示用户池——避免把「码空间不统一」的登记问题变成「记忆链路不可用」的运行故障。B1 闭环（2026-10-08）后即按 §11.6 终态路线**同批切换**（三处单点配置，均有回滚；端到端 12/12 PASS）。

### 11.5 全量回归复跑（v1.1.0 改动后实测）

`python scripts/run_regression.py` → **passed=1133  failed=0  skipped=4**，`[OK] 全量回归通过（TD-新增-009 脚本化回归）`；`ruff check openbase tests` → **All checks passed!**（较 v1.0.0 基线 1124 +9 例，即本次新增护栏用例）。

### 11.6 终态路线

```
[B1 上游登记 tenant-1] ─┐
                        ├─► 同批切换：memory 兜底码 + oidc_default_tenant + IdP 演示池
[B2/B3 依赖 B1] ────────┘        └─► 全仓单一非保留码空间（除 rag 归一映射外无需分支）
```

---

## §12 附录：证据清单

| 证据文件 | 覆盖内容 |
|---------|---------|
| `doc/test/evidence/manual/r387-outbound-header-matrix-20261008.json` | 出站头矩阵（V0~V3）、保留码契约、根因链、隔离与零残留、后果登记 |
| `doc/test/evidence/manual/r387-acceptance-20261008.json` | 收口验收 5 步（读 / 建 / 检索 / 删 / 回读） |
| `doc/test/evidence/manual/r387-memory-org-policy-20261008.json` | OpenMemory 组织策略实测（可接受码空间：`default` / 无租户头；拒绝 `tenant-1`/`tenant-2` → 403） |
| `doc/test/evidence/manual/t4-link-chain-verify-20261008.json` | 收口前读链路基线（32 条，FAIL 1 = 本缺陷） |
| `doc/test/evidence/manual/t4-write-chain-isolated-20261008.json` | 收口前写链路基线（14 步，FAIL 1 = 本缺陷） |
| `doc/test/evidence/v147/def005-multiprobe-20260920.json` | 历史口径基线（v1.4.7 方案 A/B 对照） |

---

## §13 A 批 A1/A2 变更影响登记（v1.2.0）

依据《OpenBase-自研系统多租户与授权集成总体完善方案》§6 A 批（A1/A2），本仓把「出站租户码空间」的登记收敛为**单一入口**，本文 v1.0.0/v1.1.0 中的标识随之**被取代**。

### 13.1 标识取代对照

| v1.0.0 / v1.1.0 中的标识 | 现状态 | 取代者 |
|------------------------|:------:|--------|
| `rag_default_tenant_code`（settings 字段） | **已移除** | `proxy_code_map` 覆盖表 + `BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET["rag"]` |
| `memory_default_tenant_code`（settings 字段） | **已移除** | `proxy_code_map` 覆盖表 + `BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET["memory"]` |
| `OPENBASE_RAG_DEFAULT_TENANT_CODE`（编排器 env） | **已移除** | `OPENBASE_PROXY_CODE_MAP`（JSON，含 `targets.rag` / `targets.memory`） |
| `RAG_RESERVED_TENANT_CODES` | **保留**（别名） | `OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET["rag"]` |

### 13.2 新增/变更落点

| 文件 | 性质 | 要点 |
|------|:----:|------|
| `openbase/settings.py` | 修改 | 新增 `BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET`、`proxy_code_map` 字段与三个纯函数（`parse_proxy_code_map` / `resolve_target_code_space` / `validate_target_code_space`）；校验器改为调用纯函数；移除两个 `*_default_tenant_code` 字段 |
| `openbase/modules/protocol_headers/code_space.py` | **新增** | 运行期解析单一入口：`get_target_code_space(target)` / `reserved_tenant_map(target)` / `TargetCodeSpace`，含运行期二次防线（`BaseError`） |
| `openbase/modules/rag_proxy/__init__.py` | 修改 | `_rag_tenant_alignment()` 改由 `code_space` 取值（不再读散落字段） |
| `openbase/modules/proxy/memory_proxy.py` | 修改 | 改为 `get_target_code_space("memory")`；并补 `reserved_map` 归一（当前为空表，等价无操作） |
| `scripts/service-orchestrator.ps1` | 修改 | 撤 `OPENBASE_RAG_DEFAULT_TENANT_CODE`，改显式声明 `OPENBASE_PROXY_CODE_MAP` |
| `tests/test_outbound_tenant_code_space.py` | 重写 | 25 例：内置基线 / 覆盖语义 / 启动期与运行期护栏 / 两 proxy 出站行为 |
| `tests/test_rag_proxy_identity_policy.py`、`tests/test_bl147_trust_env_wiring.py` | 修改 | 兜底注入改经登记入口；编排器护栏改为解析 `OPENBASE_PROXY_CODE_MAP` 并校验非保留 |

### 13.3 行为等价性声明

内置基线的兜底值与 A 批前**逐项相同**（rag=`tenant-1`、memory=`default`），故**行为零变化**；`proxy_code_map` 为空时的解析结果等于内置基线（已有用例锁定）。存量文档中的旧标识仅需按 §13.1 对照替换。

### 13.4 与 A 批其余项的衔接

A3（`config/role_tier_anchors.json`）与 A4（`config/error_code_map.json`）已产出并由 `tests/test_auth_registries.py` 校验；A5（协议头规范契约与开关默认值统一）待后续文档修订批次承接。

# OpenBase DevLogReport - v1.4.7

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.7（四仓日志接入补完 · 日志域收官 · 跨仓，**承接型小版本**） |
| 文档版本 | v1.2.1 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-09-19 |
| 存放 | doc/development/ |

---

## 1. 版本记录与入场检查（3.0）

| 项 | 内容 |
|----|------|
| 开发范围 | **BL-147-04**（**本仓侧**：编排器采集文件命名对齐 + 归档命名缺陷修复 + 命名实测动作）及其配套测试与文档；BL-147-01/02/03 为**四仓侧**交付（本报告仅登记回执与状态，不含四仓代码）；BL-147-05（端到端串联验收）**未执行** |
| 版本性质 | **承接型小版本**：不引入新主题，只把 v1.4.6 未达成的 R-384 余项收口（闭合 v1.4.6 Phase 6 门禁与里程碑 M10/M11）；Step 1/2 以**差异化确认**为主（不重新论证已批准的 R-384 需求本体） |
| 设计输入 | 《OpenBase-R384四仓施工派单-v1.0.0》（内部 v1.3.0，§7 采集侧施工单）、《OpenBase-R384改动包-v1.0.0》（内部 v1.2.0）、《OpenBase-R384四仓日志接入覆盖状态说明-v1.4.6》（内部 v1.3.0）、《OpenBase-单版本规划文档-v1.4.7》、《OpenBase-Phase迭代计划-v1.4.7》、《OpenBase-本版本Backlog-v1.4.7》 |
| 入场确认 | v1.4.7 Stage 0 版本规划审计**通过**（2026-09-16，AU-OpenBase-Ops，追溯链 100%／产出物 9/9／检查点 8/8／P0 覆盖 4/4／还债 20% ≥ 15%）✅ |
| 基线 | v1.4.6（**已发布**：代码提交 `bfc0572` + tag `v1.4.6` 双远程证据）；本版本基于 `main` 直发 |
| 变更面约束 | **无 DB schema 变更、无接口契约变更、无新增三方依赖**；本仓改动集中在 `scripts/`、`tests/` 与 `openbase/modules/logs/repository.py`（仅命名契约注释 + 公开常量导出，**正则本体未变更**） |
| 回滚方式 | 代码回退（`git revert`）即可；采集命名回归旧口径不影响历史文件可读性（旧 `.log` / `.err.log` 仍在适配器白名单内） |

## 2. 任务拆解与追溯（3.1 / 3.2）

| # | 子任务 | 关联 BL | 交付物 | 判据来源 |
|:-:|-------|---------|--------|---------|
| 1 | 编排器采集文件命名对齐（结构化流 `.jsonl`） | BL-147-04 | `scripts/service-orchestrator.ps1` | 《施工派单》§5 文件命名契约、§7 采集侧施工单 |
| 2 | **归档命名缺陷修复**（时间戳须在 `.err` 之前） | BL-147-04 | 同上（`Get-ServiceLogArchiveName`） | `RepoLogAdapter` 白名单 `REPO_LOG_NAME_RE`（反向验证） |
| 3 | 命名单点抽取（可测、可复用） | BL-147-04 | 同上（`Get-ServiceLogFileName` / `Get-ServiceLogArchiveName`） | 同上 |
| 4 | 命名实测工具（判据不复刻） | BL-147-04 | `scripts/verify_repo_log_naming.py`（新增） | 引用适配器白名单常量，禁复刻正则 |
| 5 | 命名实测动作（读侧零副作用） | BL-147-04 | `scripts/service-orchestrator.ps1`（`-Action namecheck`）+ `Test-ServiceLogArchiveSelfCheck` | Phase 2 §2.1 交付物「编排器改造 + **命名实测**」 |
| 6 | 单测（TDD） | BL-147-04 | `tests/test_r384_repo_log_naming.py`（新增 13 例） | 项目规约：新增代码须有测试，覆盖率 ≥ 90% |
| 7 | 存量测试日期腐化修复（回归面暴露） | 支撑 BL-147-05 回归面 | `tests/test_logs_service.py`（3 处 fixture） | 本报告 §4.3 根因与 A/B 证据 |

## 3. 实现内容（3.3）

### 3.1 采集文件命名契约（v1.4.7 口径）

**唯一判据** = `openbase/modules/logs/repository.py::REPO_LOG_NAME_RE`（`RepoLogAdapter` 文件名白名单）：

| 流类型 | 服务（svc） | 采集文件（当日） | 归档（同日重复启动） |
|--------|------------|-----------------|---------------------|
| **结构化流为 stdout** | `openrag` | `openrag-YYYYMMDD.jsonl` | `openrag-YYYYMMDD-HHmmss.jsonl` |
| 非结构化流（stderr） | `openrag` | `openrag-YYYYMMDD.err.log` | `openrag-YYYYMMDD-HHmmss.err.log` |
| **结构化流为 stderr** | `dps` / `openllm` / `openmemory` | `{svc}-YYYYMMDD.err.jsonl` | `{svc}-YYYYMMDD-HHmmss.err.jsonl` |
| 非结构化流（stdout） | `dps` / `openllm` / `openmemory` | `{svc}-YYYYMMDD.log` | `{svc}-YYYYMMDD-HHmmss.log` |
| 未声明结构化（不变） | `openbase` / `frontend` / `oidc-idp` | `{svc}-YYYYMMDD.log` / `.err.log` | `{svc}-YYYYMMDD-HHmmss(.err).log` |

> 「结构化流」由服务定义中的 `JsonStream` 声明（`openrag=stdout`；`dps`/`openllm`/`openmemory=stderr`，与《施工派单》§4「输出流维持现状」一致：三仓应用日志写 stderr、OpenRAG 写 stdout）。
> `openbase` 的 stdout 采集文件**刻意不改名**为 `.jsonl`：其同目录下已存在 C-1 自落的 `openbase-YYYYMMDD.jsonl`（L1 结构化日志），改名会被 `Start-Process` 重定向**覆盖**而毁掉 L1 证据；且 `openbase` 不是 `repo_log` 源（不受四仓白名单约束）。

### 3.2 归档命名缺陷修复（根因与前后对照）

| 项 | 内容 |
|----|------|
| 现象 | 同日重复启动时，`stderr` 采集文件的归档名形如 `{svc}-YYYYMMDD.err-HHmmss.log` |
| 根因 | 旧实现用 `[IO.Path]::GetFileNameWithoutExtension($path)` 取茎（得到 `dps-20260916.err`）再追加 `-HHmmss.log`，使时间戳落在 `.err` **之后**；而白名单正则要求 `^svc-YYYYMMDD(-HHmmss)?(\.err)?\.(jsonl|log)$` → 该类文件**不匹配**，被 `RepoLogAdapter._day_files` 按目录扫描时**静默跳过**（日志中心看不到历史归档） |
| 处置 | 归档名改为 `{base}-{HHmmss}{.err}{ext}`（时间戳置于 `.err` **之前**、保留原扩展名） |
| 对照 | 旧：`dps-20260916.err-155700.log`（❌ 不可见）→ 新：`dps-20260916-155700.err.log`（✅ 可见） |
| 遗留 | 在盘历史文件（如 `logs/openrag/openrag-20260914.err-220336.log`）仍为旧形态、**修复前后同样不可见**（非本次引入的回退）；`-Action namecheck` 在盘扫描将其单列为 `legacy`，不阻断 |

### 3.3 文件级变更表

| 文件 | 变更 | 说明 |
|------|------|------|
| `scripts/service-orchestrator.ps1` | 修改 | ① 四仓服务定义新增 `JsonStream`（`stdout`×1 / `stderr`×3）；② 新增 `Get-ServiceLogFileName`（当日命名）与 `Get-ServiceLogArchiveName`（归档命名，含 `.err` 位置修正）；③ `Initialize-ServiceLogTarget` 改用上述单点；④ 新增 `-Action namecheck` + `Test-ServiceLogArchiveSelfCheck`（临时目录内实跑归档路径）；⑤ 文件头命名契约与用法示例同步；⑥ `ValidateSet` 增列 `namecheck` |
| `openbase/modules/logs/repository.py` | 修改 | 新增公开常量 `REPO_LOG_NAME_RE`（= `_REPO_NAME_RE` 的**公开别名**，供命名实测工具与测试复用，避免口径漂移）+ `__all__` 导出 + 命名契约注释刷新。**正则本体与适配器行为零变更** |
| `scripts/verify_repo_log_naming.py` | 新建 | 命名白名单校验工具：① `--file <svc>/<basename>` 逐条判定（`ok`/`skipped`/`failed`/`legacy`）；② `--logs-root` 在盘实测扫描；③ `--tolerate-legacy-err-archive` 把修复前旧归档名记为 `legacy`；退出码 0/1/2 |
| `tests/test_r384_repo_log_naming.py` | 新建 | 13 例：四仓结构化/非结构化命名与归档全通过；反例（时间戳位置错误 / svc 段与目录不一致 / 扩展名越界 / 非法日期 / 裸文件名）；非 repo_log 源目录 skipped；在盘扫描与 `legacy` 容差；CLI 退出码；编排器结构护栏（`namecheck` + 四仓 `JsonStream` 声明计数） |
| `tests/test_logs_service.py` | 修改 | 3 处 fixture 由硬编码 `openbase-20260915.jsonl` 改为 `f"openbase-{TODAY}.jsonl"`（与该文件既有 `TODAY` 动态口径一致，见 §4.3） |

### 3.4 未变更声明（防止过度解读）

- **未改动**启停/健康检查/拓扑/`-Only`/`-FromMonitor` 语义，与 C-6 引入时的约束一致（仅改「子进程输出去向文件名」）。
- **未改动** `RepoLogAdapter` 的正则、解析、扫描窗口与脱敏口径。
- **未改动**任何四仓代码（四仓以其仓内流程独立实施与发布；本报告不代述他仓改动）。
- **未引入** uvicorn 访问日志结构化（该部分需四仓侧统一日志配置，见 §5）。

### 3.5 增量 2：DEF-BE-147-005 修复（2026-09-20，v1.2.0 增补）

| 项 | 内容 |
|----|------|
| 触发 | BL-147-05 验收残留 P1 缺陷 **DEF-BE-147-005**：启用 OpenRAG M2 受信模式后，`rag-proxy/collections` 由 **200 → 400** |
| 根因 | OpenRAG `api/middleware/identity_gate.py` L224–239「保留租户码碰撞」防护：M2 受信路径下 `X-Tenant-ID` **缺省即本地保留码 `default`** → 400 `BIZ_RESERVED_TENANT_CODE_COLLISION` |
| 决策证据（多口径 + A/B 实测） | **方案 A**（非保留租户码）→ 200 但 `data.items=[]`（租户隔离致既有知识库不可见）；**方案 B**（不注入身份头）→ 200 且数据完整。证据 `doc/test/evidence/v147/def005-multiprobe-20260920.json` |
| 裁定 | **方案 B**（本仓单点，**未改他仓代码**）；OpenRAG 侧四维身份采纳按「显式声明」降级（非静默），「跨域租户码语义对齐」升级为跨仓/设计议题（CR-147-006） |

**文件级变更表（增量 2）**：

| 文件 | 变更 | 说明 |
|------|------|------|
| `openbase/settings.py` | 修改 | 新增 `rag_inject_identity_headers: bool = True`：默认 `True` **保持既有四维身份透传语义**；置 `False` 即「不注入身份头」 |
| `openbase/modules/rag_proxy/__init__.py` | 修改 | `_build_upstream_headers` 消费该开关：关闭时以 `user_ctx=None` 走**同一装配点**（仍产出 `X-Proxy-Source` + `X-Request-Id`），**不另起旁路装配**（避免口径分叉） |
| `scripts/service-orchestrator.ps1` | 修改 | openbase `Env` 新增 `OPENBASE_RAG_INJECT_IDENTITY_HEADERS = 'false'`（联调口径**显式声明**；含根因/证据/回退路径注释） |
| `tests/test_rag_proxy_identity_policy.py` | 新建 | 3 例：① 默认注入四头 ② 关闭不注入四头 ③ **关闭仍携带 `X-Request-Id`**（串联契约不可回退） |
| `tests/test_bl147_trust_env_wiring.py` | 修改 | +1 例编排器护栏：openbase 块须声明 `OPENBASE_RAG_INJECT_IDENTITY_HEADERS = 'false'`（防口径被无意改回） |

**未变更声明（增量 2）**：未改四仓代码（含 OpenRAG）；未改 `build_outbound_headers` 的装配语义（仅其入参 `user_ctx` 由策略决定）；无 DB schema / 接口契约 / 依赖变更。

## 4. 验证与证据（3.4）

### 4.1 单测（TDD：先 RED 后 GREEN）

- 新增 `tests/test_r384_repo_log_naming.py`：初次运行 **12 failed**（被测脚本不存在 + 编排器缺 `namecheck`）→ 实现后 **13 passed**。
- 新增用例同时覆盖**反例**（旧归档命名、svc 段错位、非法日期、扩展名越界），确保「不可见」形态不会被误判为通过。

### 4.2 命名实测（`-Action namecheck`，读侧动作、不启停服务）

三段证据（完整输出见 `doc/test/evidence/v147/step3-namecheck-20260919.txt`）：

| 段 | 内容 | 结果 |
|:--:|------|------|
| ① | 编排器将产出的命名（7 服务 × 4 条目 = 28 条）交由白名单逐条校验 | **可见 16 / 跳过 12 / 不可见 0 / 历史旧命名 0**（跳过项均为非 `repo_log` 源目录） |
| ② | 在盘 `logs/` 实测扫描 | **可见 17 / 跳过 59 / 不可见 0 / 历史旧命名 1**（1 例为修复前旧归档 `openrag-20260914.err-220336.log`） |
| ③ | 归档命名自检（系统临时目录内实跑 `Initialize-ServiceLogTarget`） | **8/8 归档文件全部被白名单接受**（`dps-20260919-210700.err.jsonl` / `openrag-20260919-210700.jsonl` 等，时间戳位于 `.err` 之前），临时目录用后即删 |

### 4.3 全量回归与静态检查

| 项 | 命令 | 结果 |
|----|------|------|
| 静态检查 | `python -m ruff check openbase tests scripts` | **0 错误**（`All checks passed!`） |
| 全量回归（最终） | `python -m pytest tests` | **992 收集 / 988 通过 / 4 失败 / 4 跳过 / errors=0**（耗时 1837 s） |
| 平台 | Windows PowerShell 5 / Python 3.10 | — |
| 证据 | `doc/test/evidence/v147/step3-regression-junit.xml`（junit：tests=992 failures=4 errors=0 skipped=4） | — |

**失败项归因（如实登记，无静默放过）**：

| # | 用例 | 归因 | 判据 |
|:-:|------|------|------|
| 1-4 | `tests/test_tenant_admin.py`（2）/ `tests/test_users_admin.py`（2） | **环境性**：`asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation`（无可用 DB 连接） | 与 v1.4.6 Step 4 记录的 4 项**同型同数**（非本次引入） |

**首轮回归暴露的存量问题（已定位并修正，A/B 归因留证）**：首轮全量回归为 **7 失败** = 4 环境性 + **3 项存量测试日期腐化**（`tests/test_logs_service.py` 三个用例）：

| 项 | 内容 |
|----|------|
| 现象 | `assert 0 == 3` / `row_count=0` / `DID NOT RAISE BaseError` —— 命中 0 条 |
| 根因 | 该文件 3 处 fixture **硬编码** `openbase-20260915.jsonl`，而 `L1FileAdapter` 时间窗为「当日 − 2 天」（`max_days=2`）→ 2026-09-19 已出窗 → 扫不到文件；与该文件自身的 `TODAY = datetime.now().strftime("%Y%m%d")`（注释明示「文件名须落在窗内」）口径矛盾 |
| A/B 对照 | `git stash` 仅回退本次改动 → 在**未含本次改动**的工作树上重跑：**同样 3 项失败、断言逐字一致** → 与本次改动**无因果关系**；证据 `doc/test/evidence/v147/step3-stale-test-ab-20260919.txt`（臂 A：`3 failed, 15 passed`；臂 B：`18 passed`） |
| 处置 | 3 处 fixture 改回 `f"openbase-{TODAY}.jsonl"`（日期动态，与文件既有口径一致）；修正后 `tests/test_logs_service.py` + `tests/test_r384_repo_log_naming.py` **31 项全绿**，全量回归由 7 失败降为 **4 环境性失败** |

### 4.4 证据清单

| 证据 | 路径 |
|------|------|
| 命名实测（三段） | `doc/test/evidence/v147/step3-namecheck-20260919.txt` |
| 全量回归 junit | `doc/test/evidence/v147/step3-regression-junit.xml` |
| 存量日期腐化 A/B 对照 | `doc/test/evidence/v147/step3-stale-test-ab-20260919.txt` |

### 4.5 增量 2 验证（2026-09-20，v1.2.0 增补）

#### 4.5.1 静态检查与 TDD

| 项 | 命令 / 方式 | 结果 |
|----|------------|------|
| 静态检查 | `python -m ruff check openbase tests scripts` | **0 错误**（`All checks passed!`） |
| TDD（RED） | `pytest tests/test_rag_proxy_identity_policy.py`（实现前） | **3 failed**，报错 `Settings object has no field "rag_inject_identity_headers"` |
| TDD（GREEN） | 同上（实现后） | **3 passed** |
| 定向回归 | `python -m pytest tests/test_rag_proxy_identity_policy.py tests/test_bl147_trust_env_wiring.py tests/test_proxy_outbound_matrix.py tests/test_rag_proxy.py -q` | **41 passed**（用例数构成实测：3 + 5 + 11 + 22 = 41） |

#### 4.5.2 全量回归（脚本化）

| 项 | 命令 | 结果 |
|----|------|------|
| 全量回归 | `python scripts/run_regression.py` | **passed=996 / failed=0 / skipped=4**（3 段：`1/3 ruff` → `2/3 pytest（85 文件 / 29 组，子进程隔离）` → `3/3 汇总`） |
| 日志末尾原文 | — | `=== 3/3 汇总 ===` / `passed=996 failed=0 skipped=4` / `[OK] 全量回归通过（TD-新增-009 脚本化回归）` / `REGRESSION_DONE exit=0` |
| 失败项归因 | — | v1.4.6 Step 4 曾记录的 **4 项 asyncpg 环境性失败本次未复现**（本轮 `failed=0`）；`skipped=4` 为 `test_storage_s3_real.py` 组（依赖真实 S3 凭据，其余组 `skipped=0`） |

#### 4.5.3 实际运行验证（L1 / L2 / L3）

| 层 | 定义 | 本轮执行 | 结果 |
|:--:|------|---------|------|
| **L1 构建验证** | 构建/编译/语法检查零错误 | 本仓为 **Python 源码项目，无独立构建步骤** → 以 `ruff` 0 错误代替（同 §4.3 口径） | ✅ `All checks passed!` |
| **L2 启动验证** | 启动服务 + 健康检查通过 | 编排器启动 **openrag(8010) + openbase(8000)** 最小服务集 | ✅ 健康检查通过（`-Action start -Only openrag,openbase`） |
| **L3 冒烟测试** | 3~5 个最核心用例 | ① 经网关 `GET /api/v1/rag-proxy/collections`；② 同网关参数非法路径 `page=0` | ✅ ① **200** 且 `data.items=12`（`envelope_code=0`、`total=12`、`body_bytes=5305`）；② **400** 且 **190 字节完整 envelope**（`code=PARAM_400` + `detail[field=page,min=1]` + `request_id`） |

#### 4.5.4 证据清单（增量 2）

| 证据 | 路径 |
|------|------|
| 方案 A/B 多口径实测矩阵 | `doc/test/evidence/v147/def005-multiprobe-20260920.json` |
| 修复后网关复测（200 + `items=12` + 串联一致） | `doc/test/evidence/v147/def005-gateway-retest-20260920.json` |
| 根因定位与口径纠错说明（v1.1.0） | `doc/test/evidence/v147/def005-rag400-probe-20260920.md` |
| 全量回归日志（996/0/4） | `logs/v147-def005-regression.txt` |

#### 4.5.5 如实登记（未实测 / 未执行）

| # | 项 | 说明 |
|:-:|----|------|
| 1 | 逐模块覆盖率（`pytest --cov=openbase`） | **未实测**（本轮未执行覆盖率命令） |
| 2 | 圈复杂度 / 重复率工具扫描（`radon cc` / `jscpd`） | **未实测**（项目未配置该工具链），以变更面核定 0 |
| 3 | 全量端到端抽样重跑（TT-147-003~009） | **未执行**（属 Step 4 范围）；本轮仅完成 DEF-005 的**定向复测**（最小服务集） |
| 4 | 4 项 asyncpg 环境性失败是否稳定消除 | 本轮**未复现**，但结论限于本次运行；仍需 Step 4 稳定环境复验 |

## 5. 未闭项与人工裁定（不静默降级）

### 5.1 已裁定：采集文件「严格全 JSON」判据口径（2026-09-19）

| 项 | 内容 |
|----|------|
| 裁定人 | 项目负责人（**人工裁定**） |
| 裁定日期 | 2026-09-19 |
| 待裁定项 | 版本目标 2「采集文件抽样 **100% 行为合法 JSON** 且含 §5 必需字段」的抽样面，是否包含 uvicorn 等**框架/服务器进程自身**的输出行 |
| **裁定结论** | **采用选项 ③（收窄判据口径）**：该判据的适用面**限定为四仓输出的「应用日志行」**（即行首为 `{` 的 JSONL 行）；`uvicorn.access` 等框架自身输出行**不纳入该判据** |
| 派生口径 | ① **BL-147-05 的串联一致性抽样以「应用日志行」为比对对象**：应用日志行必须携带 `request_id` 且与网关出站头 `X-Request-Id` 完全一致；uvicorn 访问行不参与 `request_id` 比对（该行天然无此字段）；② 非应用日志行仅可走适配器「纯文本回退」解析（`method`/`path`/`status_code`），该能力受限继续在《覆盖状态说明》§5 **显式声明**，非静默降级 |
| 被否选项 | ① 四仓侧统一 uvicorn JSON formatter；② 关闭 `uvicorn.access`（`--no-access-log`）。两项**不在 v1.4.7 范围**，已登记为后续版本候选（《OpenBase-候选需求池》§1.15） |
| 影响文档（已同步升版） | 本报告 §5、覆盖状态说明 §2.0/§5、施工派单 §7/§8、本版本 Backlog「执行期口径补充」、R384 改动包 §8 #4、R384 派单分发清单 §3 |

### 5.2 未闭项（继续跟踪，**2026-09-20 刷新**）

| # | 未闭项 | 影响 | 建议处置 | 归属 | **最新状态（2026-09-20）** |
|:-:|-------|------|---------|------|--------------------------|
| 1 | **DPS P1 修正待入库**：DPS 的 filter 落点修正（挂 handler）**尚在其工作树未提交** | 该仓 hash 无法回填；跨仓交付凭据不完整 | 由 DPS 仓对话或其 `r384-closeout-commit-push.ps1` 提交后回填《施工派单》§9.1 与《覆盖状态说明》§2.0 | **DPS 仓** | **仍开放**（跨仓，本仓无凭据；本轮未实测其工作树状态） |
| 2 | **BL-147-05 端到端串联验收**（判据口径已按 §5.1 收窄，**不再受阻**） | 执行完成前，v1.4.6 Phase 6 门禁（M10/M11）**仍未闭合**；TD-新增-020 暂不可置「已偿还」 | 需运行态五方服务 + 抽样 ≥20 次「网关响应头 `X-Request-Id` ↔ 四仓**应用日志行** `request_id`」逐条比对；已于 2026-09-19 启动（见《OpenBase-测试计划-v1.4.7》） | **本仓 + 四仓（人工门禁）** | **验收通过，待人工批准**：缺陷 4/4 全闭环（DEF-BE-147-001/002/003 业务路径串联 **22/22 = 100%**、JSONL 合法率 100%、可检索 4/4；DEF-BE-147-005 复测 **200 + `items=12`** 且 `request_id` 一致）；**尚需** Step 4 全量重跑（TT-147-003~009）+ 测试回溯审计后方闭合门禁 |

> 未闭项计数：**2 项**（较 §5.1 版本维持 2 项；第 2 项由「进行中」推进为「**验收通过，待人工批准**」，闭合条件收窄为 Step 4 全量重跑与测试回溯审计）。
>
> 声明：以上未闭项均为**显式登记**，未以任何方式静默降级；本仓侧交付（BL-147-04 + DEF-BE-147-005 修复）不影响 v1.4.6 主功能，亦不改变四仓既有行为。

## 6. 变更自检与文档同步

- 变更自检：本次修改/新建**代码与测试文件 5 个**（`scripts/service-orchestrator.ps1`、`openbase/modules/logs/repository.py`、`scripts/verify_repo_log_naming.py`、`tests/test_r384_repo_log_naming.py`、`tests/test_logs_service.py`）+ **文档 6 份**（含本报告）+ `.devflow/state.json`；每次写入后均回读确认，自检 **12 次全部通过**。
- DevFlow 状态同步：`.devflow/state.json` → `currentPhase = v1_4_7_step_3_development`，`completedPhases` 补记 `v1_4_6_step_5_operations` / `v1_4_6_released` / `v1_4_7_step_0_planning`，`auditResults` 补记 `v1_4_6_step_5`（passed，报告存在）/ `v1_4_6_released`（closed，tag `v1.4.6`）/ `v1_4_7_step_0`（passed）/ `v1_4_7_step_3_increment_bl147_04`（in_progress，含未闭项）。
- 版本控制：本次开发提交 **`e6452b1`**（`feat(v1.4.7): R-384 采集命名对齐与归档命名修复（BL-147-04）`，15 文件 / +2029 −40），已推送 **origin `main`** 与 **backup `main`** 双远程（`1ad316a..e6452b1`）。
- 文档同步（均按文档版本管理规范升版并登记修订历史）：
  - 《OpenBase-本版本Backlog-v1.4.7》v1.0.0 → **v1.1.0**（执行期状态刷新）
  - 《OpenBase-R384四仓日志接入覆盖状态说明-v1.4.6》v1.2.0 → **v1.3.0**（BL-147-04 闭环 + 余项 + §5 能力表刷新）
  - 《OpenBase-R384四仓施工派单-v1.0.0》v1.2.0 → **v1.3.0**（§7 采集侧置「已实施」+ §9.1 hash 回填）
  - 《OpenBase-R384改动包-v1.0.0》v1.1.0 → **v1.2.0**（§8 #4 口径刷新）
  - 《OpenBase-R384派单分发清单-v1.0.0》v1.1.0 → **v1.2.0**（执行状态二次刷新）→ **v1.3.0**（余项裁定同步）

### 6.1 增量 2 变更自检（2026-09-20，v1.2.0 增补）

- 变更面：**代码与测试文件 5 个** —— `openbase/settings.py`、`openbase/modules/rag_proxy/__init__.py`、`scripts/service-orchestrator.ps1`、`tests/test_rag_proxy_identity_policy.py`（新建）、`tests/test_bl147_trust_env_wiring.py`；**文档 7 份**（见 §6.2）；配置 `.devflow/state.json`。
- 自检项与结果：
  1. **命名规范**：新建/修改文档均符合 `OpenBase-{文档名}-v1.4.7.md` 约定（本轮新建的三份 Step 3 门禁材料与阶段审计报告见 §6.2 ⑧）；
  2. **版本号一致性**：每份升版文档的「文件头文档版本」与「修订历史末行版本号」一致（逐份回读确认）；
  3. **产出物存在性**：以 `LS`/`Glob` 实测列出产出目录文件并逐项核对（结果见《OpenBase-开发审计移交材料-v1.4.7》§4 与《OpenBase-阶段审计报告-Stage3-v1.4.7》§3）；
  4. **变更范围保护**：本轮仅触及上述 5 个代码/测试文件与 7 份文档 + `.devflow/state.json`，未删除任何文件、未改动四仓代码、未混入无关重构；
  5. **如实性**：未实测项（覆盖率 / 复杂度 / 重复率工具扫描 / Step 4 全量重跑）已在 §4.5.5 逐条留痕，不以推测替代实测。

### 6.2 本轮（增量 2）文档同步清单

| # | 文档 | 升版 | 同步内容 |
|:-:|------|:----:|---------|
| ① | 《OpenBase-测试报告-v1.4.7》（`doc/test/`） | → **v1.3.0** | §7.5 复测 3（DEF-BE-147-005 闭环）+ 定向回归 **41 passed** + 证据口径纠错 |
| ② | 《OpenBase-问题跟踪记录-v1.4.7》（`doc/operation/`） | → **v1.4.0** | DEF-BE-147-005 闭环；CR-147-004（方案 B 实施）/CR-147-005（口径纠错）/CR-147-006（跨仓议题）；结论改为「阻断面由功能缺陷转为流程材料」 |
| ③ | 《OpenBase-本版本Backlog-v1.4.7》（`doc/version/releases/v1.4.7/`） | → **v1.5.0** | BL-147-05 状态刷新（串联判据达成 + DEF-005 闭环） |
| ④ | 《OpenBase-候选需求池》（`doc/version/global/`） | → **v0.26.0** | 新增 §1.16（R-387 跨域租户码语义对齐 / R-388 OpenRAG 拒绝路径结构化日志） |
| ⑤ | 《DEF-BE-147-005 定位证据》（`doc/test/evidence/v147/def005-rag400-probe-20260920.md`） | → **v1.1.0** | 口径纠错（撤回「响应体为空」派生发现）+ 方案 A/B 实测矩阵 + 方案 B 落地记录与后续议题 |
| ⑥ | 《OpenBase-设计开发追溯矩阵-v1.4.7》（`doc/development/`） | → **v1.0.0** | 本版本首次产出（**补齐 Step 3 门禁缺口**）：DT-147-01~04 → TD-147-01~04 → BL → 文件双向追溯 + Subtask CheckList + 版本控制记录 |
| ⑦ | 《OpenBase-DevLogReport-v1.4.7》（本报告） | → **v1.2.0** | §4.5 增量 2 验证 + §5.2 未闭项刷新 + §6.1/§6.2 变更自检与文档同步 |
| ⑧ | **本轮新建的 Step 3 门禁材料**（同为 v1.4.7，首版 v1.0.0） | 新建 | 《OpenBase-静态质量检查记录-v1.4.7》、《OpenBase-代码逻辑审查记录-v1.4.7》、《OpenBase-开发审计移交材料-v1.4.7》（均 `doc/development/`）；《OpenBase-阶段审计报告-Stage3-v1.4.7》（`doc/audit/review/`，由 AU-OpenBase-Dev 产出） |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-19 | AD-OpenBase-Dev | 初始创建：v1.4.7 Step 3 开发记录（BL-147-04 本仓采集命名对齐）。含命名契约（结构化流 `.jsonl`）、归档命名缺陷修复（根因与前后对照）、文件级变更表、TDD 单测、`-Action namecheck` 三段实测、全量回归与**存量测试日期腐化 A/B 归因**、3 项未闭项（uvicorn 访问日志非结构化 / DPS P1 修正待入库 / BL-147-05 未执行）与证据清单 |
| v1.0.1 | 2026-09-19 | AD-OpenBase-Dev | **回填开发提交与推送证据**：§6 登记提交 `e6452b1`（15 文件 / +2029 −40）及 origin / backup 双远程推送结果（`1ad316a..e6452b1`） |
| v1.1.0 | 2026-09-19 | PM-OpenBase-Dev | **人工裁定登记（选项③）**：新增 §5.1「采集文件『严格全 JSON』判据口径」——判据适用面限定为四仓**应用日志行**，uvicorn 等框架自身输出行不纳入；派生 BL-147-05 抽样以应用日志行为比对对象；被否选项 ①② 登记为后续版本候选（候选需求池 §1.15）；§5.2 未闭项由 3 项收敛为 2 项（原第 1 项转「已裁定」）；同步 6 份联动文档升版（覆盖状态说明 / 施工派单 / 本版本 Backlog / R384 改动包 / 派单分发清单 / 候选需求池） |
| **v1.2.0** | **2026-09-20** | **AD-OpenBase-Dev** | **增量 2（DEF-BE-147-005 修复）验证与门禁材料补齐**：① 新增 **§4.5 增量 2 验证**——`ruff check openbase tests scripts` **0 错误**、TDD RED（3 failed，`Settings object has no field "rag_inject_identity_headers"`）→ GREEN（3 passed）、定向回归 **41 passed**（3+5+11+22）、全量回归 **passed=996 / failed=0 / skipped=4**（`logs/v147-def005-regression.txt`；v1.4.6 Step 4 的 4 项 asyncpg 环境性失败**本次未复现**）、实际运行验证 L1（无构建步骤，以 ruff 代替）/ L2（openrag+openbase 健康检查通过）/ L3（`rag-proxy/collections` 200 + `items=12`；`page=0` → 400 + 190 字节完整 envelope）、证据清单与 **4 项未实测/未执行如实登记**；② **§5.2 未闭项刷新**——DPS P1 修正待入库**仍开放**，BL-147-05 状态更新为「**验收通过，待人工批准**」（尚需 Step 4 全量重跑 + 测试回溯审计）；③ 新增 **§6.1 增量 2 变更自检** 与 **§6.2 本轮文档同步清单**（测试报告 v1.3.0 / 问题跟踪记录 v1.4.0 / 本版本 Backlog v1.5.0 / 候选需求池 v0.26.0 / DEF-005 证据文档 v1.1.0 / 设计开发追溯矩阵 v1.0.0 / 本报告 v1.2.0 + 4 份 Step 3 门禁材料新建）；④ §1/§2/§3.1~§3.5/§4.1~§4.4 **原文未动** |
| **v1.2.1** | **2026-09-20** | **AD-OpenBase-Dev** | **验收数值同步核查（最终权威口径＝`-PerFamily 10` 强化重跑，BL-147-05）**：逐处检索本报告 **§4.5「增量 2 验证」**全段（§4.5.1~§4.5.5），**未发现** BL-147-05 前一轮（`-PerFamily 6`：14:20:16~14:28:41、24 次抽样、业务路径 13/13、探活 11 次命中 7）的中间态数值——该段数值仅为 `ruff` 0 错误、TDD 3 failed→3 passed、定向回归 41 passed（3+5+11+22）、全量回归 `passed=996 / failed=0 / skipped=4`、L3 `collections` 200 + `items=12`、`page=0` 400 + 190 字节 envelope，与最终权威口径无冲突，故 **§4.5 正文不改动**（按「无涉及处则跳过」处理）；另核对 **§5.2 未闭项**表述中的「业务路径串联 **22/22 = 100%**、JSONL 合法率 100%、可检索 4/4」与最终权威口径**同值，无需变更**；最终权威口径登记为——业务路径 **22 / 命中 22 / 命中率 1.0（100%）**（40 次抽样、校验退出码 0；探活/豁免 **18** 次单列）、四仓应用日志行 JSONL 合法率 **100%**（dps 391 / openrag 348 / openmemory 422 / openllm 2786）、`repo_log` 可检索 **4/4**（dps 391 / rag 493 / memory 422 / llm 5200），证据 `logs/v147-bl147-05-rerun-perfamily10.txt`（`E2E10_DONE exit=0`）、`doc/test/evidence/v147/bl147-05-*.json`；§5.2 中「尚需 Step 4 全量重跑 + 测试回溯审计」属增量 2 时点的历史状态表述，按**不改历史**原则保留原文；文档版本 v1.2.0 → **v1.2.1** |

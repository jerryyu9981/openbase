# OpenBase 开发审计移交材料 - v1.4.7

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.7（四仓日志接入补完 · 日志域收官 · 跨仓，承接型小版本） |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 移交对象 | AU-OpenBase-Dev（审计师，Step 3 阶段审计） |
| 创建日期 | 2026-09-20 |
| 存放 | doc/development/ |

---

## 1. 移交范围与结论

| 项 | 内容 |
|----|------|
| 本阶段范围 | **Step 3 开发（本仓侧）**：增量 1 = BL-147-04（采集命名对齐 + 归档命名缺陷修复 + 命名实测）；增量 2 = DEF-BE-147-005（P1）修复（rag-proxy 身份注入策略显式开关，方案 B） |
| 明确排除 | BL-147-01/02/03（**四仓侧**交付，各仓独立评审与发布，本材料不代述他仓改动）；Step 4 测试结论；Step 5 部署与发布 |
| 是否具备进入开发审计条件 | ✅ 具备（**未闭环 P0/P1 = 0**；已闭环缺陷 4/4） |
| 开发设计对比覆盖率 | **100%（4/4）**：DT-147-01~04 → TD-147-01~04 全部落地，其中 1 项偏差（TD-147-04 采用方案 B）已显式登记（计算口径见《OpenBase-阶段审计报告-Stage3-v1.4.7》§5） |
| 移交材料齐备性 | 追溯矩阵 / 静态质量检查记录 / 代码逻辑审查记录 / DevLogReport / 本材料 / 证据文件（详见 §4 存在性验证） |

## 2. 变更集清单（Deliverable Inventory）

> **口径声明（如实登记）**：本轮受环境约束**未执行 `git diff --numstat` / `git status` 等 git 命令**（任务方明令禁止 git 与 pytest、服务启停命令，且本机存在长任务在跑）。故本清单**按文件逐一列出**变更类型与**文件系统实测行数**，**不给出 `+n / −m` 精确增量**（避免以推测替代实测）；变更点位为源码逐行回读确认。

### 2.1 代码与测试（9 个文件）

| # | 文件 | 变更 | 实测行数 | 变更点位 | 增量 |
|:-:|------|------|:--------:|----------|:----:|
| 1 | `scripts/service-orchestrator.ps1` | 修改 | 806 | 增量 1：四仓服务定义 `JsonStream`、`Get-ServiceLogFileName` / `Get-ServiceLogArchiveName`、`-Action namecheck` + `Test-ServiceLogArchiveSelfCheck`、`ValidateSet` 增列；增量 2：L259 `OPENBASE_RAG_INJECT_IDENTITY_HEADERS = 'false'`（含 L253–L258 注释） | 1 + 2 |
| 2 | `openbase/modules/logs/repository.py` | 修改 | 919 | 公开常量 `REPO_LOG_NAME_RE` + `__all__` 导出 + 命名契约注释（**正则本体零变更**） | 1 |
| 3 | `scripts/verify_repo_log_naming.py` | **新建** | 231 | 命名白名单校验工具（`--file` / `--logs-root` / `--tolerate-legacy-err-archive`；退出码 0/1/2） | 1 |
| 4 | `tests/test_r384_repo_log_naming.py` | **新建** | 240 | 13 例（四仓命名/归档全通过 + 反例 + `skipped`/`legacy` + CLI 退出码 + 编排器结构护栏） | 1 |
| 5 | `tests/test_logs_service.py` | 修改 | 434 | 3 处 fixture 由硬编码 `openbase-20260915.jsonl` 改回 `f"openbase-{TODAY}.jsonl"`（存量为日期腐化，A/B 归因证据见 §3） | 1 |
| 6 | `openbase/settings.py` | 修改 | 409 | L179–L187 注释 + `rag_inject_identity_headers: bool = True` | 2 |
| 7 | `openbase/modules/rag_proxy/__init__.py` | 修改 | 585 | L106–L108 docstring 增补；L118 `effective_user = user if settings.rag_inject_identity_headers else None`（**仍走同一装配点**） | 2 |
| 8 | `tests/test_rag_proxy_identity_policy.py` | **新建** | 106 | 3 例：默认注入四头 / 关闭不注入四头 / 关闭仍携带 `X-Request-Id` | 2 |
| 9 | `tests/test_bl147_trust_env_wiring.py` | 修改 | 101 | L85–L101 新增 1 例（openbase 块须声明 `OPENBASE_RAG_INJECT_IDENTITY_HEADERS='false'`）；该文件现 **5 例** | 2 |

**新增文件 3 个**（第 3、4、8 项）；**修改文件 6 个**；**删除文件 0 个**。

### 2.2 文档与配置

| # | 文件 | 变更 | 实测行数 / 字节 |
|:-:|------|------|:---------------:|
| 1 | `doc/development/OpenBase-设计开发追溯矩阵-v1.4.7.md` | **新建**（补齐 Step 3 门禁缺口） | 58 行 / 5,319 B |
| 2 | `doc/development/OpenBase-静态质量检查记录-v1.4.7.md` | **新建** | 158 行 / 20,726 B |
| 3 | `doc/development/OpenBase-代码逻辑审查记录-v1.4.7.md` | **新建** | 213 行 / 24,985 B |
| 4 | `doc/development/OpenBase-开发审计移交材料-v1.4.7.md` | **新建**（本文件，自列） | 见 §4.2 |
| 5 | `doc/development/OpenBase-DevLogReport-v1.4.7.md` | 修改（v1.1.0 → **v1.2.0**） | 265 行 / 28,891 B |
| 6 | `doc/audit/review/OpenBase-阶段审计报告-Stage3-v1.4.7.md` | **新建**（由 AU 于本阶段审计后产出；**已产出**：296 行 / 30,695 B） | 296 行 / 30,695 B |
| 7 | `doc/test/evidence/v147/def005-rag400-probe-20260920.md` | 修改（→ v1.1.0：口径纠错 + 方案裁定） | 91 行 / 8,730 B |
| 8 | `.devflow/state.json` | 修改（阶段状态同步） | — |

> 另有本轮联动升版文档（**非本仓 Step 3 门禁产出，仅登记**）：《OpenBase-测试报告-v1.4.7》v1.3.0、《OpenBase-问题跟踪记录-v1.4.7》v1.4.0、《OpenBase-本版本Backlog-v1.4.7》v1.5.0、《OpenBase-候选需求池》v0.26.0（详见 DevLogReport §6.2）。

## 3. 命令与结果

### 3.1 静态质量与 TDD 证据

| 项 | 命令 | 结果 | 证据位置 |
|----|------|------|----------|
| 静态检查 | `python -m ruff check openbase tests scripts` | **`All checks passed!`（0 错误）** | 静态质量检查记录 §2；回归日志 L1–L3（`=== 1/3 ruff ===` / `[OK] ruff`） |
| TDD RED | `pytest tests/test_rag_proxy_identity_policy.py`（实现前） | **3 failed**：`Settings object has no field "rag_inject_identity_headers"` | DevLogReport §4.5.1 |
| TDD GREEN | 同上（实现后） | **3 passed** | DevLogReport §4.5.1 |
| 定向回归 | `python -m pytest tests/test_rag_proxy_identity_policy.py tests/test_bl147_trust_env_wiring.py tests/test_proxy_outbound_matrix.py tests/test_rag_proxy.py -q` | **41 passed**（用例数构成实测：3 + 5 + 11 + 22） | DevLogReport §4.5.1 |
| 全量回归（脚本化） | `python scripts/run_regression.py` | **passed=996 / failed=0 / skipped=4**；末尾 `=== 3/3 汇总 ===`、`[OK] 全量回归通过（TD-新增-009 脚本化回归）`、`REGRESSION_DONE exit=0` | `logs/v147-def005-regression.txt`（66 行） |
| 存量测试日期腐化 A/B 归因 | 臂 A（含本次改动前工作树）/ 臂 B | 臂 A `3 failed, 15 passed` / 臂 B `18 passed` → 与本次改动**无因果关系** | `doc/test/evidence/v147/step3-stale-test-ab-20260919.txt` |

### 3.2 实际运行验证（L1 / L2 / L3）

| 层 | 本轮执行 | 结果 |
|:--:|---------|------|
| L1 构建验证 | Python 源码项目**无独立构建步骤** → 以 `ruff` 0 错误代替 | ✅ `All checks passed!` |
| L2 启动验证 | 编排器启动最小服务集 **openrag(8010) + openbase(8000)**（`-Action start -Only openrag,openbase`） | ✅ 健康检查通过 |
| L3 冒烟测试 | ① 经网关 `GET /api/v1/rag-proxy/collections`；② 同网关 `page=0` | ✅ ① **200** / `envelope_code=0` / `items_count=12` / `total=12` / `body_bytes=5305`；② **400** / **190 字节完整 envelope**（`PARAM_400` + `detail[field=page,min=1,input="0"]` + `request_id`） |

### 3.3 端到端定向复测（增量 2，非 Step 4 全量）

| 判据 | 修复前 | 修复后（定向复测） | 证据 |
|------|:------:|:-----------------:|------|
| 经网关 `GET /api/v1/rag-proxy/collections` | 400（`BIZ_RESERVED_TENANT_CODE_COLLISION`） | **200** | `def005-gateway-retest-20260920.json` |
| 数据完整可见 | —（400 无数据） | **`items=12` / `total=12`** | 同上 |
| 跨系统串联（同一请求内） | （400 时亦一致） | **一致**：响应头 `X-Request-Id = req-2ebfcfc04552` ↔ OpenRAG 应用日志行 `request_started` / `api_key_authed` / `request_completed(status_code=200)` 三行同值 | 同上（`openrag_log_hits`） |
| 方案 A 反证（非保留租户码） | — | 200 但 **`items=[]`**（租户隔离致既有知识库不可见） | `def005-multiprobe-20260920.json`（A1/A2 用例） |

> **范围声明**：以上为 **DEF-BE-147-005 的定向复测（最小服务集）**，**不替代** Step 4 全量重跑（TT-147-003~009，五方服务 + ≥20 次抽样）与测试回溯审计。

## 4. 产出物存在性验证（LS / Glob 实测）

> 验证方式：以文件系统盘点（`LS` / `Glob`）列出目标目录实际文件，并逐项核对本阶段产出清单；同时记录行数与字节数以排除「空文件/占位」。**验证时间：2026-09-20**。

### 4.1 代码与测试产出（9/9 存在）

| # | 文件 | 实测行数 | 判定 |
|:-:|------|:--------:|:----:|
| 1 | `scripts/service-orchestrator.ps1` | 806 | ✅ |
| 2 | `openbase/modules/logs/repository.py` | 919 | ✅ |
| 3 | `scripts/verify_repo_log_naming.py` | 231 | ✅ |
| 4 | `tests/test_r384_repo_log_naming.py` | 240 | ✅ |
| 5 | `tests/test_logs_service.py` | 434 | ✅ |
| 6 | `openbase/settings.py` | 409 | ✅ |
| 7 | `openbase/modules/rag_proxy/__init__.py` | 585 | ✅ |
| 8 | `tests/test_rag_proxy_identity_policy.py` | 106 | ✅ |
| 9 | `tests/test_bl147_trust_env_wiring.py` | 101 | ✅ |

### 4.2 文档产出

| # | 文件 | 实测行数 / 字节 | 判定 |
|:-:|------|:---------------:|:----:|
| 1 | `doc/development/OpenBase-设计开发追溯矩阵-v1.4.7.md` | 58 / 5,319 | ✅ |
| 2 | `doc/development/OpenBase-静态质量检查记录-v1.4.7.md` | 158 / 20,726 | ✅ |
| 3 | `doc/development/OpenBase-代码逻辑审查记录-v1.4.7.md` | 213 / 24,985 | ✅ |
| 4 | `doc/development/OpenBase-DevLogReport-v1.4.7.md` | 265 / 28,891 | ✅ |
| 5 | `doc/development/OpenBase-开发审计移交材料-v1.4.7.md` | 本文件（自列，不作为核对对象） | ✅ |
| 6 | `doc/audit/review/OpenBase-阶段审计报告-Stage3-v1.4.7.md` | 296 / 30,695（**审计已完成并产出**） | ✅ |

**存在性结论：文档产出 **5/6** 实测存在（不含本文件；第 6 项阶段审计报告由 AU 于审计后产出，**现已产出** 296 行 / 30,695 B）；**无空文件、无占位**，均含实质内容（最小文本产出 58 行 / 5,319 B）。**

### 4.3 证据产出

| # | 文件 | 实测行数 / 字节 | 判定 |
|:-:|------|:---------------:|:----:|
| 1 | `doc/test/evidence/v147/def005-multiprobe-20260920.json` | 109 / 13,017 | ✅ |
| 2 | `doc/test/evidence/v147/def005-gateway-retest-20260920.json` | 22 / 1,476 | ✅ |
| 3 | `doc/test/evidence/v147/def005-rag400-probe-20260920.md`（v1.1.0） | 91 / 8,730 | ✅ |
| 4 | `doc/test/evidence/v147/step3-namecheck-20260919.txt` | 存在（三段实测） | ✅ |
| 5 | `doc/test/evidence/v147/step3-regression-junit.xml` | 存在（增量 1 junit） | ✅ |
| 6 | `doc/test/evidence/v147/step3-stale-test-ab-20260919.txt` | 存在（A/B 对照） | ✅ |
| 7 | `logs/v147-def005-regression.txt` | 66 / 3,552 | ✅ |

## 5. 已知风险与未闭项（移交声明）

| ID | 级别 | 内容 | 移交处置 |
|----|:----:|------|----------|
| RS-147-01 | P2 | 跨域租户码语义对齐（**根因未根治**，现行方案 B 为绕行） | 设计确认映射方案后决定是否恢复注入模式；已登记 CR-147-006 + 候选需求池 §1.16（R-387） |
| RS-147-02 | P2 | **DPS P1 修正待入库**（跨仓，工作树未提交） | 由 DPS 仓提交后回填《施工派单》§9.1 与《覆盖状态说明》§2.0；**本仓无凭据，未实测** |
| RS-147-03 | P2 | OpenRAG 拒绝路径缺结构化拒绝日志 | 跨仓建议（CR-147-006 / 候选需求池 §1.16 R-388） |
| RS-147-04 | P2 | **Step 4 全量重跑未执行**（TT-147-003~009 + 报告总结论刷新） | Step 4 执行；在此之前 v1.4.6 Phase 6 门禁（M10/M11）未闭合，**TD-新增-020 不得置「已偿还」** |
| RS-147-05 | P3 | 本轮未实测项：逐模块覆盖率（`--cov`）、圈复杂度/重复率工具扫描、PS 脚本单独语法解析 | 记录为未实测；建议纳入脚本化回归 |
| RS-147-06 | P3 | 在盘历史旧命名归档文件仍不可见（修复前后同样不可见，非本次引入的回退） | `-Action namecheck` 单列 `legacy` 不阻断；如需回捞一次性重命名治理 |

## 6. 测试移交输入（供 Step 4 使用）

| 项 | 内容 |
|----|------|
| 环境 | Windows PowerShell 5 / Python 3.10；最小复现集 `-Action start -Only openrag,openbase`（端口 8010 / 8000）；完整拓扑须拉起五方服务 |
| 服务启动 | `scripts/service-orchestrator.ps1 -Action start`（联调口径已含 `OPENBASE_RAG_INJECT_IDENTITY_HEADERS='false'`）；命名实测读侧动作 `-Action namecheck`（不启停服务） |
| 回归入口 | `python scripts/run_regression.py`（3 段：ruff → pytest 85 文件/29 组子进程隔离 → 汇总） |
| 关键测试数据 | 知识库列表 `items=12`（租户 `default`）；网关错误路径 `page=0`（→400 `PARAM_400`） |
| 建议回归范围 | ① rag-proxy 全链路（`test_rag_proxy*.py` + `test_proxy_outbound_matrix.py`）；② 编排器 env 护栏（`test_bl147_trust_env_wiring.py`）；③ 日志命名（`test_r384_repo_log_naming.py` + `test_logs_service.py`）；④ 全量回归 + 覆盖率 |
| 待补测试项 | TT-147-003~009（五方服务 + ≥20 次「网关响应头 ↔ 四仓应用日志行」抽样）、逐模块覆盖率（`--cov=openbase`）、测试回溯对比审计 |
| 关注风险 | RS-147-01/02/03（跨仓未闭项）、RS-147-04（Step 4 未跑前门禁未闭合） |
| Mock / 隔离 | 本轮无新增 Mock；策略开关可经 `monkeypatch` 注入（既有用例范式） |

## 7. 移交结论

- 本阶段**全部强制产出物齐备**：追溯矩阵 / 静态质量检查记录 / 代码逻辑审查记录 / DevLogReport / 本材料 / 阶段审计报告（**由 AU 已产出**），并附完整证据链（§4.3 七项实测存在）。
- **未闭环 P0/P1 = 0**；静态质量 0 错误、技术债务增长率 0/0/0（含 1 项伪阳性剔除留痕）、定向回归 41 passed、全量回归 996 passed / 0 failed / 4 skipped。
- **1 项设计偏差**（TD-147-04 采用方案 B）与 **6 项剩余风险 / 未实测项**已逐条登记；四仓侧 BL-147-01/02/03 **明确排除**在本阶段范围。
- **如实性声明**：本材料中所有命令结果均可回溯至证据文件或日志原文；**未由本次重跑的项目（ruff / pytest / 服务启停）已标注为「引用既有证据」**；环境约束（禁止运行 git / pytest / 服务启停，且本机有长任务在跑）已在 §2 与文首声明，未以推测替代实测。
- **申请进入 Step 3 阶段审计**（AU 复核 DT→TD 追溯链、产出物存在性、三项编码检查点）——审计结论见 `doc/audit/review/OpenBase-阶段审计报告-Stage3-v1.4.7.md`。

## 8. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-20 | AD-OpenBase-Dev | 初始创建：v1.4.7 Step 3 开发审计移交材料（**补齐本版本此前缺失的门禁材料**）。含移交范围与结论（覆盖 100%、未闭环 P0/P1 = 0）、变更集清单（代码/测试 9 文件 + 文档/配置 8 项，含**未执行 git diff 的口径声明**）、命令与结果（ruff 0 / TDD RED→GREEN / 定向 41 passed / 全量 996-0-4 / L1-L2-L3 / 端到端定向复测）、**产出物存在性验证（LS/Glob 实测，代码 9/9、文档 4/4、证据 7/7）**、6 项已知风险与未闭项、测试移交输入、移交结论与如实性声明 |

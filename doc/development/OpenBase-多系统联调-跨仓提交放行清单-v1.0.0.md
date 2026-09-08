# OpenBase-多系统联调-跨仓提交放行清单-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-CROSSREPO-RELEASE-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Draft]（供用户沙箱外执行；每条命令执行前请以「第 0 步核对」实核各仓 git 状态） |
| 日期 | 2026-09-09 |
| 作者 | AD（跨项目分析） |
| 版本主题 | S2（OpenMemory 段）段门禁批准后的跨仓放行清单：OpenMemory v7.2 基线先行 + S2（v7.3 拟）五份文档与源码/迁移/测试分批提交；OpenLLM/DPS/OpenRAG S0 探活等既有待提交分批核对提交；OpenBase 侧已全部提交无需放行 |
| 上游依据 | OpenMemory S2 立项方案 v1.1.0 / 设计草案 v1.0.3 / DevLogReport v1.0.1 / 测试报告 v1.0.1 / doc/design/OpenMemory-K07-端点过滤矩阵填报 v1.0.1（[Approved]，2026-09-09 S2 段门禁人工批准五项全绿）；OpenBase-数据隔离实现任务卡 v1.4.0（S2 段回写）；OpenBase commit 0713ec1=事件列表契约端点 GET /api/v1/identity/events（2026-09-09 冻结） |
| 适用范围 | 本清单涉及 OpenMemory / OpenLLM / DPS / OpenRAG 四个子系统 git 仓的放行提交作业，须由用户在沙箱外执行（沙箱内 git 仅允许操作 OpenBase 仓）；OpenBase 仓本次回写已在沙箱内提交（见 §5） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-09 | AD（跨项目分析） | 初始版本：S2（OpenMemory）段收口跨仓放行清单（OpenMemory v7.2 基线 + S2 v7.3 批次；OpenLLM/DPS/OpenRAG S0 探活等既有待提交；OpenBase 无需放行），含逐仓建议分支、提交顺序、git add/commit 模板与提交后回归命令 |

---

## 0. 使用说明与放行总原则

- 本文件为 **[Draft]** 放行指引，不是自动执行指令：沙箱仅允许提交 OpenBase 仓，其余四仓命令需用户人工在沙箱外执行。
- **放行顺序总体建议**：OpenMemory 先行（v7.2 基线 → S2 批次，四提交）→ OpenLLM / DPS / OpenRAG（S0 探活等既有待提交，按仓分批）→ OpenBase（无需放行，本次回写已另提交）。
- 每个提交前必做：`git status --porcelain` 核对、`git diff --cached --stat` 复查暂存内容仅含预期路径；**只 add 预期路径，不用 `git add -A` 兜底**（基线提交除外，见 §1.5 说明）。
- 中文文件名路径在 PowerShell 中一律用**单引号**包裹。
- 每个仓库「提交后回归」若失败：停止后续批次，修正后再继续；回归通过后再进行下一仓。
- 提交后回填：OpenMemory 实际 commit hash 需回填《OpenBase-数据隔离实现任务卡 v1.4.0》卡尾 S2 段执行摘要与各仓文档状态登记（本文档升版为 [Approved] 时一并登记，遵循文档版本管理规范）。

## 1. OpenMemory 仓（D:\Trae CN\myproject\Dev\OpenMemory）

### 1.1 现状核对基线（2026-09-09 实测）

| 项目 | 值 |
|------|-----|
| HEAD | `6cbfb71`（6cbfb719b19846eebc068b2b36f31071efc23e1f，chore: v6.9.0 全流程闭环登记 closureComplete） |
| 当前分支 | `release/v6.9.0` |
| 工作树 | v7.0~v7.2 未提交（登记口径 **69 M + 207 ??**；2026-09-09 实测 **75 M + 235 ??**——以第 0 步实核为准） |
| S2（v7.3 拟）产物 | 全部位于未跟踪/已修改工作树，因 git 沙箱受限尚未提交 |

**第 0 步核对命令**（执行任何提交前先跑）：

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
git log -1 --format='%H %s'                        # 期望 6cbfb71...（v6.9.0 发布闭环）
git branch --show-current                          # 期望 release/v6.9.0
(git status --porcelain).Count                     # 核对总行数（登记 276=69M+207??，实测 310=75M+235??）
git diff --cached --stat                           # 应无输出（无已暂存内容）
```

### 1.2 建议分支与提交顺序

- **提交 1（v7.2 基线）**：自 `release/v6.9.0` 切出 `release/v7.2.0`，在此分支提交基线。
- **提交 2~4（S2 批次）**：自基线提交切出 `release/v7.3.0`，在此分支按「五份文档 → 源码/迁移/脚本 → 测试/CI」三批提交（S2 规划承载版本 v7.3 拟，随版本规划批准）。
- 提交顺序总览：

| 序号 | 分支 | 提交内容 | 建议 commit 主题 |
|------|------|---------|-----------------|
| 1 | release/v7.2.0 | v7.0~v7.2 工作树基线（剔除 S2 专属文件） | chore: OpenMemory v7.2 基线收口 |
| 2 | release/v7.3.0 | S2 五份文档 | docs(s2): OpenMemory S2 五份文档入库 |
| 3 | release/v7.3.0 | S2 源码 + 中间件 + 迁移 v702~v704 + 脚本 | feat(s2): S2 协议头/行控/复合唯一/存量回填/事件消费端/矩阵校验 源码与迁移 |
| 4 | release/v7.3.0 | S2 测试用例 + CI s2-k07-matrix-gate job | test(s2): S2 T1~T13 RED 断言与段门禁自检用例 |

> 如需按 T 顺序拆更多提交：T1~T13 的逐卡提交仅对「新增测试文件」可按文件分组（test_s2_tN_*.py）；源码模块（identity/*、中间件）与迁移、脚本跨任务复用，不建议再按 T 拆分。本清单采用「合并」方案（用户可选项：或合并）。

### 1.3 S2（v7.3）专属文件清单（基线剔除清单，提交 2~4 的 add 集合）

```text
# 五份文档
OpenMemory-S2-过滤行控与身份接入立项方案-v1.0.0.md
OpenMemory-S2-过滤行控与身份接入设计草案-v1.0.0.md
doc/development/OpenMemory-S2-过滤行控与身份接入-DevLogReport-v1.0.0.md
doc/test/OpenMemory-S2-过滤行控与身份接入-测试报告-v1.0.0.md
doc/design/OpenMemory-K07-端点过滤矩阵填报-v1.0.0.md

# 源码与中间件（新增）
src/openmemory/identity/                    # agent_principal/audit_identity/blocklist/event_consumer/inbound_gate/protocol_headers/role_map/scope_exemption/verdict/__init__
src/openmemory/api/middleware/identity_gate.py
src/openmemory/api/middleware/block_subject_gate.py

# 迁移（S2：v702=T5 复合唯一、v703=T6 存量回填、v704=T7 事件阻断集）
alembic/versions/v702_session_registry_meta.py
alembic/versions/v703_backfill_scope_ownership.py
alembic/versions/v704_identity_blocklist.py

# 脚本与资产
scripts/k07_endpoint_matrix.py
scripts/scope_backfill_report.py
scripts/scan_auto_purge.py
scripts/smoke_l3_2.py
scripts/api_baseline.json
scripts/verify-env/                          # contract.json / verify_env_report.py 等

# 测试
tests/unit/test_s2_t*.py                     # t1~t13（含 test_s2_t1_protocol_gate.py ... test_s2_t12_m1_m2_modes.py）
tests/unit/test_l3_2_smoke.py
tests/unit/test_s2_segment_gate_selfcheck.py
```

> 混合文件说明：`.github/workflows/ci.yml` 同时含 v7.0 性能基线 job（TD-v7.0-010）与 S2 s2-k07-matrix-gate job；`src/openmemory/api/controllers.py`、`utils/config.py`、`utils/exceptions.py`、`api/middleware/structured_log.py`、`error_handler.py`、`memory/session_persistent.py` 等已跟踪文件内同时叠有 v7.2 基线改动与 S2 增量，git 无法按文件拆分。默认方案：**ci.yml 收入 S2 批次（提交 4），其余混合文件随基线（提交 1）**，避免基线提交引入引用缺失文件（s2-k07 job 依赖 scripts/k07_endpoint_matrix.py 与矩阵 doc）导致 CI 失败。若需严格拆分，见 §1.5 备注的 `git add -p` 做法。

### 1.4 放行步骤与命令模板

**提交 1 — v7.2 基线（release/v7.2.0）**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
git switch -c release/v7.2.0                      # 自 release/v6.9.0(6cbfb71) 切基线分支
git add -A                                        # 全量暂存（含 v7.x 基线 M + 未跟踪）
# 将 S2 专属文件移出暂存区（保留在工作树）；逐行执行 §1.3 清单，示例：
git reset -- 'OpenMemory-S2-过滤行控与身份接入立项方案-v1.0.0.md' 'OpenMemory-S2-过滤行控与身份接入设计草案-v1.0.0.md'
git reset -- 'doc/development/OpenMemory-S2-过滤行控与身份接入-DevLogReport-v1.0.0.md' 'doc/test/OpenMemory-S2-过滤行控与身份接入-测试报告-v1.0.0.md' 'doc/design/OpenMemory-K07-端点过滤矩阵填报-v1.0.0.md'
git reset -- 'src/openmemory/identity' 'src/openmemory/api/middleware/identity_gate.py' 'src/openmemory/api/middleware/block_subject_gate.py'
git reset -- 'alembic/versions/v702_session_registry_meta.py' 'alembic/versions/v703_backfill_scope_ownership.py' 'alembic/versions/v704_identity_blocklist.py'
git reset -- 'scripts/k07_endpoint_matrix.py' 'scripts/scope_backfill_report.py' 'scripts/scan_auto_purge.py' 'scripts/smoke_l3_2.py' 'scripts/api_baseline.json' 'scripts/verify-env'
git reset -- 'tests/unit/test_s2_t*.py' 'tests/unit/test_l3_2_smoke.py' 'tests/unit/test_s2_segment_gate_selfcheck.py'
git reset -- '.github/workflows/ci.yml'
git status --short                                 # 复核：工作树仍含上述 S2 文件（未暂存）
git commit -m "chore: OpenMemory v7.2 基线收口（v7.0~v7.2 工作树登记；S2 v7.3 专属文件剔除，后续按 S2 批次提交）"
git tag v7.2.0                                     # 可选：基线打 tag
```

**提交 2 — S2 五份文档（release/v7.3.0）**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
git switch -c release/v7.3.0                       # 自 v7.2 基线提交切 S2 分支
git add 'OpenMemory-S2-过滤行控与身份接入立项方案-v1.0.0.md' 'OpenMemory-S2-过滤行控与身份接入设计草案-v1.0.0.md' 'doc/development/OpenMemory-S2-过滤行控与身份接入-DevLogReport-v1.0.0.md' 'doc/test/OpenMemory-S2-过滤行控与身份接入-测试报告-v1.0.0.md' 'doc/design/OpenMemory-K07-端点过滤矩阵填报-v1.0.0.md'
git commit -m "docs(s2): OpenMemory S2 五份文档入库（立项方案 v1.1.0/设计草案 v1.0.3/DevLogReport v1.0.1/测试报告 v1.0.1/K07 矩阵填报 v1.0.1，[Approved] 段门禁全绿）"
```

**提交 3 — S2 源码、迁移与脚本**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
git add 'src/openmemory/identity' 'src/openmemory/api/middleware/identity_gate.py' 'src/openmemory/api/middleware/block_subject_gate.py'
git add 'alembic/versions/v702_session_registry_meta.py' 'alembic/versions/v703_backfill_scope_ownership.py' 'alembic/versions/v704_identity_blocklist.py'
git add 'scripts/k07_endpoint_matrix.py' 'scripts/scope_backfill_report.py' 'scripts/scan_auto_purge.py' 'scripts/smoke_l3_2.py' 'scripts/api_baseline.json' 'scripts/verify-env'
git commit -m "feat(s2): S2 协议头入站/行控收口/复合唯一/存量回填/事件消费端/矩阵校验 源码与迁移（T1~T13，alembic v702~v704）"
```

**提交 4 — S2 测试用例与 CI 门禁**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
git add 'tests/unit/test_s2_t*.py' 'tests/unit/test_l3_2_smoke.py' 'tests/unit/test_s2_segment_gate_selfcheck.py'
git add '.github/workflows/ci.yml'                 # 含 s2-k07-matrix-gate job（另含 v7.0 性能基线 hunk，见 §1.5 严格模式）
git commit -m "test(s2): S2 T1~T13 RED 断言与段门禁自检用例 + CI s2-k07-matrix-gate job"
git tag v7.3.0-rc.1                                # 可选：S2 收官打候选 tag
```

### 1.5 备注

- **基线提交自检**：因混合文件（controllers.py/config.py/exceptions.py/structured_log.py/error_handler.py/session_persistent.py 等）与部分被扩展的既有测试随基线提交，**v7.2 基线提交可能无法独立全绿**；全量回归门禁以提交 4 之后为准（见 §1.6）。基线提交只核对「暂存区不含 §1.3 清单文件、源码可导入」。
- **严格拆分（可选）**：若要求 v7.2 基线不含任何 S2 增量，对混合文件（含 ci.yml）改用 `git add -p` 逐 hunk 选择——在提交 1 中仅收入 v7.2 基线 hunk（性能基线 job / 基线功能），在提交 3/4 用 `git add` 收入剩余 S2 hunk；`git add -p` 为交互式，需人工逐 hunk 确认。
- 若仓内版本发布惯例需同步 CHANGELOG/Release-Note，请在提交 1 前将 v7.2 版本登记纳入（随基线），S2 收官后按发布计划补 v7.3 版本文档。

### 1.6 提交后回归（OpenMemory）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
python -m pytest tests/unit tests/integration -q -p no:cacheprovider   # 期望 1330 passed, 36 skipped（1 项 caplog 顺序敏感 flaky，见 DevLogReport §7）
python -m ruff check src scripts                                       # 期望 0 错误
python scripts/k07_endpoint_matrix.py --verify --matrix 'doc/design/OpenMemory-K07-端点过滤矩阵填报-v1.0.0.md' --openapi scripts/api_baseline.json   # 期望退出码 0（缺口清零）
python scripts/smoke_l3_2.py                                           # L3-2 冒烟（本地契约桩）
# 可选迁移幂等复核：alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```

## 2. OpenLLM 仓（D:\Trae CN\myproject\Dev\OpenLLM）

### 2.1 现状核对（2026-09-09 实测）

| 项目 | 值 |
|------|-----|
| 当前分支 | `feature/v2.13.0-openrag` |
| 工作树 | 106 M + 81 ??（以工作树为准） |
| S0 探活示例 | `backend/tests/unit/test_dps_probe_real_health.py`（未跟踪） |

> 以各仓工作树为准，先 `git status` 核对后分批提交。S0 探活等既有待提交文件归类（探活/脚本 → 文档 → 其余收口）。

### 2.2 建议分支与提交顺序

建议留在现分支 `feature/v2.13.0-openrag` 分批提交，或按你方惯例先开 `release/v2.13.0` 收口分支。建议批次 2~3 个（先核对内容再定类），顺序：S0 探活/新增测试 → 文档/既有代码 → 剩余全量收口。

### 2.3 命令模板

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenLLM'
git status --porcelain                          # 核对并记录留底
# 批 1：S0 探活与新增测试（示例；实际以 git status 为准）
git add 'backend/tests/unit/test_dps_probe_real_health.py'
git commit -m "feat(probe): S0 真实链路探活用例（test_dps_probe_real_health）"
# 批 2：既有源码/文档按类 add（示例占位，请替换为核对后的实际路径）
git add '<按 git status 归类的源码路径>' '<按 git status 归类的文档路径>'
git commit -m "feat: <按实际内容概括>"
# 批 3（如仍有剩余）：剩余收口
git add -A
git commit -m "chore: OpenLLM 既有待提交分批收口（S0 探活/S2 前置核对）"
```

### 2.4 提交后回归（OpenLLM）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenLLM'
python -m pytest tests -q        # 以仓内 pytest 配置（pytest.ini/pyproject.toml）为准
python -m ruff check src         # 以仓内 lint 配置为准
```

## 3. DPS 仓（D:\Trae CN\myproject\Dev\DPS）

### 3.1 现状核对（2026-09-09 实测）

| 项目 | 值 |
|------|-----|
| 当前分支 | `main` |
| 工作树 | 3 ??（无 M）：`doc/design/DPS-画像模板与标注模板扩展设计文档-v2.9.0.md`、`doc/design/DPS-设计评审记录-v2.9.0.md`、`doc/requirements/DPS-功能需求清单-v2.9.0.md` |

### 3.2 建议分支与提交顺序

留在 `main`，一次或按设计/需求拆两次提交即可（建议 1 批 = 1 提交，或 2 提交：需求文档 / 设计文档）。

### 3.3 命令模板

```powershell
cd 'D:\Trae CN\myproject\Dev\DPS'
git status --porcelain                          # 核对
git add 'doc/design/DPS-画像模板与标注模板扩展设计文档-v2.9.0.md' 'doc/design/DPS-设计评审记录-v2.9.0.md' 'doc/requirements/DPS-功能需求清单-v2.9.0.md'
git commit -m "docs(dps): v2.9.0 画像/标注模板扩展设计、评审记录与功能需求清单入库"
```

### 3.4 提交后回归（DPS）

```powershell
cd 'D:\Trae CN\myproject\Dev\DPS'
python -m pytest tests -q        # 以仓内 pytest 配置为准
```

## 4. OpenRAG 仓（D:\Trae CN\myproject\Dev\OpenRAG）

### 4.1 现状核对（2026-09-09 实测）

| 项目 | 值 |
|------|-----|
| 当前分支 | `master` |
| 工作树 | 无改动（clean） |

当前无 S0 探活/待提交产物，**无需放行**（建议提交数为 0）。若后续出现 S0 探活等产物，按下列模板核对后分批：

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git status --porcelain
git add '<核对后的探活/脚本/文档路径>'
git commit -m "feat(probe): S0 探活与既有待提交收口"
python -m pytest tests -q
```

## 5. OpenBase 仓（D:\Trae CN\myproject\Dev\OpenBase）

| 项目 | 值 |
|------|-----|
| 当前分支 | `main` |
| HEAD | `0713ec1`（feat(identity): 身份事件单向列表契约端点 GET /identity/events，Q-DESIGN-1 冻结） |
| 放行需求 | **已全部提交，无需放行**。跨系统 S2/联调相关 OpenBase 侧改动已随 0713ec1 及此前 S1b（P2-1）链完成 |

- 本次沙箱内已完成并提交（docs(intg)：S2 台账回写与跨仓提交放行清单）：`OpenBase-数据隔离实现任务卡-v1.0.0.md`（v1.3.0 → v1.4.0 回写）与本清单文件，commit hash 见最终执行记录。
- 仓库内 `dogfood-output/` 未跟踪文件属走查产物，**不属于放行范围**，请勿误提交。

## 6. 提交后跨仓联调回归提示

OpenMemory 提交 4 与 OpenBase（0713ec1 已就位）就绪后，进入**真实 HTTP 双签联调窗口**（移交部署/联调窗口与 S7，依据 S2 设计草案 v1.0.3 批准注记）：

1. OpenBase 侧拉起 `GET /api/v1/identity/events`（契约文档 doc/design/OpenBase-事件消费契约-v1.0.md，commit 0713ec1 冻结）。
2. OpenMemory 侧 PullChannel 以真实 HTTP 拉取事件列表，验证事件 `apply`（阻断集落库）、`event_id` 幂等（重复拉取不双写）、`blocked/{subject_id}` 查询生效。
3. 逐仓回归命令汇总：OpenMemory（§1.6）、OpenLLM（§2.4）、DPS（§3.4）、OpenRAG（§4.1），OpenBase 以 AGENTS.md 为准：`python -m pytest tests` + `python -m ruff check openbase tests`。
4. 原则边界①：事件通道属身份权威同步面，**不纳入** S7 主备切换演练矩阵；L3-2 冒烟用例以契约桩回放断言（已绿）为本地基线，真实通道结果作为 S7 级联验证输入。

## 附：建议提交批次与命令数汇总

| 仓 | 建议分支 | 建议提交批次（git commit 数） | 每批约需 git 命令 |
|----|---------|-------------------------------|-------------------|
| OpenMemory | release/v7.2.0 → release/v7.3.0 | **4**（基线 1 + S2 文档 1 + S2 源码/迁移/脚本 1 + S2 测试/CI 1） | add 2~5 条 + commit 1 条 + 回归 1~3 条/批 |
| OpenLLM | feature/v2.13.0-openrag（或收口分支） | **2~3**（S0 探活 / 既有源码文档 / 剩余收口） | 通用模板（先 git status 核对） |
| DPS | main | **1**（3 个未跟踪文档；可拆 2） | add 1 条 + commit 1 条 |
| OpenRAG | master | **0**（当前 clean；有产物时按需 1~2） | 通用模板 |
| OpenBase | main | **0**（无需放行；本次回写由沙箱内 docs(intg) 1 次提交承载） | 已执行 |

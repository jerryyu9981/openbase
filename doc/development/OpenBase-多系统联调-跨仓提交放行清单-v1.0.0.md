# OpenBase-多系统联调-跨仓提交放行清单-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-CROSSREPO-RELEASE-v1.0.0 |
| 版本 | v1.0.1 |
| 状态 | [Draft]（供用户沙箱外执行；每条命令执行前请以「第 0 步核对」实核各仓 git 状态） |
| 日期 | 2026-09-09 |
| 作者 | AD（跨项目分析） |
| 版本主题 | S2（OpenMemory 段）+ S3（OpenRAG 段）段门禁批准后的跨仓放行清单：OpenMemory v7.2 基线先行 + S2（v7.3 拟）五份文档与源码/迁移/测试分批提交；OpenRAG S3（v1.10.0 拟，§4）六份文档 + identity/中间件/配置 + storage/迁移/路由 + scripts/tests/CI 分批提交；OpenLLM/DPS S0 探活等既有待提交分批核对提交；OpenBase 侧已全部提交无需放行 |
| 上游依据 | OpenMemory S2 立项方案 v1.1.0 / 设计草案 v1.0.3 / DevLogReport v1.0.1 / 测试报告 v1.0.1 / doc/design/OpenMemory-K07-端点过滤矩阵填报 v1.0.1（[Approved]，2026-09-09 S2 段门禁人工批准五项全绿）；OpenRAG S3 立项方案 v1.1.0 / 设计草案 v1.0.1（[Approved]）/ DevLogReport v1.0.1（[Approved]，2026-09-09 S3 段门禁人工批准五项全绿）/ 测试报告 v1.0.0（[Final]）/ doc/design/OpenRAG-K07-端点过滤矩阵填报 v1.0.0（[Final]，121 行=豁免 10/覆盖 111）；OpenBase-数据隔离实现任务卡 v1.4.0（S2 段回写）与 v1.5.0（S3 段回写）；OpenBase commit 0713ec1=事件列表契约端点 GET /api/v1/identity/events（2026-09-09 冻结） |
| 适用范围 | 本清单涉及 OpenMemory / OpenLLM / DPS / OpenRAG 四个子系统 git 仓的放行提交作业，须由用户在沙箱外执行（沙箱内 git 仅允许操作 OpenBase 仓）；OpenBase 仓本次回写已在沙箱内提交（见 §5） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-09 | AD（跨项目分析） | 初始版本：S2（OpenMemory）段收口跨仓放行清单（OpenMemory v7.2 基线 + S2 v7.3 批次；OpenLLM/DPS/OpenRAG S0 探活等既有待提交；OpenBase 无需放行），含逐仓建议分支、提交顺序、git add/commit 模板与提交后回归命令 |
| v1.0.1 | 2026-09-09 | AD（跨项目分析） | S3（OpenRAG）段门禁批准（2026-09-09 五项全绿）后新增 OpenRAG 仓 S3 放行批次：§4 改写为 release/v1.10.0（拟）四批放行（文档 / identity·中间件·配置 / storage·迁移·路由 / scripts·tests·CI），含文件清单、git add/commit 模板与提交后回归命令；总览表 OpenRAG 行建议提交 0→4；OpenMemory/OpenLLM/DPS 原批次不变；同步任务卡 v1.4.0→v1.5.0（S3 段回写），本清单保持 [Draft] 供沙箱外执行 |

---

## 0. 使用说明与放行总原则

- 本文件为 **[Draft]** 放行指引，不是自动执行指令：沙箱仅允许提交 OpenBase 仓，其余四仓命令需用户人工在沙箱外执行。
- **放行顺序总体建议**：OpenMemory 先行（v7.2 基线 → S2 批次，四提交）→ OpenRAG（S3 批次，release/v1.10.0 拟，四提交，见 §4）→ OpenLLM / DPS（S0 探活等既有待提交，按仓分批）→ OpenBase（无需放行，S2/S3 台账回写已在沙箱内提交）。
- 每个提交前必做：`git status --porcelain` 核对、`git diff --cached --stat` 复查暂存内容仅含预期路径；**只 add 预期路径，不用 `git add -A` 兜底**（基线提交除外，见 §1.5 说明）。
- 中文文件名路径在 PowerShell 中一律用**单引号**包裹。
- 每个仓库「提交后回归」若失败：停止后续批次，修正后再继续；回归通过后再进行下一仓。
- 提交后回填：OpenMemory 实际 commit hash 需回填《OpenBase-数据隔离实现任务卡 v1.4.0》卡尾 S2 段执行摘要；OpenRAG 实际 commit hash 需回填任务卡 v1.5.0 卡尾 S3 段执行摘要；并同步各仓文档状态登记（本文档升版为 [Approved] 时一并登记，遵循文档版本管理规范）。

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

### 4.1 现状核对基线（2026-09-09 实测）

| 项目 | 值 |
|------|-----|
| HEAD | `959ef83`（959ef837a814a68d1f0efd03130d58ff251ef0dd，docs(v1.9.1): 发布文档同步——v1.9.1 发布闭环） |
| 当前分支 | `master` |
| 工作树 | S3 全部产物：**22 M + 32 ??**（共 54 项；identity/ 内 .pyc 属忽略项不计；以第 0 步实核为准）；**无历史未提交基线**（工作树改动全部属 S3 段，无 v1.x 旧版本滞留改动） |
| S3（v1.10.0 拟）产物 | 全部位于已修改/未跟踪工作树，因 git 沙箱受限尚未提交；无 alembic，迁移走 `src/openrag/storage/migrations.py` 幂等迁移器（create_all/DDL） |

**第 0 步核对命令**（执行任何提交前先跑）：

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git log -1 --format='%H %s'                        # 期望 959ef83...（v1.9.1 发布闭环）
git branch --show-current                          # 期望 master
(git status --porcelain).Count                     # 核对总行数（2026-09-09 实测 54=22M+32??）
git diff --cached --stat                           # 应无输出（无已暂存内容）
```

### 4.2 建议分支与提交顺序

- **提交 1~4（S3 批次）**：自 `master`（959ef83）切出 `release/v1.10.0`（S3 规划承载版本 v1.10.0 拟，Q-RG-1 定案），在分支上按「文档 → identity/中间件/配置 → storage/迁移/路由 → scripts/tests/CI」四批提交。因**无历史未提交基线**，无需基线提交；`git switch -c` 切分支不丢工作树改动。
- 提交顺序总览：

| 序号 | 分支 | 提交内容 | 建议 commit 主题 |
|------|------|---------|-----------------|
| 1 | release/v1.10.0 | S3 六份文档（仓根立项/设计草案 + doc/design K07 填报 md+matrix.json + doc/development DevLog + doc/test 测试报告） | docs(s3): OpenRAG S3 六份文档入库 |
| 2 | release/v1.10.0 | identity 包 + api/middleware（identity_gate/block_subject_gate/role_gate）+ 配置/装配/错误面/审计（settings/deps/main/router middleware/core exceptions/responses/exception_handlers/audit_logger） | feat(s3): 身份接入收口 identity/中间件/配置（协议头四态+B1、级联阻断、角色档位、审计六键、事件消费端、M1/M2） |
| 3 | release/v1.10.0 | storage（migrations/postgres/sqlite）+ models（collection/document/chunk）+ api/routes（collections/documents/index/pageindex/query）+ orchestrator/rag | feat(s3): 数据隔离 storage/迁移/路由（归属列幂等迁移+保留码回填+B2 碰撞防护、行控强制注入、复合唯一 409） |
| 4 | release/v1.10.0 | scripts（k07_endpoint_matrix/tenant_backfill_report/scan_*×4/smoke_l3_2/verify_env_contract/verify-env）+ tests（test_s3_*、test_isolation_matrix_endpoints、既有文档路由回归）+ run_tests.py + ci-cd.yml | test(s3): S3 T1~T11 RED 断言/K07 矩阵隔离用例/静态门禁与 L3-2 冒烟 + CI s3-static-gates job |

> 如需合并为 **3 批**：将批 2 + 批 3 合并为「源码一批」（文档 → 源码 → scripts/tests/CI）；不建议更细拆分（identity 与 storage/路由跨文件复用，按 T 拆会造成中间提交不可独立回归）。

### 4.3 S3 放行文件清单（四批 add 集合，2026-09-09 实测）

```text
# 批 1：六份文档（全部未跟踪）
OpenRAG-S3-数据隔离与身份接入收口立项方案-v1.0.0.md
OpenRAG-S3-数据隔离与身份接入收口设计草案-v1.0.0.md
doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.md
doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.matrix.json
doc/development/OpenRAG-S3-数据隔离与身份接入收口-DevLogReport-v1.0.0.md
doc/test/OpenRAG-S3-数据隔离与身份接入收口-测试报告-v1.0.0.md

# 批 2：identity / 中间件 / 配置 / 装配 / 审计（新增 + 已修改混合）
src/openrag/identity/                    # protocol_headers/verdict/inbound_gate/blocklist/event_consumer/role_map/tenancy/agent_principal/audit_identity/context/delegation_notes/error_codes/scope_exemption/__init__
src/openrag/api/middleware/identity_gate.py
src/openrag/api/middleware/block_subject_gate.py
src/openrag/api/middleware/role_gate.py
src/openrag/config/settings.py
src/openrag/api/deps.py                   # BlockSubjectGate resolver 装配 + store scope 注入入口
src/openrag/main.py                       # 中间件装配顺序
src/openrag/router/middleware.py          # B1：EdgeRouterMiddleware deprecated/不装配
src/openrag/core/exceptions.py            # 错误码扩展
src/openrag/api/responses.py              # 响应信封 request_id/detail
src/openrag/api/exception_handlers.py     # detail/request_id 映射
src/openrag/security/audit_logger.py      # detail.identity 六键注入

# 批 3：storage / 迁移 / 模型 / 路由 / 编排（新增 + 已修改混合）
src/openrag/storage/migrations.py         # s3_tenant_columns/s3_tenant_collision_guard/s3_composite_unique/s3_scope_exemption/s3_identity_blocklist 幂等迁移器
src/openrag/storage/postgres.py
src/openrag/storage/sqlite.py
src/openrag/models/collection.py          # tenant_code 归属位
src/openrag/models/document.py
src/openrag/models/chunk.py
src/openrag/api/routes/collections.py     # 域过滤/复合唯一 409
src/openrag/api/routes/documents.py
src/openrag/api/routes/index.py
src/openrag/api/routes/pageindex.py
src/openrag/api/routes/query.py           # 检索统一入口域过滤
src/openrag/orchestrator/rag.py           # 写链行控/幂等

# 批 4：scripts / tests / CI（新增 + 已修改混合）
scripts/k07_endpoint_matrix.py
scripts/tenant_backfill_report.py
scripts/scan_auto_purge.py
scripts/scan_no_edgerouter_assembly.py
scripts/scan_no_identity_header_bypass.py
scripts/scan_tenant_scope.py
scripts/smoke_l3_2.py
scripts/verify_env_contract.py
scripts/verify-env/                        # contract.json（schema v2，键分组）
tests/unit/test_s3_*.py                    # test_s3_t1~t11、test_s3_b2_backlog_closure
tests/unit/test_isolation_matrix_endpoints.py
tests/unit/api/test_api_routes_documents_text.py   # 既有文档路由回归（9 passed 保持语义）
run_tests.py                               # S3_SCAN_GATE_MODULES + 启动 env setdefault
.github/workflows/ci-cd.yml                # s3-static-gates job
```

> 以上为 2026-09-09 实测工作树（22 M + 32 ??）归类；执行前以 `git status --porcelain` 复核，若出现清单外路径先确认归属后再并入对应批次，**不要用 `git add -A` 兜底**。

### 4.4 放行步骤与命令模板

**切分支（提交 1 前）**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git switch -c release/v1.10.0                  # 自 master(959ef83) 切 S3 分支（工作树改动原样保留）
```

**提交 1 — S3 六份文档（release/v1.10.0）**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git add 'OpenRAG-S3-数据隔离与身份接入收口立项方案-v1.0.0.md' 'OpenRAG-S3-数据隔离与身份接入收口设计草案-v1.0.0.md'
git add 'doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.md' 'doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.matrix.json'
git add 'doc/development/OpenRAG-S3-数据隔离与身份接入收口-DevLogReport-v1.0.0.md' 'doc/test/OpenRAG-S3-数据隔离与身份接入收口-测试报告-v1.0.0.md'
git commit -m "docs(s3): OpenRAG S3 六份文档入库（立项 v1.1.0/设计草案 v1.0.1 [Approved]；DevLog v1.0.1 [Approved]/测试报告 v1.0.0/K07 填报 v1.0.0）"
```

**提交 2 — identity/中间件/配置**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git add 'src/openrag/identity' 'src/openrag/api/middleware/identity_gate.py' 'src/openrag/api/middleware/block_subject_gate.py' 'src/openrag/api/middleware/role_gate.py'
git add 'src/openrag/config/settings.py' 'src/openrag/api/deps.py' 'src/openrag/main.py' 'src/openrag/router/middleware.py' 'src/openrag/core/exceptions.py' 'src/openrag/api/responses.py' 'src/openrag/api/exception_handlers.py' 'src/openrag/security/audit_logger.py'
git commit -m "feat(s3): 身份接入收口 identity/中间件/配置（S3-T1 协议头白名单四态+B1、S3-T5 级联阻断事件消费端、S3-T6 D-V 映射、S3-T7 审计六键、S3-T9 角色档位、S3-T10 M1/M2 trust_mode）"
```

**提交 3 — storage/迁移/路由**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git add 'src/openrag/storage/migrations.py' 'src/openrag/storage/postgres.py' 'src/openrag/storage/sqlite.py'
git add 'src/openrag/models/collection.py' 'src/openrag/models/document.py' 'src/openrag/models/chunk.py'
git add 'src/openrag/api/routes/collections.py' 'src/openrag/api/routes/documents.py' 'src/openrag/api/routes/index.py' 'src/openrag/api/routes/pageindex.py' 'src/openrag/api/routes/query.py' 'src/openrag/orchestrator/rag.py'
git commit -m "feat(s3): 数据隔离 storage/迁移/路由（S3-T2 归属列幂等迁移+保留码 openrag-local 回填+B2 碰撞防护、S3-T3 行控强制注入、S3-T4 复合唯一 409、query 检索域过滤）"
```

**提交 4 — scripts/tests/CI**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git add 'scripts/k07_endpoint_matrix.py' 'scripts/tenant_backfill_report.py' 'scripts/scan_auto_purge.py' 'scripts/scan_no_edgerouter_assembly.py' 'scripts/scan_no_identity_header_bypass.py' 'scripts/scan_tenant_scope.py' 'scripts/smoke_l3_2.py' 'scripts/verify_env_contract.py' 'scripts/verify-env'
git add 'tests/unit/test_s3_*.py' 'tests/unit/test_isolation_matrix_endpoints.py' 'tests/unit/api/test_api_routes_documents_text.py'
git add 'run_tests.py' '.github/workflows/ci-cd.yml'
git commit -m "test(s3): S3 T1~T11 RED 断言/K07 矩阵隔离用例/四静态扫描与 L3-2 冒烟脚本 + CI s3-static-gates job"
git tag v1.10.0-rc.1                               # 可选：S3 收官打候选 tag
```

### 4.5 备注

- **无基线提交**：HEAD 959ef83=v1.9.1 干净基线，工作树改动全部属 S3（与 OpenMemory 的 v7.0~v7.2 未提交基线不同），无需「基线剔除」步骤；四批只是提交卫生切分。
- **中间批次回归**：批 2/批 3 为跨文件耦合源码（identity 与 storage/路由互相引用、既有测试随行扩展），**单批不一定能独立全绿**；全量回归门禁以批 4 之后为准（见 §4.6），各批提交前只核对「暂存区仅含预期路径」。
- **既有基线失败**：3 个枚举大小写类既有失败与本批无关（测试报告 §5 K-1 登记延续），不作为 S3 门禁口径；如仓内惯例需同步 CHANGELOG/Release-Note，S3 收官后按发布计划补 v1.10.0 版本文档。

### 4.6 提交后回归（OpenRAG）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
python -B -m pytest tests/unit -p no:cacheprovider            # 期望 S3 组 144 用例恒绿；既有基线除 3 个枚举大小写登记项外全绿
python -m ruff check src scripts tests/unit                   # 期望 0 错误（若含既有噪声，以新增/改动文件为准，见 DevLog §5）
python scripts/scan_no_edgerouter_assembly.py                  # 四静态扫描门禁：期望逐条退出码 0
python scripts/scan_no_identity_header_bypass.py
python scripts/scan_tenant_scope.py
python scripts/scan_auto_purge.py
python scripts/k07_endpoint_matrix.py                          # K07 矩阵核对（默认即核对模式；期望退出码 0 = 缺口清零/无漂移）
python scripts/smoke_l3_2.py                                   # L3-2 冒烟 + 段门禁自检五项（期望退出码 0；真实双签挂起登记不阻断）
python scripts/verify_env_contract.py --fail-fast              # 可选：verify-env 契约键对账（trust_mode 推导一致）
```

## 5. OpenBase 仓（D:\Trae CN\myproject\Dev\OpenBase）

| 项目 | 值 |
|------|-----|
| 当前分支 | `main` |
| HEAD | `0713ec1`（feat(identity): 身份事件单向列表契约端点 GET /identity/events，Q-DESIGN-1 冻结） |
| 放行需求 | **已全部提交，无需放行**。跨系统 S2/S3/联调相关 OpenBase 侧改动已随 0713ec1 及此前 S1b（P2-1）链完成 |

- 本次沙箱内已完成并提交（docs(intg)：S2 台账回写与跨仓提交放行清单）：`OpenBase-数据隔离实现任务卡-v1.0.0.md`（v1.3.0 → v1.4.0 回写）与本清单文件 v1.0.0，commit hash 见最终执行记录。
- 本次沙箱内再次提交（docs(intg)：S3 台账回写与跨仓提交放行清单更新）：任务卡 v1.4.0 → v1.5.0（S3/OpenRAG 段回写）、本清单 v1.0.0 → v1.0.1（§4 新增 OpenRAG S3 放行批次），commit hash 见最终执行记录。
- 仓库内 `dogfood-output/` 未跟踪文件属走查产物，**不属于放行范围**，请勿误提交。

## 6. 提交后跨仓联调回归提示

OpenMemory 提交 4 与 OpenRAG 提交 4 就绪后（OpenBase 0713ec1 已就位），进入**真实 HTTP 双签联调窗口**（移交部署/联调窗口与 S7，依据 S2 设计草案 v1.0.3 / OpenRAG S3 设计草案 v1.0.1 批准注记）：

1. OpenBase 侧拉起 `GET /api/v1/identity/events`（契约文档 doc/design/OpenBase-事件消费契约-v1.0.md，commit 0713ec1 冻结）。
2. OpenMemory 侧 PullChannel 以真实 HTTP 拉取事件列表，验证事件 `apply`（阻断集落库）、`event_id` 幂等（重复拉取不双写）、`blocked/{subject_id}` 查询生效。
3. 逐仓回归命令汇总：OpenMemory（§1.6）、OpenLLM（§2.4）、DPS（§3.4）、OpenRAG（§4.6），OpenBase 以 AGENTS.md 为准：`python -m pytest tests` + `python -m ruff check openbase tests`。
4. 原则边界①：事件通道属身份权威同步面，**不纳入** S7 主备切换演练矩阵；L3-2 冒烟用例以契约桩回放断言（已绿）为本地基线，真实通道结果作为 S7 级联验证输入。
5. OpenRAG（S3）侧在其 §4.6 回归通过后进入同一联调窗口：配置 `OPENRAG_L3_2_REAL_DOUBLE_SIGN_BASE_URL`，以 OpenBase 0713ec1 契约端点为真实事件源补跑 Pull 真实 HTTP 双签（Q-RG-7 挂起登记，门禁登记项完成前不视为最终通过），并回填 OpenRAG DevLog/测试报告与任务卡 v1.5.0 卡尾 S3 摘要；PG/Redis 实跑补验随部署验证窗口执行。

## 附：建议提交批次与命令数汇总

| 仓 | 建议分支 | 建议提交批次（git commit 数） | 每批约需 git 命令 |
|----|---------|-------------------------------|-------------------|
| OpenMemory | release/v7.2.0 → release/v7.3.0 | **4**（基线 1 + S2 文档 1 + S2 源码/迁移/脚本 1 + S2 测试/CI 1） | add 2~5 条 + commit 1 条 + 回归 1~3 条/批 |
| OpenLLM | feature/v2.13.0-openrag（或收口分支） | **2~3**（S0 探活 / 既有源码文档 / 剩余收口） | 通用模板（先 git status 核对） |
| DPS | main | **1**（3 个未跟踪文档；可拆 2） | add 1 条 + commit 1 条 |
| OpenRAG | release/v1.10.0（拟，自 master 959ef83 切出） | **4**（S3：文档 1 + identity/中间件/配置 1 + storage/迁移/路由 1 + scripts/tests/CI 1；可合并为 3） | add 1~4 条 + commit 1 条 + 回归 1~5 条/批（§4.6） |
| OpenBase | main | **0**（无需放行；S2/S3 台账回写由沙箱内 docs(intg) 提交承载） | 已执行 |

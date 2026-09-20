# OpenBase 设计开发追溯矩阵 - v1.4.7

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.7（四仓日志接入补完 · 日志域收官 · 跨仓，**承接型小版本**） |
| 文档版本 | v1.1.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-09-20 |
| 存放 | doc/development/ |

> **版本形态说明（编号来源，防误读）**：v1.4.7 为**承接型小版本**，Step 1/2 以差异化确认为主，**未产出独立版本设计文档**；故本矩阵的设计项（DT）来源为**设计输入三件套**——《OpenBase-单版本规划文档-v1.4.7》§2（版本范围）、《OpenBase-R384四仓施工派单-v1.0.0》（内部 v1.3.0）§5/§7（采集侧施工单与命名契约）、《OpenBase-R384改动包-v1.0.0》（内部 v1.2.0）。**DT-147 / TD-147 编号在本版本首次分配**（此前 v1.4.7 未产出本矩阵，属 Step 3 门禁缺口补齐项）。

---

## 1. 追溯矩阵（DT → TD → BL → 文件）

| DT | 设计项（来源） | TD | 关联 BL | 涉及文件 | 状态 |
|----|---------------|----|--------|---------|:----:|
| DT-147-01 | 采集文件命名契约：**结构化流**采集文件使用 `.jsonl`（《施工派单》§5 命名契约；规划 §2.1 条目 4「编排器输出 `{svc}-YYYYMMDD.jsonl`」） | TD-147-01 | **BL-147-04** | `scripts/service-orchestrator.ps1` | ✅ |
| DT-147-02 | 归档命名须匹配 `RepoLogAdapter` 文件名白名单（时间戳位于 `.err` **之前**、保留原扩展名） | TD-147-02 | **BL-147-04** | `scripts/service-orchestrator.ps1`（`Get-ServiceLogArchiveName`） | ✅ |
| DT-147-03 | 命名实测动作：**读侧、零副作用、判据不复刻**（引用适配器白名单常量） | TD-147-03 | **BL-147-04** | `scripts/verify_repo_log_naming.py`（新增）、`scripts/service-orchestrator.ps1`（`-Action namecheck`） | ✅ |
| DT-147-04 | rag-proxy 出站身份头注入策略：受信目标系统的身份语义与**跨域租户码冲突**处置（规划 §2.1 条目 5/6 支撑项；DEF-BE-147-005 复核裁定） | TD-147-04 | **BL-147-05（支撑）** | `openbase/settings.py`、`openbase/modules/rag_proxy/__init__.py`、`scripts/service-orchestrator.ps1` | ✅ |

**配套测试与文档件（随 TD 交付，非 DT 独立派生）**：

| TD | 测试/文档件 | 状态 |
|----|------------|:----:|
| TD-147-01/02/03 | `tests/test_r384_repo_log_naming.py`（13 例）、`tests/test_logs_service.py`（3 处 fixture 日期腐化修复） | ✅ |
| TD-147-04 | `tests/test_rag_proxy_identity_policy.py`（新增 3 例）、`tests/test_bl147_trust_env_wiring.py`（+1 例编排器声明护栏） | ✅ |
| TD-147-04 | 证据：`doc/test/evidence/v147/def005-multiprobe-20260920.json`、`def005-gateway-retest-20260920.json`；说明：`def005-rag400-probe-20260920.md`（v1.1.0） | ✅ |

## 2. Subtask CheckList（子任务状态表）

| 子任务 | 设计规划 | 状态 | 偏差说明 |
|--------|---------|:----:|---------|
| TD-147-01 命名单点 | 编排器内新增「当日命名」函数并统一调用（避免多处硬编码） | ✅ | 无 |
| TD-147-02 归档命名修复 | 归档名 `{base}-{HHmmss}{.err}{ext}`（时间戳在 `.err` 之前） | ✅ | 无 |
| TD-147-03 命名实测 | 新增独立校验工具 + `-Action namecheck` 三段实测 | ✅ | 无（判据不复刻：直接引用适配器白名单常量） |
| TD-147-04 身份注入策略 | 设计输入**未预设实现形态**；由 DEF-BE-147-005 复核裁定「方案 B：不注入身份头」 | ✅ | **有（显式登记）**：以**显式开关** `rag_inject_identity_headers`（默认 `true` 保持既有四维身份透传语义）实现，编排器对联调环境显式声明 `false`；**未采用**方案 A（实测 200 但 `items=[]`）与方案 C（跨仓放行）。原因、实测与回退路径见《OpenBase-问题跟踪记录-v1.4.7》§1 DEF-BE-147-005 与证据文档 v1.1.0 §4 |
| 未完成项 | — | **无** | 无推迟项 |

## 3. 版本控制记录（分支策略 + commit 约定）

| 项 | 内容 |
|----|------|
| 分支策略 | **`main` 直发**（承接型小版本，沿用 v1.4.6 策略；分支策略由 `.devflow/project-config.json` 配置） |
| commit 约定 | `type(scope): subject`（`feat` / `fix` / `docs` / `test` / `chore`）；footer 引用 BL / DEF 编号 |
| 本版本提交记录 | BL-147-04：`e6452b1`（`feat`，15 文件 / +2029 −40）；DEF-BE-147-005 修复 + Step 3/Step 4 门禁材料：**`be6a307`**（`fix(v1.4.7)`，27 文件）；推送状态：**未推送**（双远程推送待人工确认） |
| 双远程 | origin `main` + backup `main`（推送证据登记于《DevLogReport-v1.4.7》§6） |
| 回滚 | 代码回退（`git revert`）即可；本次新增开关默认值即「既有语义」，回退无数据面影响 |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-20 | AD-OpenBase-Dev | 初始创建（**补齐 v1.4.7 Step 3 门禁缺口**）：建立 DT-147-01~04 → TD-147-01~04 → BL-147-04/05 → 文件的双向追溯；Subtask CheckList 逐项核对并**显式登记 1 项偏差**（TD-147-04 以显式开关实现方案 B，附证据索引）；版本控制记录（分支策略 / commit 约定 / 回滚） |
| v1.1.0 | 2026-09-20 | AD-OpenBase-Dev | **回填提交与推送状态**：§3「本版本提交记录」补入 DEF-BE-147-005 修复 + Step 3/Step 4 门禁材料提交 **`be6a307`**（27 文件）及推送状态（**未推送，待人工确认**） |

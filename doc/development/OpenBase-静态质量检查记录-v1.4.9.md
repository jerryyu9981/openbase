# OpenBase 静态质量检查记录 - v1.4.9

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **OpenLLM**（编排与回写代码所在仓） |
| 版本号 | **v1.4.9**（上下文预算与回写质量） |
| 文档 | 静态质量检查记录（Step 3 产出 3） |
| 文档版本 | v1.1.2 |
| 状态 | [Review]（Step 3 收尾） |
| 日期 | 2026-09-29 |
| 检查人 | AD-OpenLLM-Dev |
| 检查对象 | 本版本 **8 个批次**全部生产代码与测试代码 ＋ 取证脚本 |
| 检查工具 | `ruff check`（lint）＋ `ruff check --select C901`（圈复杂度）＋ `pylint duplicate-code`（重复率）＋ `python -m compileall`／`py_compile`（语法） |
| 环境 | Windows / Python 3.10；cwd = `OpenLLM/backend` |

## 1. 检查项与结论（总览）

| # | 检查项 | 命令 | 范围 | 结果 |
|:-:|--------|------|------|------|
| 1 | **静态检查（lint）** | `python -m ruff check <文件…>` | 本版本改动的 12 个生产文件 ＋ 8 个新建测试文件 | **All checks passed** |
| 2 | **语法编译** | `python -m compileall -q main.py` | 入口与 lifespan（含新增接线） | **通过**（0 errors） |
| 3 | **未使用导入／符号** | 含于 `ruff check`（F401/F811/F821） | 同上 | 无告警 |
| 4 | **导入顺序与命名** | 含于 `ruff check`（I001/N） | 同上 | 无告警 |
| 5 | **复杂度与坏味道** | 含于 `ruff check`（C4/SIM/B 系列） | 同上 | 编期发现 3 处（SIM300／C420／B007）**均已修**，无残留 |

> **口径**：ruff 在本仓另有**历史遗留**告警（既有文件中的 typing 现代化 / 导入序等），**不在本次改动行**；本记录只对本版本**改动行与新建文件**负责，故以「改动面 0 告警」为通过判据。

## 2. 逐批次静态检查证据（与追溯矩阵 §5 同源）

| 批次 | 增量 | 改动文件（生产 / 测试） | `ruff check` 结果 |
|:----:|------|------------------------|-------------------|
| 1 | I-3 显式标记 | `prompt_pipeline.py` / `test_context_trim_markers.py` | All checks passed |
| 2 | I-1 跨段竞争池 | `prompt_pipeline.py` / `test_context_cross_segment_competition.py` | All checks passed |
| 2′ | I-2 丢弃原因明细 | `prompt_pipeline.py`、`context_metrics.py` / `test_context_dropped_detail.py` | All checks passed |
| 3 | I-5 仍超窗标记 | `prompt_pipeline.py`、`context_metrics.py` / `test_context_over_window_verifier.py` | All checks passed |
| 4 | I-6＋I-7 | `channel.py`、`channel_audit.py`、`component_pipeline.py`、`executor.py`、`core/config.py`、`openllm_gateway.py` / 3 个新测试 ＋ 1 个既有护栏更正 | All checks passed |
| 5 | I-8 接线 | `evaluate.py`、`profile_refine_gate.py`、`writeback_queue.py`、`openllm_gateway.py`、`main.py` / `test_profile_delta_and_precheck_wiring.py` | All checks passed |
| 6 | I-9 证据 | `evaluate.py`（fail-open 加固）/ — | All checks passed |
| 7 | **收尾补漏** | `prompt_pipeline.py`（安全余量 ＋ 回执字段）、`context_metrics.py`、`core/config.py` / `test_context_receipt_fields.py` | All checks passed |
| 7′ | **收尾一致性（续记）** | 取证脚本 `doc/test/evidence/cr149/v149_receipt_and_purity_probe.py` 与 `v149_increment_runner.py`（backend 根自动定位 ＋ 齐备性判定加固）**无生产代码改动** | All checks passed |
| **8** | **I-2 生产落线** | `assembler.py`（`format_context_with_items` ＋ 同源排序重构）、`component_pipeline.py`、`executor.py`、`api/openllm_gateway.py` / `test_segment_items_production_wiring.py`（含 1 处 `B905` 修） | All checks passed |
| **8′** | **门禁补齐** | 证据脚本 `doc/test/evidence/v149/cr149-l3-smoke-20260929.py`（真实实例冒烟） | All checks passed |

## 2b. 补充分组：技术债务增长率（3.4a，工具实测 ＋ 基线两侧比对）

| 项 | 阈值 | 实测 | 方法（**工具实测**，非「变更面核定」） |
|----|:----:|:----:|--------------------------------------|
| 新增 TODO 数 | ≤5 | **0** | 正则 `(TODO\|FIXME\|XXX\|HACK)`（大小写敏感）在 `基线..HEAD` **新增行**逐行匹配（新增 2630 行，命中 0） |
| 新增高复杂度函数数 | ≤3 | **3**（达上限） | `ruff --select C901`（`max-complexity=15`）在 **HEAD** 与**基线 `git worktree` 独立检出**两侧各跑一次，取差集（基线 5 个 → HEAD 8 个；新增＝`run_components` 26／`_build_writeback_callback` 16／`generate` 16） |
| 代码重复率增量 | ≤2% | **0** | `pylint --enable=duplicate-code`（`min-similarity-lines=10`）扫描 `app/` 全包两侧比对：`R0801` **22 → 22** |

> **与 v1.4.7 口径的差异（如实说明）**：v1.4.7 记录因「未配置工具」而标注「复杂度/重复率**未实测**」；本轮**已安装并运行** `ruff C901` 与 `pylint duplicate-code`，故口径由「变更面核定」升级为**可复算的工具实测 ＋ 两侧比对**。证据：`doc/test/evidence/v149/cr149-debt-growth-20260929.txt`。

## 3. 编期发现并修正的静态问题（如实登记）

| # | 工具规则 | 位置 | 问题 | 处置 |
|:-:|----------|------|------|------|
| 1 | `F821 Undefined name` | `channel.py` 新增 `component_channels()` | 缺 `from typing import Any` | 补齐导入（并修正其为 isort 正确位置） |
| 2 | `B007` 循环变量未使用 | 早期测试草稿 | 循环变量未使用 | 改为遍历 `.values()` |
| 3 | `SIM300` Yoda 条件 | `test_channel_audit_action_codes.py` | 常量在左的比较 | 改为集合比较 + 语义非空断言 |
| 4 | `C420` 字典推导 | `test_component_channel_routing.py` | 可用 `dict.fromkeys` | 改用 `dict.fromkeys` |
| 5 | `F811 重复导入` | `writeback_queue.py`（新增 `import json` 时） | 与既有 `json` 重复 | 去重（仅新增 `hashlib`） |
| **6** | **`B905` `zip()` 未显式 `strict=`** | `test_segment_items_production_wiring.py`（批次 8 新测试） | Python 3.10 起要求显式 `strict` | 改为 `zip(..., strict=True)`（配合前置长度断言） |

## 4. 显式未做的检查（如实登记，不含糊）

| 项 | 原因 |
|----|------|
| 类型检查（mypy/pyright） | 本仓**既有**未纳入 CI 的类型检查门（不属于本版新增约束）；本版**未**引入新类型检查门，避免扩大门禁范围 |
| 覆盖率门（`--cov`） | 属 **Step 4 测试阶段**的判据（本仓既有约定）；本记录不作为覆盖率结论 |
| 安全扫描（SAST/依赖漏洞） | 属 Step 4 / 运维阶段输入清单；本记录不冒充 |

> **口径更新（批次 8）**：原「圈复杂度／重复率**未实测**」一项**已不再适用** —— 本轮已实际安装并运行 `ruff C901` 与 `pylint duplicate-code`（见 §2b），故本记录**不再**保留「未实测」标注。

## 5. 结论

**通过**：本版本改动面静态检查 **0 告警**、语法编译通过、编期发现的 **6 类**静态问题**全部修正**且无残留；**技术债务增长率三项为工具实测**（新增 TODO 0／新增高复杂度函数 3（达上限，已逐函数登记）／重复块增量 0）。
本记录**不**覆盖运行时行为（由 §3.5 实际运行验证与 Step 3 逻辑审查承接）、覆盖率与安全扫描（分别由 Step 4 测试／运维阶段承接）。

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.1.2 | 2026-09-29 | AD-OpenLLM-Dev | **批次 8（I-2 生产落线）＋ 3.4a 债务增长率纳入检查范围**：① §2 新增第 8／8′ 行（4 个生产文件 ＋ 1 新测试 ＋ 1 证据脚本，`ruff` 全 `All checks passed`）；② **新增 §2b 技术债务增长率**（`ruff C901` ＋ `pylint duplicate-code`，**HEAD 与基线 worktree 两侧比对** ⇒ **0 / 3 / 0**）并**如实说明**与 v1.4.7「未实测」口径的差异（本轮工具已实际运行）；③ §3 新增第 6 类（`B905`）；④ §4 移除已不适用的「复杂度/重复率未实测」标注；⑤ 文头版本/日期/检查对象同步（**v1.1.2**、7 批次 → **8 批次 ＋ 取证脚本**）。结论不变（改动面 0 告警）。 |
| v1.1.1 | 2026-09-29 | AD-OpenLLM-Dev | **批次 7 收尾一致性续记纳入检查范围**：新增第 7′ 行 —— 取证脚本 `v149_receipt_and_purity_probe.py`（backend 根自动定位 ＋ 齐备性判定加固）`ruff check` **All checks passed**；本批**无生产代码改动**；文头版本号/日期/检查对象的**滞后**一并更正（v1.0.0 → **v1.1.1**、6 批次 → **7 批次**）。结论不变。 |
| v1.1.0 | 2026-09-28 | AD-OpenLLM-Dev | **收尾补漏批次纳入检查范围**：新增第 7 批（预算安全余量 ＋ 回执必填字段齐备率）改动面 lint `All checks passed`；本版本检查范围由「6 批次」扩为「**7 批次**」，结论不变（改动面 0 告警）。 |
| v1.0.0 | 2026-09-28 | AD-OpenLLM-Dev | 初始创建：6 批次改动面 lint 0 告警、语法编译通过、5 类编期静态问题修正记录；**显式登记未做的检查**（类型检查/覆盖率/SAST）及其归属阶段。状态 [Review] |

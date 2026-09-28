# OpenBase 设计开发追溯矩阵 - v1.4.9

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **OpenLLM**（编排与回写代码所在仓） |
| 版本号 | **v1.4.9**（上下文预算与回写质量） |
| 文档 | 设计开发追溯矩阵（Step 3 产出 2，TD-ID ↔ 设计项 ↔ 代码落点） |
| 文档版本 | v1.0.0 |
| 状态 | [Review]（Step 3 进行中） |
| 日期 | 2026-09-28 |
| 上游依据 | 设计基线 **v1.2.0**（[Approved]）；《需求设计追溯矩阵-v1.4.9》v1.2.0 |
| 代码仓 | `d:\Trae CN\myproject\Dev\OpenLLM\backend`（OpenBase 仓仅承载文档） |

## 1. TD-ID 追溯（设计项 → 代码落点 → 状态）

| TD-ID | 设计项（DT） | 需求 | 代码落点（OpenLLM） | 判据 | Phase | 状态 |
|-------|-------------|------|---------------------|:----:|:-----:|:----:|
| **TD-14901** | DT-149-03（回执扩展）／I-3 显式标记 | FR-149-06 | `app/edgerouter/orchestration/prompt_pipeline.py`（`_trim_segment` 报告 ＋ 文档同步） | **AC-149-03/04** | P1 | ✅ **已完成（本批）** |
| TD-14902 | DT-149-03（回执扩展）／I-2 逐条丢弃原因 | FR-149-06 | 同上（需**条目身份**（source/id/score）从取数层透传至段内裁剪 ⇒ 先做**管道改造**） | AC-149-05 | P1 | ⏳ **本批未做**（见 §3 推迟说明） |
| TD-14903 | DT-149-01／I-1 跨段配额竞争 | FR-149-03 | `prompt_pipeline.py`（预算池）＋ `BudgetPolicy` | AC-149-01/02 | P2 | ⏳ 待做（批次 2） |
| TD-14904 | DT-149-02／I-5 仍超窗显式失败标记 | FR-149-05 | `prompt_pipeline.py`（verifier 路径） | **AC-149-12** | P2 | ⏳ 待做（批次 3） |
| TD-14905 | DT-149-15／I-6 取数层逐组件通道路由 | FR-149-09 | `app/edgerouter/orchestration/component_pipeline.py`、`app/identity/channel.py` | AC-149-13 | P5 | ⏳ 待做（批次 4） |
| TD-14906 | DT-149-16／I-7 审计动作码定稿 | FR-149-10 | `app/identity/channel_audit.py`（动作码定稿 ＋ 组件级事件类型） | AC-149-14 | P5 | ⏳ 待做（批次 4） |
| TD-14907 | DT-149-17／I-8 画像增量与频控预检接线 | FR-149-11 | `app/edgerouter/orchestration/evaluate.py`、`profile_refine_gate.py` | AC-149-15 | P6 | ⏳ 待做（批次 5） |
| TD-14908 | DT-149-18／I-9 评测集与判据扩展 | FR-149-12 | `doc/test/evidence/cr149/`（执行器 ＋ 评测集） | AC-149-16 | P6 | ⏳ 待做（批次 6） |
| TD-14909 | DT-149-19／I-10 重排器条件项 | FR-149-13 | 仅登记（无代码变更） | AC-149-17（条件） | — | ✅ **按设计不实施** |

## 2. Subtask CheckList（文件级；命名与设计规划一致）

| # | 文件 | 操作 | 命名与设计一致 | 状态 |
|:-:|------|------|:--------------:|:----:|
| 1 | `app/edgerouter/orchestration/prompt_pipeline.py` | 修改（`_trim_segment` 报告 ＋ docstring） | ✅（设计 §3.6／API §2 指向该模块） | ✅ 完成 |
| 2 | `tests/unit/test_context_trim_markers.py` | **新建** | ✅（测试命名遵循仓内 `test_context_*` 约定） | ✅ 完成 |
| 3 | `prompt_pipeline.py` 预算池（跨段竞争） | 修改 | ✅ | ⏳ 批次 2 |
| 4 | `component_pipeline.py` ＋ `channel.py`（取数层路由） | 修改 | ✅ | ⏳ 批次 4 |
| 5 | `channel_audit.py`（动作码定稿） | 修改 | ✅ | ⏳ 批次 4 |

> **无新增/重命名/删除文件未落地项被隐藏**：本批仅 1 新建测试文件（已落地），其余均为后续批次（已在上表逐项标注批次）。

## 3. 本批实施记录（批次 1＝I-3）与推迟说明

**已完成**：
- `_trim_segment` 段报告新增 **`hard_truncated`**（恒有：本段是否发生文本级截断）与 **`degraded="empty_guard"`**（仅在**保底一条被触发**时出现，即该段本会被裁剪清空 ⇒ 显式降级）；`report` 类型标注随值域扩展；模块 docstring 同步（文档-实现一致）。
- **零变化保证**：无需裁剪时报告**仍缺失**（`composition.truncated` 无该段）⇒ 与既有实现逐字一致。
- **不误报**：整条丢弃（`truncated_items=0`）时 `hard_truncated=False` 且**不出现** `degraded` 键。

**推迟说明（如实）**：**I-2（逐条丢弃原因明细 `dropped[{source,id,reason}]`）本批未做** —— 原因：`_trim_segment` 当前只接触**文本单元**（`(编号前缀, 正文)`），**不持有条目身份**（source/id/score）；要让「原因明细」成立必须先**从取数层把条目元数据透传进段内裁剪**（属管道改造，非观测增量）。⇒ 按「先做最小可验证增量」原则，I-2 顺延至**批次 2 前置**（与 I-1 同批或紧前），并已在 TD-14902 标注。

## 4. 版本控制记录

| 项 | 约定 |
|----|------|
| 分支策略 | **github-flow**（沿用仓内现状：`feature/s4-identity-channel-b` 为编排/通道路线特性分支） |
| commit 模板 | `type(scope): subject`，footer 引用 **TD-ID / RT-ID** |
| 本批提交 | `feat(orchestration): 段报告显式标记 hard_truncated / degraded=empty_guard（I-3）` ＋ footer `TD-14901 / RT-149-10 / AC-149-03,04` |
| TDD 合规 | 测试先于生产代码提交（本批：`test_context_trim_markers.py` 先建并 **RED（3 failed）**，后实现 **GREEN（5 passed）**） |
| 备份 | 双远程（origin ＋ backup，非 `--mirror`） |

## 5. 验证证据（本批）

| 项 | 结果 |
|----|------|
| RED | `tests/unit/test_context_trim_markers.py` → **3 failed, 2 passed**（标记缺失，符合预期） |
| GREEN | 同文件 → **5 passed** |
| 相关面回归 | 预算/裁剪/排序/画像 4 文件 → **62 passed** |
| 静态检查 | `ruff check`（生产 ＋ 测试文件）→ **All checks passed** |
| 全量回归 | 见 DevLogReport（与基线逐项对比，零新增失败） |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-28 | AD-OpenLLM-Dev | 初始创建：9 条 TD-ID（TD-14901~14909）↔ DT/需求/代码落点/判据/Phase；Subtask CheckList（含命名一致性核对）；**批次 1（I-3）已完成**并如实登记 **I-2 推迟原因**；版本控制记录与验证证据。状态 [Review] |

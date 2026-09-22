# OpenBase 设计开发追溯矩阵 - v1.4.8

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.8（会话编排前置与回写闭环） |
| 文档版本 | v1.4.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-09-21 |
| 更新日期 | 2026-09-21 |
| 存放 | doc/development/ |
| 上游依据 | 《OpenBase-需求设计追溯矩阵-v1.4.8》（[Approved]）、《OpenBase-设计基线及开发测试移交说明-v1.4.8》（[Approved]）、《OpenBase-会话编排派单-OpenLLM-v1.0.0》v1.2.0（[Approved]） |

> **版本形态说明（防误读，`VC-017` 后更新）**：v1.4.8 主体施工落在 **OpenLLM 仓**（第零段 / 前置零 / 第一批），openbase-ui 仓配合提交会话标识。**`VC-017`（2026-09-21，用户决策「直接修改其他四仓」）已取消「本仓不实施跨仓代码改动」的施工约束**：跨仓落点由本会话**直接实施并自测**（八批，见 §4），派单文档转为「契约与验收依据」而非「唯一施工路径」。`DT / TD` 编号在本版本首次分配。

---

## 1. 追溯矩阵（DT → TD → BL → 落点）

| DT | 设计项（来源） | TD | 关联 BL | 涉及文件 / 落点 | 状态 |
|----|---------------|----|--------|-----------------|:----:|
| DT-148-01 | 基线工装（仅观测）：Prompt 组成计量 / 检索快照 / 回执落库 / 归因 A·B / 固定集与评分表 / 汇总脚本 | TD-148-01 | BL-148-01 | **跨仓**：OpenLLM `edgerouter/orchestration/`、`routing_trace`、`openllm_gateway.py`；**本仓**：`doc/design/OpenBase-B0B1基线报告框架-v1.4.8.md` | ✅ 契约就绪 |
| DT-148-02 | F-02 窗口上限**最长键优先**匹配 + 日期化模型名用例 | TD-148-02 | BL-148-02 | **跨仓**：OpenLLM `context_manager.py:43-86`/`:176-178`/`:198-200` | ✅ 契约就绪 |
| DT-148-03 | 双路径收敛（共用步骤抽取） | TD-148-03 | BL-148-03 | **跨仓**：OpenLLM `openllm_gateway.py`（同步 + `_run_stream_components`） | ✅ 契约就绪 |
| DT-148-04 | 会话轴接入：会话标识字段 + 历史按窗口纳入 + assembler 历史位 + 会话落库 | TD-148-04 | BL-148-04 | **跨仓**：OpenLLM `openllm_gateway.py`、`conversations.py`；**openbase-ui** `llm.ts`；**本仓**：`doc/design/OpenBase-API接口设计文档-v1.4.8.md` §2 | ✅ 契约就绪 |
| DT-148-05 | 三路回写接齐（+profile / 流式补齐 / 回执 / 失败隔离） | TD-148-05 | BL-148-05 | **跨仓**：OpenLLM `_build_writeback_callback`、`_run_stream_components`、WritebackStore | ✅ 契约就绪 |
| DT-148-06 | 回写幂等键修正：`(session_id, seq, target)` + DB `max_seq+1` + 迁移 | TD-148-06 | BL-148-06 | **跨仓**：OpenLLM WritebackStore、`openllm_gateway.py:620-626`；**本仓**：`doc/design/OpenBase-数据库设计文档-v1.4.8.md` §3.3/§4 | ✅ 契约就绪 |
| DT-148-07 | B0/B1 基线测量与报告 | TD-148-07 | BL-148-07（条件，D3） | **本仓**：`doc/design/OpenBase-B0B1基线报告框架-v1.4.8.md`；**跨仓**：工装回执 | ✅ 框架就绪（测量挂 D3） |
| DT-148-08 | 编排归属与 DSL 边界定界 | TD-148-08 | BL-148-08 | **本仓**：`doc/design/OpenBase-编排归属与DSL边界定界-v1.4.8.md` | ✅ 已落地 |
| DT-148-C1 | 数据模型：`routing_trace` 计量字段 / 会话标识口径 / 幂等键迁移 | TD-148-09 | BL-148-01/06 | **本仓**：`doc/design/OpenBase-数据库设计文档-v1.4.8.md` §3 | ✅ 契约就绪 |
| DT-148-C2 | API 契约：`session_id`（可选）+ 回写回执查询 + 计量导出 | TD-148-10 | BL-148-04/05 | **本仓**：`doc/design/OpenBase-API接口设计文档-v1.4.8.md` §2/§4/§5 | ✅ 契约就绪 |
| DT-148-C3 | 安全：计量/回执脱敏红线、无新权限码 | TD-148-11 | BL-148-01 | **本仓**：`doc/design/OpenBase-安全设计说明-v1.4.8.md` | ✅ 契约就绪 |
| DT-148-C4 | 非功能：回写不阻塞 / 缺省兼容 / 迁移不破 | TD-148-12 | BL-148-03/05/06 | **本仓**：`doc/design/OpenBase-非功能设计说明-v1.4.8.md` | ✅ 契约就绪 |
| DT-148-C5 | 可观测性：计量回执 + 回写回执可查可导出 | TD-148-13 | BL-148-01/05 | **本仓**：`doc/design/OpenBase-非功能设计说明-v1.4.8.md` §6 | ✅ 契约就绪 |
| （执行项）跨仓分发与会话标识派单 | 向 OpenLLM 仓分发已批准派单；向 openbase-ui 仓出具会话标识提交派单（D2） | TD-148-14 | BL-148-04 | **本仓**：`doc/planning/OpenBase-会话编排派单分发清单-v1.4.8.md`、`doc/planning/OpenBase-会话标识提交派单-openbase-ui-v1.0.0.md`；**跨仓**：OpenLLM 仓改动见 §4 | ✅ 已出具；**实施方式已变更**（`VC-017`：直接实施，见 §4） |

**配套测试与证据件（随 TD 交付）**：

| TD | 测试 / 证据件 | 状态 |
|----|--------------|:----:|
| TD-148-01~14 | 本仓**文档型验证**（L1 格式校验 + L2 打开验证 + L3 走查）见《DevLogReport-v1.4.8》§5 | ✅ |
| TD-148-14 | 分发回执登记（接收仓回执待回收） | ⏳ 待接收仓响应 |

---

## 2. Subtask CheckList（子任务状态表）

| 子任务 | 设计规划 | 状态 | 偏差说明 |
|--------|---------|:----:|---------|
| TD-148-01 基线工装 | 仅观测、不改行为；工装 1~7 | ✅ 契约就绪 | 无（实现属 OpenLLM 仓） |
| TD-148-02 F-02 修正 | 最长键优先 | ✅ 契约就绪 | 无 |
| TD-148-03 双路径收敛 | 共用步骤抽取 | ✅ 契约就绪 | 无 |
| TD-148-04 会话轴 | 历史第五类素材，插入位 `System+画像+记忆+知识库+[历史]+Query` | ✅ 契约就绪 | **设计定稿项**：需求 §4.4 要求「历史插入位置须明确」，已在架构 AD-03 定稿 |
| TD-148-05 三路回写 | +profile；流式补齐；回执 | ✅ 契约就绪 | **有条件**：流式回写可行性按 R3 前置核实结论落地；不可行须显式声明写入契约 |
| TD-148-06 幂等键修正 | 会话维度 + `max_seq+1` | ✅ 契约就绪 | 无 |
| TD-148-07 B0/B1 | 报告框架（本仓） | ✅ 框架就绪 | **有条件**：测量与报告受 D3 约束，框架已就位并保留测量入口 |
| TD-148-08 DSL 边界 | 边界条款写入设计文档 | ✅ 已落地 | 无（Step 2 交付，Step 3 归档确认） |
| TD-148-09~13 跨切面契约 | 数据 / API / 安全 / 非功能 / 可观测性 | ✅ 契约就绪 | 无 |
| TD-148-14 跨仓分发 | 分发清单 + openbase-ui 派单 | ✅ 已出具 | **有（显式登记）**：本仓不含 OpenLLM 侧代码实现（`VC-014`），验收以接收仓回执为准；接收仓排期窗口未定（属 R1） |
| 未完成项 | — | **无本仓未完成项** | 跨仓实施项（BL-148-01~06）待接收仓执行；BL-148-07 测量待 D3 |

---

## 3. 版本控制记录（分支策略 + commit 约定）

| 项 | 内容 |
|----|------|
| 分支策略 | **`main` 直发**（承接型小版本，沿用 v1.4.6/v1.4.7 策略；分支策略由 `.devflow/project-config.json` 配置） |
| commit 约定 | `type(scope): subject`（`feat` / `fix` / `docs` / `test` / `chore`）；footer 引用 **RT-ID / BL-ID** |
| RT-ID footer 约定 | 本版本提交 footer 引用 `RT-148-xx`（如 `Refs: RT-148-08`）与 `BL-148-xx` |
| 本版本提交 | 本仓为文档型交付（设计契约 + 派单 + 开发记录），提交类型 `docs(v1.4.8)`；**未推送**（双远程推送待人工确认） |
| 双远程 | origin `main` + backup `main` |
| 回滚 | 本仓无代码改动，文档回退按 `git revert`；**跨仓改动回退**：以 §4 登记的文件为单位回退（当前未提交，可整体丢弃） |

---

## 4. 跨仓直接实施登记（`VC-017` 后补记）

> 本节补记 `VC-017` 后的实际实施：TD-148-01~08 与 TD-148-C1~C5 的跨仓落点（OpenLLM 仓）已由本会话**直接实施**，本仓口径由「派单 + 回执验收」变为「直接实施 + 单元用例/护栏证据」。明细（八批、12 源文件、10 测试文件、99 passed）见《OpenBase-DevLogReport-v1.4.8》§13；逐批证据见 `doc/test/evidence/v148/openllm-crossrepo-*.txt`。

| TD | 设计项 | 实施状态（`VC-017` 后） | 关键落点（OpenLLM 仓） | 证据 |
|----|--------|------------------------|------------------------|------|
| TD-148-01 | 第零段基线工装（仅观测） | ✅ **工装 1~7 齐备**：计量 / 检索快照 / 回执落库 / 归因 A / **归因 B 工具** / **固定集与评分表（35 条 / 7 场景 / 2 组负例）** / **汇总脚本**；**真实基线数据受 `D3` 条件约束未测** | `prompt_pipeline.py`、`context_metrics.py`、`attribution_b.py`、`golden_set.py`、`baseline_report.py`、`openllm_gateway.py`、`data/golden_set_v1.json` | 批次 4/5/6/10 |
| TD-148-02 | F-02 窗口最长键优先 | ✅ 已实施并有回归用例 | `context_manager.py` | 批次 1 |
| TD-148-03 | 双路径收敛（共用步骤） | ✅ **完成**：组装环节共用（`build_prompt`）；**组件执行环节共用（`component_pipeline.run_components`，两路径私有实现已删除）**；源码级护栏防复发。端到端一致性判定属 Step 4 | `prompt_pipeline.py`、`component_pipeline.py`、`executor.py`、`openllm_gateway.py` | 批次 3/4/12 |
| TD-148-04 | 会话轴接入 | ✅ **完成**：`session_id` 契约、历史构建与两路径注入、回写取真实会话标识、会话落库与检索按会话标识对齐（口径单一来源 `services/session_scope.py`）、**前端提交会话标识（D2，`openbase-ui/src/core/session.ts` + `llm.ts`）** 均已实施 | `history.py`、`assembler.py`、`openllm_gateway.py`、`services/session_scope.py`、`services/conversation_service.py`、`api/conversations.py`、`openbase-ui/src/core/{session.ts,api/llm.ts}` | 批次 2/3/9/11 |
| TD-148-05 | 三路回写接齐 | ✅ 已实施（profile 第三路 + 流式三路 + 回执与查询接口） | `executor.py`、`explicit.py`、`auto.py`、`openllm_gateway.py`、`writeback_queue.py` | 批次 7/8 |
| TD-148-06 | 回写幂等键修正（硬判据） | ✅ 已实施（`max_seq+1`，删除进程内计数器）；运行期硬判据回归属 Step 4 | `writeback_queue.py`、`openllm_gateway.py` | 批次 1 |
| TD-148-07 | B0/B1 基线报告（条件，D3） | ⏳ 契约与框架就绪；`D3` 未确认，测量挂起 | — | — |
| TD-148-08 | DSL 边界定界（本仓） | ✅ 已落地（设计文档） | — | — |
| TD-148-C1~C5 | 数据 / API / 安全 / 非功能 / 可观测性契约 | ✅ 契约落地并在跨仓实施中兑现（新增两个查询端点、回执字段、脱敏红线用例） | 见批次 5~8 | 批次 5~8 |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-21 | AD-OpenBase-Dev | 初始创建。建立 DT-148-01~08 + C1~C5 → TD-148-01~14 → BL-148-01~08 → 落点（本仓文档 / 跨仓）双向追溯；Subtask CheckList 逐项核对并显式登记 4 项偏差（历史插入位定稿、流式回写条件、D3 条件、VC-014 跨仓实施边界）；版本控制记录（分支策略 / commit 约定 / RT-ID footer / 回滚）。状态 [Review] |
| v1.1.0 | 2026-09-21 | AD-OpenBase-Dev | **按 `VC-017`（约束反转）补记**：新增 §4「跨仓直接实施登记」逐 TD 给出实施状态（TD-148-02/05/06 与 C1~C5 已实施；TD-148-01/03/04 部分完成并注明缺口；TD-148-07 受 D3 挂起）；更新版本形态说明（取消「本仓不实施跨仓代码改动」约束）、TD-148-14 行（实施方式变更）；原 §4 修订历史顺延为 §5。状态 [Review] |
| v1.2.0 | 2026-09-21 | AD-OpenBase-Dev | **补记第十批**：§4 中 TD-148-01（第零段工装）由「部分完成」更新为「**工装 1~7 齐备**」（新增归因 B 工具 / 固定集与评分表 / 汇总脚本），并注明真实基线数据受 `D3` 条件约束未测；落点补 `attribution_b.py`、`golden_set.py`、`baseline_report.py`、`data/golden_set_v1.json`。状态 [Review] |
| v1.3.0 | 2026-09-21 | AD-OpenBase-Dev | **补记第十一批**：TD-148-04（会话轴接入）由「基本完成」更新为「**完成**」——新增前端会话标识提交（D2：`openbase-ui/src/core/session.ts` + `core/api/llm.ts`，仓库位置经用户确认为本仓；前端 204 passed / `vue-tsc` 0 errors）。状态 [Review] |
| v1.4.0 | 2026-09-21 | AD-OpenBase-Dev | **补记第十二批**：TD-148-03（双路径收敛）由「部分完成」更新为「**完成**」——新增组件执行共用步骤 `component_pipeline.run_components`，同步路径删除私有 `_run_component`、流式路径删除私有 `_run_one` 与调度循环；登记 1 项语义变更（RAG 适配器未注册 → 降级而非回退）。状态 [Review] |
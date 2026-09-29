# OpenBase 测试移交说明 - v1.4.9

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **OpenLLM**（编排与回写代码所在仓） |
| 版本号 | **v1.4.9**（上下文预算与回写质量，承接型小版本） |
| 文档 | 测试移交说明（Step 3 产出 6，`coding-stage-execution` §3.10／`project-document-management` 阶段 3 产物） |
| 文档版本 | v1.0.0 |
| 状态 | [Review]（待人工批准后进入 Step 4） |
| 作者 | AD-OpenLLM-Dev |
| 移交对象 | 测试负责人／测试工程师（Step 4 测试阶段） |
| 创建日期 | 2026-09-29 |
| 存放 | `doc/development/` |
| 上游依据 | 《开发审计移交材料-v1.4.9》v1.0.1；《DevLogReport-v1.4.9》v1.1.3；《设计开发追溯矩阵-v1.4.9》v1.9.3；《阶段审计报告-Stage3-v1.4.9》v1.3.1 |

---

## 1. 移交范围

| 项 | 内容 |
|----|------|
| 交付代码 | OpenLLM 仓 `backend/`：**13 个生产文件**（批次 1~8）＋ **11 个测试文件**（新增 10 / 修改 1）；基线 `d7742c7` → `d4bff29`，`25 files changed, 2967 insertions(+), 89 deletions(-)` |
| 交付形态 | **两仓均未推送**（本地提交）：OpenLLM **10 笔代码**＋1 笔文档；OpenBase **12 笔文档** |
| 本版增量 | I-1 跨段配额竞争／I-2 逐条丢弃原因明细（含**生产落线**）／I-3 显式标记／I-5 仍超窗显式失败标记／I-6 取数层逐组件通道路由／I-7 审计动作码定稿／I-8 画像增量与频控预检接线／I-9 评测集与判据扩展 |
| 不在本次测试范围 | Step 5 部署与灰度、发布验证；跨仓（DPS/OpenMemory/OpenRAG）自身版本的测试；openbase-ui 前端（v1.4.8 D2）改动**尚未提交**，不在本版代码基线内 |

## 2. 测试环境与入口

| 项 | 值 |
|----|-----|
| 落点与入口 | `d:\Trae CN\myproject\Dev\OpenLLM\backend`；以编排器等价 Env 启动：`python -m uvicorn main:app --host 127.0.0.1 --port <端口>` |
| 环境变量来源 | 仓库既有 `.env` ＋ `.env.shared-infra`（**密钥不落盘、不打印**）；启动脚本样例见 `doc/test/evidence/v149/cr149-instance-8041-20260929.txt` 首部 |
| 健康检查 | `GET /openllm/v1/health` → 200（`data.status=healthy`；逐组件 `channel` 可见） |
| 对话（非流式/流式） | `POST /openllm/v1/chat`／`POST /openllm/v1/chat/stream`（需 `Authorization: Bearer <token>`） |
| 登录 | `POST /api/v1/auth/login`（开发账号示例：`v148-perf` / `Perf#148aB`，见 `backend/scripts/run_perf_batch.py`） |
| 轨迹回执 | `GET /openllm/v1/trace/{request_id}` → `routing_trace.context_metrics`（**判据主要取证面**） |
| 回写回执 | `GET /openllm/v1/writeback/receipts?session_id=…` |
| 请求要点 | 预算窗口按「模型声明窗口 ∩ 部署生效窗口」解析；`model=auto` 走 5 因子路由；`session_id` 可选（缺省按用户记账） |

## 3. 开关矩阵（测试必须区分「出厂默认」与「工作区生效值」）

| 开关 | 出厂默认 | 工作区 `.env` | 测试要点 |
|------|:--------:|:------------:|----------|
| `CONTEXT_BUDGET_ENABLED` | **False** | `true` | 关闭 ⇒ 行为与 v1.4.8 **逐字一致**（回执**零新增字段**）；开启 ⇒ 回执 10 必填字段齐备 |
| `CONTEXT_CROSS_SEGMENT_COMPETITION_ENABLED` | **False** | 未设（False） | 关闭 ⇒ 各段静态配额（逐字一致）；开启 ⇒ 池回填，**T1 不破**（Σ素材 used ≤ available） |
| `COMPONENT_CHANNEL_ROUTING_ENABLED` | **False** | 未设（False） | 关闭 ⇒ 仅整体偏好、轨迹零新增维度；开启 ⇒ 逐组件标签独立、与请求级计数**互不污染** |
| `WRITEBACK_DECISION_ENABLED` | **False** | `true` | 价值闸门（沿用 v1.4.8 已具备能力，本版不改语义） |
| `PROFILE_LLM_REFINE_ENABLED` | **False** | 未设（False） | 只交付**接线**；**生效**受 D3 约束，不在本版承诺内 |
| `CONTEXT_SAFETY_MARGIN_TOKENS` | 256 | 未设（256） | 开启预算时 `available_budget = 窗口 − 输出预留 − **安全余量**` |

> **红线**：**出厂默认必须为关闭**；任何「关闭路径行为变化」都是**兼容性缺陷**（NFR-149-02／AC-149-09），应判 P0。

## 4. 判据复现命令（口径与 Step 3 证据同源）

| 目的 | 命令（在 `OpenLLM/backend` 或证据目录下执行） | 期望 |
|------|---------------------------------------------|------|
| 回执齐备率／关闭态零新增字段／不复用旧裁剪链路／无敏感落痕／超窗率 0／配置键结构护栏 | `python doc/test/evidence/cr149/v149_receipt_and_purity_probe.py` | **6/6 PASS**（任意 cwd 可跑，自动定位 backend） |
| 增量判据样本集（I-1~I-8 离线） | `python doc/test/evidence/cr149/v149_increment_runner.py` | **离线 7/7 PASS**；运行态 4 项**预期** `not_covered` |
| L3 冒烟（真实实例，6 例） | `python doc/test/evidence/v149/cr149-l3-smoke-20260929.py` | **6/6 PASS**（需实例已启动；含回执齐备/纯度/超窗/明细自洽/硬截断可见） |
| 全量回归 ＋ 基线对照 | `python -m pytest tests/unit tests/integration -q` | 与基线 `cr149-t36-full.txt` 的 **21 项失败逐 node id 相同**（即零新增失败）；本版通过数 **3772** |
| 本版新增护栏（点名） | `python -m pytest tests/unit/test_context_receipt_fields.py tests/unit/test_segment_items_production_wiring.py tests/unit/test_context_cross_segment_competition.py tests/unit/test_context_dropped_detail.py tests/unit/test_context_over_window_verifier.py tests/unit/test_component_channel_routing.py tests/unit/test_channel_audit_action_codes.py tests/unit/test_component_channel_audit_wiring.py tests/unit/test_profile_delta_and_precheck_wiring.py tests/unit/test_context_trim_markers.py` | 全通过（10 文件） |

## 5. 建议的测试重点（按风险排序）

| # | 重点 | 说明与判据 |
|:-:|------|-----------|
| 1 | **关闭即逐字回退**（兼容性红线） | 逐开关关闭态比对 v1.4.8 回执字段集合：**不得新增任何字段**；判据 AC-149-09 |
| 2 | **回执齐备率 100%**（预算生效请求） | 10 必填字段**键在且取值非 null**（`degraded` 允许 null）＋ `available_budget` 与公式自洽；判据 AC-149-05 |
| 3 | **超窗率 0** 与「仍超窗」显式标记 | 可容纳输入永不超窗；不可容纳时 `over_window=true` ＋ 溢出额度（**不静默**）；判据 AC-149-12 |
| 4 | **条目身份 ⇒ 裁剪明细**（批次 8 新增能力） | 需**真实检索数据**（`memory` 召回非空或 `openrag` 可用）：预算生效且该段有身份时，`dropped` 应含 `{source,id,reason}` 且 `len(dropped) ≤ Σ truncated[*].dropped_items`；本版仅以单元护栏证明贯通，**运行态实测属本阶段** |
| 5 | **跨段竞争池不变量**（开启态） | T1：Σ素材 used ≤ available（不超窗）；T2：**保底一条**不被竞争挤掉；段内取舍单位不变（T10） |
| 6 | **逐组件通道隔离与审计** | 组件级状态互不覆盖；请求级计数不被组件失败污染；动作码定稿取值域（含 `channel_component_failover` 的 `component` 维度）；同故障期去重 |
| 7 | **频控预检 fail-open** | `message_precheck`／`profile_delta_precheck` 异常**不得**阻断回写；预检拒绝时不得写入 |
| 8 | **无敏感落痕** | 回执/轨迹不含令牌、密钥、完整请求体、片段正文；判据 AC-149-11（SEC-149-01） |
| 9 | **双路径一致性** | 同步与流式同口径（回执字段、预算窗口、身份传入、动作码）——本版刻意统一，回归时注意不要分叉 |

## 6. 已知受限项与未覆盖项（**不得计为「已通过」**）

| 类别 | 项 | 说明 |
|------|----|------|
| 受限（**D4**） | I-4 `used_fragments` 跨仓回写**运行态** | 字段定义已冻结（API §3），跨仓落点未确认 |
| 受限（**D3**） | 画像 LLM 提炼**生效** | 仅交付接线；生效需评测支撑 |
| 受限（**环境**） | I-1／I-6／I-8 运行态段 | 需真机/多组件可用才可统计 |
| 受限（**环境**） | **条目身份运行态实测** | 本机 `openrag` 曾 `unavailable`、`memory` 召回 0 条目 ⇒ 运行时 `dropped` 为空属**预期**；需具备真实检索数据后复测 |
| 遗留（低） | 池上界用汇总 `Σdropped_tokens`（估值偏大） | T1 由一阶项封顶；登记为后续可选项 |
| 遗留（低） | 3 个函数**达**圈复杂度阈值上限（`run_components`／`_build_writeback_callback`／`generate`） | 均为接线型门控/fail-open 分支；登记为下版本重构候选 |
| 既有环境性失败 | 全量回归 **21 项** | 401 统一格式／模型路由接线／real-contract 默认值开关／流式收尾等；**与改动面无交集**，不随本版修复 |

## 7. 环境使用提示（避免误判为缺陷）

1. **组件可用性会波动**：`openrag`／`dps`／`open_memory` 常在会话间变化 ⇒ 组件级**降级**属设计内行为，且必须**如实留痕**（`degraded`／`errors`／ERROR 日志），**不得静默**；测试应区分「组件不可用（环境）」与「代码缺陷」。
2. **回写重试至上限会打 ERROR**：`writeback_queue` 目标不可用时重试 3 次后记 ERROR（可观测，非缺陷）。
3. **健康检查不等于全组件可用**：`data.status=healthy` 与逐组件 `status` 需分别读。
4. **不要把夹具结论当运行态结论**：判据探针/执行器为**夹具级**证据；运行态统计须用真实实例（如 L3 冒烟），并在报告中标注样本量。

## 8. 准入／准出建议

| 项 | 建议 |
|----|------|
| 准入（进入 Step 4） | Stage3 审计通过（本版为「通过并附条件」）＋ 本文档与《开发审计移交材料》齐备 |
| 必测门禁 | 接口/集成/E2E/回归/**覆盖率**（`--cov`）/合规/UAT —— 覆盖率门为**本阶段首次执行**（Step 3 未做，已如实登记） |
| 准出（进入 Step 5）建议 | 无未闭环 P0/P1；上表 §6 受限项**如实标注**且不计入通过；`AC-149-05/12` 的**足量样本统计**须给出数值与样本量；测试跳过项须写明原因/影响/补测计划 |
| 移交物 | 测试计划／测试用例／测试报告（含跳过项说明与 E2E 证据）／测试回溯对比审计报告（`doc/audit/verification/`） |

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-29 | AD-OpenLLM-Dev | 初始创建（补齐 `coding-stage-execution` §3.10 要求的**测试移交说明**，与《开发审计移交材料-v1.4.9》配套）：移交范围与上限、测试环境与入口（含端点与账号来源）、**开关矩阵（区分出厂默认与工作区生效值）**、判据复现命令（探针 6/6／执行器 7/7／L3 冒烟 6/6／全量回归与基线对照）、9 项测试重点（含批次 8 新增的「条目身份 ⇒ 裁剪明细」及其运行态复测要求）、受限与未覆盖项 7 类、环境使用提示 4 条、准入准出建议。状态 [Review] |

# 上下文精装配与基础组件通道优化技术方案

| 项 | 内容 |
|----|------|
| 项目 | OpenBase（开放底座）／OpenLLM（大模型网关） |
| 适用版本 | v1.4.8 迭代（会话编排前置与回写闭环）之后的优化批次 |
| 文档版本 | v1.12.0 |
| 状态 | [Draft] |
| 作者 | AD-OpenBase-Dev（架构设计） |
| 关联审计 | 本轮四问审计（双通道 / 组件决策 / 回写 / 上下文组装） |
| 关联缺陷与登记项 | `DEF-BE-148-027`、`DEF-BE-148-028`、`DEF-BE-148-029`（已闭环）；本方案新增待登记项 6 项（见 §10） |
| 关联基准证据 | `doc/test/evidence/local-model-bench/`（Ollama 小模型精度×时延基准：`README.md`、`merged-bench.md`、两批实测 JSON/CSV）；`doc/test/evidence/cr149/`（第一批运行态探针：预算裁剪 / 并行取数） |
| 目标链路 | 智能体对话 → OpenLLM 自动对接 DPS 画像 / 记忆 / 知识库 → 装配上下文 → 投喂 LLM → 回写 |
| 日期 | 2026-09-27 |

## 1. 现状定性

四项审计结论与支撑证据如下，后续所有优化都以这些事实为起点。

| 维度 | 现状 | 实测证据 |
|------|------|----------|
| 主备双通道 | 通道 B（编排 + 真实契约）已接线并跑通；通道 A（直连降级接管）只存在状态机与等价矩阵，业务路径 0 调用点；组件级"备"里只有内置 RAG 与模型 fallback 是真回退 | `CHANNEL_PREFERENCE=b-primary` 生效；`ChannelStateManager`/`record_b_component_failure` 仅被单测与脚本引用；E2E 两路径 PASS（`rag_source=external`、`kb_id_source=external`、`degraded=[]`） |
| 内置 RAG 备通道 | 代码路径可达、数据面为空 | 探针实测：`knowledge_bases.status='active'` 0 行、`backend/data/faiss/` 0 个索引目录 → `_builtin_rag_search` 返回 0 条 |
| 组件决策 | 规则优先 + 阈值 0.85 + 信号并集；单次关键词命中仅 0.8（不达标，走"回落最优候选"），≥2 次命中 0.95 才进入并集；LLM 兜底分类器与 YAML 规则热更新均未接线 | `component_router.py` 的 `R001~R005` 与 `_eval_*` 置信度；生产侧 `ComponentRouter()` 以默认规则构造，`llm_classifier=None`、无 `rules_path` |
| 执行顺序 | 路径映射 A/B/C/D，`memory → rag → llm`，llm 恒末；默认串行（`OPENLLM_ENABLE_PARALLEL=false`）；画像取数位置两路径不一致 | 流式 timeline：`auto_component_decision → memory → rag → profile_fetch → llm`；同步端点则在编排前先 `profile_fetch` |
| 回写 | 三路（memory/rag/profile）异步队列落地，幂等键 `(session_id, seq, target)`、重试 3 次指数退避、启动恢复带双上界（30 分钟/200 行） | 回写队列表实测三路 `done`、`retry_count=0` |
| 回写缺口 | 写侧"价值/重要度/频控/去重"决策器整体未接线；rag 路无"有价值才入库"判定；画像增量提炼粗糙 | `orchestration/evaluate.py` 全仓无调用点；`save_if_valuable` 仅存在于 `/writeback` API 契约；`_resolve_profile_updates` 用 2~4 字词切片与三档语气关键词 |
| 上下文组装 | 六段固定模板、全程分段计量与归因；**没有任何预算裁剪**；`system` 段恒为空 | 单轮实测 `segment_tokens`：同步 `{profile:128, memory:8167, rag:1668}`，流式 `{profile:128, memory:5321~7095, rag:1929~1967}`；`prompt_pipeline` 注释明确"只观测、不改行为，裁剪属 v1.4.9 第二批" |
| 已备好但未接线的抓手 | rag `rerank` / `score_threshold`；`MODEL_CONTEXT_LIMITS`（只用于编码器与历史预算）；`ComponentRouter(llm_classifier/rules_path)`；`ChannelStateManager`；`evaluate.py` | 网关 `_rag_handler` 仅传 `kb_id/query/top_k`，适配器默认 `rerank=False`、`score_threshold=None` |

运行环境实测约束（决定本地模型选型的边界）：本机无 NVIDIA GPU（`nvidia-smi` 缺失、OpenLLM 启动报 NVML 初始化失败）、CPU 为 i5-8400（6 核 6 线程）、内存 11.9 GB；Ollama 在 `127.0.0.1:11434` 与 `192.168.0.4:11434` 均不可达；模型注册表中 `qwen3:0.6b`、`qwen2.5:0.5b`、`llama3.2:1b` 全部 `inactive`，当前唯一生效的对话模型是远程 `deepseek-v4-flash`（`api.deepseek.com`）。

## 2. 设计原则

1. 精度优先来自"选得准"，而不是"塞得多"：先重排与去重，再考虑压缩，最后才裁剪。
2. 装配必须可预算：每段有明确 token 配额与溢出策略，超限可观测（而不是静默塞满）。
3. 精炼按需触发、有硬预算、可降级：任何模型精炼失败都退回确定性规则路径，不阻塞对话。
4. 不叠加串行时延：画像拉取与组件执行并行、可并行的取数不排队。
5. 单一实现供两条路径共用，避免同步/流式再次分叉。
6. 观测与判定分离：计量与回执只读，不改变注入内容。

## 3. 目标架构：上下文装配流水线 v2

现状是"取数 → 拼接"，目标改为四段流水线，每段各有产出物与回执。

```
取数(Retrieve)          选择(Select)             预算(Compress)          组装(Assemble)
profile ┐               重排 rerank            分段配额              system + 引用编号
memory  ├─ 并行取数 ─▶  score_threshold  ─▶   相关性排序截断   ─▶   + 注入清单回执
rag     ┘               去重(内容 hash)         溢出策略             (segment_tokens / truncated)
        │               时效/权威权重           (可插模型精炼)
        └─ 通道裁决(B 主 / A 备)与首备探针
```

### 3.1 取数

画像拉取与组件执行改为同一批次并行发起（三者互不依赖），两条路径统一为 `auth → 并行(profile_fetch ∥ memory ∥ rag) → 组装 → llm`。组件的串并行不再依赖全局开关 `OPENLLM_ENABLE_PARALLEL`，改由依赖图判定（当前 memory/rag 无依赖，具备并行条件）。通道裁决接入取数层：每个组件取数前经通道裁决器拿"本次走主还是备"，并在连续失败达阈值时切换（见 §4.1）。

**已实施（v1.3.0 第一批第 6 项）——画像段并行与两路径时序统一**：画像与组件互不依赖，但原实现为**串行且两路径顺序相反**（同步「先 `profile_fetch` 后组件」、流式「先组件后画像」）。现改为**并发句柄**：调用方在组件执行之前构造句柄（构造即启动后台取数），在**组装 Prompt 之前**统一收割（`PipelineExecutor` 内唯一收割点）。收益：画像耗时与组件耗时重叠（探针实测分段各 0.15 s 时，单轮墙钟由 0.312 s 降至 0.156 s，**省下 0.156 s**），且两条路径取数时序一致。

**未实施（留待第二批）**：通道裁决尚未进入取数层（通道 A 无业务调用点，见 §4.1 与 §10 登记项 1）。

**已实施（v1.5.0 第二批第 ② 项）——组件依赖图调度**：组件的串并行原**只看全局开关** `OPENLLM_ENABLE_PARALLEL`（默认 False ⇒ 恒串行），而 memory/rag **互不依赖**（不读对方结果）→ 本可并行的被白白串行化，且「严格顺序」这类**语义**诉求被压在一个全局布尔里。现改为**声明式依赖图**驱动：新增 `component_graph.dependency_levels()`（Kahn 式波次划分）与 `component_pipeline.resolve_schedule_plan()`（返回「波次 ＋ 同波次可否并发」），**无依赖 ⇒ 同波次并发**，**严格顺序用依赖声明** `OPENLLM_COMPONENT_DEPENDENCIES`（如 `memory:rag`）表达；成环 ⇒ fail-safe 退化为单波次保序（不把请求打挂）。探针实测：无依赖时 `memory/rag` 各 0.12 s，墙钟 **0.25 s → 0.125 s**（并行后减半）；声明 `memory:rag` 后事件序列严格为 `rag→memory`、**不重叠**。开关 `COMPONENT_DEPENDENCY_SCHEDULING_ENABLED` 默认关闭（关闭时调度语义与既有实现逐字一致）。

### 3.2 选择

三项改动，都不需要新增模型部署：

- 启用检索侧重排：组件条目参数透传 `rerank`（默认 true）与 `score_threshold`（按知识库配置或场景默认，例如 0.15），复用 OpenRAG 服务端重排能力；`openrag_client.retrieve` 已支持，`openrag.py` 的 `search()` 已透传，仅需在网关 handler 与流水线条目参数中接线。
- 内容去重：对同一轮 memory/rag 条目按内容 hash（或首 64 字 shingles）去重，避免同一事实在多条记忆里重复占用预算。
- 权重排序：在重排分数之外叠加时效与来源权重（记忆按 `updated_at` 衰减、画像字段按维度白名单、知识库条目保留原始 score），产出统一的 `rank_score` 供预算层使用。

### 3.3 预算

装配层引入分段配额与溢出策略，配额随模型窗口绑定（`MODEL_CONTEXT_LIMITS` 已有 max_tokens，可复用）：

| 段 | 配额（相对可用窗口） | 溢出策略 |
|----|----------------------|----------|
| system | 固定预留（≤5%） | 不裁剪（仅观测） |
| profile | ≤5% | 按维度优先级保留（person → business → 其他），超出丢弃低优先维度 |
| memory | ≤30%（**默认标定 28%**） | 按 `rank_score` 降序保留整条，末尾条目整体丢弃，不做半条截断；**裁剪将清空该段时保底一条**（见下） |
| rag | ≤40%（**默认标定 37%**） | 同上；单条超过单条上限（如 800 token）时按句边界截断并标注 |
| history | ≤20%（**默认标定 19%**） | 沿用现有窗口截取（丢最旧保最近）；**同样受保底一条保护** |
| query + 模板开销 | **余量 ≥5%** | 不裁剪 |

**余量约束（v1.10.0 标定，判据 T1 的结构保证）**：上表「query + 模板开销余量」是本方案**原有要求**（`query` 与段标记/换行不参与配额），但第一批实现把 5 段比例设为 `0.05/0.05/0.30/0.40/0.20`（**和恰为 1.00**）⇒ 各段满额时 `prompt_total_tokens = available + 查询 + 开销 > available`，与 T1「prompt 总长不超窗口扣减输出预留」**结构性冲突**（由 §7 执行器以「填满配额」夹具实测暴露）。故标定为 **`0.05/0.05/0.28/0.37/0.19`（和 = 0.94）**，并以不变量 `Σ 比例 ≤ 0.95` 锁定（配置键同值）。

**保底一条（v1.10.0，判据 T2）**：配额裁剪以「整条丢弃」为主；但若**单条素材本身即大于该段配额**，原实现会一路丢到空（实测 history 段 `used=0`，配额被白白浪费、该段归因彻底缺失）。故增加保底：**仅当裁剪将清空该段时**，保留首条并**硬性压进配额**（先句边界、再按比例收敛，且连同渲染编号前缀一并计入，保证 `used ≤ quota`），并记 `truncated_items`。可装下首条时不触发 ⇒ 既有「整条丢弃」语义不变。

**`quota = 0` 的语义（v1.10.0 显式化）**：视为**「不限」= 不裁剪**（fail-open）——避免误配 `CONTEXT_QUOTA_*_RATIO=0` 静默清空整段；判据 T1 的「各段 `used ≤ quota`」**仅对 `quota > 0` 的段**成立，观测里 `quota=0` 即「不限」。

产出物新增两个观测字段：`text` 层级的 `truncated: {segment: {dropped_items, dropped_tokens, truncated_items}}` 与 `budget: {segment: {quota, used}}`，与现有 `segment_tokens`/`attribution_a` 一同落 `routing_trace.context_metrics`。裁剪规则与配额通过配置键开关（缺省开启），并保证与"计量只读"的边界：计量读的是裁剪后的结果。

### 3.4 精炼

精炼分两档，确定性规则在先，模型在最后：

- 规则档（默认，零延时）：去重、按 score/时效排序、按配额整条裁剪、相邻记忆条目合并同义重复行、剥离元数据噪声（`trace_id:None` 一类平铺字段）。
- 模型档（默认关闭，按 §5.5 选型与 §5.8 预算启用）：对"条数多、单条冗长、主题分散"的记忆段或知识段做抽取式压缩或要点摘要，压缩后以编号列表回填。按实测结论，模型档只走异步档或 GPU 节点，在线档不引入生成式模型，判别式重排器除外。

两档共用同一回执字段：`refine: {mode: rule|model, model: <code>, in_tokens, out_tokens, elapsed_ms, fallback: bool}`。

**【实施状态（v1.12.0 仓内一致性审计，逐项取证）】**

| 规则档子项 | 状态 | 取证 |
|------------|------|------|
| 去重（段内保留首条） | **已实施**（第一批，`CONTEXT_DEDUP_ENABLED` 默认 True） | `prompt_pipeline._trim_segment` ① 段内去重 ＋ `_normalize_key`（压缩空白与大小写） |
| 按配额整条裁剪 ＋ 单条句边界截断 | **已实施**（第一批；保底一条见 v1.10.0） | `_trim_segment` ② / ③ ＋ `_fit_single_unit` |
| **剥离元数据噪声**（`trace_id:None` 一类平铺字段） | **未实施** | 全仓 `app/` 检索 `strip_metadata` / `METADATA_NOISE` / `noise` **零命中**；`PromptAssembler.format_context` 的平铺分支（`key: value`）**不过滤 `None`/空值、无噪声键名单** |
| **相邻记忆条目合并同义重复行** | **未实施** | 现有去重为**全段精确重复即丢弃**（非合并），且**不做同义判定**；`_normalize_key` 注释所称「同义重复」实为**归一化后的精确重复**，二者不等价 |
| 模型档（抽取式压缩 / 要点摘要） | **未实施**（第三批） | 见 §5 / §6 第三批；判据 T6 依赖达标模型与推理节点 |
| `refine` 回执字段 | **未实施** | 全仓 `app/` 检索 `"refine"` **零命中**（既无 `rule` 档回执，也无 `model` 档回执） |

> **结论**：§3.4 的**规则档**中「去重 / 裁剪 / 截断」已实施，但**元数据噪声剥离**与**相邻同义合并**两项**尚未实施**，`refine` 回执字段亦未落痕 —— 均已登记为 §10 待登记项 7，**不影响**已实施项与既有判据的结论。

### 3.5 组装

保留六段顺序（`system → profile → memory → rag → history → query`），新增两项：

- 启用 `system` 段：注入统一系统指令（身份与边界、回答风格、引用要求），不再把这类约束塞进用户消息。
- 为注入条目追加稳定引用编号（`[M1]`、`[K1]`），与归因 A 的片段索引对齐，便于回答可追溯到具体条目。

**【实施状态（v1.12.0 仓内一致性审计）】**：`system` 段启用**已实施**（第一批，`CONTEXT_SYSTEM_PROMPT_ENABLED`）；**引用编号 `[M1]`/`[K1]` 未实施** —— 取证：全仓 `app/` 检索 `[M{` / `[K{` / `[M1]` / `[K1]` **零命中**；`PromptAssembler._format_list` 与 `prompt_pipeline._trim_segment` 的 `render()` 均只产出 `"{序号}. {正文}"`（且 `_trim_segment` 会在裁剪/去重后**重排序号**，与「稳定编号」要求相反）。已登记为 §10 待登记项 7。

## 4. 四个问题的优化方案

### 4.1 主备双通道

现状是"设计有 A/B、运行只有 B"，需要先做一次定性决策，再补运行时能力。三条路线与取舍：

| 路线 | 内容 | 优点 | 代价 |
|------|------|------|------|
| 接线（推荐） | 在取数与回写路径接入 `ChannelStateManager`：组件级降级调用 `record_b_component_failure`，llm-proxy 探活调用 `record_upstream_probe`；达阈值按配置自动或人工显式回落 A；回切保留演练窗口 | 主备名副其实，故障可接管 | 需要 A 通道具备等价能力（见下） |
| 降级为探活专用 | 只保留"B 不健康 → 告警 + 人工切换开关"，A 仅承载健康探活/管理面原子操作 | 改动小、风险低 | 对话路径仍无备 |
| 废止 | 删除 A 通道对话语义，文档明确"当前为 B 单通道"，只保留组件级契约开关 | 消除误导 | 失去降级承接能力 |

配套两项必做（无论选哪条路线）：

- 内置 RAG 补底座：为内置 RAG 预置至少一个租户级知识库记录与 FAISS 索引，或在文档与配置中明确"内置 RAG 仅在有本地索引时生效"。当前"备通道存在但无内容"会在真实故障时表现为"接管成功、注入为空"。**【部分实施（v1.6.0）】**：「无内容」这一事实已由健康探针**前置可视化**（见下）；**种子动作（KB 记录 ＋ FAISS 索引）仍需运行态 DB 与嵌入模型**，本批次未执行 —— 探测实测 `faiss_root_exists=true` 但 `indexes=0`、`has_base=false`。故**当前口径明确为「内置 RAG 仅在有本地索引时生效」**，`reason` 字段直接给出该结论。
- 备通道健康探针 **【已实施（v1.6.0）】**：把"主/备可用性"纳入 `GET /openllm/v1/health` 的 components 探测（外部 OpenRAG/OpenMemory/DPS、内置 RAG 索引数、Ollama 可达性），供人工验证与自动裁决共用同一事实源。实现：新增 `_probe_builtin_rag(db)`（KB 行数 ＋ FAISS 索引数 ＋ `has_base`，无底座时 `reason` 显式说明「备通道接管后将注入为空」）、`_probe_ollama()`（`GET {OLLAMA_HOST}/api/tags` 只读面、2s 独立超时）与 `_count_faiss_indexes(root)`；`_probe_components(db)` 一次 `asyncio.gather` 并行探测 **5 项**并共用既有结果缓存；`/health` 端点增 `db` 依赖以统计 KB 行数（DB 不可用时该项降级为 `unavailable` ＋ `reason`，**探测不抛异常**）。实测 `components` 键集合 = `{dps, openrag, openmemory, builtin_rag, ollama}`，其中 `builtin_rag.status=unavailable`、`reason="内置 RAG 无底座（KB 0 行 / FAISS 0 索引）⇒ 备通道接管后将注入为空"`、`ollama.status=ok, models=2`。

人工验证口径（每项都给出可观测字段）：主通道看 `routing_trace.components.rag_source=external`；切到备通道看 `rag_source=builtin` 与 `builtin_fallback_reason`；通道裁决看 health 的 `components.*.channel` 与审计事件（**待实施：`channel` 字段取决于 §9 问题 1 的通道定性裁定**）；契约开关（`OPENLLM_*_REAL`）切换后看目标端点变化。**备通道是否可依赖**另看 health 的 `components.builtin_rag.has_base`（**v1.6.0 起可观测**）。

**【v1.11.0 口径收敛】** 上述「切到备通道看 `rag_source=builtin` 与 `builtin_fallback_reason`」此前**只在同步路径成立**：流式路径的接管发生在**共用组件步骤**（`component_pipeline.run_components`），该步骤只落 `rag_source`、**不落归因** ⇒ 流式轨迹缺「为何接管」。v1.11.0 已收敛为：① 共用步骤补落 `builtin_fallback_reason`（`ComponentRunResult` 新字段，120 字符截断）；② 两路径**共用同一落痕函数** `_merge_rag_trace()` 写 `routing_trace.components`（杜绝字段各自手写再次分叉）；③ 组装缺失 / 超时仍**不触发**回退（`DEF-BE-148-012` 语义不变）。**「审计事件」的落点**当前为接管 **WARNING 日志**（含归因），**独立的审计落库（`AuditLog`）未接入** —— 已登记为 §10 待登记项 6。

### 4.2 组件决策

| 改动 | 说明 |
|------|------|
| 候选明细落 trace | `routing_trace.decision` 增加 `candidates: [{rule_id, confidence, qualified, reason}]`，让"为什么只连一种"可复盘 |
| 阈值与单次命中语义对齐 **【已实施（v1.8.0）】** | 单次关键词命中 0.8 低于阈值 0.85，实际走"回落最优候选"；建议把 R001/R002 单次命中定为 0.86（或把阈值下调至 0.8），使"达标判定"与"最终决策"不再隐性分叉 |
| LLM 兜底接线（带预算） **【已实施（v1.8.0，开关默认关闭）】** | 规则完全无命中时，用一个小模型分类器补判（超时 300ms、失败即回落规则），并通过 `ComponentRouter(llm_classifier=...)` 注入 |
| 规则集可配置 **【已实施（v1.8.0）】** | 通过 `rules_path` 加载 YAML/JSON 规则（键名已在配置契约中），免改代码即可调整关键词与阈值 |
| 顺序优化 **【已实施（v1.5.0）】** | 断言"无依赖即并行"；`memory` 与 `rag` 并行取数，`profile` 与其同批；需要严格顺序的场景（如先画像后记忆）用依赖声明表达，不用全局开关 |

**已实施细节（v1.8.0 第二批，组件决策三余项）**：

- **阈值与单次命中语义对齐**：`R001`/`R002` **单次**命中置信度 0.8 → **0.86**（≥ 阈值 0.85）；`R005` 复合意图 0.8 → **0.86**（此前**永不达标**，只能经「回落最优候选」生效）。二者均由配置驱动（`COMPONENT_ROUTER_SINGLE_HIT_CONFIDENCE` / `COMPONENT_ROUTER_COMPOSITE_CONFIDENCE`，**默认 0.86**）；**逃生阀**：配回 0.8 即复现旧「回落」语义（供压测/A-B）。低配时仅**告警**不强制改写。实测五类查询：单次记忆/单次知识命中由「不决策」转为「直接决策」，`R005` 的 `qualified` 由 `false` → `true`，无候选查询行为不变。
- **规则集可配置**：新增 `COMPONENT_ROUTER_RULES_PATH`（YAML/JSON，留空=内置规则集）并接入 `ComponentRouter` 构造；**路径非法/文件损坏一律告警并退回内置规则**（不中断服务）。热更新（`start_watching` + `ConfigSnapshot` 哈希比对）为既有能力，继续可用。
- **LLM 兜底接线**：新增 `_build_component_router()` 统一构造入口 —— 开关 `COMPONENT_ROUTER_LLM_FALLBACK_ENABLED`（**默认关闭**）开启且存在 DB/身份时注入分类器：复用既有 `_call_llm` 链路（模型取 `COMPONENT_ROUTER_LLM_MODEL`，留空按 5 因子路由），`temperature=0`、`max_tokens=64`，并施加 **`COMPONENT_ROUTER_LLM_TIMEOUT_SECONDS`=0.3s** 超时；**超时/异常/非法 JSON 一律由路由器回落规则引擎**。**默认关闭的理由**：按 §5.4/§5.5 实测，本地 ≤1B 模型在 300ms 在线预算内无法达标 —— 无合格分类器时开启只是白付超时预算；须先按 §5.6 门槛复测出合格分类器再开。

### 4.3 回写

| 改动 | 说明 |
|------|------|
| 接回写决策器 **【已实施（v1.4.0）】** | 把 `orchestration/evaluate.py` 接入 chat 回写路径：按价值（响应非空且达最小长度）、重要度（记忆意图关键词加权）、频控（同会话窗口内同类不重复）、去重（`message_hash`）决定"是否沉淀、沉淀成什么"，并支持"提炼结论而非全文" |
| rag 入库分级 **【已实施（v1.4.0）】** | 引入 `save_if_valuable` 实际判定（而非仅契约字段）与内容 hash 去重；高价值内容全文入库，普通轮次只入库摘要或跳过，遏制知识库被自产回答持续膨胀 |
| 画像增量升级 **【基座已补回（v1.9.0）；线上 LLM 门控待决策】** | `_resolve_profile_updates` 由"词切片 + 语气三档"升级为受门控的小模型提炼（原文档称"配置键 `OPENLLM_PROFILE_LLM_REFINE` 已存在"，**v1.9.0 更正：该键在当前树不存在**，见 §9 问题 6 与 `DEF-BE-148-029`），并保留规则兜底 |
| 队列可观测与死信 **【已实施（v1.7.0）】** | 暴露队列深度、失败率、重试分布指标；`failed` 行进入死信视图并提供重放端点；失败 TTL 清理任务化 |
| 写路径与通道一致 | 回写前经 `assert_write_channel_is_primary` 校验，避免通道切换期间双写；补齐矩阵中"写路径 A/B 等价"的登记项 |

**已实施细节（v1.4.0 第二批，开关默认关闭）**：

- **接线口径**：新增 `evaluate.grade_writeback_targets()`（**纯函数、确定性**，供网关回写回调**按路**消费）与 `evaluate.grade_rag_ingest()`（入库分级）。与既有 `evaluate_session()` 的**分工**：后者产出载荷（含「窗口摘要」），会**改变记忆粒度** —— 属 §9 待裁定问题 4，故本轮**不代行决定**；前者**只回答「该不该沉淀」**（以及 rag 入库档位），**不改写任何载荷**。
- **判定规则**：价值闸门（`save_if_valuable=false` 显式拦截 / 窗口非空 / 最近轮 query 与 response 均非空且 response 长度 ≥ 2）；rag 分级 = 明确记忆意图（重要度 ≥ 0.8）**或**响应长度 ≥ `WRITEBACK_RAG_FULL_MIN_CHARS`（默认 120）⇒ `full`（全文入库），其余 ⇒ `skip`（**普通轮次跳过知识库入库**）。
- **拦截语义**：被拦截的路由回调返回 `"skipped"`（**不与 `False`（幂等命中）混用**）→ 编排层回执记 `{"status": "skipped", "reason": "value_gate"}`、流式回执记 `skipped`，满足 T5「队列表无该轮 rag 行**或状态为 skipped**」的判定口径。
- **开关与回退**：`WRITEBACK_DECISION_ENABLED`（默认 **False**）关闭时三路回调**无条件**入队、返回值语义不变 ⇒ 行为与既有实现**逐字一致**，可随时回退。

**已实施细节（v1.7.0 第二批，队列可观测与死信）**：

- **聚合指标**：`WritebackStore.stats(user_id=None)` 产出按状态计数（`pending/retrying/done/failed`）、**失败率**（空库返回 `0.0`，不除零）、**重试分布**（`retry_count` 直方图 ＋ `retried_rows` ＋ `max_retry_count`）与**积压年龄**（最早未完成行的 `updated_at`）；`WritebackQueue.stats()` 另补**进程内在飞任务数** `queue_depth`（落盘状态与在飞任务两个视角同一响应内可见）。此前只有「进程内 `_pending` 长度」一个数。
- **死信视图与重放**：`list_dead_letters(user_id, limit, offset)`（只含 `failed`、可分页、**不返回 `payload_json`**）；`claim_failed(row_ids, user_id)` **原子**把 `failed` → `pending` 并把 `retry_count` **归零**（否则重放后首败即再次触顶）后回传 payload；`WritebackQueue.replay_dead_letters()` 复用 `_run_item` 同一执行路径重新投递，**未注册 handler 的目标计 `skipped` 且行留在 `pending`**（待 `recover_pending` 或下次重放接手，避免「重放即丢失」）。
- **接口层**：`GET /openllm/v1/writeback/stats`、`GET /openllm/v1/writeback/dead-letter`、`POST /openllm/v1/writeback/dead-letter/replay`；三者**无身份一律 401（1001）**；统计与死信均**按调用方作用域**（沿用 `DEF-BE-148-007` 的 `json_extract` fail-closed 策略，历史无归属行不可见）；重放**只接受显式行 id**、**单次 ≤100**（超限 4003），防「一键全量回放」冲击 OpenMemory/OpenRAG/DPS。
- **失败 TTL 清理任务化**：`WritebackQueue.run_cleanup_loop(interval)` 由 `main.py` lifespan 启动、关闭时取消，**单轮异常不终止循环**；间隔由 `WRITEBACK_CLEANUP_INTERVAL_SECONDS`（默认 3600 s）驱动，**置 0 = 关闭定时清理**（保留手工清理能力）。此前 `cleanup_failed` 全仓无调用点 → 死信只能直连 SQLite 手工清理。

### 4.4 上下文组装

即 §3.3 与 §3.5：分段配额与溢出策略、`truncated`/`budget` 观测字段、`system` 段启用、引用编号、精炼回执。装配顺序本身不需要改，改的是"每段能放多少、放哪些、超了怎么办"。

## 5. 本地小模型精炼的必要性与选型

### 5.1 有没有必要

有必要，但不是"一律精炼"。判断依据是三类场景各自的最优手段不同：

- 条目过多、单条太长（当前主要问题：记忆段 5.3k~8.2k token、5 条记忆）→ 收益主要来自"选择"（重排 + 配额裁剪），规则就能做到，模型只用于"语义等价的压缩"。
- 主题分散、噪声多（多条记忆彼此重复或与问题无关）→ 抽取式压缩与要点摘要有明显收益，且研究结论支持可行性：ICML 2026 的 CORE-RAG 用 1.5B 压缩器把 top-k 文档压到约 3% 长度，四项 QA 基准平均提升 3.3 EM；结构化压缩路线也用 Qwen3-4B 作骨干。
- 精度要求高、时延预算紧（本研究环境单轮 9~17s）→ 生成式精炼必须**异步/按需**且**有硬超时**，否则会把时延推到不可接受区间。

结论（已由 §5.4 实测校准）：先做"选择 + 预算"（无模型、零额外时延），生成式精炼按需开启；而**生成式精炼在本环境（无 GPU、CPU-only）无法满足在线时延**——最快组合（局域网节点 0.5B）压缩一段仍需 7.1s，本机 0.6B/1B 达 32.6s/76.8s，且事实保留率仅 0.17~0.67（门槛 0.90）。因此生成式精炼的定位调整为**异步/离线**或**GPU 节点**能力，模型档从 1.7B 起测；在线路径只保留"规则档 + 检索侧重排 + 路由分类"。本机（CPU）只承担调用方与路由分类。

### 5.2 触发条件

精炼只在满足任一条件时启动，其余情况走规则档：

| 触发条件 | 阈值（初始建议） |
|----------|------------------|
| 某段 token 超配额 | memory > 配额 1.5 倍，或 rag > 配额 1.5 倍 |
| 条目数过多 | 单段条目 > 8 条 |
| 重复率高 | 段内内容相似度 > 0.85 的条目占比 > 30% |
| 多源冲突 | 同一实体在记忆与知识库给出一致性冲突的陈述 |

### 5.3 任务形态与护栏

任务限定为三类确定性目标，禁止自由改写：抽取式压缩（保留原文句子，按重要度排序去冗余）、要点摘要（每条记忆压到一句，保留实体与数值）、去噪重排（剔除与问题无关的条目）。护栏：只允许引用原文片段，不得引入新实体或数值；输出强制编号列表以便逐条归因；压缩率目标 20%~40%（不是越短越好）；任何解析失败即丢弃模型输出、回退规则档。

### 5.4 实测对比（Ollama，精度 × 时延）

评测集与打分口径：四类任务（路由 / 相关性筛选 / 抽取式压缩 / 要点摘要），每任务 4 条样本；
gold 由**预标注的关键事实**（样本标识、预算代号、数值、实体）与**相关条目下标**构成，精度不依赖人工评分；
跨模型统一 `temperature=0`、`seed` 固定、`num_ctx=4096`、`think=false`，每模型先预热且加载耗时不入分位。
基准脚本与全部明细见 `doc/test/evidence/local-model-bench/`。

| 模型（量化） | 端点 / 推理 | 路由逐字段准确率 | 筛选 F1 | 压缩事实保留 | 摘要事实保留 | 压缩率 | 吞吐 tok/s |
|---|---|---|---|---|---|---|---|
| `qwen3:0.6b`（Q4_K_M） | 本机 CPU | **1.00**（2.33s） | 0.544（9.2s） | 0.50（**32.6s**） | 0.29（8.7s） | 0.46 | 7.5 |
| `llama3.2:1b`（Q8_0） | 本机 CPU | 0.375（4.71s） | **0.697**（29.0s） | **0.667**（**76.8s**） | 0.17（26.1s） | 0.43 | 3.5 |
| `qwen2.5:0.5b`（Q4_K_M） | 局域网 192.168.0.4 | 0.375（0.60s） | 0.568（5.8s） | 0.583（7.1s） | 0.21（2.7s） | 0.44 | 30.3 |
| 解析式基线（原文保留） | 无模型 | 不适用 | 0.571（全选） | **1.00**（0s） | **1.00**（0s） | 1.00 | — |

括号内为 P50 时延。两个端点的 `size_vram` 均为 0，即**都在 CPU 上推理**（局域网节点单核性能约为本机 5 倍）；
本机模型加载耗时 11.4s（0.6B）与 19.1s（1B），局域网 5.1s。

三点解读：

- 时延差 1~2 个数量级：压缩一段上下文，本机 32.6~76.8s、局域网 7.1s，对照在线预算（CPU 档 800ms / GPU 档 400ms）全部不达标 → **在线同步精炼在当前硬件上不可行**。
- 精度差与参数量不同步：路由任务上 `qwen3:0.6b` 达到 1.00，而 `qwen2.5:0.5b`、`llama3.2:1b` 仅 0.375 → 该任务上**模型选择比参数量更关键**；压缩/摘要任务上三者事实保留率 0.17~0.67，全部低于 0.90 门槛，压缩率虽到 0.43~0.46，代价是丢标识与数值。
- 筛选任务不要交给生成式小模型：两个 0.5~0.6B 的 F1（0.544/0.568）与"全选"基线（0.571）无实质差别；`llama3.2:1b` 的 0.697 虽达标，但 29s/次不可在线。

### 5.5 选型结论

按任务分别定手段，模型只在能达门槛的场景使用：

| 任务 | 在线手段 | 门槛 | 实测结论与选型 |
|------|----------|------|----------------|
| 组件路由分类 | 规则引擎 + 小模型兜底（结果缓存） | 逐字段准确率 ≥ 0.90 | `qwen3:0.6b` 达标（1.00）；本机 P50 2.33s、局域网 0.60s → 仅用于规则不命中时的**低频兜底**，配 300ms 超时与缓存 |
| 相关性筛选 | **检索侧重排**（OpenRAG 服务端 rerank 或判别式重排器） | F1 ≥ 0.70 | 生成式 ≤1B 不达标或不可用；重排器为 0.6B 判别式模型，延迟远低于生成式 |
| 抽取式压缩 | 规则档（去重 + 排序 + 配额裁剪）；生成式仅异步/GPU | 事实保留 ≥ 0.90 | ≤1B 全部不达标（0.50~0.667）→ 在线不上模型；GPU 节点从 1.7B 起补测 |
| 要点摘要 | 同上 | 事实保留 ≥ 0.90 | ≤1B 差距更大（0.17~0.29）→ 同上 |
| 画像增量提炼 | 规则档（受 `OPENLLM_PROFILE_LLM_REFINE` 门控）；生成式仅异步 | 关键字段不错 | 与压缩同源，随压缩档一并决定 |

### 5.6 候选梯队与补测口径

补测在**具备 GPU 且能拉取模型**的节点执行，按下列顺序推进：

| 梯队 | 候选 | 规模 | 说明 |
|------|------|------|------|
| 第一 | `qwen3:1.7b`、`qwen3.5:0.8b` | 1.4GB / 1.0GB 级 | 成本最低的达标候选，先测压缩与摘要 |
| 第二 | `qwen3.5:2b`、`qwen3.5:4b`、`qwen2.5:3b` | 2~3.4GB | 覆盖"摘要不掉实体"的稳定性 |
| 备选 | `phi4-mini`、`gemma3:4b`、`llama3.2:3b` | 3~4GB | 跨家族对照，防止单家族过拟合 |
| 已具备 | `qwen3:0.6b`（路由）、`llama3.2:1b`（筛选，慢） | ≤1B | 用于路由与对照基线 |

补测通过标准：压缩/摘要事实保留 ≥ 0.90，筛选 F1 ≥ 0.70，路由逐字段准确率 ≥ 0.90，
且 P95 时延落到该部署档预算内（GPU 在线 400ms；异步档放宽到 30s）。未通过的任务一律回到规则档。

复测命令（模型可用的节点上执行，产物自动落 `doc/test/evidence/local-model-bench/`）：

```powershell
ollama pull qwen3:1.7b ; ollama pull qwen3.5:0.8b ; ollama pull qwen3.5:4b
python small_model_bench.py --base-url http://127.0.0.1:11434 `
  --models qwen3:1.7b,qwen3.5:0.8b,qwen3.5:4b --tag gpu-node
python merge_bench_reports.py --pattern "small-model-bench-*.json" --out merged-bench.md
```

### 5.7 部署形态

复用 OpenLLM 既有 `ollama` 供应商接入（不新造通道），并把实测得到的运行约束写进部署要求：

| 项 | 要求 | 依据（实测） |
|----|------|--------------|
| 运行位置 | 生成式精炼部署在具备 GPU 的节点；本机只承担路由分类与调用方 | 本机 CPU 压缩 32.6~76.8s/次、局域网 CPU 7.1s/次，均不满足在线预算 |
| 模型注册 | 拉取后把注册表对应模型置 `active`，补齐 `context_window`/`max_tokens` | 注册表中 `qwen3:0.6b`/`llama3.2:1b` 等历史条目为 `inactive` |
| 模型库目录 | 服务进程须对模型库可写；不可写时用 `OLLAMA_MODELS` 指向可写目录并复用既有 blobs/manifests | 本机 `D:\Ollama\Models` 不可写，拉取报 Access denied |
| 常驻策略 | `OLLAMA_KEEP_ALIVE` 覆盖精炼调用间隔，避免反复加载 | 本机加载 11.4s/19.1s、局域网 5.1s |
| 网络前置 | 目标节点需能访问模型仓库；不可达时先在可访问节点拉取再同步模型库 | 本环境拉取多次停在中途（0.5B 停于 379MB） |
| 调用口径 | 精炼走网关内部模型调用（同一鉴权、计量、熔断），配置声明"精炼模型编码 + 超时 + 压缩率目标" | 与既有模型调用面一致，避免旁路 |

### 5.8 精炼的预算与降级

分两档设定：**在线档**只允许规则与判别式模型进入会话路径，**异步档**才允许生成式模型（会话后批量处理）。

| 项 | 在线档 | 异步档 | 说明 |
|----|--------|--------|------|
| 允许手段 | 规则（去重 / 排序 / 配额裁剪）+ 判别式重排器 + 路由分类 | 生成式压缩与摘要（1.7B 起，部署在 GPU 节点） | 实测生成式在 CPU 上 7.1~76.8s/次，不进在线路径 |
| 预算 | 重排 ≤100ms；路由兜底 ≤300ms（命中缓存直接返回） | 单轮 ≤30s，超时即用规则档结果 | 在线预算沿用本仓库既有目标量级 |
| 压缩率目标 | 规则档 30%~60%（按配额整条裁剪） | memory 20%~40%，rag 30%~50% | 低于目标说明该段本就不必压 |
| 缓存 | 按 `(query_hash, 段内容 hash)` 缓存 10 分钟；路由分类按 query 归一化缓存 | 同左，另把"会话级压缩结果"落库 | 同会话重复提问不重复精炼 |
| 降级 | 模型不可用 / 输出非法 / 超时 → 规则档 | 同左，且失败轮次进入待重跑 | 回执 `fallback=true` 并计入观测 |
| 观测 | `refine.mode/model/in_tokens/out_tokens/elapsed_ms/fallback` | 同左 | 落 `context_metrics`，用于评测与容量规划 |

### 5.9 与现有配置的关系

`prompt_pipeline` 已经声明"裁剪属 v1.4.9 第二批且须开关控制"，本方案的 §3.3（预算与裁剪）与 §5（精炼）正好落在该批次范围内，上线顺序为"规则档 → 重排 → 生成式精炼"，每批独立开关与验收判据。生成式精炼的开关默认关闭，开启前须同时满足两项前置：模型在 §5.6 门槛下通过复测，且精炼服务部署在 GPU 节点。

## 6. 分批实施建议

| 批次 | 内容 | 依赖 | 预期收益 |
|------|------|------|----------|
| 第一批（无新模型）—— **已完成 6/6（2026-09-27，见 §11 v1.3.0）** | 预算与裁剪 + `truncated/budget` 观测；rag `rerank`/`score_threshold` 接线；内容去重；`system` 段启用；trace 候选明细；**两条路径取数顺序统一与画像并行** | 无 | 已实现：装配可预算（分段配额 + 整条裁剪 + 段内去重 + 单条句边界截断）、system 段可注入统一指令、检索侧重排可开关、路由候选可复盘、**画像与组件并行且两路径取数时序一致**；前 5 项**全部默认关闭**（行为与既有实现逐字一致），第 6 项为**时序收敛**（语义等价，仅去掉串行等待） |
| 第二批 —— **进行中（2026-09-27，见 §11 v1.4.0 / v1.5.0 / v1.6.0 / v1.7.0 / v1.8.0 / v1.11.0 / v1.11.1）** | ① **已完成：写侧价值闸门接入**；② **已完成：组件依赖图调度**；③ **已完成：备通道健康探针**；④ **已完成：回写队列可观测与死信**；⑤ **已完成：组件决策三余项（阈值与单次命中语义对齐 / 规则集可配置 / LLM 兜底接线）**；⑥ **部分完成（v1.11.0）：备通道接管轨迹的两路径口径收敛**（共用步骤补归因 ＋ 单一落痕函数 `_merge_rag_trace()`；T4 的「轨迹」段已转为**进程内可判**）；待做：通道定性（接线/探活专用/废止）+ **内置 RAG 种子底座**（需运行态 DB ＋ 嵌入模型）+ 通道裁决进取数层 + §4.3 余项（画像增量升级 / 写路径与通道一致）+ 独立审计落库；⑦ **新登记（v1.12.0 审计，未实施且不受阻）**：§3.4 规则档余项（元数据噪声剥离 / 相邻同义合并 / `refine` 回执）＋ §3.5 引用编号 `[M1]`/`[K1]` | 第一批的观测字段；⑥ 中「通道定性」「写路径与通道一致」需**人工裁定**（§9 问题 1）；⑦ **无外部依赖**（无新模型、无裁定依赖），可立即实施 | 知识库不再自污染、组件调度不再依赖全局开关、备通道虚实可观测、回写失败可观测可重放、**路由达标判定与最终决策一致（均已达成）**；**备通道接管轨迹两路径同源可复盘（v1.11.0 轨迹 / v1.11.1 无 5xx）**；主备名副其实（待裁定后） |
| 第三批 | 本地重排器 → 生成式精炼（按 §5.5 选型与 §5.8 预算）；评测集与验收判据扩展 | 生成式精炼需 GPU 节点 + 模型通过 §5.6 门槛；重排器与路由分类可先落 CPU 节点 | 多源长上下文场景的精度进一步提升 |

## 7. 验收判据

在现有 E2E 判据（同步 H1~H10、流式 S1~S10）之上扩展：

**执行器（v1.10.0 交付，v1.11.0 扩展 T4 进程内判定）**：`doc/test/evidence/cr149/t_acceptance_runner.py` —— 一键复跑本表全部判据，逐条输出 `PASS / FAIL / SKIP / BLOCKED` 与**原始测量数据**（JSON 可落盘）；默认按**当前配置**判定，`--simulate` 在**进程内**临时置位开关（退出恢复、不写配置、不影响运行中服务）以验证「开启后即达标」。`SKIP`（开关未开）与 `BLOCKED`（环境/前置缺失，如 T6 属第三批）**均不计入失败**，但会显式列出，避免"没做"被误读为"通过"。**T4 自 v1.11.0 起不再整体 `BLOCKED`**：其「轨迹」段改为**进程内判定**（同一故障下同步 / 流式两路径的 `rag_source` 与归因须同源一致），不达标即 `FAIL`；「无 5xx」段自 **v1.11.1** 亦为**进程内覆盖**（端点级 HTTP 故障注入 4 例，见判据表 T4）；仅「真实停服/改址注入」与「轨迹实际落库读取」以及 `has_base` 前置留给运行态，并以 `detail.trace_contract` / `detail.endpoint_level_evidence` / `detail.runtime_pending` 分别留痕。

| 判据 | 内容 |
|------|------|
| T1 | `context_metrics.budget` 中 **`quota > 0` 的段**满足 `used ≤ quota`；且**各段填满配额**的最坏场景下 `prompt_total_tokens ≤ 窗口 − 输出预留`（结构保证：**配额比例之和 ≤ 0.95**，留出查询 + 模板开销余量）；`quota = 0` 表示"不限"（见 §3.3） |
| T2 | 超配额场景下 `truncated` 有值且 `dropped_items > 0`，**且被裁剪段仍保留条目**（`used > 0`）—— 由「保底一条」保证（单条即超配额时保留首条并压进配额；可装下首条时仍为整条丢弃、不触发保底） |
| T3 | 启用 rerank 后 rag 条目的 score 单调性成立、低分条目被 `score_threshold` 过滤（条目数下降但 `used_ratio` 不降） |
| T4 | 注入组件故障（停 OpenRAG / 改不可达地址）后，通道裁决与内置 RAG 接管有明确轨迹（`rag_source`、审计事件），且无 5xx　**【自 v1.11.0 起拆为两段，v1.11.1 进一步收窄运行态部分：①「轨迹」= **进程内可判** —— 同一故障下同步 / 流式**两路径**须落同源的 `rag_source=builtin` 与**回退归因** `builtin_fallback_reason`，且经**同一落痕函数** `_merge_rag_trace()` 写入 `routing_trace.components`；②「无 5xx」= **已在进程内覆盖** —— 端点级（HTTP，`TestClient`）故障注入 4 例：同步 `POST /openllm/v1/chat` 与流式 `POST /openllm/v1/chat/stream` 均 200、无 error 事件、轨迹带来源与归因、装配缺失不回退（`tests/unit/test_rag_builtin_fallback_trace.py::TestEndpointLevelFaultInjection`）；**仍未覆盖**：**真实**停服/改址注入 与 轨迹**实际落库读取**（前者前置 `has_base=true` 未满足，后者只判到「落库调用入参」层）。「审计事件」当前落点为**接管告警日志**（WARNING 含归因），**独立审计落库（`AuditLog`）未接入**（见 §10 待登记项 6）】** |
| T5 | 低价值轮次不产生 rag 入库（队列表无该轮 rag 行或状态为 skipped），高价值轮次正常入库　**【可判定：v1.4.0 起由 `WRITEBACK_DECISION_ENABLED` 开启后经 `skipped` 回执判定】** |
| T6 | 精炼开启时 `refine.fallback=false` 且 `elapsed_ms ≤ 预算`；关闭或超时场景 `fallback=true` 且回答质量不降级（同一评测集对比） |
| T7 | 画像取数并发且两路径时序统一：同步 / 流式**两条路径**都落 `profile_fetch` 步骤（耗时＝启动→完成差值）；画像耗时与组件耗时**重叠**（单轮墙钟 ≈ max(分段) 而非 Σ 分段）；流式句柄在**首包之后**构造（P-4 口径不破）；画像内容确实进入 Prompt（未收割＝画像段为空，视为不通过） |
| T8 | 组件调度由**依赖图**决定：开启 `COMPONENT_DEPENDENCY_SCHEDULING_ENABLED` 后，无依赖的 `memory`/`rag` **并发**（单轮组件墙钟 ≈ max 而非 sum，即使 `enable_parallel=false`）；声明 `OPENLLM_COMPONENT_DEPENDENCIES=memory:rag` 后两组件**严格保序且不重叠**（覆盖全局并行开关）；依赖成环时**退化为单波次且不抛异常**；开关关闭时调度语义与既有实现**逐字一致** |
| T9 | 路由**达标判定与最终决策一致**：单次 `R001`/`R002` 命中与 `R005` 复合意图命中的 `candidate_report.qualified` 均为 `true` 且 `decide_sync` **直接给出决策**（不再落到「回落最优候选」）；`COMPONENT_ROUTER_RULES_PATH` 指向的规则文件生效、路径非法时退回内置规则且**不抛异常**；LLM 兜底开关关闭时**不注入分类器**、开启时超时/异常/非法输出**一律回落规则**（且分类预算 ≤300ms） |

## 8. 风险与回退

| 风险 | 影响 | 回退 |
|------|------|------|
| 裁剪过度导致关键上下文被丢弃 | 回答质量下降 | 配额与开关可配置，默认偏保守；T2 判据兜底 |
| 重排开启改变条目顺序与数量 | 既有判据（条目数 5/5）失败 | 重排与阈值分别开关，可单独回退 |
| 通道切换引入双写或写入丢失 | 数据一致性风险 | 写路径 `assert_write_channel_is_primary` 校验 + 切换期间暂停回写 |
| 本地小模型时延抖动（实测 CPU 档 7.1~76.8s/次） | 单轮时延上升 | 在线档不引入生成式模型；生成式只进异步档（单轮 ≤30s，超时回落规则档）；路由兜底 ≤300ms 且带缓存 |
| 精炼改写内容引入幻觉 | 注入不实信息 | 只允许抽取原文片段 + 编号可归因；解析失败即丢弃 |
| 并发取数后 `timeline` 步骤之和 ≥ 真实墙钟（区间重叠） | `P-1`「本仓开销」按 Σ 步骤判定时被**高估** | 各步骤耗时仍为其**自身真实耗时**（口径不变）；判定按「重叠说明」复核，必要时以关键路径（max）而非 Σ 为口径；此前的 memory/rag 并行已存在同类语义 |
| 流程未走到组装（异常 / 早期返回）时句柄未被显式收割 | 遗留后台取数任务 | 句柄以**取数完成回调**落计量（不依赖是否被收割）；`discard()` 供断连 / 早期返回取消；取数失败一律降级为 `None`，不中断主链路 |
| 组件并行度提升（memory/rag 同时外部调用）使下游并发压力上升 | 下游限流或尾延迟上升 | 参与并行的组件**仅 memory/rag 两个**且互不依赖；可用依赖声明改为串行（`memory:rag`），或关闭 `COMPONENT_DEPENDENCY_SCHEDULING_ENABLED` 整体回退 |
| 依赖声明写错（漏声明 / 成环） | 漏声明只影响并行度、不影响正确性（memory/rag 本无依赖）；成环会使调度退化 | 成环 **fail-safe**：退化为单波次保序并**告警**（不抛异常、不打挂请求）；声明解析对非法片段跳过并告警 |
| 调度语义变更影响 P-1/P-2 计量口径 | 并行后 Σ步骤 ≥ 真实墙钟（与第一批画像并行同源） | 逐组件 `timeline` 步骤**口径不变**（各为自身真实耗时）；判定按关键路径（max）复核 |
| 单次命中置信度提到 0.86 后**路由决策面变宽**（单次命中不再走 LLM 兜底/回落） | 与旧行为相比，同一查询可能由「LLM 兜底结论」变为「规则直接结论」；组件装配面随之变化 | 置信度由配置驱动，**配回 0.8 即复现旧语义**（逃生阀）；低配时路由器**告警**提示该规则将退化为「回落」；无候选查询行为完全不变 |
| 规则文件损坏 / 路径错误 | 路由不可用 | `ComponentRouter` 构造**捕获异常并告警**，保留内置规则集（不中断服务）；热更新失败仅记 ERROR，不替换现有规则 |
| LLM 兜底分类超时预算（300ms）与本地模型时延不匹配 | 开启后每轮无候选查询白付 300ms 且仍回落规则 | 开关**默认关闭**（零行为漂移）；开启前须按 §5.6 门槛复测出达标分类器；超时/异常/非法输出一律回落规则引擎 |

## 9. 待裁定问题

1. 通道 A：接线对话降级接管，还是降级为"探活 + 人工切换"，或直接废止（三选一）。
2. 精炼推理位置：实测本机 CPU 与局域网节点均为 CPU 推理（压缩 7.1~76.8s/次），建议生成式精炼部署到具备 GPU 的节点、本机只承担路由分类；若坚持本机 CPU，则只能把生成式精炼限于异步档。
3. 预算目标：是沿用知识库样本中宣称的 4096，还是按对话模型的真实窗口（8k/32k）设定，并据此给出各段配额。
4. 记忆写入语义：是否允许把"整轮全文"改为"提炼结论/摘要"（影响历史记忆的可检索粒度与回归用例）。
5. 通道切换的触发权：保持"人工显式为主、自动为可选"，还是对组件级连续失败直接自动接管。
6. 异步精炼的触发与产物归属：会话后批量压缩的结果是写入记忆（改变记忆粒度）还是仅作为装配期缓存（不改写数据）。
7. **画像增量提炼器的形态与门控**（v1.9.0 追加，源自 `DEF-BE-148-029` 修复）：`refine_profile_delta` 的提炼器已就位且契约为**同步** `refine_fn(dialogue) -> dict | None`（因 `evaluate._profile_updates_for` 为同步函数），但「小模型提炼」的**线上接线**需先裁定：① 由谁提供提炼器（网关复用 `_call_llm` 的**同步桥**？还是独立本地小模型客户端？）；② 门控配置键命名与默认值（原文档所述 `OPENLLM_PROFILE_LLM_REFINE` **在当前树不存在**，须随裁定一并新增）；③ 不接线时保持**纯规则路径**（当前默认，线上零影响）。

## 10. 待登记项

| # | 项 | 现状 | 建议登记位置 |
|:-:|----|------|--------------|
| 1 | 通道 A 未接入业务路径 | 状态机与矩阵齐备、无调用点；端到端无法验证 | 问题跟踪记录（变更请求）+ 技术债务总表 |
| 2 | 内置 RAG 备通道无底座 | **部分实施（v1.6.0）**：KB 表 0 行、FAISS 0 索引这一事实已由 `health.components.builtin_rag`（`knowledge_bases` / `indexes` / `has_base` / `reason`）**前置可视化**；**种子动作未执行**（需运行态 DB ＋ 嵌入模型）—— 当前口径明确为「内置 RAG 仅在有本地索引时生效」 | 问题跟踪记录（缺陷）→ 已于 v1.41.0 登记；环境前置说明；本方案 §4.1 |
| 3 | 写侧价值/重要度/频控/去重决策器未接线 | **已实施（v1.4.0 第二批，开关 `WRITEBACK_DECISION_ENABLED` 默认关闭）**：`grade_writeback_targets()` / `grade_rag_ingest()` 供网关三路回写回调按路消费；不达标返回 `"skipped"`（编排层回执 `{"status":"skipped","reason":"value_gate"}`、流式回执 `skipped`）；**只决定是否沉淀、不改写载荷**（「改摘要」属 §9 问题 4，未代行决定） | 问题跟踪记录（缺陷）→ 已于 v1.39.0 登记；本方案 §4.3/§7 T5 |
| 4 | 装配层无预算与裁剪、`system` 段恒空；两路径取数时序**相反**且均**串行** | **已实施（v1.3.0 第一批 6/6；前 5 项开关默认关闭，第 6 项为时序收敛）**：`BudgetPolicy` + `apply_context_budget`（去重 / 整条裁剪 / 单条句边界截断）+ `budget`/`truncated` 观测；`resolve_system_prompt` + `CONTEXT_SYSTEM_PROMPT_ENABLED`；`DeferredFetch` 并发取数句柄（画像 × 组件并行 + 组装前统一收割，两路径同口径 `profile_fetch` 计量） | 问题跟踪记录（变更请求）→ 已于 v1.37.0 / v1.38.0 登记；本方案 §3.1/§3.3/§3.5 |
| 5 | 生成式精炼缺达标模型与推理节点 | 基准实测：≤1B 事实保留 0.17~0.67（门槛 0.90），CPU 压缩 7.1~76.8s/次；两端点 `size_vram=0` | 问题跟踪记录（变更请求）+ 技术债务总表 + §5.6 补测项 |
| 6 | **备通道接管的「审计事件」无独立落库** | **v1.11.0 如实登记**：T4 判据原文要求轨迹含「`rag_source`、审计事件」。当前落点为**接管 WARNING 日志**（`OpenRAG 检索失败，回退内置 RAG（rag_source=builtin）: <归因>`）＋ `routing_trace.components`（`rag_source` / `builtin_fallback_reason`），**未写入 `AuditLog`**（`app/services/audit_service.py` 有该能力但无调用点）。**影响**：接管可在日志与轨迹复盘，但**不入审计库 ⇒ 无法按审计口径统计接管次数 / 时长分布**；**建议**：若需强审计，单独立项（含审计动作码与保留策略），本方案不代行决定 | 问题跟踪记录（变更请求）+ 技术债务总表 |
| 7 | **§3.4 规则档余项 ＋ §3.5 引用编号：正文已指定但未实施** | **v1.12.0 仓内一致性审计登记（逐项取证见 §3.4 / §3.5 的「实施状态」表）**：**(a) 剥离元数据噪声**（`trace_id:None` 一类平铺字段）；**(b) 相邻记忆条目合并同义重复行**（现有去重仅为「归一化后精确重复即丢弃」，非合并、无同义判定）；**(c) `refine` 回执字段**（`{mode, model, in_tokens, out_tokens, elapsed_ms, fallback}`；规则档亦未落痕）；**(d) 稳定引用编号 `[M1]`/`[K1]`**（与归因 A 片段索引对齐；现仅 `"{序号}. {正文}"` 且裁剪后会**重排序号**）。**性质**：四项均**无外部依赖**（无新模型、无 §9 裁定依赖）⇒ **可立即实施**；**影响**：不影响任何已实施项与已判 `PASS` 判据的结论；**建议**：作为第二批余项（⑧）优先实施，其中 (d) 建议加开关默认关闭（改动 Prompt 文本形态，(a)(b)(c) 需一并评估默认值） | 问题跟踪记录（变更请求）＋ 本方案 §6 第二批第 ⑦ 行 ＋ §3.4/§3.5 实施状态 |

## 11. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-26 | AD-OpenBase-Dev | 初始创建：基于四问审计现状给出上下文精装配流水线、四问逐项优化、本地小模型精炼的选型与预算护栏、分批实施建议与验收判据；登记 4 项待登记项与 5 项待裁定问题。状态 [Draft] |
| v1.1.0 | 2026-09-27 | AD-OpenBase-Dev | 合入 Ollama 小模型基准结论（`doc/test/evidence/local-model-bench/`）：§5 重写为"必要性 → 触发条件 → 任务形态 → 实测对比 → 选型结论 → 候选梯队与补测 → 部署形态 → 预算与降级 → 与现有配置"，明确在线档只保留规则/重排/路由分类，生成式精炼转异步或 GPU 节点；新增待登记项 5（缺达标模型与推理节点）与待裁定问题 6（异步精炼产物归属），同步更新 §6 第三批依赖、§8 时延风险回退、§10 编号引用。状态 [Draft] |
| v1.2.0 | 2026-09-27 | AD-OpenBase-Dev | **第一批实施回填（5/6 项已完成，全部默认关闭）**。① **§3.3 预算与裁剪落地**：`prompt_pipeline` 新增 `BudgetPolicy` / `load_budget_policy` / `apply_context_budget` 与 `_trim_segment`（顺序＝段内去重 → 单条句边界截断 → 分段配额整条裁剪；`system` 段仅观测不裁剪），`PromptComposition` 增 `budget` / `truncated`，`context_metrics.to_record()` 落 `budget` / `truncated`（仅在预算开启且确有裁剪时出现）；开关 `CONTEXT_BUDGET_ENABLED`（默认 **False**）与窗口/预留/五段配额/单条上限/去重共 9 项配置。**运行态探针**（真实 tokenizer）：窗口 8192 − 预留 1024 ⇒ memory 配额 2150、rag 2867；收紧窗口至 1200 − 200 时 memory 配额 300 → **丢弃 8 条 / 504 token**（`dropped_items=8`）且 `prompt_total_tokens=381`。② **§3.5 system 段落地**：`DEFAULT_SYSTEM_PROMPT` + `resolve_system_prompt`（调用方显式优先）+ `CONTEXT_SYSTEM_PROMPT_ENABLED`（默认 **False**），开启后 system 段 83 token 注入且位于 Prompt 首位。③ **§3.2 检索侧重排接线**：新增 `_rag_search_params()` 统一「条目参数优先 → 全局配置」取值口径，主通道两处 handler **与内置备通道同口径**透传 `rerank` / `score_threshold`（开关 `RAG_RERANK_ENABLED` 默认 False、`RAG_SCORE_THRESHOLD` 默认 0=不过滤）；探针实测 `{"rerank": true, "score_threshold": 0.15}`。④ **§4.2 路由候选落 trace**：`ComponentRouter.candidate_report()`（只读，不改决策契约）→ `AutoOrchestrator.decide()` 的 `plan["candidates"]` → 同步/流式**两条路径**写 `routing_trace.decision_candidates`（含 `rule_id/confidence/qualified/need_*`）；探针实测 R001/R002/R004 三条候选可见且 `qualified=true`。⑤ **护栏（TDD）**：新增 4 文件 **29 例**（`test_context_budget` 13 / `test_system_segment` 5 / `test_rag_rerank_wiring` 5 / `test_router_candidate_trace` 6）全绿；静态质量：本轮改动文件 `ruff` 零**新增**告警（`component_router.py` 余 39 项为既有历史欠账，未借机重构）。⑥ **回归**：全量 `tests/unit` **32 failed / 2991 passed / 0 error**；**触及模块 12 文件基线对照**（同命令、`git checkout HEAD~1` 前后）**失败集逐项完全相同（28 = 28，归一化 request_id 后零差异）** ⇒ **零新增失败**；新增护栏 4 文件不在失败集内。⑦ **过程中修正**：`_rag_search_params` 解析由 `try` 内**移出**（避免解析异常被 `except Exception` 误判为「外部检索失败」而触发内置回退）＋ `test_rag_unregistered_no_fallback` 替身按适配器契约补齐 `rerank/score_threshold`（**契约漂移修正**，非放宽断言）。⑧ **余项（未做）**：第一批第 6 项「两条路径取数顺序统一与画像并行」未实施（风险点在流式 `P-4` 首包计量口径），已单列 §6 一行；5 项开关的生产开启值（配额比例、单条上限、rerank 阈值、system 指令文案）待人工批准后按 §7 T1~T6 判据验证再开。⑨ 提交：**OpenLLM `65899c7`（6 生产 + 4 测试，`+454/-22`）、`892e8e7`（2 文件，`+20/-4`）**。状态 [Draft] |
| v1.3.0 | 2026-09-27 | AD-OpenBase-Dev | **第一批第 6 项实施回填（第一批 6/6 完成）**。① **新增并发取数句柄** `DeferredFetch`（`app/edgerouter/orchestration/deferred_fetch.py`）：语义为「构造即启动后台取数、组装之前统一收割」；`resolve()` **幂等**、取数异常**降级为 `None`**（不中断主链路）、`discard()` 供断连 / 早期返回取消；计量改由**取数完成回调**落 `{step, ms}`（耗时＝启动→完成差值），故**未显式收割也不丢计量**，未启动（画像注入开关关闭）仍沿用「值 `None`、步骤恒落」既有语义。② **两路径取数时序统一**：同步由「先 `await` 画像、后组件」改为「构造句柄 → 交编排层 → `PipelineExecutor` 在**组装之前**收割」；流式由「先组件、后画像」改为「**首包之后**构造句柄（P-4 口径不破）→ 组装之前 `resolve()`」。`_run_orchestrated_chat` / `AutoOrchestrator` / `ExplicitOrchestrator` / `PipelineExecutor` 的 `profile_ctx` 入参放宽为 `str \| DeferredFetch \| None`（既兼容既有字符串调用方与测试替身，也支持句柄）。③ **运行态探针**（`doc/test/evidence/cr149/profile_parallel_probe.py`，走真实 `PipelineExecutor` + `run_components`）：分段各 0.15 s 时，串行墙钟 **0.312 s** → 并发 **0.156 s**（**省 0.156 s**；3 轮取最优、含预热，串行三档 0.312/0.313/0.328、并发三档 0.172/0.156/0.156）；并发态 `profile_fetch` 步骤 **156 ms** 且画像确入 Prompt（`prompt_has_profile=true`）；两路径接线时序 4 项判定全 `true`、句柄 2 处。④ **护栏（TDD）**：新增 `test_deferred_fetch.py` **14 例**（计量不丢 / 幂等 / 失败降级 / 丢弃不落步骤 / **真实重叠序** / 执行器组装前收割 / 网关→编排层→执行器端到端入 Prompt）；把 `test_profile_fetch_timeline_guard.py` 改写为**句柄写法契约**并**新增时序契约**（4 例）——原「两路径都落计量 ＋ 各自计时 ＋ 耗时差值口径」三项不变量**全部保留且更严**（新增「首包之后启动」「组装之前收割」）。⑤ **静态质量**：本轮 7 文件 `ruff` **零告警**。⑥ **回归**：全量 `tests/unit` **32 failed / 3005 passed**（该测量轮次护栏含 `test_deferred_fetch` **13 例** + 改写护栏 4 例，同批随后补入的端到端护栏 1 例单独验证通过 ⇒ **批末态 32 failed / 3006 passed**）；**失败集与第一批基线逐项完全相同**（同命令归一化后 `Compare-Object` **32 = 32，零差异 ⇒ 零新增失败**）。⑦ **风险如实登记（新增两项入 §8）**：并发后 `timeline` 步骤之和 ≥ 真实墙钟（区间重叠 → `P-1` 判定需按关键路径复核）；异常路径句柄未显式收割（由完成回调兜底计量 + `discard()` 清理）。⑧ **未实施（留待第二批）**：组件依赖图并行（替代 `OPENLLM_ENABLE_PARALLEL` 全局开关）、通道裁决进取数层。⑨ 提交：**OpenLLM `2f296bb`（5 生产 + 2 测试，`+550/-30`）**。状态 [Draft] |
| v1.4.0 | 2026-09-27 | AD-OpenBase-Dev | **第二批第 ① 项实施回填：写侧价值闸门接入（方案 §4.3「接回写决策器」+「rag 入库分级」，判据 T5）**。① **动因（对应 §10 待登记项 3）**：`orchestration/evaluate.py`（价值 / 重要度 / 频控 / 去重决策器）**全仓无调用点**；chat 回写路径（同步 + 流式）对三路**无条件** `submit` —— memory 写整轮全文、**rag 亦无条件入库** → 低价值轮次持续污染知识库（自产回答回流）。② **设计取舍（关键）**：既有 `evaluate_session()` 产出的是**载荷**（memory 写「窗口摘要」），直接接线会**改变记忆粒度** —— 属 §9 **待裁定问题 4**，本批**不代行决定**。故新增**只回答「该不该沉淀」、不改写任何载荷**的判定入口：`evaluate.grade_writeback_targets()`（纯函数、确定性）与 `evaluate.grade_rag_ingest()`（入库分级）。③ **判定规则**：价值闸门（`save_if_valuable=false` 显式拦截 / 窗口非空 / 最近轮 query 与 response 均非空且 response 长度 ≥ 2）；**rag 分级** = 明确记忆意图（重要度 ≥ 0.8）**或** 响应长度 ≥ `WRITEBACK_RAG_FULL_MIN_CHARS`（默认 120）⇒ `full`（全文入库），其余 ⇒ `skip`（**普通轮次跳过知识库入库**，遏制自产膨胀）。④ **接线与拦截语义**：网关 `_build_writeback_callback()` 的 `_make(target)` 在 `submit` **之前**按路消费判定（同一 query/response 结果**缓存复用**，三路只算一次）；被拦截 ⇒ 返回 **`"skipped"`**（**不与 `False`（幂等命中）混用**）→ `PipelineExecutor._writeback_with_retry()` 记 `{"status":"skipped","reason":"value_gate"}`、流式 `_run_stream_writebacks()` 回执记 `skipped` ⇒ 满足 T5「队列表无该轮 rag 行**或状态为 skipped**」。⑤ **开关与回退**：新增 `WRITEBACK_DECISION_ENABLED`（默认 **False**）与 `WRITEBACK_RAG_FULL_MIN_CHARS`（默认 120）；**关闭时三路无条件入队、返回值语义不变 ⇒ 行为与既有实现逐字一致**，可随时回退。⑥ **运行态探针**（`doc/test/evidence/cr149/writeback_gate_probe.py`，真实网关回调 + 真实决策器 + 队列替身）：**开关关闭**时四类轮次（含空响应）**均入队三路**；**开关开启**时 —— 低价值轮 `returns={memory:skipped, rag:skipped, profile:skipped}` 且 **`submitted=[]`**；高价值轮（记忆意图 0.8）**三路入队**且 `rag` **全文**（`rag_response_unchanged=true`）；普通轮 `submitted=[memory, profile]` 且 **`rag` 跳过**；长响应轮（≥120 字）`rag` 全文入库。⑦ **护栏（TDD）**：新增 `tests/unit/test_writeback_decision_gate.py` **13 例**（判定纯函数 6 例 / 开关关闭逐字一致 2 例 / 开启后拦截·分级·载荷保持 4 例 / 回执 `skipped` 口径 1 例）。⑧ **回归与静态质量**：全量 `tests/unit` **32 failed / 3019 passed / 0 error**（239.85 s；收集 3051）；**失败集与上一轮（第 31 批）逐项完全相同**（逐项 testid 归一化后 `Compare-Object` **32 = 32，零差异 ⇒ 零新增失败**）；本轮 5 文件 `ruff` **零告警**。⑨ **未实施（如实登记）**：`evaluate_session()` 的**载荷形态**（窗口摘要 / 频控预检 / 画像增量）仍未接线 —— **阻塞于 §9 待裁定问题 4**（记忆写入语义：是否允许「整轮全文 → 提炼结论/摘要」）；`画像增量升级`、`队列可观测与死信`、`写路径与通道一致` 三项仍待做。⑩ 提交：**OpenLLM `c60ce2b`（4 生产 + 1 测试，`+363/-2`）**。状态 [Draft] |
| v1.5.0 | 2026-09-27 | AD-OpenBase-Dev | **第二批第 ② 项实施回填：组件依赖图调度（方案 §3.1 / §4.2「顺序优化」，判据 T8）**。① **动因**：`run_components` 的串并行**只看全局开关** `OPENLLM_ENABLE_PARALLEL`（默认 False ⇒ 恒串行），而 memory/rag **互不依赖**（不读对方结果）—— 凭开关而非依赖关系决定调度，等于把「本可并行」白白串行化；且「严格顺序」这类**语义**诉求被压在一个全局布尔里。方案要求「串并行不再依赖全局开关，改由依赖图判定；需要严格顺序用依赖声明表达，不用全局开关」。② **新增依赖图模块**（`app/edgerouter/orchestration/component_graph.py`）：`parse_dependencies(declaration)`（`child:parent` 逗号分隔；空白容忍；非法片段**跳过并告警**，不做静默猜测）、`dependency_levels(names, dependencies)`（Kahn 式波次划分，**指向未参与本次执行的组件视为已满足**）、`resolve_schedule(deps)`；**成环 ⇒ fail-safe**：退化为单波次保序并告警（**不抛异常、不打挂请求**）。③ **调度接线**（`component_pipeline.py`）：新增 `resolve_schedule_plan(names, *, enable_parallel)` → `(波次列表, 同波次可否并发)`；`run_components` 改为**按波次执行**（同波次 >1 用 `asyncio.gather`、波次间严格有序），并按**条目下标**消费以保证重复组件与原有顺序语义不变。开关 `COMPONENT_DEPENDENCY_SCHEDULING_ENABLED`（默认 **False**）**关闭时**计划恒为「单波次」且并发与否仍由 `enable_parallel` 决定 ⇒ 与既有实现**逐字一致**；**开启时**「无依赖即并行」（即使 `enable_parallel=false`），严格顺序改用 `OPENLLM_COMPONENT_DEPENDENCIES`（如 `memory:rag`）声明。④ **运行态探针**（`doc/test/evidence/cr149/component_schedule_probe.py`，真实共用组件步骤 + 真实调度器，组件各 0.12 s、含预热）：关闭态 `enable_parallel=false` ⇒ 墙钟 **0.25 s 不重叠**、`=true` ⇒ **0.125 s 重叠**（既有语义不变）；**开启态 + `enable_parallel=false` + 无依赖 ⇒ 0.125 s 重叠**（「无依赖即并行」生效）；**开启态 + 声明 `memory:rag` ⇒ 波次 `[["rag"],["memory"]]`、事件严格 `rag→memory`、0.235~0.25 s 不重叠**（声明**覆盖**全局并行开关）；图形层：无依赖单波次 / `memory:rag` 两波次 / 成环单波次 fail-safe / 解析三种形态全部符合预期。⑤ **护栏（TDD）**：新增 `tests/unit/test_component_dependency_scheduling.py` **12 例**（依赖图形 5 例：单波次 / 声明分波 / 未知依赖忽略 / 成环 fail-safe / 声明解析；开关关闭 3 例：默认值断言 / 串行不变 / 全局开关并行仍生效；开关开启 4 例：无依赖即并行（重叠序断言）/ 声明严格保序（事件序列断言）/ 单组件无副作用 / 逐组件计量不变）；**既有 `test_component_pipeline_shared.py` 13 例全绿**（共用步骤语义未变）。⑥ **回归与静态质量**：全量 `tests/unit` **32 failed / 3031 passed / 0 error**（239.55 s；收集 3063，较上一轮 +12 ＝ 本批护栏）；**失败集与上一轮逐项完全相同**（逐项 testid 归一化后 `Compare-Object` **32 = 32，零差异 ⇒ 零新增失败**）；本轮 4 文件 `ruff` **零告警**（过程中修正 2 项：惰性导入块 isort 排序、文件末尾换行）。⑦ **风险如实登记（新增三项入 §8）**：并行度提升带来下游并发压力（回退＝依赖声明或整体关开关）；依赖声明写错（漏声明只影响并行度、成环 fail-safe 退化）；并行后 Σ步骤 ≥ 真实墙钟（与第一批画像并行同源，按关键路径复核）。⑧ **未实施（如实登记）**：通道裁决进取数层（通道 A 无业务调用点，§9 问题 1 待裁定）；§4.2 余项（阈值与单次命中语义对齐、LLM 兜底分类器接线、规则集可配置）均未做。⑨ 提交：**OpenLLM `ec3485a`（3 生产 + 1 测试，`+432/-6`）**。状态 [Draft] |
| v1.6.0 | 2026-09-27 | AD-OpenBase-Dev | **第二批第 ③ 项实施回填：备通道健康探针（方案 §4.1「配套两项必做」之一，判据 T4 前置条件）**。① **动因**：方案明示「无论选哪条通道路线，以下两项必做」，其一为**备通道健康探针** —— 把「主/备可用性」纳入 `GET /openllm/v1/health` 的 components（外部三组件 ＋ **内置 RAG 索引数** ＋ **Ollama 可达性**），供人工验证与自动裁决**共用同一事实源**；现状缺口是 `components` 只含外部三组件，导致「内置 RAG 备通道无底座」**不可观测**，真实故障会表现为「接管成功、注入为空」（静默劣化）。② **实现**：新增 `_count_faiss_indexes(root)`（按 `<root>/<kb-id>/index.faiss` 计数，与 `VectorStoreService` 落盘约定同一事实源）、`_probe_builtin_rag(db)`（KB 行数 ＋ FAISS 索引数 ＋ `has_base`；无底座时 `reason` **显式**给出「备通道接管后将注入为空」）、`_ollama_probe_tags()` / `_probe_ollama()`（`GET {OLLAMA_HOST}/api/tags` 只读面、2 s 独立超时、返回 `models` 数）；`_probe_components(db)` 一次 `asyncio.gather` 并行探测 **5 项**并共用既有结果缓存；`/health` 端点增 `db` 依赖以统计 KB 行数。**探测一律不抛异常**（DB / 文件系统异常降级为 `unavailable` ＋ `reason`），保证 health 在依赖故障下仍可用。③ **开关与风险**：本项为**纯观测扩展**，无行为开关；对既有响应为**增量字段**（原三键原样保留）。④ **运行态探针**（`doc/test/evidence/cr149/health_backup_probe.py`，调真实探测函数）：`faiss_root_exists=true` 但 `faiss_indexes_scanned=0`；`builtin_rag` = `{status: unavailable, knowledge_bases: 0, indexes: 0, has_base: false, reason: "内置 RAG 无底座（KB 0 行 / FAISS 0 索引）⇒ 备通道接管后将注入为空"}`；`ollama` = `{status: ok, latency_ms: 15, models: 2}`；`components_keys = [builtin_rag, dps, ollama, openmemory, openrag]`（同一事实源）。⑤ **护栏（TDD）**：新增 `tests/unit/test_health_backup_channel_probe.py` **10 例**（无底座显式 reason / FAISS 根缺失不报错 / 底座就绪为 ok / DB 失败降级不抛 / 无 DB 支持；Ollama 可达含 models 数 / 不可达降级 / 探活 URL 取自配置且为只读面；`_probe_components` 同时含外部三组件与备通道两键 / health 端点把 db 传入探测）。⑥ **回归与静态质量**：全量 `tests/unit` **31 failed / 3042 passed / 0 error**（238.83 s；收集 3073，较上一轮 +10 ＝ 本批护栏）；**失败集为上一轮基线的子集**（32 → 31，**无新增失败项**）—— 唯一差异为既有 flaky `test_v213_gateway_ext.py::test_memory_writeback_adapter_missing_raises`（`Event loop is closed` 一类异步卫生项，隔离复跑通过）本轮**转绿**，如实登记为**基线波动而非本批收益**；本轮 2 文件 `ruff` **零告警**（过程中修正 1 项：gateway 增补缺失的 `import os`）。⑦ **未实施（如实登记）**：**内置 RAG 种子底座**（需运行态 DB ＋ 嵌入模型，本批次未执行；方案 §4.1 的替代口径「内置 RAG 仅在有本地索引时生效」已在方案中明确，并由 `has_base=false` 前置可见）；**通道定性**（接线 / 探活专用 / 废止）仍待 §9 问题 1 **人工裁定**；队列指标与死信、通道裁决进取数层未做。⑧ 提交：**OpenLLM `03a624f`（1 生产 + 1 测试，`+327/-9`）**。状态 [Draft] |
| v1.7.0 | 2026-09-27 | AD-OpenBase-Dev | **第二批第 ④ 项实施回填：回写队列可观测与死信（方案 §4.3「队列可观测与死信」）**。① **动因**：回写队列此前可观测面只有「进程内 `_pending` 长度」一个数 —— 看不出**失败率**与**重试是否集中触顶**；`failed` 行既无视图也无重放入口（只能直连 SQLite 手工排查重放），且 `cleanup_failed` 虽存在但**全仓无调用点**（死信只能靠手工清理）。② **聚合指标**：`WritebackStore.stats(user_id=None)` 以三条聚合 SQL（状态分组 / `retry_count>0` 直方图 / 最早未完成 `updated_at`）产出 `total` / `by_status` / `failure_rate`（空库 `0.0`，**不除零**）/ `retried_rows` / `retry_distribution` / `max_retry_count` / `oldest_open_at`；`WritebackQueue.stats()` 另补 `queue_depth`（在飞任务数），使「落盘状态」与「在飞任务」两个视角同一响应可见。③ **死信视图与重放**：`list_dead_letters()`（只含 `failed`、`limit`/`offset` + `total` 分页、**不含 `payload_json`**）；`claim_failed()` 在**单连接单事务 + 存储层 `_lock`** 下把 `failed` → `pending`、`retry_count=0`、`next_retry_at=NULL` 并回传 payload（**只动 `failed` 行**，执行中的行不会被拉回重跑）；`replay_dead_letters()` 复用 `_run_item` 同一执行路径（含信号量/退避），**未注册 handler 的目标计 `skipped` 且行留在 `pending`**。④ **接口层**：新增 `GET /writeback/stats`、`GET /writeback/dead-letter`、`POST /writeback/dead-letter/replay`；三者**无身份 401（1001）**、统计与死信**按调用方作用域**（沿用 `DEF-BE-148-007` 的 `json_extract` fail-closed）、重放**仅接受显式行 id 且单次 ≤100**（超限 4003），并复用 `_ensure_writeback_handlers` 保证重放可投递；**未开放全局口径**（避免以聚合推断他人回写规模，留待按角色门禁）。⑤ **失败 TTL 清理任务化**：新增 `WritebackQueue.run_cleanup_loop(interval)`（**单轮异常不终止循环**、`interval≤0` 立即返回），由 `main.py` lifespan 启动并在关闭时 `cancel()+await`；间隔由新增 `WRITEBACK_CLEANUP_INTERVAL_SECONDS`（默认 3600 s）驱动，**置 0 = 关闭定时清理**。⑥ **运行态探针**（`doc/test/evidence/cr149/writeback_observability_probe.py`，真实存储层 + 队列层 + 独立临时 SQLite）：造数（u-1 三行 done/failed×2 ＋ u-2 一行 failed）→ 全局 `stats` `{total:4, by_status:{done:1, failed:3}, failure_rate:0.75, retry_distribution:{"2":1,"3":2}, max_retry_count:3}`；**按用户作用域** `u-1` `{total:3, failed:2, failure_rate:0.667}`（u-2 与无归属历史行均不见）；死信视图 `total=3` 且 `has_payload_field=false`；**重放 2 行 → `replayed=2`、handler 实投递 2 次、两行状态转 `done`**；**越权取件返回 `[]` 且 u-2 行状态保持 `failed`**；`run_cleanup_loop(0)` 即时返回、TTL 清理对**新近**死信不误删（`failed_after_cleanup=1`）。⑦ **护栏（TDD）**：新增 `tests/unit/test_writeback_queue_observability.py` **22 例**（聚合 4 / 死信视图 3 / 取件 3 / 队列重放 3 / 接口层 5 / TTL 任务化 4）。⑧ **回归与静态质量**：全量 `tests/unit` **32 failed / 3063 passed / 0 error**（244.44 s；收集 3095，较上一轮 +22 ＝ 本批护栏）；**失败集与第 33 批基线逐项完全相同**（`Compare-Object` **32 = 32，零差异 ⇒ 零新增失败**）；**对照实验（决定性证据）**：对 `test_v213_gateway_ext.py` 用 `git stash push -- <本批 4 个生产文件>` 回退后**隔离复跑，得到与改动后完全相同的 4 个失败**（`Event loop is closed` 一族 + bypass 500）⇒ 该文件为**既有序相关 flaky**，与本批改动无关（上一轮该文件曾少失败 1 例，属同源波动）。本轮 5 文件 `ruff` **零告警**（过程修正：新增 `import asyncio`（main.py）/ `Sequence`（writeback_queue.py）/ `_sql_where` 助手）。⑨ **未实施（如实登记）**：**全局/运维口径**统计（需角色门禁）、§4.2 余项（阈值语义对齐 / LLM 兜底分类器 / 规则集可配置）、§4.3 余项（画像增量升级 / 写路径与通道一致）、通道定性（§9 问题 1 待裁定）与内置 RAG 种子底座（需运行态 DB ＋ 嵌入模型）均未做。⑩ 提交：**OpenLLM `1a572f7`（4 生产 + 1 测试，`+782/-2`）**。状态 [Draft] |
| v1.8.0 | 2026-09-27 | AD-OpenBase-Dev | **第二批第 ⑤ 项实施回填：组件决策三余项（方案 §4.2「阈值与单次命中语义对齐 / 规则集可配置 / LLM 兜底接线」，判据 T9）**。① **动因**：`R001`/`R002` **单次**关键词命中置信度 0.8 **低于阈值 0.85** ⇒ `decide_sync` 返回 `None`、实际走「回落最优候选」，即**「达标判定」与「最终决策」隐性分叉**；`R005` 复合意图同为 0.8 ⇒ **永不达标**；`ComponentRouter(rules_path=...)` 与热更新早已实现但**无任何配置键接入**（改关键词必须改代码）；`llm_classifier` 形参存在但**无任何注入点** ⇒ 兜底分类在生产**恒为死代码**。② **阈值对齐**：单次命中 0.8 → **0.86**、`R005` 0.8 → **0.86**，均由配置驱动（`COMPONENT_ROUTER_SINGLE_HIT_CONFIDENCE` / `COMPONENT_ROUTER_COMPOSITE_CONFIDENCE`，**默认 0.86**）；**逃生阀**：配回 0.8 即复现旧「回落」语义；低配时仅告警不强制改写。③ **规则集可配置**：新增 `COMPONENT_ROUTER_RULES_PATH` 并接入 `ComponentRouter` 构造；**路径非法/文件损坏告警并退回内置规则**（不中断服务）。④ **LLM 兜底接线**：新增 `_build_component_router()`（`_auto_component_plan` 统一调用）—— 开关 `COMPONENT_ROUTER_LLM_FALLBACK_ENABLED`（**默认关闭**）开启且存在 DB/身份时注入分类器：复用 `_call_llm`（模型取 `COMPONENT_ROUTER_LLM_MODEL`、`temperature=0`、`max_tokens=64`）并施加 **300ms** 超时（`COMPONENT_ROUTER_LLM_TIMEOUT_SECONDS`）；超时/异常/非法 JSON **一律回落规则**。**默认关闭理由**：按 §5.4/§5.5 实测 ≤1B 本地模型在 300ms 在线预算内不可达标，无合格分类器时开启只是白付预算。⑤ **运行态探针**（`doc/test/evidence/cr149/component_decision_probe.py`）：单次记忆／单次知识命中「旧 0.8 不决策 → 新 0.86 直接决策」、`R005` 的 `qualified` `false → true`、无候选查询不变；自定义规则文件（`X001`）生效且非法路径退回内置 5 条规则；LLM 兜底「关=不注入 / 开=注入 / 超时=回落规则」。⑥ **护栏（TDD）**：新增 `tests/unit/test_component_router_decision_tuning.py` **15 例**；**3 个既有护栏按新契约更正**（`test_component_signal_union` / `test_router_candidate_trace` / `test_orchestration` 各 1 例 —— 原断言编码的正是方案指出的「隐性分叉」，改用**逃生阀显式配回 0.8** 复现旧场景并**同时锁定新默认**，属**契约更正而非放宽断言**）。⑦ **回归与静态质量**：全量 `tests/unit` **31 failed / 3079 passed / 0 error**（244.08 s；收集 3110 ＝ 上一轮 +15）；（逐项 testid 归一化后 `Compare-Object`）**无新增失败项**（失败集为基线**子集** 32 → 31，差异项仍是已用对照实验证实的既有序相关 flaky `test_v213_gateway_ext.py::test_memory_writeback_adapter_missing_raises`）；`component_router.py` `ruff` **39 = 39 零新增**（其余文件 2 = 2 零新增；过程中把我新增的两个 `Optional[float]` 形参改为 `float | None` 以避免 +2 告警）。⑧ **未实施（如实登记）**：通道定性 / 通道裁决进取数层 / 内置 RAG 种子底座 / §4.3 写路径与通道一致（后三者依赖 §9 问题 1 裁定或运行态环境）。⑨ 提交：**OpenLLM `0abcaea`（3 生产 + 4 测试，`+417/-16`，其中 1 个测试文件新增、3 个既有护栏按新契约更正）**。状态 [Draft] |
| v1.9.0 | 2026-09-27 | AD-OpenBase-Dev | **缺陷登记与修复：`DEF-BE-148-029` 画像增量提炼服务缺失（第二批实施中的仓内一致性审计发现，详见 OpenBase《问题跟踪记录》v1.44.0 §4L）**。① **缺陷**：`evaluate.py::_profile_updates_for` 惰性导入 `app.services.profile_refine` 的三符号，而**该模块在仓内不存在**（递归查找仅命中 `__pycache__/profile_refine.cpython-310.pyc`）⇒ 写侧入口 `evaluate_session(..., {"enable_profile_delta": true})` 一旦接线即 **ModuleNotFoundError**（当前入口无调用点故未触发，属「埋雷」型 P1）。**根因**：同批源码未随提交落库 ＋ 引用方无 fail-safe ＋ 本文档 §4.3 所述配置键 `OPENLLM_PROFILE_LLM_REFINE` **当前树不存在**（文档-实现漂移，本版一并更正）。② **修复**：**(i)** 补回 `app/services/profile_refine.py`（规则提炼语义**逐字取自既有线上实现**，非重新发明；导出 `DEFAULT_PROFILE_TARGETS` / `set|get_active_profile_refiner` / `refine_profile_delta` / `extract_topics` / `infer_tone`）；**(ii)** 回写路 `writeback._resolve_profile_updates` / `_extract_topics` / `_infer_tone` 改为**薄封装委托**（**单一事实源**，既有公开名与语义保留 ⇒ `test_v2143_writeback_profile.py` 契约不破）；**(iii)** 提炼器**注入位点**（同步契约 `refine_fn(dialogue) -> dict \| None`；未注册 ⇒ 纯规则路径；失败/空/非 dict ⇒ **保留规则结果**）；**(iv)** `evaluate._profile_updates_for` 整体（**含导入**）纳入 fail-safe ⇒ 提炼链路异常**降级为空增量并告警**。③ **验证**：新增护栏 `tests/unit/test_profile_refine_service.py` **17 例**（首轮 RED 的失败信息本身即缺陷证据）；既有回写画像护栏 **13 例全绿**；运行态探针 `doc/test/evidence/cr149/profile_refine_probe.py`（三符号齐备 / 写侧链路真实产出增量 / 注入生效与失败回落 / 回写路与服务模块 5 类入参结果一致）。④ **回归**：全量 `tests/unit` **32 failed / 3095 passed / 0 error**（251.93 s；收集 3127）；失败集与已知 32 项集相同 ⇒ **零新增失败**；**对照实验（决定性）**：回退本批改动后隔离复跑 `test_v213_gateway_ext.py` 得**完全相同的 4 个失败** ⇒ 该文件为**既有序相关 flaky**，与本批无关。⑤ **§4.3「画像增量升级」状态**：**基座已补回；线上 LLM 门控待决策** —— 提炼器位点就绪，但线上接线须先裁定同步/异步形态（**§9 新增问题 7**），本批**不代行接线**，默认保持纯规则路径（线上零影响）。⑥ 提交：**OpenLLM `5589ddf`（3 生产 + 1 测试，`+442/-52`）**。状态 [Draft] |
| v1.10.0 | 2026-09-27 | AD-OpenBase-Dev | **§7 判据执行器交付 ＋ 执行器暴露的两处结构性缺口修复（第一批 T1/T2 的**实现更正**）**。① **交付执行器**（`doc/test/evidence/cr149/t_acceptance_runner.py`）：把 T1~T9 做成**一键可复跑**的判定器，逐条输出 `PASS / FAIL / SKIP / BLOCKED` ＋**原始测量数据**（`--json` 落盘）；默认按**当前配置**判定（开关未开 ⇒ `SKIP` 并给出需置哪些键），`--simulate` 在**进程内**临时置位（退出恢复、不写配置、不影响运行中服务）以验证"开启后即达标"；`SKIP`/`BLOCKED` **不计入失败**但显式列出（避免"没做"被误读成"通过"）；退出码 `0`=无 FAIL。**首跑即发挥作用**：T2 `FAIL`、T1 `PASS`（但经复核为**条目粒度偶然留隙**所致，非结构保证）。② **缺口一（T1，结构冲突）**：§3.3 原本就要求「`query + 模板开销` 留余量」，但第一批把 5 段比例设为 `0.05/0.05/0.30/0.40/0.20`（**和 = 1.00**）⇒ 各段满额时 `prompt_total_tokens = available + 查询 ＋ 开销 > available`，与 T1 结构性冲突。**修法**：标定为 `0.05/0.05/0.28/0.37/0.19`（**和 = 0.94**），新增常量 `QUOTA_HEADROOM_CEILING = 0.95` 并在配置默认值同步；执行器 T1 改用**填满配额**的最坏夹具（原夹具条目偏小、会把结构性溢出掩盖成通过）。③ **缺口二（T2，单条即超配额 ⇒ 整段清空）**：配额裁剪从尾部整条丢弃，若单条素材大于该段配额则一路丢到空（实测 history `dropped_items=6 / used=0`，配额白白浪费且该段归因缺失）。**修法**：新增 `_fit_single_unit()` 与「**保底一条**」——**仅当裁剪将清空该段时**保留首条，先按句边界、再按比例收敛，并**连同渲染编号前缀一并计入**（首版实测 `193 > 190`，即前缀未计入）硬压进配额，记 `truncated_items`；**可装下首条时不触发** ⇒ 既有整条丢弃语义不变。④ **顺带显式化**：`quota = 0` 的语义（**"不限"= 不裁剪**，fail-open，避免误配 `..._RATIO=0` 静默清空整段）写入 `BudgetPolicy.quota` docstring，且 T1 的 `used ≤ quota` **仅对 `quota > 0` 的段**成立。⑤ **护栏（TDD）**：新增 `tests/unit/test_context_budget_headroom_and_floor.py` **7 例**（保底触发与守配额（含**无句末标点的超长单条**硬性收敛）/ 可装下时不触发 / `quota=0` 语义锁定 / 内置与配置比例余量 / **满额场景 `prompt_total_tokens ≤ available`**）；既有 `test_context_budget.py` **13 例**等预算护栏**全绿**（整条丢弃语义未变）。⑥ **回归与静态质量**：全量 `tests/unit` **32 failed / 3102 passed / 0 error**（245.06 s；收集 3134 ＝ 上一轮 +7）；**失败集与上一轮逐项完全相同**（`Compare-Object` **32 = 32，零差异 ⇒ 零新增失败**）；本轮 3 文件 `ruff` **零告警**。⑦ **执行器两态实测**：**当前配置** ⇒ `{PASS:3（T3/T7/T9）, SKIP:4（T1/T2/T5/T8）, BLOCKED:2（T4/T6）, FAIL:0}`；`--simulate` ⇒ `{PASS:6, SKIP:1（T8：能力达标但开关未开）, BLOCKED:2, FAIL:0}`。**T4 为"前置不满足"的 `BLOCKED`**（内置 RAG 无底座 ⇒ 接管必然注入为空，须先补底座或声明口径）；**T6 属第三批**（生成式精炼）。⑧ **未达成（如实登记）**：T4 需**运行态故障注入**（本执行器不改外部服务状态）、T6 需**第三批能力**、T8/T1/T2/T5 **需人工批准开关值后复跑**。⑨ 提交：**OpenLLM `4389ded`（2 生产 + 1 测试，`+253/-9`）**。状态 [Draft] |
| v1.11.0 | 2026-09-27 | AD-OpenBase-Dev | **T4 轨迹两路径口径收敛（第二批第 ⑥ 项部分完成）＋ 执行器 T4 进程内化**。① **动因（复核 T4 时发现的真实缺口，非测试写法问题）**：T4 被评为 `BLOCKED` 的依据是「内置 RAG 无底座」，但其**「轨迹」部分其实不依赖运行态**，可在进程内判定。复核中发现 **流式路径的接管发生在共用组件步骤**（`component_pipeline.run_components`），该步骤**只落 `rag_source`、不落归因**；而同步路径 handler 落 `builtin_fallback_reason` ⇒ **两路径轨迹口径不一致**（流式缺「为何接管」），且两处字段**各自手写**，属可再次分叉的隐患（与 §2「双路径分叉」同类形态）。② **修复一（共用步骤落归因）**：`ComponentRunResult` 新增 `builtin_fallback_reason`，回退分支写入（新增 `REASON_MAX_CHARS = 120` 与 `_fallback_reason()` 截断，**避免异常正文无界落痕**）；模块 docstring 同步。③ **修复二（单一落痕实现）**：网关新增 `_merge_rag_trace(components, *, rag_source, builtin_fallback_reason)`，**同步与流式两路径共用**——同步路径的轨迹字面量经它构造（来源与归因取自 `shared_state`），流式路径在**初始化**与**组件执行后**两次调用它；`_run_stream_components` 回传归因；删除原手写字段与 `if shared_state.get(...)` 分支。④ **语义保持（未改既有行为）**：未执行检索仍为 `skipped` 且**不落空归因**；`external` 不落归因；**装配缺失 / 超时仍不触发回退**（`DEF-BE-148-012` 语义不变）；回退**不计 `degraded`**（回退成功 ≠ 降级）。⑤ **执行器 T4 拆分**：由「整体待运行态」改为「**轨迹 = 进程内判 ＋ 无 5xx = 运行态**」——7 项判定（两路径来源、两路径归因、归因一致、来源一致、未检索时 `skipped` 且无归因）；**轨迹不达标即 `FAIL`**；`detail` 增 `sync_trace_components` / `stream_trace_components` / `trace_contract` / `runtime_pending` / `historical_e2e_evidence`；状态仍为 `BLOCKED`（剩余运行态部分未验），但 `reason` 明确**轨迹部分已通过**。⑥ **护栏（TDD）**：新增 `tests/unit/test_rag_builtin_fallback_trace.py` **14 例**（首轮 **RED 11 failed / 3 passed**，失败信息即缺口证据）——共用步骤归因 / 回退不计降级 / 成功不带归因 / 装配缺失与超时不回退 / 开关关 / 归因截断 / 同步 handler 归因与截断 / 落痕函数三态 / **两路径逐键一致**；既有 `test_rag_unregistered_no_fallback.py` / `test_component_pipeline_shared.py` / `test_stream_auto_parity.py` 等 **89 例全绿**。⑦ **实测（执行器进程内判定）**：同一故障（`RuntimeError: OpenRAG 不可达: connection refused`）下两路径轨迹**逐键一致** —— `{rag_source: "builtin", builtin_fallback_reason: "OpenRAG 不可达: connection refused"}`；`has_base=false` 仍如实留痕（接管后注入为空）。⑧ **回归与静态质量**：全量 `tests/unit` **31 failed / 3117 passed / 0 error**（245.15 s）；**失败集零新增**（与基线 `Compare-Object` 无 `=>` 项），唯一差异为既有 flaky `test_v213_gateway_ext.py::TestWritebackInternalHandlers::test_rag_writeback_adapter_missing_raises` 本轮**转绿**（如实登记为**基线波动，非本批收益**）；本轮 3 文件 `ruff` **零告警**；执行器 5 项既有 ruff 告警（I001/F401/F841/B905/UP035）一并清理 ⇒ `All checks passed`。⑨ **如实登记的新待登记项**：T4 原文要求的「审计事件」当前落点为**接管 WARNING 日志**，**独立审计落库（`AuditLog`）未接入** → 新增 **§10 待登记项 6**（如需强审计须单独立项）。⑩ **未做**：通道定性（§9 问题 1 待裁定）、通道裁决进取数层、内置 RAG 种子底座（运行态 DB ＋ 嵌入模型）、§4.3 余项（画像增量升级形态待裁定 / 写路径与通道一致）、T6 第三批。⑪ 提交：**OpenLLM `b37e0c0`（2 生产 + 1 测试，`+387/-29`）**。状态 [Draft] |
| v1.11.1 | 2026-09-27 | AD-OpenBase-Dev | **同批补充：T4「无 5xx」段补齐端点级（HTTP）故障注入证据（护栏 14 → 18 例），执行器运行态待验范围收窄**。① **动因**：v1.11.0 只把 T4 的**轨迹**段做成进程内可判，`runtime_pending` 仍列「故障注入后的 HTTP 响应无 5xx」。复核后确认该段**同样可在进程内判定** —— 用 `TestClient` 打**真实端点**、以**适配器替身抛异常**注入组件故障即可，无需停服。② **新增护栏 4 例**（`tests/unit/test_rag_builtin_fallback_trace.py::TestEndpointLevelFaultInjection`）：**同步** `POST /openllm/v1/chat` 外部失败 + 开关开 → **200**、`routing_trace.components.rag_source=builtin` 且带归因、**不计降级**；开关关 → **200**、`rag_source=skipped` 无归因、`degraded` 含 `rag`；**装配缺失**（开关开）→ **200**、`skipped` 且**内置回退零调用**（`DEF-BE-148-012` 不回退）；**流式** `POST /openllm/v1/chat/stream` 外部失败 + 开关开 → **200**、`event: routing` / `event: done` 齐备且**无 `event: error`**、**落库轨迹入参**（`_save_trace` 第 8 个位置参数）同样带 `rag_source` 与归因。③ **口径如实标注**：故障由**适配器替身**注入（＝组件故障），**非**停服务 / 改不可达地址；该层证明「组件故障时两端点均不返回 5xx 且轨迹可复盘」，**不替代运行态真实停服 E2E**；`_save_trace` 在用例中被替身替换，故证明的是**落库调用入参**而非**实际落库读取**。④ **执行器同步**：T4 的 `runtime_pending` 收窄为「**真实**停服/改址注入」与「轨迹**实际落库**读取」两项、并新增 `detail.endpoint_level_evidence` 指向上述 4 例；`requires` 同步收窄；**状态仍为 `BLOCKED`**（该项与 `has_base=true` 前置未满足），但 `reason` 明确「轨迹 ＋ 无 5xx 均已在**进程内**覆盖」。⑤ **回归与静态质量**：全量 `tests/unit` **31 failed / 3121 passed / 0 error**（249.69 s；较 v1.11.0 轮次的 3117 增 4 ＝ 本批补充护栏）；**失败集零新增**（与基线逐项 testid 归一化后 `Compare-Object` **无 `=>` 项**）；本轮 2 文件 `ruff` **零告警**。⑥ 提交：**OpenLLM `13707fc`（1 测试，`+133/-1`）**；执行器与本文档同批入库。状态 [Draft] |
| v1.12.0 | 2026-09-27 | AD-OpenBase-Dev | **仓内一致性审计：§3.4 规则档余项与 §3.5 引用编号「正文已指定但未实施」的逐项登记（**无代码改动**）**。① **动因**：T4 收口后对方案正文做一次**逐条 vs 仓内实现**的一致性核对，以确认「正文指定 ≠ 已实施」，避免"方案写了"被误读为"已完成"。② **审计方法（可复现）**：对 `OpenLLM/backend/app/` 全仓检索关键标识 —— `strip_metadata` / `METADATA_NOISE` / `noise`、`"refine"`、`[M{` / `[K{` / `[M1]` / `[K1]`，并逐行读 `PromptAssembler.format_context` / `_format_list` 与 `prompt_pipeline._trim_segment` / `render()`。③ **审计结论（4 项未实施，均**无外部依赖**）**：**(a) 剥离元数据噪声**（`trace_id:None` 一类平铺字段）——检索零命中，平铺分支不过滤 `None`/空值且无噪声键名单；**(b) 相邻记忆条目合并同义重复行**——现有去重为「归一化后**精确重复即丢弃**」，非合并、无同义判定（`_normalize_key` 注释所称"同义重复"实为归一化精确重复）；**(c) `refine` 回执字段**（`{mode, model, in_tokens, out_tokens, elapsed_ms, fallback}`）——检索零命中，规则档亦无落痕；**(d) 稳定引用编号 `[M1]`/`[K1]`**——检索零命中，现只产出 `"{序号}. {正文}"`，且 `_trim_segment` 在裁剪/去重后会**重排序号**（与「稳定编号」要求相反）。④ **同时确认已实施**（避免审计结论被扩大化）：§3.4 规则档的**去重 / 配额整条裁剪 / 单条句边界截断**均已实施（第一批 ＋ v1.10.0 保底一条）；§3.5 的 **`system` 段启用**已实施（第一批）。⑤ **登记位置**：§3.4 / §3.5 各增「实施状态」表（含取证），§6 第二批新增第 ⑦ 行（含依赖关系：**无外部依赖、可立即实施**，与 ⑥ 中需人工裁定的各项明确区分），§10 新增**待登记项 7**（含 (a)~(d) 明细与默认值建议：(d) 建议开关默认关闭）。⑥ **影响面**：**无代码改动、无行为变化**；不影响任何已实施项、不影响已判 `PASS` 的 T3/T7/T9 与已知 `BLOCKED`/`SKIP` 结论。⑦ **下一步（不受阻）**：优先实施 (a)~(d)，其中 (c) 需先定义规则档回执的落痕位置（`context_metrics` 还是独立字段）。状态 [Draft] |

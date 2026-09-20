# OpenBase 编排链路上下文预算裁剪评估报告 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 评估主题 | R-395 编排链路接入上下文预算裁剪（可行性、方案比选与工作量） |
| 文档版本 | v1.1.0 |
| 状态 | [Review] |
| 作者 | AU-OpenBase-Dev（审计师视图，独立于设计与开发视图） |
| 评估日期 | 2026-09-21 |
| 存放 | doc/audit/assessment/ |
| 上游依据 | 《OpenBase-智能体会话上下文编排评估报告-v1.0.0》§7 缺口 **G-01**、§10 五参数 |
| 需求依据 | `doc/version/global/OpenBase-候选需求池.md` §1.18 **R-395**（P2，**当前未纳入任何版本**） |
| 落点归属 | **OpenLLM 仓**（`backend/app/edgerouter/orchestration/`），本仓不得实施（`VC-014`） |

---

## 1. 评估范围与方法

| 项 | 内容 |
|----|------|
| 评估对象 | R-395「将 `ContextManager` 接入编排链路，使 Prompt 组装按模型上下文窗口做预算感知裁剪」的可行性、方案与工作量 |
| 评估方式 | 双侧代码勘察（上下文服务能力面 + 编排链路数据流）+ **关键事实定点复核** + 方案比选 + 现状缺陷登记 |
| 勘察范围 | OpenLLM：`backend/app/services/context_manager.py`（871 行）、`backend/app/api/context.py`、`backend/app/schemas/context.py`、`backend/app/api/conversations.py`、`backend/app/api/openllm_gateway.py`（编排相关函数）、`backend/app/edgerouter/orchestration/{assembler,executor,auto,explicit}.py`、`backend/app/edgerouter/adapters/{openmemory,openrag}.py`、`backend/app/services/writeback_queue.py` |
| 关键事实定点复核 | 本报告对三项**改变结论**的事实做了逐行复核（非二手转述）：① `MODEL_CONTEXT_LIMITS` 表结构与匹配算法（`context_manager.py:43-86`、`:161-203`）；② 组装结果如何进入 LLM（`openllm_gateway.py:1122-1133`）；③ 流式路径的 Prompt 组装点（`openllm_gateway.py:1985-2005`） |
| 纪律 | 只读勘察，**未修改任何文件**；不代改需求文档与产品代码；发现项如实登记（含影响本需求工作量的新增发现） |
| 局限声明 | ① 未实机运行 OpenLLM 服务，预算裁剪效果未做端到端实测；② 工作量为人天量级**估算值**，非排期承诺；③ 未逐行核对 `ConversationMessage.token_count` 是否在写入时恒被赋值（影响 F-04 的实际表现面） |

---

## 2. 核心结论

| 序号 | 结论 | 置信度 |
|------|------|:------:|
| 1 | **R-395 不是「接线」任务，而是「新建能力」任务**。现有 `ContextManager` 的裁剪能力是**消息列表级**（`List[Dict]`），而本链路的待裁剪对象是**片段级拼接字符串**（画像 + 记忆 + 知识库 + 问题，最终合成为**单条 user 消息**）。二者粒度错配，无法通过「在编排链路里调一次 `manage_context`」实现 | 高（逐行复核） |
| 2 | 若强行把整段 Prompt 作为单条消息交给 `manage_context`，**裁剪不会发生**（无 system 消息时 `preserve_system` 策略从尾部填充，单条消息必被整条保留）；若换 `recent` 策略，单条超限时会返回**空列表**，属灾难性行为 | 高 |
| 3 | 需求必须新增**片段级预算裁剪能力**，并在**同步与流式两条路径**同时接入（流式路径已实测为独立实现、绕过编排层） | 高（逐行复核） |
| 4 | ~~推荐方案 B1（按条目尾截断的片段级预算，保持 `PromptAssembler` 签名兼容），可满足最小可用；若采纳「分段 token 配额」参数则升级为 B2（配额制）~~ → **已被第 5 条修正，B1 降为过渡形态** | 中高 |
| 5 | **v1.1.0 方案修正**：推荐方案由 B1（按条目尾截断）上调为 **B2（结构化片段 + 配额保底 + 相关性竞争）**，B1 降为过渡形态。依据人工给定的「既精准又省 token」原则：B1 只满足省 token，精准不足 | 高 |
| 6 | **v1.1.0 范围修正**：R-395 由单条需求调整为**四段实施链的第二批**，前置零 R-397（双路径收敛）、第一批 R-396（会话轴）+ R-398（三路回写接线）、第三批（回写质量与反馈）；R-395 依赖 R-396 完成 | 高 |
| 7 | 工作量（v1.1.0 重估）：前置零 3~4、第一批 6~8、第二批 8~9、第三批 4~6，合计 **21~26 人天**（估算值，非承诺） | 中 |
| 8 | 五项待决策参数中，**仅「分段 token 配额」是 R-395 的硬依赖**；其余四项对实现路径影响有限。其中「回写粒度」经复核**不受预算裁剪影响**（回写 payload 为 query + response，非组装后 Prompt） | 高（代码复核） |
| 9 | 勘察累计发现 **10 项既有缺陷/隐患**（F-01~F-10）。新增的 **F-09**（三路回写未接线）与 **F-08**（回写幂等键）均为 **P1**：前端全部走流式而流式路径零回写，**记忆、知识库、画像三者当前全不更新** | 高（逐行复核） |

**总体结论：R-395 技术上可行，但需求描述需修正——应从「接入 `ContextManager`」改为「新增片段级预算裁剪能力并双路径接入」；方案取 B2 而非 B1；实施位置为四段链的第二批，依赖 R-397 与 R-396/R-398 先行。建议先就「分段 token 配额」拍板，同时把 F-02 纳入同批修正范围；回写侧缺口（F-09、F-08）同为 P1，须与预算裁剪同批推进。**

---

## 3. 现状实测

### 3.1 待裁剪对象的真实形态（关键）

| 环节 | 实测事实 | 来源 |
|------|----------|------|
| 记忆上下文产生 | `OpenMemoryAdapter.search(...)` 返回 **dict**，条目含 `content` 与 **`score`**（按 score 降序 top_k 截断） | `adapters/openmemory.py` |
| 知识库上下文产生 | `OpenRAGAdapter.search(...)` 返回 **dict**（`{"results": [...]}`），条目含 `content` 与 **`score`**；内置回退路径返回 `list[dict]` | `adapters/openrag.py` |
| 格式化为 Prompt 片段 | `PromptAssembler.format_context(name, data)` → **纯字符串** `"1. {content}\n2. {content}"`。**`score` 与 `metadata` 在此步被丢弃**（`_format_list` 只取 `content/text/chunk/name`） | `assembler.py:78-129` |
| 片段落位 | `contexts["memory_ctx"]` / `contexts["rag_ctx"]`（仅非空时写入） | `executor.py:233-265` |
| 组装 | `assembler.render(system_prompt, memory_ctx, rag_ctx, profile_ctx, query)` → 单一字符串，模板顺序为 System + 画像 + 记忆 + 知识库 + 问题 | `executor.py:137-143`；`assembler.py:19-25` |
| 进入 LLM | `_build_gateway_request(model_code, query=prompt, ...)` → **`messages=[Message(role=USER, content=prompt)]`**，即整段 Prompt 成为**唯一一条 user 消息** | **逐行复核** `openllm_gateway.py:1122-1133` |
| `system_prompt` 实参 | 网关全链路恒传空字符串（两处 `render` 调用均传 `""`），模板中的 system 段当前不会渲染出内容 | `executor.py:137-143`、`openllm_gateway.py:1993-1999` |

**结论：待裁剪对象是「4~5 个文本片段拼成的单一字符串」，而非「消息数组」；且片段内的条目仍保持检索时的排序（编号列表尾部即低分条目）。**

### 3.2 `ContextManager` 现有能力与边界

| 能力 | 签名 / 事实 | 对 R-395 的可用性 |
|------|-------------|-------------------|
| 文本计数 | `count_tokens(text, model_name="default") -> int`（tiktoken，编码器由硬编码表决定） | **可直接复用** |
| 消息计数 | `count_messages_tokens(messages, model_name="default") -> int`（每条 +4，末尾 +2） | 可用，但口径为消息级 |
| 窗口上限 | `get_model_context_limit(model_name) -> int`（硬编码 `MODEL_CONTEXT_LIMITS`，33 个模型 + `default=128000`） | **可复用，但存在 F-02 缺陷** |
| 消息级裁剪 | `prune_context(messages, max_tokens, strategy="preserve_system", model="default", preserve_recent_n=4)`；6 种策略：`recent` / `head_tail` / `system_priority` / `preserve_system`（默认）/ `preserve_recent_n` / `summarize_old` | **粒度不匹配，不可直接用于本链路** |
| 编排入口 | `async manage_context(messages, model, max_tokens=None, strategy="preserve_system", preserve_recent_n=4, summarize_threshold=0.7) -> (messages, management_info)` | 同上；且 `summarize_threshold` 为死参数（未参与任何逻辑） |
| 会话统计 | `get_context_stats(conversation_id) -> dict` | 与 R-395 无关 |

**现有能力的三处结构缺口（实测）：**

1. **无片段/字符串级裁剪契约**：所有入口类型注解均为 `List[Dict[str, Any]]` 或 `List[ConversationMessage]`，不存在接受 `List[str]` / 片段对象 + `budget_tokens` 的方法；也不存在「encode → 截断 → decode」式文本裁剪（`count_tokens` 只测量不修改）。
2. **无「预算」概念**：全仓 `budget_tokens|token_budget|reserved_tokens` 零命中；`get_model_context_limit()` 只返回裸整数，**未预留输出 token、无安全余量系数**。
3. **无丢弃回执**：`manage_context` 以 `len(messages) - len(pruned_messages)` **推算** `pruned_count`，不返回被丢弃的内容、ID 或原因（无法用于可观测）。

**另有两点已知脆弱性（影响是否复用现有方法）：** ① `manage_context` 裁剪后**不做二次校验、不重试**，无法保证 `final_tokens <= model_limit`；② `_prune_recent` 在末条即超限时会返回**空列表**；③ 构造参数 `max_context_tokens=128000` 存而不用（死参数）。

### 3.3 编排链路数据流（同步 `/openllm/v1/chat`）

| 步骤 | 函数 | 关键事实 |
|:----:|------|----------|
| 1 | `openllm_chat` | 身份校验（`identity is None → 1001`）；`request_id = openllm-{uuid24}` |
| 2 | `_normalize_request` | 归一为 `(mode, pipeline, query, output_mode)`；explicit 走 `_validate_pipeline`（4001~4005），auto 走 `_auto_pipeline` |
| 3 | `_route_model_auto` | 网关级预路由（5 因子：成本权重 0.4 / 时延权重 0.3 / 能力 `chat`），写回 `comp["model"]` 与 `fallback_model` |
| 4 | `_get_semantic_cache` | 语义缓存命中则直接返回（不执行编排） |
| 5 | `_build_profile_ctx` | 取用户画像 → `profile_ctx: str \| None` |
| 6 | `_build_writeback_callback` | 构造 memory/rag 回写回调（`kwargs = {user_id, session_id}`） |
| 7 | `_run_orchestrated_chat` | `explicit/openai` → `ExplicitOrchestrator.run`；`auto` → `AutoOrchestrator.run`（`ComponentRouter` 决策 + A/B/C/D 路径） |
| 8 | `PipelineExecutor.execute` | 组件调度（默认 `enable_parallel=False` 串行）；`_run_component` 内 `format_context` → `contexts["*_ctx"]` |
| 9 | **`assembler.render(...)`** | **本需求的候选插入点 A**（`executor.py:137-143`），此处 memory/rag 上下文均已就绪 |
| 10 | `llm_handler` → `_call_llm` → `_call_llm_once` | `check_quota(quota_type="token_input", amount=1000, ...)`（**固定常量 1000**，非实际 token） |
| 11 | `_build_gateway_request` | **整段 Prompt 作为唯一 user 消息** |
| 12 | 回写触发 | LLM 成功后异步（`_schedule_writeback` + 指数退避 ≤3 次），**不阻塞主链路** |

**token 计量现状：整条编排链路无任何 token 计量或预算判断。** `orchestration/` 目录内对 `token|budget|max_tokens|context_window|truncat` 的匹配仅命中 `evaluate.py` 的响应长度判定（`MIN_RESPONSE_LENGTH = 2`），与 token 无关；`openllm_gateway.py` 与 `orchestration/` **均未 import `context_manager`**。

### 3.4 流式路径实测：独立实现、绕过编排层

| 维度 | 同步 `/chat` | 流式 `/chat/stream` |
|------|--------------|---------------------|
| 组件执行 | 经 `PipelineExecutor` | **绕过编排层**，`_run_stream_components` 直接调 adapter 并自行 `format_context` |
| Prompt 组装 | `executor.py:137-143` | **`openllm_gateway.py:1993-1999` 另起一处**（逐行复核确认） |
| 模型 `"auto"` | 5 因子路由 + fallback 重试 | 仅 `_resolve_model_code` → `settings.DEFAULT_LLM_MODEL`（**无 5 因子、无 fallback**） |
| `mode="auto"` | 经 `ComponentRouter` 决策 | 仅 `_auto_pipeline`（**无组件路由决策**） |
| 记忆/知识库回写 | 有 | **无** |
| 语义缓存 | 读 + 写 | **无** |
| 画像上下文时机 | 编排前 | 组件执行**之后**才获取 |

**结论：预算裁剪若只接入同步路径，流式路径仍会超窗；若两处各自实现，将形成第三处实现分叉。建议抽取公共「预算 + 组装」步骤供两路径共用。**

---

## 4. 关键判断：为什么「直接接入」不可行

| 判断 | 依据 | 后果 |
|------|------|------|
| **粒度错配** | 待裁剪对象是片段拼接字符串；`ContextManager` 只处理消息列表 | 调用后不会发生裁剪 |
| **单条消息结构** | 整段 Prompt 成为唯一 user 消息（已逐行复核） | 无法通过「删消息」达成降预算；换 `recent` 策略且有超限时返回空列表 |
| **双路径分叉** | 流式路径为独立实现（已逐行复核） | 单点接入必然覆盖不全 |
| **无预算概念** | 无输出预留、无余量系数、无丢弃回执 | 即使能裁，也无法安全地裁（可能把输出空间挤没） |

**因此 R-395 的需求描述应修正为：新增「片段级预算裁剪」能力（含输出预留与余量）→ 抽取公共组装步骤 → 在同步与流式两条路径接入 → 输出可观测回执。**

---

## 5. 方案比选

### 5.1 方案 A：复用现有消息级 `manage_context`（不采纳）

把组装好的 Prompt 包成 `[{"role": "user", "content": prompt}]` 后调用 `manage_context`。

不采纳理由：① 单条消息场景下默认策略不裁剪，等于无效；② 换 `recent` 策略有返回空列表的风险；③ 即便裁成，也是「整条保/整条丢」，无法保留高价值片段；④ 无输出预留与回执，仍不满足可观测要求。

### 5.2 方案 B1：片段级预算裁剪 + 按条目尾截断（**推荐，最小可用**）

| 要素 | 设计要点 |
|------|----------|
| 新增能力 | 片段级预算裁剪：输入片段集合（名称 / 文本 / 优先级）+ 模型名 + 预留输出 token + 安全系数；输出「保留片段 + 丢弃清单 + 前后 token 数 + 是否发生硬截断」 |
| 预算公式 | `budget = (get_model_context_limit(model) - reserved_output_tokens) × safety_ratio`（建议 `safety_ratio` 可配，初值按余量 10%~15% 取值，具体值待人工确认） |
| 裁剪顺序 | **必须保留** `query`；`system` 为空当前可忽略；其余按优先级（建议 profile → memory → rag）在超出预算时从**条目标题尾部**逐条丢弃（利用「编号列表尾部即低分条目」这一实测特性，近似实现低分优先丢弃） |
| 切分粒度 | **按条目切分而非按字符切分**，避免把编号列表切断在中途；单条即超预算时按该条做文本级截断并标记 `hard_truncated` |
| 二次校验 | 裁剪后重新计数，仍超预算则显式降级（不得静默放行） |
| 接入点 | 同步：`executor.py:137-143` 之前；流式：`openllm_gateway.py:1993` 之前。**建议两处共用同一函数** |
| 可观测 | 在 `routing_trace` 增补预算回执：`{model, window, reserved, budget, original_tokens, final_tokens, dropped, truncated}` |

### 5.3 方案 B2：方案 B1 + 分段配额制（若采纳「分段 token 配额」参数）

在 B1 之上为每个片段设定占比配额（如 System / 画像 / 记忆 / 知识库 / 问题），各片段先按自身配额裁剪再合并；相邻片段可借余额。工作量与调参成本高于 B1，但可控性最好。

### 5.4 方案 C：在适配器层前置裁剪（不采纳）

在 `OpenMemoryAdapter` / `OpenRAGAdapter` 内按 token 预算裁剪检索结果。

不采纳理由：① 适配器不掌握最终模型与输出预留（模型在编排后段才确定），无法算出正确预算；② 会把预算策略散落到每个适配器，形成多处重复；③ 破坏适配器的单一职责。

### 5.5 比选汇总

| 方案 | 结论 | 一句话理由 | 估算工作量 |
|------|:----:|------------|:----------:|
| A 复用消息级裁剪 | 不采纳 | 粒度错配，实测无法生效且有空列表风险 | — |
| **B1 片段级 + 尾截断** | **推荐** | 匹配真实形态，改动面小，两路径可共用 | ≈6 人天 |
| B2 配额制 | 备选 | 可控性最好，依赖「分段配额」参数拍板 | ≈8~9 人天 |
| C 适配器层裁剪 | 不采纳 | 预算信息在适配器层不可得，职责分散 | — |

> 说明：若同时收敛流式与同步双路径实现（推荐但不属 R-395 必需），追加约 3~4 人天。

---

## 6. 五项待决策参数的影响分析

| 序号 | 参数 | 候选取值 | 对 R-395 实现的影响 | 硬依赖 |
|:----:|------|----------|---------------------|:------:|
| 1 | 触发模式 | auto（现默认）/ explicit 强制 / 混合 | auto 下组件组合随 A/B/C/D 路径变化，预算须**动态**分配；explicit 下组件与参数由调用方给定，预算可更**确定**。影响裁剪算法是动态还是静态配置 | 否 |
| 2 | 单次调用延迟预算 | 未定 | 现状 `enable_parallel` 默认 **False**（memory + rag 串行），双路检索时延线性叠加。若定紧延迟预算则须开并行；并行不影响预算计算（先聚合后裁剪），仅影响超时降级口径 | 否 |
| 3 | 回写粒度与幂等键 | 现为 `session_id + seq + target` | **经复核不受影响**：回写 payload 由 `query` 与模型 `response` 组成，**不是**组装后 Prompt；裁剪发生在检索之后、调用之前，不回改检索结果 | 否 |
| 4 | scope 命名口径 | 未定 | 与 R-387 跨域租户码语义相邻；对 R-395 无直接影响（`user_id` / `kb_id` 均为显式参数） | 否 |
| 5 | **分段 token 配额** | 未定 | **直接决定算法形态**：定配额 → 走 B2（配额制）；不定配额 → 走 B1（优先级 + 尾截断）。此项未拍板则无法确定实现方案 | **是** |

**结论：仅第 5 项构成硬依赖。** 建议：若暂不打算细调配额，直接按 B1 路线推进；若计划做配额治理，则先定配额再实施，避免二次返工。

---

## 7. 顺带发现（实测，需单独登记）

| ID | 发现 | 等级 | 实测依据 | 对 R-395 的影响 | 建议 |
|----|------|:----:|----------|-----------------|------|
| **F-01** | **流式路径绕过编排层**：`_run_stream_components` 不经 `PipelineExecutor`；流式无记忆/知识库回写、无语义缓存；`model="auto"` 不走 5 因子路由与 fallback；`mode="auto"` 不经 `ComponentRouter` 决策 | **P2** | 逐行复核 `openllm_gateway.py:1985-2005` 与流式端点实现 | **直接放大 R-395 范围**：预算裁剪必须双路径接入，否则流式仍超窗 | 建议登记新候选（跨仓），并与 R-395 同批评估 |
| **F-02** | **`MODEL_CONTEXT_LIMITS` 前缀匹配缺陷**：`gpt-4` 是表中**首个键**（`context_manager.py:45`），匹配算法在精确匹配失败后**按插入顺序**做 `startswith`（`:176-178`、`:198-200`）。因此日期化模型名 `gpt-4o-2024-08-06`、`gpt-4-turbo-2024-04-09`、`gpt-4-32k-0314` 均会**先命中 `gpt-4`**，返回 **8192 / cl100k_base**（应为 128000 / `o200k_base` 或 32768） | **P2** | 逐行复核（`MODEL_CONTEXT_LIMITS` 表 + 两个匹配函数） | **直接削弱预算准确性**：窗口被低估 15.6 倍时，上下文会被过度裁剪，高价值片段被无谓丢弃；编码器选错还会导致计数偏差 | 建议与 R-395 **同批修正**（改为最长键优先匹配或显式别名表），并补日期化模型名用例 |
| **F-03** | `check_quota(quota_type="token_input", amount=1000, ...)` 使用**固定常量 1000**，与 Prompt 实际 token 无关 | P3 | `openllm_gateway.py:1156-1164`、`:1249-1257` | 不阻塞 R-395；但预算能力就绪后可顺带改为实际 token | 可选随批优化 |
| **F-04** | 死参数 / 语义不符：`ContextManager.max_context_tokens`（构造参数，全文未读）；`manage_context.summarize_threshold`（未参与逻辑）；`get_context_stats.estimated_context_window` 实为 `total_tokens` 的复制值 | P3 | `context_manager.py:92`、`:214`、`:851` | 增加 R-395 阅读成本，易误判预算来源 | 建议随批清理 |
| **F-05** | `system_prompt` 在网关全链路**恒为空字符串**（两处 `render` 均传 `""`），模板 system 段永不渲染 | P3（信息性） | `executor.py:137-143`、`openllm_gateway.py:1993-1999` | 预算分配可暂不预留 system 段，简化 B1 | 记录不修 |
| **F-06** | `manage_context` 裁剪后**不二次校验、不重试**；`_prune_recent` 末条超限时返回**空列表**；`summarize_old` 的摘要切片按长度推断「被丢弃的旧消息」，与 `_prune_preserve_system` 的非连续输出语义不符 | P2 | `context_manager.py:249-273`、`:311-330`、`:268`、`:472-480` | 若复用现有方法做预算，需先补二次校验 | 建议 R-395 实现时**不复用**这些方法，另建能力 |

> **F-06 与本需求的直接关系：B1 方案明确不复用现有 `prune_*` / `manage_context`，仅复用 `count_tokens` 与 `get_model_context_limit`（后者需先修 F-02）。**

**v1.1.0 新增发现（回写侧，均为 P1）：**

| ID | 发现 | 等级 | 实测依据 | 对 R-395 的影响 | 建议 |
|----|------|:----:|----------|-----------------|------|
| **F-09** | **三路回写未接线**：回写能力齐全（memory/rag/profile + 幂等 + 退避 + 落盘 + 启动恢复），但运行中的调用链一条都未接 —— ① 流式端点未构造回写回调且 `_run_stream_components` 不接收回写参数；② `_build_writeback_callback` 仅返回 memory 与 rag 两个回调，profile 仅存在于独立 API；③ `POST /openllm/v1/writeback` 在 OpenBase 前端与网关均无调用点 | **P1** | 前端会话页与 Playground 全部走流式（`Conversations.vue:246`、`Playground.vue:117`），非流式 `sendChat` 无调用点；`_build_writeback_callback` 返回两个回调；调用点检索覆盖前端与网关 | 回写是编排的对偶面：只检索不更新，记忆不增长、知识库不沉淀、画像不演化，「精准」随时间下降，且缺「哪些片段被使用」的反馈使配额与竞争失去依据 | 登记候选需求池 **R-398** + 技术债务总表（**TD-新增-022**）；纳入四段链第一批 |
| **F-10** | **写入质量开关失效**：`save_if_valuable` 默认 `True` 并透传进队列 payload，但执行侧 `_rag_writeback` 从未读取；同一语义只在 `orchestration/evaluate.py:139` 有实现 | P2 | `writeback.py:53`、`:396` 与 `_rag_writeback` 实现比对 | 走该 API 时每轮模型回复原样入知识库，形成自引用污染，长期降低检索可信度，反向削弱预算裁剪的选择质量 | 随 R-398 修正；间隔期内建议先关闭 `rag` 路回写 |

---

## 8. 工作量与测试策略

### 8.1 工作量估算（人天，估算值）

| 工作项 | B1 | B2 | 备注 |
|--------|:--:|:--:|------|
| 新增片段级预算裁剪能力（含输出预留、余量、丢弃回执） | 1.5 | 2.5 | 复用 `count_tokens` 与编码器缓存 |
| 抽取公共「预算 + 组装」步骤并接入同步路径 | 0.5 | 0.5 | `executor.py` |
| 接入流式路径 | 0.5 | 0.5 | `openllm_gateway.py` |
| 预算参数与默认值（预留输出、余量系数、优先级） | 0.5 | 1.0 | 含配置读取 |
| `routing_trace` 预算回执与日志 | 0.5 | 0.5 | 可观测 |
| 单测（含边界用例） | 1.5 | 2.0 | 见 8.2 |
| 集成与双路径一致性用例 | 1.0 | 1.0 | 见 8.2 |
| 联调与文档 | 0.5 | 0.5 | |
| **合计** | **≈6** | **≈8~9** | 均为估算值，非承诺 |
| （可选）收敛双路径实现 | +3~4 | +3~4 | 建议但非 R-395 必需 |

**不含**：F-02 修正（建议同批，约 +0.5~1 人天）、F-01 双路径收敛。

### 8.2 测试策略（要点）

| 层级 | 用例要点 |
|------|----------|
| 单测 | 正常裁剪；**单片段即超预算**（触发文本级硬截断）；空上下文（无 memory/无 rag）；超长 query（唯一必须保留项本身超预算时的显式降级）；**日期化模型名**（`gpt-4o-2024-08-06` → 须得 128000 而非 8192，回归 F-02）；预算恰好等于片段总和（边界不裁） |
| 集成 | 同一输入分别打 `/openllm/v1/chat` 与 `/chat/stream`，断言两路径 prompt token **均 ≤ 预算**且丢弃清单一致（防止第三处实现分叉） |
| 回归 | 本仓无代码变更，既有 4 仓回归基线不受影响；OpenLLM 侧须补其自身回归 |
| 证据 | 裁剪前后 token 数、丢弃片段清单及原因、`routing_trace` 预算回执快照 |

---

## 9. 风险与约束

| ID | 类型 | 内容 | 等级 | 应对 |
|----|------|------|:----:|------|
| RSK-01 | 范围 | 流式路径为独立实现，单点接入覆盖不全（F-01） | 高 | 双路径同批接入；优先抽取公共步骤 |
| RSK-02 | 准确性 | `MODEL_CONTEXT_LIMITS` 前缀匹配缺陷使窗口被低估（F-02），预算过紧导致过度裁剪 | 高 | 与 R-395 同批修正；补日期化模型名用例 |
| RSK-03 | 实现 | 若复用现有 `manage_context` / `prune_*`，存在不二次校验与返回空列表风险（F-06） | 中高 | B1 明确不复用，仅复用计数与窗口查询 |
| RSK-04 | 切分 | 按字符截断会破坏编号列表结构，导致 Prompt 语义破损 | 中 | 按条目切分；单条超限才做文本级截断并显式标记 |
| RSK-05 | 排期 | 落点在 OpenLLM 仓，受跨仓立项与排期制约 | 中 | 走跨仓派单；本仓不代改（`VC-014`） |
| RSK-06 | 观测 | 裁剪静默发生，排障时无法判断上下文为何变短 | 中 | 强制预算回执入 `routing_trace`；无回执视为未完成 |
| ASM-01 | 假设 | 适配器返回结果按 score 降序，「编号列表尾部 = 低分条目」，尾截断可近似低分优先丢弃 | — | 若某适配器不保证排序，需改为结构化片段入参（升级 B2） |
| ASM-02 | 假设 | `get_model_context_limit` 可代表所选模型的真实窗口（F-02 修正后成立） | — | 依赖 F-02 |
| CON-01 | 约束 | 本仓不得修改其他仓代码（`VC-014`） | — | 跨仓派单 |
| CON-02 | 约束 | 实施须先经 Step 0 版本规划纳入版本 | — | 本报告仅评估，不构成排期承诺 |

---

## 10. 结论与建议动作

1. **需求描述修正（已同步回写候选需求池 §1.18 R-395 文字口径，2026-09-21）**：由「接入 `ContextManager`」改为「**新增片段级预算裁剪能力并同步/流式双路径接入，含输出预留与可观测回执**」。
2. **方案选择（v1.1.0 修正）**：推荐 **B2**（结构化片段 + 配额保底 + 相关性竞争），B1（按条目尾截断）降为过渡形态。依据人工给定的「既精准又省 token」原则，B1 只满足省 token。
3. **范围位置（v1.1.0 新增）**：R-395 为**四段实施链的第二批**，前置零 R-397（双路径收敛）、第一批 R-396（会话轴）+ R-398（三路回写接线）、第三批（回写质量与反馈）；依赖关系与站位理由见《OpenBase-会话上下文编排统一方案-v1.0.0》v1.1.0 §5.2。
4. **硬依赖**：仅「分段 token 配额」需先拍板；其余四项参数不阻塞。
5. **同批修正建议**：**F-02**（前缀匹配缺陷）与 **F-06**（不复用现有裁剪方法）随 R-395 一并纳入范围；**F-01** 已登记为 R-397 并前置；**F-09**（三路回写未接线，P1）已登记为 R-398，与 R-395 依赖同一会话标识。
6. **前置动作**：由 OpenLLM 仓立项或走跨仓派单；本仓仅保留评估与登记职责。
7. **本报告不修改任何代码**；对既有文档的交叉引用由各文档自身升版维护（候选需求池 v0.30.0、技术债务总表 v0.5.5、统一方案 v1.1.0）。

---

## 11. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|------|----------|
| v1.0.0 | 2026-09-21 | AU-OpenBase-Dev | 初始创建。范围：R-395 可行性、方案比选与工作量评估。核心结论：R-395 为「新建片段级能力」而非「接线」，粒度错配（消息级 vs 片段级）与双路径分叉（流式绕过编排层）为两项决定性事实；推荐方案 B1（≈6 人天，估算值），B2 备选；五项待决策参数中仅「分段 token 配额」构成硬依赖，且回写粒度经复核不受预算裁剪影响。附既有缺陷发现 6 项（F-01~F-06），其中 F-02（`MODEL_CONTEXT_LIMITS` 前缀匹配致窗口低估 15.6 倍）与 F-06（现有裁剪方法不二次校验、可返回空列表）建议与 R-395 同批修正。关键事实（`MODEL_CONTEXT_LIMITS` 表与匹配算法、组装结果作为唯一 user 消息、流式路径 Prompt 组装点）均经逐行复核，非二手转述。 |
| v1.1.0 | 2026-09-21 | AU-OpenBase-Dev | **回写侧纳入范围与方案口径修正**（依据人工给定的「既精准又省 token」原则与「每次会话仍需回写更新记忆/知识库/画像」的核实结论）。§2 结论表修正第 4 条（B1 标注为已被第 5 条替代）、新增第 5~9 条（方案上调为 B2、范围调整为四段链第二批、工作量重估 21~26 人天、累计发现 10 项）；§7 新增回写侧发现 **F-09**（三路回写未接线，**P1**）与 **F-10**（`save_if_valuable` 空开关，P2）；§10 建议动作由 6 条扩为 7 条并注明已同步回写的下游文档版本。核实事实：前端全部走流式（`Conversations.vue:246`、`Playground.vue:117`）、非流式 `sendChat` 无调用点、流式端点未构造回写回调、`_build_writeback_callback` 仅返回 memory 与 rag、`/openllm/v1/writeback` 在 OpenBase 前端与网关均无调用点、`save_if_valuable` 在执行侧从未被读取。**未改变 §3~§6、§8、§9 既有结论。** |

# OpenBase 智能体会话上下文编排评估报告 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 评估主题 | 智能体会话上下文编排：网关 ↔ OpenLLM 编排归属与 LiteLLM 选型 |
| 文档版本 | v1.1.0 |
| 状态 | [Review] |
| 作者 | AU-OpenBase-Dev（审计师视图，独立于设计与开发视图） |
| 评估日期 | 2026-09-20 |
| 存放 | doc/audit/assessment/ |
| 关联版本 | v1.4.7（已发布，commit `a835132`）/ v1.4.8+（候选承接） |
| 评估起因 | 用户提问：「如何让智能体会话通过网关进入 OpenLLM 后，可以自动处理 memory（OpenMemory）和知识库（OpenRAG）以及上下文发送给合适的 LLM？关键问题有哪些、可采用什么技术方案、公开开源方案是否有成熟对应、什么最适合我们」；追加提问：「是落在网关侧还是落在 OpenLLM 侧更合理？为什么不借鉴或者使用 LiteLLM？」 |

---

## 1. 评估范围与方法

| 项 | 内容 |
|----|------|
| 评估对象 | ① 会话上下文编排链路的现有实现边界；② 编排层归属（OpenBase 网关侧 vs OpenLLM 侧）；③ 是否引入 LiteLLM 作为编排/路由框架 |
| 评估方式 | 双侧代码实测勘察（读文件 + 结构化检索）+ 依赖清点 + 既有设计文档口径核对 + 方案比选 |
| 实测动作 | ① 读 `openbase/modules/llm_proxy/__init__.py`，确认网关侧编排能力与上游转发目标；② 读 OpenLLM `backend/app/edgerouter/orchestration/`（`auto.py` / `explicit.py` / `assembler.py` / `component_router.py`）与 `backend/app/api/writeback.py`；③ 检索 OpenLLM 全仓依赖，确认是否已引入 litellm / langchain / vllm / openai SDK；④ 检索 `ContextManager` 在 `backend/app/api` 的引用面，确认编排链路是否接入上下文预算；⑤ 核对《OpenBase-网关服务发现与聚合编排技术方案》与《OpenBase-系统架构设计文档-v1.4.6》的「编排」口径 |
| 纪律 | 不代改需求文档与产品代码；本轮**未改动任何生产代码**；发现项如实登记，含对前期结论的修正 |
| 局限声明 | LiteLLM 能力对照基于其公开特性描述，本轮**未做其代码级核验**，其许可与商用边界亦未复验，均不作为决策的唯一依据；工作量为人天量级**估算值**，非排期承诺 |

---

## 2. 结论摘要

| 序号 | 结论 | 置信度 |
|------|------|:------:|
| 1 | **编排层归属 OpenLLM 侧，且该能力已实现**，不需要在网关侧新建 Context Orchestrator | 高（代码实测） |
| 2 | 网关侧应保持「薄策略层」定位：身份与租户、策略与配额、审计与链路、透传；**不承担 LLM 调用链编排** | 高 |
| 3 | **不引入 LiteLLM 作为框架依赖**；其能力与 OpenLLM 既有实现高度重叠，且我们所缺的（上下文装配）恰是它不提供的 | 高 |
| 4 | 可**借鉴** LiteLLM 的三处语义（pre/post-call 生命周期命名、fallback/cooldown 策略、virtual-key → 预算映射），不建议引入其代码 | 中 |
| 5 | 真正的增量缺口仅 2 项：**编排归属与 DSL 边界定界**、**编排链路接入上下文预算裁剪**；另有 5 个参数待人工决策 | 高 |
| 6 | 若「网关侧新建编排层」被采纳，将出现双编排实现与双路由权威不明，且与 `VC-014` 跨仓边界冲突 | 高 |
| 7 | 本轮调研前一阶段曾判定「在网关侧加薄 Context Orchestrator」，该结论**经代码实测后予以撤回**，根因是「聚合编排」一词在两侧同名不同物（详见 §4.1 与 §8 RSK-02） | 高 |

**总体结论：维持现有归属（编排在 OpenLLM），网关侧不新增编排组件；不引入 LiteLLM；优先处理 §7 两项缺口。**

---

## 3. 现状勘察（实测）

### 3.1 网关侧（OpenBase，实测）

| 勘察项 | 实测结果 | 证据 |
|--------|----------|------|
| 网关 LLM 代理模块构成 | `openbase/modules/llm_proxy/` 下**仅 `__init__.py` 一个文件**，无编排子模块 | 目录列举 |
| 是否存在编排/钩子实现 | 模块内**无**编排逻辑、无 pre/post-call 钩子、无组件路由 | 结构化检索（`def chat` / `orchestrat` / `hook` / `pre_call` / `post_call`）零命中 |
| 上游转发目标 | 转发 OpenLLM 编排入口：`/openllm/v1/models`、`/openllm/v1/chat`、`/openllm/v1/chat/stream`、`/openllm/v1/health`、`/openllm/v1/conversations/*` | 模块内路由定义 |
| 身份传递 | `_build_upstream_headers` 经 `build_outbound_headers(..., TARGET_SYSTEM_LLM)` 组装 `X-User-ID / X-Tenant-ID / X-Org-ID / X-User-Role`，并改写 `X-Proxy-Source=openbase-llm-proxy` | 模块内实现 |
| 传输行为 | `/chat/stream` 按 SSE 逐事件转发（`event: routing` → `chunk×N` → `done`），**不做组装** | 模块文档字符串与转发实现 |

**小结：网关侧已是「身份 + 透传」形态，本身就是薄层；它不是待补齐的编排层，而是编排链路的入口。**

### 3.2 OpenLLM 侧（实测）

| 能力 | 实现位置 | 已实现职责 |
|------|----------|------------|
| 组件路由器 | `backend/app/edgerouter/orchestration/component_router.py` | R001~R005 规则引擎；置信度阈值 0.85 优先匹配；置信度不足走轻量 LLM 兜底分类；兜底失败回落规则引擎；规则集 YAML/JSON 热更新 |
| auto 编排器 | `backend/app/edgerouter/orchestration/auto.py` | 决策映射 4 路径：A（memory）/ B（rag）/ C（memory+rag）/ D（空）；含 `enable_memory` 覆盖与 `enable_llm` 开关 |
| explicit 编排器 | `backend/app/edgerouter/orchestration/explicit.py` | pipeline 结构校验（错误码 4001~4005）；`llm` 组件必须在末尾；memory 必填 `user_id`、rag 必填 `kb_id`；输出模式与 llm 存在性一致性校验 |
| Prompt 组装器 | `backend/app/edgerouter/orchestration/assembler.py` | Jinja2 严格顺序：System Prompt + 画像 + 记忆上下文 + 知识库上下文 + 用户问题；未调用组件不注入 |
| 管道执行器 | `backend/app/edgerouter/orchestration/executor.py` | 按 pipeline 顺序调度组件 handler，支持并行开关与画像上下文透传 |
| 三路回写 | `backend/app/api/writeback.py` | `POST /openllm/v1/writeback`：memory / rag / profile 三路，异步默认 + 同步可选；幂等键 `session_id + seq + target`（重复投递返回 `duplicated=true`）；异步队列指数退避 ≤3 次不阻塞主流程；字段先行校验（白名单 `VALID_TARGETS`） |
| 编排入口与流式 | `backend/app/api/openllm_gateway.py` | `POST /chat`、`POST /chat/stream`、`GET /rag/collections`、`POST /rag/ingest`、`GET /models`、`GET /trace/{request_id}`、`GET /health`；含 `_run_orchestrated_chat`、`_run_stream_components`、`_build_writeback_callback`、`_route_model_auto`、语义缓存、trace 落库 |
| 模型路由与预算 | `backend/app/api/budgets.py` + `edgerouter/core/{router,strategy,registry}.py` | `BudgetScope` / `BudgetPeriod` / USD 上限 / `is_exceeded` / `usage_percentage`；`RouteEngine` 提供 `parse_request` / `inject_context` / `route` |
| 隔离与鉴权 | `backend/app/edgerouter/{isolator.py,auth/,middleware/}` | org namespace 隔离、JWT/API Key 双通道（`get_gateway_identity`）、RBAC、配额与审计中间件 |
| 组件适配器 | `backend/app/edgerouter/adapters/` | openllm、openmemory、openrag、profile、dps_client、hermes_agent |
| 上下文计量 | `backend/app/services/context_manager.py` | `count_tokens` / `count_messages_tokens` / `manage_context` / `get_context_stats` / `get_model_context_limit` |

**小结：用户所问的「自动处理 memory + 知识库 + 上下文并分发至合适 LLM」，其四要素（组件路由、上下文装配、模型选择、结果回写）在 OpenLLM 侧**均已实现**；链路本身是通的。**

### 3.3 依赖实测（关键否定证据）

| 勘察项 | 实测结果 |
|--------|----------|
| OpenLLM 是否依赖 litellm | **否**（全仓检索零命中） |
| OpenLLM 是否依赖 langchain / vllm / openai SDK | **否**（全仓检索零命中） |
| OpenLLM 实际声明的 HTTP 依赖 | 仅 `requests`（`backend/tests/locust/requirements.txt`、`edgerouter-sdk/pyproject.toml`） |

**小结：OpenLLM 是**自建**的 LLM 网关，不是任何现有网关框架的封装层。这一点直接决定 §5 的选型结论。**

---

## 4. 方案比选

### 4.1 方案 A：网关侧新建薄 Context Orchestrator（不采纳，含结论修正）

| 维度 | 评估 |
|------|------|
| 主张 | 在 OpenBase 网关的 `llm_proxy` 内新增上下文编排层，由网关负责调用 OpenMemory / OpenRAG / 画像并组装 Prompt |
| 不采纳理由 | ① **与 OpenLLM 既有编排重复**，形成两套编排实现；② 网关热路径新增 3 个跨服务依赖（memory / rag / profile），放大故障面；③ SSE 从直通变为两跳组装，流式语义复杂化；④ `llm_proxy` 当前无任何编排代码，等于从零构建，而 OpenLLM 侧约 6 个编排模块已实现且有测试覆盖；⑤ 模型/上下文语义每次调整都要发一次网关版本 |
| **结论修正声明** | 本轮调研早期曾输出「方案 A：网关侧薄 Context Orchestrator」建议。该建议的产生原因是**只勘察了网关侧 `llm_proxy`（确为纯透传），未读 OpenLLM 的 `edgerouter/orchestration`**，因而误判编排能力缺位。经 §3.2 代码实测后**撤回该建议**。 |
| 根因 | 「聚合编排」一词在两侧同名不同物：网关侧指**业务数据 BFF 跨系统一次取数（G3）**，OpenLLM 侧指**LLM 调用链上下文装配**。详见 §6 与 RSK-02 |

### 4.2 方案 B：复用并扩展 OpenLLM 既有编排（采纳）

| 维度 | 评估 |
|------|------|
| 主张 | 编排层保持 OpenLLM 归属；网关继续只做身份与策略；增量工作收敛为「补预算裁剪 + 定边界口径」 |
| 采纳理由 | ① 编排引擎、组件适配器、回写队列、预算与上下文计量均已在位且可复用；② 身份虽由网关签发，但 OpenLLM 侧已有 `RequestContext` + `isolator` 承接隔离，无需迁移职责；③ 变更面最小，不触碰四仓边界争议；④ 网关保持薄层，符合《系统架构设计文档-v1.4.6》将 `gateway` 归入平台「可观测与审计」域的既有定位 |

### 4.3 方案 C：引入 LiteLLM 作为编排/路由框架（不采纳）

详见 §5。

### 4.4 方案 D：LiteLLM 作为 OpenLLM 的 upstream adapter（条件性保留）

| 维度 | 评估 |
|------|------|
| 主张 | 不引入为框架，仅在特定条件下把 LiteLLM proxy 注册为 OpenLLM 的一个 upstream provider |
| 触发条件 | 需要接入**大量外部供应商（百级）**且现有 `edgerouter/core/registry.py` 覆盖不足时 |
| 性质 | 「引入但不接管编排」：LiteLLM 只作为模型出口之一，编排、身份、隔离、审计仍在 OpenLLM 侧 |
| 当前处置 | **不建独立需求 ID**，作为边界条款随 R-394 表述；无实际需求时不做评估 |

### 4.5 比选汇总

| 方案 | 落点 | 结论 | 一句话理由 |
|------|------|:----:|------------|
| A 网关侧新建编排 | OpenBase 网关 | **不采纳** | 与既有编排重复，且网关侧从零构建、依赖面放大 |
| B 复用扩展 OpenLLM 编排 | OpenLLM | **采纳** | 能力已在位，增量最小，不触跨仓边界 |
| C 引入 LiteLLM 框架 | OpenLLM（替换） | **不采纳** | 能力高度重叠 + 契约不匹配 + 缺的它不给 |
| D LiteLLM 作为 upstream | OpenLLM 之下 | **条件性保留** | 仅在百级供应商 fan-out 时评估 |

---

## 5. LiteLLM 能力对照与不采纳理由

> 说明：下表「LiteLLM 能力」列基于其公开特性描述（本轮未做代码级核验）；「OpenLLM 对位」列为 §3.2 实测结果。

| LiteLLM 能力 | OpenLLM 对位实现 | 是否缺失 |
|---|---|:---:|
| 多供应商 / provider 抽象 | `edgerouter/adapters/` + `core/registry.py` | 不缺 |
| 模型路由与回退策略 | `core/router.py`（`RouteEngine`）+ `core/strategy.py` + `_route_model_auto` | 不缺 |
| 成本预算与虚拟密钥 | `api/budgets.py`（scope / period / USD 上限 / `is_exceeded`） | 不缺 |
| 限流与配额 | `edgerouter/middleware/quota.py` | 不缺 |
| 审计与用量记录 | `edgerouter/middleware/audit.py` + `edgerouter/metrics/collector.py` | 不缺 |
| 鉴权与 RBAC | `edgerouter/auth/`（`edge_auth` / `jwt_handler` / `rbac`） | 不缺 |
| pre/post-call 钩子 | `orchestration/` 四段式（路由 → 组装 → 执行 → 回写） | 不缺 |
| **记忆 / 知识库 / 画像的上下文装配** | `orchestration/auto|explicit` + `assembler.py` + adapters | **LiteLLM 不提供该能力** |

**四条不采纳理由：**

1. **功能重叠导致双路由权威不明。** 两套模型路由与两套预算治理同时存在时，线上异常无法界定责任主体，排障成本高于收益。
2. **与四仓边界和变更控制冲突。** `VC-014` 规定本仓不得修改其他仓代码；引入 LiteLLM 属 OpenLLM 侧编排层重构，须走该仓立项与跨仓派单，成本与风险均高于「补两项缺口」。
3. **身份与隔离契约不匹配。** OpenLLM 的编排建立在四维身份（`X-Tenant-ID` / `X-User-ID` / `X-Org-ID` / `X-User-Role`）、org namespace 隔离（`isolator.py`）与 `request_id` 日志链之上；LiteLLM 无对应概念，接入仍需自写适配器，且会把隔离保证移出中间层。
4. **缺口恰在其能力之外。** 我们缺的是**上下文预算感知裁剪**与**回写治理口径**；LiteLLM 的钩子仅是扩展点，不提供上下文装配实现，引入后仍需自行补齐。

**可借鉴而非引入的三处语义：**

| 借鉴项 | 用途 |
|--------|------|
| `async_pre_call_hook` / `async_post_call_success_hook` 的生命周期命名 | 用于固化编排三段契约（组装前 / 调用中 / 回写后），统一 `_build_writeback_callback` 一类回调的命名口径 |
| fallback 列表 + cooldown + 预算门限 | 用于扩展 `core/strategy.py` 的回退策略（当前较薄） |
| virtual-key → 预算映射 | 用于对接 `api/budgets.py`，形成租户级预算视图 |

**合规提示：** LiteLLM 的许可条款与商用边界本轮**未复验**，若后续进入方案 D 评估，须先完成许可与法务确认，不得以本轮结论直接豁免。

---

## 6. 职责边界定义（建议条款）

| 维度 | OpenBase 网关（策略与身份边界） | OpenLLM（编排与执行） |
|------|--------------------------------|----------------------|
| 身份 | JWT / API Key 校验；四维身份头组装；`X-Proxy-Source` 标记 | 解析为 `RequestContext`；org 隔离与 namespace 前缀 |
| 策略 | 模型白名单、租户预算上限的**策略下发与准入** | 策略**执行**（选模、预算扣减、组件可用性探测） |
| 编排 | **不编排** LLM 调用链 | 组件路由 → Prompt 组装 → 模型路由 → 调用 → 回写 |
| 组件依赖 | 不直连 OpenMemory / OpenRAG / 画像 | 经 adapters 直连上述组件 |
| 传输 | SSE 逐事件透传 | 事件序列 `routing → chunk×N → done` |
| 审计 | `request_id` 贯通、网关侧结构化日志 | `request_id` 落地、`/trace/{request_id}` 查询 |
| 变更归属 | 本仓（OpenBase） | OpenLLM 仓（须跨仓派单） |

**边界条款建议（R-394 拟纳入）：**

1. 「聚合编排」在 OpenBase 文档中**专指**网关侧 BFF 跨系统业务数据取数（G3），**不得**用于描述 LLM 调用链上下文装配。
2. LLM 调用链的上下文装配与组件编排**唯一归属** OpenLLM `edgerouter/orchestration/`，网关侧不得新增同类实现。
3. 网关对模型与组件的控制形式限定为**策略下发与准入**，不体现为调用链编排。
4. 条件性保留项（方案 D）在触发条件成立前不纳入设计，触发条件须经 Step 0 版本规划评估。

---

## 7. 缺口清单

| ID | 缺口 | 严重度 | 实测依据 | 落点 | 建议承接 |
|----|------|:------:|----------|------|----------|
| **G-01** | **编排链路未接入上下文预算裁剪**：`ContextManager` 具备 token 计数与模型窗口上限能力，但编排链路未调用；`PromptAssembler` 为纯 Jinja2 渲染、无截断，双路注入（记忆 + 知识库）存在超窗风险 | 高 | ① 结构化检索显示 `ContextManager` 仅被 `backend/app/api/conversations.py` 与 `backend/app/api/context.py` 引用，编排入口未引用；② `assembler.py` 的 `DEFAULT_TEMPLATE` 与 `render()` 无截断或预算参数 | OpenLLM 仓 | **R-395**（候选） |
| **G-02** | **编排归属与 DSL 边界未定界**：网关侧 BFF 聚合编排 DSL 与 OpenLLM 侧 pipeline DSL 并存，文档口径未明确各自适用范围，已实际导致一次误判 | 中高 | 《OpenBase-网关服务发现与聚合编排技术方案》定义聚合层（BFF 编排执行器 DSL、G3 聚合编排）；OpenLLM `orchestration/explicit.py` 定义 pipeline DSL；两处均用「编排」 | 本仓文档（可协同） | **R-394**（候选） |
| **G-03** | **五项参数未决策**：触发模式、单次调用延迟预算、回写粒度与幂等键、scope 命名口径、分段 token 配额 | 中 | 无既定取值；回写幂等键现为 `session_id + seq + target`（仅现状记录，非最终口径） | 人工决策 | 随 R-395，未单独立项 |

**权威性说明：** G-01 由代码检索与文件阅读直接得出；G-03 为需求侧待决策项，非缺陷。

---

## 8. 风险、假设与约束

| ID | 类型 | 内容 | 等级 | 应对 |
|----|------|------|:----:|------|
| RSK-01 | 技术 | 记忆与知识库双路注入在长上下文场景下超出模型窗口，导致调用失败或静默截断 | 中高 | 由 G-01 / R-395 处理；超窗须有显式降级与可观测口径，禁止静默丢弃 |
| RSK-02 | 过程 | 「编排」同名歧义在设计与评审环节被重复误判（**本轮已实际发生一次并导致结论撤回**） | 中 | 由 G-02 / R-394 定界，写入文档口径条款 |
| RSK-03 | 排期 | R-395 落点在 OpenLLM 仓，受跨仓排期与立项节奏制约 | 中 | 走跨仓派单；本仓不代改（`VC-014`） |
| RSK-04 | 合规 | LiteLLM 许可与商用边界本轮未复验 | 低 | 仅作条件性保留；进入方案 D 评估前完成法务确认 |
| ASM-01 | 假设 | 会话历史由 OpenLLM 会话存储承接、长期记忆由 OpenMemory 承接、知识库由 OpenRAG 承接，三者职责不重叠 | — | 若后续出现职责重叠需重新评估回写策略 |
| ASM-02 | 假设 | auto 编排（规则 + LLM 兜底）在主要场景下决策质量可接受，无需外部决策模型 | — | 置信度阈值 0.85 与兜底链路已在位，可观测后再调 |
| CON-01 | 约束 | 本仓不得修改其他仓代码（`VC-014`） | — | 跨仓变更一律走派单 |
| CON-02 | 约束 | 编排层变更须经 Step 0 版本规划评估后方可进入实施 | — | 本报告仅评估与登记，不构成排期承诺 |

---

## 9. 登记建议与承接

| ID | 建议 | 目标版本 | 优先级 | 状态 |
|----|------|----------|:------:|:----:|
| R-394 | 编排归属与 DSL 边界定界（文档口径整合，不涉代码） | 待定（建议 v1.4.8+） | P2 | 候选 |
| R-395 | 编排链路接入上下文预算裁剪（OpenLLM 仓改造） | 待定 | P2 | 候选 |

登记位置：`doc/version/global/OpenBase-候选需求池.md` **§1.18**（文档版本 v0.28.0 → **v0.29.0**）；两条**均未纳入任何版本**，实施时机由后续 Step 0 版本规划决定。

---

## 10. 待人工决策参数

| 序号 | 参数 | 选项 / 待定内容 | 影响面 |
|:----:|------|-----------------|--------|
| 1 | 触发模式 | auto（现默认）/ explicit 强制 / 按租户或场景混合 | 编排入口契约与前端行为 |
| 2 | 单次调用延迟预算 | 未定；记忆 + 知识库双路检索串行会线性叠加时延 | 是否需并行检索与超时降级 |
| 3 | 回写粒度与幂等键 | 现为 `session_id + seq + target`；是否调整粒度与去重窗口 | 重复写入与幂等语义 |
| 4 | scope 命名口径 | 记忆 / 知识库作用域命名规则未定 | 与 R-387 跨域租户码语义议题相邻 |
| 5 | 分段 token 配额 | 画像 / 记忆 / 知识库各占多少 token 配额未定 | 直接决定 G-01 的裁剪策略 |

**上述 5 项未定前，不建议进入 R-395 实施。**

---

## 11. 结论与后续动作

1. **归属维持**：编排层归 OpenLLM，网关保持薄策略层；网关侧**不新增**编排组件。方案 A 结论已撤回并记录原因。
2. **不引入 LiteLLM**：以 §5 四条理由为决策依据；借鉴其三处语义；方案 D 作条件性保留。
3. **优先缺口**：G-01（预算裁剪）与 G-02（边界定界）已登记为 R-395 / R-394，均为 P2 候选，未纳入任何版本。
4. **前置动作（v1.1.0 口径更正）**：R-395 评估已先行启动并产出下游报告（见第 6 条）。经该报告 §6 实测认定，§10 五项参数中**仅「分段 token 配额」构成 R-395 的硬依赖**，其余四项（触发模式、延迟预算、回写粒度、scope 命名）均不阻塞实施；故本项原「先完成五项参数决策」的要求**收窄为「先拍板分段 token 配额」**。
5. **本报告不修改任何生产代码**；R-395 若推进，其落点在 OpenLLM 仓，须走跨仓派单。
6. **下游报告（v1.1.0 新增）**：《OpenBase-编排链路上下文预算裁剪评估报告-v1.0.0》（`doc/audit/assessment/`，状态 [Review]）承接本报告 §7 缺口 **G-01**。该报告**修正了 G-01 的需求口径**——由「接入 `ContextManager`」改为「**新增片段级预算裁剪能力并同步/流式双路径接入**」（依据：现有裁剪能力为消息级而待裁剪对象为片段级拼接字符串，且实测整段 Prompt 作为**唯一 user 消息**进入 LLM）；并新增既有缺陷发现 **F-01~F-06**，其中 **F-02**（`MODEL_CONTEXT_LIMITS` 前缀匹配致窗口被低估 15.6 倍）与 **F-06**（现有裁剪方法不二次校验、可返回空列表）建议与 R-395 同批修正。**本报告 §3~§9 的结论不受影响，仅 §7 G-01 的口径以该报告为准。**

---

## 12. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-09-20 | AU-OpenBase-Dev | 初始创建。范围：会话上下文编排链路的归属裁决与 LiteLLM 选型评估。结论：编排归属 OpenLLM 侧且已实现；网关侧保持薄策略层；不引入 LiteLLM（借鉴三处语义，方案 D 条件性保留）；登记缺口 G-01（预算裁剪，→ R-395）、G-02（边界定界，→ R-394）、G-03（五参数待决策）。含结论修正声明（撤回早期「方案 A 网关侧新建编排」建议）与根因分析（「聚合编排」同名不同物）。依据：双侧代码实测（`openbase/modules/llm_proxy/`、OpenLLM `backend/app/edgerouter/orchestration/`、`backend/app/api/writeback.py`、`backend/app/services/context_manager.py`、OpenLLM 全仓依赖检索）+ 既有设计文档口径核对。 |
| v1.1.0 | 2026-09-21 | AU-OpenBase-Dev | 下游报告交叉引用与口径更正：新增 §11 第 6 条，指向《OpenBase-编排链路上下文预算裁剪评估报告-v1.0.0》（承接 §7 缺口 G-01），并记录该报告对 G-01 需求口径的修正（「接入 ContextManager」→「新增片段级预算裁剪能力并双路径接入」）与新增缺陷发现 F-01~F-06；§11 第 4 条「前置动作」口径收窄为「仅分段 token 配额构成硬依赖」。本次**未改变 §3~§9 任何既有结论**，仅追加引用与更正一处前置条件表述。 |

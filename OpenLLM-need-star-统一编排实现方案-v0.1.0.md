# OpenLLM need\_\* 统一编排实现方案（v0.10.0）

| 属性   | 内容                                                                                                                                                                                                                                                                                                                          | <br /> |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| 文档编号 | OB-INTG-LLM-NEEDSTAR-v0.10.0                                                                                                                                                                                                                                                                                                | <br /> |
| 版本   | v0.10.0（草稿 \[Draft]，Phase 1 / W2 / W3 / W4 已实施）                                                                                                                                                                                                                                                                             | <br /> |
| 状态   | Phase 1 已实施（读侧 R1~~R13 / 写侧 W1）+ W2 已实施 + W3 已实施 + W4 已实施（真实契约落地 Phase A\~D，真实模式开关待联调启用）；治理 R3~~R5 已定案且 P0/P1-4 已实施；Phase 2 待评审                                                                                                                                                                                             | <br /> |
| 作者   | AD（跨项目分析）                                                                                                                                                                                                                                                                                                                   | <br /> |
| 日期   | 2026-09-04                                                                                                                                                                                                                                                                                                                  | <br /> |
| 适用范围 | OpenLLM 仓库 backend/app 网关编排层；SSE 契约扩展需 OpenBase 前端侧同步评估                                                                                                                                                                                                                                                                     | <br /> |
| 输入   | 流程分析报告 v1.1.0（§6.3/§6.4）；编排核心层与网关/契约层接口级只读深挖（v0.2 新增）；四件套身份头矩阵调研；双链路拓扑需求澄清（v0.2.1）；会话后沉淀/回写侧只读调研（v0.3.0 新增）；写侧目标文件接口级提取（v0.4.0 新增）；Phase 1 实施记录与偏差回写（v0.5.0 新增）；W2 实施记录回写（v0.6.0 新增）；W3 实施记录回写（v0.7.0 新增）；tests/unit 全量宽回归记录追加（v0.7.1）；治理 R3\~R5 结论同步（v0.8.0 新增）；治理 P0 实施同步（v0.9.0 新增）；真实契约落地（P1-4+W4 合流）最终状态同步（v0.10.0 新增） | <br /> |

***

## 1. 目标与范围

- 目标：把当前 memory/rag 的 need\_\* 编排升级为 need\_\* 三件套统一编排（memory + rag + profile/DPS）：画像从"固定注入"迁移为与 memory/rag 同级的一等组件（共享执行/并行/计时/降级/上报语义），SSE routing 契约扩展 need\_profile / profile\_source。

- 明确不做：不引入 OpenBase 编排层（路线 B）；不改变"OpenBase=外部入口、OpenLLM=内网编排"分层；不改动 ComponentRouter 现有 decision 契约键（见 D1）。

- 阶段划分：Phase 1 组件化 + 契约上报（画像默认仍注入，语义向后兼容）；Phase 2 精细化触发策略（可选，另行评审）。

- 写侧（会话后沉淀）同步纳入范围：读侧（need\_\* 上下文召回）与写侧（沉淀回写）为对称两半场，见 §8。

## 2. 现状关键事实（接口级核对摘要）

- 键名接缝：编排层 pipeline entry 用 name/params 键（executor.py）；外部契约与 gateway 校验用 component 键（explicit.py、openllm\_gateway.py）。新增 profile 必须两处对齐。

- 决策：ComponentRouter.decide 仅非流式 auto 使用；decision 返回纯 dict（need\_memory/need\_rag/reason），被单测精确断言（test\_orchestration.py:618-628）。options 是自由 dict；enable\_memory/enable\_rag 缺省 True（auto.py）。

- 执行：PipelineExecutor.\_run\_component 全泛型；组件调度集硬编码 memory/rag（executor.py:105），raw\_results 收集同（executor.py:124）。非流式 handler 由 \_build\_component\_handlers 注入，流式走 \_run\_stream\_components——两套执行逻辑并存（技术债，本次不重构）。

- 画像半成品（B1）：profile\_ctx 已是 assembler.render 参数与 executor/auto/explicit 透传形参；gateway 在 chat 与 stream 路径无条件拉取，失败静默 None，不进决策/路径/degraded/timeline。

- 组装器：模板画像段已存在且在 memory 前；format\_context 对 str 原样返回、对空画像 dict 输出空串——画像需独立格式化（\_format\_profile\_ctx）。

- routing\_trace/components 多处构造：非流式、缓存命中、占位、bypass、流式初始（routing 事件唯一写入处）。\_save\_trace 原样落库。

- 流式时序局限：画像拉取在 routing yield 之后；要在 routing 事件带真实 profile\_source 必须提前到 yield 前。

- 写侧（沉淀）：回写基础设施已实现（WritebackQueue：SQLite、targets CHECK memory/rag/profile、UNIQUE(session\_id,seq,target)、重试上限 3；显式 POST /openllm/v1/writeback；三 handler；executor 门控仅非流式 /chat）。缺口：流式/缓存/旁路零沉淀、画像漂移未接线、save\_if\_valuable 未消费、session\_id 实为用户 id、recover/cleanup 未接线、写回无 org 前缀、死行风险、真实上游写契约存疑（/openrag/v1/ingest、/openmemory/v1/write 为 stub 契约）。

- 测试 DI：编排层纯构造注入；网关 API 用 TestClient + patch adapter；队列/写回 API/漂移各有专门单测。

## 2A. 双链路拓扑约束（v0.2.1 需求澄清）

OpenLLM 与四件套之间存在两条并行链路，均为设计意图，不可互相替代：

| 链路     | 路径                                                                          | 用途                                                           | OpenLLM 故障时                |
| ------ | --------------------------------------------------------------------------- | ------------------------------------------------------------ | -------------------------- |
| 主通道    | 前端 → OpenBase llm-proxy → OpenLLM 统一网关 →（网关内嵌编排）组件回调 OpenMemory/OpenRAG/DPS | 大模型对话/知识增强对话：need\_\* 决策与上下文组装在网关内完成                         | 不可用（依赖 LLM 生成）             |
| 旁路（透传） | 前端 → OpenBase rag-proxy / memory-proxy / dps-proxy → 对应系统                   | 知识库管理/RAG 问答、记忆、画像等独立业务能力（如 ChatView 走 rag-proxy 直连 OpenRAG） | 仍可用，保证 OpenLLM 不通时其他四件套可访问 |

约束含义：

1. need\_\* 组件回调（memory/rag/profile）仅存在于主通道（OpenLLM 网关内网直连），不回环经 OpenBase proxy 调用——OpenBase 各专属 proxy 是旁路/业务通道，不应成为编排层中转。
2. 治理 R1 = 双链路边界书面化而非去重；两链路读写同一批上游数据，身份语义与凭据通道必须一致（R3/R4/R5 冲突治理直接影响旁路切换后的数据隔离正确性）。

## 3. 设计决策（读侧，v0.2 修订）

- D1 触发方式 = enable\_profile 恒注入开关门控，不扩 ComponentRouter decision 契约：R00x 规则、\_parse\_llm\_decision、decision keys 全不动；need\_profile 只作运行时上报字段。

- D2 运行时生效值：enable\_profile\_effective = chat\_req.enable\_profile 优先，否则 settings.OPENLLM\_ENABLE\_PROFILE（默认 True）；真拉取需 DPS\_ENABLED + DPS\_BASE\_URL + adapter 就绪。

- D3 profile 入组件执行通道但不出 raw\_results：executor 组件集、explicit/gateway 白名单、auto entries 放行 profile；raw\_results 元组不加。

- D4 格式化为 handler 内预格式化：handlers\["profile"] 返回 \_format\_profile\_ctx 字符串 → format\_context str 分支透传 → contexts\["profile\_ctx"]。assembler.py 零改动。

- D5 参数与校验：explicit/gateway 白名单加 profile；user\_id 必填（对齐 memory 4003）；auto entry user\_id 沿用 options 到 request\_context 兜底。

- D6 流式 routing 准确性：画像拉取提前到 routing 事件前；原流式内联拉取删除，render 从 contexts 取。

- D7 过渡兜底：非流式保留内联拉取过渡，render 双源兜底；流式无兜底；稳定后另 commit 清理。

- D8 契约与配置：SSE 契约只增可选字段；config 新增 OPENLLM\_ENABLE\_PROFILE（默认 True，DPS\_ENABLED 双门控）。

## 4. 读侧落点映射（R1\~R13，Phase 1 实现依据）

> 缩写：GW = app\api\openllm\_gateway.py；E/A/X = app\edgerouter\orchestration\ 下 executor/auto/explicit；C = app\core\config.py。

| #   | 落点                              | 改动内容                                                                                                                                                     |
| --- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | C DPS 配置后                       | 新增 OPENLLM\_ENABLE\_PROFILE（默认 True，注释 DPS\_ENABLED 双门控）                                                                                                 |
| R2  | GW 请求模型                         | 顶层字段 enable\_profile（可选 bool）                                                                                                                            |
| R3  | GW 新增 helper                    | \_effective\_enable\_profile(chat\_req)（请求 → 配置缺省 → False）                                                                                               |
| R4  | GW \_build\_component\_handlers | shared\_state 初始化加 profile\_source=skipped                                                                                                               |
| R5  | GW \_build\_component\_handlers | 新增 handlers\["profile"]：adapter 拉取 → \_format\_profile\_ctx 返回 str；None/异常转 ComponentUnavailableError(dps)；成功置 profile\_source=dps；timeline step profile |
| R6  | E 组件集                           | 组件集加 profile；raw\_results 元组不加                                                                                                                           |
| R7  | A auto entries                  | enable 生效且有 user\_id 时前置注入 profile entry；PATH\_MAP 不变                                                                                                    |
| R8  | X + GW 校验                       | 白名单加 profile；4003 校验 profile.user\_id；\_auto\_pipeline 保持 truthy 判定                                                                                      |
| R9  | GW 流式                           | \_run\_stream\_components 加 profile 分支并返回 profile\_source；画像拉取提前到 routing yield 前；删除内联拉取；render 从 contexts 取                                             |
| R10 | routing\_trace 构造点              | 非流式组件上报补 need\_profile/profile\_source（按画像实际注入）；缓存命中与占位路径为 false/skipped；流式初始填 enable 值、yield 前修正                                                        |
| R11 | GW \_save\_trace                | 无需改动（原样落库）                                                                                                                                               |
| R12 | SSE 契约文档                        | routing 行只增可选 need\_profile/profile\_source；版本升 v1.1.0                                                                                                   |
| R13 | E render + 非流式                  | render 双源兜底（contexts 优先、profile\_ctx 形参回落）；非流式内联保留过渡                                                                                                     |

执行顺序建议：R1 到 R8（每步跑单测）→ R9 → R10 → R12；R11/R13 收尾。

## 5. 读侧测试计划（Phase 1）

- 既有约束：decision 契约护栏测试保持不动（D1）。

- 新增：executor profile 注入/并行池三组件/降级；auto enable\_profile 开关两态（FakeRouter）；explicit profile 校验与 4003；非流式 routing\_trace need\_profile/profile\_source 两态；流式 routing 事件真实 profile\_source；\_run\_stream\_components 函数级直测（当前空白）；缓存/占位字段同步。

- 命令（backend 目录）：python -m pytest tests/unit/test\_orchestration.py 与网关相关测试文件，详见 §9.2 复现环境。

## 6. 治理清单（四件套内部网关/身份隔离 vs OpenBase）

结论：合理分层保留（OpenBase=外部唯一入口 + 四件套内部纵深防御）。R3~~R5 已完成跨仓库评审并定案：见《四件套身份隔离治理评审（R3~~R5）》v1.2.0（Q1\~Q6 决策记录于其 §7，立项路线图 P0/P1/P2 于其 §8）；R1 边界书面化于 §2A，R2/R6 并入同一路线图。治理 P0（P0-1/P0-2/P0-3）已于 2026-09-04 实施（治理文档 v1.2.0 §9），本表行级 P0 联动项均已落地，P1/P2 待立项：

| #  | 治理项           | 定案（治理评审 v1.2.0）与联动                                                                                                                    |
| -- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| R1 | 双链路边界与身份一致性   | 边界已书面化（§2A，主通道/旁路均保留）；可辨识性与 M3 走 Q4 / P0-2〔已实施〕（llm\_proxy 注入 X-User-ID/X-Org-ID/X-Proxy-Source + OpenLLM TRUSTED\_PROXY\_SOURCES 解析） |
| R2 | 三套同名隔离引擎      | 内网统一身份协议头列为 P2-1（Q2/Q3 定案后评估，待立项）                                                                                                     |
| R3 | user\_id 双标识  | Q3 + Q4 定案：对外租户键统一为 tenants.code（P1-3，待立项）；旁路最小档打通外部 sub 可辨识（P0-2〔已实施〕）；DPS 硬绑 id=1 治理入 P2-2（待立项）                                     |
| R4 | org/tenant 串味 | Q2/Q3 定案：tenant 为唯一租户键、org 头退役为兼容别名、dps\_org\_map 停用（P1-2/P1-3，待立项）                                                                   |
| R5 | 凭据通道碎片化       | Q1/Q6 定案：统一 X-API-Key——P0-1 门禁与 bypass 收敛〔已实施〕、出站 X-API-Key 头〔已实施〕；P1-1/P1-4 待立项（stub 契约转真实，衔接本方案 W4-1/W4-2）                          |
| R6 | 审计身份头空转       | Q4/P0-2〔已实施〕打通 M3 归属链路（llm\_proxy 三头 + 可信源配置）                                                                                         |

## 7. 风险与开放问题

1. D1 取消 decision 键扩展后，画像触发仅靠 enable\_profile + adapter 就绪，无条件注入语义；Phase 2 精细化时再评估演进 decision 契约。
2. output\_mode=raw\_results 下 profile 不进 raw\_results（D3），画像仅为 prompt 上下文，属预期。
3. DPS /profile/v1/\* 真实端点缺失（v2.14.3 P1 已登记）：读侧可先对接 stub 契约；真实联调需 DPS 侧补端点或用既有能力映射。
4. 流式下画像与 memory/rag 并行依赖 enable\_parallel；默认串行时画像为首 token 前一次额外 RTT（现状延续）。
5. 治理清单 R1\~R6 与本方案解耦，另行评审排期。
6. 双链路旁路一致性：OpenLLM 故障切旁路时同一用户必须落到同一隔离键；R3/R4/R5 治理未完成前，切换可能改变数据可见域——旁路上线检查需含身份头一致性验证。

## 8. 写侧编排：会话后沉淀（v0.3.0 评估 + v0.4.0 落点细化）

> 范围：每次会话经 OpenBase 调用四件套之后的沉淀——记忆（OpenMemory）、画像（DPS）、知识（OpenRAG）。与读侧构成对称两半场。

### 8.1 现状盘点（写侧资产与缺口）

已有资产：WritebackQueue（SQLite；targets CHECK memory/rag/profile；UNIQUE(session\_id,seq,target)；重试上限 3 指数退避；单例 get\_writeback\_queue()）；显式 POST /openllm/v1/writeback（sync/async 双模、seq 缺省 max\_seq+1）；三个 handler；executor 非流式 /chat 门控触发 memory/rag 回写；profile\_drift.py（判定 + 调度器类，未接线）。

| 沉淀对象           | 现状通道                                                         | 触发                                                           | 缺口                                                                                                            |
| -------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| 记忆（OpenMemory） | memory\_adapter.write（query/response/session\_id/metadata）   | 仅非流式 /chat：pipeline 含 memory 且 LLM 成功                        | 流式/缓存/旁路零沉淀；无提炼与重要度/确认闸门；契约风险（client /openmemory/v1/write vs 真实 /remember）                                    |
| 画像（DPS）        | update\_profile → /profile/v1/update；漂移仅 classify\_drift 打日志 | 仅显式 POST /writeback（DPS\_ENABLED 默认 False；主链路不构造 profile 闭包） | 无自动画像沉淀；DriftRecomputeScheduler 无生产接线；提炼为关键词规则非 LLM                                                           |
| 知识（OpenRAG）    | rag handler 单轮 response 全文 ingest 至 kb                       | 同记忆门控                                                        | save\_if\_valuable 未消费；全文自动入库污染；契约存疑（/openrag/v1/ingest 为 stub；真实 OpenRAG 为 /api/v1 文档上传 PENDING / 治理 ingest） |
| 会话级            | 无                                                            | 无                                                            | 无会话结束 trigger、无多轮摘要、沉淀源=单轮 query+response                                                                     |

基础设施缺口：① session\_id 实为 user\_id + 进程内 seq（重启归零冲突）；② recover/cleanup 未接线，handler 未注册分支不落 failed → 永久 pending 死行（\_ensure\_handlers 仅在写回端点内调用）；③ 写回 RequestContext 固定 org\_id 空与 namespace 空；④ 双链路归属未定（ChatView 旁路会话不进回写）。

### 8.2 编排评估结论（方向）

1. 沉淀要有价值分级，不是全量沉淀：记忆=提炼后低频写；画像=delta+置信度（低置信进漂移队列）；知识=仅显式认可，单轮 response 全文自动 ingest 默认关闭。
2. 写侧决策器与读侧对称：EvaluateSession 输出 Evaluation 列表，逐项过闸门（价值/重要度/频控/去重）。
3. 统一走 WritebackQueue 且先修基础设施：启动期 handler 注册、recover 接线、幂等键会话/消息级化、写回身份前缀一致（治理 R3/R4）。
4. 主通道为沉淀主编排位：流式收尾与缓存命中补偿加"会话评估到沉淀"钩子；画像漂移调度器接线。
5. 旁路沉淀最小集 + 知识管理式入库：旁路显式触发（记忆/画像）；知识走 OpenRAG 管理式，不在对话链路自动全文 ingest。
6. 契约对齐前置：真实 OpenMemory/OpenRAG 写契约与 DPS /profile/v1/\*，属双链路治理 R3\~R5 的一部分。

### 8.3 接口级落点映射（v0.4.0，替代原分阶段简表）

> 缩写：WQ = app\services\writeback\_queue.py；WB = app\api\writeback.py；PD = app\services\profile\_drift.py；GW/EX/MN/CF 同前。

**W1 基础设施修复（已实施，v0.5.0 标注）**

| #    | 落点                             | 接口级改动                                                                                                                                                       | 实施状态                  |
| ---- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| W1-1 | MN lifespan 启动段、yield 前        | init\_writeback\_subsystem（注册三 handler + recover\_pending），失败 WARN 不阻断启动                                                                                    | 已实施                   |
| W1-2 | WQ \_run\_item handler None 分支 | handler 缺失：mark\_failed + error 日志（不再永久 pending）                                                                                                            | 已实施                   |
| W1-3 | MN 关闭段                         | 全局队列 drain()（优雅停机，try/except 降级）                                                                                                                            | 已实施                   |
| W1-4 | WQ DDL 与 enqueue/submit        | 增量演进：新增 user\_id/message\_hash 列 + 部分唯一索引（message\_hash 非空）；保留旧 UNIQUE(session\_id,seq,target)；seq 放宽为可空、store 写锁内 max\_seq+1 兜底；compute\_message\_hash 纯函数 | 已实施（迁移方式偏差见 §9.3 D-4） |
| W1-5 | GW 自动回调                        | base\_kwargs 携带 user\_id/session\_id/org\_id/namespace\_prefix；回调提交 seq=None + message\_hash；删除进程内 seq 计数器                                                  | 已实施                   |
| W1-6 | WB 上下文与请求模型                    | \_build\_wb\_request\_context 读 org\_id/namespace\_prefix；WritebackRequest 增加可选字段并透传                                                                        | 已实施                   |

**W2 主通道非流式质量化（已实施，v0.6.0 标注）**

| #    | 落点                                    | 接口级改动                                                                                                                                                            | 实施状态                        |
| ---- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| W2-1 | WB \_rag\_writeback                   | 消费 save\_if\_valuable：False 跳过 ingest 记 skipped；True 维持现状 ingest（内容级决策交 W3）                                                                                      | 已实施                         |
| W2-2 | WB \_memory\_writeback + EX 门控 + auto | 记忆类型化：memory entry/回调透传 memory\_type + importance；缺省 episodic；metadata 恒携带；importance 校验与防御性过滤                                                                   | 已实施                         |
| W2-3 | GW 回调 + 调用点 + 提炼模块                    | 回调返回（memory/rag/profile + base\_kwargs）；非流式成功后按画像信号提交 profile target；提炼纯函数入 services\profile\_refine.py；LLM 提炼开关 OPENLLM\_PROFILE\_LLM\_REFINE（默认关）与注入门控，真实链路待接线 | 已实施（LLM 链路取舍见 9.5 D-11）     |
| W2-4 | WB + PD + MN                          | 写前 classify\_drift；低置信转漂移重算条目（phase=drift\_recompute）入队；handler 支持 phase 分支；lifespan 接线 DriftRecomputeScheduler（最小档观测）与 stop()；两配置消费化                            | 已实施（scheduler 档位见 9.5 D-10） |

**W3 流式与会话级（已实施，v0.7.0 标注）**

| #    | 落点             | 接口级改动                                                                                                                                                     | 实施状态                  |
| ---- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| W3-1 | 新增 evaluate.py | 写侧决策器 evaluate\_session → Evaluation 列表；闸门=价值（save\_if\_valuable + 质量启发式）/重要度（意图关键词）/频控去重（WritebackStore.exists\_message 预检）；rag 默认不产出，仅 enable\_rag 显式开启 | 已实施                   |
| W3-2 | GW 流式收尾与断连分支   | 会话评估到沉淀提交钩子：窗口聚合后逐 Evaluation submit（真实 message\_hash）；正常/异常收尾 await 执行、GeneratorExit 断连用 shield 后台任务；总开关 OPENLLM\_STREAM\_WRITEBACK（默认 False）            | 已实施（收尾方式取舍见 9.6 D-13） |
| W3-3 | GW 缓存命中        | 命中默认零沉淀；配置 OPENLLM\_CACHE\_WRITEBACK（默认 False）开启且命中时仅提交 memory summary，不触发 LLM 提炼                                                                         | 已实施                   |
| W3-4 | 窗口与提炼          | summarize\_window 确定性窗口摘要（Q/A 截断、最近 8 轮、上限 800 字）；summary 只写结论不写全文；当前窗口=当轮（多轮扩展点见 9.6 D-15）                                                               | 已实施                   |

**W4 契约与旁路（已随真实契约落地立项实施，v0.10.0 标注）**

> 实施状态（v0.10.0）：W4-1~~W4-5 全部随《真实契约落地与沉淀收敛立项方案》v1.2.0（P1-4 + W4 合流）Phase A~~D 实施完毕（任务 T1~~T8，含 D1~~D4 定案）；OpenLLM 真实模式开关（OPENLLM\_OPENMEMORY\_REAL / OPENRAG\_REAL / DPS\_REAL）缺省 False，真实服务联调待执行；实施与残余项记录见立项方案 §7。
>
> 状态注（v0.11.0，2026-09-06）：P1 级发布批次完成——画像对话内注入（OPENLLM\_DPS\_REAL=true：explicit profile 组件真实注入，routing profile\_source=dps）与漂移重算真实落地（低置信 0.3 → phase=drift\_recompute 条目 → 真实 PUT，version 12→13）；网关 dps 健康探活契约分叉修复（real→client.ping）。实证细节见《OpenBase-DPS对接完善任务书》v2.6.0 与 OpenLLM 仓提交。

| #    | 落点                                   | 接口级改动                                                          |
| ---- | ------------------------------------ | -------------------------------------------------------------- |
| W4-1 | openmemory\_client vs OpenMemory 真实  | 写契约对齐：确认 /openmemory/v1/write 前缀；否则改用真实 RememberRequest        |
| W4-2 | openrag adapter/client vs 真实 OpenRAG | 知识沉淀统一管理式：client 新增文档上传（PENDING + 轮询）或治理 ingest；stub 契约标注废弃或兼容 |
| W4-3 | dps\_client                          | /profile/v1/\* 真实端点落地或改用既有能力映射；解除 P1                           |
| W4-4 | OpenBase 侧（旁路归属）                     | 旁路会话沉淀归属评审；沉淀责任矩阵文档化                                           |
| W4-5 | 双链路一致性（写侧配套）                         | org 前缀/四头与 R3\~R5 同步落地，两链路写隔离键一致                               |

### 8.4 写侧测试与执行顺序（v0.4.0）

- 新增用例：W1-1/W1-2（handler 未注册转 failed 非死行；启动注册+recover 集成）；W1-4（message\_hash 幂等、重启后 hash 幂等不冲突、旧库演进幂等）；W1-6（org 前缀透传）；W2-1（save\_if\_valuable=false 不 ingest）；W2-3（主链路 profile 回写接线与低置信转漂移）；W2-4（scheduler 注入 start/stop）；W3-1（EvaluateSession 决策与闸门）；W3-2（流式 done 后触发沉淀钩子）。DI 复用：临时 DB、API fake adapter、executor fake writeback + patch sleep。

- 回归护栏：writeback\_queue / writeback API / writeback\_profile / drift / memory\_writeback 相关单测保持全绿。

- 执行顺序：W1/W2/W3（已完成）→ W4（依赖治理 R3\~R5 评审后实施）。

## 9. 实施记录与偏差（Phase 1，v0.5.0）

### 9.1 实施范围与验证结论

Phase 1（读侧 R1\~R13 + 写侧 W1）已按 TDD 在 OpenLLM 仓库实施完毕（2026-09-04，OpenLLM backend 目录），全部回归通过、ruff 0 错误：

| 批次      | 范围                                | 关键文件                                                          | 回归结论                                |
| ------- | --------------------------------- | ------------------------------------------------------------- | ----------------------------------- |
| R1\~R8  | 配置开关/请求字段/组件执行层                   | config.py；openllm\_gateway.py；executor.py、auto.py、explicit.py | 89 passed（核心 4 文件）＋168 passed（扩展护栏） |
| R9\~R13 | 流式组件化/画像预取前置/routing 上报/契约升版/双源兜底 | openllm\_gateway.py、executor.py；SSE 契约文档升 v1.1.0              | 251 passed                          |
| W1      | 写回基础设施修复                          | writeback\_queue.py、writeback.py、openllm\_gateway.py、main.py  | 137 passed（既有 8 文件零改动保持通过）          |

新增测试文件：tests\unit\test\_profile\_component\_phase1.py（26 条）、tests\unit\test\_stream\_profile\_routing.py（14 条）、tests\unit\test\_writeback\_w1\_phase1.py（21 条）。

### 9.2 复现环境（测试运行约定）

- 解释器：D:\PostgreSQL\17\pgAdmin 4\python\python.exe（Python 3.13，见 tests\conftest.py 环境适配注释）。

- 环境变量：OPENLLM\_TEST\_EXTRAS 指向 backend\extras.venv\Lib\site-packages；WRITEBACK\_DB\_PATH 与 SEMANTIC\_CACHE\_DB\_PATH 指向工作区临时 DB（避免写入仓库 data 目录被沙箱拦截）；PYTHONDONTWRITEBYTECODE=1、PYTHONPYCACHEPREFIX 指向临时目录。

- 命令：python -m pytest 目标文件 -q -p no:cacheprovider -o addopts=''；静态检查 .pylib\bin\ruff.exe check --no-cache 改动文件。

### 9.3 已记录偏差（实施与方案表的差异及理由）

| #   | 偏差                                                                                                      | 理由与影响                                                          |
| --- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| D-1 | R7 extract\_targets 取值走 options 自由键透传（方案未定键名）                                                           | 无默认键约定，自由 dict 语义；handler 经 params 原样透传 adapter                |
| D-2 | test\_coverage\_boost\_v2112.py 一处 auto 全链路 pipeline 断言调整为 profile 前置                                   | R7 默认注入属 Phase 1 预期；routing\_trace path/decision 断言不变，决策契约护栏未动 |
| D-3 | 流式 llm-only explicit 请求不再无条件注入画像（原 B1 固定注入）                                                             | D7 组件化唯一来源：流式无兜底；explicit 需自行声明 profile 组件（白名单已放行）             |
| D-4 | W1-4 迁移采用增量演进（ALTER TABLE ADD COLUMN ＋ 部分唯一索引），替代 rename+重建                                             | 破坏性重建风险高；旧行与显式 API（无 hash）天然豁免新约束；重启后 hash 幂等由落库索引保证           |
| D-5 | W1-5 直接删除进程内 seq 计数器与函数                                                                                 | 仅网关内部使用无外部引用，不留死代码                                             |
| D-6 | W1-6 写回 user\_id 归一为 org 前缀形态（已带前缀不叠加）；身份字段按 GatewayIdentity 实际结构读取；session\_id 无会话上下文时以 user\_id 兜底并注释 | 与读侧请求上下文对齐（治理 R3 局部收敛）；显式 API 仅显式传参才透传，向后兼容                    |
| D-7 | lifespan 启动注册与 recover 失败仅 WARN 不阻断启动                                                                   | 保障可用性；队列恢复属尽力而为                                                |

### 9.4 剩余门禁

- 写侧 W4 已随真实契约落地立项（P1-4+W4 合流，立项方案 v1.2.0）实施完毕；残余为真实服务联调与真实模式开关启用（见 §8.3 W4 状态注）。

- 会话级多轮窗口沉淀为扩展点（网关无会话上下文，当前以当轮为窗口，需 conversation 上下文贯通后启用，见 9.6 D-15）。

- 读侧 Phase 2（画像条件化触发，演进 decision 契约）另行评审。

- 过渡语义清理（R13 稳定后删除非流式内联拉取链）留待后续 commit。

- LLM 画像提炼真实链路（OPENLLM\_PROFILE\_LLM\_REFINE 开启后的调用链接线）留待后续（见 9.5 D-11）。

### 9.5 W2 实施记录（v0.6.0）

W2（写侧主通道非流式质量化，W2-1\~W2-4）已按 TDD 在 OpenLLM 仓库实施完毕（2026-09-04），全量回归 223 passed、ruff 0 错误：

| 条目   | 落地行为                                                                                                                                                                                                                                                               |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| W2-1 | `_rag_writeback` 先判 save\_if\_valuable（缺省 True）：False 记 INFO 后直接返回，不构造 documents、不触发 ingest；True 维持现状（内容级决策交 W3）                                                                                                                                                   |
| W2-2 | WritebackTarget 增加 importance（0\~1，越界 4001）；\_resolve\_memory\_metadata 恒带 memory\_type（缺省 episodic）+ importance（越界防御过滤）；主链路经 executor memory entry 参数抽取与 auto options 透传                                                                                          |
| W2-3 | \_build\_writeback\_callback 返回 memory/rag/profile 三路 + base\_kwargs；非流式成功后 \_auto\_submit\_profile\_delta 按画像信号提交 profile target，信号不足记 skipped；提炼纯函数抽至新模块 services\profile\_refine.py（显式 updates 优先 → extract\_targets+dialogue 规则抽取）；LLM 提炼开关与注入门控（默认关闭，真实链路待接线） |
| W2-4 | 写前 classify\_drift：低置信（低于 PROFILE\_DRIFT\_CONFIDENCE\_THRESHOLD）不直写 DPS，生成 phase=drift\_recompute 条目入队（相位参与 message\_hash 区分）；handler 支持 phase 分支按快照重算执行 update；lifespan 经 start/stop\_drift\_recompute\_scheduler 接线 DriftRecomputeScheduler（最小档存量观测）             |

验证：新增 tests\unit\test\_writeback\_w2\_phase1.py（46 条）；全量回归 11 文件 223 passed（writeback W1 21、writeback\_queue 8、gateway\_ext 23、memory\_writeback 6、writeback\_profile 13、drift 11、orchestration 31、openllm\_gateway 24、profile\_component 26、stream\_profile\_routing 14、W2 新增 46）；ruff 0 错误。既有断言两处更新（test\_writeback\_w1\_phase1 回调解包 3 元改 4 元；test\_v2142\_memory\_writeback 缺省 memory\_type 由 None 改为 episodic）。

W2 偏差（D-8 起）：

| #    | 偏差                                                                                           | 理由与影响                                                                         |
| ---- | -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| D-8  | \_build\_writeback\_callback 实际返回 4 元组（三路回调 + base\_kwargs）而非字面三元组                           | executor 记忆/rag 门控需独立 base\_kwargs（含 query/response 合并），保留第 4 元；W1 两处解包断言同步更新 |
| D-9  | 漂移判定在 \_profile\_writeback 写 DPS 前执行：低置信先落普通行（标记 done），执行时生成 phase=drift\_recompute 漂移行承载最终写 | 语义等价"不直写、转漂移重算"；drift 哈希含相位不与普通行去重冲突；库内多一行已完成普通记录                             |
| D-10 | 调度器本轮为最小档接线（start/stop + 存量观测回调），周期性全量重算主体由队列 phase 条目承担                                     | 与方案 §8.4"最小档/完整档"表述一致，窗口级完善属 W3                                               |
| D-11 | OPENLLM\_PROFILE\_LLM\_REFINE（默认 False）仅完成开关 + 注入门控接口，真实 LLM 调用链未接线                          | 复用既有 LLM 调用链改造成本高且默认关闭；不造假实现，接口可单测 mock，真实链路留待后续                              |
| D-12 | profile 自动沉淀触发信号取 routing\_trace.components.profile\_source == dps（含显式/openai 通道内联画像注入的情况）   | 口径已在代码注释与本节声明，保证画像信号口径唯一                                                      |

### 9.6 W3 实施记录（v0.7.0）

W3（写侧流式与会话级，W3-1\~W3-4）已按 TDD 在 OpenLLM 仓库实施完毕（2026-09-04）。新增 tests\unit\test\_writeback\_w3\_phase1.py（28 条）；全量回归 13 文件全绿（W3 新增 28、W2 46、W1 21、stream\_profile\_routing 14、openllm\_gateway 24、orchestration 31、profile\_component 26、stream\_optimization 12、memory\_writeback 6、writeback\_profile 13、writeback\_queue 8、gateway\_ext 23、drift 11）＋额外安全网 109 passed（coverage\_boost\_v2112 / chat\_stream\_api / semantic\_cache）；ruff 0 错误；既有测试断言零改动。

| 条目   | 落地行为                                                                                                                                                                                                                                                                           |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| W3-1 | 新增 app\edgerouter\orchestration\evaluate.py：Evaluation 结构与 evaluate\_session；闸门=价值（save\_if\_valuable + response 质量阈值）/重要度（记忆意图关键词 0.5/0.8）/频控去重（WritebackStore.exists\_message 预检，哈希语义与 W1-4 一致）；默认产出 memory summary；rag 默认不产出仅 enable\_rag 显式开启；profile 增量可选（LLM 提炼仍走 W2 开关） |
| W3-2 | 流式收尾钩子：generate() 三处接线（GeneratorExit 断连 shield、\_finalize\_stream RuntimeError 回落 shield、正常/异常收尾 await 执行）；窗口聚合 → evaluate\_session → 三路回调 submit（真实 message\_hash）；总开关 OPENLLM\_STREAM\_WRITEBACK（默认 False，注释避免静默行为变化）                                                        |
| W3-3 | 缓存命中默认零沉淀；OPENLLM\_CACHE\_WRITEBACK（默认 False）开启且命中时仅提交 memory summary（问答对摘要），LLM 零调用                                                                                                                                                                                           |
| W3-4 | summarize\_window：确定性、Q/A 分轮截断（120/240 字）、最近 8 轮、上限 800 字、空窗口返回空串；summary 只写结论                                                                                                                                                                                                 |

W3 偏差（D-13 起）：

| #    | 偏差                                                                                          | 理由与影响                                                                   |
| ---- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| D-13 | 收尾执行方式：可 await 上下文（正常完成/异常分支）同步 await 钩子，仅 GeneratorExit/await 不可用处用后台 shield               | 沉淀只写回队列不依赖请求生命周期 DB；同步 await 保证 SSE 收尾与落库有序且可确定性测试；断连路径保持 shield 尽力而为语义 |
| D-14 | 流式钩子 profile 画像增量仅在 profile\_source == dps（画像信号足）时开启，默认 llm-only/无画像流不产出                    | 与 W2-3 非流式口径一致，§8.2 结论 5 的保守实现                                          |
| D-15 | 沉淀窗口以当轮 query+response 为准（网关无会话上下文；既有 conversation\_service 需 conversation\_id 对齐而请求/身份未承载） | 不引入新持久化依赖；扩展点与取舍已注释，多轮窗口需会话上下文贯通后启用                                     |

### 9.7 tests/unit 全量宽回归记录（v0.7.1 追加）

针对 R1~~R13 与 W1~~W3 全部实施内容，在 OpenLLM backend 目录对 tests/unit 做一次全量宽回归（复现环境见 9.2）：

| 项    | 结果                                                                                                                                                |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| 全量单测 | tests/unit 1637 passed，0 failed，退出码 0                                                                                                             |
| 耗时   | 198.15s（约 3 分 18 秒）                                                                                                                               |
| 告警   | 42 条 warnings 均非阻断：既有 mock coroutine 未 await 的 RuntimeWarning（test\_v213\_gateway\_ext）与 fixture DROP 排序 SAWarning（conftest），非本次实施引入              |
| 结论   | 读侧 Phase 1 与写侧 W1~~W3 的全部实现（含新增测试文件 test\_profile\_component\_phase1 / test\_stream\_profile\_routing / test\_writeback\_w1~~w3\_phase1）未引入任何单测回归 |

### 9.8 治理 P0 实施同步（v0.9.0）

治理路线图 P0 批次（P0-1 空密钥门禁与 bypass 收敛、出站 X-API-Key 头统一；P0-2 llm\_proxy 三头注入与 OpenLLM 可信源解析；P0-3 DPS 端口 8000 对齐与探活）已于 2026-09-04 实施完成，实施记录与验证见治理文档 v1.2.0 §9。对本方案的影响：§6 行级 P0 联动项均已落地（外部身份可经 M3 链路解析到请求上下文），W4/P1-4 的真实联调前置条件（凭据与身份形态）已具备。

## 10. 修订历史

| 版本      | 日期         | 修改人       | 摘要                                                               |
| ------- | ---------- | --------- | ---------------------------------------------------------------- |
| v0.1.0  | 2026-09-04 | AD（跨项目分析） | 初稿：现状证据、Phase 1/2 变更清单、测试计划、治理清单                                 |
| v0.2.0  | 2026-09-04 | AD（跨项目分析） | 落点细化：读侧接口级核对；D1 修订（不扩 decision 契约）；R1\~R13 落点映射                  |
| v0.2.1  | 2026-09-04 | AD（跨项目分析） | 双链路拓扑澄清（主通道/旁路，保 OpenLLM 故障可用）；修正治理 R1；增补旁路身份一致性风险               |
| v0.3.0  | 2026-09-04 | AD（跨项目分析） | 写侧编排评估：会话后沉淀现状盘点与缺口、沉淀决策器/统一队列/分阶段 W1\~W4 方向                     |
| v0.4.0  | 2026-09-04 | AD（跨项目分析） | 写侧接口级落点：W1\~W4 逐项落点映射与测试/执行顺序                                    |
| v0.5.0  | 2026-09-04 | AD（跨项目分析） | Phase 1 实施完成回写：读侧 R1~~R13 与写侧 W1 实施结果、复现环境、偏差 D-1~~D-7、剩余门禁      |
| v0.6.0  | 2026-09-04 | AD（跨项目分析） | W2 实施完成回写：W2-1\~W2-4 落地行为、223 passed 验证、W2 表标注已实施、偏差 D-8\~\~D-12 |
| v0.7.0  | 2026-09-04 | AD（跨项目分析） | W3 实施完成回写：W3-1\~W3-4 落地行为、28 新增与全量回归验证、W3 表标注已实施、偏差 D-13\~\~D-15 |
| v0.7.1  | 2026-09-04 | AD（跨项目分析） | 追加 tests/unit 全量宽回归记录（1637 passed / 0 failed / 198.15s，见 9.7）    |
| v0.8.0  | 2026-09-04 | AD（跨项目分析） | 治理 R3\~\~R5 结论同步：评审定案（治理文档 v1.1.0）入 §6 治理清单行级联动、状态与 W4 前置更新      |
| v0.9.0  | 2026-09-04 | AD（跨项目分析） | 治理 P0 实施同步：治理文档 v1.2.0（P0 已实施）引用入 §6/§8.3/§9.4，新增 §9.8 同步记录      |
| v0.10.0 | 2026-09-04 | AD（跨项目分析） | 真实契约落地（P1-4+W4 合流）最终状态同步：W4 已实施标注、真实模式开关状态、9.4 门禁更新              |


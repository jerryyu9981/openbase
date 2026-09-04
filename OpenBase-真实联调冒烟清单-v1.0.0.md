# 真实联调冒烟清单（need_* 统一编排 · 沉淀 · 真实契约）v1.1.0

| 属性 | 内容 |
| ---- | ---- |
| 文档编号 | OB-INTG-SMOKE-v1.1.0 |
| 版本 | v1.1.0（草稿 [Draft]，评审结论已并入） |
| 状态 | 待执行（需真实服务环境） |
| 作者 | AD（跨项目分析） |
| 日期 | 2026-09-04 |
| 前置 | 治理 P0（门禁/密钥/X-API-Key/M3 头/端口 8000）；真实契约立项 v1.2.0 Phase A~D 已实施；need_* v0.10.0 / 治理 v1.3.0 / HTML v1.6.0 |
| 输入 | 清单 v1.0.0；评审结论（G1~G4 缺口、T1~T3 收敛、执行性建议，2026-09-04 并入 v1.1.0） |

## 1. 目标与通过标准

目标：在真实服务实例上验证 OpenMemory/OpenRAG/DPS 真实契约、OpenLLM 读侧（画像/检索/记忆上下文）与写侧沉淀（三路回写/流式钩子）端到端可用，为三个真实模式开关置默认提供依据。

通过标准：下列 S-* 用例全部通过；任一失败项记录并修复后重跑；通过后登记"真实模式启用决策"与 DPS /profile/v1 P1 解除。

## 2. 环境准备（起服前）

### 2.1 配置基线（各仓库 .env，禁止明文入库）

| 服务 | 端口（源码默认） | 必配 | 备注 |
| ---- | ---- | ---- | ---- |
| OpenLLM | 8001 | API_KEY_PREFIX 密钥对、OPENMEMORY_/OPENRAG_/DPS_* 地址 | TRUSTED_PROXY_SOURCES 含 openbase-llm-proxy |
| OpenMemory | 按部署 | OPENMEMORY_SERVER_API_KEY（非空，门禁） | X-API-Key 鉴权生效 |
| OpenRAG | 按部署 | OPENRAG_API_SERVICE_API_KEY（非空，门禁）；ALLOW_EMPTY=false | text 端点 /documents/text 存在 |
| DPS | 8000（MCP 8013） | 库可用；org/tenant 预置（org-1/tenant-1 或映射目标）；DPS_DEMO_SEED 按需 | PUT 画像端点仅 v2 可用 |
| OpenBase | 8000 起（视编排） | OPENBASE_DPS_UPSTREAM_BASE 指向真实 DPS | rag 上游按真实 OpenRAG 地址 env 覆盖 |

### 2.2 开关与预置

- OpenLLM：`OPENLLM_OPENMEMORY_REAL=true / OPENLLM_OPENRAG_REAL=true / OPENLLM_DPS_REAL=true`（冒烟期间开，失败即回退 False）；DPS 真实四头（OPENLLM_DPS_REAL_ORG/TENANT/USER/ROLE）按预置实体填。
- OpenBase llm-proxy：确认注入三头；OpenLLM TRUSTED_PROXY_SOURCES 含 openbase-llm-proxy。
- 预置：OpenRAG 建测试集合 kb_smoke_01；OpenMemory 测试用户（与 OpenLLM external 身份对应）；DPS 组织/租户 + 起始 profile 行（calculate 前置 person 存在）；OpenBase 测试账号。

## 3. 冒烟用例矩阵

优先级语义（v1.1.0 新增）：**P0 = 真实模式启用决策的阻塞项**，必须全绿；**P1 = 可选/登记项**，失败不阻塞启用，仅记录。入口准则：五服务 /health 通过、密钥非空校验脚本通过、三真实开关显式开启并确认日志 contract=real 标记、DPS org/tenant 与四头预置一致。出口准则：P0 全绿且 P1 项登记完成。执行性溯源见 §3.7（用例与任务 T*/W* 映射）。

### S0 配置生效自检（P0，v1.1.0 新增）
| 用例 | 校验点 | 期望 |
| ---- | ---- | ---- |
| S0-1 | 三真实开关生效 | OpenLLM 起服日志出现 contract=real（open_memory/open_rag/dps 注入点）；开关确认为 true |
| S0-2 | OpenRAG text 路由存在 | GET /openrag/endpoints（含 X-API-Key）列表含 /api/v1/collections/{collection_id}/documents/text |
| S0-3 | DPS 画像端点可用 | GET /health 通过；v2 路由注册含 PUT /portrait/{person_id}（OpenAPI 列表核对） |
| S0-4 | M3 可信源生效 | OpenLLM 配置 TRUSTED_PROXY_SOURCES 含 openbase-llm-proxy；审计 external 字段初探（见 S5-3） |
| S0-5 | 资源前缀与可重放 | 冒烟资源统一 smoke_ 前缀；脚本可重放（先清理上次残留，S3-2/S4-2 幂等由 hash/唯一键保证） |

### S1 基础探活与门禁（P0）
- S1-1 OpenRAG/OpenMemory 非空密钥下鉴权：无 X-API-Key → 401；正确 → 200（health/受保护端点各一）。
- S1-2 OpenLLM 对三上游地址可达（client ping/health 直测或日志无连接错误）。

### S2 OpenMemory 真实契约（P0）
- S2-1 remember：POST /api/v1/remember 成功（content=response、metadata 含 query、memory_type 翻译：preference→persistent 等按 D1 矩阵）；返回 memory_id。
- S2-2 recall：按 user_id 命中 S2-1 记忆（top_k 过滤生效）；session 分支（带 session_id 仅会话内）。
- S2-3 错误形态：无内容 422 / 错误 X-API-Key 401 → OpenLLM adapter 抛既有组件级异常（不中断主链路）。
- S2-4 写侧端到端：主通道非流式 /chat 成功（memory 组件执行）后，真实 OpenMemory 出现该轮记忆（message_hash 幂等：重放不重复写）。
- S2-5（G4）已知语义对齐：recall 空 query 按真实语义（422 或空结果）断言；session 记忆仅在提供 session_id 时产生（SESSION），不提供则 PERSISTENT。
- S2-6（G4）history 不校验：真实模式 history 返回空列表并 warning 属预期行为（已知限制，不设通过断言）。

### S3 OpenRAG 真实契约（P0）
- S3-1 collections：真实创建/列表经 client（id 与 name 关联）；检索 retrieve 命中（score/元数据正确，客户端按需阈值过滤）。
- S3-2 text 入库端到端：POST /collections/{cid}/documents/text → status=PENDING → 轮询 GET documents/{id} → COMPLETED；重复 content 幂等返回既有文档。
- S3-3 检索可见：入库 COMPLETED 后 retrieve 命中新文本片段。
- S3-4 沉淀端到端：非流式对话成功且 rag 组件执行（kb 指定集合）后，真实集合文档数 +1（ingest_text 通道）；流式（开关 OPENLLM_STREAM_WRITEBACK=true）同理。

### S4 DPS 真实契约（画像）（P0；S4-4 为 P1）
- S4-0（G1）调用通道与角色预置：主路径走 OpenBase dps-proxy（利用 X-User-ID=1 super_admin 绑定）；OpenLLM 直连（OPENLLM_DPS_REAL）需先将所用 X-User-ID 绑定角色（admin/operator 含 portrait:update）并确认 OPENLLM_DPS_REAL_ORG/TENANT/USER/ROLE 与 DPS 预置实体一致；禁止使用 /api/v1 前缀（PUT 恒 403）。
- S4-1 读：calculate（person 预置行）→ get 返回六维与 attrs；OpenLLM 真实模式下 profile 注入正常（routing need_profile/profile_source=dps）。
- S4-2 写：PUT /api/v2/portrait/{person_id}（person 子集 + business.attributes）→ 持久化；重启 DPS 后 GET 仍可见（重启存活）。
- S4-3 四头与归属：缺 X-Org/X-Tenant → 401/403；正确预置实体 + X-User-ID → 200；OpenBase dps-proxy PUT 转发同参数通过。
- S4-4 写回/漂移（P1 可选；D3 联调后启用）：ProfileAdapter update_profile（真实模式）成功；低置信走 drift_recompute 条目逻辑在真实队列落地。

### S5 主链路端到端（OpenBase 入口）（P0）
- S5-1 JWT 登录 → llm-proxy /chat（非流式）：routing 事件含 need_profile/need_memory/need_rag 与真实 profile_source；回答正常。
- S5-2 /chat/stream：SSE 全事件（routing→chunk→done）正常；画像预取前置时序正确。
- S5-3 M3：OpenLLM 审计落库 external_user_id/external_org_id 非空（API Key 通道 + 可信源）；伪造 JWT 头不落库。
- S5-4 沉淀收尾：流式对话结束触发 EvaluateSession 钩子，memory summary 出现在真实 OpenMemory。
- S5-5（G2）llm-only explicit 语义：流式请求不含画像组件 → routing 无 need_profile、服务正常（D-3 语义回归）。
- S5-6（G2）降级路径：OpenRAG 停服 → 主通道检索降级 builtin（rag_source=builtin / degraded 标记），对话不中断。

### S6 旁路与双链路一致性（P0；S6-3 为 P1 登记）
- S6-1 rag-proxy（ChatView 路径）query/stream 可用（OpenRAG 真实地址 + X-API-Key）。
- S6-2 memory-proxy 显式 remember/recall 可用（四头/双头注入正确）。
- S6-3 跨链路一致性冒烟：同一用户主通道沉淀 → 旁路 memory-proxy recall 命中（隔离键形态一致验证）；预期结果记录（若因键形态差异 miss，登记为 P2-1 内网协议头依据）。
- S6-4（T2）P1 登记不阻塞：S4-4 与 S6-3 的差异/失败结果仅记录，不作为真实模式启用决策的阻塞项。

### 3.7 执行性溯源（v1.1.0 新增）

| 用例组 | 溯源 |
| ---- | ---- |
| S0 | 治理 P0（门禁/密钥/M3）；Phase A~C 真实开关（T7） |
| S1 | 治理 P0-1a/P0-1b；P0-3 探活 |
| S2 | 立项 T1/T2（OpenMemory 真实适配与翻译）＋写侧 W2/W3 |
| S3 | 立项 T3/T4（OpenRAG retrieve/text 入库）＋W2 rag 沉淀 |
| S4 | 立项 T5（DPS attributes/PUT/ProfileAdapter 真实模式）＋W2-3/W2-4 写回与漂移 |
| S5 | 读侧 R1~R13（画像/契约/上报）＋写侧 W1~W3＋治理 P0-2（M3） |
| S6 | 双链路拓扑（§2.3）＋治理 R3~R5 结论与 P2-1 依据收集 |

## 4. 失败处理与回滚

- 任一 S 级用例失败：记录（复现步骤/日志/期望 vs 实际），先修复代码或配置；必要时将相关真实模式开关回退 False（stub 分支保留，业务不中断）。
- 环境故障（服务未起/密钥缺失）不算用例失败，单独记录为环境待办。
- 冒烟全程保留日志输出文件（各服务 stdout 定向工作区日志目录）。

## 5. 产物与决策

| 产物 | 说明 |
| ---- | ---- |
| 冒烟执行记录 | 每用例结果（PASS/FAIL/环境待办）+ 证据（请求响应/日志摘录） |
| 真实模式启用决策 | 依据 S2~S6 结果决定三个开关默认值（或按服务拆分启用）与部署文档更新 |
| 解除登记 | DPS /profile/v1 P1 解除（改以真实 /api/v2 能力替代记录）；技术债务表对应条目关闭 |
| 残余立项输入 | S6-3 结果入治理 P2-1（内网统一协议）评估依据 |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
| ---- | ---- | ---- | ---- |
| v1.0.0 | 2026-09-04 | AD（跨项目分析） | 初稿：环境准备与配置基线、S1~S6 冒烟用例矩阵、失败回滚与产物决策 |
| v1.1.0 | 2026-09-04 | AD（跨项目分析） | 评审并入：新增 S0 配置生效自检、优先级（P0/P1）标注、G1~G4 增补用例（S2-5/6、S4-0、S5-5/6、S6-4）、T1~T3 收敛标注、§3.7 执行性溯源、入口/出口准则 |

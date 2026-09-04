# 真实契约落地与沉淀收敛立项方案（P1-4 + W4 合流）v1.2.0

| 属性   | 内容                                                                                                                 |
| ---- | ------------------------------------------------------------------------------------------------------------------ |
| 文档编号 | OB-INTG-REALCONTRACT-P14W4-v1.2.0                                                                                  |
| 版本   | v1.2.0（草稿 \[Draft]，Phase A/B/C 已实施，D 收尾记录完成） |                                                                                     |
| 状态   | 已批准并实施：Phase A/B/C 完成（T1~T5、T7）；Phase D 收尾记录就绪；真实联调待执行 |                                                                      |
| 作者   | AD（跨项目分析）                                                                                                          |
| 日期   | 2026-09-04                                                                                                         |
| 适用范围 | OpenLLM / OpenRAG / OpenMemory / DPS / OpenBase 五仓库（真实契约适配与沉淀通道收敛）                                                 |
| 输入   | 治理文档 v1.2.0（§7 Q1/Q6、§8 P1-4/P2-2）；need\_\* 方案 v0.9.0（§8.3 W4-1~~W4-5）；端点契约调研两份（2026-09-04）；D1~~D4 人工定案（v1.1.0 新增）；Phase A/B/C 实施与 D 收尾记录（v1.2.0 新增） |

## 1. 立项背景与范围

目标：把 OpenLLM 读/写侧对 OpenMemory、OpenRAG、DPS 的调用从 **stub 契约（/openrag/v1、/openmemory/v1）切换到真实 /api/v1（+DPS /api/v2）端点**，并把写侧沉淀通道收敛为真实可用形态；消除"验收基于 stub"债务（v2.14.3 P1、技术债务表登记），打通读侧 R1~~R13 与写侧 W1~~W3 的真实联调。

明确不做：不引入 OpenBase 编排层路线 B；不做治理 P2（内网统一协议头）；不重做 W1\~W3 已实施行为（真实模式仅替换适配层）。

## 2. 真实契约事实（与 stub 的关键差异）

### 2.1 OpenMemory（/api/v1，默认 8000，密钥 OPENMEMORY\_SERVER\_API\_KEY）

| stub（/openmemory/v1）                               | 真实端点                                                                                                                   | 差异要点                                                                                                                                            |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| write {user\_id,query,response} → {write\_id}      | remember {content 必填, memory\_type=auto, user\_id?, session\_id?, agent\_id?, metadata} → MemoryResult{memory\_id,...} | query+response 需拼接为 content；返回 memory\_id；响应无 envelope（HTTPException detail / E-code 两类错误形态并存）                                                  |
| search {user\_id,query,memory\_types}              | recall {query, strategy=auto, user\_id?, session\_id?, agent\_id?, top\_k}                                             | 无 memory\_types 过滤（用 strategy）；无 filters；响应 SearchResult（memory\_id/content/score/memory\_type/metadata/highlights...），无顶层 created\_at/user\_id |
| history/{user\_id}                                 | 无对等端点（GET /memories/{id} 单条；sessions 无 user 维度）                                                                        | 按 user 拉历史需 recall+user\_id 方案                                                                                                                  |
| memory\_type 枚举 episodic/preference/summary/entity | 真实 session/persistent/graph/episode                                                                                    | **枚举不一致，需翻译层**；remember auto 语义=有 session 记 SESSION、否则 PERSISTENT                                                                               |

### 2.2 OpenRAG（/api/v1，默认 8000，密钥 OPENRAG\_API\_SERVICE\_API\_KEY，X-API-Key）

| stub（/openrag/v1）                                                       | 真实端点                                                                                                                                                                            | 差异要点                                                                  |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| search {kb\_id,query,...} → {results}                                   | collections/{collection\_id}/query/retrieve {query,top\_k,retrieval\_strategy,rerank,filters} → envelope data.items\[{chunk\_id,document\_id,collection\_id,content,score,...}] | kb\_id→路径 collection\_id；响应多 envelope；字段名不同；无 score\_threshold（客户端过滤） |
| ingest {kb\_id,documents:\[{content,metadata}]} → {accepted,ingest\_id} | 无 JSON 文本批量入库端点：documents 上传为 multipart 单文件（field=file，异步 PENDING，GET documents/{id} 轮询 status/error\_message）；governance/ingest 仅生命周期登记不真入库                                    | **缺口：自动"文本沉淀"无真实落点**（见决策 D2）                                          |
| collections                                                             | GET/POST collections（id=uuid 与 name 分离）                                                                                                                                         | 需集合创建/查名语义对齐                                                          |

### 2.3 DPS（/api/v2，默认 8000）

- 读可行：POST /api/v2/portrait/calculate（person\_id 必填，先保证行存在）→ GET /api/v2/portrait/{person\_id}（六维 score 列）。

- 写不可持久：画像打标走 /portraits/{person\_id}/tags 仅为进程内存（重启丢失、不参与计算）；REST 无 create/update portrait；storage 写引擎依赖不存在的 db.generate\_id/transaction（疑似死代码）。

- person\_id 由调用方提供（UNIQUE(person\_id, tenant\_id)），profile 无 user 绑定字段 → 需 person\_id=OpenBase 用户规约。

- 归属强制：X-Org-ID/X-Tenant-ID 必须命中库实体（否则 403/401）；X-User-ID 与 RBAC 必传；维度键三套命名不一致。

- /profile/v1/get|update|dimensions 在真实 DPS 无实现（既有结论），且既有画像 API 无法承载 ProfileAdapter 的 person/business 写语义。

## 3. 工作分解（W4-1\~W4-5 + P1-4）

| #  | 任务                                                                                                                                | 归属仓库                 | 关键落点（参考现文件）                                                                                                         | 验收要点                                               |
| -- | --------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| T1 | OpenMemory 客户端转真实：remember/recall 适配（base=/api/v1；content 拼接；错误双形态解析）                                                             | OpenLLM              | edgerouter\adapters\openmemory\_client.py、openmemory.py；配置 OPENMEMORY\_\*（对齐真实 OPENMEMORY\_SERVER\_API\_KEY / host） | 单测 + 真实 OpenMemory 联调用例（stub 关闭态）；write/recall 往返  |
| T2 | memory\_type 翻译层：内部 episodic/preference/summary/entity ↔ 真实 session/persistent/graph/episode（决策 D1 定映射；remember 缺省语义改 persistent） | OpenLLM              | openmemory\_client/adapter、writeback 校验与 W2 默认值                                                                     | 翻译矩阵单测；默认值回归（原 episodic→新语义）                       |
| T3 | OpenRAG retrieve 转真实：kb/集合 id 对齐、envelope 解析、score 客户端过滤                                                                          | OpenLLM              | edgerouter\adapters\openrag\_client.py、openrag.py（\_isolate\_kb\_id 语义保留）                                           | 单测 + retrieve 联调；filters 语法对账                      |
| T4 | 知识沉淀通道：真实文本入库落点（决策 D2 定形态；倾向 OpenRAG 新增 JSON 文本端点走同一异步索引）                                                                         | OpenRAG、OpenLLM      | OpenRAG api\routes\documents.py（新增 text 路由或复用 BackgroundTasks 链）；\_rag\_writeback 改调真实通道                            | 端到端：写入→PENDING→轮询 COMPLETED；幂等（去重沿用 message\_hash） |
| T5 | 画像契约最小集：读=calculate+get；写=决策 D3（倾向 DPS 补持久化 PUT/落库并修复写路径），ProfileAdapter 真实模式与四头注入；写回/漂移开关至联调后启用                                  | DPS、OpenLLM、OpenBase | DPS rest\_api routes/database/storage；OpenLLM adapters\profile.py/dps\_client.py；OpenBase dps\_proxy 暴露新端点与头        | 画像读联调；写持久化重启存活；person\_id=用户规约文档化                  |
| T6 | 旁路沉淀归属落地（决策 D4 定范围）：责任矩阵文档 + 显式沉淀通道（memory-proxy remember 为主）                                                                     | OpenBase、OpenLLM     | OpenBase modules\proxy\memory\_proxy.py（现有 remember 即通道）；ChatView 旁路不自动沉淀的语义固化                                      | 责任矩阵文档；跨链路身份一致性用例（P0 后 external 头场景）               |
| T7 | stub 兼容分支：保留本地离线测试，标注 Deprecated 与真实模式开关（config OPENLLM\_\*\_REAL\_MODE 之类缺省联调后默认真实）                                              | OpenLLM              | mock\_services 注释与客户端分支选择                                                                                           | 切换测试：stub/真实两态全绿                                   |
| T8 | 收尾与文档：W4-5 写侧一致性核对清单（已实施项 P0/W1-6 复核）；上游地址对账（OpenRAG 8000 vs OpenBase 配置 8010、OpenMemory 8020、DPS 8000）                           | OpenBase、OpenLLM     | settings/环境注入说明                                                                                                     | 核对清单入立项验收记录                                        |

## 4. 阶段与依赖

| 阶段                   | 内容                                            | 依赖                              |
| -------------------- | --------------------------------------------- | ------------------------------- |
| Phase A（T1/T2/T7 先行） | OpenMemory 真实契约适配 + memory\_type 翻译 + stub 分支 | 决策 D1；治理 P0-1b 已具备（X-API-Key 头） |
| Phase B（T3/T4）       | OpenRAG retrieve 适配 + 文本入库端点                  | 决策 D2；治理 P0-1a/1b 已具备           |
| Phase C（T5）          | DPS 画像最小契约与 ProfileAdapter 真实模式               | 决策 D3；需 DPS 侧立项配合               |
| Phase D（T6/T8）       | 旁路沉淀矩阵、写侧一致性核对与收尾                             | 决策 D4；A\~C 联调结果回填               |

依赖说明：治理 P0（门禁/出站 X-API-Key/M3 头/端口）已实施，为真实联调前提；本立项不含 P1-2/P1-3（tenant/code 收敛），其影响仅在后续统一时再次触碰适配层。

## 5. 决策点（需人工定案）

| #  | 决策点                  | 选项与建议                                                                                                                                                                                           |
| -- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 | memory\_type 映射与默认语义 | 建议：内部白名单保留（避免破坏 W2 校验），翻译 episodic→episode、preference→persistent、summary→session（带 session\_id）/persistent、entity→graph；remember 缺省从 episodic 改 persistent（与真实 auto 无 session 语义一致），并在联调确认映射正确性 |
| D2 | OpenRAG 文本沉淀落点形态     | 建议 A：OpenRAG 新增 JSON 文本端点（如 POST /collections/{cid}/documents/text，content+metadata→ 同一异步索引链），语义最贴近现状"文本沉淀"；选项 B：仅文档上传（临时文件 multipart），无新增端点但语义错位（文本需落临时文件）                                     |
| D3 | DPS 画像写侧范围           | 建议 A（最小可行写）：DPS 补持久化 PUT /api/v2/portrait/{person\_id}（落库 profile 字段子集）+ 修复写路径；ProfileAdapter 写/漂移在联调后启用；选项 B：仅读（calculate/get），写回与漂移在 DPS 契约补齐前保持关闭并登记（W2/W3 已实现逻辑不受影响）                        |
| D4 | 旁路沉淀范围               | 建议最小集：责任矩阵文档 + 显式 memory-proxy remember/improve 通道 + ChatView 语义固化；服务端会话总结编排器（session-summary）单独立项评估（避免本立项膨胀）                                                                                   |

### 5.1 决策定案记录（v1.1.0，人工批准 2026-09-04）

| 决策 | 定案                                                                                                                                                                           |
| -- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 | 按建议：内部白名单保留，翻译 episodic→episode、preference→persistent、summary→session（带 session\_id）否则 persistent、entity→graph；remember 缺省改 persistent（与真实 auto 无 session 语义一致）；映射正确性以联调用例确认 |
| D2 | 按建议 A：OpenRAG 新增 JSON 文本入库端点（POST /collections/{cid}/documents/text，content+metadata，复用同一异步索引链与状态轮询）                                                                         |
| D3 | 按建议 A：DPS 补持久化 PUT /api/v2/portrait/{person\_id}（落库 profile 字段子集）并修复/启用写路径；ProfileAdapter 写回与漂移在真实联调通过后启用                                                                    |
| D4 | 按最小集：责任矩阵文档 + 显式 memory-proxy remember/improve 通道 + ChatView 语义固化；session-summary 服务端编排器单独立项                                                                                 |

## 6. 测试与验收策略

- 真实联调环境：OpenMemory/OpenRAG 以非空密钥启动（P0-1a 门禁后的配置基准确认）；OpenLLM 真实模式开关指向真实地址。

- 用例矩阵：每任务单测（stub 态回归）+ 集成联调（真实态）；T4 端到端（写入→PENDING→COMPLETED 轮询）；T5 写持久化重启存活用例；T6 跨链路身份一致性冒烟（P0-2 external 头生效后 recall 命中）。

- 回归护栏：need\_\* 方案 §9 各实施批次对应测试文件保持全绿（OpenLLM）；OpenBase/OpenRAG/OpenMemory 各自相关子集。

## 7. 实施进度与收尾记录（v1.2.0）

### 7.1 Phase A/B/C 实施结果（2026-09-04，均按 TDD）

| 阶段 | 落地 | 验证 |
| ---- | ---- | ---- |
| Phase A（T1/T2/T7） | OPENLLM_OPENMEMORY_REAL（默认 False）：remember/recall 真实方法族、D1 翻译表（episodic→episode、preference→persistent、summary→session/persistent、entity→graph，缺省 persistent）、history 真实态返回空+warning、错误双形态；stub 标注 Deprecated | 30 新增用例；回归 164 passed；ruff 0 |
| Phase B1（T4 端点） | OpenRAG POST /collections/{cid}/documents/text（JSON，复用异步索引链与 sha256 去重，PENDING 轮询） | 9 新增用例；回归 110 passed（3 个前置失败与本次无关） |
| Phase B2（T3/T4 客户端） | OPENLLM_OPENRAG_REAL（默认 False）：retrieve→/collections/{cid}/query/retrieve、ingest_text→text 端点、get_document 轮询、collections id/name 关联；真实模式取消 {org}_ 前缀改写（上游集合全局唯一 id + 治理承接，取舍注释）；_rag_writeback 真实态 ingest_text 提交不阻塞轮询 | 28 新增用例；回归 209 passed；ruff 0 |
| Phase C1（T5 DPS） | profile 双后端新增 attributes_json（PG JSONB/SQLite TEXT，幂等演进 init_schema 内）；PUT /api/v2/portrait/{person_id}（person 白名单子集列 + business.attributes 整体覆盖、服务端取 contextvar 归属、404/缓存失效/version+updated_at 服务端维护）；未触碰遗留写引擎 | 14 新增用例（含真实 SQLite 持久化重启存活）；回归 32 passed；ast 0 错误 |
| Phase C2（T5 OpenLLM+OpenBase） | OPENLLM_DPS_REAL（默认 False）与四头配置；dps_client profile_read（calculate→get）/profile_update（PUT）；ProfileAdapter 真实分支（person_id=external 优先规约、data/updates 键映射文档化）；网关注入+contract 日志；OpenBase dps-proxy 新增 PUT /portraits/{person_id} 转发；profile_stub 标 Deprecated | 22 新增用例；回归 141+21 passed；OpenBase 20 passed；ruff 0 |

### 7.2 旁路沉淀责任矩阵（T6，D4 最小集）

| 会话类型 | 链路 | 沉淀通道 | 触发方 | 状态 |
| ---- | ---- | ---- | ---- | ---- |
| 主通道非流式对话 | llm-proxy → OpenLLM /chat | memory/rag/profile 三路回写（W2） | OpenLLM 编排（自动） | 已实现（stub 契约模式；真实模式开关待联调） |
| 主通道流式对话 | llm-proxy → OpenLLM /chat/stream | W3 finalize 钩子（OPENLLM_STREAM_WRITEBACK） | OpenLLM 编排（开关默认关） | 已实现 |
| 旁路 RAG 问答（ChatView） | rag-proxy → OpenRAG | 不自动沉淀（前端无收藏入口，语义固化：只检索不沉淀） | — | 固化（本阶段不改 UI） |
| 旁路显式记忆 | memory-proxy /remember、/improve | OpenBase memory 模块页面/调用方显式 | 已存在（显式通道） | 已确认 |
| 知识管理式入库 | rag-proxy documents 上传 / OpenRAG 管理面 | 文档上传（PENDING 异步）/本立项新增 documents/text | 管理面/沉淀方显式 | 已具备 |
| 画像显式写回 | dps-proxy PUT portraits/{id} | OpenBase dps-proxy 新路由 | 显式（OpenLLM 真实模式写/漂移联调后启用） | 已具备（v2 前缀） |

结论：主通道沉淀归 OpenLLM 编排；旁路沉淀最小集=显式 memory-proxy + 管理式知识入库 + dps-proxy PUT；ChatView 不自动沉淀；session-summary 服务端编排器未纳入本立项（另行评估）。

### 7.3 写侧一致性核对与地址对账（T8）

一致性核对（已具备/已实施）：写回 RequestContext org 前缀（W1-6）；自动回写 message_hash 幂等（W1-4）；出站 X-API-Key 统一（P0-1b）；M3 external 身份解析到请求上下文（P0-2）——真实模式 person_id 优先 external_user_id。待联调确认：memory_type 翻译正确性、真实 OpenMemory/OpenRAG 往返、DPS attributes 可见性。

地址对账（部署配置项，代码注释已提示）：

| 上游 | 源码默认 | OpenBase/OpenLLM 配置现状 | 处理 |
| ---- | ---- | ---- | ---- |
| OpenLLM | 8001 | llm 8001 | 一致 |
| OpenRAG | 8000 | OpenBase 配置 8010（stub 用） | 真实部署需 env 指向 8000（或部署端口） |
| OpenMemory | 8000 | OpenBase 配置 8020 | 真实部署按实际端口 env 覆盖（8020 或默认 8000） |
| DPS | 8000（MCP 8013） | P0-3 已对齐 8000 | 一致 |

### 7.4 残余项与风险（如实登记）

1. 真实联调（真实服务实例）未执行：本阶段全部为单测/自检，真实态开关（OPENLLM_OPENMEMORY_REAL / OPENRAG_REAL / DPS_REAL）需在真实环境冒烟后置默认或明确部署启用。
2. DPS 侧未跑：PG 后端实写（含 JSONB）、真实 Redis 缓存、PERMISSION_ENABLED 开启态 RBAC、/api/v1 前缀 PUT（恒 403 已文档化）。
3. OpenRAG 前置失败用例 3 个与 P0 前状态枚举大小写等历史问题相关，未在本立项修复。
4. 测试环境临时处理（已还原）：为绕开 pgAdmin Python site-packages 中 rich 包损坏曾建立用户 site-packages junction（指向 OpenLLM .pylib\rich）；已删除 junction（[System.IO.Directory]::Delete 链接本体，目标目录完好），pgAdmin rich 现可正常导入（import rich 验证通过）。
5. DPS 既有写链（storage/annotation/version/track）与 profile_tag 读链列假设两后端不符等历史漂移未修复（超出本立项），已登记待后续治理。

## 8. 修订历史

| 版本     | 日期         | 修改人       | 摘要                                                                 |
| ------ | ---------- | --------- | ------------------------------------------------------------------ |
| v1.0.0 | 2026-09-04 | AD（跨项目分析） | 初稿：契约差异事实（OpenMemory/OpenRAG/DPS）、工作分解 T1~~T8、阶段依赖、决策点 D1~~D4、验收策略 |
| v1.1.0 | 2026-09-04 | AD（跨项目分析） | D1~D4 人工定案（§5.1），状态转已批准并启动 Phase A/B 实施 |
| v1.2.0 | 2026-09-04 | AD（跨项目分析） | Phase A/B/C 实施结果与 Phase D 收尾记录（§7）：旁路沉淀责任矩阵、一致性核对与地址对账、残余项登记 |                          |


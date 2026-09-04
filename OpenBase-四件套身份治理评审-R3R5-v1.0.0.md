# 四件套身份隔离治理评审（R3\~R5）v1.5.0

| 属性   | 内容                                                                                                                         |
| ---- | -------------------------------------------------------------------------------------------------------------------------- |
| 文档编号 | OB-INTG-IDENT-GOV-R3R5-v1.3.0                                                                                              |
| 版本   | v1.3.0（草稿 \[Draft]，决策已定；P0/P1-4 已实施）                                                                                       |
| 状态   | 已决策；P0 已实施（2026-09-04）；P1-4 已实施（与 W4 合流，立项方案 v1.2.0）；P1-1\~P1-3 与 P2 待立项                                                   |
| 作者   | AD（跨项目分析）                                                                                                                  |
| 日期   | 2026-09-04                                                                                                                 |
| 适用范围 | OpenBase / OpenLLM / OpenRAG / OpenMemory / DPS 五仓库身份与凭据语义                                                                 |
| 输入   | 方案 v0.8.0 治理清单 §6（R1~~R6）；双链路拓扑约束（主通道/旁路）；两个只读取证报告；Q1~~Q6 利弊展开与决策定案（v1.1.0 新增）；P0 批次实施回写（v1.2.0 新增）；P1-4 合流实施同步（v1.3.0 新增） |

## 1. 评审范围与结论摘要

范围：治理清单 R3（user\_id 双标识）、R4（org/tenant 串味）、R5（凭据通道碎片），仅评审不改码，输出目标态、决策档位与优先级，供跨仓库立项。

核心结论：四件套体系当前**不存在一个可通行的公共身份/凭据协议**——同一用户在主通道与旁路落到不同隔离键（记忆互相不可见），org\_id 一个头名四处语义，各上游鉴权默认态与调用方假设普遍不符（多个默认无鉴权或伪凭据旁路）。此状态是 W4 与"旁路上线检查"的前置阻塞项，建议按本文 §7 决策后立项治理，其中 P0 项应在部署基线前完成。

## 2. 关键事实（消费端实证矩阵）

| 服务         | 默认鉴权态                              | 消费凭据/头                                       | 受保护范围                       | 隔离键模型                                     | 兜底行为                         |
| ---------- | ---------------------------------- | -------------------------------------------- | --------------------------- | ----------------------------------------- | ---------------------------- |
| OpenRAG    | 默认无鉴权（service\_api\_key 空则跳过）      | 仅 X-API-Key；bypass: 前缀免密钥                    | /api/v1 减去 /api/v1/system 等 | 无隔离键（Collection/Document 无 org 字段，裸 uuid） | 未配 key 放行；bypass 放行          |
| OpenMemory | 默认无鉴权（RBAC/ABAC/Gateway/多租户全关）     | 可选 X-API-Key；开启时 X-Org-ID/X-User-ID 或 Bearer | /api/v1、/metrics（配 key 后）   | 裸 user\_id 可选过滤（不传即全量召回）                  | 组织无策略放行；回落 default/anonymous |
| DPS        | 业务端点无 Bearer/API-Key，身份头强校验        | X-Org-ID/X-Tenant-ID/X-User-ID/X-User-Role   | 除 health/auth/org 创建外全部     | org+tenant 库实体存在性 + 可选 tenant 过滤          | 未知 org 403、缺头 401；DB 故障降级放行  |
| OpenLLM    | 仅消费 Authorization（API Key 或自有 JWT） | Bearer；不解析 X-User-ID/X-Org-ID                | /openllm/v1                 | 内部 user(UUID) + {org\_id}\_ 前缀            | API Key 属主归一                 |

关键差异（与调用方假设不符）：OpenRAG 的 X-API-Key 默认不生效且 bypass 为伪凭据；OpenMemory 无 /openmemory/v1/write 与 /history，但存在**无用户隔离的 /sessions 端点族**；DPS 端口源码为 8000（MCP 8013），此前配置假设 8030 **无源码证据，需对账**；DPS 启动硬绑 user\_id=1 为 super\_admin。

## 3. 问题定性

### 3.1 R3 user\_id 双标识

证据：OpenBase JWT sub=本地用户 int id（auth login）；memory\_proxy/dps\_proxy 以裸 sub 作 X-User-ID（memory\_proxy.py:91、dps\_proxy.py:106）；llm\_proxy 不转发任何身份，OpenLLM 侧以 API Key 属主 UUID 为 user，RequestContext 拼 {org\_id}\_{user\_id}（openllm\_gateway.py:249），并作为 OpenMemory/OpenRAG/DPS 出站键；DPS 侧启动硬绑"X-User-ID=1 → super\_admin"。

影响：

1. 同一用户主通道键=裸 sub（如 "42"），旁路键={OpenLLM org}\_{OpenLLM user UUID}——两链路记忆/知识互不可见。
2. 旁路终端用户被 API Key 属主归一化：多 OpenBase 用户共享一键即共享一命名空间，审计无法回溯真实用户。
3. DPS 硬绑 id=1 属"头注入信任"，任何调用方伪造 X-User-ID=1 即获 super\_admin（DPS 侧无独立校验）。
4. OpenLLM 画像出站 user\_id 再加 {org}\_ 前缀（profile.py:42-49），与 DPS 主通道 X-User-ID 形态再次分裂。

### 3.2 R4 org/tenant 串味

证据：login/refresh/OIDC 四处 org\_id==tenant\_id 同值签发（auth login extra={"org\_id": tenant\_value}）；值取 tenants.id（数字），而 OIDC 绑定时用 Tenant.code 查找——键值语义错位；OpenBase "org 模块"实为部门树，JWT org\_id 与其无关；OpenLLM organization\_id=其自有 tenants.id（UUID）；DPS X-Org-ID=DPS 库组织——X-Org-ID 一个头名四处语义。

影响：dps\_org\_map/dps\_tenant\_map（OpenBase 值→DPS 值）若按 Tenant.code 配置将永不命中（输入是数字 id）；同值签发使测试夹具中"org≠tenant"的拆分形态在生产不可达；默认兜底 openbase-default/default 属弱隔离。DPS 要求 org/tenant 双实体预存且关联，OpenBase 同值签发仅在 DPS 侧恰好同码时可用。

### 3.3 R5 凭据通道碎片

证据：9 类通道鉴权形态各异（memory\_proxy 双头、rag\_proxy X-API-Key、dps\_proxy 身份头、llm\_proxy Bearer、OpenLLM→三上游 无鉴权/可选 Bearer）；OpenRAG bypass: 前缀免密钥；OpenMemory 三种凭据通道并存且默认全关；DPS 无 API-Key/Bearer 校验、两处 fail-open（DB 故障、权限引擎未初始化）；共享静态默认密钥即生产种子值；llm\_proxy 不发 M3 头且 OpenLLM TRUSTED\_PROXY\_SOURCES 默认空 → 外部身份归属恒空。

影响：同上游两种头方案（OpenRAG：主通道 X-API-Key vs 旁路 Bearer）；内部直连默认无凭据防线；归属审计空转；任一默认密钥泄露即伪造全通道。

## 4. 同一用户跨链路推演（不一致实证）

样本身份：OpenBase users.id=42、tenants.id=3（code=acme）。

| 维度             | 主通道（proxy 直连）      | 旁路（llm\_proxy → OpenLLM → 上游） | 一致性 |
| -------------- | ------------------ | ----------------------------- | --- |
| OpenMemory 用户键 | 42（裸 sub）          | org-xxxx-uuid\_9f8e…-uuid     | 不一致 |
| OpenRAG kb 标识  | 裸集合名（无前缀）          | {org}\_ 前缀                    | 不一致 |
| DPS 组织/用户      | 42 / 3（或映射后 DPS 码） | OpenLLM org 前缀体系              | 不一致 |
| 终端用户可辨识        | 可（sub 直达）          | 不可（API Key 属主归一）              | 不一致 |

## 5. 目标态与决策档位

### 5.1 R3（跨链路身份同形 + 可辨识）

| 档位       | 方案                                                                                                                                                                  | 归属               | 影响               |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ---------------- |
| 最小（推荐起步） | 旁路内部 user 键保留 {org}\_ 前缀的同时，新增外部身份映射层：llm\_proxy 注入 X-User-ID(sub)/X-Org-ID 并经 OpenLLM 可信源解析绑定（TRUSTED\_PROXY\_SOURCES + X-Proxy-Source），旁路出站键与主通道 sub 语义对齐或显式双键映射表 | OpenBase+OpenLLM | 打通两链路键映射，可辨识终端用户 |
| 完整       | 统一"内网身份协议头"（external user/org），五个仓库全部消费同形键                                                                                                                          | 全仓               | 根治，工作量最大         |

### 5.2 R4（org/tenant 语义收敛）

方向：① 明确唯一租户键（tenants.code 或 id 择一贯穿签发与映射表），org 头降级为"别名/兼容"或正式引入独立 org 实体；② DPS 映射表键按统一后的租户值对齐；③ 默认兜底改 fail-closed 或显式配置化。待 Q2/Q3 决策。

### 5.3 R5（凭据统一与信任链）

方向：① 内部直连（OpenLLM→OpenRAG/OpenMemory/DPS）统一 X-API-Key 形态并纳入部署基线（密钥为空时启动告警/拒绝，移除 bypass 伪凭据或要求同密钥）；② llm\_proxy 增投 X-User-ID/X-Org-ID/X-Proxy-Source，OpenLLM 配置可信源（联动 R3 最小档与 M3）；③ 共享默认密钥改环境注入/运行时生成；④ DPS fail-open 两处与 id=1 硬绑治理；⑤ 端口对账（8000 vs 8030）。

## 6. 优先级与执行建议

| 级别         | 事项                                                                                                           | 备注          |
| ---------- | ------------------------------------------------------------------------------------------------------------ | ----------- |
| P0（部署基线前置） | OpenRAG/OpenMemory 密钥配置化与空密钥启动门禁；bypass 伪凭据处置；DPS 端口与 8030 配置对账；M3 归属头链路打通（R3 最小档 + TRUSTED\_PROXY\_SOURCES） | 与旁路上线检查直接相关 |
| P1         | org/tenant 语义收敛（Q2/Q3 定案后）；dps\_org\_map/dps\_tenant\_map 键对齐；DPS fail-open 与 id=1 硬绑治理                      | 跨仓库立项       |
| P2         | 内网统一身份协议头（5.1 完整档）；OpenMemory sessions 隔离与 /openmemory/v1 契约落地（衔接 W4-1/W4-2/W4-3）                            | 长期          |

## 7. 决策记录（v1.1.0）

| 决策点              | 定案                                                                                        | 理由要点                                                                                                      |
| ---------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Q1 内部直连凭据        | 统一 X-API-Key 并加空密钥门禁，分两步（先门禁后统一头）                                                         | 与 OpenBase 侧 rag/memory-proxy 通道同形；OpenRAG 只认 X-API-Key；先门禁根治"默认无鉴权部署"，统一头与 Q6 契约落地合流；DPS 依赖身份头校验不强行造 key |
| Q2 org/tenant 拆分 | 不拆分：明确 tenant 为唯一租户键，org 头退役为兼容别名                                                         | 当前无独立 org 产品诉求（YAGNI）；拆分成本最高且波及全链路；同值双键错位可即时消除                                                            |
| Q3 租户键形态         | 对外统一为 tenants.code，内部 FK 保留 id                                                            | code 跨系统稳定、DPS/IdP 天然对齐；映射表语义正确；存量 token 过期自然收敛，存量映射配置与审计展示兼容列入迁移清单                                       |
| Q4 旁路可辨识         | 最小档起步（llm\_proxy 投 X-User-ID/X-Org-ID/X-Proxy-Source + OpenLLM 可信源解析），完整档入 P2 路线图         | 打通 M3 归属与终端用户可辨识，改动集中在两仓网关层；避免在 Q2/Q3 未定型前做全仓协议重构                                                         |
| Q5 DPS 端口        | OpenBase 配置对齐 DPS 源码默认 8000（MCP 8013），部署层兜底复核                                             | 源码为准（全仓无 8030）；一行配置修复；真实环境端口映射属部署清单问题，启动探活校验 /health                                                      |
| Q6 stub 契约去留     | 转真实实现并保留兼容分支：先 OpenMemory（/api/v1/remember、/recall）后 OpenRAG（检索对账先行，documents/governance） | 消除"验收基于 stub"债务；与 W4-1/W4-2 合流处理路径/模型/凭据；兼容分支供本地离线测试并标注 Deprecated                                        |

## 8. 立项路线图（v1.1.0 定案；P0 已实施，实施记录见 §9）

| 级别   | 事项                                                                                               | 归属仓库                       | 关键改动面                                                     | 依赖/联动           | 状态                                                     |
| ---- | ------------------------------------------------------------------------------------------------ | -------------------------- | --------------------------------------------------------- | --------------- | ------------------------------------------------------ |
| P0-1 | OpenRAG/OpenMemory 空密钥启动门禁；OpenLLM 三上游客户端补/统一 X-API-Key 头（门禁先行）                                  | OpenRAG、OpenMemory、OpenLLM | settings/config 校验；openmemory\_client/openrag\_client 头注入 | Q1 步骤 1；部署基线前置  | 已实施                                                    |
| P0-2 | llm\_proxy 注入 X-User-ID/X-Org-ID/X-Proxy-Source；OpenLLM 配置 TRUSTED\_PROXY\_SOURCES 并解析外部身份到请求上下文 | OpenBase、OpenLLM           | llm\_proxy 头字典；openllm\_gateway identity/审计提取             | Q4 最小档；M3 归属打通  | 已实施                                                    |
| P0-3 | DPS 端口对齐：OpenBase dps\_upstream\_base 按实际 8000 修正并加 /health 探活校验                                 | OpenBase                   | settings + 启动探活                                           | Q5              | 已实施                                                    |
| P1-1 | OpenLLM 出站统一 X-API-Key（含 writeback 消费端）                                                          | OpenLLM                    | 三 client 鉴权形态收敛；config 密钥字段                               | Q1 步骤 2         | 已实施（并入 P0-1b：OpenLLM 出站统一 X-API-Key 头，含 writeback 消费端） |
| P1-2 | tenant 唯一 + org 头兼容别名：签发/代理层去 org 双键语义，dps\_org\_map 停用                                          | OpenBase、DPS               | auth/oidc/proxy 头构造；DPS 侧 org 校验策略                        | Q2              | 待立项                                                    |
| P1-3 | 对外租户键切 code：签发、身份头、映射表；存量迁移清单                                                                    | OpenBase、DPS               | JWT claims 与 proxy 映射取值；迁移与兼容                             | Q3；Q5/Q1 后置对齐   | 待立项                                                    |
| P1-4 | stub 契约转真实：OpenMemory /api/v1/remember+recall 客户端适配与隔离键语义修正；OpenRAG 检索对账后适配 /api/v1              | OpenLLM、OpenMemory、OpenRAG | openmemory\_client/openrag\_client；OpenRAG search 对账      | Q6；衔接 W4-1/W4-2 | 已实施（与 W4 合流，立项方案 v1.2.0 Phase A\~D）                    |
| P2-1 | 内网统一身份协议头（external user/org 同形键全仓消费）                                                             | 五仓库                        | 各上游隔离键重构                                                  | Q2/Q3 定案后评估     | 待立项                                                    |
| P2-2 | OpenMemory /sessions 端点隔离与归属校验；DPS fail-open 两处与 X-User-ID=1 硬绑治理                                | OpenMemory、DPS             | sessions 过滤；中间件 fail-closed                               | 与 P1-4 同批次评估    | 待立项                                                    |

## 9. P0 实施记录（v1.2.0）

| 项     | 落地行为                                                                                                                                                                                                                                                                      | 验证                                                                |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| P0-1a | OpenRAG：allow\_empty\_service\_key 默认 False + 启动 fail-fast（生产态放行开关无效）；bypass 伪凭据收敛为 hmac 精确匹配 bypass\_api\_key（未配置则旁路关闭）。OpenMemory：allow\_empty\_api\_key 同语义门禁                                                                                                          | OpenRAG 346 passed；OpenMemory 161+22 passed；语法全量 0 错误             |
| P0-1b | OpenLLM 新增 OPENMEMORY\_API\_KEY（空带头兼容）；set\_auth\_header 由 Bearer 切 X-API-Key（OpenRAG 中间件只读该头）；writeback 经同 adapter 自动继承                                                                                                                                                  | 81 passed（新增 11），ruff 0；1 处既有断言改名已记录                              |
| P0-3  | dps\_upstream\_base 默认 8000（注释环境覆盖）；dps\_health\_check\_enabled/interval 与惰性 /health 探活（fail-open 降级、节流去重）；编排 ps1 显式覆盖 8030                                                                                                                                               | 26+74 passed；ruff/compileall OK；探活新增分支全覆盖                         |
| P0-2  | OpenBase llm\_proxy 仅当可解析 JWT 身份时注入 X-User-ID/X-Org-ID/X-Proxy-Source(openbase-llm-proxy)。OpenLLM：TRUSTED\_PROXY\_SOURCES 默认含 openbase-llm-proxy；services/external\_identity.py 收敛解析（API Key 通道+可信源+头存在才解析，防伪造）；GatewayIdentity/RequestContext 携带 external 字段（默认 None 兼容） | OpenBase 26 passed；OpenLLM 101+135+272 passed；ruff 通过（存量违规净减，未新增） |

遗留与注意事项：OpenLLM 本地 .env 的 TRUSTED\_PROXY\_SOURCES 需在真实部署补 openbase-llm-proxy（部署配置项）；OpenBase PROXY\_SYSTEMS\["dps"] 通用通道仍默认 8030（与 R-381 dps-proxy 独立，建议 P 项跟进）；OpenRAG 仓根未跟踪 .env 含真实 key，部署应改环境注入管理；决策文档文件名仍为 v1.0.0 基线（文件内修订至 v1.2.0）。

### 9.1 P1-4 合流实施记录（v1.3.0）

P1-4（stub 契约转真实）已与 need\_\* 方案 W4 合流实施完毕：见《真实契约落地与沉淀收敛立项方案》v1.2.0 §7——Phase A（OpenMemory remember/recall 真实适配与 memory\_type 翻译）、Phase B（OpenRAG text 入库端点 + retrieve/ingest\_text 客户端）、Phase C（DPS attributes\_json 演进与 PUT 画像端点 + ProfileAdapter 真实模式 + OpenBase dps-proxy PUT 转发）、Phase D（旁路沉淀责任矩阵与收尾）。真实模式开关（OPENLLM\_OPENMEMORY\_REAL / OPENRAG\_REAL / DPS\_REAL）缺省 False，真实服务联调待执行；残余项登记于立项方案 §7.4。

### 9.2 真实联调遗留登记（v1.4.0；L-2 已解除 v1.5.0）

按 `.env.shared-infra` 共享基础设施启动五件套执行冒烟（清单《真实联调冒烟清单》v1.1.0，S0\~S6）后登记遗留：

| 编号  | 遗留                                 | 现象与根因                                                                                                                   | 修复方向/状态                                                                                                          | 关联                                |
| --- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| L-1 | DPS PG 方言缺陷                        | 真实 PG 下 `/api/v2/portrait/calc`、`get`、`put` 均 500 INTERNAL\_ERROR；根因为 SQL 使用 qmark 风格 `?` 占位符（散布约 30 文件），PG 后端需 `$1` 风格 | 在 DPS `database.py` 增加方言适配层后全量回归（P1 修复项）；冒烟期临时解除=SQLite 回退模式                                                     | 治理 P1-2/P1-3 同批次；冒烟 S4 阻塞项        |
| L-2 | ~~S5 生成侧模型配置~~ **已解除（2026-09-04）** | 根因=冒烟载荷模型 `test-model` 未注册 + `qwen3:0.6b` 提供方本机 Ollama 未运行                                                              | 换用真实模型 `llama3.2:1b`（Ollama LAN 192.168.0.4）经 llm-proxy→OpenLLM 全链路实证 `routing→21×chunk→done` 通过；模型注册表位于共享库 nuct | 冒烟 S5 解除；自动化用例读取超时需放宽 ≥120s（可选跟进） |
| L-3 | S2 直连密钥形态                          | OpenMemory 直连 X-API-Key 401；真实写链路已由 S6-2（memory-proxy→remember 返回 memory\_id）验证通过                                       | 结论：纯 X-API-Key 直连非受支持形态；S2 以 S6-2 替代验证收口                                                                         | 冒烟 S2                             |

冒烟已验证通过项：S0/S1 门禁、S3 OpenRAG 真实文本入库→COMPLETED→检索端到端、S6-1 rag-proxy、S6-2 memory-proxy 显式沉淀；OpenBase JWT 门禁与编排 27 项健康检查。

## 10. 修订历史

| 版本     | 日期         | 修改人       | 摘要                                                                                                   |
| ------ | ---------- | --------- | ---------------------------------------------------------------------------------------------------- |
| v1.0.0 | 2026-09-04 | AD（跨项目分析） | 初稿：R3~~R5 消费端实证、问题定性、跨链路推演、决策档位与优先级、待决策点 Q1~~Q6                                                      |
| v1.1.0 | 2026-09-04 | AD（跨项目分析） | 决策定案回写：Q1\~Q6 决策记录（§7）、立项路线图 P0/P1/P2（§8）、状态转已决策待立项                                                  |
| v1.2.0 | 2026-09-04 | AD（跨项目分析） | P0 实施完成回写：P0-1/P0-2/P0-3 落地行为与验证（§9）、路线图 P0 标注已实施、状态更新                                               |
| v1.3.0 | 2026-09-04 | AD（跨项目分析） | P1-4 合流实施同步（§9.1）：与 W4 合流完成 Phase A\~D；路线图 P1-1/P1-4 标注已实施；状态更新                                      |
| v1.4.0 | 2026-09-04 | AD（跨项目分析） | 真实联调遗留登记（§9.2）：L-1 DPS PG 方言缺陷、L-2 S5 模型配置、L-3 S2 直连密钥形态；冒烟通过项记录                                     |
| v1.5.0 | 2026-09-04 | AD（跨项目分析） | L-2 解除回写（§9.2）：根因为载荷模型未注册与本地 Ollama 未运行；llama3.2:1b（Ollama LAN）实证 routing→chunk→done 全链路通过；冒烟默认模型已更新 |


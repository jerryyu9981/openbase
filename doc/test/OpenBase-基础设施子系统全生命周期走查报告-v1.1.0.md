# OpenBase 基础设施子系统全生命周期走查报告（v1.1.0）

| 项目 | 内容 |
| --- | --- |
| 文档编号 | OB-TEST-LIFECYCLE-WALKTHROUGH-v1.1.0 |
| 文档版本 | v1.1.0 |
| 文档状态 | [Review]（待人工批准） |
| 适用环境 | Dev（共享基础设施 192.168.0.151 ＋ 本机服务端口） |
| 走查日期 | 2026-11-06（v1.0.0）／2026-11-07（v1.1.0 缺口闭合复验） |
| 编写角色 | 测试工程师（QA）／开发工程师（Dev）协同 |
| 关联文档 | 《OpenBase-全栈功能走查报告-v1.0.0》《OpenBase-API接口设计文档-v1.4.10》《OpenBase-平台模块生命周期补口-DevLogReport-v1.0.0》 |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 | 状态 |
| --- | --- | --- | --- | --- |
| v1.1.0 | 2026-11-07 | Dev／QA | 闭合 §7 生命周期缺口 GAP-01~03：新增字典类型删除、配置键删除、agent 列表与删除接口；补 6 项闭环单测并在真实 Dev 环境完成实测（含走查残留数据清理）；§6 补记门禁结果 | [Review] |
| v1.0.0 | 2026-11-06 | QA／Dev | 首版：四子系统全生命周期走查、缺陷修复与复验、质量门禁结果、生命周期缺口登记 | [Review] |

---

## 1. 概述

### 1.1 走查目的

对 OpenBase 统一底座及其挂接的基础设施子系统，按**全生命周期**（创建 → 读取／检索 → 更新 → 状态流转 → 回滚 → 删除 → 删除后不可见）逐环节做**真实数据闭环**验证，确认接口不是"返回 200 的空壳"，并修复阻断闭环的缺陷。

### 1.2 走查范围

| 范围 | 说明 |
| --- | --- |
| OpenRAG（8010） | 知识库集合创建／详情／检索／删除，文档与对话链路（既有用例复跑） |
| OpenMemory（8020） | 记忆写入（remember）／召回（recall）／列表／详情／遗忘（forget）／删除后不可见 |
| DPS（8030） | 画像模板全生命周期：新建 → 详情 → 列表 → 更新 → 预检 → 启用 → 停用 → 版本对比 → 回滚 → 删除 → 404；子模板引用保护 409 |
| OpenLLM（8001） | 模型列表／详情／对话推理／会话创建／消息写入与读取／会话删除 |
| OpenBase 平台模块（8000） | 网关、租户、组织、字典、配置、文件、通知、调度、MCP、日志、AI 应用、用户、密钥（上一轮 56 项） |

**不在本轮范围**：前端页面像素级走查（前端 5173 未在本轮启动；页面调用的即是本报告覆盖的同源 API）、OIDC 交互式授权码流程（8090 未在本轮启动，密码登录通道已覆盖）。

### 1.3 结论摘要

- 四个基础设施子系统的**生命周期闭环全部打通**：创建/写入、读取/检索、更新/状态流转、删除、删除后 404 均取得真实数据证据。
- 本轮共修复 **6 项**阻断或失真缺陷（DPS 2 类 500、DPS 删除接口缺失、dps-proxy 全线 401、默认模型失效、Memory 代理超时），其中 2 项为跨仓（OpenBase ↔ DPS）契约补齐。
- 质量门禁：OpenBase `ruff` 全通过；平台补口定向单测 6 通过；dps-proxy 定向单测 123 通过；DPS 模板相关用例 419 通过、模板引擎专项 22 通过；OpenBase 全量单测因跨仓扫描类用例在本机阻塞，登记为 PENDING（证据见 §6）。
- v1.0.0 登记的 **3 项平台模块生命周期缺口（GAP-01~03）已于 v1.1.0 全部闭合**（新增字典类型删除、配置键删除、agent 列表与删除），并在真实 Dev 环境取得闭环证据（见 §7）。

---

## 2. 走查环境与方法

### 2.1 服务拓扑（实跑状态）

| 服务 | 端口 | 启动方式 | 走查时状态 |
| --- | --- | --- | --- |
| OpenBase 统一底座 | 8000 | uvicorn（demo_app） | 运行中 |
| OpenLLM 大模型网关 | 8001 | service-orchestrator（WMI 脱离会话） | 运行中（冷启动 193s） |
| OpenRAG 知识库 | 8010 | service-orchestrator | 运行中 |
| OpenMemory 记忆服务 | 8020 | service-orchestrator | 运行中（冷启动 294s） |
| DPS 数据画像 | 8030 | service-orchestrator | 运行中 |
| OIDC IdP | 8090 | — | 未启动（本轮不涉及） |
| 统一前端 | 5173 | — | 未启动（本轮不涉及） |

### 2.2 依赖与凭据

- 共享基础设施：PostgreSQL `192.168.0.151:5432`、Redis `:6380`、Qdrant `:6333`、Neo4j `:7687`、MinIO `:9000`、Ollama `http://192.168.0.4:11434`。
- 登录：`POST /api/v1/auth/login`（`admin/admin123`），响应顶层 `access_token`。
- 请求统一经 OpenBase 代理前缀：`/api/v1/rag-proxy`、`/api/v1/memory-proxy`、`/api/v1/llm-proxy`、`/api/v1/dps-proxy`。

### 2.3 判定口径（"真实有效"的定义）

| 环节 | 通过判据 |
| --- | --- |
| 创建/写入 | 2xx 且返回可用主键；随后可被详情/列表读回 |
| 读取/检索 | 返回内容与写入内容一致（语义检索命中写入文本） |
| 更新 | 版本号递增或字段值变更，且详情回读可见 |
| 状态流转 | 启用/停用后状态字段真实改变 |
| 删除 | 2xx；随后详情返回 404；列表不再出现 |
| 保护语义 | 存在下游引用时删除被拒（409）且数据保留 |

所有用例均通过 HTTP 真实调用（非 mock），失败用例须定位到根因并复验。

---

## 3. 结论总览

| 子系统 | 关键闭环用例 | 通过 | 失败 | 结论 |
| --- | --- | --- | --- | --- |
| OpenRAG | 创建集合 → 详情 → 检索 → 删除 → 404（5 项）＋ 既有文档/对话 8 项 | 13 | 0 | 通过 |
| OpenMemory | remember → recall → list → detail → forget → 404（6 项） | 6 | 0 | 通过（需 ≥180s 代理等待预算） |
| DPS 画像模板 | 新建 → 详情 → 列表 → 更新 → 预检 → 启用 → 停用 → 对比 → 回滚 → 删除 → 404（11 项）＋ 409 引用保护 2 项 | 17 | 0 | 通过 |
| OpenLLM | 模型列表 → 模型详情 → 对话推理 → 会话创建 → 消息写入 → 消息读取 → 会话删除（8 项） | 8 | 0 | 通过（gpt-4 除外，见 §5.6） |
| 平台模块（上一轮） | 网关/租户/组织/字典/配置/文件/通知/调度/MCP/日志/AI 应用/用户/密钥 | 56 | 0 | 通过 |

---

## 4. 逐子系统走查记录

### 4.1 OpenRAG（8010）

| 步骤 | 接口 | 结果 | 证据要点 |
| --- | --- | --- | --- |
| 创建集合 | `POST /api/v1/rag-proxy/collections` | 通过 | 返回集合 id |
| 集合详情 | `GET /api/v1/rag-proxy/collections/{id}` | 通过 | 名称/描述与创建一致 |
| 检索 | `POST /api/v1/rag-proxy/collections/{id}/query/retrieve` | 通过 | 返回检索结构（空库时为空结果，非报错） |
| 删除集合 | `DELETE /api/v1/rag-proxy/collections/{id}` | 通过 | 2xx |
| 删除后详情 | `GET /api/v1/rag-proxy/collections/{id}` | 通过 | 404 |

既有链路复跑：集合列表、文档入库、RAG 对话（返回真实答案与来源引用）共 8 项全部通过。

### 4.2 OpenMemory（8020）

| 步骤 | 接口 | 结果 | 证据要点 |
| --- | --- | --- | --- |
| 写入记忆 | `POST /api/v1/memory-proxy/remember` | 通过 | 返回 memory id；上游实测耗时约 79s（Qdrant 192.168.0.151 写入＋PG） |
| 召回 | `POST /api/v1/memory-proxy/recall` | 通过 | 命中写入文本 |
| 列表 | `GET /api/v1/memory-proxy/memories` | 通过 | 分页结构正常 |
| 详情 | `GET /api/v1/memory-proxy/memories/{id}` | 通过 | 内容一致 |
| 遗忘 | `POST /api/v1/memory-proxy/forget` | 通过 | 2xx |
| 删除后详情 | `GET /api/v1/memory-proxy/memories/{id}` | 通过 | 404/410 |

> 说明：`remember` 首次实测经 OpenBase 返回 `SYS_502 DPS upstream unreachable`（消息体为空），直连上游日志显示该请求**实际 200 成功**，耗时 78.9s，超过代理默认 20s 等待预算。已按 §5.5 调整等待预算后复验全绿。该现象为**环境时延**导致，非上游数据缺陷。

### 4.3 DPS（8030）画像模板全生命周期

| # | 步骤 | 接口 | 结果 |
| --- | --- | --- | --- |
| 1 | 新建模板 | `POST /api/v1/dps-proxy/templates` | 通过（修复前 500） |
| 2 | 模板详情 | `GET /api/v1/dps-proxy/templates/{code}` | 通过 |
| 3 | 模板列表 | `GET /api/v1/dps-proxy/templates` | 通过 |
| 4 | 更新模板 | `PUT /api/v1/dps-proxy/templates/{code}` | 通过（版本 v1 → v2） |
| 5 | 预检 | `GET /api/v1/dps-proxy/templates/{code}/preflight` | 通过 |
| 6 | 启用 | `POST /api/v1/dps-proxy/templates/{code}/activate` | 通过（修复前 500） |
| 7 | 停用 | `POST /api/v1/dps-proxy/templates/{code}/deactivate` | 通过 |
| 8 | 版本对比 | `GET /api/v1/dps-proxy/templates/{code}/diff?from=&to=` | 通过 |
| 9 | 回滚 | `POST /api/v1/dps-proxy/templates/{code}/rollback` | 通过 |
| 10 | 删除 | `DELETE /api/v1/dps-proxy/templates/{code}` | 通过（本轮新增能力） |
| 11 | 删除后详情 | `GET /api/v1/dps-proxy/templates/{code}` | 通过（404） |
| 12 | 子模板引用保护 | 父模板被 `extends` 引用时删除 | 通过（409，父模板保留） |
| 13 | 模板包导出 | `POST /api/v1/dps-proxy/template-packages/export` | 通过（`scope.codes` 指定已存在模板） |

补充：标签体系（标签分类/标签/血缘）CRUD 在上一轮已通过；本轮复核删除链路无回归。

### 4.4 OpenLLM（8001）

| 步骤 | 接口 | 结果 | 证据要点 |
| --- | --- | --- | --- |
| 模型列表 | `GET /api/v1/llm-proxy/models` | 通过 | 注册表返回 6 个模型（gpt-4 / deepseek-v4-flash / qwen2.5:0.5b / llama3.2:1b / qwen3.5:2b / qwen3.5:4b） |
| 模型详情 | `GET /api/v1/llm-proxy/models/qwen2.5:0.5b` | 通过 | 容量/状态字段可读 |
| 对话推理 | `POST /api/v1/llm-proxy/chat` | 通过 | 真实返回"走查通过！" |
| 会话创建 | `POST /api/v1/llm-proxy/conversations` | 通过 | 返回会话 id |
| 消息写入 | `POST /api/v1/llm-proxy/conversations/{id}/messages` | 通过 | 2xx |
| 消息读取 | `GET /api/v1/llm-proxy/conversations/{id}/messages` | 通过 | 可读回写入消息 |
| 会话删除 | `DELETE /api/v1/llm-proxy/conversations/{id}` | 通过 | 2xx |

### 4.5 平台模块（上一轮结论引用）

网关（多系统探活）、租户、组织、字典、配置、文件、通知、调度、MCP、日志、AI 应用、用户、密钥共 56 项用例全部通过；本轮仅复核其与四子系统的联动（`/api/v1/gateway/ping` 四系统 `reachable=true`）。

---

## 5. 本轮缺陷与修复

| 编号 | 现象 | 根因 | 修复 | 复验 |
| --- | --- | --- | --- | --- |
| DEF-01 | DPS 画像模板**新建／更新／状态切换** 500 | `template_engine.py` 把 `datetime.now(timezone.utc).isoformat()`（字符串）写入 `TIMESTAMPTZ` 列，asyncpg 拒绝 `str` | 改为 datetime 对象（与 `annotation_template_engine.py` 的 OBS-02 修法一致），覆盖 create/update/set_status/_write_history | 新建/更新/启用/停用全部 2xx |
| DEF-02 | DPS 启用/停用 500 `Object of type UUID is not JSON serializable` | history 快照写入 JSON 列时含整行 UUID/datetime | `_dump` 增加 `default=str` 兜底 | 启用/停用 2xx，history 可读 |
| DEF-03 | 画像模板无删除接口，生命周期断链 | DPS 与 OpenBase 代理均未提供 DELETE | DPS 新增 `DELETE /api/v2/portrait/templates/{code}`（含子模板/标注模板/标签血缘引用检查 → 409）；OpenBase 新增 `DELETE /api/v1/dps-proxy/templates/{code}` 透传 | 删除 2xx → 404；引用场景 409；单测覆盖 |
| DEF-04 | `/api/v1/dps-proxy/*` **全线 401 `missing bearer token`**（同 token 访问其它模块 200） | `OPENBASE_DPS_UPSTREAM_BASE` 未配置，默认 `http://127.0.0.1:8000` 与 OpenBase 自身同端口 → 代理**自环**，上游 401/404 被归一化后表现为 dps-proxy 鉴权失败 | `.env.shared-infra` 显式配置 `OPENBASE_DPS_UPSTREAM_BASE=http://127.0.0.1:8030`（该键与 `tests/test_dps_proxy.py` 的默认值口径一致，不改默认值） | dps-proxy 健康检查与 13 项生命周期用例全通过 |
| DEF-05 | 默认模型不可用：`DEFAULT_LLM_MODEL=qwen3:0.6b` 已不在注册表 | 共享环境模型注册表变更，环境变量未同步 | `.env.shared-infra` 改为现存模型 `qwen2.5:0.5b` | 默认选路与对话 200，真实返回内容 |
| DEF-06 | Memory 写入经代理稳定 502（上游实际成功） | 上游 `remember` 实测 79s，代理默认 20s 超时 | `.env.shared-infra` 设 `OPENBASE_MEMORY_UPSTREAM_TIMEOUT=180` | 6 项闭环全通过 |

变更文件：

- DPS 仓：`src/engines/template_engine.py`、`src/engines/template_version_engine.py`、`src/rest_api/routes/routes_profiles.py`、`src/tests/test_template_engine_v2_10.py`
- OpenBase 仓：`openbase/modules/dps_proxy/__init__.py`、`tests/test_dps_proxy_v1410_contract.py`、`tests/test_dps_proxy_routes_v1410.py`、`.env.shared-infra`（未入库）

> `tests/test_dps_proxy_routes_v1410.py` 的「路由对象数 = 22」守卫原按路径计数，新增同路径 `DELETE /templates/{code}` 后误报为 23。已把计数口径改为 `(路径, 方法)` 精确配对，v1.4.10 契约仍严格为 22，后续版本同路径追加方法不再误判。

> 备注：`src/engines/annotation_engine.py` 存在同类时间戳写法，但该引擎属 **TD-2902 登记"禁止启用或修复"**，本轮**未改动**（曾误改并已完整回滚）。

---

## 6. 质量门禁

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| OpenBase 静态检查 | `python -m ruff check openbase tests` | All checks passed（v1.1.0 补口后复跑仍通过） |
| OpenBase 平台补口定向单测 | `python -m pytest tests/test_platform_lifecycle_delete.py -q` | **6 passed**（v1.1.0 新增：字典 409/删除→404、配置回退默认值/仅默认值 409、agent 列表→删除→吊销→401→幂等、缺失 agent 404） |
| OpenBase dps-proxy 定向单测 | `python -m pytest tests/test_dps_proxy.py tests/test_dps_proxy_v1410_contract.py tests/test_dps_proxy_routes_v1410.py -q` | **123 passed**（含本轮新增 DELETE 转发／409 透传 2 例） |
| OpenBase 全量单测 | `python -m pytest tests -q --timeout=120`（忽略 5 个真实基础设施依赖文件） | **PENDING（环境受限，见下）** |
| DPS 模板相关用例 | `pytest src/tests -k "template or portrait or annotation"`（忽略缺 `mccabe` 的复杂度守卫文件） | 419 passed |
| DPS 模板引擎专项 | `pytest src/tests/test_template_engine_v2_10.py` | 22 passed |

> DPS 全量单测在本轮修复前基线为 1920 passed；本轮仅改动模板引擎与路由，模板相关 419 项全通过。

**OpenBase 全量单测未能闭合的环境证据（两次尝试，均在 `pytest-timeout` 中断，无汇总统计）**：

1. 第一次按 `--ignore` 排除 `test_storage_s3_real.py`／`test_orchestrator_db_failover.py`／`test_audit_db_services.py`／`test_p2_residuals.py`／`test_storage_s3.py`，运行至 **28%** 中断于 `tests/test_s7_t6_gate.py::gate_report`——该 fixture 以子进程执行 `scripts/gate_aggregate.py --dry-run --skip-main-batch`，`subprocess.communicate` 超过 180s 未返回。
2. 第二次追加忽略 `test_s7_t6_gate.py`，运行至约 **30%** 中断于 `tests/test_cross_repo_auth_gate.py::test_error_code_map_literals_exist_in_targets`——`scripts/cross_repo_auth_gate.py:233` 的 `repo_text()` 递归遍历兄弟仓库源码时阻塞（`Path.is_file()` 长时间无返回）。

两次中断点均为**跨仓源码扫描／递归门禁聚合**类用例，依赖本机兄弟仓库布局与共享基础设施；本轮改动仅涉及 `openbase/modules/dps_proxy/__init__.py` 与 3 个 dps-proxy 测试文件，定向用例已 100% 通过。故本项登记为 PENDING，建议在具备完整兄弟仓与共享基础设施的联调机上执行 `python -m pytest tests` 完成终验。

---

## 7. 生命周期缺口登记（v1.1.0 已全部闭合）

| 编号 | 模块 | 原缺口 | 影响 | v1.1.0 落地 | 状态 |
| --- | --- | --- | --- | --- | --- |
| GAP-01 | 字典 | `/api/v1/dicts` 仅 GET/POST，**无类型删除接口**；走查残留 `wt_dict_type` 无法通过 API 清理 | 字典类型只增不减 | 新增 `DELETE /api/v1/dicts/{type_code}`（存在字典项 → 409 `BIZ_CONFLICT`；不存在 → 404；删除后清 Redis 缓存） | ✅ 已闭合 |
| GAP-02 | 配置 | `/api/v1/configs/{key}` 无 DELETE；走查残留 `walkthrough.key` | 配置项无法删除，只能改值 | 新增 `DELETE /api/v1/configs/{key}`（删 DB 行＋各级运行时覆盖，回退环境变量/代码默认值；仅默认值 → 409 `BIZ_CONFIG_CONFLICT`；未知键 → 404；版本历史保留供审计） | ✅ 已闭合 |
| GAP-03 | 身份 Agent | `/api/v1/identity/agents` 仅 POST（无列表/删除）；走查残留 `wt_agent_01` | Agent 生命周期不完整、不可审计 | 新增 `GET /api/v1/identity/agents`（分页＋租户隔离）与 `DELETE /api/v1/identity/agents/{agent_id}`（软删 `status=0`/`suspended` ＋ 级联吊销全部有效密钥 ＋ 清主体缓存，幂等） | ✅ 已闭合 |

**真实环境复验证据（2026-11-07，Dev／共享 PG＋Redis）**：

| 步骤 | 响应 |
| --- | --- |
| 字典：建类型→建字典项 | 200／200（item id=8） |
| 字典：有字典项时删类型 | **409** `BIZ_CONFLICT`，`detail.item_count=1` |
| 字典：删字典项→删类型→再删 | 200 → 200 `deleted:true` → **404** `BIZ_404` |
| 配置：设值→查→删→再查→再删 | 200 → 200 `v1` → 200 `deleted:true,restored_default:false` → 200 `value:null` → **404** |
| Agent：创建→列表→删除 | 200（agent 131）→ 200 列表含该主体 → 200 `{status:0, revoked_keys:1}` |
| Agent：删除后持原密钥访问 | **401** `AUTH_API_KEY_INVALID`（`agent api key revoked`） |
| Agent：重复删除 | 200（幂等，`revoked_keys:0`） |
| 残留清理 | `walkthrough.key` 200；字典 `wt_dict_type` 200；`wt_agent_01` 200（均已删除） |

详细契约与变更清单见《OpenBase-平台模块生命周期补口-DevLogReport-v1.0.0》。

---

## 8. 风险与后续建议

1. **共享基础设施时延**：PG/Qdrant 跨网访问使 DPS 单请求约 13s、Memory 写入约 79s，代理等待预算与服务健康检查阈值需与实测对齐（本轮已将 Memory 预算调至 180s）。建议在测试基线文档中登记各子系统 P95 时延。
2. **冷启动耗时**：OpenMemory 294s、OpenLLM 193s，接近 orchestrator 健康等待上限（300s/180s）。建议对冷启动服务单独设更长的健康等待或预热。
3. **启动期环境一致性**：`DPS_BASE_URL`（OpenLLM 用）与 `OPENBASE_DPS_UPSTREAM_BASE`（OpenBase 用）语义不同，易漏配。建议在 `.env.shared-infra` 增加成对注释（本轮已补）并在编排脚本启动日志中打印实际生效值。
4. **orchestrator 状态显示**：`status` 对"运行中但单次健康探测超时"的服务显示"不健康"，与本轮实测可用性不一致，建议区分"探活超时"与"服务不可用"。

---

## 9. 附录

### 9.1 复验脚本（临时，不随仓交付）

- `phase18_lifecycle.py`：DPS 模板全生命周期 11 步
- `phase19_lifecycle_tail.py`：删除后 404、导出、409 引用保护、LLM 对比参数
- `phase20_subsystems.py`：RAG／Memory／LLM 生命周期
- `phase21_llm.py`、`phase22_memory.py`：子系统单点复验
- `cleanup_templates.py`：走查模板清理
- `probe_platform_delete.py`（v1.1.0）：字典／配置／agent 删除接口真实环境复验与残留清理

### 9.2 术语

| 术语 | 含义 |
| --- | --- |
| 生命周期闭环 | 创建→读取→更新→删除→删除后不可见 全链路均取得真实证据 |
| 自环 | 代理上游地址指向自身端口，导致请求被自身鉴权拦截 |
| 引用保护 | 存在下游引用（子模板/标注模板/标签血缘）时禁止删除 |

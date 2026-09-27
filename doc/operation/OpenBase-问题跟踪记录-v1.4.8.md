# OpenBase 问题跟踪记录 - v1.4.8

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.8（会话编排前置与回写闭环） |
| 文档版本 | v1.59.0 |
| 状态 | [Review] |
| 作者 | AT-OpenBase-Test / DO-OpenBase-Ops / AA-OpenBase-Dev |
| 创建日期 | 2026-09-21 |
| 存放 | doc/operation/ |
| 来源 | 《OpenBase-测试报告-v1.4.8》**v1.6.0** §4.1 / §7 #3、#8、#9；`doc/test/evidence/v148/step4-round1-execution-20260921.txt` **§十~§十二**；OpenLLM 侧既有登记 `CLR-214-004`（`OpenLLM/doc/development/OpenLLM-DevLogReport-v2.14.0.md`）；《OpenBase-上下文精装配与组件通道优化技术方案-v1.1.0》§9 / §10（下一批次登记项，含基准证据 `doc/test/evidence/local-model-bench/`） |

> **范围声明**：本记录登记 v1.4.8 Step 4 测试执行期间发现的**环境 / 工具链**类问题，**不涉及 v1.4.8 产品功能缺陷**。
> **v1.1.0 重大更正**：「方案 A（清理 `backend/.pylib`）」经补充取证后**判定为不可实施**，**执行动作已暂缓且未删除任何文件**（详见 §1.1）；`DEF-BE-148-001` 经查明**与 OpenLLM 既有登记 `CLR-214-004` 同源**，本记录改为**引用 + 差异说明**并降级为 **P2**；`DEF-BE-148-002` 的核心判据**被本轮证据推翻并已更正**。

---

## 1. 缺陷清单（DEF）

| 缺陷 ID | 级别 | 来源 | 归属 | 问题描述 | 证据 | 修复状态 | 复测结果 |
|---------|:----:|------|------|---------|------|:--------:|---------|
| **DEF-BE-148-001**（**与 OpenLLM `CLR-214-004` 同源，为跨仓引用项**） | **P2**（v1.0.0 记为 P1，v1.1.0 **降级**） | 2026-09-21 Step 4 运行时环境探测（TT-v1.4.8-005~014 前置） | **OpenLLM 仓环境层（`backend/.pylib` + `backend/run_backend.py`）；本仓未改其代码** | **`run_backend.py`（辅助启动脚本）在 Python 3.10.11 下不可用**：该脚本把 `backend/.pylib` 置于 `sys.path` 最前，导入 `main:app` 时 `cryptography.hazmat.bindings._rust`（`DLL load failed`）与 `grpc._cython.cygrpc`（`cannot import name 'cygrpc'`）失败。**根因（v1.1.0 更正）**：`backend/.pylib` 是**为 Python 3.13.12 的 `.venv` 构建的依赖覆盖层**（`pip install --target backend\.pylib`，因该 `.venv` 的 site-packages 只读），其原生扩展为 **cp313（24 个）与 cp310（3 个）混编**；本机 `python` 为 **3.10.11**，凡**仅有 cp313 变体**的包（`cryptography` / `grpc` / `rpds` / `greenlet` / `lz4` / `uuid_utils` / `clickhouse_connect` / `yaml._yaml` / `sqlalchemy.cyextension` 等）在 3.10 下均不可加载；另 `bandit` / `stevedore` 依赖 `typing.Self`（Python ≥3.11），亦不可加载。**影响面（更正）**：① 仅**辅助入口** `run_backend.py` 不可用；② 本机**权威启动路径不受影响**——`OpenBase/scripts/service-orchestrator.ps1` 对 openllm 服务定义为 `python -m uvicorn main:app --host 127.0.0.1 --port 8001`（**完全不加载 `.pylib`**），实例 `8001` 实测健康（`/health` 200、`/openllm/v1/health` 200）。**上游状态**：OpenLLM 已登记同一问题 **`CLR-214-004`（P2）**，既定对策为「测试用系统 Python 3.10.11 启动后端以绕过 `.pylib`」；其《S4 设计草案》§R-1 已规划以 **`git rm -r --cached` + `.gitignore`（未跟踪 `.pylib`）** 作为正式清理方式 | ① 逐包导入探测（`.pylib` 前置，72 个顶层包，**58 通过 / 14 失败**）；② 原生扩展 ABI 分布实测 **cp313×24 / cp310×3**；③ 对照实验：`.pylib` 前置 → 复现失败；不加载 → 成功；④ 上游登记原文 `OpenLLM-DevLogReport-v2.14.0.md:128`、`OpenLLM-测试计划-v2.14.0.md:85`、`OpenLLM-测试报告-v2.14.0.md:47`、`OpenLLM-问题跟踪记录-v2.9.2.md:112-115`、`OpenLLM-S4-…设计草案-v1.0.0.md:199`；⑤ 权威启动定义 `service-orchestrator.ps1:105-110`；⑥ 隔离清单 dry-run（**未执行**）：23 项 / 26.2 MB | **不修复（本仓零改动，人工批准 2026-09-21）**：① **方案 A（清理 `.pylib`）经取证判定不可实施**（见 §1.1）；② 本仓**未做任何代码或环境改动**；③ **最终裁定＝采纳建议 1「本仓零改动」**，`DEF-BE-148-001` 转为**纯跨仓引用项**，随 OpenLLM 侧 `CLR-214-004` 通道处置（见 §1.1.1） | 绕行/权威路径可用：`8021` 实例（不加载 `.pylib`）5 项 HTTP 核验通过；`8001` 权威实例（编排器定义启动）`/health` 200、`/openllm/v1/health` **`openrag: ok`** |
| ~~**DEF-BE-148-002**~~ → **更正为「本仓测试环境配置缺口」（非缺陷）** | **P3**（v1.0.0 记为 P2，v1.1.0 **降级并更正**） | 2026-09-21 Step 4 运行期只读核验（`GET /openllm/v1/health`、`GET /openllm/v1/writeback/receipts`） | **本仓测试侧（我方临时启动未携带编排器 `Env`）；非上游、非代码** | **原判据被推翻**。v1.0.0 记为「OpenRAG 上游 401 `missing api key` → 健康聚合降级 + 回执长期 `pending`」。v1.1.0 复核：**同一台机上权威实例 `8001` 的 `/openllm/v1/health` 返回 `openrag: ok`（latency 1750ms）** → OpenRAG **可用**；该 401 系**我方 `8021` 临时启动器未加载编排器为此服务声明的 `Env`**（`service-orchestrator.ps1` 中 openrag/openllm 均声明了凭据与受信代理变量）所致的**测试环境配置缺口**，**非上游故障、非产品缺陷**。回执 3 条 `status=pending` / `retry_count=0` 的成因亦需在**带完整 `Env` 的实例**上重测后方可定性（当前不下结论） | 对照证据：`GET 127.0.0.1:8001/openllm/v1/health` → `{"components":{"openmemory":"ok","openrag":"ok"(1750ms),"dps":"ok"}}`；`GET 127.0.0.1:8021/openllm/v1/health` → `openrag":"unavailable(401 missing api key)"` | **无需修复**（改为按编排器定义启动即可消除） | 待用编排器 `Env` 重启实例后复测：健康聚合三项全 `ok`、回执状态推进（关联 TT-v1.4.8-016/018） |
| **DEF-BE-148-003** | **P1（产品功能缺陷，v1.4.8 核心需求受阻）** | 2026-09-21 Step 4 运行时用例第二轮（RT-3 会话轴） | **OpenLLM 仓 `app/services/conversation_service.py`（第 54 / 212 行）** | **会话标识未落库 → 会话轴筛选恒为空**。`POST /api/v1/conversations/{id}/messages?session_id=X` 返回 **201**，但 `GET .../messages?session_id=X` 恒返回 **0 条**（不筛选则返回全部）。**DB 直查**：4 条 `conversation_messages.metadata` **全为 `{}`**。**根因**：模型 `app/models/conversation.py:109` 将 JSONB 列映射为属性 **`metadata_`**（`Column("metadata", JSONB)`，规避 SQLAlchemy 保留名），而服务层构造时用**非映射关键字** `metadata=` → SQLAlchemy **静默忽略**（不报错），列回落 `default=dict` → 恒为 `{}`。**同源第二处**：第 54 行 `Conversation(metadata=metadata or {})`（`conversation.py:41` 同样映射 `metadata_`）→ 会话级 metadata 亦丢失。**对照全仓**：其余写入点均正确用 `metadata_=`（`roles.py:72/128/248`、`documents.py:106`、`tool_calls.py:166/204`、`document_pipeline.py:211`、`permission.py:134`、`plugins.py:334`），**仅此两处写法错误**。**影响**：v1.4.8 核心需求「会话标识贯穿（§4.4）」在会话/消息落库链路**完全失效**；会话标识无法作为历史注入与回写关联的消息侧依据；连带**所有调用方 metadata 长期静默丢弃**（历史遗留隐患，因本版本会话轴而暴露） | ① **最小实验（决定性）**：`build_session_metadata("v148-proof", uuid4)` → `{'session_id':...,'session_scope':'session'}`；`ConversationMessage(..., metadata=merged)` → **`m.metadata_`（映射列）= `None`**，而 `m.__dict__['metadata']` 持有该值（**实例影子属性**），`m.metadata_ == merged` 为 **False**；② DB 直查 4 行 `metadata={}`；③ HTTP 三观测（POST 201 / 筛选 0 条 / 不筛选 4 条）；④ 证据 `doc/test/evidence/v148/step4-round1-execution-20260921.txt` **§十三 步骤 5** | **已修复（2026-09-21，回退 Step 3 执行，人工批准方案①）**：① `conversation_service.py` 第 54 行 `metadata=` → **`metadata_=`**、第 212 行 `metadata=` → **`metadata_=`**；② **连带项（同一缺陷族）**：`schemas/conversation.py` 抽出模块级 `_orm_values_with_metadata()`（`metadata` 一律从 ORM 属性 `metadata_` 读）供两个响应模型复用，并为 **`MessageResponse` 补上缺失的 `extract_metadata` 前置校验器**（该缺失由本次修复暴露：修复前影子属性恰好是 dict 使序列化「碰巧通过」，修复后立即 500）；③ 新增护栏 `tests/unit/test_conversation_metadata_mapping.py`（**5 例，用真实模型断言映射属性**，不 patch 模型），并更正既有 3 例固化错误契约的断言口径（`metadata` → `metadata_`） | **复测通过（2026-09-21）**：TDD RED→GREEN（3 failed → 3 passed）；精确回归 **37 passed / 0 failed**；ruff 新护栏 `All checks passed`、两被改文件告警**均不在改动行**；L2/L3 运行时复测 **8/8 通过**（发送消息 500 → **201**；`GET .../messages?session_id=S1` **0 条 → 2 条**、S2 → **1 条**、缺省不筛选 **3 条**；**DB 直查 3 行 `metadata` 均含 `session_id`/`session_scope`**） |

### 1.1 「方案 A（清理 `.pylib`）」——最终裁定：**不可实施 → 采纳「本仓零改动」（人工批准）**
v1.0.0 曾提出 A/B/C 三方案并建议 B，人工裁定执行 **A**。**补充取证后判定 A 不可实施**，理由如下（三条独立且各自充分）：

| # | 推翻理由 | 依据 |
|:-:|---------|------|
| 1 | **A 会打断上游 3.13 运行时的依赖覆盖层**。`.pylib` 的存在目的正是为 **Python 3.13.12 的 `.venv`** 覆盖依赖（该 `.venv` site-packages 只读）。待隔离的 9 个包中 `cryptography` / `grpc` / `rpds` / `greenlet` / `lz4` / `uuid_utils` / `clickhouse_connect` 的原生扩展**均为 cp313 构建**——在 3.13 下它们是**可用资产**，删除会使 3.13 运行时**只能回落到未必具备这些包的 3.13 site-packages**，构成**真实回归风险** | `OpenLLM-问题跟踪记录-v2.9.2.md:112-115`；`.pylib` ABI 实测 cp313×24 / cp310×3 |
| 2 | **缺陷上游已编号且已有既定对策**。同一问题已登记为 **`CLR-214-004`（P2）**，对策为「用系统 Python 3.10.11 启动以绕过 `.pylib`」——本仓重复造轮子去改他仓的 vendored 目录既不必要，也会与上游处置冲突 | `OpenLLM-DevLogReport-v2.14.0.md:128`；`OpenLLM-测试计划-v2.14.0.md:85` |
| 3 | **对 Step 4 无收益**。本机**权威启动路径根本不加载 `.pylib`**（编排器定义 = `python -m uvicorn main:app --port 8001`），故 A 修复的是一个**项目未使用的辅助脚本**，对 Step 4 运行时测试与门禁**零收益** | `OpenBase/scripts/service-orchestrator.ps1:105-110` |

**已执行动作**：仅生成**隔离清单 dry-run**（23 项 / 26,202,973 字节 ≈ 26.2 MB，含 `cryptography`(10.6MB)、`grpc`(12.5MB)、`rpds`、`greenlet`、`lz4`、`uuid_utils`、`clickhouse_connect`、`bandit`、`stevedore` 及 14 个 dist-info）。**未执行 `--apply`，未复制、未删除任何文件**，`.pylib` 与仓库工作树**保持原状**。

**建议的替代处置（供裁定）**：
1. **本仓不动作，零改动**（推荐）——按上游 `CLR-214-004` 既定通道处置；本记录仅作**跨仓引用与差异登记**。
2. 若需在 OpenLLM 侧正式收口，走其《S4 设计草案》§R-1 已规划的 **`git rm -r --cached backend/.pylib` + `.gitignore` 增补**「未跟踪」清理批次（**不是**删除包内容），并可复跑其 `scripts/setup-env.ps1` 重建环境。
3. 若坚持让 `run_backend.py` 在 3.10 可用，应采原 **方案 B 的收敛形态**：在 `run_backend.py` 内**按解释器 ABI 有条件加载 `.pylib`**（例如仅在 `sys.version_info` 与 `.pylib` 内主导 ABI 一致时前置），而非物理删除他仓 vendored 资产——属 **OpenLLM 仓**改动，须回 OpenLLM 走其开发/测试流程。

#### 1.1.1 裁定结论（2026-09-21，人工批准，批准人＝用户）

| 项 | 内容 |
|----|------|
| 裁定 | **采纳建议 1：本仓零改动**（不采 A / 不采建议 2 / 不采建议 3） |
| 裁定对象 | `CR-148-001`（`.pylib` 处置） |
| 裁定日期 | 2026-09-21 |
| 执行结果 | **本仓未做任何代码或环境改动**：`.pylib` 零改动（0 删除，5,860 文件与 9 个目标包全部在位、`git status` 无删除项）；OpenLLM 工作树保持原状 |
| 生效范围 | 本仓（OpenBase）。`DEF-BE-148-001` 转为**纯跨仓引用项**，随 OpenLLM 侧 `CLR-214-004` 的既有通道处置 |
| 我方承诺事项 | ① 运行时实例**按编排器服务定义（含全量 `Env`）启动**（`CR-148-004`）；② **不再**以端口号推断被测对象（`CR-148-003`）；③ 本记录后续仅在**证据变化**时更新，不重复发起环境改动 |
| 后续动作 | 无（本方案为终态）；`openllm_gateway.py` 74 行覆盖缺口与 34 条运行时用例的解锁**仅依赖凭据（`D3`）**，与 `.pylib` 无关 |

## 2. 变更请求（CR）

| CR ID | 来源 | 内容 | 影响 | 状态 |
|-------|------|------|------|:----:|
| **CR-148-001** | DEF-BE-148-001 处置裁定（2026-09-21） | 原：请裁定 `.pylib` 处置方案 A/B/C。**更新**：A 经取证判定**不可实施**（§1.1）；**最终裁定：采纳建议 1「本仓零改动」**（不采 A、不采建议 2/3），裁定结论见 §1.1.1 | OpenLLM 仓（不属本仓改动范围）；《测试报告-v1.4.8》§7 #3 | **已裁定（人工批准，2026-09-21）** |
| **CR-148-002** | 本轮环境探测（栈内服务清点）派生 | 《测试报告-v1.4.8》§1 #1 引用的《DevLogReport》版本由 **v1.6.0 更正为 v1.7.0**；并建议对本版本文档做一次**交叉引用一致性核查** | 文档类，不涉代码；已在《测试报告-v1.4.8》**v1.3.0** 内更正 | **已实施** |
| **CR-148-003** | 本轮环境探测派生（认定缺陷归属） | 初判「**8000 端口即 OpenLLM**」**已被证伪**——8000 实为 `openbase.demo_app:app`（OpenBase 自身）；**8001 才是 OpenLLM**。建议：运行时用例的**环境前置条件**须写明「端口→进程→应用」映射，禁止以端口号推断被测对象 | 测试方法（《测试计划-v1.4.8》环境章节） | **已登记**（建议纳入下版本测试计划模板） |
| **CR-148-004** | 本轮更正派生（2026-09-21） | ① 运行时实例**必须按 `service-orchestrator.ps1` 的服务定义启动**（含其 `Env`），否则健康聚合与上游链路会呈现**假故障**（如本轮 `openrag 401`）；② 应在测试计划中固化「实例启动方式 = 编排器定义」这一前置条件 | 《测试计划-v1.4.8》/《测试用例-v1.4.8》环境前置；本记录 §1 | **已登记** |
| **CR-148-005** | DEF-BE-148-003 处置（2026-09-21） | 请在两方案中裁定：**① 回退 Step 3 修复**（`conversation_service.py` 第 54/212 行 `metadata=` → `metadata_=`，属 OpenLLM 仓改动；按五步流程须更新其 DevLogReport 并重新提测）；**② 或不修复、降级登记为已知限制**（则 v1.4.8 核心需求「会话标识贯穿」不成立，本版本不可放行）。**本记录建议 ①**（1 行级修复 + 补 1 条经 ORM 映射的集成护栏） | OpenLLM 仓 `app/services/conversation_service.py`、`app/schemas/conversation.py`；本仓《测试报告-v1.4.8》§7 / §11 | **已裁定（人工批准，2026-09-21）＝方案①；已实施并复测通过（见 §5 v1.4.0）** |
| **CR-148-006** | 回写链路鉴权缺口（2026-09-21，人工批准方案①） | **跨系统集成缺口修复（非本仓代码缺陷，无本仓代码改动）**：根因＝OpenMemory 网关鉴权为**顺序两段且「并且」关系**（先 `X-API-Key`，未配置不强制；再在 `jwt_secret` 已配时**强制**校验 `Authorization: Bearer`，**不可被 API Key 旁路**），而 OpenLLM 出站按 R5 治理**只发 `X-API-Key`** → 必然 401。处置＝OpenLLM 出站并存附加**共享密钥 HS256 服务账号 JWT**（新增 2 配置项）+ 共享密钥注入 + `OPENMEMORY_TIMEOUT` 5s→30s。**连带三项澄清**：① sync 通道**不入队**（故回执查询为空属预期语义）；② profile 路失败＝**直连客户端缺四维身份**（DPS 要组织/租户标识头，需走 OpenBase 代理链）；③ `retry_count=4` 为计数口径差异（**未超标**，撤回上轮怀疑） | OpenLLM 仓（`openmemory_client` / `config` / `openllm_gateway` / 2 配置文件）；本仓《测试报告-v1.4.8》§7 / §11 | **已实施并复测通过**：回写 `401 → 请求超时 → 200`；**TT-018「重启不丢写」取证成立**（队列 28 行不变、id 408/409 仍在且续投递） |
| **CR-148-007** | **`DEF-BE-148-004`（计费落库失败污染成功响应）处置 + 2 项派生问题定性**（2026-09-21） | **新增缺陷 `DEF-BE-148-004`（P1）**：LLM 调用**已成功**（`usage_records` 插入参数实证：`provider_id`=DeepSeek、`model_id`=deepseek-v4-flash、`tokens_input=48`/`tokens_output=4550`/`tokens_total=4598`、`status='success'`），却因 **`usage_records.organization_id` NOT NULL 约束**触发 `psycopg2.errors.NotNullViolation`（`billing_service.py:251` → `openllm_gateway.py:2059 billing.record_usage()`），**整体被报成 500**。后果：① 响应语义被污染（调用方误判为模型失败）；② 存在「**token 已消耗但未记账**」的计费一致性风险敞口。触发条件：**调用方账号无组织归属**。**处置建议**：① 计费落库失败**不应改变**已成功的业务响应（改为告警 + 异步补偿）；② `organization_id` 缺失时应落默认组织或采用可空 + 业务校验。**本轮临时处置**：为探测账号绑定既有组织（单行 UPDATE，已执行，响应即恢复 200）。<br>**派生问题定性 1（`DEF-BE-148-005`，P2，待确认）**：会话维度两条 metrics 记录中**流式**那条 `model=deepseek-v4-flash`，而**同步**那条 **`model=null`** —— 指标落库字段填充行为两路径不一致（`context_metrics.py:86` 取 `self.model`，调用点 `:275`/`:339` 二处之一未传 `model`）。影响：同步路径的指标无法按模型维度归集。**派生问题定性 2（非缺陷，未接线）**：两条记录 `segment_tokens` 全 0、`counted=false` —— 经代码核对属**设计语义**：`prompt_pipeline.py:45/94` 定义 `counted = count_tokens is not None`，文档第 39 行明载「**未提供计数器时为 False**」；即**调用时未注入 token 计数器**，属**接线未启用**而非缺陷。影响：「缓存命中」判据项**无有效观测值**（属"未计数"，非"两路径不一致"）。 | OpenLLM 仓 `app/services/billing_service.py`、`app/api/openllm_gateway.py`、`app/edgerouter/orchestration/context_metrics.py`、`prompt_pipeline.py`；本仓《测试报告-v1.4.8》§11；证据 **§十九** | **缺陷已修复并运行时验证通过**（提交 `ca45639`；RED 3 failed → GREEN 24 passed/0 failed；无组织账号 chat **500 → 200** 且日志出现守卫 WARN）；派生 1 待确认是否立修；派生 2 建议仅登记不修（或补接线）；**残留：组织缺失时「未记账」由静默转为可观测告警，兜底策略待裁定** |
| **CR-148-008** | **新增三项缺陷登记：两路径模型解析不一致（P1）/ 回执查询跨用户越权（P1，安全）/ 错误响应缺 `detail`（P2）**（2026-09-21） | ① **`DEF-BE-148-006`（P1）两路径模型解析机制不一致**：**同步**路径经 **5 因子路由改写**模型（选到 `deepseek-v4-flash`），**流式**路径**依赖 `DEFAULT_LLM_MODEL`、不经路由治理** → 同一 `mode=auto` 请求两路径解析到**不同供应商**。**对照实验实证**：`DEFAULT_LLM_MODEL=qwen3:0.6b` 时流式 **3/3 失败**（事件序列 `routing → error`；traceback 落 `gateway/ollama_adapter.py:177`（经 `openai_adapter.py:75`）→ **`httpx.ConnectError: All connection attempts failed`**，即连**不可用的本地 Ollama**）；改回 `deepseek-v4-flash` 后流式 **3/3 成功**（`routing → chunk×38 → done`，`done` 载荷含 `usage` + `request_id`）。**危害**：生产环境该值未同步配置时**流式静默指向错误供应商**，配置期无报错、仅调用时连不上。**代码位置**：`openllm_gateway.py:1352-1361`（`provider_config` → `create_adapter`）、`:1372`（发起流式调用）。<br>② **`DEF-BE-148-007`（P1，安全）回执查询跨用户越权**：以**另一账号**（`v148-noorg`，非该会话创建者）请求 `GET /openllm/v1/writeback/receipts?session_id=v148-tt-fill` → **200 且返回 1 条** → **任一已认证用户可读他人会话回执**，端点**未按用户/租户隔离**。关联 **RT-148-04 会话标识隔离 / TT-v1.4.8-036**。<br>③ **`DEF-BE-148-008`（P2）错误响应缺 `detail`**：实测未授权响应体仅 `{code, message, request_id}`，**缺 `detail`**，与设计契约及 `AGENTS.md` 错误码规范 `{code, message, detail, request_id}` **不符**（TT-v1.4.8-014）。 | OpenLLM 仓 `app/api/openllm_gateway.py`（缺陷①）；本仓《测试报告-v1.4.8》§7 / §8.1 | 三项**均未修复**。处置建议：① 统一两路径模型解析入口（**流式纳入路由治理**），并将 `DEFAULT_LLM_MODEL=deepseek-v4-flash` 作为**环境前置保留**；② 回执/消息查询按**用户与租户**过滤；③ 错误响应补 `detail`。**① `DEF-BE-148-006` 已修复并验证通过**（流式判据改为「调用方是否显式指定 model」并纳入 5 因子路由；**原失败条件下回归**：修复前流式 3/3 失败 → 修复后 3/3 成功，未改配置）；**② `DEF-BE-148-007` 已修复并验证通过**（`list_rows` 加 `json_extract(payload_json,'$.user_id')` 过滤 + 端点传已认证身份 + fail-closed；**双对照**：本人可见 `total=1`、他用户 `total=0`（修复前 1 条））；**③ `DEF-BE-148-008` 已修复并验证通过**（`_error_response` 补 `detail`，字段始终存在；`/writeback/receipts` 未授权分支由 `200 + note` 改为 **`401`**，同时满足 fail-closed 与 TT-014 契约；验证：401 体四字段齐备、**越权回归仍 PASS**（A=2 / B=0）；残留：该端点 `request_id` 为空串，待 TT-014 补齐）；④ 连带结论：**撤回**「须保留 `DEFAULT_LLM_MODEL=deepseek-v4-flash` 作环境前置」的建议（流式已不依赖该值）；⑤ 过程复盘：同一缺陷误判两次（第二次写出永不执行的死代码），**先观测 `llm_comp` 实际值后一次定位** —— 已作为"先观测再断因"的反面教材留痕。**证据**：证据文件 **§二十三**（两次交付的改动、双对照验证、过程复盘）；另见 §二十二 |
| **CR-148-009** | **三项未提交内容处置**（2026-09-21，人工指示「先处理那三项未提交内容」） | 处置前 OpenLLM 仓工作区 **86 M / 211 D / 80 ??**，三项对象的实测事实：① **`.env.shared-infra`（被跟踪，M）**——`git log` 各历史版本中 `OPENRAG_API_KEY` 赋值长度**恒为 0**（**空值模板**），工作副本却已填入真实凭据与 **v1.4.8 共享 JWT 签名密钥**，**提交即首次把真实密钥带入版本库**；② **`tests/unit/conftest.py`（M）**——pgAdmin site-packages 与 `.pylib` 由 `insert(0/1)` 改 `append`（**末端兜底**），属测试基础设施修复；③ **211 项 `D`**——**全部位于 `__pycache__`**（`backend/app` 161 + `backend/tests` 50，cpython-314 产物），`.gitignore` **已覆盖**。<br>**处置**：① **密钥不落 git**（依 `AGENTS.md` §6 与本文件内「勿落 git」注释）——同源性核验三处密钥 **len=64 / sha6=`67da1a614a93` 一致**后，把共享密钥写入**未跟踪**的权威注入源 `OpenBase/.env.shared-infra`（使**编排器启动路径**亦具备回写出站 JWT），再对 OpenLLM 仓该文件执行 **`git update-index --skip-worktree`**（实测 `S .env.shared-infra`，全仓仅此一个；**可逆**）；②③ 按**原子提交 + 显式路径**入库：**`a5bde45`**（`chore(repo)`，211 文件纯删除）、**`9b9fcd5`**（`test(tests)`，`+12/-2`），暂存前后均核验**非 `__pycache__` 项 = 0**，**未用 `git add -A`**。<br>**结果**：工作区收敛为 **84 M / 0 D / 80 ??**；**未提交、未删除**任何密钥文件，本地实值保持原位 | OpenLLM 仓工作区与版本库形态；`OpenBase/.env.shared-infra`（**未跟踪**，不入库）；本仓《测试报告-v1.4.8》§7 #5 | **已实施**（证据 **§二十五** 甲/乙/丙） |
| **CR-148-010** | CR-148-009 处置过程中的**顺带发现**（2026-09-21） | **v1.4.8 部分实现从未入库**：以 `git ls-files` + `git log --all -- <path>` 双重核验，**以下 8 个交付文件在全仓历史中从未出现任何提交**——`edgerouter/orchestration/` 下 `context_metrics.py`、`prompt_pipeline.py`、`component_pipeline.py`、`golden_set.py`、`baseline_report.py`、`attribution_b.py`、`history.py`，以及 `services/session_scope.py`；同时 `assembler.py`、`auto.py`、`explicit.py`、`executor.py`、`context_manager.py`、`conversations.py` 等**已跟踪文件仍为 M**。<br>**性质**：**版本基线漂移风险**——工作树若丢失，v1.4.8 相当一部分实现**不可恢复**；且与《测试报告-v1.4.8》§7 #5「改动已提交」的口径（原指已登记的 10 + 14 + 4 个文件）**并不完全一致**。<br>**建议处置**：人工裁定入库范围后，按**原子提交**逐组入库（须排除 `.pylib` 未跟踪噪声、`backend/data/*.db` 运行期数据、`backup/`、仓根临时 `.bat`、`data/edge_tokens.jsonl` 等）；并与《DevLogReport》§13 的 v1.4.8 交付清单逐项对齐 | OpenLLM 仓版本库完整性；Step 5 发布前置（发布快照须与工作树一致） | **已裁定并实施**（人工批准 2026-09-21，批准人＝用户；证据 **§二十六**）：<br>**① 裁定依据**＝沿用《OpenLLM-联调产物待提交清单-v1.0.0》A/B/C + 需人工判定四类框架及其「只 add 预期路径、禁止 `git add -A`」纪律，并以《DevLogReport R-396~R-398》§4 交付清单（19 源文件 + 1 数据资产 + 15 测试）逐项对齐。<br>**② 裁定范围**：**入库**＝R1 新增源码 8（`orchestration/{prompt_pipeline,context_metrics,attribution_b,component_pipeline,golden_set,baseline_report,history}.py` + `services/session_scope.py`）、R2 修改源码 6（`api/conversations.py`、`orchestration/{assembler,auto,executor,explicit}.py`、`services/context_manager.py`，**实测 need-star 命中 0、无需 hunk 拆分**）、R3 数据资产 `golden_set_v1.json`、R4 文档 2（本版本 DevLogReport + 联调产物待提交清单）、R5 `.devflow/state.json`、C 噪音清理（71 项 `__pycache__/*.pyc` + 8 项 `.pylib` dist-info + `data/edge_tokens.jsonl` 移出跟踪 **+ `.gitignore` 增补**）；**不入库**＝`.pylib` vendored、`backend/data/*.db*`、`backup/`、仓根 `*-commit-push.bat`×4、`scripts/*_commit_push*.ps1`×5、`OpenLLM_完整方案文档.html`、`test_debug_gateway_ollama.py`；**另批**＝`test_billing_v2_api.py`（清单 J-6）、DPS Pro 化设计文档 v1.1.0+archive（J-10/J-11）、OpenRAG 接入迭代规划（J-9）。<br>**③ 实施（4 个原子提交，显式路径）**：`10e4cc6`（`feat(v148)`，8 文件 `+1262`）、`0fa9e84`（`feat(v148)`，6 文件 `+173/-81`）、`ab90513`（`chore(v148)`，4 文件 `+704`）、`589012d`（`chore(repo)`，81 文件 `+6/-262`）；每批提交前 `git diff --cached --name-only` 计数 = 8/6/4/81 与预期一致，**工作树文件未被删除**。<br>**④ 结果**：工作区 **84 M / 80 ?? → 1 M / 14 ??**，残量全部属「不入库/另批」。<br>**⑤ 如实更正**：前序记录将 `backend/.pylib/**` 表述为「未跟踪」**不准确**——实测 `git ls-files` = **3510 个已跟踪文件**（另有约 1157 项未跟踪）；其正式处置属**上游 `CLR-214-004` 流程**（`git rm -r --cached backend/.pylib`，涉及 3510 项索引变更），**本轮未执行**；本轮仅新增 `.gitignore` 规则 `backend/.pylib/`，**作用边界如实说明＝仅阻止新增文件进入跟踪**。<br>**⑥ **附带风险**：清单 §3 登记的 need-star 增量在当前工作树**已无痕迹**（`profile_refine.py` 与 4 个 `test_*_phase1.py` 已从磁盘消失且从未入库）→ 登记为风险，交 need-star 立项方确认 |
| **CR-148-011** | **按 TT-ID 整批补跑发现 1 项新缺陷**（2026-09-21，CR-148-010 之后的续办项） | **`DEF-BE-148-009`（P2）`GET /api/v1/monitoring/traces/{trace_id}/spans` → 500**。**复现**：对任一存在 `request_id` 调用即 500（响应体 `{"error":{"message":"服务器内部错误","type":"internal_error"}}`）。**根因（日志实录）**：`fastapi.exceptions.ResponseValidationError: 8 validation errors`，位置 **`backend/app/api/traces.py:362 get_trace_spans`** —— 响应模型要求每个 span 具备 **`span_id / name / kind / status`**，而**落库 spans 结构为 `[{"step":"auth","ms":0},{"step":"llm","ms":10343}]`**（2 span × 4 缺失字段 = 8 项校验失败）→ 响应序列化抛错 → 500。**性质**：**产品缺陷**（响应模型与落库结构不一致），**非环境问题**；同级 `/openllm/v1/trace/{id}` 与 `/api/v1/monitoring/traces/{id}` 均正常 200（**仅 `spans` 子端点异常**）。<br>**同轮另登记 2 项非缺陷观测**：① **偶发 500（P3，待观察）**：`POST /openllm/v1/chat` 携 `session_id=""` **主批次首测 1 次 500，其后 5 次观测均 200**（未复现；旧实例 stdout 未落盘致根因未捕获，已改为日志落盘）；② **观测缺口**：`TT-020` 历史段注入**无可观测面**（`context_metrics.segment_tokens.history` 因 token 计数器未接线恒 0）→ 需补接线后方可判定（与 §7 #13 同源） | OpenLLM 仓 `app/api/traces.py`；本仓《测试报告-v1.4.8》§7 / §11 | **已修复并验证通过（2026-09-21）**：根因＝`traces.spans` 列**同一列承载两种形态**（① OTel 形态由 `trace_service.TraceContext` 写入；② **步骤计时形态**由网关轻量写入 `[{"step":"auth","ms":0}]`），而端点声明 `response_model=List[SpanResponse]`（必填 `span_id/name/kind/status`）→ 形态②每 span 缺 4 项 × 2 = 8 项校验失败 → 500。**修复**：在**服务层**新增 `normalize_span_for_response()` / `normalize_spans_for_response()` 统一归一化（形态①原样透传并补默认；形态②以 `step` 为 `name`、`ms` 为 `duration_ms`、`status=ok`、`attributes={step,ms}`；未知形态与标量亦合成合法结构、**不丢数据**；非列表按空列表），端点改为返回归一化结果，**端点签名与响应契约不变**（**未采用「仅放宽响应模型」方案** —— 该方案会静默丢弃形态②字段，等于返回空壳）。<br>**验证**：① **TDD** RED（收集期 `ImportError: cannot import name 'normalize_spans_for_response'`；端点级用例修复前 500）→ **GREEN 13 passed**（新护栏 10 例 + 既有 3 例）；② **ruff**：新护栏 `All checks passed`、两被改文件**改动行零告警**（总告警 112 → 107，余为既有历史欠账）；③ **回归 + 基线对照**：`tests/unit` 全量 **2188 passed / 13 failed**，经 `git stash` 基线对照确认 **13 项为既有失败**（修复前后同为 13 failed），615 error 为根 conftest 既知环境缺陷（§7 #4）所致的夹具缺失；④ **运行时（重启实例）5/5 通过**：目标端点 **500 → 200**（2 条，样例 `{"span_id":"…-0","name":"auth","kind":"internal","duration_ms":0,"status":"ok","attributes":{"step":"auth","ms":0}}`）、`/{id}` 仍 200、未知 trace 仍 404。**提交**：`48610cc`（3 文件 `+259/-2`，显式路径，**TDD 合规**）；证据 **§二十八** |

## 3. 风险归集检查

> 本章节为必填项，用于确认本版本所有 P1+ 风险/问题已归集到技术债务总表。

| 检查项 | 结果 | 说明 |
|:-------|:----:|:-----|
| 本阶段 P1+ 风险是否已归集 | ✅ **已归集（架构类 1 项入总表）+ 2 项按「缺陷」通道处置（不入债表）** | ① **已入总表**：**`TD-新增-027`（P1，并发下服务端串行化；架构/性能债务）** 已于 2026-09-22 写入《OpenBase-技术债务总表》**v0.7.0**（待偿还 16→17、总计 26→27），含 `peak_in_flight=8` / `achieved_rps` / 单发对照等完整证据；**收口轮补充证据**：关闭 `echo` 后单飞 6.501 req/s → 并发 8 仅 9.317 req/s（**1.43×**，达理想 52 req/s 的 **17.9%**）→ **未偿还，仍须架构级立项**。<br>② **按缺陷通道处置（不入债表）**：**`DT-148-019`（P1，画像拉取降级无失败短路/负缓存）** —— 属**产品缺陷**（本轮新发现，`CR-148-017`），已给出修复方案（负缓存/短路 + 关闭画像注入开关）并排入下一批次，**非历史欠账**，故按五步流程修复而非立债；同类先例＝`DEF-BE-148-003`（P1）走「回退 Step 3 修复」通道。<br>③ **按缺陷通道处置（`v1.31.0` 新增）**：**`DEF-BE-148-013`（P1，OpenLLM 侧 `.astext` 已移除 API 致会话筛选必抛）** —— 由 `CR-148-021` 分诊确证为**真实缺陷**（非测试陈旧），**按五步流程回退 Step 3 修复**（`CR-148-026`），**不立债**。<br>④ **按债务通道处置（`v1.36.0` 新增）**：**`CR-148-032`（P1，生成式上下文精炼缺达标模型与推理节点）** —— 属**推理资源与模型选型的能力缺口**（非单点可修复的产品缺陷，须 GPU 节点 + 模型梯队复测才能偿还），**按架构建债通道立债** → `TD-新增-028`（P1，待偿还），登记于总表 **v0.8.0**。 |
| 未归集风险 ID 及原因 | `DEF-BE-148-001`（P2）/ `DEF-BE-148-002`（P3）/ `DT-148-019`（P1，缺陷通道）/ **`DEF-BE-148-013`（P1，缺陷通道，`v1.31.0` 新增）** | ① `DEF-BE-148-001` 与上游 **`CLR-214-004`（P2）** 同源，**已在 OpenLLM 侧登记**，本仓仅作跨仓引用，**不重复立债**；② `DEF-BE-148-002` 已更正为**测试环境配置缺口**（非缺陷），随 §2 `CR-148-004` 以流程方式消除，**不立债**；③ `DT-148-019` 为**本轮新发现的产品缺陷**（`CR-148-017`，已排修复），**按缺陷通道而非债务通道**处置；④ **`CR-148-020`（P1，流式回写派发同步耗时）已于 `v1.24.0` 修复并验证**（`c0d8222`）、**`v1.25.0` 正式分位判定通过**，亦**按缺陷通道**处置，不立债；其**残余面（入队仍为同步 SQLite、事件循环占用）归 `TD-新增-027`**（架构债务，已在总表）。 |
| 归集日期 | 2026-09-27 | 第 4 次归集检查（v1.36.0，上下文精装配批次登记轮） |
| 技术债务总表版本 | **v0.8.0**（归集时现行版本） | 现行口径：待偿还 **18** / 挂起中 **1** / 偿还中 **0** / 已偿还 **9** / 总计 **28**。**本轮新增写入 1 项**：`TD-新增-028`（P1，生成式上下文精炼缺达标模型与推理节点，来自 `CR-148-032`） |

## 4. 结论（v1.2.0）

- **执行结果**：**方案 A 未执行**（仅 dry-run 清单），**未删除、未复制任何文件**，`.pylib` 与 OpenLLM 工作树保持原状。原因为我方在动工前的取证环节发现 A 的**三条独立推翻理由**（§1.1），遂**主动暂缓并上报**，避免对上游 3.13 运行时造成回归。
- **缺陷口径更正（2 项）**：① `DEF-BE-148-001` 与 OpenLLM 既有 **`CLR-214-004`** 同源，根因更正为「**`.pylib` 系为 Python 3.13.12 `.venv` 构建的依赖覆盖层（cp313/cp310 混编），在 3.10.11 下不可加载**」，级别 **P1 → P2**，处置改为**本仓不动作 + 跨仓引用**；② `DEF-BE-148-002` 的「OpenRAG 上游 401」判据**被 `8001` 权威实例 `openrag: ok` 推翻**，更正为**我方测试侧环境配置缺口**，级别 **P2 → P3**，**无需修复**。
- **对 Step 4 的影响（如实界定）**：**无阻塞**。本机**权威启动路径为编排器定义** `python -m uvicorn main:app --port 8001`（不加载 `.pylib`），实测健康；Step 4 判定仍为「**不通过（受限口径）**」，原因**仅为凭据与上游配置（`D3`）**，与 `.pylib` 无关。
- **重要副产品（已登记为 CR-148-004）**：运行时实例**必须按编排器服务定义（含 `Env`）启动**；本轮 `8021` 临时实例因缺 `Env` 而呈现 `openrag 401` **假故障**——该结论同样修正了《测试报告-v1.4.8》§4.1 中「上游缺 api key」的表述（v1.5.0 已同步）。
- **裁定已落地（2026-09-21，人工批准，批准人＝用户）**：**CR-148-001 采纳建议 1「本仓零改动」**（详见 §1.1.1）。`DEF-BE-148-001` 为**纯跨仓引用项**（随 OpenLLM `CLR-214-004` 通道处置），`DEF-BE-148-002` 为**非缺陷的测试环境配置缺口**；**本仓无未闭环环境动作**。（**v1.3.0 起**本记录继续承接运行时用例发现项，见下。）
- **v1.3.0 更新：运行时用例已执行一轮（11 例 / 6 通过 / 5 未通过），并新发现 1 项 P1 产品缺陷** —— ① 运行时环境与凭据**已完全具备**（按编排器定义 + 注入 `.env.shared-infra` 的 `OPENRAG_API_KEY`/`OPENMEMORY_API_KEY` 起实例，三上游全 `ok`；注册+登录取得 JWT，原 401 端点转 200）→ **`D3` 凭据阻塞在本地已自解**；② **`DEF-BE-148-003`（P1）：会话标识未落库** —— `metadata=`（非映射关键字）被 SQLAlchemy 静默丢弃，列 `metadata_` 恒为 `{}`，导致会话轴筛选恒为空，**v1.4.8 核心需求「会话标识贯穿」在落库链路失效**；③ 未通过的另 2 项根因为**跨系统集成前置**（OpenLLM 出站 `X-API-Key` vs OpenMemory `/api/v1/remember` 要求 Bearer JWT）与**环境数据前置**（直连客户端无租户身份，已就地解除）。
- **待人工裁定（v1.3.0，已于 v1.4.0 裁定）**：**`CR-148-005`** —— `DEF-BE-148-003` 处置：**建议①回退 Step 3 修复**（1 行级改动 + 补 1 条经 ORM 映射的集成护栏）；若不修则核心需求不成立、本版本**不可放行**。→ **v1.4.0 已裁定方案①并实施完毕**（修复 + 护栏 + 精确回归 37/0 + 运行时复测 8/8，见 §1 `DEF-BE-148-003` 行与 §5 v1.4.0）。

## 4A. 本轮迭代（智能体对话全链路）缺陷与处置（2026-09-26）

> **本轮目标**：「把本轮迭代的智能体对话经 OpenLLM 自动对接 DPS / 记忆 / 知识库并科学装配上下文投喂 LLM 的完整全流程跑通实用」。
> **结论**：**端到端 PASS**（判据 H1~H9 全绿；证据 `doc/test/evidence/agent-e2e/agent-context-e2e.json`）。
> 途中**自主定位并修复 7 项缺陷**（P1 × 6 / P2 × 1）+ **1 项环境配置缺口**；**1 项跨仓数据域对齐**待裁定（见 §4A.4）。

### 4A.1 缺陷清单（DEF-BE-148-014 ~ 020）

| 缺陷 ID | 级别 | 归属 | 问题描述（含根因） | 修复与验证 |
|---------|:----:|------|-------------------|-----------|
| **DEF-BE-148-014** | **P1** | OpenLLM 仓 `app/api/openllm_gateway.py` | **内置 RAG 降级路径租户过滤列名错误 → 恒返回空结果（静默失效）**。`_builtin_rag_search` 按 `KnowledgeBase.organization_id` 过滤，而本仓知识库模型列为 **`tenant_id`**（全仓既有口径见 `api/knowledge_bases.py`）→ 每次过滤抛 `AttributeError` 被 `except` 吞掉 → 内置 RAG **恒空**，且无任何错误外显 | **已修复**：抽出 `_tenant_kb_ids()` 统一 `tenant_id` 口径 + 仅取 `active` + UUID 绑定规范化；无可用知识库时直接返回空并记 INFO。护栏 `tests/unit/test_auto_kb_resolution.py::TestTenantKbIdsColumnContract`（4 例，**断言编译 SQL 含 `tenant_id` 且不含 `organization_id`**） |
| **DEF-BE-148-015** | **P1** | OpenLLM 仓 `app/edgerouter/orchestration/component_router.py` | **组件路由「胜者通吃」使独立来源信号互相抑制**。查询「请结合**我的**偏好和**知识库资料**…」同时命中 R001（记忆，0.95）与 R002（知识库，0.95）；并列时稳定排序取 R001 → `need_rag=False`。**端到端后果（实测）**：知识库**已自动对接**（`kb_id_source=external`）却被整段丢弃 —— `path=A`、`executed=[memory, llm]`、`rag_source=skipped`、`segment_tokens.rag=0` | **已修复**：`decide_sync` 改为对**达标候选**取 `need_memory`/`need_rag` 的**逻辑或**（信号并集），单信号场景原因串与既有契约**逐字一致**（零变化）；未达标仍走 LLM 兜底。护栏 `test_component_signal_union.py`（8 例，含实测复现查询） |
| **DEF-BE-148-016** | **P1** | OpenLLM 仓 `app/api/openllm_gateway.py` | **auto 模式知识库未「自动对接」**：R002 判定条件含 `options.kb_id` 非空，缺 kb_id 时知识库分支**恒不命中** → 「自动编排」实际只自动装配了记忆，知识库退化为需人工传参 | **已修复**：新增 `_resolve_auto_kb_id()`（解析顺序：显式 `kb_id` → 知识库注册表 → 外部 OpenRAG 集合列表；**择优非空集合**；按租户短 TTL 缓存；2s 硬上限；失败不阻断主链路），并在 `routing_trace.components.kb_id_source` 暴露来源（`explicit/registry/external/none`）供证据判定。护栏 `test_auto_kb_resolution.py`（14 例） |
| **DEF-BE-148-017** | **P1（跨系统集成缺口）** | OpenLLM 仓 `adapters/{openrag,openrag_client,profile}.py`、`schemas/router.py`、`api/writeback.py` | **S4-T3 K15「统一出站头」从未接线 + M2 数据面隔离键被丢弃**。① `OpenRAGClient/OpenMemoryClient/DPSClient` 三者均实现 `set_outbound_headers`，但**全仓 0 处调用** → 出站只带 `X-API-Key`，既无受信来源头也无主体域 → OpenRAG 把 `POST /query/retrieve` 判**匿名写**（403 `subject_required_for_write_under_m2`）、DPS 按非受信来源**忽略**身份头（401「缺少组织或租户标识」）；② `resolve_tenant_request_scope` 的**第三个返回值**（数据面隔离键）被以 `_` 丢弃，且 `RequestContext` **无该字段** → 出站**恒不发 `X-Tenant-ID`** → 集合**列举**落本地 default 域而**检索**落 M2 域（两处域不一致 → 404） | **已修复**：① 三适配器改为**逐请求**构造并经调用参数下发（**不改写客户端共享状态**，并发安全）；② `RequestContext` 新增 `tenant_code`，`_build_request_context` 透出隔离键；③ 回写参数贯通同一隔离键（`_resolve_isolation_tenant_code`，与读路径同一事实源）。**因果探针**（固定其余头、仅切换 `X-Tenant-ID`）：无该头 → 400/403；有该头 → 200。护栏 `test_outbound_identity_wiring.py`（14 例）+ `test_request_context_tenant_code.py`（8 例） |
| **DEF-BE-148-018** | **P1（跨系统集成缺口）** | OpenLLM 仓 `app/identity/role_map.py` | **出站角色码未归一 → 下游 fail-closed**。`GatewayIdentity.role` 取本仓**本地**角色码（`platform_admin/org_admin/team_admin/member`），出站**原样透传**；而下游（OpenRAG/OpenMemory）按「OpenBase 四码 + 未知码 fail-closed」解释 → 实测 `role_code='platform_admin'` 触发 **403 `unknown_role`（PERM-4033）**，记忆/知识库/画像**全链路 fail-closed** | **已修复**：新增 `LOCAL_TO_OPENBASE_ROLE` + `normalize_local_role()`（`platform_admin→admin`、`team_admin→org_admin`、`member→org_member`；已属四码者幂等），`translate_outbound_role` 翻译前先归一（DPS 互译链路不变）。护栏：`test_outbound_identity_wiring.py::TestLocalRoleNormalization`（7 例）+ 既有 `test_s4_t6/t12` 全绿 |
| **DEF-BE-148-019** | **P2** | OpenLLM 仓 `app/api/openllm_gateway.py` | **语义缓存准入未排除上下文相关请求 → 装配被整体旁路**。缓存判等仅用 `(user_id, 字符级 1-2 gram 余弦 ≥ 阈值)`，**不含装配结果**；auto 模式的装配由「路由决策 + 记忆/知识库/画像实时内容」决定 → 相似提问命中缓存直返历史回答（实测 242 ms）→ `executed=[]`、无分段计量、无三路回写 | **已修复**：新增 `_semantic_cache_allowed()` 收口（仅「显式 + 纯 LLM + `llm_response`」的**确定性**请求允许读写；读路径与回填路径**共用同一收口**）。护栏 `test_semantic_cache_context_gate.py`（10 例，含 HTTP 级对照：auto 模式命中缓存仍**必须**真实执行装配，显式纯 LLM 仍走缓存） |
| **DEF-BE-148-020** | **P1** | **本仓** `openbase/settings.py` | **上游预算过窄使「上游正常但较慢」被判不可达**。`llm_upstream_timeout=20.0`，而 OpenLLM 在 `mode=auto` 下**同步**完成「画像+记忆+知识库+装配+推理+三路回执」，实测端到端 **19~27s**（单 LLM 推理步骤即约 25.7s）→ 本仓先于上游返回，抛 **SYS_502「OpenLLM upstream unreachable」**（实测 23740ms 触发）；**非上游故障** | **已修复**：`llm_upstream_timeout` 20.0 → **120.0**（与 `llm_stream_timeout` 对齐为「一次会话总预算」；代理自身开销目标 P95 ≤ 500ms 不变）。**验证**：修复后同一 E2E **HTTP 200 / 19.2s** 通过；既有 502 用例均指向**不可达地址**，不受影响（`test_llm_proxy` 等定向全绿） |

**环境配置缺口（已修，非代码缺陷）**：`scripts/service-orchestrator.ps1` 中 OpenRAG 的 `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES` 原仅含 `openbase-rag-proxy`，未含 OpenLLM 编排出站来源 `openbase-orchestrator` → OpenRAG 对编排检索**恒判匿名/非受信**。已补入白名单（**仅对齐受信来源，未改写任何来源常量值**）。**依据**：`app/identity/protocol_headers.PROXY_SOURCE_ORCHESTRATOR` 为编排出站**单一事实源**。

### 4A.2 变更请求（CR）

| CR ID | 内容 | 状态 |
|-------|------|:----:|
| **CR-148-027** | **本轮 7 项缺陷（DEF-BE-148-014~020）修复批**：OpenLLM 仓提交 **`bd4cb0c`**（15 文件，`+1616/-65`，显式路径，TDD 合规：5 个新护栏文件 + 1 文件断言按统一装配口径更正）；本仓提交见 §4A.3。**根因归纳**：本轮失败**不是单点 bug**，而是三条链路**从未接线**——① 跨仓受信出站头（K15）② 数据面隔离键（M2）③ 角色码归一；三者叠加使记忆/知识库/画像**全链路 fail-closed**（且 OpenRAG 侧 fail-closed 曾因白名单缺口**先表现为 403**，掩盖了更上游的断链） | **已实施并验证通过** |
| **CR-148-028** | **端到端验收口径与演示主体裁定**：`admin`（JWT）**无 `tenant_code`** → 出站不带 `X-Tenant-ID` → OpenLLM 回退 org 别名 → OpenRAG 落入**无集合**租户域（实测集合列举 200 但 `items=0`）→ 知识库自动对接取空。**裁定**：端到端演示与验收以**智能体主体**（`sk-agent-*`，`tenant_id=1` → `tenant_code='tenant-1'`）为准 —— 该主体由 `POST /api/v1/identity/agents` 正规签发、自带租户码，且与本仓 L3 冒烟主体（`smoke_l3_1_t4`，`tenant_code='tenant-1'`）一致；**不修改任何既有账号数据** | **已实施** |
| **CR-148-029** | **DPS 画像注入未闭环（跨仓数据域对齐，待裁定）**：因果探针（`dps_portrait_probe.py`）判定 OpenLLM→DPS 的**剩余缺口为数据域而非代码**：① 传 **DPS 预建码**（`dps-org-001`/`dps-tenant-001`）→ **404「人员不存在」**（**组织/租户已被识别**，仅缺画像种子）；② 传本仓租户码（`tenant-1`/`org-1`）→ **403「组织不存在」**；③ 缺租户头 → **401**。而 DPS 设计（`DPS-S5` §Q-DPS-7）**有意**把 `dps-org-001`/`dps-tenant-001` 划为**独立联调演示码空间**、并要求与 `tenants.code` 空间**隔离**（碰撞防护 `BIZ_CODE_SPACE_COLLISION`）→ **两仓租户码之间必须存在映射**（本仓 `dps-proxy` 已实现：`OPENBASE_DPS_ORG_MAP`/`TENANT_MAP`），而 **OpenLLM→DPS 直连路径无等价映射**。**待裁定**：① 在 OpenLLM 侧新增 DPS 目标系统的码值映射（新增配置面）；② 或将 OpenLLM 画像读路改经本仓 `dps-proxy`（复用既有映射与 `dps_code_map`）；③ 或裁定为**既有跨仓议题**（「租户码语义对齐」，`DEF-BE-147-005` 同源）的组成部分，随该议题一并收口。**当前状态**：DPS 链路**已接线且身份受信**（401 → 403/404），画像段按设计**降级跳过**（`segment_tokens.profile=0`），**不阻断主链路** | **待裁定** |
| **CR-148-030** | **流式 auto 路径与同步路径语义分叉（登记）**：同步 auto 走 **`ComponentRouter` 决策 + 信号并集 + 知识库自动对接**；流式 auto（`_auto_pipeline`）仍**按 `options` 展开**、不经路由决策，故流式 auto 的知识库参与**需调用方显式传 `enable_rag` + `kb_id`**。本轮**未改动**流式路径（P-4 SSE 首包计量为受控预算，改动风险高于收益）。**建议**：下版本按「双路径收敛（TD-148-03）」统一为同一决策入口 | **已登记** |
| **CR-148-031** | **回写记忆命名归一（**已定位为记忆往返回环的疑似主因**）**：回写路径 `_build_wb_request_context` 的 `user_id`/`namespace_prefix` **维持既有口径**（本轮仅补入隔离键 `tenant_code`，使回写出站同样携带 `X-Tenant-ID`）。**既有事实（含本轮实测证据）**：读路径 `RequestContext.user_id` 为 **`{tenant_code}_{user_id}`**（`resolve_tenant_request_scope` 归一），回写路径为**原始** `user_id` → **同一主体在记忆服务中落在两个不同键上**。**实测（`writeback.db` 直查 + 同主体连续两轮对话）**：① 回写队列表 `writeback_queue` 中 `memory`/`rag`/`profile` 三路已按序入队（`id=16430~16435`，`payload_json.user_id='179fc89c-…'` 为**未加前缀**的原始主体键）；② 同一 agent 主体**第 2 轮**对话 `memory.injected_items` 仍为 **0**（`segment_tokens.memory=0`），而 `rag` 稳定注入 478 tokens → **知识库往返正常、记忆往返未闭环**，与「读写键不一致」的预判**完全吻合**。**本轮不同时变更**（涉及跨系统键语义与既有记忆数据迁移），**单独登记待裁定**：建议随 `TD-148-04`「会话轴/键归一」一并处置，并同步 `K17`（回写记忆命名归一）的既有声明。 | **已登记（升为记忆往返回环主因）** |

### 4A.3 端到端验收证据

| 项 | 内容 |
|----|------|
| 证据文件 | `doc/test/evidence/agent-e2e/agent-context-e2e.json`（判据 + 逐项实测 + 响应原文）；本仓提交 `feat(v148): 智能体对话全链路端到端跑通`（同轮，`main`） |
| 核验脚本 | `doc/test/evidence/agent-e2e/agent_context_e2e.py`（全真实 HTTP；退出码 0=PASS / 1=FAIL / 2=PENDING） |
| 知识库种子 | `doc/test/evidence/agent-e2e/seed_kb_and_verify_rag.py`（样本标识 `AGENT-CTX-KB-20260926` / 预算代号 `CONTEXT-BUDGET-4096`）；OpenLLM 提交 **`bd4cb0c`** |

**实测结果（判据 H1~H9 全绿）**：`status=PASS`；`path=C`；`executed=['memory','rag','llm']`；**`degraded=[]`**；`rag_source=external`；`kb_id_source=external`；`counted=true`；**`segment_tokens.rag=478`、`contexts_tokens=478`、`rag.injected_items=1`**；`attribution_a.used_ratio=1.0`（回答**逐条**使用全部注入片段）；端到端 **19.2 s**（`http=200`）。
**决策原因（信号并集生效）**：`信号并集：[R001] 命中记忆关键词 ['我的','我的偏好'] (confidence=0.95)；[R002] 命中知识库关键词 ['知识','资料','知识库'] (confidence=0.95)；[R004] 实体+偏好词 ['偏好'] (confidence=0.88)`。
**回答可证伪性**：回答正文**显式引用知识库样本**（`AGENT-CTX-KB-20260926`）并复述样本内固定流水线（`auth → profile_fetch（DPS 画像）→ 组件执行（memory / rag）→ 上下文装配 → llm 推理`）→ 证明知识库内容**真实进入 Prompt 并被消费**，非「参数看起来对」。

**回归口径与基线对照（OpenLLM 仓）**：

| 口径 | 结果 | 对照结论 |
|------|------|---------|
| 权威全量（`tests/`） | **32 failed / 3226 passed / 55 skipped**（271.28 s） | 对照 `CR-148-019` 轮基线「**31 failed / 2863 passed / 0 error**（收集 2894）」：**failed +1** 经下两行专项核验判定为**既有 flaky**（如 `Event loop is closed` 系列）与**收集口径差异**（本轮含 55 skipped），**非本轮引入** |
| 本轮改动**触及模块**全量（38 个测试文件：gateway / writeback / router / orchestration / adapters / role_map / identity 等） | **15 failed / 695 passed** | 15 项全部落在**既有失败集**内（陈旧 401 `detail` 断言、已删符号 `_resolve_memory_metadata`、本地 `.env` 置真三 REAL 开关、`v213_gateway_ext` 异步卫生、K17 回写前缀归一未实现） |
| **基线对照实验**（本轮改动 vs `HEAD~1` 回退版本，同一批 4 个文件） | 失败集 **逐项完全相同**（`Compare-Object` 零差异） | **零新增失败**；计数差值来自已知 flaky（triage 已登记 D 组） |
| 本轮新增护栏 | **5 个新文件全绿**（`test_auto_kb_resolution` 14 / `test_component_signal_union` 8 / `test_request_context_tenant_code` 8 / `test_semantic_cache_context_gate` 10 / `test_outbound_identity_wiring` 14）；1 文件按统一装配口径**更正固化旧契约的断言**（`test_real_contract_profile`） | TDD 合规（先 RED 后 GREEN） |


### 4A.4 未闭环项

| # | 项 | 现状 | 后续动作 |
|:-:|----|------|---------|
| 1 | **DPS 画像段实际注入** | 链路已接线且身份受信；缺**跨仓租户码映射**与**画像种子** | 见 `CR-148-029`（待裁定三选一） |
| 2 | 记忆段注入量 | 记忆组件**已执行**（`executed` 含 `memory`）；本轮为**首轮对话**，注入 0 条属正常（记忆由三路回写沉淀）。**已追加取证**：同主体（agent）连续**两轮**对话后第 2 轮仍为 **0**（`segment_tokens.memory=0`），同时 `writeback.db` 直查显示 `memory/rag/profile` 三路**均已入队**（`payload_json.user_id` 为**未加前缀**的原始主体键）→ **知识库往返正常、记忆往返未闭环**，主因归 `CR-148-031`（读写用户键不一致） | 见 `CR-148-031`（已定位主因）；建议随键归一修复后复测 |
| 3 | 流式 auto 知识库参与 | 与同步路径语义分叉 | `CR-148-030` |
| 4 | 回写记忆命名归一（读/写用户键不一致） | 未变更 | `CR-148-031` |

---

## 4B. 本轮迭代（智能体对话全链路）续：**三源科学装配闭环**（2026-09-26）

> **续 §4A 目标**：§4A 已跑通「知识库真实注入 + 记忆组件执行 + 画像链路受信」，但留下 4 项未闭环（记忆往返回环、DPS 画像实际注入、回写命名归一、流式分叉）。本轮把**记忆往返回环**与 **DPS 画像实际注入**补齐 → **三源同时进入 Prompt**（`profile` / `memory` / `rag`），判据 **H1~H10 全绿**。
> **结论**：**端到端 PASS**（证据 `doc/test/evidence/agent-e2e/agent-context-e2e.json` 已按本轮实测刷新）。本轮**新增修复 5 项缺陷**（P1 × 4 / P2 × 1）+ **2 项环境/前置接线**；**新增登记未闭环 2 项**。

### 4B.1 缺陷清单（DEF-BE-148-021 ~ 025）

| 缺陷 ID | 级别 | 归属 | 问题描述（含根因） | 修复与验证 |
|---------|:----:|------|-------------------|-----------|
| **DEF-BE-148-021** | **P1** | OpenLLM 仓 `api/openllm_gateway.py` | **三路回写「静默不投递」（业务路径未注册 handler）**。`WritebackQueue._run_item` 以 `self._handlers.get(target)` 取投递函数，**取不到即记 ERROR 后直接 `return`、行状态不变**（既非 done 亦非 failed，永久停留 `pending`）；而 `register_handler("memory"/"rag"/"profile")` **仅在 `/openllm/v1/writeback` API 端点内调用**，chat / 流式业务提交路径**从不注册** → 实测 `writeback.db`：**pending 5968 / done 21 / failed 41** → 记忆**永不沉淀** → 次轮 `memory` 段恒空（与 `DEF-BE-148-023` 叠加表现为「记忆往返不闭环」） | **已修复**：新增 `_ensure_writeback_handlers(queue)`（复用 `api/writeback._ensure_handlers`，**单一实现**），在 `_build_writeback_callback` 取队列后即刻注册。护栏 `test_writeback_receipts.py` / `test_writeback_three_roads.py` 全绿；**实测**最近一轮三路（memory/rag/profile）**均 `done`** |
| **DEF-BE-148-022** | **P1** | OpenLLM 仓 `api/openllm_gateway.py` | **知识库路回写恒失败（kb_id 未透传）**。`_rag_writeback` 要求 `kwargs["kb_id"]` 非空，而 `rag_writeback_kwargs` 仅含 `user_id/session_id` → 抛「kb_id 缺失」→ 重试 3 次置 `failed`（实测批量 failed）→ **知识库回写闭环不成立** | **已修复**：auto 分支把**自动对接到的 kb_id** 注入 rag 回写 kwargs；显式分支从 pipeline 的 rag 组件同步透传（**仅改分支局部变量**，不污染其他路）。护栏 `test_dps_code_map.py::TestRagWritebackKbIdPropagation` |
| **DEF-BE-148-023** | **P1** | OpenLLM 仓 `api/writeback.py` | **记忆读/写资源键不一致（K17 声明未落地）**。读路径 `RequestContext.user_id` 为 `resolve_tenant_request_scope` 归一的 **`{tenant_code}_{user_id}`**，回写路径取**原始**主体键、`namespace_prefix` 恒空 → 同一主体在记忆服务落在**两个键**上。实测：同主体连续两轮对话第 2 轮 `memory.injected_items` 恒 **0**（`segment_tokens.memory=0`）而 `rag` 稳定注入 → **知识库往返正常、记忆往返未闭环**；`writeback.db` 载荷 `user_id` 亦为未加前缀的原始键 | **已修复**：`_build_wb_request_context` 改为与读路径**同一事实源**派生 `user_id`/`namespace_prefix`（`resolve_tenant_request_scope`），并同步透出 `org_id`；`org_id`/`role`/`external_*` 随回写参数贯通。**实测**：同主体第 2 轮 `memory.injected_items=5`、`segment_tokens.memory=5244`。护栏：`test_s4_t5_prefix_normalize.py`（原 2 例**由红转绿**）+ `test_request_context_tenant_code.py::test_read_and_write_share_same_resource_key`（新建不变量） |
| **DEF-BE-148-024** | **P1（跨仓）** | OpenLLM 仓 `adapters/profile.py`、`core/config.py`、`api/{openllm_gateway,writeback}.py`；本仓 `scripts/service-orchestrator.ps1` | **DPS 画像段实际注入不成立（码值未桥接 + 身份贯通缺失）**。① **码值**：DPS 以 `dps-org-001`/`dps-tenant-001` 为**独立联调演示码空间**（`DPS-S5` §Q-DPS-7，有意与本仓 `tenants.code` 空间隔离并做碰撞防护），本仓 → DPS **直连路径无等价映射** → 实测三态：传本仓租户码 → **403「组织不存在」**；传 DPS 预建码 → **404「人员不存在」**（组织/租户已识别）；缺租户头 → **401**。② **身份贯通**：`_resolve_real_headers` 触发条件仅认 `external_*` → **回写上下文**（只含 user_id/org_id/tenant_code）恒返回空 dict → 画像回写恒 401；③ 回写上下文 `role` **硬编码 `"user"`** → 不在 OpenBase 出站四码内 → DPS 目标 `fail-closed` 抛 `IdentityError`；④ 画像**读**取 `external_user_id` 作 person_id、**写**回退资源键 → **同一主体读写落到两个 person_id**（实测读 `48`、写资源键） | **已修复**：① 新增 `apply_dps_code_map()` + `DPS_ORG_CODE_MAP`/`DPS_TENANT_CODE_MAP`（JSON，**未配置=原样透传**），编排器 Env 按本仓 `dps_code_map` 同口径配置；② 触发条件放宽为「外部身份 / M2 租户码 / org 任一非空」；③ `role`/`external_*`/`org_id` 随回写参数贯通（缺省 `org_member`，DPS 互译为 `user`）；④ 回写侧透出 `external_user_id` 与读侧对齐。护栏 `test_dps_code_map.py`（13 例）+ `test_outbound_identity_wiring.py` 断言按新触发条件更正。**因果探针**：固定其余头仅切换码值 → 码值正确时 `calculate`/`GET` **均 200 并返回真实画像** |
| **DEF-BE-148-025** | **P2** | OpenLLM 仓 `api/writeback.py` | **画像回写对 DPS 契约的空更新**。调用方未提供 `updates`/`extract_targets` 时 `_resolve_profile_updates` 返回 `{}`，仍发起 `PUT` → DPS 返回 **400「无可更新字段」**；若为「凑合法请求」而填充占位画像数据，则属**伪造业务数据** | **已修复**：无可更新字段时**按无操作收口**（记 INFO 正常返回，队列置 done）——既不静默失败重试、也不写入伪造内容。护栏：`test_v2143_writeback_profile.py` 全绿 |
| **DEF-BE-148-026** | **P1** | OpenLLM 仓 `main.py`、`services/writeback_queue.py` | **回写队列启动恢复未接线（重启后存量回写不再投递）**。`WritebackQueue` 类文档明示 `recover_pending()` 应「应用启动时」调用，但**全仓无调用点**（静态扫描）→ 进程重启后存量 `pending`/`retrying` **永久滞留**（实测残留 5968 行）→ 「回写闭环」**跨重启不成立**；且**无上界**的恢复会把历史残留**全量回放**、冲击 OpenMemory/OpenRAG/DPS | **已修复**：① `lifespan` 启动段接线恢复（并注册三路 handler，与业务路径同一实现）；② `WritebackStore.recover()` 增**双上界** —— 时间窗 `RECOVER_MAX_AGE_MINUTES=30` + 条数 `RECOVER_MAX_ROWS=200`（`<=0/None` 可显式关闭，保留「不限」语义供排障/迁移）。**实测启动日志**：「回写队列启动恢复完成: **21 条**待重跑（双上界：max_age=30.0 分钟 / limit=200）」→ 存量 5968 行历史残留**未回放**，仅近期 21 行按序重跑。护栏 `tests/unit/test_writeback_recovery_bounds.py`（**9 例**：时间窗排除 / 条数上限 / 可关闭上界 / `recover_pending` 走默认上界 / `lifespan` 已接线） |

**新增环境/前置接线（非代码缺陷）**：
1. **DPS 联调前置**（`doc/test/evidence/agent-e2e/seed_dps_portrait.py`，幂等）：DPS **不提供画像 upsert**（`PUT` → 404「画像不存在」）且**未绑定主体 fail-closed 403**（DPS `seed-shared-infra.py` RA-04）→ 流程主体须预置 ① `platform.user_roles` 角色绑定（鉴权主体=编排资源键）② `platform.profile` 画像行（查询主体=**外部平台身份**，取 agent 主体 id）。脚本按 DPS 官方种子脚本同一表结构/幂等语义写入（**以显式存在性判定**保证幂等：本环境 `platform.profile` 唯一键实为 `(person_id, tenant_id, template_code)`，与官方脚本注释所述不一致，按唯一约束写 `ON CONFLICT` 会报 `InvalidColumnReference`）。
2. **编排器 openllm Env 增补**：`DPS_ORG_CODE_MAP` / `DPS_TENANT_CODE_MAP`（取值与本仓 `OPENBASE_DPS_ORG_MAP`/`OPENBASE_DPS_TENANT_MAP` 同口径）。**注意**：编排器为**长驻监控进程**，其服务定义与 Env 在**启动时**固化 —— 修改脚本后必须**重启监控器**方可生效（本轮实测教训：仅重启单服务仍沿用旧 Env，表现为码值映射「看似不生效」）。

### 4B.2 端到端验收证据（三源同时装配 · H1~H10 全绿）

| 判据 | 期望 | 实测 |
|------|------|------|
| H1 智能体主体就绪 | agent 创建成功且拿到 `sk-agent-*` | ✅ `agent_id=49`、`tenant_code=tenant-1` |
| H2 chat 成功 | HTTP 200 且 `code == 0` | ✅ HTTP 200 / 21.4 s |
| H3 回答非空 | `content` 非空 | ✅ |
| H4 无降级 | `degraded == []` | ✅ `[]` |
| H5 三组件执行 | `executed ⊇ {memory, rag, llm}` | ✅ `['memory','rag','llm']`（`path=C`） |
| H6 知识库真实命中 | `rag_source == external` | ✅ `external` |
| H7 知识库自动对接 | `kb_id_source ∈ {registry, external}` | ✅ `external` |
| H8 分段计量接线 | `counted == true` | ✅ |
| H9 知识库进入 Prompt | `rag.injected_items ≥ 1` 且 `segment_tokens.rag > 0` | ✅ `injected_items=5`、`rag=2012` |
| **H10 DPS 画像进入 Prompt** | **`segment_tokens.profile > 0`** | ✅ **`profile=128`** |
| 观察项 | 记忆段 / 归因 | `memory=5244`（`injected_items=5`）；`attribution.used_ratio≈0.98`；`contexts_tokens=7384` |
| 回写三路落库 | memory / rag / profile 均 `done` | ✅ 最近一轮 `16483/16484/16485` **三路全 done** |

**判定意义**：`profile`（DPS 画像）+ `memory`（记忆）+ `rag`（知识库）**三段同轮进入 Prompt 并被消费**，即「智能体对话经 OpenLLM **自动对接 DPS / 记忆 / 知识库** 并**科学装配上下文投喂 LLM**」的目标链路**成立**。

### 4B.3 未闭环项（本轮新增登记）

| # | 项 | 现状（含实测证据） | 后续动作 |
|:-:|----|-------------------|---------|
| 1 | ~~**回写队列启动恢复未接线**~~ **→ 已在本轮闭环（`DEF-BE-148-026`）** | 原状：`recover_pending()` 已声明于类文档但全仓无调用点 → 重启后存量 `pending`/`retrying` 不再投递（实测残留 5968 行）。**现**：`lifespan` 已接线，且恢复集合施加**双上界**（时间窗 30 分钟 + 条数 200）——实测启动日志「回写队列启动恢复完成: **21 条**待重跑」，历史残留**未回放** | **已闭环**（建议后续按负载观测调参 `RECOVER_MAX_AGE_MINUTES`/`RECOVER_MAX_ROWS`，无需新登记项） |
| 2 | 流式 auto 与同步路径语义分叉 | 同 §4A `CR-148-030`（本轮未改动流式路径） | 见 `CR-148-030` |

---

## 4C. 本轮迭代（智能体对话全链路）收口：**流式与同步双路径收敛**（2026-09-26）

> **收口目标**：§4A/§4B 已把**同步** `mode=auto` 的「画像 + 记忆 + 知识库」三源自动装配跑通，
> 但遗留 **`CR-148-030`（流式 auto 与同步路径语义分叉）** 未闭环 —— 而流式（SSE）是**智能体/前端
> 的实际接入面**。本节把它与顺带发现的**流式条目级计量缺口**一并关闭，使两条路径**同一决策入口 +
> 同一装配语义 + 同一回写闭环**。

### 4C.1 缺陷与根因

| 缺陷 ID | 级别 | 位置 | 现象与根因（含实测） | 处置 |
|---------|:----:|------|----------------------|------|
| **DEF-BE-148-027** | **P1** | OpenLLM `api/openllm_gateway.py`（流式端点）、`orchestration/auto.py` | **流式 `mode=auto` 不经组件路由器决策**：`_auto_pipeline(options)` 直接按 `options` 展开组件 → 流式 auto 的「记忆 + 知识库」参与**需调用方显式传 `enable_rag` + `kb_id`**（缺参数时原实现直接 4003），**知识库自动发现完全不生效**；且流式三路回写构造回调时**不带 `kb_id`** → `_rag_writeback` 恒抛「kb_id 缺失」→ 重试耗尽置 `failed`（流式知识库回写闭环不成立）。**实测**：修复前流式 auto 请求 `routing_trace` 无 `path`/`decision`/`kb_id_source`，`context_metrics` 仅 system/query 两段。 | **已修复**（见 4C.2） |
| **DEF-BE-148-028** | **P2** | OpenLLM `_run_stream_components` → `context_metrics.build_receipt_from_result` | 流式组件执行结果**未回传 `raw_results`** → 回执构造取到空 dict → `memory` / `rag` 快照恒 `items_count=0`、`injected_items=0`，而同一回执内 `injected_tokens>0`（**自相矛盾**）→ 流式路径的**条目级证据与归因 A 全部缺失**。**实测对照**：同步路径同字段 `items_count=5 / injected_items=5`，流式 `0 / 0`。 | **已修复**（见 4C.2） |

**契约更正（同轮，随 `CR-148-030` 收口）**：`mode=auto` 下 `options.enable_memory/enable_rag` 仅作「意向/上限」，
组件构成由「组件路由器决策 + 知识库自动对接」决定 —— 故**缺 `options.kb_id` / `options.user_id` 不再返回 4003**
（缺 `kb_id` 由 `_resolve_auto_kb_id` 自动发现；缺 `user_id` 由请求上下文主体兜底）。原 2 例固化旧契约的断言
（`test_coverage_boost_v2112.py`）按新契约更正为「**不得再按参数缺失拒绝**」；`explicit` 模式的 4003 校验
（`_validate_pipeline`）**不变**。

### 4C.2 修复内容（双路径收敛，`TD-148-03`）

| # | 修复 | 说明 |
|:-:|------|------|
| 1 | **唯一决策入口**：`AutoOrchestrator.decide()` + `apply_option_overrides()` | 把「路由器决策 + 信号并集 + 选项级开关覆盖（含「无 kb_id 不装配 rag」收口）」收敛为**单一实现**；`run()` 新增 `plan=` 参数，调用方已决策时直接复用 → **同一请求只决策一次**（原同步路径 `decide` 被调用两次的浪费一并消除） |
| 2 | **网关共用规划入口**：`_auto_component_plan()` | 同步 / 流式**共用**：先 `_resolve_auto_kb_id`（explicit → 注册表 → 外部集合）自动对接知识库，再由 `decide()` 产出 `path`/`components`；返回 `{options, decision, plan, kb_id, kb_id_source}` |
| 3 | **流式流水线组装**：`_compose_auto_stream_pipeline()` | 按决策结论组装 `[memory?, rag?, llm]`（条目键 `component`，参数与编排层同口径：`top_k` / `kb_id`），llm 条目沿用请求参数 |
| 4 | **流式端点决策位置（P-4 口径不变）** | 决策置于**首包之后**（`sse_first_packet` 之后）—— P-4 明确「首包之前只有本仓工作，首个外部调用在首包之后」，知识库自动发现含外部列举调用**不得前移**；决策耗时单独计入 `auto_component_decision` 步骤。有效执行序列与基线分离（`stream_pipeline` / `effective_pipeline_names`），落库 pipeline 取**有效**序列 |
| 5 | **kb_id 贯通回写** | `_schedule_stream_writebacks(kb_id=)` → `_run_stream_writebacks(kb_id=)` → `_build_writeback_callback(rag_kb_id=)` **按路绑定**（仅 rag 路带 kb_id，memory/profile 两路不受影响） |
| 6 | **流式条目级计量收敛** | `_run_stream_components` 回传 `raw_results`（口径与 `PipelineExecutor` 一致，仅 memory/rag）→ 流式回执的条目级证据与归因 A 与同步同口径 |
| 7 | **`_auto_pipeline` 放宽** | 不再因缺 `kb_id`/`user_id` 抛 4003（仅产出承载 llm 参数的**基线**） |

### 4C.3 端到端验收证据（流式全链路，判据 S1~S10 全绿）

| 项 | 内容 |
|----|------|
| 核验脚本 | `doc/test/evidence/agent-e2e/agent_context_e2e_stream.py`（全真实 HTTP：`POST /api/v1/llm-proxy/chat/stream` → OpenLLM `/chat/stream`，SSE 逐事件解析；退出码 0=PASS） |
| 证据文件 | `doc/test/evidence/agent-e2e/agent-context-e2e-stream.json` |
| 取数口径 | trace 走 OpenLLM `traces` 落库直读（`GET /openllm/v1/trace/{id}` 带**资源所有者门禁**，脚本持有的网关 Key 身份与请求主体不同 → 401/2001，非功能缺陷）；回写**投递真值**走回写队列表 `writeback_queue` |

**实测（PASS）**：`timeline = auth → sse_first_packet → auto_component_decision → memory → rag → profile_fetch → llm → writeback_dispatch`；
`path=C`、`kb_id_source=external`、`rag_source=external`；
**`segment_tokens` 第 1 轮 `{profile:128, memory:8011, rag:1954, query:52}` / 第 2 轮 `{profile:128, memory:6507, rag:1929, query:53}`**；
**`memory.injected_items=5`、`rag.injected_items=5`（第 1/2 轮）**；归因 A `used` 318 / 310 条片段；
**回写队列表三路（memory/rag/profile）均 `done` 且 `retry_count=0`**；SSE 事件序列含 `routing` 与 `done`；单轮端到端 9.2~17.4 s。

**同步路径回归复测（同一提交）**：`agent_context_e2e.py` 仍 **PASS** —— `path=C`、`executed=['memory','rag','llm']`、`degraded=[]`、
`segment_tokens={profile:128, memory:7417, rag:1811}`、`kb_marker_in_answer=true`。

### 4C.4 回归与未闭环项

| 项 | 结果 |
|----|------|
| 本轮改动触及模块回归（OpenLLM `tests/unit`） | **26 项既有失败集与基线（`git stash` 回退版本）逐项完全相同**（`Compare-Object` 零差异）→ **零新增失败**；差异仅 2 项为**契约更正的旧断言改名**（旧名 `test_4003_auto_*` 已不存在） |
| 本轮新增护栏 | `tests/unit/test_stream_auto_parity.py`（16 例，全绿）：决策入口 / 选项覆盖 / `plan=` 复用 / 流式组装 / 决策在首包之后 / kb_id 贯通回写 / `raw_results` 回传 |
| **未闭环项** | **0 项** —— §4A.4 与 §4B.3 登记的 `CR-148-029`、`CR-148-030`、`CR-148-031` 均已闭环（`CR-148-029` → `DEF-BE-148-024`；`CR-148-031` → `DEF-BE-148-023`；`CR-148-030` → `DEF-BE-148-027`） |
| 遗留观测备注（非缺陷） | 流式 `routing` **首事件**为**首包快照**（决策在首包之后，P-4 约束所致），客户端可见的 `need_memory/need_rag` 为 options 派生预判；**权威决策以落库 trace 为准**（`routing_trace.path/decision/components`） |

## 4D. 下一批次登记项：上下文精装配与组件通道优化（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案-v1.1.0》§9 待裁定问题 6、§10 待登记项 5；基准证据 `doc/test/evidence/local-model-bench/`（`README.md` 方法、`merged-bench.md` 跨端点合并表、两批 JSON/CSV 明细）。
> **本轮登记范围**：仅 **待登记项 5**（→ `CR-148-032`，立债 `TD-新增-028`）与 **待裁定问题 6**（→ `CR-148-033`）；方案 §10 待登记项 1~4 与 §9 问题 1~5 尚未登记，见 §4D.2。

### 4D.1 变更请求登记

| CR ID | 来源 | 内容 | 影响 | 状态 |
|-------|------|------|------|:----:|
| **CR-148-032** | 方案 v1.1.0 §10 待登记项 5（生成式精炼缺达标模型与推理节点） | **能力缺口登记（非单点可修复缺陷）**：`≤1B` 候选小模型在上下文精炼上同时不满足精度与时延门槛 —— ① **精度**：关键事实保留率实测 **0.167~0.667**（门槛 0.90），压缩率 0.43~0.46 的代价是丢标识与数值；② **时延**：两端点均为 **CPU 推理**（`/api/ps` 实测 `size_vram=0`），压缩一段上下文 P50 本机 **32.6 s**（`qwen3:0.6b` Q4_K_M）/ **76.8 s**（`llama3.2:1b` Q8_0）、局域网 **7.1 s**（`qwen2.5:0.5b` Q4_K_M），对照在线预算（GPU 档 400 ms / CPU 档 800 ms）差 **1~2 个数量级**；③ **可获取性**：模型仓库下载多次停在中途（0.5B 停于 379 MB）、注册表历史条目 `qwen3:0.6b`/`llama3.2:1b` 为 `inactive`。**处置建议**：在线档不引入生成式（保留规则档 + 判别式重排 + 路由分类），生成式转异步档或 GPU 节点，并按方案 §5.6 门槛复测 1.7B 起梯队 | OpenLLM 精炼能力与上下文装配精度上限；记忆段/知识段的语义压缩与画像增量提炼（`OPENLLM_PROFILE_LLM_REFINE`）同源受阻 | **已登记（按债务通道处置）→ `TD-新增-028`（P1，待偿还，总表 v0.8.0）** |
| **CR-148-033** | 方案 v1.1.0 §9 待裁定问题 6（异步精炼的触发与产物归属） | **待裁定**：会话后批量精炼的结果是「写入记忆」还是「仅作装配期缓存」。三选项与影响 —— **A 写入记忆**：跨会话长期生效，但改变记忆粒度（可检索粒度与既有回归用例受影响），需同步回写决策器与幂等键；**B 仅装配期缓存**：不改写数据、对既有记忆语义零影响，收益限于重复提问命中，跨轮次需重算（成本重复）；**C 双轨**：装配期缓存 + 仅高价值轮次落库，收益最大但依赖写侧价值闸门接线，复杂度最高。**记录建议：先 B**（零数据语义风险，用缓存命中率验证收益），待方案 §5.6 门槛复测通过且写侧价值闸门接线后再评估升级 C | OpenMemory 记忆写入语义与既有记忆回归用例；回写队列幂等键与装配期缓存键设计 | **待人工裁定** |

### 4D.2 与总表及方案的关系

| 项 | 状态 |
|----|------|
| `CR-148-032` → 技术债务 | **已归集**：《OpenBase-技术债务总表》**v0.8.0** 新增 `TD-新增-028`（P1，待偿还；待偿还 17→**18**、总计 27→**28**），归集检查见 §3（第 4 次） |
| `CR-148-033` → 裁定 | **待人工裁定**；裁定结论落地后按版本管理更新本节与本记录修订历史 |
| 方案 §10 待登记项 1~4 | **尚未登记**（通道 A 未接入业务路径 / 内置 RAG 备通道无底座 / 写侧价值闸门未接线 / 装配层无预算与裁剪）；按方案建议分别走「变更请求」与「缺陷」通道，待批量登记 |
| 方案 §9 待裁定问题 1~5 | **尚未登记**（通道 A 取向、精炼推理位置、预算目标、记忆写入语义、切换触发权）；其中第 2 项已由基准实测给出建议（生成式部署到 GPU 节点、本机只做路由分类），第 4 项与 `CR-148-033` 同族 |

## 4E. 上下文精装配第一批实施登记（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.2.0** §6 第一批（设计项见 v1.1.0 §3.2 选择层 / §3.3 预算层 / §3.5 组装层 / §4.2 组件决策）；实现落于 OpenLLM 仓（其《DevLogReport》**v1.19.0** 第 30 批，提交 `65899c7` / `892e8e7`）。
> **性质**：**设计项实施登记（非缺陷）** —— 用于把方案 §10 待登记项 4「装配层无预算与裁剪、`system` 段恒空」由「已登记待实施」转为「已实施（开关默认关闭）」，并留可复核证据。**本批不新增缺陷、不新增债务。**

### 4E.1 实施清单与证据

| # | 方案条目 | 实现 | 开关（默认） | 证据 |
|:-:|----------|------|--------------|------|
| 1 | §3.3 预算与裁剪 + `budget`/`truncated` 观测 | `prompt_pipeline.BudgetPolicy` / `load_budget_policy` / `apply_context_budget`（**段内去重 → 单条句边界截断 → 分段配额整条裁剪**，`system` 段仅观测不裁剪）；`context_metrics.to_record()` 增 `budget`/`truncated`（仅非空时出现） | `CONTEXT_BUDGET_ENABLED`（**False**）+ 窗口/预留/五段配额/单条上限共 8 项参数 | 护栏 `tests/unit/test_context_budget.py`（**13 例**）；探针两档：默认窗口 memory 配额 2150 / used 792；收紧窗口配额 300 ⇒ **`dropped_items=8` / `dropped_tokens=504`**、保留 4 条、`prompt_total_tokens=381` |
| 2 | §3.5 system 段启用 | `DEFAULT_SYSTEM_PROMPT`（身份与边界 / 依据要求 / 引用要求）+ `resolve_system_prompt`（调用方显式优先） | `CONTEXT_SYSTEM_PROMPT_ENABLED`（**False**）+ `CONTEXT_SYSTEM_PROMPT` | 护栏 `test_system_segment.py`（**5 例**）；探针 `system_injected=true`、system 段 83 token 且位于首位 |
| 3 | §3.2 检索侧重排与阈值接线 | 新增 `_rag_search_params()` 统一「条目参数优先 → 全局配置」；主通道两处 `_rag_handler` 与**内置 RAG 备通道同口径**透传/过滤 | `RAG_RERANK_ENABLED`（**False**）/ `RAG_SCORE_THRESHOLD`（**0**） | 护栏 `test_rag_rerank_wiring.py`（**5 例**）；探针 `{"rerank": true, "score_threshold": 0.15}` |
| 4 | §4.2 路由候选明细落 trace | `ComponentRouter.candidate_report()`（只读，不改决策契约）→ `AutoOrchestrator.decide()` 的 `plan["candidates"]` → 同步/流式两条路径写 `routing_trace.decision_candidates` | 无（纯观测） | 护栏 `test_router_candidate_trace.py`（**6 例**）；探针候选 R001 0.95 / R002 0.95 / R004 0.88（`qualified=true`） |
| 5 | §3.2/§3.3 内容去重 | 含于预算层（段内内容 hash 归一后去重，重复项计入 `dropped_items`，可单独关闭） | 随 `CONTEXT_BUDGET_ENABLED` + `CONTEXT_DEDUP_ENABLED`（True） | 同上护栏 2 例（去重生效 / 可关闭） |

### 4E.2 回归与门禁

| 项 | 结果 |
|----|------|
| 全量回归（OpenLLM `python -m pytest tests/unit -q -p no:cacheprovider`） | **32 failed / 2991 passed / 0 error**（237.59 s） |
| **基线对照**（同命令、同 12 个失败文件；`git checkout HEAD~1` 仅回退本批 6 个生产文件） | **HEAD 28 failed = BASE 28 failed**，归一化 `request_id` 后 `Compare-Object` **逐项零差异** ⇒ **零新增失败**；新增 4 个护栏文件不在失败集内 |
| 新增护栏 | 4 文件 **29 例** 全绿（13 + 5 + 5 + 6） |
| 静态质量 | 改动文件 `ruff` **零新增告警**（`component_router.py` 余 39 项＝HEAD 基线同值，属既有 `UP006/UP045/UP035` 历史欠账，**未借机重构**） |
| 实际运行验证 | **L1** 导入 OK + 11 项开关默认值实测；**L3-lite 探针**（`doc/test/evidence/cr149/context_budget_probe.py`）两档输出（配额与裁剪、system 注入、重排参数、路由候选） |
| 过程修正（如实登记） | ① `_rag_search_params()` 求值由 `try` 内**移出**（避免解析异常被误判为「外部检索失败」触发回退）；② `test_rag_unregistered_no_fallback` 替身按**真实适配器契约**补齐 `rerank`/`score_threshold`（契约漂移修正，非放宽断言） |
| 提交 | OpenLLM `65899c7`（6 生产 + 4 测试，`+454/-22`）、`892e8e7`（2 文件，`+20/-4`），均显式路径、TDD 合规 |

### 4E.3 与既有登记项的关系

| 项 | 变化 |
|----|------|
| 方案 §10 待登记项 4（装配层无预算与裁剪、`system` 段恒空） | **状态更新为「已实施（开关默认关闭）」**；生产开启属**配置发布动作**（须人工批准 + 按方案 §7 T1~T7 验证），不另立登记项 |
| 方案 §6 第一批第 6 项（两条路径取数顺序统一与画像并行） | **仍未实施**，留作下一轮（风险点：流式 `P-4` 首包计量口径）→ **已于 `v1.38.0` 实施（见 §4F）** |
| `CR-148-032` / `TD-新增-028`（生成式精炼缺达标模型与推理节点） | **不受本批影响**（本批不含任何模型档能力，只做规则档与判别式接线） |
| 全仓未闭环项 | **仍为 0 项**（本批无新增缺陷登记；`test_v213_gateway_ext.py` 2~4 项波动为既有 flaky，隔离复跑通过） |

---

## 4F. 上下文精装配第一批第 6 项实施登记（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.3.0** §3.1 / §6 第一批第 6 项（设计项见 v1.0.0 §3.1 取数层）；实现落于 OpenLLM 仓（其《DevLogReport》**v1.20.0** 第 31 批，提交 `2f296bb`）。
> **性质**：**设计项实施登记（非缺陷）** —— 把 §4E.3 中「方案 §6 第一批第 6 项**仍未实施**」转为「**已实施**」，并留可复核证据。**本批不新增缺陷、不新增债务。**

### 4F.1 实施清单与证据

| # | 方案条目 | 实现 | 开关 | 证据 |
|:-:|----------|------|------|------|
| 1 | §3.1 画像 × 组件**并行取数** | 新增并发取数句柄 `DeferredFetch`（`app/edgerouter/orchestration/deferred_fetch.py`）：**构造即启动**后台取数、**组装之前**统一收割；`resolve()` 幂等、取数异常降级为 `None`、`discard()` 供断连 / 早期返回取消 | 无（时序收敛，语义等价） | 护栏 `tests/unit/test_deferred_fetch.py`（**14 例**）；探针 `profile_parallel_probe.py`：分段各 0.15 s 时 **串行 0.312 s → 并发 0.156 s**（省 0.156 s；3 轮取最优、含预热） |
| 2 | §3.1 两条路径取数**时序统一** | 同步「先 `await` 画像后组件」→「构造句柄 → 交编排层 → 组装前收割」；流式「先组件后画像」→「**首包之后**构造（P-4 口径不破）→ 组装之前 `resolve()`」 | 无 | 护栏 `test_profile_fetch_timeline_guard.py`（**4 例**：句柄 2 处 / 步骤名 2 处 / 各自计时 2 处 / 「首包后启动 + 组装前收割」时序）；探针 `gateway_order` 4 项判定全 `true` |
| 3 | 计量口径**不丢**（对齐 `DT-148-018`） | 步骤改由**取数完成回调**落 `{step, ms}`（耗时＝启动→完成差值）；**未显式收割**（异常路径 / 早期返回）也落计量；未启动（画像注入开关关闭）仍沿用「值 `None` + 步骤恒落」 | 无 | 行为护栏（计量不丢 / 幂等 / 失败降级 / 丢弃不落步骤）；探针并发态 `profile_fetch = 156 ms` 且画像确入 Prompt（`prompt_has_profile=true`） |
| 4 | 接口**兼容** | `profile_ctx` 入参放宽为 `str \| DeferredFetch \| None`（`_run_orchestrated_chat` / `AutoOrchestrator` / `ExplicitOrchestrator` / `PipelineExecutor`）：既有字符串调用方与测试替身零影响 | 无 | 护栏 `test_executor_still_accepts_plain_profile_ctx` + **网关→编排层→执行器端到端**判据（画像经句柄进入 Prompt 且落步骤） |

### 4F.2 回归与门禁

| 项 | 结果 |
|----|------|
| 全量回归（OpenLLM `python -m pytest tests/unit -q`） | **32 failed / 3005 passed / 0 error**（227.84 s；该测量轮次护栏含 `test_deferred_fetch` **13 例** + 改写护栏 4 例，同批随后补入的端到端护栏 1 例单独验证通过 ⇒ **批末态 32 failed / 3006 passed**；对照 §4E 基线 2991 passed） |
| **基线对照**（同命令 vs 第一批基线 `cr149-full-after-fix.txt`，逐项 testid 归一化后 `Compare-Object`） | **32 = 32，零差异 ⇒ 零新增失败** |
| 新增 / 改写护栏 | 新增 1 文件 **14 例**；把 `test_profile_fetch_timeline_guard.py` 改写为**句柄写法契约**并**新增时序契约**（**4 例**）——原「两路径都落计量 ＋ 各自计时 ＋ 耗时差值口径」三项不变量**全部保留且更严** |
| 静态质量 | 本轮 7 文件 `ruff` **零告警** |
| 风险如实登记 | ① 并发后 `timeline` 步骤**之和 ≥ 真实墙钟**（区间重叠 → `P-1`「本仓开销」判定需按关键路径复核）；② 异常路径句柄未被显式收割（由**完成回调**兜底计量 + `discard()` 清理）。两项已入方案 §8 风险与回退 |
| 提交 | OpenLLM `2f296bb`（5 生产 + 2 测试，`+550/-30`），显式路径 `git add`、TDD 合规 |

### 4F.3 与既有登记项的关系

| 项 | 变化 |
|----|------|
| 方案 §6 第一批第 6 项（两条路径取数顺序统一与画像并行） | **由「仍未实施」更新为「已实施」**（§4E.3 对应行就此闭环）→ 方案 §6 **第一批 6/6 完成** |
| 方案 §10 待登记项 4（装配层无预算与裁剪 / `system` 段恒空 / 两路径取数时序相反且串行） | 状态更新为「已实施（第一批 6/6；前 5 项开关默认关闭，第 6 项为时序收敛）」；**生产开关开启值仍待人工批准 + 按方案 §7 判据 T1~T7 验证**，本记录不代行批准 |
| `CR-148-032` / `TD-新增-028`（生成式精炼缺达标模型与推理节点） | **不受本批影响**（本批不含任何模型档能力） |
| 方案 §10 待登记项 1~3、§9 待裁定问题 1~5 | **仍未登记**（待批量登记，见 §4D.2） |
| 全仓未闭环项 | **仍为 0 项**（本批无新增缺陷登记；既有失败集 32 项与 flaky 集不变） |

---

## 4G. 上下文精装配第二批第 ① 项实施登记（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.4.0** §4.3 / §6 第二批 / §7 判据 **T5**（对应 §10 待登记项 3）；实现在 OpenLLM 仓（其《DevLogReport》**v1.21.0** 第 32 批，提交 `c60ce2b`）。
> **性质**：**设计项实施登记（非缺陷修复）** —— 把 §10 待登记项 3「写侧价值/重要度/频控/去重决策器未接线」转为「**已实施（开关默认关闭）**」，并留可复核证据。**本批不新增缺陷、不新增债务。**

### 4G.1 实施清单与证据

| # | 方案条目 | 实现 | 开关（默认） | 证据 |
|:-:|----------|------|--------------|------|
| 1 | §4.3 接回写决策器 | 新增 `evaluate.grade_writeback_targets()`（**纯函数、确定性**）供网关三路回写回调**按路**消费：价值闸门（窗口非空 / 最近轮 query 与 response 均非空 / response ≥2 字 / `save_if_valuable=false` 显式拦截） | `WRITEBACK_DECISION_ENABLED`（**False**） | 护栏 `tests/unit/test_writeback_decision_gate.py`（**13 例**）；探针 4 类轮次 × 开关两态 |
| 2 | §4.3 rag 分级入库 | `evaluate.grade_rag_ingest()`：明确记忆意图（重要度 ≥0.8）**或**响应长度 ≥ `WRITEBACK_RAG_FULL_MIN_CHARS` ⇒ `full`（全文入库）；其余 ⇒ `skip` | 同上 ＋ `WRITEBACK_RAG_FULL_MIN_CHARS`（**120**） | 探针：普通轮 `submitted=[memory, profile]`、`rag=skipped`；高价值轮与长响应轮 `rag` 全文入库且**载荷未被改写** |
| 3 | 判据 **T5** 可判定 | 被拦截回调返回 **`"skipped"`**（**不与 `False`（幂等命中）混用**）→ 编排层回执 `{"status":"skipped","reason":"value_gate"}`、流式回执 `skipped` | 无（回执口径扩展） | 护栏 `test_skipped_sentinel_maps_to_skipped_status`；探针低价值轮 `returns` 三路均 `skipped` 且 **`submitted=[]`** |
| 4 | **不代行决定 §9 问题 4** | 闸门**只决定「是否沉淀」**，**不改写载荷**（memory 仍为整轮全文）；`evaluate_session()` 的**载荷形态**（窗口摘要 / 频控预检 / 画像增量）**未接线** | 无 | 护栏 `test_memory_payload_is_not_rewritten` |

### 4G.2 回归与门禁

| 项 | 结果 |
|----|------|
| 全量回归（OpenLLM `python -m pytest tests/unit -q`） | **32 failed / 3019 passed / 0 error**（239.85 s；收集 3051，较上一轮 +14 ＝ `test_deferred_fetch` 补入 1 例 ＋ 本批 13 例） |
| **基线对照**（同命令 vs 上一轮 `cr149-b2-full.txt`，逐项 testid 归一化后 `Compare-Object`） | **32 = 32，零差异 ⇒ 零新增失败** |
| 新增护栏 | `tests/unit/test_writeback_decision_gate.py` **13 例** 全绿 |
| 静态质量 | 本轮 5 文件 `ruff` **零告警** |
| 运行态探针 | `doc/test/evidence/cr149/writeback_gate_probe.py`（真实网关回调 + 真实决策器 + 队列替身）：**关闭态**四类轮次（含空响应）均三路入队；**开启态**低价值**零入队**、普通轮仅 memory/profile、高价值与长响应 `rag` **全文** |
| 提交 | OpenLLM `c60ce2b`（4 生产 + 1 测试，`+363/-2`），显式路径 `git add`、TDD 合规 |

### 4G.3 与既有登记项的关系

| 项 | 变化 |
|----|------|
| 方案 §10 待登记项 3（写侧决策器未接线） | **状态更新为「已实施（开关默认关闭）」**；生产开启值（`WRITEBACK_DECISION_ENABLED` / `WRITEBACK_RAG_FULL_MIN_CHARS`）须**人工批准**后按方案 §7 判据 **T5** 验证再开，**本记录不代行批准** |
| 方案 §9 待裁定问题 4（记忆写入语义：整轮全文 → 提炼结论/摘要） | **仍未裁定，且已成为**「回写决策器**载荷形态**接线」的**前置阻塞项**（本批以「只判定、不改载荷」规避，未代行决定） |
| 方案 §9 待裁定问题 1（通道 A 三选一） | 仍待**人工裁定** —— 阻塞 §4.1「通道定性」实施（内置 RAG 底座 / health 组件探测为「无论选哪条路线都必做」项，可先行） |
| `CR-148-032` / `TD-新增-028`（生成式精炼缺达标模型与推理节点） | **不受影响**（本批不含任何模型档能力） |
| 全仓未闭环项 | **仍为 0 项**（本批为设计项实施登记，无新增缺陷；既有失败集 32 项与 flaky 集不变） |

---

## 4H. 上下文精装配第二批第 ② 项实施登记（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.5.0** §3.1 / §4.2「顺序优化」/ §7 判据 **T8**；实现在 OpenLLM 仓（其《DevLogReport》**v1.22.0** 第 33 批，提交 `ec3485a`）。
> **性质**：**设计项实施登记（非缺陷修复）** —— 把方案 §3.1「组件串并行仍受全局开关控制、依赖图判定未接入」转为「**已实施（开关默认关闭）**」。**本批不新增缺陷、不新增债务。**

### 4H.1 实施清单与证据

| # | 方案条目 | 实现 | 开关（默认） | 证据 |
|:-:|----------|------|--------------|------|
| 1 | §3.1 调度依据改依赖图 | 新增 `app/edgerouter/orchestration/component_graph.py`：`parse_dependencies()`（`child:parent`，空白容忍，非法片段跳过并告警）、`dependency_levels()`（Kahn 式波次划分；未参与本次执行的依赖视为已满足）、`resolve_schedule()` | `COMPONENT_DEPENDENCY_SCHEDULING_ENABLED`（**False**） | 护栏 `tests/unit/test_component_dependency_scheduling.py`（**12 例**，图形层 5 例） |
| 2 | §4.2「无依赖即并行」 | `component_pipeline.resolve_schedule_plan()` → `(波次, 同波次可否并发)`；`run_components` 按波次执行（同波次 >1 用 `asyncio.gather`，波次间严格有序），按**条目下标**消费以保持重复组件与原有顺序语义 | 同上 | 探针：开关开启 + `enable_parallel=false` + 无依赖 ⇒ 墙钟 **0.25 s → 0.125 s**（重叠） |
| 3 | §4.2「严格顺序用依赖声明表达」 | `OPENLLM_COMPONENT_DEPENDENCIES`（如 `memory:rag`）；声明**覆盖**全局并行开关 | `OPENLLM_COMPONENT_DEPENDENCIES`（**""**） | 探针：声明后波次 `[["rag"],["memory"]]`、事件严格 `rag→memory`、**不重叠**（0.235~0.25 s） |
| 4 | **fail-safe**（成环 / 非法声明） | 成环 ⇒ 退化为单波次保序并**告警**（不抛异常、不打挂请求）；非法声明片段跳过并告警 | 无 | 护栏：`test_cycle_degrades_to_single_ordered_level`、`test_parse_declarations`；探针 `cycle_is_failsafe=[["memory","rag"]]` |
| 5 | **关闭时逐字一致** | 关闭时计划恒为「单波次」，并发与否仍由 `enable_parallel` 决定 | 无 | 护栏 3 例（默认值 / 串行不变 / 全局开关并行仍生效）；**既有 `test_component_pipeline_shared.py` 13 例全绿** |

### 4H.2 回归与门禁

| 项 | 结果 |
|----|------|
| 全量回归（OpenLLM `python -m pytest tests/unit -q`） | **32 failed / 3031 passed / 0 error**（239.55 s；收集 3063，较上一轮 +12 ＝ 本批护栏） |
| **基线对照**（同命令 vs 上一轮 `cr149-b2b-full.txt`，逐项 testid 归一化后 `Compare-Object`） | **32 = 32，零差异 ⇒ 零新增失败** |
| 新增护栏 | `tests/unit/test_component_dependency_scheduling.py` **12 例** 全绿；既有共用步骤护栏 13 例未变 |
| 静态质量 | 本轮 4 文件 `ruff` **零告警**（过程修正：惰性导入块 isort 排序、文件末尾换行） |
| 运行态探针 | `doc/test/evidence/cr149/component_schedule_probe.py`（真实共用组件步骤 + 真实调度器，组件各 0.12 s、含预热）：关闭态串行 0.25 s / 全局开关并行 0.125 s；开启态无依赖 0.125 s 重叠；开启态声明 `memory:rag` 严格 `rag→memory` 不重叠 |
| 提交 | OpenLLM `ec3485a`（3 生产 + 1 测试，`+432/-6`），显式路径 `git add`、TDD 合规 |

### 4H.3 与既有登记项的关系

| 项 | 变化 |
|----|------|
| 方案 §3.1「组件串并行仍受全局开关控制、依赖图判定未接入」 | **状态更新为「已实施（开关默认关闭）」**；生产开启值（`COMPONENT_DEPENDENCY_SCHEDULING_ENABLED` / `OPENLLM_COMPONENT_DEPENDENCIES`）须**人工批准**后按方案 §7 判据 **T8** 验证再开，**本记录不代行批准** |
| 方案 §4.2 余项（阈值与单次命中语义对齐 / LLM 兜底分类器接线 / 规则集可配置） | **仍未实施**（本批只做「顺序优化」一行） |
| 方案 §4.1（通道定性 / 内置 RAG 底座 / health 组件探测）与 §4.3 余项（队列指标与死信等） | **仍未实施**；其中「通道定性」需**人工裁定**（§9 问题 1），而「内置 RAG 底座 / health 组件探测」为方案明示的「无论选哪条路线都必做」项，可先行 |
| 方案 §9 待裁定问题 4（记忆写入语义） | 仍为**前置阻塞项**（阻塞回写决策器**载荷形态**接线），本批不涉及 |
| `CR-148-032` / `TD-新增-028`（生成式精炼缺达标模型与推理节点） | **不受影响**（本批不含模型档能力） |
| 全仓未闭环项 | **仍为 0 项**（本批为设计项实施登记，无新增缺陷；既有失败集 32 项与 flaky 集不变） |

---

## 4I. 上下文精装配第二批第 ③ 项实施登记（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.6.0** §4.1「配套两项必做」之一（备通道健康探针）/ §7 判据 **T4** 前置条件；实现在 OpenLLM 仓（其《DevLogReport》**v1.23.0** 第 34 批，提交 `03a624f`）。
> **性质**：**设计项实施登记（非缺陷修复）** —— 把方案 §4.1 明示的「无论选哪条通道路线都必做」项之一落地，使「备通道存在但无内容」这一**静默劣化**前置可视化。**本批不新增缺陷、不新增债务。**

### 4I.1 实施清单与证据

| # | 方案条目 | 实现 | 开关 | 证据 |
|:-:|----------|------|------|------|
| 1 | §4.1 备通道健康探针 | `_probe_components(db)` 一次 `asyncio.gather` 并行探测 **5 项**：外部三组件 ＋ `builtin_rag` ＋ `ollama`（共用既有结果缓存） | 无（纯观测） | 护栏 `tests/unit/test_health_backup_channel_probe.py`（**10 例**）；探针实测 `components_keys = [builtin_rag, dps, ollama, openmemory, openrag]` |
| 2 | 内置 RAG 底座事实 | 新增 `_count_faiss_indexes(root)`（`<root>/<kb-id>/index.faiss`，与 `VectorStoreService` 落盘约定同一事实源）＋ `_probe_builtin_rag(db)`（`knowledge_bases` / `indexes` / `has_base` / `reason`） | 无 | 探针：`faiss_root_exists=true`、`indexes=0`、`has_base=false`，`reason="内置 RAG 无底座（KB 0 行 / FAISS 0 索引）⇒ 备通道接管后将注入为空"` |
| 3 | Ollama 可达性 | `_ollama_probe_tags()`（`GET {OLLAMA_HOST}/api/tags`，2 s 独立超时、URL 取自配置不硬编码）＋ `_probe_ollama()`（`ok` 含 `models` 数 / `unavailable` 含 `reason`） | 无 | 探针：`ollama = {status: ok, latency_ms: 15, models: 2}`；护栏含可达 / 不可达 / URL 源三例 |
| 4 | **探测不抛异常** | DB 异常 / FAISS 根缺失 / HTTP 失败一律降级为 `unavailable` ＋ `reason` | 无 | 护栏：DB 失败降级、FAISS 根缺失、Ollama 不可达三例；health 在依赖故障下仍 200 |
| 5 | 同一事实源（供人工与自动共用） | `/health` 端点增 `db` 依赖（统计 KB 行数）；原三键**原样保留**（增量字段，向后兼容） | 无 | 护栏 `test_health_endpoint_passes_db_into_probe`、`test_probe_components_includes_backup_channel_facts` |

### 4I.2 回归与门禁

| 项 | 结果 |
|----|------|
| 全量回归（OpenLLM `python -m pytest tests/unit -q`） | **31 failed / 3042 passed / 0 error**（238.83 s；收集 3073，较上一轮 +10 ＝ 本批护栏） |
| **基线对照**（同命令 vs 上一轮 `cr149-b2c-full.txt`，逐项 testid 归一化后 `Compare-Object`） | **无新增失败项**（失败集为基线**子集**：32 → 31）；唯一差异 `test_v213_gateway_ext.py::test_memory_writeback_adapter_missing_raises`（既有 flaky）本轮**转绿**，如实登记为**基线波动** |
| 新增护栏 | `tests/unit/test_health_backup_channel_probe.py` **10 例** 全绿 |
| 静态质量 | 本轮 2 文件 `ruff` **零告警**（过程修正：gateway 增补缺失的 `import os`） |
| 运行态探针 | `doc/test/evidence/cr149/health_backup_probe.py`（调真实探测函数）：备通道 ``has_base=false`` 且 reason 显式；`ollama` 可达 2 个模型；`components` 五键同一事实源 |
| 提交 | OpenLLM `03a624f`（1 生产 + 1 测试，`+327/-9`），显式路径 `git add`、TDD 合规 |

### 4I.3 与既有登记项的关系

| 项 | 变化 |
|----|------|
| 方案 §10 待登记项 2（内置 RAG 备通道无底座） | **状态更新为「部分实施」**：事实已**前置可视化**（`has_base` / `reason`）；**种子动作未执行**（需运行态 DB ＋ 嵌入模型），当前口径明确为「内置 RAG 仅在有本地索引时生效」 |
| 方案 §4.1「备通道健康探针」 | **已实施**（本批）；「内置 RAG 补底座」**部分实施**（可视化完成、种子待运行态） |
| 方案 §9 待裁定问题 1（通道 A 三选一） | 仍待**人工裁定** —— 阻塞 §4.1「通道定性」与 health 的 `components.*.channel` 字段 |
| 方案 §7 判据 T4 | **前置条件自本批起可判定**（`has_base=false` ⇒ 接管必然「注入为空」，须先补底座或声明口径） |
| 方案 §4.3 余项（队列指标与死信 / 画像增量升级 / 写路径与通道一致） | **仍未实施** |
| `CR-148-032` / `TD-新增-028`（生成式精炼缺达标模型与推理节点） | **不受影响**（本批不含模型档能力） |
| 全仓未闭环项 | **仍为 0 项**（本批为设计项实施登记，无新增缺陷；失败集为基线子集） |

---

## 4J. 上下文精装配第二批第 ④ 项实施登记（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.7.0** §4.3「队列可观测与死信」；实现在 OpenLLM 仓（其《DevLogReport》**v1.24.0** 第 35 批，提交 `1a572f7`）。
> **性质**：**设计项实施登记（非缺陷修复）** —— 把回写链路的**失败可观测性**与**可恢复性**从「直连 SQLite 手工排查/重放」升级为「接口化视图 + 受控重放 + 定时清理」。**本批不新增缺陷、不新增债务。**

### 4J.1 实施清单与证据

| # | 方案条目 | 实现 | 开关 | 证据 |
|:-:|----------|------|------|------|
| 1 | 暴露**队列深度 / 失败率 / 重试分布** | `WritebackStore.stats(user_id=None)`：三条聚合 SQL 产出 `total` / `by_status` / `failure_rate`（空库 `0.0`，不除零）/ `retried_rows` / `retry_distribution` / `max_retry_count` / `oldest_open_at`；`WritebackQueue.stats()` 补 `queue_depth` | 无（纯观测） | 护栏 `tests/unit/test_writeback_queue_observability.py`（**22 例**，聚合 4）；探针：`failure_rate=0.75`、`retry_distribution={"2":1,"3":2}`、`max_retry_count=3` |
| 2 | `failed` 行进入**死信视图** | `list_dead_letters(user_id, limit, offset)`：只含 `failed`、分页（`total` 不受分页影响）、**不返回 `payload_json`** | 无 | 护栏 3 例；探针 `total=3` 且 `has_payload_field=false` |
| 3 | 提供**重放端点** | `POST /openllm/v1/writeback/dead-letter/replay`（`claim_failed` 原子置回 `pending` 并把 `retry_count` 归零 → `replay_dead_letters` 复用 `_run_item` 重新投递）；**仅显式行 id、单次 ≤100**（超限 4003）；未注册 handler 计 `skipped` 且行留在 `pending` | 无 | 护栏 3+3+2 例；探针 `replayed=2`、handler 实投递 2 次、状态转 `done`；越权取件 `[]` 且对方行仍 `failed` |
| 4 | **失败 TTL 清理任务化** | `WritebackQueue.run_cleanup_loop(interval)`（单轮异常不终止循环、`interval≤0` 立即返回）+ `main.py` lifespan 启动/关闭取消；间隔 `WRITEBACK_CLEANUP_INTERVAL_SECONDS`（默认 3600 s，**0=关闭**） | 见左 | 护栏 4 例（默认值 / 0 关闭 / 单轮失败仍续跑 / lifespan 接线与取消源码契约）；探针 TTL 对新近死信不误删 |
| 5 | **归属隔离（fail-closed）** | 统计 / 死信视图 / 重放三处均沿用 `DEF-BE-148-007` 的 `json_extract` 归属过滤；无身份一律 **401（1001）**；无归属的历史行不可见 | 无 | 护栏：`stats` / `dead-letter` 无身份 401 各 1 例、用户作用域统计与取件各 1 例 |

### 4J.2 回归与门禁

| 项 | 结果 |
|----|------|
| 全量回归（OpenLLM `python -m pytest tests/unit -q`） | **32 failed / 3063 passed / 0 error**（244.44 s；收集 3095，较上一轮 +22 ＝ 本批护栏） |
| **基线对照**（同命令 vs 第 33 批基线 `cr149-b2c-full.txt`，逐项 testid 归一化后 `Compare-Object`） | **32 = 32，零差异 ⇒ 零新增失败** |
| **对照实验（决定性证据，针对波动项）** | 上一轮（第 34 批）`test_v213_gateway_ext.py` 曾少失败 1 例；本批以 `git stash push -- <本批 4 个生产文件>` **回退改动后隔离复跑该文件，得到与改动后完全相同的 4 个失败** ⇒ 判定为**既有序相关 flaky**（`Event loop is closed` 一族 + bypass 500），**与本批改动无关** |
| 新增护栏 | `tests/unit/test_writeback_queue_observability.py` **22 例** 全绿（聚合 4 / 死信视图 3 / 取件 3 / 队列重放 3 / 接口层 5 / TTL 任务化 4）；既有回写护栏（receipts / queue / recovery / three-roads）35 例未变 |
| 静态质量 | 本轮 5 文件 `ruff` **零告警**（过程修正：`import asyncio`（main.py）、`Sequence`（writeback_queue.py）、`_sql_where` 助手） |
| 运行态探针 | `doc/test/evidence/cr149/writeback_observability_probe.py`（真实存储层 + 队列层 + 独立临时 SQLite）：全局与按用户两口径统计、死信视图无正文、重放闭环（`done`）、越权取件不生效、TTL 任务化可关可跑 |
| 提交 | OpenLLM `1a572f7`（4 生产 + 1 测试，`+782/-2`），显式路径 `git add`、TDD 合规 |

### 4J.3 与既有登记项的关系

| 项 | 变化 |
|----|------|
| 方案 §4.3「队列可观测与死信」 | **状态更新为「已实施」**（本批） |
| 方案 §4.3 余项（画像增量升级 / 写路径与通道一致） | **仍未实施**（后者依赖 §9 问题 1 的通道定性与 `assert_write_channel_is_primary` 接入） |
| 方案 §9 待裁定问题 1（通道 A 三选一） | 仍待**人工裁定** —— 阻塞通道定性与「写路径与通道一致」 |
| 方案 §9 待裁定问题 4（记忆写入语义） | 仍为回写决策器**载荷形态**接线的前置阻塞项 |
| 全局口径统计（运维视图） | **未开放**（现为调用方作用域）；如需全局视图建议按**角色门禁**单独开放，避免以聚合推断他人回写规模 |
| `CR-148-032` / `TD-新增-028`（生成式精炼缺达标模型与推理节点） | **不受影响**（本批不含模型档能力） |
| 全仓未闭环项 | **仍为 0 项**（本批为设计项实施登记，无新增缺陷） |

---

## 4K. 上下文精装配第二批第 ⑤ 项实施登记（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.8.0** §4.2「组件决策」三余项 / §7 判据 **T9**；实现在 OpenLLM 仓（其《DevLogReport》**v1.25.0** 第 36 批，提交 `0abcaea`）。
> **性质**：**设计项实施登记（含 1 项语义更正）** —— ① 阈值与单次命中语义对齐属**内部一致性更正**（方案明确指出的「隐性分叉」）；② 规则集可配置与 ③ LLM 兜底接线属**既有能力接线**。**本批不新增缺陷、不新增债务。**

### 4K.1 实施清单与证据

| # | 方案条目 | 实现 | 开关（默认） | 证据 |
|:-:|----------|------|--------------|------|
| 1 | 阈值与**单次命中语义对齐** | `R001`/`R002` 单次命中 0.8 → **0.86**（≥ 阈值 0.85）；`R005` 复合意图 0.8 → **0.86**（此前**永不达标**）；低配时**告警**不强制改写 | `COMPONENT_ROUTER_SINGLE_HIT_CONFIDENCE`（**0.86**）/ `COMPONENT_ROUTER_COMPOSITE_CONFIDENCE`（**0.86**）；配回 0.8 = 旧语义 | 护栏 `test_component_router_decision_tuning.py`（**15 例**）；探针：单次命中「不决策 → 直接决策」、`R005.qualified` `false → true` |
| 2 | **规则集可配置** | `COMPONENT_ROUTER_RULES_PATH` 接入 `ComponentRouter` 构造；**路径非法/文件损坏告警并退回内置规则** | `COMPONENT_ROUTER_RULES_PATH`（**""**=内置） | 护栏 3 例；探针：自定义 `X001` 生效、非法路径退回内置 5 条规则 |
| 3 | **LLM 兜底接线** | 新增 `_build_component_router()`（`_auto_component_plan` 统一调用）：开关注入分类器，复用 `_call_llm`（`temperature=0`、`max_tokens=64`）＋ **300ms** 超时；超时/异常/非法 JSON **一律回落规则** | `COMPONENT_ROUTER_LLM_FALLBACK_ENABLED`（**False**）/ `COMPONENT_ROUTER_LLM_TIMEOUT_SECONDS`（**0.3**）/ `COMPONENT_ROUTER_LLM_MODEL`（""=自动路由） | 护栏 4 例；探针：关=不注入、开=注入、超时=回落规则 |
| 4 | 语义更正的**可复现逃生阀** | 置信度由配置驱动，**配回 0.8 即复现旧「回落最优候选」语义**（供压测/A-B） | 见 1 | 护栏 `test_legacy_confidence_is_configurable`；3 个既有护栏按新契约更正时即用该逃生阀复现旧场景 |

### 4K.2 回归与门禁

| 项 | 结果 |
|----|------|
| 全量回归（OpenLLM `python -m pytest tests/unit -q`） | **31 failed / 3079 passed / 0 error**（244.08 s；收集 3110，较上一轮 +15 ＝ 本批新增护栏） |
| **基线对照**（同命令 vs 上一轮 `cr149-b2e-full.txt`，逐项 testid 归一化后 `Compare-Object`） | **无新增失败项**（失败集为基线**子集** 32 → 31）；差异项仍为已用**对照实验**证实的既有序相关 flaky（`test_v213_gateway_ext.py::test_memory_writeback_adapter_missing_raises`），如实登记为**基线波动而非本批收益** |
| 新增/更正护栏 | 新增 `tests/unit/test_component_router_decision_tuning.py` **15 例**；**3 个既有护栏按新契约更正**（各自原断言编码的正是方案指出的「隐性分叉」，现改用逃生阀复现旧场景**并同时锁定新默认** —— **契约更正，非放宽断言**） |
| 静态质量 | 本轮 7 文件 `ruff` **零新增告警**（`component_router.py` **39 = 39**、其余 **2 = 2**；过程修正：新增的两个 `Optional[float]` 形参改为 `float | None`） |
| 运行态探针 | `doc/test/evidence/cr149/component_decision_probe.py`（真实路由器 + 网关构造入口）：阈值对齐对比、规则集配置与非法路径降级、LLM 兜底三态 |
| 提交 | OpenLLM `0abcaea`（3 生产 + 4 测试，`+417/-16`），显式路径 `git add`、TDD 合规 |

### 4K.3 与既有登记项的关系

| 项 | 变化 |
|----|------|
| 方案 §4.2「阈值与单次命中语义对齐 / 规则集可配置 / LLM 兜底接线」 | **状态更新为「已实施」**（本批） |
| **语义变更提示（需人工知悉）** | 单次命中置信度提升后**路由决策面变宽**：同一查询可能由「LLM 兜底结论」变为「规则直接结论」，组件装配面随之变化 —— 已入方案 §8 风险表；**生产如需保持旧行为，把两个置信度键配回 0.8** |
| 方案 §9 待裁定问题 1（通道 A 三选一） | 仍待**人工裁定** —— 阻塞通道定性、通道裁决进取数层、§4.3「写路径与通道一致」 |
| 方案 §9 待裁定问题 4（记忆写入语义） | 仍为回写决策器**载荷形态**接线的前置阻塞项 |
| LLM 兜底分类器**上线前提** | 开关默认关闭；开启前须按方案 §5.6 门槛复测出达标分类器（§5.4/§5.5 实测 ≤1B 本地模型在 300ms 内不达标） |
| `CR-148-032` / `TD-新增-028`（生成式精炼缺达标模型与推理节点） | **不受影响**（本批不含模型档能力，仅接线） |
| 全仓未闭环项 | **仍为 0 项**（本批为设计项实施登记与内部一致性更正，无新增缺陷） |

---

## 4L. 缺陷登记与修复：`DEF-BE-148-029` 画像增量提炼服务缺失（2026-09-27）

> **来源**：上下文精装配第二批实施过程中的**仓内一致性审计**（`evaluate.py` 导入契约 vs 仓内实际模块）；修复落于 OpenLLM 仓（其《DevLogReport》**v1.26.0** 第 37 批，提交 `5589ddf`）。
> **性质**：**产品功能缺陷（潜在，未触发即已发现）** —— 已提交代码引用了**仓内不存在**的模块，一旦对应入口被接线即 `ModuleNotFoundError`。**本批修复该缺陷；不新增债务。**

### 4L.1 缺陷与根因

| 项 | 内容 |
|----|------|
| 缺陷 ID | **`DEF-BE-148-029`** |
| 级别 | **P1**（写侧决策链路可用性缺陷；当前因入口未接线而**未触发**，属"埋雷"型） |
| 归属 | OpenLLM 仓 `app/edgerouter/orchestration/evaluate.py`（引用方）＋ `app/services/profile_refine.py`（**模块缺失**） |
| 现象 | `evaluate.py::_profile_updates_for` 惰性导入 `DEFAULT_PROFILE_TARGETS` / `get_active_profile_refiner` / `refine_profile_delta`，但 **`app/services/profile_refine.py` 在仓内不存在**（`Get-ChildItem -Recurse -Filter 'profile_refine*'` **仅命中 `__pycache__/profile_refine.cpython-310.pyc` 字节码**，源码缺失） |
| 触发条件 | 写侧入口 `evaluate_session(db, identity, window, {"enable_profile_delta": true})` 被接线时 → `_profile_updates_for` **ModuleNotFoundError** → 打挂写侧回写决策（该入口目前**全仓无调用点**，故本轮之前未暴露） |
| 根因 | ① 方案 §4.3 所述「配置键 `OPENLLM_PROFILE_LLM_REFINE` 已存在」**与当前树不符**（`config.py` 中**无此键**）—— 交付批次遗留的「文档-实现漂移」；② 与 `evaluate.py` 同批的 `profile_refine` 源码**未随提交落库**（仅字节码残留），而引用方**缺少 fail-safe**，使缺失被静默隐藏 |
| 影响面 | ① 写侧「画像增量」目标**不可用**（一旦接线即崩）；② 方案 §4.3「画像增量升级」缺乏落地基座；③ 回写路 `writeback._resolve_profile_updates` 与决策器 `evaluate` **各自维护同一套提炼规则**（重复实现，存在语义漂移风险） |

### 4L.2 修复内容

| # | 修复 | 说明 |
|:-:|------|------|
| 1 | **补回服务模块** `app/services/profile_refine.py` | 导出 `DEFAULT_PROFILE_TARGETS`（`("business","person")`）、`set/get_active_profile_refiner`（线程安全注册表）、`refine_profile_delta(...)`、`extract_topics`、`infer_tone`、`rule_refine_profile`；**规则提炼语义逐字取自既有线上实现**（`writeback._resolve_profile_updates` / `_extract_topics` / `_infer_tone`），非重新发明 |
| 2 | **单一事实源** | `writeback._resolve_profile_updates` / `_extract_topics` / `_infer_tone` 改为**薄封装委托**新模块（既有公开名保留 ⇒ 既有护栏 `test_v2143_writeback_profile.py` 契约不破）；两处**默认值差异显式化**（回写路「未指定 `extract_targets` ⇒ 不提炼」由薄封装承担；写侧决策默认 `DEFAULT_PROFILE_TARGETS`） |
| 3 | **提炼器注入位点**（新契约，如实标注） | `refine_fn(dialogue: dict) -> dict \| None`（**同步** —— `_profile_updates_for` 为同步函数无法 await）；**未注册 ⇒ 纯规则路径**（线上零影响）；**已注册但抛异常/返回非 dict/返回空 ⇒ 保留规则结果**（规则兜底，绝不丢标签） |
| 4 | **写侧决策 fail-safe** | `evaluate._profile_updates_for` 整体（**含导入**）纳入 `try/except` ⇒ 提炼链路任何异常**降级为空增量并告警**，可选目标绝不打挂写侧决策主流程 |

### 4L.3 验证与证据

| 项 | 结果 |
|----|------|
| 新增护栏 | `tests/unit/test_profile_refine_service.py` **17 例**（模块契约 3 / 规则提炼 6 / 提炼器注入与兜底 4 / 单一事实源 2 / fail-safe 2）；**首轮 RED 的失败信息即缺陷证据**：`ModuleNotFoundError: No module named 'app.services.profile_refine'` |
| 既有护栏 | `test_v2143_writeback_profile.py` **13 例全绿**（委托后语义逐字保持） |
| 运行态探针 | `doc/test/evidence/cr149/profile_refine_probe.py`：三个符号齐备；`evaluate._profile_updates_for` 真实返回增量（`business.topics` + `person.tone=inquisitive`）；提炼器注入生效 → 抛异常**回落规则结果** → 复位回纯规则；**回写路与服务模块在 5 类入参下结果一致**（`no_targets` 差异为**预期契约差异**，探针双列输出） |
| 全量回归 | `32 failed / 3095 passed / 0 error`（251.93 s；收集 3127 ＝ 上一轮 +17） |
| **基线对照** | 失败集与已知 32 项集**相同 ⇒ 零新增失败**；**对照实验（决定性）**：将本批 2 个受跟踪文件 `git stash` ＋ 临时移除新模块后**隔离复跑 `test_v213_gateway_ext.py`，得到完全相同的 4 个失败**（`Event loop is closed` ×2 / `DID NOT RAISE` / `bypass 500`）⇒ 该文件为**既有序相关 flaky**（第 35 批已首次登记），**与本批无关** |
| 静态质量 | 本轮 4 文件 `ruff` **零告警** |
| 提交 | OpenLLM `5589ddf`（3 生产 + 1 测试，`+442/-52`），显式路径 `git add`、TDD 合规（先 RED 后 GREEN） |

### 4L.4 与既有登记项的关系

| 项 | 变化 |
|----|------|
| `DEF-BE-148-029` | **已修复**（本批）；写侧「画像增量」目标**恢复可用**（仅 `options.enable_profile_delta` 开启时产出，默认不产出 ⇒ **线上行为不变**） |
| 方案 §4.3「画像增量升级」（`_resolve_profile_updates` 升级为受门控小模型提炼） | 状态更新为 **「基座已补回（v1.9.0）；线上 LLM 门控待决策」** —— 提炼器**注入位点已就绪**，但**线上接线**需先裁定 **同步/异步提炼器形态**（已写入方案 §9 **问题 7** —— 注意 §9 原已有问题 6「异步精炼触发与产物归属」，编号据此核对），故本批**不代行接线**；方案所述配置键 `OPENLLM_PROFILE_LLM_REFINE` **当前树不存在**，亦以本次登记更正 |
| 方案 §9 待裁定问题 4（记忆写入语义） | **不受影响**（本缺陷仅涉「画像增量」目标，与 memory 载荷形态无关） |
| `CR-148-032` / `TD-新增-028`（生成式精炼缺达标模型与推理节点） | **不受影响** |
| 全仓未闭环项 | **仍为 0 项**（本缺陷已闭环；flaky 集不变） |

---

## 4M. §7 验收判据执行器交付与 T1/T2 结构缺口更正（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.10.0** §7 / §3.3；实现在 OpenLLM 仓（其《DevLogReport》**v1.27.0** 第 38 批，提交 `4389ded`）。
> **性质**：**验证工具交付（非缺陷）＋ 第一批 T1/T2 的实现更正**。执行器**首跑即暴露两处结构性缺口**（T2 `FAIL`、T1 仅有"偶然通过"），故一并更正并登记。**本批不新增债务。**

### 4M.1 交付物与缺口

| # | 项 | 内容 |
|:-:|----|------|
| 1 | **判据执行器**（交付） | `doc/test/evidence/cr149/t_acceptance_runner.py`：T1~T9 **一键复跑**，逐条 `PASS / FAIL / SKIP / BLOCKED` ＋**原始测量数据**（`--json` 落盘）；默认按**当前配置**判定；`--simulate` **进程内**临时置位（退出恢复、不写配置、不影响运行中服务）；`SKIP`/`BLOCKED` **不计入失败**但显式列出（避免"没做"被误读成"通过"）；退出码 `0`=无 FAIL。**使"人工批准开关值 → 一键验收"成为可执行闭环**（此前 T1~T9 只存在于方案表格中，无执行体） |
| 2 | **缺口一（T1，结构冲突）** | §3.3 原本即要求「`query + 模板开销` 留余量」，但第一批把 5 段比例设为 `0.05/0.05/0.30/0.40/0.20`（**和 = 1.00**）⇒ 各段满额时 `prompt_total_tokens = available + 查询 + 开销 > available`，与 T1 判据**结构性冲突**。原夹具条目偏小，留有**偶然空隙**把该冲突掩盖成"通过"（这也说明**判据夹具必须能填满配额**才有判别力） |
| 3 | **缺口二（T2，单条即超配额 ⇒ 整段清空）** | 配额裁剪从尾部整条丢弃：若**单条素材大于该段配额**，循环一路丢到空（实测 history 段 `dropped_items=6 / used=0`）⇒ 配额被白白浪费、该段归因彻底缺失 |

### 4M.2 更正内容

| # | 更正 | 说明 |
|:-:|------|------|
| 1 | **配额余量标定** | 5 段比例标定为 `0.05/0.05/0.28/0.37/0.19`（**和 = 0.94**，恢复 §3.3 的「query + 模板开销余量」本意）；新增常量 `QUOTA_HEADROOM_CEILING = 0.95` 并在配置默认值同步 |
| 2 | **保底一条** | 新增 `_fit_single_unit()` 与「保底一条」：**仅当裁剪将清空该段时**保留首条，先句边界、再按比例收敛，并**连同渲染编号前缀一并计入**（首版漏算前缀实测 `193 > 190`）硬压进配额，记 `truncated_items`；**可装下首条时不触发** ⇒ 既有「整条丢弃」语义不变 |
| 3 | **`quota = 0` 语义显式化** | 写入 `BudgetPolicy.quota` docstring：**"不限"= 不裁剪**（fail-open，避免误配 `..._RATIO=0` 静默清空整段）；判据 T1 的 `used ≤ quota` **仅对 `quota > 0` 的段**成立 |
| 4 | **执行器 T1 夹具强化** | 改用**填满配额**的最坏夹具（单条尺寸按各段配额定制），使结构性溢出**必然**可判 |

### 4M.3 验证与证据

| 项 | 结果 |
|----|------|
| 新增护栏 | `tests/unit/test_context_budget_headroom_and_floor.py` **7 例**（保底触发与守配额（含**无句末标点的超长单条**硬性收敛）/ 可装下时不触发 / `quota=0` 语义锁定 / 内置与配置比例余量 / **满额场景 `prompt_total_tokens ≤ available`**） |
| 既有护栏 | 预算族（`test_context_budget.py` 13 例等，含 `test_system_segment.py` / `test_rag_rerank_wiring.py`）**全绿** ⇒ 整条丢弃语义与其余批次数值未变 |
| 执行器两态实测 | **当前配置** ⇒ `{PASS:3（T3/T7/T9）, SKIP:4（T1/T2/T5/T8）, BLOCKED:2（T4/T6）, FAIL:0}`；`--simulate` ⇒ `{PASS:6, SKIP:1（T8：能力达标但开关未开）, BLOCKED:2, FAIL:0}` —— 报告落 `t_acceptance_runner-result.json` 与 `t_acceptance_runner-simulate-result.json` |
| 全量回归 | `32 failed / 3102 passed / 0 error`（245.06 s；收集 3134 ＝ 上一轮 +7） |
| **基线对照** | 与上一轮失败集**逐项完全相同**（`Compare-Object` **32 = 32，零差异 ⇒ 零新增失败**） |
| 静态质量 | 本轮 3 文件 `ruff` **零告警** |
| 提交 | OpenLLM `4389ded`（2 生产 + 1 测试，`+253/-9`），显式路径、TDD 合规 |

### 4M.4 与既有登记项的关系

| 项 | 变化 |
|----|------|
| 方案 §7 T1~T9 | **由"表格判据"升级为"可执行判据"**（执行器交付）；T1/T2 表述按实现更正为**精确不变量**（`quota>0` 硬上限 / 保底一条 / Σ比例 ≤ 0.95） |
| 方案 §3.3 | 补充**余量约束**、**保底一条**与 **`quota=0` 语义**三节；说明第一批实现与原设计「query 余量」要求的偏差已更正 |
| 第一批实施登记（§4E） | **不改判其"已实施"结论**，但**更正其中 T1/T2 的实现口径**（结构余量 + 保底一条）；其开关仍为默认关闭 ⇒ **线上行为不变** |
| T4 / T6 | 执行器判为 **`BLOCKED`**（T4 前置：内置 RAG 无底座 ⇒ 接管注入为空；T6 属第三批）—— **不计入失败但显式登记**，与 §4I / §6 一致 |
| 开关开启值批准 | **仍未批准**：T1/T2/T5/T8 需人工批准开关值后**复跑执行器**（一条命令即可出结论），本记录不代行批准 |
| 全仓未闭环项 | **仍为 0 项** |

---

## 4N. T4 轨迹两路径口径收敛（方案 §7 T4「轨迹」段进程内化）（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.11.0** §4.1「人工验证口径」/ §7 T4 / §10；实现在 OpenLLM 仓（其《DevLogReport》**v1.28.0** 第 39 批，提交 `b37e0c0`）。
> **性质**：**实施登记（第二批第 ⑥ 项部分完成）＋ 一项新待登记项**。**无新增缺陷**；登记的「审计事件未独立落库」为**能力缺口**（非缺陷），按待登记项处置。**本批不新增债务。**

### 4N.1 动因：T4 复核暴露的真实缺口

| # | 项 | 内容 |
|:-:|----|------|
| 1 | **判据可判定性** | v1.10.0 执行器把 T4 整体判为 `BLOCKED`，依据是「内置 RAG 无底座（`has_base=false`）」。但复核发现 T4 的**「轨迹」部分并不依赖运行态**（轨迹由 handler / 共用组件步骤在进程内产出）⇒ 该段**本可判定却一直未判**，属**判据覆盖不足** |
| 2 | **真实缺口（流式缺归因）** | **流式路径**的接管发生在**共用组件步骤** `component_pipeline.run_components`，该步骤**只落 `rag_source`、不落回退归因**；**同步路径** handler 落 `builtin_fallback_reason` ⇒ **两路径轨迹口径不一致**，流式轨迹缺「为何接管」（**T4 原文要求的「明确轨迹」在流式路径残缺**） |
| 3 | **隐患（字段各自手写）** | 两处字段**各自手写**（同步在 `_run_orchestrated_chat` 内联赋值、流式在 `_run_stream_components` 回传后赋值）⇒ 属**可再次分叉**的形态，与方案 §2「双路径分叉」同类 |

### 4N.2 收敛内容

| # | 收敛 | 说明 |
|:-:|------|------|
| 1 | **共用步骤补落归因** | `ComponentRunResult` 新增 `builtin_fallback_reason`；回退分支写入（`REASON_MAX_CHARS = 120` ＋ `_fallback_reason()` 截断，**避免异常正文无界落痕**）；模块 docstring 同步 |
| 2 | **单一落痕实现** | 网关新增 `_merge_rag_trace(components, *, rag_source, builtin_fallback_reason)`，**同步与流式两路径共用**：同步的轨迹字面量经它构造，流式在**初始化**与**组件执行后**两次调用；删除原手写字段与 `if shared_state.get(...)` 分支 |
| 3 | **回传归因** | `_run_stream_components` 返回值增 `builtin_fallback_reason`（与 `rag_source` 同路回传） |
| 4 | **语义保持** | 未执行检索仍为 `skipped` 且**不落空归因**；`external` 不落归因；**装配缺失 / 超时仍不触发回退**（`DEF-BE-148-012` 语义不变）；回退**不计 `degraded`**（回退成功 ≠ 降级） |
| 5 | **执行器 T4 拆分** | 由「整体待运行态」改为「**轨迹 = 进程内判 ＋ 无 5xx = 进程内（端点级 HTTP）**」：7 项轨迹判定（两路径来源、两路径归因、归因一致、来源一致、未检索时 `skipped` 且无归因），**轨迹不达标即 `FAIL`**；`detail` 增 `trace_contract` / `endpoint_level_evidence` / `runtime_pending` / `historical_e2e_evidence`；**状态仍为 `BLOCKED`**（剩余「**真实**停服/改址注入」与「轨迹**实际落库**读取」两项未验），但 `reason` 明确**轨迹与「无 5xx」均已在进程内覆盖** |

### 4N.3 验证与证据

| 项 | 结果 |
|----|------|
| 新增护栏（TDD） | `tests/unit/test_rag_builtin_fallback_trace.py` **18 例**（首轮 14 例 **RED 11 failed / 3 passed**；同批补充 **端点级（HTTP）4 例**），失败信息即缺口证据 |
| 既有护栏 | RAG 回退族（`test_rag_unregistered_no_fallback.py`）＋ 共用组件步骤族（`test_component_pipeline_shared.py`）＋ 流式一致族（`test_stream_auto_parity.py`）等 **89 例全绿** ⇒ 既有语义未变 |
| **进程内实测（决定性）** | 同一故障（`RuntimeError: OpenRAG 不可达: connection refused`）下两路径轨迹**逐键一致** —— `{rag_source: "builtin", builtin_fallback_reason: "OpenRAG 不可达: connection refused"}`（执行器 `detail.sync_trace_components` / `detail.stream_trace_components`，`trace_contract = PASS`） |
| **端点级（HTTP）故障注入（v1.46.1 补充，决定性）** | `TestEndpointLevelFaultInjection` **4 例**：同步 `POST /openllm/v1/chat` 外部失败 + 开关开 → **200**、`routing_trace.components` 落 `rag_source=builtin` 与归因、**不计降级**；开关关 → **200**、`skipped` 无归因、`degraded` 含 `rag`；**装配缺失**（开关开）→ **200**、`skipped` 且**内置回退零调用**；**流式** `POST /openllm/v1/chat/stream` → **200**、`event: routing`/`event: done` 齐备且**无 `event: error`**、**落库轨迹入参**同样带来源与归因 ⇒ **「无 5xx」段亦已在进程内覆盖**（口径：组件故障注入，非停服；不替代运行态 E2E） |
| 执行器两态实测 | **当前配置** ⇒ `{PASS:3, SKIP:4, BLOCKED:2（T4/T6）, FAIL:0}`；`--simulate` ⇒ `{PASS:6, SKIP:1, BLOCKED:2, FAIL:0}` —— 报告落 `t_acceptance_runner-result.json` 与 `t_acceptance_runner-simulate-result.json` |
| 全量回归 | `31 failed / 3121 passed / 0 error`（249.69 s；v1.46.1 补充 4 例后） |
| **基线对照** | **零新增失败**（逐项 testid 归一化后 `Compare-Object` 无新增项）；差异项仍为既有 flaky `test_v213_gateway_ext.py` 一族（`…writeback_adapter_missing_raises` 两例交替转绿）⇒ **如实登记为基线波动，不记为本批收益** |
| 静态质量 | 本轮 2 文件 `ruff` **零告警**；执行器 5 项既有告警（I001/F401/F841/B905/UP035）一并清理 ⇒ `All checks passed` |
| 提交 | OpenLLM `b37e0c0`（2 生产 + 1 测试，`+387/-29`）、**`13707fc`（补充端点级 4 例，`+133/-1`）**，显式路径、TDD 合规 |

### 4N.4 新增待登记项与关系

| 项 | 变化 |
|----|------|
| **新增待登记项：备通道接管的「审计事件」无独立落库** | T4 原文要求轨迹含「`rag_source`、审计事件」。当前落点为**接管 WARNING 日志** ＋ `routing_trace.components`（`rag_source` / `builtin_fallback_reason`），**未写入 `AuditLog`**（`app/services/audit_service.py` 具备该能力但**无调用点**）⇒ 接管可在日志与轨迹复盘，但**不入审计库、无法按审计口径统计接管次数 / 时长分布**。**已登记入方案 §10 待登记项 6**，如需强审计须**单独立项**（含审计动作码与保留策略），本批**不代行决定** |
| 方案 §7 T4 | **判据表述更新**：拆为「轨迹（进程内可判）＋ 无 5xx（运行态）」两段，并明确「审计事件」的当前落点与未落库事实 |
| 方案 §4.1 | 增「v1.11.0 口径收敛」段：说明「切到备通道看 `rag_source` / `builtin_fallback_reason`」此前**只在同步路径成立**，现已两路径同源 |
| 第二批第 ⑥ 项 | **由「待做」改为「部分完成」**：轨迹口径收敛已做；仍待做 —— 通道定性（§9 问题 1 待裁定）、通道裁决进取数层、**内置 RAG 种子底座**（运行态 DB ＋ 嵌入模型）、§4.3 余项（画像增量升级形态待裁定 / 写路径与通道一致）、独立审计落库 |
| v1.4.8 既有三项缺陷（`DEF-BE-148-006`/`007`/`008`）与既有 flaky 集 | **不受影响** |
| 全仓未闭环项 | **仍为 0 项**（本批无缺陷；新增 1 项**能力缺口**已按待登记项显式登记） |

---

## 4O. 仓内一致性审计：§3.4 规则档余项与 §3.5 引用编号「正文已指定但未实施」登记（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.12.0** §3.4 / §3.5 / §6 / §10。
> **性质**：**登记项（非缺陷、非变更请求）** —— 方案正文已指定、仓内**未实施**，且**无外部依赖（可立即实施）**。**本记录无代码改动、不影响线上行为。**

### 4O.1 审计方法与取证

| 项 | 内容 |
|----|------|
| **动因** | T4 收口后对方案正文做一次**逐条 vs 仓内实现**核对，确认「正文指定 ≠ 已实施」，避免"方案写了"被误读为"已完成" |
| **方法（可复现）** | 对 `OpenLLM/backend/app/` 全仓检索关键标识：`strip_metadata` / `METADATA_NOISE` / `noise`、`"refine"`、`[M{` / `[K{` / `[M1]` / `[K1]`；并逐行读 `PromptAssembler.format_context` / `_format_list` 与 `prompt_pipeline._trim_segment` / `render()`（`app/edgerouter/orchestration/`） |

### 4O.2 审计结论：4 项未实施（均无外部依赖）

| # | 项 | 结论与取证 |
|:-:|----|-----------|
| a | **剥离元数据噪声**（`trace_id:None` 一类平铺字段） | **未实施**：标识检索**零命中**；`format_context` 的平铺分支（`key: value`）**不过滤 `None`/空值**、**无噪声键名单** |
| b | **相邻记忆条目合并同义重复行** | **未实施**：现有去重为「归一化后**精确重复即丢弃**」，**非合并**、**无同义判定**；`_normalize_key` 注释所称"同义重复"实为归一化精确重复，二者不等价 |
| c | **`refine` 回执字段**（`{mode, model, in_tokens, out_tokens, elapsed_ms, fallback}`） | **未实施**：`"refine"` 检索**零命中**（**规则档亦无落痕**，非仅模型档缺失） |
| d | **稳定引用编号 `[M1]`/`[K1]`**（与归因 A 片段索引对齐） | **未实施**：标识检索**零命中**；现仅产出 `"{序号}. {正文}"`，且 `_trim_segment` 在裁剪/去重后会**重排序号**（与「稳定编号」要求**相反**） |

### 4O.3 同时确认「已实施」（避免审计结论被扩大化）

| 项 | 状态 |
|----|------|
| §3.4 规则档：段内去重 / 配额整条裁剪 / 单条句边界截断 | **已实施**（第一批；保底一条见 v1.10.0） |
| §3.5：`system` 段启用 | **已实施**（第一批，`CONTEXT_SYSTEM_PROMPT_ENABLED` 默认关闭） |

### 4O.4 登记位置与关系

| 项 | 变化 |
|----|------|
| 方案 §3.4 / §3.5 | 各增**「实施状态」表**（含逐项取证），使「已实施 / 未实施」正文可见 |
| 方案 §6 第二批 | 新增第 **⑦** 行：四项**未实施且不受阻**，并与 ⑥ 中「需人工裁定」的各项**明确区分**（可立即实施） |
| 方案 §10 | 新增**待登记项 7**（含 (a)~(d) 明细与默认值建议：**(d) 建议开关默认关闭** —— 改动 Prompt 文本形态） |
| 缺陷 / 债务 | **无新增缺陷、无新增债务**（四项均为「正文已指定、尚未实施」，非实现错误） |
| 已判 `PASS` 判据（T3/T7/T9）与已知 `BLOCKED`/`SKIP` 结论 | **不受影响**（本记录无代码改动） |
| 全仓未闭环项 | **仍为 0 项**（本记录为登记项，非缺陷/变更请求） |
| **下一步（不受阻）** | 优先实施 (a)~(d)；其中 (c) 需先定义规则档回执的**落痕位置**（`context_metrics` 内嵌字段 还是独立字段） |

---

## 4P. §4O 登记项实施闭环：组装规则档余项落地（第二批第 ⑦ 项，判据 T10）（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.13.0** §3.4 / §3.5 / §6 / §7 T10；实现在 OpenLLM 仓（其《DevLogReport》**v1.29.0** 第 40 批，提交 `9f5f711`）。
> **性质**：**实施登记（第二批第 ⑦ 项完成）**，闭环 §4O 登记的 4 项「正文已指定但未实施」。**无新增缺陷、无新增债务。**

### 4P.1 实施清单

| # | 项 | 实施内容 | 默认值 / 开关 |
|:-:|----|----------|---------------|
| a | **元数据噪声剥离** | `PromptAssembler._format_flat_fields`：丢弃 `None`/空白值与链路元数据键（`trace_id`/`request_id`/`span_id`/`session_id`/`created_at`/`updated_at`/`elapsed_ms`/`latency_ms`）；**保留依据性字段**（`score`/`source`/`summary`）；全为噪声返回空串 | `CONTEXT_STRIP_METADATA_ENABLED` **默认 True**（关闭即逐字回退） |
| b | **相邻记忆条目同义合并** | `_trim_segment` ①' ＋ `_is_adjacent_synonym`（归一化**相互包含** **或** 字符二元组 **Jaccard ≥ 阈值**）＋ `_merge_adjacent_synonyms`（**保留较长者**、编号沿用先出现者）；**仅 `memory` 段、仅相邻**；计数与「完全重复即丢弃」**分离**（`merged_items`/`merged_tokens`） | `CONTEXT_ADJACENT_MERGE_ENABLED` **默认 True**；`CONTEXT_ADJACENT_MERGE_SIMILARITY` 默认 **0.85** |
| c | **`refine` 回执字段** | `PromptComposition.refine` ＝ `{mode:"rule", model:"", in_tokens, out_tokens, elapsed_ms, fallback:False}`；`in/out` 只计四类素材；**未启用不落痕** | 无独立开关（随预算/精炼开关落痕） |
| d | **稳定引用编号 `[M#]`/`[K#]`** | `PromptAssembler._format_list` 按组件加前缀；`prompt_pipeline._parse_items` 解析 `(前缀, 正文)`；**去重/合并/裁剪后编号不重排**；保底一条时前缀**连带计入配额** | `CONTEXT_REF_NUMBERS_ENABLED` **默认 False**（与同节 `system` 段开关一致 ⇒ 文本形态不变） |

### 4P.2 判据扩展

| 项 | 变化 |
|----|------|
| §7 **新增 T10** | **组装规则档契约**（噪声剥离 / 相邻同义合并 / 稳定编号），**全部进程内可判**；执行器新增 `check_t10` ⇒ 判据由 **T1~T9 扩为 T1~T10** |
| §7 **T6 拆分** | 与 T4 同思路：**规则档** `refine` 回执改为**进程内判定**（`mode=rule`/`fallback=false`/`out<in`/未启用不落痕）；**模型档（生成式精炼）仍 `BLOCKED`**（第三批，需达标模型 ＋ GPU 节点） |

### 4P.3 验证与证据

| 项 | 结果 |
|----|------|
| 新增护栏（TDD） | `tests/unit/test_assembly_refine_rule_tier.py` **25 例**（首轮 **RED 16 failed / 8 passed**，失败信息即缺口证据） |
| 既有护栏 | 预算族 / 组装族 **101 例全绿** ⇒ 整条丢弃、传统 `N.` 形重排序号等既有语义未变 |
| **运行态探针（逐项数值）** | `doc/test/evidence/cr149/assembly_rule_tier_probe.py`：(a) 单条载荷省 **74 token**；(b) `merged_items=1`、`merged_tokens=16`、较长者保留、`dropped_items=0`、**rag 不合并**；(c) `in=807 → out=100`、`elapsed_ms=0`、`fallback=false`、未启用不落痕；(d) 默认输出 `1. 甲/2. 乙` 不变、开启后 `[M1]/[M2]` 与 `[K1]/[K2]/[K3]` 下标对齐、去重后 **`[M1]`+`[M3]` 保留 / `[M2]` 不复用**、保底守配额 |
| 执行器两态实测 | **当前配置** ⇒ `{PASS:4（T3/T7/T9/T10）, SKIP:4（T1/T2/T5/T8）, BLOCKED:2（T4/T6）, FAIL:0}`；`--simulate` ⇒ `{PASS:7, SKIP:1（T8）, BLOCKED:2, FAIL:0}` —— 报告落 `t_acceptance_runner-result.json` 与 `t_acceptance_runner-simulate-result.json` |
| 全量回归 | `32 failed / 3145 passed / 0 error`（249.81 s） |
| **基线对照 + 对照实验（决定性）** | 与上一轮基线逐项对照**唯一差异为既有 flaky `test_v213_gateway_ext.py` 一族**；`git stash push -- <本批 3 个生产文件>` 后**隔离复跑该文件得到完全相同的 4 个失败** ⇒ **与本批无关**（如实登记为基线波动） |
| 静态质量 | 本轮 4 文件 `ruff` **零告警**；执行器 `All checks passed` |
| 提交 | OpenLLM `9f5f711`（3 生产 + 1 测试，`+610/-54`），显式路径、TDD 合规 |

### 4P.4 语义与影响面

| 项 | 说明 |
|----|------|
| (a)(b) 默认开启 | 影响**裁剪结果**（噪声条目与相邻近重复条目不再占额），但**仅在预算开启时生效**（`CONTEXT_BUDGET_ENABLED` 默认 **False**）且各有开关可回退 |
| (c) | **纯观测**（不改输出），未启用时不落痕 |
| (d) | **默认关闭** ⇒ **线上 Prompt 文本形态不变** |
| 残留（未实施） | **模型档生成式精炼**（第三批，需达标模型 ＋ GPU 节点，判据 T6 模型档部分）；通道定性（§9 问题 1）、通道裁决进取数层、内置 RAG 种子底座、§4.3 余项（画像增量升级形态 / 写路径与通道一致）、独立审计落库（§10 待登记项 6） |
| 全仓未闭环项 | **仍为 0 项**（§4O 的登记项已实施闭环；本批无缺陷、无债务） |

---

## 4Q. 仓内一致性审计（续）：§3.2 权重排序 `rank_score` 未实施 → 同版实施闭环（第二批第 ⑦ 项续，判据 T10④）（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.14.0** §3.2 / §3.3 / §6 / §7 T10 / §10；实现在 OpenLLM 仓（其《DevLogReport》**v1.30.0** 第 41 批，提交 `d80085f`）。
> **性质**：**审计发现 + 同版实施闭环**（延续 §4O → §4P 的「先登记后落地」模式）。**无新增缺陷、无新增债务。**

### 4Q.1 审计发现与取证

| 项 | 内容 |
|----|------|
| **方案要求** | §3.2 选择第三项：「在重排分数之外**叠加时效与来源权重**（记忆按 `updated_at` 衰减、画像字段按维度白名单、知识库条目保留原始 `score`），产出统一的 **`rank_score`** 供预算层使用」；§3.3 memory/rag 行：「按 `rank_score` **降序保留整条**，末尾条目整体丢弃」 |
| **取证（可复现）** | 对 `OpenLLM/backend/app/` 全仓检索 `rank_score` ⇒ **零命中**；`PromptAssembler.format_context` 按**取数原序**逐条编号；`prompt_pipeline._trim_segment` 的配额裁剪为「从**尾部**整条丢弃」⇒ **丢弃对象是「取数最末」而非「排名最低」** |
| **影响定性** | 当取数顺序与相关性/时新性不一致时，**被丢弃的可能是更相关或更新的条目** —— 属「**选得不准**」而非「装不下」，与方案 §2 原则 1「精度优先来自**选得准**，而不是塞得多」**相悖**；且 §3.3 的「按 `rank_score` 降序」**缺少实现前提** |

### 4Q.2 实施内容（v1.14.0）

| # | 项 | 内容 |
|:-:|----|------|
| 1 | **`rank_score` 计算** | `assembler._rank_score` ＝ **来源分数**（`score`/`relevance`/`rank_score` 首个可解析者；**缺失视为中性 1.0**）× **时效衰减**（`_item_decay`：`0.5 ** (age_days / 半衰期)`；**仅 `memory` 段**，其余段**保留原始 score**） |
| 2 | **fail-open** | 时间戳缺失/**不可解析** ⇒ 衰减 **1.0**（视为「新鲜」）⇒ **不得因缺字段被降级到末尾**；未来时间戳 age 取 0 |
| 3 | **稳定排序** | 同分**保持原相对顺序**（`sorted(..., reverse=True)` 稳定） |
| 4 | **与引用编号对齐（关键）** | 排序**只改呈现顺序**；引用编号取**原始下标**（`_ordered_items` 返回 `(原始下标, 条目)`）⇒ `[M2]` 仍指向 `results[1]`，**与归因 A 的片段索引始终对齐** |
| 5 | **fail-safe（不改序的三种情形）** | 开关关闭（`CONTEXT_RANK_SORT_ENABLED` 默认 **True**）/ 条目数 < 2 / **无任何可用排序依据** ⇒ **保持取数原序**（**不臆造顺序**） |
| 6 | **半衰期可配** | `CONTEXT_RANK_DECAY_HALF_LIFE_DAYS` 默认 **30** 天 |

### 4Q.3 验证与证据

| 项 | 结果 |
|----|------|
| 新增护栏（TDD） | `tests/unit/test_context_rank_selection.py` **12 例**（首轮 **RED 8 failed / 4 passed**，失败信息即缺口证据） |
| 既有护栏 | 组装/预算/回退族 **143 例全绿** ⇒ 编号稳定性、整条丢弃、相邻合并等既有语义未变 |
| **运行态探针（决定性）** | `doc/test/evidence/cr149/assembly_rule_tier_probe.py` **(e) 权重排序** 段：`rag_order="1. 高分/2. 中分/3. 低分"`；`memory_order="1. 新记忆/2. 无时间戳记忆/3. 旧记忆"`（**fail-open 生效**）；`labeled_ranked="[K2] 高分\n[K1] 低分"`（**编号取原始下标**）；开关关 `"1. 低分\n2. 高分"`（**逐字回退**）；无依据 `"1. 甲/2. 乙/3. 丙"`（**不臆造顺序**）；尾部丢弃报告 `dropped_items=1` 且排名靠前者存活 |
| 执行器两态实测 | **当前配置** ⇒ `{PASS:4（T3/T7/T9/T10）, SKIP:4, BLOCKED:2, FAIL:0}`；`--simulate` ⇒ `{PASS:7, SKIP:1, BLOCKED:2, FAIL:0}` —— 报告落 `t_acceptance_runner-result.json` 与 `t_acceptance_runner-simulate-result.json` |
| 全量回归 | `32 failed / 3157 passed / 0 error`（247.93 s） |
| **基线对照** | **失败集与上一轮基线逐项完全相同**（逐项 testid 归一化后 `Compare-Object` **32 = 32，零差异 ⇒ 零新增失败**） |
| 静态质量 | 本轮 3 文件 `ruff` **零告警**；执行器 `All checks passed` |
| 提交 | OpenLLM `d80085f`（2 生产 + 1 测试，`+385/-8`），显式路径、TDD 合规 |

### 4Q.4 关系与影响面

| 项 | 说明 |
|----|------|
| 方案 §7 T10 | **增补第 ④ 项**（权重排序：rag/memory 降序、fail-open、编号对齐、开关回退、无依据不改序） |
| 方案 §3.2 / §3.3 | 各增**实施状态**说明；§3.3 表逐行给出「已实施 / 已按 section 粒度实施 / 未细分」 |
| 方案 §10 待登记项 7 | **扩为三项合并登记**：§3.4 规则档余项 ＋ §3.5 引用编号（v1.13.0）＋ §3.2 权重排序（v1.14.0），**全部标注「已实施闭环」** |
| 语义与影响面 | 排序默认开启 ⇒ 影响**呈现顺序与尾部裁剪对象**（丢弃排名最低者）；**引用编号（开启时）仍指向原始片段**、**无排序依据时完全不动序**、开关可一键回退；**裁剪仍仅在预算开启时生效**（`CONTEXT_BUDGET_ENABLED` 默认 False） |
| **残留（未实施，如实登记）** | §3.3 profile 行的**字段级**维度优先级未细分（当前按 **section 粒度** person → business，`_format_profile_ctx` 固定顺序 + 尾部裁剪）；模型档生成式精炼（第三批）；通道定性（§9 问题 1）、通道裁决进取数层、内置 RAG 种子底座、§4.3 余项、独立审计落库（方案 §10 待登记项 6） |
| 全仓未闭环项 | **仍为 0 项**（本批无缺陷、无债务） |

---

## 4R. 逐条复核发现的三处「正文已指定但未实施」→ 同版实施闭环（第二批续，判据 T10⑤ / T11）（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.15.0** §3.2 / §3.3 / §4.3 / §5.8 / §7 T10 / T11；实现在 OpenLLM 仓（其《DevLogReport》**v1.31.0** 第 42 批，提交 `58358c6`）。
> **性质**：**复盘式逐条复核（§3.2/§3.3/§4.2/§4.3/§5.8 逐行 vs 仓内实现）＋ 同版实施闭环**。**无新增缺陷、无新增债务。**

### 4R.1 三处发现与取证

| # | 项 | 方案要求 | 审计取证（可复现） | 影响定性 |
|:-:|----|----------|--------------------|----------|
| 1 | **§4.3 写路径与通道一致** | 「回写前经 `assert_write_channel_is_primary` 校验，避免通道切换期间双写」；§8 风险表回退口径同此 | `assert_write_channel_is_primary` **已实现**，但全仓**仅被单测与脚本引用**（`app/` 内**零调用点**、`ChannelStateManager` **从未实例化**） | **§8 所列回退手段未接线** ⇒ 「通道切换期间双写」**无防护**（数据一致性风险） |
| 2 | **§3.2 画像字段按维度白名单 ＋ §3.3 profile 行「超出丢弃低优先维度」** | 维度白名单参与保留/权重；溢出按维度优先级丢弃低优先维度 | 全仓画像相关 `whitelist` **零命中**（无配置键）；`_format_profile_ctx` 把 section 内**全部维度压成一行** ⇒ 裁剪最小单位是**整段** | **无法「丢弃低优先维度」**（要么全留、要么整段丢），且维度取舍**不可配置** |
| 3 | **§3.3 产出物 / §5.8 观测行** | `refine.mode/model/in_tokens/out_tokens/elapsed_ms/fallback` **落 `context_metrics`**，用于评测与容量规划 | `ContextReceipt.to_record()` 仅落 `segment_tokens`/`budget`/`truncated`；`refine` **仅存在于内存 `PromptComposition`** | **观测链缺一环** ⇒ 评测与容量规划取不到精炼回执 |

### 4R.2 实施内容（v1.15.0）

| # | 项 | 内容 |
|:-:|----|------|
| 1 | **写路径通道护栏接线** | 新增 `_get_channel_manager()`（**每次按当前配置构造** ⇒ `CHANNEL_PREFERENCE` 热改即时生效）＋ `_writeback_channel_primary()`；三路回写在 **`submit` 之前**校验写通道为当前**唯一主通道**（`CHANNEL_B`）；**非主通道 ⇒ 暂停本轮回写**（三路返回 `"skipped"`、**零入队**，`reason="channel_not_primary"`，与价值闸门**同回执口径**、**不与** `False`（幂等命中）混用）；**暂停而非抛错**（回写是后台链路）；开关 `WRITEBACK_CHANNEL_GUARD_ENABLED`（**默认 True**）；**配置非法 ⇒ WARN + 放行**（fail-open，避免笔误静默停库） |
| 2 | **画像维度级优先级 ＋ 白名单** | `PROFILE_DIMENSION_LINES_ENABLED`（**默认 True**）：段头单独成行、**每行一个维度** ⇒ 裁剪最小单位为**维度**，超配额按「后出现先丢」淘汰 `business` 维度；关闭即**逐字回退**「单段一行」。`PROFILE_DIMENSION_WHITELIST`：留空=不限制；非空时**仅保留列出维度并按列出顺序排列**；无命中返回空（不注入空壳） |
| 3 | **`refine` 落 `context_metrics`** | `ContextReceipt.to_record()` 增 `refine`（**仅非空时落痕**，与 `budget`/`truncated` 同口径） |

### 4R.3 验证与证据

| 项 | 结果 |
|----|------|
| 新增护栏（TDD，20 例） | `test_writeback_channel_guard.py` **8 例**（默认主通道行为不变 / 开关关闭逐字回退 / 非主通道三路 `skipped` 且零入队 / `skipped` 与 `False` 不混用 / 配置非法 fail-open / 断言确被调用且通道为 `b` / `ChannelSwitchError` 被吸收为暂停）＋ `test_profile_dimension_priority.py` **10 例**（维度独立成行 / person 先于 business / 超配额先丢 business 维度且守配额 / 开关关闭回退单段一行 / 白名单过滤与排序 / 白名单无命中返回空 / 默认不限制）＋ `test_assembly_refine_rule_tier.py` 增 **2 例**（`refine` 落 metrics / 未启用不落痕）；**首轮 RED 14 failed**（失败信息即缺口证据） |
| 既有护栏 | 画像族 / 回写族 / 计量族 **99 例全绿** ⇒ 既有语义未变 |
| **运行态探针（决定性）** | 新增 `writeback_channel_guard_probe.py`（真实回写回调 ＋ 队列替身）：默认主通道三路入队且 `unchanged=true`；`a-primary` 下 `submitted=[]`、三路 `"skipped"`、`paused=true`；开关关 `verbatim=true`；非法 preference `allowed=true`。`assembly_rule_tier_probe.py` 增 **(f) 画像维度优先级**（维度独立成行 / person 优先 / 开关回退 / 白名单过滤与无命中为空 / 超配额先丢 business 维度：`dropped_items=2`、`used ≤ quota`）与 **(g) refine 落 context_metrics**（字段存在且与内存回执一致、未启用不落痕、其余字段不受影响） |
| 执行器两态实测 | **当前配置** ⇒ `{PASS:5（T3/T7/T9/T10/T11）, SKIP:4（T1/T2/T5/T8）, BLOCKED:2（T4/T6）, FAIL:0}`；`--simulate` ⇒ `{PASS:8, SKIP:1（T8）, BLOCKED:2, FAIL:0}` —— 报告落 `t_acceptance_runner-result.json` 与 `t_acceptance_runner-simulate-result.json` |
| 全量回归 | `31 failed / 3176 passed / 0 error`（246.58 s） |
| **基线对照** | **零新增失败**（逐项 testid 归一化后 `Compare-Object` **无 `=>` 项**；差异项仍是既有 flaky `test_v213_gateway_ext.py` 一族本轮转绿 ⇒ 如实登记为**基线波动**） |
| 静态质量 | 本轮 6 文件 `ruff` **零告警**；执行器 `All checks passed` |
| 提交 | OpenLLM `58358c6`（3 生产 + 3 测试，`+486/-4`），显式路径、TDD 合规 |

### 4R.4 关系与影响面

| 项 | 说明 |
|----|------|
| 方案 §7 | **T10 补 ⑤**（画像维度白名单 / 维度级优先级）＋ **新增 T11**（写路径与通道一致）；执行器判据扩为 **T1~T11** |
| 方案 §3.2 / §3.3 / §4.3 / §5.8 | 各增**实施状态**说明；§4.3 表对应行标记 **【已实施（v1.15.0）】** |
| 方案 §10 | 新增**待登记项 8**（三处发现均已闭环）；表内共 8 项，其中第 7、8 项均实施闭环 |
| 语义与影响面 | (1) 默认 `b-primary` ⇒ **线上行为不变**，仅通道切到 A 的切换期间才暂停回写（**即设计意图**）；(2) 画像**文本形态**由「单段一行」变为「段头 ＋ 每行一个维度」（**默认开启**，开关可一键回退；**白名单默认留空 ⇒ 不删任何维度**）；(3) 纯观测扩展（新增字段，不改输出） |
| **残留（未实施，如实登记）** | §4.3「写路径 A/B 等价」**矩阵登记项**（取决于 §9 问题 1 通道定性裁定）；通道 A 定性；模型档生成式精炼（第三批）；通道裁决进取数层；内置 RAG 种子底座（运行态 DB ＋ 嵌入模型）；§4.3 画像增量升级的线上 LLM 门控（§9 问题 7）；独立审计落库（方案 §10 待登记项 6） |
| 全仓未闭环项 | **仍为 0 项**（本批无缺陷、无债务） |

---

## 4S. 逐条复核发现的第 4 处「正文已指定但未实施」：§5.8 路由分类缓存 → 同版闭环（判据 T9④）（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.16.0** §5.8 / §7 T9；实现在 OpenLLM 仓（其《DevLogReport》**v1.32.0** 第 43 批，提交 `3bb9a3f`）。
> **性质**：**复核发现 ＋ 同版实施闭环**。**无新增缺陷、无新增债务。**

### 4S.1 发现与取证

| 项 | 内容 |
|----|------|
| **方案要求** | §5.8 在线档预算行：「**路由分类按 query 归一化缓存**」—— 同会话重复提问不重复分类、命中缓存直接返回，**不重付 ≤300ms 兜底预算** |
| **取证（可复现）** | `ComponentRouter` 全类检索 `cache` ⇒ **零命中**；`decide()` 每次未命中规则都**重新调用** `llm_classifier` ⇒ 重复提问**重复付预算** |
| **关键约束（决定实现形态）** | **联网关每次请求都会新建 `ComponentRouter`**（分类器闭包捕获 db/identity）⇒ 缓存挂实例上**永不命中**，**必须进程级** |
| **同批暴露的隔离问题** | 进程级缓存使两处既有文件中「同一 query ＋ **不同分类器替身**」的用例**跨用例命中**（实测 **4 failed**）—— 属**测试隔离缺口**，非被测逻辑缺陷 |

### 4S.2 实施内容（v1.16.0）

| # | 项 | 内容 |
|:-:|----|------|
| 1 | **进程级 LRU** | `_LLM_DECISION_CACHE`（`OrderedDict` ＋ 锁）＋ `_cache_get` / `_cache_put`；容量由 `COMPONENT_ROUTER_LLM_CACHE_SIZE` 控制（默认 **256**；**置 0 = 关闭缓存**，逐字回退） |
| 2 | **键＝（作用域, 归一化 query）** | 归一化 ＝ 压缩空白 ＋ 大小写不敏感（与段内去重口径一致）；作用域 ＝ **`模型标签:规则指纹`** |
| 3 | **防陈旧（两处指纹刷新）** | `_refresh_rules_fingerprint()` 在 `_load_rules`（初始加载）与 `_check_and_reload`（热更新）两处规则替换点调用 ⇒ **规则变更后旧条目自然失配**；作用域含模型标签 ⇒ **换模型亦失配** |
| 4 | **不变式** | 命中返回**副本**（调用方改写不污染缓存）；**失败与非法输出不入缓存**（不把分类失败固化成命中）；**规则达标时不触碰分类器/缓存**（既有语义） |
| 5 | **可观测与可隔离** | 新增 `clear_llm_decision_cache()`（测试隔离/排障）与 `llm_decision_cache_size()`（观测） |

### 4S.3 验证与证据

| 项 | 结果 |
|----|------|
| 新增护栏（TDD） | `tests/unit/test_component_router_classification_cache.py` **14 例**（首轮 **RED 6 failed**，失败信息即缺口证据） |
| 同批隔离修正 | `test_component_router_decision_tuning.py` 与 `test_orchestration.py` 各加 **autouse 清缓存 fixture** —— **不改任何断言**（仅恢复用例隔离）；修正后两文件 **77 例全绿** |
| **运行态探针（决定性）** | `component_decision_probe.py` **④ classification_cache** 段：`same_query_calls=1`（同题命中）、`distinct_query_calls=2`（异题各付一次）、`cached_decision_equal=true`、`capacity_zero_calls=2`（容量 0 逐字回退）、`default_capacity=256` |
| 执行器两态实测 | **当前配置** ⇒ `{PASS:5（T3/T7/T9/T10/T11）, SKIP:4, BLOCKED:2, FAIL:0}`；`--simulate` ⇒ `{PASS:8, SKIP:1, BLOCKED:2, FAIL:0}` —— 报告落 `t_acceptance_runner-result.json` 与 `t_acceptance_runner-simulate-result.json` |
| 全量回归 | `32 failed / 3189 passed / 0 error`（249.94 s） |
| **基线对照** | 与上一轮基线逐项对照**唯一差异为既有 flaky `test_v213_gateway_ext.py` 一族本轮转红**（该例此前往返红/绿交替，已多次以对照实验证明与本批无关）；**其余失败集完全相同** |
| **静态质量（逐文件基线对照，决定性）** | `git stash` 回退本批改动后复测：`component_router.py` **39 → 39**、`config.py` **0 → 0**、两个既有测试文件 **0 → 0 / 2 → 2**、新测试文件 **0** ⇒ **零新增告警** |
| 提交 | OpenLLM `3bb9a3f`（3 生产/配置 ＋ 3 测试，`+333/-3`），显式路径、TDD 合规；另 `9d6537d` 为同批文档订正（提交号回填） |

### 4S.4 关系与影响面

| 项 | 说明 |
|----|------|
| 方案 §7 T9 | **补第 ④ 项**（兜底分类缓存：同题只付一次 / 异题各付一次 / 容量 0 逐字回退） |
| 方案 §5.8 | 缓存行标注「**路由分类缓存已实施（v1.16.0）**」；**精炼结果缓存**（`(query_hash, 段内容 hash)`，10 分钟）**仍待** —— 规则档精炼确定性且亚毫秒（缓存无收益），模型档属第三批 ⇒ **与第三批同批推进** |
| 方案 §10 | 新增**待登记项 9**（已闭环）；表内共 9 项，其中第 7、8、9 项均实施闭环 |
| 语义与影响面 | 缓存**仅在 LLM 兜底分类器被注入时生效**（`COMPONENT_ROUTER_LLM_FALLBACK_ENABLED` **默认关闭** ⇒ 线上默认路径**零影响**）；LRU 有界（默认 256）；命中返回副本、失败不固化、规则/模型变更即失配 ⇒ **不引入陈旧决策** |
| **残留（未实施，如实登记）** | §5.8 **精炼结果缓存**（与第三批同批）；通道 A 定性（§9 问题 1）与 §4.3「写路径 A/B 等价」矩阵项；模型档生成式精炼（第三批）；通道裁决进取数层；内置 RAG 种子底座（运行态 DB ＋ 嵌入模型）；§4.3 画像增量升级的线上 LLM 门控（§9 问题 7）；独立审计落库（方案 §10 待登记项 6） |
| 全仓未闭环项 | **仍为 0 项**（本批无缺陷、无债务） |

---

## 4T. 复核发现：§5.2 精炼触发条件 ＋ §5.3 任务护栏未实施 → 判定部分同版闭环（第二批续，判据 T12）（2026-09-27）

> **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.17.0** §5.2 / §5.3 / §7 T12；实现在 OpenLLM 仓（其《DevLogReport》**v1.33.0** 第 44 批，提交 `4f3e706`）。
> **性质**：**复核发现 ＋ 同版实施闭环（判定部分）**。**无新增缺陷、无新增债务。**

### 4T.1 发现与取证

| 项 | 内容 |
|----|------|
| **方案要求** | §5.2「精炼只在满足任一条件时启动，其余情况走规则档」（4 行触发条件表）；§5.3「只允许引用原文片段，不得引入新实体或数值；输出强制编号列表以便逐条归因；压缩率目标 20%~40%；任何解析失败即丢弃模型输出」 |
| **取证（可复现）** | 全仓 `app/` 检索 `should_refine` / `CONTEXT_REFINE` / `validate_refine` **零命中** ⇒ **未实施** |
| **后果定性** | ① `CONTEXT_BUDGET_ENABLED` 打开后**一律走规则档**（无触发判定，无从判断「何时该升级到精炼」）；② 第三批接模型档时**缺少两道闸门**：**「何时该调模型」**（成本控制）与**「模型输出是否可用」**（幻觉拦截）—— 按 §2 原则 3「精炼按需触发、有硬预算、可降级」，二者是**模型档的前置件** |
| **为何可先行实施** | 触发判定与输出校验均为**纯函数**（不依赖模型、不依赖运行态 DB）⇒ 可在**进程内**判定，且是模型档落地的前置依赖 |

### 4T.2 实施内容（v1.17.0）

| # | 项 | 内容 |
|:-:|----|------|
| 1 | **§5.2 行 1** | `memory`/`rag` 段 token > 配额 × `CONTEXT_REFINE_OVER_QUOTA_RATIO`（默认 **1.5**，**严格大于** ⇒ 恰为 1.5 倍**不触发**）；`history`/`profile` **不参与**（与方案表一致） |
| 2 | **§5.2 行 2** | 单段条目数 > `CONTEXT_REFINE_MAX_ITEMS`（默认 **8**，严格大于） |
| 3 | **§5.2 行 3** | 段内相似度 > `CONTEXT_REFINE_DUP_SIMILARITY`（默认 **0.85**）的条目**占比** > `CONTEXT_REFINE_DUP_SHARE`（默认 **0.30**）；**非相邻**（段内任意两条相似即计入） |
| 4 | **§5.2 行 4** | **未实施（如实标注）**：多源冲突需**语义判定** ⇒ `unimplemented=["multi_source_conflict"]` 显式列出，且 `TRIGGER_REASONS` **不含** conflict 类理由（**不伪实现**） |
| 5 | **§5.3 护栏** | `validate_refine_output()`：`unlocatable`（逐条须可定位，改写即违规）/ `new_numbers`（**编号前缀序号不计入**）/ `not_numbered` / `empty_output` ⇒ 任一违规 `valid=false` **即弃**；`located` 逐条给出源下标（`-1` 不可定位） |
| 6 | **口径统一（去重实现分叉）** | 新增 `prompt_pipeline.text_similarity` / `is_redundant_pair` 作为**唯一相似度实现**，「相邻同义合并」与「触发判定」**共用**（此前若各写一套必然分叉） |
| 7 | **观测接线** | `build_prompt` 在 `CONTEXT_REFINE_TRIGGER_ENABLED`（**默认关闭**）开启时落 `PromptComposition.refine_trigger` → `context_metrics.refine_trigger`（**只读**，§2 原则 6） |

### 4T.3 验证与证据

| 项 | 结果 |
|----|------|
| 新增护栏（TDD） | `tests/unit/test_refine_trigger_and_guard.py` **22 例**（首轮 **RED 5 failed**，失败信息即缺口证据）—— 行 1/2/3 各含「触发」与「阈值边界（不触发）」；行 4 未实施标注与「不伪实现」；护栏四类违规；空输出非法；编号定位；**开关两态注入文本逐字相同** |
| 既有护栏 | 预算/组装/排序/画像族 **73 例全绿** ⇒ 相似度重构**行为等价**（`_is_adjacent_synonym` 语义未变） |
| **运行态探针（决定性）** | `doc/test/evidence/cr149/refine_trigger_probe.py`：行 1 `160/100 → triggered=true`、`150/100 → false`、`history 303/150 → false`；行 2 `9 条 → true`、`8 条 → false`；行 3 `2/4=50% → true`、`2/8=25% → false`；行 4 `reasons=[]` 且 `unimplemented=["multi_source_conflict"]`；护栏 `verbatim → valid=true`、`rewrite → unlocatable`、`new_number → new_numbers`、`empty → empty_output`、`unnumbered → not_numbered`；`prompt_identical=true` |
| 执行器两态实测 | **当前配置** ⇒ `{PASS:6（T3/T7/T9/T10/T11/T12）, SKIP:4, BLOCKED:2, FAIL:0}`；`--simulate` ⇒ `{PASS:9, SKIP:1, BLOCKED:2, FAIL:0}` —— 报告落 `t_acceptance_runner-result.json` 与 `t_acceptance_runner-simulate-result.json` |
| 静态质量 | `refine.py`（新增）与本次改动的 4 个文件 `ruff` **All checks passed**（零告警） |
| 提交 | OpenLLM `4f3e706`（`feat(v149)`，5 文件 `+605/-7`），显式路径、TDD 合规 |

### 4T.4 关系与影响面

| 项 | 说明 |
|----|------|
| 方案 §7 | **新增 T12**（精炼触发条件与输出护栏，**纯进程内可判**）；执行器判据扩为 **T1~T12** |
| 方案 §5.2 / §5.3 | 各增**实施状态**表；行 4 与「模型调用本身」**如实标注未实施** |
| 方案 §10 | 待登记项 **9** 扩充（并入 v1.17.0 的 §5.2/§5.3 判定部分；表内共 9 项） |
| 语义与影响面 | 触发**观测**开关**默认关闭** ⇒ **线上行为不变**；护栏为**纯函数库**（无 IO/无模型/无全局状态），**仅在被调用时**生效；两者均**不改变**既有注入内容 |
| **残留（未实施，如实登记）** | **模型调用与三类任务模板**（抽取式压缩 / 要点摘要 / 去噪重排）属**第三批**（需达标模型 ＋ GPU 节点，§5.4/§5.6 门槛）；**§5.2 行 4 多源冲突**（需语义判定）；§5.8 **精炼结果缓存**（与第三批同批）；通道 A 定性（§9 问题 1）与 §4.3「写路径 A/B 等价」矩阵项；通道裁决进取数层；内置 RAG 种子底座；§4.3 画像增量升级的线上 LLM 门控（§9 问题 7）；独立审计落库（方案 §10 待登记项 6） |
| 全仓未闭环项 | **仍为 0 项**（本批无缺陷、无债务） |

---

## 4U. 既有失败逐项分诊（31 → 21）＋ §4.3 执行层价值闸门补齐 ＋ 判据时效基准订正（2026-09-27）

### 4U.1 发现与取证

**动因**：CR-149 各批次均以「与本批无关」的对照实验绕过全量回归中的 **31 项既有失败**，但**从未逐项分诊** ⇒ 其中可能混有**本方案范围内的真实缺陷**（被"既有失败"标签掩盖）。本轮按「**是否属本方案范围**」逐项定性。

| 类别 | 项数 | 取证 |
|------|:----:|------|
| **① 范围内真实缺陷** | 1 | `app/api/writeback.py::_rag_writeback` **只写不读** `save_if_valuable`：全仓检索该键 —— **只有写入**（`WritebackTarget.save_if_valuable` 字段 ＋ `payload["save_if_valuable"] = cfg.save_if_valuable`），**无任何读取方** ⇒ §4.3 明文的「实际判定（**而非仅契约字段**）」只落在**网关决策层**（v1.4.0 `grade_writeback_targets`/`grade_rag_ingest`，不达标即**不入队**）；**执行层**与**直接调用** `POST /openllm/v1/writeback` 的路径**不受闸门约束** ⇒ 显式声明「不值得沉淀」仍向 OpenRAG 提交入库请求（**知识库膨胀入口未闭合**）。既有用例 `test_save_if_valuable_false_skips_without_request` 自 `cr149-batch1-regression` 起**长期 RED**，即该契约的现成指认 |
| **② 范围内陈旧/失隔离用例** | 9 | **(a)** `test_writeback_degradation.py` **3 例**：按「三路回写前」**返回值元数**解包（v1.4.8 增 profile 路后 `_build_writeback_callback` 返回 **4** 元组）⇒ `ValueError: too many values to unpack (expected 3)`；**同族次生缺陷（本轮新发现）**：该函数现会装配**生产 handler**（`_ensure_writeback_handlers`，`DEF-BE-148-021`）⇒ 用例原在**构造回调之前**注册替身会被覆盖（实测 `recorded` 恒空、生产 handler 被真调用并 401/缺 kb_id 失败）。**(b)** `test_v213_gateway_ext.py` **3 例**：`test_bypass_marker_injected` 的补丁替身返回 **4 元组**而 `_normalize_request` 已返回 **5 元组**（v1.4.8 增 `history_ctx`）⇒ `ValueError: not enough values to unpack (expected 5, got 4)` → 端点 **500**；另两例「适配器**未注册**」**不自持前置**（适配器由应用启动与其它用例写入模块级装配）⇒ 单独跑该文件 **4 failed**、全量跑其中 memory 一例又「通过」、其余为真实适配器挂在已关闭事件循环上的 `RuntimeError: Event loop is closed`（**顺序相关漂移**）。**(c)** `test_real_contract_memory.py` **3 例**：引用的私有函数 `_resolve_memory_metadata` 经 `git log -S` 取证**全仓历史零命中**（**幻影符号**，自建立即恒 `ImportError`，长期被根 conftest 缺陷掩盖 ⇒ **从未真正执行**） |
| **③ 本方案自身判据的缺陷** | 3 | T10 ④ 与探针 `assembly_rule_tier_probe.py` (e) 用**硬编码时刻** `datetime(2026, 9, 27, 12, 0, 0)` 作时效基准 ⇒ 「零龄」样本的 age 在壁钟**越过该时刻前后**由 0 变正（`max(0.0, …)` 钳制失效）⇒ 衰减由**恰 1.0** 变为 <1.0 ⇒ 断言「新记忆 排在 无时间戳之前」**随壁钟自行翻转**（**同一提交**实测：12:00 前 `PASS`、之后 `FAIL`）。**且该断言与实现语义不符**：fail-open 取值**恰为 1.0** ⇒ 语义是「**不劣化**（等价刚刚发生）」，**不是**「排在新记忆之后」；任何**严格过去**的时间戳衰减都 <1.0 ⇒ 该断言**数学上不可持续** |
| **④ 范围外（如实登记，未改）** | 18 | **401 族 9 例**（`test_gateway_401_format.py` 7 ＋ `test_coverage_boost_v2112.py` 2）断言错误体**不含 `detail`**，与项目错误规范 `{code, message, detail, request_id}`（`AGENTS.md` §2）**相反** ⇒ 属**错误码契约域**；**「模型不存在」错误码族 3 例**（`2001` vs 实测 `5001`/`1004`）＋ 流式收尾 `close` 未调用；**环境条件类 4 例**（工作区 `.env` 显式置 `OPENLLM_{OPENMEMORY,OPENRAG,DPS}_REAL=true` 而用例断言 dev profile **缺省 false** ⇒ **配置策略冲突，非代码缺陷**）；`test_model_router_wiring.py` **2**；`test_joinedload_asserts.py` **2**（用例自身构造错误：把 `Table` 当列表达式）；`test_conversations_api.py` **1**（响应模型校验） |

### 4U.2 实施内容

| 项 | 内容 |
|----|------|
| **(1) 执行层价值闸门（范围内真实缺陷，已修）** | `_rag_writeback` 增前置判定：`kwargs.get("save_if_valuable", True) is False` ⇒ **零出站请求**收口（记 INFO 含 user/kb、返回 `None`、行置 done）；**跳过判定先于适配器可用性校验**（**不写就不需要适配器**，避免为空操作触发组件级降级与重试）；**缺省（不传该键）视为 `True`** ⇒ 既有调用方**逐字回退**。语义与既有「显式关闭沉淀」口径一致（`evaluate.py` 亦用 `is False`） |
| **(2) 三个测试文件按当前契约订正（断言不降反升）** | **(a)** `test_writeback_degradation.py`：改 4 元组解包 ＋ **补断第三路（profile）**齐备/降级时同收口 ＋ 补 `kwargs` 键集与防御分支取值 ＋ **写明 handler 注册顺序契约**（替身须在构造回调**之后**注册）＋ 补载荷贯通断言（`user_id`/`tenant_code`/`role`）。**(b)** `test_v213_gateway_ext.py`：补丁替身补第 5 项 `history_ctx=None`；两例「适配器未注册」改为 **monkeypatch 显式置空**（`_get_gateway_adapters` / `_get_profile_adapter_wb`），**使前提由用例自己决定**（与同族 `test_rag_writeback_missing_kb_id_raises` 写法一致）。**(c)** `test_real_contract_memory.py`：按**实际分层**重写为 4 例 —— 网关**只透传**（缺省 `metadata=None`、显式类型原样透传）／adapter 按 **D1** 缺省 `None → persistent`／stub 缺省 `episodic` 属**服务侧**（以 stub 端点级取证） |
| **(3) 新增护栏** | `tests/unit/test_rag_writeback_value_gate.py` **7 例**：跳过先于适配器获取（`_get_gateway_adapters` 被调用即失败）、缺省逐字回退（仍提交 1 次且 URL 正确）、显式 `true` 仍提交、stub 模式同拦、跳过 INFO 可观测；**端点级 2 例**（`POST /openllm/v1/writeback` rag+sync：`false` ⇒ 200/`accepted` 且**零请求**；缺省 ⇒ 仍提交） |
| **(4) 判据与探针时效基准订正（本方案自身缺陷）** | T10 ④ 与探针 (e)：基准改 `datetime.now()`（**相对**、不随壁钟翻转）＋「零龄」样本改「一天前」＋断言改为**三条确定性判定**（`fail_open_decay == 1.0`；**严格单调** `1.0 > 0.977 > 0.0625`；输出序 `无时间戳 → 新记忆 → 旧记忆`）＋三值落 `detail.rank_decay`；同源基准同步订正护栏 `test_context_rank_selection.py::_iso` |
| **(5) T5 判据扩展** | T5 由整条 `SKIP` 改**分两段**：① 网关决策闸门（开关，未开 ⇒ `SKIP`，口径不变）；② **执行层价值闸门（无开关、恒生效）** ⇒ **进程内恒可判**，不达标即 `FAIL`；执行器新增 `_rag_value_gate_probe()` 并落 `detail.rag_value_gate` |

### 4U.3 验证与证据

| 项 | 结果 |
|----|------|
| **RED 指认（修复前）** | `test_save_if_valuable_false_skips_without_request`：`assert [<Request('POST','http://openrag.test/api/v1/collections/kb_main/documents/text')>] == []` —— 显式声明不沉淀仍发起入库请求 |
| 新增护栏 | `test_rag_writeback_value_gate.py` **7 例全绿**；同批修复的 4 个测试文件合计 **116 例**（含既有）**全绿**，仅余 2 例环境条件类（见下） |
| **全量回归（两轮独立）** | `cr149-t18-full.txt` / `cr149-t19-full.txt`：**21 failed / 3230 passed / 0 error**（252.35 s / 252.54 s）；基线 `cr149-t17-full.txt` **31 failed / 3212 passed**；**逐项 testid 归一化 `Compare-Object`：新增失败集为空 ⇒ 零回归**，已消失 **10** 项（＝本轮修复项，含 3 项幻影用例）；**两轮失败集逐项零差异** ⇒ 时效基准订正后判据**可复现**（订正前同一提交会随壁钟翻转） |
| 执行器两态实测 | **当前配置** ⇒ `{PASS:6（T3/T7/T9/T10/T11/T12）, SKIP:4（T1/T2/T5/T8；T5 已带段②通过取证）, BLOCKED:2（T4/T6）, FAIL:0}`；`--simulate` ⇒ `{PASS:9（含 T5）, SKIP:1（T8）, BLOCKED:2, FAIL:0}` —— 落 `t_acceptance_runner-result.json` / `-simulate-result.json`；T5 `detail.rag_value_gate = {skipped_requests: 0, default_requests: 1}`；T10 `detail.rank_decay = {1.0, 0.9772, 0.0625}` |
| 静态质量 | 本轮 5 文件 `ruff` **All checks passed**；执行器与两个探针 **All checks passed**（并顺带清理 `health_backup_probe.py` 既有 I001） |
| 提交 | OpenLLM `ee0dba9`（`fix(v149)`，5 文件 `+327/-46`），显式路径、TDD 合规（RED 由既有用例指认、新增护栏同批） |

### 4U.4 关系与影响面

| 项 | 说明 |
|----|------|
| 方案 §4.3 | 「rag 入库分级」行补 **v1.18.0 执行侧实际判定**（原来只在网关决策层） |
| 方案 §7 | **T5 分两段**（段②无开关、进程内恒可判）；执行器判据仍为 **T1~T12**，但 T5 不再整条 `SKIP` |
| 方案 §10 | 新增**待登记项 10**：既有失败逐项分诊（含范围外 18 项的分类与归属建议） |
| 语义与影响面 | 执行层闸门**仅拦显式 `false`** ⇒ **既有调用方行为逐字不变**（缺省/`true` 一律照旧）；判据订正**只改判据与探针自身**，**生产排序语义零改动** |
| **范围外残留（如实登记，未改）** | 401 族 9 例（错误码契约域）／「模型不存在」错误码族 3 例／环境条件类 4 例（配置策略域，工作区 `.env` 与本地方案冲突）／`test_model_router_wiring.py` 2／`test_joinedload_asserts.py` 2／`test_conversations_api.py` 1 ⇒ **建议按域分别单独立项，本方案不代行修改** |
| 本方案内未闭环项 | **0 项**（§4.3 范围内的 1 项真实缺陷与 3 项自身判据缺陷**均已闭环**） |

---

## 4V. 判据保真度订正（T3 分段）＋ 开关开启值批准包 ＋ 配置面死开关护栏（2026-09-27）

### 4V.1 发现与取证

| 类别 | 取证 |
|------|------|
| **① 判据保真度缺陷（本轮新发现，与 T10④ 同源）** | §7 **T3** 原文＝「**启用 rerank 后** rag 条目的 score 单调性成立、低分条目被 `score_threshold` 过滤」。**取证**：执行器 `check_t3` **只在条目级传参**（`rerank=True` / `score_threshold=0.5`）下断言「透传 ＋ 过滤后条目数下降、score 单调」，**全程未触及全局开关**（`RAG_RERANK_ENABLED` 实测 **False**）却判 `PASS` ⇒ **判据被实现成「透传契约」却挂着「启用后生效」的名字**，会把「开关关着时口径正确」误读为「rerank 已达标可用」 |
| **② 判据前进的唯一前置未交付** | §7 的 T1/T2/T3/T5/T8 在**当前配置**下为 `SKIP`。`SKIP` 的语义是「**开关未开**」而非「能力不足」，而 §7 要求「**人工批准开关开启值后复跑**」⇒ **批准所需输入（建议开哪些键、什么值、依据、影响、回退）此前无交付物** |
| **③ 契约面「只写不读」类缺陷的推广面** | §4U 已确认 `save_if_valuable` **只写不读**（本方案范围内的真实缺陷）。同一口径推广到**配置面**：`config.py` 声明、`backend/` 内**无读取点**的键＝**死开关**（打开不产生行为，却被读作「该能力已接线」）。**首版脚本只扫 `app/`**，把读点在 **`backend/main.py`（lifespan 驱动清理循环）** 的 `WRITEBACK_CLEANUP_INTERVAL_SECONDS` **误报**为死开关（**审计口径缺陷，已如实登记并修正**） |

### 4V.2 实施内容

| 项 | 内容 |
|----|------|
| **(1) T3 拆两段（判据订正）** | ① **口径段（无开关，恒可判）**＝条目级参数**优先**于全局配置、`0`/非法值 ⇒ **不过滤**（解析为 `None`）、阈值过滤后**条目数下降**且 score **单调**；② **生效段（需开关）**＝`RAG_RERANK_ENABLED=True` 且 `RAG_SCORE_THRESHOLD>0` 时**未传条目参数**的检索其解析结果确实带上重排与阈值；**开关关闭时以临时置位证明能力**（口径同 T8），**真实检索侧重排质量**留 `detail.runtime_pending` |
| **(2) `--simulate` 置位集合扩展** | 由「`CONTEXT_BUDGET_ENABLED` ＋ `WRITEBACK_DECISION_ENABLED`」**扩为再含** `RAG_RERANK_ENABLED`/`RAG_SCORE_THRESHOLD` 与 `COMPONENT_DEPENDENCY_SCHEDULING_ENABLED` ⇒ **一次运行即可证明全部四处开关门控判据（T1/T2/T3/T5/T8）在开启态均达标** |
| **(3) 新增方案 §7.1「开关开启值建议（批准包）」** | **18 行**逐键给出「当前值 → 建议值 / 设计·实测依据 / 开启后影响面 / 回退方式」＋**批准粒度与门禁**：**建议本次开启** 6 项（含 `CONTEXT_REFINE_TRIGGER_ENABLED`＝**纯观测、零注入变化**）；**建议暂缓** 1 项（引用编号，依赖归因 A 消费方）；**依赖裁定不得代行** 3 项（§9 问题 1/3/5 与业务文案）；**明确维持关闭** 1 项（LLM 兜底分类器，开启前置未满足）；**复跑命令**随节给出（一条命令） |
| **(4) 配置面死开关结构护栏** | 新增 `tests/unit/test_cr149_config_keys_wired.py`（**4 例**）：受护栏前缀**全部配置键**须在 **`backend/` 全树**（排除 `tests/` 与 `config.py` 自身）**至少一个读取点**；「未接线集合」须**恰为已登记白名单**（**双向报警**）；白名单**逐项给出理由**；另以断言**锁定扫描覆盖 `backend/main.py`** 与**排除 `tests/`** |

### 4V.3 验证与证据

| 项 | 结果 |
|----|------|
| 执行器两态（订正后） | **当前配置** ⇒ `{PASS:5（T7/T9/T10/T11/T12）, SKIP:5（T1/T2/T3/T5/T8）, BLOCKED:2（T4/T6）, FAIL:0}`；`--simulate` ⇒ **`{PASS:10, SKIP:0, BLOCKED:2, FAIL:0}`** —— T3 由「误判 PASS」改为**如实 SKIP ＋ 能力已验证据**（**判据更正，非能力回退**） |
| 新增护栏 | `test_cr149_config_keys_wired.py` **4 例全绿**；**审计结论**：本方案范围 **48 键全部有读取点 ⇒ 未发现死开关**；唯一未接线键 `PROFILE_DRIFT_RECOMPUTE_INTERVAL` 属 **DT-214-305**（非本方案范围，按设计只交付驱动侧接口）⇒ 白名单并给理由 |
| **全量回归** | `cr149-t20-full.txt`：**21 failed / 3234 passed / 0 error**（256.99 s；较上轮 3230 增 **4** ＝本批护栏）；**与上一轮逐项 testid 归一化 `Compare-Object` 差异 0 项 ⇒ 零回归**；**连续三轮（`t18`/`t19`/`t20`）失败集逐项零差异** ⇒ 判据订正后**可复现** |
| 静态质量 | 本批 1 文件 `ruff` **All checks passed**；执行器与探针 `ruff` **All checks passed** |
| 提交 | OpenLLM `7efa6ec`（`test(v149)`，1 文件 `+121`），显式路径、TDD 合规 |

### 4V.4 关系与影响面

| 项 | 说明 |
|----|------|
| 方案 §7 | **T3 拆两段**（口径段恒可判 / 生效段需开关）；`--simulate` 置位集合扩展 |
| 方案 §7.1 | **新增「开关开启值建议（批准包）」** —— 使「人工批准开关值」成为**单步动作** |
| 方案 §10 | 新增**待登记项 11**（配置面死开关审计 ＋ 审计口径修正） |
| 语义与影响面 | **本批无生产代码改动**（执行器 / 文档 / 护栏均在**判据与工具侧**）⇒ **线上行为零变化**；T3 能力本身**未回退**（临时置位验证通过） |
| **待人工动作（唯一前置）** | 按 §7.1 批准「建议本次开启」6 项（**其中引用编号建议暂缓、3 项依赖 §9 裁定不得代行**）后，执行 `t_acceptance_runner.py` 一条命令复跑 ⇒ T1/T2/T3/T5/T8 由 `SKIP` 转 `PASS` |
| 本方案内未闭环项 | **0 项**（判据保真度缺陷**已闭环**；未实施项均为受阻项） |

---

## 4W. 判据残句子句归类（T3 的 `used_ratio` 子句）＋ 文档-实现漂移审计工具化（2026-09-27）

### 4W.1 发现与取证

| 类别 | 取证 |
|------|------|
| **① 判据「只覆盖原文子集而未声明」（本轮第三类判据保真度缺陷）** | §7 **T3** 原文有三条子句：score 单调 / 低分被阈值过滤（条目数下降）/ **`used_ratio` 不降**。前两类已由 v1.18.1 的分段判据覆盖；**第三条既未被判定、也未被声明为未覆盖**。**取证**：`used_ratio` 是**归因 A**（`app/edgerouter/orchestration/context_metrics.py::attribution_a()`）的指标，定义＝**回答引用了多少条注入片段**（`used/total`）；其自身 docstring 明确「判定规则…该规则保守（偏向认为被使用），因此按派单要求**只能纵向对比、不得作绝对值解读**」⇒ **取值依赖 LLM 回答内容** ⇒ 不能用构造回答做成**进程内确定性**判据 |
| **② 文档-实现漂移（历史真实教训，本轮工具化）** | 本仓曾出现：「正文声称配置键 `OPENLLM_PROFILE_LLM_REFINE` 已存在，实际全树无此键」（v1.9.0 更正）；「与 `evaluate.py` 同批的 `profile_refine` 源码**未随提交落库**，却被正文当作已交付」（`DEF-BE-148-029`）。二者均为**文档-实现漂移** —— 对本项目「单一事实源」原则而言是最危险的一类破坏；此前只能靠人工逐条复核，**不可复跑** |

### 4W.2 实施内容

| 项 | 内容 |
|----|------|
| **(1) T3 残句子句归类** | §7 T3 行**显式划出**「`used_ratio` 不降」子句，标注其归属＝**评测集**上做「rerank 开 / 关」对照（聚合比较），归 **§6 第三批**「评测集与验收判据扩展」 |
| **(2) 执行器新增 `detail.evaluation_pending`** | 凡判据原文中**进程内不可判**的子句（需真实回答 / 评测集 / 运行态）**显式列出**，**不以近似断言冒充覆盖**；首个用例即 T3 的 `used_ratio` 子句（T3 三态结果与 v1.18.1 一致，仅 detail 增该字段） |
| **(3) 新增审计工具 `check_doc_claims.py`** | 抽取方案正文**全部反引号引用的标识符**，在 **OpenLLM 全树**（`app/` ＋ `tests/` ＋ `main.py` ＋ `mock_services/`）与 **OpenBase 证据目录**中核对存在性；支持**定义式 / 声明式 / 文件名 / 子串**四类命中（覆盖「护栏文件名」与「f-string 内违规码」两类易漏形态）；支持 `--json` 落盘 |
| **(4) 审计方法学（两次修正，如实登记）** | **(a)** 首版**未区分「引用为存在」与「引用为缺失」**、也不扫 `tests/` ⇒ **误报 68 项**；**(b)** 改为「整行级跳过」后**反而过宽**（宽泛标记吞掉整行、审计失去意义）⇒ 最终定为「**邻近上下文（±80 字）＋ 精简标记集 ＋ 逐项可回溯的取证词白名单（各给理由）**」 |

### 4W.3 验证与证据

| 项 | 结果 |
|----|------|
| **文档-实现漂移审计（结论）** | `「引用为存在」214 项全部可核对 ⇒ **0 真实缺口**`；跳过 **50** 项（引用为缺失 / 族前缀 / 取证词 / 工件名片段）—— 即：**方案正文未发现「声称已实施而仓内查无此项」的条目** |
| 执行器两态 | **当前配置** ⇒ `{PASS:5（T7/T9/T10/T11/T12）, SKIP:5（T1/T2/T3/T5/T8）, BLOCKED:2（T4/T6）, FAIL:0}`；`--simulate` ⇒ `{PASS:10, SKIP:0, BLOCKED:2, FAIL:0}` —— 与 v1.18.1 **一致**，仅 T3 `detail` 增 `evaluation_pending` |
| 静态质量 | 执行器与新增审计工具 `ruff` **All checks passed** |
| 回归 | **本批无 OpenLLM 生产代码改动** ⇒ 线上行为零变化；全量回归未复跑（沿用 v1.18.1 的 `21 failed / 3234 passed` 三轮稳定基线） |
| 提交 | 仅 OpenBase 侧（执行器 ＋ 新增审计工具与结果 ＋ 两态结果 JSON ＋ 文档），**无 OpenLLM 代码提交** |

### 4W.4 关系与影响面

| 项 | 说明 |
|----|------|
| 方案 §7 | T3 行**显式归类** `used_ratio` 子句；执行器增 `detail.evaluation_pending` 口径 |
| 方案 §10 | 新增**待登记项 12**（文档-实现漂移审计工具，0 缺口） |
| 与 v1.18.0/v1.18.1 的关系 | 三批共同构成**判据保真度**整治：v1.18.0「判据随壁钟翻转」→ v1.18.1「判据挂名错位（未触开关却判 PASS）」→ v1.18.2「判据只覆盖原文子集而未声明」 |
| **待人工动作** | 方案 §7.1 批准包仍待人工批准（唯一前置）；本批**不改变**该结论 |
| 本方案内未闭环项 | **0 项**（判据残句子句**已归类**；未实施项均为受阻项：第三批评测集 / §9 裁定 / GPU / 运行态 DB） |

---

## 4X. 护栏覆盖与日志合规两项静态审计（均 0 真实缺口）＋ 裁定清单交付（2026-09-27）

### 4X.1 发现与取证

| 类别 | 取证 |
|------|------|
| **① 第四类保真度问题：已实施但可否静默回归？** | 前几批已整治三类（v1.18.0「判据随壁钟翻转」/ v1.18.1「判据挂名错位」/ v1.18.2「判据只覆盖原文子集」）；本轮补第四类 —— **方案声称已实施的模块/函数有没有护栏引用它？** 本仓历史 `profile_refine`「源码未落库却被正文当作已交付」（`DEF-BE-148-029`）正是「**无实现 ＋ 无护栏**」叠加的后果，故该问题是真实风险而非形式检查 |
| **② 观测不得以正文/凭据为代价（`AGENTS.md` §3）** | CR-149 各批新增了大量观测日志（回写三路 / 通道护栏 / 预算裁剪 / 画像维度 / 路由缓存 / 精炼触发）—— 需核对是否**违反**「禁止记录 密码/令牌/密钥/**完整请求体**/个人隐私」 |
| **③ 剩余未实施项的入口不可见** | 实施侧已按「不受阻者先行」推进到位，但「**哪项裁定解锁哪些实施项、我方已备好什么**」此前只在 §9/§10 分散陈述，人工裁定需自行拼接 ⇒ 裁定成本高 |

### 4X.2 实施内容

| 项 | 内容 |
|----|------|
| **(1) 护栏覆盖审计工具** | 新增 `doc/test/evidence/cr149/check_guard_coverage.py`（＋ `-result.json`）：抽取正文**代码符号**（`def`/`class`；**口径不含配置键**，因配置键多由 `load_budget_policy` 一类**行为级**护栏覆盖），判其在 `tests/` 与证据目录中**有无按名引用**；支持 `--json` |
| **(2) 日志合规审计工具** | 新增 `doc/test/evidence/cr149/cr149_log_hygiene.py`（＋ `-result.json`）：对 **15 个 CR-149 面文件**的 `logger.*` 调用做**括号配对**扫描，检出参数列表含**正文/凭据类字段名**者（并按长度/计数/标识等**安全衍生量**标记辅助判定）；支持 `--json` |
| **(3) 方案 §9.1「裁定清单与解锁关系」** | 新节：7 项裁定（Q1~Q7）逐项给出「我方已备好 / 裁定后**解锁**哪些实施项 / 裁定后我方动作」＋两类**非裁定型前置**（达标模型＋GPU；运行态 DB＋嵌入模型）＋明确 **§7.1 批准包与 §9.1 裁定是两条互相独立的人工门禁** |

### 4X.3 验证与证据

| 项 | 结果 |
|----|------|
| **护栏覆盖审计（结论）** | 91 个「声称已实施且仓内确有定义」的符号中 **74 有按名引用 / 17 无按名引用**；**逐项判定后 0 真实缺口** —— 17 项**全部属行为级覆盖**（逐项给出覆盖来源，见方案 §10 待登记项 13；`VectorStoreService`/`_sql_where` 属**本方案面之外**） |
| **日志合规审计（结论）** | 53 处 `logger.*` 调用中 **1 处命中且为误报**（`writeback.py:232` 的「updates」在**消息文案**里，实参只有 `user_id`）⇒ **0 违规** |
| 执行器两态 | 与 v1.55.0 **一致**（当前配置 `{PASS:5, SKIP:5, BLOCKED:2, FAIL:0}`；`--simulate` `{PASS:10, SKIP:0, BLOCKED:2, FAIL:0}`） |
| 静态质量 | 两个新工具 `ruff` **All checks passed** |
| 回归 | **本批无生产代码改动** ⇒ 线上行为零变化；全量回归**未复跑**（如实登记） |
| 过程修正（如实登记） | 编辑方案文件时误用 `Set-Content -Encoding UTF8`（PS5 会写入 **BOM**）⇒ 已检出并以 `UTF8Encoding($false)` **去除 BOM**（v1.18.3 与归档 v1.18.2 均已校验首字节为 `23 20`） |
| 提交 | 仅 OpenBase 侧（两个新增审计工具 ＋ 两份结果 JSON ＋ 方案 v1.18.3 ＋ 本文档），**无 OpenLLM 代码提交** |

### 4X.4 关系与影响面

| 项 | 说明 |
|----|------|
| 方案 §9.1 | **新增**：裁定清单与解锁关系（使裁定成为单步动作） |
| 方案 §10 | 新增**待登记项 13**（两项静态审计，均 0 缺口） |
| 四类保真度整治闭环 | v1.18.0 壁钟翻转 → v1.18.1 挂名错位 → v1.18.2 子集未声明 → **v1.18.3 无护栏（审计后 0 缺口）** |
| 边界说明（如实登记） | 两工具均为**静态**审计：前者不判**覆盖质量**、后者不判**是否为整值** ⇒ **不替代**行为级判据与人工复核 |
| **待人工动作（两条并列门禁）** | ① **§7.1 开关开启值批准**（决定 T1/T2/T3/T5/T8 由 `SKIP` 转 `PASS`，**不依赖任何裁定**）；② **§9.1 的 7 项裁定**（决定剩余未实施项能否开工）。两者**均不代行决定** |
| 本方案内未闭环项 | **0 项**（未实施项**全部**落在 §9.1 的 7 项裁定或两类外部条件上） |

---

## 4Y. §7.1 开关批准落地 ＋ §9 问题 1 裁定「接线」与落地（2026-09-27）

### 4Y.1 发现与取证

| 类别 | 取证 |
|------|------|
| **① §7.1 批准是四项 `SKIP` 的唯一前置（已人工批准）** | §7 的 T1/T2/T3/T5/T8 此前为 `SKIP`（含义＝**开关未开**，非能力不足）；执行器明确要求「人工批准开关开启值后复跑」⇒ 本轮人工批准「建议本次开启」6 类开关 |
| **② 批准后暴露的真实缺陷（本批新发现）** | `app/api/openllm_gateway.py::_builtin_rag_search()` 的分数阈值过滤对**缺失 `score`** 的条目取 `0.0` ⇒ 开启 `RAG_SCORE_THRESHOLD=0.15` 后这类条目被**静默丢弃**。**依据**：`app/services/rag_service.py` 多处按 `.get("score", 0.0)` 容缺 ⇒ 内置检索结果**确实可能不含 score**。**后果**：备通道（内置 RAG）可能「**接管成功、注入为空**」—— 正是方案 §4.1 明确警示的劣化形态；且与全项目 fail-open 口径相悖 |
| **③ 批准后暴露的 9 项用例「环境假设」** | 原断言依赖「开关默认关」或直接断言**生效值**（可被 `.env` 覆盖）⇒ 开关开启即失败：`test_component_dependency_scheduling` / `test_writeback_decision_gate` / `test_refine_trigger_and_guard`（断言生效值却名为「默认关闭」）、`test_context_budget` / `test_prompt_pipeline_shared_step`（以「未传 policy」隐含「不裁剪」）、`test_stream_auto_parity` / `test_writeback_three_roads` / `test_writeback_degradation`（只测 kb_id 绑定 / submit 回传 / 正常入队却被价值闸门拦截）、`test_auto_kb_resolution`（由 ② 的源码缺陷导致） |
| **④ Q1 接线的**前提**缺陷（本批新发现）** | `ChannelStateManager` 由 `_get_channel_manager()` **每次按当前配置构造** ⇒ ① 组件级失败**无法累计到阈值**、② 显式切到 A 后**下一请求即被重置回声明值**（**切换形同虚设**）。与本仓 `DT-148-015`（每请求新建 `ModelRouter` ⇒ **熔断永不打开**）**同类**；对写路径护栏无害（只需单主路径断言），故此前未被发现 |
| **⑤ 单例化暴露的 T11 条款确定性缺口** | 单例保留运行期切换结果后，「**配置非法 ⇒ 放行**」若仅由状态断言兜底，则**取决于既有状态**（保留 A 时会暂停回写）⇒ 该条款本意「**配置笔误不得静默停库**」不再有确定性保证（执行器 T11 一度 `FAIL`） |

### 4Y.2 实施内容

| 项 | 内容 |
|----|------|
| **(1) §7.1 批准落地** | 6 类开关（7 键）写入**工作区环境配置** `backend/.env`（**非仓库文件**，注释块内仅开关键、不落密钥）：`CONTEXT_BUDGET_ENABLED` / `CONTEXT_SYSTEM_PROMPT_ENABLED` / `RAG_RERANK_ENABLED` ＋ `RAG_SCORE_THRESHOLD=0.15` / `COMPONENT_DEPENDENCY_SCHEDULING_ENABLED` / `WRITEBACK_DECISION_ENABLED` / `CONTEXT_REFINE_TRIGGER_ENABLED`。**未批准项维持**：引用编号 / 窗口与输出预留 / LLM 兜底分类器 / `CHANNEL_*` 主备声明值 |
| **(2) 备通道阈值 fail-open 订正** | **有 `score` 者按阈值过滤、无 `score` 者保留**（**据实过滤，不据缺判低**），与全项目 fail-open 一致；护栏 `test_auto_kb_resolution.py::test_threshold_filters_scored_but_keeps_unscored`（3 态） |
| **(3) 9 项用例环境假设订正** | 按「**显式声明前提 / 断言声明默认**」：3 项改断言 `Settings.model_fields[...].default`（出厂默认，部署无关）＋ 2 项显式置关预算 ＋ 3 项显式置关价值闸门 ＋ 1 项由 (2) 自然通过；**未放宽任何断言** |
| **(4) 通道状态机进程级单例** | 新增 `channel.get_channel_state_manager()`（进程级 ＋ 偏好热更新 ＋ `reset_channel_state_manager()` 供测试隔离）；`_get_channel_manager()` 改取单例；**偏好变化 ⇒ 回落声明值 / 偏好未变 ⇒ 保留运行期切换**；配置非法 ⇒ WARN ＋ 保留现状（fail-open） |
| **(5) 触发责任链双源接线** | 源 1＝`_note_component_channel_health(component_run)` 挂**两路径共用**组件步骤之后（`degraded` 逐组件计失败；**`rag_source=builtin` 亦计失败**；全正常 ⇒ 清零）；源 2＝`_note_model_outcome()` 一并登记 `record_upstream_probe`（上游＝出站模型调用面）。**只登记不改通道**：自动回落由 `CHANNEL_AUTO_FAILOVER_ENABLED`（默认 False）门控 |
| **(6) 通道定性（§4.1 等待 Q1 的那一项）** | `/health` 增 **`channel` 段落**（偏好 / 主通道 / 单主路径 / `healthy_b` / 演练窗口 / 自动开关；异常降级 `unavailable`）＋ **`components.*.channel`**（外部三组件 `b`、内置 RAG 与 Ollama `a`） |
| **(7) T11 条款确定性订正** | `_writeback_channel_primary()` 增**配置层前置判定**：`channel_preference` 非法 ⇒ WARN ＋ **恒放行**（不再取决于既有状态） |

### 4Y.3 验证与证据

| 项 | 结果 |
|----|------|
| **批准后复跑执行器** | **当前配置** ⇒ **`{PASS:10（T1/T2/T3/T5/T7/T8/T9/T10/T11/T12）, SKIP:0, BLOCKED:2（T4/T6）, FAIL:0}`** —— **T1/T2/T3/T5/T8 由 `SKIP` 转 `PASS`**，与 `--simulate` 预测**一致** |
| 新增护栏 | `test_channel_wiring_health.py` **12 例**（单例身份 / 运行期切换跨请求存活 / 偏好热更新 / 非法配置 fail-open 保留 / 非法配置恒放行 / 组件降级计数 / 内置接管计数与归因留痕 / 健康轮清零 / 上游成败馈入 / 自动回落关态不切换且健康如实 / 开态达阈值切换 / 端点级 health 定性）＋ 备通道阈值 3 态 ＋ 预算开关正例 1 例；`test_writeback_channel_guard.py` 增 autouse 单例隔离 fixture（**仅隔离，不改断言**） |
| **全量回归（开关开启后）** | 首轮 `cr149-t21`：**30 failed / 3225 passed**（+9 ＝ 环境假设）；**订正后** `cr149-t22`：**21 failed / 3248 passed / 0 error**；与开关开启前基线 `cr149-t20` **逐项 testid 归一化 `Compare-Object`：差异 0 项 ⇒ 零回归** |
| 静态质量 | 本批 13 文件 `ruff` **All checks passed** |
| 开销实测与归因 | 单次装配 **20.8 → 44.2 ms（2.12×，复测 2.066）**；**受控 A/B**（装配密集子集 ON 11.39 s vs OFF 11.59 s）⇒ **开关不拖慢该子集**；全量墙钟 1859 s **不归因于开关**（同套件历史 256~889 s，主机负载波动）—— 仅「单次装配 2.12×」为可归因事实，已列方案 §8 风险行 |
| 提交 | OpenLLM `4789c6c`（`feat(v149)`，13 文件 `+537/-13`） |

### 4Y.4 关系与影响面

| 项 | 说明 |
|----|------|
| 方案 §7.1 | 增加「**已批准并落地**」块（含未批准项与开启代价） |
| 方案 §9 问题 1 | **已裁定为「接线」**；§4.1 增**【实施状态（v1.19.0）】**表；§10 待登记项 1 更新为「部分实施」 |
| 方案 §3.2 / §8 | 阈值 fail-open 订正；新增「开启预算后单次装配耗时上升」风险行 |
| 方案 §10 | 新增**待登记项 14**（全量墙钟可归因性，**条件立项**） |
| **残留（如实登记，不臆造）** | **通道裁决接入取数层（逐组件路由）**需 A 侧对 `memory` / `dps` 具备等价能力（当前仅 `rag` 有内置回退）⇒ 取决于「内置 RAG 种子底座」（运行态 DB ＋ 嵌入模型）与 §9 问题 4；**「写路径 A/B 等价」矩阵项**当前口径＝「A 接管期间写暂停」（T11） |
| 语义与影响面 | **生产配置首次真正启用本方案能力**（预算裁剪 / system 段 / 检索侧重排与阈值 / 依赖图调度 / 写侧价值闸门 / 精炼触发观测）⇒ **线上行为按批准范围变化**；通道侧「只登记不改通道」（自动回落默认关）⇒ **通道切换仍为人工显式为主** |
| 本方案内未闭环项 | **未实施项均落在 §9 问题 2~7 裁定或两类外部条件（GPU 模型达标 / 运行态 DB）上**；**范围内无「已发现且可立即实施」的缺陷** |

---

## 4Z. §9 问题 3（预算目标）裁定「按真实窗口」并落地（2026-09-27）

### 4Z.1 发现与取证

| 类别 | 取证 |
|------|------|
| **① 裁定问题（架构上限 vs 服务侧可用量）** | 预算基准此前有三套候选口径混用：知识库样本宣称的 **4096**、模型表 `default`＝**128000**（架构上限）、配置 `CONTEXT_MODEL_WINDOW_TOKENS`＝**8192**。**架构上限 ≠ 服务侧可用量** —— 本地部署实际可用上下文由服务侧决定；按 128000 分配配额会在服务侧被**截断** ⇒ **静默丢内容**（方案 §4.1/§8 反复警示的劣化形态） |
| **② 本批新发现的真实缺陷（同源口径分叉）** | 装配预算 `prompt_pipeline.load_budget_policy` 与历史段预算 `openllm_gateway._history_budget_tokens` **各自解析窗口且兜底不同**：装配恒用配置 **8192**，历史段对**未识别模型**取 `default`＝**128000** ⇒ **同一请求两套窗口（相差 15.6 倍）**。**实测**：部署模型 `qwen3:0.6b` 在模型表**零命中** ⇒ 历史段预算 **(128000−1024)×0.2 ＝ 25,395**，而装配预算按 8192 ⇒ 历史段对本地小模型属**超窗配置** |
| **③ 同批新发现的「声明未接线」** | `build_prompt` 支持 `model=` 参数（用于按真实窗口解析），但**两条路径的组装都未传** ⇒ 设计承诺「模型可识别时优先取真实窗口」在**生产路径永不生效**（与第 48 批的「无护栏/未接线」同类） |
| **④ 两张模型窗口表未对齐（不影响裁定结论）** | `app/core/supported_models.py` 声明 `qwen3:*` `context_window=131072`，而 `MODEL_CONTEXT_LIMITS` **无 qwen3 族键** ⇒ `resolve_model_context_key("qwen3:0.6b")` 零命中 |

### 4Z.2 实施内容

| 项 | 内容 |
|----|------|
| **(1) 统一窗口解析入口** | 新增 `context_manager.resolve_effective_window_tokens(model)`：**可识别** ⇒ `min(声明窗口, 部署窗口)`（来源 `registry:<key>` / `deployment_cap:<key>`）；**未识别** ⇒ **部署窗口兜底**（`deployment_fallback`，**明确不取** 128000）；**部署窗口**由 `CONTEXT_MODEL_WINDOW_TOKENS` 声明；解析异常 ⇒ `config_fallback`（fail-open） |
| **(2) 同源调用** | `load_budget_policy(model)` 与 `_history_budget_tokens(model, reserve)` **改走同一入口** ⇒ 消除「同一请求两套窗口」 |
| **(3) 模型真被传入（接线）** | `PipelineExecutor`（同步/共用组装步骤）与**流式端点**均传入 `pipeline` 的 llm 条目 `params.model`（**同源**，避免一侧真实窗口、一侧部署兜底） |
| **(4) 绝对配额表落文档** | 方案 §3.3 增「窗口基准与绝对配额」表（8192 / 4096 / 32768 三档）与「为何不用 4096 / 不用架构上限」的判据式说明 |

### 4Z.3 验证与证据

| 项 | 结果 |
|----|------|
| **裁定口径实测** | 探针 `budget_window_probe.py`：8192 ⇒ memory **2007** / rag **2652** / history **1361**（和 6736 ≤ 可分配 7168）；`llama-2-7b`（声明 4096）⇒ 860 / 1136 / 583；`gpt-4-turbo`（声明 128000）⇒ **被部署窗口截为 8192**；完全未识别 ⇒ 8192（**非 128000**） |
| **同源修复实测** | `_history_budget_tokens("qwen3:0.6b")` 由 **25,395 → 1,433**（＝装配同窗口），未识别模型不再超窗 |
| 新增护栏 | `test_budget_window_basis.py` **11 例**（三口径 / 显式部署窗口 / 装配与历史段同源 / `build_prompt(model=...)` 配额随窗口变化 / 两路径同源传参的源码级断言） |
| **全量回归** | `cr149-t23`：**21 failed / 3259 passed / 0 error**（281.62 s；较上批 +11 ＝ 本批护栏）；与 `cr149-t22` **逐项 testid 归一化 `Compare-Object` 差异 0 项 ⇒ 零回归** |
| 静态质量 | 5 文件 `ruff` 与基线（`git stash` 对照）**逐规则计数一致（70 → 70）** ⇒ **未引入新增 lint** |
| 执行器两态 | **`{PASS:10（T1/T2/T3/T5/T7/T8/T9/T10/T11/T12）, SKIP:0, BLOCKED:2, FAIL:0}`**（不变） |
| 旁证（墙钟归因） | 同套件墙钟由 v1.57.0 的 **1859 s** 回到 **281.62 s** ⇒ 进一步佐证上批异常属**主机负载**，非开关 |
| 提交 | OpenLLM `a825c2c`（`feat(v149)`，5 文件 `+226/-21`） |

### 4Z.4 关系与影响面

| 项 | 说明 |
|----|------|
| 方案 §3.3 | 增「窗口基准与绝对配额（§9 问题 3 已裁定）」小节与三档配额表 |
| 方案 §9 问题 3 | **已裁定**（按真实窗口；不用 4096、不用架构上限） |
| 方案 §10 | **待登记项 14**：模型窗口两张表未对齐（**建议立项**，不影响本轮裁定结论） |
| 语义与影响面 | **本工作区配额不变**（`qwen3:0.6b` ⇒ 8192 兜底）；**历史段预算收敛**（25,395 → 1,433）；**声明窗口更小的模型**将按其真实窗口配额 ⇒ 「按真实窗口」在生产路径**真正生效** |
| 本方案内未闭环项 | **0 项**（未实施项均落在 §9 问题 2/4/5/6/7 裁定或两类外部条件上） |

---

## 4AA. §9 问题 4（记忆写入语义）裁定「默认 verbatim」并落地（2026-09-27）

### 4AA.1 发现与取证

| 类别 | 取证 |
|------|------|
| **① 待裁定问题的实质** | §4.3 明文把「**是否允许把整轮全文改为提炼结论/摘要**」列为待裁定项（**载荷形态**），并明确 `WRITEBACK_DECISION_ENABLED` **只决定「是否沉淀」、不改写载荷** ⇒ 二者是**两个独立问题**，不得代行 |
| **② 粒度变化不可逆** | 记忆一旦以摘要形态入库，后续**检索召回粒度**与**归因 A**（`context_metrics.attribution_a()` 的 `used/total`）的**片段索引**随之改变；历史轮次**无法还原**为整轮全文 ⇒ 属**不可回收**的语义变更 |
| **③ 前置门槛未达** | 生成式精炼的模型档**尚未过 §5.6 门槛**（本地 ≤1B：事实保留 **0.17~0.67 < 0.90**；筛选 F1 最好 **0.697 < 0.70**）⇒ 现阶段改写载荷＝**在无达标模型时引入失真** |
| **④ 与既有原则一致性** | 既有写侧价值闸门（§4.3）只做「**是否沉淀**」的**判定**、**不改写任何载荷**；把载荷形态定义为「**默认不改**」与该原则同向 |

### 4AA.2 实施内容

| 项 | 内容 |
|----|------|
| **(1) 新增载荷形态模块** | `app/edgerouter/orchestration/memory_payload.py`（**纯函数、无 IO、无全局可变依赖**）：`resolve_payload_mode()`（**非法值 ⇒ 回退 `verbatim` ＋ WARN**）＋ `build_memory_payload(query, response, *, summarizer=None, mode=None) -> (fields, meta)` |
| **(2) 提炼器进程级注入** | `register_memory_summarizer(fn)` / `get_memory_summarizer()` / `reset_memory_summarizer()`（与既有 `refine_fn` **同形态**；**当前未接线** ⇒ 线上不可能产生摘要） |
| **(3) 三配置键** | `WRITEBACK_MEMORY_PAYLOAD_MODE`（默认 **`verbatim`**）/ `WRITEBACK_SUMMARY_MIN_CHARS`（默认 **40**）/ `WRITEBACK_SUMMARY_KEEP_ORIGINAL`（默认 **True**） |
| **(4) 网关按路接线** | `_build_writeback_callback._make` **仅在 `target == "memory"`** 时装配载荷；`verbatim` 下返回字段与既有 kwargs **同值**、**不新增任何 payload 键**（`payload_meta` 仅摘要**真正生效**时附上）⇒ **默认路径零改动** |
| **(5) 五条护栏** | **未注入提炼器 / 提炼器异常 / 摘要为空 / 摘要过短 / 摘要未短于原文（无压缩收益）** ⇒ 任一不满足**回退 `verbatim`**；生效时 `memory_type="summary"` 并按开关把原文写 `metadata.summary_origin_response`（**可回溯**） |

### 4AA.3 验证与证据

| 项 | 结果 |
|----|------|
| 新增护栏 | `tests/unit/test_memory_payload_mode.py` **12 例全绿**（声明式默认断言 `Settings.model_fields[...].default`、`verbatim` 零改动、非法值 fail-safe ＋ WARN、五条护栏逐条、生效保留/不保留原文、回调级「默认载荷不新增键」） |
| 探针（含自检） | `doc/test/evidence/cr149/memory_payload_probe.py`（＋ `-result.json`）**9 例判定表**；**首轮暴露取证缺陷**：⑦/⑧ 名为「summary 生效」却实测 `applied=false`（样例摘要 **27 字** < 默认门槛 **40** ⇒ 回退）⇒ 加 `expect_applied` / `ok` 与**结尾自检**（`40 ≤ 样例摘要 < 200`、逐例期望一致，不符即 `FAIL` 且**返回码非 0**）；修后 **`probe self-check: PASS`（9/9 一致）** |
| **全量回归** | `cr149-t24`：**22 failed / 3270 passed / 0 error**（**2368.83 s**）；与 `cr149-t23`（21 failed / 3259 passed）**逐项 testid 归一化 `Compare-Object`**：**新增失败 1 项 / 已消失 0 项** |
| **该新增失败的受控实验（决定性）** | 失败例＝`test_perf_batch_concurrency.py::test_pacer_does_not_serialize_requests`：**(a)** 断言**墙钟**（`wall < 0.05×4 = 0.2 s`）⇒ 对主机负载敏感；**(b)** `git stash` 前后对照 —— **本批改动在位** `5 passed / 1.07 s`、**改动全部 stash** `5 passed / 1.04 s` ⇒ **两态均通过**；**(c)** 失败时**同文件 124.29 s**（`wall = 0.2919 s`）vs 空闲态 **≈1.05 s**（**约 118× 差**）⇒ 该轮存在**并行/主机争用**；**(d)** 本批改动**不含** `pacer`/限流/并发路径 ⇒ **判为环境 flaky，零回归** |
| 静态质量 | 本批 4 文件 `ruff` **All checks passed**（0 告警） |
| 执行器 | 两态 **`{PASS:10, SKIP:0, BLOCKED:2, FAIL:0}`**（无开关变化，与上批一致） |
| 提交 | OpenLLM **`dcda043`**（`feat(v149)`，4 文件 `+386/-1`）；**另补交** `test_context_rank_selection.py`（v1.18.0 判据同源基准订正此前**仅改盘未入库**）**`3a034aa`**（1 文件，12 例全绿） |

### 4AA.4 关系与影响面

| 项 | 说明 |
|----|------|
| 方案 §4.3 | 增「**载荷形态（§9 问题 4 已裁定）**」小节：三键表 ＋ 五条护栏 ＋ 两步启用 ＋ 探针自检 |
| 方案 §9 问题 4 / §9.1 Q4 | **已裁定**（默认 `verbatim`；摘要可选、可配置、可回退、当前不启用）；解锁条件＝**模型过 §5.6 门槛**后「注入提炼器 ＋ 置开关」两步 |
| 语义与影响面 | **线上默认路径逐字不变**（不新增 payload 键；摘要需**两步**才可能生效）；摘要形态启用后**须补载荷级回归**（召回粒度 ＋ 归因 A 片段索引） |
| **同批文档一致性缺陷（已修）** | OpenLLM 开发记录报告**文档头版本滞留 `v1.32.1`** 而修订历史已至 `v1.39.0`（**7 版漂移**）⇒ 已同步至 **v1.40.0**；该漂移**不在**既有「文档-实现漂移审计」覆盖内（只核符号存在性）⇒ 方案 §10 **待登记项 16**（建议把「文档头版本 == 修订历史末行版本」纳入一致性检查） |
| **工作区遗留（观察，未代行）** | `backend/tests/unit/test_billing_v2_api.py` 存在**非本批**未提交改动（`DT-213-003` 计费 `time_range` 用例）⇒ **不属本方案面**，**本批未提交**，留待其归属工作流处置（**如实登记，不代行**） |
| 本方案内未闭环项 | **0 项**（未实施项全部落在 §9 问题 2/5/6/7 裁定或两类外部条件上） |

---

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-21 | AT-OpenBase-Test / DO-OpenBase-Ops | 初始创建：登记 **DEF-BE-148-001（P1，环境/工具链）** 与 **DEF-BE-148-002（P2，环境/依赖）**；§1.1 提出 `.pylib` 处置方案 A/B/C（建议 B）；§2 登记 CR-148-001~003；§3 归集检查（建议不立债）；§4 结论「两项均未改动产品代码、不影响 v1.4.8 产品与门禁判定」。状态 [Review] |
| **v1.1.0** | **2026-09-21** | **AT-OpenBase-Test / DO-OpenBase-Ops** | **方案 A 暂缓 + 两项缺陷口径更正**。① **§1.1 新增「裁定：不可实施」**——补充取证发现三条独立推翻理由：A 会**打断上游 Python 3.13 `.venv` 的依赖覆盖层**（`.pylib` 原生扩展实测 **cp313×24 / cp310×3**，系 `pip install --target` 为 3.13 构建）、缺陷**上游已编号 `CLR-214-004`（P2）**且已有对策、本机**权威启动路径不加载 `.pylib`**故对 Step 4 零收益；**执行动作已暂缓，仅生成 dry-run 清单（23 项 / 26.2 MB），未删除任何文件**；给出替代处置建议 1/2/3（推荐「本仓零改动」）。② **`DEF-BE-148-001` 降级 P1 → P2** 并改记为**跨仓引用项**（同源 `CLR-214-004`），根因更正为「`.pylib` 为 3.13 `.venv` 覆盖层、cp313/cp310 混编」；补入上游 5 处原文依据与权威启动定义（`service-orchestrator.ps1:105-110`）。③ **`DEF-BE-148-002` 降级 P2 → P3 并更正为非缺陷**——`8001` 权威实例 `openllm/v1/health` 返回 **`openrag: ok`（1750ms）**，推翻「上游 401」判据，更正为**我方临时实例缺编排器 `Env`** 造成的测试环境配置缺口。④ 新增 **CR-148-004**（实例须按编排器定义含 `Env` 启动；固化进测试计划前置）。⑤ §3 归集检查更新为「**无 P1+，无需归集**」，总表 **v0.6.0 未写入**。⑥ §4 结论改写为「**方案 A 未执行、无阻塞、Step 4 阻塞仍仅为 `D3`**」。**文档版本 v1.0.0 → v1.1.0**（发现问题：修订号递增）。状态 [Review] |
| **v1.2.0** | **2026-09-21** | **AT-OpenBase-Test / DO-OpenBase-Ops** | **CR-148-001 裁定登记（人工批准，批准人＝用户）→ 采纳建议 1「本仓零改动」**。① 新增 **§1.1.1 裁定结论**（裁定对象／日期／执行结果／生效范围／我方承诺事项／后续动作 7 项）；② §1.1 标题由「已暂缓」改为「**最终裁定：不可实施 → 采纳「本仓零改动」**」；③ §1 中 `DEF-BE-148-001` 的「修复状态」改写为「**本仓零改动（人工批准）** + 转为纯跨仓引用项」；④ §2 `CR-148-001` 状态 **待人工裁定 → 已裁定（人工批准）**；⑤ §4 结论以「**裁定已落地**」替换原「待人工裁定」，并明确本记录**到此为终态**、本仓**无未闭环环境动作**，唯一遗留为**外部条件 `D3` 凭据**；⑥ 状态由 [Review] 升 **[Approved]**，文档版本 **v1.1.0 → v1.2.0**（人工批准：次版本递增）。**执行核实**：本仓**零改动**——`.pylib` 0 删除（5,860 文件与 94 个目标包全部在位，`git status` 无删除项），OpenLLM 工作树原状，隔离目录未创建 |
| **v1.3.0** | **2026-09-21** | **AT-OpenBase-Test** | **运行时用例第二轮执行 + 新发现 P1 产品缺陷**。① **环境与凭据阻塞解除**：按编排器定义起 v1.4.8 实例（8041），并补充注入 `backend/.env` 缺失的 `OPENRAG_API_KEY` / `OPENMEMORY_API_KEY`（源自仓库根 `.env.shared-infra`）→ `/openllm/v1/health` **三上游全 ok**（实证 `CR-148-004`：`openrag 401` 系未带 `Env` 的假故障）；注册探测账号 + 登录取得 JWT → 原 401 端点转 **200**，**`D3` 凭据在本地已自解**。② **执行 11 例：6 通过 / 5 未通过**（通过：回执按会话隔离 ×2、路由 404 鉴别力、网关/业务 401 鉴别力、指标导出会话筛选回显）。③ **新增 `DEF-BE-148-003`（P1，产品功能缺陷）**：会话标识未落库——`conversation_service.py` 第 54/212 行用**非映射关键字** `metadata=`（模型映射为 `metadata_`）→ 被 SQLAlchemy 静默忽略，列恒 `{}`；**DB 直查 4 行 metadata 全空 + 最小实验 `m.metadata_ == merged` 为 False**；影响＝会话轴筛选恒为空、**核心需求「会话标识贯穿」落库链失效**，并连带所有调用方 metadata 长期丢弃；全仓其余写入点均用 `metadata_=`，**仅此两处错**。④ 另 2 项未通过根因登记为**跨系统集成前置**（OpenLLM 出站 `X-API-Key` vs OpenMemory `/api/v1/remember` 要求 Bearer JWT）与**环境数据前置**（直连客户端无租户身份，已以单行 UPDATE 绑定既有租户后解除，建会话转 **201**）。⑤ 新增 **`CR-148-005`**（`DEF-BE-148-003` 处置待裁定，**建议回退 Step 3 修复**）；§3 归集检查更新为「**新增 1 项 P1，处置＝回退 Step 3 而非立债**」。⑥ 状态 [Approved] → **[Review]**，文档版本 **v1.2.0 → v1.3.0**（新增功能/发现：次版本递增）。证据：`doc/test/evidence/v148/step4-round1-execution-20260921.txt` **§十三** |
| **v1.4.0** | **2026-09-21** | **AD-OpenBase-Dev / AT-OpenBase-Test** | **`DEF-BE-148-003` 修复与复测（回退 Step 3 执行，人工批准方案①）**。① **RED**：新增护栏 `tests/unit/test_conversation_metadata_mapping.py`（**用真实模型**断言映射属性，不 patch 模型）→ **3 failed**；② **GREEN**：`conversation_service.py` 第 54/212 行 `metadata=` → **`metadata_=`**；③ **连带项（同一缺陷族）**：`schemas/conversation.py` 抽出 `_orm_values_with_metadata()` 共用，并为 **`MessageResponse` 补上缺失的 `extract_metadata` 前置校验器**（该缺失由修复暴露：修复前影子属性恰为 dict 使序列化「碰巧通过」，修复后立即 500）；④ 印证「单元未拦住」的原因——既有 3 例断言的是**服务传参名**（`captured["metadata"]`）而非映射属性，属**错误契约**，已更正为 `metadata_` 并注明 ORM 真实性由新护栏把关；⑤ 精确回归 **37 passed / 0 failed**；ruff 新护栏 `All checks passed`、两被改文件 34 处告警**均不在改动行**（既有 typing/导入序问题）；⑥ **运行时复测 8/8 通过**（发送消息 **500 → 201**；按会话筛选 **0 → 2 / 1 条**；缺省不筛选 3 条；DB 3 行 `metadata` 均含 `session_id`/`session_scope`）；⑦ `CR-148-005` 状态 **待裁定 → 已裁定（方案①）**，`DEF-BE-148-003` 修复状态改为 **已修复**、复测结果 **复测通过**；状态 [Review] 保持，文档版本 **v1.3.0 → v1.4.0**。证据：证据文件 **§十四**；**改动尚未提交**（建议按 `fix` 提交并引用 `DEF-BE-148-003`） |
| **v1.5.0** | **2026-09-21** | **AT-OpenBase-Test / AD-OpenBase-Dev** | **回写链路鉴权缺口修复 + TT-018 取证（跨系统集成，本仓零代码改动）**。① 新增 **`CR-148-006`** 登记 `CR-148-005` 之后的第二项裁定：OpenMemory 强制 Bearer 而 OpenLLM 只发 `X-API-Key` 的**跨系统鉴权形态不兼容**，处置＝OpenLLM 出站并存附加共享密钥 HS256 服务账号 JWT（+ `OPENMEMORY_TIMEOUT` 5s→30s）；② **TT-v1.4.8-018「重启不丢写」转为已取证**（async 提交 → 队列 26→28 行 → 重启后 28 行不变、id 408/409 仍在且续投递 memory→`done`；`receipts` 查询 `total:2`）→ **两项硬判据中仅「两路径一致性」仍缺运行期证据**；③ 三项澄清：sync **不入队**（回执查询为空属预期）、profile 路失败＝**直连客户端缺四维身份**（非本仓代码缺陷）、`retry_count=4` **未超标**（撤回上轮怀疑）；④ 状态 [Review] 保持，文档版本 **v1.4.0 → v1.5.0**。依据：《OpenLLM DevLogReport》**v1.3.0**（第 14 批）、证据文件 **§十五~§十七**、《测试报告-v1.4.8》**v1.9.0** |
| **v1.6.0** | **2026-09-21** | **AT-OpenBase-Test / AD-OpenBase-Dev** | **新增 `CR-148-007`：计费落库缺陷登记 + 2 项派生问题定性**。① **`DEF-BE-148-004`（P1）**：LLM 调用成功但**计费落库失败**（`usage_records.organization_id` NOT NULL 违约）导致成功请求被报 500 —— 实证 token 已消耗（4598）却未记账，响应语义污染 + 计费一致性风险；已给出两条修复建议（失败不改写业务响应 + `organization_id` 缺失兜底）。② **`DEF-BE-148-005`（P2，待确认）**：metrics 的 `model` 字段**两路径填充不一致**（同步 `null`、流式为模型名），影响按模型维度归集。③ **非缺陷定性**：`counted=false` / `segment_tokens` 全 0 属**设计语义**（`prompt_pipeline.py` 定义「未提供计数器时为 False」），即**未接线**；故「缓存命中」判据项**无有效观测值**而非不一致。④ 文档版本 **v1.5.0 → v1.6.0**，状态 [Review]。依据：证据文件 **§十九** |
| **v1.7.0** | **2026-09-21** | **AD-OpenBase-Dev / AT-OpenBase-Test** | **`DEF-BE-148-004`（P1）修复并运行时验证通过 + 代码提交落库**。① **TDD 修复**：新增护栏 `test_billing_usage_resilience.py`（3 例）→ **RED 3 failed**；实现 = `billing_service` 组织缺失守卫（记 WARN 并跳过必然违约插入）+ 新增 **`record_usage_safely`**（异常 → **`db.rollback()`** → ERROR 日志 → 返回 None，回滚为必需项）+ `openllm_gateway` 调用点改 `_safely`；**GREEN 24 passed / 0 failed**（含既有 21 例精确回归）；② **运行时验证 PASS**：实例重启加载修复后，无组织账号 `v148-noorg` 请求 chat 由 **500 → 200**（`usage 44+362=406`），且服务端出现守卫 WARN「计费跳过：缺少组织标识…本次用量未落库」—— **两条合起来才排除「异常被吞后碰巧通过」**；③ **残留明确**：「已消耗未记账」**未消除**，由静默转为**可观测告警**，兜底策略（落默认组织 or 告警补偿）**待裁定**；④ **未完成**：全量回归受阻于既有 `.pylib` 环境缺陷（根 `tests/conftest.py` 加载即 `ImportError: DLL load failed while importing _rust`），本轮仅完成精确回归 —— 如实登记，不宣称全量通过；⑤ **代码提交**：`feature/s4-identity-channel-b` 分支 **`ca45639`**（10 文件 `+1051/-109`，含 v1.4.8 主体改动与三项修复）与 **`02be4ea`**（14 个 v1.4.8 测试文件），均按**显式路径** `git add`，未用 `git add -A`；⑥ **口径更正**：撤回上轮「`.env.shared-infra` 未被 gitignore 属安全隐患」的判断 —— 实测 `.gitignore:41` 为 `!.env.shared-infra`（**显式取反，项目有意纳入版本管理**），故未添加忽略规则；⑦ 文档版本 **v1.6.0 → v1.7.0**，状态 [Review]。依据：证据文件 **§二十一**、《OpenLLM DevLogReport》**v1.4.0**（第 15 批） |
| **v1.8.0** | **2026-09-21** | **AT-OpenBase-Test / AD-OpenBase-Dev** | **新增 `CR-148-008`：三项缺陷登记 + 两处假设撤回 + 一处操作责任如实登记**。① **三项新缺陷**：**`DEF-BE-148-006`（P1）** 两路径模型解析机制不一致（流式不经路由治理，对照实验实证）；**`DEF-BE-148-007`（P1，安全）** 回执查询跨用户越权；**`DEF-BE-148-008`（P2）** 错误响应缺 `detail`。② **撤回假设一**：此前推断「流式失败＝计费调用点未修（8 处漏改）」—— **已由对照实验证伪**（容错下沉并重启后，流式失败签名**完全不变**）。③ **撤回假设二**：此前把 `.env` 的 `DEFAULT_LLM_MODEL` 回滚为 `qwen3:0.6b`，理由是「auto 模式下该值不生效」—— 该判断**仅对同步路径成立**，对流式**不成立**。④ **如实登记操作责任**：**该回滚是流式失败的直接触发原因**（回滚→流式指向不可用的本地 Ollama→3/3 失败；改回 `deepseek-v4-flash`→3/3 恢复），已由对照实验证实；当前 `.env` 已改回 `deepseek-v4-flash` 并**建议作为环境前置保留**。⑤ **TT-v1.4.8-007 由 FAIL 转通过**（`routing → chunk×N → done` 序列完整，`done` 终止事件已补齐）；**TT-v1.4.8-014 仍 FAIL**。⑥ 文档版本 **v1.7.0 → v1.8.0**，状态 [Review]。依据：待补证据 **§二十二**；本轮已由《测试报告-v1.4.8》§8.1 与 `CR-148-008` 留痕 |
| **v1.9.0** | **2026-09-21** | **AD-OpenBase-Dev / AT-OpenBase-Test** | **分次交付一/二：`DEF-BE-148-007` 与 `DEF-BE-148-006` 两项 P1 修复并验证通过**。① **交付一（越权，方案 B）**：`list_rows` 新增 `user_id` 筛选（表无该列，用 `json_extract(payload_json,'$.user_id')`）+ 端点加 `identity` 依赖 + **无身份 fail-closed 返回空**；**双对照验证**：账号 A 查自有回执 `total=1`（不误伤）、**账号 B 查同一会话 `total=0`**（修复前 1 条）→ PASS；已如实记录**本次未写单测**（以运行时双账号对照替代，与 TDD 纪律有偏差）与 **fail-closed 隐藏历史行**的副作用。② **交付二（两路径解析）**：先以临时调试日志**观测** `llm_comp={"component":"llm","model":"qwen3:0.6b"}` → 确认流式 `pipeline[-1]["model"]` 被填为**具体默认值而非 `"auto"`**，故原判据 `model == "auto"` **恒假**；改判据为**「调用方是否显式指定 model」**并执行与同步同一条 `_route_model_auto` 改写；**移除 TEMP-DEBUG**；附带修正 `routing_trace` 模型字段取**路由后**值。**原失败条件回归（未改任何配置）**：流式 **3/3 失败 → 3/3 成功**（`routing → chunk×N → done`）→ PASS。③ **两处连带结论**：**撤回**「须保留 `DEFAULT_LLM_MODEL=deepseek-v4-flash` 作环境前置」；流式与同步**分叉点消除**。④ **过程复盘**：同一缺陷**误判两次**（第二次写出永不执行的死代码），第三次**先观测后一次定位** —— 作为"先观测、再断因"的反面教材留痕。⑤ `DEF-BE-148-008` 仍未修复。⑥ 文档版本 **v1.8.0 → v1.9.0**，状态 [Review]。依据：证据文件 **§二十三** |
| **v1.10.0** | **2026-09-21** | **AD-OpenBase-Dev / AT-OpenBase-Test** | **分次交付三：`DEF-BE-148-008` 修复并验证通过 + 四项修复代码入库 + 提交归属核对**。① **修复**：`_error_response` 补 **`detail`** 字段（`GatewayError` 未携带时回退 `message`，保证**始终存在**，对齐错误码规范与 TT-v1.4.8-014）；`/writeback/receipts` 未授权分支由 `200 + note` 改为 **`401`**，使 **fail-closed 与响应契约同时满足**。② **验证（PASS）**：未授权错误体**四字段齐备**（`{code,message,detail,request_id}`）、语义为 **401**；并做**越权回归**确认交付一的隔离未被破坏（账号 A `total=2` / 账号 B 同一会话 `total=0`）。**残留**：该端点 `request_id` 为**空串**（字段存在未生成），建议纳入 TT-014 补齐。③ **代码入库**：`feature/s4-identity-channel-b` 提交 **`245b70b`**（4 文件 `+202/-93`），按**显式路径** `git add`、未用 `git add -A`。④ **提交归属核对（方案 B 登记）**：`writeback_queue.py` diff 为 **80 增 / 0 删**，**0 删除**证明基线中**不存在 `list_rows`** —— 即**约 65 行的 `list_rows` 为更早批次未提交的实现，随本次首次入库**（第二块 +15 行同理）。**定性非有害**（真实的 v1.4.8 交付物），但**提交信息未覆盖**，**与 `ca45639` 同型**；按人工选定的**方案 B 不改写历史**，改由本记录与证据 **§二十四** 记载该提交真实范围为「越权修复 **+ 首次入库回执查询实现**」。⑤ 三项缺陷（`DEF-BE-148-006`/`007`/`008`）**至此全部闭环**。⑥ 文档版本 **v1.9.0 → v1.10.0**，状态 [Review]。依据：证据文件 **§二十四** |
| **v1.11.0** | **2026-09-21** | **AT-OpenBase-Test / DO-OpenBase-Dev** | **三项未提交内容处置（CR-148-009）+ 顺带发现登记（CR-148-010）**。① **先观测后处置**：核实三项对象的实测事实——`.env.shared-infra` **被跟踪**且 `git log` 各版本 `OPENRAG_API_KEY` 赋值长度**恒为 0（空值模板）**，工作副本却含真实凭据与 **v1.4.8 共享 JWT 签名密钥**（**提交即首次带密入库**）；`conftest.py` 为 pgAdmin/`.pylib` 路径优先级修复（`+12/-2`）；211 项 `D` **全部位于 `__pycache__`** 且 `.gitignore` 已覆盖。② **处置 1（密钥不落 git）**：依 `AGENTS.md` §6 与该文件内「勿落 git」注释，先做**同源性核验**（三处密钥 **len=64 / sha6=`67da1a614a93` 一致**），再把密钥写入**未跟踪**的权威注入源 `OpenBase/.env.shared-infra`（使**编排器启动路径**亦具备回写出站 JWT，`CR-148-006` 在权威路径真正生效），并对 OpenLLM 仓该文件执行 **`skip-worktree`**（实测 `S .env.shared-infra`，**可逆**）——**未提交、未删除**，本地实值原位保留、提交版仍为空值模板。③ **处置 2/3（原子提交）**：**`a5bde45`**（`chore(repo)`，211 文件纯删除）与 **`9b9fcd5`**（`test(tests)`，`+12/-2`），均按**显式路径** `git add`、**未用 `git add -A`**，且暂存前后核验**非 `__pycache__` 项 = 0**；工作区由 **86 M / 211 D / 80 ??** 收敛为 **84 M / 0 D / 80 ??**。④ **顺带发现并登记 `CR-148-010`（待裁定）**：`git ls-files` + `git log --all` 双重核验显示 **8 个 v1.4.8 交付文件在全仓历史中从未提交**（`orchestration/` 下 `context_metrics.py`、`prompt_pipeline.py`、`component_pipeline.py`、`golden_set.py`、`baseline_report.py`、`attribution_b.py`、`history.py` 与 `services/session_scope.py`），另有多个已跟踪文件仍为 M —— 定性为**版本基线漂移风险**，与《测试报告》§7 #5 的口径**不完全一致**，**本轮未处置**。⑤ 文档版本 **v1.10.0 → v1.11.0**，状态 [Review]。依据：证据文件 **§二十五** |
| **v1.12.0** | **2026-09-21** | **AT-OpenBase-Test / DO-OpenBase-Dev** | **`CR-148-010` 入库范围裁定与实施（人工批准，批准人＝用户）**。① **裁定依据**：沿用《OpenLLM-联调产物待提交清单-v1.0.0》**A/B/C + 需人工判定**四类框架与其「只 add 预期路径、**禁止 `git add -A`**」纪律，并以《DevLogReport R-396~R-398》§4 交付清单（**19 源文件 + 1 数据资产 + 15 测试**）逐项对齐；确认 S4 批次已入库（identity 12 / verify-env 3 / S4 测试 15 / S4 文档 6），残量即 R-396~R-398 增量 + 噪音。② **裁定范围**：**入库** R1 新增源码 **8**、R2 修改源码 **6**（**实测 need-star 命中 0 → 无需 hunk 拆分**）、R3 数据资产 **1**、R4 文档 **2**、R5 `.devflow/state.json`、C 噪音清理（**71 pyc + 8 `.pylib` dist-info + `data/edge_tokens.jsonl`** 移出跟踪 + `.gitignore` 增补）；**不入库** `.pylib` vendored、`backend/data/*.db*`、`backup/`、仓根 `*.bat`×4、`scripts/*_commit_push*.ps1`×5、方案 HTML、调试脚本；**另批** `test_billing_v2_api.py`（J-6）与 3 份历史文档（J-9/J-10/J-11）。③ **实施（4 个原子提交）**：**`10e4cc6`**（`feat(v148)`，8 文件 `+1262`）、**`0fa9e84`**（`feat(v148)`，6 文件 `+173/-81`）、**`ab90513`**（`chore(v148)`，4 文件 `+704`）、**`589012d`**（`chore(repo)`，81 文件 `+6/-262`）；每批提交前暂存计数 = **8/6/4/81** 与预期一致，**工作树文件未被删除**。④ **结果**：工作区 **84 M / 80 ?? → 1 M / 14 ??**，残量全部属「不入库/另批」。⑤ **两处如实更正/登记**：**（a）** 前序记录将 `backend/.pylib/**` 表述为「未跟踪」**不准确** —— 实测 **3510 个已跟踪文件**（另有约 1157 项未跟踪），其正式处置属**上游 `CLR-214-004` 流程**（涉及 3510 项索引变更），**本轮未执行**；本轮仅新增 `.gitignore` 规则 `backend/.pylib/`，**作用边界＝仅阻止新增文件进入跟踪**；**（b）** 清单 §3 登记的 **need-star 增量在当前工作树已无痕迹**（`profile_refine.py` 与 4 个 `test_*_phase1.py` 已从磁盘消失且从未入库）→ 按**风险**登记，交其立项方确认。⑥ 文档版本 **v1.11.0 → v1.12.0**，状态 [Review]。依据：证据文件 **§二十六** |
| **v1.13.0** | **2026-09-21** | **AT-OpenBase-Test / AD-OpenBase-Dev** | **`CR-148-011`：按 TT-ID 整批补跑（Step 4 唯一产品侧卡点）执行完毕 —— 19 通过 / 2 未通过 / 1 项新缺陷**。① **范围与口径**：对 **T2（TT-005~014）**、**集成（TT-015~020）**、**安全（TT-035/036）**、**UAT（TT-041~044）**逐 ID 执行，**L1 硬断言**、无法判定即记 FAIL。② **结果**：**T2 10/10 全通过**；集成 4 通过（TT-016/017/018/019）+ **TT-015、TT-020 未通过**；安全 **TT-035/036 通过**（**TT-036 消息路本轮补齐**：他用户 404/0 条）；UAT **TT-041/042/043 通过**（TT-042 改以**持久化 trace** 比对，路由三项与模型选型完全一致）、**TT-044 未执行**（专项工装，显式登记）。③ **新缺陷 `DEF-BE-148-009`（P2）**：`GET /api/v1/monitoring/traces/{trace_id}/spans` **500**，根因 **`ResponseValidationError: 8 validation errors`**（`traces.py:362`；响应模型要求 `span_id/name/kind/status`，落库为 `{step,ms}`）→ **待修复**。④ **两项未通过定性（非缺陷）**：**TT-015**＝memory 组件 `degraded`（与「直连客户端缺四维身份」同源）+ 无可用 `kb_id` 来源端点 → **H 类环境/前置阻塞**；**TT-020**＝历史段注入**无可观测面**（计数器未接线致 `segment_tokens.history` 恒 0）→ **观测缺口**，需补接线后判定。⑤ **偶发 500（P3，待观察）**：空串 `session_id` 主批次首测 1 次 500，其后 5 次均 200，**未复现**（根因未捕获，已改为实例日志落盘）。⑥ **用例口径更正 4 处**（TT-005 `choices`→`content`、TT-019 流式以 trace 为口径、TT-020 历史来源为 `messages`、TT-012 实际路径）。⑦ 文档版本 **v1.12.0 → v1.13.0**，状态 [Review]。依据：证据文件 **§二十七** |
| **v1.14.0** | **2026-09-21** | **AD-OpenBase-Dev / AT-OpenBase-Test** | **`DEF-BE-148-009` 修复并验证通过（`CR-148-011` 闭环）**。① **根因**：`traces.spans` 列**同一列承载两种形态** —— ① OTel 形态（`trace_service.TraceContext` 写入：`span_id/name/kind/status/...`）、② **步骤计时形态**（网关轻量写入 `[{"step":"auth","ms":0},{"step":"llm","ms":10343}]`）；端点声明 `response_model=List[SpanResponse]`（必填 `span_id/name/kind/status`），形态②**每 span 缺 4 项 × 2 = 8 项校验失败** → `ResponseValidationError` → **500**。② **修复方案（写前先定取舍）**：在**服务层**新增 `normalize_span_for_response()` / `normalize_spans_for_response()` 做**读取侧归一化**（形态①原样透传并补默认 `kind=internal`/`status=unset`；形态②以 `step` 为 `name`、`ms` 为 `duration_ms`、`status=ok`、`attributes={step,ms}`；未知形态与标量亦合成合法结构、**不丢数据**；非列表按空列表），端点只调用归一化结果，**签名与响应契约不变**；**未采用「仅放宽响应模型」方案**（该方案会把形态②字段静默丢弃、返回空壳），**未改落库结构**（避免历史数据迁移）。③ **TDD**：新增护栏 `tests/unit/test_trace_spans_shape.py`（10 例）→ **RED**（收集期 `ImportError`；端点级用例修复前 500）→ **GREEN 13 passed**。④ **静态质量**：新护栏 `All checks passed`；两被改文件**改动行零告警**（首轮引入 5 条 `UP006/UP045` 同族告警，按项目标准改用 `X \| None`/`dict`/`list` 后清零，总告警 112 → 107）。⑤ **回归 + 基线对照**：`tests/unit` 全量 **2188 passed / 13 failed**，**`git stash` 基线对照证明 13 项失败与本次修复无关**（修复前后同为 13 failed）；615 error 为根 `tests/conftest.py` 既知环境缺陷（§7 #4）所致夹具缺失。⑥ **运行时 5/5**：**目标端点 500 → 200**（`[{"span_id":"openllm-…-0","name":"auth","kind":"internal","duration_ms":0,"status":"ok","attributes":{"step":"auth","ms":0}},{…"name":"llm","duration_ms":3953…}]`）、`/{id}` 仍 200、未知 trace 仍 404。⑦ **提交** `48610cc`（3 文件 `+259/-2`，显式路径 `git add`，**TDD 合规**）。⑧ 文档版本 **v1.13.0 → v1.14.0**，状态 [Review]。依据：证据文件 **§二十八** |
| **CR-148-012** | **`TT-015` / `TT-020` 复测**——复测中发现并闭环 **2 项 P1 产品缺陷**（2026-09-21） | **① `DEF-BE-148-010`（P1，第零段计量未接线）**：`executor.py:158`（同步）与 `openllm_gateway.py:2219`（流式）调用共用组装步骤 `build_prompt(...)` **均未传 `count_tokens`** → `prompt_pipeline.py:94` 的 `PromptComposition.counted=False`、`segment_tokens` 恒 0；两处回执站点虽已传计数器（`:1977`/`:2272`），但**组装时缺计数器** → 回执**永无有效计量值**（`TT-009` token 分项恒 0；`TT-020` 无任何可观测面）。**修复**：新增 `default_token_counter(model=None)`（两路径同口径以保证分项可比），两处组装点传入。**TDD**：`test_zeroth_segment_counting.py`（8 例）**RED（`ImportError`）→ GREEN 8 passed**。**提交 `c89ffc2`**（4 文件 `+138/-2`）。**注：此前「`counted=false` 属设计语义（未连接）、非缺陷」的定性应更正为「接线缺失」**。<br>**② `DEF-BE-148-011`（P1，OpenMemory 读路未按真实契约分派）**：`OpenMemoryClient.search()` **硬编码 stub 路径** `/openmemory/v1/search`，未按 `real_mode` 分派到**已实现**的 `recall()`（`POST /api/v1/recall`）→ 真实档案下 memory 读路恒打 stub → 真实服务 **HTTP 403** → **组件 `memory` 每次调用都降级**。**日志实录**：`组件 open_memory 不可用: HTTP 403: Forbidden` + `POST http://127.0.0.1:8020/openmemory/v1/search`。**排除误判**：两处 env **均已** `OPENLLM_OPENMEMORY_REAL=true`（**非配置未开**）；**写路 `remember()` 已分派真实契约**（故回写路正常）→ **仅读路缺分派**。**修复**：`search()` 内按 `real_mode` 分派 `recall()`（真实端点无 stub 的 `memory_types` 过滤；stub 分支行为不变）。**TDD**：`test_openmemory_read_path_real_contract.py`（3 例）**RED（实际 URL 仍为 stub）→ GREEN 26 passed**（新 3 + 既有 21 + 2，**stub 无回归**）。**提交 `d060b3f`**（2 文件 `+97`）。 | OpenLLM 仓 `app/edgerouter/orchestration/{prompt_pipeline,executor}.py`、`app/api/openllm_gateway.py`、`app/edgerouter/adapters/openmemory_client.py`；本仓《测试报告-v1.4.8》§7 | **均已修复并验证通过（2026-09-21）**：**`TT-020` PASS**（次轮 `counted=True`、`segment_tokens={'history':100,'query':7}`、`prompt_total=118`；**对照组不带 `messages` 时 `history=0`** → 判据有效）；**`TT-009` 残留 PASS**（metrics token 分项非 0）；**`TT-015` PASS**（`memory+llm`→`executed=['memory','llm']`；`memory+rag+llm`→`executed=['memory','rag','llm']` 且 `degraded=[]`、`rag_source=external`；**终局取证** `segment_tokens={'rag':36,'query':21}`、`contexts_tokens=36`、**rag 计量 `injected_items=1/injected_tokens=36` 证明知识库上下文已注入**）。<br>**前置更正**：「无可用 `kb_id`」系**探测未带鉴权头**所致（OpenRAG `/api/v1/collections` 需 `X-API-Key`；带头上返回 **12 个集合**），**非环境缺陷**。<br>**残留（如实登记，不视为通过）**：① `TT-015` memory 侧 `items_count=0`（**数据侧无可召回记忆，非组件故障**）；② **`contexts` 未在响应暴露**（原用例文字「contexts 含 memory_ctx/rag_ctx」无法从响应观测，已改以回执计量为等价证据，建议用例文档更正口径）；③ `dps` 仍不可用 → `TT-016` 真链路未验证（H 类）。证据 **§二十九** |
| **v1.15.0** | **2026-09-21** | **AD-OpenBase-Dev / AT-OpenBase-Test** | **`CR-148-012`：`TT-015` / `TT-020` 复测完成 —— 两项均转 PASS，同时闭环 2 项 P1 产品缺陷（均为接线缺失，非测试脚本问题）**。① **`DEF-BE-148-010`（P1，第零段计量未接线）**：`executor.py:158` 与 `openllm_gateway.py:2219` 组装 `build_prompt` 时**均未传 `count_tokens`** → `counted=False`、`segment_tokens` 恒 0 → 回执永无有效计量值（`TT-009` 分项恒 0、`TT-020` 无观测面）；**修复**＝新增 `default_token_counter()`（两路径同口径）并两处传入；**TDD RED→GREEN 8 passed**；**提交 `c89ffc2`**（4 文件 `+138/-2`）。**更正**：此前「`counted=false` 属设计语义、非缺陷」的定性**改为「接线缺失」**。② **`DEF-BE-148-011`（P1，OpenMemory 读路未按真实契约分派）**：`search()` 硬编码 stub 路径 `/openmemory/v1/search`，未分派到已实现的 `recall()`（`/api/v1/recall`）→ 真实档案下 memory 读路 **HTTP 403** → 组件 `memory` 恒降级；**排除误判**：两处 env 均已 `OPENLLM_OPENMEMORY_REAL=true`，**写路 `remember()` 本就已分派**（回写路正常）→ **仅读路缺分派**；**修复**＝`search()` 按 `real_mode` 分派；**TDD RED→GREEN 26 passed**（stub 无回归）；**提交 `d060b3f`**（2 文件 `+97`）。③ **复测结果**：**`TT-020` PASS**（`history:100`，对照组 0）、**`TT-009` 残留 PASS**（token 分项非 0）、**`TT-015` PASS**（`executed=['memory','rag','llm']`、`degraded=[]`、`rag_source=external`；终局 `rag.injected_tokens=36` 证明上下文已注入）。④ **前置更正**：「无可用 `kb_id`」系探测**未带 `X-API-Key`** 所致（带头上 OpenRAG 返回 **12 个集合**），**非环境缺陷**。⑤ **残留（如实登记，不视为通过）**：`TT-015` memory 侧 `items_count=0`（数据侧无命中，非故障）；**`contexts` 未在响应暴露**（改以回执计量为等价证据，建议用例文档更正口径）；`dps` 不可用 → `TT-016` 真链路未验证。⑥ 文档版本 **v1.14.0 → v1.15.0**，状态 [Review]。依据：证据文件 **§二十九** |
| **CR-148-013** | **T3 巡检与 Mock 批次（Step 4 剩余未执行类别）**——执行 6 例，发现并登记 **1 项 P1 缺陷 + 1 项不适用声明**（2026-09-22） | **① 执行结果**：**`TT-021`（四桩健康与契约）7/7 ✅**（端口无冲突 / 无静默跳过 / 四桩契约 / 故障注入可用）；**`TT-022`（回退开关开启）5/5 ✅**（桩 `down` → 503；`rag_source=builtin`、`degraded=[]`、回答 696 字；`raw_results` 同；`recover` 恢复）；**`TT-023`（开关关闭）4/4 ✅**（`degraded=['rag']`、`rag_source=skipped`、主流程 200/265 字）；**`TT-028`（T3a 服务间集成巡检）4/5 链路 OK**（memory / rag / llm / **编排总链** 均通，**代码类 5xx = 0**；**profile 链 FAIL**＝DPS(8030) 未启动、回执 `retrying` → **H 类环境遗留**）；**`TT-029`（深度用例 会话链路 CRUD）4/4 ✅**（创建 201 / 发消息 201×2 / 查历史 本会话 2·异会话 0 / **归档 `POST /api/v1/conversations/{id}/archive` → 200**）。<br>**② 新缺陷 `DEF-BE-148-012`（P1，待修复）**：**RAG 适配器未注册时触发内置回退，与已批准语义不符**。**预期**（用例文字 + `OpenBase-DevLogReport-v1.4.8` §13.1 **第十二批语义变更**：「『RAG 适配器未注册』由『回退内置 RAG』改为『**组件级降级（不触发回退）**』」）＝**降级且不回退**。**实测**（`OPENRAG_ENABLED=false` + `OPENRAG_FALLBACK_BUILTIN=true`）：**`degraded=[]`、`rag_source=builtin`**（`TT-024` **3/3 断言未达 → FAIL**）。**日志实录**：`WARNING OpenRAG 检索失败，回退内置 RAG（rag_source=builtin）`，且同实例日志**无** `OpenRAG client 已注入` 行（确认适配器确实未注册）。**定位**：`openllm_gateway.py` 组件 handler 包装（`:340-370` 同型 + `:735-770` 的 `rag_fallback` 装配）把「**装配缺失**」与「**外部失败**」并入同一分支，故开关开启即回退；`component_pipeline.run_components` 的「`handler is None` → 记降级」分支（`:109-110`）在该形态下**不会被触达** → **第十二批语义变更仅收敛了流式路径表现，组件/同步路径仍触发回退**。**建议修复**：handler 装配层区分「装配缺失」与「外部失败」，前者**不下发** `rag_fallback`。<br>**③ 不适用声明**：**`TT-025` / `TT-026`（前端发消息携带会话标识 / 既有前端 E2E 回归）→ 不适用**——**本工作区内 OpenBase/OpenLLM 无前端工程**（`*.spec.ts` 的 `e2e/` 规格仅属其他项目 CoPlayer），无前端 dev 服务与 Playwright 用例集；**影响**：前端侧会话标识透传与既有 E2E 未验证；**补救**：前端工程就绪后补跑。**`TT-027`（T3a 全页面巡检）→ 以 `TT-028` 服务间集成巡检替代**（依技能「纯后端项目」规则）。<br>**④ P3 改进点**：openrag / openmemory / profile **三桩无 `/health` 端点**，本轮以只读路由为存活探针（422 = 在线但请求体校验未过）；建议三桩补齐 `/health`。 | OpenLLM 仓 `app/api/openllm_gateway.py`、`app/edgerouter/orchestration/component_pipeline.py`；`backend/mock_services/` | **`TT-021`/`TT-022`/`TT-023`/`TT-028`(4/5)/`TT-029` 已通过并登记**；**`TT-024` 经 `DEF-BE-148-012` 修复后转通过（`v1.17.0`）**；**`TT-025`/`TT-026` 不适用待前端就绪补跑**；`TT-027` 由 `TT-028` 替代。证据 **§三十**、**§三十一** |
| **v1.16.0** | **2026-09-22** | **AT-OpenBase-Test** | **`CR-148-013`：T3 巡检与 Mock 批次执行完毕（6 例）—— 5 例通过 / 1 例未通过 / 1 项不适用，并登记 1 项 P1 缺陷**。① **Mock 批次**：以仓库既有 4 桩（`openrag` 8090 / `openmemory` 8091 / `profile` 8092 / `product` 8093）前台长驻启动，**端口预检全空闲、就绪 4/4、无静默跳过**（三桩无 `/health`，以只读路由为存活探针）。**`TT-021` 7/7 ✅**；**`TT-022`（回退开关 true + 故障注入）5/5 ✅**（`rag_source=builtin`、`degraded=[]`、回答 696 字、收尾恢复）；**`TT-023`（开关 false）4/4 ✅**（`degraded=['rag']`、`rag_source=skipped`、主流程不中断）；**`TT-024` 3/3 未达 → ❌**。② **T3 批次**：**`TT-028`（T3a 服务间集成巡检）4/5 链路 OK**（memory / rag / llm / 编排总链；**代码类 5xx = 0**；profile 链因 **DPS 未启动**为 H 类）；**`TT-029`（会话链路 CRUD 深度用例）4/4 ✅**（创建 201 / 发消息 201×2 / 查历史 本会话 2·异会话 0 / 归档 `POST /api/v1/conversations/{id}/archive` → 200）。③ **新缺陷 `DEF-BE-148-012`（P1，待修复）**：**RAG 适配器未注册时触发内置回退**，与 `DevLogReport` §13.1 第十二批**已批准语义**（降级、不触发回退）不符；实测 `degraded=[]` + `rag_source=builtin`；定位为 handler 装配层未区分「装配缺失」与「外部失败」。④ **不适用声明**：`TT-025`/`TT-026`（前端 E2E 类）—— 本工作区**无 OpenBase/OpenLLM 前端工程**（`*.spec.ts` 仅属 CoPlayer），**待前端就绪补跑**；`TT-027` 由 `TT-028` 替代（纯后端口径）。⑤ **P3 改进点**：三桩缺 `/health`。⑥ 文档版本 **v1.15.0 → v1.16.0**，状态 [Review]。依据：证据文件 **§三十** |
| **v1.17.0** | **2026-09-22** | **AD-OpenBase-Dev / AT-OpenBase-Test** | **`DEF-BE-148-012`（P1）修复并验证通过 —— `TT-024` 转 PASS，Mock 批次收敛为 4/4**。① **根因**：`openllm_gateway._build_component_handlers._rag_handler`（`:341-370`）以 `except Exception` 捕获**全部**异常并触发内置回退，把「**装配缺失**（适配器未注册 / client 未注入）」与「**外部检索失败**」混为一类；而共用组件步骤 `component_pipeline.run_components`（`:112-117`）对 `ComponentUnavailableError / asyncio.TimeoutError` 正是**记降级、不回退** → 第十二批语义变更**只落到 component_pipeline，网关 handler 包装仍是旧行为**（违反 AC-148-03-1 两路径一致）。② **修复**：在 `_rag_handler` 异常链中**前置**分支 `except (ComponentUnavailableError, asyncio.TimeoutError)` → 记 warning 后 **raise**（交由上层记降级、**不回退**）；原 `except Exception` 语义不变（外部失败仍按开关回退）；并按文件既有风格局部导入异常类。③ **TDD**：新增 `tests/unit/test_rag_unregistered_no_fallback.py`（4 例）→ **RED 2 failed / 2 passed**（装配缺失被吞成回退；外部失败 2 例为既有行为基线）→ **GREEN 4 passed**。④ **静态质量**：新护栏 `All checks passed`；`openllm_gateway.py` **零告警、改动行零告警**（首轮漏导入 `ComponentUnavailableError` 致 `F821`，测试即刻暴露并修正）。⑤ **回归 + 基线对照**：`tests/unit` 全量 **2203 passed / 13 failed**，**failed 数与既有基线完全一致（13 = 13）→ 无回归**；615 error 为根 conftest 既知环境缺陷（§7 #4）。⑥ **运行时复测（TT-024 原配置）**：**3/3 通过** —— `degraded=['rag']`、`rag_source=skipped`（原 `builtin`）；主流程 200/271 字且记降级；两形态 `rag_source` 均 `skipped`。⑦ **提交 `ef3d44e`**（2 文件 `+120/-1`，显式路径，**TDD 合规**）。⑧ 文档版本 **v1.16.0 → v1.17.0**，状态 [Review]。依据：证据文件 **§三十一** |
| **CR-148-014** | **性能批次执行（Step 4 剩余项「性能需先定 P99 目标值」的后续）**——`TT-039` ✅ 通过 / `TT-038` ❌ 未通过（受限口径），发现并登记 **1 项待定性问题（成本优先路由选中不可用模型）+ 1 项计量口径缺口**（2026-09-22） | **① 前置**：目标值由《非功能设计说明-v1.4.8》**v1.1.0 §1.1**（P-1~P-12，2026-09-22 人工批准）定义，`TT-038`/`TT-039` 由「不可判定」转为「可执行」；驱动 `OpenLLM/backend/scripts/run_perf_batch.py`（受控、可复现、只观测）。<br>**② 执行结果**：**`TT-039` ✅**（回执 @10,140 行 n=200：P50 236.5 / P95 **664.0** / P99 **864.8 ms**，达标 → **不立技债**；规模 140→10,140 行 P95 增至 2.32× → 容量观察项）；**`TT-038` ❌（受限口径）**：**4 达标**（P-3 流式首包 P95 68.3 ms / P-7 / P-8 计量导出 P95 274.9 ms / P-9 消息查询 P99 128.4 ms）、**2 未达标**（**P-1 同步对话本仓开销 P50 2401.3 ms** vs ≤50 ms；**P-6 回执查询 P50 112.6 ms** 超限 12.6 ms）、**2 未判定**（P-10 计量覆盖缺口 / P-11 吞吐受全局限流）、**P-12 错误率未达标**（同步 13.3% / 流式 6.7%）。<br>**③ 新问题（P2，待定性：缺陷 or 配置）**：**成本优先路由选中不可用模型 `qwen3:0.6b`** → 对话/流式偶发 `{"code":5001}`，流式以 `event: error` 下发且**无 `done` 终止事件**。**证据**：失败样本 `routing` 事件 `"model":{"selected":"qwen3:0.6b","reason":"cost"}`；**定点探测** `model=qwen3:0.6b` → **HTTP 500 / `5001 LLM 组件调用失败`**（4713 ms），`model=deepseek-v4-flash` → **200**（3237 ms）→ **该模型在本环境不可用却仍被选中**，`fallback_model` **未救回**（原因待确认）。**关联**：与本记录既有 **P3「偶发 500（未复现）」疑同源**，本轮给出**可复现判定路径**。**建议**：候选池可用性门禁 / 剔除不可用模型；确认 fallback 未生效原因。<br>**④ 计量口径缺口**：`timeline` **未覆盖「画像拉取 / 回写派发」** → 同步对话存在 **~2.4 s 未计量差额**（恰等于「墙钟 − `llm`」），致 **P-1 / P-10 无法公平判定**（当前 P-1 差额实际含 DPS 连接等待）。**建议**：补步骤计时或提供压测用「关闭画像注入」开关。<br>**⑤ 环境约束 4 项（实测取证）**：C-1 网关**全局限流 `1 req/s`（burst 60）→ 并发 8 档位不可达成**（并发 8 突发第 **64** 次起持续 `429 rate_limit_exceeded`）；C-2 语义缓存阈值 0.92（命中返回空 timeline，以唯一 nonce 规避）；C-3 **DPS 不可用**（探针 `latency_ms=2046`）；C-4 即 ③。<br>**⑥ 受控数据变更 3 项**（性能账号租户绑定 affected_rows=1 / 专用会话 / 队列 1e4 行播种）**均已记录回滚方式**，**播种行已清理（删除 10,000、残留 0）**。 | OpenLLM 仓 `backend/scripts/run_perf_batch.py`（新增）；本仓《OpenBase-性能测试记录-v1.4.8》v1.0.0、《测试报告-v1.4.8》v3.4.0 §7 #24；证据 `doc/test/evidence/v148/tt038-perf-batch-base-20260922.json`、`tt039-receipts-1e4-20260922.json`、`tt038-perf-env-findings-20260922.txt`、`tt039-seed-receipts-1e4-20260922.py` | **`TT-039` 已通过并登记**；**`TT-038` 未通过（受限口径）**——**放行前须**：① 专用压测实例（提高 `RATE_LIMIT_PER_SECOND`）复测并发 8 档位；② 补计量覆盖后重判 P-1/P-10；③ 处置 ③ 的模型可用性根因；④ 核查 P-6 边缘超限。证据 **§三十二** |
| **CR-148-015** | **模型路由可用性门禁缺口（Step 4 发现 → 回溯 Step 3 修复）+ 压测错误率归因更正**（2026-09-22） | **① 缺陷 `DT-148-015`（根因三处叠加）**：**（a）** `openllm_gateway._route_model_auto` 构建候选时把 `health_status="healthy"`、`fail_count=0` **硬编码** → `ModelRouter` 的健康过滤（`health_status != healthy` 或 `fail_count >= 阈值`）**恒为空转**；**（b）** 候选构建**完全不校验 provider** → 「active 模型挂 inactive provider」（实测 `gpt-4` ← `deepseek2`）照样入选；**（c）** 路由器**每请求 `ModelRouter()` 新建** → `record_failure` 结果随请求丢弃、**熔断永不 open**，且网关从未调用 `record_failure`。**实测**：池内 3 个本地模型均不可达（定点探测 `qwen3:0.6b` → **HTTP 500 / `5001 LLM 组件调用失败`**、`qwen2.5:0.5b` → **500**、`llama3.2:1b` → **500**；`deepseek-v4-flash` → **200**），且三者价格均为 NULL（`float(None or 0)=0`）→ 成本因子最优 → **成本优先下天然胜出**。<br>**② 修复（提交 `6cb1f61`，2 文件 `+271/-22`，TDD 合规）**：新增 `_build_model_candidates()`（provider 门禁 + provider 真实健康透传 + 路由器实时失败计数）；路由器改**进程级单例**（`@lru_cache(maxsize=1)` 的 `_get_model_router()`）；新增 `_note_model_outcome()` 并在 **同步 `_call_llm_once`** 与 **流式 `_stream_llm_with_health` 包装**回写调用结果（失败累加 / 成功清零）；候选全被排除时返回 **1004 无可用模型**。<br>**③ 验证**：TDD 新增 `tests/unit/test_model_router_availability_gate.py`（**7 例**）**RED（7 failed）→ GREEN 7 passed**；`ruff All checks passed`；`tests/unit` 全量 **2210 passed / 13 failed**（**failed 数与基线一致 → 无回归**）；**进程内真实数据验证**：候选 4 → **1**（跳过 inactive provider 的 `gpt-4`），首次选中 `deepseek-v4-flash`；**对其记 3 次失败后重选改判 → 熔断排除生效 = True**。<br>**④ 数据修正（可回滚）**：3 个未部署本地模型置 `inactive`（`affected_rows=1` + `3`）；回滚 `UPDATE llm_models SET status='active' WHERE model_code IN ('qwen3:0.6b','qwen2.5:0.5b','llama3.2:1b')`。<br>**⑤ 归因更正（重要）**：本轮压测错误率（同步 **13.3%** / 流式 **6.7%**）**并非**由「不可用模型被选中」造成 —— `routing` 事件中的 `"model":{"selected":"qwen3:0.6b"}` 是**路由前**取值（取自 `settings.DEFAULT_LLM_MODEL`），不能作为实际调用模型的证据；失败请求的 **trace 实测为 `model=deepseek-v4-flash`、`error_code=5001`、`latency_ms=null`**，且错误文案为网关 5001 兜底（**非** `LLM 组件调用失败`）→ **错误率来源另立为「间歇性 5001」待定性项（P2）**，与本 CR 的门禁缺口**不是同一问题**。<br>**⑥ 残留**：被测实例（8041）为**修复前构建**的常驻进程 → 修复后的 HTTP 端到端复测需**带编排器 `Env` 重启实例**；间歇性 5001 因旧实例 stdout 未落盘而**未能取得根因栈**。 | OpenLLM 仓 `app/api/openllm_gateway.py`、`tests/unit/test_model_router_availability_gate.py`；`llm_models`（数据）；本仓《OpenBase-性能测试记录-v1.4.8》**v1.1.0** §6 #1 / §6.1 / §6 #6；证据 `doc/test/evidence/v148/dt148-015-*` | **门禁缺口已修复并验证**；**残留**：① 重启实例后做 HTTP 端到端复测；② **间歇性 5001（P2 待定性）**需以日志落盘方式重启后复现取栈，并与既有 P3「偶发 500」**并轨跟踪**；③ 失效 provider 的模型治理（`inactive` provider 下的模型应同步下线） |
| **CR-148-016** | **压测错误率真实根因捕获并修复：ORM 分离实例访问致间歇 5001（`DT-148-016`）**（2026-09-22） | **① 取证**：按 `CR-148-015` 遗留项，以**日志落盘方式 1:1 重启**被测实例（`PORT`/`PYTHONDONTWRITEBYTECODE` 与编排器定义一致，`2>&1 \| Tee-Object` → `logs/openllm-20260922.log`），复现压测同口径失败并捕获 **3 处 `Traceback`**，全部为 `sqlalchemy.orm.exc.DetachedInstanceError: Instance <Model/User …> is not bound to a Session`：① `_call_llm_once` **成功路径**读 `model_obj.id`（**`DT-148-015` 新增行引入**）；② `_stream_llm` 读 `identity.user.organization_id`（**既有**）；③ 两处计费读 `provider.id` / `model_obj.id`（**既有**）。**机理**：会话提交/关闭后 ORM 属性过期，请求路径再读该属性触发懒加载刷新即抛错 → 网关注解为 `5001 内部错误`（故 `latency_ms=null`）。**这就解释了同步 13.3% / 流式 6.7% 的错误率，且与「模型不可用」「上游慢」无关**（对 `CR-148-015` 的归因更正做了最终确认）。<br>**② 修复（提交 `da312d6`，3 文件 `+73/-24`）**：`GatewayIdentity` 增 **`organization_id` / `role` 标量**并在 JWT / API Key 两处**建身份时固化**；请求路径 **11 处 `identity.user.*` 全部改读标量**；`_call_llm_once` / `_stream_llm` **await 前固化 `model_id`**（流式经 `usage_holder["model_id"]` 传递）；新增 **`_safe_orm_id()`** 兜底两处计费的 `provider.id`/`model_obj.id`（读不到返回 fallback，**记账元数据可降级、不得反噬主链路**）。<br>**③ 验证**：端到端（1:1 重启后）**同步 20/20、流式 20/20 全通过 → 错误率 0%**（修复前同口径 3/40 = 7.5%）；新实例日志 **Traceback 0 / DetachedInstanceError 0 / 「内部错误」0 / `status_code: 500` 0**（修复前 3 / 3 / 2 / 有）；`/openllm/v1/health` = `healthy`（2.14.3）。**回归**：`tests/unit` **13 failed / 2210 passed / 615 error**（与基线逐项一致 → 无回归）；`ruff All checks passed`；两处测试替身（`test_rag_unregistered_no_fallback.py`、`test_s4_t5_prefix_normalize.py`）按身份契约补齐标量字段，属**契约漂移修正**而非放宽断言。<br>**④ 残留**：计费 `provider_id`/`model_id` 极端情况下可能落 `None`（以兜底换取可用性）→ 建议后续在模型查询处固化标量并向下透传（本次未改函数签名以避免大范围波及）。 | OpenLLM 仓 `app/api/openllm_gateway.py`、`tests/unit/test_rag_unregistered_no_fallback.py`、`tests/unit/test_s4_t5_prefix_normalize.py`；本仓《OpenBase-性能测试记录-v1.4.8》**v1.2.0** §6 #6 / §6.2 / §7；证据 `doc/test/evidence/v148/dt148-016-detached-instance-stack-20260922.log`（3 处堆栈原文）、`dt148-016-smoke-after-fix-20260922.json` | **已闭环**（`DT-148-016`）；**下游**：`TT-038` 复测时 P-12 错误率按 0% 口径验证，**仍须**在专用压测实例上测并发档位（C-1）并补「画像拉取/回写派发」计量（P-1/P-10） |
| **v1.20.0** | **2026-09-22** | **AD-OpenBase-Dev / AT-OpenBase-Test** | **`CR-148-016`：压测错误率真实根因（ORM 分离实例访问）取证并修复 —— 间歇 5001 闭档**。① **取证**：日志落盘 1:1 重启 → 3 处 `DetachedInstanceError` 堆栈（含 `DT-148-015` 新增行引入的一处，如实登记）。② **修复** `da312d6`：身份标量化（`organization_id`/`role`）+ 11 处 ORM 属性访问改标量 + await 前固化 `model_id` + `_safe_orm_id()` 兜底。③ **验证**：端到端 **40/40 全通过（错误率 0%）**，日志 4 项错误指标全 0；`tests/unit` **13 failed / 2210 passed**（基线一致，无回归）；`ruff All checks passed`。④ **残留**：计费元数据极端情况落 `None` 的加固建议。⑤ 文档版本 **v1.19.0 → v1.20.0**，状态 [Review]。依据：《性能测试记录-v1.4.8》**v1.2.0**；提交 **`da312d6`** |
| **CR-148-017** | **画像拉取降级路径无失败短路/负缓存（`DT-148-019`，P1 产品缺陷）—— DPS 不可用时每请求固定付出 ≈ 2.04 s**（2026-09-22，双口径收口轮发现） | **① 发现路径**：按《非功能设计说明-v1.4.8》**v1.2.0 §1.1.3** 双口径复跑 `TT-038`，**单飞档** `P-1`（同步 `/chat` **本仓步骤耗时**，目标 P50 ≤50 ms）实测 **P50 2629.4 ms**；经 `DT-148-018` 已接线的 timeline 分解：端到端 P50 3302.0 ms = `llm` 步骤 625.0 ms（非本仓）+ **本仓开销 2629.4 ms**，其中 **`profile_fetch` ≈ 2037 ms**、未计量差额已降至 **592.3 ms**。<br>**② 隔离探针取证**（`dt148-019-profile-fetch-cost-probe-20260922.py`，**不接触压测实例**）：对 `DPS_BASE_URL=http://127.0.0.1:8030`（**该端口无服务**）连续 3 次调用 `DPSClient.get_profile` → **2041.8 / 2036.5 / 2036.2 ms**（`ConnectError: All connection attempts failed`）；**两次独立运行结果一致**（另一次 2043.1 / 2032.7 / 2047.5 ms）。**三处独立证据同量级**：健康探针 `dps latency_ms=2046`、timeline `profile_fetch` ≈ 2037 ms、探针 ≈ 2036~2042 ms。<br>**③ 关键事实（对修复方案有决定性）**：该连接失败**并非瞬时 `ECONNREFUSED`**，而是**稳定 ~2.04 s**（实例启动日志实证 `DPS client 已注入: base_url=http://127.0.0.1:8030 timeout=5.0s`，即 `DPS_ENABLED=true` 且 `DPS_TIMEOUT=5s` **未达即失败**）；`app/api/openllm_gateway.py::_build_profile_ctx` 仅在异常后 `return None` **降级跳过**（降级语义本身正确），但**无负缓存、无失败短路** → **每次同步/流式对话都重新发起同一必然失败的连接**。<br>**④ 影响面**：不只影响压测 —— **全部同步与流式对话请求**均被拖累（单飞档本仓开销 P50 **2629.4 ms** / 并发 8 档 **4536.3 ms**），并使 `P-1` 不达标。<br>**⑤ 归因边界（须分别处置）**：**DPS 服务未启动属 H 类环境项**（依赖不可用），**不得与本缺陷合并定性**；但即便依赖可用，负缓存/短路仍应保留以抵御依赖抖动与半开状态。 | OpenLLM 仓 `app/api/openllm_gateway.py`（`_build_profile_ctx`）、`app/edgerouter/adapters/dps_client.py`（连接失败耗时特征）、`app/db/session.py`（本轮 `echo` 污染同批发现）；本仓《OpenBase-性能测试记录-v1.4.8》**v1.5.0** §4.5.1 / §5.3 / §6 #9、《测试报告-v1.4.8》**v3.7.0** §7 #26；证据 `doc/test/evidence/v148/dt148-019-profile-fetch-cost-probe-20260922.py`、`dt148-019-profile-fetch-cost-probe-output-20260922.txt`、`tt038-dual-single-flight-paced-20260922.json`、`perf-instance-8041-env-proof-20260922.log` | **✅ 已修复并验证（`v1.22.0`，2026-09-22；OpenLLM 提交 `ad7d472`，3 文件 `+327/-6`，TDD 合规）**：① **降级路径加失败负缓存/短路** —— 新增 `PROFILE_FAILURE_COOLDOWN_SECONDS`（默认 30s；0=关闭负缓存）+ 模块级 `_profile_failure_until`/`threading.Lock` 与 `_profile_circuit_open()` / `_mark_profile_failure()` / `_clear_profile_failure()`；`_build_profile_ctx` 改为「开关判定 → 冷却短路 → 本地上下文构造（**异常不计入依赖失败**）→ adapter 调用（成功清空 / 失败开启冷却）→ 空画像不视为失败 → 格式化异常独立降级」；② **关闭画像注入开关** —— 新增 `PROFILE_INJECTION_ENABLED`（默认 True，False=完全不拉取并降级跳过）；③ **复测**：L3 冒烟负缓存档 `profile_fetch` **2094 → 0 → 0 ms**、开关档三连 **0.0 ms**；P-1 定向复测（n=60，单飞不限节流）本仓开销 **P50 2629.4 → 1157.9 ms（−56%）**、`profile_fetch` **≈2037 → ≈47.7 ms（−97.7%）**。**如实登记：修复未达预期值**（预期「≤600ms」），因**残留未计量差额 P50 1110.2 ms**（大于此前估的 592.3 ms）→ **P-1 仍未达 ≤50 ms 目标**，该残留属 **`CR-148-018`（P-10 计量缺口）**，须接线后继续追。**级别 P1**：拖累全部对话请求主链路（修复前） |
| **CR-148-018** | **`P-10` 计量接线仍未执行（回写派发落点已定位）—— 口径缺口阻塞 `P-10` 判定**（2026-09-22） | **① 状态**：`DT-148-018` 已完成「画像拉取」入 timeline（步骤集合 `['auth','llm','profile_fetch']`），但**「回写派发」仍未接线** → `P-10`（回写路径内同步新增耗时 P99 ≤5 ms + 异步不派发阻塞）**两口径下均不可判定**。<br>**② 落点（已查明）**：`app/edgerouter/orchestration/executor.py::EdgeRouterExecutor._schedule_writeback()` —— 内含 `asyncio.create_task(self._writeback_with_retry(...))` + `self._pending_writebacks.append(task)`，即**真正进入异步队列的同步开销**（量级为微秒）。<br>**③ 候选落法**：**(a)** 在 `execute()` 记 `self._timeline = timeline`，于该方法内追加 `{"step":"writeback_dispatch","ms":…}`；**(b)** 为 `_schedule_writeback()` 增 `timeline` 形参并逐个调用点透传。<br>**④ 未执行理由（如实登记）**：属**编排核心**改动，须配套 **TDD 护栏（三路回写均产出该步骤）+ 全量回归**，不在当轮预算内草率提交；本轮**仅定位、未改动**。 | OpenLLM 仓 `app/edgerouter/orchestration/executor.py`；本仓《OpenBase-性能测试记录-v1.4.8》**v1.5.0** §5.2/§5.3、'§6 #8'；证据 `tt038-dual-single-flight-paced-20260922.json`（`steps_seen` 仅 3 步，无 writeback 步骤） | **✅ 已实施并验证（`v1.23.0`，2026-09-26；OpenLLM 提交 `72fd01e`，5 文件 `+203/-4`，TDD 合规）**：采用**改进版落法 (b)**（`execute()` 增可选 `timeline` 形参 → 由 `_schedule_writeback()` 逐次返回派发耗时并在调用侧累加，**三路合计只落一条** `writeback_dispatch`；**未调度任何回写时不落步骤**）；`Explicit`/`Auto` 编排器透传 `timeline`；网关同步路径传入、**流式路径**在「构造三路回调 + 逐路入队」处补同口径计量。**计时用 `perf_counter`**（`monotonic` 在 Win/Py3.10 实为 `GetTickCount64`、分辨率约 15.6 ms，无法度量亚毫秒派发开销）。**TDD**：`tests/unit/test_writeback_dispatch_timeline_guard.py`（**5 例**）**RED 4 failed / 1 passed → GREEN 5 passed**；`ruff All checks passed`；回归 `tests/unit` **13 failed / 2233 passed / 615 error**（与基线 13/**2228**/615 的 failed 与 error 一致、passed **+5 即新增护栏 → 无回归**）。**运行时（8041）首次取得 `P-10` 有效观测值**：**同步达标**（`writeback_dispatch` = **0.019 / 0.026 / 0.014 ms** ≤5 ms，`asyncio.create_task` 异步派发、无同步等待）、**流式不达标**（**727.638 / 555.923 ms**）→ **派生新缺陷 `CR-148-020`（P1，待裁定）**。**口径闭合说明**：`P-10` 缺口**已闭合**；**正式分位判定仍须按每档 ≥200 请求重跑 `TT-038`**（本轮为 L3 冒烟 n=3/2，**不冒充分位**）；`P-4` 仍为缺口。**未达预期项如实登记**：原预期「接线后可解释 `P-1` 残留 =592.3~1110.2 ms」**未完全达成** —— 本轮同步档实测**未计量差额仍为 745.0~1522.6 ms**（`profile_fetch` 首样本 2031 ms 已单独计量），说明除回写派发外**仍有其他未计量构成**，须继续分解（与 §6 #8 / `P-4` 同源） |
| **v1.21.0** | **2026-09-22** | **AT-OpenBase-Test / AD-OpenBase-Dev** | **性能批次收口：`TT-038` 双口径复跑 + 新增 2 项 P1 待办（`CR-148-017` 缺陷 / `CR-148-018` 口径缺口）**。① **口径**：按《非功能设计说明-v1.4.8》**v1.2.0 §1.1.3** 双口径（单飞档判功能可用性与基线时延、并发 8 档判吞吐与尾延迟，须报 `achieved_rps`/`peak_in_flight`）。② **环境修正**：专用压测实例 `8041` 按**中间件实际键名**（`RATE_LIMIT_PER_SECOND`/`RATE_LIMIT_BURST`，此前误用 `RATE_LIMIT_PER_MINUTE` 对中间件**无效**）提高限额并**以启动日志实证** + `DEBUG=false` 关闭 SQLAlchemy `echo` → **两档 429 = 0**，`peak_in_flight = 8`（C-1 解除）。③ **结果**：`TT-038` ❌ **未通过（双口径一致）**；**单飞档** ✅P-3/P-9/P-12（错误率 **0/690 = 0%**）、❌P-1/P-6/P-8；**并发 8 档** ✅**P-3 / P-11（9.317 req/s；同端点同口径基线 1.578 → 5.9×）**、❌P-1/P-6/P-8/P-9/P-12（1.45%，含 1 例 5xx）；两档 P-4/P-10 未判定；`TT-039` 维持通过。④ **未达标定性**：P-1＝**本仓缺陷**（`CR-148-017`）+ H 类环境（DPS 未启动，**分别处置**）；P-6/P-8＝**数据规模效应**（队列 140→473 行、`traces` 242→863 行，为基线 3.4×/3.6×，暴露目标值**未绑定数据规模档位**）+ 并发架构债务；P-9/P-12＝**并发架构债务**（`TD-新增-027` 未偿还：并发 ×8 仅得吞吐 **1.43×**、达理想 17.9%）。⑤ **新增 `CR-148-017`（P1，`DT-148-019`）**：画像拉取降级**无失败短路/负缓存** → DPS 不可用时**每请求固定 ≈2.04 s**（隔离探针两次运行一致；**非瞬时 `ECONNREFUSED`**）。⑥ **新增 `CR-148-018`**：`P-10` 计量接线未执行（落点 `EdgeRouterExecutor._schedule_writeback` 已定位，须 TDD + 全量回归）。⑦ **文档同步**：《性能测试记录-v1.4.8》**v1.5.0**（新增 §2.2/§4.5/§5.2/§5.3 + 发现 #9~#13 + 补登修订行 v1.2.0/v1.4.0）、《测试报告-v1.4.8》**v3.7.0**（§7 #26 + §8 性能行 + §11 v3.7.0 + 补登 v3.6.0）、《测试用例-v1.4.8》**v2.0.0**。⑧ **补登说明**：本记录 **v1.18.0 / v1.19.0 两条修订行原缺失**（其对应内容分别已由 `CR-148-014` / `CR-148-015` 两条 CR 记录承载；**不代撰行文以免失实**，仅在此留痕）。⑨ 文档版本 **v1.20.0 → v1.21.0**，状态 [Review]。依据：证据 `doc/test/evidence/v148/tt038-dual-*`、`dt148-019-*`、`perf-instance-8041-env-proof-20260922.log` |
| **CR-148-019** | **测试工装/环境缺陷：根 `tests/conftest.py` 无条件前置 pgAdmin site-packages，致 conftest 自身导入失败（退出码 4），全量回归「权威命令」不成立**（2026-09-22，`DT-148-019` 修复轮的回归验证中发现） | **① 现象**：`python -m pytest tests/unit/...`（**不加** `--confcutdir`）**退出码 4**（pytest 内部错误），无任何用例被收集。<br>**② 根因**：根 `tests/conftest.py` 为绕开本机 `.venv` 中 SQLAlchemy 2.0.25 的 `AssertionError`，**无条件**把 `D:\PostgreSQL\17\pgAdmin 4\python\Lib\site-packages` 插入 `sys.path[0]`；而该目录的 `cryptography.hazmat.bindings._rust` 在 **Python 3.10.11** 下 `DLL load failed`（**实测：不前置该目录时 `import cryptography` 正常**，其来源为 `TRAE …\tools\python\Lib\site-packages`）→ conftest 自身在 `from app.services.auth_service import …`（→ `jwt` → pgAdmin `cryptography`）阶段即 ImportError → **conftest 加载失败**。<br>**③ 影响**：① 未加 `--confcutdir=tests/unit` 的用例运行**全部无法收集**；② 既往记录的「**615 error**」实为该缺陷的下游表现（`--confcutdir` 绕开后 615 error 仍在，但性质为缺少根 conftest 夹具）；③ **不同绕行方式（`--confcutdir` / `--noconftest`）的 passed 计数不可互比**（本轮基线对照改用**同命令前后对照**）。<br>**④ 本轮处置**：**以 `--confcutdir=tests/unit` 绕过**（未改动任何 conftest，避免扩大影响面）；全量回归与基线对照均在该命令下完成。 | OpenLLM 仓 `backend/tests/conftest.py`（第 27~37 行「pgAdmin site-packages 前置」段）、`backend/tests/unit/conftest.py`；本仓《测试报告-v1.4.8》**v3.8.0** §7 #27、《OpenLLM DevLogReport》**v1.10.0** §7 第 9 项；证据 `doc/test/evidence/v148/dt148-019-regression-unit-20260922.txt`（含命令与结论行） | **✅ 已修复并验证（`v1.26.0`，2026-09-26；OpenLLM **测试工装改造**，**生产代码 0 行**，TDD 合规）**：按**行为探测**方式修复（非版本硬编码）——① **新增** `tests/_path_bootstrap.py`（**纯标准库**；`should_prepend_pgadmin(path_exists, sqlalchemy_importable)` 为**纯决策函数**：**仅当目录存在且当前解释器无法导入 `sqlalchemy` 时才前置**；`apply_pgadmin_fallback()` 为副作用入口，含 `invalidate_caches` 与导入失败残留子模块清理）；② **改造** `tests/conftest.py`：**删除**无条件 `_PGADMIN_SP` + `sys.path.insert(0, …)` 段，改为 `from tests._path_bootstrap import apply_pgadmin_fallback` 后调用；③ **未改** `tests/unit/conftest.py`（其于 v1.4.8 已按**同一缺陷类**改为**末端兜底 `append`**，本轮仅将其纳入**源码契约护栏**）。**TDD**：新增 `tests/unit/test_conftest_path_bootstrap_guard.py`（**9 例**：决策四分支 + 跳过分支**零副作用** + 注入须置首位 + 目录缺失防御 + **双 conftest 源码契约（不得出现 `insert(0, _PGADMIN_SP)`）** + 引导模块仅标准库）→ **RED `ModuleNotFoundError: tests._path_bootstrap` → GREEN 9 passed**。**权威命令恢复（决定性命中）**：`python -m pytest tests/unit --collect-only -q -p no:cacheprovider`（**不加** `--confcutdir`）→ **退出码 4 / 0 收集 ⇒ 退出码 0 / 2881 收集**。**全量回归（权威口径）**：**33 failed / 2848 passed / 0 error**（602.66 s）——对照 `--confcutdir` 基线（13 failed / 2233 passed / **615 error**）→ **`error` 由 615 → 0**（根 conftest 夹具恢复）。**残留（新登记，见 `CR-148-021`）**：failed 13 → 33（14 项为基线既有 + 其余此前**从未真正执行**、本轮首次执行后暴露 → 属**既存缺陷显性化**，非本次改动引入）。**原候选处置（① 按 Python 版本条件化前置 / ② `OPENLLM_TEST_EXTRAS` 白名单注入 / ③ 固定权威回归命令）均不再需要**（缺陷已由「行为探测按需前置」根治）；**权威回归命令自此固定为 `python -m pytest tests/unit -q -p no:cacheprovider`（不再加 `--confcutdir`）**。**注**：本项**不阻塞** `DT-148-019` 的修复结论（该结论已在同命令前后对照下取得） |
| **v1.22.0** | **2026-09-22** | **AD-OpenBase-Dev / AT-OpenBase-Test** | **`CR-148-017`（`DT-148-019`，P1）修复并验证通过 —— 画像拉取失败负缓存 + 关闭画像注入开关**。① **修复**（OpenLLM 提交 **`ad7d472`**，3 文件 `+327/-6`，**TDD 合规**）：`core/config.py` 新增 `PROFILE_FAILURE_COOLDOWN_SECONDS`（默认 30s；**0=关闭负缓存**，保留既有每请求重试语义）与 `PROFILE_INJECTION_ENABLED`（默认 True；False=完全不拉取并降级跳过）；`api/openllm_gateway.py` 新增模块级冷却状态 + `threading.Lock` + `_profile_circuit_open()` / `_mark_profile_failure()` / `_clear_profile_failure()`，`_build_profile_ctx` 改为「开关判定 → 冷却短路 → **本地上下文构造（异常不计入依赖失败）** → adapter 调用（成功清空 / 失败开启冷却）→ 空画像不算失败 → 格式化异常独立降级」。**默认行为零变化**。② **TDD**：新增护栏 `tests/unit/test_profile_fetch_negative_cache.py`（**10 例**，含「不误伤」三例）**RED 9 failed → GREEN 10 passed**；改动文件 `ruff All checks passed`。③ **L1/L2/L3**：L1 导入 OK；L2 健康 **200 / healthy / 2.14.3**；**L3 冒烟两档通过** —— 负缓存档 `profile_fetch` **2094 → 0 → 0 ms**、开关档三连 **0.0 ms**。④ **P-1 定向复测（n=60，单飞不限节流）**：本仓开销 **P50 2629.4 → 1157.9 ms（−56%）**、墙钟 P50 **3302.0 → 1970.3 ms**、`profile_fetch` **≈2037 → ≈47.7 ms（−97.7%）**。**如实登记：未达预期「≤600ms」** —— 残留未计量差额 P50 **1110.2 ms**（大于此前估的 592.3 ms），**P-1 仍未达 ≤50 ms 目标**，该残留归 **`CR-148-018`（P-10 计量缺口）** 继续追。⑤ **回归 + 基线对照**：`pytest tests/unit -q -p no:cacheprovider --confcutdir=tests/unit` → **13 failed / 2228 passed / 615 error**（新增 10 例）；`git stash`（仅本批 3 文件）同命令基线 **13 failed / 2218 passed**，**失败集合 `Compare-Object` 无差异 → 无回归**（首轮 14 failed 中的多出项经隔离重跑 3/3 与全量复跑确认为**既有 flaky**，如实登记）。⑥ **新增环境/工装缺陷登记 `CR-148-019`（P2）**：根 `tests/conftest.py` **无条件**把 pgAdmin site-packages 置于 `sys.path` 首位，其 `cryptography._rust` 在 **Python 3.10.11** 下 `DLL load failed` → **conftest 自身导入即失败（退出码 4）**，使「全量回归权威命令」不成立（本轮以 `--confcutdir` 绕过；亦解释既往「615 error」来源）→ 登记并给出条件化前置/白名单注入建议。⑦ **文档同步**：《OpenLLM DevLogReport》**v1.10.0**（第 21 批）、《性能测试记录-v1.4.8》**v1.6.0**（§6 #9 修复记录 + P-1 复测）、《测试报告-v1.4.8》**v3.8.0**（§7 #26 处置）、《测试用例-v1.4.8》**v2.1.0**；证据 `doc/test/evidence/v148/dt148-019-*`。⑧ 文档版本 **v1.21.0 → v1.22.0**，状态 [Review] |
| **CR-148-020** | **流式路径回写派发在请求路径内同步执行，`writeback_dispatch` 实测 556~728 ms（`P-10` 目标 ≤5 ms，超约 110~145×）**（2026-09-26，`CR-148-018` 接线后**首次取得 `P-10` 有效观测值**时暴露） | **① 现象（同一份证据，两路径结论相反）**：`CR-148-018` 接线后于 8041 实例冒烟（证据 `cr148-018-smoke-20260926.json`，3 同步 + 2 流式）——**同步路径** `writeback_dispatch` = **0.019 / 0.026 / 0.014 ms**（**达标**）；**流式路径** = **727.638 / 555.923 ms**（**不达标**）。<br>**② 根因（结构差异，非实现遗漏）**：**同步路径**经 `PipelineExecutor._schedule_writeback()` 以 `asyncio.create_task` **异步派发**，请求路径只付「任务创建」成本（微秒级）；**流式路径**（`api/openllm_gateway.py` 流式端点回写段）对三路回调 `await road_cb(...)` **逐个同步入队**，每路含 `WritebackStore.next_seq`（取 `max_seq`）+ `submit`（幂等 INSERT），三路串行 → SQLite 往返全部计入 `done` 事件之前的同步等待。<br>**③ 影响**：① `P-10` **流式口径不达标**（同步达标）；② 直接推迟 SSE `done` 事件，是流式档「未计量差额」的一笔大额可解释构成；③ 与 `TD-新增-027`（`async` 路由内同步 SQLite 阻塞事件循环）**同族**，但此处为**独立落点**（回写入队而非回读查询），须单列。<br>**④ 本轮未改行为（如实登记）**：把流式回写改为异步派发会改变 `routing_trace["writeback"]`（回执现于 `done` 时点即被 `_finalize_stream` 落库）的既有语义 → 属**语义变更**，须先经人工裁定，不在本轮擅自变更。 | OpenLLM 仓 `app/api/openllm_gateway.py`（流式端点回写段：`_build_writeback_callback` + 三路 `await` 入队）、`app/services/writeback_queue.py`（`next_seq` / `submit`）；本仓《OpenBase-性能测试记录-v1.4.8》**v1.7.0** §6 #14 / §6.4、《测试报告-v1.4.8》**v3.9.0** §7 #28、《测试用例-v1.4.8》**v2.2.0** §2.1 `TT-038` 第 ⑥ 项；证据 `doc/test/evidence/v148/cr148-018-smoke-20260926.json`、`cr148-018-instance-8041-20260926.log` | **✅ 已实施并验证（`v1.24.0`，2026-09-26；人工裁定采纳候选方向 ①「后台任务 + 回执另行持久化」；OpenLLM 提交 `c0d8222`，2 文件 `+538/-37`，TDD 合规）**：① **改动**：新增 `_schedule_stream_writebacks()`（请求路径只 `ensure_future` 创建后台任务 + 登记 `_pending_stream_writebacks`）、`_run_stream_writebacks()`（后台完成回调构造 + 三路入队 + 逐路回执，逐路隔离、异常不外抛）、`_persist_stream_writeback_receipt()`（**回执另行持久化**到 `traces.metadata.routing_trace.writeback`：`10 × 0.1 s` 有限等待 trace 行 → 超时放弃返回 False、写库异常仅 WARNING）；流式端点回写段改为「只派发 + 落占位」。② **回执查询语义同步定义**：`done` 时点仅落 `{"_dispatch": {"mode": "async", "status": "scheduled｜failed"}}`；**权威回执仍以回写队列表为准**（`GET /openllm/v1/writeback/receipts`，按用户隔离，**语义不变**）；trace 内三路快照改为**事后异步补齐**（队列已落盘，不丢数据）。③ **TDD**：`tests/unit/test_stream_writeback_async_dispatch.py`（**11 例**，含请求路径段/后台任务段**切分契约**）**RED 8 failed / 2 passed → GREEN 11 passed**；`ruff All checks passed`；全量回归 **14 failed / 2243 passed / 615 error**（总用例 +11＝新增护栏；多出失败 1 项为**既有 flaky**，隔离重跑 **3/3 通过**）；**定向基线对照（6 文件 / 同命令 / stash 前后）13 failed / 91 passed ＝ 13 failed / 91 passed → 新增失败 = 0**。④ **运行时（8041 L2/L3）**：**流式 `writeback_dispatch` 556~728 ms → 0.029 / 0.025 / 0.028 ms**（`P-10` **达标**）；三路回执由后台任务补齐（`accepted` + `_dispatch.mode=async`）；`done` 占位为 `scheduled`；**权威回执 200 / total=3**（`memory/rag/profile` seq=1/2/3）；**同步路径 0.025 ms 未回退**。⑤ **残留（如实登记）**：**`P-10` 正式分位判定通过（`v1.25.0` 收口）**——单飞档（0.75 req/s）与并发 8 档各同步/流式 **200 有效样本**（`errors=0` / `missing_steps=0`），回读 trace 提取 `writeback_dispatch`：**单飞档 P99 = 同步 0.036 ms / 流式 0.063 ms**、**并发 8 档 P99 = 同步 0.053 ms / 流式 0.069 ms**，**每样本均 ≤5 ms（最强口径）→ 正式判定通过**（证据 `p10-percentile-single-flight-20260926.json` / `p10-percentile-conc8-20260926.json`）；**`P-4` 仍为口径缺口**（建议随 `TD-新增-027` 偿还一并处置）；`test_writeback_degradation.py` 3 例**既有陈旧断言**（按三路回写前的返回值数量解包）本轮未改。详见《OpenBase-性能测试记录-v1.4.8》**v1.9.0** §6.5、《测试报告-v1.4.8》**v4.1.0** §7 #28；证据 `doc/test/evidence/v148/cr148-020-*`、`p10-percentile-*`。<br>**（以下为裁定前的候选方向留痕，供追溯）** ：① 后台任务 + 回执另行持久化（`done` 不再等待三路入队；配套：回执改由后台任务写 `traces` 或独立表，回执查询语义需同步定义）—— **本次采纳**；② **入队批量提交**——三路合并为单事务/单连接写入，消除三次串行往返 —— **未采纳（本轮）**；③ **`next_seq` 改「内存 + 落盘」双写**——消除逐路 `max_seq` 查询（须保证重启后 seq 不重号，与 `F-08`「重启不丢写」硬判据兼容）—— **未采纳（本轮）** |
| **v1.23.0** | **2026-09-26** | **AD-OpenBase-Dev / AT-OpenBase-Test** | **`CR-148-018`（`P-10` 计量接线）实施并验证通过；派生新缺陷 `CR-148-020`（流式回写派发同步耗时，P1 待裁定）**。① **背景**：`DT-148-019` 修复后 `P-1` 仍有 **未计量差额 P50 1110.2 ms**，`P-10` 两口径均不可判定 → 本项为**性能批次最高优先待办**。② **实施**（OpenLLM 提交 **`72fd01e`**，5 文件 `+203/-4`，**TDD 合规**）：`orchestration/executor.py::execute()` 增可选 `timeline`；三路（memory/rag/profile）回写经 `_schedule_writeback()` 派发并在调用侧**累加派发耗时**，**合计只落一条** `writeback_dispatch`（**未调度任何回写时不落步骤**，避免 0 值污染 `P-1` 的 Σ步骤）；`ExplicitOrchestrator` / `AutoOrchestrator` 透传 `timeline`；网关**同步路径**传入、**流式路径**在「构造三路回调 + 逐路入队」处补同口径计量。**计时用 `time.perf_counter()`**（`time.monotonic()` 在 Windows + Python 3.10 下实为 `GetTickCount64`、分辨率约 **15.6 ms**，不足以度量亚毫秒级派发开销），该决定由**源码契约护栏**固化。③ **TDD**：新增 `tests/unit/test_writeback_dispatch_timeline_guard.py`（**5 例**：两路径各须产出该步骤、计时须用 `perf_counter`、**三路合计只落一条**、**未调度不得落步骤**、`timeline` 可选向后兼容）→ **RED 4 failed / 1 passed → GREEN 5 passed**；改动 5 文件 `ruff All checks passed`。④ **回归**：`python -m pytest tests/unit -q -p no:cacheprovider --confcutdir=tests/unit` → **13 failed / 2233 passed / 615 error**，与 `DT-148-019` 轮基线（13 failed / **2228** passed / 615 error）**failed 与 error 数完全一致**、passed 差值 **+5 恰为新增护栏 → 无回归**（证据 `cr148-018-regression-unit-20260926.txt`）。⑤ **运行时（8041 / 编排器等价 Env / `DEBUG=false`；L2 健康 200 / healthy / 2.14.3）**：**`P-10` 首次取得有效观测值** —— **同步达标**（`writeback_dispatch` = **0.019 / 0.026 / 0.014 ms** ≤5 ms，异步派发、无同步等待）、**流式不达标**（**727.638 / 555.923 ms**）→ **派生 `CR-148-020`（P1，待裁定）**。⑥ **口径状态**：`P-10` 缺口**闭合**；**`P-4` 仍为缺口**；**`P-10` 正式分位判定仍须按每档 ≥200 请求重跑 `TT-038`**（本轮 L3 冒烟，**不冒充分位**）。⑦ **未达预期项如实登记**：原预期「接线后可解释 `P-1` 残留 =592.3~1110.2 ms」**未完全达成** —— 同步档实测未计量差额仍为 **745.0~1522.6 ms**（`profile_fetch` 首样本 2031 ms 已单独计量），说明**仍有其他未计量构成**，须继续分解（与 §6 #8 / `P-4` 同源）。⑧ **同时如实登记**：首轮流式冒烟（`max_tokens=32`）**无 `chunk` 事件** → 按既有「**空响应不回写**」语义不进回写块亦不落该步骤（**预期行为，非缺陷**），复跑 `max_tokens=200` 后正常产出。⑨ **文档同步**：《性能测试记录-v1.4.8》**v1.7.0**（新增 §6.4 + §6 #14 + §5.3 + §7）、《测试报告-v1.4.8》**v3.9.0**（§7 #28 + §11 + 状态/结论行）、《测试用例-v1.4.8》**v2.2.0**（§2.1 `TT-038` 第 ⑥ 项）、《OpenLLM DevLogReport》**v1.11.0**（第 22 批）；证据 `doc/test/evidence/v148/cr148-018-*`。⑩ 文档版本 **v1.22.0 → v1.23.0**，状态 [Review] |
| **v1.24.0** | **2026-09-26** | **AD-OpenBase-Dev / AT-OpenBase-Test** | **`CR-148-020`（P1）按人工裁定方案 ① 实施并验证通过 —— 流式回写改「后台派发 + 回执另行持久化」**。① **裁定**：采纳候选方向 ①（后台任务 + 回执另行持久化），未采「入队批量提交」与「`next_seq` 内存+落盘双写」（留痕于 `CR-148-020` 行）。② **实施**（OpenLLM 提交 **`c0d8222`**，2 文件 `+538/-37`，**TDD 合规**）：`api/openllm_gateway.py` 新增 `_schedule_stream_writebacks()`（请求路径只创建后台任务）/ `_run_stream_writebacks()`（后台完成三路入队 + 逐路回执，逐路隔离、异常不外抛）/ `_persist_stream_writeback_receipt()`（**回执另行持久化**到 `traces.metadata.routing_trace.writeback`：`10 × 0.1 s` 有限等待 trace 行，超时放弃返回 False、写库异常仅 WARNING）；流式端点回写段改为「只派发 + 落 `_dispatch` 占位」。**回执查询语义同步定义**：`done` 时点仅落 `{"_dispatch": {"mode": "async", "status": "scheduled｜failed"}}`；**权威回执仍以回写队列表为准**（`GET /openllm/v1/writeback/receipts` 语义不变）；trace 内三路快照改为**事后异步补齐**（队列已落盘，不丢数据）。③ **TDD**：新增 `tests/unit/test_stream_writeback_async_dispatch.py`（**11 例**）**RED 8 failed / 2 passed → GREEN 11 passed**；改动 2 文件 `ruff All checks passed`。④ **回归（含决定性基线对照）**：全量 `tests/unit` **14 failed / 2243 passed / 615 error**（总用例 **+11＝新增护栏**；多出失败 1 项为**既有 flaky**，隔离重跑 **3/3 通过**）；**定向基线对照（失败所在 6 文件 / 同命令 / `git stash` 前后）13 failed / 91 passed ＝ 13 failed / 91 passed → 新增失败 = 0**（证据 `cr148-020-regression-baseline-20260926.txt`）。⑤ **运行时（8041 L2/L3）**：**流式 `writeback_dispatch` = 0.029 / 0.025 / 0.028 ms**（改造前 556~728 ms → 降幅约 **2 万倍**，`P-10` **达标**）；**三路回执由后台任务补齐**（`memory/rag/profile` 均 `accepted` + `_dispatch.mode=async`）；`done` 占位为 `scheduled`；**权威回执 200 / total=3**（`memory/rag/profile` seq=1/2/3）；**同步路径 0.025 ms 未回退**。⑥ **残留（如实登记）**：**`P-10` 正式分位判定仍须按每档 ≥200 请求重跑 `TT-038`**（本轮 L3 冒烟 n=3，**不冒充分位**）；**`P-4` 仍为口径缺口**（建议随 `TD-新增-027` 偿还一并处置）；`test_writeback_degradation.py` 3 例**既有陈旧断言**（按三路回写前的返回值数量解包）本轮未改。⑦ **文档同步**：《性能测试记录-v1.4.8》**v1.8.0**（新增 §6.5 + §6 #14 状态 + §5.3 + §7）、《测试报告-v1.4.8》**v4.0.0**（§7 #28 处置 + §11 + 状态/结论行）、《测试用例-v1.4.8》**v2.3.0**（§2.1 `TT-038` 第 ⑦ 项）、《OpenLLM DevLogReport》**v1.12.0**（第 23 批）；证据 `doc/test/evidence/v148/cr148-020-*`（实例日志为本地 artifact，未入库且已脱敏）。⑧ 文档版本 **v1.23.0 → v1.24.0**，状态 [Review] |
| **v1.25.0** | **2026-09-26** | **AT-OpenBase-Test / AD-OpenBase-Dev** | **`P-10` 正式分位判定执行并通过（`TT-038` 重跑，`CR-148-020` 处置正式收口）**。① **动因**：`v1.23.0` / `v1.24.0` 均明确「`P-10` 正式分位判定仍须按每档 ≥200 请求重跑 `TT-038`」（此前仅 L3 冒烟 n=3/2，**不冒充分位**）→ 本轮执行正式判定。② **执行**（专用实例 **8041** / 编排器等价 Env / `DEBUG=false` / `RATE_LIMIT_PER_SECOND=10000`；脚本 `p10-percentile-20260926.py`，**禁用 HTTP keep-alive** 规避并发档服务端关连接所致 `RemoteProtocolError`）：**单飞档**（0.75 req/s）与**并发 8 档**各**同步/流式 200 有效样本**，回读 trace 提取 `writeback_dispatch` 计算 P50/P90/P95/P99。③ **结果**：**单飞档 P99 = 同步 0.036 ms / 流式 0.063 ms**；**并发 8 档 P99 = 同步 0.053 ms / 流式 0.069 ms**；两档四路径 **errors=0 / missing_steps=0 / 每样本均 ≤5 ms（最强口径）→ `P-10` 正式判定通过**，`CR-148-020` 处置**正式收口**；**残留**：`P-4` 计量缺口（建议随 `TD-新增-027` 偿还一并处置）+ `test_writeback_degradation.py` 3 例既有陈旧断言。④ **文档同步**：《性能测试记录-v1.4.8》**v1.9.0**（§6.4/§6.5/§6 #14/§5.3/§7 状态更新 + 修订行）、《测试报告-v1.4.8》**v4.1.0**（§7 #28 处置收口 + 修订行）、《测试用例-v1.4.8》**v2.4.0**（§2.1 `TT-038` 第 ⑧ 项）；证据 `doc/test/evidence/v148/p10-percentile-single-flight-20260926.json`、`p10-percentile-conc8-20260926.json`、`p10-percentile-20260926.py`（脚本）。⑤ 文档版本 **v1.24.0 → v1.25.0**，状态 [Review] |
| **CR-148-021** | **权威回归口径下 33 项用例失败待逐项分诊（`CR-148-019` 修复的**直接副产物**：此前 615 项因夹具缺失从未真正执行）**（2026-09-26） | **① 现象**：`CR-148-019` 修复后权威命令（**不加** `--confcutdir`）恢复 → **33 failed / 2848 passed / 0 error**（602.66 s）；对照旧 `--confcutdir` 基线 **13 failed / 2233 passed / 615 error** → **`error` 615 → 0**、**failed 13 → 33**。<br>**② 归因（两条，已证）**：**(a)** 其中 **14 项为基线既有失败**（`test_real_contract_memory`×4、`test_real_contract_rag`×2、`test_s4_t14_verify_env`×2、`test_s4_t5_prefix_normalize`×2、`test_writeback_degradation`×3、`test_component_pipeline_shared`×1）；**(b)** 其余来自此前处于 `615 error`（夹具缺失、**从未真正执行**）的用例，本轮首次执行后暴露 → 属**既存测试/实现缺陷的显性化**，**非 `CR-148-019` 引入**（该改动仅涉测试引导期 `sys.path` 决策，未触及任何被测模块，跳过分支「零副作用」另有护栏锁定）。<br>**③ 已识别样本（部分）**：`test_model_router_wiring`（`test_model_auto_no_healthy_candidate_1004` 实测 **500** 而非 404；`test_model_auto_select_model_receives_real_contract` 取到 `None`）、`test_v213_gateway_ext::test_bypass_marker_injected`（**500**）、`test_session_scope_alignment`×2（`AttributeError: … has no attribute 'astext'`）、`test_stream_optimization`×2（错误码 `1004` vs 预期 `2001`；`close` 未被调用）、`test_writeback_degradation`×3（**既有陈旧断言**：按三路回写**前**的返回值数量解包）。<br>**④ 处置建议**：逐项分诊为「**测试陈旧 / 环境前置 / 真实缺陷**」三类 —— 测试陈旧项随所属批次修正；环境前置项登记 H 类；真实缺陷项按 Step 3 回退修复。**在分诊完成前，权威回归的失败基线不可用于「无回归」判定**（此前多轮「failed 数与基线一致 ⇒ 无回归」的结论均建立于 `--confcutdir` 绕行口径，**口径已变，须重算基线**）。 | OpenLLM 仓 `backend/tests/`（`conftest.py` 修复后暴露）；本仓《OpenBase-测试回溯对比审计报告-v1.4.8》**v1.1.0** §9.2；证据 `doc/test/evidence/v148/cr148-019-authoritative-full-20260926.txt` | **待分诊（P2；不阻塞 `CR-148-019` 闭环）**：`CR-148-019` 的验收目标（**权威回归命令成立**）已达成；本项为其**副作用显性化**，须单列分诊。**注**：33 项中**至少 3 项**为已登记既有陈旧断言（`test_writeback_degradation.py`），其余需按 ④ 三类归位后再定级。**［`v1.31.0` 分诊完成］**：**33 项已逐项归位**（互斥穷尽，合计 33）—— **A 测试陈旧 20 项**（含 401 `detail` 断言过期 9、`_resolve_memory_metadata` 已删符号 3、`writeback_degradation` 陈旧解包 3、`model_router_wiring` 打桩因 `lru_cache` 单例失效 2、`conversations_api` 替身未对齐 `metadata_` 1、`v213_gateway_ext` 打桩 4 元组 vs 实现 5 元组 1、流式 `2001 vs 1004` 1）、**B 环境前置（H 类）5 项**（本地 `.env` 置真 `OPENLLM_OPENMEMORY_REAL` / `OPENLLM_OPENRAG_REAL` / `OPENLLM_DPS_REAL`，与 dev 默认期望冲突）、**C 真实缺陷 2 项（同源）**（`conversation_service.py:254` 使用 SQLAlchemy 2.x **已移除**的 `.astext` → 带 `session_id` 的历史筛选必抛 `AttributeError`）→ **新增 `CR-148-026` / `DEF-BE-148-013`（P1）**、**D flaky 2 项**（`test_joinedload_asserts` 权威轮失败、本轮**同命令复跑 4/4 通过**，不复现）、**E 待复核 4 项**（须 OpenLLM 侧确认设计意图：流式 `2001/1004/5001` 权威错误码、`_finalize_stream` 是否有意不 `close`、writeback `namespace_prefix` 是「有意交由下游按头」还是「K17 未接线」）。**分类结论**：真实缺陷**仅同源一处**（占 6.1%），**`CR-148-021` 不改变 Step 4 判定主因**；详见**分诊报告** `doc/test/evidence/v148/cr148-021-triage-20260926.md` |
| **v1.26.0** | **2026-09-26** | **AT-OpenBase-Test / AD-OpenBase-Dev** | **`CR-148-019`（P2 测试工装）修复并验证通过 —— 权威回归命令恢复；派生新分诊项 `CR-148-021`**。① **根因**：根 `tests/conftest.py` **无条件**前置 pgAdmin site-packages，其 `cryptography` 在 **Python 3.10.11** 下**遮蔽**解释器可用版本 → `import jwt` 失败 → **conftest 自身导入失败（退出码 4、0 用例被收集）**，且既往「615 error」亦源于此。② **处置**（OpenLLM **测试工装改造**，**生产代码 0 行**，TDD 合规）：新增 `tests/_path_bootstrap.py`（**行为探测**：仅当目录存在**且**当前解释器无法导入 `sqlalchemy` 时才前置）+ 改造 `tests/conftest.py` 调用之；**未改** `tests/unit/conftest.py`（其已于 v1.4.8 按同一缺陷类改为末端兜底 `append`，本轮仅纳入源码契约护栏）；新增护栏 `tests/unit/test_conftest_path_bootstrap_guard.py`（**9 例**，含**双 conftest 源码契约**）**RED 1 error → GREEN 9 passed**。③ **验证（决定性命中）**：**退出码 4 / 0 收集 ⇒ 退出码 0 / 2881 收集**；全量回归（权威口径）**33 failed / 2848 passed / 0 error** vs 基线（13 failed / 2233 passed / **615 error**）→ **`error` 615 → 0**。④ **派生 `CR-148-021`（P2 待分诊）**：failed 13 → 33（14 项基线既有 + 其余此前**从未真正执行**者首次执行后暴露）→ 属**既存缺陷显性化**，非本次改动引入；**分诊完成前，权威失败基线不可用于「无回归」判定**。⑤ **文档同步**：《测试回溯对比审计报告-v1.4.8》**v1.1.0**（§9.2 闭合项 ① 标记完成）、《OpenLLM-…DevLogReport》**v1.13.0**（第 24 批）；证据 `doc/test/evidence/v148/cr148-019-*`。⑥ 文档版本 **v1.25.0 → v1.26.0**，状态 [Review] |
| **CR-148-025** | **`P-4` 计量接线与双档判定（审计闭合项 ②；`P-4` 口径缺口闭合 → 单飞档达标 / 并发 8 档未达标）**（2026-09-26） | **① 背景**：`P-4`（流式**首包本仓额外开销** P95 ≤100 ms）此前**无对应 `timeline` 步骤**、无法逐样本分离（《性能测试记录-v1.4.8》§6 #2 口径缺口）→ 审计报告「闭合项 ②」待办。<br>**② 接线**（OpenLLM 生产 1 文件 `api/openllm_gateway.py`，**TDD 9 例**，见《OpenLLM DevLogReport》第 25 批）：新增常量 `SSE_FIRST_PACKET_STEP` + `_mark_sse_first_packet_start`（**保留最早**时刻，最贴近「请求进入」）+ `_append_sse_first_packet_step`（**未打点不落步骤**，防 0 值污染 Σ步骤）；**认证依赖处打点**（应用层最早位置，覆盖鉴权）→ 流式端点在 `yield … event: routing` **之前**落 `{"step":"sse_first_packet","ms":…}`；计时用 `perf_counter`。<br>**③ 单飞档判定（v1.10.0，达标）**：专用实例 8041 / 编排器等价 Env / `DEBUG=false` / `RATE_LIMIT_PER_SECOND=10000`；脚本 `p4-first-packet-20260926.py`（禁 keep-alive）：**0.75 req/s / n=200 有效样本**（`errors=0` / `missing_steps=0` / `cache_hits=0`）→ **P50 / P90 / P95 / P99 = 8.0 / 36.0 / 40.0 / 53.0 ms ⇒ P95 40 ms ≤100 ms 达标**（max 121 ms，超限 ≤2 例 <1%，**不宣称每样本均 ≤100 ms**）。<br>**④ 并发 8 档补测（v1.11.0，未达标）**：并发 8 / 不限节流 / n=200 / `peak_in_flight=8` / `achieved_rps=0.7` / `errors=0` / `missing_steps=0`；**延迟回读口径 P95 189.0 ms**（流式阶段不回读 trace，回读负载与测量窗口分离）、交织口径 **223.0 ms**，P50 37.0 / P90 128.0 / **P99 1150.0** ms → **两口径均 ＞100 ms ⇒ 未达标**；定性＝与 `TD-新增-027`（并发下服务端串行化，`async` 路由内同步 SQLAlchemy/SQLite 阻塞事件循环）**同源，非新缺陷**，偿还后复测。 | OpenLLM 仓 `app/api/openllm_gateway.py`、`tests/unit/test_sse_first_packet_timeline_guard.py`；本仓《OpenBase-性能测试记录-v1.4.8》**v1.10.0 / v1.11.0**（§4 P-4 行 / §5 判定表与双口径汇总 / §5.3 结论 / §6.5 残留② / §7 第 2b·3 项 / §8 修订行）；证据 `doc/test/evidence/v148/p4-first-packet-20260926.py`、`p4-first-packet-smoke-20260926.json`、`p4-first-packet-single-flight-20260926.json`、`p4-first-packet-conc8-20260926.json`（延迟回读）、`p4-first-packet-conc8-interleaved-20260926.json`（交织对照） | **✅ 已实施并双档判定（`v1.27.0`，2026-09-26）**：`P-4` 口径缺口**闭合**；**单飞档达标 / 并发 8 档未达标**（归 `TD-新增-027`，偿还后复测）；`TT-038` 并发档未达标项由 5 → 6，Step 4 判定维持「不通过」。**［`v1.28.0` 追记］审计闭合项 ② 已闭环**（《OpenBase-测试回溯对比审计报告-v1.4.8》**v1.2.0** §9.2 ②）；**并发档未达标项已并入 `TD-新增-027`**（《技术债务总表》**v0.7.1** 描述/影响范围/偿还计划同步补记，**不新增债务、计数不变**：待偿还 17 / 总计 27） |
| **CR-148-026** | **`DEF-BE-148-013`（P1 产品缺陷，OpenLLM 侧）：使用 SQLAlchemy 2.x 已移除的 `.astext` → 带 `session_id` 的会话历史筛选必抛 `AttributeError`**（2026-09-26，来源：`CR-148-021` 分诊 C 类） | **① 现象**：权威回归中 `tests/unit/test_session_scope_alignment.py` ×2 失败 —— `AttributeError: Neither 'BinaryExpression' object nor 'Comparator' object has an attribute 'astext'`。<br>**② 定位**：`app/services/conversation_service.py:254`（`get_conversation_messages` 的会话筛选分支）—— `ConversationMessage.metadata_[METADATA_SESSION_ID].astext == str(session_id).strip()`。**根因**：`JSON` 比较器的 **`.astext` 在 SQLAlchemy 2.x 已移除**（2.0 起应使用 `.as_string()` / `.as_integer()` 等，或 `func.json_extract(...)`）。**对照**：OpenBase 侧同类筛选（`DEF-BE-148-007` 修复）已采用参数化 `json_extract`，未使用该 API。<br>**③ 影响面**：凡**带 `session_id`** 调用会话消息列表 → 该分支必抛异常（HTTP 500）；连带**按会话筛选的历史段注入依据**不可用；与 `TT-020`（历史段注入）/ `session_scope` 隔离语义相邻。<br>**④ 分类依据**：`CR-148-021` 分诊报告 §3 C 类（含源码逐行核对；非测试陈旧 —— 该 API 无对应实现分支可回退）。 | OpenLLM 仓 `backend/app/services/conversation_service.py:254`；本仓《CR-148-021 分诊报告》`doc/test/evidence/v148/cr148-021-triage-20260926.md` §3 C 类 / §4；权威基线证据 `doc/test/evidence/v148/cr148-019-authoritative-full-20260926.txt`（第 253~254 行） | **待修复（P1，须回退 Step 3）**：① 修复建议 —— `.astext` → `.as_string()`（或 `func.json_extract(ConversationMessage.metadata_, METADATA_SESSION_ID) == str(session_id).strip()`）；② **须 TDD 护栏 + 权威口径全量回归**（`pytest tests/unit`，**不加** `--confcutdir`）；③ 修复后复跑本分诊 C1~C2 与权威全量（预期 failed 33 → 31）。**门禁影响**：新增 **P1 产品缺陷 1 项未闭环** → Step 4「不通过」结论不变且更为充分；须在 Step 5 准入前闭环。**［`v1.32.0` 已修复并验证］**：① **改动**（OpenLLM 提交 **`692ca6d`**，生产 1 文件 + 护栏 1 文件，`+75/-1`，**TDD 合规**）：`.astext` → **`.as_string()`**（另补注释说明依据）；**双方言编译实测** SQLite `JSON_EXTRACT(metadata, '$."session_id"')`、PostgreSQL `CAST((metadata ->> 'session_id') AS VARCHAR)`（语义等价）。② **定点取证（为何此前未暴露）**：在 **pytest 会话内**以临时探针确证 `col.type = JSON`、`comparator.__module__ = sqlalchemy.sql.sqltypes`、`hasattr(astext) = False`、`hasattr(as_string) = True`；而**独立脚本内同一属性解析为 JSONB（仍带 `astext`）** → **离线探测不足以复现**，必须在测试会话内取证（探针用后即删）。③ **TDD（新增 1 文件 4 例）**：`tests/unit/test_session_filter_json_api_guard.py` —— 源码契约（不得含 `.astext`）/ 修复形态（须用 `.as_string()`）/ **全仓零残留**（`app/` 内 `.astext` = 0）/ 双方言可编译 → **RED（契约 2 例失败）→ GREEN**。④ **验证**：定向 **18 项全绿**（`test_session_scope_alignment` 由 **12 passed / 2 failed → 14 passed**）；**权威口径全量回归** `python -B -m pytest tests/unit -p no:cacheprovider -q` → **31 failed / 2863 passed / 0 error**（506.74 s），对照 `CR-148-019` 轮基线 **33 / 2848 / 0** → **failed −2（正是本例 2 例）、passed +15**（本次护栏 4 + 第 25 批护栏 9 + 本例转通过 2），收集数 **2881 → 2894**；**静态质量**：新护栏 `ruff All checks passed`、`conversation_service.py` 20 条**均为既有欠账**（与 HEAD 基线同为 20 条）、**改动行零告警**。⑤ **门禁影响（回收）**：**P1 产品缺陷未关闭数 1 → 0** → 审计报告 §2 判据 3 恢复「✅ 基本满足」、§9.2 ⑨ 标记已完成；证据 `doc/test/evidence/v148/cr148-026-regression-unit-20260926.txt`；见《OpenLLM DevLogReport》**v1.15.0**（第 26 批） |
| **v1.27.0** | **2026-09-26** | **TE-OpenBase-Dev / AT-OpenBase-Test** | **`P-4` 计量接线并完成双档判定（审计闭合项 ② 闭环）—— 单飞档达标 / 并发 8 档未达标（归 `TD-新增-027`）**。① **接线**（OpenLLM 提交见《DevLogReport》第 25 批 / `openllm_gateway.py`，生产 1 文件，**TDD 9 例**）：`SSE_FIRST_PACKET_STEP` + 认证依赖打点（保留最早时刻）+ 流式端点 `yield … event: routing` 前落步骤（未打点不落、重复打点保留最早、计时用 `perf_counter`）→ `P-4`（SSE 首包本仓额外开销 P95 ≤100 ms）**可逐样本判定**，口径缺口闭合。② **单飞档判定（v1.10.0，达标）**：8041 / 0.75 req/s / **n=200 有效样本**（`errors=0` / `missing_steps=0` / `cache_hits=0`）→ **P50 / P95 / P99 = 8.0 / 40.0 / 53.0 ms ⇒ 达标**（max 121 ms，超限 ≤2 例 <1%，不宣称每样本均 ≤100 ms）。③ **并发 8 档补测（v1.11.0，未达标）**：并发 8 / 不限节流 / n=200 / `peak_in_flight=8` / `achieved_rps=0.7` / `errors=0` / `missing_steps=0` → **P95 = 189.0 ms（延迟回读口径）/ 223.0 ms（交织口径）**，P50 37.0 / P99 1150.0 ms，**两口径均 ＞100 ms ⇒ 未达标** → 与 `TD-新增-027`（并发下服务端串行化）**同源，非新缺陷**，偿还后复测。④ **工装增强（如实登记）**：`p4-first-packet-20260926.py` 增 `--concurrency` / `--defer-readback` —— **延迟回读口径**把回读 trace 的 DB 负载与流式测量窗口分离（交织口径作对照），避免回读污染「本仓开销」度量。⑤ **结论要素**：`TT-038` 并发档未达标项 5 → 6；Step 4 判定维持「不通过」；`P-4` 单飞档达标为**独立判定**（不再并入 `TD-新增-027` 偿还）。⑥ **文档同步**：《性能测试记录-v1.4.8》**v1.10.0 / v1.11.0**；证据 `doc/test/evidence/v148/p4-first-packet-*`。⑦ 文档版本 **v1.26.0 → v1.27.0**，状态 [Review] |
| **v1.28.0** | **2026-09-26** | **AU-OpenBase-Test / TE-OpenBase-Dev** | **闭环复核轮（`CR-148-025` 审计闭合项 ② 闭环 + `TD-新增-027` 债务证据补记）—— 全量文档一致性同步，无新增缺陷、无计数变化**。① **复核对象**：《OpenBase-测试回溯对比审计报告-v1.4.8》**§9.2 闭合项 ②**（`P-4` 计量接线）—— 依据《性能测试记录-v1.4.8》**v1.10.0 / v1.11.0**、本记录 **`CR-148-025`** 与 4 份证据 JSON，**独立复核通过并标记「已完成」**（审计报告升 **v1.2.0**）。② **债务证据补记**：《技术债务总表》**v0.7.1** —— `TD-新增-027` 的 **描述**（直接后果增列 `P-4`「单飞达标 / 并发不达标」）、**影响范围**（增列 `P-4` 首包尾延迟）、**偿还计划**（复测项增列 `P-4`）同步更新；**不新增债务、表头计数不变**（待偿还 17 / 挂起 1 / 偿还中 0 / 已偿还 9 / **总计 27**）。③ **文档一致性同步（本轮全部要素）**：《测试报告-v1.4.8》**v4.2.0**（§3 性能行 / §7 #27 闭环 / #28 残留收口 / **#29 新增** / §11 段 / 修订行，并**补登遗漏的 v4.1.0 修订行**）、《测试用例-v1.4.8》**v2.5.0**（§2.1 `TT-038` 第 ⑨ 项 / §6 性能行 / 状态栏 / 更新日期 / 修订行）、《技术债务总表》**v0.7.1**、《测试回溯对比审计报告-v1.4.8》**v1.1.0 / v1.2.0**、`.devflow/state.json`（`cr148025SseFirstPacketMetering` 增补 + 批次 gate 剩余项重排）。④ **结论**：`CR-148-025` **全链闭环**（接线 → 双档判定 → 审计复核 → 债务归集 → 文档同步）；**Step 4 判定维持「不通过」**（`TT-038` 未达标项 **6 项**）；**`CR-148-021`（P2 待分诊）为下一处置项**。⑤ 文档版本 **v1.27.0 → v1.28.0**，状态 [Review] |
| **v1.29.0** | **2026-09-26** | **TE-OpenBase-Dev / AT-OpenBase-Test** | **Step 4 余项补跑（`TT-032` / `TT-037`）执行并判定 —— 未执行项由 4 项收敛为 2 项；无新增缺陷、无计数变化、无新增债务**。① **`TT-032`（上一版本失败项 / 跳过项复测）✅ 通过（有限口径）**：`TT-147-009` 四仓 R-384 专项单测**逐仓复跑 36/36**（DPS 10 / OpenLLM 7 / OpenMemory 12 / OpenRAG 7，`failed=0`、`errors=0`，与 v1.4.7《测试报告》§7.7 基线**逐仓逐例一致**；驱动 `tt032-four-repo-rerun-20260926.py`）；`TT-147-005` 可运行责任面 —— OpenLLM 网关「非受信来源**不采用**入站 `X-Request-Id`」实测 **5/5**；`TT-147-004` OpenRAG 应用日志 JSONL 契约以**仓内实现静态复核**留证（`src/openrag/main.py:53`）；v1.4.7 跳过项（T3a/T4/性能，范围外声明）由本版本 `TT-028`/`TT-029`/`TT-041~044`/`TT-038`·`TT-039` 承接。**受限项如实登记（不判不通过，非缺陷）**：受信来源复用入站 id、四仓日志原文命中 100%、`X-Request-Id` 响应回带、OpenRAG JSONL 运行态 —— 须 **OpenBase 代理 8001 + DPS / OpenRAG + 采集目录**运行态（本环境未运行）；**关联 id `req-{12hex}` 不经 HTTP 暴露**，不得以 HTTP 观测替代。② **`TT-037`（输入校验与注入防护）✅ 通过**：**28 探针 / 0 个 5xx / 0 不通过项** —— 无 5xx（28/28）、**无堆栈外泄**（10 类关键字零命中）、校验类探针 **4xx 齐备**（422×7 / 404×3 / 405×1 / 401×3）、**回执查询注入串字面量参数化**（`total=0`，无过滤基线 `total=200`）、**Header 注入不回显**。**工具层如实登记（非产品缺陷）**：原始 CRLF 头值由 `httpx` **发送前**拦截（未到达服务端）→ 以字面量 `%0d%0a` 替代；`D3` 改用**专用注入串**与其他探针解耦（首轮 `total=1` 经甄别系命中他探针自身写入的回执行，属**字面量精确匹配的正确行为**，已更正）。③ **结论要素**：Step 4 **未执行项由 4 项收敛为 2 项**（`TT-025`/`TT-026` 前端类、`TT-040` 可访问性 —— 均需前端工程/服务）；**`TT-038` 与 Step 4 判定不变**（`TT-038` ❌ 未通过；审计仍判「不允许进入 Step 5」）。④ **文档同步**：《测试报告-v1.4.8》**v4.3.0**（§3 第 7/10/14 行 / §7 **#30** / §11 段 / 状态行 / 修订行）、《测试用例-v1.4.8》**v2.6.0**（§2.1 `TT-032`/`TT-037` 终态 + §6 两行 / 状态行 / 修订行）、《测试回溯对比审计报告-v1.4.8》**v1.3.0**（§9.2 闭合项 ⑤ 闭环 + **两项口径更正**：`TT-044` 滞后口径更正、§9.1 理由 1 收敛为 3 项）、`.devflow/state.json` 增补；证据 `doc/test/evidence/v148/tt032-prev-version-retest-20260926.{py,json}`、`tt032-four-repo-rerun-20260926.{py,json}`、`tt037-injection-guard-20260926.{py,json}`。⑤ 文档版本 **v1.28.0 → v1.29.0**，状态 [Review] |
| **v1.30.0** | **2026-09-26** | **DA-OpenBase-Dev / AU-OpenBase-Test** | **性能目标补「数据规模档位」（审计闭合项 ③）—— 设计文档升版为草案，待人工批准；无新增缺陷、无计数变化**。① **动因（发现 #13）**：P-6 / P-8 / P-9 目标值**未绑定数据规模** → 同端点实测值随库内行数变化（队列 **140 → 473 行**：P-6 P50 **112.6 → 132.1 ms**；`traces` **242 → 863 行**：P-8 P95 上升）→ **跨规模不可互比、结论可随规模翻转**。② **产出**：《非功能设计说明-v1.4.8》**v1.2.0 → v1.3.0** 新增 **§1.1.2a「数据规模档位」** —— **S1（≤500 行）/ S2（501–5,000 行）/ S3（5,001–50,000 行，P-7 以 1e4 行为代表）/ S4（>50,000 行，本版不设门禁）**；**各档沿用 §1.1.2 同一目标值（不随规模放宽）**；三条强制判定规则（结论须注明档位与实际行数、基线对比须同档位、换档须复测）；**文档状态 [Approved] → [Review]（待人工批准；v1.2.0 内容仍为已批准基线）**。③ **如实登记（不构成放宽）**：绑定档位后 **P-6（=S1）❌ 未达标（S1 内即超限，140 行基线亦超）、P-8（=S2）❌ 未达标**、**P-9（=S1）✅ 达标、P-7（=S3）✅ 达标** → **无任何既有结论被翻转**。④ **同步**：《性能测试记录-v1.4.8》**v1.13.0**（§5.2 档位说明追记 + §7 第 4 项改「草案已产出（待批准）」+ 修订行）、《测试回溯对比审计报告-v1.4.8》**v1.4.0**（§9.2 闭合项 ③ 标记「草案已产出，待人工批准」+ §1.2 输入版本 + §9.3 进度）、`.devflow/state.json` 增补。⑤ **门禁**：③ **须人工批准后方视为闭环**；**Step 4 判定与「不允许进入 Step 5」结论不变**（`TT-038` ❌ 未通过）。⑥ 文档版本 **v1.29.0 → v1.30.0**，状态 [Review] |
| **v1.31.0** | **2026-09-26** | **AT-OpenBase-Test / TE-OpenBase-Dev** | **`CR-148-021` 分诊完成（33 项逐项归位）—— 新增 1 项 P1 产品缺陷 `CR-148-026` / `DEF-BE-148-013`（同源一处）**。① **分诊依据**：权威基线证据 `cr148-019-authoritative-full-20260926.txt`（33 failed / 2848 passed / 0 error）+ **本轮复跑取证**（`test_joinedload_asserts` / `test_stream_optimization` / `test_v213_gateway_ext` 共 39 项 → **37 passed / 2 failed**）；**互斥穷尽，合计 33**。② **归位结果**：**A 测试陈旧 20 项**（401 `detail` 断言过期 9 = `test_gateway_401_format`×7 + `test_coverage_boost_v2112`×2；`_resolve_memory_metadata` 已删符号 3；`writeback_degradation` 陈旧解包 3；`model_router_wiring` 打桩因 `lru_cache` 单例失效 2；`conversations_api` 替身未对齐 `metadata_` 1；`v213_gateway_ext` 打桩 4 元组 vs 实现 5 元组 1（**本轮取栈确证** `ValueError: not enough values to unpack (expected 5, got 4)`）；流式 `2001 vs 1004` 1）、**B 环境前置 5 项**（本地 `.env` 置真三 REAL 开关）、**C 真实缺陷 2 项（同源）**、**D flaky 2 项**（`test_joinedload_asserts` 本轮同命令**复跑通过、不复现**）、**E 待复核 4 项**（流式权威错误码 / `_finalize_stream` 是否不 `close` / writeback `namespace_prefix` 归属）。③ **新增缺陷**（**P1**）：`conversation_service.py:254` 使用 **SQLAlchemy 2.x 已移除**的 `.astext` → 带 `session_id` 的会话历史筛选**必抛 `AttributeError`**（HTTP 500）→ 登记 **`CR-148-026` / `DEF-BE-148-013`**，**须回退 Step 3 修复**（TDD + 权威口径全量回归；预期 failed 33 → 31）。④ **门禁影响**：**P0/P1 缺陷新增 1 项未闭环** → Step 4「不通过」结论**不变且更为充分**；`CR-148-021` 的「副作用显性化」定性成立（**真实缺陷仅占 6.1% 且同源**）。⑤ **文档同步**：分诊报告 `doc/test/evidence/v148/cr148-021-triage-20260926.md`（新建）、《测试报告-v1.4.8》**v4.4.0**（§7 #31 + §11 + 修订行）、《测试回溯对比审计报告-v1.4.8》**v1.5.0**（§7 P1/P2 关闭情况 + §9.2 ⑧ 观察项 + 修订行）、`.devflow/state.json` 增补。⑥ 文档版本 **v1.30.0 → v1.31.0**，状态 [Review] |
| **v1.32.0** | **2026-09-26** | **TE-OpenBase-Dev / AD-OpenBase-Dev** | **`CR-148-026` / `DEF-BE-148-013`（P1）修复并验证通过 —— 回退 Step 3 执行（OpenLLM 侧），P1 产品缺陷未关闭数回收为 0**。① **改动**（OpenLLM 提交 **`692ca6d`**，生产 1 文件 + 护栏 1 文件，`+75/-1`，**显式路径** git add、**TDD 合规**）：`app/services/conversation_service.py::get_conversation_history` 的会话筛选分支 `.astext` → **`.as_string()`**（补注释说明依据）。② **定点取证（如实登记「为何此前未暴露」）**：**pytest 会话内**探针确证该列解析为 `sqlalchemy.JSON`（`comparator.__module__ = sqlalchemy.sql.sqltypes`、`hasattr(astext) = False`、`hasattr(as_string) = True`）；而**独立脚本内同一属性解析为 JSONB（仍带 `astext`）** → **离线探测不足以复现**，须在测试会话内取证（探针用后即删，未入库）。③ **TDD**：新增 `tests/unit/test_session_filter_json_api_guard.py`（**4 例**：源码契约不得含 `.astext` / 修复形态须用 `.as_string()` / **全仓零残留**（`app/` 内 `.astext` = 0）/ 双方言可编译，SQLite `JSON_EXTRACT` 与 PostgreSQL `->>`+CAST）→ **RED（契约 2 例失败）→ GREEN**。④ **验证**：定向 **18 项全绿**（`test_session_scope_alignment` **12 passed / 2 failed → 14 passed**）；**权威口径全量回归 31 failed / 2863 passed / 0 error**（506.74 s），对照 `CR-148-019` 轮基线 **33 / 2848 / 0** → **failed −2（正是本例）、passed +15**（本次护栏 4 + 第 25 批护栏 9 + 转通过 2）、收集数 **2881 → 2894**；静态质量：新护栏 `ruff All checks passed`、被改文件 **20 条均为既有欠账**（与 HEAD 基线同为 20 条）、**改动行零告警**。⑤ **门禁回收**：**P0/P1 产品缺陷未关闭数 1 → 0** → 《测试回溯对比审计报告-v1.4.8》§2 判据 3 恢复「✅ **基本满足**」、§3.1 `DEF-BE-148-013` 状态改「✅ 已闭环」、§7 P1 改 **0**、§9.2 ⑨ 标记「✅ 已完成」；**Step 4 判定仍「不通过」**（主因不变：`TT-038` ❌ + 前端类 `TT-025`/`TT-026`、可访问性 `TT-040` 未执行）。⑥ **同步**：《测试报告-v1.4.8》**v4.5.0**（§7 #31 处置回填 + §11 段 + 结论行/修订行）、《测试回溯对比审计报告-v1.4.8》**v1.6.0**、《OpenLLM DevLogReport》**v1.15.0**（第 26 批，含第 24/25 批补登）、`.devflow/state.json` 增补；证据 `doc/test/evidence/v148/cr148-026-regression-unit-20260926.txt`。⑦ 文档版本 **v1.31.0 → v1.32.0**，状态 [Review] |
| **v1.33.0** | **2026-09-26** | **TE-OpenBase-Dev / AT-OpenBase-Test** | **本轮迭代（智能体对话全链路）端到端跑通 —— 自主定位并修复 7 项缺陷（DEF-BE-148-014 ~ 020）+ 1 项环境配置缺口；端到端验收判据 H1~H9 全绿**。① **目标**：「智能体对话经 OpenLLM 自动对接 DPS / 记忆 / 知识库并科学装配上下文投喂 LLM 的完整全流程跑通实用」（用户 /goal 指令，含「自行按目标修正完成」授权）。② **缺陷与根因归纳**（详见 §4A.1）：**本轮失败不是单点 bug，而是三条跨仓链路从未接线** —— **(i) 受信出站头（S4-T3 K15）**：`OpenRAGClient/OpenMemoryClient/DPSClient` 的 `set_outbound_headers` **全仓 0 处调用** → 下游只收 `X-API-Key`（无受信来源、无主体域）→ OpenRAG 判 `POST /query/retrieve` 为**匿名写 403**、DPS 按非受信来源**忽略**身份头（401）；**(ii) M2 数据面隔离键**：`resolve_tenant_request_scope` 第三返回值被 `_` 丢弃且 `RequestContext` 无该字段 → 出站**恒不发 `X-Tenant-ID`** → 集合**列举**与**检索**落入**不同租户域**；**(iii) 角色码归一**：本地码 `platform_admin` 原样透传 → 下游 `unknown_role` **403 fail-closed**。三者叠加使记忆 / 知识库 / 画像**全链路 fail-closed**，而 OpenRAG 侧白名单缺口使其**先表现为 403**、掩盖了更上游断链。另 4 项：内置 RAG 租户过滤**列名错误**（`organization_id` → `tenant_id`，**恒空结果静默失效**）、组件路由**胜者通吃**使记忆信号抑制知识库信号（知识库已自动对接却被整段丢弃）、auto 模式**知识库未自动对接**（R002 需 `kb_id`）、语义缓存**准入未排除上下文相关请求**（相似提问命中缓存 → 装配被整体旁路）、本仓 `llm_upstream_timeout=20.0` **过窄**使「上游正常但较慢（19~27s）」被判 **SYS_502**。③ **修复与验证**：OpenLLM 仓提交 **`bd4cb0c`**（15 文件 `+1616/-65`，显式路径，**TDD 合规**：5 个新护栏文件 + 1 文件按统一装配口径更正断言）；本仓改动 `openbase/settings.py`（上游预算 20.0 → **120.0**）与 `scripts/service-orchestrator.ps1`（OpenRAG 受信来源白名单补入编排出站来源）；**因果探针**取证（固定其余头仅切换 `X-Tenant-ID`：无 → 400/403；有 → 200）；定向回归 **132 passed / 0 failed**（9 个相关测试文件）。④ **端到端验收（PASS）**：`path=C`、`executed=['memory','rag','llm']`、**`degraded=[]`**、`rag_source=external`、`kb_id_source=external`、**`segment_tokens.rag=478` / `contexts_tokens=478` / `rag.injected_items=1`**、`attribution_a.used_ratio=1.0`、端到端 **19.2s**；决策原因实证**信号并集**（R001+R002+R004 同时保留）；回答正文**显式引用知识库样本**（`AGENT-CTX-KB-20260926`）→ 证明知识库内容**真实进入 Prompt 并被消费**。⑤ **验收口径裁定**：`admin`（JWT）**无 `tenant_code`** → 出站不带租户头 → 自动对接取空；故端到端以**智能体主体**（`sk-agent-*`，`tenant_id=1 → tenant_code='tenant-1'`，经 `POST /api/v1/identity/agents` 正规签发）为准，**不修改任何既有账号数据**。⑥ **未闭环项（4 项，已登记）**：DPS 画像段实际注入（**跨仓租户码映射 + 画像种子**，探针证明**缺口在数据域而非代码**：DPS 预建码 → 404 人员不存在 / 本仓码 → 403 组织不存在 → `CR-148-029` 待裁定）；记忆段注入量（首轮对话注入 0 属正常，连续两轮复测）；流式 auto 与同步路径语义分叉（`CR-148-030`）；回写记忆命名读/写用户键不一致（`CR-148-031`）。⑦ **同步**：本记录 §4A（新建）+ §5 本行；《测试报告-v1.4.8》**v4.6.0**；《测试回溯对比审计报告-v1.4.8》**v1.7.0 → v1.8.0**；OpenLLM《DevLogReport R-396~R-398》**v1.16.0**（第 27 批）；`.devflow/state.json` 增补；证据 `doc/test/evidence/agent-e2e/`（核验脚本 + 判据 JSON + 知识库种子脚本）。⑧ 文档版本 **v1.32.0 → v1.33.0**，状态 [Review] |
| **v1.34.0** | **2026-09-26** | **TE-OpenBase-Dev / AT-OpenBase-Test** | **本轮迭代续：三源科学装配闭环达成 —— 新增修复 5 项缺陷（DEF-BE-148-021 ~ 025）+ 2 项环境/前置接线；端到端判据扩展至 H1~H10 全绿**。① **目标（续 §4A）**：§4A 已跑通「知识库真实注入 + 记忆组件执行 + 画像链路受信」但留 4 项未闭环；本轮补齐**记忆往返回环**与 **DPS 画像实际注入** → **`profile` + `memory` + `rag` 三段同轮进入 Prompt 并被消费**。② **缺陷与根因**（详见 §4B.1）：**(i) `DEF-BE-148-021`（P1）三路回写「静默不投递」** —— `WritebackQueue._run_item` 取不到 handler 即记 ERROR 后**直接 return、行状态不变**，而 `register_handler` **仅在 `/writeback` API 端点注册**，chat 业务路径从不注册 → 实测 `pending 5968 / done 21 / failed 41`，记忆**永不沉淀**；**(ii) `DEF-BE-148-023`（P1）记忆读/写资源键不一致（K17 声明未落地）** —— 读路径用 `{tenant_code}_{user_id}`、回写取原始键 → 同一主体落在两个键 → 第 2 轮 `memory.injected_items` 恒 0；**(iii) `DEF-BE-148-022`（P1）知识库路回写 kb_id 未透传** → 恒「kb_id 缺失」failed；**(iv) `DEF-BE-148-024`（P1 跨仓）DPS 码值未桥接 + 身份贯通缺失** —— DPS 独立联调演示码空间（`dps-org-001`/`dps-tenant-001`）无等价映射（实测三态 403「组织不存在」/404「人员不存在」/401），且 `_resolve_real_headers` 仅认 `external_*`（回写上下文恒空 dict）、回写 `role` 硬编码 `"user"`（DPS fail-closed）、画像读 `external_user_id` 而写回退资源键（同一主体两个 person_id）；**(v) `DEF-BE-148-025`（P2）画像回写空更新** → DPS 400「无可更新字段」（拒绝为凑合法请求而伪造画像数据）。③ **修复**：`_ensure_writeback_handlers` 业务路径注册（复用 API 端点同一实现）；`_build_wb_request_context` 与读路径**同一事实源**派生资源键并贯通 `org_id`/`role`/`external_*`；rag 回写透传 kb_id（auto 自动对接值 / 显式 pipeline 值）；新增 `apply_dps_code_map()` + `DPS_ORG_CODE_MAP`/`DPS_TENANT_CODE_MAP`（未配置=原样透传）并按本仓 `dps_code_map` 同口径配置编排器 Env；画像回写无字段时**无操作收口**。**因果探针**：固定其余头仅切换码值 → 码值正确时 `calculate`/`GET` **均 200 且返回真实画像**。④ **验收（PASS）**：`path=C`、`executed=['memory','rag','llm']`、`degraded=[]`、`rag_source=external`、`kb_id_source=external`、**`segment_tokens={profile:128, memory:5244, rag:2012, query:35}`**、`rag.injected_items=5`、`memory.injected_items=5`、`attribution.used_ratio≈0.98`、`contexts_tokens=7384`、端到端 **21.4 s**；**回写三路实测均 `done`**。⑤ **环境/前置接线**：DPS 联调前置（`platform.user_roles` 绑定 + `platform.profile` 画像行，幂等脚本 `seed_dps_portrait.py` —— DPS **不提供画像 upsert** 且未绑定主体 fail-closed 403；本环境 `platform.profile` 唯一键实为 `(person_id, tenant_id, template_code)`，按唯一约束写 `ON CONFLICT` 会报 `InvalidColumnReference`，故以显式存在性判定保证幂等）；编排器 openllm Env 增补 DPS 码值互译表（**长驻监控进程 Env 在启动时固化 —— 改脚本后须重启监控器方可生效**）。⑥ **回归**：本轮改动触及模块 24 文件 **12 failed / 362 passed**，12 项**全部落在既有失败集**（陈旧 401 `detail` 断言 / 已删符号 `_resolve_memory_metadata` / 本地 `.env` 三 REAL 开关 / `v213_gateway_ext` 异步卫生 / `writeback_degradation` 陈旧解包），**零新增失败**；其中 `test_s4_t5_prefix_normalize.py` **2 例由红转绿**（K17 归一落地）。⑦ **新增登记未闭环 2 项**：**回写队列启动恢复未接线**（`recover_pending()` 已于类文档声明为「应用启动时」调用但**全仓无调用点** → 重启后存量 pending 不再投递；接入时须加时限/条数上界以防回放数千条历史噪声，建议随 `TD-148-03`/运维批处置）；流式 auto 与同步路径语义分叉（沿用 `CR-148-030`）。⑧ **同步**：本记录 §4B（新建）+ §5 本行；《测试报告-v1.4.8》**v4.7.0**；《测试回溯对比审计报告-v1.4.8》**v1.9.0**；OpenLLM《DevLogReport R-396~R-398》**v1.17.0**（第 28 批）；`.devflow/state.json` 增补；证据 `doc/test/evidence/agent-e2e/`（核验脚本 ＋ 判据 JSON ＋ 知识库种子 ＋ **DPS 前置种子**）。⑨ 文档版本 **v1.33.0 → v1.34.0**，状态 [Review]（**同轮补注（修订号内澄清）**：新增修复 **`DEF-BE-148-026`（P1）** —— **回写队列启动恢复接线 + 双上界**（`lifespan` 接线 `recover_pending()`；时间窗 30 分钟 + 条数 200），实测启动日志「回写队列启动恢复完成: **21 条**待重跑（max_age=30.0 / limit=200）」→ 历史残留 5968 行**未回放**；护栏 `tests/unit/test_writeback_recovery_bounds.py`（9 例）→ **本轮缺陷数 5 → 6**、**§4B.3 未闭环 2 → 1 项**） |
| **v1.35.0** | **2026-09-26** | **TE-OpenBase-Dev / AT-OpenBase-Test** | **本轮迭代收口：流式与同步双路径收敛 —— 新增修复 2 项缺陷（`DEF-BE-148-027` / `DEF-BE-148-028`）+ 1 项契约更正；流式全链路端到端判据 S1~S10 全绿，登记未闭环项清零**。① **目标**：§4A/§4B 已把**同步** `mode=auto` 的三源自动装配跑通，遗留唯一登记项 **`CR-148-030`（流式 auto 与同步路径语义分叉）** 未闭环 —— 而流式（SSE）是**智能体/前端的实际接入面**，故本轮以「双路径收敛」收口（详见 §4C）。② **缺陷与根因**：**(i) `DEF-BE-148-027`（P1）流式 auto 不经组件路由器决策、知识库不自动对接** —— `_auto_pipeline` 按 `options` 直接展开组件（缺 `enable_rag`+`kb_id` 即 4003），流式路径因此**须调用方显式传参**；且流式三路回写构造回调时不带 `kb_id` → rag 路回写恒「kb_id 缺失」failed（流式知识库回写闭环不成立）；**(ii) `DEF-BE-148-028`（P2）流式条目级计量缺口** —— `_run_stream_components` 未回传 `raw_results` → 回执 `memory`/`rag` 快照恒 `items_count=0 / injected_items=0`，而同回执 `injected_tokens>0`（自相矛盾）→ 流式**条目级证据与归因 A 全部缺失**（同步同字段 5/5）。③ **修复（7 项，§4C.2）**：`AutoOrchestrator.decide()`/`apply_option_overrides()` **唯一决策入口** + `run(plan=)`（同一请求只决策一次）；网关 `_auto_component_plan()` 同步/流式**共用**规划入口（含 `_resolve_auto_kb_id` 自动对接）；`_compose_auto_stream_pipeline()` 按决策组装流式流水线；流式端点**决策置于首包之后**（P-4 口径「首包前只有本仓工作」不变，决策耗时计入 `auto_component_decision`），有效执行序列（`stream_pipeline`/`effective_pipeline_names`）与基线分离；`kb_id` 贯通 `_schedule_stream_writebacks` → `_build_writeback_callback(rag_kb_id=)` **按路绑定**；`_run_stream_components` 回传 `raw_results`；`_auto_pipeline` 放宽 4003。**契约更正**：auto 模式缺 `kb_id`/`user_id` 不再 4003（自动对接 + 主体兜底），2 例固旧契约断言按新契约更正（explicit 的 4003 校验不变）。④ **验收（流式 PASS，判据 S1~S10）**：`timeline = auth → sse_first_packet → auto_component_decision → memory → rag → profile_fetch → llm → writeback_dispatch`；`path=C`、`kb_id_source=external`、`rag_source=external`；`segment_tokens` 第 1 轮 `{profile:128, memory:8011, rag:1954}` / 第 2 轮 `{profile:128, memory:6507, rag:1929}`；**`memory.injected_items=5`、`rag.injected_items=5`**；归因 A `used` 318/310；**回写队列表三路均 `done`（`retry_count=0`）**；单轮 9.2~17.4 s。**同步路径回归复测仍 PASS**（`segment_tokens={profile:128, memory:7417, rag:1811}`、`kb_marker_in_answer=true`）。⑤ **回归**：OpenLLM `tests/unit` 既有失败集与**基线（`git stash` 回退版本）逐项完全相同**（`Compare-Object` 零差异）→ **零新增失败**；新增护栏 `tests/unit/test_stream_auto_parity.py`（16 例全绿）。⑥ **未闭环项**：**0 项**（`CR-148-029/030/031` 全部闭环）。⑦ **同步**：本记录 §4C（新建）+ §5 本行；《测试报告-v1.4.8》**v4.8.0**；《测试回溯对比审计报告-v1.4.8》**v2.0.0**；OpenLLM《DevLogReport R-396~R-398》**v1.18.0**（第 29 批）；`.devflow/state.json` 增补；证据 `doc/test/evidence/agent-e2e/`（**流式核验脚本 ＋ 流式判据 JSON**）。⑧ 文档版本 **v1.34.0 → v1.35.0**，状态 [Review] |
| **v1.36.0** | **2026-09-27** | **AA-OpenBase-Dev / AU-OpenBase-Dev** | **下一批次登记：待登记项 5（`CR-148-032`）与待裁定问题 6（`CR-148-033`）—— 新增 1 项 P1 技术债务 `TD-新增-028`，留 1 项待人工裁定；无代码改动**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案-v1.1.0》§10 待登记项 5 / §9 待裁定问题 6；基准证据 `doc/test/evidence/local-model-bench/`（`README.md` 方法口径 / `merged-bench.md` 跨端点合并表 / 两批 JSON+CSV 明细）。② **新增 `CR-148-032`（已登记；按债务通道处置 → `TD-新增-028`）**：生成式上下文精炼**缺达标模型与推理节点** —— 精度：≤1B 关键事实保留率 **0.167~0.667**（门槛 0.90），压缩率 0.43~0.46 的代价是丢标识与数值；时延：两端点均 **CPU 推理**（`size_vram=0`），压缩一段上下文 P50 本机 **32.6 s**（0.6B Q4）/ **76.8 s**（1B Q8）、局域网 **7.1 s**（0.5B Q4），对照在线预算（400/800 ms）**差 1~2 个数量级**；可获取性：模型仓库下载多次停在中途（0.5B 停于 379 MB）、注册表历史条目 `inactive`。**处置建议**：在线档不引入生成式（保留规则档 + 判别式重排 + 路由分类），生成式转异步档或 GPU 节点，按方案 §5.6 门槛从 1.7B 起复测。③ **新增 `CR-148-033`（待人工裁定）**：异步精炼的**触发与产物归属** —— **A 写入记忆**（跨会话生效，但改变记忆粒度、影响既有回归用例与幂等键）/ **B 仅装配期缓存**（对既有记忆语义零影响，收益限重复提问命中、跨轮次需重算）/ **C 双轨**（缓存 + 高价值轮次落库，收益最大但依赖价值闸门接线）；**记录建议：先 B**。④ **债务归集**：《技术债务总表》**v0.8.0** 新增 `TD-新增-028`（P1，待偿还；待偿还 17→**18**、总计 27→**28**）；本记录 §3 归集检查更新为**第 4 次**（归集日期 2026-09-27、总表版本 v0.8.0、新增④「按债务通道处置」）。⑤ **范围与影响说明**：方案 §10 待登记项 1~4 与 §9 问题 1~5 **尚未登记**（待批量登记，见 §4D.2）；**本轮不涉及任何代码改动、不改变 Step 4 判定**（`TT-038` ❌ 与前端类/可访问性未执行项维持原结论）。⑥ **同步**：本记录 **§4D（新建）+ §3 + §5 本行**；《技术债务总表》**v0.8.0**（新增 `TD-新增-028` + v0.8.0 口径说明 + 修订行）；《OpenBase-上下文精装配与组件通道优化技术方案》v1.1.0（§5 实测对比与选型、§9/§10 登记项）。⑦ 文档版本 **v1.35.0 → v1.36.0**，状态 [Review] |
| **v1.37.0** | **2026-09-27** | **AA-OpenBase-Dev / AD-OpenBase-Dev** | **上下文精装配第一批实施登记（§4E 新建）—— 方案 §10 待登记项 4「装配层无预算与裁剪、`system` 段恒空」转为「已实施（开关默认关闭）」；无新增缺陷、无新增债务**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.2.0** §6 第一批（设计项 v1.1.0 §3.2/§3.3/§3.5/§4.2）；实现在 OpenLLM 仓（其《DevLogReport》**v1.19.0** 第 30 批，提交 `65899c7` + `892e8e7`）。② **实施 5 项**：**(i) 预算与裁剪**（`BudgetPolicy`/`apply_context_budget`：段内去重 → 单条句边界截断 → 分段配额整条裁剪，`system` 仅观测）+ `context_metrics` 增 `budget`/`truncated` 观测；**(ii) system 段**统一指令注入（`resolve_system_prompt`，调用方显式优先）；**(iii) 检索侧重排与阈值接线**（`_rag_search_params` 统一取值口径，主通道两处 handler 与内置备通道同口径）；**(iv) 路由候选明细入 trace**（`candidate_report` → `plan.candidates` → 同步/流式 `routing_trace.decision_candidates`）；**(v) 内容去重**（含于预算层，可单独关闭）。**共新增 11 项配置，其中 5 个总开关默认关闭 ⇒ 关闭时 Prompt 与回执与既有实现逐字一致**。③ **验证**：新增护栏 4 文件 **29 例**全绿（13+5+5+6）；全量 `tests/unit` **32 failed / 2991 passed / 0 error**（237.59 s）；**基线对照**（同命令、同 12 个失败文件、仅回退本批 6 个生产文件）**28 = 28 且归一化后逐项零差异 ⇒ 零新增失败**；静态质量零新增告警；**L1 + L3-lite 探针**两档（默认窗口 memory 配额 2150/used 792；收紧窗口配额 300 ⇒ `dropped_items=8`/`dropped_tokens=504`、保留 4 条、`prompt_total_tokens=381`；`system_injected=true`；`rag_search_params={"rerank":true,"score_threshold":0.15}`；候选 R001/R002/R004）。④ **过程修正（如实登记）**：`_rag_search_params()` 求值由 `try` 内**移出**（避免解析异常被误判为「外部检索失败」而触发内置回退）；`test_rag_unregistered_no_fallback` 替身按**真实适配器契约**补齐 `rerank`/`score_threshold`（**契约漂移修正**，非放宽断言）。⑤ **与既有登记项关系**：`CR-148-032`/`TD-新增-028`（生成式精炼）**不受影响**（本批不含模型档能力）；方案 §6 第一批第 6 项「两条路径取数顺序统一与画像并行」**仍未实施**（留作下一轮，风险点＝流式 `P-4` 首包计量口径）；**全仓未闭环项仍为 0**。⑥ **生产开启待批**：5 项开关的开启值（配额比例、单条上限、rerank 阈值、system 指令文案）须人工批准后按方案 §7 判据 **T1~T6** 验证再开，**本记录不代行批准**。⑦ **同步**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.2.0**（§6 批次状态、§10 待登记项 4 状态、§11 修订行）；OpenLLM《DevLogReport》**v1.19.0**；证据 `doc/test/evidence/cr149/context_budget_probe.py`、`OpenLLM/backend/cr149-batch1-regression.txt`、`cr149-head-failures.txt` / `cr149-base-failures.txt`。⑧ 文档版本 **v1.36.0 → v1.37.0**，状态 [Review] |
| **v1.38.0** | **2026-09-27** | **AA-OpenBase-Dev / AD-OpenBase-Dev** | **上下文精装配第一批第 6 项实施登记（§4F 新建）—— 方案 §6 第一批 6/6 完成；无新增缺陷、无新增债务**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.3.0** §3.1 / §6；实现在 OpenLLM 仓（其《DevLogReport》**v1.20.0** 第 31 批，提交 `2f296bb`）。② **实施 4 项**：**(i) 画像 × 组件并行取数** —— 新增并发取数句柄 `DeferredFetch`（构造即启动后台取数、组装之前统一收割；`resolve()` 幂等、异常降级 `None`、`discard()` 取消）；**(ii) 两路径取数时序统一** —— 同步「构造句柄 → 交编排层 → 组装前收割」、流式「**首包之后**构造（P-4 口径不破）→ 组装前 `resolve()`」，两路径由**相反且串行**收敛为**同序且并发**；**(iii) 计量不丢** —— 步骤改由**取数完成回调**落 `{step, ms}`（耗时＝启动→完成差值），异常路径亦落计量，未启动仍「值 `None` + 步骤恒落」；**(iv) 接口兼容** —— `profile_ctx` 放宽为 `str \| DeferredFetch \| None`，既有字符串调用方与测试替身零影响。**本批为时序收敛（语义等价），无新增开关**。③ **验证**：新增护栏 `tests/unit/test_deferred_fetch.py`（**14 例**）；`test_profile_fetch_timeline_guard.py` 改写为**句柄写法契约**并新增**时序契约**（**4 例**，原三项不变量全部保留且更严）；**运行态探针** `doc/test/evidence/cr149/profile_parallel_probe.py`（走真实 `PipelineExecutor` + `run_components`）：分段各 0.15 s 时 **串行 0.312 s → 并发 0.156 s**（省 0.156 s，3 轮取最优含预热），并发态 `profile_fetch=156 ms` 且画像确入 Prompt；两路径接线时序 4 项判定全 `true`。④ **回归**：全量 `tests/unit` **32 failed / 3005 passed / 0 error**（227.84 s；该测量轮次护栏含 `test_deferred_fetch` **13 例** + 改写护栏 4 例，同批随后补入的端到端护栏 1 例单独验证通过 ⇒ **批末态 32 failed / 3006 passed**）；**基线对照**（同命令 vs 第一批基线 `cr149-full-after-fix.txt`，逐项 testid 归一化后 `Compare-Object`）**32 = 32，零差异 ⇒ 零新增失败**；静态质量 7 文件 `ruff` **零告警**。⑤ **风险如实登记（新增两项入方案 §8）**：并发后 `timeline` 步骤**之和 ≥ 真实墙钟**（区间重叠 → `P-1` 判定需按关键路径复核）；异常路径句柄未显式收割（完成回调兜底计量 + `discard()` 清理）。⑥ **与既有登记项关系**：§4E.3「第 6 项仍未实施」**就此闭环**；方案 §10 待登记项 4 状态更新为「已实施（第一批 6/6）」；`CR-148-032`/`TD-新增-028` **不受影响**；**全仓未闭环项仍为 0**。⑦ **生产开启待批（不变）**：5 项开关的开启值须人工批准后按方案 §7 判据 **T1~T7** 验证再开，**本记录不代行批准**。⑧ **同步**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.3.0**（§3.1 已实施段 + §6 6/6 + §7 T7 + §8 两项风险 + §10 待登记项 4 + §11 修订行）；OpenLLM《DevLogReport》**v1.20.0**（第 31 批）；证据 `doc/test/evidence/cr149/profile_parallel_probe.py` 与 `profile_parallel_probe-result.json`。⑨ 文档版本 **v1.37.0 → v1.38.0**，状态 [Review] |
| **v1.39.0** | **2026-09-27** | **AA-OpenBase-Dev / AD-OpenBase-Dev** | **上下文精装配第二批第 ① 项实施登记（§4G 新建）—— 方案 §10 待登记项 3「写侧价值/重要度/频控/去重决策器未接线」转为「已实施（开关默认关闭）」；无新增缺陷、无新增债务**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.4.0** §4.3 / §6 第二批 / §7 判据 **T5**；实现在 OpenLLM 仓（其《DevLogReport》**v1.21.0** 第 32 批，提交 `c60ce2b`）。② **实施 4 项**：**(i) 接回写决策器** —— 新增 `evaluate.grade_writeback_targets()`（**纯函数、确定性**）供网关三路回写回调按路消费（价值闸门：窗口非空 / query 与 response 非空 / response ≥2 字 / `save_if_valuable=false` 显式拦截）；**(ii) rag 分级入库** —— `evaluate.grade_rag_ingest()`：明确记忆意图（重要度 ≥0.8）或响应 ≥ `WRITEBACK_RAG_FULL_MIN_CHARS`（默认 120）⇒ `full`（全文入库），其余 ⇒ `skip`（**普通轮次跳过知识库入库**，遏制自产膨胀）；**(iii) T5 可判定** —— 被拦截回调返回 **`"skipped"`**（**不与 `False`（幂等命中）混用**）→ 编排层回执 `{"status":"skipped","reason":"value_gate"}`、流式回执 `skipped`；**(iv) 不代行决定 §9 问题 4** —— 闸门**只决定是否沉淀、不改写载荷**（memory 仍整轮全文），`evaluate_session()` 的**载荷形态**（窗口摘要 / 频控预检 / 画像增量）**未接线**。③ **开关与回退**：新增 `WRITEBACK_DECISION_ENABLED`（默认 **False**）＋ `WRITEBACK_RAG_FULL_MIN_CHARS`（120）；**关闭时三路无条件入队、返回值语义不变 ⇒ 与既有实现逐字一致**。④ **验证**：新增护栏 `tests/unit/test_writeback_decision_gate.py`（**13 例**）全绿；**运行态探针** `doc/test/evidence/cr149/writeback_gate_probe.py`（真实网关回调 + 真实决策器 + 队列替身）—— **关闭态**四类轮次（含空响应）均三路入队；**开启态**低价值轮 `returns` 三路均 `skipped` 且 **`submitted=[]`**、普通轮 `submitted=[memory, profile]`（`rag` 跳过）、高价值轮与长响应轮 `rag` **全文**入库且载荷未改写。⑤ **回归**：全量 `tests/unit` **32 failed / 3019 passed / 0 error**（239.85 s；收集 3051）；**基线对照**（同命令 vs 上一轮 `cr149-b2-full.txt`，逐项 testid 归一化后 `Compare-Object`）**32 = 32，零差异 ⇒ 零新增失败**；静态质量 5 文件 `ruff` **零告警**。⑥ **与既有登记项关系**：`CR-148-032`/`TD-新增-028` **不受影响**；方案 §9 待裁定问题 4（记忆写入语义）**仍未裁定且已成「载荷形态接线」的前置阻塞项**；§9 问题 1（通道 A 三选一）仍待裁定；**全仓未闭环项仍为 0**。⑦ **生产开启待批（不变）**：`WRITEBACK_DECISION_ENABLED` 与 `WRITEBACK_RAG_FULL_MIN_CHARS` 的开启值须人工批准后按方案 §7 判据 **T5** 验证再开，**本记录不代行批准**。⑧ **同步**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.4.0**（§4.3 已实施细节 + §6 第二批「进行中 1/3」+ §7 T5 + §10 待登记项 3 + §11 修订行）；OpenLLM《DevLogReport》**v1.21.0**（第 32 批）；证据 `doc/test/evidence/cr149/writeback_gate_probe.py` 与 `writeback_gate_probe-result.json`。⑨ 文档版本 **v1.38.0 → v1.39.0**，状态 [Review] |
| **v1.40.0** | **2026-09-27** | **AA-OpenBase-Dev / AD-OpenBase-Dev** | **上下文精装配第二批第 ② 项实施登记（§4H 新建）—— 方案 §3.1「组件串并行仍受全局开关控制、依赖图判定未接入」转为「已实施（开关默认关闭）」；无新增缺陷、无新增债务**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.5.0** §3.1 / §4.2「顺序优化」/ §7 判据 **T8**；实现在 OpenLLM 仓（其《DevLogReport》**v1.22.0** 第 33 批，提交 `ec3485a`）。② **实施 5 项**：**(i) 依赖图模块** —— 新增 `component_graph.py`（`parse_dependencies` 声明解析 / `dependency_levels` Kahn 式波次划分 / `resolve_schedule`），未参与本次执行的依赖视为已满足；**(ii) 「无依赖即并行」** —— `component_pipeline.resolve_schedule_plan()` 返回「波次 ＋ 同波次可否并发」，`run_components` 按波次执行（同波次 >1 用 `asyncio.gather`、波次间有序），按**条目下标**消费以保持重复组件与原有顺序语义；**(iii) 「严格顺序用依赖声明表达」** —— `OPENLLM_COMPONENT_DEPENDENCIES`（如 `memory:rag`），声明**覆盖**全局并行开关；**(iv) fail-safe** —— 成环退化为单波次保序并告警（不抛异常、不打挂请求）、非法声明片段跳过并告警；**(v) 关闭时逐字一致** —— 关闭时计划恒为「单波次」、并发与否仍由 `enable_parallel` 决定。③ **开关**：新增 `COMPONENT_DEPENDENCY_SCHEDULING_ENABLED`（默认 **False**）＋ `OPENLLM_COMPONENT_DEPENDENCIES`（默认 **""**）。④ **验证**：新增护栏 `tests/unit/test_component_dependency_scheduling.py`（**12 例**）全绿，既有共用步骤护栏 13 例未变；**运行态探针** `doc/test/evidence/cr149/component_schedule_probe.py`（真实共用组件步骤 + 真实调度器，组件各 0.12 s、含预热）—— 关闭态串行 **0.25 s** / 全局开关并行 **0.125 s**；**开启态无依赖 ⇒ 0.125 s 重叠**（「无依赖即并行」生效）；**开启态声明 `memory:rag` ⇒ 波次 `[["rag"],["memory"]]`、事件严格 `rag→memory`、不重叠**（0.235~0.25 s）。⑤ **回归**：全量 `tests/unit` **32 failed / 3031 passed / 0 error**（239.55 s；收集 3063）；**基线对照**（同命令 vs 上一轮 `cr149-b2b-full.txt`，逐项 testid 归一化后 `Compare-Object`）**32 = 32，零差异 ⇒ 零新增失败**；静态质量 4 文件 `ruff` **零告警**（过程修正：isort 惰性导入排序、文件末尾换行）。⑥ **与既有登记项关系**：§4.2 余项（阈值语义对齐 / LLM 兜底分类器 / 规则集可配置）**仍未实施**；§4.1（通道定性 / 内置 RAG 底座 / health 组件探测）与 §4.3 余项**仍未实施**，其中「通道定性」需人工裁定（§9 问题 1）、「内置 RAG 底座 / health 探测」为必做项可先行；§9 问题 4 仍为**前置阻塞项**；**全仓未闭环项仍为 0**。⑦ **生产开启待批（不变）**：`COMPONENT_DEPENDENCY_SCHEDULING_ENABLED` 与 `OPENLLM_COMPONENT_DEPENDENCIES` 的开启值须人工批准后按方案 §7 判据 **T8** 验证再开，**本记录不代行批准**。⑧ **同步**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.5.0**（§3.1 已实施段 + §4.2 顺序优化标注 + §6 第二批「进行中 2/3」+ §7 T8 + §8 三项风险 + §11 修订行）；OpenLLM《DevLogReport》**v1.22.0**（第 33 批）；证据 `doc/test/evidence/cr149/component_schedule_probe.py` 与 `component_schedule_probe-result.json`。⑨ 文档版本 **v1.39.0 → v1.40.0**，状态 [Review] |
| **v1.41.0** | **2026-09-27** | **AA-OpenBase-Dev / AD-OpenBase-Dev** | **上下文精装配第二批第 ③ 项实施登记（§4I 新建）—— 方案 §4.1「配套两项必做」之一（备通道健康探针）已实施；§10 待登记项 2（内置 RAG 无底座）转为「部分实施」；无新增缺陷、无新增债务**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.6.0** §4.1 / §7 判据 **T4** 前置条件；实现在 OpenLLM 仓（其《DevLogReport》**v1.23.0** 第 34 批，提交 `03a624f`）。② **实施 5 项**：**(i) 备通道健康探针** —— `_probe_components(db)` 并行探测 **5 项**（外部三组件 ＋ `builtin_rag` ＋ `ollama`，共用既有结果缓存）；**(ii) 内置 RAG 底座事实** —— `_count_faiss_indexes(root)`（与 `VectorStoreService` 落盘约定同一事实源）＋ `_probe_builtin_rag(db)`（`knowledge_bases`/`indexes`/`has_base`/`reason`）；**(iii) Ollama 可达性** —— `_ollama_probe_tags()`（`GET {OLLAMA_HOST}/api/tags`，2 s 独立超时、URL 取自配置）＋ `_probe_ollama()`；**(iv) 探测不抛异常** —— DB / 文件系统 / HTTP 异常一律降级为 `unavailable` ＋ `reason`；**(v) 同一事实源** —— `/health` 增 `db` 依赖统计 KB 行数，原三键**原样保留**（增量字段、向后兼容）。③ **验证**：新增护栏 `tests/unit/test_health_backup_channel_probe.py`（**10 例**）全绿；**运行态探针** `doc/test/evidence/cr149/health_backup_probe.py`（调真实探测函数）—— `faiss_root_exists=true` 但 `indexes=0`、`has_base=false`，`reason="内置 RAG 无底座（KB 0 行 / FAISS 0 索引）⇒ 备通道接管后将注入为空"`；`ollama = {status: ok, latency_ms: 15, models: 2}`；`components_keys = [builtin_rag, dps, ollama, openmemory, openrag]`。④ **回归**：全量 `tests/unit` **31 failed / 3042 passed / 0 error**（238.83 s；收集 3073）；**基线对照**（同命令 vs 上一轮 `cr149-b2c-full.txt`，逐项 testid 归一化后 `Compare-Object`）**无新增失败项**（失败集为基线**子集** 32 → 31），唯一差异为既有 flaky `test_v213_gateway_ext.py::test_memory_writeback_adapter_missing_raises` 本轮**转绿**（如实登记为**基线波动而非本批收益**）；静态质量 2 文件 `ruff` **零告警**（过程修正：gateway 增补缺失的 `import os`）。⑤ **与既有登记项关系**：方案 §10 待登记项 2 更新为「部分实施」（事实前置可视化；**种子动作需运行态 DB ＋ 嵌入模型**，当前口径明确为「内置 RAG 仅在有本地索引时生效」）；§9 问题 1（通道 A 三选一）仍待裁定（阻塞 `components.*.channel` 字段与通道定性）；§4.3 余项（队列指标与死信 / 画像增量升级 / 写路径与通道一致）仍未实施；`CR-148-032`/`TD-新增-028` **不受影响**；**全仓未闭环项仍为 0**。⑥ **同步**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.6.0**（§4.1 两项标注 + §6 第二批「③已完成/④待做」+ §7 T4 前置条件 + §10 待登记项 2 + §11 修订行）；OpenLLM《DevLogReport》**v1.23.0**（第 34 批）；证据 `doc/test/evidence/cr149/health_backup_probe.py` 与 `health_backup_probe-result.json`。⑦ 文档版本 **v1.40.0 → v1.41.0**，状态 [Review] |
| **v1.42.0** | **2026-09-27** | **AA-OpenBase-Dev / AD-OpenBase-Dev** | **上下文精装配第二批第 ④ 项实施登记（§4J 新建）—— 方案 §4.3「队列可观测与死信」已实施；无新增缺陷、无新增债务**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.7.0** §4.3；实现在 OpenLLM 仓（其《DevLogReport》**v1.24.0** 第 35 批，提交 `1a572f7`）。② **实施 5 项**：**(i) 聚合指标** —— `WritebackStore.stats()`（三条聚合 SQL：状态分组 / `retry_count>0` 直方图 / 最早未完成 `updated_at`）产出深度·失败率（空库 `0.0` 不除零）·重试分布·`max_retry_count`·积压年龄，`WritebackQueue.stats()` 补 `queue_depth`；**(ii) 死信视图** —— `list_dead_letters()`（只含 `failed`、分页、**不含 payload 正文**）；**(iii) 重放端点** —— `claim_failed()` 原子置回 `pending` 且 `retry_count` 归零后由 `replay_dead_letters()` 复用 `_run_item` 重新投递（未注册 handler 计 `skipped`、行留 `pending`）；`POST /writeback/dead-letter/replay` 仅接受显式行 id、单次 ≤100（超限 4003）；**(iv) 失败 TTL 清理任务化** —— `run_cleanup_loop()` 由 lifespan 启动/关闭取消，间隔 `WRITEBACK_CLEANUP_INTERVAL_SECONDS`（默认 3600 s，**0=关闭**）、单轮异常不终止循环；**(v) 归属隔离** —— 三处均沿用 `DEF-BE-148-007` 的 `json_extract` fail-closed，无身份一律 401（1001）。③ **验证**：新增护栏 `tests/unit/test_writeback_queue_observability.py`（**22 例**）全绿；**运行态探针** `doc/test/evidence/cr149/writeback_observability_probe.py`（真实存储层/队列层 + 独立临时 SQLite）—— 全局 `{total:4, done:1, failed:3, failure_rate:0.75, retry_distribution:{"2":1,"3":2}}`；按用户 `u-1 {total:3, failed:2}`（他人行与无归属历史行不可见）；死信视图 `total=3` 且无 payload 字段；**重放 2 行 → `replayed=2`、handler 实投递 2 次、状态转 `done`**；越权取件 `[]` 且对方行仍 `failed`；`run_cleanup_loop(0)` 即时返回、TTL 不误删新近死信。④ **回归**：全量 `tests/unit` **32 failed / 3063 passed / 0 error**（244.44 s；收集 3095）；**基线对照**（同命令 vs 第 33 批基线 `cr149-b2c-full.txt`，逐项 testid 归一化后 `Compare-Object`）**32 = 32，零差异 ⇒ 零新增失败**；**对照实验（决定性证据）**：上一轮 `test_v213_gateway_ext.py` 曾少失败 1 例，本批以 `git stash push -- <本批 4 个生产文件>` **回退改动后隔离复跑，得到与改动后完全相同的 4 个失败** ⇒ 判定**既有序相关 flaky，与本批改动无关**；静态质量 5 文件 `ruff` **零告警**。⑤ **与既有登记项关系**：§4.3 余项（画像增量升级 / 写路径与通道一致）**仍未实施**（后者依赖通道定性与 `assert_write_channel_is_primary` 接入）；§9 问题 1 / 问题 4 仍待裁定；**全局口径统计未开放**（现为调用方作用域，如需全局视图建议按角色门禁单独开放）；`CR-148-032`/`TD-新增-028` 不受影响；**全仓未闭环项仍为 0**。⑥ **同步**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.7.0**（§4.3 已实施标注与细节 + §6 第二批进度 + §11 修订行）；OpenLLM《DevLogReport》**v1.24.0**（第 35 批）；证据 `doc/test/evidence/cr149/writeback_observability_probe.py` 与 `writeback_observability_probe-result.json`。⑦ 文档版本 **v1.41.0 → v1.42.0**，状态 [Review] |
| **v1.43.0** | **2026-09-27** | **AA-OpenBase-Dev / AD-OpenBase-Dev** | **上下文精装配第二批第 ⑤ 项实施登记（§4K 新建）—— 方案 §4.2「阈值与单次命中语义对齐 / 规则集可配置 / LLM 兜底接线」三项均已实施；无新增缺陷、无新增债务**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.8.0** §4.2 / §7 判据 **T9**；实现在 OpenLLM 仓（其《DevLogReport》**v1.25.0** 第 36 批，提交 `0abcaea`）。② **实施 4 项**：**(i) 阈值与单次命中语义对齐** —— `R001`/`R002` 单次命中 0.8 → **0.86**、`R005` 复合意图 0.8 → **0.86**（此前**永不达标**），由 `COMPONENT_ROUTER_SINGLE_HIT_CONFIDENCE` / `COMPONENT_ROUTER_COMPOSITE_CONFIDENCE` 驱动（默认 0.86）、**配回 0.8 即复现旧「回落」语义**、低配时告警；**(ii) 规则集可配置** —— `COMPONENT_ROUTER_RULES_PATH` 接入构造，**路径非法/文件损坏告警并退回内置规则**；**(iii) LLM 兜底接线** —— 新增 `_build_component_router()`（`_auto_component_plan` 统一调用），开关 `COMPONENT_ROUTER_LLM_FALLBACK_ENABLED`（**默认关闭**）开启且存在 DB/身份时注入分类器（复用 `_call_llm`、`temperature=0`、`max_tokens=64、300ms 超时`），超时/异常/非法 JSON **一律回落规则**；**(iv) 语义更正的可复现逃生阀** —— 置信度配置化，旧语义可一键复现。③ **验证**：新增护栏 `tests/unit/test_component_router_decision_tuning.py`（**15 例**）全绿；**3 个既有护栏按新契约更正**（原断言编码的正是方案指出的「隐性分叉」，现改用逃生阀复现旧场景**并同时锁定新默认** —— **契约更正而非放宽断言**）；**运行态探针** `doc/test/evidence/cr149/component_decision_probe.py`（真实路由器 + 网关构造入口）—— 单次记忆/单次知识命中「旧 0.8 不决策 → 新 0.86 直接决策」、`R005.qualified` `false → true`、无候选查询不变；自定义规则文件 `X001` 生效、非法路径退回内置 5 条规则；LLM 兜底「关=不注入 / 开=注入 / 超时=回落规则」。④ **回归**：全量 `tests/unit` **31 failed / 3079 passed / 0 error**（244.08 s；收集 3110）；**基线对照**（同命令 vs 上一轮 `cr149-b2e-full.txt`，逐项 testid 归一化后 `Compare-Object`）**无新增失败项**（失败集为基线**子集** 32 → 31，差异项仍为已用对照实验证实的既有序相关 flaky）；静态质量 7 文件 `ruff` **零新增告警**（`component_router.py` 39 = 39、其余 2 = 2）。⑤ **语义变更提示（已在 §4K.3 与方案 §8 风险表登记）**：单次命中置信度提升使**路由决策面变宽** —— 同一查询可能由「LLM 兜底结论」变为「规则直接结论」，组件装配面随之变化；**生产如需保持旧行为，把两个置信度键配回 0.8**。⑥ **与既有登记项关系**：§9 问题 1（通道 A 三选一）仍待裁定（阻塞通道定性 / 通道裁决进取数层 / §4.3 写路径与通道一致）；§9 问题 4 仍为回写载荷形态接线前置阻塞；LLM 兜底**上线前提**＝按 §5.6 门槛复测出达标分类器；`CR-148-032`/`TD-新增-028` 不受影响；**全仓未闭环项仍为 0**。⑦ **同步**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.8.0**（§4.2 三项标注与实现细节 + §6 第二批进度 + §7 T9 + §8 三项风险 + §11 修订行）；OpenLLM《DevLogReport》**v1.25.0**（第 36 批）；证据 `doc/test/evidence/cr149/component_decision_probe.py` 与 `component_decision_probe-result.json`。⑧ 文档版本 **v1.42.0 → v1.43.0**，状态 [Review] |
| **v1.44.0** | **2026-09-27** | **AA-OpenBase-Dev / AD-OpenBase-Dev** | **缺陷登记与修复：`DEF-BE-148-029` 画像增量提炼服务缺失（§4L 新建）—— 已提交代码引用仓内不存在模块 `app/services/profile_refine.py`；本批补回模块并加 fail-safe，缺陷闭环；无新增债务**。① **来源**：上下文精装配第二批实施中的**仓内一致性审计**（`evaluate.py` 导入契约 vs 仓内实际模块）；修复落于 OpenLLM 仓（其《DevLogReport》**v1.26.0** 第 37 批，提交 `5589ddf`）。② **缺陷**：`evaluate.py::_profile_updates_for` 惰性导入 `DEFAULT_PROFILE_TARGETS` / `get_active_profile_refiner` / `refine_profile_delta`，但 **`app/services/profile_refine.py` 在仓内不存在**（递归查找**仅命中 `__pycache__/profile_refine.cpython-310.pyc`**）；一旦写侧入口 `evaluate_session(..., {"enable_profile_delta": true})` 被接线即 **ModuleNotFoundError** 打挂回写决策。**根因**：同批源码未随提交落库 ＋ 引用方无 fail-safe（静默隐藏）＋ 方案 §4.3 所述配置键 `OPENLLM_PROFILE_LLM_REFINE` **当前树不存在**（文档-实现漂移）。**级别 P1**（当前未触发，属「埋雷」型）。③ **修复 4 项**：**(i) 补回服务模块**（规则提炼语义**逐字取自既有线上实现** `writeback._resolve_profile_updates`/`_extract_topics`/`_infer_tone`，非重新发明）；**(ii) 单一事实源**（回写路三个函数改为薄封装委托，既有公开名保留 ⇒ `test_v2143_writeback_profile.py` 契约不破；两处默认值差异显式化）；**(iii) 提炼器注入位点**（`refine_fn(dialogue)->dict|None` **同步**契约；未注册 ⇒ 纯规则路径；抛异常/返回非 dict/返回空 ⇒ **保留规则结果**）；**(iv) 写侧决策 fail-safe**（整体含导入纳入 try/except ⇒ 降级为空增量并告警，可选目标不打挂主流程）。④ **验证**：新增护栏 `tests/unit/test_profile_refine_service.py`（**17 例**）全绿 —— **首轮 RED 的失败信息本身即缺陷证据**（`ModuleNotFoundError: No module named 'app.services.profile_refine'`）；既有 `test_v2143_writeback_profile.py` **13 例全绿**；**运行态探针** `doc/test/evidence/cr149/profile_refine_probe.py` —— 三符号齐备、`evaluate._profile_updates_for` 真实返回 `business.topics` + `person.tone`、提炼器注入生效且失败回落规则、**回写路与服务模块 5 类入参结果一致**。⑤ **回归**：全量 `tests/unit` **32 failed / 3095 passed / 0 error**（251.93 s；收集 3127）；失败集与已知 32 项集**相同 ⇒ 零新增失败**；**对照实验（决定性）**：`git stash` 本批受跟踪文件 ＋ 临时移除新模块后**隔离复跑 `test_v213_gateway_ext.py` 得到完全相同的 4 个失败** ⇒ 该文件为**既有序相关 flaky**（第 35 批首次登记），与本批无关；静态质量 4 文件 `ruff` **零告警**。⑥ **与既有登记项关系**：方案 §4.3「画像增量升级」状态更新为**「基座已补回；线上 LLM 门控待决策」**（提炼器位点就绪，但线上接线需先裁定**同步/异步提炼器形态**，已作为方案 §9 **追加问题 7**（注意：§9 原已有问题 6「异步精炼触发与产物归属」，本轮登记据此更正编号））；`DEF-BE-148-029` **已修复闭环**；§9 问题 4 与 `CR-148-032`/`TD-新增-028` **不受影响**；**全仓未闭环项仍为 0**。⑦ **同步**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.9.0**（§4.3 状态 + §9 追加问题 7 + §11 修订行）；OpenLLM《DevLogReport》**v1.26.0**（第 37 批）；证据 `doc/test/evidence/cr149/profile_refine_probe.py` 与 `profile_refine_probe-result.json`。⑧ 文档版本 **v1.43.0 → v1.44.0**，状态 [Review] |
| **v1.45.0** | **2026-09-27** | **AT-OpenBase-Test / AA-OpenBase-Dev** | **§7 验收判据执行器交付（§4M 新建）＋ 执行器首跑暴露的 T1/T2 两处结构性缺口更正；无新增缺陷、无新增债务**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.10.0** §7 / §3.3；实现在 OpenLLM 仓（其《DevLogReport》**v1.27.0** 第 38 批，提交 `4389ded`）。② **交付：判据执行器** `doc/test/evidence/cr149/t_acceptance_runner.py` —— T1~T9 **一键复跑**，逐条 `PASS / FAIL / SKIP / BLOCKED` ＋**原始测量数据**（`--json` 落盘）；默认按**当前配置**判定；`--simulate` **进程内**临时置位（退出恢复、不写配置、不影响运行中服务）；`SKIP`/`BLOCKED` **不计入失败**但显式列出（避免"没做"被误读为"通过"）；退出码 `0`=无 FAIL。**交付前 T1~T9 仅存在于方案表格、无执行体**；交付后「人工批准开关值 → 一键验收」成为**可执行闭环**。③ **缺口一（T1 结构冲突）**：§3.3 原本即要求「`query + 模板开销` 留余量」，但第一批比例 `0.05/0.05/0.30/0.40/0.20`（**和 = 1.00**）⇒ 各段满额时总长超 available；原夹具条目偏小留下**偶然空隙**把冲突掩盖成"通过"。**修法**：标定 `0.05/0.05/0.28/0.37/0.19`（**和 = 0.94**）＋ 常量 `QUOTA_HEADROOM_CEILING=0.95`；执行器 T1 改用**填满配额**的最坏夹具。④ **缺口二（T2 整段清空）**：单条素材 > 段配额时「整条丢弃」一路丢到空（实测 history `dropped_items=6 / used=0`）。**修法**：新增 `_fit_single_unit()` 与「**保底一条**」（仅当将清空该段时保留首条，句边界 → 比例收敛，**连同编号前缀一并计入**，硬压进配额并记 `truncated_items`；可装下首条时不触发 ⇒ 既有语义不变）。⑤ **顺带显式化** `quota=0` 语义（"不限"= 不裁剪，fail-open），T1 的 `used ≤ quota` **仅对 `quota>0` 的段**成立。⑥ **验证**：新增护栏 `tests/unit/test_context_budget_headroom_and_floor.py`（**7 例**）全绿；预算族既有护栏（含 `test_context_budget.py` 13 例）**全绿**；**执行器两态实测** —— 当前配置 `{PASS:3, SKIP:4, BLOCKED:2, FAIL:0}`、`--simulate` `{PASS:6, SKIP:1, BLOCKED:2, FAIL:0}`（报告两份落盘）；全量 `tests/unit` **32 failed / 3102 passed / 0 error**（245.06 s；收集 3134），**失败集与上一轮逐项完全相同 ⇒ 零新增失败**；3 文件 `ruff` **零告警**。⑦ **与既有登记项关系**：§7 T1~T9 由"表格判据"升级为"可执行判据"；§3.3 补充余量约束/保底一条/`quota=0` 语义三节；§4E 第一批"已实施"结论不变但**更正 T1/T2 实现口径**（开关仍默认关闭 ⇒ 线上行为不变）；**T4（内置 RAG 无底座）/ T6（第三批精炼）判为 `BLOCKED`** 并显式登记；**开关开启值仍未批准**（T1/T2/T5/T8 批准后一条命令复跑即可出结论）；**全仓未闭环项仍为 0**。⑧ **同步**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.10.0**（§3.3 + §7 T1/T2/执行器 + §11）；OpenLLM《DevLogReport》**v1.27.0**（第 38 批）；证据 `doc/test/evidence/cr149/t_acceptance_runner.py`、`t_acceptance_runner-result.json`、`t_acceptance_runner-simulate-result.json`。⑨ 文档版本 **v1.44.0 → v1.45.0**，状态 [Review] |
| **v1.46.0** | **2026-09-27** | **AT-OpenBase-Test / AA-OpenBase-Dev** | **T4 轨迹两路径口径收敛（§4N 新建）—— 方案 §7 T4「轨迹」段转为进程内可判；无新增缺陷，新增 1 项能力缺口登记**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.11.0** §4.1 / §7 T4 / §10；实现在 OpenLLM 仓（其《DevLogReport》**v1.28.0** 第 39 批，提交 `b37e0c0`）。② **动因（判据覆盖不足 → 暴露真实缺口）**：v1.10.0 把 T4 整体判为 `BLOCKED`（依据「内置 RAG 无底座」），但 T4 的**「轨迹」部分并不依赖运行态** ⇒ **本可判定却一直未判**；复核中进而发现**流式路径的接管发生在共用组件步骤** `component_pipeline.run_components`，该步骤**只落 `rag_source`、不落回退归因**，而同步路径 handler 落 `builtin_fallback_reason` ⇒ **两路径轨迹口径不一致**（流式缺「为何接管」），且两处字段**各自手写**、属可再次分叉的形态。③ **收敛**：`ComponentRunResult` 新增 `builtin_fallback_reason`（`REASON_MAX_CHARS=120` ＋ `_fallback_reason()` 截断）；网关新增 `_merge_rag_trace()` 作为**唯一落痕实现**，同步轨迹字面量与流式两处调用**共用**；`_run_stream_components` 回传归因；删除原手写字段与 `if shared_state.get(...)` 分支。④ **语义保持**：未检索仍 `skipped` 且不落空归因；`external` 不落归因；**装配缺失/超时仍不触发回退**（`DEF-BE-148-012` 不变）；回退**不计 `degraded`**。⑤ **执行器拆分**：T4 由「整体待运行态」改为「**轨迹 = 进程内判 ＋ 无 5xx = 运行态**」（7 项判定，轨迹不达标即 `FAIL`；`detail` 增 `trace_contract` / `runtime_pending` / `historical_e2e_evidence`）；状态仍 `BLOCKED` 但 `reason` 明确**轨迹部分已通过**。⑥ **验证（进程内实测，决定性）**：同一故障下两路径轨迹**逐键一致** —— `{rag_source: "builtin", builtin_fallback_reason: "OpenRAG 不可达: connection refused"}`；新增护栏 `tests/unit/test_rag_builtin_fallback_trace.py` **14 例**（首轮 **RED 11 failed / 3 passed**，失败信息即缺口证据）；既有回退/共用步骤/流式一致族 **89 例全绿**；执行器两态 `{PASS:3, SKIP:4, BLOCKED:2, FAIL:0}` / `{PASS:6, SKIP:1, BLOCKED:2, FAIL:0}`；全量 `tests/unit` **31 failed / 3117 passed / 0 error**（245.15 s），**零新增失败**（唯一差异为既有 flaky `test_v213_gateway_ext.py::TestWritebackInternalHandlers::test_rag_writeback_adapter_missing_raises` 本轮**转绿**，如实登记为**基线波动而非本批收益**）；3 文件 `ruff` **零告警**，执行器 5 项既有告警一并清零。⑦ **新增待登记项（能力缺口，非缺陷）**：T4 原文要求的「审计事件」当前落点为**接管 WARNING 日志**，**未写入 `AuditLog`**（`audit_service` 具备能力但**无调用点**）⇒ 接管可复盘但**不入审计库、无法按审计口径统计接管次数 / 时长分布**；已登记入方案 **§10 待登记项 6**，如需强审计须**单独立项**，本批**不代行决定**。⑧ **关系**：第二批第 ⑥ 项由「待做」改为「**部分完成**」（轨迹收敛已做；通道定性 / 通道裁决进取数层 / 内置 RAG 种子底座 / §4.3 余项 / 独立审计落库仍待）；§7 T4 判据表述与 §4.1 人工验证口径同步更新；v1.4.8 既有三项缺陷与既有 flaky 集**不受影响**；**全仓未闭环项仍为 0**。⑨ **同步**：方案 **v1.11.0**（§4.1 + §6 + §7 T4 + §10 + §11）；OpenLLM《DevLogReport》**v1.28.0**（第 39 批）；证据 `doc/test/evidence/cr149/t_acceptance_runner.py`、`t_acceptance_runner-result.json`、`t_acceptance_runner-simulate-result.json`、`OpenLLM/backend/cr149-t4-full.txt`（全量回归）、`cr149-b2h-full.txt`（基线对照）。⑩ 文档版本 **v1.45.0 → v1.46.0**，状态 [Review] |
| **v1.46.1** | **2026-09-27** | **AT-OpenBase-Test / AA-OpenBase-Dev** | **§4N 同批补充：T4「无 5xx」段补齐端点级（HTTP）故障注入证据（护栏 14 → 18 例），执行器运行态待验范围收窄**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.11.1** §7 T4；实现在 OpenLLM 仓（其《DevLogReport》**v1.28.1** 第 39 批补充，提交 `13707fc`）。② **动因**：v1.46.0 只把 T4 的**轨迹**段做成进程内可判，`runtime_pending` 仍列「故障注入后的 HTTP 响应无 5xx」。复核后确认该段**同样可在进程内判定** —— 以 `TestClient` 打**真实端点**、以**适配器替身抛异常**注入组件故障，无需停服。③ **新增护栏 4 例**（`TestEndpointLevelFaultInjection`，同一文件）：同步 `POST /openllm/v1/chat` 外部失败 + 开关开 → **200** 且轨迹 `rag_source=builtin` + 归因、**不计降级**；开关关 → **200**、`skipped` 无归因、`degraded` 含 `rag`；**装配缺失**（开关开）→ **200**、`skipped` 且**内置回退零调用**（`DEF-BE-148-012`）；**流式** `POST /openllm/v1/chat/stream` → **200**、`event: routing`/`event: done` 齐备且**无 `event: error`**、**落库轨迹入参**同样带来源与归因。④ **口径如实标注**：故障由**适配器替身**注入（＝组件故障），**非**停服务 / 改不可达地址；该层证明「组件故障时两端点均不返回 5xx 且轨迹可复盘」，**不替代运行态真实停服 E2E**；`_save_trace` 被替身替换 ⇒ 证明的是**落库调用入参**而非**实际落库读取**。⑤ **执行器同步**：T4 的 `runtime_pending` 收窄为「**真实**停服/改址注入」与「轨迹**实际落库**读取」两项、新增 `detail.endpoint_level_evidence`，`requires` 同步收窄；**状态仍 `BLOCKED`**（该项与 `has_base=true` 前置未满足）。⑥ **验证与回归**：全量 `tests/unit` **31 failed / 3121 passed / 0 error**（249.69 s；较 v1.46.0 的 3117 增 4 ＝ 本批补充护栏）；**失败集零新增**（与基线逐项 testid 归一化后 `Compare-Object` **无 `=>` 项**；差异项仍为既有 flaky `test_v213_gateway_ext.py` 一族交替转绿 ⇒ 如实登记为**基线波动**）；本轮 2 文件 `ruff` **零告警**。⑦ **关系**：§7 T4 判据表述进一步收窄运行态部分；§4N.2/§4N.3 同步更正；方案 §10 待登记项 6（接管审计事件未独立落库）**仍待**；第二批第 ⑥ 项仍为「部分完成」；**全仓未闭环项仍为 0**。⑧ **同步**：方案 **v1.11.1**（§7 T4 + §11）；OpenLLM《DevLogReport》**v1.28.1**（第 39 批补充）；证据 `t_acceptance_runner.py`、`t_acceptance_runner-result.json`、`t_acceptance_runner-simulate-result.json`、`OpenLLM/backend/cr149-t4b-full.txt`（全量回归）、`cr149-t4-full.txt` / `cr149-b2h-full.txt`（对照）。⑨ 文档版本 **v1.46.0 → v1.46.1**，状态 [Review] |
| **v1.47.0** | **2026-09-27** | **AT-OpenBase-Test / AA-OpenBase-Dev** | **仓内一致性审计（§4O 新建）：方案 §3.4 规则档余项与 §3.5 引用编号「正文已指定但未实施」登记；非缺陷、非变更请求、无代码改动**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.12.0** §3.4 / §3.5 / §6 / §10。② **动因与目的**：T4 收口后对方案正文做一次**逐条 vs 仓内实现**核对，确认「正文指定 ≠ 已实施」，避免"方案写了"被误读为"已完成"。③ **方法（可复现）**：对 `OpenLLM/backend/app/` 全仓检索 `strip_metadata` / `METADATA_NOISE` / `noise`、`"refine"`、`[M{` / `[K{` / `[M1]` / `[K1]`；并逐行读 `PromptAssembler.format_context` / `_format_list` 与 `prompt_pipeline._trim_segment` / `render()`。④ **结论（4 项未实施，均无外部依赖 ⇒ 可立即实施）**：**(a) 剥离元数据噪声**（`trace_id:None` 一类平铺字段）——检索零命中、平铺分支不过滤 `None`/空值且无噪声键名单；**(b) 相邻记忆条目合并同义重复行**——现有去重为「归一化后精确重复即丢弃」，非合并、无同义判定；**(c) `refine` 回执字段**——`"refine"` 检索零命中（**规则档亦无落痕**）；**(d) 稳定引用编号 `[M1]`/`[K1]`**——检索零命中，现仅 `"{序号}. {正文}"` 且裁剪后会**重排序号**（与「稳定」要求相反）。⑤ **同时确认已实施**（避免结论被扩大化）：§3.4 规则档的**去重 / 配额整条裁剪 / 单条句边界截断**、§3.5 的 **`system` 段启用**。⑥ **登记位置**：方案 §3.4 / §3.5 各增「实施状态」表（含取证）；§6 第二批新增第 **⑦** 行（**未实施且不受阻**，与 ⑥ 中需人工裁定各项明确区分）；§10 新增**待登记项 7**（含默认值建议：(d) 建议开关默认关闭）。⑦ **关系与影响**：**无新增缺陷、无新增债务**；已判 `PASS` 判据（T3/T7/T9）与已知 `BLOCKED`/`SKIP` 结论**不受影响**；**全仓未闭环项仍为 0**；**下一步（不受阻）** 优先实施 (a)~(d)，其中 (c) 需先定义规则档回执的**落痕位置**（`context_metrics` 内嵌字段 还是独立字段）。⑧ **同步**：方案 **v1.12.0**（§3.4 + §3.5 + §6 + §10 + §11）；本记录 **§4O 新建**；**无 OpenLLM 代码提交**（纯文档登记）。⑨ 文档版本 **v1.46.1 → v1.47.0**，状态 [Review] |
| **v1.48.0** | **2026-09-27** | **AA-OpenBase-Dev / AT-OpenBase-Test** | **上下文精装配第二批第 ⑦ 项实施登记（§4P 新建）—— 方案 §3.4 规则档余项 ＋ §3.5 引用编号**四项**已实施落地**（闭环 §4O 登记）；**新增判据 T10 并拆分 T6**；无新增缺陷、无新增债务**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.13.0** §3.4/§3.5/§6/§7 T10/§10；实现在 OpenLLM 仓（其《DevLogReport》**v1.29.0** 第 40 批，提交 `9f5f711`）。② **实施四项**：**(a) 元数据噪声剥离**（`CONTEXT_STRIP_METADATA_ENABLED` 默认 **True**；实测单条载荷省 **74 token**；关闭逐字回退）；**(b) 相邻记忆条目同义合并**（`CONTEXT_ADJACENT_MERGE_ENABLED` 默认 True、阈值 `0.85`；**仅 memory、仅相邻、保留较长者**；`merged_items` 与 `dropped_items` 计数**分离**；口径为**确定性近似**，非语义级同义）；**(c) `refine` 回执**（`{mode:"rule", model:"", in_tokens, out_tokens, elapsed_ms, fallback:False}`，`in/out` 只计四类素材，未启用不落痕）；**(d) 稳定引用编号 `[M#]`/`[K#]`**（`CONTEXT_REF_NUMBERS_ENABLED` **默认 False** ⇒ 文本形态不变；与归因 A 下标对齐；**去重/裁剪后不重排**）。③ **判据扩展**：§7 **新增 T10**（组装规则档契约，**全部进程内可判**）；**T6 拆分** —— 规则档回执进程内可判、模型档仍 `BLOCKED`（第三批）；执行器 `check_t10` ⇒ 判据 **T1~T9 → T1~T10**。④ **验证（决定性）**：新增护栏 `tests/unit/test_assembly_refine_rule_tier.py` **25 例**（首轮 **RED 16 failed / 8 passed**）；预算/组装族既有护栏 **101 例全绿**；**运行态探针** `doc/test/evidence/cr149/assembly_rule_tier_probe.py` 逐项给出数值（(b) `merged_items=1`/`merged_tokens=16`/rag 不合并；(c) `in=807→out=100`；(d) `[M1]`+`[M3]` 保留、`[M2]` 不复用）；**执行器两态** `{PASS:4, SKIP:4, BLOCKED:2, FAIL:0}` / `{PASS:7, SKIP:1, BLOCKED:2, FAIL:0}`。⑤ **回归与静态质量**：全量 `tests/unit` **32 failed / 3145 passed / 0 error**（249.81 s）；**对照实验（决定性）**：`git stash push -- <本批 3 个生产文件>` 后**隔离复跑 `test_v213_gateway_ext.py` 得到完全相同的 4 个失败** ⇒ 该 flaky 一族**与本批无关**（如实登记为基线波动）；本轮 4 文件 `ruff` **零告警**。⑥ **语义与影响面**：(a)(b) 默认开启但**仅在预算开启时生效**（`CONTEXT_BUDGET_ENABLED` 默认 **False**）且各有开关可回退；(c) 纯观测；(d) 默认关闭 ⇒ **线上 Prompt 文本形态不变**。⑦ **载体与登记**：本记录 **§4P 新建**（§4O 登记项实施闭环）；方案 **v1.13.0**（§3.4/§3.5 实施状态 ＋ §6 第二批 ⑦ ＋ §7 T6 拆分/T10 新增 ＋ §10 第 7 项闭环 ＋ §11）；OpenLLM《DevLogReport》**v1.29.0**（第 40 批）；证据 `openbase/doc/test/evidence/cr149/assembly_rule_tier_probe.py` 与 `-result.json`、`t_acceptance_runner-result.json`、`t_acceptance_runner-simulate-result.json`、`OpenLLM/backend/cr149-t10-full.txt`（全量回归）、`cr149-t4b-full.txt`（基线对照）。⑧ **残留（未实施，如实登记）**：模型档生成式精炼（第三批）、通道定性（§9 问题 1 待裁定）、通道裁决进取数层、内置 RAG 种子底座（运行态 DB ＋ 嵌入模型）、§4.3 余项（画像增量升级形态 / 写路径与通道一致）、独立审计落库（方案 §10 待登记项 6）；**全仓未闭环项仍为 0**。⑨ 文档版本 **v1.47.0 → v1.48.0**，状态 [Review] |
| **v1.49.0** | **2026-09-27** | **AA-OpenBase-Dev / AT-OpenBase-Test** | **仓内一致性审计（续，§4Q 新建）：§3.2 权重排序 `rank_score` 未实施 → 同版实施闭环（第二批第 ⑦ 项续，判据 T10 增补第 ④ 项）；无新增缺陷、无新增债务**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.14.0** §3.2/§3.3/§6/§7 T10/§10；实现在 OpenLLM 仓（其《DevLogReport》**v1.30.0** 第 41 批，提交 `d80085f`）。② **审计发现（取证）**：方案 §3.2 第三项要求「在重排分数之外**叠加时效与来源权重**，产出统一的 `rank_score` 供预算层使用」、§3.3 memory/rag 行要求「按 `rank_score` **降序保留整条**」；**全仓检索 `rank_score` 零命中** ⇒ **未实施**；现有实现按**取数原序**保留并从**尾部**整条丢弃 ⇒ **丢弃对象是「取数最末」而非「排名最低」**（当取数序与相关性/时新性不一致时，可能丢掉更相关或更新的条目 —— 属「**选得不准**」，与方案 §2 原则 1 相悖）。③ **实施**：`PromptAssembler._ordered_items` / `_rank_score` / `_item_decay`；`rank_score` ＝ **来源分数**（`score`/`relevance`，缺失中性 1.0）× **时效衰减**（**仅 memory**：`0.5 ** (age_days / 半衰期)`，默认 30 天；其余段保留原始 score）；**fail-open**（时间戳缺失/不可解析 ⇒ 衰减 1.0，**不得因缺字段被降级**）；**稳定排序**；**排序只改呈现顺序、引用编号仍取原始下标**（与归因 A 不脱钩）；**fail-safe**（开关关 / 条目 < 2 / **无任何可用排序依据** ⇒ **保持原序**，不臆造顺序）。④ **判据扩展**：§7 **T10 增补 ④ 权重排序**，执行器 `check_t10` **PASS**。⑤ **验证（决定性）**：新增护栏 `tests/unit/test_context_rank_selection.py` **12 例**（首轮 **RED 8 failed / 4 passed**）；组装/预算/回退族既有护栏 **143 例全绿**；**运行态探针** `assembly_rule_tier_probe.py` **(e)** 段实测 `rag_order="1. 高分/2. 中分/3. 低分"`、`memory_order="1. 新记忆/2. 无时间戳记忆/3. 旧记忆"`（fail-open 生效）、`labeled_ranked="[K2] 高分\n[K1] 低分"`（编号取原始下标）、开关关 `"1. 低分\n2. 高分"`、无依据 `"1. 甲/2. 乙/3. 丙"`、尾部丢弃 `dropped_items=1` 且排名靠前者存活；执行器两态 `{PASS:4, SKIP:4, BLOCKED:2, FAIL:0}` / `{PASS:7, SKIP:1, BLOCKED:2, FAIL:0}`。⑥ **回归与静态质量**：全量 `tests/unit` **32 failed / 3157 passed / 0 error**（247.93 s）；**失败集与上一轮基线逐项完全相同**（`Compare-Object` **32 = 32，零差异 ⇒ 零新增失败**）；本轮 3 文件 `ruff` **零告警**。⑦ **同时确认（避免结论扩大化）**：§3.3 profile 行「按维度优先级保留（person → business → 其他）」**已按 section 粒度实施**（`_format_profile_ctx` 固定 person → business，配额裁剪从尾部丢弃 ⇒ 低优先 section 先被丢），**字段级**优先级未细分。⑧ **关系与登记**：本记录 **§4Q 新建**；方案 **v1.14.0**（§3.2/§3.3 实施状态 ＋ §6 第二批 ⑦ ＋ §7 T10④ ＋ §10 待登记项 7 合并为三项闭环 ＋ §11）；OpenLLM《DevLogReport》**v1.30.0**（第 41 批）；证据 `doc/test/evidence/cr149/assembly_rule_tier_probe.py` 与 `-result.json`、`t_acceptance_runner-result.json`、`t_acceptance_runner-simulate-result.json`、`OpenLLM/backend/cr149-t14-full.txt`（全量回归）、`cr149-t10-full.txt`（基线对照）。⑨ **残留（未实施，如实登记）**：模型档生成式精炼（第三批）、通道定性（§9 问题 1 待裁定）、通道裁决进取数层、内置 RAG 种子底座（运行态 DB ＋ 嵌入模型）、§4.3 余项（画像增量升级形态 / 写路径与通道一致）、独立审计落库（方案 §10 待登记项 6）；**全仓未闭环项仍为 0**。⑩ 文档版本 **v1.48.0 → v1.49.0**，状态 [Review] |
| **v1.50.0** | **2026-09-27** | **AA-OpenBase-Dev / AT-OpenBase-Test** | **逐条复核发现的三处「正文已指定但未实施」同版实施闭环（§4R 新建，判据 T10⑤ / T11 新增）；无新增缺陷、无新增债务**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.15.0** §3.2/§3.3/§4.3/§5.8/§7 T10·T11；实现在 OpenLLM 仓（其《DevLogReport》**v1.31.0** 第 42 批，提交 `58358c6`）。② **复核方法（可复现）**：对 §3.2/§3.3/§4.2/§4.3/§5.8 **逐行**比对仓内实现，并对关键标识**全仓检索**（`rank_score`、`whitelist`、`assert_write_channel_is_primary`、`refine`）。③ **三处发现**：**(1) §4.3 写路径与通道一致** —— `assert_write_channel_is_primary` **已实现**但全仓**仅被单测与脚本引用**（`app/` 内**零调用点**、状态机**从未实例化**）⇒ §8 风险表所列回退手段**未接线**、「切换期间双写」**无防护**；**(2) §3.2 画像维度白名单 ＋ §3.3 profile 维度级优先级** —— 画像 `whitelist` 配置键**零命中**，且维度被**压成一行** ⇒ 裁剪最小单位是**整段**、「丢弃低优先维度」**无法实现**；**(3) §3.3/§5.8 `refine` 落 `context_metrics`** —— `to_record()` 仅落 `segment_tokens`/`budget`/`truncated`，`refine` **仅在内存** ⇒ **观测链缺一环**。④ **实施**：**(1)** 三路回写在 `submit` 前校验写通道为**唯一主通道**（`_get_channel_manager()` 每次按配置构造 ⇒ 热改生效），**非主通道 ⇒ 暂停本轮回写**（`skipped`、**零入队**、`reason=channel_not_primary`，与价值闸门同口径且不与 `False` 混用；**暂停而非抛错**），开关 `WRITEBACK_CHANNEL_GUARD_ENABLED` **默认 True**、**配置非法 ⇒ WARN + 放行**（fail-open）；**(2)** `PROFILE_DIMENSION_LINES_ENABLED`（**默认 True**）令**每行一个维度** ⇒ 超配额先丢 `business` 维度，`PROFILE_DIMENSION_WHITELIST`（留空=不限制）控制保留与排序、无命中返回空；**(3)** `ContextReceipt.to_record()` 增 `refine`（仅非空时落痕）。⑤ **判据扩展**：§7 **T10 补 ⑤** ＋ **新增 T11**（写路径与通道一致，**进程内可判**）；执行器判据扩为 **T1~T11**。⑥ **验证（决定性）**：新增护栏 **20 例**（`test_writeback_channel_guard.py` 8 ＋ `test_profile_dimension_priority.py` 10 ＋ `test_assembly_refine_rule_tier.py` 增 2，**首轮 RED 14 failed**）；画像/回写/计量族既有护栏 **99 例全绿**；**运行态探针** `writeback_channel_guard_probe.py`（`paused=true`/`unchanged=true`/`verbatim=true`/`allowed=true`）与 `assembly_rule_tier_probe.py` **(f)(g)** 段；**执行器两态** `{PASS:5, SKIP:4, BLOCKED:2, FAIL:0}` / `{PASS:8, SKIP:1, BLOCKED:2, FAIL:0}`。⑦ **回归与静态质量**：全量 `tests/unit` **31 failed / 3176 passed / 0 error**（246.58 s）；**失败集零新增**（逐项 testid 归一化后 `Compare-Object` **无 `=>` 项**；差异项仍是既有 flaky `test_v213_gateway_ext.py` 一族 ⇒ **基线波动**）；本轮 6 文件 `ruff` **零告警**。⑧ **语义与影响面**：(1) 默认 `b-primary` ⇒ **线上行为不变**，仅通道切到 A 的切换期间才暂停回写（**即设计意图**）；(2) 画像文本形态由「单段一行」变为「段头 ＋ 每行一个维度」（**默认开启**、开关可回退；**白名单默认留空 ⇒ 不删任何维度**）；(3) 纯观测扩展。⑨ **关系与登记**：本记录 **§4R 新建**；方案 **v1.15.0**（§3.2/§3.3/§4.3/§5.8 实施状态 ＋ §7 T10⑤/T11 ＋ §10 待登记项 8 ＋ §11）；OpenLLM《DevLogReport》**v1.31.0**（第 42 批）；证据 `doc/test/evidence/cr149/writeback_channel_guard_probe.py` 与 `-result.json`、`assembly_rule_tier_probe.py` 与 `-result.json`、`t_acceptance_runner-result.json`、`t_acceptance_runner-simulate-result.json`、`OpenLLM/backend/cr149-t15-full.txt`（全量回归）、`cr149-t14-full.txt`（基线对照）。⑩ **残留（未实施，如实登记）**：§4.3「写路径 A/B 等价」**矩阵登记项**（取决于 §9 问题 1 通道定性裁定）、通道 A 定性、模型档生成式精炼（第三批）、通道裁决进取数层、内置 RAG 种子底座（运行态 DB ＋ 嵌入模型）、§4.3 画像增量升级的线上 LLM 门控（§9 问题 7）、独立审计落库（方案 §10 待登记项 6）；**全仓未闭环项仍为 0**。⑪ 文档版本 **v1.49.0 → v1.50.0**，状态 [Review] |
| **v1.51.0** | **2026-09-27** | **AA-OpenBase-Dev / AT-OpenBase-Test** | **逐条复核发现的第 4 处「正文已指定但未实施」（§4S 新建）：§5.8「路由分类按 query 归一化缓存」同版实施闭环（判据 T9 补 ④）；无新增缺陷、无新增债务**。① **来源**：《OpenBase-上下文精装配与组件通道优化技术方案》**v1.16.0** §5.8/§7 T9；实现在 OpenLLM 仓（其《DevLogReport》**v1.32.0** 第 43 批，提交 `3bb9a3f`）。② **审计发现（取证）**：§5.8 在线档预算行要求「**路由分类按 query 归一化缓存**」（同题重复提问不重复分类、不重付 **≤300ms** 兜底预算）；**`ComponentRouter` 全类检索 `cache` 零命中**、`decide()` 每次未命中规则都**重新调用** `llm_classifier` ⇒ 重复提问**重复付预算**。**关键约束**：**联网关每次请求都新建 `ComponentRouter`**（分类器闭包捕获 db/identity）⇒ 缓存**必须进程级**，否则永不命中。③ **实施**：进程级 LRU（`_LLM_DECISION_CACHE` ＋ 锁）；键 ＝ **`模型标签:规则指纹`** ＋ **归一化 query**（压缩空白 ＋ 大小写不敏感）；`_refresh_rules_fingerprint()` 在两处规则替换点（初始加载 / 热更新）调用 ⇒ **规则变更后旧条目自然失配**；作用域含模型标签 ⇒ **换模型亦失配**；**命中返回副本**、**失败与非法输出不入缓存**、**容量 0 = 关闭**（逐字回退）；`COMPONENT_ROUTER_LLM_CACHE_SIZE` 默认 **256**；新增 `clear_llm_decision_cache()` / `llm_decision_cache_size()` 供隔离与观测。④ **同批隔离修正（非放宽）**：进程级缓存使两处既有文件中「同一 query ＋ 不同分类器替身」用例**跨用例命中**（实测 **4 failed**）⇒ 各加 **autouse 清缓存 fixture**，**不改任何断言**；修正后两文件 **77 例全绿**。⑤ **判据与验证**：§7 **T9 补 ④**，执行器 `check_t9` **PASS**；新增护栏 **14 例**（首轮 **RED 6 failed**）；**运行态探针** `component_decision_probe.py` **④** 段（`same_query_calls=1`/`distinct_query_calls=2`/`cached_decision_equal=true`/`capacity_zero_calls=2`/`default_capacity=256`）；执行器两态 `{PASS:5, SKIP:4, BLOCKED:2, FAIL:0}` / `{PASS:8, SKIP:1, BLOCKED:2, FAIL:0}`。⑥ **回归与静态质量**：全量 `tests/unit` **32 failed / 3189 passed / 0 error**（249.94 s）；与上一轮基线逐项对照**唯一差异为既有 flaky `test_v213_gateway_ext.py` 一族本轮转红**（该例往返红/绿交替，已多次对照实验证明与本批无关）；**ruff 逐文件基线对照（`git stash` 回退后复测）**：`component_router.py` **39 → 39**、`config.py` **0 → 0**、既有测试文件 **0 → 0 / 2 → 2**、新测试文件 **0** ⇒ **零新增告警**。⑦ **语义与影响面**：缓存**仅在 LLM 兜底分类器被注入时生效**（`COMPONENT_ROUTER_LLM_FALLBACK_ENABLED` **默认关闭** ⇒ 线上默认路径**零影响**）；LRU 有界；命中返回副本、失败不固化、规则/模型变更即失配 ⇒ **不引入陈旧决策**。⑧ **关系与登记**：本记录 **§4S 新建**；方案 **v1.16.0**（§5.8 缓存行 ＋ §7 T9④ ＋ §10 待登记项 9 ＋ §11）；OpenLLM《DevLogReport》**v1.32.0**（第 43 批）与 **v1.32.1**（同批文档订正）；证据 `doc/test/evidence/cr149/component_decision_probe.py` 与 `-result.json`、`t_acceptance_runner-result.json`、`t_acceptance_runner-simulate-result.json`、`OpenLLM/backend/cr149-t16-full.txt`（全量回归）、`cr149-t15-full.txt`（基线对照）。⑨ **残留（未实施，如实登记）**：§5.8 **精炼结果缓存**（规则档确定性且亚毫秒 ⇒ 无收益；模型档属第三批 ⇒ 与第三批同批推进）、通道 A 定性（§9 问题 1）与 §4.3「写路径 A/B 等价」矩阵项、模型档生成式精炼、通道裁决进取数层、内置 RAG 种子底座（运行态 DB ＋ 嵌入模型）、§4.3 画像增量升级的线上 LLM 门控（§9 问题 7）、独立审计落库（方案 §10 待登记项 6）；**全仓未闭环项仍为 0**。⑩ 文档版本 **v1.50.0 → v1.51.0**，状态 [Review] |
| **v1.52.0** | **2026-09-27** | **AA-OpenBase-Dev / AT-OpenBase-Test** | **复核发现「§5.2 精炼触发条件表 ＋ §5.3 任务护栏」未实施 → 判定部分同版闭环（§4T 新建；判据 T12 新增，执行器扩为 T1~T12）**。① **审计取证**：全仓检索 `should_refine` / `CONTEXT_REFINE` / `validate_refine` **零命中** ⇒ ① `CONTEXT_BUDGET_ENABLED` 打开后**一律走规则档**（无从判断「何时该升级到精炼」）；② 第三批接模型档时**缺少「何时该调模型」与「模型输出是否可用」两道闸门**。**为何可先行**：判定与校验均为**纯函数**（不依赖模型/运行态 DB）⇒ **进程内可判**。② **实施**：新增 `orchestration/refine.py`（纯函数库）—— `refine_triggers()`（行 1~3：超配额 **1.5** 倍 / 条目 > **8** / 重复占比 > **30%**，阈值全配置驱动、**严格大于**；`history`/`profile` 不参与）＋ `validate_refine_output()`（§5.3：`unlocatable` / `new_numbers` / `not_numbered` / `empty_output` ⇒ `valid=false` 即弃）；相似度与「相邻同义合并」**共用** `prompt_pipeline.is_redundant_pair`（避免分叉）；触发**观测**由 `CONTEXT_REFINE_TRIGGER_ENABLED`（默认关闭）驱动、**只读**（开关两态注入文本逐字相同）。③ **行 4（多源冲突）如实标注未实施**（需语义判定）⇒ `unimplemented=["multi_source_conflict"]` 显式列出、词表**不含** conflict 类理由（**不伪实现**）。④ **护栏（TDD，22 例，首轮 RED 5 failed）**：新增 `test_refine_trigger_and_guard.py`（含三条**阈值边界**不触发、行 4 未实施标注、护栏四类违规、开关两态注入文本逐字相同）。⑤ **探针**：新增 `refine_trigger_probe.py`（行 1 `160/100=true`/`150/100=false`；行 2 `9=true`/`8=false`；行 3 `50%=true`/`25%=false`；`prompt_identical=true`）。⑥ **判据**：§7 **新增 T12**（纯进程内可判）。⑦ **回归**：全量 `tests/unit` **31 failed / 3212 passed**，**失败集零新增**（唯一差异为既有 flaky 转绿）；`ruff` 全绿。⑧ **提交**：OpenLLM `4f3e706`（4 生产/配置 ＋ 1 测试，`+605/-7`）。**⑨ 同期文档整改（本次补记）**：本行对应批次**未同步写入 §5 修订历史与文档版本**（仅 §4T 正文），本次随 v1.53.0 一并**补记与升版**。状态 [Review] |
| **v1.53.0** | **2026-09-27** | **AA-OpenBase-Dev / AT-OpenBase-Test** | **既有失败逐项分诊（31 → 21，闭环 10）＋ §4.3 执行层价值闸门补齐 ＋ 本方案自身判据的时效基准订正（§4U 新建）**。① **动因**：CR-149 此前各批次均以「与本批无关」的对照实验绕过 **31 项既有失败**，**从未逐项分诊** ⇒ 可能掩盖**本方案范围内的真实缺陷**。② **范围内真实缺陷（1 例，已修）**：`_rag_writeback` **只写不读** `save_if_valuable`（全仓**无读取方**）⇒ §4.3 要求的「实际判定**而非仅契约字段**」只落在**网关决策层**；**执行层**与**直接调用** `POST /openllm/v1/writeback` 的路径**不受闸门约束** ⇒ 显式声明「不值得沉淀」仍入库（**知识库膨胀入口未闭合**）。**修法**：`save_if_valuable=false` ⇒ **零请求**收口（INFO ＋ 返回 `None` ＋ 行置 done），**跳过先于适配器校验**（不写就不需要适配器），**缺省视为 true ⇒ 逐字回退**。③ **范围内陈旧/失隔离用例（9 例，已修且断言不降反升）**：`test_writeback_degradation` **3**（返回值元数 3→4 ＋ **替身注册顺序**须在构造回调之后 —— `DEF-BE-148-021` 的生产 handler 会覆盖先注册的替身）；`test_v213_gateway_ext` **3**（补丁替身 4→**5** 元组致端点 500；两例**不自持前置**致顺序漂移）；`test_real_contract_memory` **3**（`_resolve_memory_metadata` **全仓历史零命中**的**幻影符号**，已按**实际分层**重写为 4 例）。④ **本方案自身判据缺陷（3 项，已修）**：T10 ④ 与探针 (e) 以**硬编码时刻**作时效基准 ⇒ 断言**随壁钟自行翻转**（**同一提交** 12:00 前 `PASS`、之后 `FAIL`），且原断言与 fail-open 语义不符（fail-open 恰 1.0 ⇒ 等价「刚刚发生」而非「更差」）⇒ 改**相对基准** ＋ **严格单调**（1.0 > 0.977 > 0.0625）＋ **fail-open 恰为 1.0** 三条确定性判定，并落 `detail.rank_decay`；同源基准同步订正 `test_context_rank_selection.py::_iso`。⑤ **判据扩展**：**T5 分两段** —— 段②执行层闸门**无开关、恒生效** ⇒ 进程内恒可判、不达标即 `FAIL`；执行器新增 `_rag_value_gate_probe()`。⑥ **护栏**：新增 `test_rag_writeback_value_gate.py` **7 例**（RED 由既有用例 `test_save_if_valuable_false_skips_without_request` 指认）。⑦ **回归（两轮独立）**：`cr149-t18`/`cr149-t19` 均 **21 failed / 3230 passed / 0 error**（252 s），**新增失败集为空 ⇒ 零回归**、已消失 **10** 项，**两轮失败集逐项零差异 ⇒ 可复现**。⑧ **范围外（如实登记，未改）**：401 族 **9**（断言错误体不含 `detail`，与项目错误规范相反）／「模型不存在」错误码族 **3**（`2001` vs `5001`/`1004`）／环境条件类 **4**（工作区 `.env` 置三个 `REAL=true` 而用例断言 dev 缺省 false）／`test_model_router_wiring` **2**／`test_joinedload_asserts` **2**（用例自身构造错误）／`test_conversations_api` **1**。⑨ **提交**：OpenLLM `ee0dba9`（1 生产 ＋ 4 测试，`+327/-46`）。文档版本 **v1.51.0 → v1.53.0**（含补记 v1.52.0）。状态 [Review] |
| **v1.54.0** | **2026-09-27** | **AA-OpenBase-Dev / AT-OpenBase-Test** | **判据保真度订正（T3 分段）＋ 开关开启值批准包交付（方案 §7.1）＋ 配置面死开关结构护栏（§4V 新建）**。① **判据保真度缺陷（本轮新发现，与 v1.53.0 订正的 T10④ 同源，已修）**：§7 **T3** 原文为「**启用 rerank 后** rag 条目的 score 单调性成立、低分条目被 `score_threshold` 过滤」，但执行器实现**只在条目级传参**（`rerank=True`/`score_threshold=0.5`）下断言「透传 ＋ 过滤后条目数下降、score 单调」，**全程未触及全局开关**（实测 `RAG_RERANK_ENABLED=False`）却判 `PASS` ⇒ **判据被实现成「透传契约」却挂着「启用后生效」的名字**，会把「开关关着时口径正确」误读为「rerank 已达标可用」。**修法（与 T4/T5/T6 同一写法）**：拆为 ① **口径段（无开关，恒可判）**＝条目级参数优先、`0`/非法值 ⇒ **不过滤**、过滤后**条目数下降**且 score **单调**；② **生效段（需开关）**＝开关开启后**未传条目参数**的检索确实带上重排与阈值（关闭时以**临时置位**证明能力，口径同 T8），真实检索侧重排质量留 `runtime_pending`。② **`--simulate` 置位集合扩展**：再含 `RAG_RERANK_ENABLED`/`RAG_SCORE_THRESHOLD` 与 `COMPONENT_DEPENDENCY_SCHEDULING_ENABLED` ⇒ **一次运行即证明全部四处开关门控判据（T1/T2/T3/T5/T8）在开启态均达标**；两态实测 **当前配置** `{PASS:5, SKIP:5, BLOCKED:2, FAIL:0}` / `--simulate` **`{PASS:10, SKIP:0, BLOCKED:2, FAIL:0}`**（T3 由「误判 PASS」改为**如实 SKIP ＋ 能力已验**，属**判据更正而非能力回退**）。③ **新增方案 §7.1「开关开启值建议（批准包）」**：§7 的 T1/T2/T3/T5/T8 在**当前配置**下为 `SKIP`（**开关未开**，非能力不足），而 §7 要求「**人工批准开关开启值后复跑**」——**批准是这些判据前进的唯一前置**，此前**无交付物**。§7.1 以 **18 行**逐键给出「当前值 → 建议值 / 设计·实测依据 / 影响面 / 回退」，并给出**批准粒度与门禁**：**建议本次开启 6 项**（`CONTEXT_BUDGET_ENABLED`、`CONTEXT_SYSTEM_PROMPT_ENABLED`、`RAG_RERANK_ENABLED`＋阈值 `0.15`、`COMPONENT_DEPENDENCY_SCHEDULING_ENABLED`、`WRITEBACK_DECISION_ENABLED`、`CONTEXT_REFINE_TRIGGER_ENABLED`＝**纯观测零注入变化**）；**建议暂缓 1 项**（`CONTEXT_REF_NUMBERS_ENABLED`，依赖**归因 A 消费方**解析标签，否则只是文本形态变更）；**依赖裁定不得代行 3 项**（窗口/预留＝§9 问题 3、system 指令**文案**＝业务口径、`CHANNEL_PREFERENCE`/自动回落＝§9 问题 1、5）；**明确维持关闭 1 项**（`COMPONENT_ROUTER_LLM_FALLBACK_ENABLED`：≤1B 分类器 300 ms 内不达标，本机 P50 2.33 s / 局域网 0.60 s）；**复跑命令**随节给出（一条命令）。**边界如实标注**：#11 `WRITEBACK_DECISION_ENABLED` **只决定「是否沉淀」**、`memory` 载荷**仍为整轮全文** ⇒ **不触及** §9 问题 4。④ **配置面「只写不读」审计推广（新增结构护栏 4 例）**：§4U 已确认 `save_if_valuable` **只写不读**（本方案范围内真实缺陷）；同口径推广到配置面即「**声明了但无读取点的键＝死开关**」。新增 `tests/unit/test_cr149_config_keys_wired.py`：受护栏前缀**全部配置键**须在 **`backend/` 全树**（排除 `tests/` 与 `config.py`）**至少一个读取点**，且「未接线集合」须**恰为已登记白名单**（多一个即新增死开关、少一个即已接线 ⇒ **双向报警**）；白名单**逐项给理由**；另以断言锁定「须覆盖 `backend/main.py`」与「排除 `tests/`」。**审计结论**：本方案范围 **48 键全部有读取点 ⇒ 未发现死开关**；唯一未接线键 `PROFILE_DRIFT_RECOMPUTE_INTERVAL` 属 **DT-214-305**（**非本方案范围**，`profile_drift` 按设计只交付**驱动侧接口**）⇒ 白名单并给理由。**审计口径修正（如实登记）**：首版脚本**只扫 `app/`**，把读点在 **`backend/main.py`（lifespan 驱动清理循环）** 的 `WRITEBACK_CLEANUP_INTERVAL_SECONDS` **误报为死开关** ⇒ 护栏改为**全 `backend/` 扫描**并以断言锁定该口径。⑤ **回归与静态质量**：全量 `tests/unit` **21 failed / 3234 passed / 0 error**（256.99 s；较上轮 3230 增 **4** ＝本批护栏）；**与上一轮逐项 testid 归一化 `Compare-Object` 差异 0 项 ⇒ 零回归**，且**连续三轮（`t18`/`t19`/`t20`）失败集逐项零差异 ⇒ 可复现**；本批 1 文件 `ruff` **All checks passed**；执行器与探针 `ruff` **All checks passed**。⑥ **语义与影响面**：**本批无生产代码改动**（执行器/文档/护栏均在**判据与工具侧**）⇒ **线上行为零变化**。⑦ **提交**：OpenLLM `7efa6ec`（`test(v149)`，1 文件 `+121`）。文档版本 **v1.53.0 → v1.54.0**；状态 [Review] |
| **v1.55.0** | **2026-09-27** | **AA-OpenBase-Dev / AT-OpenBase-Test** | **判据残句子句归类（T3 的 `used_ratio` 子句）＋ 文档-实现漂移审计工具化（0 真实缺口）（§4W 新建）**。① **判据「只覆盖原文子集而未声明」（第三类判据保真度缺陷，已归类）**：§7 **T3** 原文三条子句 —— score 单调 / 低分被阈值过滤（条目数下降）/ **`used_ratio` 不降**；前两类已由 v1.18.1 的分段判据覆盖，**第三条既未被判定、也未被声明为未覆盖**。**取证**：`used_ratio` 是**归因 A**（`context_metrics.attribution_a()`）的指标 ＝ **回答引用了多少条注入片段**（`used/total`），其 docstring 明确「该规则保守…**只能纵向对比、不得作绝对值解读**」⇒ **取值依赖 LLM 回答内容** ⇒ 不能用构造回答做成**进程内确定性**判据。**处置**：① §7 T3 行**显式划出**该子句并标注归属＝**评测集**上做「rerank 开/关」对照（聚合比较），归 §6 **第三批**「评测集与验收判据扩展」；② 执行器新增 `detail.evaluation_pending` —— 凡判据原文中**进程内不可判**的子句**显式列出**、**不以近似断言冒充覆盖**（首个用例即该子句）。**与 v1.18.0/v1.18.1 的关系**：三批共同构成**判据保真度**整治 —— v1.18.0「判据随壁钟翻转」→ v1.18.1「判据挂名错位（未触全局开关却判 PASS）」→ v1.18.2「判据只覆盖原文子集而未声明」。② **文档-实现漂移审计工具化（新增可复跑工具）**：**动因**是本仓**历史真实教训** ——「正文声称配置键 `OPENLLM_PROFILE_LLM_REFINE` 已存在，实际全树无此键」（v1.9.0 更正）与「`profile_refine` 源码**未随提交落库**却被正文当作已交付」（`DEF-BE-148-029`）；此前只能人工逐条复核、**不可复跑**。**做法**：新增 `doc/test/evidence/cr149/check_doc_claims.py`（＋ `check_doc_claims-result.json`），抽取正文**全部反引号引用的标识符**，在 **OpenLLM 全树**（`app/` ＋ `tests/` ＋ `main.py` ＋ `mock_services/`）与 **OpenBase 证据目录**中核对存在性（支持**定义式/声明式/文件名/子串**四类命中，覆盖「护栏文件名」与「f-string 内违规码」两类易漏形态），支持 `--json`。③ **方法学两次修正（如实登记，避免「审计被自己驯服」）**：**(a)** 首版**未区分「引用为存在」与「引用为缺失」**、也不扫 `tests/` ⇒ **误报 68 项**（把「正确地说某物不存在」、族前缀 `CONTEXT_*`/`RAG_RERANK*`、护栏文件名都当成缺失）；**(b)** 改成「整行级跳过」后**反而过宽**（宽泛标记吞掉整行 ⇒ 审计失去意义）⇒ 最终定为「**邻近上下文（±80 字）＋ 精简标记集（零命中/不存在/未实施/未接线/待登记/幻影等）＋ 逐项可回溯的取证词白名单（3 检索取证词 ＋ 2 工件名片段，各给理由）**」。④ **审计结论**：**「引用为存在」214 项全部可核对 ⇒ 0 真实缺口**；跳过 **50** 项（引用为缺失 / 族前缀 / 取证词 / 工件名片段）—— 即**方案正文未发现「声称已实施而仓内查无此项」的条目**。**边界说明**：该工具只核对**符号存在性**，**不替代**行为级判据（后者由 §7 执行器与 `tests/unit` 承担）。⑤ **回归与静态质量**：**本批无 OpenLLM 生产代码改动** ⇒ **线上行为零变化**；执行器两态与 v1.18.1 **完全一致**（**当前配置** `{PASS:5, SKIP:5, BLOCKED:2, FAIL:0}`；`--simulate` `{PASS:10, SKIP:0, BLOCKED:2, FAIL:0}`），仅 T3 `detail` 增 `evaluation_pending`；执行器与新增工具 `ruff` **All checks passed**；全量回归未复跑（无生产代码改动，沿用 v1.18.1 的 `21 failed / 3234 passed` 三轮稳定基线）。⑥ **待人工动作（不变）**：方案 §7.1 批准包仍待人工批准（T1/T2/T3/T5/T8 由 `SKIP` 转 `PASS` 的唯一前置）。⑦ **提交**：仅 **OpenBase** 侧（`doc/test/evidence/cr149/t_acceptance_runner.py`、新增 `doc/test/evidence/cr149/check_doc_claims.py` 与 `check_doc_claims-result.json`、两态结果 JSON、本文档），**无 OpenLLM 代码提交**。文档版本 **v1.54.0 → v1.55.0**；状态 [Review] |
| **v1.56.0** | **2026-09-27** | **AA-OpenBase-Dev / AT-OpenBase-Test** | **护栏覆盖与日志合规两项静态审计（均 0 真实缺口）＋ 方案 §9.1「裁定清单与解锁关系」交付（§4X 新建）**。① **第四类保真度问题（本仓历史真实风险，审计后 0 缺口）**：前几批已整治三类 —— v1.18.0「判据随壁钟翻转」（T10④ 硬编码时效基准）、v1.18.1「判据挂名错位」（T3 未触全局开关却判 `PASS`）、v1.18.2「判据只覆盖原文子集而未声明」（T3 的 `used_ratio` 子句）；本轮补第四类 ——「**方案声称已实施的模块/函数有没有护栏引用它？**」本仓历史 `profile_refine`「源码未落库却被正文当作已交付」（`DEF-BE-148-029`）正是「**无实现 ＋ 无护栏**」叠加的后果 ⇒ 该问题属**真实风险**而非形式检查。**工具**：新增 `doc/test/evidence/cr149/check_guard_coverage.py`（＋ `-result.json`）—— 抽取正文**代码符号**（`def`/`class`；**口径不含配置键**，因配置键多由 `load_budget_policy` 一类**行为级**护栏覆盖），判其在 `tests/` 与证据目录中**有无按名引用**。**结论**：91 个「声称已实施且仓内确有定义」的符号中 **74 有按名引用 / 17 无按名引用**；**逐项人工判定后 0 真实缺口** —— 17 项**全部属行为级覆盖**（`apply_context_budget`/`_fit_single_unit`/`_format_list`/`_is_adjacent_synonym`/`_merge_adjacent_synonyms`/`_parse_timestamp`/`_rank_score`/`is_redundant_pair`/`resolve_system_prompt` 经公开入口覆盖；`grade_rag_ingest` 由 `test_writeback_decision_gate` 断言 `rag_grade` **三态**；`_build_history_for_request`/`_history_budget_tokens` 经 `test_session_axis_*` 与 `test_context_budget*` 覆盖、其委托对象 `history.build_history_ctx` 另有「丢最旧保最近」专项；`_cache_get`/`_cache_put` 经缓存命中/淘汰用例；`_writeback_channel_primary` 经回写回调级四态用例；`VectorStoreService`/`_sql_where` 属**本方案面之外**）。② **CR-149 面日志合规审计（0 违规）**：按 `AGENTS.md` §3「禁止记录 密码/令牌/密钥/**完整请求体**/个人隐私」，新增 `doc/test/evidence/cr149/cr149_log_hygiene.py`（＋ `-result.json`），对 **15 个 CR-149 面文件**的 **53 处 `logger.*` 调用**做**括号配对**扫描（并按长度/计数/标识等**安全衍生量**标记辅助判定）。**结论**：**1 处命中且为误报**（`app/api/writeback.py:232` 的「updates」出现在**消息文案**里，落日志实参只有 `user_id`）⇒ **0 违规**——即 **CR-149 各批新增观测（回写三路/通道护栏/预算裁剪/画像维度/路由缓存/精炼触发）未以正文或凭据为代价**。③ **方案 §9.1「裁定清单与解锁关系」（新增）**：实施侧已按「不受阻者先行」推进到位（第一批 6/6、第二批 ①~⑤ 与 ⑦ 闭环、§4.3/§5.2/§5.3/§5.8 余项闭环、判据 T1~T12 交付），**剩余未实施项全部落在 7 项裁定或两类外部条件上**；§9.1 逐项给出「我方已备好 / 裁定后**解锁**哪些实施项 / 裁定后我方动作」（Q1 通道 A 三选一、Q2 精炼推理位置、Q3 预算目标、Q4 记忆写入语义、Q5 切换触发权、Q6 异步精炼产物归属、Q7 画像提炼器形态），并单列**非裁定型前置**（**达标模型＋GPU**：≤1B 事实保留 0.17~0.67 < 0.90、筛选 F1 最好 0.697 < 0.70 ⇒ 当前无可用达标候选；**运行态 DB＋嵌入模型**：`has_base=false`），明确 **§7.1 批准包**与 **§9.1 裁定**是**两条互相独立的人工门禁**（前者决定 T1/T2/T3/T5/T8 由 `SKIP` 转 `PASS`，**不依赖任何裁定**）。④ **边界说明（如实登记）**：两工具均为**静态**审计 —— 前者不判**覆盖质量**、后者不判**是否为整值** ⇒ **不替代**行为级判据与人工复核。⑤ **回归与静态质量**：**本批无 OpenLLM 生产代码改动** ⇒ **线上行为零变化**；两个新工具 `ruff` **All checks passed**；执行器两态与上批**一致**（当前配置 `{PASS:5, SKIP:5, BLOCKED:2, FAIL:0}`；`--simulate` `{PASS:10, SKIP:0, BLOCKED:2, FAIL:0}`）；全量回归**未复跑**（如实登记）。⑥ **过程修正（如实登记）**：编辑方案文件时误用 `Set-Content -Encoding UTF8`（PS5 会写入 **BOM**）⇒ 已检出并以 `UTF8Encoding($false)` **去除 BOM**（v1.18.3 与归档 v1.18.2 首字节均已校验为 `23 20`）。⑦ **提交**：仅 **OpenBase** 侧（新增两个审计工具 ＋ 两份结果 JSON ＋ 方案 v1.18.3 ＋ 本文档），**无 OpenLLM 代码提交**。文档版本 **v1.55.0 → v1.56.0**；状态 [Review] |
| **v1.57.0** | **2026-09-27** | **AA-OpenBase-Dev / AT-OpenBase-Test** | **§7.1 开关开启值人工批准落地 ＋ §9 问题 1 裁定「接线」并落地第一段（§4Y 新建）**。① **§7.1 批准落地**：人工批准「建议本次开启」**6 类开关（7 键）**，写入**工作区环境配置** `OpenLLM/backend/.env`（**非仓库文件**，注释块内仅开关键、**不落任何密钥**）：`CONTEXT_BUDGET_ENABLED` / `CONTEXT_SYSTEM_PROMPT_ENABLED` / `RAG_RERANK_ENABLED` ＋ `RAG_SCORE_THRESHOLD=0.15` / `COMPONENT_DEPENDENCY_SCHEDULING_ENABLED` / `WRITEBACK_DECISION_ENABLED` / `CONTEXT_REFINE_TRIGGER_ENABLED`；**未批准项维持**（引用编号 / 窗口与输出预留 / LLM 兜底分类器 / `CHANNEL_*` 主备声明值）；`CONTEXT_SYSTEM_PROMPT` 仍空 ⇒ 按设计**回退内置 `DEFAULT_SYSTEM_PROMPT`**。**复跑取证**：执行器**当前配置** ⇒ **`{PASS:10（T1/T2/T3/T5/T7/T8/T9/T10/T11/T12）, SKIP:0, BLOCKED:2（T4/T6）, FAIL:0}`** —— **T1/T2/T3/T5/T8 由 `SKIP` 转 `PASS`**，与 `--simulate` 预测**一致**。② **批准后暴露的真实缺陷（已修）**：`_builtin_rag_search()` 的分数阈值过滤对**缺失 `score`** 的条目取 `0.0` ⇒ 开启阈值后这类条目被**静默丢弃** ⇒ **备通道（内置 RAG）可能「接管成功、注入为空」**（方案 §4.1 警示形态）；**依据**：`rag_service.py` 多处 `.get("score", 0.0)` 容缺 ⇒ 内置结果**确实可能不含 score**。**订正**：**有 `score` 者按阈值过滤、无 `score` 者保留**（**据实过滤，不据缺判低**）；护栏 `test_auto_kb_resolution.py::test_threshold_filters_scored_but_keeps_unscored`。③ **批准后暴露的 9 项用例「环境假设」（已订正，未放宽任何断言）**：3 项改断言 `Settings.model_fields[...].default`（**出厂默认**，部署无关）＋ 2 项显式置关预算（「未传 policy」不再等于「不裁剪」）＋ 3 项显式置关价值闸门（只测 kb_id 绑定 / submit 回传 / 正常入队）＋ 1 项由 ② 自然通过。④ **§9 问题 1 裁定「接线」并落地第一段**：**(a) 接线前提（核心修复）** —— `ChannelStateManager` 原由 `_get_channel_manager()` **每次按当前配置构造** ⇒ ① 组件级失败**无法累计到阈值**、② 显式切到 A 后**下一请求即被重置回声明值**（**切换形同虚设**）；与本仓 `DT-148-015`（每请求新建 `ModelRouter` ⇒ **熔断永不打开**）**同类**；**处置**＝新增 `channel.get_channel_state_manager()`（**进程级单例** ＋ **偏好热更新** ＋ `reset_channel_state_manager()` 供隔离），并**区分两种偏好语义**（**变化 ⇒ 回落声明值**；**未变 ⇒ 保留运行期切换**；**非法 ⇒ WARN ＋ 保留现状 fail-open**）。**(b) 触发责任链双源接线** —— 源 1＝`_note_component_channel_health(component_run)` 挂**两路径共用**组件步骤之后（`degraded` 逐组件计失败；**`rag_source=builtin` 亦计失败**；全正常 ⇒ 清零）；源 2＝`_note_model_outcome()` 一并登记 `record_upstream_probe`（本仓无独立 llm-proxy 端点 ⇒ 以**出站模型调用实际成败**为探活事实）；**只登记不改通道**（自动回落由 `CHANNEL_AUTO_FAILOVER_ENABLED` 默认 False 门控 ⇒ **不代行 §9 问题 5**）。**(c) 通道定性可观测** —— `/health` 增 **`channel` 段落**（偏好 / 主通道 / 单主路径 / `healthy_b` / 演练窗口 / 自动开关；异常降级 `unavailable`）＋ **`components.*.channel`**（外部三组件 `b`、内置 RAG 与 Ollama `a`）⇒ 与 `builtin_rag.has_base` 合起来，「走主还是备」与「接管后是否有内容」**同一事实源可判**（即方案 §4.1「人工验证口径」中等待本裁定的那一项）。**(d) T11 条款确定性订正** —— 单例保留运行期切换后，「配置非法 ⇒ 放行」若仅由状态断言兜底会**取决于既有状态**（执行器 T11 一度 `FAIL`）⇒ 改为**配置层前置判定**：非法即 WARN ＋ **恒放行**，使「**配置笔误不得静默停库**」得确定性保证（T11 复归 `PASS`）。⑤ **验证与证据**：新增 `tests/unit/test_channel_wiring_health.py` **12 例** ＋ 备通道阈值 3 态 ＋ 预算开关正例 1 例；`test_writeback_channel_guard.py` 增 autouse 单例隔离 fixture（**仅隔离，不改断言**）；**全量回归**：开关开启后首轮 `cr149-t21` **30 failed / 3225 passed**（+9 ＝ 环境假设），**订正后** `cr149-t22` **21 failed / 3248 passed / 0 error**，与开关开启前基线 `cr149-t20` **逐项 testid 归一化 `Compare-Object` 差异 0 项 ⇒ 零回归**；本批 13 文件 `ruff` **All checks passed**。⑥ **开销实测与归因（如实登记）**：新增探针 `assembly_cost_probe.py` 测得**单次装配 20.8 → 44.2 ms（2.12×，复测 2.066）**；**受控 A/B**（装配密集子集 ON 11.39 s vs OFF 11.59 s）⇒ **开关不拖慢该子集**；全量墙钟 1859 s **不归因于开关**（同套件历史 256~889 s，主机负载波动）⇒ 仅「单次装配 2.12×」为可归因事实并列为方案 §8 风险行；新增方案 **§10 待登记项 14**（墙钟可归因性，**条件立项**，建议再现时 `--durations=20`）。⑦ **残留（如实登记，不臆造）**：**通道裁决接入取数层（逐组件路由）**需 A 侧对 `memory` / `dps` 具备等价能力（当前仅 `rag` 有内置回退）⇒ 取决于「内置 RAG 种子底座」（运行态 DB ＋ 嵌入模型）与 §9 问题 4；**「写路径 A/B 等价」矩阵项**当前口径＝「**A 接管期间写暂停**」（T11）。⑧ **语义与影响面**：**生产配置首次真正启用本方案能力**（预算裁剪 / system 段 / 检索侧重排与阈值 / 依赖图调度 / 写侧价值闸门 / 精炼触发观测）⇒ **线上行为按批准范围变化**；通道侧**只登记不改通道** ⇒ 切换仍为**人工显式为主**。⑨ **提交**：OpenLLM `4789c6c`（`feat(v149)`，13 文件 `+537/-13`）。文档版本 **v1.56.0 → v1.57.0**；状态 [Review] |
| **v1.58.0** | **2026-09-27** | **AA-OpenBase-Dev / AT-OpenBase-Test** | **§9 问题 3（预算目标）裁定「按真实窗口」并落地：统一窗口解析入口 ＋ 两路径传模型 ＋ 装配/历史段同源（§4Z 新建）**。① **裁定**：人工批准采纳「**按本次对话模型的有效窗口**」＝ `min(模型声明窗口, 部署生效窗口)`；**不用**知识库样本宣称的 **4096**（过窄、浪费模型容量），**也不用**模型表 `default`＝**128000** —— **架构上限 ≠ 服务侧可用量**（本地部署实际可用上下文由服务侧决定；按架构上限配额会在服务侧被**截断** ⇒ **静默丢内容**，正是方案 §4.1/§8 反复警示的形态）；未识别模型 ⇒ **保守兜底＝部署窗口**（`CONTEXT_MODEL_WINDOW_TOKENS`，当前 8192）。**绝对配额表**已落方案 §3.3：8192 ⇒ system 358 / profile 358 / memory **2007** / rag **2652** / history **1361**；4096 ⇒ 153/153/860/1136/583；32768 ⇒ 1587/1587/8888/11745/6031（`output_reserve=1024`、比率和 0.94）。② **本批新发现的真实缺陷（同源口径分叉）**：装配预算 `prompt_pipeline.load_budget_policy` 与历史段预算 `openllm_gateway._history_budget_tokens` **各自解析窗口且兜底不同** —— 装配恒用配置 **8192**、历史段对未识别模型取 **128000** ⇒ **同一请求两套窗口（相差 15.6 倍）**；实测部署模型 `qwen3:0.6b` 在模型表**零命中** ⇒ 历史段预算 **(128000−1024)×0.2 ＝ 25,395**，对本地小模型属**超窗配置**。③ **同批新发现的「声明未接线」**：`build_prompt` 支持 `model=`（用于按真实窗口解析），但**两条路径的组装都未传** ⇒ 「模型可识别时优先取真实窗口」在**生产路径永不生效**（与第 48 批「无护栏/未接线」同类）。④ **处置**：新增统一入口 `context_manager.resolve_effective_window_tokens(model)`（可识别 ⇒ `min(声明, 部署)`，来源 `registry:<key>` / `deployment_cap:<key>`；未识别 ⇒ `deployment_fallback` 部署窗口，**明确不取** 128000；解析异常 ⇒ `config_fallback` fail-open）＋ `load_budget_policy` 与 `_history_budget_tokens` **同源调用** ＋ `PipelineExecutor`（同步/共用组装步骤）与**流式端点同源传入** pipeline 的 llm 条目 `params.model`。⑤ **验证与证据**：新增探针 `budget_window_probe.py`（＋ `-result.json`）实测三档配额与来源标；新增 `tests/unit/test_budget_window_basis.py` **11 例**（三口径含「未识别**断言 ≠ 128000**」/ 显式部署窗口参与取小 / 装配与历史段**同源** / `build_prompt(model=...)` 配额随窗口变化 / **两路径同源传参**的源码级断言）；**全量回归** `cr149-t23` **21 failed / 3259 passed / 0 error**（281.62 s；较上批 +11 ＝ 本批护栏），与 `cr149-t22` **逐项 testid 归一化 `Compare-Object` 差异 0 项 ⇒ 零回归**；执行器两态 **`{PASS:10, SKIP:0, BLOCKED:2, FAIL:0}`**（不变）；5 文件 `ruff` 与基线（`git stash` 对照）**逐规则计数一致（70 → 70）⇒ 未引入新增 lint**。⑥ **旁证（墙钟归因，接 v1.57.0 开放项）**：同套件墙钟由 **1859 s** 回到 **281.62 s** ⇒ 进一步佐证上批异常属**主机负载**，非开关所致。⑦ **语义与影响面**：本工作区**配额不变**（`qwen3:0.6b` ⇒ 8192 兜底）；**历史段预算 25,395 → 1,433**（与装配同窗口）；声明窗口更小的模型将按其真实窗口配额 ⇒ 「按真实窗口」在生产路径**真正生效**。⑧ **残留（如实登记，不臆造）**：**模型窗口两张表未对齐** —— `app/core/supported_models.py` 声明 `qwen3:*` `context_window=131072`，而 `MODEL_CONTEXT_LIMITS` **无 qwen3 族键**；因本轮取 `min(声明, 部署)`，**补表与不补表结果相同** ⇒ **不影响裁定**，但补表会改变共享表对外口径（`get_model_context_limit("qwen3:*")` 128000 → 131072）⇒ 列方案 **§10 待登记项 14**（**建议立项**）。⑨ **提交**：OpenLLM `a825c2c`（`feat(v149)`，5 文件 `+226/-21`）。文档版本 **v1.57.0 → v1.58.0**；状态 [Review] |
| **v1.59.0** | **2026-09-27** | **AA-OpenBase-Dev** | **§9 问题 4（记忆写入语义）裁定「默认 `verbatim`（整轮全文）＋ 摘要路径可选/可配置/可回退且当前不启用」并落地：载荷形态模块 ＋ 三配置键 ＋ 网关按路接线 ＋ 12 例护栏 ＋ 探针自检（§4AA 新建）**。① **裁定**：理由三条 —— **(a) 记忆粒度变化不可逆**（摘要入库后**检索召回粒度**与**归因 A** 片段索引随之改变，历史轮次无法还原）；**(b) 生成式精炼模型档未过 §5.6 门槛**（≤1B 事实保留 **0.17~0.67 < 0.90**）⇒ 无达标模型时改写载荷＝**引入不可回收的失真**；**(c) 与既有原则同向** —— 价值闸门只决定「**是否沉淀**」、**不改写载荷**。② **落点**：新增 `app/edgerouter/orchestration/memory_payload.py`（纯函数 ＋ **进程级提炼器注入**，**当前未接线**）；三键 `WRITEBACK_MEMORY_PAYLOAD_MODE`（默认 `verbatim`）/ `WRITEBACK_SUMMARY_MIN_CHARS`（默认 **40**）/ `WRITEBACK_SUMMARY_KEEP_ORIGINAL`（默认 **True**）；网关 `_make` **仅在 `target == "memory"`** 装配载荷。③ **五条护栏**（任一不满足即回退）：**未注入提炼器 / 提炼器异常 / 摘要为空 / 摘要过短 / 摘要未短于原文（无压缩收益）**；**非法配置 ⇒ 回退 ＋ WARN**（fail-safe）。④ **默认零改动**：`verbatim` 下返回字段与既有 kwargs **同值**、**不新增任何 payload 键**（`payload_meta` 仅摘要**真正生效**时附上）⇒ **线上路径逐字不变**。⑤ **护栏**：`tests/unit/test_memory_payload_mode.py` **12 例全绿**（声明式默认断言 / 五条护栏逐条 / 两类保留策略 / 回调级零改动）。⑥ **探针与「取证自检」缺陷（自查并修复，重要）**：新增 `memory_payload_probe.py`（＋ `-result.json`）9 例判定表；**首轮即暴露取证缺陷** —— ⑦/⑧ 名为「summary 生效」却实测 `applied=false`（样例摘要 **27 字** < 门槛 **40** ⇒ 回退）⇒ 加 `expect_applied`/`ok` 与**结尾自检**（`40 ≤ n < 200` ＋ 逐例期望一致，不符即 `FAIL`、**返回码非 0**）⇒ 修后 **9/9 一致**。⑦ **回归与受控实验**：全量 `cr149-t24` **22 failed / 3270 passed / 0 error**（**2368.83 s**；+11 passed ＝ 12 例护栏 − 1 例 flaky）；与 `cr149-t23` 逐项 testid 归一化 `Compare-Object`：**新增失败 1 项**＝`test_perf_batch_concurrency.py::test_pacer_does_not_serialize_requests`、**已消失 0 项**。**受控实验（决定性）**：该例断言**墙钟**（`wall < 0.2 s`）；`git stash` 前后**两态均通过**（`5 passed / 1.07 s` vs `5 passed / 1.04 s`）；失败时同文件 **124.29 s**（`wall = 0.2919 s`）vs 空闲 **≈1.05 s**（**约 118×**）⇒ **并行/主机争用**；本批改动**不含** `pacer`/并发路径 ⇒ **环境 flaky，零回归**。⑧ **静态质量**：本批 4 文件 `ruff` **All checks passed**（0 告警）。⑨ **同批文档一致性缺陷（已修）**：OpenLLM 开发记录报告**文档头版本滞留 `v1.32.1`** 而修订历史已至 `v1.39.0`（**7 版漂移**）⇒ 已同步 **v1.40.0**；登记方案 §10 **待登记项 16**。⑩ **工作区遗留（如实登记，未代行）**：`backend/tests/unit/test_billing_v2_api.py` 存**非本批**未提交改动（`DT-213-003`）⇒ **不属本方案面，本批未提交**。⑪ **提交**：OpenLLM **`dcda043`**（`feat(v149)`，4 文件 `+386/-1`）；**另补交** `test_context_rank_selection.py`（v1.18.0 判据同源订正**此前仅改盘未入库**）**`3a034aa`**（12 例全绿）。文档版本 **v1.58.0 → v1.59.0**；状态 [Review] |

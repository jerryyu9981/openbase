# 批次 3 任务清单（R7 / R9 / R2）

| 项 | 内容 |
|---|---|
| **版本** | v1.0.0 |
| **状态** | [Review] |
| **对应规格** | `doc/design/批次3-全链路贯通修复/spec.md` v1.0.0 |
| **作者** | 架构组 |
| **日期** | 2026-11-12 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-12 | 首版：R7(T1-T4) / R9(T5-T9) / R2(T10-T16) 任务、验证命令与门禁 | 架构组 |
| v1.1.0 | 2026-11-12 | 勾选 T1–T16 完成项，追加实施记录与验证结果（含 2 处偏差） | 架构组 |

## 任务总览

| ID | 编号 | 任务 | 仓 | 依赖 | 优先级 |
|---|---|---|---|---|---|
| T1 | R7 | `history.py` 四策略裁剪 + 单测 | OpenLLM | - | 高 |
| T2 | R7 | 网关 `context_policy` 校验、meta 组装、同步/流式回显 | OpenLLM | T1 | 高 |
| T3 | R7 | 门户 `llm-proxy` 校验与 `context_meta` 补齐 + 单测 | OpenBase | T2 | 高 |
| T4 | R7 | 定向验证 + 方案文档留痕 | OpenBase | T1-T3 | 中 |
| T5 | R9 | DPS DDL/迁移：`external_id` 列 + 唯一索引 | DPS | T4 | 高 |
| T6 | R9 | DPS 写路径落列 + 冲突 409 + by-external 端点 | DPS | T5 | 高 |
| T7 | R9 | DPS 单测 | DPS | T6 | 高 |
| T8 | R9 | 门户 `dps-proxy` by-external 代理 + 单测 | OpenBase | T6 | 高 |
| T9 | R9 | OpenLLM 画像回写携带 `external_id` + 单测 | OpenLLM | T6 | 中 |
| T10 | R2 | OpenLLM 配置 + `KbIdMap` 模型 + 建表接线 | OpenLLM | T9 | 高 |
| T11 | R2 | `OpenRAGClient` 补齐 collection/document 方法 | OpenLLM | T10 | 高 |
| T12 | R2 | `kb_openrag_bridge.py` 代理服务层 | OpenLLM | T11 | 高 |
| T13 | R2 | 知识库/文档路由代理分支 + 只读 410 | OpenLLM | T12 | 高 |
| T14 | R2 | 迁移脚本（幂等 + dry-run + 对账） | OpenLLM | T12 | 高 |
| T15 | R2 | 单测：代理模式 / 映射表 / 只读 | OpenLLM | T13,T14 | 高 |
| T16 | 收口 | 三仓定向验证、方案升 v1.6.0、提交推送 | 全部 | T1-T15 | 高 |

---

## T1 R7：四策略裁剪 [x]

**文件**：`OpenLLM/backend/app/edgerouter/orchestration/history.py`

**步骤**
1. 先写 `backend/tests/unit/test_context_policy.py`（RED）：构造 8 条历史，分别断言 `recent/head_tail/system_priority/summarize_old` 的输出行数与内容包含关系。
2. `build_history_ctx` 增加 `strategy: str = "recent"`；抽出 `_trim_recent`；新增 `_trim_head_tail`、`_trim_system_priority`、`_summarize_old`。
3. 未知 strategy 回落 `recent`。

**验证**：`D:\venvs\openllm\Scripts\python.exe -m pytest backend/tests/unit/test_context_policy.py -q`

---

## T2 R7：网关接线 [x]

**文件**：`OpenLLM/backend/app/api/openllm_gateway.py`

**步骤**
1. `OpenLLMChatRequest` 新增 `context_policy`；新增 `CONTEXT_POLICY_STRATEGIES` 与 `_resolve_context_policy`（非法 → `GatewayError(4003, ...)`，`max_tokens` 上限 200000）。
2. `_build_history_for_request` 返回 `(text, meta)`；`_normalize_request` 返回 6 元组；更新 3783/4092 两处解包。
3. 同步 `data` 加 `context_meta`（`raw_results` 模式同样）；流式 routing 事件 data 加 `context_meta`。
4. 单测补充：非法参数 4003；不传策略时输出与旧逻辑一致。

**验证**：`pytest backend/tests/unit/test_context_policy.py backend/tests/unit/test_openllm_gateway*.py -q`

---

## T3 R7：门户代理 [x]

**文件**：`OpenBase/openbase/modules/llm_proxy/__init__.py`，新增 `OpenBase/tests/test_llm_proxy_context_policy.py`

**步骤**
1. 新增 `_validate_context_policy`（非 dict/非法 strategy/max_tokens/preserve_recent_n → `BaseError(ErrorCode.PARAM_INVALID)`）。
2. `llm_chat`、`llm_chat_stream` 转发前校验。
3. 新增 `_with_context_meta`：2xx `data` 缺 `context_meta` 时补 `{strategy, applied: false, source: "openbase-default"}`。
4. 单测：非法 400、透传、补默认值。

**验证**：`D:\venvs\openbase\Scripts\python.exe -m pytest tests/test_llm_proxy_context_policy.py -q`

---

## T4 R7：收口 [x]

1. `ruff check openbase tests` 0 错误；OpenBase 全量 `pytest tests`。
2. OpenLLM 相关单测全通过。
3. 方案文档升 **v1.6.0**，修订历史追加 R7 实施记录（含偏差：前端设置页展示延后至批次 4）。
4. 提交：OpenBase、OpenLLM 各一次，只 add 本任务明确文件（OpenLLM 已有大量无关未提交改动，禁止 `git add -A`）。

---

## T5 R9：DPS DDL 与幂等迁移 [x]

**文件**：`DPS/src/ddl/schema_root.py`、`DPS/src/database.py`

**步骤**
1. `PROFILE_PG` / `PROFILE_SQLITE` 增加 `external_id`。
2. `database.py` 新增 `_ensure_profile_external_id()`：PG `ADD COLUMN IF NOT EXISTS` + 部分唯一索引；SQLite PRAGMA 探测后 ALTER + 部分唯一索引。
3. 在启动初始化与既有 profile 索引复核函数处调用。

**验证**：`python -m py_compile src/database.py`；启动 DPS（或执行初始化函数）后确认列与索引存在。

---

## T6 R9：DPS 写路径与查询端点 [x]

**文件**：`DPS/src/identity/error_codes.py`、`DPS/src/rest_api/routes/routes_profiles.py`

**步骤**
1. 错误码新增 `BIZ_EXTERNAL_ID_CONFLICT` + 消息映射。
2. `_TOP_LEVEL_WHITELIST` 加 `external_id`；新增 `_validate_external_id`（str、1-200 字符，非法 400）。
3. `_parse_portrait_update_body` 返回 3 元组；更新 PUT/PATCH 调用点。
4. `_persist_portrait_update` 增加 `external_id` 参数并落列；唯一冲突 → `BaseError(BIZ_EXTERNAL_ID_CONFLICT)`。
5. 新增 `GET /portrait/by-external/{external_id}`，**注册在 `/portrait/{person_id}` 之前**；返回与 GET portrait 同构；未命中 404。

**验证**：`pytest src/tests/test_batch3_r9_external_id.py -o addopts="" -q`

---

## T7 R9：DPS 单测 [x]

**文件**：新增 `DPS/src/tests/test_batch3_r9_external_id.py`

覆盖：写入落列、同 org 唯一冲突 409、by-external 200/404、租户隔离、不传时行为不变。

---

## T8 R9：门户代理 [x]

**文件**：`OpenBase/openbase/modules/dps_proxy/__init__.py`，新增 `OpenBase/tests/test_dps_proxy_external_id.py`

**步骤**：新增 `GET /portraits/by-external/{external_id}`（注册在 `/portraits/{person_id}` 之前），复用 `_forward`；单测断言上游路径、身份头、404 透传。

---

## T9 R9：OpenLLM 回写携带 external_id [x]

**文件**：`OpenLLM/backend/app/edgerouter/adapters/profile.py`

**步骤**：写回 payload 增加 `external_id`（`subject_id` → `external_user_id` → 不携带）；扩展现有 profile 写回单测断言。

---

## T10 R2：配置与映射模型 [x]

**文件**：`OpenLLM/backend/app/settings.py`、新增 `backend/app/models/kb_id_map.py`、`backend/app/db/session.py`

**步骤**：新增 `OPENLLM_KB_PROXY_ENABLED` / `OPENLLM_KB_READONLY` / `OPENLLM_KB_TIMEOUT`；`KbIdMap` 模型（`legacy_kb_id` 唯一）；`create_all` 前导入。

---

## T11 R2：OpenRAG 客户端 [x]

**文件**：`OpenLLM/backend/app/edgerouter/adapters/openrag_client.py`

**步骤**：新增 `create_collection`、`get_collection`、`update_collection`、`delete_collection`、`get_collection_stats`、`list_documents`、`delete_document`，复用 `_request`/`_raise_business_error`，统一 `ComponentUnavailableError`。

---

## T12 R2：代理服务层 [x]

**文件**：新增 `OpenLLM/backend/app/services/kb_openrag_bridge.py`

**步骤**：实现 `resolve_collection`（映射 → 按名查 → 建库 → 写映射）、集合 CRUD、统计、文档列表/文本入库/删除；`(tenant_code, name)` 首次访问建库；进程级 `AsyncClient`。

---

## T13 R2：路由接线 [x]

**文件**：`OpenLLM/backend/app/api/knowledge_bases.py`、`OpenLLM/backend/app/api/documents.py`

**步骤**
1. 每个端点：`OPENLLM_KB_PROXY_ENABLED` → 代理分支（响应头 `Deprecation: true`、`Sunset: ...`）；否则本地实现。
2. 写端点：代理关闭且 `OPENLLM_KB_READONLY` → 410 `BIZ_KB_MIGRATED`。
3. 代理模式响应改用 `KnowledgeBaseProxyResponse(id: str)`（若 OpenRAG id 非 UUID）。

---

## T14 R2：迁移脚本 [x]

**文件**：新增 `OpenLLM/backend/scripts/migrate_kb_to_openrag.py`

**步骤**：遍历本地 KB/Document → 建/查 collection → `content_hash` 去重后 `/documents/text` 重放 → 轮询状态（≤120s）→ 写 `kb_id_map` → 输出对账 JSON；支持 `--dry-run`；文档数不一致退出码 2；幂等重跑。

---

## T15 R2：单测 [x]

**文件**：新增 `OpenLLM/backend/tests/unit/test_kb_proxy_mode.py`、`test_kb_id_map.py`

覆盖：开关关闭走本地（回归）、开启走 fake bridge、上游不可用 503、只读 410、Deprecation 头、映射幂等。

---

## T16 收口与留痕 [x]

1. 验证命令（全部）：
   - OpenBase：`ruff check openbase tests`、`pytest tests`
   - DPS：`pytest src/tests/test_batch3_r9_external_id.py -o addopts=""`
   - OpenLLM：`pytest backend/tests/unit/test_context_policy.py backend/tests/unit/test_kb_proxy_mode.py backend/tests/unit/test_kb_id_map.py`
   - 迁移脚本 `py_compile`
   - OpenRAG：`py_compile` 两个路由文件（本仓零改动）
2. 已知噪声：OpenBase `tests/test_settings.py::test_dps_upstream_defaults_aligned_to_source_port` 全量串跑偶发失败（单跑通过，与本批次无关），在实施记录中注明。
3. 方案文档 `doc/design/OpenBase-四基础子系统全链路贯通修复方案-v1.0.0.md` 升 **v1.6.0**：R2/R7/R9 段落加实施标记（含偏差与开关默认值）。
4. 提交推送：
   - OpenBase：`doc/design/批次3-全链路贯通修复/spec.md`、`tasks.md`、方案文档、`openbase/modules/llm_proxy/__init__.py`、`openbase/modules/dps_proxy/__init__.py`、2 个新测试 → 推送 origin/backup/github；
   - DPS：3 个改动文件 + 1 个新测试 → 推送 main；
   - OpenLLM：本批次明确文件 + 新测试/脚本 → 推送当前分支（不 add 无关改动）。

---

## 实施记录（v1.1.0，2026-11-12）

### 验证结果

| 范围 | 命令 | 结果 |
|---|---|---|
| OpenBase 静态检查 | `D:\venvs\openbase\Scripts\ruff.exe check openbase tests` | All checks passed |
| OpenBase R7 单测 | `pytest tests/test_llm_proxy_context_policy.py` | 6 passed |
| OpenBase R9 单测 | `pytest tests/test_dps_proxy.py` | 40 passed（含新增 2 条） |
| DPS R9 单测 | `pytest src/tests/test_batch3_r9_external_id.py -o addopts=""` | 8 passed |
| DPS R1 回归 | `pytest src/tests/test_batch2_r1_patch_merge.py -o addopts=""` | 7 passed |
| OpenLLM R7/R9/R2 单测 | `pytest tests/unit/test_context_policy.py test_batch3_r9_writeback_external_id.py test_kb_proxy_mode.py test_kb_id_map.py` | 23 passed |
| OpenLLM 既有 KB/Document/OpenRAG 回归 | `test_knowledge_bases_api.py`、`test_documents_api.py`、`test_openrag_client.py` | 29 passed |
| OpenLLM 网关回归 | `test_openllm_gateway.py`、`test_session_axis_gateway.py`、`test_v213_gateway_ext.py` | 全通过 |
| 编译检查 | `py_compile`（OpenLLM/DPS 本批次文件） | 通过 |

### 偏差与实现说明

1. **R9 允许仅 external_id 更新**：`_parse_portrait_update_body` 的"至少一项"判定纳入 `external_id`，便于单独登记映射；其余校验不变。
2. **R2 documents 无 `/text` 端点**：OpenLLM 既有上传端点按 UTF-8 文本提取后调用 OpenRAG `documents/text`；非文本上传返回 422（原能力不变）。
3. **R2 代理响应结构**：代理分支直接返回旧字段 `dict`（`id: str`），不新增 Pydantic 响应模型；非代理分支类型不变。
4. **R2 配置位置**：实际配置定义在 `backend/app/core/config.py`（非 `app/settings.py`）；建表接入点为 `backend/app/db/session.py::init_db`。
5. **R2 迁移脚本位置**：`backend/scripts/migrate_kb_to_openrag.py`。
6. **R9 测试位置**：门户用例追加在既有 `tests/test_dps_proxy.py`（复用其 fake 上游夹具），未新建独立文件。
7. **R7 前端展示**：按规格 §1 约定延后至批次 4（避免与用户未提交的 Playground/llm.ts 冲突），本批次仅提供 API 能力与回显。

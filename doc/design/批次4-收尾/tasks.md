# 批次 4 任务清单（收尾）

| 项 | 内容 |
|---|---|
| **版本** | v1.3.0 |
| **状态** | [Review] |
| **对应规格** | `doc/design/批次4-收尾/spec.md` v1.3.0 |
| **作者** | 架构组 |
| **日期** | 2026-11-12 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-12 | 首版：T1–T9 任务、验证命令与门禁 | 架构组 |
| v1.1.0 | 2026-11-12 | 勾选 T1–T9，追加实施记录与验证结果（7 项偏差见规格 §9） | 架构组 |
| v1.2.0 | 2026-11-12 | 全栈启动后补跑八项联调：PASS=7、PARTIAL=1、FAIL=0；脚本适配受信来源头/租户 B 主体/既有画像（规格 §9.2 第 9 条） | 架构组 |
| v1.3.0 | 2026-11-21 | 用户裁定：T6 两文件（`llm.ts`、`Playground.vue`）作为 R7 前端闭环单独提交入库，不再保留在工作区 | 架构组 |

## 任务总览

| ID | 范围 | 任务 | 仓 | 依赖 | 优先级 |
|---|---|---|---|---|---|
| T1 | R2 | `OpenRAGClient.reindex_document` + 桥接方法 | OpenLLM | - | 高 |
| T2 | R2 | `documents.py` 补 `get_document` / `reprocess` 代理分支 | OpenLLM | T1 | 高 |
| T3 | R2 | OpenLLM 单测：代理分支 / 503 / 本地回归 | OpenLLM | T2 | 高 |
| T4 | R7 | 新增 `core/contextPolicy.ts` + 单测 | OpenBase | - | 高 |
| T5 | R7 | 新增 `InferenceSettings.vue` + 路由/菜单 | OpenBase | T4 | 高 |
| T6 | R7 | Playground/llm.ts 追加透传与回显（按 2026-11-21 裁定单独提交） | OpenBase | T4,T5 | 高 |
| T7 | 联调 | 八项清单契约级核对 + `verify_full_chain_checklist.py` + 执行记录 | OpenBase | T2,T5 | 高 |
| T8 | 收口 | 全量验证、spec/tasks 升 v1.1.0、方案升 v1.7.0 | OpenBase | T1-T7 | 高 |
| T9 | 收口 | 各仓提交推送（OpenBase 三远程；两文件按 2026-11-21 裁定单独提交） | 全部 | T8 | 高 |

---

## T1 R2：OpenRAG reindex 客户端与桥接 [x]

**文件**：`OpenLLM/backend/app/edgerouter/adapters/openrag_client.py`、`OpenLLM/backend/app/services/kb_openrag_bridge.py`

**步骤**
1. `OpenRAGClient.reindex_document(collection_id, document_id, headers=None)` → `POST /api/v1/collections/{cid}/documents/{did}/reindex`，解析信封 `data`。
2. `KbOpenRAGBridge.reindex_document(tenant_code, collection_id, document_id)` 透传身份头。

**验证**：`py_compile` 两文件；T3 单测覆盖调用路径。

---

## T2 R2：路由代理分支 [x]

**文件**：`OpenLLM/backend/app/api/documents.py`

**步骤**
1. `get_document` → `async def`；代理分支：解析租户/集合 → `bridge.get_document` → `document_to_legacy` + `DEPRECATION_HEADERS`；上游不可用 503。
2. `reprocess_document` → `async def`；代理分支置于 `ensure_local_writable()` 之前，调用 `bridge.reindex_document`，返回旧字段 + 废弃头。
3. 本地分支保持不变（只读开关仍返回 410）。

---

## T3 R2：单测 [x]

**文件**：新增 `OpenLLM/backend/tests/unit/test_kb_documents_proxy_gaps.py`

覆盖：代理开启 `GET /documents/{id}` 命中 fake bridge；`POST .../reprocess` 调用 reindex；上游异常 503；代理关闭回归。

**验证**：`D:\venvs\openllm\Scripts\python.exe -m pytest backend/tests/unit/test_kb_documents_proxy_gaps.py backend/tests/unit/test_kb_proxy_mode.py -q`

---

## T4 R7：contextPolicy 模块与单测 [x]

**文件**：新增 `openbase-ui/src/core/contextPolicy.ts`、`openbase-ui/tests/r7-context-policy.spec.ts`

**步骤**
1. 导出类型、白名单标签、`normalizeContextPolicy/load/save/extractContextMeta`。
2. 单测覆盖合法/非法/边界/存储/事件提取。

**验证**：`cd openbase-ui; .\node_modules\.bin\vitest.cmd run tests/r7-context-policy.spec.ts`

---

## T5 R7：设置页与路由 [x]

**文件**：新增 `openbase-ui/src/modules/openllm/pages/InferenceSettings.vue`；改 `openbase-ui/src/modules/openllm/index.ts`

**步骤**
1. 页面只读展示四策略语义、当前值与来源说明；管理员（`system:config`/`system:superadmin`）可编辑保存/恢复默认。
2. 路由 `settings` 与菜单「推理设置」；跑 `nav-consistency`。

**验证**：`cd openbase-ui; .\node_modules\.bin\vue-tsc.cmd --noEmit`；`vitest run tests/nav-consistency.spec.ts`

---

## T6 R7：Playground 透传与回显（追加；2026-11-21 裁定单独提交） [x]

**文件**：`openbase-ui/src/core/api/llm.ts`、`openbase-ui/src/modules/openllm/pages/Playground.vue`

**步骤**
1. `ChatStreamPayload` 增 `context_policy`；`ChatChunk` 增 `context_meta`。
2. `send()` 读取本地策略注入两条通道；`routing`/`done` 解析 `context_meta` 并展示。
3. 不改动用户既有双通道逻辑；按 2026-11-21 用户裁定，两文件作为 R7 前端闭环**单独提交**入库。

---

## T7 联调清单执行 [x]

**文件**：新增 `scripts/verify_full_chain_checklist.py`；新增 `doc/test/OpenBase-四基础子系统全链路联调清单执行记录-v1.0.0.md`

**步骤**
1. 探测环境端口，记录证据。
2. 逐项映射契约级证据（见 spec §4.2）。
3. 脚本实现八项检查、JSON 落盘、退出码语义。
4. 无环境时执行脚本，确认输出 BLOCKED 且退出码 0，记录到执行记录文档。

---

## T8 收口 [x]

1. 运行 spec §6 全部验证命令，记录结果。
2. `spec.md` / `tasks.md` 升 v1.1.0（实施记录、偏差）。
3. 方案文档升 v1.7.0，修订历史追加批次 4。

---

## T9 提交推送 [x]

1. OpenBase：新增前端文件、`openllm/index.ts`、脚本、文档；推送 origin/backup/github。
2. OpenLLM：3 个改动文件 + 1 个新测试；推送当前分支。
3. DPS/OpenRAG 零改动。
4. 明确排除 `openbase-ui/src/core/api/llm.ts`、`Playground.vue`（用户未提交改动）。

---

## 实施记录（v1.1.0，2026-11-12）

### 验证结果

| 范围 | 结果 |
|---|---|
| OpenBase ruff | All checks passed |
| OpenBase 定向回归（8 个文件） | 164 passed（0 失败） |
| OpenBase 全量 | 执行至 62% 无失败后主动终止（`.env` Redis 远端不可达导致逐例约 20s，环境限制） |
| 前端 vue-tsc | 0 错误 |
| 前端 vitest | 32 passed（R7 11 + 菜单一致性 21） |
| OpenLLM 新增 + 代理回归 | 11 passed |
| OpenLLM 文档/知识库/OpenRAG 回归 | 29 passed |
| 联调脚本 | `BLOCKED=8`，退出码 0，证据落盘 `doc/test/evidence/full-chain/` |

### 偏差

见 `spec.md` §9.2（8 项），核心为：两个路由改 `async`、reprocess 返回 `pending`、429→503 登记、门户七项路由登记不补、策略为浏览器本地配置、两个脏文件不入库、脚本 `trust_env=False`、测试 Redis 快速失败覆盖。

### 提交

- OpenLLM：`5bcd64e`（feature/s4-identity-channel-b，origin/backup/github）
- OpenBase：本批次收尾提交（origin/backup/github）

### 联调补跑（v1.2.0）

- 启动：`scripts/service-orchestrator.ps1 -Action start`（8000/8001/8010/8020/8030/5173 + PG 均健康）
- 执行：`scripts/verify_full_chain_checklist.py`（`OPENBASE_TOKEN` + `OPENBASE_TOKEN_B` + `OPENBASE_PROXY_SOURCE`）
- 结果：**PASS=7、PARTIAL=1（第 8 项 R5 未上线）、FAIL=0**，退出码 0
- 证据：`doc/test/evidence/full-chain/full-chain-20261112T175716Z.json`
- 前置：租户 B 主体 `batch4-t2-user`（tenant_id=2）、既有人员 `tenant-1_1`


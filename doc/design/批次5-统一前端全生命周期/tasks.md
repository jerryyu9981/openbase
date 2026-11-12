# 批次 5：统一前端四子系统全生命周期补齐（任务清单）

| 项 | 内容 |
|---|---|
| **版本** | v1.2.0 |
| **状态** | [Final]（已实施并验证，含 5.1 增量） |
| **对应规格** | `doc/design/批次5-统一前端全生命周期/spec.md` v1.2.0 |
| **适用范围** | OpenBase（门户后端 rag_proxy / dps_proxy、openbase-ui） |
| **作者** | 架构组 |
| **日期** | 2026-11-13 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-13 | 首版：T1~T10 任务拆分、依赖、验收映射与验证命令 | 架构组 |
| v1.1.0 | 2026-11-13 | 实施完成：T1~T10 全部勾选，回填验证记录（27/130/4/24/6/7 项用例与 41 项联合回归） | 架构组 |
| v1.2.0 | 2026-11-13 | 新增 T11：画像 DELETE 端点（DPS 软删除 + 门户代理 + 前端入口 + 测试） | 架构组 |

---

## 1. 执行约定

- 顺序执行；每个任务完成即勾选 `[x]`，并同步记录验证结果。
- 测试先行（RED → GREEN）：T4/T5/T7/T8 先补测试再改实现。
- 每条任务完成后运行对应验证命令，不通过不得进入下一任务。
- 提交边界见规格 §1.3：**不修改、不提交** `openbase-ui/src/core/api/llm.ts` 与 `Playground.vue`。

---

## 2. 任务清单

### T1 后端：知识库集合更新代理

- [x] `openbase/modules/rag_proxy/__init__.py` 新增 `CollectionUpdate` 模型（字段与边界见规格 §5.1.1）。
- [x] 新增 `PUT /collections/{collection_id}` 代理路由，`rebuild` 为 query 参数，`exclude_none=True, exclude_unset=True` 透传。
- [x] `tests/test_rag_proxy.py` 增补用例：转发方法/路径/查询参数正确；`rebuild=true` 仅在该值为真时出现；上游 409 原样透传。
- [x] 验证：`ruff check openbase tests`；`pytest tests/test_rag_proxy.py -q`。

**验收映射**：AC-KB-7。

### T2 后端：画像计算异步参数通道修正

- [x] `openbase/modules/dps_proxy/__init__.py` 修改 `dps_portrait_calculate`：新增 `async_` query（alias `async`），从 body 移除 `async`，按设置默认值决定 `true/false`。
- [x] `tests/test_dps_proxy.py` 增补用例：默认（设置开）→ 上游收到 `?async=true` 且 body 无 `async`；显式 `?async=false` → 覆盖默认；设置关且未显式 → `?async=false`。
- [x] 验证：`ruff check openbase tests`；`pytest tests/test_dps_proxy.py tests/test_dps_proxy_routes_v1410.py -q`。

**验收映射**：AC-POR-1、AC-POR-2。

### T3 前端 API：会话子系统封装

- [x] 新建 `openbase-ui/src/core/api/conversation.ts`：`ConversationMessage` 类型、`conversationApi.getConversation`、`conversationApi.appendMessage`。
- [x] 不修改 `core/api/llm.ts`（会话列表/删除/归档/消息列表继续复用 `llmApi`）。
- [x] 验证：`vue-tsc --noEmit`。

**验收映射**：AC-CTX-1、AC-CTX-2。

### T4 前端：会话历史加载与回写

- [x] 先写 `openbase-ui/tests/conversation-lifecycle.spec.ts`（mock `llmApi` 与 `conversationApi`）：
  - 打开会话触发 `listMessages` 并渲染历史；
  - 发送后调用 `appendMessage` 两次（user/assistant）；
  - 加载失败展示提示条与重试。
- [x] `modules/openllm/pages/Conversations.vue`：`openChat` 改为异步加载详情 + 消息；新增 `historyLoading`/`historyError`；发送完成后 best-effort 回写。
- [x] 归档会话续聊时按后端 400 提示「会话已归档，请先取消归档」。
- [x] 验证：`vitest run tests/conversation-lifecycle.spec.ts`、`vue-tsc --noEmit`。

**验收映射**：AC-CTX-1~4。

### T5 前端：记忆运行监控页

- [x] 先写 `openbase-ui/tests/memory-monitor.spec.ts`（mock `http.get`）：三探针并发、`range` 变更仅重拉 monitor、单探针失败降级。
- [x] 新建 `modules/memory/pages/MemoryMonitor.vue`：三探针状态卡、`range` 选择（1h/24h/7d）、monitor 指标渲染、刷新/重试、`data-test` 属性。
- [x] `modules/memory/index.ts` 新增 `monitor` 路由与菜单「运行监控」。
- [x] 验证：`vitest run tests/memory-monitor.spec.ts tests/nav-consistency.spec.ts`、`vue-tsc --noEmit`。

**验收映射**：AC-MEM-1~4。

### T6 前端 API：画像与知识库封装补齐

- [x] `core/api/dps.ts` 追加 `getPortraitByExternal`、`updatePortrait`（`If-Match` 由 `version` 生成）。
- [x] `core/api/rag.ts` 追加 `RagCollectionUpdate` 类型与 `updateCollection`（`rebuild` 参数）。
- [x] 验证：`vue-tsc --noEmit`。

**验收映射**：AC-POR-3、AC-POR-4、AC-KB-7。

### T7 前端：画像计算、外部 ID 查询与属性编辑

- [x] 先写 `openbase-ui/tests/portrait-lifecycle.spec.ts`：计算（task_id 轮询成功/失败/同步返回）、外部 ID 命中跳转、PATCH 携带 `If-Match`、409 触发重载。
- [x] `modules/portrait/pages/PortraitList.vue`：新增「计算画像」对话框与「按外部 ID 查询」；轮询复用 `dpsApi.waitPortraitTask`。
- [x] `modules/portrait/pages/PortraitDetail.vue`：展示 `version`；新增「编辑属性」抽屉（JSON 校验、PATCH、409 处理）。
- [x] 验证：`vitest run tests/portrait-lifecycle.spec.ts`、`vue-tsc --noEmit`。

**验收映射**：AC-POR-1~6。

### T8 前端：知识库详情页真实化

- [x] 先写 `openbase-ui/tests/knowledge-lifecycle.spec.ts`：集合信息/文档列表来自 API；上传后轮询至终态；重建/删除调用对应 API；检索与问答分别调用 `retrieve`/`query`；集合更新确认 `rebuild`；断言无硬编码文档。
- [x] 重写 `modules/knowledge/pages/KnowledgeDetail.vue`：
  - 集合信息 + 编辑对话框（分块字段变更二次确认 → `rebuild=true`）；
  - 文档表格（状态映射、上传轮询、重建索引、删除）；
  - 检索台双模式（纯检索 / RAG 问答），移除 `agentMode`；
  - 统一 `describeError` 与空态/加载态。
- [x] 验证：`vitest run tests/knowledge-lifecycle.spec.ts`、`vue-tsc --noEmit`。

**验收映射**：AC-KB-1~8。

### T9 全量验证

- [x] 后端：`ruff check openbase tests`（0 错误）；定向 `pytest tests/test_rag_proxy.py tests/test_dps_proxy.py tests/test_dps_proxy_routes_v1410.py tests/test_dps_proxy_v1410_contract.py -q`（全通过）。
- [x] 前端：`vue-tsc --noEmit`（0 错误）；`vitest run tests/nav-consistency.spec.ts tests/conversation-lifecycle.spec.ts tests/memory-monitor.spec.ts tests/portrait-lifecycle.spec.ts tests/knowledge-lifecycle.spec.ts`（全通过）。
- [x] 结果回填至本文件「3. 验证记录」。

**验收映射**：§8 质量门禁。

### T10 留痕与提交

- [x] 规格与任务清单升版（v1.1.0），追加修订历史与实施记录（含偏差）。
- [x] 更新方案文档《OpenBase-四基础子系统全链路贯通修复方案-v1.0.0.md》版本至 v1.8.0，登记批次 5 范围与结论。
- [x] 按规格 §1.3 提交边界提交并推送三远程（origin / backup / github `main`），提交 `353fd0e`。
- [x] 核对 `git status`：确认未误纳入 `llm.ts`、`Playground.vue`、`scripts/service-orchestrator.ps1` 及用户其他未提交文件。

**验收映射**：文档与仓库留痕。

### T11 画像 DELETE 端点补齐（批次 5.1）

- [x] DPS 新增 `DELETE /api/v2/portrait/{person_id}`（软删除 + 租户隔离 + 幂等），`src/tests/test_batch5_1_portrait_delete.py` 4 例。
- [x] 门户新增 `DELETE /api/v1/dps-proxy/portraits/{person_id}` 代理，`tests/test_dps_proxy.py` 新增 3 例（转发/404/幂等透传）。
- [x] 前端 `dpsApi.deletePortrait` + 列表删除 + 详情删除（二次确认、404 提示、详情返回列表），`portrait-lifecycle.spec.ts` 新增 2 例。
- [x] 验证：DPS 11 passed（含既有 PATCH 回归）、门户 44 passed、前端 8 passed、`vue-tsc --noEmit` 0 错误。
- [x] 文档：规格 §11（AC-DEL-1~4）与方案 v1.9.0 留痕。

**验收映射**：AC-DEL-1~4。

---

## 3. 验证记录

> 实施完成后回填（命令、结果、证据路径）。

| 任务 | 命令 | 结果 | 备注 |
|---|---|---|---|
| T1 | `pytest tests/test_rag_proxy.py -q` | 27 passed | 新增 3 例（PUT 转发/rebuild query/409 透传） |
| T2 | `pytest tests/test_dps_proxy.py tests/test_dps_proxy_routes_v1410.py tests/test_dps_proxy_v1410_contract.py -q` | 130 passed | 新增 1 例 + 修订 3 例（async 走 query） |
| T4 | `vitest run tests/conversation-lifecycle.spec.ts` | 4 passed | 历史加载/回写/失败重试/归档提示 |
| T5 | `vitest run tests/memory-monitor.spec.ts tests/nav-consistency.spec.ts` | 24 passed | 三探针/range/失败降级 + 导航一致 |
| T7 | `vitest run tests/portrait-lifecycle.spec.ts` | 6 passed | 异步与同步计算/外部 ID/PATCH/409 |
| T8 | `vitest run tests/knowledge-lifecycle.spec.ts` | 7 passed | 真实数据/上传轮询/重建/删除/双模式/rebuild |
| T9 | `ruff check openbase tests` | All checks passed | 0 错误 |
| T9 | `vitest run <5 个 spec>` | 41 passed / 5 files | 含 nav-consistency 21 例 |
| T9 | `vue-tsc --noEmit` | 0 错误 | — |
| T11 | `pytest src/tests/test_batch5_1_portrait_delete.py`（DPS） | 4 passed | 软删除可见性/幂等/404/租户隔离 |
| T11 | `pytest tests/test_dps_proxy.py` | 44 passed | 新增 DELETE 转发/404/幂等 3 例 |
| T11 | `vitest run tests/portrait-lifecycle.spec.ts` | 8 passed | 新增列表/详情删除 2 例 |

---

## 4. 依赖与顺序

```
T1 ─┐
T2 ─┼─→ T3 ─→ T4
T6 ─┼─→ T7
    └─→ T8（依赖 T1、T6）
T9（依赖 T1~T8 全部完成）─→ T10
```

- T3/T6 仅涉及 API 封装，可与 T1/T2 并行。
- T8 依赖 T1（后端 PUT）与 T6（前端 `updateCollection`）。

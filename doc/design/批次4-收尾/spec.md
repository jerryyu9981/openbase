# 批次 4 收尾规格说明（R7 前端 / R2 端点核对 / 联调清单 / 文档收口）

| 项 | 内容 |
|---|---|
| **版本** | v1.2.0 |
| **状态** | [Review] |
| **适用范围** | OpenBase（门户/前端）、OpenLLM（知识库路由）；DPS/OpenRAG 仅核对不改动 |
| **上游依据** | 《OpenBase-四基础子系统全链路贯通审计报告-v1.0.0》§4 联调清单；《全链路贯通修复方案-v1.6.0》；《批次 3 全链路贯通修复规格》§7 风险表 |
| **作者** | 架构组 |
| **日期** | 2026-11-12 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-12 | 首版：批次 4 四项范围（R7 前端展示、R2 遗漏端点核对、审计 §4 联调清单执行、文档收口）的改动文件、契约、验证命令、提交边界与回滚 | 架构组 |
| v1.1.0 | 2026-11-12 | 实施完成：R2 补齐 documents 详情/重处理代理，R7 前端设置页与 Playground 透传回显落地，§4 八项联调契约级核对与可复跑脚本交付；追加 §9 实施记录（验证结果与 7 项偏差） | 架构组 |
| v1.2.0 | 2026-11-12 | 联调补跑：全栈启动后八项实测 PASS=7 / PARTIAL=1（第 8 项 R5 未上线）；脚本适配受信来源头、租户 B 主体令牌、既有画像人员；新增偏差 9 | 架构组 |

---

## 1. 范围与约束

本批次为收尾批次，只做四项：

| 顺序 | 编号 | 目标 | 改动仓 |
|---|---|---|---|
| 1 | R2 | 遗漏端点核对：补齐代理分支，登记不补齐项 | OpenLLM |
| 2 | R7 | 前端设置页展示上下文裁剪策略 + Playground 透传与回显 | OpenBase（前端） |
| 3 | 联调 | 审计报告 §4 八项联调清单执行与证据留痕 | OpenBase |
| 4 | 收口 | 文档升版、任务勾选、提交推送 | 全部 |

统一约束：

1. **不含**：R5 生产 `enforce` 开关、G5 兜底清理、G2 agent 租户治理；本批次不改 DPS/OpenRAG 代码。
2. R7 前端仅新增"客户端侧策略配置"（localStorage），不新增后端配置端点；OpenLLM 已有 `context_policy` 契约（批次 3）。
3. **提交边界**：`openbase-ui/src/core/api/llm.ts`、`openbase-ui/src/modules/openllm/pages/Playground.vue` 含用户未提交的双通道改动。本批次仅在其上**追加** R7 内容，**禁止覆盖**；提交时**不纳入**这两个文件（保留在工作区，由用户自行决定提交），仅提交新增前端文件与 `modules/openllm/index.ts`。
4. 错误响应保持 `{code, message, detail, request_id}`；OpenLLM 保持既有 `HTTPException` 详情信封。
5. 新增文件与改动须中文注释，命名遵循仓库既有约定。
6. 文档每次更新同步升版本并追加修订历史。

---

## 2. R2 遗漏端点核对（OpenLLM）

### 2.1 核对方法

以 `OpenLLM/backend/app/api/*.py` 的 `APIRouter` 注册表为全集，与 `OpenRAG/src/openrag/api/routes/collections.py`、`documents.py` 的实际路由逐条对照，核验批次 3 代理分支的覆盖率。

### 2.2 核对结论

| OpenLLM 旧端点 | 批次 3 状态 | 本批次处置 |
|---|---|---|
| `GET /knowledge-bases` | 已代理 | 不改 |
| `POST /knowledge-bases` | 已代理 | 不改 |
| `GET /knowledge-bases/{kb_id}` | 已代理 | 不改 |
| `PUT /knowledge-bases/{kb_id}` | 已代理 | 不改 |
| `DELETE /knowledge-bases/{kb_id}` | 已代理 | 不改 |
| `GET /knowledge-bases/{kb_id}/stats` | 已代理 | 不改 |
| `POST /knowledge-bases/{kb_id}/documents` | 已代理（UTF-8 文本提取） | 不改 |
| `GET /knowledge-bases/{kb_id}/documents` | 已代理 | 不改 |
| `GET /knowledge-bases/{kb_id}/documents/{doc_id}` | **遗漏**（无代理分支，代理模式下 kb_id 非 UUID → 404） | **本次补齐**：`bridge.get_document` |
| `DELETE /knowledge-bases/{kb_id}/documents/{doc_id}` | 已代理 | 不改 |
| `POST /knowledge-bases/{kb_id}/documents/{doc_id}/reprocess` | **遗漏**（仅本地分支，代理模式必然 404） | **本次补齐**：映射 OpenRAG `POST /collections/{cid}/documents/{did}/reindex` |

### 2.3 改动清单（OpenLLM）

1. `backend/app/edgerouter/adapters/openrag_client.py`
   - 新增 `reindex_document(collection_id, document_id, headers=None) -> dict[str, Any]`：
     `POST {base}/api/v1/collections/{cid}/documents/{did}/reindex`，复用 `_request` + `_raise_business_error`，返回信封 `data`（缺省 `{}`）。
2. `backend/app/services/kb_openrag_bridge.py`
   - 新增 `reindex_document(tenant_code, collection_id, document_id)`，透传身份头。
3. `backend/app/api/documents.py`
   - `get_document` 改为 `async def`；在本地分支前增加代理分支：
     `resolve_tenant_code` → `bridge.resolve_collection_id` → `bridge.get_document` → `document_to_legacy(...)` + `DEPRECATION_HEADERS`；`ComponentUnavailableError` → `upstream_unavailable`（503）。
   - `reprocess_document` 改为 `async def`；在 `ensure_local_writable()` **之前**增加代理分支：
     同上解析后调用 `bridge.reindex_document`，返回 `document_to_legacy` + `DEPRECATION_HEADERS`（HTTP 200）。
4. 单测：新增 `backend/tests/unit/test_kb_documents_proxy_gaps.py`，覆盖
   - 代理开启时 `GET /documents/{id}` 命中 fake bridge 且返回旧字段；
   - 代理开启时 `POST /documents/{id}/reprocess` 调用 `reindex_document`；
   - 上游不可用 → 503；代理关闭时 `reprocess` 仍走本地（只读开关开启则 410）。

### 2.4 登记不补齐项（门户 `rag_proxy` vs OpenRAG）

以下 OpenRAG 路由门户 `openbase/modules/rag_proxy` 未暴露，**本批次登记、不实现**（门户现有页面未使用，补代理需产品确认字段映射与权限口径）：

| OpenRAG 路由 | 说明 | 登记理由 |
|---|---|---|
| `PUT /collections/{cid}` | 集合配置更新 | 门户无编辑入口；批次 3 已由 OpenLLM 旧接口代理覆盖 |
| `GET /collections/{cid}/stats` | 集合统计 | 门户无展示位 |
| `GET /collections/{cid}/health` | 集合健康 | 门户 `/rag-proxy/health` 为上游整体健康 |
| `GET /documents/{did}/chunks` | 分块查看 | 门户无分块浏览页 |
| `GET /documents/{did}/download` | 原文下载 | 门户无下载入口 |
| `POST /documents/batch` | 批量操作 | 门户无批量交互 |
| `POST /documents/text` | JSON 文本入库 | 门户上传走 multipart；OpenLLM 旧接口已代理改走文本入库 |

### 2.5 验收

- 代理模式下 `GET /knowledge-bases/{cid}/documents/{did}` 返回 200 且字段与旧 `DocumentResponse` 同构；
- 代理模式下 `POST .../reprocess` 触发上游 reindex 且返回 200；
- 代理关闭时两个端点行为与现网完全一致（回归）；
- OpenLLM 定向单测全通过。

---

## 3. R7 前端展示

### 3.1 现状与目标

后端已支持 `context_policy` 请求字段与 `context_meta` 回显（批次 3）。前端无任何展示与入口。
目标：设置页可查看/（管理员）调整裁剪策略；Playground 聊天请求携带策略；流式响应回显 `context_meta`。

### 3.2 新增模块 `openbase-ui/src/core/contextPolicy.ts`

纯函数模块（无 Vue 依赖，便于单测）：

```ts
export type ContextStrategy = 'recent' | 'head_tail' | 'system_priority' | 'summarize_old'
export interface ContextPolicy {
  strategy: ContextStrategy
  max_tokens?: number
  preserve_recent_n?: number
}
export interface ContextMeta {
  strategy?: string
  budget_tokens?: number
  history_messages?: number
  included_messages?: number
  dropped_messages?: number
  history_tokens?: number
  summarized?: boolean
  applied?: boolean
  source?: string
}
export const CONTEXT_POLICY_STORAGE_KEY = 'openbase.contextPolicy'
export const CONTEXT_STRATEGY_LABELS: Record<ContextStrategy, string>
export function normalizeContextPolicy(raw: unknown): ContextPolicy | null  // 校验并裁剪非法值；全默认返回 null
export function loadContextPolicy(): ContextPolicy | null                    // localStorage 读取 + normalize
export function saveContextPolicy(policy: ContextPolicy | null): void       // null 时删除键
export function extractContextMeta(payload: unknown): ContextMeta | null    // 从 routing/done 事件 data 提取 context_meta
```

规则：`strategy` 白名单外 → `recent`；`max_tokens` 非正整数或 >200000 → 丢弃；`preserve_recent_n` 非负整数或 >100 → 丢弃；`recent` 策略时 `preserve_recent_n` 不输出。

### 3.3 新增页面 `openbase-ui/src/modules/openllm/pages/InferenceSettings.vue`

- 只读展示：当前策略（中文标签）、`max_tokens`、`preserve_recent_n`、策略语义说明（四策略各一行）。
- 管理员（`auth.hasPermission('system:config') || auth.hasPermission('system:superadmin')`）可见"编辑/保存/恢复默认"；非管理员仅只读，并提示"需系统管理员权限"。
- 保存写入 localStorage，提示"仅影响当前浏览器，随下一次对话透传"。
- 表单校验与 `normalizeContextPolicy` 同口径；`data-test`：`context-policy-card`、`context-policy-strategy`、`context-policy-max-tokens`、`context-policy-preserve`、`context-policy-save`、`context-policy-reset`。
- 路由与菜单：`openbase-ui/src/modules/openllm/index.ts` 增加 `{ path: 'settings', name: 'openllm-settings', ... }`，并在"AI 应用"分组加入菜单项「推理设置」。

### 3.4 追加（不覆盖）现有脏文件

1. `openbase-ui/src/core/api/llm.ts`
   - `import type { ContextPolicy, ContextMeta } from '@/core/contextPolicy'`
   - `ChatStreamPayload` 增加 `context_policy?: ContextPolicy`；`ChatChunk` 增加 `context_meta?: ContextMeta`。
2. `openbase-ui/src/modules/openllm/pages/Playground.vue`
   - `send()` 组装 payload 时：`const policy = loadContextPolicy(); if (policy) payload.context_policy = policy`（直连与自动编排两条通道都携带）。
   - SSE `routing` 与 `done` 事件解析中调用 `extractContextMeta`，保存到 `contextMeta` ref；模板在 `channel-hint` 下方新增一行 `data-test="playground-context-meta"`：`上下文 <策略> · 入参 N/M 条 · 预算 B tokens`（无 meta 时不渲染）。

### 3.5 单测

新增 `openbase-ui/tests/r7-context-policy.spec.ts`：

- `normalizeContextPolicy` 白名单/范围/非法类型用例；
- `load/save` 读写与删除（清空 localStorage 后返回 null）；
- `extractContextMeta` 从 `routing`/`done` 两种载荷提取、缺失返回 null；
- 挂载 `InferenceSettings.vue`：无权限只读、有权限保存调用 localStorage。

### 3.6 验收

- 设置页展示当前策略；管理员修改后刷新仍保留；非管理员无法保存；
- Playground 请求体可见 `context_policy`（单测断言），流式响应含 `context_meta` 时展示摘要；
- `vue-tsc --noEmit` 0 错误；新增 vitest 用例全通过；既有 `nav-consistency` 用例全通过。

### 3.7 提交边界

`llm.ts`、`Playground.vue` 的改动**不进入本批次提交**（见 §1 约束 3）；提交内容为 `contextPolicy.ts`、`InferenceSettings.vue`、`openllm/index.ts`、新测试文件。

---

## 4. 审计报告 §4 联调清单执行

### 4.1 执行方式

环境探测结论：`127.0.0.1` 的 8000/8010/8020/8030/8040/5173/11434 **均未监听**，无法进行真实端到端联调。
因此采用"契约级验证 + 可复跑脚本"双轨：

> **v1.2.0 补跑**：通过 `scripts/service-orchestrator.ps1 -Action start` 启动五个服务与前端后，
> 八项实测结果为 **PASS=7、PARTIAL=1（第 8 项缺租户头，R5 生产 enforce 未上线）、FAIL=0**，
> 证据 `doc/test/evidence/full-chain/full-chain-20261112T175716Z.json`。详见
> `doc/test/OpenBase-四基础子系统全链路联调清单执行记录-v1.0.0.md` v1.1.0。

1. 契约级：以既有 pytest 用例（代理转发、租户隔离、画像合并、上下文策略）为证据，逐项给出结论；
2. 可复跑：新增 `scripts/verify_full_chain_checklist.py`，在运行环境可用时一键执行八项并落盘证据。

### 4.2 八项映射

| # | 清单项 | 契约级证据（文件::用例） | 本次结论 |
|---|---|---|---|
| 1 | 上下文两轮 | `OpenLLM/backend/tests/unit/test_context_policy.py`；`tests/test_llm_proxy_context_policy.py` | 契约级 PASS；端到端 BLOCKED（需 OpenLLM+Ollama） |
| 2 | 记忆召回 | `tests/test_memory_proxy.py`（recall 转发与身份头） | 契约级 PASS；端到端 BLOCKED（需 OpenMemory） |
| 3 | 记忆 PATCH | `openbase/modules/proxy/memory_proxy.py::patch("/memories/{memory_id}")` + `tests/test_memory_proxy.py` | 契约级 PASS；端到端 BLOCKED |
| 4 | 知识库上传/检索 | `tests/test_rag_proxy.py`（上传/列表/查询转发） | 契约级 PASS；端到端 BLOCKED（需 OpenRAG） |
| 5 | 租户隔离 404 | `tests/test_rag_proxy_identity_policy.py`（上游 404 透传） | 契约级 PASS；端到端 BLOCKED |
| 6 | 画像计算/读取 | `tests/test_dps_proxy.py`（calculate/详情转发） | 契约级 PASS；端到端 BLOCKED（需 DPS） |
| 7 | 画像双标签合并 | `DPS/src/tests/test_batch2_r1_patch_merge.py`（PATCH 深合并） | 契约级 PASS；端到端 BLOCKED |
| 8 | 缺租户头 400 | `tests/test_entry_tenant_guard.py` | 按当前实现记录实际状态码；R5 生产 enforce 未上线，结论"部分满足" |

### 4.3 新增脚本 `scripts/verify_full_chain_checklist.py`

- 环境变量：`OPENBASE_BASE_URL`（默认 `http://127.0.0.1:8000`）、`OPENBASE_TOKEN`（Bearer）、`OPENBASE_TENANT_ID`（A 租户）、`OPENBASE_TENANT_ID_B`（隔离租户）。
- 依赖：仅 `httpx`（OpenBase venv 已具备）。
- 行为：逐项执行 §4.2 八项；连接失败 → 该项 `BLOCKED`；断言失败 → `FAIL`；全通过 → `PASS`。
- 输出：控制台摘要 + `--json` 全量；默认写入 `doc/test/evidence/full-chain/full-chain-<UTC时间戳>.json`。
- 退出码：存在 `FAIL` → 1；否则 0（`BLOCKED` 不算失败，但摘要中显著标注）。

### 4.4 执行记录文档

新增 `doc/test/OpenBase-四基础子系统全链路联调清单执行记录-v1.0.0.md`：环境探测证据、八项逐条结论、脚本用法、遗留项（R5 enforce、运行环境）。

---

## 5. 文档与留痕

1. 本规格与 `tasks.md` 实施后升 **v1.1.0**，追加"实施记录"（验证命令与结果、偏差）。
2. `doc/design/OpenBase-四基础子系统全链路贯通修复方案-v1.0.0.md` 升 **v1.7.0**：批次 4 记录（R2 补齐项与登记项、R7 前端、联调清单结论）。
3. `tasks.md` 逐项勾选。

---

## 6. 验证命令

```powershell
# OpenBase 静态检查与全量测试
D:\venvs\openbase\Scripts\ruff.exe check openbase tests
D:\venvs\openbase\Scripts\python.exe -m pytest tests

# OpenBase 定向
D:\venvs\openbase\Scripts\python.exe -m pytest tests/test_llm_proxy_context_policy.py tests/test_rag_proxy.py tests/test_dps_proxy.py tests/test_memory_proxy.py tests/test_entry_tenant_guard.py -q

# OpenLLM 定向（新增与回归）
D:\venvs\openllm\Scripts\python.exe -m pytest backend/tests/unit/test_kb_documents_proxy_gaps.py backend/tests/unit/test_kb_proxy_mode.py backend/tests/unit/test_documents_api.py -q

# 前端类型检查与单测
cd openbase-ui; .\node_modules\.bin\vue-tsc.cmd --noEmit
cd openbase-ui; .\node_modules\.bin\vitest.cmd run tests/r7-context-policy.spec.ts tests/nav-consistency.spec.ts

# 联调清单脚本（无环境时输出 BLOCKED）
D:\venvs\openbase\Scripts\python.exe scripts/verify_full_chain_checklist.py --json
```

已知噪声：`tests/test_settings.py::test_dps_upstream_defaults_aligned_to_source_port` 全量串跑偶发失败（单跑通过），与本批次无关。

---

## 7. 风险与回滚

| 风险 | 处置 |
|---|---|
| OpenRAG reindex 限流（60s 内重复 429）被 `_raise_business_error` 映射为 503 | 登记为已知偏差；前端提示"稍后重试" |
| 前端权限点 `system:config` 与现网角色不匹配 | 同时接受 `system:superadmin`；无权限时降级只读，不影响使用 |
| 修改脏文件引入用户改动覆盖 | 仅追加片段；提交排除两个脏文件 |
| 联调脚本在无环境时报错 | 连接失败统一记 `BLOCKED`，退出码 0 |
| 新增路由影响菜单一致性用例 | 同批更新 `openllm/index.ts` 路由与菜单，跑 `nav-consistency.spec.ts` |

回滚：OpenLLM 删除两个代理分支与两个新方法；前端删除新增页面与路由、Playground 追加段；脚本与文档删除即可。无数据库变更。

---

## 8. 附录：本批次文件清单

**OpenLLM（改）**

- `backend/app/edgerouter/adapters/openrag_client.py`
- `backend/app/services/kb_openrag_bridge.py`
- `backend/app/api/documents.py`
- `backend/tests/unit/test_kb_documents_proxy_gaps.py`（新）

**OpenBase（改/新）**

- 新：`openbase-ui/src/core/contextPolicy.ts`
- 新：`openbase-ui/src/modules/openllm/pages/InferenceSettings.vue`
- 改：`openbase-ui/src/modules/openllm/index.ts`
- 新：`openbase-ui/tests/r7-context-policy.spec.ts`
- 新：`scripts/verify_full_chain_checklist.py`
- 改（仅工作区，不提交）：`openbase-ui/src/core/api/llm.ts`、`openbase-ui/src/modules/openllm/pages/Playground.vue`
- 新：`doc/design/批次4-收尾/spec.md`、`tasks.md`
- 新：`doc/test/OpenBase-四基础子系统全链路联调清单执行记录-v1.0.0.md`
- 改：`doc/design/OpenBase-四基础子系统全链路贯通修复方案-v1.0.0.md`（升 v1.7.0）

---

## 9. 实施记录（v1.1.0，2026-11-12）

### 9.1 验证结果

| 范围 | 命令 | 结果 |
|---|---|---|
| OpenBase 静态检查 | `ruff check openbase tests` | All checks passed |
| OpenBase 全量测试 | `python -m pytest tests` | 环境限制：`.env` 的 Redis 指向 `192.168.0.151:6380` 不可达，逐用例连接等待导致约 20s/例；执行至 **62%（0 失败）** 后主动终止（非代码失败） |
| OpenBase 定向回归 | `pytest test_llm_proxy.py test_llm_proxy_context_policy.py test_rag_proxy.py test_rag_proxy_identity_policy.py test_dps_proxy.py test_memory_proxy.py test_entry_tenant_guard.py test_proxy_auth.py`（`OPENBASE_REDIS_URL` 指向本地未监听端口快速失败） | **164 passed**（330s，0 失败） |
| 前端类型检查 | `vue-tsc --noEmit` | 0 错误 |
| 前端单测 | `vitest run tests/r7-context-policy.spec.ts tests/nav-consistency.spec.ts` | 32 passed（R7 11 + 菜单一致性 21） |
| OpenLLM 新增单测 | `pytest backend/tests/unit/test_kb_documents_proxy_gaps.py test_kb_proxy_mode.py` | 11 passed |
| OpenLLM 回归 | `pytest test_documents_api.py test_openrag_client.py test_knowledge_bases_api.py` | 29 passed |
| 联调脚本 | `python scripts/verify_full_chain_checklist.py` | `BLOCKED=8`，退出码 0，证据已落盘 |
| 联调补跑（全栈启动） | 同上（`OPENBASE_TOKEN` + `OPENBASE_TOKEN_B` + `OPENBASE_PROXY_SOURCE`） | **PASS=7、PARTIAL=1、FAIL=0**，退出码 0 |

### 9.2 偏差与实现说明

1. **`get_document` / `reprocess_document` 改为 `async def`**：原为同步函数，新增代理分支需 await 桥接调用；FastAPI 调用方式不变，本地分支逻辑与返回结构不变。
2. **reprocess 代理响应状态**：OpenRAG reindex 仅返回任务受理结果，旧字段输出统一置 `status=pending`，真实状态由详情端点轮询。
3. **上游 429 映射**：OpenRAG reindex 60 秒冷却返回 429，经 `_raise_business_error` 统一转 `ComponentUnavailableError` → 503；已登记为已知偏差。
4. **门户 `rag_proxy` 七项路由登记不补**：`PUT collection`、`stats`、`health`、`chunks`、`download`、`batch`、`text` 门户无使用场景，按 §2.4 登记，待产品确认后再补。
5. **前端策略配置为浏览器本地**：使用 `localStorage`（键 `openbase.contextPolicy`），未新增后端配置端点；管理员判定为 `system:config` 或 `system:superadmin`。
6. **两个脏文件不提交**：`openbase-ui/src/core/api/llm.ts`、`Playground.vue` 仅在用户既有双通道改动上追加 R7 片段，按要求不纳入本批次提交，保留在工作区。
7. **联调脚本禁用系统代理**：`httpx.Client(trust_env=False)`，避免本机代理不可达导致连接长期挂起；连接拒绝统一记 `BLOCKED`。
8. **测试环境 Redis 加速**：本机 `.env` 的 `OPENBASE_REDIS_URL` 指向不可达远端，`isolate_identity_cache` 逐用例连接等待；定向回归通过临时覆盖 `OPENBASE_REDIS_URL=redis://127.0.0.1:6399/0`（快速失败）执行，未改动任何代码与配置。
9. **联调脚本按真实契约适配**（补跑发现）：① 非受信来源携带身份头会被 403，脚本增加 `X-Proxy-Source=openbase-orchestrator`（受信来源）；② `llm-proxy` 不携带 `X-Tenant-ID`（否则与 API Key 归属不一致触发 OpenLLM D20 403）；③ 隔离验证改用租户 B 主体令牌 `OPENBASE_TOKEN_B`（入站租户头不改变 JWT 主体归属）；④ 画像计算使用既有人员（不存在 `person_id` 返回 404）；⑤ 第 8 项按实际返回 200 记 `PARTIAL`（R5 未上线）。


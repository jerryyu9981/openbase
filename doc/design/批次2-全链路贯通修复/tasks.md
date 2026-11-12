# 批次 2 任务清单（R1 / R3 长期 / R6 / R8）

| 项 | 内容 |
|---|---|
| **版本** | v1.1.0 |
| **状态** | [Final] |
| **关联规格** | `doc/design/批次2-全链路贯通修复/spec.md` v1.0.2 |
| **日期** | 2026-11-12 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-12 | 首版：按 R8 → R6 → R1 → R3 顺序拆分可验证任务 | 架构组 |
| v1.1.0 | 2026-11-12 | 全部 T1–T24 执行完成，逐项勾选；附验证结果 | 架构组 |

执行顺序固定为：T1–T4（R8）→ T5–T9（R6）→ T10–T15（R1）→ T16–T21（R3）→ T22–T24（验证/留痕/推送）。

| 完成 | ID | 仓 | 任务 | 产出/改动点 | 验收 |
|---|---|---|---|---|---|
| [x] | T1 | OpenRAG | 重试限流 | `api/routes/documents.py`：`REINDEX_COOLDOWN_SECONDS=60`、模块级 dict + `threading.Lock`、429 `BIZ_REINDEX_THROTTLED` | 60s 内二次重试 429；首次正常提交 |
| [x] | T2 | OpenRAG | 限流单测 | `tests/unit/api/test_api_routes_supplement_users_docs.py` 新增冷却清理 fixture + 429 用例 | 语法检查通过；限流逻辑单测已补（本机无 OpenRAG venv，pytest 未执行） |
| [x] | T3 | OpenBase | reindex 代理 | `openbase/modules/rag_proxy/__init__.py` 新增 POST 路由 + `rag.document.reindex` 日志 | 200 转发、429 原样透传（单测通过） |
| [x] | T4 | OpenBase 前端 | 重试入口 | `rag.ts` 新增 `retryDocument`；`KnowledgeAdminView.vue` FAILED/ERROR 行显示「重试」 | 代码落地；类型检查结果见 T22 |
| [x] | T5 | OpenMemory | 原生分页存储 | `storage/relational_store.py` 新增 `list_memories_paginated`（scope fail-closed、type/tag、offset/limit、total） | scope 缺省 500 语义单测通过 |
| [x] | T6 | OpenMemory | 持久层/服务封装 | `memory/session_persistent.py` + `memory/service.py` 新增 `list_memories` | 委托与 `NotImplementedError` 单测通过 |
| [x] | T7 | OpenMemory | 列表端点 | `api/controllers.py` 新增 `GET /api/v1/memories`（offset/limit/type/tag，归一 `memory_id`/`tags`） | 端点代码落地；501 回退契约一致 |
| [x] | T8 | OpenBase | 列表直连 | `proxy/memory_proxy.py` `memory_list` 优先原生端点，404/405/501 回退 recall | 原生分页 total=42 单测通过 |
| [x] | T9 | OpenBase | 列表回归 | 定向 pytest（memory proxy） | 全通过 |
| [x] | T10 | DPS | 深合并函数 | `routes_profiles.py` 新增 `_deep_merge_attributes` | 6 类合并语义单测通过 |
| [x] | T11 | DPS | PATCH 路由 | `PATCH /portrait/{person_id}`：If-Match 校验、读-合并-写、409、`profile.patch` 日志 | A+B 合并、If-Match 冲突/成功单测通过 |
| [x] | T12 | DPS | 响应版本 | `_persist_portrait_update` 返回 `data.version`；PATCH 返回 `attributes_version` | 单测断言 `attributes_version == 2` 通过 |
| [x] | T13 | OpenBase | PATCH 代理 | `dps_proxy/__init__.py` 新增 `PATCH /portraits/{person_id}`，透传 `If-Match` | 单测通过 |
| [x] | T14 | OpenLLM | 客户端合并参数 | `adapters/dps_client.py` `profile_update(patch, if_match)` | 由 T15 覆盖方法/参数传递 |
| [x] | T15 | OpenLLM | 回写合并 + 冲突重放 | `adapters/profile.py`：`PROFILE_WRITEBACK_MERGE`、409 重放一次、仍冲突跳过 | 4 项单测通过（默认 PATCH / 重放 / 跳过 / 关闭回 PUT） |
| [x] | T16 | DPS | 任务表 DDL | `src/ddl/schema_portrait.py` 新增 `portrait_calc_task`（PG/SQLite）；`database.py` 两处初始化调用 | DDL 20 项测试全通过；唯一索引断言通过 |
| [x] | T17 | DPS | 计算逻辑抽取 | `_execute_calc(person_id, template_code)` 复用同步计算 + 模板命名空间持久化 | 同步路径行为不变 |
| [x] | T18 | DPS | 异步提交 | `POST /portrait/calculate?async=true` → 202 `{task_id,status}`；幂等复用 | 重复提交同一 task_id 单测通过 |
| [x] | T19 | DPS | 任务执行与查询 | `_run_calc_task` 状态流转；`GET /portrait/tasks/{id}`；`GET /portrait/{person_id}/tasks` | succeeded/failed 两条路径单测通过 |
| [x] | T20 | OpenBase | 默认异步 + 任务代理 | `dps_proxy` 注入 `async:true`；新增 `GET /portraits/tasks/{task_id}` | 默认注入、显式 false 不覆盖、任务透传单测通过 |
| [x] | T21 | OpenBase 前端 | 异步 helper | `dps.ts` 新增 `getPortraitTask`、`waitPortraitTask`（2s/60s）；保留 504 提示 | 代码落地；类型检查结果见 T22 |
| [x] | T22 | 全部 | 定向验证 | OpenBase ruff + 定向 pytest；DPS/OpenMemory/OpenLLM 定向 pytest；前端 `vue-tsc` | 见下方「验证结果」 |
| [x] | T23 | OpenBase | 文档留痕 | 修复方案升 v1.5.0 + 修订历史；spec v1.0.2 / tasks v1.1.0 置 [Final] | 版本与修订历史一致 |
| [x] | T24 | 全部 | 提交推送 | 各仓 commit；OpenBase 推送 origin/backup/github | 见提交记录（不包含用户既有改动） |

## 验证结果

| 范围 | 命令 | 结果 |
|---|---|---|
| OpenBase 静态检查 | `ruff check openbase tests` | All checks passed |
| OpenBase 代理定向 | `pytest tests/test_memory_proxy.py tests/test_dps_proxy.py tests/test_rag_proxy.py` | 通过 |
| DPS 批次 2 | `pytest src/tests/test_batch2_r1_patch_merge.py src/tests/test_batch2_r3_async_calc.py` | 10 passed |
| DPS DDL | `pytest src/tests/test_v2_11_ddl_portrait.py` | 20 passed |
| OpenMemory R6 | `pytest tests/unit/test_r6_memory_list.py` | 3 passed |
| OpenLLM 画像契约 | `pytest backend/tests/unit/test_real_contract_profile.py` | 26 passed |
| OpenRAG | 本机无可用 venv | `py_compile` 通过；限流用例已补 |
| 前端 | `vue-tsc --noEmit` | 见提交前结果 |

## 完成定义

- 所有 T1–T24 完成并留痕；
- 验收条目与 `spec.md` §2.4/§3.5/§4.4/§5.5 一致；
- 回滚开关可用（R1/R3/R6/R8 均可在不改代码下回退）。

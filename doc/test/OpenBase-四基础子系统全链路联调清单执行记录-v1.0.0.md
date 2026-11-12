# OpenBase 四基础子系统全链路联调清单执行记录

| 项 | 内容 |
|---|---|
| **版本** | v1.0.0 |
| **状态** | [Review] |
| **依据** | 《OpenBase-四基础子系统全链路贯通审计报告-v1.0.0》§4；《批次 4 收尾规格》§4 |
| **执行时间** | 2026-11-12（Asia/Shanghai） |
| **执行方式** | 环境探测 + 契约级自动化证据 + 可复跑脚本（本机未启动任何子系统） |
| **作者** | 架构组 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-12 | 首版：八项联调清单环境探测、契约级证据映射、脚本结果与遗留项 | 架构组 |

---

## 1. 环境探测结论

对 `127.0.0.1` 常用端口逐一探测（`Test-NetConnection`）：

| 端口 | 预期服务 | 结果 |
|---|---|---|
| 8000 | OpenBase 门户 | 未监听 |
| 8010 | OpenRAG | 未监听 |
| 8020 | OpenMemory | 未监听 |
| 8030 | DPS | 未监听 |
| 8040 | 保留 | 未监听 |
| 5173 | openbase-ui 开发服务器 | 未监听 |
| 11434 | Ollama | 未监听 |

**结论**：本轮无法执行真实端到端联调，改以"契约级 pytest 证据 + 可复跑脚本"交付；脚本在环境就绪后可直接补跑。

---

## 2. 八项清单逐条结论

| # | 清单项 | 通过标准（审计 §4） | 契约级证据 | 本轮结论 |
|---|---|---|---|---|
| 1 | 上下文两轮 | 同 session 两轮，第 2 轮引用第 1 轮 | `OpenLLM/backend/tests/unit/test_context_policy.py`（四策略与 meta）；`tests/test_llm_proxy_context_policy.py`（门户透传/回显） | 契约级 PASS；端到端 BLOCKED |
| 2 | 记忆召回 | chat 后同 user 召回含本轮事实 | `tests/test_memory_proxy.py`（recall 转发、身份四头、上游错误透传） | 契约级 PASS；端到端 BLOCKED |
| 3 | 记忆 PATCH | 内容更新生效 | `openbase/modules/proxy/memory_proxy.py`（R4：`PATCH /memories/{memory_id}`，字段白名单）；`tests/test_memory_proxy.py` | 契约级 PASS；端到端 BLOCKED |
| 4 | 知识库上传/检索 | 文档 SUCCEEDED、检索命中带引用 | `tests/test_rag_proxy.py`（建库/上传/详情轮询/retrieve 转发与字段透传） | 契约级 PASS；端到端 BLOCKED |
| 5 | 知识库隔离 | 租户 B 查租户 A → 404 | `tests/test_rag_proxy_identity_policy.py`（上游 404 原样透传、身份头注入） | 契约级 PASS；端到端 BLOCKED |
| 6 | 画像计算/读取 | 计算后 GET 返回六维 + attributes | `tests/test_dps_proxy.py`（calculate、详情、超时与错误映射） | 契约级 PASS；端到端 BLOCKED |
| 7 | 画像双标签合并 | 两次写入后 GET 同时含 A、B | `DPS/src/tests/test_batch2_r1_patch_merge.py`（PATCH 深合并 / list 去重追加） | 契约级 PASS；端到端 BLOCKED |
| 8 | 缺租户头 | 400 `PARAM_TENANT_REQUIRED` | `tests/test_entry_tenant_guard.py`（当前入口租户守卫口径） | 部分满足：R5 生产 `enforce` 未上线，按当前实现记录 |

---

## 3. 可复跑脚本

**脚本**：`scripts/verify_full_chain_checklist.py`

```powershell
$env:OPENBASE_BASE_URL  = "http://127.0.0.1:8000"
$env:OPENBASE_TOKEN     = "<登录门户后的 JWT>"
$env:OPENBASE_TENANT_ID = "<租户 A>"
$env:OPENBASE_TENANT_ID_B = "<租户 B>"   # 第 5 项隔离检查需要
$env:OPENBASE_CHAT_MODEL  = "qwen2.5:0.5b" # 可选，缺省从 /llm-proxy/models 取首个可用
$env:OPENBASE_USER_ID     = "batch4-user"  # 可选，记忆召回用户
D:\venvs\openbase\Scripts\python.exe scripts/verify_full_chain_checklist.py --json
```

| 约定 | 说明 |
|---|---|
| 仅经门户 | 所有请求走 OpenBase `/api/v1/*-proxy/*`，不直连子系统 |
| 状态语义 | `PASS` 通过 / `FAIL` 断言失败 / `BLOCKED` 环境或前置缺失 / `PARTIAL` 与目标有差距（第 8 项） |
| 退出码 | 存在 `FAIL` → 1；否则 0（`BLOCKED` 不算失败） |
| 证据 | 默认写 `doc/test/evidence/full-chain/full-chain-<UTC>.json` |

### 3.1 本轮实际执行结果

本机未启动服务、未提供 Token，脚本输出：

```
汇总：BLOCKED=8
证据文件：doc/test/evidence/full-chain/full-chain-20261112T152101Z.json
EXIT=0
```

各项均因 `WinError 10061`（目标计算机积极拒绝）或前置数据缺失（第 3/5/7 项依赖前序成功）记 `BLOCKED`，符合"无环境不误报失败"的设计。

---

## 4. 遗留项

| 项 | 说明 | 承接 |
|---|---|---|
| 真实环境联调 | 八项端到端需 OpenBase/OpenLLM/OpenMemory/OpenRAG/DPS 与 Ollama 同时在线 | 环境就绪后按 §3 一键补跑 |
| R5 生产 enforce | 缺租户头当前非统一 400，第 8 项仅"部分满足" | 后续批次（本批次不含） |
| OpenRAG reindex 限流 | 60 秒内重复 reprocess 返回 429，经 `_raise_business_error` 统一转 503 | 已登记（批次 4 规格 §7） |

---

## 5. 复跑检查表

- [ ] 五个服务与 Ollama 均已启动并通过健康检查
- [ ] `OPENBASE_TOKEN` 为有效 JWT（未过期）
- [ ] 租户 A/B 各自存在可用知识库权限
- [ ] 脚本退出码为 0 且 `PASS=8`（第 8 项在 R5 上线前允许 `PARTIAL`）
- [ ] 证据 JSON 已归档至 `doc/test/evidence/full-chain/`

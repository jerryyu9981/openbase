# OpenBase 四基础子系统全链路联调清单执行记录

| 项 | 内容 |
|---|---|
| **版本** | v1.1.0 |
| **状态** | [Review] |
| **依据** | 《OpenBase-四基础子系统全链路贯通审计报告-v1.0.0》§4；《批次 4 收尾规格》§4 |
| **执行时间** | 2026-11-12（Asia/Shanghai） |
| **执行方式** | 契约级自动化证据 + 可复跑脚本；v1.1.0 补跑：本机五服务全栈启动后实测 |
| **作者** | 架构组 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-12 | 首版：八项联调清单环境探测、契约级证据映射、无环境 BLOCKED 结果与遗留项 | 架构组 |
| v1.1.0 | 2026-11-12 | 全栈启动后补跑：8 项实测（PASS=7、PARTIAL=1），补充身份头信任、租户 B 主体、既有画像等前置；更新脚本环境变量与证据 | 架构组 |

---

## 1. 环境

### 1.1 v1.0.0 探测（未启动）

`127.0.0.1` 的 8000/8010/8020/8030/5173/11434 均未监听，仅交付契约级证据。

### 1.2 v1.1.0 补跑环境（已启动）

通过 `scripts/service-orchestrator.ps1 -Action start` 启动全栈并健康检查通过：

| 服务 | 端口 | 状态 |
|---|---|---|
| OpenBase 门户 | 8000 | 健康 |
| OpenLLM 推理网关 | 8001 | 健康（模型 `qwen2.5:0.5b` 可用） |
| OpenRAG | 8010 | 健康 |
| OpenMemory | 8020 | 健康 |
| DPS | 8030 | 健康 |
| openbase-ui | 5173 | 健康 |
| PostgreSQL | 5432 | 健康 |

> 备注：Redis（6380）未启动；编排器按"仅 PG 为硬门禁"策略放行。

---

## 2. 八项清单实测结论

| # | 清单项 | 实测结果 | 证据 |
|---|---|---|---|
| 1 | 上下文两轮 | **PASS**：同 `session_id` 两轮均 200，响应含 `context_meta` | `session=batch4-54c592e232` |
| 2 | 记忆召回 | **PASS**：按 `user_id` 召回 1 条 | 召回数 1 |
| 3 | 记忆 PATCH | **PASS**：`PATCH /memory-proxy/memories/{id}` 200 | `memory=baed4288-...` |
| 4 | 知识库上传/检索 | **PASS**：建库 → 文本上传 → 状态 `completed` → `query/retrieve` 200 | `collection=7433a296-...`、`document=90017265-...` |
| 5 | 知识库租户隔离 | **PASS**：租户 B 主体查详情与跨库检索均 **404** | 同一 collection |
| 6 | 画像计算/读取 | **PASS**：既有人员 `tenant-1_1` 计算 200、详情 200 | `person=tenant-1_1` |
| 7 | 画像双标签合并 | **PASS**：两次 PATCH 后 `batch4_tags=["A","B"]` | 合并读回 |
| 8 | 缺租户头 | **PARTIAL**：缺省 `X-Tenant-ID` 写请求返回 200（期望 400） | R5 生产 `enforce` 未上线 |

**汇总：PASS=7、PARTIAL=1、FAIL=0；脚本退出码 0。**
证据文件：`doc/test/evidence/full-chain/full-chain-20261112T175716Z.json`。

---

## 3. 可复跑脚本

**脚本**：`scripts/verify_full_chain_checklist.py`

### 3.1 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `OPENBASE_TOKEN` | 是 | 租户 A 主体 JWT（如 `admin`） |
| `OPENBASE_TOKEN_B` | 第 5 项必需 | 租户 B 主体 JWT（隔离验证必须换主体，仅带 `X-Tenant-ID` 不生效） |
| `OPENBASE_TENANT_ID` | 否 | 默认租户 A 代码，如 `tenant-1` |
| `OPENBASE_TENANT_ID_B` | 否 | 租户 B 代码，如 `tenant-2` |
| `OPENBASE_PROXY_SOURCE` | 否 | 受信来源标识，默认 `openbase-orchestrator`（须在 `OPENBASE_TRUSTED_PROXY_SOURCES` 内） |
| `OPENBASE_CHAT_MODEL` | 否 | 默认从 `/llm-proxy/models` 取首个可用模型 |
| `OPENBASE_USER_ID` | 否 | 记忆召回用户，默认 `batch4-user` |
| `OPENBASE_PERSON_ID` | 否 | 画像人员，缺省取既有画像列表首条 |

### 3.2 一键执行（PowerShell 5）

```powershell
$login  = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/auth/login' -Method Post `
  -ContentType 'application/json' -Body '{"username":"admin","password":"admin123"}'
$loginB = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/auth/login' -Method Post `
  -ContentType 'application/json' -Body '{"username":"batch4-t2-user","password":"Batch4!2026"}'
$env:OPENBASE_BASE_URL='http://127.0.0.1:8000'
$env:OPENBASE_TOKEN=$login.access_token
$env:OPENBASE_TOKEN_B=$loginB.access_token
$env:OPENBASE_TENANT_ID='tenant-1'
$env:OPENBASE_TENANT_ID_B='tenant-2'
$env:OPENBASE_USER_ID='1'
$env:OPENBASE_CHAT_MODEL='qwen2.5:0.5b'
$env:OPENBASE_PROXY_SOURCE='openbase-orchestrator'
D:\venvs\openbase\Scripts\python.exe scripts\verify_full_chain_checklist.py
```

| 约定 | 说明 |
|---|---|
| 仅经门户 | 所有请求走 OpenBase `/api/v1/*-proxy/*`，不直连子系统 |
| 状态语义 | `PASS` / `FAIL` / `BLOCKED`（环境或前置缺失）/ `PARTIAL`（第 8 项，与目标有差距） |
| 退出码 | 存在 `FAIL` → 1；否则 0 |
| 证据 | 默认写 `doc/test/evidence/full-chain/full-chain-<UTC>.json` |

### 3.3 补跑中发现并已适配的契约细节

1. **身份头信任**：R5 强校验期，非受信来源携带 `X-Tenant-ID/X-Org-ID` 会被拒绝（403 `PERM_UNTRUSTED_IDENTITY_HEADER`）；脚本以 `X-Proxy-Source: openbase-orchestrator`（受信来源）发起。
2. **llm-proxy 不带租户头**：出站租户由 API Key 归属决定；强带主体租户（`tenant_id=1`）会与 Key 归属 `tenant-1` 不一致触发 OpenLLM D20 → 403。
3. **隔离必须换主体**：门户按 JWT 主体租户出站，仅改入站 `X-Tenant-ID` 不改变归属；需租户 B 用户令牌（本次创建 `batch4-t2-user`，`tenant_id=2`）才能验证 404。
4. **画像计算需既有人员**：`portraits/calculate` 对不存在 `person_id` 返回 404「人员不存在」；脚本缺省取既有画像首条。
5. **画像 PATCH 合并生效**：两次 `{"business":{"attributes":{"batch4_tags":[tag]}}}` 后读回 `["A","B"]`，与批次 2 R1 语义一致。

---

## 4. 遗留项

| 项 | 说明 | 承接 |
|---|---|---|
| R5 生产 enforce | 缺租户头当前非统一 400（第 8 项 PARTIAL） | 后续批次（本批次不含） |
| Redis 未启动 | 6380 未监听，编排器放行；影响缓存类能力，不影响本次八项 | 环境补齐 |
| OpenRAG reindex 限流 | 60 秒内重复 reprocess 返回 429（经统一错误映射为 503） | 已登记（批次 4 规格 §7） |
| 联调测试数据 | 知识库 `batch4-verify-*`、画像 `batch4_tags`、用户 `batch4-t2-user` | 由环境清理流程处理 |

---

## 5. 复跑检查表

- [x] 五个服务与 PostgreSQL 已启动并通过健康检查
- [x] `OPENBASE_TOKEN` 与 `OPENBASE_TOKEN_B` 均为有效 JWT
- [x] 租户 A/B 主体与知识库权限可用
- [x] 脚本退出码为 0（PASS=7、PARTIAL=1）
- [x] 证据 JSON 已归档至 `doc/test/evidence/full-chain/`

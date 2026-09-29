# llm_proxy → OpenLLM 链路实测证据（2026-09-30）

| 项 | 内容 |
|----|------|
| **证据编号** | `E-LLMPROXY-20260930` |
| **对应待验项** | D-1410-03 遗留「待实测」第 2 项：**`llm_proxy` → OpenLLM 链路**（A-1410-01 落地的 AI 复核辅助通道） |
| **执行人** | DO-OpenBase-Dev（部署验证）／AA-OpenBase-Dev |
| **执行日期** | 2026-09-30 |
| **取证方式** | **端到端真实 HTTP 调用**（起本仓与被调方服务，逐项发请求并记录原始响应） |
| **结论** | ✅ **链路实测通过**（含一次真实推理完成）；另发现 **4 项环境／配置问题**（F1~F4，不属链路缺陷） |

---

## 1. 环境与前置

| 组件 | 配置 | 实测可达性 |
|------|------|:----------:|
| OpenBase（本仓） | `uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000` | ✅ 启动成功（`Application startup complete`） |
| OpenLLM（被调方） | `uvicorn main:app --host 127.0.0.1 --port 8001`（与 `settings.llm_upstream_base` 一致） | ✅ 启动成功（`Uvicorn running on http://127.0.0.1:8001`） |
| 共享 PostgreSQL | `192.168.0.151:5432` | ✅ 可达 |
| 共享 Redis | `192.168.0.151:6380` | ✅ 可达 |
| 本机 Ollama | `127.0.0.1:11434` | ❌ **不可达**（未启动） |

> 链路参数：`llm_upstream_base=http://127.0.0.1:8001`；本仓持有网关密钥经 `Authorization: Bearer` 注入；OpenLLM 侧 `TRUSTED_PROXY_SOURCES=openbase-llm-proxy`。

---

## 2. 实测结果（原始响应摘要）

| # | 步骤 | 请求 | 结果 | 判据 |
|:-:|------|------|:----:|------|
| ① | 本仓存活 | `GET /health` | **200** `{"status":"ok"}` | 服务就绪 |
| ② | 匿名访问链路 | `GET /api/v1/llm-proxy/models`（无凭据） | **401** `{"code":"AUTH_401","message":"missing bearer token"}` | ✅ JWT 门禁 fail-closed |
| ③ | 裸身份头（无可信来源） | 同上 ＋ `X-User-ID/X-Tenant-ID/X-Org-ID/X-User-Role` | **403** `{"code":"PERM_UNTRUSTED_IDENTITY_HEADER","message":"identity headers from untrusted source"}` | ✅ **防伪造生效** |
| ④ | 登录 | `POST /api/v1/auth/login`（`admin`） | **200**（`access_token` 长度 261，前缀 `eyJhbGciOiJI`） | 取得调用凭据 |
| ⑤ | **链路·模型列表（关键判据）** | `GET /api/v1/llm-proxy/models` ＋ `Bearer` | **200** `{"code":0,"message":"success","data":{"models":[{"id":"gpt-4","owned_by":"DeepSeek2"},{"id":"deepseek-v4-flash","owned_by":"DeepSeek"}]}}` | ✅ **链路 + 网关密钥 + 可信来源 三项打通**（返回 **OpenLLM 真实注册表**，非本仓 mock） |
| ⑥ | 链路·推理（错误模型名） | `POST /api/v1/llm-proxy/chat`（`model=qwen3:0.6b`） | **404** `{"code":2001,"message":"模型 'qwen3:0.6b' 不存在"}` | ✅ 上游**真实语义**回传（证明请求确实到达 OpenLLM） |
| ⑦ | **链路·推理（真实模型，修正后）** | `POST /api/v1/llm-proxy/chat`（`model=deepseek-v4-flash`） | **200** `{"code":0,"message":"success","data":{"mode":"openai","pipeline":["llm"],"model":"deepseek-v4-flash","usage":{"prompt_tokens":87,"completion_tokens":16,"total_tokens":103},"routing_trace":{…}}}` | ✅ **完成一次真实推理**（含 token 计量与组件路由轨迹） |
| ⑧ | 备选模型可用性 | `POST /api/v1/llm-proxy/chat`（`model=gpt-4`） | **500** `{"code":5001,"message":"模型服务暂时不可用"}` | ⚠ 该模型上游 provider 不可用（**模型级**问题，非链路问题） |

**原始响应留存**：⑤／⑦ 的完整响应体包含 OpenLLM 的 `request_id`（如 `openllm-f7cd116d7ec24d9e84c23a03`）、`routing_trace.components`（`need_memory:false`／`need_rag:false`／`reason:"openai"`）、`context_metrics`（`segment_tokens` 分段计量与预算字段）。

---

## 3. 结论

> **本版 `llm_proxy` → OpenLLM 链路：实测通过。** 依据：⑤ 返回 **200 ＋ OpenLLM 真实模型注册表**，⑦ 返回 **200 ＋ 真实推理结果（含 usage 与 routing_trace）**；② ③ 证明门禁与防伪造在链路前端生效。
> **A-1410-01 的落地前提（"复用 OpenLLM 通道的 LLM 能力"）获得实测支撑**，本版 AI 复核辅助**无需 DPS 新能力、无需本仓新增后端**（AD-3 结论成立）。

---

## 4. 附带发现（F1~F4，**如实登记，不属链路缺陷**）

| # | 发现 | 证据 | 影响与处置 |
|:-:|------|------|------------|
| **F1** | **OpenLLM 运行时版本号与已交付 tag 不一致**：`GET :8001/health` 报 `"version":"2.14.3"`、`app_version:"2.14.3"`，而本版已按 **v2.14.4** 交付该仓改动 | `/health` 响应原文（见上）；`.env` 中 `APP_VERSION=2.14.3` **覆盖**了代码默认值 `2.14.4` | **登记**：v2.14.4 的**代码改动已生效**（`sql_echo:false` 与 `uptime_seconds` 均在本实例 `/health` 中出现，即新字段已上线），但**版本字符串被 `.env` 钉住** ⇒ 版本口径漂移。建议 OpenLLM 侧同步 `.env`；属该仓收尾项，**不阻塞本仓** |
| **F2** | **`DEFAULT_LLM_MODEL` 与 OpenLLM 注册表漂移**：OpenLLM `.env` 配 `DEFAULT_LLM_MODEL=qwen3:0.6b`，但注册表仅 `gpt-4`／`deepseek-v4-flash` ⇒ 调用该默认模型必 **404 2001** | 实测 ⑥ | **登记**（属 OpenLLM 侧配置漂移，与 F-1 历史修复同类复发）；**本版 AI 复核辅助须显式传真实模型名**（不得依赖默认模型） |
| **F3** | `gpt-4` 上游 provider 不可用（500 5001） | 实测 ⑧ | 环境性；**Step 4 做 AI 复核链路用例时须选可用模型**（建议 `deepseek-v4-flash`） |
| **F4** | **OpenBase 启动时 DB 初始化失败并降级内存**：日志 `"message": "fallback: memory demo user seeded (admin/admin123)"` | 启动日志 | 本次链路验证**不受影响**（`llm_proxy` 不依赖本仓 DB）；但**属部署前置**：Step 3／4 前须核实本仓 DB 初始化失败原因（共享库 schema／权限），否则请求侧功能会降级 |

---

## 5. 复原与清理

| 项 | 处置 |
|----|------|
| 测试实例 | OpenBase(8000) 与 OpenLLM(8001) **均已停止**，无残留进程占用 |
| 凭据 | 未落盘任何密钥／令牌原文；仅记录长度与前缀 |
| 脚本 | 探针脚本为临时脚本，未入仓 |

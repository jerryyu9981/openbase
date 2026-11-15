# OpenBase 全服务端到端走查与上生产就绪修复 Spec

- 版本：v1.2.0
- 状态：[Approved]（已批准并实施，验证通过）
- 适用环境：Dev（本机 127.0.0.1，共享基础设施 192.168.0.151）
- 作者：AI 编码代理（承接 2026-11-15 端到端走查）
- 批准人：项目负责人
- 修订历史：
  - v1.0.0（2026-11-15）：首版。汇总 7 服务拉起与三轮全页面/全功能走查结果，固化 2 项 P1 阻断缺陷修复设计、2 项 P2 遗留登记。
  - v1.1.0（2026-11-15）：批准并实施 DEF-01/DEF-02 修复；补测 7 条、ruff 0 错误、定向测试 37 条全通过；重启 openbase 后运行时验收与浏览器复走查全 PASS；追加 §8 变更记录。
  - v1.2.0（2026-11-15）：按用户要求收敛两项 P2 遗留——DEF-03（记忆列表筛选计数）与 DEF-04（通用代理 RAG/Memory 上游凭据）；补测 5 条并更新 1 条既有断言，ruff 0 错误，代理相关 68 条回归全通过，运行时与浏览器复验 PASS；追加 §9。

---

## 1. 背景与目标

用户要求：拉起 OpenBase 统一前端及后端全部 5 个服务（openllm/openrag/openmemory/oidc-idp/dps）+ openbase + frontend，完成全页面全功能端到端走查，判定是否可上生产。

本 Spec 目标：
1. 记录当前服务与走查事实（证据化）。
2. 对走查发现的缺陷做根因定性与最小修复设计。
3. 定义修复后的验收标准与复走查范围。
4. 明确不修复项（遗留登记），避免范围膨胀。

---

## 2. 当前事实（已实测，2026-11-15）

### 2.1 服务状态

| 端口 | 服务 | 状态 |
|---|---|---|
| 8000 | openbase | LISTEN |
| 8001 | openllm | LISTEN |
| 8010 | openrag | LISTEN |
| 8020 | openmemory | LISTEN |
| 8030 | dps | LISTEN |
| 8090 | oidc-idp | LISTEN |
| 5173 | 统一前端（vite） | LISTEN |

编排器 `scripts/service-orchestrator.ps1 -Action startcheck` 结果：27 PASS / 0 FAIL / 0 SKIP；后台 `-Action monitor -Interval 15 -MaxRestarts 3` 维持自愈。

### 2.2 走查结论（三轮）

| 范围 | 结论 |
|---|---|
| 登录 / 退出登录 / 未登录重定向 | PASS |
| 仪表盘（模块数 5、用户 115、24h 调用量 2） | PASS |
| OpenLLM 模型页（5 个模型全部在线） | PASS |
| 知识库列表（8 条集合） | PASS |
| 记忆列表（31 条）/ 记忆详情 | PASS |
| 记忆搜索（"咖啡" 31→1 条结果） | PASS（列表页计数不一致，见 DEF-03） |
| 画像列表（18 条）/ 画像详情（tenant-1_1，版本 78） | PASS |
| 服务发现与编排（4 实例健康） | PASS |
| 聚合网关测试页：页面渲染 | PASS |
| 聚合网关测试页：执行聚合 | **FAIL**（DEF-01） |
| 网关四系统连通性检测 | **FAIL**：dps 误报不可达（DEF-02） |
| 前端 console error / 错误 toast / 404 | 无异常 |

---

## 3. 缺陷清单与根因

### DEF-01（P1，100% 复现）聚合网关执行失败

- 现象：默认两步执行返回
  `upstream openllm/openrag unreachable: Request URL is missing an 'http://' or 'https://' protocol.`
  结果 `{"model_total": null, "kb_total": null}`。
- 根因：[aggregate.py](file:///d:/Trae%20CN/myproject/Dev/OpenBase/openbase/modules/gateway/aggregate.py#L48-L48)、[aggregate.py](file:///d:/Trae%20CN/myproject/Dev/OpenBase/openbase/modules/gateway/aggregate.py#L107-L107) 使用**相对路径** `"/api/v1/proxy"` 拼 URL；[router.py](file:///d:/Trae%20CN/myproject/Dev/OpenBase/openbase/modules/gateway/router.py#L184-L187) 未传绝对地址。httpx 对相对 URL 抛 `UnsupportedProtocol`（`HTTPError` 子类），被第 66 行捕获后转成上述错误文案。
- 附因：自调用 `/api/v1/proxy` 需携带调用方 JWT，否则 401；当前设计未传递该头。
- 附因（默认配置错误，已实测）：
  - `openllm` 正确路径为 `/openllm/v1/models`（`/models` 经通用代理 404）；
  - `openrag` 的 `/kb/list` 不存在（原生为 `/api/v1/collections`，且通用代理缺 `X-API-Key` → 401）；
  - `dps` 可用路径为 `/health/liveness`。

### DEF-02（P1）DPS 连通性误报不可达

- 现象：`GET /api/v1/gateway/ping` 中 dps `reachable=false`，其余三系统正常（~300ms）。
- 根因：[router.py](file:///d:/Trae%20CN/myproject/Dev/OpenBase/openbase/modules/gateway/router.py#L167-L167) 硬编码 `GET http://host:port/health`；实测 DPS `/health` = 404、`/health/liveness` = 200（DPS 仅提供 `/health/liveness|readiness|startup` 与 `/healthz`）。

### DEF-03（P2，不阻断）记忆列表关键词筛选后分页总数不一致

- 现象：输入关键词后表格 31→1 行，分页 total 仍显示 31。
- 根因：[MemoryList.vue](file:///d:/Trae%20CN/myproject/Dev/OpenBase/openbase-ui/src/modules/memory/pages/MemoryList.vue#L179-L190) 关键词为**当前页客户端过滤**，`total` 仍用服务端总数，且未重置页码。
- 处置：本轮登记遗留，不修改（见 §6）。

### DEF-04（P2，不阻断）通用代理对 openrag/openmemory 返回 401

- 现象：`/api/v1/proxy/openrag/api/v1/collections`、`/api/v1/proxy/openmemory/api/v1/memories` 均 401；专用代理 `/api/v1/rag-proxy/collections`、`/api/v1/memory-proxy/memories` 均 200。
- 根因：通用代理仅对 openllm 注入上游凭据（API Key），openrag 需 `X-API-Key`、openmemory 另有认证；这些由专用代理模块承担。
- 处置：本轮登记遗留；聚合页默认步骤改用已验证可用的 openllm + dps，openrag/openmemory 在聚合中会以 `errors` 明细呈现（符合 `return_errors` 设计）。

---

## 4. 变更设计（最小改动）

### 4.1 后端

文件 `openbase/modules/gateway/aggregate.py`
1. `_fetch_step(step, proxy_base, semaphore, forward_headers: dict[str, str] | None = None)`：新增透传头参数；`client.request(method, url, headers=dict(forward_headers or {}))`。
2. `execute_aggregate(request, proxy_base="http://127.0.0.1:8000/api/v1/proxy", forward_headers=None)`：默认值改为绝对地址（兜底）；向 `_fetch_step` 透传 `forward_headers`。

文件 `openbase/modules/gateway/router.py`
1. 引入 `Request`；聚合路由签名改为 `async def aggregate(request: Request, payload: AggregateRequest)`：
   - `proxy_base = str(request.base_url).rstrip("/") + "/api/v1/proxy"`
   - `authorization = request.headers.get("authorization")`
   - `forward_headers = {"Authorization": authorization} if authorization else {}`
   - `execute_aggregate(payload.model_dump(), proxy_base=proxy_base, forward_headers=forward_headers)`
2. 新增 `_HEALTH_PATHS = {"dps": ("/health/liveness", "/health")}` 与 `_probe_health(target)`：先取 `target.meta["health_path"]`，再按系统候选链依次探测，任一 2xx 即可达；`gateway_ping` 改调用该函数（替换第 167 行硬编码）。

### 4.2 前端

文件 `openbase-ui/src/pages/platform/observability/GatewayAggregateView.vue`
- 默认步骤改为：`{id:'models', system:'openllm', path:'/openllm/v1/models'}`、`{id:'dps', system:'dps', path:'/health/liveness'}`。
- 默认映射改为：`models → ${models.data.models}`、`dps_status → ${dps.data.status}`。

### 4.3 不改动项
- 不新增配置项、不改 `PROXY_SYSTEMS`、不改专用代理（rag/memory）。
- 不改动 DEF-03 / DEF-04。

---

## 5. 测试与验收标准

### 5.1 新增/修改测试（TDD，先红后绿）
`tests/test_gateway.py`
- 聚合透传：`execute_aggregate(req, proxy_base="http://test/api/v1/proxy", forward_headers={"Authorization":"Bearer t"})` → Fake Client 记录的 URL 为绝对地址且携带该头。
- 健康路径回落：`_probe_health` 对 `/health` 404、`/health/liveness` 200 时判定可达；全失败判定不可达。

`tests/test_gateway_api.py`
- `POST /api/v1/gateway/aggregate` 在 monkeypatch `execute_aggregate` 时，断言收到的 `proxy_base` 以 `http` 开头且 `forward_headers` 带调用方 Authorization。
- `GET /api/v1/gateway/ping`：mock 上游 `/health` 404、`/health/liveness` 200，断言 dps `reachable=true`。

覆盖率：新增/修改代码行覆盖率 ≥ 90%（定向 `--cov=openbase.modules.gateway`）。

### 5.2 静态与回归
```bash
python -m ruff check openbase tests
python -m pytest tests/test_gateway.py tests/test_gateway_api.py -q
```

### 5.3 运行时验收（服务已运行，改后需重启 openbase 与前端）
1. `POST /api/v1/gateway/aggregate`（默认两步，带 admin JWT）→ `data.errors == []`，`data.result.dps_status == "healthy"`。
2. `GET /api/v1/gateway/ping` → 四系统 `reachable` 全为 true。
3. 前端 `/platform/observability/gateway-test` 点击「执行聚合」→ 结果 JSON 可见、无 `agg-error`。
4. 复走查：登录/仪表盘/OpenLLM/知识库/记忆/画像/网关/服务发现/退出登录，无 console error、无错误 toast、无 404。

### 5.4 交付纪律
- 文档留痕：本 Spec + 任务清单 + 变更记录（版本与修订历史）。
- 提交并推送 origin / backup / github 三远程。

---

## 6. 风险、假设与遗留

风险
- 自调用代理增加一次本机 HTTP 往返（毫秒级），仅在聚合链路生效。
- 若部署在反向代理之后，`request.base_url` 依赖 `Host`/`X-Forwarded-*` 可从应用侧回连；若不可回连，可用 `OPENBASE_*` 兜底改走绝对 self base（后续如需再引入配置项）。

假设
- 通用代理已注入 openllm 凭据与身份头（已实测 200）。
- 前端经 vite 代理访问 8000，`Host` 为可回连地址。

遗留（P2，已于 v1.2.0 收敛，见 §9）
- DEF-03 记忆列表关键词筛选分页计数不一致 —— 已修复。
- DEF-04 通用代理对 openrag/openmemory 401 —— 已修复（凭据注入与专用代理同源）。

---

## 7. 人工裁定结果（2026-11-15）

1. 批准按 §4 修复 DEF-01、DEF-02。
2. 同意 DEF-03、DEF-04 作为 P2 遗留登记、本轮不修。

---

## 8. 实施结果与变更记录（v1.1.0）

### 8.1 代码变更

| 文件 | 变更 |
|---|---|
| `openbase/modules/gateway/aggregate.py` | `_fetch_step`/`execute_aggregate` 新增 `forward_headers`；新增 `DEFAULT_PROXY_BASE` 绝对地址兜底；透传 Authorization |
| `openbase/modules/gateway/router.py` | 聚合路由改收 `Request`，以 `request.base_url` 组绝对 proxy_base 并透传 Authorization；新增 `_HEALTH_PATHS`/`_probe_health`（meta > 系统候选链），`gateway_ping` 改用之 |
| `openbase-ui/src/pages/platform/observability/GatewayAggregateView.vue` | 默认步骤改为 openllm `/openllm/v1/models` + dps `/health/liveness`；默认映射改为 `${models.data.data.models}` 与 `${dps.data.status}` |
| `tests/test_gateway.py` | 新增 4 条：绝对 URL + 转发头、DPS liveness 回落、meta 优先、全失败 |
| `tests/test_gateway_api.py` | 新增 2 条：路由透传断言、ping DPS 可达回归 |

### 8.2 验证证据

- `ruff check openbase tests`：All checks passed（0 错误）。
- `pytest tests/test_gateway.py tests/test_gateway_api.py`：37 条全通过。
- 定向覆盖率：`router.py` 97%、`schemas.py` 100%、`registry.py` 93%；新增/修改行均被覆盖（aggregate 剩余未覆盖为既有超时/错误分支）。
- 运行时（重启 openbase 后）：
  - `POST /api/v1/gateway/aggregate`（openllm + dps）→ `errors=0`、`dps_status=healthy`、模型数组 5 条。
  - `GET /api/v1/gateway/ping` → openllm/openrag/openmemory/dps 全部 `reachable=true`（266~312ms）。
- 浏览器复走查：
  - 聚合网关测试页执行成功，结果 JSON 含 5 个模型与 `dps_status: healthy`，无「部分步骤失败」。
  - 服务发现与编排：4 实例全部「健康」，连续失败 0。
  - 仪表盘/OpenLLM 模型/知识库/记忆/画像：均正常渲染且有数据（5/5/8/31/18 条），无错误提示。

### 8.3 残留风险与遗留

- 自调用代理增加一次本机往返（毫秒级），仅聚合链路。
- 反向代理部署下依赖 `Host`/`X-Forwarded-*` 可回连；不可回连时后续可引入 self base 配置项。
- DEF-03（记忆列表关键词筛选分页计数）与 DEF-04（通用代理对 openrag/openmemory 401）维持 P2 遗留（v1.2.0 已收敛，见 §9）。

---

## 9. P2 收敛记录（v1.2.0）

### 9.1 DEF-03 记忆列表筛选计数

- 文件：`openbase-ui/src/modules/memory/pages/MemoryList.vue`
- 变更：
  1. 记忆类型改为**服务端过滤**（`memory_type` 查询参数），total 与结果一致；
  2. 关键词（当前页内过滤）激活时，分页总数改用 `filtered.length`（`displayTotal`），并固定展示过滤结果；
  3. 关键词变化自动回到第 1 页；输入框提示明确「当前页」；清空触发重载。
- 验证：浏览器实测初始「共 31 条」→ 输入「咖啡」后「共 1 条」且仅 1 行 → 清空恢复 31 条。

### 9.2 DEF-04 通用代理凭据补齐

- 文件：`openbase/modules/proxy/__init__.py`
- 变更：`_inject_upstream_credentials(system, headers, request=None, *, is_service_key=False)`
  - openrag → `X-API-Key: settings.rag_api_key`；
  - openmemory → `X-API-Key: settings.memory_api_key` + 透传调用方原 JWT（双层认证；服务 Key 通道不构造 Authorization，复用 memory_proxy 的 `_original_bearer_token`）；
  - openllm / dps 行为不变。
- 测试：`tests/test_proxy_outbound_matrix.py` 新增 5 条；`tests/test_proxy_target_system_v190.py` 更新凭据矩阵断言。
- 验证：`/api/v1/proxy/openrag/api/v1/collections` 与 `/api/v1/proxy/openmemory/api/v1/memories?limit=1` 均由 401 → **200**；聚合编排（openrag+openmemory+dps）`errors=0`。
- 回归：`ruff` 0 错误；代理相关 68 条测试全通过。

### 9.3 残留说明

- 关键词过滤范围仍为**当前页**（OpenMemory 原生列表未提供内容全文检索参数），UI 已明示；跨页全文检索应使用「记忆搜索」（语义检索）页面。

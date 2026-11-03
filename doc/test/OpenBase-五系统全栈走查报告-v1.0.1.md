# OpenBase 五系统全栈走查报告

## 文档元信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | TEST-WALK-ALL-001 |
| 文档版本 | v1.0.1 |
| 文档状态 | [Review] |
| 适用环境 | 本机 Windows 原生进程（无 Docker），共享设施 `192.168.0.151`（PG 5432 / Redis 6380 / Qdrant 6333 / Neo4j 7687 / MinIO 9000） |
| 走查执行 | 2026-11-03 23:06 ~ 23:56（本机时间） |
| 走查范围 | OpenBase 8000、OpenLLM 8001、OpenRAG 8010、OpenMemory 8020、DPS 8030、OIDC-IdP 8090、统一前端 5173 |
| 执行方式 | 后端：页面探测 + OpenAPI 枚举 + 只读 GET 全量执行；前端：Playwright 逐页 E2E（含非破坏性交互） |
| 上游依据 | `OpenBase-四系统APIKey优化生产窗口执行单与回滚方案-v1.0.5.md` §13、`OpenBase-生产侧硬门禁待办清单与回执-XR-OPS-08-v1.0.1.md` |
| 关联历史 | `OpenBase-全栈功能走查报告-v1.0.0.md`、`OpenBase-前端全页面走查报告-v1.2.1.md` |

> 本报告为**只读走查**记录：仅执行 GET / 页面访问；含路径参数的端点在 OpenAPI 枚举后跳过；写操作、删除、审批、发布类端点一律未调用；前端仅点击查询/刷新/切换等非破坏性控件。

## 1. 走查口径与判定规则

| 维度 | 口径 |
| --- | --- |
| 页面 | 后端服务页面探针 + 前端统一入口 77 个路由页 |
| 功能 | 按 OpenAPI `paths` 统计全部方法，仅执行无路径参数的 `GET`；模板路径（含 `{param}`）记录为「跳过」 |
| 认证 | OpenBase 用 `admin` 账号登录换取 Bearer Token 后走查读接口；OpenMemory 使用服务 API Key；DPS 保持 fail-closed 不额外注入凭据 |
| 判定 | `2xx` = 通过；`401/403` = 门禁生效（需区分「应有门禁」与「配置缺失」）；`400/422` = 参数校验生效；`5xx` 或超时 = 缺陷；前端以「导航成功 + 无 render fallback + 无 console/page error」为 PASS |
| 不做 | 不写入、不修改、不删除任何业务数据；不启停外部依赖；不改动生产配置 |

## 2. 环境就绪与启动结果

启动命令（项目既定编排器，WMI 脱离会话启动，避免宿主会话回收子进程）：

```powershell
.\scripts\service-orchestrator.ps1 -Action start -PythonHome "D:\Trae CN\myproject\Dev\OpenBase\.venv-test\Scripts\python.exe"
```

数据面预检（启动前，`doc/test/evidence/ops/db-startup-probe-20261103-231*.json`）：

| 依赖 | 地址 | 结果 |
| --- | --- | --- |
| PostgreSQL 主用 | `192.168.0.151:5432` | ok（2213~6061ms） |
| PostgreSQL 备选 | `127.0.0.1:5432` | ok（4620~7894ms），实际 mode=primary |
| Redis | `192.168.0.151:6380` | ok |
| Qdrant | `192.168.0.151:6333` | ok |
| Neo4j | `192.168.0.151:7687` | ok |
| MinIO | `192.168.0.151:9000` | ok |

服务状态（走查时点实测）：

| 服务 | 端口 | 健康探针 | 冷启动耗时（编排器口径） | 结论 |
| --- | --- | --- | --- | --- |
| OpenBase | 8000 | `/health` 200 `{"status":"ok"}` | 227s 通过 | ✅ |
| OpenLLM | 8001 | `/health` 200（首轮 8s 探针超时，放宽后正常） | 219s 超时（进程存活，后自愈） | ⚠️ 慢启动 |
| OpenRAG | 8010 | `/api/v1/system/health` 200（`/health` 为 404） | 172s 通过 | ✅ |
| OpenMemory | 8020 | `/health` `/health/readiness` `/health/liveness` 全 200 | 163s 通过 | ✅ |
| DPS | 8030 | `/health/liveness` `/health/readiness` `/health/startup` `/healthz` 全 200 | 100s 探针超时（端口约 190s 就绪） | ⚠️ 慢启动 |
| OIDC-IdP | 8090 | `/health` 200、`/.well-known/openid-configuration` 200、`/jwks` 200 | 31s 通过 | ✅ |
| 统一前端 | 5173 | `/` 200（Vite dev，proxy → 8000） | 146s 探针超时（随后可访问） | ⚠️ 慢启动 |

> 环境限制：本机 PowerShell 单条命令延迟可达 30s 以上，且直接 `Start-Process`/`subprocess` 拉起的子进程会被宿主会话回收（日志 0 字节）；本次改由编排器 WMI 方式启动，服务可持续运行。

## 3. 页面走查

### 3.1 后端服务页面（OpenAPI 文档页与健康页）

| 服务 | `/` | `/docs` | `/redoc` | `/openapi.json` | 健康页 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| OpenBase | 404 | 200 | 200 | 200（`OpenBase v1.4.12`） | `/health` 200 | 无根路由，文档页正常 |
| OpenLLM | 200 | 200 | 200 | 200（293 paths） | `/health` 200（首轮超时） | 文档页正常 |
| OpenRAG | 404 | 200 | 200 | 200（98 paths） | `/api/v1/system/health` 200 | `/health` 404（健康路由挂在 `/api/v1` 前缀下） |
| OpenMemory | 401 | 200 | 401 | 200（31 paths） | `/health`、`/health/readiness`、`/health/liveness` 全 200 | **`/docs` 开放而 `/redoc` 受门禁**，口径不一致（见 D-3） |
| DPS | 401 | 401 | 401 | 401 | 四个健康路由全 200 | 默认 fail-closed，文档页亦被门禁 |
| OIDC-IdP | 404 | 404 | — | 200（7 paths） | `/health` 200 | 未开放 Swagger/ReDoc |

### 3.2 统一前端全页面 E2E（含交互）

工具：`openbase-ui/scripts/ui_e2e_all_services.mjs --interact`（Playwright Chromium，`OPENBASE_BASE_URL=http://localhost:5173`）。

| 模块 | 页面数 | PASS | FAIL |
| --- | --- | --- | --- |
| openbase（公共功能五域） | 44 | 44 | 0 |
| openllm | 11 | 10 | 1 |
| openrag | 2 | 2 | 0 |
| openmemory | 6 | 6 | 0 |
| dps | 14 | 14 | 0 |
| **合计** | **77** | **76** | **1** |

唯一 FAIL：

| 页面 | 现象 | 判定 |
| --- | --- | --- |
| `/openllm/models/comparison`（模型对比） | `[Vue Router warn]: No match found for location`，页面未注册路由 | 缺陷 D-2（侧栏入口指向不存在的路由） |

其余 76 页：导航成功、未重定向至 `/auth/login`、无渲染兜底、无 console error / pageerror，`api 失败 0 次`；交互型页面（API 密钥、服务发现、路由策略、熔断器、EdgeRouter、知识库控制台、记忆写入等）点击非破坏性控件后均无异常。

## 4. 后端 API 功能走查统计

| 服务 | paths | 操作数 | GET 操作 | 已执行 | 2xx | 门禁 401/403 | 模板跳过 | 其他 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OpenBase | 173 | 221 | 110 | 76 | 56 | 1 | 34 | 400×7、422×1、无响应×11 |
| OpenLLM | 293 | 368 | 198 | 117 | 19 | 95 | 81 | 400×1、503×1、无响应×1 |
| OpenRAG | 98 | 115 | 47 | 25 | 22 | 0 | 22 | 404×3（查询语义）、无响应×22 |
| OpenMemory | 31 | 37 | 19 | 11 | 5 | 6 | 8 | — |
| DPS | — | — | — | — | — | 401（全部） | — | `/openapi.json` 401，无法枚举 |
| OIDC-IdP | 7 | 7 | 5 | 5 | 3 | 1 | 0 | 422×1（缺参） |

口径说明：

- **OpenBase**：带 Bearer Token 后读接口 2xx 56 项（`/api/v1/auth/me`、密钥、角色契约、租户上下文、审计、字典、文件、通知、AI 应用、四个 proxy 等）；仅 `/api/v1/auth/revocations` 需要额外 API Key（`AUTH_API_KEY_INVALID`），属预期；7 个 400 与 1 个 422 均为必填参数校验生效；11 个无响应项为跨服务 proxy 或 OIDC 跳转（放宽超时后 10/11 可返回，见 D-4）。
- **OpenLLM**：95 个 401 为 JWT 门禁（`无法验证凭据`）——本服务未接受 OpenBase 签发的令牌，属跨系统令牌未打通（见 D-6）；`/api/v1/chat/models` 返回「缺少API密钥」；`/api/v1/local-models/gpu/stats/all` 返回 503（`pynvml` 未安装，GPU 监控不可用）；`/openllm/v1/health` 超时。
- **OpenRAG**：22 个 2xx 覆盖系统健康、统计、集合列表、文档、分块、检索等；3 个 404 为「文档/任务/查询不存在」的语义返回（非路由缺失）；22 个无响应为 SSE/长任务类端点，超时阈值内未返回。
- **OpenMemory**：带服务 API Key 后 5 个 2xx；6 个 401 为「缺少 Bearer Token」（组织、衰减配置、监控、会话、图谱总览、指标），属双鉴权设计；语义检索 `POST /api/v1/recall` 经 OpenBase `memory-proxy` 调用返回 500（见 D-1，核心缺陷）。
- **DPS**：未携带凭据时全部端点（含 `/openapi.json`、`/docs`）返回 401，符合「fail-closed」预期（编排器 checkall 亦按 401 判 PASS）；因此本次对 DPS 仅覆盖健康端点与前端 14 页 UI 走查。
- **OIDC-IdP**：`/authorize` 缺参 422、`/userinfo` 无令牌 401，均属参数校验/门禁生效；discovery 与 JWKS 正常。

## 5. 认证与门禁观察

| 场景 | 实际表现 | 判定 |
| --- | --- | --- |
| OpenBase 无 Token 读接口 | 70 个端点 `AUTH_401 missing bearer token` | 门禁生效 ✅ |
| OpenBase 有 Token | 56 个 2xx，仅 revocations 需 API Key | 正常 ✅ |
| OpenBase `/mcp/tools/list` | `invalid mcp credential (missing_credential)` | 门禁生效 ✅ |
| OpenLLM 全部业务读接口 | 95 个 `401 无法验证凭据`（OpenBase Token 不被接受） | 跨系统令牌未打通 ⚠️ |
| OpenMemory | API Key 覆盖大部分接口；组织/监控/会话/图谱需 Bearer JWT | 双鉴权，口径需在文档中明确 ⚠️ |
| DPS | 无凭据一律 401（含文档页） | fail-closed ✅ |
| OIDC-IdP | `/jwks`、discovery 开放，`/authorize` 需 client_id | 正常 ✅ |

## 6. 缺陷与风险清单

| 编号 | 级别 | 位置 | 现象 | 根因 / 证据 | 建议 |
| --- | --- | --- | --- | --- | --- |
| D-1 | P1 | OpenMemory `POST /api/v1/recall`（经 OpenBase `/api/v1/memory-proxy/memories`） | 500 `INTERNAL_ERROR`，上游 4.2~12.5s 后返回 500 | `AttributeError: 'AsyncQdrantClient' object has no attribute 'search'` → `VectorStoreError: Search failed` → `SearchError`（OpenMemory 日志 2026-11-03T15:39/15:49 UTC） | 升级/适配 qdrant-client 异步接口（`query_points`），并补回归用例 |
| D-2 | P2 | 前端 `/openllm/models/comparison` | 侧栏入口点击后 Vue Router 报 `No match found`，页面不可达 | 路由表未注册该路径（或菜单与路由不同步） | 注册路由或下线入口 |
| D-3 | P2 | OpenMemory `/docs` 与 `/redoc` | `/docs` 200、`/redoc` 401、`/` 401 | 文档页门禁白名单未一致 | 统一白名单口径 |
| D-4 | P2 | OpenBase 跨服务 proxy（memory/llm/rag/dps/gateway） | 10s 阈值内 11 个端点无响应；放宽到 60s 后 10 个返回 200（`gateway/ping` 22.6s、`llm-proxy/health` 7.3s） | 冷启动后上游首次调用慢 + proxy 默认超时偏紧 | 评估 proxy 超时与首调预热策略；`gateway/ping` 中 `openllm.reachable=false` 需复核 |
| D-5 | P3 | OpenBase `/api/v1/auth/me` | 首轮 8s 探针超时，复测 0.1s 200 | 启动后瞬时资源竞争 | 观察即可 |
| D-6 | P2 | OpenLLM 鉴权 | OpenBase Token 不被接受（95 个 401） | 两系统 JWT 签发/校验未统一（issuer/密钥不一致） | 与 F0-7 网关/IdP 口径对齐后复测 |
| D-7 | P3 | OpenLLM GPU | `/api/v1/local-models/gpu/stats/all` 503 | `pynvml` 未安装 | 安装或显式降级提示 |
| D-8 | P3 | OpenRAG 健康路由 | `/health` 404，仅 `/api/v1/system/health` 可用 | 健康路由挂载在 API 前缀下 | 文档标注或补根级别名 |
| D-9 | P3 | OpenMemory 冷启动 | 单次启动 136~280s，编排器 300s 门限内偶发超时 | 本机内存紧张（空闲物理内存约 1.1GB），CLIP/向量组件加载慢 | 与运维确认内存配额 |

### 6.1 缺陷处置状态（截至 2026-11-04）

逐项处置结果、验证证据与仍受生产环境阻塞的项，见 `OpenBase-五系统走查缺陷整改与残余风险处置报告-v1.0.0.md`。摘要：

| 编号 | 处置状态 | 说明 |
| --- | --- | --- |
| D-1 | 已修复并复测 | OpenMemory 双路径适配 `query_points`/`search`，`/api/v1/recall` 与 `memory-proxy` 均 200 |
| D-2 | 已修复并 E2E 通过 | 深链改为 12s 引导预算，`/openllm/models/comparison` PASS（openllm 11/11） |
| D-3 | 已修复并复测 | `/docs`、`/redoc`、`/openapi.json` 统一白名单，均 200 |
| D-4 | 复测通过 | warm 态 proxy 全 200，`gateway/ping` 1.02s，判定为冷启动抖动 |
| D-5 / D-9 | 观察项 | 启动期资源竞争与内存配额，非代码缺陷 |
| D-6 | 待生产口径对齐 | 跨系统 JWT 打通依赖 G-2/G-3 网关与 IdP 参数 |
| D-7 | 正确降级 | 无 GPU 环境返回 503 + 明确提示，不安装无效依赖 |
| D-8 | 已修复并复测 | OpenRAG 新增根 `/health` 轻量探针，200 |

## 7. 结论

1. **服务可用性**：五系统 + OIDC IdP + 统一前端全部可拉起并通过健康探针；OpenBase `/health`、OpenRAG `/api/v1/system/health`、OpenMemory 三级健康、DPS 四健康路由、OIDC discovery/JWKS 均为 200。
2. **页面可用性**：前端 77 页中 76 页 PASS，唯一 FAIL 为 `/openllm/models/comparison` 路由缺失；后端文档页除 DPS（fail-closed）与 OIDC（未开放）外均正常。
3. **功能可用性**：OpenBase 认证态读接口 56 项 2xx；OpenRAG 22 项 2xx；OpenMemory 5 项 2xx；OIDC 3 项 2xx；DPS 因 fail-closed 仅覆盖健康端点与 UI。
4. **必须修复**：D-1（记忆检索 500）为唯一 P1，直接影响「记忆搜索」功能闭环；其余为 P2/P3，列入整改。

## 8. 证据清单

| 证据 | 说明 |
| --- | --- |
| `xr08-walkthrough-auth-20261103-233910.json` | OpenBase（带 Token）+ OpenMemory（带 API Key）最终走查结果 |
| `xr08-walkthrough-selected2-20261103-232311.json` | OpenRAG / OpenMemory 首轮 / OIDC / DPS / OpenBase 免鉴权轮 |
| `xr08-walkthrough-live-20261103-230648.json` | OpenLLM 全量 GET 走查（117 项执行） |
| `xr08-ui-e2e-20261103.json` | 统一前端 77 页逐页 E2E（含交互与 API 调用记录） |
| `logs/service-orchestrator/orchestrator-20261103.log` | 启动/健康判定与冷启动耗时原始日志（不随文档提交） |

## 9. 风险、假设与约束

- 只读走查不覆盖写/改/删链路（如创建租户、写记忆、发布模板、审批），这些能力的通过需在**专用测试数据 + 可回滚窗口**内另行执行。
- 本机进程稳定性受宿主会话与内存影响：直接 `Start-Process` 拉起的子进程会被回收，须统一走 `service-orchestrator.ps1`（WMI 脱离会话）。
- `openllm` 和 `dps` 健康探针超时不代表服务不可用，本报告以「端口监听 + 端点实测」为准。
- 前端 E2E 通过 `localhost:5173` 访问（Vite 仅监听 IPv6 回环），后端 proxy 指向 `127.0.0.1:8000`。

## 10. 修订历史

| 版本 | 日期 | 修订人 | 修订摘要 | 状态 |
| --- | --- | --- | --- | --- |
| v1.0.1 | 2026-11-04 | AI 执行 / 待人工复核 | 补充 §6.1 缺陷处置状态（D-1/D-2/D-3/D-8 已修复复测，D-4 复测通过，D-6 待生产口径）；上游门禁单引用升版至 v1.0.1 | [Review] |
| v1.0.0 | 2026-11-03 | AI 执行 / 待人工复核 | 首次记录五系统 + 统一前端全栈只读走查：启动结果、页面探针、OpenAPI 全量 GET 统计、前端 77 页 E2E、9 项缺陷 | [Review] |

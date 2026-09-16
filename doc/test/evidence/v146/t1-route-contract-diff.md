# OpenBase v1.4.6 测试报告 · T1 契约层（路由映射表 diff）

| 项 | 内容 |
| --- | --- |
| 报告版本 | v1.0.0 |
| 状态 | [Draft] |
| 测试角色 | AT-OpenBase-Test（Step 4 测试 · 后端轨道 T1） |
| 生成时间 | 2026-09-15 22:00:41 |
| 被测版本 | v1.4.6（日志中心 + 模块开关增量） |
| 契约事实源 A | 进程内 `openbase.demo_app:app` OpenAPI（`app.openapi()`，FastAPI 0.139.2） |
| 契约事实源 B | 前端调用面 `openbase-ui/src/core/api/logs.ts`、`modules.ts`（`http` baseURL=/api/v1） |

> 命令：`python dump_openapi_v146.py`（导入 `openbase.demo_app:app` → `app.openapi()`）

## 1. 取证命令与原始摘要

```text
$ python dump_openapi_v146.py
database init failed, fallback to memory: connection was closed in the middle of operation
UserWarning: Duplicate Operation ID proxy_api_v1_proxy__system___path__patch ...
TOTAL PATHS: 123
TARGET PATHS: {"/api/v1/modules": ["GET"], "/api/v1/modules/{module_id}": ["GET", "PATCH"], "/api/v1/logs/search": ["GET"], "/api/v1/logs/facets": ["GET"], "/api/v1/logs/facets/presets": ["GET"], "/api/v1/logs/export": ["GET"]}
```

说明：导入期 `database init failed` 属本机环境现象（PG 连接在 `asyncio.run` 初始化循环中被关闭），应用按设计降级为内存演示用户；OpenAPI 生成不依赖 DB，不影响本项契约结论。

## 2. v1.4.6 端点存在性断言

| # | Method | Path | OpenAPI 是否存在 | operationId | 查询参数 | 路径参数 | 声明响应码 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | GET | `/api/v1/logs/search` | YES | `search_logs_api_v1_logs_search_get` | source,module,operation,result,operator,q,from,to,case_id,run_id,step_id,page,page_size | (none) | 200,422 |
| 2 | GET | `/api/v1/logs/facets` | YES | `facets_logs_api_v1_logs_facets_get` | source,module,operation,result,operator,q,from,to,case_id,run_id,step_id | (none) | 200,422 |
| 3 | GET | `/api/v1/logs/facets/presets` | YES | `facets_presets_api_v1_logs_facets_presets_get` | (none) | (none) | 200 |
| 4 | GET | `/api/v1/logs/export` | YES | `export_logs_api_v1_logs_export_get` | source,module,operation,result,operator,q,from,to,case_id,run_id,step_id,format | (none) | 200,422 |
| 5 | GET | `/api/v1/modules` | YES | `list_modules_api_v1_modules_get` | (none) | (none) | 200 |
| 6 | PATCH | `/api/v1/modules/{module_id}` | YES | `switch_module_api_v1_modules__module_id__patch` | (none) | module_id | 200,422 |

## 3. 路由映射表 diff（前端调用面 → OpenAPI）

| 前端调用 | 前端位置 | 前端 method+path | OpenAPI 对应 | 后端缺失参数 | 后端多出参数 | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| logsApi.search | `openbase-ui/src/core/api/logs.ts:123` | `GET /logs/search` | `GET /api/v1/logs/search` | - | - | PASS |
| logsApi.facets | `openbase-ui/src/core/api/logs.ts:128` | `GET /logs/facets` | `GET /api/v1/logs/facets` | - | - | PASS |
| logsApi.export | `openbase-ui/src/core/api/logs.ts:139` | `GET /logs/export` | `GET /api/v1/logs/export` | - | - | PASS |
| listModuleDefinitions | `openbase-ui/src/core/api/modules.ts:48` | `GET /modules` | `GET /api/v1/modules` | - | - | PASS |
| modulesWriteApi.switch | `openbase-ui/src/core/api/modules.ts:41` | `PATCH /modules/{moduleId}` | `PATCH /api/v1/modules/{module_id}` | - | - | PASS |

### 3.1 逐条说明

- `logsApi.search`（`openbase-ui/src/core/api/logs.ts:123`）：buildLogParams(93-110) 拼装 source/module/operation/result/operator/q/from/to/case_id/run_id/step_id；120-122 追加 page/page_size；page_size 前端 clamp 至 [1,100]（112-116） → 判定 **PASS**
- `logsApi.facets`（`openbase-ui/src/core/api/logs.ts:128`）：复用 buildLogParams（不追加 page/page_size） → 判定 **PASS**
- `logsApi.export`（`openbase-ui/src/core/api/logs.ts:139`）：buildLogParams + format（csv|json，138 行）；responseType=blob → 判定 **PASS**
- `listModuleDefinitions`（`openbase-ui/src/core/api/modules.ts:48`）：只读注册表；同契约亦见 core/api/auth.ts:65 modulesApi.list → 判定 **PASS**
- `modulesWriteApi.switch`（`openbase-ui/src/core/api/modules.ts:41`）：body = {status}（模块 ID 走路径参数，非查询参数） → 判定 **PASS**

## 4. 非漂移项（信息登记）

| 端点 | 说明 |
| --- | --- |
| `GET /api/v1/modules/{module_id}` | 后端提供模块详情（GET），前端调用面未使用（模块页仅用 list + patch）→ 后端额外能力，非漂移 |
| `GET /api/v1/logs/facets/presets` | 路径模板占位符命名：前端为 JS 模板字面量 `${moduleId}`（modules.ts:41），后端为 `{module_id}`（FastAPI 路径参数）。占位符名不参与 HTTP 报文，仅影响 REST 文档可读性 → 非契约漂移，本报告按「占位符归一化」后比对（两者归一化模板同为 `/api/v1/modules/{}`） |
| `GET /api/v1/logs/facets/presets` | GET /api/v1/logs/facets/presets 在 OpenAPI 中存在且受权 log:read，但 openbase-ui/src 全量检索 `presets` 零命中（前端无调用方）→ 后端能力先行、前端未接线（非契约漂移） |

## 5. 漂移判定

- 未发现 404 类（前端调用的端点/方法在 OpenAPI 中缺失）与 422 类（查询参数名不一致）契约漂移；v1.4.6 五个端点在 OpenAPI 中全部存在，前端所有查询/路径/请求体参数名与后端 schema 完全一致。

**T1 结论：PASS**

## 6. 备注（受测范围边界）

- OpenAPI 的 `security` 为空（项目采用自定义 AuthMiddleware + `require_permission` 门禁，不走 FastAPI SecurityScheme），故权限红线不在 T1 从 OpenAPI 判定，而在 T2/T3 以真实请求状态码验证。
- `page_size` 后端 `le=100`（schema 上限）与前端 `clampPageSize` 上限 100 一致（logs.ts:87,112-116）。

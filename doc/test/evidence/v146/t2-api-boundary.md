# OpenBase v1.4.6 测试报告 · T2 接口层（响应结构 + 边界参数）

| 项 | 内容 |
| --- | --- |
| 报告版本 | v1.0.0 |
| 状态 | [Draft] |
| 测试角色 | AT-OpenBase-Test（Step 4 测试 · 后端轨道 T2） |
| 生成时间 | 2026-09-15 22:05:09 |
| 被测版本 | v1.4.6 |
| 执行方式 | fastapi.testclient.TestClient（进程内，未启 uvicorn） |

## 1. 环境与隔离口径

| 依赖 | 状态 |
| --- | --- |
| python | 3.10.11 |
| postgres_5432 | 在监听（本脚本不依赖） |
| redis | 未启动（本脚本不依赖） |
| upstream | OpenLLM/OpenRAG/OpenMemory/DPS 未启动（本脚本不依赖） |
| audit_channel | SQLite 内存库（真实建表 + 真实 commit） |
| log_source | 临时目录 L1 JSONL（OPENBASE_LOG_DIR） |
| token_issuer | openbase.modules.auth.jwt.create_access_token |

## 2. 既有测试基线（Step 4 指定命令）

```text
$ python -m pytest tests/test_logs_endpoints_api.py tests/test_logs_service.py tests/test_logs_derivation.py \
    tests/test_log_reserved_keys.py tests/test_modules_switch_api.py tests/test_db_init.py \
    tests/test_audit_db_persist.py -p no:cacheprovider --tb=line -q
结果：120 tests, 119 passed, 1 failed, 0 skipped（junit 复核：tests=120 failures=1 errors=0 skipped=0）
FAILED tests/test_audit_db_persist.py::test_persist_audit_record_writes_audit_log_row - assert 12 == 1
```

| 测试文件 | 用例数 | 失败 |
| --- | --- | --- |
| `tests/test_logs_endpoints_api.py` | 26 | 0 |
| `tests/test_logs_service.py` | 11 | 0 |
| `tests/test_logs_derivation.py` | 56 | 0 |
| `tests/test_log_reserved_keys.py` | 4 | 0 |
| `tests/test_modules_switch_api.py` | 11 | 0 |
| `tests/test_db_init.py` | 5 | 0 |
| `tests/test_audit_db_persist.py` | 7 | 1 |

### 2.1 唯一失败项定位（单文件隔离复跑 + 顺序对照）

| 复跑命令 | 用例数 | 失败 | 结论 |
| --- | --- | --- | --- |
| `python -m pytest tests/test_audit_db_persist.py -p no:cacheprovider --tb=line -q -rf` | 7 | 0 | 单文件全绿 |
| `python -m pytest tests/test_logs_endpoints_api.py tests/test_audit_db_persist.py ...` | 33 | 0 | 前序为 HTTP 日志用例时不复现 |
| `python -m pytest tests/test_modules_switch_api.py tests/test_audit_db_persist.py ...` | 18 | 1 | **稳定复现**（`assert 12 == 1`） |

根因（代码级定位，非臆测）：`openbase/modules/audit/__init__.py` 的 `audit_persist_queue` 为**进程级单例**，`submit()` 只在入队瞬间读 `OPENBASE_AUDIT_DB_PERSIST`；`tests/test_modules_switch_api.py::sqlite_session_factory` 把该开关置 1 并以 `TestClient` 发请求 → `AuditMiddleware` 把 11 条 `api.request` 审计条目入队且**无人消费**（用例只置开关、不回滚队列）；随后 `test_persist_audit_record_writes_audit_log_row` 调 `drain_once()`，把残留 11 条一并写进自己的 `_RecordingSession`，于是 `len(session.added)` = 12 而非 1。

对照：`tests/test_logs_endpoints_api.py::export_audit_channel` 夹具已显式阻断入队（其 docstring 明确提示该残留风险），`test_modules_switch_api.py` 未做同样防护 → **测试隔离缺陷（用例侧，P2）**，非 v1.4.6 业务代码缺陷。全量回归按字母序执行（`test_audit_db_persist.py` 先于 `test_modules_switch_api.py`）时不复现，本命令的文件顺序（任务指定）刚好触发。

## 3. 用例执行汇总

- 用例总数 **39**：通过 **39**，失败 **0**

| 端点 | 用例数 | 通过 | 失败 |
| --- | --- | --- | --- |
| `GET /logs/search` | 14 | 14 | 0 |
| `GET /logs/facets` | 4 | 4 | 0 |
| `GET /logs/facets/presets` | 4 | 4 | 0 |
| `GET /logs/export` | 8 | 8 | 0 |
| `GET /modules` | 2 | 2 | 0 |
| `PATCH /modules/{id}` | 7 | 7 | 0 |

## 4. 用例明细（状态码 + 断言）

### 4.1 日志检索 `GET /api/v1/logs/search`

| 用例 | 场景 | 期望状态 | 实际状态 | 判定 |
| --- | --- | --- | --- | --- |
| T2-A1 | 正常检索（source=l1_file，默认分页） | [200] | 200 | PASS |
| T2-A2 | 边界：page_size=0（下界越界，schema ge=1） | [422] | 422 | PASS |
| T2-A3 | 边界：page_size=101（上界越界，schema le=100） | [422] | 422 | PASS |
| T2-A4 | 边界：page_size=100（上界内最大值） | [200] | 200 | PASS |
| T2-A5 | 边界：page=0（下界越界，schema ge=1） | [422] | 422 | PASS |
| T2-A6 | 边界：非法 source（枚举白名单） | [422] | 422 | PASS |
| T2-A7 | 边界：非法 module（枚举白名单） | [422] | 422 | PASS |
| T2-A8 | 边界：非法 result（枚举白名单） | [422] | 422 | PASS |
| T2-A9 | 边界：非法 operation（枚举白名单） | [422] | 422 | PASS |
| T2-A10 | 边界：q 超长 201（schema max_length=200） | [422] | 422 | PASS |
| T2-A11 | 边界：from>to（时间窗倒置） | [200, 400] | 200 | PASS |
| T2-A12 | 重复同名参数（module=dps&module=rag，OR 语义） | [200] | 200 | PASS |
| T2-A13 | 无令牌 → 401 | [401] | 401 | PASS |
| T2-A14 | 无权限（令牌无 log:read）→ 403 | [403] | 403 | PASS |

关键断言明细：

- **T2-A1**（正常检索（source=l1_file，默认分页））
  - [通过] 200：status=200
  - [通过] data.items 为 list：type=list
  - [通过] data.total 为 int：value=3
  - [通过] data.page 为 int：value=1
  - [通过] data.page_size 为 int：value=20
  - [通过] data.truncated 为 bool：value=False
  - [通过] 条目含 18 字段（§2 契约）：keys=18
  - [通过] total==3：total=3
  - 取证补充：`{"data_keys": ["items", "page", "page_size", "total", "truncated"], "item_keys": ["action", "case_id", "duration_ms", "ip_address", "method", "module", "operation", "operator_id", "path", "request_id", "result", "run_id", "source", "status_code", "step_id", "summary", "tenant_id", "ts"]}`
- **T2-A2**（边界：page_size=0（下界越界，schema ge=1））
  - [通过] 422：status=422
  - [通过] detail 含参数定位：list
- **T2-A3**（边界：page_size=101（上界越界，schema le=100））
  - [通过] 422：status=422
- **T2-A4**（边界：page_size=100（上界内最大值））
  - [通过] 200：status=200
  - [通过] page_size 回显 100：value=100
- **T2-A5**（边界：page=0（下界越界，schema ge=1））
  - [通过] 422：status=422
- **T2-A6**（边界：非法 source（枚举白名单））
  - [通过] 422：status=422
- **T2-A7**（边界：非法 module（枚举白名单））
  - [通过] 422：status=422
- **T2-A8**（边界：非法 result（枚举白名单））
  - [通过] 422：status=422
- **T2-A9**（边界：非法 operation（枚举白名单））
  - [通过] 422：status=422
- **T2-A10**（边界：q 超长 201（schema max_length=200））
  - [通过] 422：status=422
- **T2-A11**（边界：from>to（时间窗倒置））
  - [通过] 无 5xx：status=200
  - [通过] 200 时空集（无静默返回全量）：status=200, total=0
  - [通过] 400 时错误码为 PARAM 前缀：code=n/a
  - 取证补充：`{"observed": "200 且 total=0（后端未对时间窗倒置做参数拒绝，按空集处理）"}`
- **T2-A12**（重复同名参数（module=dps&module=rag，OR 语义））
  - [通过] 200：status=200
  - [通过] 命中 2 条（OR 生效）：total=2
- **T2-A13**（无令牌 → 401）
  - [通过] 401：status=401
- **T2-A14**（无权限（令牌无 log:read）→ 403）
  - [通过] 403：status=403
  - [通过] 错误码 AUTH_FORBIDDEN：code=AUTH_403

### 4.2 维度聚合 `GET /api/v1/logs/facets`

| 用例 | 场景 | 期望状态 | 实际状态 | 判定 |
| --- | --- | --- | --- | --- |
| T2-B1 | 正常聚合（四维度计数） | [200] | 200 | PASS |
| T2-B2 | 边界：非法 source | [422] | 422 | PASS |
| T2-B3 | 无令牌 → 401 | [401] | 401 | PASS |
| T2-B4 | 无权限 → 403 | [403] | 403 | PASS |

关键断言明细：

- **T2-B1**（正常聚合（四维度计数））
  - [通过] 200：status=200
  - [通过] module 为 dict：value={'dps': 1, 'rag': 1, 'identity': 1}
  - [通过] operation 为 dict：value={'proxy': 2, 'auth_login': 1}
  - [通过] result 为 dict：value={'success': 2, 'server_error': 1}
  - [通过] operator 为 dict：value={'other': 3}
  - [通过] module 计数=identity/dps/rag 各 1：value={'dps': 1, 'rag': 1, 'identity': 1}
  - 取证补充：`{"data_keys": ["module", "operation", "operator", "result"], "frontend_type_declares": ["source", "module", "operation", "result", "operator", "truncated"], "note": "前端 LogFacetsResponse 声明 source/truncated 两字段，后端未返回（页面仅消费三个维度字典）"}`
- **T2-B2**（边界：非法 source）
  - [通过] 422：status=422
- **T2-B3**（无令牌 → 401）
  - [通过] 401：status=401
- **T2-B4**（无权限 → 403）
  - [通过] 403：status=403
  - [通过] 错误码 AUTH_FORBIDDEN：code=AUTH_403

### 4.3 筛选候选 `GET /api/v1/logs/facets/presets`

| 用例 | 场景 | 期望状态 | 实际状态 | 判定 |
| --- | --- | --- | --- | --- |
| T2-C1 | 候选枚举（供前端下拉） | [200] | 200 | PASS |
| T2-C2 | 边界：无声明参数的端点收到多余参数 | [200] | 200 | PASS |
| T2-C3 | 无令牌 → 401 | [401] | 401 | PASS |
| T2-C4 | 无权限 → 403 | [403] | 403 | PASS |

关键断言明细：

- **T2-C1**（候选枚举（供前端下拉））
  - [通过] 200：status=200
  - [通过] source.values 全枚举：value=['l1_file', 'audit_db', 'test_record', 'repo_log']
  - [通过] module.values 含 identity/dps/rag：value=['identity', 'dps', 'rag', 'memory', 'llm', 'gateway', 'testing', 'other']
  - [通过] values 均为 list：types=['list', 'list', 'list', 'list']
  - 取证补充：`{"data_keys": ["module", "operation", "result", "source"]}`
- **T2-C2**（边界：无声明参数的端点收到多余参数）
  - [通过] 200（FastAPI 忽略未声明查询参数）：status=200
- **T2-C3**（无令牌 → 401）
  - [通过] 401：status=401
- **T2-C4**（无权限 → 403）
  - [通过] 403：status=403
  - [通过] 错误码 AUTH_FORBIDDEN：code=AUTH_403

### 4.4 导出 `GET /api/v1/logs/export`

| 用例 | 场景 | 期望状态 | 实际状态 | 判定 |
| --- | --- | --- | --- | --- |
| T2-D1 | 正常导出 CSV（附件名/BOM/表头） | [200] | 200 | PASS |
| T2-D2 | 正常导出 JSON | [200] | 200 | PASS |
| T2-D3 | 边界：format 非法（xml） | [422] | 422 | PASS |
| T2-D4 | 边界：非法 source | [422] | 422 | PASS |
| T2-D5 | 边界：命中 10005 条 > 上限 10000 | [400] | 400 | PASS |
| T2-D6 | 边界：留痕通道显式不可用（OPENBASE_AUDIT_DB_PERSIST=0） | [503] | 503 | PASS |
| T2-D7 | 无令牌 → 401 | [401] | 401 | PASS |
| T2-D8 | 无权限 → 403 | [403] | 403 | PASS |

关键断言明细：

- **T2-D1**（正常导出 CSV（附件名/BOM/表头））
  - [通过] 200：status=200
  - [通过] Content-Type=text/csv; charset=utf-8：value=text/csv; charset=utf-8
  - [通过] Content-Disposition 附件名合规：value=attachment; filename="logs-l1_file-20260915-220508.csv"
  - [通过] BOM 存在：head=b'\xef\xbb\xbfts,'
  - [通过] 1 表头 + 3 数据行：lines=4
- **T2-D2**（正常导出 JSON）
  - [通过] 200：status=200
  - [通过] Content-Type=application/json：value=application/json
  - [通过] 附件扩展名 .json：value=attachment; filename="logs-l1_file-20260915-220508.json"
  - [通过] 3 条记录：len=3
- **T2-D3**（边界：format 非法（xml））
  - [通过] 422：status=422
  - [通过] 不得返回附件：has_cd=False
- **T2-D4**（边界：非法 source）
  - [通过] 422：status=422
- **T2-D5**（边界：命中 10005 条 > 上限 10000）
  - [通过] 400：status=400
  - [通过] 错误码 PARAM_400：code=PARAM_400
  - [通过] detail.limit=10000：detail={'matched': 10005, 'limit': 10000}
  - [通过] detail.matched>10000：detail={'matched': 10005, 'limit': 10000}
  - [通过] 统一错误体含 request_id：request_id=req-eb4b79e64d41
  - [通过] 不得返回附件：has_cd=False
  - 取证补充：`{"observed_matched": 10005}`
- **T2-D6**（边界：留痕通道显式不可用（OPENBASE_AUDIT_DB_PERSIST=0））
  - [通过] 503：status=503
  - [通过] 错误码 BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE：code=BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE
  - [通过] 不得返回未留痕文件：has_cd=False
- **T2-D7**（无令牌 → 401）
  - [通过] 401：status=401
- **T2-D8**（无权限 → 403）
  - [通过] 403：status=403
  - [通过] 错误码 AUTH_FORBIDDEN：code=AUTH_403

### 4.5 模块注册表 `GET /api/v1/modules` 与开关 `PATCH /api/v1/modules/{id}`

| 用例 | 场景 | 期望状态 | 实际状态 | 判定 |
| --- | --- | --- | --- | --- |
| T2-E1 | 模块注册表（5 模块，字段齐备） | [200] | 200 | PASS |
| T2-E2 | 无令牌 → 401（get_current_user 门禁） | [401] | 401 | PASS |
| T2-E3 | 边界：非法 status（paused） | [422] | 422 | PASS |
| T2-E4 | 边界：模块不存在 | [404] | 404 | PASS |
| T2-E5 | 无令牌 → 401 | [401] | 401 | PASS |
| T2-E6 | 无权限（无 module:manage）→ 403 | [403] | 403 | PASS |
| T2-E7 | 正常停用（enabled→disabled，先留痕后生效） | [200] | 200 | PASS |
| T2-E8 | 幂等：同状态重复停用（不重复留痕） | [200] | 200 | PASS |
| T2-E9 | 边界：留痕不可用 → 拒绝变更（fail-closed） | [400, 503] | 503 | PASS |

关键断言明细：

- **T2-E1**（模块注册表（5 模块，字段齐备））
  - [通过] 200：status=200
  - [通过] data.items 为 list：type=list
  - [通过] data.total 为 int：value=5
  - [通过] 包含 gateway 模块（v1.4.6 可达性修复）：ids=['openllm', 'knowledge', 'memory', 'portrait', 'gateway']
  - [通过] 模块字段集齐备：keys=['entry', 'icon', 'id', 'name', 'permission', 'route_prefix', 'sort_order', 'status']
  - 取证补充：`{"items": [{"id": "openllm", "status": "enabled"}, {"id": "knowledge", "status": "enabled"}, {"id": "memory", "status": "enabled"}, {"id": "portrait", "status": "enabled"}, {"id": "gateway", "status": "enabled"}]}`
- **T2-E2**（无令牌 → 401（get_current_user 门禁））
  - [通过] 401：status=401
- **T2-E3**（边界：非法 status（paused））
  - [通过] 422：status=422
- **T2-E4**（边界：模块不存在）
  - [通过] 404：status=404
  - [通过] 错误码 PARAM_404：code=PARAM_404
  - [通过] detail 含 allowed 提示：detail={'module_id': 'nosuchmodule', 'allowed': ['openllm', 'knowledge', 'memory', 'portrait', 'gateway']}
- **T2-E5**（无令牌 → 401）
  - [通过] 401：status=401
- **T2-E6**（无权限（无 module:manage）→ 403）
  - [通过] 403：status=403
  - [通过] 错误码 AUTH_FORBIDDEN：code=AUTH_403
- **T2-E7**（正常停用（enabled→disabled，先留痕后生效））
  - [通过] 200：status=200
  - [通过] status=disabled：value=disabled
  - [通过] previous_status=enabled：value=enabled
  - [通过] effective=next_login：value=next_login
  - [通过] 含 request_id：value=req-748e7652866b
  - 取证补充：`{"data_keys": ["effective", "id", "previous_status", "request_id", "status"]}`
- **T2-E8**（幂等：同状态重复停用（不重复留痕））
  - [通过] 200：status=200
  - [通过] previous_status==status（无变更标记）：previous=disabled, status=disabled
- **T2-E9**（边界：留痕不可用 → 拒绝变更（fail-closed））
  - [通过] 受控错误（非未捕获 500）：status=503
  - [通过] 错误码 BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE：code=BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE

## 5. 响应结构字段名与类型核对（§2/§3 契约）

| 端点 | 后端实际 data 字段 | 类型核对 | 前端类型声明 | 结论 |
| --- | --- | --- | --- | --- |
| `GET /logs/search` | `items/total/page/page_size/truncated` | items=list、total/page/page_size=int、truncated=bool、条目 18 字段 | `LogSearchResponse = {items,total,page,page_size,source,truncated}` | 后端未返回 `source`（前端声明多一个字段） |
| `GET /logs/facets` | `module/operation/result/operator` | 四维度均为 `dict[str,int]` | `LogFacetsResponse = {source,module,operation,result,operator,truncated}` | 后端未返回 `source`/`truncated`（前端声明多两个字段） |
| `GET /logs/facets/presets` | `source/module/operation/result` | 每维度 `{values: list[str]}` | 前端无调用方（openbase-ui/src 内 `presets` 零命中） | 后端能力先行，前端未接线 |
| `GET /logs/export` | 二进制附件（CSV/JSON） | `text/csv; charset=utf-8` / `application/json` + `Content-Disposition` | 前端 `responseType: blob` | 一致 |
| `GET /modules` | `items/total` | items=list[8 字段]、total=int | `ApiSuccess<{items: ModuleDefinition[]; total: number}>` | 一致 |
| `PATCH /modules/{id}` | `id/status/previous_status/effective/request_id` | 全为 str，status/previous_status ∈ {enabled,disabled} | `ModuleSwitchResult` 同字段同类型 | 一致 |

## 6. 留痕与持久化取证（同一轮次真实落库）

- `audit_logs(action=log.export)` 行数：**2**
  - user_id=7 resource=logs:export request_id=req-0fdf52ad5e0a detail=`{"actor": "7", "source": "l1_file", "filters": {}, "row_count": 3, "format": "csv"}`
  - user_id=7 resource=logs:export request_id=req-e7c140abf681 detail=`{"actor": "7", "source": "l1_file", "filters": {}, "row_count": 3, "format": "json"}`
- `audit_logs(action=module.switch)` 行数：**2**（首轮变更 1 条 + 幂等重复请求 **未** 新增）
  - user_id=1 resource=module:openllm request_id=req-748e7652866b detail=`{"operator_id": "1", "module_id": "openllm", "previous_status": "enabled", "status": "disabled"}`
  - user_id=1 resource=module:openllm request_id=req-2caee09d146d detail=`{"operator_id": "1", "module_id": "openllm", "previous_status": "disabled", "status": "enabled"}`
- `dynamic_modules` 复核：`{"id": "openllm", "status": "enabled"}`（测试清理后回到 enabled）

## 7. 发现与判定

- 非法 status（`paused`）→ 422；模块不存在 → 404 `PARAM_404`（detail 含 allowed）；无令牌 401；无权限 403；留痕不可用 → 503 `BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE`（fail-closed，状态不变）：**全部符合 ADR-146-07 定案口径**。
- `page_size` 越界（0 / 101）→ 422，与 schema `ge=1, le=100` 及前端 `clampPageSize`（上限 100）一致。
- 时间窗倒置（`from > to`）后端返回 **200 且 total=0**（按空集处理，无参数拒绝、无 5xx）：属设计未明确定义的口径，登记为观察项 P2（建议在 API 文档 §3.1 补充说明或增加参数校验）。
- 响应体字段与前端类型声明存在「多声明、后端未返回」差异（`search.source`、`facets.source`、`facets.truncated`）：当前页面仅消费 `truncated`（已返回）与三个维度字典，**未观察到运行时影响**，登记为 P2（类型定义与实际报文不一致）。

**T2 结论：PASS**（39/39 通过）

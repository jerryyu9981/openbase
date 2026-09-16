# OpenBase v1.4.6 测试报告 · 后端集成测试（两条链路贯通 + 留痕校验）

| 项 | 内容 |
| --- | --- |
| 报告版本 | v1.0.0 |
| 状态 | [Draft] |
| 测试角色 | AT-OpenBase-Test（Step 4 测试 · 后端轨道 集成测试） |
| 生成时间 | 2026-09-15 22:07:10 |
| 被测版本 | v1.4.6 |
| 执行方式 | fastapi.testclient.TestClient（进程内，未启 uvicorn） |

## 1. 隔离口径

| 项 | 口径 |
| --- | --- |
| audit_and_rbac_db | SQLite 内存库（真实建表 / 真实 commit / 真实 SELECT 校验） |
| log_source | 临时 L1 JSONL 目录（OPENBASE_LOG_DIR） |
| queue_guard | submit_audit_persist 阻断入队（防跨用例污染） |

说明：本机仅 PostgreSQL(5432) 在监听，且**应用进程无法完成 PG 会话**（详见 `regression-backend.md` §3 环境探针）；Redis 与上游四服务（OpenLLM/OpenRAG/OpenMemory/DPS）未启动。故链路②（模块开关）与链路①的留痕落库改用 SQLite 内存库承载（真实建表 / 真实 commit / 真实 SELECT 校验），HTTP 面全部为真实请求-响应。

## 2. 结论判定

| # | 判定项 | 结果 |
| --- | --- | --- |
| 1 | ① 登录（DB 用户 + 密码校验）200 且签发令牌 | PASS |
| 2 | ① 令牌权限点来自 DB RBAC（含 *） | PASS |
| 3 | ① 日志检索 200 | PASS |
| 4 | ① 导出 200 且返回附件 | PASS |
| 5 | ① audit_logs(log.export) 恰好 1 条 | PASS |
| 6 | ① 留痕 request_id 与导出响应头一致 | PASS |
| 7 | ① 留痕操作人 = 登录用户 | PASS |
| 8 | ② 模块列表 200（5 模块含 gateway） | PASS |
| 9 | ② PATCH 200 且 status=disabled | PASS |
| 10 | ② audit_logs(module.switch) 首轮恰 1 条 | PASS |
| 11 | ② 留痕 detail 记录 enabled→disabled | PASS |
| 12 | ② GET 复核 openllm=disabled | PASS |
| 13 | ② dynamic_modules 状态落库 | PASS |
| 14 | ② 语义字段（route_prefix/permission）未被改动 | PASS |
| 15 | ② 二次变更→共 2 条留痕（每次变更 1 条） | PASS |
| 16 | 负向：错误口令 401 | PASS |
| 17 | 负向：无令牌 401 | PASS |
| 18 | 负向：无权限令牌 403 | PASS |
| 19 | 负向：无权限请求未产生留痕 | PASS |

**集成测试结论：PASS**（19/19 项判定通过）

## 3. 链路①：登录/鉴权 → 日志检索 → 导出 → 留痕

| 步骤 | 操作 | 关键结果 |
| --- | --- | --- |
| B-1-1 | POST /api/v1/auth/login（DB 用户 + 密码校验） | `{"status": 200, "response_keys": ["access_token", "expires_in", "refresh_expires_in", "refresh_token", "token_type"], "token_type": "bearer", "expires_in": 7200, "login_ok": true}` |
| B-1-2 | GET /api/v1/auth/me（权限点来自 DB RBAC） | `{"status": 200, "id": 1, "username": "admin", "permissions": ["*"]}` |
| B-1-3 | GET /api/v1/logs/search（登录令牌） | `{"status": 200, "data_keys": ["items", "page", "page_size", "total", "truncated"], "total": 1, "items_request_ids": ["int-req-1"], "x_request_id": "req-18cb88c7a808"}` |
| B-1-4 | GET /api/v1/logs/export（登录令牌） | `{"status": 200, "content_type": "text/csv; charset=utf-8", "content_disposition": "attachment; filename=\"logs-l1_file-20260915-220710.csv\"", "content_preview": "ts,source,module,operation,result,request_id,method,path,status_code,duration_ms,operator_id,tenant_id,ip_address,case_i", "x_request_id"…` |
| B-1-5 | SELECT audit_logs WHERE action='log.export'（留痕校验） | `{"row_count": 1, "checks": {"恰好 1 条留痕": true, "action=log.export": true, "user_id=登录用户": true, "detail 字段集 = actor/source/filters/row_count/format": true, "检索关键字 q 未落留痕": true, "request_id 与响应头一致": true}}` |

留痕明细（真实 SELECT）：

```json
[
  {
    "id": 1,
    "user_id": 1,
    "action": "log.export",
    "resource": "logs:export",
    "resource_id": "l1_file",
    "request_id": "req-6c4ae806d783",
    "detail": {
      "actor": "1",
      "source": "l1_file",
      "filters": {
        "module": [
          "dps"
        ]
      },
      "row_count": 1,
      "format": "csv"
    }
  }
]
```

留痕逐条断言：

- [通过] 恰好 1 条留痕
- [通过] action=log.export
- [通过] user_id=登录用户
- [通过] detail 字段集 = actor/source/filters/row_count/format
- [通过] 检索关键字 q 未落留痕
- [通过] request_id 与响应头一致

## 4. 链路②：模块列表 → 开关变更 → 复核 → 留痕/持久化

| 步骤 | 操作 | 关键结果 |
| --- | --- | --- |
| B-2-1 | GET /api/v1/modules（变更前） | `{"status": 200, "total": 5, "statuses": {"openllm": "enabled", "knowledge": "enabled", "memory": "enabled", "portrait": "enabled", "gateway": "enabled"}, "gateway_present": true}` |
| B-2-2 | PATCH /api/v1/modules/openllm {status:disabled} | `{"status": 200, "data": {"id": "openllm", "status": "disabled", "previous_status": "enabled", "effective": "next_login", "request_id": "req-33606f569b42"}, "x_request_id": "req-33606f569b42"}` |
| B-2-3 | SELECT audit_logs WHERE action='module.switch'（留痕校验） | `{"row_count": 1, "checks": {"恰好 1 条留痕（先留痕后生效）": true, "action=module.switch": true, "resource=module:openllm": true, "detail.previous_status=enabled": true, "detail.status=disabled": true, "operator=登录用户": true, "request_id 与响应头一致": true}}` |
| B-2-4 | SELECT dynamic_modules WHERE id='openllm'（状态持久化） | `{"row": {"id": "openllm", "status": "disabled", "route_prefix": "/openllm", "permission": "openllm:view"}, "checks": {"status 落库为 disabled": true}}` |
| B-2-5 | GET /api/v1/modules（变更后复核） | `{"status": 200, "statuses": {"openllm": "disabled", "knowledge": "enabled", "memory": "enabled", "portrait": "enabled", "gateway": "enabled"}, "checks": {"openllm=disabled": true}}` |
| B-2-6 | GET /api/v1/modules/openllm（语义不变复核） | `{"status": "disabled", "id": "openllm", "route_prefix": "/openllm", "permission": "openllm:view", "checks": {"route_prefix 未改动": true, "permission 未改动": true}}` |
| B-2-7 | PATCH /api/v1/modules/openllm {status:enabled}（测试清理 + 二次留痕验证） | `{"status": 200, "data": {"id": "openllm", "status": "enabled", "previous_status": "disabled", "effective": "next_login", "request_id": "req-83329b5e138a"}, "switch_rows_after": 2}` |

留痕明细（真实 SELECT）：

```json
[
  {
    "id": 2,
    "user_id": 1,
    "action": "module.switch",
    "resource": "module:openllm",
    "resource_id": "openllm",
    "request_id": "req-33606f569b42",
    "detail": {
      "operator_id": "1",
      "module_id": "openllm",
      "previous_status": "enabled",
      "status": "disabled"
    }
  }
]
```

留痕逐条断言：

- [通过] 恰好 1 条留痕（先留痕后生效）
- [通过] action=module.switch
- [通过] resource=module:openllm
- [通过] detail.previous_status=enabled
- [通过] detail.status=disabled
- [通过] operator=登录用户
- [通过] request_id 与响应头一致

状态持久化断言：动态库 `dynamic_modules(id='openllm')` 状态在测试清理后回到 `enabled`，变更过程中读取到 `disabled`（见步骤 B-2-4）。

## 5. 负向链路（鉴权/权限红线）

| 步骤 | 场景 | 结果 |
| --- | --- | --- |
| B-3-1 | POST /auth/login（错误口令） | `{"status": 401, "body": {"code": "AUTH_401", "message": "invalid username or password", "detail": null, "request_id": "req-1b7cb81082e7"}}` |
| B-3-2 | GET /logs/search（无令牌） | `{"status": 401}` |
| B-3-3 | 无权限令牌（无 log:read / module:manage） | `{"search_status": 403, "search_code": "AUTH_403", "patch_status": 403, "patch_code": "AUTH_403"}` |

## 6. 观察项（环境/降级模式登记，非 v1.4.6 增量缺陷）

### OBS-1 DB 不可达（降级模式）下登录令牌无权限点，权限门禁端点返回 403

- 证据：`{"login_status": 200, "me_permissions": ["*"], "logs_search_status": 403}`
- 分析：login 签发令牌只带 role，不带 permissions；require_permission 走 payload 权限 → DB 权限矩阵 → 内存 PermissionStore 三级回退。DB 不可达且内存 PermissionStore 未配置时，登录令牌对 log:read / module:manage 均无授权（/auth/me 的 admin 通配只影响响应体，不参与门禁）。
- 归类：环境限制 + 降级模式行为登记（非 v1.4.6 增量代码缺陷）

阶段 A 原始步骤记录：

- A-1 降级模式：POST /auth/login（DB 不可达 → 内存演示用户）：`{"status": 200, "token_issued": true, "me_status": 200, "me_permissions": ["*"], "search_status": 403, "search_code": "AUTH_403"}`

## 7. 未覆盖项（受环境限制）

- 真实 PG（`openbase` schema）上的 `dynamic_modules` / `audit_logs` 落库未验证：本机 PG 进程不可用（见回归报告环境探针）；改用 SQLite 同结构表完成等价验证，PG 就绪后建议复跑同一链路。
- Redis 缓存链路（身份主体缓存）未参与：Redis 未启动。
- 上游四服务联调未执行：OpenLLM/OpenRAG/OpenMemory/DPS 未启动（本轮后端轨道不涉及其代理链）。

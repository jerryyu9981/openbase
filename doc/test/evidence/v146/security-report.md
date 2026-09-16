# OpenBase v1.4.6 专项测试 · 安全测试报告

| 项目 | 内容 |
|------|------|
| 文档名称 | OpenBase v1.4.6 专项测试 · 安全测试报告 |
| 文档版本 | v1.1.0 |
| 状态 | [Review]（v1.1.0 已登记 P1 缺陷闭环与回归证据，待完整复测后置 [Approved]） |
| 被测版本 | v1.4.6（日志中心四端点 + 模块开关） |
| 被测对象 | `GET /api/v1/logs/search`、`GET /api/v1/logs/facets`、`GET /api/v1/logs/facets/presets`、`GET /api/v1/logs/export`、`GET /api/v1/modules`、`PATCH /api/v1/modules/{id}`；权限码 `log:read` / `module:manage` |
| 测试类型 | 专项测试（安全：权限红线 / 路径穿越 / 敏感信息脱敏 / SQL 注入 / 依赖漏洞） |
| 作者 | SE-OpenBase-Test（测试工程师）/ AT-OpenBase-Test（自动化测试） |
| 执行日期 | 2026-09-15 |
| 证据文件 | `doc/test/evidence/v146/security-raw.json`（56 项检查原始记录）、`doc/test/evidence/v146/security-supplementary.json`（补充探测原始记录） |
| 依据 | `doc/requirements/OpenBase-开发需求文档-v1.4.6.md` §4.6/§4.7/§4.15；`doc/design/OpenBase-API接口设计文档-v1.4.6.md` §3.3/§3.4/§5；`doc/design/OpenBase-非功能设计说明-v1.4.6.md` §3/§5；`doc/design/OpenBase-系统架构设计文档-v1.4.6.md` §6/§7；`AGENTS.md` §6 |

---

## 1. 环境与数据准备（真实命令）

### 1.1 环境约束（如实登记）

| 项 | 实测状态 | 命令/证据 |
|----|----------|-----------|
| PostgreSQL | 可用（`192.168.0.151:5432`，库 `nuct`，schema `openbase`） | `Get-NetTCPConnection -LocalPort 5432 -State Listen` → 2 条监听记录 |
| Redis | **未启动**（6379 无监听；`.env` 配置的 192.168.0.151:6380 亦不可达） | `Get-NetTCPConnection -LocalPort 6379 -State Listen` → 计数 0 |
| 上游四服务（OpenLLM/OpenRAG/OpenMemory/DPS） | **未启动**（四仓日志以本地合成文件代替，见 1.2） | 四仓服务端口未监听 |
| 端口 8011 | **已被占用**（存在先于本次测试启动的 OpenBase 实例，pid 2756，`/health` 返回 `{"status":"ok"}`），故本次测试改用 **8021/8022/8023** | `Get-NetTCPConnection -LocalPort 8011 -State Listen` |

> 说明：占用 8011 的实例其 `OPENBASE_LOG_DIR` 不可控，无法注入合成日志分片；因此本次安全/性能测试在独立端口启动受控实例，全部结论均来自受控实例的真实响应。

### 1.2 受控实例启动命令

```powershell
# 主实例（8021）：50,000 行 L1 分片 + 四仓采集日志（repo_log）
$env:POSTGRES_URL='postgresql://<user>:<password>@<host>:5432/<db>'   # 取自 .env.shared-infra（凭据不落证据文件）
$env:OPENBASE_LOG_DIR='c:\Users\jerry\.trae-cn\work\6a8c5d08e67967d7e6726b59\v146-logs'
$env:OPENBASE_LOG_SETUP='0'      # 被测服务自身不写 JSONL，保证分片行数口径确定
python -m uvicorn openbase.demo_app:app --port 8021 --host 127.0.0.1 --log-level warning

# 留痕通道关闭实例（8023）：验证 fail-closed 语义
$env:OPENBASE_AUDIT_DB_PERSIST='0'   # 其余同上
python -m uvicorn openbase.demo_app:app --port 8023 --host 127.0.0.1 --log-level warning
```

### 1.3 合成数据集（脚本：`gen_log_data.py`，仅写临时目录，不触碰仓库）

| 文件 | 行数 | 字节 | 用途 |
|------|-----:|-----:|------|
| `v146-logs/openbase/openbase-20260914.jsonl` | 50,000 | 12,959,221 | 主分片（含 4 条敏感样本行与检索关键字 `SECRETSEARCH`） |
| `v146-logs/openbase/openbase-20260913.jsonl` | 5 | 1,260 | 时间窗边界（超出 max_days=2 窗口，默认不参与检索） |
| `v146-logs/openbase/openbase-20260914-evil.jsonl` | 3 | — | **非白名单命名**分片（含 `OPENBASE_TRAVERSAL_LEAK_MARKER_DO_NOT_RETURN`） |
| `v146-logs/secret-20260914.jsonl` | 3 | — | 日志目录**外**哨兵文件 |
| `v146-logs/openllm/openllm-20260914.jsonl` | 2 | 657 | `repo_log` 源：JSONL 含明文凭据 |
| `v146-logs/openllm/openllm-20260914.log` | 2 | — | `repo_log` 源：纯文本回退路径含明文凭据 |
| `<work>/LEAK_MARKER.txt` | 1 | — | `logs/` 上级目录哨兵（穿越探测目标） |

### 1.4 令牌构造（真实签名，密钥取自仓库 `.env`，响应体仅留必需字段）

| 令牌 | sub | payload `permissions` | 说明 |
|------|-----|----------------------|------|
| `no_token` | — | — | 不带 `Authorization` |
| `privileged` | 1 | `["log:read","module:manage"]` | DB 侧 `admin` 角色持 `*` 通配 |
| `viewer` | 4 | `[]` | DB 侧 `viewer` 角色（无 `log:read`/`module:manage`） |
| `logread_only` | 4 | `["log:read"]` | 仅日志读权限 |
| `forged` | 1 | 同上 | 使用**错误密钥**签名（`attacker-secret-****`） |
| `garbage` | — | — | 非 JWT 字符串 |

DB 侧权限矩阵实测（`select p.code, r.code ...`）：

```text
*                 → admin（role_permission 行 1）
log:read          → org_admin（4 用户）
module:manage     → org_admin（4 用户）
viewer / user 角色：仅 dps:view、gateway:view、openllm:view、openmemory:view、openrag:view —— 不含 log:read / module:manage
```

---

## 2. ① 权限红线

**执行命令**

```powershell
python 'c:\Users\jerry\.trae-cn\work\6a8c5d08e67967d7e6726b59\security_test.py'
```

**结果：19/19 通过**（原始记录 `security-raw.json` §1 权限红线）

| 用例 | 请求 | 期望 | 实测 | 响应体（节选，真实输出） |
|------|------|:----:|:----:|--------------------------|
| 无令牌 | `GET /api/v1/logs/search` | 401 | **401** ✅ | `{"code":"AUTH_401","message":"missing bearer token","detail":null,"request_id":"req-d4c6c50bd5d9"}` |
| 无令牌 | `GET /api/v1/logs/facets` | 401 | **401** ✅ | 同上（`req-…`） |
| 无令牌 | `GET /api/v1/logs/facets/presets` | 401 | **401** ✅ | 同上 |
| 无令牌 | `GET /api/v1/logs/export` | 401 | **401** ✅ | `{"code":"AUTH_401","message":"missing bearer token",...}` |
| 无令牌 | `GET /api/v1/modules` | 401 | **401** ✅ | 同上 |
| 无令牌 | `PATCH /api/v1/modules/openllm` | 401 | **401** ✅ | 同上（请求体 `{"status":"disabled"}` 未被处理） |
| 无 `log:read`（viewer） | `GET /api/v1/logs/search` | 403 | **403** ✅ | `{"code":"AUTH_403","message":"missing permission: log:read","detail":null,"request_id":"req-f8f71464ae54"}` |
| 无 `log:read` | `/facets`、`/facets/presets`、`/export` | 403 | **403** ✅ | 同上（逐端点实测） |
| 有 `log:read` | `GET /api/v1/logs/search` | 200 | **200** ✅ | `{"code":0,"message":"success","data":{...}}` |
| 无 `module:manage`（viewer） | `PATCH /api/v1/modules/openllm` | 403 | **403** ✅ | `{"code":"AUTH_403","message":"missing permission: module:manage",...}` |
| 有 `log:read`、无 `module:manage` | `PATCH /api/v1/modules/openllm` | 403 | **403** ✅ | `{"code":"AUTH_403","message":"missing permission: module:manage",...}` |
| 伪造签名 | `GET /api/v1/logs/search` | 401 | **401** ✅ | `{"code":"AUTH_401","message":"invalid or expired token",...}` |
| 畸形令牌 | `GET /api/v1/logs/search` | 401 | **401** ✅ | `{"code":"AUTH_401","message":"invalid or expired token",...}` |
| 非法 status 枚举 | `PATCH {"status":"hacked"}` | 4xx | **422** ✅（口径偏差见 §8-P2-3） | `{"code":"PARAM_422","message":"parameter validation error","detail":[{"loc":["body","status"],"msg":"Input should be 'enabled' or 'disabled'",...}]}` |
| 不存在模块 | `PATCH /api/v1/modules/%.%/%…/etc/passwd` | 4xx | **404** ✅ | `{"code":"404","message":"Not Found",...}` |

**附加控制项（正向取证）**

| 用例 | 实测 |
|------|------|
| 幂等 PATCH（状态与当前一致） | 200 `{"data":{"id":"openllm","status":"enabled","previous_status":"enabled","effective":"next_login","request_id":"req-9bdb11c33c0c"}}`，**不落库、不重复留痕**（`dynamic_modules` 无新增行，`audit_logs(action=module.switch)` 行数不变） |
| 模块开关真实变更往返 | 200 → `dynamic_modules` 出现 `memory=disabled` 行 + `audit_logs` 新增 `module.switch` 行，`detail={"operator_id":"1","module_id":"memory","previous_status":"enabled","status":"disabled"}`；随后回切 `enabled` 复原（详见 `security-supplementary.json` → `module_switch_audit`） |
| 留痕通道不可用（8023，`OPENBASE_AUDIT_DB_PERSIST=0`） | `GET /logs/export` → **503** `{"code":"BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE","message":"log export rejected: audit trail unavailable",...}`；`PATCH /api/v1/modules/memory {"status":"disabled"}` → **503** `{"code":"BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE",...}`，且 `dynamic_modules` 前后均为空（**状态未被变更**，fail-closed 生效） |
| 观察项（非缺陷） | `GET /api/v1/modules` 仅需登录（viewer 令牌 200），无权限点约束 —— 与实现一致（`Depends(get_current_user)`），设计 §3.4 未对该读接口定义权限码，登记为观察项 |

---

## 3. ② 路径穿越防护

**结果：15/15 通过**

### 3.1 `source` 参数注入（枚举白名单拦截）

| 注入值 | 实测状态 | 响应体（节选） |
|--------|:--------:|----------------|
| `../../../../etc/passwd` | **422** | `{"code":"PARAM_422","detail":[{"type":"literal_error","loc":["query","source"],"msg":"Input should be 'l1_file', 'audit_db', 'test_record' or 'repo_log'","input":"../../../../etc/pa…` |
| `..\..\..\windows\win.ini` | **422** | 同上（`input` 为反斜杠形态） |
| `/etc/passwd` | **422** | 同上 |
| `C:\Windows\win.ini` | **422** | 同上 |
| `openbase-20260914.jsonl` | **422** | 同上（**文件名不被接受为 source**，证实无「文件名直通」通道） |
| `openbase-20260914-evil.jsonl` | **422** | 同上 |
| `../openbase/openbase-20260914.jsonl` | **422** | 同上 |

判定：`source` 为 `Literal` 枚举，路径形态载荷在 **Pydantic 层**被拒；响应体不含 `OPENBASE_TRAVERSAL_LEAK_MARKER_DO_NOT_RETURN`、`root:x:`、`[extensions]`（实测 `leaked=false`）。

### 3.2 时间窗 / 文件分片相关参数注入

| 注入点 | 值 | 实测 | 泄漏 |
|--------|----|:----:|:----:|
| `from` | `../../../../etc/passwd` | 200（解析失败 → 回落默认时间窗） | 否 |
| `from` | `/etc/passwd` | 200 | 否 |
| `from` | `20260914` | 200 | 否 |
| `to` | `..\..\..\windows\win.ini` | 200 | 否 |
| `from` | `2026-09-14T00:00:00Z' OR 1=1 --` | 200 | 否 |
| `to` | `1900-01-01T00:00:00Z` | 200 | 否 |
| `case_id` / `run_id` / `q` | `../../etc/passwd`、`/etc/shadow` | 200 | 否 |

判定：文件名**由代码按时间窗推导**（`openbase-{YYYYMMDD}.jsonl`），用户参数不参与路径拼接；非法时间串经 `_parse_datetime` 返回 `None` 后回落默认窗口，不产生任何文件系统副作用。

### 3.3 非白名单分片与目录外文件隔离（正向取证）

| 用例 | 实测 |
|------|------|
| 主分片全量检索（50000 行）响应体与 CSV 导出体 | **均不含** `OPENBASE_TRAVERSAL_LEAK_MARKER_DO_NOT_RETURN`，亦无 `path="/leak"` 条目 ✅ |
| 适配器级实证 `L1FileAdapter(log_root=v146-logs)._slice_documents()` | 仅返回 `['openbase\\openbase-20260914.jsonl']`（`openbase-20260914-evil.jsonl` 与 `secret-20260914.jsonl` **未纳入**） |
| `L1FileAdapter._safe_path()` 探针 | `evil_shard=拒绝`、`outside_file=拒绝`、`../.. /LEAK_MARKER.txt=拒绝`、`C:/Windows/win.ini=拒绝`、`openbase-20260914.jsonl=允许` |

> 结论：需求 §4.7「路径安全」与 AC-146-07-3（时间窗推导 + 白名单正则 + `Path.resolve()` 目录归属三重校验）**实测成立**。

---

## 4. ③ 敏感信息脱敏

**结果：7/8 通过（1 项失败 → P1 缺陷，见 §8-P1-1）**

### 4.1 L1 源（`l1_file`）：符合契约

检索命令（等价 HTTP 调用）：

```
GET /api/v1/logs/search?source=l1_file&q=SECRETSEARCH&page=1&page_size=50   → 200，total=4
```

样本行真实响应（节选）：

```json
{"ts":"2026-09-14T10:00:00.000+00:00","source":"l1_file","module":"llm","operation":"proxy","result":"success",
 "request_id":"req-SECRETSEARCH-0001","path":"/api/v1/llm-proxy/v1/chat/completions","status_code":200,
 "summary":{"resp_status":{"access_token":"***","ok":true},
            "resp_headers":{"authorization":"***","set-cookie":"***","content-type":"application/json"},
            "upstream_status":{"api_key":"***","code":200}}}
```

| 断言 | 实测 |
|------|------|
| `resp_headers.authorization` / `set-cookie`、`resp_status.access_token` / `credential` / `jwt`、`upstream_status.api_key` | 全部 `"***"` ✅ |
| 响应体不含任一台账明文（`sk-openllm-fff…`、`P@ssw0rd-Plaintext-2026`、`sk-upstream-…`、`access-token-plain-…`、`sess-9f8e…`、`eyJhbGciOiJIUzI1NiJ9.plaintext.signature`） | 0 命中 ✅ |
| 顶层凭据字段（`password`/`token`/`api_key`） | **未透出**（`LogEntry` 18 字段收敛，改行 `summary=null`） ✅ |
| CSV 导出（`format=csv&q=SECRETSEARCH`） | 首字节 `\ufeff`，表头 `ts,source,module,operation,result,…`；明文 0 命中 ✅ |
| JSON 导出（`format=json&q=SECRETSEARCH`） | 明文 0 命中 ✅ |

### 4.2 `repo_log`（四仓采集日志）源：**存在明文凭据泄漏**

| 通道 | 样本（真实响应） | 判定 |
|------|------------------|:----:|
| JSONL 路径（`message` 自由文本） | `"summary":{"level":"ERROR","service":"openllm","message":"auth failed for credential=sk-upstream-abcdef1234567890abcdef1234567890","event":"auth.login"}` | **泄漏**（上游 API Key 明文） |
| JSONL 路径（`message` 自由文本） | `"message":"upstream call ok, token=Bearer sk-openllm-ffffffffffffffffffffffffffffffff"` | **泄漏**（Bearer 令牌明文） |
| 纯文本回退路径（`summary.raw.line`） | `"raw":{"line":"2026-09-14 14:00:00 10.0.0.9 - - \"POST /v1/SECRETSEARCH/chat HTTP/1.1\" 200 123 p***@ssw0rd-Plaintext-2026 token=sk-openllm-ffffffffffffffffffffffffffffffff"}` | **泄漏**（令牌明文；口令仅因**邮箱正则误命中**被改写，非凭据规则命中） |

复算命令：

```powershell
python 'c:\Users\jerry\.trae-cn\work\6a8c5d08e67967d7e6726b59\repo_text_probe.py'   # 输出 repo-text-fallback.json
# 实测：status=200 total=3；'sk-openllm-ffffffffffffffffffffffffffffffff' in body => True
```

根因（代码级，只读核对，未修改源码）：`openbase/modules/logs/repository.py` → `RepoLogAdapter._parse_line()` 仅对 **键名** 白名单字段（`level/service/message/event`）调用 `_mask_props` → `core/mask.py:mask_sensitive()`；`mask_sensitive` 对**字符串值**只做手机号/证件号/邮箱三类 PII 正则（`_mask_text`），**不识别 `token=`/`credential=`/`Bearer …`/`sk-…` 等凭据模式**，键名不敏感即原样返回。

契约依据（明确违反）：

- 需求 §4.7：`token`/`key`/`password`/证件号/手机号等**不得返回明文**；脱敏复用 `mask_sensitive` 统一口径；
- 需求 §4.19 / 非功能设计 §3「四仓日志脱敏」：四仓日志经 `RepoLogAdapter` **服务端统一脱敏，不得因新源放宽口径**（AC-146-19-3）；「沿用各仓既有脱敏逻辑但不依赖它（本仓再兜一层）」；
- 需求 §4.7「检索词」：查询关键字不写日志（本项实测通过，见 4.3）。

### 4.3 留痕（`audit_logs`）不含检索关键字与导出内容

```sql
select count(*) from openbase.audit_logs where detail::text like '%SECRETSEARCH%' or action like '%SECRETSEARCH%';
-- 0
select id, action, request_id, detail::text from openbase.audit_logs where action in ('log.export','module.switch') order by id desc limit 1;
-- 8751 | log.export | req-5fc8ae45de03 | {"actor": "1", "source": "l1_file", "filters": {}, "row_count": 4, "format": "json"}
```

| 断言 | 实测 |
|------|------|
| `audit_logs` 全表无检索关键字 `SECRETSEARCH` | **0 命中** ✅ |
| `log.export` 留痕 `detail` 键集 | `{actor, source, filters, row_count, format}`，`filters` 内**无 `q`** ✅ |
| 留痕不含导出内容（无 `status_code`/CSV 行内容） | 抽样核对通过 ✅ |

---

## 5. ④ SQL 注入尝试（`audit_db` 源）

**执行命令**：`python security_test.py`（§4 SQL 注入段）

| 注入位置 | 载荷 | HTTP 状态 | `data.total` | 500？ | 越权（≥1000 行）？ |
|----------|------|:---------:|:------------:|:-----:|:-----------------:|
| `q` | `' OR 1=1 --` | 200 | 0 | 否 | 否 |
| `q` | `%' OR '1'='1` | 200 | 0 | 否 | 否 |
| `q` | `'; DROP TABLE openbase.audit_logs; --` | 200 | 0 | 否 | 否 |
| `q` | `') UNION SELECT null,password,… from openbase.users --` | 200 | 0 | 否 | 否 |
| `operator` | `' OR 1=1 --` | 200 | 0 | 否 | 否 |
| `operator` | `1 OR 1=1` | 200 | 0 | 否 | 否 |
| 注入后完整性 | — | — | `audit_logs` 8551 → 8557（**未减少**，表结构完好）、`users`=30 | — | — |

代码级核对（只读）：`AuditDbAdapter._filters_to_orm()` 使用 `sa.or_(AuditLog.request_id.ilike("%…%"), …)` 与 `select(AuditLog).where(...)`，**全部为 SQLAlchemy 绑定参数**，无字符串拼接 SQL（符合 `AGENTS.md` §5）。

**重要限定（如实登记）**：上述 6 条注入用例的 `total` 恒为 0，**并非**「注入被正确抵御」的充分证据 —— 原因是 `audit_db` 源在该环境下**整体不可用并静默返回空集**（服务端日志 `audit_db source fetch degraded`；库内 `audit_logs` 实测 8,566 行、`action='api.request'` 5,492 行）。因此「是否越权返回」**本环境不可判定**，必须在该缺陷修复后复测（详见 §8-P1-2 与 `security-supplementary.json` → `auditdb_source_http`）。

---

## 6. ⑤ 依赖漏洞扫描

| 子项 | 命令 | 结果 |
|------|------|------|
| 后端 | `python -m pip_audit --version` | **`No module named pip_audit`** → 工具不可用（未联网安装） |
| 后端（替代） | `python -m pip list --format=freeze` | 共 **261** 个包；关键项：`fastapi==0.139.2`、`uvicorn==0.51.0`、`starlette==1.3.1`、`pydantic==2.13.4`、`SQLAlchemy==2.0.49`、`asyncpg==0.31.0`、`python-jose==3.5.0`、`PyJWT==2.13.0`、`bcrypt==3.2.2`、`cryptography==46.0.7`、`requests==2.33.1`、`httpx==0.28.1` |
| 前端 | `npm audit --omit=dev --json`（`openbase-ui/`） | **1 项 moderate**：`echarts`（直接依赖）**XSS**，`GHSA-fgmj-fm8m-jvvx`，`CVSS 6.1`，影响范围 `<6.1.0`，可用修复版本 `6.1.0`（semver-major）；`metadata: {info:0, low:0, moderate:1, high:0, critical:0, total:1}`，生产依赖 118 / 开发依赖 400 |

未覆盖说明：后端仅做「清单留档」，未做 CVE 匹配（工具缺失）；前端仅扫描 `--omit=dev`（依据任务口径），devDependencies 未扫描。

---

## 7. 结果汇总

| 序 | 测试项 | 用例数 | 通过 | 失败 | 结论 |
|:--:|--------|-------:|-----:|-----:|------|
| ① | 权限红线（含 fail-closed 与留痕正向取证） | 19 | 19 | 0 | **通过** |
| ② | 路径穿越防护 | 15 | 15 | 0 | **通过** |
| ③ | 敏感信息脱敏 | 8 | 7 | 1 | **不通过**（P1-1：`repo_log` 自由文本泄漏凭据） |
| ④ | SQL 注入尝试 | 7 | 7 | 0 | **条件通过**（无 500、无泄漏、表完好；越权判定因源降级不可判定，需复测） |
| ⑤ | 依赖漏洞扫描 | 3 | 2 | 1 | 后端工具缺失（留档）；前端 **1 moderate** |
| —— | **合计** | **56**（自动断言）/ **52**（口径化用例） | 55 | 1 | 详见 §8 |

---

## 8. 问题清单

### P1-1（代码缺陷）`repo_log` 源自由文本字段未脱敏，上游凭据明文回显

- **现象**：`GET /api/v1/logs/search?source=repo_log` 返回的 `summary.message`（JSONL 路径）与 `summary.raw.line`（纯文本回退路径）中原样包含 `sk-…` API Key、`Bearer …` 令牌等明文凭据。
- **影响面**：日志中心（管理员可读）与**导出能力**（`/logs/export` 同源同字段）→ 凭据经 Web 页面/CSV 二次扩散；与本版本 G5「权限与脱敏合规」直接冲突。
- **契约依据**：需求 §4.7、§4.19；非功能设计 §3「四仓日志脱敏（不得因新源放宽口径）」；AC-146-19-3。
- **根因**：`core/mask.py:mask_sensitive()` 仅按**键名**判定凭据 + 对字符串仅做 PII 正则；`repository.py:RepoLogAdapter._parse_line()` 的自由文本（`message`/`raw.line`）无凭据模式兜底。
- **修复建议（不属本次执行范围，供开发轨闭环）**：在 `mask_sensitive`/日志适配器上增加凭据模式规则（`(?i)(bearer\s+|token=|password=|api_key=|secret=|sk-[A-Za-z0-9_-]{16,})` → `***`），并对 `message`/`raw.line` 截断前统一过一遍脱敏；补一条针对 `repo_log` 明文凭据的回归用例。
- **证据**：`security-raw.json`（FAIL 项）、`security-supplementary.json` → `repo_log_text_fallback`。

### P1-2（代码缺陷 + 静默降级）`audit_db` 源在 HTTP 服务内恒不可用，且降级为 200 空结果

- **现象**：`source=audit_db` 检索恒返回 `{"items":[],"total":0}`（200），`facets` 四维计数全空；服务端 WARN `audit_db source fetch degraded`；而库内 `audit_logs` 实测 8,566 行（`api.request` 5,492 行）。
- **根因（复现证据 `auditdb-degrade-repro.json`）**：`AuditDbAdapter.fetch()` 在 **worker 线程内** `asyncio.run(self._fetch_async(...))`，与 uvicorn 主事件循环**共用进程级 async 引擎/连接池** → 跨事件循环复用 asyncpg 连接：线程内报 `AttributeError: 'NoneType' object has no attribute 'send'`；**反向污染**主循环后续查询：`InterfaceError: cannot perform operation: another operation is in progress`（步骤 1 主循环查询 OK → 步骤 2 线程 `asyncio.run` 失败 → 步骤 3/6 主循环查询亦失败）。
- **契约依据**：非功能设计 §5「单源不可用 → 该源 `SYS_503` + `items=[]`（不跨源兜底）」「DB 连接失败 → `SYS_503`」；§4 可观测性「不静默」。实现在 `AuditDbAdapter.fetch()` 内 `except Exception → WARN + FetchResult([],0,False)`，**调用方无感知**，UI 会呈现「无数据」而非错误（误导排障）。
- **影响面**：日志中心四源之一（审计库）功能不可用；同时带来**跨请求 DB 连接污染**风险（观测到其它 ORM 查询瞬时失败，随后自愈）。
- **顺带关联**：开发审查 §8 RS-146-02（asyncpg 连接不稳）与 RS-146-05（L1 坏行 500）同属「适配器在服务运行态下的执行模型」问题族，建议一并整改（改为 async 适配器协议或在 `to_thread` 内使用**独立引擎**）。
- **证据**：`security-supplementary.json` → `auditdb_source_http` / `auditdb_degrade_repro`。

### 8.1 P1 缺陷闭环（2026-09-16）

两项 P1 缺陷均已在 Step 4 内完成代码修复，并由自动化 HTTP 层回归用例闭环（下述用例全部在 `tests/test_logs_endpoints_api.py` / `tests/test_mask.py`，随 `python -m pytest tests` 全量通过）。

#### P1-1 闭环：`repo_log` 自由文本凭据兜底脱敏

| 项 | 内容 |
|----|------|
| 修复位置 | `openbase/core/mask.py`：新增 `_mask_credentials_in_text`（凭据模式兜底，SEC-146-001）——对**字符串值**按统一模式遮蔽 `Bearer <token>` / `sk-*` / `AKIA[0-9A-Z]{16}` / `token/password/secret/api[_-]?key/… = <value>` / `authorization:`；廉价前置 `_CREDENTIAL_HINT_PATTERN` 无线索时零开销直返。既有键名脱敏与隐私文本口径**不放宽**（`test_credential_patterns_do_not_widen_key_name_masking` 锁定）。 |
| 接线 | `openbase/modules/logs/repository.py` → `RepoLogAdapter._parse_line()`：JSONL 的 `summary.message/event` 与纯文本回退的 `summary.raw.line` 均经 `_mask_props → mask_sensitive` 脱敏后再对外。 |
| 回归用例 | `tests/test_mask.py::test_free_text_credentials_are_masked`、`test_credentials_masked_in_nested_and_list_values`（自由文本兜底）；`tests/test_logs_endpoints_api.py::test_repo_log_free_text_credentials_are_masked_in_search`（搜索响应体 `summary.message`/`summary.raw.line`）、`test_repo_log_free_text_credentials_are_masked_in_export`（CSV 导出物）。 |
| 判定 | 复现口径样本（`sk-openllm-fff…` / `Bearer eyJ…`）在搜索响应体与导出物中 **0 明文命中**；修复后 `assert 'sk-...' in body → False`。 |

#### P1-2 闭环：`audit_db` 源主事件循环取数 + 显式 503（消除静默降级与跨循环连接污染）

| 项 | 内容 |
|----|------|
| 修复位置 | `openbase/modules/logs/repository.py` → `AuditDbAdapter`：新增 `fetch_async` / `facets_async`（主事件循环内使用既有 async 会话取数，成功→真实返回库内行；源不可用→抛 `BaseError(SYS_SOURCE_UNAVAILABLE)`，**不静默返回空集**）；同步入口 `fetch`/`facets` **显式失败**（禁止在工作线程内自建事件循环复用进程级连接池）。 |
| 接线 | `openbase/modules/logs/router.py` 三端点（search/facets/export）统一调用 `service.*_async`；`service.py::_fetch_async/_facets_async` 按 `async_source` 分流（DB 源主循环 async / 文件源 `to_thread`）——执行面契约 INT-146-001。 |
| 回归用例 | `tests/test_logs_service.py::test_audit_db_sync_fetch_path_rejected_with_sys_503`（同步入口拒用）；`tests/test_logs_endpoints_api.py::test_audit_db_source_unavailable_returns_sys_503`、`test_audit_db_source_unavailable_is_not_silent_on_all_endpoints`（三端点源不可用→503，`detail={"source":"audit_db"}`，无 `degraded` 关键字）。 |
| 判定 | 源不可用路径由「200 + total=0 静默降级」改为 **503 `SYS_503`**，符合非功能设计 §5「单源不可用 → 该源 + `items=[]`」「DB 连接失败 → `SYS_503`」「不静默」；服务端日志由 `audit_db source fetch degraded`（WARN，吞异常）改为 `audit_db source unavailable` + 显式 503。 |

> 两项闭环后，§5 SQL 注入「越权返回」判定与 §9 受限项中「`audit_db` 源复测」「LIKE 通配 P2-2」「RS-146-02 asyncpg 波动用例」「RS-146-05 L1 坏行」等联动复测项已具备执行条件，见 §9 补救计划更新。

### P2-1（代码缺陷 · 设计偏差）`/logs/export` 未按设计流式返回

- **现象**：设计（非功能 §2「导出上限」行）要求「导出采用**流式写**（`StreamingResponse`）避免整份驻留内存」；实现 `logs/service.py:export()` 用 `io.StringIO` 全量拼接后 `Response(content=...)` 返回（`router.py:98`）。
- **影响**：10,000 行上限下整份内容驻留内存（实测 8,000 行 CSV 体量见 `perf-raw.json`），与设计口径不一致；不构成安全漏洞但属契约/非功能偏差。
- **证据**：`logs/service.py:334-345`（`buffer = io.StringIO()`）+ `logs/router.py:98-102`（`Response`）。

### P2-2（安全观察）`q` 为 LIKE 通配注入面（未影响本版本结论）

- `AuditDbAdapter._filters_to_orm()` 将 `q` 绑定进 `ilike("%…%")`，`%`/`_` 会被当作**通配符**（LIKE 语义注入，非 SQL 注入）。因 `audit_db` 源当前降级（P1-2），本环境**未能实测**该行为；登记为待复测项，修复 P1-2 后应补充 `q=%`、`q=_` 用例并确认是否需要转义。

### P2-3（契约偏差）参数校验状态码/错误码与设计文档不一致

| 场景 | 设计（API §3.1/§3.4） | 实测 | 证据 |
|------|----------------------|------|------|
| `source` 非法 | 400 `PARAM_400` | **422** `PARAM_422` | `security-raw.json` |
| `status` 非法 | 400 `PARAM_400` | **422** `PARAM_422` | 同上 |
| 模块不存在 | 404（v1.2.0 新增错误码） | 404 ✅（但 body 为 `{"code":"404","message":"Not Found"}`，非统一错误体） | 同上 |

与开发审查 §8 RS-146-01「`PARAM_400` vs `PARAM_INVALID` 并存」为同一待评审口径；建议 Step 4 评审裁定后**回写设计文档**（前端文案依赖 `detail.field`）。

> **后续处置（2026-09-16）**：本项已由人工裁定——采用**改实现对齐设计**（而非回写设计文档）：参数校验统一 **400 `PARAM_400`**（`openbase/core/errors/{codes,base}.py`），时间窗非法 `from > to` 与时间格式非法均显式 400（`modules/logs/service.py`）。上表实测记录保持原样（报告出具时状态），复核证据见 `doc/test/OpenBase-测试报告-v1.4.6.md` §9.2。模块不存在的 404 body 非统一体（`PARAM_404`/`BIZ_404` 双码）仍登记待裁定。

---

## 9. 未执行 / 受限项与补救计划

| 项 | 状态 | 原因 | 补救计划 |
|----|------|------|----------|
| `pip-audit` 后端 CVE 扫描 | **未执行** | 环境未安装 `pip_audit`（`No module named pip_audit`），按任务口径不联网安装 | 在有网/受控环境执行 `pip install pip-audit && python -m pip_audit -r requirements.txt`（或对 `pyproject.toml` 依赖执行），结果回填本报告 §6；后端 `requirements/pyproject` 版本清单已留档 |
| 前端 devDependencies 漏洞 | 未执行 | 任务口径限定 `--omit=dev` | 追加 `npm audit --json`（含 dev）作为补充证据 |
| Redis 相关安全项（事件通道/缓存投毒） | 未执行 | Redis 未启动（6379/6380 均无监听），v1.4.6 四端点不依赖 Redis | 联调窗口（Redis 就绪）补充；登记为环境限制 |
| 上游四服务真实日志脱敏核验 | **部分替代** | 上游未启动，无法取得真实上游日志 | 已用**合成上游日志**（JSONL + 纯文本）覆盖脱敏口径；联调窗口以真实四仓日志复测 P1-1 修复效果 |
| `audit_db` 源 SQL 注入「越权返回」判定 | 不可判定（v1.0.0）→ **复测条件已达成**（v1.1.0） | 源降级恒返回空集（P1-2） | P1-2 已闭环；随 Step 4 回归在可用 DB 环境复测 §5 全部 6 条载荷 + LIKE 通配用例（P2-2） |
| 渗透类测试（越权横向、SSRF、DoS 压测阈值） | 未执行 | 超出本次专项范围（属安全评审/独立渗透范围） | 建议纳入 v1.5 平台治理版本的安全专项 |
| RS-146-02 的 4 项 asyncpg 波动用例 | 未执行 | 属功能回归范围（本次为安全/性能/可访问性/合规专项），且与 P1-2 同源 | 建议随 P1-2 整改后在稳定环境重跑 `tests/test_tenant_admin.py`、`tests/test_users_admin.py` 并登记 |

---

## 10. 结论

1. **权限红线全部成立**：日志中心四端点与模块开关的 401/403/401（伪造）× 无令牌/无权限/伪造签名组合共 19 项全部符合设计（需求 §4.7、§4.15；AC-146-15-2）；模块开关的**先留痕后生效 + 留痕不可用 fail-closed（503 且状态不变）**经 8023 实例实测成立。
2. **路径穿越防护成立**：`source` 枚举白名单 + 时间窗推导文件名 + 白名单正则 + 目录归属校验三重防线的正向/逆向用例全部通过，未出现任何系统文件内容回显。
3. **脱敏缺陷已闭环（P1-1）**：L1 源与留痕口径合规；`repo_log` 自由文本曾明文回显上游凭据（违反 AC-146-19-3），现已由 `mask.py` 凭据模式兜底修复，并在搜索/导出回归用例中确认 0 明文命中。
4. **`audit_db` 源缺陷已闭环（P1-2）**：跨事件循环复用连接池导致源恒不可用且静默 200 空结果，现已改为**主事件循环取数 + 源不可用显式 503**（符合非功能设计 §5，消除静默降级与跨请求连接污染）；§5 SQL 注入「越权返回」判定已具备复测条件。
5. 其余为 P2 级偏差（流式导出、参数校验状态码、LIKE 通配）与工具/环境限制（`pip-audit`、Redis、上游服务），均已给出补救计划。

---

## 11. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-15 | SE-OpenBase-Test / AT-OpenBase-Test | 初始版本：v1.4.6 安全专项（权限红线 19 项 / 路径穿越 15 项 / 脱敏 8 项 / SQL 注入 7 项 / 依赖扫描 3 项 = 56 项自动断言，55 通过）；登记 P1 缺陷 2 项、P2 偏差 3 项、受限项 7 项；证据 `security-raw.json`、`security-supplementary.json` |
| v1.1.0 | 2026-09-16 | SE-OpenBase-Test / AT-OpenBase-Test | 登记 P1 缺陷闭环：P1-1 `repo_log` 自由文本凭据兜底脱敏（`core/mask.py`，SEC-146-001）、P1-2 `audit_db` 主事件循环取数 + 源不可用显式 503（`repository.py` / `router.py` / `service.py`，INT-146-001）；新增 §8.1 闭环记录与回归用例（`test_mask.py`、`test_logs_endpoints_api.py`、`test_logs_service.py`）；更新结论与补救计划（§5 SQL 注入「越权返回」判定、LIKE 通配 P2-2、RS-146-02/05 具备复测条件）

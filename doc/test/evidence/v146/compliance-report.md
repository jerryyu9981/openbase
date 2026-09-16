# OpenBase v1.4.6 专项测试 · 合规测试报告

| 项目 | 内容 |
|------|------|
| 文档名称 | OpenBase v1.4.6 专项测试 · 合规测试报告 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 被测版本 | v1.4.6（日志中心四端点 + 模块开关，权限码 `log:read` / `module:manage`） |
| 测试类型 | 专项测试（合规：文档与版本一致性 / API 契约 / 敏感配置入库 / 依赖许可与版本锁定） |
| 作者 | SE-OpenBase-Test（测试工程师）/ AT-OpenBase-Test（自动化测试） |
| 执行日期 | 2026-09-15 |
| 仓库基线 | `HEAD = b39ed64`（`docs(v1.4.6): 回填 Step 3 基线提交 db5682b 与技术债务编号修正`），工作区除本次新增 `doc/test/evidence/v146/**` 外无改动 |
| 原始数据 | `doc/test/evidence/v146/compliance-raw.json`、`compliance-contract.json`、`compliance-export-headers.json`、`compliance-supplementary.json` |
| 依据 | 用户《需求文档标准化编写规则》§四/§五；`doc/design/OpenBase-API接口设计文档-v1.4.6.md` §3.1/§3.3/§3.4/§5；`AGENTS.md` §5/§6；`doc/development/OpenBase-代码逻辑审查记录-v1.4.6.md` §8（RS-146-01/06） |

---

## 1. ① 文档与版本一致性

**执行命令**

```powershell
python 'c:\Users\jerry\.trae-cn\work\6a8c5d08e67967d7e6726b59\compliance_check.py'
# 产出 compliance-raw.json → docs_version_consistency
```

**v1.4.6 文档存在性**

| 目录 | 存在 | v1.4.6 文档数 | 文件清单 |
|------|:----:|:-------------:|----------|
| `doc/requirements/` | ✅ | **5** | 开发需求文档 / 需求基线及设计移交说明 / 需求来源与干系人 / 需求评审记录 / 需求追溯矩阵 |
| `doc/design/` | ✅ | **8** | API接口设计文档 / UI设计文档 / 前端架构设计文档 / 系统架构设计文档 / 设计评审记录 / 路径归属矩阵 / 部署架构草案 / 非功能设计说明 |
| `doc/development/` | ✅ | **4** | DevLogReport / 代码逻辑审查记录 / 开发审计移交材料 / 设计开发追溯矩阵 |
| 合计 | — | **17** | 全部命名含 `-v1.4.6`，与版本号声明一致 |

**文件头「文档版本」 vs 修订历史底部版本号（17 份全量核对）**

| 结论 | 数量 | 明细 |
|------|:----:|------|
| **一致** | **16 / 17** | 例：开发需求文档 头 `v1.4.0` = 末行 `v1.4.0`；API接口设计文档 `v1.2.0`= `v1.2.0`；DevLogReport `v1.0.1`=`v1.0.1`；非功能设计说明 `v1.1.0`=`v1.1.0`；代码逻辑审查记录 `v1.0.0`=`v1.0.0` |
| **不一致 / 无元信息** | **1** | `doc/design/OpenBase-路径归属矩阵-v1.4.6.md`：**无 `文档版本` / `状态` 字段，且无「修订历史」章节**（该文件为脚本生成物，头部含"生成方式/生成日期/来源"） |

- 状态字段抽检：`doc/requirements/**` 5 份均为 `[Approved]`；`doc/design/**` 与 `doc/development/**` 均为 `[Review]`（与 Step 3/4 阶段一致，登记为流程事实而非缺陷）。
- **P2-1（文档规范）**：`路径归属矩阵-v1.4.6.md` 未按《需求文档标准化编写规则》§二提供"文档元信息（版本、状态、作者、修订历史）"。建议补 `文档版本/状态/生成人` 与修订历史段（保留"脚本生成、禁人工转写"声明），或将其明确登记为**产物型附件**（在文档地图索引中标注"非受控文档"）。

---

## 2. ② API 契约合规（OpenAPI ↔ 设计文档 §3.3/§3.4/§5）

**执行命令**

```powershell
python 'c:\Users\jerry\.trae-cn\work\6a8c5d08e67967d7e6726b59\contract_check.py'      # → compliance-contract.json
python 'c:\Users\jerry\.trae-cn\work\6a8c5d08e67967d7e6726b59\export_headers.py'      # → compliance-export-headers.json
python 'c:\Users\jerry\.trae-cn\work\6a8c5d08e67967d7e6726b59\compliance_supplementary.py'  # → compliance-supplementary.json
```

### 2.1 OpenAPI 结构（`GET /openapi.json`）

| 端点 | OpenAPI 声明 | 设计文档 | 结论 |
|------|--------------|----------|:----:|
| `/api/v1/logs/search` | `GET` | §3.1 GET | ✅ |
| `/api/v1/logs/facets` | `GET` | §3.2 GET | ✅ |
| `/api/v1/logs/facets/presets` | `GET` | §3.2（`facets` 族） | ✅ |
| `/api/v1/logs/export` | `GET` | §3.3 GET | ✅ |
| `/api/v1/modules` | `GET` | UI/模块注册表读接口 | ✅ |
| `/api/v1/modules/{module_id}` | `GET` + `PATCH` | §3.4 PATCH | ✅ |

| 项 | 实测 | 判定 |
|----|------|:----:|
| `search` 查询参数名 | `source, module, operation, result, operator, q, from, to, case_id, run_id, step_id, page, page_size` —— 与 §3.1 参数表**逐项一致** | ✅ |
| `export` 查询参数名 | 同集合（去掉 `page/page_size`）+ `format` | ✅ |
| `PATCH` 请求体 | `#/components/schemas/ModuleStatusRequest`，`required: true` | ✅ |
| 错误响应体 | 运行时统一为 `{code, message, detail, request_id}`（实测 401/403/404/422/400/503 全部符合）；404 一类经中间件/路由兜底时为 `{"code":"404","message":"Not Found"}`（FastAPI 默认，非项目统一体） | ⚠️ 见 P2-3 |
| OpenAPI `info.version` | **`1.0.0`**（= `openbase.__version__`），非 `v1.4.6` | ❌ 见 P2-2 |
| `components.securitySchemes` | **缺失**（未声明 Bearer JWT 鉴权方案） | ❌ 见 P2-2 |
| `search` 响应码声明 | 仅 `200` / `422`（未声明 401/403/400/503，与 §5 错误码表不对齐） | ❌ 见 P2-2 |
| 路径参数名 | `module_id`（设计文档写作 `{id}`） | ⚠️ 见 P2-3 |

### 2.2 §3.3 导出契约（逐项实测）

| 契约点（设计原文） | 实测 | 判定 |
|--------------------|------|:----:|
| `Content-Type: text/csv; charset=utf-8` | `text/csv; charset=utf-8` | ✅ |
| `Content-Type: application/json`（json） | `application/json` | ✅ |
| `Content-Disposition: attachment; filename="logs-<source>-<ts>.<ext>"` | `attachment; filename="logs-l1_file-20260915-223228.csv"` / `…20260915-223249.json`（正则校验通过） | ✅ |
| `<ts>` = `YYYYMMDD-HHMMSS` 本地时区、ASCII、可排序 | 与请求时刻本地时间一致（22:32:28 / 22:32:49，系统本地 +08:00） | ✅ |
| CSV 首字节 `\ufeff` BOM | `first_bytes = efbbbf74732c736f7572…` | ✅ |
| JSON **无** BOM | `first_bytes = 5b7b22747322…`（`[{`） | ✅ |
| CSV 表头/列与 §2 一致 | `ts,source,module,operation,result,request_id,method,path,status_code,duration_ms,operator_id,tenant_id,ip_address,case_id,step_id,run_id,action,summary`（`CSV_COLUMNS` 18 列） | ✅ |
| `summary` 紧凑 JSON 字符串 | `json.dumps(..., separators=(",", ":"))`（代码级核对） | ✅ |
| 命中 >10000 → 400 `PARAM_400` + `detail={matched,limit}` | `{"code":"PARAM_400","message":"export matched rows exceed limit: matched=50000, limit=10000","detail":{"matched":50000,"limit":10000}}` | ✅ |
| 每次导出写 1 条 `audit_logs(action=log.export)`，`detail={actor,source,filters,row_count,format}`，不记录导出内容 | 实测 `{"actor":"1","source":"l1_file","filters":{},"row_count":4,"format":"json"}`；全表无检索关键字 | ✅ |
| 留痕失败不影响导出（降级） | 代码路径 `record_export_audit` 捕获异常 → `WARN` 后继续返回文件（本次未构造 DB 写入异常场景，登记为未覆盖） | ⚪ 未覆盖 |
| 留痕通道显式关闭 → 503 `BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE` | 8023 实例实测 `{"code":"BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE","message":"log export rejected: audit trail unavailable","detail":{"reason":"audit persist disabled"}}` | ✅ |
| 导出流式写（`StreamingResponse`，非功能 §2） | **未实现**：`io.StringIO` 全量拼接 + 普通 `Response`（`logs/service.py:334-345`、`logs/router.py:98-102`） | ❌ 见 P2-4 |

### 2.3 §3.4 模块开关契约（逐项实测）

| 契约点 | 实测 | 判定 |
|--------|------|:----:|
| 权限 `module:manage`，无权限 403 | viewer / 仅 `log:read` 令牌 → 403 `missing permission: module:manage` | ✅ |
| 请求体 `{"status":"enabled"\|"disabled"}`，非法 → 400 | 非法值 `hacked` → **422** `PARAM_422`（设计写 400 `PARAM_400`） | ❌ 见 P2-3 |
| 响应 200 含 `id/status/previous_status/effective=next_login/request_id` | `{"id":"openllm","status":"enabled","previous_status":"enabled","effective":"next_login","request_id":"req-9bdb11c33c0c"}` | ✅ |
| 幂等：目标状态与当前相同 → 200 且不重复留痕 | 200 + `previous_status == status`；`dynamic_modules` 无新增行，`module.switch` 留痕条数不变 | ✅ |
| 留痕失败处置 = 变更失败并回滚（fail-closed） | 8023（`OPENBASE_AUDIT_DB_PERSIST=0`）→ 503 `BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE`，`dynamic_modules` 前后均为空 | ✅ |
| 留痕 `detail={operator_id,module_id,previous_status,status}` | `{"operator_id":"1","module_id":"memory","previous_status":"enabled","status":"disabled"}` | ✅ |
| 状态持久化 `dynamic_modules`（幂等 upsert），读优先 DB | 变更后 DB 出现 `memory=disabled` 行；`GET /api/v1/modules` 回读为改动后状态 | ✅ |
| 语义不变（不动 `id/route_prefix/permission`） | 注册表 5 项 `id/route_prefix/permission` 与出厂值一致 | ✅ |
| 模块不存在 → 404 | `PATCH /api/v1/modules/not-a-module` → 404 `{"code":"PARAM_404","message":"module not found","detail":{"module_id":"not-a-module","allowed":[…]}}`；同条件 `GET` → 404 **`BIZ_404`** | ⚠️ 见 P2-3（同语义双错误码） |

### 2.4 §5 错误码与参数边界

| 场景 | 设计 | 实测 | 判定 |
|------|------|------|:----:|
| 无令牌 | 401 `AUTH_*` | 401 `AUTH_401` | ✅ |
| 无权限 | 403 `PERM_*` | 403 **`AUTH_403`**（message 正确） | ⚠️ 前缀与设计"PERM"不符，见 P2-3 |
| `source` 非法 | 400 `PARAM_400` | **422** `PARAM_422` | ❌ P2-3 |
| `page_size > 100` | 400 | **422** `PARAM_422`（`less_than_equal`） | ❌ P2-3 |
| `page < 1` | — | **422** `PARAM_422` | ⚠️ P2-3（同类） |
| `q` 长度 > 200 | 400（约束 ≤200） | **422** `PARAM_422`（`string_too_long`） | ⚠️ P2-3 |
| 缺 `source` | 必需 | **422** `PARAM_422` | ✅（语义正确） |
| `from > to` | **400** | **200** + `{"items":[],"total":0}` | ❌ 见 P2-5 |
| 留痕不可用 | 503 `BIZ_*_AUDIT_UNAVAILABLE` | 503 `BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE` / `BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE` | ✅ |
| 响应 200 数据体（§3.1） | `{items,total,page,page_size,**source**,truncated}` | `data` 键 = `{items,page,page_size,total,truncated}` → **缺 `source`** | ❌ P2-6 |
| 响应 200 数据体（§3.2 facets） | `{source,module,operation,result,operator,truncated}` | `data` 键 = `{module,operation,operator,result}` → **缺 `source`/`truncated`** | ❌ P2-6 |
| 成功响应包体形态（设计 §内文："成功端点直接返回业务对象"） | 扁平业务对象 | 全站为 `{code,message,data}` 信封（前端 `http.ts` 亦按 `data.data` 解包） | ⚠️ 文档与实现口径不一致，见 P2-6 |
| facets 计数一致性（AC-146-02-4） | 各维度计数和 = search `total` | 四维计数和均 = **50000** = search `total`（50000） | ✅ |
| 分页一致性（AC-146-04-2） | 跨页不重不漏 | page1/page2/page3 `request_id` **交集为空**；深页（page=99999）→ `items=[]` | ✅ |
| `truncated` 语义（≤2 分片 / ≤200,000 行） | 触顶 200 + `truncated=true` | 201k 分片 → `{"total":200000,"truncated":true}`；50k 分片 → `truncated:false` | ✅ |

> **后续处置（2026-09-16，本报告出具后）**：本节 P2-3 所列「参数校验 422 `PARAM_422` vs 设计 400 `PARAM_400`」与 P2-5「`from > to` 未拒绝」已由人工裁定**改实现对齐设计**并落地——参数校验统一 **400 `PARAM_400`**、时间窗与时间格式非法均显式 400（详见 `doc/test/OpenBase-测试报告-v1.4.6.md` §9.2、`doc/operation/OpenBase-问题跟踪记录-v1.4.6.md` §3.5）。**本报告 §2.3/§2.4 的实测记录保持原样，仅代表报告出具时的状态。** 其余 P2-3 同族项（404 双错误码 `PARAM_404`/`BIZ_404`、403 前缀 `AUTH_403` vs 设计 `PERM_*`、路径参数名 `module_id` vs `{id}`）仍登记待裁定。

---

## 3. ③ 敏感配置不入库

**执行命令**

```powershell
git ls-files | Select-String -Pattern '\.env|\.pem|\.key|secrets|id_rsa'
git status --short
```

| 检查项 | 实测 | 判定 |
|--------|------|:----:|
| 受控文件总数 | 1,077 | — |
| 受控 `.env*` 文件数 | **0**（`tracked_env_files: []`） | ✅ |
| 受控密钥文件（`*.pem` / `*.key` / `secrets.*` / `*/keys/*` / `*.p12` / `*.jks`） | **0** | ✅ |
| 磁盘上存在的敏感配置（未受控） | `.env`（2,860 B）、`.env.shared-infra`（4,757 B） | ✅ 均未入库 |
| `.gitignore` 覆盖 | `.env` ✅ / `.env.*` ✅ / `*.pem` ✅ / `*.key` ✅ / `secrets.*` ✅ / `.ssh/` ✅（另有 `.runtime/`、`scripts/oidc-idp/keys/`、`/logs/`、`dist/` 等） | ✅ |
| 工作区洁净度（禁止改动源码/测试的合规证据） | `git status --short` → 仅 `?? doc/test/evidence/v146/`（本次新增证据目录），**无任何已跟踪文件被修改** | ✅ |

> 说明：本次测试全程未修改仓库源码与测试文件；`.env` 中的 JWT 密钥仅在本地用于签发测试令牌，报告中未回显该密钥明文。

---

## 4. ④ 依赖许可与版本锁定

| 检查项 | 实测 | 判定 |
|--------|------|:----:|
| 前端锁定文件 | `openbase-ui/package-lock.json` **已入库**（246,773 B，`lockfileVersion: 3`，`packages: 518`） | ✅ |
| 前端声明 | `package.json` `version: 1.3.0`；`dependencies` 8 项（axios/vue/vue-router/pinia/element-plus/echarts/d3/@element-plus/icons-vue）；`devDependencies` 15 项 | ✅ |
| 前端版本运算符 | 全部为 `^x.y.z`（由 lock 文件兜底精确版本） | ✅ |
| Python 依赖清单 | `pyproject.toml` `dependencies` 16 项：`fastapi>=0.110`、`uvicorn[standard]>=0.29`、`sqlalchemy[asyncio]>=2.0`、`asyncpg>=0.29`、`alembic>=1.13`、`redis>=5.0`、`pydantic>=2.6`、`pydantic-settings>=2.2`、`python-jose[cryptography]>=3.3`、`passlib[bcrypt]>=1.7`、`python-multipart>=0.0.9`、`apscheduler>=3.10`、`fastmcp>=1.0`、`opentelemetry-api>=1.24`、`opentelemetry-sdk>=1.24`、`opentelemetry-exporter-otlp-proto-http>=1.24` | ⚠️ 见 P2-7 |
| Python 锁定文件 | **不存在**（无 `requirements*.txt` / `poetry.lock` / `uv.lock` / `Pipfile.lock`，`git ls-files` 无命中） | ❌ 见 P2-7 |
| 依赖许可（前端 node_modules 顶层 261 个包） | MIT 175、ISC 51、BSD-3-Clause 11、BSD-2-Clause 9、Apache-2.0 7、BlueOak-1.0.0 4、Python-2.0 1、Unlicense 1、0BSD 1、(MIT OR CC0-1.0) 1 | ✅ **无 GPL/AGPL/LGPL 等传染性许可** |
| 仓库根许可文件 | `LICENSE` / `LICENSE.md` **不存在**（`package.json` 标 `"private": true`） | ⚠️ 见 P2-8 |

---

## 5. 结果汇总

| 序 | 合规维度 | 检查项 | 通过 | 不通过/待办 |
|:--:|----------|-------:|-----:|-------------|
| ① | 文档与版本一致性 | 18（存在性 3 目录 + 17 份文档头/修订历史） | 17 | 1（P2-1 路径归属矩阵缺元信息） |
| ② | API 契约（OpenAPI + §3.3/§3.4/§5） | 43 | 35 | 8（P2-2~P2-6） |
| ③ | 敏感配置不入库 | 5 | **5** | 0 |
| ④ | 依赖许可与版本锁定 | 8 | 5 | 3（P2-7 / P2-8 / 许可无传染性为通过） |
| — | **合计** | **74** | **62** | **12** |

---

## 6. 问题清单

| ID | 级别 | 类型 | 内容 | 建议 |
|----|:----:|------|------|------|
| C-P2-1 | P2 | 文档规范 | `路径归属矩阵-v1.4.6.md` 缺"文档版本/状态/修订历史"（脚本生成物） | 补元信息与修订历史，或在文档地图索引中登记为"非受控产物型附件" |
| C-P2-2 | P2 | 契约完备性 | OpenAPI `info.version = 1.0.0`（非 v1.4.6）；**未声明 `securitySchemes`（Bearer JWT）**；`/logs/search` 仅声明 200/422，未声明 401/403/400/503（与 §5 错误码表不对齐） | ① 版本号与发布版本联动（`init_app` 传入 `Settings.app_version`）；② 补 `HTTPBearer` 安全方案与 `responses` 错误码声明；③ 便于外部对接方按 OpenAPI 直接对接与对账 |
| C-P2-3 | P2 | 契约一致性 | 参数/枚举校验返回 **422 `PARAM_422`**（设计写 400 `PARAM_400`）；403 使用 **`AUTH_403`**（设计写 `PERM_*`）；同一"模块不存在"出现 **`PARAM_404`（PATCH）与 `BIZ_404`（GET）** 两种码；FastAPI 兜底 404 返回非统一错误体；路径参数名 `module_id` vs 设计 `{id}` | 与 RS-146-01 一并裁定：统一 400/422 口径、统一 403 前缀为 `PERM_`、同语义统一错误码、404 兜底纳入统一错误体；裁定后**回写 API 设计文档 §3.1/§3.4/§5** |
| C-P2-4 | P2 | 非功能契约 | 设计要求导出**流式写**（`StreamingResponse`），实现为内存整体拼接 + 普通 `Response` | 改 `StreamingResponse`（生成器逐行 `yield`），顺带降低大导出内存占用 |
| C-P2-5 | P2 | 契约一致性 | `from > to` 设计要求 **400**，实测 **200**（空结果），无参数关系校验 | 在 `LogQueryParams` 增加模型级校验（`from <= to`，否则 `PARAM_400`），并补回归用例 |
| C-P2-6 | P2 | 契约一致性 | 成功响应体：`search` 缺 `source`；`facets` 缺 `source` 与 `truncated`（均在设计 §3.1/§3.2 明列）；成功体采用 `{code,message,data}` 信封而设计文档写"成功端点直接返回业务对象" | 二选一：① 实现补齐 `source`/`truncated` 字段并**修订设计文档**写明信封口径（推荐，因前端 `http.ts` 已按 `data.data` 解包）；② 若坚持扁平体则需前后端同步改造 |
| C-P2-7 | P2 | 版本锁定 | Python 侧仅有下限约束（16 项全为 `>=`）且**无锁定文件**，依赖不可复现 | 生成 `requirements.lock`（`uv pip compile` / `pip-compile`）或以 `pyproject` + `uv.lock` 固定；CI 中校验锁文件与安装一致 |
| C-P2-8 | P2 | 许可合规 | 仓库根无 `LICENSE` 文件（私有仓库，非阻塞）；前端仅扫描 `node_modules` 顶层许可字段，未做逐文件许可文本与传递依赖许可清单 | 如需内部合规台账，补充 `license-checker`/`pip-licenses` 报告并归档至 `doc/`；私有仓库可显式声明"内部使用" |

> 说明：以上均为 **P2（不阻塞验收，建议随 v1.4.6 出清或登记为债务）**；未发现 P0/P1 级合规问题（敏感配置入库、许可传染风险两项**均为 0 命中**）。

---

## 7. 未执行 / 受限项与补救计划

| 项 | 状态 | 原因 | 补救计划 |
|----|------|------|----------|
| Python 依赖 CVE 与许可清单（`pip-audit` / `pip-licenses`） | 未执行 | 环境未安装 `pip_audit`（不联网安装） | 见《security-report.md》§9 |
| 前端 devDependencies 许可/漏洞 | 未执行 | 任务口径限定 `--omit=dev` | 追加 `npm audit --json`（全量）与 `license-checker --json` |
| 导出留痕失败降级路径（DB 写入异常） | 未执行 | 未构造"通道可用但落库异常"场景（需注入 DB 故障） | 用 toxiproxy/停库方式构造，或在单测层以 monkeypatch 覆盖并登记 |
| 四仓（跨仓）契约合规（BL-146-16~20） | 未执行 | 四仓未启动、跨仓产物不在本仓范围（需求 §11.1 明确"本仓不代改他仓"） | 联调窗口按 AC-146-16-1/20-1 逐仓验收 |
| 合规文档与仓库对账（文档地图索引一致性） | 未执行 | 本次抽检 17 份 v1.4.6 文档；全量文档地图对账属 `verify-env` 门禁范围 | 由 S7/门禁脚本补充（已有 `doc/shr/doc-map/orphan-check.json` 证据） |

---

## 8. 结论

1. **敏感配置与工作区纪律合规（唯一全绿维度）**：`git ls-files` 中 `.env*` 与密钥类文件均为 **0**；`.gitignore` 6 项模式全覆盖；本次测试未修改仓库任何受控文件（工作区仅新增 `doc/test/evidence/v146/**`）。
2. **文档体系完整**：v1.4.6 在 `requirements/design/development` 三目录齐备（5/8/4 = 17 份），文档头版本号与修订历史底部版本号 **16/17 一致**，唯一偏差为脚本生成的路径归属矩阵缺元信息。
3. **API 契约主体合规**：OpenAPI 端点/方法/参数名与设计一致；导出契约（Content-Type、文件名与时间戳格式、CSV BOM、JSON 无 BOM、列序、10000 上限 `detail={matched,limit}`）、模块开关契约（幂等不重复留痕、先留痕后生效 fail-closed、状态持久化、语义不变）与错误体 `{code,message,detail,request_id}` **逐项实测符合**；facets 计数一致性与跨页不重不漏两项审计互证口径成立。
4. **8 项 P2 契约/文档偏差**已逐条登记（含 `source`/`truncated` 字段缺失、400↔422 与 403 前缀、`from>to` 未校验、导出未流式、OpenAPI 版本与安全方案缺失、Python 无锁文件），其中多项与本仓既有《代码逻辑审查记录-v1.4.6》§8 RS-146-01 重合，建议**一并裁定并回写设计文档**后关闭。
5. 依赖许可层面**无传染性许可风险**；前端锁定文件齐备，Python 侧锁定缺失为主要可复现性缺口。

---

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-15 | SE-OpenBase-Test / AT-OpenBase-Test | 初始版本：四维合规核对（文档一致性 18 项、API 契约 43 项、敏感配置 5 项、依赖许可 8 项，合计 74 项 / 通过 62 项）；登记 P2 问题 8 项与未执行项 5 项；证据 `compliance-raw.json`、`compliance-contract.json`、`compliance-export-headers.json`、`compliance-supplementary.json` |

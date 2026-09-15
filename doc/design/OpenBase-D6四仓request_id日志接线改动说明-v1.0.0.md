# OpenBase-D6四仓request_id日志接线改动说明-v1.0.0

## 文档元信息

| 项 | 内容 |
|------|-----|
| 文档编号 | OB-DESIGN-D6-CROSSREPO-LOG-v1.0.0 |
| 版本 | v1.1.0 |
| 状态 | [Draft]（跨仓施工依据，各仓按自身流程评审后实施）· **本说明已纳入 v1.4.6 版本次范围（VC-014 / BL-146-16，Phase 6；2026-09-15 裁决）** |
| 作者 | AI（S7 批次 35 跨仓施工说明会话） |
| 日期 | 2026-09-13 |
| 适用范围 | **DPS / OpenLLM / OpenMemory / OpenRAG 四仓**（OpenBase 侧不含实施项） |
| 上游依据 | 《OpenBase-人工端到端测试日志记录方案-v1.0.0》**v1.1.0** §11.8（实测核实）与 §9.1（**D-6 = ②：推动四仓补齐 request_id 接线**）；《OpenBase-文档地图索引-v1.0.0》（v1.0.9） |
| 性质 | 跨仓施工说明（非本仓代码改动单）；各仓独立评审、独立提交 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-13 | AI（S7 批次 35） | 初始版本：四仓现状实证 + 统一约定 + 逐仓改动（含可直接粘贴的代码片段与验证方法）+ 验收标准 + 改动一览 + 风险与未决项 |
| v1.1.0 | 2026-09-15 | PM-OpenBase-Dev | **版本归属登记（VC-014）**：用户裁决"把日志相关功能调整都放到一个版本里"→ **本说明纳入 v1.4.6**，落为 **BL-146-16**（P0，Phase 6），并与 **BL-146-17（四仓 JSONL 结构化）同批施工**；**本次不改动本说明的施工内容**（§2 统一约定 / §3 逐仓改动 / §4 验收标准 / §5 改动一览 原文未变），仅登记归属并新增状态注记。配套评估见《OpenBase-R384-四仓日志接入可行性粗筛与D6施工量评估》v1.1.0（D-6 本体 ≈4.2 人天；跨仓流程成本约占 73%） |

---

## §1 背景与目标

### 1.1 背景（实测结论，来自 §11.8）

四仓的日志**都能被编排器重定向捕获**（前提 1 四仓 PASS），但**日志里都没有 `request_id`**（前提 2 四仓均未打通）：

| 仓 | 现状（实证） |
|----|-------------|
| DPS | `identity/request_id.py` 的 contextvar 已在 `identity_gate_middleware.py:109` 写入，但**全仓无任何 Filter/Formatter/`extra=` 消费它**（`get_current_request_id()` 零调用）→ 形态上是**死接线** |
| OpenLLM | `app/identity/audit_identity.py:112-129` 的 `identity_log_extra()` **已产出 `request_id`**，但只塞进审计 DB（`app/middleware/audit.py:320-327`），从未传给 `logger.*(extra=…)` |
| OpenMemory | `utils/struct_logger.py` 具备 JSON formatter 且从 contextvars 取 `request_id`；`api/middleware/structured_log.py:144-197` **已组装** `request_id`/`status_code`/`elapsed_ms`，但 `:26` 用的是标准 `logging.getLogger` → `extra` 被根 logger 的纯文本 formatter **丢弃** |
| OpenRAG | 全仓 `request_id`/`X-Request-Id` **零匹配**（其相关性 ID 走 `X-Correlation-ID`）；`observability/logging.py:366` 的 `LoggingMiddleware` **定义但从未注册**（`main.py:75-89` 只注册 CORS + Prometheus） |

**共同特征：四仓的状态码/耗时其实都已采集**（指标 / 审计表 / 中间件组装），只差"送进日志"这一步——因此本说明的改动量都很小。

### 1.2 目标

1. 四仓**请求日志携带 `request_id`**，且取值与网关出站头 `X-Request-Id` **完全一致**（可串联）；
2. 人工排查时，可按同一个 `request_id` 从网关追进子系统内部日志；
3. 改动**不改变**各仓日志输出流（仍写原 stdout/stderr，保证被 OpenBase 编排器捕获）。

### 1.3 非目标与边界

- 不改接口契约、不改鉴权语义、不新增第三方依赖；
- 不改既有日志的**语义**（只增字段，不删不弱化）；
- 不替代各仓的可观测性建设（本说明只解决 `request_id` 串联）；
- OpenBase 侧**不代改**他仓代码。

---

## §2 统一约定（四仓一致，强制）

| 项 | 约定 |
|----|------|
| 头名 | `X-Request-Id`（与 OpenBase 协议头规范一致） |
| 取值语义 | **受信来源透传复用**；**非受信来源携带则忽略并本地重新生成** `req-{12hex}`（防伪造串联） |
| 日志字段名 | 统一 `request_id`（JSON key 与 format 占位符同名） |
| 兜底 | 无上下文路径（豁免/健康检查/非请求上下文）**一律输出 `"-"`**，禁止出现 `KeyError` |
| 输出流 | 维持现状（DPS/OpenLLM/OpenMemory → stderr；OpenRAG → stdout），不得改为仅落自有文件 |
| 级别 | 沿用各仓现有级别开关，不新增 |
| 禁止 | 不记录令牌/密码/密钥/完整请求体；沿用各仓既有脱敏逻辑 |

---

## §3 逐仓改动

### 3.1 DPS（改动量最小：+10/-1 行）

**现状证据**：`src/main.py:36-41` 的 `basicConfig(level=…, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")`；`src/identity/request_id.py:14-33` 已有 `get_current_request_id()`。

**改动（`src/main.py`）**：

```python
# src/main.py —— 在 logging.basicConfig 之前
from identity.request_id import get_current_request_id


class RequestIdFilter(logging.Filter):
    """把 contextvar 中的 request_id 注入日志记录；无上下文时输出 "-"。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_current_request_id() or "-"
        return True


logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
)
logging.getLogger().addFilter(RequestIdFilter())
```

**注意**：
- 必须用 `addFilter` 挂到 **root logger**（`basicConfig` 只建 handler，不装 filter）；
- 豁免路径（`EXEMPT_PATHS`）不写 contextvar → 由 `"-"` 兜底，**不要**改成 `record.request_id` 缺省不设，否则 format 会抛 `KeyError`。

**验证**：带 `X-Proxy-Source: openbase-dps-proxy` + `X-Request-Id: req-abc123456789` 请求 → 日志行含 `[req-abc123456789]`；匿名请求 → 含 `[-]`。
**单测**：`RequestIdFilter` 取值/兜底二分（有 contextvar / 无 contextvar）。

### 3.2 OpenLLM（+10/-2 行）

**现状证据**：`backend/main.py:79-84` 用 `format=settings.LOG_FORMAT`；`backend/app/core/config.py:180-184`（`LOG_FORMAT` 不含 `request_id`）；`backend/app/identity/request_id.py:12-29` 已有 `get_current_request_id()`；`backend/app/identity/audit_identity.py:112-129` 已产出 `request_id`（当前只进审计 DB）。

**改动**：

```python
# backend/main.py —— 在 logging.basicConfig 之前
from app.identity.request_id import get_current_request_id


class RequestIdFilter(logging.Filter):
    """把 contextvar 中的 request_id 注入日志记录；无上下文时输出 "-"。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_current_request_id() or "-"
        return True


logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
)
logging.getLogger().addFilter(RequestIdFilter())
```

```python
# backend/app/core/config.py:182 —— 默认值追加 request_id 占位符
LOG_FORMAT = "%(asctime)s - [%(request_id)s] - %(name)s - %(levelname)s - %(message)s"
```

**注意**：`LOG_FORMAT` 是配置项，若环境变量已显式设置旧格式，需同步更新部署侧配置，否则新字段不会显示（**两侧必须一致**）。
**验证/单测**：同 §3.1。

### 3.3 OpenMemory（最小改动，但有循环导入风险）

**现状证据**：`api/middleware/structured_log.py:26` 为标准 `logging.getLogger(__name__)`；同文件 `:31-45` 定义 `request_id_ctx` 等；`utils/struct_logger.py:56-69` **从该中间件模块导入同一组 ContextVar 实例**（`try: from openmemory.api.middleware.structured_log import request_id_ctx, …`），因此可确认二者**是同一对象**；`struct_logger.py:182-198` 的 JSON formatter 会输出 `request_id`/`trace_id`/`service`/`env`。

**改动（方案 A，推荐）**：让 emit 点走结构化门面。

```python
# api/middleware/structured_log.py —— 删除顶部 logger = logging.getLogger(__name__)
# 改为延迟导入，避免与 struct_logger 顶部 import 形成循环依赖
def _structured_logger():
    """延迟获取结构化 logger（避免模块级循环导入）。"""
    from openmemory.utils.struct_logger import get_logger

    return get_logger(__name__)
```

调用点由 `logger.info("access_log", extra={"structured": log_entry})` 调整为结构化门面入参形式（`get_logger` 返回的 `StructLogger` 以 **kwargs 接收字段）。

**实施时须核对（不得凭猜）**：`StructLogger._log()` 对 kwargs 的处理方式（是否注入 `extra`、是否与 `extra["structured"]` 合并），据此决定调用点写法；`struct_logger.py:211-212` 附近有对应合并逻辑。

**改动（方案 B，备选）**：在 `api/server.py:788` 用 `dictConfig` 给根 logger 装载 `JSONFormatter`（替代纯文本 format），并确保 `create_app` 启动路径也会执行到日志配置。方案 B 会改变**全部**日志格式（符合"结构化 JSON"标准），但影响面大于方案 A。

**现有隐患（一并处理）**：`basicConfig` 只在 `main()` 内 → 若以 `uvicorn openmemory.api.server:create_app` 启动，根 logger 不被配置。**请先核实编排器/部署的实际启动命令**，再决定是否需要把配置移到模块级或 `create_app` 内。

**验证**：访问任一接口 → stderr 出现 JSON 行，且含 `"request_id": "req-…"`。

### 3.4 OpenRAG（改动最大：需启用一个从未注册的中间件）

**现状证据**：`src/openrag/observability/logging.py:366-403` 定义了 `LoggingMiddleware`（读 `X-Correlation-ID`/`X-Trace-ID`/`X-Span-ID`，打 `request_started`），`:418-424` 有 `request_completed` 记录 `status_code`+`duration_ms`；`src/openrag/main.py:75-89` **只注册** `CORSMiddleware` 与 `PrometheusMiddleware`；实际运行的日志配置在 `repository/config/logging.py:58-63`（`StreamHandler(sys.stdout)`），**未使用** `observability/logging.py`。

**改动 1：注册中间件（`src/openrag/main.py`，放在 Prometheus 之后）**

```python
# src/openrag/main.py —— 与 Prometheus 中间件同风格注册
try:
    from openrag.observability.logging import LoggingMiddleware
    # add_middleware 后注册者位于外层，放在此处可确保覆盖全部请求
    app.add_middleware(LoggingMiddleware, service_name="openrag")
except ImportError:
    logger.warning("Logging 中间件未安装，跳过")
```

**改动 2：补 `X-Request-Id` 受信透传（`observability/logging.py` 的 `__call__`，与 `X-Correlation-ID` 处理并列）**

```python
# observability/logging.py:384-389 附近，紧随 correlation id 处理之后
rid = request.headers.get("X-Request-Id")
if rid and _is_trusted_source(request):          # 受信判定沿用本仓既有代理来源校验
    set_request_id(rid)                           # 写入本仓 request_id 上下文（新增）
elif rid:
    # 非受信来源携带 → 忽略并本地重新生成，防伪造串联
    set_request_id(generate_request_id())
```

**改动 3（可选）**：`repository/config/logging.py:58-63` 的文本 formatter 增加 `request_id` 占位符——**仅当**最终确认请求日志走该栈输出时才需要；否则会出现两套日志栈（`observability` vs `config`）重复输出，**建议统一为其中一套**。

**验证**：经网关 `rag-proxy` 调用 → OpenRAG 日志中 `request_id` 与网关日志一致；直连（非受信）携带伪造头 → 生成新的 `req-{12hex}`。
**单测**：受信透传 / 非受信忽略重生成 两分支（本仓已有同类测试范式：`tests/unit/test_s3_t7_audit_identity.py` 的 request_id 用例可参照）。

---

## §4 验收标准（四仓统一）

| 类别 | 标准 | 判定方式 |
|------|------|---------|
| **串联一致性** | 同一请求在网关日志与子系统日志中的 `request_id` **完全一致** | 取响应头 `X-Request-Id`，两侧 grep 比对 |
| **兜底健壮** | 无上下文/豁免/健康检查路径不抛 `KeyError`，输出 `"-"` 或 `null` | 单测 + 匿名请求实测 |
| **输出流不变** | 日志仍写原 stdout/stderr（可被编排器捕获） | 重定向验证 |
| **回归** | 各仓既有测试全通过 | 各仓测试命令 |
| **覆盖率** | 新增代码满足各仓自身覆盖率要求 | 各仓覆盖率报告 |
| **安全** | 不新增敏感字段输出（token/密码/完整请求体） | 单测 + 日志扫描 |

---

## §5 四仓改动一览

| 仓 | 改动文件 | 性质 | 预估行数 | 风险 |
|----|---------|------|---------|------|
| **DPS** | `src/main.py` | 修改 | +10 / -1 | 低（format 变更影响所有日志行） |
| **OpenLLM** | `backend/main.py`、`backend/app/core/config.py` | 修改 | +10 / -2 | 低（`LOG_FORMAT` 默认值与部署侧配置需同步） |
| **OpenMemory** | `api/middleware/structured_log.py`（+ 视情况 `api/server.py`） | 修改 | +3 ~ +15 | **中**（循环导入；`StructLogger` kwargs 形态；启动路径） |
| **OpenRAG** | `src/openrag/main.py`、`src/openrag/observability/logging.py`（+ 可选 `repository/config/logging.py`） | 修改 | +15 ~ +40 | **中**（首次启用请求日志中间件→日志量上升；两套日志栈需统一） |

**合计**：4 仓、7 个文件、约 +38 ~ +67 行；无新增依赖、无接口变更。

---

## §6 与 OpenBase 侧的对接点与时序

| 项 | 说明 |
|----|------|
| 出站头已就绪 | OpenBase 代理出站经 `openbase/modules/protocol_headers/inject.py` 装配 `X-Request-Id`（取值优先级：显式传入 > `request.state.request_id` > 新生成）——四仓**无需等 OpenBase 改动**即可接收该头 |
| 采集依赖 | 四仓日志要被自动收集到 `logs/<service>/`，依赖 OpenBase 侧 **C-6（编排器重定向）** 落地；在此之前四仓日志仍可在各自控制台/自有落点查看 |
| 时序 | 按 **D-6 决议**：四仓改动**不阻塞** OpenBase 侧批 1/批 2，二者并行；四仓各走自身评审与提交流程 |

---

## §7 风险与未决项

| # | 风险/未决 | 处置 |
|---|----------|------|
| R-1 | **OpenMemory 循环导入**：`struct_logger` 顶部从中间件导入 ContextVar，若中间件在顶部反向导入 `struct_logger` 会成环 | 采用 §3.3 的**延迟导入**写法（函数内 import），并加导入顺序单测 |
| R-2 | **OpenMemory 启动路径**：`basicConfig` 仅在 `main()` | 实施前核实实际启动命令；必要时把配置移到模块级/`create_app` |
| R-3 | **OpenRAG 两套日志栈并存**（`observability/logging.py` vs `repository/config/logging.py`） | 实施时统一为一套，避免双 handler 重复输出 |
| R-4 | **OpenRAG 启用中间件后日志量上升** | 保持 `log_request_body=False`/`log_response_body=False` 默认；必要时按各级别采样 |
| R-5 | **DPS/OpenLLM format 变更影响既有人工 grep 习惯** | 在各自运行手册登记新格式样例 |
| R-6 | 受信来源判定口径各仓不一 | 以 OpenBase 协议头规范为准（受信代理来源透传、非受信忽略重生成），各仓沿用自身既有校验实现 |
| R-7 | `request_id` → 与网关串联依赖"网关出站透传 + 子系统受信复用"两端一致 | 验收用同一请求双向比对（§4 串联一致性） |

---

## §8 附录：端到端验证方法（任选一仓先做）

```powershell
# 1) 取网关 request_id（响应头回传）
$resp = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/dps-proxy/reports/overview' `
  -Headers @{ Authorization = "Bearer $env:OPENBASE_ACCESS_TOKEN" }
$rid = $resp.Headers['X-Request-Id']

# 2) 在子系统日志中按同一 request_id 检索（编排器采集后路径如下）
Select-String -Path 'logs/dps/*.log' -Pattern $rid
```

**通过判据**：步骤 2 能命中该 `request_id`，且命中行的状态码/耗时与该次请求实际结果一致。

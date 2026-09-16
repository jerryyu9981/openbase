# OpenBase-R384改动包-v1.0.0

| 项 | 内容 |
|------|------|
| 文档编号 | OB-CHANGESET-R384-CROSSREPO-v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev / AA-OpenBase-Dev |
| 日期 | 2026-09-16 |
| 存放 | doc/planning/ |
| 版本归属 | **v1.4.7**（承接型小版本；BL-147-02 / BL-147-03） |
| 上游依据 | 《OpenBase-R384四仓施工派单-v1.0.0》§6；《OpenBase-D6四仓request_id日志接线改动说明-v1.0.0》§3；**《OpenBase-单版本规划文档-v1.4.7》** |
| 执行方式 | **本会话沙箱禁止写入同级四仓**（实测拒绝），故以"改动包"交付：**在各仓自身对话中按其流程应用**，或在**沙箱外**执行（四仓已有 `*_commit_push.ps1` / `*.bat` 辅助脚本） |

---

## 1. 重要更正：启动路径实测（纠正 D-6 的两处落点）

> 依据 OpenBase 编排器 `scripts/service-orchestrator.ps1` **实测启动命令**（本仓可读，为 6.0 核实项④的实质结论）。

| 仓 | 编排器实际启动 | 日志配置现状 | **D-6 原落点** | **修正后落点** |
|----|---------------|-------------|---------------|---------------|
| **DPS** | `python -m uvicorn rest_api.app:app --app-dir src` | `src/rest_api/app.py:40` 仅 `logger = logging.getLogger(__name__)`，**无日志配置**；`src/main.py:37-40` 的 `basicConfig` **在此路径不执行** | `src/main.py` ❌ | **`src/rest_api/app.py`**（+ 抽公共 `src/logging_setup.py` 供 `main.py` 共用） |
| **OpenLLM** | `python -m uvicorn main:app`（cwd=`backend`） | `backend/main.py:80-83` `basicConfig(format=settings.LOG_FORMAT)` | `backend/main.py` ✅ | **不变**（D-6 方案有效） |
| **OpenMemory** | `python scripts\start_openmemory.py`（→ `create_app()`） | `src/openmemory/api/server.py:788` 的 `basicConfig` **在 `main()` 内，此路径不执行**（与 6.0 核实项①一致） | `api/middleware/structured_log.py`（部分） | **`src/openmemory/api/server.py`（模块级或 `create_app()`）** + `structured_log.py` 门面改造 |
| **OpenRAG** | `python -m uvicorn openrag.main:app --app-dir src` | `src/openrag/main.py:51` `setup_logging(level=..., json_format=settings.is_production)`（**在 lifespan 内**） | `src/openrag/main.py` + `observability/logging.py` ✅ | **不变**；另需 `json_format=True`（采集环境）方为 JSONL |

**结论**：若按 D-6 原落点实施，**DPS 与 OpenMemory 两仓的改动不会生效**（配置不在实际执行路径上）。本改动包已按修正落点给出方案。

## 2. 通用件（四仓复用，建议各自落在本仓 logging 模块内）

> 以下为**完整可用实现**，四仓可原样复用（`service` 传入各自 svc 名）。要点：`RequestIdFilter` 必须挂在 **root logger**；无上下文一律 `"-"`，**不得让 `record.request_id` 缺省不设**（否则 format 抛 `KeyError`）。

```python
# -*- coding: utf-8 -*-
"""R-384 日志接线：request_id 注入 + JSON Lines 输出（BL-147-02 / BL-147-03）。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Callable

_CONFIGURED = False


class RequestIdFilter(logging.Filter):
    """把 request_id 注入日志记录；无上下文（豁免/健康检查/非请求上下文）输出 "-"。"""

    def __init__(self, getter: Callable[[], str | None]) -> None:
        super().__init__()
        self._getter = getter

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            value = self._getter()
        except Exception:  # noqa: BLE001 - 取值失败不得丢日志
            value = None
        record.request_id = value or "-"
        return True


class JsonLineFormatter(logging.Formatter):
    """单行 JSON 输出（字段与 OpenBase LogEntry 可映射集对齐，见施工派单 §5）。"""

    _OPTIONAL_KEYS = (
        "method", "path", "status_code", "duration_ms", "operator_id",
        "tenant_id", "ip", "case_id", "step_id", "run_id", "action", "event",
    )

    def __init__(self, service: str) -> None:
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            # 契约：ts 为 ISO 8601（适配器 _iso 解析，无时区视为 UTC）
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "service": self._service,
            "logger": record.name,
            "message": record.getMessage(),
            # 契约：request_id 必须存在（兜底 "-"）
            "request_id": getattr(record, "request_id", "-"),
        }
        for key in self._OPTIONAL_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(
    service: str,
    level: str = "INFO",
    *,
    get_request_id: Callable[[], str | None],
    json_lines: bool = True,
) -> None:
    """装配日志：root filter（request_id）+ root handler formatter（JSON Lines）。

    - 幂等：重复调用仅生效一次（DPS 的 `app.py` 与 `main.py` 双入口会各调一次）。
    - **输出流不变**：仍为 stderr（DPS/OpenLLM/OpenMemory）/ stdout（OpenRAG）。
    """
    global _CONFIGURED
    logger = logging.getLogger()
    # 幂等挂 filter（root logger 上只挂一次）
    if not any(isinstance(f, RequestIdFilter) for f in logger.filters):
        logger.addFilter(RequestIdFilter(get_request_id))
    if _CONFIGURED:
        return
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    formatter: logging.Formatter = (
        JsonLineFormatter(service) if json_lines
        else logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s"
        )
    )
    handler = logging.StreamHandler()  # 默认 stderr；OpenRAG 传 sys.stdout
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    _CONFIGURED = True
```

> **访问日志说明（重要）**：uvicorn 自身的 `uvicorn.access` 行仍为纯文本——其携带 `ip - - "METHOD /path HTTP/1.1" 200`，**OpenBase 适配器可按"纯文本回退"解析出 `method/path/status_code`**（`_parse_line` 逐行判断 `{` 开头，故**同一文件内 JSON 行与文本行可混存**）。若要求全文件严格 JSONL，需在**采集侧**用 `--log-config` 统一 uvicorn 访问日志格式（属 BL-147-04 范围，见施工派单 §7）。

## 3. DPS 改动（落点已修正）

### 3.1 新增 `src/logging_setup.py`

将 §2 通用件写入该文件，并追加 DPS 专用装配入口：

```python
# src/logging_setup.py —— 末尾追加
from identity.request_id import get_current_request_id  # DPS 既有（src/identity/request_id.py）

SERVICE_NAME = "dps"


def setup_dps_logging(level: str = "INFO", *, json_lines: bool = True) -> None:
    """DPS 日志装配（R-384）：request_id 注入 + JSON Lines。"""
    configure_logging(SERVICE_NAME, level, get_request_id=get_current_request_id, json_lines=json_lines)
```

### 3.2 修改 `src/rest_api/app.py`（**实际生效落点**）

在 `logger = logging.getLogger(__name__)`（实测位于 `:40`）**之后**插入：

```python
# R-384（BL-147-02/03）：日志装配必须在模块导入期执行——编排器实启 `rest_api.app:app`，
# 不经过 src/main.py，故 src/main.py 的 basicConfig 在该路径不生效。
from config import settings as _settings  # 该文件已使用 settings（:355）

from logging_setup import setup_dps_logging

setup_dps_logging(_settings.log_level)
```

> 注意：若 `app.py` 中 `settings` 的导入名不是 `settings`，请沿用该文件既有导入名（实测 `app.py` 使用 `settings`，见 `:355`），避免重复导入别名。

### 3.3 修改 `src/main.py`（开发模式入口，保持一致）

将 `:37-40` 的 `logging.basicConfig(...)` 块替换为：

```python
from logging_setup import setup_dps_logging

setup_dps_logging(settings.log_level)
```

### 3.4 新增单测 `src/tests/test_r384_request_id_filter.py`

```python
# -*- coding: utf-8 -*-
"""R-384/BL-147-02：request_id 注入与 JSON Lines 契约（RED→GREEN）。"""
from __future__ import annotations

import json
import logging

from identity.request_id import set_current_request_id
from logging_setup import JsonLineFormatter, RequestIdFilter, configure_logging


def test_request_id_filter_uses_contextvar_when_present() -> None:
    """有上下文：record.request_id 取 contextvar 值。"""
    set_current_request_id("req-abc123456789")
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", None, None)
    assert RequestIdFilter(
        lambda: "req-abc123456789"
    ).filter(record) is True
    assert record.request_id == "req-abc123456789"


def test_request_id_filter_falls_back_to_dash() -> None:
    """无上下文：兜底为 "-"，且不得抛异常。"""
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", None, None)
    assert RequestIdFilter(lambda: None).filter(record) is True
    assert record.request_id == "-"


def test_request_id_filter_survives_getter_error() -> None:
    """取值异常不得丢日志。"""
    def _boom() -> str | None:
        raise RuntimeError("boom")

    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", None, None)
    assert RequestIdFilter(_boom).filter(record) is True
    assert record.request_id == "-"


def test_json_line_formatter_emits_contract_fields() -> None:
    """JSONL 契约：ts/level/service/request_id 必备，可选字段按 extra 透出。"""
    record = logging.LogRecord("dps.api", logging.INFO, __file__, 1, "ok", None, None)
    record.request_id = "req-abc123456789"
    record.method = "POST"
    record.path = "/api/v2/portrait/list"
    record.status_code = 200
    record.duration_ms = 12

    payload = json.loads(JsonLineFormatter("dps").format(record))

    assert payload["service"] == "dps"
    assert payload["request_id"] == "req-abc123456789"
    assert payload["method"] == "POST"
    assert payload["path"] == "/api/v2/portrait/list"
    assert payload["status_code"] == 200  # 必须为 JSON 数字
    assert isinstance(payload["status_code"], int)
    assert payload["ts"].endswith("Z")


def test_configure_logging_is_idempotent() -> None:
    """双入口（app.py / main.py）重复调用只生效一次。"""
    configure_logging("dps", "INFO", get_request_id=lambda: None, json_lines=True)
    configure_logging("dps", "INFO", get_request_id=lambda: None, json_lines=True)
    root = logging.getLogger()
    assert sum(isinstance(f, RequestIdFilter) for f in root.filters) == 1
```

### 3.5 校验与回归（在 DPS 仓内）

```powershell
cd 'D:\Trae CN\myproject\Dev\DPS'
python -m pytest src/tests/test_r384_request_id_filter.py -p no:randomly   # 新增用例全绿
python -m pytest src/tests -p no:randomly                                  # S5 全组回归
python -m ruff check src
python scripts/k07_endpoint_matrix.py --check
python scripts/smoke_l3_2.py --quick
# 端到端：带 X-Proxy-Source: openbase-dps-proxy + X-Request-Id: req-abc123456789 请求
# → 日志行含 "request_id":"req-abc123456789"；匿名请求 → "request_id":"-"
```

## 4. OpenLLM 改动（落点不变）

### 4.1 新增 `backend/app/core/r384_logging.py`

写入 §2 通用件 + 装配入口：

```python
# backend/app/core/r384_logging.py —— 末尾追加
from app.identity.request_id import get_current_request_id  # 本仓既有

SERVICE_NAME = "openllm"


def setup_openllm_logging(level: str = "INFO", *, json_lines: bool = True) -> None:
    """OpenLLM 日志装配（R-384）：request_id 注入 + JSON Lines。"""
    configure_logging(SERVICE_NAME, level, get_request_id=get_current_request_id, json_lines=json_lines)
```

### 4.2 修改 `backend/main.py`（`:80-83`）

```python
# 原：
# logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL), format=settings.LOG_FORMAT)
from app.core.r384_logging import setup_openllm_logging

setup_openllm_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)
```

### 4.3 修改 `backend/app/core/config.py`（`:181-183`）

```python
LOG_FORMAT: str = Field(
    default="%(asctime)s - [%(request_id)s] - %(name)s - %(levelname)s - %(message)s",
    description="日志格式（文本模式；R-384 追加 request_id 占位符）"
)
```

> **注意**：`LOG_FORMAT` 为配置项。若部署侧环境变量显式设置了旧格式，需**同步更新**（否则文本模式缺 `request_id`）；`json_lines=True` 时该格式不参与输出。

### 4.4 新增单测 `backend/tests/unit/test_r384_request_id_filter.py`

与 §3.4 同构，改 import 为 `from app.core.r384_logging import JsonLineFormatter, RequestIdFilter, configure_logging`、`from app.identity.request_id import ...`，断言中 `service == "openllm"`。

### 4.5 校验与回归

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenLLM\backend'
python -B -m pytest tests/unit/test_r384_request_id_filter.py -p no:cacheprovider
python -B -m pytest tests/unit -p no:cacheprovider
python -m ruff check app scripts tests/unit
python scripts/k07_endpoint_matrix.py --verify
python scripts/verify-env/verify_env.py --fail-fast
python scripts/smoke_l3_2.py
```

> **提交纪律**：本仓工作区存在大量未入库残留（含敏感 `backend/.env.shared-infra`、`data/edge_tokens.jsonl` 与 336 项历史误入库 `.pyc`）→ **只 add 本改动涉及文件，禁止 `git add -A`**。

## 5. OpenMemory 改动（含 6.0 核实项①结论）

### 5.1 核实项①结论（本改动包已实测）

`src/openmemory/api/server.py:782 main()` 内的 `basicConfig` 在编排器实启命令（`python scripts\start_openmemory.py` → `create_app()`）下**不执行** → **当前应用级日志未进入采集流**。因此日志配置必须外移。

### 5.2 修改 `src/openmemory/api/server.py`（落点）

在模块级 `logger = logging.getLogger(__name__)`（`:222`）**之后**新增：

```python
# R-384（BL-147-02/03）：日志配置外移至模块级——编排器实启 scripts/start_openmemory.py
# → create_app()，不经过 main()（:782 的 basicConfig 不生效）。
import sys

from openmemory.api.middleware.structured_log import request_id_ctx
from openmemory.utils.r384_logging import configure_logging


def _get_request_id() -> str | None:
    return request_id_ctx.get()


configure_logging(
    "openmemory",
    "INFO",
    get_request_id=_get_request_id,
    json_lines=True,
    stream=sys.stderr,
)
```

> 若 `server.py` 顶部导入 `structured_log` 会造成循环导入（本仓既有风险 R-1），改为在函数内延迟导入并延迟调用（例如在 `create_app()` 开头调用 `configure_logging`）。

### 5.3 修改 `src/openmemory/api/middleware/structured_log.py`（`:26`）

将模块级 `logger = logging.getLogger(__name__)` 改为**延迟导入的结构化门面**（沿用本仓 `StructLogger`），并在访问日志处补 `request_id` 落点：

```python
# 原：logger = logging.getLogger(__name__)
def _structured_logger():
    """延迟获取结构化 logger（避免与 struct_logger 顶部 import 形成循环依赖）。"""
    from openmemory.utils.struct_logger import get_logger

    return get_logger(__name__)
```

调用点（`extra={"structured": log_entry}`）改为该门面 kwargs 形式；**实施前必须核实** `StructLogger._log()` 对 kwargs 的处理（是否注入 `extra`/是否与 `extra["structured"]` 合并），据实调整写法。

### 5.4 新增单测

`tests/unit/test_r384_logging_contract.py`：① 导入顺序（不触发循环导入）；② 结构化行含 `request_id`；③ `configure_logging` 幂等。

### 5.5 校验与回归

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
python -m pytest tests/unit/test_r384_logging_contract.py -p no:cacheprovider
python -m pytest            # 按本仓 pyproject [tool.pytest.ini_options]
python -m ruff check src
# 端到端：访问任一接口 → 采集文件出现 JSON 行且含 "request_id"
```

## 6. OpenRAG 改动（落点不变 + 降险结论）

### 6.1 实测降险结论

`src/openrag/main.py:51` 在 **lifespan 内**调用 `setup_logging(level=..., json_format=settings.is_production)`；`observability/logging.py:410` 的 `self.logger = get_logger("openrag.api")` 与 `config/logging.py:71` 的 `get_logger` **同源**（structlog 门面）→ 其 `logger.info("request_started", method=..., ...)` kwargs 风格成立，**注册中间件不会报错**；两处并非"两套栈"，D-6 R-3 降级为"确认 contextvar 单一来源"。

### 6.2 修改 `src/openrag/main.py`（`add_middleware` 段，Prometheus 之后）

```python
    # R-384（BL-147-02）：请求日志中间件（X-Request-Id 贯穿），置于 Prometheus 之后
    try:
        from openrag.observability.logging import LoggingMiddleware

        app.add_middleware(LoggingMiddleware, service_name="openrag")
    except ImportError:
        logger.warning("LoggingMiddleware 未安装，跳过")
```

### 6.3 修改 `src/openrag/observability/logging.py`（`__call__` 内、`X-Correlation-ID` 处理之后）

```python
        # R-384（BL-147-02）：X-Request-Id 受信透传 / 非受信忽略重生成
        rid = request.headers.get("X-Request-Id")
        if rid and _is_trusted_source(request):
            set_request_id(rid)
        elif rid:
            set_request_id(generate_request_id())
```

> `_is_trusted_source` 沿用本仓既有代理来源校验实现；`set_request_id` / `generate_request_id` 如本仓未定义需新增（对齐协议头规范 `req-{12hex}`）。

### 6.4 JSONL（BL-147-03）

采集环境让 `json_format=True`（现为 `settings.is_production`）：在编排器环境显式置生产态，或改造 `main.py:51` 为 `json_format=True`（**建议**：新增独立开关 `OPENRAG_LOG_JSON=true` 读取，避免与 `is_production` 语义耦合）。structlog 的 `TimeStamper(fmt="iso")` 输出键为 **`timestamp`**——适配器已接受该键（别名表 `ts`/`timestamp`/`time`）。

### 6.5 新增单测 `tests/unit/test_r384_request_id.py`

受信透传 / 非受信忽略重生成两分支（可参照本仓 `tests/unit/test_s3_t7_audit_identity.py` 的 request_id 用例范式）。

### 6.6 校验与回归

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
python -m pytest tests/unit/test_r384_request_id.py -p no:cacheprovider
python run_tests.py
python -m ruff check src scripts tests/unit
python scripts/k07_endpoint_matrix.py
python scripts/smoke_l3_2.py
```

## 7. 提交与回执（各仓）

| 项 | 要求 |
|----|------|
| 提交粒度 | 批 A（`request_id` 接线）/ 批 B（JSONL）分两批，或合并同批 |
| 提交信息 | `feat(logging): R-384/BL-147-02 四仓 request_id 日志接线 + JSONL 结构化` |
| 提交纪律 | 禁止 `git add -A`；只 add 本改动涉及文件；提交前复核无敏感文件（`.env*`、令牌样本） |
| 辅助脚本 | 四仓已有 `dps-commit-push.bat` / `scripts/dps_commit_push.ps1`、`f1_commit_push.ps1`、`k07_commit_push.ps1`、`f2_commit_push.ps1`、`rag1_commit_push.ps1`（沙箱外执行） |
| 回执内容 | commit hash（批 A/B）+ 回归结果 + 单测证据（含两分支）+ 覆盖状态确认 |
| hash 回填 | 回执后回填《施工派单》§9.1 与《技术债务总表》TD-新增-020 |

## 8. 未决与风险

| # | 项 | 说明 |
|:-:|----|------|
| 1 | **本改动包未在目标仓运行验证** | 沙箱禁止写入同级四仓，无法在本会话跑各仓测试 → **各仓应用后必须执行 §3.5/§4.5/§5.5/§6.6 回归** |
| 2 | DPS 双入口一致性 | `rest_api/app.py`（实启路径）与 `main.py`（开发模式）均需装配；`configure_logging` 已做幂等 |
| 3 | OpenMemory 循环导入 | 见 §5.2 注（延迟导入兜底） |
| 4 | uvicorn 访问日志仍为文本 | 同一文件内 JSON 行与文本行混存，适配器逐行判断可解析；严格全 JSON 需采集侧 `--log-config`（BL-147-04） |
| 5 | `status_code` 类型 | 必须输出 **JSON 数字**（字符串不会被适配器采纳，导致"结果"维度落 `unknown`） |

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-16 | AD-OpenBase-Dev / AA-OpenBase-Dev | 初始创建：R-384 四仓改动包。**含对 D-6 的两处落点更正**（依据编排器实测启动命令：DPS 实走 `rest_api.app:app`、OpenMemory 实走启动脚本，原落点不生效）；提供四仓可复用通用件（`RequestIdFilter` + `JsonLineFormatter` + 幂等 `configure_logging`）、DPS/OpenLLM 完整改动与单测、OpenMemory/OpenRAG 改动（含 6.0 核实结论与降险结论）、逐仓校验命令与提交流程、5 项未决风险 |

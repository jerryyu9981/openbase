# OpenBase-R384派单-OpenMemory-v1.0.0

| 项 | 内容 |
|------|------|
| 文档编号 | OB-DISPATCH-R384-OPENMEMORY-v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Approved]（待分发执行） |
| 出具方 | OpenBase 项目（PM-OpenBase-Dev / AA-OpenBase-Dev） |
| 接收方 | **OpenMemory 仓对话**（本仓独立评审、独立提交、独立发布） |
| 出具日期 | 2026-09-16 |
| 版本归属 | OpenBase v1.4.7（承接型小版本）；OpenMemory 侧为跨仓改动 |
| 上游依据 | 《OpenBase-D6四仓request_id日志接线改动说明-v1.0.0》§3.3；《OpenBase-R384改动包-v1.0.0》§5；《OpenBase-R384四仓施工派单-v1.0.0》 |
| 性质 | **单仓施工指令（自包含）**——本文件无需依赖其他 OpenBase 文档即可执行 |
| 风险提示 | **本仓是四仓中唯一存在"日志配置未生效 + 循环导入"双风险的仓**，请严格按 §2 核实后再动手 |

---

## 1. 任务与目标

| 项 | 内容 |
|----|------|
| 需求 | **R-384 四仓日志接入**（OpenMemory 切片）：请求日志携带 `request_id`（与网关出站头 `X-Request-Id` 一致），并输出 **JSON Lines**，使 OpenMemory 日志可在 OpenBase 日志中心按 `module=memory` 检索、按 `request_id` 从网关串联追踪 |
| 关联 | OpenBase **BL-147-02**（`request_id` 接线）、**BL-147-03**（JSONL 结构化） |
| 本仓底数 | `api/middleware/structured_log.py:144-197` **已组装** `request_id`/`status_code`/`elapsed_ms`；但 `:26` 用的是标准 `logging.getLogger` → `extra` 被根 logger 的纯文本 formatter **丢弃**。本次即"把已组装的值真正落进日志" |
| 验收 | ① 带 `X-Request-Id` 请求 → 应用日志行含该 `request_id`；② 匿名/豁免 → `"-"`；③ 应用日志行为合法 JSON 且 `status_code` 为**数字**；④ 回归全通过 |

## 2. 前置核实（本仓 2 项，**必须先做**）

| # | 核实项 | 已知证据 | 要求 |
|:-:|-------|---------|------|
| 1 | **日志配置是否生效** | `src/openmemory/api/server.py:782 main()` 内才有 `logging.basicConfig`；而编排器实启命令为 `python scripts\start_openmemory.py` → `create_app()`，**不经过 `main()`** → 倾向"未配置"（应用 INFO 日志不进采集流） | 实跑确认：启动后访问任一接口，观察采集文件/控制台是否出现**应用级**日志行。若缺失 → 按 §4.2 把配置外移 |
| 2 | **StructLogger 输出路径与 kwargs 处理** | `utils/struct_logger.py:65` 与中间件 `structured_log.py:31` 是**同一组 ContextVar**；`struct_logger.py:182-198` JSON formatter 输出 `request_id`/`trace_id` 等；`get_logger()` 在 `:329` | 阅读 `StructLogger._log()`（`struct_logger.py:211-212` 附近）确认 **kwargs 如何进入 `extra`、是否与 `extra["structured"]` 合并** —— 据此决定 §4.3 的调用点写法；并确认 **不会双重输出**（同一行不得被 StructLogger handler 与 root handler 各写一次） |

## 3. 契约（强制）

| 项 | 约定 |
|----|------|
| 头名 | `X-Request-Id`；受信来源**透传复用**，非受信来源**忽略并本地重新生成** `req-{12hex}` |
| 日志字段 | 统一 `request_id`；无上下文路径一律 `"-"`，**禁止 `KeyError`** |
| 输出流 | 维持现状（**stderr**），不得改为仅落自有文件 |
| 禁止 | 不记录令牌/密码/密钥/完整请求体 |
| 采集目录 | `logs/openmemory/`、文件名 `openmemory-YYYYMMDD.jsonl`（**目录名不得改**，OpenBase 按目录名映射 `module=memory`） |

**JSONL 字段契约**（OpenBase 适配器实际读取键，超集允许）：

| 字段 | 必需 | 类型 | 说明 |
|------|:---:|------|------|
| `ts` | 必需 | ISO 8601 字符串 | `Z` 允许；无时区按 UTC；**无法解析的行整行丢弃** |
| `request_id` | 必需 | 字符串 | 与网关一致 |
| `method` / `path` | 必需 | 字符串 | 用于"操作类型"维度 |
| `status_code` | 必需 | **JSON 数字** | 字符串不会被采纳，"结果"维度落 `unknown` |
| `duration_ms` | 建议 | 数字 | 访问日志已有 `elapsed_ms`，映射为该键 |
| `level` | 建议 | 字符串 | — |
| `operator_id` | 建议 | 字符串 | 可用 `user_id_ctx` 映射 |
| `module` | — | — | **无需输出**（由采集目录名映射） |

## 4. 改动清单

### 4.1 新增 `src/openmemory/utils/r384_logging.py`

> 设计要点：本模块**不导入任何中间件**（避免循环导入）——`request_id` 取值函数由调用方（`api/server.py`）传入。

```python
# -*- coding: utf-8 -*-
"""R-384 日志接线：request_id 注入 + JSON Lines 输出（BL-147-02 / BL-147-03）。

本模块刻意不导入 api.middleware.*，ContextVar 取值由调用方注入，规避循环导入。
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Callable, TextIO

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
    """单行 JSON 输出（字段与 OpenBase LogEntry 可映射集对齐）。"""

    _OPTIONAL_KEYS = (
        "method", "path", "status_code", "duration_ms", "operator_id",
        "tenant_id", "ip", "case_id", "step_id", "run_id", "action", "event",
    )

    def __init__(self, service: str) -> None:
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "service": self._service,
            "logger": record.name,
            "message": record.getMessage(),
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
    service: str = "openmemory",
    level: str = "INFO",
    *,
    get_request_id: Callable[[], str | None],
    json_lines: bool = True,
    stream: TextIO | None = None,
) -> None:
    """装配日志：root filter（request_id）+ root handler formatter（JSON Lines）。幂等。

    输出流默认 stderr；如需 stdout 显式传 `stream=sys.stdout`。
    """
    global _CONFIGURED
    logger = logging.getLogger()
    if not any(isinstance(f, RequestIdFilter) for f in logger.filters):
        logger.addFilter(RequestIdFilter(get_request_id))
    if _CONFIGURED:
        return
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    formatter: logging.Formatter = (
        JsonLineFormatter(service) if json_lines
        else logging.Formatter("%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s")
    )
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    _CONFIGURED = True
```

### 4.2 修改 `src/openmemory/api/server.py`（**实际生效落点**）

在模块级 `logger = logging.getLogger(__name__)`（实测 `:222`）**之后**插入：

```python
# R-384（BL-147-02/03）：日志配置外移至模块级——编排器实启 scripts/start_openmemory.py
# → create_app()，不经过 main()（:782 的 basicConfig 在该路径不执行）。
from openmemory.api.middleware.structured_log import request_id_ctx
from openmemory.utils.r384_logging import configure_logging


def _get_request_id() -> str | None:
    """从本仓中间件 ContextVar 读取当前请求 request_id。"""
    return request_id_ctx.get()


configure_logging("openmemory", "INFO", get_request_id=_get_request_id, json_lines=True)
```

> **循环导入兜底**：若模块级 `from ...structured_log import request_id_ctx` 触发循环导入，改为在 `create_app()`（`:225`）**函数内**延迟导入并调用 `configure_logging(...)`；此时务必确认 `create_app()` 在每次启动路径上都会执行（本仓两条路径都会）。

### 4.3 修改 `src/openmemory/api/middleware/structured_log.py`（`:26`，**按 §2 核实结论择一**）

**方案 A（推荐：统一走 root 装配）**：删除模块级 `logger = logging.getLogger(__name__)`，调用点改为标准 logger 并**通过 `extra=` 携带上下文字段**，使其被 §4.1 的 JSON formatter 采纳：

```python
logger = logging.getLogger(__name__)  # 保留模块级 logger，但不再依赖它承载结构字段

# 访问日志调用点（示意）：
logger.info(
    "access_log",
    extra={
        "method": request.method,
        "path": request.url.path,
        "status_code": log_entry["status_code"],   # 必须为 int
        "duration_ms": log_entry["elapsed_ms"],
        "operator_id": user_id_ctx.get(),
    },
)
```

**方案 B（复用本仓 StructLogger）**：让中间件改走 `utils/struct_logger.get_logger()` 门面（延迟导入），由 StructLogger 既有 JSON formatter 输出（其会带 `request_id`）。

> **两条路径择一，禁止并行**（否则同一行会被两个 handler 各写一次，产生重复日志）。选择依据见 §2 核实项②。

### 4.4 现有隐患（一并处理）

`basicConfig` 仅在 `main()` 内 → 按 §4.2 外移后，`main()` 内的 `basicConfig` 建议删除或改为调用同一 `configure_logging`，避免双份 handler。

## 5. 新增单测 `tests/unit/test_r384_logging_contract.py`

```python
# -*- coding: utf-8 -*-
"""R-384/BL-147-02：request_id 注入、JSON Lines 契约与幂等。"""
from __future__ import annotations

import json
import logging

from openmemory.utils.r384_logging import JsonLineFormatter, RequestIdFilter, configure_logging


def _record() -> logging.LogRecord:
    return logging.LogRecord("openmemory.api", logging.INFO, __file__, 1, "hello", None, None)


def test_filter_uses_value_when_present() -> None:
    record = _record()
    assert RequestIdFilter(lambda: "req-abc123456789").filter(record) is True
    assert record.request_id == "req-abc123456789"


def test_filter_falls_back_to_dash() -> None:
    record = _record()
    assert RequestIdFilter(lambda: None).filter(record) is True
    assert record.request_id == "-"


def test_filter_survives_getter_error() -> None:
    def _boom() -> str | None:
        raise RuntimeError("boom")

    record = _record()
    assert RequestIdFilter(_boom).filter(record) is True
    assert record.request_id == "-"


def test_json_line_formatter_emits_contract_fields() -> None:
    record = _record()
    record.request_id = "req-abc123456789"
    record.method = "POST"
    record.path = "/api/v1/memories"
    record.status_code = 201
    record.duration_ms = 7

    payload = json.loads(JsonLineFormatter("openmemory").format(record))

    assert payload["service"] == "openmemory"
    assert payload["request_id"] == "req-abc123456789"
    assert isinstance(payload["status_code"], int)
    assert payload["ts"].endswith("Z")


def test_configure_logging_is_idempotent() -> None:
    configure_logging("openmemory", "INFO", get_request_id=lambda: None, json_lines=True)
    configure_logging("openmemory", "INFO", get_request_id=lambda: None, json_lines=True)
    root = logging.getLogger()
    assert sum(isinstance(f, RequestIdFilter) for f in root.filters) == 1
```

**另需 1 个导入顺序用例**：断言 `import openmemory.api.server` 与 `import openmemory.utils.struct_logger` 不产生循环导入异常（本仓 R-1 风险的回归护栏）。

## 6. 校验与回归（本仓执行）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'

python -m pytest tests/unit/test_r384_logging_contract.py -p no:cacheprovider
python -m pytest          # 按本仓 pyproject [tool.pytest.ini_options] 配置
python -m ruff check src

# 端到端：访问任一接口 → 采集文件出现 JSON 行且含 "request_id"；匿名请求 → "-"
```

## 7. 提交与回执

| 项 | 要求 |
|----|------|
| 分支 | 本仓当前分支（实测 `release/v7.3.0`）或本仓发布分支 |
| 提交信息 | `feat(logging): R-384/BL-147-02 request_id 日志接线 + JSONL 结构化` |
| 提交纪律 | **禁止 `git add -A`**。本仓工作区存在大量未跟踪项（`doc/testing/evidence/*.txt` 证据、`storage/`、`get-pip.py`，以及名为 `json`、`markdown` 的可疑文件）→ 只 add 本指令涉及文件；提交前复核无敏感文件 |
| 可用辅助 | 本仓已有 `k07-commit-push.bat` / `scripts/k07_commit_push.ps1`（沙箱外执行） |
| **回执内容** | ① commit hash；② 回归命令与通过数；③ 新增单测结果；④ 核实项①②结论（配置是否外移、输出路径择一）；⑤ 是否达到 §1 四项验收 |

**回执模板**：

```text
[OpenMemory / R-384 回执]
- commit: <hash>
- 核实①: 原启动路径下应用日志 <已生效/未生效> → 处理: <外移配置至 server.py 模块级 / other>
- 核实②: StructLogger._log kwargs 处理 = <...>；输出路径择一 = <方案A root 装配 / 方案B StructLogger>
- 回归: pytest = <n> passed / ruff = 0
- 单测: test_r384_logging_contract.py = 5 passed (+导入顺序 1)
- 验收: ①request_id ✅ ②兜底 "-" ✅ ③JSONL(status_code 数字) ✅ ④回归全通过 ✅
- 备注: <异常/偏差>
```

## 8. 约束与风险

| # | 项 | 说明 |
|:-:|----|------|
| 1 | 本指令未在 OpenMemory 仓运行验证 | 出具方沙箱禁止写入同级仓 → **务必执行 §6 回归后再提交** |
| 2 | **循环导入**（`struct_logger` ↔ 中间件） | §4.1 模块刻意零中间件依赖；§4.2 提供延迟导入兜底；另加导入顺序单测 |
| 3 | **重复输出** | §4.3 方案 A/B 择一，禁止并行；§4.4 清理 `main()` 内遗留 `basicConfig` |
| 4 | 启动路径 | `main()` 内的旧配置在实启路径下不生效 → 必须外移（§4.2），否则应用日志仍进不了采集流 |
| 5 | uvicorn 访问日志仍为文本 | 与 JSON 行混存，OpenBase 适配器逐行判断可解析；**本仓无需处理** |

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-16 | AA-OpenBase-Dev | 初始创建：OpenMemory 单仓施工指令（自包含）。含 2 项强制前置核实（日志配置生效性 / StructLogger 输出路径）、契约与 JSONL 字段表、完整改动代码（新增零依赖 `utils/r384_logging.py` + `server.py` 装配外移 + `structured_log.py` 两方案择一）、单测 5 例 + 导入顺序护栏、回归命令、回执模板与 5 项风险 |

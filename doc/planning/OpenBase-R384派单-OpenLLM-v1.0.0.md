# OpenBase-R384派单-OpenLLM-v1.0.0

| 项 | 内容 |
|------|------|
| 文档编号 | OB-DISPATCH-R384-OPENLLM-v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Approved]（待分发执行） |
| 出具方 | OpenBase 项目（PM-OpenBase-Dev / AA-OpenBase-Dev） |
| 接收方 | **OpenLLM 仓对话**（本仓独立评审、独立提交、独立发布） |
| 出具日期 | 2026-09-16 |
| 版本归属 | OpenBase v1.4.7（承接型小版本）；OpenLLM 侧为跨仓改动 |
| 上游依据 | 《OpenBase-D6四仓request_id日志接线改动说明-v1.0.0》；《OpenBase-R384改动包-v1.0.0》§4；《OpenBase-R384四仓施工派单-v1.0.0》 |
| 性质 | **单仓施工指令（自包含）**——本文件无需依赖其他 OpenBase 文档即可执行 |

---

## 1. 任务与目标

| 项 | 内容 |
|----|------|
| 需求 | **R-384 四仓日志接入**（OpenLLM 切片）：请求日志携带 `request_id`（与网关出站头 `X-Request-Id` 一致），并输出 **JSON Lines**，使 OpenLLM 日志可在 OpenBase 日志中心按 `module=llm` 检索、按 `request_id` 从网关串联追踪 |
| 关联 | OpenBase **BL-147-02**（`request_id` 接线）、**BL-147-03**（JSONL 结构化） |
| 本仓底数 | `app/identity/audit_identity.py::identity_log_extra()` **已产出 `request_id`**，但当前只进审计库，从未传给 `logger.*(extra=…)` → 本次即"把已有的值送进日志" |
| 验收 | ① 带 `X-Request-Id` 请求 → 应用日志行含该 `request_id`；② 匿名/豁免 → `"-"`；③ 应用日志行为合法 JSON 且 `status_code` 为**数字**；④ 回归全通过 |

## 2. 前置核实（本仓 1 项）

| # | 核实项 | 方法 | 结论要求 |
|:-:|-------|------|---------|
| 1 | 实际启动路径与日志配置生效点 | 确认编排器/生产实启命令。**外部实测**：OpenLLM 实走 `python -m uvicorn main:app`（cwd=`backend`）→ `backend/main.py` 模块级配置**生效** | 落点为 `backend/main.py`（本指令按此给出）；若本仓实测不同，先更正落点 |

## 3. 契约（强制）

| 项 | 约定 |
|----|------|
| 头名 | `X-Request-Id`；受信来源**透传复用**，非受信来源**忽略并本地重新生成** `req-{12hex}` |
| 日志字段 | 统一 `request_id`；无上下文路径一律 `"-"`，**禁止 `KeyError`** |
| 输出流 | 维持现状（**stderr**），不得改为仅落自有文件 |
| 禁止 | 不记录令牌/密码/密钥/完整请求体 |
| 采集目录 | `logs/openllm/`、文件名 `openllm-YYYYMMDD.jsonl`（**目录名不得改**，OpenBase 按目录名映射 `module=llm`） |

**JSONL 字段契约**（OpenBase 适配器实际读取键，超集允许）：

| 字段 | 必需 | 类型 | 说明 |
|------|:---:|------|------|
| `ts` | 必需 | ISO 8601 字符串 | `Z` 允许；无时区按 UTC；**无法解析的行整行丢弃** |
| `request_id` | 必需 | 字符串 | 与网关一致 |
| `method` / `path` | 必需 | 字符串 | 用于"操作类型"维度 |
| `status_code` | 必需 | **JSON 数字** | 字符串不会被采纳，"结果"维度落 `unknown` |
| `duration_ms` | 建议 | 数字 | — |
| `level` | 建议 | 字符串 | — |
| `operator_id` | 建议 | 字符串 | "操作人"维度 |
| `module` | — | — | **无需输出**（由采集目录名映射） |

## 4. 改动清单

### 4.1 新增 `backend/app/core/r384_logging.py`

```python
# -*- coding: utf-8 -*-
"""R-384 日志接线：request_id 注入 + JSON Lines 输出（BL-147-02 / BL-147-03）。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Callable

from app.identity.request_id import get_current_request_id  # 本仓既有

_CONFIGURED = False
SERVICE_NAME = "openllm"


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
    service: str,
    level: str = "INFO",
    *,
    get_request_id: Callable[[], str | None],
    json_lines: bool = True,
) -> None:
    """装配日志：root filter（request_id）+ root handler formatter（JSON Lines）。幂等。"""
    global _CONFIGURED
    logger = logging.getLogger()
    if not any(isinstance(f, RequestIdFilter) for f in logger.filters):
        logger.addFilter(RequestIdFilter(get_request_id))
    if _CONFIGURED:
        return
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    formatter: logging.Formatter = (
        JsonLineFormatter(service) if json_lines
        else logging.Formatter("%(asctime)s - [%(request_id)s] - %(name)s - %(levelname)s - %(message)s")
    )
    handler = logging.StreamHandler()  # 默认 stderr
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    _CONFIGURED = True


def setup_openllm_logging(level: str = "INFO", *, json_lines: bool = True) -> None:
    """OpenLLM 日志装配（R-384）。"""
    configure_logging(SERVICE_NAME, level, get_request_id=get_current_request_id, json_lines=json_lines)
```

### 4.2 修改 `backend/main.py`（`:80-83`）

```python
# 原：
# logging.basicConfig(
#     level=getattr(logging, settings.LOG_LEVEL),
#     format=settings.LOG_FORMAT
# )
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

### 4.4 可选（推荐）：把既有 `request_id` 送进日志

`app/identity/audit_identity.py::identity_log_extra()` 已产出 `request_id`。可在记录审计访问日志处一并透出 HTTP 上下文字段，使"操作类型/结果/操作人"维度更完整：

```python
logger.info("access", extra={**identity_log_extra(), "method": request.method,
                             "path": request.url.path, "status_code": response.status_code,
                             "duration_ms": elapsed_ms})
```

> 属可选增强；不做也可满足 §1 验收（`method/path/status_code` 仍可由 uvicorn 访问行经 OpenBase 的纯文本回退解析获得）。

## 5. 新增单测 `backend/tests/unit/test_r384_request_id_filter.py`

```python
# -*- coding: utf-8 -*-
"""R-384/BL-147-02：request_id 注入与 JSON Lines 契约。"""
from __future__ import annotations

import json
import logging

from app.core.r384_logging import JsonLineFormatter, RequestIdFilter, configure_logging


def _record() -> logging.LogRecord:
    return logging.LogRecord("app.api", logging.INFO, __file__, 1, "hello", None, None)


def test_filter_uses_contextvar_when_present() -> None:
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
    record.path = "/api/v1/chat/completions"
    record.status_code = 200
    record.duration_ms = 9

    payload = json.loads(JsonLineFormatter("openllm").format(record))

    assert payload["service"] == "openllm"
    assert payload["request_id"] == "req-abc123456789"
    assert isinstance(payload["status_code"], int)
    assert payload["ts"].endswith("Z")


def test_configure_logging_is_idempotent() -> None:
    configure_logging("openllm", "INFO", get_request_id=lambda: None, json_lines=True)
    configure_logging("openllm", "INFO", get_request_id=lambda: None, json_lines=True)
    root = logging.getLogger()
    assert sum(isinstance(f, RequestIdFilter) for f in root.filters) == 1
```

## 6. 校验与回归（本仓执行）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenLLM\backend'

python -B -m pytest tests/unit/test_r384_request_id_filter.py -p no:cacheprovider
python -B -m pytest tests/unit -p no:cacheprovider      # 期望 S4 全组 + 受影响回归全绿
python -m ruff check app scripts tests/unit
python scripts/k07_endpoint_matrix.py --verify
python scripts/verify-env/verify_env.py --fail-fast
python scripts/smoke_l3_2.py
```

**端到端验证**：经 OpenBase `llm-proxy` 调用 → OpenLLM 日志 `request_id` 与网关日志一致；直连（非受信）携带伪造头 → 生成新的 `req-{12hex}`。

## 7. 提交与回执

| 项 | 要求 |
|----|------|
| 分支 | 本仓当前工作分支（实测 `feature/s4-identity-channel-b`）或本仓发布分支 |
| 提交信息 | `feat(logging): R-384/BL-147-02 request_id 日志接线 + JSONL 结构化` |
| 提交纪律 | **禁止 `git add -A`**。本仓工作区现存大量未入库残留，**含敏感文件 `backend/.env.shared-infra`、`data/edge_tokens.jsonl`，以及 336 项历史误入库 `.pyc` 变更** → 只 add 本指令涉及文件：`backend/app/core/r384_logging.py`、`backend/main.py`、`backend/app/core/config.py`、`backend/tests/unit/test_r384_request_id_filter.py` |
| 可用辅助 | 本仓已有 `f1-commit-push.bat` / `scripts/f1_commit_push.ps1`、`k07-commit-push.bat` / `scripts/k07_commit_push.ps1`（沙箱外执行） |
| **回执内容** | ① commit hash；② 回归命令与通过数；③ 新增单测结果；④ 是否达到 §1 四项验收 |

**回执模板**：

```text
[OpenLLM / R-384 回执]
- 批 A/B commit: <hash>
- 回归: pytest tests/unit = <n> passed / ruff = 0 / k07 --verify = exit 0 / verify-env = pass / smoke = exit 0
- 单测: test_r384_request_id_filter.py = 5 passed
- 验收: ①request_id 串联 ✅ ②兜底 "-" ✅ ③JSONL(status_code 数字) ✅ ④回归全通过 ✅
- 备注: <异常/偏差；环境变量 LOG_FORMAT 是否需同步>
```

## 8. 约束与风险

| # | 项 | 说明 |
|:-:|----|------|
| 1 | 本指令未在 OpenLLM 仓运行验证 | 出具方沙箱禁止写入同级仓 → **务必执行 §6 回归后再提交** |
| 2 | `LOG_FORMAT` 两侧一致性 | 代码默认值与部署侧环境变量必须同步，否则文本模式缺 `request_id` |
| 3 | uvicorn 访问日志仍为文本 | 与 JSON 行混存，OpenBase 适配器逐行判断可解析；**本仓无需处理** |
| 4 | 提交误纳敏感文件 | 本仓工作区含 `.env.shared-infra` 与令牌样本 → 严格遵守 §7 纪律 |

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-16 | AA-OpenBase-Dev | 初始创建：OpenLLM 单仓施工指令（自包含）。含前置核实（落点 `backend/main.py` 确认有效）、契约与 JSONL 字段表、完整改动代码（新增 `app/core/r384_logging.py` + 改 `main.py`/`config.py` + 可选增强）、单测 5 例、回归命令、回执模板与 4 项风险（含敏感文件提交纪律） |

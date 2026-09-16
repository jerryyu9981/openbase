# OpenBase-R384派单-DPS-v1.0.0

| 项 | 内容 |
|------|------|
| 文档编号 | OB-DISPATCH-R384-DPS-v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Approved]（待分发执行） |
| 出具方 | OpenBase 项目（PM-OpenBase-Dev / AA-OpenBase-Dev） |
| 接收方 | **DPS 仓对话**（本仓独立评审、独立提交、独立发布） |
| 出具日期 | 2026-09-16 |
| 版本归属 | OpenBase v1.4.7（承接型小版本）；DPS 侧为跨仓改动 |
| 上游依据 | 《OpenBase-D6四仓request_id日志接线改动说明-v1.0.0》；《OpenBase-R384改动包-v1.0.0》§3；《OpenBase-R384四仓施工派单-v1.0.0》 |
| 性质 | **单仓施工指令（自包含）**——本文件无需依赖其他 OpenBase 文档即可执行 |

---

## 1. 任务与目标

| 项 | 内容 |
|----|------|
| 需求 | **R-384 四仓日志接入**（DPS 切片）：请求日志携带 `request_id`（与网关出站头 `X-Request-Id` 一致），并输出 **JSON Lines**，使 DPS 日志可在 OpenBase 日志中心按 `module=dps` 检索、按 `request_id` 从网关串联追踪 |
| 关联 | OpenBase **BL-147-02**（`request_id` 接线）、**BL-147-03**（JSONL 结构化） |
| 验收 | ① 带 `X-Request-Id` 请求 → 应用日志行含该 `request_id`；② 匿名/豁免请求 → `"-"`；③ 应用日志行为合法 JSON 且 `status_code` 为**数字**；④ 回归全通过 |

## 2. 前置核实（本仓 1 项，必须先做）

| # | 核实项 | 方法 | 结论要求 |
|:-:|-------|------|---------|
| 1 | **实际启动路径与日志配置生效点** | 确认编排器/生产实启命令。**外部实测已发现**：DPS 实走 `python -m uvicorn rest_api.app:app --app-dir src`，**不经过 `src/main.py`** → 该文件 `:37-40` 的 `logging.basicConfig` **不生效** | 以 `src/rest_api/app.py` 为落点（本指令即按此给出）；`src/main.py` 同步改造以保开发模式一致 |

> 若本仓实测启动路径与上述不同，请先以实测为准调整落点，再施工。

## 3. 契约（强制）

| 项 | 约定 |
|----|------|
| 头名 | `X-Request-Id`；受信来源**透传复用**，非受信来源**忽略并本地重新生成** `req-{12hex}` |
| 日志字段 | 统一 `request_id`；无上下文路径（豁免/健康检查/非请求上下文）一律 `"-"`，**禁止 `KeyError`** |
| 输出流 | 维持现状（**stderr**），不得改为仅落自有文件 |
| 禁止 | 不记录令牌/密码/密钥/完整请求体 |
| 采集目录 | `logs/dps/`、文件名 `dps-YYYYMMDD.jsonl`（**目录名不得改**，OpenBase 按目录名映射 `module`） |

**JSONL 字段契约**（OpenBase 适配器 `RepoLogAdapter._parse_line` 实际读取键，超集允许）：

| 字段 | 必需 | 类型 | 说明 |
|------|:---:|------|------|
| `ts` | 必需 | ISO 8601 字符串 | `Z` 允许；无时区按 UTC；**无法解析的行会被整行丢弃** |
| `request_id` | 必需 | 字符串 | 与网关一致 |
| `method` / `path` | 必需 | 字符串 | 用于"操作类型"维度 |
| `status_code` | 必需 | **JSON 数字** | 字符串 `"200"` **不会被采纳**，"结果"维度会落 `unknown` |
| `duration_ms` | 建议 | 数字 | — |
| `level` | 建议 | 字符串 | — |
| `operator_id` | 建议 | 字符串 | "操作人"维度 |
| `module` | — | — | **无需输出**（由采集目录名映射） |

## 4. 改动清单

### 4.1 新增 `src/logging_setup.py`

```python
# -*- coding: utf-8 -*-
"""R-384 日志接线：request_id 注入 + JSON Lines 输出（BL-147-02 / BL-147-03）。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Callable

from identity.request_id import get_current_request_id  # DPS 既有（src/identity/request_id.py）

_CONFIGURED = False
SERVICE_NAME = "dps"


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
    """装配日志：root filter（request_id）+ root handler formatter（JSON Lines）。

    - **幂等**：重复调用仅生效一次（`rest_api/app.py` 与 `main.py` 双入口各调一次）。
    - **输出流不变**：仍为 stderr。
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
    handler = logging.StreamHandler()  # 默认 stderr
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    _CONFIGURED = True


def setup_dps_logging(level: str = "INFO", *, json_lines: bool = True) -> None:
    """DPS 日志装配（R-384）。"""
    configure_logging(SERVICE_NAME, level, get_request_id=get_current_request_id, json_lines=json_lines)
```

### 4.2 修改 `src/rest_api/app.py`（**实际生效落点**）

在 `logger = logging.getLogger(__name__)`（实测 `:40`）**之后**插入：

```python
# R-384（BL-147-02/03）：日志装配必须在模块导入期执行——编排器实启 `rest_api.app:app`，
# 不经过 src/main.py，故 src/main.py 的 basicConfig 在该路径不生效。
from logging_setup import setup_dps_logging

setup_dps_logging(settings.log_level)
```

> 沿用该文件既有的 `settings` 导入名（实测 `app.py` 使用 `settings`，见 `:355`），不要重复导入别名。

### 4.3 修改 `src/main.py`（开发模式入口，保持一致）

将 `:37-40` 的 `logging.basicConfig(...)` 块替换为：

```python
from logging_setup import setup_dps_logging

setup_dps_logging(settings.log_level)
```

> 该文件 `:34` 已 `from config import settings`；`logger = logging.getLogger(__name__)` 保留。

## 5. 新增单测 `src/tests/test_r384_request_id_filter.py`

```python
# -*- coding: utf-8 -*-
"""R-384/BL-147-02：request_id 注入与 JSON Lines 契约。"""
from __future__ import annotations

import json
import logging

from logging_setup import JsonLineFormatter, RequestIdFilter, configure_logging


def _record() -> logging.LogRecord:
    return logging.LogRecord("dps.api", logging.INFO, __file__, 1, "hello", None, None)


def test_filter_uses_contextvar_when_present() -> None:
    """有上下文：record.request_id 取 contextvar 值。"""
    record = _record()
    assert RequestIdFilter(lambda: "req-abc123456789").filter(record) is True
    assert record.request_id == "req-abc123456789"


def test_filter_falls_back_to_dash() -> None:
    """无上下文：兜底 "-"，不抛异常。"""
    record = _record()
    assert RequestIdFilter(lambda: None).filter(record) is True
    assert record.request_id == "-"


def test_filter_survives_getter_error() -> None:
    """取值异常不得丢日志。"""
    def _boom() -> str | None:
        raise RuntimeError("boom")

    record = _record()
    assert RequestIdFilter(_boom).filter(record) is True
    assert record.request_id == "-"


def test_json_line_formatter_emits_contract_fields() -> None:
    """JSONL 契约：必备字段 + 可选字段透出；status_code 必须为数字。"""
    record = _record()
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
    assert isinstance(payload["status_code"], int)
    assert payload["ts"].endswith("Z")


def test_configure_logging_is_idempotent() -> None:
    """双入口重复调用只生效一次。"""
    configure_logging("dps", "INFO", get_request_id=lambda: None, json_lines=True)
    configure_logging("dps", "INFO", get_request_id=lambda: None, json_lines=True)
    root = logging.getLogger()
    assert sum(isinstance(f, RequestIdFilter) for f in root.filters) == 1
```

## 6. 校验与回归（本仓执行）

```powershell
cd 'D:\Trae CN\myproject\Dev\DPS'

# 1) 新增用例
python -m pytest src/tests/test_r384_request_id_filter.py -p no:randomly

# 2) 回归（S5 隔离组 + 静态检查 + 门禁）
python -m pytest src/tests -p no:randomly
python -m ruff check src
python scripts/k07_endpoint_matrix.py --check
python scripts/smoke_l3_2.py --quick
```

**端到端验证**：带 `X-Proxy-Source: openbase-dps-proxy` + `X-Request-Id: req-abc123456789` 请求 → 日志行含 `"request_id":"req-abc123456789"`；匿名请求 → `"request_id":"-"`。

## 7. 提交与回执

| 项 | 要求 |
|----|------|
| 分支 | 本仓自定（建议在 `main` 或其发布分支） |
| 提交粒度 | 批 A（`request_id` 接线）/ 批 B（JSONL）可合并同批；提交信息：`feat(logging): R-384/BL-147-02 request_id 日志接线 + JSONL 结构化` |
| 提交纪律 | **禁止 `git add -A`**；只 add 本指令涉及文件（`src/logging_setup.py`、`src/rest_api/app.py`、`src/main.py`、`src/tests/test_r384_request_id_filter.py`）；提交前复核无敏感文件 |
| 可用辅助 | 本仓已有 `dps-commit-push.bat` / `scripts/dps_commit_push.ps1`（沙箱外执行） |
| **回执内容** | ① commit hash；② 回归命令与通过数；③ 新增单测结果；④ 是否达到 §1 四项验收 |

**回执模板**：

```text
[DPS / R-384 回执]
- 批 A/B commit: <hash>
- 回归: pytest src/tests = <n> passed / ruff = 0 / k07 --check = exit 0 / smoke --quick = exit 0
- 单测: test_r384_request_id_filter.py = 5 passed
- 验收: ①request_id 串联 ✅ ②兜底 "-" ✅ ③JSONL(status_code 数字) ✅ ④回归全通过 ✅
- 备注: <异常/偏差>
```

## 8. 约束与风险

| # | 项 | 说明 |
|:-:|----|------|
| 1 | 本指令未在 DPS 仓运行验证 | 出具方沙箱禁止写入同级仓 → **务必执行 §6 回归后再提交** |
| 2 | 双入口一致性 | `rest_api/app.py`（实启）与 `main.py`（开发模式）均需装配；`configure_logging` 已幂等 |
| 3 | uvicorn 访问日志仍为文本 | 同一文件内 JSON 行与文本行混存——OpenBase 适配器**逐行判断**可解析（文本行仍能取到 `method/path/status`）；严格全 JSON 由 OpenBase 采集侧另行处理，**本仓无需处理** |
| 4 | 日志格式变更影响人工 grep 习惯 | 建议在本仓运行手册登记新格式样例 |

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-16 | AA-OpenBase-Dev | 初始创建：DPS 单仓施工指令（自包含）。含前置核实（**落点已更正为 `rest_api/app.py`**）、契约与 JSONL 字段表、完整改动代码（新增 `logging_setup.py` + 改两处入口）、单测 5 例、回归命令、回执模板与 4 项风险 |

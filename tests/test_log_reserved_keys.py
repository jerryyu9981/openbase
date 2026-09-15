"""日志 `extra` 保留键冲突回归（缺陷 AD-20260914-02）.

背景（真实缺陷，2026-09-14 联调窗口实测发现）
--------------------------------------------------
CPython `logging.Logger.makeRecord()` 对 `extra=` 的键做如下校验::

    if (key in ["message", "asctime"]) or (key in rv.__dict__):
        raise KeyError("Attempt to overwrite %r in LogRecord" % key)

因此 `extra={"name": ...}` 会抛 ``KeyError: "Attempt to overwrite 'name' in LogRecord"``。
在 HTTP 路径上表现为 **500**（实测 `POST /api/v1/auth/api-keys` → 500 `SYS_500`，
`request_id=req-b9743f1eec30`；根因 `openbase/modules/auth/api_keys.py` 的
``logger.info("api key created", extra={"name": name})``）。

同类站点（扫描发现 5 处）：`modules/auth/api_keys.py`（create/revoke）、
`modules/mcp/__init__.py`（tool_registered/server_started）、
`modules/ai_apps/__init__.py`（app created）。

覆盖范围
--------
1. 静态防复发：`openbase/**/*.py` 的 `extra={...}` 不得使用 LogRecord 保留键；
2. 行为回归：受权签发服务密钥返回 200 且含一次明文 `ob_k_*` 密钥；列表可读。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi.testclient import TestClient

from openbase.demo_app import app
from openbase.modules.auth import api_keys as api_keys_module
from openbase.modules.auth.api_keys import ApiKeyStore
from openbase.modules.auth.jwt import create_access_token

ROOT = Path(__file__).resolve().parent.parent

# LogRecord 内建属性（`makeRecord` 校验命中集合）+ Formatter 专属键
RESERVED_KEYS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
    }
)

_EXTRA_BLOCK = re.compile(r"extra=\{([^}]*)\}", re.DOTALL)
_DICT_KEY = re.compile(r"[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']\s*:")

client = TestClient(app)
ADMIN_HEADERS = {
    "Authorization": "Bearer "
    + create_access_token("1", username="admin", extra={"permissions": ["*"]})
}


def _iter_sources() -> list[Path]:
    return sorted((ROOT / "openbase").rglob("*.py"))


def test_no_reserved_keys_in_logging_extra() -> None:
    """静态扫描：`extra=` 不得使用 LogRecord 保留键（否则运行时 KeyError → 500）."""
    offenders: list[str] = []
    for path in _iter_sources():
        text = path.read_text(encoding="utf-8")
        for block in _EXTRA_BLOCK.finditer(text):
            for key in _DICT_KEY.findall(block.group(1)):
                if key in RESERVED_KEYS:
                    offenders.append(f"{path.relative_to(ROOT)}: extra 使用保留键 {key!r}")
    assert not offenders, "日志 extra 使用 LogRecord 保留键（会抛 KeyError）:\n" + "\n".join(offenders)


def test_create_api_key_returns_200(caplog) -> None:
    """行为回归：受权签发服务密钥 → 200 且返回一次性明文 `ob_k_*` 密钥.

    注意：必须显式把该模块 logger 提到 INFO（生产由 logging_setup 统一置 INFO）；
    否则 pytest 默认级别下 ``logger.info`` 不生成记录，缺陷会被"假绿"掩盖。
    """
    with caplog.at_level(logging.INFO, logger=api_keys_module.logger.name):
        resp = client.post(
            "/api/v1/auth/api-keys",
            json={"name": "t4-regression-key", "description": "regression AD-20260914-02"},
            headers=ADMIN_HEADERS,
        )
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body.get("name") == "t4-regression-key"
    assert str(body.get("key") or "").startswith("ob_k_"), body


def test_list_api_keys_returns_200() -> None:
    """行为回归：列表端点（revoke/list 同源链路）不因日志调用而 500."""
    resp = client.get("/api/v1/auth/api-keys", headers=ADMIN_HEADERS)
    assert resp.status_code == 200, resp.text[:300]
    assert isinstance(resp.json(), list)


def test_api_key_store_create_survives_info_logging() -> None:
    """根因级回归：INFO 级别下 `ApiKeyStore.create()` 不得因 extra 保留键抛 KeyError.

    生产由 `logging_setup.setup_logging()` 统一置 INFO（这也是该缺陷只在真实服务
    暴露、而单测默认级别下"假绿"的原因），故此处显式复现生产日志级别。
    """
    logger = api_keys_module.logger
    previous_level = logger.level
    logger.setLevel(logging.INFO)
    try:
        store = ApiKeyStore()
        raw_key = store.create(name="t4-log-guard")
    finally:
        logger.setLevel(previous_level)
    assert raw_key.startswith("ob_k_")

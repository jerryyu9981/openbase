"""MCP stdio 传输适配测试（原覆盖率 0%，补齐线性会话路径）.

覆盖：凭证工具白名单映射、非法 JSON 行容错、协议请求响应输出、
默认 stdin/stdout 流分支、stdio 入口 main() 的凭证解析与会话调用。
"""

from __future__ import annotations

import io
import json
import sys

from openbase.modules.mcp import stdio as stdio_module
from openbase.modules.mcp.credentials import MCPCredential
from openbase.modules.mcp.stdio import _allowed_tools, main, run_stdio_session


def _credential(tools: tuple[str, ...] | None = None) -> MCPCredential:
    return MCPCredential(subject="stdio-test", credential_type="stdio-token", tools=tools)


def test_allowed_tools_mapping() -> None:
    """未声明白名单 → None（不限定）；声明后 → frozenset."""
    assert _allowed_tools(_credential()) is None
    assert _allowed_tools(_credential(("demo", "echo"))) == frozenset({"demo", "echo"})


def test_run_stdio_session_handles_valid_and_invalid_lines() -> None:
    """空行跳过、非法 JSON 返回 -32700、合法协议请求正常响应且退出码 0."""
    requests = [
        "",
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
        "{not-json",
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
    ]
    stream_in = io.StringIO("\n".join(requests) + "\n")
    stream_out = io.StringIO()

    exit_code = run_stdio_session(_credential(("demo",)), stream_in=stream_in, stream_out=stream_out)

    assert exit_code == 0
    responses = [json.loads(line) for line in stream_out.getvalue().splitlines()]
    assert len(responses) == 3
    errors = [response for response in responses if "code" in response]
    assert errors and errors[0]["code"] == -32700
    initialize = next(response for response in responses if "protocolVersion" in response)
    assert initialize["protocolVersion"]
    tools_response = next(response for response in responses if "tools" in response)
    # 白名单收窄：只保留 demo（若该工具未注册则为空列表，但响应结构成立）
    assert all(tool["name"] in {"demo"} for tool in tools_response["tools"])


def test_run_stdio_session_uses_default_streams(monkeypatch) -> None:
    """未注入流时回落到 sys.stdin / sys.stdout."""
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 3, "method": "initialize"}) + "\n"),
    )
    fake_stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    assert run_stdio_session(_credential()) == 0
    assert json.loads(fake_stdout.getvalue().strip())["protocolVersion"]


def test_main_resolves_credential_then_runs_session(monkeypatch) -> None:
    """入口 main()：先解析宿主令牌，再执行会话并透传退出码."""
    credential = _credential(("demo",))
    monkeypatch.setattr(stdio_module, "resolve_stdio_credential", lambda: credential)
    monkeypatch.setattr(stdio_module, "run_stdio_session", lambda cred: 7)
    assert main() == 7

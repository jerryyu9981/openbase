"""MCP stdio 传输适配（E1 §10.3-3）.

stdin/stdout 逐行 JSON-RPC：宿主在启动进程时通过 ``OPENBASE_MCP_TOKEN_FILE``
（优先）或 ``OPENBASE_MCP_TOKEN`` 注入**短期令牌**；本适配器在会话开始前完成
验签/``exp`` 校验并确定工具白名单，令牌缺失或失效即退出（fail-closed）。

注意：stdio 视为本地可信传输边界，但**不等于匿名可信** —— 仍必须携带可验证的
短期凭证，禁止把长期服务 Key 写入本地配置文件。
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import IO, Any

from openbase.modules.mcp.credentials import MCPCredential, resolve_stdio_credential


def _allowed_tools(credential: MCPCredential) -> frozenset[str] | None:
    """凭证工具白名单 → 协议层集合（None = 不限定）."""
    return None if credential.tools is None else frozenset(credential.tools)


def _write(stream: IO[str], payload: dict[str, Any]) -> None:
    """输出单条 JSON 响应（UTF-8 原文，不记录令牌）."""
    stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    stream.flush()


def run_stdio_session(
    credential: MCPCredential,
    stream_in: IO[str] | None = None,
    stream_out: IO[str] | None = None,
) -> int:
    """执行一次 stdio 会话（读取直到 EOF），返回进程退出码.

    Args:
        credential: 已校验的凭证（由 :func:`resolve_stdio_credential` 生成）。
        stream_in: 输入流（缺省 stdin，测试可注入）。
        stream_out: 输出流（缺省 stdout，测试可注入）。

    Returns:
        0 正常结束；单条非法 JSON 仅返回错误响应，不中断会话。
    """
    from openbase.modules.mcp import get_mcp_server

    reader = stream_in if stream_in is not None else sys.stdin
    writer = stream_out if stream_out is not None else sys.stdout
    allowed_tools = _allowed_tools(credential)
    server = get_mcp_server()
    for raw_line in reader:
        line = raw_line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            _write(writer, {"error": "invalid json", "code": -32700})
            continue
        response = asyncio.run(server.handle_request(request, allowed_tools=allowed_tools))
        _write(writer, response)
    return 0


def main() -> int:
    """stdio 入口：先解析宿主注入的令牌（失败即退出），再进入会话."""
    credential = resolve_stdio_credential()
    return run_stdio_session(credential)

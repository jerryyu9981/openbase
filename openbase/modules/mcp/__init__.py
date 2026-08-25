"""mcp 模块：MCP 工具封装（MCPServer + FastMCP 集成 + decorator 注册）.

来源：OpenRAG src/openrag/mcp_server/server.py（MCPServer 工具注册/协议分发模式抽取）
+ OpenMemory api/mcp_server.py（工具定义结构），适配 openbase 统一日志与鉴权约定。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, Request

from openbase.core.errors import BaseError, ErrorCode

logger = logging.getLogger("openbase.mcp")

router = APIRouter(prefix="/mcp", tags=["mcp"])


async def _require_mcp_key(request: Request) -> None:
    """MCP 服务级 API Key 鉴权（双接口体系 D-002，SR-008）.

    校验 X-API-Key 请求头是否在配置的 mcp_api_keys 中；
    未配置 key 时禁止工具调用（安全默认）。
    """
    from openbase.settings import get_settings

    keys = [
        k.strip()
        for k in get_settings().mcp_api_keys.split(",")
        if k.strip()
    ]
    provided = request.headers.get("X-API-Key", "")
    if not keys or provided not in keys:
        raise BaseError(ErrorCode.AUTH_UNAUTHORIZED, "invalid or missing mcp api key")

# FastMCP 实例（懒初始化）
_fastmcp = None
# 已注册工具注册表
_tool_registry: dict[str, dict[str, Any]] = {}


class MCPServer:
    """MCP 服务器核心.

    来源：OpenRAG src/openrag/mcp_server/server.py（复制级抽取协议分发模式，
    适配 openbase 统一日志）。
    支持 tools/list、tools/call、initialize 协议方法与工具注册/注销。
    """

    PROTOCOL_VERSION = "2024-11-05"

    def __init__(self, name: str = "openbase-mcp", version: str = "1.0.0") -> None:
        """初始化 MCP 服务器.

        Args:
            name: 服务器名称。
            version: 服务器版本号。
        """
        self.name = name
        self.version = version
        self._tools: dict[str, dict[str, Any]] = {}
        self._running: bool = False
        self._request_handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
        }

    # ---- 工具注册 ----

    def register_tool(self, tool_def: dict[str, Any]) -> None:
        """注册单个工具.

        Args:
            tool_def: 工具定义字典（name/description/input_schema/func）。
        """
        name = tool_def.get("name", "")
        if name:
            self._tools[name] = tool_def
            logger.info("mcp_tool_registered", extra={"name": name})

    def register_tools(self, tools: list[dict[str, Any]]) -> None:
        """批量注册工具."""
        for tool in tools:
            self.register_tool(tool)

    def unregister_tool(self, name: str) -> bool:
        """注销工具.

        Returns:
            注销成功返回 True；不存在返回 False。
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def list_tools(self) -> list[dict[str, Any]]:
        """返回已注册工具列表（可缓存，对齐 2026-07 MCP 规范）."""
        return [
            {"name": t["name"], "description": t.get("description", ""), "input_schema": t.get("input_schema", {})}
            for t in self._tools.values()
        ]

    # ---- 协议处理 ----

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理 MCP 请求并返回响应.

        Args:
            request: MCP 请求字典（{method, params, id}）。

        Returns:
            MCP 响应字典（JSON-RPC 风格）。
        """
        method = request.get("method", "")
        handler = self._request_handlers.get(method)
        if handler is None:
            return {"error": f"Unknown method: {method}", "code": -32601}
        try:
            return await handler(request)
        except Exception as exc:  # noqa: BLE001
            logger.exception("mcp request failed", extra={"method": method})
            return {"error": str(exc), "code": -32000}

    async def _handle_initialize(self, request: dict[str, Any]) -> dict[str, Any]:
        """initialize 握手：返回协议版本与能力声明."""
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": True}},
            "serverInfo": {"name": self.name, "version": self.version},
        }

    async def _handle_tools_list(self, request: dict[str, Any]) -> dict[str, Any]:
        """tools/list：返回工具清单（可缓存）."""
        return {"tools": self.list_tools()}

    async def _handle_tools_call(self, request: dict[str, Any]) -> dict[str, Any]:
        """tools/call：调用工具并返回结果.

        执行注册工具函数；函数在 registry 中为可调用对象时实际执行。
        """
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        tool_def = self._tools.get(tool_name)
        if tool_def is None:
            return {"content": [{"type": "text", "text": f"Tool '{tool_name}' not found"}], "isError": True}

        func = tool_def.get("func")
        if func is None:
            return {
                "content": [{"type": "text", "text": f"Tool '{tool_name}' executed with args: {arguments}"}],
                "isError": False,
            }
        try:
            result = await func(**arguments) if _is_async(func) else func(**arguments)
            return {"content": [{"type": "text", "text": str(result)}], "isError": False}
        except Exception as exc:  # noqa: BLE001
            logger.exception("mcp tool call failed", extra={"tool": tool_name})
            return {"content": [{"type": "text", "text": f"Tool '{tool_name}' failed: {exc}"}], "isError": True}

    # ---- 生命周期 ----

    async def start(self) -> None:
        """启动 MCP 服务器."""
        self._running = True
        logger.info("mcp_server_started", extra={"name": self.name, "version": self.version})

    async def stop(self) -> None:
        """停止 MCP 服务器."""
        self._running = False

    @property
    def is_running(self) -> bool:
        """服务器是否运行中."""
        return self._running

    def get_server_info(self) -> dict[str, Any]:
        """服务器信息."""
        return {
            "name": self.name,
            "version": self.version,
            "running": self._running,
            "tools_count": len(self._tools),
        }


def _is_async(func: Callable[..., Any]) -> bool:
    """判断函数是否异步."""
    import inspect

    return inspect.iscoroutinefunction(func)


# 全局 MCPServer 实例（协议级）
_mcp_server: MCPServer | None = None


def get_mcp_server() -> MCPServer:
    """获取全局 MCPServer 实例（懒初始化）."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
    return _mcp_server


def get_fastmcp(name: str = "openbase-mcp"):
    """获取 FastMCP 实例（懒初始化）.

    Returns:
        FastMCP 实例；fastmcp 库不可用时返回 None。
    """
    global _fastmcp
    if _fastmcp is None:
        try:
            from fastmcp import FastMCP

            _fastmcp = FastMCP(name)
        except ImportError:
            logger.warning("fastmcp not installed, mcp tools disabled")
            return None
    return _fastmcp


def register_tool(name: str, description: str = "") -> Callable[..., Any]:
    """工具注册装饰器（双注册：FastMCP + MCPServer）.

    用法::

        @register_tool("openrag_search", "检索知识库")
        async def search(query: str) -> str: ...

    Args:
        name: 工具名。
        description: 工具描述。

    Returns:
        装饰器。
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        tool_def = {"name": name, "description": description, "func": func}
        _tool_registry[name] = tool_def
        # 注册到协议级 MCPServer
        get_mcp_server().register_tool(tool_def)
        # 注册到 FastMCP（可用时）
        server = get_fastmcp()
        if server is not None:
            try:
                server.tool(description=description)(func)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "failed to register tool on fastmcp",
                    extra={"tool": name, "error": str(exc)},
                )
        return func

    return decorator


@router.get("/tools/list", dependencies=[Depends(_require_mcp_key)])
async def list_tools() -> dict:
    """工具清单（可缓存，对齐 2026-07 MCP 规范）.

    Returns:
        {"tools": [{name, description, input_schema}, ...]}
    """
    return {"tools": get_mcp_server().list_tools()}


@router.post("/tools/call", dependencies=[Depends(_require_mcp_key)])
async def call_tool(payload: dict) -> dict:
    """工具调用（HTTP 适配层，对接 MCPServer 协议处理）."""
    return await get_mcp_server().handle_request(
        {"method": "tools/call", "params": payload}
    )


@router.get("/server/info")
async def server_info() -> dict:
    """MCP 服务器信息（调试用）."""
    return get_mcp_server().get_server_info()

__version__ = "1.1.0"

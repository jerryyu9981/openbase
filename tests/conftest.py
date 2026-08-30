"""pytest 全局配置：Windows 事件循环策略修复（TD-新增-009）.

背景：Windows 默认 ProactorEventLoop 在 pytest-asyncio auto 模式 + 多个
starlette TestClient（anyio portal 线程）组合执行时，跨线程创建/关闭
event loop 触发 C 层 access violation / Segmentation fault（全量 pytest
本机崩溃）。切换 SelectorEventLoopPolicy 为线程安全实现修复。

注：仅影响本机测试运行，不影响应用运行时（uvicorn 独立进程）。
"""
from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

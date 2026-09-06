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


def reset_db_singletons() -> None:
    """重置 core.db.session 全局 engine/session 单例（T2 隔离修复 2026-09-06）.

    OIDC E2E 族以"DB 不可达 → 降级直签"为断言语义：autouse fixture 会把
    OPENBASE_DB_URL 指为不可达以模拟空库。但全量 pytest 中前序用例可能已按
    真实库创建全局 engine 单例（core/db/session._engine），OIDC 用例再走
    get_db 会复用该 engine 直连真实库 → 固定 sub 命中历史 OidcIdentity 行
    复用旧用户（'3'/'4'），env 隔离被绕过。本函数先 dispose 再置空两个单例，
    使后续 get_db 按当前（不可达）env 重建。
    """
    from openbase.core import db as db_pkg

    session_mod = db_pkg.session
    engine = session_mod._engine
    if engine is not None:
        try:
            asyncio.run(engine.dispose())
        except Exception:
            # dispose 失败仅告警：置空后旧引擎由 GC 回收（进程级测试可容忍）
            pass
    session_mod._engine = None
    session_mod._session_factory = None


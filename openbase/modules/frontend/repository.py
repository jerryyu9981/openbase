"""frontend 模块数据访问层：``dynamic_modules`` 表读写（v1.4.6 状态持久化）.

建表归属（已核实，无需新增迁移）：``DynamicModule`` 定义于
``core/models/business.py`` 并挂载到 ``Base.metadata``，由
``core/db/init.py::create_tables`` 的 ``Base.metadata.create_all`` 随初始化链建表；
``Base.metadata.tables`` 中确含 ``dynamic_modules``（DevLogReport 可引用该结论）。

本层只做参数化读写（select/where/主键 get），不吞异常也不做业务降级——
DB 不可用的降级口径（回退内存 + WARN）由 Service 层决定，保证「失败可见」。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from openbase.core.models import DynamicModule

__all__ = ["ModuleStatusRepository"]


class ModuleStatusRepository:
    """``dynamic_modules`` 状态读写（SQLAlchemy 参数化查询，禁止字符串拼接 SQL）."""

    @staticmethod
    async def load_status_map() -> dict[str, str]:
        """读取全部模块的持久化状态.

        Returns:
            ``{module_id: status}``（仅取显式列 id/status，非 ``SELECT *``）。
        """
        from openbase.core.db.session import get_session_factory

        statement = select(DynamicModule.id, DynamicModule.status)
        async with get_session_factory()() as session:
            rows = (await session.execute(statement)).all()
        return {row[0]: row[1] for row in rows}

    @staticmethod
    async def upsert_status(
        module_id: str,
        status: str,
        *,
        defaults: dict[str, Any] | None = None,
    ) -> None:
        """幂等 upsert 模块状态：行存在 → 仅 update ``status``；不存在 → insert 新行.

        Args:
            module_id: 模块标识（主键）。
            status: 目标状态（enabled / disabled）。
            defaults: 新建行时的注册表默认值（name/icon/route_prefix/entry/permission/
                sort_order）；缺失字段按模块标识推导，保证非空约束不违约。
        """
        from openbase.core.db.session import get_session_factory

        source = defaults or {}
        async with get_session_factory()() as session:
            existing = await session.get(DynamicModule, module_id)
            if existing is None:
                session.add(
                    DynamicModule(
                        id=module_id,
                        name=str(source.get("name") or module_id),
                        icon=source.get("icon"),
                        route_prefix=str(source.get("route_prefix") or f"/{module_id}"),
                        entry=str(source.get("entry") or f"modules/{module_id}"),
                        permission=str(source.get("permission") or ""),
                        status=status,
                        sort_order=int(source.get("sort_order") or 0),
                    )
                )
            else:
                # 语义不变（AC-146-15-4）：模块启停只改 status，不动注册身份字段
                existing.status = status
            await session.commit()

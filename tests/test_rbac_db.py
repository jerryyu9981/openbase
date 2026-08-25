"""RBAC 数据库权限矩阵测试（SQLite）：user → role → permission 查询链."""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from openbase.core.models import Base


@pytest.fixture()
def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def _setup():
        Base.metadata.schema = None
        for table in Base.metadata.tables.values():
            table.schema = None
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_setup())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    asyncio.run(engine.dispose())


def test_permission_service_db_query(session_factory):
    """数据库权限矩阵查询：user → role → permission."""
    from openbase.core.models import Permission, Role, User
    from openbase.core.models.base import role_permission, user_role
    from openbase.modules.auth.rbac import PermissionService

    async def main():
        async with session_factory() as s:
            # 用户/角色/权限 + 关联
            u = User(username="alice", password_hash="x", display_name="Alice", status=1)
            r = Role(name="编辑", code="editor", description="")
            p1 = Permission(code="doc:edit", name="编辑文档", module="doc", type=3)
            s.add_all([u, r, p1])
            await s.flush()
            await s.execute(user_role.insert().values(user_id=u.id, role_id=r.id))
            await s.execute(role_permission.insert().values(role_id=r.id, permission_id=p1.id))
            await s.commit()

            perms = await PermissionService.permissions_for(s, u.id)
            assert "doc:edit" in perms

            # 无权限用户
            u2 = User(username="bob", password_hash="y", display_name="Bob", status=1)
            s.add(u2)
            await s.commit()
            assert await PermissionService.permissions_for(s, u2.id) == []

    asyncio.run(main())


def test_permission_service_admin_wildcard(session_factory):
    """admin 角色通配 * 权限."""
    from openbase.core.models import Permission, Role, User
    from openbase.core.models.base import role_permission, user_role
    from openbase.modules.auth.rbac import PermissionService

    async def main():
        async with session_factory() as s:
            u = User(username="admin2", password_hash="x", display_name="Admin", status=1)
            r = Role(name="系统管理员", code="admin", description="")
            p = Permission(code="*", name="全部权限", module="system", type=3)
            s.add_all([u, r, p])
            await s.flush()
            await s.execute(user_role.insert().values(user_id=u.id, role_id=r.id))
            await s.execute(role_permission.insert().values(role_id=r.id, permission_id=p.id))
            await s.commit()

            perms = await PermissionService.permissions_for(s, u.id)
            assert "*" in perms

    asyncio.run(main())


def test_require_permission_fallback_store():
    """数据库不可用时 require_permission 回退 PermissionStore."""
    import asyncio

    from openbase.modules.auth.rbac import PermissionService, PermissionStore

    PermissionStore.configure_roles({"editor": ["doc:edit"]})
    PermissionStore.assign_role("42", "editor")

    async def main():
        # 伪造 session（查询抛异常 → 回退 store）
        class _BadSession:
            async def execute(self, *a, **k):
                raise RuntimeError("db down")

        perms = await PermissionService.permissions_for_with_fallback(_BadSession(), "42")
        assert "doc:edit" in perms

    asyncio.run(main())

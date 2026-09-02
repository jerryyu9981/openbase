"""OIDC 用户体系绑定单测（OB-AUTH-OIDC v1.3.0：JIT 自动建号 + sub 映射）.

覆盖: openbase/modules/auth/oidc.py _bind_or_create_user
使用 SQLite async 引擎（内存/临时文件），直测绑定策略。
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from openbase.core.models import Base, OidcIdentity, Role, User, user_role
from openbase.modules.auth.oidc import _bind_or_create_user

CLAIMS_ADMIN = {
    "iss": "http://127.0.0.1:8090",
    "sub": "oidc-sub-admin-001",
    "preferred_username": "oidc-admin",
    "email": "oidc-admin@openbase.local",
    "name": "OIDC Admin",
    "roles": ["org_admin"],
}


@pytest.fixture()
async def session():
    """SQLite async 会话（内存库 + 幂等建表 + 基础角色种子）. """
    # 防御测试隔离：init_db 可能把 Base 表 schema 全局置为 openbase（PG 场景），
    # SQLite 无 schema 概念，建表前统一重置为 None，避免跨文件污染
    for table in Base.metadata.tables.values():
        table.schema = None
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        # 基础角色种子（对应 core/db/init.py 幂等种子）
        for code, name in (("viewer", "只读用户"), ("user", "普通用户"), ("org_admin", "组织管理员")):
            sess.add(Role(name=name, code=code, description="", is_system=True))
        await sess.commit()
        yield sess
    await engine.dispose()


async def _count(sess, model) -> int:
    result = await sess.execute(select(model))
    return len(result.scalars().all())


@pytest.mark.asyncio
async def test_jit_create_binds_mapping_and_role(session):
    """首次 OIDC 登录：JIT 建号 + OidcIdentity 映射 + org_admin 角色绑定. """
    bound = await _bind_or_create_user(CLAIMS_ADMIN, session)
    assert bound is not None
    assert bound["username"] == "oidc-admin"
    assert bound["role"] == "org_admin"

    # users 表 1 行（无重复）+ oidc_identity 1 行
    assert await _count(session, User) == 1
    assert await _count(session, OidcIdentity) == 1

    # 用户存在且密码不可登录（随机占位哈希）
    result = await session.execute(select(User).where(User.username == "oidc-admin"))
    user = result.scalar_one()
    assert user.email == "oidc-admin@openbase.local"
    assert user.status == 1
    # user_role 绑定 org_admin
    r_res = await session.execute(
        select(Role).join(user_role, user_role.c.role_id == Role.id).where(user_role.c.user_id == user.id)
    )
    role_codes = [r.code for r in r_res.scalars().all()]
    assert "org_admin" in role_codes


@pytest.mark.asyncio
async def test_reuse_existing_identity(session):
    """二次 OIDC 登录：按 sub 复用既有用户（不重复建号，id 一致）. """
    first = await _bind_or_create_user(CLAIMS_ADMIN, session)
    assert first is not None
    second = await _bind_or_create_user(CLAIMS_ADMIN, session)
    assert second is not None
    assert second["id"] == first["id"]
    assert await _count(session, User) == 1
    assert await _count(session, OidcIdentity) == 1


@pytest.mark.asyncio
async def test_username_conflict_gets_suffix(session):
    """用户名冲突（已存在同 username）：自动加随机后缀保持唯一. """
    # 预置同用户名用户（如管理员手动创建）
    session.add(
        User(
            username="oidc-admin",
            password_hash="x",
            display_name="Existing",
            status=1,
        )
    )
    await session.commit()
    bound = await _bind_or_create_user(CLAIMS_ADMIN, session)
    assert bound is not None
    assert bound["username"].startswith("oidc-admin-")
    assert await _count(session, User) == 2


@pytest.mark.asyncio
async def test_role_mapping_filters_unknown_roles(session):
    """角色映射：claims roles 仅绑定已知 Role.code，未知忽略. """
    claims = dict(CLAIMS_ADMIN, roles=["org_admin", "super_hero", "user"])
    bound = await _bind_or_create_user(claims, session)
    assert bound is not None
    assert bound["role"] == "org_admin"
    result = await session.execute(select(User).where(User.username == "oidc-admin"))
    user = result.scalar_one()
    r_res = await session.execute(
        select(Role.code).join(user_role, user_role.c.role_id == Role.id).where(user_role.c.user_id == user.id)
    )
    codes = list(r_res.scalars().all())
    assert "org_admin" in codes and "user" in codes and "super_hero" not in codes


@pytest.mark.asyncio
async def test_db_failure_returns_none(session):
    """DB 异常：返回 None（调用方降级以 IdP sub 直签，网关可用性优先）. """
    # 关闭连接使查询抛异常 → 绑定返回 None
    await session.close()
    broken_session = AsyncSession(bind=None)
    result = await _bind_or_create_user(CLAIMS_ADMIN, broken_session)
    assert result is None

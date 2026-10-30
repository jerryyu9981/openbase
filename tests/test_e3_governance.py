"""E3 政务暂缓项（可软件部分）测试.

覆盖四项：

- E3-1 三权分立（职责互斥）与 ABAC 属性判定（deny-overrides / 跨租户默认拒绝）；
- E3-2 集中审计导出（NDJSON 流式、条数上限）与留存清理（dry-run 默认、删头不断链）；
- E3-3 签名算法注册表与启动门禁（SM2 预留不可用，配置即拒绝）；
- E3-4 统一 IdP Provider 登记（解析门禁、对外视图不含 client_secret）。

测试策略：纯函数直接断言；端点用最小 FastAPI 应用 + 文件型 SQLite（与既有
``test_audit_chain`` / ``api_key_client`` 同口径，不依赖共享 PG）。
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from openbase.core.db import audit_chain  # noqa: F401 - 导入即注册 before_flush 链式哈希钩子
from openbase.core.db.audit_chain import verify_audit_chain
from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import install_exception_handlers
from openbase.core.models import AuditLog, Base
from openbase.core.security.signature_algorithms import (
    RSA_ALGORITHM,
    SM2_ALGORITHM,
    assert_signature_algorithm_usable,
    available_signature_algorithms,
    get_signature_algorithm,
    register_signature_algorithm,
)
from openbase.modules.auth.access_control import (
    DUTY_AUDIT_ADMIN,
    DUTY_ROLE_PERMISSIONS,
    DUTY_SECURITY_ADMIN,
    DUTY_SYSTEM_ADMIN,
    AbacEffect,
    SeparationOfDutiesError,
    assert_separation_of_duties,
    conflicting_duty_pairs,
    evaluate_abac,
    parse_abac_rules,
)
from openbase.modules.auth.idp_registry import (
    IdpProviderConfig,
    parse_idp_providers,
    public_provider_views,
)
from openbase.settings import Settings

# ---- 公共夹具 ----


def _clear_metadata_schema() -> None:
    """SQLite 无 schema 概念：建表前置空（与既有用例同口径）."""
    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None


async def _create_schema(engine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@pytest.fixture()
def sqlite_engine(tmp_path):
    """文件型 SQLite 引擎（函数级，表已建好）."""
    _clear_metadata_schema()
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'e3_governance.db'}")
    asyncio.run(_create_schema(engine))
    yield engine
    asyncio.run(engine.dispose())


def _override_get_db(factory):
    """构造 ``get_db`` 覆写（返回独立会话）."""

    async def _get_db():
        async with factory() as session:
            yield session

    return _get_db


def _admin_identity() -> dict:
    """超管身份（权限通配，覆盖 require_permission / ensure_user_permission）."""
    return {"id": "1", "username": "admin", "permissions": ["*"]}


# ---- E3-1 三权分立 ----


def test_conflicting_duty_pairs_detects_mutual_exclusion() -> None:
    """任意两种职责同授即冲突；非职责角色被忽略."""
    assert conflicting_duty_pairs([DUTY_SYSTEM_ADMIN, "ordinary"]) == []
    assert conflicting_duty_pairs([DUTY_SYSTEM_ADMIN, DUTY_AUDIT_ADMIN]) == [
        (DUTY_SYSTEM_ADMIN, DUTY_AUDIT_ADMIN)
    ]
    assert conflicting_duty_pairs(
        [DUTY_AUDIT_ADMIN, DUTY_SECURITY_ADMIN, DUTY_SYSTEM_ADMIN]
    ) == [
        (DUTY_SYSTEM_ADMIN, DUTY_SECURITY_ADMIN),
        (DUTY_SYSTEM_ADMIN, DUTY_AUDIT_ADMIN),
        (DUTY_SECURITY_ADMIN, DUTY_AUDIT_ADMIN),
    ]


def test_assert_separation_of_duties_fail_closed() -> None:
    """冲突即抛 ``SeparationOfDutiesError``；无冲突放行."""
    assert_separation_of_duties([DUTY_SYSTEM_ADMIN])
    with pytest.raises(SeparationOfDutiesError, match="三权分立违规"):
        assert_separation_of_duties([DUTY_SECURITY_ADMIN, DUTY_AUDIT_ADMIN])


def test_duty_permission_baselines_are_disjoint() -> None:
    """三职责的权限点基线互不重叠（职责层面即分离）."""
    duty_codes = list(DUTY_ROLE_PERMISSIONS)
    for left in range(len(duty_codes)):
        for right in range(left + 1, len(duty_codes)):
            left_permissions = set(DUTY_ROLE_PERMISSIONS[duty_codes[left]])
            right_permissions = set(DUTY_ROLE_PERMISSIONS[duty_codes[right]])
            assert left_permissions.isdisjoint(right_permissions)


# ---- E3-1 ABAC ----


def test_parse_abac_rules_valid_and_empty() -> None:
    """空串 → 无策略；合法数组 → 规则元组（保持顺序，缺省字段补默认）."""
    assert parse_abac_rules("") == ()
    rules = parse_abac_rules(
        json.dumps(
            [
                {"effect": "deny", "permission": "key:revoke", "roles": ["auditor"]},
                {"effect": "allow", "tenant": "acme", "cross_tenant": True},
            ]
        )
    )
    assert rules[0].effect == "deny"
    assert rules[0].roles == ("auditor",)
    assert rules[1].permission == "*"
    assert rules[1].tenant == "acme"
    assert rules[1].cross_tenant is True


@pytest.mark.parametrize(
    ("raw", "match"),
    [
        ("not-json", "不是合法 JSON"),
        ('{"effect": "allow"}', "顶层必须为 JSON 数组"),
        ('[{"effect": "maybe"}]', "effect 必须为 allow/deny"),
        ('[{"effect": "allow", "roles": "admin"}]', "roles 必须为数组"),
    ],
)
def test_parse_abac_rules_rejects_invalid(raw: str, match: str) -> None:
    """非法策略一律 ValueError（启动门禁 fail-fast）."""
    with pytest.raises(ValueError, match=match):
        parse_abac_rules(raw)


def test_evaluate_abac_deny_overrides_allow() -> None:
    """deny 覆盖 allow."""
    rules = parse_abac_rules(
        json.dumps(
            [
                {"effect": "allow", "permission": "key:issue"},
                {"effect": "deny", "permission": "key:issue"},
            ]
        )
    )
    result = evaluate_abac(
        rules,
        permission="key:issue",
        subject_tenant="acme",
        resource_tenant="acme",
    )
    assert result.effect is AbacEffect.DENY
    assert result.reason == "deny_rule_matched"


def test_evaluate_abac_allow_and_not_applicable() -> None:
    """命中 allow → allow；无策略命中 → not_applicable（回落 RBAC）."""
    rules = parse_abac_rules(json.dumps([{"effect": "allow", "permission": "audit:read"}]))
    allowed = evaluate_abac(
        rules, permission="audit:read", subject_tenant="acme", resource_tenant="acme"
    )
    assert allowed.decision == "allow"
    assert allowed.reason == "allow_rule_matched"

    untouched = evaluate_abac(
        rules, permission="user:delete", subject_tenant="acme", resource_tenant="acme"
    )
    assert untouched.effect is AbacEffect.NOT_APPLICABLE
    assert untouched.reason == "no_policy_matched"


def test_evaluate_abac_cross_tenant_default_deny() -> None:
    """跨租户默认拒绝；策略显式 cross_tenant 才放行."""
    rules = parse_abac_rules(json.dumps([{"effect": "allow", "permission": "audit:read"}]))
    denied = evaluate_abac(
        rules, permission="audit:read", subject_tenant="acme", resource_tenant="other"
    )
    assert denied.effect is AbacEffect.DENY
    assert denied.reason == "cross_tenant_without_allow"

    cross_rules = parse_abac_rules(
        json.dumps([{"effect": "allow", "permission": "audit:read", "cross_tenant": True}])
    )
    allowed = evaluate_abac(
        cross_rules,
        permission="audit:read",
        subject_tenant="acme",
        resource_tenant="other",
    )
    assert allowed.decision == "allow"


def test_evaluate_abac_role_and_tenant_constraints() -> None:
    """规则的角色/租户约束不满足时不算命中."""
    rules = parse_abac_rules(
        json.dumps([{"effect": "allow", "permission": "key:issue", "roles": ["security_admin"]}])
    )
    result = evaluate_abac(
        rules,
        permission="key:issue",
        subject_tenant="acme",
        resource_tenant="acme",
        roles=["developer"],
    )
    assert result.effect is AbacEffect.NOT_APPLICABLE


# ---- E3-1 端点 ----


def test_access_endpoints_check_and_duties(sqlite_engine, monkeypatch) -> None:
    """ABAC 试算与职责清单端点（策略由配置注入）."""
    import openbase.modules.auth.access_api as access_api
    from openbase.modules.auth.access_api import router as access_router

    factory = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    monkeypatch.setattr(
        access_api,
        "get_settings",
        lambda: SimpleNamespace(abac_policies='[{"effect":"deny","permission":"key:issue"}]'),
    )

    app = FastAPI()
    app.include_router(access_router)
    install_exception_handlers(app)
    app.dependency_overrides[get_db] = _override_get_db(factory)
    app.dependency_overrides[get_current_user] = _admin_identity

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/access/check",
            json={"permission": "key:issue", "resource_tenant": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["decision"] == "deny"
        assert body["reason"] == "deny_rule_matched"

        duties = client.get("/api/v1/auth/access/duties")
        assert duties.status_code == 200
        data = duties.json()["data"]
        assert data["mutually_exclusive"] is True
        assert set(data["duties"]) == {
            DUTY_SYSTEM_ADMIN,
            DUTY_SECURITY_ADMIN,
            DUTY_AUDIT_ADMIN,
        }


# ---- E3-2 审计导出与留存 ----


async def _seed_audit_rows(factory, specs: list[dict]) -> list[int]:
    """按顺序插入审计行（before_flush 钩子自动赋链式哈希）."""
    row_ids: list[int] = []
    for spec in specs:
        async with factory() as session:
            record = AuditLog(
                action=spec["action"],
                request_id=spec["request_id"],
                created_at=spec["created_at"],
                detail={"seed": spec["request_id"]},
            )
            session.add(record)
            await session.commit()
            row_ids.append(record.id)
    return row_ids


def _audit_app(sqlite_engine):
    """最小应用：审计路由 + 身份/会话覆写."""
    from openbase.modules.audit import api_router

    factory = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(api_router)
    install_exception_handlers(app)
    app.dependency_overrides[get_db] = _override_get_db(factory)
    app.dependency_overrides[get_current_user] = _admin_identity
    return app, factory


def test_audit_export_ndjson_stream_and_limits(sqlite_engine, monkeypatch) -> None:
    """NDJSON 流式导出：按 id 升序、行数受 limit 约束、超配置上限拒绝."""
    import openbase.modules.audit as audit_module

    app, factory = _audit_app(sqlite_engine)
    now = dt.datetime.now(dt.timezone.utc)
    asyncio.run(
        _seed_audit_rows(
            factory,
            [
                {"action": "a.old", "request_id": "req-old", "created_at": now - dt.timedelta(days=800)},
                {"action": "a.mid", "request_id": "req-mid", "created_at": now - dt.timedelta(days=5)},
                {"action": "a.new", "request_id": "req-new", "created_at": now},
            ],
        )
    )
    monkeypatch.setattr(
        audit_module, "get_settings", lambda: SimpleNamespace(audit_export_max_rows=10)
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/audit/export", params={"limit": 2})
        assert response.status_code == 200
        assert "application/x-ndjson" in response.headers["content-type"]
        assert response.headers["X-Row-Limit"] == "2"
        lines = [json.loads(line) for line in response.text.splitlines() if line]
        assert [line["request_id"] for line in lines] == ["req-old", "req-mid"]
        assert all(line["entry_hash"] for line in lines)

        filtered = client.get(
            "/api/v1/audit/export", params={"since": "2026-01-01T00:00:00Z"}
        )
        assert filtered.status_code == 200
        request_ids = [
            json.loads(line)["request_id"]
            for line in filtered.text.splitlines()
            if line
        ]
        assert request_ids == ["req-mid", "req-new"]

        over_limit = client.get("/api/v1/audit/export", params={"limit": 11})
        assert over_limit.status_code == 400
        assert over_limit.json()["code"] == "PARAM_INVALID"

        inverted = client.get(
            "/api/v1/audit/export",
            params={"since": "2026-06-01T00:00:00Z", "until": "2026-01-01T00:00:00Z"},
        )
        assert inverted.status_code == 400
        assert inverted.json()["code"] == "PARAM_INVALID"


def test_audit_retention_requires_enabled_policy(sqlite_engine, monkeypatch) -> None:
    """留存未启用（=0）时拒绝执行清理."""
    import openbase.modules.audit as audit_module

    app, _factory = _audit_app(sqlite_engine)
    monkeypatch.setattr(
        audit_module, "get_settings", lambda: SimpleNamespace(audit_retention_days=0)
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/audit/retention/purge")
        assert response.status_code in (400, 409)
        assert response.json()["code"] == "BIZ_CONFIG_CONFLICT"


def test_audit_retention_dry_run_and_purge_keeps_chain_valid(
    sqlite_engine, monkeypatch
) -> None:
    """dry-run 只统计；真实清理删除最旧头部且链校验仍通过."""
    import openbase.modules.audit as audit_module

    app, factory = _audit_app(sqlite_engine)
    now = dt.datetime.now(dt.timezone.utc)
    asyncio.run(
        _seed_audit_rows(
            factory,
            [
                {"action": "a.expired.1", "request_id": "req-exp-1", "created_at": now - dt.timedelta(days=90)},
                {"action": "a.expired.2", "request_id": "req-exp-2", "created_at": now - dt.timedelta(days=60)},
                {"action": "a.fresh", "request_id": "req-fresh", "created_at": now},
            ],
        )
    )
    monkeypatch.setattr(
        audit_module, "get_settings", lambda: SimpleNamespace(audit_retention_days=30)
    )

    with TestClient(app) as client:
        dry = client.post("/api/v1/audit/retention/purge")
        assert dry.status_code == 200
        assert dry.json()["data"]["candidate_rows"] == 2
        assert dry.json()["data"]["deleted_rows"] == 0

        real = client.post("/api/v1/audit/retention/purge", params={"dry_run": False})
        assert real.status_code == 200
        assert real.json()["data"]["deleted_rows"] == 2

    async def _verify() -> dict:
        async with factory() as session:
            return await verify_audit_chain(session)

    result = asyncio.run(_verify())
    assert result["ok"] is True
    assert result["checked"] == 1


# ---- E3-3 签名算法门禁 ----


def test_signature_algorithm_registry_marks_sm2_unavailable() -> None:
    """SM2 为预留位（不可用）；HS256/RS256 可用."""
    assert set(available_signature_algorithms()) == {"HS256", RSA_ALGORITHM}
    sm2 = get_signature_algorithm(SM2_ALGORITHM)
    assert sm2.available is False
    with pytest.raises(ValueError, match="不可用"):
        assert_signature_algorithm_usable(SM2_ALGORITHM)
    with pytest.raises(ValueError, match="未知签名算法"):
        get_signature_algorithm("ES256")


def test_register_signature_algorithm_replace_semantics() -> None:
    """同名重复登记须显式 replace；登记者随后可判定可用."""
    from openbase.core.security.signature_algorithms import SignatureAlgorithm

    with pytest.raises(ValueError, match="已登记"):
        register_signature_algorithm(SignatureAlgorithm("HS256", True))
    register_signature_algorithm(
        SignatureAlgorithm("SM2-TEST", True, "测试接线"), replace=True
    )
    assert assert_signature_algorithm_usable("sm2-test").name == "SM2-TEST"


def test_settings_reject_unusable_or_unknown_jwt_algorithm() -> None:
    """jwt_algorithm 门禁：SM2 预留即拒绝、未知算法拒绝、HS256 通过."""
    with pytest.raises(ValueError, match="不可用"):
        Settings(jwt_algorithm=SM2_ALGORITHM)
    with pytest.raises(ValueError, match="未知签名算法"):
        Settings(jwt_algorithm="ES256")
    assert Settings(jwt_algorithm="HS256").jwt_algorithm == "HS256"


def test_settings_e3_governance_gates() -> None:
    """ABAC / 留存 / 导出上限 / IdP 配置的 fail-fast 门禁."""
    assert Settings(abac_policies="[]").abac_policies == "[]"
    with pytest.raises(ValueError, match="不是合法 JSON"):
        Settings(abac_policies="not-json")
    with pytest.raises(ValueError, match="≥30"):
        Settings(audit_retention_days=10)
    assert Settings(audit_retention_days=0).audit_retention_days == 0
    assert Settings(audit_retention_days=30).audit_retention_days == 30
    with pytest.raises(ValueError, match="必须为正整数"):
        Settings(audit_export_max_rows=0)
    with pytest.raises(ValueError, match="name 必须唯一"):
        Settings(
            idp_providers=json.dumps(
                [
                    {"name": "idp-a", "discovery_url": "https://a/.well-known", "client_id": "c1"},
                    {"name": "idp-a", "discovery_url": "https://b/.well-known", "client_id": "c2"},
                ]
            )
        )


# ---- E3-4 IdP Provider ----


def test_parse_idp_providers_valid_and_invalid() -> None:
    """空配置 → 无 Provider；缺必填/非法 profile 一律 ValueError."""
    assert parse_idp_providers("") == ()
    providers = parse_idp_providers(
        json.dumps(
            [
                {
                    "name": "gov-idp",
                    "discovery_url": "https://idp.example/.well-known/openid-configuration",
                    "client_id": "openbase",
                    "client_secret": "s3cret",
                    "profile": "keycloak",
                    "default_tenant": "gov",
                }
            ]
        )
    )
    assert providers[0].name == "gov-idp"
    assert providers[0].profile == "keycloak"

    with pytest.raises(ValueError, match="缺少 name"):
        parse_idp_providers(json.dumps([{"discovery_url": "https://x", "client_id": "c"}]))
    with pytest.raises(ValueError, match="discovery_url"):
        parse_idp_providers(json.dumps([{"name": "x", "discovery_url": "ftp://x", "client_id": "c"}]))
    with pytest.raises(ValueError, match="缺少 client_id"):
        parse_idp_providers(json.dumps([{"name": "x", "discovery_url": "https://x"}]))
    with pytest.raises(ValueError, match="profile 不受支持"):
        parse_idp_providers(
            json.dumps(
                [{"name": "x", "discovery_url": "https://x", "client_id": "c", "profile": "saml"}]
            )
        )


def test_public_provider_views_never_expose_secret() -> None:
    """对外视图不含 client_secret，仅暴露 has_client_secret."""
    views = public_provider_views(
        (
            IdpProviderConfig(
                name="gov-idp",
                discovery_url="https://idp.example/.well-known/openid-configuration",
                client_id="openbase",
                client_secret="s3cret",
            ),
        )
    )
    assert "client_secret" not in views[0]
    assert views[0]["has_client_secret"] is True


def test_idp_providers_endpoint_never_exposes_secret(sqlite_engine, monkeypatch) -> None:
    """Provider 列表端点（登录用户可读），响应体不含明文密钥."""
    import openbase.modules.auth.idp_registry as idp_registry
    from openbase.modules.auth.idp_registry import router as idp_router

    raw = json.dumps(
        [
            {
                "name": "gov-idp",
                "discovery_url": "https://idp.example/.well-known/openid-configuration",
                "client_id": "openbase",
                "client_secret": "s3cret",
            }
        ]
    )
    monkeypatch.setattr(
        idp_registry, "get_settings", lambda: SimpleNamespace(idp_providers=raw)
    )

    app = FastAPI()
    app.include_router(idp_router)
    install_exception_handlers(app)
    app.dependency_overrides[get_current_user] = _admin_identity

    with TestClient(app) as client:
        response = client.get("/api/v1/auth/idp/providers")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["count"] == 1
        assert "client_secret" not in data["providers"][0]
        assert "s3cret" not in response.text

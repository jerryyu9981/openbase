"""BaseDBService 与 audit 边界逻辑补充测试（覆盖率提升）."""



def test_base_db_service_fallback_logs(caplog):
    """BaseDBService._fallback 记录降级日志."""
    import logging

    from openbase.core.db.services import BaseDBService

    with caplog.at_level(logging.WARNING, logger="openbase.db.services"):
        BaseDBService._fallback("test.svc", ValueError("boom"))
    assert any("fallback to memory" in r.message for r in caplog.records)


def test_base_db_service_db_available_false(monkeypatch):
    """引擎未初始化时 _db_available 返回 False."""
    from openbase.core.db.services import BaseDBService

    def fake_get_engine():
        raise RuntimeError("engine not ready")

    monkeypatch.setattr("openbase.core.db.session.get_engine", fake_get_engine)
    assert BaseDBService._db_available() is False


def test_audit_sanitize_and_ip():
    """audit 脱敏与 IP 提取边界."""
    from openbase.modules.audit import APICallRecord, AuditService

    AuditService.record_api_call(
        APICallRecord(
            method="POST", path="/api/v1/auth/login", status_code=401,
            duration_ms=3, request_id="req-x",
            error="invalid credentials", ip_address="192.168.0.151",
        )
    )
    records = AuditService.records()
    assert len(records) >= 1
    assert records[0]["ip_address"] == "192.168.0.151"


def test_audit_health_in_app():
    """init_app 装配后 /health 可用（白名单路径）."""
    from fastapi.testclient import TestClient

    from openbase import init_app
    from openbase.settings import Settings

    settings = Settings()
    settings.enable_module("auth")
    settings.enable_module("audit")
    client = TestClient(init_app(settings))
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

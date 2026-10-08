"""JWT 密钥管理单测（v1.7.0）.

覆盖：production 弱密钥拒绝 / development 放行 / 签发 fail-closed / 轮换双密钥验签宽限
"""
import sys

import pytest
from pydantic import ValidationError

from openbase.modules.auth.jwt import (
    _sign_secret,
    create_access_token,
    decode_access_token,
)
from openbase.settings import WEAK_JWT_SECRETS

STRONG = "x9kQ2vR8pLmN4cJ6tWzY3uEaFhG1sBd0iK5nM7qPrS"  # 42 字符强随机示例
OLD = "v8pQ2aR4sT6uW8yZ0cE3gI5kM7oQ9sU1wY4"  # 旧密钥（轮换宽限）


def _module():
    # openbase/__init__.py 将包属性 settings 覆盖为实例；须经 sys.modules 取真模块
    return sys.modules["openbase.settings"]


@pytest.fixture(autouse=True)
def _reset_settings():
    """每个用例重置 settings 单例，避免跨用例污染. """
    _module()._settings = None
    yield
    _module()._settings = None


def _make(env: str = "development", secret: str = STRONG, previous: str = "") -> object:
    s = _module().Settings(env=env, jwt_secret=secret, jwt_secret_previous=previous)
    _module()._settings = s
    return s


# ---------------------------------------------------------------------------
# settings 校验器
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("weak", sorted(WEAK_JWT_SECRETS))
def test_production_rejects_weak_secret(weak):
    """production：空/占位/演示密钥一律启动失败（fail-fast）. """
    with pytest.raises(ValidationError):
        _module().Settings(env="production", jwt_secret=weak)


def test_production_requires_min_length():
    with pytest.raises(ValidationError):
        _module().Settings(env="production", jwt_secret="short-secret")


def test_production_accepts_strong_secret():
    """production + 强密钥 + 吊销强校验开启 → 通过（B4 生产门禁要求 enforce=True）."""
    s = _module().Settings(env="production", jwt_secret=STRONG, enforce_token_version=True)
    assert s.jwt_secret == STRONG


def test_development_allows_weak_with_warning():
    s = _module().Settings(env="development", jwt_secret="test-jwt-secret-for-v680")
    assert s.jwt_secret == "test-jwt-secret-for-v680"


# ---------------------------------------------------------------------------
# 签发 fail-closed
# ---------------------------------------------------------------------------


def test_sign_requires_configured_secret():
    _make(secret="")  # development + 空
    with pytest.raises(ValueError):
        _sign_secret()


# ---------------------------------------------------------------------------
# 轮换宽限
# ---------------------------------------------------------------------------


def test_rotation_old_token_still_verifies():
    """轮换中：旧密钥签发 token 在（新当前 + previous=旧）配置下验签通过. """
    _make(secret=STRONG, previous=OLD)
    from jose import jwt as jose_jwt

    old_token = jose_jwt.encode({"sub": "1", "type": "access"}, OLD, algorithm="HS256")
    payload = decode_access_token(old_token)
    assert payload is not None and payload["sub"] == "1"


def test_rotation_new_token_verifies_and_sign_uses_current():
    """新密钥签发 token 验签通过；签发始终用当前密钥（旧密钥不可伪造新签发）. """
    _make(secret=STRONG, previous=OLD)
    from jose import JWTError
    from jose import jwt as jose_jwt

    new_token = create_access_token("2")
    payload = decode_access_token(new_token)
    assert payload is not None and payload["sub"] == "2"
    # 新签发 token 用旧密钥验签应失败（签发密钥 = 当前密钥）
    with pytest.raises(JWTError):
        jose_jwt.decode(new_token, OLD, algorithms=["HS256"])


def test_rotation_complete_old_secret_removed():
    """轮换完成（移除 previous）：旧密钥 token 验签失败（宽限期结束）. """
    _make(secret=STRONG, previous="")
    from jose import jwt as jose_jwt

    old_token = jose_jwt.encode({"sub": "3", "type": "access"}, OLD, algorithm="HS256")
    assert decode_access_token(old_token) is None


def test_import_order_no_side_effects():
    """WEAK_JWT_SECRETS 定义完整（已知弱值全覆盖）. """
    assert "test-jwt-secret-for-v680" in WEAK_JWT_SECRETS
    assert "change-me-in-production" in WEAK_JWT_SECRETS
    assert "" in WEAK_JWT_SECRETS

"""Tests for admin-api Settings JWT validation (issue #109)."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# admin-api/ is a service package — add it to sys.path so `app.core.config` resolves
# the same way it does at runtime inside the admin-api container.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ADMIN_API_ROOT = _PROJECT_ROOT / "admin-api"
if str(_ADMIN_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_ADMIN_API_ROOT))

from app.core import config as config_module  # type: ignore  # noqa: E402
from app.core.config import (  # type: ignore  # noqa: E402
    JWT_SECRET_MIN_LENGTH,
    KNOWN_WEAK_JWT_SECRETS,
    Settings,
    get_settings,
)

_VALID_LONG_SECRET = "a" * JWT_SECRET_MIN_LENGTH
_BASE_VALID_KWARGS = {
    "mongo_uri": "mongodb://user:pass@host:27017",
    "admin_username": "alice",
    "admin_password_hash": "$2b$12$abc",
    "cors_origins": "http://localhost:3000",
}


def _settings(**overrides) -> Settings:
    kwargs = {**_BASE_VALID_KWARGS, "jwt_secret": _VALID_LONG_SECRET, **overrides}
    return Settings(**kwargs)


@pytest.mark.parametrize("weak", sorted(KNOWN_WEAK_JWT_SECRETS))
def test_validate_rejects_known_weak_jwt_secrets(weak: str) -> None:
    is_valid, missing = _settings(jwt_secret=weak).validate_required_secrets()
    assert is_valid is False
    assert any("JWT_SECRET" in m for m in missing), missing


@pytest.mark.parametrize("weak", sorted(KNOWN_WEAK_JWT_SECRETS))
def test_validate_rejects_known_weak_case_insensitive(weak: str) -> None:
    is_valid, missing = _settings(jwt_secret=weak.upper()).validate_required_secrets()
    assert is_valid is False
    assert any("known-weak" in m for m in missing), missing


def test_validate_rejects_short_secret() -> None:
    is_valid, missing = _settings(jwt_secret="short").validate_required_secrets()
    assert is_valid is False
    assert any("too short" in m for m in missing), missing


def test_validate_rejects_empty_secret() -> None:
    is_valid, missing = _settings(jwt_secret="").validate_required_secrets()
    assert is_valid is False
    assert "JWT_SECRET" in missing


def test_validate_accepts_strong_secret() -> None:
    is_valid, missing = _settings(jwt_secret=_VALID_LONG_SECRET).validate_required_secrets()
    assert is_valid is True, missing
    assert missing == []


def test_validate_accepts_64_char_boundary() -> None:
    boundary = "x" * JWT_SECRET_MIN_LENGTH
    is_valid, _ = _settings(jwt_secret=boundary).validate_required_secrets()
    assert is_valid is True


def test_validate_rejects_63_char_just_below_boundary() -> None:
    below = "x" * (JWT_SECRET_MIN_LENGTH - 1)
    is_valid, missing = _settings(jwt_secret=below).validate_required_secrets()
    assert is_valid is False
    assert any("too short" in m for m in missing), missing


def test_get_settings_raises_on_weak_value_from_env() -> None:
    get_settings.cache_clear()

    fake_manager = mock.Mock()
    fake_manager.get_secret.return_value = None  # Force env-var fallback

    env = {
        "MONGO_URI": "mongodb://user:pass@host:27017",
        "ADMIN_USERNAME": "alice",
        "ADMIN_PASSWORD_HASH": "$2b$12$abc",
        "JWT_SECRET": "testsecret",
        "CORS_ORIGINS": "http://localhost:3000",
    }

    with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(
        config_module, "get_secret_manager", return_value=fake_manager
    ):
        with pytest.raises(ValueError, match="JWT_SECRET"):
            get_settings()

    get_settings.cache_clear()


def test_get_settings_accepts_valid_env() -> None:
    get_settings.cache_clear()

    fake_manager = mock.Mock()
    fake_manager.get_secret.return_value = None

    env = {
        "MONGO_URI": "mongodb://user:pass@host:27017",
        "ADMIN_USERNAME": "alice",
        "ADMIN_PASSWORD_HASH": "$2b$12$abc",
        "JWT_SECRET": _VALID_LONG_SECRET,
        "CORS_ORIGINS": "http://localhost:3000",
    }

    with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(
        config_module, "get_secret_manager", return_value=fake_manager
    ):
        settings = get_settings()
        assert settings.jwt_secret == _VALID_LONG_SECRET

    get_settings.cache_clear()

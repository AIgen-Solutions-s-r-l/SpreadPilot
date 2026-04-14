"""Tests for admin-api CORS hardening (issue #111)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load cors.py by absolute path to avoid the `app` package-name collision
# between admin-api/app/ and trading-bot/app/ that otherwise breaks in CI
# (where both are on PYTHONPATH).
_CORS_PATH = Path(__file__).resolve().parents[2] / "admin-api" / "app" / "core" / "cors.py"
_spec = importlib.util.spec_from_file_location("_admin_api_cors", _CORS_PATH)
assert _spec and _spec.loader
_admin_api_cors = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_admin_api_cors)
configure_cors = _admin_api_cors.configure_cors


def _settings(cors_origins: str) -> SimpleNamespace:
    # The helper only needs `.cors_origins`; a namespace is enough and keeps the
    # test decoupled from the full Settings model.
    return SimpleNamespace(cors_origins=cors_origins)


def _cors_middleware_options(app: FastAPI) -> dict:
    for middleware in app.user_middleware:
        if middleware.cls is CORSMiddleware:
            return middleware.kwargs
    raise AssertionError("CORSMiddleware not registered on app")


def test_rejects_empty_cors_origins() -> None:
    app = FastAPI()
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        configure_cors(app, _settings(""))


def test_rejects_exact_wildcard() -> None:
    app = FastAPI()
    with pytest.raises(ValueError, match=r"[Ww]ildcard"):
        configure_cors(app, _settings("*"))


def test_rejects_wildcard_in_comma_separated_list() -> None:
    app = FastAPI()
    with pytest.raises(ValueError, match=r"[Ww]ildcard"):
        configure_cors(app, _settings("http://localhost:3000,*"))


def test_accepts_single_valid_origin() -> None:
    app = FastAPI()
    configure_cors(app, _settings("http://localhost:3000"))
    opts = _cors_middleware_options(app)
    assert opts["allow_origins"] == ["http://localhost:3000"]


def test_accepts_multiple_valid_origins_trimming_whitespace() -> None:
    app = FastAPI()
    configure_cors(app, _settings(" http://localhost:3000 , https://app.example.com "))
    opts = _cors_middleware_options(app)
    assert opts["allow_origins"] == ["http://localhost:3000", "https://app.example.com"]


def test_credentials_enabled_and_origins_are_never_wildcard() -> None:
    """Unconditional assertion: credentials on, wildcard off, always together."""
    app = FastAPI()
    configure_cors(app, _settings("http://localhost:3000"))
    opts = _cors_middleware_options(app)
    assert opts["allow_credentials"] is True
    assert "*" not in opts["allow_origins"]


def test_methods_are_explicit_allowlist_not_wildcard() -> None:
    app = FastAPI()
    configure_cors(app, _settings("http://localhost:3000"))
    opts = _cors_middleware_options(app)
    assert opts["allow_methods"] != ["*"]
    assert set(opts["allow_methods"]) == {"GET", "POST", "PUT", "DELETE", "OPTIONS"}


def test_headers_are_explicit_allowlist_not_wildcard() -> None:
    app = FastAPI()
    configure_cors(app, _settings("http://localhost:3000"))
    opts = _cors_middleware_options(app)
    assert opts["allow_headers"] != ["*"]
    assert set(opts["allow_headers"]) == {"Content-Type", "Authorization"}


def test_expose_headers_is_not_set() -> None:
    """expose_headers defaults to [] when unset, never ['*']."""
    app = FastAPI()
    configure_cors(app, _settings("http://localhost:3000"))
    opts = _cors_middleware_options(app)
    assert opts.get("expose_headers", []) == []


def test_rejects_whitespace_only_origin() -> None:
    """A single whitespace entry is equivalent to empty — must fail fast."""
    app = FastAPI()
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        configure_cors(app, _settings("   "))

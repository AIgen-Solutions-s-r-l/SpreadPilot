"""Tests for admin-api CORS hardening (issue #111)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ADMIN_API_ROOT = _PROJECT_ROOT / "admin-api"
if str(_ADMIN_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_ADMIN_API_ROOT))

from app.core.cors import configure_cors  # type: ignore


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


def test_credentials_never_combined_with_wildcard() -> None:
    """After configure_cors, if credentials are allowed, origins must not be ['*']."""
    app = FastAPI()
    configure_cors(app, _settings("http://localhost:3000"))
    opts = _cors_middleware_options(app)
    if opts.get("allow_credentials"):
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


def test_expose_headers_does_not_contain_wildcard() -> None:
    app = FastAPI()
    configure_cors(app, _settings("http://localhost:3000"))
    opts = _cors_middleware_options(app)
    assert "*" not in opts.get("expose_headers", [])

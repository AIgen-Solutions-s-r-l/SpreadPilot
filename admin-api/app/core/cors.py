"""Shared CORS configuration for admin-api entrypoints.

Centralising the CORS middleware setup here prevents the two entrypoints
(`main.py` and `admin_api.py`) from drifting apart — historically `admin_api.py`
shipped a permissive `allow_origins=['*']` fallback with `allow_credentials=True`,
which is a CORS bypass (see issue #111).
"""
from __future__ import annotations

from typing import Protocol

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Explicit allowlists — no wildcards. HEAD/PATCH are intentionally excluded;
# add them here if a concrete endpoint requires them.
ALLOWED_METHODS: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
ALLOWED_HEADERS: list[str] = ["Content-Type", "Authorization"]


class _SettingsLike(Protocol):
    cors_origins: str


def configure_cors(app: FastAPI, settings: _SettingsLike) -> list[str]:
    """Validate CORS_ORIGINS and register CORSMiddleware on `app`.

    Side effect: calls `app.add_middleware(CORSMiddleware, ...)` with an
    explicit methods/headers allowlist and `allow_credentials=True`.

    Raises ValueError (fail-fast) if `settings.cors_origins` is empty,
    whitespace-only, or contains the wildcard `*`. Returns the parsed
    list of allowed origins for logging / testing purposes.
    """
    raw = (settings.cors_origins or "").strip()
    if not raw:
        raise ValueError(
            "CORS_ORIGINS must be set via environment variable. "
            "Wildcard (*) is not allowed for security. "
            "Example: CORS_ORIGINS=http://localhost:3000,https://app.example.com"
        )

    origins = [o.strip() for o in raw.split(",") if o.strip()]

    if "*" in origins:
        raise ValueError(
            "Wildcard (*) is not allowed in CORS_ORIGINS. "
            "Specify explicit allowed origins "
            "(e.g., http://localhost:3000,https://app.example.com)."
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        # Required for JWT bearer-token cookies and the Authorization header.
        # Safe because wildcard origins are rejected above.
        allow_credentials=True,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
    )
    return origins

"""Unit tests for WebSocket endpoint exception handling (issue #166).

Imports the websocket module via importlib to avoid pulling in the full
admin-api config/settings chain which requires Vault secrets.
"""

import importlib.util
import inspect
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocketDisconnect

_WS_PATH = (
    Path(__file__).resolve().parents[2]
    / "admin-api"
    / "app"
    / "api"
    / "v1"
    / "endpoints"
    / "websocket.py"
)


def _load_websocket_module():
    """Load the websocket module with a stubbed settings dependency."""
    app_core_config = types.ModuleType("app.core.config")
    mock_settings = MagicMock()
    mock_settings.jwt_secret = "x" * 32
    mock_settings.jwt_algorithm = "HS256"
    mock_settings.admin_username = "admin"
    app_core_config.get_settings = lambda: mock_settings

    app_core = types.ModuleType("app.core")
    app_mod = types.ModuleType("app")
    app_api = types.ModuleType("app.api")
    app_api_v1 = types.ModuleType("app.api.v1")
    app_api_v1_endpoints = types.ModuleType("app.api.v1.endpoints")

    for name, mod in [
        ("app", app_mod),
        ("app.core", app_core),
        ("app.core.config", app_core_config),
        ("app.api", app_api),
        ("app.api.v1", app_api_v1),
        ("app.api.v1.endpoints", app_api_v1_endpoints),
    ]:
        sys.modules.setdefault(name, mod)

    spec = importlib.util.spec_from_file_location("app.api.v1.endpoints.websocket", _WS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ws_mod = _load_websocket_module()


class TestWebSocketExceptionHandling:
    """Verify correct exception ordering and cleanup in the WebSocket endpoint."""

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up_connection(self):
        """WebSocketDisconnect must trigger manager.disconnect — not the auth-error branch."""
        manager = _ws_mod.manager
        websocket_endpoint = _ws_mod.websocket_endpoint

        mock_ws = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        with patch.object(manager, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = lambda ws, user: manager.active_connections.__setitem__(
                ws, user
            )
            with patch.object(
                _ws_mod, "validate_ws_token", new_callable=AsyncMock, return_value="admin"
            ):
                await websocket_endpoint(mock_ws, token="valid_token")

        assert mock_ws not in manager.active_connections

    @pytest.mark.asyncio
    async def test_auth_failure_closes_with_policy_violation(self):
        """Auth failure must close with code 1008, not leak into the disconnect branch."""
        manager = _ws_mod.manager
        websocket_endpoint = _ws_mod.websocket_endpoint

        mock_ws = AsyncMock()
        initial_count = len(manager.active_connections)

        with patch.object(
            _ws_mod,
            "validate_ws_token",
            new_callable=AsyncMock,
            side_effect=Exception("Invalid token"),
        ):
            await websocket_endpoint(mock_ws, token="bad_token")

        mock_ws.close.assert_called_once_with(code=1008, reason="Invalid token")
        assert len(manager.active_connections) == initial_count

    def test_no_bare_except_in_source(self):
        """Source must not contain bare 'except:' — only typed exception handlers."""
        source = inspect.getsource(_ws_mod.websocket_endpoint)
        lines = [line.strip() for line in source.splitlines()]
        bare_excepts = [line for line in lines if line == "except:"]
        assert len(bare_excepts) == 0, f"Found bare except: {bare_excepts}"

    @pytest.mark.asyncio
    async def test_inbound_messages_are_not_echoed(self):
        """Client messages are discarded — the dashboard channel is server-push only."""
        manager = _ws_mod.manager
        websocket_endpoint = _ws_mod.websocket_endpoint

        # Receive two client messages, then disconnect.
        mock_ws = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=["hello", "world", WebSocketDisconnect()])

        with patch.object(manager, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = lambda ws, user: manager.active_connections.__setitem__(
                ws, user
            )
            with patch.object(
                _ws_mod, "validate_ws_token", new_callable=AsyncMock, return_value="admin"
            ):
                await websocket_endpoint(mock_ws, token="valid_token")

        # No echo — send_text must never be called from the receive loop.
        mock_ws.send_text.assert_not_called()

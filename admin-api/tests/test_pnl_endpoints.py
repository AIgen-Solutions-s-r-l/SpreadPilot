from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime

import pytest
import pytz
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_get_today_pnl_success(client: TestClient, auth_headers: dict):
    """Test successful retrieval of today's P&L from PostgreSQL."""
    # Mock P&L data
    mock_rows = [
        MagicMock(follower_id="follower1", pnl=1500.50),
        MagicMock(follower_id="follower2", pnl=-200.75),
    ]
    
    with patch("admin-api.app.api.v1.endpoints.pnl.get_postgres_session") as mock_session:
        mock_async_cm = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_async_cm
        mock_async_cm.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.__iter__ = lambda x: iter(mock_rows)
        mock_async_cm.execute.return_value = mock_result
        
        response = client.get("/api/v1/pnl/today", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["follower_id"] == "follower1"
    assert data[0]["pnl"] == 1500.50
    assert data[1]["follower_id"] == "follower2"
    assert data[1]["pnl"] == -200.75


@pytest.mark.asyncio
async def test_get_today_pnl_no_data(client: TestClient, auth_headers: dict):
    """Test today's P&L when no data exists."""
    with patch("admin-api.app.api.v1.endpoints.pnl.get_postgres_session") as mock_session:
        mock_async_cm = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_async_cm
        mock_async_cm.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.__iter__ = lambda x: iter([])  # Empty result
        mock_async_cm.execute.return_value = mock_result
        
        response = client.get("/api/v1/pnl/today", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data == []  # Empty list when no data


@pytest.mark.asyncio
async def test_get_month_pnl_success(client: TestClient, auth_headers: dict):
    """Test successful retrieval of monthly P&L from PostgreSQL."""
    # Mock monthly P&L data
    mock_rows = [
        MagicMock(follower_id="follower1", pnl=2500.00),
        MagicMock(follower_id="follower2", pnl=-500.00),
        MagicMock(follower_id="follower3", pnl=1200.00),
    ]
    
    with patch("admin-api.app.api.v1.endpoints.pnl.get_postgres_session") as mock_session:
        mock_async_cm = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_async_cm
        mock_async_cm.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.__iter__ = lambda x: iter(mock_rows)
        mock_async_cm.execute.return_value = mock_result
        
        response = client.get(
            "/api/v1/pnl/month?year=2024&month=1", headers=auth_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["follower_id"] == "follower1"
    assert data[0]["pnl"] == 2500.00
    assert data[1]["follower_id"] == "follower2"
    assert data[1]["pnl"] == -500.00
    assert data[2]["follower_id"] == "follower3"
    assert data[2]["pnl"] == 1200.00


@pytest.mark.asyncio
async def test_get_month_pnl_invalid_month(client: TestClient, auth_headers: dict):
    """Test monthly P&L with invalid month."""
    response = client.get("/api/v1/pnl/month?year=2024&month=13", headers=auth_headers)
    assert response.status_code == 400
    assert "Invalid month" in response.json()["detail"]


def test_pnl_endpoints_require_auth(client: TestClient):
    """Test that P&L endpoints require authentication."""
    response = client.get("/api/v1/pnl/today")
    assert response.status_code == 401

    response = client.get("/api/v1/pnl/month")
    assert response.status_code == 401

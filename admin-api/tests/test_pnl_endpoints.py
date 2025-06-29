from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_get_today_pnl_success(client: TestClient, auth_headers: dict):
    """Test successful retrieval of today's P&L."""
    mock_pnl_data = {
        "date": "2024-01-15",
        "total_pnl": 1500.50,
        "realized_pnl": 1000.00,
        "unrealized_pnl": 500.50,
        "trades": [{"symbol": "QQQ", "pnl": 1000.00, "quantity": 10}],
    }

    with patch("admin-api.app.api.v1.endpoints.pnl.get_mongo_db") as mock_db:
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = mock_pnl_data
        mock_db.return_value = {"daily_pnl": mock_collection}

        response = client.get("/api/v1/pnl/today", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total_pnl"] == 1500.50
    assert data["realized_pnl"] == 1000.00


@pytest.mark.asyncio
async def test_get_today_pnl_no_data(client: TestClient, auth_headers: dict):
    """Test today's P&L when no data exists."""
    with patch("admin-api.app.api.v1.endpoints.pnl.get_mongo_db") as mock_db:
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = None
        mock_db.return_value = {"daily_pnl": mock_collection}

        response = client.get("/api/v1/pnl/today", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total_pnl"] == 0.0
    assert "message" in data


@pytest.mark.asyncio
async def test_get_month_pnl_success(client: TestClient, auth_headers: dict):
    """Test successful retrieval of monthly P&L."""
    mock_daily_data = [
        {"date": "2024-01-01", "total_pnl": 100.00},
        {"date": "2024-01-02", "total_pnl": -50.00},
        {"date": "2024-01-03", "total_pnl": 200.00},
    ]

    with patch("admin-api.app.api.v1.endpoints.pnl.get_mongo_db") as mock_db:
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = mock_daily_data

        mock_collection = AsyncMock()
        mock_collection.find.return_value.sort.return_value = mock_cursor

        mock_db.return_value = {"daily_pnl": mock_collection}

        response = client.get(
            "/api/v1/pnl/month?year=2024&month=1", headers=auth_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2024
    assert data["month"] == 1
    assert data["total_pnl"] == 250.00
    assert data["days_with_data"] == 3


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

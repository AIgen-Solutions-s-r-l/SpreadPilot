from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_get_recent_logs_default(client: TestClient, auth_headers: dict):
    """Test fetching recent logs with default parameters."""
    mock_logs = [
        {
            "timestamp": datetime(2024, 1, 15, 10, 30, 0),
            "service": "trading-bot",
            "level": "INFO",
            "message": "Position opened for follower ABC",
        },
        {
            "timestamp": datetime(2024, 1, 15, 10, 25, 0),
            "service": "admin-api",
            "level": "ERROR",
            "message": "Failed to connect to database",
        },
    ]

    with patch("admin-api.app.api.v1.endpoints.logs.get_mongo_db") as mock_db:
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = mock_logs

        mock_collection = AsyncMock()
        mock_collection.find.return_value.sort.return_value.limit.return_value = mock_cursor

        mock_db.return_value = {"logs": mock_collection}

        response = client.get("/api/v1/logs/recent", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert data["requested"] == 200
    assert len(data["logs"]) == 2


@pytest.mark.asyncio
async def test_get_recent_logs_with_filters(client: TestClient, auth_headers: dict):
    """Test fetching logs with filters."""
    mock_logs = [
        {
            "timestamp": datetime(2024, 1, 15, 10, 30, 0),
            "service": "trading-bot",
            "level": "ERROR",
            "message": "Connection timeout error",
        }
    ]

    with patch("admin-api.app.api.v1.endpoints.logs.get_mongo_db") as mock_db:
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = mock_logs

        mock_collection = AsyncMock()
        mock_collection.find.return_value.sort.return_value.limit.return_value = mock_cursor

        mock_db.return_value = {"logs": mock_collection}

        response = client.get(
            "/api/v1/logs/recent?n=50&service=trading-bot&level=ERROR&search=error",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["requested"] == 50
    assert data["filters"]["service"] == "trading-bot"
    assert data["filters"]["level"] == "ERROR"
    assert data["filters"]["search"] == "error"


@pytest.mark.asyncio
async def test_get_recent_logs_limit_validation(client: TestClient, auth_headers: dict):
    """Test log limit validation."""
    # Test with n > 1000
    response = client.get("/api/v1/logs/recent?n=1500", headers=auth_headers)
    assert response.status_code == 422  # Validation error

    # Test with n < 1
    response = client.get("/api/v1/logs/recent?n=0", headers=auth_headers)
    assert response.status_code == 422


def test_logs_endpoint_requires_auth(client: TestClient):
    """Test that logs endpoint requires authentication."""
    response = client.get("/api/v1/logs/recent")
    assert response.status_code == 401

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_manual_close_success(client: TestClient, auth_headers: dict):
    """Test successful manual close operation with IBKR client."""
    request_data = {
        "follower_id": "test_follower_123",
        "pin": "0312",
        "close_all": True,
        "reason": "Emergency close requested",
    }

    with patch(
        "admin-api.app.api.v1.endpoints.manual_operations.get_mongo_db"
    ) as mock_db, patch(
        "admin-api.app.api.v1.endpoints.manual_operations.IBKRClient"
    ) as mock_ibkr_class:
        # Mock follower exists
        mock_followers = AsyncMock()
        mock_followers.find_one.return_value = {
            "_id": "test_follower_123",
            "name": "Test Follower",
        }

        # Mock operations collection
        mock_operations = AsyncMock()
        mock_operations.insert_one.return_value.inserted_id = "operation_123"

        # Mock alerts collection
        mock_alerts = AsyncMock()

        mock_db.return_value = {
            "followers": mock_followers,
            "manual_operations": mock_operations,
            "alerts": mock_alerts,
        }
        
        # Mock IBKR client
        mock_ibkr_instance = AsyncMock()
        mock_ibkr_instance.close_all_positions.return_value = {
            "status": "SUCCESS",
            "message": "Successfully closed all positions",
            "closed_positions": 5
        }
        mock_ibkr_class.return_value = mock_ibkr_instance

        response = client.post(
            "/api/v1/manual-close", json=request_data, headers=auth_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["follower_id"] == "test_follower_123"
    assert data["closed_positions"] == 5
    assert "operation_123" in data["message"]


@pytest.mark.asyncio
async def test_manual_close_invalid_pin(client: TestClient, auth_headers: dict):
    """Test manual close with invalid PIN."""
    request_data = {
        "follower_id": "test_follower_123",
        "pin": "9999",  # Wrong PIN
        "close_all": True,
    }

    response = client.post(
        "/api/v1/manual-close", json=request_data, headers=auth_headers
    )

    assert response.status_code == 403
    assert "Invalid PIN" in response.json()["detail"]


@pytest.mark.asyncio
async def test_manual_close_follower_not_found(client: TestClient, auth_headers: dict):
    """Test manual close for non-existent follower."""
    request_data = {
        "follower_id": "non_existent_follower",
        "pin": "0312",
        "close_all": True,
    }

    with patch(
        "admin-api.app.api.v1.endpoints.manual_operations.get_mongo_db"
    ) as mock_db:
        mock_followers = AsyncMock()
        mock_followers.find_one.return_value = None

        mock_db.return_value = {"followers": mock_followers}

        response = client.post(
            "/api/v1/manual-close", json=request_data, headers=auth_headers
        )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_manual_close_specific_positions(client: TestClient, auth_headers: dict):
    """Test manual close for specific positions."""
    request_data = {
        "follower_id": "test_follower_123",
        "pin": "0312",
        "close_all": False,
        "position_ids": ["pos1", "pos2", "pos3"],
    }

    with patch(
        "admin-api.app.api.v1.endpoints.manual_operations.get_mongo_db"
    ) as mock_db, patch(
        "admin-api.app.api.v1.endpoints.manual_operations.IBKRClient"
    ) as mock_ibkr_class:
        mock_followers = AsyncMock()
        mock_followers.find_one.return_value = {"_id": "test_follower_123"}

        mock_operations = AsyncMock()
        mock_operations.insert_one.return_value.inserted_id = "operation_456"

        mock_alerts = AsyncMock()

        mock_db.return_value = {
            "followers": mock_followers,
            "manual_operations": mock_operations,
            "alerts": mock_alerts,
        }
        
        # Mock IBKR client
        mock_ibkr_instance = AsyncMock()
        mock_ibkr_instance.close_all_positions.return_value = {
            "status": "SUCCESS",
            "message": "Successfully closed positions",
            "closed_positions": 3
        }
        mock_ibkr_class.return_value = mock_ibkr_instance

        response = client.post(
            "/api/v1/manual-close", json=request_data, headers=auth_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["closed_positions"] == 3


@pytest.mark.asyncio
async def test_manual_close_ibkr_failure(client: TestClient, auth_headers: dict):
    """Test manual close when IBKR client fails."""
    request_data = {
        "follower_id": "test_follower_123",
        "pin": "0312",
        "close_all": True,
    }

    with patch(
        "admin-api.app.api.v1.endpoints.manual_operations.get_mongo_db"
    ) as mock_db, patch(
        "admin-api.app.api.v1.endpoints.manual_operations.IBKRClient"
    ) as mock_ibkr_class:
        # Mock follower exists
        mock_followers = AsyncMock()
        mock_followers.find_one.return_value = {"_id": "test_follower_123"}

        mock_db.return_value = {
            "followers": mock_followers,
            "manual_operations": AsyncMock(),
            "alerts": AsyncMock(),
        }
        
        # Mock IBKR client failure
        mock_ibkr_instance = AsyncMock()
        mock_ibkr_instance.close_all_positions.side_effect = Exception("Connection failed")
        mock_ibkr_class.return_value = mock_ibkr_instance

        response = client.post(
            "/api/v1/manual-close", json=request_data, headers=auth_headers
        )

    assert response.status_code == 500
    assert "Failed to execute manual close" in response.json()["detail"]


def test_manual_close_requires_auth(client: TestClient):
    """Test that manual close endpoint requires authentication."""
    request_data = {
        "follower_id": "test_follower_123",
        "pin": "0312",
        "close_all": True,
    }

    response = client.post("/api/v1/manual-close", json=request_data)
    assert response.status_code == 401

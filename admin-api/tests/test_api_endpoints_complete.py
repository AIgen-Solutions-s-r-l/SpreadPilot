"""Test that all API endpoints are properly implemented."""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_pnl_endpoints_exist(async_client: AsyncClient, auth_headers: dict):
    """Test that P&L endpoints are accessible."""
    # Test today's P&L endpoint
    response = await async_client.get("/api/v1/pnl/today", headers=auth_headers)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]  # 404 if no data
    
    # Test monthly P&L endpoint
    response = await async_client.get("/api/v1/pnl/month", headers=auth_headers)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]  # 404 if no data


@pytest.mark.asyncio
async def test_logs_endpoint_exists(async_client: AsyncClient, auth_headers: dict):
    """Test that logs endpoint is accessible."""
    response = await async_client.get("/api/v1/logs/", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), dict)
    assert "logs" in response.json()


@pytest.mark.asyncio
async def test_manual_close_endpoint_exists(async_client: AsyncClient, auth_headers: dict):
    """Test that manual close endpoint exists and requires PIN."""
    # Test without PIN (should fail)
    request_data = {
        "follower_id": "test_follower",
        "pin": "wrong_pin",
        "close_all": True,
        "reason": "Test close"
    }
    
    response = await async_client.post(
        "/api/v1/manual-close",
        json=request_data,
        headers=auth_headers
    )
    
    # Should return 403 for wrong PIN
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Invalid PIN" in response.json()["detail"]


@pytest.mark.asyncio
async def test_all_endpoints_require_auth(async_client: AsyncClient):
    """Test that all endpoints require authentication."""
    endpoints = [
        ("/api/v1/pnl/today", "GET"),
        ("/api/v1/pnl/month", "GET"),
        ("/api/v1/logs/", "GET"),
        ("/api/v1/manual-close", "POST"),
    ]
    
    for endpoint, method in endpoints:
        if method == "GET":
            response = await async_client.get(endpoint)
        else:
            response = await async_client.post(endpoint, json={})
        
        # Should return 401 without auth
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio  
async def test_pnl_month_with_params(async_client: AsyncClient, auth_headers: dict):
    """Test P&L month endpoint with year and month parameters."""
    # Test with valid parameters
    response = await async_client.get(
        "/api/v1/pnl/month?year=2025&month=1",
        headers=auth_headers
    )
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    # Test with invalid month
    response = await async_client.get(
        "/api/v1/pnl/month?year=2025&month=13",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid month" in response.json()["detail"]


@pytest.mark.asyncio
async def test_logs_with_filters(async_client: AsyncClient, auth_headers: dict):
    """Test logs endpoint with various filters."""
    # Test with limit
    response = await async_client.get(
        "/api/v1/logs/?limit=10",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    logs = response.json()["logs"]
    assert len(logs) <= 10
    
    # Test with service filter
    response = await async_client.get(
        "/api/v1/logs/?service=trading-bot",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Test with level filter
    response = await async_client.get(
        "/api/v1/logs/?level=ERROR",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Test with search
    response = await async_client.get(
        "/api/v1/logs/?search=error",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
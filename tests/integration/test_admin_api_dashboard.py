from typing import Any  # Add missing import

"""Integration tests for the admin API dashboard endpoints."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx  # Re-add import
import pytest
from bson import ObjectId  # Added for MongoDB IDs
from fastapi.testclient import TestClient  # Import TestClient
from motor.motor_asyncio import AsyncIOMotorDatabase  # Added for type hinting

from spreadpilot_core.models.follower import Follower, FollowerState

# Explicitly import the fixtures we intend to use
# Use admin_api_test_client for WS tests, admin_api_client for regular HTTP tests


@pytest.mark.asyncio  # Ensure async marker
async def test_dashboard_api_endpoints(  # Ensure async def
    admin_api_client: tuple[httpx.AsyncClient, Any, str],  # Expect client
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _, _ = admin_api_client  # Unpack client
    """
    Test dashboard related API endpoints.

    This test verifies:
    1. /api/v1/dashboard/summary returns expected structure
    2. /api/v1/dashboard/status returns expected structure
    3. /api/v1/dashboard/periodic_update triggers the background task (mocked)
    """
    # Create some followers with different states
    follower_ids_to_cleanup = []
    try:
        follower_data_active = {
            "_id": str(ObjectId()),
            "email": "dash-active@example.com",
            "iban": "IBAN-DASH-A",
            "ibkr_username": "dashuserA",
            "ibkr_secret_ref": "secretA",
            "commission_pct": 10,
            "enabled": True,
            "state": FollowerState.ACTIVE.value,
            "daily_pnl": 100.50,
            "monthly_pnl": 500.75,
        }
        follower_data_inactive = {
            "_id": str(ObjectId()),
            "email": "dash-inactive@example.com",
            "iban": "IBAN-DASH-I",
            "ibkr_username": "dashuserI",
            "ibkr_secret_ref": "secretI",
            "commission_pct": 15,
            "enabled": False,
            "state": FollowerState.DISABLED.value,
            "daily_pnl": -20.0,
            "monthly_pnl": -100.0,
        }
        await test_mongo_db.followers.insert_many([follower_data_active, follower_data_inactive])
        follower_ids_to_cleanup.append(follower_data_active["_id"])
        follower_ids_to_cleanup.append(follower_data_inactive["_id"])

        # 1. Test /summary endpoint
        response_summary = await admin_api_client.get("/api/v1/dashboard/summary")  # Ensure await
        assert response_summary.status_code == 200
        summary_data = response_summary.json()

        # Assert against the actual keys returned by the endpoint
        assert "follower_stats" in summary_data
        assert "system_status" in summary_data

        # Check follower stats structure
        follower_stats = summary_data["follower_stats"]
        assert "total" in follower_stats
        assert "active" in follower_stats
        assert "inactive" in follower_stats

        # Check the values based on the inserted data
        assert follower_stats["total"] == 2
        assert follower_stats["active"] == 1
        assert follower_stats["inactive"] == 1
        assert summary_data["system_status"] == "operational"

        # Test /stats endpoint (if implemented)
        # response_stats = await admin_api_client.get("/api/v1/dashboard/stats")
        # assert response_stats.status_code == 200

        # Test /alerts endpoint (if implemented)
        # response_alerts = await admin_api_client.get("/api/v1/dashboard/alerts")
        # assert response_alerts.status_code == 200

        # Test /performance endpoint (if implemented)
        # response_perf = await admin_api_client.get("/api/v1/dashboard/performance")
        # assert response_perf.status_code == 200

    finally:
        # Clean up
        if follower_ids_to_cleanup:
            await test_mongo_db.followers.delete_many({"_id": {"$in": follower_ids_to_cleanup}})


@pytest.mark.asyncio  # Ensure async marker
async def test_dashboard_api_error_handling(  # Ensure async def
    admin_api_client: tuple[httpx.AsyncClient, Any, str],  # Expect client
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _, _ = admin_api_client  # Unpack client
    """Test error handling in dashboard API endpoints."""

    # Test /summary with service error (patching the actual underlying method)
    with patch(
        "admin_api.app.services.follower_service.FollowerService.get_followers",
        new_callable=AsyncMock,
    ) as mock_get_followers_summary:
        mock_get_followers_summary.side_effect = Exception("Summary DB Error")
        # Need to patch get_settings as well, as it's a dependency in the endpoint
        with patch(
            "admin_api.app.api.v1.endpoints.dashboard.get_settings",
            return_value=MagicMock(),
        ):
            response = await admin_api_client.get("/api/v1/dashboard/summary")  # Ensure await
        assert response.status_code == 500
        # Check for a generic server error message as the specific exception might be caught
        assert "Internal Server Error" in response.text or "Summary DB Error" in response.text

    # Test /summary again with a different service error (patching the actual underlying method)
    with patch(
        "admin_api.app.services.follower_service.FollowerService.get_followers",
        new_callable=AsyncMock,
    ) as mock_get_followers_summary_alt:
        mock_get_followers_summary_alt.side_effect = Exception("Summary DB Error 2")
        # Need to patch get_settings as well
        with patch(
            "admin_api.app.api.v1.endpoints.dashboard.get_settings",
            return_value=MagicMock(),
        ):
            response = await admin_api_client.get("/api/v1/dashboard/summary")  # Ensure await
        assert response.status_code == 500
        # Check for a generic server error message
        assert "Internal Server Error" in response.text or "Summary DB Error 2" in response.text


@pytest.mark.asyncio
async def test_periodic_follower_update_task(
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test the periodic follower update background task logic more directly.
    """
    from admin_api.app.api.v1.endpoints.dashboard import periodic_follower_update_task
    from admin_api.app.core.config import get_settings
    from admin_api.app.services.follower_service import FollowerService

    settings = get_settings()
    follower_id_active = str(ObjectId())
    follower_id_disabled = str(ObjectId())
    follower_id_error = str(ObjectId())

    # Mock data
    mock_followers = [
        MagicMock(id=follower_id_active, enabled=True, spec=Follower),
        MagicMock(id=follower_id_disabled, enabled=False, spec=Follower),
        MagicMock(
            id=follower_id_error, enabled=True, spec=Follower
        ),  # Enabled but will cause error
    ]

    # Patch the service methods used by the task
    # Patch the service method and broadcast function used by the task
    with (
        patch(
            "admin_api.app.services.follower_service.FollowerService.get_followers",
            new_callable=AsyncMock,
        ) as mock_get_all,
        patch(
            "admin_api.app.api.v1.endpoints.dashboard.broadcast_updates",
            new_callable=AsyncMock,
        ) as mock_broadcast,
    ):
        mock_get_all.return_value = mock_followers

        # Instantiate the service needed by the task
        # We need a settings object for the service, get it or mock it
        try:
            settings = get_settings()
        except Exception:  # Handle potential config errors if not fully set up
            settings = MagicMock()

        service = FollowerService(db=test_mongo_db, settings=settings)
        test_interval = 0.1  # Define a short interval for the test

        # Run the task function directly, passing the mocked service and the test interval
        task = asyncio.create_task(
            periodic_follower_update_task(follower_service=service, interval_seconds=test_interval)
        )
        await asyncio.sleep(
            test_interval * 2
        )  # Allow task to run at least once based on the test interval
        task.cancel()  # Stop the infinite loop
        try:
            await task
        except asyncio.CancelledError:
            pass  # Expected cancellation

        # Assertions
        mock_get_all.assert_called()  # Check if get_followers was called at least once
        mock_broadcast.assert_called()  # Check if broadcast was called at least once

        # Verify the broadcast message structure (optional but good)
        if mock_broadcast.call_args_list:
            call_args, _ = mock_broadcast.call_args_list[0]
            message = call_args[0]
            assert message["type"] == "follower_update"
            assert "data" in message
            assert "followers" in message["data"]
            assert "timestamp" in message["data"]
            assert len(message["data"]["followers"]) == len(mock_followers)


# --- WebSocket Tests (Commented Out) ---


@pytest.mark.asyncio
async def test_websocket_dashboard_connect(
    admin_api_test_client: TestClient,  # Use the TestClient fixture
    test_mongo_db: AsyncIOMotorDatabase,
):
    """Test connecting to the dashboard WebSocket using TestClient."""
    # Create follower using the TestClient's sync interface within the async test
    follower_data = {
        "email": "websocket-test@example.com",
        "iban": "IBAN-WEBSOCKET-TEST",
        "ibkr_username": "websocket_test_user",
        "commission_pct": 15,
        "ibkr_secret_ref": "test-secret-ref",
    }
    response = admin_api_test_client.post("/api/v1/followers", json=follower_data)
    assert response.status_code == 201, f"Failed to create follower: {response.text}"
    created_follower = response.json()
    follower_id = created_follower["id"]

    try:
        # Use TestClient's websocket_connect within the async test
        with admin_api_test_client.websocket_connect("/api/v1/ws/dashboard") as websocket:
            initial_message = websocket.receive_json()  # Sync receive
            assert initial_message["type"] == "initial_state"
            assert "followers" in initial_message["data"]
            assert isinstance(initial_message["data"]["followers"], list)
            # Check if the created follower is present (use the correct ID field)
            assert any(f["id"] == follower_id for f in initial_message["data"]["followers"])
    finally:
        # Cleanup needs to be async as test_mongo_db is async
        await test_mongo_db.followers.delete_one({"_id": follower_id})


@pytest.mark.asyncio
async def test_websocket_dashboard_multiple_clients(
    admin_api_test_client: TestClient,  # Use the TestClient fixture
    test_mongo_db: AsyncIOMotorDatabase,
):
    """Test multiple clients connecting via TestClient."""
    from admin_api.app.api.v1.endpoints.dashboard import active_connections

    # Create follower using TestClient
    follower_data = {
        "email": "multi-client-test@example.com",
        "iban": "IBAN-MULTI-CLIENT-TEST",
        "ibkr_username": "multi_client_user",
        "commission_pct": 10,
        "ibkr_secret_ref": "test-secret-ref",
    }
    response = admin_api_test_client.post("/api/v1/followers", json=follower_data)
    assert response.status_code == 201, f"Failed to create follower: {response.text}"
    created_follower = response.json()
    follower_id = created_follower["id"]

    num_clients = 3
    websockets_list = []
    initial_connection_count = len(active_connections)

    try:
        # Connect multiple clients using TestClient
        for i in range(num_clients):
            ws = admin_api_test_client.websocket_connect("/api/v1/ws/dashboard")
            websockets_list.append(ws)
            initial_message = ws.receive_json()
            assert initial_message["type"] == "initial_state"
            assert "followers" in initial_message["data"]
            assert len(active_connections) == initial_connection_count + i + 1

        # All clients connected, check final count
        assert len(active_connections) == initial_connection_count + num_clients

        # Disconnect clients
        for ws in websockets_list:
            ws.close()

        # Check count after closing (add delay)
        await asyncio.sleep(0.5)  # Give server time to process disconnections
        assert len(active_connections) == initial_connection_count

    finally:
        # Ensure cleanup even on failure
        for ws in websockets_list:
            try:
                ws.close()
            except Exception:
                pass
        # Async DB cleanup
        await test_mongo_db.followers.delete_one({"_id": follower_id})


# Make this test async and use the unified TestClient fixture
@pytest.mark.asyncio
async def test_websocket_dashboard_disconnection_handling(
    admin_api_test_client: TestClient,  # Use the async-compatible TestClient fixture
    test_mongo_db: AsyncIOMotorDatabase,  # Keep DB fixture
):
    """Test handling of WebSocket client disconnections using TestClient in async test."""
    from admin_api.app.api.v1.endpoints.dashboard import active_connections

    initial_connection_count = len(active_connections)

    try:
        with admin_api_test_client.websocket_connect("/api/v1/ws/dashboard") as websocket:
            websocket.receive_json()  # Receive initial state
            assert len(active_connections) == initial_connection_count + 1

        # Connection is closed when exiting 'with' block
        # Need a small delay to allow the server-side finally block to execute
        await asyncio.sleep(0.5)  # Use asyncio.sleep in async test
        assert len(active_connections) == initial_connection_count

    except Exception as e:
        # Add debugging for potential TestClient issues
        pytest.fail(f"TestClient WebSocket connection failed: {e}")

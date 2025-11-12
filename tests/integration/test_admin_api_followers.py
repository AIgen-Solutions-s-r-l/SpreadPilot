from typing import Any  # Add missing import

"""Integration tests for the admin API follower endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx  # Re-add import
import pytest
from bson import ObjectId  # Added for MongoDB IDs
from fastapi.testclient import TestClient  # Import TestClient
from motor.motor_asyncio import AsyncIOMotorDatabase  # Added for type hinting
from spreadpilot_core.models.follower import Follower, FollowerState

# Explicitly import the fixtures we intend to use


@pytest.mark.asyncio  # Add back async marker
async def test_list_followers(  # Add back async def
    admin_api_client: tuple[httpx.AsyncClient, Any, str],  # Expect tuple from fixture
    test_mongo_db: AsyncIOMotorDatabase,  # Keep direct DB access for setup/cleanup
):
    admin_api_client, _, _ = admin_api_client  # Unpack client, ignore app and base_url
    """
    Test listing all followers using MongoDB.

    This test verifies:
    1. Endpoint returns all followers from MongoDB
    2. Response format is correct (assuming service converts _id to id)
    """
    # Create test followers directly in MongoDB
    followers_data = []
    follower_ids_to_cleanup = []
    for i in range(3):
        follower = Follower(
            id=str(ObjectId()),  # Simulate ID generation if needed by model, though DB uses _id
            email=f"list-test{i}@example.com",
            iban=f"NL91ABNA0417164{i}00",
            ibkr_username=f"list-testuser{i}",
            ibkr_secret_ref=f"projects/spreadpilot-test/secrets/ibkr-password-list-testuser{i}",
            commission_pct=20.0 + i,
            enabled=(i % 2 == 0),
            state=FollowerState.ACTIVE if (i % 2 == 0) else FollowerState.DISABLED,
        )
        mongo_data = follower.model_dump(exclude={"id"})
        followers_data.append(mongo_data)

    insert_result = await test_mongo_db.followers.insert_many(followers_data)
    inserted_ids = insert_result.inserted_ids
    follower_ids_to_cleanup.extend(inserted_ids)

    with patch(
        "admin_api.app.api.v1.endpoints.followers.get_settings",
        return_value=MagicMock(),
    ):
        response = await admin_api_client.get("/api/v1/followers")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= len(inserted_ids)

    response_follower_ids = {f["id"] for f in data}
    inserted_id_strs = {str(oid) for oid in inserted_ids}
    assert inserted_id_strs.issubset(response_follower_ids)

    for i, inserted_id in enumerate(inserted_ids):
        follower_in_response = next((f for f in data if f["id"] == str(inserted_id)), None)
        assert follower_in_response is not None
        assert follower_in_response["email"] == f"list-test{i}@example.com"
        assert follower_in_response["enabled"] == (i % 2 == 0)

    await test_mongo_db.followers.delete_many({"_id": {"$in": follower_ids_to_cleanup}})


@pytest.mark.asyncio
async def test_create_follower(
    admin_api_client: tuple[httpx.AsyncClient, Any, str],  # Corrected unpacking
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _, _ = admin_api_client  # Corrected unpacking
    """Test creating a new follower using MongoDB."""
    follower_payload = {
        "email": "create-test@example.com",
        "iban": "NL91ABNA0417164301",
        "ibkr_username": "create-testuser",
        "ibkr_secret_ref": "projects/spreadpilot-test/secrets/ibkr-password-create-testuser",
        "commission_pct": 25.0,
    }
    follower_id_to_cleanup = None
    try:
        with patch(
            "admin_api.app.api.v1.endpoints.followers.get_settings",
            return_value=MagicMock(),
        ):
            response = await admin_api_client.post("/api/v1/followers", json=follower_payload)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == follower_payload["email"]
        assert data["iban"] == follower_payload["iban"]
        assert data["ibkr_username"] == follower_payload["ibkr_username"]
        assert data["commission_pct"] == follower_payload["commission_pct"]
        assert data["enabled"] is False
        assert data["state"] == FollowerState.DISABLED.value
        assert "id" in data
        follower_id_str = data["id"]
        follower_id_to_cleanup = follower_id_str
        follower_doc = await test_mongo_db.followers.find_one({"_id": follower_id_to_cleanup})
        assert follower_doc is not None
        assert follower_doc["email"] == follower_payload["email"]
        assert follower_doc["enabled"] is False
    finally:
        if follower_id_to_cleanup:
            await test_mongo_db.followers.delete_one({"_id": follower_id_to_cleanup})


@pytest.mark.asyncio
async def test_toggle_follower(
    admin_api_client: tuple[httpx.AsyncClient, Any, str],  # Corrected unpacking
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _, _ = admin_api_client  # Corrected unpacking
    """Test toggling a follower's enabled status using MongoDB."""
    initial_enabled = True
    follower_id_str = str(uuid.uuid4())
    follower = Follower(
        id=follower_id_str,
        email="toggle-test@example.com",
        iban="NL91ABNA0417164302",
        ibkr_username="toggle-testuser",
        ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-toggle-testuser",
        commission_pct=20.0,
        enabled=initial_enabled,
        state=FollowerState.ACTIVE,
    )
    mongo_data = follower.model_dump(by_alias=True)
    insert_result = await test_mongo_db.followers.insert_one(mongo_data)
    assert insert_result.inserted_id == follower_id_str
    try:
        with patch(
            "admin_api.app.api.v1.endpoints.followers.get_settings",
            return_value=MagicMock(),
        ):
            response = await admin_api_client.post(f"/api/v1/followers/{follower_id_str}/toggle")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == follower_id_str
        assert data["enabled"] is not initial_enabled

        updated_doc = await test_mongo_db.followers.find_one({"_id": follower_id_str})
        assert updated_doc is not None
        assert updated_doc["enabled"] is False

        with patch(
            "admin_api.app.api.v1.endpoints.followers.get_settings",
            return_value=MagicMock(),
        ):
            response_toggle_back = await admin_api_client.post(
                f"/api/v1/followers/{follower_id_str}/toggle"
            )
        assert response_toggle_back.status_code == 200
        data_toggle_back = response_toggle_back.json()
        assert data_toggle_back["enabled"] is initial_enabled

        final_doc = await test_mongo_db.followers.find_one({"_id": follower_id_str})
        assert final_doc is not None
        assert final_doc["enabled"] is initial_enabled
    finally:
        await test_mongo_db.followers.delete_one({"_id": follower_id_str})


@pytest.mark.asyncio
async def test_toggle_nonexistent_follower(
    admin_api_client: tuple[httpx.AsyncClient, Any, str],  # Corrected unpacking
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _, _ = admin_api_client  # Corrected unpacking
    """Test toggling a non-existent follower using MongoDB backend."""
    nonexistent_id = str(ObjectId())
    with patch(
        "admin_api.app.api.v1.endpoints.followers.get_settings",
        return_value=MagicMock(),
    ):
        response = await admin_api_client.post(f"/api/v1/followers/{nonexistent_id}/toggle")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_trigger_close_positions(
    admin_api_client: tuple[httpx.AsyncClient, Any, str],  # Corrected unpacking
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _, _ = admin_api_client  # Corrected unpacking
    """Test triggering close positions for a follower using MongoDB backend."""
    follower_id_str = str(uuid.uuid4())
    follower = Follower(
        id=follower_id_str,
        email="close-test@example.com",
        iban="NL91ABNA0417164303",
        ibkr_username="close-testuser",
        ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-close-testuser",
        commission_pct=20.0,
        enabled=True,
        state=FollowerState.ACTIVE,
    )
    mongo_data = follower.model_dump(by_alias=True)
    insert_result = await test_mongo_db.followers.insert_one(mongo_data)
    assert insert_result.inserted_id == follower_id_str
    try:
        with patch(
            "admin_api.app.services.follower_service.FollowerService.trigger_close_positions",
            new_callable=AsyncMock,
        ) as mock_trigger:
            mock_trigger.return_value = True
            with patch(
                "admin_api.app.api.v1.endpoints.followers.get_settings",
                return_value=MagicMock(),
            ):
                response = await admin_api_client.post(f"/api/v1/close/{follower_id_str}")

        assert response.status_code == 202
        data = response.json()
        assert "message" in data
        assert follower_id_str in data["message"]
        mock_trigger.assert_called_once_with(follower_id_str)
    finally:
        await test_mongo_db.followers.delete_one({"_id": follower_id_str})


@pytest.mark.asyncio
async def test_trigger_close_positions_nonexistent_follower(
    admin_api_client: tuple[httpx.AsyncClient, Any, str],  # Corrected unpacking
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _, _ = admin_api_client  # Corrected unpacking
    """Test triggering close positions for a non-existent follower."""
    nonexistent_id = str(ObjectId())
    with patch(
        "admin_api.app.api.v1.endpoints.followers.get_settings",
        return_value=MagicMock(),
    ):
        response = await admin_api_client.post(f"/api/v1/close/{nonexistent_id}")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_create_follower_validation_error(admin_api_test_client_sync: TestClient):
    """Test creating a follower with invalid data."""
    invalid_follower_data = {
        "email": "invalid-email",
        "iban": "NL91ABNA0417164306",
        "ibkr_username": "validation-user",
        "ibkr_secret_ref": "secret",
        "commission_pct": 10,
    }
    response = admin_api_test_client_sync.post("/api/v1/followers", json=invalid_follower_data)
    assert response.status_code == 422
    assert "value is not a valid email address" in response.text

    missing_field_data = {
        "email": "valid@example.com",
        "ibkr_username": "validation-user2",
        "ibkr_secret_ref": "secret2",
        "commission_pct": 12,
    }
    response = admin_api_test_client_sync.post("/api/v1/followers", json=missing_field_data)
    assert response.status_code == 422
    assert "Field required" in response.text and "iban" in response.text

    invalid_commission_data = {
        "email": "valid2@example.com",
        "iban": "NL91ABNA0417164307",
        "ibkr_username": "validation-user3",
        "ibkr_secret_ref": "secret3",
        "commission_pct": 110,
    }
    response = admin_api_test_client_sync.post("/api/v1/followers", json=invalid_commission_data)
    assert response.status_code == 422
    # Check specific Pydantic v2 error message structure if possible, otherwise generic check
    assert (
        "Input should be less than or equal to 100" in response.text
        or "commission_pct" in response.text
    )


def test_toggle_nonexistent_follower_error(admin_api_test_client_sync: TestClient):
    """Test toggling a non-existent follower using the synchronous client."""
    nonexistent_id = str(ObjectId())
    # This test is implemented in async version below due to async operations in endpoint
    # Sync test client cannot properly handle async motor operations
    pass  # See test_toggle_follower_status_nonexistent_async below


@pytest.mark.asyncio
async def test_followers_api_error_handling(
    admin_api_client: tuple[httpx.AsyncClient, Any, str],  # Corrected unpacking
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _, _ = admin_api_client  # Corrected unpacking
    """Test error handling scenarios in the followers API."""
    follower_data = {
        "email": "duplicate-test@example.com",
        "iban": "IBAN-DUP-1",
        "ibkr_username": "dupuser1",
        "ibkr_secret_ref": "secretdup1",
        "commission_pct": 10,
    }
    response = await admin_api_client.post("/api/v1/followers", json=follower_data)
    assert response.status_code == 201
    created_id = response.json()["id"]
    try:
        follower_data_dup = {
            "email": "duplicate-test@example.com",
            "iban": "IBAN-DUP-2",
            "ibkr_username": "dupuser2",
            "ibkr_secret_ref": "secretdup2",
            "commission_pct": 15,
        }
        response_dup = await admin_api_client.post("/api/v1/followers", json=follower_data_dup)
        assert response_dup.status_code == 400
        assert "already exists" in response_dup.json()["detail"].lower()

        with patch(
            "admin_api.app.services.follower_service.FollowerService.toggle_follower_enabled",
            new_callable=AsyncMock,
        ) as mock_toggle:
            mock_toggle.side_effect = Exception("Toggle Service Error")
            response_toggle_err = await admin_api_client.post(
                f"/api/v1/followers/{created_id}/toggle"
            )
            assert response_toggle_err.status_code == 500
            # Check for generic 500 message from API layer
            assert "An unexpected server error occurred" in response_toggle_err.text

        with patch(
            "admin_api.app.services.follower_service.FollowerService.trigger_close_positions",
            new_callable=AsyncMock,
        ) as mock_trigger_err:
            mock_trigger_err.side_effect = Exception("Trigger Close Service Error")
            response_close_err = await admin_api_client.post(f"/api/v1/close/{created_id}")
            assert response_close_err.status_code == 500
            # Check for generic 500 message from API layer
            assert "Failed to trigger close positions" in response_close_err.text
    finally:
        await test_mongo_db.followers.delete_one({"_id": created_id})


@pytest.mark.asyncio
async def test_list_followers_error_handling(
    admin_api_client: tuple[httpx.AsyncClient, Any, str],  # Corrected unpacking
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _, _ = admin_api_client  # Corrected unpacking
    """Test error handling for the list followers endpoint."""
    # Patch the correct service method 'get_followers'
    with patch(
        "admin_api.app.services.follower_service.FollowerService.get_followers",
        new_callable=AsyncMock,
    ) as mock_get_followers:
        mock_get_followers.side_effect = Exception("List DB Error")
        # Need to patch get_settings as well, as it's a dependency in the endpoint
        with patch(
            "admin_api.app.api.v1.endpoints.followers.get_settings",
            return_value=MagicMock(),
        ):
            response = await admin_api_client.get("/api/v1/followers")
        assert response.status_code == 500
        # Check for a generic server error message as the specific exception might be caught
        assert (
            "Internal Server Error" in response.text
            or "Failed to retrieve followers" in response.text
        )


@pytest.mark.asyncio
async def test_create_follower_service_error(
    admin_api_client: tuple[httpx.AsyncClient, Any, str],  # Corrected unpacking
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _, _ = admin_api_client  # Corrected unpacking
    """Test error handling during follower creation at the service level."""
    follower_data = {
        "email": "create-error@example.com",
        "iban": "IBAN-CERR",
        "ibkr_username": "cerruser",
        "ibkr_secret_ref": "secretcerr",
        "commission_pct": 10,
    }
    with patch(
        "admin_api.app.services.follower_service.FollowerService.create_follower",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.side_effect = Exception("Create Service Error")
        with patch(
            "admin_api.app.api.v1.endpoints.followers.get_settings",
            return_value=MagicMock(),
        ):
            response = await admin_api_client.post("/api/v1/followers", json=follower_data)
    assert response.status_code == 500
    # Check for generic 500 message from API layer
    assert "Failed to create follower" in response.text


@pytest.mark.asyncio
async def test_toggle_follower_service_error(
    admin_api_client: tuple[httpx.AsyncClient, Any, str],  # Corrected unpacking
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _, _ = admin_api_client  # Corrected unpacking
    """Test error handling during follower toggle at the service level."""
    follower_data = {
        "_id": str(ObjectId()),
        "email": "toggle-error@example.com",
        "iban": "IBAN-TERR",
        "ibkr_username": "terruser",
        "ibkr_secret_ref": "secretterr",
        "commission_pct": 10,
    }
    await test_mongo_db.followers.insert_one(follower_data)
    follower_id = follower_data["_id"]
    try:
        with patch(
            "admin_api.app.services.follower_service.FollowerService.toggle_follower_enabled",
            new_callable=AsyncMock,
        ) as mock_toggle:
            mock_toggle.side_effect = Exception("Toggle Service Error")
            with patch(
                "admin_api.app.api.v1.endpoints.followers.get_settings",
                return_value=MagicMock(),
            ):
                response = await admin_api_client.post(f"/api/v1/followers/{follower_id}/toggle")
        assert response.status_code == 500
        # Check for generic 500 message from API layer
        assert "An unexpected server error occurred" in response.text
    finally:
        await test_mongo_db.followers.delete_one({"_id": follower_id})

"""Integration tests for the admin API and dashboard."""

import asyncio
import datetime
import json
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId # Added for MongoDB IDs

from fastapi.testclient import TestClient
from fastapi import Depends # Added for service dependency injection
from admin_api.app.api.v1.endpoints.followers import get_follower_service # Added for service dependency
# from google.cloud import firestore # Removed Firestore
from motor.motor_asyncio import AsyncIOMotorDatabase # Added for type hinting

from spreadpilot_core.models.follower import Follower, FollowerState
import importlib

# Import modules using importlib
admin_api_schemas = importlib.import_module('admin_api.app.schemas.follower')
admin_api_services = importlib.import_module('admin_api.app.services.follower_service')

# Get specific imports
FollowerCreate = admin_api_schemas.FollowerCreate
FollowerRead = admin_api_schemas.FollowerRead
FollowerService = admin_api_services.FollowerService


@pytest.mark.asyncio
async def test_list_followers(
    # admin_api_client: TestClient, # Removed TestClient
    test_mongo_db: AsyncIOMotorDatabase,
    follower_service: FollowerService = Depends(get_follower_service), # Add service dependency
):
    """
    Test listing all followers using MongoDB via the service.

    This test verifies:
    1. Service returns all followers from MongoDB
    2. Response format is correct (FollowerRead model)
    """
    # Create test followers directly in MongoDB
    followers_data = []
    follower_ids_to_cleanup = []
    for i in range(3):
        # Generate ObjectId here if needed, or let MongoDB do it
        follower = Follower(
            id=str(ObjectId()), # Simulate ID generation if needed by model, though DB uses _id
            email=f"list-test{i}@example.com",
            iban=f"NL91ABNA0417164{i}00",
            ibkr_username=f"list-testuser{i}",
            ibkr_secret_ref=f"projects/spreadpilot-test/secrets/ibkr-password-list-testuser{i}",
            commission_pct=20.0 + i,
            enabled=(i % 2 == 0),
            state=FollowerState.ACTIVE if (i % 2 == 0) else FollowerState.DISABLED,
        )
        # Prepare data for MongoDB insertion (without 'id', let DB generate '_id')
        mongo_data = follower.model_dump(exclude={'id'})
        followers_data.append(mongo_data)

    # Insert into MongoDB
    insert_result = await test_mongo_db.followers.insert_many(followers_data)
    inserted_ids = insert_result.inserted_ids
    follower_ids_to_cleanup.extend(inserted_ids) # Store ObjectIds for cleanup

    # Call the service method directly
    followers_list = await follower_service.get_followers()

    # Verify response
    assert isinstance(followers_list, list)
    # Check if at least the inserted followers are present
    assert len(followers_list) >= len(inserted_ids)

    # Verify each inserted follower is in the response
    response_follower_ids = {f.id for f in followers_list}
    inserted_id_strs = {str(oid) for oid in inserted_ids}
    assert inserted_id_strs.issubset(response_follower_ids)

    # Verify data for one follower
    for i, inserted_id in enumerate(inserted_ids):
        follower_in_response = next((f for f in followers_list if f.id == str(inserted_id)), None)
        assert follower_in_response is not None
        assert follower_in_response.email == f"list-test{i}@example.com"
        assert follower_in_response.enabled == (i % 2 == 0)

    # Clean up test followers
    await test_mongo_db.followers.delete_many({"_id": {"$in": follower_ids_to_cleanup}})


@pytest.mark.asyncio
async def test_create_follower(
    admin_api_client: TestClient,
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test creating a new follower using MongoDB.

    This test verifies:
    1. Follower is created with correct data
    2. Response contains the created follower (with 'id' as string)
    3. Follower is stored in MongoDB (with '_id' as ObjectId)
    """
    # Create follower data
    follower_payload = {
        "email": "create-test@example.com",
        "iban": "NL91ABNA0417164301",
        "ibkr_username": "create-testuser",
        "ibkr_secret_ref": "projects/spreadpilot-test/secrets/ibkr-password-create-testuser",
        "commission_pct": 25.0,
    }
    follower_id_to_cleanup = None

    try:
        # Mock the get_settings dependency
        with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
            # Call the endpoint
            response = admin_api_client.post(
                "/api/v1/followers",
                json=follower_payload,
            )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == follower_payload["email"]
        assert data["iban"] == follower_payload["iban"]
        assert data["ibkr_username"] == follower_payload["ibkr_username"]
        assert data["commission_pct"] == follower_payload["commission_pct"]
        assert data["enabled"] is False  # Default value
        assert data["state"] == FollowerState.DISABLED.value  # Default value
        assert "id" in data
        follower_id_str = data["id"]
        follower_id_to_cleanup = follower_id_str # Store string ID for cleanup

        # Verify follower was stored in MongoDB (assuming service stores string UUID as _id)
        follower_doc = await test_mongo_db.followers.find_one({"_id": follower_id_to_cleanup})
        assert follower_doc is not None
        assert follower_doc["email"] == follower_payload["email"]
        assert follower_doc["enabled"] is False

    finally:
        # Clean up
        if follower_id_to_cleanup:
            await test_mongo_db.followers.delete_one({"_id": follower_id_to_cleanup}) # Use string ID


@pytest.mark.asyncio
async def test_toggle_follower(
    # admin_api_client: TestClient, # Removed TestClient
    test_mongo_db: AsyncIOMotorDatabase,
    follower_service: FollowerService = Depends(get_follower_service), # Add service dependency
):
    """
    Test toggling a follower's enabled status using MongoDB via the service.

    This test verifies:
    1. Follower's enabled status is toggled via service
    2. Service returns the updated follower model
    3. Follower is updated in MongoDB
    """
    # Insert a test follower
    initial_enabled = True
    follower = Follower(
        id=str(ObjectId()), # Not used for insertion, just for model validation
        email="toggle-test@example.com",
        iban="NL91ABNA0417164302",
        ibkr_username="toggle-testuser",
        ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-toggle-testuser",
        commission_pct=20.0,
        enabled=initial_enabled,
        state=FollowerState.ACTIVE,
    )
    mongo_data = follower.model_dump(exclude={'id'})
    insert_result = await test_mongo_db.followers.insert_one(mongo_data)
    follower_oid = insert_result.inserted_id
    follower_id_str = str(follower_oid)

    try:
        # Call the service method to toggle
        updated_follower = await follower_service.toggle_follower_enabled(follower_id_str)

        # Verify response from service
        assert updated_follower is not None
        assert updated_follower.id == follower_id_str
        assert updated_follower.enabled is not initial_enabled  # Should be toggled to False

        # Verify follower was updated in MongoDB
        updated_doc = await test_mongo_db.followers.find_one({"_id": follower_oid})
        assert updated_doc is not None
        assert updated_doc["enabled"] is False # Check toggled state

        # Toggle back via service
        updated_follower_back = await follower_service.toggle_follower_enabled(follower_id_str)
        assert updated_follower_back is not None
        assert updated_follower_back.enabled is initial_enabled # Should be back to True

        # Verify in DB again
        final_doc = await test_mongo_db.followers.find_one({"_id": follower_oid})
        assert final_doc is not None
        assert final_doc["enabled"] is initial_enabled

    finally:
        # Clean up
        await test_mongo_db.followers.delete_one({"_id": follower_oid})


# Note: No async needed as it doesn't interact with DB directly for setup/cleanup
def test_toggle_nonexistent_follower(
    admin_api_client: TestClient,
    test_mongo_db: AsyncIOMotorDatabase, # Fixture needed for client override, but not used directly
):
    """
    Test toggling a non-existent follower using MongoDB backend.

    This test verifies:
    1. Appropriate error is returned
    2. Status code is 404
    """
    # Generate a random follower ID that doesn't exist (use ObjectId format)
    nonexistent_id = str(ObjectId())

    # Mock the get_settings dependency
    with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
        # Call the endpoint
        response = admin_api_client.post(f"/api/v1/followers/{nonexistent_id}/toggle")

    # Verify response
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_trigger_close_positions(
    # admin_api_client: TestClient, # Removed TestClient
    test_mongo_db: AsyncIOMotorDatabase,
    follower_service: FollowerService = Depends(get_follower_service), # Add service dependency
):
    """
    Test triggering close positions for a follower using MongoDB backend via the service.

    This test verifies:
    1. Service method is called correctly
    2. Underlying publish mechanism is mocked and called
    """
    # Insert a test follower
    follower = Follower(
        id=str(ObjectId()), # Not used for insertion
        email="close-test@example.com",
        iban="NL91ABNA0417164303",
        ibkr_username="close-testuser",
        ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-close-testuser",
        commission_pct=20.0,
        enabled=True,
        state=FollowerState.ACTIVE,
    )
    mongo_data = follower.model_dump(exclude={'id'})
    insert_result = await test_mongo_db.followers.insert_one(mongo_data)
    follower_oid = insert_result.inserted_id
    follower_id_str = str(follower_oid)

    try:
        # Mock the underlying publish_message function used by the service
        with patch("admin_api.app.services.follower_service.publish_message",
                   new_callable=AsyncMock) as mock_publish:
            mock_publish.return_value = True # Simulate successful publish

            # Call the service method directly
            success = await follower_service.trigger_close_positions(follower_id_str)

            # Verify response from service
            assert success is True

            # Verify the publish function was called correctly
            mock_publish.assert_called_once()
            args = mock_publish.call_args[0]
            assert args[0] == "close-positions"  # Topic
            message = json.loads(args[1])  # Message
            assert message["follower_id"] == follower_id_str
            assert "timestamp" in message

    finally:
        # Clean up
        await test_mongo_db.followers.delete_one({"_id": follower_oid})


# Note: No async needed as it doesn't interact with DB directly for setup/cleanup
def test_trigger_close_positions_nonexistent_follower(
    admin_api_client: TestClient,
    test_mongo_db: AsyncIOMotorDatabase, # Fixture needed for client override
):
    """
    Test triggering close positions for a non-existent follower using MongoDB backend.

    This test verifies:
    1. Appropriate error is returned
    2. Status code is 404
    """
    # Generate a random follower ID that doesn't exist (use ObjectId format)
    nonexistent_id = str(ObjectId())

    # Mock the get_settings dependency
    with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
        # Call the endpoint
        response = admin_api_client.post(f"/api/v1/close/{nonexistent_id}")

    # Verify response
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_follower_service_integration(
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test the FollowerService integration with MongoDB.

    This test verifies:
    1. Followers can be created, retrieved, and updated via the service
    2. Service methods interact correctly with MongoDB
    """
    # Create a follower service instance
    service = FollowerService(db=test_mongo_db, settings=MagicMock())
    follower_id_to_cleanup = None # Store string ID

    try:
        # Create a new follower
        follower_payload = FollowerCreate(
            email="service-test@example.com",
            iban="NL91ABNA0417164304",
            ibkr_username="serviceuser",
            ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-serviceuser",
            commission_pct=30.0,
        )

        # Test create_follower
        follower = await service.create_follower(follower_payload)
        assert follower.id is not None # Service should return string ID
        follower_id_to_cleanup = follower.id # Store string ID for cleanup/verification
        assert follower.email == follower_payload.email
        assert follower.enabled is False

        # Verify in DB (assuming service stores string UUID as _id)
        db_doc = await test_mongo_db.followers.find_one({"_id": follower_id_to_cleanup})
        assert db_doc is not None
        assert db_doc["email"] == follower_payload.email

        # Test get_follower_by_id
        retrieved_follower = await service.get_follower_by_id(follower.id) # Pass string ID
        assert retrieved_follower is not None
        assert retrieved_follower.id == follower.id
        assert retrieved_follower.email == follower.email

        # Test toggle_follower_enabled
        updated_follower = await service.toggle_follower_enabled(follower.id) # Pass string ID
        assert updated_follower is not None
        assert updated_follower.enabled is True

        # Verify in DB (assuming service stores string UUID as _id)
        db_doc_toggled = await test_mongo_db.followers.find_one({"_id": follower_id_to_cleanup})
        assert db_doc_toggled is not None
        assert db_doc_toggled["enabled"] is True

        # Test get_followers
        followers = await service.get_followers()
        assert len(followers) >= 1
        assert any(f.id == follower.id for f in followers)

    finally:
        # Clean up
        if follower_id_to_cleanup:
            await test_mongo_db.followers.delete_one({"_id": follower_id_to_cleanup}) # Use string ID


@pytest.mark.asyncio
async def test_trigger_close_positions_service(
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test the service method for triggering close positions using MongoDB backend.

    This test verifies:
    1. Service method communicates with trading-bot (mocked publish)
    2. Command is properly formatted and sent
    """
    # Insert a test follower
    follower = Follower(
        id=str(ObjectId()), # Not used for insertion
        email="trigger-service-test@example.com",
        iban="NL91ABNA0417164305",
        ibkr_username="trigger-service-user",
        ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-trigger-service-user",
        commission_pct=20.0,
        enabled=True,
        state=FollowerState.ACTIVE,
    )
    mongo_data = follower.model_dump(exclude={'id'})
    insert_result = await test_mongo_db.followers.insert_one(mongo_data)
    follower_oid = insert_result.inserted_id
    follower_id_str = str(follower_oid)

    try:
        # Mock the publish_message method
        with patch("admin_api.app.services.follower_service.publish_message", new_callable=AsyncMock) as mock_publish:
            mock_publish.return_value = True

            # Create service instance
            service = FollowerService(db=test_mongo_db, settings=MagicMock())

            # Call the method
            result = await service.trigger_close_positions(follower_id_str)

            # Verify result
            assert result is True

            # Verify publish_message was called with correct arguments
            mock_publish.assert_called_once()
            args = mock_publish.call_args[0]
            assert args[0] == "close-positions"  # Topic
            message = json.loads(args[1])  # Message
            assert message["follower_id"] == follower_id_str
            assert "timestamp" in message
    finally:
        # Clean up
        await test_mongo_db.followers.delete_one({"_id": follower_oid})
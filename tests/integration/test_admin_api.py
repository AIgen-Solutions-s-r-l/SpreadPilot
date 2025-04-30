from typing import Any # Add missing import
"""Integration tests for the admin API and dashboard."""

import asyncio
import datetime
import json
import pytest
import uuid
import anyio # Import anyio
import time # Import time
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId # Added for MongoDB IDs
import websockets # Import websockets library
from spreadpilot_core.logging.logger import get_logger # Import logger

import httpx # Re-add import
from fastapi.testclient import TestClient # Import TestClient
import httpx_ws # Import httpx-ws
# from anyio.abc import TestClient as AnyioTestClient # Remove anyio import
from fastapi import Depends # Added for service dependency injection
from admin_api.app.api.v1.endpoints.followers import get_follower_service # Added for service dependency
# from google.cloud import firestore # Removed Firestore
from motor.motor_asyncio import AsyncIOMotorDatabase # Added for type hinting
import admin_api.app.api.v1.endpoints.dashboard # Import dashboard module for direct patching

from spreadpilot_core.models.follower import Follower, FollowerState
import importlib

# Import modules using importlib
admin_api_db = importlib.import_module('admin_api.app.db.mongodb') # Changed to mongodb
admin_api_services = importlib.import_module('admin_api.app.services.follower_service')
admin_api_schemas = importlib.import_module('admin_api.app.schemas.follower')
admin_api_config = importlib.import_module('admin_api.app.core.config')

# Get specific imports
get_mongo_db = admin_api_db.get_mongo_db # Changed to get_mongo_db
FollowerService = admin_api_services.FollowerService
FollowerRead = admin_api_schemas.FollowerRead
get_settings = admin_api_config.get_settings
Settings = admin_api_config.Settings

# Note: This is a simplified mock for testing purposes.
# In a real application, you would use a proper dependency injection override.
def override_get_settings():
    """Override for get_settings dependency."""
    # Return a mock settings object with necessary attributes
    mock_settings = MagicMock()
    mock_settings.firestore_project_id = "test-project" # Keep for compatibility if needed
    mock_settings.mongodb_url = "mongodb://test:test@localhost:27017" # Use testcontainers URL
    mock_settings.mongodb_db_name = "test_db" # Use a test database name
    mock_settings.trading_bot_pubsub_topic = "test-topic" # Add pubsub topic
    mock_settings.trading_bot_pubsub_project_id = "test-project" # Add pubsub project id
    mock_settings.environment = "TESTING" # Add environment setting
    return mock_settings

# Note: This is a simplified mock for testing purposes.
# In a real application, you would use a proper dependency injection override.
async def override_get_mongo_db():
    """Override for get_mongo_db dependency."""
    # This mock will be replaced by the testcontainers fixture
    # which provides a real test MongoDB connection.
    # We keep this here primarily for type hinting and clarity.
    # The actual connection is managed by the fixture.
    return MagicMock(spec=AsyncIOMotorDatabase)


# Apply overrides for testing
# admin_api_main.app.dependency_overrides[get_settings] = override_get_settings
# admin_api_main.app.dependency_overrides[get_mongo_db] = override_get_mongo_db


# Use TestClient for synchronous testing where possible
# For async tests, use httpx.AsyncClient with the app instance
# client = TestClient(admin_api_main.app) # Keep for sync tests if any


# Fixture to provide an async client and the app instance
@pytest.fixture(scope="module")
async def admin_api_client(test_mongo_db: AsyncIOMotorDatabase, test_db_url: str, test_db_name: str): # Add URL and name from fixture
    """Provides an async test client for the admin API."""
    # Override dependencies for the test client instance
    def get_test_settings():
        mock_settings = MagicMock()
        mock_settings.firestore_project_id = "test-project"
        # Inject the dynamic DB URL and name from the fixture into settings
        mock_settings.mongodb_url = test_db_url
        mock_settings.mongodb_db_name = test_db_name
        mock_settings.trading_bot_pubsub_topic = "test-topic"
        mock_settings.trading_bot_pubsub_project_id = "test-project"
        mock_settings.environment = "TESTING"
        return mock_settings

    # This override might not be strictly needed anymore if get_mongo_db uses settings,
    # but keep it for now to ensure the correct DB object is available if directly requested.
    async def get_test_mongo_db():
        return test_mongo_db # Return the actual test DB from fixture

    # Create a new FastAPI app instance for testing with overridden dependencies
    # This avoids interfering with the global app instance if it were imported directly
    from fastapi import FastAPI
    test_app = FastAPI()

    # Import and include the routers *after* creating the test_app
    from admin_api.app.api.v1.endpoints import followers, dashboard
    test_app.include_router(followers.router, prefix="/api/v1")
    test_app.include_router(dashboard.router, prefix="/api/v1")


    # Apply dependency overrides to the test app instance
    test_app.dependency_overrides[followers.get_settings] = get_test_settings
    test_app.dependency_overrides[followers.get_mongo_db] = get_test_mongo_db
    test_app.dependency_overrides[dashboard.get_settings] = get_test_settings
    test_app.dependency_overrides[dashboard.get_mongo_db] = get_test_mongo_db
    test_app.dependency_overrides[dashboard.get_follower_service] = lambda: FollowerService(db=test_mongo_db, settings=get_test_settings())


    # Use httpx.AsyncClient with the test app instance
    async with httpx.AsyncClient(app=test_app, base_url="http://testserver") as client:
        # Return the client, the app instance, and the base_url
        yield client, test_app, "http://testserver"


# Fixture for MongoDB testcontainers
@pytest.fixture(scope="module")
async def test_mongo_db():
    """Provides a test MongoDB database using testcontainers."""
    from testcontainers.mongodb import MongoDbContainer
    from motor.motor_asyncio import AsyncIOMotorClient

    # Define credentials
    mongo_user = "testuser"
    db_name = f"test_db_{uuid.uuid4().hex}"

    # Configure container without explicit credentials
    container = MongoDbContainer("mongo:6.0")
    with container as mongo:
        # Get the connection URL directly from the container
        test_db_url = mongo.get_connection_url()
        # Append the unique database name
        if "?" in test_db_url:
             test_db_url = f"{test_db_url.split('?')[0]}/{db_name}?{test_db_url.split('?')[1]}"
        else:
             test_db_url = f"{test_db_url}/{db_name}"


        logger = get_logger(__name__) # Instantiate logger
        logger.info(f"Using test MongoDB (unauthenticated): {test_db_url}")

        # Create an async client using the constructed URL
        client = AsyncIOMotorClient(test_db_url)
        db = client[db_name]

        # Remove the ping attempt for now, let tests fail if auth is still broken
        # logger.info("Waiting for MongoDB container auth...")
        # await asyncio.sleep(1.0)
        # try:
        #     await client.admin.command('ping')
        #     logger.info("Successfully pinged test MongoDB server.")
        # except Exception as e:
        #     logger.error(f"Failed to ping test MongoDB server: {e}", exc_info=True)
        # raise # Re-raise if ping fails

    # Yield the database instance, URL, and name
    yield db, test_db_url, db_name

    # Teardown: Drop the test database
    logger.info(f"Dropping test MongoDB database: {db_name}")
    try:
        # Ensure client is still connected before dropping
        await client.admin.command('ping') # Check connection
        await client.drop_database(db_name)
        logger.info(f"Successfully dropped test MongoDB database: {db_name}")
    except Exception as e:
        logger.error(f"Error dropping test database {db_name}: {e}", exc_info=True)
    finally:
        client.close()

# Fixture to extract the test DB URL from the main mongo fixture
@pytest.fixture(scope="module")
async def test_db_url(test_mongo_db: tuple[AsyncIOMotorDatabase, str, str]) -> str:
    _, url, _ = test_mongo_db
    return url

# Fixture to extract the test DB name from the main mongo fixture
@pytest.fixture(scope="module")
async def test_db_name(test_mongo_db: tuple[AsyncIOMotorDatabase, str, str]) -> str:
    _, _, name = test_mongo_db
    return name

# Modify admin_api_client fixture to use the new fixtures
@pytest.fixture(scope="module")
async def admin_api_client(
    test_mongo_db: AsyncIOMotorDatabase, # Keep dependency for direct DB access if needed
    test_db_url: str,
    test_db_name: str
):
    """Provides an async test client for the admin API."""
    # Override dependencies for the test client instance
    def get_test_settings():
        mock_settings = MagicMock()
        mock_settings.firestore_project_id = "test-project"
        # Inject the dynamic DB URL and name from the fixture into settings
        mock_settings.mongodb_url = test_db_url
        mock_settings.mongodb_db_name = test_db_name
        mock_settings.trading_bot_pubsub_topic = "test-topic"
        mock_settings.trading_bot_pubsub_project_id = "test-project"
        mock_settings.environment = "TESTING"
        return mock_settings

    # This override might not be strictly needed anymore if get_mongo_db uses settings,
    # but keep it for now to ensure the correct DB object is available if directly requested.
    async def get_test_mongo_db():
        return test_mongo_db # Return the actual test DB from fixture

    # Create a new FastAPI app instance for testing with overridden dependencies
    # This avoids interfering with the global app instance if it were imported directly
    from fastapi import FastAPI
    test_app = FastAPI()

    # Import and include the routers *after* creating the test_app
    from admin_api.app.api.v1.endpoints import followers, dashboard
    test_app.include_router(followers.router, prefix="/api/v1")
    test_app.include_router(dashboard.router, prefix="/api/v1")


    # Apply dependency overrides to the test app instance
    test_app.dependency_overrides[followers.get_settings] = get_test_settings
    test_app.dependency_overrides[followers.get_mongo_db] = get_test_mongo_db
    test_app.dependency_overrides[dashboard.get_settings] = get_test_settings
    test_app.dependency_overrides[dashboard.get_mongo_db] = get_test_mongo_db
    test_app.dependency_overrides[dashboard.get_follower_service] = lambda: FollowerService(db=test_mongo_db, settings=get_test_settings())


    # Use httpx.AsyncClient with the test app instance
    async with httpx.AsyncClient(app=test_app, base_url="http://testserver") as client:
        # Return the client, the app instance, and the base_url
        yield client, test_app, "http://testserver"


@pytest.mark.asyncio # Add back async marker
async def test_list_followers( # Add back async def
    admin_api_client: tuple[httpx.AsyncClient, Any, str], # Expect tuple from fixture
    test_mongo_db: AsyncIOMotorDatabase, # Keep direct DB access for setup/cleanup
):
    admin_api_client, _, _ = admin_api_client # Unpack client, ignore app and base_url
    """
    Test listing all followers using MongoDB.

    This test verifies:
    1. Endpoint returns all followers from MongoDB
    2. Response format is correct (assuming service converts _id to id)
    """
    # client, _ = admin_api_client # No longer need to unpack
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

    # Mock the get_settings dependency (get_db is handled by admin_api_client fixture)
    with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
        # Call the endpoint using the client fixture directly
        response = await admin_api_client.get("/api/v1/followers") # Add await

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Check if at least the inserted followers are present
    assert len(data) >= len(inserted_ids)

    # Verify each inserted follower is in the response (assuming API returns 'id' as string)
    response_follower_ids = {f["id"] for f in data}
    inserted_id_strs = {str(oid) for oid in inserted_ids}
    assert inserted_id_strs.issubset(response_follower_ids)

    # Verify data for one follower
    for i, inserted_id in enumerate(inserted_ids):
        follower_in_response = next((f for f in data if f["id"] == str(inserted_id)), None)
        assert follower_in_response is not None
        assert follower_in_response["email"] == f"list-test{i}@example.com"
        assert follower_in_response["enabled"] == (i % 2 == 0)

    # Clean up test followers
    await test_mongo_db.followers.delete_many({"_id": {"$in": follower_ids_to_cleanup}})


@pytest.mark.asyncio # Add back async marker
async def test_create_follower( # Add back async def
    admin_api_client: tuple[httpx.AsyncClient, Any], # Expect tuple
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _ = admin_api_client # Unpack client
    """
    Test creating a new follower using MongoDB.

    This test verifies:
    1. Follower is created with correct data
    2. Response contains the created follower (with 'id' as string)
    3. Follower is stored in MongoDB (with '_id' as ObjectId)
    """
    # client, _ = admin_api_client # No longer need to unpack
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
            # Call the endpoint using the client fixture directly
            response = await admin_api_client.post( # Add await
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


@pytest.mark.asyncio # Add back async marker
async def test_toggle_follower( # Add back async def
    admin_api_client: tuple[httpx.AsyncClient, Any], # Expect tuple
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _ = admin_api_client # Unpack client
    """
    Test toggling a follower's enabled status using MongoDB.

    This test verifies:
    1. Follower's enabled status is toggled
    2. Response contains the updated follower
    3. Follower is updated in MongoDB
    """
    # client, _ = admin_api_client # No longer need to unpack
    # Insert a test follower
    initial_enabled = True
    follower_id_str = str(uuid.uuid4()) # Generate UUID string ID
    follower = Follower(
        id=follower_id_str, # Use the generated UUID string
        email="toggle-test@example.com",
        iban="NL91ABNA0417164302",
        ibkr_username="toggle-testuser",
        ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-toggle-testuser",
        commission_pct=20.0,
        enabled=initial_enabled,
        state=FollowerState.ACTIVE,
    )
    # Use model_dump(by_alias=True) to get {'_id': follower_id_str, ...}
    mongo_data = follower.model_dump(by_alias=True)
    # Insert data including the '_id'
    insert_result = await test_mongo_db.followers.insert_one(mongo_data)
    # Verify insertion used our ID
    assert insert_result.inserted_id == follower_id_str

    try:
        # Mock the get_settings dependency
        with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
            # Call the endpoint to toggle using the client fixture directly
            response = await admin_api_client.post(f"/api/v1/followers/{follower_id_str}/toggle") # Add await

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == follower_id_str
        assert data["enabled"] is not initial_enabled  # Should be toggled to False

        # Verify follower was updated in MongoDB
        updated_doc = await test_mongo_db.followers.find_one({"_id": follower_id_str}) # Use string ID
        assert updated_doc is not None
        assert updated_doc["enabled"] is False # Check toggled state

        # Toggle back
        with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
            response_toggle_back = await admin_api_client.post(f"/api/v1/followers/{follower_id_str}/toggle") # Add await
        assert response_toggle_back.status_code == 200
        data_toggle_back = response_toggle_back.json()
        assert data_toggle_back["enabled"] is initial_enabled # Should be back to True

        # Verify in DB again
        final_doc = await test_mongo_db.followers.find_one({"_id": follower_id_str}) # Query by string ID
        assert final_doc is not None
        assert final_doc["enabled"] is initial_enabled

    finally:
        # Clean up
        await test_mongo_db.followers.delete_one({"_id": follower_id_str}) # Delete by string ID


# Note: No async needed as it doesn't interact with DB directly for setup/cleanup
# Note: This test needs to be async now because admin_api_client is async
@pytest.mark.asyncio # Add back async marker
async def test_toggle_nonexistent_follower( # Add back async def
    admin_api_client: tuple[httpx.AsyncClient, Any], # Expect tuple
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _ = admin_api_client # Unpack client
    """
    Test toggling a non-existent follower using MongoDB backend.

    This test verifies:
    1. Appropriate error is returned
    2. Status code is 404
    """
    # client, _ = admin_api_client # No longer need to unpack
    # Generate a random follower ID that doesn't exist (use ObjectId format)
    nonexistent_id = str(ObjectId())

    # Mock the get_settings dependency
    with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
        # Call the endpoint using the client fixture directly
        response = await admin_api_client.post(f"/api/v1/followers/{nonexistent_id}/toggle") # Add await

    # Verify response
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio # Add back async marker
async def test_trigger_close_positions( # Add back async def
    admin_api_client: tuple[httpx.AsyncClient, Any], # Expect tuple
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _ = admin_api_client # Unpack client
    """
    Test triggering close positions for a follower using MongoDB backend.

    This test verifies:
    1. Close positions command is triggered via service method mock
    2. Response indicates success
    """
    # client, _ = admin_api_client # No longer need to unpack
    # Insert a test follower
    follower_id_str = str(uuid.uuid4()) # Generate UUID string ID
    follower = Follower(
        id=follower_id_str, # Use the generated UUID string
        email="close-test@example.com",
        iban="NL91ABNA0417164303",
        ibkr_username="close-testuser",
        ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-close-testuser",
        commission_pct=20.0,
        enabled=True,
        state=FollowerState.ACTIVE,
    )
    # Use model_dump(by_alias=True) to get {'_id': follower_id_str, ...}
    mongo_data = follower.model_dump(by_alias=True)
    # Insert data including the '_id'
    insert_result = await test_mongo_db.followers.insert_one(mongo_data)
    # Verify insertion used our ID
    assert insert_result.inserted_id == follower_id_str

    try:
        # Mock the follower service's trigger_close_positions method
        # Patch the actual service method, not relying on endpoint injection here
        with patch("admin_api.app.services.follower_service.FollowerService.trigger_close_positions",
                   new_callable=AsyncMock) as mock_trigger:
            mock_trigger.return_value = True

            # Mock the get_settings dependency
            with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
                # Call the endpoint using the client fixture directly
                response = await admin_api_client.post(f"/api/v1/close/{follower_id_str}") # Add await

        # Verify response
        assert response.status_code == 202  # Accepted
        data = response.json()
        assert "message" in data
        assert follower_id_str in data["message"]

        # Verify the service method was called
        mock_trigger.assert_called_once_with(follower_id_str)

    finally:
        # Clean up
        await test_mongo_db.followers.delete_one({"_id": follower_id_str}) # Delete by string ID


# Note: No async needed as it doesn't interact with DB directly for setup/cleanup
# Note: This test needs to be async now because admin_api_client is async
@pytest.mark.asyncio # Add back async marker
async def test_trigger_close_positions_nonexistent_follower( # Add back async def
    admin_api_client: tuple[httpx.AsyncClient, Any], # Expect tuple
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _ = admin_api_client # Unpack client
    """
    Test triggering close positions for a non-existent follower using MongoDB backend.

    This test verifies:
    1. Appropriate error is returned
    2. Status code is 404
    """
    # client, _ = admin_api_client # No longer need to unpack
    # Generate a random follower ID that doesn't exist (use ObjectId format)
    nonexistent_id = str(ObjectId())

    # Mock the get_settings dependency
    with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
        # Call the endpoint using the client fixture directly
        response = await admin_api_client.post(f"/api/v1/close/{nonexistent_id}") # Add await

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


# --- WebSocket Dashboard Tests ---
# Import httpx_ws for async WebSocket testing
from httpx_ws import AsyncWebSocketSession
from httpx_ws.transport import ASGIWebSocketTransport # Import transport

# Ensure WebSocket tests are async and use the tuple fixture correctly
@pytest.mark.asyncio
async def test_websocket_dashboard_connect(
    admin_api_client: tuple[httpx.AsyncClient, Any, str], # Expect tuple with base_url
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, app, _ = admin_api_client # Unpack client and app, ignore base_url
    """
    Test connecting to the dashboard WebSocket and receiving messages.

    This test verifies:
    1. WebSocket connection can be established using client.websocket_connect
    2. Initial state message is received correctly
    """
    # Create a test follower to have some data
    follower_data = {
        "email": "websocket-test@example.com",
        "iban": "IBAN-WEBSOCKET-TEST",
        "ibkr_username": "websocket_test_user",
        "commission_pct": 15,
        "ibkr_secret_ref": "test-secret-ref"
    }
    # Create the follower using the API client
    response = await admin_api_client.post("/api/v1/followers", json=follower_data)
    assert response.status_code == 201, f"Failed to create follower: {response.text}"
    created_follower = response.json()
    follower_id = created_follower["id"]

    # Use the base_url from the fixture to connect to the WebSocket
    # Use relative URL for client's websocket_connect
    ws_url = "/api/v1/ws/dashboard"
    websocket = None # Initialize

    try:
        # Connect using the client's websocket_connect context manager
        async with admin_api_client.websocket_connect(ws_url) as websocket:
            # Receive the initial message
            initial_message = await websocket.receive_json()
        assert initial_message["type"] == "initial_state"
        assert "followers" in initial_message["data"]
        assert isinstance(initial_message["data"]["followers"], list)
        # Check if our created follower is in the initial list
        assert any(f["id"] == follower_id for f in initial_message["data"]["followers"])

        # Optional: Test sending/receiving if endpoint supports it
        # await websocket.send_text("ping")
        # response_text = await websocket.receive_text()
        # assert response_text == "pong" # Or whatever the echo is

    finally:
        # Clean up WebSocket connection
        if websocket:
            await websocket.close()
        # Clean up the created follower
        await test_mongo_db.followers.delete_one({"_id": follower_id})


@pytest.mark.asyncio
async def test_websocket_dashboard_multiple_clients(
    admin_api_client: tuple[httpx.AsyncClient, Any, str], # Expect tuple with base_url
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, app, _ = admin_api_client # Unpack client and app, ignore base_url
    """
    Test multiple clients connecting to the dashboard WebSocket.

    This test verifies:
    1. Multiple WebSocket connections can be established using client.websocket_connect
    2. Initial data is sent to each client
    3. All clients receive broadcast messages (simulated)
    """
    # Create a test follower
    follower_data = {
        "email": "multi-client-test@example.com",
        "iban": "IBAN-MULTI-CLIENT-TEST",
        "ibkr_username": "multi_client_user",
        "commission_pct": 10,
        "ibkr_secret_ref": "test-secret-ref"
    }
    response = await admin_api_client.post("/api/v1/followers", json=follower_data)
    assert response.status_code == 201, f"Failed to create follower: {response.text}"
    created_follower = response.json()
    follower_id = created_follower["id"]

    ws_url = "/api/v1/ws/dashboard" # Use relative URL for client

    # Connect multiple clients
    num_clients = 3
    websockets = []
    try:
        # Use a context manager to handle multiple connections
        async with anyio.create_task_group() as tg:
            for _ in range(num_clients):
                # Use client.websocket_connect within the task group
                ws = await tg.start(admin_api_client.websocket_connect, ws_url)
                websockets.append(ws)
                # Receive initial data for each connection
                initial_message = await ws.receive_json()
            assert initial_message["type"] == "initial_state"
            assert "followers" in initial_message["data"]

        # Simulate a broadcast message
        broadcast_message = {"type": "test_broadcast", "data": {"status": "ok"}}
        # Patch the actual broadcast_updates function and call it directly
        with patch('admin_api.app.api.v1.endpoints.dashboard.broadcast_updates', wraps=admin_api.app.api.v1.endpoints.dashboard.broadcast_updates) as mock_broadcast:
             await admin_api.app.api.v1.endpoints.dashboard.broadcast_updates(broadcast_message)
             # Verify the original function was called
             mock_broadcast.assert_called_once_with(broadcast_message)


        # Verify all clients received the broadcast message
        for websocket in websockets:
            received_message = await websocket.receive_json()
            assert received_message == broadcast_message

    finally:
        # Close all connections
        for websocket in websockets:
            await websocket.close()
        # Clean up the created follower
        await test_mongo_db.followers.delete_one({"_id": follower_id})


@pytest.mark.asyncio
async def test_websocket_dashboard_disconnection_handling(
    admin_api_client: tuple[httpx.AsyncClient, Any, str], # Expect tuple with base_url
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, app, base_url = admin_api_client # Unpack tuple
    """
    Test handling of WebSocket client disconnections.

    This test verifies:
    1. Clients are removed from active_connections upon disconnection
    """
    ws_url = base_url.replace("http", "ws") + "/api/v1/ws/dashboard"

    # Check initial state of active connections
    from admin_api.app.api.v1.endpoints.dashboard import active_connections
    initial_connection_count = len(active_connections)

    # Connect a client using the client's context manager
    async with admin_api_client.websocket_connect(ws_url) as websocket:
        # Receive initial data to ensure connection is fully established
        await websocket.receive_json()

        # Check that the connection is in the active set
        # Accessing the underlying connection object might be fragile.
        # Let's check the count instead for robustness.
        assert len(active_connections) == initial_connection_count + 1

        # Connection closes automatically when exiting 'async with'

    # Allow a moment for the disconnection handling to process on the server
    await asyncio.sleep(0.1)

    # Check that the connection is removed from the active set by checking the count
    assert len(active_connections) == initial_connection_count


# --- Admin API Endpoint Tests ---

def test_create_follower_validation_error(admin_api_test_client: TestClient):
    """Test creating a follower with invalid data."""
    # Missing required fields
    invalid_follower_data = {
        "email": "invalid-test@example.com",
        # iban, ibkr_username, commission_pct, ibkr_secret_ref are missing
    }
    response = admin_api_test_client.post(
        "/api/v1/followers",
        json=invalid_follower_data,
    )

    assert response.status_code == 422  # Unprocessable Entity
    # Check for validation error details (Pydantic errors)
    errors = response.json()["detail"]
    assert isinstance(errors, list)
    assert any(error["loc"] == ("body", "iban") for error in errors)
    assert any(error["loc"] == ("body", "ibkr_username") for error in errors)
    assert any(error["loc"] == ("body", "commission_pct") for error in errors)
    assert any(error["loc"] == ("body", "ibkr_secret_ref") for error in errors)

    # Invalid commission_pct (negative)
    invalid_commission_data = {
        "email": "invalid-commission@example.com",
        "iban": "NL91ABNA0417164999",
        "ibkr_username": "invaliduser",
        "ibkr_secret_ref": "test-secret",
        "commission_pct": -10.0, # Invalid value
    }
    response = admin_api_test_client.post(
        "/api/v1/followers",
        json=invalid_commission_data,
    )
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert isinstance(errors, list)
    assert any(error.get("msg", "").lower() == "ensure this value is greater than or equal to 0" for error in errors)


def test_toggle_nonexistent_follower_error(admin_api_test_client: TestClient):
    """Test toggling a non-existent follower."""
    nonexistent_id = "nonexistent-id-123"
    response = admin_api_test_client.post(f"/api/v1/followers/{nonexistent_id}/toggle")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
def test_update_follower_state(test_mongo_db: AsyncIOMotorDatabase):
    """Test updating a follower's state directly using the service."""
    from admin_api.app.services.follower_service import FollowerService
    from admin_api.app.schemas.follower import FollowerCreate, FollowerState
    from admin_api.app.core.config import get_settings

    async def test_state_updates():
        settings = get_settings()
        follower_service = FollowerService(db=test_mongo_db, settings=settings)

        # Create a follower
        follower_create = FollowerCreate(
            email="state-test@example.com",
            iban="NL91ABNA0417164306",
            ibkr_username="stateuser",
            ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-stateuser",
            commission_pct=20.0,
        )
        follower = await follower_service.create_follower(follower_create)
        follower_id = follower.id

        try:
            # Update state to ACTIVE
            updated_follower = await follower_service.update_follower_state(follower_id, FollowerState.ACTIVE)
            assert updated_follower.state == FollowerState.ACTIVE

            # Verify in DB
            db_doc = await test_mongo_db.followers.find_one({"_id": follower_id})
            assert db_doc["state"] == FollowerState.ACTIVE.value

            # Update state to DISABLED (should also set enabled to False)
            updated_follower_disabled = await follower_service.update_follower_state(follower_id, FollowerState.DISABLED)
            assert updated_follower_disabled.state == FollowerState.DISABLED
            assert updated_follower_disabled.enabled is False

            # Verify in DB
            db_doc_disabled = await test_mongo_db.followers.find_one({"_id": follower_id})
            assert db_doc_disabled["state"] == FollowerState.DISABLED.value
            assert db_doc_disabled["enabled"] is False

            # Update state to ACTIVE again (should also set enabled to True)
            updated_follower_active_again = await follower_service.update_follower_state(follower_id, FollowerState.ACTIVE)
            assert updated_follower_active_again.state == FollowerState.ACTIVE
            assert updated_follower_active_again.enabled is True

            # Verify in DB
            db_doc_active_again = await test_mongo_db.followers.find_one({"_id": follower_id})
            assert db_doc_active_again["state"] == FollowerState.ACTIVE.value
            assert db_doc_active_again["enabled"] is True


            # Attempt to update a non-existent follower
            nonexistent_id = str(ObjectId())
            nonexistent_result = await follower_service.update_follower_state(nonexistent_id, FollowerState.ARCHIVED)
            assert nonexistent_result is None # Should return None for non-existent

        finally:
            # Clean up
            await test_mongo_db.followers.delete_one({"_id": follower_id})

    asyncio.run(test_state_updates())


@pytest.mark.asyncio
def test_service_error_handling(test_mongo_db: AsyncIOMotorDatabase):
    """Test error handling in the follower service."""
    from admin_api.app.services.follower_service import FollowerService
    from admin_api.app.schemas.follower import FollowerCreate
    from admin_api.app.core.config import get_settings
    from motor.core import Collection

    async def test_errors():
        settings = get_settings()
        follower_service = FollowerService(db=test_mongo_db, settings=settings)

        # Mock the collection to raise an exception on insert_one
        with patch.object(test_mongo_db, 'followers') as mock_collection:
            mock_collection.insert_one.side_effect = Exception("Insert error")

            # Attempt to create a follower, expect an exception
            follower_create = FollowerCreate(
                email="error-test@example.com",
                iban="NL91ABNA0417164307",
                ibkr_username="erroruser",
                ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-erroruser",
                commission_pct=20.0,
            )
            with pytest.raises(Exception, match="Insert error"):
                await follower_service.create_follower(follower_create)

        # Mock the collection to raise an exception on find_one
        with patch.object(test_mongo_db, 'followers') as mock_collection:
            mock_collection.find_one.side_effect = Exception("Find error")

            # Attempt to get a follower by id, expect an exception
            with pytest.raises(Exception, match="Find error"):
                await follower_service.get_follower_by_id("some-id")

        # Mock the collection to raise an exception on find
        with patch.object(test_mongo_db, 'followers') as mock_collection:
            # Mock the cursor returned by find
            mock_cursor = MagicMock()
            mock_cursor.to_list.side_effect = Exception("Find all error")
            mock_collection.find.return_value = mock_cursor

            # Attempt to get all followers, expect an exception
            with pytest.raises(Exception, match="Find all error"):
                await follower_service.get_followers()

        # Mock the collection to raise an exception on update_one
        with patch.object(test_mongo_db, 'followers') as mock_collection:
             mock_collection.update_one.side_effect = Exception("Update error")

             # Attempt to toggle follower enabled, expect an exception
             with pytest.raises(Exception, match="Update error"):
                 await follower_service.toggle_follower_enabled("some-id")

        # Mock the collection to raise an exception on delete_one
        with patch.object(test_mongo_db, 'followers') as mock_collection:
             mock_collection.delete_one.side_effect = Exception("Delete error")

             # Attempt to delete follower, expect an exception
             with pytest.raises(Exception, match="Delete error"):
                 await follower_service.delete_follower("some-id")


    asyncio.run(test_errors())


@pytest.mark.asyncio # Ensure async marker
async def test_dashboard_api_endpoints( # Ensure async def
    admin_api_client: tuple[httpx.AsyncClient, Any], # Expect tuple
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _ = admin_api_client # Unpack client
    """Test the dashboard API endpoints."""
    # Create some test followers
    follower_data_active = {
        "email": "dashboard-test-active@example.com",
        "iban": "IBAN-DASHBOARD-ACTIVE",
        "ibkr_username": "dashboard_active_user",
        "commission_pct": 10,
        "ibkr_secret_ref": "test-secret-ref",
        "enabled": True,
        "state": "ACTIVE"
    }
    follower_data_inactive = {
        "email": "dashboard-test-inactive@example.com",
        "iban": "IBAN-DASHBOARD-INACTIVE",
        "ibkr_username": "dashboard_inactive_user",
        "commission_pct": 10,
        "ibkr_secret_ref": "test-secret-ref",
        "enabled": False,
        "state": "DISABLED"
    }

    # Use the client to create followers via the API
    response_active = await admin_api_client.post( # Ensure await
        "/api/v1/followers",
        json=follower_data_active
    )
    assert response_active.status_code == 201
    created_active = response_active.json()
    active_follower_id = created_active["id"]

    response_inactive = await admin_api_client.post( # Ensure await
        "/api/v1/followers",
        json=follower_data_inactive
    )
    assert response_inactive.status_code == 201
    created_inactive = response_inactive.json()
    inactive_follower_id = created_inactive["id"]

    try:
        # Test get_dashboard_summary
        response_summary = await admin_api_client.get("/api/v1/dashboard/summary")
        assert response_summary.status_code == 200
        summary_data = response_summary.json()
        assert summary_data["follower_count"] >= 2 # May have other followers from other tests
        assert summary_data["active_follower_count"] >= 1
        assert "last_updated" in summary_data

        # Test get_dashboard_stats
        response_stats = await admin_api_client.get("/api/v1/dashboard/stats")
        assert response_stats.status_code == 200
        stats_data = response_stats.json()
        assert "stats" in stats_data
        assert isinstance(stats_data["stats"], list)
        follower_stats = next((s for s in stats_data["stats"] if s["type"] == "followers"), None)
        assert follower_stats is not None
        assert follower_stats["total"] >= 2
        assert follower_stats["active"] >= 1
        assert follower_stats["inactive"] >= 1
        assert "last_updated" in stats_data

        # Test get_dashboard_alerts (placeholder)
        response_alerts = await admin_api_client.get("/api/v1/dashboard/alerts")
        assert response_alerts.status_code == 200
        alerts_data = response_alerts.json()
        assert "alerts" in alerts_data
        assert isinstance(alerts_data["alerts"], list)
        assert "last_updated" in alerts_data

        # Test get_dashboard_performance (placeholder)
        response_performance = await admin_api_client.get("/api/v1/dashboard/performance")
        assert response_performance.status_code == 200
        performance_data = response_performance.json()
        assert "performance" in performance_data
        assert "last_updated" in performance_data

        # Test the periodic task (basic check that it runs without crashing)
        # This is hard to test comprehensively without a real WebSocket client
        # But we can at least mock dependencies and see if it runs a cycle
        from admin_api.app.api.v1.endpoints.dashboard import periodic_follower_update_task
        from admin_api.app.services.follower_service import FollowerService
        from unittest.mock import AsyncMock, MagicMock, patch
        import asyncio

        mock_follower_service = MagicMock(spec=FollowerService)
        mock_follower_service.get_followers.return_value = [] # Return empty list for simplicity

        with patch('admin_api.app.api.v1.endpoints.dashboard.broadcast_updates', AsyncMock()) as mock_broadcast:
            # Create a task that will be cancelled immediately
            task = asyncio.create_task(periodic_follower_update_task(
                follower_service=mock_follower_service,
                interval_seconds=0.1
            ))

            # Wait a short time to let it run at least one cycle
            await asyncio.sleep(0.5)

            # Cancel the task
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass  # Expected

            # Verify broadcast_updates was called at least once
            assert mock_broadcast.called


    finally:
        # Clean up test followers
        await test_mongo_db.followers.delete_one({"_id": active_follower_id})
        await test_mongo_db.followers.delete_one({"_id": inactive_follower_id})


@pytest.mark.asyncio # Ensure async marker
async def test_dashboard_api_error_handling( # Ensure async def
    admin_api_client: tuple[httpx.AsyncClient, Any], # Expect tuple
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _ = admin_api_client # Unpack client
    """Test error handling in the dashboard API endpoints."""
    # Mock the follower service to raise an exception
    with patch("admin_api.app.api.v1.endpoints.dashboard.get_follower_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.get_followers.side_effect = Exception("Database error")
        mock_get_service.return_value = mock_service

        # Test get_dashboard_summary error handling
        response_summary = await admin_api_client.get("/api/v1/dashboard/summary")
        assert response_summary.status_code == 500
        assert "Database error" in response_summary.json()["detail"]

        # Test get_dashboard_stats error handling
        response_stats = await admin_api_client.get("/api/v1/dashboard/stats")
        assert response_stats.status_code == 500
        assert "Database error" in response_stats.json()["detail"]

        # Note: Alerts and Performance endpoints are placeholders and don't use the service yet,
        # so no specific error handling tests for them based on service errors.


@pytest.mark.asyncio
async def test_periodic_follower_update_task(
    admin_api_client: httpx.AsyncClient,
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test the periodic follower update task.

    This test verifies:
    1. The task runs and broadcasts updates
    2. The task handles errors gracefully
    """
    # Import the necessary modules
    from admin_api.app.api.v1.endpoints.dashboard import active_connections, periodic_follower_update_task
    from admin_api.app.services.follower_service import FollowerService

    # Create a mock follower service
    mock_follower_service = MagicMock(spec=FollowerService)
    mock_follower_service.get_followers.return_value = [
        MagicMock(id="1", email="test1@example.com", enabled=True),
        MagicMock(id="2", email="test2@example.com", enabled=False)
    ]

    # Create a mock WebSocket connection
    mock_websocket = MagicMock()
    mock_websocket.send_json = AsyncMock()
    active_connections.add(mock_websocket)

    try:
        # Mock broadcast_updates to avoid actual WebSocket operations
        with patch('admin_api.app.api.v1.endpoints.dashboard.broadcast_updates', AsyncMock()) as mock_broadcast:
            # Create a task that will be cancelled immediately
            import asyncio
            task = asyncio.create_task(periodic_follower_update_task(
                follower_service=mock_follower_service,
                interval_seconds=0.1
            ))

            # Wait a longer time to let it run at least one cycle
            await asyncio.sleep(0.5) # Increased sleep time

            # Cancel the task
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass  # Expected

            # Verify broadcast_updates was called at least once
            assert mock_broadcast.called

        # Test error handling in the task
        mock_follower_service.get_followers.side_effect = Exception("Database error")

        with patch('admin_api.app.api.v1.endpoints.dashboard.broadcast_updates', AsyncMock()) as mock_broadcast:
            # Create a task that will be cancelled immediately
            import asyncio
            task = asyncio.create_task(periodic_follower_update_task(
                follower_service=mock_follower_service,
                interval_seconds=0.1
            ))

            # Wait a short time for the task to run, hit the exception, and call the mock
            await asyncio.sleep(0.3) # Correctly indented sleep

            # Cancel the task
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass  # Expected

            # Verify the task didn't crash despite the exception
            # The broadcast should still be called with an error message
            assert mock_broadcast.called
    finally: # Correctly aligned finally block relative to the main 'try' starting around line 1090
        # Clean up by removing our mock connection
        active_connections.remove(mock_websocket) # Correctly indented cleanup


@pytest.mark.asyncio # Ensure async marker
async def test_followers_api_error_handling( # Ensure async def
    admin_api_client: tuple[httpx.AsyncClient, Any], # Expect tuple
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _ = admin_api_client # Unpack client
    """Test error handling in the followers API endpoints."""
    # Test 404 error when trying to close positions for a non-existent follower
    nonexistent_id = "nonexistent-follower-id"
    response = await admin_api_client.post(
        f"/api/v1/close/{nonexistent_id}"
    )

    assert response.status_code == 404
    error_detail = response.json()
    assert "detail" in error_detail
    assert nonexistent_id in error_detail["detail"]

    # Test service unavailable error when trigger_close_positions fails
    # We need to create a follower first
    follower_data = {
        "email": "close-test@example.com",
        "iban": "IBAN-CLOSE-TEST",
        "ibkr_username": "close_test_user",
        "commission_pct": 15,
        "ibkr_secret_ref": "test-secret-ref"
    }

    response = await admin_api_client.post( # Ensure await
        "/api/v1/followers",
        json=follower_data
    )

    assert response.status_code == 201
    created_follower = response.json()
    follower_id = created_follower["id"]

    try:
        # Mock the trigger_close_positions method to return False
        from unittest.mock import patch
        with patch("admin_api.app.services.follower_service.FollowerService.trigger_close_positions", return_value=False) as mock_trigger:
            # Mock the get_settings dependency
            with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
                response = await admin_api_client.post(
                    f"/api/v1/close/{follower_id}"
                )

        assert response.status_code == 503 # Service Unavailable
        assert "Failed to trigger close positions" in response.json()["detail"]
        mock_trigger.assert_called_once_with(follower_id)

        # Test service unavailable error when trigger_close_positions raises an exception
        with patch("admin_api.app.services.follower_service.FollowerService.trigger_close_positions", side_effect=Exception("Pub/Sub error")) as mock_trigger:
             # Mock the get_settings dependency
            with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
                response = await admin_api_client.post(
                    f"/api/v1/close/{follower_id}"
                )

        assert response.status_code == 503 # Service Unavailable
        assert "Pub/Sub error" in response.json()["detail"]
        mock_trigger.assert_called_once_with(follower_id)

    finally:
        # Clean up the created follower
        await test_mongo_db.followers.delete_one({"_id": follower_id})


@pytest.mark.asyncio # Ensure async marker
async def test_list_followers_error_handling( # Ensure async def
    admin_api_client: tuple[httpx.AsyncClient, Any], # Expect tuple
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _ = admin_api_client # Unpack client
    """Test error handling in the list followers endpoint."""
    # Mock the follower service to raise an exception
    with patch("admin_api.app.api.v1.endpoints.followers.get_follower_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.get_followers.side_effect = Exception("Database connection failed")
        mock_get_service.return_value = mock_service

        response = await admin_api_client.get("/api/v1/followers")

        assert response.status_code == 500 # Internal Server Error
        assert "Database connection failed" in response.json()["detail"]


@pytest.mark.asyncio # Ensure async marker
async def test_create_follower_service_error( # Ensure async def
    admin_api_client: tuple[httpx.AsyncClient, Any], # Expect tuple
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _ = admin_api_client # Unpack client
    """Test error handling when follower service fails during creation."""
    follower_data = {
        "email": "create-error-test@example.com",
        "iban": "IBAN-CREATE-ERROR",
        "ibkr_username": "create_error_user",
        "commission_pct": 15,
        "ibkr_secret_ref": "test-secret-ref"
    }

    # Mock the follower service to raise an exception during create_follower
    with patch("admin_api.app.api.v1.endpoints.followers.get_follower_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.create_follower.side_effect = Exception("Service creation failed")
        mock_get_service.return_value = mock_service

        response = await admin_api_client.post(
            "/api/v1/followers",
            json=follower_data
        )

        assert response.status_code == 500 # Internal Server Error
        assert "Service creation failed" in response.json()["detail"]


@pytest.mark.asyncio # Ensure async marker
async def test_toggle_follower_service_error( # Ensure async def
    admin_api_client: tuple[httpx.AsyncClient, Any], # Expect tuple
    test_mongo_db: AsyncIOMotorDatabase,
):
    admin_api_client, _ = admin_api_client # Unpack client
    """Test error handling when follower service fails during toggle."""
    # We need a follower to attempt toggling
    follower_data = {
        "email": "toggle-error-test@example.com",
        "iban": "IBAN-TOGGLE-ERROR",
        "ibkr_username": "toggle_error_user",
        "commission_pct": 15,
        "ibkr_secret_ref": "test-secret-ref"
    }

    response = await admin_api_client.post(
        "/api/v1/followers",
        json=follower_data
    )
    assert response.status_code == 201
    created_follower = response.json()
    follower_id = created_follower["id"]

    try:
        # Mock the follower service to raise an exception during toggle_follower_enabled
        with patch("admin_api.app.api.v1.endpoints.followers.get_follower_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.toggle_follower_enabled.side_effect = Exception("Service toggle failed")
            mock_get_service.return_value = mock_service

            response = await admin_api_client.post(
                f"/api/v1/followers/{follower_id}/toggle"
            )

            assert response.status_code == 500 # Internal Server Error
            assert "Service toggle failed" in response.json()["detail"]

    finally:
        # Clean up the created follower
        await test_mongo_db.followers.delete_one({"_id": follower_id})


@pytest.mark.asyncio
async def test_follower_service_additional_methods(
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test additional FollowerService methods integration with MongoDB.

    This test verifies:
    1. Followers can be retrieved by email
    2. Followers can be updated
    3. Followers can be deleted
    """
    from admin_api.app.services.follower_service import FollowerService
    from admin_api.app.schemas.follower import FollowerCreate, FollowerUpdate
    from admin_api.app.core.config import get_settings

    settings = get_settings()
    service = FollowerService(db=test_mongo_db, settings=settings)
    follower_id_to_cleanup = None # Store string ID

    try:
        # Create a new follower
        follower_create = FollowerCreate(
            email="additional-methods-test@example.com",
            iban="NL91ABNA0417164308",
            ibkr_username="additionaluser",
            ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-additionaluser",
            commission_pct=20.0,
        )
        follower = await service.create_follower(follower_create)
        follower_id = follower.id
        follower_id_to_cleanup = follower_id

        # Test get_follower_by_email
        follower_by_email = await service.get_follower_by_email(follower.email)
        assert follower_by_email is not None
        assert follower_by_email.id == follower_id
        assert follower_by_email.email == follower.email

        # Test update_follower
        update_data = FollowerUpdate(
            email="updated-additional-methods-test@example.com",
            commission_pct=25.0,
        )
        updated_follower = await service.update_follower(follower_id, update_data)
        assert updated_follower is not None
        assert updated_follower.id == follower_id
        assert updated_follower.email == update_data.email
        assert updated_follower.commission_pct == update_data.commission_pct

        # Verify in DB
        db_doc = await test_mongo_db.followers.find_one({"_id": follower_id})
        assert db_doc["email"] == update_data.email
        assert db_doc["commission_pct"] == update_data.commission_pct

        # Test delete_follower
        delete_result = await service.delete_follower(follower_id)
        assert delete_result is True # Assuming service returns True on success

        # Verify deleted in DB
        deleted_doc = await test_mongo_db.followers.find_one({"_id": follower_id})
        assert deleted_doc is None

        # Test deleting non-existent follower
        nonexistent_id = str(ObjectId())
        delete_nonexistent_result = await service.delete_follower(nonexistent_id)
        assert delete_nonexistent_result is False # Assuming service returns False for non-existent

    finally:
        # Ensure cleanup even if delete_follower failed in the test
        if follower_id_to_cleanup:
             await test_mongo_db.followers.delete_one({"_id": follower_id_to_cleanup})


@pytest.mark.asyncio
async def test_follower_service_batch_operations(
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test batch operations in FollowerService integration with MongoDB.

    This test verifies:
    1. Multiple followers can be created in a batch
    2. Multiple followers can be retrieved by IDs
    """
    from admin_api.app.services.follower_service import FollowerService
    from admin_api.app.schemas.follower import FollowerCreate, FollowerUpdate
    from admin_api.app.core.config import get_settings

    settings = get_settings()
    service = FollowerService(db=test_mongo_db, settings=settings)
    follower_ids_to_cleanup = []

    try:
        # Test batch creation
        batch_creates = [
            FollowerCreate(email="batch-test-1@example.com", iban="IBAN-BATCH-1", ibkr_username="batchuser1", commission_pct=10, ibkr_secret_ref="secret1"),
            FollowerCreate(email="batch-test-2@example.com", iban="IBAN-BATCH-2", ibkr_username="batchuser2", commission_pct=12, ibkr_secret_ref="secret2"),
            FollowerCreate(email="batch-test-3@example.com", iban="IBAN-BATCH-3", ibkr_username="batchuser3", commission_pct=14, ibkr_secret_ref="secret3"),
        ]
        created_followers = await service.create_followers_batch(batch_creates)
        assert len(created_followers) == len(batch_creates)
        follower_ids = [f.id for f in created_followers]
        follower_ids_to_cleanup.extend(follower_ids)

        # Verify in DB
        db_docs = await test_mongo_db.followers.find({"_id": {"$in": follower_ids}}).to_list(length=len(follower_ids))
        assert len(db_docs) == len(follower_ids)
        db_ids = {doc["_id"] for doc in db_docs}
        assert set(follower_ids) == db_ids

        # Test get_followers_by_ids
        retrieved_followers = await service.get_followers_by_ids(follower_ids)
        assert len(retrieved_followers) == len(follower_ids)
        retrieved_ids = {f.id for f in retrieved_followers}
        assert set(follower_ids) == retrieved_ids

        # Test getting followers with some non-existent IDs
        mixed_ids = follower_ids + [str(ObjectId()), str(ObjectId())]
        retrieved_mixed = await service.get_followers_by_ids(mixed_ids)
        assert len(retrieved_mixed) == len(follower_ids) # Should only return existing ones
        retrieved_mixed_ids = {f.id for f in retrieved_mixed}
        assert set(follower_ids) == retrieved_mixed_ids


    finally:
        # Clean up
        if follower_ids_to_cleanup:
            await test_mongo_db.followers.delete_many({"_id": {"$in": follower_ids_to_cleanup}})


@pytest.mark.asyncio
async def test_follower_service_trading_operations(
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test trading-related operations in FollowerService integration.

    This test verifies:
    1. Recording trades for a follower
    2. Recording positions for a follower
    3. Updating assignment state for a position
    """
    from admin_api.app.services.follower_service import FollowerService
    from admin_api.app.schemas.follower import FollowerCreate
    from admin_api.app.core.config import get_settings
    from spreadpilot_core.models.trade import Trade
    from spreadpilot_core.models.position import Position, AssignmentState
    from unittest.mock import AsyncMock, MagicMock, patch
    import datetime

    settings = get_settings()
    service = FollowerService(db=test_mongo_db, settings=settings)
    follower_id_to_cleanup = None
    trade_ids_to_cleanup = []
    position_ids_to_cleanup = []

    try:
        # Create a follower
        follower_create = FollowerCreate(
            email="trading-ops-test@example.com",
            iban="IBAN-TRADING-OPS",
            ibkr_username="tradingopuser",
            ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-tradingopuser",
            commission_pct=20.0,
        )
        follower = await service.create_follower(follower_create)
        follower_id = follower.id
        follower_id_to_cleanup = follower_id

        # Test record_trade
        trade_data = {
            "follower_id": follower_id,
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 10,
            "price": 150.0,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "commission": 1.5,
            "details": {"order_id": "12345"}
        }
        trade = Trade(**trade_data)

        # Mock the collection to return an ObjectId on insert_one
        with patch.object(test_mongo_db, 'trades') as mock_collection:
             mock_collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())
             # Patch the actual record_trade method to use the mock collection
             with patch("admin_api.app.services.follower_service.FollowerService.record_trade", wraps=service.record_trade) as mock_record:
                 trade_id = await mock_record(trade)
                 assert trade_id is not None # Assuming it returns the inserted ID
                 trade_ids_to_cleanup.append(trade_id) # Store the returned ID

        # Test record_position
        test_positions = [
            Position(
                follower_id=follower_id,
                symbol="GOOG",
                quantity=5,
                average_cost=2500.0,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                assignment_state=AssignmentState.PENDING,
                details={"contract_id": "67890"}
            ),
             Position(
                follower_id=follower_id,
                symbol="MSFT",
                quantity=20,
                average_cost=300.0,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                assignment_state=AssignmentState.ASSIGNED,
                details={"contract_id": "abcde"}
            )
        ]

        # Mock the collection to return InsertManyResult with ObjectIds
        with patch.object(test_mongo_db, 'positions') as mock_collection:
            mock_collection.insert_many.return_value = MagicMock(inserted_ids=[ObjectId(), ObjectId()])
            # Patch the actual record_positions method
            with patch("admin_api.app.services.follower_service.FollowerService.record_positions", wraps=service.record_positions) as mock_record_positions:
                position_ids = await mock_record_positions(test_positions)
                assert len(position_ids) == len(test_positions)
                position_ids_to_cleanup.extend(position_ids) # Store the returned IDs

        # Test update_position_assignment_state
        if position_ids_to_cleanup:
            position_id_to_update = position_ids_to_cleanup[0]
            updated_position = await service.update_position_assignment_state(position_id_to_update, AssignmentState.ASSIGNED)
            assert updated_position is not None
            assert updated_position.assignment_state == AssignmentState.ASSIGNED

            # Verify in DB
            db_doc = await test_mongo_db.positions.find_one({"_id": position_id_to_update})
            assert db_doc["assignment_state"] == AssignmentState.ASSIGNED.value


    finally:
        # Clean up
        if follower_id_to_cleanup:
            await test_mongo_db.followers.delete_one({"_id": follower_id_to_cleanup})
        if trade_ids_to_cleanup:
            # Assuming trade_ids_to_cleanup contains ObjectIds returned by the mock
            await test_mongo_db.trades.delete_many({"_id": {"$in": trade_ids_to_cleanup}})
        if position_ids_to_cleanup:
             # Assuming position_ids_to_cleanup contains ObjectIds returned by the mock
            await test_mongo_db.positions.delete_many({"_id": {"$in": position_ids_to_cleanup}})
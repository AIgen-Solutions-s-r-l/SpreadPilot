# Import the function to test and the collection name constant
# Use importlib to avoid potential import issues during test collection if admin_api is not directly in path
import importlib
import os
from unittest.mock import AsyncMock, patch

import pytest
from motor.motor_asyncio import AsyncIOMotorDatabase

admin_api_main = importlib.import_module("admin_api.app.main")
secrets_utils = importlib.import_module("spreadpilot_core.utils.secrets")

load_secrets_into_env = admin_api_main.load_secrets_into_env
SECRETS_COLLECTION_NAME = secrets_utils.SECRETS_COLLECTION_NAME

# Mark all tests in this module as async using pytest-asyncio
pytestmark = pytest.mark.asyncio

# Secrets to use in this test
TEST_SECRETS_CONFIG = [
    "TEST_SECRET_ONE",
    "TEST_SECRET_TWO",
    "NON_EXISTENT_SECRET",  # Include one that won't be found
]


@pytest.fixture(autouse=True)
def cleanup_env_vars():
    """Fixture to automatically clean up environment variables set during tests."""
    original_env = os.environ.copy()
    yield
    # Restore original environment variables, removing any added ones
    added_keys = set(os.environ.keys()) - set(original_env.keys())
    for key in added_keys:
        del os.environ[key]
    # Restore any modified keys (less common but safer)
    for key, value in original_env.items():
        os.environ[key] = value


async def test_load_secrets_into_env_integration(test_mongo_db: AsyncIOMotorDatabase):
    """
    Integration test for load_secrets_into_env.
    Verifies that secrets are fetched from the test MongoDB and set as environment variables.
    """
    # --- Arrange ---
    secret_one_value = "value_one_123"
    secret_two_value = "value_two_456"
    test_env_name = "testing_load"  # Use a specific env for this test

    # Insert mock secrets into the test database
    secrets_collection = test_mongo_db[SECRETS_COLLECTION_NAME]
    await secrets_collection.insert_many(
        [
            {
                "name": "TEST_SECRET_ONE",
                "environment": test_env_name,
                "value": secret_one_value,
            },
            {
                "name": "TEST_SECRET_TWO",
                "environment": test_env_name,
                "value": secret_two_value,
            },
            # NON_EXISTENT_SECRET is intentionally omitted
        ]
    )

    # Ensure the target env vars are not set initially
    os.environ.pop("TEST_SECRET_ONE", None)
    os.environ.pop("TEST_SECRET_TWO", None)
    os.environ.pop("NON_EXISTENT_SECRET", None)

    # Patch the list of secrets the function tries to fetch
    # Patch the database connection/getter functions used *within* load_secrets_into_env
    # Patch APP_ENV to control the environment lookup
    with (
        patch.dict(os.environ, {"APP_ENV": test_env_name}, clear=False),
        patch("admin_api.app.main.SECRETS_TO_FETCH", TEST_SECRETS_CONFIG),
        patch(
            "admin_api.app.db.mongodb.connect_to_mongo", new_callable=AsyncMock
        ) as mock_connect,
        patch(
            "admin_api.app.db.mongodb.close_mongo_connection", new_callable=AsyncMock
        ) as mock_close,
        patch(
            "admin_api.app.db.mongodb.get_mongo_db",
            AsyncMock(return_value=test_mongo_db),
        ) as mock_get_db,
    ):

        # --- Act ---
        await load_secrets_into_env()

        # --- Assert ---
        # Check that the correct environment variables were set
        assert os.environ.get("TEST_SECRET_ONE") == secret_one_value
        assert os.environ.get("TEST_SECRET_TWO") == secret_two_value
        # Check that the non-existent secret was not set
        assert "NON_EXISTENT_SECRET" not in os.environ

        # Mock assertions are removed as we are testing integration with a real DB collection here.
        # The environment variable assertions above confirm the core functionality.

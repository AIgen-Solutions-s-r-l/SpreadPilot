import os
from unittest.mock import AsyncMock, patch

import pytest

# Assuming spreadpilot-core is installed or in PYTHONPATH
from spreadpilot_core.utils.secrets import (
    SECRETS_COLLECTION_NAME,
    get_secret_from_mongo,
)

# Mark all tests in this module as async using pytest-asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    """Fixture to create a mock AsyncIOMotorDatabase."""
    mock_db_instance = AsyncMock()
    mock_collection = AsyncMock()
    mock_db_instance.__getitem__.return_value = mock_collection  # db['secrets']
    return mock_db_instance


async def test_get_secret_success_explicit_env(mock_db):
    """Test successful secret retrieval with an explicit environment."""
    secret_name = "TEST_API_KEY"
    environment = "production"
    expected_value = "prod_secret_123"

    mock_db[SECRETS_COLLECTION_NAME].find_one.return_value = {
        "name": secret_name,
        "environment": environment,
        "value": expected_value,
    }

    result = await get_secret_from_mongo(mock_db, secret_name, environment)

    assert result == expected_value
    mock_db[SECRETS_COLLECTION_NAME].find_one.assert_awaited_once_with(
        {"name": secret_name, "environment": environment}
    )


@patch.dict(os.environ, {"APP_ENV": "staging"}, clear=True)
async def test_get_secret_success_default_env(mock_db):
    """Test successful secret retrieval using default environment from APP_ENV."""
    secret_name = "TEST_API_KEY"
    environment = "staging"  # Should be picked from APP_ENV
    expected_value = "staging_secret_456"

    mock_db[SECRETS_COLLECTION_NAME].find_one.return_value = {
        "name": secret_name,
        "environment": environment,
        "value": expected_value,
    }

    result = await get_secret_from_mongo(mock_db, secret_name)  # No environment passed

    assert result == expected_value
    mock_db[SECRETS_COLLECTION_NAME].find_one.assert_awaited_once_with(
        {"name": secret_name, "environment": environment}
    )


@patch.dict(os.environ, {}, clear=True)  # Ensure APP_ENV is not set
async def test_get_secret_success_default_env_fallback(mock_db):
    """Test successful secret retrieval using fallback default environment ('development')."""
    secret_name = "TEST_API_KEY"
    environment = "development"  # Should fallback to this
    expected_value = "dev_secret_789"

    mock_db[SECRETS_COLLECTION_NAME].find_one.return_value = {
        "name": secret_name,
        "environment": environment,
        "value": expected_value,
    }

    result = await get_secret_from_mongo(mock_db, secret_name)  # No environment passed

    assert result == expected_value
    mock_db[SECRETS_COLLECTION_NAME].find_one.assert_awaited_once_with(
        {"name": secret_name, "environment": environment}
    )


async def test_get_secret_not_found(mock_db):
    """Test case where the secret is not found in the database."""
    secret_name = "NON_EXISTENT_SECRET"
    environment = "production"

    mock_db[SECRETS_COLLECTION_NAME].find_one.return_value = None  # Simulate not found

    result = await get_secret_from_mongo(mock_db, secret_name, environment)

    assert result is None
    mock_db[SECRETS_COLLECTION_NAME].find_one.assert_awaited_once_with(
        {"name": secret_name, "environment": environment}
    )


async def test_get_secret_found_but_value_missing(mock_db):
    """Test case where the secret document exists but lacks the 'value' field."""
    secret_name = "SECRET_NO_VALUE"
    environment = "production"

    mock_db[SECRETS_COLLECTION_NAME].find_one.return_value = {
        "name": secret_name,
        "environment": environment,
        # Missing "value" field
    }

    result = await get_secret_from_mongo(mock_db, secret_name, environment)

    assert result is None
    mock_db[SECRETS_COLLECTION_NAME].find_one.assert_awaited_once_with(
        {"name": secret_name, "environment": environment}
    )


async def test_get_secret_db_error(mock_db):
    """Test case where the database operation raises an exception."""
    secret_name = "SECRET_DB_ERROR"
    environment = "production"

    mock_db[SECRETS_COLLECTION_NAME].find_one.side_effect = Exception(
        "Simulated DB Connection Error"
    )

    result = await get_secret_from_mongo(mock_db, secret_name, environment)

    assert result is None
    mock_db[SECRETS_COLLECTION_NAME].find_one.assert_awaited_once_with(
        {"name": secret_name, "environment": environment}
    )


async def test_get_secret_no_db_instance():
    """Test case where the db instance is None."""
    secret_name = "ANY_SECRET"
    environment = "production"

    result = await get_secret_from_mongo(None, secret_name, environment)

    assert result is None


async def test_get_secret_value_is_not_string(mock_db):
    """Test that non-string values are converted to string."""
    secret_name = "NUMERIC_SECRET"
    environment = "production"
    expected_value = 12345  # Numeric value

    mock_db[SECRETS_COLLECTION_NAME].find_one.return_value = {
        "name": secret_name,
        "environment": environment,
        "value": expected_value,
    }

    result = await get_secret_from_mongo(mock_db, secret_name, environment)

    assert result == str(expected_value)  # Should be converted to string
    mock_db[SECRETS_COLLECTION_NAME].find_one.assert_awaited_once_with(
        {"name": secret_name, "environment": environment}
    )

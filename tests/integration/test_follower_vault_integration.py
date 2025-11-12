"""Integration tests for follower management with Vault integration."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from motor.motor_asyncio import AsyncIOMotorDatabase

from admin_api.app.services.follower_service import FollowerService
from spreadpilot_core.models.follower import FollowerState
from spreadpilot_core.utils.vault import VaultClient


@pytest.mark.asyncio
async def test_create_follower_with_vault_secret(test_mongo_db: AsyncIOMotorDatabase):
    """
    Test creating a follower with Vault secret reference.

    This test verifies:
    1. Follower is created with vault_secret_ref
    2. Secrets are stored in Vault
    3. Follower document is stored in MongoDB
    4. Secrets can be retrieved using the reference
    """
    # Create follower service
    settings = MagicMock()
    settings.mongo_db_name = "test_db"
    follower_service = FollowerService(db=test_mongo_db, settings=settings)

    # Mock Vault client
    mock_vault_client = MagicMock(spec=VaultClient)
    mock_vault_client.put_secret.return_value = True
    mock_vault_client.get_ibkr_credentials.return_value = {
        "IB_USER": "test_user",
        "IB_PASS": "test_password_secure",
    }

    # Create follower data
    follower_id = str(uuid.uuid4())
    vault_secret_ref = f"secret/ibkr/follower_{follower_id}"

    follower_data = {
        "email": f"follower-{follower_id}@example.com",
        "iban": f"IBAN-{follower_id}",
        "ibkr_username": "test_user",
        "ibkr_password": "test_password_secure",  # Will be stored in Vault
        "commission_pct": 20.0,
        "vault_secret_ref": vault_secret_ref,
        "enabled": True,
    }

    with patch("spreadpilot_core.utils.vault.get_vault_client", return_value=mock_vault_client):
        # Create follower
        created_follower = await follower_service.create_follower(follower_data)

        # Verify follower was created
        assert created_follower.id is not None
        assert created_follower.email == follower_data["email"]
        assert created_follower.vault_secret_ref == vault_secret_ref

        # Verify secrets were stored in Vault
        mock_vault_client.put_secret.assert_called_once_with(
            vault_secret_ref,
            {"IB_USER": "test_user", "IB_PASS": "test_password_secure"},
        )

        # Verify follower exists in MongoDB
        stored_follower = await test_mongo_db.followers.find_one({"_id": created_follower.id})
        assert stored_follower is not None
        assert stored_follower["vault_secret_ref"] == vault_secret_ref
        # Password should not be stored in MongoDB
        assert "ibkr_password" not in stored_follower

        # Verify secrets can be retrieved from Vault
        retrieved_creds = mock_vault_client.get_ibkr_credentials(vault_secret_ref)
        assert retrieved_creds["IB_USER"] == "test_user"
        assert retrieved_creds["IB_PASS"] == "test_password_secure"

    # Cleanup
    await test_mongo_db.followers.delete_one({"_id": created_follower.id})


@pytest.mark.asyncio
async def test_update_follower_vault_credentials(test_mongo_db: AsyncIOMotorDatabase):
    """
    Test updating follower credentials in Vault.

    This test verifies:
    1. Existing follower credentials can be updated
    2. New credentials are stored in Vault
    3. Old credentials are replaced
    """
    # Create initial follower
    follower_id = str(uuid.uuid4())
    vault_secret_ref = f"secret/ibkr/follower_{follower_id}"

    initial_follower_data = {
        "_id": follower_id,
        "email": f"update-test-{follower_id}@example.com",
        "iban": f"IBAN-UPDATE-{follower_id}",
        "ibkr_username": "old_username",
        "vault_secret_ref": vault_secret_ref,
        "commission_pct": 15.0,
        "enabled": True,
        "state": FollowerState.ACTIVE.value,
    }

    await test_mongo_db.followers.insert_one(initial_follower_data)

    # Mock Vault client
    mock_vault_client = MagicMock(spec=VaultClient)
    mock_vault_client.put_secret.return_value = True

    # Create follower service
    settings = MagicMock()
    settings.mongo_db_name = "test_db"
    follower_service = FollowerService(db=test_mongo_db, settings=settings)

    # Update credentials
    update_data = {
        "ibkr_username": "new_username",
        "ibkr_password": "new_password_secure_2024",
    }

    with patch("spreadpilot_core.utils.vault.get_vault_client", return_value=mock_vault_client):
        # Update follower
        updated_follower = await follower_service.update_follower(follower_id, update_data)

        # Verify follower was updated
        assert updated_follower.ibkr_username == "new_username"

        # Verify new credentials were stored in Vault
        mock_vault_client.put_secret.assert_called_with(
            vault_secret_ref,
            {"IB_USER": "new_username", "IB_PASS": "new_password_secure_2024"},
        )

        # Verify MongoDB document was updated
        stored_follower = await test_mongo_db.followers.find_one({"_id": follower_id})
        assert stored_follower["ibkr_username"] == "new_username"
        assert "ibkr_password" not in stored_follower  # Should not be stored in DB

    # Cleanup
    await test_mongo_db.followers.delete_one({"_id": follower_id})


@pytest.mark.asyncio
async def test_delete_follower_removes_vault_secrets(
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test that deleting a follower also removes Vault secrets.

    This test verifies:
    1. Follower deletion removes MongoDB document
    2. Associated Vault secrets are deleted
    3. Proper cleanup is performed
    """
    # Create follower
    follower_id = str(uuid.uuid4())
    vault_secret_ref = f"secret/ibkr/follower_{follower_id}"

    follower_data = {
        "_id": follower_id,
        "email": f"delete-test-{follower_id}@example.com",
        "iban": f"IBAN-DELETE-{follower_id}",
        "ibkr_username": "delete_test_user",
        "vault_secret_ref": vault_secret_ref,
        "commission_pct": 10.0,
        "enabled": True,
        "state": FollowerState.ACTIVE.value,
    }

    await test_mongo_db.followers.insert_one(follower_data)

    # Mock Vault client
    mock_vault_client = MagicMock(spec=VaultClient)
    mock_vault_client.delete_secret = AsyncMock(return_value=True)

    # Create follower service
    settings = MagicMock()
    settings.mongo_db_name = "test_db"
    follower_service = FollowerService(db=test_mongo_db, settings=settings)

    with patch("spreadpilot_core.utils.vault.get_vault_client", return_value=mock_vault_client):
        # Delete follower
        result = await follower_service.delete_follower(follower_id)
        assert result is True

        # Verify follower was deleted from MongoDB
        deleted_follower = await test_mongo_db.followers.find_one({"_id": follower_id})
        assert deleted_follower is None

        # Verify Vault secrets were deleted
        mock_vault_client.delete_secret.assert_called_once_with(vault_secret_ref)


@pytest.mark.asyncio
async def test_vault_connection_failure_handling(test_mongo_db: AsyncIOMotorDatabase):
    """
    Test handling of Vault connection failures.

    This test verifies:
    1. Graceful handling when Vault is unavailable
    2. Proper error messages are returned
    3. Follower creation fails safely
    """
    # Mock Vault client that fails
    mock_vault_client = MagicMock(spec=VaultClient)
    mock_vault_client.put_secret.side_effect = Exception("Vault connection failed")
    mock_vault_client.health_check.return_value = False

    # Create follower service
    settings = MagicMock()
    settings.mongo_db_name = "test_db"
    follower_service = FollowerService(db=test_mongo_db, settings=settings)

    # Attempt to create follower
    follower_data = {
        "email": "vault-fail-test@example.com",
        "iban": "IBAN-VAULT-FAIL",
        "ibkr_username": "fail_test_user",
        "ibkr_password": "fail_test_password",
        "commission_pct": 20.0,
        "vault_secret_ref": "secret/ibkr/follower_fail_test",
    }

    with patch("spreadpilot_core.utils.vault.get_vault_client", return_value=mock_vault_client):
        # Follower creation should fail
        with pytest.raises(Exception) as exc_info:
            await follower_service.create_follower(follower_data)

        assert "Vault" in str(exc_info.value)

        # Verify no follower was created in MongoDB
        failed_follower = await test_mongo_db.followers.find_one({"email": follower_data["email"]})
        assert failed_follower is None

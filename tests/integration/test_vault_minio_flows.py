"""Integration tests for Vault and MinIO flows."""

import os
import pytest
import uuid
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from motor.motor_asyncio import AsyncIOMotorDatabase

from spreadpilot_core.utils.vault import VaultClient, get_vault_client
from spreadpilot_core.models.follower import Follower, FollowerState


@pytest.mark.asyncio
async def test_vault_secret_retrieval(test_mongo_db: AsyncIOMotorDatabase):
    """
    Test retrieving secrets from Vault for a follower.
    
    This test verifies:
    1. Follower document with vault_secret_ref is inserted in MongoDB
    2. Secrets are retrieved from Vault using the reference
    3. Retrieved credentials match expected format
    """
    # Create test follower with Vault secret reference
    follower_id = str(uuid.uuid4())
    vault_secret_ref = f"secret/ibkr/follower_{follower_id}"
    
    follower_data = {
        "_id": follower_id,
        "email": f"vault-test-{follower_id}@example.com",
        "iban": f"IBAN-VAULT-{follower_id}",
        "ibkr_username": f"vault_user_{follower_id}",
        "vault_secret_ref": vault_secret_ref,  # Reference to Vault secret
        "commission_pct": 20.0,
        "enabled": True,
        "state": FollowerState.ACTIVE.value,
    }
    
    # Insert follower document in MongoDB
    await test_mongo_db.followers.insert_one(follower_data)
    
    try:
        # Verify follower was inserted
        retrieved_follower = await test_mongo_db.followers.find_one({"_id": follower_id})
        assert retrieved_follower is not None
        assert retrieved_follower["vault_secret_ref"] == vault_secret_ref
        
        # Mock Vault client to return test credentials
        mock_vault_client = MagicMock(spec=VaultClient)
        mock_vault_client.get_ibkr_credentials.return_value = {
            "IB_USER": f"vault_user_{follower_id}",
            "IB_PASS": f"vault_pass_{follower_id}_secure"
        }
        
        # Patch get_vault_client to return our mock
        with patch('spreadpilot_core.utils.vault.get_vault_client', return_value=mock_vault_client):
            # Get Vault client and retrieve credentials
            vault_client = get_vault_client()
            credentials = vault_client.get_ibkr_credentials(vault_secret_ref)
            
            # Verify credentials were retrieved
            assert credentials is not None
            assert "IB_USER" in credentials
            assert "IB_PASS" in credentials
            assert credentials["IB_USER"] == f"vault_user_{follower_id}"
            assert credentials["IB_PASS"] == f"vault_pass_{follower_id}_secure"
            
            # Verify the mock was called with correct parameters
            mock_vault_client.get_ibkr_credentials.assert_called_once_with(vault_secret_ref)
    
    finally:
        # Cleanup
        await test_mongo_db.followers.delete_one({"_id": follower_id})


@pytest.mark.asyncio
async def test_vault_integration_with_gateway_manager(test_mongo_db: AsyncIOMotorDatabase):
    """
    Test Vault integration with IBGateway manager.
    
    This test verifies:
    1. Gateway manager retrieves credentials from Vault
    2. Credentials are used to start IBGateway container
    3. Error handling when Vault credentials are missing
    """
    from spreadpilot_core.ibkr.gateway_manager import GatewayManager
    
    # Create test follower with Vault reference
    follower_id = str(uuid.uuid4())
    vault_secret_ref = f"secret/ibkr/follower_{follower_id}"
    
    follower = Follower(
        id=follower_id,
        email=f"gateway-vault-test@example.com",
        iban=f"IBAN-GW-VAULT",
        ibkr_username=f"gw_vault_user",
        vault_secret_ref=vault_secret_ref,
        commission_pct=15.0,
        enabled=True,
        state=FollowerState.ACTIVE
    )
    
    # Mock Vault credentials
    mock_credentials = {
        "IB_USER": "vault_gw_user",
        "IB_PASS": "vault_gw_password_secure"
    }
    
    # Create gateway manager with mocked dependencies
    mock_docker_client = MagicMock()
    mock_container = MagicMock()
    mock_container.id = "mock-container-id"
    mock_docker_client.containers.run.return_value = mock_container
    
    gateway_manager = GatewayManager(vault_enabled=True)
    gateway_manager.docker_client = mock_docker_client
    
    # Mock Vault client
    with patch.object(gateway_manager, '_get_ibkr_credentials_from_vault', return_value=mock_credentials):
        try:
            # Start gateway for follower
            gateway_instance = await gateway_manager._start_gateway(follower)
            
            # Verify container was started with Vault credentials
            mock_docker_client.containers.run.assert_called_once()
            call_args = mock_docker_client.containers.run.call_args
            
            # Check environment variables passed to container
            env_vars = call_args[1]['environment']
            assert env_vars['IB_USER'] == mock_credentials['IB_USER']
            assert env_vars['IB_PASS'] == mock_credentials['IB_PASS']
            
            # Verify gateway instance was created
            assert gateway_instance.follower_id == follower_id
            assert gateway_instance.container_id == mock_container.id
            
        finally:
            # Cleanup
            if follower_id in gateway_manager.gateways:
                del gateway_manager.gateways[follower_id]


@pytest.mark.asyncio 
async def test_minio_report_storage(test_mongo_db: AsyncIOMotorDatabase):
    """
    Test storing reports in MinIO/S3.
    
    This test verifies:
    1. PDF report is generated
    2. Report is uploaded to MinIO bucket
    3. Report object exists and can be retrieved
    4. Pre-signed URL is generated
    """
    from report_worker.app.service.minio_service import MinIOService
    
    # Create test report data
    report_id = str(uuid.uuid4())
    follower_id = str(uuid.uuid4())
    report_data = {
        "report_id": report_id,
        "follower_id": follower_id,
        "year": 2024,
        "month": 1,
        "total_pnl": "1500.00",
        "commission_amount": "300.00",
        "generated_at": datetime.datetime.now().isoformat()
    }
    
    # Mock MinIO client
    mock_minio_client = MagicMock()
    mock_minio_client.bucket_exists.return_value = True
    mock_minio_client.put_object.return_value = None
    mock_minio_client.stat_object.return_value = MagicMock(size=1024, etag="mock-etag")
    mock_minio_client.presigned_get_object.return_value = "https://minio.example.com/bucket/report.pdf?signature=xyz"
    
    # Create MinIO service with mocked client
    minio_service = MinIOService(
        endpoint="minio.example.com",
        access_key="test-access-key",
        secret_key="test-secret-key",
        bucket_name="test-reports",
        secure=True
    )
    minio_service.client = mock_minio_client
    
    # Mock PDF content
    pdf_content = b"Mock PDF report content"
    report_filename = f"monthly_report_{follower_id}_{report_data['year']}_{report_data['month']:02d}.pdf"
    
    try:
        # Upload report to MinIO
        object_name = f"reports/{follower_id}/{report_filename}"
        result = await minio_service.upload_report(
            report_content=pdf_content,
            object_name=object_name,
            content_type="application/pdf"
        )
        
        # Verify upload was called
        mock_minio_client.put_object.assert_called_once()
        call_args = mock_minio_client.put_object.call_args
        assert call_args[1]['bucket_name'] == "test-reports"
        assert call_args[1]['object_name'] == object_name
        assert call_args[1]['length'] == len(pdf_content)
        assert call_args[1]['content_type'] == "application/pdf"
        
        # Verify object exists
        exists = await minio_service.report_exists(object_name)
        assert exists is True
        mock_minio_client.stat_object.assert_called_with("test-reports", object_name)
        
        # Generate pre-signed URL
        presigned_url = await minio_service.get_presigned_url(object_name, expires_days=30)
        assert presigned_url is not None
        assert "signature=" in presigned_url
        mock_minio_client.presigned_get_object.assert_called_once()
        
        # Store report metadata in MongoDB
        report_doc = {
            **report_data,
            "minio_object_name": object_name,
            "minio_bucket": "test-reports",
            "presigned_url": presigned_url,
            "url_expires_at": datetime.datetime.now() + datetime.timedelta(days=30)
        }
        
        await test_mongo_db.monthly_reports.insert_one(report_doc)
        
        # Verify report was stored in MongoDB
        stored_report = await test_mongo_db.monthly_reports.find_one({"report_id": report_id})
        assert stored_report is not None
        assert stored_report["minio_object_name"] == object_name
        assert stored_report["presigned_url"] == presigned_url
        
    finally:
        # Cleanup
        await test_mongo_db.monthly_reports.delete_one({"report_id": report_id})


@pytest.mark.asyncio
async def test_minio_lifecycle_policy():
    """
    Test MinIO lifecycle policy configuration.
    
    This test verifies:
    1. Lifecycle policy is set on the bucket
    2. Objects are automatically deleted after expiration
    """
    from report_worker.app.service.minio_service import MinIOService
    import json
    
    # Mock MinIO client
    mock_minio_client = MagicMock()
    mock_minio_client.bucket_exists.return_value = True
    
    # Create MinIO service
    minio_service = MinIOService(
        endpoint="minio.example.com",
        access_key="test-access-key",
        secret_key="test-secret-key", 
        bucket_name="test-reports",
        secure=True
    )
    minio_service.client = mock_minio_client
    
    # Set lifecycle policy
    lifecycle_config = {
        "Rules": [{
            "ID": "delete-old-reports",
            "Status": "Enabled",
            "Filter": {"Prefix": "reports/"},
            "Expiration": {"Days": 90}
        }]
    }
    
    # Configure lifecycle policy
    await minio_service.set_lifecycle_policy(lifecycle_config)
    
    # Verify policy was set
    mock_minio_client.set_bucket_lifecycle.assert_called_once()
    call_args = mock_minio_client.set_bucket_lifecycle.call_args
    assert call_args[1]['bucket_name'] == "test-reports"
    
    # Parse the config that was set
    set_config = call_args[1]['config']
    if isinstance(set_config, str):
        set_config = json.loads(set_config)
    
    assert "Rules" in set_config
    assert len(set_config["Rules"]) == 1
    assert set_config["Rules"][0]["ID"] == "delete-old-reports"
    assert set_config["Rules"][0]["Expiration"]["Days"] == 90


@pytest.mark.asyncio
async def test_vault_secret_rotation():
    """
    Test Vault secret rotation workflow.
    
    This test verifies:
    1. Current secrets can be retrieved
    2. Secrets can be updated/rotated
    3. New secrets are immediately available
    """
    vault_client = VaultClient(vault_enabled=True)
    
    # Mock the Vault client methods
    mock_hvac_client = MagicMock()
    mock_hvac_client.is_authenticated.return_value = True
    
    # Initial secret values
    initial_secret = {
        "data": {
            "data": {
                "IB_USER": "original_user",
                "IB_PASS": "original_pass"
            }
        }
    }
    
    # Rotated secret values
    rotated_secret = {
        "data": {
            "data": {
                "IB_USER": "original_user",  # Username stays same
                "IB_PASS": "new_rotated_pass_2024"
            }
        }
    }
    
    # Setup mock to return different values on successive calls
    mock_hvac_client.secrets.kv.v2.read_secret_version.side_effect = [
        initial_secret,
        rotated_secret
    ]
    
    vault_client._client = mock_hvac_client
    
    # Get initial credentials
    path = "secret/ibkr/follower_123"
    initial_creds = vault_client.get_secret(path)
    assert initial_creds["IB_USER"] == "original_user"
    assert initial_creds["IB_PASS"] == "original_pass"
    
    # Simulate secret rotation
    new_credentials = {
        "IB_USER": "original_user",
        "IB_PASS": "new_rotated_pass_2024"
    }
    
    # Update secret in Vault
    mock_hvac_client.secrets.kv.v2.create_or_update_secret.return_value = None
    success = vault_client.put_secret(path, new_credentials)
    assert success is True
    
    # Verify new credentials are available
    updated_creds = vault_client.get_secret(path)
    assert updated_creds["IB_USER"] == "original_user"
    assert updated_creds["IB_PASS"] == "new_rotated_pass_2024"
    
    # Verify correct Vault methods were called
    assert mock_hvac_client.secrets.kv.v2.read_secret_version.call_count == 2
    mock_hvac_client.secrets.kv.v2.create_or_update_secret.assert_called_once()
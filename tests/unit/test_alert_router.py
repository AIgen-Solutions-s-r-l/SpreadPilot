"""Unit tests for Alert Router service."""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis import aioredis as fakeredis
from httpx import Response

from spreadpilot_core.models.alert import Alert, AlertSeverity


@pytest.fixture
async def fake_redis():
    """Create a fake Redis client for testing."""
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    await client.close()


@pytest.fixture
def mock_alert():
    """Create a mock alert for testing."""
    return Alert(
        follower_id="test_follower_123",
        reason="Test alert reason",
        severity=AlertSeverity.CRITICAL,
        service="test_service",
        timestamp=time.time()
    )


@pytest.fixture
async def alert_router():
    """Create an alert router instance for testing."""
    # Import here to avoid issues
    from alert_router.app.alert_router import AlertRouter
    
    router = AlertRouter()
    # Override config for testing
    router.config.telegram_bot_token = "test_bot_token"
    router.config.telegram_chat_id = "test_chat_id"
    router.config.smtp_uri = "smtp://user:pass@smtp.test.com:587"
    router.config.email_from = "alerts@test.com"
    router.config.email_to = "admin@test.com"
    
    yield router


class TestAlertRouter:
    """Test suite for Alert Router."""
    
    @pytest.mark.asyncio
    async def test_redis_stream_subscription(self, alert_router, fake_redis, mock_alert):
        """Test that alert router subscribes to Redis stream and processes messages."""
        # Setup
        alert_router.redis_client = fake_redis
        
        # Mock MongoDB
        mock_mongo_db = MagicMock()
        mock_collection = AsyncMock()
        mock_mongo_db.__getitem__.return_value = mock_collection
        alert_router.mongo_db = mock_mongo_db
        
        # Mock HTTP client
        mock_httpx = AsyncMock()
        alert_router.httpx_client = mock_httpx
        
        # Create consumer group
        await fake_redis.xgroup_create("alerts", "alert-router", id="0")
        
        # Add alert to stream
        alert_data = {"data": mock_alert.model_dump_json()}
        msg_id = await fake_redis.xadd("alerts", alert_data)
        
        # Mock process methods
        with patch.object(alert_router, "_send_telegram_with_retry", new_callable=AsyncMock) as mock_telegram:
            with patch.object(alert_router, "_send_email_with_retry", new_callable=AsyncMock) as mock_email:
                # Process one iteration
                alert_router._running = True
                
                # Read and process message
                messages = await fake_redis.xreadgroup(
                    "alert-router",
                    "consumer-1",
                    {"alerts": ">"},
                    count=1
                )
                
                assert len(messages) > 0
                for stream_name, stream_messages in messages:
                    for msg_id, data in stream_messages:
                        await alert_router._process_single_alert(msg_id, data)
                
                # Verify methods were called
                mock_telegram.assert_called_once()
                mock_email.assert_called_once()
                mock_collection.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_telegram_notification_with_retry(self, alert_router, mock_alert):
        """Test Telegram notification with retry on failure."""
        # Mock HTTP client
        mock_httpx = AsyncMock()
        alert_router.httpx_client = mock_httpx
        
        # First two calls fail, third succeeds
        mock_response_fail = MagicMock(spec=Response)
        mock_response_fail.raise_for_status.side_effect = Exception("Network error")
        
        mock_response_success = MagicMock(spec=Response)
        mock_response_success.raise_for_status.return_value = None
        
        mock_httpx.post.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success
        ]
        
        # Send alert
        await alert_router._send_telegram_with_retry(mock_alert)
        
        # Verify retries
        assert mock_httpx.post.call_count == 3
        
        # Check message format
        call_args = mock_httpx.post.call_args_list[0]
        assert "https://api.telegram.org/bot" in call_args[0][0]
        json_data = call_args[1]["json"]
        assert json_data["chat_id"] == "test_chat_id"
        assert "SpreadPilot Alert" in json_data["text"]
        assert mock_alert.reason in json_data["text"]
    
    @pytest.mark.asyncio
    async def test_email_notification_with_retry(self, alert_router, mock_alert):
        """Test email notification with retry on failure."""
        # Mock aiosmtplib
        with patch("alert_router.app.alert_router.aiosmtplib") as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.SMTP.return_value.__aenter__.return_value = mock_smtp_instance
            
            # First two calls fail, third succeeds
            mock_smtp_instance.send_message.side_effect = [
                Exception("SMTP error"),
                Exception("Connection timeout"),
                None  # Success
            ]
            
            # Send alert
            await alert_router._send_email_with_retry(mock_alert)
            
            # Verify retries
            assert mock_smtp_instance.send_message.call_count == 3
            
            # Check email content
            call_args = mock_smtp_instance.send_message.call_args_list[0]
            email_msg = call_args[0][0]
            assert alert_router.config.email_from in str(email_msg["From"])
            assert alert_router.config.email_to in str(email_msg["To"])
            assert "SpreadPilot Alert" in str(email_msg["Subject"])
    
    @pytest.mark.asyncio
    async def test_failed_alert_status_in_mongo(self, alert_router, mock_alert):
        """Test that failed alerts are properly logged to MongoDB."""
        # Mock MongoDB
        mock_mongo_db = MagicMock()
        mock_collection = AsyncMock()
        mock_mongo_db.__getitem__.return_value = mock_collection
        alert_router.mongo_db = mock_mongo_db
        
        # Log failed alert
        await alert_router._log_alert_to_mongo(
            alert=mock_alert,
            msg_id="test_msg_id",
            success=False,
            telegram_sent=False,
            email_sent=False
        )
        
        # Verify MongoDB insert
        mock_collection.insert_one.assert_called_once()
        insert_data = mock_collection.insert_one.call_args[0][0]
        assert insert_data["status"] == "failed"
        assert insert_data["success"] is False
        assert insert_data["channels"]["telegram"] is False
        assert insert_data["channels"]["email"] is False
    
    @pytest.mark.asyncio
    async def test_vault_secret_loading(self, alert_router):
        """Test loading secrets from Vault."""
        alert_router.config.vault_enabled = True
        alert_router.config.telegram_bot_token = None
        alert_router.config.smtp_uri = None
        
        with patch("alert_router.app.alert_router.get_vault_client") as mock_vault:
            mock_vault_client = MagicMock()
            mock_vault.return_value = mock_vault_client
            
            # Mock Vault responses
            mock_vault_client.get_secret.side_effect = [
                {"token": "vault_bot_token", "chat_id": "vault_chat_id"},  # Telegram
                {"uri": "smtp://vault:pass@smtp.vault.com:587", "from": "vault@test.com"}  # SMTP
            ]
            
            # Load secrets
            await alert_router._load_vault_secrets()
            
            # Verify secrets were loaded
            assert alert_router.config.telegram_bot_token == "vault_bot_token"
            assert alert_router.config.telegram_chat_id == "vault_chat_id"
            assert alert_router.config.smtp_uri == "smtp://vault:pass@smtp.vault.com:587"
            assert alert_router.config.email_from == "vault@test.com"
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test the health check endpoint."""
        from alert_router.app.alert_router import app
        from fastapi.testclient import TestClient
        
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "alert-router"
            assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_consumer_group_creation(self, alert_router, fake_redis):
        """Test that consumer group is created if it doesn't exist."""
        alert_router.redis_client = fake_redis
        
        # Mock other dependencies
        alert_router.mongo_client = MagicMock()
        alert_router.mongo_db = MagicMock()
        alert_router.httpx_client = AsyncMock()
        
        # Start router (which should create consumer group)
        with patch.object(alert_router, "_process_alerts", new_callable=AsyncMock):
            await alert_router.start()
        
        # Verify consumer group exists
        groups = await fake_redis.xinfo_groups("alerts")
        assert any(g["name"] == alert_router.config.redis_consumer_group for g in groups)
    
    @pytest.mark.asyncio
    async def test_final_failure_after_retries(self, alert_router, mock_alert):
        """Test that final failure is handled after all retries are exhausted."""
        # Mock HTTP client to always fail
        mock_httpx = AsyncMock()
        alert_router.httpx_client = mock_httpx
        
        mock_response = MagicMock(spec=Response)
        mock_response.raise_for_status.side_effect = Exception("Permanent failure")
        mock_httpx.post.return_value = mock_response
        
        # Mock MongoDB
        mock_mongo_db = MagicMock()
        mock_collection = AsyncMock()
        mock_mongo_db.__getitem__.return_value = mock_collection
        alert_router.mongo_db = mock_mongo_db
        
        # Process alert (should fail after retries)
        alert_data = {"data": mock_alert.model_dump_json()}
        
        # This should not raise, but log the failure
        await alert_router._process_single_alert("msg_123", alert_data)
        
        # Verify failure was logged to MongoDB
        mock_collection.insert_one.assert_called_once()
        insert_data = mock_collection.insert_one.call_args[0][0]
        assert insert_data["status"] == "failed"
        assert insert_data["success"] is False
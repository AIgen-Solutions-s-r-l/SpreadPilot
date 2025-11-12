"""Unit tests for alert router with httpx_mock and fakeredis."""

import asyncio
import json
import time
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import httpx
import pytest
from alert_router.app.alert_router import AlertRouter, AlertRouterConfig
from httpx_mock import HTTPXMock
from spreadpilot_core.models.alert import Alert, AlertSeverity


@pytest.fixture
async def fake_redis():
    """Create a fake Redis client."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def alert_config():
    """Create test alert router configuration."""
    return AlertRouterConfig(
        redis_url="redis://fake",
        telegram_bot_token="test_bot_token",
        telegram_chat_id="test_chat_id",
        smtp_uri="smtp://testuser:testpass@smtp.test.com:587",
        email_from="test@example.com",
        email_to="admin@example.com",
        mongo_uri="mongodb://fake",
        vault_enabled=False,
    )


@pytest.fixture
async def mock_router(alert_config, fake_redis):
    """Create a mock alert router for testing."""
    router = AlertRouter()
    router.config = alert_config
    router.redis_client = fake_redis
    router.mongo_db = AsyncMock()
    router.httpx_client = AsyncMock(spec=httpx.AsyncClient)
    router._running = True
    return router


@pytest.fixture
def test_alert():
    """Create a test alert."""
    return Alert(
        follower_id="test_follower",
        reason="Test alert reason",
        severity=AlertSeverity.CRITICAL,
        service="test_service",
        timestamp=time.time(),
    )


class TestAlertRouter:
    """Test alert router functionality."""

    @pytest.mark.asyncio
    async def test_telegram_message_sent(self, mock_router, test_alert):
        """Test that Telegram messages are sent correctly."""
        with HTTPXMock() as httpx_mock:
            # Mock Telegram API response
            httpx_mock.add_response(
                method="POST",
                url=f"https://api.telegram.org/bot{mock_router.config.telegram_bot_token}/sendMessage",
                json={"ok": True, "result": {"message_id": 123}},
                status_code=200,
            )

            # Create real httpx client for this test
            mock_router.httpx_client = httpx.AsyncClient()

            try:
                # Send Telegram alert
                await mock_router._send_telegram_with_retry(test_alert)

                # Verify the request was made
                requests = httpx_mock.get_requests()
                assert len(requests) == 1

                request = requests[0]
                assert request.method == "POST"
                assert f"bot{mock_router.config.telegram_bot_token}" in str(request.url)

                # Check request payload
                payload = json.loads(request.content)
                assert payload["chat_id"] == mock_router.config.telegram_chat_id
                assert "SpreadPilot Alert" in payload["text"]
                assert test_alert.reason in payload["text"]
                assert test_alert.severity.value in payload["text"]

            finally:
                await mock_router.httpx_client.aclose()

    @pytest.mark.asyncio
    async def test_telegram_retry_on_failure(self, mock_router, test_alert):
        """Test that Telegram sending retries on failure."""
        with HTTPXMock() as httpx_mock:
            # Mock failed responses (first 2 fail, 3rd succeeds)
            httpx_mock.add_response(
                method="POST",
                url=f"https://api.telegram.org/bot{mock_router.config.telegram_bot_token}/sendMessage",
                status_code=500,
            )
            httpx_mock.add_response(
                method="POST",
                url=f"https://api.telegram.org/bot{mock_router.config.telegram_bot_token}/sendMessage",
                status_code=500,
            )
            httpx_mock.add_response(
                method="POST",
                url=f"https://api.telegram.org/bot{mock_router.config.telegram_bot_token}/sendMessage",
                json={"ok": True, "result": {"message_id": 123}},
                status_code=200,
            )

            mock_router.httpx_client = httpx.AsyncClient()

            try:
                # Should succeed on 3rd attempt
                await mock_router._send_telegram_with_retry(test_alert)

                # Verify 3 requests were made
                requests = httpx_mock.get_requests()
                assert len(requests) == 3

            finally:
                await mock_router.httpx_client.aclose()

    @pytest.mark.asyncio
    async def test_telegram_max_retries_exceeded(self, mock_router, test_alert):
        """Test that Telegram sending fails after max retries."""
        with HTTPXMock() as httpx_mock:
            # Mock all responses as failures
            for _ in range(5):  # More than max_tries=3
                httpx_mock.add_response(
                    method="POST",
                    url=f"https://api.telegram.org/bot{mock_router.config.telegram_bot_token}/sendMessage",
                    status_code=500,
                )

            mock_router.httpx_client = httpx.AsyncClient()

            try:
                # Should raise exception after 3 attempts
                with pytest.raises(httpx.HTTPStatusError):
                    await mock_router._send_telegram_with_retry(test_alert)

                # Verify exactly 3 attempts were made
                requests = httpx_mock.get_requests()
                assert len(requests) == 3

            finally:
                await mock_router.httpx_client.aclose()

    @pytest.mark.asyncio
    async def test_email_sending(self, mock_router, test_alert):
        """Test email sending functionality."""
        # Mock aiosmtplib
        with patch("alert_router.app.alert_router.aiosmtplib.SMTP") as mock_smtp:
            smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = smtp_instance

            await mock_router._send_email_with_retry(test_alert)

            # Verify SMTP connection was created
            mock_smtp.assert_called_once_with(hostname="smtp.test.com", port=587, start_tls=True)

            # Verify login was called
            smtp_instance.login.assert_called_once_with("testuser", "testpass")

            # Verify message was sent
            smtp_instance.send_message.assert_called_once()

            # Check message content
            sent_message = smtp_instance.send_message.call_args[0][0]
            assert sent_message["Subject"].startswith("SpreadPilot Alert: CRITICAL")
            assert test_alert.reason in str(sent_message)

    @pytest.mark.asyncio
    async def test_email_retry_on_failure(self, mock_router, test_alert):
        """Test email retry on SMTP failure."""
        with patch("alert_router.app.alert_router.aiosmtplib.SMTP") as mock_smtp:
            smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = smtp_instance

            # First two attempts fail, third succeeds
            smtp_instance.send_message.side_effect = [
                Exception("SMTP Error 1"),
                Exception("SMTP Error 2"),
                None,  # Success
            ]

            await mock_router._send_email_with_retry(test_alert)

            # Verify 3 attempts were made
            assert smtp_instance.send_message.call_count == 3

    @pytest.mark.asyncio
    async def test_redis_stream_processing(self, mock_router, test_alert, fake_redis):
        """Test Redis stream message processing."""
        # Add alert to Redis stream
        alert_data = {"data": test_alert.model_dump_json()}
        message_id = await fake_redis.xadd("alerts", alert_data)

        # Create consumer group
        await fake_redis.xgroup_create("alerts", "alert-router", id="0", mkstream=True)

        # Mock the routing methods
        mock_router._send_telegram_with_retry = AsyncMock()
        mock_router._send_email_with_retry = AsyncMock()
        mock_router._log_alert_to_mongo = AsyncMock()

        # Process the message
        await mock_router._process_single_alert(message_id, alert_data)

        # Verify routing methods were called
        mock_router._send_telegram_with_retry.assert_called_once_with(test_alert)
        mock_router._send_email_with_retry.assert_called_once_with(test_alert)
        mock_router._log_alert_to_mongo.assert_called_once()

        # Check log call arguments
        log_call = mock_router._log_alert_to_mongo.call_args
        assert log_call[0][0] == test_alert  # alert
        assert log_call[0][1] == message_id  # msg_id
        assert log_call[1]["success"] is True
        assert log_call[1]["telegram_sent"] is True
        assert log_call[1]["email_sent"] is True

    @pytest.mark.asyncio
    async def test_mongo_logging(self, mock_router, test_alert):
        """Test MongoDB alert logging."""
        await mock_router._log_alert_to_mongo(
            test_alert, "test_msg_id", success=True, telegram_sent=True, email_sent=False
        )

        # Verify MongoDB insert was called
        mock_router.mongo_db.__getitem__.assert_called_with("alert_history")
        collection = mock_router.mongo_db["alert_history"]
        collection.insert_one.assert_called_once()

        # Check inserted document
        inserted_doc = collection.insert_one.call_args[0][0]
        assert inserted_doc["msg_id"] == "test_msg_id"
        assert inserted_doc["alert"] == test_alert.model_dump()
        assert inserted_doc["success"] is True
        assert inserted_doc["channels"]["telegram"] is True
        assert inserted_doc["channels"]["email"] is False
        assert inserted_doc["status"] == "completed"

    @pytest.mark.asyncio
    async def test_alert_severity_emojis(self, mock_router):
        """Test that different alert severities use correct emojis."""
        test_cases = [
            (AlertSeverity.INFO, "ℹ️"),
            (AlertSeverity.WARNING, "⚠️"),
            (AlertSeverity.CRITICAL, "🚨"),
            (AlertSeverity.ERROR, "❌"),
        ]

        with HTTPXMock() as httpx_mock:
            # Mock successful responses for all severities
            for _ in test_cases:
                httpx_mock.add_response(
                    method="POST",
                    url=f"https://api.telegram.org/bot{mock_router.config.telegram_bot_token}/sendMessage",
                    json={"ok": True, "result": {"message_id": 123}},
                    status_code=200,
                )

            mock_router.httpx_client = httpx.AsyncClient()

            try:
                for severity, expected_emoji in test_cases:
                    alert = Alert(
                        follower_id="test",
                        reason="Test",
                        severity=severity,
                        service="test",
                        timestamp=time.time(),
                    )

                    await mock_router._send_telegram_with_retry(alert)

                # Check that correct emojis were used
                requests = httpx_mock.get_requests()
                for i, (severity, expected_emoji) in enumerate(test_cases):
                    payload = json.loads(requests[i].content)
                    assert expected_emoji in payload["text"]

            finally:
                await mock_router.httpx_client.aclose()

    @pytest.mark.asyncio
    async def test_partial_delivery_failure(self, mock_router, test_alert):
        """Test handling when one delivery method fails but other succeeds."""
        # Mock Telegram success, email failure
        with HTTPXMock() as httpx_mock:
            httpx_mock.add_response(
                method="POST",
                url=f"https://api.telegram.org/bot{mock_router.config.telegram_bot_token}/sendMessage",
                json={"ok": True, "result": {"message_id": 123}},
                status_code=200,
            )

            mock_router.httpx_client = httpx.AsyncClient()

            with patch("alert_router.app.alert_router.aiosmtplib.SMTP") as mock_smtp:
                smtp_instance = AsyncMock()
                mock_smtp.return_value.__aenter__.return_value = smtp_instance
                smtp_instance.send_message.side_effect = Exception("SMTP Failed")

                mock_router._log_alert_to_mongo = AsyncMock()

                try:
                    # Process alert data
                    alert_data = {"data": test_alert.model_dump_json()}
                    await mock_router._process_single_alert("test_id", alert_data)

                    # Verify logging shows partial success
                    log_call = mock_router._log_alert_to_mongo.call_args
                    assert log_call[1]["success"] is False  # Overall failed due to email
                    assert log_call[1]["telegram_sent"] is True
                    assert log_call[1]["email_sent"] is False

                finally:
                    await mock_router.httpx_client.aclose()


class TestAlertRouterIntegration:
    """Integration tests for alert router."""

    @pytest.mark.asyncio
    async def test_full_alert_flow(self, fake_redis):
        """Test complete alert processing flow."""
        # Create router with fake dependencies
        router = AlertRouter()
        router.config = AlertRouterConfig(
            redis_url="redis://fake",
            telegram_bot_token="test_token",
            telegram_chat_id="test_chat",
            smtp_uri="smtp://user:pass@smtp.test.com:587",
            vault_enabled=False,
        )
        router.redis_client = fake_redis
        router.mongo_db = AsyncMock()
        router.httpx_client = AsyncMock()
        router._running = True

        # Create consumer group
        await fake_redis.xgroup_create("alerts", "alert-router", id="0", mkstream=True)

        # Mock delivery methods
        router._send_telegram_with_retry = AsyncMock()
        router._send_email_with_retry = AsyncMock()
        router._log_alert_to_mongo = AsyncMock()

        # Add test alert to stream
        test_alert = Alert(
            follower_id="integration_test",
            reason="Integration test alert",
            severity=AlertSeverity.WARNING,
            service="test",
            timestamp=time.time(),
        )

        alert_data = {"data": test_alert.model_dump_json()}
        message_id = await fake_redis.xadd("alerts", alert_data)

        # Process one round of alerts
        messages = await fake_redis.xreadgroup(
            "alert-router", "test-consumer", {"alerts": ">"}, count=10, block=100  # Short block
        )

        # Process the message
        for stream_name, stream_messages in messages:
            for msg_id, data in stream_messages:
                await router._process_single_alert(msg_id, data)
                await fake_redis.xack("alerts", "alert-router", msg_id)

        # Verify all methods were called
        router._send_telegram_with_retry.assert_called_once()
        router._send_email_with_retry.assert_called_once()
        router._log_alert_to_mongo.assert_called_once()

        # Verify message was acknowledged
        pending = await fake_redis.xpending("alerts", "alert-router")
        assert pending["pending"] == 0  # No pending messages

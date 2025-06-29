"""Unit tests for Redis alert subscriber."""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from app.service.redis_subscriber import RedisAlertSubscriber

from spreadpilot_core.models.alert import AlertEvent, AlertType


@pytest.fixture
def sample_alert_event():
    """Create a sample alert event for testing."""
    return AlertEvent(
        event_type=AlertType.COMPONENT_DOWN,
        timestamp=datetime(2025, 6, 28, 12, 0, 0),
        message="Trading Bot is not responding",
        params={
            "component_name": "trading-bot",
            "last_heartbeat": "2025-06-28T11:45:00Z",
            "attempts": 3,
        },
    )


@pytest.fixture
def redis_subscriber():
    """Create a Redis subscriber instance."""
    return RedisAlertSubscriber(
        redis_url="redis://localhost:6379",
        stream_key="test-alerts",
        consumer_group="test-group",
        consumer_name="test-consumer",
    )


class TestRedisAlertSubscriber:
    """Test cases for RedisAlertSubscriber."""

    @pytest.mark.asyncio
    async def test_connect_creates_consumer_group(self, redis_subscriber):
        """Test that connect creates consumer group if it doesn't exist."""
        mock_redis = AsyncMock()
        mock_redis.xgroup_create = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            await redis_subscriber.connect()

        mock_redis.xgroup_create.assert_called_once_with(
            "test-alerts", "test-group", id="0-0", mkstream=True
        )
        assert redis_subscriber.redis_client == mock_redis

    @pytest.mark.asyncio
    async def test_connect_handles_existing_group(self, redis_subscriber):
        """Test that connect handles BUSYGROUP error for existing groups."""
        mock_redis = AsyncMock()
        import redis

        mock_redis.xgroup_create = AsyncMock(
            side_effect=redis.ResponseError(
                "BUSYGROUP Consumer Group name already exists"
            )
        )

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            await redis_subscriber.connect()

        # Should not raise exception
        assert redis_subscriber.redis_client == mock_redis

    @pytest.mark.asyncio
    async def test_disconnect(self, redis_subscriber):
        """Test Redis disconnect."""
        mock_redis = AsyncMock()
        redis_subscriber.redis_client = mock_redis

        await redis_subscriber.disconnect()

        mock_redis.close.assert_called_once()
        assert redis_subscriber.redis_client is None

    @pytest.mark.asyncio
    async def test_process_message_success(self, redis_subscriber, sample_alert_event):
        """Test successful message processing."""
        # Prepare message data
        alert_data = {
            "event_type": sample_alert_event.event_type.value,
            "timestamp": sample_alert_event.timestamp.isoformat(),
            "message": sample_alert_event.message,
            "params": sample_alert_event.params,
        }
        message_data = {"alert": json.dumps(alert_data)}

        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.xack = AsyncMock()
        redis_subscriber.redis_client = mock_redis

        # Mock BackoffAlertRouter with context manager support
        mock_router = AsyncMock()
        mock_router.route_alert_with_backoff = AsyncMock()
        mock_router.__aenter__ = AsyncMock(return_value=mock_router)
        mock_router.__aexit__ = AsyncMock()

        with patch(
            "app.service.redis_subscriber.BackoffAlertRouter", return_value=mock_router
        ):
            result = await redis_subscriber.process_message("1234-0", message_data)

        assert result is True
        mock_router.route_alert_with_backoff.assert_called_once()
        mock_redis.xack.assert_called_once_with("test-alerts", "test-group", "1234-0")

    @pytest.mark.asyncio
    async def test_process_message_invalid_json(self, redis_subscriber):
        """Test message processing with invalid JSON."""
        message_data = {"alert": "invalid-json"}

        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.xack = AsyncMock()
        redis_subscriber.redis_client = mock_redis

        result = await redis_subscriber.process_message("1234-0", message_data)

        assert result is False
        # Should still acknowledge bad message
        mock_redis.xack.assert_called_once_with("test-alerts", "test-group", "1234-0")

    @pytest.mark.asyncio
    async def test_process_message_routing_failure(
        self, redis_subscriber, sample_alert_event
    ):
        """Test message processing when routing fails."""
        # Prepare message data
        alert_data = {
            "event_type": sample_alert_event.event_type.value,
            "timestamp": sample_alert_event.timestamp.isoformat(),
            "message": sample_alert_event.message,
            "params": sample_alert_event.params,
        }
        message_data = {"alert": json.dumps(alert_data)}

        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.xack = AsyncMock()
        redis_subscriber.redis_client = mock_redis

        # Mock BackoffAlertRouter to fail with context manager support
        mock_router = AsyncMock()
        mock_router.route_alert_with_backoff = AsyncMock(
            side_effect=Exception("Routing failed")
        )
        mock_router.__aenter__ = AsyncMock(return_value=mock_router)
        mock_router.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.service.redis_subscriber.BackoffAlertRouter", return_value=mock_router
        ):
            result = await redis_subscriber.process_message("1234-0", message_data)

        assert result is False
        # Should NOT acknowledge failed message
        mock_redis.xack.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_processes_messages(self, redis_subscriber):
        """Test that run() processes messages from Redis stream."""
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.xreadgroup = AsyncMock()

        # Simulate receiving one message then stopping
        message_data = {
            "alert": json.dumps(
                {
                    "event_type": "COMPONENT_DOWN",
                    "timestamp": "2025-06-28T12:00:00",
                    "message": "Test message",
                    "params": {},
                }
            )
        }

        mock_redis.xreadgroup.side_effect = [
            # First call returns a message
            [("test-alerts", [("1234-0", message_data)])],
            # Second call triggers stop
            asyncio.CancelledError(),
        ]

        mock_redis.xack = AsyncMock()

        # Mock BackoffAlertRouter with context manager support
        mock_router = AsyncMock()
        mock_router.route_alert_with_backoff = AsyncMock()
        mock_router.__aenter__ = AsyncMock(return_value=mock_router)
        mock_router.__aexit__ = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            with patch(
                "app.service.redis_subscriber.BackoffAlertRouter",
                return_value=mock_router,
            ):
                redis_subscriber._running = True

                # Run subscriber until cancelled
                try:
                    await redis_subscriber.run()
                except asyncio.CancelledError:
                    pass  # Expected

        # Verify message was processed
        mock_redis.xreadgroup.assert_called()
        mock_router.route_alert_with_backoff.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_handles_errors(self, redis_subscriber):
        """Test that run() handles errors gracefully."""
        # Mock Redis client
        mock_redis = AsyncMock()

        # Simulate error then stop
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Redis connection error")
            else:
                redis_subscriber._running = False
                return []

        mock_redis.xreadgroup = AsyncMock(side_effect=side_effect)

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await redis_subscriber.run()

        # Should have slept after error
        mock_sleep.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_stop(self, redis_subscriber):
        """Test stopping the subscriber."""
        redis_subscriber._running = True

        await redis_subscriber.stop()

        assert redis_subscriber._running is False

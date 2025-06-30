"""
Integration tests for watchdog Redis alert publishing
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fakeredis import aioredis as fakeredis
from watchdog import ServiceWatchdog

from spreadpilot_core.models.alert import Alert, AlertSeverity


@pytest.fixture
async def fake_redis():
    """Create a fake Redis client for testing."""
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    await client.close()


@pytest.fixture
async def watchdog_with_redis(fake_redis):
    """Create a ServiceWatchdog instance with fake Redis."""
    watchdog = ServiceWatchdog()
    watchdog.redis_client = fake_redis
    watchdog.http_client = AsyncMock()
    watchdog.mongo_db = None  # Skip MongoDB for these tests
    yield watchdog


class TestWatchdogRedisAlerts:
    """Test suite for watchdog Redis alert publishing."""

    @pytest.mark.asyncio
    async def test_publish_recovery_alert(self, watchdog_with_redis, fake_redis):
        """Test publishing a recovery alert to Redis."""
        await watchdog_with_redis.publish_alert("trading_bot", "recovery", True)

        # Check alert was published to Redis
        messages = await fake_redis.xrange("alerts")
        assert len(messages) == 1

        # Parse and verify alert
        msg_id, data = messages[0]
        alert_json = data["data"]
        alert = Alert.model_validate_json(alert_json)

        assert alert.service == "watchdog"
        assert alert.follower_id == "system"
        assert "RECOVERED" in alert.reason
        assert "Trading Bot" in alert.reason
        assert alert.severity == AlertSeverity.INFO
        assert alert.details["component_name"] == "trading_bot"
        assert alert.details["action"] == "recovery"
        assert alert.details["success"] is True

    @pytest.mark.asyncio
    async def test_publish_restart_success_alert(self, watchdog_with_redis, fake_redis):
        """Test publishing a successful restart alert."""
        # Set failure count to simulate prior failures
        watchdog_with_redis.failure_counts["admin_api"] = 3

        await watchdog_with_redis.publish_alert("admin_api", "restart", True)

        messages = await fake_redis.xrange("alerts")
        assert len(messages) == 1

        msg_id, data = messages[0]
        alert = Alert.model_validate_json(data["data"])

        assert alert.severity == AlertSeverity.WARNING
        assert "RESTARTED" in alert.reason
        assert "Admin API" in alert.reason
        assert alert.details["consecutive_failures"] == 3
        assert alert.details["success"] is True

    @pytest.mark.asyncio
    async def test_publish_restart_failure_alert(self, watchdog_with_redis, fake_redis):
        """Test publishing a failed restart alert."""
        watchdog_with_redis.failure_counts["report_worker"] = 3

        await watchdog_with_redis.publish_alert("report_worker", "restart", False)

        messages = await fake_redis.xrange("alerts")
        assert len(messages) == 1

        msg_id, data = messages[0]
        alert = Alert.model_validate_json(data["data"])

        assert alert.severity == AlertSeverity.CRITICAL
        assert "RESTART_FAILED" in alert.reason
        assert "Report Worker" in alert.reason
        assert alert.details["success"] is False

    @pytest.mark.asyncio
    async def test_monitor_service_publishes_alerts(self, watchdog_with_redis, fake_redis):
        """Test that monitor_service publishes alerts via Redis."""
        # Mock unhealthy service that triggers restart
        watchdog_with_redis.check_service_health = AsyncMock(return_value=False)
        watchdog_with_redis.restart_service = Mock(return_value=True)
        watchdog_with_redis.failure_counts["frontend"] = 2  # One below threshold

        # Monitor service (should trigger restart)
        await watchdog_with_redis.monitor_service("frontend")

        # Check alert was published
        messages = await fake_redis.xrange("alerts")
        assert len(messages) == 1

        alert = Alert.model_validate_json(messages[0][1]["data"])
        assert alert.severity == AlertSeverity.WARNING
        assert "RESTARTED" in alert.reason

    @pytest.mark.asyncio
    async def test_multiple_alerts_published(self, watchdog_with_redis, fake_redis):
        """Test publishing multiple alerts."""
        # Publish several different alerts
        await watchdog_with_redis.publish_alert("trading_bot", "recovery", True)
        await watchdog_with_redis.publish_alert("admin_api", "restart", False)
        await watchdog_with_redis.publish_alert("report_worker", "restart", True)

        # Check all alerts were published
        messages = await fake_redis.xrange("alerts")
        assert len(messages) == 3

        # Verify each alert
        alerts = [Alert.model_validate_json(msg[1]["data"]) for msg in messages]

        # Recovery alert
        recovery_alert = next(a for a in alerts if "RECOVERED" in a.reason)
        assert recovery_alert.severity == AlertSeverity.INFO

        # Failed restart alert
        failed_alert = next(a for a in alerts if "RESTART_FAILED" in a.reason)
        assert failed_alert.severity == AlertSeverity.CRITICAL

        # Successful restart alert
        success_alert = next(a for a in alerts if "RESTARTED" in a.reason and a.details["success"])
        assert success_alert.severity == AlertSeverity.WARNING

    @pytest.mark.asyncio
    async def test_alert_contains_health_url(self, watchdog_with_redis, fake_redis):
        """Test that alerts contain the health URL for debugging."""
        await watchdog_with_redis.publish_alert("trading_bot", "restart", False)

        messages = await fake_redis.xrange("alerts")
        alert = Alert.model_validate_json(messages[0][1]["data"])

        assert "health_url" in alert.details
        assert alert.details["health_url"] == "http://trading-bot:8080/health"

    @pytest.mark.asyncio
    async def test_redis_connection_error_handled(self, watchdog_with_redis):
        """Test that Redis connection errors are handled gracefully."""
        # Mock Redis to raise an exception
        watchdog_with_redis.redis_client.xadd = AsyncMock(
            side_effect=Exception("Redis connection error")
        )

        # Should not raise exception
        await watchdog_with_redis.publish_alert("trading_bot", "restart", True)

        # Verify error was logged (in real implementation)
        watchdog_with_redis.redis_client.xadd.assert_called_once()

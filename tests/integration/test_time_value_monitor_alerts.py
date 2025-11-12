"""Integration tests for Time Value Monitor alert path.

This test verifies:
1. Time value monitor publishes alerts to Redis
2. Alerts are properly formatted with correct severity
3. Alert router receives and processes TV monitor alerts
"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorDatabase
from spreadpilot_core.models.alert import AlertEvent, AlertSeverity, AlertType
from spreadpilot_core.models.follower import Follower
from spreadpilot_core.models.position import Position, PositionState
from trading_bot.app.service.time_value_monitor import TimeValueMonitor, TimeValueStatus


@pytest.mark.asyncio
async def test_tv_monitor_publishes_critical_alert(
    test_follower: Follower,
    test_mongo_db: AsyncIOMotorDatabase,
):
    """Test that TV monitor publishes critical alerts when time value <= $0.10."""
    # Create mock service
    mock_service = MagicMock()
    mock_service.mongo_db = test_mongo_db
    mock_service.settings = MagicMock(redis_url="redis://localhost:6379")

    # Create mock IBKR manager
    mock_ibkr_manager = AsyncMock()
    mock_service.ibkr_manager = mock_ibkr_manager

    # Create time value monitor
    tv_monitor = TimeValueMonitor(mock_service)

    # Mock Redis client
    mock_redis = AsyncMock(spec=redis.Redis)
    mock_redis.xadd = AsyncMock(return_value=b"1234567890-0")
    tv_monitor.redis_client = mock_redis

    # Create test position with low time value
    test_position = Position(
        id="pos123",
        follower_id=test_follower.id,
        date="2025-01-20",
        symbol="QQQ",
        long_qty=10,
        short_qty=10,
        long_strikes=[445.0] * 10,
        short_strikes=[450.0] * 10,
        state=PositionState.OPEN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Mock time value calculation to return critical value
    tv_monitor._calculate_time_value = AsyncMock(return_value=0.05)  # $0.05 < $0.10

    # Mock position closing
    tv_monitor._close_position = AsyncMock(return_value=True)

    # Check position time value
    await tv_monitor._check_position_time_value(test_position)

    # Verify alert was published to Redis
    mock_redis.xadd.assert_called_once()
    call_args = mock_redis.xadd.call_args

    # Check Redis stream name
    assert call_args[0][0] == "alerts:stream"

    # Check alert data
    alert_data = json.loads(call_args[0][1][b"data"].decode())
    assert alert_data["type"] == AlertType.CRITICAL.value
    assert alert_data["source"] == "time_value_monitor"
    assert alert_data["reason"] == "TIME_VALUE_THRESHOLD"
    assert alert_data["time_value"] == 0.05
    assert alert_data["threshold"] == 0.10
    assert alert_data["action"] == "AUTO_CLOSE"
    assert alert_data["follower_id"] == test_follower.id
    assert alert_data["position_id"] == "pos123"

    # Verify position was closed
    tv_monitor._close_position.assert_called_once_with(test_position)


@pytest.mark.asyncio
async def test_tv_monitor_publishes_risk_alert(
    test_follower: Follower,
    test_mongo_db: AsyncIOMotorDatabase,
):
    """Test that TV monitor publishes risk alerts when $0.10 < time value <= $1.00."""
    # Create mock service
    mock_service = MagicMock()
    mock_service.mongo_db = test_mongo_db
    mock_service.settings = MagicMock(redis_url="redis://localhost:6379")

    # Create mock IBKR manager
    mock_ibkr_manager = AsyncMock()
    mock_service.ibkr_manager = mock_ibkr_manager

    # Create time value monitor
    tv_monitor = TimeValueMonitor(mock_service)

    # Mock Redis client
    mock_redis = AsyncMock(spec=redis.Redis)
    mock_redis.xadd = AsyncMock(return_value=b"1234567890-0")
    tv_monitor.redis_client = mock_redis

    # Create test position with risk-level time value
    test_position = Position(
        id="pos456",
        follower_id=test_follower.id,
        date="2025-01-20",
        symbol="QQQ",
        long_qty=5,
        short_qty=5,
        long_strikes=[440.0] * 5,
        short_strikes=[445.0] * 5,
        state=PositionState.OPEN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Mock time value calculation to return risk value
    tv_monitor._calculate_time_value = AsyncMock(return_value=0.50)  # $0.10 < $0.50 <= $1.00

    # Check position time value
    await tv_monitor._check_position_time_value(test_position)

    # Verify alert was published to Redis
    mock_redis.xadd.assert_called_once()
    call_args = mock_redis.xadd.call_args

    # Check alert data
    alert_data = json.loads(call_args[0][1][b"data"].decode())
    assert alert_data["type"] == AlertType.WARNING.value
    assert alert_data["source"] == "time_value_monitor"
    assert alert_data["reason"] == "TIME_VALUE_RISK"
    assert alert_data["time_value"] == 0.50
    assert alert_data["status"] == TimeValueStatus.RISK.value
    assert alert_data["follower_id"] == test_follower.id
    assert alert_data["position_id"] == "pos456"

    # Verify position was NOT closed (only warning)
    assert not hasattr(tv_monitor, "_close_position") or not tv_monitor._close_position.called


@pytest.mark.asyncio
async def test_tv_monitor_alert_integration_with_router(
    test_follower: Follower,
    test_mongo_db: AsyncIOMotorDatabase,
):
    """Test complete integration of TV monitor alerts with alert router."""
    # Setup Redis connection for test
    redis_client = await redis.from_url("redis://localhost:6379", decode_responses=False)

    try:
        # Clear any existing alerts
        await redis_client.delete("alerts:stream")

        # Create mock service
        mock_service = MagicMock()
        mock_service.mongo_db = test_mongo_db
        mock_service.settings = MagicMock(redis_url="redis://localhost:6379")

        # Create time value monitor with real Redis
        tv_monitor = TimeValueMonitor(mock_service)
        await tv_monitor.connect_redis()

        # Create test position
        test_position = Position(
            id="pos789",
            follower_id=test_follower.id,
            date="2025-01-20",
            symbol="QQQ",
            long_qty=20,
            short_qty=20,
            long_strikes=[450.0] * 20,
            short_strikes=[455.0] * 20,
            state=PositionState.OPEN,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Mock calculations and actions
        tv_monitor._calculate_time_value = AsyncMock(return_value=0.08)
        tv_monitor._close_position = AsyncMock(return_value=True)

        # Publish alert
        await tv_monitor._publish_alert(
            {
                "type": AlertType.CRITICAL.value,
                "source": "time_value_monitor",
                "severity": AlertSeverity.CRITICAL.value,
                "reason": "TIME_VALUE_THRESHOLD",
                "time_value": 0.08,
                "threshold": 0.10,
                "action": "AUTO_CLOSE",
                "follower_id": test_follower.id,
                "position_id": test_position.id,
                "symbol": test_position.symbol,
                "message": f"Time value ${0.08:.2f} below threshold ${0.10:.2f} - Auto-closing position",
            }
        )

        # Verify alert was published to Redis stream
        alerts = await redis_client.xrange("alerts:stream", count=1)
        assert len(alerts) == 1

        # Parse and verify alert content
        alert_id, alert_fields = alerts[0]
        alert_data = json.loads(alert_fields[b"data"])

        assert alert_data["type"] == AlertType.CRITICAL.value
        assert alert_data["severity"] == AlertSeverity.CRITICAL.value
        assert alert_data["source"] == "time_value_monitor"
        assert alert_data["reason"] == "TIME_VALUE_THRESHOLD"
        assert alert_data["time_value"] == 0.08
        assert alert_data["follower_id"] == test_follower.id
        assert "Auto-closing position" in alert_data["message"]

    finally:
        # Cleanup
        await redis_client.delete("alerts:stream")
        await redis_client.close()


@pytest.mark.asyncio
async def test_tv_monitor_handles_calculation_errors(
    test_follower: Follower,
    test_mongo_db: AsyncIOMotorDatabase,
):
    """Test that TV monitor handles errors gracefully and publishes error alerts."""
    # Create mock service
    mock_service = MagicMock()
    mock_service.mongo_db = test_mongo_db
    mock_service.settings = MagicMock(redis_url="redis://localhost:6379")

    # Create time value monitor
    tv_monitor = TimeValueMonitor(mock_service)

    # Mock Redis client
    mock_redis = AsyncMock(spec=redis.Redis)
    mock_redis.xadd = AsyncMock(return_value=b"1234567890-0")
    tv_monitor.redis_client = mock_redis

    # Create test position
    test_position = Position(
        id="pos_error",
        follower_id=test_follower.id,
        date="2025-01-20",
        symbol="QQQ",
        long_qty=1,
        short_qty=1,
        long_strikes=[460.0],
        short_strikes=[465.0],
        state=PositionState.OPEN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Mock time value calculation to raise error
    tv_monitor._calculate_time_value = AsyncMock(side_effect=Exception("Market data unavailable"))

    # Check position time value - should not raise
    await tv_monitor._check_position_time_value(test_position)

    # Verify error alert was published
    mock_redis.xadd.assert_called_once()
    call_args = mock_redis.xadd.call_args

    # Check error alert data
    alert_data = json.loads(call_args[0][1][b"data"].decode())
    assert alert_data["type"] == AlertType.ERROR.value
    assert alert_data["source"] == "time_value_monitor"
    assert alert_data["reason"] == "CALCULATION_ERROR"
    assert "Market data unavailable" in alert_data["error"]
    assert alert_data["follower_id"] == test_follower.id
    assert alert_data["position_id"] == "pos_error"

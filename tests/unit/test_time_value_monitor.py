"""Unit tests for Time Value Monitor."""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis import aioredis as fakeredis
from ib_insync import Contract, Stock
from spreadpilot_core.models.alert import Alert, AlertSeverity
from trading_bot.app.service.time_value_monitor import (TimeValueMonitor,
                                                        TimeValueStatus)


@pytest.fixture
async def fake_redis():
    """Create a fake Redis client for testing."""
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    await client.close()


@pytest.fixture
def mock_service():
    """Create a mock trading service."""
    service = MagicMock()
    service.active_followers = {"test_follower_123": MagicMock(id="test_follower_123")}

    # Mock IBKR manager
    mock_ibkr_manager = MagicMock()
    service.ibkr_manager = mock_ibkr_manager

    return service


@pytest.fixture
def mock_ibkr_client():
    """Create a mock IBKR client."""
    client = MagicMock()
    client.ensure_connected = AsyncMock(return_value=True)

    # Mock IB instance
    mock_ib = MagicMock()
    client.ib = mock_ib

    # Mock market price methods
    client.get_market_price = AsyncMock()

    return client


@pytest.fixture
async def tv_monitor(mock_service, fake_redis):
    """Create a time value monitor instance."""
    monitor = TimeValueMonitor(mock_service)
    monitor.redis_client = fake_redis
    yield monitor
    # Cleanup
    if monitor.is_running:
        await monitor.stop_monitoring()


class TestTimeValueMonitor:
    """Test suite for Time Value Monitor."""

    @pytest.mark.asyncio
    async def test_scheduler_initialization(self, tv_monitor):
        """Test that apscheduler is properly initialized."""
        await tv_monitor.start_monitoring()

        assert tv_monitor.is_running is True
        assert tv_monitor.scheduler.running is True

        # Check job was added
        jobs = tv_monitor.scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "time_value_monitor"

    @pytest.mark.asyncio
    async def test_intrinsic_value_calculation(self, tv_monitor):
        """Test intrinsic value calculation for calls and puts."""
        # Test call option
        intrinsic_call = tv_monitor._calculate_intrinsic_value(
            strike=450.0, right="C", underlying_price=455.0
        )
        assert intrinsic_call == 5.0

        # Test OTM call
        intrinsic_otm_call = tv_monitor._calculate_intrinsic_value(
            strike=460.0, right="C", underlying_price=455.0
        )
        assert intrinsic_otm_call == 0.0

        # Test put option
        intrinsic_put = tv_monitor._calculate_intrinsic_value(
            strike=460.0, right="P", underlying_price=455.0
        )
        assert intrinsic_put == 5.0

        # Test OTM put
        intrinsic_otm_put = tv_monitor._calculate_intrinsic_value(
            strike=450.0, right="P", underlying_price=455.0
        )
        assert intrinsic_otm_put == 0.0

    @pytest.mark.asyncio
    async def test_time_value_status_determination(self, tv_monitor):
        """Test time value status categorization."""
        # Critical: TV <= $0.10
        assert tv_monitor._get_time_value_status(0.05) == TimeValueStatus.CRITICAL
        assert tv_monitor._get_time_value_status(0.10) == TimeValueStatus.CRITICAL

        # Risk: $0.10 < TV <= $1.00
        assert tv_monitor._get_time_value_status(0.11) == TimeValueStatus.RISK
        assert tv_monitor._get_time_value_status(0.50) == TimeValueStatus.RISK
        assert tv_monitor._get_time_value_status(1.00) == TimeValueStatus.RISK

        # Safe: TV > $1.00
        assert tv_monitor._get_time_value_status(1.01) == TimeValueStatus.SAFE
        assert tv_monitor._get_time_value_status(2.50) == TimeValueStatus.SAFE

    @pytest.mark.asyncio
    async def test_position_check_with_safe_tv(
        self, tv_monitor, mock_service, mock_ibkr_client, fake_redis
    ):
        """Test position check when time value is safe."""
        # Setup
        mock_service.ibkr_manager.get_client.return_value = mock_ibkr_client

        # Mock position
        mock_position = MagicMock()
        mock_position.contract.secType = "OPT"
        mock_position.contract.symbol = "QQQ"
        mock_position.contract.strike = 450.0
        mock_position.contract.right = "C"
        mock_position.position = 10

        mock_ibkr_client.ib.positions.return_value = [mock_position]

        # Mock prices: option at $3.50, underlying at $455, intrinsic = $5, TV = -$1.50
        mock_ibkr_client.get_market_price.side_effect = [3.50, 455.0]

        # Run check
        await tv_monitor._check_follower_positions(
            "test_follower_123", mock_service.active_followers["test_follower_123"]
        )

        # Check status was published to Redis
        status_key = await fake_redis.get("tv:test_follower_123")
        assert status_key is not None
        status_data = json.loads(status_key)
        assert status_data["status"] == "SAFE"
        assert abs(status_data["time_value"] - (-1.50)) < 0.01

        # No alerts should be published for SAFE status
        alerts = await fake_redis.xrange("alerts")
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_position_check_with_risk_tv(
        self, tv_monitor, mock_service, mock_ibkr_client, fake_redis
    ):
        """Test position check when time value is at risk level."""
        # Setup
        mock_service.ibkr_manager.get_client.return_value = mock_ibkr_client

        # Mock position
        mock_position = MagicMock()
        mock_position.contract.secType = "OPT"
        mock_position.contract.symbol = "QQQ"
        mock_position.contract.strike = 450.0
        mock_position.contract.right = "P"
        mock_position.position = -5

        mock_ibkr_client.ib.positions.return_value = [mock_position]

        # Mock prices: option at $5.50, underlying at $445, intrinsic = $5, TV = $0.50
        mock_ibkr_client.get_market_price.side_effect = [5.50, 445.0]

        # Run check
        await tv_monitor._check_follower_positions(
            "test_follower_123", mock_service.active_followers["test_follower_123"]
        )

        # Check status
        status_key = await fake_redis.get("tv:test_follower_123")
        status_data = json.loads(status_key)
        assert status_data["status"] == "RISK"

        # Check alert was published
        alerts = await fake_redis.xrange("alerts")
        assert len(alerts) == 1

        _, alert_data = alerts[0]
        alert = Alert.model_validate_json(alert_data["data"])
        assert alert.follower_id == "test_follower_123"
        assert "TIME_VALUE_WARNING" in alert.reason
        assert "$0.50" in alert.reason
        assert alert.severity == AlertSeverity.WARNING

    @pytest.mark.asyncio
    async def test_position_liquidation_on_critical_tv(
        self, tv_monitor, mock_service, mock_ibkr_client, fake_redis
    ):
        """Test automatic position liquidation when TV <= $0.10."""
        # Setup
        mock_service.ibkr_manager.get_client.return_value = mock_ibkr_client

        # Mock position (short put)
        mock_position = MagicMock()
        mock_position.contract.secType = "OPT"
        mock_position.contract.symbol = "QQQ"
        mock_position.contract.strike = 450.0
        mock_position.contract.right = "P"
        mock_position.position = -10  # Short position

        mock_ibkr_client.ib.positions.return_value = [mock_position]

        # Mock prices: option at $5.08, underlying at $445, intrinsic = $5, TV = $0.08
        mock_ibkr_client.get_market_price.side_effect = [5.08, 445.0]

        # Mock order placement
        mock_trade = MagicMock()
        mock_trade.orderStatus.status = "Filled"
        mock_trade.orderStatus.avgFillPrice = 5.10
        mock_trade.order.orderId = 12345
        mock_ibkr_client.ib.placeOrder.return_value = mock_trade

        # Run check
        await tv_monitor._check_follower_positions(
            "test_follower_123", mock_service.active_followers["test_follower_123"]
        )

        # Check market order was placed to close position
        mock_ibkr_client.ib.placeOrder.assert_called_once()
        call_args = mock_ibkr_client.ib.placeOrder.call_args
        order = call_args[0][1]
        assert order.action == "BUY"  # Buy to close short position
        assert order.totalQuantity == 10

        # Check status
        status_key = await fake_redis.get("tv:test_follower_123")
        status_data = json.loads(status_key)
        assert status_data["status"] == "CRITICAL"

        # Check alerts (should have critical alert + liquidation success)
        alerts = await fake_redis.xrange("alerts")
        assert len(alerts) == 2

        # First alert: critical warning
        _, alert1_data = alerts[0]
        alert1 = Alert.model_validate_json(alert1_data["data"])
        assert "TIME_VALUE_THRESHOLD" in alert1.reason
        assert alert1.severity == AlertSeverity.CRITICAL

        # Second alert: liquidation success
        _, alert2_data = alerts[1]
        alert2 = Alert.model_validate_json(alert2_data["data"])
        assert "TIME_VALUE_LIQUIDATION" in alert2.reason
        assert "Successfully closed position" in alert2.reason
        assert alert2.severity == AlertSeverity.INFO

    @pytest.mark.asyncio
    async def test_multiple_positions_monitoring(
        self, tv_monitor, mock_service, mock_ibkr_client, fake_redis
    ):
        """Test monitoring multiple positions with different time values."""
        # Setup
        mock_service.ibkr_manager.get_client.return_value = mock_ibkr_client

        # Mock multiple positions
        positions = [
            # Safe position
            MagicMock(
                contract=MagicMock(secType="OPT", symbol="QQQ", strike=440.0, right="C"), position=5
            ),
            # Risk position
            MagicMock(
                contract=MagicMock(secType="OPT", symbol="QQQ", strike=450.0, right="P"),
                position=-10,
            ),
            # Critical position
            MagicMock(
                contract=MagicMock(secType="OPT", symbol="QQQ", strike=460.0, right="C"),
                position=15,
            ),
            # Non-QQQ option (should be ignored)
            MagicMock(
                contract=MagicMock(secType="OPT", symbol="SPY", strike=400.0, right="P"),
                position=20,
            ),
        ]

        mock_ibkr_client.ib.positions.return_value = positions

        # Mock prices for each position check
        # Position 1: Safe (TV = $2.00)
        # Position 2: Risk (TV = $0.75)
        # Position 3: Critical (TV = $0.05)
        mock_ibkr_client.get_market_price.side_effect = [
            7.00,
            445.0,  # Position 1: option $7, underlying $445, intrinsic $5, TV $2
            5.75,
            445.0,  # Position 2: option $5.75, underlying $445, intrinsic $5, TV $0.75
            0.05,
            445.0,  # Position 3: option $0.05, underlying $445, intrinsic $0, TV $0.05
        ]

        # Mock order for critical position
        mock_trade = MagicMock()
        mock_trade.orderStatus.status = "Filled"
        mock_trade.orderStatus.avgFillPrice = 0.06
        mock_trade.order.orderId = 12345
        mock_ibkr_client.ib.placeOrder.return_value = mock_trade

        # Run check
        await tv_monitor._check_follower_positions(
            "test_follower_123", mock_service.active_followers["test_follower_123"]
        )

        # Verify only QQQ options were checked (3 positions)
        assert (
            mock_ibkr_client.get_market_price.call_count == 6
        )  # 2 calls per position (option + underlying)

        # Check alerts
        alerts = await fake_redis.xrange("alerts")
        # Should have: 1 risk alert + 1 critical alert + 1 liquidation alert
        assert len(alerts) == 3

    @pytest.mark.asyncio
    async def test_error_handling_no_ibkr_client(self, tv_monitor, mock_service, fake_redis):
        """Test handling when IBKR client is not available."""
        # Setup: no IBKR client available
        mock_service.ibkr_manager.get_client.return_value = None

        # Run check - should log warning but not raise
        await tv_monitor._check_follower_positions(
            "test_follower_123", mock_service.active_followers["test_follower_123"]
        )

        # No alerts or status should be published
        alerts = await fake_redis.xrange("alerts")
        assert len(alerts) == 0

        status = await fake_redis.get("tv:test_follower_123")
        assert status is None

    @pytest.mark.asyncio
    async def test_error_handling_market_price_failure(
        self, tv_monitor, mock_service, mock_ibkr_client, fake_redis
    ):
        """Test handling when market price retrieval fails."""
        # Setup
        mock_service.ibkr_manager.get_client.return_value = mock_ibkr_client

        # Mock position
        mock_position = MagicMock()
        mock_position.contract.secType = "OPT"
        mock_position.contract.symbol = "QQQ"
        mock_position.contract.strike = 450.0
        mock_position.contract.right = "C"
        mock_position.position = 10

        mock_ibkr_client.ib.positions.return_value = [mock_position]

        # Mock price failure
        mock_ibkr_client.get_market_price.return_value = None

        # Run check - should handle gracefully
        await tv_monitor._check_follower_positions(
            "test_follower_123", mock_service.active_followers["test_follower_123"]
        )

        # No alerts or status should be published
        alerts = await fake_redis.xrange("alerts")
        assert len(alerts) == 0

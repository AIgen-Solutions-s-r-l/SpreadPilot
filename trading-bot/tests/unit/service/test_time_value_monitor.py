"""Unit tests for TimeValueMonitor with mock IB."""

import asyncio
import json
import os
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis
import pytest
from freezegun import freeze_time
import pytz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../../spreadpilot-core"))

from app.service.time_value_monitor import TimeValueMonitor, TimeValueStatus
from spreadpilot_core.models.alert import AlertType, AlertEvent


class MockPosition:
    """Mock IB position object."""

    def __init__(self, contract, position):
        self.contract = contract
        self.position = position


class MockContract:
    """Mock IB contract object."""

    def __init__(self, symbol, secType, strike, right):
        self.symbol = symbol
        self.secType = secType
        self.strike = strike
        self.right = right


class MockOrderStatus:
    """Mock IB order status."""

    def __init__(self, status="Filled", avgFillPrice=1.0):
        self.status = status
        self.avgFillPrice = avgFillPrice


class MockOrder:
    """Mock IB order."""

    def __init__(self, orderId=12345):
        self.orderId = orderId


class MockTrade:
    """Mock IB trade object."""

    def __init__(self, status="Filled", avgFillPrice=1.0):
        self.orderStatus = MockOrderStatus(status, avgFillPrice)
        self.order = MockOrder()


@pytest.mark.asyncio
class TestTimeValueMonitor:
    """Test cases for TimeValueMonitor."""

    @pytest.fixture
    def setup(self):
        """Set up test fixtures."""
        # Create mock service
        self.mock_service = MagicMock()
        self.mock_service.active_followers = {"test-follower": MagicMock()}
        self.mock_service.ibkr_manager = MagicMock()

        # Create monitor
        self.monitor = TimeValueMonitor(self.mock_service, redis_url="redis://fake")
        
        # Create fake Redis
        self.fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)
        self.monitor.redis_client = self.fake_redis

    async def test_intrinsic_value_calculation(self, setup):
        """Test intrinsic value calculation for calls and puts."""
        # Test call option
        # Strike 100, underlying 105 -> intrinsic value = 5
        intrinsic = self.monitor._calculate_intrinsic_value(100, "C", 105)
        assert intrinsic == 5

        # Strike 100, underlying 95 -> intrinsic value = 0 (OTM)
        intrinsic = self.monitor._calculate_intrinsic_value(100, "C", 95)
        assert intrinsic == 0

        # Test put option
        # Strike 100, underlying 95 -> intrinsic value = 5
        intrinsic = self.monitor._calculate_intrinsic_value(100, "P", 95)
        assert intrinsic == 5

        # Strike 100, underlying 105 -> intrinsic value = 0 (OTM)
        intrinsic = self.monitor._calculate_intrinsic_value(100, "P", 105)
        assert intrinsic == 0

    async def test_time_value_status(self, setup):
        """Test time value status determination."""
        # Test CRITICAL status (TV <= $0.10)
        status = self.monitor._get_time_value_status(0.05)
        assert status == TimeValueStatus.CRITICAL

        status = self.monitor._get_time_value_status(0.10)
        assert status == TimeValueStatus.CRITICAL

        # Test RISK status ($0.10 < TV <= $1.00)
        status = self.monitor._get_time_value_status(0.50)
        assert status == TimeValueStatus.RISK

        status = self.monitor._get_time_value_status(1.00)
        assert status == TimeValueStatus.RISK

        # Test SAFE status (TV > $1.00)
        status = self.monitor._get_time_value_status(1.50)
        assert status == TimeValueStatus.SAFE

    async def test_check_position_time_value_safe(self, setup):
        """Test checking position with safe time value."""
        # Mock IBKR client
        mock_client = MagicMock()
        mock_client.get_market_price = AsyncMock()

        # Mock market prices
        # Option price: $2.50
        # Underlying: $100, Strike: $98 Put -> Intrinsic: $0
        # Time value: $2.50 - $0 = $2.50 (SAFE)
        mock_client.get_market_price.side_effect = [2.50, 100.0]

        # Create position
        contract = MockContract("QQQ", "OPT", 98.0, "P")
        position = MockPosition(contract, 10)

        await self.monitor._check_position_time_value(
            "test-follower", mock_client, position, contract
        )

        # Check Redis TV status was updated
        tv_status = await self.monitor.redis_client.get("tv:test-follower")
        assert tv_status is not None
        status_data = json.loads(tv_status)
        assert status_data["status"] == TimeValueStatus.SAFE.value
        assert status_data["time_value"] == 2.50

    async def test_check_position_time_value_risk(self, setup):
        """Test checking position with risk time value."""
        # Mock IBKR client
        mock_client = MagicMock()
        mock_client.get_market_price = AsyncMock()

        # Mock market prices
        # Option price: $0.80
        # Underlying: $100, Strike: $98 Put -> Intrinsic: $0
        # Time value: $0.80 - $0 = $0.80 (RISK)
        mock_client.get_market_price.side_effect = [0.80, 100.0]

        # Create position
        contract = MockContract("QQQ", "OPT", 98.0, "P")
        position = MockPosition(contract, 10)

        await self.monitor._check_position_time_value(
            "test-follower", mock_client, position, contract
        )

        # Check alert was published
        alerts = await self.monitor.redis_client.xrange("alerts", "-", "+")
        assert len(alerts) == 1
        
        # Parse alert event
        msg_id, data = alerts[0]
        alert_event = AlertEvent.model_validate_json(data["data"])
        assert alert_event.event_type == AlertType.MID_TOO_LOW
        assert "low time value" in alert_event.message
        assert alert_event.params["time_value"] == 0.80

    async def test_check_position_time_value_critical_and_close(self, setup):
        """Test checking position with critical time value and auto-close."""
        # Mock IBKR client
        mock_client = MagicMock()
        mock_client.get_market_price = AsyncMock()
        mock_client.ib = MagicMock()

        # Mock market prices
        # Option price: $0.08
        # Underlying: $100, Strike: $98 Put -> Intrinsic: $0
        # Time value: $0.08 - $0 = $0.08 (CRITICAL)
        mock_client.get_market_price.side_effect = [0.08, 100.0]

        # Mock order placement
        mock_trade = MockTrade(status="Filled", avgFillPrice=0.07)
        mock_client.ib.placeOrder = MagicMock(return_value=mock_trade)

        # Create position (long 10 contracts)
        contract = MockContract("QQQ", "OPT", 98.0, "P")
        position = MockPosition(contract, 10)

        await self.monitor._check_position_time_value(
            "test-follower", mock_client, position, contract
        )

        # Verify market order was placed
        mock_client.ib.placeOrder.assert_called_once()
        placed_contract, placed_order = mock_client.ib.placeOrder.call_args[0]

        # Check order details (SELL to close long position)
        assert placed_order.action == "SELL"
        assert placed_order.totalQuantity == 10

        # Check alerts were published (critical alert + success alert)
        alerts = await self.monitor.redis_client.xrange("alerts", "-", "+")
        assert len(alerts) == 2  # Critical + Success

        # Check critical alert
        msg_id, data = alerts[0]
        alert_event = AlertEvent.model_validate_json(data["data"])
        assert alert_event.event_type == AlertType.LIMIT_REACHED
        assert "critical time value" in alert_event.message

        # Check success alert
        msg_id, data = alerts[1]
        alert_event = AlertEvent.model_validate_json(data["data"])
        assert alert_event.event_type == AlertType.ASSIGNMENT_COMPENSATED
        assert "Successfully closed position" in alert_event.message

    async def test_check_position_short_critical(self, setup):
        """Test checking short position with critical time value."""
        # Mock IBKR client
        mock_client = MagicMock()
        mock_client.get_market_price = AsyncMock()
        mock_client.ib = MagicMock()

        # Mock market prices
        # Option price: $0.09
        # Underlying: $100, Strike: $102 Call -> Intrinsic: $0
        # Time value: $0.09 - $0 = $0.09 (CRITICAL)
        mock_client.get_market_price.side_effect = [0.09, 100.0]

        # Mock order placement
        mock_trade = MockTrade(status="Filled", avgFillPrice=0.08)
        mock_client.ib.placeOrder = MagicMock(return_value=mock_trade)

        # Create short position (-5 contracts)
        contract = MockContract("QQQ", "OPT", 102.0, "C")
        position = MockPosition(contract, -5)

        await self.monitor._check_position_time_value(
            "test-follower", mock_client, position, contract
        )

        # Verify market order was placed
        mock_client.ib.placeOrder.assert_called_once()
        placed_contract, placed_order = mock_client.ib.placeOrder.call_args[0]

        # Check order details (BUY to close short position)
        assert placed_order.action == "BUY"
        assert placed_order.totalQuantity == 5

    @freeze_time("2024-01-15 10:00:00", tz_offset=-5)
    async def test_monitoring_loop(self, setup):
        """Test the monitoring loop functionality."""
        # Mock dependencies
        self.monitor.monitoring_interval = 0.1  # Short interval for testing
        self.monitor._check_all_positions = AsyncMock()

        # Start monitoring
        await self.monitor.start_monitoring()
        assert self.monitor.is_running is True

        # Let it run for a bit
        await asyncio.sleep(0.3)

        # Should have been called at least twice
        assert self.monitor._check_all_positions.call_count >= 2

        # Stop monitoring
        await self.monitor.stop_monitoring()
        assert self.monitor.is_running is False

    async def test_check_all_positions(self, setup):
        """Test checking positions for all followers."""
        # Mock follower positions check
        self.monitor._check_follower_positions = AsyncMock()

        # Add more followers
        self.mock_service.active_followers = {
            "follower1": MagicMock(),
            "follower2": MagicMock(),
            "follower3": MagicMock(),
        }

        await self.monitor._check_all_positions()

        # Should check each follower
        assert self.monitor._check_follower_positions.call_count == 3

    async def test_no_positions(self, setup):
        """Test handling when no positions exist."""
        # Mock IBKR client
        mock_client = MagicMock()
        mock_client.ensure_connected = AsyncMock(return_value=True)
        mock_client.ib.positions = MagicMock(return_value=[])

        self.mock_service.ibkr_manager.get_client = AsyncMock(return_value=mock_client)

        # Should not raise any errors
        await self.monitor._check_follower_positions("test-follower", MagicMock())

    async def test_connection_failure(self, setup):
        """Test handling IBKR connection failure."""
        # Mock IBKR client that fails to connect
        mock_client = MagicMock()
        mock_client.ensure_connected = AsyncMock(return_value=False)

        self.mock_service.ibkr_manager.get_client = AsyncMock(return_value=mock_client)

        # Should handle gracefully
        await self.monitor._check_follower_positions("test-follower", MagicMock())

    async def test_market_price_failure(self, setup):
        """Test handling when market price is unavailable."""
        # Mock IBKR client
        mock_client = MagicMock()
        mock_client.get_market_price = AsyncMock(return_value=None)

        # Create position
        contract = MockContract("QQQ", "OPT", 98.0, "P")
        position = MockPosition(contract, 10)

        # Should handle gracefully
        await self.monitor._check_position_time_value(
            "test-follower", mock_client, position, contract
        )

        # No alerts should be published
        alerts = await self.monitor.redis_client.xrange("alerts", "-", "+")
        assert len(alerts) == 0

    async def test_context_manager(self, setup):
        """Test context manager functionality."""
        monitor = TimeValueMonitor(self.mock_service, redis_url="redis://fake")
        
        with patch("redis.asyncio.from_url") as mock_redis:
            mock_redis.return_value = self.fake_redis
            
            async with monitor as m:
                assert m.redis_client is not None

        # Should be disconnected after context exit
        assert monitor.redis_client is None

    async def test_scheduler_timezone(self, setup):
        """Test that scheduler uses US/Eastern timezone."""
        await self.monitor.start_monitoring()
        
        # Verify scheduler timezone is US/Eastern
        assert self.monitor.scheduler.timezone == pytz.timezone('US/Eastern')
        
        await self.monitor.stop_monitoring()

    async def test_redis_key_expiration(self, setup):
        """Test that Redis keys have proper expiration."""
        # Mock to capture Redis set call
        original_set = self.monitor.redis_client.set
        set_calls = []
        
        async def capture_set(*args, **kwargs):
            set_calls.append((args, kwargs))
            return await original_set(*args, **kwargs)
        
        self.monitor.redis_client.set = capture_set
        
        await self.monitor._publish_time_value_status(
            "test-follower", 0.50, TimeValueStatus.RISK
        )
        
        # Verify expiration is set
        assert len(set_calls) == 1
        _, kwargs = set_calls[0]
        assert kwargs.get("ex") == 300  # 5 minutes
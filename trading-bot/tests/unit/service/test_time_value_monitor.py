"""Unit tests for TimeValueMonitor with mock IB."""

import asyncio
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis as fakeredis

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../../spreadpilot-core"))

from app.service.time_value_monitor import TimeValueMonitor, TimeValueStatus
from spreadpilot_core.models.alert import AlertType


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


class TestTimeValueMonitor(unittest.TestCase):
    """Test cases for TimeValueMonitor."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock service
        self.mock_service = MagicMock()
        self.mock_service.active_followers = {"test-follower": MagicMock()}
        self.mock_service.ibkr_manager = MagicMock()

        # Create monitor
        self.monitor = TimeValueMonitor(self.mock_service, redis_url="redis://fake")

    async def test_intrinsic_value_calculation(self):
        """Test intrinsic value calculation for calls and puts."""
        # Test call option
        # Strike 100, underlying 105 -> intrinsic value = 5
        intrinsic = self.monitor._calculate_intrinsic_value(100, "C", 105)
        self.assertEqual(intrinsic, 5)

        # Strike 100, underlying 95 -> intrinsic value = 0 (OTM)
        intrinsic = self.monitor._calculate_intrinsic_value(100, "C", 95)
        self.assertEqual(intrinsic, 0)

        # Test put option
        # Strike 100, underlying 95 -> intrinsic value = 5
        intrinsic = self.monitor._calculate_intrinsic_value(100, "P", 95)
        self.assertEqual(intrinsic, 5)

        # Strike 100, underlying 105 -> intrinsic value = 0 (OTM)
        intrinsic = self.monitor._calculate_intrinsic_value(100, "P", 105)
        self.assertEqual(intrinsic, 0)

    async def test_time_value_status(self):
        """Test time value status determination."""
        # Test CRITICAL status (TV <= $0.10)
        status = self.monitor._get_time_value_status(0.05)
        self.assertEqual(status, TimeValueStatus.CRITICAL)

        status = self.monitor._get_time_value_status(0.10)
        self.assertEqual(status, TimeValueStatus.CRITICAL)

        # Test RISK status ($0.10 < TV <= $1.00)
        status = self.monitor._get_time_value_status(0.50)
        self.assertEqual(status, TimeValueStatus.RISK)

        status = self.monitor._get_time_value_status(1.00)
        self.assertEqual(status, TimeValueStatus.RISK)

        # Test SAFE status (TV > $1.00)
        status = self.monitor._get_time_value_status(1.50)
        self.assertEqual(status, TimeValueStatus.SAFE)

    async def test_check_position_time_value_safe(self):
        """Test checking position with safe time value."""
        # Create fake Redis
        fake_redis = fakeredis.FakeRedis(decode_responses=True)

        with patch("redis.asyncio.from_url", return_value=fake_redis):
            await self.monitor.connect_redis()

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

            # Check alert was published
            alerts = await fake_redis.xread({"alerts": 0})
            self.assertEqual(len(alerts), 1)

            # Parse alert
            stream_name, messages = alerts[0]
            message_id, data = messages[0]
            alert_json = data[b"alert"]
            alert_data = json.loads(alert_json)

            # Verify alert content
            self.assertIn("SAFE", alert_data["message"])
            self.assertEqual(alert_data["params"]["status"], TimeValueStatus.SAFE)
            self.assertEqual(alert_data["params"]["time_value"], 2.50)

    async def test_check_position_time_value_risk(self):
        """Test checking position with risk time value."""
        # Create fake Redis
        fake_redis = fakeredis.FakeRedis(decode_responses=True)

        with patch("redis.asyncio.from_url", return_value=fake_redis):
            await self.monitor.connect_redis()

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
            alerts = await fake_redis.xread({"alerts": 0})
            self.assertEqual(len(alerts), 1)

            # Parse alert
            stream_name, messages = alerts[0]
            message_id, data = messages[0]
            alert_json = data[b"alert"]
            alert_data = json.loads(alert_json)

            # Verify alert content
            self.assertIn("RISK", alert_data["message"])
            self.assertEqual(alert_data["params"]["status"], TimeValueStatus.RISK)
            self.assertEqual(alert_data["params"]["time_value"], 0.80)

    async def test_check_position_time_value_critical_and_close(self):
        """Test checking position with critical time value and auto-close."""
        # Create fake Redis
        fake_redis = fakeredis.FakeRedis(decode_responses=True)

        with patch("redis.asyncio.from_url", return_value=fake_redis):
            await self.monitor.connect_redis()

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
            self.assertEqual(placed_order.action, "SELL")
            self.assertEqual(placed_order.totalQuantity, 10)

            # Check alerts were published (critical alert + success alert)
            alerts = await fake_redis.xread({"alerts": 0})
            self.assertEqual(len(alerts), 1)

            # Parse alerts
            stream_name, messages = alerts[0]
            self.assertEqual(len(messages), 2)  # Critical + Success

            # Check critical alert
            message_id, data = messages[0]
            alert_json = data[b"alert"]
            alert_data = json.loads(alert_json)
            self.assertIn("CRITICAL", alert_data["message"])

            # Check success alert
            message_id, data = messages[1]
            alert_json = data[b"alert"]
            alert_data = json.loads(alert_json)
            self.assertEqual(alert_data["event_type"], AlertType.ASSIGNMENT_COMPENSATED.value)
            self.assertIn("Closed position", alert_data["message"])

    async def test_check_position_short_critical(self):
        """Test checking short position with critical time value."""
        # Create fake Redis
        fake_redis = fakeredis.FakeRedis(decode_responses=True)

        with patch("redis.asyncio.from_url", return_value=fake_redis):
            await self.monitor.connect_redis()

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
            self.assertEqual(placed_order.action, "BUY")
            self.assertEqual(placed_order.totalQuantity, 5)

    async def test_monitoring_loop(self):
        """Test the monitoring loop functionality."""
        # Mock dependencies
        self.monitor.monitoring_interval = 0.1  # Short interval for testing
        self.monitor._check_all_positions = AsyncMock()

        # Start monitoring
        await self.monitor.start_monitoring()
        self.assertTrue(self.monitor.is_running)

        # Let it run for a bit
        await asyncio.sleep(0.3)

        # Should have been called at least twice
        self.assertGreaterEqual(self.monitor._check_all_positions.call_count, 2)

        # Stop monitoring
        await self.monitor.stop_monitoring()
        self.assertFalse(self.monitor.is_running)

    async def test_check_all_positions(self):
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
        self.assertEqual(self.monitor._check_follower_positions.call_count, 3)

    async def test_no_positions(self):
        """Test handling when no positions exist."""
        # Mock IBKR client
        mock_client = MagicMock()
        mock_client.ensure_connected = AsyncMock(return_value=True)
        mock_client.ib.positions = MagicMock(return_value=[])

        self.mock_service.ibkr_manager.get_client = AsyncMock(return_value=mock_client)

        # Should not raise any errors
        await self.monitor._check_follower_positions("test-follower", MagicMock())

    async def test_connection_failure(self):
        """Test handling IBKR connection failure."""
        # Mock IBKR client that fails to connect
        mock_client = MagicMock()
        mock_client.ensure_connected = AsyncMock(return_value=False)

        self.mock_service.ibkr_manager.get_client = AsyncMock(return_value=mock_client)

        # Should handle gracefully
        await self.monitor._check_follower_positions("test-follower", MagicMock())

    async def test_market_price_failure(self):
        """Test handling when market price is unavailable."""
        # Create fake Redis
        fake_redis = fakeredis.FakeRedis(decode_responses=True)

        with patch("redis.asyncio.from_url", return_value=fake_redis):
            await self.monitor.connect_redis()

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
            alerts = await fake_redis.xread({"alerts": 0})
            self.assertEqual(len(alerts), 0)

    async def test_context_manager(self):
        """Test context manager functionality."""
        async with self.monitor as m:
            self.assertIsNotNone(m.redis_client)

        # Should be disconnected after context exit
        self.assertIsNone(self.monitor.redis_client)


if __name__ == "__main__":
    # Run async tests
    import asyncio

    async def run_tests():
        test_instance = TestTimeValueMonitor()
        test_instance.setUp()

        print("Testing intrinsic value calculation...")
        await test_instance.test_intrinsic_value_calculation()

        test_instance.setUp()
        print("Testing time value status...")
        await test_instance.test_time_value_status()

        test_instance.setUp()
        print("Testing safe position...")
        await test_instance.test_check_position_time_value_safe()

        test_instance.setUp()
        print("Testing risk position...")
        await test_instance.test_check_position_time_value_risk()

        test_instance.setUp()
        print("Testing critical position with auto-close...")
        await test_instance.test_check_position_time_value_critical_and_close()

        test_instance.setUp()
        print("Testing short position critical...")
        await test_instance.test_check_position_short_critical()

        test_instance.setUp()
        print("Testing monitoring loop...")
        await test_instance.test_monitoring_loop()

        test_instance.setUp()
        print("Testing check all positions...")
        await test_instance.test_check_all_positions()

        test_instance.setUp()
        print("Testing no positions...")
        await test_instance.test_no_positions()

        test_instance.setUp()
        print("Testing connection failure...")
        await test_instance.test_connection_failure()

        test_instance.setUp()
        print("Testing market price failure...")
        await test_instance.test_market_price_failure()

        test_instance.setUp()
        print("Testing context manager...")
        await test_instance.test_context_manager()

        print("All tests passed!")

    asyncio.run(run_tests())

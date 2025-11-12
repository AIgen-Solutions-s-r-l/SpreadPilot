"""Unit tests for VerticalSpreadExecutor Redis alert publishing."""

import asyncio
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis as fakeredis

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../../spreadpilot-core"))

from app.service.executor import VerticalSpreadExecutor
from spreadpilot_core.ibkr.client import IBKRClient, OrderStatus
from spreadpilot_core.models.alert import AlertType


class TestVerticalSpreadExecutorRedisAlerts(unittest.TestCase):
    """Test cases for Redis alert publishing in VerticalSpreadExecutor."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock IBKR client
        self.mock_ibkr_client = MagicMock(spec=IBKRClient)
        self.mock_ibkr_client.ib = MagicMock()
        self.mock_ibkr_client.ensure_connected = AsyncMock(return_value=True)
        self.mock_ibkr_client._get_qqq_option_contract = MagicMock()
        self.mock_ibkr_client.get_market_price = AsyncMock()
        self.mock_ibkr_client.get_account_summary = AsyncMock()

        # Create executor with fake Redis
        self.executor = VerticalSpreadExecutor(self.mock_ibkr_client, redis_url="redis://fake")

        # Test signal
        self.test_signal = {
            "strategy": "Long",
            "qty_per_leg": 1,
            "strike_long": 380.0,
            "strike_short": 385.0,
        }

        self.follower_id = "test-follower-123"

    async def test_margin_fail_alert(self):
        """Test that margin failure triggers NO_MARGIN alert to Redis."""
        # Create fake Redis instance
        fake_redis = fakeredis.FakeRedis(decode_responses=True)

        with patch("redis.asyncio.from_url", return_value=fake_redis):
            # Mock whatIf check to fail
            mock_whatif_result = MagicMock()
            mock_whatif_result.initMarginChange = "10000"
            mock_whatif_result.maintMarginChange = "8000"
            mock_whatif_result.equityWithLoanAfter = "50000"
            self.mock_ibkr_client.ib.whatIfOrderAsync = AsyncMock(return_value=mock_whatif_result)

            # Mock account summary with insufficient funds
            self.mock_ibkr_client.get_account_summary = AsyncMock(
                return_value={"AvailableFunds": "5000"}
            )

            # Execute and expect failure
            result = await self.executor.execute_vertical_spread(self.test_signal, self.follower_id)

            # Check that order was rejected
            self.assertEqual(result["status"], OrderStatus.REJECTED)
            self.assertIn("Margin check failed", result["error"])

            # Check Redis for alert
            alerts = await fake_redis.xread({"alerts": 0})
            self.assertEqual(len(alerts), 1)

            # Parse and verify alert
            stream_name, messages = alerts[0]
            self.assertEqual(stream_name, b"alerts")
            self.assertEqual(len(messages), 1)

            message_id, data = messages[0]
            alert_json = data[b"alert"]
            alert_data = json.loads(alert_json)

            # Verify alert content
            self.assertEqual(alert_data["event_type"], AlertType.NO_MARGIN.value)
            self.assertIn("Margin check failed", alert_data["message"])
            self.assertEqual(alert_data["params"]["follower_id"], self.follower_id)

    async def test_mid_price_threshold_alert(self):
        """Test that MID price below threshold triggers MID_TOO_LOW alert."""
        # Create fake Redis instance
        fake_redis = fakeredis.FakeRedis(decode_responses=True)

        with patch("redis.asyncio.from_url", return_value=fake_redis):
            # Mock successful whatIf check
            mock_whatif_result = MagicMock()
            mock_whatif_result.initMarginChange = "1000"
            mock_whatif_result.maintMarginChange = "800"
            mock_whatif_result.equityWithLoanAfter = "50000"
            self.mock_ibkr_client.ib.whatIfOrderAsync = AsyncMock(return_value=mock_whatif_result)

            # Mock account summary with sufficient funds
            self.mock_ibkr_client.get_account_summary = AsyncMock(
                return_value={"AvailableFunds": "10000"}
            )

            # Mock market prices that result in low MID price
            self.mock_ibkr_client.get_market_price = AsyncMock(
                side_effect=[0.30, 0.80]  # Long price  # Short price
            )

            # Execute with threshold that will fail
            result = await self.executor.execute_vertical_spread(
                self.test_signal, self.follower_id, min_price_threshold=0.70
            )

            # Check that order was rejected
            self.assertEqual(result["status"], OrderStatus.REJECTED)
            self.assertIn("below minimum threshold", result["error"])

            # Check Redis for alert
            alerts = await fake_redis.xread({"alerts": 0})
            self.assertEqual(len(alerts), 1)

            # Parse and verify alert
            stream_name, messages = alerts[0]
            message_id, data = messages[0]
            alert_json = data[b"alert"]
            alert_data = json.loads(alert_json)

            # Verify alert content
            self.assertEqual(alert_data["event_type"], AlertType.MID_TOO_LOW.value)
            self.assertIn("below threshold", alert_data["message"])
            self.assertEqual(alert_data["params"]["follower_id"], self.follower_id)
            self.assertEqual(alert_data["params"]["mid_price"], 0.5)
            self.assertEqual(alert_data["params"]["threshold"], 0.70)

    async def test_ladder_exhausted_alert(self):
        """Test that exhausting all ladder attempts triggers LIMIT_REACHED alert."""
        # Create fake Redis instance
        fake_redis = fakeredis.FakeRedis(decode_responses=True)

        with patch("redis.asyncio.from_url", return_value=fake_redis):
            # Mock successful whatIf check
            mock_whatif_result = MagicMock()
            mock_whatif_result.initMarginChange = "1000"
            mock_whatif_result.maintMarginChange = "800"
            mock_whatif_result.equityWithLoanAfter = "50000"
            self.mock_ibkr_client.ib.whatIfOrderAsync = AsyncMock(return_value=mock_whatif_result)

            # Mock account summary with sufficient funds
            self.mock_ibkr_client.get_account_summary = AsyncMock(
                return_value={"AvailableFunds": "10000"}
            )

            # Mock market prices
            self.mock_ibkr_client.get_market_price = AsyncMock(
                side_effect=[1.00, 2.00]  # Long price  # Short price
            )

            # Mock order placement that never fills
            mock_trade = MagicMock()
            mock_trade.orderStatus.status = "Submitted"
            mock_trade.orderStatus.filled = 0
            mock_trade.order.orderId = 12345
            self.mock_ibkr_client.ib.placeOrder = MagicMock(return_value=mock_trade)
            self.mock_ibkr_client.ib.waitOnUpdate = MagicMock()
            self.mock_ibkr_client.ib.cancelOrder = MagicMock()

            # Execute with low max_attempts to speed up test
            result = await self.executor.execute_vertical_spread(
                self.test_signal,
                self.follower_id,
                max_attempts=2,
                attempt_interval=0.1,
                timeout_per_attempt=0.1,
            )

            # Check that order was rejected due to exhausted attempts
            self.assertEqual(result["status"], OrderStatus.REJECTED)
            self.assertIn("attempts exhausted", result["error"])

            # Check Redis for alert
            alerts = await fake_redis.xread({"alerts": 0})
            self.assertEqual(len(alerts), 1)

            # Parse and verify alert
            stream_name, messages = alerts[0]
            message_id, data = messages[0]
            alert_json = data[b"alert"]
            alert_data = json.loads(alert_json)

            # Verify alert content
            self.assertEqual(alert_data["event_type"], AlertType.LIMIT_REACHED.value)
            self.assertIn("attempts exhausted", alert_data["message"])
            self.assertEqual(alert_data["params"]["follower_id"], self.follower_id)
            self.assertEqual(alert_data["params"]["max_attempts"], 2)

    async def test_ib_rejection_alert(self):
        """Test that IB rejection/error triggers GATEWAY_UNREACHABLE alert."""
        # Create fake Redis instance
        fake_redis = fakeredis.FakeRedis(decode_responses=True)

        with patch("redis.asyncio.from_url", return_value=fake_redis):
            # Mock connection failure
            self.mock_ibkr_client.ensure_connected = AsyncMock(return_value=False)

            # Execute and expect failure
            result = await self.executor.execute_vertical_spread(self.test_signal, self.follower_id)

            # Check that order was rejected
            self.assertEqual(result["status"], OrderStatus.REJECTED)

            # Check Redis for alert
            alerts = await fake_redis.xread({"alerts": 0})
            self.assertEqual(len(alerts), 1)

            # Parse and verify alert
            stream_name, messages = alerts[0]
            message_id, data = messages[0]
            alert_json = data[b"alert"]
            alert_data = json.loads(alert_json)

            # Verify alert content
            self.assertEqual(alert_data["event_type"], AlertType.GATEWAY_UNREACHABLE.value)
            self.assertIn("Execution error", alert_data["message"])
            self.assertEqual(alert_data["params"]["follower_id"], self.follower_id)

    async def test_redis_connection_handling(self):
        """Test Redis connection and disconnection."""
        fake_redis = fakeredis.FakeRedis(decode_responses=True)

        with patch("redis.asyncio.from_url", return_value=fake_redis) as mock_from_url:
            # Test connection
            await self.executor.connect_redis()
            mock_from_url.assert_called_once_with("redis://fake", decode_responses=True)
            self.assertIsNotNone(self.executor.redis_client)

            # Test disconnection
            with patch.object(fake_redis, "close", new_callable=AsyncMock) as mock_close:
                await self.executor.disconnect_redis()
                mock_close.assert_called_once()
                self.assertIsNone(self.executor.redis_client)

    async def test_context_manager(self):
        """Test executor as async context manager."""
        fake_redis = fakeredis.FakeRedis(decode_responses=True)

        with patch("redis.asyncio.from_url", return_value=fake_redis):
            async with self.executor as executor:
                self.assertIsNotNone(executor.redis_client)

            # Should be disconnected after context exit
            self.assertIsNone(self.executor.redis_client)


if __name__ == "__main__":
    # Run async tests
    import asyncio

    async def run_tests():
        test_instance = TestVerticalSpreadExecutorRedisAlerts()
        test_instance.setUp()

        print("Testing margin fail alert...")
        await test_instance.test_margin_fail_alert()

        test_instance.setUp()
        print("Testing MID price threshold alert...")
        await test_instance.test_mid_price_threshold_alert()

        test_instance.setUp()
        print("Testing ladder exhausted alert...")
        await test_instance.test_ladder_exhausted_alert()

        test_instance.setUp()
        print("Testing IB rejection alert...")
        await test_instance.test_ib_rejection_alert()

        test_instance.setUp()
        print("Testing Redis connection handling...")
        await test_instance.test_redis_connection_handling()

        test_instance.setUp()
        print("Testing context manager...")
        await test_instance.test_context_manager()

        print("All tests passed!")

    asyncio.run(run_tests())

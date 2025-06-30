"""Unit tests for the VerticalSpreadExecutor."""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../../spreadpilot-core"))

from app.service.executor import VerticalSpreadExecutor

from spreadpilot_core.ibkr.client import IBKRClient, OrderStatus
from spreadpilot_core.models.alert import AlertSeverity


class TestVerticalSpreadExecutor(unittest.TestCase):
    """Test cases for the VerticalSpreadExecutor."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock IBKR client
        self.mock_ibkr_client = MagicMock(spec=IBKRClient)
        self.mock_ibkr_client.ib = MagicMock()
        self.mock_ibkr_client.ensure_connected = AsyncMock(return_value=True)
        self.mock_ibkr_client._get_qqq_option_contract = MagicMock()
        self.mock_ibkr_client.get_market_price = AsyncMock()
        self.mock_ibkr_client.get_account_summary = AsyncMock()

        # Create executor instance with fake Redis URL
        self.executor = VerticalSpreadExecutor(self.mock_ibkr_client, redis_url="redis://fake")

        # Test signal
        self.test_signal = {
            "strategy": "Long",
            "qty_per_leg": 1,
            "strike_long": 380.0,
            "strike_short": 385.0,
        }

        self.follower_id = "test-follower-123"

    async def test_execute_vertical_spread_success(self):
        """Test successful execution of vertical spread."""
        # Mock whatIf check
        mock_whatif_result = MagicMock()
        mock_whatif_result.initMarginChange = "500.0"
        mock_whatif_result.maintMarginChange = "400.0"
        mock_whatif_result.equityWithLoanAfter = "10000.0"

        self.mock_ibkr_client.ib.whatIfOrderAsync = AsyncMock(return_value=mock_whatif_result)
        self.mock_ibkr_client.get_account_summary = AsyncMock(
            return_value={"AvailableFunds": "1000.0"}
        )

        # Mock market price calculation
        self.mock_ibkr_client.get_market_price = AsyncMock(
            side_effect=[2.50, 3.25]
        )  # long_price, short_price

        # Mock successful order execution
        mock_trade = MagicMock()
        mock_trade.order.orderId = 12345
        mock_trade.orderStatus.status = "Filled"
        mock_trade.orderStatus.avgFillPrice = 0.75
        mock_trade.orderStatus.filled = 1

        self.mock_ibkr_client.ib.placeOrder = MagicMock(return_value=mock_trade)

        # Execute
        result = await self.executor.execute_vertical_spread(self.test_signal, self.follower_id)

        # Verify results
        self.assertEqual(result["status"], OrderStatus.FILLED)
        self.assertEqual(result["trade_id"], "12345")
        self.assertEqual(result["fill_price"], 0.75)
        self.assertEqual(result["follower_id"], self.follower_id)
        self.assertIn("fill_time", result)

    async def test_execute_vertical_spread_invalid_signal(self):
        """Test execution with invalid signal."""
        invalid_signal = {
            "strategy": "Long",
            # Missing required fields
        }

        result = await self.executor.execute_vertical_spread(invalid_signal, self.follower_id)

        self.assertEqual(result["status"], OrderStatus.REJECTED)
        self.assertIn("Invalid signal", result["error"])
        self.assertEqual(result["follower_id"], self.follower_id)

    async def test_execute_vertical_spread_margin_check_failure(self):
        """Test execution when margin check fails."""
        # Mock failed whatIf check
        mock_whatif_result = MagicMock()
        mock_whatif_result.initMarginChange = "1500.0"  # More than available
        mock_whatif_result.maintMarginChange = "1200.0"
        mock_whatif_result.equityWithLoanAfter = "8500.0"

        self.mock_ibkr_client.ib.whatIfOrderAsync = AsyncMock(return_value=mock_whatif_result)
        self.mock_ibkr_client.get_account_summary = AsyncMock(
            return_value={"AvailableFunds": "1000.0"}
        )

        # Mock _send_alert
        self.executor._send_alert = AsyncMock()

        result = await self.executor.execute_vertical_spread(self.test_signal, self.follower_id)

        self.assertEqual(result["status"], OrderStatus.REJECTED)
        self.assertIn("Margin check failed", result["error"])
        self.assertIn("margin_details", result)

        # Verify alert was sent
        self.executor._send_alert.assert_called_once()

    async def test_execute_vertical_spread_mid_price_below_threshold(self):
        """Test execution when MID price is below threshold."""
        # Mock successful margin check
        mock_whatif_result = MagicMock()
        mock_whatif_result.initMarginChange = "500.0"
        mock_whatif_result.maintMarginChange = "400.0"
        mock_whatif_result.equityWithLoanAfter = "10000.0"

        self.mock_ibkr_client.ib.whatIfOrderAsync = AsyncMock(return_value=mock_whatif_result)
        self.mock_ibkr_client.get_account_summary = AsyncMock(
            return_value={"AvailableFunds": "1000.0"}
        )

        # Mock market prices that result in low MID price
        self.mock_ibkr_client.get_market_price = AsyncMock(
            side_effect=[2.50, 2.60]
        )  # MID = 0.10 (below 0.70)

        # Mock _send_alert
        self.executor._send_alert = AsyncMock()

        result = await self.executor.execute_vertical_spread(self.test_signal, self.follower_id)

        self.assertEqual(result["status"], OrderStatus.REJECTED)
        self.assertIn("below minimum threshold", result["error"])
        self.assertEqual(result["mid_price"], 0.10)
        self.assertEqual(result["threshold"], 0.70)

        # Verify alert was sent
        self.executor._send_alert.assert_called_once()

    async def test_perform_whatif_margin_check_success(self):
        """Test successful whatIf margin check."""
        # Mock whatIf result
        mock_whatif_result = MagicMock()
        mock_whatif_result.initMarginChange = "500.0"
        mock_whatif_result.maintMarginChange = "400.0"
        mock_whatif_result.equityWithLoanAfter = "10000.0"

        self.mock_ibkr_client.ib.whatIfOrderAsync = AsyncMock(return_value=mock_whatif_result)
        self.mock_ibkr_client.get_account_summary = AsyncMock(
            return_value={"AvailableFunds": "1000.0"}
        )

        # Mock contract creation
        mock_contract = MagicMock()
        self.mock_ibkr_client._get_qqq_option_contract = MagicMock(return_value=mock_contract)

        result = await self.executor._perform_whatif_margin_check(
            "Long", 1, 380.0, 385.0, self.follower_id
        )

        self.assertTrue(result["success"])
        self.assertIsNone(result["error"])
        self.assertEqual(result["init_margin"], 500.0)
        self.assertEqual(result["available_funds"], 1000.0)

    async def test_perform_whatif_margin_check_insufficient_margin(self):
        """Test whatIf margin check with insufficient margin."""
        # Mock whatIf result with high margin requirement
        mock_whatif_result = MagicMock()
        mock_whatif_result.initMarginChange = "1500.0"  # More than available
        mock_whatif_result.maintMarginChange = "1200.0"
        mock_whatif_result.equityWithLoanAfter = "8500.0"

        self.mock_ibkr_client.ib.whatIfOrderAsync = AsyncMock(return_value=mock_whatif_result)
        self.mock_ibkr_client.get_account_summary = AsyncMock(
            return_value={"AvailableFunds": "1000.0"}
        )

        # Mock contract creation
        mock_contract = MagicMock()
        self.mock_ibkr_client._get_qqq_option_contract = MagicMock(return_value=mock_contract)

        result = await self.executor._perform_whatif_margin_check(
            "Long", 1, 380.0, 385.0, self.follower_id
        )

        self.assertFalse(result["success"])
        self.assertIn("Insufficient margin", result["error"])
        self.assertEqual(result["init_margin"], 1500.0)
        self.assertEqual(result["available_funds"], 1000.0)

    async def test_perform_whatif_margin_check_invalid_strategy(self):
        """Test whatIf margin check with invalid strategy."""
        result = await self.executor._perform_whatif_margin_check(
            "Invalid", 1, 380.0, 385.0, self.follower_id
        )

        self.assertFalse(result["success"])
        self.assertIn("Invalid strategy", result["error"])

    async def test_perform_whatif_margin_check_connection_failure(self):
        """Test whatIf margin check when not connected."""
        self.mock_ibkr_client.ensure_connected = AsyncMock(return_value=False)

        result = await self.executor._perform_whatif_margin_check(
            "Long", 1, 380.0, 385.0, self.follower_id
        )

        self.assertFalse(result["success"])
        self.assertIn("Not connected", result["error"])

    async def test_calculate_mid_price_success(self):
        """Test successful MID price calculation."""
        # Mock market prices
        self.mock_ibkr_client.get_market_price = AsyncMock(side_effect=[2.50, 3.25])  # long, short

        # Mock contract creation
        mock_contract = MagicMock()
        self.mock_ibkr_client._get_qqq_option_contract = MagicMock(return_value=mock_contract)

        result = await self.executor._calculate_mid_price("Long", 380.0, 385.0)

        self.assertTrue(result["success"])
        self.assertEqual(result["mid_price"], 0.75)  # 3.25 - 2.50
        self.assertEqual(result["long_price"], 2.50)
        self.assertEqual(result["short_price"], 3.25)

    async def test_calculate_mid_price_failed_market_data(self):
        """Test MID price calculation when market data fails."""
        # Mock failed market prices
        self.mock_ibkr_client.get_market_price = AsyncMock(side_effect=[None, 3.25])  # long fails

        # Mock contract creation
        mock_contract = MagicMock()
        self.mock_ibkr_client._get_qqq_option_contract = MagicMock(return_value=mock_contract)

        result = await self.executor._calculate_mid_price("Long", 380.0, 385.0)

        self.assertFalse(result["success"])
        self.assertIn("Failed to get market prices", result["error"])

    async def test_calculate_mid_price_invalid_strategy(self):
        """Test MID price calculation with invalid strategy."""
        result = await self.executor._calculate_mid_price("Invalid", 380.0, 385.0)

        self.assertFalse(result["success"])
        self.assertIn("Invalid strategy", result["error"])

    async def test_execute_limit_ladder_immediate_fill(self):
        """Test limit-ladder execution with immediate fill."""
        # Mock contract creation
        mock_contract = MagicMock()
        self.mock_ibkr_client._get_qqq_option_contract = MagicMock(return_value=mock_contract)

        # Mock successful order execution
        mock_trade = MagicMock()
        mock_trade.order.orderId = 12345
        mock_trade.orderStatus.status = "Filled"
        mock_trade.orderStatus.avgFillPrice = 0.75
        mock_trade.orderStatus.filled = 1

        self.mock_ibkr_client.ib.placeOrder = MagicMock(return_value=mock_trade)

        result = await self.executor._execute_limit_ladder(
            strategy="Long",
            qty_per_leg=1,
            strike_long=380.0,
            strike_short=385.0,
            initial_mid_price=0.75,
            max_attempts=5,
            price_increment=0.01,
            min_price_threshold=0.70,
            attempt_interval=1,  # Short for testing
            timeout_per_attempt=1,  # Short for testing
            follower_id=self.follower_id,
        )

        self.assertEqual(result["status"], OrderStatus.FILLED)
        self.assertEqual(result["trade_id"], "12345")
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(result["fill_price"], 0.75)

    async def test_execute_limit_ladder_price_below_threshold(self):
        """Test limit-ladder execution when price falls below threshold."""
        # Mock _send_alert
        self.executor._send_alert = AsyncMock()

        result = await self.executor._execute_limit_ladder(
            strategy="Long",
            qty_per_leg=1,
            strike_long=380.0,
            strike_short=385.0,
            initial_mid_price=0.65,  # Below threshold
            max_attempts=5,
            price_increment=0.01,
            min_price_threshold=0.70,
            attempt_interval=1,
            timeout_per_attempt=1,
            follower_id=self.follower_id,
        )

        self.assertEqual(result["status"], OrderStatus.CANCELED)
        self.assertIn("below threshold", result["error"])
        self.executor._send_alert.assert_called_once()

    async def test_execute_limit_ladder_all_attempts_exhausted(self):
        """Test limit-ladder execution when all attempts are exhausted."""
        # Mock contract creation
        mock_contract = MagicMock()
        self.mock_ibkr_client._get_qqq_option_contract = MagicMock(return_value=mock_contract)

        # Mock unfilled orders
        mock_trade = MagicMock()
        mock_trade.order.orderId = 12345
        mock_trade.orderStatus.status = "Submitted"  # Not filled
        mock_trade.orderStatus.filled = 0

        self.mock_ibkr_client.ib.placeOrder = MagicMock(return_value=mock_trade)
        self.mock_ibkr_client.ib.cancelOrder = MagicMock()

        # Mock _send_alert
        self.executor._send_alert = AsyncMock()

        result = await self.executor._execute_limit_ladder(
            strategy="Long",
            qty_per_leg=1,
            strike_long=380.0,
            strike_short=385.0,
            initial_mid_price=0.75,
            max_attempts=2,  # Small for testing
            price_increment=0.01,
            min_price_threshold=0.70,
            attempt_interval=0.1,  # Short for testing
            timeout_per_attempt=0.1,  # Short for testing
            follower_id=self.follower_id,
        )

        self.assertEqual(result["status"], OrderStatus.REJECTED)
        self.assertIn("attempts exhausted", result["error"])
        self.assertEqual(result["attempts"], 2)

        # Verify alert was sent
        self.executor._send_alert.assert_called_once()

    async def test_execute_limit_ladder_partial_fill(self):
        """Test limit-ladder execution with partial fill."""
        # Mock contract creation
        mock_contract = MagicMock()
        self.mock_ibkr_client._get_qqq_option_contract = MagicMock(return_value=mock_contract)

        # Mock partial fill
        mock_trade = MagicMock()
        mock_trade.order.orderId = 12345
        mock_trade.orderStatus.status = "Submitted"
        mock_trade.orderStatus.avgFillPrice = 0.75
        mock_trade.orderStatus.filled = 1
        mock_trade.orderStatus.remaining = 1

        self.mock_ibkr_client.ib.placeOrder = MagicMock(return_value=mock_trade)

        result = await self.executor._execute_limit_ladder(
            strategy="Long",
            qty_per_leg=2,  # Order for 2, fill 1
            strike_long=380.0,
            strike_short=385.0,
            initial_mid_price=0.75,
            max_attempts=5,
            price_increment=0.01,
            min_price_threshold=0.70,
            attempt_interval=0.1,
            timeout_per_attempt=0.1,
            follower_id=self.follower_id,
        )

        self.assertEqual(result["status"], OrderStatus.PARTIAL)
        self.assertEqual(result["filled_quantity"], 1)
        self.assertEqual(result["remaining_quantity"], 1)

    async def test_send_alert(self):
        """Test alert sending functionality."""
        # Test that _send_alert doesn't raise exceptions
        await self.executor._send_alert("Test message", AlertSeverity.MEDIUM, self.follower_id)

        # This test primarily ensures the method doesn't crash
        # In a real implementation, we would verify the alert was sent to the alert system

    def test_executor_initialization(self):
        """Test executor initialization."""
        executor = VerticalSpreadExecutor(self.mock_ibkr_client)
        self.assertEqual(executor.ibkr_client, self.mock_ibkr_client)

    async def test_execute_vertical_spread_bear_call_strategy(self):
        """Test execution with Bear Call (Short) strategy."""
        # Modify signal for Bear Call
        bear_call_signal = {
            "strategy": "Short",  # Bear Call
            "qty_per_leg": 1,
            "strike_long": 390.0,  # Higher strike for Bear Call
            "strike_short": 385.0,  # Lower strike for Bear Call
        }

        # Mock whatIf check
        mock_whatif_result = MagicMock()
        mock_whatif_result.initMarginChange = "500.0"
        mock_whatif_result.maintMarginChange = "400.0"
        mock_whatif_result.equityWithLoanAfter = "10000.0"

        self.mock_ibkr_client.ib.whatIfOrderAsync = AsyncMock(return_value=mock_whatif_result)
        self.mock_ibkr_client.get_account_summary = AsyncMock(
            return_value={"AvailableFunds": "1000.0"}
        )

        # Mock market price calculation for calls
        self.mock_ibkr_client.get_market_price = AsyncMock(
            side_effect=[1.50, 2.25]
        )  # long_price, short_price

        # Mock successful order execution
        mock_trade = MagicMock()
        mock_trade.order.orderId = 12346
        mock_trade.orderStatus.status = "Filled"
        mock_trade.orderStatus.avgFillPrice = 0.75
        mock_trade.orderStatus.filled = 1

        self.mock_ibkr_client.ib.placeOrder = MagicMock(return_value=mock_trade)

        # Execute
        result = await self.executor.execute_vertical_spread(bear_call_signal, self.follower_id)

        # Verify results
        self.assertEqual(result["status"], OrderStatus.FILLED)
        self.assertEqual(result["strategy"], "Short")
        self.assertEqual(result["strikes"]["long"], 390.0)
        self.assertEqual(result["strikes"]["short"], 385.0)

    async def test_execute_vertical_spread_exception_handling(self):
        """Test execution with unexpected exception."""
        # Mock an exception during execution
        self.mock_ibkr_client.ensure_connected = AsyncMock(
            side_effect=Exception("Connection error")
        )

        # Mock _send_alert
        self.executor._send_alert = AsyncMock()

        result = await self.executor.execute_vertical_spread(self.test_signal, self.follower_id)

        self.assertEqual(result["status"], OrderStatus.REJECTED)
        self.assertIn("Execution error", result["error"])
        self.assertEqual(result["follower_id"], self.follower_id)

        # Verify alert was sent
        self.executor._send_alert.assert_called_once()

    async def test_execute_vertical_spread_whatif_no_result(self):
        """Test execution when whatIf returns no result."""
        # Mock empty whatIf result
        self.mock_ibkr_client.ib.whatIfOrderAsync = AsyncMock(return_value=None)

        result = await self.executor.execute_vertical_spread(self.test_signal, self.follower_id)

        self.assertEqual(result["status"], OrderStatus.REJECTED)
        self.assertIn("Margin check failed", result["error"])

    async def test_execute_limit_ladder_incremental_pricing(self):
        """Test that limit-ladder correctly increments pricing."""
        # Mock contract creation
        mock_contract = MagicMock()
        self.mock_ibkr_client._get_qqq_option_contract = MagicMock(return_value=mock_contract)

        # Track the limit prices used
        used_prices = []

        def mock_place_order(contract, order):
            used_prices.append(order.lmtPrice)
            mock_trade = MagicMock()
            mock_trade.order.orderId = len(used_prices)
            mock_trade.orderStatus.status = "Submitted" if len(used_prices) < 3 else "Filled"
            mock_trade.orderStatus.avgFillPrice = order.lmtPrice
            mock_trade.orderStatus.filled = 1 if mock_trade.orderStatus.status == "Filled" else 0
            return mock_trade

        self.mock_ibkr_client.ib.placeOrder = MagicMock(side_effect=mock_place_order)
        self.mock_ibkr_client.ib.cancelOrder = MagicMock()

        result = await self.executor._execute_limit_ladder(
            strategy="Long",
            qty_per_leg=1,
            strike_long=380.0,
            strike_short=385.0,
            initial_mid_price=0.75,
            max_attempts=5,
            price_increment=0.01,
            min_price_threshold=0.70,
            attempt_interval=0.1,
            timeout_per_attempt=0.1,
            follower_id=self.follower_id,
        )

        # Verify price increments
        self.assertEqual(len(used_prices), 3)  # Should fill on 3rd attempt
        self.assertEqual(used_prices[0], 0.75)  # Initial
        self.assertEqual(used_prices[1], 0.76)  # +0.01
        self.assertEqual(used_prices[2], 0.77)  # +0.01 again

        self.assertEqual(result["status"], OrderStatus.FILLED)
        self.assertEqual(result["attempts"], 3)

    def test_convenience_function_not_implemented(self):
        """Test the convenience function raises NotImplementedError."""
        from trading_bot.app.service.executor import execute_vertical_spread

        with self.assertRaises(NotImplementedError):
            asyncio.run(execute_vertical_spread(self.test_signal, self.follower_id))


# Async test runner
class AsyncTestRunner:
    """Helper to run async tests."""

    @staticmethod
    def run_async_test(test_method):
        """Run an async test method."""

        def wrapper(self):
            return asyncio.run(test_method(self))

        return wrapper


# Apply async wrapper to test methods
for attr_name in dir(TestVerticalSpreadExecutor):
    if attr_name.startswith("test_") and "async" in attr_name:
        attr = getattr(TestVerticalSpreadExecutor, attr_name)
        if asyncio.iscoroutinefunction(attr):
            setattr(
                TestVerticalSpreadExecutor,
                attr_name,
                AsyncTestRunner.run_async_test(attr),
            )


if __name__ == "__main__":
    unittest.main()

"""Unit tests for the Vertical Spreads Strategy Handler."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from trading_bot.app.service.vertical_spreads_strategy_handler import (
    VerticalSpreadsStrategyHandler,
)


class TestVerticalSpreadsStrategyHandler(unittest.TestCase):
    """Test cases for the Vertical Spreads Strategy Handler."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = MagicMock()
        self.service.settings = MagicMock()
        self.service.settings.ib_gateway_host = "localhost"
        self.service.settings.ib_gateway_port = 4002
        self.service.settings.ib_client_id = 1
        self.service.settings.ib_trading_mode = "paper"

        self.config = {
            "enabled": True,
            "ibkr_secret_ref": "ibkr_vertical_spreads_strategy",
            "symbol": "QQQ",
            "signal_time": "09:27:00",
            "max_attempts": 10,
            "price_increment": 0.01,
            "min_price": 0.70,
            "timeout_seconds": 5,
            "time_value_threshold": 0.10,
            "time_value_check_interval": 60,
        }

        self.handler = VerticalSpreadsStrategyHandler(self.service, self.config)
        self.handler.ibkr_client = AsyncMock()
        self.handler._initialized = True

    @patch("trading_bot.app.service.vertical_spreads_strategy_handler.get_ny_time")
    async def test_process_signal(self, mock_get_ny_time):
        """Test processing a valid signal."""
        # Mock the necessary methods
        self.handler._check_margin_for_trade = AsyncMock(return_value=(True, None))
        self.handler._place_vertical_spread = AsyncMock(
            return_value={"status": "FILLED", "fill_price": 0.75}
        )
        self.handler._send_alert = AsyncMock()

        # Create a test signal
        signal = {
            "ticker": "QQQ",
            "strategy": "Long",
            "qty_per_leg": 1,
            "strike_long": 380.0,
            "strike_short": 385.0,
        }

        # Process the signal
        await self.handler._process_signal(signal)

        # Verify the methods were called with correct arguments
        self.handler._check_margin_for_trade.assert_called_once_with(
            strategy="Long", qty_per_leg=1, strike_long=380.0, strike_short=385.0
        )

        self.handler._place_vertical_spread.assert_called_once_with(
            strategy="Long", qty_per_leg=1, strike_long=380.0, strike_short=385.0
        )

        self.handler._send_alert.assert_called_once_with(
            symbol="QQQ",
            action="BUY",
            quantity=1,
            price=0.75,
            order_type="LMT",
            signal_type="Long Vertical Spread",
        )

    @patch("trading_bot.app.service.vertical_spreads_strategy_handler.get_ny_time")
    async def test_process_signal_invalid_ticker(self, mock_get_ny_time):
        """Test processing a signal with invalid ticker."""
        # Create a test signal with invalid ticker
        signal = {
            "ticker": "SPY",  # Not QQQ
            "strategy": "Long",
            "qty_per_leg": 1,
            "strike_long": 380.0,
            "strike_short": 385.0,
        }

        # Mock the methods that should not be called
        self.handler._check_margin_for_trade = AsyncMock()
        self.handler._place_vertical_spread = AsyncMock()
        self.handler._send_alert = AsyncMock()

        # Process the signal
        await self.handler._process_signal(signal)

        # Verify the methods were not called
        self.handler._check_margin_for_trade.assert_not_called()
        self.handler._place_vertical_spread.assert_not_called()
        self.handler._send_alert.assert_not_called()

    @patch("trading_bot.app.service.vertical_spreads_strategy_handler.get_ny_time")
    async def test_process_signal_insufficient_margin(self, mock_get_ny_time):
        """Test processing a signal with insufficient margin."""
        # Mock the necessary methods
        self.handler._check_margin_for_trade = AsyncMock(return_value=(False, "Insufficient funds"))
        self.handler._place_vertical_spread = AsyncMock()
        self.handler._send_alert = AsyncMock()

        # Create a test signal
        signal = {
            "ticker": "QQQ",
            "strategy": "Long",
            "qty_per_leg": 1,
            "strike_long": 380.0,
            "strike_short": 385.0,
        }

        # Process the signal
        await self.handler._process_signal(signal)

        # Verify the methods were called correctly
        self.handler._check_margin_for_trade.assert_called_once()
        self.handler._place_vertical_spread.assert_not_called()
        self.handler._send_alert.assert_not_called()

    async def test_calculate_time_value(self):
        """Test calculating time value for an option position."""
        # Mock the necessary methods
        self.handler.ibkr_client._get_qqq_option_contract = MagicMock()
        self.handler.ibkr_client.get_market_price = AsyncMock(
            side_effect=[1.50, 390.0]
        )  # Option price, underlying price
        self.handler.ibkr_client.get_stock_contract = AsyncMock()

        # Calculate time value for a call option
        time_value = await self.handler._calculate_time_value("QQQ-380-C", 1)

        # Expected time value: option price - intrinsic value = 1.50 - (390 - 380) = 1.50 - 10 = -8.50
        # But since time value can't be negative, it should be 0
        self.assertIsNotNone(time_value)
        self.assertEqual(time_value, 0)

        # Reset mocks
        self.handler.ibkr_client.get_market_price.reset_mock()
        self.handler.ibkr_client.get_market_price.side_effect = [
            1.50,
            370.0,
        ]  # Option price, underlying price

        # Calculate time value for a put option
        time_value = await self.handler._calculate_time_value("QQQ-380-P", 1)

        # Expected time value: option price - intrinsic value = 1.50 - (380 - 370) = 1.50 - 10 = -8.50
        # But since time value can't be negative, it should be 0
        self.assertIsNotNone(time_value)
        self.assertEqual(time_value, 0)

    @patch("trading_bot.app.service.vertical_spreads_strategy_handler.get_ny_time")
    async def test_monitor_time_value_closes_position(self, mock_get_ny_time):
        """Test that monitor_time_value closes positions when time value is below threshold."""
        # Mock the necessary methods
        self.handler.ibkr_client.get_positions = AsyncMock(return_value={"QQQ-380-C": 1})
        self.handler._calculate_time_value = AsyncMock(return_value=0.05)  # Below threshold
        self.handler._close_position = AsyncMock()

        # Monitor time value
        await self.handler._monitor_time_value()

        # Verify the methods were called correctly
        self.handler.ibkr_client.get_positions.assert_called_once()
        self.handler._calculate_time_value.assert_called_once_with("QQQ-380-C", 1)
        self.handler._close_position.assert_called_once_with("QQQ-380-C", 1)

    @patch("trading_bot.app.service.vertical_spreads_strategy_handler.get_ny_time")
    async def test_monitor_time_value_keeps_position(self, mock_get_ny_time):
        """Test that monitor_time_value keeps positions when time value is above threshold."""
        # Mock the necessary methods
        self.handler.ibkr_client.get_positions = AsyncMock(return_value={"QQQ-380-C": 1})
        self.handler._calculate_time_value = AsyncMock(return_value=0.15)  # Above threshold
        self.handler._close_position = AsyncMock()

        # Monitor time value
        await self.handler._monitor_time_value()

        # Verify the methods were called correctly
        self.handler.ibkr_client.get_positions.assert_called_once()
        self.handler._calculate_time_value.assert_called_once_with("QQQ-380-C", 1)
        self.handler._close_position.assert_not_called()


if __name__ == "__main__":
    unittest.main()

"""Integration tests for the Vertical Spreads Strategy."""

import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from trading_bot.app.config import VERTICAL_SPREADS_STRATEGY, Settings
from trading_bot.app.service.base import TradingService
from trading_bot.app.sheets import GoogleSheetsClient


@pytest.mark.asyncio
async def test_vertical_spreads_strategy_initialization():
    """Test that the Vertical Spreads Strategy initializes correctly."""
    # Mock settings and sheets client
    settings = MagicMock(spec=Settings)
    settings.ib_gateway_host = "localhost"
    settings.ib_gateway_port = 4002
    settings.ib_client_id = 1
    settings.ib_trading_mode = "paper"

    sheets_client = MagicMock(spec=GoogleSheetsClient)
    sheets_client.is_connected.return_value = True

    # Create a mock MongoDB client
    mongo_client = AsyncMock(spec=AsyncIOMotorClient)
    mongo_db = AsyncMock()
    mongo_client.__getitem__.return_value = mongo_db

    # Create a trading service with mocked dependencies
    with (
        patch(
            "trading_bot.app.service.base.connect_to_mongo", return_value=mongo_client
        ),
        patch("trading_bot.app.service.base.get_mongo_db", return_value=mongo_db),
    ):
        service = TradingService(settings, sheets_client)
        service.mongo_db = mongo_db

        # Mock the IBKR client in the vertical spreads strategy handler
        service.vertical_spreads_strategy_handler.ibkr_client = AsyncMock()
        service.vertical_spreads_strategy_handler.ibkr_client.connect = AsyncMock(
            return_value=True
        )
        service.vertical_spreads_strategy_handler.ibkr_client.is_connected = AsyncMock(
            return_value=True
        )
        service.vertical_spreads_strategy_handler.ibkr_client.get_positions = AsyncMock(
            return_value={}
        )

        # Initialize the vertical spreads strategy handler
        await service.vertical_spreads_strategy_handler.initialize()

        # Verify that the handler was initialized correctly
        assert service.vertical_spreads_strategy_handler._initialized is True


@pytest.mark.asyncio
async def test_vertical_spreads_strategy_signal_processing():
    """Test that the Vertical Spreads Strategy processes signals correctly."""
    # Mock settings and sheets client
    settings = MagicMock(spec=Settings)
    settings.ib_gateway_host = "localhost"
    settings.ib_gateway_port = 4002
    settings.ib_client_id = 1
    settings.ib_trading_mode = "paper"

    sheets_client = MagicMock(spec=GoogleSheetsClient)
    sheets_client.is_connected.return_value = True

    # Create a mock signal
    signal = {
        "ticker": "QQQ",
        "strategy": "Long",
        "qty_per_leg": 1,
        "strike_long": 380.0,
        "strike_short": 385.0,
    }
    sheets_client.fetch_signal = AsyncMock(return_value=signal)

    # Create a mock MongoDB client
    mongo_client = AsyncMock(spec=AsyncIOMotorClient)
    mongo_db = AsyncMock()
    mongo_client.__getitem__.return_value = mongo_db

    # Create a trading service with mocked dependencies
    with (
        patch(
            "trading_bot.app.service.base.connect_to_mongo", return_value=mongo_client
        ),
        patch("trading_bot.app.service.base.get_mongo_db", return_value=mongo_db),
        patch(
            "trading_bot.app.service.vertical_spreads_strategy_handler.get_ny_time"
        ) as mock_get_ny_time,
    ):

        # Mock NY time to be 9:27 AM
        mock_time = datetime.datetime(2025, 5, 19, 9, 27, 0)
        mock_get_ny_time.return_value = mock_time

        service = TradingService(settings, sheets_client)
        service.mongo_db = mongo_db

        # Mock the IBKR client in the vertical spreads strategy handler
        service.vertical_spreads_strategy_handler.ibkr_client = AsyncMock()
        service.vertical_spreads_strategy_handler.ibkr_client.connect = AsyncMock(
            return_value=True
        )
        service.vertical_spreads_strategy_handler.ibkr_client.is_connected = AsyncMock(
            return_value=True
        )
        service.vertical_spreads_strategy_handler.ibkr_client.get_positions = AsyncMock(
            return_value={}
        )
        service.vertical_spreads_strategy_handler.ibkr_client.check_margin_for_trade = (
            AsyncMock(return_value=(True, None))
        )
        service.vertical_spreads_strategy_handler.ibkr_client.place_vertical_spread = (
            AsyncMock(
                return_value={
                    "status": "FILLED",
                    "trade_id": "123456",
                    "fill_price": 0.75,
                    "fill_time": datetime.datetime.now().isoformat(),
                }
            )
        )

        # Mock the alert manager
        service.alert_manager = AsyncMock()
        service.alert_manager.create_alert = AsyncMock()

        # Initialize the vertical spreads strategy handler
        await service.vertical_spreads_strategy_handler.initialize()

        # Create a shutdown event
        shutdown_event = asyncio.Event()

        # Run the strategy handler for a short time
        task = asyncio.create_task(
            service.vertical_spreads_strategy_handler.run(shutdown_event)
        )

        # Wait a short time for the handler to process the signal
        await asyncio.sleep(0.1)

        # Set the shutdown event to stop the handler
        shutdown_event.set()

        # Wait for the handler to stop
        await task

        # Verify that the signal was processed correctly
        sheets_client.fetch_signal.assert_called_once()
        service.vertical_spreads_strategy_handler.ibkr_client.check_margin_for_trade.assert_called_once_with(
            strategy="Long", qty_per_leg=1, strike_long=380.0, strike_short=385.0
        )
        service.vertical_spreads_strategy_handler.ibkr_client.place_vertical_spread.assert_called_once_with(
            strategy="Long",
            qty_per_leg=1,
            strike_long=380.0,
            strike_short=385.0,
            max_attempts=VERTICAL_SPREADS_STRATEGY["max_attempts"],
            price_increment=VERTICAL_SPREADS_STRATEGY["price_increment"],
            min_price=VERTICAL_SPREADS_STRATEGY["min_price"],
            timeout_seconds=VERTICAL_SPREADS_STRATEGY["timeout_seconds"],
        )
        service.alert_manager.create_alert.assert_called_once()


@pytest.mark.asyncio
async def test_vertical_spreads_strategy_time_value_monitoring():
    """Test that the Vertical Spreads Strategy monitors time value correctly."""
    # Mock settings and sheets client
    settings = MagicMock(spec=Settings)
    settings.ib_gateway_host = "localhost"
    settings.ib_gateway_port = 4002
    settings.ib_client_id = 1
    settings.ib_trading_mode = "paper"

    sheets_client = MagicMock(spec=GoogleSheetsClient)
    sheets_client.is_connected.return_value = True
    sheets_client.fetch_signal = AsyncMock(return_value=None)

    # Create a mock MongoDB client
    mongo_client = AsyncMock(spec=AsyncIOMotorClient)
    mongo_db = AsyncMock()
    mongo_client.__getitem__.return_value = mongo_db

    # Create a trading service with mocked dependencies
    with (
        patch(
            "trading_bot.app.service.base.connect_to_mongo", return_value=mongo_client
        ),
        patch("trading_bot.app.service.base.get_mongo_db", return_value=mongo_db),
        patch(
            "trading_bot.app.service.vertical_spreads_strategy_handler.get_ny_time"
        ) as mock_get_ny_time,
    ):

        # Mock NY time to be during trading hours
        mock_time = datetime.datetime(2025, 5, 19, 10, 30, 0)
        mock_get_ny_time.return_value = mock_time

        service = TradingService(settings, sheets_client)
        service.mongo_db = mongo_db

        # Mock the IBKR client in the vertical spreads strategy handler
        service.vertical_spreads_strategy_handler.ibkr_client = AsyncMock()
        service.vertical_spreads_strategy_handler.ibkr_client.connect = AsyncMock(
            return_value=True
        )
        service.vertical_spreads_strategy_handler.ibkr_client.is_connected = AsyncMock(
            return_value=True
        )
        service.vertical_spreads_strategy_handler.ibkr_client.get_positions = AsyncMock(
            return_value={"QQQ-380-C": 1}
        )

        # Mock the time value calculation to return a value below the threshold
        service.vertical_spreads_strategy_handler._calculate_time_value = AsyncMock(
            return_value=0.05
        )
        service.vertical_spreads_strategy_handler._close_position = AsyncMock()

        # Mock the alert manager
        service.alert_manager = AsyncMock()
        service.alert_manager.create_alert = AsyncMock()

        # Initialize the vertical spreads strategy handler
        await service.vertical_spreads_strategy_handler.initialize()

        # Create a shutdown event
        shutdown_event = asyncio.Event()

        # Run the strategy handler for a short time
        task = asyncio.create_task(
            service.vertical_spreads_strategy_handler.run(shutdown_event)
        )

        # Wait a short time for the handler to monitor time value
        await asyncio.sleep(0.1)

        # Set the shutdown event to stop the handler
        shutdown_event.set()

        # Wait for the handler to stop
        await task

        # Verify that the time value was monitored correctly
        service.vertical_spreads_strategy_handler.ibkr_client.get_positions.assert_called()
        service.vertical_spreads_strategy_handler._calculate_time_value.assert_called_once_with(
            "QQQ-380-C", 1
        )
        service.vertical_spreads_strategy_handler._close_position.assert_called_once_with(
            "QQQ-380-C", 1
        )

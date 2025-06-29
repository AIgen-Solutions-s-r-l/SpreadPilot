import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ib_insync import BarData, Stock
from trading_bot.app.config import ORIGINAL_EMA_STRATEGY, Settings
from trading_bot.app.service.base import TradingService
from trading_bot.app.sheets import GoogleSheetsClient

from spreadpilot_core.ibkr.client import IBKRClient

# Mock data
MOCK_STOCK_CONTRACT = Stock(symbol="SOXS", exchange="SMART", currency="USD", conId=123)

MOCK_BAR_DATA = [
    BarData(
        date=datetime.datetime(2025, 4, 18, 10, 0, 0),
        open=20.0,
        high=21.0,
        low=19.0,
        close=20.5,
        volume=1000,
        average=20.2,
        barCount=100,
    ),
    BarData(
        date=datetime.datetime(2025, 4, 18, 10, 5, 0),
        open=20.5,
        high=21.5,
        low=20.0,
        close=21.0,
        volume=1200,
        average=20.8,
        barCount=120,
    ),
]


# Mock IBKR server responses
class MockIBKRServer:
    """Mock IBKR server for integration testing."""

    def __init__(self):
        self.positions = {"SOXS": 0, "SOXL": 0}
        self.orders = []
        self.historical_data = {"SOXS": MOCK_BAR_DATA, "SOXL": MOCK_BAR_DATA}
        self.contracts = {
            "SOXS": MOCK_STOCK_CONTRACT,
            "SOXL": Stock(symbol="SOXL", exchange="SMART", currency="USD", conId=456),
        }

    def get_positions(self):
        """Return current positions."""
        return [
            MagicMock(contract=Stock(symbol=symbol), position=qty)
            for symbol, qty in self.positions.items()
        ]

    def get_contract(self, symbol):
        """Return contract for symbol."""
        return self.contracts.get(symbol)

    def get_historical_data(self, symbol, duration, bar_size):
        """Return historical data for symbol."""
        return self.historical_data.get(symbol, [])

    def place_order(self, contract, order):
        """Place an order and update positions."""
        self.orders.append((contract, order))

        # Update positions based on order
        symbol = contract.symbol
        if symbol in self.positions:
            if order.action == "BUY":
                self.positions[symbol] += order.totalQuantity
            elif order.action == "SELL":
                self.positions[symbol] -= order.totalQuantity

        return MagicMock(orderStatus=MagicMock(status="Filled"))


# Fixtures


@pytest.fixture
def mock_ibkr_server():
    """Fixture to create a mock IBKR server."""
    return MockIBKRServer()


@pytest.fixture
def mock_ibkr_client(mock_ibkr_server):
    """Fixture to create a mock IBKRClient that uses the mock server."""
    client = MagicMock(spec=IBKRClient)
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    client.is_connected = MagicMock(return_value=True)

    # Link to mock server
    client.get_positions = AsyncMock(
        side_effect=lambda: mock_ibkr_server.get_positions()
    )
    client.get_contract_details = AsyncMock(
        side_effect=lambda symbol, **kwargs: [
            MagicMock(contract=mock_ibkr_server.get_contract(symbol))
        ]
    )
    client.get_historical_data = AsyncMock(
        side_effect=lambda contract, **kwargs: mock_ibkr_server.get_historical_data(
            contract.symbol,
            kwargs.get("duration_str", "1 D"),
            kwargs.get("bar_size_setting", "5 mins"),
        )
    )
    client.place_order = AsyncMock(
        side_effect=lambda contract, order: mock_ibkr_server.place_order(
            contract, order
        )
    )

    return client


@pytest.fixture
def mock_sheets_client():
    """Fixture to create a mock GoogleSheetsClient."""
    client = MagicMock(spec=GoogleSheetsClient)
    client.connect = AsyncMock(return_value=True)
    client.is_connected = MagicMock(return_value=True)
    client.fetch_signal = AsyncMock(return_value=None)  # No signals for this test
    return client


@pytest.fixture
def mock_settings():
    """Fixture to create mock settings."""
    settings = MagicMock(spec=Settings)
    settings.ib_gateway_host = "127.0.0.1"
    settings.ib_gateway_port = 4002
    settings.ib_client_id = 1
    settings.ib_trading_mode = "paper"
    settings.project_id = "test-project"
    return settings


@pytest.fixture
async def trading_service(mock_settings, mock_sheets_client):
    """Fixture to create a TradingService with mocked dependencies."""
    # Patch Firebase and Secret Manager
    with patch("trading_bot.app.service.base.firebase_admin.initialize_app"):
        with patch("trading_bot.app.service.base.firestore.client"):
            with patch(
                "trading_bot.app.service.base.secretmanager.SecretManagerServiceClient"
            ):
                service = TradingService(mock_settings, mock_sheets_client)
                # Mock DB and secret client
                service.db = MagicMock()
                service.secret_client = MagicMock()
                service.get_secret = AsyncMock(return_value="test_secret")

                # Mock alert manager
                service.alert_manager = MagicMock()
                service.alert_manager.create_alert = AsyncMock()

                yield service


# Integration Tests


@pytest.mark.asyncio
async def test_original_strategy_initialization(trading_service, mock_ibkr_client):
    """Test that the OriginalStrategyHandler initializes correctly within TradingService."""
    # Patch the IBKRClient creation
    with patch(
        "trading_bot.app.service.original_strategy_handler.IBKRClient",
        return_value=mock_ibkr_client,
    ):
        # Initialize the handler
        await trading_service.original_strategy_handler.initialize()

        # Check that the IBKR client was connected
        mock_ibkr_client.connect.assert_called_once()

        # Check that initial positions and historical data were fetched
        mock_ibkr_client.get_positions.assert_called_once()
        assert mock_ibkr_client.get_historical_data.call_count == len(
            ORIGINAL_EMA_STRATEGY["symbols"]
        )

        # Check that the handler is marked as initialized
        assert trading_service.original_strategy_handler._initialized is True


@pytest.mark.asyncio
async def test_trading_service_run_with_strategy(trading_service, mock_ibkr_client):
    """Test that TradingService correctly manages the OriginalStrategyHandler's background task."""
    # Patch the IBKRClient creation
    with patch(
        "trading_bot.app.service.original_strategy_handler.IBKRClient",
        return_value=mock_ibkr_client,
    ):
        # Patch the run method to return immediately
        with patch.object(
            trading_service.original_strategy_handler, "run", AsyncMock()
        ) as mock_run:
            # Create shutdown event
            shutdown_event = asyncio.Event()

            # Start the service in a task
            task = asyncio.create_task(trading_service.run(shutdown_event))

            # Give it a moment to start
            await asyncio.sleep(0.1)

            # Set shutdown event to stop the service
            shutdown_event.set()

            # Wait for the service to stop
            await task

            # Check that the handler's run method was called with the shutdown event
            mock_run.assert_called_once_with(shutdown_event)


@pytest.mark.asyncio
async def test_trading_service_shutdown_with_strategy(
    trading_service, mock_ibkr_client
):
    """Test that TradingService correctly shuts down the OriginalStrategyHandler."""
    # Patch the IBKRClient creation
    with patch(
        "trading_bot.app.service.original_strategy_handler.IBKRClient",
        return_value=mock_ibkr_client,
    ):
        # Patch the shutdown method
        with patch.object(
            trading_service.original_strategy_handler, "shutdown", AsyncMock()
        ) as mock_shutdown:
            # Shutdown the service
            await trading_service.shutdown()

            # Check that the handler's shutdown method was called
            mock_shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_strategy_interaction_with_ibkr(
    trading_service, mock_ibkr_client, mock_ibkr_server
):
    """Test that the OriginalStrategyHandler correctly interacts with IBKRClient."""
    # Patch the IBKRClient creation
    with patch(
        "trading_bot.app.service.original_strategy_handler.IBKRClient",
        return_value=mock_ibkr_client,
    ):
        # Initialize the handler
        await trading_service.original_strategy_handler.initialize()

        # Create a bar that will trigger a bullish crossover
        symbol = "SOXS"
        bar = BarData(
            date=datetime.datetime(2025, 4, 18, 11, 20, 0),
            open=31.0,
            high=32.0,
            low=30.5,
            close=31.5,
            volume=3200,
            average=31.2,
            barCount=150,
        )

        # Patch the crossover detection to force a bullish crossover
        with patch.object(
            trading_service.original_strategy_handler,
            "_check_bullish_crossover",
            return_value=True,
        ):
            with patch.object(
                trading_service.original_strategy_handler,
                "_check_bearish_crossover",
                return_value=False,
            ):
                # Process the bar
                await trading_service.original_strategy_handler._process_bar(
                    symbol, bar
                )

                # Check that orders were placed
                assert mock_ibkr_client.place_order.call_count >= 1

                # Check that alerts were sent
                assert trading_service.alert_manager.create_alert.call_count >= 1

                # Check that positions were updated in the mock server
                assert mock_ibkr_server.positions[symbol] > 0


@pytest.mark.asyncio
async def test_strategy_eod_processing(
    trading_service, mock_ibkr_client, mock_ibkr_server
):
    """Test that the OriginalStrategyHandler correctly processes EOD."""
    # Patch the IBKRClient creation
    with patch(
        "trading_bot.app.service.original_strategy_handler.IBKRClient",
        return_value=mock_ibkr_client,
    ):
        # Initialize the handler
        await trading_service.original_strategy_handler.initialize()

        # Set up positions in the handler and server
        trading_service.original_strategy_handler.positions = {"SOXS": 100, "SOXL": -50}
        mock_ibkr_server.positions = {"SOXS": 100, "SOXL": -50}

        # Process EOD
        await trading_service.original_strategy_handler._process_eod()

        # Check that orders were placed
        assert mock_ibkr_client.place_order.call_count == 2  # One for each symbol

        # Check that alerts were sent
        assert trading_service.alert_manager.create_alert.call_count == 2

        # Check that positions were updated in the handler
        assert trading_service.original_strategy_handler.positions["SOXS"] == 0
        assert trading_service.original_strategy_handler.positions["SOXL"] == 0

        # Check that positions were updated in the mock server
        assert mock_ibkr_server.positions["SOXS"] == 0
        assert mock_ibkr_server.positions["SOXL"] == 0


@pytest.mark.asyncio
async def test_strategy_market_data_response(
    trading_service, mock_ibkr_client, mock_ibkr_server
):
    """Test that the OriginalStrategyHandler correctly responds to market data changes."""
    # Patch the IBKRClient creation
    with patch(
        "trading_bot.app.service.original_strategy_handler.IBKRClient",
        return_value=mock_ibkr_client,
    ):
        # Initialize the handler
        await trading_service.original_strategy_handler.initialize()

        # Set up initial positions
        trading_service.original_strategy_handler.positions = {"SOXS": 0, "SOXL": 0}
        mock_ibkr_server.positions = {"SOXS": 0, "SOXL": 0}

        # Create a sequence of bars that will trigger different signals
        bars = [
            # Bullish crossover for SOXS
            BarData(
                date=datetime.datetime(2025, 4, 18, 10, 0, 0),
                open=20.0,
                high=21.0,
                low=19.0,
                close=20.5,
                volume=1000,
                average=20.2,
                barCount=100,
            ),
            # Bearish crossover for SOXL
            BarData(
                date=datetime.datetime(2025, 4, 18, 10, 5, 0),
                open=20.5,
                high=21.5,
                low=20.0,
                close=21.0,
                volume=1200,
                average=20.8,
                barCount=120,
            ),
            # No crossover
            BarData(
                date=datetime.datetime(2025, 4, 18, 10, 10, 0),
                open=21.0,
                high=22.0,
                low=20.5,
                close=21.5,
                volume=1300,
                average=21.2,
                barCount=130,
            ),
        ]

        # Process each bar with different crossover scenarios
        # First bar: Bullish crossover for SOXS
        with patch.object(
            trading_service.original_strategy_handler,
            "_check_bullish_crossover",
            return_value=True,
        ):
            with patch.object(
                trading_service.original_strategy_handler,
                "_check_bearish_crossover",
                return_value=False,
            ):
                await trading_service.original_strategy_handler._process_bar(
                    "SOXS", bars[0]
                )

        # Second bar: Bearish crossover for SOXL
        with patch.object(
            trading_service.original_strategy_handler,
            "_check_bullish_crossover",
            return_value=False,
        ):
            with patch.object(
                trading_service.original_strategy_handler,
                "_check_bearish_crossover",
                return_value=True,
            ):
                await trading_service.original_strategy_handler._process_bar(
                    "SOXL", bars[1]
                )

        # Third bar: No crossover
        with patch.object(
            trading_service.original_strategy_handler,
            "_check_bullish_crossover",
            return_value=False,
        ):
            with patch.object(
                trading_service.original_strategy_handler,
                "_check_bearish_crossover",
                return_value=False,
            ):
                await trading_service.original_strategy_handler._process_bar(
                    "SOXS", bars[2]
                )

        # Check that the correct orders were placed
        assert (
            mock_ibkr_client.place_order.call_count >= 4
        )  # At least 4 orders (2 for SOXS, 2 for SOXL)

        # Check that the correct alerts were sent
        assert (
            trading_service.alert_manager.create_alert.call_count >= 2
        )  # At least 2 alerts

        # Check that positions were updated correctly
        assert (
            trading_service.original_strategy_handler.positions["SOXS"] > 0
        )  # Long SOXS
        assert (
            trading_service.original_strategy_handler.positions["SOXL"] < 0
        )  # Short SOXL

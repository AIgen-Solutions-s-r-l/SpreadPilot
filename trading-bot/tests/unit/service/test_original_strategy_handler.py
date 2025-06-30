import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from ib_insync import BarData, Stock
from trading_bot.app.service.original_strategy_handler import OriginalStrategyHandler

from spreadpilot_core.ibkr.client import IBKRClient

# Mock data
MOCK_CONFIG = {
    "enabled": True,
    "ibkr_secret_ref": "test_secret_ref",
    "symbols": ["SOXS", "SOXL"],
    "fast_ema": 7,
    "slow_ema": 21,
    "bar_period": "5 mins",
    "trading_start_time": "09:30:00",
    "trading_end_time": "15:29:00",
    "dollar_amount": 10000,
    "trailing_stop_pct": 1.0,
    "close_at_eod": True,
}

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

MOCK_HISTORICAL_DF = pd.DataFrame(
    [
        {
            "time": datetime.datetime(2025, 4, 18, 9, 30, 0),
            "open": 20.0,
            "high": 21.0,
            "low": 19.0,
            "close": 20.0,
            "volume": 1000,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 9, 35, 0),
            "open": 20.0,
            "high": 21.0,
            "low": 19.0,
            "close": 20.5,
            "volume": 1100,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 9, 40, 0),
            "open": 20.5,
            "high": 21.5,
            "low": 20.0,
            "close": 21.0,
            "volume": 1200,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 9, 45, 0),
            "open": 21.0,
            "high": 22.0,
            "low": 20.5,
            "close": 21.5,
            "volume": 1300,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 9, 50, 0),
            "open": 21.5,
            "high": 22.5,
            "low": 21.0,
            "close": 22.0,
            "volume": 1400,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 9, 55, 0),
            "open": 22.0,
            "high": 23.0,
            "low": 21.5,
            "close": 22.5,
            "volume": 1500,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 10, 0, 0),
            "open": 22.5,
            "high": 23.5,
            "low": 22.0,
            "close": 23.0,
            "volume": 1600,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 10, 5, 0),
            "open": 23.0,
            "high": 24.0,
            "low": 22.5,
            "close": 23.5,
            "volume": 1700,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 10, 10, 0),
            "open": 23.5,
            "high": 24.5,
            "low": 23.0,
            "close": 24.0,
            "volume": 1800,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 10, 15, 0),
            "open": 24.0,
            "high": 25.0,
            "low": 23.5,
            "close": 24.5,
            "volume": 1900,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 10, 20, 0),
            "open": 24.5,
            "high": 25.5,
            "low": 24.0,
            "close": 25.0,
            "volume": 2000,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 10, 25, 0),
            "open": 25.0,
            "high": 26.0,
            "low": 24.5,
            "close": 25.5,
            "volume": 2100,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 10, 30, 0),
            "open": 25.5,
            "high": 26.5,
            "low": 25.0,
            "close": 26.0,
            "volume": 2200,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 10, 35, 0),
            "open": 26.0,
            "high": 27.0,
            "low": 25.5,
            "close": 26.5,
            "volume": 2300,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 10, 40, 0),
            "open": 26.5,
            "high": 27.5,
            "low": 26.0,
            "close": 27.0,
            "volume": 2400,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 10, 45, 0),
            "open": 27.0,
            "high": 28.0,
            "low": 26.5,
            "close": 27.5,
            "volume": 2500,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 10, 50, 0),
            "open": 27.5,
            "high": 28.5,
            "low": 27.0,
            "close": 28.0,
            "volume": 2600,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 10, 55, 0),
            "open": 28.0,
            "high": 29.0,
            "low": 27.5,
            "close": 28.5,
            "volume": 2700,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 11, 0, 0),
            "open": 28.5,
            "high": 29.5,
            "low": 28.0,
            "close": 29.0,
            "volume": 2800,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 11, 5, 0),
            "open": 29.0,
            "high": 30.0,
            "low": 28.5,
            "close": 29.5,
            "volume": 2900,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 11, 10, 0),
            "open": 29.5,
            "high": 30.5,
            "low": 29.0,
            "close": 30.0,
            "volume": 3000,
        },
        {
            "time": datetime.datetime(2025, 4, 18, 11, 15, 0),
            "open": 30.0,
            "high": 31.0,
            "low": 29.5,
            "close": 30.5,
            "volume": 3100,
        },
    ]
)

# Set the time index
MOCK_HISTORICAL_DF.set_index("time", inplace=True)


@pytest.fixture
def mock_trading_service():
    """Fixture to create a mock TradingService."""
    service = MagicMock()
    service.alert_manager = MagicMock()
    service.alert_manager.create_alert = AsyncMock()
    service.get_secret = AsyncMock(return_value="test_secret")
    service.settings = MagicMock()
    service.settings.ib_gateway_host = "127.0.0.1"
    service.settings.ib_gateway_port = 4002
    service.settings.ib_client_id = 1
    service.settings.ib_trading_mode = "paper"
    return service


@pytest.fixture
def mock_ibkr_client():
    """Fixture to create a mock IBKRClient."""
    client = MagicMock(spec=IBKRClient)
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    client.is_connected = MagicMock(return_value=True)
    client.get_contract_details = AsyncMock(return_value=[MagicMock(contract=MOCK_STOCK_CONTRACT)])
    client.get_historical_data = AsyncMock(return_value=MOCK_BAR_DATA)
    client.get_positions = AsyncMock(return_value=[])
    client.place_order = AsyncMock(return_value=MagicMock())
    return client


@pytest.fixture
async def strategy_handler(mock_trading_service, mock_ibkr_client):
    """Fixture to create an OriginalStrategyHandler with mocked dependencies."""
    with patch(
        "trading_bot.app.service.original_strategy_handler.IBKRClient",
        return_value=mock_ibkr_client,
    ):
        handler = OriginalStrategyHandler(mock_trading_service, MOCK_CONFIG)
        handler.ibkr_client = mock_ibkr_client  # Directly set the mocked client
        handler._initialized = True  # Mark as initialized for testing
        handler.historical_data = {
            "SOXS": MOCK_HISTORICAL_DF.copy(),
            "SOXL": MOCK_HISTORICAL_DF.copy(),
        }
        yield handler


# --- Test Initialization ---


@pytest.mark.asyncio
async def test_initialization(mock_trading_service, mock_ibkr_client):
    """Test the initialization of the OriginalStrategyHandler."""
    with patch(
        "trading_bot.app.service.original_strategy_handler.IBKRClient",
        return_value=mock_ibkr_client,
    ):
        handler = OriginalStrategyHandler(mock_trading_service, MOCK_CONFIG)
        await handler.initialize()

        # Check that the IBKR client was created and connected
        mock_ibkr_client.connect.assert_called_once()

        # Check that initial positions and historical data were fetched
        mock_ibkr_client.get_positions.assert_called_once()
        assert mock_ibkr_client.get_historical_data.call_count == len(MOCK_CONFIG["symbols"])

        # Check that the handler is marked as initialized
        assert handler._initialized is True


@pytest.mark.asyncio
async def test_initialization_disabled(mock_trading_service, mock_ibkr_client):
    """Test initialization when the strategy is disabled."""
    disabled_config = MOCK_CONFIG.copy()
    disabled_config["enabled"] = False

    with patch(
        "trading_bot.app.service.original_strategy_handler.IBKRClient",
        return_value=mock_ibkr_client,
    ):
        handler = OriginalStrategyHandler(mock_trading_service, disabled_config)
        await handler.initialize()

        # Check that the IBKR client was not created or connected
        mock_ibkr_client.connect.assert_not_called()

        # Check that the handler is not marked as initialized
        assert handler._initialized is False


@pytest.mark.asyncio
async def test_initialization_error(mock_trading_service, mock_ibkr_client):
    """Test initialization when an error occurs."""
    mock_ibkr_client.connect.side_effect = Exception("Connection error")

    with patch(
        "trading_bot.app.service.original_strategy_handler.IBKRClient",
        return_value=mock_ibkr_client,
    ):
        handler = OriginalStrategyHandler(mock_trading_service, MOCK_CONFIG)
        await handler.initialize()

        # Check that the IBKR client attempted to connect
        mock_ibkr_client.connect.assert_called_once()

        # Check that the handler is not marked as initialized
        assert handler._initialized is False


# --- Test EMA Calculation ---


def test_calculate_ema(strategy_handler):
    """Test the EMA calculation logic."""
    # Create a simple series for testing
    series = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])

    # Calculate EMAs
    fast_ema = strategy_handler._calculate_ema(series, MOCK_CONFIG["fast_ema"])
    slow_ema = strategy_handler._calculate_ema(series, MOCK_CONFIG["slow_ema"])

    # Check that the EMAs have the correct length
    assert len(fast_ema) == len(series)
    assert len(slow_ema) == len(series)

    # Check that the fast EMA is more responsive to recent prices
    assert fast_ema.iloc[-1] > slow_ema.iloc[-1]

    # Check that the EMAs are calculated correctly (basic sanity check)
    assert (
        fast_ema.iloc[-1] < series.iloc[-1]
    )  # EMA should be less than the last price in an uptrend
    assert (
        slow_ema.iloc[-1] < fast_ema.iloc[-1]
    )  # Slow EMA should lag behind fast EMA in an uptrend


# --- Test Crossover Detection ---


def test_check_bullish_crossover(strategy_handler):
    """Test the bullish crossover detection logic."""
    # Create series where fast EMA crosses above slow EMA
    fast_ema = pd.Series([10, 11, 12, 13, 14])
    slow_ema = pd.Series([12, 12.5, 13, 13.2, 13.5])

    # No crossover initially (fast below slow)
    assert not strategy_handler._check_bullish_crossover(fast_ema[:2], slow_ema[:2])

    # Create a bullish crossover (fast crosses above slow)
    fast_ema_cross = pd.Series([12, 13, 14])
    slow_ema_cross = pd.Series([13, 13, 13])

    # Should detect the crossover
    assert strategy_handler._check_bullish_crossover(fast_ema_cross, slow_ema_cross)

    # Test with insufficient data
    assert not strategy_handler._check_bullish_crossover(pd.Series([10]), pd.Series([12]))


def test_check_bearish_crossover(strategy_handler):
    """Test the bearish crossover detection logic."""
    # Create series where fast EMA crosses below slow EMA
    fast_ema = pd.Series([15, 14, 13, 12, 11])
    slow_ema = pd.Series([13, 12.8, 12.5, 12.2, 12])

    # No crossover initially (fast above slow)
    assert not strategy_handler._check_bearish_crossover(fast_ema[:2], slow_ema[:2])

    # Create a bearish crossover (fast crosses below slow)
    fast_ema_cross = pd.Series([13, 12, 11])
    slow_ema_cross = pd.Series([12, 12, 12])

    # Should detect the crossover
    assert strategy_handler._check_bearish_crossover(fast_ema_cross, slow_ema_cross)

    # Test with insufficient data
    assert not strategy_handler._check_bearish_crossover(pd.Series([10]), pd.Series([12]))


# --- Test Position Sizing ---


def test_calculate_position_size(strategy_handler):
    """Test the position sizing calculation."""
    # Test with different prices
    assert strategy_handler._calculate_position_size(100.0) == 100  # $10,000 / $100 = 100 shares
    assert strategy_handler._calculate_position_size(50.0) == 200  # $10,000 / $50 = 200 shares
    assert strategy_handler._calculate_position_size(200.0) == 50  # $10,000 / $200 = 50 shares

    # Test with very high price (should return at least 1 share)
    assert strategy_handler._calculate_position_size(15000.0) == 1

    # Test with zero or negative price (should handle gracefully)
    assert strategy_handler._calculate_position_size(0.0) == 0
    assert strategy_handler._calculate_position_size(-50.0) == 0


# --- Test Order Creation ---


def test_create_market_order(strategy_handler):
    """Test the market order creation logic."""
    # Test buy order
    buy_order = strategy_handler._create_market_order("BUY", 100)
    assert buy_order.orderType == "MKT"
    assert buy_order.action == "BUY"
    assert buy_order.totalQuantity == 100

    # Test sell order
    sell_order = strategy_handler._create_market_order("SELL", 50)
    assert sell_order.orderType == "MKT"
    assert sell_order.action == "SELL"
    assert sell_order.totalQuantity == 50

    # Test with negative quantity (should use absolute value)
    neg_order = strategy_handler._create_market_order("BUY", -75)
    assert neg_order.totalQuantity == 75


def test_create_trailing_stop_order(strategy_handler):
    """Test the trailing stop order creation logic."""
    # Test buy trailing stop
    buy_stop = strategy_handler._create_trailing_stop_order("BUY", 100, 1.0)
    assert buy_stop.orderType == "TRAIL"
    assert buy_stop.action == "BUY"
    assert buy_stop.totalQuantity == 100
    assert buy_stop.trailingPercent == 1.0
    assert buy_stop.tif == "GTC"  # Good Till Cancelled

    # Test sell trailing stop
    sell_stop = strategy_handler._create_trailing_stop_order("SELL", 50, 2.0)
    assert sell_stop.orderType == "TRAIL"
    assert sell_stop.action == "SELL"
    assert sell_stop.totalQuantity == 50
    assert sell_stop.trailingPercent == 2.0
    assert sell_stop.tif == "GTC"

    # Test with negative quantity (should use absolute value)
    neg_stop = strategy_handler._create_trailing_stop_order("SELL", -75, 1.5)
    assert neg_stop.totalQuantity == 75


# --- Test Process Bar ---


@pytest.mark.asyncio
async def test_process_bar_bullish_crossover(strategy_handler, mock_ibkr_client):
    """Test processing a bar with a bullish crossover."""
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

    # Modify historical data to create a bullish crossover scenario
    # Last row has fast EMA below slow EMA
    df = strategy_handler.historical_data[symbol]

    # Calculate EMAs before the new bar
    fast_ema = strategy_handler._calculate_ema(df["close"], MOCK_CONFIG["fast_ema"])
    slow_ema = strategy_handler._calculate_ema(df["close"], MOCK_CONFIG["slow_ema"])

    # Patch the crossover detection to force a bullish crossover
    with patch.object(strategy_handler, "_check_bullish_crossover", return_value=True):
        with patch.object(strategy_handler, "_check_bearish_crossover", return_value=False):
            # Process the bar
            await strategy_handler._process_bar(symbol, bar)

            # Check that a buy order was placed
            mock_ibkr_client.place_order.assert_called()

            # Check that at least 2 orders were placed (entry + stop)
            assert mock_ibkr_client.place_order.call_count >= 2

            # Check that an alert was sent
            strategy_handler.service.alert_manager.create_alert.assert_called()

            # Check that the position was updated
            assert symbol in strategy_handler.positions
            assert strategy_handler.positions[symbol] > 0  # Long position


@pytest.mark.asyncio
async def test_process_bar_bearish_crossover(strategy_handler, mock_ibkr_client):
    """Test processing a bar with a bearish crossover."""
    # Create a bar that will trigger a bearish crossover
    symbol = "SOXL"
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

    # Modify historical data to create a bearish crossover scenario
    # Last row has fast EMA above slow EMA
    df = strategy_handler.historical_data[symbol]

    # Calculate EMAs before the new bar
    fast_ema = strategy_handler._calculate_ema(df["close"], MOCK_CONFIG["fast_ema"])
    slow_ema = strategy_handler._calculate_ema(df["close"], MOCK_CONFIG["slow_ema"])

    # Patch the crossover detection to force a bearish crossover
    with patch.object(strategy_handler, "_check_bullish_crossover", return_value=False):
        with patch.object(strategy_handler, "_check_bearish_crossover", return_value=True):
            # Process the bar
            await strategy_handler._process_bar(symbol, bar)

            # Check that a sell order was placed
            mock_ibkr_client.place_order.assert_called()

            # Check that at least 2 orders were placed (entry + stop)
            assert mock_ibkr_client.place_order.call_count >= 2

            # Check that an alert was sent
            strategy_handler.service.alert_manager.create_alert.assert_called()

            # Check that the position was updated
            assert symbol in strategy_handler.positions
            assert strategy_handler.positions[symbol] < 0  # Short position


@pytest.mark.asyncio
async def test_process_bar_no_crossover(strategy_handler, mock_ibkr_client):
    """Test processing a bar with no crossover."""
    # Create a bar that will not trigger a crossover
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

    # Patch the crossover detection to force no crossover
    with patch.object(strategy_handler, "_check_bullish_crossover", return_value=False):
        with patch.object(strategy_handler, "_check_bearish_crossover", return_value=False):
            # Process the bar
            await strategy_handler._process_bar(symbol, bar)

            # Check that no orders were placed
            mock_ibkr_client.place_order.assert_not_called()

            # Check that no alerts were sent
            strategy_handler.service.alert_manager.create_alert.assert_not_called()


# --- Test EOD Processing ---


@pytest.mark.asyncio
async def test_process_eod_with_positions(strategy_handler, mock_ibkr_client):
    """Test EOD processing with open positions."""
    # Set up positions
    strategy_handler.positions = {"SOXS": 100, "SOXL": -50}

    # Process EOD
    await strategy_handler._process_eod()

    # Check that orders were placed to close positions
    assert mock_ibkr_client.place_order.call_count == 2  # One for each symbol

    # Check that alerts were sent
    assert strategy_handler.service.alert_manager.create_alert.call_count == 2

    # Check that positions were updated
    assert strategy_handler.positions["SOXS"] == 0
    assert strategy_handler.positions["SOXL"] == 0


@pytest.mark.asyncio
async def test_process_eod_no_positions(strategy_handler, mock_ibkr_client):
    """Test EOD processing with no open positions."""
    # Set up empty positions
    strategy_handler.positions = {"SOXS": 0, "SOXL": 0}

    # Process EOD
    await strategy_handler._process_eod()

    # Check that no orders were placed
    mock_ibkr_client.place_order.assert_not_called()

    # Check that no alerts were sent
    strategy_handler.service.alert_manager.create_alert.assert_not_called()


@pytest.mark.asyncio
async def test_process_eod_disabled(strategy_handler, mock_ibkr_client):
    """Test EOD processing when close_at_eod is disabled."""
    # Set up positions
    strategy_handler.positions = {"SOXS": 100, "SOXL": -50}

    # Disable close_at_eod
    strategy_handler.config["close_at_eod"] = False

    # Process EOD
    await strategy_handler._process_eod()

    # Check that no orders were placed
    mock_ibkr_client.place_order.assert_not_called()

    # Check that no alerts were sent
    strategy_handler.service.alert_manager.create_alert.assert_not_called()

    # Check that positions were not updated
    assert strategy_handler.positions["SOXS"] == 100
    assert strategy_handler.positions["SOXL"] == -50


# --- Test Run Method ---


@pytest.mark.asyncio
async def test_run_not_initialized(strategy_handler):
    """Test run method when handler is not initialized."""
    # Mark as not initialized
    strategy_handler._initialized = False

    # Create shutdown event
    shutdown_event = asyncio.Event()

    # Run the handler
    await strategy_handler.run(shutdown_event)

    # Check that the handler exited without processing
    strategy_handler.ibkr_client.get_historical_data.assert_not_called()


@pytest.mark.asyncio
async def test_run_shutdown(strategy_handler):
    """Test run method with immediate shutdown."""
    # Create shutdown event and set it
    shutdown_event = asyncio.Event()
    shutdown_event.set()

    # Run the handler
    await strategy_handler.run(shutdown_event)

    # Check that shutdown was called
    with patch.object(strategy_handler, "shutdown") as mock_shutdown:
        await strategy_handler.run(shutdown_event)
        mock_shutdown.assert_called_once()


# --- Test Shutdown ---


@pytest.mark.asyncio
async def test_shutdown(strategy_handler, mock_ibkr_client):
    """Test the shutdown method."""
    # Run shutdown
    await strategy_handler.shutdown()

    # Check that the IBKR client was disconnected
    mock_ibkr_client.disconnect.assert_called_once()

    # Check that the handler is marked as not initialized
    assert strategy_handler._initialized is False


@pytest.mark.asyncio
async def test_shutdown_not_connected(strategy_handler, mock_ibkr_client):
    """Test shutdown when not connected."""
    # Mock client not connected
    mock_ibkr_client.is_connected.return_value = False

    # Run shutdown
    await strategy_handler.shutdown()

    # Check that disconnect was not called
    mock_ibkr_client.disconnect.assert_not_called()

    # Check that the handler is marked as not initialized
    assert strategy_handler._initialized is False

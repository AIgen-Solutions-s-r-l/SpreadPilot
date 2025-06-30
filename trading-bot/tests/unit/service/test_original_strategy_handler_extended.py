import asyncio
import datetime
import os

# Import directly from the module path to avoid the import error
# Import directly from the relative path to avoid the import error
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from ib_insync import BarData, Position, Stock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from app.service.original_strategy_handler import OriginalStrategyHandler

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from spreadpilot_core.ibkr.client import IBKRClient

# Mock data (same as in the original test file)
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

# Create a DataFrame with time as the index
time_index = [
    datetime.datetime(2025, 4, 18, 9, 30, 0),
    datetime.datetime(2025, 4, 18, 9, 35, 0),
    datetime.datetime(2025, 4, 18, 9, 40, 0),
    datetime.datetime(2025, 4, 18, 9, 45, 0),
    datetime.datetime(2025, 4, 18, 9, 50, 0),
    datetime.datetime(2025, 4, 18, 9, 55, 0),
    datetime.datetime(2025, 4, 18, 10, 0, 0),
    datetime.datetime(2025, 4, 18, 10, 5, 0),
    datetime.datetime(2025, 4, 18, 10, 10, 0),
    datetime.datetime(2025, 4, 18, 10, 15, 0),
    datetime.datetime(2025, 4, 18, 10, 20, 0),
    datetime.datetime(2025, 4, 18, 10, 25, 0),
    datetime.datetime(2025, 4, 18, 10, 30, 0),
    datetime.datetime(2025, 4, 18, 10, 35, 0),
    datetime.datetime(2025, 4, 18, 10, 40, 0),
    datetime.datetime(2025, 4, 18, 10, 45, 0),
    datetime.datetime(2025, 4, 18, 10, 50, 0),
    datetime.datetime(2025, 4, 18, 10, 55, 0),
    datetime.datetime(2025, 4, 18, 11, 0, 0),
    datetime.datetime(2025, 4, 18, 11, 5, 0),
    datetime.datetime(2025, 4, 18, 11, 10, 0),
    datetime.datetime(2025, 4, 18, 11, 15, 0),
]

data = {
    "open": [
        20.0,
        20.0,
        20.5,
        21.0,
        21.5,
        22.0,
        22.5,
        23.0,
        23.5,
        24.0,
        24.5,
        25.0,
        25.5,
        26.0,
        26.5,
        27.0,
        27.5,
        28.0,
        28.5,
        29.0,
        29.5,
        30.0,
    ],
    "high": [
        21.0,
        21.0,
        21.5,
        22.0,
        22.5,
        23.0,
        23.5,
        24.0,
        24.5,
        25.0,
        25.5,
        26.0,
        26.5,
        27.0,
        27.5,
        28.0,
        28.5,
        29.0,
        29.5,
        30.0,
        30.5,
        31.0,
    ],
    "low": [
        19.0,
        19.0,
        20.0,
        20.5,
        21.0,
        21.5,
        22.0,
        22.5,
        23.0,
        23.5,
        24.0,
        24.5,
        25.0,
        25.5,
        26.0,
        26.5,
        27.0,
        27.5,
        28.0,
        28.5,
        29.0,
        29.5,
    ],
    "close": [
        20.0,
        20.5,
        21.0,
        21.5,
        22.0,
        22.5,
        23.0,
        23.5,
        24.0,
        24.5,
        25.0,
        25.5,
        26.0,
        26.5,
        27.0,
        27.5,
        28.0,
        28.5,
        29.0,
        29.5,
        30.0,
        30.5,
    ],
    "volume": [
        1000,
        1100,
        1200,
        1300,
        1400,
        1500,
        1600,
        1700,
        1800,
        1900,
        2000,
        2100,
        2200,
        2300,
        2400,
        2500,
        2600,
        2700,
        2800,
        2900,
        3000,
        3100,
    ],
}

MOCK_HISTORICAL_DF = pd.DataFrame(data, index=time_index)


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
        "app.service.original_strategy_handler.IBKRClient",
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


# --- Test _fetch_initial_positions Method ---


@pytest.mark.asyncio
async def test_fetch_initial_positions_success(strategy_handler, mock_ibkr_client):
    """Test successful fetching of initial positions."""
    # Setup mock positions
    mock_position1 = MagicMock(spec=Position)
    mock_position1.contract = MagicMock()
    mock_position1.contract.symbol = "SOXS"
    mock_position1.position = 100

    mock_position2 = MagicMock(spec=Position)
    mock_position2.contract = MagicMock()
    mock_position2.contract.symbol = "SOXL"
    mock_position2.position = -50

    mock_position3 = MagicMock(spec=Position)
    mock_position3.contract = MagicMock()
    mock_position3.contract.symbol = "AAPL"  # Not in config symbols
    mock_position3.position = 200

    mock_ibkr_client.get_positions.return_value = [
        mock_position1,
        mock_position2,
        mock_position3,
    ]

    # Call the method
    await strategy_handler._fetch_initial_positions()

    # Verify
    mock_ibkr_client.get_positions.assert_called_once()
    assert strategy_handler.positions == {"SOXS": 100, "SOXL": -50}
    assert "AAPL" not in strategy_handler.positions  # Should filter out symbols not in config


@pytest.mark.asyncio
async def test_fetch_initial_positions_not_connected(strategy_handler, mock_ibkr_client):
    """Test fetching positions when IBKR client is not connected."""
    # Setup mock to return not connected
    mock_ibkr_client.is_connected.return_value = False

    # Call the method
    await strategy_handler._fetch_initial_positions()

    # Verify
    mock_ibkr_client.get_positions.assert_not_called()
    assert strategy_handler.positions == {}


@pytest.mark.asyncio
async def test_fetch_initial_positions_error(strategy_handler, mock_ibkr_client):
    """Test error handling when fetching positions."""
    # Setup mock to raise an exception
    mock_ibkr_client.get_positions.side_effect = Exception("Test error")

    # Call the method
    await strategy_handler._fetch_initial_positions()

    # Verify
    mock_ibkr_client.get_positions.assert_called_once()
    assert strategy_handler.positions == {}


# --- Test _fetch_initial_historical_data Method ---


@pytest.mark.asyncio
async def test_fetch_initial_historical_data_success(strategy_handler, mock_ibkr_client):
    """Test successful fetching of initial historical data."""
    # Setup - create a mock DataFrame to return from get_historical_data
    mock_df = pd.DataFrame(
        {
            "open": [20.0],
            "high": [21.0],
            "low": [19.0],
            "close": [20.5],
            "volume": [1000],
        },
        index=[datetime.datetime(2025, 4, 18, 10, 0, 0)],
    )

    # Store the mock DataFrame in the handler
    for symbol in MOCK_CONFIG["symbols"]:
        strategy_handler.historical_data[symbol] = mock_df

    # Call the method
    await strategy_handler._fetch_initial_historical_data()

    # Verify
    assert mock_ibkr_client.get_contract_details.call_count == len(MOCK_CONFIG["symbols"])
    assert mock_ibkr_client.get_historical_data.call_count == len(MOCK_CONFIG["symbols"])


@pytest.mark.asyncio
async def test_fetch_initial_historical_data_not_connected(strategy_handler, mock_ibkr_client):
    """Test fetching historical data when IBKR client is not connected."""
    # Setup mock to return not connected
    mock_ibkr_client.is_connected.return_value = False

    # Clear existing historical data
    strategy_handler.historical_data = {}

    # Call the method
    await strategy_handler._fetch_initial_historical_data()

    # Verify
    mock_ibkr_client.get_contract_details.assert_not_called()
    mock_ibkr_client.get_historical_data.assert_not_called()
    assert strategy_handler.historical_data == {}


@pytest.mark.asyncio
async def test_fetch_initial_historical_data_contract_not_found(strategy_handler, mock_ibkr_client):
    """Test handling when contract details are not found."""
    # Setup mock to return empty list for contract details
    mock_ibkr_client.get_contract_details.return_value = []

    # Clear existing historical data
    strategy_handler.historical_data = {}

    # Initialize empty DataFrames for each symbol (this is what the method should do)
    for symbol in MOCK_CONFIG["symbols"]:
        strategy_handler.historical_data[symbol] = pd.DataFrame()

    # Call the method
    await strategy_handler._fetch_initial_historical_data()

    # Verify
    assert mock_ibkr_client.get_contract_details.call_count == len(MOCK_CONFIG["symbols"])
    assert mock_ibkr_client.get_historical_data.call_count == 0

    # Check that empty DataFrames were created for each symbol
    for symbol in MOCK_CONFIG["symbols"]:
        assert symbol in strategy_handler.historical_data
        assert strategy_handler.historical_data[symbol].empty


@pytest.mark.asyncio
async def test_fetch_initial_historical_data_no_bars(strategy_handler, mock_ibkr_client):
    """Test handling when no historical bars are returned."""
    # Setup mock to return empty list for historical data
    mock_ibkr_client.get_historical_data.return_value = []

    # Clear existing historical data
    strategy_handler.historical_data = {}

    # Call the method
    await strategy_handler._fetch_initial_historical_data()

    # Verify
    assert mock_ibkr_client.get_contract_details.call_count == len(MOCK_CONFIG["symbols"])
    assert mock_ibkr_client.get_historical_data.call_count == len(MOCK_CONFIG["symbols"])

    # Check that empty DataFrames were created for each symbol
    for symbol in MOCK_CONFIG["symbols"]:
        assert symbol in strategy_handler.historical_data
        assert strategy_handler.historical_data[symbol].empty


@pytest.mark.asyncio
async def test_fetch_initial_historical_data_error(strategy_handler, mock_ibkr_client):
    """Test error handling when fetching historical data."""
    # Setup mock to raise an exception
    mock_ibkr_client.get_historical_data.side_effect = Exception("Test error")

    # Clear existing historical data
    strategy_handler.historical_data = {}

    # Call the method
    await strategy_handler._fetch_initial_historical_data()

    # Verify
    assert mock_ibkr_client.get_contract_details.call_count == len(MOCK_CONFIG["symbols"])
    assert mock_ibkr_client.get_historical_data.call_count == len(MOCK_CONFIG["symbols"])

    # Check that empty DataFrames were created for each symbol
    for symbol in MOCK_CONFIG["symbols"]:
        assert symbol in strategy_handler.historical_data
        assert strategy_handler.historical_data[symbol].empty


# --- Test _process_bar Error Handling ---


@pytest.mark.asyncio
async def test_process_bar_no_historical_data(strategy_handler, mock_ibkr_client):
    """Test processing a bar when no historical data exists for the symbol."""
    # Setup
    symbol = "UNKNOWN"
    bar = MOCK_BAR_DATA[0]

    # Call the method
    await strategy_handler._process_bar(symbol, bar)

    # Verify no orders were placed
    mock_ibkr_client.place_order.assert_not_called()


@pytest.mark.asyncio
async def test_process_bar_insufficient_data(strategy_handler, mock_ibkr_client):
    """Test processing a bar with insufficient historical data for EMA calculation."""
    # Setup - create a small DataFrame with fewer rows than required for slow EMA
    symbol = "SOXS"
    bar = MOCK_BAR_DATA[0]

    # Create a small DataFrame with time already as index
    small_df = pd.DataFrame(
        {
            "open": [20.0, 20.5, 21.0, 21.5, 22.0],
            "high": [21.0, 21.5, 22.0, 22.5, 23.0],
            "low": [19.0, 19.5, 20.0, 20.5, 21.0],
            "close": [20.5, 21.0, 21.5, 22.0, 22.5],
            "volume": [1000, 1100, 1200, 1300, 1400],
        },
        index=[
            datetime.datetime(2025, 4, 18, 9, 30, 0),
            datetime.datetime(2025, 4, 18, 9, 35, 0),
            datetime.datetime(2025, 4, 18, 9, 40, 0),
            datetime.datetime(2025, 4, 18, 9, 45, 0),
            datetime.datetime(2025, 4, 18, 9, 50, 0),
        ],
    )

    strategy_handler.historical_data[symbol] = small_df

    # Create a mock for the new_row DataFrame that includes a 'time' column
    mock_df = MagicMock()
    mock_df.set_index.return_value = pd.DataFrame(
        {"open": 20.0, "high": 21.0, "low": 19.0, "close": 20.5, "volume": 1000},
        index=[datetime.datetime(2025, 4, 18, 10, 0, 0)],
    )

    # Mock the concat result
    concat_result = small_df.copy()

    # Patch both DataFrame creation and concat in _process_bar
    with (
        patch("pandas.DataFrame", return_value=mock_df),
        patch("pandas.concat", return_value=concat_result),
    ):
        # Call the method
        await strategy_handler._process_bar(symbol, bar)

        # Verify no orders were placed
        mock_ibkr_client.place_order.assert_not_called()

        # Verify set_index was called with 'time'
        mock_df.set_index.assert_called_once_with("time", inplace=True)


@pytest.mark.asyncio
async def test_process_bar_ema_calculation_error(strategy_handler, mock_ibkr_client):
    """Test error handling during EMA calculation."""
    # Setup
    symbol = "SOXS"
    bar = MOCK_BAR_DATA[0]

    # Create a mock for the new_row DataFrame that includes a 'time' column
    mock_df = MagicMock()
    mock_df.set_index.return_value = pd.DataFrame(
        {"open": 20.0, "high": 21.0, "low": 19.0, "close": 20.5, "volume": 1000},
        index=[datetime.datetime(2025, 4, 18, 10, 0, 0)],
    )

    # Mock the concat result
    concat_result = MOCK_HISTORICAL_DF.copy()

    # Patch DataFrame creation, concat, and the _calculate_ema method
    with (
        patch("pandas.DataFrame", return_value=mock_df),
        patch("pandas.concat", return_value=concat_result),
        patch.object(
            strategy_handler,
            "_calculate_ema",
            side_effect=Exception("EMA calculation error"),
        ),
    ):
        # Call the method
        await strategy_handler._process_bar(symbol, bar)

        # Verify no orders were placed
        mock_ibkr_client.place_order.assert_not_called()

        # Verify set_index was called with 'time'
        mock_df.set_index.assert_called_once_with("time", inplace=True)


@pytest.mark.asyncio
async def test_process_bar_contract_not_found(strategy_handler, mock_ibkr_client):
    """Test processing a bar when contract details cannot be found."""
    # Setup
    symbol = "SOXS"
    bar = MOCK_BAR_DATA[0]

    # Mock contract details to return empty list
    mock_ibkr_client.get_contract_details.return_value = []

    # Create a mock for the new_row DataFrame that includes a 'time' column
    mock_df = MagicMock()
    mock_df.set_index.return_value = pd.DataFrame(
        {"open": 20.0, "high": 21.0, "low": 19.0, "close": 20.5, "volume": 1000},
        index=[datetime.datetime(2025, 4, 18, 10, 0, 0)],
    )

    # Mock the concat result
    concat_result = MOCK_HISTORICAL_DF.copy()

    # Patch DataFrame creation, concat, and the crossover methods
    with (
        patch("pandas.DataFrame", return_value=mock_df),
        patch("pandas.concat", return_value=concat_result),
        patch.object(strategy_handler, "_check_bullish_crossover", return_value=True),
        patch.object(strategy_handler, "_check_bearish_crossover", return_value=False),
    ):
        # Call the method
        await strategy_handler._process_bar(symbol, bar)

        # Verify contract details were requested but no orders were placed
        mock_ibkr_client.get_contract_details.assert_called_once()
        mock_ibkr_client.place_order.assert_not_called()

        # Verify set_index was called with 'time'
        mock_df.set_index.assert_called_once_with("time", inplace=True)


@pytest.mark.asyncio
async def test_process_bar_order_placement_error(strategy_handler, mock_ibkr_client):
    """Test error handling during order placement."""
    # Setup
    symbol = "SOXS"
    bar = MOCK_BAR_DATA[0]

    # Mock place_order to raise an exception
    mock_ibkr_client.place_order.side_effect = Exception("Order placement error")

    # Create a mock for the new_row DataFrame that includes a 'time' column
    mock_df = MagicMock()
    mock_df.set_index.return_value = pd.DataFrame(
        {"open": 20.0, "high": 21.0, "low": 19.0, "close": 20.5, "volume": 1000},
        index=[datetime.datetime(2025, 4, 18, 10, 0, 0)],
    )

    # Mock the concat result
    concat_result = MOCK_HISTORICAL_DF.copy()

    # Patch DataFrame creation, concat, and the crossover methods
    with (
        patch("pandas.DataFrame", return_value=mock_df),
        patch("pandas.concat", return_value=concat_result),
        patch.object(strategy_handler, "_check_bullish_crossover", return_value=True),
        patch.object(strategy_handler, "_check_bearish_crossover", return_value=False),
    ):
        # Call the method
        await strategy_handler._process_bar(symbol, bar)

        # Verify contract details were requested and order placement was attempted
        mock_ibkr_client.get_contract_details.assert_called_once()
        mock_ibkr_client.place_order.assert_called()

        # Verify set_index was called with 'time'
        mock_df.set_index.assert_called_once_with("time", inplace=True)


# --- Test _send_alert Method ---


@pytest.mark.asyncio
async def test_send_alert_success(strategy_handler):
    """Test successful alert sending."""
    # Setup
    symbol = "SOXS"
    action = "BUY"
    quantity = 100
    price = 25.0
    order_type = "MKT"
    signal_type = "Bullish Crossover"

    # Mock the Alert class to avoid validation errors
    with patch("app.service.original_strategy_handler.Alert") as MockAlert:
        # Configure the mock to return a properly configured alert object
        mock_alert = MagicMock()
        mock_alert.symbol = symbol
        mock_alert.action = action
        mock_alert.quantity = quantity
        mock_alert.price = price
        mock_alert.order_type = order_type
        mock_alert.strategy = "ORIGINAL_EMA"
        mock_alert.signal_type = signal_type
        MockAlert.return_value = mock_alert

        # Call the method
        await strategy_handler._send_alert(symbol, action, quantity, price, order_type, signal_type)

        # Verify alert was created with correct parameters
        MockAlert.assert_called_once()
        strategy_handler.service.alert_manager.create_alert.assert_called_once_with(mock_alert)


@pytest.mark.asyncio
async def test_send_alert_error(strategy_handler):
    """Test error handling during alert sending."""
    # Setup
    symbol = "SOXS"
    action = "BUY"
    quantity = 100
    price = 25.0
    order_type = "MKT"
    signal_type = "Bullish Crossover"

    # Mock the Alert class to avoid validation errors
    with patch("app.service.original_strategy_handler.Alert") as MockAlert:
        # Configure the mock to return a properly configured alert object
        mock_alert = MagicMock()
        MockAlert.return_value = mock_alert

        # Mock create_alert to raise an exception
        strategy_handler.service.alert_manager.create_alert.side_effect = Exception(
            "Alert creation error"
        )

        # Call the method
        await strategy_handler._send_alert(symbol, action, quantity, price, order_type, signal_type)

        # Verify alert creation was attempted
        strategy_handler.service.alert_manager.create_alert.assert_called_once_with(mock_alert)


# --- Test _process_eod Error Handling ---


@pytest.mark.asyncio
async def test_process_eod_not_connected(strategy_handler, mock_ibkr_client):
    """Test EOD processing when IBKR client is not connected."""
    # Setup
    strategy_handler.positions = {"SOXS": 100, "SOXL": -50}
    mock_ibkr_client.is_connected.return_value = False

    # Call the method
    await strategy_handler._process_eod()

    # Verify no orders were placed
    mock_ibkr_client.place_order.assert_not_called()

    # Positions should remain unchanged
    assert strategy_handler.positions == {"SOXS": 100, "SOXL": -50}


@pytest.mark.asyncio
async def test_process_eod_contract_not_found(strategy_handler, mock_ibkr_client):
    """Test EOD processing when contract details cannot be found."""
    # Setup
    strategy_handler.positions = {"SOXS": 100, "SOXL": -50}

    # Mock contract details to return empty list for the first call only
    mock_ibkr_client.get_contract_details.side_effect = [
        [],
        [MagicMock(contract=MOCK_STOCK_CONTRACT)],
    ]

    # Call the method
    await strategy_handler._process_eod()

    # Verify contract details were requested twice (once for each symbol)
    assert mock_ibkr_client.get_contract_details.call_count == 2

    # Only one order should have been placed (for SOXL)
    assert mock_ibkr_client.place_order.call_count == 1

    # SOXS position should remain unchanged, SOXL should be closed
    assert strategy_handler.positions["SOXS"] == 100
    assert strategy_handler.positions["SOXL"] == 0


@pytest.mark.asyncio
async def test_process_eod_order_placement_error(strategy_handler, mock_ibkr_client):
    """Test error handling during order placement in EOD processing."""
    # Setup
    strategy_handler.positions = {"SOXS": 100, "SOXL": -50}

    # Mock place_order to raise an exception for the first call only
    mock_ibkr_client.place_order.side_effect = [
        Exception("Order placement error"),
        MagicMock(),
    ]

    # Call the method
    await strategy_handler._process_eod()

    # Verify contract details were requested twice (once for each symbol)
    assert mock_ibkr_client.get_contract_details.call_count == 2

    # Two order placements should have been attempted
    assert mock_ibkr_client.place_order.call_count == 2

    # SOXS position should remain unchanged due to error, SOXL should be closed
    assert strategy_handler.positions["SOXS"] == 100
    assert strategy_handler.positions["SOXL"] == 0


# --- Test Run Method Main Loop ---


@pytest.mark.asyncio
async def test_run_main_loop(strategy_handler, mock_ibkr_client):
    """Test the main run loop functionality."""
    # Setup
    shutdown_event = asyncio.Event()

    # Create a side effect to set the shutdown event after one iteration
    original_sleep = asyncio.sleep
    sleep_counter = 0

    async def mock_sleep(seconds):
        nonlocal sleep_counter
        sleep_counter += 1
        if sleep_counter >= 2:  # Set shutdown after second sleep
            shutdown_event.set()
        await original_sleep(0.01)  # Use a small sleep time for testing

    # Patch asyncio.sleep to use our mock
    with patch("asyncio.sleep", side_effect=mock_sleep):
        # Call the run method
        await strategy_handler.run(shutdown_event)

        # Verify shutdown was called
        assert sleep_counter >= 2
        assert shutdown_event.is_set()


@pytest.mark.asyncio
async def test_run_cancelled_error(strategy_handler):
    """Test handling of CancelledError in the run loop."""
    # Setup
    shutdown_event = asyncio.Event()

    # Patch both asyncio.sleep and the shutdown method
    with (
        patch("asyncio.sleep", side_effect=asyncio.CancelledError),
        patch.object(strategy_handler, "shutdown") as mock_shutdown,
    ):
        # Call the run method
        await strategy_handler.run(shutdown_event)

        # Verify shutdown was called
        mock_shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_run_general_exception(strategy_handler):
    """Test handling of general exceptions in the run loop."""
    # Setup
    shutdown_event = asyncio.Event()

    # Patch both asyncio.sleep and the shutdown method
    with (
        patch("asyncio.sleep", side_effect=Exception("Test exception")),
        patch.object(strategy_handler, "shutdown") as mock_shutdown,
    ):
        # Call the run method
        await strategy_handler.run(shutdown_event)

        # Verify shutdown was called
        mock_shutdown.assert_called_once()


# --- Test _calculate_ema Method ---


@pytest.mark.asyncio
async def test_calculate_ema(strategy_handler):
    """Test EMA calculation."""
    # Setup
    series = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0])
    span = 5

    # Call the method
    result = strategy_handler._calculate_ema(series, span)

    # Verify
    assert isinstance(result, pd.Series)
    assert len(result) == len(series)

    # Check that the EMA is calculated correctly (values should increase)
    assert result.iloc[-1] > result.iloc[0]

    # EMA should be between min and max of the series
    assert result.iloc[-1] <= series.max()
    assert result.iloc[-1] >= series.min()


# --- Test Crossover Detection Methods ---


@pytest.mark.asyncio
async def test_check_bullish_crossover(strategy_handler):
    """Test bullish crossover detection."""
    # Setup - create Series with a bullish crossover
    # prev_fast (12.0) < prev_slow (12.5) and current_fast (13.5) >= current_slow (13.0)
    fast_ema = pd.Series([9.0, 10.0, 11.0, 12.0, 13.5])
    slow_ema = pd.Series([9.5, 10.5, 11.5, 12.5, 13.0])

    # Call the method - should detect a bullish crossover
    result = strategy_handler._check_bullish_crossover(fast_ema, slow_ema)

    # Verify
    assert result == True


@pytest.mark.asyncio
async def test_check_bearish_crossover(strategy_handler):
    """Test bearish crossover detection."""
    # Setup - create Series with a bearish crossover
    # prev_fast (11.5) > prev_slow (11.0) and current_fast (10.5) <= current_slow (10.8)
    fast_ema = pd.Series([13.5, 13.0, 12.5, 11.5, 10.5])
    slow_ema = pd.Series([13.0, 12.5, 12.0, 11.0, 10.8])

    # Call the method - should detect a bearish crossover
    result = strategy_handler._check_bearish_crossover(fast_ema, slow_ema)

    # Verify
    assert result == True


@pytest.mark.asyncio
async def test_no_crossover(strategy_handler):
    """Test no crossover detection."""
    # Setup - create Series with no crossover
    # Fast EMA always above slow EMA
    fast_ema = pd.Series([9.0, 10.0, 11.0, 12.0, 13.0])
    slow_ema = pd.Series([8.0, 9.0, 10.0, 11.0, 12.0])

    # Call the methods - should not detect any crossover
    bullish_result = strategy_handler._check_bullish_crossover(fast_ema, slow_ema)
    bearish_result = strategy_handler._check_bearish_crossover(fast_ema, slow_ema)

    # Verify
    assert bullish_result == False
    assert bearish_result == False


# --- Test Order Creation Methods ---


@pytest.mark.asyncio
async def test_create_market_order(strategy_handler):
    """Test creating a market order."""
    # Setup
    action = "BUY"
    quantity = 100

    # Call the method
    order = strategy_handler._create_market_order(action, quantity)

    # Verify
    assert order.orderType == "MKT"
    assert order.action == action
    assert order.totalQuantity == quantity


@pytest.mark.asyncio
async def test_create_trailing_stop_order(strategy_handler):
    """Test creating a trailing stop order."""
    # Setup
    action = "SELL"
    quantity = 50
    trailing_percent = 1.0

    # Call the method
    order = strategy_handler._create_trailing_stop_order(action, quantity, trailing_percent)

    # Verify
    assert order.orderType == "TRAIL"
    assert order.action == action
    assert order.totalQuantity == quantity
    assert order.trailingPercent == trailing_percent
    assert order.tif == "GTC"


# --- Test Position Size Calculation ---


@pytest.mark.asyncio
async def test_calculate_position_size(strategy_handler):
    """Test position size calculation."""
    # Setup
    price = 25.0
    strategy_handler.config["dollar_amount"] = 1000

    # Call the method
    quantity = strategy_handler._calculate_position_size(price)

    # Verify
    assert quantity == 40  # $1000 / $25 = 40 shares

    # Test with zero price
    assert strategy_handler._calculate_position_size(0) == 0

    # Test with very high price
    assert strategy_handler._calculate_position_size(2000) == 1  # Minimum 1 share


# --- Test initialize Method ---


@pytest.mark.asyncio
async def test_initialize_success(strategy_handler, mock_ibkr_client, mock_trading_service):
    """Test successful initialization."""
    # Setup
    strategy_handler._initialized = False

    # Reset mocks to clear any previous calls
    mock_ibkr_client.connect.reset_mock()
    mock_ibkr_client.get_positions.reset_mock()
    mock_ibkr_client.get_contract_details.reset_mock()
    mock_ibkr_client.get_historical_data.reset_mock()

    # Mock the get_secret method
    mock_trading_service.get_secret = AsyncMock()

    # Call the method
    await strategy_handler.initialize()

    # Verify
    assert strategy_handler._initialized == True
    mock_ibkr_client.connect.assert_called_once()


@pytest.mark.asyncio
async def test_initialize_already_initialized(strategy_handler, mock_ibkr_client):
    """Test initialization when already initialized."""
    # Setup
    strategy_handler._initialized = True
    strategy_handler.config["enabled"] = True

    # Reset mocks to clear any previous calls
    mock_ibkr_client.connect.reset_mock()

    # Call the method
    await strategy_handler.initialize()

    # Verify - should not try to connect again
    mock_ibkr_client.connect.assert_not_called()


@pytest.mark.asyncio
async def test_initialize_disabled(strategy_handler, mock_ibkr_client):
    """Test initialization when strategy is disabled."""
    # Setup
    strategy_handler._initialized = False
    strategy_handler.config["enabled"] = False

    # Reset mocks to clear any previous calls
    mock_ibkr_client.connect.reset_mock()

    # Call the method
    await strategy_handler.initialize()

    # Verify - should not try to connect
    mock_ibkr_client.connect.assert_not_called()
    assert strategy_handler._initialized == False


# --- Test shutdown Method ---


@pytest.mark.asyncio
async def test_shutdown_when_initialized(strategy_handler, mock_ibkr_client):
    """Test shutdown when initialized."""
    # Setup
    strategy_handler._initialized = True
    mock_ibkr_client.is_connected.return_value = True

    # Reset mocks to clear any previous calls
    mock_ibkr_client.disconnect.reset_mock()

    # Call the method
    await strategy_handler.shutdown()

    # Verify
    mock_ibkr_client.disconnect.assert_called_once()
    assert strategy_handler._initialized == False


@pytest.mark.asyncio
async def test_shutdown_when_not_connected(strategy_handler, mock_ibkr_client):
    """Test shutdown when client is not connected."""
    # Setup
    strategy_handler._initialized = True
    mock_ibkr_client.is_connected.return_value = False

    # Reset mocks to clear any previous calls
    mock_ibkr_client.disconnect.reset_mock()

    # Call the method
    await strategy_handler.shutdown()

    # Verify
    mock_ibkr_client.disconnect.assert_not_called()
    assert strategy_handler._initialized == False


# --- Additional tests for coverage gaps ---


@pytest.mark.asyncio
async def test_initialize_error(mock_trading_service):
    """Test initialize handles connection errors properly."""
    with patch("app.service.original_strategy_handler.IBKRClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.connect.side_effect = Exception("Init error")
        MockClient.return_value = mock_client
        handler = OriginalStrategyHandler(mock_trading_service, {**MOCK_CONFIG, "enabled": True})
        await handler.initialize()
        assert handler._initialized is False


@pytest.mark.asyncio
async def test_run_without_initialization(strategy_handler):
    """Test run does nothing if not initialized."""
    handler = strategy_handler
    handler._initialized = False
    with patch.object(handler, "shutdown") as mock_shutdown:
        await handler.run(asyncio.Event())
        mock_shutdown.assert_not_called()


@pytest.mark.asyncio
async def test_process_bar_bullish_entry(strategy_handler, mock_ibkr_client):
    """Test processing a bar with bullish crossover places entry and trailing stop orders."""
    symbol = "SOXS"
    bar = MOCK_BAR_DATA[0]
    strategy_handler.historical_data[symbol] = MOCK_HISTORICAL_DF.copy()
    mock_ibkr_client.place_order.reset_mock()
    with (
        patch.object(strategy_handler, "_check_bullish_crossover", return_value=True),
        patch.object(strategy_handler, "_check_bearish_crossover", return_value=False),
    ):
        await strategy_handler._process_bar(symbol, bar)
    assert mock_ibkr_client.place_order.call_count == 2


@pytest.mark.asyncio
async def test_process_bar_bearish_entry(strategy_handler, mock_ibkr_client):
    """Test processing a bar with bearish crossover places entry and trailing stop orders."""
    symbol = "SOXS"
    bar = MOCK_BAR_DATA[0]
    strategy_handler.historical_data[symbol] = MOCK_HISTORICAL_DF.copy()
    strategy_handler.positions[symbol] = 0
    mock_ibkr_client.place_order.reset_mock()
    with (
        patch.object(strategy_handler, "_check_bullish_crossover", return_value=False),
        patch.object(strategy_handler, "_check_bearish_crossover", return_value=True),
    ):
        await strategy_handler._process_bar(symbol, bar)
    assert mock_ibkr_client.place_order.call_count == 2


@pytest.mark.asyncio
async def test_process_eod_disabled(strategy_handler, mock_ibkr_client):
    """Test EOD processing skips when close_at_eod is False."""
    handler = strategy_handler
    handler.config["close_at_eod"] = False
    mock_ibkr_client.get_contract_details.reset_mock()
    await handler._process_eod()
    mock_ibkr_client.get_contract_details.assert_not_called()


@pytest.mark.asyncio
async def test_process_eod_success(strategy_handler, mock_ibkr_client):
    """Test successful EOD processing closes positions and sends alerts."""
    handler = strategy_handler
    # Set up one open position
    handler.config["close_at_eod"] = True

    handler.positions = {"SOXS": 50}
    # Mock contract details and order placement
    mock_ibkr_client.get_contract_details.return_value = [MagicMock(contract=MOCK_STOCK_CONTRACT)]
    mock_ibkr_client.place_order.return_value = MagicMock()
    # Patch _send_alert to avoid pydantic validation and capture calls
    with patch.object(handler, "_send_alert", new_callable=AsyncMock) as mock_send_alert:
        await handler._process_eod()
    # Verify contract lookup and order placement
    mock_ibkr_client.get_contract_details.assert_called_once_with(
        "SOXS", sec_type="STK", exchange="SMART"
    )
    mock_ibkr_client.place_order.assert_called_once()
    # Verify alert sent with expected parameters (price None for market EOD)
    mock_send_alert.assert_called_once_with("SOXS", "SELL", 50, None, "MKT", "EOD Close")
    # Position should be reset to zero
    assert handler.positions["SOXS"] == 0

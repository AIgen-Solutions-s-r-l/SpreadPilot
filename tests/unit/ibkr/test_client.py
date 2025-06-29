import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import ib_insync
import pytest
from ib_insync import BarData, CommissionReport, Fill, Order, Stock
from ib_insync import OrderStatus as IBOrderStatus
from ib_insync import Trade as IBTrade

from spreadpilot_core.ibkr.client import IBKRClient

# Mock data
MOCK_STOCK_CONTRACT = Stock(symbol="AAPL", exchange="SMART", currency="USD", conId=123)
MOCK_BAR_DATA = [
    BarData(
        date=datetime.datetime(2025, 4, 18, 10, 0, 0),
        open=150.0,
        high=151.0,
        low=149.0,
        close=150.5,
        volume=1000,
        average=150.2,
        barCount=100,
    ),
    BarData(
        date=datetime.datetime(2025, 4, 18, 10, 1, 0),
        open=150.5,
        high=151.5,
        low=149.5,
        close=151.0,
        volume=1200,
        average=150.8,
        barCount=120,
    ),
]
MOCK_ORDER = Order(orderId=1, action="BUY", totalQuantity=100, orderType="MKT")
MOCK_TRADE = IBTrade(
    contract=MOCK_STOCK_CONTRACT,
    order=MOCK_ORDER,
    orderStatus=IBOrderStatus(
        status="Filled", filled=100, remaining=0, avgFillPrice=150.5
    ),
    fills=[
        Fill(
            contract=MOCK_STOCK_CONTRACT,
            execution=MagicMock(avgPrice=150.5, shares=100),
            commissionReport=CommissionReport(
                commission=1.0, currency="USD"
            ),  # Added mock commission report
            time=datetime.datetime.now(),  # Added mock time
        )
    ],
    log=[],
)
MOCK_POSITIONS_RAW = [
    MagicMock(contract=Stock(symbol="AAPL", conId=123), position=100.0),
    MagicMock(contract=Stock(symbol="MSFT", conId=456), position=-50.0),
    MagicMock(
        contract=Stock(symbol="GOOG", conId=789), position=0.0
    ),  # Test zero position
]


@pytest.fixture
def mock_ib_insync():
    """Fixture to mock the ib_insync.IB instance."""
    mock = MagicMock(spec=ib_insync.IB)
    mock.connectAsync = AsyncMock(return_value=None)
    mock.isConnected = MagicMock(return_value=True)
    mock.reqHistoricalDataAsync = AsyncMock(return_value=MOCK_BAR_DATA)
    mock.placeOrder = MagicMock(return_value=MOCK_TRADE)
    mock.reqPositionsAsync = AsyncMock(return_value=MOCK_POSITIONS_RAW)
    # Mock qualifyContractsAsync if needed for get_stock_contract testing
    # mock.qualifyContractsAsync = AsyncMock(return_value=[MOCK_STOCK_CONTRACT])
    return mock


@pytest.fixture
async def ibkr_client(mock_ib_insync):
    """Fixture to create an IBKRClient instance with a mocked IB connection."""
    with patch(
        "spreadpilot_core.ibkr.client.ib_insync.IB", return_value=mock_ib_insync
    ):
        client = IBKRClient(username="testuser", password="testpassword")
        # Mock the internal _connected flag and ib instance directly after init
        client.ib = mock_ib_insync
        client._connected = True
        # Mock ensure_connected to always return True for unit tests
        client.ensure_connected = AsyncMock(return_value=True)
        yield client
        # No explicit disconnect needed as the mock handles it


# --- Test get_stock_contract ---


@pytest.mark.asyncio
async def test_get_stock_contract_success(ibkr_client: IBKRClient):
    """Test successful stock contract creation."""
    symbol = "AAPL"
    exchange = "NASDAQ"
    currency = "USD"

    # If qualification is added, mock ibkr_client.ib.qualifyContractsAsync here
    # ibkr_client.ib.qualifyContractsAsync = AsyncMock(return_value=[Stock(symbol=symbol, exchange=exchange, currency=currency, conId=123)])

    contract = await ibkr_client.get_stock_contract(symbol, exchange, currency)

    assert isinstance(contract, Stock)
    assert contract.symbol == symbol
    assert contract.exchange == exchange
    assert contract.currency == currency
    # ibkr_client.ib.qualifyContractsAsync.assert_called_once() # Uncomment if qualification is added


@pytest.mark.asyncio
async def test_get_stock_contract_defaults(ibkr_client: IBKRClient):
    """Test stock contract creation with default exchange and currency."""
    symbol = "TSLA"
    contract = await ibkr_client.get_stock_contract(symbol)

    assert isinstance(contract, Stock)
    assert contract.symbol == symbol
    assert contract.exchange == "SMART"
    assert contract.currency == "USD"


@pytest.mark.asyncio
async def test_get_stock_contract_error(ibkr_client: IBKRClient):
    """Test error during stock contract creation (e.g., qualification fails)."""
    symbol = "ERROR"
    # Mock qualification failure if qualification is added
    # ibkr_client.ib.qualifyContractsAsync = AsyncMock(return_value=[])

    # For now, just test basic instantiation error (less likely but good practice)
    with patch(
        "spreadpilot_core.ibkr.client.Stock", side_effect=ValueError("Test Error")
    ):
        with pytest.raises(ValueError, match="Test Error"):
            await ibkr_client.get_stock_contract(symbol)


# --- Test request_historical_data ---


@pytest.mark.asyncio
async def test_request_historical_data_success(
    ibkr_client: IBKRClient, mock_ib_insync: MagicMock
):
    """Test successful historical data request."""
    bars = await ibkr_client.request_historical_data(
        MOCK_STOCK_CONTRACT, durationStr="5 D", barSizeSetting="1 hour"
    )

    assert bars == MOCK_BAR_DATA
    mock_ib_insync.reqHistoricalDataAsync.assert_called_once_with(
        MOCK_STOCK_CONTRACT,
        endDateTime="",
        durationStr="5 D",
        barSizeSetting="1 hour",
        whatToShow="TRADES",
        useRTH=True,
        formatDate=1,
    )
    ibkr_client.ensure_connected.assert_called_once()


@pytest.mark.asyncio
async def test_request_historical_data_not_connected(
    ibkr_client: IBKRClient, mock_ib_insync: MagicMock
):
    """Test historical data request when not connected."""
    ibkr_client.ensure_connected = AsyncMock(return_value=False)  # Override fixture

    bars = await ibkr_client.request_historical_data(MOCK_STOCK_CONTRACT)

    assert bars == []
    mock_ib_insync.reqHistoricalDataAsync.assert_not_called()
    ibkr_client.ensure_connected.assert_called_once()


@pytest.mark.asyncio
async def test_request_historical_data_api_error(
    ibkr_client: IBKRClient, mock_ib_insync: MagicMock
):
    """Test historical data request when API call fails."""
    mock_ib_insync.reqHistoricalDataAsync.side_effect = ConnectionError("API Failed")

    bars = await ibkr_client.request_historical_data(MOCK_STOCK_CONTRACT)

    assert bars == []
    mock_ib_insync.reqHistoricalDataAsync.assert_called_once()
    ibkr_client.ensure_connected.assert_called_once()


# --- Test place_order ---


@pytest.mark.asyncio
async def test_place_order_success(ibkr_client: IBKRClient, mock_ib_insync: MagicMock):
    """Test successful order placement."""
    trade = await ibkr_client.place_order(MOCK_STOCK_CONTRACT, MOCK_ORDER)

    assert trade == MOCK_TRADE
    mock_ib_insync.placeOrder.assert_called_once_with(MOCK_STOCK_CONTRACT, MOCK_ORDER)
    ibkr_client.ensure_connected.assert_called_once()


@pytest.mark.asyncio
async def test_place_order_not_connected(
    ibkr_client: IBKRClient, mock_ib_insync: MagicMock
):
    """Test order placement when not connected."""
    ibkr_client.ensure_connected = AsyncMock(return_value=False)  # Override fixture

    trade = await ibkr_client.place_order(MOCK_STOCK_CONTRACT, MOCK_ORDER)

    assert trade is None
    mock_ib_insync.placeOrder.assert_not_called()
    ibkr_client.ensure_connected.assert_called_once()


@pytest.mark.asyncio
async def test_place_order_api_error(
    ibkr_client: IBKRClient, mock_ib_insync: MagicMock
):
    """Test order placement when API call fails."""
    mock_ib_insync.placeOrder.side_effect = ValueError("Order Rejected")

    trade = await ibkr_client.place_order(MOCK_STOCK_CONTRACT, MOCK_ORDER)

    assert trade is None
    mock_ib_insync.placeOrder.assert_called_once_with(MOCK_STOCK_CONTRACT, MOCK_ORDER)
    ibkr_client.ensure_connected.assert_called_once()


# --- Test request_stock_positions ---


@pytest.mark.asyncio
async def test_request_stock_positions_success(
    ibkr_client: IBKRClient, mock_ib_insync: MagicMock
):
    """Test successful stock position retrieval."""
    symbols = ["AAPL", "MSFT", "GOOG", "AMZN"]  # AMZN not in mock data
    expected_positions = {"AAPL": 100.0, "MSFT": -50.0, "GOOG": 0.0, "AMZN": 0.0}

    positions = await ibkr_client.request_stock_positions(symbols)

    assert positions == expected_positions
    mock_ib_insync.reqPositionsAsync.assert_called_once()
    ibkr_client.ensure_connected.assert_called_once()


@pytest.mark.asyncio
async def test_request_stock_positions_case_insensitive(
    ibkr_client: IBKRClient, mock_ib_insync: MagicMock
):
    """Test case-insensitive symbol matching for positions."""
    symbols = ["aapl", "MsFt"]
    expected_positions = {"aapl": 100.0, "MsFt": -50.0}  # Keys should match input case

    # Adjust mock return value symbol case for this test if needed, but logic handles it
    # MOCK_POSITIONS_RAW_CASE = [
    #     MagicMock(contract=Stock(symbol="AAPL", conId=123), position=100.0),
    #     MagicMock(contract=Stock(symbol="MSFT", conId=456), position=-50.0),
    # ]
    # mock_ib_insync.reqPositionsAsync.return_value = MOCK_POSITIONS_RAW_CASE

    positions = await ibkr_client.request_stock_positions(symbols)

    # We need to compare ignoring case in keys for correctness here
    assert positions.get("aapl") == 100.0
    assert positions.get("MsFt") == -50.0
    assert len(positions) == 2


@pytest.mark.asyncio
async def test_request_stock_positions_not_connected(
    ibkr_client: IBKRClient, mock_ib_insync: MagicMock
):
    """Test stock position retrieval when not connected."""
    ibkr_client.ensure_connected = AsyncMock(return_value=False)  # Override fixture
    symbols = ["AAPL"]

    positions = await ibkr_client.request_stock_positions(symbols)

    assert positions == {}
    mock_ib_insync.reqPositionsAsync.assert_not_called()
    ibkr_client.ensure_connected.assert_called_once()


@pytest.mark.asyncio
async def test_request_stock_positions_api_error(
    ibkr_client: IBKRClient, mock_ib_insync: MagicMock
):
    """Test stock position retrieval when API call fails."""
    mock_ib_insync.reqPositionsAsync.side_effect = TimeoutError("Request Timed Out")
    symbols = ["AAPL"]

    positions = await ibkr_client.request_stock_positions(symbols)

    assert positions == {}
    mock_ib_insync.reqPositionsAsync.assert_called_once()
    ibkr_client.ensure_connected.assert_called_once()


@pytest.mark.asyncio
async def test_request_stock_positions_empty_symbols(
    ibkr_client: IBKRClient, mock_ib_insync: MagicMock
):
    """Test requesting positions with an empty list of symbols."""
    symbols = []
    expected_positions = {}

    positions = await ibkr_client.request_stock_positions(symbols)

    assert positions == expected_positions
    # reqPositionsAsync might still be called by the implementation, which is fine
    # mock_ib_insync.reqPositionsAsync.assert_called_once()
    ibkr_client.ensure_connected.assert_called_once()


@pytest.mark.asyncio
async def test_request_stock_positions_no_matching(
    ibkr_client: IBKRClient, mock_ib_insync: MagicMock
):
    """Test requesting positions for symbols that don't exist in the account."""
    symbols = ["IBM", "ORCL"]
    expected_positions = {"IBM": 0.0, "ORCL": 0.0}

    positions = await ibkr_client.request_stock_positions(symbols)

    assert positions == expected_positions
    mock_ib_insync.reqPositionsAsync.assert_called_once()
    ibkr_client.ensure_connected.assert_called_once()

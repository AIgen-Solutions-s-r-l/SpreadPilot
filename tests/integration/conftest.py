"""Pytest fixtures for SpreadPilot integration tests."""

import asyncio
import datetime
import os
import uuid
from typing import Dict, List, Optional, Any, Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from google.cloud import firestore
from fastapi.testclient import TestClient

from spreadpilot_core.models.follower import Follower, FollowerState
from spreadpilot_core.models.trade import Trade, TradeSide, TradeStatus
from spreadpilot_core.models.position import Position, AssignmentState
from spreadpilot_core.models.alert import Alert, AlertSeverity, AlertType
from spreadpilot_core.ibkr.client import IBKRClient, OrderStatus

# Import services for testing
import importlib

# Import modules using importlib
trading_bot_service = importlib.import_module('trading-bot.app.service.signals')
trading_bot_sheets = importlib.import_module('trading-bot.app.sheets')
alert_router_service = importlib.import_module('alert-router.app.service.router')
report_worker_service = importlib.import_module('report-worker.app.service.pnl')
admin_api_main = importlib.import_module('admin-api.app.main')

# Get specific imports
SignalProcessor = trading_bot_service.SignalProcessor
GoogleSheetsClient = trading_bot_sheets.GoogleSheetsClient
route_alert = alert_router_service.route_alert
calculate_monthly_pnl = report_worker_service.calculate_monthly_pnl
admin_app = admin_api_main.app


# ---- Environment Setup ----

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment variables."""
    # Set environment variables for testing
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    os.environ["GOOGLE_CLOUD_PROJECT"] = "spreadpilot-test"
    os.environ["TESTING"] = "true"
    
    # Yield to allow tests to run
    yield
    
    # Clean up (if needed)
    pass


# ---- Mock IBKR Client ----

class MockIBKRClient:
    """Mock IBKR client for testing."""
    
    def __init__(self):
        self.connected = False
        self.orders = []
        self.positions = {}
        self.account_summary = {
            "NetLiquidation": 100000.0,
            "AvailableFunds": 50000.0,
            "MaintMarginReq": 20000.0,
        }
        self.pnl = {
            "DailyPnL": 1000.0,
            "UnrealizedPnL": 500.0,
            "RealizedPnL": 500.0,
        }
    
    async def connect(self) -> bool:
        """Mock connect method."""
        self.connected = True
        return True
    
    async def disconnect(self) -> None:
        """Mock disconnect method."""
        self.connected = False
    
    async def ensure_connected(self) -> bool:
        """Mock ensure_connected method."""
        return self.connected
    
    async def place_vertical_spread(
        self,
        strategy: str,
        qty_per_leg: int,
        strike_long: float,
        strike_short: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock place_vertical_spread method."""
        order_id = str(uuid.uuid4())
        order = {
            "id": order_id,
            "strategy": strategy,
            "qty_per_leg": qty_per_leg,
            "strike_long": strike_long,
            "strike_short": strike_short,
            "status": OrderStatus.FILLED,
            "fill_price": 0.75,
            "fill_time": datetime.datetime.now().isoformat(),
        }
        self.orders.append(order)
        return {
            "status": OrderStatus.FILLED,
            "trade_id": order_id,
            "fill_price": 0.75,
            "fill_time": datetime.datetime.now().isoformat(),
        }
    
    async def update_positions(self) -> bool:
        """Mock update_positions method."""
        return True
    
    async def get_positions(self, force_update: bool = False) -> Dict[str, int]:
        """Mock get_positions method."""
        return self.positions
    
    async def check_assignment(self) -> tuple[AssignmentState, int, int]:
        """Mock check_assignment method."""
        return AssignmentState.NONE, 0, 0
    
    async def exercise_options(self, qty: int) -> Dict[str, Any]:
        """Mock exercise_options method."""
        return {
            "success": True,
            "qty_exercised": qty,
        }
    
    async def close_all_positions(self) -> Dict[str, Any]:
        """Mock close_all_positions method."""
        self.positions = {}
        return {
            "success": True,
            "positions_closed": 2,
        }
    
    async def get_account_summary(self) -> Dict[str, Any]:
        """Mock get_account_summary method."""
        return self.account_summary
    
    async def check_margin_for_trade(
        self,
        strategy: str,
        qty_per_leg: int,
        strike_long: float,
        strike_short: float,
    ) -> tuple[bool, Optional[str]]:
        """Mock check_margin_for_trade method."""
        return True, None
    
    async def get_pnl(self) -> Dict[str, float]:
        """Mock get_pnl method."""
        return self.pnl


@pytest.fixture
def mock_ibkr_client():
    """Fixture for mock IBKR client."""
    return MockIBKRClient()


@pytest_asyncio.fixture
async def patched_ibkr_client(mock_ibkr_client):
    """Fixture to patch the IBKRClient with the mock."""
    with patch("spreadpilot_core.ibkr.client.IBKRClient", return_value=mock_ibkr_client):
        yield mock_ibkr_client


# ---- Mock Google Sheets Client ----

class MockGoogleSheetsClient:
    """Mock Google Sheets client for testing."""
    
    def __init__(self, sheet_url: str = "https://example.com/sheet", api_key: Optional[str] = None):
        self.sheet_url = sheet_url
        self.api_key = api_key
        self.sheet_id = "mock-sheet-id"
        self.connected = False
        self.last_fetch_time = None
        self.last_signal = None
        self.test_signals = []
    
    async def connect(self) -> bool:
        """Mock connect method."""
        self.connected = True
        return True
    
    def is_connected(self) -> bool:
        """Mock is_connected method."""
        return self.connected
    
    def add_test_signal(self, signal: Dict[str, Any]):
        """Add a test signal for testing."""
        self.test_signals.append(signal)
    
    async def fetch_signal(self) -> Optional[Dict[str, Any]]:
        """Mock fetch_signal method."""
        if not self.test_signals:
            return None
        
        signal = self.test_signals.pop(0)
        self.last_fetch_time = datetime.datetime.now()
        self.last_signal = signal
        return signal
    
    async def wait_for_signal(self, timeout_seconds: int = 1) -> Optional[Dict[str, Any]]:
        """Mock wait_for_signal method."""
        return await self.fetch_signal()


@pytest.fixture
def mock_sheets_client():
    """Fixture for mock Google Sheets client."""
    client = MockGoogleSheetsClient()
    
    # Add a test signal
    client.add_test_signal({
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "ticker": "QQQ",
        "strategy": "Long",  # Bull Put
        "qty_per_leg": 1,
        "strike_long": 380.0,
        "strike_short": 385.0,
    })
    
    return client


@pytest_asyncio.fixture
async def patched_sheets_client(mock_sheets_client):
    """Fixture to patch the GoogleSheetsClient with the mock."""
    with patch("trading_bot.app.sheets.GoogleSheetsClient", return_value=mock_sheets_client):
        yield mock_sheets_client


# ---- Firestore Emulator Client ----

@pytest_asyncio.fixture
async def firestore_client():
    """Fixture for Firestore client using emulator."""
    # Ensure environment variables are set
    assert os.environ.get("FIRESTORE_EMULATOR_HOST"), "Firestore emulator host not set"
    assert os.environ.get("GOOGLE_CLOUD_PROJECT"), "Google Cloud project not set"
    
    # Create client
    client = firestore.Client()
    
    # Clear collections before tests
    collections = ["followers", "trades", "positions", "alerts", "daily_pnl", "monthly_reports"]
    for collection in collections:
        docs = client.collection(collection).stream()
        for doc in docs:
            doc.reference.delete()
    
    yield client
    
    # Clean up after tests
    for collection in collections:
        docs = client.collection(collection).stream()
        for doc in docs:
            doc.reference.delete()


# ---- Test Data Fixtures ----

@pytest_asyncio.fixture
async def test_follower(firestore_client):
    """Fixture to create a test follower in Firestore."""
    follower_id = f"test-follower-{uuid.uuid4()}"
    follower = Follower(
        id=follower_id,
        email="test@example.com",
        iban="NL91ABNA0417164300",
        ibkr_username="testuser",
        ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-testuser",
        commission_pct=20.0,
        enabled=True,
        state=FollowerState.ACTIVE,
    )
    
    # Save to Firestore
    firestore_client.collection("followers").document(follower_id).set(follower.to_dict())
    
    yield follower
    
    # Clean up
    firestore_client.collection("followers").document(follower_id).delete()


@pytest_asyncio.fixture
async def test_trade(firestore_client, test_follower):
    """Fixture to create a test trade in Firestore."""
    trade_id = f"test-trade-{uuid.uuid4()}"
    trade = Trade(
        id=trade_id,
        follower_id=test_follower.id,
        side=TradeSide.LONG,
        qty=1,
        strike=380.0,
        limit_price_requested=0.75,
        status=TradeStatus.FILLED,
        timestamps={
            "submitted": datetime.datetime.now(),
            "filled": datetime.datetime.now(),
        },
    )
    
    # Save to Firestore
    firestore_client.collection("trades").document(trade_id).set(trade.to_dict())
    
    yield trade
    
    # Clean up
    firestore_client.collection("trades").document(trade_id).delete()


@pytest_asyncio.fixture
async def test_position(firestore_client, test_follower):
    """Fixture to create a test position in Firestore."""
    date = datetime.datetime.now().strftime("%Y%m%d")
    position = Position(
        follower_id=test_follower.id,
        date=date,
        short_qty=1,
        long_qty=1,
        pnl_realized=0.0,
        pnl_mtm=0.0,
        assignment_state=AssignmentState.NONE,
    )
    
    # Save to Firestore
    doc_path = f"positions/{test_follower.id}/daily/{date}"
    firestore_client.document(doc_path).set(position.to_dict())
    
    yield position
    
    # Clean up
    firestore_client.document(doc_path).delete()


# ---- Service Fixtures ----

@pytest_asyncio.fixture
async def signal_processor(patched_ibkr_client, firestore_client):
    """Fixture for SignalProcessor with mocked dependencies."""
    # Create a mock trading service
    mock_service = MagicMock()
    mock_service.active_followers = {"test-follower-id": True}
    mock_service.ibkr_manager.place_vertical_spread = patched_ibkr_client.place_vertical_spread
    mock_service.ibkr_manager.check_margin_for_trade = patched_ibkr_client.check_margin_for_trade
    mock_service.db = firestore_client
    
    # Create alert manager mock
    mock_service.alert_manager.create_alert = AsyncMock()
    
    # Create position manager mock
    mock_service.position_manager.update_position = AsyncMock()
    
    # Create settings mock
    mock_service.settings = MagicMock()
    mock_service.settings.min_price = 0.70
    
    processor = SignalProcessor(mock_service)
    yield processor


@pytest.fixture
def admin_api_client():
    """Fixture for FastAPI TestClient for admin API."""
    with TestClient(admin_app) as client:
        yield client


# ---- Mock Email and Telegram ----

@pytest_asyncio.fixture
async def mock_email_sender():
    """Fixture to mock email sending."""
    with patch("spreadpilot_core.utils.email.send_email") as mock:
        mock.return_value = True
        yield mock


@pytest_asyncio.fixture
async def mock_telegram_sender():
    """Fixture to mock Telegram sending."""
    with patch("spreadpilot_core.utils.telegram.send_telegram_message") as mock:
        mock.return_value = True
        yield mock
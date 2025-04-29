import sys # Keep sys import if needed elsewhere, otherwise remove if only used for path
import os

# """Pytest fixtures for SpreadPilot integration tests.""" # Moved path logic to test files
"""Pytest fixtures for SpreadPilot integration tests."""

import asyncio
import datetime
import os
import uuid
from typing import Dict, List, Optional, Any, Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
import motor.motor_asyncio # Added for MongoDB
from testcontainers.mongodb import MongoDbContainer # Added for Testcontainers

import pytest
import pytest_asyncio
# from google.cloud import firestore # Removed Firestore
from fastapi.testclient import TestClient
from fastapi import Depends # Added for dependency override
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase # Added for MongoDB types
# from fastapi.testclient import TestClient # Remove TestClient
import httpx # Re-add httpx import
# from anyio.abc import TestClient as AnyioTestClient # Remove anyio import

# Import the dependency getter to override using importlib
# from admin_api.app.db.mongodb import get_mongo_db # Replaced with importlib below

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
# report_worker_service = importlib.import_module('report-worker.app.service.pnl') # Removed - Not needed for admin_api tests, causes credential error
admin_api_main = importlib.import_module('admin_api.app.main')
admin_api_mongodb_db = importlib.import_module('admin_api.app.db.mongodb') # Added for get_mongo_db

# Get specific imports
SignalProcessor = trading_bot_service.SignalProcessor
GoogleSheetsClient = trading_bot_sheets.GoogleSheetsClient
route_alert = alert_router_service.route_alert
# calculate_monthly_pnl = report_worker_service.calculate_monthly_pnl # Removed
admin_app = admin_api_main.app
get_mongo_db = admin_api_mongodb_db.get_mongo_db # Get the function to override


# ---- Environment Setup ----

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment variables and mock external services."""
    # Set environment variables for testing
    # os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8084" # Removed Firestore emulator env var
    os.environ["GOOGLE_CLOUD_PROJECT"] = "spreadpilot-test" # Keep if needed elsewhere, otherwise remove
    os.environ["TESTING"] = "true"
    # Add MongoDB URI override if needed by settings, otherwise Testcontainers handles it
    # os.environ["MONGO_URI_OVERRIDE"] = "mongodb://test:test@localhost:27017" # Example

    # Mock firestore client globally to prevent credential errors during collection/imports
    with patch("google.cloud.firestore.Client", MagicMock()) as mock_firestore:
        # Yield to allow tests to run with the mock active
        yield mock_firestore

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
        follower_id: Optional[str] = None, # Add follower_id
        **kwargs # Add kwargs to accept unexpected args
    ) -> tuple[bool, Optional[str]]:
        """Mock check_margin_for_trade method."""
        # Basic mock logic, can be enhanced if needed
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


# ---- MongoDB Testcontainer Fixture ----

@pytest.fixture(scope="session")
def mongodb_container() -> Generator[MongoDbContainer, None, None]:
    """Starts and stops a MongoDB Testcontainer for the test session."""
    # Using a specific image version known to work well
    with MongoDbContainer("mongo:6.0") as mongo:
        yield mongo

# ---- MongoDB Test Database Fixture ----

@pytest_asyncio.fixture(scope="function")
async def test_mongo_db(mongodb_container: MongoDbContainer) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Provides a connection to a unique test database within the MongoDB container."""
    mongo_uri = mongodb_container.get_connection_url()
    test_db_name = f"test_db_{uuid.uuid4().hex}"
    # Get the current event loop provided by pytest-asyncio
    # Motor should pick up the correct loop automatically when run via pytest-asyncio/anyio
    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    db = client[test_db_name]
    print(f"Using test MongoDB: {mongo_uri}/{test_db_name}") # For debugging

    yield db # Provide the database object to the test

    # Cleanup: Drop the test database after the test function completes
    await client.drop_database(test_db_name)
    client.close()
    print(f"Dropped test MongoDB database: {test_db_name}") # For debugging

# ---- FastAPI Dependency Override ----

async def override_get_mongo_db(test_db: AsyncIOMotorDatabase = Depends(test_mongo_db)) -> AsyncIOMotorDatabase:
    """Dependency override function that returns the test_mongo_db fixture."""
    return test_db

# ---- Service Fixtures ----

# Note: signal_processor fixture still uses firestore_client.
# This will need to be updated if signal_processor also moves to MongoDB.
# For now, we focus on admin_api_client.
@pytest_asyncio.fixture
async def signal_processor(patched_ibkr_client): # Removed firestore_client dependency
    """Fixture for SignalProcessor with mocked dependencies.
       WARNING: Database dependency needs update if SignalProcessor uses MongoDB.
    """
    # Create a mock trading service
    mock_service = MagicMock()
    mock_service.active_followers = {"test-follower-id": True}
    mock_service.ibkr_manager.place_vertical_spread = patched_ibkr_client.place_vertical_spread
    mock_service.ibkr_manager.check_margin_for_trade = patched_ibkr_client.check_margin_for_trade
    # mock_service.db = firestore_client # Removed Firestore dependency

    # Create alert manager mock
    mock_service.alert_manager.create_alert = AsyncMock()

    # Create position manager mock
    mock_service.position_manager.update_position = AsyncMock()

    # Create settings mock
    mock_service.settings = MagicMock()
    mock_service.settings.min_price = 0.70

    processor = SignalProcessor(mock_service)
    yield processor


# Re-add httpx import

@pytest_asyncio.fixture # Keep as async fixture
async def admin_api_client(test_mongo_db: AsyncIOMotorDatabase) -> AsyncGenerator[httpx.AsyncClient, None]: # Change type hint back to httpx
    """Async fixture providing an httpx.AsyncClient against the admin_api app with MongoDB override."""
    # Override the get_mongo_db dependency for the test client (used by endpoints via Depends)
    admin_app.dependency_overrides[get_mongo_db] = lambda: test_mongo_db

    # Patch the direct async call within the dashboard's background task fallback logic
    # The patch needs to return an awaitable that yields the test_mongo_db instance
    async def mock_get_mongo_db_for_task():
        return test_mongo_db

    # Patch both the endpoint dependency injection AND the direct call in the dashboard background task
    # Use the correct import path for patching
    dashboard_endpoint_path = "admin_api.app.api.v1.endpoints.dashboard" # Use underscore
    followers_endpoint_path = "admin_api.app.api.v1.endpoints.followers" # Use underscore

    with patch(f"{dashboard_endpoint_path}.get_mongo_db", new=mock_get_mongo_db_for_task), \
         patch(f"{followers_endpoint_path}.get_mongo_db", new=mock_get_mongo_db_for_task): # Ensure followers endpoint is also patched if direct calls exist
        # Use ASGITransport for testing ASGI apps like FastAPI with httpx
        transport = httpx.ASGITransport(app=admin_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client

    # Clean up the override after the fixture scope ends
    admin_app.dependency_overrides.clear()


# ---- Test Data Fixtures ----

@pytest_asyncio.fixture(scope="function")
async def test_follower(test_mongo_db: AsyncIOMotorDatabase) -> Follower:
    """Fixture to create a sample follower in the test MongoDB."""
    follower_data = {
        "_id": "test-follower-id", # Use a fixed ID for predictability
        "name": "Test Follower",
        "email": "test.follower@example.com",
        "phone": "+1234567890",
        "ibkr_account_id": "U123456",
        "commission_pct": 20.0,
        "state": FollowerState.ACTIVE.value,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
        "telegram_chat_id": "12345",
        "max_risk_per_trade": 100.0,
        "assigned_options": [],
        "daily_pnl": 0.0,
        "monthly_pnl": 0.0,
        "total_pnl": 0.0,
        # Add missing required fields
        "iban": "DE89 3704 0044 0532 0130 00",
        "ibkr_username": "testuser",
        "ibkr_secret_ref": "projects/spreadpilot-test/secrets/test-ibkr-secret/versions/latest", # Example ref
    }
    # Insert the follower data
    await test_mongo_db.followers.insert_one(follower_data)
    print(f"Inserted test follower: {follower_data['_id']}") # Debugging

    # Yield a Pydantic model instance
    yield Follower(**follower_data)

    # Cleanup: Remove the follower after the test
    await test_mongo_db.followers.delete_one({"_id": follower_data["_id"]})
    print(f"Deleted test follower: {follower_data['_id']}") # Debugging


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
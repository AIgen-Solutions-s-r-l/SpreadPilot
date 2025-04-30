import httpx_ws # Explicitly import to ensure patching might occur earlier
import sys # Keep sys import if needed elsewhere, otherwise remove if only used for path
import os

# """Pytest fixtures for SpreadPilot integration tests.""" # Moved path logic to test files
"""Pytest fixtures for SpreadPilot integration tests."""

import asyncio
import datetime
import os
import uuid
import importlib
from typing import Dict, List, Optional, Any, Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
import motor.motor_asyncio # Added for MongoDB
import testcontainers.core.config # Added for timeout adjustment
from testcontainers.mongodb import MongoDbContainer # Added for Testcontainers

import pytest
import pytest_asyncio
# from google.cloud import firestore # Removed Firestore import
from fastapi.testclient import TestClient # Add TestClient import
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import httpx
import uvicorn
import threading
import socket
import time

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
alert_router_service = importlib.import_module('alert_router.app.service.router') # Updated path
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
    # os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8084" # Removed Firestore env var
    os.environ["GOOGLE_CLOUD_PROJECT"] = "spreadpilot-test" # Keep if other services might need it, but admin-api doesn't directly use it now
    os.environ["TESTING"] = "true"
    # MongoDB URI is handled by Testcontainers and dependency injection override

    # Remove global Firestore mock - no longer needed
    # with patch("google.cloud.firestore.Client", MagicMock()) as mock_firestore:
    #     yield mock_firestore
    yield # Yield control to run tests

    # Clean up (if needed)
    # Remove potentially conflicting env vars if set elsewhere, though testcontainers is preferred
    os.environ.pop("FIRESTORE_EMULATOR_HOST", None)


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
    # Increase the default timeout for testcontainers
    original_timeout = testcontainers.core.config.TIMEOUT
    testcontainers.core.config.TIMEOUT = 300 # Increase to 300 seconds
    try:
        with MongoDbContainer("mongo:6.0") as mongo:
            # Add a small delay to allow Docker networking to stabilize, especially on Windows/WSL
            # time.sleep(5) # Keep the sleep, maybe it helps in conjunction with timeout
            yield mongo
    finally:
        # Restore original timeout
        testcontainers.core.config.TIMEOUT = original_timeout

# ---- MongoDB Test Database Fixture ----

@pytest_asyncio.fixture(scope="function")
async def test_mongo_db(mongodb_container: MongoDbContainer) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Provides a connection to a unique test database within the MongoDB container."""
    mongo_uri = mongodb_container.get_connection_url()
    test_db_name = f"test_db_{uuid.uuid4().hex}"
    # Get the current running event loop from asyncio (optional, motor might detect)
    # loop = asyncio.get_running_loop()
    # Initialize motor client WITHOUT explicitly passing the loop
    # Let motor detect the running loop provided by anyio/pytest-asyncio
    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    db = client[test_db_name]
    # print(f"Using test MongoDB: {mongo_uri}/{test_db_name} on loop {id(asyncio.get_running_loop())}") # Debugging if needed

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
       WARNING: This fixture is likely outdated as SignalProcessor probably uses Firestore.
       It's kept here for structure but might need removal or update in a separate task
       focused on refactoring the trading-bot tests.
    """
    # Create a mock trading service
    mock_service = MagicMock()
    mock_service.active_followers = {"test-follower-id": True}
    mock_service.ibkr_manager.place_vertical_spread = patched_ibkr_client.place_vertical_spread
    mock_service.ibkr_manager.check_margin_for_trade = patched_ibkr_client.check_margin_for_trade
    # mock_service.db = firestore_client # Ensure no lingering Firestore reference

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

# Helper function to find a free port
def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

# Uvicorn server runner
class UvicornServer(uvicorn.Server):
    def install_signal_handlers(self):
        pass # Prevent uvicorn from handling signals in tests

    def run_in_thread(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        # Wait briefly for server to start - adjust sleep time if needed
        time.sleep(1.5)

    def stop(self):
        self.should_exit = True
        if hasattr(self, 'thread') and self.thread.is_alive():
             self.thread.join(timeout=1) # Wait briefly for thread to exit

@pytest_asyncio.fixture(scope="function")
async def admin_api_client(mongodb_container: MongoDbContainer) -> AsyncGenerator[tuple[httpx.AsyncClient, Any, str], None]:
    """
    Async fixture providing an httpx.AsyncClient against a running admin_api app instance
    with the FollowerService dependency overridden to use the correct MongoDB connection
    within the Uvicorn thread. Runs the app using Uvicorn in a thread.
    Yields the client, the app instance, and the actual base_url.
    """
    # Get connection details from the container fixture
    mongo_uri = mongodb_container.get_connection_url()
    # Use a consistent test DB name structure if needed, or let service use default
    # test_db_name = f"test_db_{uuid.uuid4().hex}" # Or use settings default

    # Import necessary modules here to avoid potential import cycles
    dashboard_module = importlib.import_module('admin_api.app.api.v1.endpoints.dashboard')
    followers_module = importlib.import_module('admin_api.app.api.v1.endpoints.followers')
    follower_service_module = importlib.import_module('admin_api.app.services.follower_service')
    config_module = importlib.import_module('admin_api.app.core.config')
    FollowerService = follower_service_module.FollowerService
    get_settings_func = config_module.get_settings
    settings = get_settings_func() # Get settings once

    # Define the override function for get_follower_service
    # This will be executed within the Uvicorn thread's event loop
    async def override_get_follower_service_for_thread():
        # Import logger inside the function to ensure it's available in the thread
        from spreadpilot_core.logging.logger import get_logger
        logger = get_logger(__name__ + ".override_get_follower_service_for_thread")

        # Create a NEW motor client and DB connection INSIDE the override
        # This ensures it uses the loop of the thread calling the dependency
        logger.debug(f"Override: Creating new Motor client for {mongo_uri}")
        thread_local_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        thread_local_db = thread_local_client[settings.mongo_db_name] # Use db name from settings
        logger.debug(f"Override: Instantiating FollowerService with thread-local DB")
        service_instance = FollowerService(db=thread_local_db, settings=settings)
        # Note: We might need to manage the closing of thread_local_client if many tests run
        return service_instance

    # Apply the override for the service dependency
    admin_app.dependency_overrides[dashboard_module.get_follower_service] = override_get_follower_service_for_thread
    admin_app.dependency_overrides[followers_module.get_follower_service] = override_get_follower_service_for_thread

    # --- Run App with Uvicorn ---
    host = "127.0.0.1"
    port = find_free_port()
    base_url = f"http://{host}:{port}"

    config = uvicorn.Config(admin_app, host=host, port=port, log_level="warning")
    server = UvicornServer(config=config)
    server.run_in_thread()
    # --- End Run App ---

    try:
        # Create client pointing to the running server
        async with httpx.AsyncClient(base_url=base_url, timeout=20) as client: # Increase timeout slightly more
             await asyncio.sleep(1.0) # Increase sleep slightly for server startup
             yield client, admin_app, base_url # Yield client, app, and REAL base_url
    finally:
        # Stop the server and clean up overrides
        server.stop()
        admin_app.dependency_overrides.clear()


# Fixture providing the TestClient, overriding the core get_mongo_db dependency
@pytest_asyncio.fixture(scope="function")
async def admin_api_test_client(test_mongo_db: AsyncIOMotorDatabase) -> AsyncGenerator[TestClient, None]:
    """
    Async fixture providing a FastAPI TestClient against the admin_api app
    with the core get_mongo_db dependency overridden to use the test_mongo_db fixture.
    """
    # Override the core get_mongo_db dependency directly
    async def override_get_db_for_test_client():
        # test_mongo_db is already resolved by pytest-asyncio
        return test_mongo_db

    # Ensure we are overriding the correct get_mongo_db function imported by the app
    db_module = importlib.import_module('admin_api.app.db.mongodb')
    original_get_mongo_db = db_module.get_mongo_db
    admin_app.dependency_overrides[original_get_mongo_db] = override_get_db_for_test_client

    # TestClient itself is synchronous but uses anyio internally
    client = TestClient(admin_app)
    try:
        yield client # Yield the TestClient
    finally:
        # Clean up the overrides after the test
        admin_app.dependency_overrides.clear()


# ---- Test Data Fixtures ---- is the next logical line after removing this fixture

# Remove the admin_api_ws_client fixture as it's replaced by the modified admin_api_client


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
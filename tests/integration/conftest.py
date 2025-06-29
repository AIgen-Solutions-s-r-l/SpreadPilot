import os

# """Pytest fixtures for SpreadPilot integration tests.""" # Moved path logic to test files
"""Pytest fixtures for SpreadPilot integration tests."""

import asyncio
import datetime
import importlib
import socket
import threading
import time
import uuid
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import patch

import httpx
import motor.motor_asyncio  # Added for MongoDB
import pytest
import pytest_asyncio
import testcontainers.core.config  # Added for timeout adjustment
import uvicorn
from fastapi import Depends

# Removed Firestore import line
from fastapi.testclient import TestClient  # Add TestClient import
from motor.motor_asyncio import AsyncIOMotorDatabase
from testcontainers.mongodb import MongoDbContainer  # Added for Testcontainers

from spreadpilot_core.ibkr.client import OrderStatus

# Import the dependency getter to override using importlib
# from admin_api.app.db.mongodb import get_mongo_db # Replaced with importlib below
from spreadpilot_core.models.follower import Follower, FollowerState
from spreadpilot_core.models.position import AssignmentState

# Import services for testing

# Add service directories to Python path to handle hyphenated module names
import sys
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "trading-bot"))
sys.path.insert(0, str(project_root / "alert-router"))
sys.path.insert(0, str(project_root / "admin-api"))

# Import modules using importlib with correct paths
try:
    trading_bot_service = importlib.import_module("app.service.signals")
    trading_bot_sheets = importlib.import_module("app.sheets")
    alert_router_service = importlib.import_module("app.service.router")
    admin_api_main = importlib.import_module("app.main")
    admin_api_mongodb_db = importlib.import_module("app.db.mongodb")
except ImportError as e:
    # Fallback for CI environment where modules might not be available
    print(f"Warning: Could not import modules: {e}")
    trading_bot_service = None
    trading_bot_sheets = None
    alert_router_service = None
    admin_api_main = None
    admin_api_mongodb_db = None

# Get specific imports
SignalProcessor = trading_bot_service.SignalProcessor if trading_bot_service else None
GoogleSheetsClient = trading_bot_sheets.GoogleSheetsClient if trading_bot_sheets else None
route_alert = alert_router_service.route_alert if alert_router_service else None
# calculate_monthly_pnl = report_worker_service.calculate_monthly_pnl # Removed
admin_app = admin_api_main.app if admin_api_main else None
get_mongo_db = admin_api_mongodb_db.get_mongo_db if admin_api_mongodb_db else None  # Get the function to override


# ---- Environment Setup ----


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment variables and mock external services."""
    # Set environment variables for testing
    # Removed Firestore env var line
    os.environ["GOOGLE_CLOUD_PROJECT"] = (
        "spreadpilot-test"  # Keep if other services might need it
    )
    os.environ["TESTING"] = "true"
    # MongoDB URI is handled by Testcontainers and dependency injection override

    # Removed global Firestore mock block
    yield  # Yield control to run tests

    # Clean up (if needed)
    # Removed Firestore env var cleanup


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
        **kwargs,
    ) -> dict[str, Any]:
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

    async def get_positions(self, force_update: bool = False) -> dict[str, int]:
        """Mock get_positions method."""
        return self.positions

    async def check_assignment(self) -> tuple[AssignmentState, int, int]:
        """Mock check_assignment method."""
        return AssignmentState.NONE, 0, 0

    async def exercise_options(self, qty: int) -> dict[str, Any]:
        """Mock exercise_options method."""
        return {
            "success": True,
            "qty_exercised": qty,
        }

    async def close_all_positions(self) -> dict[str, Any]:
        """Mock close_all_positions method."""
        self.positions = {}
        return {
            "success": True,
            "positions_closed": 2,
        }

    async def get_account_summary(self) -> dict[str, Any]:
        """Mock get_account_summary method."""
        return self.account_summary

    async def check_margin_for_trade(
        self,
        strategy: str,
        qty_per_leg: int,
        strike_long: float,
        strike_short: float,
        follower_id: str | None = None,  # Add follower_id
        **kwargs,  # Add kwargs to accept unexpected args
    ) -> tuple[bool, str | None]:
        """Mock check_margin_for_trade method."""
        # Basic mock logic, can be enhanced if needed
        return True, None

    async def get_pnl(self) -> dict[str, float]:
        """Mock get_pnl method."""
        return self.pnl


@pytest.fixture
def mock_ibkr_client():
    """Fixture for mock IBKR client."""
    return MockIBKRClient()


@pytest_asyncio.fixture
async def patched_ibkr_client(mock_ibkr_client):
    """Fixture to patch the IBKRClient with the mock."""
    with patch(
        "spreadpilot_core.ibkr.client.IBKRClient", return_value=mock_ibkr_client
    ):
        yield mock_ibkr_client


# ---- Mock Google Sheets Client ----


class MockGoogleSheetsClient:
    """Mock Google Sheets client for testing."""

    def __init__(
        self, sheet_url: str = "https://example.com/sheet", api_key: str | None = None
    ):
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

    def add_test_signal(self, signal: dict[str, Any]):
        """Add a test signal for testing."""
        self.test_signals.append(signal)

    async def fetch_signal(self) -> dict[str, Any] | None:
        """Mock fetch_signal method."""
        if not self.test_signals:
            return None

        signal = self.test_signals.pop(0)
        self.last_fetch_time = datetime.datetime.now()
        self.last_signal = signal
        return signal

    async def wait_for_signal(self, timeout_seconds: int = 1) -> dict[str, Any] | None:
        """Mock wait_for_signal method."""
        return await self.fetch_signal()


@pytest.fixture
def mock_sheets_client():
    """Fixture for mock Google Sheets client."""
    client = MockGoogleSheetsClient()

    # Add a test signal
    client.add_test_signal(
        {
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "ticker": "QQQ",
            "strategy": "Long",  # Bull Put
            "qty_per_leg": 1,
            "strike_long": 380.0,
            "strike_short": 385.0,
        }
    )

    return client


@pytest_asyncio.fixture
async def patched_sheets_client(mock_sheets_client):
    """Fixture to patch the GoogleSheetsClient with the mock."""
    with patch(
        "trading_bot.app.sheets.GoogleSheetsClient", return_value=mock_sheets_client
    ):
        yield mock_sheets_client


# ---- MongoDB Testcontainer Fixture ----


@pytest.fixture(scope="session")
def mongodb_container() -> Generator[MongoDbContainer, None, None]:
    """Starts and stops a MongoDB Testcontainer for the test session."""
    # Using a specific image version known to work well
    # Increase the default timeout for testcontainers
    original_timeout = testcontainers.core.config.TIMEOUT
    testcontainers.core.config.TIMEOUT = 300  # Increase to 300 seconds
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
async def test_mongo_db(
    mongodb_container: MongoDbContainer,
) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
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

    yield db  # Provide the database object to the test

    # Cleanup: Drop the test database after the test function completes
    await client.drop_database(test_db_name)
    client.close()
    print(f"Dropped test MongoDB database: {test_db_name}")  # For debugging


# ---- FastAPI Dependency Override ----


async def override_get_mongo_db(
    test_db: AsyncIOMotorDatabase = Depends(test_mongo_db),
) -> AsyncIOMotorDatabase:
    """Dependency override function that returns the test_mongo_db fixture."""
    return test_db


# ---- Service Fixtures ----

# Removed outdated signal_processor fixture (lines 322-347)


# Re-add httpx import


# Helper function to find a free port
def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


# Uvicorn server runner
class UvicornServer(uvicorn.Server):
    def install_signal_handlers(self):
        pass  # Prevent uvicorn from handling signals in tests

    def run_in_thread(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        # Wait briefly for server to start - adjust sleep time if needed
        time.sleep(1.5)

    def stop(self):
        self.should_exit = True
        if hasattr(self, "thread") and self.thread.is_alive():
            self.thread.join(timeout=1)  # Wait briefly for thread to exit


@pytest_asyncio.fixture(scope="function")
async def admin_api_client(
    test_mongo_db: AsyncIOMotorDatabase,
) -> AsyncGenerator[tuple[httpx.AsyncClient, Any, str], None]:
    """
    Async fixture providing an httpx.AsyncClient against a running admin_api app instance.
    Overrides the application's Settings dependency to use the test database connection.
    Runs the app using Uvicorn in a thread.
    Yields the client, the app instance, and the actual base_url.
    """
    # Get the connection URI from the test_mongo_db fixture's client
    mongo_uri = f"mongodb://{test_mongo_db.client.HOST}:{test_mongo_db.client.PORT}"
    db_name = test_mongo_db.name  # Get the unique test DB name

    # Import necessary modules
    config_module = importlib.import_module("admin_api.app.core.config")
    admin_api_main_module = importlib.import_module("admin_api.app.main")
    Settings = config_module.Settings
    original_get_settings = config_module.get_settings
    admin_app_instance = admin_api_main_module.app

    # Define the override function for get_settings
    def get_test_settings():
        # Create a settings instance specifically for the test, overriding DB details
        return Settings(mongo_uri=mongo_uri, mongo_db_name=db_name)

    # Apply the override for the settings dependency
    admin_app_instance.dependency_overrides[original_get_settings] = get_test_settings

    # --- Run App with Uvicorn ---
    host = "127.0.0.1"
    port = find_free_port()
    base_url = f"http://{host}:{port}"

    config = uvicorn.Config(
        admin_app_instance, host=host, port=port, log_level="warning"
    )
    server = UvicornServer(config=config)
    server.run_in_thread()
    # --- End Run App ---

    try:
        # Create client pointing to the running server
        async with httpx.AsyncClient(base_url=base_url, timeout=20) as client:
            await asyncio.sleep(1.0)  # Allow server startup
            yield client, admin_app_instance, base_url
    finally:
        # Stop the server
        server.stop()
        # Clean up overrides
        admin_app_instance.dependency_overrides.clear()
        # No clients_to_close list in this version


# Fixture providing the TestClient, overriding the core get_mongo_db dependency
@pytest_asyncio.fixture(scope="function")
async def admin_api_test_client(
    test_mongo_db: AsyncIOMotorDatabase,
) -> AsyncGenerator[TestClient, None]:
    """
    Async fixture providing a FastAPI TestClient against the admin_api app
    with the application's Settings dependency overridden to use the test_mongo_db fixture.
    """
    # Get the connection URI from the test_mongo_db fixture's client
    mongo_uri = f"mongodb://{test_mongo_db.client.HOST}:{test_mongo_db.client.PORT}"
    db_name = test_mongo_db.name  # Get the unique test DB name

    # Import necessary modules
    config_module = importlib.import_module("admin_api.app.core.config")
    admin_api_main_module = importlib.import_module("admin_api.app.main")
    Settings = config_module.Settings
    original_get_settings = config_module.get_settings
    admin_app_instance = admin_api_main_module.app

    # Define the override function for get_settings
    def get_test_settings():
        # Create a settings instance specifically for the test, overriding DB details
        return Settings(mongo_uri=mongo_uri, mongo_db_name=db_name)

    # Apply the override for the settings dependency
    admin_app_instance.dependency_overrides[original_get_settings] = get_test_settings

    # TestClient itself is synchronous but uses anyio internally
    client = TestClient(admin_app_instance)
    try:
        yield client  # Yield the TestClient
    finally:
        # Clean up the overrides after the test
        admin_app_instance.dependency_overrides.clear()


# ---- Test Data Fixtures ---- is the next logical line after removing this fixture

# Remove the admin_api_ws_client fixture as it's replaced by the modified admin_api_client


# ---- Test Data Fixtures ----
@pytest_asyncio.fixture(scope="function")
async def test_follower(test_mongo_db: AsyncIOMotorDatabase) -> Follower:
    """Fixture to create a sample follower in the test MongoDB."""
    follower_data = {
        "_id": "test-follower-id",  # Use a fixed ID for predictability
        "name": "Test Follower",
        "email": "test.follower@example.com",
        "phone": "+1234567890",
        "ibkr_account_id": "U123456",
        "commission_pct": 20.0,
        "state": FollowerState.ACTIVE.value,
        "created_at": datetime.datetime.now(datetime.UTC),
        "updated_at": datetime.datetime.now(datetime.UTC),
        "telegram_chat_id": "12345",
        "max_risk_per_trade": 100.0,
        "assigned_options": [],
        "daily_pnl": 0.0,
        "monthly_pnl": 0.0,
        "total_pnl": 0.0,
        # Add missing required fields
        "iban": "DE89 3704 0044 0532 0130 00",
        "ibkr_username": "testuser",
        "ibkr_secret_ref": "projects/spreadpilot-test/secrets/test-ibkr-secret/versions/latest",  # Example ref
    }
    # Insert the follower data
    await test_mongo_db.followers.insert_one(follower_data)
    print(f"Inserted test follower: {follower_data['_id']}")  # Debugging

    # Yield a Pydantic model instance
    yield Follower(**follower_data)

    # Cleanup: Remove the follower after the test
    await test_mongo_db.followers.delete_one({"_id": follower_data["_id"]})
    print(f"Deleted test follower: {follower_data['_id']}")  # Debugging


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

"""
Configuration and fixtures for E2E tests.
"""

import asyncio
import os
from pathlib import Path

import pytest


# Add E2E marker
def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")


# Configure async test execution
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test environment variables
@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ.update(
        {
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "DEBUG",
            "MONGO_URI": "mongodb://admin:password@localhost:27017/spreadpilot_test?authSource=admin",
            "IBKR_GATEWAY_URL": "http://localhost:5001",
            "GOOGLE_APPLICATION_CREDENTIALS": str(
                Path(__file__).parent / "test_credentials.json"
            ),
            "SMTP_SERVER": "localhost",
            "SMTP_PORT": "1025",  # MailHog port
            "GCS_BUCKET": "test-reports",
            "JWT_SECRET": "test_secret_123",
        }
    )
    yield
    # Cleanup if needed


# Skip E2E tests by default unless explicitly requested
def pytest_collection_modifyitems(config, items):
    if not config.option.markexpr:
        skip_e2e = pytest.mark.skip(
            reason="E2E tests skipped by default. Use -m e2e to run."
        )
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)

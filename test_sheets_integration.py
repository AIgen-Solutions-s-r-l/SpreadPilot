"""Test script for Google Sheets integration."""

import asyncio
import os
from dotenv import load_dotenv

import sys
sys.path.append('.')  # Add current directory to path
from trading_bot.app.sheets import GoogleSheetsClient  # This will fail due to hyphen in directory name

# Alternative import approach
import importlib.util
import os

# Dynamically import the sheets module
sheets_path = os.path.join('trading-bot', 'app', 'sheets.py')
spec = importlib.util.spec_from_file_location("sheets", sheets_path)
sheets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sheets)
GoogleSheetsClient = sheets.GoogleSheetsClient
# Import logging from spreadpilot-core
spreadpilot_core_path = os.path.join('spreadpilot-core', 'spreadpilot_core')
logging_path = os.path.join(spreadpilot_core_path, 'logging', '__init__.py')
spec = importlib.util.spec_from_file_location("logging", logging_path)
logging_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logging_module)
setup_logging = logging_module.setup_logging
get_logger = logging_module.get_logger

# Load environment variables from .env.test
load_dotenv('.env.test')

# Set up logging
setup_logging(service_name="test-sheets-integration")
logger = get_logger(__name__)

async def test_sheets_integration():
    """Test Google Sheets integration."""
    # Get Google Sheets URL from environment
    sheet_url = os.getenv("GOOGLE_SHEET_URL")
    api_key = os.getenv("GOOGLE_SHEETS_API_KEY")
    
    if not sheet_url:
        logger.error("GOOGLE_SHEET_URL environment variable not set")
        return
    
    # Initialize Google Sheets client
    sheets_client = GoogleSheetsClient(sheet_url=sheet_url, api_key=api_key)
    
    # Connect to Google Sheets
    if not await sheets_client.connect():
        logger.error("Failed to connect to Google Sheets")
        return
    
    # Fetch signal
    signal = await sheets_client.fetch_signal()
    
    if not signal:
        logger.warning("No signal found for current date")
        return
    
    # Log signal
    logger.info(
        "Fetched signal from Google Sheets",
        signal=signal,
    )
    
    # Verify signal structure
    expected_keys = ["date", "ticker", "strategy", "qty_per_leg", "strike_long", "strike_short"]
    for key in expected_keys:
        if key not in signal:
            logger.error(f"Signal missing key: {key}")
            return
    
    # Log success
    logger.info("Signal structure verified successfully")
    
    # Log strategy and strikes
    logger.info(
        "Strategy and strikes",
        strategy=signal["strategy"],
        strike_long=signal["strike_long"],
        strike_short=signal["strike_short"],
    )

if __name__ == "__main__":
    asyncio.run(test_sheets_integration())
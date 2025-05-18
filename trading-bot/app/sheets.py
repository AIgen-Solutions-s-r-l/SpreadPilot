"""Google Sheets client for fetching trading signals."""

import asyncio
import datetime
import re
from typing import Dict, List, Optional, Tuple, Union

import aiohttp

from spreadpilot_core.logging import get_logger
from spreadpilot_core.utils.time import get_ny_time

logger = get_logger(__name__)


class GoogleSheetsClient:
    """Client for fetching data from Google Sheets."""

    def __init__(self, sheet_url: str, api_key: Optional[str] = None):
        """Initialize the Google Sheets client.

        Args:
            sheet_url: URL of the Google Sheet
            api_key: Google Sheets API key (optional)
        """
        self.sheet_url = sheet_url
        self.api_key = api_key
        self.sheet_id = self._extract_sheet_id(sheet_url)
        self.connected = False
        self.last_fetch_time = None
        self.last_signal = None
        
        logger.info(
            "Initialized Google Sheets client",
            sheet_id=self.sheet_id,
        )

    def _extract_sheet_id(self, url: str) -> str:
        """Extract sheet ID from URL.

        Args:
            url: Google Sheet URL

        Returns:
            Sheet ID
        """
        # Extract sheet ID from URL
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
        if not match:
            raise ValueError(f"Invalid Google Sheet URL: {url}")
        
        return match.group(1)

    async def connect(self) -> bool:
        """Connect to Google Sheets API.

        Returns:
            True if connected successfully, False otherwise
        """
        try:
            # Test connection by fetching sheet metadata
            async with aiohttp.ClientSession() as session:
                url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.sheet_id}"
                if self.api_key:
                    url += f"?key={self.api_key}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        self.connected = True
                        logger.info("Connected to Google Sheets API")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Failed to connect to Google Sheets API: {error_text}",
                            status=response.status,
                        )
                        self.connected = False
                        return False
        except Exception as e:
            logger.error(f"Error connecting to Google Sheets API: {e}")
            self.connected = False
            return False

    async def fetch_signal(self) -> Optional[Dict[str, Union[str, int, float]]]:
        """Fetch trading signal from Google Sheet.

        Returns:
            Signal dict or None if no signal found
        """
        try:
            # Get current date in NY timezone
            ny_time = get_ny_time()
            current_date = ny_time.strftime("%Y-%m-%d")
            
            # Fetch sheet data
            async with aiohttp.ClientSession() as session:
                # Fetch sheet data from the first sheet (index 0)
                url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.sheet_id}/values/Sheet1"
                if self.api_key:
                    url += f"?key={self.api_key}"
                
                async with session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"Failed to fetch sheet data: {error_text}",
                            status=response.status,
                        )
                        return None
                    
                    data = await response.json()
                    
                    if "values" not in data:
                        logger.warning("No values found in sheet data")
                        return None
                    
                    values = data["values"]
                    
                    # Find header row
                    header_row = None
                    for i, row in enumerate(values):
                        if "Data" in row and "Ticker" in row and "Strategia" in row:
                            header_row = i
                            break
                    
                    if header_row is None:
                        logger.warning("Header row not found in sheet data")
                        return None
                    
                    # Get header indices
                    headers = values[header_row]
                    date_index = headers.index("Data")
                    ticker_index = headers.index("Ticker")
                    strategy_index = headers.index("Strategia")
                    
                    # Find columns for strikes and quantity
                    qty_index = None
                    buy_put_index = None
                    sell_put_index = None
                    sell_call_index = None
                    buy_call_index = None
                    
                    for i, header in enumerate(headers):
                        if "Quantità per Leg" in header:
                            qty_index = i
                        elif header == "Buy Put":
                            buy_put_index = i
                        elif header == "Sell Put":
                            sell_put_index = i
                        elif header == "Sell Call":
                            sell_call_index = i
                        elif header == "Buy Call":
                            buy_call_index = i
                    
                    if (qty_index is None or buy_put_index is None or sell_put_index is None or
                        sell_call_index is None or buy_call_index is None):
                        logger.warning(
                            "Required columns not found in sheet data",
                            headers=headers,
                        )
                        return None
                    
                    # Find row for current date
                    signal_row = None
                    for i in range(header_row + 1, len(values)):
                        row = values[i]
                        if len(row) <= date_index:
                            continue
                        
                        row_date = row[date_index]
                        if row_date == current_date:
                            signal_row = i
                            break
                    
                    if signal_row is None:
                        logger.debug(
                            "No signal found for current date",
                            current_date=current_date,
                        )
                        return None
                    
                    # Get signal data
                    row = values[signal_row]
                    
                    # Check if ticker is QQQ
                    if len(row) <= ticker_index or row[ticker_index] != "QQQ":
                        logger.debug(
                            "Signal ticker is not QQQ",
                            ticker=row[ticker_index] if len(row) > ticker_index else None,
                        )
                        return None
                    
                    # Check if we have all required data
                    if (len(row) <= strategy_index or
                        len(row) <= qty_index or
                        len(row) <= strike_long_index or
                        len(row) <= strike_short_index):
                        logger.warning(
                            "Signal row is missing required data",
                            row=row,
                        )
                        return None
                    
                    # Determine which strike prices to use based on strategy
                    strategy = row[strategy_index]
                    strike_long = None
                    strike_short = None
                    
                    if strategy == "Long":
                        # For Long strategy, use Buy Put and Sell Put
                        strike_long = float(row[buy_put_index])
                        strike_short = float(row[sell_put_index])
                    elif strategy == "Short":
                        # For Short strategy, use Buy Call and Sell Call
                        strike_long = float(row[buy_call_index])
                        strike_short = float(row[sell_call_index])
                    else:
                        logger.warning(
                            "Unknown strategy in signal",
                            strategy=strategy,
                        )
                        return None
                    
                    # Create signal dict
                    signal = {
                        "date": current_date,
                        "ticker": row[ticker_index],
                        "strategy": strategy,
                        "qty_per_leg": int(row[qty_index]),
                        "strike_long": strike_long,
                        "strike_short": strike_short,
                    }
                    
                    # Update last fetch time and signal
                    self.last_fetch_time = datetime.datetime.now()
                    self.last_signal = signal
                    
                    logger.info(
                        "Fetched signal from Google Sheets",
                        signal=signal,
                    )
                    
                    return signal
        except Exception as e:
            logger.error(f"Error fetching signal from Google Sheets: {e}")
            return None

    async def wait_for_signal(self, timeout_seconds: int = 300) -> Optional[Dict[str, Union[str, int, float]]]:
        """Wait for a trading signal to appear in the Google Sheet.

        Args:
            timeout_seconds: Timeout in seconds

        Returns:
            Signal dict or None if timeout reached
        """
        start_time = datetime.datetime.now()
        
        while (datetime.datetime.now() - start_time).total_seconds() < timeout_seconds:
            signal = await self.fetch_signal()
            
            if signal:
                return signal
            
            # Wait before retrying
            await asyncio.sleep(1)
        
        logger.warning(
            "Timeout waiting for signal",
            timeout_seconds=timeout_seconds,
        )
        
        return None

    def is_connected(self) -> bool:
        """Check if connected to Google Sheets API.

        Returns:
            True if connected, False otherwise
        """
        return self.connected
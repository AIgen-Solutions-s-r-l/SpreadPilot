"""Signal listener service for SpreadPilot trading signals.

This module implements a scheduled service that:
1. Connects to Google Sheets at 09:27 EST daily
2. Polls for today's date row until ticker cell is filled
3. Emits Signal dataclass on Redis Pub/Sub channel
"""

import asyncio
import json
from datetime import date, datetime

import gspread
import pytz
import redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from spreadpilot_core.logging import get_logger
from spreadpilot_core.models import Signal

from .config import get_settings

logger = get_logger(__name__)


class SignalListener:
    """Scheduled signal listener for Google Sheets trading signals."""

    def __init__(
        self,
        google_sheet_url: str | None = None,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_channel: str = "trading_signals",
        poll_interval_seconds: int = 5,
        max_poll_attempts: int = 120,  # 10 minutes of polling
        credentials_path: str | None = None,
    ):
        """Initialize the signal listener.

        Args:
            google_sheet_url: URL of the Google Sheet containing signals
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            redis_channel: Redis channel name for signal emission
            poll_interval_seconds: Seconds between polling attempts
            max_poll_attempts: Maximum polling attempts before timeout
            credentials_path: Path to Google service account credentials
        """
        self.settings = get_settings()
        self.google_sheet_url = google_sheet_url or self.settings.google_sheet_url
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_channel = redis_channel
        self.poll_interval_seconds = poll_interval_seconds
        self.max_poll_attempts = max_poll_attempts
        self.credentials_path = credentials_path

        # Initialize components
        self.scheduler: AsyncIOScheduler | None = None
        self.redis_client: redis.Redis | None = None
        self.gsheet_client: gspread.Client | None = None
        self.worksheet: gspread.Worksheet | None = None

        # Timezone setup
        self.eastern = pytz.timezone("US/Eastern")

        logger.info("Signal listener initialized")

    async def start(self):
        """Start the signal listener scheduler."""
        logger.info("Starting signal listener service")

        try:
            # Initialize Redis connection
            await self._init_redis()

            # Initialize scheduler
            self.scheduler = AsyncIOScheduler(timezone=self.eastern)

            # Schedule signal fetching at 09:27 EST daily
            self.scheduler.add_job(
                self._fetch_signal_job,
                trigger=CronTrigger(hour=9, minute=27, timezone=self.eastern),
                id="daily_signal_fetch",
                name="Daily Signal Fetch",
                replace_existing=True,
            )

            # Start scheduler
            self.scheduler.start()

            logger.info("Signal listener started - scheduled for 09:27 EST daily")

        except Exception as e:
            logger.error(f"Failed to start signal listener: {e}")
            raise

    async def stop(self):
        """Stop the signal listener scheduler."""
        logger.info("Stopping signal listener service")

        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=True)

        if self.redis_client:
            (
                await self.redis_client.aclose()
                if hasattr(self.redis_client, "aclose")
                else self.redis_client.close()
            )

        logger.info("Signal listener stopped")

    async def _init_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                decode_responses=True,
            )

            # Test connection
            await asyncio.get_event_loop().run_in_executor(None, self.redis_client.ping)

            logger.info(f"Redis connection established: {self.redis_host}:{self.redis_port}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def _init_gsheet_connection(self):
        """Initialize Google Sheets connection."""
        try:
            if self.credentials_path:
                self.gsheet_client = gspread.service_account(filename=self.credentials_path)
            else:
                # Try to use default credentials or environment
                self.gsheet_client = gspread.service_account()

            # Open the spreadsheet
            spreadsheet = self.gsheet_client.open_by_url(self.google_sheet_url)
            self.worksheet = spreadsheet.sheet1  # Assume first sheet

            logger.info("Google Sheets connection established")

        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            raise

    async def _fetch_signal_job(self):
        """Scheduled job to fetch today's signal."""
        try:
            logger.info("Starting scheduled signal fetch at 09:27 EST")

            # Connect to Google Sheets
            await self._init_gsheet_connection()

            # Poll for today's signal
            signal = await self._poll_for_todays_signal()

            if signal:
                # Emit signal to Redis Pub/Sub
                await self._emit_signal(signal)
                logger.info(f"Successfully processed and emitted signal: {signal}")
            else:
                logger.warning("No signal found for today within polling timeout")

        except Exception as e:
            logger.error(f"Error in scheduled signal fetch: {e}")

    async def _poll_for_todays_signal(self) -> Signal | None:
        """Poll Google Sheets for today's signal until ticker is filled.

        Returns:
            Signal object if found, None if timeout
        """
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")

        logger.info(f"Polling for signal on date: {today_str}")

        for attempt in range(1, self.max_poll_attempts + 1):
            try:
                # Get all values from the sheet
                all_values = await asyncio.get_event_loop().run_in_executor(
                    None, self.worksheet.get_all_values
                )

                # Find row with today's date
                signal = self._find_signal_for_date(all_values, today)

                if signal:
                    logger.info(f"Found signal for today on attempt {attempt}: {signal}")
                    return signal

                if attempt % 10 == 0:  # Log every 10 attempts (50 seconds)
                    logger.info(
                        f"Polling attempt {attempt}/{self.max_poll_attempts} - no signal yet"
                    )

                # Wait before next poll
                await asyncio.sleep(self.poll_interval_seconds)

            except Exception as e:
                logger.error(f"Error during polling attempt {attempt}: {e}")
                await asyncio.sleep(self.poll_interval_seconds)

        logger.warning(f"Signal polling timed out after {self.max_poll_attempts} attempts")
        return None

    def _find_signal_for_date(self, all_values: list, target_date: date) -> Signal | None:
        """Find and parse signal for specific date from sheet values.

        Args:
            all_values: All values from the Google Sheet
            target_date: Date to search for

        Returns:
            Signal object if found and ticker is filled, None otherwise
        """
        target_date_str = target_date.strftime("%Y-%m-%d")

        # Assume header row format: Date, Ticker, Strategy, Qty_Per_Leg, Strike_Long, Strike_Short
        for row_idx, row in enumerate(all_values[1:], start=2):  # Skip header row
            if len(row) < 6:
                continue

            date_cell = row[0].strip()
            ticker_cell = row[1].strip()

            # Check if this is today's row and ticker is filled
            if date_cell == target_date_str and ticker_cell:
                try:
                    signal = Signal(
                        ticker=ticker_cell,
                        strategy=row[2].strip(),
                        qty_per_leg=int(row[3]),
                        strike_long=float(row[4]),
                        strike_short=float(row[5]),
                        signal_date=target_date,
                        sheet_row=row_idx,
                        timestamp=datetime.now(self.eastern),
                    )

                    return signal

                except (ValueError, IndexError) as e:
                    logger.warning(f"Invalid signal data in row {row_idx}: {e}")
                    continue

        return None

    async def _emit_signal(self, signal: Signal):
        """Emit signal to Redis Pub/Sub channel.

        Args:
            signal: Signal object to emit
        """
        try:
            # Convert signal to JSON
            signal_data = {
                **signal.to_dict(),
                "signal_date": signal.signal_date.isoformat(),
                "timestamp": signal.timestamp.isoformat(),
            }

            signal_json = json.dumps(signal_data, default=str)

            # Publish to Redis channel
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis_client.publish, self.redis_channel, signal_json
            )

            logger.info(f"Signal emitted to Redis channel '{self.redis_channel}': {signal}")

        except Exception as e:
            logger.error(f"Failed to emit signal to Redis: {e}")
            raise

    # Manual trigger method for testing
    async def fetch_signal_now(self) -> Signal | None:
        """Manually trigger signal fetch (for testing purposes).

        Returns:
            Signal object if found, None otherwise
        """
        logger.info("Manual signal fetch triggered")
        await self._init_gsheet_connection()
        return await self._poll_for_todays_signal()

"""Unit tests for SignalListener with freezegun and gspread mocks."""

import json
from datetime import date, datetime
from unittest.mock import Mock, patch

import pytest
import pytz
from freezegun import freeze_time

from spreadpilot_core.models import Signal
import sys
from pathlib import Path

# Add trading-bot to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "trading-bot"))

from app.signal_listener import SignalListener


class TestSignalListener:
    """Test SignalListener class."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock()
        settings.google_sheet_url = "https://docs.google.com/spreadsheets/test"
        return settings

    @pytest.fixture
    def signal_listener(self, mock_settings):
        """Create SignalListener instance for testing."""
        with patch(
            "trading_bot.app.signal_listener.get_settings", return_value=mock_settings
        ):
            return SignalListener(
                google_sheet_url="https://docs.google.com/spreadsheets/test",
                redis_host="localhost",
                redis_port=6379,
                redis_channel="test_signals",
                poll_interval_seconds=1,  # Fast polling for tests
                max_poll_attempts=5,  # Quick timeout for tests
            )

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.publish.return_value = 1
        return mock_redis

    @pytest.fixture
    def mock_gsheet_client(self):
        """Mock Google Sheets client."""
        mock_client = Mock()
        mock_spreadsheet = Mock()
        mock_worksheet = Mock()

        mock_client.open_by_url.return_value = mock_spreadsheet
        mock_spreadsheet.sheet1 = mock_worksheet

        return mock_client, mock_worksheet

    @pytest.mark.asyncio
    async def test_signal_listener_initialization(self, signal_listener):
        """Test SignalListener initialization."""
        assert (
            signal_listener.google_sheet_url
            == "https://docs.google.com/spreadsheets/test"
        )
        assert signal_listener.redis_host == "localhost"
        assert signal_listener.redis_port == 6379
        assert signal_listener.redis_channel == "test_signals"
        assert signal_listener.poll_interval_seconds == 1
        assert signal_listener.max_poll_attempts == 5
        assert signal_listener.eastern.zone == "US/Eastern"

    @pytest.mark.asyncio
    async def test_start_scheduler(self, signal_listener, mock_redis):
        """Test starting the scheduler."""
        with (
            patch("redis.Redis", return_value=mock_redis),
            patch(
                "trading_bot.app.signal_listener.AsyncIOScheduler"
            ) as mock_scheduler_class,
        ):

            mock_scheduler = Mock()
            mock_scheduler_class.return_value = mock_scheduler

            await signal_listener.start()

            # Verify Redis connection was initialized
            mock_redis.ping.assert_called_once()

            # Verify scheduler was configured
            mock_scheduler_class.assert_called_once_with(
                timezone=signal_listener.eastern
            )
            mock_scheduler.add_job.assert_called_once()
            mock_scheduler.start.assert_called_once()

            # Check job configuration
            job_call = mock_scheduler.add_job.call_args
            assert job_call[1]["id"] == "daily_signal_fetch"
            assert job_call[1]["name"] == "Daily Signal Fetch"

    @pytest.mark.asyncio
    async def test_stop_scheduler(self, signal_listener):
        """Test stopping the scheduler."""
        # Setup mocks
        mock_scheduler = Mock()
        mock_scheduler.running = True
        mock_redis = Mock()

        signal_listener.scheduler = mock_scheduler
        signal_listener.redis_client = mock_redis

        await signal_listener.stop()

        mock_scheduler.shutdown.assert_called_once_with(wait=True)

    @pytest.mark.asyncio
    async def test_gsheet_connection_initialization(
        self, signal_listener, mock_gsheet_client
    ):
        """Test Google Sheets connection initialization."""
        mock_client, mock_worksheet = mock_gsheet_client

        with patch("gspread.service_account", return_value=mock_client):
            await signal_listener._init_gsheet_connection()

            assert signal_listener.gsheet_client == mock_client
            assert signal_listener.worksheet == mock_worksheet
            mock_client.open_by_url.assert_called_once_with(
                signal_listener.google_sheet_url
            )

    @pytest.mark.asyncio
    async def test_gsheet_connection_with_credentials_path(
        self, signal_listener, mock_gsheet_client
    ):
        """Test Google Sheets connection with credentials path."""
        mock_client, mock_worksheet = mock_gsheet_client
        signal_listener.credentials_path = "/path/to/credentials.json"

        with patch(
            "gspread.service_account", return_value=mock_client
        ) as mock_service_account:
            await signal_listener._init_gsheet_connection()

            mock_service_account.assert_called_once_with(
                filename="/path/to/credentials.json"
            )

    def test_find_signal_for_date_success(self, signal_listener):
        """Test finding signal for specific date."""
        target_date = date(2025, 6, 27)

        # Mock sheet data: header + data row
        sheet_data = [
            [
                "Date",
                "Ticker",
                "Strategy",
                "Qty_Per_Leg",
                "Strike_Long",
                "Strike_Short",
            ],
            ["2025-06-27", "QQQ", "Long", "10", "450.0", "455.0"],
        ]

        with freeze_time("2025-06-27 09:30:00", tz_offset=-5):  # EST
            signal = signal_listener._find_signal_for_date(sheet_data, target_date)

        assert signal is not None
        assert signal.ticker == "QQQ"
        assert signal.strategy == "Long"
        assert signal.qty_per_leg == 10
        assert signal.strike_long == 450.0
        assert signal.strike_short == 455.0
        assert signal.signal_date == target_date
        assert signal.sheet_row == 2

    def test_find_signal_for_date_empty_ticker(self, signal_listener):
        """Test finding signal when ticker cell is empty."""
        target_date = date(2025, 6, 27)

        # Mock sheet data with empty ticker
        sheet_data = [
            [
                "Date",
                "Ticker",
                "Strategy",
                "Qty_Per_Leg",
                "Strike_Long",
                "Strike_Short",
            ],
            ["2025-06-27", "", "Long", "10", "450.0", "455.0"],
        ]

        signal = signal_listener._find_signal_for_date(sheet_data, target_date)
        assert signal is None

    def test_find_signal_for_date_wrong_date(self, signal_listener):
        """Test finding signal for wrong date."""
        target_date = date(2025, 6, 27)

        # Mock sheet data with different date
        sheet_data = [
            [
                "Date",
                "Ticker",
                "Strategy",
                "Qty_Per_Leg",
                "Strike_Long",
                "Strike_Short",
            ],
            ["2025-06-26", "QQQ", "Long", "10", "450.0", "455.0"],
        ]

        signal = signal_listener._find_signal_for_date(sheet_data, target_date)
        assert signal is None

    def test_find_signal_for_date_invalid_data(self, signal_listener):
        """Test finding signal with invalid data."""
        target_date = date(2025, 6, 27)

        # Mock sheet data with invalid numbers
        sheet_data = [
            [
                "Date",
                "Ticker",
                "Strategy",
                "Qty_Per_Leg",
                "Strike_Long",
                "Strike_Short",
            ],
            ["2025-06-27", "QQQ", "Long", "invalid", "450.0", "455.0"],
        ]

        signal = signal_listener._find_signal_for_date(sheet_data, target_date)
        assert signal is None

    @pytest.mark.asyncio
    async def test_poll_for_todays_signal_success(
        self, signal_listener, mock_gsheet_client
    ):
        """Test successful polling for today's signal."""
        mock_client, mock_worksheet = mock_gsheet_client
        signal_listener.gsheet_client = mock_client
        signal_listener.worksheet = mock_worksheet

        # Mock sheet data
        sheet_data = [
            [
                "Date",
                "Ticker",
                "Strategy",
                "Qty_Per_Leg",
                "Strike_Long",
                "Strike_Short",
            ],
            ["2025-06-27", "QQQ", "Long", "10", "450.0", "455.0"],
        ]
        mock_worksheet.get_all_values.return_value = sheet_data

        with freeze_time("2025-06-27 09:30:00", tz_offset=-5):  # EST
            signal = await signal_listener._poll_for_todays_signal()

        assert signal is not None
        assert signal.ticker == "QQQ"
        mock_worksheet.get_all_values.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_for_todays_signal_timeout(
        self, signal_listener, mock_gsheet_client
    ):
        """Test polling timeout when no signal found."""
        mock_client, mock_worksheet = mock_gsheet_client
        signal_listener.gsheet_client = mock_client
        signal_listener.worksheet = mock_worksheet
        signal_listener.max_poll_attempts = 2  # Quick timeout

        # Mock empty sheet data
        sheet_data = [
            ["Date", "Ticker", "Strategy", "Qty_Per_Leg", "Strike_Long", "Strike_Short"]
        ]
        mock_worksheet.get_all_values.return_value = sheet_data

        with freeze_time("2025-06-27 09:30:00", tz_offset=-5):  # EST
            signal = await signal_listener._poll_for_todays_signal()

        assert signal is None
        assert mock_worksheet.get_all_values.call_count == 2

    @pytest.mark.asyncio
    async def test_poll_for_todays_signal_progressive_fill(
        self, signal_listener, mock_gsheet_client
    ):
        """Test polling that finds signal after ticker is filled."""
        mock_client, mock_worksheet = mock_gsheet_client
        signal_listener.gsheet_client = mock_client
        signal_listener.worksheet = mock_worksheet

        # First call: empty ticker, second call: filled ticker
        sheet_data_empty = [
            [
                "Date",
                "Ticker",
                "Strategy",
                "Qty_Per_Leg",
                "Strike_Long",
                "Strike_Short",
            ],
            ["2025-06-27", "", "Long", "10", "450.0", "455.0"],
        ]
        sheet_data_filled = [
            [
                "Date",
                "Ticker",
                "Strategy",
                "Qty_Per_Leg",
                "Strike_Long",
                "Strike_Short",
            ],
            ["2025-06-27", "QQQ", "Long", "10", "450.0", "455.0"],
        ]

        mock_worksheet.get_all_values.side_effect = [
            sheet_data_empty,
            sheet_data_filled,
        ]

        with freeze_time("2025-06-27 09:30:00", tz_offset=-5):  # EST
            signal = await signal_listener._poll_for_todays_signal()

        assert signal is not None
        assert signal.ticker == "QQQ"
        assert mock_worksheet.get_all_values.call_count == 2

    @pytest.mark.asyncio
    async def test_emit_signal_to_redis(self, signal_listener, mock_redis):
        """Test emitting signal to Redis Pub/Sub."""
        signal_listener.redis_client = mock_redis

        signal = Signal(
            ticker="QQQ",
            strategy="Long",
            qty_per_leg=10,
            strike_long=450.0,
            strike_short=455.0,
            signal_date=date(2025, 6, 27),
            sheet_row=2,
            timestamp=datetime(
                2025, 6, 27, 9, 30, 0, tzinfo=pytz.timezone("US/Eastern")
            ),
        )

        await signal_listener._emit_signal(signal)

        # Verify Redis publish was called
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args[0]

        assert call_args[0] == "test_signals"  # channel

        # Verify signal data
        published_data = json.loads(call_args[1])
        assert published_data["ticker"] == "QQQ"
        assert published_data["strategy"] == "Long"
        assert published_data["qty_per_leg"] == 10

    @pytest.mark.asyncio
    async def test_fetch_signal_job_success(
        self, signal_listener, mock_gsheet_client, mock_redis
    ):
        """Test complete signal fetch job execution."""
        mock_client, mock_worksheet = mock_gsheet_client
        signal_listener.redis_client = mock_redis

        # Mock sheet data
        sheet_data = [
            [
                "Date",
                "Ticker",
                "Strategy",
                "Qty_Per_Leg",
                "Strike_Long",
                "Strike_Short",
            ],
            ["2025-06-27", "QQQ", "Long", "10", "450.0", "455.0"],
        ]
        mock_worksheet.get_all_values.return_value = sheet_data

        with (
            patch("gspread.service_account", return_value=mock_client),
            freeze_time("2025-06-27 09:30:00", tz_offset=-5),
        ):  # EST

            await signal_listener._fetch_signal_job()

        # Verify Google Sheets was accessed
        mock_client.open_by_url.assert_called_once()
        mock_worksheet.get_all_values.assert_called_once()

        # Verify Redis publish was called
        mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_signal_job_gsheet_error(self, signal_listener, mock_redis):
        """Test signal fetch job with Google Sheets error."""
        signal_listener.redis_client = mock_redis

        with patch("gspread.service_account", side_effect=Exception("GSheet error")):
            # Should not raise exception, just log error
            await signal_listener._fetch_signal_job()

        # Verify Redis publish was not called due to error
        mock_redis.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_manual_fetch_signal_now(self, signal_listener, mock_gsheet_client):
        """Test manual signal fetch trigger."""
        mock_client, mock_worksheet = mock_gsheet_client

        sheet_data = [
            [
                "Date",
                "Ticker",
                "Strategy",
                "Qty_Per_Leg",
                "Strike_Long",
                "Strike_Short",
            ],
            ["2025-06-27", "QQQ", "Long", "10", "450.0", "455.0"],
        ]
        mock_worksheet.get_all_values.return_value = sheet_data

        with (
            patch("gspread.service_account", return_value=mock_client),
            freeze_time("2025-06-27 09:30:00", tz_offset=-5),
        ):  # EST

            signal = await signal_listener.fetch_signal_now()

        assert signal is not None
        assert signal.ticker == "QQQ"


class TestSignalModel:
    """Test Signal dataclass."""

    def test_signal_creation(self):
        """Test Signal dataclass creation."""
        signal = Signal(
            ticker="QQQ",
            strategy="Long",
            qty_per_leg=10,
            strike_long=450.0,
            strike_short=455.0,
            signal_date=date(2025, 6, 27),
            sheet_row=2,
            timestamp=datetime(2025, 6, 27, 9, 30, 0),
        )

        assert signal.ticker == "QQQ"
        assert signal.strategy == "Long"
        assert signal.qty_per_leg == 10
        assert signal.strike_long == 450.0
        assert signal.strike_short == 455.0

    def test_signal_to_dict(self):
        """Test Signal to_dict method."""
        signal = Signal(
            ticker="QQQ",
            strategy="Long",
            qty_per_leg=10,
            strike_long=450.0,
            strike_short=455.0,
            signal_date=date(2025, 6, 27),
            sheet_row=2,
            timestamp=datetime(2025, 6, 27, 9, 30, 0),
        )

        signal_dict = signal.to_dict()

        assert signal_dict["ticker"] == "QQQ"
        assert signal_dict["strategy"] == "Long"
        assert signal_dict["qty_per_leg"] == 10
        assert isinstance(signal_dict["signal_date"], date)
        assert isinstance(signal_dict["timestamp"], datetime)

    def test_signal_from_dict(self):
        """Test Signal from_dict method."""
        signal_data = {
            "ticker": "QQQ",
            "strategy": "Long",
            "qty_per_leg": 10,
            "strike_long": 450.0,
            "strike_short": 455.0,
            "signal_date": "2025-06-27",
            "sheet_row": 2,
            "timestamp": "2025-06-27T09:30:00",
        }

        signal = Signal.from_dict(signal_data)

        assert signal.ticker == "QQQ"
        assert signal.strategy == "Long"
        assert isinstance(signal.signal_date, date)
        assert isinstance(signal.timestamp, datetime)

    def test_signal_str_representation(self):
        """Test Signal string representation."""
        signal = Signal(
            ticker="QQQ",
            strategy="Long",
            qty_per_leg=10,
            strike_long=450.0,
            strike_short=455.0,
            signal_date=date(2025, 6, 27),
            sheet_row=2,
            timestamp=datetime(2025, 6, 27, 9, 30, 0),
        )

        str_repr = str(signal)
        assert "QQQ" in str_repr
        assert "Long" in str_repr
        assert "10x" in str_repr
        assert "450.0/455.0" in str_repr
        assert "2025-06-27" in str_repr


class TestSchedulerIntegration:
    """Test scheduler integration with freezegun."""

    @pytest.mark.asyncio
    async def test_scheduler_cron_trigger(self):
        """Test scheduler cron configuration."""
        import pytz
        from apscheduler.triggers.cron import CronTrigger

        # Test the cron trigger configuration
        eastern = pytz.timezone("US/Eastern")
        trigger = CronTrigger(hour=9, minute=27, timezone=eastern)

        # Test with specific date/time
        with freeze_time("2025-06-27 14:27:00"):  # 14:27 UTC = 09:27 EST
            next_run = trigger.get_next_fire_time(None, datetime.now(eastern))

            # Should be triggered at the frozen time
            assert next_run.hour == 9
            assert next_run.minute == 27

    @pytest.mark.asyncio
    async def test_timezone_handling(self, signal_listener):
        """Test US/Eastern timezone handling."""
        # Test timezone conversion
        eastern = signal_listener.eastern

        with freeze_time("2025-06-27 14:27:00"):  # UTC
            eastern_time = datetime.now(eastern)
            assert eastern_time.hour == 9  # 14:27 UTC = 09:27 EST (during DST)
            assert eastern_time.minute == 27

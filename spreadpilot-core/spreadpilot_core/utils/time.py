"""Time utilities for SpreadPilot."""

import datetime

import pytz

from ..logging import get_logger

logger = get_logger(__name__)

# New York timezone
NY_TIMEZONE = pytz.timezone("America/New_York")

# Market hours (Eastern Time)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0

# Market days (0 = Monday, 6 = Sunday)
MARKET_DAYS = [0, 1, 2, 3, 4]  # Monday to Friday


def get_ny_time(dt: datetime.datetime | None = None) -> datetime.datetime:
    """Get current time in New York timezone.

    Args:
        dt: Datetime to convert (default: current UTC time)

    Returns:
        Datetime in New York timezone
    """
    if dt is None:
        dt = datetime.datetime.now(pytz.UTC)
    elif dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)

    return dt.astimezone(NY_TIMEZONE)


def is_market_open(dt: datetime.datetime | None = None) -> bool:
    """Check if market is open.

    Args:
        dt: Datetime to check (default: current time)

    Returns:
        True if market is open, False otherwise
    """
    ny_time = get_ny_time(dt)

    # Check if it's a weekday
    if ny_time.weekday() not in MARKET_DAYS:
        return False

    # Check if it's within market hours
    market_open = ny_time.replace(
        hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0
    )
    market_close = ny_time.replace(
        hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0
    )

    return market_open <= ny_time < market_close


def get_market_open_close_times(
    date: datetime.date | None = None,
) -> tuple[datetime.datetime, datetime.datetime]:
    """Get market open and close times for a given date.

    Args:
        date: Date to get market hours for (default: today in NY)

    Returns:
        Tuple of (market_open, market_close) datetimes
    """
    if date is None:
        date = get_ny_time().date()

    # Create datetime objects for market open and close
    market_open = NY_TIMEZONE.localize(
        datetime.datetime.combine(
            date,
            datetime.time(MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE, 0),
        )
    )
    market_close = NY_TIMEZONE.localize(
        datetime.datetime.combine(
            date,
            datetime.time(MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE, 0),
        )
    )

    return market_open, market_close


def get_current_trading_date() -> str:
    """Get current trading date in YYYYMMDD format.

    Returns:
        Current trading date in YYYYMMDD format
    """
    ny_time = get_ny_time()

    # If it's before market open, use previous trading day
    if ny_time.hour < MARKET_OPEN_HOUR or (
        ny_time.hour == MARKET_OPEN_HOUR and ny_time.minute < MARKET_OPEN_MINUTE
    ):
        # Go back to previous trading day
        date = ny_time.date()
        days_back = 1

        # Keep going back until we find a trading day
        while days_back < 10:  # Limit to 10 days to avoid infinite loop
            date = date - datetime.timedelta(days=1)
            if date.weekday() in MARKET_DAYS:
                break
            days_back += 1

        return date.strftime("%Y%m%d")

    # If it's after market close but still the same day, use current date
    return ny_time.strftime("%Y%m%d")


def format_ny_time(dt: datetime.datetime | None = None) -> str:
    """Format datetime in New York timezone.

    Args:
        dt: Datetime to format (default: current time)

    Returns:
        Formatted datetime string
    """
    ny_time = get_ny_time(dt)
    return ny_time.strftime("%Y-%m-%d %H:%M:%S %Z")


def seconds_until_market_open(dt: datetime.datetime | None = None) -> int:
    """Get seconds until market open.

    Args:
        dt: Datetime to check from (default: current time)

    Returns:
        Seconds until market open, or 0 if market is open
    """
    ny_time = get_ny_time(dt)

    # If market is already open, return 0
    if is_market_open(ny_time):
        return 0

    # Get market open time for today
    market_open, _ = get_market_open_close_times(ny_time.date())

    # If it's after market close, get market open time for next trading day
    if ny_time > market_open:
        # Find next trading day
        next_date = ny_time.date() + datetime.timedelta(days=1)
        while next_date.weekday() not in MARKET_DAYS:
            next_date += datetime.timedelta(days=1)

        market_open, _ = get_market_open_close_times(next_date)

    # Calculate seconds until market open
    return int((market_open - ny_time).total_seconds())

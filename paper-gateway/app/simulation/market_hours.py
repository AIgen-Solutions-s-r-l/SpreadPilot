"""Market hours simulation for paper trading."""

from datetime import datetime, time
from typing import List

import pytz

from ..config import get_settings

# US market holidays for 2024-2025 (simplified)
MARKET_HOLIDAYS = [
    "2024-01-01",  # New Year's Day
    "2024-01-15",  # MLK Day
    "2024-02-19",  # Presidents Day
    "2024-03-29",  # Good Friday
    "2024-05-27",  # Memorial Day
    "2024-06-19",  # Juneteenth
    "2024-07-04",  # Independence Day
    "2024-09-02",  # Labor Day
    "2024-11-28",  # Thanksgiving
    "2024-12-25",  # Christmas
    "2025-01-01",  # New Year's Day
    "2025-01-20",  # MLK Day
    "2025-02-17",  # Presidents Day
    "2025-04-18",  # Good Friday
    "2025-05-26",  # Memorial Day
    "2025-06-19",  # Juneteenth
    "2025-07-04",  # Independence Day
    "2025-09-01",  # Labor Day
    "2025-11-27",  # Thanksgiving
    "2025-12-25",  # Christmas
]


def is_market_open(dt: datetime = None) -> bool:
    """Check if market is currently open.

    Args:
        dt: Datetime to check (defaults to now in US/Eastern)

    Returns:
        True if market is open, False otherwise
    """
    settings = get_settings()

    if dt is None:
        dt = datetime.now(pytz.timezone("US/Eastern"))
    elif dt.tzinfo is None:
        # Assume UTC and convert
        dt = dt.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone("US/Eastern"))

    # Weekend check
    if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    # Holiday check
    date_str = dt.strftime("%Y-%m-%d")
    if date_str in MARKET_HOLIDAYS:
        return False

    # Market hours check (9:30 AM - 4:00 PM ET)
    market_open = time(
        settings.market_open_hour,
        settings.market_open_minute,
    )
    market_close = time(
        settings.market_close_hour,
        settings.market_close_minute,
    )

    current_time = dt.time()
    return market_open <= current_time <= market_close


def get_market_status() -> dict:
    """Get current market status.

    Returns:
        Dict with market status information
    """
    now = datetime.now(pytz.timezone("US/Eastern"))
    is_open = is_market_open(now)

    settings = get_settings()
    market_open = time(settings.market_open_hour, settings.market_open_minute)
    market_close = time(settings.market_close_hour, settings.market_close_minute)

    return {
        "is_open": is_open,
        "current_time": now.isoformat(),
        "market_open_time": market_open.isoformat(),
        "market_close_time": market_close.isoformat(),
        "timezone": "US/Eastern",
        "is_weekend": now.weekday() >= 5,
        "is_holiday": now.strftime("%Y-%m-%d") in MARKET_HOLIDAYS,
    }


def get_next_market_open() -> datetime:
    """Get next market open time.

    Returns:
        Datetime of next market open
    """
    settings = get_settings()
    now = datetime.now(pytz.timezone("US/Eastern"))

    # Start checking from tomorrow
    check_date = now.replace(
        hour=settings.market_open_hour,
        minute=settings.market_open_minute,
        second=0,
        microsecond=0,
    )

    # If we're before market open today, check today first
    if now.time() < time(settings.market_open_hour, settings.market_open_minute):
        if is_market_open(check_date):
            return check_date

    # Otherwise check future days
    from datetime import timedelta

    for _ in range(10):  # Check up to 10 days ahead
        check_date += timedelta(days=1)
        if is_market_open(check_date):
            return check_date

    # Fallback (should never reach here)
    return check_date


def validate_trading_hours(dt: datetime = None) -> tuple[bool, str]:
    """Validate if trading is allowed at given time.

    Args:
        dt: Datetime to check (defaults to now)

    Returns:
        Tuple of (is_valid, rejection_reason)
    """
    if not is_market_open(dt):
        status = get_market_status()

        if status["is_weekend"]:
            return False, "Market closed: Weekend"
        elif status["is_holiday"]:
            return False, "Market closed: Holiday"
        else:
            return (
                False,
                f"Market closed: Outside trading hours ({status['market_open_time']}-{status['market_close_time']} ET)",
            )

    return True, ""

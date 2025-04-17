import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from google.cloud import firestore
from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.position import Position
from spreadpilot_core.models.follower import Follower

from .. import config

logger = get_logger(__name__)

# Initialize Firestore client (consider moving to a central db module if complexity grows)
try:
    db = firestore.Client(
        project=config.GCP_PROJECT_ID, database=config.FIRESTORE_DATABASE
    )
    logger.info(f"Firestore client initialized for project '{config.GCP_PROJECT_ID}' and database '{config.FIRESTORE_DATABASE}'")
except Exception as e:
    logger.exception("Failed to initialize Firestore client", exc_info=e)
    # Depending on deployment, might want to raise or exit
    db = None # Indicate failure

# --- Constants ---
TWO_PLACES = Decimal("0.01")

# --- Helper Functions ---

def _quantize(value: Decimal) -> Decimal:
    """Quantizes a Decimal value to two decimal places."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

# --- Daily P&L Calculation ---

# Structure for storing daily results (adjust collection name as needed)
DAILY_PNL_COLLECTION = "daily_pnl"

def calculate_and_store_daily_pnl(calculation_date: datetime.date) -> Decimal:
    """
    Fetches closed positions for a given date, calculates the total P&L,
    stores it in Firestore, and returns the calculated P&L.

    Args:
        calculation_date: The date for which to calculate P&L.

    Returns:
        The total P&L for the day as a Decimal.
        Returns Decimal(0) if Firestore client is not available or on error.
    """
    if not db:
        logger.error("Firestore client not available. Cannot calculate daily P&L.")
        return Decimal("0.0")

    logger.info(f"Calculating daily P&L for {calculation_date.isoformat()}...")

    start_dt = datetime.datetime.combine(calculation_date, datetime.time.min)
    end_dt = datetime.datetime.combine(calculation_date, datetime.time.max)

    total_daily_pnl = Decimal("0.0")
    positions_processed = 0

    try:
        positions_ref = db.collection(Position.collection_name())
        # Query for positions closed within the given date
        query = positions_ref.where("status", "==", "CLOSED").where(
            "close_timestamp", ">=", start_dt
        ).where("close_timestamp", "<=", end_dt)

        closed_positions = query.stream()

        for pos_snap in closed_positions:
            try:
                pos_data = pos_snap.to_dict()
                # Assuming 'pnl' is stored directly as a number/string convertible to Decimal
                pnl_value = Decimal(str(pos_data.get("pnl", "0.0")))
                total_daily_pnl += pnl_value
                positions_processed += 1
            except Exception as e:
                logger.warning(f"Failed to process position {pos_snap.id}: {e}", exc_info=True)

        logger.info(f"Processed {positions_processed} closed positions for {calculation_date.isoformat()}. Total P&L: {total_daily_pnl}")

        # Store the result in Firestore
        daily_pnl_doc_ref = db.collection(DAILY_PNL_COLLECTION).document(calculation_date.isoformat())
        daily_pnl_data = {
            "date": calculation_date.isoformat(),
            "total_pnl": str(total_daily_pnl), # Store as string for precision
            "calculation_timestamp": firestore.SERVER_TIMESTAMP,
            "positions_processed": positions_processed,
        }
        daily_pnl_doc_ref.set(daily_pnl_data)
        logger.info(f"Stored daily P&L for {calculation_date.isoformat()} in Firestore.")

        return _quantize(total_daily_pnl)

    except Exception as e:
        logger.exception(f"Error calculating or storing daily P&L for {calculation_date.isoformat()}", exc_info=e)
        return Decimal("0.0")


# --- Monthly P&L Calculation ---

def calculate_monthly_pnl(year: int, month: int) -> Decimal:
    """
    Calculates the total P&L for a given month by aggregating stored daily P&L figures.

    Args:
        year: The year.
        month: The month (1-12).

    Returns:
        The total P&L for the month as a Decimal.
        Returns Decimal(0) if Firestore client is not available or on error.
    """
    if not db:
        logger.error("Firestore client not available. Cannot calculate monthly P&L.")
        return Decimal("0.0")

    logger.info(f"Calculating monthly P&L for {year:04d}-{month:02d}...")

    # Determine date range for the query
    start_date_str = f"{year:04d}-{month:02d}-01"
    try:
        # Find the first day of the next month to set the upper bound
        if month == 12:
            end_date_str = f"{year + 1:04d}-01-01"
        else:
            end_date_str = f"{year:04d}-{month + 1:02d}-01"
    except ValueError:
        logger.error(f"Invalid year/month provided: {year}-{month}")
        return Decimal("0.0")

    total_monthly_pnl = Decimal("0.0")
    days_aggregated = 0

    try:
        daily_pnl_ref = db.collection(DAILY_PNL_COLLECTION)
        query = daily_pnl_ref.where("date", ">=", start_date_str).where("date", "<", end_date_str)

        daily_results = query.stream()

        for daily_snap in daily_results:
            try:
                daily_data = daily_snap.to_dict()
                daily_pnl = Decimal(str(daily_data.get("total_pnl", "0.0")))
                total_monthly_pnl += daily_pnl
                days_aggregated += 1
            except Exception as e:
                logger.warning(f"Failed to process daily P&L record {daily_snap.id}: {e}", exc_info=True)

        logger.info(f"Aggregated {days_aggregated} daily records for {year:04d}-{month:02d}. Total P&L: {total_monthly_pnl}")
        return _quantize(total_monthly_pnl)

    except Exception as e:
        logger.exception(f"Error calculating monthly P&L for {year:04d}-{month:02d}", exc_info=e)
        return Decimal("0.0")


# --- Commission Calculation ---

def calculate_commission(monthly_pnl: Decimal, follower: Follower) -> Decimal:
    """
    Calculates the commission based on the monthly P&L and follower's settings.

    Args:
        monthly_pnl: The total P&L for the month.
        follower: The Follower object containing commission details.

    Returns:
        The calculated commission amount as a Decimal.
    """
    if monthly_pnl <= 0:
        logger.debug(f"Monthly P&L is not positive ({monthly_pnl}). No commission for follower {follower.id}.")
        return Decimal("0.0")

    commission_pct = follower.commission_percentage
    if commission_pct is None:
        commission_pct = config.DEFAULT_COMMISSION_PERCENTAGE
        logger.debug(f"Follower {follower.id} has no specific commission percentage, using default: {commission_pct}%")
    else:
         logger.debug(f"Using follower {follower.id}'s commission percentage: {commission_pct}%")

    commission_pct_decimal = Decimal(str(commission_pct)) / Decimal("100.0")
    commission_amount = monthly_pnl * commission_pct_decimal

    quantized_commission = _quantize(commission_amount)
    logger.info(f"Calculated commission for follower {follower.id}: P&L={monthly_pnl}, Rate={commission_pct}%, Commission={quantized_commission}")
    return quantized_commission

# --- Follower Data Fetching (Moved to report_service, but placeholder if needed here) ---
# def get_all_active_followers() -> List[Follower]:
#     """Fetches all active followers from Firestore."""
#     # ... Implementation ...
#     pass

# Alias for backward compatibility with tests
calculate_daily_pnl = calculate_and_store_daily_pnl
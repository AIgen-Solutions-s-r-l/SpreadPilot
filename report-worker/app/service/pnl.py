import datetime

from spreadpilot_core.db.mongodb import get_mongo_db
from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.follower import Follower
from spreadpilot_core.models.position import Position

from .. import config

logger = get_logger(__name__)


async def _get_positions_for_month(year: int, month: int) -> list[Position]:
    """
    Fetches positions from MongoDB for the specified month.

    Args:
        year: The year to fetch positions for
        month: The month to fetch positions for (1-12)

    Returns:
        List of Position objects
    """
    try:
        db = await get_mongo_db()

        # Calculate start and end dates for the month
        start_date = datetime.date(year, month, 1)
        if month == 12:
            end_date = datetime.date(year + 1, 1, 1)
        else:
            end_date = datetime.date(year, month + 1, 1)

        # Convert to datetime for MongoDB query
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_datetime = datetime.datetime.combine(end_date, datetime.time.min)

        # Query positions collection
        positions_collection = db["positions"]
        cursor = positions_collection.find({"date": {"$gte": start_datetime, "$lt": end_datetime}})

        # Convert to Position objects
        positions = []
        async for doc in cursor:
            try:
                positions.append(Position.model_validate(doc))
            except Exception as e:
                doc_id = doc.get("_id", "UNKNOWN_ID")
                logger.warning(f"Failed to parse position data for {doc_id}: {e}", exc_info=True)

        logger.info(f"Fetched {len(positions)} positions for {year}-{month:02d}")
        return positions
    except Exception as e:
        logger.exception(f"Error fetching positions for {year}-{month:02d}", exc_info=e)
        return []


async def calculate_monthly_pnl(year: int, month: int) -> float:
    """
    Calculates the total P&L for the specified month.

    Args:
        year: The year to calculate P&L for
        month: The month to calculate P&L for (1-12)

    Returns:
        Total P&L for the month
    """
    logger.info(f"Calculating monthly P&L for {year}-{month:02d}")

    try:
        # Get all positions for the specified month
        positions = await _get_positions_for_month(year, month)

        total_pnl = 0.0

        for position in positions:
            # Calculate P&L for each position
            position_pnl = 0.0

            # For options, calculate based on entry price vs current/exit price
            if position.contract_type in ["CALL", "PUT"]:
                entry_value = float(position.avg_cost) * position.quantity

                # Use realized P&L if position is closed, otherwise current market value
                if position.quantity == 0:
                    # Closed position - use realized P&L
                    position_pnl = float(position.pnl_realized)
                else:
                    # Open position - calculate unrealized P&L
                    current_value = float(position.market_value or 0)
                    position_pnl = current_value - entry_value

            total_pnl += position_pnl

            logger.debug(
                f"Position {position.symbol} {position.strike}{position.contract_type}: "
                f"P&L = ${position_pnl:.2f}"
            )

        logger.info(f"Total monthly P&L for {year}-{month:02d}: ${total_pnl:.2f}")
        return total_pnl

    except Exception as e:
        logger.error(f"Error calculating monthly P&L: {e}", exc_info=True)
        return 0.0


def calculate_commission(total_pnl: float, follower: Follower) -> float:
    """
    Calculates the commission amount for a follower based on the total P&L.

    Args:
        total_pnl: The total P&L for the period
        follower: The follower to calculate commission for

    Returns:
        Commission amount
    """
    # Get commission percentage from follower or default
    commission_pct = (
        follower.commission_pct
        if follower.commission_pct is not None
        else config.DEFAULT_COMMISSION_PERCENTAGE
    )

    # Only calculate commission if P&L is positive
    if total_pnl <= 0:
        return 0.0

    # Calculate commission
    commission = total_pnl * (commission_pct / 100.0)

    logger.info(
        f"Calculated commission for follower {follower.id}: {commission} ({commission_pct}% of {total_pnl})"
    )
    return commission


async def calculate_and_store_daily_pnl(calculation_date: datetime.date) -> float:
    """
    Calculates and stores the daily P&L for the specified date.

    Args:
        calculation_date: The date to calculate P&L for

    Returns:
        Daily P&L for the date
    """
    logger.info(f"Calculating daily P&L for {calculation_date.isoformat()}")

    try:
        # Get MongoDB connection
        db = await get_mongo_db()
        if not db:
            logger.error("Failed to connect to MongoDB")
            return 0.0

        # Calculate start and end datetime for the day
        start_datetime = datetime.datetime.combine(calculation_date, datetime.time.min)
        end_datetime = datetime.datetime.combine(calculation_date, datetime.time.max)

        # Fetch positions from MongoDB for the specified date
        positions_collection = db["positions"]
        cursor = positions_collection.find({"date": {"$gte": start_datetime, "$lte": end_datetime}})

        total_daily_pnl = 0.0
        position_count = 0

        async for position_doc in cursor:
            try:
                # Convert to Position object
                position = Position.model_validate(position_doc)

                # Calculate daily P&L for this position
                position_pnl = 0.0

                if position.contract_type in ["CALL", "PUT"]:
                    # Use daily realized P&L plus change in unrealized P&L
                    position_pnl = float(position.pnl_realized or 0)

                    # Add unrealized P&L change if position is still open
                    if position.quantity != 0:
                        position_pnl += float(position.pnl_unrealized or 0)

                total_daily_pnl += position_pnl
                position_count += 1

                logger.debug(
                    f"Position {position.symbol} {position.strike}{position.contract_type}: "
                    f"Daily P&L = ${position_pnl:.2f}"
                )

            except Exception as e:
                logger.error(f"Error processing position: {e}")
                continue

        # Store the daily P&L in MongoDB (optional - could store in a daily_pnl collection)
        daily_pnl_collection = db["daily_pnl"]
        await daily_pnl_collection.update_one(
            {"date": calculation_date.isoformat()},
            {
                "$set": {
                    "date": calculation_date.isoformat(),
                    "total_pnl": total_daily_pnl,
                    "position_count": position_count,
                    "calculated_at": datetime.datetime.utcnow(),
                }
            },
            upsert=True,
        )

        logger.info(
            f"Daily P&L for {calculation_date.isoformat()}: ${total_daily_pnl:.2f} "
            f"({position_count} positions)"
        )
        return total_daily_pnl

    except Exception as e:
        logger.error(f"Error calculating daily P&L: {e}", exc_info=True)
        return 0.0

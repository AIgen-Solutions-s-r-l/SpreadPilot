from datetime import date, datetime

import pytz
from app.api.v1.endpoints.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from spreadpilot_core.db.mongodb import get_mongo_db
from spreadpilot_core.logging.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# NY timezone for market hours
NY_TZ = pytz.timezone("America/New_York")


@router.get("/today", dependencies=[Depends(get_current_user)])
async def get_today_pnl():
    """
    Get today's P&L data.
    Returns the current day's profit and loss information.
    """
    try:
        db: AsyncIOMotorDatabase = await get_mongo_db()

        # Get today's date in NY timezone
        today = datetime.now(NY_TZ).date()

        # Query for today's P&L data
        pnl_collection = db["daily_pnl"]
        today_pnl = await pnl_collection.find_one(
            {"date": today.isoformat()}, {"_id": 0}
        )

        if not today_pnl:
            return {
                "date": today.isoformat(),
                "total_pnl": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "trades": [],
                "message": "No P&L data available for today",
            }

        return today_pnl

    except Exception as e:
        logger.error(f"Error fetching today's P&L: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch P&L data",
        )


@router.get("/month", dependencies=[Depends(get_current_user)])
async def get_month_pnl(year: int | None = None, month: int | None = None):
    """
    Get monthly P&L data.
    If year and month are not provided, returns current month's data.
    """
    try:
        db: AsyncIOMotorDatabase = await get_mongo_db()

        # Default to current month if not specified
        if not year or not month:
            now = datetime.now(NY_TZ)
            year = now.year
            month = now.month

        # Validate month
        if month < 1 or month > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid month. Must be between 1 and 12",
            )

        # Calculate date range for the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        # Query for monthly P&L data
        pnl_collection = db["daily_pnl"]
        cursor = pnl_collection.find(
            {"date": {"$gte": start_date.isoformat(), "$lt": end_date.isoformat()}},
            {"_id": 0},
        ).sort("date", 1)

        daily_pnl_list = await cursor.to_list(length=None)

        # Calculate monthly totals
        total_pnl = sum(day.get("total_pnl", 0) for day in daily_pnl_list)
        realized_pnl = sum(day.get("realized_pnl", 0) for day in daily_pnl_list)
        unrealized_pnl = sum(day.get("unrealized_pnl", 0) for day in daily_pnl_list)

        return {
            "year": year,
            "month": month,
            "total_pnl": total_pnl,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "daily_breakdown": daily_pnl_list,
            "days_with_data": len(daily_pnl_list),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching monthly P&L: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch monthly P&L data",
        )

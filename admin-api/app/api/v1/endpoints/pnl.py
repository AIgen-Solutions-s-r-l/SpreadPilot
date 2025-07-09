from datetime import date, datetime

import pytz
from app.api.v1.endpoints.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from spreadpilot_core.db.postgresql import get_postgres_session
from spreadpilot_core.models.pnl import PnLIntraday, PnLMonthly
from spreadpilot_core.logging.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# NY timezone for market hours
NY_TZ = pytz.timezone("America/New_York")


@router.get("/today", dependencies=[Depends(get_current_user)])
async def get_today_pnl():
    """
    Get today's P&L data for all followers.
    Returns the current day's profit and loss information from pnl_intraday table.
    """
    try:
        async with get_postgres_session() as session:
            # Get today's date in NY timezone
            today = datetime.now(NY_TZ).date()
            
            # Query for today's P&L data - get latest snapshot for each follower
            stmt = (
                select(
                    PnLIntraday.follower_id,
                    func.sum(PnLIntraday.total_pnl).label("pnl")
                )
                .where(PnLIntraday.trading_date == today)
                .group_by(PnLIntraday.follower_id)
            )
            
            result = await session.execute(stmt)
            pnl_data = [
                {"follower_id": row.follower_id, "pnl": float(row.pnl or 0)}
                for row in result
            ]
            
            return pnl_data

    except Exception as e:
        logger.error(f"Error fetching today's P&L: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch P&L data",
        )


@router.get("/month", dependencies=[Depends(get_current_user)])
async def get_month_pnl(year: int | None = None, month: int | None = None):
    """
    Get monthly P&L data for all followers.
    If year and month are not provided, returns current month's data from pnl_monthly table.
    """
    try:
        async with get_postgres_session() as session:
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

            # Query pnl_monthly table
            stmt = (
                select(
                    PnLMonthly.follower_id,
                    PnLMonthly.total_pnl.label("pnl")
                )
                .where(
                    (PnLMonthly.year == year) & 
                    (PnLMonthly.month == month)
                )
            )
            
            result = await session.execute(stmt)
            pnl_data = [
                {"follower_id": row.follower_id, "pnl": float(row.pnl or 0)}
                for row in result
            ]
            
            return pnl_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching monthly P&L: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch monthly P&L data",
        )

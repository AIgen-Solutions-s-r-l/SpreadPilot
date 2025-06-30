from datetime import date, datetime
from typing import List

import pytz
from app.api.v1.endpoints.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from spreadpilot_core.db.postgresql import get_postgres_session
from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.pnl import PnLDaily, PnLIntraday, PnLMonthly

router = APIRouter()
logger = get_logger(__name__)

# NY timezone for market hours
NY_TZ = pytz.timezone("America/New_York")


@router.get("/today", dependencies=[Depends(get_current_user)])
async def get_today_pnl():
    """
    Get today's P&L data.
    Returns aggregated P&L for all followers for the current day.
    """
    try:
        today = datetime.now(NY_TZ).date()

        async with get_postgres_session() as session:
            # Get today's daily P&L data for all followers
            daily_result = await session.execute(
                select(PnLDaily)
                .where(PnLDaily.trading_date == today)
                .order_by(desc(PnLDaily.rollup_time))
            )
            daily_summaries = daily_result.scalars().all()

            # Get latest intraday snapshots for real-time data
            intraday_result = await session.execute(
                select(PnLIntraday)
                .where(
                    and_(
                        PnLIntraday.trading_date == today,
                        PnLIntraday.snapshot_time
                        >= datetime.combine(today, datetime.min.time().replace(tzinfo=NY_TZ)),
                    )
                )
                .order_by(desc(PnLIntraday.snapshot_time))
                .limit(50)  # Get latest snapshots
            )
            intraday_snapshots = intraday_result.scalars().all()

            # Aggregate totals
            total_realized = sum(d.realized_pnl for d in daily_summaries)
            total_unrealized = sum(d.unrealized_pnl_end for d in daily_summaries)
            total_pnl = total_realized + total_unrealized
            total_trades = sum(d.trades_count for d in daily_summaries)
            total_commission = sum(d.total_commission for d in daily_summaries)

            # Get follower breakdown
            follower_breakdown = []
            for daily in daily_summaries:
                follower_breakdown.append(
                    {
                        "follower_id": daily.follower_id,
                        "realized_pnl": float(daily.realized_pnl),
                        "unrealized_pnl": float(daily.unrealized_pnl_end),
                        "total_pnl": float(daily.total_pnl),
                        "trades_count": daily.trades_count,
                        "commission": float(daily.total_commission),
                        "positions": daily.closing_positions,
                    }
                )

            return {
                "date": today.isoformat(),
                "total_pnl": float(total_pnl),
                "realized_pnl": float(total_realized),
                "unrealized_pnl": float(total_unrealized),
                "total_trades": total_trades,
                "total_commission": float(total_commission),
                "follower_breakdown": follower_breakdown,
                "intraday_snapshots_count": len(intraday_snapshots),
                "last_update": (
                    intraday_snapshots[0].snapshot_time.isoformat() if intraday_snapshots else None
                ),
            }

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

        async with get_postgres_session() as session:
            # Get monthly P&L summaries
            monthly_result = await session.execute(
                select(PnLMonthly)
                .where(and_(PnLMonthly.year == year, PnLMonthly.month == month))
                .order_by(PnLMonthly.follower_id)
            )
            monthly_summaries = monthly_result.scalars().all()

            # Get daily breakdown for the month
            daily_result = await session.execute(
                select(PnLDaily)
                .where(
                    and_(
                        func.extract("year", PnLDaily.trading_date) == year,
                        func.extract("month", PnLDaily.trading_date) == month,
                    )
                )
                .order_by(PnLDaily.trading_date, PnLDaily.follower_id)
            )
            daily_summaries = daily_result.scalars().all()

            # Aggregate monthly totals
            total_realized = sum(m.realized_pnl for m in monthly_summaries)
            total_unrealized = sum(m.unrealized_pnl_end for m in monthly_summaries)
            total_pnl = sum(m.total_pnl for m in monthly_summaries)
            total_trades = sum(m.total_trades for m in monthly_summaries)
            total_commission = sum(m.total_commission for m in monthly_summaries)
            total_trading_days = sum(m.trading_days for m in monthly_summaries)

            # Calculate performance metrics
            best_day = max((m.best_day_pnl for m in monthly_summaries if m.best_day_pnl), default=0)
            worst_day = min(
                (m.worst_day_pnl for m in monthly_summaries if m.worst_day_pnl), default=0
            )
            total_winning_days = sum(m.winning_days for m in monthly_summaries)
            total_losing_days = sum(m.losing_days for m in monthly_summaries)

            # Follower breakdown
            follower_breakdown = []
            for monthly in monthly_summaries:
                follower_breakdown.append(
                    {
                        "follower_id": monthly.follower_id,
                        "realized_pnl": float(monthly.realized_pnl),
                        "unrealized_pnl": float(monthly.unrealized_pnl_end),
                        "total_pnl": float(monthly.total_pnl),
                        "trading_days": monthly.trading_days,
                        "total_trades": monthly.total_trades,
                        "commission": float(monthly.total_commission),
                        "avg_daily_pnl": (
                            float(monthly.avg_daily_pnl) if monthly.avg_daily_pnl else 0
                        ),
                        "best_day": float(monthly.best_day_pnl) if monthly.best_day_pnl else 0,
                        "worst_day": float(monthly.worst_day_pnl) if monthly.worst_day_pnl else 0,
                        "winning_days": monthly.winning_days,
                        "losing_days": monthly.losing_days,
                        "win_rate": (
                            (monthly.winning_days / monthly.trading_days * 100)
                            if monthly.trading_days > 0
                            else 0
                        ),
                    }
                )

            # Daily breakdown
            daily_breakdown = []
            for daily in daily_summaries:
                daily_breakdown.append(
                    {
                        "date": daily.trading_date.isoformat(),
                        "follower_id": daily.follower_id,
                        "total_pnl": float(daily.total_pnl),
                        "realized_pnl": float(daily.realized_pnl),
                        "trades_count": daily.trades_count,
                        "commission": float(daily.total_commission),
                    }
                )

            return {
                "year": year,
                "month": month,
                "total_pnl": float(total_pnl),
                "realized_pnl": float(total_realized),
                "unrealized_pnl": float(total_unrealized),
                "total_trades": total_trades,
                "total_commission": float(total_commission),
                "trading_days": total_trading_days,
                "best_day": float(best_day),
                "worst_day": float(worst_day),
                "winning_days": total_winning_days,
                "losing_days": total_losing_days,
                "win_rate": (
                    (total_winning_days / total_trading_days * 100) if total_trading_days > 0 else 0
                ),
                "follower_breakdown": follower_breakdown,
                "daily_breakdown": daily_breakdown,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching monthly P&L: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch monthly P&L data",
        )

"""P&L service for real-time monitoring and daily/monthly rollups."""

import asyncio
import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Set
from datetime import date, time
import pytz

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from spreadpilot_core.logging import get_logger
from spreadpilot_core.db.postgresql import get_postgres_session
from spreadpilot_core.models.pnl import (
    Trade, Quote, PnLIntraday, PnLDaily, PnLMonthly, TradeType
)
from spreadpilot_core.models import Position  # MongoDB position model
from spreadpilot_core.db.mongodb import get_mongo_db

logger = get_logger(__name__)

# Eastern timezone for rollup times
ET = pytz.timezone('US/Eastern')


class PnLService:
    """Service for P&L tracking, calculation, and rollups."""

    def __init__(self, trading_service):
        """Initialize P&L service.
        
        Args:
            trading_service: Main trading service instance
        """
        self.trading_service = trading_service
        self.monitoring_active = False
        self.subscriptions_active = False
        
        # Track active followers for P&L calculation
        self.active_followers: Set[str] = set()
        
        # In-memory quote cache for faster MTM calculations
        self.quote_cache: Dict[str, Quote] = {}
        
        logger.info("Initialized P&L service")

    async def start_monitoring(self, shutdown_event: asyncio.Event):
        """Start P&L monitoring and rollup tasks.
        
        Args:
            shutdown_event: Event to signal shutdown
        """
        try:
            logger.info("Starting P&L monitoring service")
            self.monitoring_active = True
            
            # Start concurrent tasks
            tasks = [
                asyncio.create_task(self._mtm_calculation_loop(shutdown_event)),
                asyncio.create_task(self._daily_rollup_scheduler(shutdown_event)),
                asyncio.create_task(self._monthly_rollup_scheduler(shutdown_event)),
                asyncio.create_task(self._quote_subscription_loop(shutdown_event)),
            ]
            
            # Wait for any task to complete or shutdown
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            logger.info("P&L monitoring service cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in P&L monitoring service: {e}", exc_info=True)
        finally:
            self.monitoring_active = False
            self.subscriptions_active = False

    async def _mtm_calculation_loop(self, shutdown_event: asyncio.Event):
        """Calculate mark-to-market P&L every 30 seconds."""
        try:
            while not shutdown_event.is_set() and self.monitoring_active:
                try:
                    # Only calculate during market hours
                    if self.trading_service.is_market_open():
                        await self._calculate_and_store_mtm()
                    
                    # Wait 30 seconds before next calculation
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"Error in MTM calculation: {e}", exc_info=True)
                    await asyncio.sleep(10)  # Wait before retrying
                    
        except asyncio.CancelledError:
            logger.info("MTM calculation loop cancelled")
            raise

    async def _calculate_and_store_mtm(self):
        """Calculate current mark-to-market P&L for all active followers."""
        try:
            # Get active followers from trading service
            self.active_followers = set(self.trading_service.active_followers)
            
            if not self.active_followers:
                logger.debug("No active followers for P&L calculation")
                return
            
            # Calculate P&L for each follower
            for follower_id in self.active_followers:
                try:
                    await self._calculate_follower_mtm(follower_id)
                except Exception as e:
                    logger.error(f"Error calculating MTM for follower {follower_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in MTM calculation: {e}")

    async def _calculate_follower_mtm(self, follower_id: str):
        """Calculate and store MTM P&L for a specific follower."""
        try:
            # Get current positions from MongoDB
            mongo_db = await get_mongo_db()
            positions_collection = mongo_db["positions"]
            
            # Get today's positions
            today = datetime.date.today().strftime("%Y%m%d")
            position_doc = await positions_collection.find_one({
                "follower_id": follower_id,
                "date": today
            })
            
            if not position_doc:
                logger.debug(f"No positions found for follower {follower_id} on {today}")
                return
            
            # Get IBKR client for real-time P&L
            client = await self.trading_service.ibkr_manager.get_client(follower_id)
            if not client:
                logger.warning(f"No IBKR client available for follower {follower_id}")
                return
            
            # Get current P&L from IBKR
            ibkr_pnl = await client.get_pnl()
            if ibkr_pnl is None:
                logger.warning(f"Could not get P&L from IBKR for follower {follower_id}")
                return
            
            # Calculate additional metrics
            position_count = self._count_active_positions(position_doc)
            total_market_value = await self._calculate_market_value(client, position_doc)
            total_commission = await self._get_daily_commission(follower_id)
            
            # Store intraday P&L snapshot
            await self._store_intraday_pnl(
                follower_id=follower_id,
                realized_pnl=Decimal(str(position_doc.get("pnl_realized", 0))),
                unrealized_pnl=Decimal(str(ibkr_pnl)),
                position_count=position_count,
                total_market_value=total_market_value,
                total_commission=total_commission
            )
            
            logger.debug(f"Stored MTM P&L for follower {follower_id}: "
                        f"realized=${position_doc.get('pnl_realized', 0):.2f}, "
                        f"unrealized=${ibkr_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error calculating follower MTM for {follower_id}: {e}")

    def _count_active_positions(self, position_doc: dict) -> int:
        """Count active positions from position document."""
        long_qty = position_doc.get("long_qty", 0)
        short_qty = position_doc.get("short_qty", 0)
        return abs(long_qty) + abs(short_qty)

    async def _calculate_market_value(self, client, position_doc: dict) -> Decimal:
        """Calculate total market value of positions."""
        try:
            # Get current market value from IBKR
            market_value = await client.get_portfolio_value()
            return Decimal(str(market_value or 0))
        except Exception as e:
            logger.error(f"Error calculating market value: {e}")
            return Decimal("0")

    async def _get_daily_commission(self, follower_id: str) -> Decimal:
        """Get total commission for today."""
        try:
            today = datetime.date.today()
            
            async with get_postgres_session() as session:
                result = await session.execute(
                    select(func.sum(Trade.commission))
                    .where(
                        and_(
                            Trade.follower_id == follower_id,
                            func.date(Trade.trade_time) == today
                        )
                    )
                )
                commission = result.scalar() or Decimal("0")
                return commission
                
        except Exception as e:
            logger.error(f"Error getting daily commission for {follower_id}: {e}")
            return Decimal("0")

    async def _store_intraday_pnl(self, follower_id: str, realized_pnl: Decimal, 
                                 unrealized_pnl: Decimal, position_count: int,
                                 total_market_value: Decimal, total_commission: Decimal):
        """Store intraday P&L snapshot."""
        try:
            now = datetime.datetime.utcnow()
            today = now.date()
            
            pnl_snapshot = PnLIntraday(
                follower_id=follower_id,
                snapshot_time=now,
                trading_date=today,
                realized_pnl=realized_pnl,
                unrealized_pnl=unrealized_pnl,
                total_pnl=realized_pnl + unrealized_pnl,
                position_count=position_count,
                total_market_value=total_market_value,
                total_commission=total_commission
            )
            
            async with get_postgres_session() as session:
                session.add(pnl_snapshot)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing intraday P&L: {e}")

    async def _quote_subscription_loop(self, shutdown_event: asyncio.Event):
        """Subscribe to quote feeds and store in database."""
        try:
            self.subscriptions_active = True
            logger.info("Starting quote subscription loop")
            
            while not shutdown_event.is_set() and self.subscriptions_active:
                try:
                    # Subscribe to quotes for active positions
                    await self._subscribe_to_position_quotes()
                    
                    # Wait before next subscription check
                    await asyncio.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"Error in quote subscription: {e}", exc_info=True)
                    await asyncio.sleep(30)
                    
        except asyncio.CancelledError:
            logger.info("Quote subscription loop cancelled")
            raise
        finally:
            self.subscriptions_active = False

    async def _subscribe_to_position_quotes(self):
        """Subscribe to quotes for all active positions."""
        try:
            # This is a placeholder - in real implementation, you would:
            # 1. Get all active option contracts from positions
            # 2. Subscribe to IBKR market data for those contracts
            # 3. Store quotes as they arrive
            
            # For now, we'll simulate this by getting current quotes
            for follower_id in self.active_followers:
                client = await self.trading_service.ibkr_manager.get_client(follower_id)
                if client:
                    # Get quotes for active positions
                    # This would be implemented based on IBKR API capabilities
                    pass
                    
        except Exception as e:
            logger.error(f"Error subscribing to position quotes: {e}")

    async def _daily_rollup_scheduler(self, shutdown_event: asyncio.Event):
        """Schedule daily rollups at 16:30 ET."""
        try:
            while not shutdown_event.is_set() and self.monitoring_active:
                try:
                    # Check if it's time for daily rollup (16:30 ET)
                    now_et = datetime.datetime.now(ET)
                    target_time = time(16, 30)  # 4:30 PM ET
                    
                    if (now_et.time() >= target_time and 
                        now_et.time() <= time(16, 35)):  # 5-minute window
                        
                        # Check if we already ran today
                        if not await self._daily_rollup_completed_today():
                            logger.info("Starting daily P&L rollup at 16:30 ET")
                            await self._perform_daily_rollup()
                    
                    # Check every minute
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Error in daily rollup scheduler: {e}", exc_info=True)
                    await asyncio.sleep(60)
                    
        except asyncio.CancelledError:
            logger.info("Daily rollup scheduler cancelled")
            raise

    async def _monthly_rollup_scheduler(self, shutdown_event: asyncio.Event):
        """Schedule monthly rollups at 00:10 ET on 1st of month."""
        try:
            while not shutdown_event.is_set() and self.monitoring_active:
                try:
                    # Check if it's time for monthly rollup (00:10 ET on 1st)
                    now_et = datetime.datetime.now(ET)
                    
                    if (now_et.day == 1 and 
                        now_et.time() >= time(0, 10) and 
                        now_et.time() <= time(0, 15)):  # 5-minute window
                        
                        # Check if we already ran this month
                        if not await self._monthly_rollup_completed():
                            logger.info("Starting monthly P&L rollup at 00:10 ET")
                            await self._perform_monthly_rollup()
                    
                    # Check every hour
                    await asyncio.sleep(3600)
                    
                except Exception as e:
                    logger.error(f"Error in monthly rollup scheduler: {e}", exc_info=True)
                    await asyncio.sleep(3600)
                    
        except asyncio.CancelledError:
            logger.info("Monthly rollup scheduler cancelled")
            raise

    async def _daily_rollup_completed_today(self) -> bool:
        """Check if daily rollup was already completed today."""
        try:
            today = datetime.date.today()
            
            async with get_postgres_session() as session:
                result = await session.execute(
                    select(PnLDaily)
                    .where(
                        and_(
                            PnLDaily.trading_date == today,
                            PnLDaily.is_finalized == True
                        )
                    )
                    .limit(1)
                )
                return result.scalar() is not None
                
        except Exception as e:
            logger.error(f"Error checking daily rollup status: {e}")
            return False

    async def _monthly_rollup_completed(self) -> bool:
        """Check if monthly rollup was completed for current month."""
        try:
            now = datetime.datetime.now()
            # Check previous month since rollup happens on 1st
            if now.month == 1:
                year, month = now.year - 1, 12
            else:
                year, month = now.year, now.month - 1
            
            async with get_postgres_session() as session:
                result = await session.execute(
                    select(PnLMonthly)
                    .where(
                        and_(
                            PnLMonthly.year == year,
                            PnLMonthly.month == month,
                            PnLMonthly.is_finalized == True
                        )
                    )
                    .limit(1)
                )
                return result.scalar() is not None
                
        except Exception as e:
            logger.error(f"Error checking monthly rollup status: {e}")
            return False

    async def _perform_daily_rollup(self):
        """Perform daily P&L rollup for all followers."""
        try:
            today = datetime.date.today()
            
            for follower_id in self.active_followers:
                try:
                    await self._rollup_daily_pnl(follower_id, today)
                except Exception as e:
                    logger.error(f"Error in daily rollup for follower {follower_id}: {e}")
            
            logger.info(f"Completed daily P&L rollup for {len(self.active_followers)} followers")
            
        except Exception as e:
            logger.error(f"Error in daily rollup: {e}")

    async def _rollup_daily_pnl(self, follower_id: str, trading_date: date):
        """Rollup daily P&L for a specific follower."""
        try:
            async with get_postgres_session() as session:
                # Get all intraday snapshots for the day
                intraday_result = await session.execute(
                    select(PnLIntraday)
                    .where(
                        and_(
                            PnLIntraday.follower_id == follower_id,
                            PnLIntraday.trading_date == trading_date
                        )
                    )
                    .order_by(PnLIntraday.snapshot_time)
                )
                intraday_snapshots = intraday_result.scalars().all()
                
                if not intraday_snapshots:
                    logger.debug(f"No intraday data for follower {follower_id} on {trading_date}")
                    return
                
                # Calculate daily metrics
                first_snapshot = intraday_snapshots[0]
                last_snapshot = intraday_snapshots[-1]
                
                # Get trade count and volume for the day
                trades_result = await session.execute(
                    select(
                        func.count(Trade.id),
                        func.sum(func.abs(Trade.quantity)),
                        func.sum(Trade.commission)
                    )
                    .where(
                        and_(
                            Trade.follower_id == follower_id,
                            func.date(Trade.trade_time) == trading_date
                        )
                    )
                )
                trade_stats = trades_result.first()
                trades_count = trade_stats[0] or 0
                total_volume = trade_stats[1] or 0
                total_commission = trade_stats[2] or Decimal("0")
                
                # Calculate performance metrics
                max_profit = max((s.total_pnl for s in intraday_snapshots), default=Decimal("0"))
                max_drawdown = min((s.total_pnl for s in intraday_snapshots), default=Decimal("0"))
                
                # Create daily summary
                daily_pnl = PnLDaily(
                    follower_id=follower_id,
                    trading_date=trading_date,
                    opening_balance=first_snapshot.total_market_value,
                    opening_positions=first_snapshot.position_count,
                    realized_pnl=last_snapshot.realized_pnl,
                    unrealized_pnl_start=first_snapshot.unrealized_pnl,
                    unrealized_pnl_end=last_snapshot.unrealized_pnl,
                    total_pnl=last_snapshot.total_pnl,
                    trades_count=trades_count,
                    total_volume=total_volume,
                    total_commission=total_commission,
                    closing_balance=last_snapshot.total_market_value,
                    closing_positions=last_snapshot.position_count,
                    max_drawdown=max_drawdown,
                    max_profit=max_profit,
                    is_finalized=True,
                    rollup_time=datetime.datetime.utcnow()
                )
                
                session.add(daily_pnl)
                await session.commit()
                
                logger.info(f"Completed daily rollup for follower {follower_id}: "
                           f"total_pnl=${daily_pnl.total_pnl:.2f}, trades={trades_count}")
                
        except Exception as e:
            logger.error(f"Error in daily rollup for {follower_id}: {e}")

    async def _perform_monthly_rollup(self):
        """Perform monthly P&L rollup for all followers."""
        try:
            # Get previous month
            now = datetime.datetime.now()
            if now.month == 1:
                year, month = now.year - 1, 12
            else:
                year, month = now.year, now.month - 1
            
            for follower_id in self.active_followers:
                try:
                    await self._rollup_monthly_pnl(follower_id, year, month)
                except Exception as e:
                    logger.error(f"Error in monthly rollup for follower {follower_id}: {e}")
            
            logger.info(f"Completed monthly P&L rollup for {year}-{month:02d}")
            
        except Exception as e:
            logger.error(f"Error in monthly rollup: {e}")

    async def _rollup_monthly_pnl(self, follower_id: str, year: int, month: int):
        """Rollup monthly P&L for a specific follower."""
        try:
            async with get_postgres_session() as session:
                # Get all daily summaries for the month
                daily_result = await session.execute(
                    select(PnLDaily)
                    .where(
                        and_(
                            PnLDaily.follower_id == follower_id,
                            func.extract('year', PnLDaily.trading_date) == year,
                            func.extract('month', PnLDaily.trading_date) == month
                        )
                    )
                    .order_by(PnLDaily.trading_date)
                )
                daily_summaries = daily_result.scalars().all()
                
                if not daily_summaries:
                    logger.debug(f"No daily data for follower {follower_id} in {year}-{month:02d}")
                    return
                
                # Calculate monthly metrics
                total_realized = sum(d.realized_pnl for d in daily_summaries)
                total_pnl = sum(d.total_pnl for d in daily_summaries)
                total_trades = sum(d.trades_count for d in daily_summaries)
                total_volume = sum(d.total_volume for d in daily_summaries)
                total_commission = sum(d.total_commission for d in daily_summaries)
                
                # Performance metrics
                best_day = max((d.total_pnl for d in daily_summaries), default=Decimal("0"))
                worst_day = min((d.total_pnl for d in daily_summaries), default=Decimal("0"))
                max_profit = max((d.max_profit for d in daily_summaries if d.max_profit), default=Decimal("0"))
                max_drawdown = min((d.max_drawdown for d in daily_summaries if d.max_drawdown), default=Decimal("0"))
                
                # Win/Loss statistics
                winning_days = sum(1 for d in daily_summaries if d.total_pnl > 0)
                losing_days = sum(1 for d in daily_summaries if d.total_pnl < 0)
                breakeven_days = sum(1 for d in daily_summaries if d.total_pnl == 0)
                
                avg_daily_pnl = total_pnl / len(daily_summaries) if daily_summaries else Decimal("0")
                
                # Get start/end unrealized P&L
                first_day = daily_summaries[0]
                last_day = daily_summaries[-1]
                
                monthly_pnl = PnLMonthly(
                    follower_id=follower_id,
                    year=year,
                    month=month,
                    realized_pnl=total_realized,
                    unrealized_pnl_start=first_day.unrealized_pnl_start,
                    unrealized_pnl_end=last_day.unrealized_pnl_end,
                    total_pnl=total_pnl,
                    trading_days=len(daily_summaries),
                    total_trades=total_trades,
                    total_volume=total_volume,
                    total_commission=total_commission,
                    best_day_pnl=best_day,
                    worst_day_pnl=worst_day,
                    max_drawdown=max_drawdown,
                    max_profit=max_profit,
                    avg_daily_pnl=avg_daily_pnl,
                    winning_days=winning_days,
                    losing_days=losing_days,
                    breakeven_days=breakeven_days,
                    is_finalized=True,
                    rollup_time=datetime.datetime.utcnow()
                )
                
                session.add(monthly_pnl)
                await session.commit()
                
                logger.info(f"Completed monthly rollup for follower {follower_id} {year}-{month:02d}: "
                           f"total_pnl=${monthly_pnl.total_pnl:.2f}, "
                           f"winning_days={winning_days}, losing_days={losing_days}")
                
        except Exception as e:
            logger.error(f"Error in monthly rollup for {follower_id}: {e}")

    async def record_trade_fill(self, follower_id: str, trade_data: dict):
        """Record a trade fill in the P&L database.
        
        Args:
            follower_id: Follower ID
            trade_data: Trade execution details
        """
        try:
            trade = Trade(
                follower_id=follower_id,
                symbol=trade_data.get("symbol", "QQQ"),
                contract_type=trade_data.get("contract_type", "PUT"),
                strike=Decimal(str(trade_data.get("strike", 0))),
                expiration=trade_data.get("expiration"),
                trade_type=trade_data.get("side", "BUY"),
                quantity=trade_data.get("quantity", 0),
                price=Decimal(str(trade_data.get("price", 0))),
                commission=Decimal(str(trade_data.get("commission", 0))),
                order_id=trade_data.get("order_id"),
                execution_id=trade_data.get("execution_id"),
                trade_time=trade_data.get("trade_time", datetime.datetime.utcnow())
            )
            
            async with get_postgres_session() as session:
                session.add(trade)
                await session.commit()
                
            logger.info(f"Recorded trade fill for {follower_id}: "
                       f"{trade.trade_type} {trade.quantity} {trade.symbol} "
                       f"{trade.strike}{trade.contract_type} @ ${trade.price}")
                       
        except Exception as e:
            logger.error(f"Error recording trade fill: {e}")

    async def get_real_time_pnl(self, follower_id: str) -> Optional[dict]:
        """Get latest real-time P&L for a follower."""
        try:
            async with get_postgres_session() as session:
                result = await session.execute(
                    select(PnLIntraday)
                    .where(PnLIntraday.follower_id == follower_id)
                    .order_by(desc(PnLIntraday.snapshot_time))
                    .limit(1)
                )
                latest_pnl = result.scalar()
                
                if latest_pnl:
                    return {
                        "follower_id": latest_pnl.follower_id,
                        "snapshot_time": latest_pnl.snapshot_time,
                        "realized_pnl": float(latest_pnl.realized_pnl),
                        "unrealized_pnl": float(latest_pnl.unrealized_pnl),
                        "total_pnl": float(latest_pnl.total_pnl),
                        "position_count": latest_pnl.position_count,
                        "total_market_value": float(latest_pnl.total_market_value)
                    }
                    
                return None
                
        except Exception as e:
            logger.error(f"Error getting real-time P&L for {follower_id}: {e}")
            return None

    async def stop_monitoring(self):
        """Stop P&L monitoring."""
        logger.info("Stopping P&L monitoring service")
        self.monitoring_active = False
        self.subscriptions_active = False
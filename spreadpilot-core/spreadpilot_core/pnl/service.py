"""P&L service for real-time monitoring, calculation, and commission tracking.

This service subscribes to trade fills and tick feeds, updates P&L tables
(intraday, daily, monthly), and calculates commission based on positive monthly P&L.
"""

import asyncio
import datetime
import json
from datetime import date, time
from decimal import Decimal
from typing import Any

import pytz
import redis.asyncio as redis
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.mongodb import get_mongo_db
from ..db.postgresql import get_postgres_session
from ..logging import get_logger
from ..models.pnl import (
    CommissionMonthly,
    PnLDaily,
    PnLIntraday,
    PnLMonthly,
    Quote,
    Trade,
)
from ..utils.redis_client import get_redis_client

logger = get_logger(__name__)

# Eastern timezone for rollup times
ET = pytz.timezone("US/Eastern")


class PnLService:
    """Service for P&L tracking, calculation, and rollups with commission management."""

    def __init__(self):
        """Initialize P&L service."""
        self.monitoring_active = False
        self.subscriptions_active = False

        # Track active followers for P&L calculation
        self.active_followers: set[str] = set()

        # In-memory quote cache for faster MTM calculations
        self.quote_cache: dict[str, Quote] = {}

        # Callback functions for external integrations
        self.get_follower_positions_callback = None
        self.get_market_price_callback = None
        self.subscribe_to_tick_feed_callback = None
        
        # Redis client for stream subscriptions
        self.redis_client: redis.Redis | None = None

        logger.info("Initialized P&L service")

    def set_callbacks(
        self, get_positions_fn=None, get_market_price_fn=None, subscribe_tick_fn=None
    ):
        """Set callback functions for external integrations.

        Args:
            get_positions_fn: Function to get follower positions (follower_id) -> List[Position]
            get_market_price_fn: Function to get market price for contract
            subscribe_tick_fn: Function to subscribe to tick feed for contract
        """
        self.get_follower_positions_callback = get_positions_fn
        self.get_market_price_callback = get_market_price_fn
        self.subscribe_to_tick_feed_callback = subscribe_tick_fn

    async def start_monitoring(self, shutdown_event: asyncio.Event):
        """Start P&L monitoring and rollup tasks.

        Args:
            shutdown_event: Event to signal shutdown
        """
        try:
            logger.info("Starting P&L monitoring service")
            self.monitoring_active = True
            
            # Initialize Redis client
            self.redis_client = await get_redis_client()
            if not self.redis_client:
                logger.error("Failed to connect to Redis")
                return

            # Start concurrent tasks
            tasks = [
                asyncio.create_task(self._mtm_calculation_loop(shutdown_event)),
                asyncio.create_task(self._daily_rollup_scheduler(shutdown_event)),
                asyncio.create_task(self._monthly_rollup_scheduler(shutdown_event)),
                asyncio.create_task(self._redis_stream_subscriber(shutdown_event)),
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
            if self.redis_client:
                await self.redis_client.close()

    async def record_trade_fill(self, follower_id: str, fill_data: dict[str, Any]):
        """Record a trade fill from IBKR.

        Args:
            follower_id: Follower ID
            fill_data: Dictionary containing trade fill information
                - symbol: e.g., "QQQ"
                - contract_type: "CALL" or "PUT"
                - strike: Strike price
                - expiration: Expiration date
                - trade_type: "BUY" or "SELL"
                - quantity: Number of contracts
                - price: Fill price
                - commission: Commission paid
                - order_id: Order ID
                - execution_id: Execution ID
                - trade_time: Trade timestamp
        """
        try:
            trade = Trade(
                follower_id=follower_id,
                symbol=fill_data["symbol"],
                contract_type=fill_data["contract_type"],
                strike=Decimal(str(fill_data["strike"])),
                expiration=fill_data["expiration"],
                trade_type=fill_data["trade_type"],
                quantity=fill_data["quantity"],
                price=Decimal(str(fill_data["price"])),
                commission=Decimal(str(fill_data.get("commission", 0))),
                order_id=fill_data.get("order_id"),
                execution_id=fill_data.get("execution_id"),
                trade_time=fill_data["trade_time"],
            )

            async with get_postgres_session() as session:
                session.add(trade)
                await session.commit()

            logger.info(
                f"Recorded trade fill for {follower_id}: "
                f"{fill_data['trade_type']} {fill_data['quantity']} "
                f"{fill_data['symbol']} {fill_data['strike']} {fill_data['contract_type']} "
                f"@ ${fill_data['price']}"
            )

        except Exception as e:
            logger.error(f"Error recording trade fill: {e}", exc_info=True)

    async def update_quote(self, quote_data: dict[str, Any]):
        """Update market quote for a contract.

        Args:
            quote_data: Dictionary containing quote information
                - symbol: e.g., "QQQ"
                - contract_type: "CALL", "PUT", or "STK"
                - strike: Strike price (optional for stocks)
                - expiration: Expiration date (optional for stocks)
                - bid: Bid price
                - ask: Ask price
                - last: Last trade price
                - volume: Volume
                - quote_time: Quote timestamp
        """
        try:
            quote = Quote(
                symbol=quote_data["symbol"],
                contract_type=quote_data["contract_type"],
                strike=(
                    Decimal(str(quote_data["strike"]))
                    if quote_data.get("strike")
                    else None
                ),
                expiration=quote_data.get("expiration"),
                bid=Decimal(str(quote_data["bid"])) if quote_data.get("bid") else None,
                ask=Decimal(str(quote_data["ask"])) if quote_data.get("ask") else None,
                last=(
                    Decimal(str(quote_data["last"])) if quote_data.get("last") else None
                ),
                volume=quote_data.get("volume"),
                quote_time=quote_data["quote_time"],
            )

            async with get_postgres_session() as session:
                session.add(quote)
                await session.commit()

            # Update cache for faster MTM calculations
            cache_key = self._get_quote_cache_key(quote_data)
            self.quote_cache[cache_key] = quote

        except Exception as e:
            logger.error(f"Error updating quote: {e}", exc_info=True)

    def _get_quote_cache_key(self, quote_data: dict[str, Any]) -> str:
        """Generate cache key for a quote."""
        parts = [quote_data["symbol"], quote_data["contract_type"]]
        if quote_data.get("strike"):
            parts.append(str(quote_data["strike"]))
        if quote_data.get("expiration"):
            parts.append(quote_data["expiration"].isoformat())
        return "|".join(parts)

    async def add_follower(self, follower_id: str):
        """Add a follower to active P&L tracking.

        Args:
            follower_id: Follower ID to start tracking
        """
        self.active_followers.add(follower_id)
        logger.info(f"Added follower {follower_id} to P&L tracking")

    async def remove_follower(self, follower_id: str):
        """Remove a follower from active P&L tracking.

        Args:
            follower_id: Follower ID to stop tracking
        """
        self.active_followers.discard(follower_id)
        logger.info(f"Removed follower {follower_id} from P&L tracking")

    async def _mtm_calculation_loop(self, shutdown_event: asyncio.Event):
        """Calculate mark-to-market P&L every 30 seconds."""
        try:
            while not shutdown_event.is_set() and self.monitoring_active:
                try:
                    # Only calculate during market hours
                    if self._is_market_open():
                        await self._calculate_and_store_mtm()

                    # Wait 30 seconds before next calculation
                    await asyncio.sleep(30)

                except Exception as e:
                    logger.error(f"Error in MTM calculation: {e}", exc_info=True)
                    await asyncio.sleep(10)  # Wait before retrying

        except asyncio.CancelledError:
            logger.info("MTM calculation loop cancelled")
            raise

    def _is_market_open(self) -> bool:
        """Check if US market is open."""
        now = datetime.datetime.now(ET)
        # Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
        if now.weekday() >= 5:  # Saturday or Sunday
            return False
        market_open = time(9, 30)
        market_close = time(16, 0)
        return market_open <= now.time() <= market_close

    async def _calculate_and_store_mtm(self):
        """Calculate current mark-to-market P&L for all active followers."""
        try:
            for follower_id in self.active_followers:
                try:
                    await self._calculate_follower_mtm(follower_id)
                except Exception as e:
                    logger.error(
                        f"Error calculating MTM for follower {follower_id}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error in MTM calculation: {e}")

    async def _calculate_follower_mtm(self, follower_id: str):
        """Calculate MTM P&L for a specific follower."""
        try:
            # Get current positions (using callback)
            if not self.get_follower_positions_callback:
                logger.debug("No position callback set, skipping MTM calculation")
                return

            positions = await self.get_follower_positions_callback(follower_id)
            if not positions:
                logger.debug(f"No positions for follower {follower_id}")
                return

            # Calculate realized P&L from today's trades
            realized_pnl = await self._get_realized_pnl_today(follower_id)

            # Calculate unrealized P&L from open positions
            unrealized_pnl = Decimal("0")
            total_market_value = Decimal("0")
            position_count = 0

            for position in positions:
                if position.quantity != 0:
                    position_count += 1

                    # Get current market price
                    if self.get_market_price_callback:
                        market_price = await self.get_market_price_callback(position)
                        if market_price:
                            position_value = (
                                Decimal(str(market_price))
                                * Decimal(str(abs(position.quantity)))
                                * 100
                            )
                            total_market_value += position_value

                            # Calculate unrealized P&L
                            avg_cost = Decimal(str(position.avg_cost))
                            if position.quantity > 0:  # Long position
                                unrealized = (
                                    (Decimal(str(market_price)) - avg_cost)
                                    * Decimal(str(position.quantity))
                                    * 100
                                )
                            else:  # Short position
                                unrealized = (
                                    (avg_cost - Decimal(str(market_price)))
                                    * Decimal(str(abs(position.quantity)))
                                    * 100
                                )
                            unrealized_pnl += unrealized

            # Get today's commission
            total_commission = await self._get_daily_commission(follower_id)

            # Store MTM snapshot
            await self._store_intraday_pnl(
                follower_id=follower_id,
                realized_pnl=realized_pnl,
                unrealized_pnl=unrealized_pnl,
                position_count=position_count,
                total_market_value=total_market_value,
                total_commission=total_commission,
            )

        except Exception as e:
            logger.error(f"Error calculating follower MTM: {e}")

    async def _get_realized_pnl_today(self, follower_id: str) -> Decimal:
        """Get realized P&L from today's trades."""
        try:
            today = date.today()

            async with get_postgres_session() as session:
                # Get all trades for today
                result = await session.execute(
                    select(Trade)
                    .where(
                        and_(
                            Trade.follower_id == follower_id,
                            func.date(Trade.trade_time) == today,
                        )
                    )
                    .order_by(Trade.trade_time)
                )
                trades = result.scalars().all()

                # Calculate realized P&L
                # This is simplified - in reality, you'd match trades to calculate actual P&L
                realized_pnl = Decimal("0")
                for trade in trades:
                    # For now, we'll use a simplified calculation
                    # In production, you'd match opening and closing trades
                    pass

                return realized_pnl

        except Exception as e:
            logger.error(f"Error getting realized P&L: {e}")
            return Decimal("0")

    async def _get_daily_commission(self, follower_id: str) -> Decimal:
        """Get total commission paid today."""
        try:
            today = date.today()

            async with get_postgres_session() as session:
                result = await session.execute(
                    select(func.sum(Trade.commission)).where(
                        and_(
                            Trade.follower_id == follower_id,
                            func.date(Trade.trade_time) == today,
                        )
                    )
                )
                commission = result.scalar() or Decimal("0")
                return commission

        except Exception as e:
            logger.error(f"Error getting daily commission for {follower_id}: {e}")
            return Decimal("0")

    async def _store_intraday_pnl(
        self,
        follower_id: str,
        realized_pnl: Decimal,
        unrealized_pnl: Decimal,
        position_count: int,
        total_market_value: Decimal,
        total_commission: Decimal,
    ):
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
                total_commission=total_commission,
            )

            async with get_postgres_session() as session:
                session.add(pnl_snapshot)
                await session.commit()

        except Exception as e:
            logger.error(f"Error storing intraday P&L: {e}")

    async def _redis_stream_subscriber(self, shutdown_event: asyncio.Event):
        """Subscribe to Redis streams for trade fills and quotes."""
        try:
            self.subscriptions_active = True
            logger.info("Starting Redis stream subscriptions")
            
            if not self.redis_client:
                logger.error("No Redis client available")
                return

            # Create consumer group if it doesn't exist
            try:
                await self.redis_client.xgroup_create("trade_fills", "pnl_service", id="0", mkstream=True)
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(f"Error creating consumer group for trade_fills: {e}")
            
            try:
                await self.redis_client.xgroup_create("quotes", "pnl_service", id="0", mkstream=True)
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(f"Error creating consumer group for quotes: {e}")

            while not shutdown_event.is_set() and self.subscriptions_active:
                try:
                    # Read from trade_fills stream
                    trade_messages = await self.redis_client.xreadgroup(
                        "pnl_service", "pnl_worker",
                        {"trade_fills": ">"},
                        count=10,
                        block=1000  # 1 second timeout
                    )
                    
                    for stream_name, messages in trade_messages:
                        for message_id, fields in messages:
                            try:
                                # Process trade fill
                                fill_data = json.loads(fields.get("data", "{}"))
                                follower_id = fill_data.get("follower_id")
                                if follower_id:
                                    await self.record_trade_fill(follower_id, fill_data)
                                
                                # Acknowledge message
                                await self.redis_client.xack("trade_fills", "pnl_service", message_id)
                                
                            except Exception as e:
                                logger.error(f"Error processing trade fill: {e}")

                    # Read from quotes stream
                    quote_messages = await self.redis_client.xreadgroup(
                        "pnl_service", "pnl_worker",
                        {"quotes": ">"},
                        count=10,
                        block=1000  # 1 second timeout
                    )
                    
                    for stream_name, messages in quote_messages:
                        for message_id, fields in messages:
                            try:
                                # Process quote update
                                quote_data = json.loads(fields.get("data", "{}"))
                                await self.update_quote(quote_data)
                                
                                # Acknowledge message
                                await self.redis_client.xack("quotes", "pnl_service", message_id)
                                
                            except Exception as e:
                                logger.error(f"Error processing quote: {e}")

                except redis.exceptions.ConnectionError as e:
                    logger.error(f"Redis connection error: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
                except Exception as e:
                    logger.error(f"Error in Redis stream subscription: {e}", exc_info=True)
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Redis stream subscription cancelled")
            raise
        finally:
            self.subscriptions_active = False

    async def _subscribe_to_position_quotes(self):
        """Subscribe to quotes for all active positions."""
        try:
            if not self.subscribe_to_tick_feed_callback:
                logger.debug("No tick feed subscription callback set")
                return

            # Get all unique contracts from active positions
            contracts = set()
            for follower_id in self.active_followers:
                if self.get_follower_positions_callback:
                    positions = await self.get_follower_positions_callback(follower_id)
                    for position in positions:
                        if position.quantity != 0:
                            contracts.add(
                                (
                                    position.symbol,
                                    position.contract_type,
                                    position.strike,
                                    position.expiration,
                                )
                            )

            # Subscribe to tick feed for each contract
            for contract_info in contracts:
                await self.subscribe_to_tick_feed_callback(contract_info)

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

                    if now_et.time() >= target_time and now_et.time() <= time(
                        16, 35
                    ):  # 5-minute window

                        # Check if we already ran today
                        if not await self._daily_rollup_completed_today():
                            logger.info("Starting daily P&L rollup at 16:30 ET")
                            await self._perform_daily_rollup()

                    # Check every minute
                    await asyncio.sleep(60)

                except Exception as e:
                    logger.error(f"Error in daily rollup scheduler: {e}", exc_info=True)
                    await asyncio.sleep(300)  # Wait 5 minutes before retrying

        except asyncio.CancelledError:
            logger.info("Daily rollup scheduler cancelled")
            raise

    async def _daily_rollup_completed_today(self) -> bool:
        """Check if daily rollup was already completed today."""
        try:
            today = date.today()

            async with get_postgres_session() as session:
                result = await session.execute(
                    select(PnLDaily)
                    .where(
                        and_(
                            PnLDaily.trading_date == today,
                            PnLDaily.is_finalized == True,
                        )
                    )
                    .limit(1)
                )
                return result.scalar() is not None

        except Exception as e:
            logger.error(f"Error checking daily rollup status: {e}")
            return False

    async def _perform_daily_rollup(self):
        """Perform daily P&L rollup for all followers."""
        try:
            today = date.today()

            for follower_id in self.active_followers:
                try:
                    await self._rollup_daily_pnl(follower_id, today)
                except Exception as e:
                    logger.error(
                        f"Error in daily rollup for follower {follower_id}: {e}"
                    )

            logger.info(f"Completed daily P&L rollup for {today}")

        except Exception as e:
            logger.error(f"Error in daily rollup: {e}")

    async def _rollup_daily_pnl(self, follower_id: str, trading_date: date):
        """Rollup daily P&L for a specific follower."""
        try:
            async with get_postgres_session() as session:
                # Get all intraday snapshots for today
                intraday_result = await session.execute(
                    select(PnLIntraday)
                    .where(
                        and_(
                            PnLIntraday.follower_id == follower_id,
                            PnLIntraday.trading_date == trading_date,
                        )
                    )
                    .order_by(PnLIntraday.snapshot_time)
                )
                snapshots = intraday_result.scalars().all()

                if not snapshots:
                    logger.debug(
                        f"No intraday data for follower {follower_id} on {trading_date}"
                    )
                    return

                # Get first and last snapshots
                first_snapshot = snapshots[0]
                last_snapshot = snapshots[-1]

                # Calculate daily metrics
                max_profit = max((s.total_pnl for s in snapshots), default=Decimal("0"))
                max_drawdown = min(
                    (s.total_pnl for s in snapshots), default=Decimal("0")
                )

                # Get trading activity
                trades_result = await session.execute(
                    select(Trade).where(
                        and_(
                            Trade.follower_id == follower_id,
                            func.date(Trade.trade_time) == trading_date,
                        )
                    )
                )
                trades = trades_result.scalars().all()

                trades_count = len(trades)
                total_volume = sum(t.quantity for t in trades)
                total_commission = sum(t.commission for t in trades)

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
                    rollup_time=datetime.datetime.utcnow(),
                )

                session.add(daily_pnl)
                await session.commit()

                logger.info(
                    f"Completed daily rollup for follower {follower_id}: "
                    f"total_pnl=${daily_pnl.total_pnl:.2f}, trades={trades_count}"
                )

        except Exception as e:
            logger.error(f"Error in daily rollup for {follower_id}: {e}")

    async def _monthly_rollup_scheduler(self, shutdown_event: asyncio.Event):
        """Schedule monthly rollups at 00:10 ET on the 1st of each month."""
        try:
            while not shutdown_event.is_set() and self.monitoring_active:
                try:
                    # Check if it's the 1st of the month at 00:10 ET
                    now_et = datetime.datetime.now(ET)

                    if (
                        now_et.day == 1
                        and now_et.time() >= time(0, 10)
                        and now_et.time() <= time(0, 15)
                    ):  # 5-minute window

                        # Check if we already ran this month
                        if not await self._monthly_rollup_completed():
                            logger.info(
                                "Starting monthly P&L rollup at 00:10 ET on the 1st"
                            )
                            await self._perform_monthly_rollup()

                    # Check every 5 minutes
                    await asyncio.sleep(300)

                except Exception as e:
                    logger.error(
                        f"Error in monthly rollup scheduler: {e}", exc_info=True
                    )
                    await asyncio.sleep(600)  # Wait 10 minutes before retrying

        except asyncio.CancelledError:
            logger.info("Monthly rollup scheduler cancelled")
            raise

    async def _monthly_rollup_completed(self) -> bool:
        """Check if monthly rollup was already completed."""
        try:
            # Get previous month
            now = datetime.datetime.now()
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
                            PnLMonthly.is_finalized == True,
                        )
                    )
                    .limit(1)
                )
                return result.scalar() is not None

        except Exception as e:
            logger.error(f"Error checking monthly rollup status: {e}")
            return False

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
                    logger.error(
                        f"Error in monthly rollup for follower {follower_id}: {e}"
                    )

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
                            func.extract("year", PnLDaily.trading_date) == year,
                            func.extract("month", PnLDaily.trading_date) == month,
                        )
                    )
                    .order_by(PnLDaily.trading_date)
                )
                daily_summaries = daily_result.scalars().all()

                if not daily_summaries:
                    logger.debug(
                        f"No daily data for follower {follower_id} in {year}-{month:02d}"
                    )
                    return

                # Calculate monthly metrics
                total_realized = sum(d.realized_pnl for d in daily_summaries)
                total_pnl = sum(d.total_pnl for d in daily_summaries)
                total_trades = sum(d.trades_count for d in daily_summaries)
                total_volume = sum(d.total_volume for d in daily_summaries)
                total_commission = sum(d.total_commission for d in daily_summaries)

                # Performance metrics
                best_day = max(
                    (d.total_pnl for d in daily_summaries), default=Decimal("0")
                )
                worst_day = min(
                    (d.total_pnl for d in daily_summaries), default=Decimal("0")
                )
                max_profit = max(
                    (d.max_profit for d in daily_summaries if d.max_profit),
                    default=Decimal("0"),
                )
                max_drawdown = min(
                    (d.max_drawdown for d in daily_summaries if d.max_drawdown),
                    default=Decimal("0"),
                )

                # Win/Loss statistics
                winning_days = sum(1 for d in daily_summaries if d.total_pnl > 0)
                losing_days = sum(1 for d in daily_summaries if d.total_pnl < 0)
                breakeven_days = sum(1 for d in daily_summaries if d.total_pnl == 0)

                avg_daily_pnl = (
                    total_pnl / len(daily_summaries)
                    if daily_summaries
                    else Decimal("0")
                )

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
                    rollup_time=datetime.datetime.utcnow(),
                )

                session.add(monthly_pnl)
                await session.commit()

                # Calculate monthly commission after P&L rollup
                await self._calculate_monthly_commission(
                    session, follower_id, year, month, total_pnl
                )

                logger.info(
                    f"Completed monthly rollup for follower {follower_id} {year}-{month:02d}: "
                    f"total_pnl=${monthly_pnl.total_pnl:.2f}, "
                    f"winning_days={winning_days}, losing_days={losing_days}"
                )

        except Exception as e:
            logger.error(f"Error in monthly rollup for {follower_id}: {e}")

    async def _calculate_monthly_commission(
        self,
        session: AsyncSession,
        follower_id: str,
        year: int,
        month: int,
        monthly_pnl: Decimal,
    ):
        """Calculate monthly commission based on positive P&L.

        Rule: if pnl_month > 0 => commission = pct * pnl_month, else 0

        Args:
            session: Database session
            follower_id: Follower ID
            year: Year of the month
            month: Month number
            monthly_pnl: Total P&L for the month
        """
        try:
            # Get follower details from MongoDB (IBAN, email, commission percentage)
            follower_data = await self._get_follower_data(follower_id)
            if not follower_data:
                logger.error(f"Could not retrieve follower data for {follower_id}")
                return

            # Calculate commission only if P&L is positive
            is_payable = monthly_pnl > 0
            commission_pct = (
                Decimal(str(follower_data.get("commission_pct", 20))) / 100
            )  # Convert percentage to decimal
            commission_amount = (
                commission_pct * monthly_pnl if is_payable else Decimal("0")
            )

            # Check if commission entry already exists
            existing_result = await session.execute(
                select(CommissionMonthly).where(
                    and_(
                        CommissionMonthly.follower_id == follower_id,
                        CommissionMonthly.year == year,
                        CommissionMonthly.month == month,
                    )
                )
            )
            existing_commission = existing_result.scalar()

            if existing_commission:
                # Update existing commission entry
                existing_commission.monthly_pnl = monthly_pnl
                existing_commission.commission_pct = commission_pct
                existing_commission.commission_amount = commission_amount
                existing_commission.is_payable = is_payable
                existing_commission.follower_iban = follower_data.get("iban", "")
                existing_commission.follower_email = follower_data.get("email", "")
                existing_commission.calculated_at = datetime.datetime.utcnow()
                existing_commission.updated_at = datetime.datetime.utcnow()

                logger.info(
                    f"Updated commission for follower {follower_id} {year}-{month:02d}: "
                    f"pnl=${monthly_pnl:.2f}, commission=${commission_amount:.2f}"
                )
            else:
                # Create new commission entry
                commission_entry = CommissionMonthly(
                    follower_id=follower_id,
                    year=year,
                    month=month,
                    monthly_pnl=monthly_pnl,
                    commission_pct=commission_pct,
                    commission_amount=commission_amount,
                    commission_currency="EUR",
                    follower_iban=follower_data.get("iban", ""),
                    follower_email=follower_data.get("email", ""),
                    is_payable=is_payable,
                    is_paid=False,
                )

                session.add(commission_entry)

                logger.info(
                    f"Calculated commission for follower {follower_id} {year}-{month:02d}: "
                    f"pnl=${monthly_pnl:.2f}, commission_pct={commission_pct*100:.1f}%, "
                    f"commission=${commission_amount:.2f}, payable={is_payable}"
                )

            await session.commit()

        except Exception as e:
            logger.error(f"Error calculating monthly commission for {follower_id}: {e}")
            await session.rollback()

    async def _get_follower_data(self, follower_id: str) -> dict | None:
        """Get follower data from MongoDB including IBAN and commission percentage.

        Args:
            follower_id: Follower ID

        Returns:
            Dictionary with follower data or None if not found
        """
        try:
            db = await get_mongo_db()
            follower_doc = await db.followers.find_one({"_id": follower_id})

            if follower_doc:
                return {
                    "id": follower_id,
                    "email": follower_doc.get("email", ""),
                    "iban": follower_doc.get("iban", ""),
                    "commission_pct": follower_doc.get(
                        "commission_pct", 20
                    ),  # Default 20%
                }

            return None

        except Exception as e:
            logger.error(f"Error retrieving follower data: {e}")
            return None

    async def get_current_pnl(self, follower_id: str) -> dict[str, Any]:
        """Get current P&L for a follower.

        Args:
            follower_id: Follower ID

        Returns:
            Dictionary with current P&L metrics
        """
        try:
            today = date.today()

            async with get_postgres_session() as session:
                # Get latest intraday snapshot
                latest_result = await session.execute(
                    select(PnLIntraday)
                    .where(
                        and_(
                            PnLIntraday.follower_id == follower_id,
                            PnLIntraday.trading_date == today,
                        )
                    )
                    .order_by(desc(PnLIntraday.snapshot_time))
                    .limit(1)
                )
                latest_snapshot = latest_result.scalar()

                if latest_snapshot:
                    return {
                        "follower_id": follower_id,
                        "timestamp": latest_snapshot.snapshot_time,
                        "realized_pnl": float(latest_snapshot.realized_pnl),
                        "unrealized_pnl": float(latest_snapshot.unrealized_pnl),
                        "total_pnl": float(latest_snapshot.total_pnl),
                        "position_count": latest_snapshot.position_count,
                        "total_market_value": float(latest_snapshot.total_market_value),
                    }
                else:
                    return {
                        "follower_id": follower_id,
                        "timestamp": datetime.datetime.utcnow(),
                        "realized_pnl": 0.0,
                        "unrealized_pnl": 0.0,
                        "total_pnl": 0.0,
                        "position_count": 0,
                        "total_market_value": 0.0,
                    }

        except Exception as e:
            logger.error(f"Error getting current P&L: {e}")
            return {"follower_id": follower_id, "error": str(e)}

    async def get_monthly_commission(
        self, follower_id: str, year: int, month: int
    ) -> dict[str, Any]:
        """Get monthly commission for a follower.

        Args:
            follower_id: Follower ID
            year: Year
            month: Month

        Returns:
            Dictionary with commission details
        """
        try:
            async with get_postgres_session() as session:
                result = await session.execute(
                    select(CommissionMonthly).where(
                        and_(
                            CommissionMonthly.follower_id == follower_id,
                            CommissionMonthly.year == year,
                            CommissionMonthly.month == month,
                        )
                    )
                )
                commission = result.scalar()

                if commission:
                    return {
                        "follower_id": follower_id,
                        "year": year,
                        "month": month,
                        "monthly_pnl": float(commission.monthly_pnl),
                        "commission_pct": float(
                            commission.commission_pct * 100
                        ),  # Convert to percentage
                        "commission_amount": float(commission.commission_amount),
                        "is_payable": commission.is_payable,
                        "is_paid": commission.is_paid,
                        "payment_date": (
                            commission.payment_date.isoformat()
                            if commission.payment_date
                            else None
                        ),
                        "payment_reference": commission.payment_reference,
                    }
                else:
                    return {
                        "follower_id": follower_id,
                        "year": year,
                        "month": month,
                        "monthly_pnl": 0.0,
                        "commission_pct": 0.0,
                        "commission_amount": 0.0,
                        "is_payable": False,
                        "is_paid": False,
                    }

        except Exception as e:
            logger.error(f"Error getting monthly commission: {e}")
            return {
                "follower_id": follower_id,
                "year": year,
                "month": month,
                "error": str(e),
            }

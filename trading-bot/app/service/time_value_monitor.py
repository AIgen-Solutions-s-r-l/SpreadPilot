"""Time Value Monitor for SpreadPilot trading service.

Monitors open positions and automatically closes them when time value falls below $0.10.
"""

import asyncio
import json
from enum import Enum
from typing import Any

import ib_insync
import redis.asyncio as redis
from ib_insync import Contract, MarketOrder

from spreadpilot_core.logging import get_logger
from spreadpilot_core.models.alert import AlertEvent, AlertSeverity, AlertType

logger = get_logger(__name__)


class TimeValueStatus(str, Enum):
    """Time value status enum."""

    SAFE = "SAFE"  # TV > $1.00
    RISK = "RISK"  # $0.10 < TV <= $1.00
    CRITICAL = "CRITICAL"  # TV <= $0.10


class TimeValueMonitor:
    """Monitor for tracking time value of open positions."""

    def __init__(self, service, redis_url: str = "redis://localhost:6379"):
        """Initialize the time value monitor.

        Args:
            service: Trading service instance
            redis_url: Redis connection URL
        """
        self.service = service
        self.redis_url = redis_url
        self.redis_client: redis.Redis | None = None
        self.monitoring_interval = 60  # seconds
        self.tv_threshold = 0.10  # $0.10 threshold
        self.is_running = False
        self._monitor_task: asyncio.Task | None = None

        logger.info("Initialized time value monitor")

    async def connect_redis(self):
        """Connect to Redis if not already connected."""
        if self.redis_client is None:
            self.redis_client = await redis.from_url(
                self.redis_url, decode_responses=True
            )
            logger.info("Connected to Redis for alert publishing")

    async def disconnect_redis(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Disconnected from Redis")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect_redis()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect_redis()

    async def start_monitoring(self):
        """Start the time value monitoring loop."""
        if self.is_running:
            logger.warning("Time value monitor is already running")
            return

        self.is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Started time value monitoring")

    async def stop_monitoring(self):
        """Stop the time value monitoring loop."""
        if not self.is_running:
            logger.warning("Time value monitor is not running")
            return

        self.is_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped time value monitoring")

    async def _monitor_loop(self):
        """Main monitoring loop that runs every interval."""
        await self.connect_redis()

        while self.is_running:
            try:
                await self._check_all_positions()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in time value monitor loop: {e}", exc_info=True)
                await asyncio.sleep(self.monitoring_interval)

    async def _check_all_positions(self):
        """Check time value for all open positions."""
        logger.debug("Checking time value for all positions")

        # Get all active followers
        for follower_id, follower in self.service.active_followers.items():
            try:
                await self._check_follower_positions(follower_id, follower)
            except Exception as e:
                logger.error(
                    f"Error checking positions for follower {follower_id}: {e}",
                    exc_info=True,
                )

    async def _check_follower_positions(self, follower_id: str, follower: Any):
        """Check time value for a specific follower's positions.

        Args:
            follower_id: Follower ID
            follower: Follower object
        """
        # Get IBKR client for this follower
        ibkr_client = await self.service.ibkr_manager.get_client(follower_id)
        if not ibkr_client:
            logger.warning(f"No IBKR client available for follower {follower_id}")
            return

        # Ensure connected
        if not await ibkr_client.ensure_connected():
            logger.error(f"Failed to connect to IB Gateway for follower {follower_id}")
            return

        # Get all positions from IB
        try:
            positions = ibkr_client.ib.positions()

            for position in positions:
                contract = position.contract

                # Only check QQQ options
                if contract.secType == "OPT" and contract.symbol == "QQQ":
                    await self._check_position_time_value(
                        follower_id, ibkr_client, position, contract
                    )

        except Exception as e:
            logger.error(
                f"Error getting positions for follower {follower_id}: {e}",
                exc_info=True,
            )

    async def _check_position_time_value(
        self, follower_id: str, ibkr_client: Any, position: Any, contract: Contract
    ):
        """Check time value for a specific position.

        Args:
            follower_id: Follower ID
            ibkr_client: IBKR client instance
            position: IB position object
            contract: IB contract object
        """
        try:
            # Get market price for the option
            market_price = await ibkr_client.get_market_price(contract)
            if market_price is None:
                logger.warning(
                    f"Failed to get market price for {contract.symbol} {contract.strike} {contract.right}"
                )
                return

            # Get underlying price
            underlying_contract = ib_insync.Stock("QQQ", "SMART", "USD")
            underlying_price = await ibkr_client.get_market_price(underlying_contract)
            if underlying_price is None:
                logger.warning("Failed to get underlying QQQ price")
                return

            # Calculate intrinsic value
            intrinsic_value = self._calculate_intrinsic_value(
                contract.strike, contract.right, underlying_price
            )

            # Calculate time value
            time_value = market_price - intrinsic_value

            # Determine status
            status = self._get_time_value_status(time_value)

            logger.info(
                "Position time value check",
                follower_id=follower_id,
                symbol=contract.symbol,
                strike=contract.strike,
                right=contract.right,
                position_qty=position.position,
                market_price=market_price,
                intrinsic_value=intrinsic_value,
                time_value=time_value,
                status=status,
            )

            # Publish alert based on status
            await self._publish_time_value_alert(
                follower_id, contract, position.position, time_value, status
            )

            # If critical (TV <= $0.10), close the position
            if status == TimeValueStatus.CRITICAL and position.position != 0:
                await self._close_position(
                    follower_id, ibkr_client, contract, position.position, time_value
                )

        except Exception as e:
            logger.error(
                f"Error checking time value for position: {e}",
                follower_id=follower_id,
                contract_symbol=contract.symbol,
                strike=contract.strike,
                right=contract.right,
                exc_info=True,
            )

    def _calculate_intrinsic_value(
        self, strike: float, right: str, underlying_price: float
    ) -> float:
        """Calculate intrinsic value of an option.

        Args:
            strike: Strike price
            right: Option right ("C" for call, "P" for put)
            underlying_price: Current underlying price

        Returns:
            Intrinsic value
        """
        if right == "C":  # Call option
            return max(0, underlying_price - strike)
        else:  # Put option
            return max(0, strike - underlying_price)

    def _get_time_value_status(self, time_value: float) -> TimeValueStatus:
        """Get status based on time value.

        Args:
            time_value: Time value in dollars

        Returns:
            TimeValueStatus enum
        """
        if time_value <= self.tv_threshold:
            return TimeValueStatus.CRITICAL
        elif time_value <= 1.00:
            return TimeValueStatus.RISK
        else:
            return TimeValueStatus.SAFE

    async def _publish_time_value_alert(
        self,
        follower_id: str,
        contract: Contract,
        position_qty: int,
        time_value: float,
        status: TimeValueStatus,
    ):
        """Publish time value alert to Redis.

        Args:
            follower_id: Follower ID
            contract: Option contract
            position_qty: Position quantity
            time_value: Current time value
            status: Time value status
        """
        # Map status to severity
        severity_map = {
            TimeValueStatus.SAFE: AlertSeverity.INFO,
            TimeValueStatus.RISK: AlertSeverity.WARNING,
            TimeValueStatus.CRITICAL: AlertSeverity.CRITICAL,
        }

        # Create alert event
        alert_event = AlertEvent(
            event_type=AlertType.ASSIGNMENT_DETECTED,  # Using this for time value alerts
            message=f"Time value {status} for {contract.symbol} {contract.strike}{contract.right}: ${time_value:.2f}",
            params={
                "follower_id": follower_id,
                "symbol": contract.symbol,
                "strike": contract.strike,
                "right": contract.right,
                "position_qty": position_qty,
                "time_value": time_value,
                "status": status,
                "severity": severity_map[status].value,
            },
        )

        try:
            if self.redis_client:
                alert_json = json.dumps(alert_event.model_dump(mode="json"))
                await self.redis_client.xadd("alerts", {"alert": alert_json})
                logger.debug(
                    f"Published time value alert: {status} for follower {follower_id}"
                )
        except Exception as e:
            logger.error(f"Failed to publish time value alert: {e}", exc_info=True)

    async def _close_position(
        self,
        follower_id: str,
        ibkr_client: Any,
        contract: Contract,
        position_qty: int,
        time_value: float,
    ):
        """Close a position when time value is critical.

        Args:
            follower_id: Follower ID
            ibkr_client: IBKR client instance
            contract: Option contract
            position_qty: Position quantity
            time_value: Current time value
        """
        logger.warning(
            "Closing position due to critical time value",
            follower_id=follower_id,
            symbol=contract.symbol,
            strike=contract.strike,
            right=contract.right,
            position_qty=position_qty,
            time_value=time_value,
        )

        try:
            # Create market order to close position
            # If long position (qty > 0), sell to close
            # If short position (qty < 0), buy to close
            action = "SELL" if position_qty > 0 else "BUY"
            order = MarketOrder(
                action=action, totalQuantity=abs(position_qty), transmit=True
            )

            # Place the order
            trade = ibkr_client.ib.placeOrder(contract, order)

            # Wait a bit for order to process
            await asyncio.sleep(2)

            # Check order status
            if trade.orderStatus.status == "Filled":
                logger.info(
                    "Successfully closed position",
                    follower_id=follower_id,
                    order_id=trade.order.orderId,
                    fill_price=trade.orderStatus.avgFillPrice,
                )

                # Publish success alert
                alert_event = AlertEvent(
                    event_type=AlertType.ASSIGNMENT_COMPENSATED,
                    message=f"Closed position for {contract.symbol} {contract.strike}{contract.right} due to TV <= ${self.tv_threshold}",
                    params={
                        "follower_id": follower_id,
                        "symbol": contract.symbol,
                        "strike": contract.strike,
                        "right": contract.right,
                        "position_qty": position_qty,
                        "time_value": time_value,
                        "fill_price": trade.orderStatus.avgFillPrice,
                        "order_id": trade.order.orderId,
                    },
                )

                if self.redis_client:
                    alert_json = json.dumps(alert_event.model_dump(mode="json"))
                    await self.redis_client.xadd("alerts", {"alert": alert_json})
            else:
                logger.error(
                    "Failed to close position",
                    follower_id=follower_id,
                    order_status=trade.orderStatus.status,
                    order_id=trade.order.orderId,
                )

        except Exception as e:
            logger.error(
                f"Error closing position: {e}",
                follower_id=follower_id,
                contract_symbol=contract.symbol,
                strike=contract.strike,
                right=contract.right,
                exc_info=True,
            )

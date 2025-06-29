"""Time Value Monitor Service for auto-closing spreads when TV ≤ $0.10."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

import redis.asyncio as redis
from ib_insync import IB, Contract, MarketOrder, Option, Stock
from motor.motor_asyncio import AsyncIOMotorDatabase

from spreadpilot_core.logging import get_logger
from spreadpilot_core.models.follower import Follower
from spreadpilot_core.models.position import Position, PositionState
from spreadpilot_core.models.alert import Alert, AlertType, AlertEvent, AlertSeverity

logger = get_logger(__name__)


class TimeValueMonitor:
    """Monitor spreads and auto-close when time value ≤ $0.10."""
    
    def __init__(self, service):
        """Initialize the Time Value Monitor.
        
        Args:
            service: Trading service instance
        """
        self.service = service
        self.time_value_threshold = 0.10
        self.check_interval = 60
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.redis_url = "redis://localhost:6379"
        self.redis_client: redis.Redis | None = None
        
    async def start_monitoring(self) -> None:
        """Start the time value monitoring task."""
        if self._running:
            logger.warning("Time value monitor is already running")
            return
            
        # Connect to Redis
        await self._connect_redis()
            
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(
            f"Time value monitor started (threshold: ${self.time_value_threshold}, "
            f"interval: {self.check_interval}s)"
        )
        
    async def stop_monitoring(self) -> None:
        """Stop the time value monitoring task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
        # Disconnect from Redis
        await self._disconnect_redis()
        logger.info("Time value monitor stopped")
        
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_all_positions()
            except Exception as e:
                logger.error(f"Error in time value monitor loop: {e}")
            
            # Wait for next check
            await asyncio.sleep(self.check_interval)
            
    async def _check_all_positions(self) -> None:
        """Check all open positions for time value threshold."""
        if not self.service.mongo_db:
            logger.error("MongoDB not initialized")
            return
            
        # Get all open positions
        positions_collection = self.service.mongo_db["positions"]
        cursor = positions_collection.find({
            "state": PositionState.OPEN.value,
            "position_type": "SPREAD"
        })
        
        positions = []
        async for doc in cursor:
            try:
                position = Position.model_validate(doc)
                positions.append(position)
            except Exception as e:
                logger.error(f"Failed to parse position document: {e}")
                
        if not positions:
            logger.debug("No open spread positions to monitor")
            return
            
        logger.info(f"Checking {len(positions)} open spread positions")
        
        # Check each position
        for position in positions:
            try:
                await self._check_position_time_value(position)
            except Exception as e:
                logger.error(
                    f"Error checking position {position.id} for "
                    f"follower {position.follower_id}: {e}"
                )
                
    async def _check_position_time_value(self, position: Position) -> None:
        """Check a single position's time value.
        
        Args:
            position: Position to check
        """
        # Calculate time value
        time_value = await self._calculate_time_value(position)
        
        if time_value is None:
            logger.warning(
                f"Could not calculate time value for position {position.id}"
            )
            return
            
        logger.info(
            f"Position {position.id} (follower: {position.follower_id}) - "
            f"Time Value: ${time_value:.2f}"
        )
        
        # Check if below threshold
        if time_value <= self.time_value_threshold:
            logger.warning(
                f"Position {position.id} time value ${time_value:.2f} is below "
                f"threshold ${self.time_value_threshold} - auto-closing"
            )
            
            # Send market order to close
            success = await self._close_position(position)
            
            # Publish alert
            alert_data = {
                "type": AlertType.CRITICAL.value,
                "reason": "TIME_VALUE_THRESHOLD",
                "follower_id": position.follower_id,
                "position_id": position.id,
                "time_value": time_value,
                "threshold": self.time_value_threshold,
                "action": "AUTO_CLOSE",
                "success": success,
                "timestamp": datetime.now(timezone.utc),
            }
            
            await self._publish_alert(alert_data)
            
            # Publish to Redis stream
            await self._publish_redis_alert(alert_data)
            
    async def _calculate_time_value(self, position: Position) -> Optional[float]:
        """Calculate the time value (extrinsic value) of a spread position.
        
        Time Value = Market Price - Intrinsic Value
        
        Args:
            position: Position to calculate time value for
            
        Returns:
            Time value in dollars, or None if calculation fails
        """
        try:
            # Get current market data for the spread
            spread_contract = await self._create_spread_contract(position)
            if not spread_contract:
                return None
                
            # Get IB client for the follower
            ib_client = await self.service.ibkr_manager.get_client(position.follower_id)
            if not ib_client:
                logger.error(f"No IB client available for follower {position.follower_id}")
                return None
                
            # Request market data
            ticker = ib_client.reqMktData(spread_contract, "", False, False)
            
            # Wait for data
            await asyncio.sleep(2)
            
            # Get mid price
            if ticker.bid is not None and ticker.ask is not None:
                market_price = (ticker.bid + ticker.ask) / 2
            elif ticker.last is not None:
                market_price = ticker.last
            else:
                logger.warning(f"No market data available for position {position.id}")
                ib_client.cancelMktData(spread_contract)
                return None
                
            self.ib.cancelMktData(spread_contract)
            
            # Calculate intrinsic value
            intrinsic_value = await self._calculate_intrinsic_value(position)
            
            if intrinsic_value is None:
                return None
                
            # Time value = Market price - Intrinsic value
            # For spreads, multiply by 100 (option multiplier)
            time_value = (market_price - intrinsic_value) * 100
            
            return max(0, time_value)  # Time value cannot be negative
            
        except Exception as e:
            logger.error(f"Error calculating time value: {e}")
            return None
            
    async def _calculate_intrinsic_value(self, position: Position) -> Optional[float]:
        """Calculate the intrinsic value of a spread.
        
        Args:
            position: Position to calculate intrinsic value for
            
        Returns:
            Intrinsic value per spread, or None if calculation fails
        """
        try:
            # Get IB client for the follower
            ib_client = await self.service.ibkr_manager.get_client(position.follower_id)
            if not ib_client:
                logger.error(f"No IB client available for follower {position.follower_id}")
                return None
                
            # Get underlying price
            underlying = Stock("QQQ", "SMART", "USD")
            ticker = ib_client.reqMktData(underlying, "", False, False)
            await asyncio.sleep(1)
            
            if ticker.last is not None:
                underlying_price = ticker.last
            else:
                logger.warning("Could not get underlying price for QQQ")
                ib_client.cancelMktData(underlying)
                return None
                
            self.ib.cancelMktData(underlying)
            
            # Parse position details to get strikes
            # Assuming position.symbol contains info like "QQQ 240103C450/455"
            parts = position.symbol.split()
            if len(parts) < 2:
                return None
                
            # Extract strikes from the spread notation
            spread_info = parts[1]
            if "/" not in spread_info:
                return None
                
            # Parse strikes and option type
            is_call = "C" in spread_info
            strikes_str = spread_info.replace("C", "").replace("P", "")
            strikes = strikes_str.split("/")
            
            if len(strikes) != 2:
                return None
                
            long_strike = float(strikes[0])
            short_strike = float(strikes[1])
            
            # Calculate intrinsic value based on spread type
            if position.strategy_type == "BULL_PUT":
                # Bull Put Spread (short put spread)
                # Max profit when underlying > higher strike
                # Intrinsic value = max(0, short_strike - long_strike) when ITM
                if underlying_price <= long_strike:
                    # Both puts ITM - max loss
                    intrinsic_value = short_strike - long_strike
                elif underlying_price >= short_strike:
                    # Both puts OTM - no intrinsic value
                    intrinsic_value = 0
                else:
                    # Partially ITM
                    intrinsic_value = short_strike - underlying_price
                    
            elif position.strategy_type == "BEAR_CALL":
                # Bear Call Spread (short call spread)
                # Max profit when underlying < lower strike
                # Intrinsic value = max(0, short_strike - long_strike) when ITM
                if underlying_price >= short_strike:
                    # Both calls ITM - max loss
                    intrinsic_value = short_strike - long_strike
                elif underlying_price <= long_strike:
                    # Both calls OTM - no intrinsic value
                    intrinsic_value = 0
                else:
                    # Partially ITM
                    intrinsic_value = underlying_price - long_strike
            else:
                logger.warning(f"Unknown strategy type: {position.strategy_type}")
                return None
                
            return abs(intrinsic_value)
            
        except Exception as e:
            logger.error(f"Error calculating intrinsic value: {e}")
            return None
            
    async def _create_spread_contract(self, position: Position) -> Optional[Contract]:
        """Create IB contract for the spread position.
        
        Args:
            position: Position to create contract for
            
        Returns:
            IB Contract object or None if creation fails
        """
        try:
            # Parse position symbol to extract contract details
            # Example: "QQQ 240103C450/455"
            parts = position.symbol.split()
            if len(parts) < 2:
                return None
                
            symbol = parts[0]
            spread_info = parts[1]
            
            # Extract expiry date (YYMMDD format)
            expiry = "20" + spread_info[:6]
            
            # Extract option type
            is_call = "C" in spread_info
            right = "C" if is_call else "P"
            
            # Extract strikes
            strikes_str = spread_info[6:].replace("C", "").replace("P", "")
            strikes = strikes_str.split("/")
            
            if len(strikes) != 2:
                return None
                
            long_strike = float(strikes[0])
            short_strike = float(strikes[1])
            
            # Create combo contract for the spread
            combo = Contract()
            combo.symbol = symbol
            combo.secType = "BAG"
            combo.currency = "USD"
            combo.exchange = "SMART"
            
            # Create legs
            leg1 = Option(symbol, expiry, long_strike, right, "SMART")
            leg2 = Option(symbol, expiry, short_strike, right, "SMART")
            
            # Get IB client for the follower
            ib_client = await self.service.ibkr_manager.get_client(position.follower_id)
            if not ib_client:
                logger.error(f"No IB client available for follower {position.follower_id}")
                return None
                
            # Qualify contracts
            ib_client.qualifyContracts(leg1, leg2)
            
            # Add combo legs based on strategy type
            if position.strategy_type == "BULL_PUT":
                # Bull Put: Buy low put, Sell high put
                combo.comboLegs = [
                    Contract.ComboLeg(conId=leg1.conId, ratio=1, action="BUY"),
                    Contract.ComboLeg(conId=leg2.conId, ratio=1, action="SELL"),
                ]
            elif position.strategy_type == "BEAR_CALL":
                # Bear Call: Buy high call, Sell low call
                combo.comboLegs = [
                    Contract.ComboLeg(conId=leg2.conId, ratio=1, action="BUY"),
                    Contract.ComboLeg(conId=leg1.conId, ratio=1, action="SELL"),
                ]
            else:
                return None
                
            return combo
            
        except Exception as e:
            logger.error(f"Error creating spread contract: {e}")
            return None
            
    async def _close_position(self, position: Position) -> bool:
        """Close a position with a market order.
        
        Args:
            position: Position to close
            
        Returns:
            True if order was placed successfully, False otherwise
        """
        try:
            # Create contract
            contract = await self._create_spread_contract(position)
            if not contract:
                logger.error(f"Could not create contract for position {position.id}")
                return False
                
            # Determine order action (opposite of opening trade)
            if position.strategy_type == "BULL_PUT":
                # To close Bull Put: Sell the spread (opposite of opening)
                action = "SELL"
            elif position.strategy_type == "BEAR_CALL":
                # To close Bear Call: Buy the spread (opposite of opening)
                action = "BUY"
            else:
                logger.error(f"Unknown strategy type: {position.strategy_type}")
                return False
                
            # Create market order
            order = MarketOrder(action, position.quantity)
            order.transmit = True
            
            # Get IB client for the follower
            ib_client = await self.service.ibkr_manager.get_client(position.follower_id)
            if not ib_client:
                logger.error(f"No IB client available for follower {position.follower_id}")
                return False
                
            # Place order
            trade = ib_client.placeOrder(contract, order)
            
            # Wait for order to be placed
            await asyncio.sleep(2)
            
            if trade.orderStatus.status in ["Submitted", "Filled", "PreSubmitted"]:
                logger.info(
                    f"Market order placed to close position {position.id} - "
                    f"Status: {trade.orderStatus.status}"
                )
                
                # Update position state in database
                await self._update_position_state(position, PositionState.CLOSING)
                
                return True
            else:
                logger.error(
                    f"Failed to place market order for position {position.id} - "
                    f"Status: {trade.orderStatus.status}"
                )
                return False
                
        except Exception as e:
            logger.error(f"Error closing position {position.id}: {e}")
            return False
            
    async def _update_position_state(
        self, position: Position, new_state: PositionState
    ) -> None:
        """Update position state in database.
        
        Args:
            position: Position to update
            new_state: New position state
        """
        try:
            positions_collection = self.service.mongo_db["positions"]
            await positions_collection.update_one(
                {"_id": position.id},
                {
                    "$set": {
                        "state": new_state.value,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            logger.info(
                f"Updated position {position.id} state to {new_state.value}"
            )
        except Exception as e:
            logger.error(f"Error updating position state: {e}")
            
    async def _publish_alert(self, alert_data: Dict) -> None:
        """Publish alert to database.
        
        Args:
            alert_data: Alert data dictionary
        """
        try:
            alerts_collection = self.service.mongo_db["alerts"]
            alert = Alert(
                type=alert_data["type"],
                reason=alert_data["reason"],
                follower_id=alert_data["follower_id"],
                details=alert_data,
                created_at=alert_data["timestamp"],
            )
            
            await alerts_collection.insert_one(alert.model_dump(by_alias=True))
            logger.info(
                f"Published {alert.type} alert for position {alert_data['position_id']}"
            )
        except Exception as e:
            logger.error(f"Error publishing alert: {e}")
            
    async def _connect_redis(self) -> None:
        """Connect to Redis."""
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis for alert publishing")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            
    async def _disconnect_redis(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Disconnected from Redis")
            
    async def _publish_redis_alert(self, alert_data: Dict) -> None:
        """Publish alert to Redis stream.
        
        Args:
            alert_data: Alert data dictionary
        """
        if not self.redis_client:
            logger.warning("Redis client not connected, skipping alert publish")
            return
            
        try:
            # Create AlertEvent for Redis
            alert_event = AlertEvent(
                alert_type=AlertType.ASSIGNMENT_DETECTED,
                severity=AlertSeverity.CRITICAL,
                follower_id=alert_data["follower_id"],
                timestamp=alert_data["timestamp"],
                details={
                    "position_id": alert_data["position_id"],
                    "time_value": alert_data["time_value"],
                    "threshold": alert_data["threshold"],
                    "reason": alert_data["reason"],
                    "action": alert_data["action"],
                    "success": alert_data["success"],
                },
            )
            
            # Publish to Redis stream
            await self.redis_client.xadd(
                "alerts",
                {"data": json.dumps(alert_event.model_dump(mode="json"))},
            )
            
            logger.info(
                f"Published TIME_VALUE_THRESHOLD alert to Redis for position {alert_data['position_id']}"
            )
        except Exception as e:
            logger.error(f"Error publishing alert to Redis: {e}")
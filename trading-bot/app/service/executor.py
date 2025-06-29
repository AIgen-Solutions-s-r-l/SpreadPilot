"""Order execution module with limit-ladder strategy for QQQ vertical spreads."""

import asyncio
import datetime
import json
import time
from typing import Dict, Any, Optional, Tuple

import ib_insync
from ib_insync import Order, MarketOrder, LimitOrder
import redis.asyncio as redis

from spreadpilot_core.logging import get_logger
from spreadpilot_core.ibkr.client import IBKRClient, OrderStatus
from spreadpilot_core.models.alert import Alert, AlertType, AlertSeverity, AlertEvent

logger = get_logger(__name__)


class VerticalSpreadExecutor:
    """Executes vertical spread orders with limit-ladder strategy and margin checks."""

    def __init__(self, ibkr_client: IBKRClient, redis_url: str = "redis://localhost:6379"):
        """Initialize the executor.
        
        Args:
            ibkr_client: Connected IBKR client instance
            redis_url: Redis connection URL
        """
        self.ibkr_client = ibkr_client
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        logger.info("VerticalSpreadExecutor initialized")
    
    async def connect_redis(self):
        """Connect to Redis if not already connected."""
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Connected to Redis at {self.redis_url}")
    
    async def disconnect_redis(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Disconnected from Redis")
    
    async def _publish_alert(self, alert_event: AlertEvent):
        """Publish an alert event to Redis alerts stream.
        
        Args:
            alert_event: Alert event to publish
        """
        try:
            # Ensure Redis is connected
            await self.connect_redis()
            
            # Serialize the alert event
            alert_data = alert_event.model_dump(mode="json")
            alert_json = json.dumps(alert_data)
            
            # Add to Redis stream
            await self.redis_client.xadd(
                "alerts",
                {"alert": alert_json}
            )
            
            logger.info(f"Published alert to Redis: {alert_event.event_type.value}")
        except Exception as e:
            logger.error(f"Failed to publish alert to Redis: {e}")

    async def execute_vertical_spread(
        self,
        signal: Dict[str, Any],
        follower_id: str,
        max_attempts: int = 10,
        price_increment: float = 0.01,
        min_price_threshold: float = 0.70,
        attempt_interval: int = 5,
        timeout_per_attempt: int = 5
    ) -> Dict[str, Any]:
        """Execute a vertical spread order with limit-ladder strategy.
        
        Args:
            signal: Trading signal containing strategy details
            follower_id: ID of the follower to execute for
            max_attempts: Maximum number of pricing attempts
            price_increment: Price increment per attempt (makes limit less negative)
            min_price_threshold: Minimum acceptable MID price (absolute value)
            attempt_interval: Seconds between attempts
            timeout_per_attempt: Timeout for each individual attempt
            
        Returns:
            Dict containing execution results and fill details
        """
        try:
            # Extract signal parameters
            strategy = signal.get("strategy")
            qty_per_leg = signal.get("qty_per_leg", 1)
            strike_long = signal.get("strike_long")
            strike_short = signal.get("strike_short")
            
            # Validate signal
            if not all([strategy, strike_long, strike_short]):
                return {
                    "status": OrderStatus.REJECTED,
                    "error": "Invalid signal: missing required parameters",
                    "follower_id": follower_id,
                    "signal": signal
                }
            
            logger.info(
                f"Executing vertical spread for follower {follower_id}",
                strategy=strategy,
                qty_per_leg=qty_per_leg,
                strike_long=strike_long,
                strike_short=strike_short
            )
            
            # Phase 1: Pre-trade margin check via IB API whatIf
            margin_check_result = await self._perform_whatif_margin_check(
                strategy, qty_per_leg, strike_long, strike_short, follower_id
            )
            
            if not margin_check_result["success"]:
                await self._send_alert(
                    f"Margin check failed for follower {follower_id}: {margin_check_result['error']}",
                    AlertType.NO_MARGIN,
                    params={
                        "follower_id": follower_id,
                        "error": margin_check_result['error'],
                        "margin_details": margin_check_result
                    }
                )
                return {
                    "status": OrderStatus.REJECTED,
                    "error": f"Margin check failed: {margin_check_result['error']}",
                    "follower_id": follower_id,
                    "margin_details": margin_check_result
                }
            
            # Phase 2: Get market data and calculate MID price
            mid_price_result = await self._calculate_mid_price(strategy, strike_long, strike_short)
            
            if not mid_price_result["success"]:
                return {
                    "status": OrderStatus.REJECTED,
                    "error": f"Failed to calculate MID price: {mid_price_result['error']}",
                    "follower_id": follower_id
                }
            
            mid_price = mid_price_result["mid_price"]
            
            # Phase 3: Check if MID price meets minimum threshold
            if abs(mid_price) < min_price_threshold:
                await self._send_alert(
                    f"MID price {mid_price:.3f} below threshold {min_price_threshold} for follower {follower_id}",
                    AlertType.MID_TOO_LOW,
                    params={
                        "follower_id": follower_id,
                        "mid_price": mid_price,
                        "threshold": min_price_threshold,
                        "strategy": strategy,
                        "strike_long": strike_long,
                        "strike_short": strike_short
                    }
                )
                return {
                    "status": OrderStatus.REJECTED,
                    "error": f"MID price {mid_price:.3f} below minimum threshold {min_price_threshold}",
                    "follower_id": follower_id,
                    "mid_price": mid_price,
                    "threshold": min_price_threshold
                }
            
            # Phase 4: Execute limit-ladder strategy
            execution_result = await self._execute_limit_ladder(
                strategy=strategy,
                qty_per_leg=qty_per_leg,
                strike_long=strike_long,
                strike_short=strike_short,
                initial_mid_price=mid_price,
                max_attempts=max_attempts,
                price_increment=price_increment,
                min_price_threshold=min_price_threshold,
                attempt_interval=attempt_interval,
                timeout_per_attempt=timeout_per_attempt,
                follower_id=follower_id
            )
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Error executing vertical spread for follower {follower_id}: {e}")
            await self._send_alert(
                f"Execution error for follower {follower_id}: {str(e)}",
                AlertType.GATEWAY_UNREACHABLE,  # Generic IB rejection/error
                params={
                    "follower_id": follower_id,
                    "error": str(e),
                    "signal": signal
                }
            )
            return {
                "status": OrderStatus.REJECTED,
                "error": f"Execution error: {str(e)}",
                "follower_id": follower_id
            }

    async def _perform_whatif_margin_check(
        self,
        strategy: str,
        qty_per_leg: int,
        strike_long: float,
        strike_short: float,
        follower_id: str
    ) -> Dict[str, Any]:
        """Perform IB API whatIf margin check before placing order.
        
        Args:
            strategy: Strategy type ("Long" or "Short")
            qty_per_leg: Quantity per leg
            strike_long: Long strike price
            strike_short: Short strike price
            follower_id: Follower ID for logging
            
        Returns:
            Dict with margin check results
        """
        try:
            if not await self.ibkr_client.ensure_connected():
                return {
                    "success": False,
                    "error": "Not connected to IB Gateway"
                }
            
            # Determine option rights based on strategy
            if strategy == "Long":  # Bull Put
                long_right = "P"
                short_right = "P"
            elif strategy == "Short":  # Bear Call
                long_right = "C"
                short_right = "C"
            else:
                return {
                    "success": False,
                    "error": f"Invalid strategy: {strategy}"
                }
            
            # Create contracts for whatIf check
            long_contract = self.ibkr_client._get_qqq_option_contract(strike_long, long_right)
            short_contract = self.ibkr_client._get_qqq_option_contract(strike_short, short_right)
            
            # Create combo contract for spread
            combo_contract = ib_insync.Bag("QQQ", "SMART", "USD")
            combo_contract.addLeg(long_contract, 1)  # Buy long leg
            combo_contract.addLeg(short_contract, -1)  # Sell short leg
            
            # Create a test order for whatIf check
            test_order = LimitOrder(
                action="BUY",
                totalQuantity=qty_per_leg,
                lmtPrice=1.0,  # Placeholder price for whatIf
                whatIf=True  # This makes it a whatIf order
            )
            
            # Submit whatIf order to get margin requirements
            logger.info(f"Performing whatIf margin check for follower {follower_id}")
            whatif_result = await self.ibkr_client.ib.whatIfOrderAsync(combo_contract, test_order)
            
            if not whatif_result:
                return {
                    "success": False,
                    "error": "No whatIf result returned from IB"
                }
            
            # Extract margin requirements
            init_margin = float(whatif_result.initMarginChange or 0)
            maint_margin = float(whatif_result.maintMarginChange or 0)
            equity_with_loan = float(whatif_result.equityWithLoanAfter or 0)
            
            # Get account summary for available funds
            account_summary = await self.ibkr_client.get_account_summary()
            available_funds = float(account_summary.get("AvailableFunds", 0))
            
            # Check if we have sufficient margin
            margin_sufficient = available_funds >= abs(init_margin)
            
            logger.info(
                f"WhatIf margin check for follower {follower_id}",
                init_margin=init_margin,
                maint_margin=maint_margin,
                available_funds=available_funds,
                margin_sufficient=margin_sufficient
            )
            
            return {
                "success": margin_sufficient,
                "error": None if margin_sufficient else f"Insufficient margin: need {abs(init_margin)}, have {available_funds}",
                "init_margin": init_margin,
                "maint_margin": maint_margin,
                "available_funds": available_funds,
                "equity_with_loan": equity_with_loan
            }
            
        except Exception as e:
            logger.error(f"Error in whatIf margin check for follower {follower_id}: {e}")
            return {
                "success": False,
                "error": f"WhatIf check error: {str(e)}"
            }

    async def _calculate_mid_price(
        self,
        strategy: str,
        strike_long: float,
        strike_short: float
    ) -> Dict[str, Any]:
        """Calculate the MID price for the vertical spread.
        
        Args:
            strategy: Strategy type ("Long" or "Short")
            strike_long: Long strike price
            strike_short: Short strike price
            
        Returns:
            Dict with MID price calculation results
        """
        try:
            # Determine option rights
            if strategy == "Long":  # Bull Put
                long_right = "P"
                short_right = "P"
            elif strategy == "Short":  # Bear Call
                long_right = "C"
                short_right = "C"
            else:
                return {
                    "success": False,
                    "error": f"Invalid strategy: {strategy}"
                }
            
            # Create contracts
            long_contract = self.ibkr_client._get_qqq_option_contract(strike_long, long_right)
            short_contract = self.ibkr_client._get_qqq_option_contract(strike_short, short_right)
            
            # Get market prices
            long_price = await self.ibkr_client.get_market_price(long_contract)
            short_price = await self.ibkr_client.get_market_price(short_contract)
            
            if long_price is None or short_price is None:
                return {
                    "success": False,
                    "error": f"Failed to get market prices: long={long_price}, short={short_price}"
                }
            
            # Calculate MID price (spread price)
            # For both Bull Put and Bear Call: short_price - long_price (typically negative)
            mid_price = short_price - long_price
            
            logger.info(
                f"Calculated MID price for {strategy} spread",
                long_price=long_price,
                short_price=short_price,
                mid_price=mid_price
            )
            
            return {
                "success": True,
                "mid_price": mid_price,
                "long_price": long_price,
                "short_price": short_price
            }
            
        except Exception as e:
            logger.error(f"Error calculating MID price: {e}")
            return {
                "success": False,
                "error": f"MID price calculation error: {str(e)}"
            }

    async def _execute_limit_ladder(
        self,
        strategy: str,
        qty_per_leg: int,
        strike_long: float,
        strike_short: float,
        initial_mid_price: float,
        max_attempts: int,
        price_increment: float,
        min_price_threshold: float,
        attempt_interval: int,
        timeout_per_attempt: int,
        follower_id: str
    ) -> Dict[str, Any]:
        """Execute the limit-ladder strategy.
        
        Args:
            strategy: Strategy type
            qty_per_leg: Quantity per leg
            strike_long: Long strike price
            strike_short: Short strike price
            initial_mid_price: Starting MID price
            max_attempts: Maximum attempts
            price_increment: Price increment per attempt
            min_price_threshold: Minimum price threshold
            attempt_interval: Seconds between attempts
            timeout_per_attempt: Timeout per attempt
            follower_id: Follower ID
            
        Returns:
            Dict with execution results
        """
        try:
            # Determine option rights
            if strategy == "Long":  # Bull Put
                long_right = "P"
                short_right = "P"
            else:  # Bear Call
                long_right = "C"
                short_right = "C"
            
            # Create contracts
            long_contract = self.ibkr_client._get_qqq_option_contract(strike_long, long_right)
            short_contract = self.ibkr_client._get_qqq_option_contract(strike_short, short_right)
            
            # Create combo contract for spread
            combo_contract = ib_insync.Bag("QQQ", "SMART", "USD")
            combo_contract.addLeg(long_contract, 1)
            combo_contract.addLeg(short_contract, -1)
            
            # Start with initial MID price as limit
            current_limit_price = initial_mid_price
            
            logger.info(
                f"Starting limit-ladder execution for follower {follower_id}",
                initial_limit=current_limit_price,
                max_attempts=max_attempts,
                price_increment=price_increment
            )
            
            for attempt in range(1, max_attempts + 1):
                # Check if current limit price still meets threshold
                if abs(current_limit_price) < min_price_threshold:
                    await self._send_alert(
                        f"Limit price {current_limit_price:.3f} fell below threshold {min_price_threshold} for follower {follower_id}",
                        AlertType.MID_TOO_LOW,
                        params={
                            "follower_id": follower_id,
                            "limit_price": current_limit_price,
                            "threshold": min_price_threshold,
                            "attempt": attempt,
                            "strategy": strategy
                        }
                    )
                    return {
                        "status": OrderStatus.CANCELED,
                        "error": f"Limit price {current_limit_price:.3f} below threshold",
                        "follower_id": follower_id,
                        "attempts": attempt - 1,
                        "final_limit": current_limit_price,
                        "threshold": min_price_threshold
                    }
                
                logger.info(
                    f"Attempt {attempt}/{max_attempts} for follower {follower_id}",
                    limit_price=current_limit_price
                )
                
                # Create limit order
                order = LimitOrder(
                    action="BUY",
                    totalQuantity=qty_per_leg,
                    lmtPrice=current_limit_price,
                    transmit=True
                )
                
                # Place the order
                trade = self.ibkr_client.ib.placeOrder(combo_contract, order)
                
                # Wait for fill or timeout
                start_time = time.time()
                while time.time() - start_time < timeout_per_attempt:
                    await asyncio.sleep(0.1)
                    self.ibkr_client.ib.waitOnUpdate(timeout=0.1)
                    
                    if trade.orderStatus.status in ["Filled", "Cancelled", "Inactive"]:
                        break
                
                # Check if order was filled
                if trade.orderStatus.status == "Filled":
                    logger.info(
                        f"Order filled on attempt {attempt} for follower {follower_id}",
                        order_id=trade.order.orderId,
                        fill_price=trade.orderStatus.avgFillPrice,
                        filled_qty=trade.orderStatus.filled
                    )
                    
                    return {
                        "status": OrderStatus.FILLED,
                        "trade_id": str(trade.order.orderId),
                        "fill_price": trade.orderStatus.avgFillPrice,
                        "filled_quantity": trade.orderStatus.filled,
                        "fill_time": datetime.datetime.now().isoformat(),
                        "follower_id": follower_id,
                        "attempts": attempt,
                        "final_limit": current_limit_price,
                        "strategy": strategy,
                        "strikes": {
                            "long": strike_long,
                            "short": strike_short
                        }
                    }
                
                # Check for partial fills
                if trade.orderStatus.status == "Submitted" and trade.orderStatus.filled > 0:
                    logger.info(
                        f"Partial fill on attempt {attempt} for follower {follower_id}",
                        order_id=trade.order.orderId,
                        filled=trade.orderStatus.filled,
                        remaining=trade.orderStatus.remaining
                    )
                    
                    return {
                        "status": OrderStatus.PARTIAL,
                        "trade_id": str(trade.order.orderId),
                        "fill_price": trade.orderStatus.avgFillPrice,
                        "filled_quantity": trade.orderStatus.filled,
                        "remaining_quantity": trade.orderStatus.remaining,
                        "fill_time": datetime.datetime.now().isoformat(),
                        "follower_id": follower_id,
                        "attempts": attempt,
                        "final_limit": current_limit_price
                    }
                
                # Cancel unfilled order before next attempt
                if trade.orderStatus.status not in ["Cancelled", "Inactive"]:
                    self.ibkr_client.ib.cancelOrder(order)
                    await asyncio.sleep(0.5)  # Wait for cancellation
                
                # Increment limit price for next attempt (make it less negative)
                current_limit_price += price_increment
                
                # Wait before next attempt (except on last attempt)
                if attempt < max_attempts:
                    await asyncio.sleep(attempt_interval)
            
            # All attempts exhausted
            await self._send_alert(
                f"All {max_attempts} attempts exhausted for follower {follower_id}",
                AlertType.LIMIT_REACHED,
                params={
                    "follower_id": follower_id,
                    "max_attempts": max_attempts,
                    "final_limit": current_limit_price,
                    "initial_limit": initial_mid_price,
                    "strategy": strategy,
                    "strike_long": strike_long,
                    "strike_short": strike_short
                }
            )
            
            return {
                "status": OrderStatus.REJECTED,
                "error": f"All {max_attempts} attempts exhausted",
                "follower_id": follower_id,
                "attempts": max_attempts,
                "final_limit": current_limit_price,
                "initial_limit": initial_mid_price
            }
            
        except Exception as e:
            logger.error(f"Error in limit-ladder execution for follower {follower_id}: {e}")
            return {
                "status": OrderStatus.REJECTED,
                "error": f"Limit-ladder execution error: {str(e)}",
                "follower_id": follower_id
            }

    async def _send_alert(self, message: str, alert_type: AlertType, params: Optional[Dict[str, Any]] = None):
        """Send an alert about execution events.
        
        Args:
            message: Alert message
            alert_type: Type of alert
            params: Optional parameters for the alert
        """
        try:
            # Log the alert
            logger.warning(f"ALERT [{alert_type.value}]: {message}")
            
            # Create and publish alert event to Redis
            alert_event = AlertEvent(
                event_type=alert_type,
                message=message,
                params=params or {}
            )
            
            await self._publish_alert(alert_event)
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect_redis()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect_redis()


# Convenience function that matches the task requirements
async def execute_vertical_spread(signal: Dict[str, Any], follower_id: str) -> Dict[str, Any]:
    """Execute a vertical spread order with limit-ladder strategy.
    
    This is a convenience function that creates an executor instance and executes
    the spread. In a real application, you would typically create the executor
    once and reuse it, but this function matches the task specification.
    
    Args:
        signal: Trading signal containing strategy details
        follower_id: ID of the follower to execute for
        
    Returns:
        Dict containing execution results and fill details
    """
    # This would typically get the IBKR client from a service or dependency injection
    # For now, we assume it's available through some means
    from spreadpilot_core.ibkr.gateway_manager import GatewayManager
    
    # Get IBKR client for the follower (this would be injected in real implementation)
    # For demonstration, we'll raise an error since this needs proper integration
    raise NotImplementedError(
        "execute_vertical_spread() requires integration with GatewayManager to get IBKR client. "
        "Use VerticalSpreadExecutor class directly with an IBKR client instance."
    )
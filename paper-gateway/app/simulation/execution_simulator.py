"""Order execution simulation for paper trading."""

import random
from datetime import datetime
from typing import Optional, Tuple

from ..config import get_settings
from ..models import AssetType, OrderAction, OrderStatus, OrderType, OptionType
from .commission import calculate_commission, calculate_slippage
from .market_hours import validate_trading_hours
from .price_simulator import get_price_simulator


class ExecutionSimulator:
    """Simulates order execution with realistic market conditions."""

    def __init__(self):
        """Initialize execution simulator."""
        self.settings = get_settings()
        self.price_simulator = get_price_simulator()

    def simulate_order_execution(
        self,
        symbol: str,
        action: OrderAction,
        quantity: int,
        order_type: OrderType,
        limit_price: Optional[float],
        asset_type: AssetType,
        strike: Optional[float] = None,
        expiry: Optional[str] = None,
        option_type: Optional[OptionType] = None,
    ) -> Tuple[OrderStatus, Optional[float], int, float, float, Optional[str]]:
        """Simulate order execution.

        Args:
            symbol: Symbol to trade
            action: BUY or SELL
            quantity: Number of shares/contracts
            order_type: MARKET or LIMIT
            limit_price: Limit price (for LIMIT orders)
            asset_type: STOCK or OPTION
            strike: Strike price (for options)
            expiry: Expiry date (for options)
            option_type: CALL or PUT (for options)

        Returns:
            Tuple of (status, fill_price, filled_quantity, commission, slippage, rejection_reason)
        """
        # Validate market hours
        is_valid, rejection_reason = validate_trading_hours()
        if not is_valid:
            return (
                OrderStatus.REJECTED,
                None,
                0,
                0.0,
                0.0,
                rejection_reason,
            )

        # Get current market price
        current_price = self.price_simulator.get_current_price(
            symbol=symbol,
            asset_type=asset_type,
            strike=strike,
            expiry=expiry,
            option_type=option_type,
        )

        # Get bid/ask spread
        bid, ask = self.price_simulator.get_bid_ask_spread(symbol, current_price)

        # Determine fill price based on order type
        if order_type == OrderType.MARKET:
            # Market order: execute at ask (BUY) or bid (SELL)
            fill_price = ask if action == OrderAction.BUY else bid
            status = OrderStatus.FILLED
            filled_quantity = quantity

        elif order_type == OrderType.LIMIT:
            if limit_price is None:
                return (
                    OrderStatus.REJECTED,
                    None,
                    0,
                    0.0,
                    0.0,
                    "Limit price required for LIMIT order",
                )

            # Limit order: check if executable
            if action == OrderAction.BUY:
                # BUY limit: execute if ask <= limit_price
                if ask <= limit_price:
                    fill_price = min(ask, limit_price)
                    status = OrderStatus.FILLED
                    filled_quantity = quantity
                else:
                    # Would remain pending in real system
                    # For paper trading, we'll reject non-immediate fills
                    return (
                        OrderStatus.REJECTED,
                        None,
                        0,
                        0.0,
                        0.0,
                        f"Limit price ${limit_price} below ask ${ask}",
                    )
            else:  # SELL
                # SELL limit: execute if bid >= limit_price
                if bid >= limit_price:
                    fill_price = max(bid, limit_price)
                    status = OrderStatus.FILLED
                    filled_quantity = quantity
                else:
                    return (
                        OrderStatus.REJECTED,
                        None,
                        0,
                        0.0,
                        0.0,
                        f"Limit price ${limit_price} above bid ${bid}",
                    )
        else:
            return (
                OrderStatus.REJECTED,
                None,
                0,
                0.0,
                0.0,
                f"Unsupported order type: {order_type}",
            )

        # Simulate partial fills for large orders (>500 shares)
        if quantity > 500 and random.random() < 0.1:  # 10% chance
            filled_quantity = int(quantity * random.uniform(0.7, 0.9))
            status = OrderStatus.PARTIAL

        # Calculate commission
        commission = calculate_commission(filled_quantity, fill_price, asset_type)

        # Calculate slippage
        slippage = calculate_slippage(filled_quantity, fill_price, action.value)

        # Apply slippage to fill price
        if action == OrderAction.BUY:
            fill_price += slippage / filled_quantity  # Increases cost
        else:
            fill_price -= slippage / filled_quantity  # Decreases proceeds

        fill_price = round(fill_price, 2)

        return (
            status,
            fill_price,
            filled_quantity,
            commission,
            slippage,
            None,
        )

    def can_afford_order(
        self,
        cash_balance: float,
        action: OrderAction,
        quantity: int,
        estimated_price: float,
        asset_type: AssetType,
    ) -> Tuple[bool, Optional[str]]:
        """Check if account has sufficient funds for order.

        Args:
            cash_balance: Available cash
            action: BUY or SELL
            quantity: Order quantity
            estimated_price: Estimated fill price
            asset_type: Asset type

        Returns:
            Tuple of (can_afford, rejection_reason)
        """
        if action == OrderAction.SELL:
            # Selling doesn't require cash
            # Position check happens at storage layer
            return True, None

        # Calculate required funds for BUY
        trade_value = quantity * estimated_price
        estimated_commission = calculate_commission(quantity, estimated_price, asset_type)
        estimated_slippage = calculate_slippage(quantity, estimated_price, action.value)

        required_funds = trade_value + estimated_commission + estimated_slippage

        if cash_balance < required_funds:
            return False, f"Insufficient funds: need ${required_funds:.2f}, have ${cash_balance:.2f}"

        return True, None


# Singleton instance
_execution_simulator = None


def get_execution_simulator() -> ExecutionSimulator:
    """Get execution simulator singleton."""
    global _execution_simulator
    if _execution_simulator is None:
        _execution_simulator = ExecutionSimulator()
    return _execution_simulator

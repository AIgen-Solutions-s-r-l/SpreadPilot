"""State management for paper trading account."""

import time
from datetime import datetime
from typing import Dict, List, Optional

from ..config import get_settings
from ..models import (AccountDocument, AccountInfo, AssetType, OrderAction,
                      OrderDocument, OrderStatus, PerformanceMetrics, Position,
                      PositionDocument)
from ..simulation.price_simulator import get_price_simulator
from .mongo import get_mongo_client


class StateManager:
    """Manages paper trading account state."""

    def __init__(self):
        """Initialize state manager."""
        self.settings = get_settings()
        self.mongo = get_mongo_client()
        self.price_simulator = get_price_simulator()

    async def initialize_account(self) -> AccountDocument:
        """Initialize paper trading account if not exists.

        Returns:
            Account document
        """
        account_col = self.mongo.get_account_collection()

        # Check if account exists
        existing = await account_col.find_one({})
        if existing:
            return AccountDocument(**existing)

        # Create new account
        account = AccountDocument(
            cash_balance=self.settings.paper_initial_balance,
            total_pnl=0.0,
            total_commission=0.0,
            initial_balance=self.settings.paper_initial_balance,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        await account_col.insert_one(account.dict())
        return account

    async def get_account(self) -> AccountDocument:
        """Get current account state.

        Returns:
            Account document
        """
        account_col = self.mongo.get_account_collection()
        account_data = await account_col.find_one({})

        if not account_data:
            return await self.initialize_account()

        return AccountDocument(**account_data)

    async def update_account_balance(self, delta: float, commission: float = 0.0):
        """Update account cash balance.

        Args:
            delta: Change in cash balance (negative for debit, positive for credit)
            commission: Commission paid on this transaction
        """
        account_col = self.mongo.get_account_collection()

        await account_col.update_one(
            {},
            {
                "$inc": {
                    "cash_balance": delta,
                    "total_commission": commission,
                },
                "$set": {
                    "updated_at": datetime.utcnow(),
                },
            },
        )

    async def save_order(self, order: OrderDocument):
        """Save order to database.

        Args:
            order: Order document to save
        """
        orders_col = self.mongo.get_orders_collection()
        await orders_col.insert_one(order.dict())

    async def get_order(self, order_id: str) -> Optional[OrderDocument]:
        """Get order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order document or None
        """
        orders_col = self.mongo.get_orders_collection()
        order_data = await orders_col.find_one({"order_id": order_id})

        if not order_data:
            return None

        return OrderDocument(**order_data)

    async def get_all_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
    ) -> List[OrderDocument]:
        """Get orders with optional filters.

        Args:
            symbol: Filter by symbol
            status: Filter by status
            limit: Maximum number of orders to return

        Returns:
            List of order documents
        """
        orders_col = self.mongo.get_orders_collection()

        query = {}
        if symbol:
            query["symbol"] = symbol
        if status:
            query["status"] = status.value

        cursor = orders_col.find(query).sort("timestamp", -1).limit(limit)
        orders = await cursor.to_list(length=limit)

        return [OrderDocument(**order) for order in orders]

    async def get_position(self, symbol: str) -> Optional[PositionDocument]:
        """Get position by symbol.

        Args:
            symbol: Symbol

        Returns:
            Position document or None
        """
        positions_col = self.mongo.get_positions_collection()
        position_data = await positions_col.find_one({"symbol": symbol})

        if not position_data:
            return None

        return PositionDocument(**position_data)

    async def update_position(
        self,
        symbol: str,
        action: OrderAction,
        quantity: int,
        fill_price: float,
        asset_type: AssetType,
        strike: Optional[float] = None,
        expiry: Optional[str] = None,
        option_type: Optional[str] = None,
    ):
        """Update position after order execution.

        Args:
            symbol: Symbol
            action: BUY or SELL
            quantity: Quantity filled
            fill_price: Fill price
            asset_type: Asset type
            strike: Strike price (for options)
            expiry: Expiry date (for options)
            option_type: Option type (for options)
        """
        positions_col = self.mongo.get_positions_collection()
        position = await self.get_position(symbol)

        if action == OrderAction.BUY:
            if position is None:
                # New position
                new_position = PositionDocument(
                    symbol=symbol,
                    quantity=quantity,
                    avg_cost=fill_price,
                    realized_pnl=0.0,
                    asset_type=asset_type.value,
                    strike=strike,
                    expiry=expiry,
                    option_type=option_type,
                )
                await positions_col.insert_one(new_position.dict())
            else:
                # Add to existing position
                total_cost = (position.quantity * position.avg_cost) + (quantity * fill_price)
                new_quantity = position.quantity + quantity
                new_avg_cost = total_cost / new_quantity if new_quantity > 0 else 0

                await positions_col.update_one(
                    {"symbol": symbol},
                    {
                        "$set": {
                            "quantity": new_quantity,
                            "avg_cost": new_avg_cost,
                        }
                    },
                )

        elif action == OrderAction.SELL:
            if position is None:
                # Error: selling without position
                # This should be caught earlier, but handle gracefully
                return

            # Reduce position
            new_quantity = position.quantity - quantity
            realized_pnl = (fill_price - position.avg_cost) * quantity

            if new_quantity <= 0:
                # Close position
                await positions_col.delete_one({"symbol": symbol})
            else:
                # Partial close
                await positions_col.update_one(
                    {"symbol": symbol},
                    {
                        "$set": {"quantity": new_quantity},
                        "$inc": {"realized_pnl": realized_pnl},
                    },
                )

            # Update account total PnL
            account_col = self.mongo.get_account_collection()
            await account_col.update_one(
                {},
                {"$inc": {"total_pnl": realized_pnl}},
            )

    async def get_all_positions(self) -> List[Position]:
        """Get all current positions with current prices.

        Returns:
            List of positions with market values
        """
        positions_col = self.mongo.get_positions_collection()
        cursor = positions_col.find({})
        positions_data = await cursor.to_list(length=None)

        positions = []
        for pos_data in positions_data:
            pos_doc = PositionDocument(**pos_data)

            # Get current price
            asset_type = AssetType(pos_doc.asset_type)
            current_price = self.price_simulator.get_current_price(
                symbol=pos_doc.symbol,
                asset_type=asset_type,
                strike=pos_doc.strike,
                expiry=pos_doc.expiry,
                option_type=pos_doc.option_type,
            )

            # Calculate values
            market_value = pos_doc.quantity * current_price
            unrealized_pnl = (current_price - pos_doc.avg_cost) * pos_doc.quantity

            position = Position(
                symbol=pos_doc.symbol,
                quantity=pos_doc.quantity,
                avg_cost=pos_doc.avg_cost,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                realized_pnl=pos_doc.realized_pnl,
                asset_type=asset_type,
                strike=pos_doc.strike,
                expiry=pos_doc.expiry,
                option_type=pos_doc.option_type,
            )
            positions.append(position)

        return positions

    async def get_account_info(self) -> AccountInfo:
        """Get detailed account information.

        Returns:
            Account info with current values
        """
        account = await self.get_account()
        positions = await self.get_all_positions()

        # Calculate positions value
        positions_value = sum(pos.market_value for pos in positions)
        unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)

        # Net liquidation = cash + positions value
        net_liquidation = account.cash_balance + positions_value

        # Available funds (simplified - assume no margin)
        available_funds = account.cash_balance

        # Buying power (2x for margin accounts, 1x for cash)
        buying_power = account.cash_balance

        # Daily P&L (total unrealized + realized today)
        # Simplified: just use unrealized
        daily_pnl = unrealized_pnl

        # Total P&L
        total_pnl = account.total_pnl + unrealized_pnl

        # Margin used
        margin_used = positions_value * 0.25  # Assume 25% margin requirement

        return AccountInfo(
            net_liquidation=round(net_liquidation, 2),
            available_funds=round(available_funds, 2),
            buying_power=round(buying_power, 2),
            daily_pnl=round(daily_pnl, 2),
            total_pnl=round(total_pnl, 2),
            positions_value=round(positions_value, 2),
            cash_balance=round(account.cash_balance, 2),
            margin_used=round(margin_used, 2),
        )

    async def get_performance_metrics(self) -> PerformanceMetrics:
        """Calculate performance metrics.

        Returns:
            Performance metrics
        """
        orders = await self.get_all_orders(status=OrderStatus.FILLED, limit=10000)
        account = await self.get_account()

        total_trades = len(orders)
        if total_trades == 0:
            return PerformanceMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                total_commission=account.total_commission,
                sharpe_ratio=None,
                max_drawdown=0.0,
                average_win=0.0,
                average_loss=0.0,
                profit_factor=0.0,
            )

        # Calculate wins/losses (simplified - based on buy/sell pairs)
        wins = []
        losses = []

        sell_orders = [o for o in orders if o.action == "SELL"]
        for sell_order in sell_orders:
            # Find corresponding buy orders for this symbol
            buy_orders = [
                o
                for o in orders
                if o.action == "BUY"
                and o.symbol == sell_order.symbol
                and o.timestamp < sell_order.timestamp
            ]

            if buy_orders:
                avg_buy_price = sum(o.fill_price for o in buy_orders) / len(buy_orders)
                pnl = (sell_order.fill_price - avg_buy_price) * sell_order.filled_quantity

                if pnl > 0:
                    wins.append(pnl)
                else:
                    losses.append(abs(pnl))

        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        average_win = sum(wins) / len(wins) if wins else 0.0
        average_loss = sum(losses) / len(losses) if losses else 0.0

        total_win = sum(wins)
        total_loss = sum(losses)
        profit_factor = total_win / total_loss if total_loss > 0 else 0.0

        # Max drawdown (simplified - just use current vs initial)
        account_info = await self.get_account_info()
        max_drawdown = self.settings.paper_initial_balance - account_info.net_liquidation

        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 4),
            total_pnl=round(account.total_pnl, 2),
            total_commission=round(account.total_commission, 2),
            sharpe_ratio=None,  # Would need returns time series
            max_drawdown=round(max_drawdown, 2),
            average_win=round(average_win, 2),
            average_loss=round(average_loss, 2),
            profit_factor=round(profit_factor, 2),
        )

    async def reset_account(self):
        """Reset paper trading account to initial state."""
        # Clear all collections
        await self.mongo.get_orders_collection().delete_many({})
        await self.mongo.get_positions_collection().delete_many({})
        await self.mongo.get_account_collection().delete_many({})

        # Initialize new account
        await self.initialize_account()

        # Reset price simulator
        self.price_simulator.reset_prices()

    async def set_balance(self, new_balance: float):
        """Set account balance (admin function).

        Args:
            new_balance: New cash balance
        """
        account_col = self.mongo.get_account_collection()
        await account_col.update_one(
            {},
            {
                "$set": {
                    "cash_balance": new_balance,
                    "updated_at": datetime.utcnow(),
                }
            },
        )


# Singleton instance
_state_manager = None


def get_state_manager() -> StateManager:
    """Get state manager singleton."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager

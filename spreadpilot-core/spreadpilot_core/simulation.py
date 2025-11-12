"""Simulation/Replay mode for historical data backtesting.

Replays historical market data with configurable speed for strategy validation.
"""

import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class SimulationMode(str, Enum):
    """Simulation modes."""

    BACKTEST = "backtest"  # Full historical replay
    REPLAY = "replay"  # Real-time replay at speed
    STEP = "step"  # Manual step-through


class SimulationEngine:
    """Time-travel simulation engine for backtesting."""

    def __init__(
        self,
        historical_data: List[Dict[str, Any]],
        initial_capital: float = 100000.0,
        commission_per_trade: float = 1.0,
        slippage_pct: float = 0.001,  # 0.1%
    ):
        """Initialize simulation engine.

        Args:
            historical_data: List of OHLCV data points with timestamps
            initial_capital: Starting capital
            commission_per_trade: Commission per trade
            slippage_pct: Slippage as percentage
        """
        self.data = sorted(historical_data, key=lambda x: x["timestamp"])
        self.initial_capital = initial_capital
        self.commission = commission_per_trade
        self.slippage_pct = slippage_pct

        # State
        self.current_index = 0
        self.current_time = None
        self.cash_balance = initial_capital
        self.positions = {}
        self.orders = []
        self.trades = []

        # Performance tracking
        self.equity_curve = []
        self.max_equity = initial_capital
        self.max_drawdown = 0.0

    def reset(self):
        """Reset simulation to initial state."""
        self.current_index = 0
        self.current_time = None
        self.cash_balance = self.initial_capital
        self.positions = {}
        self.orders = []
        self.trades = []
        self.equity_curve = []
        self.max_equity = self.initial_capital
        self.max_drawdown = 0.0

    def get_current_data(self) -> Optional[Dict[str, Any]]:
        """Get current data point.

        Returns:
            Current OHLCV data or None if end reached
        """
        if self.current_index >= len(self.data):
            return None
        return self.data[self.current_index]

    def step(self) -> bool:
        """Advance simulation by one data point.

        Returns:
            True if stepped, False if end reached
        """
        if self.current_index >= len(self.data):
            return False

        current = self.data[self.current_index]
        self.current_time = current["timestamp"]

        # Update positions with current prices
        self._update_positions(current)

        # Check and execute orders
        self._process_orders(current)

        # Track equity
        equity = self._calculate_equity(current)
        self.equity_curve.append(
            {
                "timestamp": self.current_time,
                "equity": equity,
                "cash": self.cash_balance,
            }
        )

        # Update drawdown
        self.max_equity = max(self.max_equity, equity)
        current_drawdown = (self.max_equity - equity) / self.max_equity
        self.max_drawdown = max(self.max_drawdown, current_drawdown)

        self.current_index += 1
        return True

    def run(
        self,
        strategy_func: Callable,
        speed: float = 1.0,
        mode: SimulationMode = SimulationMode.BACKTEST,
    ) -> Dict[str, Any]:
        """Run simulation.

        Args:
            strategy_func: Strategy function called at each step
            speed: Playback speed multiplier (1.0 = real-time)
            mode: Simulation mode

        Returns:
            Simulation results and performance metrics
        """
        self.reset()

        if mode == SimulationMode.BACKTEST:
            # Fast backtest - no delays
            while self.step():
                current = self.get_current_data()
                if current:
                    strategy_func(self, current)

        elif mode == SimulationMode.REPLAY:
            # Real-time replay with speed control
            while self.step():
                current = self.get_current_data()
                if current:
                    strategy_func(self, current)

                    # Sleep based on speed
                    if self.current_index < len(self.data) - 1:
                        next_time = datetime.fromisoformat(
                            self.data[self.current_index]["timestamp"]
                        )
                        curr_time = datetime.fromisoformat(current["timestamp"])
                        time_diff = (next_time - curr_time).total_seconds()
                        sleep_time = time_diff / speed
                        if sleep_time > 0:
                            time.sleep(sleep_time)

        elif mode == SimulationMode.STEP:
            # Manual step - strategy controls stepping
            pass

        return self.get_results()

    def place_order(
        self,
        symbol: str,
        quantity: int,
        action: str,  # "BUY" or "SELL"
        order_type: str = "MARKET",
        limit_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Place order in simulation.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: BUY or SELL
            order_type: MARKET or LIMIT
            limit_price: Limit price (for LIMIT orders)

        Returns:
            Order confirmation
        """
        order_id = f"SIM_{len(self.orders) + 1}"

        order = {
            "order_id": order_id,
            "symbol": symbol,
            "quantity": quantity,
            "action": action,
            "order_type": order_type,
            "limit_price": limit_price,
            "status": "PENDING",
            "placed_at": self.current_time,
        }

        self.orders.append(order)
        return order

    def _process_orders(self, current_data: Dict[str, Any]):
        """Process pending orders.

        Args:
            current_data: Current market data
        """
        symbol = current_data["symbol"]
        price = current_data["close"]

        for order in self.orders:
            if order["status"] != "PENDING":
                continue

            if order["symbol"] != symbol:
                continue

            # Check execution conditions
            filled = False
            fill_price = price

            if order["order_type"] == "MARKET":
                filled = True
                # Apply slippage
                if order["action"] == "BUY":
                    fill_price *= 1 + self.slippage_pct
                else:
                    fill_price *= 1 - self.slippage_pct

            elif order["order_type"] == "LIMIT":
                if order["action"] == "BUY" and price <= order["limit_price"]:
                    filled = True
                    fill_price = order["limit_price"]
                elif order["action"] == "SELL" and price >= order["limit_price"]:
                    filled = True
                    fill_price = order["limit_price"]

            if filled:
                self._execute_order(order, fill_price)

    def _execute_order(self, order: Dict[str, Any], fill_price: float):
        """Execute order.

        Args:
            order: Order to execute
            fill_price: Execution price
        """
        order["status"] = "FILLED"
        order["fill_price"] = fill_price
        order["filled_at"] = self.current_time

        # Update cash
        trade_value = fill_price * order["quantity"]
        if order["action"] == "BUY":
            self.cash_balance -= trade_value + self.commission
        else:
            self.cash_balance += trade_value - self.commission

        # Update positions
        symbol = order["symbol"]
        if symbol not in self.positions:
            self.positions[symbol] = 0

        if order["action"] == "BUY":
            self.positions[symbol] += order["quantity"]
        else:
            self.positions[symbol] -= order["quantity"]

        # Clean up zero positions
        if self.positions[symbol] == 0:
            del self.positions[symbol]

        # Record trade
        self.trades.append(
            {
                "timestamp": self.current_time,
                "symbol": symbol,
                "action": order["action"],
                "quantity": order["quantity"],
                "price": fill_price,
                "commission": self.commission,
            }
        )

    def _update_positions(self, current_data: Dict[str, Any]):
        """Update position values with current prices.

        Args:
            current_data: Current market data
        """
        # Positions updated during equity calculation
        pass

    def _calculate_equity(self, current_data: Dict[str, Any]) -> float:
        """Calculate total equity.

        Args:
            current_data: Current market data

        Returns:
            Total account equity
        """
        positions_value = 0.0
        symbol = current_data["symbol"]
        price = current_data["close"]

        if symbol in self.positions:
            positions_value += self.positions[symbol] * price

        return self.cash_balance + positions_value

    def get_results(self) -> Dict[str, Any]:
        """Get simulation results and performance metrics.

        Returns:
            Complete simulation results
        """
        # Calculate metrics
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if self._is_winning_trade(t))
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        final_equity = (
            self.equity_curve[-1]["equity"] if self.equity_curve else self.initial_capital
        )
        total_return = (final_equity - self.initial_capital) / self.initial_capital

        total_commission = sum(t["commission"] for t in self.trades)

        return {
            "simulation": {
                "start_time": self.data[0]["timestamp"] if self.data else None,
                "end_time": self.data[-1]["timestamp"] if self.data else None,
                "data_points": len(self.data),
            },
            "performance": {
                "initial_capital": self.initial_capital,
                "final_equity": final_equity,
                "total_return": total_return,
                "total_return_pct": total_return * 100,
                "max_drawdown": self.max_drawdown,
                "max_drawdown_pct": self.max_drawdown * 100,
            },
            "trading": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "win_rate_pct": win_rate * 100,
                "total_commission": total_commission,
            },
            "equity_curve": self.equity_curve,
            "trades": self.trades,
        }

    def _is_winning_trade(self, trade: Dict[str, Any]) -> bool:
        """Check if trade was profitable.

        Args:
            trade: Trade record

        Returns:
            True if winning trade
        """
        # Simplified - would need to track entry/exit pairs
        return True  # Placeholder


# Convenience functions


def run_backtest(
    historical_data: List[Dict],
    strategy_func: Callable,
    initial_capital: float = 100000.0,
) -> Dict[str, Any]:
    """Run fast backtest.

    Args:
        historical_data: Historical OHLCV data
        strategy_func: Strategy function
        initial_capital: Starting capital

    Returns:
        Backtest results
    """
    engine = SimulationEngine(historical_data, initial_capital=initial_capital)
    return engine.run(strategy_func, mode=SimulationMode.BACKTEST)


def run_replay(
    historical_data: List[Dict],
    strategy_func: Callable,
    speed: float = 10.0,
) -> Dict[str, Any]:
    """Run real-time replay at speed.

    Args:
        historical_data: Historical OHLCV data
        strategy_func: Strategy function
        speed: Playback speed multiplier

    Returns:
        Replay results
    """
    engine = SimulationEngine(historical_data)
    return engine.run(strategy_func, speed=speed, mode=SimulationMode.REPLAY)

#!/usr/bin/env python3
"""
Backtesting script for the Original EMA Crossover Strategy.

This script loads historical 5-minute bar data for SOXS and SOXL,
simulates the strategy execution using the same logic as OriginalStrategyHandler,
records all generated signals, trades, and position changes,
and calculates performance metrics.
"""

import argparse
import datetime
import logging
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import pandas as pd

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from trading_bot.app.config import ORIGINAL_EMA_STRATEGY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("backtest")


class SignalType(str, Enum):
    """Signal types for the strategy."""

    BULLISH_CROSSOVER = "BULLISH_CROSSOVER"
    BEARISH_CROSSOVER = "BEARISH_CROSSOVER"
    TRAILING_STOP = "TRAILING_STOP"
    EOD_CLOSE = "EOD_CLOSE"


@dataclass
class Trade:
    """Represents a trade in the backtest."""

    timestamp: datetime.datetime
    symbol: str
    action: str  # "BUY" or "SELL"
    quantity: float
    price: float
    order_type: str  # "MKT" or "TRAIL"
    signal_type: SignalType
    pnl: float = 0.0  # Realized P&L for this trade


@dataclass
class Position:
    """Represents a position in the backtest."""

    symbol: str
    quantity: float = 0.0
    avg_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


@dataclass
class BacktestResult:
    """Results of a backtest run."""

    trades: list[Trade] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)
    equity_curve: dict[datetime.datetime, float] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    positions: dict[str, Position] = field(default_factory=dict)


class BacktestEngine:
    """Engine for backtesting the Original EMA Strategy."""

    def __init__(self, config: dict, historical_data: dict[str, pd.DataFrame]):
        """Initialize the backtest engine."""
        self.config = config
        self.historical_data = historical_data
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self.signals: list[dict] = []
        self.equity_curve: dict[datetime.datetime, float] = {}
        self.initial_capital = config.get("dollar_amount", 10000) * len(config["symbols"])
        self.current_capital = self.initial_capital

        # Initialize positions
        for symbol in config["symbols"]:
            self.positions[symbol] = Position(symbol=symbol)

        logger.info(f"Initialized backtest engine with {len(historical_data)} symbols")
        logger.info(f"Initial capital: ${self.initial_capital:.2f}")

    def calculate_ema(self, series: pd.Series, span: int) -> pd.Series:
        """Calculates the Exponential Moving Average."""
        return series.ewm(span=span, adjust=False).mean()

    def check_bullish_crossover(self, fast_ema: pd.Series, slow_ema: pd.Series) -> bool:
        """Checks if the fast EMA crossed above the slow EMA."""
        if len(fast_ema) < 2 or len(slow_ema) < 2:
            return False
        current_fast, current_slow = fast_ema.iloc[-1], slow_ema.iloc[-1]
        prev_fast, prev_slow = fast_ema.iloc[-2], slow_ema.iloc[-2]
        return prev_fast < prev_slow and current_fast >= current_slow

    def check_bearish_crossover(self, fast_ema: pd.Series, slow_ema: pd.Series) -> bool:
        """Checks if the fast EMA crossed below the slow EMA."""
        if len(fast_ema) < 2 or len(slow_ema) < 2:
            return False
        current_fast, current_slow = fast_ema.iloc[-1], slow_ema.iloc[-1]
        prev_fast, prev_slow = fast_ema.iloc[-2], slow_ema.iloc[-2]
        return prev_fast > prev_slow and current_fast <= current_slow

    def calculate_position_size(self, price: float) -> int:
        """Calculates position size based on dollar amount and price."""
        if price <= 0:
            return 0
        dollar_amount = self.config.get("dollar_amount", 10000)
        quantity = int(dollar_amount / price)
        return max(1, quantity)  # Ensure at least 1 share

    def execute_trade(self, timestamp, symbol, action, quantity, price, order_type, signal_type):
        """Execute a trade in the backtest."""
        position = self.positions[symbol]
        pnl = 0.0

        if action == "BUY":
            if position.quantity < 0:  # Closing short position
                pnl = (position.avg_price - price) * min(abs(position.quantity), quantity)
                position.realized_pnl += pnl

                if abs(position.quantity) <= quantity:  # Fully closed
                    position.quantity = 0
                    position.avg_price = 0.0
                else:  # Partially closed
                    position.quantity += quantity
            else:  # Opening or adding to long position
                if position.quantity == 0:  # New position
                    position.avg_price = price
                    position.quantity = quantity
                else:  # Adding to position
                    # Update average price
                    total_cost = position.avg_price * position.quantity + price * quantity
                    position.quantity += quantity
                    position.avg_price = total_cost / position.quantity

        elif action == "SELL":
            if position.quantity > 0:  # Closing long position
                pnl = (price - position.avg_price) * min(position.quantity, quantity)
                position.realized_pnl += pnl

                if position.quantity <= quantity:  # Fully closed
                    position.quantity = 0
                    position.avg_price = 0.0
                else:  # Partially closed
                    position.quantity -= quantity
            else:  # Opening or adding to short position
                if position.quantity == 0:  # New position
                    position.avg_price = price
                    position.quantity = -quantity
                else:  # Adding to position
                    # Update average price
                    total_cost = position.avg_price * abs(position.quantity) + price * quantity
                    position.quantity -= quantity
                    position.avg_price = total_cost / abs(position.quantity)

        # Update capital
        self.current_capital += pnl

        # Create and record the trade
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            order_type=order_type,
            signal_type=signal_type,
            pnl=pnl,
        )
        self.trades.append(trade)

        # Log the trade
        logger.info(
            f"Trade: {timestamp} {action} {quantity} {symbol} @ ${price:.2f} "
            f"({order_type}, {signal_type.value}) - P&L: ${pnl:.2f}"
        )

        return trade

    def update_equity_curve(self, timestamp: datetime.datetime, prices: dict[str, float]):
        """Update the equity curve with current positions and prices."""
        # Calculate unrealized P&L for each position
        unrealized_pnl = 0.0
        for symbol, position in self.positions.items():
            if position.quantity != 0 and symbol in prices:
                price = prices[symbol]
                if position.quantity > 0:  # Long position
                    position.unrealized_pnl = (price - position.avg_price) * position.quantity
                else:  # Short position
                    position.unrealized_pnl = (position.avg_price - price) * abs(position.quantity)
                unrealized_pnl += position.unrealized_pnl

        # Calculate total equity
        total_equity = self.current_capital + unrealized_pnl

        # Record in equity curve
        self.equity_curve[timestamp] = total_equity

    def process_bar(
        self, timestamp, symbol, open_price, high_price, low_price, close_price, volume
    ):
        """Process a single price bar for a symbol."""
        # Get historical data for this symbol
        df = self.historical_data[symbol]

        # Ensure we have enough data
        if len(df) < self.config["slow_ema"]:
            logger.debug(f"Not enough data for {symbol} to calculate EMAs")
            return

        # Calculate EMAs
        close_prices = df["close"]
        fast_ema = self.calculate_ema(close_prices, self.config["fast_ema"])
        slow_ema = self.calculate_ema(close_prices, self.config["slow_ema"])

        # Check for crossovers
        is_bullish_crossover = self.check_bullish_crossover(fast_ema, slow_ema)
        is_bearish_crossover = self.check_bearish_crossover(fast_ema, slow_ema)

        # Get current position
        position = self.positions[symbol]
        current_position = position.quantity

        # Record signal if crossover detected
        if is_bullish_crossover:
            self.signals.append(
                {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "type": SignalType.BULLISH_CROSSOVER,
                    "fast_ema": fast_ema.iloc[-1],
                    "slow_ema": slow_ema.iloc[-1],
                    "price": close_price,
                }
            )
            logger.info(f"Signal: {timestamp} BULLISH_CROSSOVER for {symbol} @ ${close_price:.2f}")

        elif is_bearish_crossover:
            self.signals.append(
                {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "type": SignalType.BEARISH_CROSSOVER,
                    "fast_ema": fast_ema.iloc[-1],
                    "slow_ema": slow_ema.iloc[-1],
                    "price": close_price,
                }
            )
            logger.info(f"Signal: {timestamp} BEARISH_CROSSOVER for {symbol} @ ${close_price:.2f}")

        # Execute trades based on signals
        if is_bullish_crossover and current_position <= 0:
            # Close short position if exists
            if current_position < 0:
                self.execute_trade(
                    timestamp=timestamp,
                    symbol=symbol,
                    action="BUY",
                    quantity=abs(current_position),
                    price=close_price,
                    order_type="MKT",
                    signal_type=SignalType.BULLISH_CROSSOVER,
                )

            # Enter long position
            quantity = self.calculate_position_size(close_price)
            self.execute_trade(
                timestamp=timestamp,
                symbol=symbol,
                action="BUY",
                quantity=quantity,
                price=close_price,
                order_type="MKT",
                signal_type=SignalType.BULLISH_CROSSOVER,
            )

        elif is_bearish_crossover and current_position >= 0:
            # Close long position if exists
            if current_position > 0:
                self.execute_trade(
                    timestamp=timestamp,
                    symbol=symbol,
                    action="SELL",
                    quantity=current_position,
                    price=close_price,
                    order_type="MKT",
                    signal_type=SignalType.BEARISH_CROSSOVER,
                )

            # Enter short position
            quantity = self.calculate_position_size(close_price)
            self.execute_trade(
                timestamp=timestamp,
                symbol=symbol,
                action="SELL",
                quantity=quantity,
                price=close_price,
                order_type="MKT",
                signal_type=SignalType.BEARISH_CROSSOVER,
            )

        # Check for trailing stop hits (simplified simulation)
        if self.config["trailing_stop_pct"] > 0:
            trailing_pct = self.config["trailing_stop_pct"] / 100.0

            if current_position > 0:  # Long position
                stop_price = position.avg_price * (1.0 - trailing_pct)
                if low_price <= stop_price:
                    # Trailing stop hit for long position
                    self.signals.append(
                        {
                            "timestamp": timestamp,
                            "symbol": symbol,
                            "type": SignalType.TRAILING_STOP,
                            "price": stop_price,
                        }
                    )
                    logger.info(
                        f"Signal: {timestamp} TRAILING_STOP for {symbol} long @ ${stop_price:.2f}"
                    )

                    self.execute_trade(
                        timestamp=timestamp,
                        symbol=symbol,
                        action="SELL",
                        quantity=current_position,
                        price=stop_price,  # Use stop price for simulation
                        order_type="TRAIL",
                        signal_type=SignalType.TRAILING_STOP,
                    )

            elif current_position < 0:  # Short position
                stop_price = position.avg_price * (1.0 + trailing_pct)
                if high_price >= stop_price:
                    # Trailing stop hit for short position
                    self.signals.append(
                        {
                            "timestamp": timestamp,
                            "symbol": symbol,
                            "type": SignalType.TRAILING_STOP,
                            "price": stop_price,
                        }
                    )
                    logger.info(
                        f"Signal: {timestamp} TRAILING_STOP for {symbol} short @ ${stop_price:.2f}"
                    )

                    self.execute_trade(
                        timestamp=timestamp,
                        symbol=symbol,
                        action="BUY",
                        quantity=abs(current_position),
                        price=stop_price,  # Use stop price for simulation
                        order_type="TRAIL",
                        signal_type=SignalType.TRAILING_STOP,
                    )

        # Update equity curve
        self.update_equity_curve(timestamp, {symbol: close_price})

    def process_eod(self, timestamp: datetime.datetime, prices: dict[str, float]):
        """Process end-of-day logic, closing positions if configured."""
        if not self.config.get("close_at_eod", False):
            logger.info("EOD: Close at EOD is disabled")
            return

        logger.info(f"EOD: Processing end-of-day logic at {timestamp}")

        for symbol, position in self.positions.items():
            if position.quantity != 0 and symbol in prices:
                price = prices[symbol]

                # Record EOD signal
                self.signals.append(
                    {
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "type": SignalType.EOD_CLOSE,
                        "price": price,
                    }
                )
                logger.info(f"Signal: {timestamp} EOD_CLOSE for {symbol} @ ${price:.2f}")

                # Close position
                if position.quantity > 0:
                    self.execute_trade(
                        timestamp=timestamp,
                        symbol=symbol,
                        action="SELL",
                        quantity=position.quantity,
                        price=price,
                        order_type="MKT",
                        signal_type=SignalType.EOD_CLOSE,
                    )
                else:
                    self.execute_trade(
                        timestamp=timestamp,
                        symbol=symbol,
                        action="BUY",
                        quantity=abs(position.quantity),
                        price=price,
                        order_type="MKT",
                        signal_type=SignalType.EOD_CLOSE,
                    )

    def is_trading_hours(self, timestamp: datetime.datetime) -> bool:
        """Check if the timestamp is within trading hours."""
        time_str = timestamp.strftime("%H:%M:%S")
        return self.config["trading_start_time"] <= time_str <= self.config["trading_end_time"]

    def is_eod(self, timestamp: datetime.datetime) -> bool:
        """Check if the timestamp is at the end of the trading day."""
        time_str = timestamp.strftime("%H:%M:%S")
        return time_str >= self.config["trading_end_time"]

    def run(self) -> BacktestResult:
        """Run the backtest."""
        logger.info("Starting backtest run")

        # Get common date range across all symbols
        start_dates = []
        end_dates = []
        for symbol, df in self.historical_data.items():
            if not df.empty:
                start_dates.append(df.index[0])
                end_dates.append(df.index[-1])

        if not start_dates or not end_dates:
            logger.error("No data available for backtesting")
            return BacktestResult()

        start_date = max(start_dates)
        end_date = min(end_dates)

        logger.info(f"Backtest period: {start_date} to {end_date}")

        # Ensure we have enough data for EMA calculation
        for symbol, df in self.historical_data.items():
            if len(df) < self.config["slow_ema"]:
                logger.warning(f"Not enough data for {symbol} to calculate slow EMA")
                return BacktestResult()

        # Process each day
        current_date = None
        eod_processed = False

        # Create a combined DataFrame with all symbols
        combined_data = []
        for symbol, df in self.historical_data.items():
            df_copy = df.copy()
            df_copy["symbol"] = symbol
            combined_data.append(df_copy)

        if not combined_data:
            logger.error("No data available for backtesting")
            return BacktestResult()

        all_data = pd.concat(combined_data)
        all_data = all_data.sort_index()

        # Process each bar
        for timestamp, group in all_data.groupby(level=0):
            # Check if new day
            date = timestamp.date()
            if current_date != date:
                if current_date is not None and not eod_processed:
                    # Process EOD for previous day
                    eod_prices = {
                        symbol: self.historical_data[symbol]
                        .loc[self.historical_data[symbol].index.date == current_date]["close"]
                        .iloc[-1]
                        for symbol in self.config["symbols"]
                        if current_date in self.historical_data[symbol].index.date
                    }
                    self.process_eod(
                        timestamp=datetime.datetime.combine(current_date, datetime.time(16, 0, 0)),
                        prices=eod_prices,
                    )

                current_date = date
                eod_processed = False
                logger.info(f"Processing day: {current_date}")

            # Check if within trading hours
            if not self.is_trading_hours(timestamp):
                continue

            # Check if EOD
            if self.is_eod(timestamp) and not eod_processed:
                # Process EOD
                eod_prices = {row["symbol"]: row["close"] for _, row in group.iterrows()}
                self.process_eod(timestamp=timestamp, prices=eod_prices)
                eod_processed = True
                continue

            # Process each symbol's bar
            for symbol, row in group.iterrows():
                self.process_bar(
                    timestamp=timestamp,
                    symbol=row["symbol"],
                    open_price=row["open"],
                    high_price=row["high"],
                    low_price=row["low"],
                    close_price=row["close"],
                    volume=row["volume"],
                )

        # Process EOD for the last day if needed
        if current_date is not None and not eod_processed:
            eod_prices = {
                symbol: self.historical_data[symbol]
                .loc[self.historical_data[symbol].index.date == current_date]["close"]
                .iloc[-1]
                for symbol in self.config["symbols"]
                if current_date in self.historical_data[symbol].index.date
            }
            self.process_eod(
                timestamp=datetime.datetime.combine(current_date, datetime.time(16, 0, 0)),
                prices=eod_prices,
            )

        # Calculate metrics
        metrics = self.calculate_metrics()

        logger.info("Backtest run completed")

        # Return results
        return BacktestResult(
            trades=self.trades,
            signals=self.signals,
            equity_curve=self.equity_curve,
            metrics=metrics,
            positions=self.positions,
        )

    def calculate_metrics(self) -> dict[str, float]:
        """Calculate performance metrics."""
        if not self.trades:
            return {}

        # Calculate basic metrics
        total_trades = len(self.trades)
        winning_trades = sum(1 for trade in self.trades if trade.pnl > 0)
        losing_trades = sum(1 for trade in self.trades if trade.pnl < 0)

        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        total_pnl = sum(trade.pnl for trade in self.trades)
        avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0.0

        avg_win = (
            sum(trade.pnl for trade in self.trades if trade.pnl > 0) / winning_trades
            if winning_trades > 0
            else 0.0
        )
        avg_loss = (
            sum(trade.pnl for trade in self.trades if trade.pnl < 0) / losing_trades
            if losing_trades > 0
            else 0.0
        )

        profit_factor = (
            sum(trade.pnl for trade in self.trades if trade.pnl > 0)
            / abs(sum(trade.pnl for trade in self.trades if trade.pnl < 0))
            if sum(trade.pnl for trade in self.trades if trade.pnl < 0) != 0
            else float("inf")
        )

        # Calculate returns
        if self.equity_curve:
            initial_equity = list(self.equity_curve.values())[0]
            final_equity = list(self.equity_curve.values())[-1]
            total_return = (final_equity - initial_equity) / initial_equity
        else:
            total_return = 0.0

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_pnl_per_trade": avg_pnl_per_trade,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "total_return": total_return,
        }


def load_historical_data(data_dir: str) -> dict[str, pd.DataFrame]:
    """Load historical data from CSV files."""
    historical_data = {}

    for symbol in ORIGINAL_EMA_STRATEGY["symbols"]:
        file_path = os.path.join(data_dir, f"{symbol.lower()}_5min.csv")

        if not os.path.exists(file_path):
            logger.warning(f"Historical data file not found: {file_path}")
            continue

        try:
            # Load data from CSV
            df = pd.read_csv(file_path)

            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Set timestamp as index
            df.set_index("timestamp", inplace=True)

            # Sort by timestamp
            df.sort_index(inplace=True)

            # Store in dictionary
            historical_data[symbol] = df

            logger.info(f"Loaded {len(df)} bars for {symbol}")

        except Exception as e:
            logger.error(f"Error loading historical data for {symbol}: {e}")

    return historical_data


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Backtest the Original EMA Strategy")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Directory containing historical data CSV files",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Directory to save backtest reports",
    )
    args = parser.parse_args()

    # Load historical data
    historical_data = load_historical_data(args.data_dir)

    if not historical_data:
        logger.error("No historical data loaded, cannot run backtest")
        return

    # Create backtest engine
    engine = BacktestEngine(ORIGINAL_EMA_STRATEGY, historical_data)

    # Run backtest
    result = engine.run()

    # Generate report
    if result.trades:
        logger.info(f"Backtest completed with {len(result.trades)} trades")
        logger.info(f"Total P&L: ${result.metrics.get('total_pnl', 0):.2f}")
        logger.info(f"Win rate: {result.metrics.get('win_rate', 0) * 100:.2f}%")
        logger.info(f"Profit factor: {result.metrics.get('profit_factor', 0):.2f}")
        logger.info(f"Total return: {result.metrics.get('total_return', 0) * 100:.2f}%")
    else:
        logger.warning("Backtest completed with no trades")


if __name__ == "__main__":
    main()

# Simulation/Replay Mode

Backtest strategies and replay historical data with configurable speed for strategy validation and optimization.

## Quick Start

```python
from spreadpilot_core.simulation import run_backtest
from spreadpilot_core.test_data_generator import generate_test_prices

# Generate historical data
prices = generate_test_prices("QQQ", days=30)

# Define strategy
def my_strategy(engine, current_data):
    # Example: Buy on price dips
    if current_data["close"] < 375:
        engine.place_order("QQQ", 100, "BUY")
    elif "QQQ" in engine.positions and current_data["close"] > 385:
        engine.place_order("QQQ", 100, "SELL")

# Run backtest
results = run_backtest(prices, my_strategy, initial_capital=100000)

print(f"Total Return: {results['performance']['total_return_pct']:.2f}%")
print(f"Win Rate: {results['trading']['win_rate_pct']:.2f}%")
print(f"Max Drawdown: {results['performance']['max_drawdown_pct']:.2f}%")
```

## Modes

### 1. Backtest Mode (Fast)

Full historical replay without delays:

```python
from spreadpilot_core.simulation import SimulationEngine, SimulationMode

engine = SimulationEngine(historical_data, initial_capital=100000)
results = engine.run(strategy_func, mode=SimulationMode.BACKTEST)
```

### 2. Replay Mode (Real-time)

Real-time replay at configurable speed:

```python
from spreadpilot_core.simulation import run_replay

# 10x speed (1 minute = 6 seconds)
results = run_replay(historical_data, strategy_func, speed=10.0)

# 100x speed (very fast)
results = run_replay(historical_data, strategy_func, speed=100.0)
```

### 3. Step Mode (Manual)

Manual step-through for debugging:

```python
engine = SimulationEngine(historical_data)

while engine.step():
    current = engine.get_current_data()
    strategy_func(engine, current)

    # Pause for inspection
    input("Press Enter to continue...")
```

## Strategy Function

Strategy functions receive engine and current data:

```python
def strategy(engine, current_data):
    """Strategy implementation.

    Args:
        engine: SimulationEngine instance
        current_data: Current OHLCV data point
    """
    symbol = current_data["symbol"]
    price = current_data["close"]

    # Access engine state
    cash = engine.cash_balance
    positions = engine.positions

    # Place orders
    if should_buy(price):
        engine.place_order(symbol, 100, "BUY")

    if should_sell(price) and symbol in positions:
        engine.place_order(symbol, 100, "SELL")
```

## Results

```json
{
  "simulation": {
    "start_time": "2024-01-01T09:30:00",
    "end_time": "2024-01-30T16:00:00",
    "data_points": 11700
  },
  "performance": {
    "initial_capital": 100000.0,
    "final_equity": 105250.0,
    "total_return": 0.0525,
    "total_return_pct": 5.25,
    "max_drawdown": 0.0325,
    "max_drawdown_pct": 3.25
  },
  "trading": {
    "total_trades": 45,
    "winning_trades": 28,
    "losing_trades": 17,
    "win_rate": 0.622,
    "win_rate_pct": 62.2,
    "total_commission": 45.0
  },
  "equity_curve": [...],
  "trades": [...]
}
```

## Features

✅ **Time-Travel**: Step through historical data
✅ **Configurable Speed**: 1x to 100x replay
✅ **Realistic Execution**: Slippage + commission
✅ **Performance Metrics**: Return, drawdown, win rate
✅ **Equity Curve**: Track portfolio value over time
✅ **Order Types**: Market and limit orders

## Configuration

```python
engine = SimulationEngine(
    historical_data=prices,
    initial_capital=100000.0,    # Starting cash
    commission_per_trade=1.0,    # Commission per trade
    slippage_pct=0.001,          # 0.1% slippage
)
```

## Integration with Test Data Generator

```python
from spreadpilot_core.test_data_generator import TestDataGenerator, ScenarioType
from spreadpilot_core.simulation import run_backtest

# Generate crash scenario
generator = TestDataGenerator()
crash_data = generator.generate_price_history("SPY", days=5, volatility=0.05)

# Test strategy under crash
results = run_backtest(crash_data, my_strategy)
print(f"Crash Performance: {results['performance']['total_return_pct']:.2f}%")
```

## Use Cases

- **Backtest strategies** on historical data
- **Parameter optimization** (test different settings)
- **Risk assessment** (crash scenarios, volatility)
- **Strategy comparison** (A/B testing)
- **Regression testing** (ensure no degradation)

## Limitations

- Simplified P&L calculation (no cost basis tracking)
- No multi-symbol position tracking yet
- No Greeks simulation for options
- No corporate actions (splits, dividends)
- Market impact not fully modeled

**Status**: Framework complete, advanced features planned.

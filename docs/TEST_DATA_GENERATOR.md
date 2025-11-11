# Test Data Generator

Generate realistic market data and trading scenarios for testing, development, and training.

## Quick Start

```python
from spreadpilot_core.test_data_generator import (
    TestDataGenerator,
    ScenarioType,
    generate_test_prices,
    generate_scenario,
)

# Generate price history
prices = generate_test_prices("QQQ", days=30)

# Generate specific scenario
winning_trade = generate_scenario(ScenarioType.WINNING_TRADE, "QQQ")

# Generate all fixtures
from spreadpilot_core.test_data_generator import generate_all_fixtures
generate_all_fixtures("tests/fixtures")
```

## Scenario Types

- `WINNING_TRADE` - Profitable vertical spread
- `LOSING_TRADE` - Unprofitable trade
- `ASSIGNMENT` - Option assignment
- `EARLY_CLOSE` - 50% profit target hit
- `MARKET_CRASH` - 10-25% drop
- `GAP_UP` / `GAP_DOWN` - Overnight gaps
- `LOW_LIQUIDITY` - Wide spreads, thin book
- `HIGH_VOLATILITY` - Volatile price action
- `SIDEWAYS_MARKET` - Choppy, mean-reverting

## Usage

### Price History

```python
generator = TestDataGenerator()

# 30 days of 1-minute data
prices = generator.generate_price_history(
    symbol="QQQ",
    days=30,
    interval_minutes=1,
    volatility=0.02,  # 2% daily
)

# Export to CSV
generator.export_to_csv(prices, "prices_QQQ.csv")
```

### Trade Scenarios

```python
# Winning trade
scenario = generator.generate_trade_scenario(
    ScenarioType.WINNING_TRADE,
    symbol="QQQ"
)
# {
#   "scenario_type": "winning_trade",
#   "entry_price": 1.05,
#   "exit_price": 0.25,
#   "pnl": 80.00,
#   "net_pnl": 77.40
# }

# Market crash
crash = generator.generate_trade_scenario(
    ScenarioType.MARKET_CRASH,
    symbol="SPY"
)
# {
#   "scenario_type": "market_crash",
#   "pre_crash_price": 450.00,
#   "crash_low": 360.00,
#   "crash_magnitude_pct": 20.0,
#   "price_path": [450, 445, 440, ...]
# }
```

### Test Fixtures

```python
# Generate 10 scenarios per type
fixtures = generator.generate_test_fixtures(num_scenarios=10)

# Export all
generator.export_to_json(fixtures, "fixtures/scenarios.json")

# Use in tests
import pytest

@pytest.fixture
def winning_trade_data():
    return generate_scenario(ScenarioType.WINNING_TRADE)

def test_pnl_calculation(winning_trade_data):
    pnl = calculate_pnl(winning_trade_data)
    assert pnl > 0
```

## Features

✅ **Realistic Prices**: GBM-based price simulation
✅ **Edge Cases**: Crashes, gaps, low liquidity
✅ **Reproducible**: Seed-based generation
✅ **Multiple Formats**: JSON, CSV export
✅ **Pre-built Scenarios**: 10 common scenarios
✅ **Customizable**: Adjust volatility, duration, etc.

## CLI Tool (Planned)

```bash
# Generate fixtures
python -m spreadpilot_core.test_data_generator \
  --output tests/fixtures \
  --scenarios 10 \
  --seed 42

# Generate price data
python -m spreadpilot_core.test_data_generator \
  --mode prices \
  --symbol QQQ \
  --days 30 \
  --output prices.csv
```

**Status**: Framework complete, CLI planned for future.

# Vertical Spreads on QQQ Strategy Implementation

## Overview

This document describes the implementation of the Vertical Spreads on QQQ trading strategy in the SpreadPilot platform. The strategy replaces the previous EMA Crossover Strategy with a more sophisticated options trading approach.

## Strategy Description

The Vertical Spreads on QQQ strategy is designed to:

1. Monitor Google Sheets for trading signals at 9:27 AM NY Time
2. Execute Bull Put Spreads for "Long" signals and Bear Call Spreads for "Short" signals
3. Use a sophisticated limit order placement strategy with price improvement logic
4. Monitor Time Value of open positions and close them when Time Value < $0.10

## Implementation Components

### 1. Google Sheets Integration

The strategy uses the existing `GoogleSheetsClient` class to connect to Google Sheets and fetch trading signals. The client is configured to:

- Connect to a specified Google Sheet URL
- Parse signals containing:
  - "QQQ" in the "Ticker" cell
  - "Long" or "Short" in the "Strategy" cell
  - Quantity per leg
  - Strike prices for both legs

### 2. Options Contract Creation

The strategy creates options contracts for vertical spreads:

- For "Long" signals (Bull Put Spreads):
  - Buy a put option at a lower strike price
  - Sell a put option at a higher strike price
  - Both options have the same expiration date (0DTE - same day expiration)

- For "Short" signals (Bear Call Spreads):
  - Buy a call option at a higher strike price
  - Sell a call option at a lower strike price
  - Both options have the same expiration date (0DTE - same day expiration)

### 3. Limit Order Logic

The strategy implements a sophisticated limit order placement strategy:

1. Pre-trade funds check to ensure sufficient margin
2. MID price calculation (midpoint between bid and ask prices)
3. Minimum premium check ($0.70 threshold)
4. Limit order placement at the calculated MID price
5. "Chasing logic" that decreases the price by $0.01 every 5 seconds if the order is not filled
6. The process continues until the order is filled or the price falls below the $0.70 minimum threshold

### 4. Time Value Monitoring

The strategy continuously monitors the Time Value of open positions:

1. Time Value is calculated as the option price minus its intrinsic value
2. Positions are checked every minute
3. If Time Value falls below $0.10, the position is automatically closed using a Market Order

## Code Structure

### Main Components

1. **VerticalSpreadsStrategyHandler** (`trading-bot/app/service/vertical_spreads_strategy_handler.py`):
   - Main class implementing the strategy logic
   - Manages its own IBKR connection and state
   - Monitors Google Sheets for signals
   - Processes signals and places orders
   - Monitors Time Value of open positions

2. **Configuration** (`trading-bot/app/config.py`):
   - `VERTICAL_SPREADS_STRATEGY` configuration dictionary
   - Contains parameters like signal time, price thresholds, and timeouts

3. **Integration with TradingService** (`trading-bot/app/service/base.py`):
   - The `TradingService` class initializes and runs the strategy handler
   - Provides access to shared services like alert management and MongoDB

### Key Methods

1. `initialize()`: Connects to IBKR and fetches initial positions
2. `run()`: Main execution loop that monitors for signals and Time Value
3. `_process_signal()`: Processes a trading signal from Google Sheets
4. `_place_vertical_spread()`: Places a vertical spread order with chasing logic
5. `_monitor_time_value()`: Monitors Time Value of open positions
6. `_calculate_time_value()`: Calculates Time Value for an option position
7. `_close_position()`: Closes a position using a Market Order

## Testing

The implementation includes both unit tests and integration tests:

1. **Unit Tests** (`trading-bot/tests/unit/service/test_vertical_spreads_strategy_handler.py`):
   - Test individual methods of the `VerticalSpreadsStrategyHandler` class
   - Mock dependencies to isolate the code being tested

2. **Integration Tests** (`trading-bot/tests/integration/test_vertical_spreads_strategy.py`):
   - Test the interaction between the strategy handler and other components
   - Verify that signals are processed correctly
   - Verify that Time Value monitoring works correctly

## Configuration

The strategy is configured in `trading-bot/app/config.py`:

```python
VERTICAL_SPREADS_STRATEGY = {
    "enabled": True,
    "ibkr_secret_ref": "ibkr_vertical_spreads_strategy",  # For dedicated credentials
    "symbol": "QQQ",
    "signal_time": "09:27:00",  # NY Time to check for signals
    "max_attempts": 10,  # Maximum number of attempts for limit orders
    "price_increment": 0.01,  # Price increment for each attempt
    "min_price": 0.70,  # Minimum price threshold for vertical spreads
    "timeout_seconds": 5,  # Timeout in seconds for each attempt
    "time_value_threshold": 0.10,  # Time Value threshold for closing positions
    "time_value_check_interval": 60  # Check Time Value every 60 seconds
}
```

## Deployment

To deploy the Vertical Spreads strategy:

1. Ensure the `VERTICAL_SPREADS_STRATEGY` configuration is enabled in `config.py`
2. Disable the `ORIGINAL_EMA_STRATEGY` configuration if not needed
3. Ensure the Google Sheets API key and URL are correctly configured
4. Start the trading bot service

## Monitoring and Alerts

The strategy sends alerts for significant events:

1. When a vertical spread order is filled
2. When a position is closed due to Time Value falling below the threshold

Alerts are sent through the existing alert management system, which can deliver notifications via:
- Telegram
- Email
- Dashboard notifications

## Future Enhancements

Potential future enhancements to the strategy:

1. Dynamic strike price selection based on market conditions
2. More sophisticated Time Value monitoring with multiple thresholds
3. Integration with market data feeds for real-time pricing
4. Machine learning models for signal generation
5. Risk management improvements with position sizing based on account value
# Order Execution Documentation

## Overview

The SpreadPilot Order Execution system provides advanced limit-ladder execution strategies for QQQ vertical spreads with comprehensive pre-trade risk management and dynamic pricing algorithms.

## VerticalSpreadExecutor

The `VerticalSpreadExecutor` class implements sophisticated order execution logic that maximizes fill rates while maintaining risk controls.

### Key Features

- **Pre-trade Margin Validation**: Uses IB API `whatIf` orders to validate margin requirements before execution
- **Dynamic Pricing Strategy**: Limit-ladder approach that incrementally improves pricing to achieve fills
- **Risk Controls**: Automatic rejection when spread pricing falls below profitability thresholds
- **Comprehensive Alerting**: Real-time notifications for execution events and risk conditions
- **Multi-Strategy Support**: Handles both Bull Put (Long) and Bear Call (Short) vertical spreads

## Execution Algorithm

### Phase 1: Pre-trade Validation

```python
# Margin check using IB whatIf API
whatif_result = await ib.whatIfOrderAsync(combo_contract, test_order)
margin_required = float(whatif_result.initMarginChange)
available_funds = float(account_summary["AvailableFunds"])

if available_funds < margin_required:
    # Reject execution and alert
```

### Phase 2: Market Data Analysis

```python
# Calculate spread MID price
long_price = await get_market_price(long_contract)
short_price = await get_market_price(short_contract)
mid_price = short_price - long_price  # Spread premium
```

### Phase 3: Threshold Validation

```python
# Skip execution if MID < 0.70 (insufficient premium)
if abs(mid_price) < 0.70:
    await send_alert("MID price below threshold")
    return {"status": "REJECTED", "reason": "Insufficient premium"}
```

### Phase 4: Limit-Ladder Execution

```python
# Start at MID price, increment by 0.01 every 5 seconds
current_limit = mid_price
for attempt in range(max_attempts):
    order = LimitOrder(action="BUY", totalQuantity=qty, lmtPrice=current_limit)
    trade = ib.placeOrder(combo_contract, order)
    
    # Wait for fill or timeout (5 seconds)
    if await wait_for_fill(trade, timeout=5):
        return {"status": "FILLED", "fill_price": trade.avgFillPrice}
    
    # Cancel and increment price
    ib.cancelOrder(order)
    current_limit += 0.01  # Make limit less negative (better price)
    
    # Check threshold again
    if abs(current_limit) < 0.70:
        break
```

## Usage Examples

### Basic Usage

```python
from trading_bot.app.service.executor import VerticalSpreadExecutor

# Initialize with IBKR client
executor = VerticalSpreadExecutor(ibkr_client)

# Define trading signal
signal = {
    "strategy": "Long",  # Bull Put spread
    "qty_per_leg": 1,
    "strike_long": 380.0,
    "strike_short": 385.0
}

# Execute the spread
result = await executor.execute_vertical_spread(signal, "follower-123")

if result["status"] == "FILLED":
    print(f"Order filled at {result['fill_price']}")
else:
    print(f"Execution failed: {result['error']}")
```

### Configuration Parameters

```python
result = await executor.execute_vertical_spread(
    signal=signal,
    follower_id="follower-123",
    max_attempts=10,           # Maximum pricing attempts
    price_increment=0.01,      # Price improvement per attempt
    min_price_threshold=0.70,  # Minimum acceptable premium
    attempt_interval=5,        # Seconds between attempts
    timeout_per_attempt=5      # Timeout for each order attempt
)
```

## Response Format

### Successful Execution

```json
{
    "status": "FILLED",
    "trade_id": "12345",
    "fill_price": 0.75,
    "filled_quantity": 1,
    "fill_time": "2025-06-27T19:45:30.123456",
    "follower_id": "follower-123",
    "attempts": 3,
    "final_limit": 0.77,
    "strategy": "Long",
    "strikes": {
        "long": 380.0,
        "short": 385.0
    }
}
```

### Partial Fill

```json
{
    "status": "PARTIAL",
    "trade_id": "12346",
    "fill_price": 0.75,
    "filled_quantity": 1,
    "remaining_quantity": 1,
    "fill_time": "2025-06-27T19:45:30.123456",
    "follower_id": "follower-123",
    "attempts": 2,
    "final_limit": 0.76
}
```

### Rejected Execution

```json
{
    "status": "REJECTED",
    "error": "MID price 0.65 below minimum threshold 0.70",
    "follower_id": "follower-123",
    "mid_price": 0.65,
    "threshold": 0.70
}
```

### Margin Check Failure

```json
{
    "status": "REJECTED",
    "error": "Margin check failed: Insufficient margin: need 1500.0, have 1000.0",
    "follower_id": "follower-123",
    "margin_details": {
        "success": false,
        "init_margin": 1500.0,
        "available_funds": 1000.0,
        "equity_with_loan": 8500.0
    }
}
```

## Strategy Types

### Bull Put Spreads (Long Strategy)

- **Long leg**: Lower strike put (buy)
- **Short leg**: Higher strike put (sell)
- **Market outlook**: Bullish (expect price to stay above short strike)
- **Premium**: Collected (credit spread)

```python
signal = {
    "strategy": "Long",
    "strike_long": 380.0,   # Lower strike (buy)
    "strike_short": 385.0,  # Higher strike (sell)
    "qty_per_leg": 1
}
```

### Bear Call Spreads (Short Strategy)

- **Long leg**: Higher strike call (buy)
- **Short leg**: Lower strike call (sell)
- **Market outlook**: Bearish (expect price to stay below short strike)
- **Premium**: Collected (credit spread)

```python
signal = {
    "strategy": "Short",
    "strike_long": 390.0,   # Higher strike (buy)
    "strike_short": 385.0,  # Lower strike (sell)
    "qty_per_leg": 1
}
```

## Risk Management

### Pre-trade Checks

1. **Margin Validation**: IB `whatIf` API confirms sufficient buying power
2. **Premium Threshold**: Ensures minimum 0.70 spread premium
3. **Strike Validation**: Verifies correct strike relationships for strategy type
4. **Market Data**: Confirms valid option prices before execution

### During Execution

1. **Timeout Controls**: Each order attempt limited to 5 seconds
2. **Price Limits**: Stops attempting when premium falls below threshold
3. **Order Cancellation**: Automatically cancels unfilled orders
4. **Alert Generation**: Notifies on all significant events

### Post-execution

1. **Fill Validation**: Confirms order fill status and pricing
2. **Position Tracking**: Updates internal position records
3. **Performance Logging**: Records execution metrics
4. **Error Reporting**: Detailed error information for failures

## Integration with Gateway Manager

The executor integrates seamlessly with the Gateway Manager for multi-follower support:

```python
# Get dedicated IBKR client for follower
ib_client = await gateway_manager.get_client(follower_id)

# Create executor instance
executor = VerticalSpreadExecutor(ib_client)

# Execute trade with isolated connection
result = await executor.execute_vertical_spread(signal, follower_id)
```

## Error Handling

### Connection Issues

```python
try:
    result = await executor.execute_vertical_spread(signal, follower_id)
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    # Automatic retry or failover logic
```

### Market Data Issues

```python
if not long_price or not short_price:
    return {
        "status": "REJECTED",
        "error": "Failed to get market prices",
        "details": {"long_price": long_price, "short_price": short_price}
    }
```

### Validation Errors

```python
if not all([strategy, strike_long, strike_short]):
    return {
        "status": "REJECTED",
        "error": "Invalid signal: missing required parameters"
    }
```

## Performance Metrics

### Execution Statistics

- **Fill Rate**: Percentage of orders successfully filled
- **Average Attempts**: Mean number of attempts required for fills
- **Time to Fill**: Average execution time for successful orders
- **Price Improvement**: Amount of price enhancement achieved

### Monitoring

```python
# Performance tracking
logger.info(
    "Execution completed",
    follower_id=follower_id,
    attempts=attempts,
    fill_price=fill_price,
    execution_time=execution_time
)
```

## Testing

### Unit Tests

The executor includes comprehensive unit tests covering:

- Successful execution scenarios
- Margin check failures
- Price threshold violations
- Partial fills and timeouts
- Exception handling
- Both Bull Put and Bear Call strategies

### Mock Testing

```python
# Mock IB client for testing
mock_client = MagicMock(spec=IBKRClient)
mock_client.ib.whatIfOrderAsync = AsyncMock(return_value=mock_whatif_result)

# Test execution
executor = VerticalSpreadExecutor(mock_client)
result = await executor.execute_vertical_spread(test_signal, "test-follower")
```

### Integration Testing

Tests with actual IB Gateway connections in paper trading mode to validate:

- Real market data integration
- Actual order placement and fills
- Margin calculation accuracy
- Network timeout handling

## Configuration

### Environment Variables

```bash
# Execution parameters
EXECUTOR_MAX_ATTEMPTS=10
EXECUTOR_PRICE_INCREMENT=0.01
EXECUTOR_MIN_THRESHOLD=0.70
EXECUTOR_ATTEMPT_INTERVAL=5
EXECUTOR_ORDER_TIMEOUT=5
```

### Runtime Configuration

```python
executor_config = {
    "max_attempts": 10,
    "price_increment": 0.01,
    "min_price_threshold": 0.70,
    "attempt_interval": 5,
    "timeout_per_attempt": 5
}
```

## Troubleshooting

### Common Issues

#### "Margin check failed"
- **Cause**: Insufficient buying power in account
- **Solution**: Increase account funding or reduce position size

#### "MID price below threshold"
- **Cause**: Spread premium too low for profitable execution
- **Solution**: Wait for better market conditions or adjust strategy

#### "All attempts exhausted"
- **Cause**: Market conditions preventing fills at acceptable prices
- **Solution**: Review max_attempts and price_increment settings

#### "Connection failed"
- **Cause**: IBGateway connectivity issues
- **Solution**: Check Gateway Manager status and restart if needed

### Debug Information

Enable detailed logging for troubleshooting:

```python
import logging
logging.getLogger("trading_bot.app.service.executor").setLevel(logging.DEBUG)
```

This provides detailed execution flow information including:
- Market price calculations
- Order placement attempts
- Price increment progression
- Timeout and cancellation events
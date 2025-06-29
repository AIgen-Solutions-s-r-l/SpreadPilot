# Executor Alert Publishing

The `VerticalSpreadExecutor` in `service/executor.py` publishes alerts to Redis stream for various execution failures.

## Alert Types

### NO_MARGIN
Published when pre-trade margin check fails via IB API whatIf.

**Trigger Conditions:**
- Insufficient available funds
- whatIf check returns error

**Alert Parameters:**
- `follower_id`: Affected follower
- `error`: Error message
- `margin_details`: whatIf results including init_margin, maint_margin, available_funds

### MID_TOO_LOW  
Published when spread MID price falls below minimum threshold (default 0.70).

**Trigger Conditions:**
- Initial MID price < min_price_threshold
- During ladder execution if adjusted price < threshold

**Alert Parameters:**
- `follower_id`: Affected follower
- `mid_price`: Calculated MID price
- `threshold`: Minimum price threshold
- `strategy`: Trading strategy (Long/Short)
- `strike_long`: Long strike price
- `strike_short`: Short strike price

### LIMIT_REACHED
Published when all limit-ladder attempts are exhausted without fill.

**Trigger Conditions:**
- max_attempts reached without order fill
- All orders timeout or remain unfilled

**Alert Parameters:**
- `follower_id`: Affected follower
- `max_attempts`: Number of attempts made
- `final_limit`: Final limit price attempted
- `initial_limit`: Starting limit price
- `strategy`: Trading strategy

### GATEWAY_UNREACHABLE
Published for general IB Gateway errors and connection issues.

**Trigger Conditions:**
- IB Gateway connection failure
- Unexpected execution exceptions

**Alert Parameters:**
- `follower_id`: Affected follower
- `error`: Error message
- `signal`: Original trading signal

## Redis Integration

Alerts are published to Redis stream `alerts` using the following flow:

1. `_send_alert()` creates AlertEvent with appropriate type and parameters
2. `_publish_alert()` serializes and publishes to Redis stream
3. Alert router service subscribes to stream and routes to Telegram/Email

## Testing

Comprehensive unit tests in `test_executor_redis_alerts.py` verify:
- Each alert type is published correctly
- Alert parameters are properly formatted
- Redis connection handling works correctly
- Context manager properly manages connections
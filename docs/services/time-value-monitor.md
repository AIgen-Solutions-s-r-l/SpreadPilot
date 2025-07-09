# ⏱️ Time-Value Monitor Service

> 🚀 **Automated risk management service** that monitors option positions and auto-closes them when time value falls below critical thresholds

## Overview

The Time-Value Monitor is an integrated component of the Trading Bot service that continuously monitors all open option positions. It calculates the time value (extrinsic value) of each position and automatically closes positions when the time value drops to $0.10 or below, protecting traders from rapid time decay near expiration.

## How It Works

### Time Value Calculation

```
Time Value = Option Market Price - Intrinsic Value

Where:
- Call Intrinsic Value = max(0, Underlying Price - Strike Price)
- Put Intrinsic Value = max(0, Strike Price - Underlying Price)
```

### Status Levels

| Status | Time Value Range | Action | Redis Key |
|--------|-----------------|--------|-----------|
| 🟢 **SAFE** | > $1.00 | Monitor only | `tv:{follower_id}` |
| 🟡 **RISK** | $0.10 < TV ≤ $1.00 | Alert + Monitor | `tv:{follower_id}` |
| 🔴 **CRITICAL** | ≤ $0.10 | Alert + Auto-close | `tv:{follower_id}` |

### Monitoring Schedule

- **Frequency**: Every 60 seconds
- **Timezone**: US/Eastern (NYSE timezone)
- **Scheduler**: APScheduler with interval trigger

## Architecture

### Integration with Trading Bot

```python
# In trading-bot/app/service/base.py
self.time_value_monitor = TimeValueMonitor(self)

# Started automatically in the main service loop
time_value_monitor_task = asyncio.create_task(
    self.time_value_monitor.start_monitoring()
)
```

### Redis State Management

The monitor publishes real-time status updates to Redis:

```json
// Key: tv:{follower_id}
{
  "status": "RISK",
  "time_value": 0.45,
  "timestamp": 1234567890
}
```

Keys expire after 5 minutes to prevent stale data.

### Alert Events

When positions enter RISK or CRITICAL status, the monitor publishes AlertEvent messages to the Redis `alerts` stream:

```python
AlertEvent(
    event_type=AlertType.LIMIT_REACHED,  # For CRITICAL
    message="Position QQQ 450P has critical time value $0.08 <= $0.10. Closing position.",
    params={
        "follower_id": "follower123",
        "symbol": "QQQ",
        "strike": 450.0,
        "right": "P",
        "time_value": 0.08
    }
)
```

## Auto-Close Logic

When a position reaches CRITICAL status (TV ≤ $0.10):

1. **Generate Market Order**:
   - Long positions (qty > 0): SELL to close
   - Short positions (qty < 0): BUY to close

2. **Execute Order**:
   - Places market order via IB Gateway
   - Waits for fill confirmation

3. **Publish Success Alert**:
   - Confirms position closure
   - Reports fill price

## Configuration

### Environment Variables

```bash
# Redis connection (required)
REDIS_URL=redis://redis:6379

# Monitoring interval (optional, default: 60)
TIME_VALUE_MONITOR_INTERVAL=60

# Time value threshold (optional, default: 0.10)
TIME_VALUE_THRESHOLD=0.10
```

### Docker Compose

The Time-Value Monitor runs within the Trading Bot container:

```yaml
trading-bot:
  environment:
    - REDIS_URL=redis://redis:6379
  depends_on:
    - redis
    - mongodb
```

## Monitoring & Observability

### Logs

```
INFO: Started time value monitoring with 60s interval
INFO: Position time value check - follower_id=f123, symbol=QQQ, strike=450, right=P, time_value=0.08, status=CRITICAL
WARNING: Closing position due to critical time value - follower_id=f123, time_value=0.08
INFO: Successfully closed position - order_id=12345, fill_price=0.07
```

### Metrics

- Positions monitored per cycle
- Auto-close orders executed
- Alert events published
- Processing time per follower

## Testing

### Unit Tests

```bash
# Run time-value monitor tests
pytest trading-bot/tests/unit/service/test_time_value_monitor.py -v
```

### Test Coverage

- ✅ Intrinsic value calculation (calls/puts)
- ✅ Status determination (SAFE/RISK/CRITICAL)
- ✅ Redis state updates with expiration
- ✅ Alert event publishing
- ✅ Auto-close order generation
- ✅ Scheduler timezone configuration
- ✅ Error handling and recovery

### Integration Testing

```python
# Test with fake Redis and mocked IB client
async def test_monitoring_loop():
    monitor = TimeValueMonitor(service)
    await monitor.start_monitoring()
    
    # Verify scheduler is running
    assert monitor.is_running
    assert monitor.scheduler.timezone == pytz.timezone('US/Eastern')
```

## Best Practices

1. **Position Size Limits**: Monitor respects existing position limits
2. **Market Hours**: Continues monitoring during extended hours
3. **Connection Resilience**: Handles IB Gateway disconnections gracefully
4. **Alert Deduplication**: Prevents duplicate alerts for same position
5. **Order Validation**: Verifies order fills before confirming closure

## Troubleshooting

### Common Issues

1. **No positions detected**:
   - Check IB Gateway connection
   - Verify follower is enabled
   - Ensure positions exist in account

2. **Orders not filling**:
   - Check market hours
   - Verify sufficient liquidity
   - Review order rejection reasons

3. **Redis connection errors**:
   - Verify Redis is running
   - Check network connectivity
   - Review Redis logs

### Debug Mode

Enable debug logging:

```python
logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)
```

## Future Enhancements

- [ ] Configurable thresholds per follower
- [ ] Historical time value tracking
- [ ] Machine learning for optimal close timing
- [ ] Multi-leg spread support
- [ ] Custom alert channels per follower
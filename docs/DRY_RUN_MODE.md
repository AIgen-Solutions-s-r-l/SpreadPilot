# Dry-Run Mode

Dry-Run Mode allows you to simulate all SpreadPilot operations without actually executing them. Perfect for validation, testing, training, and compliance auditing.

## Overview

**Dry-Run Mode** intercepts operations at execution time and:
- Logs what would have been done
- Returns mock/simulated values
- Collects detailed operation reports
- Continues normal flow without side effects

**Supported Operations**:
- Trading (order placement, position management)
- Database (inserts, updates, deletes)
- Email (alerts, reports)
- Notifications (Telegram, webhooks)
- External API calls

---

## Quick Start

### Enable Dry-Run Mode

**Environment Variable**:
```bash
# Enable globally
DRY_RUN_MODE=true

# Start services
docker-compose up -d
```

**Programmatic**:
```python
from spreadpilot_core.dry_run import DryRunConfig

# Enable dry-run mode
DryRunConfig.enable()

# Check if enabled
if DryRunConfig.is_enabled():
    print("Running in dry-run mode")

# Disable
DryRunConfig.disable()
```

### Example Output

When dry-run mode is enabled:

```
[DRY-RUN] TRADE: place_order - Would execute with args: {'symbol': 'QQQ', 'quantity': 100, 'action': 'BUY'}
[DRY-RUN] DATABASE: save_order - Would execute with args: {'order_id': 'ORD_123', 'status': 'FILLED'}
[DRY-RUN] EMAIL: send_alert - Would execute with args: {'to': 'admin@example.com', 'subject': 'Order Filled'}
[DRY-RUN] NOTIFICATION: send_telegram - Would execute with args: {'message': 'Position opened: QQQ'}
```

---

## Usage

### Decorator-Based

**Basic Decorator**:
```python
from spreadpilot_core.dry_run import dry_run

@dry_run("trade", return_value={"order_id": "DRY_123", "status": "DRY_RUN"})
def place_order(symbol: str, quantity: int):
    """Place order via IBKR."""
    # Real implementation
    return ibkr_client.place_order(symbol, quantity)

# When dry-run enabled: logs operation, returns mock value
# When dry-run disabled: executes normally
result = place_order("QQQ", 100)
```

**Specialized Decorators**:
```python
from spreadpilot_core.dry_run import (
    dry_run_trade,
    dry_run_database,
    dry_run_email,
    dry_run_notification,
)

@dry_run_trade()
def place_vertical_spread(symbol, strike, expiry):
    return ibkr.place_spread_order(symbol, strike, expiry)

@dry_run_database()
def save_position(position_data):
    return db.positions.insert_one(position_data)

@dry_run_email()
def send_daily_report(recipient, report_data):
    return email.send(recipient, "Daily Report", report_data)

@dry_run_notification()
def send_telegram_alert(message):
    return telegram_bot.send_message(chat_id, message)
```

**Async Decorators**:
```python
from spreadpilot_core.dry_run import dry_run_async, dry_run_database_async

@dry_run_database_async()
async def save_order(order_data):
    await db.orders.insert_one(order_data)

@dry_run_async("api_call", return_value={"success": True})
async def call_external_api(endpoint, data):
    async with httpx.AsyncClient() as client:
        return await client.post(endpoint, json=data)
```

### Context Manager

**Temporary Dry-Run**:
```python
from spreadpilot_core.dry_run import dry_run_context

# Normal execution
place_order("QQQ", 50)  # Actually executes

# Temporary dry-run
with dry_run_context():
    place_order("QQQ", 100)  # Simulated
    send_email("test@example.com", "Alert")  # Simulated

# Back to normal
place_order("SPY", 25)  # Actually executes
```

**Testing Scenarios**:
```python
from spreadpilot_core.dry_run import DryRunConfig, dry_run_context

# Test disaster recovery
with dry_run_context():
    # Simulate recovery procedures
    for position in stuck_positions:
        close_position(position)

    # Check what would happen
    report = DryRunConfig.get_report()
    print(f"Would close {report['total_operations']} positions")
```

---

## Configuration

### Environment Variables

```bash
# Enable dry-run mode globally
DRY_RUN_MODE=true

# Disable operation logging (silent dry-run)
DRY_RUN_LOG_OPERATIONS=false

# Disable report collection (no memory overhead)
DRY_RUN_COLLECT_REPORTS=false
```

### Trading Bot Configuration

**trading-bot/app/config.py** (example integration):
```python
class Settings(BaseSettings):
    # Dry-run mode
    dry_run_mode: bool = Field(
        default=False,
        env="DRY_RUN_MODE",
        description="Enable dry-run mode (simulate operations)",
    )

    # ... other settings
```

**Initialization** (trading-bot/app/main.py):
```python
from spreadpilot_core.dry_run import DryRunConfig
from app.config import get_settings

settings = get_settings()

if settings.dry_run_mode:
    DryRunConfig.enable()
    logger.warning("🔵 DRY-RUN MODE ENABLED - Operations will be simulated")
```

---

## Reports

### Get Operations Report

```python
from spreadpilot_core.dry_run import DryRunConfig

# Enable and run operations
DryRunConfig.enable()

place_order("QQQ", 100)
save_to_db({"data": "value"})
send_email("admin@example.com", "Alert")

# Get report
report = DryRunConfig.get_report()

print(f"Total operations: {report['total_operations']}")
print(f"By type: {report['operations_by_type']}")
# Output:
# Total operations: 3
# By type: {'trade': 1, 'database': 1, 'email': 1}

# Get detailed operations log
for op in report['operations']:
    print(f"{op['type']}: {op['function']} at {op['timestamp']}")
```

### Report Structure

```json
{
  "total_operations": 5,
  "operations_by_type": {
    "trade": 2,
    "database": 2,
    "email": 1
  },
  "operations": [
    {
      "type": "trade",
      "function": "trading_bot.service.ibkr.place_order",
      "timestamp": "2024-01-15T14:30:00.123Z",
      "arguments": {
        "symbol": "QQQ",
        "quantity": 100,
        "action": "BUY"
      }
    },
    {
      "type": "database",
      "function": "trading_bot.service.orders.save_order",
      "timestamp": "2024-01-15T14:30:00.456Z",
      "arguments": {
        "order_id": "ORD_123",
        "status": "FILLED"
      }
    }
  ],
  "generated_at": "2024-01-15T14:35:00.000Z"
}
```

### Clear Report

```python
# Clear operations log
DryRunConfig.clear_operations_log()
```

---

## Use Cases

### 1. Configuration Validation

**Test new configuration before going live**:
```python
from spreadpilot_core.dry_run import dry_run_context

# Load new config
new_config = load_config("production.yaml")

with dry_run_context():
    # Test all operations with new config
    trading_bot.run_strategy()

    # Review what would happen
    report = DryRunConfig.get_report()
    if report['total_operations'] > 0:
        print("✅ Configuration valid")
        # Apply for real
        apply_config(new_config)
```

### 2. Strategy Testing

**Validate strategy logic without executing trades**:
```python
DryRunConfig.enable()

# Run strategy for full day
start_time = datetime.now().replace(hour=9, minute=30)
end_time = datetime.now().replace(hour=16, minute=0)

strategy.backtest(start_time, end_time)

# Analyze results
report = DryRunConfig.get_report()
trades = [op for op in report['operations'] if op['type'] == 'trade']
print(f"Strategy would place {len(trades)} trades")
```

### 3. Disaster Recovery Testing

**Test recovery procedures safely**:
```python
with dry_run_context():
    # Simulate recovery
    for position in get_stuck_positions():
        emergency_close_position(position)

    for order in get_failed_orders():
        retry_order(order)

    # Review impact
    report = DryRunConfig.get_report()
    print(f"Recovery would perform {report['total_operations']} operations")
```

### 4. Training & Demonstrations

**Demo system without real operations**:
```python
# Training mode
DryRunConfig.enable()

# Show features to new user
demo_place_order("QQQ", 100)
demo_close_position("QQQ")
demo_send_alert("Position closed")

# All operations simulated
```

### 5. Compliance Auditing

**Record what would happen for audit trail**:
```python
DryRunConfig.enable()

# Run compliance check
compliance_bot.validate_all_positions()

# Export audit trail
report = DryRunConfig.get_report()
with open("audit_trail.json", "w") as f:
    json.dump(report, f, indent=2)
```

---

## Integration Examples

### Trading Bot

**trading-bot/app/service/ibkr.py**:
```python
from spreadpilot_core.dry_run import dry_run_trade

class IBKRService:
    @dry_run_trade()
    def place_order(self, symbol: str, quantity: int, action: str):
        """Place order via IBKR Gateway."""
        logger.info(f"Placing {action} order: {quantity} {symbol}")

        # Real IBKR API call
        order = self.client.place_order(
            symbol=symbol,
            quantity=quantity,
            action=action,
        )

        return {
            "order_id": order.orderId,
            "status": order.status,
            "fill_price": order.avgFillPrice,
        }

    @dry_run_trade()
    def close_position(self, symbol: str):
        """Close position."""
        position = self.get_position(symbol)

        return self.place_order(
            symbol=symbol,
            quantity=abs(position.quantity),
            action="SELL" if position.quantity > 0 else "BUY",
        )
```

### Database Operations

**admin-api/app/service/positions.py**:
```python
from spreadpilot_core.dry_run import dry_run_database_async

class PositionService:
    @dry_run_database_async()
    async def save_position(self, position_data: dict):
        """Save position to database."""
        result = await self.db.positions.insert_one(position_data)
        return result.inserted_id

    @dry_run_database_async()
    async def update_position(self, position_id: str, updates: dict):
        """Update position."""
        await self.db.positions.update_one(
            {"_id": position_id},
            {"$set": updates}
        )
```

### Email & Notifications

**alert-router/app/service/alerts.py**:
```python
from spreadpilot_core.dry_run import dry_run_email, dry_run_notification

class AlertService:
    @dry_run_email()
    def send_email_alert(self, subject: str, body: str):
        """Send email alert."""
        self.email_client.send(
            to=self.config.admin_email,
            subject=subject,
            body=body,
        )

    @dry_run_notification()
    def send_telegram_alert(self, message: str):
        """Send Telegram alert."""
        self.telegram_bot.send_message(
            chat_id=self.config.telegram_chat_id,
            text=message,
        )
```

---

## Best Practices

### 1. Always Use Decorators

**Good**:
```python
@dry_run_trade()
def place_order(symbol, quantity):
    return ibkr.place_order(symbol, quantity)
```

**Bad** (manual checks):
```python
def place_order(symbol, quantity):
    if DRY_RUN_MODE:
        logger.info(f"Would place order: {symbol} {quantity}")
        return {"status": "DRY_RUN"}
    return ibkr.place_order(symbol, quantity)
```

### 2. Provide Realistic Return Values

```python
# Good - realistic mock
@dry_run_trade(return_value={
    "order_id": "DRY_123",
    "status": "FILLED",
    "fill_price": 380.50,
    "commission": 1.00
})
def place_order(symbol, quantity):
    return ibkr.place_order(symbol, quantity)

# Bad - None breaks downstream code
@dry_run_trade()  # Returns None by default
def place_order(symbol, quantity):
    return ibkr.place_order(symbol, quantity)
```

### 3. Test Both Modes

```python
import pytest
from spreadpilot_core.dry_run import DryRunConfig

def test_place_order_real():
    """Test real execution."""
    DryRunConfig.disable()
    result = place_order("QQQ", 100)
    assert "order_id" in result

def test_place_order_dry_run():
    """Test dry-run simulation."""
    DryRunConfig.enable()
    result = place_order("QQQ", 100)
    assert result["status"] == "DRY_RUN"

    # Verify operation logged
    report = DryRunConfig.get_report()
    assert report["total_operations"] == 1
```

### 4. Clear Log Between Tests

```python
def setup():
    """Test setup."""
    DryRunConfig.clear_operations_log()
    DryRunConfig.enable()

def teardown():
    """Test teardown."""
    DryRunConfig.disable()
    DryRunConfig.clear_operations_log()
```

### 5. Use Context Manager for Isolation

```python
# Good - isolated dry-run
def validate_config(config):
    with dry_run_context():
        apply_config(config)
        test_all_operations()

        report = DryRunConfig.get_report()
        return report["total_operations"] > 0

# Bad - affects global state
def validate_config(config):
    DryRunConfig.enable()
    apply_config(config)
    # Forgot to disable - affects other code!
```

---

## Limitations

**Not Simulated**:
- External system state changes (market data, broker state)
- Time-dependent operations (unless mocked separately)
- Network latency
- Database constraints (unique keys, foreign keys)
- Third-party API rate limits

**Edge Cases**:
- Operations that depend on previous operation results may behave differently
- Asynchronous operations complete instantly (no real delay)
- Resource allocation (memory, connections) not simulated

**Recommendation**: Combine dry-run mode with paper trading gateway for comprehensive simulation.

---

## Troubleshooting

### Dry-Run Not Working

**Check configuration**:
```python
from spreadpilot_core.dry_run import DryRunConfig

print(f"Dry-run enabled: {DryRunConfig.is_enabled()}")
```

**Check decorator**:
```python
# Ensure decorator is applied
@dry_run_trade()  # Must have ()
def place_order(...):
    pass
```

### Operations Still Executing

**Verify initialization**:
```python
# In main.py startup
if settings.dry_run_mode:
    DryRunConfig.enable()
```

**Check decorator order**:
```python
# Good - dry_run first
@dry_run_trade()
@log_execution
def place_order(...):
    pass

# Bad - dry_run second (may not work)
@log_execution
@dry_run_trade()
def place_order(...):
    pass
```

### Report Empty

**Check collection is enabled**:
```python
# Ensure collection not disabled
DRY_RUN_COLLECT_REPORTS=true
```

---

## API Reference

### DryRunConfig

```python
class DryRunConfig:
    @classmethod
    def enable() -> None:
        """Enable dry-run mode globally."""

    @classmethod
    def disable() -> None:
        """Disable dry-run mode globally."""

    @classmethod
    def is_enabled() -> bool:
        """Check if dry-run mode is enabled."""

    @classmethod
    def get_report() -> dict:
        """Get dry-run execution report."""

    @classmethod
    def clear_operations_log() -> None:
        """Clear operations log."""
```

### Decorators

```python
@dry_run(operation_type: str, return_value: Any = None, log_args: bool = True)
@dry_run_async(operation_type: str, return_value: Any = None, log_args: bool = True)
@dry_run_trade(return_value: Optional[dict] = None)
@dry_run_database(return_value: Any = True)
@dry_run_database_async(return_value: Any = True)
@dry_run_email(return_value: Any = True)
@dry_run_notification(return_value: Any = True)
@dry_run_api_call(return_value: Any = None)
```

### Context Manager

```python
with dry_run_context():
    # Operations simulated
    pass
# Back to normal
```

---

## Related Documentation

- [Paper Trading Mode](PAPER_TRADING_MODE.md) - Full market simulation
- [Testing Guide](05-testing-guide.md) - E2E testing strategies
- [Email Preview Mode](EMAIL_PREVIEW_MODE.md) - Email testing

---

**Quality**: Production-ready
**Status**: Complete
**Version**: 1.0.0

# Dry-Run Mode Integration Guide

Complete guide for using dry-run mode across SpreadPilot services to simulate operations without executing them.

## Overview

Dry-run mode allows you to test trading and alerting workflows without:
- Actually placing trades with IBKR
- Sending emails or Telegram notifications
- Making real API calls

All operations are logged but not executed, making it perfect for:
- Testing new strategies
- Debugging workflows
- Validating configurations
- Running demos

## Quick Start

### Enable Dry-Run Mode

Add to your `.env` file:

```bash
DRY_RUN_MODE=true
```

Or set as environment variable:

```bash
export DRY_RUN_MODE=true
```

### Services Supporting Dry-Run Mode

✅ **trading-bot**: Simulates IBKR trades
✅ **alert-router**: Simulates email/Telegram notifications
✅ **report-worker**: Simulates report generation and email sending
✅ **admin-api**: Simulates manual operations and database writes

## Integration Details

### 1. Trading Bot Integration

**Location**: `trading-bot/app/main.py`

**Configuration**:
```python
# trading-bot/app/config.py
dry_run_mode: bool = Field(
    default=False,
    env="DRY_RUN_MODE",
    description="Enable dry-run mode (simulate operations without executing)",
)
```

**Initialization**:
```python
# On startup
if settings.dry_run_mode:
    DryRunConfig.enable()
    logger.warning("🔵 DRY-RUN MODE ENABLED - Operations will be simulated")
```

**Decorated Methods**:
- `IBKRClient.place_order()` - Simulates order placement

**Log Output**:
```
🔵 [DRY-RUN] [TRADE] Would execute: place_order
  Args: contract=<Contract QQQ>, order=<MarketOrder qty=10>
```

### 2. Alert Router Integration

**Location**: `alert-router/app/main.py`

**Configuration**:
```python
# alert-router/app/config.py
DRY_RUN_MODE: bool = Field(
    default=False,
    env="DRY_RUN_MODE",
    description="Enable dry-run mode (simulate operations without executing)",
)
```

**Initialization**:
```python
# On startup
if settings.DRY_RUN_MODE:
    DryRunConfig.enable()
    logger.warning("🔵 DRY-RUN MODE ENABLED - Notifications will be simulated")
```

**Decorated Methods**:
- `AlertRouter.send_telegram_alert()` - Simulates Telegram messages
- `AlertRouter.send_email_alert()` - Simulates email sending

**Log Output**:
```
🔵 [DRY-RUN] [NOTIFICATION] Would execute: send_telegram_alert
  Args: chat_id='12345', message='Alert: System down'
🔵 [DRY-RUN] [EMAIL] Would execute: send_email_alert
  Args: recipient='admin@example.com', subject='Alert: System down'
```

### 3. Report Worker Integration

**Location**: `report-worker/app/main.py`

**Configuration**:
```python
# report-worker/app/config.py
dry_run_mode: bool = Field(
    default=False,
    env="DRY_RUN_MODE",
    description="Enable dry-run mode (simulate operations without executing)",
)
```

**Initialization**:
```python
# On startup
if config.get_settings().dry_run_mode:
    DryRunConfig.enable()
    logger.warning("🔵 DRY-RUN MODE ENABLED - Reports and emails will be simulated")
```

**Decorated Methods**:
- `CommissionMailer._send_commission_email()` - Simulates commission email sending
- `EmailSender.send_email()` - Simulates SendGrid email sending (spreadpilot-core)
- `SMTPEmailSender.send_email()` - Simulates SMTP email sending (spreadpilot-core)
- `send_email()` - Simulates standalone email function (spreadpilot-core)

**Log Output**:
```
🔵 [DRY-RUN] [EMAIL] Would execute: _send_commission_email
  Args: <CommissionMonthly record>, <Database session>
🔵 [DRY-RUN] [EMAIL] Would execute: send_email
  Args: to_email='follower@example.com', subject='Commission Report - January 2025'
```

### 4. Admin API Integration

**Location**: `admin-api/main.py`

**Configuration**:
```python
# admin-api/app/core/config.py
dry_run_mode: bool = os.getenv("DRY_RUN_MODE", "false").lower() == "true"
```

**Initialization**:
```python
# On startup
if settings.dry_run_mode:
    DryRunConfig.enable()
    logger.warning("🔵 DRY-RUN MODE ENABLED - Manual operations will be simulated")
```

**Decorated Methods**:
- `manual_close_positions()` - Simulates manual position close operations

**Log Output**:
```
🔵 [DRY-RUN] [MANUAL_OPERATION] Would execute: manual_close_positions
  Args: request=<ManualCloseRequest follower_id='FOLLOWER_001'>
```

**API Response (Dry-Run)**:
```json
{
  "success": true,
  "message": "[DRY-RUN] Manual close operation simulated (not executed)",
  "closed_positions": 0,
  "follower_id": "DRY_RUN",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## Usage Examples

### Example 1: Test Trading Strategy

```bash
# Enable dry-run mode
export DRY_RUN_MODE=true

# Start trading bot
cd trading-bot
python -m app.main
```

**Expected Logs**:
```
INFO: Trading bot started
WARNING: 🔵 DRY-RUN MODE ENABLED - Operations will be simulated
INFO: Processing signal for QQQ vertical spread
🔵 [DRY-RUN] [TRADE] Would execute: place_order
  Args: contract=<Contract QQQ 400C>, order=<MarketOrder qty=1>
INFO: Trade simulated successfully
```

### Example 2: Test Alert Delivery

```bash
# Enable dry-run mode
export DRY_RUN_MODE=true

# Start alert router
cd alert-router
python -m app.main
```

**Expected Logs**:
```
INFO: Alert Router service starting...
WARNING: 🔵 DRY-RUN MODE ENABLED - Notifications will be simulated
INFO: Processing alert: COMPONENT_DOWN
🔵 [DRY-RUN] [NOTIFICATION] Would execute: send_telegram_alert
  Args: chat_id='12345', message='🔴 *Component Down*...'
INFO: Alert routing complete (simulated)
```

### Example 3: Test Report Generation

```bash
# Enable dry-run mode
export DRY_RUN_MODE=true

# Start report worker
cd report-worker
python -m app.main
```

**Expected Logs**:
```
INFO: Report worker started
WARNING: 🔵 DRY-RUN MODE ENABLED - Reports and emails will be simulated
INFO: Processing monthly reports
🔵 [DRY-RUN] [EMAIL] Would execute: _send_commission_email
  Args: record=<CommissionMonthly follower_id='FOLLOWER_001'>, db=<Session>
INFO: Report email simulated successfully
```

### Example 4: Test Manual Operations API

```bash
# Enable dry-run mode
export DRY_RUN_MODE=true

# Start admin API
cd admin-api
python main.py
```

**Make API Request**:
```bash
curl -X POST http://localhost:8080/api/v1/manual-close \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "follower_id": "FOLLOWER_001",
    "pin": "0312",
    "close_all": true,
    "reason": "Testing dry-run mode"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "message": "[DRY-RUN] Manual close operation simulated (not executed)",
  "closed_positions": 0,
  "follower_id": "DRY_RUN",
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

**Expected Logs**:
```
INFO: Admin API started
WARNING: 🔵 DRY-RUN MODE ENABLED - Manual operations will be simulated
INFO: Received manual close request for follower FOLLOWER_001
🔵 [DRY-RUN] [MANUAL_OPERATION] Would execute: manual_close_positions
INFO: Manual operation simulated (not executed)
```

### Example 5: Docker Compose Integration

```yaml
# docker-compose.yml
services:
  trading-bot:
    environment:
      - DRY_RUN_MODE=true
    # ... rest of config

  alert-router:
    environment:
      - DRY_RUN_MODE=true
    # ... rest of config

  report-worker:
    environment:
      - DRY_RUN_MODE=true
    # ... rest of config

  admin-api:
    environment:
      - DRY_RUN_MODE=true
    # ... rest of config
```

**Start all services in dry-run mode**:
```bash
docker-compose up
```

### Example 6: Programmatic Testing

```python
from spreadpilot_core.dry_run import DryRunConfig
from spreadpilot_core.ibkr.client import IBKRClient

# Enable dry-run globally
DryRunConfig.enable()

# Create client
client = IBKRClient(host="127.0.0.1", port=4002)

# This will be simulated, not executed
await client.place_order(contract, order)
# Logs: 🔵 [DRY-RUN] [TRADE] Would execute: place_order

# Check if dry-run is enabled
if DryRunConfig.is_enabled():
    print("Running in simulation mode")

# Disable dry-run
DryRunConfig.disable()

# This will execute for real
await client.place_order(contract, order)
```

## Testing Checklist

Use this checklist to verify dry-run mode is working correctly:

### Trading Bot
- [ ] Start trading-bot with `DRY_RUN_MODE=true`
- [ ] Verify startup log shows "🔵 DRY-RUN MODE ENABLED"
- [ ] Trigger a trade signal
- [ ] Verify log shows "🔵 [DRY-RUN] [TRADE]"
- [ ] Verify no actual orders appear in IBKR
- [ ] Verify position database shows simulated trades (if applicable)

### Alert Router
- [ ] Start alert-router with `DRY_RUN_MODE=true`
- [ ] Verify startup log shows "🔵 DRY-RUN MODE ENABLED"
- [ ] Trigger an alert (use test script or API)
- [ ] Verify log shows "🔵 [DRY-RUN] [NOTIFICATION]" or "🔵 [DRY-RUN] [EMAIL]"
- [ ] Verify no actual emails sent (check SendGrid dashboard)
- [ ] Verify no actual Telegram messages sent (check bot)

### Report Worker
- [ ] Start report-worker with `DRY_RUN_MODE=true`
- [ ] Verify startup log shows "🔵 DRY-RUN MODE ENABLED"
- [ ] Trigger a report generation (use test script or Pub/Sub)
- [ ] Verify log shows "🔵 [DRY-RUN] [EMAIL]"
- [ ] Verify no actual emails sent (check SendGrid dashboard or SMTP logs)
- [ ] Verify no database updates for sent status
- [ ] Verify PDF/Excel generation may still occur (file operations not blocked)

### Admin API
- [ ] Start admin-api with `DRY_RUN_MODE=true`
- [ ] Verify startup log shows "🔵 DRY-RUN MODE ENABLED"
- [ ] Make manual close API request with valid PIN
- [ ] Verify log shows "🔵 [DRY-RUN] [MANUAL_OPERATION]"
- [ ] Verify response message contains "[DRY-RUN]"
- [ ] Verify no database entries created in `manual_operations` collection
- [ ] Verify no alerts created in database
- [ ] Verify follower_id in response is "DRY_RUN"

## Configuration Matrix

| Service | Config File | Environment Variable | Decorated Methods |
|---------|-------------|---------------------|-------------------|
| trading-bot | `trading-bot/app/config.py` | `DRY_RUN_MODE` | `IBKRClient.place_order()` |
| alert-router | `alert-router/app/config.py` | `DRY_RUN_MODE` | `AlertRouter.send_telegram_alert()`<br>`AlertRouter.send_email_alert()` |
| report-worker | `report-worker/app/config.py` | `DRY_RUN_MODE` | `CommissionMailer._send_commission_email()`<br>`EmailSender.send_email()`<br>`SMTPEmailSender.send_email()`<br>`send_email()` (standalone) |
| admin-api | `admin-api/app/core/config.py` | `DRY_RUN_MODE` | `manual_close_positions()` |

## Decorator Reference

### Available Decorators

```python
from spreadpilot_core.dry_run import dry_run_async

@dry_run_async("trade", return_value=None)
async def place_order(self, contract, order):
    """Simulates trade placement in dry-run mode."""
    # Real implementation
    pass

@dry_run_async("notification", return_value=True)
async def send_telegram_alert(self, chat_id, message):
    """Simulates Telegram notification in dry-run mode."""
    # Real implementation
    pass

@dry_run_async("email", return_value=True)
async def send_email_alert(self, recipient, subject, html):
    """Simulates email sending in dry-run mode."""
    # Real implementation
    pass
```

### Custom Decorators

```python
@dry_run_async("custom_operation", return_value={"status": "success"})
async def my_custom_operation(self, param1, param2):
    """Your custom operation that should be simulated."""
    # Real implementation
    pass
```

## Return Value Behavior

In dry-run mode, decorated functions return the specified `return_value`:

| Decorator | Return Value | Use Case |
|-----------|-------------|----------|
| `@dry_run_async("trade", return_value=None)` | `None` | Match error return pattern |
| `@dry_run_async("notification", return_value=True)` | `True` | Simulate success |
| `@dry_run_async("email", return_value=True)` | `True` | Simulate success |

## Troubleshooting

### Dry-Run Mode Not Activating

**Symptom**: Operations execute for real even with `DRY_RUN_MODE=true`

**Solutions**:
1. Check environment variable is set: `echo $DRY_RUN_MODE`
2. Verify config file has field: `dry_run_mode` or `DRY_RUN_MODE`
3. Check startup logs for "🔵 DRY-RUN MODE ENABLED"
4. Ensure decorator is imported: `from spreadpilot_core.dry_run import dry_run_async`

### Missing Dry-Run Logs

**Symptom**: No "🔵 [DRY-RUN]" logs appearing

**Solutions**:
1. Check log level is INFO or DEBUG
2. Verify DryRunConfig.enable() is called at startup
3. Check decorator is applied: `@dry_run_async(...)`
4. Ensure method is actually being called

### Import Errors

**Symptom**: `ImportError: cannot import name 'dry_run_async'`

**Solutions**:
1. Ensure spreadpilot-core is installed: `pip install -e ./spreadpilot-core`
2. Check spreadpilot-core has dry_run module
3. Verify Python path includes spreadpilot-core

## Best Practices

1. **Always test with dry-run first**: Never test new strategies with real money
2. **Use in staging environments**: Keep production in live mode only
3. **Log verbosely**: Increase log level to DEBUG for detailed simulation info
4. **Verify decorator placement**: Ensure decorators are on the right methods
5. **Document simulated operations**: Add docstring notes about dry-run behavior
6. **Test both modes**: Verify code works in both dry-run and live modes

## Integration Status

### ✅ Completed
- [x] Core dry-run framework (`spreadpilot-core/spreadpilot_core/dry_run.py`)
- [x] Trading bot integration
- [x] Alert router integration
- [x] Report worker integration
- [x] Admin API integration
- [x] Email utility decorators (SendGrid + SMTP)
- [x] Configuration via environment variables
- [x] Async decorator support
- [x] Integration documentation
- [x] Integration tests
- [x] Manual operations dry-run support

### 🔄 Planned
- [ ] Dashboard dry-run status indicator
- [ ] Dry-run mode API endpoint (`GET /api/v1/dry-run/status`)
- [ ] Automated dry-run tests in CI/CD
- [ ] Performance metrics comparison (dry-run vs live)
- [ ] Dry-run mode for database read operations (optional)

## Related Documentation

- [Dry-Run Mode Framework](./DRY_RUN_MODE.md) - Core framework documentation
- [Testing Strategy](./TESTING_STRATEGY.md) - Overall testing approach
- [Simulation/Replay Mode](./SIMULATION_REPLAY_MODE.md) - Historical backtesting
- [Paper Trading Gateway](./PAPER_TRADING_GATEWAY.md) - IBKR paper account setup

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review logs for "🔵 [DRY-RUN]" prefixes
3. Open GitHub issue with logs and configuration

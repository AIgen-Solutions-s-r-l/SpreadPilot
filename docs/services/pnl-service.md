# P&L Service Documentation

## Overview

The P&L Service is a comprehensive real-time monitoring and calculation system implemented in `spreadpilot-core/spreadpilot_core/pnl/service.py`. It provides:

- **Real-time MTM calculations** every 30 seconds during market hours
- **Daily rollups** at 16:30 ET for end-of-day summaries
- **Monthly rollups** at 00:10 ET on the 1st of each month
- **Commission calculation** based on positive monthly P&L

## Architecture

### Core Components

1. **PnLService Class**
   - Main service orchestrator
   - Manages concurrent monitoring tasks
   - Handles follower subscriptions
   - Integrates with external systems via callbacks

2. **Data Models** (PostgreSQL)
   - `PnLIntraday`: Real-time MTM snapshots
   - `PnLDaily`: Daily rollup summaries
   - `PnLMonthly`: Monthly rollup summaries
   - `CommissionMonthly`: Monthly commission calculations
   - `Trade`: Individual trade records
   - `Quote`: Market price snapshots

### Key Features

#### 1. MTM Calculation Loop (`_mtm_calculation_loop`)
```python
async def _mtm_calculation_loop(self, shutdown_event: asyncio.Event):
    """Calculate mark-to-market P&L every 30 seconds."""
    while not shutdown_event.is_set() and self.monitoring_active:
        if self._is_market_open():
            await self._calculate_and_store_mtm()
        await asyncio.sleep(30)
```

- Runs continuously during market hours (9:30 AM - 4:00 PM ET)
- Calculates realized P&L from today's trades
- Calculates unrealized P&L from open positions
- Stores snapshots in `PnLIntraday` table

#### 2. Daily Rollup Scheduler (`_daily_rollup_scheduler`)
```python
async def _daily_rollup_scheduler(self, shutdown_event: asyncio.Event):
    """Schedule daily rollups at 16:30 ET."""
    # Runs at 16:30 ET (4:30 PM ET)
    # Aggregates intraday snapshots
    # Calculates daily metrics
    # Stores in PnLDaily table
```

- Executes at 16:30 ET daily
- Aggregates all intraday snapshots
- Calculates daily metrics (max profit, max drawdown, trade count)
- Creates finalized daily summary

#### 3. Monthly Rollup Scheduler (`_monthly_rollup_scheduler`)
```python
async def _monthly_rollup_scheduler(self, shutdown_event: asyncio.Event):
    """Schedule monthly rollups at 00:10 ET on the 1st of each month."""
    # Runs at 00:10 ET on the 1st
    # Aggregates daily summaries
    # Calculates monthly metrics
    # Triggers commission calculation
```

- Executes at 00:10 ET on the 1st of each month
- Aggregates previous month's daily summaries
- Calculates monthly performance metrics
- Triggers commission calculation

#### 4. Commission Calculation (`_calculate_monthly_commission`)
```python
async def _calculate_monthly_commission(
    self,
    session: AsyncSession,
    follower_id: str,
    year: int,
    month: int,
    monthly_pnl: Decimal,
):
    """Calculate monthly commission based on positive P&L."""
    # Rule: if pnl_month > 0 => commission = pct * pnl_month, else 0
    is_payable = monthly_pnl > 0
    commission_amount = commission_pct * monthly_pnl if is_payable else Decimal("0")
```

- Calculates commission only on positive monthly P&L
- Uses follower's commission percentage (default 20%)
- Stores in `CommissionMonthly` table with IBAN and email

## Integration

### Callback System

The service uses callbacks to integrate with external systems:

```python
pnl_service.set_callbacks(
    get_positions_fn=get_follower_positions,     # Get current positions
    get_market_price_fn=get_market_price,        # Get market prices
    subscribe_tick_fn=subscribe_to_tick_feed     # Subscribe to quotes
)
```

### Database Schema

All P&L tables are managed through Alembic migrations:

1. `001_initial_pnl_schema.py` - Creates core P&L tables
2. `002_add_commission_monthly.py` - Adds commission tracking
3. `003_add_email_sent_to_commission_monthly.py` - Adds email tracking

## Usage

### Starting the Service

```python
# Initialize service
pnl_service = PnLService()

# Set up callbacks
pnl_service.set_callbacks(...)

# Add followers to monitor
await pnl_service.add_follower("follower-123")

# Start monitoring
shutdown_event = asyncio.Event()
await pnl_service.start_monitoring(shutdown_event)
```

### Recording Trades

```python
fill_data = {
    "symbol": "QQQ",
    "contract_type": "PUT",
    "strike": 450.0,
    "expiration": "2025-07-18",
    "trade_type": "SELL",
    "quantity": 5,
    "price": 2.45,
    "commission": 1.25,
    "order_id": "ORDER123",
    "execution_id": "EXEC123"
}

await pnl_service.record_trade_fill("follower-123", fill_data)
```

### Querying P&L Data

```python
# Get current P&L
current_pnl = await pnl_service.get_current_pnl("follower-123")

# Get monthly commission
commission = await pnl_service.get_monthly_commission("follower-123", 2025, 6)
```

## Market Hours

The service respects US market hours:
- **Active Hours**: Monday-Friday, 9:30 AM - 4:00 PM ET
- **Daily Rollup**: 4:30 PM ET
- **Monthly Rollup**: 12:10 AM ET on the 1st

## Performance Considerations

1. **Concurrent Processing**: All followers are processed concurrently
2. **Quote Caching**: In-memory cache reduces API calls
3. **Batch Operations**: Database operations are batched where possible
4. **Error Isolation**: Errors in one follower don't affect others

## Error Handling

- Each monitoring loop has independent error handling
- Failed calculations are logged but don't stop the service
- Automatic retry with exponential backoff for transient errors
- Critical errors publish alerts to Redis stream

## Future Enhancements

1. **Real-time WebSocket Updates**: Push P&L updates to clients
2. **Historical P&L API**: Query historical P&L data
3. **Performance Analytics**: Advanced metrics and analytics
4. **Multi-Currency Support**: Handle non-USD positions
5. **Tax Reporting**: Generate tax-optimized reports
# Paper Trading Mode

Paper Trading Mode provides a production-ready simulation environment for SpreadPilot, allowing risk-free strategy testing with realistic market conditions.

## Overview

**Paper Trading Gateway** is a mock IBKR Gateway that simulates:
- Realistic price movements with volatility
- Order execution with slippage and commissions
- Market hours enforcement
- Persistent account state
- Performance tracking and analytics

**Use Cases**:
- Strategy testing without capital risk
- User onboarding and training
- Development and QA testing
- What-if analysis and backtesting

---

## Quick Start

### Start Paper Trading Mode

```bash
# Start all services with paper trading gateway
docker-compose --profile paper up -d

# Verify gateway is running
curl http://localhost:4003/health

# Check gateway logs
docker logs spreadpilot-paper-gateway
```

### Configure Trading Bot for Paper Mode

Update `.env` or environment variables:

```bash
# Point to paper gateway instead of real IBKR
IB_GATEWAY_HOST=paper-gateway
IB_GATEWAY_PORT=4003
IB_TRADING_MODE=paper
```

### Access Paper Trading API

Interactive API documentation: **http://localhost:4003/docs**

---

## Configuration

### Environment Variables

```bash
# Paper Trading Settings
PAPER_INITIAL_BALANCE=100000        # Starting account balance
PAPER_COMMISSION_RATE=0.005         # Stock commission per share
PAPER_OPTION_COMMISSION=0.65        # Option commission per contract
PAPER_SLIPPAGE_BPS=5                # Slippage in basis points
PAPER_VOLATILITY=0.02               # Daily volatility (2%)

# Market Data
MARKET_DATA_SOURCE=mock             # Options: mock, historical, live

# Market Hours (US Eastern Time)
MARKET_OPEN_HOUR=9
MARKET_OPEN_MINUTE=30
MARKET_CLOSE_HOUR=16
MARKET_CLOSE_MINUTE=0
```

### Default Values

| Setting | Default | Description |
|---------|---------|-------------|
| Initial Balance | $100,000 | Starting cash |
| Stock Commission | $0.005/share | Min $1, max 1% of trade |
| Option Commission | $0.65/contract | Per IBKR schedule |
| Slippage | 5 bps | Market impact |
| Volatility | 2% | Daily price movement |

---

## How It Works

### 1. Price Simulation

**Stocks (e.g., QQQ)**:
- Uses **Geometric Brownian Motion** (GBM)
- Configurable volatility (default: 2% daily)
- Random walk with normal distribution
- Bid/ask spread: 1-5 cents

**Formula**:
```
dS = S × (μ × dt + σ × √dt × Z)
```
Where:
- S = current price
- μ = drift (0 for intraday)
- σ = volatility
- Z ~ N(0, 1) normal random variable

**Options**:
- Simplified **Black-Scholes** pricing
- Intrinsic value + time value
- Volatility-based time decay

### 2. Order Execution

**Market Orders**:
- Execute immediately at bid (SELL) or ask (BUY)
- Always filled (during market hours)
- Slippage applied based on order size

**Limit Orders**:
- Execute if price crosses limit
- Immediate-or-cancel (no pending orders)
- Rejected if limit not met

**Partial Fills**:
- 10% chance for orders > 500 shares
- Filled quantity: 70-90% of order

### 3. Slippage Model

Uses **square root market impact model**:

```
Slippage (bps) = Base_BPS × √(Quantity / Liquidity_Threshold)
```

- Base slippage: 5 bps (configurable)
- Liquidity threshold: 1,000 shares
- Maximum: 20 bps cap

**Example**:
- 100 shares: ~1.6 bps ($0.006 per share at $100)
- 500 shares: ~3.5 bps ($0.014 per share)
- 2,000 shares: ~7.1 bps ($0.028 per share)

### 4. Commission Calculation

**Stocks**:
```
Commission = Quantity × $0.005
Minimum: $1
Maximum: 1% of trade value
```

**Options**:
```
Commission = Contracts × $0.65
```

### 5. Market Hours

**Trading Allowed**:
- Monday - Friday
- 9:30 AM - 4:00 PM Eastern Time
- Excludes US market holidays

**Holidays** (2024-2025):
- New Year's Day
- MLK Day
- Presidents Day
- Good Friday
- Memorial Day
- Juneteenth
- Independence Day
- Labor Day
- Thanksgiving
- Christmas

Orders placed outside hours are **rejected** with specific reason.

---

## API Reference

### Health Check

```bash
GET /health

Response:
{
  "status": "healthy",
  "service": "Paper Trading Gateway",
  "version": "1.0.0",
  "market_open": true,
  "timestamp": "2024-01-15T14:30:00Z"
}
```

### Market Status

```bash
GET /api/v1/market/status

Response:
{
  "is_open": true,
  "current_time": "2024-01-15T14:30:00-05:00",
  "market_open_time": "09:30:00",
  "market_close_time": "16:00:00",
  "timezone": "US/Eastern",
  "is_weekend": false,
  "is_holiday": false
}
```

### Place Order

```bash
POST /api/v1/orders
Content-Type: application/json

{
  "symbol": "QQQ",
  "action": "BUY",
  "quantity": 100,
  "order_type": "MKT",
  "asset_type": "STOCK"
}

Response:
{
  "order_id": "PAPER_1705338600000",
  "symbol": "QQQ",
  "action": "BUY",
  "quantity": 100,
  "order_type": "MKT",
  "status": "FILLED",
  "fill_price": 380.52,
  "filled_quantity": 100,
  "commission": 1.00,
  "timestamp": "2024-01-15T14:30:00Z",
  "rejection_reason": null
}
```

### Get Positions

```bash
GET /api/v1/positions

Response:
[
  {
    "symbol": "QQQ",
    "quantity": 100,
    "avg_cost": 380.50,
    "current_price": 380.75,
    "market_value": 38075.00,
    "unrealized_pnl": 25.00,
    "realized_pnl": 0.00,
    "asset_type": "STOCK"
  }
]
```

### Get Account Info

```bash
GET /api/v1/account

Response:
{
  "net_liquidation": 100025.00,
  "available_funds": 61925.00,
  "buying_power": 61925.00,
  "daily_pnl": 25.00,
  "total_pnl": 25.00,
  "positions_value": 38075.00,
  "cash_balance": 61950.00,
  "margin_used": 9518.75
}
```

### Get Performance Metrics

```bash
GET /api/v1/account/performance

Response:
{
  "total_trades": 10,
  "winning_trades": 6,
  "losing_trades": 4,
  "win_rate": 0.6,
  "total_pnl": 1250.50,
  "total_commission": 50.00,
  "sharpe_ratio": null,
  "max_drawdown": 500.00,
  "average_win": 300.00,
  "average_loss": 125.00,
  "profit_factor": 2.4
}
```

### Admin: Reset Account

```bash
POST /api/v1/admin/reset

Response:
{
  "success": true,
  "message": "Paper trading account reset to initial state"
}
```

### Admin: Set Balance

```bash
PUT /api/v1/admin/balance
Content-Type: application/json

{
  "new_balance": 100000
}

Response:
{
  "net_liquidation": 100000.00,
  "cash_balance": 100000.00,
  ...
}
```

---

## Usage Examples

### Example 1: Basic Stock Trade

```bash
# 1. Check market is open
curl http://localhost:4003/api/v1/market/status

# 2. Place BUY order
curl -X POST http://localhost:4003/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "QQQ",
    "action": "BUY",
    "quantity": 100,
    "order_type": "MKT",
    "asset_type": "STOCK"
  }'

# 3. Check position
curl http://localhost:4003/api/v1/positions

# 4. Place SELL order to close
curl -X POST http://localhost:4003/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "QQQ",
    "action": "SELL",
    "quantity": 100,
    "order_type": "MKT",
    "asset_type": "STOCK"
  }'

# 5. Check performance
curl http://localhost:4003/api/v1/account/performance
```

### Example 2: Limit Order

```bash
curl -X POST http://localhost:4003/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "SPY",
    "action": "BUY",
    "quantity": 50,
    "order_type": "LMT",
    "limit_price": 450.00,
    "asset_type": "STOCK"
  }'
```

### Example 3: Option Trade

```bash
curl -X POST http://localhost:4003/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "QQQ",
    "action": "BUY",
    "quantity": 10,
    "order_type": "MKT",
    "asset_type": "OPTION",
    "strike": 380.0,
    "expiry": "2024-02-16",
    "option_type": "CALL"
  }'
```

---

## Integration with SpreadPilot

### Trading Bot

The trading bot automatically works with paper gateway when configured:

```yaml
# docker-compose.yml or .env
environment:
  - IB_GATEWAY_HOST=paper-gateway  # Use paper gateway
  - IB_GATEWAY_PORT=4003
  - IB_TRADING_MODE=paper
```

**No code changes needed** - the trading bot uses the same IBKR client interface.

### Admin API

Configure admin API to route to paper gateway:

```yaml
environment:
  - IBKR_GATEWAY_URL=http://paper-gateway:4003
```

### Frontend Dashboard

The dashboard can display paper mode indicator (Phase 3 - planned):
- Visual badge: "PAPER MODE" vs "LIVE MODE"
- Color scheme: Blue/green for paper, red/orange for live
- Mode toggle in settings

---

## Performance Metrics

### Available Metrics

| Metric | Description |
|--------|-------------|
| Total Trades | Number of completed trades |
| Win Rate | Percentage of winning trades |
| Total P&L | Realized profit/loss |
| Total Commission | Cumulative fees paid |
| Max Drawdown | Largest peak-to-trough decline |
| Average Win | Mean profit of winning trades |
| Average Loss | Mean loss of losing trades |
| Profit Factor | Total wins / Total losses |
| Sharpe Ratio | Risk-adjusted returns (requires time series) |

### Interpretation

**Good Performance Indicators**:
- Win rate > 50%
- Profit factor > 1.5
- Sharpe ratio > 1.0 (if available)
- Max drawdown < 20% of initial balance

**Warning Signs**:
- Win rate < 40%
- Profit factor < 1.0
- Max drawdown > 30%
- High commission/P&L ratio

---

## Comparison: Paper vs Live

| Aspect | Paper Mode | Live Mode |
|--------|-----------|-----------|
| **Risk** | Zero financial risk | Real capital at risk |
| **Setup** | No IBKR credentials | Requires IBKR account |
| **Costs** | Simulated commissions | Real fees |
| **Data** | Simulated prices | Real market data |
| **Execution** | Instant (no queues) | Market delays |
| **Slippage** | Modeled | Actual market impact |
| **Liquidity** | Unlimited | Real constraints |
| **Market Hours** | Enforced | Actual exchange hours |

---

## Limitations

### Not Simulated

- ❌ Complex order types (bracket, trailing stop, OCO)
- ❌ Corporate actions (splits, dividends)
- ❌ Overnight interest/fees
- ❌ Liquidity constraints (low-volume stocks)
- ❌ Exchange-specific rules
- ❌ Bid/ask queue dynamics
- ❌ Flash crashes or circuit breakers
- ❌ News-driven volatility spikes

### Known Differences

- ⚠️ Slippage model is simplified (square root)
- ⚠️ No bid/ask depth simulation
- ⚠️ All orders execute immediately (or reject)
- ⚠️ Volatility is constant (not time-varying)
- ⚠️ No impact from other market participants

**Important**: Paper trading results **may differ significantly** from live trading. Always test strategies with small positions in live markets before scaling up.

---

## Migration: Paper → Live

### Preparation Checklist

- [ ] Verify paper trading profitability (> 50% win rate)
- [ ] Check max drawdown is acceptable (< 20%)
- [ ] Review commission impact on strategy
- [ ] Understand slippage differences
- [ ] Test with minimum position sizes first

### Configuration Changes

```bash
# Switch from paper to live
IB_GATEWAY_HOST=ib-gateway        # Real IBKR Gateway
IB_GATEWAY_PORT=4001              # Live port (4002 for IBKR paper)
IB_TRADING_MODE=live              # Set to live

# Add IBKR credentials
IB_USERNAME=your_username
IB_PASSWORD=your_password
```

### Gradual Rollout

1. **Start Small**: Use 10% of intended position size
2. **Monitor Closely**: Watch first 10 trades for differences
3. **Adjust Strategy**: Account for real slippage/commission
4. **Scale Up**: Gradually increase position size
5. **Compare**: Track paper vs live performance

---

## Troubleshooting

### Gateway Not Starting

```bash
# Check MongoDB
docker logs spreadpilot-mongodb

# Check gateway logs
docker logs spreadpilot-paper-gateway

# Verify network
docker exec spreadpilot-paper-gateway ping mongodb
```

### Orders Rejected

**"Market closed" errors**:
- Check current time is 9:30 AM - 4:00 PM ET
- Verify not weekend or holiday
- Use: `curl http://localhost:4003/api/v1/market/status`

**"Insufficient funds" errors**:
- Check account balance: `curl http://localhost:4003/api/v1/account`
- Reduce position size
- Reset account: `curl -X POST http://localhost:4003/api/v1/admin/reset`

**"Position not found" (on SELL)**:
- Verify you have position: `curl http://localhost:4003/api/v1/positions`
- Check symbol spelling matches exactly

### Prices Not Realistic

Prices use random walk simulation. To adjust:

```bash
# Change volatility (0.02 = 2% daily)
PAPER_VOLATILITY=0.03

# Or reset to base prices
curl -X POST http://localhost:4003/api/v1/admin/reset
```

### Performance Issues

MongoDB queries slow:
```bash
# Check indexes
docker exec spreadpilot-mongodb mongosh spreadpilot_paper --eval "db.orders.getIndexes()"

# Limit history
docker exec spreadpilot-mongodb mongosh spreadpilot_paper --eval "db.orders.deleteMany({timestamp: {\$lt: ISODate('2024-01-01')}})"
```

---

## Advanced Usage

### Custom Price Scenarios

Set specific base prices for testing:

```python
# Admin endpoint (future enhancement)
PUT /api/v1/admin/prices
{
  "QQQ": 380.0,
  "SPY": 450.0
}
```

### Load Testing

Generate high-volume orders:

```bash
for i in {1..100}; do
  curl -X POST http://localhost:4003/api/v1/orders \
    -H "Content-Type: application/json" \
    -d "{\"symbol\":\"QQQ\",\"action\":\"BUY\",\"quantity\":10,\"order_type\":\"MKT\",\"asset_type\":\"STOCK\"}"
done
```

### Automated Testing

```python
import httpx

# Initialize
client = httpx.Client(base_url="http://localhost:4003")

# Reset account
client.post("/api/v1/admin/reset")

# Place orders
for _ in range(10):
    order = client.post("/api/v1/orders", json={
        "symbol": "QQQ",
        "action": "BUY",
        "quantity": 100,
        "order_type": "MKT",
        "asset_type": "STOCK"
    })
    assert order.status_code == 200

# Check results
perf = client.get("/api/v1/account/performance").json()
assert perf["win_rate"] >= 0.4
```

---

## FAQ

**Q: Do I need IBKR credentials for paper trading?**
A: No, paper gateway runs completely standalone.

**Q: Can I run paper and live mode simultaneously?**
A: Yes! Use different environment configs for each trading bot instance.

**Q: Does paper mode support all order types?**
A: Currently only MARKET and LIMIT. Complex orders (bracket, trailing stop) are not supported.

**Q: How accurate is the price simulation?**
A: Prices use GBM which is realistic for short-term testing. For long-term backtesting, consider using historical data.

**Q: Can I import historical data?**
A: Not yet, but planned for `MARKET_DATA_SOURCE=historical` mode.

**Q: Does paper mode slow down my system?**
A: No, it's lightweight (< 100MB RAM, minimal CPU).

**Q: Can multiple users share one paper gateway?**
A: Currently one shared account. Multi-user support is planned.

---

## Related Documentation

- [Email Preview Mode](EMAIL_PREVIEW_MODE.md) - MailHog for email testing
- [Testing Guide](05-testing-guide.md) - E2E testing with mocks
- [IBKR Integration](gateway-manager.md) - Real gateway management

---

**Quality**: Production-ready
**Status**: Complete
**Version**: 1.0.0

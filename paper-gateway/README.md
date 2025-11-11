# Paper Trading Gateway

Production-ready paper trading gateway for SpreadPilot that simulates IBKR Gateway with realistic market conditions.

## Features

- **Realistic Price Simulation**: Geometric Brownian Motion for stocks, simplified Black-Scholes for options
- **Order Execution**: Market and limit orders with slippage and commission simulation
- **Market Hours**: NYSE/NASDAQ trading hours enforcement with holiday calendar
- **Persistent State**: MongoDB storage for orders, positions, and account data
- **Performance Metrics**: Win rate, P&L, Sharpe ratio, max drawdown tracking
- **Admin Functions**: Reset account, adjust balance for testing

## Quick Start

### With Docker Compose (Recommended)

```bash
# Start paper trading gateway
docker-compose --profile paper up -d

# Check gateway is running
curl http://localhost:4003/health

# View logs
docker logs spreadpilot-paper-gateway
```

### Standalone

```bash
cd paper-gateway

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MONGO_URI=mongodb://admin:password@localhost:27017
export PAPER_INITIAL_BALANCE=100000

# Run gateway
python -m app.main
```

## API Documentation

Interactive API docs available at: http://localhost:4003/docs

### Orders

**Place Order**:
```bash
curl -X POST http://localhost:4003/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "QQQ",
    "action": "BUY",
    "quantity": 100,
    "order_type": "MKT",
    "asset_type": "STOCK"
  }'
```

**Get Order**:
```bash
curl http://localhost:4003/api/v1/orders/{order_id}
```

### Positions

**Get All Positions**:
```bash
curl http://localhost:4003/api/v1/positions
```

**Close Position**:
```bash
curl -X POST http://localhost:4003/api/v1/positions/QQQ/close
```

### Account

**Get Account Info**:
```bash
curl http://localhost:4003/api/v1/account
```

**Get Performance Metrics**:
```bash
curl http://localhost:4003/api/v1/account/performance
```

### Admin

**Reset Account**:
```bash
curl -X POST http://localhost:4003/api/v1/admin/reset
```

**Set Balance**:
```bash
curl -X PUT http://localhost:4003/api/v1/admin/balance \
  -H "Content-Type: application/json" \
  -d '{"new_balance": 100000}'
```

## Configuration

Environment variables:

```bash
# MongoDB
MONGO_URI=mongodb://admin:password@mongodb:27017
MONGO_DB_NAME=spreadpilot_paper

# Paper Trading
PAPER_INITIAL_BALANCE=100000        # Initial account balance
PAPER_COMMISSION_RATE=0.005         # $0.005 per share
PAPER_OPTION_COMMISSION=0.65        # $0.65 per contract
PAPER_SLIPPAGE_BPS=5                # 5 basis points slippage
PAPER_VOLATILITY=0.02               # 2% daily volatility

# Market Hours (US Eastern)
MARKET_OPEN_HOUR=9
MARKET_OPEN_MINUTE=30
MARKET_CLOSE_HOUR=16
MARKET_CLOSE_MINUTE=0

# Market Data
MARKET_DATA_SOURCE=mock             # mock, historical, or live

# Logging
LOG_LEVEL=INFO
```

## Simulation Models

### Stock Price Simulation

Uses Geometric Brownian Motion:

```
dS = S * (μ * dt + σ * √dt * Z)
```

Where:
- S = current price
- μ = drift (assumed 0 for intraday)
- σ = volatility (configurable)
- Z = standard normal random variable

### Option Price Simulation

Simplified Black-Scholes:

```
Option Price = Intrinsic Value + Time Value
```

Where:
- Intrinsic Value = max(S - K, 0) for calls, max(K - S, 0) for puts
- Time Value = σ * S * √T * 0.4 (simplified)

### Slippage Model

Square root market impact:

```
Slippage (bps) = Base_BPS * √(Quantity / Liquidity_Threshold)
```

Capped at 20 bps.

### Commission Model

IBKR fee schedule:
- **Stocks**: $0.005 per share, min $1, max 1% of trade value
- **Options**: $0.65 per contract

## Market Hours

Trading allowed:
- **Days**: Monday - Friday
- **Hours**: 9:30 AM - 4:00 PM Eastern Time
- **Holidays**: US market holidays excluded

Orders placed outside market hours are rejected.

## Performance Metrics

Tracked metrics:
- Total trades (wins/losses)
- Win rate
- Total P&L
- Total commission
- Max drawdown
- Average win/loss
- Profit factor
- Sharpe ratio (if sufficient data)

## Limitations

Not simulated:
- Complex order types (bracket, OCO, trailing stop)
- Corporate actions (splits, dividends)
- Overnight interest/fees
- Liquidity constraints
- Exchange-specific rules
- Bid/ask queue dynamics

**Note**: Paper trading results may differ significantly from live trading.

## Integration with SpreadPilot

### Trading Bot Configuration

Update trading-bot environment variables:

```bash
IB_GATEWAY_HOST=paper-gateway  # Point to paper gateway
IB_GATEWAY_PORT=4003           # Paper gateway port
IB_TRADING_MODE=paper          # Set to paper mode
```

### Admin API Configuration

Update admin-api environment variables:

```bash
IBKR_GATEWAY_URL=http://paper-gateway:4003
```

## Development

### Project Structure

```
paper-gateway/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── models.py            # Data models
│   ├── simulation/
│   │   ├── price_simulator.py
│   │   ├── execution_simulator.py
│   │   ├── market_hours.py
│   │   └── commission.py
│   ├── storage/
│   │   ├── mongo.py
│   │   └── state.py
│   └── api/
│       └── (endpoint modules)
├── tests/
│   └── (test files)
├── Dockerfile
├── requirements.txt
└── README.md
```

### Running Tests

```bash
pytest tests/ -v
```

## Troubleshooting

### Gateway not starting

```bash
# Check MongoDB connection
docker logs spreadpilot-mongodb

# Check gateway logs
docker logs spreadpilot-paper-gateway

# Verify MongoDB URI
docker exec spreadpilot-paper-gateway env | grep MONGO
```

### Orders rejected

Check:
- Market hours (9:30 AM - 4:00 PM ET, weekdays)
- Account balance (BUY orders require sufficient funds)
- Position exists (SELL orders require existing position)

### Prices not updating

Prices update on each request using random walk simulation. Reset prices:

```bash
curl -X POST http://localhost:4003/api/v1/admin/reset
```

## License

Part of SpreadPilot project.

# Issue #70: Paper Trading Mode Using Mock IBKR Gateway

**Status**: 🔄 In Progress
**Priority**: MEDIUM
**Effort**: 5-7 days
**Date**: 2025-11-11

---

## Problem

Currently, SpreadPilot has:
- **Production**: Real IBKR Gateway for live/paper trading via TWS
- **E2E Testing**: Basic mock IBKR gateway in `tests/e2e/Dockerfile.ibkr-mock`

**Gap**: The E2E mock is too simple for realistic paper trading:
- No price simulation with volatility
- No slippage or commission simulation
- No market hours simulation
- No persistent state storage
- Not integrated with main docker-compose
- No dashboard visibility

**Need**: Full-featured paper trading mode that simulates real market conditions without requiring IBKR credentials or capital.

---

## Solution Design

### Architecture

```
┌─────────────────┐
│  Trading Bot    │
│                 │
│  IB_GATEWAY_URL │────┐
└─────────────────┘    │
                       ├──> (mode switch) ──┐
┌─────────────────┐    │                    │
│  Admin API      │────┘                    │
└─────────────────┘                         │
                                            ▼
                     ┌──────────────────────────────┐
                     │   Paper Mode (NEW)           │
                     │                              │
                     │  - Mock IBKR Gateway         │
                     │  - Price Simulation          │
                     │  - Slippage/Commission       │
                     │  - Market Hours              │
                     │  - Persistent State (MongoDB)│
                     │  - Performance Tracking      │
                     └──────────────────────────────┘
                                   │
                                   ▼
                     ┌──────────────────────────────┐
                     │   Live Mode (Existing)       │
                     │                              │
                     │  - Real IBKR Gateway         │
                     │  - Real Market Data          │
                     │  - Actual Execution          │
                     └──────────────────────────────┘
```

### Implementation Strategy

**Option Chosen**: Enhance existing mock to production-grade paper trading service

**Why**:
1. ✅ Reuses existing E2E infrastructure
2. ✅ Already has basic order/position logic
3. ✅ Can be gradually enhanced
4. ✅ Docker profile approach (like MailHog)

---

## Implementation Plan

### Phase 1: Enhanced Mock Gateway (2-3 days)

#### 1.1 Realistic Price Simulation
- Market data provider integration (or mock price feeds)
- Volatility simulation (Black-Scholes for options)
- Bid/ask spread simulation
- Time-of-day volatility patterns

#### 1.2 Order Execution Simulation
- Slippage modeling (based on order size)
- Commission calculation (IBKR fee schedule)
- Partial fills for large orders
- Order rejection scenarios (margin, market hours)

#### 1.3 Market Hours Simulation
- NYSE/NASDAQ trading hours (9:30-16:00 ET)
- Pre-market/after-hours handling
- Holiday calendar
- Extended hours option trading restrictions

#### 1.4 Persistent State
- MongoDB integration for:
  - Orders history
  - Positions state
  - Account balances
  - Trade P&L
  - Performance metrics

### Phase 2: Production Integration (1-2 days)

#### 2.1 Docker Compose Integration
- Add `paper-gateway` service to docker-compose.yml
- Docker profile approach: `--profile paper`
- Environment variable: `PAPER_MODE=true`
- Service dependencies and health checks

#### 2.2 Configuration
- New env vars:
  - `PAPER_MODE_ENABLED` (boolean)
  - `PAPER_INITIAL_BALANCE` (default: $100,000)
  - `PAPER_COMMISSION_RATE` (default: IBKR rates)
  - `PAPER_SLIPPAGE_BPS` (basis points)
  - `PAPER_DATA_SOURCE` (mock/historical/live)

#### 2.3 Service Discovery
- Trading bot auto-detects paper vs live mode
- Admin API routes paper mode requests
- Fallback logic if paper gateway unavailable

### Phase 3: Dashboard Integration (1-2 days)

#### 3.1 Mode Indicator
- Visual badge: "PAPER MODE" or "LIVE MODE"
- Distinct color schemes (paper = blue/green, live = red/orange)
- Mode displayed in:
  - Header
  - Login screen
  - Position lists
  - Trade history

#### 3.2 Performance Comparison
- Side-by-side paper vs live metrics
- Paper trading leaderboard (if multi-user)
- Performance reports:
  - Sharpe ratio
  - Max drawdown
  - Win rate
  - Average P&L

#### 3.3 Paper-Specific Features
- Reset paper account button
- Adjust paper balance
- Fast-forward time (for testing)
- Scenario testing (crash simulation)

### Phase 4: Testing & Documentation (1 day)

#### 4.1 Testing
- Unit tests for price simulation
- Unit tests for slippage/commission
- Integration tests for paper mode flow
- E2E tests comparing paper vs existing mock

#### 4.2 Documentation
- `docs/PAPER_TRADING_MODE.md`
  - Quick start guide
  - Configuration reference
  - Simulation models explained
  - Limitations and caveats
  - Migration guide (paper → live)

---

## File Structure

### New Files
```
paper-gateway/
├── Dockerfile
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app
│   ├── config.py                  # Configuration
│   ├── models.py                  # Data models
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── price_simulator.py     # Market price simulation
│   │   ├── execution_simulator.py # Order execution logic
│   │   ├── market_hours.py        # Trading hours logic
│   │   └── commission.py          # Fee calculation
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── mongo.py               # MongoDB integration
│   │   └── state.py               # State management
│   └── api/
│       ├── __init__.py
│       ├── orders.py              # Order endpoints
│       ├── positions.py           # Position endpoints
│       ├── account.py             # Account endpoints
│       └── admin.py               # Admin endpoints (reset, etc.)
├── tests/
│   ├── __init__.py
│   ├── test_price_simulator.py
│   ├── test_execution_simulator.py
│   ├── test_market_hours.py
│   └── test_api.py
└── README.md
```

### Modified Files
```
docker-compose.yml                  # Add paper-gateway service
.env.dev.template                   # Add paper mode env vars
trading-bot/app/config.py           # Add PAPER_MODE config
frontend/src/types/trading.ts      # Add mode type
frontend/src/contexts/TradingModeContext.tsx  # NEW
frontend/src/components/layout/DashboardLayout.tsx  # Mode indicator
frontend/src/pages/DashboardPage.tsx           # Mode display
docs/PAPER_TRADING_MODE.md          # NEW documentation
```

---

## Technical Details

### Price Simulation

**For Stocks (QQQ)**:
```python
def simulate_price(symbol: str, base_price: float, volatility: float = 0.02):
    """Simulate realistic stock price with volatility."""
    # Geometric Brownian Motion
    dt = 1.0 / (252 * 6.5 * 60)  # 1 minute timestep
    drift = 0.0  # Assume zero drift for short-term
    noise = np.random.normal(0, 1)
    dS = base_price * (drift * dt + volatility * np.sqrt(dt) * noise)
    return base_price + dS
```

**For Options**:
```python
def simulate_option_price(
    underlying_price: float,
    strike: float,
    expiry: datetime,
    option_type: str,  # CALL or PUT
    volatility: float = 0.25,
    risk_free_rate: float = 0.04
):
    """Black-Scholes option pricing."""
    # Use QuantLib or py_vollib for pricing
    return black_scholes(...)
```

### Slippage Model

```python
def calculate_slippage(order_quantity: int, liquidity: float = 1000000):
    """Calculate realistic slippage based on order size."""
    # Square root model
    market_impact_bps = 10 * np.sqrt(order_quantity / liquidity)
    # Cap at 20 bps
    return min(market_impact_bps, 20)
```

### Commission Model

```python
def calculate_commission(order_quantity: int, price: float, asset_type: str):
    """IBKR commission schedule."""
    if asset_type == "STOCK":
        # $0.005 per share, min $1, max 1% of trade value
        commission = max(1.0, min(order_quantity * 0.005, price * order_quantity * 0.01))
    elif asset_type == "OPTION":
        # $0.65 per contract, with volume tiers
        commission = order_quantity * 0.65
    return commission
```

### Market Hours Logic

```python
from datetime import time
import pytz

def is_market_open(dt: datetime = None):
    """Check if market is open."""
    if dt is None:
        dt = datetime.now(pytz.timezone('US/Eastern'))

    # Weekend
    if dt.weekday() >= 5:
        return False

    # Market hours: 9:30 AM - 4:00 PM ET
    market_open = time(9, 30)
    market_close = time(16, 0)

    current_time = dt.time()
    return market_open <= current_time <= market_close
```

---

## Configuration Example

### docker-compose.yml

```yaml
  paper-gateway:
    build:
      context: ./paper-gateway
      dockerfile: Dockerfile
    container_name: spreadpilot-paper-gateway
    environment:
      - MONGO_URI=mongodb://${MONGO_INITDB_ROOT_USERNAME}:${MONGO_INITDB_ROOT_PASSWORD}@mongodb:27017
      - MONGO_DB_NAME=spreadpilot_paper
      - PAPER_INITIAL_BALANCE=${PAPER_INITIAL_BALANCE:-100000}
      - PAPER_COMMISSION_RATE=${PAPER_COMMISSION_RATE:-0.005}
      - PAPER_SLIPPAGE_BPS=${PAPER_SLIPPAGE_BPS:-5}
      - PAPER_VOLATILITY=${PAPER_VOLATILITY:-0.02}
      - MARKET_DATA_SOURCE=${MARKET_DATA_SOURCE:-mock}
      - LOG_LEVEL=INFO
    ports:
      - "4003:4003"  # Paper gateway port
    networks:
      - spreadpilot-network
    depends_on:
      - mongodb
    restart: unless-stopped
    profiles:
      - paper  # Only start with --profile paper
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4003/health"]
      interval: 10s
      timeout: 5s
      retries: 3
```

### Environment Variables

```bash
# Paper Trading Mode
PAPER_MODE_ENABLED=true
PAPER_INITIAL_BALANCE=100000
PAPER_COMMISSION_RATE=0.005  # $0.005 per share
PAPER_SLIPPAGE_BPS=5         # 5 basis points
PAPER_VOLATILITY=0.02        # 2% daily volatility
MARKET_DATA_SOURCE=mock      # mock, historical, or live

# Override IBKR gateway URL when in paper mode
IB_GATEWAY_HOST=paper-gateway
IB_GATEWAY_PORT=4003
```

---

## API Compatibility

Paper gateway implements same endpoints as real IBKR Gateway:

### Orders
- `POST /api/v1/orders` - Place order
- `GET /api/v1/orders/{order_id}` - Get order status
- `DELETE /api/v1/orders/{order_id}` - Cancel order

### Positions
- `GET /api/v1/positions` - Get all positions
- `POST /api/v1/positions/{symbol}/close` - Close position

### Account
- `GET /api/v1/account` - Get account info
- `GET /api/v1/account/summary` - Account summary

### Paper-Specific (Admin)
- `POST /api/v1/admin/reset` - Reset paper account
- `PUT /api/v1/admin/balance` - Adjust paper balance
- `GET /api/v1/admin/performance` - Get performance metrics
- `POST /api/v1/admin/scenario` - Run scenario test

---

## Benefits

### Development
- ✅ No IBKR credentials needed
- ✅ No TWS/Gateway installation required
- ✅ Fast iteration (no real market delays)
- ✅ Reproducible testing scenarios

### User Onboarding
- ✅ Risk-free strategy testing
- ✅ Learn platform without capital
- ✅ Build confidence before going live
- ✅ Compare paper vs live performance

### Testing & QA
- ✅ Automated E2E tests without market dependency
- ✅ Scenario testing (crash, volatility spike)
- ✅ Performance regression testing
- ✅ Load testing with simulated orders

---

## Limitations & Caveats

### Not Simulated (Yet)
- ❌ Complex order types (bracket, OCO)
- ❌ Corporate actions (splits, dividends)
- ❌ Overnight interest/fees
- ❌ Liquidity constraints (low volume stocks)
- ❌ Exchange-specific rules

### Known Differences from Live
- ⚠️ No bid/ask queue dynamics
- ⚠️ Simplified slippage model
- ⚠️ Mock volatility (not real market data)
- ⚠️ No exchange outages/delays

**Documentation will clearly state**: *Paper trading results may differ significantly from live trading due to simulation limitations.*

---

## Migration Path

### Paper → Live

1. **Preparation**:
   - Review paper trading performance
   - Verify strategy profitability
   - Check risk metrics (drawdown, Sharpe)

2. **Configuration**:
   - Set `PAPER_MODE_ENABLED=false`
   - Update `IB_GATEWAY_HOST` to real gateway
   - Configure IBKR credentials
   - Start with small position sizes

3. **Monitoring**:
   - Compare paper vs live performance
   - Adjust strategy based on slippage differences
   - Monitor commission impact
   - Track market impact

---

## Success Criteria

- [ ] Paper gateway starts with `docker-compose --profile paper up`
- [ ] Realistic price simulation with configurable volatility
- [ ] Order slippage and commission calculation
- [ ] Market hours enforcement
- [ ] Persistent state in MongoDB
- [ ] Dashboard displays "PAPER MODE" indicator
- [ ] Performance metrics tracked and displayed
- [ ] Reset functionality works
- [ ] Integration tests pass
- [ ] Documentation complete

---

## Timeline

**Total Estimated Effort**: 5-7 days

| Phase | Task | Effort |
|-------|------|--------|
| 1 | Enhanced Mock Gateway | 2-3 days |
| 2 | Production Integration | 1-2 days |
| 3 | Dashboard Integration | 1-2 days |
| 4 | Testing & Documentation | 1 day |

---

## Protocol

Following **LIFECYCLE-ORCHESTRATOR-ENHANCED-PROTO.yaml**:
- ✅ Phase 1: Discover & Frame (This document)
- ⏳ Phase 2: Design (Detailed technical design)
- ⏳ Phase 3: Build & Validate
- ⏳ Phase 4: Test & Review
- ⏳ Phase 5: Release & Launch
- ⏳ Phase 6: Operate & Learn

---

**Next Steps**:
1. Review implementation plan
2. Decide on market data source (mock vs historical)
3. Begin Phase 1.1: Price simulation implementation

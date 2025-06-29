# 🤖 SpreadPilot Trading Bot

> ⚡ **Core trading engine** that executes QQQ options strategies with advanced order management and real-time position monitoring

The Trading Bot is the heart of SpreadPilot, responsible for automated strategy execution, position management, and real-time P&L calculations with sophisticated risk controls.

## 🎯 Core Responsibilities

### 📊 **Strategy Execution**
- 🔗 **IBKR Integration**: Direct connection to Interactive Brokers Gateway
- 📈 **Signal Processing**: Google Sheets signal polling and validation
- ⚡ **Order Execution**: Advanced limit-ladder execution with margin checks
- 🎯 **Multi-Follower**: Isolated execution for multiple trading accounts

### 🛡️ **Risk Management**
- ⚠️ **Time Value Monitor**: Automatic liquidation when TV <= $0.10
  - 60-second monitoring cycle for all open QQQ option positions
  - Calculates time value (market price - intrinsic value)
  - Publishes SAFE/RISK/CRITICAL alerts to Redis stream
  - Auto-closes positions via market orders when TV <= $0.10
- 📋 **Position Tracking**: Real-time position monitoring and assignment handling
- 💰 **P&L Calculation**: 30-second MTM updates with PostgreSQL storage
- 🔒 **Margin Validation**: Pre-trade margin checks and position limits
- 🚨 **Redis Alert Publishing**: Real-time alerts to Redis stream on execution failures

### 🔄 **Real-time Operations**
- ⏱️ **Live Monitoring**: Continuous position and market data updates
- 🚨 **Alert Generation**: Automated notifications for critical events
- 📊 **Data Pipeline**: Real-time data flow to PostgreSQL and MongoDB
- 🎛️ **API Interface**: RESTful endpoints for external control

---

## 🏗️ Architecture

### 🧩 **Service Components**

| Component | Purpose | Location |
|-----------|---------|----------|
| 🎛️ **TradingService** | Main orchestrator | `app/service/base.py` |
| 🏦 **IBKR Client** | Interactive Brokers integration | `app/service/ibkr.py` |
| 📡 **Signal Processor** | Google Sheets polling & signal validation | `app/service/signals.py` |
| 📋 **Position Manager** | Position tracking & assignment handling | `app/service/positions.py` |
| ⚠️ **Time Value Monitor** | Risk management & liquidation | `app/service/time_value_monitor.py` |
| 💰 **P&L Service** | Real-time P&L calculation | `app/service/pnl_service.py` |
| 🔔 **Alert Manager** | Notification generation | `app/service/alerts.py` |
| ⚡ **Executor** | Order execution with Redis alerts | `app/service/executor.py` |

### 📊 **Data Flow**

```mermaid
graph LR
    A[📊 Google Sheets] --> B[📡 Signal Processor]
    B --> C[🤖 Trading Service]
    C --> D[🏦 IBKR Gateway]
    D --> E[📋 Position Manager]
    E --> F[💰 P&L Service]
    F --> G[🐘 PostgreSQL]
    E --> H[🍃 MongoDB]
    C --> I[🔔 Alert Manager]
    E --> J[⚠️ Time Value Monitor]
    J --> K[🔴 Redis Alerts]
    J --> D
```

---

## 🚀 API Endpoints

### 🔍 **Monitoring**

| Method | Endpoint | Description |
|--------|----------|-------------|
| 📊 GET | `/health` | Service health check |
| 📈 GET | `/status` | Detailed trading bot status |

### 🎯 **Trading Control**

| Method | Endpoint | Description |
|--------|----------|-------------|
| ⚡ POST | `/trade/signal` | Execute manual trade signal |
| ❌ POST | `/close/{follower_id}` | Close positions for specific follower |
| 🚫 POST | `/close/all` | Emergency close all positions |

### 📋 **API Examples**

#### Execute Manual Signal
```bash
curl -X POST "http://localhost:8001/trade/signal" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "vertical_spread",
    "qty_per_leg": 10,
    "strike_long": 445.0,
    "strike_short": 450.0,
    "follower_id": "follower123"
  }'
```

#### Check Trading Status
```bash
curl "http://localhost:8001/status"
```

---

## 🛠️ Development

### 📋 Prerequisites

- 🐍 **Python 3.11+** - Runtime environment
- 🏦 **IB Gateway/TWS** - Interactive Brokers connection
- 📊 **Google Sheets API** - Strategy signal source
- 🐘 **PostgreSQL** - P&L data storage
- 🍃 **MongoDB** - Trading data and configuration
- 🔐 **HashiCorp Vault** - Credential management (optional)
- 🔴 **Redis** - Alert stream publishing

### 🔧 Local Setup

```bash
# 1️⃣ Install dependencies
cd trading-bot/
pip install -e ../spreadpilot-core
pip install -r requirements.txt

# 2️⃣ Set up environment
cp .env.template .env
# Edit .env with your configuration

# 3️⃣ Start IB Gateway
# Configure IB Gateway with paper trading account

# 4️⃣ Run the service
uvicorn app.main:app --reload --port 8001
```

### ⚙️ Configuration

Key environment variables:

```bash
# 🏦 Interactive Brokers
IB_GATEWAY_HOST=127.0.0.1
IB_GATEWAY_PORT=4002  # 4001 for live, 4002 for paper
IB_CLIENT_ID=1
IB_TRADING_MODE=paper

# 📊 Google Sheets
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/...
GOOGLE_SHEETS_API_KEY=your_api_key

# 🎯 Trading Parameters
MIN_PRICE=0.70
PRICE_INCREMENT=0.01
MAX_ATTEMPTS=10
TIMEOUT_SECONDS=5

# ⏱️ Polling Intervals
POLLING_INTERVAL_SECONDS=1.0
POSITION_CHECK_INTERVAL_SECONDS=60.0

# 🔔 Alerts
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
SENDGRID_API_KEY=your_sendgrid_key
ADMIN_EMAIL=admin@example.com

# 🔴 Redis
REDIS_URL=redis://localhost:6379

# 🔐 HashiCorp Vault (for secrets)
VAULT_ENABLED=true
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=your_vault_token
VAULT_MOUNT_POINT=secret
```

---

## 🐳 Docker Deployment

### 🏗️ Build & Run

```bash
# 🏗️ Build the image
docker build -t spreadpilot-trading-bot .

# 🚀 Run locally
docker run -p 8001:8001 --env-file .env spreadpilot-trading-bot

# 📋 Check container
docker ps | grep trading-bot
```

### ☁️ Cloud Deployment

```bash
# 🏗️ Build for GCR
docker build -t gcr.io/your-project/trading-bot:latest .

# 📤 Push to registry
docker push gcr.io/your-project/trading-bot:latest

# 🚀 Deploy to Cloud Run
gcloud run deploy trading-bot \
  --image gcr.io/your-project/trading-bot:latest \
  --platform managed \
  --port 8001
```

---

## 🧪 Testing & Development

### 🧪 Running Tests

```bash
# 🧪 All tests
pytest tests/

# ⚡ Unit tests only
pytest tests/unit/

# 🔗 Integration tests
pytest tests/integration/

# 📊 Coverage report
pytest --cov=app --cov-report=html
```

### 🎨 Code Quality

```bash
# 🎨 Format code
black app/ tests/

# 📏 Linting
flake8 app/ tests/

# 🔍 Type checking
mypy app/
```

### 🐛 Debugging

```bash
# 📄 View logs
docker logs trading-bot

# 🔍 Debug mode
LOG_LEVEL=DEBUG uvicorn app.main:app --reload

# 🏦 Test IBKR connection
python -c "
from app.service.ibkr import IBKRClient
client = IBKRClient()
print('IBKR Connected:', client.is_connected())
"
```

---

## ⚡ Import Pattern

The trading bot uses a hyphenated directory name which requires special import handling:

```python
# ✅ Correct import method
import importlib

# Import modules
trading_service = importlib.import_module('trading-bot.app.service.base')
signal_processor = importlib.import_module('trading-bot.app.service.signals')

# Access classes
TradingService = trading_service.TradingService
SignalProcessor = signal_processor.SignalProcessor
```

---

## 🔧 Troubleshooting

### 🏦 **IBKR Connection Issues**

```bash
# ✅ Check IB Gateway status
curl http://localhost:5000/v1/api/portal/sso/validate

# ✅ Verify port configuration
netstat -an | grep 4002

# ✅ Test connection
telnet localhost 4002
```

### 📊 **Google Sheets Issues**

- ✅ Verify service account has Sheet access
- ✅ Check API key permissions
- ✅ Validate Sheet URL format
- ✅ Test with `gspread` library directly

### 🗄️ **Database Connection**

```bash
# 🐘 Test PostgreSQL
psql postgresql://user:pass@localhost:5432/spreadpilot_pnl

# 🍃 Test MongoDB
mongosh mongodb://user:pass@localhost:27017/spreadpilot_admin
```

### 📞 **Getting Help**

- 📄 Check logs: `docker logs trading-bot`
- 🔍 Enable debug: `LOG_LEVEL=DEBUG`
- 📊 Monitor metrics: `curl localhost:8001/metrics`
- 🎛️ Check dashboard: Admin UI at port 8080

---

## 🎯 Key Features

### ⚡ **Advanced Order Execution**
- 🎯 Limit-ladder strategy with dynamic pricing
- 🔍 Pre-trade margin validation
- ⏱️ Configurable timeout and retry logic
- 📊 Real-time fill monitoring
- 🚨 Redis alert publishing on execution failures:
  - **NO_MARGIN**: Insufficient margin for trade
  - **MID_TOO_LOW**: MID price below threshold
  - **LIMIT_REACHED**: All ladder attempts exhausted
  - **GATEWAY_UNREACHABLE**: IB connection/rejection errors

### 🛡️ **Risk Management**
- ⚠️ Time value monitoring (TV < $0.10 liquidation)
- 📋 Position limit enforcement
- 💰 Real-time P&L tracking
- 🚨 Automated alert generation

### 🔄 **Multi-Follower Support**
- 👥 Isolated execution per follower
- 🔐 Vault-based credential management
- 📊 Individual P&L tracking
- ⚙️ Configurable parameters per follower

---

<div align="center">

**🤖 Powering automated options trading with precision and reliability**

[📖 API Docs](./docs/api.md) • [🏗️ Architecture](./docs/architecture.md) • [🔧 Configuration](./docs/configuration.md)

</div>
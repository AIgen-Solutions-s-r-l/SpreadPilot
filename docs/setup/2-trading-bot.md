# 🤖 Trading Bot Setup Guide for SpreadPilot

This comprehensive guide provides detailed instructions for setting up the Trading Bot, the core service of the SpreadPilot system that executes automated trading strategies.

## 📋 Table of Contents

- [Prerequisites](#-prerequisites)
- [Understanding the Trading Bot](#-understanding-the-trading-bot)
- [Docker Configuration](#-docker-configuration)
- [Environment Setup](#-environment-setup)
- [Google Sheets Setup](#-google-sheets-setup)
- [Starting the Trading Bot](#-starting-the-trading-bot)
- [Verification](#-verification)
- [API Testing](#-api-testing)
- [Troubleshooting](#-troubleshooting)
- [Performance Optimization](#-performance-optimization)
- [Security Considerations](#-security-considerations)

## 🔧 Prerequisites

- ✅ Docker and Docker Compose installed
- ✅ MongoDB service running ([see MongoDB Setup](./0-mongodb.md))
- ✅ IB Gateway service running ([see IB Gateway Setup](./1-ib-gateway.md))
- ✅ Google Cloud service account with Sheets API access
- ✅ Google Sheet with trading signals
- ✅ SendGrid account for email alerts (optional)
- ✅ Telegram bot for instant notifications (optional)

## 🎯 Understanding the Trading Bot

The Trading Bot is the heart of SpreadPilot, responsible for automated trading operations.

### Core Responsibilities

| Function | Description | Frequency |
|----------|-------------|-----------|
| **Signal Processing** | Polls Google Sheets for trading signals | Every 1 second |
| **Order Execution** | Places orders via IB Gateway | On signal detection |
| **Position Monitoring** | Tracks open positions and P&L | Every 60 seconds |
| **P&L Calculation** | Real-time MTM calculations with commission tracking | Every 30 seconds |
| **Assignment Detection** | Monitors for option assignments | Every 60 seconds |
| **Alert Generation** | Creates alerts for important events | As needed |
| **Follower Management** | Manages copy-trading accounts | Real-time |

### Architecture Overview

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Google Sheets  │────▶│ Trading Bot  │────▶│ IB Gateway  │
└─────────────────┘     └──────────────┘     └─────────────┘
                               │
                        ┌──────┴──────┐
                        ▼             ▼
                   ┌─────────┐  ┌──────────┐
                   │ MongoDB │  │  Alerts  │
                   └─────────┘  └──────────┘
```

### P&L Service Integration

The Trading Bot integrates with the P&L service from `spreadpilot-core` for real-time profit/loss tracking:

| Component | Purpose | Details |
|-----------|---------|---------|
| **MTM Calculations** | Mark-to-market P&L every 30 seconds | Updates `pnl_intraday` table |
| **Daily Rollups** | Consolidated daily P&L at 16:30 ET | Creates `pnl_daily` records |
| **Monthly Rollups** | Monthly summaries at 00:10 ET on 1st | Updates `pnl_monthly` with commission |
| **Commission Logic** | `commission = pct * pnl_month` if `pnl_month > 0` | 20% default commission rate |

The P&L service uses PostgreSQL for storage and provides real-time data to the admin dashboard.

## 🐳 Docker Configuration

### Container Setup

The Trading Bot configuration in `docker-compose.yml`:

```yaml
trading-bot:
  build:
    context: .
    dockerfile: trading-bot/Dockerfile
  container_name: spreadpilot-trading-bot
  environment:
    # MongoDB Configuration
    - MONGODB_URI=mongodb://spreadpilot_user:${MONGODB_PASSWORD}@mongodb:27017/spreadpilot
    
    # IB Gateway Configuration
    - IB_GATEWAY_HOST=ib-gateway
    - IB_GATEWAY_PORT=4002
    - IB_CLIENT_ID=1
    
    # Google Sheets Configuration
    - GOOGLE_SHEET_URL=${GOOGLE_SHEET_URL}
    - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json
    
    # Alert Configuration
    - SENDGRID_API_KEY=${SENDGRID_API_KEY}
    - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
    - ADMIN_EMAIL=${ADMIN_EMAIL}
    
    # Trading Parameters
    - MIN_PRICE=${MIN_PRICE:-0.70}
    - PRICE_INCREMENT=${PRICE_INCREMENT:-0.01}
    - MAX_ATTEMPTS=${MAX_ATTEMPTS:-10}
    - TIMEOUT_SECONDS=${TIMEOUT_SECONDS:-5}
    - POLLING_INTERVAL_SECONDS=${POLLING_INTERVAL_SECONDS:-1.0}
    - POSITION_CHECK_INTERVAL_SECONDS=${POSITION_CHECK_INTERVAL_SECONDS:-60.0}
    
    # Observability
    - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
    - LOG_LEVEL=${LOG_LEVEL:-INFO}
  volumes:
    - ./credentials:/app/credentials:ro
    - ./logs/trading-bot:/app/logs
  depends_on:
    mongodb:
      condition: service_healthy
    ib-gateway:
      condition: service_healthy
  ports:
    - "8081:8080"
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

## 🔐 Environment Setup

### 1️⃣ Core Configuration

Add to your `.env` file:

```bash
# Google Sheets Configuration
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
GOOGLE_SHEET_NAME="Trading Signals"  # Optional, defaults to first sheet

# MongoDB (from previous setup)
MONGODB_PASSWORD=your_mongodb_password

# Alert Configuration
SENDGRID_API_KEY=SG.your_sendgrid_api_key
ADMIN_EMAIL=alerts@yourdomain.com
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-1001234567890
```

### 2️⃣ Trading Parameters

Configure trading behavior:

```bash
# Price Limits
MIN_PRICE=0.70              # Minimum option price
MAX_PRICE=5.00              # Maximum option price
PRICE_INCREMENT=0.01        # Price adjustment increment

# Execution Settings
MAX_ATTEMPTS=10             # Max order attempts
TIMEOUT_SECONDS=5           # Order timeout
ORDER_DELAY_MS=100          # Delay between orders

# Monitoring Intervals
POLLING_INTERVAL_SECONDS=1.0           # Sheet polling frequency
POSITION_CHECK_INTERVAL_SECONDS=60.0   # Position check frequency
ASSIGNMENT_CHECK_HOUR=16               # Daily assignment check time (EST)
```

### 3️⃣ Google Cloud Credentials

1. **Create Service Account:**
   ```bash
   # Using Google Cloud Console
   gcloud iam service-accounts create spreadpilot-trading \
       --display-name="SpreadPilot Trading Bot"
   
   # Grant necessary permissions
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
       --member="serviceAccount:spreadpilot-trading@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/sheets.viewer"
   ```

2. **Generate Key File:**
   ```bash
   # Create credentials directory
   mkdir -p credentials
   
   # Generate key
   gcloud iam service-accounts keys create \
       credentials/service-account.json \
       --iam-account=spreadpilot-trading@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

3. **Share Google Sheet:**
   - Open your Google Sheet
   - Click "Share"
   - Add the service account email
   - Grant "Viewer" access

## 📊 Google Sheets Setup

### 1️⃣ Sheet Structure

Create a Google Sheet with the following columns:

| Column | Name | Type | Example | Description |
|--------|------|------|---------|-------------|
| A | Strategy | Text | "BearCallSpread" | Strategy identifier |
| B | Quantity | Number | 2 | Contracts per leg |
| C | Long Strike | Number | 440 | Long option strike |
| D | Short Strike | Number | 445 | Short option strike |
| E | Expiry | Date | "2024-01-19" | Option expiration |
| F | Status | Text | "PENDING" | Signal status |
| G | Timestamp | DateTime | Auto | Signal timestamp |

### 2️⃣ Example Sheet Setup

```
| Strategy | Quantity | Long Strike | Short Strike | Expiry | Status | Timestamp |
|----------|----------|-------------|--------------|--------|--------|-----------|
| QQQ_BCS  | 2        | 440         | 445          | 2024-01-19 | PENDING | 2024-01-15 09:30:00 |
| SPY_BCS  | 1        | 485         | 490          | 2024-01-19 | PENDING | 2024-01-15 09:31:00 |
```

### 3️⃣ Sheet Permissions

```bash
# Make sheet accessible to service account
# In Google Sheets: Share → Add service account email → Viewer access
```

## 🚀 Starting the Trading Bot

### 1️⃣ Pre-flight Checks

```bash
# Verify dependencies are running
docker-compose ps | grep -E "(mongodb|ib-gateway)"

# Check credentials
ls -la credentials/service-account.json

# Validate environment
docker-compose config | grep -A20 trading-bot
```

### 2️⃣ Start the Service

```bash
# Start Trading Bot
docker-compose up -d trading-bot

# Monitor startup logs
docker-compose logs -f trading-bot --tail 100
```

### 3️⃣ Verify Startup

Look for these success indicators:

```
INFO: Starting Trading Bot v1.0.0
INFO: Connected to MongoDB at mongodb:27017
INFO: Connected to IB Gateway at ib-gateway:4002
INFO: Authenticated with Google Sheets API
INFO: Loaded 3 active followers
INFO: Starting signal polling (interval: 1.0s)
INFO: Trading Bot ready for operations
```

## ✅ Verification

### 🔍 Container Health

```bash
# Check container status
docker ps --filter name=trading-bot --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Verify health endpoint
curl -s http://localhost:8081/health | jq
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 120,
  "components": {
    "mongodb": "connected",
    "ib_gateway": "connected",
    "google_sheets": "connected"
  }
}
```

### 📊 Service Status

```bash
# Get detailed status
curl -s http://localhost:8081/status | jq
```

Expected response:
```json
{
  "status": "running",
  "timestamp": "2024-01-15T14:30:00Z",
  "services": {
    "ibkr_connected": true,
    "sheets_connected": true,
    "mongodb_connected": true
  },
  "metrics": {
    "active_followers": 3,
    "open_positions": 5,
    "signals_processed_today": 12,
    "orders_executed_today": 10
  },
  "last_signal_check": "2024-01-15T14:29:59Z",
  "last_position_check": "2024-01-15T14:29:00Z"
}
```

## 🧪 API Testing

### 1️⃣ Test Signal Processing

```bash
# Manually trigger signal processing
curl -X POST http://localhost:8081/api/v1/signals/process \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "TEST_STRATEGY",
    "quantity": 1,
    "long_strike": 440,
    "short_strike": 445,
    "expiry": "2024-01-19"
  }'
```

### 2️⃣ Test Order Execution

```bash
# Test order placement (paper trading only)
curl -X POST http://localhost:8081/api/v1/orders/test \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "QQQ",
    "quantity": 1,
    "order_type": "LMT",
    "limit_price": 1.50,
    "action": "BUY"
  }'
```

### 3️⃣ Get Active Positions

```bash
# List all positions
curl -s http://localhost:8081/api/v1/positions | jq

# Get positions for specific follower
curl -s http://localhost:8081/api/v1/positions?follower_id=FOLLOWER001 | jq
```

## 🔧 Troubleshooting

### 🚫 Common Issues

#### Google Sheets Connection Failed

**Symptoms:** 
- Error: "Failed to connect to Google Sheets"
- No signals being detected

**Solutions:**
```bash
# 1. Verify credentials
docker exec spreadpilot-trading-bot ls -la /app/credentials/

# 2. Test Google Sheets API
docker exec spreadpilot-trading-bot python -c "
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

creds = service_account.Credentials.from_service_account_file(
    '/app/credentials/service-account.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)
service = build('sheets', 'v4', credentials=creds)
print('✅ Google Sheets API connected')
"

# 3. Check sheet permissions
# Ensure service account email has access to the sheet
```

#### IB Gateway Connection Lost

**Symptoms:**
- Error: "Lost connection to IB Gateway"
- Orders not being executed

**Solutions:**
```bash
# 1. Check IB Gateway health
curl http://localhost:4002/health

# 2. Restart connection
curl -X POST http://localhost:8081/api/v1/ibkr/reconnect

# 3. Check for account locks
docker logs spreadpilot-ib-gateway --tail 50 | grep -i "lock\|fail"
```

#### High Memory Usage

**Symptoms:**
- Container using >1GB RAM
- Slow response times

**Solutions:**
```python
# Add to trading bot configuration
MEMORY_LIMIT=1g
MEMORY_RESERVATION=512m

# Enable garbage collection tuning
PYTHON_GC_THRESHOLD="700,10,10"
```

### 📊 Debug Mode

Enable detailed logging:

```bash
# Set debug environment
echo "LOG_LEVEL=DEBUG" >> .env
echo "DEBUG_MODE=true" >> .env

# Restart with debug logging
docker-compose up -d trading-bot
docker-compose logs -f trading-bot
```

## ⚡ Performance Optimization

### 1️⃣ Database Optimization

```python
# Add connection pooling
MONGODB_MIN_POOL_SIZE=10
MONGODB_MAX_POOL_SIZE=50
MONGODB_MAX_IDLE_TIME_MS=30000

# Enable compression
MONGODB_COMPRESSORS=snappy,zlib
```

### 2️⃣ Caching Strategy

```python
# Cache follower data
FOLLOWER_CACHE_TTL=300  # 5 minutes

# Cache position data
POSITION_CACHE_TTL=60   # 1 minute

# Cache market hours
MARKET_HOURS_CACHE_TTL=3600  # 1 hour
```

### 3️⃣ Rate Limiting

```python
# Configure rate limits
SHEETS_API_RATE_LIMIT=100  # requests per minute
IB_API_RATE_LIMIT=50       # requests per second
ORDER_RATE_LIMIT=10        # orders per second
```

## 🔒 Security Considerations

### 🛡️ Production Hardening

1. **API Security**
   ```yaml
   # Add API authentication
   environment:
     - API_KEY_REQUIRED=true
     - API_KEY=${TRADING_BOT_API_KEY}
   ```

2. **Network Isolation**
   ```yaml
   networks:
     - internal
   ports: []  # No external exposure in production
   ```

3. **Secret Management**
   ```bash
   # Use Google Secret Manager
   gcloud secrets create trading-bot-config --data-file=.env.production
   ```

4. **Audit Logging**
   ```python
   # Enable comprehensive audit logs
   AUDIT_LOG_ENABLED=true
   AUDIT_LOG_LEVEL=INFO
   AUDIT_LOG_RETENTION_DAYS=90
   ```

### 📊 Monitoring Setup

```yaml
# prometheus/alerts.yml
groups:
  - name: trading_bot
    rules:
      - alert: TradingBotDown
        expr: up{job="trading-bot"} == 0
        for: 2m
        
      - alert: NoSignalsProcessed
        expr: rate(signals_processed_total[5m]) == 0
        for: 10m
        
      - alert: HighErrorRate
        expr: rate(trading_errors_total[5m]) > 0.1
        for: 5m
```

## 🎯 Next Steps

After successfully setting up the Trading Bot:

1. ✅ Configure the [Admin API](./3-admin-api.md) for management interface
2. ✅ Set up [Watchdog Service](./4-watchdog.md) for monitoring
3. ✅ Configure [Alert Router](./5-alert-router.md) for notifications
4. ✅ Set up [Report Worker](./6-report-worker.md) for P&L reports

## 📚 Additional Resources

- [Trading Bot API Documentation](../api/trading-bot.md)
- [Google Sheets API Guide](https://developers.google.com/sheets/api)
- [IB API Reference](https://interactivebrokers.github.io/tws-api/)
- [SpreadPilot Architecture](../01-system-architecture.md)
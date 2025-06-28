# 💹 Interactive Brokers Gateway Setup Guide for SpreadPilot

This comprehensive guide covers the setup and configuration of the Interactive Brokers (IB) Gateway for the SpreadPilot trading system, including troubleshooting and best practices.

## 📋 Table of Contents

- [Prerequisites](#-prerequisites)
- [Understanding IB Gateway](#-understanding-ib-gateway)
- [Docker Configuration](#-docker-configuration)
- [Environment Setup](#-environment-setup)
- [Starting IB Gateway](#-starting-ib-gateway)
- [Verification](#-verification)
- [Testing Connection](#-testing-connection)
- [Troubleshooting](#-troubleshooting)
- [Security & Best Practices](#-security--best-practices)
- [Monitoring](#-monitoring)

## 🔧 Prerequisites

- ✅ Docker and Docker Compose installed
- ✅ MongoDB service running ([see MongoDB Setup](./0-mongodb.md))
- ✅ Interactive Brokers account (paper or live)
- ✅ Two-factor authentication app (if enabled on account)
- ✅ Basic understanding of trading concepts

## 🎯 Understanding IB Gateway

The Interactive Brokers Gateway is a lightweight application that provides programmatic access to IB's trading platform.

### Key Features

| Feature | Description | Purpose |
|---------|-------------|---------|
| **API Access** | RESTful/Socket interface | Programmatic trading |
| **Authentication** | Secure login handling | Account protection |
| **Order Management** | Order placement/modification | Trade execution |
| **Market Data** | Real-time/historical data | Strategy decisions |
| **Account Info** | Positions, balances, P&L | Portfolio management |

### Paper vs Live Trading

| Mode | Use Case | Credentials | Risk |
|------|----------|-------------|------|
| **Paper** | Development/Testing | Separate paper account | No real money |
| **Live** | Production trading | Live account credentials | Real money at risk |

## 🐳 Docker Configuration

### Container Setup

The IB Gateway runs in a Docker container defined in `docker-compose.yml`:

```yaml
ib-gateway:
  image: ghcr.io/gnzsnz/ib-gateway:latest
  container_name: spreadpilot-ib-gateway
  environment:
    - TWS_USERID=${IB_USERNAME}
    - TWS_PASSWORD=${IB_PASSWORD}
    - TRADING_MODE=paper  # Change to 'live' for production
    - TWS_ACCEPT_INCOMING=accept
    - TWS_LOGOFF_TIME=22:00
    - TWS_RESTART_TIME=06:00
    - TWS_TIMEZONE=America/New_York
  ports:
    - "4002:4002"  # API port
    - "5900:5900"  # VNC port (optional, for debugging)
  volumes:
    - ib_gateway_settings:/root/Jts
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "nc", "-z", "localhost", "4002"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

### Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `TWS_USERID` | IB account username | Required |
| `TWS_PASSWORD` | IB account password | Required |
| `TRADING_MODE` | `paper` or `live` | `paper` |
| `TWS_ACCEPT_INCOMING` | Auto-accept connections | `accept` |
| `TWS_LOGOFF_TIME` | Daily logout time | `22:00` |
| `TWS_RESTART_TIME` | Daily restart time | `06:00` |
| `TWS_TIMEZONE` | Gateway timezone | `America/New_York` |

## 🔐 Environment Setup

### 1️⃣ Create Environment Variables

Add to your `.env` file:

```bash
# Paper Trading Account
IB_USERNAME=paperXXXXXX
IB_PASSWORD=your_paper_password

# Optional: Two-Factor Authentication
IB_2FA_SECRET=your_2fa_secret_key  # If using TOTP

# Trading Configuration
IB_CLIENT_ID=1
IB_GATEWAY_PORT=4002
IB_TRADING_MODE=paper  # or 'live' for production
```

### 2️⃣ Paper Trading Account Setup

1. **Create Paper Account:**
   - Login to [IB Account Management](https://www.interactivebrokers.com/)
   - Navigate to Settings → Paper Trading
   - Create new paper trading account
   - Note the paper username (usually `paperXXXXXX`)

2. **Configure Paper Account:**
   ```bash
   # Paper account credentials format
   IB_USERNAME=paper123456  # Note the 'paper' prefix
   IB_PASSWORD=your_paper_password
   ```

### 3️⃣ Live Trading Account Setup

⚠️ **WARNING: Use with extreme caution!**

```bash
# Live account credentials
IB_USERNAME=U1234567
IB_PASSWORD=your_live_password
IB_TRADING_MODE=live

# Additional security settings
IB_READ_ONLY_API=false  # Set to true for monitoring only
IB_MASTER_CLIENT_ID=100  # Reserve client IDs 1-99 for manual trading
```

## 🚀 Starting IB Gateway

### 1️⃣ Start the Container

```bash
# Start IB Gateway
docker-compose up -d ib-gateway

# Follow logs
docker-compose logs -f ib-gateway
```

### 2️⃣ Monitor Startup

Watch for successful startup indicators:

```bash
# Good signs in logs:
# ✅ "Gateway initialization completed"
# ✅ "API socket listening on port 4002"
# ✅ "Successfully logged in"

# Warning signs:
# ⚠️ "Login failed"
# ⚠️ "Too many failed attempts"
# ⚠️ "Account locked"
```

### 3️⃣ Wait for Readiness

```bash
# Wait for health check
while ! docker-compose ps ib-gateway | grep -q "(healthy)"; do
    echo "Waiting for IB Gateway to be healthy..."
    sleep 10
done
echo "IB Gateway is ready!"
```

## ✅ Verification

### 🔍 Check Container Status

```bash
# View container status
docker ps --filter name=ib-gateway

# Expected output:
# STATUS          PORTS                                        NAMES
# Up 5 min (healthy)  0.0.0.0:4002->4002/tcp, 5900/tcp   spreadpilot-ib-gateway
```

### 📊 Check Logs

```bash
# View recent logs
docker logs --tail 50 spreadpilot-ib-gateway

# Check for errors
docker logs spreadpilot-ib-gateway 2>&1 | grep -i error
```

### 🔌 Test Network Connectivity

```bash
# Test API port
nc -zv localhost 4002

# Test with telnet
telnet localhost 4002

# Test with curl (should fail but confirm port is open)
curl -v telnet://localhost:4002
```

## 🧪 Testing Connection

### 1️⃣ Basic Connection Test

Create `test_ib_connection.py`:

```python
#!/usr/bin/env python3
import asyncio
from ib_insync import IB, util

async def test_connection():
    """Test IB Gateway connection"""
    ib = IB()
    
    try:
        # Connect to IB Gateway
        await ib.connectAsync('localhost', 4002, clientId=999)
        print("✅ Successfully connected to IB Gateway")
        
        # Get server info
        print(f"Server Version: {ib.client.serverVersion()}")
        print(f"Connection Time: {ib.client.connectionTime()}")
        
        # Get account info
        account_values = await ib.accountValuesAsync()
        if account_values:
            print(f"✅ Account connected: {account_values[0].account}")
            
        # Test market data
        contract = Stock('AAPL', 'SMART', 'USD')
        ticker = await ib.reqTickersAsync(contract)
        if ticker:
            print(f"✅ Market data working: AAPL = ${ticker[0].marketPrice()}")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        if ib.isConnected():
            ib.disconnect()

if __name__ == "__main__":
    util.startLoop()
    asyncio.run(test_connection())
```

Run the test:

```bash
python test_ib_connection.py
```

### 2️⃣ Advanced Health Check

Create `ib_health_check.py`:

```python
#!/usr/bin/env python3
import sys
from ib_insync import IB

def check_ib_health():
    """Comprehensive IB Gateway health check"""
    ib = IB()
    health_status = {
        "connected": False,
        "authenticated": False,
        "market_data": False,
        "account_access": False,
        "order_capability": False
    }
    
    try:
        # Test connection
        ib.connect('localhost', 4002, clientId=998)
        health_status["connected"] = True
        
        # Check authentication
        if ib.client.serverVersion() > 0:
            health_status["authenticated"] = True
        
        # Test account access
        accounts = ib.managedAccounts()
        if accounts:
            health_status["account_access"] = True
            
        # Test market data
        contract = Stock('SPY', 'SMART', 'USD')
        ticker = ib.reqTickers(contract)
        if ticker:
            health_status["market_data"] = True
            
        # Test order capability (paper only)
        if "paper" in str(accounts[0]).lower():
            health_status["order_capability"] = True
            
    except Exception as e:
        print(f"Health check error: {e}")
    finally:
        if ib.isConnected():
            ib.disconnect()
    
    # Report results
    print("IB Gateway Health Check:")
    for check, status in health_status.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {check}: {status}")
    
    # Exit with appropriate code
    if all(health_status.values()):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    check_ib_health()
```

## 🔧 Troubleshooting

### 🚫 Common Issues

#### Authentication Failures

**Problem:** Login failed with paper trading credentials

**Solutions:**
```bash
# 1. Verify paper account format
echo $IB_USERNAME  # Should show 'paperXXXXXX'

# 2. Reset login attempts
docker-compose stop ib-gateway
sleep 60  # Wait for lockout to expire
docker-compose up -d ib-gateway

# 3. Check account status
# Login to IB website and verify:
# - Paper account is active
# - No pending agreements
# - Account not locked
```

#### Connection Timeouts

**Problem:** Can't connect to API port 4002

**Solutions:**
```bash
# 1. Check port availability
sudo lsof -i :4002

# 2. Restart with fresh state
docker-compose down ib-gateway
docker volume rm spreadpilot_ib_gateway_settings
docker-compose up -d ib-gateway

# 3. Check firewall
sudo iptables -L -n | grep 4002
```

#### Two-Factor Authentication

**Problem:** 2FA preventing automated login

**Solutions:**
```bash
# Option 1: Use TOTP secret
# Add to .env:
IB_2FA_METHOD=TOTP
IB_2FA_SECRET=your_totp_secret

# Option 2: Use IB Key (requires mobile app)
# Configure in IB account settings for automated systems

# Option 3: Disable 2FA for paper account
# (Only recommended for isolated development environments)
```

### 📊 Debug Mode

Enable detailed logging:

```yaml
# Add to docker-compose.yml
ib-gateway:
  environment:
    - LOG_LEVEL=DEBUG
    - TWS_DEBUG=true
  volumes:
    - ./logs/ib-gateway:/root/Jts/logs
```

View debug logs:
```bash
tail -f logs/ib-gateway/*.log
```

## 🔒 Security & Best Practices

### 🛡️ Production Security

1. **Credential Management**
   ```bash
   # Use secrets manager
   export IB_USERNAME=$(aws secretsmanager get-secret-value --secret-id ib-username --query SecretString --output text)
   export IB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id ib-password --query SecretString --output text)
   ```

2. **Network Isolation**
   ```yaml
   # Production docker-compose.yml
   ib-gateway:
     networks:
       - internal
     ports: []  # No external exposure
   ```

3. **API Restrictions**
   ```python
   # Configure read-only access
   ib.setConnectOptions(readonly=True)
   ```

4. **Client ID Management**
   ```python
   # Reserve client IDs
   # 1-99: Manual TWS
   # 100-199: Production bots
   # 200-299: Development
   # 900-999: Testing
   ```

### 📈 Performance Optimization

1. **Connection Pooling**
   ```python
   # Reuse connections
   class IBConnectionPool:
       def __init__(self, size=5):
           self.connections = []
           for i in range(size):
               ib = IB()
               ib.connect('ib-gateway', 4002, clientId=100+i)
               self.connections.append(ib)
   ```

2. **Rate Limiting**
   ```python
   # Respect IB rate limits
   # Max 50 requests per second
   from ratelimit import limits, sleep_and_retry
   
   @sleep_and_retry
   @limits(calls=50, period=1)
   def make_ib_request():
       pass
   ```

## 📊 Monitoring

### 📈 Metrics Collection

Create `monitor_ib_gateway.sh`:

```bash
#!/bin/bash

# Collect IB Gateway metrics
while true; do
    # Check connection
    if nc -z localhost 4002; then
        echo "ib_gateway_up 1" | curl -X POST http://prometheus-pushgateway:9091/metrics/job/ib_gateway
    else
        echo "ib_gateway_up 0" | curl -X POST http://prometheus-pushgateway:9091/metrics/job/ib_gateway
    fi
    
    # Check memory usage
    MEMORY=$(docker stats --no-stream --format "{{.MemUsage}}" spreadpilot-ib-gateway | cut -d'/' -f1)
    echo "ib_gateway_memory_mb $MEMORY" | curl -X POST http://prometheus-pushgateway:9091/metrics/job/ib_gateway
    
    sleep 30
done
```

### 🚨 Alerting Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: ib_gateway
    rules:
      - alert: IBGatewayDown
        expr: ib_gateway_up == 0
        for: 2m
        annotations:
          summary: "IB Gateway is down"
          
      - alert: IBGatewayHighMemory
        expr: ib_gateway_memory_mb > 2048
        for: 5m
        annotations:
          summary: "IB Gateway memory usage is high"
```

## 🎯 Next Steps

After successfully setting up IB Gateway:

1. ✅ Configure the [Trading Bot Service](./2-trading-bot.md)
2. ✅ Set up the [Admin API](./3-admin-api.md)
3. ✅ Configure monitoring with [Watchdog](./4-watchdog.md)
4. ✅ Test order execution in paper trading

## 📚 Additional Resources

- [IB API Documentation](https://interactivebrokers.github.io/tws-api/)
- [ib-insync Documentation](https://ib-insync.readthedocs.io/)
- [IB Gateway Docker Image](https://github.com/gnzsnz/ib-gateway)
- [Interactive Brokers Support](https://www.interactivebrokers.com/en/support/)
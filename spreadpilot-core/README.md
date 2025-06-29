# 🏗️ SpreadPilot Core Library

> 🔧 **Shared foundation library** that provides essential components for all SpreadPilot microservices including IBKR integration, data models, and utilities

The `spreadpilot-core` library is the backbone of the SpreadPilot platform, offering a comprehensive set of shared functionality for trading automation, data management, and observability.

## 🎯 Overview

SpreadPilot Core provides essential building blocks for the entire platform:

### 🤖 **IBKR Integration**
- 🏦 Interactive Brokers API client wrapper
- 🔗 Connection management and authentication
- 📊 Market data and trading operations
- 🛡️ Error handling and retry mechanisms

### 📊 **Data Models**
- 🍃 MongoDB models with Pydantic validation
- 🐘 PostgreSQL models with SQLAlchemy
- 👥 Follower and trading account management
- 💰 P&L and commission calculation models

### 💹 **P&L Service**
- 📈 Real-time P&L monitoring and calculations
- ⏱️ Automatic daily rollups at 16:30 ET
- 📅 Monthly rollups at 00:10 ET on 1st
- 💸 Commission calculation (pct if pnl_month > 0)
- 🔄 Subscribe to trade fills and tick feeds

### 📈 **Report Generation**
- 📄 PDF reports with ReportLab
- 📊 Excel reports with pandas/openpyxl
- ☁️ Google Cloud Storage integration
- 🔗 Signed URL generation

### 🔔 **Communication**
- 📧 Email notifications via SendGrid
- 🤖 Telegram alerts and messaging
- 📨 Alert routing and templates
- 🚨 Error notification system

### 📝 **Observability**
- 📄 Structured logging with OpenTelemetry
- 📊 Metrics collection and reporting
- 🔍 Distributed tracing
- ☁️ Google Cloud Logging integration

---

## 🧩 Module Structure

### 📝 `logging` - Observability
```python
from spreadpilot_core.logging import get_logger, setup_logging

logger = get_logger(__name__)
setup_logging(service_name="my-service", enable_gcp=True)
```

### 🏦 `ibkr` - Interactive Brokers
```python
from spreadpilot_core.ibkr import IBKRClient

client = IBKRClient(username="user", password="pass")
positions = await client.get_positions()
```

### 📊 `models` - Data Models
```python
from spreadpilot_core.models import Follower, Position, Trade
from spreadpilot_core.models.pnl import PnLDaily, CommissionMonthly

# MongoDB models
follower = Follower(email="user@example.com", commission_pct=20.0)

# PostgreSQL models
pnl = PnLDaily(follower_id="123", date="2024-12-28", pnl_total=150.25)
```

### 🗄️ `db` - Database Connections
```python
from spreadpilot_core.db.mongodb import get_mongo_db
from spreadpilot_core.db.postgresql import get_async_db_session

# MongoDB
db = await get_mongo_db()
followers = await db.followers.find().to_list(None)

# PostgreSQL
async with get_async_db_session() as session:
    result = await session.execute(select(PnLDaily))
```

### 🛠️ `utils` - Utility Functions
```python
from spreadpilot_core.utils.pdf import generate_pdf_report
from spreadpilot_core.utils.excel import generate_excel_report
from spreadpilot_core.utils.email import send_email
from spreadpilot_core.utils.telegram import send_telegram_message

# Generate reports
pdf_path = generate_pdf_report(follower, month=12, year=2024, ...)
excel_path = generate_excel_report(follower, month=12, year=2024, ...)

# Send notifications
await send_email(to="user@example.com", subject="Report", body="...")
await send_telegram_message(chat_id="123", message="Alert!")
```

### 💹 `pnl` - P&L Service
```python
from spreadpilot_core.pnl import PnLService

# Initialize P&L service
pnl_service = PnLService()

# Set callbacks for external integrations
pnl_service.set_callbacks(
    get_positions_fn=get_follower_positions,
    get_market_price_fn=get_market_price,
    subscribe_tick_fn=subscribe_to_tick_feed
)

# Start monitoring
await pnl_service.start_monitoring(shutdown_event)

# Record trade fill
await pnl_service.record_trade_fill("follower-123", fill_data)

# Get real-time P&L
current_pnl = await pnl_service.get_current_pnl("follower-123")

# Get monthly commission
commission = await pnl_service.get_monthly_commission("follower-123", 2025, 6)
```

---

## 🚀 Installation & Setup

### 📦 Development Installation

```bash
# 1️⃣ Navigate to core library
cd spreadpilot-core/

# 2️⃣ Install in development mode
pip install -e .

# 3️⃣ Install with optional dependencies
pip install -e ".[dev,test,docs]"
```

### 🏗️ Production Installation

```bash
# Install from package
pip install spreadpilot-core

# Or from source
pip install git+https://github.com/your-org/spreadpilot.git#subdirectory=spreadpilot-core
```

### 📋 Dependencies

Core library provides optional dependency groups:

```bash
# Development tools
pip install "spreadpilot-core[dev]"  # black, flake8, mypy, isort

# Testing framework  
pip install "spreadpilot-core[test]"  # pytest, pytest-cov, pytest-asyncio

# Documentation
pip install "spreadpilot-core[docs]"  # sphinx, sphinx-rtd-theme

# All optional dependencies
pip install "spreadpilot-core[all]"
```

---

## 🛠️ Usage Examples

### 📊 Complete Trading Example

```python
import asyncio
from spreadpilot_core.logging import get_logger, setup_logging
from spreadpilot_core.ibkr import IBKRClient
from spreadpilot_core.models import Follower, Position
from spreadpilot_core.db.mongodb import get_mongo_db
from spreadpilot_core.utils.alerts import send_alert

async def trading_example():
    # Set up logging
    setup_logging(service_name="trading-example")
    logger = get_logger(__name__)
    
    # Create IBKR client
    client = IBKRClient(username="user", password="pass")
    await client.connect()
    
    # Get database connection
    db = await get_mongo_db()
    
    # Load follower
    follower_data = await db.followers.find_one({"email": "trader@example.com"})
    follower = Follower(**follower_data)
    
    # Execute trade
    order_id = await client.place_order(
        symbol="QQQ",
        action="BUY", 
        quantity=10,
        order_type="LMT",
        limit_price=445.50
    )
    
    logger.info(f"Order placed: {order_id}")
    
    # Send notification
    await send_alert(
        follower_id=follower.id,
        message=f"Order {order_id} placed successfully",
        alert_type="info"
    )

asyncio.run(trading_example())
```

### 💹 P&L Monitoring Example

```python
import asyncio
from spreadpilot_core.pnl import PnLService
from spreadpilot_core.db.mongodb import get_mongo_db

async def pnl_monitoring_example():
    # Initialize P&L service
    pnl_service = PnLService()
    
    # Define callback functions
    async def get_positions(follower_id):
        """Get follower positions from database."""
        db = await get_mongo_db()
        positions = await db.positions.find({"follower_id": follower_id}).to_list(None)
        return positions
    
    async def get_market_price(position):
        """Get market price for a position."""
        # This would typically call IBKR API
        return position.avg_cost * 1.05  # Mock 5% profit
    
    async def subscribe_tick(contract_info):
        """Subscribe to tick feed for a contract."""
        print(f"Subscribing to {contract_info}")
    
    # Set callbacks
    pnl_service.set_callbacks(
        get_positions_fn=get_positions,
        get_market_price_fn=get_market_price,
        subscribe_tick_fn=subscribe_tick
    )
    
    # Add followers to monitor
    await pnl_service.add_follower("follower-123")
    await pnl_service.add_follower("follower-456")
    
    # Record a trade fill
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
    
    # Get current P&L
    current_pnl = await pnl_service.get_current_pnl("follower-123")
    print(f"Current P&L: ${current_pnl['total_pnl']:.2f}")
    
    # Get monthly commission
    commission = await pnl_service.get_monthly_commission("follower-123", 2025, 6)
    if commission and commission['is_payable']:
        print(f"Commission due: ${commission['commission_amount']:.2f}")

asyncio.run(pnl_monitoring_example())
```

### 📄 Report Generation Example

```python
from spreadpilot_core.models import Follower
from spreadpilot_core.utils.pdf import generate_pdf_report
from spreadpilot_core.utils.excel import generate_excel_report
from google.cloud import storage

async def generate_monthly_report():
    # Create follower model
    follower = Follower(
        id="follower-123",
        email="trader@example.com", 
        iban="DE12345678901234567890",
        commission_pct=20.0
    )
    
    # Sample daily P&L data
    daily_pnl = {
        "20241201": 150.25,
        "20241202": -75.50, 
        "20241203": 200.00
    }
    
    # Generate PDF report
    pdf_path = generate_pdf_report(
        output_path="/tmp/reports",
        follower=follower,
        month=12,
        year=2024,
        pnl_total=274.75,
        commission_amount=54.95,
        daily_pnl=daily_pnl
    )
    
    # Generate Excel report
    excel_path = generate_excel_report(
        output_path="/tmp/reports", 
        follower=follower,
        month=12,
        year=2024,
        pnl_total=274.75,
        commission_amount=54.95,
        daily_pnl=daily_pnl
    )
    
    print(f"Reports generated: {pdf_path}, {excel_path}")
```

### 🐘 PostgreSQL P&L Example

```python
from spreadpilot_core.db.postgresql import get_async_db_session
from spreadpilot_core.models.pnl import PnLDaily, CommissionMonthly
from sqlalchemy import select
import datetime

async def pnl_example():
    async with get_async_db_session() as session:
        # Create daily P&L record
        pnl_record = PnLDaily(
            follower_id="follower-123",
            date=datetime.date.today(),
            pnl_total=150.25,
            pnl_realized=100.00,
            pnl_unrealized=50.25,
            created_at=datetime.datetime.utcnow()
        )
        
        session.add(pnl_record)
        
        # Query monthly P&L
        stmt = select(CommissionMonthly).where(
            CommissionMonthly.follower_id == "follower-123",
            CommissionMonthly.year == 2024,
            CommissionMonthly.month == 12
        )
        
        result = await session.execute(stmt)
        commission_record = result.scalar_one_or_none()
        
        if commission_record:
            print(f"Commission: ${commission_record.commission_amount:.2f}")
        
        await session.commit()
```

---

## 🧪 Testing

### 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=spreadpilot_core --cov-report=html

# Run specific module tests
pytest tests/test_models.py
pytest tests/test_utils.py
pytest tests/test_ibkr.py

# Run async tests
pytest tests/test_db.py -v
```

### 🎭 Testing with Mocks

```python
import pytest
from unittest.mock import AsyncMock, patch
from spreadpilot_core.ibkr import IBKRClient

@pytest.mark.asyncio
async def test_ibkr_client():
    with patch('spreadpilot_core.ibkr.ib_insync.IB') as mock_ib:
        mock_ib.return_value.connect = AsyncMock()
        mock_ib.return_value.positions = AsyncMock(return_value=[])
        
        client = IBKRClient(username="test", password="test")
        await client.connect()
        positions = await client.get_positions()
        
        assert positions == []
        mock_ib.return_value.connect.assert_called_once()
```

---

## 🎨 Development

### 🔧 Code Quality

```bash
# Format code
black spreadpilot_core/ tests/

# Sort imports  
isort spreadpilot_core/ tests/

# Linting
flake8 spreadpilot_core/ tests/

# Type checking
mypy spreadpilot_core/
```

### 📋 Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### 🏗️ Building Distribution

```bash
# Build source and wheel distributions
python -m build

# Upload to PyPI (with proper credentials)
python -m twine upload dist/*
```

---

## 📊 Configuration

### 🌍 Environment Variables

The core library respects these environment variables:

```bash
# 📝 Logging Configuration
LOG_LEVEL=INFO
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
GOOGLE_CLOUD_PROJECT=your-project-id

# 🍃 MongoDB Configuration  
MONGO_URI=mongodb://user:password@localhost:27017
MONGO_DB_NAME=spreadpilot_admin

# 🐘 PostgreSQL Configuration
POSTGRES_URI=postgresql+asyncpg://user:password@localhost:5432/spreadpilot_pnl

# 🏦 IBKR Configuration
IB_GATEWAY_HOST=127.0.0.1
IB_GATEWAY_PORT=4002
IB_CLIENT_ID=1

# 📧 Email Configuration
SENDGRID_API_KEY=your-api-key
SENDER_EMAIL=noreply@spreadpilot.com

# 🤖 Telegram Configuration
TELEGRAM_BOT_TOKEN=your-bot-token

# ☁️ Google Cloud Storage
GCS_BUCKET_NAME=spreadpilot-reports
```

---

## 🔧 Troubleshooting

### 🏦 **IBKR Connection Issues**

```python
# Test IBKR connection
from spreadpilot_core.ibkr import IBKRClient

client = IBKRClient(username="test", password="test")
try:
    await client.connect()
    print("✅ IBKR Connected")
except Exception as e:
    print(f"❌ IBKR Error: {e}")
```

### 🗄️ **Database Connection Issues**

```python
# Test MongoDB
from spreadpilot_core.db.mongodb import get_mongo_db

try:
    db = await get_mongo_db()
    result = await db.admin.command('ping')
    print("✅ MongoDB Connected")
except Exception as e:
    print(f"❌ MongoDB Error: {e}")

# Test PostgreSQL
from spreadpilot_core.db.postgresql import get_async_db_session

try:
    async with get_async_db_session() as session:
        await session.execute("SELECT 1")
    print("✅ PostgreSQL Connected")
except Exception as e:
    print(f"❌ PostgreSQL Error: {e}")
```

### 📝 **Logging Issues**

```python
# Test logging setup
from spreadpilot_core.logging import get_logger, setup_logging

setup_logging(service_name="test-service")
logger = get_logger(__name__)

logger.info("Test log message")
logger.error("Test error message", extra={"key": "value"})
```

---

## 📚 API Reference

### 🏦 IBKR Client

| Method | Description | Returns |
|--------|-------------|---------|
| `connect()` | Connect to IB Gateway | `None` |
| `disconnect()` | Disconnect from IB Gateway | `None` |
| `get_positions()` | Get current positions | `List[Position]` |
| `place_order()` | Place trading order | `str` (order ID) |
| `get_account_info()` | Get account information | `Dict` |

### 📊 Models

| Model | Purpose | Database |
|-------|---------|----------|
| `Follower` | Trading account management | MongoDB |
| `Position` | Current trading positions | MongoDB |
| `Trade` | Historical trade records | MongoDB |
| `PnLDaily` | Daily P&L calculations | PostgreSQL |
| `CommissionMonthly` | Monthly commission data | PostgreSQL |

### 🛠️ Utilities

| Function | Purpose | Returns |
|----------|---------|---------|
| `generate_pdf_report()` | Create PDF report | `str` (file path) |
| `generate_excel_report()` | Create Excel report | `str` (file path) |
| `send_email()` | Send email notification | `bool` |
| `send_telegram_message()` | Send Telegram message | `bool` |

---

## 🤝 Contributing

### 📋 Development Setup

```bash
# 1️⃣ Clone repository
git clone https://github.com/your-org/spreadpilot.git
cd spreadpilot/spreadpilot-core/

# 2️⃣ Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# 3️⃣ Install in development mode
pip install -e ".[dev,test]"

# 4️⃣ Set up pre-commit hooks
pre-commit install
```

### 🎯 Contribution Guidelines

1. 🍴 **Fork** the repository
2. 🌿 **Create** feature branch (`git checkout -b feature/amazing-feature`)
3. 🧪 **Write** tests for new functionality
4. 🎨 **Format** code (`black`, `isort`, `flake8`)
5. ✅ **Run** tests (`pytest`)
6. 📝 **Commit** changes (`git commit -m 'feat: add amazing feature'`)
7. 📤 **Push** to branch (`git push origin feature/amazing-feature`)
8. 🔄 **Create** Pull Request

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](../LICENSE) file for details.

---

<div align="center">

**🏗️ Building the foundation for automated trading excellence**

[📖 Full Documentation](../docs/) • [🧪 Testing Guide](./tests/README.md) • [🔧 API Reference](./docs/api.md)

</div>
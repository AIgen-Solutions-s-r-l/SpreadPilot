# SpreadPilot Testing Strategy

Comprehensive guide to testing philosophy, mock infrastructure, and best practices.

---

## Overview

Our testing philosophy prioritizes **isolation**, **reliability**, and **fast feedback** while maintaining high confidence in production behavior.

**Core Principles**:
- **Fast unit tests** - Instant feedback during development
- **Isolated tests** - No dependencies between tests
- **Realistic mocks** - Mock behavior matches real systems
- **Comprehensive coverage** - Business logic 100% tested
- **Deterministic** - No flaky tests

---

## Test Pyramid

```
        /\
       /  \  E2E (Few, Slow)
      /----\
     /      \  Integration (Some, Medium)
    /--------\
   /          \  Unit (Many, Fast)
  /____________\
```

**Distribution**:
- **70%** Unit Tests - Individual components
- **20%** Integration Tests - Component interactions
- **10%** E2E Tests - Full system workflows

---

## Test Levels

### Unit Tests

**Purpose**: Test individual components in complete isolation

**Characteristics**:
- Mock **all** external dependencies
- Fast execution (<1s per test)
- High volume (hundreds of tests)
- No database, no network, no file I/O

**Location**: `tests/unit/`

**Example**:
```python
from unittest.mock import Mock, AsyncMock
import pytest

@pytest.fixture
def mock_ibkr_client():
    """Mock IBKR client for unit tests."""
    client = Mock()
    client.place_order = AsyncMock(return_value={
        "order_id": "TEST_123",
        "status": "FILLED",
        "fill_price": 380.50
    })
    return client

async def test_trade_executor_places_order(mock_ibkr_client):
    """Test trade executor successfully places order."""
    executor = TradeExecutor(ibkr_client=mock_ibkr_client)

    result = await executor.execute_trade(
        symbol="QQQ",
        quantity=100,
        action="BUY"
    )

    # Verify mock was called correctly
    mock_ibkr_client.place_order.assert_called_once_with(
        symbol="QQQ",
        quantity=100,
        action="BUY"
    )

    # Verify result
    assert result.order_id == "TEST_123"
    assert result.status == "FILLED"
```

**Run**:
```bash
pytest tests/unit/ -v
```

---

### Integration Tests

**Purpose**: Test component interactions with real infrastructure

**Characteristics**:
- Use **real** database (MongoDB, Redis)
- Mock **external** services only (IBKR, email, APIs)
- Medium execution (1-5s per test)
- Test actual database queries, caching, etc.

**Location**: `tests/integration/`

**Example**:
```python
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.fixture
async def mongo_db():
    """Real MongoDB for integration tests."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["test_db"]

    yield db

    # Cleanup
    await client.drop_database("test_db")
    client.close()

@pytest.fixture
def mock_ibkr_client():
    """Still mock external IBKR service."""
    client = Mock()
    client.place_order = AsyncMock(return_value={"order_id": "123"})
    return client

@pytest.mark.integration
async def test_order_persistence(mongo_db, mock_ibkr_client):
    """Test order is saved to database after execution."""
    service = OrderService(db=mongo_db, ibkr=mock_ibkr_client)

    # Execute trade
    order = await service.place_and_save_order(
        symbol="QQQ",
        quantity=100
    )

    # Verify saved to real database
    saved = await mongo_db.orders.find_one({"order_id": order.order_id})
    assert saved is not None
    assert saved["symbol"] == "QQQ"
    assert saved["quantity"] == 100
```

**Run**:
```bash
pytest tests/integration/ -v
```

---

### E2E Tests

**Purpose**: Test complete user workflows end-to-end

**Characteristics**:
- Use **real** services where possible (MongoDB, Redis)
- Use **mock** external services (IBKR Gateway, Email)
- Slow execution (10-60s per test)
- Test full request→response→database→notification flows

**Location**: `tests/e2e/`

**Example**:
```python
@pytest.mark.e2e
async def test_full_trading_flow(e2e_environment):
    """Test complete flow: signal → order → position → notification."""

    # 1. Post trading signal (simulated Google Sheets update)
    await post_trading_signal({
        "symbol": "QQQ",
        "action": "BUY",
        "quantity": 100
    })

    # 2. Wait for bot to process
    await asyncio.sleep(2)

    # 3. Verify order placed (check mock IBKR)
    orders = await get_orders_from_mock_ibkr()
    assert len(orders) == 1
    assert orders[0]["symbol"] == "QQQ"

    # 4. Verify position saved to database
    position = await db.positions.find_one({"symbol": "QQQ"})
    assert position is not None

    # 5. Verify email sent (check MailHog)
    emails = await get_emails_from_mailhog()
    assert len(emails) == 1
    assert "Order Filled" in emails[0]["subject"]
```

**Run**:
```bash
make e2e
# or
docker-compose -f docker-compose.e2e.yml up --abort-on-container-exit
```

---

## What We Mock and Why

### ✅ Always Mock

#### 1. IBKR Gateway
**Why**:
- Requires paid credentials
- Rate limited (expensive to exceed)
- Real money at risk
- Network latency makes tests slow
- Can't control market conditions

**How**: Mock IBKR Gateway or Paper Gateway
```python
@pytest.fixture
def mock_ibkr():
    client = Mock()
    client.place_order = AsyncMock(return_value={"order_id": "123"})
    return client
```

**Real Alternative**: Paper Gateway for integration testing
```bash
docker-compose --profile paper up -d
# Tests connect to localhost:4003
```

---

#### 2. Email Services (SendGrid, SMTP)
**Why**:
- Avoid sending spam emails
- No API keys needed
- Instant (no network delays)
- Full control over responses

**How**: MailHog email capture
```bash
docker-compose --profile dev up -d mailhog
# Check emails at http://localhost:8025
```

---

#### 3. External APIs (Google Sheets, Market Data)
**Why**:
- API quotas and rate limits
- Costs money
- Network unreliability
- Can't control data

**How**: Mock HTTP responses
```python
@pytest.fixture
def mock_google_sheets(httpx_mock):
    httpx_mock.add_response(
        url="https://sheets.googleapis.com/v4/spreadsheets/...",
        json={"values": [["QQQ", "BUY", "100"]]}
    )
```

---

#### 4. Time/Dates
**Why**:
- Deterministic tests
- Test time-dependent logic
- Fast-forward through delays

**How**: `freezegun` library
```python
from freezegun import freeze_time

@freeze_time("2024-01-15 14:30:00")
def test_market_hours():
    assert is_market_open()  # Always Monday 2:30 PM
```

---

### ⚠️ Sometimes Mock

#### Database (MongoDB, Redis)
- **Unit Tests**: Mock (fast, isolated)
- **Integration Tests**: Real (test queries)
- **E2E Tests**: Real (test persistence)

```python
# Unit test - Mock
@pytest.fixture
def mock_db():
    db = Mock()
    db.orders.insert_one = AsyncMock(return_value=Mock(inserted_id="123"))
    return db

# Integration test - Real
@pytest.fixture
async def real_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    yield client["test_db"]
    await client.drop_database("test_db")
```

---

### ❌ Never Mock

#### 1. Business Logic
**Why**: We're testing **our** code, not mocks

**Bad**:
```python
# DON'T DO THIS
def test_calculate_pnl():
    mock_calculator = Mock()
    mock_calculator.calculate_pnl.return_value = 100.0
    assert mock_calculator.calculate_pnl() == 100.0  # Testing nothing!
```

**Good**:
```python
# DO THIS
def test_calculate_pnl():
    calculator = PnLCalculator()  # Real implementation
    pnl = calculator.calculate_pnl(
        entry_price=380.0,
        exit_price=360.0,
        quantity=100
    )
    assert pnl == -2000.0  # Testing real calculation
```

---

#### 2. Data Models
**Why**: Models are simple, cheap to instantiate

```python
# DO THIS - Use real models
from app.models import Order

def test_order_validation():
    order = Order(symbol="QQQ", quantity=100)  # Real model
    assert order.is_valid()
```

---

#### 3. Utility Functions
**Why**: Pure functions are fast and deterministic

```python
# DO THIS - Test real utilities
from app.utils import format_currency

def test_format_currency():
    assert format_currency(1234.56) == "$1,234.56"
```

---

## Mock Infrastructure

### 1. Paper Trading Gateway

**Purpose**: Realistic IBKR Gateway simulation for development and testing

**Location**: `paper-gateway/`

**Features**:
- GBM price simulation
- Order execution with slippage
- Commission calculation
- Market hours enforcement
- MongoDB persistence
- Performance metrics

**Usage**:
```bash
# Start paper gateway
docker-compose --profile paper up -d

# In tests, connect to localhost:4003
ibkr_client = IBKRClient(host="localhost", port=4003)
```

**When to Use**:
- Integration tests requiring realistic execution
- Manual testing of trading strategies
- Development without real IBKR account

**Documentation**: [PAPER_TRADING_MODE.md](PAPER_TRADING_MODE.md)

---

### 2. Mock IBKR Gateway (E2E)

**Purpose**: Simple, fast mock for E2E tests

**Location**: `tests/e2e/Dockerfile.ibkr-mock`

**Features**:
- Instant order fills
- Position tracking
- Account balance
- Minimal state

**Usage**:
```bash
# Automatically started by docker-compose.e2e.yml
make e2e
```

**When to Use**:
- E2E tests requiring fast execution
- CI/CD pipelines
- Testing error scenarios

---

### 3. MailHog (Email Testing)

**Purpose**: Capture and inspect emails without sending

**Location**: Docker Hub `mailhog/mailhog`

**Features**:
- SMTP server (port 1025)
- Web UI (port 8025)
- API for automated checks
- Email preview

**Usage**:
```bash
# Start MailHog
docker-compose --profile dev up -d mailhog

# Configure services
SMTP_SERVER=mailhog
SMTP_PORT=1025

# View emails
open http://localhost:8025

# Check via API in tests
emails = httpx.get("http://localhost:8025/api/v2/messages").json()
```

**When to Use**:
- All tests requiring email
- Development email preview
- E2E email verification

**Documentation**: [EMAIL_PREVIEW_MODE.md](EMAIL_PREVIEW_MODE.md)

---

### 4. Dry-Run Mode

**Purpose**: Simulate operations without execution

**Location**: `spreadpilot-core/spreadpilot_core/dry_run.py`

**Features**:
- Decorator-based
- Automatic logging
- Operation reports
- Context manager

**Usage**:
```python
from spreadpilot_core.dry_run import dry_run_trade, DryRunConfig

@dry_run_trade()
def place_order(symbol, quantity):
    return ibkr.place_order(symbol, quantity)

# Enable for tests
DryRunConfig.enable()

result = place_order("QQQ", 100)
# Returns mock, logs operation, doesn't execute

# Get report
report = DryRunConfig.get_report()
assert report["total_operations"] == 1
```

**When to Use**:
- Configuration validation tests
- Disaster recovery simulation
- Training/demo mode
- Compliance testing

**Documentation**: [DRY_RUN_MODE.md](DRY_RUN_MODE.md)

---

### 5. Test Data Generator

**Purpose**: Generate realistic market data and scenarios

**Location**: `spreadpilot-core/spreadpilot_core/test_data_generator.py`

**Features**:
- 10 scenario types
- GBM price simulation
- Reproducible (seed-based)
- JSON/CSV export

**Usage**:
```python
from spreadpilot_core.test_data_generator import (
    generate_test_prices,
    generate_scenario,
    ScenarioType
)

# Generate price data
prices = generate_test_prices("QQQ", days=30)

# Generate crash scenario
crash = generate_scenario(ScenarioType.MARKET_CRASH)

# Use in tests
@pytest.fixture
def market_crash_data():
    return generate_scenario(ScenarioType.MARKET_CRASH)

def test_strategy_under_crash(market_crash_data):
    result = backtest(market_crash_data)
    assert result.max_drawdown < 0.20  # <20% drawdown
```

**When to Use**:
- Backtesting tests
- Edge case testing
- Performance benchmarking
- Reproducible test data

**Documentation**: [TEST_DATA_GENERATOR.md](TEST_DATA_GENERATOR.md)

---

### 6. Simulation/Replay Engine

**Purpose**: Backtest strategies on historical data

**Location**: `spreadpilot-core/spreadpilot_core/simulation.py`

**Features**:
- Time-travel through data
- 3 modes (Backtest, Replay, Step)
- Performance metrics
- Equity curve tracking

**Usage**:
```python
from spreadpilot_core.simulation import run_backtest

def my_strategy(engine, current_data):
    if current_data["close"] < 375:
        engine.place_order("QQQ", 100, "BUY")

results = run_backtest(historical_data, my_strategy)

assert results["performance"]["total_return_pct"] > 5.0
assert results["trading"]["win_rate_pct"] > 50.0
```

**When to Use**:
- Strategy validation tests
- Parameter optimization tests
- Regression testing
- Performance comparison

**Documentation**: [SIMULATION_REPLAY_MODE.md](SIMULATION_REPLAY_MODE.md)

---

## Writing Tests

### Test Structure

**AAA Pattern**: Arrange, Act, Assert

```python
def test_order_placement():
    # Arrange - Set up test data and mocks
    mock_ibkr = Mock()
    mock_ibkr.place_order = AsyncMock(return_value={"order_id": "123"})
    executor = TradeExecutor(ibkr_client=mock_ibkr)

    # Act - Execute the code under test
    result = await executor.execute_trade("QQQ", 100, "BUY")

    # Assert - Verify the outcome
    assert result.order_id == "123"
    mock_ibkr.place_order.assert_called_once()
```

---

### Naming Convention

**Pattern**: `test_<component>_<scenario>_<expected_outcome>`

**Examples**:
```python
def test_order_executor_valid_order_returns_success()
def test_position_manager_insufficient_balance_raises_error()
def test_pnl_calculator_winning_trade_returns_positive()
```

---

### Fixtures

**Use fixtures for reusable test data**:

```python
# conftest.py
@pytest.fixture
def sample_follower():
    return Follower(
        follower_id="TEST_001",
        name="Test Follower",
        account_id="ACCT_123",
        is_active=True
    )

@pytest.fixture
def sample_position():
    return Position(
        symbol="QQQ",
        quantity=100,
        avg_cost=380.0
    )

# test_positions.py
def test_close_position(sample_position):
    manager = PositionManager()
    result = manager.close(sample_position)
    assert result.status == "CLOSED"
```

---

### Parametrize for Multiple Cases

```python
@pytest.mark.parametrize("price,expected_decision", [
    (375.0, "BUY"),   # Below threshold
    (380.0, "HOLD"),  # At threshold
    (385.0, "SELL"),  # Above threshold
])
def test_trading_decision(price, expected_decision):
    strategy = MomentumStrategy(threshold=380.0)
    decision = strategy.decide(price)
    assert decision == expected_decision
```

---

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_order_placement():
    mock_ibkr = Mock()
    mock_ibkr.place_order = AsyncMock(return_value={"order_id": "123"})

    executor = TradeExecutor(ibkr_client=mock_ibkr)
    result = await executor.execute_trade("QQQ", 100, "BUY")

    assert result.order_id == "123"
```

---

## Running Tests

### Quick Reference

```bash
# All tests
make test

# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# E2E tests
make e2e

# Specific test file
pytest tests/unit/test_orders.py -v

# Specific test function
pytest tests/unit/test_orders.py::test_place_order -v

# With coverage
make test-coverage

# Coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Parallel execution (faster)
pytest -n auto

# Stop on first failure
pytest -x

# Show print statements
pytest -s

# Run marked tests
pytest -m integration
pytest -m "not slow"
```

---

### Coverage Requirements

**Minimum Coverage**: 80%
**Target Coverage**: 95%+

**Check coverage**:
```bash
make test-coverage

# Should see:
# TOTAL    1000    50    95%
```

**Coverage exceptions** (don't need 100%):
- `if __name__ == "__main__"` blocks
- Error handling for impossible states
- Defensive null checks

---

## CI/CD Testing

### GitHub Actions Workflow

**`.github/workflows/test.yml`**:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: make install-all

      - name: Lint
        run: make lint

      - name: Unit tests
        run: pytest tests/unit/ --cov

      - name: Integration tests
        run: |
          docker-compose up -d mongodb redis
          pytest tests/integration/

      - name: E2E tests
        run: make e2e

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

**Triggers**:
- Every push to any branch
- Every pull request
- Scheduled weekly for regression

---

## Best Practices

### 1. Test Isolation

**Bad** (tests depend on each other):
```python
order_id = None

def test_place_order():
    global order_id
    order_id = place_order("QQQ", 100)

def test_get_order():
    # Depends on test_place_order!
    order = get_order(order_id)
    assert order is not None
```

**Good** (independent tests):
```python
def test_place_order():
    order_id = place_order("QQQ", 100)
    assert order_id is not None

def test_get_order():
    # Create own test data
    order_id = place_order("QQQ", 100)
    order = get_order(order_id)
    assert order is not None
```

---

### 2. Fast Tests

**Bad** (unnecessary delays):
```python
def test_order_timeout():
    place_order("QQQ", 100)
    time.sleep(30)  # Wait for timeout
    assert check_timeout()
```

**Good** (mock time):
```python
@freeze_time("2024-01-01 10:00:00")
def test_order_timeout():
    place_order("QQQ", 100)

    # Fast-forward time
    with freeze_time("2024-01-01 10:00:31"):
        assert check_timeout()
```

---

### 3. Clear Assertions

**Bad** (unclear what's being tested):
```python
def test_pnl():
    result = calculate_pnl(data)
    assert result  # What are we testing?
```

**Good** (specific assertions):
```python
def test_pnl_winning_trade_returns_positive():
    result = calculate_pnl(
        entry_price=380.0,
        exit_price=390.0,
        quantity=100
    )
    assert result == 1000.0, "Expected $1000 profit"
    assert result > 0, "Winning trade should have positive P&L"
```

---

### 4. Test Edge Cases

```python
@pytest.mark.parametrize("quantity", [
    0,      # Zero
    -1,     # Negative
    1,      # Minimum
    10000,  # Large
    None,   # Null
])
def test_order_quantity_validation(quantity):
    if quantity is None or quantity <= 0:
        with pytest.raises(ValueError):
            validate_order_quantity(quantity)
    else:
        assert validate_order_quantity(quantity) == quantity
```

---

### 5. Don't Test Framework Code

**Bad** (testing FastAPI, not our code):
```python
def test_fastapi_returns_json():
    response = client.get("/")
    assert response.headers["content-type"] == "application/json"
```

**Good** (test our business logic):
```python
def test_get_followers_returns_active_only():
    response = client.get("/api/v1/followers?active=true")
    followers = response.json()
    assert all(f["is_active"] for f in followers)
```

---

## Troubleshooting

### Flaky Tests

**Symptom**: Test passes sometimes, fails other times

**Common Causes**:
1. **Time dependencies**:
   ```python
   # Bad
   assert datetime.now().hour == 14

   # Good
   with freeze_time("2024-01-01 14:00:00"):
       assert datetime.now().hour == 14
   ```

2. **Random data**:
   ```python
   # Bad
   value = random.randint(1, 100)

   # Good
   random.seed(42)  # Reproducible
   value = random.randint(1, 100)
   ```

3. **Race conditions**:
   ```python
   # Bad
   async_task()
   assert task_complete()  # May not be done yet

   # Good
   await async_task()
   assert task_complete()
   ```

---

### Slow Tests

**Symptom**: Tests take too long

**Solutions**:
1. **Mock external services**
2. **Use in-memory database**
3. **Run tests in parallel**: `pytest -n auto`
4. **Skip slow tests in dev**: `pytest -m "not slow"`

---

### Import Errors

**Symptom**: `ModuleNotFoundError`

**Solution**:
```bash
# Install in editable mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

## FAQ

**Q: Why do we mock IBKR in tests?**
A: Real IBKR requires paid credentials, is rate-limited, and involves real money. Mocking enables fast, safe, reliable tests.

**Q: Are we testing against real systems anywhere?**
A: Yes, we have:
- Paper Gateway for realistic integration testing
- Staging environment with IBKR paper account
- Periodic contract tests comparing mocks to real behavior

**Q: How do we know mocks match reality?**
A: We:
1. Run contract tests monthly comparing mock vs real IBKR
2. Use Paper Gateway with realistic simulation
3. Test in staging with real IBKR paper account
4. Monitor production for unexpected behavior

**Q: Can I run tests against real IBKR?**
A: Yes, but not recommended:
```bash
export USE_REAL_IBKR=true
export IB_USERNAME=...
export IB_PASSWORD=...
pytest tests/integration/  # Very slow, requires credentials
```

**Q: Why are some tests marked `@pytest.mark.slow`?**
A: Allows skipping slow tests during development:
```bash
pytest -m "not slow"  # Skip slow tests
pytest -m slow        # Run only slow tests
```

**Q: How often should I run the full test suite?**
A:
- **Unit tests**: Every save (use file watcher)
- **Integration tests**: Before each commit
- **E2E tests**: Before pushing
- **Full suite**: CI/CD runs on every PR

---

## Related Documentation

- [Paper Trading Mode](PAPER_TRADING_MODE.md) - Paper Gateway for testing
- [Email Preview Mode](EMAIL_PREVIEW_MODE.md) - MailHog for email testing
- [Dry-Run Mode](DRY_RUN_MODE.md) - Operation simulation
- [Test Data Generator](TEST_DATA_GENERATOR.md) - Realistic test data
- [Simulation Mode](SIMULATION_REPLAY_MODE.md) - Backtesting framework
- [Testing Guide](05-testing-guide.md) - Original testing docs

---

**Quality**: Production-ready
**Status**: Complete
**Version**: 1.0.0

# 🧪 Testing Guide for SpreadPilot

> 📖 **Comprehensive testing guide** covering unit tests, integration tests, and end-to-end testing for the SpreadPilot automated trading platform

This guide provides detailed information about SpreadPilot's testing strategy, tools, and best practices for ensuring code quality and reliability.

---

## 📚 Table of Contents

- [Testing Strategy](#-testing-strategy)
- [Test Structure](#-test-structure)
- [Unit Testing](#-unit-testing)
- [Integration Testing](#-integration-testing)
- [End-to-End Testing](#-end-to-end-testing)
- [Running Tests](#-running-tests)
- [Writing Tests](#-writing-tests)
- [Test Coverage](#-test-coverage)
- [CI/CD Integration](#-cicd-integration)
- [Best Practices](#-best-practices)

---

## 🎯 Testing Strategy

SpreadPilot employs a comprehensive testing strategy to ensure reliability:

### 📊 **Test Pyramid**

```
         /\
        /E2E\        🌐 End-to-End Tests (10%)
       /------\      - Complete workflow validation
      /Integr. \     - Production-like environment
     /----------\    
    /   Unit     \   🧪 Unit Tests (70%)
   /--------------\  - Individual components
  /________________\ - Fast execution
```

### 🎨 **Testing Principles**

- **🔄 Continuous Testing** - Tests run on every commit
- **📊 High Coverage** - Maintain >80% code coverage
- **⚡ Fast Feedback** - Quick test execution
- **🔐 Isolated Tests** - No dependencies between tests
- **📝 Clear Assertions** - Descriptive test names and failure messages

---

## 📁 Test Structure

```bash
tests/
├── unit/                    # 🧪 Unit tests
│   ├── test_models.py      # Model tests
│   ├── test_services.py    # Service layer tests
│   ├── test_utils.py       # Utility function tests
│   └── test_strategies.py  # Trading strategy tests
├── integration/            # 🔗 Integration tests
│   ├── test_ibkr.py       # IBKR integration
│   ├── test_mongodb.py    # Database integration
│   ├── test_api.py        # API endpoint tests
│   └── test_workflows.py  # Multi-service workflows
├── e2e/                   # 🌐 End-to-end tests
│   ├── e2e_test.py       # Complete workflow tests
│   ├── conftest.py       # E2E fixtures
│   ├── README.md         # E2E documentation
│   └── Dockerfile.ibkr-mock  # Mock services
├── conftest.py           # 📋 Shared fixtures
├── __init__.py
└── pytest.ini           # ⚙️ Pytest configuration
```

---

## 🧪 Unit Testing

Unit tests focus on individual components in isolation.

### 📋 **Example Unit Test**

```python
# tests/unit/test_models.py
import pytest
from datetime import datetime
from spreadpilot_core.models import Follower, Position

class TestFollowerModel:
    """Test cases for Follower model."""
    
    def test_follower_creation(self):
        """Test creating a follower with required fields."""
        follower = Follower(
            email="test@example.com",
            iban="DE89370400440532013000",
            commission_pct=20.0,
            active=True
        )
        
        assert follower.email == "test@example.com"
        assert follower.commission_pct == 20.0
        assert follower.active is True
        assert isinstance(follower.created_at, datetime)
    
    def test_follower_validation(self):
        """Test follower field validation."""
        with pytest.raises(ValueError):
            # Invalid commission percentage
            Follower(
                email="test@example.com",
                commission_pct=150.0  # Should be 0-100
            )
    
    @pytest.mark.parametrize("commission,expected", [
        (0, 0),
        (20, 20),
        (100, 100),
    ])
    def test_commission_boundaries(self, commission, expected):
        """Test commission percentage boundaries."""
        follower = Follower(
            email="test@example.com",
            commission_pct=commission
        )
        assert follower.commission_pct == expected
```

### 🎯 **Unit Test Best Practices**

- **🔍 Test One Thing** - Each test should verify a single behavior
- **📝 Descriptive Names** - Test names should explain what they test
- **🎭 Use Mocks** - Mock external dependencies
- **⚡ Keep It Fast** - Unit tests should run in milliseconds
- **🔄 Independent** - Tests should not depend on each other

---

## 🔗 Integration Testing

Integration tests verify interactions between components.

### 📋 **Example Integration Test**

```python
# tests/integration/test_api.py
import pytest
import httpx
from fastapi.testclient import TestClient
from admin_api.app.main import app

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

@pytest.fixture
async def test_follower(mongo_client):
    """Create test follower in database."""
    follower = {
        "_id": "TEST_001",
        "email": "test@example.com",
        "commission_pct": 20.0,
        "active": True,
        "created_at": datetime.utcnow()
    }
    
    await mongo_client.spreadpilot.followers.insert_one(follower)
    yield follower
    await mongo_client.spreadpilot.followers.delete_one({"_id": "TEST_001"})

class TestFollowerAPI:
    """Test follower API endpoints."""
    
    def test_get_followers(self, client, test_follower):
        """Test retrieving followers list."""
        response = client.get("/api/v1/followers")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(f["email"] == "test@example.com" for f in data)
    
    def test_create_follower(self, client):
        """Test creating a new follower."""
        follower_data = {
            "email": "new@example.com",
            "iban": "DE89370400440532013000",
            "commission_pct": 25.0
        }
        
        response = client.post("/api/v1/followers", json=follower_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"
        assert data["commission_pct"] == 25.0
```

### 🎯 **Integration Test Best Practices**

- **🗄️ Real Databases** - Use test databases, not mocks
- **🔄 Clean State** - Reset data between tests
- **🌐 Test APIs** - Verify HTTP endpoints
- **⚡ Parallel Execution** - Use isolated test databases
- **📊 Test Workflows** - Verify multi-step processes

---

## 🌐 End-to-End Testing

E2E tests validate complete user workflows in a production-like environment.

### 🚀 **E2E Test Environment**

SpreadPilot includes a comprehensive E2E test suite that spins up the entire system:

```yaml
# docker-compose.e2e.yml
version: '3.8'

services:
  mongodb-test:
    image: mongo:6.0
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password
    
  ibkr-gateway-mock:
    build:
      dockerfile: tests/e2e/Dockerfile.ibkr-mock
    ports:
      - "5001:5001"
    
  mailhog:
    image: mailhog/mailhog
    ports:
      - "8025:8025"  # Web UI
      - "1025:1025"  # SMTP
    
  # All other services...
```

### 📋 **Example E2E Test**

```python
# tests/e2e/e2e_test.py
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_trading_workflow(
    test_environment,
    mongo_client,
    test_follower
):
    """Test complete workflow from signal to report."""
    
    # Step 1: Ingest trading signal
    signal = {
        "action": "BUY",
        "symbol": "QQQ",
        "quantity": 10,
        "price": 450.50
    }
    await ingest_signal(signal)
    
    # Step 2: Verify trade execution
    trade = await wait_for_trade_execution(signal["symbol"])
    assert trade["status"] == "FILLED"
    
    # Step 3: Check position creation
    position = await get_position(test_follower["_id"], signal["symbol"])
    assert position["quantity"] == signal["quantity"]
    
    # Step 4: Trigger report generation
    report = await generate_daily_report(test_follower["_id"])
    assert report["status"] == "completed"
    
    # Step 5: Verify email delivery
    emails = await get_captured_emails()
    assert len(emails) == 1
    assert "Daily Trading Report" in emails[0]["subject"]
```

### 🎯 **E2E Test Features**

- **🐳 Docker Environment** - Complete system in containers
- **🎭 Mock Services** - IBKR Gateway, SMTP server
- **📧 Email Capture** - MailHog for email verification
- **⏱️ Realistic Timing** - Production-like delays
- **📊 Full Workflow** - Signal → Trade → Report → Email

---

## 🏃 Running Tests

### 🧪 **Unit Tests**

```bash
# Run all unit tests
pytest tests/unit/

# Run specific test file
pytest tests/unit/test_models.py

# Run with verbose output
pytest tests/unit/ -v

# Run specific test
pytest tests/unit/test_models.py::TestFollowerModel::test_follower_creation
```

### 🔗 **Integration Tests**

```bash
# Start test databases
docker-compose -f docker-compose.test.yml up -d mongodb postgres

# Run integration tests
pytest tests/integration/

# Run with coverage
pytest tests/integration/ --cov=spreadpilot_core
```

### 🌐 **End-to-End Tests**

```bash
# Start E2E environment
docker-compose -f docker-compose.e2e.yml up -d

# Wait for services to be ready
./scripts/wait-for-e2e.sh

# Run E2E tests
pytest -m e2e tests/e2e/

# View captured emails
open http://localhost:8025

# Cleanup
docker-compose -f docker-compose.e2e.yml down -v
```

### 🚀 **All Tests**

```bash
# Run entire test suite
make test

# Run with coverage report
make test-coverage

# Run specific markers
pytest -m "not e2e"  # Skip E2E tests
pytest -m "unit or integration"  # Unit and integration only
```

---

## ✏️ Writing Tests

### 📋 **Test Structure Template**

```python
import pytest
from unittest.mock import Mock, patch

class TestComponentName:
    """Test cases for ComponentName."""
    
    @pytest.fixture
    def setup_data(self):
        """Set up test data."""
        return {
            "key": "value"
        }
    
    def test_feature_happy_path(self, setup_data):
        """Test feature with valid input."""
        # Arrange
        input_data = setup_data
        expected = "expected_result"
        
        # Act
        result = function_under_test(input_data)
        
        # Assert
        assert result == expected
    
    def test_feature_error_case(self):
        """Test feature with invalid input."""
        # Arrange
        invalid_input = None
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            function_under_test(invalid_input)
        
        assert "Invalid input" in str(exc_info.value)
    
    @pytest.mark.parametrize("input,expected", [
        ("a", 1),
        ("b", 2),
        ("c", 3),
    ])
    def test_multiple_cases(self, input, expected):
        """Test with multiple input variations."""
        assert function_under_test(input) == expected
```

### 🎭 **Mocking Guidelines**

```python
# Mock external services
@patch('spreadpilot_core.ibkr.client.IBKRClient')
def test_trade_execution(mock_ibkr):
    """Test trade execution with mocked IBKR."""
    # Configure mock
    mock_instance = mock_ibkr.return_value
    mock_instance.place_order.return_value = {
        "order_id": "123",
        "status": "FILLED"
    }
    
    # Test code that uses IBKR
    result = execute_trade("QQQ", 10, "BUY")
    
    # Verify mock was called correctly
    mock_instance.place_order.assert_called_once_with(
        symbol="QQQ",
        quantity=10,
        action="BUY"
    )
    assert result["order_id"] == "123"

# Mock async functions
@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality."""
    with patch('module.async_function') as mock:
        mock.return_value = asyncio.Future()
        mock.return_value.set_result("async_result")
        
        result = await function_under_test()
        assert result == "expected"
```

---

## 📊 Test Coverage

### 📈 **Coverage Requirements**

- **🎯 Overall**: >80% coverage
- **🧪 Unit Tests**: >90% coverage
- **🔗 Integration**: >70% coverage
- **🚨 Critical Paths**: 100% coverage

### 🔍 **Running Coverage**

```bash
# Generate coverage report
pytest --cov=spreadpilot_core --cov-report=html

# View HTML report
open htmlcov/index.html

# Generate terminal report
pytest --cov=spreadpilot_core --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov=spreadpilot_core --cov-fail-under=80
```

### 📋 **Coverage Configuration**

```ini
# .coveragerc
[run]
source = .
omit = 
    */tests/*
    */venv/*
    */__pycache__/*
    */migrations/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov
```

---

## 🚀 CI/CD Integration

SpreadPilot uses GitHub Actions for continuous integration and deployment. The pipeline automatically runs on every pull request and push to main branches.

### 🔄 **Automated Pipeline**

The CI/CD pipeline includes multiple stages that run in parallel for faster feedback:

#### 🎨 **Code Quality Checks**
- **Ruff**: Fast Python linter with extensive rule sets
- **Black**: Opinionated code formatter
- **Type Checking**: MyPy static type analysis

#### 🧪 **Test Execution**
- **Unit Tests**: Fast, isolated component tests
- **Integration Tests**: Database and service integration
- **E2E Tests**: Complete workflow validation using `docker-compose`

#### 🔒 **Security Scanning**
- **Trivy**: Vulnerability scanning for dependencies and containers
- **Container Scanning**: All Docker images scanned before deployment
- **SARIF Reports**: Security findings integrated with GitHub Security tab

### 📋 **CI Configuration**

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  pull_request:
    branches: [ main, develop ]
  push:
    branches: [ main, develop ]

jobs:
  python-lint:
    name: Python Linting (Ruff & Black)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          pip install ruff black
          ruff check . --output-format=github
          black --check --diff .

  python-tests:
    name: Python Unit Tests (Pytest)
    runs-on: ubuntu-latest
    services:
      mongodb:
        image: mongo:6.0
        options: >-
          --health-cmd "mongosh --eval 'db.adminCommand({ping: 1})'"
      redis:
        image: redis:7-alpine
    steps:
      - uses: actions/checkout@v4
      - run: |
          make init-dev
          pytest tests/unit/ -v --cov=. --cov-report=xml

  e2e-tests:
    name: End-to-End Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          docker-compose -f docker-compose.e2e.yml up \
            --exit-code-from e2e-tests --abort-on-container-exit

  security-scan:
    name: Security Scan (Trivy)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          format: 'sarif'
          output: 'trivy-results.sarif'
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

### 🛡️ **Quality Gates**

All pull requests must pass these checks before merging:

1. **Code Quality**
   - ✅ No linting errors (Ruff)
   - ✅ Code properly formatted (Black)
   - ✅ Conventional commit messages

2. **Testing**
   - ✅ All unit tests passing
   - ✅ Integration tests passing
   - ✅ E2E tests passing
   - ✅ Code coverage >80%

3. **Security**
   - ✅ No HIGH or CRITICAL vulnerabilities
   - ✅ Container images scanned
   - ✅ Dependencies up to date

4. **Build Verification**
   - ✅ All services build successfully
   - ✅ Frontend builds without errors

### 📊 **Coverage Integration**

Test coverage is automatically reported to pull requests:

```yaml
- name: Upload coverage reports
  uses: codecov/codecov-action@v4
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    file: ./coverage.xml
    flags: unittests
```

### 🔄 **Scheduled Scans**

Additional security and quality checks run on schedule:

```yaml
# .github/workflows/code-quality.yml
on:
  schedule:
    - cron: '0 9 * * 1'  # Weekly on Mondays

jobs:
  code-quality:
    steps:
      - run: |
          bandit -r . -f json -o bandit-report.json
          safety check --json --output safety-report.json
```
          MONGO_URI: mongodb://localhost:27017/test
      
      - name: Generate coverage report
        run: pytest --cov=spreadpilot_core --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### 🌐 **E2E Tests in CI**

```yaml
  e2e:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Start E2E environment
        run: docker-compose -f docker-compose.e2e.yml up -d
      
      - name: Wait for services
        run: |
          timeout 300 bash -c 'until docker-compose -f docker-compose.e2e.yml ps | grep -q "healthy"; do sleep 5; done'
      
      - name: Run E2E tests
        run: pytest -m e2e tests/e2e/ -v
      
      - name: Collect logs on failure
        if: failure()
        run: docker-compose -f docker-compose.e2e.yml logs
      
      - name: Cleanup
        if: always()
        run: docker-compose -f docker-compose.e2e.yml down -v
```

---

## 🎯 Best Practices

### ✅ **Do's**

- **📝 Clear Test Names** - Test names should describe what they test
- **🔍 Single Responsibility** - Each test should verify one behavior
- **🎭 Use Fixtures** - Share setup code with pytest fixtures
- **⚡ Keep Tests Fast** - Mock slow operations
- **📊 Test Edge Cases** - Include boundary and error conditions
- **🔄 Isolated Tests** - Tests should not affect each other

### ❌ **Don'ts**

- **🚫 No Sleep Statements** - Use proper waits/mocks instead
- **🚫 No Hard-coded Values** - Use fixtures and constants
- **🚫 No Test Dependencies** - Tests should run in any order
- **🚫 No Production Data** - Use test-specific data
- **🚫 No Network Calls** - Mock external services in unit tests

### 🏗️ **Test Patterns**

```python
# Arrange-Act-Assert pattern
def test_calculation():
    # Arrange
    calculator = Calculator()
    
    # Act
    result = calculator.add(2, 3)
    
    # Assert
    assert result == 5

# Given-When-Then pattern (BDD)
def test_order_placement():
    # Given a valid trading signal
    signal = create_test_signal()
    
    # When the order is placed
    order = place_order(signal)
    
    # Then the order should be filled
    assert order.status == "FILLED"
```

---

## 🔧 Troubleshooting

### 🚨 **Common Issues**

#### Database Connection Errors
```bash
# Check if test database is running
docker-compose -f docker-compose.test.yml ps

# View database logs
docker-compose -f docker-compose.test.yml logs mongodb
```

#### Flaky Tests
```python
# Use explicit waits instead of sleep
async def wait_for_condition(condition_func, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        if await condition_func():
            return True
        await asyncio.sleep(0.1)
    raise TimeoutError("Condition not met")

# Use in tests
await wait_for_condition(
    lambda: trade_exists(order_id)
)
```

#### Mock Not Working
```python
# Ensure correct import path
# Wrong
@patch('models.User')

# Correct - use full import path
@patch('spreadpilot_core.models.User')
```

---

## 📚 Additional Resources

- 📖 [Pytest Documentation](https://docs.pytest.org/)
- 🎭 [Python Mock Guide](https://docs.python.org/3/library/unittest.mock.html)
- 📊 [Coverage.py Documentation](https://coverage.readthedocs.io/)
- 🧪 [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)

---

<div align="center">

**🧪 Quality through comprehensive testing**

[⬅️ Back to Docs](./README.md) • [🏠 Home](../README.md)

</div>
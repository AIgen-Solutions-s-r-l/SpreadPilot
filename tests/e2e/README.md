# End-to-End Tests for SpreadPilot

This directory contains comprehensive end-to-end tests that validate the complete SpreadPilot trading workflow from signal ingestion to report generation.

## Overview

The E2E test suite simulates a production-like environment using Docker Compose and validates:

1. **Signal Ingestion**: From Google Sheets to MongoDB
2. **Trade Execution**: Through mock IBKR gateway
3. **Position Management**: Creation and updates
4. **Report Generation**: PDF creation and email delivery
5. **Alert System**: Notification routing
6. **Error Handling**: Edge cases and failure scenarios
7. **Performance Monitoring**: Metrics collection

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Google Sheets  │────▶│   Trading Bot    │────▶│  IBKR Gateway   │
│     (Mock)      │     │                  │     │     (Mock)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                           │
                               ▼                           │
                        ┌──────────────────┐              │
                        │    Admin API     │◀─────────────┘
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │     MongoDB      │
                        └──────────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
            ┌──────────────────┐  ┌──────────────────┐
            │  Report Worker   │  │   Alert Router   │
            └──────────────────┘  └──────────────────┘
                    │                     │
                    ▼                     ▼
            ┌──────────────────┐  ┌──────────────────┐
            │    MailHog       │  │    Telegram      │
            │  (Email Mock)    │  │     (Mock)       │
            └──────────────────┘  └──────────────────┘
```

## Prerequisites

- Docker and Docker Compose
- Python 3.11+
- pytest and pytest-asyncio

## Running the Tests

### 1. Start the test environment:

```bash
# Start all services
docker-compose -f docker-compose.e2e.yml up -d

# Wait for services to be healthy
docker-compose -f docker-compose.e2e.yml ps
```

### 2. Run the E2E tests:

```bash
# Run all E2E tests
pytest -m e2e tests/e2e/e2e_test.py -v

# Run specific test
pytest -m e2e tests/e2e/e2e_test.py::test_complete_trading_workflow -v

# Run with debug output
pytest -m e2e tests/e2e/e2e_test.py -v -s
```

### 3. View test artifacts:

- **MailHog UI**: http://localhost:8025 (view sent emails)
- **MongoDB**: mongodb://admin:password@localhost:27017
- **Mock IBKR Gateway**: http://localhost:5001/docs

### 4. Clean up:

```bash
docker-compose -f docker-compose.e2e.yml down -v
```

## Test Scenarios

### 1. Complete Trading Workflow (`test_complete_trading_workflow`)

Tests the happy path from signal to report:
- Signal ingestion from Google Sheets
- Order placement through IBKR
- Position tracking
- Report generation
- Email delivery

### 2. Error Handling (`test_error_handling_workflow`)

Tests system resilience:
- Invalid signals
- IBKR connection failures
- Risk limit violations
- Retry mechanisms

### 3. Performance Monitoring (`test_performance_monitoring`)

Tests metrics collection:
- Trade performance tracking
- Win rate calculation
- P&L aggregation
- Sharpe ratio computation

## Mock Services

### IBKR Gateway Mock

A FastAPI application that simulates IBKR Gateway endpoints:
- `/api/v1/orders` - Place orders
- `/api/v1/positions` - Get positions
- `/api/v1/account` - Account information

### MailHog

Captures all SMTP traffic for email verification:
- SMTP Port: 1025
- Web UI: http://localhost:8025

## Debugging

### View logs:

```bash
# All services
docker-compose -f docker-compose.e2e.yml logs -f

# Specific service
docker-compose -f docker-compose.e2e.yml logs -f trading-bot-test
```

### Access MongoDB:

```bash
mongosh "mongodb://admin:password@localhost:27017/spreadpilot_test?authSource=admin"
```

### Inspect failed tests:

```bash
# Run with pytest debugging
pytest -m e2e tests/e2e/e2e_test.py --pdb

# Generate HTML report
pytest -m e2e tests/e2e/e2e_test.py --html=report.html
```

## CI/CD Integration

The E2E tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run E2E Tests
  run: |
    docker-compose -f docker-compose.e2e.yml up -d
    sleep 30  # Wait for services
    pytest -m e2e tests/e2e/e2e_test.py
  
- name: Cleanup
  if: always()
  run: docker-compose -f docker-compose.e2e.yml down -v
```

## Extending the Tests

To add new test scenarios:

1. Add test function to `e2e_test.py`
2. Mark with `@pytest.mark.e2e`
3. Use existing fixtures or create new ones
4. Follow the pattern of existing tests

Example:

```python
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_new_scenario(test_environment, mongo_client):
    # Your test logic here
    pass
```
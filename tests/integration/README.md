# SpreadPilot Integration Tests

This directory contains integration tests for the SpreadPilot system, verifying that all microservices work together correctly.

## Overview

The integration tests focus on the key workflows of the system:

1. **Trading Signal Processing Flow**:
   - Test that a trading signal from Google Sheets is correctly processed by the trading-bot
   - Verify that orders are placed with IBKR
   - Confirm that trade records are stored in the database

2. **Assignment Detection and Handling**:
   - Test the detection of assignments (short-leg)
   - Verify the re-balancing mechanism via long-leg exercise
   - Confirm that alerts are sent via the alert-router

3. **Reporting Flow**:
   - Test the P&L calculation process
   - Verify the generation of monthly reports
   - Confirm that reports are sent via email

4. **Admin API and Dashboard**:
   - Test follower CRUD operations
   - Verify the enable/disable functionality
   - Test manual close commands
   - Test dashboard data endpoints and WebSocket functionality

## Setup

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- MongoDB (via Docker Compose)

### Environment Setup

1. Create a virtual environment and install the development requirements:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

2. Start the MongoDB service using Docker Compose:

```bash
docker-compose up -d mongodb
```

3. Set the environment variables for the tests:

```bash
export GOOGLE_CLOUD_PROJECT=spreadpilot-test
export TESTING=true
export MONGO_URI=mongodb://localhost:27017
export MONGO_DB_NAME=spreadpilot_test
```

## Running the Tests

### Using Docker Compose

The recommended way to run integration tests is using Docker Compose, which automatically sets up all required services:

1. Start the required services:

```bash
docker-compose up -d mongodb
```

2. Run the tests:

```bash
pytest tests/integration/
```

### Running Specific Tests

To run a specific test file:

```bash
pytest tests/integration/test_admin_api.py
```

To run a specific test:

```bash
pytest tests/integration/test_admin_api.py::test_create_follower
```

### Test Coverage

To run tests with coverage reporting:

```bash
pytest --cov=admin_api --cov=alert_router --cov=report_worker --cov=trading-bot tests/integration/
```

## Test Structure

- `conftest.py`: Contains pytest fixtures for setting up test dependencies
- `test_trading_flow.py`: Tests for the trading signal processing flow
- `test_assignment_flow.py`: Tests for assignment detection and handling
- `test_reporting_flow.py`: Tests for P&L calculation and reporting
- `test_admin_api.py`: Tests for the admin API and dashboard

## MongoDB Test Setup

The integration tests use MongoDB for data storage. The tests use the `testcontainers` library to automatically start and manage a MongoDB container for testing. This approach ensures:

1. Tests run against a real MongoDB instance
2. Each test gets a clean, isolated database
3. No manual setup is required

The MongoDB connection is configured in `conftest.py` using the following fixtures:

- `mongodb_container`: Starts and manages the MongoDB container
- `test_mongo_db`: Creates a unique test database for each test function
- `admin_api_client`: Configures the admin API to use the test database

## Mocks

The integration tests use mocks for external dependencies:

- IBKR Gateway: Mocked to simulate trading operations
- Google Sheets: Mocked to provide test trading signals
- Email/Telegram: Mocked to verify notifications

## Troubleshooting

If you encounter issues with the tests:

1. Ensure Docker and Docker Compose are installed and running
2. Check that the MongoDB service is running: `docker-compose ps`
3. Verify that environment variables are set correctly
4. Check the logs for each service: `docker-compose logs mongodb`
5. If tests fail with connection errors, try restarting the MongoDB service:
   ```bash
   docker-compose down
   docker-compose up -d mongodb
   ```
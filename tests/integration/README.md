# SpreadPilot Integration Tests

This directory contains integration tests for the SpreadPilot system, verifying that all microservices work together correctly.

## Overview

The integration tests focus on the key workflows of the system:

1. **Trading Signal Processing Flow**:
   - Test that a trading signal from Google Sheets is correctly processed by the trading-bot
   - Verify that orders are placed with IBKR
   - Confirm that trade records are stored in Firestore

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

## Setup

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Google Cloud SDK (for Firestore emulator)

### Environment Setup

1. Create a virtual environment and install the development requirements:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-dev.in
```

2. Start the Firestore emulator:

```bash
gcloud beta emulators firestore start --host-port=localhost:8080
```

3. Set the environment variables for the tests:

```bash
export FIRESTORE_EMULATOR_HOST=localhost:8080
export GOOGLE_CLOUD_PROJECT=spreadpilot-test
export TESTING=true
```

## Running the Tests

To run all integration tests:

```bash
pytest tests/integration/
```

To run a specific test file:

```bash
pytest tests/integration/test_trading_flow.py
```

To run a specific test:

```bash
pytest tests/integration/test_trading_flow.py::test_process_trading_signal
```

## Test Structure

- `conftest.py`: Contains pytest fixtures for setting up test dependencies
- `test_trading_flow.py`: Tests for the trading signal processing flow
- `test_assignment_flow.py`: Tests for assignment detection and handling
- `test_reporting_flow.py`: Tests for P&L calculation and reporting
- `test_admin_api.py`: Tests for the admin API and dashboard

## Mocks

The integration tests use mocks for external dependencies:

- IBKR Gateway: Mocked to simulate trading operations
- Google Sheets: Mocked to provide test trading signals
- Email/Telegram: Mocked to verify notifications

## Troubleshooting

If you encounter issues with the tests:

1. Ensure all services are running correctly in Docker
2. Check that the Firestore emulator is running
3. Verify that environment variables are set correctly
4. Check the logs for each service for detailed error messages
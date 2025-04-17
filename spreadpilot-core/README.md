# SpreadPilot Core Library

This is the core library for the SpreadPilot platform, a copy-trading solution for QQQ options strategies.

## Overview

The `spreadpilot-core` library provides shared functionality used by all SpreadPilot microservices, including:

- Structured logging with OpenTelemetry integration
- IBKR API client wrapper
- Firestore data models
- Utility functions for report generation (PDF, Excel)
- Alert routing (Telegram, Email)

## Modules

- `logging`: Structured logging with GCP Cloud Logging integration
- `ibkr`: Interactive Brokers API client wrapper
- `models`: Pydantic models for Firestore data
- `utils`: Utility functions for report generation, alerts, etc.

## Installation

For development:

```bash
cd spreadpilot-core
pip install -e .
```

## Usage

```python
from spreadpilot_core.logging import get_logger
from spreadpilot_core.ibkr import IBKRClient
from spreadpilot_core.models import Follower, Position, Trade
from spreadpilot_core.utils import generate_pdf_report

# Example usage
logger = get_logger(__name__)
logger.info("Starting SpreadPilot service")

# Create IBKR client
ibkr_client = IBKRClient(username="user", password="pass")

# Create a follower model
follower = Follower(
    id="follower-123",
    email="user@example.com",
    ibkr_username="ibuser",
    commission_pct=10.0,
    enabled=True
)
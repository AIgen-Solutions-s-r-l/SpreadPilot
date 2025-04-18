# SpreadPilot System Architecture

## Overview

SpreadPilot is a copy-trading platform for QQQ options strategies, designed to automatically replicate a Google Sheets algorithm strategy to Interactive Brokers (IBKR) accounts. The system is built as a set of microservices deployed on Google Cloud Platform.

## System Components

![SpreadPilot System Architecture](./images/system-architecture.png)

### Core Services

#### Trading Bot

The Trading Bot is the central component of the SpreadPilot system. It is responsible for:

- Connecting to Interactive Brokers (IBKR) via the IB Gateway
- Polling Google Sheets for trading signals
- Executing orders on behalf of followers
- Detecting and handling assignments
- Managing positions and tracking P&L

**Technology:** Python with asyncio/aiohttp

#### Watchdog

The Watchdog service monitors the health of critical components and ensures system reliability:

- Continuously checks the health of the Trading Bot and IB Gateway
- Attempts to restart failed components
- Updates component status in Firestore
- Triggers alerts for critical failures

**Technology:** Python with asyncio/aiohttp

#### Admin API

The Admin API provides backend services for the administrative dashboard:

- REST API for follower management and system configuration
- WebSocket API for real-time log streaming
- Authentication and authorization

**Technology:** Python with FastAPI

#### Report Worker

The Report Worker generates periodic reports for followers:

- Calculates daily and monthly P&L
- Generates PDF and Excel reports
- Emails reports to followers

**Technology:** Python with Flask (for Pub/Sub handling)

#### Alert Router

The Alert Router manages the delivery of critical notifications:

- Receives alert events via Pub/Sub
- Routes alerts to appropriate channels (Telegram, email)
- Formats messages with deep links to the dashboard

**Technology:** Python with FastAPI

#### Frontend

The Frontend provides an administrative dashboard for monitoring and managing the system:

- Authentication and user management
- Follower management interface
- Real-time log console
- Manual command execution

**Technology:** React, TypeScript, Vite, Tailwind CSS

### Shared Library

#### SpreadPilot Core

The SpreadPilot Core library provides shared functionality used by all services:

- IBKR client wrapper
- Firestore models (Position, Trade, Follower, Alert)
- Structured logging
- Utilities (email, Telegram, PDF, Excel, time)

**Technology:** Python package

### Infrastructure Services

#### IB Gateway

The IB Gateway provides connectivity to Interactive Brokers:

- Handles authentication to IBKR
- Manages the trading session
- Provides API access to IBKR functionality

**Technology:** IB Gateway container

#### Firestore

Firestore serves as the primary database for the system:

- Stores follower information
- Tracks positions and trades
- Maintains system status and configuration

**Technology:** Google Cloud Firestore (Native mode)

### Observability Services

#### OpenTelemetry Collector

The OpenTelemetry Collector gathers telemetry data from all services:

- Collects metrics, traces, and logs
- Exports data to Prometheus and Cloud Monitoring

**Technology:** OpenTelemetry Collector

#### Prometheus

Prometheus stores and processes metrics data:

- Time-series database for metrics
- Query engine for metrics data
- Alert rules for monitoring

**Technology:** Prometheus

#### Grafana

Grafana provides visualization and dashboards:

- Customizable dashboards for system metrics
- Visualization of performance data
- Alert management

**Technology:** Grafana

## Communication Patterns

### Synchronous Communication

- **REST APIs**: Used for request-response interactions between services and clients
- **WebSockets**: Used for real-time communication between the Admin API and Frontend

### Asynchronous Communication

- **Pub/Sub**: Used for event-driven communication between services
  - Alert events from Trading Bot to Alert Router
  - Report generation triggers to Report Worker

## Data Flow

1. **Trading Signal Flow**:
   - Google Sheets algorithm generates trading signals
   - Trading Bot polls Google Sheets for signals
   - Trading Bot executes orders via IB Gateway
   - Trading Bot stores position and trade data in Firestore

2. **Reporting Flow**:
   - Cloud Scheduler triggers Report Worker via Pub/Sub
   - Report Worker retrieves position data from Firestore
   - Report Worker calculates P&L and generates reports
   - Report Worker emails reports to followers

3. **Alerting Flow**:
   - Services generate alert events
   - Alert events are published to Pub/Sub
   - Alert Router receives events and formats messages
   - Alert Router sends notifications via Telegram and email

4. **Monitoring Flow**:
   - Services emit metrics and logs
   - OpenTelemetry Collector gathers telemetry data
   - Prometheus stores and processes metrics
   - Grafana visualizes metrics in dashboards

## Security

- **Authentication**: JWT-based authentication for Admin API and Frontend
- **Authorization**: Role-based access control for administrative functions
- **Secrets Management**: GCP Secret Manager for sensitive configuration
- **Network Security**: Private VPC for service-to-service communication

## Scalability

- **Horizontal Scaling**: Services deployed as containers on Cloud Run
- **Statelessness**: Services designed to be stateless for easy scaling
- **Database Scaling**: Firestore automatically scales with demand

## Resilience

- **Health Monitoring**: Watchdog service monitors critical components
- **Auto-Recovery**: Failed components are automatically restarted
- **Alerting**: Critical failures trigger notifications
- **Logging**: Comprehensive logging for troubleshooting

## Code Organization

### Folder Structure Convention

SpreadPilot uses a consistent folder structure convention:

- **Hyphenated Directory Names**: All service directories use hyphenated names (`trading-bot`, `admin-api`, etc.)
- **Python Package Imports**: Each service directory contains `__init__.py` files to make it importable as a Python package
- **Import Pattern**: When importing from hyphenated directories in Python code, `importlib.import_module()` is used:

```python
import importlib
trading_bot_service = importlib.import_module('trading-bot.app.service.signals')
```

This convention ensures consistency across deployment and testing environments while maintaining Python import compatibility.

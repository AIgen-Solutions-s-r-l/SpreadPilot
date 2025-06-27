# SpreadPilot System Architecture

## Overview

SpreadPilot is a copy-trading platform for QQQ options strategies, designed to automatically replicate a Google Sheets algorithm strategy to Interactive Brokers (IBKR) accounts. The system is built as a set of microservices deployed on Google Cloud Platform.

## System Components

![SpreadPilot System Architecture](./images/system-architecture.png)

### Core Services

#### Signal Listener

The Signal Listener is a scheduled service that handles trading signal acquisition:

- Scheduled to run at 09:27 EST daily using APScheduler
- Connects to Google Sheets to poll for today's trading signals
- Waits for ticker cells to be filled before processing signals
- Publishes signals to Redis Pub/Sub channel for consumption by Trading Bot
- Built with timezone-aware scheduling for US/Eastern time zone

**Technology:** Python with APScheduler, Redis, gspread

#### Trading Bot

The Trading Bot is the central component of the SpreadPilot system. It is responsible for:

- Consuming trading signals from Redis Pub/Sub channel
- Connecting to Interactive Brokers (IBKR) via the IB Gateway
- Executing orders on behalf of followers
- Detecting and handling assignments
- Managing positions and tracking P&L

**Technology:** Python with asyncio/aiohttp

#### Watchdog

The Watchdog service monitors the health of critical components and ensures system reliability:

- Continuously checks the health of the Trading Bot and IB Gateway
- Attempts to restart failed components
- Updates component status in the database (MongoDB)
- Triggers alerts for critical failures

**Technology:** Python with asyncio/aiohttp

#### Admin API

The Admin API provides backend services for the administrative dashboard:

- REST API for follower management and system configuration
- WebSocket API for real-time log streaming
- Authentication and authorization
- JWT-based security with password hashing
- MongoDB integration for data persistence

**Technology:** Python with FastAPI

#### Report Worker

The Report Worker generates periodic reports for followers:

- Calculates daily and monthly P&L
- Generates PDF and Excel reports
- Emails reports to followers
- Receives job requests via Google Cloud Pub/Sub
- Securely loads secrets from MongoDB

**Technology:** Python with Flask (for Pub/Sub handling)

#### Alert Router

The Alert Router manages the delivery of critical notifications:

- Receives alert events via Pub/Sub
- Routes alerts to appropriate channels (Telegram, email)
- Formats messages with deep links to the dashboard
- Securely loads secrets from MongoDB
- Provides health check endpoint

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
- Database models (Position, Trade, Follower, Alert) - currently using MongoDB
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

#### Redis

Redis serves as the in-memory data store for real-time signal processing:

- Pub/Sub messaging for trading signals between Signal Listener and Trading Bot
- Caching layer for frequently accessed data
- High-performance data structure store

**Technology:** Redis (Self-hosted via Docker)

#### MongoDB

MongoDB serves as the primary database for the system:

- Stores follower information
- Tracks positions and trades
- Maintains system status and configuration
- Stores secrets for secure access by services

**Technology:** MongoDB (Self-hosted via Docker or potentially Atlas)

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

- **Redis Pub/Sub**: Used for real-time trading signal distribution
  - Signal Listener publishes trading signals to Redis channel
  - Trading Bot subscribes to signals from Redis channel
- **Google Cloud Pub/Sub**: Used for event-driven communication between services
  - Alert events from Trading Bot to Alert Router
  - Report generation triggers to Report Worker

## Data Flow

1. **Trading Signal Flow**:
   - Google Sheets algorithm generates trading signals
   - Signal Listener polls Google Sheets for signals at 09:27 EST daily
   - Signal Listener publishes validated signals to Redis Pub/Sub channel
   - Trading Bot consumes signals from Redis Pub/Sub channel
   - Trading Bot executes orders via IB Gateway
   - Trading Bot stores position and trade data in MongoDB

2. **Reporting Flow**:
   - Cloud Scheduler triggers Report Worker via Pub/Sub
   - Report Worker retrieves position data from MongoDB
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
- **Secrets Management**: MongoDB and GCP Secret Manager for sensitive configuration
- **Network Security**: Private VPC for service-to-service communication
- **Password Security**: Bcrypt hashing for password storage

## Scalability

- **Horizontal Scaling**: Services deployed as containers on Cloud Run
- **Statelessness**: Services designed to be stateless for easy scaling
- **Database Scaling**: MongoDB can be scaled horizontally (sharding) or vertically as needed.

## Resilience

- **Health Monitoring**: Watchdog service monitors critical components
- **Auto-Recovery**: Failed components are automatically restarted
- **Alerting**: Critical failures trigger notifications
- **Logging**: Comprehensive logging for troubleshooting
- **Health Checks**: Services provide health check endpoints

## Code Organization

### Folder Structure Convention

SpreadPilot uses a consistent folder structure convention:

- **Hyphenated Directory Names**: All service directories use hyphenated names (`trading-bot`, `admin-api`, `alert-router`, `report-worker`, etc.)
- **Python Package Imports**: Each service directory contains `__init__.py` files to make it importable as a Python package
- **Import Pattern**: When importing from hyphenated directories in Python code, `importlib.import_module()` is used:

```python
import importlib
trading_bot_service = importlib.import_module('trading-bot.app.service.signals')
```

This convention ensures consistency across deployment and testing environments while maintaining Python import compatibility.

## Recent Architectural Improvements

### Service Consolidation

To improve maintainability and reduce duplication, the following services have been consolidated:

1. **Admin API**: Consolidated three different implementations (`admin_api/`, `admin-api/`, and `simple-admin-api/`) into a single, unified version in `admin-api/` with:
   - Structured modular architecture
   - Async MongoDB connection
   - JWT authentication with password hashing
   - WebSocket support for real-time updates
   - Comprehensive documentation

2. **Alert Router**: Consolidated two different implementations (`alert_router/` and `alert-router/`) into a single, unified version in `alert-router/` with:
   - Structured project layout
   - Secret loading functionality
   - PubSub message handling
   - Comprehensive documentation

3. **Report Worker**: Consolidated two different implementations (`report_worker/` and `report-worker/`) into a single, unified version in `report-worker/` with:
   - Structured project layout
   - Secret loading functionality
   - PubSub message handling for report generation
   - MongoDB integration
   - Comprehensive documentation

These consolidations have improved maintainability, reduced duplication, established a consistent naming convention, and enhanced documentation across all services.

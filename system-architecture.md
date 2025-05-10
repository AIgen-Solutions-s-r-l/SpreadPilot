+++
id = "DOC-ARCH-SYSTEM-ARCHITECTURE"
title = "SpreadPilot System Architecture"
context_type = "documentation"
scope = "Overall system architecture"
target_audience = ["product managers", "architects", "engineers"]
granularity = "high-level to detailed"
status = "published"
last_updated = "2025-05-10"
tags = ["architecture", "system-design", "components", "deployment", "data", "cross-cutting-concerns"]
related_context = [
    ".ruru/tasks/TASK-WRITER-20250510-101957-ARCH-DOC.md",
    ".ruru/tasks/TASK-PYDEV-20250510-091336-TRADINGBOT.md",
    ".ruru/tasks/TASK-PYDEV-20250510-092046-WATCHDOG.md",
    ".ruru/tasks/TASK-PYDEV-20250510-092435-ADMINAPI.md",
    ".ruru/tasks/TASK-PYDEV-20250510-093122-REPORTWORKER.md",
    ".ruru/tasks/TASK-PYDEV-20250510-093633-ALERTROUTER.md",
    ".ruru/tasks/TASK-REACT-20250510-094241-FRONTEND.md",
    ".ruru/tasks/TASK-DIAGRAMER-20250510-094835-COMPONENT-INTERACTION.md",
    ".ruru/tasks/TASK-DIAGRAMER-20250510-101707-DEPLOYMENT-ARCHITECTURE.md",
    ".ruru/tasks/TASK-DIAGRAMER-20250510-101904-CROSS-CUTTING-CONCERNS.md",
    ".ruru/tasks/TASK-DIAGRAMER-20250510-094928-DATA-ARCHITECTURE.md"
]
+++

# SpreadPilot System Architecture

This document provides a comprehensive overview of the SpreadPilot trading system's software architecture, detailing its components, their interactions, deployment model, data structure, and key cross-cutting concerns.

## Component Documentation

This section provides detailed analysis findings for each core component of the SpreadPilot system.

### Trading Bot

**Purpose & Core Functionality**:
The **Trading Bot** ([`trading-bot/`](trading-bot/)) is a service responsible for automated trading operations based on signals. Its primary responsibilities and business capabilities include:
1.  **Signal Consumption**: It polls an external source (Google Sheets, as configured in [`trading-bot/app/sheets.py`](trading-bot/app/sheets.py:1)) for trading signals. These signals dictate the strategy, quantity, and strike prices for trades.
2.  **Order Execution**: Upon receiving a valid signal, it connects to Interactive Brokers (IBKR) for specified followers (defined in `spreadpilot-core/models/follower.py`) and attempts to place vertical spread option orders. This is managed by [`trading-bot/app/service/ibkr.py`](trading-bot/app/service/ibkr.py:1) which uses [`spreadpilot-core/spreadpilot_core/ibkr/client.py`](spreadpilot-core/spreadpilot_core/ibkr/client.py:1).
3.  **Position Management**: It tracks current positions for each follower, storing this data in MongoDB (models like [`spreadpilot-core/spreadpilot_core/models/position.py`](spreadpilot-core/spreadpilot_core/models/position.py:1)). It periodically checks for assignments (unexpected exercise of short options) and can attempt to compensate by exercising corresponding long options. This is handled by [`trading-bot/app/service/positions.py`](trading-bot/app/service/positions.py:1).
4.  **Follower Management**: It loads and manages a list of active "followers" from MongoDB. Trades are executed on behalf of these followers, each having their own IBKR credentials and settings.
5.  **P&L Calculation (Basic)**: It can fetch P&L data from IBKR.
6.  **Alerting**: It generates alerts for significant events (e.g., insufficient margin, order rejections, assignments) and stores them in MongoDB (model [`spreadpilot-core/spreadpilot_core/models/alert.py`](spreadpilot-core/spreadpilot_core/models/alert.py:1)). Critical alerts can trigger notifications (e.g., Telegram). This is managed by [`trading-bot/app/service/alerts.py`](trading-bot/app/service/alerts.py:1).
7.  **Configuration Management**: It loads its operational parameters (IBKR connection details, polling intervals, API keys, etc.) from environment variables and a configuration file ([`trading-bot/app/config.py`](trading-bot/app/config.py:1)). Secrets like API keys and IBKR passwords are pre-loaded from a secure MongoDB collection at startup ([`trading-bot/app/main.py`](trading-bot/app/main.py:1)).
8.  **Original Strategy Handler**: Includes a component ([`trading-bot/app/service/original_strategy_handler.py`](trading-bot/app/service/original_strategy_handler.py:1)) for an EMA crossover strategy, suggesting it can support multiple trading strategies.

The **SpreadPilot Core** ([`spreadpilot-core/`](spreadpilot-core/)) provides shared, reusable components and models for various services within the SpreadPilot ecosystem, including the Trading Bot. Its core functionalities relevant to the Trading Bot are:
1.  **IBKR Client Wrapper** ([`spreadpilot-core/spreadpilot_core/ibkr/client.py`](spreadpilot-core/spreadpilot_core/ibkr/client.py:1)): A Python client that wraps the `ib_insync` library to simplify interactions with the Interactive Brokers API for actions like placing orders, fetching positions, checking margin, and getting P&L.
2.  **Database Models** ([`spreadpilot-core/spreadpilot_core/models/`](spreadpilot-core/spreadpilot_core/models/)): Pydantic models defining the structure for data stored in MongoDB (e.g., `Follower`, `Position`, `Trade`, `Alert`).
3.  **MongoDB Utilities** ([`spreadpilot-core/spreadpilot_core/db/mongodb.py`](spreadpilot-core/spreadpilot_core/db/mongodb.py:1)): Helper functions for connecting to and interacting with MongoDB using `motor`.
4.  **Logging Utilities** ([`spreadpilot-core/spreadpilot_core/logging/logger.py`](spreadpilot-core/spreadpilot_core/logging/logger.py:1)): Standardized logging setup, including optional OpenTelemetry integration.
5.  **Utility Functions** ([`spreadpilot-core/spreadpilot_core/utils/`](spreadpilot-core/spreadpilot_core/utils/)): Various helper utilities, such as time manipulation ([`spreadpilot-core/spreadpilot_core/utils/time.py`](spreadpilot-core/spreadpilot_core/utils/time.py:1)), secret management ([`spreadpilot-core/spreadpilot_core/utils/secrets.py`](spreadpilot-core/spreadpilot_core/utils/secrets.py:1)), and Telegram notifications ([`spreadpilot-core/spreadpilot_core/utils/telegram.py`](spreadpilot-core/spreadpilot_core/utils/telegram.py:1)).

The Trading Bot acts as an execution engine, taking signals and managing trades for multiple users (followers) by leveraging the foundational services provided by SpreadPilot Core.

**Technical Implementation**:
**Languages & Frameworks:**
*   **Python**: The primary language for both `trading-bot` and `spreadpilot-core`.
*   **FastAPI**: The `trading-bot` ([`trading-bot/app/main.py`](trading-bot/app/main.py:1)) is built as a FastAPI application, providing a simple HTTP API for health checks, status, and manual signal/close operations.
*   **Pydantic**: Used extensively in `spreadpilot-core/models/` for data validation and settings management ([`trading-bot/app/config.py`](trading-bot/app/config.py:1)).
*   **`ib_insync`**: The core library used by [`spreadpilot-core/spreadpilot_core/ibkr/client.py`](spreadpilot-core/spreadpilot_core/ibkr/client.py:1) for interacting with the Interactive Brokers API.
*   **`motor`**: Asynchronous Python driver for MongoDB, used in [`spreadpilot-core/spreadpilot_core/db/mongodb.py`](spreadpilot-core/spreadpilot_core/db/mongodb.py:1) and various service components in `trading-bot` for database interactions.
*   **`aiohttp`**: Used by [`trading-bot/app/sheets.py`](trading-bot/app/sheets.py:1) for asynchronous HTTP requests to Google Sheets API.
*   **Asyncio**: Leveraged throughout the `trading-bot` and `spreadpilot-core` for concurrent operations, especially for I/O-bound tasks like API calls (IBKR, Google Sheets, MongoDB) and background polling loops (e.g., [`trading-bot/app/service/base.py`](trading-bot/app/service/base.py:1) `run` method, [`trading-bot/app/service/positions.py`](trading-bot/app/service/positions.py:1) `check_positions_periodically`).

**Design Patterns & Architectural Approaches:**
*   **Service-Oriented Architecture (SOA) / Microservices (Implicit)**: The separation of `trading-bot` and `spreadpilot-core` suggests a modular design. The `trading-bot` itself is a distinct service.
*   **Manager Pattern**: The `trading-bot/app/service/` directory contains several manager classes (e.g., `IBKRManager`, `PositionManager`, `AlertManager`, `SignalProcessor`) that encapsulate specific domains of responsibility within the `TradingService`. This promotes separation of concerns.
*   **Configuration Management**: Settings are centralized in [`trading-bot/app/config.py`](trading-bot/app/config.py:1) using Pydantic's `BaseSettings` for loading from environment variables and `.env` files. Secrets are explicitly pre-loaded from MongoDB at startup.
*   **Asynchronous Programming**: Heavy use of `async/await` for non-blocking I/O operations, crucial for a trading bot that needs to remain responsive while interacting with multiple external services.
*   **Dependency Injection (Lightweight/Implicit)**: The `TradingService` initializes and holds references to its managers and clients (e.g., `sheets_client`, `mongo_db`). These are passed to the managers upon their instantiation.
*   **State Management**: The `TradingService` maintains its operational state (e.g., `ServiceStatus` enum in [`trading-bot/app/service/base.py`](trading-bot/app/service/base.py:35)) and caches active followers. Positions are persisted in MongoDB.
*   **Modular Core Library**: `spreadpilot-core` acts as a shared library, providing common functionalities (IBKR client, DB models, logging, utils) to potentially multiple services, promoting code reuse and consistency.
*   **Polling**: The primary mechanism for fetching signals from Google Sheets is polling ([`trading-bot/app/service/base.py`](trading-bot/app/service/base.py:183)). Position checks are also done periodically.
*   **Error Handling**: `try-except` blocks are used for handling exceptions from external API calls and other operations. A global exception handler is present in [`trading-bot/app/main.py`](trading-bot/app/main.py:269).

### Watchdog

**Purpose & Core Functionality**:
The Watchdog component ([`watchdog/main.py`](watchdog/main.py:0)) serves as a monitoring service within the SpreadPilot trading system. Its primary responsibility is to periodically check the health and operational status of critical dependent services.

Core functionalities include:
- **Scheduled Health Checks**: Regularly polls a predefined list of services at a configurable interval (`CHECK_INTERVAL_SECONDS`, default 60s).
- **Service Monitoring**: Currently configured to monitor: `firestore`, `trading-bot`, `ib-gateway`, and `otel-collector`.
- **Status Logging**: Logs the start and completion of health check cycles, and the (simulated) status of each monitored service.
- **Error Reporting (Placeholder)**: Includes a placeholder to take action (e.g., notification, remediation) if a service is found to be unhealthy. The actual implementation of these actions is not yet present.

The business capability it provides is increased system reliability and awareness by detecting and (potentially) reacting to failures in other parts of the system.

**Technical Implementation**:
- **Language**: Python (version 3.10, as specified in [`watchdog/Dockerfile`](watchdog/Dockerfile:2)).
- **Frameworks/Libraries**: Primarily uses the Python standard library.
    - `logging` for application logging.
    - `time` for managing check intervals (`time.sleep()`).
    - `os` for accessing environment variables (e.g., `WATCHDOG_CHECK_INTERVAL_SECONDS`).
- **Design Patterns/Architectural Approaches**:
    - **Scheduled Polling**: The core mechanism is a `while True` loop that periodically iterates through services and performs health checks.
    - **Centralized Monitoring**: Acts as a central point for observing the health of other services.
    - **Configuration via Environment Variables**: Allows some parameters (like check interval) to be configured externally.
    - **Placeholder Implementation**: The actual health check logic in `check_service_health()` is currently a placeholder and simulates success. A real implementation would require specific checks for each service type (e.g., HTTP pings, DB connections).

### Admin API

**Purpose & Core Functionality**:
The `admin-api` component serves as the backend for the SpreadPilot administration interface. Its primary responsibilities include:
*   **Follower Management**:
    *   Registering new followers (users/accounts that replicate trades).
    *   Listing existing followers.
    *   Enabling/disabling individual followers.
    *   Triggering commands to close all positions for a specific follower (likely by communicating with the `trading-bot`).
*   **Dashboard Backend**:
    *   Providing summarized data and statistics for the admin dashboard (e.g., follower counts).
    *   Serving real-time updates (primarily follower status) to connected dashboard clients via WebSockets.
    *   Exposing placeholder endpoints for alerts and performance metrics, suggesting future expansion.
*   **System Health**:
    *   Providing a basic health check endpoint (`/health`).

The core business capability is to provide administrative oversight and control over the follower accounts within the SpreadPilot trading system, and to offer a real-time view of their status.

**Technical Implementation**:
*   **Language**: Python (version not explicitly specified, but assumed to be 3.x compatible with FastAPI).
*   **Framework**: FastAPI, a modern, high-performance web framework for building APIs with Python.
*   **Asynchronous Operations**: Leverages `asyncio` and `async/await` syntax extensively, suitable for I/O-bound operations like database interactions and WebSocket communication. `anyio` is used for managing background tasks.
*   **Configuration Management**: Uses Pydantic settings (via `admin_api.app.core.config.Settings`) to manage application configuration. Secrets can be pre-loaded from MongoDB into environment variables at startup.
*   **Database**: Interacts with MongoDB for data persistence (e.g., storing follower information). Uses `motor` (an async MongoDB driver).
*   **Modularity**: The code is structured into modules for API endpoints, services, schemas (Pydantic models), database interaction, and core configuration. `importlib` is used for dynamic imports in some places, which might be a pattern to reduce import cycles or manage optional dependencies, though its specific benefit here isn't immediately obvious without deeper context.
*   **Dependency Injection**: FastAPI's `Depends` system is used to manage dependencies, such as injecting database connections and service instances into endpoint functions.
*   **Background Tasks**: A background task (`periodic_follower_update_task`) is managed using `anyio.create_task_group` within the FastAPI lifespan event handler to periodically fetch and broadcast follower updates via WebSockets.
*   **API Versioning**: API endpoints are prefixed with `/api/v1`, indicating a versioned API.
*   **CORS**: Configured with permissive CORS settings (`allow_origins=["*"]`), which should be restricted in production.
*   **Logging**: Uses a centralized logger from `spreadpilot_core.logging`.

### Report Worker

**Purpose & Core Functionality**:
The `report-worker` component is responsible for the following:
*   **Automated Report Generation**: It generates periodic financial reports for followers of the trading strategy. This includes:
    *   **Daily P&L Calculation**: Calculates and stores the profit and loss for all closed positions on a given day.
    *   **Monthly Performance Reports**: Aggregates daily P&L data to produce comprehensive monthly reports. These reports detail overall P&L, commission calculations, and net P&L for each follower.
*   **Report Distribution**: It handles the distribution of these reports, primarily via email, to the respective followers. Reports are generated in PDF and Excel formats.
*   **Event-Driven Processing**: The worker is designed to be triggered by Pub/Sub messages, allowing for scheduled or event-driven report generation (e.g., daily P&L calculation at market close, monthly report generation at the start of a new month).

The core business capability is to provide transparent and timely performance reporting to clients (followers), ensuring they are informed about their investment's progress and associated fees.

**Technical Implementation**:
*   **Language**: Python 3.x
*   **Framework**: Flask is used as the web framework to handle incoming HTTP requests from Google Cloud Pub/Sub (push subscriptions).
*   **Primary Libraries**:
    *   `motor`: Asynchronous Python driver for MongoDB, used for all database interactions (fetching follower data, storing daily/monthly P&L, retrieving closed positions).
    *   `pydantic`: Used for data validation and settings management via models (e.g., `Follower`, `Position` from `spreadpilot-core`).
    *   `reportlab`: For generating PDF reports.
    *   `openpyxl`: For generating Excel reports.
    *   `python-dotenv`: For loading environment variables from `.env` files during local development.
    *   `pytz`: For timezone handling, particularly for determining market close dates.
    *   `sendgrid`: For sending email notifications with report attachments.
    *   `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`: For distributed tracing (though setup seems basic in the core logger).
*   **Design Patterns/Architectural Approaches**:
    *   **Service-Oriented**: The component is a distinct service focused on reporting.
    *   **Event-Driven Architecture (EDA)**: Primarily driven by Pub/Sub messages. The `/` endpoint in `main.py` acts as the subscriber.
    *   **Asynchronous Operations**: Utilizes `asyncio` and `motor` for non-blocking database operations, crucial for handling concurrent requests or long-running report generation tasks efficiently.
    *   **Modular Design**: The service logic is separated into modules:
        *   `main.py`: Flask app setup, Pub/Sub message handling, secret pre-loading.
        *   `config.py`: Application configuration management from environment variables.
        *   `service/report_service.py`: Orchestrates the report generation and P&L calculation flows.
        *   `service/pnl.py`: Handles P&L calculations (daily, monthly) and commission logic.
        *   `service/generator.py`: Responsible for creating PDF and Excel report files.
        *   `service/notifier.py`: Manages sending email notifications.
    *   **Centralized Core Library (`spreadpilot-core`)**: Leverages `spreadpilot-core` for shared models (e.g., `Follower`, `Position`), database utilities (`mongodb.py`), logging (`logger.py`), and common utilities (PDF, Excel, email, secrets).
    *   **Secret Management**: Implements a pre-loading mechanism in `main.py` to fetch secrets (e.g., email credentials) from a dedicated MongoDB collection and load them into environment variables before the main application configuration is imported. This allows sensitive data to be managed centrally and securely.

### Alert Router

**Purpose & Core Functionality**:
The Alert Router service acts as a centralized hub for processing and distributing critical alerts originating from various components within the SpreadPilot system. Its primary responsibilities are:
- **Receiving Alerts**: It ingests alert events, typically pushed via Google Cloud Pub/Sub.
- **Parsing & Validation**: It decodes and validates incoming alert data against a predefined `AlertEvent` schema (from `spreadpilot-core`).
- **Enrichment**: It formats alert messages and generates deep links to relevant sections of the SpreadPilot dashboard for quick access to contextual information.
- **Routing Notifications**: It dispatches formatted alerts to configured administrative channels, specifically Telegram and Email, based on application settings.
- **Secret Management**: It pre-loads necessary secrets (e.g., API tokens for Telegram, SMTP credentials) from a MongoDB instance into its environment at startup.

The core business capability is to ensure that system administrators are promptly and effectively notified of important events, failures, or conditions requiring attention within the trading system.

**Technical Implementation**:
- **Language**: Python 3.11 (as specified in Dockerfile).
- **Framework**: FastAPI for the web server, handling incoming Pub/Sub push requests. Uvicorn is used as the ASGI server.
- **Core Logic**:
    - The application entry point is `alert_router/app/main.py`.
    - It defines a single POST endpoint `/` to receive messages from Google Cloud Pub/Sub.
    - Incoming messages are expected to be Base64 encoded JSON, which are then decoded and parsed into an `AlertEvent` Pydantic model (defined in `spreadpilot-core`).
    - Configuration is managed via `alert_router/app/config.py` using Pydantic's `BaseSettings`, loading values from environment variables and a `.env` file.
    - Secrets (e.g., `TELEGRAM_BOT_TOKEN`, `SMTP_USER`, `SMTP_PASSWORD`) are pre-loaded into environment variables from a MongoDB collection at application startup using `motor` (async MongoDB driver) and the `get_secret_from_mongo` utility from `spreadpilot-core`. This happens before `Settings` are initialized.
    - The actual alert routing logic resides in `alert_router/app/service/router.py`. The `route_alert` function takes a validated `AlertEvent`.
    - It formats the alert message, including generating a deep link to the dashboard using `_generate_deep_link` and `_format_alert_message`.
    - It then attempts to send the formatted message via Telegram (using `python-telegram-bot` via `spreadpilot-core.utils.telegram`) and Email (using `sendgrid` via `spreadpilot-core.utils.email`).
- **Design Patterns/Architectural Approaches**:
    - **Microservice**: The Alert Router is a small, focused service with a single responsibility.
    - **Event-Driven**: It reacts to events (alerts) pushed from a message queue (Pub/Sub).
    - **Configuration Management**: Centralized configuration using Pydantic `BaseSettings`.
    - **Secret Management**: Externalized secret fetching from MongoDB at startup.
    - **Modular Design**: Core utilities (logging, models, secret fetching, notification sending) are imported from the `spreadpilot-core` library, promoting code reuse.
    - **Asynchronous Operations**: The FastAPI application is asynchronous. The secret loading and Pub/Sub message handling are `async`. Notification sending utilities from `spreadpilot-core` are called from async functions; their own internal blocking/non-blocking nature would depend on their implementation (e.g., `send_email` appears synchronous, `send_telegram_message` is awaited).

### Frontend

**Purpose & Core Functionality**:
The frontend component serves as the administrative dashboard for the SpreadPilot system. Its primary responsibilities include:
- Providing a user interface for monitoring follower status and performance (P&L).
- Displaying system logs.
- Allowing users to issue manual commands (e.g., closing positions).
- Handling user authentication and session management.

**Technical Implementation**:
- **Languages**: TypeScript
- **Frameworks**: React (`^19.0.0`), Vite (`^6.3.1`) as the build tool.
- **Routing**: `react-router-dom` (`^7.5.1`) is used for client-side routing.
- **Styling**: Tailwind CSS (`^4.1.4`) is used for a utility-first CSS approach.
- **State Management**: React Context API is used for managing global state, specifically `AuthContext` for authentication and `WebSocketContext` for WebSocket communication. Component-level state is managed using React hooks (`useState`, `useEffect`, etc.).
- **Architectural Approach**: The application follows a component-based architecture, with distinct components for layout (`DashboardLayout`), pages (`LoginPage`, `FollowersPage`, `LogsPage`, `CommandsPage`), and potentially smaller UI elements within those pages. Context API is used for dependency injection of global concerns like authentication and WebSocket.

## Architectural Visualizations

This section provides visual representations of the SpreadPilot system's architecture using Mermaid diagrams.

### Component Interaction Diagram

```mermaid
C4Component
    title SpreadPilot Component Interaction Diagram

    System_Boundary(spreadpilot, "SpreadPilot System")
        Component(frontend, "Frontend", "React Application", "User Interface")
        Component(admin_api, "Admin API", "Python FastAPI", "Provides administrative interface")
        Component(trading_bot, "Trading Bot", "Python Application", "Executes trading strategy")
        Component(watchdog, "Watchdog", "Python Application", "Monitors system health")
        Component(report_worker, "Report Worker", "Python Application", "Generates and sends reports")
        Component(alert_router, "Alert Router", "Python Application", "Routes alerts to users")
    System_Boundary_End

    System(ib_gateway, "IB Gateway", "Interactive Brokers Trading Platform", "External Trading System")
    System(mongodb, "MongoDB", "Document Database", "Stores application data")
    System(google_sheets, "Google Sheets", "Spreadsheet Service", "Configuration/Input source")
    System(telegram_api, "Telegram API", "Messaging Service", "Sends user notifications")
    System(email_smtp, "Email SMTP Service", "Email Delivery Service", "Sends user emails (e.g., SendGrid)")
    System(pubsub, "Pub/Sub System", "Messaging Queue", "Decouples services")
    System(otel_collector, "OpenTelemetry Collector", "Telemetry Collector", "Collects tracing data")
    System(firestore, "Firestore", "NoSQL Database", "Placeholder for Watchdog checks")


    Rel(frontend, admin_api, "Uses", "REST, WebSocket")
    Rel(admin_api, mongodb, "Reads/Writes", "Follower, Secrets")
    Rel(admin_api, pubsub, "Publishes", "Close Positions Command")

    Rel(trading_bot, ib_gateway, "Uses", "Proprietary API (ib_insync)")
    Rel(trading_bot, google_sheets, "Polls", "HTTPS")
    Rel(trading_bot, mongodb, "Reads/Writes", "Follower, Position, Trade, Alert, Secrets")
    Rel(trading_bot, telegram_api, "Sends messages via", "SpreadPilot Core util")
    Rel(trading_bot, pubsub, "Publishes", "AlertEvent")

    Rel(watchdog, trading_bot, "Checks health of")
    Rel(watchdog, ib_gateway, "Checks health of")
    Rel(watchdog, otel_collector, "Checks health of")
    Rel(watchdog, firestore, "Checks health of")

    Rel(report_worker, pubsub, "Receives messages from", "HTTP push")
    Rel(report_worker, mongodb, "Reads/Writes", "Follower, Position/Trade, Reports, Secrets")
    Rel(report_worker, email_smtp, "Sends emails via", "SpreadPilot Core util")

    Rel(alert_router, pubsub, "Receives messages from", "HTTP push")
    Rel(alert_router, mongodb, "Reads", "Secrets")
    Rel(alert_router, telegram_api, "Sends messages via", "SpreadPilot Core util")
    Rel(alert_router, email_smtp, "Sends emails via", "SpreadPilot Core util")

    Rel(frontend, otel_collector, "Sends tracing data to")
    Rel(admin_api, otel_collector, "Sends tracing data to")
    Rel(trading_bot, otel_collector, "Sends tracing data to")
    Rel(watchdog, otel_collector, "Sends tracing data to")
    Rel(report_worker, otel_collector, "Sends tracing data to")
    Rel(alert_router, otel_collector, "Sends tracing data to")

    UpdateLayoutConfig({"direction":"TB"})
```

### Deployment Architecture Diagram

```mermaid
C4Deployment
    title Deployment Architecture Diagram for SpreadPilot

    Deployment_Node(cloud_env, "Cloud Environment", "Google Cloud Platform (GCP) or similar") {
        Deployment_Node(container_runtime, "Container Runtime", "Managed Container Service (e.g., Cloud Run, GKE)") {
            Container(frontend_container, "Frontend", "Docker Container", "React application served by Nginx")
            Container(admin_api_container, "Admin API", "Docker Container", "FastAPI application")
            Container(trading_bot_container, "Trading Bot", "Docker Container", "FastAPI application")
            Container(watchdog_container, "Watchdog", "Docker Container", "Python application")
            Container(report_worker_container, "Report Worker", "Docker Container", "Flask application")
            Container(alert_router_container, "Alert Router", "Docker Container", "FastAPI application")
            Container(otel_collector_container, "OpenTelemetry Collector", "Docker Container", "Receives tracing data")
        }
        Deployment_Node(database_node, "Database Node", "Managed Database Service") {
             Container(mongodb, "MongoDB", "Database", "Central data store")
        }
    }

    Deployment_Node(internet, "Internet", "External Network") {
        System(user, "User", "End User")
        System(load_balancer, "Load Balancer / Reverse Proxy", "Entrypoint to the system")
        System(ib_gateway, "IB Gateway", "Interactive Brokers Trading Gateway")
        System(google_sheets, "Google Sheets", "Spreadsheet service")
        System(email_service, "Email Service", "e.g., SendGrid")
        System(telegram_api, "Telegram API", "Messaging service")
        System(pubsub_system, "Pub/Sub System", "Managed Messaging Service (e.g., GCP Pub/Sub)")
    }

    Rel(user, load_balancer, "Accesses", "HTTPS")
    Rel(load_balancer, frontend_container, "Routes traffic to", "HTTPS")
    Rel(load_balancer, admin_api_container, "Routes traffic to", "HTTPS")

    Rel(frontend_container, admin_api_container, "Communicates with", "HTTP/HTTPS")

    Rel(trading_bot_container, ib_gateway, "Connects to", "Proprietary Protocol")
    Rel(trading_bot_container, google_sheets, "Polls data from", "API")
    Rel(trading_bot_container, mongodb, "Reads/Writes data", "MongoDB Protocol")
    Rel(trading_bot_container, telegram_api, "Sends messages", "API")
    Rel(trading_bot_container, pubsub_system, "Publishes alerts", "Pub/Sub Protocol")

    Rel(watchdog_container, ib_gateway, "Checks health of", "Proprietary Protocol")
    Rel(watchdog_container, otel_collector_container, "Sends health/metrics", "OTLP")
    Rel(watchdog_container, mongodb, "Checks health of", "MongoDB Protocol") # Assuming watchdog checks DB health

    Rel(pubsub_system, report_worker_container, "Triggers (Push)", "Pub/Sub Protocol")
    Rel(report_worker_container, mongodb, "Reads data", "MongoDB Protocol")
    Rel(report_worker_container, email_service, "Sends reports", "SMTP/API")

    Rel(pubsub_system, alert_router_container, "Triggers (Push)", "Pub/Sub Protocol")
    Rel(alert_router_container, mongodb, "Fetches secrets", "MongoDB Protocol")
    Rel(alert_router_container, telegram_api, "Sends alerts", "API")
    Rel(alert_router_container, email_service, "Sends alerts", "SMTP/API")

    Rel(admin_api_container, mongodb, "Reads/Writes data", "MongoDB Protocol")
    Rel(admin_api_container, pubsub_system, "Publishes commands", "Pub/Sub Protocol") # Inferred from context

    Rel(frontend_container, otel_collector_container, "Sends tracing data", "OTLP") # Assuming frontend also sends traces
    Rel(admin_api_container, otel_collector_container, "Sends tracing data", "OTLP")
    Rel(trading_bot_container, otel_collector_container, "Sends tracing data", "OTLP")
    Rel(report_worker_container, otel_collector_container, "Sends tracing data", "OTLP")
    Rel(alert_router_container, otel_collector_container, "Sends tracing data", "OTLP")

    UpdateLayoutConfig({"direction":"TB"})
```

### Cross-cutting Concerns Diagram

```mermaid
graph TD
    subgraph "SpreadPilot Components"
        A[Trading Bot]
        B[Watchdog]
        C[Admin API]
        D[Report Worker]
        E[Alert Router]
        F[Frontend]
    end

    subgraph "Infrastructure / External"
        G[Secrets Store (MongoDB)]
        H[Otel Collector]
        I[Logging/Monitoring System]
        J[User]
        K[Load Balancer]
        L[Environment Variables]
    end

    %% Observability
    A -->|Observability| H
    B -->|Observability| H
    C -->|Observability| H
    D -->|Observability| H
    E -->|Observability| H
    F -->|Observability (console.log)| I
    H -->|Observability| I
    A -->|Observability (Stdout Logs)| I
    B -->|Observability (Stdout Logs)| I
    C -->|Observability (Stdout Logs)| I
    D -->|Observability (Stdout Logs)| I
    E -->|Observability (Stdout Logs)| I

    %% Security
    G -->|Security (Secrets)| A
    G -->|Security (Secrets)| B
    G -->|Security (Secrets)| C
    G -->|Security (Secrets)| D
    G -->|Security (Secrets)| E
    J -->|Security (Auth/Req)| K
    K -->|Security (Auth/Req)| C
    C --.->|Security (Auth Gap)| J

    %% Configuration
    L -->|Configuration| A
    L -->|Configuration| B
    L -->|Configuration| C
    L -->|Configuration| D
    L -->|Configuration| E
    L -->|Configuration| F
    G -->|Configuration (Secrets)| A
    G -->|Configuration (Secrets)| B
    G -->|Configuration (Secrets)| C
    G -->|Configuration (Secrets)| D
    G -->|Configuration (Secrets)| E

    %% Notes/Styling (Optional but helpful)
    classDef component fill:#f9f,stroke:#333,stroke-width:2px;
    class A,B,C,D,E,F component
    classDef infra fill:#ccf,stroke:#333,stroke-width:2px;
    class G,H,I,J,K,L infra
```

### Data Architecture Diagram

```mermaid
erDiagram
    Followers {
        string id PK
        string email
        string iban
        string ibkr_username
        string ibkr_secret_ref
        float commission_pct
        boolean enabled
        string state
        datetime created_at
        datetime updated_at
    }
    Positions {
        string id PK
        string follower_id FK
        string date
        int short_qty
        int long_qty
        float pnl_realized
        float pnl_mtm
        string assignment_state
        datetime updated_at
    }
    Trades {
        string id PK
        string follower_id FK
        string side
        int qty
        float strike
        float limit_price_requested
        string status
        dictionary timestamps
        string error_code OPTIONAL
        string error_msg OPTIONAL
        datetime created_at
        datetime updated_at
    }
    Alerts {
        string id PK
        string follower_id FK OPTIONAL
        string severity
        string type
        string message
        datetime created_at
        boolean acknowledged
        datetime acknowledged_at OPTIONAL
        string acknowledged_by OPTIONAL
    }
    Secrets {
        string id PK
        string name
        string value
        datetime created_at
        datetime updated_at
    }
    Daily_PnL {
        string id PK
        string follower_id FK
        string date
        float total_pnl_realized
        float total_pnl_mtm
        datetime created_at
        datetime updated_at
    }
    Monthly_Reports {
        string id PK
        string follower_id FK
        string month
        float total_pnl_realized_month
        float total_pnl_mtm_month
        string report_path
        datetime generated_at
        datetime updated_at
    }

    Followers ||--|{ Positions : "has"
    Followers ||--|{ Trades : "has"
    Followers ||--o{ Alerts : "can have"
    Followers ||--|{ Daily_PnL : "has"
    Followers ||--|{ Monthly_Reports : "has"
    Daily_PnL }|--|| Trades : "aggregates data from"
    Daily_PnL }|--|| Positions : "aggregates data from"
    Monthly_Reports }|--|| Daily_PnL : "aggregates data from"
```

## Communication Patterns

The SpreadPilot system utilizes a mix of synchronous and asynchronous communication patterns to facilitate interactions between its components and external services.

**Synchronous Communication:**

*   **RESTful HTTP:** The primary pattern for request-response interactions.
    *   The **Frontend** communicates with the **Admin API** using REST endpoints to fetch data (e.g., list followers, get dashboard summary) and trigger actions (e.g., toggle follower status).
    *   The **Watchdog** (conceptually, in a real implementation) would use HTTP/S to poll health check endpoints exposed by services like the **Trading Bot** or **Admin API**.
    *   The **Trading Bot** polls **Google Sheets** via HTTPS.
*   **WebSocket:** Used for real-time, bidirectional communication.
    *   The **Admin API** provides a WebSocket endpoint (`/ws/dashboard`) to push real-time updates (primarily follower status) to connected **Frontend** clients.
*   **Proprietary Protocol:** The **Trading Bot** and **Watchdog** communicate with the **IB Gateway** using Interactive Brokers' proprietary API protocol via the `ib_insync` library.
*   **Database Protocol:** Components like the **Trading Bot**, **Admin API**, **Report Worker**, and **Alert Router** communicate with **MongoDB** using the MongoDB wire protocol via the `motor` asynchronous driver.

**Asynchronous Communication:**

*   **Pub/Sub Messaging:** Used to decouple services and enable event-driven workflows.
    *   The **Admin API** is intended to publish "close positions" commands to a Pub/Sub topic, which the **Trading Bot** would subscribe to.
    *   Upstream components (potentially the **Trading Bot** itself, though not explicitly shown publishing in the analysis) publish **AlertEvent** messages to a Pub/Sub topic.
    *   The **Report Worker** and **Alert Router** services are triggered by receiving messages from Pub/Sub topics via HTTP push subscriptions.
*   **Email:** Used for asynchronous notifications.
    *   The **Report Worker** sends monthly reports via an **Email SMTP Service**.
    *   The **Alert Router** sends critical alerts via an **Email SMTP Service**.
*   **Telegram:** Used for asynchronous notifications.
    *   The **Trading Bot** sends some alerts via the **Telegram API**.
    *   The **Alert Router** sends critical alerts via the **Telegram API**.

This combination of patterns allows for responsive user interactions (REST, WebSocket), reliable background processing (Pub/Sub), and integration with external systems (IBKR, Google Sheets, Email, Telegram).

## System Characteristics

This section summarizes key system characteristics related to performance, resilience, security, and evolution based on the component analyses.

### Scalability

*   **Horizontal Scaling:** Most core services (Admin API, Trading Bot, Report Worker, Alert Router, Watchdog, Frontend) are designed as stateless (or near-stateless after initial config/secret loading) Docker containers, making them candidates for horizontal scaling by running multiple instances behind a load balancer or within a managed container service (e.g., Cloud Run, Kubernetes).
*   **Bottlenecks:**
    *   **MongoDB:** The central database is a potential bottleneck. Its scalability depends on its own configuration (replica sets, sharding) and the efficiency of queries from connected services.
    *   **Trading Bot (Signal Processing):** The current sequential processing of signals for each follower within a single instance will limit scaling with a large number of followers. Parallelizing this process within the bot or sharding followers across multiple bot instances would be necessary.
    *   **Admin API (WebSocket Broadcasting):** The current instance-local WebSocket connection management will not scale horizontally. A shared backplane (e.g., Redis Pub/Sub) is needed for broadcasting across multiple Admin API instances.
    *   **Report Worker (Synchronous Processing):** Processing long-running report generation tasks synchronously within the Pub/Sub request handler can lead to timeouts. Offloading this to background tasks or using a task queue would improve responsiveness and scalability.
    *   **External Services:** Rate limits and performance of external APIs (IBKR, Google Sheets, Telegram, SendGrid) can limit overall system throughput.
*   **Scaling Triggers:** Scaling would typically be managed by the hosting platform (e.g., based on CPU utilization, request count/latency, or queue depth for Pub/Sub triggered services).

### Performance Bottlenecks

*   **IBKR API Latency:** Interactions with the Interactive Brokers API are inherently subject to external network conditions and IBKR's system performance. The Trading Bot's reliance on this API for order placement and data fetching is a primary source of potential latency.
*   **Google Sheets Polling:** The polling mechanism introduces latency in signal detection. A push-based mechanism would reduce this.
*   **Database Query Performance:** Slow or unindexed queries in MongoDB can impact the responsiveness of the Admin API, Trading Bot, and Report Worker.
*   **Report Generation:** Generating PDF and Excel reports can be CPU and memory intensive, potentially causing performance issues if not managed efficiently, especially for many followers or large data sets.
*   **Network I/O:** High volume of network calls (DB, external APIs, WebSockets) can consume bandwidth and add latency.

### Resilience Boundaries

*   **Component Isolation:** The system is designed with distinct service boundaries (microservices), meaning a failure in one component (e.g., Report Worker) should ideally not directly crash other components (e.g., Trading Bot).
*   **Pub/Sub Decoupling:** The use of Pub/Sub provides resilience by decoupling publishers from subscribers. If a subscriber (e.g., Report Worker) is temporarily unavailable, messages are queued by Pub/Sub and delivered later.
*   **Error Handling & Retries:** Components implement `try-except` blocks for error handling. Some components (Trading Bot, Report Worker, Alert Router) have basic retry mechanisms for specific operations (e.g., IBKR orders, Pub/Sub message processing via 5xx responses).
*   **Graceful Degradation:** Limited graceful degradation is implemented. For example, the Alert Router can continue sending notifications via one channel if another fails. The Admin API's WebSocket task logs errors but continues its loop. However, core functions often fail if critical dependencies (like MongoDB) are unavailable.
*   **Health Checks:** The Admin API and (conceptually) Watchdog provide health checks, allowing external monitoring systems to detect unhealthy instances and potentially route traffic away or trigger restarts.
*   **Missing Patterns:** Explicit circuit breaker implementations and more sophisticated retry strategies with exponential backoff are not widely implemented, which could improve resilience against transient failures in downstream services. Dead-letter queues for Pub/Sub are not explicitly configured in the application code but are a standard Pub/Sub feature that should be utilized.

### Security Controls

*   **Authentication & Authorization:**
    *   **Critical Gap:** The **Admin API** currently lacks any explicit authentication or authorization for its HTTP and WebSocket endpoints, making it publicly accessible. This is the most significant security vulnerability.
    *   The **Frontend** implements token-based authentication for API calls, but this relies on the backend enforcing authentication.
    *   Manual commands in the Frontend require a PIN.
    *   Access to Pub/Sub push endpoints relies on infrastructure-level IAM authentication.
    *   Access to MongoDB is controlled via connection string credentials.
*   **Secret Management:** Sensitive credentials (IBKR, API keys, SMTP) are stored in a dedicated MongoDB collection and loaded into environment variables by Python services at startup using a utility from `spreadpilot-core`. This is a good practice, but the security of the secrets MongoDB instance itself is critical.
*   **Data Protection:**
    *   **In Transit:** Assumes HTTPS/TLS for communication with external services (Google Sheets, Telegram, SendGrid), Pub/Sub push, and MongoDB (if configured). Client-to-Admin API communication should be over HTTPS (handled by Load Balancer).
    *   **At Rest:** Depends on MongoDB's encryption at rest capabilities. No application-level encryption of data in MongoDB is evident.
*   **Input Validation:** Pydantic models are used extensively in Python services (Admin API, Report Worker, Alert Router) for validating incoming data (HTTP request bodies, Pub/Sub payloads), mitigating risks from malformed inputs.
*   **Dependency Security:** Security relies on keeping third-party libraries and the base OS images updated to patch known vulnerabilities.
*   **Least Privilege:** Services should ideally run with the minimum necessary permissions (e.g., database users with limited access, API keys with restricted scope).

### Evolution Strategy

*   **Modular Design:** The microservice-like structure facilitates independent development and deployment of components. New services can be added, and existing ones can be modified or replaced with minimal impact on others, provided interfaces (APIs, Pub/Sub schemas) are maintained.
*   **Shared Core Library:** `spreadpilot-core` centralizes common functionalities, promoting consistency and reducing duplication. Changes to core utilities or models need careful consideration of their impact on all consuming services.
*   **Asynchronous Communication (Pub/Sub):** The use of Pub/Sub allows for easier integration of new services that need to consume events or trigger actions without direct coupling to existing services.
*   **Configuration Management:** Using environment variables and a centralized secrets store simplifies configuration updates and allows for different configurations across environments.
*   **Placeholder Implementations:** The presence of placeholders (e.g., Watchdog health checks, Admin API dashboard sections, Pub/Sub client in Admin API) indicates areas planned for future development.
*   **Technical Debt:** Areas like the lack of Admin API authentication, potential schema mismatch in Report Worker's P&L calculation, and the need for improved WebSocket scaling represent technical debt that needs to be addressed for a robust production system.
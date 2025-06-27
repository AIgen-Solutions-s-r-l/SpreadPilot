+++
id = "README"
title = "SpreadPilot Project README"
context_type = "documentation"
scope = "Project Overview"
target_audience = ["developers", "users", "contributors"]
granularity = "overview"
status = "active"
last_updated = "2025-05-10"
tags = ["readme", "documentation", "project-setup", "api", "architecture", "testing", "deployment", "contribution", "troubleshooting", "changelog", "license", "acknowledgments"]
+++

# SpreadPilot

SpreadPilot is a sophisticated copy-trading platform designed to automate the execution of QQQ options strategies from a Google Sheets algorithm to Interactive Brokers (IBKR) accounts. Built as a collection of microservices, SpreadPilot provides a robust and scalable solution for replicating trading signals and managing positions.

## Badges

(Use placeholders or examples if specific URLs/status are unknown)

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![Docker](https://img.shields.io/badge/docker-enabled-blue)

## Features

*   **Automated Trading:** Replicate QQQ options strategies directly from Google Sheets to IBKR.
*   **Advanced Order Execution:** Limit-ladder execution strategy with pre-trade margin checks and dynamic pricing.
*   **Microservice Architecture:** Scalable and maintainable design with dedicated services for trading, monitoring, administration, reporting, and alerting.
*   **Multi-Follower Support:** Automatic IBGateway container management for each enabled follower with isolated connections.
*   **Real-time Monitoring:** Admin dashboard with real-time logs and system status updates.
*   **Flexible Alerting:** Configurable alerts via Telegram and email for critical events.
*   **Automated Reporting:** Periodic P&L reports generated in PDF and Excel formats.
*   **Containerized Deployment:** Easy setup and deployment using Docker and Docker Compose.
*   **Cloud-Ready:** Designed for deployment on Google Cloud Platform (GCP) using Cloud Build and Cloud Run.

## Installation

### Prerequisites

*   Docker and Docker Compose
*   Python 3.9+
*   `make` (optional, for using the Makefile)
*   An Interactive Brokers (IBKR) account and credentials
*   Google Cloud Platform (GCP) account and credentials (for cloud deployment)
*   SendGrid account and API key (for email notifications)
*   Telegram Bot token and chat ID (for Telegram notifications)
*   Google Sheets URL for the trading strategy

### Using Docker Compose (Recommended for local development)

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-repo/spreadpilot.git
    cd spreadpilot
    ```
2.  Create a `.env` file in the project root based on `deploy/.env.dev.template` and fill in your credentials and configuration.
3.  Build and start the services:
    ```bash
    docker-compose up --build -d
    ```
4.  Verify that the containers are running:
    ```bash
    docker-compose ps
    ```

### Manual Installation (For development without Docker)

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-repo/spreadpilot.git
    cd spreadpilot
    ```
2.  Initialize the development environment (requires Python 3.9+):
    ```bash
    make init-dev
    # or manually:
    # python3 -m venv venv
    # source venv/bin/activate
    # pip install --upgrade pip
    # pip install -r requirements-dev.txt
    # pip install -e ./spreadpilot-core
    ```
3.  Install all project dependencies:
    ```bash
    make install-all
    # or manually:
    # pip install -r requirements.txt
    # pip install -r requirements-dev.txt
    ```
4.  Configure environment variables (e.g., by sourcing a `.env` file or setting them in your shell).
5.  Run individual services (refer to each service's documentation for specific instructions).

## Quick Start

1.  Follow the [Installation](#installation) steps to set up the project using Docker Compose.
2.  Ensure your `.env` file is correctly configured with your IBKR, Google Sheets, and communication credentials.
3.  Start the services:
    ```bash
    docker-compose up -d
    ```
4.  Access the Admin Dashboard in your web browser (default: `http://localhost:8080`).
5.  Log in using the credentials configured in your `.env` file.
6.  Use the dashboard to manage followers, view logs, and monitor system status.
7.  The Trading Bot will automatically start polling your Google Sheet for trading signals and execute trades via the IB Gateway.

## Configuration

Configuration is primarily managed through environment variables. A `.env` file is used for local development.

Key environment variables include:

*   `IB_USERNAME`: Interactive Brokers username
*   `IB_PASSWORD`: Interactive Brokers password
*   `GOOGLE_SHEET_URL`: URL of the Google Sheet containing the trading strategy
*   `GOOGLE_APPLICATION_CREDENTIALS`: Path to the Google service account key file
*   `SENDGRID_API_KEY`: SendGrid API key for email notifications
*   `TELEGRAM_BOT_TOKEN`: Telegram Bot token
*   `TELEGRAM_CHAT_ID`: Telegram chat ID for notifications
*   `ADMIN_USERNAME`: Username for the Admin Dashboard
*   `ADMIN_PASSWORD_HASH`: Hashed password for the Admin Dashboard
*   `JWT_SECRET`: Secret key for JWT authentication
*   `MONGO_URI`: MongoDB connection URI
*   `MONGO_DB_NAME`: MongoDB database name

Refer to `deploy/.env.dev.template` for a complete list and descriptions.

## Admin API Documentation

The Admin API provides endpoints for managing followers and accessing system data.

Base URL: `/api/v1`

### Endpoints

#### `GET /api/v1/followers`

Retrieves a list of all registered followers.

**Response:** `List[FollowerRead]` (See `admin_api/app/schemas/follower.py` for schema)

#### `POST /api/v1/followers`

Registers a new follower in the system.

**Request Body:** `FollowerCreate` (See `admin_api/app/schemas/follower.py` for schema)

**Response:** `FollowerRead`
**Status Code:** `201 Created`

#### `POST /api/v1/followers/{follower_id}/toggle`

Enables or disables a specific follower.

**Parameters:**

*   `follower_id`: The ID of the follower (string)

**Response:** `FollowerRead` (The updated follower object)

#### `POST /api/v1/close/{follower_id}`

Sends a command to the trading bot to close all positions for a specific follower.

**Parameters:**

*   `follower_id`: The ID of the follower (string)

**Response:** `{"message": "Close positions command accepted for follower {follower_id}."}`
**Status Code:** `202 Accepted` (The action is asynchronous)

## Architecture

SpreadPilot is built with a microservice architecture, designed for scalability and maintainability.

![System Architecture Diagram](./docs/images/system-architecture.png)

### Components

*   **Trading Bot:** Connects to IBKR, polls Google Sheets, executes orders, handles assignments, manages positions.
*   **Order Executor:** Advanced limit-ladder execution engine with pre-trade margin validation and dynamic pricing strategies.
*   **Watchdog:** Monitors service health, attempts restarts, updates status, triggers alerts.
*   **Admin API:** Provides backend for the admin dashboard (follower management, real-time logs, authentication).
*   **Report Worker:** Generates periodic P&L reports (PDF/Excel) and emails them.
*   **Alert Router:** Manages alert delivery via Telegram and email.
*   **Frontend:** Admin dashboard for monitoring and management.
*   **SpreadPilot Core:** Shared Python library with IBKR client, database models, logging, and utilities.
*   **Gateway Manager:** Manages IBGateway Docker containers for each enabled follower, providing isolated connections and automatic port/client ID allocation.
*   **IB Gateway:** Provides connectivity to Interactive Brokers (managed by Gateway Manager).
*   **MongoDB:** Primary database for follower data, positions, trades, and system status.
*   **OpenTelemetry Collector:** Gathers telemetry data (metrics, traces, logs).
*   **Prometheus:** Stores and processes metrics.
*   **Grafana:** Provides visualization and dashboards for metrics.

### Communication Patterns

*   **Synchronous:** REST APIs (service-to-service, client-to-service), WebSockets (real-time updates).
*   **Asynchronous:** Pub/Sub (event-driven communication for alerts and reports).

### Data Flow

1.  **Trading Signal Flow:** Google Sheets -> Trading Bot -> Order Executor -> Gateway Manager -> IB Gateway -> MongoDB
2.  **Order Execution Flow:** Order Executor -> IB Gateway (margin check) -> Order Executor (limit-ladder) -> IB Gateway (fills)
3.  **Follower Management Flow:** Admin API -> Gateway Manager -> Docker (IBGateway containers)
4.  **Reporting Flow:** Cloud Scheduler -> Pub/Sub -> Report Worker -> MongoDB -> SendGrid
5.  **Alerting Flow:** Services -> Pub/Sub -> Alert Router -> Telegram/SendGrid
6.  **Monitoring Flow:** Services -> OpenTelemetry Collector -> Prometheus/Cloud Monitoring -> Grafana

## Contribution Guidelines

We welcome contributions to SpreadPilot! Please follow these guidelines:

1.  **Fork the repository** and create a new branch for your feature or bug fix.
2.  **Set up your development environment** using the instructions in the [Installation](#installation) section.
3.  **Adhere to the code style** used in the project (run `make format` to auto-format).
4.  **Write tests** for your changes (unit and/or integration tests).
5.  **Ensure all tests pass** (`make test`).
6.  **Write clear and concise commit messages** following the Conventional Commits specification.
7.  **Submit a pull request** to the `main` branch.

## Testing

The project includes unit and integration tests.

*   **Unit Tests:** Located in the `tests/unit/` directory. These tests verify individual components in isolation.
*   **Integration Tests:** Located in the `tests/integration/` directory. These tests verify the interaction between multiple services. Refer to [tests/integration/README.md](tests/integration/README.md) for detailed setup and running instructions.

To run all tests:

```bash
make test
```

To run integration tests specifically:

```bash
pytest tests/integration/
```

To run tests with coverage:

```bash
make test-coverage
```

## Deployment

SpreadPilot is designed for deployment on Google Cloud Platform (GCP) using Cloud Build and Cloud Run.

1.  **Configure GCP:** Set up a GCP project, enable the necessary APIs (Cloud Build, Cloud Run, Artifact Registry, Pub/Sub, Secret Manager), and configure authentication.
2.  **Build Docker Images:** Cloud Build automatically builds Docker images for each service based on the `Dockerfile`s in their respective directories. The `cloudbuild.yaml` file defines the build steps.
3.  **Push Images to Artifact Registry:** Built images are pushed to GCP Artifact Registry.
4.  **Deploy to Cloud Run:** Services are deployed to Cloud Run as managed services. The `cloudbuild.yaml` includes steps for deploying to a development environment.
5.  **Secrets Management:** Use GCP Secret Manager to store sensitive configuration like API keys and credentials. Configure Cloud Run services to access these secrets.
6.  **Pub/Sub Setup:** Create Pub/Sub topics for alerts and reports.
7.  **Cloud Scheduler:** Configure Cloud Scheduler jobs to trigger the Report Worker via Pub/Sub.

Refer to the `deploy/` directory for deployment scripts and templates, including `cloudbuild.yaml` and `.env.prod.template`.

## Troubleshooting

If you encounter issues while setting up or running SpreadPilot, consider the following:

*   **Check Docker Containers:** Ensure all required Docker containers are running (`docker-compose ps`). Restart services if necessary (`docker-compose down` then `docker-compose up -d`).
*   **Environment Variables:** Verify that all necessary environment variables are set correctly in your `.env` file or environment.
*   **Logs:** Check the logs for individual services using `docker-compose logs [service_name]` for detailed error messages.
*   **IB Gateway Connection:** Ensure the IB Gateway is running and accessible to the trading bot. Check the IB Gateway logs for connection issues.
*   **Google Sheets Access:** Verify that the Google service account has the necessary permissions to access the trading strategy Google Sheet.
*   **Firewall Rules:** If deploying to GCP, ensure firewall rules allow necessary communication between services and external services (IBKR, Google Sheets, SendGrid, Telegram).
*   **MongoDB Connection:** If running MongoDB manually, ensure it is accessible and the connection URI is correct.

(Add more specific troubleshooting steps as common issues are identified and documented.)

## Changelog

(Use placeholders or standard format)

### [Unreleased]

*   Initial development

## License

(Use placeholders or check for LICENSE file)

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. (Placeholder - check for actual LICENSE file)

## Acknowledgments

(Use placeholders)

*   Hat tip to anyone whose code was used
*   Inspiration
*   etc.
+++
# --- Basic Metadata ---
id = "SPREADPILOT-REQUIREMENTS-V1"
title = "SpreadPilot - Inferred System Requirements"
context_type = "documentation"
scope = "Functional and Non-Functional Requirements inferred from existing project analysis"
target_audience = ["developers", "architects", "project-managers"]
granularity = "summary"
status = "draft" # Marked as draft as it's inferred
last_updated = "2025-04-28" # Date of generation
# version = "1.0"
tags = ["requirements", "spreadpilot", "functional", "non-functional", "discovery"]
related_context = [
    ".ruru/context/stack_profile.json",
    "docs/01-system-architecture.md",
    "README.md"
    ]
# template_schema_doc = ".ruru/templates/toml-md/NN_requirements_doc.README.md" # Hypothetical template
source_task = "TASK-DISC-20250428-231600"
+++

# SpreadPilot - Inferred System Requirements

This document outlines the functional and non-functional requirements for the SpreadPilot system, as inferred from analysis of the existing codebase, documentation (`README.md`, `docs/01-system-architecture.md`), and configuration files during the onboarding discovery process (Task ID: `TASK-DISC-20250428-231600`).

## 1. Functional Requirements

### 1.1 Core Trading Logic
*   **[FR-001]** The system MUST copy-trade QQQ options strategies defined in a specified Google Sheet to linked Interactive Brokers (IBKR) accounts.
*   **[FR-002]** The system MUST periodically poll the designated Google Sheet for new trading signals.
*   **[FR-003]** The system MUST execute buy/sell orders for options spreads via the IBKR API (using IB Gateway) based on the signals received.
*   **[FR-004]** The system MUST detect and handle option assignment events appropriately.
*   **[FR-005]** The system MUST track Profit & Loss (P&L) for each follower account.

### 1.2 Reporting
*   **[FR-006]** The system MUST generate periodic (daily/monthly specified) reports in PDF format.
*   **[FR-007]** The system MUST generate periodic (daily/monthly specified) reports in Excel format.
*   **[FR-008]** The system MUST email the generated reports to the respective followers.

### 1.3 Administration & Monitoring
*   **[FR-009]** The system MUST provide a web-based administrative dashboard.
*   **[FR-010]** The admin dashboard MUST allow management of follower accounts (CRUD operations implied).
*   **[FR-011]** The admin dashboard MUST allow viewing and potentially modifying system configuration.
*   **[FR-012]** The admin dashboard MUST display real-time logs streamed from the backend services (via WebSockets).
*   **[FR-013]** The admin dashboard MUST provide a mechanism for manual command execution (details unspecified).
*   **[FR-014]** The system MUST monitor the health status of the core Trading Bot service.
*   **[FR-015]** The system MUST monitor the health status of the IB Gateway connection.
*   **[FR-016]** The system MUST attempt to automatically restart the Trading Bot or IB Gateway if they are detected as unhealthy.

### 1.4 Alerting
*   **[FR-017]** The system MUST route critical alerts and notifications.
*   **[FR-018]** Alerts MUST be deliverable via Telegram.
*   **[FR-019]** Alerts MUST be deliverable via email.
*   **[FR-020]** Alert messages SHOULD include relevant context or deep links to the admin dashboard where applicable.

## 2. Non-Functional Requirements

### 2.1 Architecture & Deployment
*   **[NFR-001]** The system MUST be implemented using a microservices architecture.
*   **[NFR-002]** Services MUST be containerized using Docker.
*   **[NFR-003]** The system MUST be deployable to Google Cloud Platform (GCP), specifically using Cloud Run.
*   **[NFR-004]** Services SHOULD be designed to be stateless to facilitate horizontal scaling.

### 2.2 Technology Stack
*   **[NFR-005]** Backend services MUST primarily use Python 3.11.
*   **[NFR-006]** Asynchronous operations in Python services MUST use the `asyncio` library.
*   **[NFR-007]** The Admin API MUST use the FastAPI framework. Other backend services may use FastAPI, aiohttp, or Flask as appropriate (e.g., Flask for Pub/Sub).
*   **[NFR-008]** The frontend MUST be a single-page application built with React (v19+) and TypeScript (v5.7+).
*   **[NFR-009]** The frontend MUST use Vite as the build tool.
*   **[NFR-010]** The frontend MUST use Tailwind CSS for styling.

### 2.3 Data Persistence & Communication
*   **[NFR-011]** The system MUST use Google Cloud Firestore (Native mode) as the primary database for storing follower data, positions, trades, and system status.
*   **[NFR-012]** The system MUST use Google Cloud Pub/Sub for asynchronous inter-service communication (e.g., alerts, report triggers).
*   **[NFR-013]** Synchronous communication MUST primarily use REST APIs.
*   **[NFR-014]** Real-time communication between the Admin API and Frontend MUST use WebSockets.

### 2.4 Security
*   **[NFR-015]** The Admin API and Frontend MUST implement authentication, likely using JWT.
*   **[NFR-016]** Sensitive configuration and credentials MUST be managed using GCP Secret Manager.
*   **[NFR-017]** Network security SHOULD be configured appropriately within GCP (e.g., VPC).

### 2.5 Observability & Resilience
*   **[NFR-018]** The system MUST implement observability using OpenTelemetry for collecting metrics, traces, and logs.
*   **[NFR-019]** Metrics MUST be stored in Prometheus.
*   **[NFR-020]** Dashboards for monitoring MUST be provided using Grafana.
*   **[NFR-021]** Services MUST implement structured logging, potentially using a shared library (`spreadpilot-core`).
*   **[NFR-022]** The system MUST include mechanisms for resilience, including health monitoring and automatic recovery of critical components (Trading Bot, IB Gateway).
*   **[NFR-023]** Critical system failures MUST trigger alerts.

### 2.6 Development & Code Quality
*   **[NFR-024]** The project MUST use `make` for standard development tasks (setup, test, lint, format, deploy).
*   **[NFR-025]** Python code MUST adhere to formatting standards enforced by `black` and `isort`.
*   **[NFR-026]** Python code MUST pass linting checks using `flake8`.
*   **[NFR-027]** Python code MUST include type hints and pass static analysis using `mypy`.
*   **[NFR-028]** The project MUST include automated tests using `pytest`.
*   **[NFR-029]** CI/CD pipelines MUST be implemented using Google Cloud Build.
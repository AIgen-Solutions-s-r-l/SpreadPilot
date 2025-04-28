+++
# --- Basic Metadata ---
id = "SPREADPILOT-REQUIREMENTS-V1"
title = "SpreadPilot System Requirements"
context_type = "documentation"
scope = "Functional and Non-Functional Requirements for the SpreadPilot Platform"
target_audience = ["developers", "architects", "product-manager", "qa"]
granularity = "summary"
status = "active" # Options: draft, active, deprecated, superseded
last_updated = "2025-04-28T23:33:00Z" # Use current date/time
# version = "1.0"
tags = ["requirements", "functional", "non-functional", "spreadpilot", "trading", "options"]
related_context = [
    ".ruru/context/stack_profile.json",
    "README.md",
    "docs/01-system-architecture.md",
    "project_journal/decisions/20250418-spreadpilot-architecture-reflections.md"
]
template_schema_doc = ".ruru/templates/toml-md/05_documentation.README.md" # Assuming a generic doc template schema exists
# --- Project Specific ---
project_name = "SpreadPilot"
+++

# SpreadPilot System Requirements

## 1. Overview

This document outlines the functional and non-functional requirements for the SpreadPilot platform, derived from existing project documentation and architectural decisions. SpreadPilot is a copy-trading platform designed to replicate QQQ options strategies from a Google Sheet to follower accounts on Interactive Brokers (IBKR).

## 2. Functional Requirements

### 2.1 Core Trading Logic
*   **FR-001:** The system MUST poll a specified Google Sheet at regular intervals (e.g., 1 second) to retrieve trading signals for a QQQ options strategy (Vertical Spread 0-DTE mentioned).
*   **FR-002:** The system MUST interpret the signals from the Google Sheet to determine required trading actions (e.g., open, close positions).
*   **FR-003:** The system MUST connect securely to Interactive Brokers (IBKR) via the IB Gateway using provided credentials.
*   **FR-004:** The system MUST execute trades (options orders) on behalf of registered follower accounts based on the interpreted signals.
*   **FR-005:** The system MUST manage and track open positions for each follower account in Firestore.
*   **FR-006:** The system MUST monitor follower positions for potential assignments.
*   **FR-007:** The system MUST automatically handle detected assignments according to a predefined strategy (details TBD, but handling is required).
*   **FR-008:** The system MUST calculate and track Profit & Loss (P&L) for follower accounts.

### 2.2 Reporting
*   **FR-009:** The system MUST generate periodic (daily, monthly) P&L reports for followers.
*   **FR-010:** Reports MUST be generated in PDF and Excel formats.
*   **FR-011:** Generated reports MUST be automatically emailed to the respective followers.

### 2.3 Alerting & Monitoring
*   **FR-012:** The system MUST generate alerts for critical events (e.g., trading errors, connection issues, assignment detection, component failures).
*   **FR-013:** Alerts MUST be routed to specified channels, including Telegram and email.
*   **FR-014:** Alert messages SHOULD include relevant details and potentially deep links to the admin dashboard.
*   **FR-015:** The system MUST monitor the health status of critical components (Trading Bot, IB Gateway).
*   **FR-016:** The system MUST attempt to automatically restart failed critical components.
*   **FR-017:** The health status of components MUST be tracked (e.g., in Firestore) and visible.

### 2.4 Administration & Management
*   **FR-018:** The system MUST provide a web-based administrative dashboard.
*   **FR-019:** The dashboard MUST require secure user authentication (username/password).
*   **FR-020:** The dashboard MUST allow administrators to manage follower accounts (add, view, modify, remove - details TBD).
*   **FR-021:** The dashboard MUST display real-time logs streamed from the backend services.
*   **FR-022:** The dashboard MAY allow administrators to execute certain manual commands (details TBD).
*   **FR-023:** The system MUST provide APIs (REST, WebSocket) to support the dashboard functionality.

## 3. Non-Functional Requirements

### 3.1 Performance & Scalability
*   **NFR-001:** The system MUST process trading signals and execute orders in near real-time to minimize slippage. (Polling interval target: 1 second).
*   **NFR-002:** The architecture MUST support scaling to handle a target number of followers (e.g., 300+ mentioned in reflections).
*   **NFR-003:** Individual microservices MUST be independently scalable based on their load.
*   **NFR-004:** The database (Firestore) MUST handle the load associated with the target number of followers and trading activity.

### 3.2 Reliability & Availability
*   **NFR-005:** The core trading functionality MUST be highly reliable, especially during market hours.
*   **NFR-006:** The system MUST implement mechanisms for automatic recovery from component failures (e.g., Watchdog restarting services).
*   **NFR-007:** The event-driven communication (Pub/Sub) MUST ensure reliable message delivery (at-least-once).
*   **NFR-008:** Services relying on Pub/Sub messages MUST be idempotent.
*   **NFR-009:** The system SHOULD leverage managed cloud services for high availability.

### 3.3 Security
*   **NFR-010:** All sensitive credentials (IBKR API keys, service keys, secrets) MUST be stored securely (e.g., GCP Secret Manager).
*   **NFR-011:** Access control MUST follow the principle of least privilege (e.g., IAM roles).
*   **NFR-012:** Communication between services SHOULD be secured (e.g., within a private VPC).
*   **NFR-013:** Communication with external services (IBKR, Google Sheets) MUST be secure (e.g., HTTPS).
*   **NFR-014:** The admin dashboard MUST implement secure authentication (e.g., JWT) and authorization.
*   **NFR-015:** Container images SHOULD minimize attack surface (e.g., using distroless images).

### 3.4 Maintainability & Operability
*   **NFR-016:** The codebase MUST be modular and follow principles like Separation of Concerns and Single Responsibility.
*   **NFR-017:** A shared core library MUST be used for common functionality to ensure consistency and reduce duplication.
*   **NFR-018:** The system MUST be containerized (Docker) for consistent environments and deployment.
*   **NFR-019:** Deployment processes MUST be automated (e.g., Cloud Build).
*   **NFR-020:** Configuration MUST be externalized from the code (e.g., environment variables, Secret Manager).

### 3.5 Observability
*   **NFR-021:** The system MUST implement structured logging across all services.
*   **NFR-022:** Logs SHOULD include correlation IDs to trace requests across services.
*   **NFR-023:** Key performance indicators (KPIs) and system health metrics MUST be collected (e.g., via OpenTelemetry).
*   **NFR-024:** Distributed tracing SHOULD be implemented to understand request flows.
*   **NFR-025:** Monitoring dashboards (e.g., Grafana, Cloud Monitoring) MUST be available for visualizing system health and performance.
*   **NFR-026:** Meaningful alerts MUST be configured based on collected metrics and logs.

### 3.6 Testability
*   **NFR-027:** The system MUST have a comprehensive automated testing strategy, including unit, integration, and potentially end-to-end tests.
*   **NFR-028:** Code modules MUST be designed for testability (e.g., allowing mocking of external dependencies).
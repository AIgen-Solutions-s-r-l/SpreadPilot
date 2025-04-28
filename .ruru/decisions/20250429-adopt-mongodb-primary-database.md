+++
id = "ADR-20250429-MONGO"
title = "Adopt MongoDB as Primary Database"
status = "accepted"
decision_date = "2025-04-29"
authors = ["roo-commander"]
template_schema_doc = ".ruru/templates/toml-md/07_adr.README.md"
affected_components = ["admin-api", "docker-compose.yml", "spreadpilot-core", "trading-bot", "alert-router", "report-worker"] # Estimate based on likely data needs
tags = ["database", "mongodb", "architecture", "docker", "non-proprietary", "data-persistence"]
# supersedes_adr = "" # If applicable, e.g., if replacing Firestore ADR
+++

# ADR-20250429-MONGO: Adopt MongoDB as Primary Database

**Status:** accepted

**Date:** 2025-04-29

## Context 🤔

*   The application requires a persistent database solution for storing application data (e.g., follower information, configurations, potentially trades, logs).
*   The current structure includes `admin-api/app/db/firestore.py`, suggesting Firestore might be in use or was considered.
*   There is an explicit requirement to prioritize flexibility, control, and avoid vendor lock-in associated with proprietary BaaS databases like Google Firebase/Firestore.
*   The initial deployment needs to be manageable for development and testing, suggesting containerization.
*   The architecture must support future scaling and deployment flexibility, including connecting to external, potentially managed, MongoDB clusters.

## Decision ✅ / ❌

*   **Adopt MongoDB** as the primary database technology for the SpreadPilot application.
*   Implement the initial deployment of MongoDB as a service within a **Docker container**, managed via `docker-compose.yml`.
*   Design and implement application data access layers (e.g., in `admin-api`, `spreadpilot-core`) to be **adaptable**, allowing connection to either the local Docker container or an external MongoDB cluster URI through configuration (e.g., environment variables).

## Rationale / Justification 💡

*   **Flexibility & Control:** MongoDB is a well-established, non-proprietary NoSQL database, offering significant flexibility in deployment (local, cloud, self-hosted) and avoiding vendor lock-in compared to alternatives like Firestore.
*   **Development Efficiency:** Running MongoDB in Docker simplifies the local development setup and ensures consistency across environments.
*   **Future-Proofing:** Designing the data access layer for adaptability allows seamless transition to managed services (e.g., MongoDB Atlas) or larger self-hosted clusters as the application scales, without major code rewrites.
*   **Ecosystem:** MongoDB has mature drivers and tooling for various languages, including Python (e.g., `pymongo`, `motor`).
*   **Alignment:** Meets the explicit requirement to avoid proprietary databases.

## Consequences / Implications ➡️

*   **Infrastructure:** Requires adding a MongoDB service definition to `docker-compose.yml`, including volume mapping for data persistence.
*   **Code Refactoring:** Data access logic in affected components (initially `admin-api`, likely others) must be refactored to use a MongoDB client library instead of any existing Firestore or other implementations. This includes model definitions/schemas if applicable.
*   **Configuration:** New environment variables will be needed for MongoDB connection strings (supporting both Docker service names and external URIs), database names, usernames, and passwords.
*   **Data Modeling:** Requires defining appropriate MongoDB document structures for the application's data entities.
*   **Data Migration:** If Firestore (or another DB) is currently used with existing data, a migration strategy and implementation will be necessary.
*   **Operational:** Introduces MongoDB-specific operational considerations for the future (backups, monitoring, indexing, security hardening), especially when moving beyond the initial Docker setup.
*   **Dependency Management:** MongoDB client libraries (e.g., `pymongo`, `motor`) need to be added to the requirements files of relevant services.

## Alternatives Considered (Optional Detail) 📝

*   **Continue using Firestore:** Rejected due to the explicit requirement to avoid vendor lock-in and desire for greater control.
*   **Use PostgreSQL (SQL):** While a valid option, MongoDB (NoSQL) was explicitly requested and can offer flexibility for evolving schemas often seen in trading applications.
*   **Other NoSQL Databases (e.g., Redis, Cassandra):** MongoDB provides a good balance of general-purpose NoSQL features suitable for the likely application requirements.

## Related Links 🔗 (Optional)

*   Parent Task: (Link to the initial user request/task ID if available)
*   Implementation Tasks: (Links to future MDTM tasks for Docker setup, API refactoring, etc.)
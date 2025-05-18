# SpreadPilot Onboarding Notes

## System Architecture Overview (2025-05-18)

Today we reviewed the SpreadPilot system architecture, focusing on understanding the core components and their interactions. Below is a summary of what we covered:

### What is SpreadPilot?

SpreadPilot is an automated copy-trading platform for QQQ options spread strategies. It replicates trading signals from Google Sheets to multiple Interactive Brokers accounts belonging to subscribers ("followers").

### Core Workflow

1. **Signal Generation**: Trading signals created in Google Sheets by strategy managers
2. **Automated Execution**: Trading Bot reads signals and places trades for all followers
3. **Position Management**: System monitors positions and manages assignments/expirations
4. **Notifications**: Critical alerts sent via Telegram and email
5. **Reporting**: Monthly performance reports generated and sent to followers

### Key Components

- **Trading Bot** 🤖: Executes trades via Interactive Brokers
- **Admin API** 🛠️: Provides administrative control over followers and settings
- **Frontend Dashboard** 📊: Web interface for monitoring and control
- **Report Worker** 📑: Generates performance reports and P&L calculations
- **Alert Router** 🚨: Ensures critical notifications reach administrators and followers
- **Watchdog** 👀: Monitors system health and detects issues
- **SpreadPilot Core**: Shared library with common functionality
- **Infrastructure Services**: IB Gateway, MongoDB
- **Observability Services**: OpenTelemetry, Prometheus, Grafana

### Technical Implementation

- Microservices architecture deployed on Google Cloud Platform
- Python-based backend services (FastAPI, Flask)
- React frontend with TypeScript
- MongoDB for data persistence
- Pub/Sub for asynchronous communication

### Next Steps for Onboarding

- [x] Review the setup documentation for each component
- [x] Understand the development environment setup
- [x] Explore the codebase organization
- [x] Review deployment and operations procedures

## MongoDB Setup (2025-05-18)

Today we reviewed the MongoDB setup documentation for SpreadPilot. MongoDB serves as the primary database for the system, storing follower information, positions, trades, and system configuration.

### Key Points

1. **Docker-based Setup**: MongoDB runs as a Docker container, configured in `docker-compose.yml`
   - Uses MongoDB 7.x
   - Persistent storage via Docker volumes
   - Healthcheck configured to ensure proper operation

2. **Environment Configuration**:
   - Credentials stored in `.env` file
   - Requires `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD`

3. **Application Database and User**:
   - Dedicated database named `spreadpilot`
   - Application-specific user with restricted permissions
   - Follows principle of least privilege

4. **Setup Process**:
   - Start MongoDB container: `docker-compose up -d mongodb`
   - Verify container is running: `docker ps | grep mongodb`
   - Connect with root user to create application database and user
   - Create dedicated user with `readWrite` permissions only on the application database
   - Verify application user access

5. **Security Considerations**:
   - Strong, unique passwords for production
   - Consider secrets management solutions
   - Restrict network access
   - Enable authentication and TLS/SSL
   - Implement regular backups

### Next Steps

- [x] Set up MongoDB
- [x] Set up Interactive Brokers Gateway
- [x] Configure Trading Bot
- [x] Set up Admin API
- [x] Configure Frontend

## Interactive Brokers Gateway Setup (2025-05-18)

Today we reviewed the Interactive Brokers (IB) Gateway setup documentation for SpreadPilot. The IB Gateway serves as the bridge between the trading bot and the Interactive Brokers trading platform.

### Key Points

1. **Purpose and Role**:
   - Provides programmatic interface to Interactive Brokers
   - Handles authentication with IB servers
   - Maintains connection to IB trading platform
   - Enables API access for placing orders, retrieving account info, and market data

2. **Docker-based Setup**:
   - Uses containerized version of IB Gateway (`ghcr.io/gnzsnz/ib-gateway`)
   - Configured in `docker-compose.yml`
   - Exposes port 4002 for API access
   - Automatic restart unless explicitly stopped

3. **Environment Configuration**:
   - Credentials stored in `.env` file
   - Requires `IB_USERNAME` and `IB_PASSWORD`
   - Configured for paper trading mode via `TRADING_MODE=paper`

4. **Paper vs. Live Trading**:
   - Development uses paper trading accounts (not live accounts)
   - Paper trading accounts have different credentials than live accounts
   - Paper trading usernames typically start with "paper" or "demo"
   - Must use appropriate credentials for the selected trading mode

5. **Setup Process**:
   - Configure credentials in `.env`
   - Start container: `docker-compose up -d ib-gateway`
   - Verify container is running: `docker ps | grep ib-gateway`
   - Check logs: `docker logs spreadpilot-ib-gateway`
   - Test connection with telnet or Python script

6. **Common Issues**:
   - Authentication failures (wrong credentials, account restrictions)
   - Connection issues (network problems, IB service downtime)
   - Container startup failures (image issues, resource constraints)

7. **Security Considerations**:
   - Use dedicated trading accounts with risk controls
   - Implement proper secrets management
   - Consider network isolation
   - Implement monitoring and alerting

## Trading Bot Setup (2025-05-18)

Today we reviewed the Trading Bot setup documentation for SpreadPilot. The Trading Bot is the core service of the system, responsible for executing trades based on signals from Google Sheets.

### Key Points

1. **Purpose and Responsibilities**:
   - Connects to Interactive Brokers via the IB Gateway
   - Polls Google Sheets for trading signals
   - Executes orders based on those signals
   - Monitors positions for assignments
   - Calculates profit and loss (P&L)
   - Generates alerts for important events

2. **Technical Implementation**:
   - Implemented as a FastAPI application
   - Runs in a Docker container
   - Uses the `spreadpilot-core` library for common functionality
   - Exposes API endpoints for health checks, status, and manual commands

3. **Docker Configuration**:
   - Built from Dockerfile in the `trading-bot` directory
   - Depends on MongoDB and IB Gateway services
   - Exposes port 8081 on the host (mapping to 8080 in container)
   - Mounts credentials directory for Google API authentication

4. **Environment Configuration**:
   - Google Sheets URL and API key for trading signals
   - IB Gateway connection details
   - Notification settings (Telegram, SendGrid)
   - Trading parameters (min price, price increment, etc.)

5. **Google Sheets Setup**:
   - Requires a Google Sheet with specific structure
   - Columns for strategy name, quantity per leg, strike prices
   - Sheet must be accessible to the service account
   - API key needed for authentication

6. **Setup Process**:
   - Configure environment variables in `.env`
   - Start container: `docker-compose up -d trading-bot`
   - Verify container is running: `docker ps | grep trading-bot`
   - Check logs: `docker logs spreadpilot-trading-bot`
   - Test API endpoints (health, status, manual signal)

7. **Common Issues**:
   - Connection problems with IB Gateway
   - Google Sheets authentication failures
   - MongoDB connection issues
   - Container startup failures

8. **Security Considerations**:
   - Strong, unique API keys and credentials
   - Proper secrets management
   - Restricted API access
   - Network isolation
   - Monitoring and alerting
   - Regular auditing

## Admin API Setup (2025-05-18)

Today we reviewed the Admin API setup documentation for SpreadPilot. The Admin API provides an administrative interface for the SpreadPilot trading system.

### Key Points

1. **Purpose and Responsibilities**:
   - User authentication and authorization for administrative access
   - Managing followers (users/accounts that replicate trades)
   - Providing dashboard data for monitoring trading activity
   - Exposing endpoints for manual control (e.g., closing positions)
   - Serving as the backend for the frontend web interface

2. **Technical Implementation**:
   - Implemented as a FastAPI application
   - Runs in a Docker container
   - Communicates with MongoDB for data persistence
   - Interacts with the Trading Bot for executing commands

3. **Docker Configuration**:
   - Built from Dockerfile in the `admin-api` directory
   - Depends on MongoDB and Trading Bot services
   - Exposes port 8083 on the host (mapping to 8080 in container)
   - Mounts credentials directory for Google API authentication

4. **Environment Configuration**:
   - Admin authentication settings (username, password hash, JWT secret)
   - MongoDB connection details
   - Trading Bot connection details
   - Default admin username is "admin" if not specified

5. **Authentication Setup**:
   - Requires bcrypt-hashed password in `.env` file
   - Uses JWT (JSON Web Tokens) for authentication
   - Python script provided for generating password hashes

6. **Setup Process**:
   - Configure environment variables in `.env`
   - Generate password hash for admin user
   - Start container: `docker-compose up -d admin-api`
   - Verify container is running: `docker ps | grep admin-api`
   - Check logs: `docker logs spreadpilot-admin-api`
   - Test API endpoints (health, authentication, followers)

7. **Common Issues**:
   - Authentication problems (incorrect credentials, JWT issues)
   - MongoDB connection failures
   - Trading Bot connection issues
   - Container startup failures

8. **Security Considerations**:
   - Strong, unique passwords and JWT secrets
   - Proper secrets management
   - HTTPS for production environments
   - Access restrictions
   - Rate limiting for brute force prevention
   - Regular auditing
   - Consider two-factor authentication

## Frontend Setup (2025-05-18)

Today we reviewed the Frontend setup documentation for SpreadPilot. The Frontend provides a web-based user interface for the SpreadPilot trading system.

### Key Points

1. **Purpose and Responsibilities**:
   - Providing a login interface for administrators
   - Displaying a dashboard with trading statistics and follower status
   - Allowing administrators to manage followers (enable/disable, view details)
   - Providing interfaces for viewing logs and issuing manual commands
   - Communicating with the Admin API for data and actions

2. **Technical Implementation**:
   - Implemented as a React application
   - Runs in a Docker container (Nginx serving static files)
   - Communicates with the Admin API for data and actions
   - Uses WebSockets for real-time updates

3. **Docker Configuration**:
   - Built from Dockerfile in the `frontend` directory
   - Depends on Admin API service
   - Exposes port 8080 on the host (mapping to port 80 in container)
   - Environment variables for API and WebSocket URLs

4. **Environment Configuration**:
   - `REACT_APP_API_URL` points to the Admin API URL
   - `REACT_APP_WS_URL` points to the Admin API WebSocket URL
   - For local development, these point to localhost ports
   - For production, these point to appropriate domain/IP

5. **Setup Process**:
   - Configure environment variables in `.env`
   - Start container: `docker-compose up -d frontend`
   - Verify container is running: `docker ps | grep frontend`
   - Access the frontend in a web browser at http://localhost:8080
   - Log in using admin credentials configured in Admin API

6. **Local Development**:
   - Navigate to frontend directory
   - Install dependencies with `npm install`
   - Create `.env.local` file with API URLs
   - Start development server with `npm start`
   - Access at http://localhost:3000

7. **Common Issues**:
   - Connection problems with Admin API
   - Login failures (authentication issues)
   - Container startup failures

8. **Security Considerations**:
   - Use HTTPS for production
   - Implement proper authentication
   - Consider Content Security Policy (CSP)
   - Regular dependency updates
   - Rate limiting
   - Consider two-factor authentication

9. **Customization Options**:
   - Theme colors in `frontend/src/index.css`
   - Logo in `frontend/src/assets/`
   - Layout components in `frontend/src/components/layout/`
   - Pages in `frontend/src/pages/`

## Codebase Organization (2025-05-18)

Today we explored the codebase organization of SpreadPilot in detail. The project follows a monorepo structure with multiple services, each with its own directory and code organization.

### Repository Structure

```
spreadpilot/
├── spreadpilot-core/         # Core library
│   └── spreadpilot_core/
│       ├── logging/          # Structured logging
│       ├── ibkr/             # IBKR client wrapper
│       ├── models/           # Database models (MongoDB)
│       └── utils/            # Utilities
├── trading-bot/              # Trading bot service
├── watchdog/                 # Watchdog service
├── admin-api/                # Admin API service
├── report-worker/            # Report worker service
├── alert-router/             # Alert router service
├── frontend/                 # React frontend
├── config/                   # Configuration files
├── credentials/              # Credentials (gitignored)
├── reports/                  # Generated reports
└── docker-compose.yml        # Local development setup
```

### SpreadPilot Core Library

The `spreadpilot-core` package provides shared functionality used by all services:

- **logging**: Structured logging with context
  - `logger.py`: Configures structured logging with OpenTelemetry integration

- **ibkr**: Interactive Brokers client wrapper
  - `client.py`: Async client for interacting with IB Gateway

- **models**: Database data models (MongoDB)
  - `alert.py`: Alert event model
  - `follower.py`: Follower account model
  - `position.py`: Trading position model
  - `trade.py`: Trade execution model

- **utils**: Utility functions
  - `email.py`: Email sending utilities using SendGrid
  - `excel.py`: Excel report generation utilities
  - `pdf.py`: PDF report generation utilities
  - `telegram.py`: Telegram messaging utilities
  - `time.py`: Time and date handling utilities

### Trading Bot Service

The `trading-bot` service is responsible for executing trades based on signals from Google Sheets:

- **app/config.py**: Configuration loading and validation
- **app/main.py**: Main entry point and API server
- **app/sheets.py**: Google Sheets integration
- **app/service/**: Service modules
  - **alerts.py**: Alert generation
  - **base.py**: Base service class
  - **ibkr.py**: IBKR integration
  - **positions.py**: Position management
  - **signals.py**: Signal processing

### Watchdog Service

The `watchdog` service monitors the health of critical components:

- **app/config.py**: Configuration loading and validation
- **app/main.py**: Main entry point and scheduler
- **app/service/**: Service modules
  - **monitor.py**: Health monitoring and restart logic

### Admin API Service

The `admin-api` service provides the backend for the admin dashboard:

- **main.py**: Main entry point
- **app/core/**: Core modules
  - **config.py**: Configuration loading and validation
- **app/api/**: API modules
  - **v1/api.py**: API router
  - **v1/endpoints/**: API endpoints
    - **dashboard.py**: Dashboard endpoints
    - **followers.py**: Follower management endpoints
- **app/db/**: Database modules
  - **mongodb.py**: MongoDB client (using Motor)
- **app/schemas/**: Pydantic schemas
  - **follower.py**: Follower schemas
- **app/services/**: Service modules
  - **follower_service.py**: Follower management service

### Report Worker Service

The `report-worker` service generates reports for followers:

- **app/config.py**: Configuration loading and validation
- **app/main.py**: Main entry point and Pub/Sub handler
- **app/service/**: Service modules
  - **pnl.py**: P&L calculation
  - **generator.py**: Report generation
  - **notifier.py**: Email notification
  - **report_service.py**: Report orchestration

### Alert Router Service

The `alert-router` service routes alerts to appropriate channels:

- **app/config.py**: Configuration loading and validation
- **app/main.py**: Main entry point and Pub/Sub handler
- **app/service/**: Service modules
  - **router.py**: Alert routing logic

### Frontend

The `frontend` is a React application for the admin dashboard:

- **src/main.tsx**: Main entry point
- **src/App.tsx**: Root component
- **src/components/**: UI components
  - **layout/**: Layout components
- **src/contexts/**: React contexts
  - **AuthContext.tsx**: Authentication context
  - **WebSocketContext.tsx**: WebSocket context
- **src/hooks/**: Custom React hooks
- **src/pages/**: Page components
  - **CommandsPage.tsx**: Manual commands page
  - **FollowersPage.tsx**: Follower management page
  - **LoginPage.tsx**: Login page
  - **LogsPage.tsx**: Log console page
- **src/services/**: API services
  - **followerService.ts**: Follower API service
  - **logService.ts**: Log API service
- **src/types/**: TypeScript type definitions
  - **follower.ts**: Follower types
  - **logEntry.ts**: Log entry types
- **src/utils/**: Utility functions

### Code Organization Patterns

1. **Service Structure**: Each service follows a similar structure:
   - `config.py`: Configuration loading and validation
   - `main.py`: Main entry point
   - `service/`: Service modules with specific functionality

2. **Dependency Injection**: Services use dependency injection to manage dependencies:
   - Configuration is loaded at startup
   - Services are initialized with dependencies
   - Dependencies are passed to functions that need them

3. **Asynchronous Programming**: Services use `async/await` for non-blocking I/O:
   - Database operations
   - API calls
   - File operations

4. **Error Handling**: Services use structured logging and exception handling:
   - Exceptions are caught and logged
   - Errors are propagated to the appropriate level
   - User-friendly error messages are returned

5. **Testing**: Services have unit and integration tests:
   - Unit tests for individual functions
   - Integration tests for service interactions
   - End-to-end tests for complete workflows

## Development Environment Setup (2025-05-18)

Today we reviewed the development environment setup for SpreadPilot. This covers how to set up a local development environment, run services, and understand the development workflow.

### Key Points

1. **Prerequisites**:
   - Python 3.11 or higher
   - Node.js 18 or higher
   - Docker and Docker Compose
   - Git
   - Make (optional, but recommended)

2. **Repository Structure**:
   - Monorepo organization with multiple services
   - Hyphenated directory names (`trading-bot`, `admin-api`, etc.)
   - Special import pattern using `importlib.import_module()` for hyphenated directories

3. **Initial Setup**:
   - Clone the repository
   - Create `.env` file with required environment variables
   - Create `credentials` directory with Google Cloud service account key
   - Initialize development environment with virtual environment
   - Install core library and dependencies

4. **Running Services**:
   - **Docker Compose (All Services)**:
     - `docker-compose up -d` or `make up` to start all services
     - `docker-compose logs -f` or `make logs` to view logs
     - `docker-compose down` or `make down` to stop services
   
   - **Individual Services (Local Development)**:
     - Trading Bot: `python trading-bot/app/main.py`
     - Admin API: `python admin-api/main.py`
     - Frontend: `cd frontend && npm run dev`

5. **Testing**:
   - Run all tests: `pytest` or `make test`
   - Run with coverage: `make test-coverage`
   - Run specific tests: `pytest trading-bot/tests/`
   - End-to-end tests: `make e2e`

6. **Development Workflow**:
   - Create feature branch
   - Make changes and run tests
   - Format code with Black and isort
   - Commit changes
   - Push and create pull request

7. **Debugging**:
   - Python debugger (pdb)
   - VS Code debugger configuration
   - React Developer Tools for frontend

8. **Common Development Tasks**:
   - Adding new dependencies
   - Adding new models to SpreadPilot Core
   - Adding new API endpoints
   - Adding new frontend pages
   - Creating new services

9. **Troubleshooting**:
   - MongoDB connection issues
   - IB Gateway connection issues
   - Frontend build issues

10. **Best Practices**:
    - Code style (PEP 8, Black, ESLint)
    - Testing (unit tests, fixtures, mocks)
    - Documentation (docstrings, README updates, type hints)
    - Error handling (structured logging, exceptions)
    - Configuration (environment variables, defaults, validation)

## Deployment and Operations (2025-05-18)

Today we reviewed the deployment and operations procedures for SpreadPilot. This covers how to deploy the system to Google Cloud Platform (GCP) and how to monitor, maintain, and troubleshoot the system in production.

### Deployment Process

1. **Initial GCP Setup**:
   - Create a GCP project
   - Enable required APIs (Cloud Build, Cloud Run, Artifact Registry, Firestore, Secret Manager, etc.)
   - Set up Firestore database
   - Create Artifact Registry repository

2. **Secret Management**:
   - Create secrets in Secret Manager for sensitive configuration
   - Create service account for accessing secrets
   - Grant appropriate IAM roles to service account

3. **Pub/Sub Setup**:
   - Create topics for event-driven communication (alerts, daily-reports, monthly-reports)
   - Create subscriptions for services

4. **Cloud Run Deployment**:
   - Deploy each service to Cloud Run:
     - Trading Bot
     - Watchdog
     - Admin API
     - Report Worker
     - Alert Router
     - Frontend
     - IB Gateway
   - Configure environment variables and secrets
   - Set resource allocation (memory, CPU)
   - Configure scaling parameters

5. **Cloud Scheduler Setup**:
   - Create scheduler for daily reports
   - Create scheduler for monthly reports

6. **CI/CD Setup**:
   - Create Cloud Build triggers for main and dev branches
   - Create Cloud Build configuration files

7. **Domain and SSL Setup**:
   - Configure custom domain for frontend
   - GCP automatically provisions SSL certificates

### Monitoring and Observability

1. **Cloud Monitoring**:
   - Access via Google Cloud Console
   - Key dashboards:
     - SpreadPilot Overview
     - Trading Bot Performance
     - Service Health
     - Error Rates

2. **Grafana**:
   - Advanced visualization
   - Key dashboards:
     - System Overview
     - Trading Performance
     - Service Performance
     - Error Tracking

3. **Logging**:
   - Structured logging with Cloud Logging
   - Common log queries:
     - View logs for specific services
     - View error logs
     - View logs for specific followers
     - View logs for specific operations

4. **Alerting**:
   - Cloud Monitoring alerting policies
   - Predefined alerts:
     - Service Availability
     - Error Rate
     - Trading Bot Health
     - IB Gateway Connection
     - Assignment Detection
   - Notification channels:
     - Email
     - Telegram
     - SMS
     - PagerDuty

### Routine Maintenance

1. **Backup and Restore**:
   - MongoDB backup strategies
   - Restore procedures

2. **Service Updates**:
   - Deploying new versions
   - Rolling back to previous versions

3. **Secret Rotation**:
   - Adding new versions of secrets
   - Restarting affected services

### Troubleshooting

1. **Common Issues**:
   - Trading Bot not executing orders
   - Watchdog false positives
   - Report generation failures
   - Alert routing failures

2. **Diagnostic Procedures**:
   - Health check endpoints
   - Service logs
   - Database inspection
   - Manual testing

3. **Recovery Procedures**:
   - Service recovery
   - IB Gateway recovery
   - Database recovery

### Performance Tuning

1. **Resource Allocation**:
   - Adjusting memory and CPU
   - Scaling configuration

2. **Performance Monitoring**:
   - Key metrics:
     - Request latency
     - CPU utilization
     - Memory usage
     - Error rate
     - Instance count

### Security

1. **Access Control**:
   - Managing service account permissions
   - Managing user access

2. **Audit Logging**:
   - Viewing audit logs
   - Configuring audit logging

3. **Disaster Recovery**:
   - Backup strategy
   - Recovery plan

## References

- [system-architecture.md](../../system-architecture.md)
- [docs/01-system-architecture.md](../../docs/01-system-architecture.md)
- [docs/setup/README.md](../../docs/setup/README.md)
- [docs/setup/0-mongodb.md](../../docs/setup/0-mongodb.md)
- [docs/setup/1-ib-gateway.md](../../docs/setup/1-ib-gateway.md)
- [docs/setup/2-trading-bot.md](../../docs/setup/2-trading-bot.md)
- [docs/setup/3-admin-api.md](../../docs/setup/3-admin-api.md)
- [docs/setup/4-frontend.md](../../docs/setup/4-frontend.md)
- [docs/03-development-guide.md](../../docs/03-development-guide.md)
- [docs/02-deployment-guide.md](../../docs/02-deployment-guide.md)
- [docs/04-operations-guide.md](../../docs/04-operations-guide.md)
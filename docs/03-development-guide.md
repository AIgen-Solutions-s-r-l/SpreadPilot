# SpreadPilot Development Guide

This guide provides instructions for setting up a local development environment for the SpreadPilot project, running the services locally, testing individual components, and understanding the code structure.

## Prerequisites

Before you begin, ensure you have the following installed on your development machine:

- Python 3.11 or higher
- Node.js 18 or higher
- Docker and Docker Compose
- Git
- Make (optional, but recommended)

## Repository Structure

The SpreadPilot project is organized as a monorepo with the following structure:

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

### Folder Naming Convention

SpreadPilot uses hyphenated directory names (`trading-bot`, `admin-api`, etc.) for all services. Each service directory contains an `__init__.py` file that makes it importable as a Python package.

### Importing from Hyphenated Directories

When importing from hyphenated directories in Python code, you need to use the `importlib.import_module()` function since Python's standard import syntax doesn't support hyphens in module names:

```python
# Import modules using importlib
import importlib

# Import the entire module
trading_bot_service = importlib.import_module('trading-bot.app.service.signals')
admin_api_main = importlib.import_module('admin-api.app.main')

# Import specific components
SignalProcessor = trading_bot_service.SignalProcessor
admin_app = admin_api_main.app
```

This approach allows us to maintain a consistent naming convention across deployment and testing environments while still supporting Python imports.

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/spreadpilot.git
cd spreadpilot
```

### 2. Set Up Environment Variables

Create a `.env` file in the root directory with the following variables:

```bash
# IBKR credentials
IB_USERNAME=your_ib_username
IB_PASSWORD=your_ib_password

# Google Sheets
GOOGLE_SHEET_URL=your_google_sheet_url

# Alerting
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
SENDGRID_API_KEY=your_sendgrid_api_key
ADMIN_EMAIL=admin@example.com

# Admin dashboard
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=bcrypt_hash_of_your_password
JWT_SECRET=your_jwt_secret
DASHBOARD_URL=http://localhost:8080

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

### 3. Create Credentials Directory

Create a `credentials` directory in the root of the project and add your Google Cloud service account key file:

```bash
mkdir -p credentials
# Copy your service account key file to credentials/service-account.json
```

### 4. Initialize Development Environment

If you have Make installed, you can use the provided Makefile to set up the development environment:

```bash
make init-dev
```

Alternatively, you can run the following commands manually:

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install the core library in development mode
pip install -e ./spreadpilot-core

# Install development dependencies
pip install -r requirements-dev.in
```

## Running Services Locally

### 1. Start All Services with Docker Compose

The easiest way to run the entire SpreadPilot system locally is using Docker Compose:

```bash
# Using Make
make up

# Or directly with Docker Compose
docker-compose up -d
```

This will start all services defined in the `docker-compose.yml` file, including:

- Core services (trading-bot, watchdog, admin-api, report-worker, alert-router, frontend)
- Infrastructure services (firestore emulator, ib-gateway)
- Observability services (otel-collector, prometheus, grafana)

### 2. View Service Logs

```bash
# View logs for all services
make logs

# Or directly with Docker Compose
docker-compose logs -f

# View logs for a specific service
docker-compose logs -f trading-bot
```

### 3. Stop Services

```bash
# Using Make
make down

# Or directly with Docker Compose
docker-compose down
```

## Running Individual Services

During development, you may want to run individual services directly on your machine rather than in Docker containers. This allows for faster iteration and easier debugging.

### 1. Running the Trading Bot

```bash
# Activate the virtual environment if not already activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Set environment variables
export GOOGLE_CLOUD_PROJECT=spreadpilot-dev
export FIRESTORE_EMULATOR_HOST=localhost:8084
export IB_GATEWAY_HOST=localhost
export IB_GATEWAY_PORT=4002
# Set other required environment variables from .env

# Run the trading bot
python trading-bot/app/main.py
```

### 2. Running the Admin API

```bash
# Activate the virtual environment if not already activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Set environment variables
export GOOGLE_CLOUD_PROJECT=spreadpilot-dev
export FIRESTORE_EMULATOR_HOST=localhost:8084
export TRADING_BOT_HOST=localhost
export TRADING_BOT_PORT=8081
# Set other required environment variables from .env

# Run the admin API
python admin-api/main.py
```

> **Note:** When running services directly, Python will automatically use the `__init__.py` files in the hyphenated directories to resolve imports. However, when writing code that imports from these directories, you'll need to use `importlib.import_module()` as described in the "Importing from Hyphenated Directories" section.

### 3. Running the Frontend

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend development server will be available at http://localhost:5173.

## Testing

### 1. Running All Tests

```bash
# Using Make
make test

# Or directly with pytest
pytest
```

### 2. Running Tests with Coverage

```bash
# Using Make
make test-coverage

# Or directly with pytest
pytest --cov=spreadpilot_core --cov=trading-bot --cov=watchdog --cov=admin-api --cov=report-worker --cov=alert-router
```

### 3. Running Tests for a Specific Component

```bash
# Run tests for a specific service
pytest trading-bot/tests/

# Run a specific test file
pytest watchdog/tests/service/test_monitor.py

# Run a specific test function
pytest watchdog/tests/service/test_monitor.py::test_check_health
```

### Test Import Patterns

The integration tests use `importlib.import_module()` to import from hyphenated directories. This pattern is used in `tests/integration/conftest.py` and other test files:

```python
# Import modules using importlib
import importlib

# Import modules with hyphenated names
trading_bot_service = importlib.import_module('trading-bot.app.service.signals')
alert_router_service = importlib.import_module('alert-router.app.service.router')

# Get specific imports
SignalProcessor = trading_bot_service.SignalProcessor
route_alert = alert_router_service.route_alert
```

When writing new tests, follow this pattern for importing from hyphenated directories.

### 4. Running End-to-End Tests

```bash
# Using Make
make e2e

# Or directly with pytest
pytest -m e2e
```

## Code Structure and Organization

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

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes and Run Tests

Make your changes to the codebase and run tests to ensure everything works correctly:

```bash
# Run tests
make test

# Run linters
make lint
```

### 3. Format Your Code

```bash
# Using Make
make format

# Or directly with black and isort
black spreadpilot-core trading-bot watchdog admin-api report-worker alert-router
isort spreadpilot-core trading-bot watchdog admin-api report-worker alert-router
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "Add your feature description"
```

### 5. Push Your Changes and Create a Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Debugging

### 1. Using pdb

You can use the Python debugger (pdb) to debug Python services:

```python
import pdb; pdb.set_trace()
```

### 2. Using VS Code Debugger

Create a `.vscode/launch.json` file with the following configuration:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "env": {
        "GOOGLE_CLOUD_PROJECT": "spreadpilot-dev",
        "FIRESTORE_EMULATOR_HOST": "localhost:8084"
      }
    },
    {
      "name": "Python: Trading Bot",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/trading-bot/app/main.py",
      "console": "integratedTerminal",
      "env": {
        "GOOGLE_CLOUD_PROJECT": "spreadpilot-dev",
        "FIRESTORE_EMULATOR_HOST": "localhost:8084",
        "IB_GATEWAY_HOST": "localhost",
        "IB_GATEWAY_PORT": "4002"
      }
    }
  ]
}
```

### 3. Using React Developer Tools

For debugging the frontend, install the React Developer Tools browser extension:

- [React Developer Tools for Chrome](https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi)
- [React Developer Tools for Firefox](https://addons.mozilla.org/en-US/firefox/addon/react-devtools/)

## Common Development Tasks

### 1. Adding a New Dependency

For Python services:

```bash
# Add to requirements.in file
echo "new-package==1.0.0" >> requirements-dev.in

# Generate requirements.txt
make requirements-dev

# Install the new dependency
pip install -r requirements-dev.txt
```

For the frontend:

```bash
cd frontend
npm install --save new-package
```

### 2. Adding a New Model to SpreadPilot Core

1. Create a new file in `spreadpilot-core/spreadpilot_core/models/`
2. Define the model class with Pydantic
3. Add the model to `spreadpilot-core/spreadpilot_core/models/__init__.py`

### 3. Adding a New API Endpoint

1. Create a new file in `admin-api/app/api/v1/endpoints/` or add to an existing one
2. Define the endpoint function with FastAPI
3. Add the endpoint to the router in `admin-api/app/api/v1/api.py`

### 4. Adding a New Frontend Page

1. Create a new file in `frontend/src/pages/`
2. Define the page component with React
3. Add the page to the router in `frontend/src/App.tsx`

### 5. Creating a New Service

When creating a new service, follow the established folder structure convention:

1. Use hyphenated directory names (e.g., `new-service/`)
2. Add `__init__.py` files to make the directory importable:

```bash
# Create the service directory structure
mkdir -p new-service/app/service

# Add __init__.py files
touch new-service/__init__.py
touch new-service/app/__init__.py
touch new-service/app/service/__init__.py
```

3. When importing from this service in other parts of the codebase, use `importlib.import_module()`:

```python
import importlib
new_service_module = importlib.import_module('new-service.app.service.main')
```

## Troubleshooting

### 1. MongoDB Connection Issues (Local Docker)

If you encounter issues connecting to the MongoDB container defined in `docker-compose.yml`, try the following:

```bash
# Stop all services
make down

# Check Docker container status
docker-compose ps

# Check MongoDB container logs
docker-compose logs mongo

# Ensure MongoDB container is running
docker-compose up -d mongo

# Verify connection details (host: mongo, port: 27017, credentials) in service environment variables
# (Check .env files and docker-compose.yml)

# If data corruption is suspected (rarely needed for local dev):
# Stop the container
docker-compose stop mongo
# Remove the volume (WARNING: DELETES ALL LOCAL MONGO DATA)
docker volume rm spreadpilot_mongo_data
# Restart the container
docker-compose up -d mongo

# Restart services
make up
```

### 2. IB Gateway Connection Issues

If the trading bot cannot connect to IB Gateway, check the following:

- Ensure IB Gateway is running (`docker-compose logs ib-gateway`)
- Verify the IB Gateway credentials in the `.env` file
- Check the network connectivity between the trading bot and IB Gateway

### 3. Frontend Build Issues

If you encounter issues building the frontend, try the following:

```bash
cd frontend

# Clear node_modules and reinstall dependencies
rm -rf node_modules
npm install

# Clear Vite cache
rm -rf node_modules/.vite

# Restart the development server
npm run dev
```

## Best Practices

### 1. Code Style

- Follow PEP 8 for Python code
- Use Black and isort for code formatting
- Use ESLint and Prettier for JavaScript/TypeScript code

### 2. Testing

- Write unit tests for all new functionality
- Use pytest fixtures for common test setup
- Use mocks for external dependencies

### 3. Documentation

- Add docstrings to all functions and classes
- Update README.md and other documentation when making significant changes
- Use type hints in Python code

### 4. Error Handling

- Use structured logging for errors
- Handle exceptions appropriately
- Provide meaningful error messages

### 5. Configuration

- Use environment variables for configuration
- Provide sensible defaults
- Validate configuration at startup

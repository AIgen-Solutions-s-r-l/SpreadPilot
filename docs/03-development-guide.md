# 🚀 SpreadPilot Development Guide

This comprehensive guide provides instructions for setting up a local development environment for the SpreadPilot project, running services locally, testing components, and understanding the code structure.

## 📋 Table of Contents

- [Prerequisites](#-prerequisites)
- [Repository Structure](#-repository-structure)
- [Initial Setup](#-initial-setup)
- [Running Services](#-running-services)
- [Testing](#-testing)
- [Code Organization](#-code-organization)
- [Development Workflow](#-development-workflow)
- [Debugging](#-debugging)
- [Common Tasks](#-common-tasks)
- [Troubleshooting](#-troubleshooting)
- [Best Practices](#-best-practices)

## 🔧 Prerequisites

Before you begin, ensure you have the following installed on your development machine:

- **Python** 3.11 or higher
- **Node.js** 18 or higher
- **Docker** and Docker Compose
- **Git**
- **Make** (optional, but recommended)
- **Google Cloud SDK** (for production deployments)

## 📁 Repository Structure

The SpreadPilot project is organized as a monorepo with the following structure:

```
spreadpilot/
├── 📦 spreadpilot-core/         # Core library
│   └── spreadpilot_core/
│       ├── 📊 logging/          # Structured logging
│       ├── 💹 ibkr/             # IBKR client wrapper
│       ├── 🗄️ models/           # Database models (MongoDB)
│       └── 🛠️ utils/            # Utilities
├── 🤖 trading-bot/              # Trading bot service
├── 👁️ watchdog/                 # Watchdog service
├── 🎛️ admin-api/                # Admin API service
├── 📈 report-worker/            # Report worker service
├── 🚨 alert-router/             # Alert router service
├── 🖥️ frontend/                 # React frontend
├── 🏗️ infra/                    # Infrastructure (Docker Compose)
│   ├── docker-compose.yml       # Infrastructure services
│   ├── compose-up.sh           # Infrastructure startup script
│   ├── compose-down.sh         # Infrastructure shutdown script
│   ├── health-check.sh         # Infrastructure health monitoring
│   └── README.md               # Infrastructure documentation
├── ⚙️ config/                   # Configuration files
├── 🔐 credentials/              # Credentials (gitignored)
├── 📄 reports/                  # Generated reports
└── 🐳 docker-compose.yml        # Application services setup
```

### 🏷️ Folder Naming Convention

SpreadPilot uses **hyphenated directory names** (`trading-bot`, `admin-api`, etc.) for all services. Each service directory contains an `__init__.py` file that makes it importable as a Python package.

### 📦 Importing from Hyphenated Directories

When importing from hyphenated directories in Python code, use the `importlib.import_module()` function since Python's standard import syntax doesn't support hyphens:

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

## 🚀 Initial Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/yourusername/spreadpilot.git
cd spreadpilot
```

### 2️⃣ Set Up Environment Variables

Create a `.env` file in the root directory with the following variables:

```bash
# 💹 IBKR credentials
IB_USERNAME=your_ib_username
IB_PASSWORD=your_ib_password

# 📊 Google Sheets
GOOGLE_SHEET_URL=your_google_sheet_url

# 🚨 Alerting
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
SENDGRID_API_KEY=your_sendgrid_api_key
ADMIN_EMAIL=admin@example.com

# 🎛️ Admin dashboard
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=bcrypt_hash_of_your_password
JWT_SECRET=your_jwt_secret
DASHBOARD_URL=http://localhost:8080

# 📊 Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

### 3️⃣ Create Credentials Directory

Create a `credentials` directory and add your Google Cloud service account key:

```bash
mkdir -p credentials
# Copy your service account key file to credentials/service-account.json
cp /path/to/your/service-account.json credentials/
```

### 4️⃣ Initialize Development Environment

Using Make (recommended):

```bash
make init-dev
```

Or manually:

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

## 🏃 Running Services

### 🐳 Start All Services with Docker Compose

The easiest way to run the entire SpreadPilot system locally:

```bash
# 1. Start infrastructure services
cd infra/
./compose-up.sh
cd ..

# 2. Start application services
make up
# Or directly: docker-compose up -d
```

This will start:

**Core Services:**
- 🤖 Trading Bot
- 👁️ Watchdog
- 🎛️ Admin API
- 📈 Report Worker
- 🚨 Alert Router
- 🖥️ Frontend

**Infrastructure Services:**
- 🗄️ PostgreSQL
- 🔐 Vault
- 📦 MinIO
- 🌐 Traefik

**Observability:**
- 📊 Prometheus
- 📈 Grafana
- 🔍 OpenTelemetry Collector

### 📋 View Service Logs

```bash
# All application services
make logs

# Specific application service
docker-compose logs -f trading-bot

# Infrastructure services
cd infra/ && docker-compose logs -f postgres
```

### 🛑 Stop Services

```bash
# Stop application services
make down

# Stop infrastructure services
cd infra/ && ./compose-down.sh
```

## 🧪 Running Individual Services

For faster iteration during development:

### 🤖 Trading Bot

```bash
# Activate virtual environment
source venv/bin/activate

# Set environment variables
export GOOGLE_CLOUD_PROJECT=spreadpilot-dev
export FIRESTORE_EMULATOR_HOST=localhost:8084
export IB_GATEWAY_HOST=localhost
export IB_GATEWAY_PORT=4002
source infra/.env.infra

# Run the service
python trading-bot/app/main.py
```

### 🎛️ Admin API

```bash
# Activate virtual environment
source venv/bin/activate

# Set environment variables
export GOOGLE_CLOUD_PROJECT=spreadpilot-dev
export FIRESTORE_EMULATOR_HOST=localhost:8084
export TRADING_BOT_HOST=localhost
export TRADING_BOT_PORT=8081
source infra/.env.infra

# Run the service
python admin-api/main.py
```

### 🖥️ Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

## 🧪 Testing

### ✅ Run All Tests

```bash
make test
# Or: pytest
```

### 📊 Run Tests with Coverage

```bash
make test-coverage
# Or: pytest --cov=spreadpilot_core --cov=trading-bot --cov=watchdog --cov=admin-api --cov=report-worker --cov=alert-router
```

### 🎯 Run Specific Tests

```bash
# Test a specific service
pytest trading-bot/tests/

# Test a specific file
pytest watchdog/tests/service/test_monitor.py

# Test a specific function
pytest watchdog/tests/service/test_monitor.py::test_check_health
```

### 📦 Test Import Patterns

When writing tests for hyphenated directories:

```python
import importlib

# Import modules with hyphenated names
trading_bot_service = importlib.import_module('trading-bot.app.service.signals')
alert_router_service = importlib.import_module('alert-router.app.service.router')

# Get specific imports
SignalProcessor = trading_bot_service.SignalProcessor
route_alert = alert_router_service.route_alert
```

### 🔄 End-to-End Tests

```bash
make e2e
# Or: pytest -m e2e
```

## 🏗️ Code Organization

### 📦 SpreadPilot Core Library

The shared functionality package structure:

```
spreadpilot-core/
└── spreadpilot_core/
    ├── 📊 logging/          # Structured logging with OpenTelemetry
    ├── 💹 ibkr/             # Interactive Brokers async client
    ├── 🗄️ models/           # MongoDB data models
    │   ├── alert.py         # Alert event model
    │   ├── follower.py      # Follower account model
    │   ├── position.py      # Trading position model
    │   └── trade.py         # Trade execution model
    └── 🛠️ utils/            # Utility functions
        ├── email.py         # SendGrid email utilities
        ├── excel.py         # Excel report generation
        ├── pdf.py           # PDF report generation
        ├── telegram.py      # Telegram messaging
        └── time.py          # Time/date handling
```

### 🤖 Trading Bot Service

```
trading-bot/
└── app/
    ├── config.py            # Configuration management
    ├── main.py              # Entry point & API server
    ├── sheets.py            # Google Sheets integration
    └── service/             # Business logic
        ├── alerts.py        # Alert generation
        ├── base.py          # Base service class
        ├── ibkr.py          # IBKR integration
        ├── positions.py     # Position management
        └── signals.py       # Signal processing
```

### 🎛️ Admin API Service

```
admin-api/
├── main.py                  # Entry point
└── app/
    ├── core/                # Core modules
    │   └── config.py        # Configuration
    ├── api/v1/              # API version 1
    │   ├── api.py           # API router
    │   └── endpoints/       # API endpoints
    │       ├── dashboard.py # Dashboard endpoints
    │       └── followers.py # Follower management
    ├── db/                  # Database
    │   └── mongodb.py       # MongoDB client (Motor)
    ├── schemas/             # Pydantic schemas
    │   └── follower.py      # Follower schemas
    └── services/            # Business logic
        └── follower_service.py
```

### 🖥️ Frontend Structure

```
frontend/
└── src/
    ├── main.tsx             # Entry point
    ├── App.tsx              # Root component
    ├── components/          # UI components
    │   └── layout/          # Layout components
    ├── contexts/            # React contexts
    │   ├── AuthContext.tsx  # Authentication
    │   └── WebSocketContext.tsx
    ├── hooks/               # Custom hooks
    ├── pages/               # Page components
    │   ├── CommandsPage.tsx # Manual commands
    │   ├── FollowersPage.tsx
    │   ├── LoginPage.tsx
    │   └── LogsPage.tsx     # Log console
    ├── services/            # API services
    │   ├── followerService.ts
    │   └── logService.ts
    ├── types/               # TypeScript types
    └── utils/               # Utilities
```

## 🔄 Development Workflow

### 1️⃣ Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2️⃣ Make Changes & Test

```bash
# Run tests
make test

# Run linters
make lint
```

### 3️⃣ Format Code

```bash
make format
# Or: black . && isort .
```

### 4️⃣ Commit Changes

```bash
git add .
git commit -m "feat: add your feature description"
```

### 5️⃣ Push & Create PR

```bash
git push origin feature/your-feature-name
```

## 🐛 Debugging

### 🔍 Python Debugging

Using pdb:
```python
import pdb; pdb.set_trace()
```

### 🆚 VS Code Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Trading Bot",
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

### ⚛️ React Debugging

Install browser extensions:
- [React Developer Tools for Chrome](https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi)
- [React Developer Tools for Firefox](https://addons.mozilla.org/en-US/firefox/addon/react-devtools/)

## 🛠️ Common Tasks

### ➕ Adding Dependencies

**Python:**
```bash
echo "new-package==1.0.0" >> requirements-dev.in
make requirements-dev
pip install -r requirements-dev.txt
```

**Frontend:**
```bash
cd frontend
npm install --save new-package
```

### 🏗️ Creating New Components

**New Model:**
1. Create file in `spreadpilot-core/spreadpilot_core/models/`
2. Define Pydantic model
3. Export in `__init__.py`

**New API Endpoint:**
1. Create/update file in `admin-api/app/api/v1/endpoints/`
2. Define FastAPI endpoint
3. Add to router in `api.py`

**New Frontend Page:**
1. Create file in `frontend/src/pages/`
2. Define React component
3. Add route in `App.tsx`

**New Service:**
```bash
# Create structure
mkdir -p new-service/app/service
touch new-service/__init__.py
touch new-service/app/__init__.py
touch new-service/app/service/__init__.py

# Import pattern
import importlib
new_service = importlib.import_module('new-service.app.main')
```

## 🔧 Troubleshooting

### 🗄️ Database Issues

**PostgreSQL:**
```bash
cd infra/
./health-check.sh
docker-compose logs postgres
docker-compose restart postgres
docker-compose exec postgres psql -U spreadpilot -d spreadpilot
```

**MongoDB (Legacy):**
```bash
docker-compose logs mongo
docker-compose restart mongo
# Reset data (WARNING: DELETES ALL DATA)
docker-compose stop mongo
docker volume rm spreadpilot_mongo_data
docker-compose up -d mongo
```

### 💹 IB Gateway Issues

```bash
# Check logs
docker-compose logs ib-gateway

# Verify credentials in .env
# Check network connectivity
# Restart service
docker-compose restart ib-gateway
```

### 🖥️ Frontend Issues

```bash
cd frontend
# Clean install
rm -rf node_modules package-lock.json
npm install
# Clear cache
rm -rf node_modules/.vite
npm run dev
```

## ✨ Best Practices

### 📝 Code Style
- ✅ Follow PEP 8 for Python
- ✅ Use Black & isort for formatting
- ✅ Use ESLint & Prettier for JS/TS
- ✅ Add type hints to Python code

### 🧪 Testing
- ✅ Write unit tests for new features
- ✅ Use pytest fixtures
- ✅ Mock external dependencies
- ✅ Maintain >80% code coverage

### 📚 Documentation
- ✅ Add docstrings to functions/classes
- ✅ Update README files
- ✅ Document API endpoints
- ✅ Include usage examples

### ⚠️ Error Handling
- ✅ Use structured logging
- ✅ Handle exceptions gracefully
- ✅ Provide meaningful error messages
- ✅ Include error context

### ⚙️ Configuration
- ✅ Use environment variables
- ✅ Provide sensible defaults
- ✅ Validate at startup
- ✅ Document all settings

## 🎯 Quick Commands Reference

```bash
# Setup
make init-dev          # Initialize development environment

# Running
make up               # Start all services
make down             # Stop all services
make logs             # View logs

# Testing
make test             # Run tests
make test-coverage    # Run with coverage
make lint             # Run linters
make format           # Format code

# Building
make build-images     # Build Docker images
make requirements-dev # Update Python dependencies
```

## 📚 Additional Resources

- [System Architecture](./01-system-architecture.md)
- [Deployment Guide](./02-deployment-guide.md)
- [Operations Guide](./04-operations-guide.md)
- [API Documentation](./api/)
- [Contributing Guidelines](../CONTRIBUTING.md)

## 🔒 Security Development Practices

### 🛡️ Security-First Development

When developing for SpreadPilot, always follow these security practices:

#### 1. **Pre-commit Security Checks**

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run security checks manually
./trivy_scan.sh --severity HIGH,CRITICAL
./scripts/security-utils.py audit
```

#### 2. **PIN-Protected Endpoints**

When adding dangerous operations, ensure PIN protection:

```python
from app.core.security import verify_dangerous_operation

@router.delete("/followers/{follower_id}")
async def delete_follower(
    follower_id: str,
    _: None = Depends(verify_dangerous_operation)  # Requires PIN
):
    # Dangerous operation code
```

#### 3. **Security Headers**

Always include security headers in responses:

```python
from app.core.security import get_security_headers

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    headers = get_security_headers()
    for key, value in headers.items():
        response.headers[key] = value
    return response
```

#### 4. **Database Connections**

Always use TLS/SSL for database connections:

```python
# MongoDB with TLS
MONGO_URI = "mongodb://user:pass@host:port/db?tls=true&tlsCAFile=/certs/ca.pem"

# PostgreSQL with SSL
POSTGRES_URI = "postgresql://user:pass@host:port/db?sslmode=require"
```

#### 5. **Container Security**

Ensure all Dockerfiles run as non-root:

```dockerfile
# Create non-root user
RUN adduser -D -u 1000 appuser

# Switch to non-root user
USER appuser

# Add health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8080/health || exit 1
```

#### 6. **Secret Management**

Never hardcode secrets. Use environment variables or Secret Manager:

```python
import os
from app.core.config import get_settings

# Bad
API_KEY = "sk_live_abc123"  # NEVER DO THIS

# Good
API_KEY = os.environ.get("API_KEY")
# or
settings = get_settings()
API_KEY = settings.api_key
```

### 🔍 Security Testing

Include security tests in your development:

```python
# Test PIN verification
def test_pin_verification_required():
    response = client.delete("/api/v1/followers/123")
    assert response.status_code == 400
    assert "X-PIN header required" in response.json()["detail"]

# Test security headers
def test_security_headers():
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
```

## 🚦 CI/CD Integration

### 🔄 Continuous Integration

Every code change triggers automated checks through GitHub Actions:

#### 🎨 **Code Quality**
```bash
# Run locally before pushing
ruff check .                    # Linting
black --check .                  # Formatting
mypy . --ignore-missing-imports  # Type checking
```

#### 🧪 **Automated Testing**
```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# E2E tests
docker-compose -f docker-compose.e2e.yml up --exit-code-from e2e-tests
```

#### 🔒 **Security Scanning**
```bash
# Scan for vulnerabilities
trivy fs . --severity HIGH,CRITICAL

# Scan Docker images
trivy image spreadpilot/trading-bot:latest
```

### 📋 **Pre-Push Checklist**

Before pushing code:

1. **Format Code**: `make format`
2. **Run Linters**: `make lint`
3. **Run Tests**: `make test`
4. **Update Docs**: Update relevant documentation
5. **Commit Message**: Use conventional commits format

### 🏷️ **Branch Protection**

Main branches are protected with:

- ✅ Required status checks (CI must pass)
- ✅ Require branches to be up to date
- ✅ Require code owner reviews
- ✅ Dismiss stale reviews on new commits
- ✅ No force pushes allowed

### 🔄 **Pull Request Workflow**

1. **Create Feature Branch**: `git checkout -b feature/your-feature`
2. **Make Changes**: Implement feature with tests
3. **Push Branch**: `git push origin feature/your-feature`
4. **Open PR**: Use PR template
5. **CI Runs**: Automated checks execute
6. **Code Review**: Reviewers check code
7. **Merge**: Squash and merge when approved

### 📋 Security Checklist for PRs

Before submitting a PR, verify:

- [ ] No secrets or credentials in code
- [ ] Database connections use TLS/SSL
- [ ] Dangerous endpoints require PIN verification
- [ ] Containers run as non-root user
- [ ] Security headers are implemented
- [ ] No HIGH/CRITICAL vulnerabilities in dependencies
- [ ] Unit tests cover security features
- [ ] Documentation updated for security changes

### 🚨 Reporting Security Issues

If you discover a security vulnerability:

1. **DO NOT** create a public GitHub issue
2. Email security@spreadpilot.com with details
3. Include steps to reproduce if possible
4. Wait for confirmation before disclosure

For more security information, see [Security Checklist](../security_checklist.md).

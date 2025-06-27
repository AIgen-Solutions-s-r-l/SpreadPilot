# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Python Backend Services
- **Initialize development environment**: `make init-dev` (creates venv, installs dependencies)
- **Run tests**: `make test` or `pytest`
- **Run tests with coverage**: `make test-coverage`
- **Run linting**: `make lint` (flake8 + mypy)
- **Format code**: `make format` (black + isort)
- **Install all dependencies**: `make install-all`

### Frontend (React + TypeScript)
Navigate to `frontend/` directory:
- **Development server**: `npm run dev`
- **Build**: `npm run build`
- **Lint**: `npm run lint`

### Docker Operations
- **Start all services**: `make up` or `docker-compose up -d`
- **Stop services**: `make down`
- **View logs**: `make logs`
- **Build images**: `make build-images`

### Testing
- **Unit tests**: `pytest tests/unit/`
- **Integration tests**: `pytest tests/integration/`
- **E2E tests**: `make e2e` or `pytest -m e2e`

## Architecture Overview

SpreadPilot is a microservices-based copy-trading platform that executes QQQ options strategies from Google Sheets to Interactive Brokers accounts.

### Core Services
- **trading-bot/**: Main service that polls Google Sheets, executes trades via IBKR, manages positions
- **admin-api/**: FastAPI backend providing REST endpoints for follower management and real-time logs
- **frontend/**: React/TypeScript dashboard for monitoring and administration
- **watchdog/**: Service health monitoring and restart management
- **report-worker/**: Generates periodic P&L reports (PDF/Excel) and sends via email
- **alert-router/**: Manages alert delivery via Telegram and email

### Shared Components
- **spreadpilot-core/**: Shared Python library containing:
  - IBKR client wrapper
  - MongoDB models and database utilities
  - Logging configuration
  - Utility functions (email, Excel, PDF, secrets management)

### Key Data Models
- **Follower**: Represents a trading account that follows the master strategy
- **Position**: Current trading positions per follower
- **Trade**: Historical trade records
- **Alert**: System alerts and notifications

### Communication Patterns
- **REST APIs**: Service-to-service and client-to-service communication
- **WebSockets**: Real-time updates from admin-api to frontend
- **Pub/Sub**: Event-driven communication for alerts and reports (GCP)
- **MongoDB**: Primary data store for all persistent data

### Configuration Management
- Environment variables via `.env` files (see `deploy/.env.dev.template`)
- Google Cloud Secret Manager for production secrets
- Configuration classes in `*/app/config.py` files

### Testing Strategy
- **Unit tests**: Individual component testing in `tests/unit/`
- **Integration tests**: Multi-service interaction testing in `tests/integration/`
- **Test configuration**: `pytest.ini` in project root
- **Mocking**: Uses pytest fixtures for database and external service mocking

### Key Directories
- `docs/`: Comprehensive documentation including architecture diagrams
- `deploy/`: Deployment scripts and configuration templates
- `tests/`: All test files organized by type (unit/integration)
- Each service directory contains its own `README.md` with service-specific details

### Development Workflow
1. Use `make init-dev` to set up local environment
2. Start services with `make up`
3. Access admin dashboard at `http://localhost:8080`
4. Use `make format` before committing
5. Ensure `make test` and `make lint` pass before pushing

### Production Deployment
- Google Cloud Platform using Cloud Build and Cloud Run
- Containerized deployment via Docker
- Build configuration in `cloudbuild.yaml`
- Production secrets managed via GCP Secret Manager
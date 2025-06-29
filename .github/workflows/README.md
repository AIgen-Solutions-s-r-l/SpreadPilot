# CI/CD Pipeline Documentation

## Overview

This repository uses GitHub Actions for continuous integration and deployment. The main CI pipeline (`ci.yml`) runs on every pull request and push to the `main` and `develop` branches.

## CI Pipeline Components

### 1. Python Linting & Formatting (`python-lint`)
- **Tools**: Ruff (linting) and Black (formatting)
- **Purpose**: Ensures code quality and consistent formatting
- **Commands**:
  - `ruff check . --output-format=github`
  - `black --check --diff .`

### 2. Python Unit Tests (`python-tests`)
- **Tool**: Pytest with coverage
- **Services**: MongoDB and Redis (for testing)
- **Coverage**: Uploaded to Codecov and saved as artifacts
- **Command**: `pytest tests/unit/ -v --cov=. --cov-report=xml`

### 3. Frontend Tests & Build (`frontend-tests`)
- **Tools**: npm (lint, type-check, test, build)
- **Node Version**: 18
- **Commands**:
  - `npm run lint`
  - `npm run type-check`
  - `npm test -- --coverage --watchAll=false`
  - `npm run build`

### 4. End-to-End Tests (`e2e-tests`)
- **Tool**: Docker Compose with custom test runner
- **File**: `docker-compose.e2e.yml`
- **Components**: All services with mock IBKR gateway
- **Timeout**: 15 minutes

### 5. Security Scanning (`security-scan`)
- **Tool**: Trivy
- **Scan Types**: 
  - Repository scan (for vulnerabilities in code)
  - Docker image scan (for each service)
- **Output**: SARIF format for GitHub Security tab

### 6. Integration Tests (`integration-tests`)
- **Tool**: Pytest
- **Dependencies**: Requires unit tests to pass first
- **Command**: `pytest tests/integration/ -v --maxfail=5`

## Performance Optimizations

1. **Pip Package Caching**: All Python jobs cache pip packages
2. **Docker Layer Caching**: Docker builds use buildx cache
3. **Parallel Builds**: E2E test images are built in parallel
4. **NPM Caching**: Frontend dependencies are cached

## Failure Handling

- Docker logs are collected and uploaded as artifacts on E2E test failure
- Coverage reports are always uploaded, even on test failure
- Containers are cleaned up after E2E tests (even on failure)

## Required Secrets

- `CODECOV_TOKEN`: For uploading coverage reports to Codecov

## Running CI Locally

To run the same checks locally:

```bash
# Python linting
ruff check .
black --check .

# Python tests
pytest tests/unit/ -v --cov=.

# Frontend tests
cd frontend && npm run lint && npm test

# E2E tests
docker-compose -f docker-compose.e2e.yml up --abort-on-container-exit

# Security scan
trivy fs .
```
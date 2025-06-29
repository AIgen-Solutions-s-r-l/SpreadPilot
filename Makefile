# SpreadPilot Makefile

.PHONY: init-dev install-core install-all test lint format clean build-images up down logs

# Default Python interpreter
PYTHON := python3
# Default Docker Compose file
COMPOSE_FILE := docker-compose.yml
# Default Docker registry
DOCKER_REGISTRY := gcr.io/spreadpilot

# Initialize development environment
init-dev:
	@echo "Initializing development environment..."
	$(PYTHON) -m venv venv
	. venv/bin/activate && \
	pip install --upgrade pip && \
	pip install -r requirements-dev.txt && \
	pip install -e ./spreadpilot-core
	@echo "Development environment initialized. Activate with: source venv/bin/activate"

# Install core library
install-core:
	@echo "Installing spreadpilot-core..."
	pip install -e ./spreadpilot-core

# Install all dependencies
install-all: install-core
	@echo "Installing all dependencies..."
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# Run tests
test:
	@echo "Running tests..."
	pytest

# Run tests with coverage
test-coverage:
	@echo "Running tests with coverage..."
	pytest --cov=spreadpilot_core --cov=trading-bot --cov=watchdog --cov=admin-api --cov=report-worker --cov=alert-router

# Run linting
lint:
	@echo "Running linters..."
	flake8 spreadpilot-core trading-bot watchdog admin-api report-worker alert-router
	mypy spreadpilot-core trading-bot watchdog admin-api report-worker alert-router

# Format code
format:
	@echo "Formatting code..."
	black spreadpilot-core trading-bot watchdog admin-api report-worker alert-router
	isort spreadpilot-core trading-bot watchdog admin-api report-worker alert-router

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage htmlcov/
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete

# Build Docker images
build-images:
	@echo "Building Docker images..."
	docker build -t $(DOCKER_REGISTRY)/trading-bot:latest -f trading-bot/Dockerfile .
	docker build -t $(DOCKER_REGISTRY)/watchdog:latest -f watchdog/Dockerfile .
	docker build -t $(DOCKER_REGISTRY)/admin-api:latest -f admin-api/Dockerfile .
	docker build -t $(DOCKER_REGISTRY)/report-worker:latest -f report-worker/Dockerfile .
	docker build -t $(DOCKER_REGISTRY)/alert-router:latest -f alert-router/Dockerfile .
	docker build -t $(DOCKER_REGISTRY)/frontend:latest -f frontend/Dockerfile .

# Start services with Docker Compose
up:
	@echo "Starting services..."
	docker-compose -f $(COMPOSE_FILE) up -d

# Stop services
down:
	@echo "Stopping services..."
	docker-compose -f $(COMPOSE_FILE) down

# View logs
logs:
	@echo "Viewing logs..."
	docker-compose -f $(COMPOSE_FILE) logs -f

# Run e2e tests
e2e:
	@echo "Starting E2E test environment..."
	docker-compose -f docker-compose.e2e.yml up -d
	@echo "Waiting for services to be ready..."
	sleep 30
	@echo "Running e2e tests..."
	pytest -m e2e tests/e2e/e2e_test.py -v
	@echo "E2E tests completed. View emails at http://localhost:8025"

# Clean up e2e test environment
e2e-clean:
	@echo "Cleaning up E2E test environment..."
	docker-compose -f docker-compose.e2e.yml down -v

# Generate requirements.txt from setup.py
requirements:
	@echo "Generating requirements.txt..."
	pip-compile --output-file=requirements.txt spreadpilot-core/setup.py

# Generate requirements-dev.txt
requirements-dev:
	@echo "Generating requirements-dev.txt..."
	pip-compile --output-file=requirements-dev.txt requirements-dev.in

# Deploy to dev environment
deploy-dev:
	@echo "Deploying to dev environment..."
	gcloud builds submit --config=cloudbuild-dev.yaml .

# Deploy to prod environment
deploy-prod:
	@echo "Deploying to prod environment..."
	gcloud builds submit --config=cloudbuild-prod.yaml .

# Help
help:
	@echo "SpreadPilot Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  init-dev         Initialize development environment"
	@echo "  install-core     Install core library"
	@echo "  install-all      Install all dependencies"
	@echo "  test             Run tests"
	@echo "  test-coverage    Run tests with coverage"
	@echo "  lint             Run linters"
	@echo "  format           Format code"
	@echo "  clean            Clean build artifacts"
	@echo "  build-images     Build Docker images"
	@echo "  up               Start services with Docker Compose"
	@echo "  down             Stop services"
	@echo "  logs             View logs"
	@echo "  e2e              Run e2e tests"
	@echo "  e2e-clean        Clean up e2e test environment"
	@echo "  requirements     Generate requirements.txt"
	@echo "  requirements-dev Generate requirements-dev.txt"
	@echo "  deploy-dev       Deploy to dev environment"
	@echo "  deploy-prod      Deploy to prod environment"
	@echo "  help             Show this help message"
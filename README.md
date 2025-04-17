# SpreadPilot

SpreadPilot is a copy-trading platform for QQQ options strategies, designed to automatically replicate a Google Sheets algorithm strategy to Interactive Brokers (IBKR) accounts.

## Overview

SpreadPilot enables followers to automatically execute the Vertical Spread QQQ 0-DTE strategy on their IBKR accounts. The platform includes:

- Automated trading based on signals from a Google Sheets algorithm
- Assignment detection and compensation
- P&L tracking and reporting
- Administrative dashboard for monitoring and management
- Alerting via Telegram and email

## Architecture

SpreadPilot is built as a set of microservices deployed on Google Cloud Platform:

- **trading-bot**: Connects to IBKR, polls Google Sheets, executes orders, and manages assignments
- **watchdog**: Monitors the trading bot and IB Gateway, restarts them if needed
- **admin-api**: Provides REST and WebSocket APIs for the admin dashboard
- **report-worker**: Generates monthly PDF and Excel reports
- **alert-router**: Routes alerts to Telegram and email
- **frontend**: React-based admin dashboard

All services share a common library (`spreadpilot-core`) for logging, IBKR client, Firestore models, and utilities.

### Technology Stack

- **Backend**: Python 3.11 with asyncio/aiohttp
- **Frontend**: React 18 + Vite + Tailwind CSS
- **Database**: Firestore (Native mode)
- **Secrets**: GCP Secret Manager
- **Logging**: GCP Cloud Logging
- **Monitoring**: OpenTelemetry + Cloud Monitoring
- **Containerization**: Docker + Cloud Run
- **CI/CD**: Cloud Build

## Setup

### Prerequisites

- Python 3.11
- Node.js 18+
- Docker and Docker Compose
- Google Cloud SDK
- Interactive Brokers account and IB Gateway

### Local Development Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/spreadpilot.git
cd spreadpilot
```

2. Initialize the development environment:

```bash
make init-dev
```

3. Create a `.env` file with the required environment variables:

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
```

4. Start the services:

```bash
make up
```

5. Access the admin dashboard at http://localhost:8080

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-coverage

# Run e2e tests
make e2e
```

## Development Workflow

1. Create a feature branch:

```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and run tests:

```bash
make test
make lint
```

3. Format your code:

```bash
make format
```

4. Submit a pull request

## Deployment

### Development Environment

```bash
make deploy-dev
```

### Production Environment

```bash
make deploy-prod
```

## Project Structure

```
spreadpilot/
├── spreadpilot-core/         # Core library
│   └── spreadpilot_core/
│       ├── logging/          # Structured logging
│       ├── ibkr/             # IBKR client wrapper
│       ├── models/           # Firestore models
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

## License

Proprietary - All rights reserved

## Contact

For any questions or support, please contact capital@tradeautomation.it
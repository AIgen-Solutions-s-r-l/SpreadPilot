# SpreadPilot Report Worker

This service is responsible for generating and sending monthly reports to followers, as well as calculating daily P&L.

## Features

- Receives job requests via Google Cloud Pub/Sub
- Calculates daily P&L using PostgreSQL data
- Generates monthly reports for followers (PDF and Excel formats)
- Stores reports in Google Cloud Storage
- Generates signed URLs for secure report access
- Integrates commission calculation with P&L data
- Includes IBAN information for payment processing
- Sends reports via email
- Securely loads secrets from MongoDB
- Provides health check endpoint

## Setup

### Prerequisites

- Python 3.11+
- MongoDB (for data storage and secret management)
- PostgreSQL (for P&L and commission data)
- Google Cloud Storage (for report file storage)
- Google Cloud Pub/Sub subscription
- SMTP server for sending emails

### Environment Variables

Create a `.env` file with the following variables:

```
# Core Settings
GCP_PROJECT_ID=spreadpilot-test
MONGO_URI=mongodb://user:password@localhost:27017
MONGO_DB_NAME=spreadpilot_admin
MONGO_DB_NAME_SECRETS=spreadpilot_secrets

# Report Settings
DEFAULT_COMMISSION_PERCENTAGE=20.0
REPORT_SENDER_EMAIL=capital@tradeautomation.it
ADMIN_EMAIL=admin@example.com

# Timing Settings
MARKET_CLOSE_TIMEZONE=America/New_York
MARKET_CLOSE_HOUR=16
MARKET_CLOSE_MINUTE=10

# Email Settings
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user
SMTP_PASSWORD=password
SMTP_TLS=true

# GCS Settings (for report file storage)
GCS_BUCKET_NAME=spreadpilot-reports
GCS_SERVICE_ACCOUNT_KEY_PATH=/path/to/service-account.json

# PostgreSQL Settings (for P&L data)
POSTGRES_URI=postgresql+asyncpg://user:password@localhost:5432/spreadpilot_pnl

# Logging
LOG_LEVEL=INFO

# Environment
APP_ENV=development
```

### Running Locally

1. Install dependencies:

```bash
pip install -e ./spreadpilot-core
pip install -r requirements.txt
```

2. Run the service:

```bash
python app/main.py
```

### Running with Docker

Build and run the Docker image:

```bash
docker build -t spreadpilot-report-worker .
docker run -p 8084:8084 --env-file .env spreadpilot-report-worker
```

## API Endpoints

- `POST /`: Receives Pub/Sub push messages
- `GET /health`: Health check endpoint

## Job Types

The service supports two types of jobs:

1. **Daily P&L Calculation** (`job_type: "daily"`): Calculates and stores daily P&L for the current date.
2. **Monthly Report Generation** (`job_type: "monthly"`): Generates and sends monthly reports for all active followers for the previous month, including:
   - Daily P&L table for the month
   - Total P&L and commission calculations  
   - PDF and Excel report formats
   - GCS storage with signed URL access
   - IBAN information for payment processing

## Development

To run tests:

```bash
pytest
# SpreadPilot Alert Router

This service is responsible for routing alerts from the SpreadPilot trading system to various notification channels (Telegram, Email).

## Features

- Receives alerts via Google Cloud Pub/Sub
- Routes alerts to configured notification channels:
  - Telegram
  - Email
- Generates deep links to the dashboard for easy access
- Securely loads secrets from MongoDB
- Provides health check endpoint

## Setup

### Prerequisites

- Python 3.11+
- MongoDB (for secret storage)
- Google Cloud Pub/Sub subscription
- Telegram Bot (optional)
- SMTP server (optional)

### Environment Variables

Create a `.env` file with the following variables:

```
# General Settings
GCP_PROJECT_ID=spreadpilot-test
DASHBOARD_BASE_URL=http://localhost:3000

# Telegram Settings
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ADMIN_IDS=id1,id2,id3

# Email Settings
EMAIL_SENDER=alerts@example.com
EMAIL_ADMIN_RECIPIENTS=admin1@example.com,admin2@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user
SMTP_PASSWORD=password
SMTP_TLS=true

# MongoDB Settings
MONGO_URI=mongodb://user:password@localhost:27017
MONGO_DB_NAME=spreadpilot_admin
MONGO_DB_NAME_SECRETS=spreadpilot_secrets
```

### Running Locally

1. Install dependencies:

```bash
pip install -e ./spreadpilot-core
pip install -r requirements.txt
```

2. Run the service:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Running with Docker

Build and run the Docker image:

```bash
docker build -t spreadpilot-alert-router .
docker run -p 8080:8080 --env-file .env spreadpilot-alert-router
```

## API Endpoints

- `POST /`: Receives Pub/Sub push messages
- `GET /health`: Health check endpoint

## Alert Format

Alerts are expected to be in the following format (after base64 decoding):

```json
{
  "event_type": "COMPONENT_DOWN",
  "timestamp": "2025-05-18T12:34:56.789Z",
  "message": "Trading bot is down",
  "params": {
    "component_name": "trading-bot",
    "duration_seconds": 300
  }
}
```

## Development

To run tests:

```bash
pytest
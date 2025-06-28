# SpreadPilot Alert Router

This service is responsible for routing alerts from the SpreadPilot trading system to various notification channels (Telegram, Email).

## Features

- Receives alerts via Google Cloud Pub/Sub
- Routes alerts to configured notification channels:
  - Telegram (primary channel with Markdown formatting)
  - Email (automatic fallback if Telegram fails)
- Implements intelligent retry logic with fallback strategy
- Generates deep links to the dashboard for easy access
- Formats messages with rich content (emojis, formatting, structured data)
- Concurrent message delivery for multiple recipients
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

## Alert Routing Strategy

The Alert Router implements a smart notification strategy:

1. **Primary Channel (Telegram)**:
   - Attempts to send to all configured Telegram admin IDs
   - Uses Markdown formatting for rich message display
   - Includes deep links for quick dashboard access
   - If at least one Telegram message succeeds, email is not used

2. **Fallback Channel (Email)**:
   - Automatically activated if ALL Telegram attempts fail
   - Sends HTML-formatted emails with styled content
   - Includes the same information as Telegram messages
   - Ensures alerts are never lost due to single channel failure

## Development

### Running Tests

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

Run specific test file:
```bash
pytest tests/unit/service/test_alert_router.py
```

### Testing with httpx

The alert router uses httpx for async HTTP requests. Tests use httpx mocking:

```python
# Example test with mocked Telegram API
mock_response = Mock(spec=Response)
mock_response.status_code = 200
mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}

mock_client = AsyncMock()
mock_client.post.return_value = mock_response
alert_router._http_client = mock_client
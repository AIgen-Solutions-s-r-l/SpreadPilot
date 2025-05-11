# Trading Bot Setup Guide for SpreadPilot

This document provides detailed instructions for setting up the Trading Bot for the SpreadPilot system. It covers the configuration, startup, verification, and troubleshooting steps.

## Prerequisites

- Docker and Docker Compose installed on your system
- MongoDB service set up and running (see [MongoDB Setup Guide](./0-mongodb.md))
- IB Gateway service set up and running (see [IB Gateway Setup Guide](./1-ib-gateway.md))
- Google Sheets API key (for accessing trading signals)
- Google Sheet URL containing trading signals
- Basic understanding of trading concepts and Interactive Brokers

## 1. Understanding the Trading Bot

The Trading Bot is the core service of the SpreadPilot system. It is responsible for:

1. Connecting to Interactive Brokers via the IB Gateway
2. Polling Google Sheets for trading signals
3. Executing orders based on those signals
4. Monitoring positions for assignments
5. Calculating profit and loss (P&L)
6. Generating alerts for important events

The Trading Bot is implemented as a FastAPI application that runs in a Docker container. It uses the `spreadpilot-core` library for common functionality such as database access, logging, and utilities.

## 2. Trading Bot Configuration in docker-compose.yml

The SpreadPilot system uses a containerized version of the Trading Bot, configured in the `docker-compose.yml` file. Here's the relevant section:

```yaml
trading-bot:
  build:
    context: .
    dockerfile: trading-bot/Dockerfile
  container_name: spreadpilot-trading-bot
  environment:
    - GOOGLE_CLOUD_PROJECT=spreadpilot-dev
    - FIRESTORE_EMULATOR_HOST=firestore:8080
    - IB_GATEWAY_HOST=ib-gateway
    - IB_GATEWAY_PORT=4002
    - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
    - SENDGRID_API_KEY=${SENDGRID_API_KEY}
    - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
    - GOOGLE_SHEET_URL=${GOOGLE_SHEET_URL}
    - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json
  volumes:
    - ./credentials:/app/credentials
  depends_on:
    - mongodb
    - ib-gateway
  ports:
    - "8081:8080"
  restart: unless-stopped
```

This configuration:
- Builds the Trading Bot from the Dockerfile in the `trading-bot` directory
- Names the container `spreadpilot-trading-bot`
- Sets environment variables for various services and APIs
- Mounts the `credentials` directory for Google API authentication
- Specifies dependencies on MongoDB and IB Gateway
- Exposes port 8081 on the host, mapping to port 8080 in the container
- Configures automatic restart unless explicitly stopped

## 3. Environment Variables Setup

The Trading Bot requires several environment variables to be set in the `.env` file at the project root. Here are the key variables:

```
# Google Sheets (Required for trading signals)
GOOGLE_SHEET_URL=your_google_sheet_url
GOOGLE_SHEETS_API_KEY=your_google_sheets_api_key

# Interactive Brokers (Already set up for IB Gateway)
IB_USERNAME=your_ib_username
IB_PASSWORD=your_ib_password

# Notifications (Optional but recommended)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
SENDGRID_API_KEY=your_sendgrid_api_key
ADMIN_EMAIL=your_admin_email

# Trading Parameters (Optional - defaults shown)
MIN_PRICE=0.70
PRICE_INCREMENT=0.01
MAX_ATTEMPTS=10
TIMEOUT_SECONDS=5
POLLING_INTERVAL_SECONDS=1.0
POSITION_CHECK_INTERVAL_SECONDS=60.0
```

Replace the placeholder values with your actual credentials and settings.

**Important Notes:**
- The `GOOGLE_SHEET_URL` is required and should point to a Google Sheet containing trading signals
- The `GOOGLE_SHEETS_API_KEY` is required for accessing the Google Sheets API
- The IB Gateway credentials (`IB_USERNAME` and `IB_PASSWORD`) should already be set up from the IB Gateway setup
- Notification settings are optional but highly recommended for monitoring trading activity
- Trading parameters can be adjusted based on your specific trading strategy and risk tolerance

## 4. Google Sheets Setup

The Trading Bot polls a Google Sheet for trading signals. The sheet should be structured with the following columns:

1. Strategy name
2. Quantity per leg
3. Strike price for long option
4. Strike price for short option

You'll need to:
1. Create a Google Sheet with the appropriate structure
2. Make the sheet publicly accessible or share it with the service account
3. Get the sheet URL and add it to the `.env` file as `GOOGLE_SHEET_URL`
4. Create a Google Sheets API key and add it to the `.env` file as `GOOGLE_SHEETS_API_KEY`

## 5. Starting the Trading Bot

To start the Trading Bot container:

```bash
docker-compose up -d trading-bot
```

This command:
- Starts the Trading Bot in detached mode (`-d`)
- Uses the configuration from `docker-compose.yml`
- Creates and initializes the Trading Bot container with the environment variables from `.env`
- Automatically starts the required dependencies (MongoDB and IB Gateway) if they're not already running

## 6. Verifying the Trading Bot is Running

Check if the Trading Bot container is running with:

```bash
docker ps | grep trading-bot
```

You should see output similar to:

```
CONTAINER ID   IMAGE                    COMMAND                  CREATED          STATUS          PORTS                    NAMES
abcdef123456   spreadpilot-trading-bot  "uvicorn app.main:ap…"   5 minutes ago    Up 5 minutes    0.0.0.0:8081->8080/tcp   spreadpilot-trading-bot
```

## 7. Checking Trading Bot Logs

To verify that the Trading Bot is properly connecting to Interactive Brokers and Google Sheets:

```bash
docker logs spreadpilot-trading-bot
```

Look for messages indicating successful connections:
- "Trading bot started"
- "Connected to IB Gateway"
- "Connected to Google Sheets"
- "Loaded active followers"

## 8. Testing the Trading Bot API

The Trading Bot exposes several API endpoints that you can use to check its status and trigger actions:

### Health Check

```bash
curl http://localhost:8081/health
```

Expected response if healthy:
```json
{"status": "healthy"}
```

### Status Check

```bash
curl http://localhost:8081/status
```

Expected response:
```json
{
  "status": "running",
  "ibkr_connected": true,
  "sheets_connected": true,
  "active_followers": 3
}
```

### Manual Signal Processing (for testing)

```bash
curl -X POST http://localhost:8081/trade/signal \
  -H "Content-Type: application/json" \
  -d '{"strategy": "test", "qty_per_leg": 1, "strike_long": 100, "strike_short": 105}'
```

This will trigger the Trading Bot to process a signal manually, which is useful for testing.

## 9. Troubleshooting

### Connection Issues with IB Gateway

If the Trading Bot fails to connect to the IB Gateway:

1. Verify that the IB Gateway container is running: `docker ps | grep ib-gateway`
2. Check the IB Gateway logs for authentication issues: `docker logs spreadpilot-ib-gateway`
3. Ensure the `IB_GATEWAY_HOST` and `IB_GATEWAY_PORT` environment variables are set correctly
4. Verify that the IB Gateway is properly authenticated with Interactive Brokers

### Google Sheets Connection Issues

If the Trading Bot fails to connect to Google Sheets:

1. Verify that the `GOOGLE_SHEET_URL` and `GOOGLE_SHEETS_API_KEY` environment variables are set correctly
2. Check that the Google Sheet is accessible (try opening it in a browser)
3. Verify that the Google Sheets API key has the necessary permissions
4. Check the Trading Bot logs for specific error messages related to Google Sheets

### MongoDB Connection Issues

If the Trading Bot fails to connect to MongoDB:

1. Verify that the MongoDB container is running: `docker ps | grep mongodb`
2. Check that the MongoDB credentials are correct
3. Ensure that the MongoDB database and collections are properly set up
4. Check the Trading Bot logs for specific error messages related to MongoDB

### Container Startup Issues

If the Trading Bot container fails to start:

1. Check Docker logs: `docker logs spreadpilot-trading-bot`
2. Verify that all required environment variables are set in the `.env` file
3. Ensure that the dependencies (MongoDB and IB Gateway) are running
4. Check system resources (CPU, memory, disk space)

## 10. Security Considerations

For production environments:

1. Use strong, unique API keys and credentials
2. Implement proper secrets management for all credentials
3. Restrict access to the Trading Bot API (e.g., using a reverse proxy with authentication)
4. Consider network isolation for the Trading Bot container
5. Implement monitoring and alerting for the Trading Bot status
6. Regularly audit trading activities and permissions
7. Use paper trading mode for testing before switching to live trading

## 11. Next Steps

After setting up the Trading Bot, you can proceed to configure the Admin API, which provides an administrative interface for managing followers and monitoring the system.

The Admin API will interact with the Trading Bot to:
- Manage followers (users/accounts that replicate trades)
- Monitor trading activity
- Trigger manual commands (e.g., closing positions)
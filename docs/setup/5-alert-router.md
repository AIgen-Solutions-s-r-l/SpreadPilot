# 🚨 Alert Router Setup Guide for SpreadPilot

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [1. Understanding Alert Router](#1-understanding-the-alert-router)
- [2. Docker Configuration](#2-alert-router-configuration-in-docker-composeyml)
- [3. Environment Variables](#3-environment-variables-setup)
- [4. Starting the Service](#4-starting-the-alert-router)
- [5. Health Verification](#5-verifying-the-alert-router-is-running)
- [6. Logs & Monitoring](#6-checking-alert-router-logs)
- [7. Testing](#7-testing-the-alert-router)
- [8. Troubleshooting](#8-troubleshooting)
- [9. Security](#9-security-considerations)
- [10. Next Steps](#10-next-steps)

## 📖 Overview

This document provides detailed instructions for setting up the Alert Router for the SpreadPilot system. It covers the configuration, startup, verification, and troubleshooting steps.

## ✅ Prerequisites

- Docker and Docker Compose installed on your system
- MongoDB service set up and running (see [MongoDB Setup Guide](./0-mongodb.md))
- Google Cloud Pub/Sub subscription configured
- Telegram Bot created (optional, for Telegram notifications)
- SMTP server access (optional, for email notifications)
- Basic understanding of event-driven architectures

## 1. 🎯 Understanding the Alert Router

The Alert Router is a service that manages the delivery of critical notifications from the SpreadPilot trading system.

### 🔧 Core Responsibilities

1. Receiving alert events via Google Cloud Pub/Sub
2. Routing alerts to appropriate channels (Telegram, email)
3. Formatting messages with deep links to the dashboard
4. Securely loading secrets from MongoDB
5. Providing health check endpoints

### 🏗️ Architecture

The Alert Router is implemented as a FastAPI application that runs in a Docker container. It communicates with MongoDB for secret management and with external services (Telegram, SMTP) for sending notifications.

> 📝 **Consolidation Note**: The Alert Router has been consolidated from two different implementations (`alert_router/` and `alert-router/`) into a single, unified version in `alert-router/`. This consolidation improves maintainability, reduces duplication, and provides a consistent API implementation with the best features from both previous versions.

## 2. 🐳 Alert Router Configuration in docker-compose.yml

The SpreadPilot system uses a containerized version of the Alert Router, configured in the `docker-compose.yml` file. Here's the relevant section:

```yaml
alert-router:
  build:
    context: .
    dockerfile: alert-router/Dockerfile
  container_name: spreadpilot-alert-router
  environment:
    - GOOGLE_CLOUD_PROJECT=spreadpilot-dev
    - MONGO_URI=mongodb://mongodb:27017
    - MONGO_DB_NAME=spreadpilot_admin_test
    - MONGO_DB_NAME_SECRETS=spreadpilot_secrets
    - DASHBOARD_BASE_URL=http://localhost:3000
    - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    - TELEGRAM_ADMIN_IDS=${TELEGRAM_ADMIN_IDS}
    - EMAIL_SENDER=${EMAIL_SENDER}
    - EMAIL_ADMIN_RECIPIENTS=${EMAIL_ADMIN_RECIPIENTS}
    - SMTP_HOST=${SMTP_HOST}
    - SMTP_PORT=${SMTP_PORT:-587}
    - SMTP_USER=${SMTP_USER}
    - SMTP_PASSWORD=${SMTP_PASSWORD}
    - SMTP_TLS=${SMTP_TLS:-true}
    - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
    - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json
  volumes:
    - ./credentials:/app/credentials
  depends_on:
    - mongodb
  ports:
    - "8082:8080"
  restart: unless-stopped
```

This configuration:
- Builds the Alert Router from the Dockerfile in the `alert-router` directory
- Names the container `spreadpilot-alert-router`
- Sets environment variables for various services and APIs
- Mounts the `credentials` directory for Google API authentication
- Specifies dependencies on MongoDB
- Exposes port 8082 on the host, mapping to port 8080 in the container
- Configures automatic restart unless explicitly stopped

## 3. 🔐 Environment Variables Setup

The Alert Router requires several environment variables to be set in the `.env` file at the project root. Here are the key variables:

```
# Google Cloud
GOOGLE_CLOUD_PROJECT=spreadpilot-dev

# MongoDB
MONGO_URI=mongodb://mongodb:27017
MONGO_DB_NAME=spreadpilot_admin_test
MONGO_DB_NAME_SECRETS=spreadpilot_secrets

# Dashboard
DASHBOARD_BASE_URL=http://localhost:3000

# Telegram Settings
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ADMIN_IDS=id1,id2,id3

# Email Settings
EMAIL_SENDER=alerts@example.com
EMAIL_ADMIN_RECIPIENTS=admin1@example.com,admin2@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_TLS=true
```

Replace the placeholder values with your actual credentials and settings.

### ⚠️ Important Notes
- The `TELEGRAM_BOT_TOKEN` is the token for your Telegram bot (obtained from BotFather)
- The `TELEGRAM_ADMIN_IDS` is a comma-separated list of Telegram user IDs to receive alerts
- The `EMAIL_SENDER` is the email address from which alerts will be sent
- The `EMAIL_ADMIN_RECIPIENTS` is a comma-separated list of email addresses to receive alerts
- The SMTP settings are required for sending email alerts
- For production environments, you should use strong, unique values for all these variables

## 4. 🚀 Starting the Alert Router

To start the Alert Router container:

```bash
docker-compose up -d alert-router
```

This command:
- Starts the Alert Router in detached mode (`-d`)
- Uses the configuration from `docker-compose.yml`
- Creates and initializes the Alert Router container with the environment variables from `.env`
- Automatically starts the required dependencies (MongoDB) if they're not already running

## 5. ✔️ Verifying the Alert Router is Running

Check if the Alert Router container is running with:

```bash
docker ps | grep alert-router
```

You should see output similar to:

```
CONTAINER ID   IMAGE                    COMMAND                  CREATED          STATUS          PORTS                    NAMES
abcdef123456   spreadpilot-alert-router "uvicorn app.main:a..."  5 minutes ago    Up 5 minutes    0.0.0.0:8082->8080/tcp   spreadpilot-alert-router
```

## 6. 📊 Checking Alert Router Logs

To verify that the Alert Router is properly connecting to MongoDB and loading secrets:

```bash
docker logs spreadpilot-alert-router
```

### 🟢 Success Indicators
- "Alert Router service starting..."
- "Connected to MongoDB database"
- "Successfully loaded secret"

## 7. 🧪 Testing the Alert Router

### 💚 Basic Health Check

The Alert Router exposes a health check endpoint that you can use to test its functionality:

```bash
curl http://localhost:8082/health
```

Expected response:
```json
{"status": "healthy"}
```

### 📨 Full Functionality Test

To test the full functionality, you would need to publish a message to the Pub/Sub topic that the Alert Router is subscribed to. This can be done using the Google Cloud Console or the `gcloud` command-line tool:

```bash
gcloud pubsub topics publish spreadpilot-alerts --message='{"event_type":"COMPONENT_DOWN","timestamp":"2025-05-18T12:34:56.789Z","message":"Test alert","params":{"component_name":"test"}}'
```

If configured correctly, you should receive a notification via Telegram and/or email.

## 8. 🔧 Troubleshooting

### ☁️ Pub/Sub Connection Issues

If the Alert Router fails to receive messages from Pub/Sub:

1. Verify that the Google Cloud credentials are correctly set up
2. Check that the Pub/Sub subscription is properly configured
3. Ensure that the `GOOGLE_CLOUD_PROJECT` environment variable is set correctly
4. Check the Alert Router logs for specific error messages related to Pub/Sub

### 🗄️ MongoDB Connection Issues

If the Alert Router fails to connect to MongoDB:

1. Verify that the MongoDB container is running: `docker ps | grep mongodb`
2. Check that the MongoDB credentials are correct
3. Ensure that the `MONGO_URI` and `MONGO_DB_NAME` environment variables are set correctly
4. Check the Alert Router logs for specific error messages related to MongoDB

### 📧 Notification Channel Issues

If alerts are not being sent to Telegram or email:

1. Verify that the Telegram bot token is correct
2. Check that the Telegram admin IDs are correct
3. Ensure that the SMTP settings are correct
4. Check the Alert Router logs for specific error messages related to Telegram or SMTP

### 🐳 Container Startup Issues

If the Alert Router container fails to start:

1. Check Docker logs: `docker logs spreadpilot-alert-router`
2. Verify that all required environment variables are set in the `.env` file
3. Ensure that the dependencies (MongoDB) are running
4. Check system resources (CPU, memory, disk space)

## 9. 🔒 Security Considerations

For production environments:

1. Use strong, unique passwords and tokens
2. Implement proper secrets management for all credentials
3. Consider using HTTPS for the Alert Router (e.g., using a reverse proxy)
4. Restrict access to the Alert Router to authorized services only
5. Regularly audit access logs and alert activities
6. Ensure that sensitive information is not included in alert messages

## 10. ⏭️ Next Steps

After setting up the Alert Router, you can proceed to configure the Report Worker, which generates periodic reports for followers.

### 🔗 Service Integration

The Alert Router will work in conjunction with other services to:
- Receive alerts from the Trading Bot and other services
- Route alerts to appropriate channels
- Provide timely notifications of critical events
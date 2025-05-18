# Report Worker Setup Guide for SpreadPilot

This document provides detailed instructions for setting up the Report Worker for the SpreadPilot system. It covers the configuration, startup, verification, and troubleshooting steps.

## Prerequisites

- Docker and Docker Compose installed on your system
- MongoDB service set up and running (see [MongoDB Setup Guide](./0-mongodb.md))
- Google Cloud Pub/Sub subscription configured
- SMTP server access for sending reports via email
- Basic understanding of event-driven architectures

## 1. Understanding the Report Worker

The Report Worker is a service that generates periodic reports for followers of the SpreadPilot trading system. Its primary responsibilities include:

1. Calculating daily and monthly P&L
2. Generating PDF and Excel reports
3. Emailing reports to followers
4. Receiving job requests via Google Cloud Pub/Sub
5. Securely loading secrets from MongoDB

The Report Worker is implemented as a Flask application that runs in a Docker container. It communicates with MongoDB for data storage and secret management, and with external services (SMTP) for sending reports.

> **Note on Consolidation:** The Report Worker has been consolidated from two different implementations (`report_worker/` and `report-worker/`) into a single, unified version in `report-worker/`. This consolidation improves maintainability, reduces duplication, and provides a consistent API implementation with the best features from both previous versions.

## 2. Report Worker Configuration in docker-compose.yml

The SpreadPilot system uses a containerized version of the Report Worker, configured in the `docker-compose.yml` file. Here's the relevant section:

```yaml
report-worker:
  build:
    context: .
    dockerfile: report-worker/Dockerfile
  container_name: spreadpilot-report-worker
  environment:
    - GOOGLE_CLOUD_PROJECT=spreadpilot-dev
    - MONGO_URI=mongodb://mongodb:27017
    - MONGO_DB_NAME=spreadpilot_admin_test
    - MONGO_DB_NAME_SECRETS=spreadpilot_secrets
    - DEFAULT_COMMISSION_PERCENTAGE=20.0
    - REPORT_SENDER_EMAIL=${REPORT_SENDER_EMAIL}
    - ADMIN_EMAIL=${ADMIN_EMAIL}
    - MARKET_CLOSE_TIMEZONE=America/New_York
    - MARKET_CLOSE_HOUR=16
    - MARKET_CLOSE_MINUTE=10
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
    - "8084:8084"
  restart: unless-stopped
```

This configuration:
- Builds the Report Worker from the Dockerfile in the `report-worker` directory
- Names the container `spreadpilot-report-worker`
- Sets environment variables for various services and APIs
- Mounts the `credentials` directory for Google API authentication
- Specifies dependencies on MongoDB
- Exposes port 8084 on the host, mapping to port 8084 in the container
- Configures automatic restart unless explicitly stopped

## 3. Environment Variables Setup

The Report Worker requires several environment variables to be set in the `.env` file at the project root. Here are the key variables:

```
# Google Cloud
GOOGLE_CLOUD_PROJECT=spreadpilot-dev

# MongoDB
MONGO_URI=mongodb://mongodb:27017
MONGO_DB_NAME=spreadpilot_admin_test
MONGO_DB_NAME_SECRETS=spreadpilot_secrets

# Report Settings
DEFAULT_COMMISSION_PERCENTAGE=20.0
REPORT_SENDER_EMAIL=reports@example.com
ADMIN_EMAIL=admin@example.com

# Timing Settings
MARKET_CLOSE_TIMEZONE=America/New_York
MARKET_CLOSE_HOUR=16
MARKET_CLOSE_MINUTE=10

# Email Settings
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_TLS=true

# Logging
LOG_LEVEL=INFO

# Environment
APP_ENV=development
PORT=8084
```

Replace the placeholder values with your actual credentials and settings.

**Important Notes:**
- The `DEFAULT_COMMISSION_PERCENTAGE` is the default commission percentage to use if a follower doesn't have a specific percentage set
- The `REPORT_SENDER_EMAIL` is the email address from which reports will be sent
- The `ADMIN_EMAIL` is the email address to CC on all reports
- The `MARKET_CLOSE_TIMEZONE`, `MARKET_CLOSE_HOUR`, and `MARKET_CLOSE_MINUTE` are used for daily P&L calculation
- The SMTP settings are required for sending reports via email
- For production environments, you should use strong, unique values for all these variables

## 4. Starting the Report Worker

To start the Report Worker container:

```bash
docker-compose up -d report-worker
```

This command:
- Starts the Report Worker in detached mode (`-d`)
- Uses the configuration from `docker-compose.yml`
- Creates and initializes the Report Worker container with the environment variables from `.env`
- Automatically starts the required dependencies (MongoDB) if they're not already running

## 5. Verifying the Report Worker is Running

Check if the Report Worker container is running with:

```bash
docker ps | grep report-worker
```

You should see output similar to:

```
CONTAINER ID   IMAGE                     COMMAND                  CREATED          STATUS          PORTS                    NAMES
abcdef123456   spreadpilot-report-worker "gunicorn --bind :8..." 5 minutes ago    Up 5 minutes    0.0.0.0:8084->8084/tcp   spreadpilot-report-worker
```

## 6. Checking Report Worker Logs

To verify that the Report Worker is properly connecting to MongoDB and loading secrets:

```bash
docker logs spreadpilot-report-worker
```

Look for messages indicating successful connections:
- "Report Worker service starting..."
- "Connected to MongoDB database"
- "Successfully loaded secret"
- "Configuration loaded"

## 7. Testing the Report Worker

The Report Worker exposes a health check endpoint that you can use to test its functionality:

```bash
curl http://localhost:8084/health
```

Expected response:
```json
{"status": "healthy"}
```

To test the full functionality, you would need to publish a message to the Pub/Sub topic that the Report Worker is subscribed to. This can be done using the Google Cloud Console or the `gcloud` command-line tool:

```bash
# For daily P&L calculation
gcloud pubsub topics publish spreadpilot-reports --message='{"job_type":"daily"}'

# For monthly report generation
gcloud pubsub topics publish spreadpilot-reports --message='{"job_type":"monthly"}'
```

If configured correctly, the Report Worker will process the job and generate the appropriate reports.

## 8. Troubleshooting

### Pub/Sub Connection Issues

If the Report Worker fails to receive messages from Pub/Sub:

1. Verify that the Google Cloud credentials are correctly set up
2. Check that the Pub/Sub subscription is properly configured
3. Ensure that the `GOOGLE_CLOUD_PROJECT` environment variable is set correctly
4. Check the Report Worker logs for specific error messages related to Pub/Sub

### MongoDB Connection Issues

If the Report Worker fails to connect to MongoDB:

1. Verify that the MongoDB container is running: `docker ps | grep mongodb`
2. Check that the MongoDB credentials are correct
3. Ensure that the `MONGO_URI` and `MONGO_DB_NAME` environment variables are set correctly
4. Check the Report Worker logs for specific error messages related to MongoDB

### Report Generation Issues

If reports are not being generated correctly:

1. Verify that the Report Worker has access to the necessary data in MongoDB
2. Check that the PDF and Excel generation utilities are working correctly
3. Ensure that the temporary directories for report generation are writable
4. Check the Report Worker logs for specific error messages related to report generation

### Email Sending Issues

If reports are not being sent via email:

1. Verify that the SMTP settings are correct
2. Check that the `REPORT_SENDER_EMAIL` and `ADMIN_EMAIL` are set correctly
3. Ensure that the SMTP server is accessible from the Report Worker container
4. Check the Report Worker logs for specific error messages related to SMTP

### Container Startup Issues

If the Report Worker container fails to start:

1. Check Docker logs: `docker logs spreadpilot-report-worker`
2. Verify that all required environment variables are set in the `.env` file
3. Ensure that the dependencies (MongoDB) are running
4. Check system resources (CPU, memory, disk space)

## 9. Security Considerations

For production environments:

1. Use strong, unique passwords and tokens
2. Implement proper secrets management for all credentials
3. Consider using HTTPS for the Report Worker (e.g., using a reverse proxy)
4. Restrict access to the Report Worker to authorized services only
5. Regularly audit access logs and report generation activities
6. Ensure that sensitive information is properly handled in reports
7. Implement secure file handling for temporary report files

## 10. Next Steps

After setting up the Report Worker, you can proceed to configure the Frontend, which provides a user interface for interacting with the SpreadPilot system.

The Report Worker will work in conjunction with other services to:
- Calculate P&L for trading activities
- Generate periodic reports for followers
- Provide timely financial updates to stakeholders
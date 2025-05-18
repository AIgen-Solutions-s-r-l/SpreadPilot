# Admin API Setup Guide for SpreadPilot

This document provides detailed instructions for setting up the Admin API for the SpreadPilot system. It covers the configuration, startup, verification, and troubleshooting steps.

> **Note:** For a simplified setup process, refer to the [ADMIN-API-SETUP.md](../../ADMIN-API-SETUP.md) file in the project root. It provides a Docker-based approach for generating password hashes, testing MongoDB connections, and running the Admin API.

## Prerequisites

- Docker and Docker Compose installed on your system
- MongoDB service set up and running (see [MongoDB Setup Guide](./0-mongodb.md))
- Trading Bot service set up (see [Trading Bot Setup Guide](./2-trading-bot.md))
- Basic understanding of RESTful APIs and authentication

## 1. Understanding the Admin API

The Admin API is a backend service that provides an administrative interface for the SpreadPilot trading system. Its primary responsibilities include:

1. User authentication and authorization for administrative access
2. Managing followers (users/accounts that replicate trades)
3. Providing dashboard data for monitoring trading activity
4. Exposing endpoints for manual control (e.g., closing positions)
5. Serving as the backend for the frontend web interface
6. Providing WebSocket support for real-time updates

The Admin API is implemented as a FastAPI application that runs in a Docker container. It communicates with the MongoDB database for data persistence and with the Trading Bot for executing trading commands.

> **Note on Consolidation:** The Admin API has been consolidated from three different implementations (`admin_api/`, `admin-api/`, and `simple-admin-api/`) into a single, unified version in `admin-api/`. This consolidation improves maintainability, reduces duplication, and provides a consistent API implementation with the best features from all three previous versions.

## 2. Admin API Configuration in docker-compose.yml

The SpreadPilot system uses a containerized version of the Admin API, configured in the `docker-compose.yml` file. Here's the relevant section:

```yaml
admin-api:
  build:
    context: .
    dockerfile: admin-api/Dockerfile
  container_name: spreadpilot-admin-api
  environment:
    - GOOGLE_CLOUD_PROJECT=spreadpilot-dev
    - MONGO_URI=mongodb://mongodb:27017
    - MONGO_DB_NAME=spreadpilot_admin_test
    - TRADING_BOT_HOST=trading-bot
    - TRADING_BOT_PORT=8080
    - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
    - ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
    - ADMIN_PASSWORD_HASH=${ADMIN_PASSWORD_HASH}
    - JWT_SECRET=${JWT_SECRET:-testsecret}
    - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json
  volumes:
    - ./credentials:/app/credentials
  depends_on:
    - mongodb
    - trading-bot
  ports:
    - "8083:8080"
  restart: unless-stopped
```

This configuration:
- Builds the Admin API from the Dockerfile in the `admin-api` directory
- Names the container `spreadpilot-admin-api`
- Sets environment variables for various services and APIs
- Mounts the `credentials` directory for Google API authentication
- Specifies dependencies on MongoDB and the Trading Bot
- Exposes port 8083 on the host, mapping to port 8080 in the container
- Configures automatic restart unless explicitly stopped

## 3. Environment Variables Setup

The Admin API requires several environment variables to be set in the `.env` file at the project root. Here are the key variables:

```
# Admin API Authentication
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD_HASH=your_hashed_password
JWT_SECRET=your_jwt_secret

# MongoDB (Already set up for MongoDB)
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=password
```

Replace the placeholder values with your actual credentials and settings.

**Important Notes:**
- The `ADMIN_USERNAME` is the username for logging into the Admin API
- The `ADMIN_PASSWORD_HASH` should be a bcrypt hash of your admin password
- The `JWT_SECRET` is used for signing JSON Web Tokens for authentication
- If you don't provide values for `ADMIN_USERNAME` and `JWT_SECRET`, the defaults will be used (`admin` and `testsecret` respectively)
- For production environments, you should use strong, unique values for all these variables

## 4. Generating a Password Hash

To generate a bcrypt hash for your admin password, you can use the provided utility in the Admin API:

```bash
# Using the provided Docker utility
docker-compose -f docker-compose.admin-api-setup.yml run --rm bcrypt-util
```

This will prompt you to enter a password and will output the bcrypt hash. Add the resulting hash to your `.env` file as `ADMIN_PASSWORD_HASH`.

Alternatively, you can use the Python script directly:

```bash
# Using the Python script directly
python admin-api/generate_hash.py
```

## 5. Testing MongoDB Connection

Before starting the Admin API, you can test the MongoDB connection using the provided utility:

```bash
# Using the provided Docker utility
docker-compose -f docker-compose.admin-api-setup.yml run --rm mongodb-test
```

This will attempt to connect to MongoDB using the configured URI and will output the result.

## 6. Starting the Admin API

To start the Admin API container:

```bash
docker-compose up -d admin-api
```

This command:
- Starts the Admin API in detached mode (`-d`)
- Uses the configuration from `docker-compose.yml`
- Creates and initializes the Admin API container with the environment variables from `.env`
- Automatically starts the required dependencies (MongoDB and Trading Bot) if they're not already running

## 7. Verifying the Admin API is Running

Check if the Admin API container is running with:

```bash
docker ps | grep admin-api
```

You should see output similar to:

```
CONTAINER ID   IMAGE                    COMMAND                  CREATED          STATUS          PORTS                    NAMES
abcdef123456   spreadpilot-admin-api    "python main.py"         5 minutes ago    Up 5 minutes    0.0.0.0:8083->8080/tcp   spreadpilot-admin-api
```

## 8. Checking Admin API Logs

To verify that the Admin API is properly connecting to MongoDB and the Trading Bot:

```bash
docker logs spreadpilot-admin-api
```

Look for messages indicating successful connections:
- "Admin API started"
- "Connected to MongoDB"
- "Connected to Trading Bot"

## 9. Testing the Admin API

The Admin API exposes several endpoints that you can use to test its functionality:

### Basic Health Check

```bash
curl http://localhost:8083/health
```

Expected response:
```json
{"status": "healthy"}
```

### Authentication

```bash
curl -X POST http://localhost:8083/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
```

Expected response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Use the returned token for authenticated requests:

```bash
curl http://localhost:8083/api/v1/followers \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### WebSocket Connection

The Admin API also provides WebSocket endpoints for real-time updates. You can test this using a WebSocket client or a simple JavaScript example:

```javascript
const ws = new WebSocket('ws://localhost:8083/api/v1/ws');
ws.onmessage = (event) => {
  console.log('Received:', event.data);
};
```

## 10. Troubleshooting

### Authentication Issues

If you're having trouble authenticating with the Admin API:

1. Verify that the `ADMIN_USERNAME` and `ADMIN_PASSWORD_HASH` environment variables are set correctly
2. Check that the `JWT_SECRET` environment variable is set
3. Ensure that you're using the correct username and password in your authentication requests
4. Check the Admin API logs for specific error messages related to authentication

### MongoDB Connection Issues

If the Admin API fails to connect to MongoDB:

1. Verify that the MongoDB container is running: `docker ps | grep mongodb`
2. Check that the MongoDB credentials are correct
3. Ensure that the `MONGO_URI` and `MONGO_DB_NAME` environment variables are set correctly
4. Check the Admin API logs for specific error messages related to MongoDB
5. Use the MongoDB test utility to verify the connection: `docker-compose -f docker-compose.admin-api-setup.yml run --rm mongodb-test`

### Trading Bot Connection Issues

If the Admin API fails to connect to the Trading Bot:

1. Verify that the Trading Bot container is running: `docker ps | grep trading-bot`
2. Check that the `TRADING_BOT_HOST` and `TRADING_BOT_PORT` environment variables are set correctly
3. Ensure that the Trading Bot is properly configured and running
4. Check the Admin API logs for specific error messages related to the Trading Bot connection

### Container Startup Issues

If the Admin API container fails to start:

1. Check Docker logs: `docker logs spreadpilot-admin-api`
2. Verify that all required environment variables are set in the `.env` file
3. Ensure that the dependencies (MongoDB and Trading Bot) are running
4. Check system resources (CPU, memory, disk space)

## 11. Security Considerations

For production environments:

1. Use strong, unique passwords and JWT secrets
2. Implement proper secrets management for all credentials
3. Consider using HTTPS for the Admin API (e.g., using a reverse proxy)
4. Restrict access to the Admin API to authorized users only
5. Implement rate limiting to prevent brute force attacks
6. Regularly audit access logs and user activities
7. Consider implementing two-factor authentication for additional security

## 12. Next Steps

After setting up the Admin API, you can proceed to configure the Frontend, which provides a user interface for interacting with the Admin API and monitoring the SpreadPilot system.

The Frontend will interact with the Admin API to:
- Authenticate administrators
- Display dashboard data
- Manage followers
- Trigger manual commands (e.g., closing positions)
- Receive real-time updates via WebSocket
# SpreadPilot Admin API Setup Guide

This guide will walk you through setting up the Admin API and MongoDB components of the SpreadPilot system.

## Prerequisites

- Docker and Docker Compose installed on your system
- Git (to clone the repository if you haven't already)

## Step 1: Generate a Password Hash

We've provided a Docker-based approach to generate a bcrypt hash for your admin password:

```bash
# Build the Docker image for bcrypt
docker build -t bcrypt-generator -f Dockerfile.bcrypt .

# Run the container to generate a hash
docker run -it --rm bcrypt-generator
```

When prompted, enter your desired admin password. The script will output a bcrypt hash that you can use in your environment configuration.

## Step 2: Test MongoDB Connection

Before proceeding with the Admin API setup, it's a good idea to test the MongoDB connection:

```bash
# Build the Docker image for MongoDB test
docker build -t mongodb-test -f Dockerfile.mongodb-test .

# Run the container to test MongoDB connection
docker run --network spreadpilot_default mongodb-test
```

This will test if MongoDB is accessible and functioning correctly.

## Step 3: Run the Admin API

Now that you have generated a password hash and tested the MongoDB connection, you can run the Admin API:

```bash
# Navigate to the simple-admin-api directory
cd simple-admin-api

# Start the Admin API and MongoDB containers
docker-compose up -d
```

This will start the Admin API and MongoDB containers. You can verify that they are running with:

```bash
docker ps
```

And you can check the health of the Admin API with:

```bash
curl http://localhost:8083/health
```

If everything is working correctly, you should see a response like:

```json
{"status":"healthy","database":"connected"}
```

## Step 4: Access the Admin API

The Admin API is now running and accessible at http://localhost:8083. You can use the following endpoints:

- `GET /`: Root endpoint that returns a simple greeting
- `GET /health`: Health check endpoint that verifies the MongoDB connection
- `POST /api/v1/auth/token`: Authentication endpoint for obtaining a JWT token
- `GET /api/v1/followers`: Protected endpoint that requires authentication

You can use tools like curl or Postman to interact with the API.

## Step 3: Configure Environment Variables

We've provided a sample environment file `.env.admin-api` with default values. You can use it as is for testing, or modify it with your own values:

1. Open `.env.admin-api` in your editor
2. Replace the default `ADMIN_PASSWORD_HASH` with the hash generated in Step 2
3. Update other values as needed (e.g., `JWT_SECRET`, MongoDB credentials)

## Step 4: Create Credentials Directory

The Admin API needs a directory for credentials:

```bash
mkdir -p credentials
```

For a complete setup, you would place your Google service account JSON file in this directory. For this simplified setup, we can proceed without it.

## Step 5: Start the Services

Use Docker Compose to start MongoDB and the Admin API:

```bash
docker-compose -f docker-compose.admin-api-setup.yml --env-file .env.admin-api up -d
```

This command:
- Uses our simplified docker-compose file
- Loads environment variables from `.env.admin-api`
- Starts the services in detached mode (`-d`)

## Step 6: Verify the Services are Running

Check if the containers are running:

```bash
docker ps
```

You should see two containers:
- `spreadpilot-mongodb`
- `spreadpilot-admin-api`

## Step 7: Check the Logs

View the logs to ensure everything started correctly:

```bash
docker logs spreadpilot-admin-api
```

Look for messages indicating successful startup and connection to MongoDB.

## Step 8: Test the Admin API

### Basic Health Check

```bash
curl http://localhost:8083/
```

Expected response: `{"Hello": "Admin API"}`

### Authentication

```bash
curl -X POST http://localhost:8083/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "adminpassword"}'
```

This should return a JWT token if authentication is successful.

### Access Protected Endpoints

Use the token from the previous step to access protected endpoints:

```bash
curl http://localhost:8083/api/v1/followers \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Step 9: Stopping the Services

When you're done, stop the services:

```bash
docker-compose -f docker-compose.admin-api-setup.yml down
```

To remove the volumes (including the MongoDB data):

```bash
docker-compose -f docker-compose.admin-api-setup.yml down -v
```

## Troubleshooting

### Authentication Issues

If you're having trouble authenticating:
1. Verify that the `ADMIN_USERNAME` and `ADMIN_PASSWORD_HASH` in `.env.admin-api` are correct
2. Check that you're using the correct password in your authentication requests
3. Check the Admin API logs: `docker logs spreadpilot-admin-api`

### MongoDB Connection Issues

If the Admin API fails to connect to MongoDB:
1. Verify that the MongoDB container is running: `docker ps | grep mongodb`
2. Check that the MongoDB credentials in `.env.admin-api` are correct
3. Ensure that the `MONGO_URI` is correctly formatted
4. Check the Admin API logs for specific error messages

### Container Startup Issues

If either container fails to start:
1. Check Docker logs: `docker logs spreadpilot-mongodb` or `docker logs spreadpilot-admin-api`
2. Verify that all required environment variables are set in `.env.admin-api`
3. Check system resources (CPU, memory, disk space)

## Next Steps

After successfully setting up the Admin API and MongoDB, you can:
1. Explore the API endpoints using a tool like Postman or curl
2. Set up the Frontend to interact with the Admin API
3. Add the Trading Bot and other components to complete the SpreadPilot system
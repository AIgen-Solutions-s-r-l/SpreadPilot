# SpreadPilot Frontend Setup Guide

This guide will walk you through setting up the Frontend component of the SpreadPilot system.

## Prerequisites

- Docker and Docker Compose installed on your system
- Admin API service set up and running (see [ADMIN-API-SETUP.md](./ADMIN-API-SETUP.md))

## Step 1: Configure Environment Variables

Create a `.env.frontend` file with the following content:

```
# Frontend Configuration
REACT_APP_API_URL=http://localhost:8083
REACT_APP_WS_URL=ws://localhost:8083/ws
```

These environment variables will be used by the Frontend to connect to the Admin API.

## Step 2: Create a Docker Compose File for the Frontend

Create a `docker-compose.frontend.yml` file with the following content:

```yaml
version: '3'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: spreadpilot-frontend
    environment:
      - REACT_APP_API_URL=http://localhost:8083
      - REACT_APP_WS_URL=ws://localhost:8083/ws
    ports:
      - "8080:80"
    restart: unless-stopped
```

This configuration:
- Builds the Frontend from the Dockerfile in the `frontend` directory
- Names the container `spreadpilot-frontend`
- Sets environment variables for the Admin API URL and WebSocket URL
- Exposes port 8080 on the host, mapping to port 80 in the container
- Configures automatic restart unless explicitly stopped

## Step 3: Start the Frontend

To start the Frontend container:

```bash
docker-compose -f docker-compose.frontend.yml --env-file .env.frontend up -d
```

This command:
- Starts the Frontend in detached mode (`-d`)
- Uses the configuration from `docker-compose.frontend.yml`
- Creates and initializes the Frontend container with the environment variables from `.env.frontend`

## Step 4: Verify the Frontend is Running

Check if the Frontend container is running with:

```bash
docker ps | grep frontend
```

You should see output similar to:

```
CONTAINER ID   IMAGE                    COMMAND                  CREATED          STATUS          PORTS                    NAMES
abcdef123456   spreadpilot-frontend     "nginx -g 'daemon of…"   5 minutes ago    Up 5 minutes    0.0.0.0:8080->80/tcp     spreadpilot-frontend
```

## Step 5: Access the Frontend

Once the Frontend container is running, you can access it in your web browser at:

```
http://localhost:8080
```

You should see the SpreadPilot login page. You can log in using the admin credentials you set up in the Admin API configuration.

## Troubleshooting

### Connection Issues with Admin API

If the Frontend fails to connect to the Admin API:

1. Verify that the Admin API container is running: `docker ps | grep admin-api`
2. Check that the `REACT_APP_API_URL` and `REACT_APP_WS_URL` environment variables are set correctly
3. Check the Frontend logs for specific error messages: `docker logs spreadpilot-frontend`
4. Try accessing the Admin API directly to ensure it's responding: `curl http://localhost:8083/health`

### Container Startup Issues

If the Frontend container fails to start:

1. Check Docker logs: `docker logs spreadpilot-frontend`
2. Verify that all required environment variables are set in the `.env.frontend` file
3. Check system resources (CPU, memory, disk space)
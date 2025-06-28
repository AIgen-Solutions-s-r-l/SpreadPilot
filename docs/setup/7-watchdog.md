# 👀 Watchdog Setup Guide for SpreadPilot

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [1. Understanding the Watchdog](#1-understanding-the-watchdog)
- [2. Docker Configuration](#2-watchdog-configuration-in-docker-composeyml)
- [3. Environment Variables](#3-environment-variables-setup)
- [4. Starting the Service](#4-starting-the-watchdog)
- [5. Health Verification](#5-verifying-the-watchdog-is-running)
- [6. Logs & Monitoring](#6-checking-watchdog-logs)
- [7. Testing](#7-testing-the-watchdog)
- [8. Troubleshooting](#8-troubleshooting)
- [9. Security](#9-security-considerations)
- [10. Next Steps](#10-next-steps)

## 📖 Overview

This document provides detailed instructions for setting up the Watchdog service for the SpreadPilot system. The Watchdog monitors critical services and automatically restarts them when failures are detected.

## ✅ Prerequisites

- Docker and Docker Compose installed on your system
- MongoDB service set up and running (see [MongoDB Setup Guide](./0-mongodb.md))
- Docker socket access (for container management)
- Basic understanding of health monitoring concepts

## 1. 🎯 Understanding the Watchdog

The Watchdog is a self-hosted monitoring service that ensures critical SpreadPilot components remain operational.

### 🔧 Core Responsibilities

1. Health checks every 15 seconds via HTTP endpoints
2. Tracking consecutive failures per service
3. Automatic Docker restart after 3 consecutive failures
4. Alert publication to MongoDB for failures and recovery
5. Concurrent monitoring of multiple services

### 🏗️ Architecture

The Watchdog is implemented as a Python asyncio application that:
- Uses `httpx` for async HTTP health checks
- Integrates with Docker CLI via `subprocess` for container management
- Stores alerts in MongoDB for tracking and notification
- Monitors Trading Bot, Admin API, Report Worker, and Frontend services

## 2. 🐳 Watchdog Configuration in docker-compose.yml

The SpreadPilot system includes the Watchdog service configuration:

```yaml
watchdog:
  build:
    context: ./watchdog
    dockerfile: Dockerfile
  container_name: spreadpilot-watchdog
  environment:
    - CHECK_INTERVAL_SECONDS=15
    - HEALTH_CHECK_TIMEOUT=5
    - MAX_CONSECUTIVE_FAILURES=3
    - MONGO_URI=mongodb://mongodb:27017
    - MONGO_DB_NAME=spreadpilot_admin
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock  # Docker socket for container management
    - ./spreadpilot-core:/app/spreadpilot-core    # Core library for alerts
  depends_on:
    - mongodb
    - trading-bot
    - admin-api
    - report-worker
    - frontend
  networks:
    - spreadpilot-network
  restart: unless-stopped
```

This configuration:
- Mounts the Docker socket for container management capabilities
- Connects to MongoDB for alert storage
- Monitors all critical SpreadPilot services
- Runs on the same network as monitored services

## 3. 🔐 Environment Variables Setup

The Watchdog uses the following environment variables:

```bash
# Monitoring Configuration
CHECK_INTERVAL_SECONDS=15        # Time between health checks
HEALTH_CHECK_TIMEOUT=5           # HTTP timeout for health checks
MAX_CONSECUTIVE_FAILURES=3       # Failures before restart

# MongoDB Configuration
MONGO_URI=mongodb://mongodb:27017
MONGO_DB_NAME=spreadpilot_admin
```

## 4. 🚀 Starting the Watchdog

To start the Watchdog service:

```bash
# Start with all dependencies
docker-compose up -d watchdog

# Or start the entire stack
docker-compose up -d
```

The Watchdog will automatically:
1. Connect to MongoDB
2. Begin monitoring configured services
3. Start tracking health status

## 5. ✅ Verifying the Watchdog is Running

Check that the Watchdog is operational:

```bash
# Check container status
docker ps | grep spreadpilot-watchdog

# View recent logs
docker logs spreadpilot-watchdog --tail 50

# Look for startup messages
docker logs spreadpilot-watchdog 2>&1 | grep "Watchdog service starting"
```

Expected output:
```
INFO - Watchdog service starting...
INFO - Monitoring services: trading_bot, admin_api, report_worker, frontend
INFO - Check interval: 15 seconds
INFO - Max consecutive failures before restart: 3
```

## 6. 📋 Checking Watchdog Logs

Monitor the Watchdog's activity:

```bash
# Follow logs in real-time
docker logs -f spreadpilot-watchdog

# Check for health check results
docker logs spreadpilot-watchdog 2>&1 | grep "is healthy"

# Look for restart actions
docker logs spreadpilot-watchdog 2>&1 | grep "restart"

# Check for alerts
docker logs spreadpilot-watchdog 2>&1 | grep "Alert"
```

## 7. 🧪 Testing the Watchdog

### Manual Health Check Test

Stop a service to test auto-recovery:

```bash
# Stop a monitored service
docker stop spreadpilot-admin-api

# Watch Watchdog logs
docker logs -f spreadpilot-watchdog

# Should see:
# - Failed health checks
# - After 3 failures: restart attempt
# - Alert publication
```

### Running Unit Tests

```bash
# Run tests from the watchdog directory
cd watchdog/
pytest tests/
```

## 8. 🔧 Troubleshooting

### Docker Socket Access Issues

If the Watchdog cannot restart containers:

1. Verify Docker socket is mounted correctly
2. Check container has permission to access socket
3. Ensure Docker CLI is installed in the container
4. Test manually: `docker exec spreadpilot-watchdog docker ps`

### MongoDB Connection Issues

If alerts are not being stored:

1. Verify MongoDB is running: `docker ps | grep mongodb`
2. Check MongoDB connection string in environment
3. Test connection: `docker exec spreadpilot-watchdog python -c "from motor.motor_asyncio import AsyncIOMotorClient; print('Connected')"`

### Health Check Failures

If services appear unhealthy but are running:

1. Verify health endpoints are accessible
2. Check network connectivity between containers
3. Review service logs for actual health issues
4. Test endpoints manually: `docker exec spreadpilot-watchdog curl http://trading-bot:8080/health`

## 9. 🔒 Security Considerations

### Docker Socket Access

- The Watchdog requires privileged Docker socket access
- This allows container management but is a security risk
- Consider using Docker API with TLS in production
- Limit Watchdog permissions to only necessary actions

### Network Isolation

- Run Watchdog on the same network as monitored services
- Use internal Docker networks, not host networking
- Avoid exposing Watchdog ports externally

### Alert Data

- Alerts may contain sensitive service information
- Ensure MongoDB is properly secured
- Implement access controls for alert data

## 10. ⏭️ Next Steps

After setting up the Watchdog:

1. **Monitor Alert Patterns**: Review MongoDB alerts collection for service reliability
2. **Tune Parameters**: Adjust check intervals and failure thresholds based on your needs
3. **Integrate Alerting**: Connect alerts to notification systems (Telegram, email)
4. **Add Custom Health Checks**: Extend monitoring for service-specific health criteria

### 🔗 Integration Points

The Watchdog integrates with:
- **MongoDB**: Stores all alert events
- **Docker**: Manages container lifecycle
- **Alert Router**: Processes published alerts for notifications
- **All Monitored Services**: Via health check endpoints

### 📊 Monitoring Best Practices

1. Set appropriate timeout values for your network
2. Monitor Watchdog logs for patterns
3. Review failure counts to identify problematic services
4. Use alerts to track service reliability over time
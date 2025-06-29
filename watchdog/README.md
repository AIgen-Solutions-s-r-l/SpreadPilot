# SpreadPilot Watchdog Service

A self-hosted health monitoring service that monitors all SpreadPilot containers labeled with 'spreadpilot' and automatically restarts them when failures are detected.

## Features

- **Dynamic Container Discovery**: Automatically discovers and monitors all containers with 'spreadpilot' label
- **Continuous Health Monitoring**: Checks service health endpoints every 30 seconds
- **Auto-Recovery**: Automatically restarts failed services after 3 consecutive failures
- **Concurrent Monitoring**: Checks all services in parallel for efficiency
- **Redis Alert Publishing**: Publishes critical alerts to Redis stream for downstream processing
- **Docker Integration**: Uses Docker API for container management and restart operations

## Monitored Services

The watchdog automatically monitors any running container with the label `spreadpilot`. This includes:

- Trading Bot
- Admin API
- Report Worker
- Frontend Dashboard
- Alert Router
- Admin Dashboard
- Any future services labeled with 'spreadpilot'

## Configuration

### Environment Variables

- `CHECK_INTERVAL_SECONDS`: Time between health checks (default: 30)
- `HEALTH_CHECK_TIMEOUT`: HTTP timeout for health checks (default: 10)
- `MAX_CONSECUTIVE_FAILURES`: Failures before restart (default: 3)
- `REDIS_URL`: Redis connection URL for alert publishing (default: redis://localhost:6379)

### Docker Requirements

The watchdog requires access to the Docker socket to restart containers. When running in Docker, mount the socket:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

## Health Check Logic

1. **Container Discovery**: Queries Docker API for all containers with 'spreadpilot' label
2. **Port Detection**: Automatically detects exposed ports from container configuration
3. **HTTP GET** request to `http://{container_name}:{port}/health`
4. **Success**: 200 OK status resets failure counter
5. **Failure**: Non-200 status or network error increments failure counter
6. **Auto-Restart**: After 3 consecutive failures, executes `docker restart`
7. **Alert**: Publishes critical alert to Redis stream

## Alert Events

The watchdog publishes alerts to the Redis stream `alerts` with the following types:

- `COMPONENT_DOWN`: Service restart failed or component is down
- `COMPONENT_RECOVERED`: Service recovered after failures

Alert structure:
```json
{
  "event_type": "COMPONENT_DOWN",
  "message": "Container trading-bot restart failed",
  "params": {
    "container_name": "trading-bot",
    "action": "restart",
    "success": false,
    "consecutive_failures": 3,
    "severity": "CRITICAL"
  }
}
```

## Development

### Running Tests

```bash
pytest tests/
```

### Running Locally

```bash
# Install dependencies
pip install -r requirements.in

# Run the watchdog
python main.py
```

Note: When running locally, ensure Docker is accessible and you have permissions to restart containers.

## Docker Deployment

Build and run the watchdog:

```bash
docker build -t spreadpilot-watchdog .
docker run -v /var/run/docker.sock:/var/run/docker.sock spreadpilot-watchdog
```

## Architecture

The watchdog uses:
- **docker-py**: Docker SDK for Python for container management
- **httpx**: Async HTTP client for health checks
- **asyncio**: Concurrent monitoring of multiple services
- **redis**: Redis client for alert stream publishing
- **spreadpilot-core**: Alert models and integration

## Container Labeling

To enable monitoring, containers must have the `spreadpilot` label:

```yaml
services:
  my-service:
    labels:
      - "spreadpilot"
```

## Security Considerations

- Requires Docker socket access (privileged operation)
- Should run in the same network as monitored services
- Health endpoints should be secured in production
- Watchdog user is added to docker group for container management
# SpreadPilot Watchdog Service

A self-hosted health monitoring service that monitors critical SpreadPilot components and automatically restarts them when failures are detected.

## Features

- **Continuous Health Monitoring**: Checks service health endpoints every 15 seconds
- **Auto-Recovery**: Automatically restarts failed services after 3 consecutive failures
- **Concurrent Monitoring**: Checks all services in parallel for efficiency
- **Alert Publishing**: Publishes alerts for service failures and recovery events
- **Docker Integration**: Uses Docker CLI to restart containers

## Monitored Services

The watchdog monitors the following services:

- **Gateway Manager** (`gateway-manager:8080/health`)
- **Executor** (`executor:8080/health`)
- **Monitor** (`monitor:8080/health`)
- **Dashboard** (`dashboard:3000/api/health`)

## Configuration

### Environment Variables

- `CHECK_INTERVAL_SECONDS`: Time between health checks (default: 15)
- `HEALTH_CHECK_TIMEOUT`: HTTP timeout for health checks (default: 5)
- `MAX_CONSECUTIVE_FAILURES`: Failures before restart (default: 3)

### Docker Requirements

The watchdog requires access to the Docker socket to restart containers. When running in Docker, mount the socket:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

## Health Check Logic

1. **HTTP GET** request to service health endpoint
2. **Success**: 200 OK status resets failure counter
3. **Failure**: Non-200 status or network error increments failure counter
4. **Auto-Restart**: After 3 consecutive failures, attempts Docker restart
5. **Alert**: Publishes alert for failures and recovery events

## Alert Events

The watchdog publishes the following alert types:

- `COMPONENT_DOWN`: Service restart failed
- `COMPONENT_RECOVERED`: Service recovered after failures

Alert parameters include:
- `component_name`: Service identifier
- `container_name`: Docker container name
- `action`: Action taken (restart/recovery)
- `success`: Whether action succeeded
- `consecutive_failures`: Number of failures before action

## Development

### Running Tests

```bash
pytest tests/
```

### Running Locally

```bash
python watchdog.py
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
- **httpx**: Async HTTP client for health checks
- **asyncio**: Concurrent monitoring of multiple services
- **subprocess**: Docker CLI integration for container management
- **spreadpilot-core**: Alert models and integration

## Security Considerations

- Requires Docker socket access (privileged operation)
- Should run in the same network as monitored services
- Health endpoints should be secured in production
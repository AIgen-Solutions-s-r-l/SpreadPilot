# Watchdog Integration Tests

This directory contains integration and unit tests for the SpreadPilot Watchdog service.

## Test Structure

- `test_watchdog_unit.py` - Unit tests with mocked dependencies
- `test_watchdog_integration.py` - Integration tests using Docker Compose
- `docker-compose.test.yml` - Test environment setup
- `mock_service.py` - Mock service that can simulate healthy/unhealthy states

## Running Tests

### Unit Tests
```bash
pytest tests/watchdog/test_watchdog_unit.py -v
```

### Integration Tests
```bash
# Requires Docker and Docker Compose
pytest tests/watchdog/test_watchdog_integration.py -v -s
```

## Test Scenarios

### Unit Tests
- Container discovery with 'spreadpilot' label
- Health check success/failure scenarios
- Container restart functionality
- Alert publishing to Redis
- Failure count tracking and threshold logic
- Service recovery detection

### Integration Tests
- End-to-end health monitoring workflow
- Automatic container restart after 3 failures
- Critical alert publishing to Redis stream
- Service recovery and recovery alerts
- Container discovery in Docker environment

## Mock Service

The `mock_service.py` creates a simple HTTP server that:
- Responds to `/health` endpoint
- Returns 200 (healthy) by default
- Returns 503 (unhealthy) when `/tmp/unhealthy` file exists
- Allows dynamic health state changes during tests

## Environment Variables

The test environment uses these configurations:
- `CHECK_INTERVAL_SECONDS=5` - Faster checks for testing
- `MAX_CONSECUTIVE_FAILURES=3` - Standard failure threshold
- `REDIS_URL=redis://redis:6379` - Test Redis instance
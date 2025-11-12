"""Integration test for Watchdog service with dummy container."""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import docker
import pytest
from fakeredis import aioredis as fakeredis
from fastapi import FastAPI
from fastapi.responses import Response

from spreadpilot_core.models.alert import Alert, AlertSeverity


# Create a simple FastAPI app that can return different statuses
app = FastAPI()

# Global variable to control health status
health_status = {"healthy": True, "call_count": 0}


@app.get("/health")
async def health_check():
    """Health endpoint that can be controlled during tests."""
    health_status["call_count"] += 1

    if health_status["healthy"]:
        return {"status": "healthy", "timestamp": time.time()}
    else:
        return Response(content="Unhealthy", status_code=500)


@pytest.fixture
async def fake_redis():
    """Create a fake Redis client for testing."""
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    await client.close()


@pytest.fixture
def mock_docker_client():
    """Create a mock Docker client."""
    client = MagicMock(spec=docker.DockerClient)
    return client


@pytest.fixture
def dummy_container():
    """Create a mock container object."""
    container = MagicMock()
    container.name = "test-service"
    container.id = "abc123"
    container.attrs = {"NetworkSettings": {"Ports": {"8080/tcp": [{"HostPort": "8080"}]}}}
    container.reload = MagicMock()
    container.restart = MagicMock()

    return container


class TestWatchdogIntegration:
    """Integration tests for Watchdog service."""

    @pytest.mark.asyncio
    async def test_healthy_service_monitoring(
        self, mock_docker_client, dummy_container, fake_redis
    ):
        """Test monitoring a healthy service."""
        # Import here to avoid issues
        from watchdog.main import ContainerWatchdog

        # Reset health status
        global health_status
        health_status = {"healthy": True, "call_count": 0}

        # Setup
        watchdog = ContainerWatchdog()
        watchdog.docker_client = mock_docker_client
        watchdog.redis_client = fake_redis

        # Mock httpx client to return healthy status
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_httpx = AsyncMock()
        mock_httpx.get.return_value = mock_response
        watchdog.http_client = mock_httpx

        # Mock container list
        mock_docker_client.containers.list.return_value = [dummy_container]

        # Monitor the container
        await watchdog.monitor_container(dummy_container)

        # Verify no failure count
        assert watchdog.failure_counts.get("test-service", 0) == 0

        # Verify health check was called
        mock_httpx.get.assert_called_once()
        call_args = mock_httpx.get.call_args[0][0]
        assert "http://test-service:8080/health" in call_args

        # No alerts should be published for healthy service
        alerts = await fake_redis.xrange("alerts")
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_service_failure_and_restart(
        self, mock_docker_client, dummy_container, fake_redis
    ):
        """Test service failure detection and restart after 3 consecutive failures."""
        from watchdog.main import ContainerWatchdog

        watchdog = ContainerWatchdog()
        watchdog.docker_client = mock_docker_client
        watchdog.redis_client = fake_redis

        # Mock httpx to return failures
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_httpx = AsyncMock()
        mock_httpx.get.return_value = mock_response
        watchdog.http_client = mock_httpx

        # Mock container list
        mock_docker_client.containers.list.return_value = [dummy_container]

        # Simulate 3 consecutive failures
        for i in range(3):
            await watchdog.monitor_container(dummy_container)

        # Verify failure count
        assert watchdog.failure_counts["test-service"] == 0  # Reset after restart

        # Verify restart was called
        dummy_container.restart.assert_called_once_with(timeout=30)

        # Check alert was published
        alerts = await fake_redis.xrange("alerts")
        assert len(alerts) == 1

        # Parse alert
        _, alert_data = alerts[0]
        alert = Alert.model_validate_json(alert_data["data"])

        assert alert.follower_id == "system"
        assert "SERVICE_RESTART" in alert.reason
        assert "test-service" in alert.reason
        assert "3 consecutive health check failures" in alert.reason
        assert alert.severity == AlertSeverity.WARNING
        assert alert.service == "watchdog"

    @pytest.mark.asyncio
    async def test_service_recovery_after_failures(
        self, mock_docker_client, dummy_container, fake_redis
    ):
        """Test service recovery notification after previous failures."""
        from watchdog.main import ContainerWatchdog

        watchdog = ContainerWatchdog()
        watchdog.docker_client = mock_docker_client
        watchdog.redis_client = fake_redis

        # Mock httpx
        mock_httpx = AsyncMock()
        watchdog.http_client = mock_httpx

        # Start with 2 failures
        watchdog.failure_counts["test-service"] = 2

        # Now return healthy
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx.get.return_value = mock_response

        # Monitor (should recover)
        await watchdog.monitor_container(dummy_container)

        # Verify failure count reset
        assert watchdog.failure_counts["test-service"] == 0

        # Check recovery alert
        alerts = await fake_redis.xrange("alerts")
        assert len(alerts) == 1

        _, alert_data = alerts[0]
        alert = Alert.model_validate_json(alert_data["data"])

        assert "SERVICE_RECOVERED" in alert.reason
        assert "recovered after 2 failed health checks" in alert.reason
        assert alert.severity == AlertSeverity.INFO

    @pytest.mark.asyncio
    async def test_restart_failure_critical_alert(
        self, mock_docker_client, dummy_container, fake_redis
    ):
        """Test critical alert when restart fails."""
        from watchdog.main import ContainerWatchdog

        watchdog = ContainerWatchdog()
        watchdog.docker_client = mock_docker_client
        watchdog.redis_client = fake_redis

        # Mock httpx to return failures
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_httpx = AsyncMock()
        mock_httpx.get.return_value = mock_response
        watchdog.http_client = mock_httpx

        # Mock restart to fail
        dummy_container.restart.side_effect = Exception("Docker restart failed")

        # Simulate 3 failures to trigger restart
        for i in range(3):
            await watchdog.monitor_container(dummy_container)

        # Check critical alert
        alerts = await fake_redis.xrange("alerts")
        assert len(alerts) == 1

        _, alert_data = alerts[0]
        alert = Alert.model_validate_json(alert_data["data"])

        assert "SERVICE_RESTART_FAILED" in alert.reason
        assert alert.severity == AlertSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_multiple_container_monitoring(self, mock_docker_client, fake_redis):
        """Test monitoring multiple containers with different health states."""
        from watchdog.main import ContainerWatchdog

        # Create multiple containers
        healthy_container = MagicMock()
        healthy_container.name = "healthy-service"
        healthy_container.attrs = {"NetworkSettings": {"Ports": {"8080/tcp": [{}]}}}

        unhealthy_container = MagicMock()
        unhealthy_container.name = "unhealthy-service"
        unhealthy_container.attrs = {"NetworkSettings": {"Ports": {"8081/tcp": [{}]}}}

        watchdog = ContainerWatchdog()
        watchdog.docker_client = mock_docker_client
        watchdog.redis_client = fake_redis

        # Mock httpx with different responses
        async def mock_get(url):
            response = MagicMock()
            if "healthy-service" in url:
                response.status_code = 200
            else:
                response.status_code = 500
            return response

        mock_httpx = AsyncMock()
        mock_httpx.get.side_effect = mock_get
        watchdog.http_client = mock_httpx

        # Monitor both containers
        await asyncio.gather(
            watchdog.monitor_container(healthy_container),
            watchdog.monitor_container(unhealthy_container),
        )

        # Verify failure counts
        assert watchdog.failure_counts.get("healthy-service", 0) == 0
        assert watchdog.failure_counts["unhealthy-service"] == 1

    @pytest.mark.asyncio
    async def test_watchdog_continuous_monitoring(self, mock_docker_client, fake_redis):
        """Test the main monitoring loop behavior."""
        from watchdog.main import ContainerWatchdog

        watchdog = ContainerWatchdog()
        watchdog.docker_client = mock_docker_client
        watchdog.redis_client = fake_redis

        # Mock containers
        containers = [
            MagicMock(name="service-1", attrs={"NetworkSettings": {"Ports": {"8080/tcp": [{}]}}}),
            MagicMock(name="service-2", attrs={"NetworkSettings": {"Ports": {"8081/tcp": [{}]}}}),
        ]

        mock_docker_client.containers.list.return_value = containers

        # Mock healthy responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx = AsyncMock()
        mock_httpx.get.return_value = mock_response
        watchdog.http_client = mock_httpx

        # Run monitoring for a short time
        monitor_task = asyncio.create_task(watchdog.run())
        await asyncio.sleep(0.5)  # Let it run one cycle
        monitor_task.cancel()

        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Verify containers were discovered
        assert "service-1" in watchdog.monitored_containers
        assert "service-2" in watchdog.monitored_containers

        # Verify health checks were performed
        assert mock_httpx.get.call_count >= 2  # At least one check per container

    @pytest.mark.asyncio
    async def test_stale_container_cleanup(self, mock_docker_client):
        """Test cleanup of failure counts for removed containers."""
        from watchdog.main import ContainerWatchdog

        watchdog = ContainerWatchdog()
        watchdog.docker_client = mock_docker_client

        # Set up initial failure counts
        watchdog.failure_counts = {"existing-service": 1, "removed-service": 2}

        # Mock only existing-service in container list
        existing = MagicMock()
        existing.name = "existing-service"
        mock_docker_client.containers.list.return_value = [existing]

        # Run cleanup
        await watchdog.cleanup_stale_containers()

        # Verify stale container was removed
        assert "existing-service" in watchdog.failure_counts
        assert "removed-service" not in watchdog.failure_counts

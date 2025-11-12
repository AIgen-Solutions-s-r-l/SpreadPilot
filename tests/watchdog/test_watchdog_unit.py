"""
Unit tests for watchdog service.
"""

import json
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add watchdog directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../watchdog"))

from main import ContainerWatchdog


class MockContainer:
    """Mock Docker container"""

    def __init__(self, name, status="running"):
        self.name = name
        self.status = status
        self.attrs = {"NetworkSettings": {"Ports": {"8080/tcp": [{"HostPort": "8080"}]}}}

    def reload(self):
        pass

    def restart(self, timeout=None):
        pass


@pytest.fixture
def mock_docker_client():
    """Mock Docker client"""
    with patch("docker.from_env") as mock:
        client = Mock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client"""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    client = AsyncMock()
    return client


@pytest.fixture
async def watchdog(mock_docker_client, mock_httpx_client, mock_redis_client):
    """Create watchdog instance with mocked dependencies"""
    watchdog = ContainerWatchdog()
    watchdog.http_client = mock_httpx_client
    watchdog.redis_client = mock_redis_client
    return watchdog


class TestContainerWatchdog:
    """Unit tests for ContainerWatchdog class"""

    def test_init(self, mock_docker_client):
        """Test watchdog initialization"""
        watchdog = ContainerWatchdog()
        assert watchdog.docker_client is not None
        assert watchdog.failure_counts == {}
        assert watchdog.monitored_containers == set()

    @pytest.mark.asyncio
    async def test_get_spreadpilot_containers(self, watchdog, mock_docker_client):
        """Test getting containers with spreadpilot label"""
        # Mock containers
        containers = [
            MockContainer("service1"),
            MockContainer("service2"),
        ]
        watchdog.docker_client.containers.list.return_value = containers

        result = watchdog.get_spreadpilot_containers()

        assert len(result) == 2
        watchdog.docker_client.containers.list.assert_called_once_with(
            filters={"label": "spreadpilot", "status": "running"}
        )

    @pytest.mark.asyncio
    async def test_check_container_health_success(self, watchdog):
        """Test successful health check"""
        container = MockContainer("test-service")

        # Mock successful response
        response = Mock()
        response.status_code = 200
        watchdog.http_client.get.return_value = response

        result = await watchdog.check_container_health(container)

        assert result is True
        watchdog.http_client.get.assert_called_once_with("http://test-service:8080/health")

    @pytest.mark.asyncio
    async def test_check_container_health_failure(self, watchdog):
        """Test failed health check"""
        container = MockContainer("test-service")

        # Mock failed response
        response = Mock()
        response.status_code = 503
        watchdog.http_client.get.return_value = response

        result = await watchdog.check_container_health(container)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_container_health_exception(self, watchdog):
        """Test health check with connection error"""
        container = MockContainer("test-service")

        # Mock connection error
        watchdog.http_client.get.side_effect = Exception("Connection refused")

        result = await watchdog.check_container_health(container)

        assert result is False

    def test_restart_container_success(self, watchdog):
        """Test successful container restart"""
        container = Mock()
        container.name = "test-service"
        container.restart.return_value = None

        result = watchdog.restart_container(container)

        assert result is True
        container.restart.assert_called_once_with(timeout=30)

    def test_restart_container_failure(self, watchdog):
        """Test failed container restart"""
        container = Mock()
        container.name = "test-service"
        container.restart.side_effect = Exception("Restart failed")

        result = watchdog.restart_container(container)

        assert result is False

    @pytest.mark.asyncio
    async def test_publish_critical_alert(self, watchdog):
        """Test publishing critical alert to Redis"""
        await watchdog.publish_critical_alert("test-service", "restart", False)

        # Verify Redis xadd was called
        watchdog.redis_client.xadd.assert_called_once()
        call_args = watchdog.redis_client.xadd.call_args

        assert call_args[0][0] == "alerts"
        alert_data = json.loads(call_args[0][1]["alert"])
        assert alert_data["event_type"] == "COMPONENT_DOWN"
        assert "test-service" in alert_data["message"]
        assert alert_data["params"]["severity"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_monitor_container_healthy(self, watchdog):
        """Test monitoring healthy container"""
        container = MockContainer("test-service")

        # Mock healthy response
        response = Mock()
        response.status_code = 200
        watchdog.http_client.get.return_value = response

        await watchdog.monitor_container(container)

        assert watchdog.failure_counts["test-service"] == 0
        watchdog.redis_client.xadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_monitor_container_unhealthy_below_threshold(self, watchdog):
        """Test monitoring unhealthy container below failure threshold"""
        container = MockContainer("test-service")

        # Mock unhealthy response
        response = Mock()
        response.status_code = 503
        watchdog.http_client.get.return_value = response

        await watchdog.monitor_container(container)

        assert watchdog.failure_counts["test-service"] == 1
        # Should not restart or publish alert yet
        watchdog.redis_client.xadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_monitor_container_unhealthy_exceeds_threshold(self, watchdog):
        """Test monitoring unhealthy container that exceeds failure threshold"""
        container = Mock()
        container.name = "test-service"
        container.attrs = {"NetworkSettings": {"Ports": {"8080/tcp": [{"HostPort": "8080"}]}}}
        container.reload = Mock()
        container.restart = Mock()

        # Set failure count to threshold - 1
        watchdog.failure_counts["test-service"] = 2

        # Mock unhealthy response
        response = Mock()
        response.status_code = 503
        watchdog.http_client.get.return_value = response

        await watchdog.monitor_container(container)

        # Should restart container
        container.restart.assert_called_once_with(timeout=30)

        # Should publish alert
        watchdog.redis_client.xadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_monitor_container_recovery(self, watchdog):
        """Test container recovery after failures"""
        container = MockContainer("test-service")

        # Set previous failure count
        watchdog.failure_counts["test-service"] = 2

        # Mock healthy response
        response = Mock()
        response.status_code = 200
        watchdog.http_client.get.return_value = response

        await watchdog.monitor_container(container)

        # Failure count should be reset
        assert watchdog.failure_counts["test-service"] == 0

        # Should publish recovery alert
        watchdog.redis_client.xadd.assert_called_once()
        call_args = watchdog.redis_client.xadd.call_args
        alert_data = json.loads(call_args[0][1]["alert"])
        assert alert_data["event_type"] == "COMPONENT_RECOVERED"

    @pytest.mark.asyncio
    async def test_cleanup_stale_containers(self, watchdog):
        """Test cleanup of stale container failure counts"""
        # Set failure counts for multiple containers
        watchdog.failure_counts = {
            "service1": 1,
            "service2": 2,
            "service3": 3,
        }

        # Mock current containers (service2 removed)
        containers = [
            MockContainer("service1"),
            MockContainer("service3"),
        ]
        watchdog.docker_client.containers.list.return_value = containers

        await watchdog.cleanup_stale_containers()

        # service2 should be removed from failure counts
        assert "service1" in watchdog.failure_counts
        assert "service2" not in watchdog.failure_counts
        assert "service3" in watchdog.failure_counts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

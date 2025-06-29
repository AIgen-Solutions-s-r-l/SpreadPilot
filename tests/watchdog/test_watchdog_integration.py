"""
Integration tests for watchdog service with Docker Compose.
"""

import json
import time
from pathlib import Path

import docker
import pytest
import redis

# Test configuration
COMPOSE_FILE = Path(__file__).parent / "docker-compose.test.yml"
REDIS_URL = "redis://localhost:6379"
UNHEALTHY_SERVICE = "test-unhealthy-service"
WATCHDOG_CONTAINER = "test-watchdog"


@pytest.fixture(scope="module")
def docker_client():
    """Get Docker client"""
    return docker.from_env()


@pytest.fixture(scope="module")
def redis_client():
    """Get Redis client"""
    client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    yield client
    client.close()


@pytest.fixture(scope="module", autouse=True)
def setup_teardown(docker_client):
    """Setup and teardown Docker Compose environment"""
    # Start services
    import subprocess

    compose_dir = Path(__file__).parent
    cmd = ["docker-compose", "-f", str(COMPOSE_FILE), "up", "-d"]
    subprocess.run(cmd, cwd=compose_dir, check=True)

    # Wait for services to be ready
    time.sleep(10)

    yield

    # Teardown
    cmd = ["docker-compose", "-f", str(COMPOSE_FILE), "down", "-v"]
    subprocess.run(cmd, cwd=compose_dir)


def get_container(docker_client, name):
    """Get container by name"""
    try:
        return docker_client.containers.get(name)
    except docker.errors.NotFound:
        return None


def make_service_unhealthy(docker_client, container_name):
    """Make a service unhealthy by creating flag file"""
    container = get_container(docker_client, container_name)
    if container:
        container.exec_run("touch /tmp/unhealthy")
        print(f"Made {container_name} unhealthy")


def make_service_healthy(docker_client, container_name):
    """Make a service healthy by removing flag file"""
    container = get_container(docker_client, container_name)
    if container:
        container.exec_run("rm -f /tmp/unhealthy")
        print(f"Made {container_name} healthy")


def get_alerts_from_redis(redis_client, stream_key="alerts", count=10):
    """Get recent alerts from Redis stream"""
    try:
        # Read last N messages from stream
        messages = redis_client.xrevrange(stream_key, count=count)
        alerts = []
        for msg_id, data in messages:
            if b"alert" in data:
                alert_json = data[b"alert"]
                alert = json.loads(alert_json)
                alerts.append(alert)
        return alerts
    except Exception as e:
        print(f"Error reading alerts: {e}")
        return []


def wait_for_alert(redis_client, container_name, alert_type, timeout=60):
    """Wait for specific alert to appear in Redis"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        alerts = get_alerts_from_redis(redis_client)
        for alert in alerts:
            params = alert.get("params", {})
            if (
                params.get("container_name") == container_name
                and alert.get("event_type") == alert_type
            ):
                return alert
        time.sleep(1)
    return None


class TestWatchdogIntegration:
    """Integration tests for watchdog service"""

    def test_healthy_service_monitoring(self, docker_client, redis_client):
        """Test that healthy services don't trigger alerts"""
        # Ensure healthy-service is running
        container = get_container(docker_client, "test-healthy-service")
        assert container is not None
        assert container.status == "running"

        # Wait for monitoring cycles
        time.sleep(20)

        # Check no alerts for healthy service
        alerts = get_alerts_from_redis(redis_client)
        healthy_alerts = [
            a
            for a in alerts
            if a.get("params", {}).get("container_name") == "test-healthy-service"
        ]

        # Should have no alerts for healthy service
        assert len(healthy_alerts) == 0

    def test_unhealthy_service_restart(self, docker_client, redis_client):
        """Test that unhealthy services get restarted after 3 failures"""
        # Make service unhealthy
        make_service_unhealthy(docker_client, UNHEALTHY_SERVICE)

        # Wait for restart to occur (3 failures × 5 seconds + buffer)
        print("Waiting for service to be detected as unhealthy and restarted...")

        # Look for restart alert
        alert = wait_for_alert(
            redis_client, UNHEALTHY_SERVICE, "COMPONENT_DOWN", timeout=30
        )
        assert alert is not None, "Expected COMPONENT_DOWN alert not found"

        # Verify restart was attempted
        assert alert["params"]["action"] == "restart"
        assert alert["params"]["consecutive_failures"] >= 3

        # Check that container was actually restarted
        container = get_container(docker_client, UNHEALTHY_SERVICE)
        assert container is not None

    def test_service_recovery(self, docker_client, redis_client):
        """Test that recovered services generate recovery alerts"""
        # First make service healthy
        make_service_healthy(docker_client, UNHEALTHY_SERVICE)
        time.sleep(10)

        # Make service unhealthy briefly
        make_service_unhealthy(docker_client, UNHEALTHY_SERVICE)
        time.sleep(10)

        # Make service healthy again
        make_service_healthy(docker_client, UNHEALTHY_SERVICE)

        # Wait for recovery
        print("Waiting for service recovery...")
        alert = wait_for_alert(
            redis_client, UNHEALTHY_SERVICE, "COMPONENT_RECOVERED", timeout=30
        )
        assert alert is not None, "Expected COMPONENT_RECOVERED alert not found"

        # Verify recovery alert
        assert alert["params"]["action"] == "recovery"
        assert alert["params"]["success"] is True

    def test_watchdog_container_discovery(self, docker_client):
        """Test that watchdog discovers containers with spreadpilot label"""
        # Check watchdog logs for discovered containers
        watchdog = get_container(docker_client, WATCHDOG_CONTAINER)
        assert watchdog is not None

        logs = watchdog.logs(tail=100).decode("utf-8")

        # Should discover our test containers
        assert "test-healthy-service" in logs
        assert "test-unhealthy-service" in logs
        assert "test-no-health-service" in logs

    def test_critical_alerts_published(self, docker_client, redis_client):
        """Test that critical alerts are published to Redis"""
        # Clear existing alerts
        redis_client.delete("alerts")

        # Make service unhealthy
        make_service_unhealthy(docker_client, UNHEALTHY_SERVICE)

        # Wait for critical alert
        print("Waiting for critical alert...")
        time.sleep(20)

        alerts = get_alerts_from_redis(redis_client)
        critical_alerts = [
            a for a in alerts if a.get("params", {}).get("severity") == "CRITICAL"
        ]

        assert len(critical_alerts) > 0, "No critical alerts found"

        # Verify alert structure
        alert = critical_alerts[0]
        assert "event_type" in alert
        assert "message" in alert
        assert "params" in alert
        assert alert["params"]["container_name"] == UNHEALTHY_SERVICE


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

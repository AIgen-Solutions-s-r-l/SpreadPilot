"""Integration test for watchdog with unhealthy dummy service."""

import asyncio
import json
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import docker
import fakeredis.aioredis as fakeredis
import pytest

from spreadpilot_core.models.alert import AlertType


class TestWatchdogIntegration(unittest.TestCase):
    """Integration tests for the container watchdog."""

    @classmethod
    def setUpClass(cls):
        """Set up Docker client."""
        cls.docker_client = docker.from_env()
        
    def setUp(self):
        """Set up test environment."""
        self.test_container_name = "test-unhealthy-service"
        self.cleanup_container()
        
    def tearDown(self):
        """Clean up test environment."""
        self.cleanup_container()
        
    def cleanup_container(self):
        """Remove test container if it exists."""
        try:
            container = self.docker_client.containers.get(self.test_container_name)
            container.remove(force=True)
        except docker.errors.NotFound:
            pass
            
    async def test_unhealthy_service_restart(self):
        """Test watchdog restarts unhealthy service after 3 failures."""
        # Import here to avoid import issues
        from main import ContainerWatchdog
        
        # Create unhealthy dummy service with Flask
        # This service will return 503 on /health endpoint
        dockerfile_content = """
FROM python:3.11-alpine
RUN pip install flask
COPY app.py /app.py
CMD ["python", "/app.py"]
"""
        
        app_content = """
from flask import Flask, jsonify
import os

app = Flask(__name__)
call_count = 0

@app.route('/health')
def health():
    global call_count
    call_count += 1
    # Return unhealthy for first 4 calls (to trigger restart)
    if call_count <= 4:
        return jsonify({"status": "unhealthy"}), 503
    # Return healthy after restart
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
"""
        
        # Create temporary directory with Dockerfile and app
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write Dockerfile
            with open(f"{tmpdir}/Dockerfile", "w") as f:
                f.write(dockerfile_content)
                
            # Write Flask app
            with open(f"{tmpdir}/app.py", "w") as f:
                f.write(app_content)
                
            # Build image
            image, _ = self.docker_client.images.build(
                path=tmpdir,
                tag="test-unhealthy:latest",
                rm=True
            )
            
        # Start unhealthy container with spreadpilot label
        container = self.docker_client.containers.run(
            "test-unhealthy:latest",
            name=self.test_container_name,
            labels={"spreadpilot": "true"},
            ports={"8080/tcp": None},  # Random host port
            detach=True,
            auto_remove=False
        )
        
        # Wait for container to start
        await asyncio.sleep(2)
        
        # Create fake Redis for alert capture
        fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)
        
        # Track restart attempts
        restart_called = False
        original_restart = container.restart
        
        def mock_restart(**kwargs):
            nonlocal restart_called
            restart_called = True
            # Actually restart the container
            return original_restart(**kwargs)
            
        container.restart = mock_restart
        
        # Create watchdog with faster intervals for testing
        with patch("main.CHECK_INTERVAL_SECONDS", 2):
            with patch("main.MAX_CONSECUTIVE_FAILURES", 3):
                with patch("redis.asyncio.from_url", return_value=fake_redis):
                    watchdog = ContainerWatchdog()
                    watchdog.redis_client = fake_redis
                    watchdog.http_client = AsyncMock()
                    
                    # Mock HTTP client to simulate health check failures
                    health_check_count = 0
                    
                    async def mock_get(url):
                        nonlocal health_check_count
                        health_check_count += 1
                        
                        response = MagicMock()
                        if health_check_count <= 3:
                            # First 3 checks fail
                            response.status_code = 503
                        else:
                            # After restart, health check succeeds
                            response.status_code = 200
                        return response
                        
                    watchdog.http_client.get = mock_get
                    
                    # Run monitoring for enough cycles to trigger restart
                    monitor_task = asyncio.create_task(watchdog.run())
                    
                    # Wait for 3 failed health checks + restart
                    await asyncio.sleep(8)
                    
                    # Cancel monitoring
                    monitor_task.cancel()
                    try:
                        await monitor_task
                    except asyncio.CancelledError:
                        pass
                        
        # Verify restart was called
        self.assertTrue(restart_called, "Container should have been restarted")
        
        # Verify alerts were published
        alerts = []
        messages = await fake_redis.xrange("alerts", count=10)
        for _, data in messages:
            alert_json = data["alert"]
            alert = json.loads(alert_json)
            alerts.append(alert)
            
        # Should have at least one restart alert
        restart_alerts = [a for a in alerts if "restart" in a["message"]]
        self.assertGreater(len(restart_alerts), 0, "Should have published restart alert")
        
        # Verify the restart alert content
        restart_alert = restart_alerts[0]
        self.assertIn(self.test_container_name, restart_alert["message"])
        self.assertEqual(restart_alert["params"]["action"], "restart")
        self.assertTrue(restart_alert["params"]["success"])
        
    async def test_healthy_service_no_restart(self):
        """Test watchdog doesn't restart healthy services."""
        from main import ContainerWatchdog
        
        # Create healthy dummy service
        dockerfile_content = """
FROM python:3.11-alpine
RUN pip install flask
COPY app.py /app.py
CMD ["python", "/app.py"]
"""
        
        app_content = """
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
"""
        
        # Create temporary directory with Dockerfile and app
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write Dockerfile
            with open(f"{tmpdir}/Dockerfile", "w") as f:
                f.write(dockerfile_content)
                
            # Write Flask app
            with open(f"{tmpdir}/app.py", "w") as f:
                f.write(app_content)
                
            # Build image
            image, _ = self.docker_client.images.build(
                path=tmpdir,
                tag="test-healthy:latest",
                rm=True
            )
            
        # Start healthy container
        container = self.docker_client.containers.run(
            "test-healthy:latest",
            name="test-healthy-service",
            labels={"spreadpilot": "true"},
            ports={"8080/tcp": None},
            detach=True,
            auto_remove=False
        )
        
        try:
            # Wait for container to start
            await asyncio.sleep(2)
            
            # Track restart attempts
            restart_called = False
            original_restart = container.restart
            
            def mock_restart(**kwargs):
                nonlocal restart_called
                restart_called = True
                return original_restart(**kwargs)
                
            container.restart = mock_restart
            
            # Create watchdog
            fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)
            
            with patch("main.CHECK_INTERVAL_SECONDS", 1):
                with patch("redis.asyncio.from_url", return_value=fake_redis):
                    watchdog = ContainerWatchdog()
                    watchdog.redis_client = fake_redis
                    watchdog.http_client = AsyncMock()
                    
                    # Mock successful health checks
                    async def mock_get(url):
                        response = MagicMock()
                        response.status_code = 200
                        return response
                        
                    watchdog.http_client.get = mock_get
                    
                    # Run monitoring for several cycles
                    monitor_task = asyncio.create_task(watchdog.run())
                    await asyncio.sleep(5)
                    
                    # Cancel monitoring
                    monitor_task.cancel()
                    try:
                        await monitor_task
                    except asyncio.CancelledError:
                        pass
                        
            # Verify no restart was called
            self.assertFalse(restart_called, "Healthy container should not be restarted")
            
            # Verify no critical alerts
            messages = await fake_redis.xrange("alerts", count=10)
            self.assertEqual(len(messages), 0, "No alerts should be published for healthy service")
            
        finally:
            # Clean up
            try:
                container.remove(force=True)
            except:
                pass
                
    async def test_container_recovery_alert(self):
        """Test watchdog publishes recovery alert when service becomes healthy."""
        from main import ContainerWatchdog
        
        # Create watchdog
        fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)
        
        # Create mock container
        mock_container = MagicMock()
        mock_container.name = "test-recovery-service"
        
        with patch("redis.asyncio.from_url", return_value=fake_redis):
            watchdog = ContainerWatchdog()
            watchdog.redis_client = fake_redis
            watchdog.http_client = AsyncMock()
            
            # Simulate failing then recovering
            check_count = 0
            
            async def mock_get(url):
                nonlocal check_count
                check_count += 1
                response = MagicMock()
                
                if check_count <= 2:
                    # First 2 checks fail
                    response.status_code = 503
                else:
                    # Then recover
                    response.status_code = 200
                return response
                
            watchdog.http_client.get = mock_get
            
            # Monitor the container through failure and recovery
            for _ in range(3):
                await watchdog.monitor_container(mock_container)
                
        # Check alerts
        messages = await fake_redis.xrange("alerts", count=10)
        alerts = []
        for _, data in messages:
            alert_json = data["alert"]
            alert = json.loads(alert_json)
            alerts.append(alert)
            
        # Should have recovery alert
        recovery_alerts = [a for a in alerts if "recovery" in a["message"]]
        self.assertEqual(len(recovery_alerts), 1, "Should have one recovery alert")
        
        recovery_alert = recovery_alerts[0]
        self.assertEqual(recovery_alert["event_type"], AlertType.COMPONENT_RECOVERED.value)
        self.assertIn("test-recovery-service", recovery_alert["message"])
        self.assertTrue(recovery_alert["params"]["success"])


if __name__ == "__main__":
    # Run async tests
    async def run_tests():
        test_instance = TestWatchdogIntegration()
        test_instance.setUpClass()
        
        try:
            test_instance.setUp()
            print("Testing unhealthy service restart...")
            await test_instance.test_unhealthy_service_restart()
            print("✓ Unhealthy service restart test passed")
            
            test_instance.setUp()
            print("Testing healthy service no restart...")
            await test_instance.test_healthy_service_no_restart()
            print("✓ Healthy service test passed")
            
            test_instance.setUp()
            print("Testing container recovery alert...")
            await test_instance.test_container_recovery_alert()
            print("✓ Recovery alert test passed")
            
            print("\nAll integration tests passed!")
            
        finally:
            test_instance.tearDown()
            
    asyncio.run(run_tests())
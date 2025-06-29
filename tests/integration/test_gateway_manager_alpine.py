"""Integration test for GatewayManager with Alpine container emulating IBGateway."""

import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import docker
import pytest
from ib_insync import IB

from spreadpilot_core.ibkr.gateway_manager import (
    GatewayInstance,
    GatewayManager,
    GatewayStatus,
)
from spreadpilot_core.models.follower import Follower, FollowerState


class TestGatewayManagerIntegration(unittest.TestCase):
    """Integration tests for GatewayManager with Alpine container."""

    @classmethod
    def setUpClass(cls):
        """Set up Docker client."""
        cls.docker_client = docker.from_env()
        
    def setUp(self):
        """Set up test environment."""
        # Create gateway manager with test configuration
        self.gateway_manager = GatewayManager(
            gateway_image="alpine:latest",  # Use Alpine to emulate IBGateway
            port_range_start=5100,
            port_range_end=5200,
            client_id_range_start=9000,
            client_id_range_end=9999,
            container_prefix="test-ibgateway",
            healthcheck_interval=5,  # Faster checks for testing
            max_startup_time=30,
            vault_enabled=False,  # Disable Vault for testing
        )
        
        # Mock MongoDB
        self.mock_db = {
            "followers": AsyncMock()
        }
        
        # Test follower
        self.test_follower = Follower(
            id="test-follower-123",
            name="Test Follower",
            email="test@example.com",
            enabled=True,
            state=FollowerState.ACTIVE,
            ibkr_username="test_user",
            strategy="vertical_spreads",
        )
        
    def tearDown(self):
        """Clean up test environment."""
        # Stop any running test containers
        try:
            containers = self.docker_client.containers.list(
                filters={"name": "test-ibgateway-*"}
            )
            for container in containers:
                container.remove(force=True)
        except Exception:
            pass
            
    async def test_alpine_container_lifecycle(self):
        """Test container lifecycle with Alpine container."""
        # Mock MongoDB connection
        with patch("spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=self.mock_db):
            # Mock follower query
            self.mock_db["followers"].find = MagicMock(return_value=MockAsyncIterator([]))
            
            # Start gateway manager
            await self.gateway_manager.start()
            
            # Create Alpine container that simulates IBGateway
            container_name = f"test-ibgateway-{self.test_follower.id}"
            
            # Remove any existing container
            try:
                existing = self.docker_client.containers.get(container_name)
                existing.remove(force=True)
            except docker.errors.NotFound:
                pass
                
            # Start Alpine container with netcat listening on port 4002
            container = self.docker_client.containers.run(
                "alpine:latest",
                name=container_name,
                command="sh -c 'apk add --no-cache netcat-openbsd && nc -l -k -p 4002'",
                ports={"4002/tcp": 5101},
                detach=True,
                auto_remove=False,
            )
            
            # Wait for container to start
            await asyncio.sleep(2)
            
            # Create gateway instance
            gateway = GatewayInstance(
                follower_id=self.test_follower.id,
                container_id=container.id,
                host_port=5101,
                client_id=9001,
                status=GatewayStatus.STARTING,
                container=container,
            )
            
            self.gateway_manager.gateways[self.test_follower.id] = gateway
            
            # Test health check
            current_time = time.time()
            await self.gateway_manager._check_gateway_health(gateway, current_time)
            
            # Container should be detected as running
            container.reload()
            self.assertEqual(container.status, "running")
            
            # Test reconnection by killing the container
            container.kill()
            await asyncio.sleep(1)
            
            # Health check should detect container stopped
            await self.gateway_manager._check_gateway_health(gateway, time.time())
            self.assertEqual(gateway.status, GatewayStatus.STOPPED)
            
            # Clean up
            await self.gateway_manager.stop()
            
            # Verify container is removed
            with self.assertRaises(docker.errors.NotFound):
                self.docker_client.containers.get(container_name)
                
    async def test_reconnection_logic(self):
        """Test IB client reconnection logic."""
        # Mock IB client
        mock_ib = MagicMock(spec=IB)
        mock_ib.isConnected = MagicMock(return_value=False)
        mock_ib.connectAsync = AsyncMock()
        mock_ib.managedAccounts = MagicMock(return_value=["DU123456"])
        
        # Create gateway instance
        gateway = GatewayInstance(
            follower_id="test-follower",
            container_id="test-container",
            host_port=5102,
            client_id=9002,
            status=GatewayStatus.RUNNING,
            ib_client=mock_ib,
        )
        
        # Mock IB constructor
        with patch("spreadpilot_core.ibkr.gateway_manager.IB", return_value=mock_ib):
            # Test reconnection
            result = await self.gateway_manager._connect_ib_client(gateway)
            
            # Verify connection attempt
            mock_ib.connectAsync.assert_called_once_with(
                host="localhost",
                port=5102,
                clientId=9002,
                timeout=10,
            )
            
            # Verify managed accounts check
            mock_ib.managedAccounts.assert_called_once()
            
    async def test_clean_shutdown(self):
        """Test clean shutdown of gateway manager."""
        # Mock MongoDB and monitoring task
        with patch("spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=self.mock_db):
            self.mock_db["followers"].find = MagicMock(return_value=MockAsyncIterator([]))
            
            # Start gateway manager
            await self.gateway_manager.start()
            
            # Add a mock gateway
            mock_container = MagicMock()
            mock_container.stop = MagicMock()
            mock_container.wait = MagicMock()
            mock_container.remove = MagicMock()
            
            mock_ib_client = MagicMock()
            mock_ib_client.disconnect = MagicMock()
            
            gateway = GatewayInstance(
                follower_id="test-follower",
                container_id="test-container",
                host_port=5103,
                client_id=9003,
                status=GatewayStatus.RUNNING,
                container=mock_container,
                ib_client=mock_ib_client,
            )
            
            self.gateway_manager.gateways["test-follower"] = gateway
            self.gateway_manager.used_ports.add(5103)
            self.gateway_manager.used_client_ids.add(9003)
            
            # Stop gateway manager
            await self.gateway_manager.stop()
            
            # Verify shutdown sequence
            mock_ib_client.disconnect.assert_called_once()
            mock_container.stop.assert_called_once_with(timeout=30)
            mock_container.wait.assert_called_once()
            mock_container.remove.assert_called_once()
            
            # Verify resources cleaned up
            self.assertEqual(len(self.gateway_manager.gateways), 0)
            self.assertNotIn(5103, self.gateway_manager.used_ports)
            self.assertNotIn(9003, self.gateway_manager.used_client_ids)
            self.assertTrue(self.gateway_manager._shutdown)
            
    async def test_heartbeat_monitoring(self):
        """Test heartbeat monitoring loop."""
        # Create a mock gateway
        mock_container = MagicMock()
        mock_container.reload = MagicMock()
        mock_container.status = "running"
        
        gateway = GatewayInstance(
            follower_id="test-follower",
            container_id="test-container",
            host_port=5104,
            client_id=9004,
            status=GatewayStatus.RUNNING,
            container=mock_container,
        )
        
        self.gateway_manager.gateways["test-follower"] = gateway
        self.gateway_manager.healthcheck_interval = 0.5  # Fast checks for testing
        
        # Track health checks
        health_check_count = 0
        original_check = self.gateway_manager._check_gateway_health
        
        async def mock_check_health(gw, time):
            nonlocal health_check_count
            health_check_count += 1
            await original_check(gw, time)
            
        self.gateway_manager._check_gateway_health = mock_check_health
        
        # Start monitoring
        monitor_task = asyncio.create_task(self.gateway_manager._monitor_gateways())
        
        # Let it run for a bit
        await asyncio.sleep(1.5)
        
        # Stop monitoring
        self.gateway_manager._shutdown = True
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
            
        # Verify health checks were performed
        self.assertGreaterEqual(health_check_count, 2)
        

class MockAsyncIterator:
    """Mock async iterator for MongoDB cursor."""
    
    def __init__(self, items):
        self.items = items
        self.index = 0
        
    def __aiter__(self):
        return self
        
    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


if __name__ == "__main__":
    # Run async tests
    async def run_tests():
        test_instance = TestGatewayManagerIntegration()
        test_instance.setUpClass()
        
        try:
            test_instance.setUp()
            print("Testing Alpine container lifecycle...")
            await test_instance.test_alpine_container_lifecycle()
            print("✓ Alpine container lifecycle test passed")
            
            test_instance.setUp()
            print("Testing reconnection logic...")
            await test_instance.test_reconnection_logic()
            print("✓ Reconnection logic test passed")
            
            test_instance.setUp()
            print("Testing clean shutdown...")
            await test_instance.test_clean_shutdown()
            print("✓ Clean shutdown test passed")
            
            test_instance.setUp()
            print("Testing heartbeat monitoring...")
            await test_instance.test_heartbeat_monitoring()
            print("✓ Heartbeat monitoring test passed")
            
            print("\nAll integration tests passed!")
            
        finally:
            test_instance.tearDown()
            
    asyncio.run(run_tests())
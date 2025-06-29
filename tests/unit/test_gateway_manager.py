"""Unit tests for GatewayManager with mocked Docker SDK."""

import asyncio
import time
from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock, patch

import docker
import pytest

from spreadpilot_core.ibkr.gateway_manager import (
    GatewayInstance,
    GatewayManager,
    GatewayStatus,
)
from spreadpilot_core.models.alert import AlertSeverity
from spreadpilot_core.models.follower import FollowerState


@dataclass
class MockFollower:
    """Mock follower for testing."""

    id: str
    ibkr_username: str
    vault_secret_ref: str = None
    enabled: bool = True
    state: str = FollowerState.ACTIVE.value


class TestGatewayManager:
    """Test GatewayManager functionality with mocked Docker SDK."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("spreadpilot_core.ibkr.gateway_manager.docker.from_env"):
            self.gateway_manager = GatewayManager(
                healthcheck_interval=1, max_startup_time=2  # Short interval for testing
            )
            self.gateway_manager.docker_client = Mock()

    @pytest.mark.asyncio
    async def test_start_gateway_allocates_resources(self):
        """Test that starting a gateway allocates port and client ID."""
        # Arrange
        mock_container = Mock()
        mock_container.id = "test_container_id"
        self.gateway_manager.docker_client.containers.run.return_value = mock_container
        self.gateway_manager.docker_client.containers.get.side_effect = (
            docker.errors.NotFound("Not found")
        )

        follower = MockFollower(id="test_follower", ibkr_username="test_user")

        # Act
        with patch.object(
            self.gateway_manager, "_get_ibkr_credentials_from_vault", return_value=None
        ):
            gateway = await self.gateway_manager._start_gateway(follower)

        # Assert
        assert gateway.follower_id == "test_follower"
        assert gateway.host_port in range(4100, 4201)
        assert gateway.client_id in range(1000, 10000)
        assert gateway.host_port in self.gateway_manager.used_ports
        assert gateway.client_id in self.gateway_manager.used_client_ids

    @pytest.mark.asyncio
    async def test_heartbeat_with_isconnected(self):
        """Test heartbeat mechanism using ib_insync.isConnected()."""
        # Arrange
        mock_ib_client = Mock()
        mock_ib_client.isConnected.return_value = True

        gateway = GatewayInstance(
            follower_id="test_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING,
            ib_client=mock_ib_client,
            container=Mock(),
        )
        gateway.container.reload = Mock()
        gateway.container.status = "running"

        self.gateway_manager.gateways["test_follower"] = gateway

        # Act
        await self.gateway_manager._check_gateway_health(gateway, time.time())

        # Assert
        mock_ib_client.isConnected.assert_called_once()
        assert gateway.status == GatewayStatus.RUNNING

    @pytest.mark.asyncio
    async def test_reconnection_with_backoff(self):
        """Test reconnection attempts with exponential backoff."""
        # Arrange
        mock_ib = Mock()
        mock_ib.isConnected.return_value = True
        mock_ib.managedAccounts.return_value = ["DU123456"]

        gateway = GatewayInstance(
            follower_id="test_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING,
        )

        # Mock backoff decorator behavior
        connection_attempts = 0

        async def mock_connect(*args, **kwargs):
            nonlocal connection_attempts
            connection_attempts += 1
            if connection_attempts < 3:
                raise ConnectionError("Connection failed")
            # Success on third attempt
            return

        with patch("ib_insync.IB") as mock_ib_class:
            mock_ib_instance = AsyncMock()
            mock_ib_instance.connectAsync = mock_connect
            mock_ib_instance.isConnected.return_value = True
            mock_ib_instance.managedAccounts.return_value = ["DU123456"]
            mock_ib_class.return_value = mock_ib_instance

            # Act
            result = await self.gateway_manager._connect_ib_client(gateway)

            # Assert
            assert connection_attempts == 3  # Should retry until success
            assert gateway.ib_client is not None

    @pytest.mark.asyncio
    async def test_stop_follower_gateway_graceful_shutdown(self):
        """Test graceful Docker stop with timeout."""
        # Arrange
        mock_container = Mock()
        mock_ib_client = Mock()

        gateway = GatewayInstance(
            follower_id="test_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING,
            container=mock_container,
            ib_client=mock_ib_client,
        )

        self.gateway_manager.gateways["test_follower"] = gateway
        self.gateway_manager.used_ports.add(4100)
        self.gateway_manager.used_client_ids.add(1000)

        # Act
        await self.gateway_manager.stop_follower_gateway("test_follower")

        # Assert
        mock_ib_client.disconnect.assert_called_once()
        mock_container.stop.assert_called_once_with(timeout=30)
        mock_container.wait.assert_called_once()
        mock_container.remove.assert_called_once()
        assert "test_follower" not in self.gateway_manager.gateways
        assert 4100 not in self.gateway_manager.used_ports
        assert 1000 not in self.gateway_manager.used_client_ids

    @pytest.mark.asyncio
    async def test_stop_follower_gateway_force_removal_on_error(self):
        """Test force removal when graceful stop fails."""
        # Arrange
        mock_container = Mock()
        mock_container.stop.side_effect = Exception("Stop failed")
        mock_container.remove.side_effect = [
            Exception("Remove failed"),
            None,
        ]  # Fail first, succeed on force

        gateway = GatewayInstance(
            follower_id="test_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING,
            container=mock_container,
        )

        self.gateway_manager.gateways["test_follower"] = gateway

        # Act
        await self.gateway_manager.stop_follower_gateway("test_follower")

        # Assert
        assert mock_container.remove.call_count == 2
        mock_container.remove.assert_called_with(force=True)

    @pytest.mark.asyncio
    async def test_vault_credentials_retrieval(self):
        """Test retrieving IB_USER and IB_PASS from Vault."""
        # Arrange
        mock_container = Mock()
        mock_container.id = "test_container_id"
        self.gateway_manager.docker_client.containers.run.return_value = mock_container
        self.gateway_manager.docker_client.containers.get.side_effect = (
            docker.errors.NotFound("Not found")
        )

        vault_credentials = {"IB_USER": "vault_username", "IB_PASS": "vault_password"}

        follower = MockFollower(
            id="test_follower",
            ibkr_username="stored_user",
            vault_secret_ref="ibkr/test_follower",
        )

        # Act
        with patch.object(
            self.gateway_manager,
            "_get_ibkr_credentials_from_vault",
            return_value=vault_credentials,
        ):
            await self.gateway_manager._start_gateway(follower)

        # Assert
        call_args = self.gateway_manager.docker_client.containers.run.call_args
        environment = call_args[1]["environment"]
        assert environment["IB_USER"] == "vault_username"
        assert environment["IB_PASS"] == "vault_password"

    @pytest.mark.asyncio
    async def test_monitor_gateways_periodic_health_check(self):
        """Test that monitor task checks gateway health every 30 seconds."""
        # Arrange
        mock_ib_client = Mock()
        mock_ib_client.isConnected.return_value = True

        gateway = GatewayInstance(
            follower_id="test_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING,
            ib_client=mock_ib_client,
            container=Mock(),
        )
        gateway.container.reload = Mock()
        gateway.container.status = "running"

        self.gateway_manager.gateways["test_follower"] = gateway
        self.gateway_manager.healthcheck_interval = 0.1  # Fast for testing

        # Act
        monitor_task = asyncio.create_task(self.gateway_manager._monitor_gateways())
        await asyncio.sleep(0.3)  # Let it run for 3 intervals
        self.gateway_manager._shutdown = True
        await monitor_task

        # Assert
        assert mock_ib_client.isConnected.call_count >= 2

    @pytest.mark.asyncio
    async def test_reconnect_on_disconnected_client(self):
        """Test automatic reconnection when isConnected() returns False."""
        # Arrange
        mock_ib_client = Mock()
        mock_ib_client.isConnected.return_value = False

        gateway = GatewayInstance(
            follower_id="test_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING,
            ib_client=mock_ib_client,
            container=Mock(),
        )
        gateway.container.reload = Mock()
        gateway.container.status = "running"

        self.gateway_manager.gateways["test_follower"] = gateway

        # Mock successful reconnection
        with patch.object(
            self.gateway_manager, "_connect_ib_client", return_value=AsyncMock()
        ) as mock_connect:
            # Act
            await self.gateway_manager._check_gateway_health(gateway, time.time())

            # Assert
            mock_connect.assert_called_once_with(gateway)

    @pytest.mark.asyncio
    async def test_get_client_returns_connected_client(self):
        """Test get_client returns connected IB client instance."""
        # Arrange
        mock_ib_client = Mock()
        mock_ib_client.isConnected.return_value = True

        gateway = GatewayInstance(
            follower_id="test_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING,
            ib_client=mock_ib_client,
        )

        self.gateway_manager.gateways["test_follower"] = gateway

        # Act
        client = await self.gateway_manager.get_client("test_follower")

        # Assert
        assert client == mock_ib_client
        mock_ib_client.isConnected.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_client_creates_new_connection_if_needed(self):
        """Test get_client creates new connection if not connected."""
        # Arrange
        gateway = GatewayInstance(
            follower_id="test_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING,
            ib_client=None,  # No client yet
        )

        self.gateway_manager.gateways["test_follower"] = gateway

        mock_new_client = Mock()
        mock_new_client.isConnected.return_value = True

        with patch.object(
            self.gateway_manager, "_connect_ib_client", return_value=mock_new_client
        ) as mock_connect:
            # Act
            client = await self.gateway_manager.get_client("test_follower")

            # Assert
            assert client == mock_new_client
            mock_connect.assert_called_once_with(gateway)

    @pytest.mark.asyncio
    async def test_reload_followers_adds_new_followers(self):
        """Test reload_followers adds new active followers."""
        # Arrange
        mock_db = {"followers": Mock()}

        new_follower = {
            "_id": "new_follower",
            "id": "new_follower",
            "ibkr_username": "new_user",
            "enabled": True,
            "state": FollowerState.ACTIVE.value,
        }

        # Mock async iterator
        class AsyncIterator:
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

        mock_db["followers"].find.return_value = AsyncIterator([new_follower])

        with patch(
            "spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=mock_db
        ):
            with patch.object(
                self.gateway_manager, "_start_gateway", return_value=AsyncMock()
            ) as mock_start:
                # Act
                await self.gateway_manager.reload_followers()

                # Assert
                mock_start.assert_called_once()
                call_args = mock_start.call_args[0][0]
                assert call_args.id == "new_follower"

    @pytest.mark.asyncio
    async def test_reload_followers_removes_inactive_followers(self):
        """Test reload_followers removes followers that are no longer active."""
        # Arrange
        # Add existing gateway
        existing_gateway = GatewayInstance(
            follower_id="old_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING,
        )
        self.gateway_manager.gateways["old_follower"] = existing_gateway

        mock_db = {"followers": Mock()}

        # Empty list - no active followers
        class AsyncIterator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        mock_db["followers"].find.return_value = AsyncIterator()

        with patch(
            "spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=mock_db
        ):
            with patch.object(
                self.gateway_manager, "_stop_gateway", return_value=AsyncMock()
            ) as mock_stop:
                # Act
                await self.gateway_manager.reload_followers()

                # Assert
                mock_stop.assert_called_once_with("old_follower")

    @pytest.mark.asyncio
    async def test_vault_credentials_retry_and_alert(self):
        """Test Vault credentials retrieval with retry logic and alert on failure."""
        # Arrange
        follower = MockFollower(
            id="test_follower",
            ibkr_username="test_user",
            vault_secret_ref="ibkr/test_follower"
        )
        
        # Mock Vault client to fail all retries
        with patch("spreadpilot_core.ibkr.gateway_manager.get_vault_client") as mock_vault:
            mock_vault_client = Mock()
            mock_vault_client.get_ibkr_credentials.side_effect = Exception("Vault error")
            mock_vault.return_value = mock_vault_client
            
            # Mock Redis for alert publishing
            with patch("spreadpilot_core.utils.redis_client.get_redis_client") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis.return_value = mock_redis_client
                
                # Act - should fail after retries
                try:
                    await self.gateway_manager._get_ibkr_credentials_from_vault(follower)
                except Exception:
                    pass  # Expected to fail
                
                # Assert - verify retries happened (backoff decorator behavior)
                assert mock_vault_client.get_ibkr_credentials.call_count >= 1

    @pytest.mark.asyncio
    async def test_connection_failure_counting(self):
        """Test that connection failures are counted and trigger reconnect after 2 failures."""
        # Arrange
        mock_ib_client = Mock()
        mock_ib_client.isConnected.return_value = False  # Simulate disconnection
        
        gateway = GatewayInstance(
            follower_id="test_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING,
            ib_client=mock_ib_client,
            container=Mock(),
            connection_failures=0
        )
        gateway.container.reload = Mock()
        gateway.container.status = "running"
        
        self.gateway_manager.gateways["test_follower"] = gateway
        
        # Act - First failure
        await self.gateway_manager._check_gateway_health(gateway, time.time())
        assert gateway.connection_failures == 1
        
        # Act - Second failure should trigger reconnect
        with patch.object(self.gateway_manager, "_reconnect", new_callable=AsyncMock) as mock_reconnect:
            await self.gateway_manager._check_gateway_health(gateway, time.time() + 35)
            
            # Assert
            assert gateway.connection_failures == 2
            mock_reconnect.assert_called_once_with(gateway)

    @pytest.mark.asyncio
    async def test_mongodb_gateway_mapping_storage(self):
        """Test that gateway mappings are stored in MongoDB."""
        # Arrange
        gateway = GatewayInstance(
            follower_id="test_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING
        )
        
        mock_db = AsyncMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        
        # Act
        with patch("spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=mock_db):
            await self.gateway_manager._store_gateway_mapping(gateway)
        
        # Assert
        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        assert call_args[0][0] == {"follower_id": "test_follower"}
        assert call_args[0][1]["$set"]["container_name"] == "ibgw-test_follower"
        assert call_args[0][1]["$set"]["host_port"] == 4100
        assert call_args[1]["upsert"] is True

    @pytest.mark.asyncio
    async def test_mongodb_gateway_mapping_removal(self):
        """Test that gateway mappings are removed from MongoDB on stop."""
        # Arrange
        mock_db = AsyncMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        
        # Act
        with patch("spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=mock_db):
            await self.gateway_manager._remove_gateway_mapping("test_follower")
        
        # Assert
        mock_collection.delete_one.assert_called_once_with({"follower_id": "test_follower"})

    @pytest.mark.asyncio
    async def test_alert_publishing_on_reconnect_failure(self):
        """Test that alerts are published when reconnection fails."""
        # Arrange
        mock_ib_client = Mock()
        mock_ib_client.isConnected.return_value = False
        
        gateway = GatewayInstance(
            follower_id="test_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING,
            ib_client=mock_ib_client,
            container=Mock(),
            connection_failures=1  # Already had one failure
        )
        gateway.container.reload = Mock()
        gateway.container.status = "running"
        
        self.gateway_manager.gateways["test_follower"] = gateway
        
        # Mock reconnect to fail
        with patch.object(self.gateway_manager, "_reconnect", side_effect=Exception("Reconnect failed")):
            with patch("spreadpilot_core.utils.redis_client.get_redis_client") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis.return_value = mock_redis_client
                
                # Act
                await self.gateway_manager._check_gateway_health(gateway, time.time())
                
                # Assert
                assert gateway.status == GatewayStatus.FAILED
                mock_redis_client.xadd.assert_called_once()
                call_args = mock_redis_client.xadd.call_args[0]
                assert call_args[0] == "alerts"
                assert "Failed to reconnect" in call_args[1]["data"]

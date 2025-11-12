"""Simplified unit tests for GatewayManager core functionality."""

# Mock all the dependencies before importing
import sys
from dataclasses import dataclass
from unittest.mock import Mock, patch

import pytest

sys.modules["docker"] = Mock()
sys.modules["ib_insync"] = Mock()
sys.modules["motor"] = Mock()
sys.modules["motor.motor_asyncio"] = Mock()

from spreadpilot_core.ibkr.gateway_manager import (
    GatewayInstance,
    GatewayManager,
    GatewayStatus,
)


@dataclass
class MockFollower:
    """Mock follower for testing."""

    id: str
    ibkr_username: str
    vault_secret_ref: str = None


class TestGatewayManagerCore:
    """Test core GatewayManager functionality."""

    def test_gateway_instance_creation(self):
        """Test GatewayInstance dataclass creation."""
        gateway = GatewayInstance(
            follower_id="test_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.STARTING,
        )

        assert gateway.follower_id == "test_follower"
        assert gateway.container_id == "test_container"
        assert gateway.host_port == 4100
        assert gateway.client_id == 1000
        assert gateway.status == GatewayStatus.STARTING
        assert gateway.container is None
        assert gateway.ib_client is None
        assert gateway.last_healthcheck is None

    def test_gateway_status_enum(self):
        """Test GatewayStatus enum values."""
        assert GatewayStatus.STARTING.value == "STARTING"
        assert GatewayStatus.RUNNING.value == "RUNNING"
        assert GatewayStatus.STOPPED.value == "STOPPED"
        assert GatewayStatus.FAILED.value == "FAILED"

    @patch("spreadpilot_core.ibkr.gateway_manager.docker.from_env")
    def test_gateway_manager_initialization(self, mock_docker):
        """Test GatewayManager initialization."""
        mock_docker.return_value = Mock()

        manager = GatewayManager(
            gateway_image="test:latest",
            port_range_start=5000,
            port_range_end=5100,
            client_id_range_start=2000,
            client_id_range_end=2999,
            container_prefix="test-prefix",
            healthcheck_interval=60,
            max_startup_time=300,
            vault_enabled=False,
        )

        assert manager.gateway_image == "test:latest"
        assert manager.port_range_start == 5000
        assert manager.port_range_end == 5100
        assert manager.client_id_range_start == 2000
        assert manager.client_id_range_end == 2999
        assert manager.container_prefix == "test-prefix"
        assert manager.healthcheck_interval == 60
        assert manager.max_startup_time == 300
        assert manager.vault_enabled is False
        assert manager.gateways == {}
        assert len(manager.used_ports) == 0
        assert len(manager.used_client_ids) == 0

    @patch("spreadpilot_core.ibkr.gateway_manager.docker.from_env")
    def test_allocate_port(self, mock_docker):
        """Test port allocation."""
        mock_docker.return_value = Mock()

        manager = GatewayManager(port_range_start=4100, port_range_end=4102)

        # Allocate first port
        port1 = manager._allocate_port()
        assert port1 == 4100
        assert port1 in manager.used_ports

        # Allocate second port
        port2 = manager._allocate_port()
        assert port2 == 4101
        assert port2 in manager.used_ports

        # Allocate third port
        port3 = manager._allocate_port()
        assert port3 == 4102
        assert port3 in manager.used_ports

        # No more ports available
        with pytest.raises(RuntimeError, match="No available ports"):
            manager._allocate_port()

    @patch("spreadpilot_core.ibkr.gateway_manager.docker.from_env")
    def test_allocate_client_id(self, mock_docker):
        """Test client ID allocation."""
        mock_docker.return_value = Mock()

        manager = GatewayManager(client_id_range_start=1000, client_id_range_end=1002)

        # Mock random to return predictable values
        with patch("spreadpilot_core.ibkr.gateway_manager.random.randint") as mock_randint:
            mock_randint.side_effect = [1000, 1001, 1002, 1000, 1001, 1002] * 20

            # Allocate IDs
            id1 = manager._allocate_client_id()
            assert id1 == 1000
            assert id1 in manager.used_client_ids

            id2 = manager._allocate_client_id()
            assert id2 == 1001
            assert id2 in manager.used_client_ids

            id3 = manager._allocate_client_id()
            assert id3 == 1002
            assert id3 in manager.used_client_ids

    @patch("spreadpilot_core.ibkr.gateway_manager.docker.from_env")
    def test_get_gateway_status(self, mock_docker):
        """Test getting gateway status."""
        mock_docker.return_value = Mock()

        manager = GatewayManager()

        # No gateway exists
        status = manager.get_gateway_status("unknown_follower")
        assert status is None

        # Add a gateway
        gateway = GatewayInstance(
            follower_id="test_follower",
            container_id="test_container",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING,
        )
        manager.gateways["test_follower"] = gateway

        # Get status
        status = manager.get_gateway_status("test_follower")
        assert status == GatewayStatus.RUNNING

    @patch("spreadpilot_core.ibkr.gateway_manager.docker.from_env")
    def test_list_gateways(self, mock_docker):
        """Test listing gateways."""
        mock_docker.return_value = Mock()

        manager = GatewayManager()

        # Empty list
        gateways = manager.list_gateways()
        assert gateways == {}

        # Add gateways
        mock_ib_client = Mock()
        mock_ib_client.isConnected.return_value = True

        gateway1 = GatewayInstance(
            follower_id="follower1",
            container_id="container1",
            host_port=4100,
            client_id=1000,
            status=GatewayStatus.RUNNING,
            ib_client=mock_ib_client,
        )

        gateway2 = GatewayInstance(
            follower_id="follower2",
            container_id="container2",
            host_port=4101,
            client_id=1001,
            status=GatewayStatus.STARTING,
        )

        manager.gateways["follower1"] = gateway1
        manager.gateways["follower2"] = gateway2

        # List gateways
        gateways = manager.list_gateways()

        assert len(gateways) == 2
        assert gateways["follower1"]["status"] == "RUNNING"
        assert gateways["follower1"]["host_port"] == 4100
        assert gateways["follower1"]["client_id"] == 1000
        assert gateways["follower1"]["connected"] is True

        assert gateways["follower2"]["status"] == "STARTING"
        assert gateways["follower2"]["host_port"] == 4101
        assert gateways["follower2"]["client_id"] == 1001
        assert gateways["follower2"]["connected"] is False

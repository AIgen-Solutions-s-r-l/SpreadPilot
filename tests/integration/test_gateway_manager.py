"""Integration tests for GatewayManager."""

import asyncio
import time
from unittest.mock import MagicMock, patch

import docker
import pytest

from spreadpilot_core.ibkr.gateway_manager import (
    GatewayManager,
    GatewayStatus,
)
from spreadpilot_core.models.follower import FollowerState


class MockContainer:
    """Mock Docker container for testing."""

    def __init__(self, container_id: str, name: str, status: str = "running"):
        self.id = container_id
        self.name = name
        self.status = status
        self.attrs = {"Created": time.time() - 10}  # Container created 10 seconds ago
        self._removed = False

    def reload(self):
        """Reload container status."""
        pass

    def stop(self, timeout: int = 10):
        """Stop the container."""
        self.status = "exited"

    def remove(self, force: bool = False):
        """Remove the container."""
        self._removed = True


class MockDockerClient:
    """Mock Docker client for testing."""

    def __init__(self):
        self.containers = MagicMock()
        self._containers: dict[str, MockContainer] = {}

        # Configure containers.run to create mock containers
        self.containers.run.side_effect = self._create_container
        self.containers.get.side_effect = self._get_container

    def _create_container(self, image: str, **kwargs) -> MockContainer:
        """Create a mock container."""
        name = kwargs.get("name", f"container-{len(self._containers)}")
        container_id = f"mock-{name}-{len(self._containers)}"

        container = MockContainer(container_id, name)
        self._containers[name] = container

        return container

    def _get_container(self, name: str) -> MockContainer:
        """Get a container by name."""
        if name in self._containers:
            return self._containers[name]
        raise docker.errors.NotFound(f"Container {name} not found")


class MockIBClient:
    """Mock IB client that simulates gateway connection."""

    def __init__(self, should_connect: bool = True, should_echo: bool = True):
        self.should_connect = should_connect
        self.should_echo = should_echo
        self._connected = False
        self._managed_accounts = ["U1234567"] if should_connect else []

    async def connectAsync(
        self, host: str, port: int, clientId: int, timeout: int = 10
    ):
        """Mock connection to gateway."""
        if self.should_connect:
            self._connected = True
            if self.should_echo:
                print(f"API client connected to {host}:{port} with clientId {clientId}")
        else:
            raise ConnectionError("Mock connection failed")

    def isConnected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    def disconnect(self):
        """Disconnect the client."""
        self._connected = False

    def managedAccounts(self) -> list:
        """Return managed accounts."""
        return self._managed_accounts


@pytest.fixture
async def mock_db():
    """Mock MongoDB database with test followers."""
    followers_data = [
        {
            "_id": "follower-1",
            "email": "test1@example.com",
            "iban": "DE89370400440532013000",
            "ibkr_username": "testuser1",
            "ibkr_secret_ref": "secret-ref-1",
            "commission_pct": 2.5,
            "enabled": True,
            "state": FollowerState.ACTIVE.value,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        },
        {
            "_id": "follower-2",
            "email": "test2@example.com",
            "iban": "DE89370400440532013001",
            "ibkr_username": "testuser2",
            "ibkr_secret_ref": "secret-ref-2",
            "commission_pct": 3.0,
            "enabled": True,
            "state": FollowerState.ACTIVE.value,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        },
        {
            "_id": "follower-3",
            "email": "test3@example.com",
            "iban": "DE89370400440532013002",
            "ibkr_username": "testuser3",
            "ibkr_secret_ref": "secret-ref-3",
            "commission_pct": 1.5,
            "enabled": False,  # Disabled follower
            "state": FollowerState.DISABLED.value,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        },
    ]

    # Create mock collection with async iteration
    mock_collection = MagicMock()

    async def mock_find(*args, **kwargs):
        """Mock find operation that returns enabled followers."""
        query = args[0] if args else {}
        enabled = query.get("enabled", None)
        state = query.get("state", None)

        # Filter followers based on query
        filtered_data = []
        for follower in followers_data:
            if enabled is not None and follower["enabled"] != enabled:
                continue
            if state is not None and follower["state"] != state:
                continue
            filtered_data.append(follower)

        # Create async iterator
        class AsyncIterator:
            def __init__(self, data):
                self.data = data
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.data):
                    raise StopAsyncIteration
                item = self.data[self.index]
                self.index += 1
                return item

        return AsyncIterator(filtered_data)

    mock_collection.find.side_effect = mock_find

    # Mock database
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    return mock_db


@pytest.fixture
def mock_docker_client():
    """Mock Docker client."""
    return MockDockerClient()


@pytest.fixture
async def gateway_manager(mock_docker_client):
    """Create a GatewayManager instance for testing."""
    with patch(
        "spreadpilot_core.ibkr.gateway_manager.docker.from_env",
        return_value=mock_docker_client,
    ):
        manager = GatewayManager(
            port_range_start=4100,
            port_range_end=4110,
            client_id_range_start=1000,
            client_id_range_end=1010,
            healthcheck_interval=1,  # Fast healthchecks for testing
            max_startup_time=5,
        )
        yield manager

        # Cleanup
        if not manager._shutdown:
            await manager.stop()


@pytest.mark.asyncio
async def test_gateway_manager_start_with_enabled_followers(gateway_manager, mock_db):
    """Test that the gateway manager starts containers for enabled followers."""

    with patch(
        "spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=mock_db
    ):
        with patch(
            "spreadpilot_core.ibkr.gateway_manager.IB", return_value=MockIBClient()
        ):
            await gateway_manager.start()

            # Should have started 2 gateways (follower-1 and follower-2)
            assert len(gateway_manager.gateways) == 2
            assert "follower-1" in gateway_manager.gateways
            assert "follower-2" in gateway_manager.gateways
            assert "follower-3" not in gateway_manager.gateways  # Disabled

            # Check gateway instances
            gateway1 = gateway_manager.gateways["follower-1"]
            assert gateway1.follower_id == "follower-1"
            assert 4100 <= gateway1.host_port <= 4110
            assert 1000 <= gateway1.client_id <= 1010
            assert gateway1.status == GatewayStatus.STARTING

            gateway2 = gateway_manager.gateways["follower-2"]
            assert gateway2.follower_id == "follower-2"
            assert gateway1.host_port != gateway2.host_port  # Different ports
            assert gateway1.client_id != gateway2.client_id  # Different client IDs


@pytest.mark.asyncio
async def test_get_client_returns_connected_ib_instance(
    gateway_manager, mock_db, capsys
):
    """Test that get_client returns a connected IB instance with echo message."""

    with patch(
        "spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=mock_db
    ):
        with patch(
            "spreadpilot_core.ibkr.gateway_manager.IB",
            return_value=MockIBClient(should_echo=True),
        ):
            await gateway_manager.start()

            # Wait a moment for gateway to start
            await asyncio.sleep(0.1)

            # Set gateway status to running (simulate successful startup)
            gateway_manager.gateways["follower-1"].status = GatewayStatus.RUNNING

            # Get client
            client = await gateway_manager.get_client("follower-1")

            assert client is not None
            assert client.isConnected()

            # Check that echo message was printed
            captured = capsys.readouterr()
            assert "API client connected" in captured.out


@pytest.mark.asyncio
async def test_get_client_returns_none_for_non_existent_follower(
    gateway_manager, mock_db
):
    """Test that get_client returns None for non-existent follower."""

    with patch(
        "spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=mock_db
    ):
        with patch(
            "spreadpilot_core.ibkr.gateway_manager.IB", return_value=MockIBClient()
        ):
            await gateway_manager.start()

            client = await gateway_manager.get_client("non-existent-follower")
            assert client is None


@pytest.mark.asyncio
async def test_get_client_returns_none_for_stopped_gateway(gateway_manager, mock_db):
    """Test that get_client returns None when gateway is not running."""

    with patch(
        "spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=mock_db
    ):
        with patch(
            "spreadpilot_core.ibkr.gateway_manager.IB", return_value=MockIBClient()
        ):
            await gateway_manager.start()

            # Set gateway status to stopped
            gateway_manager.gateways["follower-1"].status = GatewayStatus.STOPPED

            client = await gateway_manager.get_client("follower-1")
            assert client is None


@pytest.mark.asyncio
async def test_connection_retry_with_exponential_backoff(gateway_manager, mock_db):
    """Test that connection failures trigger exponential backoff retry."""

    # Create a mock that fails twice then succeeds
    call_count = 0

    def create_mock_client():
        nonlocal call_count
        call_count += 1
        return MockIBClient(should_connect=call_count >= 3)  # Fail first 2 attempts

    with patch(
        "spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=mock_db
    ):
        with patch(
            "spreadpilot_core.ibkr.gateway_manager.IB", side_effect=create_mock_client
        ):
            await gateway_manager.start()

            # Set gateway status to running
            gateway_manager.gateways["follower-1"].status = GatewayStatus.RUNNING

            # This should eventually succeed after retries
            client = await gateway_manager.get_client("follower-1")

            assert client is not None
            assert client.isConnected()
            assert call_count >= 3  # At least 3 attempts were made


@pytest.mark.asyncio
async def test_reload_followers_adds_new_enabled_follower(gateway_manager, mock_db):
    """Test that reload_followers starts gateway for newly enabled follower."""

    with patch(
        "spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=mock_db
    ):
        with patch(
            "spreadpilot_core.ibkr.gateway_manager.IB", return_value=MockIBClient()
        ):
            await gateway_manager.start()

            # Initially should have 2 gateways
            assert len(gateway_manager.gateways) == 2

            # Mock the database to return follower-3 as now enabled
            async def mock_find_updated(*args, **kwargs):
                updated_data = [
                    {
                        "_id": "follower-1",
                        "email": "test1@example.com",
                        "iban": "DE89370400440532013000",
                        "ibkr_username": "testuser1",
                        "ibkr_secret_ref": "secret-ref-1",
                        "commission_pct": 2.5,
                        "enabled": True,
                        "state": FollowerState.ACTIVE.value,
                        "created_at": "2023-01-01T00:00:00Z",
                        "updated_at": "2023-01-01T00:00:00Z",
                    },
                    {
                        "_id": "follower-3",  # Now enabled
                        "email": "test3@example.com",
                        "iban": "DE89370400440532013002",
                        "ibkr_username": "testuser3",
                        "ibkr_secret_ref": "secret-ref-3",
                        "commission_pct": 1.5,
                        "enabled": True,
                        "state": FollowerState.ACTIVE.value,
                        "created_at": "2023-01-01T00:00:00Z",
                        "updated_at": "2023-01-01T00:00:00Z",
                    },
                ]

                class AsyncIterator:
                    def __init__(self, data):
                        self.data = data
                        self.index = 0

                    def __aiter__(self):
                        return self

                    async def __anext__(self):
                        if self.index >= len(self.data):
                            raise StopAsyncIteration
                        item = self.data[self.index]
                        self.index += 1
                        return item

                return AsyncIterator(updated_data)

            # Update the mock to return new data
            mock_db["followers"].find.side_effect = mock_find_updated

            # Reload followers
            await gateway_manager.reload_followers()

            # Should now have follower-1 and follower-3, but not follower-2
            assert len(gateway_manager.gateways) == 2
            assert "follower-1" in gateway_manager.gateways
            assert "follower-3" in gateway_manager.gateways
            assert "follower-2" not in gateway_manager.gateways


@pytest.mark.asyncio
async def test_gateway_status_and_listing(gateway_manager, mock_db):
    """Test gateway status reporting and listing functionality."""

    with patch(
        "spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=mock_db
    ):
        with patch(
            "spreadpilot_core.ibkr.gateway_manager.IB", return_value=MockIBClient()
        ):
            await gateway_manager.start()

            # Test status reporting
            status1 = gateway_manager.get_gateway_status("follower-1")
            assert status1 == GatewayStatus.STARTING

            status_none = gateway_manager.get_gateway_status("non-existent")
            assert status_none is None

            # Test gateway listing
            gateways_list = gateway_manager.list_gateways()
            assert len(gateways_list) == 2
            assert "follower-1" in gateways_list
            assert "follower-2" in gateways_list

            # Check gateway info structure
            gateway_info = gateways_list["follower-1"]
            assert "status" in gateway_info
            assert "host_port" in gateway_info
            assert "client_id" in gateway_info
            assert "container_id" in gateway_info
            assert "connected" in gateway_info

            assert gateway_info["status"] == GatewayStatus.STARTING.value
            assert isinstance(gateway_info["host_port"], int)
            assert isinstance(gateway_info["client_id"], int)
            assert isinstance(gateway_info["connected"], bool)


@pytest.mark.asyncio
async def test_manager_stop_cleans_up_resources(gateway_manager, mock_db):
    """Test that stopping the manager cleans up all resources."""

    with patch(
        "spreadpilot_core.ibkr.gateway_manager.get_mongo_db", return_value=mock_db
    ):
        with patch(
            "spreadpilot_core.ibkr.gateway_manager.IB", return_value=MockIBClient()
        ):
            await gateway_manager.start()

            # Verify gateways are running
            assert len(gateway_manager.gateways) == 2
            initial_ports = {gw.host_port for gw in gateway_manager.gateways.values()}
            initial_client_ids = {
                gw.client_id for gw in gateway_manager.gateways.values()
            }

            # Stop the manager
            await gateway_manager.stop()

            # Verify cleanup
            assert len(gateway_manager.gateways) == 0
            assert gateway_manager._shutdown is True
            assert len(gateway_manager.used_ports) == 0
            assert len(gateway_manager.used_client_ids) == 0


@pytest.mark.asyncio
async def test_port_and_client_id_allocation(gateway_manager):
    """Test port and client ID allocation logic."""

    # Test port allocation
    port1 = gateway_manager._allocate_port()
    port2 = gateway_manager._allocate_port()

    assert 4100 <= port1 <= 4110
    assert 4100 <= port2 <= 4110
    assert port1 != port2
    assert port1 in gateway_manager.used_ports
    assert port2 in gateway_manager.used_ports

    # Test client ID allocation
    client_id1 = gateway_manager._allocate_client_id()
    client_id2 = gateway_manager._allocate_client_id()

    assert 1000 <= client_id1 <= 1010
    assert 1000 <= client_id2 <= 1010
    assert client_id1 != client_id2
    assert client_id1 in gateway_manager.used_client_ids
    assert client_id2 in gateway_manager.used_client_ids


@pytest.mark.asyncio
async def test_resource_exhaustion_raises_runtime_error(gateway_manager):
    """Test that resource exhaustion raises appropriate errors."""

    # Exhaust all ports
    for _ in range(11):  # Port range is 4100-4110 (11 ports)
        try:
            gateway_manager._allocate_port()
        except RuntimeError:
            break

    # Next allocation should fail
    with pytest.raises(RuntimeError, match="No available ports"):
        gateway_manager._allocate_port()

    # Reset for client ID test
    gateway_manager.used_client_ids.clear()

    # Exhaust all client IDs
    for _ in range(11):  # Client ID range is 1000-1010 (11 IDs)
        try:
            gateway_manager._allocate_client_id()
        except RuntimeError:
            break

    # Next allocation should fail
    with pytest.raises(RuntimeError, match="No available client IDs"):
        gateway_manager._allocate_client_id()

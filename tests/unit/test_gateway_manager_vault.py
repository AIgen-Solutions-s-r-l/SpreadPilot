"""Unit tests for GatewayManager Vault integration."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock, patch

import pytest
from spreadpilot_core.ibkr.gateway_manager import GatewayManager, GatewayStatus
from spreadpilot_core.models.follower import FollowerState


@dataclass
class MockFollower:
    """Mock follower for testing."""

    id: str
    ibkr_username: str
    vault_secret_ref: str = None
    enabled: bool = True
    state: str = FollowerState.ACTIVE.value


class TestGatewayManagerVaultIntegration:
    """Test GatewayManager Vault integration."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("spreadpilot_core.ibkr.gateway_manager.docker.from_env"):
            self.gateway_manager = GatewayManager(vault_enabled=True)
            self.gateway_manager.docker_client = Mock()

    @pytest.mark.asyncio
    @patch("spreadpilot_core.ibkr.gateway_manager.get_vault_client")
    async def test_get_ibkr_credentials_from_vault_success(self, mock_get_vault_client):
        """Test successful credential retrieval from Vault."""
        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.return_value = {
            "IB_USER": "vault_user",
            "IB_PASS": "vault_pass",
        }
        mock_get_vault_client.return_value = mock_vault_client

        follower = MockFollower(
            id="test_follower",
            ibkr_username="test_user",
            vault_secret_ref="ibkr/test",
        )

        unwrapped = type(self.gateway_manager)._get_ibkr_credentials_from_vault.__wrapped__
        result = await unwrapped(self.gateway_manager, follower)

        assert result == {"IB_USER": "vault_user", "IB_PASS": "vault_pass"}
        mock_vault_client.get_ibkr_credentials.assert_called_once_with("ibkr/test")

    @pytest.mark.asyncio
    @patch("spreadpilot_core.ibkr.gateway_manager.get_vault_client")
    async def test_get_ibkr_credentials_from_vault_not_found(self, mock_get_vault_client):
        """Test credential retrieval when not found in Vault."""
        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.return_value = None
        mock_get_vault_client.return_value = mock_vault_client

        follower = MockFollower(
            id="test_follower",
            ibkr_username="test_user",
            vault_secret_ref="ibkr/test",
        )

        with patch.object(self.gateway_manager, "_publish_alert", new_callable=AsyncMock):
            unwrapped = type(self.gateway_manager)._get_ibkr_credentials_from_vault.__wrapped__
            result = await unwrapped(self.gateway_manager, follower)

        assert result is None

    @pytest.mark.asyncio
    @patch("spreadpilot_core.ibkr.gateway_manager.get_vault_client")
    async def test_get_ibkr_credentials_from_vault_error(self, mock_get_vault_client):
        """Test credential retrieval when Vault throws error raises after retries."""
        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.side_effect = Exception("Vault connection error")
        mock_get_vault_client.return_value = mock_vault_client

        follower = MockFollower(
            id="test_follower",
            ibkr_username="test_user",
            vault_secret_ref="ibkr/test",
        )

        unwrapped = type(self.gateway_manager)._get_ibkr_credentials_from_vault.__wrapped__
        with pytest.raises(Exception, match="Vault connection error"):
            await unwrapped(self.gateway_manager, follower)

    @pytest.mark.asyncio
    async def test_get_ibkr_credentials_from_vault_disabled(self):
        """Test credential retrieval when Vault is disabled returns None."""
        with patch("spreadpilot_core.ibkr.gateway_manager.docker.from_env"):
            gateway_manager = GatewayManager(vault_enabled=False)

        follower = MockFollower(id="test_follower", ibkr_username="test_user")

        unwrapped = type(gateway_manager)._get_ibkr_credentials_from_vault.__wrapped__
        result = await unwrapped(gateway_manager, follower)

        assert result is None

    @pytest.mark.asyncio
    async def test_start_gateway_with_vault_credentials(self):
        """Test starting gateway with valid Vault credentials."""
        import docker as docker_lib

        mock_container = Mock()
        mock_container.id = "test_container_id"
        self.gateway_manager.docker_client.containers.run.return_value = mock_container
        self.gateway_manager.docker_client.containers.get.side_effect = docker_lib.errors.NotFound(
            "Not found"
        )

        follower = MockFollower(
            id="test_follower",
            ibkr_username="stored_user",
            vault_secret_ref="ibkr/test_follower",
        )

        with (
            patch.object(
                self.gateway_manager,
                "_get_ibkr_credentials_from_vault",
                new_callable=AsyncMock,
                return_value={"IB_USER": "vault_user", "IB_PASS": "vault_pass"},
            ),
            patch.object(self.gateway_manager, "_store_gateway_mapping", new_callable=AsyncMock),
        ):
            gateway = await self.gateway_manager._start_gateway(follower)

        assert gateway.follower_id == "test_follower"
        assert gateway.status == GatewayStatus.STARTING

        call_args = self.gateway_manager.docker_client.containers.run.call_args
        environment = call_args[1]["environment"]
        assert environment["IB_USER"] == "vault_user"
        assert environment["IB_PASS"] == "vault_pass"

    @pytest.mark.asyncio
    async def test_start_gateway_vault_returns_none_raises(self):
        """Test that _start_gateway raises when Vault returns no credentials."""
        follower = MockFollower(
            id="test_follower",
            ibkr_username="stored_user",
            vault_secret_ref="ibkr/test_follower",
        )

        with (
            patch.object(
                self.gateway_manager,
                "_get_ibkr_credentials_from_vault",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(self.gateway_manager, "_publish_alert", new_callable=AsyncMock),
        ):
            with pytest.raises(ValueError, match="Failed to retrieve Vault credentials"):
                await self.gateway_manager._start_gateway(follower)

    @pytest.mark.asyncio
    async def test_start_gateway_no_vault_secret_ref_raises(self):
        """Test that _start_gateway raises when follower has no vault_secret_ref."""
        follower = MockFollower(id="test_follower", ibkr_username="stored_user")

        with patch.object(self.gateway_manager, "_publish_alert", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="Failed to retrieve Vault credentials"):
                await self.gateway_manager._start_gateway(follower)

    @pytest.mark.asyncio
    async def test_start_gateway_vault_disabled_raises(self):
        """Test that _start_gateway raises when Vault is disabled (no credentials available)."""
        with patch("spreadpilot_core.ibkr.gateway_manager.docker.from_env"):
            gateway_manager = GatewayManager(vault_enabled=False)
            gateway_manager.docker_client = Mock()

        follower = MockFollower(
            id="test_follower",
            ibkr_username="stored_user",
            vault_secret_ref="ibkr/test_follower",
        )

        with patch.object(gateway_manager, "_publish_alert", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="Failed to retrieve Vault credentials"):
                await gateway_manager._start_gateway(follower)


class TestGatewayManagerVaultConfiguration:
    """Test GatewayManager Vault configuration."""

    @patch("spreadpilot_core.ibkr.gateway_manager.docker.from_env")
    def test_gateway_manager_vault_enabled_by_default(self, _mock_docker):
        """Test that Vault is enabled by default."""
        gateway_manager = GatewayManager()
        assert gateway_manager.vault_enabled is True

    @patch("spreadpilot_core.ibkr.gateway_manager.docker.from_env")
    def test_gateway_manager_vault_can_be_disabled(self, _mock_docker):
        """Test that Vault can be disabled."""
        gateway_manager = GatewayManager(vault_enabled=False)
        assert gateway_manager.vault_enabled is False

    @patch("spreadpilot_core.ibkr.gateway_manager.docker.from_env")
    def test_gateway_manager_other_parameters_unchanged(self, _mock_docker):
        """Test that other parameters work normally with Vault integration."""
        gateway_manager = GatewayManager(
            gateway_image="custom:latest",
            port_range_start=5000,
            port_range_end=5100,
            vault_enabled=False,
        )

        assert gateway_manager.gateway_image == "custom:latest"
        assert gateway_manager.port_range_start == 5000
        assert gateway_manager.port_range_end == 5100
        assert gateway_manager.vault_enabled is False

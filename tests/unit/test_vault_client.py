"""Unit tests for Vault client utilities."""

from unittest.mock import Mock, patch

import pytest
from hvac.exceptions import VaultError

from spreadpilot_core.utils.vault import (
    VaultClient,
    get_ibkr_credentials_from_vault,
    get_vault_client,
)


class TestVaultClient:
    """Test VaultClient class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.vault_client = VaultClient(
            vault_url="http://test-vault:8200",
            vault_token="test-token",
            mount_point="test-secret",
            verify_ssl=False,
        )

    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_client_property_creates_authenticated_client(self, mock_hvac_client):
        """Test that client property creates and authenticates client."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client_instance

        # Act
        client = self.vault_client.client

        # Assert
        mock_hvac_client.assert_called_once_with(
            url="http://test-vault:8200", token="test-token", verify=False
        )
        mock_client_instance.is_authenticated.assert_called_once()
        assert client == mock_client_instance

    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_client_property_raises_error_when_not_authenticated(self, mock_hvac_client):
        """Test that client property raises error when not authenticated."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = False
        mock_hvac_client.return_value = mock_client_instance

        # Act & Assert
        with pytest.raises(VaultError, match="Vault authentication failed"):
            _ = self.vault_client.client

    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_get_secret_success(self, mock_hvac_client):
        """Test successful secret retrieval."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = True
        mock_client_instance.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"IB_USER": "test_user", "IB_PASS": "test_pass"}}
        }
        mock_hvac_client.return_value = mock_client_instance

        # Act
        result = self.vault_client.get_secret("test/path")

        # Assert
        assert result == {"IB_USER": "test_user", "IB_PASS": "test_pass"}
        mock_client_instance.secrets.kv.v2.read_secret_version.assert_called_once_with(
            path="test/path", mount_point="test-secret"
        )

    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_get_secret_with_key(self, mock_hvac_client):
        """Test secret retrieval with specific key."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = True
        mock_client_instance.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"IB_USER": "test_user", "IB_PASS": "test_pass"}}
        }
        mock_hvac_client.return_value = mock_client_instance

        # Act
        result = self.vault_client.get_secret("test/path", "IB_USER")

        # Assert
        assert result == "test_user"

    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_get_secret_returns_none_on_error(self, mock_hvac_client):
        """Test that get_secret returns None on error."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = True
        mock_client_instance.secrets.kv.v2.read_secret_version.side_effect = Exception(
            "Vault error"
        )
        mock_hvac_client.return_value = mock_client_instance

        # Act
        result = self.vault_client.get_secret("test/path")

        # Assert
        assert result is None

    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_get_ibkr_credentials_success(self, mock_hvac_client):
        """Test successful IBKR credentials retrieval."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = True
        mock_client_instance.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"IB_USER": "test_user", "IB_PASS": "test_pass"}}
        }
        mock_hvac_client.return_value = mock_client_instance

        # Act
        result = self.vault_client.get_ibkr_credentials("ibkr/test")

        # Assert
        assert result == {"IB_USER": "test_user", "IB_PASS": "test_pass"}

    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_get_ibkr_credentials_alternative_keys(self, mock_hvac_client):
        """Test IBKR credentials retrieval with alternative key names."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = True
        mock_client_instance.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"username": "test_user", "password": "test_pass"}}
        }
        mock_hvac_client.return_value = mock_client_instance

        # Act
        result = self.vault_client.get_ibkr_credentials("ibkr/test")

        # Assert
        assert result == {"IB_USER": "test_user", "IB_PASS": "test_pass"}

    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_get_ibkr_credentials_missing_keys(self, mock_hvac_client):
        """Test IBKR credentials retrieval with missing keys."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = True
        mock_client_instance.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"some_other_key": "value"}}
        }
        mock_hvac_client.return_value = mock_client_instance

        # Act
        result = self.vault_client.get_ibkr_credentials("ibkr/test")

        # Assert
        assert result is None

    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_put_secret_success(self, mock_hvac_client):
        """Test successful secret storage."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client_instance

        secret_data = {"IB_USER": "test_user", "IB_PASS": "test_pass"}

        # Act
        result = self.vault_client.put_secret("test/path", secret_data)

        # Assert
        assert result is True
        mock_client_instance.secrets.kv.v2.create_or_update_secret.assert_called_once_with(
            path="test/path", secret=secret_data, mount_point="test-secret"
        )

    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_put_secret_failure(self, mock_hvac_client):
        """Test secret storage failure."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = True
        mock_client_instance.secrets.kv.v2.create_or_update_secret.side_effect = Exception(
            "Vault error"
        )
        mock_hvac_client.return_value = mock_client_instance

        secret_data = {"IB_USER": "test_user", "IB_PASS": "test_pass"}

        # Act
        result = self.vault_client.put_secret("test/path", secret_data)

        # Assert
        assert result is False

    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_health_check_healthy(self, mock_hvac_client):
        """Test health check when Vault is healthy."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = True
        mock_client_instance.sys.read_health_status.return_value = {
            "initialized": True,
            "sealed": False,
        }
        mock_hvac_client.return_value = mock_client_instance

        # Act
        result = self.vault_client.health_check()

        # Assert
        assert result is True

    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_health_check_unhealthy(self, mock_hvac_client):
        """Test health check when Vault is unhealthy."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = True
        mock_client_instance.sys.read_health_status.return_value = {
            "initialized": False,
            "sealed": True,
        }
        mock_hvac_client.return_value = mock_client_instance

        # Act
        result = self.vault_client.health_check()

        # Assert
        assert result is False

    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_health_check_error(self, mock_hvac_client):
        """Test health check when there's an error."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = True
        mock_client_instance.sys.read_health_status.side_effect = Exception("Connection error")
        mock_hvac_client.return_value = mock_client_instance

        # Act
        result = self.vault_client.health_check()

        # Assert
        assert result is False


class TestVaultUtilityFunctions:
    """Test Vault utility functions."""

    @patch("spreadpilot_core.utils.vault.VaultClient")
    def test_get_vault_client_cached(self, mock_vault_client_class):
        """Test that get_vault_client returns cached instance."""
        # Clear cache first
        get_vault_client.cache_clear()

        # Arrange
        mock_instance = Mock()
        mock_vault_client_class.return_value = mock_instance

        # Act
        client1 = get_vault_client()
        client2 = get_vault_client()

        # Assert
        assert client1 == client2
        mock_vault_client_class.assert_called_once()

    @patch("spreadpilot_core.utils.vault.get_vault_client")
    def test_get_ibkr_credentials_from_vault(self, mock_get_vault_client):
        """Test convenience function for getting IBKR credentials."""
        # Arrange
        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.return_value = {
            "IB_USER": "test_user",
            "IB_PASS": "test_pass",
        }
        mock_get_vault_client.return_value = mock_vault_client

        # Act
        result = get_ibkr_credentials_from_vault("ibkr/test")

        # Assert
        assert result == {"IB_USER": "test_user", "IB_PASS": "test_pass"}
        mock_vault_client.get_ibkr_credentials.assert_called_once_with("ibkr/test")


class TestVaultEnvironmentVariables:
    """Test Vault client with environment variables."""

    @patch.dict(
        "os.environ",
        {"VAULT_ADDR": "http://env-vault:8200", "VAULT_TOKEN": "env-token"},
    )
    @patch("spreadpilot_core.utils.vault.hvac.Client")
    def test_vault_client_uses_environment_variables(self, mock_hvac_client):
        """Test that VaultClient uses environment variables when no params provided."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client_instance

        # Act
        vault_client = VaultClient()
        _ = vault_client.client

        # Assert
        mock_hvac_client.assert_called_once_with(
            url="http://env-vault:8200", token="env-token", verify=True
        )
        assert vault_client.vault_url == "http://env-vault:8200"
        assert vault_client.vault_token == "env-token"

"""Unit tests for trading-bot config Vault integration."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

# Add trading-bot to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "trading-bot"))

from app.config import Settings


class TestSettingsVaultIntegration:
    """Test Settings class Vault integration."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create settings with test values
        self.settings = Settings(
            google_sheet_url="https://docs.google.com/spreadsheets/test",
            vault_url="http://test-vault:8200",
            vault_token="test-token",
            vault_mount_point="test-secret",
            vault_enabled=True,
        )

    def test_vault_configuration_defaults(self):
        """Test Vault configuration default values."""
        settings = Settings(google_sheet_url="https://docs.google.com/spreadsheets/test")

        assert settings.vault_url == "http://vault:8200"
        assert settings.vault_token == "dev-only-token"
        assert settings.vault_mount_point == "secret"
        assert settings.vault_enabled is True

    @patch.dict(
        "os.environ",
        {
            "VAULT_ADDR": "http://env-vault:8200",
            "VAULT_TOKEN": "env-token",
            "VAULT_MOUNT_POINT": "env-secret",
            "VAULT_ENABLED": "false",
        },
    )
    def test_vault_configuration_from_environment(self):
        """Test Vault configuration from environment variables."""
        settings = Settings(google_sheet_url="https://docs.google.com/spreadsheets/test")

        assert settings.vault_url == "http://env-vault:8200"
        assert settings.vault_token == "env-token"
        assert settings.vault_mount_point == "env-secret"
        assert settings.vault_enabled is False

    @patch("app.config.get_vault_client")
    def test_get_ibkr_credentials_from_vault_success(self, mock_get_vault_client):
        """Test successful IBKR credentials retrieval from Vault."""
        # Arrange
        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.return_value = {
            "IB_USER": "vault_user",
            "IB_PASS": "vault_pass",
        }
        mock_get_vault_client.return_value = mock_vault_client

        # Act
        result = self.settings.get_ibkr_credentials_from_vault("ibkr/test")

        # Assert
        assert result == {"IB_USER": "vault_user", "IB_PASS": "vault_pass"}

        # Verify that client configuration was updated
        assert mock_vault_client.vault_url == self.settings.vault_url
        assert mock_vault_client.vault_token == self.settings.vault_token
        assert mock_vault_client.mount_point == self.settings.vault_mount_point
        assert mock_vault_client._client is None  # Client was reset

        mock_vault_client.get_ibkr_credentials.assert_called_once_with("ibkr/test")

    @patch("app.config.get_vault_client")
    def test_get_ibkr_credentials_from_vault_not_found(self, mock_get_vault_client):
        """Test IBKR credentials retrieval when not found in Vault."""
        # Arrange
        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.return_value = None
        mock_get_vault_client.return_value = mock_vault_client

        # Act
        result = self.settings.get_ibkr_credentials_from_vault("ibkr/test")

        # Assert
        assert result is None

    @patch("app.config.get_vault_client")
    def test_get_ibkr_credentials_from_vault_error(self, mock_get_vault_client):
        """Test IBKR credentials retrieval when Vault throws error."""
        # Arrange
        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.side_effect = Exception("Vault connection error")
        mock_get_vault_client.return_value = mock_vault_client

        # Act
        result = self.settings.get_ibkr_credentials_from_vault("ibkr/test")

        # Assert
        assert result is None

    def test_get_ibkr_credentials_from_vault_disabled(self):
        """Test IBKR credentials retrieval when Vault is disabled."""
        # Arrange
        settings = Settings(
            google_sheet_url="https://docs.google.com/spreadsheets/test",
            vault_enabled=False,
        )

        # Act
        result = settings.get_ibkr_credentials_from_vault("ibkr/test")

        # Assert
        assert result is None

    @patch("app.config.get_vault_client")
    def test_vault_client_configuration_override(self, mock_get_vault_client):
        """Test that Settings properly configures the Vault client."""
        # Arrange
        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.return_value = {
            "IB_USER": "test_user",
            "IB_PASS": "test_pass",
        }
        mock_get_vault_client.return_value = mock_vault_client

        custom_settings = Settings(
            google_sheet_url="https://docs.google.com/spreadsheets/test",
            vault_url="http://custom-vault:8200",
            vault_token="custom-token",
            vault_mount_point="custom-secret",
        )

        # Act
        result = custom_settings.get_ibkr_credentials_from_vault("ibkr/test")

        # Assert
        assert result == {"IB_USER": "test_user", "IB_PASS": "test_pass"}

        # Verify client was configured with custom settings
        assert mock_vault_client.vault_url == "http://custom-vault:8200"
        assert mock_vault_client.vault_token == "custom-token"
        assert mock_vault_client.mount_point == "custom-secret"

    def test_trading_mode_validation_unchanged(self):
        """Test that trading mode validation still works with Vault integration."""
        # Test valid trading mode
        settings = Settings(
            google_sheet_url="https://docs.google.com/spreadsheets/test",
            ib_trading_mode="paper",
        )
        assert settings.ib_trading_mode == "paper"

        # Test invalid trading mode should raise ValidationError
        with pytest.raises(ValidationError):
            Settings(
                google_sheet_url="https://docs.google.com/spreadsheets/test",
                ib_trading_mode="invalid",
            )


class TestSettingsIntegrationWithStrategies:
    """Test Settings integration with strategy configurations."""

    @patch("app.config.get_vault_client")
    def test_vertical_spreads_strategy_vault_integration(self, mock_get_vault_client):
        """Test that vertical spreads strategy configuration can work with Vault."""
        # Arrange
        from app.config import VERTICAL_SPREADS_STRATEGY

        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.return_value = {
            "IB_USER": "spreads_user",
            "IB_PASS": "spreads_pass",
        }
        mock_get_vault_client.return_value = mock_vault_client

        settings = Settings(google_sheet_url="https://docs.google.com/spreadsheets/test")

        # Act - Get credentials for vertical spreads strategy
        result = settings.get_ibkr_credentials_from_vault(
            VERTICAL_SPREADS_STRATEGY["ibkr_secret_ref"]
        )

        # Assert
        assert result == {"IB_USER": "spreads_user", "IB_PASS": "spreads_pass"}
        mock_vault_client.get_ibkr_credentials.assert_called_once_with(
            "ibkr_vertical_spreads_strategy"
        )


class TestSettingsBackwardCompatibility:
    """Test that Settings maintains backward compatibility."""

    def test_existing_configuration_unchanged(self):
        """Test that existing configuration fields are unchanged."""
        settings = Settings(
            google_sheet_url="https://docs.google.com/spreadsheets/test",
            project_id="test-project",
            ib_gateway_host="127.0.0.1",
            ib_gateway_port=4002,
            ib_client_id=1,
            ib_trading_mode="paper",
            min_price=0.70,
            price_increment=0.01,
            max_attempts=10,
            timeout_seconds=5,
            polling_interval_seconds=1.0,
            position_check_interval_seconds=60.0,
        )

        # Verify all existing fields work
        assert settings.project_id == "test-project"
        assert settings.ib_gateway_host == "127.0.0.1"
        assert settings.ib_gateway_port == 4002
        assert settings.ib_client_id == 1
        assert settings.ib_trading_mode == "paper"
        assert settings.min_price == 0.70
        assert settings.price_increment == 0.01
        assert settings.max_attempts == 10
        assert settings.timeout_seconds == 5
        assert settings.polling_interval_seconds == 1.0
        assert settings.position_check_interval_seconds == 60.0

    def test_configuration_with_and_without_vault(self):
        """Test that configuration works both with and without Vault."""
        # Without Vault
        settings_no_vault = Settings(
            google_sheet_url="https://docs.google.com/spreadsheets/test",
            vault_enabled=False,
        )
        assert settings_no_vault.vault_enabled is False

        # With Vault
        settings_with_vault = Settings(
            google_sheet_url="https://docs.google.com/spreadsheets/test",
            vault_enabled=True,
        )
        assert settings_with_vault.vault_enabled is True

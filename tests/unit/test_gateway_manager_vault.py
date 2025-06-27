"""Unit tests for GatewayManager Vault integration."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from spreadpilot_core.ibkr.gateway_manager import GatewayManager, GatewayStatus
from spreadpilot_core.models.follower import Follower


@dataclass
class MockFollower:
    """Mock follower for testing."""
    id: str
    ibkr_username: str
    vault_secret_ref: str = None


class TestGatewayManagerVaultIntegration:
    """Test GatewayManager Vault integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.gateway_manager = GatewayManager(vault_enabled=True)
    
    @patch('spreadpilot_core.ibkr.gateway_manager.get_vault_client')
    def test_get_ibkr_credentials_from_vault_success(self, mock_get_vault_client):
        """Test successful credential retrieval from Vault."""
        # Arrange
        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.return_value = {
            "IB_USER": "vault_user",
            "IB_PASS": "vault_pass"
        }
        mock_get_vault_client.return_value = mock_vault_client
        
        # Act
        result = self.gateway_manager._get_ibkr_credentials_from_vault("ibkr/test")
        
        # Assert
        assert result == {"IB_USER": "vault_user", "IB_PASS": "vault_pass"}
        mock_vault_client.get_ibkr_credentials.assert_called_once_with("ibkr/test")
    
    @patch('spreadpilot_core.ibkr.gateway_manager.get_vault_client')
    def test_get_ibkr_credentials_from_vault_not_found(self, mock_get_vault_client):
        """Test credential retrieval when not found in Vault."""
        # Arrange
        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.return_value = None
        mock_get_vault_client.return_value = mock_vault_client
        
        # Act
        result = self.gateway_manager._get_ibkr_credentials_from_vault("ibkr/test")
        
        # Assert
        assert result is None
    
    @patch('spreadpilot_core.ibkr.gateway_manager.get_vault_client')
    def test_get_ibkr_credentials_from_vault_error(self, mock_get_vault_client):
        """Test credential retrieval when Vault throws error."""
        # Arrange
        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.side_effect = Exception("Vault connection error")
        mock_get_vault_client.return_value = mock_vault_client
        
        # Act
        result = self.gateway_manager._get_ibkr_credentials_from_vault("ibkr/test")
        
        # Assert
        assert result is None
    
    def test_get_ibkr_credentials_from_vault_disabled(self):
        """Test credential retrieval when Vault is disabled."""
        # Arrange
        gateway_manager = GatewayManager(vault_enabled=False)
        
        # Act
        result = gateway_manager._get_ibkr_credentials_from_vault("ibkr/test")
        
        # Assert
        assert result is None
    
    @patch('spreadpilot_core.ibkr.gateway_manager.docker.from_env')
    @patch('spreadpilot_core.ibkr.gateway_manager.get_vault_client')
    def test_start_gateway_with_vault_credentials(self, mock_get_vault_client, mock_docker):
        """Test starting gateway with Vault credentials."""
        # Arrange
        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.return_value = {
            "IB_USER": "vault_user",
            "IB_PASS": "vault_pass"
        }
        mock_get_vault_client.return_value = mock_vault_client
        
        mock_docker_client = Mock()
        mock_container = Mock()
        mock_container.id = "test_container_id"
        mock_docker_client.containers.run.return_value = mock_container
        mock_docker_client.containers.get.side_effect = Exception("Not found")  # No existing container
        mock_docker.return_value = mock_docker_client
        
        follower = MockFollower(
            id="test_follower",
            ibkr_username="stored_user",
            vault_secret_ref="ibkr/test_follower"
        )
        
        # Mock port and client ID allocation
        with patch.object(self.gateway_manager, '_allocate_port', return_value=4100), \
             patch.object(self.gateway_manager, '_allocate_client_id', return_value=1000):
            
            # Act
            gateway = self.gateway_manager._start_gateway(follower)
            
            # Assert
            assert gateway.follower_id == "test_follower"
            assert gateway.host_port == 4100
            assert gateway.client_id == 1000
            assert gateway.status == GatewayStatus.STARTING
            
            # Verify Docker container was started with Vault credentials
            mock_docker_client.containers.run.assert_called_once()
            call_args = mock_docker_client.containers.run.call_args
            environment = call_args[1]['environment']
            assert environment['TWS_USERID'] == "vault_user"
            assert environment['TWS_PASSWORD'] == "vault_pass"
    
    @patch('spreadpilot_core.ibkr.gateway_manager.docker.from_env')
    @patch('spreadpilot_core.ibkr.gateway_manager.get_vault_client')
    def test_start_gateway_vault_fallback_to_stored_credentials(self, mock_get_vault_client, mock_docker):
        """Test starting gateway falls back to stored credentials when Vault fails."""
        # Arrange
        mock_vault_client = Mock()
        mock_vault_client.get_ibkr_credentials.return_value = None  # Vault credentials not found
        mock_get_vault_client.return_value = mock_vault_client
        
        mock_docker_client = Mock()
        mock_container = Mock()
        mock_container.id = "test_container_id"
        mock_docker_client.containers.run.return_value = mock_container
        mock_docker_client.containers.get.side_effect = Exception("Not found")  # No existing container
        mock_docker.return_value = mock_docker_client
        
        follower = MockFollower(
            id="test_follower",
            ibkr_username="stored_user",
            vault_secret_ref="ibkr/test_follower"
        )
        
        # Mock port and client ID allocation
        with patch.object(self.gateway_manager, '_allocate_port', return_value=4100), \
             patch.object(self.gateway_manager, '_allocate_client_id', return_value=1000):
            
            # Act
            gateway = self.gateway_manager._start_gateway(follower)
            
            # Assert
            mock_docker_client.containers.run.assert_called_once()
            call_args = mock_docker_client.containers.run.call_args
            environment = call_args[1]['environment']
            assert environment['TWS_USERID'] == "stored_user"
            assert environment['TWS_PASSWORD'] == "placeholder"  # Fallback password
    
    @patch('spreadpilot_core.ibkr.gateway_manager.docker.from_env')
    def test_start_gateway_no_vault_secret_ref(self, mock_docker):
        """Test starting gateway without Vault secret reference uses stored credentials."""
        # Arrange
        mock_docker_client = Mock()
        mock_container = Mock()
        mock_container.id = "test_container_id"
        mock_docker_client.containers.run.return_value = mock_container
        mock_docker_client.containers.get.side_effect = Exception("Not found")  # No existing container
        mock_docker.return_value = mock_docker_client
        
        follower = MockFollower(
            id="test_follower",
            ibkr_username="stored_user"
            # No vault_secret_ref
        )
        
        # Mock port and client ID allocation
        with patch.object(self.gateway_manager, '_allocate_port', return_value=4100), \
             patch.object(self.gateway_manager, '_allocate_client_id', return_value=1000):
            
            # Act
            gateway = self.gateway_manager._start_gateway(follower)
            
            # Assert
            mock_docker_client.containers.run.assert_called_once()
            call_args = mock_docker_client.containers.run.call_args
            environment = call_args[1]['environment']
            assert environment['TWS_USERID'] == "stored_user"
            assert environment['TWS_PASSWORD'] == "placeholder"  # Fallback password
    
    @patch('spreadpilot_core.ibkr.gateway_manager.docker.from_env')
    def test_start_gateway_vault_disabled(self, mock_docker):
        """Test starting gateway with Vault disabled uses stored credentials."""
        # Arrange
        gateway_manager = GatewayManager(vault_enabled=False)
        
        mock_docker_client = Mock()
        mock_container = Mock()
        mock_container.id = "test_container_id"
        mock_docker_client.containers.run.return_value = mock_container
        mock_docker_client.containers.get.side_effect = Exception("Not found")  # No existing container
        mock_docker.return_value = mock_docker_client
        
        follower = MockFollower(
            id="test_follower",
            ibkr_username="stored_user",
            vault_secret_ref="ibkr/test_follower"
        )
        
        # Mock port and client ID allocation
        with patch.object(gateway_manager, '_allocate_port', return_value=4100), \
             patch.object(gateway_manager, '_allocate_client_id', return_value=1000):
            
            # Act
            gateway = gateway_manager._start_gateway(follower)
            
            # Assert
            mock_docker_client.containers.run.assert_called_once()
            call_args = mock_docker_client.containers.run.call_args
            environment = call_args[1]['environment']
            assert environment['TWS_USERID'] == "stored_user"
            assert environment['TWS_PASSWORD'] == "placeholder"  # Fallback password


class TestGatewayManagerVaultConfiguration:
    """Test GatewayManager Vault configuration."""
    
    def test_gateway_manager_vault_enabled_by_default(self):
        """Test that Vault is enabled by default."""
        gateway_manager = GatewayManager()
        assert gateway_manager.vault_enabled is True
    
    def test_gateway_manager_vault_can_be_disabled(self):
        """Test that Vault can be disabled."""
        gateway_manager = GatewayManager(vault_enabled=False)
        assert gateway_manager.vault_enabled is False
    
    def test_gateway_manager_other_parameters_unchanged(self):
        """Test that other parameters work normally with Vault integration."""
        gateway_manager = GatewayManager(
            gateway_image="custom:latest",
            port_range_start=5000,
            port_range_end=5100,
            vault_enabled=False
        )
        
        assert gateway_manager.gateway_image == "custom:latest"
        assert gateway_manager.port_range_start == 5000
        assert gateway_manager.port_range_end == 5100
        assert gateway_manager.vault_enabled is False
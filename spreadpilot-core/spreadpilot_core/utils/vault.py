"""HashiCorp Vault client utilities for SpreadPilot."""

import os
from typing import Dict, Optional, Any
from functools import lru_cache

import hvac
from hvac.exceptions import VaultError

from ..logging import get_logger

logger = get_logger(__name__)


class VaultClient:
    """HashiCorp Vault client wrapper for SpreadPilot."""
    
    def __init__(
        self,
        vault_url: Optional[str] = None,
        vault_token: Optional[str] = None,
        mount_point: str = "secret",
        verify_ssl: bool = True
    ):
        """Initialize Vault client.
        
        Args:
            vault_url: Vault server URL (defaults to VAULT_ADDR env var)
            vault_token: Vault token (defaults to VAULT_TOKEN env var)
            mount_point: KV mount point (default: "secret")
            verify_ssl: Whether to verify SSL certificates
        """
        self.vault_url = vault_url or os.getenv("VAULT_ADDR", "http://vault:8200")
        self.vault_token = vault_token or os.getenv("VAULT_TOKEN", "dev-only-token")
        self.mount_point = mount_point
        self.verify_ssl = verify_ssl
        
        self._client: Optional[hvac.Client] = None
        
    @property
    def client(self) -> hvac.Client:
        """Get or create Vault client."""
        if self._client is None:
            self._client = hvac.Client(
                url=self.vault_url,
                token=self.vault_token,
                verify=self.verify_ssl
            )
            
            # Verify client is authenticated
            if not self._client.is_authenticated():
                logger.error("Vault client is not authenticated")
                raise VaultError("Vault authentication failed")
                
            logger.info("Vault client initialized and authenticated")
            
        return self._client
    
    def get_secret(self, path: str, key: Optional[str] = None) -> Optional[Any]:
        """Get secret from Vault.
        
        Args:
            path: Secret path in Vault
            key: Specific key to retrieve from secret (returns entire secret if None)
            
        Returns:
            Secret value or None if not found
        """
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self.mount_point
            )
            
            secret_data = response["data"]["data"]
            
            if key:
                return secret_data.get(key)
            else:
                return secret_data
                
        except Exception as e:
            logger.error(f"Error retrieving secret from path '{path}': {e}")
            return None
    
    def get_ibkr_credentials(self, secret_ref: str) -> Optional[Dict[str, str]]:
        """Get IBKR credentials from Vault.
        
        Args:
            secret_ref: Secret reference/path for IBKR credentials
            
        Returns:
            Dict with 'IB_USER' and 'IB_PASS' keys or None if not found
        """
        try:
            # Try direct path first
            credentials = self.get_secret(secret_ref)
            
            if credentials and isinstance(credentials, dict):
                # Check for expected keys
                if "IB_USER" in credentials and "IB_PASS" in credentials:
                    logger.info(f"Retrieved IBKR credentials from Vault path: {secret_ref}")
                    return {
                        "IB_USER": credentials["IB_USER"],
                        "IB_PASS": credentials["IB_PASS"]
                    }
                
                # Check for alternative key formats
                username = credentials.get("username") or credentials.get("user")
                password = credentials.get("password") or credentials.get("pass")
                
                if username and password:
                    logger.info(f"Retrieved IBKR credentials from Vault path: {secret_ref}")
                    return {
                        "IB_USER": username,
                        "IB_PASS": password
                    }
            
            logger.warning(f"No valid IBKR credentials found in Vault path: {secret_ref}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving IBKR credentials from Vault: {e}")
            return None
    
    def put_secret(self, path: str, secret: Dict[str, Any]) -> bool:
        """Store secret in Vault.
        
        Args:
            path: Secret path in Vault
            secret: Secret data to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=secret,
                mount_point=self.mount_point
            )
            
            logger.info(f"Secret stored successfully at path: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing secret at path '{path}': {e}")
            return False
    
    def health_check(self) -> bool:
        """Check Vault health and connectivity.
        
        Returns:
            True if Vault is healthy and accessible, False otherwise
        """
        try:
            health = self.client.sys.read_health_status()
            
            # Check if Vault is initialized and not sealed
            is_healthy = health.get("initialized", False) and not health.get("sealed", True)
            
            if is_healthy:
                logger.debug("Vault health check passed")
            else:
                logger.warning(f"Vault health check failed: {health}")
                
            return is_healthy
            
        except Exception as e:
            logger.error(f"Vault health check error: {e}")
            return False


@lru_cache()
def get_vault_client() -> VaultClient:
    """Get cached Vault client instance.
    
    Returns:
        VaultClient instance
    """
    return VaultClient()


def get_ibkr_credentials_from_vault(secret_ref: str) -> Optional[Dict[str, str]]:
    """Convenience function to get IBKR credentials from Vault.
    
    Args:
        secret_ref: Secret reference/path for IBKR credentials
        
    Returns:
        Dict with 'IB_USER' and 'IB_PASS' keys or None if not found
    """
    vault_client = get_vault_client()
    return vault_client.get_ibkr_credentials(secret_ref)
"""
Unified secret management for SpreadPilot using HashiCorp Vault.

This module provides a centralized way to manage all secrets across SpreadPilot
services, with automatic fallback to environment variables for backward compatibility.
"""

import os
from enum import Enum
from functools import lru_cache
from typing import Any, Optional

from pydantic import BaseModel, Field

from ..logging import get_logger
from .vault import VaultClient, get_vault_client

logger = get_logger(__name__)


class SecretType(str, Enum):
    """Enumeration of secret types in SpreadPilot."""
    
    # Authentication & Security
    JWT_SECRET = "jwt_secret"
    ADMIN_USERNAME = "admin_username"
    ADMIN_PASSWORD_HASH = "admin_password_hash"
    SECURITY_PIN_HASH = "security_pin_hash"
    
    # Database
    MONGO_URI = "mongo_uri"
    POSTGRES_URI = "postgres_uri"
    REDIS_URL = "redis_url"
    
    # External APIs
    GOOGLE_SHEETS_API_KEY = "google_sheets_api_key"
    SENDGRID_API_KEY = "sendgrid_api_key"
    TELEGRAM_BOT_TOKEN = "telegram_bot_token"
    TELEGRAM_CHAT_ID = "telegram_chat_id"
    
    # Email/SMTP
    SMTP_USER = "smtp_user"
    SMTP_PASSWORD = "smtp_password"
    SMTP_URI = "smtp_uri"
    
    # Cloud Storage
    MINIO_ACCESS_KEY = "minio_access_key"
    MINIO_SECRET_KEY = "minio_secret_key"
    GCS_SERVICE_ACCOUNT_KEY = "gcs_service_account_key"
    
    # IBKR Trading
    IB_USER = "ib_user"
    IB_PASS = "ib_pass"


class SecretConfig(BaseModel):
    """Configuration for a secret."""
    
    vault_path: str = Field(..., description="Path in Vault where secret is stored")
    env_var: str = Field(..., description="Environment variable name for fallback")
    default_value: Optional[str] = Field(None, description="Default value if not found")
    required: bool = Field(True, description="Whether secret is required")
    sensitive: bool = Field(True, description="Whether to mask in logs")


# Secret configuration mapping
SECRET_CONFIGS = {
    # Authentication & Security
    SecretType.JWT_SECRET: SecretConfig(
        vault_path="secret/spreadpilot/auth/jwt",
        env_var="JWT_SECRET",
        required=True
    ),
    SecretType.ADMIN_USERNAME: SecretConfig(
        vault_path="secret/spreadpilot/auth/admin",
        env_var="ADMIN_USERNAME",
        default_value="admin",
        required=False
    ),
    SecretType.ADMIN_PASSWORD_HASH: SecretConfig(
        vault_path="secret/spreadpilot/auth/admin",
        env_var="ADMIN_PASSWORD_HASH",
        required=True
    ),
    SecretType.SECURITY_PIN_HASH: SecretConfig(
        vault_path="secret/spreadpilot/auth/security",
        env_var="SECURITY_PIN_HASH",
        required=True
    ),
    
    # Database
    SecretType.MONGO_URI: SecretConfig(
        vault_path="secret/spreadpilot/database/mongodb",
        env_var="MONGO_URI",
        default_value="mongodb://mongodb:27017",
        required=False
    ),
    SecretType.POSTGRES_URI: SecretConfig(
        vault_path="secret/spreadpilot/database/postgres",
        env_var="DATABASE_URL",
        required=False
    ),
    SecretType.REDIS_URL: SecretConfig(
        vault_path="secret/spreadpilot/database/redis",
        env_var="REDIS_URL",
        default_value="redis://redis:6379",
        required=False
    ),
    
    # External APIs
    SecretType.GOOGLE_SHEETS_API_KEY: SecretConfig(
        vault_path="secret/spreadpilot/external/google",
        env_var="GOOGLE_SHEETS_API_KEY",
        required=True
    ),
    SecretType.SENDGRID_API_KEY: SecretConfig(
        vault_path="secret/spreadpilot/external/sendgrid",
        env_var="SENDGRID_API_KEY",
        required=False
    ),
    SecretType.TELEGRAM_BOT_TOKEN: SecretConfig(
        vault_path="secret/spreadpilot/external/telegram",
        env_var="TELEGRAM_BOT_TOKEN",
        required=False
    ),
    SecretType.TELEGRAM_CHAT_ID: SecretConfig(
        vault_path="secret/spreadpilot/external/telegram",
        env_var="TELEGRAM_CHAT_ID",
        required=False
    ),
    
    # Email/SMTP
    SecretType.SMTP_USER: SecretConfig(
        vault_path="secret/spreadpilot/email/smtp",
        env_var="SMTP_USER",
        required=False
    ),
    SecretType.SMTP_PASSWORD: SecretConfig(
        vault_path="secret/spreadpilot/email/smtp",
        env_var="SMTP_PASSWORD",
        required=False
    ),
    SecretType.SMTP_URI: SecretConfig(
        vault_path="secret/spreadpilot/email/smtp",
        env_var="SMTP_URI",
        required=False
    ),
    
    # Cloud Storage
    SecretType.MINIO_ACCESS_KEY: SecretConfig(
        vault_path="secret/spreadpilot/storage/minio",
        env_var="MINIO_ACCESS_KEY",
        required=False
    ),
    SecretType.MINIO_SECRET_KEY: SecretConfig(
        vault_path="secret/spreadpilot/storage/minio",
        env_var="MINIO_SECRET_KEY",
        required=False
    ),
    SecretType.GCS_SERVICE_ACCOUNT_KEY: SecretConfig(
        vault_path="secret/spreadpilot/storage/gcs",
        env_var="GCS_SERVICE_ACCOUNT_KEY_PATH",
        required=False
    ),
    
    # IBKR Trading
    SecretType.IB_USER: SecretConfig(
        vault_path="secret/spreadpilot/ibkr/credentials",
        env_var="IB_USER",
        required=True
    ),
    SecretType.IB_PASS: SecretConfig(
        vault_path="secret/spreadpilot/ibkr/credentials",
        env_var="IB_PASS",
        required=True
    ),
}


class SecretManager:
    """Unified secret manager for SpreadPilot."""
    
    def __init__(self, vault_client: Optional[VaultClient] = None, use_vault: bool = True):
        """Initialize secret manager.
        
        Args:
            vault_client: Optional Vault client instance
            use_vault: Whether to use Vault (can be disabled for testing)
        """
        self.vault_client = vault_client or get_vault_client() if use_vault else None
        self.use_vault = use_vault and self.vault_client is not None
        self._cache: dict[SecretType, Any] = {}
        
        if self.use_vault:
            logger.info("SecretManager initialized with Vault backend")
        else:
            logger.info("SecretManager initialized with environment variable backend only")
    
    def get_secret(self, secret_type: SecretType, force_refresh: bool = False) -> Optional[str]:
        """Get a secret value.
        
        Args:
            secret_type: Type of secret to retrieve
            force_refresh: Force refresh from source (bypass cache)
            
        Returns:
            Secret value or None if not found and not required
            
        Raises:
            ValueError: If required secret is not found
        """
        # Check cache first
        if not force_refresh and secret_type in self._cache:
            return self._cache[secret_type]
        
        config = SECRET_CONFIGS[secret_type]
        value = None
        
        # Try Vault first if enabled
        if self.use_vault:
            try:
                vault_data = self.vault_client.get_secret(config.vault_path)
                if vault_data and isinstance(vault_data, dict):
                    # Extract the specific key from vault data
                    key_name = secret_type.value
                    value = vault_data.get(key_name)
                    
                    if value:
                        logger.debug(
                            f"Retrieved {secret_type.value} from Vault"
                            if not config.sensitive
                            else f"Retrieved {secret_type.value} from Vault (masked)"
                        )
            except Exception as e:
                logger.warning(f"Failed to retrieve {secret_type.value} from Vault: {e}")
        
        # Fall back to environment variable
        if value is None:
            value = os.getenv(config.env_var)
            if value:
                logger.debug(
                    f"Retrieved {secret_type.value} from environment variable"
                    if not config.sensitive
                    else f"Retrieved {secret_type.value} from environment (masked)"
                )
        
        # Use default value if available
        if value is None and config.default_value is not None:
            value = config.default_value
            logger.debug(f"Using default value for {secret_type.value}")
        
        # Check if required
        if value is None and config.required:
            raise ValueError(
                f"Required secret {secret_type.value} not found in Vault or environment"
            )
        
        # Cache the value
        if value is not None:
            self._cache[secret_type] = value
        
        return value
    
    def get_secret_dict(self, *secret_types: SecretType) -> dict[str, Optional[str]]:
        """Get multiple secrets as a dictionary.
        
        Args:
            *secret_types: Secret types to retrieve
            
        Returns:
            Dictionary mapping env var names to values
        """
        result = {}
        for secret_type in secret_types:
            config = SECRET_CONFIGS[secret_type]
            value = self.get_secret(secret_type)
            result[config.env_var] = value
        return result
    
    def get_database_config(self) -> dict[str, Optional[str]]:
        """Get all database configuration secrets."""
        return self.get_secret_dict(
            SecretType.MONGO_URI,
            SecretType.POSTGRES_URI,
            SecretType.REDIS_URL
        )
    
    def get_auth_config(self) -> dict[str, Optional[str]]:
        """Get authentication configuration secrets."""
        return self.get_secret_dict(
            SecretType.JWT_SECRET,
            SecretType.ADMIN_USERNAME,
            SecretType.ADMIN_PASSWORD_HASH,
            SecretType.SECURITY_PIN_HASH
        )
    
    def get_external_api_config(self) -> dict[str, Optional[str]]:
        """Get external API configuration secrets."""
        return self.get_secret_dict(
            SecretType.GOOGLE_SHEETS_API_KEY,
            SecretType.SENDGRID_API_KEY,
            SecretType.TELEGRAM_BOT_TOKEN,
            SecretType.TELEGRAM_CHAT_ID
        )
    
    def get_email_config(self) -> dict[str, Optional[str]]:
        """Get email/SMTP configuration secrets."""
        return self.get_secret_dict(
            SecretType.SMTP_USER,
            SecretType.SMTP_PASSWORD,
            SecretType.SMTP_URI
        )
    
    def get_storage_config(self) -> dict[str, Optional[str]]:
        """Get cloud storage configuration secrets."""
        return self.get_secret_dict(
            SecretType.MINIO_ACCESS_KEY,
            SecretType.MINIO_SECRET_KEY,
            SecretType.GCS_SERVICE_ACCOUNT_KEY
        )
    
    def get_ibkr_credentials(self) -> dict[str, Optional[str]]:
        """Get IBKR trading credentials."""
        return {
            "IB_USER": self.get_secret(SecretType.IB_USER),
            "IB_PASS": self.get_secret(SecretType.IB_PASS)
        }
    
    def store_secret(self, secret_type: SecretType, value: str) -> bool:
        """Store a secret in Vault.
        
        Args:
            secret_type: Type of secret to store
            value: Secret value
            
        Returns:
            True if successful, False otherwise
        """
        if not self.use_vault:
            logger.warning("Cannot store secret without Vault backend")
            return False
        
        config = SECRET_CONFIGS[secret_type]
        
        try:
            # Get existing secrets at this path
            existing = self.vault_client.get_secret(config.vault_path) or {}
            
            # Update with new value
            existing[secret_type.value] = value
            
            # Store back to Vault
            success = self.vault_client.put_secret(config.vault_path, existing)
            
            if success:
                # Clear cache for this secret
                self._cache.pop(secret_type, None)
                logger.info(f"Stored {secret_type.value} in Vault")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to store {secret_type.value} in Vault: {e}")
            return False
    
    def clear_cache(self):
        """Clear the internal secret cache."""
        self._cache.clear()
        logger.debug("Secret cache cleared")


# Global secret manager instance
_secret_manager: Optional[SecretManager] = None


@lru_cache
def get_secret_manager() -> SecretManager:
    """Get or create the global secret manager instance.
    
    Returns:
        SecretManager instance
    """
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager


# Convenience functions
def get_secret(secret_type: SecretType) -> Optional[str]:
    """Get a secret value using the global secret manager.
    
    Args:
        secret_type: Type of secret to retrieve
        
    Returns:
        Secret value or None if not found
    """
    return get_secret_manager().get_secret(secret_type)


def get_database_config() -> dict[str, Optional[str]]:
    """Get database configuration using the global secret manager."""
    return get_secret_manager().get_database_config()


def get_auth_config() -> dict[str, Optional[str]]:
    """Get authentication configuration using the global secret manager."""
    return get_secret_manager().get_auth_config()


def get_ibkr_credentials() -> dict[str, Optional[str]]:
    """Get IBKR credentials using the global secret manager."""
    return get_secret_manager().get_ibkr_credentials()
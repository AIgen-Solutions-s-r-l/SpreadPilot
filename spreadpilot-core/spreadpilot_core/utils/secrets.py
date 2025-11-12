import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from spreadpilot_core.logging import get_logger

from .secret_manager import SecretType, get_secret_manager

logger = get_logger(__name__)

SECRETS_COLLECTION_NAME = "secrets"  # Define the collection name


async def get_secret_from_mongo(
    db: AsyncIOMotorDatabase,
    secret_name: str,
    environment: str | None = None,
) -> str | None:
    """
    Retrieves a secret value from the designated MongoDB secrets collection.

    Args:
        db: An initialized AsyncIOMotorDatabase instance.
        secret_name: The name of the secret to retrieve (e.g., "TELEGRAM_BOT_TOKEN").
        environment: The environment scope (e.g., "production", "development").
                     If None, defaults to os.environ.get("APP_ENV", "development").

    Returns:
        The secret value as a string if found, otherwise None.
    """
    if db is None:
        logger.error("MongoDB database instance is not provided.")
        return None

    if environment is None:
        environment = os.environ.get("APP_ENV", "development")
        logger.debug(f"No environment specified, defaulting to '{environment}' based on APP_ENV.")

    collection = db[SECRETS_COLLECTION_NAME]
    query = {"name": secret_name, "environment": environment}

    try:
        logger.debug(
            f"Attempting to fetch secret '{secret_name}' for environment '{environment}' from collection '{SECRETS_COLLECTION_NAME}'."
        )
        secret_doc = await collection.find_one(query)

        if secret_doc:
            secret_value = secret_doc.get("value")
            if secret_value:
                logger.info(
                    f"Successfully retrieved secret '{secret_name}' for environment '{environment}'."
                )
                # Consider adding a check here for sensitive values if logging values directly is a concern
                # logger.debug(f"Secret value: {secret_value[:5]}...") # Example redaction
                return str(secret_value)  # Ensure it's a string
            else:
                logger.warning(
                    f"Secret document found for '{secret_name}' in environment '{environment}', but 'value' field is missing or empty."
                )
                return None
        else:
            logger.warning(
                f"Secret '{secret_name}' not found for environment '{environment}' in collection '{SECRETS_COLLECTION_NAME}'."
            )
            return None
    except Exception as e:
        logger.error(f"Error retrieving secret '{secret_name}' from MongoDB: {e}", exc_info=True)
        return None


def get_secret(secret_name: str, fallback_to_env: bool = True) -> Optional[str]:
    """
    Get a secret value using the unified secret manager.

    This function provides a simple interface to retrieve secrets with automatic
    fallback handling. It will try in order:
    1. HashiCorp Vault (if configured)
    2. Environment variables (if fallback enabled)
    3. Default values (for non-required secrets)

    Args:
        secret_name: Name of the secret (should match SecretType enum values)
        fallback_to_env: Whether to fall back to environment variables

    Returns:
        Secret value or None if not found
    """
    try:
        # Map common secret names to SecretType
        secret_type_map = {
            "JWT_SECRET": SecretType.JWT_SECRET,
            "ADMIN_USERNAME": SecretType.ADMIN_USERNAME,
            "ADMIN_PASSWORD_HASH": SecretType.ADMIN_PASSWORD_HASH,
            "SECURITY_PIN_HASH": SecretType.SECURITY_PIN_HASH,
            "MONGO_URI": SecretType.MONGO_URI,
            "DATABASE_URL": SecretType.POSTGRES_URI,
            "POSTGRES_URI": SecretType.POSTGRES_URI,
            "REDIS_URL": SecretType.REDIS_URL,
            "SENDGRID_API_KEY": SecretType.SENDGRID_API_KEY,
            "TELEGRAM_BOT_TOKEN": SecretType.TELEGRAM_BOT_TOKEN,
            "TELEGRAM_CHAT_ID": SecretType.TELEGRAM_CHAT_ID,
            "SMTP_USER": SecretType.SMTP_USER,
            "SMTP_PASSWORD": SecretType.SMTP_PASSWORD,
            "SMTP_URI": SecretType.SMTP_URI,
            "MINIO_ACCESS_KEY": SecretType.MINIO_ACCESS_KEY,
            "MINIO_SECRET_KEY": SecretType.MINIO_SECRET_KEY,
            "GCS_SERVICE_ACCOUNT_KEY_PATH": SecretType.GCS_SERVICE_ACCOUNT_KEY,
            "IB_USER": SecretType.IB_USER,
            "IB_PASS": SecretType.IB_PASS,
        }

        # Get the secret type
        secret_type = secret_type_map.get(secret_name.upper())

        if secret_type:
            # Use the secret manager
            secret_manager = get_secret_manager()
            return secret_manager.get_secret(secret_type)
        else:
            # Unknown secret, try environment variable if fallback enabled
            if fallback_to_env:
                value = os.getenv(secret_name)
                if value:
                    logger.debug(f"Retrieved {secret_name} from environment variable")
                    return value
                else:
                    logger.warning(f"Secret {secret_name} not found in Vault or environment")
            else:
                logger.warning(f"Unknown secret type: {secret_name}")
            return None

    except Exception as e:
        logger.error(f"Error retrieving secret {secret_name}: {e}")

        # Fall back to environment variable on error
        if fallback_to_env:
            return os.getenv(secret_name)
        return None

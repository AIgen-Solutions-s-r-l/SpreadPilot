import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from spreadpilot_core.logging import get_logger

logger = get_logger(__name__)

SECRETS_COLLECTION_NAME = "secrets"  # Define the collection name

async def get_secret_from_mongo(
    db: AsyncIOMotorDatabase,
    secret_name: str,
    environment: Optional[str] = None,
) -> Optional[str]:
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
        logger.debug(f"Attempting to fetch secret '{secret_name}' for environment '{environment}' from collection '{SECRETS_COLLECTION_NAME}'.")
        secret_doc = await collection.find_one(query)

        if secret_doc:
            secret_value = secret_doc.get("value")
            if secret_value:
                logger.info(f"Successfully retrieved secret '{secret_name}' for environment '{environment}'.")
                # Consider adding a check here for sensitive values if logging values directly is a concern
                # logger.debug(f"Secret value: {secret_value[:5]}...") # Example redaction
                return str(secret_value) # Ensure it's a string
            else:
                logger.warning(f"Secret document found for '{secret_name}' in environment '{environment}', but 'value' field is missing or empty.")
                return None
        else:
            logger.warning(f"Secret '{secret_name}' not found for environment '{environment}' in collection '{SECRETS_COLLECTION_NAME}'.")
            return None
    except Exception as e:
        logger.error(f"Error retrieving secret '{secret_name}' from MongoDB: {e}", exc_info=True)
        return None
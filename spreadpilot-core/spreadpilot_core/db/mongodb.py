import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from spreadpilot_core.logging.logger import get_logger

logger = get_logger(__name__)

# MongoDB connection details from environment variables
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "spreadpilot")  # Default DB name if not set

if not MONGO_URI:
    logger.error("MONGO_URI environment variable is not set.")
    raise ValueError("MONGO_URI environment variable is required for MongoDB connection.")

# Global variable to hold the client instance
_mongo_client: AsyncIOMotorClient | None = None


async def connect_to_mongo():
    """Initializes the MongoDB client connection."""
    global _mongo_client
    # Prevent initialization if TESTING env var is set, rely on dependency injection/mocking
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    if _mongo_client is None and not is_testing:
        logger.info(f"Connecting to MongoDB at {MONGO_URI}...")
        try:
            _mongo_client = AsyncIOMotorClient(MONGO_URI)
            # Optional: Verify connection by pinging the admin database
            await _mongo_client.admin.command("ping")
            logger.info("MongoDB client initialized and connection verified successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize or connect to MongoDB: {e}", exc_info=True)
            _mongo_client = None  # Reset on failure
            raise
    elif is_testing:
        logger.debug(
            "TESTING environment detected, skipping default MongoDB client initialization."
        )
    elif _mongo_client:
        logger.debug("MongoDB client already initialized.")


async def close_mongo_connection():
    """Closes the MongoDB client connection."""
    global _mongo_client
    if _mongo_client:
        logger.info("Closing MongoDB connection...")
        _mongo_client.close()
        _mongo_client = None
        logger.info("MongoDB connection closed.")


def get_mongo_client() -> AsyncIOMotorClient:
    """
    Returns the initialized MongoDB client instance.
    Raises RuntimeError if the client is not initialized.
    """
    if _mongo_client is None:
        # This should ideally not happen if connect_to_mongo is called at application startup
        # or if dependency injection provides one during testing.
        logger.error("MongoDB client accessed before initialization!")
        raise RuntimeError(
            "MongoDB client not initialized. Call connect_to_mongo first or ensure it's provided via context/DI."
        )
    return _mongo_client


async def get_mongo_db() -> AsyncIOMotorDatabase:
    """
    Returns the MongoDB database instance using the initialized client.
    To be used where an async database handle is needed.
    """
    client = get_mongo_client()  # Get the client (global or overridden)
    return client[MONGO_DB_NAME]


# Note: Removed the __main__ block for test connection as it's not typical for a library.
# Connection testing should be part of integration tests or application startup checks.

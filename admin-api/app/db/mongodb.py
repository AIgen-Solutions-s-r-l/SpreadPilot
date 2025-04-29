# import os # No longer needed for direct env var access here
import asyncio
import importlib # Use importlib for consistency
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from spreadpilot_core.logging.logger import get_logger
# from functools import lru_cache # Not using lru_cache for client instance

# Import settings using importlib
admin_api_config = importlib.import_module('admin-api.app.core.config')
get_settings = admin_api_config.get_settings
settings = get_settings() # Load settings once

logger = get_logger(__name__)

# MongoDB connection details from settings
MONGO_URI = settings.mongo_uri
MONGO_DB_NAME = settings.mongo_db_name

# Global variable to hold the client instance
_mongo_client: AsyncIOMotorClient | None = None

async def connect_to_mongo():
    """Initializes the MongoDB client connection."""
    global _mongo_client
    if _mongo_client is None:
        logger.info(f"Connecting to MongoDB at {MONGO_URI}...")
        try:
            _mongo_client = AsyncIOMotorClient(MONGO_URI)
            # Optional: Verify connection by listing database names (requires admin privileges)
            # await _mongo_client.list_database_names()
            logger.info("MongoDB client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB client: {e}", exc_info=True)
            _mongo_client = None # Reset on failure
            raise

async def close_mongo_connection():
    """Closes the MongoDB client connection."""
    global _mongo_client
    if _mongo_client:
        logger.info("Closing MongoDB connection...")
        _mongo_client.close()
        _mongo_client = None
        logger.info("MongoDB connection closed.")

def get_mongo_client() -> AsyncIOMotorClient:
    """Returns the initialized MongoDB client instance."""
    if _mongo_client is None:
        # This should ideally not happen if connect_to_mongo is called at startup
        logger.warning("MongoDB client accessed before initialization!")
        # Attempt synchronous connection as a fallback (not recommended for async apps)
        # Or raise an error
        raise RuntimeError("MongoDB client not initialized. Call connect_to_mongo first.")
    return _mongo_client

async def get_mongo_db() -> AsyncIOMotorDatabase:
    """
    Dependency function to get the MongoDB database instance.
    To be used with FastAPI's Depends().
    Ensures the client is initialized.
    """
    if _mongo_client is None:
        await connect_to_mongo() # Ensure connection is established if not already
    
    client = get_mongo_client()
    return client[MONGO_DB_NAME]

# Example usage (optional, for testing connection)
async def _test_connection():
    try:
        await connect_to_mongo()
        db = await get_mongo_db()
        # Perform a simple operation, e.g., list collections
        collections = await db.list_collection_names()
        logger.info(f"Successfully connected to MongoDB database '{settings.mongo_db_name}'. Collections: {collections}")
    except Exception as e:
        logger.error(f"MongoDB connection test failed: {e}", exc_info=True)
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    # Basic test to check if client initializes and connects
    asyncio.run(_test_connection())
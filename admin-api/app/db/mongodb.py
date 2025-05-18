import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from spreadpilot_core.logging.logger import get_logger

# Get logger
logger = get_logger(__name__)

# Global variables to hold the client instance
_mongo_client: AsyncIOMotorClient | None = None

# Function to get settings (can be replaced with a proper settings module)
def get_db_settings():
    return {
        "mongo_uri": os.getenv("MONGO_URI", "mongodb://admin:password@mongodb:27017"),
        "mongo_db_name": os.getenv("MONGO_DB_NAME", "spreadpilot_admin")
    }

# Get MongoDB connection details from settings
settings = get_db_settings()
MONGO_URI = settings["mongo_uri"]
MONGO_DB_NAME = settings["mongo_db_name"]

logger.info(f"MongoDB configuration: DB={MONGO_DB_NAME}")

async def connect_to_mongo():
    """Initializes the MongoDB client connection."""
    global _mongo_client
    # Prevent initialization if TESTING env var is set, rely on dependency injection
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    if _mongo_client is None and not is_testing:
        logger.info(f"Connecting to MongoDB at {MONGO_URI}...")
        try:
            _mongo_client = AsyncIOMotorClient(MONGO_URI)
            # Verify connection
            await _mongo_client.admin.command('ismaster')
            logger.info("MongoDB client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB client: {e}", exc_info=True)
            _mongo_client = None # Reset on failure
            raise
    elif is_testing:
        logger.debug("TESTING environment detected, skipping default MongoDB client initialization.")

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
        # or if dependency injection provides one during testing.
        logger.error("MongoDB client accessed before initialization!")
        raise RuntimeError("MongoDB client not initialized. Call connect_to_mongo first.")
    return _mongo_client

async def get_db() -> AsyncIOMotorDatabase:
    """
    Dependency function to get the MongoDB database instance.
    To be used with FastAPI's Depends().
    """
    client = get_mongo_client()
    return client[MONGO_DB_NAME]

# Function to check database connection (for health checks)
async def check_connection():
    try:
        # The ismaster command is cheap and does not require auth
        client = get_mongo_client()
        await client.admin.command('ismaster')
        logger.info("Successfully connected to MongoDB!")
        return True
    except Exception as e:
        logger.error(f"MongoDB connection error: {e}")
        return False

# Define collections
def get_followers_collection():
    client = get_mongo_client()
    db = client[MONGO_DB_NAME]
    return db.followers

# Example usage (optional, for testing connection)
async def _test_connection():
    try:
        await connect_to_mongo()
        db = await get_db()
        # Perform a simple operation, e.g., list collections
        collections = await db.list_collection_names()
        logger.info(f"Successfully connected to MongoDB database '{MONGO_DB_NAME}'. Collections: {collections}")
    except Exception as e:
        logger.error(f"MongoDB connection test failed: {e}", exc_info=True)
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    # Basic test to check if client initializes and connects
    asyncio.run(_test_connection())
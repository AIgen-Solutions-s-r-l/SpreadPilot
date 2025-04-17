import os
from functools import lru_cache

from google.cloud import firestore
from spreadpilot_core.logging.logger import get_logger

logger = get_logger(__name__)

# Determine project ID (adjust if needed, e.g., from env var)
# If running locally with emulator, project_id might be different.
# If running on GCP, it might be inferred automatically.
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "spreadpilot") # Replace 'spreadpilot' if needed

@lru_cache() # Cache the client instance for efficiency
def get_firestore_client() -> firestore.AsyncClient:
    """
    Initializes and returns an asynchronous Firestore client.

    Uses LRU cache to ensure only one client instance is created.
    Handles potential emulator usage via FIRESTORE_EMULATOR_HOST env var.
    """
    try:
        # Firestore client automatically uses FIRESTORE_EMULATOR_HOST if set
        emulator_host = os.getenv("FIRESTORE_EMULATOR_HOST")
        if emulator_host:
            logger.info(f"Using Firestore emulator at {emulator_host}")
            # Note: For async client with emulator, credentials aren't strictly needed,
            # but explicitly providing anonymous creds can prevent potential issues.
            from google.auth.credentials import AnonymousCredentials
            client = firestore.AsyncClient(project=PROJECT_ID, credentials=AnonymousCredentials())
        else:
            logger.info(f"Connecting to Firestore project: {PROJECT_ID}")
            client = firestore.AsyncClient(project=PROJECT_ID)
        logger.info("Firestore AsyncClient initialized successfully.")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Firestore client: {e}", exc_info=True)
        raise

async def get_db() -> firestore.AsyncClient:
    """
    Dependency function to get the Firestore client instance.
    To be used with FastAPI's Depends().
    """
    return get_firestore_client()

# Example usage (optional, for testing connection)
async def _test_connection():
    try:
        client = get_firestore_client()
        # Perform a simple operation, e.g., list collections
        collections = [col async for col in client.collections()]
        logger.info(f"Successfully connected to Firestore. Collections: {[c.id for c in collections]}")
    except Exception as e:
        logger.error(f"Firestore connection test failed: {e}", exc_info=True)

if __name__ == "__main__":
    # Basic test to check if client initializes
    import asyncio
    asyncio.run(_test_connection())
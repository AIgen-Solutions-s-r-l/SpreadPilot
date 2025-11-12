"""Redis client for admin-api rate limiting and caching."""

import os

try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # type: ignore

from spreadpilot_core.logging.logger import get_logger

logger = get_logger(__name__)

# Global Redis client instance
_redis_client: redis.Redis | None = None


async def connect_to_redis() -> None:
    """Initialize Redis client connection."""
    global _redis_client

    # Skip if testing
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    if is_testing:
        logger.debug("TESTING environment detected, skipping Redis client initialization.")
        return

    if _redis_client is not None:
        logger.debug("Redis client already initialized.")
        return

    if redis is None:
        logger.warning("redis package not installed. Rate limiting will use in-memory storage.")
        return

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    try:
        logger.info(f"Connecting to Redis at {redis_url}...")
        _redis_client = redis.from_url(redis_url, decode_responses=True)

        # Test connection
        await _redis_client.ping()
        logger.info("Redis client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
        _redis_client = None


async def close_redis_connection() -> None:
    """Close Redis client connection."""
    global _redis_client

    if _redis_client:
        logger.info("Closing Redis connection...")
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed.")


def get_redis_client() -> redis.Redis | None:
    """
    Get the Redis client instance.

    Returns:
        Redis client or None if not initialized/available
    """
    return _redis_client


def is_redis_available() -> bool:
    """
    Check if Redis is available and connected.

    Returns:
        True if Redis is available, False otherwise
    """
    return _redis_client is not None and redis is not None

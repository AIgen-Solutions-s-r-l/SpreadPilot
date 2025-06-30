"""Redis client utilities for SpreadPilot."""

import os
from typing import Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from ..logging import get_logger

logger = get_logger(__name__)

# Global Redis client instance
_redis_client: Optional[Redis] = None


async def get_redis_client() -> Optional[Redis]:
    """Get or create async Redis client instance.

    Returns:
        Redis client instance or None if connection fails
    """
    global _redis_client

    if _redis_client is None:
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            _redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 3,  # TCP_KEEPINTVL
                    3: 5,  # TCP_KEEPCNT
                },
            )

            # Test connection
            await _redis_client.ping()
            logger.info(f"Connected to Redis at {redis_url}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            _redis_client = None

    return _redis_client


async def close_redis_connection():
    """Close the Redis connection."""
    global _redis_client

    if _redis_client:
        try:
            await _redis_client.close()
            logger.info("Closed Redis connection")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
        finally:
            _redis_client = None

"""Unit tests for Redis client connection management."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.db.redis_client import (
    connect_to_redis,
    disconnect_from_redis,
    get_redis_client,
    is_redis_available,
    _redis_client,
)


@pytest.mark.asyncio
class TestRedisClient:
    """Test Redis client connection management."""

    async def test_connect_to_redis_success(self):
        """Test successful Redis connection."""
        with patch("app.db.redis_client.redis") as mock_redis:
            mock_client = AsyncMock()
            mock_redis.from_url.return_value = mock_client

            with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379"}):
                await connect_to_redis()

            mock_redis.from_url.assert_called_once_with(
                "redis://localhost:6379", decode_responses=True
            )
            mock_client.ping.assert_awaited_once()

    async def test_connect_to_redis_default_url(self):
        """Test Redis connection with default URL."""
        with patch("app.db.redis_client.redis") as mock_redis:
            mock_client = AsyncMock()
            mock_redis.from_url.return_value = mock_client

            with patch.dict("os.environ", {}, clear=True):
                await connect_to_redis()

            # Should use default URL
            mock_redis.from_url.assert_called_once_with(
                "redis://localhost:6379", decode_responses=True
            )

    async def test_connect_to_redis_connection_failure(self):
        """Test handling of Redis connection failure."""
        with patch("app.db.redis_client.redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping.side_effect = Exception("Connection refused")
            mock_redis.from_url.return_value = mock_client

            with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379"}):
                await connect_to_redis()

            # Should not raise exception
            mock_client.ping.assert_awaited_once()

    async def test_connect_to_redis_module_not_available(self):
        """Test when redis module is not available."""
        with patch("app.db.redis_client.redis", None):
            await connect_to_redis()

            # Should handle gracefully
            assert _redis_client is None

    async def test_disconnect_from_redis_success(self):
        """Test successful Redis disconnection."""
        mock_client = AsyncMock()

        with patch("app.db.redis_client._redis_client", mock_client):
            await disconnect_from_redis()

        mock_client.close.assert_awaited_once()

    async def test_disconnect_from_redis_no_client(self):
        """Test disconnection when no client exists."""
        with patch("app.db.redis_client._redis_client", None):
            # Should not raise exception
            await disconnect_from_redis()

    async def test_disconnect_from_redis_exception(self):
        """Test exception handling during disconnection."""
        mock_client = AsyncMock()
        mock_client.close.side_effect = Exception("Close error")

        with patch("app.db.redis_client._redis_client", mock_client):
            # Should not raise exception
            await disconnect_from_redis()

        mock_client.close.assert_awaited_once()

    def test_get_redis_client_available(self):
        """Test getting Redis client when available."""
        mock_client = Mock()

        with patch("app.db.redis_client._redis_client", mock_client):
            client = get_redis_client()

        assert client == mock_client

    def test_get_redis_client_not_available(self):
        """Test getting Redis client when not available."""
        with patch("app.db.redis_client._redis_client", None):
            client = get_redis_client()

        assert client is None

    def test_is_redis_available_true(self):
        """Test Redis availability check when available."""
        mock_client = Mock()

        with patch("app.db.redis_client._redis_client", mock_client), patch(
            "app.db.redis_client.redis", Mock()
        ):
            available = is_redis_available()

        assert available is True

    def test_is_redis_available_no_client(self):
        """Test Redis availability check when client not initialized."""
        with patch("app.db.redis_client._redis_client", None), patch(
            "app.db.redis_client.redis", Mock()
        ):
            available = is_redis_available()

        assert available is False

    def test_is_redis_available_no_module(self):
        """Test Redis availability check when module not installed."""
        mock_client = Mock()

        with patch("app.db.redis_client._redis_client", mock_client), patch(
            "app.db.redis_client.redis", None
        ):
            available = is_redis_available()

        assert available is False

    def test_is_redis_available_both_missing(self):
        """Test Redis availability check when both client and module missing."""
        with patch("app.db.redis_client._redis_client", None), patch(
            "app.db.redis_client.redis", None
        ):
            available = is_redis_available()

        assert available is False

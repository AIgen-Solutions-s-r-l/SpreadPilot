"""Unit tests for Redis-based rate limiting in security module."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.core.security import (
    MAX_PIN_ATTEMPTS,
    PIN_LOCKOUT_DURATION,
    PINVerification,
)


@pytest.fixture
def pin_verifier():
    """Create a PIN verification instance with a test PIN."""
    verifier = PINVerification()
    verifier.set_pin("123456")
    return verifier


@pytest.mark.asyncio
class TestPINVerificationRedis:
    """Test PIN verification with Redis rate limiting."""

    async def test_verify_pin_success_with_redis(self, pin_verifier):
        """Test successful PIN verification with Redis."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # No lockout

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
        ):
            result = await pin_verifier.verify_pin("123456", "user123")

        assert result is True
        # Should clear attempts on success
        mock_redis.delete.assert_awaited_once()

    async def test_verify_pin_failure_records_in_redis(self, pin_verifier):
        """Test failed PIN attempt is recorded in Redis."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # No lockout
        mock_redis.zrangebyscore.return_value = []  # No previous attempts

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
            pytest.raises(HTTPException) as exc_info,
        ):
            await pin_verifier.verify_pin("wrong", "user123")

        assert exc_info.value.status_code == 403
        # Should record attempt in Redis
        mock_redis.zadd.assert_awaited_once()
        mock_redis.expire.assert_awaited_once()
        mock_redis.zremrangebyscore.assert_awaited_once()

    async def test_verify_pin_lockout_with_redis(self, pin_verifier):
        """Test lockout after max attempts with Redis."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # No existing lockout
        # Return timestamps for MAX_PIN_ATTEMPTS failed attempts
        mock_redis.zrangebyscore.return_value = [
            str(datetime.utcnow().timestamp()) for _ in range(MAX_PIN_ATTEMPTS)
        ]

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
            pytest.raises(HTTPException) as exc_info,
        ):
            await pin_verifier.verify_pin("wrong", "user123")

        assert exc_info.value.status_code == 429
        assert "locked" in exc_info.value.detail.lower()
        # Should set lockout in Redis
        mock_redis.set.assert_awaited_once()

    async def test_verify_pin_during_active_lockout(self, pin_verifier):
        """Test verification during active lockout period."""
        lockout_end = datetime.utcnow() + timedelta(minutes=5)
        mock_redis = AsyncMock()
        mock_redis.get.return_value = lockout_end.isoformat()

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
            pytest.raises(HTTPException) as exc_info,
        ):
            await pin_verifier.verify_pin("123456", "user123")

        assert exc_info.value.status_code == 429
        assert "try again in" in exc_info.value.detail.lower()

    async def test_verify_pin_after_lockout_expired(self, pin_verifier):
        """Test verification after lockout period expired."""
        lockout_end = datetime.utcnow() - timedelta(minutes=5)
        mock_redis = AsyncMock()
        mock_redis.get.return_value = lockout_end.isoformat()

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
        ):
            result = await pin_verifier.verify_pin("123456", "user123")

        assert result is True
        # Should clear attempts after expired lockout
        mock_redis.delete.assert_awaited()

    async def test_verify_pin_fallback_when_redis_unavailable(self, pin_verifier):
        """Test fallback to in-memory when Redis unavailable."""
        with (
            patch("app.core.security.get_redis_client", return_value=None),
            patch("app.core.security.is_redis_available", return_value=False),
        ):
            result = await pin_verifier.verify_pin("123456", "user123")

        assert result is True

    async def test_verify_pin_redis_exception_falls_back(self, pin_verifier):
        """Test fallback to in-memory when Redis raises exception."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis connection error")

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
        ):
            result = await pin_verifier.verify_pin("123456", "user123")

        assert result is True


@pytest.mark.asyncio
class TestPINVerificationFallback:
    """Test in-memory fallback for PIN rate limiting."""

    async def test_fallback_rate_limiting(self, pin_verifier):
        """Test in-memory rate limiting when Redis unavailable."""
        with (
            patch("app.core.security.get_redis_client", return_value=None),
            patch("app.core.security.is_redis_available", return_value=False),
        ):
            # Make multiple failed attempts
            for i in range(MAX_PIN_ATTEMPTS - 1):
                with pytest.raises(HTTPException) as exc_info:
                    await pin_verifier.verify_pin("wrong", "user123")
                assert exc_info.value.status_code == 403

            # Final attempt should trigger lockout
            with pytest.raises(HTTPException) as exc_info:
                await pin_verifier.verify_pin("wrong", "user123")
            assert exc_info.value.status_code == 429

    async def test_fallback_clears_after_success(self, pin_verifier):
        """Test in-memory attempts cleared after successful verification."""
        with (
            patch("app.core.security.get_redis_client", return_value=None),
            patch("app.core.security.is_redis_available", return_value=False),
        ):
            # Make a failed attempt
            with pytest.raises(HTTPException):
                await pin_verifier.verify_pin("wrong", "user123")

            # Successful verification should clear attempts
            result = await pin_verifier.verify_pin("123456", "user123")
            assert result is True

            # New failed attempts should start from zero
            with pytest.raises(HTTPException) as exc_info:
                await pin_verifier.verify_pin("wrong", "user123")
            # Should show all attempts remaining
            assert str(MAX_PIN_ATTEMPTS) in exc_info.value.detail


@pytest.mark.asyncio
class TestRecordFailedAttempt:
    """Test recording failed PIN attempts."""

    async def test_record_attempt_in_redis(self, pin_verifier):
        """Test recording attempt in Redis."""
        mock_redis = AsyncMock()

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
        ):
            await pin_verifier._record_failed_attempt("user123")

        mock_redis.zadd.assert_awaited_once()
        mock_redis.expire.assert_awaited_once()
        mock_redis.zremrangebyscore.assert_awaited_once()

    async def test_record_attempt_redis_failure_uses_fallback(self, pin_verifier):
        """Test fallback when Redis fails to record attempt."""
        mock_redis = AsyncMock()
        mock_redis.zadd.side_effect = Exception("Redis error")

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
            patch.object(pin_verifier, "_record_failed_attempt_fallback") as mock_fallback,
        ):
            await pin_verifier._record_failed_attempt("user123")

        mock_fallback.assert_called_once_with("user123")

    async def test_record_attempt_in_memory(self, pin_verifier):
        """Test recording attempt in memory when Redis unavailable."""
        from app.core.security import _pin_attempts_fallback

        _pin_attempts_fallback.clear()

        with (
            patch("app.core.security.get_redis_client", return_value=None),
            patch("app.core.security.is_redis_available", return_value=False),
        ):
            await pin_verifier._record_failed_attempt("user123")

        assert "user123" in _pin_attempts_fallback
        assert len(_pin_attempts_fallback["user123"]) == 1


@pytest.mark.asyncio
class TestGetRecentAttempts:
    """Test retrieving recent PIN attempts."""

    async def test_get_attempts_from_redis(self, pin_verifier):
        """Test retrieving attempts from Redis."""
        now = datetime.utcnow()
        timestamps = [str((now - timedelta(minutes=i)).timestamp()) for i in range(3)]
        mock_redis = AsyncMock()
        mock_redis.zrangebyscore.return_value = timestamps

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
        ):
            attempts = await pin_verifier._get_recent_attempts("user123")

        assert len(attempts) == 3
        mock_redis.zrangebyscore.assert_awaited_once()

    async def test_get_attempts_redis_failure_uses_fallback(self, pin_verifier):
        """Test fallback when Redis fails to get attempts."""
        mock_redis = AsyncMock()
        mock_redis.zrangebyscore.side_effect = Exception("Redis error")

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
            patch.object(
                pin_verifier, "_get_recent_attempts_fallback", return_value=[]
            ) as mock_fallback,
        ):
            attempts = await pin_verifier._get_recent_attempts("user123")

        assert attempts == []
        mock_fallback.assert_called_once_with("user123")

    async def test_get_attempts_from_memory(self, pin_verifier):
        """Test retrieving attempts from memory when Redis unavailable."""
        from app.core.security import _pin_attempts_fallback

        _pin_attempts_fallback.clear()
        now = datetime.utcnow()
        _pin_attempts_fallback["user123"] = [now - timedelta(minutes=i) for i in range(3)]

        with (
            patch("app.core.security.get_redis_client", return_value=None),
            patch("app.core.security.is_redis_available", return_value=False),
        ):
            attempts = await pin_verifier._get_recent_attempts("user123")

        assert len(attempts) == 3


@pytest.mark.asyncio
class TestSetLockout:
    """Test setting lockout for users."""

    async def test_set_lockout_in_redis(self, pin_verifier):
        """Test setting lockout in Redis."""
        lockout_end = datetime.utcnow() + timedelta(minutes=15)
        mock_redis = AsyncMock()

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
        ):
            await pin_verifier._set_lockout("user123", lockout_end)

        mock_redis.set.assert_awaited_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "pin_lockout:user123"
        assert call_args[1]["ex"] == PIN_LOCKOUT_DURATION

    async def test_set_lockout_redis_failure_uses_fallback(self, pin_verifier):
        """Test fallback when Redis fails to set lockout."""
        from app.core.security import _locked_users_fallback

        _locked_users_fallback.clear()
        lockout_end = datetime.utcnow() + timedelta(minutes=15)
        mock_redis = AsyncMock()
        mock_redis.set.side_effect = Exception("Redis error")

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
        ):
            await pin_verifier._set_lockout("user123", lockout_end)

        assert "user123" in _locked_users_fallback

    async def test_set_lockout_in_memory(self, pin_verifier):
        """Test setting lockout in memory when Redis unavailable."""
        from app.core.security import _locked_users_fallback

        _locked_users_fallback.clear()
        lockout_end = datetime.utcnow() + timedelta(minutes=15)

        with (
            patch("app.core.security.get_redis_client", return_value=None),
            patch("app.core.security.is_redis_available", return_value=False),
        ):
            await pin_verifier._set_lockout("user123", lockout_end)

        assert "user123" in _locked_users_fallback
        assert _locked_users_fallback["user123"] == lockout_end


@pytest.mark.asyncio
class TestGetLockoutEnd:
    """Test retrieving lockout end time."""

    async def test_get_lockout_from_redis(self, pin_verifier):
        """Test retrieving lockout from Redis."""
        lockout_end = datetime.utcnow() + timedelta(minutes=15)
        mock_redis = AsyncMock()
        mock_redis.get.return_value = lockout_end.isoformat()

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
        ):
            result = await pin_verifier._get_lockout_end("user123")

        assert result is not None
        assert isinstance(result, datetime)
        mock_redis.get.assert_awaited_once_with("pin_lockout:user123")

    async def test_get_lockout_not_found_in_redis(self, pin_verifier):
        """Test when lockout not found in Redis."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
        ):
            result = await pin_verifier._get_lockout_end("user123")

        assert result is None

    async def test_get_lockout_redis_failure_uses_fallback(self, pin_verifier):
        """Test fallback when Redis fails to get lockout."""
        from app.core.security import _locked_users_fallback

        lockout_end = datetime.utcnow() + timedelta(minutes=15)
        _locked_users_fallback["user123"] = lockout_end
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis error")

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
        ):
            result = await pin_verifier._get_lockout_end("user123")

        assert result == lockout_end

    async def test_get_lockout_from_memory(self, pin_verifier):
        """Test retrieving lockout from memory when Redis unavailable."""
        from app.core.security import _locked_users_fallback

        _locked_users_fallback.clear()
        lockout_end = datetime.utcnow() + timedelta(minutes=15)
        _locked_users_fallback["user123"] = lockout_end

        with (
            patch("app.core.security.get_redis_client", return_value=None),
            patch("app.core.security.is_redis_available", return_value=False),
        ):
            result = await pin_verifier._get_lockout_end("user123")

        assert result == lockout_end


@pytest.mark.asyncio
class TestClearAttempts:
    """Test clearing failed attempts and lockout."""

    async def test_clear_attempts_in_redis(self, pin_verifier):
        """Test clearing attempts in Redis."""
        mock_redis = AsyncMock()

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
        ):
            await pin_verifier._clear_attempts("user123")

        mock_redis.delete.assert_awaited_once_with("pin_attempts:user123", "pin_lockout:user123")

    async def test_clear_attempts_redis_failure_uses_fallback(self, pin_verifier):
        """Test fallback when Redis fails to clear attempts."""
        from app.core.security import _locked_users_fallback, _pin_attempts_fallback

        _pin_attempts_fallback["user123"] = [datetime.utcnow()]
        _locked_users_fallback["user123"] = datetime.utcnow()
        mock_redis = AsyncMock()
        mock_redis.delete.side_effect = Exception("Redis error")

        with (
            patch("app.core.security.get_redis_client", return_value=mock_redis),
            patch("app.core.security.is_redis_available", return_value=True),
        ):
            await pin_verifier._clear_attempts("user123")

        assert len(_pin_attempts_fallback["user123"]) == 0
        assert "user123" not in _locked_users_fallback

    async def test_clear_attempts_in_memory(self, pin_verifier):
        """Test clearing attempts in memory when Redis unavailable."""
        from app.core.security import _locked_users_fallback, _pin_attempts_fallback

        _pin_attempts_fallback.clear()
        _locked_users_fallback.clear()
        _pin_attempts_fallback["user123"] = [datetime.utcnow()]
        _locked_users_fallback["user123"] = datetime.utcnow()

        with (
            patch("app.core.security.get_redis_client", return_value=None),
            patch("app.core.security.is_redis_available", return_value=False),
        ):
            await pin_verifier._clear_attempts("user123")

        assert len(_pin_attempts_fallback["user123"]) == 0
        assert "user123" not in _locked_users_fallback

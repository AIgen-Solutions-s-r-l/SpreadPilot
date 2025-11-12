"""
Security module for SpreadPilot Admin API.
Implements PIN verification for dangerous endpoints and security utilities.
"""

import re
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from spreadpilot_core.logging.logger import get_logger

from ..db.mongodb import get_db
from ..db.redis_client import get_redis_client, is_redis_available

logger = get_logger(__name__)

# Security configuration
PIN_LENGTH = 6
MAX_PIN_ATTEMPTS = 3
PIN_LOCKOUT_DURATION = 900  # 15 minutes in seconds
PIN_EXPIRY_DAYS = 90

# Dangerous endpoints requiring PIN verification
DANGEROUS_ENDPOINTS = [
    "/api/v1/followers/{follower_id}/delete",
    "/api/v1/positions/close-all",
    "/api/v1/settings/reset",
    "/api/v1/trading/emergency-stop",
    "/api/v1/database/purge",
    "/api/v1/credentials/rotate",
]

# Password context for PIN hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory fallback rate limiting storage (only used if Redis unavailable)
_pin_attempts_fallback: dict[str, list[datetime]] = defaultdict(list)
_locked_users_fallback: dict[str, datetime] = {}

# Security headers
security = HTTPBearer()


class PINVerification:
    """
    PIN verification system for dangerous operations.
    Implements rate limiting and lockout mechanisms.
    """

    def __init__(self):
        self.pin_hash: str | None = None
        self.pin_created_at: datetime | None = None
        self.last_rotation: datetime | None = None

    def set_pin(self, pin: str) -> None:
        """
        Set a new PIN with validation.

        Args:
            pin: The PIN to set (must be 6+ digits)

        Raises:
            ValueError: If PIN doesn't meet requirements
        """
        if not self._validate_pin_complexity(pin):
            raise ValueError("PIN must be at least 6 digits and not sequential")

        self.pin_hash = pwd_context.hash(pin)
        self.pin_created_at = datetime.utcnow()
        self.last_rotation = datetime.utcnow()

        logger.info("PIN updated successfully")

    async def verify_pin(self, pin: str, user_id: str) -> bool:
        """
        Verify PIN with rate limiting.

        Args:
            pin: The PIN to verify
            user_id: User identifier for rate limiting

        Returns:
            bool: True if PIN is valid

        Raises:
            HTTPException: If user is locked out or PIN expired
        """
        # Check if user is locked out
        lockout_end = await self._get_lockout_end(user_id)
        if lockout_end:
            if datetime.utcnow() < lockout_end:
                remaining = int((lockout_end - datetime.utcnow()).total_seconds())
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed attempts. Try again in {remaining} seconds.",
                )
            else:
                # Lockout expired, clear attempts
                await self._clear_attempts(user_id)

        # Check PIN expiry
        if self.pin_created_at:
            days_old = (datetime.utcnow() - self.pin_created_at).days
            if days_old > PIN_EXPIRY_DAYS:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="PIN expired. Please set a new PIN.",
                )

        # Verify PIN
        if not self.pin_hash or not pwd_context.verify(pin, self.pin_hash):
            # Record failed attempt
            await self._record_failed_attempt(user_id)

            # Check if user should be locked out
            attempts = await self._get_recent_attempts(user_id)
            if len(attempts) >= MAX_PIN_ATTEMPTS:
                lockout_end = datetime.utcnow() + timedelta(seconds=PIN_LOCKOUT_DURATION)
                await self._set_lockout(user_id, lockout_end)
                logger.warning(f"User {user_id} locked out due to multiple failed PIN attempts")

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed attempts. Account locked for {PIN_LOCKOUT_DURATION // 60} minutes.",
                )

            remaining_attempts = MAX_PIN_ATTEMPTS - len(attempts)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Invalid PIN. {remaining_attempts} attempts remaining.",
            )

        # Clear failed attempts on successful verification
        await self._clear_attempts(user_id)
        logger.info(f"PIN verified successfully for user {user_id}")

        return True

    def _validate_pin_complexity(self, pin: str) -> bool:
        """
        Validate PIN complexity requirements.

        Args:
            pin: The PIN to validate

        Returns:
            bool: True if PIN meets requirements
        """
        # Check length
        if len(pin) < PIN_LENGTH:
            return False

        # Check if all digits
        if not pin.isdigit():
            return False

        # Check for sequential patterns
        if self._is_sequential(pin):
            return False

        # Check for repeated digits
        if len(set(pin)) == 1:
            return False

        # Check for common patterns
        common_patterns = ["123456", "000000", "111111", "123123", "012345"]
        if pin in common_patterns:
            return False

        return True

    def _is_sequential(self, pin: str) -> bool:
        """Check if PIN is sequential (e.g., 123456, 654321)."""
        ascending = all(int(pin[i]) == int(pin[i - 1]) + 1 for i in range(1, len(pin)))
        descending = all(int(pin[i]) == int(pin[i - 1]) - 1 for i in range(1, len(pin)))
        return ascending or descending

    async def _record_failed_attempt(self, user_id: str) -> None:
        """Record a failed PIN attempt (uses Redis if available, otherwise in-memory)."""
        redis_client = get_redis_client()

        if redis_client and is_redis_available():
            # Use Redis sorted set with timestamp as score
            key = f"pin_attempts:{user_id}"
            timestamp = datetime.utcnow().timestamp()

            try:
                # Add attempt with timestamp as score
                await redis_client.zadd(key, {str(timestamp): timestamp})

                # Set expiry on the key
                await redis_client.expire(key, PIN_LOCKOUT_DURATION)

                # Clean up old attempts
                cutoff = timestamp - PIN_LOCKOUT_DURATION
                await redis_client.zremrangebyscore(key, "-inf", cutoff)
            except Exception as e:
                logger.error(f"Failed to record attempt in Redis: {e}", exc_info=True)
                # Fallback to in-memory
                self._record_failed_attempt_fallback(user_id)
        else:
            # Fallback to in-memory storage
            self._record_failed_attempt_fallback(user_id)

    def _record_failed_attempt_fallback(self, user_id: str) -> None:
        """Fallback: Record failed attempt in memory."""
        _pin_attempts_fallback[user_id].append(datetime.utcnow())

        # Clean up old attempts
        cutoff = datetime.utcnow() - timedelta(seconds=PIN_LOCKOUT_DURATION)
        _pin_attempts_fallback[user_id] = [
            attempt for attempt in _pin_attempts_fallback[user_id] if attempt > cutoff
        ]

    async def _get_recent_attempts(self, user_id: str) -> list[datetime]:
        """Get recent PIN attempts within the lockout window."""
        redis_client = get_redis_client()

        if redis_client and is_redis_available():
            key = f"pin_attempts:{user_id}"
            cutoff = datetime.utcnow().timestamp() - PIN_LOCKOUT_DURATION

            try:
                # Get attempts after cutoff
                attempts = await redis_client.zrangebyscore(key, cutoff, "+inf")
                # Using utcfromtimestamp since we store timestamps in UTC
                return [datetime.utcfromtimestamp(float(ts)) for ts in attempts]
            except Exception as e:
                logger.error(f"Failed to get attempts from Redis: {e}", exc_info=True)
                # Fallback to in-memory
                return self._get_recent_attempts_fallback(user_id)
        else:
            # Fallback to in-memory storage
            return self._get_recent_attempts_fallback(user_id)

    def _get_recent_attempts_fallback(self, user_id: str) -> list[datetime]:
        """Fallback: Get recent attempts from memory."""
        cutoff = datetime.utcnow() - timedelta(seconds=PIN_LOCKOUT_DURATION)
        return [attempt for attempt in _pin_attempts_fallback[user_id] if attempt > cutoff]

    async def _set_lockout(self, user_id: str, lockout_end: datetime) -> None:
        """Set lockout time for a user."""
        redis_client = get_redis_client()

        if redis_client and is_redis_available():
            key = f"pin_lockout:{user_id}"

            try:
                # Store lockout end time
                await redis_client.set(key, lockout_end.isoformat(), ex=PIN_LOCKOUT_DURATION)
            except Exception as e:
                logger.error(f"Failed to set lockout in Redis: {e}", exc_info=True)
                # Fallback to in-memory
                _locked_users_fallback[user_id] = lockout_end
        else:
            # Fallback to in-memory storage
            _locked_users_fallback[user_id] = lockout_end

    async def _get_lockout_end(self, user_id: str) -> datetime | None:
        """Get lockout end time for a user."""
        redis_client = get_redis_client()

        if redis_client and is_redis_available():
            key = f"pin_lockout:{user_id}"

            try:
                lockout_str = await redis_client.get(key)
                if lockout_str:
                    return datetime.fromisoformat(lockout_str)
                return None
            except Exception as e:
                logger.error(f"Failed to get lockout from Redis: {e}", exc_info=True)
                # Fallback to in-memory
                return _locked_users_fallback.get(user_id)
        else:
            # Fallback to in-memory storage
            return _locked_users_fallback.get(user_id)

    async def _clear_attempts(self, user_id: str) -> None:
        """Clear failed attempts and lockout for a user."""
        redis_client = get_redis_client()

        if redis_client and is_redis_available():
            try:
                await redis_client.delete(f"pin_attempts:{user_id}", f"pin_lockout:{user_id}")
            except Exception as e:
                logger.error(f"Failed to clear attempts in Redis: {e}", exc_info=True)
                # Fallback to in-memory
                if user_id in _pin_attempts_fallback:
                    _pin_attempts_fallback[user_id].clear()
                if user_id in _locked_users_fallback:
                    _locked_users_fallback.pop(user_id, None)
        else:
            # Fallback to in-memory storage
            if user_id in _pin_attempts_fallback:
                _pin_attempts_fallback[user_id].clear()
            if user_id in _locked_users_fallback:
                _locked_users_fallback.pop(user_id, None)

    def is_pin_required(self, endpoint: str) -> bool:
        """
        Check if an endpoint requires PIN verification.

        Args:
            endpoint: The endpoint path

        Returns:
            bool: True if PIN is required
        """
        # Normalize endpoint
        endpoint = endpoint.rstrip("/")

        # Check exact matches and patterns
        for dangerous_endpoint in DANGEROUS_ENDPOINTS:
            # Handle parameterized endpoints
            if "{" in dangerous_endpoint:
                pattern = dangerous_endpoint.replace("{follower_id}", r"[^/]+")
                pattern = pattern.replace("{", r"\{").replace("}", r"\}")
                if re.match(pattern, endpoint):
                    return True
            elif endpoint == dangerous_endpoint:
                return True

        return False


# Global PIN verification instance
pin_verifier = PINVerification()


async def verify_dangerous_operation(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_pin: str | None = Header(None, description="PIN for dangerous operations"),
    x_user_id: str | None = Header(None, description="User identifier"),
) -> None:
    """
    FastAPI dependency to verify PIN for dangerous operations.

    Args:
        credentials: JWT token from Authorization header
        x_pin: PIN from X-PIN header
        x_user_id: User identifier from X-User-ID header

    Raises:
        HTTPException: If PIN is missing or invalid
    """
    if not x_pin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-PIN header required for this operation",
        )

    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-ID header required for this operation",
        )

    # Verify PIN
    await pin_verifier.verify_pin(x_pin, x_user_id)


def get_security_headers() -> dict[str, str]:
    """
    Get security headers for responses.

    Returns:
        Dict of security headers
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' wss: https:;"
        ),
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    }


async def store_audit_log(audit_entry: dict) -> None:
    """
    Store audit log entry in MongoDB.

    Args:
        audit_entry: Dictionary containing audit log data
    """
    try:
        db = await get_db()
        audit_collection = db.security_audit_logs

        # Add created_at timestamp for indexing
        audit_entry["created_at"] = datetime.utcnow()

        await audit_collection.insert_one(audit_entry)
        logger.debug(f"Stored audit log entry for user {audit_entry.get('user_id')}")
    except Exception as e:
        # Don't fail the request if audit logging fails, but log the error
        logger.error(f"Failed to store audit log: {e}", exc_info=True)


class SecurityAudit:
    """
    Security audit logging for dangerous operations.
    """

    @staticmethod
    async def log_dangerous_operation(
        user_id: str,
        endpoint: str,
        operation: str,
        details: dict | None = None,
        request: Request | None = None,
    ) -> None:
        """
        Log a dangerous operation for audit trail.

        Args:
            user_id: User who performed the operation
            endpoint: API endpoint accessed
            operation: Description of the operation
            details: Additional details to log
            request: FastAPI Request object to extract IP and user agent
        """
        # Extract IP address and user agent from request if available
        ip_address = "0.0.0.0"
        user_agent = "Unknown"

        if request:
            # Get real IP from X-Forwarded-For header (if behind proxy) or direct client
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # X-Forwarded-For can contain multiple IPs, take the first one
                ip_address = forwarded_for.split(",")[0].strip()
            elif request.client:
                ip_address = request.client.host

            # Get user agent
            user_agent = request.headers.get("User-Agent", "Unknown")

        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "endpoint": endpoint,
            "operation": operation,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        logger.warning(f"SECURITY_AUDIT: {audit_entry}")

        # Store in database
        await store_audit_log(audit_entry)

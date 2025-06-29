"""Alert router with exponential backoff and MongoDB failure tracking."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from spreadpilot_core.models.alert import AlertEvent

from ..config import settings
from .alert_router import AlertRouter

logger = logging.getLogger(__name__)


class BackoffAlertRouter:
    """Alert router with 3-stride exponential backoff and failure tracking."""

    def __init__(
        self,
        mongo_url: str | None = None,
        mongo_db: str | None = None,
        base_delay: float = 1.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ):
        """Initialize the backoff router.

        Args:
            mongo_url: MongoDB connection URL
            mongo_db: MongoDB database name
            base_delay: Base delay in seconds for first retry
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff factor
        """
        self.mongo_url = mongo_url or settings.MONGO_URI
        self.mongo_db = mongo_db or settings.MONGO_DB_NAME or "spreadpilot"
        self.base_delay = base_delay
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.mongo_client: AsyncIOMotorClient | None = None
        self.alert_router = AlertRouter()

    async def connect(self):
        """Connect to MongoDB."""
        if not self.mongo_client:
            self.mongo_client = AsyncIOMotorClient(self.mongo_url)
            logger.info("Connected to MongoDB for alert tracking")

    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.mongo_client:
            self.mongo_client.close()
            self.mongo_client = None
            logger.info("Disconnected from MongoDB")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        await self.alert_router.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.alert_router.__aexit__(exc_type, exc_val, exc_tb)
        await self.disconnect()

    async def save_alert_attempt(
        self,
        alert_event: AlertEvent,
        attempt: int,
        success: bool,
        error: str | None = None,
        results: dict[str, Any] | None = None,
    ):
        """Save alert attempt to MongoDB.

        Args:
            alert_event: The alert event
            attempt: Attempt number (1-based)
            success: Whether the attempt was successful
            error: Error message if failed
            results: Routing results if available
        """
        if not self.mongo_client:
            return

        db = self.mongo_client[self.mongo_db]
        collection = db.alert_attempts

        document = {
            "alert_id": f"{alert_event.event_type.value}_{alert_event.timestamp.isoformat()}",
            "event_type": alert_event.event_type.value,
            "timestamp": alert_event.timestamp,
            "message": alert_event.message,
            "params": alert_event.params,
            "attempt": attempt,
            "attempt_time": datetime.now(UTC),
            "success": success,
            "error": error,
            "results": results,
            "status": (
                "success"
                if success
                else ("failed" if attempt >= self.max_retries else "retrying")
            ),
        }

        await collection.insert_one(document)
        logger.info(
            f"Saved alert attempt {attempt} for {alert_event.event_type.value} to MongoDB"
        )

    async def mark_alert_failed(self, alert_event: AlertEvent, final_error: str):
        """Mark an alert as permanently failed in MongoDB.

        Args:
            alert_event: The alert event
            final_error: Final error message
        """
        if not self.mongo_client:
            return

        db = self.mongo_client[self.mongo_db]
        collection = db.failed_alerts

        document = {
            "alert_id": f"{alert_event.event_type.value}_{alert_event.timestamp.isoformat()}",
            "event_type": alert_event.event_type.value,
            "timestamp": alert_event.timestamp,
            "message": alert_event.message,
            "params": alert_event.params,
            "failed_at": datetime.now(UTC),
            "final_error": final_error,
            "total_attempts": self.max_retries,
        }

        await collection.insert_one(document)
        logger.error(
            f"Marked alert {alert_event.event_type.value} as permanently failed in MongoDB"
        )

    async def route_alert_with_backoff(self, alert_event: AlertEvent) -> dict[str, Any]:
        """Route alert with exponential backoff retry logic.

        Args:
            alert_event: Alert event to route

        Returns:
            Final routing results

        Raises:
            Exception: If all retry attempts fail
        """
        last_error = None
        last_results = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Routing alert {alert_event.event_type.value}, attempt {attempt}/{self.max_retries}"
                )

                # Try to route the alert
                results = await self.alert_router.route_alert(alert_event)

                # Save successful attempt
                await self.save_alert_attempt(
                    alert_event, attempt, success=True, results=results
                )

                logger.info(
                    f"Successfully routed alert {alert_event.event_type.value} on attempt {attempt}"
                )
                return results

            except Exception as e:
                last_error = str(e)
                logger.error(f"Failed to route alert on attempt {attempt}: {e}")

                # Save failed attempt
                await self.save_alert_attempt(
                    alert_event,
                    attempt,
                    success=False,
                    error=last_error,
                    results=last_results,
                )

                # If this was the last attempt, mark as permanently failed
                if attempt == self.max_retries:
                    await self.mark_alert_failed(alert_event, last_error)
                    raise Exception(
                        f"Failed to route alert after {self.max_retries} attempts: {last_error}"
                    )

                # Calculate exponential backoff delay
                delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
                logger.info(f"Waiting {delay:.1f} seconds before retry...")
                await asyncio.sleep(delay)

        # Should never reach here, but just in case
        raise Exception(f"Failed to route alert after {self.max_retries} attempts")

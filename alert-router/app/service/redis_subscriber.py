"""Redis stream subscriber for alert events."""

import asyncio
import json
import logging
from typing import Any

import redis.asyncio as redis

from spreadpilot_core.models.alert import AlertEvent

from ..config import settings
from .backoff_router import BackoffAlertRouter

logger = logging.getLogger(__name__)


class RedisAlertSubscriber:
    """Subscribes to Redis alerts stream and routes alerts."""

    def __init__(
        self,
        redis_url: str | None = None,
        stream_key: str = "alerts",
        consumer_group: str = "alert-router-group",
        consumer_name: str = "alert-router-1",
    ):
        """Initialize the Redis subscriber.

        Args:
            redis_url: Redis connection URL
            stream_key: Redis stream key to subscribe to
            consumer_group: Consumer group name
            consumer_name: Consumer name within the group
        """
        self.redis_url = redis_url or settings.REDIS_URL or "redis://localhost:6379"
        self.stream_key = stream_key
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.redis_client: redis.Redis | None = None
        self._running = False

    async def connect(self):
        """Connect to Redis."""
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Connected to Redis at {self.redis_url}")

            # Create consumer group if it doesn't exist
            try:
                await self.redis_client.xgroup_create(
                    self.stream_key, self.consumer_group, id="0-0", mkstream=True
                )
                logger.info(
                    f"Created consumer group '{self.consumer_group}' for stream '{self.stream_key}'"
                )
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.info(
                        f"Consumer group '{self.consumer_group}' already exists"
                    )
                else:
                    raise

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Disconnected from Redis")

    async def process_message(self, message_id: str, data: dict[str, Any]) -> bool:
        """Process a single message from the stream.

        Args:
            message_id: Redis message ID
            data: Message data

        Returns:
            True if processed successfully, False otherwise
        """
        try:
            # Parse the alert event
            alert_data = json.loads(data.get("alert", "{}"))
            alert_event = AlertEvent(**alert_data)

            logger.info(
                f"Processing alert {message_id}: {alert_event.event_type.value}"
            )

            # Route the alert with exponential backoff
            async with BackoffAlertRouter() as router:
                await router.route_alert_with_backoff(alert_event)

            # Acknowledge the message
            await self.redis_client.xack(
                self.stream_key, self.consumer_group, message_id
            )

            logger.info(f"Successfully processed alert {message_id}")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode alert JSON for message {message_id}: {e}")
            # Still acknowledge to prevent reprocessing of bad messages
            await self.redis_client.xack(
                self.stream_key, self.consumer_group, message_id
            )
            return False

        except Exception as e:
            logger.error(f"Failed to process alert {message_id}: {e}", exc_info=True)
            # Don't acknowledge - let it be retried
            return False

    async def run(self):
        """Run the subscriber loop."""
        await self.connect()
        self._running = True

        logger.info(f"Starting Redis stream subscriber for '{self.stream_key}'")

        while self._running:
            try:
                # Read messages from the stream
                messages = await self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_key: ">"},  # Read only new messages
                    count=10,
                    block=1000,  # Block for 1 second
                )

                if messages:
                    for stream_name, stream_messages in messages:
                        for message_id, data in stream_messages:
                            await self.process_message(message_id, data)

            except asyncio.CancelledError:
                logger.info("Subscriber cancelled")
                break
            except Exception as e:
                logger.error(f"Error in subscriber loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying

        await self.disconnect()
        logger.info("Redis stream subscriber stopped")

    async def stop(self):
        """Stop the subscriber."""
        self._running = False

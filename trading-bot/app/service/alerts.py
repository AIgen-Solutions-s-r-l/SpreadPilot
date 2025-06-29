"""Alert manager for SpreadPilot trading service."""

import uuid
from datetime import datetime  # Added datetime

from bson import ObjectId  # Added ObjectId

from spreadpilot_core.logging import get_logger
from spreadpilot_core.models import Alert, AlertSeverity, AlertType
from spreadpilot_core.utils.telegram import send_alert_message

logger = get_logger(__name__)


class AlertManager:
    """Manager for alerts and notifications."""

    def __init__(self, service):
        """Initialize the alert manager.

        Args:
            service: Trading service instance
        """
        self.service = service

        logger.info("Initialized alert manager")

    async def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        follower_id: str | None = None,
    ) -> str | None:
        """Create an alert and send notifications.

        Args:
            alert_type: Alert type
            severity: Alert severity
            message: Alert message
            follower_id: Follower ID (optional)

        Returns:
            Alert ID or None if creation failed
        """
        try:
            # Create alert ID
            alert_id = str(uuid.uuid4())

            # Create alert
            alert = Alert(
                id=alert_id,
                follower_id=follower_id,
                severity=severity,
                type=alert_type,
                message=message,
            )

            # Save alert to MongoDB
            if not self.service.mongo_db:
                logger.error("MongoDB not initialized, cannot save alert.")
                raise RuntimeError("MongoDB client not available in AlertManager")

            alerts_collection = self.service.mongo_db["alerts"]
            # Use model_dump(by_alias=True) to get MongoDB-compatible dict (_id)
            alert_dict = alert.model_dump(by_alias=True, exclude_none=True)
            # Ensure the ID is an ObjectId if it exists, though insert_one handles it if not present
            if "_id" in alert_dict:
                alert_dict["_id"] = ObjectId(alert_dict["_id"])
            else:
                # If ID wasn't pre-generated and passed to model, let Mongo generate it
                # Or ensure the model always has an ID before this point
                pass  # Assuming alert.id was set with uuid4() as before

            await alerts_collection.insert_one(alert_dict)
            logger.debug(f"Saved alert {alert.id} to MongoDB.")

            logger.info(
                "Created alert",
                alert_id=alert_id,
                follower_id=follower_id,
                type=alert_type,
                severity=severity,
            )

            # Send notifications
            await self._send_notifications(
                alert_id=alert_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                follower_id=follower_id,
            )

            return alert_id
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return None

    async def _send_notifications(
        self,
        alert_id: str,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        follower_id: str | None = None,
    ):
        """Send notifications for an alert.

        Args:
            alert_id: Alert ID
            alert_type: Alert type
            severity: Alert severity
            message: Alert message
            follower_id: Follower ID (optional)
        """
        try:
            # Send Telegram notification for critical alerts
            if severity == AlertSeverity.CRITICAL:
                await self._send_telegram_notification(
                    alert_type=alert_type,
                    message=message,
                    follower_id=follower_id,
                )

            # TODO: Send email notification
            # This would be implemented in a future version
        except Exception as e:
            logger.error(f"Error sending notifications for alert {alert_id}: {e}")

    async def _send_telegram_notification(
        self,
        alert_type: AlertType,
        message: str,
        follower_id: str | None = None,
    ):
        """Send Telegram notification.

        Args:
            alert_type: Alert type
            message: Alert message
            follower_id: Follower ID (optional)
        """
        try:
            # Check if Telegram settings are configured
            if (
                not self.service.settings.telegram_bot_token
                or not self.service.settings.telegram_chat_id
            ):
                logger.warning(
                    "Telegram settings not configured, skipping notification"
                )
                return

            # Send alert message
            await send_alert_message(
                alert_type=alert_type.value,
                message=message,
                follower_id=follower_id,
                dashboard_url=self.service.settings.dashboard_url,
                bot_token=self.service.settings.telegram_bot_token,
                chat_id=self.service.settings.telegram_chat_id,
            )

            logger.info(
                "Sent Telegram notification",
                alert_type=alert_type,
                follower_id=follower_id,
            )
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")

    async def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an alert.

        Args:
            alert_id: Alert ID
            user: User who acknowledged the alert

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.service.mongo_db:
                logger.error("MongoDB not initialized, cannot acknowledge alert.")
                raise RuntimeError("MongoDB client not available in AlertManager")

            alerts_collection = self.service.mongo_db["alerts"]

            # Convert string ID to ObjectId for querying
            try:
                alert_object_id = ObjectId(alert_id)
            except Exception:
                logger.error(f"Invalid alert ID format: {alert_id}")
                return False

            # Find the alert document
            alert_doc = await alerts_collection.find_one({"_id": alert_object_id})

            # Check if alert exists
            if not alert_doc:
                logger.error(f"Alert not found: {alert_id}")
                return False

            # Check if already acknowledged
            if alert_doc.get("acknowledged", False):
                logger.warning(f"Alert already acknowledged: {alert_id}")
                return True

            # Update alert in MongoDB
            update_result = await alerts_collection.update_one(
                {"_id": alert_object_id},
                {
                    "$set": {
                        "acknowledged": True,
                        "acknowledged_at": datetime.now(
                            datetime.timezone.utc
                        ),  # Use timezone-aware UTC now
                        "acknowledged_by": user,
                    }
                },
            )

            if update_result.modified_count == 0:
                # This might happen in a race condition if acknowledged between find_one and update_one
                logger.warning(
                    f"Alert {alert_id} was potentially acknowledged by another process concurrently, or update failed."
                )
                # Check again to be sure
                refreshed_doc = await alerts_collection.find_one(
                    {"_id": alert_object_id}
                )
                if refreshed_doc and refreshed_doc.get("acknowledged"):
                    return True  # It is acknowledged now
                else:
                    logger.error(
                        f"Failed to acknowledge alert {alert_id} despite finding it initially."
                    )
                    return False  # Update failed

            logger.info(
                "Acknowledged alert",
                alert_id=alert_id,
                user=user,
            )

            return True
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False

"""Alert manager for SpreadPilot trading service."""

import uuid
from typing import Optional

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
        follower_id: Optional[str] = None,
    ) -> Optional[str]:
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
            
            # Save alert to Firestore
            self.service.db.collection("alerts").document(alert_id).set(alert.to_dict())
            
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
        follower_id: Optional[str] = None,
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
        follower_id: Optional[str] = None,
    ):
        """Send Telegram notification.

        Args:
            alert_type: Alert type
            message: Alert message
            follower_id: Follower ID (optional)
        """
        try:
            # Check if Telegram settings are configured
            if not self.service.settings.telegram_bot_token or not self.service.settings.telegram_chat_id:
                logger.warning("Telegram settings not configured, skipping notification")
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
            # Get alert document
            alert_ref = self.service.db.collection("alerts").document(alert_id)
            alert_doc = alert_ref.get()
            
            # Check if alert exists
            if not alert_doc.exists:
                logger.error(f"Alert not found: {alert_id}")
                return False
            
            # Get alert data
            alert_data = alert_doc.to_dict()
            
            # Check if already acknowledged
            if alert_data.get("acknowledged", False):
                logger.warning(f"Alert already acknowledged: {alert_id}")
                return True
            
            # Update alert
            alert_ref.update({
                "acknowledged": True,
                "acknowledgedAt": datetime.datetime.now(),
                "acknowledgedBy": user,
            })
            
            logger.info(
                "Acknowledged alert",
                alert_id=alert_id,
                user=user,
            )
            
            return True
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False
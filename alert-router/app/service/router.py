import logging
from typing import Optional, Tuple

from spreadpilot_core.models.alert import AlertEvent, AlertType
from spreadpilot_core.utils.email import send_email
from spreadpilot_core.utils.telegram import send_telegram_message

from ..config import settings

logger = logging.getLogger(__name__)

def _generate_deep_link(event: AlertEvent) -> Optional[str]:
    """Generates a deep link to the dashboard based on the event type."""
    if not settings.DASHBOARD_BASE_URL:
        return None

    base_url = settings.DASHBOARD_BASE_URL.rstrip("/")
    params = event.params or {}

    # Basic links based on event type
    if event.event_type in [
        AlertType.COMPONENT_DOWN,
        AlertType.GATEWAY_UNREACHABLE,
        AlertType.WATCHDOG_FAILURE,
    ]:
        component = params.get("component_name", "system")
        return f"{base_url}/status?component={component}"
    elif event.event_type == AlertType.NO_MARGIN:
        account = params.get("account_id", "default")
        return f"{base_url}/accounts/{account}"
    elif event.event_type == AlertType.REPORT_FAILED:
        report_id = params.get("report_id", "latest")
        return f"{base_url}/reports/{report_id}"
    elif event.event_type in [
        AlertType.MID_TOO_LOW,
        AlertType.LIMIT_REACHED,
        AlertType.ASSIGNMENT_DETECTED,
        AlertType.ASSIGNMENT_COMPENSATED,
        AlertType.PARTIAL_FILL_HIGH,
    ]:
        follower_id = params.get("follower_id", None)
        if follower_id:
            return f"{base_url}/followers/{follower_id}"
        else:
            return f"{base_url}/dashboard"  # Fallback if no follower ID

    return f"{base_url}/dashboard"  # Default fallback

def _format_alert_message(event: AlertEvent) -> Tuple[str, str]:
    """Formats the alert subject and body."""
    deep_link = _generate_deep_link(event)
    link_text = f"\n\nDashboard Link: {deep_link}" if deep_link else ""

    subject = f"🚨 SpreadPilot Alert: {event.event_type.value}"
    body = (
        f"Critical Event: {event.event_type.value}\n"
        f"Timestamp: {event.timestamp.isoformat()}\n"
        f"Message: {event.message}\n"
    )

    if event.params:
        body += "Details:\n"
        for key, value in event.params.items():
            body += f"  - {key.replace('_', ' ').title()}: {value}\n"

    body += link_text
    return subject, body

async def route_alert(event: AlertEvent):
    """
    Routes the alert event to configured notification channels
    (Telegram, Email).
    """
    logger.info(f"Routing alert for event: {event.event_type.value}")
    subject, body = _format_alert_message(event)

    # Send to Telegram
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_ADMIN_IDS:
        logger.info(f"Sending alert to Telegram admins: {settings.TELEGRAM_ADMIN_IDS}")
        # Loop through admin IDs and send individually
        for chat_id in settings.TELEGRAM_ADMIN_IDS:
            try:
                logger.debug(f"Sending Telegram alert to chat_id: {chat_id}")
                await send_telegram_message(
                    bot_token=settings.TELEGRAM_BOT_TOKEN,
                    chat_id=chat_id,
                    message=body,
                )
                logger.info(f"Alert sent successfully via Telegram to {chat_id}.")
            except Exception as e:
                logger.error(f"Failed to send alert via Telegram to {chat_id}: {e}", exc_info=True)
    else:
        logger.warning("Telegram is not configured. Skipping Telegram notification.")

    # Send to Email
    if (
        settings.EMAIL_SENDER
        and settings.EMAIL_ADMIN_RECIPIENTS
        and settings.SMTP_HOST
    ):
        logger.info(f"Sending alert to email admins: {settings.EMAIL_ADMIN_RECIPIENTS}")
        # Loop through admin recipients and send individually
        for recipient_email in settings.EMAIL_ADMIN_RECIPIENTS:
            try:
                logger.debug(f"Sending Email alert to recipient: {recipient_email}")
                send_email(
                    from_email=settings.EMAIL_SENDER,
                    to_email=recipient_email,
                    subject=subject,
                    html_content=body,
                )
                logger.info(f"Alert sent successfully via Email to {recipient_email}.")
            except Exception as e:
                logger.error(f"Failed to send alert via Email to {recipient_email}: {e}", exc_info=True)
    else:
        logger.warning("Email is not configured. Skipping Email notification.")
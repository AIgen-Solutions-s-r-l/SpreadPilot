import logging
from typing import Optional

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

    # Basic links based on event type - adjust paths as needed for actual
    # dashboard routes
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


def _format_alert_message(event: AlertEvent) -> tuple[str, str]:
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
        logger.info(
            "Sending alert to Telegram admins: "
            f"{settings.TELEGRAM_ADMIN_IDS}"
        )
        try:
            # Assuming send_telegram_message is async or running in executor
            await send_telegram_message(
                bot_token=settings.TELEGRAM_BOT_TOKEN,
                chat_ids=settings.TELEGRAM_ADMIN_IDS,
                message=body,
            )
            logger.info("Alert sent successfully via Telegram.")
        except Exception as e:
            logger.error(
                f"Failed to send alert via Telegram: {e}", exc_info=True
            )
    else:
        logger.warning(
            "Telegram is not configured. Skipping Telegram notification."
        )

    # Send to Email
    if (
        settings.EMAIL_SENDER
        and settings.EMAIL_ADMIN_RECIPIENTS
        and settings.SMTP_HOST
    ):
        logger.info(
            "Sending alert to email admins: "
            f"{settings.EMAIL_ADMIN_RECIPIENTS}"
        )
        try:
            # Assuming send_email handles async or runs in executor if needed
            send_email(
                sender=settings.EMAIL_SENDER,
                recipients=settings.EMAIL_ADMIN_RECIPIENTS,
                subject=subject,
                body=body,
                smtp_host=settings.SMTP_HOST,
                smtp_port=settings.SMTP_PORT,
                smtp_user=settings.SMTP_USER,
                smtp_password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_TLS,
            )
            logger.info("Alert sent successfully via Email.")
        except Exception as e:
            logger.error(
                f"Failed to send alert via Email: {e}", exc_info=True
            )
    else:
        logger.warning(
            "Email is not configured. Skipping Email notification."
        )

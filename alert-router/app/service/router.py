import logging

from spreadpilot_core.models.alert import AlertEvent, AlertType

from ..config import settings

logger = logging.getLogger(__name__)


def _generate_deep_link(event: AlertEvent) -> str | None:
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
    (Telegram with Email fallback).
    """
    # Import here to avoid circular imports
    from .alert_router import AlertRouter

    async with AlertRouter() as router:
        await router.route_alert(event)

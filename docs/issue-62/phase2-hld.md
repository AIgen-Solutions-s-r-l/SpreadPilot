# Phase 2: High-Level Design - Issue #62

**Issue**: Implement Email Alert Notifications
**Date**: 2025-11-11
**Effort**: 4 hours (Quick Win)

## Design Summary

Add email notification capability to `trading-bot/app/service/alerts.py` by implementing the TODO at line 126 using existing `spreadpilot_core.utils.email.EmailSender`.

## Implementation Plan

### Add Method: `_send_email_notification()`

```python
async def _send_email_notification(
    self,
    alert_type: AlertType,
    severity: AlertSeverity,
    message: str,
    follower_id: str | None = None,
):
    """Send email notification for alert."""
    # 1. Check if email is configured
    if not self.service.settings.sendgrid_api_key or not self.service.settings.admin_email:
        logger.warning("Email settings not configured, skipping notification")
        return

    # 2. Initialize EmailSender (cached)
    # 3. Format HTML email
    # 4. Send via SendGrid
    # 5. Log result
```

### Update `_send_notifications()` - Remove TODO

```python
async def _send_notifications(self, ...):
    # Send Telegram for CRITICAL
    if severity == AlertSeverity.CRITICAL:
        await self._send_telegram_notification(...)

    # Send email for all severities
    await self._send_email_notification(
        alert_type, severity, message, follower_id
    )
```

## Design Principles

- ✅ **Fail gracefully**: Email failure doesn't block Telegram
- ✅ **Reuse existing**: Use `EmailSender` class
- ✅ **Observable**: Log all attempts
- ✅ **Configurable**: Honor existing settings

## Testing Strategy

1. Unit test: Email configuration check
2. Unit test: Email sending (mocked)
3. Manual test: Send real email

**Effort**: 4 hours total

---

**Approved**: ✅ Proceed to Phase 3

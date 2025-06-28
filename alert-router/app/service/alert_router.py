"""Enhanced alert router with Telegram priority and email fallback."""

import logging
from typing import Optional, Tuple, List
import httpx
import asyncio
from datetime import datetime

from spreadpilot_core.models.alert import AlertEvent, AlertType
from spreadpilot_core.utils.email import send_email

from ..config import settings

logger = logging.getLogger(__name__)


class AlertRouter:
    """Routes alerts to notification channels with fallback support."""
    
    def __init__(
        self,
        telegram_token: Optional[str] = None,
        telegram_admin_ids: Optional[List[str]] = None,
        email_sender: Optional[str] = None,
        email_recipients: Optional[List[str]] = None,
        smtp_config: Optional[dict] = None,
        dashboard_base_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        """Initialize the alert router with configuration.
        
        Args:
            telegram_token: Telegram bot token
            telegram_admin_ids: List of Telegram chat IDs to notify
            email_sender: Email sender address
            email_recipients: List of email recipients
            smtp_config: SMTP configuration dict
            dashboard_base_url: Base URL for dashboard deep links
            http_client: Optional httpx client for testing
        """
        self.telegram_token = telegram_token or settings.TELEGRAM_BOT_TOKEN
        self.telegram_admin_ids = telegram_admin_ids or settings.TELEGRAM_ADMIN_IDS
        self.email_sender = email_sender or settings.EMAIL_SENDER
        self.email_recipients = email_recipients or settings.EMAIL_ADMIN_RECIPIENTS
        self.smtp_config = smtp_config or {
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "user": settings.SMTP_USER,
            "password": settings.SMTP_PASSWORD,
            "tls": settings.SMTP_TLS,
        }
        self.dashboard_base_url = dashboard_base_url or settings.DASHBOARD_BASE_URL
        self._http_client = http_client
        
    async def __aenter__(self):
        """Async context manager entry."""
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._http_client and not hasattr(self._http_client, '_test_client'):
            await self._http_client.aclose()
    
    def _generate_deep_link(self, event: AlertEvent) -> Optional[str]:
        """Generate a deep link to the dashboard based on the event type."""
        if not self.dashboard_base_url:
            return None

        base_url = self.dashboard_base_url.rstrip("/")
        params = event.params or {}

        # Route based on event type
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
                return f"{base_url}/dashboard"

        return f"{base_url}/dashboard"
    
    def _format_alert_message(self, event: AlertEvent) -> Tuple[str, str, str]:
        """Format the alert for different channels.
        
        Returns:
            Tuple of (subject, plain_text, html_content)
        """
        deep_link = self._generate_deep_link(event)
        
        # Emoji based on severity
        emoji_map = {
            AlertType.COMPONENT_DOWN: "🔴",
            AlertType.GATEWAY_UNREACHABLE: "🔴",
            AlertType.WATCHDOG_FAILURE: "🔴",
            AlertType.NO_MARGIN: "⚠️",
            AlertType.REPORT_FAILED: "⚠️",
            AlertType.MID_TOO_LOW: "📊",
            AlertType.LIMIT_REACHED: "🎯",
            AlertType.ASSIGNMENT_DETECTED: "📋",
            AlertType.ASSIGNMENT_COMPENSATED: "✅",
            AlertType.PARTIAL_FILL_HIGH: "📈",
        }
        emoji = emoji_map.get(event.event_type, "🚨")
        
        subject = f"{emoji} SpreadPilot Alert: {event.event_type.value}"
        
        # Plain text format for Telegram
        plain_text = (
            f"{emoji} *{event.event_type.value}*\n\n"
            f"🕐 {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"📝 {event.message}\n"
        )
        
        if event.params:
            plain_text += "\n*Details:*\n"
            for key, value in event.params.items():
                formatted_key = key.replace('_', ' ').title()
                plain_text += f"• {formatted_key}: `{value}`\n"
        
        if deep_link:
            plain_text += f"\n🔗 [View in Dashboard]({deep_link})"
        
        # HTML format for email
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #d32f2f;">{emoji} {event.event_type.value}</h2>
            
            <p><strong>Timestamp:</strong> {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p><strong>Message:</strong> {event.message}</p>
            
            {self._format_details_html(event.params) if event.params else ''}
            
            {f'<p><a href="{deep_link}" style="background-color: #1976d2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 20px;">View in Dashboard</a></p>' if deep_link else ''}
            
            <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
            <p style="font-size: 0.9em; color: #666;">
                This is an automated alert from SpreadPilot. Do not reply to this message.
            </p>
        </body>
        </html>
        """
        
        return subject, plain_text, html_content
    
    def _format_details_html(self, params: dict) -> str:
        """Format event parameters as HTML."""
        if not params:
            return ""
            
        html = "<h3>Details:</h3><ul>"
        for key, value in params.items():
            formatted_key = key.replace('_', ' ').title()
            html += f"<li><strong>{formatted_key}:</strong> {value}</li>"
        html += "</ul>"
        return html
    
    async def send_telegram_alert(self, chat_id: str, message: str) -> bool:
        """Send alert via Telegram.
        
        Args:
            chat_id: Telegram chat ID
            message: Message to send (supports Markdown)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.telegram_token:
            logger.warning("Telegram token not configured")
            return False
            
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }
        
        try:
            if not self._http_client:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=payload)
            else:
                response = await self._http_client.post(url, json=payload)
                
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                logger.info(f"Telegram alert sent successfully to {chat_id}")
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description', 'Unknown error')}")
                return False
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Telegram HTTP error {e.response.status_code}: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram alert to {chat_id}: {e}", exc_info=True)
            return False
    
    async def send_email_alert(self, recipient: str, subject: str, html_content: str) -> bool:
        """Send alert via email.
        
        Args:
            recipient: Email recipient
            subject: Email subject
            html_content: HTML email content
            
        Returns:
            True if successful, False otherwise
        """
        if not all([self.email_sender, self.smtp_config.get("host")]):
            logger.warning("Email configuration incomplete")
            return False
            
        try:
            send_email(
                from_email=self.email_sender,
                to_email=recipient,
                subject=subject,
                html_content=html_content,
                smtp_host=self.smtp_config["host"],
                smtp_port=self.smtp_config["port"],
                smtp_user=self.smtp_config.get("user"),
                smtp_password=self.smtp_config.get("password"),
                use_tls=self.smtp_config.get("tls", True),
            )
            logger.info(f"Email alert sent successfully to {recipient}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert to {recipient}: {e}", exc_info=True)
            return False
    
    async def route_alert(self, event: AlertEvent) -> dict:
        """Route alert to notification channels with fallback.
        
        Args:
            event: Alert event to route
            
        Returns:
            Dictionary with routing results
        """
        logger.info(f"Routing alert: {event.event_type.value}")
        subject, telegram_msg, email_html = self._format_alert_message(event)
        
        results = {
            "telegram": {"attempted": 0, "success": 0, "failed": 0},
            "email": {"attempted": 0, "success": 0, "failed": 0},
            "fallback_used": False,
        }
        
        # Try Telegram first
        telegram_success = False
        if self.telegram_token and self.telegram_admin_ids:
            logger.info(f"Attempting Telegram delivery to {len(self.telegram_admin_ids)} recipients")
            
            tasks = []
            for chat_id in self.telegram_admin_ids:
                results["telegram"]["attempted"] += 1
                tasks.append(self.send_telegram_alert(chat_id, telegram_msg))
            
            # Send all Telegram messages concurrently
            telegram_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for idx, result in enumerate(telegram_results):
                if isinstance(result, Exception):
                    logger.error(f"Telegram send exception: {result}")
                    results["telegram"]["failed"] += 1
                elif result:
                    results["telegram"]["success"] += 1
                    telegram_success = True
                else:
                    results["telegram"]["failed"] += 1
        else:
            logger.warning("Telegram not configured, skipping")
        
        # If Telegram failed (or not configured), fall back to email
        if not telegram_success:
            logger.info("Telegram delivery failed or not configured, falling back to email")
            results["fallback_used"] = True
            
            if self.email_sender and self.email_recipients:
                logger.info(f"Attempting email delivery to {len(self.email_recipients)} recipients")
                
                tasks = []
                for recipient in self.email_recipients:
                    results["email"]["attempted"] += 1
                    tasks.append(self.send_email_alert(recipient, subject, email_html))
                
                # Send all emails concurrently
                email_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for idx, result in enumerate(email_results):
                    if isinstance(result, Exception):
                        logger.error(f"Email send exception: {result}")
                        results["email"]["failed"] += 1
                    elif result:
                        results["email"]["success"] += 1
                    else:
                        results["email"]["failed"] += 1
            else:
                logger.error("Email not configured, alert delivery failed completely!")
        
        # Log summary
        logger.info(f"Alert routing complete: {results}")
        
        # Raise if no notifications were sent successfully
        total_success = results["telegram"]["success"] + results["email"]["success"]
        if total_success == 0:
            raise Exception("Failed to deliver alert via any channel")
        
        return results


# Convenience function for backward compatibility
async def route_alert(event: AlertEvent) -> dict:
    """Route an alert using the default configuration."""
    async with AlertRouter() as router:
        return await router.route_alert(event)
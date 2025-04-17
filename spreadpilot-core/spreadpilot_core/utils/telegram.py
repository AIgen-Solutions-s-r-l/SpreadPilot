"""Telegram messaging utilities for SpreadPilot."""

import os
from typing import Optional

import aiohttp

from ..logging import get_logger

logger = get_logger(__name__)


class TelegramSender:
    """Telegram message sender."""

    def __init__(self, bot_token: str, chat_id: str):
        """Initialize the Telegram sender.

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        logger.info(
            "Initialized Telegram sender",
            chat_id=chat_id,
        )

    async def send_message(
        self,
        message: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = True,
    ) -> bool:
        """Send a message to Telegram.

        Args:
            message: Message text
            parse_mode: Parse mode (HTML or Markdown)
            disable_web_page_preview: Whether to disable web page preview

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            # Prepare payload
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": disable_web_page_preview,
            }
            
            # Send request
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload) as response:
                    # Check response
                    if response.status == 200:
                        response_json = await response.json()
                        if response_json.get("ok"):
                            logger.info(
                                "Telegram message sent successfully",
                                chat_id=self.chat_id,
                                message_id=response_json.get("result", {}).get("message_id"),
                            )
                            return True
                    
                    # Log error
                    error_text = await response.text()
                    logger.error(
                        f"Failed to send Telegram message: {error_text}",
                        chat_id=self.chat_id,
                        status=response.status,
                    )
                    return False
        except Exception as e:
            logger.error(
                f"Error sending Telegram message: {e}",
                chat_id=self.chat_id,
            )
            return False


async def send_telegram_message(
    message: str,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = True,
) -> bool:
    """Send a message to Telegram.

    Args:
        message: Message text
        bot_token: Telegram bot token (optional, defaults to TELEGRAM_BOT_TOKEN env var)
        chat_id: Telegram chat ID (optional, defaults to TELEGRAM_CHAT_ID env var)
        parse_mode: Parse mode (HTML or Markdown)
        disable_web_page_preview: Whether to disable web page preview

    Returns:
        True if message was sent successfully, False otherwise
    """
    # Get bot token from environment if not provided
    if not bot_token:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.error("Telegram bot token not provided")
            return False
    
    # Get chat ID from environment if not provided
    if not chat_id:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if not chat_id:
            logger.error("Telegram chat ID not provided")
            return False
    
    # Create Telegram sender
    sender = TelegramSender(bot_token, chat_id)
    
    # Send message
    return await sender.send_message(
        message=message,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
    )


async def send_alert_message(
    alert_type: str,
    message: str,
    follower_id: Optional[str] = None,
    dashboard_url: Optional[str] = None,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> bool:
    """Send an alert message to Telegram.

    Args:
        alert_type: Alert type (e.g., "COMPONENT_DOWN", "NO_MARGIN")
        message: Alert message
        follower_id: Follower ID (optional)
        dashboard_url: Dashboard URL (optional)
        bot_token: Telegram bot token (optional)
        chat_id: Telegram chat ID (optional)

    Returns:
        True if message was sent successfully, False otherwise
    """
    # Create formatted message
    formatted_message = f"<b>🚨 ALERT: {alert_type}</b>\n\n"
    
    # Add follower ID if provided
    if follower_id:
        formatted_message += f"<b>Follower:</b> {follower_id}\n\n"
    
    # Add message
    formatted_message += f"{message}\n"
    
    # Add dashboard link if provided
    if dashboard_url:
        # If follower ID is provided, add deep link to follower
        if follower_id and "?" not in dashboard_url:
            dashboard_url = f"{dashboard_url}?follower={follower_id}"
        
        formatted_message += f"\n<a href='{dashboard_url}'>View in Dashboard</a>"
    
    # Send message
    return await send_telegram_message(
        message=formatted_message,
        bot_token=bot_token,
        chat_id=chat_id,
    )
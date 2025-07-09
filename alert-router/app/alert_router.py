"""Alert Router Service for SpreadPilot.

Subscribes to Redis stream 'alerts' and routes them to Telegram and email.
"""

import asyncio
import json
import os
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

import aiosmtplib
import backoff
import httpx
import redis.asyncio as redis
from contextlib import asynccontextmanager
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel

from spreadpilot_core.logging import get_logger
from spreadpilot_core.models.alert import Alert, AlertEvent, AlertSeverity, AlertType
from spreadpilot_core.utils.vault import get_vault_client

logger = get_logger(__name__)


class AlertRouterConfig(BaseModel):
    """Configuration for alert router."""

    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_consumer_group: str = "alert-router"
    redis_consumer_name: str = os.getenv("HOSTNAME", "alert-router-1")

    telegram_bot_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")

    smtp_uri: Optional[str] = os.getenv("SMTP_URI")  # smtp://user:pass@smtp.gmail.com:587
    email_from: str = os.getenv("EMAIL_FROM", "alerts@spreadpilot.com")
    email_to: str = os.getenv("EMAIL_TO", "admin@spreadpilot.com")

    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME", "spreadpilot")

    vault_enabled: bool = os.getenv("VAULT_ENABLED", "true").lower() == "true"
    vault_mount_point: str = os.getenv("VAULT_MOUNT_POINT", "secret")


class AlertRouter:
    """Routes alerts from Redis to various channels."""

    def __init__(self):
        self.config = AlertRouterConfig()
        self.redis_client: Optional[redis.Redis] = None
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.mongo_db: Optional[AsyncIOMotorDatabase] = None
        self.httpx_client: Optional[httpx.AsyncClient] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the alert router."""
        logger.info("Starting alert router")

        # Initialize connections
        await self._init_redis()
        await self._init_mongo()
        await self._init_httpx()
        await self._load_vault_secrets()

        # Create consumer group if it doesn't exist
        try:
            await self.redis_client.xgroup_create(
                "alerts", self.config.redis_consumer_group, id="0"
            )
            logger.info(f"Created consumer group: {self.config.redis_consumer_group}")
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info("Consumer group already exists")
            else:
                raise

        # Start processing task
        self._running = True
        self._task = asyncio.create_task(self._process_alerts())
        logger.info("Alert router started")

    async def stop(self):
        """Stop the alert router."""
        logger.info("Stopping alert router")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Close connections
        if self.redis_client:
            await self.redis_client.close()
        if self.mongo_client:
            self.mongo_client.close()
        if self.httpx_client:
            await self.httpx_client.aclose()

        logger.info("Alert router stopped")

    async def _init_redis(self):
        """Initialize Redis connection."""
        self.redis_client = redis.from_url(self.config.redis_url, decode_responses=True)
        await self.redis_client.ping()
        logger.info("Connected to Redis")

    async def _init_mongo(self):
        """Initialize MongoDB connection."""
        self.mongo_client = AsyncIOMotorClient(self.config.mongo_uri)
        self.mongo_db = self.mongo_client[self.config.mongo_db_name]
        # Test connection
        await self.mongo_db.command("ping")
        logger.info("Connected to MongoDB")

    async def _init_httpx(self):
        """Initialize HTTP client."""
        self.httpx_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0), limits=httpx.Limits(max_connections=10)
        )

    async def _load_vault_secrets(self):
        """Load secrets from Vault if enabled."""
        if not self.config.vault_enabled:
            logger.info("Vault disabled, using environment variables")
            return

        try:
            vault_client = get_vault_client()

            # Load Telegram credentials
            if not self.config.telegram_bot_token:
                telegram_secret = vault_client.get_secret("telegram/bot")
                if telegram_secret:
                    self.config.telegram_bot_token = telegram_secret.get("token")
                    self.config.telegram_chat_id = telegram_secret.get("chat_id")
                    logger.info("Loaded Telegram credentials from Vault")

            # Load SMTP credentials
            if not self.config.smtp_uri:
                smtp_secret = vault_client.get_secret("smtp/credentials")
                if smtp_secret:
                    self.config.smtp_uri = smtp_secret.get("uri")
                    self.config.email_from = smtp_secret.get("from", self.config.email_from)
                    self.config.email_to = smtp_secret.get("to", self.config.email_to)
                    logger.info("Loaded SMTP credentials from Vault")

        except Exception as e:
            logger.error(f"Failed to load Vault secrets: {e}")

    async def _process_alerts(self):
        """Main processing loop for alerts."""
        logger.info("Starting alert processing loop")

        while self._running:
            try:
                # Read from Redis stream
                messages = await self.redis_client.xreadgroup(
                    self.config.redis_consumer_group,
                    self.config.redis_consumer_name,
                    {"alerts": ">"},
                    count=10,
                    block=1000,  # Block for 1 second
                )

                for stream_name, stream_messages in messages:
                    for msg_id, data in stream_messages:
                        try:
                            await self._process_single_alert(msg_id, data)
                            # Acknowledge message
                            await self.redis_client.xack(
                                "alerts", self.config.redis_consumer_group, msg_id
                            )
                        except Exception as e:
                            logger.error(f"Error processing alert {msg_id}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert processing loop: {e}")
                await asyncio.sleep(5)  # Wait before retry

    async def _process_single_alert(self, msg_id: str, data: Dict[str, Any]):
        """Process a single alert message."""
        try:
            # Parse alert event data
            alert_json = data.get("data", "{}")
            alert_event = AlertEvent.model_validate_json(alert_json)

            logger.info(
                f"Processing alert event: {alert_event.message} "
                f"of type {alert_event.event_type}"
            )

            # Route to appropriate channels with retry
            success = True
            telegram_sent = False
            email_sent = False

            # Send to Telegram
            if self.config.telegram_bot_token and self.config.telegram_chat_id:
                try:
                    await self._send_telegram_with_retry(alert_event)
                    telegram_sent = True
                except Exception as e:
                    logger.error(f"Failed to send Telegram after retries: {e}")
                    success = False

            # Send email
            if self.config.smtp_uri:
                try:
                    await self._send_email_with_retry(alert_event)
                    email_sent = True
                except Exception as e:
                    logger.error(f"Failed to send email after retries: {e}")
                    success = False

            # Log to MongoDB
            await self._log_alert_to_mongo(
                alert_event, msg_id, success=success, telegram_sent=telegram_sent, email_sent=email_sent
            )

        except Exception as e:
            logger.error(f"Failed to process alert message: {e}")
            raise

    @backoff.on_exception(backoff.expo, Exception, max_tries=3, max_time=30)
    async def _send_telegram_with_retry(self, alert_event: AlertEvent):
        """Send alert to Telegram with exponential backoff retry."""
        # Map event types to severity for emoji
        type_to_severity = {
            AlertType.COMPONENT_DOWN: AlertSeverity.CRITICAL,
            AlertType.NO_MARGIN: AlertSeverity.CRITICAL,
            AlertType.MID_TOO_LOW: AlertSeverity.WARNING,
            AlertType.LIMIT_REACHED: AlertSeverity.WARNING,
            AlertType.ASSIGNMENT_DETECTED: AlertSeverity.INFO,
            AlertType.ASSIGNMENT_COMPENSATED: AlertSeverity.INFO,
            AlertType.REPORT_FAILED: AlertSeverity.WARNING,
            AlertType.PARTIAL_FILL_HIGH: AlertSeverity.WARNING,
            AlertType.GATEWAY_UNREACHABLE: AlertSeverity.CRITICAL,
            AlertType.WATCHDOG_FAILURE: AlertSeverity.CRITICAL,
        }
        
        severity_emoji = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
        }

        severity = type_to_severity.get(alert_event.event_type, AlertSeverity.INFO)
        emoji = severity_emoji.get(severity, "📢")
        
        # Format params for display
        params_text = ""
        if alert_event.params:
            params_text = "\n".join([f"*{k}:* {v}" for k, v in alert_event.params.items()])
            params_text = f"\n{params_text}"

        message = (
            f"{emoji} *SpreadPilot Alert*\n\n"
            f"*Type:* {alert_event.event_type.value}\n"
            f"*Message:* {alert_event.message}{params_text}\n"
            f"*Time:* {alert_event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        # Send to Telegram
        url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"

        response = await self.httpx_client.post(
            url,
            json={
                "chat_id": self.config.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
            },
        )

        response.raise_for_status()
        logger.info(f"Sent Telegram alert: {alert_event.event_type}")

    @backoff.on_exception(backoff.expo, Exception, max_tries=3, max_time=30)
    async def _send_email_with_retry(self, alert_event: AlertEvent):
        """Send alert via email with exponential backoff retry."""
        # Parse SMTP URI
        # Format: smtp://user:pass@host:port
        import urllib.parse

        parsed = urllib.parse.urlparse(self.config.smtp_uri)

        smtp_host = parsed.hostname
        smtp_port = parsed.port or 587
        smtp_user = parsed.username
        smtp_pass = parsed.password

        # Create email
        msg = MIMEMultipart()
        msg["From"] = self.config.email_from
        msg["To"] = self.config.email_to
        msg["Subject"] = f"SpreadPilot Alert: {alert_event.event_type.value} - {alert_event.message[:50]}"

        # Format params for display
        params_text = ""
        if alert_event.params:
            params_lines = [f"{k}: {v}" for k, v in alert_event.params.items()]
            params_text = "\n" + "\n".join(params_lines)

        # Email body
        body = f"""
SpreadPilot Alert Notification

Alert Type: {alert_event.event_type.value}
Message: {alert_event.message}{params_text}
Time: {alert_event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

This is an automated alert from the SpreadPilot trading system.
        """

        msg.attach(MIMEText(body, "plain"))

        # Send email
        async with aiosmtplib.SMTP(hostname=smtp_host, port=smtp_port, start_tls=True) as smtp:
            if smtp_user and smtp_pass:
                await smtp.login(smtp_user, smtp_pass)
            await smtp.send_message(msg)

        logger.info(f"Sent email alert: {alert_event.event_type}")

    async def _log_alert_to_mongo(
        self, alert_event: AlertEvent, msg_id: str, success: bool, telegram_sent: bool, email_sent: bool
    ):
        """Log alert processing to MongoDB."""
        try:
            alerts_collection = self.mongo_db["alert_history"]

            await alerts_collection.insert_one(
                {
                    "msg_id": msg_id,
                    "alert_event": alert_event.model_dump(),
                    "processed_at": time.time(),
                    "success": success,
                    "channels": {"telegram": telegram_sent, "email": email_sent},
                    "status": "completed" if success else "failed",
                }
            )

            logger.debug(f"Logged alert {msg_id} to MongoDB")

        except Exception as e:
            logger.error(f"Failed to log alert to MongoDB: {e}")




# Global router instance
router = AlertRouter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the app."""
    # Startup
    await router.start()
    yield
    # Shutdown
    await router.stop()


app = FastAPI(title="Alert Router", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "alert-router", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8006)

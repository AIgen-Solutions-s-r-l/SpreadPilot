"""
SpreadPilot Watchdog Service - Self-hosted health monitoring with auto-recovery
"""

import asyncio
import logging
import os
import subprocess
import sys
from datetime import datetime

import httpx
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient

from spreadpilot_core.models.alert import Alert, AlertEvent, AlertSeverity, AlertType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Service configuration
SERVICES = {
    "trading_bot": {
        "container_name": "spreadpilot-trading-bot",
        "health_url": "http://trading-bot:8080/health",
        "display_name": "Trading Bot",
    },
    "admin_api": {
        "container_name": "spreadpilot-admin-api",
        "health_url": "http://admin-api:8080/health",
        "display_name": "Admin API",
    },
    "report_worker": {
        "container_name": "spreadpilot-report-worker",
        "health_url": "http://report-worker:8080/health",
        "display_name": "Report Worker",
    },
    "frontend": {
        "container_name": "spreadpilot-frontend",
        "health_url": "http://frontend:3000/api/health",
        "display_name": "Frontend Dashboard",
    },
}

# Configuration
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "15"))
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "5"))
MAX_CONSECUTIVE_FAILURES = int(os.getenv("MAX_CONSECUTIVE_FAILURES", "3"))

# MongoDB configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "spreadpilot_admin")

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_ALERT_STREAM = os.getenv("REDIS_ALERT_STREAM", "alerts")


class ServiceWatchdog:
    """Monitors service health and performs auto-recovery"""

    def __init__(self):
        self.failure_counts: dict[str, int] = dict.fromkeys(SERVICES, 0)
        self.http_client: httpx.AsyncClient | None = None
        self.mongo_client: AsyncIOMotorClient | None = None
        self.mongo_db = None
        self.redis_client: redis.Redis | None = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.http_client = httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT)
        self.mongo_client = AsyncIOMotorClient(MONGO_URI)
        self.mongo_db = self.mongo_client[MONGO_DB_NAME]
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.http_client:
            await self.http_client.aclose()
        if self.mongo_client:
            self.mongo_client.close()
        if self.redis_client:
            await self.redis_client.close()

    async def check_service_health(self, service_name: str) -> bool:
        """
        Check the health of a service by calling its health endpoint.

        Args:
            service_name: Name of the service to check

        Returns:
            True if service is healthy, False otherwise
        """
        service_config = SERVICES[service_name]
        health_url = service_config["health_url"]

        try:
            logger.debug(f"Checking health of {service_name} at {health_url}")
            response = await self.http_client.get(health_url)

            if response.status_code == 200:
                logger.debug(f"{service_name} is healthy")
                # Also check response body if available
                try:
                    health_data = response.json()
                    if isinstance(health_data, dict) and health_data.get("status") == "unhealthy":
                        logger.warning(f"{service_name} reports unhealthy status in response body")
                        return False
                except Exception:
                    # If can't parse JSON, just use status code
                    pass
                return True
            else:
                logger.warning(f"{service_name} returned unhealthy status: {response.status_code}")
                return False

        except httpx.ConnectError:
            logger.error(f"{service_name} connection refused at {health_url}")
            return False
        except httpx.TimeoutException:
            logger.error(f"{service_name} health check timed out after {HEALTH_CHECK_TIMEOUT}s")
            return False
        except httpx.RequestError as e:
            logger.error(f"Failed to reach {service_name}: {type(e).__name__}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking {service_name}: {e}")
            return False

    def restart_service(self, service_name: str) -> bool:
        """
        Restart a Docker container using subprocess.

        Args:
            service_name: Name of the service to restart

        Returns:
            True if restart was successful, False otherwise
        """
        container_name = SERVICES[service_name]["container_name"]

        try:
            logger.info(f"Attempting to restart {container_name}")
            result = subprocess.run(
                ["docker", "restart", container_name],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info(f"Successfully restarted {container_name}")
                return True
            else:
                logger.error(f"Failed to restart {container_name}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout while restarting {container_name}")
            return False
        except Exception as e:
            logger.error(f"Error restarting {container_name}: {e}")
            return False

    async def publish_alert(self, service_name: str, action: str, success: bool):
        """
        Publish an alert about service status via Redis Streams.

        Args:
            service_name: Name of the service
            action: Action taken (e.g., "restart")
            success: Whether the action was successful
        """
        service_config = SERVICES[service_name]

        # Determine severity based on action and success
        if action == "recovery":
            severity = AlertSeverity.INFO
            reason = f"RECOVERED: {service_config['display_name']} is now healthy"
        elif action == "restart" and success:
            severity = AlertSeverity.WARNING
            reason = (
                f"RESTARTED: {service_config['display_name']} was "
                "successfully restarted after failures"
            )
        elif action == "restart" and not success:
            severity = AlertSeverity.CRITICAL
            reason = f"RESTART_FAILED: Failed to restart {service_config['display_name']}"
        else:
            severity = AlertSeverity.ERROR
            reason = f"DOWN: {service_config['display_name']} is not responding"

        # Create alert compatible with alert router
        alert = Alert(
            service="watchdog",
            follower_id="system",  # System-level alert
            reason=reason,
            severity=severity,
            timestamp=datetime.utcnow(),
            details={
                "component_name": service_name,
                "container_name": service_config["container_name"],
                "action": action,
                "success": success,
                "consecutive_failures": self.failure_counts[service_name],
                "health_url": service_config["health_url"],
            },
        )

        # Publish to Redis Stream for alert router
        try:
            if self.redis_client:
                alert_json = alert.model_dump_json()
                await self.redis_client.xadd(REDIS_ALERT_STREAM, {"data": alert_json})
                logger.info(f"Alert published to Redis: {alert.reason}")
            else:
                logger.warning("Redis not connected, alert not published")
        except Exception as e:
            logger.error(f"Failed to publish alert to Redis: {e}")

        # Also store in MongoDB for persistence
        try:
            if self.mongo_db:
                # Store as AlertEvent for MongoDB compatibility
                event_type = (
                    AlertType.COMPONENT_RECOVERED
                    if action == "recovery"
                    else AlertType.COMPONENT_DOWN
                )
                alert_event = AlertEvent(
                    event_type=event_type,
                    timestamp=alert.timestamp,
                    message=alert.reason,
                    params=alert.details,
                )
                await self.mongo_db.alerts.insert_one(alert_event.dict())
                logger.info(f"Alert stored in MongoDB for persistence")
        except Exception as e:
            logger.error(f"Failed to store alert in MongoDB: {e}")

    async def monitor_service(self, service_name: str):
        """
        Monitor a single service and take action if unhealthy.

        Args:
            service_name: Name of the service to monitor
        """
        is_healthy = await self.check_service_health(service_name)

        if is_healthy:
            # Reset failure count on successful health check
            if self.failure_counts[service_name] > 0:
                logger.info(
                    f"{service_name} recovered after {self.failure_counts[service_name]} failures"
                )
                await self.publish_alert(service_name, "recovery", True)
            self.failure_counts[service_name] = 0
        else:
            # Increment failure count
            self.failure_counts[service_name] += 1
            logger.warning(
                f"{service_name} failed health check "
                f"({self.failure_counts[service_name]}/{MAX_CONSECUTIVE_FAILURES})"
            )

            # Take action after max consecutive failures
            if self.failure_counts[service_name] >= MAX_CONSECUTIVE_FAILURES:
                logger.error(
                    f"{service_name} exceeded max consecutive failures. " "Attempting restart..."
                )

                # Restart the service
                restart_success = self.restart_service(service_name)

                # Publish alert about the restart attempt
                await self.publish_alert(service_name, "restart", restart_success)

                # Reset failure count after successful restart
                if restart_success:
                    self.failure_counts[service_name] = 0
                    # Wait a bit for service to come up before next check
                    await asyncio.sleep(10)

    async def run(self):
        """Main monitoring loop"""
        logger.info("Watchdog service starting...")
        logger.info(f"Monitoring services: {', '.join(SERVICES.keys())}")
        logger.info(f"Check interval: {CHECK_INTERVAL_SECONDS} seconds")
        logger.info(f"Max consecutive failures before restart: {MAX_CONSECUTIVE_FAILURES}")

        while True:
            try:
                # Check all services concurrently
                tasks = [self.monitor_service(service_name) for service_name in SERVICES]
                await asyncio.gather(*tasks)

                # Wait before next check cycle
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)

            except asyncio.CancelledError:
                logger.info("Watchdog service cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                # Continue monitoring even if there's an error
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)


async def main():
    """Main entry point"""
    try:
        async with ServiceWatchdog() as watchdog:
            await watchdog.run()
    except KeyboardInterrupt:
        logger.info("Watchdog service stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

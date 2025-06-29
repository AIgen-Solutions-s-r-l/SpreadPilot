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
from motor.motor_asyncio import AsyncIOMotorClient

from spreadpilot_core.models.alert import AlertEvent, AlertType

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


class ServiceWatchdog:
    """Monitors service health and performs auto-recovery"""

    def __init__(self):
        self.failure_counts: dict[str, int] = dict.fromkeys(SERVICES, 0)
        self.http_client: httpx.AsyncClient | None = None
        self.mongo_client: AsyncIOMotorClient | None = None
        self.mongo_db = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.http_client = httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT)
        self.mongo_client = AsyncIOMotorClient(MONGO_URI)
        self.mongo_db = self.mongo_client[MONGO_DB_NAME]
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.http_client:
            await self.http_client.aclose()
        if self.mongo_client:
            self.mongo_client.close()

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
                return True
            else:
                logger.warning(
                    f"{service_name} returned unhealthy status: {response.status_code}"
                )
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
        Publish an alert about service status.

        Args:
            service_name: Name of the service
            action: Action taken (e.g., "restart")
            success: Whether the action was successful
        """
        service_config = SERVICES[service_name]

        # Determine alert type based on action and success
        if action == "recovery":
            event_type = AlertType.COMPONENT_RECOVERED
        elif not success:
            event_type = AlertType.COMPONENT_DOWN
        else:
            event_type = AlertType.COMPONENT_RECOVERED

        alert = AlertEvent(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            message=f"{service_config['display_name']} {action} {'succeeded' if success else 'failed'}",
            params={
                "component_name": service_name,
                "container_name": service_config["container_name"],
                "action": action,
                "success": success,
                "consecutive_failures": self.failure_counts[service_name],
            },
        )

        # Store alert in MongoDB
        try:
            if self.mongo_db:
                alert_dict = alert.dict()
                await self.mongo_db.alerts.insert_one(alert_dict)
                logger.info(f"Alert stored in MongoDB: {alert.message}")
            else:
                logger.warning("MongoDB not connected, alert not stored")
        except Exception as e:
            logger.error(f"Failed to store alert in MongoDB: {e}")

        # Log the alert
        logger.info(f"Alert published: {alert.message}")

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
                    f"{service_name} exceeded max consecutive failures. "
                    "Attempting restart..."
                )

                # Restart the service
                restart_success = self.restart_service(service_name)

                # Publish alert about the restart attempt
                await self.publish_alert(service_name, "restart", restart_success)

                # Reset failure count after restart attempt
                if restart_success:
                    self.failure_counts[service_name] = 0

    async def run(self):
        """Main monitoring loop"""
        logger.info("Watchdog service starting...")
        logger.info(f"Monitoring services: {', '.join(SERVICES.keys())}")
        logger.info(f"Check interval: {CHECK_INTERVAL_SECONDS} seconds")
        logger.info(
            f"Max consecutive failures before restart: {MAX_CONSECUTIVE_FAILURES}"
        )

        while True:
            try:
                # Check all services concurrently
                tasks = [
                    self.monitor_service(service_name) for service_name in SERVICES
                ]
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

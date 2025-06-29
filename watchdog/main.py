"""
SpreadPilot Watchdog Service - Container health monitoring with auto-recovery
"""

import asyncio
import json
import logging
import os

import docker
import httpx
import redis.asyncio as redis

from spreadpilot_core.models.alert import AlertEvent, AlertSeverity, AlertType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Configuration
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "30"))
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "10"))
MAX_CONSECUTIVE_FAILURES = int(os.getenv("MAX_CONSECUTIVE_FAILURES", "3"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


class ContainerWatchdog:
    """Monitors containers labeled 'spreadpilot' and performs auto-recovery"""

    def __init__(self):
        self.docker_client = docker.from_env()
        self.failure_counts: dict[str, int] = {}
        self.http_client: httpx.AsyncClient | None = None
        self.redis_client: redis.Redis | None = None
        self.monitored_containers: set[str] = set()

    async def __aenter__(self):
        """Async context manager entry"""
        self.http_client = httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT)
        self.redis_client = await redis.from_url(REDIS_URL, decode_responses=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.http_client:
            await self.http_client.aclose()
        if self.redis_client:
            await self.redis_client.close()

    def get_spreadpilot_containers(self) -> list[docker.models.containers.Container]:
        """Get all running containers with 'spreadpilot' label"""
        try:
            containers = self.docker_client.containers.list(
                filters={"label": "spreadpilot", "status": "running"}
            )
            return containers
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return []

    async def check_container_health(self, container) -> bool:
        """
        Check the health of a container by calling its /health endpoint.

        Args:
            container: Docker container object

        Returns:
            True if container is healthy, False otherwise
        """
        container_name = container.name

        # Get container's exposed port (assume health check on first exposed port)
        try:
            # Get container details
            container.reload()
            ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})

            # Find the first exposed port
            health_port = None
            for port_key, port_info in ports.items():
                if port_info and "/" in port_key:
                    port_num = port_key.split("/")[0]
                    health_port = port_num
                    break

            if not health_port:
                logger.warning(f"{container_name} has no exposed ports")
                return True  # Assume healthy if no ports exposed

            # Use container name as hostname within Docker network
            health_url = f"http://{container_name}:{health_port}/health"

            logger.debug(f"Checking health of {container_name} at {health_url}")
            response = await self.http_client.get(health_url)

            if response.status_code == 200:
                logger.debug(f"{container_name} is healthy")
                return True
            else:
                logger.warning(
                    f"{container_name} returned unhealthy status: {response.status_code}"
                )
                return False

        except httpx.RequestError as e:
            logger.error(f"Failed to reach {container_name}: {type(e).__name__}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking {container_name}: {e}")
            return False

    def restart_container(self, container) -> bool:
        """
        Restart a Docker container.

        Args:
            container: Docker container object

        Returns:
            True if restart was successful, False otherwise
        """
        container_name = container.name

        try:
            logger.info(f"Attempting to restart {container_name}")
            container.restart(timeout=30)
            logger.info(f"Successfully restarted {container_name}")
            return True

        except Exception as e:
            logger.error(f"Error restarting {container_name}: {e}")
            return False

    async def publish_critical_alert(
        self, container_name: str, action: str, success: bool
    ):
        """
        Publish a critical alert to Redis stream.

        Args:
            container_name: Name of the container
            action: Action taken (e.g., "restart")
            success: Whether the action was successful
        """
        alert_event = AlertEvent(
            event_type=(
                AlertType.COMPONENT_DOWN
                if not success
                else AlertType.COMPONENT_RECOVERED
            ),
            message=f"Container {container_name} {action} {'succeeded' if success else 'failed'}",
            params={
                "container_name": container_name,
                "action": action,
                "success": success,
                "consecutive_failures": self.failure_counts.get(container_name, 0),
                "severity": (
                    AlertSeverity.CRITICAL.value
                    if not success
                    else AlertSeverity.INFO.value
                ),
            },
        )

        try:
            if self.redis_client:
                alert_json = json.dumps(alert_event.model_dump(mode="json"))
                await self.redis_client.xadd("alerts", {"alert": alert_json})
                logger.info(f"Published critical alert: {alert_event.message}")
            else:
                logger.warning("Redis not connected, alert not published")
        except Exception as e:
            logger.error(f"Failed to publish alert to Redis: {e}")

    async def monitor_container(self, container):
        """
        Monitor a single container and take action if unhealthy.

        Args:
            container: Docker container object
        """
        container_name = container.name

        # Initialize failure count if not exists
        if container_name not in self.failure_counts:
            self.failure_counts[container_name] = 0

        is_healthy = await self.check_container_health(container)

        if is_healthy:
            # Reset failure count on successful health check
            if self.failure_counts[container_name] > 0:
                logger.info(
                    f"{container_name} recovered after {self.failure_counts[container_name]} failures"
                )
                await self.publish_critical_alert(container_name, "recovery", True)
            self.failure_counts[container_name] = 0
        else:
            # Increment failure count
            self.failure_counts[container_name] += 1
            logger.warning(
                f"{container_name} failed health check "
                f"({self.failure_counts[container_name]}/{MAX_CONSECUTIVE_FAILURES})"
            )

            # Take action after max consecutive failures
            if self.failure_counts[container_name] >= MAX_CONSECUTIVE_FAILURES:
                logger.error(
                    f"{container_name} exceeded max consecutive failures. "
                    "Attempting restart..."
                )

                # Restart the container
                restart_success = self.restart_container(container)

                # Publish critical alert about the restart attempt
                await self.publish_critical_alert(
                    container_name, "restart", restart_success
                )

                # Reset failure count after restart attempt
                if restart_success:
                    self.failure_counts[container_name] = 0

    async def cleanup_stale_containers(self):
        """Remove failure counts for containers that no longer exist"""
        current_containers = {c.name for c in self.get_spreadpilot_containers()}
        stale_containers = set(self.failure_counts.keys()) - current_containers

        for container_name in stale_containers:
            logger.info(f"Removing stale container from monitoring: {container_name}")
            del self.failure_counts[container_name]

    async def run(self):
        """Main monitoring loop"""
        logger.info("Container watchdog service starting...")
        logger.info(f"Check interval: {CHECK_INTERVAL_SECONDS} seconds")
        logger.info(
            f"Max consecutive failures before restart: {MAX_CONSECUTIVE_FAILURES}"
        )
        logger.info("Monitoring all containers labeled 'spreadpilot'")

        while True:
            try:
                # Get current list of spreadpilot containers
                containers = self.get_spreadpilot_containers()

                # Log newly discovered containers
                current_names = {c.name for c in containers}
                new_containers = current_names - self.monitored_containers
                if new_containers:
                    logger.info(
                        f"Discovered new containers: {', '.join(new_containers)}"
                    )
                self.monitored_containers = current_names

                if not containers:
                    logger.warning("No containers with 'spreadpilot' label found")
                else:
                    # Check all containers concurrently
                    tasks = [
                        self.monitor_container(container) for container in containers
                    ]
                    await asyncio.gather(*tasks)

                # Cleanup stale containers from failure counts
                await self.cleanup_stale_containers()

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
        async with ContainerWatchdog() as watchdog:
            await watchdog.run()
    except KeyboardInterrupt:
        logger.info("Watchdog service stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

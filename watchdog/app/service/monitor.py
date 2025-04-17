# watchdog/app/service/monitor.py
import asyncio
import time
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, Optional

import httpx
from google.cloud import firestore_async  # type: ignore

from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.alert import Alert, AlertLevel, AlertSource
from spreadpilot_core.utils.alerting import AlertManager  # Assuming AlertManager exists

from ..config import settings

logger = get_logger(__name__)


class ComponentStatus(Enum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    RESTARTING = "RESTARTING"
    DOWN = "DOWN"


class MonitoredComponent:
    """Represents a component being monitored."""

    def __init__(
        self,
        name: str,
        health_endpoint: Optional[str],
        max_restarts: int = settings.MAX_RESTART_ATTEMPTS,
        restart_backoff: int = settings.RESTART_BACKOFF_SECONDS,
        heartbeat_timeout: int = settings.HEARTBEAT_TIMEOUT_SECONDS,
    ):
        self.name = name
        self.health_endpoint = health_endpoint
        self.max_restarts = max_restarts
        self.restart_backoff = restart_backoff
        self.heartbeat_timeout = timedelta(seconds=heartbeat_timeout)

        self.status: ComponentStatus = ComponentStatus.UNKNOWN
        self.last_heartbeat: Optional[datetime] = None
        self.restart_attempts: int = 0
        self.last_restart_attempt_time: Optional[datetime] = None
        self.is_restarting: bool = False

    async def check_health(self, client: httpx.AsyncClient) -> bool:
        """Checks the health endpoint of the component."""
        if not self.health_endpoint:
            logger.warning(f"No health endpoint configured for {self.name}, skipping check.")
            # Assume healthy if no endpoint? Or UNKNOWN? Let's assume UNKNOWN requires manual check
            # For now, treat as healthy if no endpoint defined, maybe needs refinement
            self.last_heartbeat = datetime.now(timezone.utc)
            return True

        try:
            response = await client.get(self.health_endpoint, timeout=10.0)
            response.raise_for_status()
            # TODO: Potentially check response content for more detailed status
            logger.debug(f"Health check successful for {self.name}")
            self.last_heartbeat = datetime.now(timezone.utc)
            self.restart_attempts = 0  # Reset attempts on successful heartbeat
            self.is_restarting = False # No longer restarting if healthy
            return True
        except httpx.RequestError as e:
            logger.warning(f"Health check failed for {self.name}: Request error {e}")
            return False
        except httpx.HTTPStatusError as e:
            logger.warning(f"Health check failed for {self.name}: Status {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during health check for {self.name}: {e}", exc_info=True)
            return False

    def is_heartbeat_timed_out(self) -> bool:
        """Checks if the last heartbeat is older than the timeout."""
        if self.last_heartbeat is None:
            # Never seen a heartbeat, consider it timed out after initial grace period?
            # For now, assume it needs a first successful check.
            return True # Treat as timed out if never received
        return datetime.now(timezone.utc) - self.last_heartbeat > self.heartbeat_timeout

    async def attempt_restart(self) -> bool:
        """Attempts to restart the component."""
        if self.restart_attempts >= self.max_restarts:
            logger.error(f"Max restart attempts reached for {self.name}. Marking as DOWN.")
            return False # Cannot restart anymore

        # Check backoff period
        now = datetime.now(timezone.utc)
        if self.last_restart_attempt_time and (now - self.last_restart_attempt_time) < timedelta(seconds=self.restart_backoff):
            logger.info(f"Restart backoff period active for {self.name}. Skipping restart attempt.")
            return True # Still in restarting phase, but waiting

        logger.warning(f"Attempting restart {self.restart_attempts + 1}/{self.max_restarts} for {self.name}...")
        self.is_restarting = True
        self.last_restart_attempt_time = now
        self.restart_attempts += 1

        # --- Restart Logic Placeholder ---
        # This needs to be implemented based on how components are deployed
        # Examples:
        # - Call Cloud Run API to redeploy/restart service instance
        # - Use kubectl to delete/recreate pod
        # - Send a specific command via an API
        logger.info(f"Placeholder: Restart logic for {self.name} would execute here.")
        await asyncio.sleep(2) # Simulate restart delay
        # --- End Placeholder ---

        # Assume restart command was issued, actual success confirmed by next health check
        return True


class MonitorService:
    """Service to monitor components, update status, and trigger restarts/alerts."""

    def __init__(self):
        self.db = firestore_async.AsyncClient(project=settings.PROJECT_ID)
        self.status_collection_ref = self.db.collection(settings.FIRESTORE_STATUS_COLLECTION)
        self.http_client = httpx.AsyncClient()
        self.alert_manager = AlertManager(service_name=settings.ALERT_SERVICE_NAME) # Assuming AlertManager setup

        self.components: Dict[str, MonitoredComponent] = {
            settings.TRADING_BOT_NAME: MonitoredComponent(
                name=settings.TRADING_BOT_NAME,
                health_endpoint=settings.TRADING_BOT_HEALTH_ENDPOINT,
            ),
            settings.IB_GATEWAY_NAME: MonitoredComponent(
                name=settings.IB_GATEWAY_NAME,
                health_endpoint=settings.IB_GATEWAY_HEALTH_ENDPOINT,
                # Maybe IB Gateway needs different restart logic/attempts? Configurable per component.
            ),
        }
        self._stop_event = asyncio.Event()

    async def update_firestore_status(self, component: MonitoredComponent):
        """Updates the component status in Firestore."""
        doc_ref = self.status_collection_ref.document(component.name)
        status_data = {
            "service_name": component.name,
            "status": component.status.value,
            "last_heartbeat": component.last_heartbeat,
            "last_updated": firestore_async.SERVER_TIMESTAMP,
            "restart_attempts": component.restart_attempts,
            "environment": settings.ENVIRONMENT,
        }
        try:
            await doc_ref.set(status_data, merge=True)
            logger.debug(f"Updated Firestore status for {component.name} to {component.status.value}")
        except Exception as e:
            logger.error(f"Failed to update Firestore status for {component.name}: {e}", exc_info=True)

    async def send_critical_alert(self, component: MonitoredComponent):
        """Sends a critical alert for an irrecoverable component."""
        alert = Alert(
            level=AlertLevel.CRITICAL,
            source=AlertSource.WATCHDOG,
            service=settings.ALERT_SERVICE_NAME,
            component=component.name,
            message=f"Component '{component.name}' is DOWN after {component.max_restarts} failed restart attempts.",
            details={"last_heartbeat": str(component.last_heartbeat) if component.last_heartbeat else "Never"},
            timestamp=datetime.now(timezone.utc),
        )
        try:
            await self.alert_manager.send_alert(alert)
            logger.critical(f"Sent CRITICAL alert for component {component.name}")
        except Exception as e:
            logger.error(f"Failed to send critical alert for {component.name}: {e}", exc_info=True)

    async def run_check_cycle(self):
        """Performs a single monitoring cycle for all components."""
        logger.info("Starting monitoring cycle...")
        check_tasks = [self.check_component(name) for name in self.components.keys()]
        await asyncio.gather(*check_tasks)
        logger.info("Monitoring cycle finished.")

    async def check_component(self, component_name: str):
        """Checks a single component's health and takes action."""
        component = self.components[component_name]
        previous_status = component.status

        is_healthy = await component.check_health(self.http_client)

        if is_healthy:
            component.status = ComponentStatus.HEALTHY
        else:
            if component.is_heartbeat_timed_out():
                logger.warning(f"Heartbeat timeout detected for {component.name}. Last seen: {component.last_heartbeat}")
                if component.is_restarting or await component.attempt_restart():
                    component.status = ComponentStatus.RESTARTING
                else:
                    # Max restarts reached
                    component.status = ComponentStatus.DOWN
                    if previous_status != ComponentStatus.DOWN: # Avoid alert spam
                         await self.send_critical_alert(component)
            else:
                # Health check failed, but heartbeat not yet timed out
                component.status = ComponentStatus.UNHEALTHY
                logger.warning(f"{component.name} is UNHEALTHY but within heartbeat timeout.")


        # Update Firestore only if status changed
        if component.status != previous_status:
            await self.update_firestore_status(component)
        else:
            # Optionally update timestamp even if status is same
            # await self.update_firestore_status(component) # Uncomment if last_updated always needed
            pass


    async def start(self):
        """Starts the monitoring loop."""
        logger.info(f"Starting Watchdog Monitor Service in {settings.ENVIRONMENT} environment.")
        logger.info(f"Monitoring: {list(self.components.keys())}")
        logger.info(f"Check Interval: {settings.CHECK_INTERVAL_SECONDS}s, Timeout: {settings.HEARTBEAT_TIMEOUT_SECONDS}s")

        # Initial status update
        init_tasks = [self.update_firestore_status(comp) for comp in self.components.values()]
        await asyncio.gather(*init_tasks)


        while not self._stop_event.is_set():
            start_time = time.monotonic()
            try:
                await self.run_check_cycle()
            except Exception as e:
                logger.error(f"Unhandled exception in monitoring cycle: {e}", exc_info=True)

            # Wait for the next cycle, accounting for execution time
            elapsed_time = time.monotonic() - start_time
            wait_time = max(0, settings.CHECK_INTERVAL_SECONDS - elapsed_time)
            logger.debug(f"Waiting {wait_time:.2f} seconds for next cycle.")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=wait_time)
            except asyncio.TimeoutError:
                continue # Timeout is expected, continue loop

        logger.info("Monitor service stopping.")
        await self.http_client.aclose()
        logger.info("HTTP client closed.")


    async def stop(self):
        """Signals the monitoring loop to stop."""
        logger.info("Received stop signal.")
        self._stop_event.set()
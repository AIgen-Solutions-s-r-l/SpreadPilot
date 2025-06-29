"""IBGateway Docker Container Manager for SpreadPilot."""

import asyncio
import random
import time
from dataclasses import dataclass
from enum import Enum

import backoff
import docker
from ib_insync import IB

from ..logging import get_logger
from ..models.follower import Follower, FollowerState
from ..utils.vault import get_vault_client


# Import MongoDB function lazily to avoid import errors during testing
def get_mongo_db():
    """Get MongoDB connection lazily."""
    from ..db.mongodb import get_mongo_db as _get_mongo_db

    return _get_mongo_db()


logger = get_logger(__name__)


class GatewayStatus(str, Enum):
    """Gateway container status."""

    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


@dataclass
class GatewayInstance:
    """Represents an IBGateway Docker container instance."""

    follower_id: str
    container_id: str
    host_port: int
    client_id: int
    status: GatewayStatus
    container: docker.models.containers.Container | None = None
    ib_client: IB | None = None
    last_healthcheck: float | None = None


class GatewayManager:
    """Manages IBGateway Docker containers for multiple followers."""

    def __init__(
        self,
        gateway_image: str = "ghcr.io/gnzsnz/ib-gateway:latest",
        port_range_start: int = 4100,
        port_range_end: int = 4200,
        client_id_range_start: int = 1000,
        client_id_range_end: int = 9999,
        container_prefix: str = "ibgateway-follower",
        healthcheck_interval: int = 30,
        max_startup_time: int = 120,
        vault_enabled: bool = True,
    ):
        """Initialize the gateway manager.

        Args:
            gateway_image: Docker image for IBGateway
            port_range_start: Start of port range for gateway containers
            port_range_end: End of port range for gateway containers
            client_id_range_start: Start of TWS client ID range
            client_id_range_end: End of TWS client ID range
            container_prefix: Prefix for container names
            healthcheck_interval: Interval between healthchecks in seconds
            max_startup_time: Maximum time to wait for container startup
            vault_enabled: Whether to use Vault for credential retrieval
        """
        self.gateway_image = gateway_image
        self.port_range_start = port_range_start
        self.port_range_end = port_range_end
        self.client_id_range_start = client_id_range_start
        self.client_id_range_end = client_id_range_end
        self.container_prefix = container_prefix
        self.healthcheck_interval = healthcheck_interval
        self.max_startup_time = max_startup_time
        self.vault_enabled = vault_enabled

        self.docker_client = docker.from_env()
        self.gateways: dict[str, GatewayInstance] = {}
        self.used_ports: set = set()
        self.used_client_ids: set = set()

        # Background task handle
        self._monitor_task: asyncio.Task | None = None
        self._shutdown = False

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        max_time=30,
        on_backoff=lambda details: logger.warning(
            f"Retrying Vault fetch (attempt {details['tries']}): {details['exception']}"
        ),
    )
    def _get_ibkr_credentials_from_vault(
        self, secret_ref: str
    ) -> dict[str, str] | None:
        """Get IBKR credentials from Vault with retry logic.

        Args:
            secret_ref: Secret reference/path for IBKR credentials

        Returns:
            Dict with 'IB_USER' and 'IB_PASS' keys or None if not found
        """
        if not self.vault_enabled:
            logger.warning("Vault is disabled, cannot retrieve IBKR credentials")
            return None

        try:
            vault_client = get_vault_client()
            credentials = vault_client.get_ibkr_credentials(secret_ref)

            if credentials:
                logger.info(
                    f"Retrieved IBKR credentials from Vault for secret: {secret_ref}"
                )
                return credentials
            else:
                logger.warning(
                    f"No IBKR credentials found in Vault for secret: {secret_ref}"
                )
                return None

        except Exception as e:
            logger.error(f"Error retrieving IBKR credentials from Vault: {e}")
            raise  # Re-raise to trigger backoff retry

    async def start(self) -> None:
        """Start the gateway manager and load enabled followers."""
        logger.info("Starting IBGateway Manager")

        try:
            await self._load_enabled_followers()

            # Start monitoring task
            self._monitor_task = asyncio.create_task(self._monitor_gateways())

            logger.info(f"Gateway Manager started with {len(self.gateways)} followers")

        except Exception as e:
            logger.error(f"Failed to start Gateway Manager: {e}")
            raise

    async def stop(self) -> None:
        """Stop the gateway manager and all containers with graceful shutdown."""
        logger.info("Starting graceful shutdown of IBGateway Manager")

        self._shutdown = True

        # Cancel monitoring task first to prevent new health checks
        if self._monitor_task:
            logger.debug("Cancelling monitoring task")
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                logger.debug("Monitoring task cancelled")

        # Gracefully stop all gateways in parallel with timeout
        if self.gateways:
            logger.info(f"Stopping {len(self.gateways)} gateway containers")

            # Create tasks for parallel shutdown
            shutdown_tasks = []
            for follower_id in list(self.gateways.keys()):
                task = asyncio.create_task(self._stop_gateway(follower_id))
                shutdown_tasks.append(task)

            # Wait for all shutdowns with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*shutdown_tasks, return_exceptions=True),
                    timeout=45,  # 45 seconds total timeout
                )
                logger.info("All gateways stopped successfully")
            except TimeoutError:
                logger.warning(
                    "Some gateways did not stop within timeout, forcing cleanup"
                )
                # Force cleanup any remaining containers
                for follower_id, gateway in list(self.gateways.items()):
                    if gateway.container:
                        try:
                            gateway.container.remove(force=True)
                            logger.warning(
                                f"Force removed container for follower {follower_id}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to force remove container for {follower_id}: {e}"
                            )

        # Close Docker client
        try:
            self.docker_client.close()
            logger.debug("Docker client closed")
        except Exception as e:
            logger.error(f"Error closing Docker client: {e}")

        logger.info("Gateway Manager stopped")

    async def get_client(self, follower_id: str) -> IB | None:
        """Get a ready IB client instance for the follower.

        Args:
            follower_id: The follower ID

        Returns:
            Ready IB client instance or None if not available
        """
        gateway = self.gateways.get(follower_id)
        if not gateway:
            logger.warning(f"No gateway found for follower {follower_id}")
            return None

        if gateway.status != GatewayStatus.RUNNING:
            logger.warning(
                f"Gateway for follower {follower_id} is not running (status: {gateway.status})"
            )
            return None

        # Return existing connected client if available
        if gateway.ib_client and gateway.ib_client.isConnected():
            return gateway.ib_client

        # Create new client connection
        try:
            return await self._connect_ib_client(gateway)
        except Exception as e:
            logger.error(f"Failed to connect IB client for follower {follower_id}: {e}")
            return None

    async def _load_enabled_followers(self) -> None:
        """Load enabled followers from database and start their gateways."""
        db = get_mongo_db()
        if not db:
            raise RuntimeError("MongoDB connection not available")

        # Query enabled followers
        followers_collection = db["followers"]
        cursor = followers_collection.find(
            {"enabled": True, "state": FollowerState.ACTIVE.value}
        )

        followers = []
        async for doc in cursor:
            try:
                follower = Follower.model_validate(doc)
                followers.append(follower)
            except Exception as e:
                logger.error(f"Failed to parse follower document: {e}")

        logger.info(f"Found {len(followers)} enabled followers")

        # Start gateways for each follower
        for follower in followers:
            try:
                await self._start_gateway(follower)
            except Exception as e:
                logger.error(f"Failed to start gateway for follower {follower.id}: {e}")

    async def _start_gateway(self, follower: Follower) -> GatewayInstance:
        """Start an IBGateway container for a follower.

        Args:
            follower: The follower configuration

        Returns:
            Gateway instance
        """
        logger.info(f"Starting IBGateway for follower {follower.id}")

        # Allocate port and client ID
        host_port = self._allocate_port()
        client_id = self._allocate_client_id()

        container_name = f"{self.container_prefix}-{follower.id}"

        try:
            # Remove existing container if present
            try:
                existing = self.docker_client.containers.get(container_name)
                existing.remove(force=True)
                logger.info(f"Removed existing container {container_name}")
            except docker.errors.NotFound:
                pass

            # Get IBKR credentials from Vault
            if hasattr(follower, "vault_secret_ref") and follower.vault_secret_ref:
                # Try to get credentials from Vault using follower's secret reference
                credentials = self._get_ibkr_credentials_from_vault(
                    follower.vault_secret_ref
                )
                if credentials:
                    ibkr_username = credentials.get("IB_USER", follower.ibkr_username)
                    ibkr_password = credentials.get("IB_PASS")
                    if not ibkr_password:
                        raise ValueError(
                            f"No password found in Vault for follower {follower.id}"
                        )
                    logger.info(f"Using Vault credentials for follower {follower.id}")
                else:
                    raise ValueError(
                        f"Failed to retrieve Vault credentials for follower {follower.id}"
                    )
            else:
                raise ValueError(
                    f"No Vault secret reference configured for follower {follower.id}"
                )

            # Start container
            container = self.docker_client.containers.run(
                self.gateway_image,
                name=container_name,
                ports={
                    "4002/tcp": host_port,  # TWS API port
                },
                environment={
                    "IB_USER": ibkr_username,
                    "IB_PASS": ibkr_password,
                    "TRADING_MODE": "paper",  # Default to paper trading
                    "TWS_SETTINGS_PATH": "/opt/ibc",
                    "DISPLAY": ":0",
                },
                detach=True,
                remove=False,
                auto_remove=False,
            )

            gateway = GatewayInstance(
                follower_id=follower.id,
                container_id=container.id,
                host_port=host_port,
                client_id=client_id,
                status=GatewayStatus.STARTING,
                container=container,
            )

            self.gateways[follower.id] = gateway

            logger.info(
                f"Started IBGateway container {container_name} for follower {follower.id} on port {host_port}"
            )

            return gateway

        except Exception as e:
            # Clean up allocated resources on failure
            self.used_ports.discard(host_port)
            self.used_client_ids.discard(client_id)
            logger.error(f"Failed to start IBGateway for follower {follower.id}: {e}")
            raise

    async def stop_follower_gateway(self, follower_id: str) -> None:
        """Stop the IBGateway container for a specific follower.

        Public method to gracefully stop a follower's gateway.

        Args:
            follower_id: The follower ID
        """
        await self._stop_gateway(follower_id)

    async def _stop_gateway(self, follower_id: str) -> None:
        """Stop the IBGateway container for a follower with enhanced graceful shutdown.

        Args:
            follower_id: The follower ID
        """
        gateway = self.gateways.get(follower_id)
        if not gateway:
            return

        logger.info(f"Starting graceful shutdown for IBGateway {follower_id}")
        start_time = time.time()

        # Step 1: Gracefully disconnect IB client with retry
        if gateway.ib_client:
            disconnect_success = False
            for attempt in range(3):
                try:
                    if gateway.ib_client.isConnected():
                        # Send disconnect request
                        gateway.ib_client.disconnect()
                        # Wait a moment for disconnect to complete
                        await asyncio.sleep(0.5)
                    disconnect_success = True
                    logger.debug(f"IB client disconnected for follower {follower_id}")
                    break
                except Exception as e:
                    logger.warning(
                        f"Attempt {attempt + 1} to disconnect IB client for follower {follower_id} failed: {e}"
                    )
                    if attempt < 2:
                        await asyncio.sleep(1)

            if not disconnect_success:
                logger.error(
                    f"Failed to disconnect IB client for follower {follower_id} after 3 attempts"
                )

            # Clear the client reference
            gateway.ib_client = None

        # Step 2: Stop container with graceful shutdown sequence
        if gateway.container:
            try:
                # Check if container is still running
                gateway.container.reload()
                if gateway.container.status == "running":
                    logger.debug(
                        f"Sending SIGTERM to container for follower {follower_id}"
                    )

                    # Send graceful stop signal (SIGTERM)
                    gateway.container.stop(timeout=30)

                    # Wait for container to exit
                    exit_result = gateway.container.wait(timeout=35)
                    exit_code = exit_result.get("StatusCode", -1)

                    if exit_code == 0:
                        logger.info(
                            f"Container for follower {follower_id} stopped gracefully (exit code: 0)"
                        )
                    else:
                        logger.warning(
                            f"Container for follower {follower_id} stopped with exit code: {exit_code}"
                        )

                        # Get final logs for debugging
                        try:
                            logs = gateway.container.logs(tail=20)
                            logger.debug(
                                f"Final container logs for {follower_id}: {logs.decode('utf-8', errors='ignore')}"
                            )
                        except Exception:
                            pass

                # Remove container
                logger.debug(f"Removing container for follower {follower_id}")
                gateway.container.remove()
                logger.info(
                    f"Container removed for follower {follower_id} (shutdown took {time.time() - start_time:.1f}s)"
                )

            except docker.errors.NotFound:
                logger.warning(
                    f"Container for follower {follower_id} was already removed"
                )
            except Exception as e:
                logger.error(
                    f"Error during graceful shutdown for follower {follower_id}: {e}"
                )

                # Last resort: force remove
                try:
                    gateway.container.kill()
                    gateway.container.remove(force=True)
                    logger.warning(
                        f"Force removed container for follower {follower_id} after graceful shutdown failed"
                    )
                except Exception as e2:
                    logger.error(
                        f"Failed to force remove container for follower {follower_id}: {e2}"
                    )

        # Step 3: Clean up resources
        self.used_ports.discard(gateway.host_port)
        self.used_client_ids.discard(gateway.client_id)

        # Step 4: Remove from tracking
        del self.gateways[follower_id]

        logger.info(
            f"Completed shutdown for IBGateway {follower_id} (total time: {time.time() - start_time:.1f}s)"
        )

    @backoff.on_exception(
        backoff.expo, (ConnectionError, OSError, Exception), max_tries=5, max_time=60
    )
    async def _connect_ib_client(self, gateway: GatewayInstance) -> IB:
        """Connect IB client to the gateway with retry logic.

        Args:
            gateway: Gateway instance

        Returns:
            Connected IB client

        Raises:
            ConnectionError: If connection fails after retries
        """
        logger.debug(f"Connecting IB client for follower {gateway.follower_id}")

        # Disconnect existing client if present
        if gateway.ib_client:
            try:
                gateway.ib_client.disconnect()
            except Exception:
                pass

        # Create new client
        ib = IB()

        try:
            # Connect to gateway
            await ib.connectAsync(
                host="localhost",
                port=gateway.host_port,
                clientId=gateway.client_id,
                timeout=10,
            )

            # Verify connection
            if not ib.isConnected():
                raise ConnectionError(
                    f"Failed to connect to IBGateway for follower {gateway.follower_id}"
                )

            # Test with a simple request
            account = ib.managedAccounts()
            if not account:
                raise ConnectionError(
                    f"No managed accounts found for follower {gateway.follower_id}"
                )

            gateway.ib_client = ib
            logger.info(
                f"IB client connected for follower {gateway.follower_id} on port {gateway.host_port}"
            )

            return ib

        except Exception as e:
            try:
                ib.disconnect()
            except Exception:
                pass
            logger.error(
                f"Failed to connect IB client for follower {gateway.follower_id}: {e}"
            )
            raise

    async def _monitor_gateways(self) -> None:
        """Monitor gateway containers and maintain health."""
        logger.info("Starting gateway monitoring")

        while not self._shutdown:
            try:
                current_time = time.time()

                for follower_id, gateway in list(self.gateways.items()):
                    try:
                        await self._check_gateway_health(gateway, current_time)
                    except Exception as e:
                        logger.error(
                            f"Error checking health for follower {follower_id}: {e}"
                        )

                # Wait for next check
                await asyncio.sleep(self.healthcheck_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in gateway monitoring: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying

        logger.info("Gateway monitoring stopped")

    async def _check_gateway_health(
        self, gateway: GatewayInstance, current_time: float
    ) -> None:
        """Check the health of a gateway instance.

        Args:
            gateway: Gateway instance to check
            current_time: Current timestamp
        """
        # Skip if recently checked
        if (
            gateway.last_healthcheck
            and current_time - gateway.last_healthcheck < self.healthcheck_interval
        ):
            return

        gateway.last_healthcheck = current_time

        # Check container status
        if gateway.container:
            try:
                gateway.container.reload()
                container_status = gateway.container.status

                # Get container logs for debugging
                logs = gateway.container.logs(tail=10, timestamps=True)
                if logs and gateway.status == GatewayStatus.STARTING:
                    logger.debug(
                        f"Recent container logs for follower {gateway.follower_id}: {logs.decode('utf-8', errors='ignore')[-500:]}"
                    )

                if container_status == "running":
                    # Check container health status if available
                    health_status = (
                        gateway.container.attrs.get("State", {})
                        .get("Health", {})
                        .get("Status")
                    )
                    if health_status and health_status != "healthy":
                        logger.warning(
                            f"Gateway container for follower {gateway.follower_id} is {health_status}"
                        )

                    if gateway.status == GatewayStatus.STARTING:
                        # Check if gateway is ready by attempting connection
                        try:
                            await self._connect_ib_client(gateway)
                            gateway.status = GatewayStatus.RUNNING
                            logger.info(
                                f"Gateway for follower {gateway.follower_id} is now running"
                            )
                        except Exception as e:
                            # Still starting up - check startup time
                            created_timestamp = gateway.container.attrs.get(
                                "Created", ""
                            )
                            if created_timestamp:
                                # Parse ISO timestamp
                                from datetime import datetime

                                created_dt = datetime.fromisoformat(
                                    created_timestamp.replace("Z", "+00:00")
                                )
                                startup_time = current_time - created_dt.timestamp()

                                if startup_time > self.max_startup_time:
                                    gateway.status = GatewayStatus.FAILED
                                    logger.error(
                                        f"Gateway for follower {gateway.follower_id} failed to start within {self.max_startup_time}s: {e}"
                                    )
                                else:
                                    logger.debug(
                                        f"Gateway for follower {gateway.follower_id} still starting ({startup_time:.0f}s): {e}"
                                    )

                    elif gateway.status == GatewayStatus.RUNNING:
                        # Enhanced health check with connection validation
                        connection_healthy = False

                        if gateway.ib_client:
                            try:
                                # Check if connected
                                if gateway.ib_client.isConnected():
                                    # Perform a lightweight API call to verify connection is truly alive
                                    server_time = gateway.ib_client.reqCurrentTime()
                                    if server_time:
                                        connection_healthy = True
                                        logger.debug(
                                            f"Gateway for follower {gateway.follower_id} health check passed (server time: {server_time})"
                                        )
                            except Exception as e:
                                logger.warning(
                                    f"Health probe failed for follower {gateway.follower_id}: {e}"
                                )

                        if not connection_healthy:
                            logger.warning(
                                f"IB connection unhealthy for follower {gateway.follower_id}, attempting reconnect"
                            )
                            try:
                                # Disconnect existing client if any
                                if gateway.ib_client:
                                    try:
                                        gateway.ib_client.disconnect()
                                    except Exception:
                                        pass
                                    gateway.ib_client = None

                                # Reconnect
                                await self._connect_ib_client(gateway)
                                logger.info(
                                    f"Successfully reconnected IB client for follower {gateway.follower_id}"
                                )
                            except Exception as e:
                                logger.error(
                                    f"Failed to reconnect IB client for follower {gateway.follower_id}: {e}"
                                )
                                gateway.status = GatewayStatus.FAILED

                                # Schedule container restart in the background
                                logger.info(
                                    f"Scheduling container restart for follower {gateway.follower_id}"
                                )
                                asyncio.create_task(
                                    self._restart_failed_gateway(gateway.follower_id)
                                )

                elif container_status in ["exited", "dead", "removing"]:
                    gateway.status = GatewayStatus.STOPPED
                    exit_code = gateway.container.attrs.get("State", {}).get(
                        "ExitCode", "unknown"
                    )
                    logger.warning(
                        f"Gateway container for follower {gateway.follower_id} has stopped (status: {container_status}, exit code: {exit_code})"
                    )

                    # Get container logs for debugging
                    try:
                        logs = gateway.container.logs(tail=50)
                        logger.error(
                            f"Container logs for stopped gateway {gateway.follower_id}: {logs.decode('utf-8', errors='ignore')}"
                        )
                    except Exception:
                        pass

            except docker.errors.NotFound:
                gateway.status = GatewayStatus.STOPPED
                logger.warning(
                    f"Gateway container for follower {gateway.follower_id} not found"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error checking health for follower {gateway.follower_id}: {e}"
                )

    def _allocate_port(self) -> int:
        """Allocate an available port for a gateway.

        Returns:
            Available port number

        Raises:
            RuntimeError: If no ports available
        """
        for port in range(self.port_range_start, self.port_range_end + 1):
            if port not in self.used_ports:
                self.used_ports.add(port)
                return port

        raise RuntimeError("No available ports for IBGateway")

    def _allocate_client_id(self) -> int:
        """Allocate a random client ID for TWS connection.

        Returns:
            Available client ID

        Raises:
            RuntimeError: If no client IDs available
        """
        attempts = 100  # Prevent infinite loop
        while attempts > 0:
            client_id = random.randint(
                self.client_id_range_start, self.client_id_range_end
            )
            if client_id not in self.used_client_ids:
                self.used_client_ids.add(client_id)
                return client_id
            attempts -= 1

        raise RuntimeError("No available client IDs for TWS connection")

    async def _restart_failed_gateway(self, follower_id: str) -> bool:
        """Restart a failed gateway container.

        Args:
            follower_id: The follower ID

        Returns:
            True if restart was successful, False otherwise
        """
        logger.info(f"Attempting to restart gateway for follower {follower_id}")

        # First, clean up the existing gateway
        await self._stop_gateway(follower_id)

        # Get follower configuration from database
        db = get_mongo_db()
        if not db:
            logger.error("MongoDB connection not available for gateway restart")
            return False

        try:
            followers_collection = db["followers"]
            follower_doc = await followers_collection.find_one(
                {
                    "id": follower_id,
                    "enabled": True,
                    "state": FollowerState.ACTIVE.value,
                }
            )

            if not follower_doc:
                logger.warning(f"Follower {follower_id} not found or not active")
                return False

            follower = Follower.model_validate(follower_doc)

            # Restart the gateway
            await self._start_gateway(follower)

            # Wait a moment and check if it started successfully
            await asyncio.sleep(5)

            gateway = self.gateways.get(follower_id)
            if gateway and gateway.status != GatewayStatus.FAILED:
                logger.info(
                    f"Successfully restarted gateway for follower {follower_id}"
                )
                return True
            else:
                logger.error(f"Gateway restart failed for follower {follower_id}")
                return False

        except Exception as e:
            logger.error(f"Error restarting gateway for follower {follower_id}: {e}")
            return False

    async def reload_followers(self) -> None:
        """Reload followers from database and update gateways accordingly."""
        logger.info("Reloading followers configuration")

        # Get current enabled followers
        db = get_mongo_db()
        if not db:
            logger.error("MongoDB connection not available for reload")
            return

        followers_collection = db["followers"]
        cursor = followers_collection.find(
            {"enabled": True, "state": FollowerState.ACTIVE.value}
        )

        active_follower_ids = set()
        async for doc in cursor:
            try:
                follower = Follower.model_validate(doc)
                active_follower_ids.add(follower.id)

                # Start gateway if not already running
                if follower.id not in self.gateways:
                    await self._start_gateway(follower)
                else:
                    # Check if existing gateway needs restart
                    gateway = self.gateways.get(follower.id)
                    if gateway and gateway.status == GatewayStatus.FAILED:
                        logger.info(
                            f"Restarting failed gateway for follower {follower.id}"
                        )
                        await self._restart_failed_gateway(follower.id)

            except Exception as e:
                logger.error(f"Failed to process follower during reload: {e}")

        # Stop gateways for followers that are no longer active
        for follower_id in list(self.gateways.keys()):
            if follower_id not in active_follower_ids:
                await self._stop_gateway(follower_id)

        logger.info(f"Followers reloaded, now managing {len(self.gateways)} gateways")

    def get_gateway_status(self, follower_id: str) -> GatewayStatus | None:
        """Get the status of a gateway for a follower.

        Args:
            follower_id: The follower ID

        Returns:
            Gateway status or None if not found
        """
        gateway = self.gateways.get(follower_id)
        return gateway.status if gateway else None

    def list_gateways(self) -> dict[str, dict]:
        """List all gateways and their status.

        Returns:
            Dictionary mapping follower IDs to gateway info
        """
        result = {}
        for follower_id, gateway in self.gateways.items():
            result[follower_id] = {
                "status": gateway.status.value,
                "host_port": gateway.host_port,
                "client_id": gateway.client_id,
                "container_id": gateway.container_id,
                "connected": (
                    gateway.ib_client.isConnected() if gateway.ib_client else False
                ),
            }
        return result

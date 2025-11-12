"""Base trading service for SpreadPilot."""

import asyncio
import datetime
import time
from enum import Enum

# Removed firebase_admin imports
from motor.motor_asyncio import AsyncIOMotorDatabase  # Added Motor import
from spreadpilot_core.db.mongodb import (  # Added MongoDB imports
    close_mongo_connection,
    connect_to_mongo,
    get_mongo_db,
)
from spreadpilot_core.logging import get_logger
from spreadpilot_core.models import Follower
from spreadpilot_core.utils.time import (
    format_ny_time,
    get_ny_time,
    is_market_open,
    seconds_until_market_open,
)

from ..config import VERTICAL_SPREADS_STRATEGY, Settings
from ..signal_generator import QQQSignalGenerator
from .alerts import AlertManager
from .ibkr import IBKRManager
from .pnl_service import PnLService
from .positions import PositionManager
from .signals import SignalProcessor
from .time_value_monitor import TimeValueMonitor
from .vertical_spreads_strategy_handler import VerticalSpreadsStrategyHandler

logger = get_logger(__name__)


class ServiceStatus(str, Enum):
    """Service status enum."""

    STARTING = "STARTING"
    RUNNING = "RUNNING"
    WAITING_FOR_MARKET = "WAITING_FOR_MARKET"
    WAITING_FOR_SIGNAL = "WAITING_FOR_SIGNAL"
    TRADING = "TRADING"
    MONITORING = "MONITORING"
    ERROR = "ERROR"
    SHUTDOWN = "SHUTDOWN"


class TradingService:
    """Trading service for SpreadPilot."""

    def __init__(
        self,
        settings: Settings,
    ):
        """Initialize the trading service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.signal_generator: QQQSignalGenerator | None = None  # Initialized after IBKR connection
        self.status = ServiceStatus.STARTING
        self.active_followers: dict[str, Follower] = {}
        self.mongo_db: AsyncIOMotorDatabase | None = None  # Changed db to mongo_db
        self.vault_client = None
        self.health_check_time = time.time()

        # MongoDB client/db will be initialized in _init_mongo called by run()

        # Initialize Vault client
        self._init_vault_client()

        # Initialize managers
        self.ibkr_manager = IBKRManager(self)
        self.position_manager = PositionManager(self)
        self.alert_manager = AlertManager(self)
        self.signal_processor = SignalProcessor(self)
        self.pnl_service = PnLService(self)
        self.time_value_monitor = TimeValueMonitor(self)
        self.vertical_spreads_strategy_handler = VerticalSpreadsStrategyHandler(
            self, VERTICAL_SPREADS_STRATEGY
        )

        logger.info("Initialized trading service")

    # Removed _init_firebase method

    async def _init_mongo(self):
        """Initialize MongoDB connection using the core module."""
        if self.mongo_db is None:
            try:
                await connect_to_mongo()  # Ensure client is connected
                self.mongo_db = await get_mongo_db()  # Get the database handle
                logger.info("MongoDB connection established and database handle acquired.")
            except Exception as e:
                logger.error(f"Error initializing MongoDB: {e}", exc_info=True)
                self.status = ServiceStatus.ERROR
                # Propagate the error to stop the service startup if connection fails
                raise

    def _init_vault_client(self):
        """Initialize Vault client."""
        try:
            if self.settings.vault_enabled:
                from spreadpilot_core.utils.vault import get_vault_client

                self.vault_client = get_vault_client()
                # Override client settings with config values
                self.vault_client.vault_url = self.settings.vault_url
                if self.settings.vault_token:
                    self.vault_client.vault_token = self.settings.vault_token
                self.vault_client.mount_point = self.settings.vault_mount_point
                # Reset client to pick up new settings
                self.vault_client._client = None
                logger.info("Initialized Vault client")
            else:
                logger.info("Vault integration is disabled")
        except Exception as e:
            logger.error(f"Error initializing Vault client: {e}")
            self.status = ServiceStatus.ERROR

    async def run(self, shutdown_event: asyncio.Event):
        """Run the trading service.

        Args:
            shutdown_event: Event to signal shutdown
        """
        try:
            logger.info("Starting trading service")

            # Initialize MongoDB connection
            await self._init_mongo()
            if self.status == ServiceStatus.ERROR:  # Check if mongo init failed
                return

            # Initialize signal generator (if enabled) after IBKR connection
            if self.settings.signal_generator_enabled:
                logger.info("Initializing internal signal generator")
                # Get IBKR client from manager (will connect if not already connected)
                ib_client = self.ibkr_manager.ib

                self.signal_generator = QQQSignalGenerator(
                    ib_client=ib_client,
                    short_leg_delta=self.settings.short_leg_delta,
                    long_leg_delta=self.settings.long_leg_delta,
                    sma_short_period=self.settings.sma_short_period,
                    sma_long_period=self.settings.sma_long_period,
                    qty_per_leg=self.settings.qty_per_leg,
                )
                logger.info("Signal generator initialized successfully")
            else:
                logger.info("Signal generator is disabled")

            # Load active followers
            await self.load_active_followers()
            if self.status == ServiceStatus.ERROR:  # Check if follower loading failed
                return

            # Start background tasks
            position_check_task = asyncio.create_task(
                self.position_manager.check_positions_periodically(shutdown_event)
            )

            # Start P&L monitoring service
            pnl_monitoring_task = asyncio.create_task(
                self.pnl_service.start_monitoring(shutdown_event)
            )

            # Start time value monitoring service
            time_value_monitor_task = asyncio.create_task(
                self.time_value_monitor.start_monitoring()
            )

            # Start the Vertical Spreads Strategy handler
            vertical_spreads_task = asyncio.create_task(
                self.vertical_spreads_strategy_handler.run(shutdown_event)
            )

            # Main loop
            while not shutdown_event.is_set():
                try:
                    # Update health check time
                    self.health_check_time = time.time()

                    # Check if market is open
                    if not is_market_open():
                        # Calculate time until market open
                        seconds = seconds_until_market_open()

                        if seconds > 0:
                            # Wait for market to open
                            self.status = ServiceStatus.WAITING_FOR_MARKET

                            logger.info(
                                "Waiting for market to open",
                                seconds=seconds,
                                time_until=format_ny_time(
                                    get_ny_time() + datetime.timedelta(seconds=seconds)
                                ),
                            )

                            # Wait for market to open or shutdown
                            try:
                                await asyncio.wait_for(
                                    shutdown_event.wait(),
                                    timeout=min(seconds, 60),  # Check every minute
                                )
                            except TimeoutError:
                                # Continue waiting
                                continue

                            # If shutdown event is set, exit
                            if shutdown_event.is_set():
                                break

                            continue

                    # Market is open, monitoring
                    # Note: Signal generation is now handled by VerticalSpreadsStrategyHandler
                    # at 9:27 AM daily. This main loop is now primarily for health checks.
                    self.status = ServiceStatus.MONITORING

                    # Wait before next check
                    await asyncio.sleep(60)  # Check every minute

                except Exception as e:
                    logger.error(f"Error in trading service main loop: {e}", exc_info=True)
                    self.status = ServiceStatus.ERROR

                    # Wait before retrying
                    await asyncio.sleep(10)

            # Cancel background tasks
            position_check_task.cancel()
            pnl_monitoring_task.cancel()
            vertical_spreads_task.cancel()

            # Stop time value monitor
            await self.time_value_monitor.stop_monitoring()
            time_value_monitor_task.cancel()

            # Wait for background tasks to complete
            try:
                await asyncio.gather(
                    position_check_task,
                    pnl_monitoring_task,
                    vertical_spreads_task,
                    time_value_monitor_task,
                    return_exceptions=True,  # Don't let one cancelled task stop others
                )
            except asyncio.CancelledError:
                logger.debug("Background tasks cancelled.")

            logger.info("Trading service stopped")
            self.status = ServiceStatus.SHUTDOWN

        except Exception as e:
            logger.error(f"Error in trading service: {e}", exc_info=True)
            self.status = ServiceStatus.ERROR

    async def shutdown(self):
        """Shut down the trading service."""
        logger.info("Shutting down trading service")
        # Disconnect from IBKR
        await self.ibkr_manager.disconnect_all()

        # Close MongoDB connection
        await close_mongo_connection()

        self.status = ServiceStatus.SHUTDOWN
        logger.info("Trading service shutdown complete")

    async def load_active_followers(self):
        """Load active followers from MongoDB."""
        if not self.mongo_db:
            logger.error("MongoDB is not initialized. Cannot load followers.")
            self.status = ServiceStatus.ERROR
            return

        logger.info("Loading active followers from MongoDB...")
        self.active_followers = {}  # Clear existing followers
        try:
            # Query followers collection in MongoDB
            followers_collection = self.mongo_db["followers"]
            cursor = followers_collection.find({"enabled": True})

            # Process followers
            async for doc in cursor:
                try:
                    # Create follower model using Pydantic's validation
                    # This automatically handles the _id alias and type conversions
                    follower = Follower.model_validate(doc)

                    # Add to active followers
                    self.active_followers[follower.id] = follower

                    logger.debug(  # Changed to debug to reduce noise
                        "Loaded active follower",
                        follower_id=follower.id,
                        email=follower.email,
                    )
                except Exception as validation_error:
                    # Log error for specific document but continue loading others
                    doc_id = doc.get("_id", "UNKNOWN_ID")
                    logger.error(
                        f"Error validating follower data for doc {doc_id}: {validation_error}",
                        exc_info=True,
                    )

            logger.info(
                "Finished loading active followers",
                count=len(self.active_followers),
            )
        except Exception as e:
            logger.error(f"Error loading active followers from MongoDB: {e}", exc_info=True)
            self.status = ServiceStatus.ERROR

    async def get_secret(self, secret_ref: str) -> str | None:
        """Get secret from Vault.

        Args:
            secret_ref: Secret reference

        Returns:
            Secret value or None if not available
        """
        if not self.settings.vault_enabled or not self.vault_client:
            logger.warning("Vault is not enabled or client not initialized")
            return None

        try:
            # Get secret from Vault
            secret = self.vault_client.get_secret(secret_ref)
            if isinstance(secret, dict):
                # If it's a dict, return the first value or look for a specific key
                if "value" in secret:
                    return secret["value"]
                elif len(secret) == 1:
                    return list(secret.values())[0]
                else:
                    logger.warning(
                        f"Secret {secret_ref} is a dict with multiple values, returning None"
                    )
                    return None
            return secret
        except Exception as e:
            logger.error(f"Error getting secret {secret_ref}: {e}")
            return None

    def get_ibkr_credentials(self, secret_ref: str) -> dict[str, str] | None:
        """Get IBKR credentials from Vault.

        Args:
            secret_ref: Secret reference for IBKR credentials

        Returns:
            Dict with 'IB_USER' and 'IB_PASS' keys or None if not found
        """
        if not self.settings.vault_enabled or not self.vault_client:
            logger.warning("Vault is not enabled or client not initialized")
            return None

        try:
            credentials = self.vault_client.get_ibkr_credentials(secret_ref)
            if credentials:
                logger.info(f"Successfully retrieved IBKR credentials from Vault for: {secret_ref}")
                return credentials
            else:
                logger.warning(f"No IBKR credentials found in Vault for: {secret_ref}")
                return None
        except Exception as e:
            logger.error(f"Error getting IBKR credentials from Vault: {e}")
            return None

    def is_healthy(self) -> bool:
        """Check if the service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        # Check if status is ERROR
        if self.status == ServiceStatus.ERROR:
            return False

        # Check if health check time is recent
        if time.time() - self.health_check_time > 60:  # 60 seconds
            return False

        return True

    def get_status(self) -> str:
        """Get service status.

        Returns:
            Service status
        """
        return self.status.value

    def is_ibkr_connected(self) -> bool:
        """Check if IBKR is connected.

        Returns:
            True if connected, False otherwise
        """
        return self.ibkr_manager.is_connected()

    def is_signal_generator_enabled(self) -> bool:
        """Check if signal generator is enabled and initialized.

        Returns:
            True if signal generator is available, False otherwise
        """
        return self.signal_generator is not None

    def get_active_follower_count(self) -> int:
        """Get number of active followers.

        Returns:
            Number of active followers
        """
        return len(self.active_followers)

    async def close_positions(self, follower_id: str) -> dict:
        """Close all positions for a follower.

        Args:
            follower_id: Follower ID

        Returns:
            Dict with results
        """
        return await self.position_manager.close_positions(follower_id)

    async def close_all_positions(self) -> dict:
        """Close all positions for all followers.

        Returns:
            Dict with results
        """
        return await self.position_manager.close_all_positions()

"""Base trading service for SpreadPilot."""

import asyncio
import datetime
import time
from enum import Enum
from typing import Dict, Optional

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import secretmanager

from spreadpilot_core.ibkr import IBKRClient
from spreadpilot_core.logging import get_logger
from spreadpilot_core.models import Follower, Position
from spreadpilot_core.utils.time import (
    format_ny_time,
    get_ny_time,
    is_market_open,
    seconds_until_market_open,
)

from ..config import Settings, ORIGINAL_EMA_STRATEGY
from ..sheets import GoogleSheetsClient
from .alerts import AlertManager
from .ibkr import IBKRManager
from .positions import PositionManager
from .signals import SignalProcessor
from .original_strategy_handler import OriginalStrategyHandler

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
        sheets_client: GoogleSheetsClient,
    ):
        """Initialize the trading service.

        Args:
            settings: Application settings
            sheets_client: Google Sheets client
        """
        self.settings = settings
        self.sheets_client = sheets_client
        self.status = ServiceStatus.STARTING
        self.active_followers: Dict[str, Follower] = {}
        self.db = None
        self.secret_client = None
        self.health_check_time = time.time()
        
        # Initialize Firebase
        self._init_firebase()
        
        # Initialize Secret Manager
        self._init_secret_manager()
        
        # Initialize managers
        self.ibkr_manager = IBKRManager(self)
        self.position_manager = PositionManager(self)
        self.alert_manager = AlertManager(self)
        self.signal_processor = SignalProcessor(self)
        self.original_strategy_handler = OriginalStrategyHandler(self, ORIGINAL_EMA_STRATEGY)
        
        logger.info("Initialized trading service")

    def _init_firebase(self):
        """Initialize Firebase."""
        try:
            # Check if already initialized
            if firebase_admin._apps:
                self.db = firestore.client()
                logger.info("Firebase already initialized")
                return
            
            # Initialize Firebase
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {
                "projectId": self.settings.project_id,
            })
            
            # Get Firestore client
            self.db = firestore.client()
            
            logger.info("Initialized Firebase")
        except Exception as e:
            logger.error(f"Error initializing Firebase: {e}")
            self.status = ServiceStatus.ERROR

    def _init_secret_manager(self):
        """Initialize Secret Manager."""
        try:
            # Initialize Secret Manager client
            self.secret_client = secretmanager.SecretManagerServiceClient()
            
            logger.info("Initialized Secret Manager")
        except Exception as e:
            logger.error(f"Error initializing Secret Manager: {e}")
            self.status = ServiceStatus.ERROR

    async def run(self, shutdown_event: asyncio.Event):
        """Run the trading service.

        Args:
            shutdown_event: Event to signal shutdown
        """
        try:
            logger.info("Starting trading service")
            
            # Connect to Google Sheets
            if not await self.sheets_client.connect():
                logger.error("Failed to connect to Google Sheets")
                self.status = ServiceStatus.ERROR
                return
            
            # Load active followers
            await self.load_active_followers()
            
            # Initialize and start Original Strategy Handler (if enabled)
            await self.original_strategy_handler.initialize()
            original_strategy_task = asyncio.create_task(
                self.original_strategy_handler.run(shutdown_event)
            )
            
            # Start other background tasks
            position_check_task = asyncio.create_task(
                self.position_manager.check_positions_periodically(shutdown_event)
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
                            except asyncio.TimeoutError:
                                # Continue waiting
                                continue
                            
                            # If shutdown event is set, exit
                            if shutdown_event.is_set():
                                break
                            
                            continue
                    
                    # Market is open, wait for signal
                    self.status = ServiceStatus.WAITING_FOR_SIGNAL
                    
                    # Fetch signal
                    signal = await self.sheets_client.fetch_signal()
                    
                    if not signal:
                        # No signal yet, wait and retry
                        await asyncio.sleep(self.settings.polling_interval_seconds)
                        continue
                    
                    # Process signal
                    self.status = ServiceStatus.TRADING
                    
                    logger.info(
                        "Processing signal",
                        signal=signal,
                    )
                    
                    # Process signal for all active followers
                    for follower_id, follower in self.active_followers.items():
                        await self.signal_processor.process_signal(
                            strategy=signal["strategy"],
                            qty_per_leg=signal["qty_per_leg"],
                            strike_long=signal["strike_long"],
                            strike_short=signal["strike_short"],
                            follower_id=follower_id,
                        )
                    
                    # Switch to monitoring mode
                    self.status = ServiceStatus.MONITORING
                    
                    # Wait for next trading day
                    await asyncio.sleep(60 * 60)  # Check every hour
                
                except Exception as e:
                    logger.error(f"Error in trading service main loop: {e}", exc_info=True)
                    self.status = ServiceStatus.ERROR
                    
                    # Wait before retrying
                    await asyncio.sleep(10)
            
            # Cancel background tasks
            position_check_task.cancel()
            original_strategy_task.cancel()
            
            # Wait for background tasks to complete
            try:
                await asyncio.gather(
                    position_check_task,
                    original_strategy_task,
                    return_exceptions=True # Don't let one cancelled task stop others
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
        
        # Disconnect from IBKR (main manager)
        await self.ibkr_manager.disconnect_all()
        
        # Shutdown Original Strategy Handler
        await self.original_strategy_handler.shutdown()
        
        self.status = ServiceStatus.SHUTDOWN
        logger.info("Trading service shutdown complete")

    async def load_active_followers(self):
        """Load active followers from Firestore."""
        try:
            # Query followers collection
            followers_ref = self.db.collection("followers")
            query = followers_ref.where("enabled", "==", True)
            
            # Get followers
            followers_snapshot = query.get()
            
            # Process followers
            for doc in followers_snapshot:
                follower_id = doc.id
                follower_data = doc.to_dict()
                
                # Create follower model
                follower = Follower.from_dict(follower_id, follower_data)
                
                # Add to active followers
                self.active_followers[follower_id] = follower
                
                logger.info(
                    "Loaded active follower",
                    follower_id=follower_id,
                    email=follower.email,
                )
            
            logger.info(
                "Loaded active followers",
                count=len(self.active_followers),
            )
        except Exception as e:
            logger.error(f"Error loading active followers: {e}")
            self.status = ServiceStatus.ERROR

    async def get_secret(self, secret_ref: str) -> Optional[str]:
        """Get secret from Secret Manager.

        Args:
            secret_ref: Secret reference

        Returns:
            Secret value or None if not available
        """
        try:
            # Build the resource name of the secret version
            name = f"projects/{self.settings.project_id}/secrets/{secret_ref}/versions/latest"
            
            # Access the secret version
            response = self.secret_client.access_secret_version(request={"name": name})
            
            # Return the decoded payload
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Error getting secret {secret_ref}: {e}")
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

    def is_sheets_connected(self) -> bool:
        """Check if Google Sheets is connected.

        Returns:
            True if connected, False otherwise
        """
        return self.sheets_client.is_connected()

    def get_active_follower_count(self) -> int:
        """Get number of active followers.

        Returns:
            Number of active followers
        """
        return len(self.active_followers)

    async def close_positions(self, follower_id: str) -> Dict:
        """Close all positions for a follower.

        Args:
            follower_id: Follower ID

        Returns:
            Dict with results
        """
        return await self.position_manager.close_positions(follower_id)

    async def close_all_positions(self) -> Dict:
        """Close all positions for all followers.

        Returns:
            Dict with results
        """
        return await self.position_manager.close_all_positions()
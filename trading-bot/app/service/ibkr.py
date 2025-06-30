"""IBKR manager for SpreadPilot trading service."""

from spreadpilot_core.ibkr import IBKRClient
from spreadpilot_core.logging import get_logger

logger = get_logger(__name__)


class IBKRManager:
    """Manager for IBKR client interactions."""

    def __init__(self, service):
        """Initialize the IBKR manager.

        Args:
            service: Trading service instance
        """
        self.service = service
        self.ibkr_clients: dict[str, IBKRClient] = {}

        logger.info("Initialized IBKR manager")

    async def get_client(self, follower_id: str) -> IBKRClient | None:
        """Get IBKR client for a follower.

        Args:
            follower_id: Follower ID

        Returns:
            IBKR client or None if not available
        """
        # Check if client already exists
        if follower_id in self.ibkr_clients:
            # Check if client is connected
            client = self.ibkr_clients[follower_id]
            if await client.ensure_connected():
                return client

            # Client is not connected, remove it
            del self.ibkr_clients[follower_id]

        # Get follower
        follower = self.service.active_followers.get(follower_id)
        if not follower:
            logger.error(f"Follower not found: {follower_id}")
            return None

        # Get IBKR password from Secret Manager
        ibkr_password = await self.service.get_secret(follower.ibkr_secret_ref)
        if not ibkr_password:
            logger.error(f"Failed to get IBKR password for follower {follower_id}")
            return None

        # Create IBKR client
        client = IBKRClient(
            username=follower.ibkr_username,
            password=ibkr_password,
            trading_mode=self.service.settings.ib_trading_mode,
            host=self.service.settings.ib_gateway_host,
            port=self.service.settings.ib_gateway_port,
            client_id=self.service.settings.ib_client_id,
        )

        # Connect to IBKR
        if not await client.connect():
            logger.error(f"Failed to connect to IBKR for follower {follower_id}")
            return None

        # Store client
        self.ibkr_clients[follower_id] = client

        logger.info(
            "Connected to IBKR",
            follower_id=follower_id,
            username=follower.ibkr_username,
        )

        return client

    async def disconnect_all(self):
        """Disconnect all IBKR clients."""
        for follower_id, client in self.ibkr_clients.items():
            try:
                await client.disconnect()
                logger.info(f"Disconnected from IBKR for follower {follower_id}")
            except Exception as e:
                logger.error(f"Error disconnecting from IBKR for follower {follower_id}: {e}")

        # Clear clients
        self.ibkr_clients = {}

    async def check_margin_for_trade(
        self,
        follower_id: str,
        strategy: str,
        qty_per_leg: int,
        strike_long: float,
        strike_short: float,
    ) -> tuple[bool, str | None]:
        """Check if account has enough margin for a trade.

        Args:
            follower_id: Follower ID
            strategy: Strategy type ("Long" for Bull Put, "Short" for Bear Call)
            qty_per_leg: Quantity per leg
            strike_long: Strike price for long leg
            strike_short: Strike price for short leg

        Returns:
            Tuple of (has_margin, error_message)
        """
        # Get IBKR client
        client = await self.get_client(follower_id)
        if not client:
            return False, "Failed to connect to IBKR"

        # Check margin
        return await client.check_margin_for_trade(
            strategy=strategy,
            qty_per_leg=qty_per_leg,
            strike_long=strike_long,
            strike_short=strike_short,
        )

    async def place_vertical_spread(
        self,
        follower_id: str,
        strategy: str,
        qty_per_leg: int,
        strike_long: float,
        strike_short: float,
    ) -> dict:
        """Place a vertical spread order.

        Args:
            follower_id: Follower ID
            strategy: Strategy type ("Long" for Bull Put, "Short" for Bear Call)
            qty_per_leg: Quantity per leg
            strike_long: Strike price for long leg
            strike_short: Strike price for short leg

        Returns:
            Dict with order status and details
        """
        # Get IBKR client
        client = await self.get_client(follower_id)
        if not client:
            return {
                "status": "REJECTED",
                "error": "Failed to connect to IBKR",
            }

        # Place vertical spread
        return await client.place_vertical_spread(
            strategy=strategy,
            qty_per_leg=qty_per_leg,
            strike_long=strike_long,
            strike_short=strike_short,
            max_attempts=self.service.settings.max_attempts,
            price_increment=self.service.settings.price_increment,
            min_price=self.service.settings.min_price,
            timeout_seconds=self.service.settings.timeout_seconds,
        )

    async def close_positions(self, follower_id: str) -> dict:
        """Close all positions for a follower.

        Args:
            follower_id: Follower ID

        Returns:
            Dict with results
        """
        # Get IBKR client
        client = await self.get_client(follower_id)
        if not client:
            return {
                "success": False,
                "error": "Failed to connect to IBKR",
            }

        # Close positions
        result = await client.close_all_positions()

        return {
            "success": result.get("status") == "SUCCESS",
            "results": result.get("results", []),
            "error": result.get("error"),
        }

    async def exercise_options(
        self,
        follower_id: str,
        strike: float,
        right: str,
        quantity: int,
    ) -> dict:
        """Exercise options.

        Args:
            follower_id: Follower ID
            strike: Strike price
            right: Option right ("C" or "P")
            quantity: Quantity to exercise

        Returns:
            Dict with results
        """
        # Get IBKR client
        client = await self.get_client(follower_id)
        if not client:
            return {
                "success": False,
                "error": "Failed to connect to IBKR",
            }

        # Exercise options
        result = await client.exercise_options(
            strike=strike,
            right=right,
            quantity=quantity,
        )

        return {
            "success": result.get("status") == "SUCCESS",
            "error": result.get("error"),
        }

    def is_connected(self) -> bool:
        """Check if any IBKR client is connected.

        Returns:
            True if any client is connected, False otherwise
        """
        return len(self.ibkr_clients) > 0

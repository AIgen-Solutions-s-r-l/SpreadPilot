"""Handler for the Vertical Spreads on QQQ Strategy."""

import asyncio
import datetime
from typing import TYPE_CHECKING, Any

from ib_insync import Order

from spreadpilot_core.ibkr.client import IBKRClient
from spreadpilot_core.logging import get_logger
from spreadpilot_core.models.alert import Alert
from spreadpilot_core.utils.time import get_ny_time

if TYPE_CHECKING:
    from .base import TradingService

logger = get_logger(__name__)


class VerticalSpreadsStrategyHandler:
    """
    Implements the logic for the Vertical Spreads on QQQ trading strategy.
    Manages its own IBKR connection and state.
    """

    def __init__(self, service: "TradingService", config: dict[str, Any]):
        """
        Initialize the VerticalSpreadsStrategyHandler.

        Args:
            service: The main TradingService instance.
            config: Strategy-specific configuration dictionary.
        """
        self.service = service
        self.config = config
        self.ibkr_client: IBKRClient | None = None
        self.positions: dict[str, float] = {}  # Symbol -> Quantity
        self.active_orders: dict[str, list[Order]] = {}  # Symbol -> List of active orders
        self._initialized = False
        self._last_signal_check = None
        self._last_time_value_check = None
        logger.info("VerticalSpreadsStrategyHandler initialized.")

    async def initialize(self):
        """
        Initialize the handler: connect to IBKR, fetch initial data.
        """
        if not self.config.get("enabled", False):
            logger.info("Vertical Spreads Strategy is disabled in config.")
            return

        if self._initialized:
            logger.warning("VerticalSpreadsStrategyHandler already initialized.")
            return

        logger.info("Initializing VerticalSpreadsStrategyHandler...")
        try:
            # Use a dedicated IBKR client for the strategy
            ib_settings = {
                "host": self.service.settings.ib_gateway_host,
                "port": self.service.settings.ib_gateway_port,
                "client_id": self.service.settings.ib_client_id + 20,  # Use a different client ID
                "account": None,  # Let ib_insync determine account or fetch from secrets
                "trading_mode": self.service.settings.ib_trading_mode,
            }
            self.ibkr_client = IBKRClient(**ib_settings)
            await self.ibkr_client.connect()
            logger.info("IBKR client connected for Vertical Spreads Strategy.")

            # Fetch initial positions for QQQ
            await self._fetch_initial_positions()

            self._initialized = True
            logger.info("VerticalSpreadsStrategyHandler initialization complete.")

        except Exception as e:
            logger.error(f"Error initializing VerticalSpreadsStrategyHandler: {e}", exc_info=True)
            self._initialized = False

    async def _fetch_initial_positions(self):
        """Fetch initial portfolio positions for QQQ options."""
        if not self.ibkr_client or not self.ibkr_client.is_connected():
            logger.warning("IBKR client not connected, cannot fetch initial positions.")
            return

        logger.info("Fetching initial positions...")
        try:
            # Get positions from IBKR
            positions = await self.ibkr_client.get_positions(force_update=True)
            self.positions = positions
            logger.info(f"Initial positions fetched: {self.positions}")
        except Exception as e:
            logger.error(f"Error fetching initial positions: {e}", exc_info=True)
            self.positions = {}

    async def run(self, shutdown_event: asyncio.Event):
        """
        Main execution loop for the strategy handler.
        Monitors Google Sheets for signals at 9:27 AM NY Time and processes them.
        Also monitors Time Value of open positions.
        """
        if not self._initialized:
            logger.warning("VerticalSpreadsStrategyHandler not initialized, cannot run.")
            return

        logger.info("Starting VerticalSpreadsStrategyHandler run loop...")
        try:
            while not shutdown_event.is_set():
                # 1. Check if it's time to check for signals (9:27 AM NY Time)
                ny_time = get_ny_time()
                is_signal_time = ny_time.hour == 9 and ny_time.minute == 27

                # 2. Check for signals if it's time
                if is_signal_time and (
                    self._last_signal_check is None
                    or (ny_time - self._last_signal_check).total_seconds() > 60
                ):
                    logger.info("Checking for signals at 9:27 AM NY Time...")
                    self._last_signal_check = ny_time

                    # Generate signal using internal signal generator
                    if self.service.signal_generator:
                        logger.info("Generating signal using internal signal generator...")
                        signal = await self.service.signal_generator.generate_signal()

                        if signal:
                            logger.info(f"Signal generated: {signal}")
                            await self._process_signal(signal)
                        else:
                            logger.info("No signal generated (market conditions unclear or error).")
                    else:
                        logger.warning("Signal generator not initialized. No signal generated.")

                # 3. Monitor Time Value of open positions
                if (
                    self._last_time_value_check is None
                    or (ny_time - self._last_time_value_check).total_seconds() > 60
                ):  # Check every minute
                    self._last_time_value_check = ny_time
                    await self._monitor_time_value()

                # 4. Sleep to prevent tight looping
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("VerticalSpreadsStrategyHandler run loop cancelled.")
        except Exception as e:
            logger.error(f"Error in VerticalSpreadsStrategyHandler run loop: {e}", exc_info=True)
        finally:
            logger.info("VerticalSpreadsStrategyHandler run loop finished.")
            await self.shutdown()

    async def _process_signal(self, signal: dict[str, Any]):
        """
        Process a trading signal from Google Sheets.

        Args:
            signal: Signal dictionary with strategy, qty_per_leg, strike_long, strike_short
        """
        try:
            # Validate signal
            if signal.get("ticker") != "QQQ":
                logger.warning(f"Signal ticker is not QQQ: {signal.get('ticker')}")
                return

            strategy = signal.get("strategy")
            qty_per_leg = signal.get("qty_per_leg")
            strike_long = signal.get("strike_long")
            strike_short = signal.get("strike_short")

            if not all([strategy, qty_per_leg, strike_long, strike_short]):
                logger.warning(f"Invalid signal: {signal}")
                return

            logger.info(
                f"Processing signal: {strategy} {qty_per_leg} contracts, strikes: {strike_long}/{strike_short}"
            )

            # Check funds before placing order
            has_margin, margin_error = await self._check_margin_for_trade(
                strategy=strategy,
                qty_per_leg=qty_per_leg,
                strike_long=strike_long,
                strike_short=strike_short,
            )

            if not has_margin:
                logger.error(f"Insufficient margin: {margin_error}")
                return

            # Place vertical spread order
            result = await self._place_vertical_spread(
                strategy=strategy,
                qty_per_leg=qty_per_leg,
                strike_long=strike_long,
                strike_short=strike_short,
            )

            logger.info(f"Order placement result: {result}")

            # Send alert
            if result.get("status") == "FILLED":
                await self._send_alert(
                    symbol="QQQ",
                    action="BUY" if strategy == "Long" else "SELL",
                    quantity=qty_per_leg,
                    price=result.get("fill_price"),
                    order_type="LMT",
                    signal_type=f"{strategy} Vertical Spread",
                )

        except Exception as e:
            logger.error(f"Error processing signal: {e}", exc_info=True)

    async def _check_margin_for_trade(
        self, strategy: str, qty_per_leg: int, strike_long: float, strike_short: float
    ) -> tuple[bool, str | None]:
        """
        Check if there's enough margin for the trade.

        Args:
            strategy: Strategy type ("Long" for Bull Put, "Short" for Bear Call)
            qty_per_leg: Quantity per leg
            strike_long: Strike price for long leg
            strike_short: Strike price for short leg

        Returns:
            Tuple of (has_margin, error_message)
        """
        if not self.ibkr_client or not self.ibkr_client.is_connected():
            return False, "IBKR client not connected"

        return await self.ibkr_client.check_margin_for_trade(
            strategy=strategy,
            qty_per_leg=qty_per_leg,
            strike_long=strike_long,
            strike_short=strike_short,
        )

    async def _place_vertical_spread(
        self, strategy: str, qty_per_leg: int, strike_long: float, strike_short: float
    ) -> dict[str, Any]:
        """
        Place a vertical spread order with the chasing logic.

        Args:
            strategy: Strategy type ("Long" for Bull Put, "Short" for Bear Call)
            qty_per_leg: Quantity per leg
            strike_long: Strike price for long leg
            strike_short: Strike price for short leg

        Returns:
            Dict with order status and details
        """
        if not self.ibkr_client or not self.ibkr_client.is_connected():
            return {"status": "REJECTED", "error": "IBKR client not connected"}

        # Use the client's place_vertical_spread method which implements the chasing logic
        return await self.ibkr_client.place_vertical_spread(
            strategy=strategy,
            qty_per_leg=qty_per_leg,
            strike_long=strike_long,
            strike_short=strike_short,
            max_attempts=self.config.get("max_attempts", 10),
            price_increment=self.config.get("price_increment", 0.01),
            min_price=self.config.get("min_price", 0.70),
            timeout_seconds=self.config.get("timeout_seconds", 5),
        )

    async def _monitor_time_value(self):
        """
        Monitor the Time Value of open positions and close them if Time Value < $0.10.
        """
        if not self.ibkr_client or not self.ibkr_client.is_connected():
            logger.warning("IBKR client not connected, cannot monitor Time Value.")
            return

        try:
            # Get current positions
            positions = await self.ibkr_client.get_positions(force_update=True)

            # Check for QQQ option positions
            for key, qty in positions.items():
                if "QQQ" in key and qty != 0:
                    # Calculate Time Value for the position
                    time_value = await self._calculate_time_value(key, qty)

                    if time_value is not None:
                        logger.debug(f"Time Value for {key}: ${time_value:.2f}")

                        # Close position if Time Value < $0.10
                        if time_value < 0.10:
                            logger.info(
                                f"Time Value below threshold for {key}: ${time_value:.2f}, closing position"
                            )
                            await self._close_position(key, qty)

        except Exception as e:
            logger.error(f"Error monitoring Time Value: {e}", exc_info=True)

    async def _calculate_time_value(self, position_key: str, qty: float) -> float | None:
        """
        Calculate the Time Value of an option position.

        Args:
            position_key: Position key (e.g., "QQQ-380-C")
            qty: Position quantity

        Returns:
            Time Value or None if calculation failed
        """
        try:
            # Parse position key to get contract details
            parts = position_key.split("-")
            if len(parts) < 3:
                logger.warning(f"Invalid position key: {position_key}")
                return None

            symbol = parts[0]
            strike = float(parts[1])
            right = parts[2]

            # Create option contract
            if right == "C":
                contract = self.ibkr_client._get_qqq_option_contract(strike, "C")
            elif right == "P":
                contract = self.ibkr_client._get_qqq_option_contract(strike, "P")
            else:
                logger.warning(f"Invalid option right: {right}")
                return None

            # Get market price
            option_price = await self.ibkr_client.get_market_price(contract)
            if option_price is None:
                logger.warning(f"Failed to get market price for {position_key}")
                return None

            # Get underlying price
            underlying_contract = await self.ibkr_client.get_stock_contract("QQQ")
            underlying_price = await self.ibkr_client.get_market_price(underlying_contract)
            if underlying_price is None:
                logger.warning("Failed to get underlying price for QQQ")
                return None

            # Calculate intrinsic value
            if right == "C":  # Call option
                intrinsic_value = max(0, underlying_price - strike)
            else:  # Put option
                intrinsic_value = max(0, strike - underlying_price)

            # Calculate Time Value
            time_value = option_price - intrinsic_value

            return time_value

        except Exception as e:
            logger.error(f"Error calculating Time Value for {position_key}: {e}", exc_info=True)
            return None

    async def _close_position(self, position_key: str, qty: float):
        """
        Close a position using a Market Order.

        Args:
            position_key: Position key (e.g., "QQQ-380-C")
            qty: Position quantity
        """
        try:
            # Parse position key to get contract details
            parts = position_key.split("-")
            if len(parts) < 3:
                logger.warning(f"Invalid position key: {position_key}")
                return

            symbol = parts[0]
            strike = float(parts[1])
            right = parts[2]

            # Create option contract
            if right == "C":
                contract = self.ibkr_client._get_qqq_option_contract(strike, "C")
            elif right == "P":
                contract = self.ibkr_client._get_qqq_option_contract(strike, "P")
            else:
                logger.warning(f"Invalid option right: {right}")
                return

            # Determine action based on position quantity
            action = "SELL" if qty > 0 else "BUY"
            abs_qty = abs(qty)

            # Create market order
            order = Order(orderType="MKT", action=action, totalQuantity=abs_qty)

            # Place order
            trade = await self.ibkr_client.place_order(contract, order)

            if trade:
                logger.info(
                    f"Closed position {position_key} with market order: {trade.order.orderId}"
                )

                # Send alert
                await self._send_alert(
                    symbol="QQQ",
                    action=action,
                    quantity=abs_qty,
                    price=None,  # Price unknown for market order
                    order_type="MKT",
                    signal_type="Time Value Close",
                )
            else:
                logger.error(f"Failed to close position {position_key}")

        except Exception as e:
            logger.error(f"Error closing position {position_key}: {e}", exc_info=True)

    async def _send_alert(
        self,
        symbol: str,
        action: str,
        quantity: float,
        price: float | None,
        order_type: str,
        signal_type: str,
    ):
        """
        Send an alert using the main service's alert manager.

        Args:
            symbol: Symbol (e.g., "QQQ")
            action: Order action (e.g., "BUY", "SELL")
            quantity: Order quantity
            price: Order price (can be None for market orders)
            order_type: Order type (e.g., "MKT", "LMT")
            signal_type: Signal type description
        """
        try:
            alert = Alert(
                symbol=symbol,
                action=action,
                quantity=quantity,
                price=price,
                order_type=order_type,
                strategy="VERTICAL_SPREADS",
                signal_type=signal_type,
                timestamp=datetime.datetime.now(datetime.UTC),
            )
            await self.service.alert_manager.create_alert(alert)
            logger.info(f"Sent alert: {signal_type} {action} {quantity} {symbol}")
        except Exception as e:
            logger.error(f"Failed to send alert for {symbol}: {e}", exc_info=True)

    async def shutdown(self):
        """
        Cleanly disconnect the dedicated IBKR client.
        """
        logger.info("Shutting down VerticalSpreadsStrategyHandler...")
        if self.ibkr_client and self.ibkr_client.is_connected():
            await self.ibkr_client.disconnect()
            logger.info("IBKR client for Vertical Spreads Strategy disconnected.")
        self._initialized = False

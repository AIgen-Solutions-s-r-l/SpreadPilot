"""Interactive Brokers API client wrapper for SpreadPilot."""

import asyncio
import datetime
import time
from enum import Enum
from functools import lru_cache
from typing import Any

import ib_insync
from ib_insync import BarData, Contract, Option, Order, Stock
from ib_insync import Trade as IBTrade

from ..logging import get_logger

try:
    from ..dry_run import dry_run_async
except ImportError:
    # Fallback if dry_run not available (backwards compatibility)
    def dry_run_async(operation_type: str, return_value: Any = None, log_args: bool = True):
        def decorator(func):
            return func
        return decorator

logger = get_logger(__name__)


@lru_cache(maxsize=128)
def _create_stock_contract_cached(
    symbol: str, exchange: str = "SMART", currency: str = "USD"
) -> Stock:
    """Create and cache Stock contract objects.

    Args:
        symbol: Stock ticker symbol.
        exchange: The exchange to trade on (default: SMART).
        currency: The currency (default: USD).

    Returns:
        An ib_insync.Stock contract object (cached).

    Note:
        This function is cached with LRU (Least Recently Used) policy.
        Cache size is 128 contracts, suitable for most trading scenarios.
        Cache is shared across all IBKRClient instances.
    """
    return Stock(symbol=symbol, exchange=exchange, currency=currency)


class OrderSide(str, Enum):
    """Order side enum."""

    LONG = "LONG"
    SHORT = "SHORT"


class OrderStatus(str, Enum):
    """Order status enum."""

    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    SUBMITTED = "SUBMITTED"
    PENDING = "PENDING"


class AssignmentState(str, Enum):
    """Assignment state enum."""

    NONE = "NONE"
    ASSIGNED = "ASSIGNED"
    COMPENSATED = "COMPENSATED"


class IBKRClient:
    """Interactive Brokers API client wrapper."""

    def __init__(
        self,
        username: str,
        password: str,
        trading_mode: str = "paper",
        host: str = "127.0.0.1",
        port: int = 4002,  # Default port for paper trading
        client_id: int = 1,
        timeout: int = 30,
    ):
        """Initialize the IBKR client.

        Args:
            username: IBKR username
            password: IBKR password
            trading_mode: Trading mode ("paper" or "live")
            host: IB Gateway host
            port: IB Gateway port (4001 for live, 4002 for paper)
            client_id: Client ID
            timeout: Connection timeout in seconds
        """
        self.username = username
        self.password = password
        self.trading_mode = trading_mode
        self.host = host
        self.port = port if port else (4002 if trading_mode == "paper" else 4001)
        self.client_id = client_id
        self.timeout = timeout

        # Initialize IB client
        self.ib = ib_insync.IB()
        self._connected = False

        # Cache for contracts and positions
        self._contracts_cache = {}
        self._positions_cache = {}
        self._last_positions_update = 0

        logger.info(
            "IBKR client initialized for user %s in %s mode at %s:%s",
            username,
            trading_mode,
            host,
            port,
        )

    async def connect(self) -> bool:
        """Connect to IB Gateway.

        Returns:
            True if connected successfully, False otherwise
        """
        if self._connected and self.ib.isConnected():
            logger.info("Already connected to IB Gateway")
            return True

        try:
            logger.info(
                "Connecting to IB Gateway",
                host=self.host,
                port=self.port,
                client_id=self.client_id,
            )

            # Connect to IB Gateway
            await self.ib.connectAsync(
                host=self.host,
                port=self.port,
                clientId=self.client_id,
                timeout=self.timeout,
                readonly=False,  # Need write access for trading
            )

            # Check if connected
            if not self.ib.isConnected():
                logger.error("Failed to connect to IB Gateway")
                return False

            # Set connected flag
            self._connected = True

            # Log connection
            logger.info(
                "Connected to IB Gateway",
                account=self.ib.client.getAccounts(),
                server_version=self.ib.client.serverVersion(),
            )

            # Initialize positions cache
            await self.update_positions()

            return True
        except Exception as e:
            logger.error(f"Error connecting to IB Gateway: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from IB Gateway."""
        if self.ib.isConnected():
            logger.info("Disconnecting from IB Gateway")
            self.ib.disconnect()
            self._connected = False
            logger.info("Disconnected from IB Gateway")

    async def ensure_connected(self) -> bool:
        """Ensure connection to IB Gateway.

        Returns:
            True if connected, False otherwise
        """
        if not self._connected or not self.ib.isConnected():
            return await self.connect()
        return True

    def _get_qqq_option_contract(
        self,
        strike: float,
        right: str,
        expiry: str | None = None,
    ) -> Option:
        """Get QQQ option contract.

        Args:
            strike: Strike price
            right: Option right ("C" for call, "P" for put)
            expiry: Option expiry date (YYYYMMDD format), defaults to today (0-DTE)

        Returns:
            Option contract
        """
        # Use today as expiry if not provided (0-DTE)
        if not expiry:
            today = datetime.datetime.now().strftime("%Y%m%d")
            expiry = today

        # Create cache key
        cache_key = f"QQQ-{expiry}-{strike}-{right}"

        # Check cache
        if cache_key in self._contracts_cache:
            return self._contracts_cache[cache_key]

        # Create contract
        contract = Option(
            symbol="QQQ",
            lastTradeDateOrContractMonth=expiry,
            strike=strike,
            right=right,
            exchange="SMART",
            currency="USD",
        )

        # Cache contract
        self._contracts_cache[cache_key] = contract

        return contract

    async def get_market_price(self, contract: Contract) -> float | None:
        """Get market price for a contract.

        Args:
            contract: Contract to get price for

        Returns:
            Market price or None if not available
        """
        if not await self.ensure_connected():
            logger.error("Not connected to IB Gateway")
            return None

        try:
            # Request market data
            self.ib.reqMktData(contract)

            # Wait for market data
            for _ in range(10):  # Try for 1 second
                await asyncio.sleep(0.1)
                ticker = self.ib.reqTickers(contract)[0]

                # Check if we have a valid price
                if ticker.midpoint() > 0:
                    # Cancel market data subscription
                    self.ib.cancelMktData(contract)
                    return ticker.midpoint()

            # Cancel market data subscription
            self.ib.cancelMktData(contract)

            logger.warning(
                "Failed to get market price",
                contract=contract.symbol,
                strike=contract.strike,
                right=contract.right,
            )
            return None
        except Exception as e:
            logger.error(f"Error getting market price: {e}")
            return None

    async def get_stock_contract(
        self, symbol: str, exchange: str = "SMART", currency: str = "USD"
    ) -> Stock:
        """Create an IBKR Contract object for a stock symbol.

        Args:
            symbol: Stock ticker symbol.
            exchange: The exchange to trade on (default: SMART).
            currency: The currency (default: USD).

        Returns:
            An ib_insync.Stock contract object (cached).

        Note:
            Contract creation is cached with LRU policy (maxsize=128).
            Repeated calls with the same parameters return cached instances.
        """
        logger.debug(
            f"Getting stock contract - symbol: {symbol}, exchange: {exchange}, currency: {currency}"
        )
        try:
            # Use cached contract creation
            contract = _create_stock_contract_cached(
                symbol=symbol, exchange=exchange, currency=currency
            )
            # Optional: Qualify contract details if needed
            # qualified_contracts = await self.ib.qualifyContractsAsync(contract)
            # if not qualified_contracts:
            #     logger.error("Could not qualify contract", contract=contract)
            #     raise ValueError(f"Could not qualify contract for {symbol}")
            # contract = qualified_contracts[0]

            logger.debug(f"Stock contract retrieved: {repr(contract)}")
            return contract
        except Exception:
            logger.error(
                f"Error getting stock contract for symbol: {symbol}",
                exc_info=True,
            )
            raise  # Re-raise the exception after logging

    async def request_historical_data(
        self,
        contract: Contract,
        endDateTime: str = "",
        durationStr: str = "1 D",
        barSizeSetting: str = "1 min",
        whatToShow: str = "TRADES",
        useRTH: bool = True,
    ) -> list[BarData]:
        """Request historical bar data for a contract.

        Args:
            contract: The ib_insync Contract object.
            endDateTime: End date/time in 'YYYYMMDD HH:MM:SS [tz]' format or '' for now.
            durationStr: Duration string (e.g., '1 D', '1 M', '1 Y').
            barSizeSetting: Bar size (e.g., '1 min', '1 hour', '1 day').
            whatToShow: Data type (e.g., 'TRADES', 'MIDPOINT', 'BID', 'ASK').
            useRTH: Use Regular Trading Hours (True) or include data outside RTH (False).

        Returns:
            A list of ib_insync.BarData objects.
        """
        if not await self.ensure_connected():
            logger.error("Not connected to IB Gateway, cannot request historical data")
            return []

        logger.info(
            "Requesting historical data",
            contract=contract.localSymbol or contract.symbol,
            endDateTime=endDateTime,
            durationStr=durationStr,
            barSizeSetting=barSizeSetting,
            whatToShow=whatToShow,
            useRTH=useRTH,
        )
        try:
            bars = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime=endDateTime,
                durationStr=durationStr,
                barSizeSetting=barSizeSetting,
                whatToShow=whatToShow,
                useRTH=useRTH,
                formatDate=1,  # Return as datetime objects
            )
            logger.info(
                f"Received {len(bars)} historical bars",
                contract=contract.localSymbol or contract.symbol,
            )
            return bars
        except Exception:
            logger.error(
                "Error requesting historical data",
                contract=contract.localSymbol or contract.symbol,
                exc_info=True,
            )
            return []  # Return empty list on error

    @dry_run_async("trade", return_value=None)
    async def place_order(self, contract: Contract, order: Order) -> IBTrade | None:
        """Place an order (MKT or TRAIL) for a contract.

        Args:
            contract: The ib_insync Contract object.
            order: The ib_insync Order object (e.g., MarketOrder, TrailOrder).

        Returns:
            An ib_insync.Trade object with order status and details, or None on error.

        Note:
            When dry-run mode is enabled, this method will log the operation
            but not actually place the order. Returns None in dry-run mode.
        """
        if not await self.ensure_connected():
            logger.error("Not connected to IB Gateway, cannot place order")
            return None

        logger.info(
            "Placing order",
            contract=contract.localSymbol or contract.symbol,
            order_type=order.orderType,
            action=order.action,
            quantity=order.totalQuantity,
            limit_price=getattr(order, "lmtPrice", None),
            aux_price=getattr(order, "auxPrice", None),
            trail_stop_price=getattr(order, "trailStopPrice", None),
            trailing_percent=getattr(order, "trailingPercent", None),
        )
        try:
            trade = self.ib.placeOrder(contract, order)
            logger.info(
                "Order placed successfully",
                order_id=trade.order.orderId,
                contract=contract.localSymbol or contract.symbol,
                status=trade.orderStatus.status,
            )
            # Note: This returns the trade object immediately.
            # The status might still be 'Submitted'. Caller needs to monitor the trade object for updates.
            return trade
        except Exception:
            logger.error(
                "Error placing order",
                contract=contract.localSymbol or contract.symbol,
                order_type=order.orderType,
                exc_info=True,
            )
            return None

    async def request_stock_positions(self, symbols: list[str]) -> dict[str, float]:
        """Request current positions for specific stock symbols.

        Args:
            symbols: A list of stock ticker symbols.

        Returns:
            A dictionary mapping symbols to their current position size (float).
            Returns an empty dictionary if not connected or on error.
        """
        if not await self.ensure_connected():
            logger.error("Not connected to IB Gateway, cannot request positions")
            return {}

        logger.info(f"Requesting stock positions for symbols: {symbols}")
        try:
            # Fetch all current positions from IB
            all_positions = await self.ib.reqPositionsAsync()

            # Initialize result with requested symbols mapped to 0.0
            stock_positions = dict.fromkeys(symbols, 0.0)
            # Create a lookup map: lowercase symbol -> original symbol
            symbol_lookup = {s.lower(): s for s in symbols}

            for pos in all_positions:
                contract = pos.contract
                # Check if it's a stock and if its lowercase symbol matches a requested one
                contract_symbol_lower = contract.symbol.lower()
                if contract.secType == "STK" and contract_symbol_lower in symbol_lookup:
                    # Use the original requested symbol casing as the key
                    original_symbol = symbol_lookup[contract_symbol_lower]
                    stock_positions[original_symbol] = pos.position
                    logger.debug(
                        f"Found position for {original_symbol} ({contract.symbol}): {pos.position}"
                    )

            # No need for the second loop, as all requested symbols are already keys

            logger.info(f"Stock positions retrieved: {stock_positions}")
            return stock_positions
        except Exception:
            logger.error("Error requesting stock positions", exc_info=True)
            return {}  # Return empty dict on error

    async def place_vertical_spread(
        self,
        strategy: str,
        qty_per_leg: int,
        strike_long: float,
        strike_short: float,
        max_attempts: int = 10,
        price_increment: float = 0.01,
        min_price: float = 0.70,
        timeout_seconds: int = 5,
    ) -> dict[str, Any]:
        """Place a vertical spread order.

        Args:
            strategy: Strategy type ("Long" for Bull Put, "Short" for Bear Call)
            qty_per_leg: Quantity per leg
            strike_long: Strike price for long leg
            strike_short: Strike price for short leg
            max_attempts: Maximum number of attempts to place the order
            price_increment: Price increment for each attempt
            min_price: Minimum price to accept
            timeout_seconds: Timeout in seconds for each attempt

        Returns:
            Dict with order status and details
        """
        if not await self.ensure_connected():
            logger.error("Not connected to IB Gateway")
            return {
                "status": OrderStatus.REJECTED,
                "error": "Not connected to IB Gateway",
                "trade_id": None,
            }

        try:
            # Determine option rights based on strategy
            if strategy == "Long":  # Bull Put
                long_right = "P"
                short_right = "P"
                # For Bull Put, long strike is lower than short strike
                if strike_long >= strike_short:
                    logger.error(
                        "Invalid strikes for Bull Put",
                        strike_long=strike_long,
                        strike_short=strike_short,
                    )
                    return {
                        "status": OrderStatus.REJECTED,
                        "error": "Invalid strikes for Bull Put",
                        "trade_id": None,
                    }
            elif strategy == "Short":  # Bear Call
                long_right = "C"
                short_right = "C"
                # For Bear Call, long strike is higher than short strike
                if strike_long <= strike_short:
                    logger.error(
                        "Invalid strikes for Bear Call",
                        strike_long=strike_long,
                        strike_short=strike_short,
                    )
                    return {
                        "status": OrderStatus.REJECTED,
                        "error": "Invalid strikes for Bear Call",
                        "trade_id": None,
                    }
            else:
                logger.error(f"Invalid strategy: {strategy}")
                return {
                    "status": OrderStatus.REJECTED,
                    "error": f"Invalid strategy: {strategy}",
                    "trade_id": None,
                }

            # Create contracts
            long_contract = self._get_qqq_option_contract(strike_long, long_right)
            short_contract = self._get_qqq_option_contract(strike_short, short_right)

            # Get market prices
            long_price = await self.get_market_price(long_contract)
            short_price = await self.get_market_price(short_contract)

            if long_price is None or short_price is None:
                logger.error(
                    "Failed to get market prices",
                    long_price=long_price,
                    short_price=short_price,
                )
                return {
                    "status": OrderStatus.REJECTED,
                    "error": "Failed to get market prices",
                    "trade_id": None,
                }

            # Calculate mid price for the spread
            # For Bull Put: short_price - long_price (negative value)
            # For Bear Call: short_price - long_price (negative value)
            mid_price = short_price - long_price

            logger.info(
                "Calculated mid price",
                strategy=strategy,
                long_price=long_price,
                short_price=short_price,
                mid_price=mid_price,
            )

            # Check if mid price is too low (absolute value)
            if abs(mid_price) < min_price:
                logger.error(
                    "Mid price too low",
                    mid_price=mid_price,
                    min_price=min_price,
                )
                return {
                    "status": OrderStatus.REJECTED,
                    "error": "Mid price too low",
                    "trade_id": None,
                    "mid_price": mid_price,
                }

            # Create combo contract for vertical spread
            bag = ib_insync.Bag("QQQ", "SMART", "USD")

            # Add legs to the bag
            bag.addLeg(long_contract, 1)
            bag.addLeg(short_contract, -1)

            # Initial limit price
            limit_price = mid_price

            # Try to place the order with decreasing price
            for attempt in range(max_attempts):
                logger.info(
                    f"Attempt {attempt + 1}/{max_attempts} to place order",
                    limit_price=limit_price,
                )

                # Create order
                order = ib_insync.LimitOrder(
                    action="BUY",
                    totalQuantity=qty_per_leg,
                    lmtPrice=limit_price,
                    transmit=True,
                )

                # Place order
                trade = self.ib.placeOrder(bag, order)

                # Wait for order to be filled or timeout
                start_time = time.time()
                while time.time() - start_time < timeout_seconds:
                    await asyncio.sleep(0.1)
                    self.ib.waitOnUpdate(timeout=0.1)

                    # Check order status
                    if trade.orderStatus.status in ["Filled", "Cancelled", "Inactive"]:
                        break

                # Check if order was filled
                if trade.orderStatus.status == "Filled":
                    logger.info(
                        "Order filled",
                        order_id=trade.order.orderId,
                        fill_price=trade.orderStatus.avgFillPrice,
                    )
                    return {
                        "status": OrderStatus.FILLED,
                        "trade_id": str(trade.order.orderId),
                        "fill_price": trade.orderStatus.avgFillPrice,
                        "fill_time": datetime.datetime.now().isoformat(),
                    }

                # Check if order was partially filled
                if trade.orderStatus.status == "Submitted" and trade.orderStatus.filled > 0:
                    logger.info(
                        "Order partially filled",
                        order_id=trade.order.orderId,
                        filled=trade.orderStatus.filled,
                        remaining=trade.orderStatus.remaining,
                    )
                    return {
                        "status": OrderStatus.PARTIAL,
                        "trade_id": str(trade.order.orderId),
                        "filled": trade.orderStatus.filled,
                        "remaining": trade.orderStatus.remaining,
                        "fill_price": trade.orderStatus.avgFillPrice,
                        "fill_time": datetime.datetime.now().isoformat(),
                    }

                # Cancel the order if not filled
                if trade.orderStatus.status != "Cancelled":
                    self.ib.cancelOrder(order)

                # Calculate new limit price
                limit_price += price_increment  # Decrease the negative value

                # Check if new limit price is too high
                if abs(limit_price) < min_price:
                    logger.warning(
                        "Limit price too high",
                        limit_price=limit_price,
                        min_price=min_price,
                    )
                    return {
                        "status": OrderStatus.REJECTED,
                        "error": "Limit price too high",
                        "trade_id": None,
                    }

            # If we get here, all attempts failed
            logger.error("Failed to place order after all attempts")
            return {
                "status": OrderStatus.REJECTED,
                "error": "Failed to place order after all attempts",
                "trade_id": None,
            }
        except Exception as e:
            logger.error(f"Error placing vertical spread: {e}")
            return {
                "status": OrderStatus.REJECTED,
                "error": str(e),
                "trade_id": None,
            }

    async def update_positions(self) -> bool:
        """Update positions cache.

        Returns:
            True if successful, False otherwise
        """
        if not await self.ensure_connected():
            logger.error("Not connected to IB Gateway")
            return False

        try:
            # Get positions
            positions = self.ib.positions()

            # Update cache
            self._positions_cache = {}
            for position in positions:
                contract = position.contract
                if contract.secType == "OPT" and contract.symbol == "QQQ":
                    key = f"{contract.strike}-{contract.right}"
                    self._positions_cache[key] = position.position

            # Update timestamp
            self._last_positions_update = time.time()

            logger.debug(
                "Positions updated",
                positions=self._positions_cache,
            )

            return True
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
            return False

    async def get_positions(self, force_update: bool = False) -> dict[str, int]:
        """Get current positions.

        Args:
            force_update: Force update of positions cache

        Returns:
            Dict mapping contract keys to position sizes
        """
        # Update positions if needed
        if force_update or time.time() - self._last_positions_update > 60:
            await self.update_positions()

        return self._positions_cache

    async def check_assignment(self) -> tuple[AssignmentState, int, int]:
        """Check for assignment by comparing short and long positions.

        Returns:
            Tuple of (assignment state, short qty, long qty)
        """
        # Update positions
        await self.update_positions()

        # Count short and long positions
        short_qty = 0
        long_qty = 0

        for key, qty in self._positions_cache.items():
            if qty > 0:  # Long position
                long_qty += qty
            elif qty < 0:  # Short position
                short_qty += abs(qty)

        # Check for assignment
        if short_qty < long_qty:
            return AssignmentState.ASSIGNED, short_qty, long_qty

        return AssignmentState.NONE, short_qty, long_qty

    async def exercise_options(
        self,
        strike: float,
        right: str,
        quantity: int,
    ) -> dict[str, Any]:
        """Exercise options to compensate for assignment.

        Args:
            strike: Strike price of the long option to exercise
            right: Option right ("C" for call, "P" for put)
            quantity: Quantity to exercise

        Returns:
            Dict with exercise status and details
        """
        if not await self.ensure_connected():
            logger.error("Not connected to IB Gateway")
            return {
                "status": "FAILED",
                "error": "Not connected to IB Gateway",
            }

        try:
            # Get contract
            contract = self._get_qqq_option_contract(strike, right)

            # Exercise option
            self.ib.exerciseOptions(contract, quantity, 1, self.ib.wrapper.accounts[0], 0)

            logger.info(
                "Options exercised",
                strike=strike,
                right=right,
                quantity=quantity,
            )

            return {
                "status": "SUCCESS",
                "strike": strike,
                "right": right,
                "quantity": quantity,
            }
        except Exception as e:
            logger.error(f"Error exercising options: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
            }

    async def close_all_positions(self) -> dict[str, Any]:
        """Close all positions with market orders.

        Returns:
            Dict with close status and details
        """
        if not await self.ensure_connected():
            logger.error("Not connected to IB Gateway")
            return {
                "status": "FAILED",
                "error": "Not connected to IB Gateway",
            }

        try:
            # Update positions
            await self.update_positions()

            # Check if we have any positions
            if not self._positions_cache:
                logger.info("No positions to close")
                return {
                    "status": "SUCCESS",
                    "message": "No positions to close",
                }

            # Close each position
            results = []
            for key, qty in self._positions_cache.items():
                if qty == 0:
                    continue

                # Parse key to get strike and right
                strike, right = key.split("-")
                strike = float(strike)

                # Get contract
                contract = self._get_qqq_option_contract(strike, right)

                # Create market order (opposite of position)
                action = "SELL" if qty > 0 else "BUY"
                order = ib_insync.MarketOrder(
                    action=action,
                    totalQuantity=abs(qty),
                    transmit=True,
                )

                # Place order
                trade = self.ib.placeOrder(contract, order)

                # Wait for order to be filled
                for _ in range(10):  # Wait up to 1 second
                    await asyncio.sleep(0.1)
                    self.ib.waitOnUpdate(timeout=0.1)

                    # Check order status
                    if trade.orderStatus.status in ["Filled", "Cancelled", "Inactive"]:
                        break

                # Record result
                results.append(
                    {
                        "contract": key,
                        "qty": qty,
                        "action": action,
                        "status": trade.orderStatus.status,
                        "filled": trade.orderStatus.filled,
                    }
                )

            logger.info(
                "Closed all positions",
                results=results,
            )

            return {
                "status": "SUCCESS",
                "results": results,
            }
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
            }

    async def get_account_summary(self) -> dict[str, Any]:
        """Get account summary.

        Returns:
            Dict with account summary
        """
        if not await self.ensure_connected():
            logger.error("Not connected to IB Gateway")
            return {}

        try:
            # Request account summary
            account = self.ib.wrapper.accounts[0]
            summary = self.ib.accountSummary(account)

            # Convert to dict
            result = {}
            for item in summary:
                result[item.tag] = item.value

            return result
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return {}

    async def check_margin_for_trade(
        self,
        strategy: str,
        qty_per_leg: int,
        strike_long: float,
        strike_short: float,
    ) -> tuple[bool, str | None]:
        """Check if account has enough margin for a trade.

        Args:
            strategy: Strategy type ("Long" for Bull Put, "Short" for Bear Call)
            qty_per_leg: Quantity per leg
            strike_long: Strike price for long leg
            strike_short: Strike price for short leg

        Returns:
            Tuple of (has_margin, error_message)
        """
        if not await self.ensure_connected():
            logger.error("Not connected to IB Gateway")
            return False, "Not connected to IB Gateway"

        try:
            # Get account summary
            summary = await self.get_account_summary()

            # Check available funds
            available_funds = float(summary.get("AvailableFunds", 0))

            # Calculate margin requirement (simplified)
            if strategy == "Long":  # Bull Put
                # For Bull Put, margin is approximately (short_strike - long_strike) * 100 * qty
                margin_required = (strike_short - strike_long) * 100 * qty_per_leg
            else:  # Bear Call
                # For Bear Call, margin is approximately (strike_long - strike_short) * 100 * qty
                margin_required = (strike_long - strike_short) * 100 * qty_per_leg

            # Add buffer (20%)
            margin_required *= 1.2

            logger.info(
                "Margin check",
                available_funds=available_funds,
                margin_required=margin_required,
                strategy=strategy,
            )

            # Check if we have enough margin
            if available_funds < margin_required:
                return (
                    False,
                    f"Insufficient margin: {available_funds} < {margin_required}",
                )

            return True, None
        except Exception as e:
            logger.error(f"Error checking margin: {e}")
            return False, str(e)

    async def get_pnl(self) -> dict[str, float]:
        """Get current P&L.

        Returns:
            Dict with P&L information
        """
        if not await self.ensure_connected():
            logger.error("Not connected to IB Gateway")
            return {}

        try:
            # Request PnL
            account = self.ib.wrapper.accounts[0]
            self.ib.reqPnL(account, "")

            # Wait for PnL data
            await asyncio.sleep(1)

            # Get PnL data
            pnl_data = self.ib.pnl()

            # Cancel PnL subscription
            self.ib.cancelPnL(account, "")

            if not pnl_data:
                logger.warning("No PnL data available")
                return {}

            # Extract PnL information
            result = {
                "daily_pnl": pnl_data.dailyPnL,
                "unrealized_pnl": pnl_data.unrealizedPnL,
                "realized_pnl": pnl_data.realizedPnL,
            }

            return result
        except Exception as e:
            logger.error(f"Error getting PnL: {e}")
            return {}

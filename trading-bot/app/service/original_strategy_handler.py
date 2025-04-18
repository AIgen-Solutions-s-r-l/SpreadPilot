"""Handler for the Original EMA Crossover Strategy."""

import asyncio
import datetime
from typing import TYPE_CHECKING, Dict, Any, List

import pandas as pd
from ib_insync import Order, Contract, BarData

from spreadpilot_core.logging import get_logger
from spreadpilot_core.ibkr.client import IBKRClient
from spreadpilot_core.models.alert import Alert

if TYPE_CHECKING:
    from .base import TradingService

logger = get_logger(__name__)


class OriginalStrategyHandler:
    """
    Implements the logic for the original EMA crossover trading strategy.
    Manages its own IBKR connection and state.
    """

    def __init__(self, service: "TradingService", config: Dict[str, Any]):
        """
        Initialize the OriginalStrategyHandler.

        Args:
            service: The main TradingService instance.
            config: Strategy-specific configuration dictionary.
        """
        self.service = service
        self.config = config
        self.ibkr_client: IBKRClient | None = None
        self.positions: Dict[str, float] = {}  # Symbol -> Quantity
        self.historical_data: Dict[str, pd.DataFrame] = {} # Symbol -> DataFrame
        self.active_orders: Dict[str, List[Order]] = {} # Symbol -> List of active orders
        self._initialized = False
        logger.info("OriginalStrategyHandler initialized.")

    async def initialize(self):
        """
        Initialize the handler: connect to IBKR, fetch initial data.
        """
        if not self.config.get("enabled", False):
            logger.info("Original EMA Strategy is disabled in config.")
            return

        if self._initialized:
            logger.warning("OriginalStrategyHandler already initialized.")
            return

        logger.info("Initializing OriginalStrategyHandler...")
        try:
            # TODO: Fetch dedicated IBKR credentials using self.config["ibkr_secret_ref"]
            # For now, using the main service credentials for testing setup
            ib_settings = {
                "host": self.service.settings.ib_gateway_host,
                "port": self.service.settings.ib_gateway_port,
                "client_id": self.service.settings.ib_client_id + 10, # Use a different client ID
                "account": None, # Let ib_insync determine account or fetch from secrets
                "trading_mode": self.service.settings.ib_trading_mode,
            }
            self.ibkr_client = IBKRClient(**ib_settings)
            await self.ibkr_client.connect()
            logger.info("IBKR client connected for Original Strategy.")

            # Fetch initial positions for configured symbols
            await self._fetch_initial_positions()

            # Fetch initial historical data
            await self._fetch_initial_historical_data()

            self._initialized = True
            logger.info("OriginalStrategyHandler initialization complete.")

        except Exception as e:
            logger.error(f"Error initializing OriginalStrategyHandler: {e}", exc_info=True)
            self._initialized = False
            # Optionally re-raise or handle specific connection errors

    async def _fetch_initial_positions(self):
        """Fetch initial portfolio positions for the configured symbols."""
        if not self.ibkr_client or not self.ibkr_client.is_connected():
            logger.warning("IBKR client not connected, cannot fetch initial positions.")
            return

        logger.info("Fetching initial positions...")
        try:
            all_positions = await self.ibkr_client.get_positions()
            self.positions = {
                pos.contract.symbol: pos.position
                for pos in all_positions
                if pos.contract.symbol in self.config["symbols"]
            }
            logger.info(f"Initial positions fetched: {self.positions}")
        except Exception as e:
            logger.error(f"Error fetching initial positions: {e}", exc_info=True)
            self.positions = {}


    async def _fetch_initial_historical_data(self):
        """Fetch initial historical data needed for EMA calculation."""
        if not self.ibkr_client or not self.ibkr_client.is_connected():
            logger.warning("IBKR client not connected, cannot fetch historical data.")
            return

        logger.info("Fetching initial historical data...")
        # Determine required lookback period (at least slow_ema + buffer)
        required_bars = self.config["slow_ema"] + 5 # Add a small buffer
        duration_str = f"{required_bars * 2} D" # Request more days to be safe

        for symbol in self.config["symbols"]:
            try:
                contract = await self.ibkr_client.get_contract_details(symbol, sec_type='STK', exchange='SMART')
                if not contract:
                    logger.warning(f"Could not find contract details for {symbol}")
                    continue

                bars = await self.ibkr_client.get_historical_data(
                    contract=contract[0].contract, # Use the first result
                    duration_str=duration_str,
                    bar_size_setting=self.config["bar_period"],
                    what_to_show="TRADES",
                    use_rth=True
                )
                if bars:
                    df = pd.DataFrame([{'time': b.date, 'open': b.open, 'high': b.high, 'low': b.low, 'close': b.close, 'volume': b.volume} for b in bars])
                    df['time'] = pd.to_datetime(df['time'])
                    df.set_index('time', inplace=True)
                    self.historical_data[symbol] = df
                    logger.info(f"Fetched {len(df)} historical bars for {symbol}")
                else:
                    logger.warning(f"No historical data returned for {symbol}")
                    self.historical_data[symbol] = pd.DataFrame() # Empty DataFrame

            except Exception as e:
                logger.error(f"Error fetching historical data for {symbol}: {e}", exc_info=True)
                self.historical_data[symbol] = pd.DataFrame() # Ensure key exists

    async def run(self, shutdown_event: asyncio.Event):
        """
        Main execution loop for the strategy handler.
        Waits for bar closes, fetches data, and processes bars during trading hours.
        """
        if not self._initialized:
            logger.warning("OriginalStrategyHandler not initialized, cannot run.")
            return

        logger.info("Starting OriginalStrategyHandler run loop...")
        try:
            while not shutdown_event.is_set():
                # 1. Check if within trading hours
                # TODO: Implement trading hours check using config times

                # 2. Wait for the next bar close
                # TODO: Implement logic to wait for the next '5 mins' bar close

                # 3. Fetch latest bar data for each symbol
                # TODO: Fetch latest bar data

                # 4. Process the latest bar for each symbol
                # for symbol in self.config["symbols"]:
                #     if symbol in latest_bars:
                #          await self._process_bar(symbol, latest_bars[symbol])

                # 5. Check for End-of-Day processing
                # TODO: Implement EOD check and call _process_eod if needed

                # Add a small sleep to prevent tight looping if logic is fast
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("OriginalStrategyHandler run loop cancelled.")
        except Exception as e:
            logger.error(f"Error in OriginalStrategyHandler run loop: {e}", exc_info=True)
        finally:
            logger.info("OriginalStrategyHandler run loop finished.")
            await self.shutdown()

    async def _process_bar(self, symbol: str, bar: BarData):
        """
        Process a new bar for a given symbol. Calculates EMAs, checks for
        crossovers, manages positions, and places orders.

        Args:
            symbol: The stock symbol.
            bar: The latest BarData object.
        """
        logger.debug(f"Processing bar for {symbol}: {bar}")
        if symbol not in self.historical_data:
            logger.warning(f"No historical data found for {symbol}, cannot process bar.")
            return

        # 1. Append new bar to historical data
        new_row = pd.DataFrame([{'time': pd.to_datetime(bar.date), 'open': bar.open, 'high': bar.high, 'low': bar.low, 'close': bar.close, 'volume': bar.volume}])
        new_row.set_index('time', inplace=True)
        self.historical_data[symbol] = pd.concat([self.historical_data[symbol], new_row])

        # Ensure enough data for EMA calculation
        if len(self.historical_data[symbol]) < self.config["slow_ema"]:
            logger.debug(f"Not enough historical data for {symbol} to calculate EMAs ({len(self.historical_data[symbol])}/{self.config['slow_ema']}).")
            return

        # 2. Calculate EMAs
        try:
            close_prices = self.historical_data[symbol]['close']
            fast_ema = self._calculate_ema(close_prices, self.config["fast_ema"])
            slow_ema = self._calculate_ema(close_prices, self.config["slow_ema"])
        except Exception as e:
            logger.error(f"Error calculating EMAs for {symbol}: {e}", exc_info=True)
            return

        # 3. Check for Crossovers (need at least 2 points for comparison)
        if len(fast_ema) < 2 or len(slow_ema) < 2:
            logger.debug(f"Not enough EMA points to check for crossover for {symbol}.")
            return

        is_bullish_crossover = self._check_bullish_crossover(fast_ema, slow_ema)
        is_bearish_crossover = self._check_bearish_crossover(fast_ema, slow_ema)

        current_position = self.positions.get(symbol, 0)
        current_price = bar.close

        # 4. Strategy Logic & Order Placement
        try:
            contract = await self.ibkr_client.get_contract_details(symbol, sec_type='STK', exchange='SMART')
            if not contract:
                logger.warning(f"Could not find contract for {symbol} during processing.")
                return
            contract = contract[0].contract

            if is_bullish_crossover and current_position <= 0: # Enter long or close short
                # Close short position if exists
                if current_position < 0:
                    logger.info(f"Bullish Crossover: Closing short position for {symbol}")
                    close_order = self._create_market_order('BUY', abs(current_position))
                    trade = await self.ibkr_client.place_order(contract, close_order)
                    logger.info(f"Placed order to close short {symbol}: {trade}")
                    await self._send_alert(symbol, 'BUY', abs(current_position), current_price, 'MKT', 'Close Short (Bullish Crossover)')
                    self.positions[symbol] = 0 # Assume filled for now, update on fill event later

                # Enter long position
                logger.info(f"Bullish Crossover: Entering long position for {symbol}")
                quantity = self._calculate_position_size(current_price)
                entry_order = self._create_market_order('BUY', quantity)
                trade = await self.ibkr_client.place_order(contract, entry_order)
                logger.info(f"Placed order to enter long {symbol}: {trade}")
                await self._send_alert(symbol, 'BUY', quantity, current_price, 'MKT', 'Enter Long (Bullish Crossover)')
                self.positions[symbol] = quantity # Assume filled

                # Place trailing stop loss
                if self.config["trailing_stop_pct"] > 0:
                    stop_order = self._create_trailing_stop_order('SELL', quantity, self.config["trailing_stop_pct"])
                    stop_trade = await self.ibkr_client.place_order(contract, stop_order)
                    logger.info(f"Placed trailing stop loss for long {symbol}: {stop_trade}")
                    # TODO: Track this stop order

            elif is_bearish_crossover and current_position >= 0: # Enter short or close long
                 # Close long position if exists
                if current_position > 0:
                    logger.info(f"Bearish Crossover: Closing long position for {symbol}")
                    close_order = self._create_market_order('SELL', abs(current_position))
                    trade = await self.ibkr_client.place_order(contract, close_order)
                    logger.info(f"Placed order to close long {symbol}: {trade}")
                    await self._send_alert(symbol, 'SELL', abs(current_position), current_price, 'MKT', 'Close Long (Bearish Crossover)')
                    self.positions[symbol] = 0 # Assume filled

                # Enter short position
                logger.info(f"Bearish Crossover: Entering short position for {symbol}")
                quantity = self._calculate_position_size(current_price)
                entry_order = self._create_market_order('SELL', quantity)
                trade = await self.ibkr_client.place_order(contract, entry_order)
                logger.info(f"Placed order to enter short {symbol}: {trade}")
                await self._send_alert(symbol, 'SELL', quantity, current_price, 'MKT', 'Enter Short (Bearish Crossover)')
                self.positions[symbol] = -quantity # Assume filled

                # Place trailing stop loss (buy back)
                if self.config["trailing_stop_pct"] > 0:
                    stop_order = self._create_trailing_stop_order('BUY', quantity, self.config["trailing_stop_pct"])
                    stop_trade = await self.ibkr_client.place_order(contract, stop_order)
                    logger.info(f"Placed trailing stop loss for short {symbol}: {stop_trade}")
                    # TODO: Track this stop order

        except Exception as e:
            logger.error(f"Error processing bar and placing orders for {symbol}: {e}", exc_info=True)


    async def _process_eod(self):
        """
        Handle End-of-Day logic, such as closing open positions if configured.
        """
        if not self.config.get("close_at_eod", False):
            logger.info("Close at EOD is disabled.")
            return

        logger.info("Processing End-of-Day logic...")
        if not self.ibkr_client or not self.ibkr_client.is_connected():
            logger.warning("IBKR client not connected, cannot process EOD.")
            return

        for symbol, position in list(self.positions.items()): # Iterate over a copy
            if position != 0:
                logger.info(f"EOD: Closing position for {symbol} ({position})")
                try:
                    contract = await self.ibkr_client.get_contract_details(symbol, sec_type='STK', exchange='SMART')
                    if not contract:
                        logger.warning(f"Could not find contract for {symbol} during EOD.")
                        continue
                    contract = contract[0].contract

                    action = 'SELL' if position > 0 else 'BUY'
                    quantity = abs(position)
                    close_order = self._create_market_order(action, quantity)
                    trade = await self.ibkr_client.place_order(contract, close_order)
                    logger.info(f"Placed EOD closing order for {symbol}: {trade}")
                    await self._send_alert(symbol, action, quantity, None, 'MKT', 'EOD Close') # Price unknown for MKT EOD
                    self.positions[symbol] = 0 # Assume closed

                except Exception as e:
                    logger.error(f"Error closing position for {symbol} at EOD: {e}", exc_info=True)

        logger.info("End-of-Day processing complete.")


    async def shutdown(self):
        """
        Cleanly disconnect the dedicated IBKR client.
        """
        logger.info("Shutting down OriginalStrategyHandler...")
        if self.ibkr_client and self.ibkr_client.is_connected():
            await self.ibkr_client.disconnect()
            logger.info("IBKR client for Original Strategy disconnected.")
        self._initialized = False

    # --- Helper Methods ---

    def _calculate_ema(self, series: pd.Series, span: int) -> pd.Series:
        """Calculates the Exponential Moving Average."""
        return series.ewm(span=span, adjust=False).mean()

    def _check_bullish_crossover(self, fast_ema: pd.Series, slow_ema: pd.Series) -> bool:
        """Checks if the fast EMA crossed above the slow EMA."""
        if len(fast_ema) < 2 or len(slow_ema) < 2:
            return False
        current_fast = fast_ema.iloc[-1]
        current_slow = slow_ema.iloc[-1]
        prev_fast = fast_ema.iloc[-2]
        prev_slow = slow_ema.iloc[-2]
        return prev_fast < prev_slow and current_fast >= current_slow

    def _check_bearish_crossover(self, fast_ema: pd.Series, slow_ema: pd.Series) -> bool:
        """Checks if the fast EMA crossed below the slow EMA."""
        if len(fast_ema) < 2 or len(slow_ema) < 2:
            return False
        current_fast = fast_ema.iloc[-1]
        current_slow = slow_ema.iloc[-1]
        prev_fast = fast_ema.iloc[-2]
        prev_slow = slow_ema.iloc[-2]
        return prev_fast > prev_slow and current_fast <= current_slow

    def _create_market_order(self, action: str, quantity: float) -> Order:
        """Creates an IBKR Market Order."""
        return Order(orderType='MKT', action=action, totalQuantity=abs(quantity))

    def _create_trailing_stop_order(self, action: str, quantity: float, trailing_percent: float) -> Order:
        """Creates an IBKR Trailing Stop Order."""
        return Order(
            orderType='TRAIL',
            action=action,
            totalQuantity=abs(quantity),
            trailingPercent=trailing_percent,
            tif='GTC' # Good Till Cancelled for stops usually
        )

    def _calculate_position_size(self, price: float) -> int:
        """Calculates position size based on dollar amount and price."""
        if price <= 0:
            return 0
        dollar_amount = self.config.get("dollar_amount", 1000) # Default to 1000 if not set
        quantity = int(dollar_amount / price)
        return max(1, quantity) # Ensure at least 1 share

    async def _send_alert(self, symbol: str, action: str, quantity: float, price: float | None, order_type: str, signal_type: str):
        """Sends an alert using the main service's alert manager."""
        try:
            alert = Alert(
                symbol=symbol,
                action=action,
                quantity=quantity,
                price=price, # Can be None for market orders filled later
                order_type=order_type,
                strategy="ORIGINAL_EMA",
                signal_type=signal_type,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            await self.service.alert_manager.create_alert(alert)
            logger.info(f"Sent alert: {signal_type} {action} {quantity} {symbol}")
        except Exception as e:
            logger.error(f"Failed to send alert for {symbol}: {e}", exc_info=True)
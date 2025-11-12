"""Internal signal generator for QQQ vertical spreads.

This module generates trading signals based on:
- Time-based triggers (daily at 9:27 AM ET)
- Market trend analysis (SMA crossovers, momentum)
- Delta-based strike selection using IBKR option chains
- Historical data analysis from MongoDB

IMPORTANT: This module uses ib_insync library which has blocking I/O operations.
All blocking IBKR calls (reqMktData, reqHistoricalData, qualifyContracts, etc.)
should be wrapped with asyncio.to_thread() to prevent blocking the event loop.
See: https://ib-insync.readthedocs.io/recipes.html#asyncio-integration
"""

import asyncio
from datetime import datetime, timedelta

from ib_insync import IB, Option, Stock
from spreadpilot_core.logging import get_logger
from spreadpilot_core.utils.time import get_ny_time

logger = get_logger(__name__)


class QQQSignalGenerator:
    """
    Generates trading signals for QQQ vertical spreads based on market analysis.
    """

    def __init__(
        self,
        ib_client: IB,
        short_leg_delta: float = 0.30,
        long_leg_delta: float = 0.15,
        sma_short_period: int = 20,
        sma_long_period: int = 50,
        qty_per_leg: int = 1,
    ):
        """
        Initialize the signal generator.

        Args:
            ib_client: Interactive Brokers client for market data
            short_leg_delta: Target delta for short leg (default 0.30)
            long_leg_delta: Target delta for long leg (default 0.15)
            sma_short_period: Short-term SMA period in days (default 20)
            sma_long_period: Long-term SMA period in days (default 50)
            qty_per_leg: Quantity of contracts per leg (default 1)
        """
        self.ib = ib_client
        self.short_leg_delta = abs(short_leg_delta)
        self.long_leg_delta = abs(long_leg_delta)
        self.sma_short_period = sma_short_period
        self.sma_long_period = sma_long_period
        self.qty_per_leg = qty_per_leg

        # Cache for historical data
        self._price_cache: list[float] = []
        self._cache_updated: datetime | None = None

        logger.info(
            "Initialized QQQ signal generator",
            short_leg_delta=short_leg_delta,
            long_leg_delta=long_leg_delta,
            sma_short=sma_short_period,
            sma_long=sma_long_period,
        )

    async def generate_signal(self) -> dict | None:
        """
        Generate a trading signal based on current market conditions.

        Returns:
            Signal dictionary with structure:
            {
                "date": str,           # Current date "YYYY-MM-DD"
                "ticker": str,         # Always "QQQ"
                "strategy": str,       # "Long" (Bull Put) or "Short" (Bear Call)
                "qty_per_leg": int,    # Quantity per leg
                "strike_long": float,  # Strike for long leg
                "strike_short": float, # Strike for short leg
            }
            Returns None if unable to generate signal or market conditions unclear
        """
        try:
            ny_time = get_ny_time()
            current_date = ny_time.strftime("%Y-%m-%d")

            logger.info("Generating signal for QQQ vertical spread", date=current_date)

            # Step 1: Get current QQQ price
            current_price = await self._get_current_price()
            if not current_price:
                logger.error("Unable to fetch current QQQ price")
                return None

            logger.info(f"Current QQQ price: ${current_price:.2f}")

            # Step 2: Determine strategy based on market trend
            strategy = await self._determine_strategy(current_price)
            if not strategy:
                logger.warning("Unable to determine strategy from market conditions")
                return None

            logger.info(f"Selected strategy: {strategy}")

            # Step 3: Get option expiration (nearest Friday)
            expiration = self._get_next_expiration(ny_time)
            logger.info(f"Target expiration: {expiration}")

            # Step 4: Select strikes based on delta
            strikes = await self._select_strikes_by_delta(current_price, expiration, strategy)

            if not strikes:
                logger.error("Unable to select strikes based on delta criteria")
                return None

            strike_long, strike_short = strikes
            logger.info(f"Selected strikes: Long={strike_long}, Short={strike_short}")

            # Step 5: Build signal
            signal = {
                "date": current_date,
                "ticker": "QQQ",
                "strategy": strategy,
                "qty_per_leg": self.qty_per_leg,
                "strike_long": strike_long,
                "strike_short": strike_short,
            }

            logger.info("Generated signal successfully", signal=signal)
            return signal

        except Exception as e:
            logger.error(f"Error generating signal: {e}", exc_info=True)
            return None

    async def _get_current_price(self) -> float | None:
        """
        Get current QQQ market price from IBKR.

        Returns:
            Current price or None if unavailable
        """
        try:
            # Create QQQ stock contract
            qqq = Stock("QQQ", "SMART", "USD")

            # Request market data
            self.ib.qualifyContracts(qqq)
            ticker = self.ib.reqMktData(qqq, "", False, False)

            # Wait for data with timeout
            for _ in range(50):  # 5 second timeout
                await asyncio.sleep(0.1)
                if ticker.last and ticker.last > 0:
                    price = ticker.last
                    self.ib.cancelMktData(qqq)
                    return float(price)

            # Fallback to delayed data
            if ticker.close and ticker.close > 0:
                price = ticker.close
                self.ib.cancelMktData(qqq)
                return float(price)

            self.ib.cancelMktData(qqq)
            logger.error("No valid market data received for QQQ")
            return None

        except Exception as e:
            logger.error(f"Error fetching QQQ price: {e}", exc_info=True)
            return None

    async def _determine_strategy(self, current_price: float) -> str | None:
        """
        Determine strategy (Long/Short) based on market trend analysis.

        Uses Simple Moving Average crossover:
        - If short-term SMA > long-term SMA: Bullish → "Long" (Bull Put Spread)
        - If short-term SMA < long-term SMA: Bearish → "Short" (Bear Call Spread)

        Args:
            current_price: Current QQQ price

        Returns:
            "Long" for bullish, "Short" for bearish, None if unclear
        """
        try:
            # Update price history if needed
            await self._update_price_history()

            if len(self._price_cache) < self.sma_long_period:
                logger.warning(
                    f"Insufficient historical data: {len(self._price_cache)} days, "
                    f"need {self.sma_long_period}"
                )
                # Fallback: use simple momentum
                return await self._fallback_strategy(current_price)

            # Calculate SMAs
            prices = self._price_cache[-self.sma_long_period :]
            sma_short = sum(prices[-self.sma_short_period :]) / self.sma_short_period
            sma_long = sum(prices) / self.sma_long_period

            logger.info(
                f"Technical analysis: SMA{self.sma_short_period}={sma_short:.2f}, "
                f"SMA{self.sma_long_period}={sma_long:.2f}"
            )

            # Determine trend
            if sma_short > sma_long:
                logger.info("Bullish trend detected (SMA crossover)")
                return "Long"  # Bull Put Spread
            elif sma_short < sma_long:
                logger.info("Bearish trend detected (SMA crossover)")
                return "Short"  # Bear Call Spread
            else:
                logger.info("Neutral trend, no clear signal")
                return None

        except Exception as e:
            logger.error(f"Error determining strategy: {e}", exc_info=True)
            return None

    async def _fallback_strategy(self, current_price: float) -> str | None:
        """
        Fallback strategy when insufficient historical data.
        Uses simple short-term momentum.

        Args:
            current_price: Current QQQ price

        Returns:
            "Long" or "Short" based on recent price action
        """
        try:
            if len(self._price_cache) < 5:
                logger.warning("Insufficient data even for fallback strategy")
                return "Long"  # Default to bullish bias

            # Compare current price to 5-day average
            recent_avg = sum(self._price_cache[-5:]) / 5

            if current_price > recent_avg * 1.01:  # 1% above average
                logger.info("Short-term bullish momentum detected")
                return "Long"
            elif current_price < recent_avg * 0.99:  # 1% below average
                logger.info("Short-term bearish momentum detected")
                return "Short"
            else:
                logger.info("Neutral momentum, defaulting to Long")
                return "Long"

        except Exception as e:
            logger.error(f"Error in fallback strategy: {e}", exc_info=True)
            return "Long"  # Conservative default

    async def _update_price_history(self) -> None:
        """
        Update cached price history from IBKR historical data.
        Only updates once per day to avoid excessive API calls.
        """
        try:
            # Check if cache needs updating
            now = datetime.utcnow()
            if self._cache_updated and (now - self._cache_updated).total_seconds() < 3600:
                logger.debug("Price cache is fresh, skipping update")
                return

            logger.info("Updating QQQ price history from IBKR")

            # Create QQQ contract
            qqq = Stock("QQQ", "SMART", "USD")
            self.ib.qualifyContracts(qqq)

            # Request historical data (60 days to ensure enough for SMA)
            end_datetime = ""
            duration = f"{self.sma_long_period + 10} D"
            bar_size = "1 day"

            bars = self.ib.reqHistoricalData(
                qqq,
                endDateTime=end_datetime,
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1,
            )

            if bars:
                self._price_cache = [bar.close for bar in bars]
                self._cache_updated = now
                logger.info(f"Updated price cache with {len(self._price_cache)} days of data")
            else:
                logger.warning("No historical data received from IBKR")

        except Exception as e:
            logger.error(f"Error updating price history: {e}", exc_info=True)

    def _get_next_expiration(self, current_time: datetime) -> str:
        """
        Get the next Friday expiration date in YYYYMMDD format.

        Args:
            current_time: Current datetime in NY timezone

        Returns:
            Expiration date string in YYYYMMDD format
        """
        # Get days until Friday (4 = Friday in weekday())
        days_ahead = 4 - current_time.weekday()

        # If today is Friday and before market close, use today
        if days_ahead == 0 and current_time.hour < 16:
            expiration = current_time
        # Otherwise, get next Friday
        elif days_ahead < 0:
            days_ahead += 7
            expiration = current_time + timedelta(days=days_ahead)
        else:
            expiration = current_time + timedelta(days=days_ahead)

        return expiration.strftime("%Y%m%d")

    async def _select_strikes_by_delta(
        self, current_price: float, expiration: str, strategy: str
    ) -> tuple[float, float] | None:
        """
        Select strike prices based on target delta values.

        Args:
            current_price: Current QQQ price
            expiration: Option expiration in YYYYMMDD format
            strategy: "Long" (Bull Put) or "Short" (Bear Call)

        Returns:
            Tuple of (strike_long, strike_short) or None if unable to select
        """
        try:
            # Determine option type based on strategy
            right = "P" if strategy == "Long" else "C"

            logger.info(f"Fetching option chain for {strategy} strategy ({right} options)")

            # Get option chain
            qqq = Stock("QQQ", "SMART", "USD")
            self.ib.qualifyContracts(qqq)

            chains = self.ib.reqSecDefOptParams(
                underlyingSymbol="QQQ",
                futFopExchange="",
                underlyingSecType="STK",
                underlyingConId=qqq.conId,
            )

            if not chains:
                logger.error("No option chains available")
                return None

            # Find chain for our expiration
            target_chain = None
            for chain in chains:
                if expiration in chain.expirations:
                    target_chain = chain
                    break

            if not target_chain:
                logger.error(f"No option chain found for expiration {expiration}")
                return None

            # Get available strikes around current price
            strikes = sorted(target_chain.strikes)

            # Filter strikes based on strategy
            if strategy == "Long":
                # For Bull Put Spread, we want strikes below current price
                relevant_strikes = [s for s in strikes if s < current_price]
            else:
                # For Bear Call Spread, we want strikes above current price
                relevant_strikes = [s for s in strikes if s > current_price]

            if len(relevant_strikes) < 2:
                logger.error("Insufficient strikes available")
                return None

            # Request option data to get Greeks
            # For performance, sample strikes instead of all
            sample_strikes = relevant_strikes[:: max(1, len(relevant_strikes) // 20)]

            option_data = []
            for strike in sample_strikes:
                option = Option("QQQ", expiration, strike, right, "SMART")
                self.ib.qualifyContracts(option)
                ticker = self.ib.reqMktData(option, "", False, False)

                try:
                    # Wait briefly for data
                    for _ in range(10):
                        await asyncio.sleep(0.1)
                        if ticker.modelGreeks and ticker.modelGreeks.delta:
                            option_data.append(
                                {
                                    "strike": strike,
                                    "delta": abs(ticker.modelGreeks.delta),
                                }
                            )
                            break
                finally:
                    # Always cancel market data subscription, even if error occurs
                    self.ib.cancelMktData(option)

            if len(option_data) < 2:
                logger.error("Unable to fetch option Greeks")
                return self._fallback_strike_selection(current_price, relevant_strikes, strategy)

            # Find strikes closest to target deltas
            short_strike = min(option_data, key=lambda x: abs(x["delta"] - self.short_leg_delta))[
                "strike"
            ]

            long_strike = min(option_data, key=lambda x: abs(x["delta"] - self.long_leg_delta))[
                "strike"
            ]

            # Ensure proper ordering
            if strategy == "Long":
                # Bull Put: long strike < short strike
                strike_long = min(long_strike, short_strike)
                strike_short = max(long_strike, short_strike)
            else:
                # Bear Call: long strike > short strike
                strike_long = max(long_strike, short_strike)
                strike_short = min(long_strike, short_strike)

            return (strike_long, strike_short)

        except Exception as e:
            logger.error(f"Error selecting strikes by delta: {e}", exc_info=True)
            return self._fallback_strike_selection(current_price, relevant_strikes, strategy)

    def _fallback_strike_selection(
        self, current_price: float, strikes: list[float], strategy: str
    ) -> tuple[float, float] | None:
        """
        Fallback strike selection using percentage offsets when delta data unavailable.

        Args:
            current_price: Current QQQ price
            strikes: Available strike prices
            strategy: "Long" or "Short"

        Returns:
            Tuple of (strike_long, strike_short)
        """
        try:
            logger.warning("Using fallback strike selection based on percentage offsets")

            if strategy == "Long":
                # Bull Put Spread: strikes below current price
                # Short leg ~2% OTM, Long leg ~4% OTM
                short_target = current_price * 0.98
                long_target = current_price * 0.96

                short_strike = min(strikes, key=lambda x: abs(x - short_target))
                long_strike = min(strikes, key=lambda x: abs(x - long_target))

                return (min(long_strike, short_strike), max(long_strike, short_strike))
            else:
                # Bear Call Spread: strikes above current price
                # Short leg ~2% OTM, Long leg ~4% OTM
                short_target = current_price * 1.02
                long_target = current_price * 1.04

                short_strike = min(strikes, key=lambda x: abs(x - short_target))
                long_strike = min(strikes, key=lambda x: abs(x - long_target))

                return (max(long_strike, short_strike), min(long_strike, short_strike))

        except Exception as e:
            logger.error(f"Error in fallback strike selection: {e}", exc_info=True)
            return None

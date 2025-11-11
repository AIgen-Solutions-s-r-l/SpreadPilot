"""Price simulation for paper trading."""

import random
from datetime import datetime
from typing import Dict, Optional

import numpy as np

from ..config import get_settings
from ..models import AssetType, OptionType


class PriceSimulator:
    """Simulates realistic market prices for paper trading."""

    def __init__(self):
        """Initialize price simulator."""
        self.settings = get_settings()
        self._base_prices: Dict[str, float] = {}
        self._last_update: Dict[str, datetime] = {}

        # Initialize with realistic base prices
        self._base_prices = {
            "QQQ": 380.0,  # Typical QQQ price
            "SPY": 450.0,  # Typical SPY price
            "AAPL": 180.0,  # Typical AAPL price
        }

    def get_stock_price(self, symbol: str) -> float:
        """Get simulated stock price with volatility.

        Uses Geometric Brownian Motion for realistic price simulation.

        Args:
            symbol: Stock symbol

        Returns:
            Simulated current price
        """
        # Get or initialize base price
        if symbol not in self._base_prices:
            # Default to reasonable price for unknown symbols
            self._base_prices[symbol] = 100.0

        base_price = self._base_prices[symbol]

        # Simulate intraday price movement
        # Time step: assume 1 minute intervals
        dt = 1.0 / (252 * 6.5 * 60)  # 1 minute in trading years

        # Volatility (annualized)
        volatility = self.settings.paper_volatility

        # Drift (assume zero for intraday)
        drift = 0.0

        # Generate random walk
        noise = np.random.normal(0, 1)
        dS = base_price * (drift * dt + volatility * np.sqrt(dt) * noise)

        # Update and persist new price (for consistency within same time window)
        new_price = max(base_price + dS, 0.01)  # Prevent negative prices
        self._base_prices[symbol] = new_price

        return round(new_price, 2)

    def get_bid_ask_spread(self, symbol: str, price: float) -> tuple[float, float]:
        """Get simulated bid/ask prices.

        Args:
            symbol: Stock symbol
            price: Current mid price

        Returns:
            Tuple of (bid_price, ask_price)
        """
        # Typical spread: 1-5 cents for liquid stocks
        spread_cents = random.uniform(0.01, 0.05)
        half_spread = spread_cents / 2

        bid = round(price - half_spread, 2)
        ask = round(price + half_spread, 2)

        return bid, ask

    def get_option_price(
        self,
        symbol: str,
        strike: float,
        expiry: str,
        option_type: OptionType,
        underlying_price: Optional[float] = None,
    ) -> float:
        """Get simulated option price using simplified Black-Scholes.

        This is a simplified model for paper trading simulation.
        Real implementation would use proper Black-Scholes with Greeks.

        Args:
            symbol: Underlying symbol
            strike: Strike price
            expiry: Expiry date (YYYY-MM-DD)
            option_type: CALL or PUT
            underlying_price: Current underlying price (optional)

        Returns:
            Simulated option price
        """
        if underlying_price is None:
            underlying_price = self.get_stock_price(symbol)

        # Calculate time to expiration
        expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
        now = datetime.now()
        days_to_expiry = max((expiry_date - now).days, 0)
        time_to_expiry = days_to_expiry / 365.0

        # Simplified intrinsic value calculation
        if option_type == OptionType.CALL:
            intrinsic = max(underlying_price - strike, 0)
        else:  # PUT
            intrinsic = max(strike - underlying_price, 0)

        # Time value (simplified)
        # Real model would use Black-Scholes with IV
        volatility = self.settings.paper_volatility * np.sqrt(252)  # Annualized
        time_value = volatility * underlying_price * np.sqrt(time_to_expiry) * 0.4

        # Total option price
        option_price = intrinsic + time_value

        # Add some noise
        noise = random.uniform(-0.05, 0.05)
        option_price = max(option_price + noise, 0.01)  # Min $0.01

        return round(option_price, 2)

    def reset_prices(self):
        """Reset all prices to base values."""
        self._base_prices = {
            "QQQ": 380.0,
            "SPY": 450.0,
            "AAPL": 180.0,
        }
        self._last_update.clear()

    def set_base_price(self, symbol: str, price: float):
        """Set base price for a symbol (for testing/admin).

        Args:
            symbol: Stock symbol
            price: Base price to set
        """
        self._base_prices[symbol] = price

    def get_current_price(
        self,
        symbol: str,
        asset_type: AssetType,
        strike: Optional[float] = None,
        expiry: Optional[str] = None,
        option_type: Optional[OptionType] = None,
    ) -> float:
        """Get current price for any asset type.

        Args:
            symbol: Symbol
            asset_type: STOCK or OPTION
            strike: Strike price (for options)
            expiry: Expiry date (for options)
            option_type: CALL or PUT (for options)

        Returns:
            Current simulated price
        """
        if asset_type == AssetType.STOCK:
            return self.get_stock_price(symbol)
        elif asset_type == AssetType.OPTION:
            if not all([strike, expiry, option_type]):
                raise ValueError("Options require strike, expiry, and option_type")
            return self.get_option_price(symbol, strike, expiry, option_type)
        else:
            raise ValueError(f"Unknown asset type: {asset_type}")


# Singleton instance
_price_simulator = None


def get_price_simulator() -> PriceSimulator:
    """Get price simulator singleton."""
    global _price_simulator
    if _price_simulator is None:
        _price_simulator = PriceSimulator()
    return _price_simulator

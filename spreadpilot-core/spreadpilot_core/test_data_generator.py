"""Test data generator for realistic trading scenarios.

Generates realistic market data, trade scenarios, and edge cases for testing.
"""

import random
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Any, Optional
import json


class ScenarioType(str, Enum):
    """Test scenario types."""

    WINNING_TRADE = "winning_trade"
    LOSING_TRADE = "losing_trade"
    ASSIGNMENT = "assignment"
    EARLY_CLOSE = "early_close"
    MARKET_CRASH = "market_crash"
    GAP_UP = "gap_up"
    GAP_DOWN = "gap_down"
    LOW_LIQUIDITY = "low_liquidity"
    HIGH_VOLATILITY = "high_volatility"
    SIDEWAYS_MARKET = "sideways_market"


class TestDataGenerator:
    """Generates realistic test data for trading scenarios."""

    def __init__(self, seed: Optional[int] = None):
        """Initialize generator.

        Args:
            seed: Random seed for reproducible data
        """
        if seed is not None:
            random.seed(seed)

        self.symbols = ["QQQ", "SPY", "AAPL", "MSFT", "GOOGL"]
        self.base_prices = {
            "QQQ": 380.0,
            "SPY": 450.0,
            "AAPL": 180.0,
            "MSFT": 370.0,
            "GOOGL": 140.0,
        }

    def generate_price_history(
        self,
        symbol: str,
        days: int = 30,
        interval_minutes: int = 1,
        volatility: float = 0.02,
    ) -> List[Dict[str, Any]]:
        """Generate realistic price history.

        Args:
            symbol: Stock symbol
            days: Number of days
            interval_minutes: Minutes between data points
            volatility: Daily volatility (default: 2%)

        Returns:
            List of OHLCV data points
        """
        base_price = self.base_prices.get(symbol, 100.0)
        data = []

        # Trading hours: 9:30 AM - 4:00 PM ET
        start_time = datetime.now() - timedelta(days=days)
        current_price = base_price

        for day in range(days):
            day_start = start_time + timedelta(days=day)
            day_start = day_start.replace(hour=9, minute=30, second=0, microsecond=0)

            # Skip weekends
            if day_start.weekday() >= 5:
                continue

            # Trading minutes: 6.5 hours * 60 = 390 minutes
            for minute in range(0, 390, interval_minutes):
                timestamp = day_start + timedelta(minutes=minute)

                # GBM price movement
                dt = interval_minutes / (252 * 6.5 * 60)  # Fraction of trading year
                drift = 0.0  # Assume zero drift
                noise = random.gauss(0, 1)
                price_change = current_price * (drift * dt + volatility * (dt**0.5) * noise)

                open_price = current_price
                high_price = max(current_price, current_price + abs(price_change))
                low_price = min(current_price, current_price - abs(price_change))
                close_price = current_price + price_change
                current_price = close_price

                # Volume (random but realistic)
                volume = int(random.gauss(1000000, 200000))

                data.append(
                    {
                        "timestamp": timestamp.isoformat(),
                        "symbol": symbol,
                        "open": round(open_price, 2),
                        "high": round(high_price, 2),
                        "low": round(low_price, 2),
                        "close": round(close_price, 2),
                        "volume": max(volume, 100),
                    }
                )

        return data

    def generate_trade_scenario(
        self,
        scenario_type: ScenarioType,
        symbol: str = "QQQ",
    ) -> Dict[str, Any]:
        """Generate specific trade scenario.

        Args:
            scenario_type: Type of scenario to generate
            symbol: Stock symbol

        Returns:
            Complete trade scenario data
        """
        base_price = self.base_prices.get(symbol, 100.0)
        quantity = random.randint(1, 10)  # 1-10 contracts

        if scenario_type == ScenarioType.WINNING_TRADE:
            return self._generate_winning_trade(symbol, base_price, quantity)
        elif scenario_type == ScenarioType.LOSING_TRADE:
            return self._generate_losing_trade(symbol, base_price, quantity)
        elif scenario_type == ScenarioType.ASSIGNMENT:
            return self._generate_assignment_scenario(symbol, base_price, quantity)
        elif scenario_type == ScenarioType.EARLY_CLOSE:
            return self._generate_early_close(symbol, base_price, quantity)
        elif scenario_type == ScenarioType.MARKET_CRASH:
            return self._generate_market_crash(symbol, base_price)
        elif scenario_type == ScenarioType.GAP_UP:
            return self._generate_gap_scenario(symbol, base_price, direction="up")
        elif scenario_type == ScenarioType.GAP_DOWN:
            return self._generate_gap_scenario(symbol, base_price, direction="down")
        elif scenario_type == ScenarioType.LOW_LIQUIDITY:
            return self._generate_low_liquidity(symbol, base_price)
        elif scenario_type == ScenarioType.HIGH_VOLATILITY:
            return self._generate_high_volatility(symbol, base_price)
        else:  # SIDEWAYS_MARKET
            return self._generate_sideways_market(symbol, base_price)

    def _generate_winning_trade(self, symbol: str, price: float, quantity: int) -> Dict:
        """Generate profitable trade scenario."""
        strike = round(price * 0.95, 0)  # 5% OTM
        entry_price = random.uniform(0.70, 1.20)
        exit_price = random.uniform(0.10, 0.40)  # Profitable exit
        pnl = (entry_price - exit_price) * quantity * 100

        return {
            "scenario_type": "winning_trade",
            "symbol": symbol,
            "quantity": quantity,
            "strike": strike,
            "entry_date": (datetime.now() - timedelta(days=20)).isoformat(),
            "exit_date": (datetime.now() - timedelta(days=5)).isoformat(),
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "pnl": round(pnl, 2),
            "commission": quantity * 0.65 * 4,  # Entry + exit, 2 legs each
            "net_pnl": round(pnl - (quantity * 0.65 * 4), 2),
        }

    def _generate_losing_trade(self, symbol: str, price: float, quantity: int) -> Dict:
        """Generate unprofitable trade scenario."""
        strike = round(price * 0.95, 0)
        entry_price = random.uniform(0.70, 1.20)
        exit_price = random.uniform(1.50, 2.50)  # Losing exit
        pnl = (entry_price - exit_price) * quantity * 100

        return {
            "scenario_type": "losing_trade",
            "symbol": symbol,
            "quantity": quantity,
            "strike": strike,
            "entry_date": (datetime.now() - timedelta(days=20)).isoformat(),
            "exit_date": (datetime.now() - timedelta(days=2)).isoformat(),
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "pnl": round(pnl, 2),
            "commission": quantity * 0.65 * 4,
            "net_pnl": round(pnl - (quantity * 0.65 * 4), 2),
        }

    def _generate_assignment_scenario(self, symbol: str, price: float, quantity: int) -> Dict:
        """Generate option assignment scenario."""
        strike = round(price * 0.98, 0)  # Near ATM

        return {
            "scenario_type": "assignment",
            "symbol": symbol,
            "quantity": quantity,
            "strike": strike,
            "assignment_date": datetime.now().isoformat(),
            "assignment_price": strike,
            "shares_assigned": quantity * 100,
            "current_price": round(price, 2),
            "unrealized_pnl": round((price - strike) * quantity * 100, 2),
        }

    def _generate_early_close(self, symbol: str, price: float, quantity: int) -> Dict:
        """Generate early close scenario (e.g., 50% profit target)."""
        strike = round(price * 0.95, 0)
        entry_price = random.uniform(0.70, 1.20)
        exit_price = entry_price * 0.5  # 50% profit

        return {
            "scenario_type": "early_close",
            "symbol": symbol,
            "quantity": quantity,
            "strike": strike,
            "entry_date": (datetime.now() - timedelta(days=10)).isoformat(),
            "exit_date": (datetime.now() - timedelta(days=3)).isoformat(),
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "profit_target_pct": 50,
            "days_to_close": 7,
        }

    def _generate_market_crash(self, symbol: str, price: float) -> Dict:
        """Generate market crash scenario."""
        crash_magnitude = random.uniform(0.10, 0.25)  # 10-25% drop
        crash_price = price * (1 - crash_magnitude)

        # Generate intraday crash
        prices = []
        current = price
        for minute in range(0, 120, 5):  # 2 hour crash
            drop = (price - crash_price) / 24 * (minute / 5)
            current = price - drop + random.gauss(0, 2)
            prices.append(round(current, 2))

        return {
            "scenario_type": "market_crash",
            "symbol": symbol,
            "pre_crash_price": round(price, 2),
            "crash_low": round(crash_price, 2),
            "crash_magnitude_pct": round(crash_magnitude * 100, 1),
            "duration_minutes": 120,
            "price_path": prices,
        }

    def _generate_gap_scenario(self, symbol: str, price: float, direction: str) -> Dict:
        """Generate gap up/down scenario."""
        gap_pct = random.uniform(0.02, 0.08)  # 2-8% gap
        if direction == "down":
            gap_pct = -gap_pct

        yesterday_close = price
        today_open = price * (1 + gap_pct)

        return {
            "scenario_type": f"gap_{direction}",
            "symbol": symbol,
            "yesterday_close": round(yesterday_close, 2),
            "today_open": round(today_open, 2),
            "gap_amount": round(today_open - yesterday_close, 2),
            "gap_pct": round(gap_pct * 100, 2),
        }

    def _generate_low_liquidity(self, symbol: str, price: float) -> Dict:
        """Generate low liquidity scenario."""
        return {
            "scenario_type": "low_liquidity",
            "symbol": symbol,
            "price": round(price, 2),
            "bid": round(price - 0.50, 2),  # Wide spread
            "ask": round(price + 0.50, 2),
            "bid_size": 10,  # Small size
            "ask_size": 10,
            "volume_1min": 500,  # Low volume
            "slippage_risk": "HIGH",
        }

    def _generate_high_volatility(self, symbol: str, price: float) -> Dict:
        """Generate high volatility scenario."""
        # Generate volatile price movement
        prices = [price]
        for _ in range(60):  # 1 hour of data
            change_pct = random.gauss(0, 0.01)  # 1% std dev per minute
            prices.append(prices[-1] * (1 + change_pct))

        return {
            "scenario_type": "high_volatility",
            "symbol": symbol,
            "price_range_pct": round((max(prices) - min(prices)) / price * 100, 2),
            "volatility_estimate": 0.05,  # 5% volatility (high)
            "price_path": [round(p, 2) for p in prices],
        }

    def _generate_sideways_market(self, symbol: str, price: float) -> Dict:
        """Generate sideways/choppy market scenario."""
        # Generate mean-reverting prices
        prices = [price]
        for _ in range(390):  # Full day
            # Mean reversion
            deviation = prices[-1] - price
            change = -deviation * 0.1 + random.gauss(0, 0.5)
            prices.append(prices[-1] + change)

        return {
            "scenario_type": "sideways_market",
            "symbol": symbol,
            "mean_price": round(price, 2),
            "price_range_pct": round((max(prices) - min(prices)) / price * 100, 2),
            "trend": "SIDEWAYS",
            "price_path": [round(p, 2) for p in prices[::10]],  # Sample every 10 minutes
        }

    def generate_test_fixtures(self, num_scenarios: int = 10) -> Dict[str, List]:
        """Generate complete test fixture set.

        Args:
            num_scenarios: Number of scenarios per type

        Returns:
            Dictionary of test fixtures by scenario type
        """
        fixtures = {}

        for scenario_type in ScenarioType:
            scenarios = []
            for i in range(num_scenarios):
                symbol = random.choice(self.symbols)
                scenario = self.generate_trade_scenario(scenario_type, symbol)
                scenario["fixture_id"] = f"{scenario_type.value}_{i}"
                scenarios.append(scenario)

            fixtures[scenario_type.value] = scenarios

        return fixtures

    def export_to_json(self, data: Any, filepath: str):
        """Export data to JSON file.

        Args:
            data: Data to export
            filepath: Output file path
        """
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def export_to_csv(self, data: List[Dict], filepath: str):
        """Export data to CSV file.

        Args:
            data: List of dictionaries
            filepath: Output file path
        """
        import csv

        if not data:
            return

        keys = data[0].keys()
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)


# Convenience functions


def generate_test_prices(symbol: str = "QQQ", days: int = 30) -> List[Dict]:
    """Generate test price history.

    Args:
        symbol: Stock symbol
        days: Number of days

    Returns:
        Price history data
    """
    generator = TestDataGenerator()
    return generator.generate_price_history(symbol, days)


def generate_scenario(scenario_type: ScenarioType, symbol: str = "QQQ") -> Dict:
    """Generate specific test scenario.

    Args:
        scenario_type: Type of scenario
        symbol: Stock symbol

    Returns:
        Scenario data
    """
    generator = TestDataGenerator()
    return generator.generate_trade_scenario(scenario_type, symbol)


def generate_all_fixtures(output_dir: str = "tests/fixtures"):
    """Generate all test fixtures and export to files.

    Args:
        output_dir: Output directory for fixture files
    """
    import os

    os.makedirs(output_dir, exist_ok=True)

    generator = TestDataGenerator(seed=42)  # Reproducible

    # Generate fixtures
    fixtures = generator.generate_test_fixtures(num_scenarios=10)

    # Export
    generator.export_to_json(fixtures, f"{output_dir}/scenarios.json")

    # Generate price histories
    for symbol in generator.symbols:
        prices = generator.generate_price_history(symbol, days=30)
        generator.export_to_csv(prices, f"{output_dir}/prices_{symbol}.csv")

    print(f"Generated fixtures in {output_dir}")

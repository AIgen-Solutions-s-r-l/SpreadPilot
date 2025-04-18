# Implementation Plan: Original EMA Strategy in SpreadPilot

## Overview

This document outlines the plan to implement the original EMA crossover strategy from the OLD_CODE system into the new SpreadPilot platform. The customer has requested to begin with this established approach before considering any modifications or enhancements.

## Original Strategy Specifications

Based on analysis of the OLD_CODE, the original strategy has the following specifications:

| Parameter | Value | Source File |
|-----------|-------|-------------|
| Trading Instruments | SOXS, SOXL ETFs | main.py |
| Fast EMA Period | 7 | CONFIG.json |
| Slow EMA Period | 21 | CONFIG.json |
| Bar Period | 5 minutes | CONFIG.json |
| Trailing Stop | 1% | CONFIG.json |
| Close Positions at EOD | Yes | CONFIG.json |
| Trading Hours | 9:30 AM - 3:29 PM (NY) | CONFIG.json |
| Position Sizing | Fixed dollar amount ($10,000) | CONFIG.json |
| Execution Broker | Interactive Brokers | Bot.py |

## Feasibility Assessment

The original strategy can be fully implemented within the SpreadPilot architecture with no technical limitations. The microservices architecture of SpreadPilot actually provides advantages for implementing this strategy with improved reliability and monitoring.

| Aspect | Feasibility | Notes |
|--------|-------------|-------|
| Technical Indicators | ✓ Feasible | EMA calculations can be implemented in trading-bot service |
| Instrument Support | ✓ Feasible | SOXS/SOXL are standard ETFs supported by SpreadPilot |
| Order Types | ✓ Feasible | Market orders and trailing stops are supported |
| IBKR Integration | ✓ Feasible | SpreadPilot has IBKR client in core library |
| Trading Hours | ✓ Feasible | Configurable in SpreadPilot |
| Position Sizing | ✓ Feasible | Can be configured in trading-bot service |
| EOD Position Closing | ✓ Feasible | Can be implemented in trading-bot service |

## Implementation Plan

### 1. Configuration Setup

Create a dedicated configuration for the original strategy:

```python
# trading-bot/app/config.py - Add configuration section

ORIGINAL_STRATEGY_CONFIG = {
    "enabled": True,
    "instruments": ["SOXS", "SOXL"],
    "fast_ema_period": 7,
    "slow_ema_period": 21,
    "bar_period": "5 mins",
    "trailing_stop_percent": 1.0,
    "close_positions_at_eod": True,
    "trading_hours_start": "09:30:00",
    "trading_hours_end": "15:29:00",
    "dollars_per_trade": 10000
}
```

### 2. Strategy Implementation

Create a dedicated strategy class in the trading-bot service:

```python
# trading-bot/app/service/strategies/original_ema_strategy.py

from spreadpilot_core.models.alert import Alert
from spreadpilot_core.models.position import Position
from spreadpilot_core.ibkr.client import IBKRClient
import pandas as pd
from datetime import datetime
import pytz

class OriginalEMAStrategy:
    def __init__(self, config, ibkr_client: IBKRClient, logger):
        self.config = config
        self.ibkr_client = ibkr_client
        self.logger = logger
        self.symbol_data = {}
        self.active_positions = {}
        
        # Initialize data structures for each symbol
        for symbol in self.config["instruments"]:
            self.symbol_data[symbol] = {
                "historical_data": pd.DataFrame(
                    columns=["date", "open", "high", "low", "close", "volume", "EMA_fast", "EMA_slow"]
                ),
                "active_position": 0,
                "high_since_last_bullish": None
            }
    
    def initialize(self):
        """Initialize the strategy, fetch historical data"""
        for symbol in self.config["instruments"]:
            # Request historical data from IBKR
            bars = self.ibkr_client.request_historical_data(
                symbol=symbol,
                bar_size=self.config["bar_period"],
                duration=f"{20 * self.config['slow_ema_period']} D",
                what_to_show="TRADES",
                use_rth=True
            )
            
            # Process historical data
            for bar in bars:
                self._add_historical_data(symbol, bar)
            
            # Get current positions
            positions = self.ibkr_client.request_positions()
            for position in positions:
                if position.symbol in self.config["instruments"]:
                    self.symbol_data[position.symbol]["active_position"] = position.position
                    self.logger.info(f"Found existing position in {position.symbol}: {position.position}")
    
    def _add_historical_data(self, symbol, bar):
        """Add historical data and calculate EMAs"""
        # Similar to SymbolData.addHistoricalData in OLD_CODE
        new_row = {
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
            "EMA_fast": None,
            "EMA_slow": None
        }
        
        df = self.symbol_data[symbol]["historical_data"]
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Calculate EMAs
        if len(df) >= 2:
            df.loc[:, "EMA_fast"] = df["close"].ewm(span=self.config["fast_ema_period"], adjust=False).mean()
            df.loc[:, "EMA_slow"] = df["close"].ewm(span=self.config["slow_ema_period"], adjust=False).mean()
        
        self.symbol_data[symbol]["historical_data"] = df
    
    def _check_bearish_ema_crossover(self, symbol):
        """Check for bearish EMA crossover"""
        df = self.symbol_data[symbol]["historical_data"]
        if len(df) < 3:
            return False
            
        prev_candle = df.iloc[-3]
        current_candle = df.iloc[-2]
        
        return (prev_candle["EMA_fast"] > prev_candle["EMA_slow"] and 
                current_candle["EMA_fast"] <= current_candle["EMA_slow"])
    
    def _check_bullish_ema_crossover(self, symbol):
        """Check for bullish EMA crossover"""
        df = self.symbol_data[symbol]["historical_data"]
        if len(df) < 3:
            return False
            
        prev_candle = df.iloc[-3]
        current_candle = df.iloc[-2]
        
        return (prev_candle["EMA_fast"] < prev_candle["EMA_slow"] and 
                current_candle["EMA_fast"] >= current_candle["EMA_slow"])
    
    def _update_high_since_last_bullish(self, symbol):
        """Update the high since last bullish crossover"""
        df = self.symbol_data[symbol]["historical_data"]
        if len(df) < 3:
            return
            
        completed_candle = df.iloc[-2]
        
        if completed_candle["EMA_fast"] < completed_candle["EMA_slow"]:
            self.symbol_data[symbol]["high_since_last_bullish"] = None
        else:
            if self._check_bullish_ema_crossover(symbol):
                self.symbol_data[symbol]["high_since_last_bullish"] = completed_candle["high"]
            else:
                if self.symbol_data[symbol]["high_since_last_bullish"] is None:
                    self.symbol_data[symbol]["high_since_last_bullish"] = completed_candle["high"]
                else:
                    self.symbol_data[symbol]["high_since_last_bullish"] = max(
                        self.symbol_data[symbol]["high_since_last_bullish"], 
                        completed_candle["high"]
                    )
    
    def _close_position_if_any(self, symbol):
        """Close position if any exists"""
        position = self.symbol_data[symbol]["active_position"]
        if position != 0:
            self.logger.info(f"Closing position in {symbol}: {position}")
            
            # Create market order to close position
            order_action = "BUY" if position < 0 else "SELL"
            quantity = abs(position)
            
            # Place order via IBKR client
            order_id = self.ibkr_client.place_order(
                symbol=symbol,
                order_type="MKT",
                action=order_action,
                quantity=quantity,
                transmit=True
            )
            
            # Create alert for the system
            alert = Alert(
                symbol=symbol,
                action=order_action,
                quantity=quantity,
                price=0,  # Market order
                order_type="MKT",
                strategy="ORIGINAL_EMA",
                signal_type="EXIT"
            )
            
            return alert
        
        return None
    
    def _place_buy_orders(self, symbol):
        """Place buy orders based on strategy"""
        # Calculate position size
        last_price = self.symbol_data[symbol]["historical_data"].iloc[-1]["close"]
        position_size = int(self.config["dollars_per_trade"] / last_price)
        
        if position_size <= 0:
            self.logger.warning(f"Invalid position size calculated for {symbol}: {position_size}")
            return None
        
        self.logger.info(f"Placing buy order for {symbol}, quantity: {position_size}")
        
        # Place market order
        order_id = self.ibkr_client.place_order(
            symbol=symbol,
            order_type="MKT",
            action="BUY",
            quantity=position_size,
            transmit=True
        )
        
        # Place trailing stop
        stop_order_id = self.ibkr_client.place_order(
            symbol=symbol,
            order_type="TRAIL",
            action="SELL",
            quantity=position_size,
            trailing_percent=self.config["trailing_stop_percent"],
            transmit=True
        )
        
        # Create alert for the system
        alert = Alert(
            symbol=symbol,
            action="BUY",
            quantity=position_size,
            price=0,  # Market order
            order_type="MKT",
            strategy="ORIGINAL_EMA",
            signal_type="ENTRY"
        )
        
        return alert
    
    def on_bar_update(self, symbol, bar):
        """Process new bar data"""
        self._add_historical_data(symbol, bar)
        self._update_high_since_last_bullish(symbol)
        
        # Check if we're within trading hours
        ny_timezone = pytz.timezone("America/New_York")
        current_time = datetime.now(ny_timezone).time()
        start_time = datetime.strptime(self.config["trading_hours_start"], "%H:%M:%S").time()
        end_time = datetime.strptime(self.config["trading_hours_end"], "%H:%M:%S").time()
        
        if not (start_time <= current_time <= end_time):
            self.logger.debug(f"Outside trading hours: {current_time}")
            return None
        
        # Strategy logic
        alerts = []
        
        # Check for exit signals
        if self.symbol_data[symbol]["active_position"] > 0:
            df = self.symbol_data[symbol]["historical_data"]
            last_candle = df.iloc[-2]
            
            if (self._check_bearish_ema_crossover(symbol) or 
                last_candle["EMA_fast"] < last_candle["EMA_slow"]):
                alert = self._close_position_if_any(symbol)
                if alert:
                    alerts.append(alert)
        
        # Check for entry signals
        elif self.symbol_data[symbol]["active_position"] == 0:
            if self._check_bullish_ema_crossover(symbol):
                alert = self._place_buy_orders(symbol)
                if alert:
                    alerts.append(alert)
        
        return alerts if alerts else None
    
    def end_of_day(self):
        """Handle end of day operations"""
        if not self.config["close_positions_at_eod"]:
            return None
            
        alerts = []
        for symbol in self.config["instruments"]:
            if self.symbol_data[symbol]["active_position"] != 0:
                alert = self._close_position_if_any(symbol)
                if alert:
                    alerts.append(alert)
        
        return alerts if alerts else None
```

### 3. Integration with Trading Bot Service

Modify the trading bot service to incorporate the original strategy:

```python
# trading-bot/app/main.py - Add strategy initialization

from app.service.strategies.original_ema_strategy import OriginalEMAStrategy
from spreadpilot_core.ibkr.client import IBKRClient
from app.config import ORIGINAL_STRATEGY_CONFIG

# Initialize IBKR client
ibkr_client = IBKRClient(
    host="127.0.0.1",
    port=7496 if config.RUN_ON_REAL else 7497,
    client_id=1
)

# Initialize strategy
original_strategy = OriginalEMAStrategy(
    config=ORIGINAL_STRATEGY_CONFIG,
    ibkr_client=ibkr_client,
    logger=logger
)

# Initialize strategy data
original_strategy.initialize()

# Register strategy with the main event loop
app.register_strategy("ORIGINAL_EMA", original_strategy)
```

### 4. Alert Router Integration

Ensure the alert router can handle alerts from the original strategy:

```python
# alert-router/app/service/router.py - Add strategy handling

@router.route("ORIGINAL_EMA")
def route_original_ema_alerts(alert):
    """Route alerts from the original EMA strategy"""
    # For the original strategy, we'll route alerts directly to execution
    # without any modifications, as requested by the customer
    return {
        "route_to": "execution",
        "modified_alert": alert
    }
```

### 5. Reporting Integration

Ensure the reporting service can handle the original strategy:

```python
# report-worker/app/service/generator.py - Add strategy reporting

def generate_original_ema_report(trades, start_date, end_date):
    """Generate report for the original EMA strategy"""
    # Filter trades for the original strategy
    strategy_trades = [t for t in trades if t.strategy == "ORIGINAL_EMA"]
    
    # Calculate performance metrics
    total_trades = len(strategy_trades)
    winning_trades = len([t for t in strategy_trades if t.pnl > 0])
    losing_trades = len([t for t in strategy_trades if t.pnl < 0])
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    
    total_pnl = sum(t.pnl for t in strategy_trades)
    
    return {
        "strategy": "ORIGINAL_EMA",
        "period": f"{start_date} to {end_date}",
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "total_pnl": total_pnl
    }
```

## Testing Plan

1. **Unit Testing**:
   - Test EMA calculation accuracy
   - Test crossover detection logic
   - Test position sizing calculation

2. **Integration Testing**:
   - Test IBKR connectivity and order placement
   - Test alert generation and routing
   - Test end-of-day position closing

3. **Historical Backtesting**:
   - Run the strategy on historical data
   - Compare results with OLD_CODE performance

4. **Paper Trading**:
   - Run the strategy in paper trading mode
   - Verify order execution and position management
   - Compare behavior with OLD_CODE

5. **Production Validation**:
   - Run in parallel with OLD_CODE (if possible)
   - Compare trade signals and execution

## Implementation Timeline

| Phase | Task | Duration | Dependencies |
|-------|------|----------|--------------|
| 1 | Configuration Setup | 1 day | None |
| 2 | Strategy Implementation | 3 days | Configuration |
| 3 | Trading Bot Integration | 2 days | Strategy Implementation |
| 4 | Alert Router Integration | 1 day | Trading Bot Integration |
| 5 | Reporting Integration | 2 days | Alert Router Integration |
| 6 | Unit Testing | 2 days | All Implementation |
| 7 | Integration Testing | 3 days | Unit Testing |
| 8 | Historical Backtesting | 2 days | Integration Testing |
| 9 | Paper Trading | 5 days | Historical Backtesting |
| 10 | Production Validation | 5 days | Paper Trading |

**Total Estimated Time**: 26 working days (approximately 5-6 weeks)

## Conclusion

The original EMA crossover strategy from OLD_CODE can be fully implemented within the SpreadPilot architecture. The implementation will preserve all the original strategy parameters and logic while benefiting from the improved infrastructure of the SpreadPilot platform.

This approach allows the customer to start with their established strategy before considering any modifications or enhancements, as requested. Once the original strategy is successfully implemented and validated, we can discuss potential improvements or additional strategies to leverage the full capabilities of the SpreadPilot platform.

---

*Document Version: 1.0*  
*Last Updated: April 18, 2025*  
*Prepared by: Roo Commander*
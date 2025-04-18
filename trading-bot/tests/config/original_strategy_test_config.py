"""
Test configuration for the Original EMA Strategy.

This module contains test parameters, mock data sources, and test credentials
for unit and integration testing of the Original EMA Strategy.
"""

import datetime
import pandas as pd
from typing import Dict, List

# Test parameters matching the original strategy
TEST_ORIGINAL_EMA_STRATEGY = {
    "enabled": True,
    "ibkr_secret_ref": "test_ibkr_secret",
    "symbols": ["SOXS", "SOXL"],
    "fast_ema": 7,
    "slow_ema": 21,
    "bar_period": "5 mins",
    "trading_start_time": "09:30:00",
    "trading_end_time": "15:29:00",
    "dollar_amount": 10000,
    "trailing_stop_pct": 1.0,
    "close_at_eod": True
}

# Test credentials for IBKR
TEST_IBKR_CREDENTIALS = {
    "username": "testuser",
    "password": "testpassword",
    "host": "127.0.0.1",
    "port": 4002,  # Paper trading port
    "client_id": 1,
    "trading_mode": "paper"
}

# Mock historical data for SOXS (uptrend scenario)
def create_mock_soxs_uptrend_data() -> pd.DataFrame:
    """Create mock historical data for SOXS in an uptrend scenario."""
    # Create a date range for the last 30 days with 5-minute intervals during market hours
    now = datetime.datetime.now()
    start_date = now - datetime.timedelta(days=30)
    
    # Create an empty list to store data
    data = []
    
    # Generate data for each day
    current_date = start_date
    while current_date <= now:
        # Skip weekends
        if current_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            current_date += datetime.timedelta(days=1)
            continue
        
        # Generate data for market hours (9:30 AM to 4:00 PM)
        market_open = datetime.datetime.combine(
            current_date.date(), datetime.time(9, 30, 0)
        )
        market_close = datetime.datetime.combine(
            current_date.date(), datetime.time(16, 0, 0)
        )
        
        # Start with a base price and create an uptrend
        base_price = 20.0 + (current_date - start_date).days * 0.5  # Gradual uptrend
        
        # Generate 5-minute bars
        current_time = market_open
        while current_time <= market_close:
            # Add some random variation to the price
            open_price = base_price + (current_time.hour + current_time.minute/60) * 0.1
            close_price = open_price + 0.2  # Slight uptrend within the day
            high_price = max(open_price, close_price) + 0.1
            low_price = min(open_price, close_price) - 0.1
            
            # Add some random volume
            volume = 1000 + (current_time.hour * 100)
            
            # Add the data point
            data.append({
                "timestamp": current_time,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume
            })
            
            # Move to the next 5-minute interval
            current_time += datetime.timedelta(minutes=5)
        
        # Move to the next day
        current_date += datetime.timedelta(days=1)
    
    # Create a DataFrame
    df = pd.DataFrame(data)
    
    # Set timestamp as index
    df.set_index("timestamp", inplace=True)
    
    return df

# Mock historical data for SOXL (downtrend scenario)
def create_mock_soxl_downtrend_data() -> pd.DataFrame:
    """Create mock historical data for SOXL in a downtrend scenario."""
    # Create a date range for the last 30 days with 5-minute intervals during market hours
    now = datetime.datetime.now()
    start_date = now - datetime.timedelta(days=30)
    
    # Create an empty list to store data
    data = []
    
    # Generate data for each day
    current_date = start_date
    while current_date <= now:
        # Skip weekends
        if current_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            current_date += datetime.timedelta(days=1)
            continue
        
        # Generate data for market hours (9:30 AM to 4:00 PM)
        market_open = datetime.datetime.combine(
            current_date.date(), datetime.time(9, 30, 0)
        )
        market_close = datetime.datetime.combine(
            current_date.date(), datetime.time(16, 0, 0)
        )
        
        # Start with a base price and create a downtrend
        base_price = 50.0 - (current_date - start_date).days * 0.3  # Gradual downtrend
        
        # Generate 5-minute bars
        current_time = market_open
        while current_time <= market_close:
            # Add some random variation to the price
            open_price = base_price - (current_time.hour + current_time.minute/60) * 0.05
            close_price = open_price - 0.1  # Slight downtrend within the day
            high_price = max(open_price, close_price) + 0.1
            low_price = min(open_price, close_price) - 0.1
            
            # Add some random volume
            volume = 1500 + (current_time.hour * 150)
            
            # Add the data point
            data.append({
                "timestamp": current_time,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume
            })
            
            # Move to the next 5-minute interval
            current_time += datetime.timedelta(minutes=5)
        
        # Move to the next day
        current_date += datetime.timedelta(days=1)
    
    # Create a DataFrame
    df = pd.DataFrame(data)
    
    # Set timestamp as index
    df.set_index("timestamp", inplace=True)
    
    return df

# Mock historical data for crossover scenarios
def create_mock_crossover_data() -> Dict[str, pd.DataFrame]:
    """Create mock historical data with specific crossover patterns."""
    # Create a date range for 5 days with 5-minute intervals during market hours
    now = datetime.datetime.now()
    start_date = now - datetime.timedelta(days=5)
    
    # Create empty DataFrames for each symbol
    data = {
        "SOXS": [],
        "SOXL": []
    }
    
    # Generate data for each day
    current_date = start_date
    day_count = 0
    while current_date <= now:
        # Skip weekends
        if current_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            current_date += datetime.timedelta(days=1)
            continue
        
        # Generate data for market hours (9:30 AM to 4:00 PM)
        market_open = datetime.datetime.combine(
            current_date.date(), datetime.time(9, 30, 0)
        )
        market_close = datetime.datetime.combine(
            current_date.date(), datetime.time(16, 0, 0)
        )
        
        # Generate 5-minute bars
        current_time = market_open
        bar_count = 0
        while current_time <= market_close:
            # SOXS: Create a bullish crossover on day 2 around noon
            if day_count == 1 and current_time.hour == 12:
                # Before crossover: fast EMA below slow EMA
                if current_time.minute < 30:
                    soxs_open = 25.0
                    soxs_close = 25.2
                # Crossover: fast EMA crosses above slow EMA
                elif current_time.minute == 30:
                    soxs_open = 25.3
                    soxs_close = 26.0
                # After crossover: fast EMA above slow EMA
                else:
                    soxs_open = 26.1
                    soxs_close = 26.3
            else:
                # Normal price action
                soxs_open = 25.0 + day_count * 0.5 + bar_count * 0.01
                soxs_close = soxs_open + 0.2
            
            soxs_high = max(soxs_open, soxs_close) + 0.1
            soxs_low = min(soxs_open, soxs_close) - 0.1
            
            # SOXL: Create a bearish crossover on day 3 around 2 PM
            if day_count == 2 and current_time.hour == 14:
                # Before crossover: fast EMA above slow EMA
                if current_time.minute < 30:
                    soxl_open = 45.0
                    soxl_close = 44.8
                # Crossover: fast EMA crosses below slow EMA
                elif current_time.minute == 30:
                    soxl_open = 44.7
                    soxl_close = 44.0
                # After crossover: fast EMA below slow EMA
                else:
                    soxl_open = 43.9
                    soxl_close = 43.7
            else:
                # Normal price action
                soxl_open = 45.0 - day_count * 0.3 - bar_count * 0.005
                soxl_close = soxl_open - 0.1
            
            soxl_high = max(soxl_open, soxl_close) + 0.1
            soxl_low = min(soxl_open, soxl_close) - 0.1
            
            # Add the data points
            data["SOXS"].append({
                "timestamp": current_time,
                "open": soxs_open,
                "high": soxs_high,
                "low": soxs_low,
                "close": soxs_close,
                "volume": 1000 + bar_count * 10
            })
            
            data["SOXL"].append({
                "timestamp": current_time,
                "open": soxl_open,
                "high": soxl_high,
                "low": soxl_low,
                "close": soxl_close,
                "volume": 1500 + bar_count * 15
            })
            
            # Move to the next 5-minute interval
            current_time += datetime.timedelta(minutes=5)
            bar_count += 1
        
        # Move to the next day
        current_date += datetime.timedelta(days=1)
        day_count += 1
    
    # Create DataFrames
    dfs = {}
    for symbol, symbol_data in data.items():
        df = pd.DataFrame(symbol_data)
        df.set_index("timestamp", inplace=True)
        dfs[symbol] = df
    
    return dfs

# Mock data for trailing stop scenarios
def create_mock_trailing_stop_data() -> Dict[str, pd.DataFrame]:
    """Create mock historical data with patterns that trigger trailing stops."""
    # Create a date range for 3 days with 5-minute intervals during market hours
    now = datetime.datetime.now()
    start_date = now - datetime.timedelta(days=3)
    
    # Create empty DataFrames for each symbol
    data = {
        "SOXS": [],
        "SOXL": []
    }
    
    # Generate data for each day
    current_date = start_date
    day_count = 0
    while current_date <= now:
        # Skip weekends
        if current_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            current_date += datetime.timedelta(days=1)
            continue
        
        # Generate data for market hours (9:30 AM to 4:00 PM)
        market_open = datetime.datetime.combine(
            current_date.date(), datetime.time(9, 30, 0)
        )
        market_close = datetime.datetime.combine(
            current_date.date(), datetime.time(16, 0, 0)
        )
        
        # Generate 5-minute bars
        current_time = market_open
        bar_count = 0
        while current_time <= market_close:
            # SOXS: Create a pattern that triggers a trailing stop for a long position on day 1
            if day_count == 0:
                if current_time.hour < 11:
                    # Uptrend before position entry
                    soxs_open = 20.0 + bar_count * 0.05
                    soxs_close = soxs_open + 0.1
                elif current_time.hour == 11 and current_time.minute == 0:
                    # Bullish crossover bar (position entry)
                    soxs_open = 22.0
                    soxs_close = 22.5
                elif current_time.hour < 14:
                    # Continued uptrend after entry
                    soxs_open = 22.5 + (bar_count - 30) * 0.02
                    soxs_close = soxs_open + 0.05
                else:
                    # Sharp drop that triggers trailing stop (1% below recent high)
                    soxs_open = 23.5
                    soxs_close = 23.0
                    if current_time.hour == 14 and current_time.minute == 0:
                        # The bar that triggers the stop
                        soxs_low = 22.0  # More than 1% below the entry price
                    else:
                        soxs_low = soxs_open - 0.2
            else:
                # Normal price action on other days
                soxs_open = 20.0 + day_count * 0.5 + bar_count * 0.01
                soxs_close = soxs_open + 0.1
                soxs_low = soxs_open - 0.2
            
            soxs_high = max(soxs_open, soxs_close) + 0.1
            if 'soxs_low' not in locals():
                soxs_low = min(soxs_open, soxs_close) - 0.1
            
            # SOXL: Create a pattern that triggers a trailing stop for a short position on day 2
            if day_count == 1:
                if current_time.hour < 11:
                    # Downtrend before position entry
                    soxl_open = 40.0 - bar_count * 0.05
                    soxl_close = soxl_open - 0.1
                elif current_time.hour == 11 and current_time.minute == 0:
                    # Bearish crossover bar (position entry)
                    soxl_open = 38.0
                    soxl_close = 37.5
                elif current_time.hour < 14:
                    # Continued downtrend after entry
                    soxl_open = 37.5 - (bar_count - 30) * 0.02
                    soxl_close = soxl_open - 0.05
                else:
                    # Sharp rise that triggers trailing stop (1% above recent low)
                    soxl_open = 36.5
                    soxl_close = 37.0
                    if current_time.hour == 14 and current_time.minute == 0:
                        # The bar that triggers the stop
                        soxl_high = 38.0  # More than 1% above the entry price
                    else:
                        soxl_high = soxl_open + 0.2
            else:
                # Normal price action on other days
                soxl_open = 40.0 - day_count * 0.3 - bar_count * 0.005
                soxl_close = soxl_open - 0.1
                soxl_high = soxl_open + 0.2
            
            if 'soxl_high' not in locals():
                soxl_high = max(soxl_open, soxl_close) + 0.1
            soxl_low = min(soxl_open, soxl_close) - 0.1
            
            # Add the data points
            data["SOXS"].append({
                "timestamp": current_time,
                "open": soxs_open,
                "high": soxs_high,
                "low": soxs_low,
                "close": soxs_close,
                "volume": 1000 + bar_count * 10
            })
            
            data["SOXL"].append({
                "timestamp": current_time,
                "open": soxl_open,
                "high": soxl_high,
                "low": soxl_low,
                "close": soxl_close,
                "volume": 1500 + bar_count * 15
            })
            
            # Reset local variables
            if 'soxs_low' in locals():
                del soxs_low
            if 'soxl_high' in locals():
                del soxl_high
            
            # Move to the next 5-minute interval
            current_time += datetime.timedelta(minutes=5)
            bar_count += 1
        
        # Move to the next day
        current_date += datetime.timedelta(days=1)
        day_count += 1
    
    # Create DataFrames
    dfs = {}
    for symbol, symbol_data in data.items():
        df = pd.DataFrame(symbol_data)
        df.set_index("timestamp", inplace=True)
        dfs[symbol] = df
    
    return dfs

# Function to get mock data for testing
def get_mock_data(scenario: str = "crossover") -> Dict[str, pd.DataFrame]:
    """
    Get mock data for testing based on the specified scenario.
    
    Args:
        scenario: The scenario to get mock data for.
            Options: "crossover", "trailing_stop", "uptrend", "downtrend"
    
    Returns:
        Dictionary mapping symbols to DataFrames with historical data
    """
    if scenario == "crossover":
        return create_mock_crossover_data()
    elif scenario == "trailing_stop":
        return create_mock_trailing_stop_data()
    elif scenario == "uptrend":
        return {"SOXS": create_mock_soxs_uptrend_data(), "SOXL": create_mock_soxl_downtrend_data()}
    elif scenario == "downtrend":
        return {"SOXS": create_mock_soxl_downtrend_data(), "SOXL": create_mock_soxs_uptrend_data()}
    else:
        raise ValueError(f"Unknown scenario: {scenario}")
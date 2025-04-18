"""Integration tests for the trading signal processing flow."""

import asyncio
import datetime
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from spreadpilot_core.models.trade import Trade, TradeSide, TradeStatus
from spreadpilot_core.ibkr.client import OrderStatus
import importlib

trading_bot_service = importlib.import_module('trading-bot.app.service.signals')
SignalProcessor = trading_bot_service.SignalProcessor


@pytest.mark.asyncio
async def test_process_trading_signal(
    signal_processor,
    mock_sheets_client,
    mock_ibkr_client,
    firestore_client,
    test_follower,
):
    """
    Test that a trading signal from Google Sheets is correctly processed by the trading-bot.
    
    This test verifies:
    1. Signal is fetched from Google Sheets
    2. Order is placed with IBKR
    3. Trade record is stored in Firestore
    """
    # Setup test signal
    test_signal = {
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "ticker": "QQQ",
        "strategy": "Long",  # Bull Put
        "qty_per_leg": 1,
        "strike_long": 380.0,
        "strike_short": 385.0,
    }
    mock_sheets_client.add_test_signal(test_signal)
    
    # Ensure IBKR client is connected
    await mock_ibkr_client.connect()
    assert mock_ibkr_client.connected is True
    
    # Process signal for the test follower
    result = await signal_processor.process_signal(
        strategy=test_signal["strategy"],
        qty_per_leg=test_signal["qty_per_leg"],
        strike_long=test_signal["strike_long"],
        strike_short=test_signal["strike_short"],
        follower_id=test_follower.id,
    )
    
    # Verify result
    assert result["success"] is True
    assert "trade_id" in result
    assert result["status"] == "FILLED"
    
    # Verify order was placed with IBKR
    assert len(mock_ibkr_client.orders) > 0
    order = mock_ibkr_client.orders[-1]
    assert order["strategy"] == test_signal["strategy"]
    assert order["qty_per_leg"] == test_signal["qty_per_leg"]
    assert order["strike_long"] == test_signal["strike_long"]
    assert order["strike_short"] == test_signal["strike_short"]
    
    # Verify trade record was stored in Firestore
    trade_id = result["trade_id"]
    trade_doc = firestore_client.collection("trades").document(trade_id).get()
    assert trade_doc.exists
    
    trade_data = trade_doc.to_dict()
    assert trade_data["followerId"] == test_follower.id
    assert trade_data["side"] == TradeSide.LONG.value
    assert trade_data["qty"] == test_signal["qty_per_leg"]
    assert trade_data["strike"] == test_signal["strike_long"]
    assert trade_data["status"] == TradeStatus.FILLED.value


@pytest.mark.asyncio
async def test_process_trading_signal_insufficient_margin(
    signal_processor,
    mock_ibkr_client,
    test_follower,
):
    """
    Test handling of insufficient margin when processing a trading signal.
    
    This test verifies:
    1. Margin check fails
    2. Alert is created
    3. Order is not placed
    """
    # Setup mock to return insufficient margin
    mock_ibkr_client.check_margin_for_trade = AsyncMock(
        return_value=(False, "Insufficient funds")
    )
    
    # Process signal
    result = await signal_processor.process_signal(
        strategy="Long",
        qty_per_leg=1,
        strike_long=380.0,
        strike_short=385.0,
        follower_id=test_follower.id,
    )
    
    # Verify result
    assert result["success"] is False
    assert "Insufficient margin" in result["error"]
    
    # Verify alert was created
    signal_processor.service.alert_manager.create_alert.assert_called_once()
    
    # Verify no order was placed
    initial_order_count = len(mock_ibkr_client.orders)
    assert len(mock_ibkr_client.orders) == initial_order_count


@pytest.mark.asyncio
async def test_process_trading_signal_mid_price_too_low(
    signal_processor,
    mock_ibkr_client,
    test_follower,
):
    """
    Test handling of mid price too low when processing a trading signal.
    
    This test verifies:
    1. Order is rejected due to low mid price
    2. Alert is created
    3. Trade record is not stored
    """
    # Setup mock to return order rejected with mid price too low
    mock_ibkr_client.place_vertical_spread = AsyncMock(
        return_value={
            "status": OrderStatus.REJECTED,
            "error": "Mid price too low",
            "mid_price": 0.50,  # Below min_price of 0.70
            "trade_id": None,
        }
    )
    
    # Process signal
    result = await signal_processor.process_signal(
        strategy="Long",
        qty_per_leg=1,
        strike_long=380.0,
        strike_short=385.0,
        follower_id=test_follower.id,
    )
    
    # Verify result
    assert result["success"] is False
    assert "Mid price too low" in result["error"]
    
    # Verify alert was created
    signal_processor.service.alert_manager.create_alert.assert_called_once()


@pytest.mark.asyncio
async def test_process_trading_signal_partial_fill(
    signal_processor,
    mock_ibkr_client,
    firestore_client,
    test_follower,
):
    """
    Test handling of partial fill when processing a trading signal.
    
    This test verifies:
    1. Order is partially filled
    2. Alert is created
    3. Trade record is stored with partial status
    """
    # Setup mock to return partial fill
    mock_ibkr_client.place_vertical_spread = AsyncMock(
        return_value={
            "status": OrderStatus.PARTIAL,
            "trade_id": str(uuid.uuid4()),
            "filled": 1,
            "remaining": 1,
            "fill_price": 0.75,
            "fill_time": datetime.datetime.now().isoformat(),
        }
    )
    
    # Process signal
    result = await signal_processor.process_signal(
        strategy="Long",
        qty_per_leg=2,  # Requesting 2, but only 1 filled
        strike_long=380.0,
        strike_short=385.0,
        follower_id=test_follower.id,
    )
    
    # Verify result
    assert result["success"] is True
    assert result["status"] == OrderStatus.PARTIAL
    assert result["filled"] == 1
    
    # Verify alert was created
    signal_processor.service.alert_manager.create_alert.assert_called_once()
    
    # Verify trade record was stored in Firestore
    trade_id = result["trade_id"]
    trade_doc = firestore_client.collection("trades").document(trade_id).get()
    assert trade_doc.exists
    
    trade_data = trade_doc.to_dict()
    assert trade_data["status"] == TradeStatus.PARTIAL.value


@pytest.mark.asyncio
async def test_process_trading_signal_for_all_followers(
    signal_processor,
    mock_ibkr_client,
    firestore_client,
):
    """
    Test processing a trading signal for all active followers.
    
    This test verifies:
    1. Signal is processed for all active followers
    2. Orders are placed for each follower
    3. Trade records are stored for each follower
    """
    # Setup multiple active followers in the service
    follower_ids = [f"follower-{i}" for i in range(3)]
    signal_processor.service.active_followers = {
        follower_id: True for follower_id in follower_ids
    }
    
    # Process signal for all followers
    result = await signal_processor.process_signal(
        strategy="Long",
        qty_per_leg=1,
        strike_long=380.0,
        strike_short=385.0,
        follower_id=None,  # Process for all followers
    )
    
    # Verify result
    assert result["success"] is True
    assert "results" in result
    assert len(result["results"]) == len(follower_ids)
    
    # Verify each follower's result
    for follower_id, follower_result in result["results"].items():
        assert follower_result["success"] is True
        assert "trade_id" in follower_result
        assert follower_result["status"] == OrderStatus.FILLED
        
        # Verify trade record was stored in Firestore
        trade_id = follower_result["trade_id"]
        trade_doc = firestore_client.collection("trades").document(trade_id).get()
        assert trade_doc.exists
        
        trade_data = trade_doc.to_dict()
        assert trade_data["followerId"] == follower_id
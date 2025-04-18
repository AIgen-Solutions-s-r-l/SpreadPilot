"""Integration tests for the assignment detection and handling flow."""

import asyncio
import datetime
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from spreadpilot_core.models.position import Position, AssignmentState
from spreadpilot_core.models.alert import Alert, AlertType, AlertSeverity
from spreadpilot_core.ibkr.client import IBKRClient
import importlib

# Import modules using importlib
trading_bot_positions = importlib.import_module('trading-bot.app.service.positions')

# Get specific imports
PositionManager = trading_bot_positions.PositionManager



@pytest.mark.asyncio
async def test_assignment_detection(
    mock_ibkr_client,
    firestore_client,
    test_follower,
    test_position,
):
    """
    Test the detection of assignments (short-leg).
    
    This test verifies:
    1. Assignment is detected by IBKR client
    2. Position is updated in Firestore
    3. Alert is created
    """
    # Setup mock IBKR client to return assignment detected
    mock_ibkr_client.check_assignment = AsyncMock(
        return_value=(AssignmentState.ASSIGNED, 1, 0)
    )
    
    # Create position manager with mocked dependencies
    mock_service = MagicMock()
    mock_service.ibkr_manager.get_client = AsyncMock(return_value=mock_ibkr_client)
    mock_service.db = firestore_client
    mock_service.alert_manager.create_alert = AsyncMock()
    
    position_manager = PositionManager(mock_service)
    
    # Check for assignment
    result = await position_manager.check_assignment(test_follower.id)
    
    # Verify assignment was detected
    assert result["assignment_state"] == AssignmentState.ASSIGNED
    assert result["short_qty"] == 1
    assert result["long_qty"] == 0
    
    # Verify position was updated in Firestore
    position_doc = firestore_client.document(
        f"positions/{test_follower.id}/daily/{test_position.date}"
    ).get()
    assert position_doc.exists
    
    position_data = position_doc.to_dict()
    assert position_data["assignmentState"] == AssignmentState.ASSIGNED.value
    
    # Verify alert was created
    mock_service.alert_manager.create_alert.assert_called_once()
    call_args = mock_service.alert_manager.create_alert.call_args[1]
    assert call_args["follower_id"] == test_follower.id
    assert call_args["alert_type"] == AlertType.ASSIGNMENT_DETECTED


@pytest.mark.asyncio
async def test_assignment_compensation(
    mock_ibkr_client,
    firestore_client,
    test_follower,
    test_position,
):
    """
    Test the re-balancing mechanism via long-leg exercise.
    
    This test verifies:
    1. Long-leg exercise is triggered
    2. Position is updated to compensated state
    3. Alert is created
    """
    # Setup test position with assignment state
    test_position.assignment_state = AssignmentState.ASSIGNED
    test_position.short_qty = 0  # Assigned, so short leg is gone
    test_position.long_qty = 1   # Still have long leg
    
    # Update position in Firestore
    firestore_client.document(
        f"positions/{test_follower.id}/daily/{test_position.date}"
    ).set(test_position.to_dict())
    
    # Setup mock IBKR client
    mock_ibkr_client.exercise_options = AsyncMock(
        return_value={
            "success": True,
            "qty_exercised": 1,
        }
    )
    
    # Create position manager with mocked dependencies
    mock_service = MagicMock()
    mock_service.ibkr_manager.get_client = AsyncMock(return_value=mock_ibkr_client)
    mock_service.db = firestore_client
    mock_service.alert_manager.create_alert = AsyncMock()
    
    position_manager = PositionManager(mock_service)
    
    # Compensate assignment
    result = await position_manager.compensate_assignment(test_follower.id)
    
    # Verify compensation was successful
    assert result["success"] is True
    assert result["qty_exercised"] == 1
    
    # Verify position was updated in Firestore
    position_doc = firestore_client.document(
        f"positions/{test_follower.id}/daily/{test_position.date}"
    ).get()
    assert position_doc.exists
    
    position_data = position_doc.to_dict()
    assert position_data["assignmentState"] == AssignmentState.COMPENSATED.value
    assert position_data["longQty"] == 0  # Long leg exercised
    
    # Verify alert was created
    mock_service.alert_manager.create_alert.assert_called_once()
    call_args = mock_service.alert_manager.create_alert.call_args[1]
    assert call_args["follower_id"] == test_follower.id
    assert call_args["alert_type"] == AlertType.ASSIGNMENT_COMPENSATED


@pytest.mark.asyncio
async def test_alert_routing_for_assignment(
    mock_email_sender,
    mock_telegram_sender,
    test_follower,
):
    """
    Test that alerts are sent via the alert-router for assignment events.
    
    This test verifies:
    1. Assignment alert is routed to email and Telegram
    2. Alert contains correct information
    """
    from spreadpilot_core.models.alert import AlertEvent
    import importlib
    
    # Import module using importlib
    alert_router_service = importlib.import_module('alert-router.app.service.router')
    
    # Get specific import
    route_alert = alert_router_service.route_alert
    
    # Create test alert event
    alert_event = AlertEvent(
        event_type=AlertType.ASSIGNMENT_DETECTED,
        timestamp=datetime.datetime.now(),
        message=f"Assignment detected for follower {test_follower.id}",
        params={
            "follower_id": test_follower.id,
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "short_qty": 1,
        },
    )
    
    # Route the alert
    await route_alert(alert_event)
    
    # Verify email was sent
    mock_email_sender.assert_called_once()
    email_args = mock_email_sender.call_args[1]
    assert "Assignment detected" in email_args["subject"]
    assert test_follower.id in email_args["body"]
    
    # Verify Telegram message was sent
    mock_telegram_sender.assert_called_once()
    telegram_args = mock_telegram_sender.call_args[1]
    assert test_follower.id in telegram_args["message"]


@pytest.mark.asyncio
async def test_position_update_after_trade(
    firestore_client,
    test_follower,
):
    """
    Test that positions are correctly updated after a trade.
    
    This test verifies:
    1. New position is created if none exists
    2. Existing position is updated with new trade data
    """
    # Create position manager with mocked dependencies
    mock_service = MagicMock()
    mock_service.db = firestore_client
    
    position_manager = PositionManager(mock_service)
    
    # Create test trade
    from spreadpilot_core.models.trade import Trade, TradeSide, TradeStatus
    
    trade = Trade(
        id=str(uuid.uuid4()),
        follower_id=test_follower.id,
        side=TradeSide.LONG,
        qty=2,
        strike=380.0,
        limit_price_requested=0.75,
        status=TradeStatus.FILLED,
        timestamps={
            "submitted": datetime.datetime.now(),
            "filled": datetime.datetime.now(),
        },
    )
    
    # Update position with trade
    await position_manager.update_position(test_follower.id, trade)
    
    # Verify position was updated in Firestore
    date = datetime.datetime.now().strftime("%Y%m%d")
    position_doc = firestore_client.document(
        f"positions/{test_follower.id}/daily/{date}"
    ).get()
    assert position_doc.exists
    
    position_data = position_doc.to_dict()
    assert position_data["longQty"] == 2  # Long side trade
    assert position_data["shortQty"] == 0
    
    # Add a short side trade
    trade2 = Trade(
        id=str(uuid.uuid4()),
        follower_id=test_follower.id,
        side=TradeSide.SHORT,
        qty=1,
        strike=385.0,
        limit_price_requested=0.75,
        status=TradeStatus.FILLED,
        timestamps={
            "submitted": datetime.datetime.now(),
            "filled": datetime.datetime.now(),
        },
    )
    
    # Update position with second trade
    await position_manager.update_position(test_follower.id, trade2)
    
    # Verify position was updated with both trades
    position_doc = firestore_client.document(
        f"positions/{test_follower.id}/daily/{date}"
    ).get()
    position_data = position_doc.to_dict()
    assert position_data["longQty"] == 2
    assert position_data["shortQty"] == 1


@pytest.mark.asyncio
async def test_daily_position_check(
    mock_ibkr_client,
    firestore_client,
    test_follower,
    test_position,
):
    """
    Test the daily position check process.
    
    This test verifies:
    1. Positions are checked for all followers
    2. Assignments are detected and compensated
    3. Alerts are created as needed
    """
    # Setup mock IBKR client to return assignment detected for first check
    # and compensated for second check
    mock_ibkr_client.check_assignment = AsyncMock(
        side_effect=[
            (AssignmentState.ASSIGNED, 1, 0),  # First call - assignment detected
            (AssignmentState.COMPENSATED, 0, 0),  # Second call - after compensation
        ]
    )
    
    mock_ibkr_client.exercise_options = AsyncMock(
        return_value={
            "success": True,
            "qty_exercised": 1,
        }
    )
    
    # Create position manager with mocked dependencies
    mock_service = MagicMock()
    mock_service.ibkr_manager.get_client = AsyncMock(return_value=mock_ibkr_client)
    mock_service.db = firestore_client
    mock_service.alert_manager.create_alert = AsyncMock()
    mock_service.active_followers = {test_follower.id: True}
    
    position_manager = PositionManager(mock_service)
    
    # Run daily position check
    results = await position_manager.check_all_positions()
    
    # Verify results
    assert test_follower.id in results
    assert results[test_follower.id]["assignment_detected"] is True
    assert results[test_follower.id]["compensated"] is True
    
    # Verify position was updated in Firestore
    position_doc = firestore_client.document(
        f"positions/{test_follower.id}/daily/{test_position.date}"
    ).get()
    assert position_doc.exists
    
    position_data = position_doc.to_dict()
    assert position_data["assignmentState"] == AssignmentState.COMPENSATED.value
    
    # Verify alerts were created
    assert mock_service.alert_manager.create_alert.call_count == 2  # Two alerts: detection and compensation
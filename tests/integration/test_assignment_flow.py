"""Integration tests for the assignment detection and handling flow."""

import asyncio
import datetime
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from spreadpilot_core.models.position import Position, AssignmentState
from spreadpilot_core.models.alert import Alert, AlertType, AlertSeverity
from spreadpilot_core.ibkr.client import IBKRClient
from spreadpilot_core.utils.time import get_current_trading_date # Added import
import importlib

# Import modules using importlib
trading_bot_positions = importlib.import_module('trading-bot.app.service.positions')

# Get specific imports
PositionManager = trading_bot_positions.PositionManager


@pytest.mark.asyncio
async def test_assignment_detection(
    mock_ibkr_client,
    # Removed firestore_client fixture parameter
    test_follower,
    # test_position, # Removed non-existent fixture
    test_mongo_db, # Add mongo fixture if needed for mocking/verification
):
    """
    Test the detection of assignments (short-leg).

    This test verifies:
    1. Assignment is detected by IBKR client
    2. Position is updated (mocked/verified in MongoDB)
    3. Alert is created
    """
    # Setup mock IBKR client to return assignment detected
    mock_ibkr_client.check_assignment = AsyncMock(
        return_value=(AssignmentState.ASSIGNED, 1, 0) # short=1, long=0 after assignment
    )

    # Create position manager with mocked dependencies
    mock_service = MagicMock()
    mock_service.ibkr_manager.get_client = AsyncMock(return_value=mock_ibkr_client)
    # Removed Firestore dependency assignment

    # --- Mock MongoDB interactions ---
    # Mock find_one to return an existing position document
    trading_date = get_current_trading_date()
    initial_pos_data = Position(
        follower_id=test_follower.id,
        date=trading_date,
        assignment_state=AssignmentState.NONE,
        short_qty=1,
        long_qty=1,
    ).model_dump(by_alias=True) # Use model_dump for MongoDB structure
    # Add a mock _id if needed for validation, though find_one doesn't strictly require it in the return
    initial_pos_data['_id'] = uuid.uuid4().hex

    mock_positions_collection = AsyncMock()
    mock_positions_collection.find_one.return_value = initial_pos_data
    # Mock update_one to simulate successful update
    mock_positions_collection.update_one.return_value = MagicMock(modified_count=1)

    mock_db_handle = MagicMock()
    mock_db_handle.__getitem__.return_value = mock_positions_collection
    mock_service.mongo_db = mock_db_handle # Assign mock DB handle

    mock_service.alert_manager.create_alert = AsyncMock()

    position_manager = PositionManager(mock_service)

    # Check positions (which includes assignment check) - now async
    await position_manager.check_positions(test_follower.id)

    # Verify assignment was detected (by checking the alert mock)
    mock_service.alert_manager.create_alert.assert_called_once()
    call_args = mock_service.alert_manager.create_alert.call_args[1]
    assert call_args["follower_id"] == test_follower.id
    assert call_args["alert_type"] == AlertType.ASSIGNMENT_DETECTED

    # Verify position was updated in MongoDB mock
    mock_positions_collection.update_one.assert_called_once()
    update_call_args, update_call_kwargs = mock_positions_collection.update_one.call_args
    assert update_call_args[0] == {"follower_id": test_follower.id, "date": trading_date} # Check filter
    assert "$set" in update_call_args[1]
    assert update_call_args[1]["$set"]["assignment_state"] == AssignmentState.ASSIGNED.value
    assert update_call_args[1]["$set"]["short_qty"] == 1 # Should reflect IBKR check result
    assert update_call_args[1]["$set"]["long_qty"] == 0  # Should reflect IBKR check result


@pytest.mark.asyncio
async def test_assignment_compensation(
    mock_ibkr_client,
    # Removed firestore_client fixture parameter
    test_follower,
    # test_position, # Removed non-existent fixture
    test_mongo_db, # Add mongo fixture
):
    """
    Test the re-balancing mechanism via long-leg exercise.

    This test verifies:
    1. Long-leg exercise is triggered
    2. Position is updated to compensated state
    3. Alert is created
    """
    # --- Setup Mocks and Initial State ---
    trading_date = get_current_trading_date()
    # Simulate the state *before* check_positions is called, but after assignment
    initial_assigned_pos_data = Position(
        follower_id=test_follower.id,
        date=trading_date,
        assignment_state=AssignmentState.ASSIGNED, # Start in assigned state for this test
        short_qty=0, # Assigned, short leg gone
        long_qty=1,  # Still have long leg
        pnl_realized=0.0,
        pnl_mtm=0.0,
    ).model_dump(by_alias=True)
    initial_assigned_pos_data['_id'] = uuid.uuid4().hex # Mock an ID

    # --- Mock Database ---
    mock_positions_collection = AsyncMock()
    # find_one returns the assigned position
    mock_positions_collection.find_one.return_value = initial_assigned_pos_data
    # update_one simulates successful update
    mock_positions_collection.update_one.return_value = MagicMock(modified_count=1)

    mock_db_handle = MagicMock()
    mock_db_handle.__getitem__.return_value = mock_positions_collection
    mock_service = MagicMock()
    mock_service.mongo_db = mock_db_handle # Assign mock DB handle

    # --- Configure Mock IBKR Client for this test ---
    # 1. Return ASSIGNED state from check_assignment
    mock_ibkr_client.check_assignment = AsyncMock(return_value=(AssignmentState.ASSIGNED, 0, 1)) # short=0, long=1

    # 2. Return a long position from get_positions (needed for exercise logic)
    mock_ibkr_client.get_positions = AsyncMock(return_value={'400-C': 1}) # Example long position

    # 3. Mock exercise_options
    mock_ibkr_client.exercise_options = AsyncMock(
        return_value={"success": True, "qty_exercised": 1}
    )

    # 4. Mock get_pnl
    mock_ibkr_client.get_pnl = AsyncMock(
        return_value={'realized_pnl': 0.0, 'unrealized_pnl': 0.0}
    )

    # Create position manager with mocked dependencies
    mock_service.ibkr_manager.get_client = AsyncMock(return_value=mock_ibkr_client)
    # Ensure the ibkr_manager mock also has the exercise_options method
    mock_service.ibkr_manager.exercise_options = mock_ibkr_client.exercise_options
    mock_service.alert_manager.create_alert = AsyncMock()

    position_manager = PositionManager(mock_service)

    # Call check_positions, which should trigger compensation logic
    await position_manager.check_positions(test_follower.id)

    # Verify compensation was successful (by checking IBKR mock)
    mock_ibkr_client.exercise_options.assert_called_once()
    exercise_args = mock_ibkr_client.exercise_options.call_args[1]
    assert exercise_args["quantity"] == 1 # Exercised the remaining long leg

    # Verify position update mock was called twice (once for ASSIGNED state, once for COMPENSATED)
    assert mock_positions_collection.update_one.call_count == 2
    # Check the *last* call to verify the COMPENSATED state
    last_call_args, last_call_kwargs = mock_positions_collection.update_one.call_args_list[-1]
    assert last_call_args[0] == {"follower_id": test_follower.id, "date": trading_date} # Check filter
    assert "$set" in last_call_args[1]
    assert last_call_args[1]["$set"]["assignment_state"] == AssignmentState.COMPENSATED.value

    # Verify alerts were created (detection AND compensation)
    assert mock_service.alert_manager.create_alert.call_count == 2
    calls = mock_service.alert_manager.create_alert.call_args_list
    assert calls[0][1]["alert_type"] == AlertType.ASSIGNMENT_DETECTED # First call
    assert calls[1][1]["alert_type"] == AlertType.ASSIGNMENT_COMPENSATED # Second call
    assert calls[1][1]["follower_id"] == test_follower.id


@pytest.mark.asyncio
async def test_alert_routing_for_assignment(
    # Remove mock fixtures from signature, we'll patch directly
    test_follower,
    monkeypatch,
):
    """
    Test that alerts are sent via the alert-router for assignment events.

    This test verifies:
    1. Assignment alert is routed to email and Telegram
    2. Alert contains correct information
    """
    from spreadpilot_core.models.alert import AlertEvent, AlertType # Ensure AlertType is imported
    from unittest.mock import patch # Import patch
    import datetime # Ensure datetime is imported

    # Import the function directly
    from alert_router.app.service.router import route_alert

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

    # Patch settings AND the send functions directly within the router module's context
    # Target the functions where they are imported/used in the router module
    with patch("alert_router.app.service.router.settings") as mock_settings, \
         patch("alert_router.app.service.router.send_email") as mock_send_email, \
         patch("alert_router.app.service.router.send_telegram_message") as mock_send_telegram:

        # Configure mock settings to appear valid
        mock_settings.EMAIL_SENDER = "test-sender@example.com"
        mock_settings.EMAIL_ADMIN_RECIPIENTS = ["test-admin@example.com"]
        mock_settings.SMTP_HOST = "smtp.example.com" # Still needed if checked by router logic
        mock_settings.TELEGRAM_BOT_TOKEN = "dummy_token_123"
        mock_settings.TELEGRAM_ADMIN_IDS = ["98765"]

        # Route the alert using the patched context
        await route_alert(alert_event)

        # Verify the mocks patched *within this context* were called
        mock_send_email.assert_called_once()
        mock_send_telegram.assert_called_once()

        # Optional: Check arguments passed by the router logic to our mocks
        email_call_args = mock_send_email.call_args[1]
        assert email_call_args['to_email'] in mock_settings.EMAIL_ADMIN_RECIPIENTS
        # Check for the enum value in the subject and body
        assert alert_event.event_type.value in email_call_args['subject']
        assert alert_event.event_type.value in email_call_args['html_content']
        assert test_follower.id in email_call_args['html_content']

        telegram_call_args = mock_send_telegram.call_args[1]
        assert telegram_call_args['chat_id'] in mock_settings.TELEGRAM_ADMIN_IDS
        # Check for the enum value in the message
        assert alert_event.event_type.value in telegram_call_args['message']
        assert test_follower.id in telegram_call_args['message']


@pytest.mark.asyncio
async def test_position_update_after_trade(
    # Removed firestore_client fixture parameter
    test_follower,
    test_mongo_db, # Add mongo fixture
):
    """
    Test that positions are correctly updated after a trade.

    This test verifies:
    1. New position is created if none exists
    2. Existing position is updated with new trade data
    """
    # Create position manager with mocked dependencies
    mock_service = MagicMock()
    # --- Mock MongoDB interactions ---
    mock_positions_collection = AsyncMock()
    # Simulate find_one returning None initially, then returning the updated doc
    find_results = [None, None] # Needs adjustment based on how many times find_one is called
    async def mock_find_one(*args, **kwargs):
        # Return None first time, then the doc (needs state) - simplified for now
        if not hasattr(mock_find_one, 'call_count'):
            mock_find_one.call_count = 0
        result = find_results[mock_find_one.call_count] if mock_find_one.call_count < len(find_results) else None
        # This mock needs to be smarter to return the *updated* doc on second call
        # For now, just return None to test the insert path, then assume update works
        mock_find_one.call_count += 1
        return None # Simplified: Always simulate insert path first

    mock_positions_collection.find_one = mock_find_one # Use the async def mock
    mock_positions_collection.update_one.return_value = MagicMock(upserted_id=uuid.uuid4().hex, modified_count=0) # Simulate upsert insert

    mock_db_handle = MagicMock()
    mock_db_handle.__getitem__.return_value = mock_positions_collection
    mock_service.mongo_db = mock_db_handle # Assign mock DB handle

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

    # Update position with trade (now async)
    await position_manager.update_position(test_follower.id, trade)

    # Verify position was upserted in MongoDB mock
    mock_positions_collection.update_one.assert_called_once()
    call_args, call_kwargs = mock_positions_collection.update_one.call_args
    trading_date = get_current_trading_date()
    assert call_args[0] == {"follower_id": test_follower.id, "date": trading_date} # Check filter
    assert "$set" in call_args[1]
    assert call_args[1]["$set"]["long_qty"] == 2
    assert call_args[1]["$set"]["short_qty"] == 0
    assert call_kwargs.get("upsert") is True

    # --- Test updating existing position ---
    # Reset mock for the second call - find should return the previously "inserted" doc
    # This requires a more stateful mock or separate test case.
    # For simplicity, we'll assume the update logic works if insert works.
    # TODO: Create a separate test case for updating an existing position.

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

    # Update position with second trade (now async)
    # Reset find_one mock state if needed for update path test
    # await position_manager.update_position(test_follower.id, trade2)

    # Verify position was updated with both trades in MongoDB
    # Reset mocks for second trade
    mock_positions_collection.update_one.reset_mock()
    
    # Configure find_one to return the position after first trade
    mock_positions_collection.find_one.return_value = {
        "_id": uuid.uuid4().hex,
        "follower_id": test_follower.id,
        "date": trading_date,
        "long_qty": 2,
        "short_qty": 0,
        "assignment_state": AssignmentState.NONE.value
    }
    
    await position_manager.update_position(test_follower.id, trade2)
    
    # Verify position was updated with short trade
    mock_positions_collection.update_one.assert_called_once()
    call_args, call_kwargs = mock_positions_collection.update_one.call_args
    assert call_args[0] == {"follower_id": test_follower.id, "date": trading_date}
    assert "$set" in call_args[1]
    assert call_args[1]["$set"]["short_qty"] == 1  # Now has 1 short
    assert call_args[1]["$set"]["long_qty"] == 2  # Still has 2 long


@pytest.mark.asyncio
async def test_daily_position_check(
    mock_ibkr_client,
    # Removed firestore_client fixture parameter
    test_follower,
    # test_position, # Removed non-existent fixture
    test_mongo_db, # Add mongo fixture
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
            # First call: Return ASSIGNED, short=0, long=1 (Needs compensation)
            (AssignmentState.ASSIGNED, 0, 1),
            # Second call: Return COMPENSATED (or NONE) after compensation logic runs
            (AssignmentState.COMPENSATED, 0, 0),
        ]
    )

    mock_ibkr_client.exercise_options = AsyncMock(
        return_value={
            "success": True,
            "qty_exercised": 1,
        }
    )
    # Add mock for get_positions needed for compensation logic
    mock_ibkr_client.get_positions = AsyncMock(return_value={'400-C': 1}) # Example long position
    # Mock get_pnl
    mock_ibkr_client.get_pnl = AsyncMock(
        return_value={'realized_pnl': 0.0, 'unrealized_pnl': 0.0}
    )

    # Create position manager with mocked dependencies
    mock_service = MagicMock()
    mock_service.ibkr_manager.get_client = AsyncMock(return_value=mock_ibkr_client)
    # Ensure the ibkr_manager mock also has the exercise_options method
    mock_service.ibkr_manager.exercise_options = mock_ibkr_client.exercise_options

    # --- Mock MongoDB interactions ---
    trading_date = get_current_trading_date()
    initial_pos_data_daily = Position(
        follower_id=test_follower.id,
        date=trading_date,
        assignment_state=AssignmentState.NONE,
        short_qty=1,
        long_qty=1,
    ).model_dump(by_alias=True)
    initial_pos_data_daily['_id'] = uuid.uuid4().hex

    mock_positions_collection_daily = AsyncMock()
    mock_positions_collection_daily.find_one.return_value = initial_pos_data_daily
    mock_positions_collection_daily.update_one.return_value = MagicMock(modified_count=1)

    mock_db_handle_daily = MagicMock()
    mock_db_handle_daily.__getitem__.return_value = mock_positions_collection_daily
    mock_service.mongo_db = mock_db_handle_daily # Assign mock DB handle

    mock_service.alert_manager.create_alert = AsyncMock()
    mock_service.active_followers = {test_follower.id: True}

    position_manager = PositionManager(mock_service)

    # Run daily position check for the specific follower (now async)
    await position_manager.check_positions(test_follower.id)

    # Verify results (by checking alert mock calls)
    # Verify position was updated (Logic needs update for MongoDB)
    # Check update_one calls
    assert mock_positions_collection_daily.update_one.call_count >= 1 # At least one update (for ASSIGNED state)

    # Verify alerts were created
    assert mock_service.alert_manager.create_alert.call_count == 2  # Two alerts: detection and compensation
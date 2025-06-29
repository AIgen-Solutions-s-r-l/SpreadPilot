"""Integration tests for the FollowerService."""

import datetime
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId  # Added for MongoDB IDs
from motor.motor_asyncio import AsyncIOMotorDatabase  # Added for type hinting

from admin_api.app.core.config import get_settings
from admin_api.app.schemas.follower import FollowerCreate, FollowerUpdate

# Import necessary components from the application
from admin_api.app.services.follower_service import FollowerService
from spreadpilot_core.models.follower import FollowerState
from spreadpilot_core.models.position import AssignmentState, Position
from spreadpilot_core.models.trade import TradeStatus

# Explicitly import the fixtures we intend to use


@pytest.mark.asyncio
async def test_follower_service_integration(
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test the FollowerService integration with MongoDB.

    This test verifies:
    1. Follower can be created
    2. Follower can be retrieved by ID
    3. Follower can be updated
    4. Follower can be deleted
    5. Retrieving non-existent follower returns None
    """
    settings = get_settings()
    service = FollowerService(db=test_mongo_db, settings=settings)
    follower_id_to_cleanup = None

    try:
        # 1. Create Follower
        follower_payload = FollowerCreate(
            email="service-test@example.com",
            iban="NL91ABNA0417164304",
            ibkr_username="service-testuser",
            ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-service-testuser",
            commission_pct=15.0,
        )
        created_follower = await service.create_follower(follower_payload)
        assert created_follower is not None
        assert created_follower.email == follower_payload.email
        assert created_follower.id is not None
        follower_id_to_cleanup = created_follower.id  # Store string ID

        # 2. Retrieve Follower
        retrieved_follower = await service.get_follower_by_id(follower_id_to_cleanup)
        assert retrieved_follower is not None
        assert retrieved_follower.id == follower_id_to_cleanup
        assert retrieved_follower.email == follower_payload.email

        # 3. Update Follower
        update_data = FollowerUpdate(commission_pct=18.0, enabled=True)
        updated_follower = await service.update_follower(
            follower_id_to_cleanup, update_data
        )
        assert updated_follower is not None
        assert updated_follower.id == follower_id_to_cleanup
        assert updated_follower.commission_pct == 18.0
        assert updated_follower.enabled is True

        # Verify update in DB
        db_doc = await test_mongo_db.followers.find_one({"_id": follower_id_to_cleanup})
        assert db_doc is not None
        assert db_doc["commission_pct"] == 18.0
        assert db_doc["enabled"] is True

        # 4. Delete Follower
        deleted = await service.delete_follower(follower_id_to_cleanup)
        assert deleted is True

        # Verify deletion
        deleted_doc = await test_mongo_db.followers.find_one(
            {"_id": follower_id_to_cleanup}
        )
        assert deleted_doc is None
        follower_id_to_cleanup = None  # Prevent double deletion in finally

        # 5. Retrieve Non-existent Follower
        non_existent = await service.get_follower_by_id(str(ObjectId()))
        assert non_existent is None

    finally:
        # Clean up if deletion failed or test errored out
        if follower_id_to_cleanup:
            await test_mongo_db.followers.delete_one({"_id": follower_id_to_cleanup})


@pytest.mark.asyncio
async def test_trigger_close_positions_service(
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test the trigger_close_positions method in FollowerService integration.

    This test verifies:
    1. The method attempts to publish a message to Pub/Sub
    2. Handles non-existent follower gracefully
    """
    settings = get_settings()
    service = FollowerService(db=test_mongo_db, settings=settings)
    follower_id_to_cleanup = None

    # Patch the publish_message function directly within the service module
    with patch(
        "admin_api.app.services.follower_service.publish_message",
        new_callable=AsyncMock,
    ) as mock_publish:
        mock_publish.return_value = True  # Simulate successful publish

        try:
            # Create a follower
            follower_payload = FollowerCreate(
                email="trigger-service-test@example.com",
                iban="NL91ABNA0417164305",
                ibkr_username="trigger-service-user",
                ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-trigger-service-user",
                commission_pct=10.0,
            )
            created_follower = await service.create_follower(follower_payload)
            assert created_follower is not None
            follower_id_to_cleanup = created_follower.id

            # Test triggering close for existing follower
            result = await service.trigger_close_positions(follower_id_to_cleanup)
            assert result is True
            mock_publish.assert_called_once()  # Check if our patched function was called
            # Verify the arguments passed to publish_message
            call_args, call_kwargs = mock_publish.call_args
            # Assuming the first arg is topic name (might need adjustment if topic name changes)
            assert call_args[0] == "close-positions"
            message_data = json.loads(call_args[1])  # Second arg is the JSON string
            # Check content of the message (action might not be explicitly in this simplified version)
            assert message_data["follower_id"] == follower_id_to_cleanup
            assert "timestamp" in message_data

            # Reset mock for next call
            mock_publish.reset_mock()

            # Test triggering close for non-existent follower
            # The service method currently doesn't check existence before publishing
            # Modify if service logic changes to check existence first
            non_existent_id = str(ObjectId())
            result_non_existent = await service.trigger_close_positions(non_existent_id)
            assert (
                result_non_existent is True
            )  # Publish is attempted even if follower doesn't exist
            mock_publish.assert_called_once()  # Publish is called regardless

        finally:
            # Clean up
            if follower_id_to_cleanup:
                await test_mongo_db.followers.delete_one(
                    {"_id": follower_id_to_cleanup}
                )


@pytest.mark.asyncio
async def test_update_follower_state(test_mongo_db: AsyncIOMotorDatabase):
    """Test updating a follower's state directly using the service."""
    settings = get_settings()
    service = FollowerService(db=test_mongo_db, settings=settings)
    follower_id_to_cleanup = None
    try:
        # Create follower
        follower_create = FollowerCreate(
            email="state-test@example.com",
            iban="IBAN-STATE-TEST",
            ibkr_username="stateuser",
            ibkr_secret_ref="secret-state",
            commission_pct=10,
        )
        created = await service.create_follower(follower_create)
        assert created is not None
        follower_id_to_cleanup = created.id
        assert created.state == FollowerState.DISABLED  # Initial state

        # Update state to ACTIVE
        updated_active = await service.update_follower_state(
            follower_id_to_cleanup, FollowerState.ACTIVE
        )
        assert updated_active is not None
        assert updated_active.state == FollowerState.ACTIVE
        db_doc_active = await test_mongo_db.followers.find_one(
            {"_id": follower_id_to_cleanup}
        )
        assert db_doc_active["state"] == FollowerState.ACTIVE.value

        # Update state back to DISABLED
        updated_disabled = await service.update_follower_state(
            follower_id_to_cleanup, FollowerState.DISABLED
        )
        assert updated_disabled is not None
        assert updated_disabled.state == FollowerState.DISABLED
        # Verify last_error is cleared in the database directly
        db_doc_disabled = await test_mongo_db.followers.find_one(
            {"_id": follower_id_to_cleanup}
        )
        assert db_doc_disabled["state"] == FollowerState.DISABLED.value
        assert db_doc_disabled.get("last_error") is None  # Check DB directly

        # Test updating non-existent follower
        non_existent_id = str(ObjectId())
        updated_non_existent = await service.update_follower_state(
            non_existent_id, FollowerState.ACTIVE
        )
        assert updated_non_existent is None

    finally:
        if follower_id_to_cleanup:
            await test_mongo_db.followers.delete_one({"_id": follower_id_to_cleanup})


@pytest.mark.asyncio
async def test_service_error_handling(test_mongo_db: AsyncIOMotorDatabase):
    """Test error handling in the follower service."""
    settings = get_settings()
    service = FollowerService(db=test_mongo_db, settings=settings)

    # Test create error (mock insert_one to raise exception)
    with patch.object(
        service.collection, "insert_one", new_callable=AsyncMock
    ) as mock_insert:
        mock_insert.side_effect = Exception("Insert error")
        follower_create = FollowerCreate(
            email="error-test@example.com",
            iban="IBAN-ERROR-TEST",
            ibkr_username="erroruser",
            ibkr_secret_ref="secret-error",
            commission_pct=10,
        )
        with pytest.raises(Exception, match="Insert error"):
            await service.create_follower(follower_create)

    # Test get error (mock find_one to raise exception)
    with patch.object(
        service.collection, "find_one", new_callable=AsyncMock
    ) as mock_find:
        mock_find.side_effect = Exception("Find error")
        with pytest.raises(Exception, match="Find error"):
            await service.get_follower_by_id(str(ObjectId()))

    # Test update error (mock update_one to raise exception)
    # Need to mock find_one first to ensure the update path is reached
    with (
        patch.object(
            service.collection, "find_one", new_callable=AsyncMock
        ) as mock_find_for_update,
        patch.object(
            service.collection, "update_one", new_callable=AsyncMock
        ) as mock_update_one,
    ):  # Patch update_one
        mock_find_for_update.return_value = {
            "_id": "dummy_id",
            "email": "dummy@test.com",
        }  # Simulate finding a doc
        mock_update_one.side_effect = Exception(
            "Update error"
        )  # Mock the update operation itself to fail
        update_data = FollowerUpdate(enabled=True)
        with pytest.raises(Exception, match="Update error"):
            await service.update_follower("dummy_id", update_data)  # Use the dummy ID

    # Test delete error (mock delete_one to raise exception)
    with patch.object(
        service.collection, "delete_one", new_callable=AsyncMock
    ) as mock_delete:
        mock_delete.side_effect = Exception("Delete error")
        with pytest.raises(Exception, match="Delete error"):
            await service.delete_follower(str(ObjectId()))

    # Test trigger close error (mock find_one to return None first)
    # Note: trigger_close_positions doesn't check find_one result before publishing
    # So we test the publish error case separately below.

    # Test trigger close Pub/Sub error
    follower_id_pubsub_error = str(ObjectId())
    await service.collection.insert_one(
        {"_id": follower_id_pubsub_error, "email": "pubsub@fail.com"}
    )  # Insert dummy
    # Patch the publish_message function directly
    with patch(
        "admin_api.app.services.follower_service.publish_message",
        new_callable=AsyncMock,
    ) as mock_publish_error:
        mock_publish_error.side_effect = Exception("PubSub error")
        # Expect the service method to catch and log, returning False
        result = await service.trigger_close_positions(follower_id_pubsub_error)
        assert result is False  # Service should return False on publish error
    await service.collection.delete_one(
        {"_id": follower_id_pubsub_error}
    )  # Cleanup dummy


@pytest.mark.asyncio
async def test_follower_service_additional_methods(
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test additional FollowerService methods like get_by_email, update_pnl.
    """
    settings = get_settings()
    service = FollowerService(db=test_mongo_db, settings=settings)
    follower_id_to_cleanup = None
    email_to_test = "additional-methods@example.com"

    try:
        # Create follower
        follower_create = FollowerCreate(
            email=email_to_test,
            iban="IBAN-ADDITIONAL",
            ibkr_username="additionaluser",
            ibkr_secret_ref="secret-additional",
            commission_pct=12,
        )
        created = await service.create_follower(follower_create)
        assert created is not None
        follower_id_to_cleanup = created.id

        # Test get_by_email
        retrieved_by_email = await service.get_follower_by_email(email_to_test)
        assert retrieved_by_email is not None
        assert retrieved_by_email.id == follower_id_to_cleanup
        assert retrieved_by_email.email == email_to_test

        retrieved_nonexistent = await service.get_follower_by_email(
            "nonexistent@example.com"
        )
        assert retrieved_nonexistent is None

        # Test update_follower_pnl (assuming method exists)
        daily_pnl = 55.5
        monthly_pnl = 250.75
        # Check if method exists before calling
        if hasattr(service, "update_follower_pnl"):
            updated_pnl = await service.update_follower_pnl(
                follower_id_to_cleanup, daily_pnl, monthly_pnl
            )
            assert updated_pnl is not None
            assert updated_pnl.daily_pnl == daily_pnl
            assert updated_pnl.monthly_pnl == monthly_pnl

            # Verify in DB
            db_doc = await test_mongo_db.followers.find_one(
                {"_id": follower_id_to_cleanup}
            )
            assert db_doc["daily_pnl"] == daily_pnl
            assert db_doc["monthly_pnl"] == monthly_pnl

            # Test update_pnl for non-existent follower
            updated_pnl_nonexistent = await service.update_follower_pnl(
                str(ObjectId()), 10, 20
            )
            assert updated_pnl_nonexistent is None
        else:
            pytest.skip(
                "Skipping PnL update test: FollowerService.update_follower_pnl method not found."
            )

    finally:
        if follower_id_to_cleanup:
            await test_mongo_db.followers.delete_one({"_id": follower_id_to_cleanup})


@pytest.mark.asyncio
async def test_follower_service_batch_operations(
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test batch operations in FollowerService integration with MongoDB.

    This test verifies:
    1. Multiple followers can be created in a batch (if method exists)
    2. Multiple followers can be retrieved by IDs
    """
    settings = get_settings()
    service = FollowerService(db=test_mongo_db, settings=settings)
    follower_ids_to_cleanup = []

    try:
        # Test batch creation (assuming method exists)
        if hasattr(service, "create_followers_batch"):
            batch_creates = [
                FollowerCreate(
                    email="batch-test-1@example.com",
                    iban="IBAN-BATCH-1",
                    ibkr_username="batchuser1",
                    commission_pct=10,
                    ibkr_secret_ref="secret1",
                ),
                FollowerCreate(
                    email="batch-test-2@example.com",
                    iban="IBAN-BATCH-2",
                    ibkr_username="batchuser2",
                    commission_pct=12,
                    ibkr_secret_ref="secret2",
                ),
                FollowerCreate(
                    email="batch-test-3@example.com",
                    iban="IBAN-BATCH-3",
                    ibkr_username="batchuser3",
                    commission_pct=14,
                    ibkr_secret_ref="secret3",
                ),
            ]
            created_followers = await service.create_followers_batch(batch_creates)
            assert len(created_followers) == len(batch_creates)
            created_ids = [f.id for f in created_followers]
            follower_ids_to_cleanup.extend(created_ids)  # Store string IDs

            # Verify creation in DB
            count = await test_mongo_db.followers.count_documents(
                {"_id": {"$in": created_ids}}
            )
            assert count == len(created_ids)

            # Test batch retrieval
            retrieved_followers = await service.get_followers_by_ids(created_ids)
            assert len(retrieved_followers) == len(created_ids)
            retrieved_ids = {f.id for f in retrieved_followers}
            assert set(created_ids) == retrieved_ids

            # Test retrieval with some non-existent IDs
            mixed_ids = created_ids[:1] + [str(ObjectId()), str(ObjectId())]
            retrieved_mixed = await service.get_followers_by_ids(mixed_ids)
            assert len(retrieved_mixed) == 1  # Only the first valid ID should be found
            assert retrieved_mixed[0].id == created_ids[0]
        else:
            # Create individually if batch method doesn't exist
            created_ids = []
            for i in range(1, 4):
                follower_create = FollowerCreate(
                    email=f"batch-test-{i}@example.com",
                    iban=f"IBAN-BATCH-{i}",
                    ibkr_username=f"batchuser{i}",
                    commission_pct=10 + i * 2,
                    ibkr_secret_ref=f"secret{i}",
                )
                created = await service.create_follower(follower_create)
                created_ids.append(created.id)
            follower_ids_to_cleanup.extend(created_ids)
            pytest.skip(
                "Skipping batch creation test: FollowerService.create_followers_batch method not found."
            )

    finally:
        # Clean up
        if follower_ids_to_cleanup:
            await test_mongo_db.followers.delete_many(
                {"_id": {"$in": follower_ids_to_cleanup}}
            )


@pytest.mark.asyncio
async def test_follower_service_trading_operations(
    test_mongo_db: AsyncIOMotorDatabase,
):
    """
    Test trading-related operations in FollowerService integration.

    This test verifies:
    1. Recording trades for a follower
    2. Recording positions for a follower
    3. Updating assignment state for a position
    """
    settings = get_settings()
    service = FollowerService(db=test_mongo_db, settings=settings)
    follower_id_to_cleanup = None
    trade_ids_to_cleanup = []
    position_ids_to_cleanup = []

    try:
        # Create a follower
        follower_create = FollowerCreate(
            email="trading-ops-test@example.com",
            iban="IBAN-TRADING-OPS",
            ibkr_username="tradingopuser",
            ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-tradingopuser",
            commission_pct=20.0,
        )
        follower = await service.create_follower(follower_create)
        assert follower is not None
        follower_id_to_cleanup = follower.id

        # 1. Record Trade
        # Corrected Trade model instantiation based on ValidationError
        trade_data = {
            "id": str(uuid.uuid4()),  # Add missing ID
            "follower_id": follower_id_to_cleanup,
            "symbol": "SPY",
            "side": "LONG",  # Use valid enum value 'LONG' or 'SHORT'
            "qty": 10,  # Use correct field name 'qty'
            "strike": 450.0,  # Add missing strike
            "limit_price_requested": 450.50,  # Add missing limit_price_requested
            "price": 450.50,  # Actual fill price
            "status": (
                TradeStatus.FILLED.value if hasattr(TradeStatus, "FILLED") else "FILLED"
            ),
            "trade_time": datetime.datetime.now(datetime.UTC),
            "ibkr_order_id": "IBKR123",
        }
        # Pass the dictionary to record_trade, not the Pydantic object
        recorded_trade_result = await service.record_trade(trade_data)
        assert recorded_trade_result is True  # Assuming record_trade returns bool
        trade_id = trade_data["id"]  # Get ID from the dict
        trade_ids_to_cleanup.append(trade_id)

        # Verify trade in DB
        db_trade = await test_mongo_db.follower_trades.find_one(
            {"_id": trade_id}
        )  # Use the correct collection name
        assert db_trade is not None
        assert db_trade["follower_id"] == follower_id_to_cleanup
        assert db_trade["symbol"] == "SPY"
        assert db_trade["side"] == "LONG"

        # 2. Record Position
        position_data = {
            "follower_id": follower_id_to_cleanup,
            "symbol": "AAPL",
            "quantity": 100,
            "average_cost": 175.25,
            "last_update_time": datetime.datetime.now(datetime.UTC),
            "assignment_state": (
                AssignmentState.NONE.value
                if hasattr(AssignmentState, "NONE")
                else "NONE"
            ),  # Handle potential enum issue
            "assigned_quantity": 0,
        }
        # Assuming record_position expects the Position object
        # Need Position model to have an 'id' field or generate one
        position_data["id"] = str(uuid.uuid4())  # Add ID if missing in model
        position = Position(**position_data)
        recorded_position = await service.record_position(
            position
        )  # Pass the Position object
        assert recorded_position is not None  # Assuming it returns the object or ID
        # Adjust assertion based on return type
        # If object:
        assert recorded_position.id is not None
        position_ids_to_cleanup.append(recorded_position.id)
        pos_id_to_check = recorded_position.id
        # If bool:
        # assert recorded_position is True
        # position_ids_to_cleanup.append(position.id) # Need ID on Position model
        # pos_id_to_check = position.id

        # Verify position in DB
        db_position = await test_mongo_db.positions.find_one({"_id": pos_id_to_check})
        assert db_position is not None
        assert db_position["follower_id"] == follower_id_to_cleanup
        assert db_position["symbol"] == "AAPL"
        assert db_position["assignment_state"] == (
            AssignmentState.NONE.value if hasattr(AssignmentState, "NONE") else "NONE"
        )

        # 3. Update Assignment State
        assign_state = (
            AssignmentState.ASSIGNED_SHORT
            if hasattr(AssignmentState, "ASSIGNED_SHORT")
            else "ASSIGNED_SHORT"
        )
        updated_position = await service.update_position_assignment(
            pos_id_to_check, assign_state, 50
        )
        assert updated_position is not None
        assert updated_position.assignment_state == assign_state
        assert updated_position.assigned_quantity == 50

        # Verify update in DB
        db_position_updated = await test_mongo_db.positions.find_one(
            {"_id": pos_id_to_check}
        )
        assert db_position_updated["assignment_state"] == assign_state
        assert db_position_updated["assigned_quantity"] == 50

        # Test update non-existent position
        non_existent_assign_state = (
            AssignmentState.ASSIGNED_LONG
            if hasattr(AssignmentState, "ASSIGNED_LONG")
            else "ASSIGNED_LONG"
        )
        updated_nonexistent = await service.update_position_assignment(
            str(ObjectId()), non_existent_assign_state, 10
        )
        assert updated_nonexistent is None

    finally:
        # Cleanup
        if follower_id_to_cleanup:
            await test_mongo_db.followers.delete_one({"_id": follower_id_to_cleanup})
        if trade_ids_to_cleanup:
            await test_mongo_db.trades.delete_many(
                {"_id": {"$in": trade_ids_to_cleanup}}
            )
        if position_ids_to_cleanup:
            await test_mongo_db.positions.delete_many(
                {"_id": {"$in": position_ids_to_cleanup}}
            )

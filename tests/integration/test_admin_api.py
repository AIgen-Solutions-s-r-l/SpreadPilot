"""Integration tests for the admin API and dashboard."""

import asyncio
import datetime
import json
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from google.cloud import firestore

from spreadpilot_core.models.follower import Follower, FollowerState
from admin_api.app.schemas.follower import FollowerCreate, FollowerRead
from admin_api.app.services.follower_service import FollowerService


def test_list_followers(
    admin_api_client,
    firestore_client,
    test_follower,
):
    """
    Test listing all followers.
    
    This test verifies:
    1. Endpoint returns all followers
    2. Response format is correct
    """
    # Create additional test followers
    followers = [test_follower]
    for i in range(2):
        follower_id = f"test-follower-{uuid.uuid4()}"
        follower = Follower(
            id=follower_id,
            email=f"test{i}@example.com",
            iban=f"NL91ABNA0417164{i}00",
            ibkr_username=f"testuser{i}",
            ibkr_secret_ref=f"projects/spreadpilot-test/secrets/ibkr-password-testuser{i}",
            commission_pct=20.0,
            enabled=True,
            state=FollowerState.ACTIVE,
        )
        
        # Save to Firestore
        firestore_client.collection("followers").document(follower_id).set(follower.to_dict())
        followers.append(follower)
    
    # Mock the get_db dependency
    with patch("admin_api.app.api.v1.endpoints.followers.get_db", return_value=firestore_client):
        # Mock the get_settings dependency
        with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
            # Call the endpoint
            response = admin_api_client.get("/api/v1/followers")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= len(followers)  # May include other followers from previous tests
    
    # Verify each follower is in the response
    follower_ids = [f["id"] for f in data]
    for follower in followers:
        assert follower.id in follower_ids
    
    # Clean up additional test followers
    for follower in followers[1:]:  # Skip the first one (test_follower)
        firestore_client.collection("followers").document(follower.id).delete()


def test_create_follower(
    admin_api_client,
    firestore_client,
):
    """
    Test creating a new follower.
    
    This test verifies:
    1. Follower is created with correct data
    2. Response contains the created follower
    3. Follower is stored in Firestore
    """
    # Create follower data
    follower_data = {
        "email": "new@example.com",
        "iban": "NL91ABNA0417164300",
        "ibkr_username": "newuser",
        "ibkr_secret_ref": "projects/spreadpilot-test/secrets/ibkr-password-newuser",
        "commission_pct": 25.0,
    }
    
    # Mock the get_db dependency
    with patch("admin_api.app.api.v1.endpoints.followers.get_db", return_value=firestore_client):
        # Mock the get_settings dependency
        with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
            # Call the endpoint
            response = admin_api_client.post(
                "/api/v1/followers",
                json=follower_data,
            )
    
    # Verify response
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == follower_data["email"]
    assert data["iban"] == follower_data["iban"]
    assert data["ibkr_username"] == follower_data["ibkr_username"]
    assert data["commission_pct"] == follower_data["commission_pct"]
    assert data["enabled"] is False  # Default value
    assert data["state"] == FollowerState.DISABLED.value  # Default value
    
    # Verify follower was stored in Firestore
    follower_id = data["id"]
    follower_doc = firestore_client.collection("followers").document(follower_id).get()
    assert follower_doc.exists
    
    # Clean up
    firestore_client.collection("followers").document(follower_id).delete()


def test_toggle_follower(
    admin_api_client,
    firestore_client,
    test_follower,
):
    """
    Test toggling a follower's enabled status.
    
    This test verifies:
    1. Follower's enabled status is toggled
    2. Response contains the updated follower
    3. Follower is updated in Firestore
    """
    # Get initial enabled status
    initial_enabled = test_follower.enabled
    
    # Mock the get_db dependency
    with patch("admin_api.app.api.v1.endpoints.followers.get_db", return_value=firestore_client):
        # Mock the get_settings dependency
        with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
            # Call the endpoint
            response = admin_api_client.post(f"/api/v1/followers/{test_follower.id}/toggle")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_follower.id
    assert data["enabled"] is not initial_enabled  # Should be toggled
    
    # Verify follower was updated in Firestore
    follower_doc = firestore_client.collection("followers").document(test_follower.id).get()
    follower_data = follower_doc.to_dict()
    assert follower_data["enabled"] is not initial_enabled
    
    # Toggle back to original state
    with patch("admin_api.app.api.v1.endpoints.followers.get_db", return_value=firestore_client):
        with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
            admin_api_client.post(f"/api/v1/followers/{test_follower.id}/toggle")


def test_toggle_nonexistent_follower(
    admin_api_client,
    firestore_client,
):
    """
    Test toggling a non-existent follower.
    
    This test verifies:
    1. Appropriate error is returned
    2. Status code is 404
    """
    # Generate a random follower ID that doesn't exist
    nonexistent_id = f"nonexistent-{uuid.uuid4()}"
    
    # Mock the get_db dependency
    with patch("admin_api.app.api.v1.endpoints.followers.get_db", return_value=firestore_client):
        # Mock the get_settings dependency
        with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
            # Call the endpoint
            response = admin_api_client.post(f"/api/v1/followers/{nonexistent_id}/toggle")
    
    # Verify response
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_trigger_close_positions(
    admin_api_client,
    firestore_client,
    test_follower,
):
    """
    Test triggering close positions for a follower.
    
    This test verifies:
    1. Close positions command is triggered
    2. Response indicates success
    """
    # Mock the follower service's trigger_close_positions method
    with patch("admin_api.app.services.follower_service.FollowerService.trigger_close_positions", 
               new_callable=AsyncMock) as mock_trigger:
        mock_trigger.return_value = True
        
        # Mock the get_db dependency
        with patch("admin_api.app.api.v1.endpoints.followers.get_db", return_value=firestore_client):
            # Mock the get_settings dependency
            with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
                # Call the endpoint
                response = admin_api_client.post(f"/api/v1/close/{test_follower.id}")
    
    # Verify response
    assert response.status_code == 202  # Accepted
    data = response.json()
    assert "message" in data
    assert test_follower.id in data["message"]
    
    # Verify the service method was called
    mock_trigger.assert_called_once_with(test_follower.id)


def test_trigger_close_positions_nonexistent_follower(
    admin_api_client,
    firestore_client,
):
    """
    Test triggering close positions for a non-existent follower.
    
    This test verifies:
    1. Appropriate error is returned
    2. Status code is 404
    """
    # Generate a random follower ID that doesn't exist
    nonexistent_id = f"nonexistent-{uuid.uuid4()}"
    
    # Mock the get_db dependency
    with patch("admin_api.app.api.v1.endpoints.followers.get_db", return_value=firestore_client):
        # Mock the get_settings dependency
        with patch("admin_api.app.api.v1.endpoints.followers.get_settings", return_value=MagicMock()):
            # Call the endpoint
            response = admin_api_client.post(f"/api/v1/close/{nonexistent_id}")
    
    # Verify response
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_follower_service_integration(
    firestore_client,
):
    """
    Test the FollowerService integration with Firestore.
    
    This test verifies:
    1. Followers can be created, retrieved, and updated
    2. Service methods interact correctly with Firestore
    """
    # Create a follower service instance
    service = FollowerService(db=firestore_client, settings=MagicMock())
    
    # Create a new follower
    follower_data = FollowerCreate(
        email="service-test@example.com",
        iban="NL91ABNA0417164300",
        ibkr_username="serviceuser",
        ibkr_secret_ref="projects/spreadpilot-test/secrets/ibkr-password-serviceuser",
        commission_pct=30.0,
    )
    
    # Test create_follower
    follower = asyncio.run(service.create_follower(follower_data))
    assert follower.id is not None
    assert follower.email == follower_data.email
    assert follower.enabled is False
    
    # Test get_follower_by_id
    retrieved_follower = asyncio.run(service.get_follower_by_id(follower.id))
    assert retrieved_follower is not None
    assert retrieved_follower.id == follower.id
    assert retrieved_follower.email == follower.email
    
    # Test toggle_follower_enabled
    updated_follower = asyncio.run(service.toggle_follower_enabled(follower.id))
    assert updated_follower is not None
    assert updated_follower.enabled is True
    
    # Test get_followers
    followers = asyncio.run(service.get_followers())
    assert len(followers) >= 1
    assert any(f.id == follower.id for f in followers)
    
    # Clean up
    firestore_client.collection("followers").document(follower.id).delete()


@pytest.mark.asyncio
async def test_trigger_close_positions_service(
    firestore_client,
    test_follower,
):
    """
    Test the service method for triggering close positions.
    
    This test verifies:
    1. Service method communicates with trading-bot
    2. Command is properly formatted and sent
    """
    # Mock the publish_message method
    with patch("admin_api.app.services.follower_service.publish_message", new_callable=AsyncMock) as mock_publish:
        mock_publish.return_value = True
        
        # Create service instance
        service = FollowerService(db=firestore_client, settings=MagicMock())
        
        # Call the method
        result = await service.trigger_close_positions(test_follower.id)
        
        # Verify result
        assert result is True
        
        # Verify publish_message was called with correct arguments
        mock_publish.assert_called_once()
        args = mock_publish.call_args[0]
        assert args[0] == "close-positions"  # Topic
        message = json.loads(args[1])  # Message
        assert message["follower_id"] == test_follower.id
        assert "timestamp" in message
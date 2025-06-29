"""Unit tests for backoff alert router."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.service.backoff_router import BackoffAlertRouter
from spreadpilot_core.models.alert import AlertEvent, AlertType


@pytest.fixture
def sample_alert_event():
    """Create a sample alert event for testing."""
    return AlertEvent(
        event_type=AlertType.COMPONENT_DOWN,
        timestamp=datetime(2025, 6, 28, 12, 0, 0),
        message="Trading Bot is not responding",
        params={
            "component_name": "trading-bot",
            "last_heartbeat": "2025-06-28T11:45:00Z",
            "attempts": 3
        }
    )


@pytest.fixture
def backoff_router():
    """Create a backoff router instance."""
    return BackoffAlertRouter(
        mongo_url="mongodb://localhost:27017",
        mongo_db="test_db",
        base_delay=0.1,  # Short delay for tests
        max_retries=3,
        backoff_factor=2.0
    )


class TestBackoffAlertRouter:
    """Test cases for BackoffAlertRouter."""
    
    @pytest.mark.asyncio
    async def test_connect_disconnect(self, backoff_router):
        """Test MongoDB connection and disconnection."""
        with patch('app.service.backoff_router.AsyncIOMotorClient') as mock_client_class:
            mock_client = Mock()
            mock_client.close = Mock()
            mock_client_class.return_value = mock_client
            
            await backoff_router.connect()
            assert backoff_router.mongo_client == mock_client
            
            await backoff_router.disconnect()
            mock_client.close.assert_called_once()
            assert backoff_router.mongo_client is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self, backoff_router):
        """Test async context manager functionality."""
        with patch('app.service.backoff_router.AsyncIOMotorClient') as mock_client_class:
            mock_client = Mock()
            mock_client.close = Mock()
            mock_client_class.return_value = mock_client
            
            # Mock alert router
            mock_alert_router = AsyncMock()
            backoff_router.alert_router = mock_alert_router
            
            async with backoff_router as router:
                assert router.mongo_client == mock_client
                mock_alert_router.__aenter__.assert_called_once()
            
            mock_alert_router.__aexit__.assert_called_once()
            mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_alert_attempt(self, backoff_router, sample_alert_event):
        """Test saving alert attempt to MongoDB."""
        # Mock MongoDB
        mock_collection = AsyncMock()
        mock_db = Mock()
        mock_db.alert_attempts = mock_collection
        mock_client = Mock()
        mock_client.__getitem__ = Mock(return_value=mock_db)
        backoff_router.mongo_client = mock_client
        
        await backoff_router.save_alert_attempt(
            sample_alert_event,
            attempt=1,
            success=True,
            results={"telegram": {"success": 1}}
        )
        
        mock_collection.insert_one.assert_called_once()
        document = mock_collection.insert_one.call_args[0][0]
        
        assert document["event_type"] == "COMPONENT_DOWN"
        assert document["attempt"] == 1
        assert document["success"] is True
        assert document["status"] == "success"
        assert document["results"] == {"telegram": {"success": 1}}
    
    @pytest.mark.asyncio
    async def test_save_alert_attempt_failed_final(self, backoff_router, sample_alert_event):
        """Test saving final failed attempt."""
        # Mock MongoDB
        mock_collection = AsyncMock()
        mock_db = Mock()
        mock_db.alert_attempts = mock_collection
        mock_client = Mock()
        mock_client.__getitem__ = Mock(return_value=mock_db)
        backoff_router.mongo_client = mock_client
        
        await backoff_router.save_alert_attempt(
            sample_alert_event,
            attempt=3,  # Max retries
            success=False,
            error="Connection timeout"
        )
        
        document = mock_collection.insert_one.call_args[0][0]
        assert document["status"] == "failed"
        assert document["error"] == "Connection timeout"
    
    @pytest.mark.asyncio
    async def test_mark_alert_failed(self, backoff_router, sample_alert_event):
        """Test marking alert as permanently failed."""
        # Mock MongoDB
        mock_collection = AsyncMock()
        mock_db = Mock()
        mock_db.failed_alerts = mock_collection
        mock_client = Mock()
        mock_client.__getitem__ = Mock(return_value=mock_db)
        backoff_router.mongo_client = mock_client
        
        await backoff_router.mark_alert_failed(
            sample_alert_event,
            "All retries exhausted"
        )
        
        mock_collection.insert_one.assert_called_once()
        document = mock_collection.insert_one.call_args[0][0]
        
        assert document["event_type"] == "COMPONENT_DOWN"
        assert document["final_error"] == "All retries exhausted"
        assert document["total_attempts"] == 3
    
    @pytest.mark.asyncio
    async def test_route_alert_with_backoff_success_first_try(self, backoff_router, sample_alert_event):
        """Test successful routing on first attempt."""
        # Mock alert router
        mock_alert_router = AsyncMock()
        mock_alert_router.route_alert = AsyncMock(return_value={"success": True})
        backoff_router.alert_router = mock_alert_router
        
        # Mock MongoDB
        mock_collection = AsyncMock()
        mock_db = Mock()
        mock_db.alert_attempts = mock_collection
        mock_client = Mock()
        mock_client.__getitem__ = Mock(return_value=mock_db)
        backoff_router.mongo_client = mock_client
        
        result = await backoff_router.route_alert_with_backoff(sample_alert_event)
        
        assert result == {"success": True}
        mock_alert_router.route_alert.assert_called_once_with(sample_alert_event)
        
        # Should save successful attempt
        mock_collection.insert_one.assert_called_once()
        document = mock_collection.insert_one.call_args[0][0]
        assert document["attempt"] == 1
        assert document["success"] is True
    
    @pytest.mark.asyncio
    async def test_route_alert_with_backoff_retry_then_success(self, backoff_router, sample_alert_event):
        """Test routing with retry then success."""
        # Mock alert router to fail once then succeed
        mock_alert_router = AsyncMock()
        mock_alert_router.route_alert = AsyncMock(
            side_effect=[
                Exception("Connection error"),
                {"success": True}
            ]
        )
        backoff_router.alert_router = mock_alert_router
        
        # Mock MongoDB
        mock_attempts_collection = AsyncMock()
        mock_db = Mock()
        mock_db.alert_attempts = mock_attempts_collection
        mock_client = Mock()
        mock_client.__getitem__ = Mock(return_value=mock_db)
        backoff_router.mongo_client = mock_client
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await backoff_router.route_alert_with_backoff(sample_alert_event)
        
        assert result == {"success": True}
        assert mock_alert_router.route_alert.call_count == 2
        
        # Should have saved both attempts
        assert mock_attempts_collection.insert_one.call_count == 2
        
        # Check backoff delay
        mock_sleep.assert_called_once_with(0.1)  # base_delay * backoff_factor^0
    
    @pytest.mark.asyncio
    async def test_route_alert_with_backoff_all_retries_fail(self, backoff_router, sample_alert_event):
        """Test routing when all retries fail."""
        # Mock alert router to always fail
        mock_alert_router = AsyncMock()
        mock_alert_router.route_alert = AsyncMock(side_effect=Exception("Persistent error"))
        backoff_router.alert_router = mock_alert_router
        
        # Mock MongoDB
        mock_attempts_collection = AsyncMock()
        mock_failed_collection = AsyncMock()
        mock_db = Mock()
        mock_db.alert_attempts = mock_attempts_collection
        mock_db.failed_alerts = mock_failed_collection
        mock_client = Mock()
        mock_client.__getitem__ = Mock(return_value=mock_db)
        backoff_router.mongo_client = mock_client
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(Exception, match="Failed to route alert after 3 attempts"):
                await backoff_router.route_alert_with_backoff(sample_alert_event)
        
        assert mock_alert_router.route_alert.call_count == 3
        
        # Should have saved all attempts
        assert mock_attempts_collection.insert_one.call_count == 3
        
        # Should have marked as failed
        mock_failed_collection.insert_one.assert_called_once()
        
        # Check exponential backoff delays
        assert mock_sleep.call_count == 2  # No sleep after last attempt
        mock_sleep.assert_any_call(0.1)   # base_delay * 2^0
        mock_sleep.assert_any_call(0.2)   # base_delay * 2^1
    
    @pytest.mark.asyncio
    async def test_route_alert_without_mongo(self, backoff_router, sample_alert_event):
        """Test routing without MongoDB connection still works."""
        # No MongoDB client
        backoff_router.mongo_client = None
        
        # Mock alert router
        mock_alert_router = AsyncMock()
        mock_alert_router.route_alert = AsyncMock(return_value={"success": True})
        backoff_router.alert_router = mock_alert_router
        
        result = await backoff_router.route_alert_with_backoff(sample_alert_event)
        
        assert result == {"success": True}
        mock_alert_router.route_alert.assert_called_once_with(sample_alert_event)
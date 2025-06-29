"""Unit tests for Time Value Monitor service with fake IB client."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from ib_insync import Contract, MarketOrder, Stock, Ticker

from spreadpilot_core.models.alert import AlertType, AlertSeverity
from spreadpilot_core.models.position import Position, PositionState
from trading_bot.app.service.time_value_monitor import TimeValueMonitor


class MockService:
    """Mock trading service for testing."""
    
    def __init__(self):
        self.mongo_db = {"positions": AsyncMock(), "alerts": AsyncMock()}
        self.ibkr_manager = Mock()
        self.ibkr_manager.get_client = AsyncMock()


class FakeIBClient:
    """Fake IB client for testing."""
    
    def __init__(self):
        self.placed_orders = []
        self.market_data_requests = []
        self.qualified_contracts = []
        
    def reqMktData(self, contract, genericTickList, snapshot, regulatorySnapshot):
        """Fake market data request."""
        self.market_data_requests.append(contract)
        
        ticker = Ticker()
        if isinstance(contract, Stock):
            # Underlying price
            ticker.last = 450.0
            ticker.bid = 449.95
            ticker.ask = 450.05
        else:
            # Option spread prices
            ticker.bid = 1.20
            ticker.ask = 1.30
            ticker.last = 1.25
            
        return ticker
        
    def cancelMktData(self, contract):
        """Fake cancel market data."""
        pass
        
    def qualifyContracts(self, *contracts):
        """Fake contract qualification."""
        for i, contract in enumerate(contracts):
            contract.conId = i + 1
            self.qualified_contracts.append(contract)
            
    def placeOrder(self, contract, order):
        """Fake order placement."""
        trade = Mock()
        trade.orderStatus = Mock()
        trade.orderStatus.status = "Submitted"
        trade.contract = contract
        trade.order = order
        
        self.placed_orders.append((contract, order))
        return trade


@pytest.fixture
def mock_service():
    """Fixture for mock service."""
    return MockService()


@pytest.fixture
def fake_ib_client():
    """Fixture for fake IB client."""
    return FakeIBClient()


@pytest.fixture
def time_value_monitor(mock_service):
    """Fixture for TimeValueMonitor instance."""
    return TimeValueMonitor(service=mock_service)


class TestTimeValueMonitorService:
    """Test TimeValueMonitor functionality with service integration."""
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, time_value_monitor):
        """Test starting and stopping the monitor."""
        # Start monitor
        await time_value_monitor.start_monitoring()
        assert time_value_monitor._running is True
        assert time_value_monitor._task is not None
        
        # Stop monitor
        await time_value_monitor.stop_monitoring()
        assert time_value_monitor._running is False
        
    @pytest.mark.asyncio
    async def test_calculate_intrinsic_value_bull_put(self, time_value_monitor, mock_service, fake_ib_client):
        """Test intrinsic value calculation for Bull Put spread."""
        # Setup IB client mock
        mock_service.ibkr_manager.get_client.return_value = fake_ib_client
        
        # Create position for Bull Put spread QQQ 440/445 Put
        position = Position(
            id="pos123",
            follower_id="follower1",
            symbol="QQQ 240103P440/445",
            strategy_type="BULL_PUT",
            position_type="SPREAD",
            quantity=1,
            state=PositionState.OPEN,
            date="20240103",
            created_at=datetime.now(timezone.utc),
        )
        
        intrinsic_value = await time_value_monitor._calculate_intrinsic_value(position)
        
        # Both puts OTM (underlying at 450), intrinsic value = 0
        assert intrinsic_value == 0
        
    @pytest.mark.asyncio
    async def test_calculate_time_value(self, time_value_monitor, mock_service, fake_ib_client):
        """Test time value calculation."""
        # Setup IB client mock
        mock_service.ibkr_manager.get_client.return_value = fake_ib_client
        
        # Create position
        position = Position(
            id="pos125",
            follower_id="follower1", 
            symbol="QQQ 240103P440/445",
            strategy_type="BULL_PUT",
            position_type="SPREAD",
            quantity=1,
            state=PositionState.OPEN,
            date="20240103",
            created_at=datetime.now(timezone.utc),
        )
        
        # Calculate time value
        # Market price = 1.25, Intrinsic = 0
        # Time value = (1.25 - 0) * 100 = $125
        time_value = await time_value_monitor._calculate_time_value(position)
        
        assert time_value == 125.0
        assert len(fake_ib_client.market_data_requests) == 2  # Spread + underlying
        
    @pytest.mark.asyncio
    async def test_close_position_market_order(self, time_value_monitor, mock_service, fake_ib_client):
        """Test closing a position with market order."""
        # Setup IB client mock
        mock_service.ibkr_manager.get_client.return_value = fake_ib_client
        
        position = Position(
            id="pos126",
            follower_id="follower1",
            symbol="QQQ 240103P440/445",
            strategy_type="BULL_PUT",
            position_type="SPREAD",
            quantity=2,
            state=PositionState.OPEN,
            date="20240103",
            created_at=datetime.now(timezone.utc),
        )
        
        success = await time_value_monitor._close_position(position)
        
        assert success is True
        assert len(fake_ib_client.placed_orders) == 1
        
        contract, order = fake_ib_client.placed_orders[0]
        assert order.action == "SELL"  # Close Bull Put by selling
        assert order.totalQuantity == 2
        assert isinstance(order, MarketOrder)
        
    @pytest.mark.asyncio
    async def test_check_position_below_threshold_publishes_alert(self, time_value_monitor, mock_service):
        """Test checking position with time value below threshold publishes alert."""
        position = Position(
            id="pos128",
            follower_id="follower1",
            symbol="QQQ 240103P440/445",
            strategy_type="BULL_PUT",
            position_type="SPREAD",
            quantity=1,
            state=PositionState.OPEN,
            date="20240103",
            created_at=datetime.now(timezone.utc),
        )
        
        # Mock time value calculation to return 0.05 (below threshold)
        with patch.object(
            time_value_monitor, "_calculate_time_value", return_value=0.05
        ):
            with patch.object(
                time_value_monitor, "_close_position", return_value=True
            ):
                with patch.object(
                    time_value_monitor, "_publish_redis_alert"
                ) as mock_redis_alert:
                    await time_value_monitor._check_position_time_value(position)
                    
                    # Should publish Redis alert
                    mock_redis_alert.assert_called_once()
                    alert_data = mock_redis_alert.call_args[0][0]
                    assert alert_data["reason"] == "TIME_VALUE_THRESHOLD"
                    assert alert_data["time_value"] == 0.05
                    assert alert_data["success"] is True
                    
    @pytest.mark.asyncio
    async def test_redis_alert_publishing(self, time_value_monitor):
        """Test Redis alert publishing."""
        # Mock Redis client
        time_value_monitor.redis_client = AsyncMock()
        
        alert_data = {
            "type": AlertType.CRITICAL.value,
            "reason": "TIME_VALUE_THRESHOLD",
            "follower_id": "follower1",
            "position_id": "pos123",
            "time_value": 0.05,
            "threshold": 0.10,
            "action": "AUTO_CLOSE",
            "success": True,
            "timestamp": datetime.now(timezone.utc),
        }
        
        await time_value_monitor._publish_redis_alert(alert_data)
        
        # Check Redis xadd was called
        time_value_monitor.redis_client.xadd.assert_called_once()
        call_args = time_value_monitor.redis_client.xadd.call_args
        assert call_args[0][0] == "alerts"
        
        # Check alert data structure
        alert_json = call_args[0][1]["data"]
        assert "TIME_VALUE_THRESHOLD" in alert_json
        assert "CRITICAL" in alert_json
        
    @pytest.mark.asyncio
    async def test_monitor_loop_handles_errors(self, time_value_monitor):
        """Test that monitor loop handles errors gracefully."""
        # Mock check to raise error
        with patch.object(
            time_value_monitor, "_check_all_positions",
            side_effect=Exception("Test error")
        ):
            # Start monitor
            await time_value_monitor.start_monitoring()
            
            # Let it run briefly
            await asyncio.sleep(0.1)
            
            # Should still be running despite error
            assert time_value_monitor._running is True
            
            # Stop monitor
            await time_value_monitor.stop_monitoring()
            
    @pytest.mark.asyncio
    async def test_check_all_positions_with_mongodb(self, time_value_monitor, mock_service):
        """Test checking all open positions from MongoDB."""
        # Mock positions data
        positions_data = [
            {
                "_id": "pos130",
                "follower_id": "follower1",
                "symbol": "QQQ 240103P440/445",
                "strategy_type": "BULL_PUT",
                "position_type": "SPREAD",
                "quantity": 1,
                "state": "OPEN",
                "date": "20240103",
                "created_at": datetime.now(timezone.utc),
            },
            {
                "_id": "pos131",
                "follower_id": "follower2",
                "symbol": "QQQ 240103C455/460",
                "strategy_type": "BEAR_CALL",
                "position_type": "SPREAD",
                "quantity": 2,
                "state": "OPEN",
                "date": "20240103",
                "created_at": datetime.now(timezone.utc),
            },
        ]
        
        # Mock cursor
        class MockCursor:
            def __init__(self, data):
                self.data = data
                self.index = 0
                
            def __aiter__(self):
                return self
                
            async def __anext__(self):
                if self.index >= len(self.data):
                    raise StopAsyncIteration
                item = self.data[self.index]
                self.index += 1
                return item
                
        positions_collection = mock_service.mongo_db["positions"]
        positions_collection.find.return_value = MockCursor(positions_data)
        
        with patch.object(
            time_value_monitor, "_check_position_time_value"
        ) as mock_check:
            await time_value_monitor._check_all_positions()
            
            # Should check both positions
            assert mock_check.call_count == 2
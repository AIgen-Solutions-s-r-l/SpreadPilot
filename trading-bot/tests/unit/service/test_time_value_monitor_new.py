"""Unit tests for TimeValueMonitor with fake IB client."""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import fakeredis
import pytest
from ib_insync import Contract, MarketOrder, Stock, Ticker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "../../../../../spreadpilot-core")
)

from app.service.time_value_monitor import TimeValueMonitor

from spreadpilot_core.models.alert import AlertSeverity, AlertType
from spreadpilot_core.models.position import Position, PositionState


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
async def time_value_monitor(mock_service):
    """Fixture for TimeValueMonitor instance."""
    monitor = TimeValueMonitor(service=mock_service)
    
    # Mock Redis client
    monitor.redis_client = fakeredis.FakeAsyncRedis(decode_responses=False)
    
    yield monitor
    
    # Cleanup
    await monitor.redis_client.aclose()


class TestTimeValueMonitor:
    """Test TimeValueMonitor functionality."""
    
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
    async def test_calculate_intrinsic_value_bear_call(self, time_value_monitor, mock_service, fake_ib_client):
        """Test intrinsic value calculation for Bear Call spread."""
        # Setup IB client mock
        mock_service.ibkr_manager.get_client.return_value = fake_ib_client
        
        # Create position for Bear Call spread QQQ 455/460 Call
        position = Position(
            id="pos124",
            follower_id="follower1",
            symbol="QQQ 240103C455/460",
            strategy_type="BEAR_CALL",
            position_type="SPREAD",
            quantity=1,
            state=PositionState.OPEN,
            date="20240103",
            created_at=datetime.now(timezone.utc),
        )
        
        intrinsic_value = await time_value_monitor._calculate_intrinsic_value(position)
        
        # Both calls OTM (underlying at 450), intrinsic value = 0
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
    async def test_close_position_bull_put(self, time_value_monitor, mock_service, fake_ib_client):
        """Test closing a Bull Put position."""
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
    async def test_close_position_bear_call(self, time_value_monitor, mock_service, fake_ib_client):
        """Test closing a Bear Call position."""
        # Setup IB client mock
        mock_service.ibkr_manager.get_client.return_value = fake_ib_client
        
        position = Position(
            id="pos127",
            follower_id="follower1",
            symbol="QQQ 240103C455/460",
            strategy_type="BEAR_CALL",
            position_type="SPREAD",
            quantity=3,
            state=PositionState.OPEN,
            date="20240103",
            created_at=datetime.now(timezone.utc),
        )
        
        success = await time_value_monitor._close_position(position)
        
        assert success is True
        assert len(fake_ib_client.placed_orders) == 1
        
        contract, order = fake_ib_client.placed_orders[0]
        assert order.action == "BUY"  # Close Bear Call by buying
        assert order.totalQuantity == 3
        assert isinstance(order, MarketOrder)
        
    @pytest.mark.asyncio
    async def test_check_position_below_threshold(self, time_value_monitor, mock_service):
        """Test checking position with time value below threshold."""
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
            ) as mock_close:
                await time_value_monitor._check_position_time_value(position)
                
                # Should trigger close
                mock_close.assert_called_once_with(position)
                
                # Should publish alert to MongoDB
                alerts_collection = mock_service.mongo_db["alerts"]
                alerts_collection.insert_one.assert_called_once()
                
                # Check Redis alert was published
                redis_data = await time_value_monitor.redis_client.xrange("alerts", count=1)
                assert len(redis_data) == 1
                
    @pytest.mark.asyncio
    async def test_check_position_above_threshold(self, time_value_monitor, mock_service, fake_ib_client):
        """Test checking position with time value above threshold."""
        # Setup IB client mock
        mock_service.ibkr_manager.get_client.return_value = fake_ib_client
        
        position = Position(
            id="pos129",
            follower_id="follower1",
            symbol="QQQ 240103P440/445",
            strategy_type="BULL_PUT",
            position_type="SPREAD",
            quantity=1,
            state=PositionState.OPEN,
            date="20240103",
            created_at=datetime.now(timezone.utc),
        )
        
        # Mock time value calculation to return 1.50 (above threshold)
        with patch.object(
            time_value_monitor, "_calculate_time_value", return_value=1.50
        ):
            with patch.object(
                time_value_monitor, "_close_position"
            ) as mock_close:
                await time_value_monitor._check_position_time_value(position)
                
                # Should NOT trigger close
                mock_close.assert_not_called()
                
    @pytest.mark.asyncio
    async def test_intrinsic_value_partially_itm(self, time_value_monitor, mock_service):
        """Test intrinsic value calculation for partially ITM spreads."""
        # Create fake IB client with custom underlying price
        fake_ib = FakeIBClient()
        
        # Override underlying price
        original_req = fake_ib.reqMktData
        def custom_req(contract, *args):
            ticker = original_req(contract, *args)
            if isinstance(contract, Stock):
                ticker.last = 442.0  # Between strikes
            return ticker
        fake_ib.reqMktData = custom_req
        
        mock_service.ibkr_manager.get_client.return_value = fake_ib
        
        # Bull Put spread 440/445, underlying at 442 (partially ITM)
        position = Position(
            id="pos133",
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
        
        # Intrinsic = short_strike - underlying = 445 - 442 = 3
        assert intrinsic_value == 3.0
        
    @pytest.mark.asyncio
    async def test_redis_alert_format(self, time_value_monitor):
        """Test Redis alert is published in correct format."""
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
        
        # Read from Redis stream
        messages = await time_value_monitor.redis_client.xrange("alerts")
        assert len(messages) == 1
        
        # Parse message
        msg_id, data = messages[0]
        alert_json = json.loads(data[b"data"].decode())
        
        assert alert_json["alert_type"] == "ASSIGNMENT_DETECTED"
        assert alert_json["severity"] == "CRITICAL"
        assert alert_json["follower_id"] == "follower1"
        assert alert_json["details"]["reason"] == "TIME_VALUE_THRESHOLD"
        assert alert_json["details"]["time_value"] == 0.05
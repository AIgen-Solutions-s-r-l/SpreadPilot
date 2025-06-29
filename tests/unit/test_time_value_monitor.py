"""Unit tests for Time Value Monitor with fake IB client."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from ib_insync import Contract, MarketOrder, Stock, Ticker

from spreadpilot_core.models.alert import AlertType
from spreadpilot_core.models.position import Position, PositionState
from trading_bot.app.service.time_value_monitor import TimeValueMonitor


class FakeIB:
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
        for contract in contracts:
            contract.conId = len(self.qualified_contracts) + 1
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
def fake_ib():
    """Fixture for fake IB client."""
    return FakeIB()


@pytest.fixture
def mock_db():
    """Fixture for mock database."""
    db = AsyncMock()
    
    # Mock collections
    positions_collection = AsyncMock()
    alerts_collection = AsyncMock()
    
    db.__getitem__.side_effect = lambda name: {
        "positions": positions_collection,
        "alerts": alerts_collection,
    }[name]
    
    return db


@pytest.fixture
def time_value_monitor(mock_db, fake_ib):
    """Fixture for TimeValueMonitor instance."""
    return TimeValueMonitor(
        db=mock_db,
        ib_client=fake_ib,
        time_value_threshold=0.10,
        check_interval=60,
    )


class TestTimeValueMonitor:
    """Test TimeValueMonitor functionality."""
    
    @pytest.mark.asyncio
    async def test_start_stop(self, time_value_monitor):
        """Test starting and stopping the monitor."""
        # Start monitor
        await time_value_monitor.start()
        assert time_value_monitor._running is True
        assert time_value_monitor._task is not None
        
        # Stop monitor
        await time_value_monitor.stop()
        assert time_value_monitor._running is False
        
    @pytest.mark.asyncio
    async def test_calculate_intrinsic_value_bull_put(self, time_value_monitor):
        """Test intrinsic value calculation for Bull Put spread."""
        # Create position for Bull Put spread QQQ 440/445 Put
        position = Position(
            id="pos123",
            follower_id="follower1",
            symbol="QQQ 240103P440/445",
            strategy_type="BULL_PUT",
            position_type="SPREAD",
            quantity=1,
            state=PositionState.OPEN,
            created_at=datetime.now(timezone.utc),
        )
        
        # Mock underlying at 450 (above both strikes - max profit scenario)
        with patch.object(time_value_monitor.ib, "reqMktData") as mock_req:
            ticker = Mock()
            ticker.last = 450.0
            mock_req.return_value = ticker
            
            intrinsic_value = await time_value_monitor._calculate_intrinsic_value(position)
            
            # Both puts OTM, intrinsic value = 0
            assert intrinsic_value == 0
            
    @pytest.mark.asyncio
    async def test_calculate_intrinsic_value_bear_call(self, time_value_monitor):
        """Test intrinsic value calculation for Bear Call spread."""
        # Create position for Bear Call spread QQQ 455/460 Call
        position = Position(
            id="pos124",
            follower_id="follower1",
            symbol="QQQ 240103C455/460",
            strategy_type="BEAR_CALL",
            position_type="SPREAD",
            quantity=1,
            state=PositionState.OPEN,
            created_at=datetime.now(timezone.utc),
        )
        
        # Mock underlying at 450 (below both strikes - max profit scenario)
        with patch.object(time_value_monitor.ib, "reqMktData") as mock_req:
            ticker = Mock()
            ticker.last = 450.0
            mock_req.return_value = ticker
            
            intrinsic_value = await time_value_monitor._calculate_intrinsic_value(position)
            
            # Both calls OTM, intrinsic value = 0
            assert intrinsic_value == 0
            
    @pytest.mark.asyncio
    async def test_calculate_time_value(self, time_value_monitor, fake_ib):
        """Test time value calculation."""
        # Create position
        position = Position(
            id="pos125",
            follower_id="follower1", 
            symbol="QQQ 240103P440/445",
            strategy_type="BULL_PUT",
            position_type="SPREAD",
            quantity=1,
            state=PositionState.OPEN,
            created_at=datetime.now(timezone.utc),
        )
        
        # Calculate time value
        # Market price = 1.25, Intrinsic = 0
        # Time value = (1.25 - 0) * 100 = $125
        time_value = await time_value_monitor._calculate_time_value(position)
        
        assert time_value == 125.0
        assert len(fake_ib.market_data_requests) == 2  # Spread + underlying
        
    @pytest.mark.asyncio
    async def test_close_position_bull_put(self, time_value_monitor, fake_ib):
        """Test closing a Bull Put position."""
        position = Position(
            id="pos126",
            follower_id="follower1",
            symbol="QQQ 240103P440/445",
            strategy_type="BULL_PUT",
            position_type="SPREAD",
            quantity=2,
            state=PositionState.OPEN,
            created_at=datetime.now(timezone.utc),
        )
        
        success = await time_value_monitor._close_position(position)
        
        assert success is True
        assert len(fake_ib.placed_orders) == 1
        
        contract, order = fake_ib.placed_orders[0]
        assert order.action == "SELL"  # Close Bull Put by selling
        assert order.totalQuantity == 2
        assert isinstance(order, MarketOrder)
        
    @pytest.mark.asyncio
    async def test_close_position_bear_call(self, time_value_monitor, fake_ib):
        """Test closing a Bear Call position."""
        position = Position(
            id="pos127",
            follower_id="follower1",
            symbol="QQQ 240103C455/460",
            strategy_type="BEAR_CALL",
            position_type="SPREAD",
            quantity=3,
            state=PositionState.OPEN,
            created_at=datetime.now(timezone.utc),
        )
        
        success = await time_value_monitor._close_position(position)
        
        assert success is True
        assert len(fake_ib.placed_orders) == 1
        
        contract, order = fake_ib.placed_orders[0]
        assert order.action == "BUY"  # Close Bear Call by buying
        assert order.totalQuantity == 3
        assert isinstance(order, MarketOrder)
        
    @pytest.mark.asyncio
    async def test_check_position_below_threshold(self, time_value_monitor, mock_db):
        """Test checking position with time value below threshold."""
        position = Position(
            id="pos128",
            follower_id="follower1",
            symbol="QQQ 240103P440/445",
            strategy_type="BULL_PUT",
            position_type="SPREAD",
            quantity=1,
            state=PositionState.OPEN,
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
                
                # Should publish alert
                alerts_collection = mock_db["alerts"]
                alerts_collection.insert_one.assert_called_once()
                
                alert_data = alerts_collection.insert_one.call_args[0][0]
                assert alert_data["type"] == AlertType.CRITICAL.value
                assert alert_data["reason"] == "TIME_VALUE_THRESHOLD"
                assert alert_data["details"]["time_value"] == 0.05
                assert alert_data["details"]["action"] == "AUTO_CLOSE"
                assert alert_data["details"]["success"] is True
                
    @pytest.mark.asyncio
    async def test_check_position_above_threshold(self, time_value_monitor):
        """Test checking position with time value above threshold."""
        position = Position(
            id="pos129",
            follower_id="follower1",
            symbol="QQQ 240103P440/445",
            strategy_type="BULL_PUT",
            position_type="SPREAD",
            quantity=1,
            state=PositionState.OPEN,
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
    async def test_check_all_positions(self, time_value_monitor, mock_db):
        """Test checking all open positions."""
        # Mock positions
        positions_data = [
            {
                "_id": "pos130",
                "follower_id": "follower1",
                "symbol": "QQQ 240103P440/445",
                "strategy_type": "BULL_PUT",
                "position_type": "SPREAD",
                "quantity": 1,
                "state": "OPEN",
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
                
        positions_collection = mock_db["positions"]
        positions_collection.find.return_value = MockCursor(positions_data)
        
        with patch.object(
            time_value_monitor, "_check_position_time_value"
        ) as mock_check:
            await time_value_monitor._check_all_positions()
            
            # Should check both positions
            assert mock_check.call_count == 2
            
    @pytest.mark.asyncio
    async def test_update_position_state(self, time_value_monitor, mock_db):
        """Test updating position state in database."""
        position = Position(
            id="pos132",
            follower_id="follower1",
            symbol="QQQ 240103P440/445",
            strategy_type="BULL_PUT",
            position_type="SPREAD",
            quantity=1,
            state=PositionState.OPEN,
            created_at=datetime.now(timezone.utc),
        )
        
        await time_value_monitor._update_position_state(
            position, PositionState.CLOSING
        )
        
        positions_collection = mock_db["positions"]
        positions_collection.update_one.assert_called_once()
        
        # Check update query
        query, update = positions_collection.update_one.call_args[0]
        assert query["_id"] == "pos132"
        assert update["$set"]["state"] == PositionState.CLOSING.value
        assert "updated_at" in update["$set"]
        
    @pytest.mark.asyncio
    async def test_monitor_loop_handles_errors(self, time_value_monitor):
        """Test that monitor loop handles errors gracefully."""
        # Mock check to raise error
        with patch.object(
            time_value_monitor, "_check_all_positions",
            side_effect=Exception("Test error")
        ):
            # Start monitor
            await time_value_monitor.start()
            
            # Let it run briefly
            await asyncio.sleep(0.1)
            
            # Should still be running despite error
            assert time_value_monitor._running is True
            
            # Stop monitor
            await time_value_monitor.stop()
            
    @pytest.mark.asyncio
    async def test_intrinsic_value_partially_itm(self, time_value_monitor):
        """Test intrinsic value calculation for partially ITM spreads."""
        # Bull Put spread 440/445, underlying at 442 (partially ITM)
        position = Position(
            id="pos133",
            follower_id="follower1",
            symbol="QQQ 240103P440/445",
            strategy_type="BULL_PUT",
            position_type="SPREAD",
            quantity=1,
            state=PositionState.OPEN,
            created_at=datetime.now(timezone.utc),
        )
        
        with patch.object(time_value_monitor.ib, "reqMktData") as mock_req:
            ticker = Mock()
            ticker.last = 442.0  # Between strikes
            mock_req.return_value = ticker
            
            intrinsic_value = await time_value_monitor._calculate_intrinsic_value(position)
            
            # Intrinsic = short_strike - underlying = 445 - 442 = 3
            assert intrinsic_value == 3.0
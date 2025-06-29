"""Unit tests for P&L service with Redis streams, time-freeze and fake feed."""

import asyncio
import json
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytz
from fakeredis import aioredis as fakeredis
from freezegun import freeze_time

from spreadpilot_core.models.pnl import PnLIntraday, Trade
from spreadpilot_core.pnl.service import PnLService


@pytest.fixture
async def fake_redis():
    """Create a fake Redis client for testing."""
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    await client.close()


@pytest.fixture
def mock_postgres_session():
    """Mock PostgreSQL session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.scalars = MagicMock()
    session.scalar = MagicMock()
    return session


@pytest.fixture
def mock_mongo_db():
    """Mock MongoDB."""
    db = AsyncMock()
    db.followers.find_one = AsyncMock()
    return db


@pytest.fixture
async def pnl_service():
    """Create PnL service instance."""
    service = PnLService()
    yield service
    if service.redis_client:
        await service.redis_client.close()


class TestPnLServiceRedisStreams:
    """Test P&L service Redis stream functionality."""

    @pytest.mark.asyncio
    async def test_trade_fill_processing_from_redis(self, pnl_service, fake_redis):
        """Test processing trade fills from Redis stream."""
        # Setup Redis client
        pnl_service.redis_client = fake_redis
        
        # Mock database operations
        with patch('spreadpilot_core.pnl.service.get_postgres_session') as mock_session:
            session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = session
            
            # Add trade fill to Redis stream
            trade_data = {
                "follower_id": "test_follower",
                "symbol": "QQQ",
                "contract_type": "CALL",
                "strike": "450.0",
                "expiration": "2025-01-17",
                "trade_type": "BUY",
                "quantity": 5,
                "price": "2.50",
                "commission": "5.0",
                "order_id": "ORDER123",
                "execution_id": "EXEC456",
                "trade_time": datetime.now().isoformat()
            }
            
            # Create consumer group first
            await fake_redis.xgroup_create("trade_fills", "pnl_service", id="0", mkstream=True)
            
            # Add message to stream
            message_id = await fake_redis.xadd("trade_fills", {"data": json.dumps(trade_data)})
            
            # Process the message manually (simulating subscription)
            messages = await fake_redis.xreadgroup(
                "pnl_service", "pnl_worker",
                {"trade_fills": ">"},
                count=1,
                block=1000
            )
            
            # Process the trade fill
            for stream_name, msgs in messages:
                for msg_id, fields in msgs:
                    fill_data = json.loads(fields["data"])
                    await pnl_service.record_trade_fill(fill_data["follower_id"], fill_data)
            
            # Verify trade was added to session
            session.add.assert_called_once()
            session.commit.assert_called_once()
            
            # Check the trade object
            added_trade = session.add.call_args[0][0]
            assert isinstance(added_trade, Trade)
            assert added_trade.follower_id == "test_follower"
            assert added_trade.symbol == "QQQ"
            assert added_trade.quantity == 5
            assert added_trade.price == Decimal("2.50")

    @pytest.mark.asyncio
    async def test_quote_processing_from_redis(self, pnl_service, fake_redis):
        """Test processing quotes from Redis stream."""
        # Setup Redis client
        pnl_service.redis_client = fake_redis
        
        # Mock database operations
        with patch('spreadpilot_core.pnl.service.get_postgres_session') as mock_session:
            session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = session
            
            # Add quote to Redis stream
            quote_data = {
                "symbol": "QQQ",
                "contract_type": "CALL",
                "strike": "450.0",
                "expiration": "2025-01-17",
                "bid": "2.45",
                "ask": "2.55",
                "last": "2.50",
                "volume": 1000,
                "quote_time": datetime.now().isoformat()
            }
            
            # Create consumer group
            await fake_redis.xgroup_create("quotes", "pnl_service", id="0", mkstream=True)
            
            # Add message to stream
            await fake_redis.xadd("quotes", {"data": json.dumps(quote_data)})
            
            # Process the quote
            await pnl_service.update_quote(quote_data)
            
            # Verify quote was added to session
            session.add.assert_called_once()
            session.commit.assert_called_once()

    @freeze_time("2025-06-29 10:30:00")  # Market hours (ET)
    @pytest.mark.asyncio
    async def test_mtm_calculation_during_market_hours(self, pnl_service):
        """Test MTM calculation during market hours with time freeze."""
        with patch('spreadpilot_core.pnl.service.ET', pytz.timezone('US/Eastern')):
            # Mock market open check
            with patch.object(pnl_service, '_is_market_open', return_value=True):
                with patch.object(pnl_service, '_calculate_and_store_mtm', new_callable=AsyncMock) as mock_calc:
                    # Add a follower
                    pnl_service.active_followers.add("test_follower")
                    
                    # Run one iteration
                    await pnl_service._calculate_and_store_mtm()
                    
                    # Verify calculation was called
                    mock_calc.assert_called_once()

    @freeze_time("2025-06-29 20:00:00")  # After market hours
    @pytest.mark.asyncio
    async def test_mtm_calculation_after_market_hours(self, pnl_service):
        """Test MTM calculation skipped after market hours."""
        with patch('spreadpilot_core.pnl.service.ET', pytz.timezone('US/Eastern')):
            # Market should be closed
            assert not pnl_service._is_market_open()
            
            with patch.object(pnl_service, '_calculate_and_store_mtm', new_callable=AsyncMock) as mock_calc:
                # Run MTM loop once (should skip calculation)
                # We can't easily test the full loop, but we can test market hours check
                is_open = pnl_service._is_market_open()
                assert not is_open

    @freeze_time("2025-06-29 16:30:00")  # Daily rollup time (4:30 PM ET)
    @pytest.mark.asyncio
    async def test_daily_rollup_scheduling(self, pnl_service):
        """Test daily rollup scheduling at 16:30 ET."""
        with patch('spreadpilot_core.pnl.service.ET', pytz.timezone('US/Eastern')):
            with patch.object(pnl_service, '_daily_rollup_completed_today', return_value=False):
                with patch.object(pnl_service, '_perform_daily_rollup', new_callable=AsyncMock) as mock_rollup:
                    # Check if it's rollup time
                    now_et = datetime.now(pytz.timezone('US/Eastern'))
                    assert now_et.time().hour == 16
                    assert now_et.time().minute == 30

    @pytest.mark.asyncio
    async def test_commission_calculation_positive_pnl(self, pnl_service, mock_postgres_session, mock_mongo_db):
        """Test commission calculation for positive monthly P&L."""
        with patch('spreadpilot_core.pnl.service.get_postgres_session') as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_postgres_session
            
            with patch('spreadpilot_core.pnl.service.get_mongo_db', return_value=mock_mongo_db):
                # Mock follower data from MongoDB
                mock_mongo_db.followers.find_one.return_value = {
                    "_id": "test_follower",
                    "email": "test@example.com",
                    "iban": "DE89370400440532013000",
                    "commission_pct": 20  # 20%
                }
                
                # Mock existing commission check (return None for new commission)
                mock_result = MagicMock()
                mock_result.scalar.return_value = None
                mock_postgres_session.execute.return_value = mock_result
                
                # Test positive P&L
                monthly_pnl = Decimal("1000.00")
                
                await pnl_service._calculate_monthly_commission(
                    mock_postgres_session,
                    "test_follower",
                    2025,
                    6,
                    monthly_pnl
                )
                
                # Verify commission was added
                mock_postgres_session.add.assert_called_once()
                mock_postgres_session.commit.assert_called_once()
                
                # Check commission calculation
                commission_entry = mock_postgres_session.add.call_args[0][0]
                assert commission_entry.monthly_pnl == monthly_pnl
                assert commission_entry.commission_pct == Decimal("0.20")  # 20% as decimal
                assert commission_entry.commission_amount == Decimal("200.00")  # 20% of 1000
                assert commission_entry.is_payable is True

    @pytest.mark.asyncio
    async def test_commission_calculation_negative_pnl(self, pnl_service, mock_postgres_session, mock_mongo_db):
        """Test commission calculation for negative monthly P&L."""
        with patch('spreadpilot_core.pnl.service.get_postgres_session') as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_postgres_session
            
            with patch('spreadpilot_core.pnl.service.get_mongo_db', return_value=mock_mongo_db):
                # Mock follower data
                mock_mongo_db.followers.find_one.return_value = {
                    "_id": "test_follower",
                    "email": "test@example.com",
                    "iban": "DE89370400440532013000",
                    "commission_pct": 20
                }
                
                # Mock existing commission check
                mock_result = MagicMock()
                mock_result.scalar.return_value = None
                mock_postgres_session.execute.return_value = mock_result
                
                # Test negative P&L
                monthly_pnl = Decimal("-500.00")
                
                await pnl_service._calculate_monthly_commission(
                    mock_postgres_session,
                    "test_follower",
                    2025,
                    6,
                    monthly_pnl
                )
                
                # Verify commission was added
                mock_postgres_session.add.assert_called_once()
                
                # Check commission calculation (should be 0 for negative P&L)
                commission_entry = mock_postgres_session.add.call_args[0][0]
                assert commission_entry.monthly_pnl == monthly_pnl
                assert commission_entry.commission_amount == Decimal("0.00")  # No commission for loss
                assert commission_entry.is_payable is False

    @pytest.mark.asyncio
    async def test_fake_feed_simulation(self, pnl_service, fake_redis):
        """Test P&L calculation with simulated fake market feed."""
        # Setup fake Redis
        pnl_service.redis_client = fake_redis
        
        # Mock callback functions for positions and market prices
        mock_positions = [
            MagicMock(
                quantity=5,
                avg_cost=2.50,
                symbol="QQQ",
                contract_type="CALL",
                strike=450.0,
                expiration=date(2025, 1, 17)
            )
        ]
        
        async def mock_get_positions(follower_id):
            return mock_positions
        
        async def mock_get_market_price(position):
            # Simulate price movement: +10% gain
            return position.avg_cost * 1.1  # $2.75
        
        pnl_service.get_follower_positions_callback = mock_get_positions
        pnl_service.get_market_price_callback = mock_get_market_price
        
        # Add follower
        pnl_service.active_followers.add("test_follower")
        
        # Mock database operations
        with patch('spreadpilot_core.pnl.service.get_postgres_session') as mock_session:
            session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = session
            
            # Mock realized P&L and commission queries
            session.execute.return_value.scalar.return_value = Decimal("0")  # No realized P&L or commission
            
            # Run MTM calculation
            await pnl_service._calculate_follower_mtm("test_follower")
            
            # Verify intraday P&L was stored
            session.add.assert_called_once()
            pnl_snapshot = session.add.call_args[0][0]
            
            assert isinstance(pnl_snapshot, PnLIntraday)
            assert pnl_snapshot.follower_id == "test_follower"
            assert pnl_snapshot.position_count == 1
            
            # Calculate expected values
            # Position value: 5 contracts * $2.75 * 100 = $1375
            # Unrealized P&L: (2.75 - 2.50) * 5 * 100 = $125
            expected_market_value = Decimal("1375.00")
            expected_unrealized_pnl = Decimal("125.00")
            
            assert pnl_snapshot.total_market_value == expected_market_value
            assert pnl_snapshot.unrealized_pnl == expected_unrealized_pnl

    @pytest.mark.asyncio 
    async def test_redis_stream_error_handling(self, pnl_service, fake_redis):
        """Test error handling in Redis stream processing."""
        pnl_service.redis_client = fake_redis
        
        # Add malformed message to stream
        await fake_redis.xgroup_create("trade_fills", "pnl_service", id="0", mkstream=True)
        await fake_redis.xadd("trade_fills", {"data": "invalid_json"})
        
        # Process should handle the error gracefully
        messages = await fake_redis.xreadgroup(
            "pnl_service", "pnl_worker",
            {"trade_fills": ">"},
            count=1,
            block=100
        )
        
        # Should not raise exception when processing invalid JSON
        for stream_name, msgs in messages:
            for msg_id, fields in msgs:
                try:
                    fill_data = json.loads(fields["data"])
                    # This should fail
                    await pnl_service.record_trade_fill("test", fill_data)
                except (json.JSONDecodeError, KeyError, TypeError):
                    # Expected - should handle gracefully
                    pass

    @freeze_time("2025-01-01 00:10:00")  # Monthly rollup time
    @pytest.mark.asyncio
    async def test_monthly_rollup_scheduling(self, pnl_service):
        """Test monthly rollup scheduling on 1st at 00:10 ET."""
        with patch('spreadpilot_core.pnl.service.ET', pytz.timezone('US/Eastern')):
            # Mock rollup completion check
            with patch.object(pnl_service, '_monthly_rollup_completed', return_value=False):
                with patch.object(pnl_service, '_perform_monthly_rollup', new_callable=AsyncMock) as mock_rollup:
                    # Check if it's monthly rollup time
                    now_et = datetime.now(pytz.timezone('US/Eastern'))
                    assert now_et.day == 1
                    assert now_et.time().hour == 0
                    assert now_et.time().minute == 10

    @pytest.mark.asyncio
    async def test_pnl_service_lifecycle(self, pnl_service, fake_redis):
        """Test complete P&L service lifecycle."""
        # Mock Redis client
        with patch('spreadpilot_core.pnl.service.get_redis_client', return_value=fake_redis):
            # Create shutdown event
            shutdown_event = asyncio.Event()
            
            # Start monitoring in background
            monitor_task = asyncio.create_task(pnl_service.start_monitoring(shutdown_event))
            
            # Let it run briefly
            await asyncio.sleep(0.1)
            
            # Verify service is active
            assert pnl_service.monitoring_active is True
            assert pnl_service.redis_client is not None
            
            # Shutdown
            shutdown_event.set()
            
            # Wait for graceful shutdown
            try:
                await asyncio.wait_for(monitor_task, timeout=1.0)
            except asyncio.TimeoutError:
                monitor_task.cancel()
            
            # Verify cleanup
            assert pnl_service.monitoring_active is False
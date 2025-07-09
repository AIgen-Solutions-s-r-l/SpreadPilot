"""Unit tests for P&L service with Redis streams and rollup calculations."""

import asyncio
import datetime
from datetime import date, time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# import fakeredis.aioredis
# import freezegun
import pytest
import pytz

from spreadpilot_core.models.pnl import (
    CommissionMonthly,
    PnLDaily,
    PnLIntraday,
    PnLMonthly,
    Quote,
    Trade,
)
from spreadpilot_core.pnl.service import PnLService


@pytest.fixture
async def redis_client():
    """Create fake Redis client for testing."""
    # Mock Redis client since fakeredis is not available
    redis_mock = AsyncMock()
    redis_mock.xadd = AsyncMock()
    redis_mock.xread = AsyncMock(return_value=[])
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
async def pnl_service(redis_client):
    """Create P&L service instance with mocked dependencies."""
    service = PnLService(redis_url="redis://fake:6379")
    service.redis_client = redis_client
    
    # Mock callbacks
    service.get_follower_positions_callback = AsyncMock()
    service.get_market_price_callback = AsyncMock()
    service.subscribe_to_tick_feed_callback = AsyncMock()
    
    # Add test follower
    service.active_followers.add("test_follower")
    
    return service


@pytest.fixture
def mock_postgres_session():
    """Mock PostgreSQL session."""
    with patch("spreadpilot_core.pnl.service.get_postgres_session") as mock:
        session = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.execute = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        mock.return_value = session
        yield session


@pytest.fixture
def mock_mongo_db():
    """Mock MongoDB connection."""
    with patch("spreadpilot_core.pnl.service.get_mongo_db") as mock:
        db = AsyncMock()
        follower_doc = {
            "_id": "test_follower",
            "email": "test@example.com",
            "iban": "DE89370400440532013000",
            "commission_pct": 20,
        }
        db.followers.find_one = AsyncMock(return_value=follower_doc)
        mock.return_value = db
        yield db


class TestPnLService:
    """Test P&L service functionality."""

    @pytest.mark.asyncio
    async def test_redis_trade_fills_subscription(self, pnl_service, redis_client, mock_postgres_session):
        """Test processing trade fills from Redis stream."""
        # Add trade fill to stream
        trade_data = {
            "follower_id": "test_follower",
            "symbol": "QQQ",
            "contract_type": "CALL",
            "strike": 450.0,
            "expiration": "2024-01-19",
            "trade_type": "BUY",
            "quantity": 10,
            "price": 5.50,
            "commission": 6.50,
            "order_id": "ORD123",
            "execution_id": "EXEC456",
            "trade_time": datetime.datetime.utcnow().isoformat(),
        }
        
        import json
        await redis_client.xadd(
            "trade_fills", 
            {"trade": json.dumps(trade_data)}
        )
        
        # Create shutdown event
        shutdown_event = asyncio.Event()
        
        # Run subscription for a short time
        subscription_task = asyncio.create_task(
            pnl_service._redis_trade_fills_subscription(shutdown_event)
        )
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Stop subscription
        shutdown_event.set()
        await subscription_task
        
        # Verify trade was saved
        mock_postgres_session.add.assert_called_once()
        saved_trade = mock_postgres_session.add.call_args[0][0]
        assert isinstance(saved_trade, Trade)
        assert saved_trade.follower_id == "test_follower"
        assert saved_trade.symbol == "QQQ"
        assert saved_trade.quantity == 10

    @pytest.mark.asyncio
    async def test_redis_quotes_subscription_triggers_mtm(self, pnl_service, redis_client, mock_postgres_session):
        """Test that quote updates trigger MTM recalculation."""
        # Mock position for follower
        mock_position = Mock()
        mock_position.symbol = "QQQ"
        mock_position.contract_type = "CALL"
        mock_position.strike = Decimal("450")
        mock_position.expiration = date(2024, 1, 19)
        mock_position.quantity = 10
        mock_position.avg_cost = Decimal("5.00")
        
        pnl_service.get_follower_positions_callback.return_value = [mock_position]
        pnl_service.get_market_price_callback.return_value = Decimal("6.00")
        
        # Add quote to stream
        quote_data = {
            "symbol": "QQQ",
            "contract_type": "CALL",
            "strike": 450.0,
            "expiration": "2024-01-19",
            "bid": 5.90,
            "ask": 6.10,
            "last": 6.00,
            "volume": 1500,
            "quote_time": datetime.datetime.utcnow().isoformat(),
        }
        
        # Mock market open
        with patch.object(pnl_service, "_is_market_open", return_value=True):
            await redis_client.xadd(
                "quotes", 
                {"quote": json.dumps(quote_data)}
            )
            
            # Create shutdown event
            shutdown_event = asyncio.Event()
            
            # Run subscription for a short time
            subscription_task = asyncio.create_task(
                pnl_service._redis_quotes_subscription(shutdown_event)
            )
            
            # Wait for processing
            await asyncio.sleep(0.2)
            
            # Stop subscription
            shutdown_event.set()
            await subscription_task
        
        # Verify quote was saved and MTM was calculated
        assert mock_postgres_session.add.call_count >= 2  # Quote + PnLIntraday
        
        # Check that PnLIntraday was created
        for call in mock_postgres_session.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, PnLIntraday):
                assert obj.follower_id == "test_follower"
                assert obj.unrealized_pnl == Decimal("1000")  # (6.00 - 5.00) * 10 * 100

    @pytest.mark.asyncio
    # @freezegun.freeze_time("2024-01-15 16:30:00", tz_offset=5)  # 4:30 PM ET
    @patch("spreadpilot_core.pnl.service.datetime")
    async def test_daily_rollup_at_1630_et(self, mock_datetime, pnl_service, mock_postgres_session):
        """Test daily rollup executes at 16:30 ET."""
        # Mock datetime to be 4:30 PM ET
        mock_datetime.datetime.now.return_value = datetime.datetime(2024, 1, 15, 16, 30, 0)
        mock_datetime.datetime.utcnow.return_value = datetime.datetime(2024, 1, 15, 21, 30, 0)  # UTC
        # Mock intraday data
        mock_snapshots = []
        for i in range(10):
            snapshot = Mock(spec=PnLIntraday)
            snapshot.follower_id = "test_follower"
            snapshot.trading_date = date(2024, 1, 15)
            snapshot.snapshot_time = datetime.datetime(2024, 1, 15, 10 + i, 0)
            snapshot.realized_pnl = Decimal("100")
            snapshot.unrealized_pnl = Decimal("50") + Decimal(str(i * 10))
            snapshot.total_pnl = snapshot.realized_pnl + snapshot.unrealized_pnl
            snapshot.position_count = 5
            snapshot.total_market_value = Decimal("10000")
            snapshot.total_commission = Decimal("25")
            mock_snapshots.append(snapshot)
        
        # Mock query results
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_snapshots
        mock_result.scalar.return_value = None  # No existing daily rollup
        
        mock_postgres_session.execute.return_value = mock_result
        
        # Run daily rollup
        await pnl_service._perform_daily_rollup()
        
        # Verify daily summary was created
        daily_pnl_created = False
        for call in mock_postgres_session.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, PnLDaily):
                daily_pnl_created = True
                assert obj.follower_id == "test_follower"
                assert obj.trading_date == date(2024, 1, 15)
                assert obj.trades_count == 0  # No trades in mock
                assert obj.is_finalized is True
                break
        
        assert daily_pnl_created, "Daily P&L rollup was not created"

    @pytest.mark.asyncio
    # @freezegun.freeze_time("2024-02-01 00:10:00")  # 00:10 UTC on 1st
    @patch("spreadpilot_core.pnl.service.datetime")
    async def test_monthly_rollup_and_commission(self, mock_datetime, pnl_service, mock_postgres_session, mock_mongo_db):
        """Test monthly rollup and commission calculation."""
        # Mock datetime to be 00:10 UTC on the 1st
        mock_datetime.datetime.now.return_value = datetime.datetime(2024, 2, 1, 0, 10, 0)
        mock_datetime.datetime.utcnow.return_value = datetime.datetime(2024, 2, 1, 0, 10, 0)
        # Mock daily summaries for January
        mock_dailies = []
        total_pnl = Decimal("0")
        
        for day in range(1, 21):  # 20 trading days
            daily = Mock(spec=PnLDaily)
            daily.follower_id = "test_follower"
            daily.trading_date = date(2024, 1, day)
            daily.realized_pnl = Decimal("500")
            daily.unrealized_pnl_start = Decimal("0")
            daily.unrealized_pnl_end = Decimal("100")
            daily.total_pnl = Decimal("600")
            daily.trades_count = 10
            daily.total_volume = 100
            daily.total_commission = Decimal("50")
            daily.max_profit = Decimal("800")
            daily.max_drawdown = Decimal("-200")
            mock_dailies.append(daily)
            total_pnl += daily.total_pnl
        
        # Mock query results
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_dailies
        mock_result.scalar.return_value = None  # No existing monthly/commission
        
        mock_postgres_session.execute.return_value = mock_result
        
        # Run monthly rollup
        await pnl_service._perform_monthly_rollup()
        
        # Verify monthly summary and commission were created
        monthly_created = False
        commission_created = False
        
        for call in mock_postgres_session.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, PnLMonthly):
                monthly_created = True
                assert obj.follower_id == "test_follower"
                assert obj.year == 2024
                assert obj.month == 1
                assert obj.total_pnl == total_pnl  # 12000
                assert obj.trading_days == 20
                assert obj.winning_days == 20  # All positive in mock
                
            elif isinstance(obj, CommissionMonthly):
                commission_created = True
                assert obj.follower_id == "test_follower"
                assert obj.year == 2024
                assert obj.month == 1
                assert obj.monthly_pnl == total_pnl
                assert obj.commission_pct == Decimal("0.20")  # 20%
                assert obj.commission_amount == total_pnl * Decimal("0.20")  # 2400
                assert obj.is_payable is True  # Positive P&L
                assert obj.follower_iban == "DE89370400440532013000"
                assert obj.follower_email == "test@example.com"
        
        assert monthly_created, "Monthly P&L rollup was not created"
        assert commission_created, "Monthly commission was not created"

    @pytest.mark.asyncio
    async def test_commission_not_payable_for_negative_pnl(self, pnl_service, mock_postgres_session, mock_mongo_db):
        """Test commission is not payable when monthly P&L is negative."""
        # Create session mock
        session = mock_postgres_session
        
        # Calculate commission for negative P&L
        await pnl_service._calculate_monthly_commission(
            session,
            "test_follower",
            2024,
            1,
            Decimal("-1000")  # Negative P&L
        )
        
        # Verify commission was created but not payable
        commission_created = False
        for call in session.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, CommissionMonthly):
                commission_created = True
                assert obj.commission_amount == Decimal("0")
                assert obj.is_payable is False
                break
        
        assert commission_created, "Commission entry was not created"

    @pytest.mark.asyncio
    async def test_mtm_calculation_with_positions(self, pnl_service, mock_postgres_session):
        """Test MTM calculation with open positions."""
        # Mock positions
        position1 = Mock()
        position1.symbol = "QQQ"
        position1.quantity = 10  # Long
        position1.avg_cost = Decimal("5.00")
        
        position2 = Mock()
        position2.symbol = "QQQ"
        position2.quantity = -5  # Short
        position2.avg_cost = Decimal("6.00")
        
        pnl_service.get_follower_positions_callback.return_value = [position1, position2]
        pnl_service.get_market_price_callback.return_value = Decimal("5.50")
        
        # Mock realized P&L and commission
        with patch.object(pnl_service, "_get_realized_pnl_today", return_value=Decimal("200")):
            with patch.object(pnl_service, "_get_daily_commission", return_value=Decimal("25")):
                # Calculate MTM
                await pnl_service._calculate_follower_mtm("test_follower")
        
        # Verify intraday snapshot was created
        intraday_created = False
        for call in mock_postgres_session.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, PnLIntraday):
                intraday_created = True
                assert obj.follower_id == "test_follower"
                assert obj.realized_pnl == Decimal("200")
                # Unrealized: Long: (5.50 - 5.00) * 10 * 100 = 500
                #            Short: (6.00 - 5.50) * 5 * 100 = 250
                #            Total: 750
                assert obj.unrealized_pnl == Decimal("750")
                assert obj.total_pnl == Decimal("950")
                assert obj.position_count == 2
                assert obj.total_commission == Decimal("25")
                break
        
        assert intraday_created, "Intraday P&L snapshot was not created"

    @pytest.mark.asyncio
    async def test_get_current_pnl(self, pnl_service, mock_postgres_session):
        """Test retrieving current P&L for a follower."""
        # Mock latest snapshot
        mock_snapshot = Mock(spec=PnLIntraday)
        mock_snapshot.snapshot_time = datetime.datetime.utcnow()
        mock_snapshot.realized_pnl = Decimal("500")
        mock_snapshot.unrealized_pnl = Decimal("300")
        mock_snapshot.total_pnl = Decimal("800")
        mock_snapshot.position_count = 5
        mock_snapshot.total_market_value = Decimal("15000")
        
        mock_result = Mock()
        mock_result.scalar.return_value = mock_snapshot
        mock_postgres_session.execute.return_value = mock_result
        
        # Get current P&L
        result = await pnl_service.get_current_pnl("test_follower")
        
        assert result["follower_id"] == "test_follower"
        assert result["realized_pnl"] == 500.0
        assert result["unrealized_pnl"] == 300.0
        assert result["total_pnl"] == 800.0
        assert result["position_count"] == 5
        assert result["total_market_value"] == 15000.0

    @pytest.mark.asyncio
    async def test_get_monthly_commission(self, pnl_service, mock_postgres_session):
        """Test retrieving monthly commission details."""
        # Mock commission entry
        mock_commission = Mock(spec=CommissionMonthly)
        mock_commission.monthly_pnl = Decimal("5000")
        mock_commission.commission_pct = Decimal("0.20")
        mock_commission.commission_amount = Decimal("1000")
        mock_commission.is_payable = True
        mock_commission.is_paid = False
        mock_commission.payment_date = None
        mock_commission.payment_reference = None
        
        mock_result = Mock()
        mock_result.scalar.return_value = mock_commission
        mock_postgres_session.execute.return_value = mock_result
        
        # Get commission
        result = await pnl_service.get_monthly_commission("test_follower", 2024, 1)
        
        assert result["follower_id"] == "test_follower"
        assert result["monthly_pnl"] == 5000.0
        assert result["commission_pct"] == 20.0  # Converted to percentage
        assert result["commission_amount"] == 1000.0
        assert result["is_payable"] is True
        assert result["is_paid"] is False
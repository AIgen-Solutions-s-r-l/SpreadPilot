"""Unit tests for PnL service."""

import asyncio
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from app.service.pnl_service import PnLService


class TestPnLService:
    """Test cases for PnLService class."""

    @pytest.fixture
    def mock_trading_service(self):
        """Create a mock trading service."""
        service = MagicMock()
        service.active_followers = ["follower1", "follower2"]
        service.is_market_open.return_value = True

        # Mock IBKR manager
        service.ibkr_manager = AsyncMock()

        return service

    @pytest.fixture
    def mock_ibkr_client(self):
        """Create a mock IBKR client."""
        client = AsyncMock()
        client.get_pnl = AsyncMock(return_value=150.75)
        client.get_portfolio_value = AsyncMock(return_value=10000.00)
        return client

    @pytest.fixture
    def pnl_service(self, mock_trading_service):
        """Create a PnLService instance."""
        return PnLService(mock_trading_service)

    def test_initialization(self, pnl_service, mock_trading_service):
        """Test PnL service initialization."""
        assert pnl_service.trading_service == mock_trading_service
        assert pnl_service.monitoring_active == False
        assert pnl_service.subscriptions_active == False
        assert pnl_service.active_followers == set()
        assert pnl_service.quote_cache == {}

    @pytest.mark.asyncio
    async def test_mtm_calculation_market_closed(self, pnl_service, mock_trading_service):
        """Test MTM calculation when market is closed."""
        mock_trading_service.is_market_open.return_value = False

        with patch.object(pnl_service, "_calculate_and_store_mtm") as mock_calc:
            # Simulate one loop iteration
            shutdown_event = asyncio.Event()

            # Start the loop and stop it immediately
            task = asyncio.create_task(pnl_service._mtm_calculation_loop(shutdown_event))
            await asyncio.sleep(0.1)  # Let it start
            shutdown_event.set()

            try:
                await asyncio.wait_for(task, timeout=1.0)
            except TimeoutError:
                task.cancel()

            # Should not have called MTM calculation since market is closed
            mock_calc.assert_not_called()

    @pytest.mark.asyncio
    async def test_calculate_follower_mtm_no_client(self, pnl_service, mock_trading_service):
        """Test MTM calculation when IBKR client is not available."""
        mock_trading_service.ibkr_manager.get_client.return_value = None

        with patch("app.service.pnl_service.get_mongo_db") as mock_mongo:
            # Should exit early when no client is available
            await pnl_service._calculate_follower_mtm("follower1")

            mock_trading_service.ibkr_manager.get_client.assert_called_once_with("follower1")
            mock_mongo.assert_not_called()

    @pytest.mark.asyncio
    async def test_calculate_follower_mtm_no_positions(
        self, pnl_service, mock_trading_service, mock_ibkr_client
    ):
        """Test MTM calculation when follower has no positions."""
        mock_trading_service.ibkr_manager.get_client.return_value = mock_ibkr_client

        # Mock MongoDB to return no positions
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = None

        mock_db = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection

        with patch("app.service.pnl_service.get_mongo_db", return_value=mock_db):
            await pnl_service._calculate_follower_mtm("follower1")

            # Should have looked for positions but found none
            mock_collection.find_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_trade_fill(self, pnl_service):
        """Test recording a trade fill."""
        trade_data = {
            "symbol": "QQQ",
            "contract_type": "PUT",
            "strike": 400.0,
            "expiration": date(2024, 12, 20),
            "side": "BUY",
            "quantity": 10,
            "price": 2.50,
            "commission": 1.00,
            "order_id": "ORDER123",
            "execution_id": "EXEC456",
            "trade_time": datetime(2024, 6, 28, 14, 30, 0),
        }

        with patch("app.service.pnl_service.get_postgres_session") as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session

            await pnl_service.record_trade_fill("follower1", trade_data)

            # Should have added a trade to the session
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_count_active_positions(self, pnl_service):
        """Test counting active positions."""
        position_doc = {"long_qty": 5, "short_qty": -3}

        count = pnl_service._count_active_positions(position_doc)
        assert count == 8  # abs(5) + abs(-3)

    def test_count_active_positions_empty(self, pnl_service):
        """Test counting positions with empty document."""
        position_doc = {}

        count = pnl_service._count_active_positions(position_doc)
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_real_time_pnl_success(self, pnl_service):
        """Test getting real-time P&L data."""
        with patch("app.service.pnl_service.get_postgres_session") as mock_session_ctx:
            # Mock PnL data
            mock_pnl = MagicMock()
            mock_pnl.follower_id = "follower1"
            mock_pnl.snapshot_time = datetime(2024, 6, 28, 14, 30, 0)
            mock_pnl.realized_pnl = Decimal("100.50")
            mock_pnl.unrealized_pnl = Decimal("50.25")
            mock_pnl.total_pnl = Decimal("150.75")
            mock_pnl.position_count = 2
            mock_pnl.total_market_value = Decimal("10000.00")

            mock_result = AsyncMock()
            mock_result.scalar.return_value = mock_pnl

            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session_ctx.return_value.__aenter__.return_value = mock_session

            result = await pnl_service.get_real_time_pnl("follower1")

            assert result is not None
            assert result["follower_id"] == "follower1"
            assert result["realized_pnl"] == 100.50
            assert result["unrealized_pnl"] == 50.25
            assert result["total_pnl"] == 150.75
            assert result["position_count"] == 2

    @pytest.mark.asyncio
    async def test_get_real_time_pnl_no_data(self, pnl_service):
        """Test getting real-time P&L when no data exists."""
        with patch("app.service.pnl_service.get_postgres_session") as mock_session_ctx:
            mock_result = AsyncMock()
            mock_result.scalar.return_value = None

            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session_ctx.return_value.__aenter__.return_value = mock_session

            result = await pnl_service.get_real_time_pnl("follower1")

            assert result is None

    @pytest.mark.asyncio
    async def test_daily_rollup_completed_check(self, pnl_service):
        """Test checking if daily rollup was completed."""
        with patch("app.service.pnl_service.get_postgres_session") as mock_session_ctx:
            # Mock result indicating rollup was completed
            mock_result = AsyncMock()
            mock_result.scalar.return_value = MagicMock()  # Non-None means completed

            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session_ctx.return_value.__aenter__.return_value = mock_session

            completed = await pnl_service._daily_rollup_completed_today()

            assert completed == True

    @pytest.mark.asyncio
    async def test_monthly_rollup_completed_check(self, pnl_service):
        """Test checking if monthly rollup was completed."""
        with patch("app.service.pnl_service.get_postgres_session") as mock_session_ctx:
            # Mock result indicating no rollup completed
            mock_result = AsyncMock()
            mock_result.scalar.return_value = None

            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session_ctx.return_value.__aenter__.return_value = mock_session

            completed = await pnl_service._monthly_rollup_completed()

            assert completed == False

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, pnl_service):
        """Test stopping P&L monitoring."""
        pnl_service.monitoring_active = True
        pnl_service.subscriptions_active = True

        await pnl_service.stop_monitoring()

        assert pnl_service.monitoring_active == False
        assert pnl_service.subscriptions_active == False

    @pytest.mark.asyncio
    async def test_get_daily_commission_success(self, pnl_service):
        """Test getting daily commission total."""
        with patch("app.service.pnl_service.get_postgres_session") as mock_session_ctx:
            mock_result = AsyncMock()
            mock_result.scalar.return_value = Decimal("15.50")

            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session_ctx.return_value.__aenter__.return_value = mock_session

            commission = await pnl_service._get_daily_commission("follower1")

            assert commission == Decimal("15.50")

    @pytest.mark.asyncio
    async def test_get_daily_commission_no_trades(self, pnl_service):
        """Test getting daily commission when no trades exist."""
        with patch("app.service.pnl_service.get_postgres_session") as mock_session_ctx:
            mock_result = AsyncMock()
            mock_result.scalar.return_value = None  # No trades

            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session_ctx.return_value.__aenter__.return_value = mock_session

            commission = await pnl_service._get_daily_commission("follower1")

            assert commission == Decimal("0")

    @pytest.mark.asyncio
    async def test_calculate_market_value_success(self, pnl_service, mock_ibkr_client):
        """Test calculating market value successfully."""
        mock_ibkr_client.get_portfolio_value.return_value = 25000.75

        market_value = await pnl_service._calculate_market_value(mock_ibkr_client, {})

        assert market_value == Decimal("25000.75")

    @pytest.mark.asyncio
    async def test_calculate_market_value_error(self, pnl_service, mock_ibkr_client):
        """Test calculating market value with error."""
        mock_ibkr_client.get_portfolio_value.side_effect = Exception("IBKR Error")

        market_value = await pnl_service._calculate_market_value(mock_ibkr_client, {})

        assert market_value == Decimal("0")

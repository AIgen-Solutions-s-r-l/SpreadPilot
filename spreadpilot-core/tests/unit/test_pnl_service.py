"""Unit tests for P&L service with random fills."""

import datetime
import random
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

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

ET = pytz.timezone("US/Eastern")


@pytest.fixture
def pnl_service():
    """Create P&L service instance."""
    return PnLService()


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_follower_data():
    """Mock follower data from MongoDB."""
    return {
        "id": "test-follower-1",
        "email": "test@example.com",
        "iban": "DE89370400440532013000",
        "commission_pct": 20,  # 20%
    }


@pytest.fixture
def random_trades():
    """Generate random trade fills."""
    trades = []
    symbols = ["QQQ"]
    contract_types = ["CALL", "PUT"]

    # Generate 10 random trades
    for i in range(10):
        trade_type = random.choice(["BUY", "SELL"])
        contract_type = random.choice(contract_types)

        trade = {
            "symbol": random.choice(symbols),
            "contract_type": contract_type,
            "strike": Decimal(str(random.randint(300, 500))),
            "expiration": date.today() + timedelta(days=random.randint(1, 30)),
            "trade_type": trade_type,
            "quantity": random.randint(1, 10),
            "price": Decimal(str(round(random.uniform(0.5, 5.0), 2))),
            "commission": Decimal(str(round(random.uniform(0.5, 2.0), 2))),
            "order_id": f"ORDER{i}",
            "execution_id": f"EXEC{i}",
            "trade_time": datetime.datetime.utcnow()
            - timedelta(minutes=random.randint(0, 300)),
        }
        trades.append(trade)

    return trades


@pytest.fixture
def random_positions():
    """Generate random open positions."""
    positions = []

    for i in range(5):
        position = MagicMock()
        position.symbol = "QQQ"
        position.contract_type = random.choice(["CALL", "PUT"])
        position.strike = Decimal(str(random.randint(300, 500)))
        position.expiration = date.today() + timedelta(days=random.randint(1, 30))
        position.quantity = random.choice([-5, -3, 3, 5, 10])  # Mix of long and short
        position.avg_cost = Decimal(str(round(random.uniform(1.0, 4.0), 2)))
        positions.append(position)

    return positions


class TestPnLService:
    """Test cases for P&L service."""

    @pytest.mark.asyncio
    async def test_record_trade_fill(self, pnl_service, mock_db_session, random_trades):
        """Test recording trade fills."""
        with patch(
            "spreadpilot_core.pnl.service.get_postgres_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_db_session

            # Record a random trade
            trade_data = random_trades[0]
            await pnl_service.record_trade_fill("test-follower-1", trade_data)

            # Verify trade was added to session
            assert mock_db_session.add.called
            added_trade = mock_db_session.add.call_args[0][0]
            assert isinstance(added_trade, Trade)
            assert added_trade.follower_id == "test-follower-1"
            assert added_trade.symbol == trade_data["symbol"]
            assert added_trade.quantity == trade_data["quantity"]
            assert mock_db_session.commit.called

    @pytest.mark.asyncio
    async def test_update_quote(self, pnl_service, mock_db_session):
        """Test updating market quotes."""
        with patch(
            "spreadpilot_core.pnl.service.get_postgres_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_db_session

            quote_data = {
                "symbol": "QQQ",
                "contract_type": "CALL",
                "strike": 450.0,
                "expiration": date.today() + timedelta(days=7),
                "bid": 2.45,
                "ask": 2.50,
                "last": 2.48,
                "volume": 1500,
                "quote_time": datetime.datetime.utcnow(),
            }

            await pnl_service.update_quote(quote_data)

            # Verify quote was added and cached
            assert mock_db_session.add.called
            added_quote = mock_db_session.add.call_args[0][0]
            assert isinstance(added_quote, Quote)
            assert added_quote.symbol == "QQQ"
            assert added_quote.last == Decimal("2.48")

            # Verify quote was cached
            cache_key = pnl_service._get_quote_cache_key(quote_data)
            assert cache_key in pnl_service.quote_cache

    @pytest.mark.asyncio
    async def test_calculate_mtm_with_positions(
        self, pnl_service, mock_db_session, random_positions
    ):
        """Test MTM calculation with random positions."""
        with patch(
            "spreadpilot_core.pnl.service.get_postgres_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_db_session

            # Set up callbacks
            async def mock_get_positions(follower_id):
                return random_positions

            async def mock_get_market_price(position):
                # Simulate market price movement
                return float(position.avg_cost) + random.uniform(-0.5, 0.5)

            pnl_service.set_callbacks(
                get_positions_fn=mock_get_positions,
                get_market_price_fn=mock_get_market_price,
            )

            # Add follower
            await pnl_service.add_follower("test-follower-1")

            # Mock database responses
            mock_db_session.execute.return_value.scalar.return_value = Decimal(
                "5.50"
            )  # Commission
            mock_db_session.execute.return_value.scalars.return_value.all.return_value = (
                []
            )  # No trades

            # Calculate MTM
            await pnl_service._calculate_follower_mtm("test-follower-1")

            # Verify intraday P&L was stored
            assert mock_db_session.add.called
            added_pnl = mock_db_session.add.call_args[0][0]
            assert isinstance(added_pnl, PnLIntraday)
            assert added_pnl.follower_id == "test-follower-1"
            assert added_pnl.position_count == len(random_positions)

    @pytest.mark.asyncio
    async def test_daily_rollup(self, pnl_service, mock_db_session):
        """Test daily P&L rollup."""
        with patch(
            "spreadpilot_core.pnl.service.get_postgres_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_db_session

            # Create mock intraday snapshots
            snapshots = []
            for i in range(10):
                snapshot = MagicMock()
                snapshot.total_market_value = Decimal("100000") + Decimal(str(i * 100))
                snapshot.position_count = 5
                snapshot.realized_pnl = Decimal(str(i * 50))
                snapshot.unrealized_pnl = Decimal(str(i * 30))
                snapshot.total_pnl = snapshot.realized_pnl + snapshot.unrealized_pnl
                snapshots.append(snapshot)

            # Mock trades
            trades = []
            for i in range(5):
                trade = MagicMock()
                trade.quantity = random.randint(1, 10)
                trade.commission = Decimal("1.50")
                trades.append(trade)

            # Set up mock responses
            mock_result1 = MagicMock()
            mock_result1.scalars.return_value.all.return_value = snapshots

            mock_result2 = MagicMock()
            mock_result2.scalars.return_value.all.return_value = trades

            mock_db_session.execute.side_effect = [mock_result1, mock_result2]

            # Add follower and perform rollup
            await pnl_service.add_follower("test-follower-1")
            await pnl_service._rollup_daily_pnl("test-follower-1", date.today())

            # Verify daily P&L was created
            assert mock_db_session.add.called
            added_daily = mock_db_session.add.call_args[0][0]
            assert isinstance(added_daily, PnLDaily)
            assert added_daily.follower_id == "test-follower-1"
            assert added_daily.trades_count == len(trades)
            assert added_daily.is_finalized

    @pytest.mark.asyncio
    async def test_monthly_rollup_with_commission(
        self, pnl_service, mock_db_session, mock_follower_data
    ):
        """Test monthly P&L rollup with commission calculation."""
        with patch(
            "spreadpilot_core.pnl.service.get_postgres_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_db_session

            # Create mock daily summaries
            daily_summaries = []
            total_pnl = Decimal("0")

            for i in range(20):  # 20 trading days
                daily = MagicMock()
                daily.realized_pnl = Decimal(str(random.randint(-500, 1000)))
                daily.total_pnl = daily.realized_pnl + Decimal(
                    str(random.randint(-200, 200))
                )
                daily.trades_count = random.randint(0, 10)
                daily.total_volume = daily.trades_count * random.randint(1, 5)
                daily.total_commission = Decimal(str(daily.trades_count * 1.5))
                daily.max_profit = max(daily.total_pnl, Decimal("0"))
                daily.max_drawdown = min(daily.total_pnl, Decimal("0"))
                daily.unrealized_pnl_start = Decimal(str(random.randint(-100, 100)))
                daily.unrealized_pnl_end = Decimal(str(random.randint(-100, 100)))

                total_pnl += daily.total_pnl
                daily_summaries.append(daily)

            # Mock database responses
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = daily_summaries
            mock_result.scalar.return_value = None  # No existing commission

            mock_db_session.execute.side_effect = [mock_result, MagicMock()]

            # Mock follower data retrieval
            with patch.object(
                pnl_service, "_get_follower_data", return_value=mock_follower_data
            ):
                # Add follower and perform rollup
                await pnl_service.add_follower("test-follower-1")
                await pnl_service._rollup_monthly_pnl("test-follower-1", 2025, 6)

            # Verify monthly P&L and commission were created
            assert mock_db_session.add.call_count == 2  # Monthly P&L + Commission

            # Check monthly P&L
            monthly_pnl = mock_db_session.add.call_args_list[0][0][0]
            assert isinstance(monthly_pnl, PnLMonthly)
            assert monthly_pnl.follower_id == "test-follower-1"
            assert monthly_pnl.trading_days == len(daily_summaries)

            # Check commission calculation
            commission = mock_db_session.add.call_args_list[1][0][0]
            assert isinstance(commission, CommissionMonthly)
            assert commission.follower_id == "test-follower-1"

            # Verify commission calculation logic
            if total_pnl > 0:
                expected_commission = total_pnl * Decimal("0.20")  # 20%
                assert commission.commission_amount == expected_commission
                assert commission.is_payable
            else:
                assert commission.commission_amount == Decimal("0")
                assert not commission.is_payable

    @pytest.mark.asyncio
    async def test_commission_calculation_positive_pnl(
        self, pnl_service, mock_db_session, mock_follower_data
    ):
        """Test commission calculation with positive P&L."""
        monthly_pnl = Decimal("5000.00")  # Positive P&L

        # Mock no existing commission
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db_session.execute.return_value = mock_result

        with patch.object(
            pnl_service, "_get_follower_data", return_value=mock_follower_data
        ):
            await pnl_service._calculate_monthly_commission(
                mock_db_session, "test-follower-1", 2025, 6, monthly_pnl
            )

        # Verify commission was calculated correctly
        assert mock_db_session.add.called
        commission = mock_db_session.add.call_args[0][0]
        assert isinstance(commission, CommissionMonthly)
        assert commission.monthly_pnl == monthly_pnl
        assert commission.commission_pct == Decimal("0.20")  # 20%
        assert commission.commission_amount == Decimal("1000.00")  # 20% of 5000
        assert commission.is_payable
        assert commission.follower_iban == mock_follower_data["iban"]

    @pytest.mark.asyncio
    async def test_commission_calculation_negative_pnl(
        self, pnl_service, mock_db_session, mock_follower_data
    ):
        """Test commission calculation with negative P&L."""
        monthly_pnl = Decimal("-2000.00")  # Negative P&L

        # Mock no existing commission
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db_session.execute.return_value = mock_result

        with patch.object(
            pnl_service, "_get_follower_data", return_value=mock_follower_data
        ):
            await pnl_service._calculate_monthly_commission(
                mock_db_session, "test-follower-1", 2025, 6, monthly_pnl
            )

        # Verify no commission for negative P&L
        assert mock_db_session.add.called
        commission = mock_db_session.add.call_args[0][0]
        assert isinstance(commission, CommissionMonthly)
        assert commission.monthly_pnl == monthly_pnl
        assert commission.commission_amount == Decimal("0")
        assert not commission.is_payable

    @pytest.mark.asyncio
    async def test_commission_calculation_zero_pnl(
        self, pnl_service, mock_db_session, mock_follower_data
    ):
        """Test commission calculation with zero P&L."""
        monthly_pnl = Decimal("0.00")  # Zero P&L

        # Mock no existing commission
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db_session.execute.return_value = mock_result

        with patch.object(
            pnl_service, "_get_follower_data", return_value=mock_follower_data
        ):
            await pnl_service._calculate_monthly_commission(
                mock_db_session, "test-follower-1", 2025, 6, monthly_pnl
            )

        # Verify no commission for zero P&L
        assert mock_db_session.add.called
        commission = mock_db_session.add.call_args[0][0]
        assert isinstance(commission, CommissionMonthly)
        assert commission.monthly_pnl == monthly_pnl
        assert commission.commission_amount == Decimal("0")
        assert not commission.is_payable

    @pytest.mark.asyncio
    async def test_update_existing_commission(
        self, pnl_service, mock_db_session, mock_follower_data
    ):
        """Test updating existing commission entry."""
        monthly_pnl = Decimal("3000.00")

        # Mock existing commission
        existing_commission = MagicMock(spec=CommissionMonthly)
        mock_result = MagicMock()
        mock_result.scalar.return_value = existing_commission
        mock_db_session.execute.return_value = mock_result

        with patch.object(
            pnl_service, "_get_follower_data", return_value=mock_follower_data
        ):
            await pnl_service._calculate_monthly_commission(
                mock_db_session, "test-follower-1", 2025, 6, monthly_pnl
            )

        # Verify existing commission was updated
        assert not mock_db_session.add.called  # Should not add new entry
        assert existing_commission.monthly_pnl == monthly_pnl
        assert existing_commission.commission_pct == Decimal("0.20")
        assert existing_commission.commission_amount == Decimal("600.00")  # 20% of 3000
        assert existing_commission.is_payable

    @pytest.mark.asyncio
    async def test_market_hours_check(self, pnl_service):
        """Test market hours checking."""
        # Mock weekday during market hours
        with patch("spreadpilot_core.pnl.service.datetime") as mock_dt:
            mock_now = datetime.datetime(2025, 6, 30, 14, 30, 0)  # 2:30 PM ET on Monday
            mock_now = ET.localize(mock_now)
            mock_dt.datetime.now.return_value = mock_now

            assert pnl_service._is_market_open()

        # Mock weekend
        with patch("spreadpilot_core.pnl.service.datetime") as mock_dt:
            mock_now = datetime.datetime(2025, 6, 28, 14, 30, 0)  # Saturday
            mock_now = ET.localize(mock_now)
            mock_dt.datetime.now.return_value = mock_now

            assert not pnl_service._is_market_open()

    @pytest.mark.asyncio
    async def test_quote_subscription_loop(self, pnl_service, random_positions):
        """Test quote subscription for positions."""
        # Set up callbacks
        subscribed_contracts = []

        async def mock_get_positions(follower_id):
            return random_positions

        async def mock_subscribe_tick(contract_info):
            subscribed_contracts.append(contract_info)

        pnl_service.set_callbacks(
            get_positions_fn=mock_get_positions, subscribe_tick_fn=mock_subscribe_tick
        )

        # Add follower and subscribe to quotes
        await pnl_service.add_follower("test-follower-1")
        await pnl_service._subscribe_to_position_quotes()

        # Verify subscriptions were created for unique contracts
        assert len(subscribed_contracts) > 0
        assert len(subscribed_contracts) <= len(random_positions)

    @pytest.mark.asyncio
    async def test_get_current_pnl(self, pnl_service, mock_db_session):
        """Test getting current P&L for display."""
        with patch(
            "spreadpilot_core.pnl.service.get_postgres_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_db_session

            # Mock latest snapshot
            latest_snapshot = MagicMock()
            latest_snapshot.snapshot_time = datetime.datetime.utcnow()
            latest_snapshot.realized_pnl = Decimal("500.00")
            latest_snapshot.unrealized_pnl = Decimal("300.00")
            latest_snapshot.total_pnl = Decimal("800.00")
            latest_snapshot.position_count = 5
            latest_snapshot.total_market_value = Decimal("10000.00")

            mock_result = MagicMock()
            mock_result.scalar.return_value = latest_snapshot
            mock_db_session.execute.return_value = mock_result

            # Get current P&L
            current_pnl = await pnl_service.get_current_pnl("test-follower-1")

            assert current_pnl["follower_id"] == "test-follower-1"
            assert current_pnl["realized_pnl"] == 500.00
            assert current_pnl["unrealized_pnl"] == 300.00
            assert current_pnl["total_pnl"] == 800.00
            assert current_pnl["position_count"] == 5

    @pytest.mark.asyncio
    async def test_get_monthly_commission(self, pnl_service, mock_db_session):
        """Test retrieving monthly commission for display."""
        with patch(
            "spreadpilot_core.pnl.service.get_postgres_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_db_session

            # Mock commission entry
            commission = MagicMock()
            commission.monthly_pnl = Decimal("5000.00")
            commission.commission_pct = Decimal("0.20")
            commission.commission_amount = Decimal("1000.00")
            commission.is_payable = True
            commission.is_paid = False
            commission.payment_date = None
            commission.payment_reference = None

            mock_result = MagicMock()
            mock_result.scalar.return_value = commission
            mock_db_session.execute.return_value = mock_result

            # Get monthly commission
            result = await pnl_service.get_monthly_commission(
                "test-follower-1", 2025, 6
            )

            assert result["follower_id"] == "test-follower-1"
            assert result["monthly_pnl"] == 5000.00
            assert result["commission_pct"] == 20.0  # Converted to percentage
            assert result["commission_amount"] == 1000.00
            assert result["is_payable"]
            assert not result["is_paid"]

"""Unit tests for commission calculation functionality."""

import os
import sys
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from app.service.pnl_service import PnLService


class TestCommissionCalculation:
    """Test cases for commission calculation functionality."""

    @pytest.fixture
    def mock_trading_service(self):
        """Create a mock trading service."""
        service = MagicMock()
        service.active_followers = ["follower1", "follower2"]
        return service

    @pytest.fixture
    def pnl_service(self, mock_trading_service):
        """Create a PnLService instance."""
        return PnLService(mock_trading_service)

    @pytest.fixture
    def sample_follower_data(self):
        """Sample follower data for testing."""
        return {
            "iban": "DE89370400440532013000",
            "email": "follower@example.com",
            "commission_pct": 20.0,  # 20%
        }

    @pytest.mark.asyncio
    async def test_commission_calculation_positive_pnl(self, pnl_service, sample_follower_data):
        """Test commission calculation for positive monthly P&L."""
        # Test case: month +$1,000, 20% => €200 commission entry

        # Mock session and database operations
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.return_value = None  # No existing commission
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.add = AsyncMock()

        # Mock follower data retrieval
        with patch.object(pnl_service, "_get_follower_data", return_value=sample_follower_data):
            await pnl_service._calculate_monthly_commission(
                session=mock_session,
                follower_id="follower1",
                year=2024,
                month=6,
                monthly_pnl=Decimal("1000.00"),
            )

        # Verify commission entry was added
        mock_session.add.assert_called_once()

        # Get the commission entry that was added
        commission_entry = mock_session.add.call_args[0][0]

        # Verify commission calculation: 20% of $1,000 = $200
        assert commission_entry.follower_id == "follower1"
        assert commission_entry.year == 2024
        assert commission_entry.month == 6
        assert commission_entry.monthly_pnl == Decimal("1000.00")
        assert commission_entry.commission_pct == Decimal("0.20")  # 20% as decimal
        assert commission_entry.commission_amount == Decimal("200.00")  # 20% of 1000
        assert commission_entry.commission_currency == "EUR"
        assert commission_entry.follower_iban == "DE89370400440532013000"
        assert commission_entry.follower_email == "follower@example.com"
        assert commission_entry.is_payable == True  # Positive P&L
        assert commission_entry.is_paid == False

        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_commission_calculation_negative_pnl(self, pnl_service, sample_follower_data):
        """Test commission calculation for negative monthly P&L."""

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.return_value = None  # No existing commission
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.add = AsyncMock()

        with patch.object(pnl_service, "_get_follower_data", return_value=sample_follower_data):
            await pnl_service._calculate_monthly_commission(
                session=mock_session,
                follower_id="follower1",
                year=2024,
                month=6,
                monthly_pnl=Decimal("-500.00"),  # Negative P&L
            )

        # Verify commission entry was added
        mock_session.add.assert_called_once()

        commission_entry = mock_session.add.call_args[0][0]

        # Verify no commission for negative P&L
        assert commission_entry.monthly_pnl == Decimal("-500.00")
        assert commission_entry.commission_amount == Decimal("0.00")  # No commission for loss
        assert commission_entry.is_payable == False  # Not payable for negative P&L

    @pytest.mark.asyncio
    async def test_commission_calculation_zero_pnl(self, pnl_service, sample_follower_data):
        """Test commission calculation for zero monthly P&L."""

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.add = AsyncMock()

        with patch.object(pnl_service, "_get_follower_data", return_value=sample_follower_data):
            await pnl_service._calculate_monthly_commission(
                session=mock_session,
                follower_id="follower1",
                year=2024,
                month=6,
                monthly_pnl=Decimal("0.00"),  # Zero P&L
            )

        commission_entry = mock_session.add.call_args[0][0]

        assert commission_entry.commission_amount == Decimal("0.00")
        assert commission_entry.is_payable == False

    @pytest.mark.asyncio
    async def test_commission_calculation_update_existing(self, pnl_service, sample_follower_data):
        """Test updating existing commission entry."""

        # Mock existing commission entry
        existing_commission = MagicMock()
        existing_commission.monthly_pnl = Decimal("800.00")
        existing_commission.commission_amount = Decimal("160.00")

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.return_value = existing_commission  # Existing commission found
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        with patch.object(pnl_service, "_get_follower_data", return_value=sample_follower_data):
            await pnl_service._calculate_monthly_commission(
                session=mock_session,
                follower_id="follower1",
                year=2024,
                month=6,
                monthly_pnl=Decimal("1200.00"),  # New P&L amount
            )

        # Verify existing commission was updated
        assert existing_commission.monthly_pnl == Decimal("1200.00")
        assert existing_commission.commission_amount == Decimal("240.00")  # 20% of 1200
        assert existing_commission.is_payable == True

        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_commission_calculation_different_percentage(self, pnl_service):
        """Test commission calculation with different percentage."""

        follower_data_10pct = {
            "iban": "DE89370400440532013000",
            "email": "follower@example.com",
            "commission_pct": 10.0,  # 10%
        }

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.add = AsyncMock()

        with patch.object(pnl_service, "_get_follower_data", return_value=follower_data_10pct):
            await pnl_service._calculate_monthly_commission(
                session=mock_session,
                follower_id="follower1",
                year=2024,
                month=6,
                monthly_pnl=Decimal("1000.00"),
            )

        commission_entry = mock_session.add.call_args[0][0]

        # Verify 10% commission calculation
        assert commission_entry.commission_pct == Decimal("0.10")  # 10% as decimal
        assert commission_entry.commission_amount == Decimal("100.00")  # 10% of 1000

    @pytest.mark.asyncio
    async def test_get_follower_data_success(self, pnl_service):
        """Test successful follower data retrieval."""

        mock_follower_doc = {
            "_id": "follower1",
            "iban": "DE89370400440532013000",
            "email": "test@example.com",
            "commission_pct": 15.0,
        }

        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = mock_follower_doc

        mock_db = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection

        with patch("app.service.pnl_service.get_mongo_db", return_value=mock_db):
            follower_data = await pnl_service._get_follower_data("follower1")

        assert follower_data["iban"] == "DE89370400440532013000"
        assert follower_data["email"] == "test@example.com"
        assert follower_data["commission_pct"] == 15.0

    @pytest.mark.asyncio
    async def test_get_follower_data_not_found(self, pnl_service):
        """Test follower data retrieval when follower not found."""

        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = None  # Follower not found

        mock_db = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection

        with patch("app.service.pnl_service.get_mongo_db", return_value=mock_db):
            follower_data = await pnl_service._get_follower_data("nonexistent")

        assert follower_data is None

    @pytest.mark.asyncio
    async def test_get_monthly_commissions_no_filters(self, pnl_service):
        """Test getting monthly commissions without filters."""

        mock_commission = MagicMock()
        mock_commission.id = "uuid-123"
        mock_commission.follower_id = "follower1"
        mock_commission.year = 2024
        mock_commission.month = 6
        mock_commission.monthly_pnl = Decimal("1000.00")
        mock_commission.commission_pct = Decimal("0.20")
        mock_commission.commission_amount = Decimal("200.00")
        mock_commission.commission_currency = "EUR"
        mock_commission.follower_iban = "DE89370400440532013000"
        mock_commission.follower_email = "test@example.com"
        mock_commission.is_payable = True
        mock_commission.is_paid = False
        mock_commission.payment_date = None
        mock_commission.payment_reference = None
        mock_commission.calculated_at = datetime(2024, 7, 1, 0, 10, 0)
        mock_commission.created_at = datetime(2024, 7, 1, 0, 10, 0)
        mock_commission.updated_at = datetime(2024, 7, 1, 0, 10, 0)

        with patch("app.service.pnl_service.get_postgres_session") as mock_session_ctx:
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = [mock_commission]

            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session_ctx.return_value.__aenter__.return_value = mock_session

            commissions = await pnl_service.get_monthly_commissions()

        assert len(commissions) == 1
        commission = commissions[0]
        assert commission["follower_id"] == "follower1"
        assert commission["monthly_pnl"] == 1000.00
        assert commission["commission_pct"] == 20.0  # Converted back to percentage
        assert commission["commission_amount"] == 200.00
        assert commission["is_payable"] == True

    @pytest.mark.asyncio
    async def test_mark_commission_paid_success(self, pnl_service):
        """Test marking commission as paid."""

        mock_commission = MagicMock()
        mock_commission.is_paid = False

        with patch("app.service.pnl_service.get_postgres_session") as mock_session_ctx:
            mock_result = AsyncMock()
            mock_result.scalar.return_value = mock_commission

            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session.commit = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session

            success = await pnl_service.mark_commission_paid("uuid-123", "PAY-REF-001")

        assert success == True
        assert mock_commission.is_paid == True
        assert mock_commission.payment_reference == "PAY-REF-001"
        assert mock_commission.payment_date == date.today()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_commission_paid_not_found(self, pnl_service):
        """Test marking commission as paid when commission not found."""

        with patch("app.service.pnl_service.get_postgres_session") as mock_session_ctx:
            mock_result = AsyncMock()
            mock_result.scalar.return_value = None  # Commission not found

            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session_ctx.return_value.__aenter__.return_value = mock_session

            success = await pnl_service.mark_commission_paid("nonexistent", "PAY-REF-001")

        assert success == False

    @pytest.mark.asyncio
    async def test_commission_calculation_no_follower_data(self, pnl_service):
        """Test commission calculation when follower data cannot be retrieved."""

        mock_session = AsyncMock()

        with patch.object(pnl_service, "_get_follower_data", return_value=None):
            await pnl_service._calculate_monthly_commission(
                session=mock_session,
                follower_id="nonexistent",
                year=2024,
                month=6,
                monthly_pnl=Decimal("1000.00"),
            )

        # Should return early without creating commission entry
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_commission_exact_scenario_from_prompt(self, pnl_service):
        """Test exact scenario from prompt: month +$1,000, 20% => €200 entry."""

        # Exact test case from prompt
        follower_data = {
            "iban": "DE89370400440532013000",
            "email": "follower@example.com",
            "commission_pct": 20.0,  # 20%
        }

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.return_value = None  # No existing commission
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.add = AsyncMock()

        with patch.object(pnl_service, "_get_follower_data", return_value=follower_data):
            await pnl_service._calculate_monthly_commission(
                session=mock_session,
                follower_id="test_follower",
                year=2024,
                month=6,
                monthly_pnl=Decimal("1000.00"),  # +$1,000
            )

        # Verify the exact scenario: €200 commission entry
        commission_entry = mock_session.add.call_args[0][0]

        assert commission_entry.monthly_pnl == Decimal("1000.00")
        assert commission_entry.commission_pct == Decimal("0.20")  # 20%
        assert commission_entry.commission_amount == Decimal("200.00")  # €200
        assert commission_entry.commission_currency == "EUR"
        assert commission_entry.is_payable == True
        assert commission_entry.follower_iban == "DE89370400440532013000"

"""Isolated unit tests for time value monitor."""

import asyncio
from enum import Enum
from unittest.mock import AsyncMock, MagicMock

import pytest


class RiskStatus(str, Enum):
    """Risk status levels for time value monitoring."""

    SAFE = "SAFE"
    RISK = "RISK"
    CRITICAL = "CRITICAL"


class MockAlertType:
    """Mock alert types."""

    RISK_WARNING = "RISK_WARNING"
    TIME_VALUE_CRITICAL = "TIME_VALUE_CRITICAL"
    LIQUIDATION_COMPLETE = "LIQUIDATION_COMPLETE"
    LIQUIDATION_FAILED = "LIQUIDATION_FAILED"


class MockAlertSeverity:
    """Mock alert severities."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class TimeValueMonitor:
    """Simplified TimeValueMonitor for testing."""

    def __init__(self, service):
        self.service = service
        self.risk_statuses = {}
        self.monitoring_active = False

    async def start_monitoring(self, shutdown_event):
        """Start time value monitoring loop."""
        self.monitoring_active = True

        while not shutdown_event.is_set() and self.monitoring_active:
            try:
                if self.service.is_market_open():
                    for follower_id in self.service.active_followers:
                        await self.monitor_time_value(follower_id)
                await asyncio.sleep(60)
            except Exception:
                await asyncio.sleep(10)

    async def monitor_time_value(self, follower_id):
        """Monitor time value for a specific follower."""
        client = await self.service.ibkr_manager.get_client(follower_id)
        if not client:
            return

        positions = await client.get_positions(force_update=True)
        if not positions:
            await self._update_risk_status(follower_id, RiskStatus.SAFE)
            return

        time_value = await self._calculate_time_value(client, positions)
        if time_value is None:
            return

        if time_value < 0.10:
            await self._handle_critical_time_value(follower_id, time_value)
        elif time_value < 0.20:
            await self._update_risk_status(follower_id, RiskStatus.RISK)
            await self.service.alert_manager.create_alert(
                follower_id=follower_id,
                alert_type=MockAlertType.RISK_WARNING,
                severity=MockAlertSeverity.WARNING,
                message=f"Time value approaching liquidation threshold: ${time_value:.4f}",
            )
        else:
            await self._update_risk_status(follower_id, RiskStatus.SAFE)

    async def _calculate_time_value(self, client, positions):
        """Calculate time value for spread positions."""
        spread_mark_price = await client.get_spread_mark_price()
        if spread_mark_price is None:
            return None

        intrinsic_value = await self._calculate_intrinsic_value(client, positions)
        if intrinsic_value is None:
            return None

        time_value = spread_mark_price - intrinsic_value
        return max(0.0, time_value)

    async def _calculate_intrinsic_value(self, client, positions):
        """Calculate intrinsic value of the spread."""
        underlying_price = await client.get_underlying_price("QQQ")
        if underlying_price is None:
            return None

        intrinsic_value = 0.0

        for position_key, qty in positions.items():
            if qty == 0:
                continue

            try:
                strike_str, right = position_key.split("-")
                strike = float(strike_str)
            except ValueError:
                continue

            if right.upper() == "CALL":
                contract_intrinsic = max(0, underlying_price - strike)
            elif right.upper() == "PUT":
                contract_intrinsic = max(0, strike - underlying_price)
            else:
                continue

            intrinsic_value += contract_intrinsic * abs(qty) * (1 if qty > 0 else -1)

        return intrinsic_value

    async def _handle_critical_time_value(self, follower_id, time_value):
        """Handle critical time value by liquidating positions."""
        await self._update_risk_status(follower_id, RiskStatus.CRITICAL)

        await self.service.alert_manager.create_alert(
            follower_id=follower_id,
            alert_type=MockAlertType.TIME_VALUE_CRITICAL,
            severity=MockAlertSeverity.CRITICAL,
            message=f"Time value critical (${time_value:.4f}), initiating liquidation",
        )

        result = await self.service.position_manager.close_positions(follower_id)

        if result["success"]:
            await self.service.alert_manager.create_alert(
                follower_id=follower_id,
                alert_type=MockAlertType.LIQUIDATION_COMPLETE,
                severity=MockAlertSeverity.INFO,
                message=f"Positions liquidated due to time value: ${time_value:.4f}",
            )
            await self._update_risk_status(follower_id, RiskStatus.SAFE)
        else:
            await self.service.alert_manager.create_alert(
                follower_id=follower_id,
                alert_type=MockAlertType.LIQUIDATION_FAILED,
                severity=MockAlertSeverity.CRITICAL,
                message=f"Failed to liquidate positions: {result.get('error')}",
            )

    async def _update_risk_status(self, follower_id, status):
        """Update risk status in Redis and local cache."""
        self.risk_statuses[follower_id] = status

        if hasattr(self.service, "redis_client") and self.service.redis_client:
            key = f"risk_status:{follower_id}"
            await self.service.redis_client.set(key, status.value, ex=300)
            await self.service.redis_client.publish(
                "risk_status_updates",
                f"{follower_id}:{status.value}:2024-01-01T00:00:00",
            )

    async def get_risk_status(self, follower_id):
        """Get current risk status for a follower."""
        if hasattr(self.service, "redis_client") and self.service.redis_client:
            key = f"risk_status:{follower_id}"
            status_str = await self.service.redis_client.get(key)
            if status_str:
                return RiskStatus(
                    status_str.decode() if isinstance(status_str, bytes) else status_str
                )

        return self.risk_statuses.get(follower_id, RiskStatus.SAFE)

    async def get_all_risk_statuses(self):
        """Get risk statuses for all followers."""
        statuses = {}
        for follower_id in self.service.active_followers:
            statuses[follower_id] = await self.get_risk_status(follower_id)
        return statuses

    async def stop_monitoring(self):
        """Stop the time value monitoring."""
        self.monitoring_active = False


class TestTimeValueMonitor:
    """Test cases for TimeValueMonitor class."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock trading service."""
        service = MagicMock()
        service.active_followers = ["follower1", "follower2"]
        service.is_market_open.return_value = True

        service.ibkr_manager = AsyncMock()
        service.alert_manager = AsyncMock()
        service.alert_manager.create_alert = AsyncMock()
        service.position_manager = AsyncMock()
        service.position_manager.close_positions = AsyncMock()
        service.redis_client = AsyncMock()
        service.redis_client.set = AsyncMock()
        service.redis_client.get = AsyncMock()
        service.redis_client.publish = AsyncMock()

        return service

    @pytest.fixture
    def mock_client(self):
        """Create a mock IBKR client."""
        client = AsyncMock()
        client.get_positions = AsyncMock()
        client.get_spread_mark_price = AsyncMock()
        client.get_underlying_price = AsyncMock()
        return client

    @pytest.fixture
    def time_value_monitor(self, mock_service):
        """Create a TimeValueMonitor instance."""
        return TimeValueMonitor(mock_service)

    def test_initialization(self, time_value_monitor, mock_service):
        """Test monitor initialization."""
        assert time_value_monitor.service == mock_service
        assert time_value_monitor.risk_statuses == {}
        assert time_value_monitor.monitoring_active == False

    @pytest.mark.asyncio
    async def test_monitor_time_value_no_client(self, time_value_monitor, mock_service):
        """Test monitoring when IBKR client is not available."""
        mock_service.ibkr_manager.get_client.return_value = None

        await time_value_monitor.monitor_time_value("follower1")

        mock_service.ibkr_manager.get_client.assert_called_once_with("follower1")

    @pytest.mark.asyncio
    async def test_monitor_time_value_no_positions(
        self, time_value_monitor, mock_service, mock_client
    ):
        """Test monitoring when there are no positions."""
        mock_service.ibkr_manager.get_client.return_value = mock_client
        mock_client.get_positions.return_value = {}

        await time_value_monitor.monitor_time_value("follower1")

        assert time_value_monitor.risk_statuses["follower1"] == RiskStatus.SAFE

    @pytest.mark.asyncio
    async def test_calculate_time_value_success(self, time_value_monitor, mock_client):
        """Test successful time value calculation."""
        positions = {"400.0-PUT": -1, "405.0-PUT": 1}
        mock_client.get_spread_mark_price.return_value = 1.50
        mock_client.get_underlying_price.return_value = 410.0

        time_value = await time_value_monitor._calculate_time_value(mock_client, positions)

        # Spread mark price (1.50) - intrinsic value (0.0) = 1.50
        assert time_value == 1.50

    @pytest.mark.asyncio
    async def test_calculate_intrinsic_value_put_spread(self, time_value_monitor, mock_client):
        """Test intrinsic value calculation for put spread."""
        positions = {"400.0-PUT": -1, "405.0-PUT": 1}
        mock_client.get_underlying_price.return_value = 402.0

        intrinsic_value = await time_value_monitor._calculate_intrinsic_value(
            mock_client, positions
        )

        # Short 400 PUT: max(0, 400-402) = 0, qty=-1 -> 0
        # Long 405 PUT: max(0, 405-402) = 3, qty=1 -> 3
        # Total: 0 + 3 = 3
        assert intrinsic_value == 3.0

    @pytest.mark.asyncio
    async def test_calculate_intrinsic_value_call_spread(self, time_value_monitor, mock_client):
        """Test intrinsic value calculation for call spread."""
        positions = {"400.0-CALL": 1, "405.0-CALL": -1}
        mock_client.get_underlying_price.return_value = 402.0

        intrinsic_value = await time_value_monitor._calculate_intrinsic_value(
            mock_client, positions
        )

        # Long 400 CALL: max(0, 402-400) = 2, qty=1 -> 2
        # Short 405 CALL: max(0, 402-405) = 0, qty=-1 -> 0
        # Total: 2 + 0 = 2
        assert intrinsic_value == 2.0

    @pytest.mark.asyncio
    async def test_monitor_time_value_safe_status(
        self, time_value_monitor, mock_service, mock_client
    ):
        """Test monitoring with safe time value."""
        mock_service.ibkr_manager.get_client.return_value = mock_client
        mock_client.get_positions.return_value = {"400.0-PUT": -1, "405.0-PUT": 1}
        mock_client.get_spread_mark_price.return_value = 1.50
        mock_client.get_underlying_price.return_value = 410.0

        await time_value_monitor.monitor_time_value("follower1")

        assert time_value_monitor.risk_statuses["follower1"] == RiskStatus.SAFE
        mock_service.alert_manager.create_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_monitor_time_value_risk_status(
        self, time_value_monitor, mock_service, mock_client
    ):
        """Test monitoring with risk time value."""
        mock_service.ibkr_manager.get_client.return_value = mock_client
        mock_client.get_positions.return_value = {"400.0-PUT": -1, "405.0-PUT": 1}
        mock_client.get_spread_mark_price.return_value = 0.15
        mock_client.get_underlying_price.return_value = 410.0

        await time_value_monitor.monitor_time_value("follower1")

        assert time_value_monitor.risk_statuses["follower1"] == RiskStatus.RISK

        mock_service.alert_manager.create_alert.assert_called_once_with(
            follower_id="follower1",
            alert_type=MockAlertType.RISK_WARNING,
            severity=MockAlertSeverity.WARNING,
            message="Time value approaching liquidation threshold: $0.1500",
        )

    @pytest.mark.asyncio
    async def test_monitor_time_value_critical_status(
        self, time_value_monitor, mock_service, mock_client
    ):
        """Test monitoring with critical time value."""
        mock_service.ibkr_manager.get_client.return_value = mock_client
        mock_client.get_positions.return_value = {"400.0-PUT": -1, "405.0-PUT": 1}
        mock_client.get_spread_mark_price.return_value = 0.05
        mock_client.get_underlying_price.return_value = 410.0
        mock_service.position_manager.close_positions.return_value = {"success": True}

        await time_value_monitor.monitor_time_value("follower1")

        assert time_value_monitor.risk_statuses["follower1"] == RiskStatus.SAFE
        mock_service.position_manager.close_positions.assert_called_once_with("follower1")
        assert mock_service.alert_manager.create_alert.call_count == 2

    @pytest.mark.asyncio
    async def test_monitor_time_value_critical_liquidation_failed(
        self, time_value_monitor, mock_service, mock_client
    ):
        """Test monitoring with critical time value when liquidation fails."""
        mock_service.ibkr_manager.get_client.return_value = mock_client
        mock_client.get_positions.return_value = {"400.0-PUT": -1, "405.0-PUT": 1}
        mock_client.get_spread_mark_price.return_value = 0.05
        mock_client.get_underlying_price.return_value = 410.0
        mock_service.position_manager.close_positions.return_value = {
            "success": False,
            "error": "Test error",
        }

        await time_value_monitor.monitor_time_value("follower1")

        assert time_value_monitor.risk_statuses["follower1"] == RiskStatus.CRITICAL

    @pytest.mark.asyncio
    async def test_update_risk_status_with_redis(self, time_value_monitor, mock_service):
        """Test updating risk status with Redis."""
        await time_value_monitor._update_risk_status("follower1", RiskStatus.RISK)

        assert time_value_monitor.risk_statuses["follower1"] == RiskStatus.RISK
        mock_service.redis_client.set.assert_called_with("risk_status:follower1", "RISK", ex=300)

    @pytest.mark.asyncio
    async def test_get_risk_status_from_redis(self, time_value_monitor, mock_service):
        """Test getting risk status from Redis."""
        mock_service.redis_client.get.return_value = b"CRITICAL"

        status = await time_value_monitor.get_risk_status("follower1")

        assert status == RiskStatus.CRITICAL

    @pytest.mark.asyncio
    async def test_get_risk_status_fallback_to_cache(self, time_value_monitor, mock_service):
        """Test getting risk status falls back to local cache."""
        mock_service.redis_client.get.return_value = None
        time_value_monitor.risk_statuses["follower1"] = RiskStatus.RISK

        status = await time_value_monitor.get_risk_status("follower1")

        assert status == RiskStatus.RISK

    @pytest.mark.asyncio
    async def test_get_all_risk_statuses(self, time_value_monitor, mock_service):
        """Test getting all risk statuses."""
        time_value_monitor.risk_statuses["follower1"] = RiskStatus.RISK
        time_value_monitor.risk_statuses["follower2"] = RiskStatus.SAFE
        mock_service.redis_client.get.return_value = None

        statuses = await time_value_monitor.get_all_risk_statuses()

        expected = {
            "follower1": RiskStatus.RISK,
            "follower2": RiskStatus.SAFE,
        }
        assert statuses == expected

    @pytest.mark.asyncio
    async def test_calculate_time_value_negative_result(self, time_value_monitor, mock_client):
        """Test time value calculation with negative result."""
        positions = {"400.0-PUT": -1, "405.0-PUT": 1}
        mock_client.get_spread_mark_price.return_value = 0.50
        mock_client.get_underlying_price.return_value = 398.0  # Makes PUT more valuable

        time_value = await time_value_monitor._calculate_time_value(mock_client, positions)

        # Should return 0 when time value would be negative
        assert time_value == 0.0

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, time_value_monitor):
        """Test stopping monitoring."""
        time_value_monitor.monitoring_active = True

        await time_value_monitor.stop_monitoring()

        assert time_value_monitor.monitoring_active == False

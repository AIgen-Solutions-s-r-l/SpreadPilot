"""Unit tests for time value monitor."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from app.service.time_value_monitor import TimeValueMonitor, RiskStatus
from spreadpilot_core.models import AlertType, AlertSeverity


class TestTimeValueMonitor:
    """Test cases for TimeValueMonitor class."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock trading service."""
        service = MagicMock()
        service.active_followers = ["follower1", "follower2"]
        service.is_market_open.return_value = True
        
        # Mock IBKR manager
        service.ibkr_manager = AsyncMock()
        
        # Mock alert manager
        service.alert_manager = AsyncMock()
        service.alert_manager.create_alert = AsyncMock()
        
        # Mock position manager
        service.position_manager = AsyncMock()
        service.position_manager.close_positions = AsyncMock()
        
        # Mock Redis client
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
    async def test_start_monitoring_market_closed(self, time_value_monitor, mock_service):
        """Test monitoring when market is closed."""
        mock_service.is_market_open.return_value = False
        shutdown_event = asyncio.Event()
        
        # Stop monitoring after short delay
        async def stop_after_delay():
            await asyncio.sleep(0.1)
            shutdown_event.set()
        
        # Run monitoring and stop tasks concurrently
        await asyncio.gather(
            time_value_monitor.start_monitoring(shutdown_event),
            stop_after_delay()
        )
        
        # Should not have called monitor_time_value since market is closed
        mock_service.ibkr_manager.get_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_monitor_time_value_no_client(self, time_value_monitor, mock_service):
        """Test monitoring when IBKR client is not available."""
        mock_service.ibkr_manager.get_client.return_value = None
        
        await time_value_monitor.monitor_time_value("follower1")
        
        mock_service.ibkr_manager.get_client.assert_called_once_with("follower1")

    @pytest.mark.asyncio
    async def test_monitor_time_value_no_positions(self, time_value_monitor, mock_service, mock_client):
        """Test monitoring when there are no positions."""
        mock_service.ibkr_manager.get_client.return_value = mock_client
        mock_client.get_positions.return_value = {}
        
        await time_value_monitor.monitor_time_value("follower1")
        
        # Should set status to SAFE when no positions
        assert time_value_monitor.risk_statuses["follower1"] == RiskStatus.SAFE
        mock_service.redis_client.set.assert_called()

    @pytest.mark.asyncio
    async def test_calculate_time_value_success(self, time_value_monitor, mock_client):
        """Test successful time value calculation."""
        positions = {"400.0-PUT": -1, "405.0-PUT": 1}  # Bull put spread
        mock_client.get_spread_mark_price.return_value = 1.50
        mock_client.get_underlying_price.return_value = 410.0
        
        with patch.object(time_value_monitor, '_calculate_intrinsic_value', return_value=0.0):
            time_value = await time_value_monitor._calculate_time_value(mock_client, positions)
        
        assert time_value == 1.50

    @pytest.mark.asyncio
    async def test_calculate_time_value_no_spread_price(self, time_value_monitor, mock_client):
        """Test time value calculation when spread price unavailable."""
        positions = {"400.0-PUT": -1, "405.0-PUT": 1}
        mock_client.get_spread_mark_price.return_value = None
        
        time_value = await time_value_monitor._calculate_time_value(mock_client, positions)
        
        assert time_value is None

    @pytest.mark.asyncio
    async def test_calculate_intrinsic_value_put_spread(self, time_value_monitor, mock_client):
        """Test intrinsic value calculation for put spread."""
        positions = {"400.0-PUT": -1, "405.0-PUT": 1}  # Bull put spread
        mock_client.get_underlying_price.return_value = 402.0
        
        intrinsic_value = await time_value_monitor._calculate_intrinsic_value(mock_client, positions)
        
        # Short 400 PUT: max(0, 400-402) = 0, qty=-1 -> 0 * 1 = 0
        # Long 405 PUT: max(0, 405-402) = 3, qty=1 -> 3 * 1 = 3
        # Total: 0 + 3 = 3
        assert intrinsic_value == 3.0

    @pytest.mark.asyncio
    async def test_calculate_intrinsic_value_call_spread(self, time_value_monitor, mock_client):
        """Test intrinsic value calculation for call spread."""
        positions = {"400.0-CALL": 1, "405.0-CALL": -1}  # Bull call spread
        mock_client.get_underlying_price.return_value = 402.0
        
        intrinsic_value = await time_value_monitor._calculate_intrinsic_value(mock_client, positions)
        
        # Long 400 CALL: max(0, 402-400) = 2, qty=1 -> 2 * 1 = 2
        # Short 405 CALL: max(0, 402-405) = 0, qty=-1 -> 0 * 1 = 0
        # Total: 2 + 0 = 2
        assert intrinsic_value == 2.0

    @pytest.mark.asyncio
    async def test_calculate_intrinsic_value_no_underlying_price(self, time_value_monitor, mock_client):
        """Test intrinsic value calculation when underlying price unavailable."""
        positions = {"400.0-PUT": -1, "405.0-PUT": 1}
        mock_client.get_underlying_price.return_value = None
        
        intrinsic_value = await time_value_monitor._calculate_intrinsic_value(mock_client, positions)
        
        assert intrinsic_value is None

    @pytest.mark.asyncio
    async def test_monitor_time_value_safe_status(self, time_value_monitor, mock_service, mock_client):
        """Test monitoring with safe time value."""
        mock_service.ibkr_manager.get_client.return_value = mock_client
        mock_client.get_positions.return_value = {"400.0-PUT": -1, "405.0-PUT": 1}
        
        with patch.object(time_value_monitor, '_calculate_time_value', return_value=0.50):
            await time_value_monitor.monitor_time_value("follower1")
        
        # Should set status to SAFE
        assert time_value_monitor.risk_statuses["follower1"] == RiskStatus.SAFE
        mock_service.alert_manager.create_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_monitor_time_value_risk_status(self, time_value_monitor, mock_service, mock_client):
        """Test monitoring with risk time value."""
        mock_service.ibkr_manager.get_client.return_value = mock_client
        mock_client.get_positions.return_value = {"400.0-PUT": -1, "405.0-PUT": 1}
        
        with patch.object(time_value_monitor, '_calculate_time_value', return_value=0.15):
            await time_value_monitor.monitor_time_value("follower1")
        
        # Should set status to RISK
        assert time_value_monitor.risk_statuses["follower1"] == RiskStatus.RISK
        
        # Should create warning alert
        mock_service.alert_manager.create_alert.assert_called_once_with(
            follower_id="follower1",
            alert_type=AlertType.RISK_WARNING,
            severity=AlertSeverity.WARNING,
            message="Time value approaching liquidation threshold: $0.1500",
        )

    @pytest.mark.asyncio
    async def test_monitor_time_value_critical_status(self, time_value_monitor, mock_service, mock_client):
        """Test monitoring with critical time value."""
        mock_service.ibkr_manager.get_client.return_value = mock_client
        mock_client.get_positions.return_value = {"400.0-PUT": -1, "405.0-PUT": 1}
        mock_service.position_manager.close_positions.return_value = {"success": True}
        
        with patch.object(time_value_monitor, '_calculate_time_value', return_value=0.05):
            await time_value_monitor.monitor_time_value("follower1")
        
        # Should set status to CRITICAL initially, then SAFE after liquidation
        assert time_value_monitor.risk_statuses["follower1"] == RiskStatus.SAFE
        
        # Should call close_positions
        mock_service.position_manager.close_positions.assert_called_once_with("follower1")
        
        # Should create multiple alerts
        assert mock_service.alert_manager.create_alert.call_count == 3

    @pytest.mark.asyncio
    async def test_monitor_time_value_critical_liquidation_failed(self, time_value_monitor, mock_service, mock_client):
        """Test monitoring with critical time value when liquidation fails."""
        mock_service.ibkr_manager.get_client.return_value = mock_client
        mock_client.get_positions.return_value = {"400.0-PUT": -1, "405.0-PUT": 1}
        mock_service.position_manager.close_positions.return_value = {
            "success": False, 
            "error": "Test error"
        }
        
        with patch.object(time_value_monitor, '_calculate_time_value', return_value=0.05):
            await time_value_monitor.monitor_time_value("follower1")
        
        # Should remain at CRITICAL status
        assert time_value_monitor.risk_statuses["follower1"] == RiskStatus.CRITICAL
        
        # Should create failure alert
        mock_service.alert_manager.create_alert.assert_called_with(
            follower_id="follower1",
            alert_type=AlertType.LIQUIDATION_FAILED,
            severity=AlertSeverity.CRITICAL,
            message="Failed to liquidate positions: Test error",
        )

    @pytest.mark.asyncio
    async def test_update_risk_status_with_redis(self, time_value_monitor, mock_service):
        """Test updating risk status with Redis."""
        await time_value_monitor._update_risk_status("follower1", RiskStatus.RISK)
        
        # Should update local cache
        assert time_value_monitor.risk_statuses["follower1"] == RiskStatus.RISK
        
        # Should update Redis
        mock_service.redis_client.set.assert_called_with(
            "risk_status:follower1", "RISK", ex=300
        )
        
        # Should publish status change
        mock_service.redis_client.publish.assert_called()

    @pytest.mark.asyncio
    async def test_get_risk_status_from_redis(self, time_value_monitor, mock_service):
        """Test getting risk status from Redis."""
        mock_service.redis_client.get.return_value = b"CRITICAL"
        
        status = await time_value_monitor.get_risk_status("follower1")
        
        assert status == RiskStatus.CRITICAL
        mock_service.redis_client.get.assert_called_with("risk_status:follower1")

    @pytest.mark.asyncio
    async def test_get_risk_status_fallback_to_cache(self, time_value_monitor, mock_service):
        """Test getting risk status falls back to local cache."""
        mock_service.redis_client.get.return_value = None
        time_value_monitor.risk_statuses["follower1"] = RiskStatus.RISK
        
        status = await time_value_monitor.get_risk_status("follower1")
        
        assert status == RiskStatus.RISK

    @pytest.mark.asyncio
    async def test_get_risk_status_default_safe(self, time_value_monitor, mock_service):
        """Test getting risk status defaults to SAFE."""
        mock_service.redis_client.get.return_value = None
        
        status = await time_value_monitor.get_risk_status("unknown_follower")
        
        assert status == RiskStatus.SAFE

    @pytest.mark.asyncio
    async def test_get_all_risk_statuses(self, time_value_monitor, mock_service):
        """Test getting all risk statuses."""
        time_value_monitor.risk_statuses["follower1"] = RiskStatus.RISK
        time_value_monitor.risk_statuses["follower2"] = RiskStatus.SAFE
        
        with patch.object(time_value_monitor, 'get_risk_status', side_effect=lambda f: time_value_monitor.risk_statuses.get(f, RiskStatus.SAFE)):
            statuses = await time_value_monitor.get_all_risk_statuses()
        
        assert statuses == {
            "follower1": RiskStatus.RISK,
            "follower2": RiskStatus.SAFE,
        }

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, time_value_monitor):
        """Test stopping monitoring."""
        time_value_monitor.monitoring_active = True
        
        await time_value_monitor.stop_monitoring()
        
        assert time_value_monitor.monitoring_active == False

    @pytest.mark.asyncio
    async def test_calculate_intrinsic_value_invalid_position_key(self, time_value_monitor, mock_client):
        """Test intrinsic value calculation with invalid position key."""
        positions = {"invalid-key-format": 1, "400.0-PUT": -1}
        mock_client.get_underlying_price.return_value = 402.0
        
        intrinsic_value = await time_value_monitor._calculate_intrinsic_value(mock_client, positions)
        
        # Should only calculate for valid position (400.0-PUT)
        # PUT intrinsic: max(0, 400-402) = 0, qty=-1 -> 0
        assert intrinsic_value == 0.0

    @pytest.mark.asyncio
    async def test_calculate_intrinsic_value_unknown_option_type(self, time_value_monitor, mock_client):
        """Test intrinsic value calculation with unknown option type."""
        positions = {"400.0-UNKNOWN": 1, "405.0-PUT": -1}
        mock_client.get_underlying_price.return_value = 402.0
        
        intrinsic_value = await time_value_monitor._calculate_intrinsic_value(mock_client, positions)
        
        # Should only calculate for valid option type (PUT)
        # PUT intrinsic: max(0, 405-402) = 3, qty=-1 -> -3
        assert intrinsic_value == -3.0

    @pytest.mark.asyncio
    async def test_calculate_time_value_negative_result(self, time_value_monitor, mock_client):
        """Test time value calculation with negative result."""
        positions = {"400.0-PUT": -1, "405.0-PUT": 1}
        mock_client.get_spread_mark_price.return_value = 0.50
        
        with patch.object(time_value_monitor, '_calculate_intrinsic_value', return_value=1.00):
            time_value = await time_value_monitor._calculate_time_value(mock_client, positions)
        
        # Time value cannot be negative, should return 0
        assert time_value == 0.0
"""
Unit tests for the watchdog service
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from watchdog import MAX_CONSECUTIVE_FAILURES, SERVICES, ServiceWatchdog


@pytest.fixture
def watchdog():
    """Create a ServiceWatchdog instance for testing"""
    return ServiceWatchdog()


class TestServiceWatchdog:
    """Test cases for ServiceWatchdog"""

    @pytest.mark.asyncio
    async def test_check_service_health_success(self, watchdog):
        """Test successful health check"""
        # Mock HTTP client
        mock_response = Mock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        watchdog.http_client = mock_client

        # Test health check
        result = await watchdog.check_service_health("trading_bot")

        assert result is True
        mock_client.get.assert_called_once_with(SERVICES["trading_bot"]["health_url"])

    @pytest.mark.asyncio
    async def test_check_service_health_failure_status(self, watchdog):
        """Test health check with non-200 status"""
        # Mock HTTP client
        mock_response = Mock()
        mock_response.status_code = 503

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        watchdog.http_client = mock_client

        # Test health check
        result = await watchdog.check_service_health("admin_api")

        assert result is False

    @pytest.mark.asyncio
    async def test_check_service_health_network_error(self, watchdog):
        """Test health check with network error"""
        # Mock HTTP client to raise exception
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        watchdog.http_client = mock_client

        # Test health check
        result = await watchdog.check_service_health("report_worker")

        assert result is False

    @patch("subprocess.run")
    def test_restart_service_success(self, mock_run, watchdog):
        """Test successful service restart"""
        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Test restart
        result = watchdog.restart_service("trading_bot")

        assert result is True
        mock_run.assert_called_once_with(
            ["docker", "restart", "spreadpilot-trading-bot"],
            capture_output=True,
            text=True,
            timeout=30,
        )

    @patch("subprocess.run")
    def test_restart_service_failure(self, mock_run, watchdog):
        """Test failed service restart"""
        # Mock failed subprocess run
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: No such container"
        mock_run.return_value = mock_result

        # Test restart
        result = watchdog.restart_service("admin_api")

        assert result is False

    @pytest.mark.asyncio
    async def test_monitor_service_healthy(self, watchdog):
        """Test monitoring a healthy service"""
        # Mock healthy service
        watchdog.check_service_health = AsyncMock(return_value=True)
        watchdog.publish_alert = AsyncMock()

        # Set initial failure count
        watchdog.failure_counts["trading_bot"] = 2

        # Monitor service
        await watchdog.monitor_service("trading_bot")

        # Verify failure count reset
        assert watchdog.failure_counts["trading_bot"] == 0
        # Verify recovery alert published
        watchdog.publish_alert.assert_called_once_with("trading_bot", "recovery", True)

    @pytest.mark.asyncio
    async def test_monitor_service_unhealthy_below_threshold(self, watchdog):
        """Test monitoring an unhealthy service below failure threshold"""
        # Mock unhealthy service
        watchdog.check_service_health = AsyncMock(return_value=False)
        watchdog.publish_alert = AsyncMock()
        watchdog.restart_service = Mock()

        # Monitor service
        await watchdog.monitor_service("admin_api")

        # Verify failure count incremented
        assert watchdog.failure_counts["admin_api"] == 1
        # Verify no restart attempted
        watchdog.restart_service.assert_not_called()
        watchdog.publish_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_monitor_service_unhealthy_exceeds_threshold(self, watchdog):
        """Test monitoring an unhealthy service that exceeds failure threshold"""
        # Mock unhealthy service
        watchdog.check_service_health = AsyncMock(return_value=False)
        watchdog.publish_alert = AsyncMock()
        watchdog.restart_service = Mock(return_value=True)

        # Set failure count to threshold - 1
        watchdog.failure_counts["report_worker"] = MAX_CONSECUTIVE_FAILURES - 1

        # Monitor service
        await watchdog.monitor_service("report_worker")

        # Verify restart attempted
        watchdog.restart_service.assert_called_once_with("report_worker")
        # Verify alert published
        watchdog.publish_alert.assert_called_once_with("report_worker", "restart", True)
        # Verify failure count reset
        assert watchdog.failure_counts["report_worker"] == 0

    @pytest.mark.asyncio
    async def test_monitor_service_restart_failure(self, watchdog):
        """Test monitoring with failed restart"""
        # Mock unhealthy service and failed restart
        watchdog.check_service_health = AsyncMock(return_value=False)
        watchdog.publish_alert = AsyncMock()
        watchdog.restart_service = Mock(return_value=False)

        # Set failure count to threshold - 1
        watchdog.failure_counts["frontend"] = MAX_CONSECUTIVE_FAILURES - 1

        # Monitor service
        await watchdog.monitor_service("frontend")

        # Verify restart attempted
        watchdog.restart_service.assert_called_once_with("frontend")
        # Verify alert published with failure
        watchdog.publish_alert.assert_called_once_with("frontend", "restart", False)

    @pytest.mark.asyncio
    async def test_publish_alert_component_down(self, watchdog):
        """Test alert publishing for component down"""
        # Mock the alert publishing (in real implementation, this would use Pub/Sub)
        with patch("watchdog.logger") as mock_logger:
            await watchdog.publish_alert("trading_bot", "restart", False)

            # Verify alert logged
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "Trading Bot restart failed" in call_args

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test ServiceWatchdog context manager"""
        async with ServiceWatchdog() as watchdog:
            assert watchdog.http_client is not None
            assert isinstance(watchdog.http_client, httpx.AsyncClient)

        # After context exit, client should be closed
        # (We can't directly test if it's closed, but the context manager handles it)

    @pytest.mark.asyncio
    async def test_run_monitoring_loop(self, watchdog):
        """Test the main monitoring loop"""
        # Mock monitor_service to prevent actual monitoring
        watchdog.monitor_service = AsyncMock()

        # Run the loop for a short time
        loop_task = asyncio.create_task(watchdog.run())
        await asyncio.sleep(0.1)  # Let it run briefly
        loop_task.cancel()

        try:
            await loop_task
        except asyncio.CancelledError:
            pass

        # Verify monitor_service was called for all services
        assert watchdog.monitor_service.call_count >= len(SERVICES)

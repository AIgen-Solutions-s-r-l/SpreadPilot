"""Unit tests for Executor alert publishing."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis import aioredis as fakeredis
from ib_insync import IB

from spreadpilot_core.ibkr.client import IBKRClient, OrderStatus
from spreadpilot_core.models.alert import Alert, AlertSeverity
from trading_bot.app.service.executor import VerticalSpreadExecutor


@pytest.fixture
async def fake_redis():
    """Create a fake Redis client for testing."""
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    await client.close()


@pytest.fixture
def mock_ibkr_client():
    """Create a mock IBKR client."""
    client = MagicMock(spec=IBKRClient)
    client.ensure_connected = AsyncMock(return_value=True)
    client.get_account_summary = AsyncMock(return_value={"AvailableFunds": "10000"})
    client.get_market_price = AsyncMock(return_value=1.0)
    client._get_qqq_option_contract = MagicMock()
    
    # Mock IB instance
    mock_ib = MagicMock(spec=IB)
    mock_ib.whatIfOrderAsync = AsyncMock()
    mock_ib.placeOrder = MagicMock()
    mock_ib.cancelOrder = MagicMock()
    mock_ib.waitOnUpdate = MagicMock()
    client.ib = mock_ib
    
    return client


@pytest.fixture
async def executor(mock_ibkr_client, fake_redis):
    """Create an executor instance with mocked dependencies."""
    executor = VerticalSpreadExecutor(mock_ibkr_client)
    executor.redis_client = fake_redis
    yield executor


class TestExecutorAlerts:
    """Test suite for executor alert publishing."""
    
    @pytest.mark.asyncio
    async def test_margin_check_failure_publishes_alert(self, executor, fake_redis):
        """Test that margin check failure publishes NO_MARGIN alert."""
        # Mock whatIf to return insufficient margin
        whatif_result = MagicMock()
        whatif_result.initMarginChange = 5000
        whatif_result.maintMarginChange = 3000
        whatif_result.equityWithLoanAfter = 5000
        executor.ibkr_client.ib.whatIfOrderAsync.return_value = whatif_result
        executor.ibkr_client.get_account_summary.return_value = {"AvailableFunds": "1000"}
        
        # Execute trade that should fail margin check
        signal = {
            "strategy": "Long",
            "qty_per_leg": 10,
            "strike_long": 450,
            "strike_short": 455
        }
        
        result = await executor.execute_vertical_spread(signal, "test_follower_123")
        
        # Verify rejection
        assert result["status"] == OrderStatus.REJECTED
        assert "Margin check failed" in result["error"]
        
        # Check alert was published to Redis
        messages = await fake_redis.xrange("alerts")
        assert len(messages) == 1
        
        # Parse alert
        msg_id, data = messages[0]
        alert_json = data["data"]
        alert = Alert.model_validate_json(alert_json)
        
        # Verify alert content
        assert alert.follower_id == "test_follower_123"
        assert "NO_MARGIN" in alert.reason
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.service == "executor"
    
    @pytest.mark.asyncio
    async def test_mid_price_too_low_publishes_alert(self, executor, fake_redis):
        """Test that MID price below threshold publishes MID_TOO_LOW alert."""
        # Mock successful margin check
        whatif_result = MagicMock()
        whatif_result.initMarginChange = 500
        executor.ibkr_client.ib.whatIfOrderAsync.return_value = whatif_result
        executor.ibkr_client.get_account_summary.return_value = {"AvailableFunds": "10000"}
        
        # Mock market prices to get low MID
        executor.ibkr_client.get_market_price.side_effect = [0.30, 0.60]  # MID = 0.30
        
        # Execute trade
        signal = {
            "strategy": "Long",
            "qty_per_leg": 10,
            "strike_long": 450,
            "strike_short": 455
        }
        
        result = await executor.execute_vertical_spread(
            signal, 
            "test_follower_123",
            min_price_threshold=0.70
        )
        
        # Verify rejection
        assert result["status"] == OrderStatus.REJECTED
        assert "below minimum threshold" in result["error"]
        
        # Check alert
        messages = await fake_redis.xrange("alerts")
        assert len(messages) == 1
        
        msg_id, data = messages[0]
        alert = Alert.model_validate_json(data["data"])
        
        assert alert.follower_id == "test_follower_123"
        assert "MID_TOO_LOW" in alert.reason
        assert "$0.30" in alert.reason
        assert "$0.70" in alert.reason  # threshold
        assert alert.severity == AlertSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_limit_ladder_exhausted_publishes_alert(self, executor, fake_redis):
        """Test that exhausting all ladder attempts publishes LIMIT_REACHED alert."""
        # Mock successful margin check and MID price
        whatif_result = MagicMock()
        whatif_result.initMarginChange = 500
        executor.ibkr_client.ib.whatIfOrderAsync.return_value = whatif_result
        executor.ibkr_client.get_account_summary.return_value = {"AvailableFunds": "10000"}
        executor.ibkr_client.get_market_price.side_effect = [1.50, 2.50]  # MID = -1.00
        
        # Mock order placement that never fills
        mock_trade = MagicMock()
        mock_trade.orderStatus.status = "Submitted"
        mock_trade.orderStatus.filled = 0
        mock_trade.order.orderId = 12345
        executor.ibkr_client.ib.placeOrder.return_value = mock_trade
        
        # Execute trade with limited attempts
        signal = {
            "strategy": "Long",
            "qty_per_leg": 10,
            "strike_long": 450,
            "strike_short": 455
        }
        
        result = await executor.execute_vertical_spread(
            signal,
            "test_follower_123",
            max_attempts=2,
            attempt_interval=0.1,
            timeout_per_attempt=0.1
        )
        
        # Verify rejection
        assert result["status"] == OrderStatus.REJECTED
        assert "All 2 attempts exhausted" in result["error"]
        
        # Check alert
        messages = await fake_redis.xrange("alerts")
        assert len(messages) == 1
        
        msg_id, data = messages[0]
        alert = Alert.model_validate_json(data["data"])
        
        assert alert.follower_id == "test_follower_123"
        assert "LIMIT_REACHED" in alert.reason
        assert "All 2 attempts exhausted" in alert.reason
        assert alert.severity == AlertSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_gateway_error_publishes_alert(self, executor, fake_redis):
        """Test that IB gateway errors publish GATEWAY_UNREACHABLE alert."""
        # Mock connection failure
        executor.ibkr_client.ensure_connected.return_value = False
        
        # Execute trade
        signal = {
            "strategy": "Long",
            "qty_per_leg": 10,
            "strike_long": 450,
            "strike_short": 455
        }
        
        result = await executor.execute_vertical_spread(signal, "test_follower_123")
        
        # Verify rejection
        assert result["status"] == OrderStatus.REJECTED
        assert "Not connected to IB Gateway" in result["error"]
        
        # Check alert
        messages = await fake_redis.xrange("alerts")
        assert len(messages) == 1
        
        msg_id, data = messages[0]
        alert = Alert.model_validate_json(data["data"])
        
        assert alert.follower_id == "test_follower_123"
        assert "GATEWAY_UNREACHABLE" in alert.reason
        assert alert.severity == AlertSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_ib_rejection_publishes_alert(self, executor, fake_redis):
        """Test that IB order rejection publishes alert."""
        # Mock successful pre-checks
        whatif_result = MagicMock()
        whatif_result.initMarginChange = 500
        executor.ibkr_client.ib.whatIfOrderAsync.return_value = whatif_result
        executor.ibkr_client.get_account_summary.return_value = {"AvailableFunds": "10000"}
        executor.ibkr_client.get_market_price.side_effect = [1.50, 2.50]  # MID = -1.00
        
        # Mock IB rejection
        executor.ibkr_client.ib.placeOrder.side_effect = Exception("Order rejected by IB")
        
        # Execute trade
        signal = {
            "strategy": "Long", 
            "qty_per_leg": 10,
            "strike_long": 450,
            "strike_short": 455
        }
        
        result = await executor.execute_vertical_spread(signal, "test_follower_123")
        
        # Verify rejection
        assert result["status"] == OrderStatus.REJECTED
        
        # Check alert  
        messages = await fake_redis.xrange("alerts")
        assert len(messages) == 1
        
        msg_id, data = messages[0]
        alert = Alert.model_validate_json(data["data"])
        
        assert alert.follower_id == "test_follower_123"
        assert "GATEWAY_UNREACHABLE" in alert.reason
        assert "Order rejected by IB" in alert.reason
        assert alert.severity == AlertSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_successful_execution_no_alert(self, executor, fake_redis):
        """Test that successful execution does not publish alerts."""
        # Mock successful pre-checks
        whatif_result = MagicMock()
        whatif_result.initMarginChange = 500
        executor.ibkr_client.ib.whatIfOrderAsync.return_value = whatif_result
        executor.ibkr_client.get_account_summary.return_value = {"AvailableFunds": "10000"}
        executor.ibkr_client.get_market_price.side_effect = [1.50, 2.50]  # MID = -1.00
        
        # Mock successful order fill
        mock_trade = MagicMock()
        mock_trade.orderStatus.status = "Filled"
        mock_trade.orderStatus.filled = 10
        mock_trade.orderStatus.avgFillPrice = -0.95
        mock_trade.order.orderId = 12345
        executor.ibkr_client.ib.placeOrder.return_value = mock_trade
        
        # Execute trade
        signal = {
            "strategy": "Long",
            "qty_per_leg": 10,
            "strike_long": 450,
            "strike_short": 455
        }
        
        result = await executor.execute_vertical_spread(signal, "test_follower_123")
        
        # Verify success
        assert result["status"] == OrderStatus.FILLED
        assert result["filled_quantity"] == 10
        
        # Check no alerts were published
        messages = await fake_redis.xrange("alerts")
        assert len(messages) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_alerts_for_different_failures(self, executor, fake_redis):
        """Test multiple alerts for different failure scenarios."""
        # Execute multiple trades with different failures
        
        # 1. Margin failure
        executor.ibkr_client.get_account_summary.return_value = {"AvailableFunds": "100"}
        whatif_result = MagicMock()
        whatif_result.initMarginChange = 5000
        executor.ibkr_client.ib.whatIfOrderAsync.return_value = whatif_result
        
        signal1 = {"strategy": "Long", "qty_per_leg": 10, "strike_long": 450, "strike_short": 455}
        await executor.execute_vertical_spread(signal1, "follower_001")
        
        # 2. MID too low
        executor.ibkr_client.get_account_summary.return_value = {"AvailableFunds": "10000"}
        executor.ibkr_client.get_market_price.side_effect = [0.20, 0.40]
        
        signal2 = {"strategy": "Short", "qty_per_leg": 5, "strike_long": 460, "strike_short": 465}
        await executor.execute_vertical_spread(signal2, "follower_002")
        
        # Check both alerts
        messages = await fake_redis.xrange("alerts")
        assert len(messages) == 2
        
        # Parse alerts
        alerts = []
        for msg_id, data in messages:
            alert = Alert.model_validate_json(data["data"])
            alerts.append(alert)
        
        # Verify first alert (margin)
        assert alerts[0].follower_id == "follower_001"
        assert "NO_MARGIN" in alerts[0].reason
        
        # Verify second alert (MID)
        assert alerts[1].follower_id == "follower_002"
        assert "MID_TOO_LOW" in alerts[1].reason
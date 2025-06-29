"""Unit tests for the enhanced alert router with httpx mocking."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from app.service.alert_router import AlertRouter
from httpx import Response

from spreadpilot_core.models.alert import AlertEvent, AlertType


@pytest.fixture
def sample_alert_event():
    """Create a sample alert event for testing."""
    return AlertEvent(
        event_type=AlertType.COMPONENT_DOWN,
        timestamp=datetime(2025, 6, 28, 12, 0, 0),
        message="Trading Bot is not responding",
        params={
            "component_name": "trading-bot",
            "last_heartbeat": "2025-06-28T11:45:00Z",
            "attempts": 3,
        },
    )


@pytest.fixture
def alert_router():
    """Create an alert router with test configuration."""
    return AlertRouter(
        telegram_token="test_bot_token",
        telegram_admin_ids=["123456789", "987654321"],
        email_sender="alerts@spreadpilot.com",
        email_recipients=["admin1@example.com", "admin2@example.com"],
        smtp_config={
            "host": "smtp.example.com",
            "port": 587,
            "user": "smtp_user",
            "password": "smtp_pass",
            "tls": True,
        },
        dashboard_base_url="https://dashboard.spreadpilot.com",
    )


class TestAlertRouter:
    """Test cases for AlertRouter."""

    @pytest.mark.asyncio
    async def test_generate_deep_link_component_down(
        self, alert_router, sample_alert_event
    ):
        """Test deep link generation for component down event."""
        link = alert_router._generate_deep_link(sample_alert_event)
        assert link == "https://dashboard.spreadpilot.com/status?component=trading-bot"

    @pytest.mark.asyncio
    async def test_generate_deep_link_no_margin(self, alert_router):
        """Test deep link generation for no margin event."""
        event = AlertEvent(
            event_type=AlertType.NO_MARGIN,
            timestamp=datetime.now(),
            message="Insufficient margin",
            params={"account_id": "ACC001"},
        )
        link = alert_router._generate_deep_link(event)
        assert link == "https://dashboard.spreadpilot.com/accounts/ACC001"

    @pytest.mark.asyncio
    async def test_generate_deep_link_follower_event(self, alert_router):
        """Test deep link generation for follower-specific event."""
        event = AlertEvent(
            event_type=AlertType.ASSIGNMENT_DETECTED,
            timestamp=datetime.now(),
            message="Option assignment detected",
            params={"follower_id": "FOLLOWER001"},
        )
        link = alert_router._generate_deep_link(event)
        assert link == "https://dashboard.spreadpilot.com/followers/FOLLOWER001"

    @pytest.mark.asyncio
    async def test_format_alert_message(self, alert_router, sample_alert_event):
        """Test alert message formatting."""
        subject, telegram_msg, email_html = alert_router._format_alert_message(
            sample_alert_event
        )

        # Check subject
        assert subject == "🔴 SpreadPilot Alert: COMPONENT_DOWN"

        # Check Telegram message
        assert "🔴 *COMPONENT_DOWN*" in telegram_msg
        assert "Trading Bot is not responding" in telegram_msg
        assert "Component Name: `trading-bot`" in telegram_msg
        assert "[View in Dashboard]" in telegram_msg

        # Check HTML email
        assert "<h2" in email_html
        assert "COMPONENT_DOWN" in email_html
        assert "Trading Bot is not responding" in email_html
        assert "trading-bot" in email_html
        assert "View in Dashboard" in email_html

    @pytest.mark.asyncio
    async def test_send_telegram_alert_success(self, alert_router):
        """Test successful Telegram alert sending."""
        # Create a mock response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_response.raise_for_status = Mock()

        # Mock the HTTP client
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        alert_router._http_client = mock_client

        # Test sending
        result = await alert_router.send_telegram_alert("123456789", "Test message")

        # Verify
        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "api.telegram.org/bot" in call_args[0][0]
        assert call_args[1]["json"]["chat_id"] == "123456789"
        assert call_args[1]["json"]["text"] == "Test message"
        assert call_args[1]["json"]["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_send_telegram_alert_api_error(self, alert_router):
        """Test Telegram alert with API error response."""
        # Create a mock error response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": False,
            "description": "Bad Request: chat not found",
        }
        mock_response.raise_for_status = Mock()

        # Mock the HTTP client
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        alert_router._http_client = mock_client

        # Test sending
        result = await alert_router.send_telegram_alert("invalid_id", "Test message")

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_send_telegram_alert_http_error(self, alert_router):
        """Test Telegram alert with HTTP error."""
        # Create a mock error response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=None, response=mock_response
        )

        # Mock the HTTP client
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        alert_router._http_client = mock_client

        # Test sending
        result = await alert_router.send_telegram_alert("123456789", "Test message")

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_send_email_alert_success(self, alert_router):
        """Test successful email alert sending."""
        with patch(
            "app.service.alert_router.aiosmtplib.send", new_callable=AsyncMock
        ) as mock_send:
            result = await alert_router.send_email_alert(
                "test@example.com", "Test Subject", "<p>Test HTML</p>"
            )

            assert result is True
            mock_send.assert_called_once()

            # Check the message was created correctly
            message = mock_send.call_args[0][0]
            assert message["From"] == "alerts@spreadpilot.com"
            assert message["To"] == "test@example.com"
            assert message["Subject"] == "Test Subject"

    @pytest.mark.asyncio
    async def test_send_email_alert_failure(self, alert_router):
        """Test email alert sending failure."""
        with patch(
            "app.service.alert_router.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=Exception("SMTP error"),
        ):
            result = await alert_router.send_email_alert(
                "test@example.com", "Test Subject", "<p>Test HTML</p>"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_route_alert_telegram_success(self, alert_router, sample_alert_event):
        """Test alert routing with successful Telegram delivery."""
        # Mock successful Telegram responses
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        alert_router._http_client = mock_client

        # Route the alert
        results = await alert_router.route_alert(sample_alert_event)

        # Verify results
        assert results["telegram"]["attempted"] == 2  # Two admin IDs
        assert results["telegram"]["success"] == 2
        assert results["telegram"]["failed"] == 0
        assert results["email"]["attempted"] == 0  # Email not used
        assert results["fallback_used"] is False

        # Verify Telegram calls
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_route_alert_telegram_failure_email_fallback(
        self, alert_router, sample_alert_event
    ):
        """Test alert routing with Telegram failure and email fallback."""
        # Mock failed Telegram responses
        mock_response = Mock(spec=Response)
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=None, response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        alert_router._http_client = mock_client

        # Mock successful email
        with patch("app.service.alert_router.aiosmtplib.send", new_callable=AsyncMock):
            results = await alert_router.route_alert(sample_alert_event)

        # Verify results
        assert results["telegram"]["attempted"] == 2
        assert results["telegram"]["success"] == 0
        assert results["telegram"]["failed"] == 2
        assert results["email"]["attempted"] == 2  # Two email recipients
        assert results["email"]["success"] == 2
        assert results["fallback_used"] is True

    @pytest.mark.asyncio
    async def test_route_alert_partial_telegram_success(
        self, alert_router, sample_alert_event
    ):
        """Test alert routing with partial Telegram success (no email fallback)."""
        # Mock mixed Telegram responses (one success, one failure)
        success_response = Mock(spec=Response)
        success_response.status_code = 200
        success_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        success_response.raise_for_status = Mock()

        failure_response = Mock(spec=Response)
        failure_response.status_code = 400
        failure_response.text = "Bad Request"
        failure_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=None, response=failure_response
        )

        mock_client = AsyncMock()
        mock_client.post.side_effect = [success_response, failure_response]
        alert_router._http_client = mock_client

        # Route the alert
        results = await alert_router.route_alert(sample_alert_event)

        # Verify results
        assert results["telegram"]["attempted"] == 2
        assert results["telegram"]["success"] == 1
        assert results["telegram"]["failed"] == 1
        assert results["email"]["attempted"] == 0  # Email not used (partial success)
        assert results["fallback_used"] is False

    @pytest.mark.asyncio
    async def test_route_alert_complete_failure(self, alert_router, sample_alert_event):
        """Test alert routing with complete failure."""
        # Mock failed Telegram
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error", request=None, response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        alert_router._http_client = mock_client

        # Mock failed email
        with patch(
            "app.service.alert_router.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=Exception("SMTP error"),
        ):
            with pytest.raises(
                Exception, match="Failed to deliver alert via any channel"
            ):
                await alert_router.route_alert(sample_alert_event)

    @pytest.mark.asyncio
    async def test_route_alert_no_telegram_config(self, sample_alert_event):
        """Test alert routing without Telegram configuration."""
        router = AlertRouter(
            telegram_token=None,
            telegram_admin_ids=None,
            email_sender="alerts@spreadpilot.com",
            email_recipients=["admin@example.com"],
            smtp_config={"host": "smtp.example.com", "port": 587},
        )

        with patch("app.service.alert_router.aiosmtplib.send", new_callable=AsyncMock):
            results = await router.route_alert(sample_alert_event)

        # Should go directly to email
        assert results["telegram"]["attempted"] == 0
        assert results["email"]["attempted"] == 1
        assert results["fallback_used"] is True

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test AlertRouter context manager functionality."""
        router = AlertRouter()

        # Test that client is created and closed
        async with router as r:
            assert r._http_client is not None
            original_client = r._http_client

        # After context exit, client should be closed
        # (We can't directly test if it's closed, but we can verify it was the same instance)
        assert router._http_client == original_client

    @pytest.mark.asyncio
    async def test_context_manager_with_provided_client(self):
        """Test AlertRouter context manager with provided HTTP client."""
        mock_client = AsyncMock()
        mock_client._test_client = True  # Mark as test client

        router = AlertRouter(http_client=mock_client)

        async with router as r:
            assert r._http_client == mock_client

        # Should not close a provided client
        mock_client.aclose.assert_not_called()

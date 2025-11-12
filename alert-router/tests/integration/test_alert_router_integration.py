"""Integration tests for alert router with actual service."""

import os
from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from app.service.alert_router import AlertRouter
from app.service.router import route_alert as legacy_route_alert
from spreadpilot_core.models.alert import AlertEvent, AlertType


@pytest.fixture
def integration_alert_event():
    """Create an alert event for integration testing."""
    return AlertEvent(
        event_type=AlertType.GATEWAY_UNREACHABLE,
        timestamp=datetime.now(),
        message="IB Gateway connection lost",
        params={
            "component_name": "ib-gateway",
            "last_response": "Connection timeout",
            "retry_count": 5,
        },
    )


class TestAlertRouterIntegration:
    """Integration tests for alert router."""

    @pytest.mark.asyncio
    async def test_legacy_route_alert_function(self, integration_alert_event):
        """Test that the legacy route_alert function works with new implementation."""
        # Mock the AlertRouter to avoid actual API calls
        with patch("app.service.router.AlertRouter") as MockAlertRouter:
            mock_router = AsyncMock()
            mock_router.route_alert = AsyncMock(
                return_value={
                    "telegram": {"attempted": 2, "success": 2, "failed": 0},
                    "email": {"attempted": 0, "success": 0, "failed": 0},
                    "fallback_used": False,
                }
            )
            MockAlertRouter.return_value.__aenter__.return_value = mock_router

            # Call the legacy function
            await legacy_route_alert(integration_alert_event)

            # Verify it was called correctly
            MockAlertRouter.assert_called_once()
            mock_router.route_alert.assert_called_once_with(integration_alert_event)

    @pytest.mark.asyncio
    async def test_alert_router_with_environment_config(self, integration_alert_event):
        """Test AlertRouter picks up configuration from environment/settings."""
        # Set up minimal test environment
        test_env = {
            "TELEGRAM_BOT_TOKEN": "test_token_123",
            "TELEGRAM_ADMIN_IDS": "111111,222222",
            "EMAIL_SENDER": "test@spreadpilot.com",
            "EMAIL_ADMIN_RECIPIENTS": "admin1@test.com,admin2@test.com",
            "SMTP_HOST": "smtp.test.com",
            "DASHBOARD_BASE_URL": "https://test.spreadpilot.com",
        }

        with patch.dict(os.environ, test_env):
            # Need to reload settings to pick up new env vars

            # Create router without explicit config (should use settings)
            router = AlertRouter()

            # Verify configuration was loaded
            assert router.telegram_token == "test_token_123"
            assert router.telegram_admin_ids == ["111111", "222222"]
            assert router.email_sender == "test@spreadpilot.com"
            assert router.email_recipients == ["admin1@test.com", "admin2@test.com"]
            assert router.dashboard_base_url == "https://test.spreadpilot.com"

    @pytest.mark.asyncio
    async def test_full_alert_flow_with_mocked_apis(self, integration_alert_event):
        """Test complete alert flow with mocked external APIs."""

        # Create a test HTTP client with mocked responses
        class MockTransport(httpx.AsyncHTTPTransport):
            async def handle_async_request(self, request):
                # Mock Telegram API response
                if "api.telegram.org" in str(request.url):
                    return httpx.Response(
                        200,
                        json={"ok": True, "result": {"message_id": 999}},
                    )
                # Mock any other requests
                return httpx.Response(404)

        mock_client = httpx.AsyncClient(transport=MockTransport())

        # Create router with test config
        router = AlertRouter(
            telegram_token="test_bot_token",
            telegram_admin_ids=["123456", "789012"],
            email_sender="alerts@test.com",
            email_recipients=["admin@test.com"],
            smtp_config={"host": "smtp.test.com", "port": 587},
            dashboard_base_url="https://dashboard.test.com",
            http_client=mock_client,
        )

        try:
            # Route the alert
            results = await router.route_alert(integration_alert_event)

            # Verify successful Telegram delivery
            assert results["telegram"]["attempted"] == 2
            assert results["telegram"]["success"] == 2
            assert results["telegram"]["failed"] == 0
            assert results["fallback_used"] is False

        finally:
            await mock_client.aclose()

    @pytest.mark.asyncio
    async def test_fallback_scenario_integration(self, integration_alert_event):
        """Test fallback from Telegram to email in integration scenario."""

        # Create a test HTTP client that simulates Telegram failure
        class MockTransport(httpx.AsyncHTTPTransport):
            async def handle_async_request(self, request):
                # Mock Telegram API failure
                if "api.telegram.org" in str(request.url):
                    return httpx.Response(
                        401,
                        json={"ok": False, "description": "Unauthorized"},
                    )
                return httpx.Response(404)

        mock_client = httpx.AsyncClient(transport=MockTransport())

        # Create router
        router = AlertRouter(
            telegram_token="invalid_token",
            telegram_admin_ids=["123456"],
            email_sender="alerts@test.com",
            email_recipients=["fallback@test.com"],
            smtp_config={"host": "smtp.test.com", "port": 587},
            http_client=mock_client,
        )

        try:
            # Mock email sending
            with patch("app.service.alert_router.send_email") as mock_send_email:
                # Route the alert
                results = await router.route_alert(integration_alert_event)

                # Verify Telegram failed and email was used
                assert results["telegram"]["attempted"] == 1
                assert results["telegram"]["success"] == 0
                assert results["telegram"]["failed"] == 1
                assert results["email"]["attempted"] == 1
                assert results["email"]["success"] == 1
                assert results["fallback_used"] is True

                # Verify email was called
                mock_send_email.assert_called_once()

        finally:
            await mock_client.aclose()

    @pytest.mark.asyncio
    async def test_alert_types_formatting(self):
        """Test that different alert types are formatted correctly."""
        router = AlertRouter(dashboard_base_url="https://dash.test.com")

        # Test various alert types
        test_cases = [
            (
                AlertType.ASSIGNMENT_DETECTED,
                {"follower_id": "F001", "symbol": "QQQ"},
                "📋",
                "dash.test.com/followers/F001",
            ),
            (
                AlertType.NO_MARGIN,
                {"account_id": "ACC123", "required": 5000},
                "⚠️",
                "dash.test.com/accounts/ACC123",
            ),
            (
                AlertType.REPORT_FAILED,
                {"report_id": "RPT456", "error": "Database timeout"},
                "⚠️",
                "dash.test.com/reports/RPT456",
            ),
        ]

        for alert_type, params, expected_emoji, expected_link in test_cases:
            event = AlertEvent(
                event_type=alert_type,
                timestamp=datetime.now(),
                message=f"Test {alert_type.value}",
                params=params,
            )

            subject, telegram_msg, email_html = router._format_alert_message(event)

            # Check emoji
            assert expected_emoji in subject
            assert expected_emoji in telegram_msg

            # Check deep link
            assert expected_link in telegram_msg
            assert expected_link in email_html

            # Check params are included
            for key, value in params.items():
                assert str(value) in telegram_msg
                assert str(value) in email_html

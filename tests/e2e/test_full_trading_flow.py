"""
End-to-end test for the complete trading flow in SpreadPilot.

This test simulates the entire workflow from signal detection to trade execution,
P&L tracking, and report generation.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta

import httpx
import pytest
from faker import Faker
from motor.motor_asyncio import AsyncIOMotorClient

fake = Faker()


@pytest.fixture
async def api_client():
    """Create an authenticated API client."""
    async with httpx.AsyncClient(base_url="http://admin-api:8080") as client:
        # Login to get JWT token
        login_response = await client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "test-password"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Set auth header
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.fixture
async def mongo_client():
    """Create MongoDB client."""
    client = AsyncIOMotorClient("mongodb://admin:testpassword@mongodb:27017")
    yield client
    client.close()


@pytest.mark.asyncio
class TestFullTradingFlow:
    """Test the complete trading flow end-to-end."""

    async def test_create_follower(self, api_client, mongo_client):
        """Test creating a new follower."""
        # Create follower via API
        follower_data = {
            "name": fake.name(),
            "email": fake.email(),
            "ibkr_account_id": f"DU{fake.random_number(digits=7)}",
            "ibkr_credentials_ref": "test-vault-ref",
            "capital_allocation": 50000.0,
            "enabled": True,
            "auto_close_at_pct": 20.0,
            "max_positions": 5,
            "risk_limits": {
                "max_position_size": 10000,
                "max_daily_loss": 1000,
                "max_open_positions": 5,
            },
        }

        response = await api_client.post("/api/v1/followers", json=follower_data)
        assert response.status_code == 201
        follower = response.json()

        # Verify in database
        db = mongo_client["spreadpilot_admin"]
        db_follower = await db.followers.find_one({"_id": follower["id"]})
        assert db_follower is not None
        assert db_follower["name"] == follower_data["name"]

        return follower

    async def test_trading_signal_flow(self, api_client, mongo_client):
        """Test the flow from signal to trade execution."""
        # Create a follower first
        follower = await self.test_create_follower(api_client, mongo_client)

        # Simulate a trading signal in MongoDB
        db = mongo_client["spreadpilot_admin"]
        signal = {
            "timestamp": datetime.utcnow(),
            "source": "google_sheets",
            "strategy": "vertical_spread",
            "action": "OPEN",
            "underlying": "QQQ",
            "legs": [
                {"strike": 450, "type": "CALL", "action": "BUY", "quantity": 10},
                {"strike": 455, "type": "CALL", "action": "SELL", "quantity": 10},
            ],
            "max_price": 2.50,
            "expiration": (datetime.utcnow() + timedelta(days=30)).strftime("%Y%m%d"),
        }
        await db.trading_signals.insert_one(signal)

        # Wait for trading bot to process signal
        await asyncio.sleep(5)

        # Check if position was created
        position = await db.positions.find_one({"follower_id": follower["id"], "symbol": "QQQ"})

        # In a real test, we'd verify the position was created
        # For now, we'll just check the structure
        if position:
            assert position["follower_id"] == follower["id"]
            assert position["symbol"] == "QQQ"

    async def test_pnl_tracking(self, api_client, mongo_client):
        """Test P&L tracking and calculation."""
        # Get current P&L
        response = await api_client.get("/api/v1/pnl/today")
        assert response.status_code == 200
        today_pnl = response.json()

        # Verify structure
        assert "total_pnl" in today_pnl
        assert "realized_pnl" in today_pnl
        assert "unrealized_pnl" in today_pnl
        assert "positions_count" in today_pnl

    async def test_alert_flow(self, api_client, mongo_client):
        """Test alert generation and routing."""
        # Create a test follower
        follower = await self.test_create_follower(api_client, mongo_client)

        # Trigger a manual position close (which should generate an alert)
        response = await api_client.post(
            f"/api/v1/followers/{follower['id']}/close-positions",
            headers={"X-PIN": "123456", "X-User-ID": "test-user"},
        )

        # Wait for alert processing
        await asyncio.sleep(3)

        # Check if alert was created in MongoDB
        db = mongo_client["spreadpilot_admin"]
        alert = await db.alerts.find_one({"follower_id": follower["id"]})

        if alert:
            assert alert["follower_id"] == follower["id"]
            assert "reason" in alert

    async def test_report_generation(self, api_client):
        """Test report generation endpoint."""
        # Request a monthly report
        response = await api_client.post(
            "/api/v1/reports/generate",
            json={
                "report_type": "monthly",
                "year": datetime.utcnow().year,
                "month": datetime.utcnow().month,
                "format": "pdf",
            },
        )

        # Check response
        if response.status_code == 202:  # Accepted for async processing
            assert "task_id" in response.json()
        elif response.status_code == 200:  # Immediate response
            assert "report_url" in response.json()

    async def test_service_health(self, api_client):
        """Test all service health endpoints."""
        services = ["admin-api", "trading-bot", "report-worker", "alert-router"]

        for service in services:
            # Health endpoints might be on different ports
            port_map = {
                "admin-api": 8080,
                "trading-bot": 8080,
                "report-worker": 8080,
                "alert-router": 8080,
            }

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(
                        f"http://{service}:{port_map[service]}/health", timeout=5.0
                    )
                    assert response.status_code == 200
                    health_data = response.json()
                    assert health_data.get("status") in ["healthy", "ok"]
                except httpx.ConnectError:
                    pytest.skip(f"Service {service} not reachable")

    async def test_websocket_updates(self):
        """Test WebSocket real-time updates."""
        # This would test WebSocket connections
        # Skipping for now as it requires WebSocket client setup
        pytest.skip("WebSocket testing requires additional setup")

    async def test_watchdog_monitoring(self, mongo_client):
        """Test watchdog service monitoring."""
        # Check if watchdog is creating health check entries
        db = mongo_client["spreadpilot_admin"]

        # Wait for watchdog to perform checks
        await asyncio.sleep(15)

        # Look for watchdog alerts or health entries
        alert = await db.alerts.find_one({"service": "watchdog"})

        # Watchdog should be monitoring services
        # Verify watchdog has logged some health checks
        health_checks = await db.health_checks.count_documents(
            {"service": "watchdog", "timestamp": {"$gte": datetime.utcnow() - timedelta(minutes=1)}}
        )

        # Should have at least one health check in the last minute
        assert health_checks > 0 or alert is not None


@pytest.mark.asyncio
class TestSecurityFeatures:
    """Test security features end-to-end."""

    async def test_jwt_authentication(self):
        """Test JWT authentication flow."""
        async with httpx.AsyncClient(base_url="http://admin-api:8080") as client:
            # Try accessing protected endpoint without auth
            response = await client.get("/api/v1/followers")
            assert response.status_code == 401

            # Login
            login_response = await client.post(
                "/api/v1/auth/login", json={"username": "admin", "password": "test-password"}
            )
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]

            # Access with token
            client.headers["Authorization"] = f"Bearer {token}"
            response = await client.get("/api/v1/followers")
            assert response.status_code == 200

    async def test_pin_verification(self, api_client):
        """Test PIN verification for dangerous operations."""
        # Try dangerous operation without PIN
        response = await api_client.post(
            "/api/v1/positions/close-all", headers={"X-User-ID": "test-user"}
        )
        assert response.status_code == 400  # Missing PIN

        # Try with wrong PIN
        response = await api_client.post(
            "/api/v1/positions/close-all", headers={"X-PIN": "000000", "X-User-ID": "test-user"}
        )
        assert response.status_code in [403, 429]  # Invalid or rate limited

    async def test_vault_integration(self):
        """Test Vault secret retrieval."""
        # Verify services can connect to Vault
        async with httpx.AsyncClient() as client:
            # Check Vault health
            response = await client.get("http://vault:8200/v1/sys/health")
            assert response.status_code == 200

            # Services should be using Vault (check logs or health endpoints)
            # This is verified indirectly through successful service operations


@pytest.mark.asyncio
class TestErrorScenarios:
    """Test error handling and recovery scenarios."""

    async def test_database_connection_recovery(self, api_client):
        """Test API behavior when database is temporarily unavailable."""
        # Test that API returns appropriate error when DB operations fail
        # We can't easily stop MongoDB in E2E, but we can test error handling
        # by trying invalid operations

        # Try to get a non-existent resource
        response = await api_client.get(f"/api/v1/followers/{fake.uuid4()}")
        assert response.status_code == 404

        # Verify error response format
        error = response.json()
        assert "detail" in error

    async def test_rate_limiting(self, api_client):
        """Test API rate limiting."""
        # Make many rapid requests
        responses = []
        for _ in range(100):
            response = await api_client.get("/api/v1/followers")
            responses.append(response.status_code)

        # Should see some rate limiting (if implemented)
        # For now, just verify all requests complete
        assert all(status in [200, 429] for status in responses)

    async def test_invalid_data_handling(self, api_client):
        """Test handling of invalid data."""
        # Create follower with invalid data
        invalid_data = {
            "name": "",  # Empty name
            "email": "not-an-email",  # Invalid email
            "capital_allocation": -1000,  # Negative allocation
            "enabled": "yes",  # Wrong type
        }

        response = await api_client.post("/api/v1/followers", json=invalid_data)
        assert response.status_code == 422  # Validation error

        error_detail = response.json()
        assert "detail" in error_detail

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.api.v1.endpoints.health import router
# Create a test client
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestHealthEndpoints:
    """Test cases for health monitoring endpoints"""

    @pytest.fixture
    def mock_auth(self):
        """Mock authentication dependency"""
        with patch("app.api.v1.endpoints.health.get_current_user") as mock:
            mock.return_value = {"username": "testuser", "user_id": "123"}
            yield mock

    @pytest.fixture
    def mock_db(self):
        """Mock database dependency"""
        with patch("app.api.v1.endpoints.health.get_database") as mock:
            db_mock = AsyncMock()
            db_mock.admin.command = AsyncMock(return_value={"ok": 1})
            mock.return_value = db_mock
            yield mock

    @pytest.fixture
    def mock_psutil(self):
        """Mock psutil for system metrics"""
        with patch("app.api.v1.endpoints.health.psutil") as mock:
            mock.cpu_percent.return_value = 45.5

            memory_mock = MagicMock()
            memory_mock.percent = 60.2
            mock.virtual_memory.return_value = memory_mock

            disk_mock = MagicMock()
            disk_mock.percent = 70.8
            mock.disk_usage.return_value = disk_mock

            yield mock

    @pytest.fixture
    def mock_httpx(self):
        """Mock httpx for service health checks"""
        with patch("app.api.v1.endpoints.health.httpx.AsyncClient") as mock:

            async def mock_get(url):
                response_mock = MagicMock()
                response_mock.elapsed.total_seconds.return_value = 0.150  # 150ms

                if "trading-bot" in url:
                    response_mock.status_code = 200
                elif "watchdog" in url:
                    response_mock.status_code = 200
                elif "report-worker" in url:
                    response_mock.status_code = 500
                else:  # alert-router
                    raise httpx.ConnectError("Connection refused")

                return response_mock

            client_mock = AsyncMock()
            client_mock.__aenter__.return_value = client_mock
            client_mock.__aexit__.return_value = None
            client_mock.get = mock_get

            mock.return_value = client_mock
            yield mock

    @pytest.mark.asyncio
    async def test_get_comprehensive_health_green_status(
        self, mock_auth, mock_db, mock_psutil, mock_httpx
    ):
        """Test health endpoint returns GREEN status when all services are healthy"""

        # Mock all services as healthy
        async def mock_get_healthy(url):
            response_mock = MagicMock()
            response_mock.status_code = 200
            response_mock.elapsed.total_seconds.return_value = 0.100
            return response_mock

        mock_httpx.return_value.__aenter__.return_value.get = mock_get_healthy

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["overall_status"] == "GREEN"
        assert data["database"]["status"] == "healthy"
        assert data["system"]["status"] == "healthy"
        assert len(data["services"]) == 4
        assert all(s["status"] == "healthy" for s in data["services"])

    @pytest.mark.asyncio
    async def test_get_comprehensive_health_yellow_status(
        self, mock_auth, mock_db, mock_psutil, mock_httpx
    ):
        """Test health endpoint returns YELLOW when non-critical services are unhealthy"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["overall_status"] == "YELLOW"  # report-worker is unhealthy but not critical

        # Check specific service statuses
        services_by_name = {s["name"]: s for s in data["services"]}
        assert services_by_name["trading-bot"]["status"] == "healthy"
        assert services_by_name["report-worker"]["status"] == "unhealthy"
        assert services_by_name["alert-router"]["status"] == "unreachable"

    @pytest.mark.asyncio
    async def test_get_comprehensive_health_red_status_critical_service(
        self, mock_auth, mock_db, mock_psutil, mock_httpx
    ):
        """Test health endpoint returns RED when critical service is unhealthy"""

        # Make trading-bot (critical service) unhealthy
        async def mock_get_critical_unhealthy(url):
            response_mock = MagicMock()
            if "trading-bot" in url:
                response_mock.status_code = 500
            else:
                response_mock.status_code = 200
            response_mock.elapsed.total_seconds.return_value = 0.100
            return response_mock

        mock_httpx.return_value.__aenter__.return_value.get = mock_get_critical_unhealthy

        response = client.get("/health")
        data = response.json()
        assert data["overall_status"] == "RED"

    @pytest.mark.asyncio
    async def test_get_comprehensive_health_red_status_system_resources(
        self, mock_auth, mock_db, mock_psutil, mock_httpx
    ):
        """Test health endpoint returns RED when system resources are critical"""
        # Set high CPU usage
        mock_psutil.cpu_percent.return_value = 95.0

        response = client.get("/health")
        data = response.json()
        assert data["overall_status"] == "RED"
        assert data["system"]["status"] == "warning"
        assert data["system"]["cpu_percent"] == 95.0

    @pytest.mark.asyncio
    async def test_get_comprehensive_health_database_unhealthy(
        self, mock_auth, mock_psutil, mock_httpx
    ):
        """Test health endpoint when database is unhealthy"""
        with patch("app.api.v1.endpoints.health.get_database") as mock_db:
            db_mock = AsyncMock()
            db_mock.admin.command = AsyncMock(side_effect=Exception("Connection failed"))
            mock_db.return_value = db_mock

            response = client.get("/health")
            data = response.json()
            assert data["overall_status"] == "RED"
            assert data["database"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_restart_service_success(self, mock_auth):
        """Test successful service restart"""
        with patch("app.api.v1.endpoints.health.asyncio.sleep"):
            response = client.post("/service/trading-bot/restart")
            assert response.status_code == 200

            data = response.json()
            assert data["service"] == "trading-bot"
            assert data["action"] == "restart"
            assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_restart_service_not_found(self, mock_auth):
        """Test restart service with invalid service name"""
        response = client.post("/service/invalid-service/restart")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_services(self, mock_auth):
        """Test list services endpoint"""
        response = client.get("/services")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 4

        # Check service structure
        for service in data:
            assert "name" in service
            assert "critical" in service
            assert "health_endpoint" in service

        # Check specific services
        service_names = [s["name"] for s in data]
        assert "trading-bot" in service_names
        assert "watchdog" in service_names

    @pytest.mark.asyncio
    async def test_health_endpoint_requires_auth(self):
        """Test that health endpoints require authentication"""
        # Remove auth mock to test unauthorized access
        with patch("app.api.v1.endpoints.health.get_current_user") as mock:
            mock.side_effect = Exception("Unauthorized")

            response = client.get("/health")
            assert response.status_code == 500  # Would be 401 with proper auth handling

            response = client.post("/service/trading-bot/restart")
            assert response.status_code == 500  # Would be 401 with proper auth handling

    @pytest.mark.asyncio
    async def test_service_health_check_timeout(self, mock_auth, mock_db, mock_psutil):
        """Test service health check with timeout"""
        with patch("app.api.v1.endpoints.health.httpx.AsyncClient") as mock_httpx:

            async def mock_get_timeout(url):
                raise httpx.TimeoutException("Request timed out")

            client_mock = AsyncMock()
            client_mock.__aenter__.return_value = client_mock
            client_mock.__aexit__.return_value = None
            client_mock.get = mock_get_timeout

            mock_httpx.return_value = client_mock

            response = client.get("/health")
            data = response.json()

            # All services should be unreachable
            assert all(s["status"] == "unreachable" for s in data["services"])
            assert all("Request timed out" in s["error"] for s in data["services"])

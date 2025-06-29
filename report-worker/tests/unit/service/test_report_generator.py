"""Unit tests for report generator service."""

import datetime
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.cloud.exceptions import GoogleCloudError

from spreadpilot_core.models import Follower

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from app.config import Settings
from app.service.report_generator import (
    ReportGenerator,
    generate_follower_reports,
)


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Settings()
    settings.gcs_bucket_name = "test-bucket"
    settings.project_id = "test-project"
    return settings


@pytest.fixture
def sample_follower():
    """Sample follower for testing."""
    return Follower(
        id="follower123",
        email="test@example.com",
        iban="DE12345678901234567890",
        commission_pct=20.0,
        active=True,
    )


@pytest.fixture
def sample_daily_pnl():
    """Sample daily P&L data."""
    return {
        "20241201": 150.25,
        "20241202": -75.50,
        "20241203": 200.00,
        "20241204": 125.75,
        "20241205": -50.25,
    }


@pytest.fixture
def mock_pnl_daily_records():
    """Mock PnL daily records."""
    records = []
    dates = [
        datetime.date(2024, 12, 1),
        datetime.date(2024, 12, 2),
        datetime.date(2024, 12, 3),
        datetime.date(2024, 12, 4),
        datetime.date(2024, 12, 5),
    ]
    pnl_values = [150.25, -75.50, 200.00, 125.75, -50.25]

    for date, pnl in zip(dates, pnl_values, strict=False):
        record = MagicMock()
        record.date = date
        record.pnl_total = pnl
        records.append(record)

    return records


@pytest.fixture
def mock_commission_record():
    """Mock commission record."""
    record = MagicMock()
    record.pnl_total = 350.25
    record.commission_amount = 70.05
    return record


@pytest.mark.asyncio
class TestReportGenerator:
    """Test cases for ReportGenerator class."""

    def test_init_with_gcs_bucket(self, mock_settings):
        """Test initialization with GCS bucket configured."""
        with patch(
            "report_worker.app.service.report_generator.storage.Client"
        ) as mock_client:
            mock_bucket = MagicMock()
            mock_client.return_value.bucket.return_value = mock_bucket

            generator = ReportGenerator(mock_settings)

            assert generator.gcs_client is not None
            assert generator.bucket is mock_bucket
            mock_client.assert_called_once()

    def test_init_without_gcs_bucket(self):
        """Test initialization without GCS bucket configured."""
        settings = Settings()
        settings.gcs_bucket_name = None

        generator = ReportGenerator(settings)

        assert generator.gcs_client is None
        assert generator.bucket is None

    def test_init_gcs_error(self, mock_settings):
        """Test initialization with GCS error."""
        with patch(
            "report_worker.app.service.report_generator.storage.Client"
        ) as mock_client:
            mock_client.side_effect = Exception("GCS error")

            generator = ReportGenerator(mock_settings)

            assert generator.gcs_client is None
            assert generator.bucket is None

    async def test_get_daily_pnl_data_success(
        self, mock_settings, sample_follower, mock_pnl_daily_records
    ):
        """Test successful retrieval of daily P&L data."""
        generator = ReportGenerator(mock_settings)

        # Mock database session and query
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_pnl_daily_records
        mock_session.execute.return_value = mock_result

        with patch(
            "report_worker.app.service.report_generator.get_async_db_session"
        ) as mock_db:
            mock_db.return_value.__aenter__.return_value = mock_session

            result = await generator.get_daily_pnl_data(sample_follower.id, 2024, 12)

            expected = {
                "20241201": 150.25,
                "20241202": -75.50,
                "20241203": 200.00,
                "20241204": 125.75,
                "20241205": -50.25,
            }
            assert result == expected

    async def test_get_daily_pnl_data_error(self, mock_settings, sample_follower):
        """Test error handling in daily P&L data retrieval."""
        generator = ReportGenerator(mock_settings)

        with patch(
            "report_worker.app.service.report_generator.get_async_db_session"
        ) as mock_db:
            mock_db.side_effect = Exception("Database error")

            result = await generator.get_daily_pnl_data(sample_follower.id, 2024, 12)

            assert result == {}

    async def test_get_commission_data_success(
        self, mock_settings, sample_follower, mock_commission_record
    ):
        """Test successful retrieval of commission data."""
        generator = ReportGenerator(mock_settings)

        # Mock database session and query
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_commission_record
        mock_session.execute.return_value = mock_result

        with patch(
            "report_worker.app.service.report_generator.get_async_db_session"
        ) as mock_db:
            mock_db.return_value.__aenter__.return_value = mock_session

            total_pnl, commission = await generator.get_commission_data(
                sample_follower.id, 2024, 12
            )

            assert total_pnl == 350.25
            assert commission == 70.05

    async def test_get_commission_data_not_found(self, mock_settings, sample_follower):
        """Test commission data retrieval when record not found."""
        generator = ReportGenerator(mock_settings)

        # Mock database session and query
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch(
            "report_worker.app.service.report_generator.get_async_db_session"
        ) as mock_db:
            mock_db.return_value.__aenter__.return_value = mock_session

            total_pnl, commission = await generator.get_commission_data(
                sample_follower.id, 2024, 12
            )

            assert total_pnl == 0.0
            assert commission == 0.0

    async def test_get_commission_data_error(self, mock_settings, sample_follower):
        """Test error handling in commission data retrieval."""
        generator = ReportGenerator(mock_settings)

        with patch(
            "report_worker.app.service.report_generator.get_async_db_session"
        ) as mock_db:
            mock_db.side_effect = Exception("Database error")

            total_pnl, commission = await generator.get_commission_data(
                sample_follower.id, 2024, 12
            )

            assert total_pnl == 0.0
            assert commission == 0.0

    async def test_generate_pdf_report_success(
        self, mock_settings, sample_follower, sample_daily_pnl
    ):
        """Test successful PDF report generation."""
        generator = ReportGenerator(mock_settings)

        # Mock data retrieval methods
        generator.get_daily_pnl_data = AsyncMock(return_value=sample_daily_pnl)
        generator.get_commission_data = AsyncMock(return_value=(350.25, 70.05))

        with patch(
            "report_worker.app.service.report_generator.generate_pdf_report"
        ) as mock_pdf:
            mock_pdf.return_value = "/tmp/test_report.pdf"

            result = await generator.generate_pdf_report(sample_follower, 2024, 12)

            assert result == "/tmp/test_report.pdf"
            mock_pdf.assert_called_once()

            # Verify call arguments
            call_args = mock_pdf.call_args
            assert call_args[1]["follower"] == sample_follower
            assert call_args[1]["month"] == 12
            assert call_args[1]["year"] == 2024
            assert call_args[1]["pnl_total"] == 350.25
            assert call_args[1]["commission_amount"] == 70.05
            assert call_args[1]["daily_pnl"] == sample_daily_pnl

    async def test_generate_excel_report_success(
        self, mock_settings, sample_follower, sample_daily_pnl
    ):
        """Test successful Excel report generation."""
        generator = ReportGenerator(mock_settings)

        # Mock data retrieval methods
        generator.get_daily_pnl_data = AsyncMock(return_value=sample_daily_pnl)
        generator.get_commission_data = AsyncMock(return_value=(350.25, 70.05))

        with patch(
            "report_worker.app.service.report_generator.generate_excel_report"
        ) as mock_excel:
            mock_excel.return_value = "/tmp/test_report.xlsx"

            result = await generator.generate_excel_report(sample_follower, 2024, 12)

            assert result == "/tmp/test_report.xlsx"
            mock_excel.assert_called_once()

            # Verify call arguments
            call_args = mock_excel.call_args
            assert call_args[1]["follower"] == sample_follower
            assert call_args[1]["month"] == 12
            assert call_args[1]["year"] == 2024
            assert call_args[1]["pnl_total"] == 350.25
            assert call_args[1]["commission_amount"] == 70.05
            assert call_args[1]["daily_pnl"] == sample_daily_pnl

    def test_upload_to_gcs_success(self, mock_settings):
        """Test successful GCS upload."""
        with patch("report_worker.app.service.report_generator.storage.Client"):
            generator = ReportGenerator(mock_settings)

            # Mock successful upload
            mock_blob = MagicMock()
            generator.bucket = MagicMock()
            generator.bucket.blob.return_value = mock_blob

            result = generator.upload_to_gcs("/tmp/test.pdf", "reports/test.pdf")

            assert result is True
            generator.bucket.blob.assert_called_once_with("reports/test.pdf")
            mock_blob.upload_from_filename.assert_called_once_with("/tmp/test.pdf")

    def test_upload_to_gcs_no_bucket(self):
        """Test GCS upload when no bucket configured."""
        settings = Settings()
        generator = ReportGenerator(settings)

        result = generator.upload_to_gcs("/tmp/test.pdf", "reports/test.pdf")

        assert result is False

    def test_upload_to_gcs_error(self, mock_settings):
        """Test GCS upload error handling."""
        with patch("report_worker.app.service.report_generator.storage.Client"):
            generator = ReportGenerator(mock_settings)

            # Mock upload error
            mock_blob = MagicMock()
            mock_blob.upload_from_filename.side_effect = GoogleCloudError(
                "Upload failed"
            )
            generator.bucket = MagicMock()
            generator.bucket.blob.return_value = mock_blob

            result = generator.upload_to_gcs("/tmp/test.pdf", "reports/test.pdf")

            assert result is False

    def test_generate_signed_url_success(self, mock_settings):
        """Test successful signed URL generation."""
        with patch("report_worker.app.service.report_generator.storage.Client"):
            generator = ReportGenerator(mock_settings)

            # Mock successful signed URL generation
            mock_blob = MagicMock()
            mock_blob.generate_signed_url.return_value = (
                "https://storage.googleapis.com/signed-url"
            )
            generator.bucket = MagicMock()
            generator.bucket.blob.return_value = mock_blob

            result = generator.generate_signed_url("reports/test.pdf", 24)

            assert result == "https://storage.googleapis.com/signed-url"
            generator.bucket.blob.assert_called_once_with("reports/test.pdf")
            mock_blob.generate_signed_url.assert_called_once()

    def test_generate_signed_url_no_bucket(self):
        """Test signed URL generation when no bucket configured."""
        settings = Settings()
        generator = ReportGenerator(settings)

        result = generator.generate_signed_url("reports/test.pdf", 24)

        assert result is None

    def test_generate_signed_url_error(self, mock_settings):
        """Test signed URL generation error handling."""
        with patch("report_worker.app.service.report_generator.storage.Client"):
            generator = ReportGenerator(mock_settings)

            # Mock signed URL error
            mock_blob = MagicMock()
            mock_blob.generate_signed_url.side_effect = GoogleCloudError(
                "URL generation failed"
            )
            generator.bucket = MagicMock()
            generator.bucket.blob.return_value = mock_blob

            result = generator.generate_signed_url("reports/test.pdf", 24)

            assert result is None

    async def test_generate_and_store_reports_success(
        self, mock_settings, sample_follower
    ):
        """Test successful report generation and storage."""
        with patch("report_worker.app.service.report_generator.storage.Client"):
            generator = ReportGenerator(mock_settings)

            # Mock report generation methods
            generator.generate_pdf_report = AsyncMock(return_value="/tmp/test.pdf")
            generator.generate_excel_report = AsyncMock(return_value="/tmp/test.xlsx")
            generator.upload_to_gcs = MagicMock(return_value=True)
            generator.generate_signed_url = MagicMock(
                side_effect=["https://pdf-url", "https://excel-url"]
            )

            with (
                patch("os.remove") as mock_remove,
                patch("os.listdir", return_value=[]),
                patch("os.rmdir") as mock_rmdir,
            ):

                result = await generator.generate_and_store_reports(
                    sample_follower, 2024, 12, formats=["pdf", "excel"]
                )

                expected = {"pdf": "https://pdf-url", "excel": "https://excel-url"}
                assert result == expected

                # Verify cleanup
                assert mock_remove.call_count == 2
                assert mock_rmdir.call_count == 2

    async def test_generate_and_store_reports_upload_failure(
        self, mock_settings, sample_follower
    ):
        """Test report generation with upload failure."""
        with patch("report_worker.app.service.report_generator.storage.Client"):
            generator = ReportGenerator(mock_settings)

            # Mock report generation methods
            generator.generate_pdf_report = AsyncMock(return_value="/tmp/test.pdf")
            generator.upload_to_gcs = MagicMock(return_value=False)  # Upload fails

            with patch("os.remove"):
                result = await generator.generate_and_store_reports(
                    sample_follower, 2024, 12, formats=["pdf"]
                )

                expected = {"pdf": None}
                assert result == expected

    async def test_generate_and_store_reports_unsupported_format(
        self, mock_settings, sample_follower
    ):
        """Test report generation with unsupported format."""
        with patch("report_worker.app.service.report_generator.storage.Client"):
            generator = ReportGenerator(mock_settings)

            result = await generator.generate_and_store_reports(
                sample_follower, 2024, 12, formats=["unsupported"]
            )

            expected = {"unsupported": None}
            assert result == expected


@pytest.mark.asyncio
async def test_generate_follower_reports_convenience_function(
    mock_settings, sample_follower
):
    """Test the convenience function for generating follower reports."""
    with patch(
        "report_worker.app.service.report_generator.ReportGenerator"
    ) as mock_generator_class:
        mock_generator = MagicMock()
        mock_generator.generate_and_store_reports = AsyncMock(
            return_value={"pdf": "https://pdf-url", "excel": "https://excel-url"}
        )
        mock_generator_class.return_value = mock_generator

        result = await generate_follower_reports(
            sample_follower, 2024, 12, mock_settings, formats=["pdf", "excel"]
        )

        expected = {"pdf": "https://pdf-url", "excel": "https://excel-url"}
        assert result == expected

        mock_generator_class.assert_called_once_with(mock_settings)
        mock_generator.generate_and_store_reports.assert_called_once_with(
            follower=sample_follower,
            year=2024,
            month=12,
            formats=["pdf", "excel"],
            logo_path=None,
            expiration_hours=24,
        )

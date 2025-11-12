"""Unit tests for enhanced notifier with MinIO integration."""

import os
from unittest.mock import patch

import pytest

# Set TESTING environment variable before imports
os.environ["TESTING"] = "true"

from app.service.notifier_minio import send_report_email_with_minio
from spreadpilot_core.models.follower import Follower


@pytest.fixture
def mock_follower():
    """Create a mock follower."""
    return Follower(
        id="test-follower-123",
        name="Test Follower",
        email="test@example.com",
        enabled=True,
        commission_pct=20.0,
    )


@pytest.fixture
def test_files(tmp_path):
    """Create test PDF and Excel files."""
    pdf_file = tmp_path / "report.pdf"
    pdf_file.write_bytes(b"PDF content")

    excel_file = tmp_path / "report.xlsx"
    excel_file.write_bytes(b"Excel content")

    return str(pdf_file), str(excel_file)


class TestNotifierMinIO:
    """Test cases for enhanced notifier with MinIO."""

    @patch("app.service.notifier_minio.minio_service")
    @patch("app.service.notifier_minio.send_email")
    @patch("app.service.notifier_minio.config")
    def test_send_with_minio_success(
        self, mock_config, mock_send_email, mock_minio, mock_follower, test_files
    ):
        """Test successful email send with MinIO URLs."""
        pdf_path, excel_path = test_files

        # Configure mocks
        mock_config.REPORT_SENDER_EMAIL = "sender@example.com"
        mock_config.ADMIN_EMAIL = "admin@example.com"

        mock_minio.is_configured.return_value = True
        mock_minio.upload_report_with_url.side_effect = [
            (
                "reports/2025-05/test-follower-123/report_2025-05.pdf",
                "https://minio.example.com/pdf-url",
            ),
            (
                "reports/2025-05/test-follower-123/report_2025-05.xlsx",
                "https://minio.example.com/excel-url",
            ),
        ]

        mock_send_email.return_value = True

        # Call function
        success, report_info = send_report_email_with_minio(
            mock_follower, "2025-05", pdf_path, excel_path
        )

        # Verify results
        assert success is True
        assert report_info["pdf_url"] == "https://minio.example.com/pdf-url"
        assert report_info["excel_url"] == "https://minio.example.com/excel-url"
        assert report_info["email_sent"] is True

        # Verify MinIO calls
        assert mock_minio.upload_report_with_url.call_count == 2
        mock_minio.upload_report_with_url.assert_any_call(
            pdf_path, "test-follower-123", "2025-05", "pdf"
        )
        mock_minio.upload_report_with_url.assert_any_call(
            excel_path, "test-follower-123", "2025-05", "xlsx"
        )

        # Verify email was sent with links (not attachments)
        mock_send_email.assert_called_once()
        email_args = mock_send_email.call_args[1]
        assert email_args["from_email"] == "sender@example.com"
        assert email_args["to_email"] == "test@example.com"
        assert email_args["cc_recipients"] == ["admin@example.com"]
        assert email_args["attachments"] == []  # No attachments when using MinIO
        assert "https://minio.example.com/pdf-url" in email_args["html_content"]
        assert "https://minio.example.com/excel-url" in email_args["html_content"]

    @patch("app.service.notifier_minio.minio_service")
    @patch("app.service.notifier_minio.send_email")
    @patch("app.service.notifier_minio.config")
    def test_send_fallback_to_attachments(
        self, mock_config, mock_send_email, mock_minio, mock_follower, test_files
    ):
        """Test fallback to attachments when MinIO is not configured."""
        pdf_path, excel_path = test_files

        # Configure mocks
        mock_config.REPORT_SENDER_EMAIL = "sender@example.com"
        mock_config.ADMIN_EMAIL = None

        mock_minio.is_configured.return_value = False
        mock_send_email.return_value = True

        # Call function
        success, report_info = send_report_email_with_minio(
            mock_follower, "2025-05", pdf_path, excel_path
        )

        # Verify results
        assert success is True
        assert report_info["pdf_url"] is None
        assert report_info["excel_url"] is None
        assert report_info["email_sent"] is True

        # Verify MinIO was not called
        mock_minio.upload_report_with_url.assert_not_called()

        # Verify email was sent with attachments
        mock_send_email.assert_called_once()
        email_args = mock_send_email.call_args[1]
        assert email_args["attachments"] == [
            {"path": pdf_path, "filename": "SpreadPilot_Report_2025-05.pdf"},
            {"path": excel_path, "filename": "SpreadPilot_Report_2025-05.xlsx"},
        ]
        assert "Please find attached" in email_args["html_content"]

    @patch("app.service.notifier_minio.minio_service")
    @patch("app.service.notifier_minio.send_email")
    def test_send_pdf_not_found(self, mock_send_email, mock_minio, mock_follower):
        """Test handling of missing PDF file."""
        success, report_info = send_report_email_with_minio(
            mock_follower,
            "2025-05",
            "/nonexistent/report.pdf",
            "/nonexistent/report.xlsx",
        )

        assert success is False
        assert report_info["email_sent"] is False
        mock_send_email.assert_not_called()

    @patch("app.service.notifier_minio.minio_service")
    @patch("app.service.notifier_minio.send_email")
    def test_send_follower_no_email(self, mock_send_email, mock_minio, test_files):
        """Test handling of follower without email."""
        pdf_path, excel_path = test_files

        follower = Follower(id="no-email-follower", name="No Email", enabled=True)

        success, report_info = send_report_email_with_minio(
            follower, "2025-05", pdf_path, excel_path
        )

        assert success is False
        assert report_info["email_sent"] is False
        mock_send_email.assert_not_called()

    @patch("app.service.notifier_minio.minio_service")
    @patch("app.service.notifier_minio.send_email")
    @patch("app.service.notifier_minio.config")
    def test_send_email_failure(
        self, mock_config, mock_send_email, mock_minio, mock_follower, test_files
    ):
        """Test handling of email send failure."""
        pdf_path, excel_path = test_files

        mock_config.REPORT_SENDER_EMAIL = "sender@example.com"
        mock_config.ADMIN_EMAIL = None

        mock_minio.is_configured.return_value = False
        mock_send_email.return_value = False  # Email send fails

        success, report_info = send_report_email_with_minio(
            mock_follower, "2025-05", pdf_path, excel_path
        )

        assert success is False
        assert report_info["email_sent"] is False

    @patch("app.service.notifier_minio.minio_service")
    @patch("app.service.notifier_minio.send_email")
    @patch("app.service.notifier_minio.config")
    def test_partial_minio_upload(
        self, mock_config, mock_send_email, mock_minio, mock_follower, test_files
    ):
        """Test when only one file uploads to MinIO successfully."""
        pdf_path, excel_path = test_files

        mock_config.REPORT_SENDER_EMAIL = "sender@example.com"
        mock_config.ADMIN_EMAIL = None

        mock_minio.is_configured.return_value = True
        mock_minio.upload_report_with_url.side_effect = [
            (
                "reports/2025-05/test-follower-123/report_2025-05.pdf",
                "https://minio.example.com/pdf-url",
            ),
            (None, None),  # Excel upload fails
        ]

        mock_send_email.return_value = True

        success, report_info = send_report_email_with_minio(
            mock_follower, "2025-05", pdf_path, excel_path
        )

        # Should fall back to attachments when partial upload
        assert success is True
        assert report_info["pdf_url"] == "https://minio.example.com/pdf-url"
        assert report_info["excel_url"] is None
        assert report_info["email_sent"] is True

        # Verify email was sent with attachments (fallback)
        email_args = mock_send_email.call_args[1]
        assert len(email_args["attachments"]) == 2  # Both files as attachments
        assert "Please find attached" in email_args["html_content"]

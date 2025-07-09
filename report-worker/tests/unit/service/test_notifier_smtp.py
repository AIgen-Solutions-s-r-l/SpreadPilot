"""Unit tests for SMTP notifier with MinIO integration."""

import os
from unittest.mock import AsyncMock, patch

import pytest

# Set TESTING environment variable before imports
os.environ["TESTING"] = "true"

from spreadpilot_core.models.follower import Follower

from app.service.notifier_smtp import send_report_email_with_smtp


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


class TestNotifierSMTP:
    """Test cases for SMTP notifier with MinIO."""

    @pytest.mark.asyncio
    @patch("app.service.notifier_smtp.minio_service")
    @patch("app.service.notifier_smtp.SMTPEmailSender")
    @patch("app.service.notifier_smtp.config")
    async def test_send_with_minio_and_smtp_success(
        self, mock_config, mock_smtp_class, mock_minio, mock_follower, test_files
    ):
        """Test successful email send via SMTP with MinIO URLs."""
        pdf_path, excel_path = test_files

        # Configure mocks
        mock_config.SMTP_URI = "smtp://user:pass@smtp.example.com:587"
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

        # Mock SMTP sender
        mock_smtp_sender = AsyncMock()
        mock_smtp_sender.send_email.return_value = True
        mock_smtp_class.return_value = mock_smtp_sender

        # Call function
        success, report_info = await send_report_email_with_smtp(
            mock_follower, "2025-05", pdf_path, excel_path
        )

        # Verify results
        assert success is True
        assert report_info["pdf_url"] == "https://minio.example.com/pdf-url"
        assert report_info["excel_url"] == "https://minio.example.com/excel-url"
        assert report_info["email_sent"] is True

        # Verify MinIO calls
        assert mock_minio.upload_report_with_url.call_count == 2

        # Verify SMTP sender was initialized with URI
        mock_smtp_class.assert_called_once_with("smtp://user:pass@smtp.example.com:587")

        # Verify email was sent with links (not attachments)
        mock_smtp_sender.send_email.assert_called_once()
        email_args = mock_smtp_sender.send_email.call_args[1]
        assert email_args["from_email"] == "sender@example.com"
        assert email_args["to_email"] == "test@example.com"
        assert email_args["cc_recipients"] == ["admin@example.com"]
        assert email_args["attachments"] == []  # No attachments when using MinIO
        assert "https://minio.example.com/pdf-url" in email_args["html_content"]
        assert "https://minio.example.com/excel-url" in email_args["html_content"]

    @pytest.mark.asyncio
    @patch("app.service.notifier_smtp.minio_service")
    @patch("app.service.notifier_smtp.SMTPEmailSender")
    @patch("app.service.notifier_smtp.config")
    async def test_send_fallback_to_attachments_smtp(
        self, mock_config, mock_smtp_class, mock_minio, mock_follower, test_files
    ):
        """Test fallback to attachments when MinIO is not configured."""
        pdf_path, excel_path = test_files

        # Configure mocks
        mock_config.SMTP_URI = "smtp://smtp.example.com:587"
        mock_config.REPORT_SENDER_EMAIL = "sender@example.com"
        mock_config.ADMIN_EMAIL = None

        mock_minio.is_configured.return_value = False

        # Mock SMTP sender
        mock_smtp_sender = AsyncMock()
        mock_smtp_sender.send_email.return_value = True
        mock_smtp_class.return_value = mock_smtp_sender

        # Call function
        success, report_info = await send_report_email_with_smtp(
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
        email_args = mock_smtp_sender.send_email.call_args[1]
        assert email_args["attachments"] == [
            {"path": pdf_path, "filename": "SpreadPilot_Report_2025-05.pdf"},
            {"path": excel_path, "filename": "SpreadPilot_Report_2025-05.xlsx"},
        ]
        assert "Please find attached" in email_args["html_content"]

    @pytest.mark.asyncio
    @patch("app.service.notifier_smtp.minio_service")
    @patch("app.service.notifier_smtp.SMTPEmailSender")
    @patch("app.service.notifier_smtp.config")
    async def test_send_with_custom_smtp_uri(
        self, mock_config, mock_smtp_class, mock_minio, mock_follower, test_files
    ):
        """Test using custom SMTP URI parameter."""
        pdf_path, excel_path = test_files

        # Configure mocks
        mock_config.SMTP_URI = "smtp://default@example.com:587"  # Default from config
        mock_config.REPORT_SENDER_EMAIL = "sender@example.com"
        mock_config.ADMIN_EMAIL = None

        mock_minio.is_configured.return_value = False

        # Mock SMTP sender
        mock_smtp_sender = AsyncMock()
        mock_smtp_sender.send_email.return_value = True
        mock_smtp_class.return_value = mock_smtp_sender

        # Call function with custom SMTP URI
        custom_uri = "smtps://custom:pass@custom.smtp.com:465"
        success, report_info = await send_report_email_with_smtp(
            mock_follower, "2025-05", pdf_path, excel_path, smtp_uri=custom_uri
        )

        # Verify custom URI was used
        mock_smtp_class.assert_called_once_with(custom_uri)
        assert success is True

    @pytest.mark.asyncio
    @patch("app.service.notifier_smtp.minio_service")
    @patch("app.service.notifier_smtp.SMTPEmailSender")
    @patch("app.service.notifier_smtp.config")
    async def test_send_no_smtp_uri_configured(
        self, mock_config, mock_smtp_class, mock_minio, mock_follower, test_files
    ):
        """Test handling when no SMTP URI is configured."""
        pdf_path, excel_path = test_files

        # Configure mocks - no SMTP URI
        mock_config.SMTP_URI = None
        mock_config.REPORT_SENDER_EMAIL = "sender@example.com"

        # Call function
        success, report_info = await send_report_email_with_smtp(
            mock_follower, "2025-05", pdf_path, excel_path
        )

        # Should fail without SMTP URI
        assert success is False
        assert report_info["email_sent"] is False
        mock_smtp_class.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.service.notifier_smtp.minio_service")
    @patch("app.service.notifier_smtp.SMTPEmailSender")
    @patch("app.service.notifier_smtp.config")
    async def test_send_smtp_failure(
        self, mock_config, mock_smtp_class, mock_minio, mock_follower, test_files
    ):
        """Test handling of SMTP send failure."""
        pdf_path, excel_path = test_files

        # Configure mocks
        mock_config.SMTP_URI = "smtp://smtp.example.com:587"
        mock_config.REPORT_SENDER_EMAIL = "sender@example.com"
        mock_config.ADMIN_EMAIL = None

        mock_minio.is_configured.return_value = False

        # Mock SMTP sender to fail
        mock_smtp_sender = AsyncMock()
        mock_smtp_sender.send_email.return_value = False
        mock_smtp_class.return_value = mock_smtp_sender

        # Call function
        success, report_info = await send_report_email_with_smtp(
            mock_follower, "2025-05", pdf_path, excel_path
        )

        # Should fail
        assert success is False
        assert report_info["email_sent"] is False

    @pytest.mark.asyncio
    @patch("app.service.notifier_smtp.minio_service")
    @patch("app.service.notifier_smtp.SMTPEmailSender")
    async def test_send_missing_files(
        self, mock_smtp_class, mock_minio, mock_follower
    ):
        """Test handling of missing report files."""
        # Try with nonexistent files
        success, report_info = await send_report_email_with_smtp(
            mock_follower,
            "2025-05",
            "/nonexistent/report.pdf",
            "/nonexistent/report.xlsx",
        )

        assert success is False
        assert report_info["email_sent"] is False
        mock_smtp_class.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.service.notifier_smtp.minio_service")
    @patch("app.service.notifier_smtp.SMTPEmailSender")
    async def test_send_follower_no_email(
        self, mock_smtp_class, mock_minio, test_files
    ):
        """Test handling of follower without email."""
        pdf_path, excel_path = test_files

        follower = Follower(id="no-email-follower", name="No Email", enabled=True)

        success, report_info = await send_report_email_with_smtp(
            follower, "2025-05", pdf_path, excel_path
        )

        assert success is False
        assert report_info["email_sent"] is False
        mock_smtp_class.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.service.notifier_smtp.minio_service")
    @patch("app.service.notifier_smtp.SMTPEmailSender")
    @patch("app.service.notifier_smtp.config")
    async def test_partial_minio_upload_smtp(
        self, mock_config, mock_smtp_class, mock_minio, mock_follower, test_files
    ):
        """Test when only one file uploads to MinIO successfully."""
        pdf_path, excel_path = test_files

        # Configure mocks
        mock_config.SMTP_URI = "smtp://smtp.example.com:587"
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

        # Mock SMTP sender
        mock_smtp_sender = AsyncMock()
        mock_smtp_sender.send_email.return_value = True
        mock_smtp_class.return_value = mock_smtp_sender

        # Call function
        success, report_info = await send_report_email_with_smtp(
            mock_follower, "2025-05", pdf_path, excel_path
        )

        # Should fall back to attachments when partial upload
        assert success is True
        assert report_info["pdf_url"] == "https://minio.example.com/pdf-url"
        assert report_info["excel_url"] is None
        assert report_info["email_sent"] is True

        # Verify email was sent with attachments (fallback)
        email_args = mock_smtp_sender.send_email.call_args[1]
        assert len(email_args["attachments"]) == 2  # Both files as attachments
        assert "Please find attached" in email_args["html_content"]
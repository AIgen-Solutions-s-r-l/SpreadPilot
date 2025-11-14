"""Unit tests for report worker with MinIO integration and email."""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from moto import mock_aws
from report_worker.app.service.minio_service import MinIOService, minio_service
from report_worker.app.service.notifier_minio import send_report_email_with_minio
from spreadpilot_core.models.follower import Follower


@pytest.fixture
def temp_files():
    """Create temporary test files."""
    # Create temporary PDF and Excel files
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf_file:
        pdf_file.write(b"Fake PDF content")
        pdf_path = pdf_file.name

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as excel_file:
        excel_file.write(b"Fake Excel content")
        excel_path = excel_file.name

    yield pdf_path, excel_path

    # Cleanup
    os.unlink(pdf_path)
    os.unlink(excel_path)


@pytest.fixture
def test_follower():
    """Create a test follower."""
    return Follower(
        id="test_follower_123",
        name="Test User",
        email="test@example.com",
        enabled=True,
        commission_pct=20.0,
    )


class TestMinIOService:
    """Test MinIO service functionality."""

    @mock_aws
    def test_minio_upload_success(self, temp_files):
        """Test successful MinIO upload."""
        pdf_path, excel_path = temp_files

        # Mock MinIO configuration
        with patch.dict(
            os.environ,
            {
                "GOOGLE_CLOUD_PROJECT": "test-project",
                "REPORT_SENDER_EMAIL": "test@example.com",
                "MINIO_ENDPOINT_URL": "http://localhost:9000",
                "MINIO_ACCESS_KEY": "test_access",
                "MINIO_SECRET_KEY": "test_secret",
                "MINIO_BUCKET_NAME": "test-bucket",
            },
        ):
            service = MinIOService()

            # Test configuration
            assert service.is_configured() is True

            # Create mock S3 bucket
            import boto3

            s3_client = boto3.client(
                "s3",
                endpoint_url="http://localhost:9000",
                aws_access_key_id="test_access",
                aws_secret_access_key="test_secret",
                region_name="us-east-1",
            )
            s3_client.create_bucket(Bucket="test-bucket")

            # Test upload
            object_key = service.upload_report(pdf_path, "test/report.pdf")
            assert object_key == "test/report.pdf"

    def test_minio_not_configured(self):
        """Test MinIO service when not configured."""
        with patch.dict(
            os.environ,
            {
                "GOOGLE_CLOUD_PROJECT": "test-project",
                "REPORT_SENDER_EMAIL": "test@example.com",
            },
            clear=True,
        ):
            service = MinIOService()
            assert service.is_configured() is False

            result = service.upload_report("/fake/path.pdf", "test.pdf")
            assert result is None

    @mock_aws
    def test_minio_upload_with_url_generation(self, temp_files):
        """Test MinIO upload with URL generation."""
        pdf_path, excel_path = temp_files

        with patch.dict(
            os.environ,
            {
                "GOOGLE_CLOUD_PROJECT": "test-project",
                "REPORT_SENDER_EMAIL": "test@example.com",
                "MINIO_ENDPOINT_URL": "http://localhost:9000",
                "MINIO_ACCESS_KEY": "test_access",
                "MINIO_SECRET_KEY": "test_secret",
                "MINIO_BUCKET_NAME": "test-bucket",
            },
        ):
            service = MinIOService()

            # Create mock S3 bucket
            import boto3

            s3_client = boto3.client(
                "s3",
                endpoint_url="http://localhost:9000",
                aws_access_key_id="test_access",
                aws_secret_access_key="test_secret",
                region_name="us-east-1",
            )
            s3_client.create_bucket(Bucket="test-bucket")

            # Test upload with URL generation
            object_key, presigned_url = service.upload_report_with_url(
                pdf_path, "test_follower", "2025-06", "pdf"
            )

            assert object_key is not None
            assert presigned_url is not None
            assert "test_follower" in object_key
            assert "2025-06" in object_key

    def test_minio_file_not_found(self):
        """Test MinIO upload with non-existent file."""
        with patch.dict(
            os.environ,
            {
                "GOOGLE_CLOUD_PROJECT": "test-project",
                "REPORT_SENDER_EMAIL": "test@example.com",
            },
        ):
            service = MinIOService()
            result = service.upload_report("/non/existent/file.pdf", "test.pdf")
            assert result is None


class TestEmailWithMinIO:
    """Test email sending with MinIO integration."""

    @patch("report_worker.app.service.notifier_minio.send_email")
    @patch("report_worker.app.service.notifier_minio.minio_service")
    def test_email_with_minio_links(self, mock_minio, mock_send_email, test_follower, temp_files):
        """Test email sending with MinIO download links."""
        pdf_path, excel_path = temp_files

        # Mock MinIO service
        mock_minio.is_configured.return_value = True
        mock_minio.upload_report_with_url.side_effect = [
            ("pdf_key", "https://minio.example.com/pdf_url"),
            ("excel_key", "https://minio.example.com/excel_url"),
        ]

        # Mock email sending
        mock_send_email.return_value = True

        # Test email sending
        success, report_info = send_report_email_with_minio(
            test_follower, "2025-06", pdf_path, excel_path
        )

        assert success is True
        assert report_info["pdf_url"] == "https://minio.example.com/pdf_url"
        assert report_info["excel_url"] == "https://minio.example.com/excel_url"
        assert report_info["email_sent"] is True

        # Verify MinIO uploads were called
        assert mock_minio.upload_report_with_url.call_count == 2

        # Verify email was sent with links
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args

        # Check that email body contains download links
        html_content = call_args.kwargs["html_content"]
        assert "https://minio.example.com/pdf_url" in html_content
        assert "https://minio.example.com/excel_url" in html_content
        assert "valid for 30 days" in html_content

    @patch("report_worker.app.service.notifier_minio.send_email")
    @patch("report_worker.app.service.notifier_minio.minio_service")
    def test_email_with_attachments_fallback(
        self, mock_minio, mock_send_email, test_follower, temp_files
    ):
        """Test email sending with attachments when MinIO is not configured."""
        pdf_path, excel_path = temp_files

        # Mock MinIO service not configured
        mock_minio.is_configured.return_value = False

        # Mock email sending
        mock_send_email.return_value = True

        # Test email sending
        success, report_info = send_report_email_with_minio(
            test_follower, "2025-06", pdf_path, excel_path
        )

        assert success is True
        assert report_info["pdf_url"] is None
        assert report_info["excel_url"] is None
        assert report_info["email_sent"] is True

        # Verify email was sent with attachments
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args

        # Check that attachments were included
        attachments = call_args.kwargs["attachments"]
        assert len(attachments) == 2
        assert any(att["path"] == pdf_path for att in attachments)
        assert any(att["path"] == excel_path for att in attachments)

    @patch("report_worker.app.service.notifier_minio.send_email")
    @patch("report_worker.app.service.notifier_minio.minio_service")
    def test_email_with_minio_upload_failure(
        self, mock_minio, mock_send_email, test_follower, temp_files
    ):
        """Test email sending when MinIO upload fails."""
        pdf_path, excel_path = temp_files

        # Mock MinIO service configured but upload fails
        mock_minio.is_configured.return_value = True
        mock_minio.upload_report_with_url.return_value = (None, None)

        # Mock email sending
        mock_send_email.return_value = True

        # Test email sending
        success, report_info = send_report_email_with_minio(
            test_follower, "2025-06", pdf_path, excel_path
        )

        assert success is True
        assert report_info["pdf_url"] is None
        assert report_info["excel_url"] is None
        assert report_info["email_sent"] is True

        # Should fallback to attachments
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args
        attachments = call_args.kwargs["attachments"]
        assert len(attachments) == 2

    def test_email_missing_files(self, test_follower):
        """Test email sending with missing files."""
        success, report_info = send_report_email_with_minio(
            test_follower, "2025-06", "/non/existent/file.pdf", "/non/existent/file.xlsx"
        )

        assert success is False
        assert report_info["email_sent"] is False

    def test_email_follower_without_email(self, temp_files):
        """Test email sending to follower without email."""
        pdf_path, excel_path = temp_files

        # Create follower without email
        follower = Follower(
            id="test_follower",
            name="Test User",
            enabled=True,
            # email field missing
        )

        success, report_info = send_report_email_with_minio(
            follower, "2025-06", pdf_path, excel_path
        )

        assert success is False
        assert report_info["email_sent"] is False


class TestSMTPEmailSender:
    """Test SMTP email functionality."""

    @patch("spreadpilot_core.utils.email.aiosmtplib.send")
    @pytest.mark.asyncio
    async def test_smtp_email_sending(self, mock_send, temp_files):
        """Test SMTP email sending."""
        pdf_path, excel_path = temp_files

        from spreadpilot_core.utils.email import SMTPEmailSender

        # Mock successful send
        mock_send.return_value = None  # aiosmtplib.send returns None on success

        # Create SMTP sender
        sender = SMTPEmailSender(
            smtp_uri="smtp://user:pass@smtp.example.com:587",
            from_email="sender@example.com",
            from_name="Test Sender",
        )

        # Test email sending
        attachments = [
            {"path": pdf_path, "filename": "report.pdf"},
            {"path": excel_path, "filename": "report.xlsx"},
        ]

        result = await sender.send_email(
            to_email="recipient@example.com",
            subject="Test Report",
            html_content="<p>Test email</p>",
            attachments=attachments,
        )

        assert result is True
        mock_send.assert_called_once()

    @patch("spreadpilot_core.utils.email.aiosmtplib.send")
    @pytest.mark.asyncio
    async def test_smtp_email_error(self, mock_send):
        """Test SMTP email sending error handling."""
        from spreadpilot_core.utils.email import SMTPEmailSender

        # Mock send failure
        mock_send.side_effect = Exception("SMTP error")

        sender = SMTPEmailSender(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",
            from_email="sender@example.com",
        )

        result = await sender.send_email(
            to_email="recipient@example.com", subject="Test", html_content="<p>Test</p>"
        )

        assert result is False

    def test_smtp_uri_parsing(self):
        """Test SMTP URI parsing."""
        from spreadpilot_core.utils.email import SMTPEmailSender

        sender = SMTPEmailSender(
            smtp_uri="smtp://user123:pass456@mail.example.com:465", from_email="sender@example.com"
        )

        assert sender.smtp_host == "mail.example.com"
        assert sender.smtp_port == 465
        assert sender.smtp_user == "user123"
        assert sender.smtp_password == "pass456"


class TestReportServiceEnhanced:
    """Test enhanced report service functionality."""

    @patch("report_worker.app.service.report_service_enhanced.get_mongo_db")
    @patch("report_worker.app.service.report_service_enhanced.send_report_email_with_minio")
    @patch("report_worker.app.service.report_service_enhanced.generator")
    @patch("report_worker.app.service.report_service_enhanced.pnl")
    @pytest.mark.asyncio
    async def test_process_monthly_reports(self, mock_pnl, mock_generator, mock_email, mock_mongo):
        """Test complete monthly report processing."""
        import datetime

        from report_worker.app.service.report_service_enhanced import EnhancedReportService

        # Mock database
        mock_db = AsyncMock()
        mock_mongo.return_value = mock_db

        # Mock follower data
        follower_doc = {
            "_id": "test_follower",
            "name": "Test User",
            "email": "test@example.com",
            "enabled": True,
            "commission_pct": 20.0,
        }
        mock_db.__getitem__.return_value.find.return_value = AsyncMock()
        mock_db.__getitem__.return_value.find.return_value.__aiter__ = AsyncMock(
            return_value=iter([follower_doc])
        )

        # Mock P&L calculation
        mock_pnl.calculate_monthly_pnl.return_value = 1000.0
        mock_pnl.calculate_commission.return_value = 200.0

        # Mock report generation
        mock_generator.generate_pdf_report.return_value = "/fake/report.pdf"
        mock_generator.generate_excel_report.return_value = "/fake/report.xlsx"

        # Mock email sending
        mock_email.return_value = (
            True,
            {
                "pdf_url": "https://minio.example.com/pdf",
                "excel_url": "https://minio.example.com/excel",
                "email_sent": True,
            },
        )

        # Mock report status update
        mock_db.__getitem__.return_value.update_one = AsyncMock()

        # Create service and process reports
        service = EnhancedReportService()

        trigger_date = datetime.date(2025, 7, 1)  # July 1st, should process June
        await service.process_monthly_reports(trigger_date)

        # Verify P&L calculation was called
        mock_pnl.calculate_monthly_pnl.assert_called_once_with(2025, 6)

        # Verify report generation was called
        mock_generator.generate_pdf_report.assert_called_once()
        mock_generator.generate_excel_report.assert_called_once()

        # Verify email was sent
        mock_email.assert_called_once()

        # Verify database update
        mock_db.__getitem__.return_value.update_one.assert_called()

    @pytest.mark.asyncio
    async def test_report_sent_status_update(self):
        """Test report sent status database update."""
        from report_worker.app.service.report_service_enhanced import EnhancedReportService

        with patch("report_worker.app.service.report_service_enhanced.get_mongo_db") as mock_mongo:
            mock_db = AsyncMock()
            mock_mongo.return_value = mock_db

            # Mock collection
            mock_collection = AsyncMock()
            mock_db.__getitem__.return_value = mock_collection

            service = EnhancedReportService()

            await service._update_report_sent_status(
                follower_id="test_follower",
                report_period="2025-06",
                email_sent=True,
                pdf_url="https://minio.example.com/pdf",
                excel_url="https://minio.example.com/excel",
            )

            # Verify upsert was called
            mock_collection.update_one.assert_called_once()
            call_args = mock_collection.update_one.call_args

            # Check filter
            filter_dict = call_args[0][0]
            assert filter_dict["follower_id"] == "test_follower"
            assert filter_dict["report_period"] == "2025-06"

            # Check update data
            update_dict = call_args[0][1]["$set"]
            assert update_dict["email_sent"] is True
            assert update_dict["pdf_url"] == "https://minio.example.com/pdf"
            assert update_dict["excel_url"] == "https://minio.example.com/excel"
            assert update_dict["minio_upload"] is True

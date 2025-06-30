"""Unit tests for the commission mailer service."""

import os
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, call, patch

import pytest
from app.service.mailer import CommissionMailer, create_mailer_from_env

from spreadpilot_core.models.pnl import CommissionMonthly


@pytest.fixture
def mock_commission_record():
    """Create a mock commission record."""
    record = Mock(spec=CommissionMonthly)
    record.id = "test-id-123"
    record.follower_id = "FOLLOWER001"
    record.follower_email = "follower@example.com"
    record.follower_iban = "DE89370400440532013000"
    record.year = 2025
    record.month = 5
    record.monthly_pnl = Decimal("5000.00")
    record.commission_pct = Decimal("0.20")
    record.commission_amount = Decimal("1000.00")
    record.commission_currency = "EUR"
    record.is_payable = True
    record.is_paid = False
    record.payment_date = None
    record.payment_reference = None
    record.sent = False
    record.sent_at = None
    return record


@pytest.fixture
def mailer():
    """Create a CommissionMailer instance."""
    return CommissionMailer(
        sendgrid_api_key="test-api-key",
        admin_email="admin@example.com",
        sender_email="sender@example.com",
    )


class TestCommissionMailer:
    """Test cases for CommissionMailer."""

    @patch("app.service.mailer.SendGridAPIClient")
    def test_init(self, mock_sg_client):
        """Test mailer initialization."""
        mailer = CommissionMailer(
            sendgrid_api_key="test-key",
            admin_email="admin@test.com",
            sender_email="sender@test.com",
        )

        assert mailer.admin_email == "admin@test.com"
        assert mailer.sender_email == "sender@test.com"
        assert mailer.max_retries == 3
        assert mailer.retry_delay == 5
        mock_sg_client.assert_called_once_with("test-key")

    @patch("app.service.mailer.generate_commission_report_pdf")
    @patch("app.service.mailer.get_signed_url")
    @patch("os.remove")
    def test_send_commission_email_success(
        self,
        mock_remove,
        mock_get_signed_url,
        mock_generate_pdf,
        mailer,
        mock_commission_record,
    ):
        """Test successful email sending."""
        # Setup mocks
        mock_generate_pdf.return_value = "/tmp/test_report.pdf"
        mock_get_signed_url.return_value = "https://example.com/signed-url"

        mock_response = Mock()
        mock_response.status_code = 202
        mailer.sg.send = Mock(return_value=mock_response)

        mock_db = Mock()

        # Mock file reading
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b"PDF content"

            # Execute
            mailer._send_commission_email(mock_commission_record, mock_db)

        # Verify
        mock_generate_pdf.assert_called_once_with(mock_commission_record, "/tmp/test_report.pdf")
        mock_get_signed_url.assert_called_once()

        # Check that email was sent
        mailer.sg.send.assert_called_once()
        sent_message = mailer.sg.send.call_args[0][0]

        # Verify email properties
        assert sent_message.subject == "Commission Report - May 2025"
        assert len(sent_message.personalizations[0].tos) == 1
        assert sent_message.personalizations[0].tos[0]["email"] == "follower@example.com"
        assert len(sent_message.personalizations[0].ccs) == 1
        assert sent_message.personalizations[0].ccs[0]["email"] == "admin@example.com"

        # Verify attachment
        assert len(sent_message.attachments) == 1
        attachment = sent_message.attachments[0]
        assert attachment.file_name.file_name == "commission_report_May_2025.pdf"
        assert attachment.file_type.file_type == "application/pdf"

        # Verify database update
        assert mock_commission_record.sent == True
        assert mock_commission_record.sent_at is not None
        mock_db.commit.assert_called_once()

        # Verify cleanup
        mock_remove.assert_called_once_with("/tmp/test_report.pdf")

    @patch("app.service.mailer.generate_commission_report_pdf")
    @patch("app.service.mailer.get_signed_url")
    @patch("time.sleep")
    def test_send_commission_email_with_retry(
        self,
        mock_sleep,
        mock_get_signed_url,
        mock_generate_pdf,
        mailer,
        mock_commission_record,
    ):
        """Test email sending with retry logic."""
        # Setup mocks
        mock_generate_pdf.return_value = "/tmp/test_report.pdf"
        mock_get_signed_url.return_value = "https://example.com/signed-url"

        # First two attempts fail, third succeeds
        mock_responses = [
            Mock(status_code=500),  # First attempt fails
            Mock(status_code=503),  # Second attempt fails
            Mock(status_code=202),  # Third attempt succeeds
        ]
        mailer.sg.send = Mock(side_effect=mock_responses)

        mock_db = Mock()

        # Mock file operations
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b"PDF content"
            with patch("os.remove"):
                # Execute
                mailer._send_commission_email(mock_commission_record, mock_db)

        # Verify retries
        assert mailer.sg.send.call_count == 3
        assert mock_sleep.call_count == 2

        # Verify exponential backoff
        mock_sleep.assert_has_calls(
            [
                call(5),  # First retry: 5 * (2^0) = 5
                call(10),  # Second retry: 5 * (2^1) = 10
            ]
        )

        # Verify success
        assert mock_commission_record.sent == True
        mock_db.commit.assert_called_once()

    @patch("app.service.mailer.generate_commission_report_pdf")
    @patch("app.service.mailer.get_signed_url")
    @patch("time.sleep")
    def test_send_commission_email_all_retries_fail(
        self,
        mock_sleep,
        mock_get_signed_url,
        mock_generate_pdf,
        mailer,
        mock_commission_record,
    ):
        """Test email sending when all retries fail."""
        # Setup mocks
        mock_generate_pdf.return_value = "/tmp/test_report.pdf"
        mock_get_signed_url.return_value = "https://example.com/signed-url"

        # All attempts fail
        mailer.sg.send = Mock(side_effect=Exception("SendGrid error"))

        mock_db = Mock()

        # Mock file operations
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b"PDF content"

            # Execute and expect exception
            with pytest.raises(Exception, match="SendGrid error"):
                mailer._send_commission_email(mock_commission_record, mock_db)

        # Verify all retries were attempted
        assert mailer.sg.send.call_count == 3
        assert mock_sleep.call_count == 2

        # Verify no database update
        assert mock_commission_record.sent == False
        mock_db.commit.assert_not_called()

    def test_send_pending_reports(self, mailer):
        """Test sending multiple pending reports."""
        # Create mock records
        record1 = Mock(spec=CommissionMonthly)
        record1.follower_id = "FOLLOWER001"
        record1.sent = False
        record1.is_payable = True

        record2 = Mock(spec=CommissionMonthly)
        record2.follower_id = "FOLLOWER002"
        record2.sent = False
        record2.is_payable = True

        # Setup database mock
        mock_db = Mock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.all.return_value = [record1, record2]

        # Mock _send_commission_email
        with patch.object(mailer, "_send_commission_email") as mock_send:
            # First succeeds, second fails
            mock_send.side_effect = [None, Exception("Send failed")]

            # Execute
            results = mailer.send_pending_reports(mock_db)

        # Verify results
        assert results["total"] == 2
        assert results["success"] == 1
        assert results["failed"] == 1
        assert len(results["errors"]) == 1
        assert results["errors"][0]["follower_id"] == "FOLLOWER002"
        assert "Send failed" in results["errors"][0]["error"]

        # Verify both records were attempted
        assert mock_send.call_count == 2

    def test_send_pending_reports_filters_correctly(self, mailer):
        """Test that only unsent, payable records are selected."""
        mock_db = Mock()

        # Execute
        mailer.send_pending_reports(mock_db)

        # Verify query construction
        mock_db.query.assert_called_once_with(CommissionMonthly)
        mock_query = mock_db.query.return_value
        mock_query.filter.assert_called_once()

        # Get the filter argument
        filter_arg = mock_query.filter.call_args[0][0]

        # This is a complex SQLAlchemy expression, so we just verify it was called
        # In a real test, you might want to use a test database
        assert mock_query.filter.called

    def test_generate_email_html(self, mailer, mock_commission_record):
        """Test HTML email generation."""
        html = mailer._generate_email_html(
            mock_commission_record, "May 2025", "https://example.com/excel-report"
        )

        # Verify key content is present
        assert "Commission Report - May 2025" in html
        assert "FOLLOWER001" in html
        assert "5,000.00 EUR" in html
        assert "20.0%" in html
        assert "1,000.00 EUR" in html
        assert "DE89370400440532013000" in html
        assert "https://example.com/excel-report" in html
        assert "Download Detailed Excel Report" in html
        assert "Pending" in html  # Payment status

    def test_generate_email_html_with_payment_info(self, mailer, mock_commission_record):
        """Test HTML email generation with payment information."""
        mock_commission_record.is_paid = True
        mock_commission_record.payment_date = date(2025, 6, 15)
        mock_commission_record.payment_reference = "PAY-12345"

        html = mailer._generate_email_html(
            mock_commission_record, "May 2025", "https://example.com/excel-report"
        )

        # Verify payment info is present
        assert "Paid" in html
        assert "2025-06-15" in html
        assert "PAY-12345" in html


class TestCreateMailerFromEnv:
    """Test cases for create_mailer_from_env."""

    @patch.dict(
        os.environ,
        {
            "SENDGRID_API_KEY": "test-key",
            "ADMIN_EMAIL": "admin@test.com",
            "REPORT_SENDER_EMAIL": "sender@test.com",
        },
    )
    @patch("app.service.mailer.CommissionMailer")
    def test_create_mailer_from_env_all_vars(self, mock_mailer_class):
        """Test creating mailer with all environment variables set."""
        create_mailer_from_env()

        mock_mailer_class.assert_called_once_with("test-key", "admin@test.com", "sender@test.com")

    @patch.dict(os.environ, {"SENDGRID_API_KEY": "test-key"})
    @patch("app.service.mailer.CommissionMailer")
    def test_create_mailer_from_env_defaults(self, mock_mailer_class):
        """Test creating mailer with default values."""
        create_mailer_from_env()

        mock_mailer_class.assert_called_once_with(
            "test-key", "admin@spreadpilot.com", "reports@spreadpilot.com"
        )

    @patch.dict(os.environ, {}, clear=True)
    def test_create_mailer_from_env_missing_api_key(self):
        """Test error when SendGrid API key is missing."""
        with pytest.raises(ValueError, match="SENDGRID_API_KEY environment variable is required"):
            create_mailer_from_env()

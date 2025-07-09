"""Unit tests for SMTP email sender."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set TESTING environment variable before imports
os.environ["TESTING"] = "true"

from app.service.smtp_sender import SMTPEmailSender


class TestSMTPEmailSender:
    """Test cases for SMTP email sender."""

    def test_parse_smtp_uri_with_tls(self):
        """Test parsing SMTPS URI with authentication."""
        sender = SMTPEmailSender("smtps://user:pass@smtp.example.com:465")
        
        assert sender.hostname == "smtp.example.com"
        assert sender.port == 465
        assert sender.username == "user"
        assert sender.password == "pass"
        assert sender.use_tls is True

    def test_parse_smtp_uri_without_tls(self):
        """Test parsing SMTP URI without TLS."""
        sender = SMTPEmailSender("smtp://user:pass@smtp.example.com:587")
        
        assert sender.hostname == "smtp.example.com"
        assert sender.port == 587
        assert sender.username == "user"
        assert sender.password == "pass"
        assert sender.use_tls is False

    def test_parse_smtp_uri_defaults(self):
        """Test parsing SMTP URI with defaults."""
        sender = SMTPEmailSender("smtp://smtp.example.com")
        
        assert sender.hostname == "smtp.example.com"
        assert sender.port == 587  # Default for smtp://
        assert sender.username is None
        assert sender.password is None
        assert sender.use_tls is False

    @pytest.mark.asyncio
    @patch("app.service.smtp_sender.aiosmtplib.SMTP")
    async def test_send_email_success(self, mock_smtp_class):
        """Test successful email sending."""
        # Setup mock SMTP client
        mock_smtp = AsyncMock()
        mock_smtp_class.return_value.__aenter__.return_value = mock_smtp
        
        sender = SMTPEmailSender("smtp://user:pass@smtp.example.com:587")
        
        result = await sender.send_email(
            from_email="sender@example.com",
            to_email="recipient@example.com",
            subject="Test Report",
            html_content="<p>Test content</p>",
            cc_recipients=["cc@example.com"],
        )
        
        assert result is True
        
        # Verify SMTP connection
        mock_smtp_class.assert_called_once_with(
            hostname="smtp.example.com",
            port=587,
            use_tls=False,
            timeout=30,
        )
        
        # Verify authentication
        mock_smtp.login.assert_called_once_with("user", "pass")
        
        # Verify message was sent
        mock_smtp.send_message.assert_called_once()
        call_args = mock_smtp.send_message.call_args
        msg = call_args[0][0]
        
        assert msg["From"] == "sender@example.com"
        assert msg["To"] == "recipient@example.com"
        assert msg["Subject"] == "Test Report"
        assert msg["Cc"] == "cc@example.com"

    @pytest.mark.asyncio
    @patch("app.service.smtp_sender.aiosmtplib.SMTP")
    async def test_send_email_with_attachments(self, mock_smtp_class, tmp_path):
        """Test email sending with attachments."""
        # Create test files
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_bytes(b"PDF content")
        excel_file = tmp_path / "report.xlsx"
        excel_file.write_bytes(b"Excel content")
        
        # Setup mock SMTP client
        mock_smtp = AsyncMock()
        mock_smtp_class.return_value.__aenter__.return_value = mock_smtp
        
        sender = SMTPEmailSender("smtp://smtp.example.com:587")
        
        attachments = [
            {"path": str(pdf_file), "filename": "report.pdf"},
            {"path": str(excel_file), "filename": "report.xlsx"},
        ]
        
        result = await sender.send_email(
            from_email="sender@example.com",
            to_email="recipient@example.com",
            subject="Test Report",
            html_content="<p>Test content</p>",
            attachments=attachments,
        )
        
        assert result is True
        
        # Verify message was sent
        mock_smtp.send_message.assert_called_once()
        call_args = mock_smtp.send_message.call_args
        msg = call_args[0][0]
        
        # Check that attachments were added
        attachments_found = 0
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachments_found += 1
                filename = part.get_filename()
                assert filename in ["report.pdf", "report.xlsx"]
        
        assert attachments_found == 2

    @pytest.mark.asyncio
    @patch("app.service.smtp_sender.aiosmtplib.SMTP")
    async def test_send_email_no_auth(self, mock_smtp_class):
        """Test email sending without authentication."""
        # Setup mock SMTP client
        mock_smtp = AsyncMock()
        mock_smtp_class.return_value.__aenter__.return_value = mock_smtp
        
        sender = SMTPEmailSender("smtp://smtp.example.com:587")
        
        result = await sender.send_email(
            from_email="sender@example.com",
            to_email="recipient@example.com",
            subject="Test Report",
            html_content="<p>Test content</p>",
        )
        
        assert result is True
        
        # Verify no authentication attempted
        mock_smtp.login.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.service.smtp_sender.aiosmtplib.SMTP")
    async def test_send_email_failure(self, mock_smtp_class):
        """Test email sending failure."""
        # Setup mock SMTP client to raise exception
        mock_smtp = AsyncMock()
        mock_smtp.send_message.side_effect = Exception("SMTP error")
        mock_smtp_class.return_value.__aenter__.return_value = mock_smtp
        
        sender = SMTPEmailSender("smtp://smtp.example.com:587")
        
        result = await sender.send_email(
            from_email="sender@example.com",
            to_email="recipient@example.com",
            subject="Test Report",
            html_content="<p>Test content</p>",
        )
        
        assert result is False

    @pytest.mark.asyncio
    @patch("app.service.smtp_sender.aiosmtplib.SMTP")
    async def test_send_email_nonexistent_attachment(self, mock_smtp_class, tmp_path):
        """Test email sending with nonexistent attachment."""
        # Setup mock SMTP client
        mock_smtp = AsyncMock()
        mock_smtp_class.return_value.__aenter__.return_value = mock_smtp
        
        sender = SMTPEmailSender("smtp://smtp.example.com:587")
        
        attachments = [
            {"path": "/nonexistent/file.pdf", "filename": "report.pdf"},
        ]
        
        # Should still send email without the missing attachment
        result = await sender.send_email(
            from_email="sender@example.com",
            to_email="recipient@example.com",
            subject="Test Report",
            html_content="<p>Test content</p>",
            attachments=attachments,
        )
        
        assert result is True
        
        # Verify message was sent
        mock_smtp.send_message.assert_called_once()
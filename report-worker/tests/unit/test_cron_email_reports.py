"""Unit tests for the cron email reports job."""

import os
from unittest.mock import Mock, patch

from app.cron_email_reports import send_weekly_commission_reports


class TestSendWeeklyCommissionReports:
    """Test cases for send_weekly_commission_reports."""

    @patch("app.cron_email_reports.create_engine")
    @patch("app.cron_email_reports.sessionmaker")
    @patch("app.cron_email_reports.create_mailer_from_env")
    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"})
    def test_send_weekly_commission_reports_success(
        self, mock_create_mailer, mock_sessionmaker, mock_create_engine
    ):
        """Test successful execution of weekly commission reports."""
        # Setup mocks
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_session = Mock()
        mock_session_class = Mock(return_value=mock_session)
        mock_sessionmaker.return_value = mock_session_class

        mock_mailer = Mock()
        mock_create_mailer.return_value = mock_mailer

        # Mock successful sending
        mock_mailer.send_pending_reports.return_value = {
            "total": 5,
            "success": 5,
            "failed": 0,
            "errors": [],
        }

        # Execute
        result = send_weekly_commission_reports()

        # Verify
        assert result is True
        mock_create_engine.assert_called_once_with("postgresql://test:test@localhost/test")
        mock_mailer.send_pending_reports.assert_called_once_with(mock_session)
        mock_session.close.assert_called_once()

    @patch("app.cron_email_reports.create_engine")
    @patch("app.cron_email_reports.sessionmaker")
    @patch("app.cron_email_reports.create_mailer_from_env")
    @patch.dict(
        os.environ,
        {
            "DB_HOST": "testhost",
            "DB_PORT": "5433",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
        clear=True,
    )
    def test_send_weekly_commission_reports_with_individual_db_vars(
        self, mock_create_mailer, mock_sessionmaker, mock_create_engine
    ):
        """Test database URL construction from individual variables."""
        # Setup mocks
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_session = Mock()
        mock_session_class = Mock(return_value=mock_session)
        mock_sessionmaker.return_value = mock_session_class

        mock_mailer = Mock()
        mock_create_mailer.return_value = mock_mailer

        mock_mailer.send_pending_reports.return_value = {
            "total": 3,
            "success": 2,
            "failed": 1,
            "errors": [{"follower_id": "F001", "error": "Send failed"}],
        }

        # Execute
        result = send_weekly_commission_reports()

        # Verify
        assert result is True  # Returns True because some emails were sent
        expected_url = "postgresql://testuser:testpass@testhost:5433/testdb"
        mock_create_engine.assert_called_once_with(expected_url)

    @patch("app.cron_email_reports.create_engine")
    @patch("app.cron_email_reports.sessionmaker")
    @patch("app.cron_email_reports.create_mailer_from_env")
    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"})
    def test_send_weekly_commission_reports_all_failed(
        self, mock_create_mailer, mock_sessionmaker, mock_create_engine
    ):
        """Test when all emails fail to send."""
        # Setup mocks
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_session = Mock()
        mock_session_class = Mock(return_value=mock_session)
        mock_sessionmaker.return_value = mock_session_class

        mock_mailer = Mock()
        mock_create_mailer.return_value = mock_mailer

        # Mock all emails failing
        mock_mailer.send_pending_reports.return_value = {
            "total": 3,
            "success": 0,
            "failed": 3,
            "errors": [
                {"follower_id": "F001", "error": "Send failed"},
                {"follower_id": "F002", "error": "Send failed"},
                {"follower_id": "F003", "error": "Send failed"},
            ],
        }

        # Execute
        result = send_weekly_commission_reports()

        # Verify
        assert result is False
        mock_session.close.assert_called_once()

    @patch("app.cron_email_reports.create_engine")
    @patch("app.cron_email_reports.sessionmaker")
    @patch("app.cron_email_reports.create_mailer_from_env")
    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"})
    def test_send_weekly_commission_reports_no_pending(
        self, mock_create_mailer, mock_sessionmaker, mock_create_engine
    ):
        """Test when there are no pending reports."""
        # Setup mocks
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_session = Mock()
        mock_session_class = Mock(return_value=mock_session)
        mock_sessionmaker.return_value = mock_session_class

        mock_mailer = Mock()
        mock_create_mailer.return_value = mock_mailer

        # Mock no pending reports
        mock_mailer.send_pending_reports.return_value = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        # Execute
        result = send_weekly_commission_reports()

        # Verify
        assert result is True  # Still returns True when no errors
        mock_session.close.assert_called_once()

    @patch("app.cron_email_reports.create_engine")
    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"})
    def test_send_weekly_commission_reports_database_error(self, mock_create_engine):
        """Test handling of database connection errors."""
        # Mock database connection failure
        mock_create_engine.side_effect = Exception("Database connection failed")

        # Execute
        result = send_weekly_commission_reports()

        # Verify
        assert result is False

    @patch("app.cron_email_reports.create_engine")
    @patch("app.cron_email_reports.sessionmaker")
    @patch("app.cron_email_reports.create_mailer_from_env")
    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"})
    def test_send_weekly_commission_reports_mailer_error(
        self, mock_create_mailer, mock_sessionmaker, mock_create_engine
    ):
        """Test handling of mailer creation errors."""
        # Setup mocks
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_session = Mock()
        mock_session_class = Mock(return_value=mock_session)
        mock_sessionmaker.return_value = mock_session_class

        # Mock mailer creation failure
        mock_create_mailer.side_effect = ValueError("Missing API key")

        # Execute
        result = send_weekly_commission_reports()

        # Verify
        assert result is False
        mock_session.close.assert_called_once()

    @patch("app.cron_email_reports.create_engine")
    @patch("app.cron_email_reports.sessionmaker")
    @patch("app.cron_email_reports.create_mailer_from_env")
    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"})
    def test_send_weekly_commission_reports_ensures_session_closes(
        self, mock_create_mailer, mock_sessionmaker, mock_create_engine
    ):
        """Test that database session is always closed."""
        # Setup mocks
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_session = Mock()
        mock_session_class = Mock(return_value=mock_session)
        mock_sessionmaker.return_value = mock_session_class

        mock_mailer = Mock()
        mock_create_mailer.return_value = mock_mailer

        # Mock an error during sending
        mock_mailer.send_pending_reports.side_effect = Exception("Unexpected error")

        # Execute
        result = send_weekly_commission_reports()

        # Verify session is still closed
        assert result is False
        mock_session.close.assert_called_once()

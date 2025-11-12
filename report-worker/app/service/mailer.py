"""Email service for sending commission reports using SendGrid."""

import base64
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (Attachment, Content, Disposition, Email,
                                   FileContent, FileName, FileType, Mail, To)
from sqlalchemy import and_
from sqlalchemy.orm import Session

try:
    from spreadpilot_core.dry_run import dry_run
except ImportError:
    # Fallback if dry_run not available
    def dry_run(operation_type: str, return_value=None, log_args: bool = True):
        def decorator(func):
            return func

        return decorator


from spreadpilot_core.models.pnl import CommissionMonthly
from spreadpilot_core.utils.gcs import get_signed_url
from spreadpilot_core.utils.pdf import generate_commission_report_pdf

logger = logging.getLogger(__name__)


class CommissionMailer:
    """Service for sending commission reports via email."""

    def __init__(self, sendgrid_api_key: str, admin_email: str, sender_email: str):
        """Initialize the mailer with SendGrid configuration.

        Args:
            sendgrid_api_key: SendGrid API key
            admin_email: Admin email address to CC on all reports
            sender_email: Sender email address
        """
        self.sg = SendGridAPIClient(sendgrid_api_key)
        self.admin_email = admin_email
        self.sender_email = sender_email
        self.max_retries = 3
        self.retry_delay = 5  # seconds

    def send_pending_reports(self, db: Session) -> dict[str, Any]:
        """Send all pending commission reports.

        Args:
            db: Database session

        Returns:
            Dictionary with sending results
        """
        # Query for unsent commission records
        pending_records = (
            db.query(CommissionMonthly)
            .filter(
                and_(
                    CommissionMonthly.sent == False,
                    CommissionMonthly.is_payable == True,
                )
            )
            .all()
        )

        results = {
            "total": len(pending_records),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        logger.info(f"Found {len(pending_records)} pending commission reports to send")

        for record in pending_records:
            try:
                self._send_commission_email(record, db)
                results["success"] += 1
            except Exception as e:
                logger.error(f"Failed to send report for {record.follower_id}: {e!s}")
                results["failed"] += 1
                results["errors"].append({"follower_id": record.follower_id, "error": str(e)})

        return results

    @dry_run("email", return_value=None, log_args=False)
    def _send_commission_email(self, record: CommissionMonthly, db: Session):
        """Send commission email for a single record with retry logic.

        Args:
            record: Commission record to send
            db: Database session

        Note:
            When dry-run mode is enabled, this method will log the email
            but not actually send it. Database update is also skipped in dry-run mode.
        """
        month_name = datetime(record.year, record.month, 1).strftime("%B %Y")
        subject = f"Commission Report - {month_name}"

        # Generate PDF report
        pdf_path = self._generate_pdf_report(record)

        # Get signed URL for Excel report (assuming it's stored in GCS)
        excel_filename = f"commission_{record.follower_id}_{record.year}_{record.month:02d}.xlsx"
        excel_url = get_signed_url(
            bucket_name=os.getenv("GCS_BUCKET_NAME", "spreadpilot-reports"),
            blob_name=f"commission-reports/{excel_filename}",
            expiration_hours=168,  # 7 days
        )

        # Prepare email content
        html_content = self._generate_email_html(record, month_name, excel_url)

        # Create mail object
        message = Mail(
            from_email=Email(self.sender_email),
            to_emails=[To(record.follower_email)],
            subject=subject,
            html_content=Content("text/html", html_content),
        )

        # Add CC to admin
        message.add_cc(Email(self.admin_email))

        # Attach PDF
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
            pdf_encoded = base64.b64encode(pdf_data).decode()

        attachment = Attachment()
        attachment.file_content = FileContent(pdf_encoded)
        attachment.file_type = FileType("application/pdf")
        attachment.file_name = FileName(f'commission_report_{month_name.replace(" ", "_")}.pdf')
        attachment.disposition = Disposition("attachment")

        message.add_attachment(attachment)

        # Send with retry logic
        for attempt in range(self.max_retries):
            try:
                response = self.sg.send(message)

                if response.status_code in [200, 201, 202]:
                    # Update record as sent
                    record.sent = True
                    record.sent_at = datetime.utcnow()
                    db.commit()

                    logger.info(f"Successfully sent commission report to {record.follower_email}")

                    # Clean up PDF file
                    os.remove(pdf_path)
                    return
                else:
                    raise Exception(f"SendGrid returned status code: {response.status_code}")

            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {record.follower_email}: {e!s}"
                    )
                    time.sleep(self.retry_delay * (2**attempt))  # Exponential backoff
                else:
                    raise

    def _generate_pdf_report(self, record: CommissionMonthly) -> str:
        """Generate PDF report for commission record.

        Args:
            record: Commission record

        Returns:
            Path to generated PDF file
        """
        # Create temporary directory for PDFs
        pdf_dir = Path("/tmp/commission_reports")
        pdf_dir.mkdir(exist_ok=True)

        month_name = datetime(record.year, record.month, 1).strftime("%B_%Y")
        pdf_path = pdf_dir / f"commission_{record.follower_id}_{month_name}.pdf"

        # Generate PDF using utility function
        generate_commission_report_pdf(record, str(pdf_path))

        return str(pdf_path)

    def _generate_email_html(
        self, record: CommissionMonthly, month_name: str, excel_url: str
    ) -> str:
        """Generate HTML content for the email.

        Args:
            record: Commission record
            month_name: Formatted month name
            excel_url: Signed URL for Excel download

        Returns:
            HTML content string
        """
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2c3e50;">Commission Report - {month_name}</h2>
            
            <p>Dear {record.follower_id},</p>
            
            <p>Please find attached your commission report for {month_name}.</p>
            
            <h3 style="color: #34495e;">Commission Summary</h3>
            <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Monthly P&L:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{record.monthly_pnl:,.2f} {record.commission_currency}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Commission Rate:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{record.commission_pct * 100:.1f}%</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Commission Amount:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>{record.commission_amount:,.2f} {record.commission_currency}</strong></td>
                </tr>
            </table>
            
            <p><strong>Payment Details:</strong></p>
            <ul>
                <li>IBAN: {record.follower_iban}</li>
                <li>Payment Status: {'Paid' if record.is_paid else 'Pending'}</li>
                {f'<li>Payment Date: {record.payment_date}</li>' if record.payment_date else ''}
                {f'<li>Payment Reference: {record.payment_reference}</li>' if record.payment_reference else ''}
            </ul>
            
            <p style="margin-top: 30px;">
                <a href="{excel_url}" style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    Download Detailed Excel Report
                </a>
            </p>
            
            <p style="margin-top: 30px; font-size: 0.9em; color: #7f8c8d;">
                <em>This link will expire in 7 days. Please download your report promptly.</em>
            </p>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            
            <p style="font-size: 0.9em; color: #7f8c8d;">
                If you have any questions about this report, please contact our support team.
            </p>
            
            <p style="font-size: 0.9em; color: #7f8c8d;">
                Best regards,<br>
                SpreadPilot Team
            </p>
        </body>
        </html>
        """


def create_mailer_from_env() -> CommissionMailer:
    """Create a CommissionMailer instance from environment variables.

    Returns:
        Configured CommissionMailer instance
    """
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
    if not sendgrid_api_key:
        raise ValueError("SENDGRID_API_KEY environment variable is required")

    admin_email = os.getenv("ADMIN_EMAIL", "admin@spreadpilot.com")
    sender_email = os.getenv("REPORT_SENDER_EMAIL", "reports@spreadpilot.com")

    return CommissionMailer(sendgrid_api_key, admin_email, sender_email)
